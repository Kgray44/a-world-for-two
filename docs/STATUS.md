# Build and acceptance status

**Documentation checkpoint: 2026-10-28 UTC.** Public candidate.31 remains the
published immutable prerelease. Private candidate.48 reached native readiness
and a licensed owner join. Construction, mechanism commissioning and visual
refinement continue; the complete world and final release are not accepted.
See the [candidate.48 native record](NATIVE-CANDIDATE48.md).

## Public download and private development

| Component | Public prerelease | Private development |
| --- | --- | --- |
| Candidate | **0.1.0-candidate.31** | **0.1.0-candidate.48** |
| Availability | Immutable Prism starter | Running owned preview; unreleased |
| Enabled mods | **197 total; 191 client; 164 server** | **198 total; 192 client; 165 server** |
| Owned server helper | Bridge 0.6.17 | Bridge 0.6.34 |
| Fresh installation | ZIP/checksum verified; clean Prism import unqualified | Matching final starter and clean import pending |
| Runtime scope | Historical named records | Startup, licensed owner join, scoped construction and native mechanisms; full multiplayer pending |

Shared mods count on both sides; Essential is optional and disabled. Both use
Minecraft 1.21.1, NeoForge 21.1.262 and Java 21. Eight shaders and one resource pack
are pinned. KG's maximum client heap is 6 GiB; Sera's conservative profile is 4 GiB.
The [development lock](../catalog/lock.json) contains 208 files and 199 mod records,
198 enabled by default. [Compatibility](COMPATIBILITY.md) preserves all 224 requested
candidates. These are development counts, not a claim that all integration work
is finished. Public candidate.31 retains its own immutable snapshot.

The private bridge is 584,264 bytes, SHA-256
`071fe778b27c9450c6a9a7b602825ee2ff19bfcdba9f23ba3cb24302bd6b4b1d`.
Its pack manifest SHA-256 is
`0e5775d8d22771e97b34b5b9f508af7baf001e6371d80588315ef08261eeed0b`.

## Work in progress

| Area | Current evidence | Remaining work |
| --- | --- | --- |
| Whole north-bank pirate city | First muted western shop/headland corrections and eastern reshaping/infill clusters have native results | Buildings must occupy most buildable ground; tightly interlock varied masses with narrow crooked alleys. Correct all rejected bright/grid extensions, retain accepted originals and household contents, and review actual views |
| Full 3D architecture | New projecting/recessed entry, window and carved details are placed; actual hall views still show plain areas | Continue exterior and sensible interior relief across every structure; no flat or boxed fallback |
| Main drawbridge | Current ornamented spans passed separate receiver repair and two actual 55-degree cycles | Normal restart, vessel clearance, player use and final visual review |
| Fountain centerpiece | Revised body passed real pumped fill, four cascades, STOP/drain/reopen in47;26 carved additions and wet composition verified in 48 | Final artwork, current operation/persistence and player use |
| Southern forest | 14 additional native saplings grew in 48; earlier durable outcomes retained | Dense continuous coverage across the entire south shore to the cliff; native silhouette/ecology and persistence review |
| Greenery LIFE | 3,284 additional southern plant/vine states placed and settled; one 396-state sector held before placement | Finish woodland and town-wide flowers, climbers, planters and undergrowth, retaining native survival and paths |
| Living LIFE | First seven animals/small creatures admitted through ordinary hooks with normal AI flags | Broader population, actual behavior/persistence and genuinely usable HOME/job POIs before town residents; firefly held for darkness |
| Station, trains and route | Mill/short shuttle infrastructure placed; retained native tube/processing partial state preserved | Correctly resume commissioning, assemble/drive trains and finish a complete route/loop; no powered-network claim from blocks |
| Hypertubes and Overpressure | Existing native links and mill installations have scoped partial records | Complete normal detector/input, power, routing, passenger travel, chunk crossings and restart checks |
| Western zipline | Detailed stations/frames and finite route source prepared | Native stocked cable creation, continuous riding/braking, streaming and restart |
| Harbor and fleet | Static flagship prototype and harbor work exist | Complete detailed fleet, furnish/inspect ships and commission actual sailing craft; static hulls do not establish mobility |
| Distant terrain/graphics | DH+SeedGen retained; strict current provider failure preserved | Exact Moonlight generated-pack custody and genuine parity, map integration, travel/shader/current resource benchmarks |

The material rule permits intentional unlimited one-axis beams, borders, fences
and roof edges. A building's same block ID cannot exceed three consecutive cells
on multiple Cartesian axes. Facing differences are not material breaks. Detail,
varied proportions and actual visual composition remain required. See the
[north-bank correction](NORTH-BANK-ARTISTIC-REDESIGN.md). Open paving is not a
substitute for occupied building footprint; tiny purposeful courts are exceptions.

## Native and source evidence

The source suite completed 911 tests in 102.480 seconds: 910 passed and one Windows
real-symlink fixture skipped. Packwiz reported 208 entries/no errors; Control Room
JavaScript syntax passed. Additional source changes have focused checks and the
release-excluded QA helper has exact-JAR compilation. Source fixtures are not
native art, player travel, multiplayer or performance evidence.

Candidate.48's fourteen grown-tree results retain two separate held plots and
all original failures. Seven requests initially left undispatched by stale
telemetry were attempted only after fresh empty-server evidence; no failed tree
was automatically retried. Tree09's earlier quarantine was resolved by exact
parent review of 29,160 retained cells, preserving two unowned water/ice phase
changes and the original quarantine/failed receipts. No world rollback occurred.

Native before-state failure also held a western path batch without placement.
Its saved unsupported gravel-over-water stacks require a separately reviewed
stable route. A later botanical sector likewise remains unplaced after its
before-field failure. These are not hidden by changing expected states.

See the [scoped runtime record](NATIVE-CANDIDATE48.md) and
[sanitized receipts](../evidence/runtime/candidate48-progress.json). The accepted
small original pirate area remains the quality reference. The whole north bank,
full forest, fleet and all mechanisms still need final review. Current screenshots
with unready client terrain are failed visual evidence, not accepted artwork.

## Release gates

Before replacing the public release: finish the requested implementation and
native visual review, qualify current operation/persistence and two-player/travel
performance, build the matching Prism ZIP and verify a clean native Prism import.
Strict SeedGen parity remains unresolved; DH server LOD downloads remain the
fallback. No fingerprint checks were relaxed and no final48 pack is published.
Useful checkpoints, human progress and failed receipts remain private and intact.
Selective staging cleanup follows completion and preserves useful recovery data.

## Historical records

Each record below applies to its named candidate and timestamp.

- **Candidate.31 release and installation:** [published prerelease](https://github.com/Kgray44/a-world-for-two/releases/tag/awft-0.1.0-candidate.31)
  and [sanitized release evidence](../evidence/runtime/artistic-release-candidate.31.json).
  The public ZIP SHA-256 is
  `3dabe6a24fe8edf03a4202afbba17ed625888678d5efcf29619d40995fa503ee`.
  ZIP/sidecar and 80 configuration files passed exact checks. Two separate fresh
  headless installs each verified 195/201 CLI artifacts and left six missing after
  DNS failures. These are preserved historical failures; clean native Prism import
  remains unqualified, without treating that old DNS failure as a current diagnosis.
- **Candidate.31 startup and approval history:** [Create startup investigation](CREATE-STARTUP-RECOVERY.md).
  The saved-world automatic resume failed on unbound `create:chocolate_bucket`.
  A subsequent unchanged recovery start was rejected by automatic approval review
  with `blocked by policy` and was not executed. Separate later private recovery
  trials are recorded in the same history; the old failure is not the current
  candidate.46 startup result.
- **Private native development:** [candidate.43](NATIVE-CANDIDATE43.md),
  [candidate.42](NATIVE-CANDIDATE42.md), [candidates.39â€“41](NATIVE-CANDIDATE39-41.md),
  [candidate.38](NATIVE-CANDIDATE38.md) and [candidates.36â€“37](NATIVE-CANDIDATE36-37.md).
  These retain real prior startup, owner login, construction, captures, native
  mechanisms and failed fountain/reset outcomes.
- **Earlier gameplay measurements:** [candidate.23 owner session](../evidence/runtime/owner-play-candidate.23.json)
  and [two-player session](../evidence/runtime/two-player-session-candidate.23.json).
  They are historical performance records, rather than benchmarks of the expanded
  town or candidate.46. The earlier 1,682 loaded-holder investigation likewise
  distinguishes holders from fully simulated chunks; it did not prove a leak.
- **Client and cinematic observations:** [dragon rendering repair](DRAGON-RENDER-REPAIR.md),
  [capture provenance](../evidence/runtime/artistic-recovery-detail-20261027.json)
  and [cinematic constraints](SETTLEMENT-CINEMATIC.md) preserve their specific
  observed cases and remaining limits.

Local monitored writers must keep 30 GiB free separately on C: and D:. This is a
monitoring/admission rule, with no quota coverage over other applications or
already-running external writers.
