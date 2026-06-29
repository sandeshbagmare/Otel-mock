"""mockotel command-line entrypoint.

Run with no selection flags for an interactive menu (used by start.bat):
    python -m mockotel

Or non-interactively:
    python -m mockotel --all
    python -m mockotel --providers sumologic,datadog --base-port 5001
    python -m mockotel --list
"""

import argparse
import os
import sys
import threading
import time
import webbrowser

from . import load_providers, __version__
from .store import Store
from .server import serve as serve_provider
from .dashboard import serve_dashboard
from .persist import Capture, load_records

BANNER = r"""
                  _              _       _
  _ __ ___   ___ | | _____  ___ | |_ ___| |
 | '_ ` _ \ / _ \| |/ / _ \/ _ \| __/ _ \ |   Mock OpenTelemetry providers,
 | | | | | | (_) |   < (_) | (_) | ||  __/ |   hosted on localhost.
 |_| |_| |_|\___/|_|\_\___/ \___/ \__\___|_|   v%s
""" % __version__


def parse_args(argv):
    p = argparse.ArgumentParser(prog="mockotel",
                                description="Host mock OpenTelemetry providers locally.")
    p.add_argument("--all", action="store_true", help="start every provider")
    p.add_argument("--providers", help="comma-separated provider ids (e.g. sumologic,datadog)")
    p.add_argument("--base-port", type=int, help="assign ports sequentially from here (provider i -> base+i)")
    p.add_argument("--dashboard-port", type=int, default=8080, help="unified dashboard port (default 8080)")
    p.add_argument("--host", default="127.0.0.1", help="bind address (use 0.0.0.0 in Docker)")
    p.add_argument("--no-dashboard", action="store_true", help="don't start the unified dashboard")
    p.add_argument("--no-browser", action="store_true", help="don't open a browser")
    p.add_argument("--persist", action="store_true",
                   help="save received telemetry to JSONL and reload it on restart")
    p.add_argument("--persist-dir", default="captures",
                   help="directory for capture files (default ./captures)")
    p.add_argument("--list", action="store_true", help="list available providers and exit")
    return p.parse_args(argv)


def choose_interactively(providers):
    print(BANNER)
    print("Available providers:\n")
    for i, p in enumerate(providers, 1):
        print("  %2d. %-22s %s" % (i, p["name"], p.get("tagline", "")))
    print("\n  Enter numbers (e.g. 1,3,5), 'all', or just press Enter for ALL.")
    raw = input("  Which providers to host? [all] ").strip().lower()

    if raw in ("", "all", "a", "*"):
        selected = list(providers)
    else:
        selected = []
        for tok in raw.replace(" ", "").split(","):
            if tok.isdigit() and 1 <= int(tok) <= len(providers):
                selected.append(providers[int(tok) - 1])
            else:
                match = [p for p in providers if p["id"] == tok or p["name"].lower() == tok]
                selected.extend(match)
        if not selected:
            print("  Nothing matched - defaulting to ALL.")
            selected = list(providers)

    base = input("  Base port for providers? [5001] ").strip()
    base_port = int(base) if base.isdigit() else 5001
    dash = input("  Dashboard port? [8080] ").strip()
    dash_port = int(dash) if dash.isdigit() else 8080
    ob = input("  Open the dashboard in your browser? [Y/n] ").strip().lower()
    open_browser = ob not in ("n", "no")
    ps = input("  Save received telemetry to disk so it survives restarts? [y/N] ").strip().lower()
    persist = ps in ("y", "yes")
    return selected, base_port, dash_port, open_browser, persist


def assign_ports(selected, base_port):
    """Return list of (provider, port). base_port overrides per-provider defaults."""
    out = []
    for i, p in enumerate(selected):
        port = (base_port + i) if base_port is not None else p["port"]
        out.append((p, port))
    return out


def run(selected, base_port, dashboard_port, host, open_browser, with_dashboard,
        persist=False, persist_dir="captures"):
    assigned = assign_ports(selected, base_port)
    servers = []
    endpoints = []
    captures = []

    if persist:
        os.makedirs(persist_dir, exist_ok=True)
        print("  Persisting telemetry to ./%s/ (restored on restart)" % persist_dir)

    for provider, port in assigned:
        store = Store()
        capture = None
        if persist:
            restored = store.bulk_load(load_records(persist_dir, provider["id"], limit=2000))
            capture = Capture(os.path.join(persist_dir, provider["id"] + ".jsonl"))
            captures.append(capture)
            if restored:
                print("    %-20s restored %d record(s)" % (provider["name"], restored))
        try:
            httpd = serve_provider(provider, store, host, port, capture)
        except OSError as e:
            print("  ! %-20s could not bind %s:%d (%s) - skipped"
                  % (provider["name"], host, port, e.strerror or e))
            continue
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        servers.append(httpd)
        disp_host = "localhost" if host in ("127.0.0.1", "0.0.0.0") else host
        # Fetch over IPv4 explicitly: resolving "localhost" can stall ~2s while
        # http.client tries ::1 first against an IPv4-only bind.
        fetch_host = "127.0.0.1" if host in ("127.0.0.1", "0.0.0.0") else host
        url = "http://%s:%d" % (disp_host, port)
        endpoints.append({**provider, "url": url,
                          "fetch_url": "http://%s:%d" % (fetch_host, port), "port": port})

    if not servers:
        print("\nNo providers started (all ports in use?). Try a different --base-port.")
        return 1

    dash_url = None
    if with_dashboard:
        try:
            dhttpd = serve_dashboard(endpoints, host, dashboard_port)
            threading.Thread(target=dhttpd.serve_forever, daemon=True).start()
            dash_url = "http://%s:%d" % ("localhost" if host in ("127.0.0.1", "0.0.0.0") else host,
                                         dashboard_port)
        except OSError as e:
            print("  ! dashboard could not bind %s:%d (%s)" % (host, dashboard_port, e.strerror or e))

    _print_table(endpoints, dash_url)

    if open_browser and dash_url:
        try:
            webbrowser.open(dash_url)
        except Exception:
            pass

    print("\n  Press Ctrl+C to stop.\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        for s in servers:
            s.shutdown()
        for c in captures:
            c.close()
    return 0


def _print_table(endpoints, dash_url):
    print("\n" + "=" * 64)
    print("  PROVIDER             URL                       OTLP endpoint")
    print("  " + "-" * 60)
    for e in endpoints:
        print("  %-20s %-25s %s/v1/{traces,metrics,logs}"
              % (e["name"][:20], e["url"], e["url"]))
    print("=" * 64)
    if dash_url:
        print("  >> UNIFIED DASHBOARD  %s" % dash_url)
        print("=" * 64)
    print("\n  Send telemetry by pointing an OTEL exporter at any URL above:")
    print("    OTEL_EXPORTER_OTLP_ENDPOINT=%s" % endpoints[0]["url"])
    print("    OTEL_EXPORTER_OTLP_PROTOCOL=http/json")
    print("  Or generate sample data:  python examples/send_test_telemetry.py --all")


def main(argv=None):
    # Make console output robust on Windows code pages (cp1252) etc.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    argv = sys.argv[1:] if argv is None else argv
    args = parse_args(argv)
    providers = load_providers()

    if args.list:
        for p in providers:
            print("%-12s %-22s default port %d" % (p["id"], p["name"], p["port"]))
        return 0

    persist = args.persist
    if args.all:
        selected, base_port = list(providers), args.base_port
        open_browser, dash_port = not args.no_browser, args.dashboard_port
    elif args.providers:
        ids = [t.strip() for t in args.providers.split(",") if t.strip()]
        selected = [p for p in providers if p["id"] in ids]
        if not selected:
            print("No matching providers for: %s" % args.providers)
            return 1
        base_port = args.base_port
        open_browser, dash_port = not args.no_browser, args.dashboard_port
    else:
        # No selection flags -> interactive menu.
        selected, base_port, dash_port, open_browser, persist = choose_interactively(providers)

    return run(selected, base_port, dash_port, args.host,
               open_browser, not args.no_dashboard, persist, args.persist_dir)


if __name__ == "__main__":
    sys.exit(main())
