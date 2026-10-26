"""Reproducible metadata repair of the MIT Advanced Weather 0.1.2 artifact.

The original JAR is kept unchanged. No class, assertion, injection count or safety
check is removed. A LocalPlayer-only mixin is assigned to the client side, and the
common config serializer's YACL dependency is declared on both sides.
"""
from __future__ import annotations

import hashlib
import json
import re
import os
import subprocess
import zipfile
from copy import deepcopy
from pathlib import Path

from control_room.common import REPO, UserError, digest, write_json

PATCH_VERSION = "0.1.2+awft.3"


def build(source: Path, destination: Path, item, storage, libraries=None):
    algorithm = "sha512" if "sha512" in item["hashes"] else "sha256"
    if digest(source, algorithm) != item["hashes"][algorithm]:
        raise UserError("Advanced Weather patch base does not match the reviewed upstream hash")
    storage.reserve(item["size"] + 1024 * 1024, destination)
    if destination.exists():
        raise UserError("Patch output already exists; preserve it and use a new owned build directory")
    destination.parent.mkdir(parents=True, exist_ok=True)
    replacement = None
    if libraries is not None:
        work = destination.parent / "compile-weather"
        work.mkdir()
        embedded = work / "embedded"
        embedded.mkdir()
        with zipfile.ZipFile(source) as original:
            meta = json.loads(original.read("META-INF/jarjar/metadata.json"))
            for record in meta["jars"]:
                entry = original.getinfo(record["path"])
                if entry.file_size > 128 * 1024 * 1024:
                    raise UserError("Embedded compile dependency is too large")
                (embedded / Path(entry.filename).name).write_bytes(original.read(entry))
        jars = [source, *sorted(embedded.glob("*.jar")), *sorted(Path(libraries).rglob("*.jar"))]
        cp = os.pathsep.join(str(p).replace("\\", "/") for p in jars)
        java = Path(r"C:\Program Files\Java\jdk-21.0.10\bin\javac.exe")
        if not java.is_file():
            raise UserError("This repair build requires the tested Java 21.0.10 JDK compiler")
        classes = work / "classes"
        classes.mkdir()
        src = REPO / "compat/advanced-weather/src/net/antopfr/advancedweather/content/fluid/AWFluids.java"
        args = work / "javac.args"
        args.write_text('-proc:none\n--release\n21\n-classpath\n"' + cp + '"\n-d\n"' + classes.as_posix() + '"\n"' + src.as_posix() + '"\n', encoding="utf-8")
        result = subprocess.run([str(java), "@" + str(args)], text=True, capture_output=True, timeout=60,
                                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        (work / "javac.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        if result.returncode:
            raise UserError("Weather repair compilation failed: " + result.stderr[:2000])
        replacement = (classes / "net/antopfr/advancedweather/content/fluid/AWFluids.class").read_bytes()
    changed = []
    with zipfile.ZipFile(source) as original, zipfile.ZipFile(destination, "x") as result:
        for info in original.infolist():
            raw = original.read(info)
            if info.filename == "advancedweather.mixins.json":
                data = json.loads(raw)
                if "BlockFrictionMixin" not in data["mixins"]:
                    raise UserError("Unexpected upstream mixin layout; patch must be reviewed again")
                data["mixins"].remove("BlockFrictionMixin")
                data["client"].append("BlockFrictionMixin")
                raw = (json.dumps(data, indent=2) + "\n").encode()
                changed.append(info.filename)
            elif info.filename == "META-INF/neoforge.mods.toml":
                text = raw.decode()
                text, count = re.subn(r'^version="0\.1\.2"', 'version="' + PATCH_VERSION + '"', text, count=1, flags=re.M)
                text, dependency_count = re.subn(r'(modId\s*=\s*"yet_another_config_lib_v3"[\s\S]*?side\s*=\s*)"CLIENT"', r'\1"BOTH"', text, count=1)
                if count != 1 or dependency_count != 1:
                    raise UserError("Unexpected upstream version/dependency layout")
                raw = text.encode()
                changed.append(info.filename)
            elif info.filename == "net/antopfr/advancedweather/content/fluid/AWFluids.class" and replacement:
                raw = replacement
                changed.append(info.filename)
            result.writestr(info, raw)
        provenance = {"format": 1, "upstream_version": "0.1.2", "version": PATCH_VERSION,
                      "upstream_sha256": digest(source), "changed_entries": changed,
                      "reason": "Correct client-only mixin classification, common config dependency, and the absent mercury bucket supplier. Every other upstream class remains unchanged.",
                      "upstream_source": "https://github.com/Antop90fr1/AdvancedWeather1.21.1",
                      "source_commit_inspected": "50fe9990e03ac24638343703792797f8991b5266",
                      "license": "MIT; original work by Antopfr. Embedded libraries retain their own licenses."}
        marker = zipfile.ZipInfo("META-INF/awft-patch.json", (2026, 1, 1, 0, 0, 0))
        result.writestr(marker, json.dumps(provenance, indent=2))
        for notice in sorted((REPO / "compat/advanced-weather/notices").glob("*")):
            entry = zipfile.ZipInfo("META-INF/awft-notices/" + notice.name, (2026, 1, 1, 0, 0, 0))
            result.writestr(entry, notice.read_bytes())
    with zipfile.ZipFile(source) as original, zipfile.ZipFile(destination) as result:
        for name in original.namelist():
            if name not in changed and original.read(name) != result.read(name):
                raise UserError("An unrequested upstream entry changed during patching")
        if result.testzip():
            raise UserError("Patched archive integrity failed")
    patched = deepcopy(item)
    patched.update(filename=destination.name, version=PATCH_VERSION,
                   version_id=PATCH_VERSION, provider="local-patch", size=destination.stat().st_size,
                   hashes={"sha256": digest(destination)},
                   selection_reason=provenance["reason"])
    return patched, provenance
