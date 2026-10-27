# The two requested original buildings

These are adaptations of the owner's exact requested downloads, with attribution
to their original creators. Neither downloaded schematic, source geometry arrays,
private placement plan, world, log nor third-party executable belongs in Git.
The public tools require the original files again; they do not recreate the
creators' buildings from an embedded copy.

| Original | Creator | Exact source file |
| --- | --- | --- |
| [Pirate tavern](https://www.planetminecraft.com/project/pirate-tavern/) | Evgesha765 | `pirate_tavern_evgesha7659618353.schematic`, 8,911 bytes, SHA256 `e73346e4aa01bf9c0cea7a2e4e54b5d6b67f9f6c050b2460e6d9e6afa0301aeb` |
| [Fishermans shop](https://market.phantom-node.com/post/fishermans-shop-m34wn72u) | Shabani1, as credited by the source page; uploader bahs | `fishermans-shop-m34wn72u.litematic`, 4,736 bytes, SHA256 `2a1ecefcdbba55f86480318107dfd396ba7c98d2731711e811b5cdd0e39b5309` |

The tavern page specifically describes its roof as an old ship's hull. The shop
page lists 34 × 28 × 21, 1,779 blocks and no entities; the actual decoded file
agrees. A public download is not treated as a grant to redistribute the original
build or claim its authorship. Keep the named original bytes unchanged in private
custody, with their normal-page download receipts.

## Placement and architectural adaptation

`tools/artistic_imported_builds.py` reads the exact originals and the actual
Minecraft registry. Its output is a new private proposal and exact saved preimage
for each reserved site, not a world edit. The tool never launches Minecraft,
executes commands, places a block, imports scheduled ticks or spawns an entity.

The tavern reservation is X1282–1309, Z−1337–−1297, with no rotation. Its lower
furnished hall, kitchen, bar and double doors are at original Y5–10 above the
broad floor at Y4. Therefore original Y4 binds to world Y64, the accommodation
floor at Y12 binds to world Y72, and the top is Y101. Burying that furnished lower
hall by binding Y12 to street level would discard much of the actual design.
The 4,200 architectural cells retain their exact relative positions, including
the lower hall, stairs, beds, upper accommodation and ship-hull roof silhouette.
Original air, water and unrelated natural terrain are excluded rather than
pasting a rectangular landscape or clearing the whole source volume.

The shop reservation is X1314–1334, Z−1349–−1316, with the complete original
rotated clockwise 90 degrees and its foundation Y0 bound to world Y64. All
1,779 occupied source positions remain. Rotation applies to positions, cardinal
connections, facing, axes and standing rotations; hinge handedness and inner/
outer stair handedness retain their meaning under a proper rotation.

Aligned timber ribs, reinforced/carved Chipped log joints, framed plank panels,
masonry borders and collar courses articulate the original materials. Actual
Macaw framed windows use the original apertures; the shop's upper glazing has a
distinct clerestory frame. This is a named construction treatment, with a full
old/new substitution ledger, not random color noise or a block-facing loophole.
Both complete adapted buildings must satisfy the owner's material-ID rule:
no same-material run longer than nine, and at most one Cartesian axis longer
than three. Actual-ground masonry shoes, where necessary, are included in that
check. Those shoes may bridge only one air block above dry saved soil under real
ground-floor load points. No platform or support column is added under an
overhanging roof. Passing this geometry rule is not an artistic quality score.

Only ordinary trees in the exact reserved rectangles may be cleared. The saved
shop survey contains 47 natural Regions Unexplored willow logs and 490 willow
leaves; the separate retained court willow near X1345, Z−1329 stays outside.
Bee nests, saved block entities, fluids, foreign construction and unknown wood
cause refusal. The X1310–1313 corridor between the reservations stays untouched.

## Exact legacy conversion and harmless furnishing data

`tools/structure_import.py` decodes the 28 × 42 × 41 Alpha schematic as exactly
48,216 cells and 128 distinct numerical states. The native conversion uses the
installed Minecraft 1.21.1 flattening table plus official data migration, with
the actual server runtime classpath recorded by hash. Its successful 128-state
result is pinned separately. The earlier wrong-Guava attempt remains a failed
receipt; it is not reused as evidence.

The native `%%FILTER_ME%%` sentinel is legacy ID144, metadata1: **a floor skull,
not a piston head**. All 21 instances have exact corresponding Skull block
entities. Their SkullType and Rot determine the modern skeleton, wither-skeleton
or player head and rotation. The genuine piston and piston head already have
successful native mappings and retain them. All 14 door pairs combine the lower
half's facing/open values with the upper half's hinge/powered values. Bed halves
must form matching directional pairs. Banner Base and pattern dye values use
the original legacy dye numbering, preserving all 13 banner positions and ten
patterned flags. The stored flower-pot item overrides the global table's
context-free pot placeholder and preserves the original azure bluet.

The 11 custom player heads preserve their exact texture values and UUIDs as
controlled modern literal profiles. Texture JSON is decoded for validation only;
the only admitted texture URL is a normal `textures.minecraft.net/texture/...`
address. The tool does not fetch a skin, authenticate an account or import an
arbitrary external URL. The old, separate `Signature` property is retained in the
unchanged original and identified in the private ledger, rather than injected as
an unrelated modern rendering property. Banner patterns are converted through a
small explicit pattern whitelist. Raw source NBT is never pasted wholesale.

The tavern's other inventories are empty. Its four source decorative entities
(an armored display, a painting and two item frames) remain separately recorded
as deferred furnishing candidates. Their original WorldEdit selection origin
provides their relative positions. No spawn NBT, UUID, plugin state, attributes
or source command is emitted. The legacy potion in a frame requires exact item
migration before a later native furnishing pass. LIFE seeding and any entity
placement remain after construction.

The shop's six unsupported palette entries represent **35 placed shelves**:
31 spruce and four dark oak. They become real Handcrafted shelves at those same
positions and facings, with explicit old/new records. The newer power, water and
side-chain fields must match the inspected dry, unpowered, unconnected source;
this tool does not approximate an active storage network. All 117 source block
entities are empty/default: 61 blank signs, 35 shelves, 11 barrels, six campfires
and four undecorated pots. Their models and positions remain, with native default
furnishings instead of importing a later-version data schema.

## Native and visual gates

Legacy table fence connections and stair shapes are global placeholders, not
observations of the source neighborhood. They are listed explicitly as pending;
critical identity, direction, half, door hinge and chest-pair type remain
specified. New Handcrafted shelf joins likewise require native readback. There
is no fake Level, standalone tag approximation or claim of native connectivity.

The actual sequence is saved-preimage verification, addressed placement, a
bounded normal neighbor-shape pass in the real staging level with loaded block
tags, settling, and exact current-state export. Any lost block, changed critical
orientation, broken support, altered literal furnishing tag or changed inventory
is a failure. The resulting complete state record must get a new strict native
verification before real game/shader views can qualify the appearance and routes.
Synthetic decoding tests and material checks cannot replace those gates.

The original public boundary fixtures cover signed legacy bytes, non-cubic index
order, crossing signed 64-bit palette words, negative Litematic extents, exact
array lengths, invalid palettes, cumulative region limits, overlap, malformed
compressed NBT, invalid state syntax, door/skull/bed context and proper rotation.
Additional synthetic architectural fixtures preserve positions and axes, enforce
the complete material rule, and reject powered future shelves or unsafe profiles.
The small property-schema fixture contains actual exported block schemas only;
it contains no world identity or downloaded structure geometry.
