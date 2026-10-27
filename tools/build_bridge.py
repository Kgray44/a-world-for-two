"""Build the tiny server-only bridge reproducibly with the pinned installed JDK."""
from __future__ import annotations

import json
import os
import subprocess
import zipfile
from pathlib import Path

from control_room.common import REPO, UserError, digest

BRIDGE_VERSION = '0.6.17'

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
    bluelib=home/'server/mods/2.4.3-neoforge-1.21.1-bluelib-2.4.3.jar'
    if not bluelib.is_file() or digest(bluelib)!='efcbc58b6f0f06062f4c8c937e049b21be3fab37f76285dd5078b6a927cc486b':
        raise UserError('The exact pinned BlueLib metadata API is required for this bridge')
    jars.append(bluelib)
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
