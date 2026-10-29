"""Verify/export a managed backup to an owner-configured recovery directory.

The destination may be a separately mounted off-host volume. This tool does not
mount storage, authenticate accounts, create network connections or delete copies.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

from control_room.backups import Backups
from control_room.common import Layout, UserError, digest, read_json, utcnow, write_json
from control_room.storage import Storage


def export(home, ident, destination):
    from tools.snowfall import new_destination
    layout = Layout(home)
    storage = Storage(layout)
    backups = Backups(layout, storage, None)
    with layout.mutation:
        backups.verify(ident)
        source = backups.path(ident)
        receipt = read_json(source.with_suffix(".json"))
        target = new_destination(destination, layout.home)
        storage.reserve(source.stat().st_size + 1024 * 1024, target)
        target.mkdir(mode=0o700)
        write_json(target / "INCOMPLETE.json", {"at": utcnow(), "backup": ident})
        copied = target / source.name
        with source.open("rb") as src, copied.open("xb") as dst:
            while block := src.read(1024 * 1024):
                dst.write(block)
                storage.checkpoint(source.stat().st_size + 1024 * 1024, target)
        os.chmod(copied, 0o600)
        if digest(copied) != receipt["sha256"]:
            raise UserError("Recovery-copy hash mismatch; incomplete copy retained")
        shutil.copy2(source.with_suffix(".json"), target / (ident + ".json"))
        write_json(target / "RECOVERY.json", {"at": utcnow(), "id": ident, "sha256": receipt["sha256"],
                   "archive": source.name, "note": "Filesystem copy verified. Off-host placement and restore acceptance require separate verification."})
        (target / "INCOMPLETE.json").unlink()
        return {"directory": str(target), "sha256": receipt["sha256"], "verified": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("export")
    p.add_argument("--home", required=True, type=Path)
    p.add_argument("--id", required=True)
    p.add_argument("--destination", required=True, type=Path)
    p = sub.add_parser("verify")
    p.add_argument("--archive", required=True, type=Path)
    p.add_argument("--sha256", required=True)
    args = parser.parse_args()
    try:
        if args.action == "export":
            result = export(args.home, args.id, args.destination)
        else:
            if digest(args.archive) != args.sha256:
                raise UserError("Recovery archive does not match the retained SHA-256")
            result = {"verified": True, "archive": str(args.archive)}
        print(json.dumps(result, indent=2))
    except (UserError, OSError, ValueError) as exc:
        parser.exit(1, "Recovery copy: " + str(exc) + "\n")


if __name__ == "__main__":
    main()
