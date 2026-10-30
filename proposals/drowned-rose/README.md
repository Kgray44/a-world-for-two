# The custom Drowned Rose: current staging status

0.1.14 is prepared for the coordinating chat's matched server/client restart.
Its artifact SHA256 is
`82c0bbe1bedae4736880b9aba34c10b0b6f4136167be959c9a078181492c2854`.
This targets the large custom tavern in northern eastern Tortuga, directly south
of the two imported buildings. Keep the existing 45-resident ledger and admitted
b296 config; no initialization or identity recovery is needed.

The completed 0.1.12 trial established:

* All 45 patrons saved and observed loaded with their existing identities.
* Real seated pixels with bent legs on a green cushion; a native sample of 117
  chair exits and 4 blocked-exit waits.
* Four native instruments visibly held/played, matching arm rotations and
  recent native note activity. This does not establish heard audio.
* 147 completed native drink uses; the actual sipping pose remains pending.
* All 10 inherited stuck patrons cleared with exactly 10 existing gated recovery
  commands, without respawning. All 10 predated the guarded-exit installation.

The actual 0.1.13 trial hit AccessDeniedException during atomic status-file
publication. The scheduler latched a fault and paused; later fresh status did
not clear that pause. Its obstructed Ada images and QA camera angles do not
establish accepted micro-motion or sipping. 0.1.14 adds bounded retry of that
Windows rename failure on the existing background writer. Persistent errors
still fault and pause. Compilation and focused Windows checks pass; actual
heartbeat recovery and ordinary activity await the matched runtime trial.

On healthy load, the admitted config starts unpaused with an empty fault.
Pause, suspension and fault are not saved in the ledger. The existing
`awfttavern suspend false` command can explicitly resume a healthy paused
scheduler; it does not clear a fault or override the nearby-player and loaded-
chunk gates. The coordinating chat owns restart and any runtime command.

Actual micro-motion and sipping, heard audio, two-player synchronization,
measured performance and full tavern acceptance remain open. See
FEATURE-AUDIT.md, STATUS-PUBLISH-0114.md, MICRO-MOTION-0113.md and
INSTRUMENT-POSE-0112.md. The retained historical checkpoint
`20261030T102849Z-97b9f9` covers 385 ordinary saplings and the completed
10-resident cleanup; it is not a claim about the latest checkpoint. Java and
resources remain frozen; this update changes documentation only.

## Historical 0.1.6/0.1.3 status retained below

The following notes preserve earlier findings, not the current deployment state.

Current correction artifact is0.1.6, handed to Root and not yet game-accepted.
It combines native A* survey-constrained neighbor expansion, a saveable native
Handcrafted Seat subclass and the supplied PlayerModel seated-pose repair.
See PATH-AND-SEAT-CORRECTION.md and HANDOFF.json for exact build/validation and
the original2 recovery packet. The installed0.1.3 history is retained below.

The active0.1.3 test subsequently exposed43 actual patrons, failed band routes,
standing models in chairs and unsaved native-seat passenger loss. The two
missing original entities are retained in authenticated42bdb5 for Root's
reviewed exact-NBT recovery. See FEATURE-AUDIT.md and
PATH-AND-SEAT-CORRECTION.md. Registered45 does not mean45 currently present.

## Historical 0.1.2/0.1.3 correction

The combined deployment candidate is now0.1.3: identical0.1.2 server behavior
plus the independently supplied client-only motion patch. See
MOTION-INTEGRATION.md.0.1.2 artifacts and receipts remain immutable.

The master installed matching0.1.3 on server/client and actual initialization
added15 at03:30:43UTC. Fresh status at03:32:59UTC reports45 registered/45
profiles,0 loaded, suspendedtrue, no adapter fault and performance start−1.
The original30 UUIDs remain. The45-resident repeat check was not sent, and no
active behavior, audio, animation or performance acceptance follows from this
dormant snapshot. Earlier30-resident repeat0 remains historical evidence only.

The live30-resident session exposed frequent path refusals, fast movement,
repetitive dialogue and no successful band start. Creation/persistence passed;
the lively-tavern and music requirements have not passed. See FEATURE-AUDIT.md.

The new source appends15 identities for45 total, preserving the original30
UUIDs/names/skin bytes. It retains the exact admittedb296 config and its ledger
binding. Follow MIGRATION-45.md; initialize adds only unregistered identities.
This chat does not install artifacts, issue live commands or control the client.

The correction admits26 saved red/brown rug cells as transit, removes an
overbroad empty-approach veto, and aligns containment with the last approved
node row. Native path/seat/furniture collisions and destination reservations
remain. Refusal reasons and exact refused cells are now exposed.

Owned movement base is0.25 with navigation modifier0.5, replacing the observed
Easy NPC default0.6 and old modifier0.65. These are settings, not a measured
walking-speed claim. One resident is serviced every3 ticks; activities last
10–60s after arrival, depending on purpose. Native head glances are bounded
and preserve seat and instrument poses. No ordinary movement teleports.

There are360 individually authored lines,8 per resident, with no globally
identical line. Saved histories exclude each speaker's last6 and the last24
global lines, with no repeated fallback. Per-resident speech rests45–90s,
global delivery rests at least10s, and ambient turns are25–40s apart. Player
interaction shares those histories and cooldowns. Music/gathering poses are
excluded from casual gestures. Failed band gathering retries in10–20s;
completed performances take30–90s breaks. Status records all held instrument
IDs, melody IDs, playing flags and shared start ticks. Actual audio is still
mandatory before acceptance.

The sections below describe the earlier30-resident preparation and upstream
research. Current source behavior is described above and in MIGRATION-45.md.

Current deployment revision: see **INSTALL-C806EC.md** for the exact two-JAR
package, server-only config, native command bounds and replacement hashes.
See **FEATURE-AUDIT.md** for the implementation/evidence assessment. No source
or compilation result establishes working native NPC behavior.

Owner clarification: the large custom tavern on the north side of eastern
Tortuga, immediately south of the two imported buildings. Main envelope
X1291–1312 / Z−1290–−1269; this does not target the imported Pirate Tavern.

This additive proposal owns only `proposals/drowned-rose/**` in the existing
checkout, base `a28a7ed5a79f261aebd668be7e630c7b325c17cf`. It does not edit the
master's active bridge, catalog, Packwiz pack, dashboard or coordination files.
No world, account, third-party JAR, log or cache belongs in source control.

The master chat **Build It!** owns deployment, backups, runtime, client and
world operations under `docs/coordination/WORKSTREAMS.md`. The new owner goal
explicitly requests coordination with ongoing construction. Coordination
messages have identified this proposal and requested a serialized window;
there is no delegated live lease yet. No server/client was started or stopped,
no world was copied or edited, and no runtime mod was installed by this work.

## Delivered source

* Java21 NeoForge component initially with30 deterministic UUIDs, permanent Easy NPC
  humanoids, no beds/jobs, individual names/personas/preferences/dialogue,
  original local procedural skin assets, and a saved residency ledger.
* Staggered server decisions: one resident every five ticks; ordinary
  activities last60–240seconds after arrival. Weighted selection respects
  reservations and excludes the last three destinations. There are no separate
  permanently seated and standing populations.
* Native path requests have a five-to-nine-second retry floor; incomplete,
  outside-survey or occupied-approach paths are refused. Ordinary movement does
  not teleport. Explicit recovery additionally requires30seconds stalled,
  collision-free loaded destination, and no nearby or viewing player.
* Handcrafted `Seat.of` and native passenger/dismount behavior, approached by
  walking first. Every chair retains its exact saved state. Actual sitting,
  approach, dismount and clipping tests remain required.
* Temporary social groups, at most four reserved group members, nearby look
  targets, original dialogue with a shared30–75second speech cooldown, and
  player-initiated scripted dialogue with a five-second per-player cooldown.
  Easy NPC's configuration interaction is intercepted for managed residents to
  prevent instrument removal; the default UI is not exposed on these residents.
* Four rotating musicians gather at saved stage destinations, start the native
  Monkey Island melody on the same server tick, complete it according to the
  native parsed duration, then return to ordinary activities. Band membership,
  shared start/end ticks and next break are persisted. Range reentry restores
  the shared epoch rather than starting a new melody. Unloaded or unobserved
  residents do not receive activity decisions; no chunk tickets are created.
* Bounded asynchronous latest-status telemetry, proposed Control Room service
  and UI module: population/activity/destination/registration, music switch,
  individual rest/enable and guarded stuck recovery. Weight changes are exposed
  by the typed service/command. Dashboard routing is not installed. Population
  target and activity-frequency sliders are still absent.

The source has compiled against the actual published Easy NPC7.17.1 and installed
Immersive Melodies0.8.0, Handcrafted4.0.3, Resourceful Lib3.0.12, named Minecraft
1.21.1 and NeoForge21.1.262 APIs. Compilation is not proof of working entity
rendering, client networking, animation, furniture geometry or sound.

The restart revision restores saved arrival/seated state and unfinished activity
deadlines; overdue decisions receive a deterministic per-resident1–31second
stagger. Status distinguishes walking from the intended activity on arrival.
Chunk availability checks use four cached chunk anchors rather than scanning
all243 navigation cells. Focused regression checks cover retained deadlines
and independently staggered restart decisions; physical restart acceptance is
still pending.

## Exact upstream findings

[Core7.17.1](https://modrinth.com/mod/easy-npc-core/version/QyvBBoEd) is required
on both sides. [Config UI7.17.1](https://modrinth.com/mod/easy-npc-config-ui/version/VqoJoXmC)
is optional for this adapter, whose Java code does not call Config UI. The
latest built component declares that dependency optional. The bundle is an
additional dependency wrapper and is intentionally omitted.
Core requires NeoForge21.1.0+ and Minecraft1.21.1–1.21.x; UI declares Core7.17.1
through7.x. The optional Easy Model Entities dependency is not added.

The current Easy NPC1.21.1 source at
[`2569f1d`](https://github.com/MarkusBordihn/BOs-Easy-NPC/tree/2569f1d19f2f97c82e97dd8cd8da20eef0459f6e)
and published Core7.17.1 JAR contain no Immersive Melodies-specific class or
class-file reference to `immersive_melodies`/`ImmersiveMelodies`. The advertised
"basic integration" therefore cannot be treated as a documented ensemble API.
The adapter uses ordinary Easy NPC equipment and the native instrument APIs;
support for held-instrument rendering must still be demonstrated in game.

Further source inspection found that native Immersive Melodies injects its
animator at the tail of `HumanoidModel.setupAnim`; Easy NPC's humanoid mixin uses
the same vanilla model. Easy NPC defaults to `ModelPose.VANILLA`, and its
non-aggressive idle arm handling and vanilla model synchronization leave those
parts unchanged. This supports testing the native animation path first; it does
not establish the final rendered result or require an additional client mixin.

Installed Immersive Melodies0.8.0 contains the built-in resource
`data/immersive_melodies/melody/monkey_island.midi`. Its actual loader identifier
is **`immersive_melodies:melody/monkey_island.midi`**, retaining directory and
extension. Source pin is release
[`22d8494`](https://github.com/Luke100000/ImmersiveMelodies/tree/22d8494e0d34cf5a0cbb32881b17690e47080ba1).

[`InstrumentItem`](https://github.com/Luke100000/ImmersiveMelodies/blob/22d8494e0d34cf5a0cbb32881b17690e47080ba1/common/src/main/java/immersive_melodies/item/InstrumentItem.java)
exposes `play(stack, melody, level, entity)` and public `MELODY`, `PLAYING`,
`START_TIME`, `TRACKS` components. The overload accepting an explicit start tick
is **private in0.8.0**; this proposal does not call it. Four public calls in one
server tick share the same epoch. Resume uses the public start-time component.
Pausing an instrument left in a mob's hands is insufficient: native mob autoplay
restarts it. The adapter removes instruments during breaks/inactivity instead.

[`MelodyProgress`](https://github.com/Luke100000/ImmersiveMelodies/blob/22d8494e0d34cf5a0cbb32881b17690e47080ba1/common/src/main/java/immersive_melodies/client/MelodyProgress.java)
uses `(gameTime - startTime) *50` and the parsed melody duration, including late
join/loop position. Native auto-synchronization can follow a nearby player's
instrument; competing player music is an explicit runtime test, not assumed
fixed by our server scheduler.

Native defaults include48-block audible distance, instrument volume factor1.0,
and20ms timing humanization. Four instruments initially use their native track
settings. Do not claim an acceptable mix until actually heard; partition native
tracks or adjust the supported volume setting only after a listening comparison.
No Minecraft sound commands, replacement background audio or modified JARs exist
in this implementation.

## Saved-layout preparation

Private artifact root:
`D:\A World for Two\staging\drowned-rose-source-20261029`.
`survey.py` reads authenticated archive `20261029T203217Z-c6cdb7`, SHA256
`4741a369d9a6269d93042fc306c9ad9bdc1f55b382c50c7a22ea65e7e5edda96`.
The updated `saved-layout-2.json` has243 connected candidate navigation nodes,
12 approachable chair candidates and90 destination candidates, including four
raised-stage locations. Both columns of the main aisle, bar service, galley,
gallery routes and stair approaches are excluded as idle destinations.
These are saved-geometry candidates, not proven native paths or capacity.

`occupancy.py` independently scanned1,163 saved entity rows/passengers in the
same authenticated checkpoint. Two existing entities were inside the custom
tavern envelope: one managed improved cat and one unmanaged Naturalist bird.
It found no saved HOME/JOB/potential-JOB memories in that envelope and no
collision with any of the30 proposed UUIDs or saved player UUID filenames.
The private `existing-occupancy-c6cdb7.json` retains the exact results and region
hashes. These historical saved positions are not current live occupancy; both
creatures and any later arrivals must be preserved during the fresh native check.

The generated survey has `spawn_admitted=false` and
`native_geometry_verified=false`. The proposed install config sets only
`spawn_admitted=true` for an explicit operator initialization and leaves native
geometry evidence false. The earlier native-geometry boolean prerequisite has
been removed: actual seating/path/rendering are acceptance tests, not a flag to
assert before first deployment. Initialization requires the exact config SHA256, then compares
the complete saved tavern preimage to the loaded native world. A changed chair,
floor, furnishing or architecture refuses initialization. All relevant chunks
must already be loaded; the component never loads them to make a check pass.
Before inserting any entity it prepares all30 bodies at free native-collision
positions, preserving existing occupants. Any refusal inserts none in that
preflight; a later insertion error retains partial identities for reviewed
recovery. Startup decisions are spread over1–31seconds. Failed chair mounting
expires the destination and is not recorded as a successful sitting arrival.

The master must review current existing inhabitants, the total managed-entity
budget and native graph/seat collision before admission. The source90 slots are
not permission to add90 residents. Existing Bill/cat/other citizens must not be
deleted or substituted. Creation is fixed at30 new identities for this goal.
Already registered missing identities are reported and never automatically
respawned; review saved entities/chunks before recovery to avoid duplication.

`prepare.py` generates30 original skin PNGs, roster, and an isolated215-entry
Core-only manifest (216 with `--include-config-ui`) preserving the214-entry lock and Packwiz configuration
payload. Existing unresolved/incompatible requests remain in the owning
compatibility inventory. This is not a published or installed pack. The custom
adapter requires its own reviewed artifact pin after runtime qualification;
the dependency manifest alone does not distribute the adapter.

## Master integration and game qualification

1. Serialize shared-source/catalog/version changes. Recheck reserve with bounded
   allocations. Freeze exact source and mod hashes; review population budget.
2. Inspect the actual custom tavern and existing residents. Obtain an exclusive
   runtime/client window and a fresh verified world backup, preserving player
   inventories, current furnishings, configured permanent world and construction.
3. Install the same reviewed Core and adapter on server and client; UI is optional.
   No bundle, different loader/game versions, EULA acceptance or account login.
   Do not publish this candidate before qualification.
4. Stage the exact proposed install config in server `config/awft-tavern.json`
   before first launch. Use `/awfttavern inspect` to compare the actual native
   preimage, then initialize using the SAME file hash. No second restart or
   fabricated `native_geometry_verified=true` is needed. Native collision is
   preflighted before insertion; actual chair/path/rendering acceptance follows.
5. Under the exact config hash, initialize once, then repeat and verify
   zero duplicates. Confirm30 UUIDs plus all previous inhabitants. Observe every
   resident switching sitting/standing/walking/social roles over several cycles.
6. Observe the four real instruments playing Monkey Island together, a complete
   tune, break, rotation, distance attenuation and player-range reentry. Listen
   and tune native track selection/volume. No phase6 completion without actual
   instrument playback evidence.
7. Unload/reload chunks and restart normally. Reconcile all30 UUIDs, residency,
   current band epoch and reservations. Test absent/missing identity handling;
   no automatic replacement merely because an entity is not presently loaded.
8. Test two independently connected licensed clients, including a mid-performance
   join and nearby player instrument. Owner account input is required if the
   second client is not already available; never authenticate on their behalf.
9. Collect matched actual before/after30-resident and active-band windows using
   `benchmark.py`, with stable clients/chunks and no concurrent construction or
   wildlife changes. Preserve raw samples; use actual MSPT and profiler findings
   to tune decisions, path retries, animation and speech. No benchmark has run.

Control Room integration is proposed only: copy `dashboard.py` to
`control_room/tavern.py` and `tavern.js` to the static folder. Instantiate
`Tavern(self.layout.home,self.server.command)`, add GET `/api/tavern` and
token/origin-protected POST `/api/tavern/control`, and wire `mountTavern` through
the existing route lifecycle. Add only the listed fullmatch command patterns,
under existing construction-runtime admission; do not bypass the command
allowlist. Initialization remains a separate exact-hash owner operation.

## Evidence state

Required repository validation: **1,476 tests run, two skipped; all others passed**; Packwiz
validation passed for214 current entries; active `app.js` syntax passed.
Focused roster and dashboard validation passed. Java policy scenarios covered
30,000 transitions for30 identities, exclusive destinations, recent-history
exclusion, posture variation and full-room waiting. These are synthetic tests.

**No actual NPC, gameplay, playback, two-client, restart, performance or artistic
acceptance is claimed.** No final phase is marked complete. The goal remains
active pending serialized integration and those observations.

All local writes used bounded reserve checks. Both drives remained above30GiB.
This is a monitoring instruction; it does not constrain external applications,
cloud work or existing writers that have not loaded the instruction.
