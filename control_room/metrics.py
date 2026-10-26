from __future__ import annotations

import contextlib
import csv
import io
import json
import os
import re
import sqlite3
import threading
import time

import psutil

from .common import GiB, utcnow
from .storage import tree_size


class Metrics:
    def __init__(self, layout, storage, server):
        self.layout, self.storage, self.server = layout, storage, server
        self.path = layout.state / "metrics.sqlite3"
        self._stop = threading.Event()
        self._latest = {}
        self._process = None
        self._thread = None
        self.last_gc = None
        self._last_storage = 0
        self._sizes = {"world": 0, "caches": 0}

    def connect(self):
        connection = sqlite3.connect(self.path, timeout=5)
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def start(self):
        self.storage.reserve(64 * 1024 * 1024)
        with self.connect() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS samples (at REAL PRIMARY KEY, data TEXT NOT NULL)")
        psutil.cpu_percent()
        self._thread = threading.Thread(target=self._run, daemon=True, name="awft-metrics")
        self._thread.start()

    def _run(self):
        while not self._stop.is_set():
            try:
                self.collect()
            except Exception as exc:
                self._latest = dict(self._latest, collection_error=str(exc))
            self._stop.wait(self.layout.settings()["sample_seconds"])

    def collect(self):
        self.server.probe()
        memory = psutil.virtual_memory()
        server = self.server.snapshot()
        sample = {"at": time.time(), "host_cpu": psutil.cpu_percent(), "host_memory_percent": memory.percent,
                  "host_memory_available": memory.available, "server_cpu": None, "server_rss": None,
                  "tps": server["tick"]["tps"], "mspt": server["tick"]["mspt"],
                  "tick_at": server["tick"]["at"], "tick_source": server["tick"]["source"],
                  "heap_used": None, "gc_pause_ms": None, "loaded_chunks": None, "entities": None,
                  "dimensions": None,
                  "unavailable": {"heap_used": "No authenticated JVM heap bridge; RSS is reported separately.",
                      "loaded_chunks": "Requires an in-game or spark report.", "entities": "Requires an in-game or spark report.",
                      "dimensions": "Requires an in-game or spark report."}}
        if server["pid"]:
            try:
                if not self._process or self._process.pid != server["pid"]:
                    self._process = psutil.Process(server["pid"])
                    self._process.cpu_percent()
                else:
                    # psutil's process percentage is one logical CPU = 100%; normalize to host capacity.
                    sample["server_cpu"] = self._process.cpu_percent() / (psutil.cpu_count() or 1)
                sample["server_rss"] = self._process.memory_info().rss
            except psutil.Error:
                self._process = None
        gc = self.layout.logs / "gc.log"
        if gc.exists():
            with gc.open("rb") as stream:
                stream.seek(max(0, gc.stat().st_size - 16384))
                text = stream.read(16384).decode("utf-8", errors="replace")
            pauses = re.findall(r"Pause [^\n]*?([0-9.]+)ms", text)
            if pauses:
                sample["gc_pause_ms"] = float(pauses[-1])
                sample["gc_source"] = "Most recent Java unified GC log pause (not an interval total)"
        if time.monotonic() - self._last_storage > 60:
            self._sizes = {"world": tree_size(self.layout.world), "caches": tree_size(self.layout.caches)}
            self._last_storage = time.monotonic()
        sample["managed_sizes"] = self._sizes
        sample["alerts"] = self.alerts(sample)
        self._latest = sample
        with self.connect() as connection:
            # Live samples arrive every 5s; persist at most one point/minute (<=10,081 rows).
            connection.execute("INSERT OR REPLACE INTO samples VALUES (?, ?)", (int(sample["at"] // 60) * 60, json.dumps(sample)))
            connection.execute("DELETE FROM samples WHERE at < ?", (time.time() - 7 * 86400,))
            connection.execute("PRAGMA wal_checkpoint(PASSIVE)")
        return sample

    def alerts(self, sample):
        alerts = []
        storage = self.storage.snapshot()
        low = any(d.get("low") or d.get("free", 0) < 32 * GiB for d in storage["drives"])
        settings = self.layout.settings()
        over_world = self._sizes["world"] >= (settings["world_budget_gib"] - 1) * GiB
        over_cache = self._sizes["caches"] >= settings["cache_budget_gib"] * GiB
        if low or over_world or over_cache:
            alerts.append({"severity": "critical", "message": "Storage reserve or managed generation budget is close to its limit. Managed server writers are stopping safely."})
            if self.server.state == "online":
                with contextlib.suppress(Exception):
                    self.server._write("chunky pause")
                    self.server._write("stop")
                    self.server.state = "stopping"
        if sample["tps"] is not None and sample["tps"] < 18:
            alerts.append({"severity": "warning", "message": "Measured TPS is below 18; review exploration, entities and moving contraptions."})
        if sample["host_memory_available"] < 3 * GiB:
            alerts.append({"severity": "warning", "message": "Less than 3 GiB system RAM is available."})
        return alerts

    def latest(self):
        return self._latest

    def history(self, hours=1):
        hours = min(max(float(hours), 1 / 60), 168)
        with self.connect() as connection:
            rows = connection.execute("SELECT data FROM samples WHERE at > ? ORDER BY at", (time.time() - hours * 3600,)).fetchall()
        values = [json.loads(row[0]) for row in rows]
        stride = max(1, len(values) // 1200)
        return values[::stride][-1200:]

    def csv(self):
        stream = io.StringIO()
        fields = ["at", "host_cpu", "host_memory_percent", "host_memory_available", "server_cpu", "server_rss", "tps", "mspt", "tick_at", "gc_pause_ms"]
        writer = csv.DictWriter(stream, fields, extrasaction="ignore")
        writer.writeheader()
        for value in self.history(168):
            writer.writerow(value)
        return stream.getvalue()

    def close(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=10)
