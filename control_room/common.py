from __future__ import annotations

import contextlib
import hashlib
import json
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath

REPO = Path(__file__).resolve().parents[1]
GiB = 1024 ** 3


class UserError(Exception):
    """An actionable, safe-to-display failure."""


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def atomic_write(path: Path, content: bytes | str):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = content.encode("utf-8") if isinstance(content, str) else content
    fd, name = tempfile.mkstemp(prefix=".awft-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(name)


def write_json(path: Path, value):
    atomic_write(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def digest(path: Path, algorithm="sha256"):
    hasher = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def contained(root: Path, relative: str) -> Path:
    relative_path = Path(relative)
    if relative_path.is_absolute() or relative_path.drive or PureWindowsPath(relative).drive or ".." in relative_path.parts:
        raise UserError("Path must stay inside the selected project directory")
    lexical = root / relative_path
    # Inspect the original path before resolve() erases links and junctions.
    for parent in [lexical, *lexical.parents]:
        if parent == root:
            break
        if parent.is_symlink() or parent.is_junction():
            raise UserError("Linked directories are not allowed for managed files")
    candidate = lexical.resolve()
    if not candidate.is_relative_to(root.resolve()) or candidate == root.resolve():
        raise UserError("Path must stay inside the selected project directory")
    # Resolve follows Windows junctions; never allow an existing symlink along a path.
    for parent in [candidate, *candidate.parents]:
        if parent == root.resolve():
            break
        if parent.is_symlink() or parent.is_junction():
            raise UserError("Linked directories are not allowed for managed files")
    return candidate


class Layout:
    def __init__(self, home: Path):
        self.home = Path(home).expanduser().resolve()
        self.server = self.home / "server"
        self.world = self.home / "world"
        self.state = self.home / "dashboard"
        self.backups = self.home / "backups"
        self.staging = self.home / "staging"
        self.caches = self.home / "caches"
        self.logs = self.home / "logs"
        self.releases = self.home / "packwiz/releases"
        self.mutation = threading.RLock()

    def create(self):
        for name in ["server", "world", "dashboard", "configs", "backups", "logs", "caches",
                     "packwiz/releases", "instances", "exports", "staging"]:
            (self.home / name).mkdir(parents=True, exist_ok=True)

    @property
    def settings_path(self):
        return self.state / "settings.json"

    def settings(self):
        default = {"heap_gib": 8, "initial_heap_gib": 2, "java": "java", "port": 25565,
                   "max_players": 2, "backup_interval_hours": 6, "backup_keep": 7,
                   "backup_compression": True, "project_budget_gib": 100,
                   "cache_budget_gib": 8, "world_budget_gib": 40,
                   "prism_path": "", "tunnel_address": "", "tunnel_provider": "playit",
                   "player_names": {"KG": "", "Sera": ""}, "sample_seconds": 5,
                   "hosting_mode": "local-windows", "server_backend": "child",
                   "storage_reserve_gib": 30, "service_autostart": False,
                   "service_restart_limit": 3, "service_restart_window_seconds": 900,
                   "service_restart_delay_seconds": 30,
                   "permanent_world": False, "world_created": False}
        return default | read_json(self.settings_path, {})

    def save_settings(self, value):
        write_json(self.settings_path, value)
