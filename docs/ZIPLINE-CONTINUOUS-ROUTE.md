# Cliff-to-town zipline: actual API and station proposal

The selected [Ziplines: Rezipped!](https://modrinth.com/mod/ziplines-rezipped)
1.5.3 provides the riding physics. The exact NeoForge1.21.1
[Reconnectible Chains](https://github.com/evanbones/ConnectibleChains)2.4.4 supplies
actual chain knots/links; its binary/source SHA256 values are respectively
`70d9f048e6f358c83b2d35f8a69000ec7827023efcc6d3b75346b4e34238bbd0` and
`56c0c23493571ad43d7e9fc5266cffde1eb15521d9ac7fd2124d97acf32a7eaa`.
These exact private archives and installed bytecode were examined. No copied
third-party JAR, source archive or saved-world geometry belongs in Git.

A single decorative515m chain is not a working ride. The chain mod defaults to
range32 and normally breaks longer loaded links. The zipline client requires
actual tracked endpoint entities, so loading a remote server chunk alone does
not establish a long client cable. Stock ChainCable also inherits an empty
getNext; short links do not automatically become one continuous ride.

The isolated original `compat/proposals/zipline-graph-20261027T2315Z` adapter
uses the public Cable.getNext hook. It follows actual incoming/outgoing links at
the same live shared knot and delegates the pinned ChainCable geometry. Native
ZiplineLogic owns the rider's movement, collision, direction, speed, turn choice
and braking. There are no fake endpoints, custom geometry packets, distance
bias, world writes, terrain loads or idle forced chunks. Spans are bounded to
80m in3D; propose explicit native maxChainRange96 and client render distance≥6.
Prefer actual spans≤48m for the current simulation4: unresolved incoming holders
resolve in the source knot's tick, so a merely tracked80m source after reload is
not enough. A longer choice needs actual proof or a separately bounded real-rider
lease, which is absent from this adapter. No extra idle loading is introduced.

Registration must precede Zipline.init because a later equal-distance provider
loses the native strict comparison. The adjacent proposal README specifies the
optional CLIENT metadata, lazy mod-presence guard and dedicated-server class
loading boundary. The actual binary API probe passed ten checks in each provider
order, including exact native shared endpoint positions, the public handoff hook,
chord turn and1.329m midpoint sag on the~66m/slack16 example. It created no world,
entity or player. Loaded-world graph traversal and riding remain untested.

Native ChainCable uses the3D span length in its catenary evaluation and a+0.4
vertical offset. A fence anchor can obstruct the rider's head with the default
hangOffset2.3. Proposed server-synced hangOffset3.0 keeps the real curve unchanged;
the actual player AABB must be checked at each shared anchor and normal handoff.
Every route segment needs the actual catenary, not only a straight ray. Preserve
river navigation, bridge views, existing canopies and tree roots. The conservative
24m river-clearance planning target is not a measured maximum-vessel claim; flat
bank+8..12m supports that fail it must not be called qualified.

## Compact station architecture

`tools.artistic_zipline_stations` produces original3×5 open rigging pavilions on
the actual saved dry plots. The preferred cliff plot is centered1160,−760 with
base floor160; the selected town plot is1220,−1272 with base floor64. A second
qualified cliff-facing plot1072,−856 can be selected after final route review.
The saved geography proved compact supports and clearance, not walking access.

Each pavilion has rooted small footings, broken carved timber posts, a real
pitched roof and longitudinal ties, underside coffers and knee braces, a bolted
tag-compatible fence anchor, warm Macaw wall lamps, a louvered Macaw casement,
Handcrafted book shelf/books/cup, and a practical equipment locker. A real side
ladder and hatch reach the raised boarding deck while leaving the central
hanging-player corridor clear. The locker is explicitly empty until native
stocking is separately performed and verified. No fictional supplied tools,
entities or ride are counted.

The source enforces the complete material3/9 rule, including floors, footings,
roof and interior; different facing properties are not material breaks. It
refuses saved BEs, trees, terrain or foreign objects at all targets. Private
native preimages and an all-solid/AIR/route reservation mask accompany each
proposal. Endpoint stations remain construction-forbidden until the entire
modest dry-support route, safe exterior access and native creation protocol are
reviewed. A roof or block count is not station artistic acceptance.

## Native creation and completion gates

Use the normal chain APIs with no fake player: first refuse foreign knots and
verify actual anchor/catenary tags, block states, range and route geometry. Then
create only admitted knots and attach the directed real links with explicit
per-link slack. Capture actual native UUIDs and immutable custody immediately.
On restart, find those same UUIDs, saved relative endpoint links, source items,
slack and no duplicates; do not create replacements to hide a persistence gap.
Neither entity NBT replay nor always-loaded endpoints belongs in the procedure.

Before acceptance, verify actual survival boarding, every automatic handoff,
normal collision and safe crouched release/braking, both directions, chunk
streaming and two-player use. Check resource cost and idle chunk counts, restart
the real server, and inspect the detailed stations from eye level and at night.
The final route and these player/native/visual gates are still pending.
