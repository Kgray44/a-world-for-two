# Fleet maritime commissioning handoff

Source checkpoint, 2026-10-28. The master owns all world placement, runtime/config
changes and the single graphical client. Read the authoritative
`docs/coordination/WORKSTREAMS.md` and `handoffs/FLEET.md` in the master checkout
immediately before integration; the construction save and configured permanent
save remain separate. No live lease or Minecraft operation was performed for this
handoff. Coordinate tests through the master and run only one heavy live test.

## Implemented source and current evidence

| Item | What exists | Remaining acceptance |
| --- | --- | --- |
| Major historic ships | Original static structure templates, belowdecks and source checks in `tools/grand_harbor_fleet.py` | Current placement, actual graphics, collision, walking and preservation of existing contents |
| Real sailing cog and rowing tender | `tools/artistic_harbor_craft.py`, fixed native `HarborCraftSupport` recipes | Fresh admission, creation if lawful, controls, boarding, shared cargo, departure/return and restart |
| Cargo derricks and boat tackle | Architectural fittings; native Create parts alone do not prove a connected drive or lifted load | Exact transmission, load/sweep admission, native movement and persistence |
| Cannon service bays | Oriented native cannon blocks and maintenance tools; guns remain unloaded/unassembled | Actual access, collision and normal empty interaction; no harbor firing test authorized |

The large block-built hulls remain architecture. Do not glue their hulls, rigging,
inventories or gangways into an Aeronautics/Sable/Create physics ship merely to
make them move. The real Small Ships cog supplies the distinct sailing gameplay
path. Additional small structural vessels do not become sailing craft by export.

## Pins and read-only audit

The existing `inspect_pins(Path(r'D:\A World for Two'))` audit passed against the
cached bytes on 2026-10-28: Small Ships **2.0.2**, Create **6.0.10**, the named
Cog/Ship/ShipPart/sail/container classes, Create pulley/contraption/collision
classes, and Minecraft **1.21.1** `EntityType`. No JAR was downloaded or executed.
This is dependency identity evidence, not runtime commissioning. Full hashes and
the reviewed source revision are in `tools/settlement_maritime_attractions.py`;
the pinned [Small Ships source](https://github.com/talhanation/smallships/tree/4bfb8680a3fecd8c7e71506b941a79c51c49dffb)
is the upstream reference.

The pinned Create `HandCrankBlock` bytecode was inspected with Java21 `javap`.
`hasShaftTowards` accepts **the opposite of `FACING`**, and `canSurvive` requires
nonempty native collision on that adjacent opposite-facing block. A crank east
of a shaft must face east; a crank west of a shaft must face west. A horizontal
X drive uses `shaft[axis=x]` and `rope_pulley[axis=x]`. Verify actual rotational
connection, support and reach in the game; state alignment is only source proof.

## Preserve the failed craft custody record

The immutable historical terminal is
`H/dashboard/settlement/harbor-craft-result-f1994113-768f-44e2-abc1-64a0f4944dc7.json`
under the construction home defined by WORKSTREAMS. Its operation was **inspect**,
candidate.41/bridge0.6.27, manifest
`734313a021ab61a08a2dab8ff662c57ea6c422f51a45081c7cc7a19c27f33448`.
It refused with `Persistent entity region custody changed; no creation performed`.
The receipt records zero created entities, zero block mutations, zero remaining
owned tickets, no cleanup errors, and no pending shared native futures. It read
179 storage chunks across three dimensions; the initial Overworld listing had
seven region files including two native zero-byte placeholders. The refused
operation provides no boarding/sailing evidence.

**Exact changed file and cause are UNKNOWN.** The terminal does not retain the
before/after `DiskStamp` difference. Ordinary asynchronous saves and files opened
by native region reads are possible causes, not confirmed explanations. Do not
remove the metadata comparison, ignore nonzero changes, add sleeps/retry loops,
delete placeholders, reset UUID reservations, clear the berth, replace inventories
or rerun an old create intent to obtain a passing result.

The focused master-owned source correction is bounded diagnostics at the failed
comparison in `HarborCraftSupport.commit`: retain each changed dimension/path,
added/removed file, before/after size, modification time and header hash, and a
fresh native-mailbox pending-key set. Preserve the existing fail-closed outcome.
Then, in one coordinated inspection window, identify whether native reads created
an empty placeholder or whether real persistent entity data changed. Any changed
nonempty region/pending population invalidates the completed census; a new
complete, bounded census and matching same-tick loaded/pending checks are required
before any separately authorized creation. Do not broaden the factory recipe.

The exact proposed patch and source-only compile/probe receipt are now in
[`proposals/fleet-craft-custody-diagnostics`](../proposals/fleet-craft-custody-diagnostics/README.md).
It reuses the existing same-tick pending-UUID mailbox result to record actual keys;
it adds no futures, waits or cleanup obligations. The active helper remains
unchanged until the master reviews and integrates the proposal.

Before proposing that window, reconcile current loaded, pending and persistent
custody for the **original** requested identities, plus all reservation/intention
files. These are historic requested UUIDs, not evidence of existing entities:

| Recipe | Original requested UUID | Original proposed position |
| --- | --- | --- |
| The Sea Glass Promise, `smallships:cog` | `62cd3578-b01b-5ab4-b7e8-6f74734cb4f4` | 1196.5,63.1,-1264.5 |
| Wren harbor tender, `minecraft:boat` | `59f253a3-00b6-576b-ae62-306aa75d8a8c` | 1194.5,63.1,-1253.5 |

The fixed helper supports these two safe native recipes, not arbitrary summon
SNBT or new entity types. A changed or occupied current berth requires a reviewed
source change and fresh admission. Historical coordinates are not placement
authority. Use the engine's typed entity load/add path only after all gates pass.

## Serialized native windows

Each window needs a master-issued operation/expiry, exact save/candidate/JAR and
current verified checkpoint, scoped targets and entity/sweep masks, resource
forecast and cleanup owner. Run ReserveGuard before writers and at five-minute
intervals; reserve 30GiB independently on C: and D:. This monitoring does not
constrain external applications or existing writers. Preserve every failed
receipt and partial state. Player arrival stops construction admission.

1. **Preimage and craft inspection, at most10minutes.** Fresh exact blocks and
   block entities for the landing, hull/body/passenger/departure water and air;
   complete native AABB census after all target chunks are FULL and entity-ready;
   loaded/pending/persistent UUID census and original-intent review. Existing
   infrastructure and all unknown occupants are preserved. Require a clean
   terminal with owned tickets/streams/leases released. Inspection creates no
   craft. Resolve the custody diagnostic before scheduling creation.
2. **One authorized creation, at most5minutes.** Bind new immutable current
   documents/checkpoint without changing requested identities. Native same-tick
   preimages, AABBs and custody must pass before the durable one-shot reservation
   and actual add. Inspect root, multipart children, hull/sail state and original
   cargo capacity after normal initialization. Any unknown/partial outcome stops
   further creation; retain the actual entity and reconcile it.
3. **Actual player craft use, at most15minutes.** Master obtains the existing
   client's exclusive slot and owner's authorized participation. Walk the apron;
   board normally; use the pinned mod's actual controls; furl/unfurl, depart north
   through the exact admitted corridor, turn only in surveyed free water and
   return. Test the ordinary tender's departure, water return ladder, boarding
   stair and transfer onto the offshore ship. Record identities, positions,
   collisions, damage and cargo. Do not teleport, forge motion or simulate users.
4. **Cargo hoist before any boat lift, at most10minutes.** First verify an actually
   connected drive at the lifting point, supported/reachable operator platform,
   independent rope path, exact small payload and full swept volume. Use normal
   native controls to lift/lower an empty cargo cradle twice. Stop if the moving
   set includes hull/rig/controls, inventories, an unintended entity or blocked
   passage. Record actual signed offset, stopped/parked state and retained load.
5. **Empty tender retention, separate at most10minutes.** Only after the empty
   cargo mechanism passes and the master selects an exact small-cradle design,
   manually row one empty vanilla tender into the admitted sweep. First lifts
   carry no player. Check the same UUID, no damage/ejection/clipping, lower and
   depart normally. Small Ships cog lifting is outside this recipe. Failed native
   boat retention leaves usable skiffs at water level and the lift as cargo-only
   or decorative; report that limitation.
6. **Unloaded cannon interaction, at most5minutes.** In each vessel, walk to both
   sides of representative breeches, inspect barrel/chamber orientation, carriage
   collision, service access and tool/storage access. Demonstrate normal empty
   interaction only where the pinned mod supports it. Static structural guns do
   not become functioning cannon from a successful click. Any empty mount/aim
   demonstration needs its own small isolated sweep and master admission. Supply
   no live powder/projectile and fire no round across the harbor.

`tools/settlement_maritime_attractions.py:tender_hoist` retains an older isolated
52-block cradle proposal, 14-block travel and an explicit tender body sweep. Its
old coordinates and baseline must **not** be applied to the current R3 hull by
assumption. Regenerate exact current geometry and before states if that design is
selected. A platform-only collision mask omits the carried boat above the deck.

## Restart, multiplayer, graphics and measured harbor load

After native creation/use, the master records original UUIDs and actual contents,
parks mechanisms, performs a normal save/stop, verifies the retained checkpoint,
then restarts the same save. Check no duplicate entity, lost cargo, detached rig,
unintended contraption, obstruction, ticket leak or broken boarding route; repeat
a short departure/return and hoist cycle. A saved archive alone is not restart
evidence. The configured permanent runtime is never overwritten for this test.

KG and Sera must actually join to qualify shared boarding, seats/control handoff,
inventory access, offshore transfer and reboarding after reconnect. Record each
participant and result separately. A sole-client/helper probe cannot stand in for
two people. Lack of the second participant remains an explicit unfinished item.

Capture genuine Minecraft bow, stern, broadside, elevated, working deck, captain,
officer/wardroom, crew/mess, galley, gun deck, hold and magazine views after normal
block updates settle. Use immutable view identifiers and source/image hashes.
Review dropped rope/items, native facing/connections, proportions, glazing,
lighting, headroom and furnishing. Source flood/walk tests and a favorable camera
angle do not certify native collision or acceptable artwork.

In a single master-scheduled performance window, record a fixed stationary harbor
view and the same short voyage before/after the full harbor is loaded. Keep pack,
heap, shader, render/simulation distance, client resolution and roster identical.
Collect a bounded five-minute baseline and five-minute full-harbor sample: real
TPS/MSPT with timestamps/sample count, loaded chunks, entity/contraption counts,
server RSS/heap/CPU, client FPS/frame-time where available, and free bytes on both
drives. Stale or unavailable fields remain unavailable. Record warm-up and source
of each metric; report observed distributions and deltas, not invented targets or
acceptance from one screenshot. No harbor performance measurements exist from
this source handoff.

## Unfinished integration work

Current native custody diagnosis/correction; master-selected exact berths and
fresh preimages; current structure placement and actual visual refinement;
successful craft creation/controls/return; connected hoist and tender retention;
unloaded cannon interactions; current two-player, restart and harbor performance
qualification; and controlled final permanent-world promotion all remain open.
The only verification performed for this document was source/receipt inspection,
the passing read-only dependency/class audit, and pinned crank bytecode review.
No runtime, graphical, multiplayer, restart or performance pass is claimed.
