# The actual settlement cinematic

The prepared scenes use the installed **Lumiera 1.0.0-alpha.1 for NeoForge
1.21.1**, with camera positions fitted to the permanent settlement's real
construction plans. This is scene data for Lumiera's existing camera system.
It adds no renderer, player teleport, world command, actor, permanent chunk
ticket, forced terrain generation or global view-distance change.

The first-join candidate is **24 seconds** around the actual welcome plaza,
cottage, garden-facing village and nearby pirate-port approach. Rosewater Castle
and the harbor each have their own nearby-player replay. Each large sailing ship
has a separate local orbit. A complete castle-to-offshore first-join tour remains
pending a verified way to deliver its chunks and a real shader review.

No scene has been activated by this source tool. Real client rendering, network
coverage, skip/return behavior for these new scenes, lighting and visual
refinement remain unverified until runtime checks are recorded.

The source now requires all **ten exact constructed geometry inputs**: original
core, pirate quarter, drawbridge structure, expanded castle, south-bank district,
four large ships and final harbor access. Each plan must match its reviewed hash
and an archived native verification with the same plan hash, count, completion
time and zero failures. This is historical construction provenance; present
movement, player traversal and rendered visibility remain separate.

Harbor access comes from the final access manifest, with placed plan SHA
`e31b6d4782283b66219c551c3a345bb361ecafa0ab313340e0a767322beaa908`
and 4,148 positions. The older harbor aggregate contains an unplaced 4,036-position
access entry; it is deliberately ignored, without fallback. The offshore flagship
must match placed SHA
`c612729b69ef8d3a71faf1f56996b6ab6cd57c68adbe8fbb7c0cfbeb8e5fbc84`.
Every dense camera segment is resampled against the resulting exact overlay.
Older staged datapacks, manifests and failed probes are retained. A fresh
geometry-bound manifest does not activate a scene or replace a native parser test.

## Native format and server delivery

The author's [Lumiera description](https://modrinth.com/mod/lumiera/) documents
datapack cutscenes under `data/<namespace>/cutscenes/` and native playback/stop
commands. The exact installed JAR was also inspected directly; these are the
relevant pinned implementation facts:

- `CinematicsRegistry` extends Minecraft's `SimpleJsonResourceReloadListener`
  with the directory `cutscenes`. `CinematicsReloadHandlers` registers it in
  NeoForge's `AddReloadListenerEvent`.
- `CinematicsApi.playChained` obtains the server registry scene and sends
  `PlayCutscenePayload(sceneId, scene.toNBT(), anchorEntityId)` to that player.
  `ClientCutscenePackets.handlePlay` reconstructs the scene with
  `CinematicCutscene.fromNBT`, then calls the native sequencer.
- A server/world datapack therefore supplies these scene definitions; matching
  copies in each client's configuration are not needed for this packet path.
  The existing pinned Lumiera and text API must still be installed on clients.
- The installed `CameraPathDef.KeyframeDef` uses a `rot` object with `yaw`,
  `pitch` and `roll`, and camel-case `pathType`, `posTime`, `rotTime` and
  `fovTime`. The authoring tool writes those actual fields. Its native probe
  checks that positions, rotations, FOV and interpolation survive parsing.
- Camera keyframe times are seconds; `duration_ticks` is server tick units.
  These scenes use `camera_position_mode: absolute` and native linear segments.
  Dense points are smoothly authored offline, then their complete native
  polylines are checked against known construction.

The investigated JAR is:

`lumiera-neoforge-1.21.1-1.0.0-alpha.1.jar`

SHA-256:

`dadfcaab4fe335792f84b18d0f7d7ab499d54128c92f44cd25584aeff3f398d9`

The tool refuses a different JAR rather than assuming another release has the
same parser or network behavior. It includes an independent probe using the
mod's public parser and native NBT serialization. No Lumiera implementation is
copied or repackaged.

## Why the scenes are local

The observed official server configuration has **view-distance 6** and
**simulation-distance 4**. The owned client configuration observed during
preparation has render distance 8. New clients may choose a different value.
The six-chunk server radius is the limiting native terrain-delivery setting;
simulation distance is a different system.

The permanent spawn is around **1120, 67, −1130**. Rosewater Castle extends as
far as x1290 and z−919. The offshore Resolute is centered at **1140, −1450**.
Those locations cannot all be assumed to have real block geometry on a client
standing at spawn. A camera packet is not a chunk-streaming protocol. Loading a
server chunk or marking it forced also does not by itself send it to a distant
player's client.

Neither Distant Horizons nor SeedGen is assumed to contain the newly constructed
buildings. A distant terrain LOD is not proof of the current castle, sails,
furniture, lighting or pirate town. This source deliberately leaves the global
view distances alone.

Each scene has a manifest contract requiring the player to be safely standing
in the Overworld near its local center, with server and client distance at
least six chunks. Camera positions and look targets stay within a conservative
91-block envelope including the allowed player offset. The first-join camera
stays within approximately 62 blocks of the permanent plaza. These geometric
bounds do not prove client packet delivery or complete model visibility: actual
runtime coverage still needs inspection.

## Scene set

| Identifier | Length | Player proximity center | Contents |
| --- | --- | --- | --- |
| `awft:settlement_intro` | 24 s | 1120.5, 67, −1130.5; within 4 horizontal blocks | Cottage reveal, garden-facing village, welcome plaza and near-bank port approach |
| `awft:rosewater_castle_tour` | 20 s | 1221, 68, −996; within 16 horizontal blocks | Preserved keep, library, ballroom, observatory, Rose Court and southern gate |
| `awft:lanternwater_port_tour` | 18 s | 1120, 66, −1218; within 16 horizontal blocks | Pirate quarter, tavern frontage, quays and pier approach |
| `awft:rosewater_resolute_tour` | 18 s | Flagship center 1140, −1450; within 16 horizontal blocks | Offshore flagship's hull, cabin exterior, rig and partly unfurled sails |
| `awft:amberwake_tour` | 18 s | Ship center 1000, −1350; within 16 horizontal blocks | Amberwake exterior and furled rig |
| `awft:nightingales_debt_tour` | 18 s | Ship center 1110, −1344; within 16 horizontal blocks | Nightingale's Debt exterior and furled rig |
| `awft:sea_lavender_tour` | 18 s | Ship center 1230, −1376; within 16 horizontal blocks | Sea Lavender exterior and drying canvas |

The vessel centers, dimensions, sail states, deck levels and top heights are read
from the exact final harbor manifests and plans, not estimated from a generic
ship. The ship centers in the table are proximity centers, **not teleport
destinations**; a mast may occupy the exact center block. The player boards
normally and stands safely on deck before a replay. Native bridge checks reject
playback while in water, in a vehicle, on fire, sleeping or hurt.

All optional automatic location triggers remain **disabled recommendations**.
Control Room can replay an actually loaded scene for a selected online player,
but its current replay action does not enforce these new scene-specific
proximity contracts. Check the player's live coordinates before selecting a
local scene. Do not install enabled location triggers until the corresponding
scene's native visibility and clearance have been checked.

The actual first-join request is delayed by the existing bridge until a newly
joined player stands safely. First-join history is preserved. The scenes have a
short, quiet vanilla amethyst cue and a native title, with restrained letterbox
and fades. They do not replace the world's music, change weather/time, or leave
a long-running sound behind. Natural completion returns through Lumiera's own
cleanup; the last first-join point approaches the welcome plaza before fade-out.

## Staging and native parsing

Prepare the staged datapack:

```powershell
python -B -m tools.settlement_cinematic --home "D:\A World for Two"
```

This writes a unique `staging/settlement-cinematic-<identity>/` directory with:

- `awft-settlement-cinematic.zip`, containing `pack.mcmeta` and seven scenes.
- An expanded `datapack/` copy of exactly the same files for review.
- `manifest.json`, binding scene and archive hashes, construction geometry,
  player proximity contracts, clearance results and all remaining proof.

Preparation reads the verified-hash core, port, bridge, final castle,
south-bank plan and final four vessel/access plans. Reading a plan does not
prove it has been installed. All solid plan positions are treated conservatively
as full block cubes, including decorative models. Every camera segment is
sampled at at most 0.25-block intervals with a 0.7-block minimum clearance from
those cubes. Natural terrain, entities, culling, render models and visibility
remain separate checks.

The tool writes only its owned staging directory. It never installs a datapack,
runs a server command, changes settings, edits the first-join journal or modifies
Packwiz. Its bounded output guard reserves at most 16 MiB before writing.

Run the real parser/NBT probe against the returned directory:

```powershell
python -B -m tools.settlement_cinematic --home "D:\A World for Two" --native-probe "D:\A World for Two\staging\settlement-cinematic-<identity>"
```

The probe compiles a small original API caller against the installed named
Minecraft/NeoForge libraries and exact Lumiera JAR. It bootstraps the normal
Minecraft registries in a standalone JVM, with a 384 MiB maximum heap, then
parses every scene and round-trips its native NBT. It checks durations, event
counts, absolute mode, point counts, positions, angles, FOV and actual native
linear interpolation. It starts neither a game client nor a dedicated server.
Its source, compiler output, native output and result receipt remain in a unique
probe subdirectory, including failures. This validates format and serialization,
not server reload, remote delivery or graphics.

The native probe passed for all seven scenes at **2026-10-27 02:03:40 UTC**,
with compiler and JVM exit codes both zero. The unchanged staged ZIP SHA-256 is
`0f0beab26f165e26a5d608d3567a94e230226e5bdf2236e5cf06de5c274b587d`.
The local receipt is retained in
`staging/settlement-cinematic-final-20261027/native-probe-1793066566001452100/result.json`.
Earlier failed receipts remain alongside it. The probe now uses the installed
NeoForge launch dependency list and matching Minecraft resource-only archive,
excluding older installer-cache dependencies. Its success-marker reader also
accounts for Minecraft's normal `LoggedPrintStream` prefix. These probe repairs
did not change scene JSON or its archive. This is native format/serialization
evidence only; it is not a server registry reload or client viewing receipt.

## Activation requirements for the parent workflow

1. Preserve the current complete world backup and cinematic settings/history.
   Finish native placement/verification of the referenced construction, including
   ships before their scenes are offered as verified attractions.
2. Verify the staged archive and per-scene hashes and successful native probe.
   Inspect the ZIP: only the documented seven scene JSON files and `pack.mcmeta`
   should be present. No functions, tick/load tags or commands belong in it.
3. Copy the exact staged ZIP into the **official world's** `datapacks/` directory
   as `awft-settlement-cinematic.zip`. This is a world-specific data layer; the
   canonical Packwiz manifest and each client's mod selection remain unchanged.
4. A normal server data reload or clean startup loads the registry listener.
   A newly discovered datapack may need `datapack enable` followed by reload;
   inspect the native datapack list and console before assuming it is active.
   This source tool intentionally performs none of those actions.
5. Read fresh bridge cinematic telemetry. Expect `awft:settlement_intro` with
   480 ticks, absolute camera mode and two events; castle has 400 ticks and the
   remaining local tours 360. Preserve any parser failure output.
6. Select `awft:settlement_intro` through existing cinematic settings, preserving
   the current enabled/first-join preference and **all** existing first-join
   history. Do not reset that journal to force a repeat. Use normal replay for
   QA when a client is available, from the documented proximity center.

The existing client presentation helper handles Escape by calling Lumiera's
`requestSkip`; Control Room's stop/skip uses the native stop command. Check
immediate Escape and Control Room stop, natural completion, reconnect behavior,
safe player position, restored controls, UI and camera state. A server command
acceptance is not client acknowledgement. The existing first-join bridge also
marks history after command acceptance; do not describe that as confirmed
viewing or successful display.

Graphical review is currently deferred while the owner uses the laptop for
Battlefield 6. Do not launch Minecraft for this task until that constraint is
lifted. Later inspect every scene with the intended shaders and correct missed
terrain, occlusion, abrupt turns, horizon framing, hidden roofs, missing sails,
unloaded chunks and the final control handoff. Only then can these scenes be
called visually polished. The requested single prominent-castle/offshore
first-join flyover remains an explicitly open requirement under the current
native chunk-delivery limits.
