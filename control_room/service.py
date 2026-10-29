"""Dedicated Linux console owner and same-UID Unix-socket adapter.

No shell, remote TCP listener, RCON, pickle, or unrestricted command dispatch.
The dashboard uses this adapter; only the supervisor creates a Java child.
"""
from __future__ import annotations

import collections
import contextlib
import json
import os
import re
import signal
import socket
import socketserver
import stat
import struct
import threading
import time

from .common import Layout, UserError, read_json, utcnow, write_json

MAX_REQUEST = 16 * 1024
MAX_RESPONSE = 8 * 1024 * 1024


def socket_path(layout):
    return layout.state / "service" / "console.sock"


def internal_command(command):
    """Existing dedicated controls, never a browser-provided raw shell/console."""
    if not isinstance(command, str) or len(command) > 300:
        raise UserError("Unsupported service console request")
    patterns = [r"stop", r"chunky pause", r"neoforge tps",
                r"awft (teleport|cinematic) [a-f0-9-]{8,64}",
                r"awft permissions [A-Za-z0-9_]{1,16} [a-f0-9-]{36} [0-4] (true|false)",
                r"gamemode (survival|creative|adventure|spectator) [A-Za-z0-9_]{1,16}",
                r"experience set [A-Za-z0-9_]{1,16} (\d{1,3}|1000) levels",
                r"kick [A-Za-z0-9_]{1,16}"]
    if not any(re.fullmatch(pattern, command) for pattern in patterns):
        raise UserError("Unsupported service console request")
    return command


class ServiceServer:
    """Fail closed when the independent console owner cannot be reached."""
    independent = True

    def __init__(self, layout, storage):
        if os.name != "posix" or not hasattr(socket, "SO_PEERCRED"):
            raise UserError("The dedicated service backend requires Linux")
        self.layout, self.storage = layout, storage

    def _rpc(self, action, **data):
        path = socket_path(self.layout)
        try:
            info = path.lstat()
            if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise UserError("The console socket must be private and owned by the service account")
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as stream:
                stream.settimeout(3600 if action.startswith("backup/") else 145 if action == "stop" else 60)
                stream.connect(str(path))
                _, uid, _ = struct.unpack("3i", stream.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                if uid != os.getuid():
                    raise UserError("Unexpected console service owner")
                request = json.dumps({"action": action, **data}).encode() + b"\n"
                if len(request) > MAX_REQUEST:
                    raise UserError("Console request exceeds its limit")
                stream.sendall(request)
                with stream.makefile("rb") as source:
                    raw = source.readline(MAX_RESPONSE + 1)
                if len(raw) > MAX_RESPONSE or not raw.endswith(b"\n"):
                    raise UserError("Invalid console service response")
                response = json.loads(raw)
                if not response.get("ok"):
                    raise UserError(response.get("error", "Console operation failed; inspect service logs"))
                return response["result"]
        except (OSError, ValueError, KeyError) as exc:
            # Never infer offline or retry a possibly applied mutation.
            raise UserError("Minecraft service is unavailable; status is unknown. Inspect systemctl/journal before retrying any action.") from exc

    def snapshot(self):
        return self._rpc("snapshot")["snapshot"]

    @property
    def identity(self):
        return self._rpc("snapshot")["identity"]

    @property
    def state(self):
        return self.snapshot()["state"]

    @state.setter
    def state(self, value):
        if value != "stopping":
            raise UserError("Only the console owner may change process state")

    @property
    def warning(self):
        return self.snapshot().get("warning")

    def running(self):
        return self._rpc("snapshot")["running"]

    def start(self, notify=lambda _: None):
        notify("Requesting start from the dedicated console owner")
        return self._rpc("start")

    def stop(self, notify=lambda _: None, timeout=120):
        notify("Waiting for the dedicated service to save and close Minecraft")
        return self._rpc("stop")

    def restart(self, notify=lambda _: None):
        self.stop(notify)
        return self.start(notify)

    def command(self, command, confirmed=False):
        return self._rpc("command", command=command, confirmed=confirmed)

    def _write(self, command):
        return self._rpc("write", command=internal_command(command))

    def probe(self):
        # The supervisor probes independently of the dashboard lifetime.
        pass

    def console(self, after=0, query="", level="all"):
        return self._rpc("console", after=after, query=query, level=level)

    def wait_ready(self, timeout=360):
        if type(timeout) not in (int, float) or not 0 < timeout <= 360:
            raise UserError("Use a readiness timeout of at most 360 seconds")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            value = self.snapshot()
            if value["state"] == "online":
                return value
            if value["state"] != "starting":
                break
            time.sleep(.25)
        raise UserError("Minecraft did not report readiness; inspect its console before retrying")


class ServiceBackups:
    """The console owner serializes scheduled and requested world operations."""
    def __init__(self, local, server):
        self.local, self.server = local, server

    @property
    def last_schedule_error(self):
        return self.server._rpc("snapshot").get("backup_schedule_error")

    def list(self):
        return self.local.list()

    def path(self, ident):
        return self.local.path(ident)

    def create(self, notify=lambda _: None, reason="manual", resume=True):
        notify("Dedicated host is creating and verifying the saved-world snapshot")
        return self.server._rpc("backup/create", reason=reason, resume=resume)

    def verify(self, ident, notify=lambda _: None):
        return self.server._rpc("backup/verify", id=ident)

    def restore(self, ident, confirmation, notify=lambda _: None):
        return self.server._rpc("backup/restore", id=ident, confirmation=confirmation)

    def close(self):
        pass


class RestartPolicy:
    def __init__(self, layout):
        self.layout = layout
        self.path = layout.state / "service-restarts.json"

    def admit(self, now=None):
        now = time.time() if now is None else now
        settings = self.layout.settings()
        limit = settings["service_restart_limit"]
        window = settings["service_restart_window_seconds"]
        delay = settings["service_restart_delay_seconds"]
        if (type(limit) is not int or not 0 <= limit <= 5 or type(window) is not int
                or not 300 <= window <= 86400 or type(delay) is not int or not 10 <= delay <= 600):
            raise UserError("Invalid bounded Minecraft restart policy")
        attempts = read_json(self.path, {}).get("attempts", [])
        if not isinstance(attempts, list) or any(type(x) not in (int, float) for x in attempts):
            raise UserError("Invalid restart journal; inspect it before restarting")
        attempts = [x for x in attempts if x >= now - window]
        if len(attempts) >= limit or attempts and now - attempts[-1] < delay:
            return False
        attempts.append(now)
        write_json(self.path, {"at": utcnow(), "attempts": attempts})
        return True


class Supervisor:
    def __init__(self, layout, storage, server):
        self.layout, self.storage, self.server = layout, storage, server
        self.stop_event = threading.Event()
        self.operations = threading.RLock()
        self.policy = RestartPolicy(layout)
        self.desired_path = layout.state / "service-desired.json"
        self.desired = read_json(self.desired_path, {}).get("running", layout.settings()["service_autostart"])
        self.audit = collections.deque(maxlen=200)
        from .backups import Backups
        self.backups = Backups(layout, storage, server)

    def dispatch(self, request):
        action = request.get("action")
        if action == "snapshot":
            return {"snapshot": self.server.snapshot(), "identity": self.server.identity,
                    "running": self.server.running(), "backup_schedule_error": self.backups.last_schedule_error}
        if action == "console":
            after, query, level = request.get("after", 0), request.get("query", ""), request.get("level", "all")
            if type(after) is not int or not isinstance(query, str) or len(query) > 200 or level not in ("all", "info", "warning", "error"):
                raise UserError("Invalid console filter")
            return self.server.console(after, query, level)
        if action not in ("start", "stop", "command", "write", "backup/create", "backup/verify", "backup/restore"):
            raise UserError("Unsupported console operation")
        with self.operations:
            if self.stop_event.is_set():
                raise UserError("Console service is shutting down")
            self.storage.reserve(65536)
            self.audit.append({"at": utcnow(), "action": action})
            write_json(self.layout.state / "service-audit.json", list(self.audit))
            if action == "backup/create":
                reason, resume = request.get("reason", "manual"), request.get("resume", True)
                if not isinstance(reason, str) or len(reason) > 80 or type(resume) is not bool:
                    raise UserError("Invalid backup request")
                self.desired = False
                write_json(self.desired_path, {"running": False, "at": utcnow(), "reason": "backup in progress"})
                result = self.backups.create(reason=reason, resume=resume)
                self.desired = self.server.running()
                write_json(self.desired_path, {"running": self.desired, "at": utcnow()})
                return result
            if action == "backup/verify":
                return self.backups.verify(request.get("id"))
            if action == "backup/restore":
                return self.backups.restore(request.get("id"), request.get("confirmation"))
            if action in ("start", "stop"):
                self.desired = action == "start"
                write_json(self.desired_path, {"running": self.desired, "at": utcnow()})
                if action == "start":
                    try:
                        return self.server.start()
                    except BaseException:
                        self.desired = False
                        write_json(self.desired_path, {"running": False, "at": utcnow(), "reason": "explicit start failed; inspect before retry"})
                        raise
                return self.server.stop()
            if action == "write":
                command = internal_command(request.get("command"))
                if command == "stop":
                    return self.dispatch({"action": "stop"})
                self.server._write(command)
                return {"sent": True}
            return self.server.command(request.get("command"), request.get("confirmed") is True)


def serve(home):
    if os.name != "posix" or not hasattr(socket, "SO_PEERCRED") or os.geteuid() == 0:
        raise UserError("Run the Minecraft supervisor on Linux as a dedicated nonroot account")
    from .backups import Backups
    from .ownership import ProcessLease
    from .server import Server
    from .storage import Storage
    layout = Layout(home)
    storage = Storage(layout)
    storage.reserve(80 * 1024 * 1024)
    layout.create()
    if layout.settings()["server_backend"] != "unix-service" or layout.settings()["hosting_mode"] != "dedicated-ubuntu":
        raise UserError("Explicitly configure dedicated-ubuntu and unix-service before starting")
    lease = ProcessLease(layout.state / "console-owner.lock")
    path = socket_path(layout)
    path.parent.mkdir(mode=0o700, exist_ok=True)
    folder = path.parent.lstat()
    if not stat.S_ISDIR(folder.st_mode) or folder.st_uid != os.getuid() or folder.st_mode & 0o077:
        lease.close()
        raise UserError("The service socket directory must be private and owned by this account")
    if path.exists() or path.is_symlink():
        entry = path.lstat()
        if not stat.S_ISSOCK(entry.st_mode) or entry.st_uid != os.getuid():
            lease.close()
            raise UserError("Refusing to replace an unexpected service socket path")
        path.unlink()  # Only after the exclusive console-owner lease.
    server = Server(layout, storage)
    supervisor = Supervisor(layout, storage, server)

    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            self.connection.settimeout(150)
            _, uid, _ = struct.unpack("3i", self.connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
            if uid != os.getuid():
                return
            try:
                raw = self.rfile.readline(MAX_REQUEST + 1)
                if len(raw) > MAX_REQUEST or not raw.endswith(b"\n"):
                    raise UserError("Invalid console request")
                request = json.loads(raw)
                if not isinstance(request, dict):
                    raise UserError("Invalid console request")
                response = {"ok": True, "result": supervisor.dispatch(request)}
            except UserError as exc:
                response = {"ok": False, "error": str(exc)}
            except Exception:
                response = {"ok": False, "error": "Console operation failed; inspect the service journal"}
            data = json.dumps(response).encode() + b"\n"
            if len(data) > MAX_RESPONSE:
                data = b'{"ok":false,"error":"Console response exceeded its limit"}\n'
            with contextlib.suppress(OSError):
                self.wfile.write(data)

    # Bound concurrent requests; long stop calls hold no status lock.
    class SocketServer(socketserver.ThreadingUnixStreamServer):
        daemon_threads = True
        block_on_close = False
        slots = threading.BoundedSemaphore(8)

        def process_request(self, request, client_address):
            if not self.slots.acquire(blocking=False):
                self.shutdown_request(request)
                return
            try:
                super().process_request(request, client_address)
            except BaseException:
                self.slots.release()
                raise

        def process_request_thread(self, request, client_address):
            try:
                super().process_request_thread(request, client_address)
            finally:
                self.slots.release()

    with SocketServer(str(path), Handler) as http:
        os.chmod(path, 0o600)
        thread = threading.Thread(target=http.serve_forever, daemon=True)
        thread.start()
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, lambda *_: supervisor.stop_event.set())
        backups = supervisor.backups
        first_check = True
        scheduled_at = time.time()
        last_size_check = 0
        try:
            while not supervisor.stop_event.is_set():
                with supervisor.operations:
                    if supervisor.desired and not server.running():
                        attempt = first_check and server.state != "failed" or server.state == "failed" and supervisor.policy.admit()
                        if attempt:
                            try:
                                server.start()
                            except Exception as exc:
                                server.record("Service startup refused: " + str(exc))
                                supervisor.desired = False
                                write_json(supervisor.desired_path, {"running": False, "at": utcnow(), "reason": "startup refused"})
                    first_check = False
                    server.probe()
                    try:
                        storage.checkpoint(0)
                        if time.monotonic() - last_size_check >= 240:
                            from .storage import tree_size
                            options = layout.settings()
                            if (tree_size(layout.world) >= options["world_budget_gib"] * 1024 ** 3
                                    or tree_size(layout.caches) >= options["cache_budget_gib"] * 1024 ** 3):
                                raise UserError("World or cache growth reached its configured budget")
                            last_size_check = time.monotonic()
                    except UserError as exc:
                        server.record("Storage policy requires a graceful stop: " + str(exc))
                        supervisor.desired = False
                        write_json(supervisor.desired_path, {"running": False, "at": utcnow(), "reason": "storage policy"})
                        if server.running():
                            server.stop()
                    if time.time() - scheduled_at >= 30 and server.state == "online":
                        history = backups.list()
                        latest = max((backups.path(x["id"]).stat().st_mtime for x in history), default=scheduled_at)
                        if time.time() - latest >= layout.settings()["backup_interval_hours"] * 3600:
                            try:
                                supervisor.dispatch({"action": "backup/create", "reason": "scheduled", "resume": True})
                                backups.last_schedule_error = None
                            except Exception as exc:
                                backups.last_schedule_error = str(exc)
                supervisor.stop_event.wait(5)
        finally:
            backups.close()
            # Retain the process and lease if saving is slow. No forced kill.
            with supervisor.operations:
                while server.running():
                    try:
                        server.stop()
                    except UserError as exc:
                        server.record(str(exc))
                        time.sleep(1)
            http.shutdown()
            thread.join(timeout=5)
            path.unlink(missing_ok=True)
            lease.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="AWFT dedicated Linux Minecraft console owner")
    parser.add_argument("--home", required=True)
    args = parser.parse_args()
    try:
        serve(args.home)
    except UserError as exc:
        parser.exit(1, str(exc) + "\n")


if __name__ == "__main__":
    main()
