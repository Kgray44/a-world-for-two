from __future__ import annotations

import json
import hashlib
import os
import re
import shutil
import stat
import threading
import time
import urllib.request
import uuid
from copy import deepcopy
from pathlib import Path

from .common import REPO, UserError, contained, digest, read_json, utcnow, write_json
from .network import api
from .pack import Resolver, cache_files, generate_pack, resolve_project, validate_graph, validate_jars, validate_pack, verify_installed


SYNC_TTL_SECONDS = 60
SYNC_MAX_FILES = 1024
SYNC_MAX_BYTES = 2 * 1024 ** 3
SYNC_SCAN_SECONDS = 120


class _InventoryChanged(RuntimeError):
    pass


def _file_signature(info):
    # Python 3.12 Windows fstat exposes NTFS change time as ctime, while
    # Path.stat can expose creation time there. Birth time is common to both.
    # Keep same-handle ctime checks separately while reading the actual bytes.
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size,
            info.st_mtime_ns, getattr(info, 'st_birthtime_ns', info.st_ctime_ns))


def _small_bytes(path, missing=False):
    """Read only bounded metadata, never gameplay JAR contents on a polling thread."""
    try:
        with path.open('rb') as stream:
            opened = os.fstat(stream.fileno())
            before = _file_signature(opened)
            if before[3] > 2 * 1024 ** 2:
                raise ValueError('Integrity metadata exceeds the 2 MiB bound')
            raw = stream.read(2 * 1024 ** 2 + 1)
            finished = os.fstat(stream.fileno())
            after = _file_signature(finished)
        if before != after or after != _file_signature(path.stat()) or len(raw) != before[3]:
            raise _InventoryChanged('Integrity metadata changed while being read')
        if opened.st_ctime_ns != finished.st_ctime_ns:
            raise _InventoryChanged('Integrity metadata changed while being read')
        return raw
    except FileNotFoundError:
        if missing:
            return b''
        raise


class _OverviewIntegrity:
    """One owned, read-only worker. Its observations never authorize an operation."""
    def __init__(self, layout, capture, *, clock=time.monotonic, verifier=None):
        self.layout, self.capture, self.clock = layout, capture, clock
        self._verify = verifier or self._hash_files
        self._condition = threading.Condition()
        self._stop = threading.Event()
        self._worker = None
        self._pending = None
        self._busy = False
        self._result = None
        self._error = None
        self._attempt_signature = None
        self._attempt_finished_at = float('-inf')
        self._attempt_finished_utc = None

    def _hash_files(self, snapshot):
        """Same receipt/hash/inventory checks as strict verification, with stop/bounds.

        Startup, deploy, health and /api/sync still use verify_installed directly.
        This separate, cancellable scan exists solely for the polling display.
        """
        errors = []
        expected, files = snapshot['expected'], snapshot['files']
        if not snapshot['receipt_present']:
            errors.append('Server installation receipt is missing')
        if snapshot['receipt_pack_sha256'] != snapshot['pack_sha256']:
            errors.append('Installed receipt does not match the active pack manifest')
        if snapshot['actual'] != set(expected):
            errors.append('Server contains an unexpected mod inventory')
        deadline = time.monotonic() + SYNC_SCAN_SECONDS
        for name, expected_hash in sorted(expected.items()):
            if self._stop.is_set():
                raise InterruptedError('Overview integrity worker is closing')
            if time.monotonic() >= deadline:
                raise TimeoutError('Background integrity scan exceeded 120 seconds')
            signature = files[name]
            if signature is None or not stat.S_ISREG(signature[2]):
                errors.append('Missing or modified server file: ' + name)
                continue
            path = self.layout.server / 'mods' / name
            try:
                with path.open('rb') as stream:
                    opened = os.fstat(stream.fileno())
                    if _file_signature(opened) != signature:
                        raise _InventoryChanged('A server file changed before hashing')
                    hashed, consumed = hashlib.sha256(), 0
                    while True:
                        if self._stop.is_set():
                            raise InterruptedError('Overview integrity worker is closing')
                        if time.monotonic() >= deadline:
                            raise TimeoutError('Background integrity scan exceeded 120 seconds')
                        block = stream.read(min(1024 ** 2, signature[3] - consumed + 1))
                        if not block:
                            break
                        consumed += len(block)
                        if consumed > signature[3]:
                            raise _InventoryChanged('A server file grew while hashing')
                        hashed.update(block)
                    finished = os.fstat(stream.fileno())
                    if (consumed != signature[3] or _file_signature(finished) != signature
                            or opened.st_ctime_ns != finished.st_ctime_ns):
                        raise _InventoryChanged('A server file changed while hashing')
                    if hashed.hexdigest() != expected_hash:
                        errors.append('Missing or modified server file: ' + name)
            except FileNotFoundError:
                raise _InventoryChanged('A server file disappeared while hashing')
        return errors

    def _run(self):
        while True:
            with self._condition:
                self._condition.wait_for(lambda: self._stop.is_set() or self._pending is not None)
                if self._stop.is_set():
                    return
                snapshot, self._pending = self._pending, None
                self._busy = True
                self._attempt_signature = snapshot['signature']
            result, error = None, None
            try:
                if self.capture()['signature'] != snapshot['signature']:
                    raise _InventoryChanged('Inventory changed before the background check')
                started = time.monotonic()
                errors = self._verify(snapshot)
                if self.capture()['signature'] != snapshot['signature']:
                    raise _InventoryChanged('Inventory changed during the background check; result discarded')
                result = {'signature': snapshot['signature'], 'at': utcnow(),
                          'monotonic': self.clock(), 'errors': list(errors),
                          'duration_ms': round((time.monotonic() - started) * 1000, 3),
                          'provenance': deepcopy(snapshot['provenance'])}
            except Exception as exc:
                error = (type(exc).__name__ + ': ' + str(exc))[:300]
            with self._condition:
                self._attempt_finished_at = self.clock()
                self._attempt_finished_utc = utcnow()
                if not self._stop.is_set():
                    if result is not None:
                        self._result = result
                    self._error = error
                self._busy = False
                self._condition.notify_all()

    def view(self, snapshot=None, error=None):
        with self._condition:
            now, result = self.clock(), self._result
            age = max(0, now - result['monotonic']) if result else None
            fresh = bool(not self._stop.is_set() and not error and not self._error and result
                         and snapshot and result['signature'] == snapshot['signature']
                         and age < SYNC_TTL_SECONDS)
            # One outstanding request, no queue or per-poll thread creation.
            if (not fresh and not error and snapshot and not self._stop.is_set()
                    and not self._busy and self._pending is None
                    and (self._attempt_signature != snapshot['signature']
                         or now - self._attempt_finished_at >= SYNC_TTL_SECONDS)):
                self._pending = snapshot
                if self._worker is None:
                    self._worker = threading.Thread(target=self._run, daemon=True, name='awft-overview-integrity')
                    self._worker.start()
                self._condition.notify_all()
            checking = self._busy or self._pending is not None
            status = ('closed' if self._stop.is_set() else
                      'verified' if fresh and not result['errors'] else 'differs' if fresh else
                      'error' if error else 'checking' if checking else 'error' if self._error else
                      'stale' if result else 'unknown')
            detail = {'status': status, 'current': fresh, 'checking': checking,
                      'last_verified_at': result['at'] if result else None,
                      'age_seconds': round(age, 3) if age is not None else None,
                      'ttl_seconds': SYNC_TTL_SECONDS,
                      'last_verified_status': ('differs' if result['errors'] else 'matches') if result else None,
                      'last_verified_provenance': deepcopy(result['provenance']) if result else None,
                      'last_scan_duration_ms': result['duration_ms'] if result else None,
                      'last_attempt_finished_at': self._attempt_finished_utc,
                      'retry_after_seconds': round(max(0, SYNC_TTL_SECONDS - (now - self._attempt_finished_at)), 3)
                      if self._error and snapshot and self._attempt_signature == snapshot['signature'] and not checking else None,
                      'current_inventory_signature': snapshot['signature'] if snapshot else None,
                      'errors': list(result['errors']) if fresh else [],
                      'error': error or self._error,
                      'scope': 'Read-only background observation for overview; never a startup, deployment or acceptance gate.'}
            return {'server': ('matches' if not result['errors'] else 'not installed or differs') if fresh else
                    ('checking; current integrity unknown' if checking else 'current integrity unknown'),
                    'server_integrity': detail}

    def close(self):
        self._stop.set()
        with self._condition:
            self._pending = None
            self._condition.notify_all()
            worker = self._worker
        if worker is not None:
            worker.join(timeout=5)
        # Keep the owned thread handle if an OS read is still returning. It cannot
        # admit another scan or publish a result, and checks stop between 1 MiB reads.
        return worker is None or not worker.is_alive()


class ModManager:
    def __init__(self, layout, storage, server, backups):
        self.layout, self.storage, self.server, self.backups = layout, storage, server, backups
        self._overview_integrity = _OverviewIntegrity(layout, self._overview_snapshot)

    def close(self):
        return self._overview_integrity.close()

    def _overview_snapshot(self):
        """Cheap identity: small receipt/manifest bytes and bounded JAR stats only."""
        lock, source = self.active()
        pack = _small_bytes(source / 'pack.toml')
        raw = _small_bytes(self.layout.server / 'installed.json', missing=True)
        receipt = json.loads(raw) if raw else {}
        if not isinstance(receipt, dict):
            raise ValueError('Server receipt must be an object')
        expected = receipt.get('files', {})
        if not isinstance(expected, dict) or len(expected) > SYNC_MAX_FILES:
            raise ValueError('Server receipt exceeds the bounded inventory')
        for name, value in expected.items():
            if (not isinstance(name, str) or Path(name).name != name or '/' in name or '\\' in name or ':' in name
                    or not name.lower().endswith('.jar') or not isinstance(value, str)
                    or not re.fullmatch(r'[a-f0-9]{64}', value)):
                raise ValueError('Server receipt has an invalid filename or SHA-256')
        directory = self.layout.server / 'mods'
        if directory.is_symlink() or directory.is_junction():
            raise ValueError('Linked mod directories cannot qualify an overview integrity observation')
        before = _file_signature(directory.stat()) if directory.exists() else None
        actual = set()
        for path in directory.glob('*.jar'):
            actual.add(path.name)
            if len(actual) > SYNC_MAX_FILES:
                raise ValueError('Installed server inventory exceeds 1024 files')
        if len(actual | set(expected)) > SYNC_MAX_FILES:
            raise ValueError('Combined expected/observed inventory exceeds 1024 files')
        files, total = {}, 0
        for name in sorted(actual | set(expected)):
            try:
                info = (directory / name).lstat()
            except FileNotFoundError:
                files[name] = None
                continue
            if stat.S_ISLNK(info.st_mode):
                raise ValueError('Linked JARs cannot qualify an overview integrity observation')
            files[name] = _file_signature(info)
            total += info.st_size
            if total > SYNC_MAX_BYTES:
                raise ValueError('Installed server inventory exceeds the 2 GiB overview scan bound')
        after = _file_signature(directory.stat()) if directory.exists() else None
        if before != after:
            raise _InventoryChanged('Server inventory changed during metadata inspection')
        sha = hashlib.sha256(pack).hexdigest()
        receipt_sha = hashlib.sha256(raw).hexdigest() if raw else None
        identity = [str(source), lock['version'], sha, receipt_sha, before, files, sorted(actual)]
        signature = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
        return {'version': lock['version'], 'pack_sha256': sha, 'receipt_present': bool(receipt),
                'receipt_pack_sha256': receipt.get('pack_sha256'), 'expected': expected, 'files': files,
                'private_overlay': receipt.get('private_overlay'),
                'actual': actual, 'signature': signature,
                'provenance': {'pack_version': lock['version'], 'pack_sha256': sha,
                               'installed_receipt_sha256': receipt_sha, 'inventory_signature': signature,
                               'expected_files': len(expected), 'observed_files': len(actual),
                               'observed_bytes': total, 'hash_algorithm': 'sha256',
                               'basis': 'Exact installed receipt and active manifest bytes; filenames, file identity, size and file time metadata before/after all expected JAR hashes; same-handle change time checked while reading.'}}

    def overview_sync(self):
        """Fast display only. Explicit sync/health and operation gates stay strict."""
        try:
            snapshot = self._overview_snapshot()
        except (OSError, ValueError, TypeError, KeyError, _InventoryChanged) as exc:
            return self._sync_summary(None, None) | self._overview_integrity.view(error=str(exc)[:300])
        return self._private_overlay_sync(
            self._sync_summary(snapshot['version'], snapshot['pack_sha256'])
            | self._overview_integrity.view(snapshot), snapshot['private_overlay'])

    def active(self):
        active = read_json(self.layout.home / "packwiz/active.json")
        if active:
            release = contained(self.layout.releases, active["version"])
            return read_json(release / "lock.json"), release
        return read_json(REPO / "catalog/lock.json"), REPO / "packwiz"

    def inventory(self):
        lock, _ = self.active()
        return {"version": lock["version"], "mods": lock["mods"],
                "candidate_version": read_json(REPO / "catalog/lock.json")["version"],
                "candidate": read_json(REPO / "catalog/lock.json"),
                "update_policy": "Updates are queried on demand, selected by exact version and staged for review. Never silently update content."}

    def manual_files(self):
        # Include the current source candidate while an older qualified release is active.
        lock = read_json(REPO / "catalog/lock.json")
        return [{"slug": m["slug"], "name": m["name"], "version": m["version"], "filename": m["filename"],
                 "source": m["source"], "cached": (self.layout.caches / "mods" / m["filename"]).is_file(),
                 "license": m["license"], "size": m["size"]} for m in lock["mods"] if m.get("provider") == "curseforge"]

    def import_manual(self, slug, notify=lambda _: None):
        lock = read_json(REPO / "catalog/lock.json")
        item = next((m for m in lock["mods"] if m["slug"] == slug and m.get("provider") == "curseforge"), None)
        if not item:
            raise UserError("Choose an exact pinned manual download")
        filename = item["filename"]
        if Path(filename).name != filename or not filename.endswith(".jar"):
            raise UserError("Invalid pinned filename")
        source = Path.home() / "Downloads" / filename
        algorithm = "sha512" if "sha512" in item["hashes"] else "sha256"
        if not source.is_file() or source.is_symlink() or source.stat().st_size != item["size"] or digest(source, algorithm) != item["hashes"][algorithm]:
            raise UserError("The exact pinned file was not found in Downloads, or its size/hash differs. Download it from the displayed author page first.")
        with self.layout.mutation:
            self.storage.reserve(item["size"])
            target = self.layout.caches / "mods" / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and digest(target, algorithm) != item["hashes"][algorithm]:
                raise UserError("A different cached file is preserved; inspect it before importing")
            if not target.exists():
                shutil.copy2(source, target)
            notify("Verified " + item["name"] + "; imported to the candidate cache")
        return {"name": item["name"], "sha256": digest(target), "state": "cached candidate; active server unchanged"}

    def search(self, query):
        if not isinstance(query, str) or not 1 <= len(query) <= 100:
            raise UserError("Enter 1 to 100 characters")
        if "://" in query:
            project = resolve_project(query)
            return {"hits": [{"project_id": project["id"], "slug": project["slug"], "title": project["title"], "description": project["description"]}]}
        facets = [["versions:1.21.1"], ["categories:neoforge"], ["project_type:mod"]]
        return api("/search", {"query": query, "limit": 20, "facets": json.dumps(facets)})

    def versions(self, project):
        project = resolve_project(project)
        versions = api("/project/" + project["id"] + "/version", {"game_versions": json.dumps(["1.21.1"]), "loaders": json.dumps(["neoforge"])})
        return {"project": {key: project[key] for key in ["id", "slug", "title", "description", "client_side", "server_side", "license"]},
                "versions": [{key: v[key] for key in ["id", "version_number", "version_type", "date_published", "dependencies"]} for v in versions]}

    def curseforge(self, project_id):
        # A key is supplied through the hosting process environment, never browser input,
        # URLs, the repository, log bundles or source-control history.
        key = os.environ.get("AWFT_CURSEFORGE_API_KEY")
        if not key:
            raise UserError("CurseForge lookup requires an authorized API key in AWFT_CURSEFORGE_API_KEY. Use an official project URL and manual authorized download otherwise; no restriction bypass is attempted.")
        if not str(project_id).isdigit():
            raise UserError("Enter the numeric CurseForge project ID")
        request = urllib.request.Request("https://api.curseforge.com/v1/mods/" + str(project_id), headers={"x-api-key": key})
        with urllib.request.urlopen(request, timeout=15) as response:
            project = json.loads(response.read(2 * 1024 * 1024))["data"]
        return {"id": project["id"], "name": project["name"], "links": project["links"],
                "allowModDistribution": project.get("allowModDistribution"),
                "note": "CurseForge files require their own authorized metadata/distribution review; project lookup does not authorize republishing JARs."}

    def proposals(self):
        return [read_json(p) for p in sorted((self.layout.staging / "proposals").glob("*/proposal.json"), reverse=True)][-30:]

    def proposal_path(self, ident):
        if not re.fullmatch(r"[a-f0-9]{32}", ident):
            raise UserError("Invalid proposal ID")
        return contained(self.layout.staging / "proposals", ident)

    def propose(self, action, project, version=None, allow_prerelease=False, notify=lambda _: None):
        if action not in ("add", "remove", "update"):
            raise UserError("Choose add, remove or update")
        with self.layout.mutation:
            lock, source = self.active()
            resolver = Resolver(REPO / "evidence/research")
            identity = resolver.project(project)
            existing = next((m for m in lock["mods"] if m["project_id"] == identity["id"]), None)
            if action == "add" and existing:
                raise UserError("This project is already installed; choose a version update")
            if action in ("remove", "update") and not existing:
                raise UserError("This project is not installed")
            candidate = deepcopy(lock)
            if action == "remove":
                candidate["mods"] = [m for m in candidate["mods"] if m["project_id"] != identity["id"]]
            else:
                if not version:
                    raise UserError("Choose an exact compatible version before staging")
                choice = {"project": identity["id"], "version": version,
                          "allow_prerelease": allow_prerelease, "reason": "Owner-selected exact version staged through Control Room"}
                if existing:
                    for field in ("side", "kind", "request", "optional", "default", "world_sensitive"):
                        choice[field] = existing[field]
                candidate["mods"] = resolver.resolve([choice], baseline=lock["mods"])
            errors = validate_graph(candidate["mods"])
            if errors:
                raise UserError("Dependency/conflict check failed: " + "; ".join(errors))
            ident = uuid.uuid4().hex
            # A release ID is immutable, unique and shared by pack, server and exports.
            candidate["version"] = lock["version"].split("+", 1)[0] + "+r" + ident[:10]
            candidate["generated"] = utcnow()
            candidate["release_status"] = "candidate"
            directory = self.proposal_path(ident)
            self.storage.reserve(sum(m["size"] for m in candidate["mods"]) + 4 * 1024 * 1024)
            pack = directory / "packwiz"
            for group in ("config", "defaultconfigs"):
                if (source / group).exists():
                    shutil.copytree(source / group, pack / group)
            pack_hash = generate_pack(pack, candidate)
            write_json(directory / "lock.json", candidate)
            notify("Staged manifest; downloading only missing pinned files for static verification")
            cache_files(candidate, self.layout.caches / "mods", self.storage, notify)
            report = validate_jars(candidate, self.layout.caches / "mods")
            write_json(directory / "jar-validation.json", report)
            before, after = {m["project_id"]: m for m in lock["mods"]}, {m["project_id"]: m for m in candidate["mods"]}
            changes = []
            for pid in sorted(set(before) | set(after)):
                old, new = before.get(pid), after.get(pid)
                if old and new and old["version_id"] == new["version_id"]:
                    continue
                item = new or old
                changes.append({"name": item["name"], "project_id": pid, "from": old and old["version"],
                                "to": new and new["version"], "side": item["side"], "world_sensitive": item["world_sensitive"]})
            if not changes:
                raise UserError("The selected exact version is already installed")
            proposal = {"id": ident, "created": utcnow(), "action": action, "base_version": lock["version"],
                        "base_pack_sha256": digest(source / "pack.toml"), "version": candidate["version"],
                        "pack_sha256": pack_hash, "changes": changes, "static_errors": report["errors"],
                        "static_warnings": report["warnings"], "status": "ready for review" if not report["errors"] else "blocked by static validation",
                        "runtime": "not validated", "restart_required": any(c["side"] in ("both", "server") for c in changes),
                        "client_relaunch_required": True,
                        "warning": "Content removal or world-generation changes can permanently affect saved worlds. Production deployment requires an exact-candidate acceptance receipt, a verified backup, and published matching client manifests."}
            write_json(directory / "proposal.json", proposal)
            return proposal

    def export_proposal(self, ident):
        directory = self.proposal_path(ident)
        proposal = read_json(directory / "proposal.json")
        if not proposal:
            raise UserError("Proposal not found")
        return directory, proposal

    def deploy(self, ident, confirmation, publication_url, notify=lambda _: None):
        with self.layout.mutation:
            directory, proposal = self.export_proposal(ident)
            if confirmation != "DEPLOY " + proposal["version"]:
                raise UserError("Type DEPLOY and the complete release version after reviewing the proposal")
            if proposal["static_errors"]:
                raise UserError("Fix all static validation errors before deployment")
            lock, current = self.active()
            if digest(current / "pack.toml") != proposal["base_pack_sha256"]:
                raise UserError("Active manifest changed; create a fresh proposal")
            candidate = read_json(directory / "lock.json")
            errors = validate_pack(directory / "packwiz", candidate)
            if errors:
                raise UserError("Staged manifest failed integrity verification")
            receipt = read_json(directory / "acceptance.json", {})
            required = {"dedicated_startup", "client_startup", "two_player_sync", "backup_restore", "feature_smoke"}
            if receipt.get("pack_sha256") != proposal["pack_sha256"] or not all(receipt.get("checks", {}).get(k) == "pass" for k in required):
                raise UserError("This exact candidate still needs the documented runtime acceptance tests. Export the proposal for a test instance; no production files were changed.")
            expected_prefix = "https://kgray44.github.io/a-world-for-two/releases/" + proposal["version"] + "/"
            if publication_url != expected_prefix + "pack.toml":
                raise UserError("Publish the verified immutable client release first, then supply its exact GitHub Pages pack.toml URL")
            with urllib.request.urlopen(publication_url, timeout=20) as response:
                raw = response.read(1024 * 1024)
            import hashlib
            if hashlib.sha256(raw).hexdigest() != proposal["pack_sha256"]:
                raise UserError("Published client manifest differs from the approved server candidate")
            was_running = self.server.running()
            if was_running:
                self.server.stop(notify=notify)
            if any(self.layout.world.rglob("level.dat")):
                self.backups.create(reason="before-deploy", resume=False, notify=notify)
            self.storage.reserve(sum(m["size"] for m in candidate["mods"]) + 8 * 1024 * 1024)
            release = self.layout.releases / proposal["version"]
            if release.exists():
                raise UserError("This immutable release ID already exists")
            shutil.copytree(directory / "packwiz", release)
            write_json(release / "lock.json", candidate)
            staged_mods = directory / "server-mods"
            staged_mods.mkdir()
            files = {}
            for item in candidate["mods"]:
                if item["side"] not in ("both", "server") or item["kind"] != "mod" or item.get("optional") and not item.get("default", True):
                    continue
                shutil.copy2(self.layout.caches / "mods" / item["filename"], staged_mods / item["filename"])
                files[item["filename"]] = digest(staged_mods / item["filename"])
            rollback = directory / "previous"
            rollback.mkdir()
            prior_receipt = self.layout.server / "installed.json"
            if prior_receipt.exists():
                shutil.copy2(prior_receipt, rollback / "installed.json")
            shutil.copy2(self.layout.home / "packwiz/active.json", rollback / "active.json")
            old_mods = self.layout.server / "mods"
            os.replace(old_mods, rollback / "mods")
            try:
                os.replace(staged_mods, old_mods)
                write_json(prior_receipt, {"pack_version": candidate["version"], "pack_sha256": proposal["pack_sha256"],
                    "neoforge": candidate["neoforge"], "at": utcnow(), "files": files, "acceptance": receipt})
                write_json(self.layout.home / "packwiz/active.json", {"version": candidate["version"],
                    "pack_sha256": proposal["pack_sha256"], "publication": publication_url,
                    "client_relaunch_required": True, "at": utcnow()})
            except Exception:
                if old_mods.exists():
                    os.replace(old_mods, directory / "failed-new-mods")
                os.replace(rollback / "mods", old_mods)
                for source, target in [(rollback / "installed.json", prior_receipt), (rollback / "active.json", self.layout.home / "packwiz/active.json")]:
                    if source.exists():
                        shutil.copy2(source, target)
                raise
            proposal["status"] = "deployed"
            write_json(directory / "proposal.json", proposal)
            notify("Release activated atomically; both clients must relaunch before reconnecting")
            # Deliberately leave Minecraft offline until clients can relaunch against the release.
            return {"deployed": candidate["version"], "restart_required": True, "client_relaunch_required": True}

    def rollback(self, ident, confirmation, notify=lambda _: None):
        with self.layout.mutation:
            directory, proposal = self.export_proposal(ident)
            if confirmation != "ROLLBACK " + proposal["version"]:
                raise UserError("Type ROLLBACK and the release version to approve")
            if self.server.running():
                raise UserError("Stop the server before rolling back")
            active = read_json(self.layout.home / "packwiz/active.json", {})
            if active.get("version") != proposal["version"]:
                raise UserError("Only the currently active deployment can be rolled back")
            previous = directory / "previous"
            if not (previous / "mods").exists():
                raise UserError("The previous release's server files are not available")
            if any(self.layout.world.rglob("level.dat")):
                self.backups.create(reason="before-rollback", resume=False, notify=notify)
            safety = directory / ("rolled-back-new-" + uuid.uuid4().hex[:6])
            os.replace(self.layout.server / "mods", safety)
            try:
                os.replace(previous / "mods", self.layout.server / "mods")
                shutil.copy2(previous / "installed.json", self.layout.server / "installed.json")
                shutil.copy2(previous / "active.json", self.layout.home / "packwiz/active.json")
            except Exception:
                if not (self.layout.server / "mods").exists():
                    os.replace(safety, self.layout.server / "mods")
                raise
            proposal["status"] = "rolled back"
            write_json(directory / "proposal.json", proposal)
            return {"version": proposal["base_version"], "client_relaunch_required": True,
                    "warning": "Publish the previous current pointer before players relaunch. World rollback is separate and explicit; new content may require restoring its pre-deploy backup."}

    def _sync_summary(self, version, sha):
        reports = read_json(self.layout.state / "client-reports.json", {})
        players = {}
        for name in ("KG", "Sera"):
            report = reports.get(name)
            players[name] = {"state": "unknown", "message": "No current client receipt has been imported"}
            if report:
                matched = sha is not None and report.get("pack_sha256") == sha and report.get("jar_integrity") == "pass"
                players[name] = {"state": "reported match" if matched else "relaunch required", "reported_at": report.get("at"),
                                 "message": "Local client file inspection receipt; this is not proof of a live multiplayer connection"}
        return {"version": version, "pack_sha256": sha,
                "players": players, "pending": any(p["status"] == "ready for review" for p in self.proposals()),
                "relaunch_required": any(p["state"] != "reported match" for p in players.values())}

    @staticmethod
    def _private_overlay_sync(result, declaration):
        """A baseline client receipt cannot qualify additional private runtime files."""
        if declaration is None:
            return result
        overlay = declaration if isinstance(declaration, dict) else {}
        name = overlay.get('name')
        name = name if isinstance(name, str) and 0 < len(name) <= 160 else 'Private runtime overlay'
        mods = overlay.get('new_server_and_client_mods', [])
        mods = [filename for filename in mods if isinstance(filename, str)
                and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.+ -]{0,199}\.jar', filename)] \
            if isinstance(mods, list) and len(mods) <= SYNC_MAX_FILES else []
        accepted = overlay.get('runtime_accepted') is True
        qualification = 'reported accepted; client verification required' if accepted else 'pending runtime qualification'
        message = (name + ': install its matching private client mods and relaunch. '
                   'The baseline pack receipt does not verify this overlay. ' + qualification.capitalize() + '.')
        result['private_overlay'] = {
            'name': name, 'base_candidate': overlay.get('base_candidate', result['version']),
            'new_server_and_client_mods': mods, 'required': True,
            'runtime_accepted': accepted,
            'public_pack_published': overlay.get('public_pack_published') is True,
            'qualification': qualification, 'client_verification': 'Overlay-specific verification required',
        }
        result['relaunch_required'] = True
        for player in result['players'].values():
            player['baseline_state'] = player['state']
            player['state'] = 'private overlay required'
            player['message'] = message
        if result.get('server') == 'matches':
            result['server'] = ('private overlay installed; client verification required' if accepted
                                else 'private overlay installed; qualification pending')
        if 'server_integrity' in result:
            result['server_integrity']['receipt_scope'] = 'Installed receipt including the declared private overlay'
            result['server_integrity']['published_client_pack_match'] = False
        return result

    def sync(self):
        # Deliberately remain synchronous and uncached for explicit checks.
        lock, source = self.active()
        sha = digest(source / 'pack.toml')
        installed = read_json(self.layout.server / 'installed.json')
        return self._private_overlay_sync(self._sync_summary(lock['version'], sha) | {
            'server': 'matches' if installed and installed.get('pack_sha256') == sha
            and not verify_installed(self.layout) else 'not installed or differs'},
            installed.get('private_overlay') if installed else None)

    def import_client_report(self, player, report):
        if player not in ("KG", "Sera") or not isinstance(report, dict):
            raise UserError("Choose KG or Sera and supply a client inspection receipt")
        if report.get("format") != "awft-client-receipt:1" or report.get("jar_integrity") != "pass" or not re.fullmatch(r"[a-f0-9]{64}", report.get("pack_sha256", "")):
            raise UserError("Client receipt is missing a successful file integrity result")
        with self.layout.mutation:
            self.storage.reserve(65536)
            reports = read_json(self.layout.state / "client-reports.json", {})
            reports[player] = {k: report[k] for k in ("format", "jar_integrity", "pack_sha256", "at")}
            write_json(self.layout.state / "client-reports.json", reports)
        return self.sync()
