# Copperway Watermill and Garden Railway

**Status: source and private staging only.** The live world has not been changed by this tool. Native installation, commissioning, save/restart checks and client acceptance remain outstanding. A block-identity verification cannot establish that a machine runs, a tube carries a player, or a carriage is an assembled train.

The original settlement's `phase='complete'` engineering/station templates were not part of the placed core. Rerunning that entire phase over the completed world would overwrite later work. This module instead authors one complementary hub on the east side of Rosewater Castle. Maritime attractions have a separate owner and do not share this footprint.

## Place and preservation

The reserved authoring bounds are **x1292–1320, z−1030–−904**, with all authored cells between Y64 and Y85. Actual placement bounds and counts are emitted in the immutable manifest. The public entrance is near **1305,69,−989**. The west spur meets the natural exterior of the castle grounds; it does not breach the castle wall or claim an already verified interior connection.

The hub has a glazed timber watermill, teal stepped roof and chimney, open flour dispatch arcade, independent walking bypass, underground drive service vault, passenger platforms, three-seat observation carriage, and a small garden-view shelter with a glazed rooflight and seating. Clear operating/boarding routes are checked after the full geometry is assembled. This is original authored geometry, with native installed blocks.

All ten exact completed core/port/bridge/castle/south/ship/access plans and all five completed architectural detail plans are fixed exclusions, including their authored air. Historical and saved block entities, documented paths, mechanisms, doors and inventory buffers remain protected. The generator refuses other saved construction rather than clearing around it.

The current staging baseline is verified stopped backup **20261027T034106Z-ecd64f**. Its archive identity, content-manifest hashes, saved world seed match and Minecraft 1.21.1 `DataVersion=3955` are checked. Only the immutable ZIP is opened. Nothing is extracted and no live region is read or edited. Bounded Anvil/NBT parsing recovers exact prior states from fully generated saved chunks; unknown or missing chunks fail admission. The manifest records every changed coordinate, previous state and replacement. Natural plants, shallow fluid/terrain and ores within the finite foundation/service excavation are counted explicitly.

The player may build after that backup. **A new zero-player native before-state verification is required before any installation.** Any difference aborts the affected installation; the old air plan must never be used to clear a difference. If the current verified backup receipt changes, rerun preparation so admission uses the new receipt and its actual saved preimage. Preserve the previous bundle.

## Complementary systems

| System | Actual planned components | Required demonstration |
| --- | --- | --- |
| Watermill | Three coaxial small waterwheels; sealed shaft outlet; stopped clutch; driven millstone and press | Actual flow, RPM, stress/capacity, stop/run and recipes |
| Flour dispatch | Native extractor, flour filter, cog-driven directional pump, elbow route and inserting connector | Wheat becomes flour; flour crosses a chunk boundary and reaches the dispatch chest |
| Player tube | Two ≥16 RPM entrances, one midpoint anchor, two native 30-block Bezier spans | Native reciprocal connections, collision cells, entrance mode, round trips and four chunk-boundary crossings |
| Passenger shuttle | 103 native Steam 'n' Rails spruce track blocks; two Create stations 82 blocks apart; two-bogey three-seat carriage with opposed controls | Valid track graph, station targets/names, exact carriage glue/assembly and bidirectional driving |

The wheat line supplies the dispatch arcade. The press is a distinct on-demand iron-sheet workstation. The tube provides direct player travel; the railway is a manually driven scenic passenger route to a usable garden-view stop. No continuous train schedule, new chunk loader, creative motor, virtual power field, hostile entity or explosion is added.

### Watermill and pneumatic route

The wheel centers are **1293/1294/1295,71,−1002**. A full andesite casing carries the shaft through the glass hydraulic wall. The main line runs along X at Y71; the clutch is **1297,71,−1002**, controlled by the adjacent real lever at **1297,72,−1001**. **Lever on means stopped.** The initial install is dry and stopped; waterfall sources are a separate three-position commissioning plan.

The millstone at **1302,72,−1002** receives rotation from the X/Y gearbox directly below, whose native `axis=z` exposes those two axes. Native Chutes and an empty downward hopper feed it from the empty grain chest. A stair and gallery provide reach to that input. The press at **1307,71,−1002** has its depot two blocks below. A separate starter chest holds 16 wheat, 16 iron ingots and a wrench; active inputs/output start empty.

The extractor at **1301,72,−1002** faces west in `mode=extract`, so its attached inventory is the millstone to its east. Its native filter is `create:wheat_flour`. The pump at **1300,72,−1002** is an `ICogWheel` with axis X and meshes with the actual cogwheel below; a shaft aimed into the pump's tube face would not be a substitute. The inserting connector at **1295,72,−1019** faces north toward the empty dispatch chest at **1295,72,−1020**. The real route crosses z−1008 between chunks. The actual config currently has `packagersOnly=false`; this is a required preparation gate for direct millstone/chest use.

The pinned mod reads a lowercase `filter` ItemStack fallback in `PneumaticConnectionBlockEntity.read`; the plan uses that real native field. Commissioning must still read back `getFilter()` and verify transfers. Native inventory verification does not check that filter.

The pinned Create recipes are `data/create/recipe/milling/wheat.json` and `data/create/recipe/pressing/iron_ingot.json`: wheat guarantees flour and can additionally produce flour/seeds; an iron ingot presses into an iron sheet. Seeds intentionally remain outside the flour-only route and can be removed while stopped. Do not present the random flour yield as a fixed count.

### Hypertube: actual power and native connections

This exact Hypertube version requires **at least 16 RPM** at an entrance. Its `power` block property is not a replacement for kinetic power. The hub has a real 2:1 large-to-small cog pair at **1311,66,−1001 → 1312,67,−1001**, a buried Z drive, and cog meshes into both entrance blocks. Power comes through the main stopped clutch. Runtime RPM and capacity must be measured; geometric ratios alone do not prove an active network.

Entrances are **1311,69,−995** facing north and **1311,69,−935** facing south. A native tube anchor at **1311,69,−965** divides the route into two 30-block spans. The pinned `BezierConnection.MAX_DISTANCE` is **40**, so one 60-block connection would be invalid. The 60-block separation traverses four chunk boundaries.

The dry geometry reserves air for the curves. A row of individual visual tube blocks does not establish a travel network and is not installed here. Actual connections must be created through the pinned native APIs. The connection contract in `systems.hypertube.native_links` names each source/destination and its connectable face.

For each link, use native offsets from both `ITubeConnectionEntity` instances. The native `TubePlacement.handleHypertubeClicked` pattern is:

```java
var from = new SimpleConnection(fromPos, fromFace,
    fromBE.getConnectionOffsetOnDirection(fromFace));
var to = new SimpleConnection(toPos, toFace.getOpposite(),
    -toBE.getConnectionOffsetOnDirection(toFace));
var connection = new BezierConnection(from, to);
// Check native connection.getValidation().valid(), native collision validation,
// all chunks ready, both endpoints available and the exact write envelope first.
fromBE.setConnection(connection, fromFace);
toBE.setConnection(connection.getFromPos(), toFace);
```

This is an API contract, not an executable command or a claim that setup ran. Before either setter, compute `TubeCollision.occupiedVolume(connection.getBezierPoints(level, fromPos))`. Every new writable collision cell must be exact preverified air inside **x1310–1312,Y69–70,z−994–−936**, excluding the midpoint anchor and all nonair targets. Abort if native geometry exceeds that envelope. `TubeUtils.checkBlockCollision` must also accept both curves. `setConnection` invokes the native `TubeFiller` when `tubeCollision=true`; let the mod create its own collision path blocks, then inspect and preserve the resulting native connection data. Do not invent serialized curve points or disable collision to make a failing setup pass.

**`LOCKED` means manual/sneak-to-enter mode in this version.** Its adjacent mode lever is not an emergency stop: sneaking can still enter. The signs say so. The main clutch is the actual drive stop and must not be toggled as a substitute for testing an occupied-route shutdown. The service hatch is **1313,70,−1003**; stop the drive before opening it.

### Railway

The track is level at X1316,Y69, from z−1012 to z−910. Stations target **1316,69,−1006** and **1316,69,−924**. Their physical blocks are at X1312,Y71, with actual relative `TargetTrack:[I;4,-2,0]` and opposed `TargetDirection` booleans. The pinned `TrackTargetingBehaviour` and Minecraft `NbtUtils.writeBlockPos` confirm that the target is a relative int array. A Create station has **no facing property**.

The carriage has two native small bogeys at **1316,70,−1004** and **1316,70,−998**, both `axis=z`, plus opposed Create controls, three native seats, roof and a walk-on stair at its platform edge. Only **x1315–1317,Y70–75,z−1005–−997** may be glued. Do not capture track, platforms, buried shaft, stations, tube or other world blocks.

Block placement does not assemble a train. Use normal Create station assembly or the exact pinned public APIs: `tryEnterAssemblyMode()`, `refreshAssemblyInfo()`, `isValidBogeyOffset(int)`, `getAssemblyDirection()`, `assemble(UUID)` and `exitAssemblyMode()`. Read the actual result/exception and native train UUID. Set the two names using native `updateName(String)` only after each `edgePoint` resolves its real target and valid graph. No invented `/train` assembly command is supplied. The operations chest contains a wrench, Super Glue and a schedule item; an automatic schedule is not activated.

## Preparation and commissioning

Run source checks without creating Python caches:

```powershell
python -B -m unittest tests.test_settlement_attractions -v
python -B -m tools.settlement_attractions --home 'D:\A World for Two' --dry-run
python -B -m tools.settlement_attractions --home 'D:\A World for Two'
```

Preparation writes a fresh **private** `dashboard/settlement/attractions-<identity>/` bundle only, including geometry, complete before-state companion, three-cell dry-source verification, water activation and provenance/commissioning manifest. It never changes the generic `plan.json`, receipts, active candidate, Packwiz, open world or server. Every source file/JAR/config and previous construction plan has a recorded digest; prior staging directories are never overwritten.

Maximum disk allocation is bounded at 16 MiB on C: for source/tests and 32 MiB on D: for the complete private bundle, guarded separately before writers. Actual output is checked against that cap. The reserve is a monitoring instruction, not a quota over the owner's game or unrelated processes.

The live-world owner must perform the following after players disconnect:

1. Verify every before-state position with the exact companion SHA against the current world/backup. Zero failures are required. Install the dry plan, then verify block identities/orientation and starter inventories; inspect the public routes, gallery, water housing and service access.
2. Read the actual extractor filter and connector inventories. Read station target positions/directions and graph validity. Apply ordinary native neighbor/kinetic initialization where needed; deriving runtime flags is a separate step from matching a static palette.
3. Assemble the exact glued carriage, verify two bogeys and real station names/targets, and commission both native bounded tube connections. Keep the drive stopped and active inputs empty during those checks.
4. Verify the three dry source cells, activate the contained sources and check for leaks. Record real RPM, network stress/capacity and STOP/RUN transitions. Both tube entrances must have absolute speed at least 16 RPM.
5. Run 16 wheat through the grain input; record consumed wheat, resulting flour/seeds and the real dispatch chest delta. Press an ingot into a real iron sheet. Check pneumatic routing across its chunk boundary, halt/resume and item accounting.
6. Drive the train to both stations and back using each control end; test boarding, all seats, stopping before buffers and any platform/curve collision. Run actual tube travel in both directions, manual-entry mode, four chunk boundaries, graceful disconnection and safe exit. Any multiplayer/passive-entity case not exercised stays pending.
7. Save/restart and verify inventory conservation, station/graph/train persistence, tube connection/collision persistence and continued processing. Measure new loaded chunks and idle behavior without forcing extra chunks. Refresh the map. Shader/interior/camera and owner acceptance remain separate proof.

Current native settlement `samePlacement` checks identities and selected orientation properties. It does **not** prove pump flow, filter contents, all redstone/tube flags, kinetic readiness, station targeting, train assembly or player travel. Preserve that distinction in receipts and published documentation.

## Pinned API evidence

Read-only `javap`/JAR recipe inspection used the actual installed files; preparation refuses a different digest rather than silently reusing these conclusions:

| Installed file | SHA-256 |
| --- | --- |
| `create-1.21.1-6.0.10.jar` | `ef87fe5709f1ba1f5b8bb20a2925b5afb4669e178fd6d8bf10c167759eefe37a` |
| `overpressure-0.1.7.4.jar` | `9c03c26bc50c637dbe1d8b9e19e9c10218687c61d335b36588f11e54805c4cf7` |
| `create_hypertube-0.6.0-NEOFORGE.jar` | `7bdb8979c7ff7d3b29f7a23771b6ae4870a6dcb7ce2e4a3214fdd6059aacace8` |
| `railways-0.2.1+neoforge-mc1.21.1.jar` | `b7636c8b1b0352ed1a130dfe67f8bb574e2fc08803ed1cda4d3ea00505193914` |

Relevant native classes include `GearboxBlock`, `MillstoneBlock`, `StationBlockEntity`, `TrackTargetingBehaviour`, `AbstractBogeyBlock`, `PneumaticConnectionBlockEntity`, `ItemPumpBlock`, `HyperEntranceBlockEntity`, `TubePlacement`, `SimpleConnection`, `BezierConnection`, `ITubeConnectionEntity`, `TubeCollision` and `TubeFiller`. Their existence and method semantics support this candidate design; they are not runtime attraction receipts.
