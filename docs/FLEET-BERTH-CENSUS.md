# Fleet saved-berth census and integration order

2026-10-28 source checkpoint, branch `codex/historic-harbor-fleet`,
[draft PR3](https://github.com/Kgray44/a-world-for-two/pull/3).
The master owns placement, quay design, the native bridge and all game tests.
No fleet world/client/server action or live lease has occurred.

## Exact input and preserved reservations

Every observation in this census was genuinely read from the normal-stop
checkpoint `20261028T191243Z-6ad3a8`, archive SHA-256
`0ba7ad2097fb52273a37da6a76d8fc030133b79cd26d81b97531d8d74c2546c2`.
This is saved evidence; later city changes still require fresh native checks.
`H` means `D:\A World for Two\staging\world-tests\20261027T053650Z-artistic`.
The target remains `H/world/RosewaterArtistic`, never the configured permanent
save. The historical bridge0.6.29 registry is retained separately at
`H/staging/fleet-registry-provenance-8cfa5ae7/registry-original.json`;
it is not current installed-palette evidence.

The immutable fleet geometry remains `cec9f37`: major helper SHA-256
`fe4251af7c032257e15f90a428defb5c523bb51fea8bd09a37db43066958119a`,
smallcraft helper
`26b3ccb68473a185df827a6e0f2d3c583b6386ca836788c8bf978422976bd362`.
All studies pin the protection helper at commit
`8c0ceac28ddaad6f806e427c99432bcb072c189a`, file SHA-256
`f61f45913a9d60846bdd6a9d04e6f4a049cfdd0129f1a3d6fc2fec4612cc7984`.

The 40 common ownership records include all six additional city complete-after
masks, the bridge/transport protections and both Pippin cover points. Those two
points, `(1236,64,-1194)` and `(1224,64,-1194)`, were actually reread as AIR.
Mask record counts may overlap; their summed sizes are not a unique-cell census.
Smallcraft add Wren, conditional major berths, original cog/tender reservations
and a conservative navigation corridor. All authored AIR and reserved movement
volumes matter alongside solids. Current navigability remains untested.

## Saved candidates that passed

Bounds below are inclusive X/Y/Z and include the complete authored structure.
These are conditional source proposals, not placed vessels or dock connections.

| Vessel | Waterline origin / quarter turn | Authored bounds | Full saved cells | Two-layer under-keel water |
| --- | --- | --- | ---: | ---: |
| Resolute Wren | `(1000,63,-1366)` / 1 | `(968,57,-1380)` to `(1056,114,-1349)` | 17,358 | 2,048 |
| Tern pilot cutter | `(1168,63,-1338)` / 2 | `(1161,60,-1352)` to `(1172,88,-1318)` | 1,807 | 384 |
| Salt Marigold ketch | `(1228,63,-1320)` / 0 | `(1223,60,-1343)` to `(1235,92,-1303)` | 2,583 | 520 |

Wren's complete saved preimage contains 6,534 source-water and 10,824 AIR cells.
Tern has 796 water and 1,011 AIR; Salt Marigold has 1,104 water and 1,479 AIR.
All three have zero saved block entities or protected-cell conflicts. Tern and
Salt Marigold also have zero overlap with each other and with the **full**
target/probe masks of both held major berths. The earlier Wren source mask is
retained only as a frozen geometry reservation, not as a current observation.

The new structures contain ship-owned landing platforms. The actual quay
interfaces are **unconnected**. Wren's 24-block landing search found no qualifying
authored quay and preserved the saved ice. Any finger pier or gangway requires
the master's approved waterfront layout and exact native before states.

Use these immutable directories under `H/staging/`:

| Batch | Manifest SHA-256 |
| --- | --- |
| `fleet-berth-wren-169d2faf9ba9224f` | `35a1f45207d4b1bef6581b48fb7eb832ed462bc772d9ca893fe755f82e8a69b7` |
| `fleet-smallcraft-6c3aa58711e9a7b2` | `6c3aa58711e9a7b2032e559ba8e16c04419bbf40c9721acb3011f4850a59079f` |

The smallcraft directory is 335,273 bytes and contains five documents per accepted
craft: exact BEFORE, under-keel/boarding probe, placement, complete AFTER and
source camera recipe. Exact placement SHA-256 values are:

| Vessel | Placement SHA-256 |
| --- | --- |
| Wren | `d8aa64a72891a5f0ab48976b7c2944c005545fb8388bccd3d77cde94e69935cf` |
| Tern | `d08bd3848bbb7c0b4e08c335bcc7c105d036bed0c36d81e3baea7f8e509f8939` |
| Salt Marigold | `eb9598af1da9f5023dc8e3db8a315bf610253ee7374bfa883e0f0d52c9bb087e` |

For actual smallcraft deck captures, apply the
[camera-only override](../proposals/fleet-camera-overrides/accepted-smallcraft.json):
the generic `deck` pose inherited from the major ships sits offboard. Its corrected
pose is the existing clear onboard `working-deck` view. The original batch,
placement and immutable camera files remain preserved. Other views are unchanged.

## Held vessels and exact blockers

`H/staging/fleet-remaining-912a00f2497053b7` is 1,535,513 bytes; manifest SHA-256
`e5a26bb5851f5aa03cdf35aece8d96d3fced9bb3740e3c73441cb6a7d9ad7b08`.
It contains complete saved-state BEFORE verifications, exact obstruction reports,
nonexecutable **unapproved** plant proposals and source cameras. It contains no
placement or clearing plan. All 87,766 saved-state reads were bounded.

| Vessel / retained first pose | Complete known cells | Marine plants | Other obstruction cells |
| --- | ---: | ---: | --- |
| Golden Petrel `(1110,63,-1344)`, turn1 | 29,492 | 160 | Three ice; one `fishofthieves:shoal[treasured=false]` |
| Mercy of the Tide `(1230,63,-1376)`, turn1 | 36,756 | 248 | Fourteen dirt, two gravel, seven sand, one waterlogged `hybrid_aquatic:tube_sponge` |

Both berths fail strict saved admission. They have zero unknown cells, existing
block entities, common protection overlaps, Wren overlaps or mutual overlap.
The required two-block keel margin is **not verified**. Plant handling alone
would not resolve the remaining blockers. Preserve ice, terrain, shoals, sponges,
loot and every inventory. No vegetation permission is inferred.

Earlier finite seaward checks from checkpoint306 remain explicitly labeled old
first-refusal observations. No broad pose sweep or clearing fallback was run.
The safe fallback is to retain these source designs and request the master's
specific berth/terrain decision while advancing the independent passing batches.

Reed Fin has no admitted river berth or placement file. Four deliberately chosen
poses were refused by Rosebridge protection, the actual river navigation reserve
or saved masonry. The observed river bend runs near X1280..1300/Z-1096..-1072;
an assumed straight channel at X1193 is not valid. Retain the river and bridge
clearance; master selection of a new river edge is required.

## Deployment and verification

For each accepted batch, the master must bind the current installed candidate,
checkpoint and source pins; prove the current native palette, exact BEFORE and
support cells; then census actual occupants and body/sweep collisions. Only then
place the exact admitted document once, settle and verify the **whole** AFTER.
Preserve uncertain partial outcomes and supplied inventories rather than replaying
stock. A changed preimage stops that batch. No specialist owns that action here.

Wren's detailed sequence and 21 camera recipes are in
[FLEET-WREN-BATCH](FLEET-WREN-BATCH.md). Smallcraft recipes cover bow, stern,
broadside, elevated, deck and their compartments. They are camera instructions,
not captured images. Master-approved quay access, normal water return, circulation,
cannon interaction, real native craft use and hoist commissioning remain required.
Follow [maritime commissioning](FLEET-MARITIME-COMMISSIONING.md) for the preserved
craft-custody failure, native identities, two-player use, restart and performance.

The combined three berth modules passed 25 targeted tests in 6.937 seconds.
The remaining-major module's final provenance-only refresh passed its eight tests
again in 4.639 seconds. Parent review independently verified every current output
hash and the full smallcraft/held-major intersection masks. Earlier full discovery
passed 988 tests with one Windows symlink-privilege skip; this is not a claim that
the expanded suite was rerun. Real game graphics, use, multiplayer, restart and
harbor performance remain unverified by this workstream.

Each exporter bounds private D: output to 32 MiB and calls ReserveGuard. Source,
test and Git writes are separately bounded on C:. Both drives were measured above
the separate 30 GiB reserve. Monitoring does not constrain external applications
or already-running writers. Preserve all earlier immutable artifacts and failures.
