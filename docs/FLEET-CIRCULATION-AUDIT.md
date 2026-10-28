# Fleet circulation and source-camera audit

2026-10-28. Conservative source audit only; no Minecraft walking, client input,
native call, save/runtime modification or geometry change was performed.

Frozen sources inspected:

- `tools/grand_harbor_fleet.py`: `fe4251af7c032257e15f90a428defb5c523bb51fea8bd09a37db43066958119a`.
- `tools/grand_harbor_smallcraft.py`: `26b3ccb68473a185df827a6e0f2d3c583b6386ca836788c8bf978422976bd362`.
- `tools/grand_harbor_berth.py`: `f61f45913a9d60846bdd6a9d04e6f4a049cfdd0129f1a3d6fc2fec4612cc7984`.

The seven immutable templates came from
`H/staging/fleet-seven-cec9f37`, with every template checked against its manifest
hash. H is the construction home recorded in `docs/coordination/WORKSTREAMS.md`.
Current world-camera recipes inspected were Wren's `fleet-berth-wren-169d2faf9ba9224f`,
Petrel/Mercy's `fleet-remaining-912a00f2497053b7`, and Tern/Ketch's
`fleet-smallcraft-6c3aa58711e9a7b2`. These names identify source proposals;
they do not assert that a vessel or repair is currently deployed.

## Actual findings

### 1. The generic smallcraft `deck` frames are offboard

The shared generic local feet position `(3,2,-18)` is ahead of Tern's bow
(`Z=-14`), Ketch's bow (`Z=-17`) and Reed Fin's bow (`Z=-10`). The cell below
that position is **UNWRITTEN**, rather than an authored deck. It should not be
used as evidence of an onboard deck inspection. The pose can still be a
spectator exterior view; its existing label is misleading.

| Vessel / proposed pose | Existing generic `deck` world feet | Existing onboard `working-deck` alternative |
| --- | --- | --- |
| Tern; origin `(1168,63,-1338)`, rotation2 | `(1165,65,-1320)` | `(1166.5,65,-1337.5)` |
| Salt Marigold; origin `(1228,63,-1320)`, rotation0 | `(1231,65,-1338)` | `(1229.5,65,-1320.5)` |
| Reed Fin; no admitted world origin | Local `(3,2,-18)` | Local room-anchor-derived feet `(1.5,2,-0.5)`; no current world recipe is asserted |

For the exact two existing world alternatives, direct inspection of translated
source fields found:

| Alternative | Floor cell / state | Feet and head cells |
| --- | --- | --- |
| Tern `working-deck` | `(1166,64,-1338)`, `chipped:detailed_dark_oak_planks` | `(1166,65,-1338)` and `(1166,66,-1338)`, explicitly authored AIR |
| Salt Marigold `working-deck` | `(1229,64,-1321)`, `minecraft:spruce_planks` | `(1229,65,-1321)` and `(1229,66,-1321)`, explicitly authored AIR |

The practical correction is camera-only: select those existing `working-deck`
frames instead of generic `deck`. Preserve the placement batches. The camera
files are pinned by SHA-256:

- Tern: `367882e5dbf72e988692b958736545154c41f323707d2ece47fba557a6b0043c`.
- Salt Marigold: `35517786c9f6c42dc5687665f755ce36085122757c90a797270ae98c917b7700`.

The parent independently confirmed these same explicit floor/body cells in the
translated full-AFTER source. Their native/current-world state still belongs to
the master's normal placement and inspection process.

### 2. Rotated fractional camera points drift from voxel centers

Block-coordinate quarter turns correctly map the voxel `(x,z)` to `(-z,x)` for
rotation1. Applying that same formula directly to the center `(x+0.5,z+0.5)`
puts a camera one block west of the rotated voxel's center. The displacement
also affects the target. This is a **source-camera precision finding**, not a
hull, room or placement defect.

For example, Wren's captain anchor `(2,7,24)` translates to floor voxel
`(976,70,-1364)`. Its intended standing center is `(976.5,71,-1363.5)`;
the current fractional-point recipe has `(975.5,71,-1363.5)`, in the adjacent
source cell. That current cell did not intersect a known authored obstacle in
this audit.

Continuous point rotation about the voxel origin's center would require offsets
relative to the present result of `(+1X,0Z)` for rotation1, `(+1X,+1Z)` for
rotation2, and `(0X,+1Z)` for rotation3, applied to both feet and target.
**These offsets are explanatory, not an approved override.** Each corrected
frame would need a new body/floor check before use. The existing tested
`working-deck` alternatives above remain the immediate recommendation; do not
change their coordinates merely to recenter them.

### 3. Major-ship water return remains a separate dependency

In the frozen major templates, the sea landing's floor is local Y1, with a
walking surface at Y2. Source water is below local Y0, so the landing surface is
two blocks above the water surface. None of the four frozen major templates
contains an external return ladder at that landing. This establishes a missing
authored ladder connection, **not a proved failure of native boat dismount**.
Actual swimming, boarding and skiff dismount remain unverified.

Wren already has a separate nonexecutable three-ordinary-block request in
`H/staging/fleet-access-f29a648280829067`; this audit does not supersede it.
The equivalent minimal source dependency for the other new majors is:

| Vessel / conditional pose | Proposed local ordinary cells | Proposed world cells |
| --- | --- | --- |
| Golden Petrel `(1110,63,-1344)`, rotation1 | Full timber backing `(21,0,0)`; east-facing ladder `(22,0,0)` and `(22,1,0)` | Backing `(1110,63,-1323)`; south-facing ladder `(1110,63,-1322)` and `(1110,64,-1322)` |
| Mercy `(1230,63,-1376)`, rotation1 | Full timber backing `(20,0,0)`; east-facing ladder `(21,0,0)` and `(21,1,0)` | Backing `(1230,63,-1356)`; south-facing ladder `(1230,63,-1355)` and `(1230,64,-1355)` |

Their existing upper backing/exit floors at local `(21,1,0)` and `(20,1,0)` are
full authored timber. New lower backing and ladder cells must receive actual
current preimages; UNWRITTEN source cells are not treated as available AIR.
Exit headroom must cover the two ladder cells' upper bodies and the adjacent
landing. These additions would consume existing proposed AIR clearance and
therefore require a separate approved dependency and updated full-AFTER/probes.
Both major berths are already refused for independent marine/hard obstructions;
these ladder proposals do not resolve or authorize those changes.

For retained Lark, the existing outer landing at local `(19,1,0)` is a **top
slab**, so it should not be assumed to provide a full ladder attachment face.
A minimal additive alternative is a two-high full timber post at local
`(20,0,0)` / `(20,1,0)`, with east-facing ladders at `(21,0,0)` / `(21,1,0)`.
At the existing reference origin `(1140,63,-1450)`, rotation0, those are timber
`(1160,63,-1450)` / `(1160,64,-1450)` and ladders `(1161,63,-1450)` /
`(1161,64,-1450)`. The post's top matches the existing top-slab walking level.
This preserves the original slab and asks for four new ordinary cells.
All four cells and exit headroom are unqualified in this source audit: no saved
or native admission, neighbor-survival result, inventory write or placement
authority is claimed. The master must inspect current surroundings before
considering this small source dependency.

## Anchor and ladder results, with evidence limits

All **68 named room anchors** were checked for their structural floor and two
body cells. No new authored solid obstruction was found. Forty-six anchors have
both body cells explicitly represented as source AIR/interactable traversal
cells; **22 touch UNWRITTEN body cells**, mostly open decks, balconies and
landings. The source graph's absent-cell AIR convention does not establish
current-world clearance at those cells.

The **80 current world-camera frames** were checked directly against translated
world block fields, including a 0.6-by-1.8-block standing body. No known authored
body obstruction was found. Thirty-five frames have all checked body cells
represented in source; **45 touch UNWRITTEN cells**. Doors, ladders and carpets
were treated as traversal cases, not certified using native collision shapes.
Camera support is separately distinguished above; an exterior spectator frame
does not require a walking floor and is not a walking test.

The seven templates contain **90 ladder cells in ten columns**. The following
top exits have plausible source support, with no newly demonstrated solid
obstruction or disconnected exit:

| Vessel / ladder | Top rung, local | Adjacent exit floor, local |
| --- | --- | --- |
| Lark emergency | `(0,8,-16)` | `(1,8,-16)`; the other directions include raised slabs |
| Petrel emergency | `(6,9,-9)` | `(5,8,-9)` |
| Wren emergency | `(1,8,-9)` | `(0,7,-9)` |
| Mercy emergency | `(6,8,-9)` | `(5,7,-9)` |
| Petrel derrick | `(-9,16,-12)` | `(-9,15,-11)` |
| Wren derrick | `(-7,15,-12)` | `(-7,14,-11)` |
| Mercy derrick | `(-10,15,-12)` | `(-10,14,-11)` |
| Tern / Ketch return, one each | `(7,1,0)` | `(6,1,0)` |
| Reed Fin return | `(6,1,0)` | `(5,1,0)` |

Some exit head cells are UNWRITTEN, as counted above. This table is a source
inspection result, not native ladder survival, collision, reach or walking
acceptance. No tests were broadly rerun; focused read-only cell comparisons were
used for the concrete findings. Frozen producers, templates and placement
batches remain unchanged.
