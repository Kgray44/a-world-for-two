"""Build the tiny server-only bridge reproducibly with the pinned installed JDK."""
from __future__ import annotations

import json
import os
import subprocess
import zipfile
from pathlib import Path

from control_room.common import REPO, UserError, digest

BRIDGE_VERSION = '0.6.29'

def build(home, destination, storage):
    storage.reserve(16 * 1024 * 1024, destination)
    if destination.exists():
        raise UserError("Bridge output already exists; use a fresh owned build directory")
    work = destination.parent / "compile-bridge"
    work.mkdir(parents=True)
    classes = work / "classes"
    classes.mkdir()
    # Compile against NeoForge's named server, before the installer intermediates.
    # The vanilla/slim intermediates contain the same classes with obfuscated methods.
    libraries = home / "server/libraries"
    named = sorted(libraries.rglob("*-srg.jar"))
    jars = named + [p for p in sorted(libraries.rglob("*.jar")) if p not in named]
    # Compile-only client signatures; never copied into the bridge artifact.
    client_api=Path(os.environ["APPDATA"])/"PrismLauncher/libraries/net/minecraft/client/1.21.1-20240808.144430/client-1.21.1-20240808.144430-srg.jar"
    if not client_api.is_file() or digest(client_api)!="a649bd3ce77f122d0f83ae1b37b4b303e662470f928b9bee5fbc76580805ffd4":
        raise UserError("The exact installed named 1.21.1 client compile API is required")
    jars.insert(0,client_api)
    bluelib=home/'server/mods/2.4.3-neoforge-1.21.1-bluelib-2.4.3.jar'
    if not bluelib.is_file() or digest(bluelib)!='efcbc58b6f0f06062f4c8c937e049b21be3fab37f76285dd5078b6a927cc486b':
        raise UserError('The exact pinned BlueLib metadata API is required for this bridge')
    jars.append(bluelib)
    # These exact installed APIs are compiler inputs only. Their classes and
    # nested libraries are never copied into the owned bridge artifact.
    api_hashes = {
        'DistantHorizons-3.3.3-1.21.1-fabric-neoforge.jar': '864e70def5b0d54d619b940b66bb2784e91d3f3fc253064fdc1b3fc5786cbfab',
        'lithostitched-1.8.1-neoforge-21.1.jar': 'e0da669fa5facc61a09b9b7bae21b322993de1fcd1eb05787adffb7309598cca',
        'Distant Horizons SeedGen 0.9.1 for 1.21.1 NeoForge.jar': '58469f92f7cf13ff3c2928659ce1a57d7d05314b30e0779cb187b6fbfdb43b4e',
        'create-1.21.1-6.0.10.jar': 'ef87fe5709f1ba1f5b8bb20a2925b5afb4669e178fd6d8bf10c167759eefe37a',
        'overpressure-0.1.7.4.jar': '9c03c26bc50c637dbe1d8b9e19e9c10218687c61d335b36588f11e54805c4cf7',
        'create_hypertube-0.6.0-NEOFORGE.jar': '7bdb8979c7ff7d3b29f7a23771b6ae4870a6dcb7ce2e4a3214fdd6059aacace8',
        'railways-0.2.1+neoforge-mc1.21.1.jar': 'b7636c8b1b0352ed1a130dfe67f8bb574e2fc08803ed1cda4d3ea00505193914',
    }
    for filename, expected in api_hashes.items():
        api = home / 'server/mods' / filename
        if not api.is_file() or digest(api) != expected:
            raise UserError('A pinned native engineering compile API differs: ' + filename)
        jars.append(api)
    nested_hashes = {
        'flywheel-neoforge-1.21.1-1.0.6.jar': '31dda15c205eb596d3b3449ef03f6af7363a6cd35b3da4bfe916b304f9e5337e',
        'ponder-neoforge-1.0.82+mc1.21.1.jar': '0cf4611ad853042b689ac386184c5bbe02950efcffddb49e5f604e82baddb0dc',
        'Registrate-MC1.21-1.3.0+67.jar': '510f4041c41739f1d8ea8850ab8364d3e3a5fada8529beed5d9f479e2523db52',
    }
    import hashlib
    with zipfile.ZipFile(home / 'server/mods/create-1.21.1-6.0.10.jar') as create:
        api_dir = work / 'compile-api'
        api_dir.mkdir()
        for filename, expected in nested_hashes.items():
            member = create.getinfo('META-INF/jarjar/' + filename)
            if member.file_size > 2*1024**2:
                raise UserError('Nested compile API exceeds the finite allocation')
            raw = create.read(member)
            if hashlib.sha256(raw).hexdigest() != expected:
                raise UserError('Pinned nested compile API differs: ' + filename)
            api = api_dir / filename
            api.write_bytes(raw)
            jars.append(api)
    # The actual loader supplies this library; extraction is compile-only.
    universal=libraries/"net/neoforged/neoforge/21.1.262/neoforge-21.1.262-universal.jar"
    with zipfile.ZipFile(universal) as native:
        member=native.getinfo("META-INF/jarjar/mixinextras-neoforge-0.5.5.jar")
        if member.file_size!=727484:
            raise UserError("Pinned MixinExtras compile API size differs")
        raw=native.read(member)
        if hashlib.sha256(raw).hexdigest()!="f0c3e3c1ad835b80e70cb3f78359b71f107f74689523b4fb391f160ee487cfbf":
            raise UserError("Pinned MixinExtras compile API differs")
        api=api_dir/"mixinextras-neoforge-0.5.5.jar"
        api.write_bytes(raw);jars.append(api)
    cp = os.pathsep.join(p.as_posix() for p in jars)
    source = REPO / "compat/control-bridge"
    sources = sorted((source / "src").rglob("*.java"))
    args = work / "javac.args"
    args.write_text('-proc:none\n--release\n21\n-classpath\n"' + cp + '"\n-d\n"' + classes.as_posix() + '"\n' + "\n".join('"' + p.as_posix() + '"' for p in sources) + "\n", encoding="utf-8")
    compiler = Path(r"C:\Program Files\Java\jdk-21.0.10\bin\javac.exe")
    if not compiler.is_file():
        raise UserError("The tested Java 21.0.10 JDK compiler is required")
    result = subprocess.run([str(compiler), "-J-Xmx256m", "@" + str(args)], capture_output=True, text=True, timeout=60,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    (work / "javac.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode:
        raise UserError("Bridge compilation failed: " + result.stderr[:3000])
    with zipfile.ZipFile(destination, "x", zipfile.ZIP_DEFLATED) as archive:
        for root in (classes, source / "resources"):
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    entry = zipfile.ZipInfo(path.relative_to(root).as_posix(), (2026, 1, 1, 0, 0, 0))
                    entry.compress_type = zipfile.ZIP_DEFLATED
                    archive.writestr(entry, path.read_bytes())
        entry = zipfile.ZipInfo("META-INF/MANIFEST.MF", (2026, 1, 1, 0, 0, 0))
        archive.writestr(entry, "Manifest-Version: 1.0\nImplementation-Version: " + BRIDGE_VERSION + "\n\n")
    return {"project_id": "awft:control-bridge", "slug": "awft-control-bridge", "name": "A World for Two Control Bridge",
            "version_id": BRIDGE_VERSION, "version": BRIDGE_VERSION, "provider": "local-build", "release_type": "candidate",
            "filename": destination.name, "url": "https://github.com/Kgray44/a-world-for-two/releases/download/compat-0.1.0/" + destination.name,
            "size": destination.stat().st_size, "hashes": {"sha256": digest(destination)}, "side": "both", "kind": "mod",
            "request": None, "world_sensitive": False, "optional": False, "default": True, "dependencies": [],
            "license": {"id": "MIT"}, "source": "https://github.com/Kgray44/a-world-for-two",
            "selection_reason": "Exact owned server bridge: measured tick/JVM telemetry and lifecycle-safe Chunky listener setup.",
            "status": "Integrated but awaiting runtime validation", "validation": {"metadata": "pass", "jar": "pending", "runtime": "not run"}}
