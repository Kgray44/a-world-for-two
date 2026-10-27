# Lithostitched: native client initialization proposal

These original sources are outside active `src/`. They are not installed and do
not establish native generation parity. Do not integrate only the provisional
fingerprint phase: the seed-dependent path and mandatory basis guard are part of
the same proposal. Native server/client fingerprint comparison and codecs remain
unchanged.

The candidate35 paired exports agreed on all 1,950 selected registry keys and all
248 density-function encodings. Only the Overworld and Nether noise settings
differed. The server had actual `lithostitched:transient_merged` surface rules;
their `original_source` equalled the client's original rule. The Overworld also
had an actual Lithostitched wrapper around fluid floodedness. Those are missing
native modifications, not values to normalize out of a comparison.

## Exact installed hook order

Lithostitched 1.8.1's dedicated-server mixin, priority1500, calls
`LithostitchedInternalHooks.onServerAboutToStart` immediately before
`DedicatedServer.loadLevel`. Its native `applyModifiersAndInjections` performs:

1. `ModifierManager.applyModifiers(RegistryAccess, Registry<LevelStem>)`.
2. `SurfaceRuleManager.applySurfaceRules(RegistryAccess, Registry<LevelStem>)`.
3. `BiomeInjectorManager.applyBiomeInjectors(..., actualSeed)`.
4. Each actual `FastNoiseConfig.bind(actualSeed)`.

Hybrid Aquatic then applies its wrappers followed by trench carving at
`MinecraftServer.loadLevel` HEAD. Later, Lithostitched's `ChunkMapMixin` wraps
`RandomState.create`: it selects actual dimension-specific `WrapNoiseRouterModifier`
entries and calls native `modifyDensityFunction` for each of the15 router fields,
then native `NoiseGeneratorSettingsAccessor.setNoiseRouter`.
`WrapNoiseRouterModifier.apply` is deliberately empty; calling only the modifier
manager cannot repair the floodedness difference.

The installed HA jar provides22 injector definitions. Regions Unexplored also
provides2 FastNoise definitions, alongside Lithostitched's own region definitions.
Resource predicates still determine the actual active set. These seed-dependent
systems must not be skipped merely because SeedGen's selected fingerprints match.

## Complete client flow

In the existing client-only `HybridAquaticSeedgenMixin` normal resource-close
callback, replace the single HA call with this sequence, inside `if(withMods)`:

```java
var currentStems = LithostitchedSeedgenCompat.currentAttemptStems(stems);
LithostitchedSeedgenCompat.beforeHybrid(worldgen, currentStems, wholeSet, opened, resources);
HybridAquaticSeedgenCompat.apply(worldgen, resources, currentStems);
LithostitchedSeedgenCompat.afterHybrid(worldgen);
```

`opened` is the existing exact local `List<PackResources>`; `resources` is the
still-open exact native `CloseableResourceManager`. The callback's current native `worldgen` and returned registry are the same
object. Keep the current exact local capture/normal-close injection and existing
Tectonic resource ordering. Do not call the helper from fallback vanilla loads.

Before the server shares a seed, this performs only native modifiers/surfaces,
HA and native router wrapping. The native NORMAL preset creates current dimension
objects through `createWorldDimensions().bake(actualExplicitStems).dimensions()`.
All noise holders must belong to this exact private registry load. Explicit
custom dimensions are retained. A delegating view supplies that LEVEL_STEM
registry while every other registry object remains identical. No registry is
unfrozen or re-registered. The provisional dataset can take part in the existing
strict native handshake, but cannot construct a modded WorldBasis by itself.

The new client-only `LithostitchedSeedgenPacketMixin` scopes the exact original
NeoForge SharedWorld handler's `SeedSharing.onWorld` call. It retains the real
IPayloadContext listener and requires that exact listener to be Minecraft's current
live play connection. The scope covers the whole original body, including its
later SHARED.put. A stale/dead queued connection is refused without reopening the
gate or poisoning a new connection. The original serverGeneration early return is
preserved. `LithostitchedSeedgenWorldMixin` wraps and separately guards the original
`WorldBasis.fromSeed` inside that scope. Its dimension, actual seed and world type
are passed unchanged. On the client thread, the helper
requires no already-active native world bases, then performs one fresh exact
native `ClientWorldgen.attempt(true, sameWholeSet)` under
a scoped authenticated-seed context. This fresh dataset runs the full native
Lithostitched startup hook before HA, then the native router phase after HA.
Nothing is applied twice to the provisional dataset. This fresh load is necessary
because native injectors prepare density visitors/RandomState before HA rebinds
holders; running them late against the provisional modified dataset would not
preserve that order.

After the fresh load completes, the helper requires the same complete registry
member keys, explicit filenames, actual ordered opened pack IDs and strong
SERVER_DATA byte attestation. It calls original native
`SeedSharing.fingerprintOf` on the fresh dataset and requires exact equality with
the already accepted provisional native fingerprint. This is an additional gate,
not a replacement comparison. Only then does it publish the fresh native cached
registry and its current native prepared dimensions. The original `fromSeed`
builds the actual generator/RandomState from them; there is no custom generator,
fake server, invented seed, world file, player teleport or comparison suppression.

`LithostitchedSeedgenWorldMixin` also adds a required HEAD guard to `WorldBasis.fromSeed`.
It requires a scoped permit from the original `onWorld` wrapper, a matching actual
seed/dimension/type, the current published registry, and fully seeded prepared
dimensions with exact noise-holder identity. `beforeHybrid` also checks that this
guard mixin actually marks the transformed native class before applying anything.
If the packet wrapper is missing, the WorldBasis guard refuses generation. A
fingerprint-only partial integration therefore cannot authorize known-wrong biomes.

## Complete resource and cache custody

`LithostitchedSeedgenResources` hashes every native-valid SERVER_DATA member
selected by each actual opened pack, its ordered ID/class/namespace inventory,
root `pack.mcmeta` (including filter/overlay metadata), Composite structure and
the actual effective resource stacks in order. Native filenames alone are
insufficient: the fingerprint omits Lithostitched injector/region/FastNoise values.
Same-ID byte changes therefore fail this separate custody gate even if covered
native registry values and the native fingerprint do not change.

The named 1.21.1 `PathPackResources` and `VanillaPackResources` silently reject an
empty string listing prefix. Native `PathPackResources.listPath` also logs certain
I/O failures instead of throwing them. Exact typed private root getters therefore
feed a strict finite root walk and the public native `listPath` primitive with an
empty *segment list*. Their inventories must agree. Native namespace listing must
also match the independently read path root. Unreadable, symbolic, partial or
changing trees refuse; an absent sparse Vanilla namespace is legitimate. Actual
selected bytes still come from native `PackResources.getResource`.

The new ZIP fixture exposed a separate native empty-prefix omission: the pinned
`FilePackResources.listResources` appends a slash, producing a double slash for an
empty query. Exact typed handles inspect its already-open native ZipFile and prefix;
the bounded central directory supplies the complete valid ID inventory. Native
nonempty directory listings must match, and namespace-root files are read directly
through native `getResource`. A failed native ZIP open cannot count as an empty pack.
Nothing is extracted or independently reopened.

Each actual Composite child is attested in native overlay order, including the
primary exactly once; every child's metadata and bytes are read before the Composite
winner is attested. A byte change in a fully masked child is therefore also refused.
The exact NeoForge21.1.262 EmptyPackResources class is resource-hash pinned. Only the
exact five supported implementation classes are admitted; an unknown subclass also
refuses generation. The manager's actual pack objects/order must match `opened`;
effective stacks use native `getResourceStack(id)` over the complete known ID union.
No pack or manager is closed by the helper.

The attestation streams64KiB buffers, at most512MiB total reads per load,
32MiB/member,262,144 raw/effective entries,512 complete pack nodes,16 Composite
levels,128 path levels,1,048,576 traversal visits and a60-second deadline checked
during enumeration and reads. Failure is retained;
caps are not increased automatically. Actual game-time cost and union-filesystem
implementation coverage remain unmeasured. Nothing is written to disk by the
runtime attestation and neither input JSON nor a fingerprint is normalized.

`LithostitchedSeedgenAttemptMixin` wraps the *whole* exact native attempt in a
try/finally frame and redirects its one stems write, its one subsequent stems
read, and its one dataPackNames write. The existing callback's @Shadow static read
is outside that method, which is why `currentAttemptStems` above is mandatory.
Failed, throwing and null-returning attempts do not publish those metadata fields.
The provisional success publishes only fully validated current dimensions/names;
the outer native `get()` retains responsibility for assigning its returned loaded
registry. The authenticated fresh success keeps its metadata private until content,
member and original-native-fingerprint gates pass. Its loaded publication checks
the previous identity and rolls back its own metadata on a failed compare-and-set.

This is guarded publication, not a transaction over all upstream globals. The
native Lithostitched hook changes WORLD_SEED and prepares native seeded objects;
those effects cannot be undone by restoring a pointer. A failed seeded attempt
therefore latches a client-restart requirement. No active shared bases are allowed
during a fresh load. All guarded WorldBasis construction is serialized and denied
until complete; arbitrary upstream readers of separate volatile cache fields do
not receive an invented atomic multi-field guarantee.

## Real logout and process-lifetime seed policy

The pinned SeedGen has no actual caller of `SeedSharing.forget`; merely injecting
that method does not provide disconnect cleanup. A required dedicated-safe
`LithostitchedSeedgenClientHooks` registers NeoForge's real client LoggingOut event
and observes client ticks. It never dereferences the event player/connection,
which are legitimately nullable. It calls the exact native shared cleanup first,
then captures/closes/clears actual ClientTerrain queues through exact typed handles.
No `ClientWorldgen.get()` or registry load is invoked during cleanup.

The required whole-operation `LithostitchedSeedgenQueueMixin` holds the same
admission monitor through the original queueFor, including its early shared-basis
read and later queue-map lock. Logout closes admission under that monitor before
cleanup. A caller cannot retain an old basis and repopulate the map after cleanup.
The current-connection payload scope also closes the separate later gap between
native fromSeed returning and original onWorld publishing into SHARED. NeoForge's
queued payload context has no later connection check of its own, and the pinned
handler never reads that context. Wrapping fromSeed alone leaves this gap.
Lock order is helper monitor → connection gate → native QUEUES. Cleanup never
waits while holding a monitor that an owned worker could need.

Native queue close only calls shutdownNow. The proposal captures actual owned
ExecutorServices and observes `isTerminated` on client ticks; it does not treat
shutdown as termination. New permits remain refused while retirement is pending.
A30-second nonblocking observation deadline becomes a sticky restart requirement;
repeated logout events do not postpone that original retirement deadline.
late termination does not erase failure. A reconnect arriving before termination
also refuses rather than inventing readiness. A completed same-seed reconnect
uses the already seeded registry and does not reapply native modifiers.

Native DH can also schedule generation on external executors. The proposal does
**not** claim those jobs drained. Instead its first authenticated seed is pinned
for the lifetime of the Minecraft process and never cleared on logout. A different
seed is refused before any new native seed mutation. Every permit/queue admission
checks native WORLD_SEED still matches the process pin. An integrated-server
login/tick observation, active integrated server, or nonzero foreign native seed
before first remote activation also refuses this remote-only adapter until restart.
This intentionally limits SeedGen to the permanent remote world for that process;
it is not an arbitrary singleplayer/multi-server seed-switch implementation.

The transformed payload host, WorldBasis, native-attempt and queue classes must all carry their
required guard markers and the real client hook must be installed before any
native modification. A partial integration cannot authorize generation.
A partial/reentrant load, changed input, cleanup timeout, differing definitions or
failed publication retains a process-wide failure state. No new helper log record
contains seeds, resource contents or player/account data.

## Integration and evidence limits

Parent integration must copy Compat, Resources, LoadScope, ConnectionGate and
ClientHooks to the bridge package, add Packet, World, Attempt and Queue mixins to
the **client** list, add the exact callback sequence above,
and include the exact installed Lithostitched and SeedGen jars as compile-only APIs.
The pinned native MixinExtras0.5.5 API is nested in NeoForge21.1.262's universal jar;
its727,484B SHA256 is
`f0c3e3c1ad835b80e70cb3f78359b71f107f74689523b4fb391f160ee487cfbf`.
Do not bundle any of these dependency classes. Source/runtime jar and class-resource
guards pin Lithostitched1.8.1 and SeedGen0.9.1. Lithostitched reports MIT; SeedGen
reports ARR. This proposal contains original interoperation code and no copied
upstream implementation or assets.

`python -B -m compat.seedgen.probe_lithostitched --home <private artistic home>`
compiles against exact named installed APIs, checks native bytecode descriptors,
phase order, all cache read/write sites and flags, and exercises native Minecraft
frozen registry/normal preset selection plus15-field router custody. Actual native
PathPackResources, FilePackResources, CompositePackResources and
MultiPackResourceManager fixtures reject same-ID injector byte changes, fully masked
child changes, reorderings, root-filter metadata changes, unsupported subclasses,
invalid data roots, corrupt ZIPs and a resource exceeding the finite32MiB cap. Original policy
fixtures demonstrate the captured-old-basis/logout race, same-seed reconnect,
different/foreign-seed refusal, a real executor that ignores interruption, actual
termination observation and sticky timeout. These are isolated contract tests,
not actual transformed native packet/lifecycle execution. It uses a fresh bounded private
directory, Java21 (compiler256MiB / offline fixture384MiB), preserves failures and
does not launch a game/server or fabricate FML/ModList. The existing named client
API is included for the actual typed ClientLevel/NeoForge lifecycle signatures.
ReserveGuard admits at
most16MiB on C: and32MiB on D: before output.

The latest bounded compile and all offline contracts passed on2026-10-27.
The private result receipt has SHA256
`2d4d7c8a277e9716579da24f55899ccb679a642adf105c0385f709acd10f2bc3`.
This includes the actual production typed native handle table (none of its
client/cache/network operations invoked), stale-payload/whole-onWorld logout races,
and a real native merged-surface codec counterexample.
The immediately preceding failed fixture, which identified the native ZIP
empty-prefix omission, remains preserved separately. These receipts contain no
native packet acceptance or installed artifact.

The first compile exposed a missing nested MixinExtras compile API and use of a
MappedRegistry-only `isEmpty` method through Registry; these were corrected.
A subsequent fixture correctly refused a duplicate identical LevelStem registered
under two keys; the custom-dimension fixture now uses a distinct generator while
retaining its actual registered noise holder. Failed receipts remain private.

Still required before enabling: parent source review, native transformed mixin and
union-loader validation, one actual authenticated accepted seed packet, fresh native
input equality/readback, actual injected biome-source/seeded FastNoise evidence and
LOD generation checks. The new extra registry load's CPU/RAM cost is unmeasured.
The pure source/offline contract is not live parity or owner acceptance.

See [LITHOSTITCHED-HANDOFF.md](LITHOSTITCHED-HANDOFF.md) for the exact atomic patch,
client registrations, callback and compile-only changes, refusal states and native
acceptance map. The real TransientMergedRule codec deliberately serializes only
original_source: equal encoded settings can contain different effective surface
rules. The extra native semantic witness in that handoff is essential; fingerprint
equality is not proof of all generated terrain.
