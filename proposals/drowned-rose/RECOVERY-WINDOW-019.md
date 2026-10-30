# Recovery-only native entity-load window in0.1.9

Actual0.1.8 startup and managed-seat registration passed, but Root's four repair
commands all refused `original_chunk_entities_not_loaded:1280,65,-1280`.
The temporary block-read verification supplied FULL blocks, not loaded entity
storage. No identity was inserted. The original body/UUID/NBT gates stay intact.

The correction provides only `awfttavern prepare-recovery` and
`awfttavern finish-recovery`. Preparation requires a paused tavern scheduler,
zero real server players, admittedb296 layout/existing45 ledger and the exact
336ba5 four-missing census. No ordinary activity acquires tickets.

The helper first asynchronously reads the saved FULL headers for the36-chunk
support halo X78–83/Z−83–−78, all inside existing MCA region2/−3. The authenticated
336ba5 source independently contains all36 as FULL; current native saved headers
must also match before any ticket is added. Native `getChunkFuture(FULL,false)`
requests use existing chunks. No block writes or generation requests are made.

Exactly4 temporary tickets are owned:80/−81,80/−80,81/−81,81/−80. The helper uses
the pinned NeoForge5-argument `addRegionTicket(type,chunk,2,chunk,true)` and matching
remove call, as the existing Native LIFE helper does. Native engine support
neighborhoods are implicit; only these4 ticket centers are explicitly acquired.
There are no future `join/get` calls or shared-future cancellation.

Root sequence:

1. Suspend the scheduler with the existing command and confirm no real players.
2. Send `awfttavern prepare-recovery` once. The nonrenewable20-second total
   wall-time deadline begins at this preparation, including saved-header checks.
3. Read actual in-memory `awfttavern status`. Require `recovery_window.ready=true`,
   all4 FULL/entity-storage flags true and pending native futures0. File telemetry
   updates every5seconds and can lag; elapsed time alone is not readiness.
4. Within that window run the same3 exact-NBT restore commands and1 explicitly
   labelled Niamh profile reconstruction from the0.1.8 handoff. All original
   collision, identity, raw-file, ledger, proof and fixed-location gates remain.
5. Send `awfttavern finish-recovery`. Require activefalse, owned temporary
   tickets0, pending native futures0 and cleanup_requiredfalse. If cleanup is
   still draining, poll until genuine0. Do not infer completion from command sent.

Any context change, native future failure, repair refusal,20s expiry or server
stopping releases all owned tickets. Native tickets independently expire after
400ticks. Deadline expiry is checked on the server thread and again before every
insertion; a stalled server services cleanup at its next tick. Finish remains
available to release owned tickets even after a context change. Pending shared
native futures are observed until done, never cancelled or misreported as zero.
Already inserted original identities are retained if a later repair refuses.

The validated final artifact is
`D:\A World for Two\staging\drowned-rose-source-20261029\compile-45-0.1.9-validated\awft-tavern-0.1.9.jar`,
103,019bytes, SHA256
`46ff975cf7481b2ab6971522b27770012cc49f6a9ec010aed55575043ff5a03b`.
Use the same file on client/server. Its new private FINAL-HANDOFF.json SHA is
`25b3a218cb5f9dfac4420ac6de23da429b3e53dbd5471cd86118e1ed6193e312`.
The preliminary41193a build is uninstalled and superseded; all artifacts remain.

Four focused suites pass: window lifecycle/readiness/TTL/fault/cleanup with fake
native access; real native NBT/profile/proof validation; native-A* synthetic
detour tests;45,000 policy transitions. The0.1.8 OriginalRecovery, native path,
seat, client pose, roster and skin bytes are unchanged. Actual native ticket
readiness/cleanup, successful restoration, seat save/reload, music and gameplay
performance still require Root's running-game evidence. This source chat has
issued no live command or UI action.
