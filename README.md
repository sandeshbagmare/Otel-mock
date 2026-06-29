# mockotel — mock OpenTelemetry providers on localhost

Spin up local, branded mock versions of popular observability vendors —
**Sumo Logic, Datadog, New Relic, Honeycomb, Grafana Cloud, Splunk, Dynatrace,
Elastic** — each with its own web interface that shows the telemetry it
receives in real time. Point your app's OpenTelemetry exporter at any of them
(or at the bundled collector) and watch the data arrive.

Built for **testing and learning**: try "sending to a provider" without a SaaS
account, an API key, or an internet connection. Everything runs on your laptop,
in memory, and disappears when you stop it.

> ⚠️ These are **mocks**, not the real products. They imitate the ingest
> endpoints so you can test exporters and pipelines locally. No data ever
> leaves your machine.

```
   Your app (any OpenTelemetry SDK)
        │  OTLP gRPC :4317  /  OTLP HTTP :4318     (via the Docker collector)
        ▼
  ┌─────────────────────┐   re-encodes every signal as OTLP/JSON and fans out
  │  OTEL Collector      │ ───────────────┐
  └─────────────────────┘                 │
        │  …or send OTLP/JSON straight to a provider
        ▼                                  ▼
  Sumo Logic :5001   Datadog :5002   New Relic :5003   Honeycomb :5004
  Grafana :5005      Splunk :5006    Dynatrace :5007    Elastic :5008
        └──────────────── all aggregated by ────────────────┘
                  ★ Unified Dashboard :8080

  (optional) the same collector also feeds REAL open-source backends:
  Jaeger :16686    Zipkin :9411    Prometheus :9090    Grafana :3000
```

---

## Quick start

### Windows (no install)

Double-click **`start.bat`** (or run it in a terminal). You'll get a menu:

```
  [1]  Quick start (Python, no install) - pick providers & ports
  [2]  Start ALL providers + dashboard on default ports
  [3]  Docker full stack (adds real OTEL Collector :4317/:4318)
  [4]  Send sample telemetry to all providers
  [5]  List providers
```

Pick **[1]**, choose which providers and which base port (just press Enter for
all on the defaults), and your browser opens the unified dashboard at
<http://localhost:8080>. The only requirement is **Python 3.8+** on your PATH.

### macOS / Linux

```bash
./start.sh
# or directly:
python3 -m mockotel            # interactive menu
python3 -m mockotel --all      # everything on default ports
```

### See it light up

In another terminal, generate some sample telemetry (pure stdlib, no SDK):

```bash
python examples/send_test_telemetry.py --all
```

Open <http://localhost:8080> and watch traces, metrics, and logs stream into
every provider.

---

## Providers & default ports

| Provider               | Port | Imitates                                        |
|------------------------|------|-------------------------------------------------|
| Sumo Logic             | 5001 | OTLP/HTTP Source (`/receiver/v1/otlp/<id>/…`)    |
| Datadog                | 5002 | Intake + APM trace agent (`/api/v2/series`, `/v0.4/traces`) |
| New Relic              | 5003 | Metric/Trace/Log API + OTLP                      |
| Honeycomb              | 5004 | Events API (`/1/batch/<dataset>`) + OTLP         |
| Grafana Cloud          | 5005 | OTLP gateway / Loki / Mimir push                 |
| Splunk Observability   | 5006 | SignalFx ingest + HEC + OTLP                     |
| Dynatrace              | 5007 | OTLP + metrics/logs ingest                       |
| Elastic Observability  | 5008 | APM Server intake + OTLP                          |
| **Unified dashboard**  | 8080 | aggregates all of the above                      |

Every provider accepts **OTLP/HTTP + JSON** on the standard paths:

```
POST http://localhost:<port>/v1/traces
POST http://localhost:<port>/v1/metrics
POST http://localhost:<port>/v1/logs
```

…plus that vendor's "native" ingest paths (shown on each provider's own page),
which are accepted and displayed too.

---

## Sending telemetry to it

### From your application (OTLP/JSON, no Docker needed)

Point your OpenTelemetry SDK's HTTP/JSON exporter at a provider:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:5001   # = Sumo Logic mock
export OTEL_EXPORTER_OTLP_PROTOCOL=http/json
```

### From any SDK including gRPC/protobuf (Docker)

The pure-Python servers speak **OTLP/JSON**. To accept **protobuf and gRPC**
from any unmodified SDK, run the bundled collector — it receives OTLP on the
standard ports and forwards JSON to the mocks:

```bash
docker compose -f docker/docker-compose.yml up --build
```

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318   # HTTP (protobuf or json)
# or http://localhost:4317 for gRPC
```

One OTLP request to the collector fans out to **all eight** providers at once.

### With curl

```bash
curl -X POST http://localhost:5001/v1/traces \
  -H 'Content-Type: application/json' \
  -d '{"resourceSpans":[{"resource":{"attributes":[{"key":"service.name",
       "value":{"stringValue":"my-svc"}}]},"scopeSpans":[{"spans":[
       {"traceId":"11111111111111111111111111111111","spanId":"2222222222222222",
        "name":"GET /","kind":2,"startTimeUnixNano":"1700000000000000000",
        "endTimeUnixNano":"1700000000050000000","status":{"code":1}}]}]}]}'
```

### With the sample generator

```bash
python examples/send_test_telemetry.py --all            # all default ports
python examples/send_test_telemetry.py --endpoint http://localhost:5002
python examples/send_test_telemetry.py --collector http://localhost:4318
python examples/send_test_telemetry.py --all --rounds 10 --delay 0.3
```

---

## The dashboards

- **Per-provider page** (`http://localhost:<port>`) — branded like the real
  vendor, with a live table of received traces/metrics/logs, filters, search,
  pause, and click-to-expand raw JSON. It also shows the exact endpoint URLs to
  point your exporter at.
- **Unified dashboard** (`http://localhost:8080`) — one live view across every
  provider: per-provider cards with counts, plus a merged "firehose" of all
  telemetry colour-coded by provider.

All data is in-memory (a ring buffer, default 2000 items per provider) and is
gone when you stop the process.

---

## Real backends too (optional)

The mocks show you *what was sent*. If you also want **real, self-hostable
backends with their genuine UIs**, bring up the real-backends overlay — the same
collector fans every signal out to the mocks **and** to real software:

```bash
docker compose -f docker/docker-compose.yml -f docker/real-backends.yml up --build
```

| Real backend | UI                       | Signals  |
|--------------|--------------------------|----------|
| Jaeger       | <http://localhost:16686> | traces   |
| Zipkin       | <http://localhost:9411>  | traces   |
| Prometheus   | <http://localhost:9090>  | metrics  |
| Grafana      | <http://localhost:3000>  | traces + metrics (anonymous admin, datasources pre-provisioned) |

Point your app at the collector (`:4318` / `:4317`) and one trace appears in the
mock providers **and** in Jaeger, Zipkin, and Grafana at the same time.

## Persist & replay (optional)

By default everything is in-memory and vanishes on stop. Add `--persist` to save
received telemetry to `captures/<provider>.jsonl` and **reload it on the next
start**, so your data survives restarts:

```bash
python -m mockotel --all --persist
```

Replay captured telemetry into any provider, the collector, or the real
backends — it rebuilds OTLP/JSON from the captures and re-sends it:

```bash
python examples/replay.py --to http://localhost:5001          # into Sumo Logic mock
python examples/replay.py --collector http://localhost:4318    # through the collector
python examples/replay.py --file captures/datadog.jsonl --to http://localhost:5002
```

## CLI reference

```
python -m mockotel                       # interactive menu
python -m mockotel --all                 # start every provider + dashboard
python -m mockotel --providers sumologic,datadog
python -m mockotel --all --base-port 6000        # shift ports (provider i -> 6000+i)
python -m mockotel --all --dashboard-port 9000
python -m mockotel --all --persist               # save to ./captures and reload on restart
python -m mockotel --all --persist --persist-dir mydata
python -m mockotel --all --no-dashboard --no-browser
python -m mockotel --host 0.0.0.0        # bind all interfaces (used in Docker)
python -m mockotel --list                # list providers and exit
```

---

## Add or customise providers

Providers are defined in **`providers.json`** — no code changes needed. Add an
entry and restart:

```json
{
  "id": "mybackend",
  "name": "My Backend",
  "color": "#222831",
  "accent": "#00ADB5",
  "port": 5009,
  "tagline": "My internal telemetry sink",
  "native_paths": ["/ingest/v1"],
  "native_label": "mybackend"
}
```

- `color` / `accent` drive the page's branding.
- `native_paths` are extra POST paths (besides the OTLP `/v1/*` ones) that this
  provider should accept and display.

---

## How it works

- Each provider is a tiny `http.server`-based server (Python standard library,
  no dependencies). It decodes **OTLP/JSON** — hex trace/span IDs, decimal
  nanosecond timestamps, and the typed `AnyValue` attribute wrappers — into flat
  records, stores them in a ring buffer, and serves a polling JSON API the UI
  reads.
- The **unified dashboard** stores nothing; it fans out to each provider's
  `/api/stats` and `/api/records` over HTTP and merges the results, so native
  (single-process) and Docker (multi-container) modes behave identically.
- The **Docker collector** is the real upstream
  `otel/opentelemetry-collector-contrib`, configured with `encoding: json` on
  its `otlphttp` exporters so it converts protobuf/gRPC into JSON the mocks can
  read.

### Limitations

- The Python servers don't decode raw **OTLP/protobuf** bodies (that needs the
  proto schema); they acknowledge them and tell you to use OTLP/JSON or the
  collector. The collector path handles protobuf/gRPC for you.
- This validates **transport and payload shape**, not vendor-specific
  semantics, auth, or query languages. It's a test harness, not a real backend.

---

## References

- [OTLP specification](https://opentelemetry.io/docs/specs/otlp/)
- [OTLP/HTTP exporter `encoding: json`](https://github.com/open-telemetry/opentelemetry-collector/blob/main/exporter/otlphttpexporter/README.md)
- [Sumo Logic OTLP/HTTP Source](https://www.sumologic.com/help/docs/send-data/hosted-collectors/http-source/otlp/)

## License

MIT — see [LICENSE](LICENSE). Provider names are trademarks of their respective
owners and are used only to label local mock endpoints; this project is not
affiliated with any of them.
