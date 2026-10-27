# Bramble Lane: south-bank craft district prototype

Bramble Lane is a compact, individually authored connection between Rose & Lantern Court and the existing bascule stair. Six small buildings lean into bends in a three-wide lane: a leather repair shop, tall luthier, potter, glazier, open provision loggia and a shared mason/carpenter workshop. Their cropped corners, side wings, projecting window bay, different floor levels and short intersecting roof sections are drawn separately. They are not clone-stamped house boxes.

| Place | Ground floor | Room story |
| --- | --- | --- |
| Bramble & Buckle | Y67 | Fitted leather/shears/boot displays, repair benches and a fitting seat; household above |
| Wren & Reed | Y66 | Actual playable lute, string and wood samples, repair bench, practice seat, supper room and sleeping loft |
| Clay & Candle | Y65 | Clay worktops, real furnace, water, modelled pottery and material displays; bedroom above |
| Copper & Glass | Y66 | Glass/copper/lantern displays, real furnace, fitted bench and a little home |
| The Clover Pantry | Y67 | Open produce counter, actual food displays, pantry, working stove and family apartment |
| The Stoneleaf Workshop | Y66 | Real stonecutter, two-part Chipped mason table, tools, sample bench and side lean-to |

The native land profile is dry at ground Y63–66. Taller sampled readings near the eastern edge are existing bridge masonry; the cherry trunk over ground66 is vegetation, not a hill. The new buildings stay west of X1179 and south of Z−1120. Only building foundations, roof vegetation clearances, a finite native-tree envelope and supported paths are authored. There is no district-wide stone plinth, channel filling or whole-hill flattening.

Two small cloth awnings, actual pottery/crop objects, trade signs, flower boxes, a compact modelled wheelbarrow and lighted side pockets begin the outdoor detail. Compact hanging lanterns have explicit supports; the low rooms avoid the oversized chandelier seen in the earlier cottage capture. Real shelves use the inspected pinned Moonlight inventory codec and contain actual named items. No NPCs, ships, decorative armor stands or ambient entities are spawned, and no powered factory or automation is claimed.

The exact existing cottage and both bridge plans are exclusion masks, including their air and inventories. The sole authorized exception is a finite two-wide cottage connector: it begins beside the retained paving at X1129 and curves through X1130–1135 toward X1136,Z−1096. Only 57 old clearance-air cells are changed; no cottage solid, lamp, furnishing or block entity is replayed. The lane ends beside the existing stair at X1188,Z−1093/−1094, floor66. This avoids the lower floor64 landing farther south and preserves the whole original bridge.

`tools/artistic_craft_lane.py` requires a complete zero-failure native land survey, exact private staging registry, all three exclusion plans, the current reviewed backup SHA and a new D: staging folder. A finite 16 MiB ReserveGuard admission bounds output. It writes only a plan and private manifest; it cannot operate the server or world. The monitoring rule does not constrain external writers.

Source checks cover six complete-building material rules, the nine-block cap across all authored geometry, exact exclusion masks, five complete beds, 12 furnished room connections and a continuous cottage-to-stair path. The first prototype is **unverified artistically**. Native screenshots must assess the actual lane bends, door thresholds, roofs, ground joins, furniture scale, shop lighting and density; native walking and real interactions remain separate gates. More lived-in detail follows the first real views rather than being copied across an unseen district.
