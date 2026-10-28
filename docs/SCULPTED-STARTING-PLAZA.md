# The starting plaza and crowned cascade fountain

This original proposal makes the fountain the arrival's focal point. It uses the
actual stopped candidate41 world, not the obsolete original plaza screenshot.
That former paved square and fountain are gone: the current site is dry, stepped
natural ground north of the new cottage/craft neighborhoods. The core around
1138,−1127 has native soil atY64 and63. Registered spawn is1120,67,−1130, above
soilY65; a compact raised arrival supports that existing landing without moving
spawn or flattening the whole district.

`tools.artistic_spawn_plaza` authors separate private geometry, exact saved
preimage, hydraulic contract and forest reservation. It never mutates a world,
starts a runtime, spawns an entity, seeds an inventory or invents machine NBT.

## Architectural composition

The octagonal reflecting basin has a sealed masonry floor, shaped lower rim and
proud undercut coping. True stair coves and half-depth copper ledges shape the
central plinth; they are not four identically sized cubes with texture swaps.
Four scroll corbels support a small diamond bowl. Narrow rills divide its water
into four gravity cascades. Engaged limestone supports, projecting carved
guardians and a paired sculptural crest give the fountain a layered silhouette.
The enclosed header and its feed are incorporated into that crown.

The second composition uses actual modded architectural models in visible roles:
Dawn of Time marble edge moldings and recessed coffer slabs; Mythrais scrolls,
cloverleaf capitals and a projecting lancet crown; Rechiseled bordered coping and
cut pedestals; Chipped inlaid paving bosses; carved gargoyles and Supplementaries
crest figures; Macaw framed service glazing, golden candle branches and warm
garden lamps; and Handcrafted seating, cups and a small gilded offering bowl.
Their purpose follows the same pale carved stone and aged-metal language. The
service feed remains on the far side of the arrival rather than becoming a tall
industrial display in front of the sculpture.

Installed model inspection established that the cloverleaf capital is24pixels
wide, including a quarter-block overhang each side. The selected lancet crown
extends about29pixels wide and26pixels high; it belongs high on the dry display
face, not in a pedestrian doorway or across the water port. The wide golden bowl
is only8pixels tall, and the marble urn projects slightly above one block.
Upward-facing fancy iron lanterns remain within their16pixel height; their wall
variant has a different, taller profile. The crest figures now have actual solid
coping beneath them, clear of the feed pipe. These source/model readings still
require actual native views and collision inspection.

Warm pale stone, restrained copper joints and weathered metal connect the new
feature to the town. Three-wide paving panels meet small inlaid crossing bosses;
their actual joints satisfy the material rules without random recoloring. An
arrival view opens onto the sculpture, while two paired-bench pockets, cups,
tables, planted urns and low warm fixtures sit outside the walking line. A
framed, copper-hooded wheel niche stays on the service side of the composition.
The public promenade and new path use actual dry gaps beside the retained
neighborhood clearing, rather than treating an interior floor as a public route.

The complete fountain, plaza, machinery and foundations participate in the
three/nine material rule. Different facings of one material do not provide
breaks. The outdoor nine-block cap is also checked. These checks establish the
proposal's geometry constraints; they do not prove artistic quality.

## Real pump feed and ordinary shutoff

The installed Create1.21.1–6.0.10 JAR is pinned by SHA256
`ef87fe5709f1ba1f5b8bb20a2925b5afb4669e178fd6d8bf10c167759eefe37a`.
Its actual bytecode and installed config were inspected. The generic upstream
[mechanical-pump documentation](https://github.com/Creators-of-Create/Create/wiki/Mechanical-Pump)
describes the basic pipe/pump arrangement, but its old15-block figure is not used
as this pin's setting: the installed config and class default specify16. Its
[fluid config source](https://github.com/Creators-of-Create/Create/blob/mc1.21.1/dev/src/main/java/com/simibubi/create/infrastructure/config/CFluids.java)
also documents open-pipe source placement. Current native behavior remains a
separate test; an older wiki is not substituted for the installed code.

The real pump draws from the lower basin, through one intake, and supplies one
initially dry elevated header. A small cog meshes with the pump's actualX-axis
gear and connects to the contained waterwheel through normal shafts and a clutch.
The output route is within the pinned pump range. Glass joints make the feed
inspectable. The wheel has one independent, contained gravity supply; it cannot
fill the higher header by gravity or an unrecorded alternative path.
In this exact pin the pump's front is its FACING property and its back pulls;
the bytecode does not reverse that front/back rule with speed sign. The east-facing
pump therefore draws west and pushes east for either nonzero rotation sign. The
one cog mesh and actual flow still need native observation; synthetic tests do
not establish an8RPM result or successful transfer.

The architecture deliberately places **AIR at both the elevated header and wheel
feed source**. Only the reflecting pool is initially water. A parent-owned native
commissioning step may seed the one approved independent wheel source after
proving the header and upper jets dry and the machines stationary. It must then
observe normal wheel/pump rotation and actual water arriving in the header.
No kinetic speed, pressure, flow or fluid NBT is preloaded.

The pinned `OpenEndedPipe.provideFluidToSpace` refuses a target that is already a
source. Once the enclosed header is full, the pump therefore legitimately reaches
backpressure; a spinning pump is not evidence of continuous fluid transfer. The
visible streams thereafter use ordinary gravity. This finite fill/refill behavior
is intentional and must be described honestly.

A real sticky piston moves one stone plug into the header's single outlet,
without replacing the source itself. The accessible STOP lever operates an
ordinary six-torch riser and repeater. Lever powered means outlet closed. The
upper bowl has one-wide arms and no seeded upper sources; closing the outlet
must let the downstream nonsource water drain. The lower reflecting pool remains
filled. Reopening the outlet must restart the actual cascades. The source does
not pretend that closing a pump alone removes an already placed water source.

The inspected Create fluid valve is driven by rotation direction and its animated
mechanical position. It is not a simple redstone-powered valve switch. This
proposal uses the straightforward physical piston gate instead of adding an
unnecessary reversible valve drive or dispensing bucket inventory.

## Exact controls and native gates

| Component | Position |
| --- | --- |
| Reflecting pool | Center1138,−1127, floorY64, waterY65 |
| Pump, facing east | 1140,66,−1129 |
| Intake world water | 1139,65,−1129 |
| Output inspection riser | X1142, Y67–74, Z−1129 |
| Header open pipe, downward | 1138,74,−1129 |
| Elevated header, initially AIR | 1138,73,−1129 |
| Sole commission-only wheel source, initially AIR | 1145,69,−1131 |
| Waterwheel, facing west | 1145,66,−1130 |
| Sticky piston, facing north | 1138,73,−1126 |
| Retracted plug | 1138,73,−1127 |
| Closed plug / outlet | 1138,73,−1128 |
| Ground-accessible STOP lever, east wall face | 1142,66,−1125 |
| Four falling-jet witnesses, allY68 | 1135,−1128;1141,−1128;1138,−1131;1138,−1125 |

Before placement, verify the complete saved preimage against the current owned
world and protect every actual BE and neighboring authored solid/AIR cell. Place
only this bounded new geometry. Perform normal joining and strict complete
readback, retaining any failed receipt. If derived pipe/wire/model states differ,
investigate exact native rules; do not relax critical-state checks.

Commissioning must observe real pumped startup, stable actual header and jets,
normal STOP plug movement, complete downstream drain, START restart, a repeat
cycle and server restart persistence. Reject accidental upper infinite-source
formation or leaking water. No inventory replay, forced chunks, entity seeding,
scripted particles or fake player is part of the design.

Eight actual-game camera poses are declared for arrival, four eye-level sides,
wheel service, the crown and night arrival. Review the sculptural silhouette,
coping/column model joins, all four cascades, warm night lighting, comfortable
seating and walking. Check that the service mechanism does not dominate the
arrival and that no flat plain basin or monotonous field has slipped through.
No source count or synthetic test qualifies those artistic gates.

The private forest reservation includes all new construction, explicit body and
headroom, hydraulics and the framed arrival sightline. It is construction-forbidden
and must be incorporated before the final forest binding. Preserve its exact
hash and five-metre planting buffer; plants in ornamental urns are construction
details, while later habitat/LIFE seeding remains a separate final pass.

## Preparing the actual native commissioning request

`tools.artistic_fountain_commission` admits only the exact candidate42,
bridge0.6.28 installed JAR/class, private25575 artistic home, retained checkpoint
and frozen complete2532-cell R5 geometry. Its required input is the **actual**
successful server verification receipt and matching `.complete` hash marker.
Placement receipts, partial counts, any failures, outstanding tickets/futures,
cleanup requirements, foreign/reparse paths, stale/future times and mismatched
owner/installed hashes are refused before request creation. The proof must be
less than30minutes old and belong to this server's settlement journal.

```powershell
python -B -m tools.artistic_fountain_commission --native-verify '<exact actual owned settlement-result UUID.json>'
```

It emits a new content-addressed `dashboard/settlement/fountain-<hash16>` directory
containing only `request.json` and a sealed ownership receipt. It refuses to
overwrite or recreate an existing request. The returned typed console command
is for the parent controller to serialize after its other maintenance work.
The producer itself never invokes inspect/commission, seeds water, changes a
lever, installs code, writes a world or claims hydraulic/artistic acceptance.

The first actual R2 commissioning seeded only its independent wheel supply and
finished with zero wheel/pump RPM and no header or jet water. Its failure and
cleanup receipts remain intact. Native inspection found falling water on both
north and south wheel faces, plus water above the wheel. The source had an open
south face beside the feed; opposing flow cancellation is the bounded hypothesis.
The R3 intervention closes only that source-side opening with a full modded
carved keystone supported between the existing sidewalls. It sits above the
wheel's physical envelope. No scenery, plumbing endpoint or control position moves.

The recovery delta has exactly three targets: remove the owned independent water
source, add that one full baffle, and set the ordinary STOP lever false. It never
writes piston extension, the moving plug, flow/kinetic NBT or fluid elsewhere.
Normal updates must drain the niche and retract the piston; independently inspect
dry source, retracted piston, returned plug and clear outlet before a fresh full
R3 verification. Only that actual successful verification can admit a new request.
The new causal result, pump fill, gate cycle and visual acceptance remain separate
native gates; the source fix and focused test do not establish them.

The actual R3 run subsequently measured wheel−8RPM, pump+8RPM, an actual filled
header and all four streams, without overstress. Its STOP phase failed and that
partial result remains recorded. Installed Minecraft1.21.1 `DiodeBlock` bytecode
shows that a repeater reads input from `pos.relative(FACING)`: the authored NORTH
repeater faced its input toward the piston. R4 changes only that state property
to SOUTH, so it reads the southern dust and outputs north. No architecture,
material or position changes with that correction. The complete native gate
cycle still requires a fresh dry R4 verification and actual test.

The actual42 visual review subsequently required a separate sculptural recovery.
See [Guardian fountain recovery](FOUNTAIN-CENTERPIECE-RECOVERY.md) for the R5
statue, backed one-wide bowls, concealed side feed, explicit wet/dry evidence
boundary and current native/visual gates. The coordinates in the earlier table
describe the retained R2–R4 prototype; R5 removes its tall overhead inspection
riser and instead enters the unchanged header from the east.
