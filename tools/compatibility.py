"""Generate both compatibility views from the same complete request inventory."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path

from control_room.common import REPO, UserError, read_json, write_json, atomic_write, digest

DECISIONS = {
    "chocapic13-shaders": ("Unresolved, with investigation details", "The original author’s V9 and V9.1 beta files are legacy OptiFine-era releases without established Iris/DH support. The official CurseForge download refused automated retrieval (HTTP 403), and no authorized API key is present. An unchanged author download and native client test are required; Bliss is documented as a derivative, not substituted for the requested original.", None),
    "pastel-shaders": ("Unresolved, with investigation details", "The author’s 1.200 release offers pastel color schemes and a cozy style, but its published version list stops at 1.21 and this exact build’s DH support is unverified. Retained for investigation; Bliss, BSL and Solas provide the initial cozy choices.", None),
    "dairatz": ("Incompatible, with evidence", "The author publishes Fabric 0.4-beta for Minecraft 1.21.1. Native NeoForge 1.1.1 requires Minecraft 1.21.11 and NeoForge 21.11.42, not this 1.21.1 / 21.1 stack. Official release JAR descriptors and source properties were inspected. No matching native backport is available; Fairy Tales supplies complementary abilities but is not represented as Dairatz tameable fairies.", None),
    "create-pipes": ("Alternative selected", "Hypertubes handles players and Overpressure handles pneumatic items; Create's native vertical and diagonal Chutes remain available. No third item network is enabled before a distinct gameplay requirement and measured benefit are established.", "create-overpressure"),
    "create-pneumatic-express": ("Alternative selected", "Overpressure is the selected pneumatic item system. A second overlapping logistics implementation is not enabled without a complementary feature and compatibility proof.", "create-overpressure"),
    "create-pipe-connector": ("Unresolved, with investigation details", "Retained as a potential building convenience. Exact native loader/Create version and interaction with the selected pneumatic system need verification before inclusion.", None),
    "pirates-n-ships": ("Unresolved, with investigation details", "The v0.3.0 beta artifact and Sable 2.0.6 dependencies were acquired for an isolated compatibility experiment. AI ships, physics, artillery overlap, restart and destruction protections remain untested. Existing Small Ships, Aeronautics and Big Cannons are preserved; the beta is not in the active candidate.", None),
    "black-powder-age-of-sail": ("Unresolved, with investigation details", "The 2.3.0 artifact is retained for an isolated naval/artillery experiment. Overlap with Big Cannons and Pirate Guns and build protection remain untested; it is not installed alongside those systems by assumption.", None),
    "voxy": ("Alternative selected", "Distant Horizons + SeedGen explicitly replaces Voxy under the owner's addendum. No active dependency or profile includes it.", "distanthorizons"),
    "roxy": ("Alternative selected", "Superseded by the owner's definitive Distant Horizons decision. Roxy is not installed or required.", "distanthorizons"),
    "voxy-seedgen": ("Alternative selected", "Superseded by Distant Horizons SeedGen; no further Voxy implementation work is planned.", "dh-seedgen"),
    "lod-server-support": ("Alternative selected", "The selected DH/SeedGen server-client architecture supplies distant terrain; a separate Voxy transport is not installed.", "distanthorizons"),
    "travelers-backpack": ("Alternative selected", "Owner chose Sophisticated Backpacks and its Create integration. Do not install both systems.", "sophisticated-backpacks"),
    "fog": ("Alternative selected", "Owner excluded Fog from defaults. Preserve DH/shader fog and evaluate Advanced Weather's native effects first.", "advanced-weather"),
    "better-fog": ("Unresolved, with investigation details", "Optional only after measured shader/DH/weather tests demonstrate an improvement; excluded from defaults.", None),
    "flying-squirrels": ("Alternative selected", "Animal Garden: Sugar Glider supplies gliding pets on NeoForge 1.21.1. Sugar gliders are marsupials, not flying squirrels. Exact squirrel searches found no verified matching flying-squirrel mod for this stack.", "flying-squirrels"),
    "c2me": ("Incompatible, with evidence", "Official C2ME is Fabric. DH SeedGen's author additionally documents device-dependent C2ME/noise-optimizer incompatibility. Connector forks are excluded from this NeoForge candidate.", None),
    "scalablelux": ("Incompatible, with evidence", "Sable 2.0.6's actual neoforge.mods.toml declares ScalableLux incompatible. It is excluded.", None),
    "world-height": ("Alternative selected", "Retain the vanilla -64..319 build range. No raised-height serialization/rendering profile has passed the required Sable, terrain, DH and performance tests.", "tectonic"),
    "biomes-weve-gone": ("Alternative selected", "Regions Unexplored is the selected block/biome expansion. Adding another broad biome pool before distribution/spawn testing risks excessive overlap.", "regions-unexplored"),
    "natures-spirit": ("Alternative selected", "Regions Unexplored is selected for the first terrain comparison; this compatible alternative remains documented.", "regions-unexplored"),
    "immersive-interactions": ("Alternative selected", "Original project has no NeoForge 1.21.1 file in the captured metadata. Cinematic Interactions is the selected workstation animation system.", "cinematic-interactions"),
    "kaleidoscope": ("Alternative selected", "Kaleidoscope Cookery is integrated. The separately named Kaleidoscope is a deprecated client color/fog mod migrated to Fuzz, not a cooking system; it has no matching NeoForge 1.21.1 file.", "kaleidoscope-cookery"),
    "flame": ("Unresolved, with investigation details", "Exact-name research found a Flame torch resource pack and several unrelated particle/content projects. The intended project is ambiguous, so no unrelated substitute is silently installed.", None),
    "derivative": ("Unresolved, with investigation details", "Identified the removed Modrinth Derivative Shader listing, the DERCODE recode, and DureXXX's CurseForge Derivative [main] (1604307). ARR distribution and exact Iris 1.8/DH compatibility remain unverified; no shader is renamed or substituted.", None),
    "lodgen": ("Unresolved, with investigation details", "Exact Modrinth search found no project under this name. DH + SeedGen is selected; unknown tools are not introduced.", None),
    "servercore": ("Unresolved, with investigation details", "NeoForge 1.21.1 releases exist. Excluded pending a measured A/B run with the mandatory optimizers and weather/SeedGen; no unsupported improvement claim is made.", None),
    "alternate-current": ("Unresolved, with investigation details", "A matching NeoForge file exists; redstone behavior with Create and actual tick improvements need an isolated A/B test before inclusion.", None),
    "fastsuite": ("Unresolved, with investigation details", "Matching NeoForge file found. Recipe-heavy Create/cooking interactions and actual benefit are unmeasured; retained as a benchmark candidate.", None),
    "particle-rain": ("Unresolved, with investigation details", "Compatible loader file exists but Advanced Weather already provides custom precipitation. Do not enable a second particle/weather renderer without an overlap and storm-cost test.", None),
    "presence-footsteps": ("Unresolved, with investigation details", "The original is Fabric; a NeoForge beta port (pf-neoforge) exists. AmbientSounds and Sound Physics are selected while audio overlap and beta stability remain unmeasured.", None),
    "not-enough-animations": ("Alternative selected", "Smooth Player Animations is selected; its author lists NEA compatibility. Additional override/rendering tests are required before adding a second animation controller.", "smooth-animations"),
    "cosmetic-armor": ("Unresolved, with investigation details", "The exact requested Cosmetic Armor Reworked must be distinguished from the unrelated Fabric Cosmetic Armor and unofficial forks. Not substituted silently.", None),
    "seating": ("Alternative selected", "Take a Seat and Handcrafted supply seating without an additional generic controller.", "take-a-seat"),
    "greenhouse": ("Alternative selected", "Building/glass/roof collections, farming mods and Serene Seasons supply a greenhouse construction path; exact growth rules need in-game validation.", "serene-seasons"),
    "seasons": ("Alternative selected", "Serene Seasons is explicitly selected in the addendum; Advanced Weather includes season integration.", "serene-seasons"),
    "sable-ragdoll-corpse": ("Unresolved, with investigation details", "Available files are alpha. Inventory ownership must be proven configurable before combining physical corpses with the one selected grave system; inventory safety takes priority.", None),
    "sleep-tight": ("Alternative selected", "Excluded by atmosphere preference: nightmares, bedbugs and penalties overlap the peaceful sleep design. Use the selected bed system, Comforts and Sleep Through The Night.", "sleep-through-the-night"),
    "spartan-weaponry-reborn": ("Alternative selected", "Simply Swords + Better Combat is the requested primary weapon combination. Avoid adding a second broad arsenal.", "simply-swords"),
    "scythes-vanilla": ("Alternative selected", "Prefer the selected melee system's combat scythes and a distinct farming scythe if verified; avoid a duplicate combat arsenal.", "simply-swords"),
    "mimi": ("Unresolved, with investigation details", "A NeoForge release supports MIDI, but a third default instrument system is not enabled before checking overlap. Music Maker is preferred for piano; Immersive Melodies remains portable music.", "music-maker"),
    "wandering-pets": ("Unresolved, with investigation details", "NeoForge port found. Excluded until its roaming AI is checked against Doggy Talents Next and Cozy's Improved Cats ownership, teleportation and recovery.", None),
    "immersive-animals": ("Unresolved, with investigation details", "Exact-name Modrinth result is a chicken-coop mod with no matching NeoForge file; it does not establish the intended life-cycle project. No competing AI controller is installed.", None),
}


FILE_FIELDS = ("project_id", "slug", "name", "request", "kind", "version", "version_id",
               "filename", "size", "side", "optional", "default", "hashes", "source", "status", "validation")
PIN_FIELDS = ("project_id", "version_id", "filename", "hashes", "size", "side", "kind")

# These are immutable, tracked receipts, not a mutable acceptance cache. A changed
# receipt must be reviewed and rebound explicitly. No observation changes a lock
# status or runtime gate, including when a newer candidate reuses the same file.
RUNTIME_RECEIPTS = (
    ("client-startup-initial.json", "210d7712cb6441a18943f104e91b3e0583a3ea8f612b5dad07550104f9be7ce3",
     "Earlier licensed Prism client reached the owner-confirmed Minecraft main menu; native renderer initialization was recorded.",
     "This earlier pack startup is not current-candidate gameplay, shader, FPS or two-player acceptance."),
    ("owner-crafting-table-confirmation.json", "4f0e344440be6c4431adf502636bafb888a5253108341a32f4f0d366c1d8946d",
     "Owner confirmed responsive Minecraft chat/search and animation on a newly placed vanilla crafting table in the recorded earlier check.",
     "New-table interaction and observed responsiveness only; not every station, converted table or permanent-world candidate."),
    ("seedgen-native-fingerprint.json", "ec57684dbf95d53cd0aa47b8e7b21b85576e5791e7ff0f3548a85f5ae3f3c5d8",
     "Unmodified SeedGen 0.9.1 computed its fingerprint on actual dedicated-server modded registries with bridge 0.6.3 in candidate.17.",
     "Fresh client agreement, active generation fidelity and MapHorizons-to-Xaero map population remain unverified."),
    ("cinematic-native-parser.json", "1a22dc28806a74f139ef67378e83ae8fea572634e86ef80583aeed428879ab34",
     "The pinned Lumiera parser accepted the configured intro in a vanilla-registry bootstrap.",
     "Parser proof only; not native cinematic playback, multiplayer or a cinematic of the final settlement."),
    ("permanent-settlement-construction.json", "996ea225d2339cb4d755a4a660ff6b8531b30839f5438c2907c188afe8ef7b03",
     "Candidate.18 recorded zero native verification differences for the original core, pirate quarter and drawbridge structure; actual wheel/gear RPM snapshots were recorded.",
     "Block/state/inventory and native power evidence only; control cycles, later expansions, artistic quality and full mod-function acceptance remain separate."),
)

OBSERVATIONS = {
    "cinematic-interactions": ("owner-crafting-table-confirmation.json", "0.18.28", "sha256",
        "a710efafdee42186611fa8f4468acac5f14fa55bf4ff3c8386b13ee3fa81b997",
        "Earlier owner-confirmed new vanilla table animation and responsive input; full station and current-candidate multiplayer checks remain pending."),
    "visual-workbench": ("owner-crafting-table-confirmation.json", "21.1.2", "sha512",
        "3737a436143acc1c6f80d0633371dafb4e24026d585bf5afa80421e1d1d6bbd2243d040c43a70d6796377227c0762d058c27c2b16a3fb20d0c2602bd04ae2038",
        "Earlier repaired new vanilla table interaction was owner-confirmed. Existing converted inventories were preserved; not every workstation is accepted."),
    "dh-seedgen": ("seedgen-native-fingerprint.json", "0.9.1", "sha512",
        "4b0bbb0426d0d600fcef2deb0580f458bbf16b90440b84b9d28fe377a3107cf22ff9f166eec85b802cb5386d5af39d5b0a12ac6bf7ca04fad427206d1405c61d",
        "Native dedicated-server fingerprint passed on candidate.17 with bridge 0.6.3. Client agreement, activation and terrain fidelity remain unverified."),
    "maphorizons": ("seedgen-native-fingerprint.json", "1.1.0", "sha256",
        "da36054b9d59083481bfe9c946d17a2f0f87705a6d883718b26351848d40ff93",
        "A successful SeedGen server fingerprint does not prove that SeedGen LODs populate Xaero maps. That end-to-end check remains unverified."),
    "lumiera": ("cinematic-native-parser.json", "1.0.0-alpha.1+neoforge-1.21.1", "sha512",
        "05e2c3c510a64642d1e5d35a8fd430c0d3ab38b985f3453611d06b1f2e74241e7f43b6e99bc20e64ae03e1b634c517aae0aa84681f1fa1537defdf15a20d9228",
        "Pinned native parser accepted the configured intro. Final-settlement camera path and client playback remain separate."),
    "create": ("permanent-settlement-construction.json", "6.0.10+mc1.21.1", "sha512",
        "11cc8fc049d2f67f6548c7abfada6b82a3adb5c7ca410a742de04bbca76e03862c518721b88d806f6e6d768a4d68531fdb903a85859b25d1484d550cc7bafd4b",
        "Native structure checks and wheel/gear RPM were observed in candidate.18. Broad machinery, transport, logistics and complete control-cycle commissioning remain pending."),
}


def enabled(mod):
    return not mod.get("optional", False) or bool(mod.get("default", False))


def build_inventory(root=REPO):
    """Read source inputs only; never reuse claims from a prior generated output."""
    root = Path(root)
    requests = read_json(root / "catalog/requests.json")["requests"]
    lock_path = root / "catalog/lock.json"
    lock_bytes = lock_path.read_bytes()
    lock = json.loads(lock_bytes)
    lock_sha256 = hashlib.sha256(lock_bytes).hexdigest()
    installed = {m["request"]: m for m in lock["mods"] if m.get("request")}
    values = []
    for key, name, group in requests:
        mod = installed.get(key)
        research = read_json(root / "evidence/research" / (key + ".json"), {})
        project = research.get("project", {})
        if mod:
            status, reason = mod["status"], mod["selection_reason"]
            source, version = mod["source"], mod["version"]
        else:
            matching = [v for v in research.get("versions_1_21_1", []) if "neoforge" in v["loaders"]]
            status = "Unresolved, with investigation details"
            reason = ("Matching NeoForge 1.21.1 files found; dependency, integration and runtime review pending." if matching else
                      "No verified matching file selected. Exact project identity, loader support or overlap investigation remains in progress.")
            version = None
            source = "https://modrinth.com/project/" + project["id"] if project.get("id") else research.get('source')
        if key in DECISIONS:
            status, reason, alternative = DECISIONS[key]
            selected = installed.get(alternative) if alternative else None
            if selected:
                source, version = selected["source"], selected["version"]
        row = {"id": key, "name": name, "group": group, "status": status,
               "version": version, "side": mod["side"] if mod else None,
               "project_id": mod["project_id"] if mod else project.get("id"),
               "reason": reason, "source": source,
               "runtime": mod.get("validation", {}).get("runtime", "not run") if mod else "not run",
               "selected_by_default": bool(mod and enabled(mod)), "optional": bool(mod and mod.get("optional"))}
        if mod:
            row["file_pin"] = {k: mod[k] for k in PIN_FIELDS if k in mod}
            row["lock_validation"] = mod.get("validation", {})
        if key in DECISIONS and DECISIONS[key][2]:
            alternative = DECISIONS[key][2]
            row["selected_alternative"] = alternative
            if alternative in installed:
                row["selected_alternative_pin"] = {k: installed[alternative][k] for k in PIN_FIELDS if k in installed[alternative]}
        values.append(row)
    rows = {row["id"]: row for row in values}
    data = {"generated": lock.get("generated"), "generation_basis": "Source lock timestamp; unchanged inputs produce identical reports",
            "pack_version": lock["version"], "requests": values,
            "source_lock": {"path": "catalog/lock.json", "sha256": lock_sha256,
                            "pack_path": "packwiz/pack.toml", "pack_sha256": digest(root/"packwiz/pack.toml"),
                            "minecraft": lock["minecraft"], "neoforge": lock["neoforge"], "java": lock["java"],
                            "release_status": lock.get("release_status", "candidate")},
            "resolved_files": [{k: mod[k] for k in FILE_FIELDS if k in mod} for mod in lock["mods"]],
            "counts": {"requested_candidates": len(values), "resolved_files": len(lock["mods"]),
                       "mod_entries_including_optional": sum(m.get("kind") == "mod" for m in lock["mods"]),
                       "enabled_mod_entries": sum(m.get("kind") == "mod" and enabled(m) for m in lock["mods"]),
                       "shader_packs": sum(m.get("kind") == "shader" and enabled(m) for m in lock["mods"]),
                       "resource_packs": sum(m.get("kind") == "resourcepack" and enabled(m) for m in lock["mods"]),
                       "decision_statuses": dict(Counter(row["status"] for row in values))},
            "evidence_boundary": ("Candidate metadata, exact file hashes and static checks are distinct from runtime evidence. "
                "Earlier licensed startup and owner observations retain their original candidate/pack scope; they do not qualify "
                + lock["version"] + ", every feature, remote synchronization, shader combinations or two-player multiplayer. "
                "The lock retains its runtime gates. Construction, mechanism commissioning, persistence and visual acceptance are separate."),
            "runtime_evidence": [], "evidence_rejections": [], "isolated_candidates": []}
    evidence = {}
    for filename, expected, claim, boundary in RUNTIME_RECEIPTS:
        path = root/"evidence/runtime"/filename
        source = "evidence/runtime/"+filename
        receipt_bytes = path.read_bytes() if path.is_file() else None
        actual = hashlib.sha256(receipt_bytes).hexdigest() if receipt_bytes is not None else None
        if actual != expected:
            data["evidence_rejections"].append({"source": source, "expected_sha256": expected,
                                                "actual_sha256": actual, "reason": "Missing or changed immutable receipt; observation omitted pending review"})
            continue
        receipt = json.loads(receipt_bytes)
        entry = {"source": source, "source_sha256": actual, "at": receipt.get("at"),
                 "candidate": receipt.get("candidate"), "pack_sha256": receipt.get("pack_sha256"),
                 "claim": claim, "boundary": boundary}
        evidence[filename] = entry
        data["runtime_evidence"].append(entry)
    for key, (filename, version, algorithm, expected, note) in OBSERVATIONS.items():
        if key not in rows or filename not in evidence or key not in installed:
            continue
        mod = installed[key]
        matches = mod["version"] == version and mod.get("hashes", {}).get(algorithm) == expected
        rows[key]["runtime_observation"] = {"note": note, "evidence_source": evidence[filename]["source"],
            "evidence_sha256": evidence[filename]["source_sha256"], "observed_version": version,
            "observed_file_hash": {algorithm: expected}, "current_file_matches_observed_pin": matches,
            "evidence_scope": ("Limited prior-candidate observation; no lock runtime gate is promoted" if matches else
                               "Historical observation only: current artifact pin differs and has no acceptance from this receipt")}
    if "chocapic13-shaders" in rows:
        rows["chocapic13-shaders"]["reason"] += " The owner explicitly deferred Chocapic; it remains pending and absent from the active lock."
    experiments = read_json(root/"catalog/experiments.json", {})
    for label in ("pirates_n_ships", "blackpowder", "explorers_friend"):
        mod = experiments.get(label)
        if not mod:
            continue
        entry = {k: mod[k] for k in FILE_FIELDS if k in mod}
        entry["active_in_lock"] = any(item["project_id"] == mod["project_id"] for item in lock["mods"])
        data["isolated_candidates"].append(entry)
        row = rows.get(mod.get("request"))
        if row is None:
            continue
        row["investigated_artifact"] = {k: mod[k] for k in ("project_id", "version", "version_id", "filename", "hashes", "side", "source") if k in mod}
        if label == "explorers_friend" and not entry["active_in_lock"]:
            row["project_id"], row["source"] = mod["project_id"], mod["source"]
            row["reason"] = ("The exact native NeoForge 1.21.1 author release " + mod["version"] +
                " is pinned for an isolated comparison with squaremap. Modded block colors, rendering bounds, claims and overhead remain unmeasured. "
                "squaremap remains the active backend; the alternative is not enabled concurrently.")
    if digest(lock_path) != lock_sha256:
        raise UserError("The source lock changed during compatibility generation; rerun against the stable current lock")
    return data


def render_inventory(data):
    def clean(value):
        return str(value).replace("|", "/").replace("\n", " ")

    counts, lock = data["counts"], data["source_lock"]
    out = ["# Compatibility inventory", "",
           f"Current lock: **{data['pack_version']}**, Minecraft {lock['minecraft']}, NeoForge {lock['neoforge']}, Java {lock['java']}.", "",
           f"{counts['requested_candidates']} requested candidates are retained. The lock contains {counts['resolved_files']} exact files: "
           f"{counts['mod_entries_including_optional']} mod entries ({counts['enabled_mod_entries']} enabled by default), "
           f"{counts['shader_packs']} client shader packs and {counts['resource_packs']} resource packs. "
           "Optional file defaults and sides are listed individually below.", "", data["evidence_boundary"], "",
           f"Lock SHA-256: `{lock['sha256']}`. Pack SHA-256: `{lock['pack_sha256']}`.", "", "## Recorded runtime scope", ""]
    for entry in data["runtime_evidence"]:
        out.append(f"- {entry['claim']} {entry['boundary']} [Receipt](../{entry['source']})")
    if not data["runtime_evidence"]:
        out.append("No unchanged reviewed runtime receipt is available. Pending runtime gates remain unchanged.")
    if data["evidence_rejections"]:
        out += ["", "Missing or changed receipts were omitted pending source review; previous generated annotations are never reused."]
    out += ["", "Chocapic remains deferred at the owner's request. Distant Horizons + SeedGen is selected; Voxy and Roxy remain excluded. "
            "Isolated investigation pins are listed separately from the active lock.", "", "## Complete request decisions", "",
            "| Requested item | Decision | Exact selected version | Evidence / limitation |", "|---|---|---|---|"]
    for row in data["requests"]:
        reason = clean(row["reason"])
        if row.get("runtime_observation"):
            observation = row["runtime_observation"]
            reason += " " + clean(observation["note"])
            if not observation["current_file_matches_observed_pin"]:
                reason += " Current artifact differs from the observed file; this receipt provides no current-pin acceptance."
        if row.get("optional"):
            reason += " Optional; enabled by default." if row["selected_by_default"] else " Optional; disabled by default."
        if row.get("investigated_artifact"):
            reason += " Investigation pin: " + row["investigated_artifact"]["version"] + "; see the separate candidate table."
        source = f" [Source]({row['source']})" if row.get("source") else ""
        out.append(f"| {clean(row['name'])} | {row['status']} | {clean(row['version'] or '—')} | {reason}{source} |")
    out += ["", "## Exact resolved file inventory", "",
            "These are top-level downloadable files; bundled nested loader libraries are not additional selected mods. "
            "All pins and hashes come from the current lock. An exact file pin is not a runtime approval.", "",
            "| Project / exact filename | Exact version | Side | Default | File hash |", "|---|---|---|---|---|"]
    for mod in data["resolved_files"]:
        algorithm = next(key for key in ("sha512", "sha256", "sha1") if key in mod["hashes"])
        default = "On" if enabled(mod) else "Off (optional)"
        out.append(f"| {clean(mod['name'])}<br>`{mod['filename']}` | {clean(mod['version'])} | {mod['side']} | {default} | {algorithm}: `{mod['hashes'][algorithm]}` |")
    out += ["", "## Isolated candidate pins", "",
            "| Candidate | Exact version / filename | Side | Hash | Active status |", "|---|---|---|---|---|"]
    for mod in data["isolated_candidates"]:
        algorithm = next(key for key in ("sha512", "sha256", "sha1") if key in mod["hashes"])
        active = "Present in current lock; requires explicit status review" if mod["active_in_lock"] else "Isolated investigation; not installed in the active lock"
        out.append(f"| {clean(mod['name'])} [Source]({mod['source']}) | {mod['version']}<br>`{mod['filename']}` | {mod['side']} | {algorithm}: `{mod['hashes'][algorithm]}` | {active} |")
    out += ["", "Regenerate both complete views with `python -m tools.compatibility`. Runtime notes are bound to reviewed receipt hashes "
            "and original component pins. Changed receipts are omitted, and a changed lock or component cannot inherit prior acceptance. "
            "Unchanged inputs produce identical reports; the source lock timestamp is retained.", ""]
    return "\n".join(out)


def generate(root=REPO):
    root = Path(root)
    data = build_inventory(root)
    if digest(root/"catalog/lock.json") != data["source_lock"]["sha256"]:
        raise UserError("The source lock changed before report publication; rerun compatibility generation")
    write_json(root/"catalog/compatibility.json", data)
    atomic_write(root/"docs/COMPATIBILITY.md", render_inventory(data))
    print(f"Generated {len(data['requests'])} request records and {len(data['resolved_files'])} exact file records")
    return data


if __name__ == "__main__":
    generate()
