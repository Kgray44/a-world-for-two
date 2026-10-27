# Rosewater Castle: the Rose and Tide Palace

The expansion keeps the original castle at its established site. Its keep, four
teal-roofed towers, twin thrones, royal bed, piano, fairy table and waxed entrance
sign remain. The proposal adds a connected palace around that core, with usable
rooms, stairs, sheltered gardens and a more varied skyline. It is an original
Minecraft design for KG and Sera; no downloaded schematic or film asset is used.

This document describes a **design generator**, not a finished or visually
accepted castle. Native installation, room-by-room play, shader review, lighting,
restart persistence, performance measurements and cinematic integration remain
separate required work.

## Composition and terrain

The reviewed world footprint is **x1155–1290, z−1043–−919**, with original keep
floor **Y67**. The permanent settlement, terrain seed and surrounding landmarks
stay in place. The giant tree and cottage lie north of this reserve.

| Part | Position and levels | Purpose |
| --- | --- | --- |
| Preserved keep | Original site around 1211,−1008; Y67/74 | Great hall and throne room; old royal music gallery; real new stair |
| Four original towers | Original corner sites; Y67/73/79/85 | Continuous internal stairs, reading lookouts and small hollowed top rooms |
| Moonlit Library | West wing, x1160–1184; Y67/75 | Double-height book room, hearth, shared reading, upper map and correspondence gallery |
| Scriptorium Cellars | Beneath library, Y61 | Walkable quiet archive and modest stores with a discreet six-step descent |
| Sea Glass Ballroom | Northeast wing, x1240–1272; Y67/75 | Dance floor, playable piano stage, reception, twin staircases and upper viewing galleries |
| Royal Wing | East side, z−994–−958; Y67/75 | Dining, kitchens, pantry, staff room, workshop, royal suite, dressing/study, bath, guest room and curiosities |
| Star and Tide Observatory | East skyline, 1281,−1016; Y67/76/85/94/103 | Connected tower studies and lookout; teal spire reaches Y117 |
| Rose Court | Center south of the old keep, Y67 | A sheltered cloister loop, rose beds, reflection pool and paired seats |
| Lower Conservatory | West gully, Y63 | Glass winter garden, roses, a fairy meeting table and a hidden keepsake chest |
| Chapel of the Two Lanterns | Stable east terrain, Y67 | Quiet reflective room with paired warm lanterns and garden windows |
| Southern Rose Gate | South approach, Y67/75 | Two inhabited gate lodges and an upper portrait promenade |
| Rosewater Gardens | Southern/eastern plateau, Y68 | Sealed mirror pool, parterres, flower vessels, paths and gazebo seating for two |

The fresh survey shows a pronounced western gully. The conservatory steps down
to Y63 instead of filling that gully to courtyard level. Library foundations
follow the surveyed ground, with a genuine lower archive within them. New-wing
foundation admission refuses unsupported survey extrapolation, more than a
17-block drop, or more than a five-block cut before human review. The generator
uses the pre-construction natural survey under the old keep because the fresh
height map correctly sees its roof.

## Materials and detail

The palette is pale calcite, restrained rose accents and dark teal roofs, with
cherry furniture and warm gold lighting. Chipped calcite masonry and floor
inlays, Rechiseled quartz trim, Mythrais buttresses/cornices, Macaw roofs/windows/
doors/curtains/railings/lights, Handcrafted furnishings and Dawn of Time marble
flower vessels give each architectural layer a purpose. Actual registry IDs and
every supplied property are checked; absent IDs are errors rather than invented
substitutes.

The library has a double-height central void and a real surrounding mezzanine.
The ballroom has a separate reception and two real stair flights, a piano stage,
conversation seating and interior balconies. The royal wing uses a central
gallery with purposeful rooms on each side. The old keep retains its original
royal furnishings, while a new staircase makes its upper floor reachable. The
small original towers acquire stairs and usable lookout chambers; their
existing roof silhouettes are retained. The new observatory supplies a taller
and differently proportioned skyline.

The main suite includes a two-wide canopy bed, personal sitting space and a
balcony with two seats. The library has a shared reading couch, and the grounds
include a flower-table gazebo for two. Storage is modest and mostly empty so
KG and Sera can make the castle theirs. The fairy table is an interaction point;
no unverified fairy summoning is claimed.

## Walkable connections and water

Recorded routes describe actual standing positions with a supporting block and
two clear blocks of headroom. The generator checks these **after** furniture and
landscaping are assembled, so a later object cannot silently block a documented
route. Stair flights rise one block per adjacent step. Doors remain ordinary
operable doors. These checks cover the recorded corridors and stairs; they do
not establish that every furniture model, door shape, room or mod interaction
has been accepted in game.

The northern entrance continues to connect the old castle with the village.
West and east bailey passages reach the new library and ballroom. A rear keep
passage reaches the cloister. Service access connects its eastern promenade to
the kitchen. The lower conservatory is reached by an actual four-step descent.
The south gate leads to the raised rose terrace through a single step. The
observatory has a continuous internal stair, rather than inaccessible decorative
floors.

Every water source belongs to a reviewed basin with solid bottom and side walls.
The court pool, private bath and garden mirror have no elevated spilling source.
Containment is checked independently of the route checks. Native fluid updates
still require verification after placement.

## Preservation and output contract

`python -B -m tools.settlement_castle --home "D:\A World for Two"` prepares only
two unique, content-addressed files inside `dashboard/settlement`:

- `rosewater-castle-plan-<sha256>.json`
- `rosewater-castle-manifest-<sha256>.json`

The callable interface is `prepare(home, destination=None)`; `destination` may
select an output directory within the owned settlement directory. It never
writes `plan.json`, runs a server command, replaces a receipt, changes a world,
or installs its own design. The parent workflow must review and admit the exact
plan before native placement.

Admission requires the complete successful native `castle-survey-0.6.5.json`,
actual registry export, current verified full-world backup, the exact immutable
original core and its retained native verification receipt, and pirate-port and
drawbridge master exclusions. Every existing block entity in the old, fresh and
retained earlier surveys remains protected, including underground inventories.
All completed blocks and clearance air outside the original castle remain fixed.
Original castle furniture is fixed even when it has no block entity.

Only the listed, inventory-free original castle masonry, floors, roof blocks,
glazing and clearance air inside the small original castle bounds may be
adapted. Each final change records the exact previous state, replacement and
room/feature reason. No existing BE is changed, retagged or reset. Matching old
blocks are left untouched. The original immutable masters and failed receipts
are preserved.

The native plan is capped at 550,000 positions and 32 MiB. Its plan plus complete
audit manifest is capped at 64 MiB; the live reserve guard runs before either
file is written. There are no entity summons, hostiles, explosives, permanent
chunk tickets, command blocks or continuously operating Create networks in this
castle plan. A few useful stations, light sources and contained hearths provide
function without a large simulation load. Their measured cost remains pending.

## Required review before acceptance

Inspect the intended shader configuration from the village approach, library
gully, court, eastern gardens, observatory and aerial skyline. Review warm
windows at night and the reflection pools at sunset. Walk every room and stair,
check the old bed and inventories, and use the kitchen, library, piano, fairy
table and storage. Refine awkward proportions, roof junctions, dead ends,
clipping, empty surfaces, lighting and landscape transitions based on actual
views. Capture interior and exterior evidence; then integrate the castle reveal
into the actual settlement cinematic. Successful block verification alone does
not establish the owner's requested fairytale quality.
