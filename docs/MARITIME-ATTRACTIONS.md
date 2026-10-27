# Maritime attractions: staged design and native commissioning

This addition is source and private staging work. It has not placed a vessel,
changed the permanent world, assembled a contraption, moved a player, or proved
that a boat remains on the lift. The parent owns native admission and testing.
The four large historic ships remain furnished architecture; this addition never
assembles them into physics ships.

## A sailing vessel beside the quay

**The Sea Glass Promise** is proposed as an actual `smallships:cog` entity at
**1196.5, 63.1, -1264.5**, with its bow initially north. Its landing joins the
existing quay at **1191, 65, -1249**. A three-wide floating timber finger pier,
descending stair, two-wide clear walkway and boarding apron connect the craft to
the port. The dock uses timber pontoons; no inferred seabed excavation or new
world generation is requested.

The cog has spruce wood, furled white sails, intact canvas, no hull damage, an
empty original-size container and no loaded cannons. It remains unlocked for KG
and Sera. The plan does not forge account ownership, disable normal physics, make
the craft invulnerable, or place a ship item as a substitute for a ship entity.
Its UUID is stable; reapplying a summon after a player has moved or unloaded the
craft must not create a duplicate or reset player property.

The proposed dock keeps the berth separate from the known historic hulls and
finger piers; current service-boat and other entity occupancy still requires a
fresh native spatial scan. Coarse marine soundings are used only to refuse
obvious shallows. Every new block, water cell, multipart ship envelope and walking
clearance needs a current native before-state check. A seagrass block or a new
player build must cause that check to fail; this tool does not clear it away.
Depart north slowly past the landing before turning. A coarse sounding and a
block-volume check do not prove the entire ocean route navigable. The first eight
blocks of straight departure and its conservative lower water column are included
in the new before-state probe; the rest of the sailing route remains unproved.

## Flagship tender lift

The existing flagship hand crank at **1153, 77, -1440** drives the two X-axis
shafts and Create rope pulley at **1156, 77, -1440**. The current cradle is
25 double slabs and ten fence blocks. Its original floor is Y75, one empty cell
below the pulley. The inspected native pulley extends its rope through that gap
and can pick up a glued structure below; a fabricated Speed tag is unnecessary.

The proposal adds **17 plain non-inventory blocks** to the east side: ten double
slabs and seven fences. The resulting **52-block cradle** leaves room for a
vanilla tender beside the central rope. Its exact moving set is supplied in the
commissioning contract. The historic hull, operator walkway, shafts, pulley and
rigging remain outside that set. No new motor or perpetual chunk loader is added.

| State | Cradle floor | Tender center candidate | Purpose |
| --- | --- | --- | --- |
| Original stationary design | Y75 | No boat required | Preserve and inspect the completed structure |
| Water pickup | Y62 | 1158.5, 63.05, -1439.5 | Float an empty vanilla tender into the east half |
| Native fully retracted stop | Y76 | 1158.5, 77.05, -1439.5 | Meet the existing Y76 operator walkway |

The lower limit is a **pulley offset of 14**. Lowering farther toward the ocean
floor is outside this plan. The proposed 52-block cradle sweep contains 542
distinct cells. A separate **153-cell empty-tender body sweep** expands the
combined block/BE check to **560 cells**. This includes the previously unchecked
raised body at Y77 and Y78, such as **1158,77,-1440**. Geometry checks reject a
static obstruction or protected block entity anywhere in the union.

Read-only inspection of the pinned Minecraft `EntityType.BOAT` registration gives
native dimensions **1.375 wide by 0.5625 high**. The design uses a larger
two-block-wide envelope with vertical margin: **x1157.5–1159.5,
y62.80–78.30,z−1440.5–−1438.5** for the complete lift. The actual selected native
boat AABB must fit inside that verified envelope, be an ordinary empty oak/spruce
boat and carry no passenger during the first lift. This arithmetic does not
prove actual Create assembly, collision shapes, entity retention or safe riding.

Commission first with an empty cradle and no players in the work area. Confirm
the actual captured native block set is exactly the declared 52 blocks. Stop and
recover if it includes a hull block, rigging, inventory or walkway. Use the real
hand crank and inspect signed pulley movement and offset; do not substitute
teleports, animation or NBT-written rotational speeds.

After the unloaded round trip passes, manually sail one existing empty vanilla
oak/spruce tender into the marked east half at water level. Test a slow lift with
no rider, checking the same boat UUID, displacement, clipping, damage and return
to water. Repeat, then check both raised and unloaded states across a controlled
server restart. Test upper-walkway boarding only after retention and persistence
pass. The lift does not carry the much larger Small Ships cog. If native boat
retention fails, keep the tender at water level and the lift visibly labelled as
uncommissioned.

## A small pirate clue and underwater discovery

A waxed clue at the new cog landing points west to a small lantern buoy at
**1148, 64, -1282**. A waterlogged chest hangs on a short chain at **Y59**, four
blocks below the surveyed water surface. The suspension avoids inventing exact
seabed support from eight-block survey samples. The chest contains two emeralds,
six gold nuggets and eight cookies. There is no automatic replenishment.

The proposed dive has a direct open-water return to air beside the buoy. It adds
no tunnel, hostile mob, explosive, air pocket or forced chunk loading. Swimming,
visibility, breathing time and the actual return route remain player-test gates.
Do not advertise the dive as safe or reset the filled chest after players use it.

## Evidence and admission

The baseline is the verified backup **20261027T034106Z-ecd64f**, SHA-256
`616f1f5eb67b0502b163f3cb756f5000d8498f46847e2fc1d58bfcf3bd752fed`.
The loader binds the exact completed core, port, bridge, castle, south bank, four
ships, final access master and all five native-verified detail deltas. Historical
block-entity custody and recorded circulation are unioned. A changed baseline
requires review instead of silently inheriting the earlier checks.

The exact dependencies are Small Ships **2.0.2 for NeoForge 1.21.1** and Create
**6.0.10**. The tool checks the complete cached JAR hashes and eleven inspected class
hashes. The official [Small Ships 1.21.1 source revision](https://github.com/talhanation/smallships/tree/4bfb8680a3fecd8c7e71506b941a79c51c49dffb)
declares version 2.0.2. Its `CogEntity`, `Ship`, `ContainerShip`, `Sailable`,
`SailDamage` and `ShipPartEntity` definitions were compared with `javap` output
from the actual pinned JAR. Those source and bytecode readings establish entity
IDs, multipart dimensions and NBT field names. They do not instantiate a ship.

The inherited Boat wood field is `Type`. Small Ships reads a `Sail` compound with
`State`, lowercase `Color`, and `SailHealth`; hull state includes `HullDamage`,
`Sunken`, `Sinking` and lowercase `locked`. The proposal retains these exact
spellings. The inspected Create classes are `PulleyBlockEntity`,
`PulleyContraption`, `ContraptionCollider` and `AbstractContraptionEntity`.
Create's collision machinery supports interaction with entities, but that alone
does not establish boat carriage or retention in this particular cradle.
The additional named Minecraft `EntityType.class` is pinned by SHA-256
`ce88efd23c8db67ddbf421214711030ceccb56b7e9e978657cf1d897f82af59f`.

### Fresh spatial entity admission

The proposal now includes `spatial_entity_admission`, a machine-readable contract
covering the cog berth, initial departure and complete cradle/tender body sweep.
The pure `admit_entity_snapshot` gate is tested with fixtures; **no live entity
scan has been run**. Native commissioning must query actual entity AABBs after
every target chunk is FULL and entity-ready, deduplicate UUIDs, and apply the
result in the same game tick. Repeat immediately before each spawn, launch or
movement phase. An old snapshot, partial region query or unloaded chunk fails.

- Before spawning, every entity overlapping the berth or initial departure
  blocks admission, including pets, another boat and dropped items.
- Launch may permit only the recorded commissioned cog UUID and its actual
  native Small Ships multipart children. A pet or passenger cannot inherit that
  exception by referring to the same parent.
- Empty hoist cycles may permit only a proven owned Create controlled
  contraption UUID whose captured block set matches the exact 52-block payload
  digest. Other occupants fail.
- The tender phase additionally requires the explicitly selected existing empty
  vanilla boat UUID, native type/wood, no inventory or passengers, and an actual
  AABB within the verified design envelope. Missing or oversized tenders fail.

These are spatial protection requirements in addition to the separate
moved/unloaded duplicate-cog custody check. A successful air/water block probe
cannot see entities and cannot satisfy this contract. Native implementation must
produce authentic scan receipts; fabricated fixture data is not runtime proof.

Run from the source checkout with Python 3.12+:

```powershell
python -m tools.settlement_maritime_attractions --home 'D:\A World for Two'
python -m tools.settlement_maritime_attractions --home 'D:\A World for Two' --native-probe '<returned staging directory>'
```

The finite output guard is 8 MiB. Preparation writes only a new private staging
folder. It preserves existing proposals and failed probes. It does not call the
Control Room API, RCON, a world writer, a game launcher, or a Git operation.

- `proposal.json` deliberately uses `awft-maritime-proposal:1`; it cannot be fed
  directly to the native construction bridge. Its nested candidate plan requires
  explicit parent review and admission.
- `clearance-read-only.json` is for native **VERIFY only**. It has no entity
  commands or block-entity tags. Its unknown water/air states are hypotheses until
  the exact probe completes with zero failures.
- `manifest.json` binds source inputs, dependencies, document hashes, backup,
  cell counts and remaining tests. Private seed/world paths remain in staging.
- `native-snbt-*` preserves the optional Java 21 Minecraft NBT parser probe and
  receipt. This check covers syntax, field types and round trips. It starts no
  game or server and cannot qualify mod entity loading or movement.

Only after an exact fresh native before-state pass, backup, entity-custody review
and SNBT pass may the parent extract the candidate plan for bounded construction.
The new spatial entity contract must also pass with current native observations.
Real cog creation, boarding, two-user controls, cargo, departure and restart still
need dedicated/client checks. The hoist and dive keep their independent native
acceptance gates. Synthetic tests and source inspection are not those results.
