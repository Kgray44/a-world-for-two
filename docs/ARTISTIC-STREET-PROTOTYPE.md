# Signal Lane: first waterfront prototype

This is one new, authored street for **private staging visual review**. The previous settlement failed the owner's artistic review. Its successful block and inventory checks do not qualify its appearance. Signal Lane does not import those builders or copy their house geometry.

The ten small frontages turn around a five-block winding lane. Two- to four-storey buildings have cropped corners, timber jetties, bays and short intersecting roof sections. A three-block covered passage leads through Needle Court House into a planted courtyard and a separate return alley. Individual shops include a chandler, sailmaker, tavern, fishmonger, harbor office, bookbinder, apothecary, cooper, sailors' lodging and painter's home. Twenty-nine floor programs have real doors, stairs, storage, workstations and living furniture. These are planned useful rooms, not a claim that a player has walked them yet.

The composition uses actual registered Macaw's Windows, Doors and Roofs, Handcrafted furniture and Farmer's Delight fittings. Dark timber, pale plaster, restrained colored terracotta, shutters, trade signs and short awnings distinguish the frontages. Joists, sill courses, panels, stone joints and roof additions supply deliberate architectural material breaks. The shared strict checker applies to each entire building, including its floors, roof and chimney: no uninterrupted material run above nine, and only one axis per material may exceed three. Facing changes do not count as different materials.

The broad plaza and oversized plain buildings visible in the actual baseline captures are the problems this prototype must correct. The next work is to inspect real street-level screenshots, adjust massing and roof junctions, then spend further passes on hanging signs, lamps, workshop clutter, garden corners and inhabited interiors. Geometry counts and material compliance cannot replace that visual review.

The first real staging captures (`after-r1/street-west.png`, `inn-bend.png`, and `quay-frontage.png`) were inspected. They demonstrate the narrower, enclosed street, but the west end is too roofed-in, rear windows read as slits, bright stone corner keys look isolated, and bare grass interrupts the shop thresholds. R1 remains artistically unaccepted.

`tools/artistic_street_details.py` prepares a separate screenshot-driven R2 **delta** against the exact immutable R1 plan. It recesses the two worst opposing upper projections, uses wider real Macaw glazing, adds projecting trade displays, warm joint keys, planted sills, thinner fabric awnings, hanging signs and local lantern pools. A side balcony and courtyard tea corner supply quiet discoveries off the lane. It preserves every existing stocked/sign block entity and serializes only changed positions and new signs. It checks the complete resulting buildings, existing route headroom and a two-block-wide lane. The R2 appearance, lighting and walking must then be captured and judged in Minecraft; these changes are not visual acceptance.

Real R2 captures were also inspected, alongside the R1 chandler interior and covered passage. The shopfronts and paving improved, but thick jetty undersides still dominate the lane. The chandler's single table and barrels and the largely empty covered passage do not establish a lived-in town. The named R2 capture poses differ from R1; they must not be presented as matched before/after pairs.

`tools/artistic_street_life.py` is a separate R2→R3 detail delta. It thins exposed jetty floors to top slabs and upturned cornices while retaining floor height and full support nodes above hanging fixtures. Its individually authored room groups include lamp repair and rope displays, canvas cutting and a loom, a small tavern bar and dining wing, bookbinding shelves, herbal ingredients, fish displays, navigation tools, a painter's desk, household kitchens and crew linen. The cooper's side bay and small cart lead into a planted tea court while leaving a two-wide passage. These are specific furniture and trade compositions, not a general-purpose random room filler.

Filled Supplementaries shelves and compact flower boxes use the actual pinned `ItemDisplayTile` inventory path: one shelf slot and three flower-box slots, loaded through vanilla `ContainerHelper`. The exact Supplementaries and Moonlight JAR hashes are admission inputs. This was verified by bounded read-only inspection of those actual classes; native rendering and interaction remain separate gates. Existing inventory/sign positions, including containers without authored NBT, are protected. Only new display/storage BEs are emitted, with a hard budget of 64. No entities or running machines are added.

R3 checks the complete resulting buildings, preserved stair and door routes, twelve furniture standing spots, the two-wide lane and courtyard passage, and complete bed pairs. These checks cannot establish atmosphere. Genuine street, trade-room, alley, court and evening screenshots are still required, followed by corrections to whatever remains weak.

## Site and preparation

Default local origin is **(1224,65,-1264)**; positive Z runs inland. The 60 by 44 footprint was chosen from the preconstruction native survey's land samples. Fine shoreline/terrain confirmation remains a placement gate. The earlier proposed port site was in the river and is explicitly abandoned. The generator places no blocks at negative local Z and creates no artificial water strip.

Preparation requires a staging-only native registry and the parent's actual reviewed staging backup SHA. It emits a fresh uniquely named plan and manifest under `D:/A World for Two/staging/`; it never calls an API, edits MCA files, starts Minecraft, spawns entities or writes generic `plan.json`. It refuses an official-world registry. The explicit clearing prism is local X0–59, Z0–43, above the authored floor through Y27. The modest foundation reaches four blocks down. This clearing is authorized only for the private clean-terrain prototype, not for a permanent inhabited world.

```powershell
python -B -m tools.artistic_street --registry '<staging>/dashboard/settlement/registry.json' --output 'D:/A World for Two/staging/<NEW-private-folder>' --backup-sha256 '<actual-reviewed-backup-SHA>' --origin 1224 65 -1264
```

The emitted manifest records exact plan/source/registry hashes, rooms, routes, stock/sign block entities, actual mod IDs and capture positions. The finite output bound is 16 MiB, checked through ReserveGuard before any bundle writes. This monitoring rule does not constrain unrelated external writers. Placement remains a separate parent-owned native operation.

## Review views and current proof

| View | Player feet | Look toward |
| --- | --- | --- |
| West lane | 1224.5,66,-1241.5 | 1247,70,-1246 |
| Inn bend | 1248.5,66,-1244.5 | 1256,71,-1245 |
| Covered alley | 1252.5,66,-1235.5 | 1253,68,-1227 |
| Quay frontage | 1254.5,66,-1261.5 | 1252,73,-1250 |
| East lane | 1281.5,67,-1239.5 | 1260,70,-1243 |
| Roof silhouette | 1255,89,-1266 | 1255,73,-1242 |

Source preparation was checked in memory against the actual staging native palette: 84,480 planned placements, 30 stocked/sign block entities, ten building material-rule passes and unobstructed reserved body cells. A graph search checks each ground-floor door's connection to the stair circulation strip. Focused tests also reject missing mod fittings, obstructed entrances and material-rule violations. Their small fixture contains only the used native block properties and stock item IDs, with fictional world bindings; no actual seed or world path is published.

**Pending:** fine terrain confirmation, native placement and complete block verification, real walking and interaction, street/interior/roof screenshots with the actual modpack, two or more detail iterations, and artistic review. No beauty, owner acceptance, complete town reconstruction or performance acceptance is claimed.

## Primary design references

The narrow varied waterfront fronts of [Honfleur's Vieux Bassin](https://www.ot-honfleur.fr/en/site-culturel/le-vieux-bassin/) and the artisan street linking [Dinan and its harbor](https://www.mairie-dinan.com/visiter-dinan/) informed the scale and circulation. These are architectural references; no third-party Minecraft build, downloaded schematic or image asset is included.
