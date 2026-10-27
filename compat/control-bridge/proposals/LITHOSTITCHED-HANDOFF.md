# Full Lithostitched / SeedGen integration handoff

This is the historical source handoff applied privately in candidate 42. Frozen
proposal copies remain outside the compiled source tree. The active copy also
has explicit read-only diagnostic capture and worker dispatch. Actual server and
client startup/login passed; client modded registry preparation then refused an
enumerated but natively unreadable uppercase Cristellib metadata path. No strict
SeedGen acceptance or local-generation success is claimed. The next correction
must preserve the exact raw bytes and native unreadability, rather than filtering
or renaming that metadata. See the candidate 42 native review.

The original frozen 12-file review snapshot is retained. This revision closed a
queued-payload/logout gap and added native API and surface-codec fixtures. The
handoff generator itself changes no active source, artifact, runtime, world,
account or Git state; activation was a separate parent-reviewed action.

`compat/seedgen/prepare_lithostitched_handoff.py` prepares one complete patch and
source tree under a fresh private staging folder. It refuses a changed proposal,
failed offline receipt, missing active context or an already-created active target.
Its manifest binds every proposal source and exact active baseline, the patch,
proposed tree, client API, dependency jars and callback compile. The parent must
review/apply it as one unit and assign a new immutable bridge/candidate version.
A provisional fingerprint-only repair must never be activated.

## Exact integration surface

Five classes go into `src/worldfortwo/bridge/`: Compat, Resources, LoadScope,
ConnectionGate and ClientHooks (all named `LithostitchedSeedgen…`). Four classes
go into `src/worldfortwo/bridge/mixin/`. Append exactly these names to the existing
**client** array in `resources/awft-bridge.mixins.json`:

```json
[
  "LithostitchedSeedgenAttemptMixin",
  "LithostitchedSeedgenPacketMixin",
  "LithostitchedSeedgenWorldMixin",
  "LithostitchedSeedgenQueueMixin"
]
```

Keep the existing plugin, common/server lists, required=true, defaultRequire=1,
Tectonic ordering and fingerprint codec/comparison unchanged. The proposal's
`@Mod(value="awft_control_bridge",dist=Dist.CLIENT)` ClientHooks registers the real
NeoForge LoggingOut, LoggingIn and Post tick listeners. The common ControlBridge
needs no client call.

The existing HA callback keeps its exact normal-close ordinal0 injection,
CAPTURE_FAILHARD locals and require=1. Its one old apply line becomes:

```java
if(withMods) {
    var currentStems=LithostitchedSeedgenCompat.currentAttemptStems(stems);
    LithostitchedSeedgenCompat.beforeHybrid(worldgen,currentStems,wholeSet,opened,resources);
    HybridAquaticSeedgenCompat.apply(worldgen,resources,currentStems);
    LithostitchedSeedgenCompat.afterHybrid(worldgen);
}
```

The Shadow field is not current during an isolated attempt. Omitting the explicit
currentAttemptStems call is refused. This exact patched callback and unchanged HA
helper are compiled against the compiled proposal and actual installed APIs by
the handoff tool. This is not an installed mixin activation test.

| Mixin | Exact pinned target and role |
| --- | --- |
| Attempt | `ClientWorldgen.attempt(ZZ)RegistryAccess$Frozen`: whole-method try/finally; one stems write/read and one names write are scoped. |
| Packet | `SeedGenNeoForge.lambda$onRegisterPayloads$0(SeedGenPayloads$SharedWorld,IPayloadContext)V`: wrap its one original onWorld call; capture the exact context argument. |
| World | `WorldBasis.fromSeed(ResourceKey,long,ResourceLocation)WorldBasis`: prepare inside the current packet scope, then a separate required HEAD permit check. |
| Queue | `ClientTerrain.queueFor(ClientLevel)SeedRetrievalQueue`: serialize the whole operation with logout, including its early shared-basis read. |

The payload wrapper preserves the decoded message and original onWorld body/early
return. A queued packet must still belong to the current live listener. Custody
lasts beyond fromSeed through the original SHARED.put. A private permit cannot
authorize a direct/manual fromSeed call or an obsolete connection. Logout clears
SHARED first, closes/clears queues and observes actual owned executor termination.
shutdownNow alone is never accepted as completion.

## Compile-only dependencies and handles

The patch adds pinned Lithostitched1.8.1 and SeedGen0.9.1 installed jars to the
builder's API hash table. It adds the exact named1.21.1 client API (SHA256
`a649bd3ce77f122d0f83ae1b37b4b303e662470f928b9bee5fbc76580805ffd4`) before
the other named APIs. MixinExtras0.5.5 is extracted only as a bounded compile input
from NeoForge21.1.262:727,484B, SHA256
`f0c3e3c1ad835b80e70cb3f78359b71f107f74689523b4fb391f160ee487cfbf`.
None of these classes enter the owned bridge jar. Optional SeedGen metadata becomes
BOTH, and the pinned optional Lithostitched client dependency is declared. Parent
version/pin/release work is absent from the patch.

The offline fixture constructs the production ClientAccess table using exact
typed lookups against installed named classes, without invoking its client, cache,
load or network handles:

| Owner | Members resolved |
| --- | --- |
| ClientWorldgen | volatile loaded:Frozen, stems:Registry, dataPackNames:List; private static attempt(boolean,boolean):Frozen |
| SeedSharing | SHARED:Map; fingerprintOf(RegistryAccess):String; forget():void |
| ClientTerrain / SeedRetrievalQueue | QUEUES:Map, forget():void; workers:ExecutorService |
| Minecraft | getInstance, isSameThread, hasSingleplayerServer, getConnection:ClientPacketListener |
| ClientPacketListener / Connection | getConnection:Connection; isConnected:boolean |

Real native pack fixtures exercise the exact private Path/Vanilla roots, Composite
stack and already-open File ZIP handles. No broad member enumeration is used.
Actual transformed union/module visibility remains a native gate; named-classpath
lookup is not proof of full-loader access.

## Native semantics and strict parity

The fresh load preserves native order: modifiers → surfaces → biome injectors →
FastNoise binding, then HA wrappers/trench, then dimension-filtered router wrapping
before original RandomState construction. The provisional phase omits the
seed-dependent pieces and cannot authorize a WorldBasis. The actual accepted packet
triggers one fresh full native attempt; it never re-modifies the provisional load.

The pinned modifier manager reads current registries and invokes its native
AddWorldgenModifiersEvent each time; it has no global once-only applied flag.
Surface rules retain native priority and prepend/original/append order. Router
selection retains actual getModifiersOfType order, dimension filtering and all15
target fields. FastNoise.bind uses the original `(int)seed+salt` FNL setter. These
phases are called, not reimplemented. Event behavior and transformations still need
actual paired proof.

The new fixture executes the real TransientMergedRule codec and native constant
surface evaluation. Two different effective rules produce the same original_source
encoding and different blocks. This is native codec behavior, not a normalization
performed by the adapter. Native fingerprints also do not attest the effective
injected biome source or mutable bound FNL state. Exact input bytes and the same
native phases protect those inputs, but do not replace the final semantic witness.
Matching fingerprints alone must not be called full terrain parity.

## Bounds and refusals

Each attestation reads at most512MiB total,32MiB/member,262,144 raw/effective entries,
512 pack nodes,16 Composite levels,128 path levels,1,048,576 traversal visits and
60seconds. Both loads pass separately; worst-case extra reads are1GiB across the
provisional/authenticated loads. Streams use64KiB buffers and write no files. Actual
opened-graph size/time is unmeasured. Caps must not be raised automatically after a
native refusal. Unknown implementations, partial walks, corrupt ZIPs, byte/order
changes and unsupported roots refuse. Masked Composite children are attested too.

Registry/holder mismatch, incomplete/reentrant scope, missing marker/hook, changed
content, unequal members, native fingerprint mismatch, stale listener or failed
publication cannot authorize generation. Seeded partial failure, foreign global
WORLD_SEED, different seed, cleanup failure/timeout or integrated-server observation
requires restart. Same-world reconnect may reuse prepared registries only after
owned queue workers terminate. No waiting holds a worker-required lock.

This first-remote-seed process pin does not assert arbitrary external DH work drained
and cannot prevent another mod/integrated server writing its own globals. Restart
the client **before** changing seed or opening a local world. The adapter refuses
its own later preparation/admission after a changed context; unrelated upstream
jobs are outside that guarantee.

Source/probe/handoff writers reserve16MiB C: /32MiB D: and use new private folders.
Compiler heap is capped256MiB and fixture heap384MiB. These are offline limits,
not runtime performance measurements. ReserveGuard does not constrain unrelated
applications or existing writers.

## Native42 decision map

| Stage | Required evidence |
| --- | --- |
| Full loader | All four required mixins, exact local captures/redirect counts, client hook and union typed handles activate; dedicated server avoids client-only class loading. |
| Paired definitions | Re-export the complete scope (previously1,950 selected keys,248 densities), all selected noise settings and original native fingerprints from actual server/client. Compare exact values, not counts alone. |
| Effective definitions | Read native merged-rule effective list/order (not only original_source), actual wrapped15-field routers and current holder identities on both sides. Unknown/unexportable structure remains unknown. |
| Accepted seed | Original strict acceptance; one current live native SharedWorld packet; one complete fresh attempt; exact content/member/native-FP equality; publication only after gates. |
| Real generation | Observe actual InjectorBiomeSource/injector preparation and native FastNoise binding, then known ocean/HA and RU/FastNoise terrain through actual LOD generation. No fixture seed/terrain counts as evidence. |
| Lifecycle/cost | Real disconnect/worker retirement, same-world reconnect and stale-packet refusal; observe fingerprint/rebuild latency, RAM and CPU. Different/local seed requires a new client process. |

Failures retain receipts and caches. Do not normalize differences, remove phases,
reroll terrain, reuse stale evidence or declare native success from these offline
checks. They support reviewing a native candidate and do not qualify it.
