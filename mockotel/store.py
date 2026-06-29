"""Thread-safe in-memory ring buffer for received telemetry records.

One Store per provider process. Records are normalised telemetry items
(see otlp.flatten_*) plus metadata about how they arrived.
"""

import threading
import time
from collections import deque, Counter


class Store:
    def __init__(self, maxlen=2000):
        self._lock = threading.Lock()
        self._buf = deque(maxlen=maxlen)
        self._seq = 0
        self._counts = Counter()      # by signal type
        self._services = Counter()    # by service.name
        self.requests = 0
        self.started = time.time()
        self.last_seen = None

    def add_items(self, items, meta):
        """Append normalised items, stamping each with a monotonic seq + ts."""
        with self._lock:
            self.requests += 1
            now = time.time()
            self.last_seen = now
            added = []
            for it in items:
                self._seq += 1
                rec = {"seq": self._seq, "ts": now}
                rec.update(meta)
                rec.update(it)
                self._buf.append(rec)
                self._counts[it.get("signal", "unknown")] += 1
                self._services[it.get("service", "unknown")] += 1
                added.append(rec)
            return added

    def bulk_load(self, records):
        """Restore previously captured records (e.g. on restart) without
        re-counting them as new requests. Keeps seq monotonic for new data."""
        with self._lock:
            for rec in records:
                self._buf.append(rec)
                self._counts[rec.get("signal", "unknown")] += 1
                self._services[rec.get("service", "unknown")] += 1
                seq = rec.get("seq", 0)
                if isinstance(seq, int) and seq > self._seq:
                    self._seq = seq
                ts = rec.get("ts")
                if isinstance(ts, (int, float)):
                    self.last_seen = ts
            return len(records)

    def since(self, seq, limit=300):
        with self._lock:
            out = [r for r in self._buf if r["seq"] > seq]
        return out[-limit:]

    def recent(self, limit=300):
        with self._lock:
            return list(self._buf)[-limit:]

    def stats(self):
        with self._lock:
            return {
                "requests": self.requests,
                "total": sum(self._counts.values()),
                "by_signal": dict(self._counts),
                "services": dict(self._services),
                "seq": self._seq,
                "uptime_s": round(time.time() - self.started, 1),
                "last_seen": self.last_seen,
            }
