"""Optional persistence: append received records to per-provider JSONL files.

Enabled with `--persist`. Each provider gets captures/<id>.jsonl; every
normalised record is written as one JSON line. On the next start with
--persist, the records are pre-loaded back into memory so the dashboards show
history immediately (data survives restarts). examples/replay.py can rebuild
OTLP/JSON from these captures and re-send them anywhere.
"""

import json
import os
import threading


def capture_path(directory, provider_id):
    return os.path.join(directory, provider_id + ".jsonl")


class Capture:
    """Thread-safe append-only JSONL writer for one provider."""

    def __init__(self, path):
        self.path = path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self._fh = open(path, "a", encoding="utf-8")

    def write_many(self, records):
        if not records:
            return
        with self._lock:
            for r in records:
                self._fh.write(json.dumps(r, default=str) + "\n")
            self._fh.flush()

    def close(self):
        with self._lock:
            try:
                self._fh.close()
            except OSError:
                pass


def load_records(directory, provider_id, limit=None):
    """Read previously captured records for one provider (most recent `limit`)."""
    path = capture_path(directory, provider_id)
    out = []
    if not os.path.exists(path):
        return out
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        return out
    return out[-limit:] if limit else out
