from __future__ import annotations

import contextlib
from copy import deepcopy
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


LIVE_SECONDS = 15
DIAGNOSTIC_SECONDS = 45  # Native ticket diagnostics refresh every 30 seconds.
MAX_AGE_SECONDS = 7 * 86400
HOST_FIELDS = ('host_cpu', 'host_memory_percent', 'host_memory_available',
               'server_cpu', 'server_rss', 'gc_pause_ms')
BRIDGE_FIELDS = ('heap_used', 'heap_max', 'loaded_chunks', 'entities', 'dimensions',
                 'gc_collections', 'gc_collection_ms')
CLIENT_FIELDS = ('fps', 'heap_used', 'heap_max', 'focused', 'in_world', 'screen',
                 'camera', 'frame_interval_ms')


def measurement_freshness(stamp, now, maximum=LIVE_SECONDS, parent=None):
    """Finite response-time age, without treating an old measurement as disconnect."""
    result = {'measured_at': stamp, 'age_seconds': None, 'max_age_seconds': maximum,
              'current': False, 'status': 'unavailable'}
    try:
        if type(stamp) in (int, float) and math.isfinite(stamp):
            measured = stamp
        elif isinstance(stamp, str):
            value = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
            if value.tzinfo is None:
                raise ValueError('Timestamp has no timezone')
            measured = value.timestamp()
        else:
            raise ValueError('No measurement timestamp')
        age = now - measured
        if not math.isfinite(age):
            raise ValueError('Invalid measurement age')
        result['age_seconds'] = round(min(MAX_AGE_SECONDS, max(0, age)), 3)
        if age > MAX_AGE_SECONDS:
            result['age_capped'] = True
        if age < -2:
            result.update(status='clock_skew', reason='Measurement timestamp is ahead of the current clock.')
        elif age > maximum:
            result.update(status='stale', reason='The last measurement exceeded its freshness window.')
        else:
            result.update(current=True, status='current')
        if parent is not None and not parent['current']:
            result.update(current=False, status=parent['status'],
                          reason='The cached collection is unavailable or stale.')
    except (ValueError, TypeError, OverflowError, OSError):
        result.update(measured_at=stamp if isinstance(stamp, str) else None,
                      reason='No valid measurement timestamp is available.')
    return result


class Metrics:
    def __init__(self, layout, storage, server):
        self.layout, self.storage, self.server = layout, storage, server
        self.path = layout.state / "metrics.sqlite3"
        self._stop = threading.Event()
        self._latest = {}
        self._process = None
        self._thread = None
        self.last_gc = None
        self._sizes = {"world": None, "caches": None}
        self.observers = []
        self._atlas_index = None
        self._pending_atlas = None
        self._bookkeeping_lock = threading.Lock()
        self._bookkeeping_wake = threading.Event()
        self._bookkeeping_idle = threading.Event()
        self._bookkeeping_idle.set()
        self._bookkeeping_thread = None
        self._pending_sample = None  # Coalesce; never accumulate an unbounded queue.
        self._bookkeeping_error = None
        self._clients = []
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
        sample['clients'] = deepcopy(self._clients)
        gc = self.layout.logs / "gc.log"
        if gc.exists():
            with gc.open("rb") as stream:
                stream.seek(max(0, gc.stat().st_size - 16384))
                text = stream.read(16384).decode("utf-8", errors="replace")
            pauses = re.findall(r"Pause [^\n]*?([0-9.]+)ms", text)
            if pauses:
                sample["gc_pause_ms"] = float(pauses[-1])
                sample["gc_source"] = "Most recent Java unified GC log pause (not an interval total)"
        # Storage already measures these exact categories in its owned worker.
        # Never wait for that worker's lock or recursively rescan on this path.
        storage = self.storage.snapshot()
        inventory = storage.get('breakdown', {})
        if inventory.get('measured_at'):
            sizes = {row['key']: row.get('bytes') for row in inventory.get('categories', [])}
            self._sizes = {key: sizes.get(key) for key in ('world', 'caches')}
        sample["managed_sizes"] = dict(self._sizes)
        sample['managed_sizes_at'] = inventory.get('measured_at')
        sample['managed_sizes_updating'] = inventory.get('updating', False)
        sample["alerts"] = self.alerts(sample, storage_snapshot=storage)
        if self._bookkeeping_error:
            sample['bookkeeping_error'] = self._bookkeeping_error
        self._latest = sample
        self._queue_bookkeeping(sample)
        return sample

    def _queue_bookkeeping(self, sample):
        with self._bookkeeping_lock:
            if self._stop.is_set():
                return
            self._pending_sample = deepcopy(sample)
            self._bookkeeping_idle.clear()
            if self._bookkeeping_thread is None:
                self._bookkeeping_thread = threading.Thread(
                    target=self._run_bookkeeping, daemon=True, name='awft-metrics-bookkeeping')
                self._bookkeeping_thread.start()
            self._bookkeeping_wake.set()

    def _run_bookkeeping(self):
        while True:
            self._bookkeeping_wake.wait()
            with self._bookkeeping_lock:
                sample, self._pending_sample = self._pending_sample, None
                atlas = self._pending_atlas
                self._bookkeeping_wake.clear()
            if sample is None:
                if self._stop.is_set():
                    return
                continue
            try:
                self._bookkeep(sample, atlas)
                self._bookkeeping_error = None
            except Exception as exc:
                self._bookkeeping_error = str(exc)
            with self._bookkeeping_lock:
                if self._pending_sample is not None:
                    self._bookkeeping_wake.set()
                else:
                    self._bookkeeping_idle.set()
                    if self._stop.is_set():
                        return

    def _bookkeep(self, sample, atlas):
        # This reservation may wait for the inventory lock and scan the project.
        # It still precedes every managed index/history write; live telemetry
        # keeps its own collector while this independent work is pending.
        self.storage.checkpoint(64 * 1024 * 1024)
        if self._stop.is_set():
            return
        process_at = time.time()
        clients = self.clients.collect()
        for client in clients:
            client['process_at'] = process_at
        self._clients = clients
        if self._stop.is_set():
            return
        if atlas and atlas[0] != self._atlas_index:
            write_json(self.layout.state / 'atlas-index.json', atlas[1])
            self._atlas_index = atlas[0]
            with self._bookkeeping_lock:
                if self._pending_atlas is not None and self._pending_atlas[0] == atlas[0]:
                    self._pending_atlas = None
        for observer in self.observers:
            if self._stop.is_set():
                return
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
            sample.update(dimensions=data["dimensions"], tick_at=data["at"], bridge_at=data['at'],
                          tick_source="Owned NeoForge server bridge: tick events and JVM management beans",
                          bridge_age_seconds=round(age, 2))
            sample["players"] = players
            sample['player_roster_at'] = data['at'] if 'players' in data else None
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
                    with self._bookkeeping_lock:
                        self._pending_atlas = (serialized, atlas['locations'])
            sample["unavailable"].pop("dimensions", None)
            if data.get('chunk_diagnostics'):
                from .chunks import validate
                sample['chunk_diagnostics'] = validate(data['chunk_diagnostics'])
        except (OSError, ValueError, KeyError, TypeError) as exc:
            sample["bridge_error"] = str(exc)

    def alerts(self, sample, storage_snapshot=None):
        alerts = []
        storage = storage_snapshot if storage_snapshot is not None else self.storage.snapshot()
        low = any(d.get("low") or d.get("free", 0) < (32 * GiB if os.name == "nt" else d.get("reserve", 30 * GiB) + GiB)
                  for d in storage["drives"])
        settings = self.layout.settings()
        over_world = self._sizes["world"] is not None and self._sizes["world"] >= (settings["world_budget_gib"] - 1) * GiB
        over_cache = self._sizes["caches"] is not None and self._sizes["caches"] >= settings["cache_budget_gib"] * GiB
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
        """Project the authorized cached sample at response time; never rewrite history.

        No probes, file reads, process checks or game commands belong on this
        request path. A stalled collector is not an offline server or player.
        """
        sample = deepcopy(self._latest)
        now = time.time()
        snapshot = measurement_freshness(sample.get('at'), now)
        tick = measurement_freshness(sample.get('tick_at'), now, parent=snapshot)
        bridge = measurement_freshness(sample.get('bridge_at'), now, parent=snapshot)
        roster = measurement_freshness(sample.get('player_roster_at'), now, parent=bridge)
        sample['freshness'] = {'evaluated_at': now, 'snapshot': snapshot,
                               'tick': tick, 'bridge': bridge, 'players': roster}
        sample['last_known'] = {}
        sample['tick_measured_at'] = sample.get('tick_at')
        sample['bridge_measured_at'] = sample.get('bridge_at')
        sample['bridge_age_seconds'] = bridge['age_seconds']
        unavailable = sample.setdefault('unavailable', {})

        def retain(group, fields, measured_at):
            known = {key: sample.get(key) for key in fields if key in sample}
            if known:
                sample['last_known'][group] = dict(known, measured_at=measured_at)
            for key in fields:
                if key in sample:
                    sample[key] = None

        if not snapshot['current']:
            retain('snapshot', HOST_FIELDS, sample.get('at'))
            if sample.get('alerts'):
                sample['last_known'].setdefault('snapshot', {})['alerts'] = sample['alerts']
                sample['alerts'] = []
        if not tick['current']:
            retain('tick', ('tps', 'mspt', 'tick_at', 'tick_source'), sample.get('tick_at'))
            unavailable.update(tps='A fresh tick measurement is unavailable.',
                               mspt='A fresh tick measurement is unavailable.')
        if not bridge['current']:
            retain('bridge', (*BRIDGE_FIELDS, 'bridge_at', 'players', 'bridge_capabilities',
                              'player_roster_at', 'cinematics', 'atlas_renderer', 'atlas_objects', 'atlas_claims',
                              'atlas_index_full'), sample.get('bridge_at'))
            sample.update(players=None, bridge_capabilities=[], cinematics={}, atlas_renderer=None,
                          atlas_objects=[], atlas_claims={'available': False, 'items': [],
                          'unavailable': 'Fresh server bridge telemetry is unavailable.'})
            for key in BRIDGE_FIELDS:
                unavailable[key] = 'Fresh server bridge telemetry is unavailable.'
        sample['players_available'] = roster['current'] and isinstance(sample.get('players'), dict)
        if not sample['players_available']:
            if sample.get('players'):
                sample['last_known']['players'] = {'players': sample['players'],
                                                   'measured_at': sample.get('player_roster_at')}
            sample['players'] = None
        sample['players_online'] = len(sample['players']) if sample['players_available'] else None

        claims = sample.get('atlas_claims')
        if isinstance(claims, dict):
            fresh = measurement_freshness(claims.get('at'), now, DIAGNOSTIC_SECONDS, parent=bridge)
            sample['freshness']['atlas_claims'] = fresh
            if not fresh['current']:
                sample['last_known']['atlas_claims'] = claims
                sample['atlas_claims'] = {'at': claims.get('at'), 'available': False, 'items': [],
                    'unavailable': 'Claim boundaries are stale or unavailable; retained observations are last known.'}

        diagnostic = sample.get('chunk_diagnostics')
        if diagnostic:
            fresh = measurement_freshness(diagnostic.get('at'), now,
                                          DIAGNOSTIC_SECONDS, parent=bridge)
            sample['freshness']['chunk_diagnostics'] = fresh
            if not fresh['current']:
                sample['last_known']['chunk_diagnostics'] = diagnostic
                sample['chunk_diagnostics'] = {'at': diagnostic.get('at'),
                    'unavailable': 'Chunk diagnostics are stale or unavailable; retained measurements are last known.',
                    'freshness': fresh}

        for client in sample.get('clients', []):
            fresh = measurement_freshness(client.get('at'), now, parent=snapshot)
            client['freshness'] = fresh
            process = measurement_freshness(client.get('process_at', sample.get('at')), now, parent=snapshot)
            client['process_freshness'] = process
            client['last_known'] = {}
            if not fresh['current']:
                client['last_known']['game'] = {key: client[key] for key in ('at', *CLIENT_FIELDS)
                                                if key in client}
                for key in CLIENT_FIELDS:
                    if key in client:
                        client[key] = None
            if not process['current']:
                client['last_known']['process'] = {key: client[key] for key in ('rss', 'cpu_percent_host')
                                                   if key in client}
                client['last_known']['process']['measured_at'] = client.get('process_at', sample.get('at'))
                client.update(rss=None, cpu_percent_host=None)
        return sample

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
        self._bookkeeping_wake.set()
        if self._thread:
            self._thread.join(timeout=10)
        if self._bookkeeping_thread:
            self._bookkeeping_thread.join(timeout=10)
