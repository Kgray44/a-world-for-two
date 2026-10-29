"""Offline migration preparation. No command transfers a world or starts services."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import shutil
import stat
from pathlib import Path, PurePosixPath, PureWindowsPath

import psutil

from control_room.common import GiB, Layout, UserError, contained, digest, read_json, utcnow, write_json
from control_room.persistence import ROOTS, exclusion
from control_room.settings import format_properties, properties
from control_room.storage import Storage

FORMAT = "awft-snowfall:1"
MAX_FILES = 1_000_000
MAX_MANIFEST = 128 * 1024 * 1024
SECRET = re.compile(r'(?im)(?:^|[,{])\s*["\']?(?:api[_-]?key|access[_-]?token|rcon\.password|password|secret)["\']?\s*[:=]\s*["\']?([^\s"\',}\r\n]+)')


def safe_relative(value):
    if (not isinstance(value, str) or not value or "\\" in value or ":" in value
            or PurePosixPath(value).is_absolute() or PureWindowsPath(value).drive
            or any(p in ("", ".", "..") for p in value.split("/"))
            or any(ord(c) < 32 for c in value)):
        raise UserError("Unsafe migration path")
    return value


def regular(path):
    info = path.lstat()
    if path.is_symlink() or path.is_junction() or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise UserError("Unexpected link or special file: " + str(path))
    return info


def reject_links(path):
    for node in (path, *path.parents):
        if node.is_symlink() or node.is_junction():
            raise UserError("Migration paths cannot contain symlinks or junctions")


def new_destination(path, source):
    path = path.absolute()
    reject_links(path)
    source = source.resolve()
    if path.exists() or path.resolve().is_relative_to(source) or source.is_relative_to(path.resolve()):
        raise UserError("Choose a new destination outside the source; existing paths are never overwritten")
    if not path.parent.is_dir():
        raise UserError("Create the reviewed destination parent first")
    return path


def stopped(layout):
    """A stale receipt is not proof of an offline world."""
    owner = read_json(layout.state / "server-process.json", {})
    if owner.get("pid"):
        try:
            process = psutil.Process(owner["pid"])
            if abs(process.create_time() - owner["created"]) < .1:
                raise UserError("The recorded source Java process is still running")
        except psutil.NoSuchProcess:
            pass
        except (psutil.Error, KeyError) as exc:
            raise UserError("Could not prove that the source process is stopped") from exc
    for process in psutil.process_iter(["name"]):
        try:
            if "java" in (process.info["name"] or "").lower() and Path(process.cwd()).resolve() == layout.server:
                raise UserError("Java still uses this server directory")
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue


@contextlib.contextmanager
def offline_locks(layout):
    """Hold actual Minecraft session locks throughout the snapshot, without writing."""
    stopped(layout)
    with contextlib.ExitStack() as stack:
        if os.name == "posix":
            from control_room.ownership import ProcessLease
            lease = ProcessLease(layout.state / "world-writer.lock")
            stack.callback(lease.close)
        for path in layout.world.rglob("session.lock"):
            regular(path)
            stream = stack.enter_context(path.open("r+b"))
            try:
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                    stack.callback(msvcrt.locking, stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.lockf(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    stack.callback(fcntl.lockf, stream.fileno(), fcntl.LOCK_UN)
            except OSError as exc:
                raise UserError("A world is locked by a writer; no snapshot was made") from exc
        stopped(layout)
        yield


def inventory(layout, max_bytes, include_backups=True):
    if type(max_bytes) is not int or not 0 < max_bytes <= 2048 * GiB:
        raise UserError("Declare a migration bound between 1 byte and 2 TiB")
    reject_links(layout.home)
    records, excluded, directories, seen = [], [], [], set()
    total = 0
    for root_name in ROOTS:
        root = layout.home / root_name
        if not root.exists():
            continue
        reject_links(root)
        for directory, dirs, files in os.walk(root, followlinks=False):
            base = Path(directory)
            for name in list(dirs):
                path = base / name
                reject_links(path)
                rel = safe_relative(path.relative_to(layout.home).as_posix())
                reason = exclusion(rel, include_backups)
                if reason:
                    excluded.append({"path": rel + "/", "reason": reason})
                    dirs.remove(name)
                else:
                    directories.append(rel)
            for name in files:
                path = base / name
                info = regular(path)
                rel = safe_relative(path.relative_to(layout.home).as_posix())
                reason = exclusion(rel, include_backups)
                if reason:
                    excluded.append({"path": rel, "reason": reason})
                    continue
                if rel.casefold() in seen:
                    raise UserError("Case-colliding migration files")
                seen.add(rel.casefold())
                if path.suffix.lower() in (".json", ".toml", ".properties", ".cfg", ".yaml", ".yml", ".txt") or rel.startswith("configs/"):
                    if info.st_size > 16 * 1024 * 1024:
                        raise UserError("Review oversized configuration before migration: " + rel)
                    text = path.read_text(encoding="utf-8-sig", errors="replace")
                    if any(m[1].lower() not in ("false", "none", "null", "disabled") for m in SECRET.finditer(text)):
                        raise UserError("Possible credential requires owner review before export: " + rel)
                total += info.st_size
                if total > max_bytes or len(records) >= MAX_FILES:
                    raise UserError("Migration exceeds the declared allocation or file-count bound")
                sha = digest(path)
                if (info.st_size, info.st_mtime_ns, info.st_ctime_ns) != (path.stat().st_size, path.stat().st_mtime_ns, path.stat().st_ctime_ns):
                    raise UserError("Source changed during inventory: " + rel)
                records.append({"path": rel, "size": info.st_size, "sha256": sha})
    installed = read_json(layout.server / "installed.json", {})
    active = read_json(layout.home / "packwiz/active.json", {})
    lock = read_json(layout.releases / active.get("version", "") / "lock.json", {})
    if installed.get("neoforge") != "21.1.262" or lock.get("minecraft") != "1.21.1" or lock.get("neoforge") != "21.1.262":
        raise UserError("Migration requires the exact reviewed Minecraft 1.21.1 / NeoForge 21.1.262 release")
    if installed.get("pack_sha256") != active.get("pack_sha256"):
        raise UserError("Active pack and installation receipt disagree")
    from control_room.pack import verify_installed
    errors = verify_installed(layout)
    mods = lock.get("mods")
    if not isinstance(mods, list) or not mods:
        raise UserError("Required server mod inventory is missing from the immutable release lock")
    required = {item["filename"] for item in mods if item["side"] in ("both", "server")
                and item["kind"] != "shader" and not (item.get("optional") and not item.get("default", True))}
    if set(installed.get("files", {})) != required:
        errors.append("Required server mods differ from the immutable release inventory")
    if errors:
        raise UserError("Source mod integrity failed: " + "; ".join(errors[:5]))
    if not any(r["path"].startswith("world/") and r["path"].endswith("/level.dat") for r in records):
        raise UserError("No saved world was found in the separate world directory")
    for root in layout.home.iterdir():
        if root.name not in ROOTS:
            excluded.append({"path": root.name + ("/" if root.is_dir() else ""), "reason": "outside persistent roots; owner must review for additional required data"})
    return {"format": FORMAT, "created": utcnow(), "minecraft": "1.21.1", "neoforge": "21.1.262",
            "pack_sha256": active["pack_sha256"], "files": sorted(records, key=lambda x: x["path"]),
            "directories": sorted(set(directories)), "source_bytes": total, "excluded": excluded,
            "state": "offline preparation only; activation requires separate owner authorization"}


def export(layout, destination, max_bytes, confirmation):
    if confirmation != "EXPORT STOPPED " + str(layout.home):
        raise UserError("Owner must confirm EXPORT STOPPED followed by the exact source home")
    destination = new_destination(destination, layout.home)
    with offline_locks(layout):
        manifest = inventory(layout, max_bytes)
        encoded = json.dumps(manifest, indent=2).encode()
        if len(encoded) > MAX_MANIFEST:
            raise UserError("Migration manifest exceeds its limit")
        estimate = manifest["source_bytes"] + len(encoded) + len(manifest["files"]) * 8192 + 1024 * 1024
        storage = Storage(layout)
        storage.reserve(estimate, destination)
        destination.mkdir(mode=0o700)
        write_json(destination / "INCOMPLETE.json", {"at": utcnow(), "state": "incomplete; do not install"})
        try:
            data = destination / "data"
            data.mkdir(mode=0o700)
            for relative in manifest["directories"]:
                contained(data, relative).mkdir(mode=0o700, parents=True, exist_ok=True)
            for record in manifest["files"]:
                source = contained(layout.home, record["path"])
                regular(source)
                target = contained(data, record["path"])
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                with source.open("rb") as src, target.open("xb") as dst:
                    shutil.copyfileobj(src, dst, 1024 * 1024)
                os.chmod(target, 0o600)
                if target.stat().st_size != record["size"] or digest(target) != record["sha256"]:
                    raise UserError("Exported file hash mismatch: " + record["path"])
                storage.checkpoint(estimate, destination)
            # Re-read the complete inventory: changed, missing and newly created data fail.
            final = inventory(layout, max_bytes)
            if final["files"] != manifest["files"] or final["directories"] != manifest["directories"]:
                raise UserError("Source changed during export; incomplete bundle preserved")
            write_json(destination / "manifest.json", manifest)
            sha = digest(destination / "manifest.json")
            verify(destination, sha)
            write_json(destination / "COMPLETE.json", {"manifest_sha256": sha, "at": utcnow()})
            (destination / "INCOMPLETE.json").unlink()
            return {"bundle": str(destination), "manifest_sha256": sha, "bytes": manifest["source_bytes"], "activation": False}
        except BaseException:
            # Preserve failed transfer receipts and all partial bytes for diagnosis.
            raise


def verify(bundle, expected_sha):
    bundle = bundle.absolute()
    reject_links(bundle)
    path = bundle / "manifest.json"
    regular(path)
    if not re.fullmatch(r"[a-f0-9]{64}", expected_sha or "") or path.stat().st_size > MAX_MANIFEST or digest(path) != expected_sha:
        raise UserError("Manifest identity does not match the separately retained SHA-256")
    manifest = read_json(path)
    if manifest.get("format") != FORMAT or manifest.get("minecraft") != "1.21.1" or manifest.get("neoforge") != "21.1.262":
        raise UserError("Unsupported migration version")
    records = manifest.get("files")
    if not isinstance(records, list) or not 1 <= len(records) <= MAX_FILES:
        raise UserError("Invalid migration inventory")
    expected, folded, total = set(), set(), 0
    for record in records:
        relative = safe_relative(record["path"])
        if relative.split("/")[0] not in ROOTS or exclusion(relative, True):
            raise UserError("Unmanaged or machine-local migration entry")
        if relative in expected or relative.casefold() in folded or type(record["size"]) is not int or record["size"] < 0:
            raise UserError("Duplicate or invalid migration entry")
        expected.add(relative)
        folded.add(relative.casefold())
        target = contained(bundle / "data", relative)
        regular(target)
        if target.stat().st_size != record["size"] or digest(target) != record["sha256"]:
            raise UserError("Migration content hash mismatch: " + relative)
        total += record["size"]
    actual = set()
    for directory, dirs, files in os.walk(bundle / "data", followlinks=False):
        for name in dirs:
            reject_links(Path(directory) / name)
        for name in files:
            regular(Path(directory) / name)
            actual.add((Path(directory) / name).relative_to(bundle / "data").as_posix())
    if actual != expected or total != manifest.get("source_bytes"):
        raise UserError("Incomplete transfer or unexpected migration data")
    for relative in manifest.get("directories", []):
        safe_relative(relative)
        target = contained(bundle / "data", relative)
        reject_links(target)
        if not target.is_dir():
            raise UserError("Missing migration directory")
    return manifest


def stage(bundle, destination, expected_sha, max_bytes, project_budget_gib=100, storage_reserve_gib=30):
    """Install a verified bundle only into a fresh, inactive home; never swap saves."""
    if type(max_bytes) is not int or not 0 < max_bytes <= 2048 * GiB:
        raise UserError("Declare a staging allocation between 1 byte and 2 TiB")
    if (type(project_budget_gib) is not int or not 10 <= project_budget_gib <= 2048
            or type(storage_reserve_gib) is not int or not 1 <= storage_reserve_gib <= 1024):
        raise UserError("Invalid destination project budget or storage reserve")
    if (bundle / "INCOMPLETE.json").exists():
        raise UserError("Bundle is marked incomplete")
    complete = read_json(bundle / "COMPLETE.json", {})
    if complete.get("manifest_sha256") != expected_sha:
        raise UserError("Bundle has no matching completion receipt")
    manifest = verify(bundle, expected_sha)
    if manifest["source_bytes"] > max_bytes:
        raise UserError("Staging exceeds its declared byte bound")
    destination = new_destination(destination, bundle)
    # Reserve against the destination's configured budget, not the source volume.
    class StagingLayout(Layout):
        def settings(self):
            return super().settings() | {"project_budget_gib": project_budget_gib, "storage_reserve_gib": storage_reserve_gib}
    layout = StagingLayout(destination)
    storage = Storage(layout)
    estimate = manifest["source_bytes"] + len(manifest["files"]) * 8192 + MAX_MANIFEST + 2 * 1024 * 1024
    storage.reserve(estimate, destination)
    destination.mkdir(mode=0o700)
    write_json(destination / "MIGRATION-INCOMPLETE.json", {"at": utcnow(), "manifest_sha256": expected_sha})
    for relative in manifest.get("directories", []):
        contained(destination, relative).mkdir(mode=0o700, parents=True, exist_ok=True)
    for record in manifest["files"]:
        target = contained(destination, record["path"])
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with contained(bundle / "data", record["path"]).open("rb") as src, target.open("xb") as dst:
            shutil.copyfileobj(src, dst, 1024 * 1024)
        os.chmod(target, 0o600)
        if target.stat().st_size != record["size"] or digest(target) != record["sha256"]:
            raise UserError("Staged file hash mismatch; inactive partial preserved")
        storage.checkpoint(estimate, destination)
    # Keep original settings/properties in a separate historical record before rebinding.
    history = destination / "migration-history"
    history.mkdir(mode=0o700)
    shutil.copy2(bundle / "manifest.json", history / "manifest.json")
    for file in (layout.settings_path, layout.server / "server.properties"):
        if file.exists():
            shutil.copy2(file, history / file.name)
    settings = layout.settings()
    settings.update(hosting_mode="dedicated-ubuntu", server_backend="unix-service", java="java", prism_path="",
                    tunnel_address="", tunnel_provider="unconfigured", service_autostart=False)
    layout.save_settings(settings)
    props_path = layout.server / "server.properties"
    props = properties(props_path.read_text(encoding="utf-8-sig"))
    old = props.get("level-name", "")
    # The complete world root was retained. Rebind only a provably included relative save.
    world_name = PurePosixPath(old.replace("\\", "/")).name
    if not world_name or not (layout.world / world_name / "level.dat").is_file():
        raise UserError("Cannot bind the source level-name to an included world; partial staging preserved")
    props.update({"level-name": (layout.world / world_name).as_posix(), "server-ip": "127.0.0.1",
                  "enable-rcon": "false", "enable-query": "false", "enable-jmx-monitoring": "false",
                  "online-mode": "true", "white-list": "true", "enforce-whitelist": "true"})
    props.pop("rcon.password", None)
    from control_room.common import atomic_write
    atomic_write(props_path, format_properties(props))
    atomic_write(layout.server / "eula.txt", "# Owner acceptance required on this host\neula=false\n")
    write_json(destination / "MIGRATION-STAGED.json", {"at": utcnow(), "manifest_sha256": expected_sha,
               "world_files_verified": True, "activated": False, "next": "native NeoForge libraries, owner EULA, host preflight and explicit activation approval"})
    (destination / "MIGRATION-INCOMPLETE.json").unlink()
    return {"staged_home": str(destination), "activated": False}


def verify_staged(layout):
    marker = read_json(layout.home / "MIGRATION-STAGED.json", {})
    path = layout.home / "migration-history/manifest.json"
    regular(path)
    if (layout.home / "MIGRATION-INCOMPLETE.json").exists() or digest(path) != marker.get("manifest_sha256"):
        raise UserError("Staged migration identity is incomplete or changed")
    manifest = read_json(path)
    if manifest.get("format") != FORMAT:
        raise UserError("Invalid staged migration manifest")
    changed = {"server/server.properties", "dashboard/settings.json"}
    for record in manifest["files"]:
        if record["path"] in changed:
            continue
        target = contained(layout.home, safe_relative(record["path"]))
        regular(target)
        if target.stat().st_size != record["size"] or digest(target) != record["sha256"]:
            raise UserError("Staged persistent data differs: " + record["path"])
    return marker


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("inventory", "export"):
        command = sub.add_parser(action)
        command.add_argument("--home", type=Path, required=True)
        command.add_argument("--max-bytes", type=int, required=True)
        if action == "export":
            command.add_argument("--destination", type=Path, required=True)
            command.add_argument("--confirmation", required=True)
    for action in ("verify", "stage"):
        command = sub.add_parser(action)
        command.add_argument("--bundle", type=Path, required=True)
        command.add_argument("--manifest-sha256", required=True)
        if action == "stage":
            command.add_argument("--destination", type=Path, required=True)
            command.add_argument("--max-bytes", type=int, required=True)
            command.add_argument("--project-budget-gib", type=int, default=100)
            command.add_argument("--storage-reserve-gib", type=int, default=30)
    args = parser.parse_args()
    try:
        if args.action == "inventory":
            result = inventory(Layout(args.home), args.max_bytes)
        elif args.action == "export":
            result = export(Layout(args.home), args.destination, args.max_bytes, args.confirmation)
        elif args.action == "verify":
            value = verify(args.bundle, args.manifest_sha256)
            result = {"verified": True, "files": len(value["files"]), "source_bytes": value["source_bytes"]}
        else:
            result = stage(args.bundle, args.destination, args.manifest_sha256, args.max_bytes,
                           args.project_budget_gib, args.storage_reserve_gib)
        print(json.dumps(result, indent=2))
    except (UserError, OSError, ValueError, KeyError) as exc:
        parser.exit(1, "Snowfall: " + str(exc) + "\n")


if __name__ == "__main__":
    main()
