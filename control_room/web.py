from __future__ import annotations

import contextlib
import hmac
import io
import json
import mimetypes
import os
import secrets
import shutil
import socket
import subprocess
import threading
import urllib.error
import urllib.parse
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import psutil

from . import __version__
from .backups import Backups
from .common import REPO, Layout, UserError, contained, digest, read_json, utcnow, write_json
from .install import Installer
from .jobs import Jobs
from .metrics import Metrics
from .mod_manager import ModManager
from .pack import validate_pack, verify_installed
from .players import Players, profile
from .server import Server
from .settings import Settings
from .storage import Storage


class Application:
    def __init__(self, home):
        self.layout = Layout(home)
        self.storage = Storage(self.layout)
        self.storage.reserve(80 * 1024 * 1024)
        self.layout.create()
        self.server = Server(self.layout, self.storage)
        self.settings = Settings(self.layout, self.storage, self.server)
        self.settings.initialize()
        self.jobs = Jobs()
        self.metrics = Metrics(self.layout, self.storage, self.server)
        self.backups = Backups(self.layout, self.storage, self.server)
        self.mods = ModManager(self.layout, self.storage, self.server, self.backups)
        self.installer = Installer(self.layout, self.storage, self.server, self.settings)
        self.players = Players(self.layout, self.storage, self.server, self.settings)
        self.token = secrets.token_urlsafe(32)

    def start(self):
        self.metrics.start()
        self.backups.start_schedule()

    def close(self):
        self.backups.close()
        self.metrics.close()
        self.jobs.close()
        # Closing a dashboard never silently kills or abandons a writing world.
        if self.server.running():
            self.server.stop()

    def health(self, notify=lambda _: None):
        lock, source = self.mods.active()
        return {"at": utcnow(), "pack_errors": validate_pack(source, lock),
                "server_errors": verify_installed(self.layout), "storage": self.storage.snapshot(),
                "java": self.installer.preflight()["java_version"], "eula": self.installer.eula_accepted(),
                "runtime": self.server.snapshot(), "sync": self.mods.sync(),
                "warning": "A health check is not a multiplayer, graphics or feature acceptance test."}

    def overview(self):
        lock, _ = self.mods.active()
        history = self.backups.list()
        props = self.settings.get_properties()
        return {"app": "A World for Two: Control Room", "version": __version__, "at": utcnow(),
                "server": self.server.snapshot(), "metrics": self.metrics.latest(),
                "storage": self.storage.snapshot(), "pack": {"version": lock["version"], "minecraft": lock["minecraft"],
                    "neoforge": lock["neoforge"], "mods": len(lock["mods"]), "status": lock["release_status"]},
                "world": {"name": "A World for Two", "seed": "hidden", "view_distance": props.get("view-distance"),
                          "simulation_distance": props.get("simulation-distance")},
                "last_backup": history[0] if history else None, "backup_schedule_error": self.backups.last_schedule_error,
                "sync": self.mods.sync()}

    def connectivity(self):
        options = self.layout.settings()
        playit = []
        for process in psutil.process_iter(["pid", "name"]):
            with contextlib.suppress(psutil.Error):
                if (process.info["name"] or "").lower() in ("playit.exe", "playit"):
                    playit.append(process.info["pid"])
        return {"local_address": "127.0.0.1:" + str(options["port"]), "game_port": options["port"],
                "dashboard": "127.0.0.1:8765 (local only)",
                "playit": {"process_detected": bool(playit), "state": "process detected; tunnel unverified" if playit else "not detected",
                           "address": options["tunnel_address"] or None},
                "external_connection": "unverified until Sera joins from her own network",
                "instructions": ["Sign in to Playit, create one Minecraft Java TCP tunnel to 127.0.0.1:" + str(options["port"]) + ".",
                    "Share the Playit join address with Sera. Keep online authentication and the whitelist enabled.",
                    "Never tunnel port 8765, RCON, JMX or any dashboard endpoint.",
                    "Tailscale is an alternative. Use the opt-in network script with Sera's exact Tailscale IP and a narrow firewall rule.",
                    "Essential is an optional Prism client mod for a separately hosted-world fallback; it is not the dedicated server."]}

    def diagnostics(self):
        # Deliberately exclude server.properties, accounts, environment, tokens, saves and IP logs.
        content = io.BytesIO()
        with zipfile.ZipFile(content, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("health.json", json.dumps(self.health(), indent=2))
            archive.writestr("metrics.csv", self.metrics.csv())
            archive.writestr("console.txt", "\n".join(x["text"] for x in self.server.console()))
            archive.writestr("README.txt", "Owner-reviewed diagnostics. No world, account files, server.properties or environment is included. Review console text before sharing.\n")
        return content.getvalue()

    def get(self, path, query):
        first = lambda name, default="": query.get(name, [default])[0]
        routes = {
            "/api/bootstrap": lambda: {"app_id": "awft-control-room", "home": str(self.layout.home), "csrf": self.token, "version": __version__},
            "/api/overview": self.overview, "/api/storage": self.storage.snapshot,
            "/api/metrics": self.metrics.latest, "/api/sync": self.mods.sync,
            "/api/players": self.players.snapshot, "/api/backups": self.backups.list,
            "/api/settings": self.settings.catalog, "/api/config/history": self.settings.history,
            "/api/mods": self.mods.inventory, "/api/proposals": self.mods.proposals,
            "/api/connectivity": self.connectivity, "/api/setup": self.installer.preflight,
            "/api/jobs": self.jobs.list, "/api/health": self.health,
            "/api/compatibility": lambda: read_json(REPO / "catalog/compatibility.json", {"requests": [], "status": "report being assembled"}),
            "/api/graphics": lambda: read_json(REPO / "catalog/graphics-profiles.json", {"profiles": []}),
        }
        if path in routes:
            return routes[path]()
        if path == "/api/history":
            return self.metrics.history(first("hours", "1"))
        if path == "/api/console":
            return self.server.console(int(first("after", "0")), first("query"), first("level", "all"))
        if path == "/api/config/raw":
            return self.settings.raw(first("path"))
        if path == "/api/config/files":
            return [p.relative_to(self.layout.server).as_posix() for p in (self.layout.server / "config").rglob("*") if p.is_file() and p.suffix in (".json", ".toml", ".properties")]
        if path == "/api/mods/search":
            return self.mods.search(first("q"))
        if path == "/api/mods/versions":
            return self.mods.versions(first("project"))
        if path == "/api/player/lookup":
            return profile(first("name"))
        if path == "/api/crashes":
            return [{"name": p.name, "bytes": p.stat().st_size} for p in sorted((self.layout.server / "crash-reports").glob("*.txt"), reverse=True)[:30]]
        if path == "/api/crash":
            name = first("name")
            if not re_full_filename(name):
                raise UserError("Invalid crash report name")
            file = contained(self.layout.server / "crash-reports", name)
            if not file.is_file() or file.stat().st_size > 1024 * 1024:
                raise UserError("Crash report missing or too large")
            return {"name": name, "content": file.read_text(errors="replace")}
        if path == "/api/world/seed":
            return {"seed": self.settings.get_properties().get("level-seed") or None,
                    "note": "An empty configured seed means Minecraft chose it. Use the safe seed command and console to read the running world's actual seed."}
        raise UserError("Unknown API endpoint")

    def post(self, path, body):
        job = lambda title, function, *args: self.jobs.submit(title, function, *args)
        if path in ("/api/server/start", "/api/server/stop", "/api/server/restart"):
            action = path.rsplit("/", 1)[1]
            return job(action.title() + " world", getattr(self.server, action))
        if path == "/api/console":
            return self.server.command(body.get("command"), body.get("confirmed", False))
        if path == "/api/setup/install":
            return job("Install dedicated server", self.installer.install)
        if path == "/api/setup/repair":
            return job("Repair installation", self.installer.repair)
        if path == "/api/setup/eula":
            return self.installer.accept_eula(body.get("accepted"))
        if path == "/api/setup/players":
            return self.installer.players(body.get("names"))
        if path == "/api/player":
            return job("Update player access", self.players.update, body.get("action"), body.get("name"), body.get("confirmed", False))
        if path == "/api/settings":
            return self.settings.update(body.get("scope"), body.get("changes"), body.get("expected"))
        if path == "/api/config/propose":
            return self.settings.raw_proposal(body.get("path"), body.get("content"), body.get("expected"))
        if path == "/api/config/save":
            return self.settings.raw_save(body.get("path"), body.get("content"), body.get("expected"))
        if path == "/api/config/restore":
            return self.settings.restore(body.get("id"))
        if path == "/api/mods/propose":
            return job("Stage mod change", self.mods.propose, body.get("action"), body.get("project"), body.get("version"), body.get("allow_prerelease", False))
        if path == "/api/mods/deploy":
            return job("Deploy approved release", self.mods.deploy, body.get("id"), body.get("confirmation"), body.get("publication_url"))
        if path == "/api/mods/rollback":
            return job("Roll back release", self.mods.rollback, body.get("id"), body.get("confirmation"))
        if path == "/api/mods/curseforge":
            return self.mods.curseforge(body.get("project_id"))
        if path == "/api/client/report":
            return self.mods.import_client_report(body.get("player"), body.get("report"))
        if path == "/api/backups/create":
            return job("Create and verify world backup", self.backups.create)
        if path == "/api/backups/verify":
            return job("Verify backup integrity", self.backups.verify, body.get("id"))
        if path == "/api/backups/restore":
            return job("Restore selected world backup", self.backups.restore, body.get("id"), body.get("confirmation"))
        if path == "/api/health":
            return job("Run health check", self.health)
        if path == "/api/diagnostics/start":
            return self.server.command("spark profiler start --timeout 60")
        if path == "/api/open":
            target = body.get("target")
            if target == "server":
                if os.name != "nt":
                    raise UserError("Open folder is available on Windows")
                os.startfile(self.layout.server)
            elif target == "prism":
                options = self.layout.settings()
                prism = options.get("prism_path") or shutil.which("prismlauncher") or next((str(p) for p in [Path(os.environ.get("LOCALAPPDATA", ".")) / "Programs/PrismLauncher/prismlauncher.exe", Path(r"C:\Program Files\PrismLauncher\prismlauncher.exe")] if p.is_file()), None)
                if not prism or not Path(prism).is_file():
                    raise UserError("Prism Launcher was not found; install it from prismlauncher.org")
                subprocess.Popen([prism], creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            else:
                raise UserError("Unsupported shortcut")
            return {"opened": target}
        if path == "/api/connectivity":
            address = body.get("address", "")
            if not isinstance(address, str) or len(address) > 200 or not all(c.isalnum() or c in ".-_:" for c in address):
                raise UserError("Enter only the join hostname and optional port")
            self.storage.reserve(8192)
            options = self.layout.settings()
            options["tunnel_address"] = address
            self.layout.save_settings(options)
            return self.connectivity()
        raise UserError("Unknown API endpoint")


def re_full_filename(name):
    import re
    return isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9_.-]+\.txt", name)


class HTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        server_version = "AWFT/" + __version__

        def log_message(self, *_):
            pass

        def security(self, mutate=False):
            allowed = {"127.0.0.1:" + str(self.server.server_port), "localhost:" + str(self.server.server_port)}
            host = self.headers.get("Host", "")
            if host not in allowed or self.client_address[0] not in ("127.0.0.1", "::1"):
                return False
            if self.headers.get("Sec-Fetch-Site") == "cross-site":
                return False
            origin = self.headers.get("Origin")
            if origin and origin not in {"http://" + h for h in allowed}:
                return False
            if mutate and not hmac.compare_digest(self.headers.get("X-AWFT-CSRF", ""), app.token):
                return False
            return True

        def send(self, status, data, content_type="application/json", attachment=None):
            raw = json.dumps(data, ensure_ascii=False).encode() if content_type == "application/json" else data.encode() if isinstance(data, str) else data
            self.send_response(status)
            self.send_header("Content-Type", content_type + ("; charset=utf-8" if content_type.startswith("text/") or content_type == "application/json" else ""))
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            if attachment:
                self.send_header("Content-Disposition", 'attachment; filename="' + attachment + '"')
            self.end_headers()
            with contextlib.suppress(BrokenPipeError, ConnectionResetError):
                self.wfile.write(raw)

        def do_GET(self):
            if not self.security():
                return self.send(403, {"error": "Local origin required"})
            parsed = urllib.parse.urlsplit(self.path)
            path, query = parsed.path, urllib.parse.parse_qs(parsed.query)
            try:
                if path == "/api/export/metrics.csv":
                    return self.send(200, app.metrics.csv(), "text/csv", "awft-performance.csv")
                if path == "/api/export/diagnostics.zip":
                    return self.send(200, app.diagnostics(), "application/zip", "awft-diagnostics.zip")
                if path.startswith("/api/"):
                    return self.send(200, app.get(path, query))
                if path.startswith("/pack/"):
                    lock, release = app.mods.active()
                    relative = urllib.parse.unquote(path.removeprefix("/pack/"))
                    file = contained(release, relative)
                    if file.suffix not in (".toml", ".json", ".txt", ".properties") or not file.is_file() or file.stat().st_size > 4 * 1024 * 1024:
                        return self.send(404, {"error": "Pack file not found"})
                    return self.send(200, file.read_bytes(), "text/plain")
                files = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css", "/mark.svg": "mark.svg"}
                if path not in files:
                    return self.send(404, {"error": "Page not found"})
                file = REPO / "control_room/static" / files[path]
                return self.send(200, file.read_bytes(), mimetypes.guess_type(file)[0] or "application/octet-stream")
            except UserError as exc:
                self.send(400, {"error": str(exc)})
            except (OSError, ValueError, KeyError) as exc:
                self.send(503, {"error": "This view is temporarily unavailable: " + str(exc)[:300]})

        def do_POST(self):
            if not self.security(mutate=True):
                return self.send(403, {"error": "Local origin and current session token required"})
            try:
                if self.headers.get("Content-Type", "").split(";", 1)[0] != "application/json":
                    return self.send(415, {"error": "Use application/json"})
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 1024 * 1024:
                    return self.send(413, {"error": "Request exceeds the 1 MiB limit"})
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    raise UserError("Request body must be a JSON object")
                self.send(200, app.post(urllib.parse.urlsplit(self.path).path, body))
            except UserError as exc:
                self.send(400, {"error": str(exc)})
            except (ValueError, KeyError, TypeError) as exc:
                self.send(400, {"error": "Invalid request: " + str(exc)[:200]})
            except Exception:
                self.send(503, {"error": "The operation failed. Its files and diagnostic receipts were preserved."})
    return Handler
