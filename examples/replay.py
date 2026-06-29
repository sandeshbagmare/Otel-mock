#!/usr/bin/env python3
"""Replay captured telemetry back into a provider or collector.

Reads the JSONL capture files written by `mockotel --persist` (in ./captures/),
rebuilds OTLP/JSON requests from the normalised records, and POSTs them to a
target. Useful to reproduce a captured scenario against a fresh provider, the
Docker collector, or the real backends.

Examples
--------
    python replay.py                                   # captures/ -> http://localhost:5001
    python replay.py --dir captures --to http://localhost:5002
    python replay.py --file captures/sumologic.jsonl --collector http://localhost:4318
    python replay.py --to http://localhost:5001 --speed 2.0
"""

import argparse
import glob
import json
import os
import time
import urllib.request
import urllib.error

KIND_REV = {"UNSPECIFIED": 0, "INTERNAL": 1, "SERVER": 2, "CLIENT": 3,
            "PRODUCER": 4, "CONSUMER": 5}
STATUS_REV = {"UNSET": 0, "OK": 1, "ERROR": 2}


def _attr(key, value):
    if isinstance(value, bool):
        v = {"boolValue": value}
    elif isinstance(value, int):
        v = {"intValue": str(value)}
    elif isinstance(value, float):
        v = {"doubleValue": value}
    elif isinstance(value, (dict, list)):
        v = {"stringValue": json.dumps(value)}
    else:
        v = {"stringValue": str(value)}
    return {"key": key, "value": v}


def _attrs(d):
    return [_attr(k, v) for k, v in (d or {}).items()]


def _resource(service):
    return {"attributes": [_attr("service.name", service or "replayed")]}


def _now_ns():
    return time.time_ns()


def build_trace(rec):
    start = int(rec["start_ms"] * 1e6) if rec.get("start_ms") else _now_ns()
    dur = int((rec.get("duration_ms") or 0) * 1e6)
    span = {
        "traceId": rec.get("trace_id") or "0" * 32,
        "spanId": rec.get("span_id") or "0" * 16,
        "name": rec.get("name") or "span",
        "kind": KIND_REV.get(rec.get("kind"), 1),
        "startTimeUnixNano": str(start),
        "endTimeUnixNano": str(start + dur),
        "attributes": _attrs(rec.get("attributes")),
        "status": {"code": STATUS_REV.get(rec.get("status"), 0)},
    }
    if rec.get("parent_span_id"):
        span["parentSpanId"] = rec["parent_span_id"]
    return span


def build_metric(rec):
    mtype = rec.get("metric_type") or "gauge"
    val = rec.get("value")
    dp = {"timeUnixNano": str(_now_ns()), "attributes": _attrs(rec.get("attributes"))}
    if isinstance(val, float):
        dp["asDouble"] = val
    elif isinstance(val, int):
        dp["asInt"] = str(val)
    else:
        dp["asDouble"] = 0.0
    metric = {"name": rec.get("name") or "metric", "unit": rec.get("unit") or ""}
    if mtype == "sum":
        metric["sum"] = {"isMonotonic": True, "aggregationTemporality": 2, "dataPoints": [dp]}
    else:
        metric["gauge"] = {"dataPoints": [dp]}
    return metric


def build_log(rec):
    body = rec.get("body")
    return {
        "timeUnixNano": str(_now_ns()),
        "severityText": rec.get("severity") or "INFO",
        "severityNumber": rec.get("severity_number") or 9,
        "body": {"stringValue": "" if body is None else str(body)},
        "attributes": _attrs(rec.get("attributes")),
    }


def group_payloads(records):
    """Build one OTLP/JSON payload per (signal, service)."""
    buckets = {}
    for r in records:
        sig = r.get("signal")
        if sig not in ("trace", "metric", "log"):
            continue
        buckets.setdefault((sig, r.get("service") or "replayed"), []).append(r)

    payloads = []  # (signal_path, payload_dict)
    for (sig, service), recs in buckets.items():
        if sig == "trace":
            payloads.append(("traces", {"resourceSpans": [{
                "resource": _resource(service),
                "scopeSpans": [{"scope": {"name": "mockotel.replay"},
                                "spans": [build_trace(r) for r in recs]}]}]}))
        elif sig == "metric":
            payloads.append(("metrics", {"resourceMetrics": [{
                "resource": _resource(service),
                "scopeMetrics": [{"scope": {"name": "mockotel.replay"},
                                  "metrics": [build_metric(r) for r in recs]}]}]}))
        else:
            payloads.append(("logs", {"resourceLogs": [{
                "resource": _resource(service),
                "scopeLogs": [{"scope": {"name": "mockotel.replay"},
                               "logRecords": [build_log(r) for r in recs]}]}]}))
    return payloads


def post(base, signal, payload):
    url = base.rstrip("/") + "/v1/" + signal
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except urllib.error.URLError as e:
        return "ERR(%s)" % e.reason


def load_files(args):
    files = []
    if args.file:
        files = [args.file]
    else:
        files = sorted(glob.glob(os.path.join(args.dir, "*.jsonl")))
    records = []
    for f in files:
        if not os.path.exists(f):
            print("  (skip, not found) " + f)
            continue
        with open(f, "r", encoding="utf-8") as fh:
            n = 0
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                    n += 1
                except ValueError:
                    continue
        print("  loaded %4d records from %s" % (n, f))
    return records


def main():
    ap = argparse.ArgumentParser(description="Replay captured telemetry as OTLP/JSON.")
    ap.add_argument("--dir", default="captures", help="capture directory (default ./captures)")
    ap.add_argument("--file", help="a single capture .jsonl file")
    ap.add_argument("--to", default="http://localhost:5001", help="target OTLP base URL")
    ap.add_argument("--collector", help="OTLP collector base URL (overrides --to)")
    ap.add_argument("--speed", type=float, default=0.0,
                    help="delay (s) between batches; 0 = as fast as possible")
    args = ap.parse_args()

    target = args.collector or args.to
    print("Replaying captures -> %s\n" % target)
    records = load_files(args)
    if not records:
        print("\nNo records to replay. Run with --persist first, then send some telemetry.")
        return
    payloads = group_payloads(records)
    print("\nSending %d OTLP batch(es)..." % len(payloads))
    counts = {}
    for signal, payload in payloads:
        code = post(target, signal, payload)
        counts[signal] = counts.get(signal, 0) + 1
        print("  %-8s -> %s" % (signal, code))
        if args.speed:
            time.sleep(args.speed)
    print("\nDone. Replayed batches: %s" % counts)


if __name__ == "__main__":
    main()
