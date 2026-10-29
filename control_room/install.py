from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

from .common import GiB, REPO, UserError, atomic_write, digest, read_json, utcnow, write_json
from .network import download
from .pack import cache_files, generate_pack, validate_jars, validate_pack, verify_installed


class Installer:
    def __init__(self, layout, storage, server, settings):
        self.layout, self.storage, self.server, self.settings = layout, storage, server, settings

    def preflight(self):
        java = shutil.which(self.layout.settings()["java"])
        version = None
        if java:
            result = subprocess.run([java, "-version"], capture_output=True, text=True, timeout=10,
                                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            version = (result.stderr + result.stdout).splitlines()[0]
        return {"java": java, "java_version": version, "java_21": bool(version and re.search(r'version "21[.\"]', version)),
                "home": str(self.layout.home), "installed": read_json(self.layout.server / "installed.json"),
                "eula_accepted": self.eula_accepted(), "players": self.layout.settings()["player_names"],
                "disk": self.storage.snapshot(), "eula_url": "https://aka.ms/MinecraftEULA"}

    def eula_accepted(self):
        from .settings import properties
        path = self.layout.server / "eula.txt"
        return path.exists() and properties(path.read_text()).get("eula") == "true"

    def accept_eula(self, accepted):
        if accepted is not True:
            raise UserError("Explicit EULA acceptance is required")
        with self.layout.mutation:
            self.storage.reserve(8192)
            atomic_write(self.layout.server / "eula.txt", "# Accepted explicitly through Control Room at " + utcnow() + "\n# https://aka.ms/MinecraftEULA\neula=true\n")
            write_json(self.layout.state / "eula-acceptance.json", {"accepted": True, "at": utcnow(), "source": "explicit owner action", "url": "https://aka.ms/MinecraftEULA"})
        return {"accepted": True}

    def players(self, names):
        if not isinstance(names, dict) or set(names) != {"KG", "Sera"}:
            raise UserError("Supply the Minecraft Java usernames for KG and Sera")
        entries = []
        for label, name in names.items():
            if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_]{1,16}", name):
                raise UserError(label + ": enter the Minecraft Java profile name")
            request = urllib.request.Request("https://api.mojang.com/users/profiles/minecraft/" + name,
                                             headers={"User-Agent": "a-world-for-two/0.1"})
            try:
                with urllib.request.urlopen(request, timeout=15) as response:
                    profile = json.loads(response.read(4096))
                ident = profile["id"]
                if not re.fullmatch(r"[a-fA-F0-9]{32}", ident):
                    raise ValueError("Invalid Mojang profile ID")
                uuid = "-".join([ident[:8], ident[8:12], ident[12:16], ident[16:20], ident[20:]])
                entries.append({"uuid": uuid, "name": profile["name"]})
            except Exception as exc:
                raise UserError("Could not verify the online Minecraft profile for " + label) from exc
        if entries[0]["uuid"] == entries[1]["uuid"]:
            raise UserError("KG and Sera must use separate authenticated Minecraft profiles")
        with self.layout.mutation:
            if self.server.running():
                raise UserError("Stop the server before replacing its initial whitelist")
            path = self.layout.server / "whitelist.json"
            previous = read_json(path, [])
            if previous and previous != entries:
                self.settings.snapshot(path)
            self.storage.reserve(16384)
            write_json(path, entries)
            options = self.layout.settings()
            options["player_names"] = names
            self.layout.save_settings(options)
        return {"whitelisted": entries}

    def install(self, notify=lambda _: None, pack_source=None):
        with self.layout.mutation:
            if self.server.running():
                raise UserError("Stop the server before installing or repairing")
            preflight = self.preflight()
            if not preflight["java_21"]:
                raise UserError("Install Java 21 before installing NeoForge")
            lock = read_json((pack_source or REPO) / "catalog/lock.json")
            source = (pack_source or REPO) / "packwiz"
            errors = validate_pack(source, lock)
            if errors:
                raise UserError("Pack validation failed: " + "; ".join(errors))
            if (self.layout.server / "installed.json").exists():
                raise UserError("An installation already exists; use Repair or the staged mod deployment workflow")
            # <= 2 GiB for NeoForge's dependencies and installer scratch space, plus
            # exactly sized pinned JARs. A watcher safely interrupts an oversized installer.
            self.storage.reserve(2 * GiB + sum(m["size"] for m in lock["mods"]))
            self.layout.create()
            self.settings.initialize()
            cache_files(lock, self.layout.caches / "mods", self.storage, notify)
            report = validate_jars(lock, self.layout.caches / "mods")
            write_json(self.layout.logs / "installation-jar-validation.json", report)
            if report["errors"]:
                raise UserError("JAR dependency check failed: " + "; ".join(report["errors"][:8]))
            self.install_neoforge(lock["neoforge"], notify)
            release = self.layout.releases / lock["version"]
            if release.exists():
                if digest(release / "pack.toml") != digest(source / "pack.toml"):
                    raise UserError("Immutable release version already contains different bytes")
            else:
                shutil.copytree(source, release)
                write_json(release / "lock.json", lock)
            self.install_mods(lock, source, notify)
            return {"installed": True, "pack": lock["version"], "neoforge": lock["neoforge"],
                    "runtime": "not yet started", "next": "Accept the EULA, verify both player names, then start the server."}

    def install_neoforge(self, version, notify=lambda _: None):
        args = self.layout.server / "libraries/net/neoforged/neoforge" / version / ("win_args.txt" if os.name == "nt" else "unix_args.txt")
        if args.exists():
            return
        pins = read_json(REPO / "catalog/tools.lock.json")
        tool = pins.get("neoforge_installers", {}).get(version) or pins["neoforge_installer"]
        if version != tool["version"]:
            raise UserError("This NeoForge version has no reviewed installer pin")
        installer = self.layout.caches / tool["filename"]
        if not installer.exists():
            download(tool["url"], installer, tool["size"], tool["hashes"]["sha256"], "sha256", self.storage, notify)
        elif digest(installer) != tool["hashes"]["sha256"]:
            raise UserError("NeoForge installer hash differs from the pinned artifact")
        self.storage.reserve(2 * GiB)
        from .storage import tree_size
        before = tree_size(self.layout.server)
        command = [self.layout.settings()["java"], "-Djava.io.tmpdir=" + str(self.layout.staging), "-jar", str(installer), "--installServer", str(self.layout.server)]
        log = self.layout.logs / ("neoforge-install-" + str(time.time_ns()) + ".log")
        with log.open("x", encoding="utf-8") as stream:
            process = subprocess.Popen(command, cwd=self.layout.server, stdout=stream, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            deadline = time.monotonic() + 600
            while process.poll() is None:
                if time.monotonic() > deadline or tree_size(self.layout.server) - before > 2 * GiB:
                    process.terminate()  # Installer owns no world; preserve its partial library files/log.
                    process.wait(timeout=30)
                    raise UserError("NeoForge installer exceeded its time or disk allocation; installation log preserved")
                try:
                    self.storage.checkpoint(2 * GiB)
                except Exception:
                    process.terminate()
                    process.wait(timeout=30)
                    raise
                time.sleep(1)
        if process.returncode or not args.exists():
            raise UserError("NeoForge installation failed; inspect " + str(log))
        notify("NeoForge " + version + " installed; Minecraft has not been started")

    def install_mods(self, lock, source, notify=lambda _: None):
        mods = self.layout.server / "mods"
        if mods.exists() and any(mods.iterdir()):
            raise UserError("Existing server mods need the staged deployment workflow")
        mods.mkdir(exist_ok=True)
        files = {}
        for item in lock["mods"]:
            if item["side"] not in ("both", "server") or item["kind"] == "shader" or item.get("optional") and not item.get("default", True):
                continue
            cached = self.layout.caches / "mods" / item["filename"]
            shutil.copy2(cached, mods / item["filename"])
            files[item["filename"]] = digest(mods / item["filename"])
        for group in ("config", "defaultconfigs"):
            if (source / group).exists():
                for path in (source / group).rglob("*"):
                    if path.is_file():
                        target = self.layout.server / path.relative_to(source)
                        if not target.exists():
                            target.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(path, target)
        pack_hash = digest(source / "pack.toml")
        receipt = {"pack_version": lock["version"], "pack_sha256": pack_hash, "neoforge": lock["neoforge"],
                   "at": utcnow(), "files": files, "validation": "static dependency metadata passed; runtime pending"}
        write_json(self.layout.server / "installed.json", receipt)
        write_json(self.layout.home / "packwiz/active.json", {"version": lock["version"], "pack_sha256": pack_hash,
                   "at": utcnow(), "client_relaunch_required": True, "publication": "local candidate only"})
        notify(str(len(files)) + " server-side JARs installed; client-only files were excluded")

    def repair(self, notify=lambda _: None):
        with self.layout.mutation:
            if self.server.running():
                raise UserError("Stop the server before repair")
            active = read_json(self.layout.home / "packwiz/active.json", {})
            release = self.layout.releases / active.get("version", "missing")
            lock = read_json(release / "lock.json")
            if not lock:
                raise UserError("No installed immutable release is available for repair")
            errors = validate_pack(release, lock)
            if errors:
                raise UserError("Release metadata itself needs recovery: " + "; ".join(errors))
            cache_files(lock, self.layout.caches / "mods", self.storage, notify)
            self.install_neoforge(lock["neoforge"], notify)
            expected = {m["filename"]: m for m in lock["mods"] if m["side"] in ("both", "server") and m["kind"] == "mod" and not (m.get("optional") and not m.get("default", True))}
            self.storage.reserve(sum(m["size"] for m in expected.values()))
            quarantine = self.layout.staging / ("repair-preserved-" + str(time.time_ns()))
            quarantine.mkdir()
            for path in (self.layout.server / "mods").glob("*.jar"):
                if path.name not in expected:
                    os.replace(path, quarantine / path.name)
            for name, item in expected.items():
                target = self.layout.server / "mods" / name
                cached = self.layout.caches / "mods" / name
                if not target.exists() or digest(target) != digest(cached):
                    if target.exists():
                        os.replace(target, quarantine / name)
                    shutil.copy2(cached, target)
            return {"problems": verify_installed(self.layout), "preserved": str(quarantine)}
