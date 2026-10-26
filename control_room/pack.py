"""Exact-version resolution, Packwiz generation and static JAR verification."""
from __future__ import annotations

import io
import json
import re
import tomllib
import urllib.parse
import zipfile
from copy import deepcopy
from pathlib import Path

from .common import REPO, UserError, atomic_write, digest, read_json, utcnow, write_json
from .network import api, download

STATUSES = {"Integrated and tested", "Integrated but awaiting runtime validation", "Alternative selected",
            "Incompatible, with evidence", "Unresolved, with investigation details"}


def stable(version):
    return version["version_type"] == "release" and not re.search(r"(?:alpha|beta|(?:^|[-.])rc(?:[.\d]|$))", version["version_number"], re.I)


def compatible(version, kind="mod"):
    return "1.21.1" in version["game_versions"] and ("neoforge" in version["loaders"] if kind == "mod" else "iris" in version["loaders"])


def resolve_project(value):
    if not isinstance(value, str) or not value.strip():
        raise UserError("Enter a mod name, Modrinth project ID or project URL")
    if "://" in value:
        parsed = urllib.parse.urlsplit(value)
        if parsed.hostname not in ("modrinth.com", "www.modrinth.com") or parsed.scheme != "https":
            raise UserError("Use a Modrinth project URL. CurseForge needs an authorized API key and its separate lookup control.")
        parts = parsed.path.strip("/").split("/")
        if len(parts) < 2 or parts[0] not in ("mod", "project", "shader"):
            raise UserError("Enter a complete Modrinth project URL")
        value = parts[1]
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value):
        raise UserError("Choose an exact project from search results")
    return api("/project/" + value)


class Resolver:
    def __init__(self, metadata_dir=None):
        self.metadata_dir = metadata_dir
        self.projects, self.versions = {}, {}
        if metadata_dir and Path(metadata_dir).exists():
            for path in Path(metadata_dir).glob("*.json"):
                data = read_json(path, {})
                project = data.get("project")
                if project:
                    self.projects[project["id"]] = self.projects[project["slug"]] = project
                for version in data.get("versions_1_21_1", []):
                    self.versions[version["id"]] = version

    def project(self, value):
        if value not in self.projects:
            project = resolve_project(value)
            self.projects[project["id"]] = self.projects[project["slug"]] = project
        return self.projects[value]

    def version(self, ident):
        if ident not in self.versions:
            self.versions[ident] = api("/version/" + ident)
        return self.versions[ident]

    def select(self, project, requested=None, kind="mod", allow_prerelease=False):
        if requested:
            version = self.version(requested)
            if version["project_id"] != project["id"] or not compatible(version, kind):
                raise UserError("Exact version does not match the selected project/NeoForge 1.21.1")
            if not stable(version) and not allow_prerelease:
                raise UserError(project["title"] + " is a prerelease and needs an explicit reviewed exception")
            return version
        versions = api("/project/" + project["id"] + "/version", {"game_versions": json.dumps(["1.21.1"])})
        candidates = [v for v in versions if compatible(v, kind) and (allow_prerelease or stable(v))]
        if not candidates:
            raise UserError(project["title"] + " has no eligible NeoForge 1.21.1 release")
        version = candidates[0]
        self.versions[version["id"]] = version
        return version

    def item(self, project, version, choice=None):
        choice = choice or {}
        files = [f for f in version["files"] if f.get("primary")]
        if len(files) != 1:
            if len(version["files"]) == 1:
                files = version["files"]
            else:
                raise UserError("Select one exact primary file for " + project["title"])
        file = files[0]
        if not re.fullmatch(r"[^/\\:]+\.(jar|zip)", file["filename"], re.I):
            raise UserError("Upstream filename is unsafe")
        if not 0 < file["size"] <= 256 * 1024 * 1024:
            raise UserError("Upstream file is outside the bounded download policy")
        side = choice.get("side")
        if not side:
            side = "client" if project["server_side"] == "unsupported" else "server" if project["client_side"] == "unsupported" else "both"
        return {"project_id": project["id"], "slug": project["slug"], "name": project["title"],
                "version_id": version["id"], "version": version["version_number"], "release_type": version["version_type"],
                "filename": file["filename"], "url": file["url"], "hashes": file["hashes"], "size": file["size"],
                "side": side, "kind": choice.get("kind", "mod"), "request": choice.get("request"),
                "world_sensitive": choice.get("world_sensitive", any(c in project.get("categories", []) for c in ["worldgen", "adventure", "decoration", "technology", "food", "mobs", "equipment"])),
                "optional": choice.get("optional", False), "default": choice.get("default", True),
                "dependencies": version["dependencies"], "license": project["license"],
                "source": "https://modrinth.com/" + ("shader/" if choice.get("kind") == "shader" else "mod/") + project["slug"],
                "selection_reason": choice.get("reason", "Exact release reviewed for this candidate; JAR constraints and runtime gates still apply."),
                "status": "Integrated but awaiting runtime validation", "validation": {"metadata": "pass", "jar": "pending", "runtime": "not run"}}

    def resolve(self, choices, baseline=None):
        items = {m["project_id"]: deepcopy(m) for m in baseline or []}
        queue = []
        for choice in choices:
            project = self.project(choice["project"])
            version = self.select(project, choice.get("version"), choice.get("kind", "mod"), choice.get("allow_prerelease", False))
            item = self.item(project, version, choice)
            items[project["id"]] = item
            queue.append(item)
        processed = set()
        while queue:
            item = queue.pop(0)
            if (item["project_id"], item["version_id"], item["side"]) in processed:
                continue
            processed.add((item["project_id"], item["version_id"], item["side"]))
            for dependency in item["dependencies"]:
                if dependency["dependency_type"] != "required":
                    continue
                pid, vid = dependency["project_id"], dependency["version_id"]
                if not pid and vid:
                    pid = self.version(vid)["project_id"]
                if not pid:
                    raise UserError("Unresolved required dependency of " + item["name"])
                if pid in items:
                    if vid and items[pid]["version_id"] != vid:
                        raise UserError(item["name"] + " requires an exact version of " + items[pid]["name"] + ": " + vid)
                    if item["side"] == "both" and items[pid]["side"] == "client":
                        if self.project(pid)["server_side"] == "unsupported":
                            raise UserError(item["name"] + " requires the client-only selected dependency " + items[pid]["name"])
                        items[pid]["side"] = "both"
                        queue.append(items[pid])
                    continue
                project = self.project(pid)
                version = self.select(project, vid)
                child = self.item(project, version, {"side": "client" if item["side"] == "client" else None,
                    "reason": "Required dependency of " + item["name"]})
                # A client-only parent's dependencies must not leak onto the dedicated server.
                if item["side"] == "client":
                    child["side"] = "client"
                items[pid] = child
                queue.append(child)
        problems = validate_graph(list(items.values()))
        if problems:
            raise UserError("; ".join(problems))
        return sorted(items.values(), key=lambda m: m["name"].lower())


def validate_graph(items):
    projects = {m["project_id"]: m for m in items}
    versions = {m["version_id"] for m in items}
    errors, names = [], set()
    for item in items:
        if item["filename"].lower() in names:
            errors.append("Duplicate filename: " + item["filename"])
        names.add(item["filename"].lower())
        for dep in item["dependencies"]:
            pid, vid, kind = dep.get("project_id"), dep.get("version_id"), dep["dependency_type"]
            if kind == "required" and ((pid and pid not in projects) or (vid and vid not in versions)):
                errors.append(item["name"] + ": missing required dependency " + str(pid or vid))
            if kind == "incompatible" and ((pid in projects and not vid) or vid in versions):
                errors.append(item["name"] + ": incompatible with " + str(pid or vid))
        if item["side"] not in ("client", "server", "both"):
            errors.append("Unknown side for " + item["name"])
    if "roxy" in {m["slug"] for m in items} and any(m["slug"] == "distanthorizons" for m in items):
        errors.append("Roxy/Voxy and Distant Horizons cannot share a client profile")
    return errors


def generate_pack(directory: Path, lock):
    directory.mkdir(parents=True, exist_ok=True)
    files = []
    for item in lock["mods"]:
        shader = item["kind"] == "shader"
        relative = ("shaderpacks/" if shader else "mods/") + item["slug"] + ".pw.toml"
        quote = lambda x: json.dumps(x, ensure_ascii=False)
        hashes = item["hashes"]
        algorithm = "sha512" if "sha512" in hashes else "sha256" if "sha256" in hashes else "sha1"
        text = f"name = {quote(item['name'])}\nfilename = {quote(item['filename'])}\nside = {quote(item['side'])}\n\n[download]\nurl = {quote(item['url'])}\nhash-format = {quote(algorithm)}\nhash = {quote(hashes[algorithm])}\n"
        if item.get("provider", "modrinth") == "modrinth":
            text += f"\n[update.modrinth]\nmod-id = {quote(item['project_id'])}\nversion = {quote(item['version_id'])}\n"
        if item.get("optional"):
            text += f"\n[option]\noptional = true\ndefault = {str(item['default']).lower()}\ndescription = {quote(item['selection_reason'])}\n"
        atomic_write(directory / relative, text)
        files.append((relative, digest(directory / relative), True))
    # Include only explicit pack payload paths; reports and server secrets never enter the index.
    for folder in ["config", "defaultconfigs"]:
        for path in sorted((directory / folder).rglob("*")) if (directory / folder).exists() else []:
            if path.is_file():
                files.append((path.relative_to(directory).as_posix(), digest(path), False))
    for name in ["options.txt"]:
        path = directory / name
        if path.is_file():
            files.append((name, digest(path), False))
    index = 'hash-format = "sha256"\n' + "".join(f'\n[[files]]\nfile = {json.dumps(name)}\nhash = "{value}"\nmetafile = {str(meta).lower()}\n' for name, value, meta in sorted(files))
    atomic_write(directory / "index.toml", index)
    pack = f'name = "A World for Two"\nauthor = "KG & Sera"\nversion = "{lock["version"]}"\npack-format = "packwiz:1.1.0"\n\n[index]\nfile = "index.toml"\nhash-format = "sha256"\nhash = "{digest(directory / "index.toml")}"\n\n[versions]\nminecraft = "1.21.1"\nneoforge = "{lock["neoforge"]}"\n\n[options]\nacceptable-game-versions = ["1.21.1"]\n'
    atomic_write(directory / "pack.toml", pack)
    return digest(directory / "pack.toml")


def validate_pack(directory, lock):
    errors = validate_graph(lock["mods"])
    try:
        pack = tomllib.loads((directory / "pack.toml").read_text(encoding="utf-8"))
        if pack["version"] != lock["version"] or pack["versions"] != {"minecraft": "1.21.1", "neoforge": lock["neoforge"]}:
            errors.append("Pack version differs from the generated release lock")
        if digest(directory / "index.toml") != pack["index"]["hash"]:
            errors.append("Packwiz index hash mismatch")
        index = tomllib.loads((directory / "index.toml").read_text(encoding="utf-8"))
        expected = {m["slug"]: m for m in lock["mods"]}
        seen = set()
        for entry in index["files"]:
            path = directory / entry["file"]
            if not path.resolve().is_relative_to(directory.resolve()):
                errors.append("Pack index path escapes the pack")
                continue
            if not path.is_file() or digest(path) != entry["hash"]:
                errors.append("Indexed file hash mismatch: " + entry["file"])
                continue
            if entry.get("metafile"):
                meta = tomllib.loads(path.read_text(encoding="utf-8"))
                slug = path.name.removesuffix(".pw.toml")
                if slug not in expected:
                    errors.append("Untracked mod: " + slug)
                    continue
                item = expected[slug]
                if meta["filename"] != item["filename"] or meta["side"] != item["side"] or meta["download"].get("url") != item["url"]:
                    errors.append("Metadata differs from the lock: " + slug)
                if meta["download"]["hash"] != item["hashes"].get(meta["download"]["hash-format"]):
                    errors.append("Download hash differs: " + slug)
                seen.add(slug)
        if seen != set(expected):
            errors.append("Pack index and compatibility lock have different inventories")
    except (KeyError, ValueError, OSError) as exc:
        errors.append("Invalid Packwiz manifest: " + str(exc))
    return errors


def version_key(value):
    return tuple(int(x) if x.isdigit() else x.lower() for x in re.findall(r"\d+|[a-zA-Z]+", str(value)))


def compare_versions(left, right):
    a, b = version_key(left), version_key(right)
    for x, y in zip(a, b):
        if type(x) is type(y):
            if x != y:
                return 1 if x > y else -1
        else:
            return 1 if isinstance(x, int) else -1
    return (len(a) > len(b)) - (len(a) < len(b))


def in_range(version, constraint):
    if not constraint or constraint in ("*", "[0,)"):
        return True
    constraint = str(constraint)
    if constraint.startswith(("[", "(")):
        # Maven/NeoForge union of intervals, e.g. (,1.0],[1.2,).
        intervals = re.findall(r"([\[(])([^\[\]()]*)([\])])", constraint)
        if not intervals:
            return False
        for low_marker, body, high_marker in intervals:
            if "," not in body:
                if compare_versions(version, body) == 0:
                    return True
                continue
            low, high = [x.strip() for x in body.split(",", 1)]
            low_cmp = compare_versions(version, low) if low else 1
            high_cmp = compare_versions(version, high) if high else -1
            if (not low or low_cmp > 0 or low_cmp == 0 and low_marker == "[") and (not high or high_cmp < 0 or high_cmp == 0 and high_marker == "]"):
                return True
        return False
    # Maven bare versions are recommendations with Restriction.EVERYTHING, not [exact].
    return True


def loader_supports(modid, version, constraint, neoforge):
    if in_range(version, constraint):
        return True
    # Reproduce FancyModLoader's own 1.21.1 VersionSupportMatrix, without changing
    # upstream metadata. Source: neoforged/FancyModLoader, branch 1.21.1,
    # loader/src/main/java/net/neoforged/fml/loading/VersionSupportMatrix.java.
    if neoforge.startswith("21.1."):
        aliases = {"minecraft": "1.21", "neoforge": "21.0.166"}
        return modid in aliases and in_range(aliases[modid], constraint)
    return False


def jar_metadata(path: Path):
    def inspect(archive, nested=False):
        mods, dependencies, embedded = [], [], []
        meta_name = next((name for name in ("META-INF/neoforge.mods.toml", "META-INF/mods.toml") if name in archive.namelist()), None)
        if meta_name:
            if archive.getinfo(meta_name).file_size > 1024 * 1024:
                raise UserError("Oversized JAR metadata")
            data = tomllib.loads(archive.read(meta_name).decode("utf-8-sig"))
            manifest = archive.read("META-INF/MANIFEST.MF").decode(errors="replace") if "META-INF/MANIFEST.MF" in archive.namelist() else ""
            declared = re.search(r"^Implementation-Version:\s*(.+)$", manifest, re.M)
            for item in data.get("mods", []):
                version = str(item.get("version", ""))
                if "${file.jarVersion}" in version:
                    version = declared[1].strip() if declared else "unresolved"
                mods.append({"id": item["modId"], "version": version, "embedded": nested})
            for owner, entries in data.get("dependencies", {}).items():
                for entry in entries:
                    dependencies.append(dict(entry, owner=owner))
        # Only inspect one level of known JarJar libraries, with strict byte limits.
        if not nested and "META-INF/jarjar/metadata.json" in archive.namelist():
            meta = archive.getinfo("META-INF/jarjar/metadata.json")
            if meta.file_size > 1024 * 1024:
                raise UserError("Oversized JarJar metadata")
            data = json.loads(archive.read(meta))
            for entry in data.get("jars", []):
                name = entry["path"]
                info = archive.getinfo(name)
                if info.file_size > 128 * 1024 * 1024:
                    raise UserError("Oversized embedded dependency")
                with zipfile.ZipFile(io.BytesIO(archive.read(info))) as child:
                    child_mods, child_deps, _ = inspect(child, True)
                    embedded.extend(child_mods)
                    dependencies.extend(child_deps)
        service = "META-INF/services/net.neoforged.neoforgespi.language.IModLanguageLoader"
        language_provider = service in archive.namelist() or any("Kotlin" in n and "LanguageProvider" in n for n in archive.namelist())
        return mods, dependencies, embedded
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad:
            raise UserError("Corrupt JAR entry: " + bad)
        mods, deps, embedded = inspect(archive)
        manifest = archive.read("META-INF/MANIFEST.MF").decode(errors="replace") if "META-INF/MANIFEST.MF" in archive.namelist() else ""
        library = bool(re.search(r"^FMLModType:\s*(LIBRARY|LANGPROVIDER)\s*$", manifest, re.M))
        return {"mods": mods, "dependencies": deps, "embedded": embedded, "library": library}


def cache_files(lock, directory, storage, notify=lambda _: None, side=None):
    directory.mkdir(parents=True, exist_ok=True)
    items = [m for m in lock["mods"] if side is None or m["side"] in (side, "both")]
    storage.reserve(sum(m["size"] for m in items if not (directory / m["filename"]).exists()))
    for item in items:
        path = directory / item["filename"]
        algorithm = "sha512" if "sha512" in item["hashes"] else "sha256" if "sha256" in item["hashes"] else "sha1"
        if path.exists():
            if path.stat().st_size != item["size"] or digest(path, algorithm) != item["hashes"][algorithm]:
                raise UserError("Cached bytes differ from the pinned file: " + item["filename"])
            continue
        download(item["url"], path, item["size"], item["hashes"][algorithm], algorithm, storage, notify)
    return items


def validate_jars(lock, directory):
    errors, warnings, records = [], [], {}
    for side in ["client", "server"]:
        provided = {"minecraft": "1.21.1", "neoforge": lock["neoforge"], "java": "21", "javafml": "4"}
        dependencies = []
        direct = set()
        unresolved = set()
        for item in lock["mods"]:
            if item["kind"] == "shader" or item["side"] not in (side, "both") or item.get("optional") and not item.get("default", True):
                continue
            path = directory / item["filename"]
            if not path.exists():
                errors.append(side + ": missing cached JAR " + item["filename"])
                continue
            try:
                metadata = records.setdefault(item["filename"], jar_metadata(path))
            except (ValueError, KeyError, zipfile.BadZipFile) as exc:
                errors.append(item["name"] + ": invalid JAR " + str(exc))
                continue
            if not metadata["mods"] and not metadata.get("library"):
                errors.append(item["name"] + ": no NeoForge mod declaration")
            for mod in metadata["mods"]:
                if mod["id"] in direct:
                    errors.append(side + ": duplicate mod ID " + mod["id"])
                direct.add(mod["id"])
                provided[mod["id"]] = mod["version"]
                if mod["version"] == "unresolved":
                    unresolved.add(mod["id"])
            for mod in metadata["embedded"]:
                provided.setdefault(mod["id"], mod["version"])
                if mod["version"] == "unresolved":
                    unresolved.add(mod["id"])
            dependencies.extend(metadata["dependencies"])
        for dep in dependencies:
            dependency_side = dep.get("side", "BOTH").lower()
            if dependency_side not in ("both", side):
                continue
            required = dep.get("type", "required" if dep.get("mandatory", True) else "optional")
            modid = dep["modId"]
            if required == "incompatible" and modid in provided and in_range(provided[modid], dep.get("versionRange", "*")):
                errors.append(side + ": " + dep["owner"] + " conflicts with " + modid)
            if required not in ("required", "optional"):
                continue
            if modid not in provided:
                if required == "required":
                    errors.append(side + ": " + dep["owner"] + " requires missing " + modid + " " + dep.get("versionRange", ""))
                continue
            if modid in unresolved:
                warnings.append(side + ": cannot statically resolve bundled version for " + modid)
            elif not loader_supports(modid, provided[modid], dep.get("versionRange", "*"), lock["neoforge"]):
                errors.append(side + ": " + dep["owner"] + " needs " + modid + " " + dep.get("versionRange", "") + "; selected " + provided[modid])
    return {"at": utcnow(), "tier": "static JAR and dependency metadata, not runtime", "errors": sorted(set(errors)),
            "warnings": sorted(set(warnings)), "jars": records}


def verify_installed(layout):
    receipt = read_json(layout.server / "installed.json", {})
    errors = []
    expected = receipt.get("files", {})
    for name, sha in expected.items():
        path = layout.server / "mods" / name
        if not path.is_file() or digest(path) != sha:
            errors.append("Missing or modified server file: " + name)
    actual = {p.name for p in (layout.server / "mods").glob("*.jar")}
    if actual != set(expected):
        errors.append("Server contains an unexpected mod inventory")
    if not receipt:
        errors.append("Server installation receipt is missing")
    return errors
