"""Generate both compatibility views from the same complete request inventory."""
from __future__ import annotations

from control_room.common import REPO, read_json, utcnow, write_json, atomic_write

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


def generate():
    requests = read_json(REPO / "catalog/requests.json")["requests"]
    lock = read_json(REPO / "catalog/lock.json")
    installed = {m["request"]: m for m in lock["mods"] if m.get("request")}
    values = []
    for key, name, group in requests:
        mod = installed.get(key)
        research = read_json(REPO / "evidence/research" / (key + ".json"), {})
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
        values.append({"id": key, "name": name, "group": group, "status": status,
                       "version": version, "side": mod["side"] if mod else None,
                       "project_id": mod["project_id"] if mod else project.get("id"),
                       "reason": reason, "source": source,
                       "runtime": mod.get("validation", {}).get("runtime", "not run") if mod else "not run"})
    data = {"generated": utcnow(), "pack_version": lock["version"], "requests": values,
            "evidence_boundary": "Pinned metadata/static JAR checks are not client, graphics, feature or multiplayer acceptance."}
    write_json(REPO / "catalog/compatibility.json", data)
    text = "# Compatibility inventory\n\nGenerated from the complete request inventory and the exact Packwiz release lock.\n\n" + data["evidence_boundary"] + "\n\n"
    text += "| Requested item | Decision | Exact selected version | Evidence / limitation |\n|---|---|---|---|\n"
    for row in values:
        reason = row["reason"].replace("|", "/").replace("\n", " ")
        source = f" [Source]({row['source']})" if row["source"] else ""
        text += f"| {row['name']} | {row['status']} | {row['version'] or '—'} | {reason}{source} |\n"
    text += "\n## Exact resolved file inventory\n\n| File / project | Exact version | Side | File hash |\n|---|---|---|---|\n"
    for mod in lock["mods"]:
        alg = "sha512" if "sha512" in mod["hashes"] else "sha256" if "sha256" in mod["hashes"] else "sha1"
        text += f"| {mod['name']} | {mod['version']} | {mod['side']} | {alg}: `{mod['hashes'][alg]}` |\n"
    atomic_write(REPO / "docs/COMPATIBILITY.md", text)
    print(f"Generated {len(values)} request records and {len(lock['mods'])} exact file records")


if __name__ == "__main__":
    generate()
