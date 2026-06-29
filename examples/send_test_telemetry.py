#!/usr/bin/env python3
"""Send sample OTLP/JSON traces, metrics and logs to the mock providers.

Pure standard library — no OpenTelemetry SDK or pip install needed. It builds
spec-correct OTLP/JSON (hex 32/16-char ids, decimal-string nano timestamps,
typed attribute wrappers) and POSTs it with Content-Type: application/json.

Examples
--------
    python send_test_telemetry.py --all          # hit every default provider 5001-5008
    python send_test_telemetry.py                 # just http://localhost:5001
    python send_test_telemetry.py --endpoint http://localhost:5002
    python send_test_telemetry.py --collector http://localhost:4318   # Docker collector
    python send_test_telemetry.py --all --rounds 5 --delay 0.5
"""

import argparse
import json
import secrets
import time
import urllib.request
import urllib.error

SERVICES = ["checkout-api", "payments-worker", "frontend-web", "inventory-svc"]
ROUTES = ["/cart", "/checkout", "/pay", "/orders", "/login", "/search"]


def _hex(n):
    return secrets.token_hex(n)


def _now_ns():
    return time.time_ns()


def _attr(key, value):
    if isinstance(value, bool):
        v = {"boolValue": value}
    elif isinstance(value, int):
        v = {"intValue": str(value)}
    elif isinstance(value, float):
        v = {"doubleValue": value}
    else:
        v = {"stringValue": str(value)}
    return {"key": key, "value": v}


def _resource(service):
    return {"attributes": [_attr("service.name", service),
                           _attr("telemetry.sdk.language", "python"),
                           _attr("deployment.environment", "mockotel-demo")]}


def build_traces(service):
    start = _now_ns()
    dur_ms = secrets.randbelow(400) + 10
    end = start + dur_ms * 1_000_000
    route = secrets.choice(ROUTES)
    trace_id, span_id, child = _hex(16), _hex(8), _hex(8)
    code = 2 if secrets.randbelow(10) == 0 else 1  # occasional ERROR
    return {"resourceSpans": [{
        "resource": _resource(service),
        "scopeSpans": [{
            "scope": {"name": "mockotel.demo", "version": "1.0.0"},
            "spans": [
                {"traceId": trace_id, "spanId": span_id, "name": "HTTP GET " + route,
                 "kind": 2, "startTimeUnixNano": str(start), "endTimeUnixNano": str(end),
                 "attributes": [_attr("http.method", "GET"), _attr("http.route", route),
                                _attr("http.status_code", 500 if code == 2 else 200)],
                 "status": {"code": code, "message": "error" if code == 2 else ""}},
                {"traceId": trace_id, "spanId": child, "parentSpanId": span_id,
                 "name": "db.query orders", "kind": 3,
                 "startTimeUnixNano": str(start + 1_000_000),
                 "endTimeUnixNano": str(start + dur_ms * 500_000),
                 "attributes": [_attr("db.system", "postgresql"),
                                _attr("db.statement", "SELECT * FROM orders WHERE id=$1")],
                 "status": {"code": 1}},
            ]}]}]}


def build_metrics(service):
    now = _now_ns()
    lat = secrets.randbelow(250) + 5
    rps = secrets.randbelow(900) + 100
    return {"resourceMetrics": [{
        "resource": _resource(service),
        "scopeMetrics": [{
            "scope": {"name": "mockotel.demo"},
            "metrics": [
                {"name": "http.server.request.duration", "unit": "ms",
                 "gauge": {"dataPoints": [{"asDouble": float(lat),
                                           "timeUnixNano": str(now),
                                           "attributes": [_attr("http.route", secrets.choice(ROUTES))]}]}},
                {"name": "http.server.requests", "unit": "{request}",
                 "sum": {"isMonotonic": True, "aggregationTemporality": 2,
                         "dataPoints": [{"asInt": str(rps), "timeUnixNano": str(now)}]}},
            ]}]}]}


def build_logs(service):
    now = _now_ns()
    lvl, sev = secrets.choice([("INFO", 9), ("WARN", 13), ("ERROR", 17), ("DEBUG", 5)])
    msg = {"INFO": "request handled", "WARN": "slow downstream call",
           "ERROR": "unhandled exception in handler", "DEBUG": "cache hit"}[lvl]
    return {"resourceLogs": [{
        "resource": _resource(service),
        "scopeLogs": [{
            "scope": {"name": "mockotel.demo"},
            "logRecords": [{
                "timeUnixNano": str(now), "severityNumber": sev, "severityText": lvl,
                "body": {"stringValue": "%s (%s)" % (msg, service)},
                "traceId": _hex(16), "spanId": _hex(8),
                "attributes": [_attr("log.source", "mockotel.demo"), _attr("thread", "main")]}]}]}]}


def post(base, signal, payload):
    url = base.rstrip("/") + "/v1/" + signal
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=3) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except urllib.error.URLError as e:
        return "ERR(%s)" % e.reason


def main():
    ap = argparse.ArgumentParser(description="Send sample OTLP/JSON to mock providers.")
    ap.add_argument("--endpoint", default="http://localhost:5001",
                    help="single OTLP base URL (default http://localhost:5001)")
    ap.add_argument("--all", action="store_true",
                    help="send to all default provider ports 5001-5008")
    ap.add_argument("--collector", help="send to an OTLP/HTTP collector base URL (e.g. http://localhost:4318)")
    ap.add_argument("--rounds", type=int, default=3, help="batches to send (default 3)")
    ap.add_argument("--delay", type=float, default=0.6, help="seconds between rounds")
    args = ap.parse_args()

    if args.collector:
        targets = [args.collector]
    elif args.all:
        targets = ["http://localhost:%d" % p for p in range(5001, 5009)]
    else:
        targets = [args.endpoint]

    print("Sending %d round(s) of traces+metrics+logs to:" % args.rounds)
    for t in targets:
        print("   " + t)
    print()

    for i in range(args.rounds):
        svc = SERVICES[i % len(SERVICES)]
        for base in targets:
            codes = [post(base, "traces", build_traces(svc)),
                     post(base, "metrics", build_metrics(svc)),
                     post(base, "logs", build_logs(svc))]
            print("  round %d  %-28s traces=%s metrics=%s logs=%s"
                  % (i + 1, base, codes[0], codes[1], codes[2]))
        if i < args.rounds - 1:
            time.sleep(args.delay)
    print("\nDone. Open the dashboard (http://localhost:8080) to see it live.")


if __name__ == "__main__":
    main()
