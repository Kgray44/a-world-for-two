"""Bound every managed allocation and recheck both host reserves."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

from .common import GiB, REPO, UserError, utcnow

FLOOR = 30 * GiB
GUARD = Path(r"C:\Users\kkids\AppData\Local\AeroStorageWatch\ReserveGuard.ps1")
MAX_FILES = 1_000_000


def scan_path(path):
    # Java/Gradle caches routinely exceed legacy MAX_PATH. Use the native extended
    # path form so these bytes remain visible to allocation and live inventory checks.
    path = Path(path)
    if os.name == "nt" and not str(path).startswith("\\\\?\\"):
        return Path("\\\\?\\" + str(path.resolve()))
    return path


def tree_size(root: Path, limit=None):
    root = scan_path(root)
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
            try:
                total += path.stat().st_size
            except FileNotFoundError:
                # Downloaders and Minecraft atomically rename their own temporary
                # files. A vanished entry owns no bytes; the next scan sees its new name.
                continue
            count += 1
            if count > MAX_FILES:
                raise UserError("Directory has too many files for a bounded operation")
            if limit is not None and total > limit:
                raise UserError("Operation exceeds its declared byte budget")
    return total


class Storage:
    _associated_cache = None
    _associated_lock = threading.Lock()
    def __init__(self, layout):
        self.layout = layout
        self._lock = threading.RLock()
        self._checked = 0.0
        self.last = None
        self._usage = (0.0, 0)
        self._breakdown = None
        self._scan_at = 0.0
        self._inventory_guard = threading.Lock()
        self._inventory_worker = None
        self._inventory_attempt = 0.0
        self._inventory_error = None
        self._associated_latest = None

    def usage(self, force=False):
        if force or time.monotonic() - self._usage[0] > 60:
            self._usage = (time.monotonic(), tree_size(self.layout.home))
        return self._usage[1]

    def floor(self):
        if os.name == "nt":
            return FLOOR
        value = self.layout.settings().get("storage_reserve_gib", 30)
        if type(value) is not int or not 1 <= value <= 1024:
            raise UserError("Set a Linux storage reserve between 1 and 1024 GiB")
        return value * GiB

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
            scan_root = scan_path(self.layout.home)
            for directory, dirs, files in os.walk(scan_root, followlinks=False,
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
                    relative = path.relative_to(scan_root)
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
                raise UserError(f"This operation would exceed the project's {self.layout.settings()['project_budget_gib']} GiB storage budget")
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
                # Linux uses the selected data volume and its explicit host policy.
                existing = target
                while not existing.exists():
                    existing = existing.parent
                free = shutil.disk_usage(existing).free
                floor = self.floor()
                self.last = {"allowed": free - additional >= floor, "free": free, "estimated": additional, "reserve": floor}
                if not self.last["allowed"]:
                    raise UserError("The operation would cross the configured Linux storage reserve")
            self._checked = time.monotonic()
            return self.last

    def checkpoint(self, remaining=0, target=None, force=False):
        if force or time.monotonic() - self._checked >= 240:
            return self.reserve(remaining, target)
        return self.last

    def live_inventory(self, refresh_seconds=60, force=False):
        """Return the last measured inventory while one bounded scan refreshes it.

        Recursive storage measurement must not hold up server telemetry or every
        dashboard request. An unfinished first scan is unknown, never zero bytes.
        Reserve checks still use their independent synchronous usage/drive checks.
        """
        with self._inventory_guard:
            updating = self._inventory_worker is not None and self._inventory_worker.is_alive()
            if not updating and (force or self._inventory_worker is None or time.monotonic() - self._inventory_attempt >= refresh_seconds):
                self._inventory_attempt = time.monotonic()

                def measure():
                    try:
                        self.breakdown()
                        self._associated_latest = self.associated()
                        self._inventory_error = None
                    except Exception as error:
                        self._inventory_error = str(error)[:500]
                    finally:
                        self._inventory_attempt = time.monotonic()

                self._inventory_worker = threading.Thread(target=measure, daemon=True, name="awft-storage-inventory")
                self._inventory_worker.start()
                updating = True
        breakdown = self._breakdown or {
            "measured_at": None, "scan_ms": None, "categories": [], "bytes": None,
            "allocated_bytes": None, "files": None, "complete": False, "issues": [],
            "refresh_seconds": 5, "note": "The first measured inventory is still being collected."
        }
        return dict(breakdown, updating=updating, scan_error=self._inventory_error, refresh_seconds=refresh_seconds)

    def snapshot(self, live=False, refresh=False):
        disks = []
        existing = self.layout.home
        while not existing.exists():
            existing = existing.parent
        paths = ["C:\\", "D:\\"] if os.name == "nt" else [str(existing)]
        for path in paths:
            try:
                item = shutil.disk_usage(path)
                disks.append({"drive": path, "total": item.total, "used": item.used,
                              "free": item.free, "reserve": self.floor(), "low": item.free <= self.floor()})
            except OSError:
                disks.append({"drive": path, "error": "Drive unavailable"})
        breakdown = self.live_inventory(60, force=refresh)
        return {"drives": disks, "project_bytes": breakdown["bytes"], "breakdown": breakdown,
                "associated": self._associated_latest,
                "project_budget": self.layout.settings()["project_budget_gib"] * GiB,
                "last_guard": self.last,
                "coverage": "Managed writers only. External applications and already-running unrelated writers are outside this monitor."}

    def associated(self):
        """Include source and shared launcher data without counting D: junctions twice."""
        roots = [('source','Project source & evidence',REPO,False)]
        if os.name == 'nt':
            prism=Path(os.environ.get('APPDATA', ''))/'PrismLauncher'
            roots += [(name,'Prism shared '+name,prism/name,True) for name in ('libraries','assets','meta')]
        roots=[row for row in roots if not row[2].resolve().is_relative_to(self.layout.home)]
        signature=tuple(str(row[2]) for row in roots)
        with Storage._associated_lock:
            cached=Storage._associated_cache
            if cached and cached[0]==signature and time.monotonic()-cached[1]<15:
                return cached[2]
            rows=[]
            for key,label,root,shared in roots:
                total=count=0;issues=[]
                for directory,dirs,files in os.walk(scan_path(root),followlinks=False,onerror=lambda e:issues.append(str(e))):
                    dirs[:]=[name for name in dirs if not (Path(directory)/name).is_symlink() and not (Path(directory)/name).is_junction()]
                    for name in files:
                        path=Path(directory)/name
                        if path.is_symlink():continue
                        try:
                            total+=path.stat().st_size;count+=1
                        except FileNotFoundError:issues.append('A file changed during the scan')
                        except OSError as error:issues.append(str(error))
                        if count>MAX_FILES:raise UserError('Associated storage exceeded its bounded file-count limit')
                rows.append({'key':key,'label':label,'path':str(root),'bytes':total,'files':count,'shared':shared,'complete':not issues,'issues':issues[:5]})
            result={'measured_at':utcnow(),'refresh_seconds':15,'rows':rows,'bytes':sum(row['bytes'] for row in rows),
                'note':'Additional file contents outside the runtime project. Shared Prism data can serve other modpacks, so its full measured size is shown separately. Launcher accounts, other instances, installed Java and unrelated personal files are excluded.'}
            Storage._associated_cache=(signature,time.monotonic(),result)
            return result
