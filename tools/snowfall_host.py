"""Explicit Ubuntu preparation, service installation and gated activation.

Preflight never modifies the host. Render writes reviewed artifacts only.
Install changes only the two named AWFT units. Activation is a separate command.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

import psutil

from control_room.common import GiB, Layout, UserError, atomic_write, digest, read_json, utcnow, write_json
from control_room.storage import Storage

UNITS = ("awft-minecraft.service", "awft-control-room.service")


def absolute(value):
    # Deliberately constrain unit paths rather than guessing systemd quoting.
    if not isinstance(value, str) or not re.fullmatch(r"/[A-Za-z0-9_./-]+", value) or ".." in Path(value).parts or "%" in value:
        raise UserError("Use an absolute Linux service path without spaces, specifiers or parent traversal")
    if value == "/":
        raise UserError("The filesystem root is not a service data directory")
    return value


def configuration(value):
    if not isinstance(value, dict):
        raise UserError("Host configuration must be a JSON object")
    result = dict(value)
    for key in ("home", "source", "python"):
        result[key] = absolute(value.get(key))
    for key in ("user", "group"):
        if not isinstance(value.get(key), str) or not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", value[key]) or value[key] == "root":
            raise UserError("Choose an existing dedicated nonroot service user and group")
    bounds = {"dashboard_port": (1024, 65535, 8765), "storage_reserve_gib": (1, 1024, 30),
              "project_budget_gib": (10, 2048, 100), "cpu_weight": (1, 10000, 50),
              "io_weight": (1, 10000, 50), "memory_high_gib": (10, 128, 12), "nice": (0, 19, 5)}
    for key, (minimum, maximum, default) in bounds.items():
        number = value.get(key, default)
        if type(number) is not int or not minimum <= number <= maximum:
            raise UserError("Invalid host configuration: " + key)
        result[key] = number
    if value.get("autostart", False) not in (True, False):
        raise UserError("autostart must be a boolean")
    result["autostart"] = value.get("autostart", False) is True
    home, source = Path(result["home"]), Path(result["source"])
    if len((result["home"] + "/dashboard/service/console.sock").encode()) >= 108:
        raise UserError("Choose a shorter runtime path for the Linux Unix socket limit")
    if home == source or source.is_relative_to(home) or home.is_relative_to(source):
        raise UserError("Keep immutable application source and persistent runtime data separate")
    return result


def preflight(config):
    config = configuration(config)
    checks = []
    def check(name, passed, detail):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})
    linux = platform.system() == "Linux"
    release = platform.freedesktop_os_release() if linux else {}
    check("ubuntu", release.get("ID") == "ubuntu", release.get("PRETTY_NAME", platform.platform()))
    check("python", sys.version_info >= (3, 12), platform.python_version())
    check("systemd", linux and Path("/run/systemd/system").is_dir(), shutil.which("systemctl"))
    check("nonroot", hasattr(os, "geteuid") and os.geteuid() != 0, "Run preflight as the selected service account")
    account = None
    if linux:
        import grp
        import pwd
        try:
            account = pwd.getpwnam(config["user"])
            group = grp.getgrnam(config["group"])
            check("account", account.pw_uid == os.geteuid() and account.pw_uid != 0 and group.gr_gid == os.getegid(),
                  "Current user and primary group must match the configured dedicated account")
        except KeyError:
            check("account", False, "Snow must approve/create the dedicated account and group")
    for key in ("home", "source", "python"):
        path = Path(config[key])
        linked = any(p.is_symlink() or p.is_junction() for p in (path, *path.parents))
        check(key + "_path", path.exists() and not linked, str(path))
    data = Path(config["home"])
    if data.exists() and account:
        check("data_owner", data.stat().st_uid == account.pw_uid and os.access(data, os.R_OK | os.W_OK | os.X_OK),
              "Runtime must belong to the service account; do not recursively change unrelated paths")
    if Path(config["python"]).is_file():
        try:
            result = subprocess.run([config["python"], "-c", "import sys,psutil,PIL,nbtlib; assert sys.version_info >= (3,12); print(sys.version.split()[0])"],
                                    capture_output=True, text=True, timeout=15)
            check("service_python", result.returncode == 0, result.stdout.strip() or "Install the project's pinned dependencies in the chosen virtualenv")
        except (OSError, subprocess.TimeoutExpired):
            check("service_python", False, "Service Python could not be executed")
    java = shutil.which(Layout(data).settings()["java"])
    version = "not found"
    if java:
        try:
            result = subprocess.run([java, "-version"], capture_output=True, text=True, timeout=10)
            version = (result.stderr + result.stdout)[:1024]
        except (OSError, subprocess.TimeoutExpired):
            version = "Java probe failed"
    check("java21", bool(re.search(r'version "21[.\"]', version)), version.splitlines()[0])
    memory = psutil.virtual_memory()
    check("available_memory", memory.available >= 10 * GiB, {"total": memory.total, "available": memory.available,
          "note": "8 GiB heap plus headroom; shared Plex workload still requires sustained measurement"})
    existing = data
    while not existing.exists():
        existing = existing.parent
    disk = shutil.disk_usage(existing)
    check("storage", disk.free > config["storage_reserve_gib"] * GiB, {"free": disk.free, "total": disk.total,
          "filesystem": "owner must confirm filesystem and HDD/SSD layout; not inferred"})
    return {"at": utcnow(), "ready": all(x["passed"] for x in checks), "checks": checks,
            "unchanged": "No users, packages, services, firewall, SSH, Plex or network configuration was modified"}


def render(config, destination):
    config = configuration(config)
    destination = destination.absolute()
    if destination.exists():
        raise UserError("Render into a new review directory; prior artifacts are preserved")
    layout = Layout(destination)
    Storage(layout).reserve(1024 * 1024, destination)
    destination.mkdir(mode=0o700)
    common = (f"User={config['user']}\nGroup={config['group']}\nWorkingDirectory={config['source']}\n"
              f"Environment=AWFT_HOME={config['home']}\nEnvironment=PYTHONDONTWRITEBYTECODE=1\nUMask=0077\n"
              "NoNewPrivileges=yes\nPrivateTmp=yes\nProtectSystem=strict\nProtectHome=read-only\n"
              f"ReadWritePaths={config['home']}\nRestrictSUIDSGID=yes\nProtectKernelTunables=yes\n"
              "ProtectKernelModules=yes\nProtectControlGroups=yes\nStandardOutput=journal\nStandardError=journal\n")
    minecraft = ("[Unit]\nDescription=A World for Two Minecraft console owner\nAfter=network.target\n"
                 "StartLimitIntervalSec=900\nStartLimitBurst=3\n\n[Service]\nType=exec\n" + common +
                 f"ExecStart={config['python']} -B -m control_room.service --home {config['home']}\n"
                 "Restart=no\nKillMode=mixed\nTimeoutStopSec=180\nSendSIGKILL=no\n"
                 f"Nice={config['nice']}\nCPUWeight={config['cpu_weight']}\nIOWeight={config['io_weight']}\n"
                 f"MemoryHigh={config['memory_high_gib']}G\n\n[Install]\nWantedBy=multi-user.target\n")
    dashboard = ("[Unit]\nDescription=A World for Two loopback Control Room\nAfter=awft-minecraft.service\n"
                 "Wants=awft-minecraft.service\nStartLimitIntervalSec=900\nStartLimitBurst=3\n\n[Service]\nType=exec\n" + common +
                 f"ExecStart={config['python']} -B -m control_room run --home {config['home']} --port {config['dashboard_port']}\n"
                 "Restart=on-failure\nRestartSec=10\nTimeoutStopSec=90\n\n[Install]\nWantedBy=multi-user.target\n")
    for name, text in zip(UNITS, (minecraft, dashboard)):
        atomic_write(destination / name, text)
    write_json(destination / "host.json", config)
    write_json(destination / "PREPARED.json", {"format": "awft-systemd:1", "at": utcnow(),
               "files": {name: digest(destination / name) for name in (*UNITS, "host.json")}, "activated": False})
    return {"prepared": str(destination), "activated": False}


def prepared(directory):
    receipt = read_json(directory / "PREPARED.json", {})
    if receipt.get("format") != "awft-systemd:1" or set(receipt.get("files", {})) != {*UNITS, "host.json"}:
        raise UserError("Invalid prepared systemd bundle")
    for name, sha in receipt["files"].items():
        path = directory / name
        if path.is_symlink() or path.is_junction() or digest(path) != sha:
            raise UserError("Prepared unit/configuration changed; render and review again")
    return configuration(read_json(directory / "host.json"))


def install_units(directory, confirmation):
    prepared(directory)
    if confirmation != "INSTALL AWFT UNITS" or platform.system() != "Linux" or os.geteuid() != 0:
        raise UserError("Snow must explicitly run unit installation as root with INSTALL AWFT UNITS")
    target = Path("/etc/systemd/system")
    for name in UNITS:
        path = target / name
        if path.is_symlink():
            raise UserError("Refusing to replace a linked unit")
        if path.exists() and path.read_bytes() != (directory / name).read_bytes():
            raise UserError("Existing AWFT unit differs; stop, preserve and review its upgrade explicitly")
    subprocess.run(["systemd-analyze", "verify", *(str(directory / x) for x in UNITS)], check=True, timeout=30)
    for name in UNITS:
        path = target / name
        if not path.exists():
            with path.open("xb") as stream:
                stream.write((directory / name).read_bytes())
            os.chmod(path, 0o644)
    subprocess.run(["systemctl", "daemon-reload"], check=True, timeout=30)
    return {"installed": list(UNITS), "enabled": False, "started": False}


def configure(directory, confirmation):
    config = prepared(directory)
    layout = Layout(Path(config["home"]))
    if confirmation != "CONFIGURE " + str(layout.home):
        raise UserError("Confirm CONFIGURE followed by the exact inactive runtime home")
    from tools.snowfall import stopped, verify_staged
    stopped(layout)
    verify_staged(layout)
    result = preflight(config)
    if not result["ready"]:
        raise UserError("Host preflight failed; inspect its individual checks")
    Storage(layout).reserve(1024 * 1024)
    settings = layout.settings()
    settings.update(hosting_mode="dedicated-ubuntu", server_backend="unix-service", heap_gib=8, initial_heap_gib=2,
                    storage_reserve_gib=config["storage_reserve_gib"], project_budget_gib=config["project_budget_gib"],
                    service_autostart=config["autostart"])
    layout.save_settings(settings)
    return {"configured": str(layout.home), "activated": False}


def prepare_libraries(home, confirmation):
    layout = Layout(home)
    if confirmation != "PREPARE LIBRARIES " + str(layout.home):
        raise UserError("Confirm PREPARE LIBRARIES followed by the exact inactive home")
    from tools.snowfall import stopped, verify_staged
    from control_room.install import Installer
    stopped(layout)
    verify_staged(layout)
    if platform.system() != "Linux" or os.geteuid() == 0:
        raise UserError("Prepare native libraries as the dedicated nonroot Linux account")
    storage = Storage(layout)
    storage.reserve(2 * GiB)
    Installer(layout, storage, None, None).install_neoforge("21.1.262")
    return {"native_libraries": "prepared", "eula_accepted": False, "activated": False}


def validate_activation(directory):
    config = prepared(directory)
    result = preflight(config)
    if not result["ready"]:
        raise UserError("Host preflight failed; inspect preflight output")
    layout = Layout(Path(config["home"]))
    from tools.snowfall import stopped, verify_staged
    from control_room.pack import verify_installed
    from control_room.settings import properties
    stopped(layout)
    marker = verify_staged(layout)
    settings = layout.settings()
    if settings["hosting_mode"] != "dedicated-ubuntu" or settings["server_backend"] != "unix-service":
        raise UserError("Configure the dedicated backend before activation")
    for key in ("storage_reserve_gib", "project_budget_gib"):
        if settings[key] != config[key]:
            raise UserError("Configured host storage policy differs from the reviewed units")
    eula = layout.server / "eula.txt"
    if not eula.exists() or properties(eula.read_text()).get("eula") != "true":
        raise UserError("The owner must personally accept the EULA before activation")
    args = layout.server / "libraries/net/neoforged/neoforge/21.1.262/unix_args.txt"
    if not args.is_file() or verify_installed(layout):
        raise UserError("Native libraries or required server mod hashes are not ready")
    Storage(layout).reserve(256 * 1024 * 1024)
    return {"ready": True, "manifest_sha256": marker["manifest_sha256"], "at": utcnow()}


def activate(directory, confirmation):
    config = prepared(directory)
    if platform.system() != "Linux" or os.geteuid() != 0:
        raise UserError("Snow must run the separately authorized activation command as root")
    marker = read_json(Path(config["home"]) / "MIGRATION-STAGED.json", {})
    if confirmation != "ACTIVATE " + str(marker.get("manifest_sha256")) or not marker.get("manifest_sha256"):
        raise UserError("Activation requires ACTIVATE followed by the exact reviewed migration manifest SHA-256")
    for name in UNITS:
        target = Path("/etc/systemd/system") / name
        if not target.is_file() or target.is_symlink() or digest(target) != digest(directory / name):
            raise UserError("Installed units do not match the prepared review bundle")
    if any(subprocess.run(["systemctl", "is-active", "--quiet", name], timeout=10).returncode == 0 for name in UNITS):
        raise UserError("An AWFT service is already active; inspect status instead of replaying activation")
    subprocess.run(["runuser", "-u", config["user"], "-g", config["group"], "--", config["python"], "-B", "-m",
                    "tools.snowfall_host", "approve-activation", "--prepared", str(directory.resolve()), "--confirmation", confirmation],
                   cwd=config["source"], check=True, timeout=300)
    # This is the only command that enables/starts services; never called by render/install.
    subprocess.run(["systemctl", "enable", "--now", *UNITS], check=True, timeout=60)
    return {"services_started": list(UNITS), "minecraft_autostart": config["autostart"],
            "runtime_acceptance": "pending actual world, shutdown, reboot, SSH and multiplayer checks"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("preflight", "render"):
        p = sub.add_parser(action)
        p.add_argument("--config", type=Path, required=True)
        if action == "render":
            p.add_argument("--destination", type=Path, required=True)
    for action in ("install-units", "configure", "activate", "validate-activation", "approve-activation"):
        p = sub.add_parser(action)
        p.add_argument("--prepared", type=Path, required=True)
        if action != "validate-activation":
            p.add_argument("--confirmation", required=True)
    p = sub.add_parser("prepare-libraries")
    p.add_argument("--home", required=True, type=Path)
    p.add_argument("--confirmation", required=True)
    args = parser.parse_args()
    try:
        if args.action == "preflight":
            result = preflight(read_json(args.config))
            print(json.dumps(result, indent=2))
            return 0 if result["ready"] else 1
        if args.action == "render":
            result = render(read_json(args.config), args.destination)
        elif args.action == "configure":
            result = configure(args.prepared, args.confirmation)
        elif args.action == "prepare-libraries":
            result = prepare_libraries(args.home, args.confirmation)
        elif args.action == "activate":
            result = activate(args.prepared, args.confirmation)
        elif args.action == "validate-activation":
            result = validate_activation(args.prepared)
        elif args.action == "approve-activation":
            result = validate_activation(args.prepared)
            if args.confirmation != "ACTIVATE " + result["manifest_sha256"]:
                raise UserError("Activation confirmation does not match the reviewed manifest")
            config = prepared(args.prepared)
            layout = Layout(Path(config["home"]))
            Storage(layout).reserve(65536)
            write_json(layout.home / "MIGRATION-ACTIVATED.json", {"at": utcnow(), "manifest_sha256": result["manifest_sha256"],
                       "approval": "explicit local activation command", "runtime_acceptance": "pending"})
        else:
            result = install_units(args.prepared, args.confirmation)
        print(json.dumps(result, indent=2))
        return 0
    except (UserError, OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        parser.exit(1, "Snowfall host: " + str(exc) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
