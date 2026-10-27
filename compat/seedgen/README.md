# Hybrid Aquatic and SeedGen registry parity

The pinned Hybrid Aquatic 1.7.4 server mixin runs at `MinecraftServer.loadLevel`
HEAD. It applies density wrappers, then trench carving. Its installed wrappers
target the registered `minecraft:overworld/offset`; trench carving replaces the
registered Overworld noise router. SeedGen 0.9.1 hashes the values of both the
density-function and noise-settings registries. Loading matching resource names
without these later transformations cannot establish content parity.

`HybridAquaticSeedgenCompat` is original client-only interoperation code. It uses
the installed mod's wrapper codec, marker visitor, trench loader, JSON-string
traversal, constants and existing holder invoker. The two metadata wrappers are
read from the client's selected native resource manager, in native sorted order.
Only Minecraft record components changed by native trench processing are
replaced; all other components and registered holder identities remain intact.
The exact Hybrid Aquatic version, byte count and SHA-512 are enforced. No
third-party source, bytecode or assets are copied or bundled here.

The client mixin runs just before SeedGen's normal resource-manager close, after
registry and dimension loading, before its fingerprint is computed. It does not
change SeedGen's codecs, comparison, refusal, static stems or resource ordering.
No `MinecraftServer`, world file, player, chunk ticket or generation job is
created by this adapter.

An empty successful dimension registry is normal when dimensions come from a
world preset. In that case the adapter uses Minecraft's native
`WorldPresets.getNormalOverworld` against the **current** registry load, requiring
the `minecraft:overworld` settings key and the same registered holder. The actual
owner worlds were read-only verified to select `minecraft:normal` and store that
settings key. It does not rebind a stale stem's value by key. A mismatched current
holder is refused before mutation. Other server world types remain protected by
the unchanged strict fingerprint gate; this normal-preset fallback is not a
general world-type negotiation protocol.

The native Hybrid Aquatic `reads` helper skips unsuccessful optional density
encodings while finding references. The adapter retains that branch-selection
behavior only. It does not suppress fingerprint encoding failures or normalize
different terrain definitions into agreement.

Run the bounded offline fixture from the repository:

```powershell
python -B -m compat.seedgen.probe_hybrid --home 'D:\A World for Two'
```

It checks exact installed private API descriptors, normal-close injection locals,
native server call order, actual Minecraft frozen-registry/root-holder behavior,
ordered wrapper composition, both trench branches, untouched record components,
normal-preset fallback, stale-holder refusal and native guards. The metadata and
resource limits are explicit. Its fixture substitutions are synthetic; they are
not presented as actual Hybrid Aquatic execution.

Direct execution of the installed Hybrid Aquatic helpers in a plain JVM was
attempted and failed because its static registration requires a real NeoForge
`ModList` and event bus. That failure is preserved; no fake mod loader or server
was introduced to turn it into a pass. Native private-helper invocation, complete
registered-value equality, strict client/server fingerprint agreement and faithful
terrain generation still require an authorized real runtime test. A successful
offline fixture proves none of those outcomes.

The parent integrates `HybridAquaticSeedgenMixin` into the bridge's **client**
mixin list and owns candidate/version/build/runtime actions. These source files
alone do not activate the adapter in an installed pack.

## Candidate.32 visibility failure

The actual candidate.32 callback reached the current normal-preset selection,
then failed at public reflection of `Wrapper.Companion`. The Kotlin `Wrapper`
declaring class is nonpublic even though its field and accessors are public.
The correction uses an exact private lookup for both the specification and
Companion classes, typed getter/virtual handles, and the existing private trench
lookup for `INSTANCE`. It does not use broad accessible overrides.

A regression resolves the production handles against the original nonpublic
installed classes with initialization disabled. It also requires public lookup
to reject that class, reproducing the original access mistake. Static getters
are not invoked by this resolution check, so it needs no fake mod loader.
This new regression was added source-only after the original offline receipt;
its execution and the corrected native callback remain pending parent review.
