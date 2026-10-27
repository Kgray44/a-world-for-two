from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import stat
import threading
import time
import zipfile
from pathlib import Path, PurePosixPath

from .common import UserError, atomic_write, contained, digest, read_json, utcnow, write_json
from .storage import tree_size


class Backups:
    def __init__(self, layout, storage, server):
        self.layout, self.storage, self.server = layout, storage, server
        self._stop = threading.Event()
        self._thread = None
        self.last_schedule_error = None
        self._schedule_started = time.time()

    def list(self):
        return [dict(read_json(path), id=path.stem) for path in sorted(self.layout.backups.glob("*.json"), reverse=True)
                if not path.name.endswith(".failure.json")]

    def _unlocked_world(self):
        for path in self.layout.world.rglob("session.lock"):
            try:
                with path.open("r+b") as stream:
                    if os.name == "nt":
                        import msvcrt
                        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        import fcntl
                        fcntl.lockf(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB, 1)
                        fcntl.lockf(stream.fileno(), fcntl.LOCK_UN, 1)
            except OSError as exc:
                raise UserError("The world is locked by a writer; stop it before continuing") from exc

    def create(self, notify=lambda _: None, reason="manual", resume=True):
        with self.layout.mutation:
            was_running = self.server.running()
            if was_running:
                self.server.stop(notify=notify)
            if self.server.running():
                raise UserError("Server is still writing; backup stopped")
            self._unlocked_world()
            ident = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + os.urandom(3).hex()
            target = self.layout.backups / (ident + ".zip")
            partial = target.with_suffix(".zip.partial")
            roots = [self.layout.world, self.layout.server / "config", self.layout.server / "defaultconfigs"]
            single = [self.layout.server / "server.properties", self.layout.server / "whitelist.json",
                      self.layout.server / "ops.json", self.layout.server / "installed.json", self.layout.home / "packwiz/active.json"]
            files = [f for root in roots if root.exists() for f in root.rglob("*") if f.is_file()]
            files += [f for f in single if f.is_file()]
            if not any(f.name == "level.dat" for f in files):
                raise UserError("There is no saved world to back up yet")
            for file in files:
                contained(self.layout.home, file.relative_to(self.layout.home).as_posix())
            size = sum(f.stat().st_size for f in files)
            estimate = size + size // 100 + len(files) * 2048 + 1024 * 1024
            self.storage.reserve(estimate)
            manifest = {"format": 1, "id": ident, "created": utcnow(), "reason": reason, "files": []}
            try:
                compression = zipfile.ZIP_DEFLATED if self.layout.settings()["backup_compression"] else zipfile.ZIP_STORED
                with zipfile.ZipFile(partial, "x", compression=compression, compresslevel=3) as archive:
                    for file in files:
                        if file.name == "session.lock":
                            continue
                        relative = file.relative_to(self.layout.home).as_posix()
                        record = {"path": relative, "size": file.stat().st_size, "sha256": digest(file)}
                        manifest["files"].append(record)
                        archive.write(file, relative)
                        self.storage.checkpoint(estimate, target)
                    archive.writestr("awft-backup.json", json.dumps(manifest))
                self.verify_archive(partial)
                os.replace(partial, target)
                receipt = {"created": manifest["created"], "reason": reason, "bytes": target.stat().st_size,
                           "source_bytes": size, "sha256": digest(target), "integrity": "verified",
                           "files": len(manifest["files"]), "pack": read_json(self.layout.home / "packwiz/active.json")}
                write_json(target.with_suffix(".json"), receipt)
                notify("Backup verified: " + ident)
                self.prune()
            except Exception as exc:
                write_json(self.layout.backups / (ident + ".failure.json"), {"at": utcnow(), "error": str(exc), "partial": partial.name})
                raise
            # Restart only after integrity succeeded. A failed backup deliberately leaves the server stopped.
            if was_running and resume:
                try:
                    self.server.start(notify=notify)
                    self.server.wait_ready()
                except Exception as exc:
                    # The archive is valid even when the subsequent startup fails.
                    # Keep both facts rather than claiming the backup restored service.
                    receipt["resume"] = {"state": "failed", "error": str(exc), "at": utcnow()}
                    write_json(target.with_suffix(".json"), receipt)
                    raise UserError("Backup " + ident + " is verified, but Minecraft did not resume: " + str(exc)) from exc
                receipt["resume"] = {"state": "online", "at": utcnow()}
                write_json(target.with_suffix(".json"), receipt)
            return dict(receipt, id=ident)

    def verify_archive(self, path):
        import hashlib
        with zipfile.ZipFile(path) as archive:
            info = archive.getinfo("awft-backup.json")
            if info.file_size > 8 * 1024 * 1024:
                raise UserError("Backup manifest exceeds its size limit")
            manifest = json.loads(archive.read(info))
            if manifest.get("format") != 1 or not isinstance(manifest.get("files"), list):
                raise UserError("Unsupported backup format")
            expected = {"awft-backup.json"}
            total = 0
            for record in manifest["files"]:
                relative = record["path"]
                pure = PurePosixPath(relative)
                if pure.is_absolute() or any(p in ("..", ".", "") for p in pure.parts) or "\\" in relative or ":" in relative:
                    raise UserError("Unsafe backup path")
                if not (relative.startswith("world/") or relative.startswith("server/config/")
                        or relative.startswith("server/defaultconfigs/") or relative in
                        {"server/server.properties", "server/whitelist.json", "server/ops.json", "server/installed.json", "packwiz/active.json"}):
                    raise UserError("Backup contains an unmanaged path")
                if relative in expected:
                    raise UserError("Duplicate backup entry")
                expected.add(relative)
                entry = archive.getinfo(relative)
                if stat.S_ISLNK(entry.external_attr >> 16) or entry.file_size != record["size"]:
                    raise UserError("Invalid backup entry")
                total += entry.file_size
                if total > self.layout.settings()["project_budget_gib"] * 1024 ** 3:
                    raise UserError("Backup exceeds the configured project allocation")
                hasher = hashlib.sha256()
                with archive.open(entry) as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b""):
                        hasher.update(block)
                if hasher.hexdigest() != record["sha256"]:
                    raise UserError("Backup content hash mismatch: " + relative)
            if len(archive.namelist()) != len(expected) or set(archive.namelist()) != expected:
                raise UserError("Backup has unexpected or duplicate entries")
            return manifest, total

    def verify(self, ident, notify=lambda _: None):
        path = self.path(ident)
        receipt = read_json(path.with_suffix(".json"))
        if not receipt or digest(path) != receipt["sha256"]:
            raise UserError("Backup archive hash mismatch")
        manifest, total = self.verify_archive(path)
        return {"id": ident, "integrity": "verified", "source_bytes": total, "files": len(manifest["files"])}

    def path(self, ident):
        if not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z-[a-f0-9]{6}", ident):
            raise UserError("Invalid backup ID")
        return contained(self.layout.backups, ident + ".zip")

    def restore(self, ident, confirmation, notify=lambda _: None):
        with self.layout.mutation:
            if confirmation != "RESTORE " + ident:
                raise UserError("Type RESTORE followed by the exact backup ID to approve world replacement")
            if self.server.running():
                raise UserError("Stop the server before restoring a world")
            self._unlocked_world()
            self.verify(ident)
            path = self.path(ident)
            manifest, total = self.verify_archive(path)
            self.storage.reserve(total + 1024 * 1024)
            stage = self.layout.staging / ("restore-" + ident + "-" + os.urandom(3).hex())
            stage.mkdir()
            with zipfile.ZipFile(path) as archive:
                for record in manifest["files"]:
                    target = contained(stage, record["path"])
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(record["path"]) as source, target.open("xb") as dest:
                        shutil.copyfileobj(source, dest, 1024 * 1024)
                    if digest(target) != record["sha256"]:
                        raise UserError("Extracted backup integrity check failed")
                    self.storage.checkpoint(total, stage)
            # Preserve the current world in place by renaming it on the same volume.
            safety = self.layout.home / ("pre-restore-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + os.urandom(3).hex())
            safety.mkdir()
            if self.layout.world.exists():
                os.replace(self.layout.world, safety / "world")
            try:
                os.replace(stage / "world", self.layout.world)
            except Exception:
                if (safety / "world").exists() and not self.layout.world.exists():
                    os.replace(safety / "world", self.layout.world)
                raise
            # Restore content-bearing configuration too, but retain the current installation's
            # network/world-path properties and release pointer until release rollback is approved.
            for group in ("config", "defaultconfigs"):
                source, target = stage / "server" / group, self.layout.server / group
                if source.exists():
                    if target.exists():
                        os.replace(target, safety / group)
                    os.replace(source, target)
            write_json(safety / "receipt.json", {"restored_from": ident, "at": utcnow(),
                       "note": "Pre-restore world and configs preserved. Original properties and release metadata are retained in the staged snapshot for explicit reconciliation."})
            notify("World restored; prior world preserved at " + str(safety))
            return {"restored": ident, "previous_world": str(safety), "restart_required": True,
                    "warning": "If this backup uses another pack version, roll back that release before starting."}

    def prune(self):
        history = self.list()
        keep = self.layout.settings()["backup_keep"]
        for receipt in history[keep:]:
            if receipt.get("reason") in ("before-deploy", "before-rollback", "before-restore"):
                continue
            if receipt.get("integrity") != "verified":
                continue
            path = self.path(receipt["id"])
            # Delete only our own recorded archives with their original verified bytes.
            if path.is_file() and digest(path) == receipt["sha256"]:
                path.unlink()
                path.with_suffix(".json").unlink()

    def start_schedule(self):
        def run():
            while not self._stop.wait(30):
                history = self.list()
                last = max((self.path(x["id"]).stat().st_mtime for x in history), default=self._schedule_started)
                interval = self.layout.settings()["backup_interval_hours"] * 3600
                if time.time() - last >= interval and self.server.state == "online":
                    try:
                        self.create(reason="scheduled")
                        self.last_schedule_error = None
                    except Exception as exc:
                        self.last_schedule_error = str(exc)
        self._thread = threading.Thread(target=run, daemon=True, name="awft-backups")
        self._thread.start()

    def close(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=10)
