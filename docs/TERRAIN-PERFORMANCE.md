# Distant terrain and performance qualification

Status at 2026-10-28 18:30 UTC: source tooling is implemented. Current strict
SeedGen parity, map fidelity and complete gameplay performance are **unqualified**.
The master owns runtime installation, both saves and the next test session. This
lane has not launched Minecraft, modified either save or changed installed settings.

## Strict SeedGen result

The retained candidate.35 native exports were reread and verified against their
original status receipts. These are historical exports, not a candidate.49/50 test.

| Native observation | Dedicated server | Client |
| --- | --- | --- |
| Diagnostic native-format prefix | `de19e29860fac400` | `4c3a3a7d33b6c9c6` |
| Registry keys | 1,950 | 1,950 |
| Noise settings encoded | 7 | 7 |
| Density functions encoded | 248 | 248 |
| Encoding errors/exceptions | 0 / 0 | 0 / 0 |

All key sets and all 248 density-function encodings match. Exactly two registered
noise-setting encodings differ: `minecraft:nether` and `minecraft:overworld`.
Their differing JSON fields are surface rules on both dimensions and
`noise_router/fluid_level_floodedness` on the Overworld. No hash normalization,
entry omission, server-value substitution or permissive comparison was introduced.

Tectonic's selected pack must retain its native resources, overlays and corrected
position after raw mod roots. Hybrid Aquatic's wrappers and trench transformation
must run in the native server order. Lithostitched additionally changes effective
surface rules, dimension routers, biome injection and authenticated seed state.
An encoded `TransientMergedRule.original_source` alone does not describe its
effective ordered rule list. Equal codec output alone cannot prove that hidden
or seed-bound runtime state matches.

The retained candidate.42 server effective witness completed in 94 ms but recorded
29 UNKNOWN states: native codec errors, uninspected custom surface-rule internals
and unsupported-operation exceptions. There is no paired current client effective
witness. Identical UNKNOWNs cannot establish parity. Private witnesses include
native seed state and must remain outside Git and public reports.

The latest retained client lifecycle is candidate.48/bridge 0.6.34 on October 28:
resource custody refused Moonlight's exact `CachePathPackResources` provider for
`supplementaries:generated_pack`; fallback registry loading also failed, and the
original strict SeedGen gate stood down. The exact-provider repair is already
installed in candidate.49/bridge 0.6.35. No fresh candidate.49 client result exists.
Candidate.50/bridge 0.6.36 is master-owned integration work. Earlier log failures
must not be relabelled as its result.

`python -B -m tools.terrain_parity fingerprint --server <status> --client <status>`
compares bounded, hash-bound original diagnostic files. `effective` compares the
native effective witnesses and their exact owner-thread custody receipts. Both
always report `strict_parity_proved=false`: they provide evidence, never a runtime
generation permit. Changed data, missing value hashes, duplicate records, encoding
failures, stale custody and UNKNOWN states refuse equality. Output omits private
encodings and seeds.

The next real test must use the exact master-selected candidate on both ends and
retain: full modded load; complete ordered resource custody; native startup and
authenticated phases; original strict packet acceptance; current, paired effective
witnesses with no unresolved coverage; real LOD arrival; and full-chunk terrain
comparison. If a provider or native phase refuses, retain the first failure and
server DH fallback. Do not replace a missing result with a fixture.

## DH, MapHorizons and Xaero

A bounded read-only metadata query of the actual construction Overworld and KG
client DH databases found the same source counts:

| Database detail | Native source rows on each side |
| --- | ---: |
| 0 | 5,888 |
| 1 | 1,472 |
| 2 | 368 |
| 3 | 92 |
| 4 | 31 |
| 5 | 9 |
| 6, 7, 8 | 4 at each detail |
| Total | 7,872 |

The client database was 158,396,416 bytes; construction Overworld database was
157,958,144 bytes. Counts are metadata evidence, not equal payloads or visual
acceptance. A separate attempted all-row checksum-metadata query exceeded its
one-second progress deadline and was interrupted; full checksum comparison is
unresolved. No timeout was increased to turn that attempt into a pass.

These objects have distinct meanings:

- A FULL Minecraft chunk contains authoritative blocks, entities and gameplay
  state. Loading or generating it is a real server operation.
- A DH source is a visual LOD representation. Database detail 0 covers a 64 by
  64 block section; detail d covers `64 * 2^d` blocks per side at coarser sampling.
  The native section detail is database detail plus 6. A source is not a discovered
  chunk, and a coarse source must not be expanded into fictional fine data.
- A MapHorizons tile is a rendered view of available native DH data. The adapter
  preserves native sampling, leaves unavailable sources as holes, and gives real
  Xaero terrain precedence. It cannot repair incorrect prediction.
- Map visibility and explored records are separate. The inspected server settings
  allow a full atlas (`teamScoped=false`, `showUnexploredTerrain=true`). Seeing that
  terrain is not evidence that anyone visited it. FTB Teams support does not imply
  Open Parties and Claims privacy or exploration authority.

The pinned `maphorizons-1.1.0-awft.2.jar` and its retained original source were
inspected read-only. The terrain highlighter returns colors through Xaero's native
highlight path and checks its genuine discovery height before painting. Existing
exploration payload/state code is separate. The source establishes the intended
separation; before/after native map views, real-discovery precedence, unchanged
exploration bits, denied visibility, dimension transitions and reconnect remain
required runtime tests. Do not equate matching database row counts with these tests.

SeedGen's author explicitly describes approximated trees/features and requires
matching worldgen mods/data for multiplayer; it stands down when prerequisites
fail. [Author description](https://modrinth.com/mod/distant-horizons-seedgen).
MapHorizons describes its highlight/exploration boundary in its
[pinned README](https://github.com/VolcanicMG/MapHorizons/blob/6c80ad5be5fff2c373388dfd6ff433667edd7217/README.md).

## Performance evidence and recommended settings

There is no completed current-candidate configuration comparison yet. Historical
candidate.23's five-minute real two-player observation is useful evidence of a
problem, not final-pack acceptance:

| Historical measurement | Observed result | Interpretation |
| --- | --- | --- |
| 26 fresh two-player server samples | TPS median 19.998; sampled mean MSPT median 11.740, maximum 22.549 | Individual tick spikes were not measured by those means. |
| 19 local focused game-screen snapshots | KG FPS median 22, range 14–27 | Not reasonably smooth in that observed session. Shader attribution was uncontrolled. |
| Unbound 5.9.3 HIGH reload log interval | 44.771 seconds; KG timed out; process survived | Observed reload-associated stall; cause not isolated. |
| Later Reimagined 5.9.3 HIGH reload interval | About 0.992 seconds | Separate uncontrolled interval, not a measured shader speedup. |

Source: [retained two-player record](../evidence/runtime/two-player-session-candidate.23.json).
Four stale samples were excluded. Sera's FPS, RAM and exact client hashes were not
observed. Neither 20 TPS nor the later owner's 60 FPS observation proves low latency.

Use the [unapplied balanced and higher-quality starting presets](../proposals/terrain-performance/graphics-presets.json).
Balanced starts at 6/4 vanilla render/simulation, 64 DH chunks, one half-duty DH
worker and shaders off. Higher quality starts at 10/6, 128 DH chunks, two half-duty
workers and Reimagined Medium, with a shaders-off control. Retain the existing
8 GiB server/6 GiB KG maximum heaps for the first comparable run only if live host
headroom admits it; Sera's proposed 4 GiB start requires her hardware measurements.
Do not raise heaps to consume all laptop RAM.

The server fallback retains `SURFACE_THEN_CHUNKS`, `SURFACE`, unhealthy-server
limiting and existing conservative request rates. One earlier bounded clean stop
is not repeated lifecycle acceptance. SURFACE can omit unvisited decoration;
full player-driven chunks and their updated LODs remain authoritative. Shader
switches should be coordinated outside active multiplayer until the timeout case
is qualified. Kappa's pinned archive lacks DH terrain/water programs; do not select
it as the qualified distant-terrain preset. Other shader program presence is only
a prerequisite, not measured compatibility.

## Instrumentation and bounded runtime procedure

`compat/performance/TickWindow.java` is an unapplied helper for master integration.
Its five anchored ControlBridge edits add per-window tick max/p50/p95/p99, exact
threshold counts and separate tick-start gaps. Overflow preserves count, mean,
maximum and threshold counts while withholding incomplete percentiles. Cross-window
stalls remain visible. The helper does not alter any tick, registry or generation
rule. The Java 21 fixture uses 64 MiB/two CPUs and is synthetic only.

`tools.performance_handoff` creates a fresh private source/patch/fixture receipt;
it installs nothing. Master copies the helper into active bridge sources, reviews
the diff against the current ControlBridge, builds one new immutable candidate,
and retains the prior artifact/configuration rollback. Current API aggregation
does not forward the added field, so the passive recorder reads the native file.

`python -B -m tools.performance --window <master-window.json> --seconds 120`
records an existing session only. The explicit window binds candidate, pack,
two real JVM process generations/cwds, workload, configuration and expiry. It
never starts/stops games, sends commands, changes graphics or moves players.
Output is a unique `H/staging/terrain-performance-*` folder, capped at 12 MiB
sample data inside a 16 MiB allocation, with both-drive ReserveGuard checks.
Source capture does not control the running games' separate allocations.

It records native TPS/window means, available tick spikes, sampled client frame
windows, heaps/GC counters, process RSS/CPU-time/I/O, per-core host load, physical
RAM, Windows commit headroom/page-in rates, shared GPU use and bounded directory
sizes including WALs. Repeated native snapshots are deduplicated; stale or foreign
process data stays unavailable. Menus/focus states stay separate. Window percentiles
cannot be pooled into an invented global frame percentile. Windows page-ins also
include file-backed memory and do not by themselves prove pagefile thrashing.

Master supplies current approval out of band; a JSON file is a provenance record,
not an operating-system lock or independent authority. Its minimal schema is:

```json
{
  "format": "awft-passive-performance-window:1",
  "coordinator_chat": "01a17947-1d00-7fd1-aa5e-d1fb514f8671",
  "operation": "passive-telemetry",
  "begins_at": "REPLACE with coordinated UTC start",
  "expires_at": "REPLACE with UTC expiry, within 30 minutes",
  "candidate": "REPLACE with exact installed candidate",
  "pack_sha256": "REPLACE with exact installed hash",
  "server_home": "D:\\A World for Two\\staging\\world-tests\\20261027T053650Z-artistic",
  "client_root": "D:\\A World for Two\\instances\\AWFT_Check_20261026_214756",
  "workload": "REPLACE with actual actors/route/machine state",
  "configuration": "REPLACE with actual settings and resolution",
  "processes": {
    "server": {"pid": 0, "created": 0, "cwd": "REPLACE with H/server"},
    "client": {"pid": 0, "created": 0, "cwd": "REPLACE with client/.minecraft"}
  },
  "watch_directories": {}
}
```

Each slice is at most ten minutes. Suggested actual slices are 60–120 seconds
idle; 120–180 seconds current city/LIFE and forests/habitats; 120 seconds operating
Create; separate train and ship routes; fast movement through approved new terrain;
bounded DH generation; coordinated shader transitions; and a real two-player route.
Machines/routes/populations must be commissioned and present before labelling
their workload. The final population target is not represented by today's small
cohort. Chunk generation/load spans require actual native profiler events or
timestamped arrival measurements; loaded-chunk counts alone cannot supply them.

For comparisons keep the actual resolution, power mode, world/checkpoint, route,
population, machines and warm-cache state fixed. Preserve caches rather than
deleting evidence to manufacture a cold run. Take config byte/hash rollback
checkpoints before master changes, and retain each failed/refused result. Check
both drives and memory before each slice; player arrival, exhausted reserves or
unresolved native ownership ends admission. Only the master handles game shutdown.

## Release decision

Do not qualify a final distant-terrain release yet. Retain strict SeedGen refusal
and real server-generated DH fallback. Remaining gates are current native parity
or explicitly accepted exact limitation, map/discovery fidelity, matched gameplay
comparisons with spike evidence, two-player transport/forest/city workloads,
shader transitions, restart/cleanup, and KG/Sera acceptance. Passing source tests
and an installed adapter do not close these gates.
