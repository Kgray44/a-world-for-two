# Keel Store: a contained continuously powered working mill

## Current physical blocker — 2026-10-30

Root placed the33 dry targets. **Do not replay them or replace the barrel,
hopper, mill or their actual inventories.** The authenticated normal-stop
checkpoint `20261030T111759Z-2ed349`, SHA256
`655cfcbedc8f2be40a5289cce74785ad0d1df25317f98c46d445c5aef21fbb20`,
contains the real hopper `(1325,66,-1203)` as
`minecraft:hopper[enabled=true,facing=down]`, despite the FEED lever
`(1325,67,-1202)` being powered. The clutch and DRIVE lever are powered/STOP;
the proposed water-source cell remains AIR. The hopper disagrees with the
intended locked state. **Water activation and wheat feeding remain held.**
This supersedes the historical source-only status and intended dry AFTER below.

Root's smallest supported recovery attempt needs no construction or new helper:

1. Inspect current source AIR, actual DRIVE STOP and genuinely empty input
   barrel/hopper/mill. If goods are present, preserve/count the real partial
   instead of treating this as an empty-machine test. Keep water absent.
2. Through ordinary player interaction, toggle FEED STOP **OFF**, inspect the
   actual hopper, then toggle it **ON** and inspect again. Require ordinary
   unlocked `enabled=true` when OFF and locked `enabled=false` when ON.
   Wait for the actual native update result; elapsed time alone is not a pass.
3. If ON still leaves the hopper enabled, retain that failed check and keep the
   wet phase held. A separate small wiring correction then needs actual support,
   walking-space and inventory preservation checks. Do not write `enabled=false`
   directly, loosen AFTER, remove the barrel or replay dry construction.
4. Only a successful native OFF/ON check admits subsequent fresh seal/water
   commissioning. Other seven shops do not depend on this Keel recovery.

Pinned Minecraft1.21.1 `HopperBlock.checkPoweredState` sets enabled to the inverse
of `Level.hasNeighborSignal` during `neighborChanged`; `LeverBlock.pull` invokes
neighbor updates at both the lever and its attached block. Ordinary interaction
therefore tests the existing circuit before assuming it needs different hardware.
This is a source-supported recovery path, **not a successful runtime test**.
The exact class SHA256s from the retained server SRG artifact are
`ba8d1df706b655b1a22a725fd1904f7d41f818526c5e6f1c69b55efc33d30f45`
for HopperBlock and
`40057bfb243f9e80c808b4f09874f2876c2a9bcce65e846d102864f759cfde1f`
for LeverBlock. Neither saved state nor bytecode inspection proves current RPM,
feed locking, fluid containment, item yield, STOP performance or restart reuse.

## Historical construction source

This is a direct source packet for the existing Native construction pipeline,
with no Java, runtime, configuration, Packwiz, client or observation changes.
It complements the first three interactive shop processes. It is not deployed
or gameplay-verified. Root is the sole world writer and must admit each phase.

The installation fits the already-built Keel Store & Galley, retaining its
doors, stairs, furniture, contents, upper home and recorded walking routes.
It adds33 dry target states:31 actual AIR cells and exactly two upper mangrove
slabs that gain their missing bottom half. The original upper halves remain;
unchanged half-slabs cannot be counted as full water barriers. Water is a
separate one-cell source activation after actual dry-machine/seal verification.

| Component | Exact coordinates / orientation |
| --- | --- |
| Small waterwheel | `(1329,66,-1203)`, facing west, axisX |
| Single initial water source | `(1329,67,-1204)`, after dry admission |
| Complete potential wet/rotating plane | X1329, Y65..67, Z-1204..-1202 |
| Glass side walls | X1328 and1330, Y65..67, Z-1204..-1202 |
| North/south end walls | X1329, Y65..67, Z-1205 and-1201 |
| Exact existing upper slabs completed | `(1329,67,-1205)` and `(1329,67,-1201)` |
| Retained basin floor/ceiling | X1329, Y64 and68, Z-1204..-1202 |
| Full casing/shaft port | `(1328,66,-1203)`, gearbox axisY |
| Drive clutch | `(1327,66,-1203)`, axisX, initially powered/STOP |
| Direct drive wall lever | `(1327,66,-1202)`, south-facing, initially ON/STOP |
| Downward turn | `(1326,66,-1203)`, gearbox axisZ, X/Y shafts |
| Small side cog | `(1326,65,-1203)`, axisY |
| Millstone | `(1325,65,-1203)` |
| Input hopper | `(1325,66,-1203)`, downward, initially disabled/locked |
| New raw-wheat barrel | `(1325,67,-1203)`, west-facing, empty native default |
| Feed-stop lever | `(1325,67,-1202)`, south-facing on barrel, initially ON |
| Service feet | `(1326,65,-1202)` and `(1325,65,-1201)` |

The glass enclosure shows a real water drop and turning wheel beside the galley
mill. The actual gearbox seals the shaft port. Native fluid flow, RPM, stress,
redstone conduction, inventory capabilities, lighting/models and leak absence
still require native tests. No flow score, speed, stress, product or inventory
is invented in the source packet.

## Native commissioning order

1. Freshly verify `dry-before-VERIFY-ONLY.json` and
   `retained-seal-and-footing-VERIFY-ONLY.json`. Source is d72c27, SHA256
   `3a740e019db364cf25693c62984281a58d2615152d7050441ecffad2dd207033`.
   The canonical Native backup is separately recorded. Current cleanup/player
   changes require actual before checks, never an automatic current-state rebind.
2. Place `dry-hardware-PROPOSAL.json` once; reconcile neighbors with
   `dry-normal-joins-SETTLE-ONLY.json`; strictly verify
   `dry-complete-after-VERIFY-ONLY.json`. The actual clutch must be powered/STOP;
   the hopper must be disabled by the real powered barrel/lever. If either
   derived state disagrees, hold before feed or water. Do not force internal
   fields or weaken the supplied native state expectation.
3. Verify `water-before-after-dry-VERIFY-ONLY.json` against the completed dry
   machine. It is a future condition until this actual check passes. Place one
   legitimate bucket source at the water point. The one-cell
   `one-water-source-PROPOSAL.json` is also available for Root's existing admitted
   native placement path. Do not replay33 dry cells to add water or fix refusal.
4. Observe real fluid settling inside the nine-cell plane. Verify
   `post-water-stopped-static-VERIFY-ONLY.json`: actual source, wheel, seal,
   stopped controls and unchanged external neighbors/walks. Interior flowing
   levels are not predicted. Inspect outside all six faces for escaped water.
   On a leak/refusal preserve the result and stop admission; use ordinary scoped
   bucket recovery. No automatic retry or invented successful AFTER receipt.
5. Observe the actual wheel rotate while the drive is stopped. Toggle DRIVE
   STOP off; observe gearbox/cog/mill movement and record native speed/stress/
   capacity. The pinned wheel predicts8RPM only if actual flow score is nonzero;
   source does not establish it. Keep FEED STOP on initially.
6. Count one actual wheat into the input barrel. Turn FEED STOP off. Require
   actual hopper transfer, wheat consumption and flour output. Retrieve real
   mill contents through ordinary empty-hand interaction. Account for barrel,
   hopper, mill, actor and item entities; empty input alone is not yield evidence.
7. Run16 wheat. The packaged recipe yields16..48 flour with even excess over16
   and0..16 seeds; record observed counts and elapsed time. This bounded batch
   fits the output products without assuming an unlimited sink. Input feeding
   is automatic through a real hopper; output collection/storage are manual,
   not pneumatic automation.
8. Turn FEED STOP and DRIVE STOP on. Verify actual disabled hopper, stopped
   downstream mill, exhausted input and no uncollected drops. The wheel keeps
   turning while its chunk is naturally loaded; no forced chunks are added.
   Native BE/fluid overhead is real and must be measured, not called zero cost.
9. In Root's restart window, save normally, restart, check source/seal/counts,
   then process another wheat. Record current TPS/MSPT/CPU/RAM and actual player
   use. No multiplayer/restart/owner acceptance is inferred from source custody.

## Preserved refusals and primary source evidence

An earlier location at wheel1330,66,-1207 correctly refused: d72 contains a
barrel at1331,65,-1207, a jam display above and later book/shelf details that
older composed source listed as AIR. Nothing was cleared. Two adjacent variants
also intersected furnishings. The final fixed location avoids those objects
and all saved BEs. An assumption that the floor was plain spruce also refused;
the actual retained floor is Chipped cross-laced spruce.

Installed Chipped4.0.2, SHA256
`18ac6fd6b30db4922ccc6ee8bea5b113f69587505b7529834f37ace506427291`,
registers that material through the vanilla full-Block creator, copying vanilla
spruce properties. The exact pinned registry class is
`418a0dda53f8d871e6587caabbb2b204db19fef7aa8ad4f1c85b6d29051bd659`.
All six original floor/ceiling identities must remain unchanged. This supports
the proposed seal; it is not a successful native leak test. Neither refusal
issued a Native command or emitted a placement result. They remain failures.

Run `python -B -m tools.transport_create_continuous` with the explicit `--home`,
`--checkpoint-id`, `--checkpoint-sha` and `--create-jar` arguments from the
[first shop producer](TORTUGA-CREATE-SHOPS.md). Output is bounded to2MiB in a new
private `H/staging/transport-create-continuous-*` folder. No plan contains a
command or BE NBT payload. New machines/barrel use genuine defaults. Source is
disjoint from the first29 shop cells and owner-completed tubes/zipline. Two
precise slab additions are not general authority to replace room blocks/items.

## Retained Copper Wren continuous power: actual saved facts

Read-only d72 inspection found stale old control metadata. At1310,70,-1000 is a
gearbox, saved speed8, source1309,70,-1000, capacity256/stress0. The old stop
point1310,70,-999 is stone bricks. The actual south clutch is1311,70,-1000,
with lever1311,70,-999. The north clutch is1311,70,-1001, with lever1311,70,-1002.
Both pairs are saved powered/STOP. Preserve the owner-completed northern tube
branch. The millstone1315,71,-1000 and press1320,70,-1000 are saved speed0.

Empty grain chest:1315,74,-1000. Depot:1320,68,-1000. Flour dispatch:1311,68,-1008.
Starter chest1313,68,-994 retains16 wheat, four iron ingots and one Create Wrench.
Saved upstream rotation proves a retained powered partial; it proves no current
native speed, processing/routing or acceptance. The shortest recovery is fresh
inspection of these actual controls/counts, ordinary south-branch operation and
real goods tests. Never invoke an old helper that treats1310,70,-1000 as clutch.
