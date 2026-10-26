from __future__ import annotations

import contextlib
import csv
import io
import json
import math
import os
import re
import sqlite3
import threading
import time
from datetime import datetime

import psutil

from .common import GiB, read_json, utcnow, write_json
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
        self.observers = []
        self._atlas_index = None
        from .client_metrics import ClientMetrics
        self.clients = ClientMetrics(layout)

    @contextlib.contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=5)
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            with connection:
                yield connection
        finally:
            connection.close()

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
                  "players": {}, "bridge_capabilities": [],
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
        self.apply_bridge(sample, server)
        sample['clients'] = self.clients.collect()
        self.storage.checkpoint(64 * 1024 * 1024)
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
        for observer in self.observers:
            try:
                observer(sample)
            except Exception as exc:
                sample['atlas_monitor_error'] = str(exc)
        with self.connect() as connection:
            # Live samples arrive every 5s; persist at most one point/minute (<=10,081 rows).
            # Maps belong to the live player card and its single last-seen snapshot.
            # Repeating pixel arrays in seven days of performance history adds no value.
            history_sample = {k: v for k, v in sample.items() if k not in ("players", "bridge_capabilities", "atlas_objects", "atlas_claims", "cinematics", "chunk_diagnostics")}
            if sample.get('chunk_diagnostics', {}).get('dimensions'):
                history_sample['chunk_counts'] = {name: {k: v for k, v in row.items() if k != 'details'} for name, row in sample['chunk_diagnostics']['dimensions'].items()}
            connection.execute("INSERT OR REPLACE INTO samples VALUES (?, ?)", (int(sample["at"] // 60) * 60, json.dumps(history_sample)))
            connection.execute("DELETE FROM samples WHERE at < ?", (time.time() - 7 * 86400,))
            # A checkpoint cannot run inside this connection's write transaction.
            connection.commit()
            connection.execute("PRAGMA wal_checkpoint(PASSIVE)")
        return sample

    def apply_bridge(self, sample, server):
        """Accept only fresh data tied to this verified, owned JVM instance."""
        if server["state"] != "online" or not self.server.identity or not server["pid"]:
            return
        path = self.layout.state / "server-metrics.json"
        try:
            if not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
                return
            data = read_json(path)
            parse_time = lambda value: datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
            if data.get("format") != "awft-metrics:1" or data.get("pid") != server["pid"]:
                raise ValueError("Telemetry belongs to a different JVM")
            if abs(parse_time(data["process_started"]) - self.server.identity["created"]) > 2:
                raise ValueError("Telemetry process creation time does not match")
            age = time.time() - parse_time(data["at"])
            if not -2 <= age <= 15:
                raise ValueError("In-game telemetry is stale")
            limits = {"tps": (0, 21), "mspt": (0, 1_000_000), "heap_used": (0, 64 * GiB),
                      "heap_max": (1, 64 * GiB), "loaded_chunks": (0, 10_000_000),
                      "entities": (0, 10_000_000), "gc_collections": (0, 10**12),
                      "gc_collection_ms": (0, 10**15)}
            for key, (low, high) in limits.items():
                value = data[key]
                if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
                    raise ValueError("Invalid in-game measurement: " + key)
            if data["heap_used"] > data["heap_max"] or not isinstance(data["dimensions"], dict) or len(data["dimensions"]) > 1000:
                raise ValueError("Invalid heap or dimension measurements")
            players = data.get("players", {})
            if not isinstance(players, dict) or len(players) > 8:
                raise ValueError("Invalid player telemetry count")
            for ident, player in players.items():
                if not re.fullmatch(r"[a-f0-9-]{36}", ident) or player.get("uuid") != ident or not re.fullmatch(r"[A-Za-z0-9_]{1,16}", player.get("name", "")):
                    raise ValueError("Invalid player identity in telemetry")
                if not re.fullmatch(r"[a-z0-9_.-]+:[a-z0-9_/.-]+", player.get("dimension", "")):
                    raise ValueError("Invalid dimension in player telemetry")
                for key, bound in (("x", 30_000_000), ("y", 2048), ("z", 30_000_000), ("yaw", 10**12), ("health", 10**6), ("food", 20), ("xp_level", 2**31)):
                    value = player[key]
                    if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > bound:
                        raise ValueError("Invalid player measurement")
                if player.get("game_mode") not in ("survival", "creative", "adventure", "spectator"):
                    raise ValueError("Invalid player game mode")
                tile = player.get("map")
                if tile:
                    if tile.get("width") != 32 or tile.get("height") != 32 or tile.get("blocks_per_pixel") != 4 or len(tile.get("pixels", [])) != 1024:
                        raise ValueError("Invalid minimap dimensions")
                    if any(type(c) is not int or not -1 <= c <= 0xffffff for c in tile["pixels"]):
                        raise ValueError("Invalid minimap pixels")
                    if any(type(tile.get(key)) is not int or abs(tile[key]) > 30_001_000 for key in ("origin_x", "origin_z")):
                        raise ValueError("Invalid minimap position")
                    parse_time(tile["at"])
            for key in limits:
                sample[key] = data[key]
                sample["unavailable"].pop(key, None)
            sample.update(dimensions=data["dimensions"], tick_at=data["at"],
                          tick_source="Owned NeoForge server bridge: tick events and JVM management beans",
                          bridge_age_seconds=round(age, 2))
            sample["players"] = players
            sample["bridge_capabilities"] = [c for c in data.get("capabilities", []) if c in ("player_permissions", "player_locations", "surface_minimap", "safe_teleport", "surface_teleport", "atlas_index", "cinematics")]
            if data.get('cinematics'):
                from .cinematics import validate_telemetry
                sample['cinematics'] = validate_telemetry(data['cinematics'])
            if data.get('atlas'):
                from .atlas import validate_telemetry
                atlas = validate_telemetry(data['atlas'])
                sample['atlas_renderer'] = atlas['renderer']
                sample['atlas_objects'] = atlas['objects']
                if 'claims' in atlas:
                    sample['atlas_claims'] = atlas['claims']
                sample['atlas_index_full'] = atlas['index_full']
                serialized = json.dumps(atlas['locations'], sort_keys=True)
                if serialized != self._atlas_index:
                    # This bounded replacement is part of the metrics writer's
                    # reservation. Recheck that writer periodically instead of
                    # recursively scanning the project on every structure event.
                    self.storage.checkpoint(64 * 1024 * 1024)
                    write_json(self.layout.state / 'atlas-index.json', atlas['locations'])
                    self._atlas_index = serialized
            sample["unavailable"].pop("dimensions", None)
            if data.get('chunk_diagnostics'):
                from .chunks import validate
                sample['chunk_diagnostics'] = validate(data['chunk_diagnostics'])
        except (OSError, ValueError, KeyError, TypeError) as exc:
            sample["bridge_error"] = str(exc)

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
        fields = ["at", "host_cpu", "host_memory_percent", "host_memory_available", "server_cpu", "server_rss", "heap_used", "tps", "mspt", "tick_at", "gc_pause_ms", "loaded_chunks", "entities"]
        writer = csv.DictWriter(stream, fields, extrasaction="ignore")
        writer.writeheader()
        for value in self.history(168):
            writer.writerow(value)
        return stream.getvalue()

    def close(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=10)
