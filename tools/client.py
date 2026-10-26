"""Prepare an owned Prism test instance without touching existing instances or accounts."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import time
from pathlib import Path

from control_room.common import Layout, REPO, UserError, atomic_write, digest, read_json, utcnow, write_json
from control_room.pack import generate_pack, validate_jars
from control_room.storage import Storage


def prepare(home, player="KG", server_port=None):
    layout = Layout(home)
    storage = Storage(layout)
    lock = read_json(REPO / "catalog/lock.json")
    storage.reserve(sum(m["size"] for m in lock["mods"]) + 64 * 1024 * 1024)
    ident = "AWFT_Check_" + time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    instance = layout.home / "instances" / ident
    if instance.exists():
        raise UserError("Owned test instance must be new")
    minecraft = instance / ".minecraft"
    minecraft.mkdir(parents=True)
    weather = next(m for m in lock["mods"] if m["slug"] == "advanced-weather")
    artifact = None
    provenance = weather.get('repair')
    if weather.get('provider') != 'local-patch':
        from .weather_patch import build, PATCH_VERSION
        artifact = instance / "build" / ("advancedweather-" + PATCH_VERSION + ".jar")
        repaired, provenance = build(layout.caches / "mods" / weather["filename"], artifact, weather, storage, layout.server / "libraries")
        repaired["url"] = "https://github.com/Kgray44/a-world-for-two/releases/download/compat-0.1.0/" + artifact.name
        lock["mods"] = [repaired if m["slug"] == "advanced-weather" else m for m in lock["mods"]]
        for mod in lock["mods"]:
            if mod["slug"] == "yacl":
                mod["side"] = "both"
        lock["version"] += "+client-check.1"
    lock["validation"] = "Owned candidate client check; not a public release"
    pack = minecraft / "packwiz"
    shutil.copytree(REPO / "packwiz/config", pack / "config", dirs_exist_ok=True)
    generate_pack(pack, lock)
    write_json(pack / "lock.json", lock)
    installed = []
    for mod in lock["mods"]:
        if mod["side"] == "server" or mod.get("optional") and not mod.get("default", True):
            continue
        source = artifact if artifact and mod["slug"] == "advanced-weather" else layout.caches / "mods" / mod["filename"]
        folder = {"mod": "mods", "shader": "shaderpacks", "resourcepack": "resourcepacks"}[mod["kind"]]
        target = minecraft / folder / mod["filename"]
        target.parent.mkdir(exist_ok=True)
        algorithm = "sha512" if "sha512" in mod["hashes"] else "sha256" if "sha256" in mod["hashes"] else "sha1"
        if digest(source, algorithm) != mod["hashes"][algorithm]:
            raise UserError("Client source hash differs: " + mod["filename"])
        shutil.copy2(source, target)
        installed.append({"file": target.relative_to(minecraft).as_posix(), "sha256": digest(target), "size": target.stat().st_size})
        storage.checkpoint(sum(m["size"] for m in lock["mods"]))
    shutil.copytree(REPO / "packwiz/config", minecraft / "config", dirs_exist_ok=True)
    from control_room.cinematics import Cinematics
    menu = Cinematics(layout, storage, None, None)
    if server_port is not None and (type(server_port) is not int or not 1024 <= server_port <= 65535):
        raise UserError('Choose a valid local test server port')
    for relative, raw in menu.files().items():
        if server_port is not None and relative.endswith('awft_title.txt'):
            import re
            raw=re.sub(rb'(\[action_type:joinserver\]\s*=\s*)[^\r\n]+',lambda match:match[1]+('127.0.0.1:'+str(server_port)).encode(),raw)
        atomic_write(minecraft / relative, raw)
    write_json(instance / 'awft-menu.json', {'at': utcnow(), 'background_sha256': menu.current()['sha256'], 'status': 'installed; client visual validation pending'})
    # These are native vanilla 1.21.1 option names. Shaders remain off for startup.
    fresh = next((m["filename"] for m in lock["mods"] if m["kind"] == "resourcepack"), None)
    import json
    options = "renderDistance:8\nsimulationDistance:5\nmaxFps:60\nenableVsync:true\n"
    if fresh:
        options += "resourcePacks:" + json.dumps(["vanilla", "file/" + fresh]) + "\n"
    atomic_write(minecraft / "options.txt", options)
    components = {"formatVersion": 1, "components": [
        {"uid": "org.lwjgl3", "version": "3.3.3", "dependencyOnly": True},
        {"uid": "net.minecraft", "version": "1.21.1", "important": True},
        {"uid": "net.neoforged", "version": lock["neoforge"]}]}
    write_json(instance / "mmc-pack.json", components)
    heap_mib=6144 if player=='KG' else 4096
    atomic_write(instance / "instance.cfg", "[General]\nInstanceType=OneSix\nname=A World for Two - " + player + " client check\n"
        "OverrideMemory=true\nMinMemAlloc=1024\nMaxMemAlloc="+str(heap_mib)+"\n"
        "OverrideJavaLocation=true\nJavaPath=C:/Program Files/Java/jdk-21.0.10/bin/javaw.exe\n"
        "OverrideCommands=true\nPreLaunchCommand=\nWrapperCommand=\nPostExitCommand=\n"
        "OverrideWindow=true\nLaunchMaximized=false\nMinecraftWinWidth=1280\nMinecraftWinHeight=800\n")
    receipt = {"format": "awft-owned-client:1", "id": ident, "at": utcnow(), "player": player,
        "root": str(instance), "source_pack_sha256": digest(REPO / "packwiz/pack.toml"),
        "pack_sha256": digest(pack / "pack.toml"), "files": installed, "weather_patch": provenance,
        "maximum_heap_mib": heap_mib, "test_server_port": server_port,
        "scope": "Owned client startup check, not gameplay, shader performance or remote sync acceptance"}
    write_json(instance / "awft-owned.json", receipt)
    # A fresh junction registers this owned D: instance with the existing Prism.
    # It changes no prior instance, launcher preference or account file.
    prism_instances = Path(os.environ["APPDATA"]) / "PrismLauncher/instances"
    registration = prism_instances / ident
    storage.reserve(65536, registration)
    if registration.exists():
        raise UserError("Prism registration path already exists")
    prism_instances.mkdir(parents=True, exist_ok=True)
    os.mkdir(registration)
    os.rmdir(registration)
    # Use PowerShell's native junction operation, with separately passed arguments.
    script = "param($link,$target) New-Item -ItemType Junction -Path $link -Target $target -ErrorAction Stop | Out-Null"
    helper = instance / "register.ps1"
    atomic_write(helper, script)
    result = subprocess.run(["powershell.exe", "-NoProfile", "-File", str(helper), str(registration), str(instance)],
        capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise UserError("Prism registration failed: " + result.stderr[:1000])
    write_json(layout.state / "owned-client.json", receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", type=Path, default=Path(r"D:\A World for Two"))
    parser.add_argument("--player", choices=["KG", "Sera"], default="KG")
    parser.add_argument("--launch", action="store_true")
    parser.add_argument("--server-port", type=int)
    args = parser.parse_args()
    receipt = prepare(args.home, args.player, args.server_port)
    print("Owned Prism instance: " + receipt["id"], flush=True)
    if args.launch:
        prism = Path(os.environ["LOCALAPPDATA"]) / "Programs/PrismLauncher/prismlauncher.exe"
        process = subprocess.Popen([str(prism), "--launch", receipt["id"]],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
        print("Launch requested through Prism; verify the owned client's log before claiming startup.", flush=True)


if __name__ == "__main__":
    main()
