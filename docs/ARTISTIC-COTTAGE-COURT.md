# Rose & Lantern Court: private cottage prototype

This is a compact, individually authored romantic court for the artistic recovery. The L-shaped couple's cottage has a lower side-wing kitchen, a two-bed upstairs room and a real balcony door. A small honey bakehouse faces the court from the east, a one-storey weaver's cottage closes the south corner, and a leaded-glass potting house sits beyond the pond. Winding two-wide paths connect the entrances, orchard, outdoor kitchen and a quiet two-seat tea corner. It is a new composition rather than a reskin of the rejected settlement templates.

The proposed 42 by 38 site begins at `(1094,67,-1118)`. Original native terrain samples in this area are land at Y65–68. The couple's house floor sits one block above the central court; foundations are limited to the buildings, paths and pond. Other ground follows the surveyed small slope instead of receiving a flat plinth. Parent-owned fine native terrain confirmation is still required before placement. The origin is configurable, but the generator refuses unknown terrain or a larger slope instead of automatically flattening it.

Macaw's real windows, cottage doors, roofs, garden fences and lights combine with Handcrafted furniture, Farmer's Delight kitchens, Supplementaries planters and Chipped leaded greenhouse glazing. Roofs and floors have deliberate joists, panels and short roof sections. Complete building material checks enforce the owner's rule, including facing-independent material identity; no random texture swapping is used to hide broad surfaces.

## Native review handoff

`tools/artistic_cottages.py` writes only a fresh private staging plan and manifest. Its registry must point into staging, and it requires the parent's actual reviewed backup SHA and original native survey. It does not call APIs, start a game, place blocks or spawn entities. A 16 MiB ReserveGuard admission bounds the output. External application writers remain outside that monitoring instruction's coverage.

```powershell
python -B -m tools.artistic_cottages --registry '<staging>/dashboard/settlement/registry.json' --survey '<private-original-survey.json>' --output 'D:/A World for Two/staging/<NEW-cottage-folder>' --backup-sha256 '<actual-reviewed-backup-SHA>'
```

Suggested review feet, using the default origin:

| View | Feet | Look toward |
| --- | --- | --- |
| Garden entry | 1095,68,-1097.5 | 1112,72,-1102 |
| Couple's frontage | 1108,68,-1097 | 1104,73,-1106 |
| Pond and bakehouse | 1119,68,-1089 | 1118,71,-1101 |
| Glasshouse approach | 1122,68,-1095 | 1128,71,-1089 |
| Cottage sitting room | 1102,69,-1106 | 1109,70,-1106 |

The first court was placed in private staging after a fresh 4 m native land survey. The actual court capture is cozier than the rejected settlement, while the actual sitting-room capture still shows a dark, almost empty entrance beside the stairs. Neither image is artistic acceptance.

The separate `tools/artistic_cottage_life.py` delta responds to those captures with a lit modelled Dawn of Time hearth and banded flue, paired seating, book walls, rugs, cupboards, real skillet/bowl displays, pottery, candles, personal bedroom objects, furnished bakehouse and weaving corners, potting workbenches, filled flower boxes, a small actual wheelbarrow and tea/garden objects. It explicitly lights chandeliers and supplies ceiling chains. Stairs and their original solid floorboards stay unchanged. It also corrects both halves of the weaver's bed from the independently derived vanilla head/foot direction rule and introduces masonry cross-drains where inherited gravel and subbase strips exceeded nine blocks.

This is a delta against the exact first cottage plan: existing stocked containers are never replayed. Actual pinned display classes supply the inventory codec; correct native rendering and interaction remain separate checks. Source checks cover all four complete-building material rules, the nine-block cap across authored outdoor geometry, original route clearances, six furnished standing-space connections and four complete beds. They do not prove visual quality, light balance or furniture walking. The new rooms and court still need actual native screenshots and inspection before broader propagation or owner acceptance.

The actual furnished vestibule capture exposed a scale problem: Macaw's nominally small chandelier occupies more than one block in width and depth and dominates the low ceiling close to the camera. The separate `tools/artistic_cottage_lights.py` delta replaces the eight fixtures with compact supported hanging lanterns, retaining every chain, ceiling, stair, piece of furniture and inventory. Actual scale/light review remains pending. The entrance image chiefly shows a vestibule; use a second camera at `(1103,69,-1108)` looking toward `(1098.5,70,-1107)` to inspect the actual hearth and sitting group.
