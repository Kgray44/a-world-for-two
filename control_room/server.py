from __future__ import annotations

import collections
import contextlib
from copy import deepcopy
import json
import logging
import logging.handlers
import os
import re
import shutil
import socket
import struct
import subprocess
import threading
import time
from pathlib import Path

import psutil

from .common import UserError, digest, read_json, utcnow, write_json
from .metrics import measurement_freshness
from .settings import properties


def varint(value):
    result = bytearray()
    while True:
        byte = value & 0x7f
        value >>= 7
        result.append(byte | (0x80 if value else 0))
        if not value:
            return bytes(result)


def recv_exact(stream, count):
    if count > 1024 * 1024:
        raise UserError("Minecraft status response is too large")
    result = b""
    while len(result) < count:
        block = stream.recv(count - len(result))
        if not block:
            raise OSError("Status connection closed")
        result += block
    return result


def read_varint(stream):
    value = 0
    for shift in range(0, 35, 7):
        byte = recv_exact(stream, 1)[0]
        value |= (byte & 0x7f) << shift
        if not byte & 0x80:
            return value
    raise UserError("Invalid status packet")


def minecraft_status(port):
    with socket.create_connection(("127.0.0.1", port), timeout=1.5) as stream:
        stream.settimeout(1.5)
        host = b"127.0.0.1"
        handshake = b"\0" + varint(767) + varint(len(host)) + host + struct.pack(">H", port) + b"\1"
        stream.sendall(varint(len(handshake)) + handshake + b"\1\0")
        length = read_varint(stream)
        if length > 1024 * 1024 or recv_exact(stream, 1) != b"\0":
            raise UserError("Unexpected status response")
        payload_length = read_varint(stream)
        response = json.loads(recv_exact(stream, payload_length))
        return {"players": response.get("players", {}), "version": response.get("version", {})}


class Server:
    def __init__(self, layout, storage):
        self.layout, self.storage = layout, storage
        self._lock = threading.RLock()
        self.process = None
        self.identity = None
        self.state = "offline"
        self.started = None
        self.lines = collections.deque(maxlen=2000)
        self.events = collections.deque(maxlen=200)
        self.sequence = 0
        self.tick = {"tps": None, "mspt": None, "at": None, "source": "neoforge tps console (not sampled yet)"}
        self._last_probe = 0
        self.player_info = None
        self.player_info_at = None
        self.player_info_identity = None
        self._last_player_info = None
        self._last_player_info_at = None
        self._logger = None
        self._reader_thread = None
        self.warning = None
        self._recover_identity()

    @property
    def owner_path(self):
        return self.layout.state / "server-process.json"

    def _recover_identity(self):
        identity = read_json(self.owner_path)
        if not identity:
            return
        if identity.get("state") == "failed" and identity.get("exited"):
            self.state = "failed"
            self.warning = identity.get("warning") or "The previous Minecraft process failed. See Console & logs."
            return
        try:
            process = psutil.Process(identity["pid"])
            if abs(process.create_time() - identity["created"]) < .1 and process.cwd() == str(self.layout.server):
                if process.cmdline() == identity["command"]:
                    self.identity = identity
                    self.state = "unmanaged"
                    self.warning = "The previously owned Java process is still running. Reopen the original Control Room to stop it, or stop it from its console before restoring/deploying."
        except (psutil.Error, KeyError):
            pass

    def running(self):
        with self._lock:
            if self.process is not None and self.process.poll() is None:
                return True
            if self.identity:
                try:
                    process = psutil.Process(self.identity["pid"])
                    return abs(process.create_time() - self.identity["created"]) < .1 and process.is_running()
                except psutil.Error:
                    return False
            return False

    def record(self, line, *, process=None):
        line = re.sub(r"(?i)(access_token|password|secret|authorization)([=: ]+)\S+", r"\1\2[redacted]", line)
        # Minecraft join logs include addresses; do not copy them into dashboard bundles.
        line = re.sub(r"\[/[^\]]+\]", "[address hidden]", line)
        line = line.rstrip()[:4096]
        with self._lock:
            self.sequence += 1
            self.lines.append({"seq": self.sequence, "at": utcnow(), "text": line,
                               "level": "error" if re.search(r"\b(ERROR|FATAL|Exception|Caused by:)\b", line) else
                                        "warning" if "WARN" in line or "Can't keep up" in line else "info"})
            if self._logger:
                self._logger.info(line)
            # A former reader can still be draining after its JVM has exited.
            # Retain its output, but never let it change a newer process's state.
            if process is not None and self.process is not process:
                return
            if "Done (" in line and "For help" in line and self.state == "starting":
                self.state = "online"
            native_error = re.search(r'\[(?:main|Server thread)/(?:ERROR|FATAL)\]', line)
            fatal = native_error and any(message in line for message in (
                "Encountered an unexpected exception", "Failed to start the minecraft server",
                "Failed to wait for future Registry initialization"))
            if fatal and self.state in ("starting", "online", "failed"):
                self.state = "failed"
                self.warning = line
            match = re.search(r"\b([A-Za-z0-9_]{1,16}) (joined|left) the game", line)
            if match:
                self.events.append({"at": utcnow(), "name": match[1], "event": match[2]})
            if "Overall" in line or "overworld" in line:
                tick = re.search(r"Mean tick time:\s*([\d.]+)\s*ms.*?Mean TPS:\s*([\d.]+)", line)
                if tick and "Overall" in line:
                    self.tick = {"mspt": float(tick[1]), "tps": float(tick[2]), "at": utcnow(),
                                 "source": "NeoForge /neoforge tps, Overall"}
                current = re.search(r"\bOverall:\s*([\d.]+)\s*TPS\s*\(([\d.]+)\s*ms/tick\)", line)
                if current:
                    self.tick = {"mspt": float(current[2]), "tps": float(current[1]), "at": utcnow(),
                                 "source": "NeoForge /neoforge tps, Overall"}

    def _reader(self, process):
        try:
            for line in process.stdout:
                self.record(line, process=process)
        finally:
            code = process.wait()
            with self._lock:
                self.record("Managed Java process exited with code " + str(code), process=process)
                if self.process is process:
                    failed = code != 0 or self.state in ("starting", "failed")
                    if failed and not self.warning:
                        self.warning = ("Minecraft exited before reporting readiness (Java exit code " + str(code) + ")."
                                        if self.state == "starting" else
                                        "Minecraft process failed with Java exit code " + str(code) + ".")
                    self.state = "failed" if failed else "offline"
                    self.identity = None
                    write_json(self.owner_path, {"exited": utcnow(), "code": code,
                                                "state": self.state, "warning": self.warning})

    def start(self, notify=lambda _: None):
        # Keep the complete mutation lease, but do not hold the status lock
        # while integrity scans, reserve checks or the Java probe are running.
        with self.layout.mutation:
            with self._lock:
                if self.running():
                    raise UserError("The server is already running")
            eula = self.layout.server / "eula.txt"
            if not eula.exists() or properties(eula.read_text()).get("eula") != "true":
                raise UserError("The owner must read and accept Minecraft's EULA in Setup before the first start")
            receipt = read_json(self.layout.server / "installed.json")
            lock = read_json(self.layout.home / "packwiz/active.json")
            if not receipt or not lock or receipt.get("pack_sha256") != lock.get("pack_sha256"):
                raise UserError("Install a validated pack release before starting the server")
            from .pack import verify_installed
            problems = verify_installed(self.layout)
            if problems:
                raise UserError("Installation integrity check failed: " + "; ".join(problems[:5]))
            from .atlas import prepare_renderer
            prepare_renderer(self.layout, self.storage)
            from .storage import tree_size
            budgets = self.layout.settings()
            growth = max(0, budgets["world_budget_gib"] * 1024 ** 3 - tree_size(self.layout.world))
            growth += max(0, budgets["cache_budget_gib"] * 1024 ** 3 - tree_size(self.layout.caches))
            self.storage.reserve(growth + 256 * 1024 * 1024)
            options = self.layout.settings()
            java = shutil.which(options["java"])
            if not java:
                raise UserError("Java 21 was not found; set up Java before starting")
            version = subprocess.run([java, "-XshowSettings:properties", "-version"], text=True, capture_output=True, timeout=10,
                                     creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            if not re.search(r'version "21[.\"]', version.stderr + version.stdout):
                raise UserError("This pack requires Java 21")
            # Oracle's javapath shim can spawn a second JVM. Own the actual binary
            # so stdin, process identity and CPU/RSS all refer to Minecraft itself.
            java_home = re.search(r"^\s*java\.home\s*=\s*(.+)$", version.stderr + version.stdout, re.M)
            if java_home:
                actual_java = Path(java_home[1].strip()) / "bin" / ("java.exe" if os.name == "nt" else "java")
                if actual_java.is_file():
                    java = str(actual_java)
            args = self.layout.server / "libraries/net/neoforged/neoforge" / receipt["neoforge"] / ("win_args.txt" if os.name == "nt" else "unix_args.txt")
            if not args.exists():
                raise UserError("NeoForge installation is incomplete; run Repair")
            settings = self.layout.settings()
            command = [java, f"-Xms{settings['initial_heap_gib']}G", f"-Xmx{settings['heap_gib']}G",
                       "-XX:+UseG1GC", "-Xlog:gc*:file=../logs/gc.log:time,level,tags:filecount=3,filesize=5M",
                       "@" + str(args), "nogui"]
            with self._lock:
                # A process/identity can change while the read-only preflight
                # is in progress. Never create a second child over that owner.
                if self.running():
                    raise UserError("The server is already running")
                self._logger = logging.getLogger("awft-server-" + str(self.layout.home))
                self._logger.setLevel(logging.INFO)
                if not self._logger.handlers:
                    handler = logging.handlers.RotatingFileHandler(self.layout.logs / "console.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
                    self._logger.addHandler(handler)
                from .character_secrets import server_environment
                self.process = subprocess.Popen(command, cwd=self.layout.server, stdin=subprocess.PIPE,
                    env=server_environment(self.layout),
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                    bufsize=1, creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW) if os.name == "nt" else 0)
                proc = psutil.Process(self.process.pid)
                self.identity = {"pid": proc.pid, "created": proc.create_time(), "command": command,
                                 "cwd": str(self.layout.server), "at": utcnow()}
                write_json(self.owner_path, self.identity)
                self.started = time.time()
                self.state = "starting"
                self.warning = None
                self.tick.update(tps=None, mspt=None, at=None)
                self._reader_thread = threading.Thread(target=self._reader, args=(self.process,), daemon=True)
                self._reader_thread.start()
                result = {"state": self.state, "pid": proc.pid}
            notify("Java started; waiting for NeoForge to report readiness")
            return result

    def wait_ready(self, timeout=360):
        """Require actual readiness for an owned start; leave a slow live JVM alone."""
        if type(timeout) not in (int, float) or not 0 < timeout <= 360:
            raise UserError("Use a finite Minecraft readiness timeout of at most 360 seconds")
        process = self.process
        if process is None:
            raise UserError("No owned Minecraft startup is available to observe")
        deadline = time.monotonic() + timeout
        while (self.process is process and process.poll() is None
               and self.state == "starting" and time.monotonic() < deadline):
            time.sleep(.1)
        if self.process is not process:
            raise UserError("The owned Minecraft process changed during startup")
        if self.state == "online" and process.poll() is None:
            return self.snapshot()
        if process.poll() is not None and self._reader_thread:
            self._reader_thread.join(timeout=2)
        if self.state == "online" and process.poll() is None:
            return self.snapshot()
        raise UserError(self.warning or
            "Minecraft did not finish starting. A still-running JVM was not stopped or relaunched; see Console & logs.")

    def _write(self, command):
        with self._lock:
            if not self.process or self.process.poll() is not None or not self.process.stdin:
                raise UserError("The server console is not owned by this Control Room process")
            self.process.stdin.write(command + "\n")
            self.process.stdin.flush()

    def stop(self, notify=lambda _: None, timeout=120):
        with self.layout.mutation:
            if not self.running():
                return {"state": "offline"}
            self._write("stop")
            self.state = "stopping"
            notify("Waiting for Minecraft to flush and close the world")
            try:
                self.process.wait(timeout=timeout)
            except subprocess.TimeoutExpired as exc:
                self.warning = "Graceful shutdown has not finished. World preserved; no forced termination was attempted."
                raise UserError(self.warning) from exc
            # Do not infer descendant cleanup from the parent's exit.
            if self.identity:
                try:
                    parent = psutil.Process(self.identity["pid"])
                    if parent.children(recursive=True):
                        raise UserError("A server descendant is still alive; inspect before changing files")
                except psutil.NoSuchProcess:
                    pass
            self.state = "offline"
            return {"state": self.state}

    def restart(self, notify=lambda _: None):
        with self.layout.mutation:
            self.stop(notify=notify)
            return self.start(notify=notify)

    def command(self, command, confirmed=False):
        if not isinstance(command, str) or len(command) > 250 or re.search(r"[\r\n\x00-\x1f]", command):
            raise UserError("Enter a single server command of at most 250 characters")
        command = command.strip().lstrip("/")
        patterns = [r"list", r"neoforge tps", r"seed", r"say .{1,200}",
                    r"difficulty (peaceful|easy|normal|hard)",
                    r"gamerule (keepInventory|doDaylightCycle|doWeatherCycle|mobGriefing|doFireTick|doMobSpawning) (true|false)",
                    r"(whitelist (add|remove)|op|deop|kick) [A-Za-z0-9_]{1,16}",
                    r"spark (tps|healthreport|gcmonitor|profiler (start --timeout (30|60|120)|stop))",
                    r"chunky (pause|cancel|progress)",
                    r"awftbuild (registry|fingerprint|status|cancel)",
                    r"awftbuild worldgen-inputs [a-z0-9][a-z0-9-]{0,63} (true|false)",
                    r"awftbuild (noise|survey) -?\d{1,8} -?\d{1,8} \d{1,4} \d{1,3}",
                    r"awftbuild (place|verify|map|settle) [a-f0-9]{64}"]
        patterns.append(r"data get block -?\d{1,8} -?\d{1,3} -?\d{1,8}(?: [A-Za-z0-9_.]{1,64})?")
        patterns += [r"awftengine (status|cancel)", r"awftengine (setup|commission|close) [a-f0-9]{64}",
                     r"awftengine inspect -?\d{1,8} -?\d{1,3} -?\d{1,8}"]
        patterns += [r"awftharborcraft (status|cancel)",
                     r"awftharborcraft (inspect|create) artistic-harbor-craft-[a-f0-9]{16} [a-f0-9]{64}",
                     r"awftmill (status|cancel)",
                     r"awftattractions (status|cancel)",
                     r"awftattractions (inspect|admit) [a-z0-9-]{1,80} [a-f0-9]{64}"]
        if command.startswith(('awftengine repair-radio ', 'awftbridgeglue ', 'awftimport ', 'awftfountain ', 'awfttrees ', 'awfttreepatch ', 'awftrelocate ', 'awfttransport ', 'awftlife ', 'awftchains ', 'awftbridgetop ', 'awftmill inspect ', 'awftmill resume ')):
            owner = read_json(self.layout.state / 'artistic-owner.json', {})
            settings = self.layout.settings()
            if (owner.get('format') != 'awft-artistic-stage:1'
                    or Path(owner.get('home', '')).resolve() != self.layout.home
                    or settings.get('permanent_world') is not False
                    or settings.get('port') != 25575):
                raise UserError('Native architecture admission belongs to the owned private artistic stage')
            patterns += [r"awftengine repair-radio [a-f0-9]{64}", r"awftbridgeglue (status|cancel)",
                         r"awftbridgeglue retire bridge-refinement-admission-[a-f0-9]{16} [a-f0-9]{64}",
                         r"awftimport (status|cancel)",
                         r"awftimport settle import-joins-[a-f0-9]{16} [a-f0-9]{64}",
                         r"awftfountain (status|cancel)",
                         r"awftfountain (inspect|commission|reset|recover-gate|park-gate) fountain-[a-f0-9]{16} [a-f0-9]{64}",
                         r"awfttrees (status|cancel)",
                         r"awfttrees (describe|grow) trees-[a-f0-9]{16} [a-f0-9]{64}",
                         r"awfttreepatch (status|cancel)",
                         r"awfttreepatch (inspect|grow) treepatch-[a-f0-9]{16} [a-f0-9]{64}",
                         r"awfttransport snapshot [a-z0-9_-]{1,32}",
                         r"awftrelocate (status|cleanup)",
                         r"awftrelocate (inspect|move|inspect-moved|inspect-quarantined|record-conserved) relocation-[a-f0-9]{16} [a-f0-9]{64}",
                         r"awftlife (status|cancel)",
                         r"awftlife (inspect|seed) life-[a-f0-9]{16} [a-f0-9]{64}",
                         r"awftchains (status|cancel)",
                         r"awftchains (create|prepare-create|inspect|verify-restart) chains-[a-f0-9]{16} [a-f0-9]{64}",
                         r"awftbridgetop (status|cancel)",
                         r"awftbridgetop inspect bridge-topside-inspection-[a-f0-9]{16} [a-f0-9]{64}",
                         r"awftmill (inspect|resume) mill-resume-[a-f0-9]{16} [a-f0-9]{64}"]
        if not any(re.fullmatch(pattern, command) for pattern in patterns):
            raise UserError("This command is outside the safe console allowlist; use dedicated controls or the local server console")
        dangerous = re.match(r"(op |deop |kick |whitelist remove |gamerule |difficulty |chunky cancel|awftbuild (place|noise|survey|settle|cancel)|awftengine (setup|commission|close|repair-radio|cancel)|awftharborcraft (create|cancel)|awftmill (commission|resume|cancel)|awftattractions (admit|cancel)|awftbridgeglue (retire|cancel)|awftimport (settle|cancel)|awftfountain (commission|reset|recover-gate|park-gate|cancel)|awfttrees (grow|cancel)|awfttreepatch (grow|cancel)|awftrelocate (move|record-conserved|cleanup)|awftlife (seed|cancel)|awftchains (create|prepare-create|cancel)|awftbridgetop cancel)", command)
        if dangerous and not confirmed:
            raise UserError("Confirm this player or world setting change first")
        self._write(command)
        return {"sent": True, "command": command}

    def probe(self):
        if self.state != "online":
            self.player_info = None
            self.player_info_at = None
            return
        try:
            self.player_info = minecraft_status(self.layout.settings()["port"])
            self.player_info_at = time.time()
            self.player_info_identity = (self.identity or {}).get('pid'), (self.identity or {}).get('created')
            self._last_player_info = self.player_info
            self._last_player_info_at = self.player_info_at
        except (OSError, ValueError, UserError):
            self.player_info = None
            self.player_info_at = None
        if time.monotonic() - self._last_probe >= 30:
            with contextlib.suppress(UserError, OSError):
                self._write("neoforge tps")
            self._last_probe = time.monotonic()

    def snapshot(self):
        with self._lock:
            active = self.running()
            now = time.time()
            tick = dict(self.tick)
            tick_fresh = measurement_freshness(tick.get('at'), now)
            roster_fresh = measurement_freshness(self.player_info_at, now)
            identity = (self.identity or {}).get('pid'), (self.identity or {}).get('created')
            if not active or self.state != 'online':
                for value in (tick_fresh, roster_fresh):
                    value.update(current=False, status='unavailable', reason='No online owned server measurement is available.')
            if self.player_info_identity != identity:
                roster_fresh.update(current=False, status='unavailable',
                                    reason='The status sample does not belong to the current owned server process.')
            if not isinstance(self.player_info, dict):
                roster_fresh.update(current=False, status='unavailable', reason='No current Minecraft status reply is available.')
            known = {}
            if not tick_fresh['current']:
                if tick.get('at'):
                    known['tick'] = dict(tick)
                tick.update(tps=None, mspt=None, at=None)
            status = deepcopy(self.player_info) if roster_fresh['current'] else None
            if status is None and self._last_player_info is not None:
                known['status'] = {'measured_at': self._last_player_info_at,
                                   'data': deepcopy(self._last_player_info)}
            return {"state": self.state if active or self.state == "failed" else "offline",
                    "pid": self.identity.get("pid") if self.identity and active else None,
                    "uptime_seconds": max(0, now - self.started) if active and self.started else None,
                    "tick": tick, "status": status, "warning": self.warning,
                    'freshness': {'evaluated_at': now, 'tick': tick_fresh, 'player_status': roster_fresh},
                    'last_known': known,
                    "events": list(self.events)[-30:]}

    def console(self, after=0, query="", level="all"):
        with self._lock:
            return [x for x in self.lines if x["seq"] > after and query.lower() in x["text"].lower()
                    and (level == "all" or x["level"] == level)][-500:]
