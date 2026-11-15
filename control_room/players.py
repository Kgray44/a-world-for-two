from __future__ import annotations

import json
import math
import re
import threading
import time
import urllib.request
from datetime import datetime

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
    def __init__(self, layout, storage, server, settings, telemetry=lambda: {}):
        self.layout, self.storage, self.server, self.settings = layout, storage, server, settings
        self.telemetry = telemetry
        self.storage.reserve(2 * 1024 * 1024)
        self.last_location_sample = None
        self._snapshot_lock = threading.RLock()

    def snapshot(self):
        # Read atomic access files while a world job owns layout.mutation.
        # Only last-seen dashboard bookkeeping needs serialization here.
        with self._snapshot_lock:
            return self._snapshot()

    def _snapshot(self):
        whitelist = read_json(self.layout.server / "whitelist.json", [])
        ops = read_json(self.layout.server / "ops.json", [])
        status = self.server.snapshot()
        measurements = self.telemetry()
        fresh = False
        measured_at = measurements.get('player_roster_at') or measurements.get('bridge_at') or measurements.get('tick_at')
        if (isinstance(measured_at, str) and status["state"] == "online"
                and measurements.get('players_available') is not False):
            try:
                fresh = 0 <= time.time() - datetime.fromisoformat(measured_at.replace("Z", "+00:00")).timestamp() <= 15
            except (ValueError, TypeError):
                pass
        measured_players = measurements.get('players')
        fresh = fresh and isinstance(measured_players, dict)
        live = {ident: dict(value, at=measured_at) for ident, value in measured_players.items()} if fresh else {}
        process_offline = status['state'] in ('offline', 'failed') and not status.get('pid')
        known = read_json(self.layout.state / "last-player-locations.json", {})
        if live and measured_at != self.last_location_sample:
            known.update({ident: dict(value, at=measured_at) for ident, value in live.items()})
            known = dict(list(known.items())[-128:])
            write_json(self.layout.state / "last-player-locations.json", known)
            self.last_location_sample = measured_at
        identities = {p["uuid"]: {"uuid": p["uuid"], "name": p["name"]} for p in [*whitelist, *ops, *live.values()]}
        members = []
        for ident, person in identities.items():
            op = next((x for x in ops if x["uuid"] == ident), {})
            location = live.get(ident) or known.get(ident)
            online = ident in live if fresh else False if process_offline else None
            members.append(dict(person, whitelisted=any(x["uuid"] == ident for x in whitelist),
                operator_level=op.get("level", 0), bypass_player_limit=op.get("bypassesPlayerLimit", False),
                online=online, online_state='unknown' if online is None else 'online' if online else 'offline',
                presence_source='fresh complete bridge roster' if fresh else 'owned server process is not running' if process_offline else 'current player telemetry is unavailable',
                location=location, location_state="live" if ident in live else "last seen" if location else "not available"))
        server_roster = (status.get('status') or {}).get('players') or {}
        roster = {'online': len(live) if fresh else 0,
                  'max': server_roster.get('max', self.layout.settings()['max_players']),
                  'sample': [{'id': ident, 'name': player['name']} for ident, player in live.items()]} if fresh or process_offline else None
        return {"whitelist": whitelist, "operators": ops, "online": roster,
                'online_state': 'current' if fresh else 'offline' if process_offline else 'unknown',
                'presence_note': 'Player presence is unknown when measurements expire; last-seen coordinates are historical, not a disconnect report.',
                "events": status["events"], "online_mode": True, "members": members,
                "capabilities": measurements.get("bridge_capabilities", []) if fresh else [],
                "note": "Profile names and UUIDs only. Account credentials are never collected."}

    def details(self, name):
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_]{1,16}", name):
            raise UserError("Choose a valid Java player")
        snapshot = self.snapshot()
        who = next((p for p in snapshot["members"] if p["name"].lower() == name.lower()), None)
        if who is None:
            raise UserError("This player is not in the whitelist, operator list or current online roster")
        return dict(who, capabilities=snapshot["capabilities"])

    def permissions(self, name, level, bypass=False, confirmed=False, notify=lambda _: None):
        if type(level) is not int or not 0 <= level <= 4 or type(bypass) is not bool or level == 0 and bypass:
            raise UserError("Choose member level 0 or operator level 1–4. Player-limit bypass requires operator status.")
        if confirmed is not True:
            raise UserError("Confirm this permission change before saving")
        who = self.details(name)
        with self.layout.mutation:
            self.storage.reserve(1024 * 1024)
            path = self.layout.server / "ops.json"
            if path.exists():
                self.settings.snapshot(path)
            if self.server.running():
                if "player_permissions" not in self.snapshot()["capabilities"]:
                    raise UserError("Live permission-level editing needs the fresh Control Bridge 0.2 telemetry. Stop the server to edit offline, or install the updated bridge.")
                command = f"awft permissions {who['name']} {who['uuid']} {level} {str(bypass).lower()}"
                self.server._write(command)
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    try:
                        entries = read_json(path, [])
                        entry = next((p for p in entries if p["uuid"] == who["uuid"]), None)
                        if (level == 0 and entry is None) or (entry and entry.get("level") == level and entry.get("bypassesPlayerLimit") == bypass):
                            break
                    except (ValueError, OSError):
                        pass
                    time.sleep(.1)
                else:
                    raise UserError("The permission command was sent but persistence was not confirmed. Review the console before retrying.")
            else:
                entries = [p for p in read_json(path, []) if p["uuid"] != who["uuid"]]
                if level:
                    entries.append({"uuid": who["uuid"], "name": who["name"], "level": level, "bypassesPlayerLimit": bypass})
                write_json(path, entries)
            write_json(self.layout.logs / ("player-permissions-" + str(time.time_ns()) + ".json"),
                {"at": utcnow(), "player": who["name"], "uuid": who["uuid"], "from_level": who["operator_level"], "to_level": level, "bypass": bypass, "persistence": "confirmed"})
            notify("Saved " + who["name"] + " permission level " + str(level))
            return self.details(name)

    def game_action(self, name, action, value=None, confirmed=False, notify=lambda _: None):
        if confirmed is not True:
            raise UserError("Confirm this player change first")
        who = self.details(name)
        self.storage.reserve(1024 * 1024)
        if not self.server.running() or not who["online"]:
            raise UserError("This player must be online with current server telemetry")
        if action == "game-mode" and value in ("survival", "creative", "adventure", "spectator"):
            command = "gamemode " + value + " " + who["name"]
        elif action == "xp-level" and type(value) is int and 0 <= value <= 1000:
            command = f"experience set {who['name']} {value} levels"
        elif action == "kick":
            command = "kick " + who["name"]
        else:
            raise UserError("Choose a supported player action or XP level from 0 through 1000")
        self.server._write(command)
        write_json(self.layout.logs / ("player-game-action-" + str(time.time_ns()) + ".json"), {"at": utcnow(), "action": action, "player": who["name"], "value": value, "state": "command sent; refresh telemetry for result"})
        return {"sent": command, "note": "Refresh the live player card to confirm the result"}

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
