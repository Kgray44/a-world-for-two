# Future terrain: pinned structure refinement and qualification

Checkpoint 2026-10-28. Branch `codex/worldgen-future-terrain`, based on
`3333bc60646cc594093063ed514a3e51246e35b0`. **Source implementation is ready for
master review; native generation and deployment are not accepted.** No official
or construction save, runtime configuration, Packwiz manifest or shared catalog
was changed. The master's primary `docs/coordination/WORKSTREAMS.md` governs
integration and every Minecraft test window.

## Selected configuration

This lane adopts the master's existing template-reviewed
`proposals/future-structure-frequency/` exactly. Its actual unified diff changes
four placement files and their generator together. A reproducible review overlay
is in `proposals/worldgen-four-set-v1/datapack/`; its manifest pins every output,
the baseline policy, both source JARs and unchanged terrain inputs.

| Structure set | Spacing before / after, chunks | Separation retained | Theoretical grid opportunity increase |
| --- | --- | --- | --- |
| `castleshift:castle` | 96 / 92 | 32 | 8.88% |
| `archaeology_ruins:adoberuins` | 80 / 76 | 40 | 10.80% |
| `archaeology_ruins:mudpotterruin` | 80 / 76 | 40 | 10.80% |
| `archaeology_ruins:mudschoolruin` | 80 / 76 | 40 | 10.80% |

Every other one of the 45 reviewed baseline placement overrides remains
unchanged. Salts, frequencies, selection weights, biome filters, minimum
separations, exclusions, structure templates, loot, Tectonic settings and
dimension height remain unchanged. Castle Shift retains its ten-chunk village
exclusion. Major ancient complexes, giant temples, pirate fortresses, ocean
landmarks and large dungeons retain their existing rarity.

The pre-existing source audit examines 52 Castle Shift templates and the selected
archaeological templates. It excludes unchecked/hostile families from enrichment.
Ancient Structures' `lone_priest` template previously failed a strict Python gzip
CRC inspection; that is an unresolved source-reader observation, not a proven
Minecraft failure. No gzip validation or native check is bypassed here.

An earlier 16-set / nine-biome-filter experiment was produced before the master's
coordination document appeared. It is **held, unselected, never installed**, and
retained privately in this owned worktree. It is not part of the integration
checkpoint. The selected A/B changes spacing alone so biome changes cannot
confound its measurements.

## Measured source and synthetic results

The archive `20261028T180051Z-30624d` was verified against SHA-256
`3cb269d28ae1ccbac882a44d35277d82c83582274abad2f1cf3b41566d3e9b24`.
Its exact `world/RosewaterArtistic/level.dat` supplied the saved seed, read-only.
Only a seed digest is recorded; no world bytes or seed are committed. The old
`tools.runtime` default seed differs and must not be used for this qualification.
The archived Tectonic configuration matches the tracked baseline exactly:
SHA-256 `9ca01c0e5f109c517d2ebc025d933ca30c7c9f5010019b67527b061ecb8869d5`,
minimum Y -64, exclusive upper limit 320, vertical scale 1.4.

Eight fixed, nonoverlapping geometric windows of 512 by 512 chunks include
positive and negative coordinates. The Java 48-bit random-spread algorithm was
sampled without generating those chunks. These are actual counts from a
**synthetic grid comparison**, before biome, exclusion or native terrain checks.

| Selected set | Baseline candidates | Updated candidates | Sample difference |
| --- | --- | --- | --- |
| Adobe ruins | 333 | 367 | +10.21% |
| Mud pottery ruin | 330 | 366 | +10.91% |
| Mud school ruin | 335 | 363 | +8.36% |
| Castle Shift | 230 | 248 | +7.83% |
| Selected total | 1,228 | 1,344 | +9.45% |
| All 39 supported baseline grids | 8,366 | 8,482 | +1.39% |

Unchanged grids give identical results. Six baseline entries use custom or
frequency-reduced placements and are explicitly omitted from this synthetic
algorithm. Each window records nearest-candidate minimum/median spacing.
Separation is an algorithm offset constraint, not a universal collision radius.
No count above is a generated structure, biome-representative region survey,
benchmark, measured collision rate or performance result.

Pinned static resource inspection covers 39 artifacts and 132 structure sets.
It finds zero missing structure references, zero missing exclusion targets and
no exclusion cycles. The proposed four-set registry membership and biome
filters are unchanged. Static biome eligibility includes:

| Family | Defined structures in sets | Eligible in some Terralith biomes | Eligible in some Regions Unexplored biomes |
| --- | --- | --- | --- |
| Ancient Structures | 22 | 22 | 22 |
| Epic temples / ruins | 3 | 3 | 3 |
| Aztec Ruins | 5 | 0 | 0 |
| Archaeology Ruins | 11 | 0 | 0 |
| Castle Shift | 1 | 0 | 0 |
| Ember castles / keeps | 8 | 5 | 5 |
| Dungeons Arise | 38 | 37 | 37 |
| Philip's Ruins | 17 | 6 | 6 |
| Treasures of the Dead structures | 2 | 0 | 0 |
| Moog's temples, across dimensions | 6 | 4 | 5 |

These are resolved tag/ID memberships, not native placement successes. Several
mods deliberately name vanilla biomes directly; their exclusion of modded biome
IDs is now explicit. Those filters are not silently broadened. YUNG's jungle
temples and ocean monuments resolve both modded biome families; its desert temple
definition resolves Terralith but no Regions Unexplored member in this snapshot.

`#supplementaries:has_galleons` and `#supplementaries:has_road_signs` remain
unresolved in the archive-only index. Runtime-generated providers, pack overlays,
load order and registration hooks must be inspected natively. Author-stated
[Tectonic compatibility](https://modrinth.com/mod/tectonic) with Terralith and
TerraBlender biome mods is a prerequisite, not qualification of this exact stack.

## Implemented verification tools

- `tools.worldgen_refinement` emits a new review directory only. It validates all
  45 baseline hashes and the master's selected four changes, fails on drift, and
  never writes an installed pack or world.
- `tools.worldgen_audit` performs hash-pinned archive/tag resolution and synthetic
  grid comparison. Custom placements and runtime-generated packs retain explicit
  evidence boundaries.
- `compat/worldgen-qa` is a release-excluded native observer. It requires a
  master lease identity/expiry, explicit JVM opt-in, an owned disposable root,
  exact save/seed binding, loopback port 25585, no players and unchanged height.
  It records native loaded structure sets/biome membership, exclusion-admitted
  and biome-feasible starts, complete chunk observations, surfaces/ocean floors,
  real saved starts/piece boxes, block hashes and tick/chunk timings. Feasible
  starts are explicitly distinct from placed blocks. No force-load command,
  permanent-world path or account authentication is added.
- `tools.worldgen_results` compares exact helper-bound native receipts. It
  rejects seed/height/workload/registry drift, preserves restart differences and
  overlap candidates, reports instrumentation overhead, and cannot mark partial
  observations as acceptance.

Latest helper build: **13,026 bytes**, SHA-256
`4218edc5abf198d0abfa7882a981b5c44ea32ef628b9a3540db9edfdb0c78fc0`.
Java source SHA-256
`1f2c58d5515e563fc138b8a596f9f8653820dab25b59b2993a5f1fcb3d62916b`.
It compiled against actual installed Minecraft 1.21.1 and NeoForge 21.1.262 APIs
using Java 21.0.10. **Compilation is not native execution.** The private build
receipt preserves API hashes, reserve checks and compiler results. No helper JAR
enters Git, Packwiz or a release.

Verification at this checkpoint:

- Python 3.12.10: 967 tests, 965 passed and two Windows junction/symlink fixture
  skips; 133.930 seconds inside unittest. No test failed.
- Fourteen targeted worldgen tests passed, including drift rejection, tag cycles,
  negative grids, changed seeds/workloads, unexpected native registry edits and
  restart differences. Their invented input fixtures are source tests only and
  are never written as runtime evidence.
- Master proposal verifier: 45 canonical hashes, two pinned JARs, five actual diff
  targets and nine generator cases passed; no changes applied by that verifier.
- Pack validation: 208 lock entries, zero errors. JavaScript syntax and all four
  session tests passed. `git diff --check` passed.

The full suite began before the sprint override. Future work uses targeted
verification unless a critical integration failure justifies broader checks.

## Required disposable qualification window

Master must grant a specific window before preparing or starting a Minecraft
installation. Current lane has no such lease. Requested reservation:

- One JVM at a time, loopback 25585, maximum heap 3 GiB, initial heap 512 MiB;
  require at least 2 GiB host RAM headroom during the run.
- One private installation with hardlinks to verified immutable libraries/JARs;
  two new empty saves under `D:/A World for Two/staging/worldgen-audit/<lease>/`.
  Never copy or modify the configured permanent or construction save.
- Initial forecast C <=32 MiB and D <=3 GiB; recheck the actual bounded preparation
  before granting the writer. Maximum eight scan windows, sixteen named sets,
  384 requested FULL chunks per arm, 600 seconds per helper phase.
- Stop admission on player arrival, lease expiry, either drive reserve, folder
  budget, low host RAM, errors or uncertain lifecycle cleanup. No automatic
  retries, seed changes or replacement worlds to conceal failures.
- Preserve raw private plans, process identity, stdout/crashes, configs, receipt
  hashes and failed outcomes. Normal stop, descendant exit and released port
  require real orchestration evidence, not an advisory lock.

First compare actual loaded registry/biome resources and native feasible starts.
Select identical bounded full-chunk workloads from the union of both arms' starts,
covering actual mountains, valleys, rivers, coasts, oceans, Terralith and Regions
Unexplored biomes. Record preexisting FULL status offline; an unloaded chunk is
not automatically fresh. Inspect temple/castle/pirate/underwater pieces, terrain
cuts, entrances and suspected overlaps in the actual generated world. Acquire
normal save/stop/restart observations on both arms. Instrumented tick durations
include the observer's processing; report that cost separately and do not promote
one pair into sustained or two-player performance acceptance.

## Master-only future deployment procedure

1. Serialize the candidate with the DH/SeedGen owner and master. Recheck the exact
   gameplay pins, four-set diff, generator and current terrain bytes. Any changed
   candidate invalidates prior qualification. Preserve the saved seed and -64..320
   height range. Do not run the historical default-seed smoke command.
2. Finish disposable A/B and actual terrain/structure/biome/performance checks.
   Preserve all failed outcomes. Check a mixed-generation frontier in a disposable
   test: retain a baseline-generated patch, add new adjacent terrain after the
   update, and compare every preexisting chunk's blocks, biomes, saved starts and
   block entities across save/restart. Investigate every difference. No chunk
   deletion, retrogen, feature replay, forced population or NBT rewrite is allowed.
3. The master schedules an empty-server maintenance window and verifies a current
   retained backup plus explored-chunk/player/container provenance. A coordinate
   reservation or an empty server does not authorize this lane to deploy.
4. Apply the **existing** four-set `integration.diff` to source through the master;
   update the generated policy receipt with the same generator change, refresh
   Packwiz once under the master's file lock and validate. No stale manifests or
   unreviewed biome-filter changes. Build the matching server/client release from
   exactly the same Paxi datapack bytes. Retain the old release immutably.
5. Have TERRAIN-PERFORMANCE compare native loaded registries/resources on both
   endpoints with strict SeedGen checks enabled. The current parity gap remains a
   blocker; do not relax it, silently clear LODs/maps, or treat equal filenames as
   semantic equality. Existing DH `SURFACE_THEN_CHUNKS` / `SURFACE` fallback remains
   unchanged; a coarse LOD does not prove a generated structure or valid entrance.
6. Only the master may install the accepted candidate into the official runtime.
   Preserve existing region files, saved structures, entities, POIs, inventories
   and player progress. Keep new generation away from explored frontiers until
   the mixed-frontier check proves the exact policy safe. Inspect a small newly
   generated area and compare the retained explored-chunk inventory afterwards.
7. On a failed check, stop admission and retain the new chunks plus evidence.
   Do not delete generated chunks or replace a world to revert a configuration.
   Any coherent backup restoration or further world operation remains explicitly
   master/owner controlled. Reverting settings alone does not undo new terrain.

## Remaining acceptance

| State | Result |
| --- | --- |
| Implemented, pinned proposal and tooling | Complete for the selected four-set source checkpoint |
| Baseline/updated native structure distribution | Pending exclusive disposable test window |
| Terrain height/landforms/entrances/overlaps | Static height preserved; actual generated-terrain review pending |
| Modded biome compatibility | Static eligibility audited; literal vanilla-only gaps and generated providers remain open |
| Fresh generation time / tick spikes | No native measurements yet |
| Normal save/restart and mixed-frontier preservation | Pending |
| Client/server and strict SeedGen qualification | Coordinated with TERRAIN-PERFORMANCE; pending |
| Visual / multiplayer / official integration / owner acceptance | Pending, each separately |

The definition of done is not claimed. All requested mods remain in the unchanged
compatibility inventory, including unresolved/incompatible entries. ReserveGuard
checks passed throughout source writers; the last suite checkpoint measured
C 118,242,623,488 bytes and D 284,439,052,288 bytes free, separately above
32,212,254,720. This monitoring covers owned operations only; it is not an OS quota
and cannot constrain external applications or preexisting writers.
