# Native Moonlight initialization proposal

**Uninstalled and not runtime qualified. Strict SeedGen parity remains unproved.**
Performance PR2 is frozen at `43c2f3a39443b0220feebf09eac182a2b41bb212`.
This separate proposal addresses the fresh candidate50 primary failure:
`Moonlight server-data cache is not initialized; never infer empty` for the actual
`supplementaries:generated_pack`. Existing cache files alone do not initialize the
native provider delegate. Later vanilla/fallback registry errors are separate.

The hook wraps the original `MultiPackResourceManager` construction in pinned
SeedGen0.9.1 `attempt(ZZ)` **before either registry load**. It retains the exact
opened object identities and order, and invokes the exact Moonlight3.7.2 native
SERVER_DATA handler with those resources. The native handler refreshes its cache
strategy, prepares the original registered provider, reloads using its own
external-pack/filter branch, and publishes native state. No synthetic resources,
delegate assignment, empty-resource assumption, terrain replacement, fingerprint
override, changed codec, hash normalization, or relaxed comparison is introduced.
The existing Tectonic order and Lithostitched/Hybrid Aquatic hooks stay intact.

Only the exact reviewed Supplementaries4.0.2 provider and its one native generation
task are admitted. The installed Moonlight, Supplementaries and SeedGen JAR bytes
and versions must match. Additional SERVER_DATA providers require review. All six
client observers must be present. Asynchronous native debug dumps are refused.

Moonlight normally catches some task/serialization/recipe failures and can commit
partial data. Observers latch those errors without changing native results; the
pre-publication check rejects them. It verifies generated last-write bytes through
the original provider, the existing strict Moonlight delegate view, stable native
namespaces, and the full existing raw/selected/effective resource attestation.
After return it repeats custody and order checks. This is resource preparation;
the original SeedGen compatibility comparison must still succeed independently.

Before native preparation, a private backup retains the original entire
`dynamic-data-pack-cache`, including its existing hash. A forced pending marker in
`awft-private/moonlight-native-preparation.pending` blocks later attempts across
client launches if preparation fails. Blocking new state publication alone would
be insufficient because an old matching native hash may survive a failed rebuild.
Only successful preparation/custody removes this operation's exact owned marker.
Failure retains the backup, marker and partial native output. There is no automatic
restoration, marker deletion or retry. The owner reviews the stopped client and
backup before manual recovery. Existing DH server-generated fallback remains the
release path while parity is unproved.

## Bounds and verification

Native preparation admits at most32MiB prior cache contents,4096 backup nodes,
depth32; at most32MiB produced resource bytes,32MiB cumulative cache writes,
4096 resource IDs and1024 output directories. Replacement writes count again.
Filesystem allocation blocks must be at most64KiB. A conservative **1GiB maximum
additional allocation on the actual game drive** covers bounded contents and
node/block overhead, retained backup, hash and receipts. C: and D: separately
retain30GiB. The master must run ReserveGuard with that forecast before installing
and exercising this writer. Native admission checks the reserve again and requires
1GiB free physical memory. The60-second deadline is cooperative; it cannot preempt
a stuck native codec or filesystem call. This is not an OS quota and cannot limit
external applications or existing writers.

`native_api.py --mods <installed server mods>` inspects exact JAR class files
without a JVM, downloads, extraction or native generation. It verifies the actual
constructor/registry call order, native lifecycle and absorbed-error injection
sites. `probe.py --home <owned construction staging home>` performs a bounded
Java21 API compile (256MiB,2 processors) and a separate pure policy/gate fixture
(64MiB). It uses the actual installed runtime dependency order. The MixinExtras
compiler reference is copied from the installed NeoForge JAR into a new private
probe directory. No modloader, Mixin transformer, Minecraft bootstrap, world,
account or network is executed. Refuse below1.5GiB physical or commit headroom.
The probe forecasts2MiB on C: and64MiB on D:; it preserves failed receipts.

The Java fixture covers partial-failure latching, duplicate resource cost, byte
and node/depth limits, concurrent producers, deadlines, marker persistence across
attempts, refusal to replace an existing gate and refusal to delete a changed gate.
API compilation and class-file inspection do **not** prove Mixin transformation,
native generation, fingerprint equality or correct predicted terrain.

## Master integration and runtime qualification

1. Review the source proposal. Copy initialization/pins/budget/gate into the bridge
   package, and the six `*Mixin.java` files into its mixin package. Merge only the
   names in `mixin-entries.json` into the existing **client** array. Keep the probe
   and fixture outside the deployed JAR. The master owns all active bridge,
   version, catalog, Packwiz, build, installation and runtime changes.
2. Run existing bridge/pack checks and create an exact candidate rollback receipt.
   Use an explicit exclusive client test window. Never touch the permanent world.
   Run ReserveGuard with C:0,D:1073741824 if the game remains on D:, plus separate
   bounded build/install forecasts; retain a stopped cache/config checkpoint.
3. Verify all exact Mixin targets and observer counts apply. Boot failure or a
   refused initialization is a failed candidate. Do not remove a required observer
   or weaken a comparison to pass it. A normal generation refusal must retain its
   gate/receipt and the original SeedGen/DH fallback behavior.
4. On genuine success, capture fresh server/client resource inventories,
   fingerprints, selected pack order and current effective terrain state. Confirm
   the native strict gate accepts them. Any subsequent mismatch or UNKNOWN remains
   an unresolved incompatibility; this proposal proves no equality by itself.
5. Use owner-controlled bounded movement in an unused private test area to compare
   SeedGen prediction, eventual FULL chunks, DH LODs and maps. Distinguish LOD/map
   rendering from exploration records; check records before and after. Measure
   client frametime spikes and host physical/commit headroom during generation.

Do not ship this proposal as a verified SeedGen repair until those steps pass.
