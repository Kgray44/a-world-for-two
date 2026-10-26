from __future__ import annotations

import json
import re
import urllib.request

from .common import UserError, read_json, utcnow, write_json


def profile(name):
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_]{1,16}", name):
        raise UserError("Enter a valid Minecraft Java username")
    request = urllib.request.Request("https://api.mojang.com/users/profiles/minecraft/" + name,
                                     headers={"User-Agent": "a-world-for-two/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            result = json.loads(response.read(4096))
        ident = result["id"]
        if not re.fullmatch(r"[a-fA-F0-9]{32}", ident):
            raise ValueError("Invalid profile ID")
        return {"uuid": "-".join([ident[:8], ident[8:12], ident[12:16], ident[16:20], ident[20:]]), "name": result["name"]}
    except Exception as exc:
        raise UserError("That Java username could not be verified with Mojang. No access was changed.") from exc


class Players:
    def __init__(self, layout, storage, server, settings):
        self.layout, self.storage, self.server, self.settings = layout, storage, server, settings

    def snapshot(self):
        whitelist = read_json(self.layout.server / "whitelist.json", [])
        ops = read_json(self.layout.server / "ops.json", [])
        status = self.server.snapshot()
        return {"whitelist": whitelist, "operators": ops, "online": status.get("status", {}).get("players") if status.get("status") else None,
                "events": status["events"], "online_mode": True,
                "note": "Profile names and UUIDs only. Account credentials are never collected."}

    def update(self, action, name, confirmed=False, notify=lambda _: None):
        if action not in ("whitelist-add", "whitelist-remove", "op", "deop", "kick"):
            raise UserError("Unknown player action")
        if action in ("whitelist-remove", "op", "deop", "kick") and confirmed is not True:
            raise UserError("Confirm this access or player action")
        who = profile(name)
        with self.layout.mutation:
            self.storage.reserve(1024 * 1024)
            if self.server.running():
                command = ("whitelist " + action.removeprefix("whitelist-") if action.startswith("whitelist-") else action) + " " + who["name"]
                self.server.command(command, confirmed=True)
                return {"sent": command, "note": "The server applies the change; refresh the whitelist after its console confirmation."}
            if action == "kick":
                raise UserError("The server is offline")
            path = self.layout.server / ("whitelist.json" if action.startswith("whitelist") else "ops.json")
            entries = read_json(path, [])
            self.settings.snapshot(path) if path.exists() else None
            entries = [x for x in entries if x.get("uuid") != who["uuid"]]
            if action == "whitelist-add":
                entries.append(who)
            elif action == "op":
                entries.append(dict(who, level=3, bypassesPlayerLimit=False))
            write_json(path, entries)
            write_json(self.layout.logs / ("player-action-" + str(__import__("time").time_ns()) + ".json"),
                       {"at": utcnow(), "action": action, "player": who["name"], "uuid": who["uuid"]})
            notify("Updated " + who["name"] + " access")
            return self.snapshot()
