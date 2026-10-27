# Native idle telemetry: lifecycle and proof limits

This additive source is intended for the candidate after the frozen candidate37
build. It does not modify that build, the bounded commissioning wake or any live
server. `ControlBridge` collects `idle_simulation` inside each existing dimension
row on its normal server-thread five-second metrics sample. Control Room uses the
authenticated/current bridge sample and the nested sample's own age; it never
borrows a fresh holder timestamp for old idle state.

The helper reads the exact native `ServerLevel.emptyTime` field using a narrowly
typed getter and the actual dimension player list plus
`ForcedChunkManager.hasForcedChunks(level)`. It enumerates no fields/methods,
loads no chunks, generates no terrain, invokes no reset and changes no simulation.
Native SavedData access may materialize already-saved tracker data in the engine's
normal cache; it does not install a ticket or alter the saved trackers. Denied
getter/branch access remains unknown rather than zero or false.

The pinned patched NeoForge21.1.262 `ServerLevel.tick` resets its empty-world timer
for native dimension players or saved vanilla/block/entity forced-chunk trackers.
Otherwise it executes the entity/block-entity section only while the pre-increment
counter is below300. Temporary region-ticket readiness is independent of this
branch. The reported label is **next normal dimension tick eligibility if inputs
stay unchanged**, not how many entities or block entities actually ticked. A
post-tick value300 may follow the last eligible tick; it cannot retrospectively
prove that tick was suspended. Tick-rate controls, chunk range and individual
entity/BE conditions still apply even when the empty-world branch is eligible.

Holder counts, completed full chunks, block-ready holders, entity-ready holders,
saved vanilla forced-chunk counts and the native saved-forcing wake status remain
separate fields with their own sample timestamps. The UI presents idle suspension
as a normal idle state, not an inferred leak, failed server or performance result.

The Java probe exercises the exact production pure branch at299/300, players and
saved-force overrides, missing getter/force inputs, and signed integer behavior.
It creates no level and does not execute the reflective getter. The Node probe
executes the actual app formatter with inert DOM/HTTP fixtures, covering real zero,
unknown inputs, stale/wrong-dimension data and escaping. Neither proves transformed
runtime getter access, live HTTP/UI rendering, native BE progress, station
attachment or throughput; those remain separate parent-controlled native gates.
