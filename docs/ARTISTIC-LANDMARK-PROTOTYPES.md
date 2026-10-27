# Rosewater palace, castle approach and Rosebridge prototypes

These are original, separately staged prototypes for the owner's artistic restart. The previous castle and bridge failed visual acceptance. Native placement counts, map tiles and material-run checks do not reverse that result. The official world is not a target of this tool. Current evidence is a mixture of source checks and specific real staging-client images, identified below; no final owner acceptance is inferred.

The actual baseline client screenshots show why a replacement is needed: the castle has large uninterrupted masonry faces and an indistinct arrival, while the bridge is a broad timber strip surrounded by buildings that obscure its purpose and channel. This draft starts again with authored proportions and inhabited detail rather than adding another layer to those shells.

## Castle approach

The composition is a narrow, rising town lane between two differently shaped timber lodges, opening into a rose forecourt and a deep, pointed gate. Unequal octagonal towers flank the gate. An L-shaped archive wing and a small open cloister make an asymmetric silhouette; the gate remains legible from the walking approach. A lantern roof, double chimney, crossed gables, pale string courses, rose balcony and smaller roof finials interrupt the silhouette for identifiable architectural reasons.

The lodges have workshops, desks, books, seats, real cottage doors and Macaw windows. The castle has a correspondence room, archive salon, gallery, chart lookout and quiet tower alcove. Ordinary stairs connect the wing and gallery; a winding stair reaches the lookout. A reflecting rill, two little crossings, roses, benches and lanterns give the cloister a quieter scale. These are representative rooms, not a claim that the complete future castle is finished.

Local ground is Y63, lodge/lane floor64, raised castle court72 after the suggested +4 elevation offset. Gate/castle floors are local68; the highest finial is local106. The first proposed origin is X1214,Z−1008 with Y offset+4, giving authored bounds X1182..1244,Z−1028..−962 and heightY68..110. These bounds remain east of the western river in the earlier natural survey. That sparse, old survey is planning evidence only: the parent must confirm actual fresh staging ground and dry land for every inhabited footprint. No house may enter a river, navigation channel or bridge underspan.

## Rosebridge

The alternative upstream bridge has three unequal, genuinely open segmental arches, cambered road, stepped banks, pointed cutwaters, proud arch rings, two opposed pedestrian overlooks and small lantern/rose niches. It contains no house, room, inventory, tollhouse or oratory beneath the span. Only bridge piers and abutments enter water.

Its local road is Y69 at either end and74 at the center, with water atY63 in the optional display canvas. The center arch has nominal eight-block soffit clearance above that canvas water. It is suitable for an upstream pedestrian/tender crossing, **not a tall-ship route**. Preserve the separate main maritime bascule corridor. Do not place its synthetic context over a real river.

The actual staging crossing is X1248,Z−1104 with Y offset+1 and a90° clockwise turn, giving a road running east–west. A fresh completed native four-block profile (`fe5b49af0f42a47e0ca249fc1f4732b3c344469e2611de4e4e83f4c4e4e4fd75ec`,1,089 samples,zero failures) supports dry approaches and reports a minimum sampled bed ofY55. The exported pier foundations extend toY53, two below that sampled minimum. Four-block samples do not individually prove every unsampled bed cell. Eleven surveyed block entities retain a one-block Chebyshev margin; the nearest target is two blocks away.

The bridge's western descending tail was removed atX≤1200 to meet the separate bascule's actual Y70 southern landing. The main bridge owns the landing and machinery; this bridge begins atX1201. The two immutable source plans have **zero shared target coordinates** after the parent opened the main landing's east railing and moved its garden pocket. The accepted staging payload (`9c9b37cea97a69d9f510bfed83b70c072793ebc35fed175ce50b3355506a51f2`) has14,513 targets, boundsX1201..1308,Z−1114..−1095, and contains no moving machinery. The alternative western channel near the castle has a cliff overY100 and was rejected as a flat-approach site.

The quarter-turn transform moves actual XYZ coordinates, cardinal facing values, directional wall-connection property names, horizontal log axes, route points and both camera positions and targets. Transformed states are checked again against the actual registry. Camera yaw/pitch is recomputed from the transformed points. Castle rotation is refused because its custom roof part orientation needs a separate native review.

## Source and review contract

`tools/artistic_landmarks.py` constructs the designs against actual registered block IDs and properties. Macaw roofs, doors, windows, lights and fences, Handcrafted furniture, and Chipped/Rechiseled masonry are actual installed palette choices. Fictional or silently downgraded states are refused.

Every authored architectural block—including floors, roofs, foundations and piers—is checked by `tools/artistic_materials.py`: a material ID may exceed three consecutive blocks in at most one Cartesian axis and may never exceed nine. Facing changes do not count as material changes. Deliberate panels, string courses, framed boards, dressed piers and roof seams supply the breaks. Only explicitly labelled synthetic landscape display cells are outside this building check. Courtyard planting soil stays in the authored geometry.

The CLI requires a separately hosted path containing `staging`, a native registry whose world is inside that runtime, and its verified backup receipt. It writes a unique prototype JSON and manifest under that staging runtime. It never writes generic `plan.json`, starts a game, issues a command, edits a world or installs itself. Payload commands and explicit inventory data are empty. The manifest includes source/registry/backup hashes, local camera positions, inhabited footprints, room purposes and walking-route samples. It also provides transformed `world_cameras` and `world_routes`; the original local coordinates remain available alongside the recorded X/Y/Z origin offset and rotation.

Example after the parent exports the fresh staging registry:

```powershell
python -B -m tools.artistic_landmarks --home '<separate staging runtime>' --prototype castle-gatehouse --x 1214 --z -1008 --y-offset 4
```

The corresponding bridge invocation also requires the exact native profile and separately reviewed main-bascule plan:

```powershell
python -B -m tools.artistic_landmarks --home '<separate staging runtime>' --prototype rosebridge --x 1248 --z -1104 --y-offset 1 --rotation 90 --profile '<completed native profile>' --junction-plan '<same-stage bascule prototype.json>'
```

The parent placed the14,513-target bridge and reviewed actual `rosebridge-water.png` and `bridge-junction.png` client images. The arches, cutwaters, cornices and level road branch are visible improvements. The junction image also exposes some half-block support gaps at decorative caps/lanterns and stark approach walls. Those specific defects and softer bank landscaping remain revision work; the bridge has no final visual acceptance.

An immutable detail revision is staged as `prototype-rosebridge-872a54468be5be32/prototype.json`, SHA256 `872a54468be5be32d211ff92d4423256cfb794b9357984a1eaab8f466e0c9f76`, source `072fb455382a83e8c4b484113cd86d660571a89536225d989bf052da7ad3a190`. It changes12 top-slab caps to supported bottom slabs and one ramp branch cell, adds316 targets, and retains14,500 unchanged targets. Total14,829,zero omissions; boundsX1201..1308,Z−1116..−1095. Its explicit before/after ledger has SHA256 `53442813c5c68b4a4ffd714472b5bb2ed8c7b000bce984aab1152264106a2d08`.

The new low terrace occupies the dry north/east gravel bank, with a real ramp branch, rose pockets, seat/table group, urn, low retaining edge and supported lighting. It leaves the wet south/east shoreline and all moving machinery alone. Every one of its66 horizontal support/decor footprint cells has all four surrounding profile samples dry atY63..65; sampled evidence still requires native before-state admission. Both native block-entity margins and whole-source material rules pass. A regression refuses a wet surrounding corner and a protected native ground block entity. Eleven focused source tests pass. The1.33MB revision is staged only, bound to the same stopped `bffb38…` checkpoint; native placement and real images remain pending. Use `--bank-landscape` with the exact profile, joined main bridge and `--previous-plan` pointing to the placed9c9b37… bridge to reproduce the proposal under a new verified checkpoint.

Default export **excludes synthetic display context**. `--include-context` is only for an explicitly disposable comparison canvas; it includes authored grass/river display cells and is not a terrain-survey substitute. A fixed output bound of16MiB is reserved before writing. No native placement authority is granted by generating a file.

The first source draft passed actual-registry assembly and the complete architectural material-run rule. Focused geometry regressions cover clear route samples, door halves, terrace foundations, open arches, empty commands and staging-only output. These are source checks. Parent native placement, actual day/night/shader screenshots, readable close details, interior traversal, site safety and artistic revision are still required. No graphical acceptance has been claimed.

## Actual r1 review and the next revision

The parent placed the immutable first gatehouse draft (`1b7f1f177437b5ef9282d763d2906374c85ca8276dffa411d2032475e50e807d`) into the separate clean `RosewaterArtistic` staging world. Its eight actual client images were reviewed. The narrow lodge approach and stepped gateway improve the arrival, but **r1 failed propagation**: west-wing masonry remained a large rectangle, windows read as black slits, the archive had too little furniture, and a continuous daylight gap separated tower walls and roofs. The pale shape in the portal is actual sky/cloud beyond the unfinished rear arrival; the close portal image does not establish an occluding white block.

The next source revision responds to those images with changes of form and use:

- Broad native Macaw resizable glazed windows, projecting dressed heads/sills, lodge shutters and flower boxes.
- An inhabited projecting archive window bay and a smaller, connected west correspondence turret, with stepped buttresses and distinct lower massing.
- Full annular tower soffits and gable wall-to-roof infill, fixing the specific source gap while preserving room headroom.
- Tall bookcase banks, writing tables, a native Dawn of Time fireplace, woven rugs, curtains, window seats, domestic beds and cupboards.
- A real balcony door, cleared lane/stoops, a connected rear rose court, reflecting basin and rear garden stair.
- A cloister whose columns stand beside its walk, with capital pieces, actual arches, urns and planted seating pockets.

This revision retains every first-draft target explicitly: 23,005 are unchanged, 873 change state and 15,419 targets are newly authored, for39,297 total. Bounds become X1177..1244,Z−1037..−962 at the same origin/elevation. Foundations and explicit air-clearance account for much of the additional geometry; the count is not a quality score. Actual-registry construction and architectural material rules pass. One focused regression was added for the observed roof gap and missing balcony/library use.

The parent placed immutable r2 (`90670e8f632ae758f7299f0f36d27aab70a6ef30647fae942a7bc55d5b62a005`) after native comparison of the new15,419 before-states and explicit handling of owned furniture. Actual `castle-west.png`, `castle-roof-collar.png` and `castle-court.png` were reviewed. Projecting room masses, broad glazing, buttresses and the arched cloister read clearly; the continuous roof daylight gap is gone. The tall west base still needs terracing and planting. The first archive capture aimed into a near wall and does not establish interior quality. A corrected camera was provided. These observations permit further iteration, not final acceptance.

An optional `--previous-plan` argument binds an immutable same-world staging predecessor by hash, records changed/new/unchanged custody and refuses silent target omissions. Its `revision-cells.json` records every XYZ, previous planned state or null, and proposed state. **Null means unknown native state**, never air or clearance. Native before-state admission remains the parent's responsibility.

## Connected palace proposal, source frozen at 08:00 UTC

The next immutable staging proposal is `prototype-castle-palace-0f6400ccac0525b5/prototype.json`, SHA256 `0f6400ccac0525b56c5f2c567369c8fcace513510885c63e4beb6304ef28fc95`. It binds the current verified stopped staging backup (`bffb38eb32e2ea551faded81143731ede0609eae1695d07ee81307253c184383`) and source `74df77bb20e3b4182df2210cf1ddafa9fbbf144d7e5a21f8df4f0d0052a26d04`. Its106,610 targets spanX1173..1291,Z−1046..−962,Y64..132. Output is8,166,367 bytes, including the explicit revision-cell ledger.

The architecture adds an octagonal four-level royal structure and spire above a lower grand-stair rotunda, a broken north guest wing, an eastern kitchen/service/dining wing, and a lower ballroom with its own projecting music bay. A narrow two-level glazed artifact gallery connects the formal masses. Differing heights, polygon footprints, broad dressed window bays and actual connections shape the silhouette. It is a connected composition rather than one enlarged rectangular shell.

The furnishings and circulation are designed together:

- Twin audience seats, reception desks, woven runner, writing and conversation areas in the formal hall.
- Royal gallery with books, piano and globe; a private canopied couple suite with wardrobes, study, fireplace, seating and contained bath; a higher chart/observatory floor with workstations and window seats.
- A ballroom dance floor, guarded overlooking gallery, music stage with native piano, chandeliers, conversation groups and flower urns.
- Laid formal dining table, household salon, native stove/cooking pot, counters, sink, smoker, furnace, pantry, utility stations and an accessible cooler cellar.
- Two differently arranged guest rooms, household craft/guard rooms, quiet candle chamber, and a small correspondence study behind an ordinary operable cottage door and tied drape. No custom secret-door mechanism is claimed.
- A framed glass winter garden, guarded royal viewing balcony, lower rose court with actual stairs, and a stepped western garden that addresses the visibly high archive plinth.

The package retains every r2 target:39,267 unchanged,30 deliberate masonry/water/leaf changes,67,313 new,zero omissions. None of the30 altered predecessor targets is furniture or an inventory. The ledger has106,610 rows and SHA256 `e399bf418ad42308447d4499e88c76d6609b74e188f54e6659412cf4c908af4f`. New native targets still need fresh before-state and dry-site admission; no existing block entity may be erased by treating unknown space as air.

Actual-registry assembly passes. The full authored source—including gardens, paving, retaining foundations and all existing approach geometry—passes the stricter building material rule, which also enforces the outdoor maximum nine-block run. Ten focused tests pass. A source graph reaches15 representative room/garden destinations by ordinary steps with two-cell headroom, allowing operable doors and thin carpets. This caught and repaired a window sill obstructing the hidden study and a reversed clearance range obstructing the royal balcony. Guard regressions cover the ballroom void and terrace edges. This discrete graph is **not native collision-shape or player traversal proof**.

The proposal has not yet been placed or visually reviewed. Native before/place/after, actual façade and roof views, furnished-room captures, safe traversal, nearby terrain seating, nighttime atmosphere, fairy-garden continuity, wall-art details and the full cinematic presentation remain review obligations. No source count or named room proves those acceptance requirements.

At08:15 UTC both proposals were rebound to a newer complete stopped checkpoint, SHA256 `d4758fcab5ba0214bd9ae94e2ccf8e262f30d8f61589a4134faadd51b262cdab`. The original exports remain intact. The rebind compares exact palettes, block arrays, bounds, commands, block-entity arrays, landmarks and world identity; it changes only checkpoint/time binding and dependent payload/ledger hashes. Each new manifest preserves the original export and source digests under `checkpoint_rebind`.

| Exact proposal | New checkpoint-bound payload SHA256 | Revision ledger SHA256 |
| --- | --- | --- |
| Palace,106,610 targets | `40e4818d3d5d306ebf294da6d602da014992fa105673d242ca2beb871a2851bb` | `a16cb5456d5d546706868eb2c3289b250ac5f83a73b266fc619c852bf68685c8` |
| Bridge detail,14,829 targets | `0717e69037c47780426246e3ac9bb3ae6c62ea18e0872b2d161dc03aa1074961` | `c68e7728c134c6fb0c491078fcd8fd5b14e4d7bf94534d346ef5d571b6d0a5d4` |

These newer bindings are also staging proposals; rebinding is not placement, terrain admission or visual acceptance.

The parent's exact stopped-checkpoint dry scan admits1,416 new shell-wing columns, with groundY60..65 and no natural water. Separate read-only inspection covers all2,636 newly authored lowest-base columns, including the royal structure, rotunda and landscape:55,356 saved states acrossY60..80 contain no water/lava. The exported footprint metadata currently lists the five `palace_shell` wings but omits `palace_spire` and some outdoor bases; that metadata requires completion. The narrower five-wing receipt must not be presented as complete footprint coverage by itself.

The same saved inspection found real support gaps belowY64. A small separate underpinning proposal (`20ea35194857e417b537907ff8fa7678cf3765efe365efe08da2e8cc40baf9de`) fills369 exact cells in181 affected columns atY61..63, boundsX1235..1262,Z−1037..−1015. It stops at the first actual solid ground and preserves copper and other ore. Before-states are336 air cells,28 grass sprouts,one tall grass andfour short grass; no block entity or existing palace target is changed. Whole-palace material rules also pass with this additional support. The47KB bundle includes its exact saved-state `before.json` (`97795d15138226c400240ad523095816deb322478de79aedd6817ba437195921`), source/input provenance and per-column ground records. It binds checkpoint `d4758f…` and palace `40e481…`. Native before/place/after remains required. It is a correction of measured pockets, not a blanket foundation fill or a new artistic acceptance claim.

## Real palace r1 review and bounded r2 correction

Eight actual staging-client palace images were reviewed after08:28 UTC. The connected silhouette and roof masses are substantially more legible than the rejected old castle. The suite's native bed/fireplace and the western terraced garden are promising. Those images also reveal specific failures: blind ballroom/service faces despite the intended glazing, a guest roof strip entering the royal bedroom, the music bay's back gable hanging into the ballroom, a sparse grey audience hall, and an underfurnished kitchen. The staircase camera points too steeply into the flight's underside to establish the intended circulation. These are observed defects, not accepted visual results.

The next source revision restores the inhabited host envelopes where lower roofs overlap, while retaining the external attached masses. It relocates the misaligned glazing to actual outer polygon boundaries and explicitly restores/clears every old glass/head/sill target. The music room gains a framed native-column portal. The material-compliant garden floor now continues below projecting window hoods instead of disappearing where an overhead ornament was mistaken for an occupied room.

The interior work adds warm wall panelling and drapes, native banners and wall lighting, twin throne canopies with statuary, guarded-gallery pier detail, illuminated pantry shelves and vessels, and a lower-pitch stair camera. Differing gable accents and one actual roof-light break the broad roof planes. The glass winter garden, royal structure, rotunda and outdoor terraces also now have explicit footprint metadata. This adds detail within the existing room programme, rather than inflating the room count.

Actual-registry construction, full-source material rules and12 focused source tests pass. The correction retains all106,610 r1 targets:1,319 change,203 are new and none are omitted, giving106,813 total. A regression targets the two observed roof intrusions and blind window planes. Native comparison, placement and fresh actual interior/exterior images are still required for this revision; it has no artistic acceptance yet.

The r2 bundle now binds the complete stopped checkpoint `5269d2c42eb80d6ae70250080c0130bdf9eda1e0c812e9cd8ab33d8a4858c4cb`, which the parent reports contains palace r1, its369 underpins and bridge detail. Its full payload is `8d5d80fe380a46bd99cfd4e24d91d9c2c64bc99de4ca8e9aa2c9057858e27841`, source `7d135139388b2cdf757a83d57a0fc02faf697ebb3525959cc95628edfd784fab`, and full revision ledger `5d2cb4a27a833b1e06494de105227dc5e65ee76ae6ea75bfe11f0ea232029550`. A35KB `delta.json` (`ebb6fdaef620a92d7772a5fd454c82cc875a7ae733711753e732085b777cae5f`) reissues only the1,522 changed/new targets. It changes no existing furniture/inventory target; exact current native preimage comparison still precedes placement. The unchanged105,291 targets remain part of the full source, rather than being treated as absent.

The full source also passes the material rules when merged with the369 separate underpinning blocks. Only four newly addressed r2 foundation columns extend beyond the r1 target set, and authenticated saved state has real dirt immediately beneath each atY63. No further underpinning is required for those four. The one roof-light sill extends the maximumX bound to1292; it creates no room or ground footprint. R2 remains pending real-image review.

## Final bounded room detail, source freeze09:17 UTC

The parent placed r2 and six actual client images under `art-r2-0900` were reviewed. The newly exposed exterior glazing, corrected royal room, visible panelling and connected roof masses are real improvements. The hall's left face, ballroom margins and kitchen still look sparse. The staircase image is too close to a flight for a useful full composition, despite the improved angle. A camera at the western entrance was supplied without changing the stairs.

The final source correction restores the lower host room envelope as well as the upper floors: an attached-wing wall was still inside the audience hall and occluded its real glazing. It keeps the original chairs but adds visible upholstered throne backs, mounted textiles and grouped reception seating. The ballroom gains a framed parquet dance floor, a served refreshment table and a window seat around a deliberately open central dance rectangle. Its clerestory backing is actually opened, with hanging velvet fields to frame the music end. The kitchen gains a reachable preparation island, cutting board, served feast, plates, berry jars and coherent produce storage using the installed Farmer's Delight/Handcrafted blocks. Existing storage furniture, jars, stove and sink are retained. A short masonry apron supports the roof-light glazing; no new footprint or room is added.

The immutable full bundle `631808ef0dbdcba93f40331467a1f41ac182994fd6301508ef982d8fed743864` contains106,827 targets, with source `1ed4e53ade564a4e78ea8549770c43a72f53b67968a2657cdfa02b696fc97cc4`. It binds the newer complete stopped checkpoint `17105d30def8cb059b27a8b31d1fd114cf077c5b87458f063a84c5630917c44c` and r2 predecessor `8d5d80…`. Its12KB operational `delta.json` has SHA256 `674da43d30e08d1b8deae45d81729e60e419a1539a768ed3212c42636879a63a`:495 existing targets change,14 are new,zero are omitted and no existing furniture/inventory target changes. The full revision ledger is `bbdd7e893379052bd9ea1b70b1d1d0ccef045e63d5c66674c4b442059637591d`.

Thirteen focused source tests pass, including clear real window reveals, the unblocked central dance area, original native seats, reachable worktop props and supported dormer glazing. Actual-registry construction and the whole-source material rules, including the separate underpins, pass. The final delta is staged for the parent's exact native comparison and visual review. Further expansion is frozen; those source results do not claim final artistic or player acceptance.

One final support correction adds two attached piers behind four existing wall mounts. Two r2 banners and two lamps were placed one block too far inside the north ballroom wall, leaving air behind them. The18-block correction supplies actual support, outside the entry opening, without replacing any decorative block entity. Its exact archived before-state is18 air cells. The canonical full payload becomes `e6ffcde57520b8cb75798548ce6f8683f147c8b47f05d5bc3c9be46746159931`, source `dafcf1bf7d1dd6899d19e44bb6a40b3cb1986e31ff890cd970f93de50cfd9928`, at the same17105d… checkpoint. Counts and bounds stay106,827 and unchanged.

The parent can use `mount-support-delta.json` (`977fe1610e28e320cb75ca51a08d20f98f2b658e40bb95c07646c1bfa8db3aae`) after the509-target detail delta, with exact `mount-support-before.json` (`b364d55af6fdb67be03c586354ae25524b8f2eaba36e52760c5de86fb651c707`). Alternatively, `combined-final-delta.json` (`99cf7c97a2ab1ea1fce07d83f584e3a46380f74f905ea825d27a8ff9447d2bc1`) includes all527 changes relative to r2. These alternatives are not both applied. Existing inventory furniture and decorative block entities are preserved, whole-source rules and13 focused checks pass, and final native/visual admission remains the parent's gate. Source expansion is frozen.

## Original reference principles

The [Royal Château of Amboise's cavalry towers](https://www.chateau-amboise.com/en/les-tours-cavalieres-du-chateau-royal-damboise/) informed the idea of a deliberate arrival and useful tower circulation. [Pont Valentré](https://www.cahorsvalleedulot.com/en/explorer/visitez-la-vallee-du-lot/une-journee-a-cahors/pont-valentre/) informed legible spans, cutwaters and coherent approaches. No reference build, schematic, texture or third-party authored structure is copied.
