"""Unified dashboard server.

It does not store anything itself — on each API call it fans out to every
provider's /api/stats and /api/records over HTTP, merges the results, and
serves one combined view. This makes native (single-process) mode and Docker
(multi-container) mode behave identically: the dashboard only needs the list
of provider base URLs.
"""

import json
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from .assets import dashboard_page


def _fetch(url, timeout=1.5):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def make_dashboard_handler(endpoints):
    """endpoints: list of provider dicts each with an added 'url' key."""

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "mockotel-dashboard/1.0"

        def _send(self, code, body=b"", ctype="application/json"):
            if isinstance(body, str):
                body = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def log_message(self, *args):
            pass

        def do_GET(self):
            path = urlparse(self.path).path
            if path in ("/", "/index.html"):
                self._send(200, dashboard_page(), "text/html; charset=utf-8")
            elif path == "/healthz":
                self._send(200, json.dumps({"status": "ok"}))
            elif path == "/api/stats":
                self._send(200, json.dumps(self._stats()))
            elif path == "/api/records":
                q = parse_qs(urlparse(self.path).query)
                limit = int((q.get("limit") or ["400"])[0])
                self._send(200, json.dumps({"records": self._records(limit)}, default=str))
            else:
                self._send(404, json.dumps({"error": "not found"}))

        def _stats(self):
            providers, totals = [], {"requests": 0, "total": 0, "by_signal": {}}
            for ep in endpoints:
                s = _fetch(ep.get("fetch_url", ep["url"]) + "/api/stats")
                up = s is not None
                providers.append({
                    "id": ep["id"], "name": ep["name"], "accent": ep["accent"],
                    "color": ep["color"], "tagline": ep.get("tagline", ""),
                    "url": ep["url"], "up": up, "stats": s or {},
                })
                if s:
                    totals["requests"] += s.get("requests", 0)
                    totals["total"] += s.get("total", 0)
                    for k, v in (s.get("by_signal") or {}).items():
                        totals["by_signal"][k] = totals["by_signal"].get(k, 0) + v
            return {"providers": providers, "totals": totals}

        def _records(self, limit):
            merged = []
            per = max(40, limit // max(1, len(endpoints)))
            for ep in endpoints:
                j = _fetch(ep.get("fetch_url", ep["url"]) + "/api/records?since=0&limit=%d" % per)
                if j and j.get("records"):
                    merged.extend(j["records"])
            merged.sort(key=lambda r: r.get("ts", 0))
            return merged[-limit:]

    return Handler


def serve_dashboard(endpoints, host, port):
    return ThreadingHTTPServer((host, port), make_dashboard_handler(endpoints))
