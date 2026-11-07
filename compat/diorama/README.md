# Diorama native model calls

The official MIT Diorama 0.7.0 NeoForge 1.21.1 artifact calls vanilla's legacy
three-argument `BakedModel.getQuads` while building map colors. Existing
ShetiPhian models explicitly log that they need NeoForge's model-data API and
skip their rendering. This was observed in an independent copied-world test.

The repair changes exactly two call sites: the legacy quad call becomes
`IBakedModelExtension.getQuads(state, direction, random, ModelData.EMPTY, null)`;
the particle fallback uses `getParticleIcon(ModelData.EMPTY)`. `null` requests
all render layers. The original random seed, traversal, fallbacks and every
other upstream class/resource stay intact. This does not invent block-entity
model data for an unloaded world location.

`tools/diorama_patch.py` accepts only the exact official size and SHA-512. The
ASM 9.10.1 transformer requires exactly one matching call in each reviewed class,
recomputes stack bounds without changing control flow, and refuses layout drift.
It verifies the archive and all unchanged entries. The original license remains
inside the repaired JAR, with an added repair notice; the upstream MIT license
is also retained here. JARs and build caches stay outside Git.

```powershell
python -m tools.diorama_patch <official-0.7.0-neoforge-1.21.1.jar> <new-output-directory> --libraries "D:\A World for Two\server\libraries"
```

The copied-world native test loaded `0.7.0+awft.1-neoforge-1.21.1`, built colors
for 939,699 states in 64,619 ms and emitted no prior legacy-model warning,
`VerifyError`, or `AbstractMethodError`. This is a bounded initialization result,
not rendered-map, performance or multiplayer qualification. The test client was
terminated after the diagnostic capture because reliable UI closure was
unavailable; it does not supply clean client-shutdown acceptance.

Source reviewed: <https://github.com/SunkenInTime/diorama/tree/v0.7.0>.
Native API verified against the installed NeoForge 21.1.262 interface.
