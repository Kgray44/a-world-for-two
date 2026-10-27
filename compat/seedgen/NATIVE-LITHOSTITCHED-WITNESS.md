# Effective native Lithostitched witness proposal

`proposals/NativeLithostitchedWitness.java` remains outside active sources until
the parent explicitly integrates it. This is private read-only evidence, never
an alternate fingerprint, generator, normalization pass or acceptance override.
The native strict fingerprint and original diagnostics must remain unchanged.

Public entry point:

```java
NativeLithostitchedWitness.write(
    actualRegistryAccess,
    actualGeneratorsByDimension,
    existingOwnedPrivateDirectory,
    uniqueId,
    "actual_server_levels" /* or "current_selected_client_stems" */);
```

Capture the immutable map of **actual existing** server level generators on the
server thread. On the client thread capture the actual already-loaded cache and
the current published selected stems using exact typed handles; never reconstruct
generators, reuse the old callback shadow, request a new native load, or read a
Minecraft/Level object from the worker. Send these references to one separately
owned bounded diagnostic worker. The exporter refuses `Server thread` and `Render
thread`; no automatic tick or payload hook should perform this work.

After completion the owner must recheck the actual registry/cache/stems identity
and connection generation on the correct main thread before treating the receipt
as current. The exporter checks native WORLD_SEED and captured generator, biome
source, settings holder/value and router identities before/after. Each native FNL
state is reread after export. This detects those observed changes; it does **not**
prove arbitrary mutable graphs immutable or a volatile ABA transition impossible.

## Actual effective state, not the misleading base-only codec

- A `TransientMergedRule` exports its actual `rules()` in native order and its
  separate `original()` provenance. Native `apply()` executes `rules`, while the
  native codec encodes only `original_source`. They must never be conflated.
- Native sequence/test sources are traversed through exact private typed method
  handles. Reference rules include actual holder IDs and current values in order.
  Leaf rules use their native codec. Uninspected custom leaves explicitly add
  UNKNOWN; successful serialization alone cannot establish their hidden state.
- Every actual NoiseBased generator exports all fifteen fixed router fields in
  native order, actual classes and native encodings. Native encoding failures
  remain UNKNOWN. An actual root HolderHolder is an explicit holder node with its
  current registry identity/key and recursively inspected held value; it is not
  replaced or encoded as if the wrapper never existed. This requires no new
  transparent-root codec scope. No function or encoded value is substituted.
- Generator settings must be the exact current reference from the actual noise
  settings registry. Direct/foreign holders add UNKNOWN.
- The actual InjectorBiomeSource wrapper exports its direct delegate, native
  current injector groups and list order, per-injector native encoding, priority,
  dimension, possible/replaced biome holder lists, and current region function.
  Its effective biome-to-region output thresholds and total weights come from
  exact private native record getters. No manager/application/sample method runs.
- A current native MultiNoise source also exports its actual parameter points,
  current biome holders and real private RTree index: ordered child topology,
  all native parameter bounds and leaf holder values. A preset's native codec can
  otherwise hide updated parameters behind the preset ID. Per-worker last-result
  search hints are not read; matching this structural witness is still not a
  proof of arbitrary mutable graph immutability or actual terrain generation.
- Every current registry FastNoiseConfig exports native config encoding,
  frequency bits and salt, plus the actual protected FNL object's eighteen exact
  fields: seed, octaves, all float bits and enum values. WORLD_SEED is recorded.
  These seed-bearing files are strictly private and must never enter Git/Pages,
  public test fixtures, release notes or user-visible command output.

The entire original installed Lithostitched archive is checked against
`e0da669fa5facc61a09b9b7bae21b322993de1fcd1eb05787adffb7309598cca`
and 1,023,751 bytes, followed by seven exact original class-resource guards.
There is no broad field enumeration, arbitrary expression evaluation, world
read/write, registry mutation, bind, sample, generation, manager execution or
fingerprint invocation in the exporter.

## Bounds and honest limits

The worker has 32 dimensions, 32,768 visited nodes, 96 surface nesting levels,
4,096 per-rule/injector/config entries, 128 injector groups, a 16 MiB total
private output bound and 8 MiB per output row. It checks a 60-second deadline
between native operations and traversals. The deadline is cooperative: an
individual native codec is not preemptively interruptible, and cancellation does
not prove its worker terminated. This is why the exporter cannot run on the tick
thread and the owner must record actual worker completion/cost. Do not claim a
hard 60-second native execution guarantee or raise bounds silently.

Output is a unique `*.lithostitched.jsonl` plus separate status receipt; existing
files and partial failures are retained. C: and D: reserves and existing private
D: directory custody are checked before output. `complete_export` only means
the finite export finished. `effective_state_coverage_complete` additionally
requires zero UNKNOWN states. `strict_parity_proved` is **always false** here.
Even two successful files need an explicit per-dimension/key comparison and
current-generation provenance; neither raw output checksums nor identical
UNKNOWN states are a semantic acceptance decision.

The offline probe compiles the exact new source with the pinned named dedicated
API under a 256 MiB heap. It verifies original class guards and exact private
injector/region/config handle resolution; it executes native merged/sequence/test
surface getters and distinguishes effective dirt/gravel rules despite identical
original stone. It reads all eighteen real FNL fields and observes a synthetic
SetSeed change. It deliberately does not spoof Apollib's loader configuration to
construct a FastNoiseConfig: that requires the real native lifecycle. Earlier
missing-Apollib/config-lifecycle failed receipts are retained.

Required native evidence still includes actual server/current client export,
full applied injector/region/config observations, transformed classloader access,
original 1,950 selected keys and 248 density encodings, strict authenticated
packet acceptance, matched effective semantic state with zero unknowns, and actual
LOD/terrain generation. A successful compile/offline probe is none of those.
