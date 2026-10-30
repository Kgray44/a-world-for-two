# Implementation assessment: live progress and remaining checks

## Current candidate: 0.1.14 prepared after the actual 0.1.13 pause

0.1.14 is prepared for the coordinating chat's matched server/client restart,
SHA256 `82c0bbe1bedae4736880b9aba34c10b0b6f4136167be959c9a078181492c2854`.
This is preparation evidence; no 0.1.14 runtime acceptance is claimed here.

The actual 0.1.13 trial reported AccessDeniedException while atomically replacing
the status file. The next heartbeat latched a global fault and paused activity.
Later publication could succeed without clearing the scheduler's retained fault
and pause. Status had already reported suspended=true before the fault; that
flag alone is not evidence of a persisted pause. The Ada cushion view was
obstructed, and QA camera-angle receipts do not establish full visual acceptance.
Neither micro-motion nor sipping is accepted from that trial.

0.1.14 retries only atomic-move AccessDeniedException on the existing background
writer: six attempts, with 25/50/100/200/400 ms delays (775 ms total backoff).
No server tick sleeps or non-atomic fallback are introduced. Persistent errors
still fault and pause. Java 21 compilation, the four Java scenario suites, two
focused Python tests and five real Windows publication scenarios pass. Actual
healthy heartbeat and ordinary-activity recovery remain for the runtime trial.
See STATUS-PUBLISH-0114.md for scope and the reader-handle reproduction limit.

Healthy load of the admitted config sets paused=false, suspended=true and an
empty fault; none of those three fields is serialized in Ledger. The existing
`awfttavern suspend false` command only sets paused=false. It is appropriate for
an explicitly paused, healthy scheduler, and normally unnecessary after healthy
load. It neither clears a retained fault nor bypasses the nearby-player or
loaded-chunk gates. No ledger initialization or identity recovery is needed.
Runtime commands and the matched restart belong to the coordinating chat.

The completed 0.1.12 gameplay evidence in the large custom Drowned Rose directly
south of the two imported buildings remains:

| Feature | Actual evidence and limit |
| --- | --- |
| Population | All 45 residents saved and observed loaded with their existing identities. No ledger reset or respawn was needed. |
| Sitting/exits | Roan visibly seated with bent legs on a green cushion. One native trial sample reports 117 completed exits and 4 blocked-exit waits. |
| Ensemble | A real framebuffer shows all four native instruments and matching arm rotations. Paired native telemetry reports playing components and notes 114 ms old; heard audio remains unproved. |
| Drinking | 147 native drink completions in the reported trial sample. Actual sipping pixels remain pending. |
| Legacy stuck patrons | Exactly 10 existing gated recovery commands cleared all 10, without respawning. The authenticated pre-guard f7e43f backup already contained the same 10; no new post-guard entrant was demonstrated by the comparison. |
| Micro-movements | 0.1.13 moves the existing idle/seated motion after Smooth's shadow pass. Compilation and focused checks pass; actual final motion remains unaccepted. |

The native 0.1.12 band PNG SHA256 is
`848627512400878e9df6fbc2ed104ab72cd24a07638d60f49e5de7b39314692c`.
This is actual instrument/pose image evidence, not sound evidence. The counts
above describe completed trial samples, not fresh 0.1.13 or 0.1.14 counters.

The retained historical normal-stop checkpoint
`20261030T102849Z-97b9f9`, SHA256
`14fad9f9da599c18b3dd2a3dd62e5a10c9362f6b5dc1af0e30573b0fb6379d52`,
covers 385 ordinary saplings and the completed 10-resident cleanup. These are
the coordinating chat's checkpoint-specific observations, not a current census.
The independent saved396 census below remains evidence for its earlier checkpoint.

Java/resources 0.1.14 remain frozen. Only these documentation heads are updated.
Actual micro-motion and sipping, heard audio, two-player synchronization,
measured performance and full tavern acceptance remain open. See
MICRO-MOTION-0113.md and INSTRUMENT-POSE-0112.md for source/validation scope.
Historical findings below retain their checkpoint-specific meaning.

## Historical 0.1.11 review candidate after the actual client probe

The07:50UTC QA9 snapshot identifies Smooth Player Animations' NpcPlayerModel as
the actual model. Its override calls the vanilla setup and then overwrites the
result with its own shadow pose. The new optional subclass-TAIL hook reuses the
existing seated/sip functions after that pass. It is combined with the guarded
native chair exit in a compiled0.1.11 candidate. Actual visual sitting/sipping,
safe exits and playback acceptance remain pending. See SMOOTH-POSE-0111.md and
SAFE-DISMOUNT-0111.md; no new runtime success is inferred from the candidate.

## Population and occupied-seat save check:30 October2026,07:19UTC

The later normal-stop checkpoint `20261030T071907Z-5f7983` updates the
population and seat-serialization findings below. Its independently verified
ZIP SHA256 is
`7753471f6d96cf92fc831c97895628468858d3077450a5aab17708d03f3b937c`.
All351 LIFE and all45 tavern residents are saved exactly once:396 managed
identities, including Oona's restored original UUID and Niamh's authorized
original-profile reconstruction. All43 previously saved tavern patrons remain.
There are no global saved UUID duplicates, extra tavern identities, or player
UUID collisions. All396 have NoAI0. Names, skins, tavern persistence flags,
recursive ownership fields, LIFE intent bytes,45 ledger identities/personality
weights, both protected creatures and the2,916-cell preimage pass their checks.

Exactly three managed seats are saved as root entities, each with its one
original passenger and matching `awft_resident` UUID: Arlo Ink, Nell Tide and
Lina Splice. This is actual occupied-seat serialization evidence. Restart/load
survival and the visibly incorrect standing pose are separate outstanding
checks. It supplies no new sound, multiplayer or performance acceptance.

The private receipt is
`D:\A World for Two\staging\drowned-rose-source-20261029\saved396-20261030T071907Z-5f7983-validated.json`,
SHA256 `6aeea1fe8e49724c076337b3882e5d49a4485b98a1d23f5d5879d08aa1d3a601`.
An earlier receipt was retained with a failed expectation because this audit
used incorrect guessed surnames/IDs for Lina and Nell. The validated rerun
uses their frozen-roster identities and passes all checks; no world data was
changed to obtain that result. Production0.1.10 remains frozen.

## Historical actual0.1.10 checkpoint:30 October2026,07:05UTC

This section supersedes the older candidate assessments below. The matched
installed0.1.10 artifact remains frozen at SHA256
`fdec4106cefabc16d2d9157ae02ea9b6a03d860efdd440c4543372a182f4dab6`.
This audit update changes documentation only; it does not change that artifact.
All observations concern the large custom northern east Drowned Rose directly
south of the two imported buildings.

The actual dashboard status at07:05:11UTC reports755 decisions,1,480 path
requests,1,131 paths started and349 refusals, all `native_incomplete`.
That is approximately23.6% of requests refused; the earlier clean first101-path
sample does not characterize the longer trial. At07:05:56UTC all six residents
whose latest refusal remained `native_incomplete` shared exactly
`1299.5,65,-1277.5`: Nels, Esme, Pax, Suri, Rowe and Vesper. Their floor cell
lies outside the269-cell admitted graph, two cardinal steps from its nearest
admitted cells. A seat-dismount fallback is a hypothesis, not an established
cause. Do not expand furniture transit or teleport residents on that inference.

The same trial reports six completed server-side performance intervals, three
failed gatherings and92 native drink finishes from92 starts. Four instrument
stacks with the exact melody, PLAYING flag and common start epoch were observed
by the coordinating chat during a music phase. These establish real scheduling
and native item-use progress. They do not establish audible music, visually
correct instrument/sip poses, or two-client synchronization.

Population remains45 registered and43 physically loaded at this checkpoint.
The independently audited normal-stop7d8213 archive contains the same43 tavern
identities, including restored Dara and Rhea, alongside351 LIFE identities.
Oona and Niamh remain absent from that saved checkpoint. Registration is not
physical presence. There were no saved managed-seat vehicles in that archive,
so it does not prove seat-passenger save/reload survival.

Seating has a definite visual failure. The coordinating chat's unobstructed
`logs/visual-review/tavern110-g1-paused-0704/arlo-seat-profile.png` shows Arlo
standing with straight legs on the cushion while native status reports him
riding a saveable `awft_tavern:persistent_seat`. Native mounting therefore
works, but correct visible sitting is not delivered. A small read-only client
probe is the next diagnostic; no speculative production pose correction has
been packaged.

The installed client's debug log confirms both PlayerModel seat/drink hooks
were injected. Actual pinned EasyNPC Core7.17.1 bytecode passes the NPC itself
directly through its standard PlayerRenderer, with no AbstractClientPlayer
proxy. Its item attachment layer reads ordinary main/offhand stacks; no separate
equipment store is required, and no item-layer disable/blacklist error appears
in the trial's client logs. Actual client vehicle/skin/model state must identify
the remaining pose failure. Immersive Melodies ticks held instruments on living
NPCs, but native client progress and actual audibility remain unverified.

The implementation is partially functional, with important acceptance failures
still open:45 physical residents, reliable seating/persistence, stuck recovery,
visible drink/instrument behavior, audible synchronized music, and measured
multiplayer/performance impact. The historical compilation and synthetic tests
below cannot substitute for those checks.

## Subsequent active0.1.3 failures

The combined0.1.6 correction compiles with the supplied seated-pose patch and
passes native-A* synthetic detour/blocked/corner checks plus the existing
45,000 policy transitions and2 focused Python checks. All45 roster/skin assets
are unchanged. It is handed to Root for matched installation; actual music,
physical seating and save/unload/reload acceptance remain pending.

The active client test confirmed better walking but no music. At03:50:24UTC,
the adapter reported208 decisions,556 paths,418 refusals (409 outside_transit,
9 native_no_path),4 failed gatherings and performance start−1. Native A* was
choosing chair/table/column shortcuts that the later survey check rejected.
The correction constrains native neighbors during A* rather than admitting
those collidable cells. A native-A* synthetic detour regression passes, but
the corrected route still needs a live test.

Only43 of45 registered patrons were present while the tavern was loaded.
Oona Kelp and Dara Moss were absent from every saved entity/passenger row in
preupdate e9d33f, though earlier42bdb5 contains their exact original data.
Handcrafted's native seat type is noSave, which makes it unsuitable as the
serialized root for permanent NPC passengers. The saveable managed Seat
subclass correction compiles; actual seat save/unload/reload is still pending.
Root alone controls restoration of the two exact original UUID/NBT payloads
after fixed seat behavior and authoritative current absence are verified.
There is no ledger reset or substitute identity. The owner also observed
standing models inside chairs; the client riding-pose repair is pending.

Earlier creation/registration and saved-census evidence below remains valid
for its checkpoint. It does not establish current persistence reliability.
See PATH-AND-SEAT-CORRECTION.md for the concrete causes and bounded repairs.

## Latest live finding and correction candidate

Actual additive initialization at03:30:43UTC created15 new residents. Matching
0.1.3 server/client artifacts and the unchangedb296 config have been independently
hash-checked. Fresh03:32:59UTC status reports45 registered/45 profiles, exact
original30 plus additional15 UUIDs, no fault,0 loaded, suspendedtrue and
performance start−1. The associated2,916-state Native verification finished
with0 failures and0 temporary tickets. The repeat45 initialization command was
**not sent** because its cached read window had ended; do not claim repeat0.
The earlier30-resident repeat0 is a separate historical test. A saved45 census,
normal restart, active behavior and actual sound remain pending.

The master separately reports351 LIFE (105 villagers/246 wildlife) after seven
ordinary additions, making396 combined with45 tavern. This is a reported runtime
population state, not the older independently audited374 saved snapshot or proof
that all396 are simultaneously loaded.

The current combined candidate0.1.3 adds the supplied client-only model motion
patch to0.1.2's corrections. It compiles and its metadata/package checks pass;
actual Mixin application, visual quality and seat/instrument pose preservation
still require the master's game session. No supported lounging preset is claimed.

The quoted implementation claim described available code paths, not accepted
gameplay. Actual creation, idempotence and saved identity checks passed for30.
The master-owned client session subsequently rendered those30 and showed some
movement and dialogue, but patrons clustered, walked too quickly, repeated
lines and did not start the ensemble. At02:56UTC the live counters were72
decisions,356 path requests,370 refusals including timeouts,2 dialogue
deliveries and performance start−1. Those totals do not establish each refusal's
cause. There is no actual Monkey Island listening/synchronization acceptance.

Source inspection found that all26 central rug cells were absent from admitted
transit, arrived NPCs' empty approach squares were treated as path obstructions,
and the last graph row disagreed with the physical boundary.0.1.2 corrects these
and adds refusal reasons. It reduces movement settings from0.6×0.65 to0.25×0.5,
uses10–60s activity dwell after arrival, adds native idle glances, and replaces
the3-line pools (including one identical shared line) with8 unique lines per
resident and saved per-NPC/global histories and cooldowns. Failed gathering
now retries sooner, and instrument/song/start components appear in status.

The owner's later directive increases the target to45. The additive candidate
has45 deterministic profiles and360 distinct original lines. Focused checks
prove the original30 identities/names/social preferences/skin bytes unchanged,
45 distinct skin payloads, and45,000 synthetic policy transitions. A bounded
authenticated42bdb5 saved census found the original30 and no occurrence of the
15 additional UUIDs or any matching player UUID. This is historical admission
evidence, not current free space or successful creation of45.

| Important feature | Current evidence | Assessment |
| --- | --- | --- |
| Population/persistence |30 originally created/saved/repeat0; additive15 actually created and45 registered; later active count43 exposed native unsaved-seat loss | Seat persistence repair and exact2 recovery pending; not reliable yet |
| Appearance |30 rendered in master's session;45 packaged skin payloads differ | Basic local skins; visual quality remains limited |
| Lively activities/navigation | Real movement occurred but many routes failed; correction compiles | Incomplete until repeat live observation shows varied successful arrivals |
| Native Handcrafted seating | Native Seat creation/mounting code compiles; status now exposes riding seats | Physical clipping/facing/dismount not accepted |
| Dialogue/social behavior | Actual lines delivered, observed repetition; new360-line pools/history rules pass focused tests | Corrected source, believable conversation still unproved |
| Monkey Island | Exact installed resource and native API verified; no successful live ensemble start | Mandatory feature not delivered yet |
| Multiplayer/audio/performance | No qualifying two-client sound or matched before/after tick benchmark | Not accepted |

The existing block preimage and protected creatures remain intact in the last
verified normal-stop snapshot. All45 features must be tested in the large
custom Drowned Rose south of the two imported buildings. Compilation and
policy tests cannot establish sound, seating geometry or a bustling room.

## Historical30-resident creation and saved-census evidence

Latest independent saved census: verified normal-stop42bdb5 retains **374
managed entities across both ledgers:344 LIFE (98 villagers/246 wildlife) and
the same30 tavern patrons**. No requested identity is missing or duplicated.
All344 LIFE and30 tavern entities have NoAI0. Prior304 LIFE intent bytes and
owner fields are unchanged versus14ced4; the40 new LIFE entities have no
standard owner fields. All30 tavern names/UUIDs/persistence/owner/AI metadata,
their saved ledger and the2,916-cell tavern preimage remain intact. Both protected
existing creatures remain present with matching metadata. This extends the
earlier334 saved census below; it does not supply activity, audio or visual proof.

The matched component is now installed, and actual initialization created30
patrons. Repeating initialization returned0 new residents. Independent reading
of the verified normal-stop14ced4 archive found all30 tavern entities and all304
LIFE entities, with no missing or duplicate requested UUIDs. The saved tavern
ledger matches those30 UUIDs; every patron has its expected name,
PersistenceRequired1, NoAI0 and no top-level owner fields. The existing cat and
bird are preserved, all304 LIFE owner fields match19cdc3, and the2,916 tavern
block-state preimage cells are unchanged. The unmanaged bird is additional to
the334 combined managed identities, not counted twice.

The full server status event at01:09:03.929504700UTC was independently parsed
from both compressed log archives. It reports30 registered and30 loaded,
with no fault and all UUIDs matching the installed roster. This is one event
present in two archives, not two separate observations. It also reports
`suspended=true` and `performance_start_tick=-1`, so it supplies presence proof
without any activity or playback claim. Compressed-source hashes and a sanitized
parsed summary are retained privately; no raw log is published.

This establishes actual creation, idempotence and saved identity/flag evidence.
At that earlier checkpoint the server was empty and patrons were dormant.
The subsequent client findings are reported above; neither observation
establishes a functioning lively tavern.
The earlier statement that the candidate
"includes" all these features described code paths; it was too strong as a
description of delivered gameplay.

| Feature | What exists | What has actually been proved | What remains |
| --- | --- | --- | --- |
|30 permanent residents |30 named profiles, deterministic UUIDs, original local skins, persistence-required Easy NPC entities and saved residency ledger | Actual initialize30, repeat0; full server status shows30 loaded/registered with exact UUIDs; all30 names/persistence flags and ledger saved in14ced4 alongside304 LIFE entities | Normal restart/reload gameplay reconciliation, client presentation and sustained behavior |
|Distinct appearances |30 procedural skin textures with varied colours and some face/clothing details | Assets are packaged in the built JAR | Native rendering and visual quality. These are basic generated skins, not an art-reviewed cast |
|Activity changes | Weighted decisions, random durations, recent-destination exclusion, walking to destinations, sit/drink/social/bar/watch/window/group choices |30,000 synthetic policy transitions on an artificial slot layout, not the saved tavern | Real navigation, visible transitions, activity balance and believable behavior for all30 |
|Destination reservations | Server-side position/approach alias checks; group cap; native seat occupancy check | Source review and logical slot tests | Simultaneous physical occupancy, players using chairs, dismount and crowd circulation |
|Handcrafted sitting | Walk to approach, create native Seat, mount, dismount before moving | Compiles against the actual Handcrafted API; source failure handling reviewed | Actual chair geometry, facing, clipping and survival across chunk/restart lifecycle |
|Conversations | Small group labels, nearby look targets, local delivery, shared speech cooldown, per-player scripted replies | Source and bounded-control tests | Natural conversational turns. Social preferences are a simple activity-weight boost, not a rich social simulation; favorite-location return is not yet substantive |
|Monkey Island ensemble | Exact built-in resource verified; four real instrument stacks; native play API called in one server tick; persisted common epoch; rotation/break logic | Resource/API inspection and Java compilation | Actual sound and instrument animation, whole-tune/break/rotation observation, late join and two clients |
|Audio mix | Native distance/volume/track facilities retained | Upstream implementation inspected | Four performers initially play native track settings; overlap/loudness is untuned. Same start time is not an audio listening test |
|Containment/performance | Bounded native paths, four cached chunks, staggered decisions, no ordinary teleportation or forced chunks | Source and limited policy tests | Real containment, stuck behavior, MSPT/profiler impact on the existing population and target host |
|Control Room | Proposed backend/UI and live-status file code | Focused validation and JS syntax | Integration and browser/runtime qualification. Target/frequency sliders are absent |

The review found and corrected real defects after the first compilation:

* saved activity deadlines and seated/arrived state were not fully restored;
* a failed native chair mount could still be described as an arrived sitting activity;
* one occupied fixed spawn point could refuse all30 rather than select other safe points;
* a separate `native_geometry_verified` boolean blocked first deployment without
  proving geometry. It is now evidence only; actual native preimage/collision
  checks remain mandatory at initialization;
* Config UI was unnecessarily required by adapter metadata despite no code use.

These corrections compile and focused checks pass. None replaces in-game
validation. The historical1,476-test repository pass is not an entity behavior,
seating, musical synchronization, multiplayer or performance test for this feature.

The next decisive evidence is an owner-permitted actual game session: watch all
activity transitions and chairs, hear the native four-instrument tune, then test
normal restart/reload behavior and two clients. Actual creation, repeated
initialization and the normal-stop saved identity check have passed. Do not call the feature complete or
reliable until those observations succeed.
