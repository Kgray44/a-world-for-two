# Original public R4: current persisted READY, then normal creation

Additive from the frozen publicR3 controller SHA
`403f7180016f1e69e5b6c57b6948846e505bdfec420f3fcc8d184ca803ead069`.
R3 and its producer are unchanged. No private predecessor or literal world seed
was used. The controller API remains constructor/commands/tick/stopped/busy.

The explicit NEW `awftchains prepare-create <bundle> <sha>` uses format
`awft-native-chain-route:2` and an exact `ready_policy`. Old `create` still uses
format1 and REFUSES if all217 are not already FULL. Passive inspect stays passive.

One exclusive lease spans every phase. Before ANY ticket or simulation wake,
prepare-create reads CURRENT persisted NBT through public `chunkMap.read`, which
delegates to `IOWorker.loadAsync`. The native5×5 union AND the whole ticket/light
halo are checked. The halo is derived from actual `ChunkLevel.MAX_LEVEL`, the
distance2 ticket level, the loading-pyramid accumulated FULL dependency radius,
and an extra light-neighbor ring. No guessed217-to25 extrapolation is used.

Every current persisted result must exist and have exact coordinates,
DataVersion3955, FULL status, nonempty bounded sections and correct light data;
retrogen, unknown or oversized results refuse before ticketing. At most4 reads
are outstanding. Tags exceeding4MiB heap estimate or a256MiB cumulative scan
budget refuse; results are reduced to bounded metadata and released promptly.
The underlying Minecraft reader allocates a tag before its size is observable;
the controller does not claim it reconfigures that allocator. It retains at most
four result handles and refuses oversize data instead of promoting it.

The derived radius is capped16 and read set4096 columns. Persisted reads have a
45second wall deadline; the complete prepare-create has1800tick/90second bounds.
Unknown required halo never falls back to generation. `create=false` alone is
explicitly NOT treated as a no-generation guarantee: the current stored-FULL,
version/lighting/dependency checks are the prerequisite.

After all persisted data passes, the SAME lease adds only the finite existing
endpoint region tickets. Actual native holder readiness (`hasChunk`) precedes
one queued FULL request per proved217 cell. The controller waits for actual FULL,
then rechecks R3 geometry/chronology, stock, tags, configs, occupancy, saved census
and current world custody. Only then does the unchanged15-native-UUID durable
intent, normal additions and14-real-chain-debit/attach body run. No standalone
READY lease gap, fake player, copied entity NBT, UUID replacement, refund or replay
was added. Final ride/streaming/physical acceptance remains separate.

Finish/cancel/stop keep the controller busy until owned persisted/load futures,
ticket handles and the lease are clean. Cleanup never wakes idle simulation or
cancels shared I/O futures. Immutable terminals publish first independently from
the mutable view; publication failure retains `RECEIPT_BLOCKED` as in R3.

`tools/artistic_chain_route_request_r4.py` is the NEW producer. It preserves all
real prior native proof requirements and emits the READY policy without inventing
any live persisted-read or loading result. The installed R4 class is required.
All generated evidence/requests stay private; no command is submitted by Python.

Parent integration must keep the interlock exclusive without implicit wake in
its data-only lease acquisition. Actual45 interlock is advisory and does not
wake; prepare-create requests that initial lease with simulation=false and only
explicitly wakes after complete persisted validation. Include `busy()` in all
other maintenance gates and wire the new typed console operation deliberately.

`ReadyNbtProbe.java` is a tiny offline actual-NBT API fixture. It constructs no
Level, fake player, entity or world. A compilation or fixture pass does not prove
current world halo presence, native loading, cable creation, restart or riding.
