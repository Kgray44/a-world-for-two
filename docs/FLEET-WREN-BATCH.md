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

Private directory: `H/staging/fleet-berth-wren-169d2faf9ba9224f`, where H is the
existing construction home defined by WORKSTREAMS.
Manifest SHA-256:
`35a1f45207d4b1bef6581b48fb7eb832ed462bc772d9ca893fe755f82e8a69b7`.

Geometry commit`cec9f378f17f8a7a58c265cafe124a7dbceae623`;
fleet source`fe4251af7c032257e15f90a428defb5c523bb51fea8bd09a37db43066958119a`.
Checkpoint`20261028T191243Z-6ad3a8`, SHA-256
`0ba7ad2097fb52273a37da6a76d8fc030133b79cd26d81b97531d8d74c2546c2`.
The manifest also pins actual registry, native helpers, protected sources and
read-only saved region members. It grants no write authority.

The pinned registry is a historical native export from
`2026-10-27T23:11:56.377525200Z`, bridge`0.6.29`, SHA-256
`8cfa5ae77e20b8b5c1730b2928c55156557ebecb7e84480142088bda04ef92c4`.
Its original bytes are retained at
`H/staging/fleet-registry-provenance-8cfa5ae7/registry-original.json`.
It is not a current candidate50 palette export. Fresh master-owned native
parsing/BEFORE/AFTER validation must qualify current runtime states; the frozen
source checks alone do not do so.

| File | Master operation | Exact SHA-256 |
| --- | --- | --- |
| `current-before-VERIFY-ONLY.json` | Fresh native VERIFY immediately before placement | `71012b8da7fef9dbf5696207182d47030ac51ca99548f0caae247ca60b038323` |
| `under-keel-load-VERIFY-ONLY.json` | Fresh native VERIFY of depth/load/boarding | `681e8d6b37eb82b78ec6396e50c01a704dc3a6cc96bdb89a4f27201be3637b6f` |
| `placement.json` | PLACE only after current admissions pass | `d8aa64a72891a5f0ab48976b7c2944c005545fb8388bccd3d77cde94e69935cf` |
| `complete-after-VERIFY-ONLY.json` | VERIFY after normal native settling | `2064645686e03e530d04ba66be8c3074e2617769155bdae5b0dcaca0917d3229` |
| `camera-recipe.json` |21 actual Minecraft poses | `f515a3b99403c5fae7cd37b9645ba4e40198f3efff5b2cd6520e1e9b5a0a1e4d` |

The source-only binder is `tools/grand_harbor_berth.py`. It refuses another home,
stale checkpoint, changed source/pins, non-source water, ice, natural blocks,
block entities, unknown chunks and protected positions. To reproduce into a new
immutable output after requalifying all exact inputs:

```powershell
python -B -m tools.grand_harbor_berth --fleet-source-sha256 fe4251af7c032257e15f90a428defb5c523bb51fea8bd09a37db43066958119a
```

## Saved admission and dock boundary

Saved6ad3a8 admission genuinely reread17,358 exact cells:6,534 source-water and10,824 AIR.
There are zero block entities or other target blocks. All15,148 authored cells
are covered, including7,431 intentional AIR cells. The full two-block under-keel
margin contains2,048 water cells. There is zero overlap with40 ownership records
covering town, quay, hull, bridge and zipline masks, including all six new city
batches/eight buildings and both Pippin cover points. Those cover points were
independently reread as AIR. Both saved regions were reread from the new archive:
`r.1.-3.mca` SHA`9f824140d3f371a6a4997dfe9dce2e545f82b1403e9bd48596718385021d4cf1`;
`r.2.-3.mca` SHA`f0d6251bd0e7e4ea4518ce849605e8712e298d3c663724865fa1b328b15d1d60`.
The older306 artifacts remain preserved and were not relabelled.

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
