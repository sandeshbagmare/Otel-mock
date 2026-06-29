#!/usr/bin/env bash
# mockotel launcher for macOS / Linux (mirror of start.bat)
set -euo pipefail
cd "$(dirname "$0")"

PY="$(command -v python3 || command -v python || true)"

menu() {
  cat <<'EOF'
============================================================
           mockotel : mock OpenTelemetry providers
============================================================

  [1]  Quick start (Python, no install) - pick providers & ports
  [2]  Start ALL providers + dashboard on default ports
  [3]  Docker full stack (adds real OTEL Collector :4317/:4318)
  [4]  Docker + REAL backends (Jaeger, Zipkin, Prometheus, Grafana)
  [5]  Send sample telemetry to all providers
  [6]  Replay saved captures to a provider
  [7]  List providers
  [0]  Exit

EOF
}

need_py() {
  if [ -z "$PY" ]; then
    echo "Python 3 not found. Install it, or use option [3] Docker." ; return 1
  fi
}

while true; do
  clear 2>/dev/null || true
  menu
  read -rp "  Choose [1]: " choice
  choice="${choice:-1}"
  case "$choice" in
    1) need_py && "$PY" -m mockotel ;;
    2) need_py && "$PY" -m mockotel --all ;;
    3) command -v docker >/dev/null || { echo "Docker not found."; read -r _; continue; }
       docker compose -f docker/docker-compose.yml up --build ;;
    4) command -v docker >/dev/null || { echo "Docker not found."; read -r _; continue; }
       echo "UIs: Jaeger :16686  Zipkin :9411  Prometheus :9090  Grafana :3000"
       docker compose -f docker/docker-compose.yml -f docker/real-backends.yml up --build ;;
    5) need_py && "$PY" examples/send_test_telemetry.py --all; read -rp "Enter to continue..." _ ;;
    6) need_py && read -rp "Replay to which provider port? [5001]: " rp; rp="${rp:-5001}"
       "$PY" examples/replay.py --to "http://localhost:${rp}"; read -rp "Enter to continue..." _ ;;
    7) need_py && "$PY" -m mockotel --list; read -rp "Enter to continue..." _ ;;
    0) exit 0 ;;
    *) ;;
  esac
done
