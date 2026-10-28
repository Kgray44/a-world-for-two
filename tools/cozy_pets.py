"""Review or integrate the source-only pet proposal; never operate a runtime/save.

The master owns --apply-source. A specialist can produce --stage beneath .local.
No network, dependency re-resolution, JAR installation or native commands occur.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import subprocess
import tomllib
from pathlib import Path

from control_room.common import REPO, UserError, atomic_write, digest, read_json, utcnow, write_json
from control_room.pack import generate_pack, in_range, validate_pack
from tools.compatibility import generate as generate_inventory

PROPOSAL = REPO / "proposals/cozy-pets"
MAX_SOURCE_BYTES = 64 * 1024 * 1024


def proposal_data(proposal=PROPOSAL):
    proposal = Path(proposal)
    manifest = read_json(proposal / "manifest.json")
    audit = read_json(proposal / "static-audit.json")
    if (manifest["minecraft"], manifest["neoforge"], manifest["java"]) != ("1.21.1", "21.1.262", 21):
        raise UserError("Pet proposal stack changed; fresh review required")
    payloads = {p.relative_to(proposal / "packwiz").as_posix(): digest(p)
                for p in (proposal / "packwiz").rglob("*") if p.is_file()}
    if payloads != manifest["payloads"]:
        raise UserError("Pet payloads differ from the reviewed manifest")
    for relative in payloads:
        path = (proposal / "packwiz" / relative).resolve()
        if not path.is_relative_to((proposal / "packwiz").resolve()) or not relative.startswith("config/"):
            raise UserError("Pet payload escapes its source configuration directory")
    for name, record in audit["config_fields"].items():
        config = tomllib.loads((proposal / "packwiz/config/adorablehamsterpets" / name).read_text())
        if config != {k: v["value"] for k, v in record["fields"].items()}:
            raise UserError("Pet configuration differs from the exact native-field review")
    for item in manifest["additions"]:
        pin = audit["jars"][item["slug"]]
        if (pin["filename"], pin["size"], pin["sha512"]) != (item["filename"], item["size"], item["hashes"]["sha512"]):
            raise UserError("Pet artifact differs from the native JAR review")
    return manifest


def plan(root=REPO, proposal=PROPOSAL):
    """Add exact reviewed records while preserving every concurrent master pin."""
    root, proposal = Path(root), Path(proposal)
    manifest = proposal_data(proposal)
    lock = read_json(root / "catalog/lock.json")
    selection = read_json(root / "catalog/selection.json")
    requests = read_json(root / "catalog/requests.json")
    if (lock["minecraft"], lock["neoforge"], lock["java"]) != ("1.21.1", "21.1.262", 21):
        raise UserError("Current stack differs from the pet proposal; review before integration")
    errors = validate_pack(root / "packwiz", lock)
    if errors:
        raise UserError("Current source pack must validate before integration: " + "; ".join(errors))
    original = {m["project_id"]: copy.deepcopy(m) for m in lock["mods"]}
    expected = manifest["existing_glider"]
    glider = original.get(expected["project_id"], {})
    if any(glider.get(k) != v for k, v in expected.items()) or glider.get("optional") or not glider.get("default", True):
        raise UserError("Existing Sugar Glider pin/enablement changed; review before integration")
    changed = []
    for item in manifest["additions"]:
        previous = original.get(item["project_id"])
        if previous:
            keys = ("version_id", "filename", "hashes", "size", "side", "optional", "default")
            if any(previous.get(k) != item.get(k) for k in keys):
                raise UserError("Refusing to replace or enable a different existing pin: " + item["slug"])
        else:
            lock["mods"].append(copy.deepcopy(item))
            changed.append(item["slug"])
    for choice in manifest["choices"]:
        existing = next((c for c in selection["mods"] if c["project"] in (choice["project"],
                        next(m["project_id"] for m in manifest["additions"] if m["slug"] == choice["project"]))), None)
        if existing and existing.get("version") != choice["version"]:
            raise UserError("Selection conflicts with reviewed pet pin: " + choice["project"])
        if not existing:
            selection["mods"].append(copy.deepcopy(choice))
    for request in manifest["requests"]:
        if not any(r[0] == request[0] for r in requests["requests"]):
            requests["requests"].append(request)
    mods = {m["slug"]: m for m in lock["mods"]}
    for dep in manifest["required_native_mods"]:
        item = mods.get(dep["slug"])
        if not item or item["side"] != "both" or item.get("optional") or not item.get("default", True) or not in_range(item["version"], dep["range"]):
            raise UserError("Native hamster dependency unavailable on both sides: " + dep["slug"])
    for relative, expected_hash in manifest["payloads"].items():
        current = root / "packwiz" / relative
        if current.exists() and digest(current) != expected_hash:
            raise UserError("Refusing to overwrite an existing pet configuration: " + relative)
    # Existing mod records retain their exact bytes/validation state in memory.
    assert all(next(m for m in lock["mods"] if m["project_id"] == pid) == item for pid, item in original.items())
    return {"lock": lock, "selection": selection, "requests": requests, "new_mods": changed,
            "payloads": manifest["payloads"], "input_seals": {f: digest(root / f) for f in
                ("catalog/lock.json", "catalog/selection.json", "catalog/requests.json", "packwiz/pack.toml", "packwiz/index.toml")}}


def apply_source(root, version, proposal=PROPOSAL):
    """Master-only source integration; no download, runtime, client or save writes."""
    root, proposal = Path(root), Path(proposal)
    result = plan(root, proposal)
    if version == result["lock"]["version"]:
        raise UserError("Pet integration needs a distinct candidate version")
    if not version or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_+" for c in version):
        raise UserError("Invalid candidate version")
    # Check the complete source inventory again immediately before publication.
    if any(digest(root / f) != value for f, value in result["input_seals"].items()):
        raise UserError("Master source changed during planning; no writes made")
    result["lock"].update(version=version, generated=utcnow(),
                           validation="Pet metadata/static review only; current-candidate runtime and multiplayer acceptance pending")
    result["selection"]["version"] = version
    for name in ("lock", "selection", "requests"):
        write_json(root / "catalog" / (name + ".json"), result[name])
    for relative in result["payloads"]:
        atomic_write(root / "packwiz" / relative, (proposal / "packwiz" / relative).read_text())
    generate_pack(root / "packwiz", result["lock"])
    errors = validate_pack(root / "packwiz", result["lock"])
    if errors:
        raise UserError("Integrated pet manifest validation failed: " + "; ".join(errors))
    generate_inventory(root)
    return {"tier": "source only; runtime and permanent-world integration pending", "new_mods": result["new_mods"],
            "version": version, "pack_sha256": digest(root / "packwiz/pack.toml")}


def stage(source, target, proposal=PROPOSAL):
    source, target = Path(source).resolve(), Path(target).resolve()
    if not target.is_relative_to(source / ".local") or target.exists():
        raise UserError("Review stage must be a new directory beneath this worktree's .local")
    files = list((source / "packwiz").rglob("*"))
    size = sum(p.stat().st_size for p in files if p.is_file())
    if size + 8 * 1024 * 1024 > MAX_SOURCE_BYTES:
        raise UserError("Source-only stage exceeds its 64 MiB allocation bound")
    plan(source, proposal)  # fail before allocating a partial stage
    target.mkdir(parents=True)
    shutil.copytree(source / "packwiz", target / "packwiz")
    (target / "catalog").mkdir()
    for filename in ("lock.json", "selection.json", "requests.json", "experiments.json"):
        if (source / "catalog" / filename).is_file():
            shutil.copyfile(source / "catalog" / filename, target / "catalog" / filename)
    return apply_source(target, read_json(source / "catalog/lock.json")["version"] + "-cozy-pets-review", proposal)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--stage", type=Path)
    action.add_argument("--apply-source", action="store_true", help="Master integration owner only; source checkout only")
    parser.add_argument("--version")
    args = parser.parse_args()
    if args.stage or args.apply_source:
        if os.name != "nt":
            raise UserError("Writers require the Windows host reserve guard")
        if args.apply_source and not args.version:
            parser.error("--apply-source requires a new --version")
        guard = Path(r"C:\Users\kkids\AppData\Local\AeroStorageWatch\ReserveGuard.ps1")
        # This CLI writes only the current C:-hosted source checkout/stage.
        if REPO.drive.upper() != "C:":
            raise UserError("Recompute per-drive writer estimates before using a different source drive")
        subprocess.run(["powershell.exe", "-NoProfile", "-File", str(guard),
                        "-EstimatedCBytes", str(MAX_SOURCE_BYTES), "-EstimatedDBytes", "0"], check=True)
    if args.stage:
        result = stage(REPO, args.stage)
    elif args.apply_source:
        result = apply_source(REPO, args.version)
    else:
        proposed = plan()
        result = {"tier": "read-only proposal", "new_mods": proposed["new_mods"],
                  "input_seals": proposed["input_seals"], "payloads": proposed["payloads"]}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
