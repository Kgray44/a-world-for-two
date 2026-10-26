"""Bound every managed allocation and recheck both host reserves."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

from .common import GiB, UserError, utcnow

FLOOR = 30 * GiB
GUARD = Path(r"C:\Users\kkids\AppData\Local\AeroStorageWatch\ReserveGuard.ps1")
MAX_FILES = 1_000_000


def tree_size(root: Path, limit=None):
    total = count = 0
    if not root.exists():
        return 0
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if not (Path(directory) / d).is_symlink()
                   and not (Path(directory) / d).is_junction()]
        for file in files:
            path = Path(directory) / file
            if path.is_symlink():
                raise UserError("Linked files cannot be included in managed storage")
            total += path.stat().st_size
            count += 1
            if count > MAX_FILES:
                raise UserError("Directory has too many files for a bounded operation")
            if limit is not None and total > limit:
                raise UserError("Operation exceeds its declared byte budget")
    return total


class Storage:
    def __init__(self, layout):
        self.layout = layout
        self._lock = threading.RLock()
        self._checked = 0.0
        self.last = None
        self._usage = (0.0, 0)
        self._breakdown = None
        self._scan_at = 0.0

    def usage(self, force=False):
        if force or time.monotonic() - self._usage[0] > 60:
            self._usage = (time.monotonic(), tree_size(self.layout.home))
        return self._usage[1]

    def breakdown(self, force=False):
        """Measure all project files, including worlds, staging and failed receipts."""
        with self._lock:
            if self._breakdown is not None and not force and time.monotonic() - self._scan_at < 5:
                return self._breakdown
            started = time.monotonic()
            labels = {"world": "World saves", "server": "Server & installed mods", "dashboard": "Control Room & history",
                      "configs": "Configuration history", "backups": "Backups", "logs": "Logs & diagnostics",
                      "caches": "Download & LOD caches", "packwiz": "Pack releases", "instances": "Prism instances",
                      "exports": "Client exports", "staging": "Staging & test environments"}
            buckets, problems, identities = {}, [], set()
            measure_allocation = None
            if os.name == "nt":
                import ctypes
                from ctypes import wintypes
                kernel = ctypes.WinDLL("kernel32", use_last_error=True)
                method = kernel.GetCompressedFileSizeW
                method.argtypes, method.restype = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD)], wintypes.DWORD
                def measure_allocation(path):
                    high = wintypes.DWORD(0)
                    ctypes.set_last_error(0)
                    low = method(str(path), ctypes.byref(high))
                    if low == 0xffffffff and ctypes.get_last_error():
                        raise OSError(ctypes.get_last_error(), "Unable to measure allocated bytes")
                    return (high.value << 32) | low
            count = 0
            for directory, dirs, files in os.walk(self.layout.home, followlinks=False,
                                                  onerror=lambda error: problems.append(str(error))):
                retained = []
                for name in dirs:
                    path = Path(directory) / name
                    if path.is_symlink() or path.is_junction():
                        problems.append("Linked directory excluded: " + str(path))
                    else:
                        retained.append(name)
                dirs[:] = retained
                for name in files:
                    path = Path(directory) / name
                    relative = path.relative_to(self.layout.home)
                    key = relative.parts[0] if len(relative.parts) > 1 else "other"
                    label = labels.get(key, "Preserved prior worlds" if key.startswith("pre-restore-") else key)
                    item = buckets.setdefault(key, {"key": key, "label": label, "bytes": 0, "allocated_bytes": 0, "files": 0})
                    try:
                        if path.is_symlink():
                            problems.append("Linked file excluded: " + relative.as_posix())
                            continue
                        status = path.stat()
                        item["bytes"] += status.st_size
                        item["files"] += 1
                        identity = (status.st_dev, status.st_ino)
                        if identity not in identities:
                            item["allocated_bytes"] += measure_allocation(path) if measure_allocation else getattr(status, "st_blocks", 0) * 512
                            identities.add(identity)
                        count += 1
                        if count > MAX_FILES:
                            raise UserError("Storage inventory exceeded its bounded file-count limit")
                    except FileNotFoundError:
                        problems.append("A file changed while scanning; the next sample will refresh it")
                    except OSError as exc:
                        problems.append(str(exc))
            for key, label in labels.items():
                buckets.setdefault(key, {"key": key, "label": label, "bytes": 0, "allocated_bytes": 0, "files": 0})
            self._breakdown = {"measured_at": utcnow(), "scan_ms": round((time.monotonic() - started) * 1000, 1),
                               "categories": sorted(buckets.values(), key=lambda x: x["bytes"], reverse=True),
                               "bytes": sum(x["bytes"] for x in buckets.values()),
                               "allocated_bytes": sum(x["allocated_bytes"] for x in buckets.values()),
                               "files": count, "complete": not problems, "issues": problems[:30], "refresh_seconds": 5,
                               "note": "Live sampled file sizes, including worlds. Allocated bytes exclude filesystem metadata; hardlinks count once. Drive free space is measured independently. Files can grow between samples."}
            self._scan_at = time.monotonic()
            self._usage = (self._scan_at, self._breakdown["bytes"])
            return self._breakdown

    def reserve(self, additional: int, target: Path | None = None):
        if type(additional) is not int or additional < 0:
            raise UserError("A finite, nonnegative allocation estimate is required")
        target = (target or self.layout.home).resolve()
        with self._lock:
            if self.usage(force=True) + additional > self.layout.settings()["project_budget_gib"] * GiB:
                raise UserError("This operation would exceed the project's 100 GiB storage budget")
            if os.name == "nt":
                drive = target.drive.upper()
                estimates = {"C:": 0, "D:": 0}
                if drive not in estimates:
                    raise UserError("Managed data must be on C: or D: on this host")
                estimates[drive] = additional
                if not GUARD.is_file():
                    raise UserError("The required AeroStorageWatch ReserveGuard.ps1 is missing")
                result = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", str(GUARD), "-EstimatedCBytes", str(estimates["C:"]),
                    "-EstimatedDBytes", str(estimates["D:"])], capture_output=True, text=True,
                    timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
                try:
                    receipt = json.loads(result.stdout.strip().splitlines()[-1])
                except (ValueError, IndexError) as exc:
                    raise UserError("Storage guard did not return a valid receipt") from exc
                self.last = receipt
                if result.returncode or not receipt.get("allowed"):
                    raise UserError("Storage reserve check rejected this operation: " + receipt.get("reason", "unknown"))
            else:
                # Portable tests and CI retain the same floor on their actual volume.
                existing = target
                while not existing.exists():
                    existing = existing.parent
                free = shutil.disk_usage(existing).free
                self.last = {"allowed": free - additional >= FLOOR, "free": free, "estimated": additional}
                if not self.last["allowed"]:
                    raise UserError("The operation would cross the 30 GiB storage reserve")
            self._checked = time.monotonic()
            return self.last

    def checkpoint(self, remaining=0, target=None, force=False):
        if force or time.monotonic() - self._checked >= 240:
            return self.reserve(remaining, target)
        return self.last

    def snapshot(self):
        disks = []
        paths = ["C:\\", "D:\\"] if os.name == "nt" else [str(self.layout.home.anchor)]
        for path in paths:
            try:
                item = shutil.disk_usage(path)
                disks.append({"drive": path, "total": item.total, "used": item.used,
                              "free": item.free, "reserve": FLOOR, "low": item.free <= FLOOR})
            except OSError:
                disks.append({"drive": path, "error": "Drive unavailable"})
        breakdown = self.breakdown()
        return {"drives": disks, "project_bytes": breakdown["bytes"], "breakdown": breakdown,
                "project_budget": self.layout.settings()["project_budget_gib"] * GiB,
                "last_guard": self.last,
                "coverage": "Managed writers only. External applications and already-running unrelated writers are outside this monitor."}
