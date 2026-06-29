"""The generic mock-provider HTTP server.

One instance imitates one observability vendor. It accepts:
  * OTLP/HTTP + JSON   on /v1/traces, /v1/metrics, /v1/logs
  * the vendor's native ingest paths (from providers.json), stored opaquely
  * gzip/deflate compressed bodies (collectors compress by default)
and serves a branded web UI + a small JSON API the UI polls.

Protobuf OTLP bodies are acknowledged but not decoded (that needs the proto
schema). Use OTLP/JSON, or the bundled Docker collector which converts
protobuf/gRPC into JSON before forwarding here.
"""

import gzip
import json
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from . import otlp
from .assets import provider_page

OTLP_SIGNALS = {"/v1/traces": "traces", "/v1/metrics": "metrics", "/v1/logs": "logs"}


def _decompress(raw, encoding):
    if not raw:
        return raw
    enc = (encoding or "").lower()
    try:
        if "gzip" in enc:
            return gzip.decompress(raw)
        if "deflate" in enc:
            return zlib.decompress(raw)
    except (OSError, zlib.error):
        return raw
    return raw


def _match_native(path, provider):
    for p in provider.get("native_paths", []):
        if path == p or path.startswith(p.rstrip("/") + "/") or path.startswith(p):
            return True
    return False


def make_handler(provider, store, capture=None):
    """Build a BaseHTTPRequestHandler subclass bound to one provider + store.
    If `capture` is given, received records are also appended to disk."""

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "mockotel/1.0"

        # -- helpers ---------------------------------------------------------
        def _send(self, code, body=b"", ctype="application/json"):
            if isinstance(body, str):
                body = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "*")
            self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def log_message(self, *args):
            pass  # keep the console clean; the UI is the log

        def _read_body(self):
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            return _decompress(raw, self.headers.get("Content-Encoding"))

        # -- verbs -----------------------------------------------------------
        def do_OPTIONS(self):
            self._send(204)

        def do_GET(self):
            path = urlparse(self.path).path
            if path in ("/", "/index.html"):
                self._send(200, provider_page(provider), "text/html; charset=utf-8")
            elif path == "/healthz":
                self._send(200, json.dumps({"status": "ok", "provider": provider["id"]}))
            elif path == "/api/info":
                self._send(200, json.dumps(provider))
            elif path == "/api/stats":
                s = store.stats()
                s.update({"provider": provider["id"], "provider_name": provider["name"]})
                self._send(200, json.dumps(s))
            elif path == "/api/records":
                q = parse_qs(urlparse(self.path).query)
                since = int((q.get("since") or ["0"])[0])
                limit = int((q.get("limit") or ["300"])[0])
                recs = store.since(since, limit)
                self._send(200, json.dumps({"records": recs, "stats": store.stats()}, default=str))
            else:
                self._send(404, json.dumps({"error": "not found", "path": path}))

        def do_POST(self):
            path = urlparse(self.path).path
            ctype = self.headers.get("Content-Type", "")
            raw = self._read_body()

            # Is this an OTLP signal endpoint? (exact, or vendor-prefixed e.g.
            # Sumo's /receiver/v1/otlp/<id>/v1/traces)
            signal = OTLP_SIGNALS.get(path)
            if signal is None:
                for suffix, sig in OTLP_SIGNALS.items():
                    if path.endswith(suffix):
                        signal = sig
                        break

            if signal:
                items, ingest = self._handle_otlp(signal, ctype, raw)
                resp_code, resp_body = 200, "{}"
            elif _match_native(path, provider):
                items, ingest = self._handle_native(path, ctype, raw)
                resp_code, resp_body = 200, json.dumps({"status": "ok"})
            else:
                # Unknown path: still record it so nothing is silently dropped.
                items, ingest = self._handle_native(path, ctype, raw)
                resp_code, resp_body = 202, json.dumps({"status": "accepted", "path": path})

            meta = {"provider": provider["id"], "provider_name": provider["name"],
                    "color": provider["color"], "accent": provider["accent"],
                    "endpoint": path, "content_type": ctype, "ingest": ingest}
            if items:
                added = store.add_items(items, meta)
                if capture is not None:
                    capture.write_many(added)
            self._send(resp_code, resp_body)

        # -- ingest handling -------------------------------------------------
        def _handle_otlp(self, signal, ctype, raw):
            kind = signal[:-1]  # traces -> trace
            if "protobuf" in ctype.lower():
                note = ("OTLP/protobuf body (%d bytes) acknowledged but not decoded — "
                        "send OTLP/JSON or use the Docker collector front-door." % len(raw))
                return ([{"signal": kind, "service": "(protobuf)", "name": note,
                          "summary": note, "attributes": {}}], "otlp-protobuf")
            try:
                payload = json.loads(raw or b"{}")
                items = otlp.decode(signal, payload)
                if not items:
                    items = [{"signal": kind, "service": "(empty)",
                              "summary": "empty OTLP/%s request" % signal, "attributes": {}}]
                return items, "otlp-json"
            except ValueError as e:
                return ([{"signal": kind, "service": "(parse error)",
                          "summary": "invalid OTLP/JSON: %s" % e, "attributes": {}}], "otlp-json")

        def _handle_native(self, path, ctype, raw):
            label = provider.get("native_label", "native")
            text = raw.decode("utf-8", "replace") if raw else ""
            parsed = None
            if "json" in ctype.lower() or text[:1] in "{[":
                try:
                    parsed = json.loads(text)
                except ValueError:
                    parsed = None
            summary = "%s %s — %d bytes" % (label, path, len(raw))
            preview = text[:200].replace("\n", " ")
            if preview:
                summary += " · " + preview
            item = {"signal": "log", "service": label, "name": path,
                    "summary": summary, "endpoint": path,
                    "attributes": {"bytes": len(raw), "content_type": ctype}}
            if parsed is not None:
                item["attributes"]["payload"] = parsed
            return [item], "native:" + label

    return Handler


def serve(provider, store, host, port, capture=None):
    """Create (but do not start) a ThreadingHTTPServer for one provider."""
    return ThreadingHTTPServer((host, port), make_handler(provider, store, capture))
