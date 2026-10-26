from __future__ import annotations

import json
import os
import re
import shutil
import urllib.request
import uuid
from copy import deepcopy
from pathlib import Path

from .common import REPO, UserError, contained, digest, read_json, utcnow, write_json
from .network import api
from .pack import Resolver, cache_files, generate_pack, resolve_project, validate_graph, validate_jars, validate_pack, verify_installed


class ModManager:
    def __init__(self, layout, storage, server, backups):
        self.layout, self.storage, self.server, self.backups = layout, storage, server, backups

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

    def sync(self):
        lock, source = self.active()
        sha = digest(source / "pack.toml")
        installed = read_json(self.layout.server / "installed.json")
        reports = read_json(self.layout.state / "client-reports.json", {})
        players = {}
        for name in ("KG", "Sera"):
            report = reports.get(name)
            players[name] = {"state": "unknown", "message": "No current client receipt has been imported"}
            if report:
                matched = report.get("pack_sha256") == sha and report.get("jar_integrity") == "pass"
                players[name] = {"state": "reported match" if matched else "relaunch required", "reported_at": report.get("at"),
                                 "message": "Local client file inspection receipt; this is not proof of a live multiplayer connection"}
        return {"version": lock["version"], "pack_sha256": sha,
                "server": "matches" if installed and installed.get("pack_sha256") == sha and not verify_installed(self.layout) else "not installed or differs",
                "players": players, "pending": any(p["status"] == "ready for review" for p in self.proposals()),
                "relaunch_required": any(p["state"] != "reported match" for p in players.values())}

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
