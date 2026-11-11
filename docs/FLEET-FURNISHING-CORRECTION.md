# Fleet interior and working-detail correction

Prepared October28,2026,21:59EDT (October29,01:59UTC). This responds to the
owner's in-game finding that the new ships were sparsely furnished. The existing
art and interiors are **NOT ACCEPTED**. This packet is a source correction,
with no new Minecraft placement, screenshot, player walkthrough or acceptance.

The six original hulls remain at their actual candidate55/63 poses. No hull,
rig, existing cargo, container, stock, cannon, stair or room anchor is replayed.
Rosewater Lark and the original cog/tender are outside this delta.

## What the correction contains

| Vessel / origin / rotation | Furnishing changes | Added cells / new explicit SNBT / retained original explicit SNBT |
| --- | --- | --- |
| Golden Petrel `(1110,63,-1360)`,1 | Green merchant counting saloon with ledgers, writing tables, sea cabinets and sitting corner; officer and watch belongings; terraced grain, folded canvas and spare-spar rack; victualling dresser, grain inspection/tally bench, gun-cleaning station, reserve casks, incoming/outgoing cargo groups and laid crew mess |137 /16 /8|
| Resolute Wren `(1000,63,-1366)`,1 | Compact red dispatch cabin with packet desks, records, reading seat and lectern; officer/watch details; courier ledgers and repair stores; watch drinks, gun-maintenance bench, sorting station, wash/issue table, sealed dispatch cases, recognition cloth, storm canvas and lookout rest |104 /7 /9|
| Mercy of the Tide `(1230,63,-1392)`,1 | Blue relief-planning saloon, linen cabinets, larger after settee; officer/watch and sick-berth details; terraced relief cases and repair stores; ration dresser, clean preparation counter, washing alcove, linen repair bench, receiving and covered dressing cases, boat-party rest and mess |171 /14 /14|
| Tern `(1168,63,-1338)`,2 | Pilot chart station and hourglass, cupboard, new pilot-log/spyglass chest, berth-side cask and candles, sounding/repair chest and duty sign |9 /3 /2|
| Salt Marigold `(1228,63,-1320)`,0 | Fish-preparation bench and cutting board, tackle/knife chest, provision case and hay, folded canvas, dry pantry, supported cold pot and net-mending sign |11 /3 /2|
| Reed Fin `(1336,63,-1044)`,0 | Mixed river freight, repair surface and tool chest, folded canvas, spare timber, navigation/tally chest, chart table and freight sign |11 /3 /1|

These counts describe the patch scope, not visual quality. New explicit SNBT is
37 empty major-ship storage tags, six new stocked smallcraft chests and three
signs. Default block entities created by their blocks are not counted as explicit
SNBT. Existing36 explicit original inventory tags remain byte-identical in the
source model and are excluded from every proposed PLACE payload. Actual inventory
preservation still requires current runtime observation; source equality is not
a gameplay receipt.

Major-ship rooms are furnished for different occupations rather than receiving
one identical cabin layout. The source pass retains two-high passages, room
anchors, backed ladders, stairs, hatch openings, gun breech approaches, tender
approaches and derrick load sweeps. No ammunition, explosive, fluid, new gun,
entity, command, physics-ship conversion or quay construction is added.

## Exact source and immutable packet

New source is `tools/grand_harbor_furnishings.py`,
`tools/grand_harbor_deck_furnishings.py` and
`tools/grand_harbor_smallcraft_furnishings.py`, with corresponding dedicated
tests. The original fleet/smallcraft builders and original placement templates
are unchanged. The correction reconstructs those original models and emits
only additions to their explicitly authored AIR cells. UNWRITTEN is refused.

With **H**=`D:\A World for Two\staging\world-tests\20261027T053650Z-artistic`,
the private packet is:

`H/staging/fleet-furnishings-20261029-source-v1`

Manifest SHA256:
`5bdba581c5fbb22e8056894bccf9c016eb0e1e3c34668704a81febaac8704965`.
The packet is331,887bytes,36 hashed documents plus its manifest. All36 document
hashes and all eight dependency hashes were independently checked after export.
It uses the preserved actual historical registry SHA
`8cfa5ae77e20b8b5c1730b2928c55156557ebecb7e84480142088bda04ef92c4`;
current native palette verification remains necessary.

Each vessel directory contains `before-VERIFY-ONLY.json`,
`retained-supports-VERIFY-ONLY.json`,
`delta-PROPOSED-NOT-ADMITTED.json`, `normal-joins-SETTLE-ONLY.json`,
`complete-after-VERIFY-ONLY.json` and `source-detail.json`.
All native-format files remain verification-only/construction-forbidden.
There is no executable admitted PLACE file or deployment authority.

The BEFORE expectations are derived from the original placed source; they are
**not** an invented saved/current all-six census. The newest available archive
when prepared was c33037, which predates Petrel/Mercy/Reed. The existing canonical
native custody binding remains6ad3a8/`0ba7ad2097fb52273a37da6a76d8fc030133b79cd26d81b97531d8d74c2546c2`.
Only genuine current native BEFORE/support/entity/BE admission can establish
that every proposed target is still empty and safe. Stop on any difference.

## Validation and attempts

`python -B -m unittest discover -s tests -v` ran1038 tests in55.525seconds:
**1037 passed, one skipped, no failures/errors**, exit0. The skip remains the
Windows fixture-symlink privilege test (`WinError1314`), not a fleet failure.
All17 new furnishing tests are included. They exercise original stock/block
preservation, source circulation, original-AIR-only deltas, supported props,
occupied/missing/reserved-cell refusal, original-tag tamper refusal, empty new
major storage, no explosive/projectile supplies and no full-hull replay.

Local log: `.local/fleet-verification/unittest-furnishings-20261029.txt`, SHA256
`28f045fd66e91266b7724bebf8ea94d906e2c644d3c6a3c3c4d0e805655e907a`.
Logs stay private and are not committed. `python -B -m tools.pack validate`
passed with208 mods/no errors; `node --check control_room/static/app.js` exited0.

All six recipes also passed against the preserved full native registry, with
14/14/15 major-ship rooms and three rooms/stations per smallcraft reached by the
conservative source walk graph. Actual collision shapes and movement remain
unverified. During authoring, strict checks rejected an occupied Wren cabin
tabletop, low Wren hull-side targets and Petrel's station11 mess top, where the
original companionway had removed the table. Those recipes were corrected and
rechecked in memory; no corresponding world write was attempted.

The native verifier compares IDs and selected structural orientation fields
(`facing/axis/half/part/type/hinge`), not every cosmetic property. Actual
Minecraft views must assess shelf/table joins, signage, block models, lighting,
cabinet appearances and artistic density. Passing source/native JSON checks
cannot grant the owner's visual acceptance.

## Master deployment and remaining work

Five vessels are ready for **current admission**, independently of Mercy.
Mercy's whole detail packet remains held behind her actual water defect:
`minecraft:water[level=6]` at `(1241,56,-1398)`, expected AIR. Preserve the failed
settle and one-cell diagnostic receipts in `FLEET-NATIVE-DEPLOYMENT63.md`.
The separate shell verification/interior AIR repair proposal is not included or
silently applied here. Verify the real hull, dryness and completed normal AFTER
before admitting Mercy's furnishings. Stop if water returns.

For each available ship, the master must verify the current candidate/process,
empty roster, cleanup state and exclusive scope; authenticate the packet/source
hashes; obtain genuine native BEFORE/support/new-palette/BE/entity-body checks;
admit only its delta once; normally reconcile, then verify all targets, new
fixture stock and retained margins. Do not replay the original hull or old NBT.
Photograph bow/stern/broadside/elevated/deck/belowdeck views, inspect every room
and test actual routes, storage, boarding and ship-side work areas. The owner's
approval follows those actual views, not block totals. Preserve current player
transport systems and all other workstream construction.

No new world, client, JVM, official-server restart, runtime installation or
permanent-world promotion occurred in this correction. Quay links, Mercy's
repair, sailing/rowing/transfer, cannon/hoist operation, multiplayer, normal
restart persistence and full-harbor performance remain separately unfinished.
No TPS/MSPT/FPS/CPU/RAM claim is made by these source tests.

ReserveGuard admitted the8MiB D: export and bounded source/test writers. Before
the full checks at01:58UTC, free bytes were C118,712,647,680 and D281,673,367,552;
the test forecast was C512MiB/D128MiB. Both separate30GiB reserves passed.
This is monitoring of owned work, not an OS quota or control of unrelated apps
and existing writers. No world, JAR, credential, cache or runtime log enters Git.
