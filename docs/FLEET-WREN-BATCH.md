# First exact fleet batch: Resolute Wren

Source prepared2026-10-28 for the master. No native operation, player action,
save write or runtime change was performed by this fleet lane. Follow the
authoritative master `docs/coordination/WORKSTREAMS.md` and the
[fleet integration report](FLEET-INTEGRATION.md).

Proposed origin **(1000,63,-1366)**, quarter-turn rotation **1**. The historical
reference(1000,63,-1350) intersects saved ice. This candidate shifts16blocks
seaward and preserves the ice. It is a proposed dockside hull berth requiring
a separately approved dock interface, not an already docked ship.

## Frozen inputs and immutable files

Private directory: `H/staging/fleet-berth-wren-9d0b486aae22282e`, where H is the
existing construction home defined by WORKSTREAMS.
Manifest SHA-256:
`308a2a1cdf8dc4821639a3ba56af4608b3c08e26570b2bb76347673a1e276eb0`.

Geometry commit`cec9f378f17f8a7a58c265cafe124a7dbceae623`;
fleet source`fe4251af7c032257e15f90a428defb5c523bb51fea8bd09a37db43066958119a`.
Checkpoint`20261028T180051Z-30624d`, SHA-256
`3cb269d28ae1ccbac882a44d35277d82c83582274abad2f1cf3b41566d3e9b24`.
The manifest also pins actual registry, native helpers, protected sources and
read-only saved region members. It grants no write authority.

| File | Master operation | Exact SHA-256 |
| --- | --- | --- |
| `current-before-VERIFY-ONLY.json` | Fresh native VERIFY immediately before placement | `2c932d70570dd6ec4cd7af53af16c3239946961bd8292a964281d01100216976` |
| `under-keel-load-VERIFY-ONLY.json` | Fresh native VERIFY of depth/load/boarding | `66cc6a29175c7891a89a8a3e5ed48a20e96cd3edf8ed67cc95ff11854b1df5ce` |
| `placement.json` | PLACE only after current admissions pass | `4115e860fc9fd685ec468cf7b2ab5b81837dfdefda22364703c817d64c44b6c3` |
| `complete-after-VERIFY-ONLY.json` | VERIFY after normal native settling | `c38c2d024e93fb2165901cdb6abc03754352364626e7466ec15b7a8b5b511b4c` |
| `camera-recipe.json` |21 actual Minecraft poses | `f515a3b99403c5fae7cd37b9645ba4e40198f3efff5b2cd6520e1e9b5a0a1e4d` |

The source-only binder is `tools/grand_harbor_berth.py`. It refuses another home,
stale checkpoint, changed source/pins, non-source water, ice, natural blocks,
block entities, unknown chunks and protected positions. To reproduce into a new
immutable output after requalifying all exact inputs:

```powershell
python -B -m tools.grand_harbor_berth --fleet-source-sha256 fe4251af7c032257e15f90a428defb5c523bb51fea8bd09a37db43066958119a
```

## Saved admission and dock boundary

Saved306 admission examined17,358 exact cells:6,534 source-water and10,824 AIR.
There are zero block entities or other target blocks. All15,148 authored cells
are covered, including7,431 intentional AIR cells. The full two-block under-keel
margin contains2,048 water cells. There is zero overlap with460,570 protected
authored/AIR/BE positions from33 pinned town, quay, hull, bridge and zipline sources.

Inclusive world hull/rig/landing bounds:
`[968,57,-1380,1056,114,-1349]`.
Combined under-keel/load/boarding-probe bounds:
`[968,55,-1381,1033,78,-1346]`.

The translated landing is(1000,64,-1350). An actual Euclidean24block-radius,
Y62..67 saved search found **no authored walkable quay** and31 retained ice cells.
A separately surveyed and master-approved finger-pier/short gangway is needed.
This batch changes no quay, street, shore or connecting gangway.

## Master execution order

1. Revalidate the master lease, exact save/candidate/JAR/checkpoint, player
   exclusion, free storage and owned-resource cleanup. A saved source is not a
   current native receipt. Run the separate-drive30GiB guard with the master's
   bounded runtime/client allocation; the source output itself is capped32MiB D:.
2. Use the existing hash-bound `tools.artistic_review.native` path to VERIFY
   `current-before-VERIFY-ONLY.json` and `under-keel-load-VERIFY-ONLY.json`.
   Obtain a current native entity-AABB census for hull/rig/boarding/load. Saved
   block-state admission does not census live entities.
3. Stop on any changed state, occupant, player arrival, stale receipt, unclosed
   resources or failed terminal. Only the master then invokes PLACE for the
   exact `placement.json`, normal SETTLE for that same placement plan, and VERIFY
   for `complete-after-VERIFY-ONLY.json`. Never PLACE a VERIFY-ONLY document.
4. Retain every terminal and partial. Do not retry to hide a failure. If a bound
   input/checkpoint changes, preserve these artifacts and prepare a new batch.
5. After actual state/BE/inventory verification, use the21 slugged camera recipes
   with a new short unique prefix and exclusive client slot. Walk every room,
   boarding stairs and the backed ladder/operator route. Inspect actual graphics
   before extending placement to the rest of the fleet.

The parent independently verified hashes, native plan headers, inventory SNBT
and exact AFTER=BEFORE overlaid by PLACEMENT. Ten portable binder tests cover
rotation, tags, complete probes and refusals; the latest combined35 focused
tests passed in14.488seconds. These are source results. Native placement,
graphics, collision, hoist/cannon use, sailing, multiplayer, restart, performance
and owner acceptance remain unverified. The large hull is static architecture;
real sailing and rowing entities retain their separate custody gates.

Storage monitoring covers the owned bounded writer and cannot constrain other
apps or existing runtime writers. No full server/world copy was created.
