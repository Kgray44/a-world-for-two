# Future native attraction admission

**Source only. The currently installed bridge 0.6.9 / candidate 23 has no `awftattractions` command.** No Java build, game launch, native command, hub installation, network setup or live admission was performed for this slice. The owner is playing on the existing server. Its source and runtime receipts remain separate.

`AttractionSupport.java` implements the first prerequisite for the Copperway hub: a console-only inspection/admission state machine. It does not implement station configuration, filter assignment, glue, train assembly, tube connections, water activation, recipe demonstrations or travel. Those commands explicitly refuse execution. A successful admission snapshot is evidence about one observation interval; it grants no later mutation authority.

## Parent integration contract

The future bridge owner wires these lifecycle methods; this change does not edit `ControlBridge`, build scripts, version pins or the active pack:

```java
var attractions = new AttractionSupport(futureCandidate, futureBridgeVersion, sharedInterlock);
attractions.commands(registerCommandsEvent);
attractions.tick(server);       // once per server tick, on the server thread
attractions.stopped();          // before server resources become unavailable
```

`Interlock.acquire(owner, temporarySimulation)` must return an exclusive owned `Lease` or refuse. `Lease.valid()` must stay true only while that same lease remains exclusive. `Lease.close()` releases exactly that lease. The parent must make **all owned** settlement placement/survey/map, atlas mutation/teleport, engineering, administrative world mutation and attraction paths honor this shared interlock. A new isolated mutex would not protect against existing writers. Independent console tools and ordinary player edits are outside that lease unless explicitly integrated; inspection does not promise an atomic world snapshot in their presence. Snapshot-only player inspection can coexist only if the parent can prove it never mutates or acquires world tickets. Do not wire an always-valid dummy lease.

Both inspection and admission require this lease. `inspect` adds no tickets and refuses any target that is not already FULL, block ticking, entity ticking and entity loaded. `admit` additionally requires zero players throughout its lifetime. It may add bounded, owned NeoForge force-simulation tickets; it never calls a block/item/entity setter or a network creator. Ordinary mod simulation can initialize or change native state while those tickets exist. Zero explicit network-creation calls must not be described as zero autonomous native network changes.

The source must first compile and pass targeted native tests under Java 21 in a future candidate. The declaration checks below are not compilation evidence.

## Exact private evidence envelope

`python -B -m tools.attraction_admission` authors a fresh `dashboard/settlement/attraction-admission-<sha16>/` containing `admission.json` and the exact frozen authoring/native source copies. It never installs, starts Java, reads region files, writes a generic `plan.json` or manufactures missing build/placement receipts. Its maximum additional private output is 2 MiB, guarded through `Storage.reserve` before creating the new directory. Existing bundles are preserved.

Required arguments are `--home`, `--hub-manifest`, `--build-receipt`, `--before-receipt` and `--after-receipt`. The two native verification paths must be actual immutable `NativeJournal` terminal receipts with their adjacent `.complete` SHA markers. They must have the exact successful SettlementSupport verification status, exact plan SHA/count, zero failures, no error, ordered execution intervals, and before completion no later than after start. A cancelled receipt with zero failures fails this gate.

The future build receipt must be created by the bridge build owner from the actual built and installed artifact, with this schema:

```json
{
  "format": "awft-attraction-native-build:1",
  "candidate_version": "<future exact candidate>",
  "bridge_version": "<future exact bridge version>",
  "pack_sha256": "<actual active pack SHA-256>",
  "native_source_sha256": "<AttractionSupport.java SHA-256>",
  "bridge_jar_file": "server/mods/<actual installed bridge filename>",
  "bridge_jar_sha256": "<actual JAR SHA-256>",
  "attraction_class_sha256": "<worldfortwo/bridge/AttractionSupport.class SHA-256>"
}
```

The authoring helper verifies the installed JAR and class-entry bytes. Native admission checks its own loaded class resource, the running bridge mod version, the constructor's exact future candidate/version, current active/installed pack receipts, native world seed/path, current verified backup receipt/archive and source-copy identities. Canonical current receipts cannot be replaced with archived copies. Owned paths reject escape, linked/redirected paths and declared size drift. No account or tunnel information is needed.

Every target must have exact original prior-state custody in both the complete precondition plan and the manifest audit. All ten completed geometry masters plus five detail deltas remain immutable exclusions, **including authored air**. The helper and native streaming custody scan both reject intersections. Actual installed Create, Overpressure, Hypertube and Steam 'n' Rails JARs must match the hub's four pinned dependency identities.

If the current backup changes, this envelope refuses the old binding. Before installation, prepare the uninstalled hub against the new saved preimage. After installation, preserve its original custody proof and obtain a separately reviewed nonmutating rebind; do not rerun placement or reinterpret installed hub blocks as natural terrain.

## Native observation and limits

The command syntax, available only after future integration, is:

```text
awftattractions inspect attraction-admission-<sha16> <full-envelope-sha256>
awftattractions admit attraction-admission-<sha16> <full-envelope-sha256>
awftattractions status
awftattractions cancel
```

Only an entity-free permission-level-4 command source is accepted. `setup`, `assemble`, `connect`, `commission` and `run` refuse without performing attraction work.

The reviewed hub reserve is x1292–1320, z−1030–−904. Source limits are 45,000 target positions, 32 target chunks, 64 declared block entities, 3,600 ticks overall and 400 ticks waiting for target readiness. The actual frozen dry hub has 16,843 targets and 14 BE tags. Its static assembly/connection features remain uncommissioned.

Input reads are bounded by declared bytes. The authoring resolver scans at most 4,096 immediate evidence-directory children, at most 32 basename candidates per geometry source and 128 MiB total geometry-candidate bytes. Native input hashing uses 64 KiB chunks; fixed-geometry custody uses a streaming JSON reader with a fresh byte digest through EOF. Tick work checks a 4 ms scheduling budget and a 512-step bound. Individual native getter, file read, JSON parse, final bounded observation or journal call is not preemptible. `bounded_binding_read_ms` and observed `max_work_ms` report actual work; these constants are not measured performance guarantees. Future native timing remains required.

All target chunks must stay FULL and genuinely block/entity ticking with entity data loaded. The tool compares block identity and **every explicitly authored property**, including mutable flags that the existing placement verifier does not cover. Differences remain differences; the inspector does not rewrite them. Final current receipt hashes are rechecked before the observation.

Native observations use public getters, native item capabilities and saved metadata. They record actual component state/readiness, speed/theoretical speed, network presence, overstress, pending speed update, station target/direction/valid-track state, extractor filter and connection-list size. Admission requires the actual main clutch and stop lever to be powered; millstone, press, pump and both entrances must genuinely report stopped speed, no overstress and no pending speed update. Active grain/millstone/depot/dispatch/hopper inventories must be empty. Every pneumatic route block must report no moving cargo. Starter supplies are inspected but intentionally not required to be empty.

The installed pinned JAR class declarations were inspected without running Java. The relevant getters are `KineticBlockEntity.getSpeed()`, `getTheoreticalSpeed()`, `hasNetwork()`, `isOverStressed()`, `needsSpeedUpdate()`; `TrackTargetingBehaviour.hasValidTrack()`, `getGlobalPosition()`, `getTargetDirection()`; `PneumaticConnectionBlockEntity.getFilter()`; inherited `PneumaticTubeBlockEntity.getMovingItem()`; and `ITubeConnectionEntity.getConnections()`, whose native return type is `List<IConnection>`. The native station `edgePoint` field is used to obtain its real targeting behavior. No `getOrCreateNetwork`, speed setter or invented serialized motion is used.

On timeout, player join, lost lease, mismatch, cancel or server stop, the tool closes owned readers and removes only its identical temporary tickets. Tickets are tracked before addition, so partial addition failure still has a cleanup handle. Native chunk futures are shared engine work; they are reported, never cancelled as owned workers. Failed cleanup retains its handles and lease in `CLEANUP_REQUIRED`; `cancel` or server stop retries. A failed admission does not delete its evidence or silently retry into success. Terminal `NativeJournal` receipts and completion markers are immutable; the status file is only a progress view.

## Next native slices

1. **Stopped setup:** revalidate current custody/geometry, real readiness, empty active and in-flight inventories, and same-tick spatial entity occupancy under a fresh empty-server lease. Validate expected target BEs and pinned config before each API call. Assign the real filter with `setFilter`, validate/name stations through actual `edgePoint` and `updateName`; preserve each previous value and record every native result. Initialization must use normal mod lifecycle APIs, with no fabricated power or graph.
2. **Tube setup:** compute native offsets and the two reciprocal 30-block Bezier connections before either setter. Require native validation/collision acceptance, fresh endpoint/route occupancy, ready chunks and exact preverified air inside the reviewed TubeFiller write envelope. Journal the intended pair and prior native connection states first. Use the actual setters, verify reciprocal data and generated collision cells, and retain partial native state on failure for explicit recovery. A lone visual tube row is not a network.
3. **Carriage assembly:** fresh entity/BE occupancy and fixed-boundary checks for only x1315–1317,Y70–75,z−1005–−997. Validate the actual station graph, bogey offsets and assembly direction; create only bounded owned native glue, call the actual station assembly API and record the resulting real train UUID. Never include track/platform/shaft/tube/station blocks or claim train motion from static placement.
4. **Commissioning:** separately verify/activate the three hydraulic cells, measure real RPM/stress/STOP–RUN, run and account for real wheat/flour and iron-sheet recipes, test both train directions and tube travel, then save/restart and recheck persistence, idle chunks and player routes. Spatial occupancy must be revalidated at each potentially moving/writing step; this read-only snapshot cannot replace that admission.

## Verification tier

The 13 new Python tests exercise bounded immutable authoring, before/after chronology, rejection of cancellation, missing/fake/stale inputs, source/class drift, fixed authored-air exclusions, duplicate/invalid targets, forbidden commands, and guarded unique output using synthetic fixtures. All 41 focused admission/hub/maritime tests pass. Packwiz validation passes with 207 mods and `node --check control_room/static/app.js` passes. These checks never simulate native speed, entities, graphs or player travel. Native compilation, interlock integration, cleanup fault tests, live inspection/admission, performance, commissioning and player acceptance remain pending. Storage guard coverage applies to these owned writers, not external games or other existing writers on this host.
