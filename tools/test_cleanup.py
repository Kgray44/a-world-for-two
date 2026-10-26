"""Terminate only an owned disposable JVM after a recorded fatal server-thread crash.

Never used by production stop/backup/restore. All failed worlds, logs and receipts remain.
"""
from __future__ import annotations

import contextlib
from pathlib import Path

import psutil

from control_room.common import UserError, read_json, utcnow, write_json


def cleanup(root: Path):
    root = root.resolve()
    owner = read_json(root / "dashboard/test-owner.json", {})
    identity = read_json(root / "dashboard/server-process.json", {})
    if owner.get("id") != root.name or root.parent.name != "world-tests" or root.parent.parent.name != "staging":
        raise UserError("This directory is not an owned disposable world test")
    if not identity.get("pid"):
        return {"already_exited": True}
    try:
        process = psutil.Process(identity["pid"])
    except psutil.NoSuchProcess:
        return {"already_exited": True}
    if abs(process.create_time() - identity["created"]) > .1 or process.cmdline() != identity["command"] or process.cwd() != str(root / "server"):
        raise UserError("Disposable process identity differs; refusing cleanup")
    log = (root / "logs/console.log").read_text(errors="replace")
    if "Encountered an unexpected exception" not in log or not list((root / "server/crash-reports").glob("*.txt")):
        raise UserError("No recorded fatal server crash authorizes test-process cleanup")
    children = process.children(recursive=True)
    entries = [{"pid": p.pid, "created": p.create_time(), "command": p.cmdline(), "exe": p.exe()} for p in [process, *children]]
    receipt = {"at": utcnow(), "reason": "Fatal disposable server-thread crash left residual owned processes. This is forced test cleanup, not clean shutdown or world-integrity acceptance.", "processes": entries}
    write_json(root / "logs/forced-test-cleanup.json", receipt)
    for child in reversed(children):
        with contextlib.suppress(psutil.NoSuchProcess):
            child.terminate()
    with contextlib.suppress(psutil.NoSuchProcess):
        process.terminate()
    gone, alive = psutil.wait_procs([process, *children], timeout=10)
    receipt.update(terminated=[p.pid for p in gone], still_alive=[p.pid for p in alive])
    write_json(root / "logs/forced-test-cleanup.json", receipt)
    return receipt
