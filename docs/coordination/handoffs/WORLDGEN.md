# WORLDGEN integration checkpoint

Owner: **Refine future world generation**,
`01a183b8-961e-77b3-bf51-077fc8b7a610`. Branch `codex/worldgen-future-terrain`,
base `3333bc60646cc594093063ed514a3e51246e35b0`.

Scope: four-set future-terrain structure-spacing proposal; pinned resource and
biome eligibility audit; comparison/native-observation tooling. No shared catalog,
active Packwiz, runtime or save writes. Master maintains WORKSTREAMS.md.

Integration instructions and full before/after evidence boundaries:
[WORLDGEN-FUTURE-TERRAIN.md](../../WORLDGEN-FUTURE-TERRAIN.md).

Selected change is the master's existing `proposals/future-structure-frequency/`
diff, reproduced exactly into this branch. Castle96->92; adobe/pottery/school80->76.
Generated review datapack: `proposals/worldgen-four-set-v1/`, all files hashed.
Forty-one other baseline overrides, every salt/separation/exclusion, terrain
settings, height, seed and every requested compatibility record remain intact.
The earlier broader experiment is held outside the integration commit.

Tests: 967 total source tests, 965 passed and two Windows link-fixture skips;
eighteen targeted worldgen tests passed; 208-entry pack validation, JS syntax,
four session tests, exact master-proposal verification and actual Java21 API
compilation passed. No source test failed. No Minecraft test has run in this lane.

Measured synthetic result: selected candidates1228->1344 (+9.45%) across eight
fixed512x512-chunk windows, using the archived306 construction seed read-only.
All39 supported unconditional grids8366->8482 (+1.39%). No native performance,
collision, terrain-fit or generated-count result is claimed.

Second checkpoint adds actual historical saved-world observations:2,450 FULL
chunks,20,421 partial chunks,627,200 surface columns and37 valid saved structure
starts from verified306. A private all22,871-record payload/status inventory is
retained; the committed report is sanitized. Terralith/RU/river/coast/ocean content
exists in this old constructed footprint; no updated native A/B or timing follows.
The reusable reader's first zero-length-MCA-header failure and correction are
preserved. All18 current focused tests pass. No new Minecraft process ran.

Dependencies: TERRAIN-PERFORMANCE chat `01a183b9-759d-7161-b786-b9149472d8b0`
was sent the exact scope and strict-parity requirement. Both endpoints must use
the same Paxi resources. Existing DH fallback and strict SeedGen checks stay.
Static audit resolves132 structure sets; Supplementaries generated biome tags
and vanilla-only filters remain explicit unresolved boundaries.

Next required master action: schedule one exclusive disposable A/B window after
its current city/LIFE installation. Requested port25585, one3GiB JVM at a time,
C<=32MiB/D<=3GiB forecast subject to fresh preparation bounds and reserves;
no save copies or competing Minecraft JVM. The full run/stop conditions are in
the report. A native helper exists privately but is not installed or released.

Offline follow-up:1,440 actual pinned Minecraft RNG/spread primitive vectors
match the Python candidate sampler, zero mismatches, one CPU/192MiB heap, no mods,
bootstrap, server or save. The direct full-placement constructor requires native
Minecraft Bootstrap and its failed attempt is preserved; no native-placement
claim follows from the primitive check. `tools.worldgen_grid_probe` reproduces
the passing arithmetic check. Current native A/B window remains ungranted.

Unfinished: real representative-region counts, terrain/entrance/collision review,
fresh-chunk/per-tick measurements, normal restart, explored-frontier preservation,
native client/server parity, visuals, multiplayer and master deployment. These
are required gates, not accepted limitations. Do not mark this lane complete.
