"""Persistent data policy shared by offline migration and world backups.

Machine-local identities, pending actions, launchers, secrets and caches are never
replayed on another host. All world dimensions and mod-owned server data remain.
"""
from __future__ import annotations

from pathlib import PurePosixPath

ROOTS = ("world", "server", "dashboard", "configs", "packwiz", "backups")
LOCAL_DASHBOARD = {"server-process.json", "test-owner.json", "artistic-owner.json", "prepared-playtest.json",
                   "bridge.json", "atlas-control.json", "service-desired.json", "service-restarts.json"}
SECRET_NAMES = {".env", "accounts.json", "credentials.json", "secrets.json", "openai.dpapi", "playit.toml", "playit-secret.txt"}
BACKUP_DASHBOARD = {"settings.json", "atlas-waypoints.json", "atlas-landmark-notes.json", "atlas-settings.json",
                    "atlas-index.json", "atlas-return-history.json", "atlas-returns.json", "cinematics.json",
                    "cinematic-background.json"}


def backup_allowed(relative):
    parts = PurePosixPath(relative).parts
    if not parts or exclusion(relative):
        return False
    if parts[0] in ("world", "configs"):
        return len(parts) > 1
    if parts[0] == "server":
        return (len(parts) > 2 and parts[1] in ("config", "defaultconfigs", "datapacks")) or relative in (
            "server/server.properties", "server/whitelist.json", "server/ops.json", "server/installed.json")
    if relative == "packwiz/active.json":
        return True
    if parts[0] == "dashboard":
        return len(parts) > 2 and parts[1] in ("characters", "menu-artwork") or len(parts) == 2 and parts[1] in BACKUP_DASHBOARD
    return False


def exclusion(relative, include_backups=False):
    path = PurePosixPath(relative)
    parts = path.parts
    lower = [p.lower() for p in parts]
    if any(p in SECRET_NAMES or p.endswith((".pem", ".key", ".dpapi", ".env")) for p in lower):
        return "machine-local credential; configure separately"
    if path.name == "session.lock":
        return "world lock is recreated by Minecraft"
    if parts[0] == "backups" and not include_backups:
        return "prior backup archives are transferred separately"
    if parts[0] == "server" and len(parts) > 1 and parts[1] in ("libraries", "logs", "crash-reports"):
        return "platform libraries must be installed natively; logs stay on the source"
    if parts[0] == "server" and path.name in ("eula.txt", "run.bat", "run.sh", "user_jvm_args.txt"):
        return "host startup/EULA requires separate owner setup"
    if parts[0] == "dashboard":
        if (path.name in LOCAL_DASHBOARD or path.suffix in (".lock", ".sock")
                or any(p in ("service", "settlement", "atlas-requests", "cinematic-requests") for p in parts[1:])
                or path.name.endswith(("-owner.json", "-process.json", "-control.json"))):
            return "machine-local process identity or pending runtime operation"
    return None
