# Continuous real-chain zipline proposal for candidate44

This is original optional client code, outside active source. It uses the public
Ziplines1.5.3 Cable/Cables API and the actual Connectible Chains2.4.4 live link
graph. The compiled/source mod archives remain private; no third-party JAR or
authored structure data is included here.

The pinned stock ChainCable inherits Cable.getNext's empty collection. Splitting
a line into actual chain spans therefore needs a handoff adapter. This provider
wraps each actual ChainCable and delegates its point/progress/direction/length
without modifying native physics or adding distance bias. At an endpoint it
enumerates actual incoming and outgoing links sharing that same loaded knot.
Native ZiplineLogic already chooses the next cable by look/turn, preserves speed
and direction, checks collision and handles release/braking. It remains the rider
controller; this adapter never moves or creates a player or entity.

The graph reads only loaded entities. Spans are capped at80m in3D, with128 local
knots,256 edges and8 candidate exits as finite limits. Changed/moved/removed links
invalidate a held cable. There are no packets, fake remote anchors, world/chunk
reads that load terrain, persistent caches, tickets or idle simulation. A ride
must not depend on a remote knot outside client visibility.

## Exact registration and class loading

Use the client presentation module. Register from its CLIENT-only Presentation
constructor, after both optional mods are present but **before Zipline.init**.
Put only the following optional ordering metadata in its client mod definition:

```toml
[[dependencies.awft_client_presentation]]
modId="zipline"
type="optional"
versionRange="[1.5.3,1.5.4)"
ordering="BEFORE"
side="CLIENT"

[[dependencies.awft_client_presentation]]
modId="connectiblechains"
type="optional"
versionRange="[2.4.4,2.4.5)"
ordering="AFTER"
side="CLIENT"
```

The constructor must check both ModList entries and lazily/reflectively invoke
`worldfortwo.presentation.LoadedChainGraphProvider.registerOnce`. Do not put a
chain/zipline type in an unconditional static field or common-server entrypoint.
The existing presentation entrypoint has `@Mod(..., dist=Dist.CLIENT)` and its JAR
is client-only. Preserve that dedicated-server boundary. Add the exact installed
Ziplines and Connectible Chains JARs as compile-only APIs; do not embed them.

Provider ordering is functional: Cables picks strictly closer, so an equal-distance
provider appended after the stock one loses. The real API probe confirms both
orders. Do not use epsilon/distance bias as a workaround. Native client inspection
must confirm the selected class is the wrapper when the ride is tested.

The exact installed FML4.0.45 constructor-future and optional BEFORE audit is in
[LOADER-ORDERING.md](LOADER-ORDERING.md). It confirms these constructor tasks are
serialized by their ordering edges even though unrelated constructors run in
parallel. Register directly in the constructor, not deferred setup work.

## Pinned native semantics and route requirements

Connectible Chains defaults to maxChainRange32 and breaks overlong links during
normal ticks. Propose explicit server-synced maxChainRange96 for this80m route;
keep the source's normal length enforcement. A static515m link is insufficient:
the client stock provider requires the far knot to be tracked, and it is not
automatically available at that distance. Increasing a server ticket range alone
does not establish client visibility.

Short spans must use real modest supports on verified dry land, with two endpoint
stations and turns below45degrees (native direction-dot threshold0.707). Current
server view6/simulation4 and a client render distance of at least6 are the proposed
visibility envelope, still requiring a player test at chunk boundaries. A further
restart boundary matters: unresolved holders resolve in knot.tick, so a tracked
but non-ticking incoming source can remain unresolved. Prefer actual spans≤48m
to give the current simulation distance a one-chunk margin in both directions.
The80m adapter bound is not a claim that every80m reload is ready. A different
choice needs actual proof or an explicitly bounded real-rider simulation lease;
there is no such lease in this adapter. Per-link
customSlack16 gives the real API's1.329m midpoint sag on the probe's~66m spans;
survey each actual catenary and hanging player AABB, not only the straight chord.

Native ChainCable adds0.4 above knot.position. Default hangOffset2.3 can leave a
player's head inside a fence anchor at a shared knot. Propose the supported,
server-synced hangOffset3.0 and boarding deck floor+4 / anchor block floor+8, then
verify actual knot position, normal player dimensions and collision. Do not alter
the curve or bypass collision to force a handoff. Keep realisticPhysics and speed
at their existing settings until measured play warrants a change. Normal pickaxe,
hoe or tagged wrench attachment is supported; release while crouching suppresses
exit momentum in the pinned mod. Actual boarding and braking remain player gates.

For construction, normal APIs are `ChainKnotEntity.getOrCreate(level,pos,item,face)`
and `owner.attachChain(new Chainable.ChainData(holder,item),null,true)`. First refuse
any foreign existing knot, prove the exact anchor is in #chain_connectible, prove
the catenary item tag and native range, and create only the bounded admitted route.
Set actual link.customSlack before normal attachment. The upstream getOrCreate
does not propagate addFreshEntity's result: prove each returned knot is actually
registered in the level, alive and discoverable before counting it. Journal the actual created
UUIDs, endpoint block positions/faces, source item and directed edges; never invent
UUIDs or replay saved entity NBT. Native knot-to-knot saves use relative block
coordinates (RelX/Y/Z), source item and Slack. Restart verification must find the
same recorded knots/links without creating replacements, allow normal resolution
when both endpoint chunks load, and confirm no foreign/duplicate links or drops.
Do not keep endpoints forcibly loaded at idle. Partial creation retains exact
UUID custody and requires explicit diagnosis, not an automatic cleanup/retry.

## Evidence and remaining gates

The two Java probes compile and run against the actual pinned binary APIs, without
constructing a Level, entity or player. Ten checks per ordering verify native
endpoint math, shared endpoint continuity, sag, chord turn, the public getNext hook
and the first-provider tie rule. The compile/probe receipt is private at
`H/staging/zipline-graph-api-probe-20261027T2319Z/receipt.json`, SHA256
`c4a2f085561b717f47c32d5749f465233c22d53dab0cb991a385c58ad7f2e30a`.

This is API evidence, not a loaded-world graph, actual ride, survival safety,
multiplayer, restart or visual acceptance result. The adapter remains uninstalled.
Stations and intermediate supports require exact saved preimages and forest/view
reservations. The surveyed cliff plot does not yet have a proved walking route
from town; construction must add and verify safe access. Test survival boarding,
every live handoff, both travel directions, safe crouched release, chunk streaming,
two players and restart. The real route and ornate station appearance are still
pending native implementation/review.
