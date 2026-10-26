from __future__ import annotations

import argparse
import json
from pathlib import Path

from control_room.common import REPO, Layout, read_json, utcnow, write_json
from control_room.pack import Resolver, cache_files, generate_pack, validate_graph, validate_jars, validate_pack
from control_room.storage import Storage


def resolve():
    selection = read_json(REPO / "catalog/selection.json")
    resolver = Resolver(REPO / "evidence/research")
    items = resolver.resolve(selection["mods"])
    for repair in selection.get('repairs', []):
        base = repair['upstream_artifact']
        current = next((m for m in items if m['project_id'] == repair['project_id']), None)
        if not current or current['version_id'] != base['version_id'] or current['hashes'] != base['hashes']:
            raise ValueError('A reviewed compatibility repair no longer matches its exact upstream artifact')
        items = [repair if m['project_id'] == repair['project_id'] else m for m in items]
        if repair['slug'] == 'advanced-weather':
            for item in items:
                if item['slug'] == 'yacl':
                    item['side'] = 'both'
    items += selection.get("artifacts", [])
    lock = {"format": 1, "name": "A World for Two", "version": selection["version"], "minecraft": "1.21.1",
            "neoforge": selection["neoforge"], "java": 21, "generated": utcnow(), "release_status": "candidate",
            "validation": "Runtime and multiplayer acceptance pending", "mods": items}
    write_json(REPO / "catalog/lock.json", lock)
    pack_hash = generate_pack(REPO / "packwiz", lock)
    print(json.dumps({"version": lock["version"], "mods": len(items), "download_bytes": sum(m["size"] for m in items), "pack_sha256": pack_hash}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["resolve", "refresh", "validate", "download", "jars"])
    parser.add_argument("--home", type=Path, default=Path(r"D:\A World for Two"))
    args = parser.parse_args()
    if args.action == "resolve":
        resolve()
        return
    lock = read_json(REPO / "catalog/lock.json")
    if args.action == "refresh":
        print(json.dumps({"pack_sha256": generate_pack(REPO / "packwiz", lock), "version": lock["version"]}))
        return
    if args.action == "validate":
        errors = validate_pack(REPO / "packwiz", lock)
        print(json.dumps({"errors": errors, "mods": len(lock["mods"]), "tier": "manifest integrity"}, indent=2))
        raise SystemExit(bool(errors))
    layout = Layout(args.home)
    storage = Storage(layout)
    if args.action == "download":
        storage.reserve(sum(m["size"] for m in lock["mods"]))
        layout.create()
        cache_files(lock, layout.caches / "mods", storage, print)
    if args.action in ("download", "jars"):
        report = validate_jars(lock, layout.caches / "mods")
        previous = read_json(REPO / "evidence/jar-validation.json")
        if previous and previous != report:
            import time
            write_json(REPO / "evidence/history" / ("jar-" + str(time.time_ns()) + ".json"), previous)
        report["pack_sha256"] = __import__("control_room.common", fromlist=["digest"]).digest(REPO / "packwiz/pack.toml")
        write_json(REPO / "evidence/jar-validation.json", report)
        print(json.dumps({"jars": len(report["jars"]), "errors": report["errors"], "warnings": report["warnings"]}, indent=2))
        raise SystemExit(bool(report["errors"]))


if __name__ == "__main__":
    main()
