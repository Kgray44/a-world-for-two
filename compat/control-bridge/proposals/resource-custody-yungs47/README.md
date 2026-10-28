# Proposed exact YUNG runtime-pack custody

This directory is **not active bridge source**. It fixes one observed candidate46
client load blocker; it does not establish complete SeedGen parity or authorize a
runtime change. No fingerprint, registry codec, mod selection, world seed, native
phase, descriptor, provider JAR or packet comparison is changed.

The actual first modded attempt read253 biomes and7 world types successfully,
then the existing custody helper refused
`LocateReplacerDataPackResources`, pack `mod/yungsapi:locate_replacer`.
The next filtered-registry fallback failed because Slice & Dice's sprinkler codec
needs the excluded damage-type registry. The vanilla fallback then lacked
Lithostitched's FastNoise-config registry. Those later errors are not the first
cause and are not excused by this proposal. The resulting vanilla/none client
announcement and strict server mismatch were truthful refusals.

The pinned YUNG API5.1.9 class supplies exactly one dynamic server-data resource:
`c:tags/worldgen/structure/hidden_from_locator_selection.json`, plus its original
`pack.mcmeta`. The data comes from the author's runtime locate-replacement map.
It is not an empty pack and must not be ignored. The adapter verifies the exact
installed mod version,413763-byte JAR SHA256 and9656-byte class SHA256, requires
the exact class/pack identity, and cross-checks native namespace/list/read APIs.
It enumerates the real tag, whose bytes and effective override stack then use the
unchanged complete attestation path. It never recreates or normalizes the JSON.
Other unknown implementations and every unknown subclass still refuse.

`LithostitchedSeedgenResources.java` is an original-source proposal copied from
the frozen active source SHA
`d2e4649cf128c5573f7e5e48c2a4d5050ef80276a566ac0565a89ecd1178bc27`.
`integration.diff` shows only the exact provider inventory branch.
Integration would require that proposal and `YungLocatePackCustody.java` together;
there are no mixin registrations, pack changes or partial-activation steps here.
The parent must review/build a new immutable candidate and coordinate its normal
client lifecycle. Existing candidate46 bytes remain unchanged.

The isolated Java21 probe compiles these original files against the installed
named1.21.1/NeoForge21.1.262 runtime API dependencies. It instantiates the actual
pinned YUNG class using its exact constructor, reads the original metadata/tag
suppliers, changes only its own offline JVM's native locate map, and proves the
dynamic tag bytes change. Unknown subclasses and changed JAR bytes refuse.
The actual runtime dependency order is essential: the first fixture used an
all-cache compiler classpath and stopped in Bootstrap on an obsolete Guava ABI.
That failed receipt was retained; it was not a product/runtime failure. The
corrected exact installed dependency order passed, including a final metadata
byte witness. No game, loader, Level, network, account, player or world was used.

Reproduce from the repository with:

```text
python -B compat/control-bridge/proposals/resource-custody-yungs47/probe.py --home <owned-private-staging-home>
```

The runner checks both30GiB reserves with1MiB C/32MiB D allocation, uses2 reported
CPUs and a256MiB heap, and bounds each compile/probe to60seconds. Private outputs
stay in a unique D staging folder. This is not a total-process RSS or system-wide
quota. The source handoff manifest records the final probe receipt SHA.

Remaining native gates: NeoForge's actual ModList-to-JAR path and resource loader,
the complete current opened-pack inventory (another unknown provider must still
refuse), both native provisional/authenticated loads and original ordered
resource-content equality, full Lithostitched/Hybrid Aquatic/router order, current
holder membership, original strict fingerprint and effective semantic witness,
real packet acceptance, native LOD generation and logout/worker lifecycle. The
offline probe does not prove these. Do not normalize hashes, ignore mod lists,
filter more registries, skip native phases, choose a fallback silently or announce
sharing acceptance from this result.

Primary reference: [the author's1.21.1 native pack source](https://github.com/YUNG-GANG/YUNGs-API/blob/967a20bac3f455b0ad7d0c4047a5b11c915a0eed/Common/src/main/java/com/yungnickyoung/minecraft/yungsapi/world/structure/locate/LocateReplacerDataPackResources.java)
and [native locate map](https://github.com/YUNG-GANG/YUNGs-API/blob/967a20bac3f455b0ad7d0c4047a5b11c915a0eed/Common/src/main/java/com/yungnickyoung/minecraft/yungsapi/world/structure/locate/LocateReplacerImpl.java).
The source is referenced, not copied into this original adapter. The pinned
provider declares LGPLv3; its unchanged JAR remains a compile/runtime dependency
and is not bundled into this proposal or bridge artifact.
