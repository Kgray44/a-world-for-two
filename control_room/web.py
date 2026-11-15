from __future__ import annotations

import contextlib
import hmac
import io
import json
import logging
import logging.handlers
import mimetypes
import os
import secrets
import shutil
import socket
import subprocess
import threading
import time
import traceback
import urllib.error
import urllib.parse
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import psutil

from . import __version__
from .backups import Backups
from .atlas import Atlas
from .cinematics import Cinematics, MAX_IMAGE
from .common import REPO, Layout, UserError, contained, digest, read_json, utcnow, write_json
from .install import Installer
from .graphics import Graphics
from .playit import Playit
from .jobs import Jobs, safe_message
from .metrics import Metrics
from .mod_manager import ModManager
from .pack import public_pack_file, validate_pack, verify_installed
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
        self.error_logger = logging.getLogger('awft-dashboard-' + str(self.layout.home))
        self.error_logger.setLevel(logging.ERROR)
        if not self.error_logger.handlers:
            self.error_logger.addHandler(logging.handlers.RotatingFileHandler(
                self.layout.logs / 'dashboard-errors.log', maxBytes=512 * 1024, backupCount=2, encoding='utf-8'))
        self.server = Server(self.layout, self.storage)
        self.settings = Settings(self.layout, self.storage, self.server)
        self.settings.initialize()
        self.jobs = Jobs(self.layout.state / 'jobs.json', self.storage, lambda exc: report_error(self, exc))
        self.metrics = Metrics(self.layout, self.storage, self.server)
        self.backups = Backups(self.layout, self.storage, self.server)
        self.mods = ModManager(self.layout, self.storage, self.server, self.backups)
        self.installer = Installer(self.layout, self.storage, self.server, self.settings)
        self.players = Players(self.layout, self.storage, self.server, self.settings, self.metrics.latest)
        self.atlas = Atlas(self.layout, self.storage, self.server, self.players, self.metrics)
        self.metrics.observers.append(self.atlas.monitor)
        self.cinematics = Cinematics(self.layout, self.storage, self.server, self.players, self.metrics.latest)
        self.graphics = Graphics(self.layout, self.storage)
        self.playit = Playit()
        self.token = secrets.token_urlsafe(32)

    def start(self):
        self.playit.start_monitor()
        self.metrics.start()
        self.backups.start_schedule()

    def close(self):
        self.mods.close()
        self.playit.close()
        self.backups.close()
        self.metrics.close()
        self.jobs.close()
        self.atlas.close()
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
                "sync": self.mods.overview_sync(), 'active_test': self.active_test()}

    def active_test(self):
        """Identify another *owned, currently running* test without polling it."""
        path = self.layout.state / 'prepared-playtest.json'
        if not path.is_file() or path.stat().st_size > 512 * 1024:
            return None
        try:
            prepared = read_json(path)
            home = Path(prepared['home']).resolve()
            if prepared.get('format') != 'awft-combined-playtest:1' or not home.is_relative_to(self.layout.staging / 'world-tests'):
                return None
            owner = read_json(home / 'dashboard/test-owner.json', {})
            identity = read_json(home / 'dashboard/server-process.json', {})
            if owner.get('owner_source') != str(REPO) or not identity.get('pid'):
                return None
            process = psutil.Process(identity['pid'])
            if abs(process.create_time() - identity['created']) > .1 or Path(process.cwd()).resolve() != home / 'server':
                return None
            return {'id': prepared['id'], 'version': read_json(home / 'packwiz/active.json', {}).get('version'),
                    'url': 'http://127.0.0.1:8766/', 'game_address': '127.0.0.1:25575'}
        except (OSError, ValueError, KeyError, psutil.Error):
            return None

    def start_world(self, notify=lambda _: None):
        if self.active_test():
            raise UserError('The full playtest world is already running. Open its live Control Room at http://127.0.0.1:8766/ to manage it.')
        self.server.start(notify=notify)
        deadline = time.monotonic() + 360
        while self.server.running() and self.server.state == 'starting' and time.monotonic() < deadline:
            time.sleep(.25)
        if self.server.state != 'online':
            detail = getattr(self.server, 'warning', None)
            raise UserError('Minecraft did not finish starting. See Console & logs for the actual error; starting Java alone is not a successful server start.'
                            + (' ' + detail if detail else ''))
        return self.server.snapshot()

    def restart_world(self, notify=lambda _: None):
        if self.active_test():
            raise UserError('Manage the running playtest in its Control Room at http://127.0.0.1:8766/.')
        self.server.stop(notify=notify)
        return self.start_world(notify=notify)

    def connectivity(self):
        options = self.layout.settings()
        return {"local_address": "127.0.0.1:" + str(options["port"]), "game_port": options["port"],
                "dashboard": "127.0.0.1:8765 (local only)",
                "playit": self.playit.snapshot() | {"address": options["tunnel_address"] or None},
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
            "/api/bootstrap": lambda: {"app_id": "awft-control-room", "home": str(self.layout.home), "csrf": self.token, "version": __version__,
                                       'test_context': read_json(self.layout.state / 'test-owner.json', None)},
            "/api/overview": self.overview,
            "/api/storage": lambda: self.storage.snapshot(live=True, refresh=first('refresh') == '1'),
            "/api/metrics": self.metrics.latest, "/api/sync": self.mods.sync,
            '/api/diagnostics/chunks': lambda: self.metrics.latest().get('chunk_diagnostics', {'unavailable': 'Start the server with the updated Control Bridge to collect chunk diagnostics.'}),
            "/api/players": self.players.snapshot, "/api/backups": self.backups.list,
            "/api/atlas": self.atlas.snapshot,
            "/api/cinematics": self.cinematics.snapshot,
            "/api/atlas/export": lambda: self.atlas.export(first('collection', 'shared')),
            "/api/settings": self.settings.catalog, "/api/config/history": self.settings.history,
            "/api/mods": self.mods.inventory, "/api/proposals": self.mods.proposals,
            "/api/mods/manual": self.mods.manual_files,
            "/api/connectivity": self.connectivity, "/api/setup": self.installer.preflight,
            "/api/jobs": self.jobs.list, "/api/health": self.health,
            "/api/compatibility": lambda: read_json(REPO / "catalog/compatibility.json", {"requests": [], "status": "report being assembled"}),
            "/api/graphics": self.graphics.snapshot,
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
        if path == "/api/player/details":
            return self.players.details(first("name"))
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
        if path == '/api/cinematics/settings':
            return self.cinematics.settings(body.get('changes'), body.get('expected'))
        if path == '/api/cinematics/trigger':
            return self.cinematics.trigger(body.get('location'), body.get('scene'), body.get('expected'), body.get('id'), body.get('enabled', False))
        if path == '/api/cinematics/trigger/remove':
            return self.cinematics.remove_trigger(body.get('id'), body.get('expected'), body.get('confirmed', False))
        if path == '/api/cinematics/action':
            return job('Send cinematic command', self.cinematics.action, body.get('name'), body.get('action'), body.get('scene'))
        if path == '/api/cinematics/background/restore':
            return self.cinematics.restore(body.get('sha256'), body.get('expected'))
        if path == '/api/cinematics/background/remove':
            return self.cinematics.remove(body.get('sha256'), body.get('confirmed', False))
        if path == '/api/cinematics/background/apply':
            return job('Apply menu artwork to local client', self.cinematics.apply, body.get('client'), body.get('expected'))
        if path == '/api/cinematics/presentation':
            return job('Apply local camera preset', self.cinematics.presentation, body.get('client'), body.get('preset'), body.get('expected'))
        if path == '/api/atlas/waypoint':
            return self.atlas.save(body.get('waypoint'), body.get('expected'))
        if path == '/api/atlas/annotation':
            return self.atlas.annotate(body.get('id'), body.get('annotation'), body.get('expected'))
        if path == '/api/atlas/remove':
            return self.atlas.remove(body.get('id'), body.get('expected'), body.get('confirmed', False))
        if path == '/api/atlas/import':
            return self.atlas.import_collection(body.get('data'), body.get('expected'))
        if path == '/api/atlas/settings':
            return self.atlas.settings(body.get('changes'))
        if path == '/api/atlas/clear-cache':
            return job('Clear rendered map cache', self.atlas.clear_cache, body.get('confirmed', False))
        if path == '/api/atlas/teleport':
            return job('Safely teleport selected player', self.atlas.teleport, body.get('name'), body.get('destination'), body.get('confirmed', False))
        if path == '/api/graphics/select':
            return self.graphics.apply(body.get('client'), body.get('shader'), body.get('expected'), body.get('allow_lod_limited',False))
        if path == '/api/playit/action':
            return job('Control Playit service',self.playit.action,body.get('action'),body.get('confirmed',False))
        if path in ("/api/server/start", "/api/server/stop", "/api/server/restart"):
            action = path.rsplit("/", 1)[1]
            function = self.start_world if action == 'start' else self.restart_world if action == 'restart' else self.server.stop
            return job(action.title() + " world", function)
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
        if path == "/api/player/permissions":
            return job("Save player permissions", self.players.permissions, body.get("name"), body.get("level"), body.get("bypass", False), body.get("confirmed", False))
        if path == "/api/player/action":
            return job("Update player settings", self.players.game_action, body.get("name"), body.get("action"), body.get("value"), body.get("confirmed", False))
        if path == "/api/settings":
            return self.settings.update(body.get("scope"), body.get("changes"), body.get("expected"))
        if path == "/api/settings/mod":
            return self.settings.update_mod(body.get("id"), body.get("value"), body.get("expected"))
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
        if path == "/api/mods/import-manual":
            return job("Verify downloaded mod", self.mods.import_manual, body.get("slug"))
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


def report_error(app, exc):
    ident = secrets.token_hex(6)
    logger = getattr(app, 'error_logger', logging.getLogger(__name__))
    detail = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__, limit=8))
    logger.error('Error reference %s\n%s', ident, safe_message(detail, 10000))
    return ident


class HTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        server_version = "AWFT/" + __version__

        def log_message(self, *_):
            pass

        def security_error(self, mutate=False):
            allowed = {"127.0.0.1:" + str(self.server.server_port), "localhost:" + str(self.server.server_port)}
            host = self.headers.get("Host", "")
            if host not in allowed or self.client_address[0] not in ("127.0.0.1", "::1"):
                return 'local_origin_required'
            if self.headers.get("Sec-Fetch-Site") == "cross-site":
                return 'local_origin_required'
            origin = self.headers.get("Origin")
            if origin and origin not in {"http://" + h for h in allowed}:
                return 'local_origin_required'
            if mutate and not hmac.compare_digest(self.headers.get("X-AWFT-CSRF", "").encode(), app.token.encode()):
                return 'session_expired'
            return None

        def security(self, mutate=False):
            return self.security_error(mutate) is None

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
            with contextlib.suppress(BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                self.wfile.write(raw)

        def do_GET(self):
            if not self.security():
                return self.send(403, {"error": "Local origin required"})
            parsed = urllib.parse.urlsplit(self.path)
            path, query = parsed.path, urllib.parse.parse_qs(parsed.query)
            try:
                if path == '/cinematics/background':
                    file = app.cinematics.image(query.get('id', [None])[0])
                    raw = file.read_bytes()
                    return self.send(200, raw, 'image/png' if raw.startswith(b'\x89PNG') else 'image/jpeg')
                if path == '/api/cinematics/export':
                    return self.send(200, app.cinematics.export(), 'application/zip', 'a-world-for-two-menu-update.zip')
                if path.startswith('/atlas/tiles/'):
                    parts = path.removeprefix('/atlas/tiles/').split('/')
                    if len(parts) != 3:
                        raise UserError('Invalid map tile path')
                    file = app.atlas.tile(*parts)
                    return self.send(200, file.read_bytes(), 'image/png') if file else self.send(404, b'', 'image/png')
                if path == "/api/export/metrics.csv":
                    return self.send(200, app.metrics.csv(), "text/csv", "awft-performance.csv")
                if path == '/api/atlas/export':
                    collection = query.get('collection', ['shared'])[0]
                    return self.send(200, json.dumps(app.atlas.export(collection), ensure_ascii=False, indent=2), 'application/json', 'awft-waypoints-' + collection + '.json')
                if path == "/api/export/diagnostics.zip":
                    return self.send(200, app.diagnostics(), "application/zip", "awft-diagnostics.zip")
                if path.startswith("/api/"):
                    return self.send(200, app.get(path, query))
                if path.startswith("/pack/"):
                    lock, release = app.mods.active()
                    relative = urllib.parse.unquote(path.removeprefix("/pack/"))
                    file = public_pack_file(release, relative)
                    return self.send(200, file.read_bytes(), mimetypes.guess_type(file)[0] or 'application/octet-stream')
                files = {"/": "index.html", "/app.js": "app.js", '/session.js': 'session.js', '/polling.js': 'polling.js', '/atlas-state.js': 'atlas-state.js', "/style.css": "style.css", "/mark.svg": "mark.svg", '/atlas.js': 'atlas.js', '/cinematics.js': 'cinematics.js', '/vendor/leaflet.js': 'vendor/leaflet.js', '/vendor/leaflet.css': 'vendor/leaflet.css'}
                if path not in files:
                    return self.send(404, {"error": "Page not found"})
                file = REPO / "control_room/static" / files[path]
                return self.send(200, file.read_bytes(), mimetypes.guess_type(file)[0] or "application/octet-stream")
            except UserError as exc:
                self.send(400, {"error": safe_message(exc)})
            except Exception as exc:
                ident = report_error(app, exc)
                self.send(503, {"error": "This view is temporarily unavailable. Inspect logs/dashboard-errors.log; error reference " + ident + '.'})

        def do_POST(self):
            reason = self.security_error(mutate=True)
            if reason:
                message = ('Control Room restarted and this page has an old session. Reload the page to reconnect.' if reason == 'session_expired' else
                           'Use this computer’s local Control Room address. The request origin was rejected.')
                return self.send(403, {'code': reason, 'error': message})
            try:
                if urllib.parse.urlsplit(self.path).path == '/api/cinematics/background':
                    if self.headers.get('Content-Type', '').split(';', 1)[0] not in ('image/png', 'image/jpeg'):
                        return self.send(415, {'error': 'Upload a JPEG or PNG image'})
                    length = int(self.headers.get('Content-Length', '0'))
                    if not 0 < length <= MAX_IMAGE:
                        return self.send(413, {'error': 'Background images are limited to 8 MiB'})
                    query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                    return self.send(200, app.cinematics.upload(self.rfile.read(length), query.get('expected', [''])[0]))
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
                self.send(400, {"error": safe_message(exc)})
            except (ValueError, KeyError, TypeError):
                self.send(400, {"error": "Invalid request. Check the supplied fields and refresh before trying again."})
            except Exception as exc:
                ident = report_error(app, exc)
                self.send(503, {"error": "The operation failed. Inspect preserved files and logs/dashboard-errors.log; error reference " + ident + '.'})
    return Handler
