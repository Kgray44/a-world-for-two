# Worldgen fingerprint input diagnostic proposal

This original helper is outside production `src/` and is not installed. It inspects
the actual registry access already used by each side. It does not call a SeedGen
fingerprint/cache method, populate a cache, load client worldgen, change a registry,
create a world, or relax generation refusal. No upstream ARR source or assets are
copied. The exact installed SeedGen 0.9.1 bytecode was inspected read-only.

`SeedSharing.computePrint` uses `RegistryOps.create(JsonOps.INSTANCE, access)`:

1. Sorted resource-location strings only, in this registry order: `BIOME`,
   `PLACED_FEATURE`, `NOISE`, `MULTI_NOISE_BIOME_SOURCE_PARAMETER_LIST`.
2. Sorted holder key, then successful native encoded JSON for `NOISE_SETTINGS`
   using `NoiseGeneratorSettings.DIRECT_CODEC`.
3. Sorted holder key, then successful native encoded JSON for `DENSITY_FUNCTION`
   using `DensityFunction.DIRECT_CODEC`.

Its SHA-256 input uses UTF-8 `JsonElement.toString()` bytes, preserving native JSON
member order; the displayed native fingerprint is its first eight digest bytes.
For an ordinary codec `DataResult` error, native code still hashes the key, omits
the value, and warns. A thrown exception aborts native computation to `unknown`.
The diagnostic preserves each ordinary error and thrown exception separately;
it never labels a partial export or exception-contaminated digest as equivalent.

The source validates the original SeedSharing and ClientWorldgen class SHA-256
resources from the pinned jar (whole jar SHA-512
`4b0bbb0426d0d600fcef2deb0580f458bbf16b90440b84b9d28fe377a3107cf22ff9f166eec85b802cb5386d5af39d5b0a12ac6bf7ca04fad427206d1405c61d`).
It uses no class-member enumeration. The client reads only exact field
`ClientWorldgen.loaded: RegistryAccess.Frozen` with a typed private MethodHandle;
a null cache refuses without calling `get`, `load`, or `attempt`.

Before integration, the parent must review and add exactly this additional
diagnostic-only alternative to the existing `SeedgenFingerprintCodec.guarded`
StackWalker predicate:

```
frame.getClassName().equals("worldfortwo.bridge.WorldgenFingerprintDiagnostics")
    && frame.getMethodName().equals("encodeFingerprintValue")
```

The existing `SeedSharing.computePrint` predicate and actual root-value adapter
remain identical. This allows the same native codecs, including nested router
calls, to get the same transparent-root handling during diagnostic encoding.
No ordinary codec call gains this scope. A synthetic direct holder/constant probe
refuses export if this scope is missing; it does not register or rebind anything.

After review the parent may include this class in a subsequent candidate and wire
console-only server dispatch to
`write(server.registryAccess(), privateDirectory, uniqueId, "server_registry_access", full)`.
The QA helper calls public `writeLoadedClient(Path,String,boolean)` by exact typed
MethodHandle. These are explicit export actions, not startup hooks. Use a fresh
owned private directory and unique ID after dispatching the host ReserveGuard.
Serialize dispatch with data-pack reloads; no writer should change these frozen
registries during capture.

Each export reserves at most 16 MiB across immutable JSONL and status files. Full
encodings are opt-in. The cap is enforced before each line write; a cap failure
preserves the earlier complete lines and writes `complete=false` separately.
Individual encodings are bounded at 8 MiB, total keys at 32,768, and elapsed time
is checked between entries (20 seconds); a single native codec call cannot be
preempted by this cooperative limit. Disk admission is checked again by Java,
but does not replace the owner's two-drive ReserveGuard dispatch requirement.

The first comparison should match registry presence, sorted key sets, error status,
and each `value_sha256`, then inspect only differing full encodings privately.
The diagnostic aggregate is evidence about its inputs, never a generation permit.
The existing strict native client/server comparison remains the acceptance gate.
No native execution, compilation or equality result is claimed by this proposal.
