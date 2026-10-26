from __future__ import annotations

import difflib
import json
import math
import re
import tomllib
from pathlib import Path

from .common import UserError, atomic_write, contained, digest, read_json, utcnow, write_json

PROPERTY_SCHEMA = {
    "view-distance": {"type": "integer", "min": 2, "max": 16, "default": 8, "recommended": 8,
                      "label": "View distance", "change": "Requires restart", "description": "Full chunks sent to players. LOD distance is a separate client setting."},
    "simulation-distance": {"type": "integer", "min": 2, "max": 12, "default": 6, "recommended": 6,
                            "label": "Simulation distance", "change": "Requires restart", "description": "Active chunk simulation around each player."},
    "max-players": {"type": "integer", "min": 2, "max": 8, "default": 2, "recommended": 2,
                    "label": "Player limit", "change": "Requires restart", "description": "This server is sized for two active players."},
    "difficulty": {"type": "enum", "values": ["peaceful", "easy", "normal", "hard"], "default": "normal",
                   "recommended": "normal", "label": "Difficulty", "change": "Requires restart", "description": "Use the console difficulty control for a live change."},
    "pvp": {"type": "boolean", "default": False, "recommended": False, "label": "Player combat",
            "change": "Requires restart", "description": "Keep accidental damage out of your shared homestead."},
    "spawn-protection": {"type": "integer", "min": 0, "max": 64, "default": 0, "recommended": 0,
                         "label": "Spawn protection", "change": "Requires restart", "description": "Zero allows both whitelisted players to build at spawn."},
    "spawn-animals": {"type": "boolean", "default": True, "recommended": True, "label": "Animals",
                      "change": "Requires restart", "description": "Wildlife mods can impose additional spawn rules."},
    "spawn-monsters": {"type": "boolean", "default": True, "recommended": True, "label": "Monsters",
                       "change": "Requires restart", "description": "Difficulty and mod settings also affect spawning."},
    "motd": {"type": "string", "max_length": 120, "default": "A World for Two | KG & Sera",
             "recommended": "A World for Two | KG & Sera", "label": "Welcome message", "change": "Requires restart", "description": "Shown in the multiplayer server list."},
    "level-seed": {"type": "string", "max_length": 64, "default": "", "recommended": "",
                   "label": "World seed", "change": "Dangerous to change after world creation", "description": "Set before creating the world. Hidden from the overview until revealed."},
}

APP_SCHEMA = {
    "heap_gib": {"type": "integer", "min": 4, "max": 12, "default": 8, "recommended": 8, "label": "Server heap (GiB)", "change": "Requires restart", "description": "Eight GiB starts below the host's 32 GiB total alongside the client."},
    "backup_interval_hours": {"type": "integer", "min": 1, "max": 48, "default": 6, "recommended": 6, "label": "Backup interval (hours)", "change": "Live-changeable", "description": "Scheduled backups run after a controlled stop if the server is online."},
    "backup_keep": {"type": "integer", "min": 1, "max": 30, "default": 7, "recommended": 7, "label": "Retained backups", "change": "Live-changeable", "description": "Only verified, older managed backups may be pruned. Restore safety copies are kept."},
    "sample_seconds": {"type": "integer", "min": 5, "max": 60, "default": 5, "recommended": 5, "label": "Telemetry interval (seconds)", "change": "Live-changeable", "description": "Host and owned Java-process samples; tick telemetry is collected less often."},
    "cache_budget_gib": {"type": "integer", "min": 1, "max": 20, "default": 8, "recommended": 8, "label": "LOD/cache budget (GiB)", "change": "Live-changeable", "description": "At the limit, managed generation is paused and a warning is raised. Third-party client generators need their own limits."},
    "world_budget_gib": {"type": "integer", "min": 2, "max": 60, "default": 40, "recommended": 40, "label": "World growth budget (GiB)", "change": "Live-changeable", "description": "The managed server is stopped gracefully before unbounded world growth consumes the reserve."},
}


def validate_value(value, spec):
    kind = spec["type"]
    if kind == "integer":
        if type(value) is not int or not spec["min"] <= value <= spec["max"]:
            raise UserError(f"{spec['label']}: enter {spec['min']} through {spec['max']}")
    elif kind == "number":
        if type(value) not in (int, float) or not math.isfinite(value) or not spec["min"] <= value <= spec["max"]:
            raise UserError(f"{spec['label']}: enter {spec['min']} through {spec['max']}")
    elif kind == "boolean":
        if type(value) is not bool:
            raise UserError(spec["label"] + ": choose on or off")
    elif kind == "enum":
        if value not in spec["values"]:
            raise UserError(spec["label"] + ": unsupported value")
    elif kind == "string":
        if not isinstance(value, str) or len(value) > spec["max_length"] or any(c in value for c in "\r\n\0\\"):
            raise UserError(spec["label"] + ": invalid text")
    return value


def properties(text):
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "!")):
            continue
        if "=" not in line or line.endswith("\\"):
            raise UserError("Use one key=value property per line; continuation syntax is not supported")
        key, value = line.split("=", 1)
        if key.strip() in result:
            raise UserError("Duplicate property: " + key.strip())
        result[key.strip()] = value.strip()
    return result


def format_properties(data):
    return "# Managed by A World for Two: Control Room\n" + "".join(f"{key}={str(value).lower() if isinstance(value, bool) else value}\n" for key, value in data.items())


class Settings:
    def __init__(self, layout, storage, server):
        self.layout, self.storage, self.server = layout, storage, server

    @property
    def props_path(self):
        return self.layout.server / "server.properties"

    def get_properties(self):
        return properties(self.props_path.read_text(encoding="utf-8-sig")) if self.props_path.exists() else {}

    def catalog(self):
        current = self.get_properties()
        fields = []
        for key, spec in PROPERTY_SCHEMA.items():
            value = current.get(key, spec["default"])
            if spec["type"] == "integer":
                try:
                    value = int(value)
                except ValueError:
                    value = None
            if spec["type"] == "boolean":
                value = str(value).lower() == "true"
            fields.append(dict(spec, key=key, scope="server", current=value))
        app = self.layout.settings()
        fields += [dict(spec, key=key, scope="app", current=app[key]) for key, spec in APP_SCHEMA.items()]
        return {"fields": fields, "mods": self.mod_forms(), "gc": "Java 21 default G1; 2 GiB initial, 8 GiB maximum. Profile before changing collectors.",
                "unsupported": ["Entity activation distances are not a vanilla/NeoForge property.",
                    "Create and Sable limits use generated version-specific TOML; open the validated raw editor.",
                    "Mob spawn densities use each wildlife mod's generated settings; no guessed config keys are written.",
                    "C2ME is excluded from the primary pack because SeedGen reports device-dependent incompatibility."]}

    def initialize(self):
        self.storage.reserve(1024 * 1024)
        if not self.props_path.exists():
            data = {key: spec["default"] for key, spec in PROPERTY_SCHEMA.items()}
            data.update({"server-ip": "127.0.0.1", "server-port": 25565, "online-mode": True,
                         "white-list": True, "enforce-whitelist": True, "enable-rcon": False,
                         "enable-query": False, "enable-jmx-monitoring": False, "broadcast-rcon-to-ops": False,
                         "level-name": (self.layout.world / "AWorldForTwo").as_posix(), "max-tick-time": 60000})
            atomic_write(self.props_path, format_properties(data))
        eula = self.layout.server / "eula.txt"
        if not eula.exists():
            atomic_write(eula, "# Owner must explicitly accept https://aka.ms/MinecraftEULA\neula=false\n")

    def update(self, scope, changes, expected=None):
        if not isinstance(changes, dict) or not changes:
            raise UserError("No settings were supplied")
        with self.layout.mutation:
            schemas = PROPERTY_SCHEMA if scope == "server" else APP_SCHEMA if scope == "app" else None
            if schemas is None:
                raise UserError("Unknown settings scope")
            for key, value in changes.items():
                if key not in schemas:
                    raise UserError("Unsupported setting: " + key)
                validate_value(value, schemas[key])
                if key == "level-seed" and (self.layout.world.exists() and any(self.layout.world.rglob("level.dat"))):
                    raise UserError("The seed cannot be changed after a world exists")
            if scope == "server" and self.server.running():
                raise UserError("Stop the server before changing restart-required settings")
            path = self.props_path if scope == "server" else self.layout.settings_path
            if expected and (not path.exists() or digest(path) != expected):
                raise UserError("Configuration changed since you opened it; reload before saving")
            self.storage.reserve(2 * 1024 * 1024)
            if path.exists():
                self.snapshot(path)
            values = self.get_properties() if scope == "server" else self.layout.settings()
            values.update(changes)
            if scope == "server":
                atomic_write(path, format_properties(values))
            else:
                self.layout.save_settings(values)
            return {"saved": True, "restart_required": scope == "server" or "heap_gib" in changes}

    def snapshot(self, path):
        ident = utcnow().replace(":", "-")
        relative = path.relative_to(self.layout.home).as_posix()
        directory = self.layout.home / "configs/history" / ident
        directory.mkdir(parents=True)
        atomic_write(directory / "content", path.read_bytes())
        write_json(directory / "record.json", {"path": relative, "sha256": digest(path), "created": utcnow()})
        return ident

    def allowed_config(self, relative):
        path = contained(self.layout.server, relative)
        if relative == "server.properties" or (relative.startswith("config/") or "/serverconfig/" in relative):
            if path.suffix in (".json", ".toml", ".properties"):
                return path
        raise UserError("Only server.properties and generated mod JSON, TOML or properties files can be edited")

    def raw(self, relative):
        path = self.allowed_config(relative)
        if not path.is_file() or path.stat().st_size > 1024 * 1024:
            raise UserError("Configuration is missing or exceeds 1 MiB")
        content = path.read_text(encoding="utf-8-sig")
        if relative == "server.properties" and "rcon.password=" in content:
            raise UserError("A private RCON password is present; edit this file locally")
        return {"path": relative, "content": content, "sha256": digest(path)}

    def raw_proposal(self, relative, content, expected):
        if not isinstance(content, str) or len(content.encode()) > 1024 * 1024:
            raise UserError("Configuration text exceeds 1 MiB")
        old = self.raw(relative)
        if old["sha256"] != expected:
            raise UserError("Configuration changed; reload before editing")
        suffix = Path(relative).suffix
        try:
            if suffix == ".json":
                json.loads(content)
            elif suffix == ".toml":
                tomllib.loads(content)
            elif suffix == ".properties":
                data = properties(content)
                if relative == "server.properties":
                    prior = properties(old["content"])
                    protected = {"online-mode", "enable-rcon", "enable-query", "server-ip", "server-port", "level-name", "white-list", "enforce-whitelist", "enable-jmx-monitoring"}
                    if any(data.get(key) != prior.get(key) for key in protected):
                        raise UserError("Network, authentication and world paths require the dedicated setup controls")
                    if any(k not in prior and k.startswith("rcon.") for k in data):
                        raise UserError("RCON is not enabled through the browser")
                    for key, spec in PROPERTY_SCHEMA.items():
                        if key not in data:
                            continue
                        value = data[key]
                        if spec["type"] == "integer":
                            value = int(value)
                        elif spec["type"] == "boolean":
                            if value not in ("true", "false"):
                                raise ValueError("Boolean must be true or false")
                            value = value == "true"
                        validate_value(value, spec)
                    if data.get("level-seed") != prior.get("level-seed") and any(self.layout.world.rglob("level.dat")):
                        raise UserError("Cannot change the seed of an existing world")
        except (ValueError, tomllib.TOMLDecodeError) as exc:
            raise UserError("Invalid configuration syntax: " + str(exc)) from exc
        return {"path": relative, "expected": expected, "content": content,
                "diff": "".join(difflib.unified_diff(old["content"].splitlines(True), content.splitlines(True), "current", "proposed")),
                "warning": "Syntax verified. Mod-specific raw values still require the upstream schema and runtime validation."}

    def raw_save(self, relative, content, expected):
        with self.layout.mutation:
            if self.server.running():
                raise UserError("Stop the server before editing raw configuration")
            proposal = self.raw_proposal(relative, content, expected)
            path = self.allowed_config(relative)
            self.storage.reserve(3 * 1024 * 1024)
            prior = self.snapshot(path)
            atomic_write(path, proposal["content"])
            return {"saved": True, "previous": prior, "restart_required": True}

    def history(self):
        directory = self.layout.home / "configs/history"
        return [dict(read_json(f), id=f.parent.name) for f in sorted(directory.glob("*/record.json"), reverse=True)[:100]]

    def restore(self, ident):
        if not re.fullmatch(r"[0-9TZ.+-]+", ident):
            raise UserError("Invalid configuration history ID")
        directory = contained(self.layout.home / "configs/history", ident)
        record = read_json(directory / "record.json")
        if not record:
            raise UserError("Configuration history not found")
        target = contained(self.layout.home, record["path"])
        if digest(directory / "content") != record["sha256"]:
            raise UserError("Prior configuration failed its integrity check")
        with self.layout.mutation:
            if self.server.running():
                raise UserError("Stop the server before restoring configuration")
            self.storage.reserve(2 * 1024 * 1024)
            if target.exists():
                self.snapshot(target)
            atomic_write(target, (directory / "content").read_bytes())
        return {"restored": record["path"]}

    def mod_forms(self):
        # Version-specific field paths are deliberately explicit, not invented from labels.
        schemas = read_json(Path(__file__).resolve().parents[1] / "catalog/config-schemas.json", [])
        forms = []
        for schema in schemas:
            relative = schema["file"]
            path = contained(self.layout.server, relative)
            if not path.is_file():
                forms.append(dict(schema, available=False, reason="Generated after the first successful mod load"))
                continue
            try:
                value = json.loads(path.read_text(encoding="utf-8")) if path.suffix == ".json" else tomllib.loads(path.read_text(encoding="utf-8"))
                for key in schema["path"]:
                    value = value[key]
                forms.append(dict(schema, available=True, current=value, expected=digest(path)))
            except (KeyError, ValueError):
                forms.append(dict(schema, available=False, reason="Pinned schema does not match this generated file"))
        return forms

    def update_mod(self, ident, value, expected):
        schema = next((s for s in self.mod_forms() if s["id"] == ident), None)
        if not schema or not schema["available"]:
            raise UserError("This pinned configuration field is not available yet")
        validate_value(value, schema)
        if not expected or expected != schema["expected"]:
            raise UserError("Configuration changed; reload the form before saving")
        raw = self.raw(schema["file"])
        if Path(schema["file"]).suffix == ".json":
            data = json.loads(raw["content"])
            target = data
            for part in schema["path"][:-1]:
                target = target[part]
            target[schema["path"][-1]] = value
            content = json.dumps(data, indent=2) + "\n"
        else:
            # Change exactly one scalar inside its exact table, preserving comments,
            # order, unrelated values and array-of-table sections.
            table, key = ".".join(schema["path"][:-1]), schema["path"][-1]
            section, count, lines = "", 0, []
            for line in raw["content"].splitlines(True):
                match = re.match(r"\s*\[([^\[\]]+)\]\s*(?:#.*)?$", line.rstrip())
                if match:
                    section = match[1]
                elif re.match(r"\s*\[\[", line):
                    section = "<array>"
                if section == table and re.match(r"\s*" + re.escape(key) + r"\s*=", line):
                    encoded = json.dumps(value)
                    line = re.sub(r"^(\s*" + re.escape(key) + r"\s*=\s*)[^#\r\n]+", lambda m: m[1] + encoded + " ", line)
                    count += 1
                lines.append(line)
            if count != 1:
                raise UserError("Generated TOML no longer matches the pinned scalar schema")
            content = "".join(lines)
        return self.raw_save(schema["file"], content, expected)
