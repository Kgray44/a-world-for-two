# Disposable worldgen observer

This original helper is excluded from every release. It has **compiled only**;
no native execution result is claimed. Build without starting/installing Minecraft:

```powershell
python -B -m tools.worldgen_qa
```

The source/API/JAR receipt stays under
`D:/A World for Two/staging/worldgen-audit-builds/<id>/`. Java21.0.10 and the exact
installed Minecraft1.21.1/NeoForge21.1.262 compile APIs are required. Failed build
diagnostics and earlier build outputs are retained.

The master controls all runtime windows. After an explicit lease, an owned server
under `D:/A World for Two/staging/worldgen-audit/<lease>/server/` may use
`-Dawft.worldgen.qa=true` with loopback25585, online authentication enabled, no
players, unchanged saved seed and height. A `worldgen-test-owner.json` must contain
`purpose=awft-worldgen-disposable-ab:1`, a unique `id`, the actual `lease_id` and
the master's thread ID as `master_thread`. The private `worldgen-plan.json`
contains matching `owner_id`/`lease_id`, actual `lease_expires_at_epoch_ms`, unique
`run_id`, `seed_sha256`, `arm` (baseline/updated) and `phase` (scan/full/restart).
These files must come from the real granted window; inventing a lease marker
does not authorize a test.

Save identity is fixed to `test-worlds/<arm>` below that exact server directory.
For `scan`, provide up to eight `[chunkX,chunkZ,widthChunks]` windows (width32..512)
and up to sixteen `structure_sets`. Only native `RandomSpreadStructurePlacement`
instances with spacing>=32 are supported. Custom algorithms must be measured
separately rather than emulated. Native feasible points are not placed blocks.
For `full` and `restart`, provide the same explicit `chunks` list in every arm,
maximum384 coordinates. The plan and helper remain private; never commit a seed,
world, downloaded JAR, account or raw log.

The helper emits unique scoped reports with actual loaded registry values,
expanded biome holders, surfaces/floors, saved starts/piece boxes and block hashes.
Generation acquisition time is separate from hashing/observation overhead. Tick
samples include that overhead; they are not pure uninstrumented performance.
Player arrival, expired authority, timeout or an observation exception stops the
test and preserves its failure. It never sends a forceload command. An observation
completion is not normal-stop or process/port-cleanup proof. The orchestrator
must perform a normal stop and verify real descendant/resource exit separately.
Absent opt-in leaves the helper inactive. A misplaced helper cannot stop an
unowned runtime: that authority is acquired only after the leased disposable
save/root/port match. Startup failures cannot overwrite earlier receipt files.

Use `tools.worldgen_results` only with genuine full/restart reports and the exact
loaded helper artifact. It refuses changed seeds, height, chunk inventories,
unexpected registry edits and partial receipts. It always leaves visual,
frontier, sustained/multiplayer performance and strict SeedGen acceptance open.
See `docs/WORLDGEN-FUTURE-TERRAIN.md` for the master handoff and deployment gates.
