# Build and acceptance status

**Documentation checkpoint: 2026-10-28 UTC.** Public candidate.31 remains the
published immutable prerelease. Private candidate.46 reached native readiness,
stopped and saved normally, then restarted for a private preview last observed
ONLINE on port 25575. The licensed owner client then authenticated and joined;
full gameplay and final release acceptance remain open. See the
[candidate.46 recovery record](NATIVE-CANDIDATE46.md).

## Public download and private development

| Component | Public prerelease | Private development |
| --- | --- | --- |
| Candidate | **0.1.0-candidate.31** | **0.1.0-candidate.46** |
| Availability | Published immutable Prism starter | Private preview observed online; unreleased |
| Enabled mods | **197 total; 191 client; 164 server** | **198 total; 192 client; 165 server** |
| Owned server helper | Bridge 0.6.17 | Bridge 0.6.32 |
| Fresh installation | ZIP/checksum verified; clean Prism import unqualified | Final starter and clean import pending |
| Runtime scope | Historical records below | Startup, normal save/stop, restart and one licensed owner join; broader gameplay acceptance pending |

Shared mods count on both sides. Essential is optional and disabled. Both use
Minecraft 1.21.1, NeoForge 21.1.262 and Java 21. Eight shaders and one resource pack
are pinned. KG's maximum client heap is 6 GiB; Sera's conservative profile is 4 GiB.

The [development lock](../catalog/lock.json) now tracks candidate.46: 208 files,
including 199 mod records with 198 enabled by default. The published candidate.31
starter retains its immutable snapshot. [Compatibility](COMPATIBILITY.md) preserves
all 224 requested candidates, including unresolved alternatives.

The compiled private bridge is **558,236 bytes**, SHA-256
`5a40c5a968645d10a94efde647c197f73f1f3381a972f29fd04fe24a200eb6ce`.
Its private pack manifest SHA-256 is
`0daa15709f5300f42c64f4e794418ffb06c38b270c4e612c34ef67c18aeae370`.
Compilation, focused source tests and API fixtures are separate from native
startup, current-world persistence, gameplay, performance and owner acceptance.

## Work in progress

| Area | Evidence already available | Still required |
| --- | --- | --- |
| Continuous north-bank pirate village | Several private building groups, shops, streets and furnishings have actual placement/readback results | Fill the remaining qualified dry land coherently; verify connected routes and complete interiors; review the whole village in game |
| Full 3D architecture | Native depth layers exist across neighborhoods, castle, mill and maritime builds; further sources preserve routes and inventories | Finish projecting/recessed exterior details and sensible interior ceilings across every structure, then review actual views |
| Main drawbridge | Earlier private builds completed real powered 55° cycles and restart checks; fixed ornament has native results | Admit new moving ornaments against current glue custody, then repeat physical cycles and restart checks |
| Fountain centerpiece | Refined R5 sculpture is placed with native geometry verification | Complete the new sculpture's powered fill, four-jet flow, STOP/drain/reopen, restart and artistic review |
| Native woodland | **Seven native-grown outcomes are durable; an eighth lost all 36 owned changed cells in the crash and remains unreplayed** | Continue broader forest coverage and canopy/route/structure clearance review; retain the lost attempt and failed receipts |
| Botanical greenery | Separate authored recipes cover flowers, climbers, window planting, hedges and supported boughs | Complete placement, native survival/settling and visual review across town and woodland |
| Living LIFE | Guarded habitat/resident sources and admission controllers are prepared | **No curated LIFE cohort has been spawned**; complete current habitats/census, native admission, persistence and behavior checks |
| Cliff-to-town zipline | Western route, detailed stations/frames and guarded native cable controller are prepared | Actual loading, real stocked cable creation, continuous riding, braking, streaming and restart proof |
| Mill and transport demonstrations | Partial native mill/tube construction and separate engineering recipes exist | Complete working recipes, train/tube interaction, restart and performance commissioning |
| Distant terrain and graphics | Distant Horizons + SeedGen retained; earlier mapping/client observations preserved | Strict current client/server SeedGen parity, coarse-only map coverage and current graphics/travel benchmarks |

The hard material rules apply to complete authored buildings: a single block ID
may exceed three consecutive blocks on at most one Cartesian axis, and no
unbroken material run may exceed nine on any axis. Different facing properties
are not material breaks. Real depth, irregular human-scale streets, decorations
and atmosphere remain part of the artistic brief.

Botanical greenery and living LIFE are separate passes. Native-grown tree
outcomes and any naturally generated occupants need their own census; they are
not a curated animal or resident population. Sources, masks, inventories and
native placement counts do not establish a finished, inhabited settlement.

The owner's visual approval applies to the small pirate-town area used as the
quality reference. Full-scope artistic acceptance remains open. Existing game
images are unchanged historical captures of their named candidates and camera
views. See [artistic recovery](ARTISTIC-RECOVERY.md),
[botanical art](ARTISTIC-BOTANICAL-PASS.md), [whole south bank](WHOLE-SOUTH-BANK-FOREST.md),
[forest rollout](FOREST-ROLLOUT-AND-UNDERSTORY.md), [living landscape](SETTLEMENT-LIFE.md)
and [fountain recovery](FOUNTAIN-CENTERPIECE-RECOVERY.md).

## Runtime and release gates

Candidate.46 reached actual readiness around 04:35 UTC, then completed a normal
stop and verified clean checkpoint. A second private preview JVM was observed
ONLINE. One warmup interval measured 20 TPS and 2.12 ms/tick; this is not a travel,
multiplayer or sustained-performance benchmark. The clean checkpoint contains
637 source files and has SHA-256
`4384206f639659b09b2d332d2eb058241ca6dc15298f3808745025ed85992fac`.

The read-only crash audit retained all 37 eastern houses, 10 western buildings,
the western streets and the 118-target Rose exterior addition. Only two already
authorized bed cells differ within the compared architecture groups. Seven tree
outcomes are durable; the eighth outcome lost its 36 owned log/leaf changes and
has not been automatically replayed. No curated LIFE cohort has been spawned.

The source suite passed **754 Python tests in 69.998 seconds**, 208-entry Packwiz
validation and Control Room JavaScript syntax checking. The corrected tree-scope
snapshot passed a collection-only 131,072-key probe in **158.380 ms** under a
256 MiB heap/two-CPU bound. That probe created no native world. Its source fix and
candidate.46 startup do not qualify a complete forest or general performance.

The build also includes bounded cable preparation and read-only bridge inspection
using the shared maintenance interlock. Their source/API checks do not establish
a live ride, new bridge motion or current multiplayer acceptance. Exact scope is
in the [curated recovery evidence](../evidence/runtime/candidate46-recovery.json).

The fountain's real pumped flow in candidate.42 remains valid historical evidence
for that earlier geometry and run. It does not qualify the revised R5 centerpiece
or candidate.46. Likewise, earlier owner connections and two-player sessions keep
their original pack/world scope. Current startup, travel, input responsiveness,
shader switching and resource measurements must be recorded separately.

Strict SeedGen agreement is still unresolved. DH server LOD download fallback
remains selected while current native client/server parity is verified; Voxy and
Roxy remain excluded. [SeedGen history and limits](SEEDGEN-RUNTIME-GAP.md) retain
the exact earlier mismatch. A source repair alone does not establish agreement.

Before a replacement public release: finish the remaining implementation and
native review, produce the matching Prism starter, verify its pinned Packwiz
installation and clean native Prism import, then record matching multiplayer and
performance results. No candidate.46 final release is published by this update.
Useful recovery checkpoints and failed receipts remain preserved; selective
staging cleanup follows completion and acceptance.

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
  [candidate.42](NATIVE-CANDIDATE42.md), [candidates.39–41](NATIVE-CANDIDATE39-41.md),
  [candidate.38](NATIVE-CANDIDATE38.md) and [candidates.36–37](NATIVE-CANDIDATE36-37.md).
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
