"""Read-only, timestamped host diagnostics. Counters are not performance scores."""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import time
from pathlib import Path

import psutil

from . import __version__
from .common import utcnow

_java = {}


def snapshot(layout, server):
    memory = psutil.virtual_memory()
    os_info = platform.freedesktop_os_release() if platform.system() == "Linux" else {}
    cpu = platform.processor() or platform.machine()
    if platform.system() == "Linux":
        try:
            cpu = next(line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines() if line.startswith("model name"))
        except (OSError, StopIteration):
            pass
    options = layout.settings()
    java = options["java"]
    cached = _java.get(java)
    if not cached or time.monotonic() - cached[0] > 300:
        text = None
        executable = shutil.which(java)
        if executable:
            try:
                result = subprocess.run([executable, "-version"], capture_output=True, text=True, timeout=10,
                                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                text = (result.stderr + result.stdout).splitlines()[0][:200]
            except (OSError, subprocess.TimeoutExpired, IndexError):
                pass
        cached = _java[java] = (time.monotonic(), text, utcnow())
    existing = layout.home
    while not existing.exists():
        existing = existing.parent
    disk = shutil.disk_usage(existing)
    io = psutil.disk_io_counters()
    # HTTP requests use fresh threads; psutil's nonblocking baseline is per-thread.
    # A bounded explicit interval avoids publishing an uninitialized 0% as live.
    per_core = psutil.cpu_percent(interval=.1, percpu=True)
    plex = []
    for process in psutil.process_iter(["name"]):
        try:
            if "plex" in (process.info["name"] or "").lower():
                plex.append({"name": process.info["name"], "rss_bytes": process.memory_info().rss})
        except psutil.Error:
            pass
    runtime = server.snapshot()
    return {"at": utcnow(), "hosting_mode": options["hosting_mode"], "backend": options["server_backend"],
            "os": os_info.get("PRETTY_NAME", platform.platform()), "cpu_model": cpu,
            "per_core_cpu_percent": per_core,
            "cpu_note": "Actual per-core utilization over a bounded 100 ms sample; use sustained telemetry for tuning.",
            "memory_total": memory.total, "memory_available": memory.available,
            "storage_total": disk.total, "storage_free": disk.free,
            "disk_io_cumulative": io._asdict() if io else None, "plex_processes": plex[:32],
            "host_uptime_seconds": max(0, time.time() - psutil.boot_time()),
            "minecraft": runtime, "java_version": cached[1], "java_checked_at": cached[2],
            "control_room_version": __version__, "connectivity_method": options["tunnel_provider"],
            "dashboard_connectivity": "This response was served by the configured host over the current connection.",
            "game_reachability": "local status reply" if runtime.get("status") else "unverified",
            "remote_join": "unverified until a real external player joins"}
