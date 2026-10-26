"""Owned, bounded dedicated-server smoke tests. Never targets a permanent world."""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import shutil
import re
import time
import uuid
from pathlib import Path

import psutil

from control_room.common import GiB, Layout, REPO, UserError, digest, read_json, utcnow, write_json
from control_room.install import Installer
from control_room.pack import generate_pack
from control_room.server import Server
from control_room.settings import Settings, format_properties
from control_room.storage import Storage, tree_size


def smoke(home, seconds=120, seed="-844223996347473026", profile="full", weather_patch=False, bridge=False):
    parent = Layout(home)
    parent_storage = Storage(parent)
    parent_storage.reserve(2 * GiB)
    consent = read_json(parent.state / "eula-acceptance.json", {})
    if not consent.get("accepted"):
        raise UserError("Owner EULA acceptance for disposable tests is required")
    ident = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + uuid.uuid4().hex[:6]
    layout = Layout(parent.staging / "world-tests" / ident)
    if layout.home.exists():
        raise UserError("Test target must be a new, owned directory")
    layout.create()
    storage = Storage(layout)
    server = Server(layout, storage)
    settings = Settings(layout, storage, server)
    config = layout.settings()
    config.update(world_budget_gib=2, cache_budget_gib=1, project_budget_gib=4)
    layout.save_settings(config)
    settings.initialize()
    installer = Installer(layout, storage, server, settings)
    installer.accept_eula(True)
    write_json(layout.state / "test-owner.json", {"id": ident, "at": utcnow(), "purpose": "disposable world-generation smoke", "owner_source": str(REPO)})
    shutil.copytree(parent.server / "libraries", layout.server / "libraries")
    lock = read_json(REPO / "catalog/lock.json")
    patch_receipt = None
    patched_source = None
    if weather_patch:
        from .weather_patch import build, PATCH_VERSION
        item = next(m for m in lock["mods"] if m["slug"] == "advanced-weather")
        patched_source = layout.staging / ("advancedweather-" + PATCH_VERSION + ".jar")
        patched, patch_receipt = build(parent.caches / "mods" / item["filename"], patched_source, item, storage, parent.server / "libraries")
        lock["mods"] = [patched if m["slug"] == "advanced-weather" else m for m in lock["mods"]]
        for m in lock["mods"]:
            if m["slug"] == "yacl":
                m["side"] = "both"
        lock["version"] += "+weather-patch.1"
    bridge_source = None
    if bridge:
        from .build_bridge import build as build_bridge
        bridge_source = layout.staging / "awft-control-bridge-0.2.0.jar"
        lock["mods"].append(build_bridge(parent.home, bridge_source, storage))
        lock["version"] += "+bridge.1"
    if profile == "terrain-baseline":
        lock["mods"] = [m for m in lock["mods"] if m["slug"] not in ("regions-unexplored", "towns-and-towers")]
        lock["version"] += "+terrain-baseline"
    release = layout.releases / lock["version"]
    if (REPO / "packwiz/config").exists():
        shutil.copytree(REPO / "packwiz/config", release / "config")
    generate_pack(release, lock)
    write_json(release / "lock.json", lock)
    # Reuse verified cached sources; the installer copies them to the owned test server.
    (layout.caches / "mods").mkdir()
    for item in lock["mods"]:
        if item["side"] in ("both", "server") and item["kind"] == "mod":
            source = (patched_source if weather_patch and item["slug"] == "advanced-weather" else
                      bridge_source if bridge and item["slug"] == "awft-control-bridge" else parent.caches / "mods" / item["filename"])
            # Hardlinks only within the same volume; cached bytes are immutable after verification.
            os.link(source, layout.caches / "mods" / item["filename"])
    installer.install_mods(lock, release, print)
    props = settings.get_properties()
    props.update({"level-name": (layout.world / "TestWorld").as_posix(), "level-seed": seed,
                  "server-port": 25575, "view-distance": 6, "simulation-distance": 4,
                  "online-mode": True, "white-list": True, "enforce-whitelist": True})
    from control_room.common import atomic_write
    atomic_write(settings.props_path, format_properties(props))
    write_json(layout.server / "whitelist.json", read_json(parent.server / "whitelist.json", []))
    receipt = {"id": ident, "at": utcnow(), "home": str(layout.home), "profile": profile,
               "seed": seed, "pack_sha256": digest(release / "pack.toml"), "source_pack_sha256": digest(REPO / "packwiz/pack.toml"),
               "tier": "real local dedicated server; no two-player or client graphics proof", "startup": "pending", "samples": []}
    receipt["weather_patch"] = patch_receipt
    started = time.monotonic()
    process = None
    children = []
    try:
        server.start(notify=print)
        process = psutil.Process(server.process.pid)
        process.cpu_percent()
        deadline = time.monotonic() + 360
        while server.state == "starting" and server.running():
            if time.monotonic() > deadline:
                raise UserError("Dedicated startup exceeded the 360-second test budget")
            storage.checkpoint(2 * GiB)
            if tree_size(layout.home) > 3 * GiB:
                raise UserError("Disposable test reached its disk budget")
            if psutil.virtual_memory().available < 1.5 * GiB:
                raise UserError("Host RAM is too low to continue the disposable test safely")
            time.sleep(1)
        if server.state != "online":
            raise UserError("Dedicated startup failed; read the preserved console and crash reports")
        receipt["startup"] = "pass"
        receipt["startup_seconds"] = round(time.monotonic() - started, 3)
        print("Server ready after " + str(receipt["startup_seconds"]) + "s", flush=True)
        # Fixed, bounded coordinate probes: one spawn area and a 3x3 chunk patch away
        # from spawn. This is full chunk generation, explicitly distinct from LODs.
        server._write("forceload add 2048 2048 2080 2080")
        server._write("locate biome terralith:alpine_grove")
        if profile == "full":
            server._write("locate biome regions_unexplored:pine_taiga")
        server._write("locate structure minecraft:village_plains")
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if not server.running():
                raise UserError("Server exited during the stability sample")
            if psutil.virtual_memory().available < 1.5 * GiB:
                raise UserError("Host RAM is too low to continue the sample safely")
            children = process.children(recursive=True)
            server.probe()
            receipt["samples"].append({"at": utcnow(), "rss": process.memory_info().rss,
                "cpu_percent_host": process.cpu_percent() / (psutil.cpu_count() or 1),
                "system_available_ram": psutil.virtual_memory().available,
                "tick": dict(server.tick), "world_bytes": tree_size(layout.world)})
            storage.checkpoint(2 * GiB)
            time.sleep(5)
        server._write("forceload remove all")
        receipt["stability"] = "pass"
    except Exception as exc:
        receipt["error"] = str(exc)
        if receipt["startup"] != "pass":
            receipt["startup"] = "fail"
        print("Test result: " + str(exc), flush=True)
    finally:
        if server.running():
            try:
                server.stop(notify=print)
                receipt["shutdown"] = "pass"
            except Exception as exc:
                receipt["shutdown"] = "fail: " + str(exc)
                if server.state in ("failed", "stopping"):
                    from .test_cleanup import cleanup
                    try:
                        receipt["forced_failed_test_cleanup"] = cleanup(layout.home)
                    except Exception as cleanup_error:
                        receipt["cleanup_error"] = str(cleanup_error)
        else:
            receipt["shutdown"] = "process already exited"
        receipt["world_bytes"] = tree_size(layout.world)
        receipt["descendants_alive"] = [p.pid for p in children if p.is_running()]
        receipt["owned_process_alive"] = server.running()
        receipt["console"] = server.console()
        log = layout.logs / "console.log"
        lines = log.read_text(errors="replace").splitlines() if log.exists() else []
        fatal = [line for line in lines if re.search(r"Uncaught exception in server thread|Encountered an unexpected exception|ModLoadingException: Loading errors|Exception caught during firing event", line)]
        receipt["fatal_log_events"] = fatal[-20:]
        if fatal:
            receipt["error"] = "Fatal lifecycle exceptions were found in the complete log despite the process exit status"
            receipt["shutdown"] = "fail: lifecycle exception; process exited and world bytes were preserved"
        receipt["finished"] = utcnow()
        write_json(layout.logs / "acceptance.json", receipt)
        write_json(REPO / "evidence/runtime" / (ident + ".json"), receipt)
        print(json.dumps({k: v for k, v in receipt.items() if k not in ("samples", "console")}), flush=True)
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", type=Path, default=Path(r"D:\A World for Two"))
    parser.add_argument("--seconds", type=int, default=120)
    parser.add_argument("--seed", default="-844223996347473026")
    parser.add_argument("--profile", choices=["full", "terrain-baseline"], default="full")
    parser.add_argument("--weather-patch", action="store_true")
    parser.add_argument("--bridge", action="store_true")
    args = parser.parse_args()
    if not 30 <= args.seconds <= 1800:
        parser.error("Stability samples must be bounded to 30–1800 seconds")
    result = smoke(args.home, args.seconds, args.seed, args.profile, args.weather_patch, args.bridge)
    raise SystemExit(result.get("startup") != "pass" or "error" in result)


if __name__ == "__main__":
    main()
