"""Minimal OTLP/JSON decoding — no external dependencies.

Reference (OTLP spec 1.x):
  * Endpoints: POST /v1/traces, /v1/metrics, /v1/logs
  * traceId/spanId/parentSpanId are lowercase hex strings (32 / 16 / 16 chars)
  * *UnixNano timestamps are decimal STRINGS (to survive 64-bit precision)
  * An AnyValue is a one-key object: stringValue | boolValue | intValue |
    doubleValue | arrayValue | kvlistValue | bytesValue
We only normalise into flat, display-friendly dicts; we never re-emit OTLP.
"""

SPAN_KIND = {0: "UNSPECIFIED", 1: "INTERNAL", 2: "SERVER", 3: "CLIENT",
             4: "PRODUCER", 5: "CONSUMER"}

STATUS_CODE = {0: "UNSET", 1: "OK", 2: "ERROR"}


def any_value(v):
    """Convert an OTLP AnyValue wrapper into a plain Python value."""
    if not isinstance(v, dict):
        return v
    if "stringValue" in v:
        return v["stringValue"]
    if "boolValue" in v:
        return v["boolValue"]
    if "intValue" in v:
        try:
            return int(v["intValue"])
        except (TypeError, ValueError):
            return v["intValue"]
    if "doubleValue" in v:
        return v["doubleValue"]
    if "bytesValue" in v:
        return v["bytesValue"]
    if "arrayValue" in v:
        return [any_value(x) for x in (v["arrayValue"] or {}).get("values", [])]
    if "kvlistValue" in v:
        return {kv.get("key"): any_value(kv.get("value"))
                for kv in (v["kvlistValue"] or {}).get("values", [])}
    return None


def attrs_to_dict(attrs):
    out = {}
    for a in attrs or []:
        out[a.get("key")] = any_value(a.get("value"))
    return out


def _service_name(resource):
    return attrs_to_dict((resource or {}).get("attributes")).get(
        "service.name", "unknown_service")


def _nano_to_ms(ns):
    try:
        return int(ns) / 1e6
    except (TypeError, ValueError):
        return None


def _sev_name(num):
    if not isinstance(num, int):
        return None
    table = [(1, "TRACE"), (5, "DEBUG"), (9, "INFO"),
             (13, "WARN"), (17, "ERROR"), (21, "FATAL")]
    name = "INFO"
    for floor, label in table:
        if num >= floor:
            name = label
    return name


def flatten_traces(payload):
    items = []
    for rs in payload.get("resourceSpans", []):
        resource = rs.get("resource")
        svc = _service_name(resource)
        rattrs = attrs_to_dict((resource or {}).get("attributes"))
        for ss in rs.get("scopeSpans", []):
            scope = (ss.get("scope") or {}).get("name")
            for sp in ss.get("spans", []):
                start = _nano_to_ms(sp.get("startTimeUnixNano"))
                end = _nano_to_ms(sp.get("endTimeUnixNano"))
                dur = (end - start) if (start is not None and end is not None) else None
                kind = SPAN_KIND.get(sp.get("kind", 0), "INTERNAL")
                status = sp.get("status") or {}
                status_code = STATUS_CODE.get(status.get("code", 0), "UNSET")
                summary = "%s [%s]" % (sp.get("name"), kind)
                if dur is not None:
                    summary += "  %.2f ms" % dur
                items.append({
                    "signal": "trace", "service": svc, "scope": scope,
                    "name": sp.get("name"), "kind": kind,
                    "trace_id": sp.get("traceId"), "span_id": sp.get("spanId"),
                    "parent_span_id": sp.get("parentSpanId") or "",
                    "start_ms": start, "duration_ms": dur,
                    "status": status_code, "status_message": status.get("message", ""),
                    "attributes": attrs_to_dict(sp.get("attributes")),
                    "resource_attributes": rattrs, "summary": summary,
                })
    return items


def flatten_metrics(payload):
    items = []
    for rm in payload.get("resourceMetrics", []):
        svc = _service_name(rm.get("resource"))
        for sm in rm.get("scopeMetrics", []):
            scope = (sm.get("scope") or {}).get("name")
            for m in sm.get("metrics", []):
                name, unit = m.get("name"), m.get("unit")
                kind, dps = None, []
                for k in ("gauge", "sum", "histogram", "exponentialHistogram", "summary"):
                    if k in m:
                        kind, dps = k, (m[k] or {}).get("dataPoints", [])
                        break
                values = []
                for dp in dps:
                    if "asDouble" in dp:
                        values.append(dp["asDouble"])
                    elif "asInt" in dp:
                        try:
                            values.append(int(dp["asInt"]))
                        except (TypeError, ValueError):
                            values.append(dp["asInt"])
                    elif "count" in dp:
                        values.append(dp.get("count"))
                last = values[-1] if values else None
                summary = "%s (%s)" % (name, kind or "?")
                if last is not None:
                    summary += " = %s" % last
                if unit:
                    summary += " %s" % unit
                items.append({
                    "signal": "metric", "service": svc, "scope": scope,
                    "name": name, "unit": unit, "metric_type": kind,
                    "value": last, "datapoints": len(dps),
                    "attributes": attrs_to_dict(dps[0].get("attributes") if dps else None),
                    "summary": summary,
                })
    return items


def flatten_logs(payload):
    items = []
    for rl in payload.get("resourceLogs", []):
        svc = _service_name(rl.get("resource"))
        for sl in rl.get("scopeLogs", []):
            scope = (sl.get("scope") or {}).get("name")
            for lr in sl.get("logRecords", []):
                body = any_value(lr.get("body"))
                sev = lr.get("severityText") or _sev_name(lr.get("severityNumber")) or "INFO"
                items.append({
                    "signal": "log", "service": svc, "scope": scope,
                    "severity": sev, "severity_number": lr.get("severityNumber"),
                    "body": body, "trace_id": lr.get("traceId") or "",
                    "span_id": lr.get("spanId") or "",
                    "attributes": attrs_to_dict(lr.get("attributes")),
                    "summary": "[%s] %s" % (sev, body),
                })
    return items


def decode(signal, payload):
    """signal is one of 'traces' | 'metrics' | 'logs'."""
    if signal == "traces":
        return flatten_traces(payload)
    if signal == "metrics":
        return flatten_metrics(payload)
    if signal == "logs":
        return flatten_logs(payload)
    return []
