# Existing station naming and genuine schedule-item preparation

Source proposal only. The master must integrate an authenticated parent request,
actual helper/JAR/version/checkpoint pins, exclusive lease, storage forecast and
immutable native journal before invoking these methods. No command/tick hook or
runtime installation is supplied. Nothing here has run against Minecraft.

## Station identity and the supported naming path

`CopperWrenStationNames.inspectForManualRename` is a bounded read-only preflight.
It checks the real server thread, private construction world/25575, zero players,
the parent's valid lease, already loaded station and target chunks, exact native
IDs/directions, both old names `Track Station`, and a shared connected graph using
at most1,024 existing graph nodes. It also examines at most128native station
objects in that graph and rejects any unrelated object already using either
destination name. Named-graph preparation applies the same uniqueness check after
renaming. It does not request a graph through world reads,
add tickets, rename, write a ledger or apply/start any train schedule.

Pinned Create6.0.10 exposes `StationBlockEntity.updateName(String) -> boolean`.
Its private `updateStationState` calls `edgePoint.determineGraphLocation()` before
mutating/syncing the station. That world walk can load chunks. Therefore this
proposal deliberately provides **no naming mutator claiming zero-load safety**.
Use the ordinary native station UI in the master's coordinated ready-route/client
window. If a parent later invokes `updateName` directly, it must explicitly admit
that native world walk; an observer read window is insufficient.

Set the station at1332,71,-994 to **Copper Wren Mill**, and the one at1332,71,-942 to
**Rosewater Orchard Halt**. Preserve the target track at1336,69 with the same Z.
The62 existing straight track cells are X1336/Y69/Z-997..-936, spanning chunkX83,
chunkZ-63..-59. The6ad native verification-only source contains54spruce and8dark-oak
Railways tracks, all `shape=zo,turn=false,waterlogged=false`; neither station is
assembling. This footprint is a source fact, not a guarantee that Create's naming
world walk only reads those chunks. Do not propagate/rebuild tracks to rename.

Read-only custody from the authenticated immutable6ad archive:

| Identity | Saved value |
| --- | --- |
| Checkpoint | `20261028T191243Z-6ad3a8`, SHA `0ba7ad2097fb52273a37da6a76d8fc030133b79cd26d81b97531d8d74c2546c2` |
| `data/create_tracks.dat` | 843bytes, SHA `6fd706b924de26bae53ab30dd4346cd3f274db47373b40227af609ba6df7e47a` |
| Graph | `72c139e5-b2ab-4883-baec-0084d0012ed2`,22nodes |
| Mill station | `cdca73e6-32ac-528e-9113-7e1a044bbee1`, direction POSITIVE |
| Orchard station | `acccdcfc-a206-5b00-8041-1eda00d27dbd`, direction NEGATIVE |
| Saved trains | 0 |

Use **fresh native** IDs/directions for the `Expected` record; saved values cannot
authorize a current action. After naming, read back both actual GlobalStation
names, unchanged IDs/target positions/directions, actual graph identity and graph
continuity. Preserve any partial naming result; do not reset a successful first
name or pretend both names were applied. No raw block-entity/NBT name edit.

## One actual blank schedule item

No blank schedule is currently proven stocked. The master must supply a genuine
registered `create:schedule` item through a separately admitted legitimate action,
without overwriting stock. This helper never creates, copies, removes or refunds
items. It changes one actual existing stack's native registered component.

`CopperWrenScheduleItem.inspectStarter(world, lease, requestSHA)` reads the real
27-slot starter at1313,68,-994 into ordered `all27_native_snbt`, with empty strings
for empty slots. The master publishes that actual readback through its journal;
do not invent SNBT from a sparse observer view or reuse an old pre-feed inventory.
Before every inventory read, the helper requires the actual existing block entity
to be exactly vanilla `ChestBlockEntity`, `Blocks.CHEST` with typeSINGLE and
`getLootTable()==null`. It obtains existing BEs from the loaded chunk's BE map;
missing/pending BEs are refused rather than created/promoted by a lookup. An
arbitrary `Container.getItem()` could unpack loot and is not accepted.

`stock.setChanged()` remains mandatory and invokes native output-signal neighbor
handling. All eight first/second cardinal positions at Y68 must already be loaded:
1312/1311 and1314/1315 along X atZ-994, and Z-995/-996 and-993/-992 atX1313.
Any vanilla comparator at those positions refuses the operation because its
neighbor callback may read farther or remove an unsupported comparator. The exact
chest, callback footprint and all27slots are rechecked immediately before changing
the item, after durable intent publication, on the same server thread. No
comparator is removed and `setChanged()` is not bypassed. Zero direct helper
tickets alone is not proof of zero implicit loads or native callback effects.

After both station names, genuine conductors, actual three-seat/two-bogey train
assembly and parked native Mill attachment are proven, call
`configureBlankInStarter(world, lease, actualTrainUUID, expectedNames, slot,
passengers, actualAll27SNBT, requestSHA, mutationCallback, parentReport)`.
`passengers` is1for an initial genuine rider or2for KG/Sera's actual test.
Supply initial creative hardware before the logistics baseline, then complete
the genuine milling before/after capture and audit before conductor installation
or schedule-component changes. Subsequent engineering changes require their own
custody record.
For the requested two-player commissioning, configure2on the first invocation.
An optional solo check should use ordinary manual driving before applying that
schedule. This per-train ledger deliberately cannot be replayed to change a
one-player configuration into a two-player configuration; a later change needs
separate review and ordinary native item custody, not a new request name.
The method:

- Revalidates exact named station/graph identities and continuity, the actual
  registered train, both conductor directions, three real seats, stationary speed,
  zero passengers and absence of a previous train runtime schedule. The Mill's
  actual `getPresentTrain()` must be that same native train object.
- Requires all27 stock slots to match, the actual selected stack count1, exact
  `AllItems.SCHEDULE` identity, an empty component patch and no prior schedule.
- Builds the existing finite Mill/Orchard/Mill schedule through the native factory,
  then sets `AllDataComponents.TRAIN_SCHEDULE` on that same stack. The registry
  identity must be exactly `create:train_schedule`.
- Reads the component back with `ScheduleItem.getSchedule`, compares native
  serialized schedule content and every unrelated slot, and confirms count1 and
  no train runtime schedule. All before/after27-slot native SNBT is retained.
- Writes one forced CREATE_NEW intent and one completion under
  `world/data/awft-copper-wren-schedule/<actual-train-UUID>/`. Any existing ledger
  refuses replay, even under a new request name. A partial keeps its actual item
  and intent; no guessed reconfiguration, refund or schedule application follows.

The parent marks possible mutation before ledger/item writes and publishes actual
completion or failure. Each durable row is capped at128KiB; at most two rows are
written. This caps the helper's ledger output, not normal Minecraft save growth;
the parent's ReserveGuard forecast must separately cover that save work.

The configured item remains in the starter. A real player retrieves it and hands
it to the genuine conductor through ordinary gameplay. The helper never calls a
runtime setSchedule method, assigns conductors or starts/moves a train. Keep the
four-cell conductor overlay separate from the retained7,941-cell resume contract.
Station naming/item preparation does not complete the wider intended railway.

For ordinary disassembly/conductor installation/reassembly, record actual burner
counts in both starter and real player inventory. The installation path must
consume two genuine filled items; creative placement alone may leave item counts
unchanged. Preserve the successful initial assembly's UUID as history, and use the
actual final reassembled train UUID for schedule preparation and restart checks.
Verify three seats, two bogeys and both native conductor directions again.

## Optional fixed creative-construction hardware

`CopperWrenConstructionStock.supplyFixedHardware` is a callable proposal only,
with no command wiring or console bypass. Parent admission must explicitly name
creative construction, authenticate the request/checkpoint/JAR/helper and fresh
native all27-slot inspection, own a valid empty-world lease, forecast storage and
journal the actual outcome. Passing a boolean to the method does not obtain that
authorization. The former one-use Native51 cable lease does not authorize stock.

It requires the same exact single vanilla/no-loot chest and comparator-free loaded
callback apron. Slots3/4/5 must all be genuinely empty. It creates only these fixed
registered hardware stacks: slot3two WEST input-detector attachments, slot4two
FILLED `create:blaze_burner` items and slot5one plain blank `create:schedule`.
The actual detector getter must return the native `RedstoneDetectorAttachment`
with id `redstone_input`; the actual registered burner item must be a
`BlazeBurnerBlockItem` whose `hasCapturedBlaze()` is true. No actor, synthetic
captured-blaze NBT, wheat, flour, iron, sheet or processing product is created.

The fixed world ledger `data/awft-copper-wren-construction-stock-r1/` permits only
one forced CREATE_NEW intent and completion, irrespective of request name/nonce.
Any existing ledger refuses restock/replay. Before each native slot change and
mandatory `setChanged()`, the helper rechecks lease, chest/apron and current all27
slot custody. It verifies exact five-item additions, actual native classes,
components/getters and all before/after27-slot SNBT; every other slot is preserved.
Any partial retains actual stock and durable intent, with no refund, overwrite or
automatic retry. The parent captures failure honestly rather than treating a
partial intent as five completed additions.

This is explicit creative-authoring inventory, separate from recipe output and
inventory-conservation evidence. Take the actual logistics baseline after this
separately proven stock operation. The manual creative-client stock path remains
the fallback if the parent does not integrate/admit this helper. No stock action
has run and no stocked blank is yet proven.

## Verification and limits

Java21.0.10 compilation passed, with no diagnostics, against the existing named
Minecraft1.21.1 dedicated-server APIs, Create6.0.10 and actual installed bridge
0.6.39 for the parent's `ArtisticEngineeringSupport.Lease` interface. Bridge compile
input SHA is `496a22cf30d517dbc2bcae2806f6412c17a0656c081d0cb8fb76d0c2c8d9c1d4`;
the Lease class SHA is `8cef2bb1db9f98bce6bbe28353624fa8a2594aeb7b5a9cce844c97b7693f2205`.
Build args, zero-diagnostic compiler output and owned classes remain only in
`.local/rail-station-item-compile-r1/` (`javac-0.6.39.args`,
`diagnostics-0.6.39.txt`, `classes-0.6.39/`). A preceding recompile failed when the
master's deployment removed the old0.6.38 JAR from that older classpath; its args
remain preserved. Refreshing the compile dependency to actual0.6.39 resolved the
six missing-Lease errors, without changing runtime files or weakening any guard.
The final compile including all three new helpers and the unchanged passenger
factory passed again with zero diagnostics. Its args, exact compiler output,
source hashes, classes and compilation record are in
`.local/rail-creative-stock-compile-r1/`. It uses a bounded690,954byte snapshot of
that first-party bridge as a compile-only Lease API dependency, avoiding a race
with the master's replacement of the installed JAR. No JAR is committed or added
to another Minecraft installation.
No Minecraft server/client was launched or controlled; no runtime action occurred.

Inspected Create JAR SHA:
`ef87fe5709f1ba1f5b8bb20a2925b5afb4669e178fd6d8bf10c167759eefe37a`.
Inspected bytecode SHA values:

| Class | SHA-256 |
| --- | --- |
| `StationBlockEntity` | `5dba7eecfc4e58e38d0e84483934e8742ef9f6ef81f58a15ed2754242bd0435f` |
| `ScheduleItem` | `bed37ae67969a2741e17a0e6680ea50ca43a86719aad173443097763e2c887a9` |
| `AllDataComponents` | `aa08d818b829cee15b9bb61b3860a1d24849eb2cedd707a144ab6a8831f5a359` |

Source/API compilation is not actual mutation, item custody, train navigation,
boarding/unloading, two-player operation, restart, visual or performance evidence.
Those native tests remain required. ReserveGuard admitted the bounded owned C:
source/compile writers with D: untouched. Monitoring does not constrain external
applications, cloud work or existing writers and is not an operating-system quota.
