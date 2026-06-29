"""mockotel — a local sandbox of mock OpenTelemetry providers.

Spins up small HTTP servers that imitate real observability vendors
(Sumo Logic, Datadog, New Relic, Honeycomb, Grafana, Splunk, Dynatrace,
Elastic). Each one accepts OTLP/HTTP+JSON (and the vendor's native ingest
paths) and shows the telemetry it received in a branded web UI. A unified
dashboard aggregates everything.

Pure standard library — no pip install required.
"""

import json
from pathlib import Path

__version__ = "1.0.0"

# Built-in fallback used if providers.json is missing/unreadable.
_BUILTIN_PROVIDERS = [
    {"id": "sumologic", "name": "Sumo Logic", "color": "#102043", "accent": "#00B5E2",
     "port": 5001, "tagline": "Continuous Intelligence · OTLP/HTTP Source",
     "native_paths": ["/receiver/v1/otlp"], "native_label": "sumo-http-source"},
    {"id": "datadog", "name": "Datadog", "color": "#632CA6", "accent": "#B388EB",
     "port": 5002, "tagline": "Cloud Monitoring as a Service",
     "native_paths": ["/api/v2/series", "/api/v2/logs", "/v0.4/traces"], "native_label": "datadog-intake"},
    {"id": "newrelic", "name": "New Relic", "color": "#0B0B0B", "accent": "#1CE783",
     "port": 5003, "tagline": "All telemetry, one platform",
     "native_paths": ["/trace/v1", "/metric/v1", "/log/v1"], "native_label": "newrelic-event-api"},
    {"id": "honeycomb", "name": "Honeycomb", "color": "#1A1A2E", "accent": "#F5A623",
     "port": 5004, "tagline": "Observability for high-cardinality data",
     "native_paths": ["/1/batch", "/1/events"], "native_label": "honeycomb-events"},
    {"id": "grafana", "name": "Grafana Cloud", "color": "#1F1F23", "accent": "#F46800",
     "port": 5005, "tagline": "Tempo · Loki · Mimir · OTLP gateway",
     "native_paths": ["/loki/api/v1/push", "/otlp"], "native_label": "grafana-gateway"},
    {"id": "splunk", "name": "Splunk Observability", "color": "#0B0B0B", "accent": "#ED0080",
     "port": 5006, "tagline": "SignalFx · HEC · OTLP",
     "native_paths": ["/v2/datapoint", "/services/collector"], "native_label": "splunk-ingest"},
    {"id": "dynatrace", "name": "Dynatrace", "color": "#1A1A2E", "accent": "#B4DC00",
     "port": 5007, "tagline": "Software intelligence platform",
     "native_paths": ["/api/v2/otlp", "/api/v2/metrics/ingest"], "native_label": "dynatrace-api"},
    {"id": "elastic", "name": "Elastic Observability", "color": "#0B1628", "accent": "#00BFB3",
     "port": 5008, "tagline": "APM · Logs · Metrics on the Elastic Stack",
     "native_paths": ["/intake/v2/events"], "native_label": "elastic-apm"},
]

_DEFAULTS = {"color": "#222831", "accent": "#00ADB5", "tagline": "Mock OTEL ingest endpoint",
             "native_paths": [], "native_label": "native"}


def _config_path() -> Path:
    return Path(__file__).resolve().parent.parent / "providers.json"


def load_providers() -> list:
    """Load provider definitions from providers.json, falling back to built-ins."""
    path = _config_path()
    providers = _BUILTIN_PROVIDERS
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("providers"), list) and data["providers"]:
            providers = data["providers"]
    except (OSError, ValueError):
        pass
    # Fill in any missing display fields so the rest of the code can rely on them.
    return [{**_DEFAULTS, **p} for p in providers]
