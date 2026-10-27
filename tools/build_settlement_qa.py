"""Build the separate, release-excluded native framebuffer QA helper."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
import zipfile
from pathlib import Path

from control_room.common import Layout, REPO, UserError, digest, utcnow
from control_room.storage import Storage, tree_size

VERSION = "0.1.6"
MAX_BYTES = 16 * 1024**2
JDK = Path(r"C:\Program Files\Java\jdk-21.0.10\bin")
API_PINS = {
    "xaeroworldmap-neoforge-1.21.1-1.47.0.jar": (1427078, "6a42b6f01bd96b496e5fcc07d4541bad1a699d9ec8ad58ad40d5dcfe23a7d4c7"),
    "maphorizons-1.1.0-awft.2.jar": (121569, "cd5f5a0d41f02d1c720b0ce3f603f0cc3c3f92db02aa8226565b4e394fbc7ef4"),
    "xaerolib-neoforge-1.21.1-1.7.3.jar": (568376, "010dc4c2ff154aa8ba04c779600658b77ac0003eee3a98ac9453f6e7acd28898"),
}


def build(home=Path(r"D:\A World for Two"), *, maphorizons_api=None):
    layout = Layout(home)
    storage = Storage(layout)
    reserve = storage.reserve(MAX_BYTES)
    work = layout.staging / ("settlement-qa-build-" + str(time.time_ns()))
    classes = work / "classes"
    classes.mkdir(parents=True)
    temporary = work / "tmp"
    temporary.mkdir()
    source = REPO / "compat/qa-client"
    receipt = {"format": "awft-native-qa-build:2", "status": "failed", "version": VERSION,
               "created_at": utcnow(), "release_excluded": True, "reserve": reserve,
               "maximum_additional_bytes": MAX_BYTES, "installed": False, "game_started": False,
               "native_map_ui_linkage": "pending", "coarse_only_map_proof": "pending"}

    def bounded_write(path, content):
        raw = content.encode("utf-8") if isinstance(content, str) else content
        tree_size(work, limit=MAX_BYTES - len(raw))
        with path.open("xb") as stream:
            stream.write(raw)

    def run(name, command):
        storage.checkpoint(MAX_BYTES, force=True)
        result = subprocess.run(command, capture_output=True, timeout=60,
                                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS)
        bounded_write(work / (name + ".log"), result.stdout + result.stderr)
        receipt.setdefault("steps", []).append({"name": name, "exit_code": result.returncode,
                                                "log_sha256": digest(work / (name + ".log"))})
        if result.returncode:
            raise UserError(name + " failed; preserved private log: " + str(work / (name + ".log")))
        return result.stdout.decode("utf-8", errors="replace")

    def pin(path, name):
        size, sha = API_PINS[name]
        if not path.is_file() or path.stat().st_size != size or digest(path) != sha:
            raise UserError("The exact pinned compile-only API is required: " + name)
        return {"path": str(path), "bytes": size, "sha256": sha, "bundled_in_qa": False}

    try:
        named = Path(os.environ["APPDATA"]) / "PrismLauncher/libraries/net/minecraft/client/1.21.1-20240808.144430/client-1.21.1-20240808.144430-srg.jar"
        if not named.is_file():
            raise UserError("The pinned, normally prepared client is required")
        worldmap = layout.caches / "mods/xaeroworldmap-neoforge-1.21.1-1.47.0.jar"
        horizons = Path(maphorizons_api) if maphorizons_api else layout.caches / "mods/maphorizons-1.1.0-awft.2.jar"
        receipt["compile_only_apis"] = {
            worldmap.name: pin(worldmap, worldmap.name),
            "maphorizons-1.1.0-awft.2.jar": pin(horizons, "maphorizons-1.1.0-awft.2.jar"),
        }
        xaerolib_name = "xaerolib-neoforge-1.21.1-1.7.3.jar"
        with zipfile.ZipFile(worldmap) as archive:
            matches = [n for n in archive.namelist() if n.endswith("/" + xaerolib_name)]
            if len(matches) != 1:
                raise UserError("The pinned nested XaeroLib compile API is unavailable")
            size, sha = API_PINS[xaerolib_name]
            if archive.getinfo(matches[0]).file_size != size:
                raise UserError("The nested XaeroLib size differs")
            data = archive.read(matches[0])
            if hashlib.sha256(data).hexdigest() != sha:
                raise UserError("The nested XaeroLib hash differs")
        xaerolib = work / xaerolib_name
        bounded_write(xaerolib, data)
        receipt["compile_only_apis"][xaerolib_name] = pin(xaerolib, xaerolib_name)
        jars = [named, worldmap, horizons, xaerolib] + sorted((layout.server / "libraries").rglob("*.jar"))
        args = work / "javac.args"
        source_files = sorted((source / "src").rglob("*.java"))
        receipt["sources"] = {p.relative_to(REPO).as_posix(): digest(p) for p in source.rglob("*") if p.is_file()}
        receipt["builder_sha256"] = digest(Path(__file__))
        compile_args = ["-proc:none", "--release", "21", "-sourcepath", "", "-classpath",
                        os.pathsep.join(str(p) for p in jars), "-d", str(classes)] + list(map(str, source_files))
        bounded_write(args, "\n".join('"' + value.replace("\\", "/") + '"' for value in compile_args) + "\n")
        javac_flags = ["-J-Xmx128m", "-J-XX:ActiveProcessorCount=2", "-J-XX:+PerfDisableSharedMem", "-J-Djava.io.tmpdir=" + str(temporary)]
        run("javac", [str(JDK / "javac.exe"), *javac_flags, "@" + str(args)])
        probes = work / "probes"
        probes.mkdir()
        probe_source = source / "probes/MapCaptureGateProbe.java"
        run("javac-readiness-probe", [str(JDK / "javac.exe"), *javac_flags, "-proc:none", "--release", "21",
                                      "-sourcepath", "", "-classpath", str(classes), "-d", str(probes), str(probe_source)])
        probe = run("readiness-probe", [str(JDK / "java.exe"), "-Xmx64m", "-XX:ActiveProcessorCount=2",
                                        "-XX:+PerfDisableSharedMem", "-Djava.io.tmpdir=" + str(temporary), "-ea", "-cp",
                                        os.pathsep.join(map(str, (probes, classes))), "worldfortwo.qa.MapCaptureGateProbe"])
        if "MAP_CAPTURE_GATE_CHECKS=23 PASS; no native GUI executed" not in probe:
            raise UserError("The exact readiness probe result was not returned")
        receipt["readiness_fixture_checks"] = 23
        target = work / ("awft-settlement-qa-" + VERSION + ".jar")
        storage.checkpoint(MAX_BYTES, force=True)
        with zipfile.ZipFile(target, "x", zipfile.ZIP_DEFLATED) as archive:
            for folder in (classes, source / "resources"):
                for path in sorted(folder.rglob("*")):
                    if path.is_file():
                        info = zipfile.ZipInfo(path.relative_to(folder).as_posix(), (2026, 1, 1, 0, 0, 0))
                        info.compress_type = zipfile.ZIP_DEFLATED
                        archive.writestr(info, path.read_bytes())
        with zipfile.ZipFile(target) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)) or any(n.endswith(".jar") or n.startswith(("xaero/", "com/volcanicmg/")) for n in names):
                raise UserError("Compile-only APIs must not be packaged in the QA artifact")
            if any("Probe" in n for n in names):
                raise UserError("Standalone fixture classes must not be packaged")
        if receipt["sources"] != {p.relative_to(REPO).as_posix(): digest(p) for p in source.rglob("*") if p.is_file()}:
            raise UserError("QA source changed during its build")
        tree_size(work, limit=MAX_BYTES)
        receipt.update(status="compiled_and_readiness_fixtures_pass_native_ui_pending", artifact=str(target),
                       bytes=target.stat().st_size, sha256=digest(target))
        bounded_write(work / (target.name + ".sha256"), digest(target) + "  " + target.name + "\n")
        print(target, flush=True)
        return target
    except Exception as error:
        receipt["error"] = type(error).__name__ + ": " + str(error)
        raise
    finally:
        receipt["owned_bytes_before_receipt"] = tree_size(work, limit=MAX_BYTES)
        raw = (json.dumps(receipt, indent=2) + "\n").encode()
        bounded_write(work / "build.json", raw)
        bounded_write(work / "build.complete", hashlib.sha256(raw).hexdigest() + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=Path(r"D:\A World for Two"))
    parser.add_argument("--maphorizons-api", type=Path, help="Exact reviewed awft.2 compile-only API; never installed by this helper")
    options = parser.parse_args()
    build(options.home, maphorizons_api=options.maphorizons_api)
