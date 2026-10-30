# Control Room and World Atlas integration handoff

Owner: **Complete Control Room and WorldAtlas**, chat
`01a183b9-ca05-7ef2-8006-14b1d1d648e1`.
Branch: `codex/control-room-world-atlas`, based on
`3333bc60646cc594093063ed514a3e51246e35b0`.

Frozen implementation: PR #1, head
`8ef3ecece908a21fc8a90ca3642d3edf49c78623`; GitHub Actions run **40748848545**
passed. Subsequent read-only qualification notes are on
`codex/control-room-runtime-receipts`; they do not change that frozen source head.

The master **Build It!** owns integration, all native/runtime windows and both
world saves. Its authoritative `docs/coordination/WORKSTREAMS.md` was read from
the primary checkout on 2026-10-28. This handoff never grants a runtime lease.

## Checkpoint 1: dashboard responsiveness and evidence accuracy

Implemented:

- Atlas tile metadata inventory runs in one bounded background worker. HTTP
  responses carry original measurement time, age, pending/error state and cache
  revision. Unknown or stale inventories pause managed rendering. No tile hashes
  or chunk generation are performed by reads.
- Explicit storage refresh schedules the existing background inventory instead
  of blocking its HTTP request. Passive inventories refresh at most once/minute.
- Browser reads do not overlap. Hidden tabs stop polling; failures back off.
  History requests follow the one-minute persistence rate. API requests time out
  without automatically replaying ambiguous actions.
- Claim snapshots expire independently after 45 seconds, matching their native
  30-second sample cadence. Browser-side timestamps prevent retained coordinates,
  renderer state or claim boundaries appearing live after a delayed connection.
- Bounded task history survives backend restarts. Unfinished tasks become
  **interrupted**, never successful or automatically replayed. Unexpected errors
  do not expose exception text; token/password values are redacted.
- Atlas describes adapter availability explicitly. No automatic Xaero or
  MapHorizons synchronization, Create railway-network positions, virtual airship
  positions, or party-management API is asserted. Loaded entity observations are
  distinct from historical records. Successful native teleport results append a
  bounded return audit; native teleport acceptance remains pending.

Exclusive files: `control_room/{atlas,jobs,web,storage}.py`, the freshness
projection in `metrics.py`, `static/{app,atlas,session,polling,atlas-state}.js`,
`tests/test_control_room_completion.py`, `tests/polling.test.mjs`, and this handoff.
No Java bridge, command allowlist, Packwiz, runtime config, world or client edits.

## Verification receipts

- Baseline: `python -B -m unittest discover -s tests -v`: **953 tests passed,
  1 skipped** before changes. The six-hour sprint uses targeted subsequent runs.
- New regressions: **13 Python tests passed** in
  `test_control_room_completion.py`; **8 Node tests passed** across
  `polling.test.mjs` and `session.test.mjs`.
- Existing targeted suites: Atlas/cinematics **17 passed**, measurement freshness
  **19 passed**, safety **36 passed**.
- Syntax: `node --check control_room/static/app.js` and `atlas.js` passed.
- Actual browser: isolated blank-home Control Room at `127.0.0.1:18765`; Atlas
  loaded, a clearly labeled manual fixture waypoint was created and searched.
  A browser timer receiver error was found and fixed; subsequent checks continue.
- Earlier failed new-test runs were fixture setup errors (missing mocked
  application attributes), corrected before the passing 13-test checkpoint.

Private detailed output stays in the worktree's ignored `runtime/verification/`.
No worlds, credentials, JARs, caches or raw logs belong in the commit.

## Deployment and pending acceptance

Integrate source through the master PR queue. Stop only the approved dashboard
process after its jobs finish; do not stop/restart Minecraft without the master's
window. Restart that dashboard from the integrated source, then reload browser
tabs to pick up the new modules. Do not point a second Application at the same
runtime home. Application shutdown currently stops its owned Minecraft process,
so the master must schedule this deliberately.

Only lightweight fixtures and existing runtime GET inspection are authorized.
Actual native start/stop/restart, live TPS/MSPT/chunks/players, permission changes,
backup/restore recovery, safe teleport, moving objects, party APIs, remote mapping,
Playit controls, multiplayer and official-world integration are **pending** an
exclusive master window. No additional Minecraft copy or JVM was launched.

The master subsequently delegated the narrow startup and player snapshot lock
regions. `Server.start` now retains its full world mutation lease while releasing
the status lock during slow preflight, then rechecks ownership before creating
the child. `Players.snapshot` serializes only its small dashboard bookkeeping;
world jobs cannot block its reads. Existing command allowlists remain untouched.

Both C: and D: reserves were checked before writers and periodically. Most recent
pre-check at 18:25:57Z: C **118,559,727,616** free bytes; D **284,446,781,440**;
bounded C allocation **268,435,456**, D allocation **0**. Monitoring covers owned
writers only; external applications and pre-existing unrelated writers are
outside its enforcement.

## Checkpoint 2: review corrections and browser verification

Additional source-only files: `control_room/players.py`, only `Server.start` in
`control_room/server.py`, `tests/test_server_start_responsiveness.py`, and the
single CI test-list line in `.github/workflows/validate.yml`.

Review corrections preserve responsiveness through journal reserve checks,
fingerprint tile **metadata** rather than file contents, expire detailed cache
and adapter labels, preserve edit revisions while a dialog remains open, and
record bounded private diagnostic references for unexpected errors. A confirmed
native teleport stays complete if its optional local audit write fails; its
returned history warning never invites an automatic second move. Delayed page
responses cannot overwrite a newly selected page. Open player cards and overview
readings expire independently of network success.

Targeted verification after these changes: **138 Python tests passed**, no skips
or failures, across Control Room completion, startup responsiveness, lifecycle,
freshness, Atlas/cinematics, safety, sync cache, preview redirect and Playit/graphics.
**10 Node tests passed** across polling/freshness and session recovery. Both
JavaScript entry-point syntax checks and `git diff --check` passed. Pack validation
passed with 208 inventory records; the pack files were not changed.

Actual isolated browser checks on `127.0.0.1:18765`:

- Manual fixture waypoint create/search, dimension switching, persistent settings
  save/reload, and mobile navigation dismissal at **390 x 844** passed.
- Start refused the deliberately unaccepted EULA and showed a failed task with
  the actual reason. No JVM or child process was launched.
- Stopping/restarting only the owned Python backend preserved the failed job and
  waypoints. The old browser tab recovered: exact response sequence **POST 403,
  bootstrap GET 200, POST 200**, with one saved waypoint and no ambiguous replay.
- An artificially delayed Settings request returned 200 after navigation to
  Atlas; the active heading stayed **World Atlas**, with no JavaScript exception.
- Browser verification found and corrected a timer receiver error missed by the
  initial Node run. Earlier test-fixture errors were also corrected; current
  targeted checks pass.
- The in-app browser kept both tabs' `document.visibilityState` visible during
  the inactive-tab probe, so that probe does **not** establish hidden-tab behavior.
  Hidden/visible scheduling and non-overlap are verified by controlled Node tests.

Read-only existing-runtime observation at **2026-10-28 18:45:20Z** (not deployment
of this PR): server PID **51360**, online; fresh bridge sample **19.9689 TPS**, mean
**2.21795 ms**. One GET each measured overview **113.67 ms**, metrics **3.74 ms**,
Atlas **92.29 ms**. These are single observations, not benchmarks or overhead proof.
Atlas exposed **26 existing tiles / 525,957 bytes**, **519 recorded locations**,
**0 current loaded objects**, and an available claims snapshot with zero claims.
Its two player-access entries do not establish two online players. Real terrain
tiles were viewed in a browser. Latest tile change was **2026-10-28 17:47:35Z**;
the current construction edits' rendering is therefore **unqualified**. Do not
substitute inventory measurement time for tile render time.

An earlier probe during the master's startup window returned connection errors;
that failed receipt was preserved. No native POST, teleport, tunnel, world,
client, runtime configuration or pack write was performed by this workstream.
Native control/recovery and final-world acceptance remain master-window work.

## Read-only follow-up: actual native map updates

The master supplied six genuine `awftbuild map` results from **18:47-18:48Z** in
`H/staging/tortuga-eight-native50-1793213258700916100/actual-results.json`.
The earlier **18:45Z** observation of 17:47 tiles preceded those calls. It was
not evidence of a render failure after the calls.

At **19:04:43Z**, all six source plan SHA-256 values matched their actual map
receipts. Unique source chunk counts **2, 2, 2, 5, 4, 3** matched the reported
queued counts. Their source coordinates map to precisely two native zoom-3 tiles:

| Tile | Actual last write UTC | SHA-256 | HTTP bytes |
| --- | --- | --- | --- |
| `minecraft_overworld/3/1_-3.png` | 18:48:21.286982Z | `a227ffbc803acb9ad1b435a85af85a7698e10ff6e8d7ad7611660dc17aa6cd92` | Exact match, stable file |
| `minecraft_overworld/3/2_-3.png` | 18:59:51.162428Z | `522eebc8cce9e36111ed9a770c69991066e73ee184546358aaba449f17bdbd4e` | Exact match, stable file |

At that observation the Atlas reported **26 tiles / 526,213 bytes**, latest tile
write **18:59:51Z**, and renderer queue **0**, paused **false**, overloaded **false**.
This establishes updated target files and correct serving for the six named
source batches. It does not prove every rendered pixel, every later world edit,
or the new dashboard source's deployment. A latest-write time does not reveal
all intervening writes or establish an exact render latency.

The private exact reconciliation receipt is
`runtime/verification/native50-map-reconciliation.json` in this owned worktree.
Only the six bounded source plans and two explicitly selected tile files were
hashed for this qualification; dashboard polling never performs these checks.
No native command, configuration, provider, bridge or world change was made.

Pinned API inspection found no disabled-background or output-path fault. Existing
`SettlementSupport` map handling already deduplicates plan chunk coordinates and
calls the pinned internal `MapWorldInternal.chunkModified(ChunkCoordinate)` path.
The actual configuration enables 32 chunks per 30 seconds on one render thread.
Image writes occur asynchronously after snapshot futures complete. No additional
flush timer, player-presence gate or unchanged-pixel save shortcut was found.
There is no basis here for another bridge feature or an idle-simulation bypass.

Squaremap 1.3.2 pin: JAR SHA-256
`e22ecd8c18a7a345c462e0988a3c6f41e366eed9a14ac276279e6edfed23813d`,
upstream commit `7157ae6`. Public `api.MapWorld` has no refresh method. Rendering
may read the surrounding eight chunk snapshots. The vanilla provider skips
missing/non-FULL stored terrain but can load previously generated neighbors;
Moonrise uses a different path. No runtime ModList/provider identity or strictly
loaded-only/no-generation acceptance is asserted from filename inspection.

## Transport API dependency

The [proposed transport observation contract in PR #5](https://github.com/Kgray44/a-world-for-two/pull/5)
is `docs/TRANSPORT-OBSERVATION-CONTRACT.md`. It is **not installed in candidate.50**.
No transport HTTP endpoint or continuous position feed exists in that candidate.
The native contract is on-demand, master-window controlled and scoped to the
Copper Wren region. It explicitly reports ship and airship positions unavailable.
Missing observations must remain unavailable, rather than an empty train list.
This workstream links the dependency only; it does not install, invoke or broaden
that observer, expose proposed coordinates as live, or change its authority.

## Frozen display against actual native GET data

A temporary loopback reader on 18765 served the unchanged **8ef3ece frontend and
Atlas GET model** against actual 8766 GET responses and existing tile metadata.
Its visible banner said **READ-ONLY QUALIFICATION**. It never initialized the
Application lifecycle, scheduler or backups, never issued an in-game command,
discarded the native administrator's CSRF value, and rejected every POST with
405 before forwarding. A bounded `/api/qa-read-only-probe` confirmed that refusal.
This qualifies the named display/model paths, not deployment of the complete
Application or a native administration write path.

The new UI rendered actual tiles, observation times and available zero-claim
data without JavaScript exceptions. During the master's genuine shutdown,
`Stop world` job **7e48108aac884a348110e8a8f745cfec** completed at
**19:11:29.369654Z**. Read-only observations of both ports then reported **offline,
PID null, bridge unavailable**. The new Atlas kept KG's **19:04:39** coordinates
labelled **last seen**; claim/live-object availability expired. Performance showed
unavailable current TPS, MSPT, heap and chunk counts while retaining measured
history. The earlier genuine master `Start world` job
**4c6344d5999840b686eceac955ad0814** finished at **18:37:28.557014Z**. These were
master-owned operations observed passively, not actions by this workstream or
proof of the new startup-lock implementation running in the native controller.

Private receipts: `runtime/verification/frozen-ui-native-readonly.json`,
`frozen-atlas-native-readonly.png`, `frozen-performance-native-readonly.png`, and
the retained 4 KiB QA harness. The reader used approximately **37 MB RSS**, had
**zero child processes**, and was retired at **19:19:48Z** after its browser tab
closed. Port 18765 was verified released. No installed code, native/world/config
file, account, tunnel, player or Minecraft process was changed by that reader.

## Integrated candidate.51: actual controller browser smoke

The master integrated the frozen Control Room changes as **f1e8c70** and the
map/transport notes as **35f3af7**. The primary checkout was **59ab966c7a8b22ff012ee2ac907cfae06fc5b982**
when inspected at 19:28Z. The master restarted its controller while the game was
offline. Actual loopback listener **127.0.0.1:8766** belonged to Python **7068**,
created **19:21:07Z**. No second Application or game JVM was started by CONTROL.
The master reports installed candidate.51 / bridge0.6.37, JAR
`cb634e9c848b11d6f2cb90533de8f91779dc56b8420a37857ae9b2bf75bce2a6`, pack
`ea98d75560d5ccc58f597ffab040fee7ae8af7b9e38f9b8496b55f1aa296c4bb`.
Those artifact identities are master-supplied, not rehashed by this reader.

Actual deployed `app.js`, `atlas.js`, `session.js`, `polling.js` and
`atlas-state.js` matched the primary checkout byte for byte and frozen **8ef3ece**
after checkout newline normalization. The native **Start world** job
`a1dd3a31212c4fd2b89ca93f215b5035` was complete at **19:24:10.584603Z**;
the actual controller reported **online, PID2108**, with zero online players.
This establishes a successful master-triggered start through the integrated
controller. CONTROL did not issue the action or observe the entire preflight.

Browser smoke at **19:26-19:28Z** used the actual 8766 Application, not the prior
read-only harness. Atlas displayed real terrain and correctly dated last-seen KG
coordinates. Searching **Willow** found one historical named-entity observation;
switching to Nether removed that Overworld result, and returning restored it.
The integration panel explicitly described the partial/unverified adapters.
Performance displayed live TPS/MSPT, process CPU/RSS, heap, history and the
Overworld's **841 holders / 49 full / 25 block-ready / 9 entity-ready**, with
zero pending unloads and zero saved vanilla forced chunks. The diagnostic cost
shown was **0.68 ms**, one observation. Idle-branch eligibility was labelled
separately from actual entity/block-entity tick executions.

Players/access showed the two real offline whitelist entries and operator levels
3 and 4. Settings, storage, 208-file candidate.51 mod inventory, retained backup
records and Connectivity loaded. Task history showed the actual completed start.
No permission/configuration/mod/backup/tunnel controls were invoked. Playit was
stopped, unlinked and externally unverified. The recorded browser event window
contained **zero non-GET requests, zero JavaScript exceptions and zero console
warnings/errors**. The browser tab was closed after the smoke.

At **19:29:16Z**, one bounded GET set measured overview **82.840 ms**, metrics
**17.222 ms**, jobs **2.276 ms**, Atlas **11.882 ms**, chunk diagnostics **2.696 ms**
and sync **1024.206 ms**. Metrics were **19.9987 TPS / 2.390742 MSPT**,
RSS **4,255,727,616 bytes**, heap-used **2,150,090,088 bytes**, and 30 entities.
Atlas inventory remained **26 tiles / 526,213 bytes**, measured19:29:01Z in
**47 ms**; actual tiles had changed19:27:03Z. These are individual uncontrolled
observations, not a sustained overhead or benchmark acceptance. Python RSS was
approximately **46.5 MB** at19:28Z. A qualification-script request to the incorrect
`/static/app.js` route first returned404; the source-declared `/app.js` route was
then used. That probe mistake is retained in the private receipt.

Private receipts: `runtime/verification/integrated-native-candidate51.json`,
`integrated-browser-candidate51.json`, `integrated-atlas-candidate51.png` and
`integrated-performance-candidate51.png`. None is committed. The 19:29:33Z guard
passed a bounded4MiB C allocation with **122,117,562,368 C bytes** and
**284,115,083,264 D bytes** free. This monitors owned writers; it does not constrain
external applications or pre-existing writers.

## Requirement-by-requirement acceptance boundary

The implementation and safe fallbacks are integrated. Full goal acceptance
remains open where native mutation, remote clients or missing adapters are named
below. A visible button or a synthetic test alone is not runtime acceptance.

| Requested capability | Current evidence / exact remaining boundary |
| --- | --- |
| Start, stop, restart, status | Integrated master-triggered start and actual online status proved. Earlier master stop observed on old controller. New-source native stop/restart cycle still needs the master's serialized window. |
| Startup failure | Actual isolated browser EULA refusal and correct failed task; mocked child-exit/readiness regressions pass. No deliberate installed native startup failure was induced. |
| TPS/MSPT and history | Actual integrated browser and fresh bridge values proved; measured history is displayed. Sustained finished-world load qualification belongs to performance/master. |
| CPU, RAM, heap, disk | Actual process/host/heap samples and cached storage inventory displayed. Disk measurements show age and managed-writer coverage. |
| Chunk-holder/ticking diagnostics | Actual native holder, ticket, ready-range and idle-input records displayed. They do not establish individual entity/BE tick progress. |
| Player locations, permissions, whitelist, operator levels | Actual offline access records and historical coordinates displayed; expiry/permission safety tests pass. Live player movement and native access edits have not been exercised by CONTROL. |
| Backups, restore, recovery | Real retained verified backup records displayed; synthetic exact-byte restore/corruption/traversal tests pass. No official-world restore performed. Native recovery remains master-owned. |
| Configuration and optimization | Actual forms load; isolated save/reload and stale-edit/seed/restart protections tested. No installed server setting changed by CONTROL. |
| Packwiz management/update state | Actual candidate.51 pinned inventory and sync endpoint available. No remote version lookup, candidate deployment or rollback performed by CONTROL. Inventory entries correctly retain runtime-pending status. |
| Transport/Create diagnostics | Source contract linked above; no continuous dashboard/network-train feed consumed. Candidate.51 native observer commissioning is TRANSPORT/master-owned and does not establish Atlas integration. |
| Population/wildlife diagnostics | Actual aggregate entity counts and historical named entities available. No species/population-health dashboard adapter is integrated; no census or unsupported wildlife API is claimed. |
| Playit | Actual stopped/unlinked state and missing local IPC reported; protocol/redaction/action tests pass. Starting/linking/remote joining remains owner/master work. Dashboard remains loopback-only. |
| Safe errors and task history | Durable interrupted-job, bounded/redacted error tests and isolated backend restart/session recovery passed; actual integrated start history displayed. Native backend restart with an active job was not induced. |
| Accurate current map tiles | Six real map batch receipts reconciled to two actual files/HTTP bytes; integrated UI serves actual changed terrain cache with separate render/measurement times. Every final-world edit/pixel is not yet qualified. |
| Search, waypoints, shared collections | Actual historical location search/dimension filtering proved; isolated waypoint create/search and atomic shared/private import/export tests pass. No native shared waypoint mutation performed. |
| Live player markers/dimensions | Native dimensions and offline last-seen markers displayed; expiry tests pass. Zero-player smoke cannot establish live movement or cross-dimension player tracking. |
| Claims/parties | Actual current zero-claim snapshot displayed; independent45s expiry and bounded geometry tested. Nonempty boundary display and party membership/permission editing have no runtime proof; party editor has no verified adapter. |
| Xaero/MapHorizons sync | Explicitly unverified; Atlas JSON exchange does not synchronize client files or DH/MapHorizons tiles. No suitable automatic adapter has been qualified. |
| Structures | Actual discovered records with observation times displayed/searchable; source evidence preserved by annotation tests. |
| Moving objects, trains, ships, airships, named pets | Historical named entities visible; supported loaded entity observations are freshness-bound. Continuous train-network/virtual-airship positions have no verified dashboard adapter. No current vehicle movement was observed. This is not a claim that all upstream APIs are impossible. |
| Safe teleport / return history | Bridge/dimension validation and bounded audit behavior tested synthetically. No actual human player teleport or return was performed. Master-controlled player participation is required for native acceptance. |
| Mobile, async work, polling | Actual isolated390x844 menu dismissal/no horizontal overflow, delayed-response navigation race and backend reconnect passed. Controlled Node tests prove hidden/overlap/backoff behavior; IAB did not expose a genuinely hidden tab in that run. |
| Local security | Actual listener127.0.0.1:8766 and origin/token/loopback regressions verified; public connectivity instructions target only25575. No public dashboard exposure or tunnel reconfiguration performed. |

For final release, master should serialize the remaining native stop/restart and
checkpoint/recovery qualification, real player movement and approved teleport/
return, any approved access/configuration edits, and remote Playit/client joins.
Reuse the existing single runtime and preserve both named saves. Unsupported or
unverified sync/party/vehicle/population adapters remain explicit limitations;
they must not be replaced by invented positions or broadened sprint features.

## Recovery browser follow-up: event-driven backup feedback

Follow-up source commit **ebe9cb6d7f912ddc6b48f6503b21a90a2e98bd7c**, branch
`codex/control-room-recovery-feedback`, changes only `static/app.js` (+3/-1).
Actual browser creation completed, but the Backups page retained its empty list.
The correction refreshes the list once after a newly observed terminal task,
deferring while a dialog is open. It adds no recurring backup inventory polling.
The second archive appeared automatically in the browser without reloading.
Syntax and diff checks passed; the frozen PR#1 remains unchanged.

The isolated home is `runtime/recovery-browser-home` in this owned worktree.
Its files explicitly contain **synthetic fixture payloads**, not a Minecraft
save. No Minecraft JVM, server installation or EULA acceptance was involved.
Actual browser/HTTP/job/ZIP/filesystem operations established:

- Backup `20261028T193247Z-cbe85c` completed as job
  `36686a7dc5dc4ae8bdc511423602e799`, four files/9,244 source bytes/1,942 ZIP bytes.
- Wrong restore confirmation failed job `fb5aa1af111c4709bf8c1454dab818b2`
  without changing any fixture byte or creating a replacement directory.
- Correct restore completed job `ec7e4a10440e4698bee3f85ff5d814f5` at19:34:16Z.
  Exact original level/config bytes were restored; exact newer bytes survived in
  `pre-restore-20261028T193416Z-67f8f4`. EULA remained false.
- After completed tasks and child/process ownership checks, only the isolated
  backend was restarted: Python6412 -> Python50280. The same browser reconnected
  and retained all four prior task outcomes. Its old-token Verify request received
  **403 -> bootstrap200 -> POST200**, creating exactly one verification job.
- Deliberately corrupting the second test archive made Verify fail accurately:
  job `533fba071cf44d77948cd99224c09d68`, **Backup archive hash mismatch**.
  The original second ZIP bytes were preserved separately. The valid first
  archive and restored files were untouched.

The last check also exposed an existing reporting gap: the failed archive's
creation receipt and list badge still say **verified**. This does not bypass
restore verification, but it is misleading after a known failed check. Narrow
`Backups.verify/list` ownership was requested from the master at19:37Z for an
explicit cached verification outcome/timestamp. Until corrected, inspect the
failed verification task; do not infer current integrity from the creation badge.

Receipts are `runtime/verification/recovery-browser-result.json`,
`recovery-browser-reconnect.json` and `recovery-browser-restore.png`; raw failed
navigation and startup logs remain private. The first browser open preceded
listener readiness and was refused; the owned process stayed alive and was not
restarted on that observation failure. All of this is browser/file-backed
qualification with synthetic payloads, not native Minecraft recovery acceptance.

### Corrected explicit verification outcomes

The master granted source-only `Backups.verify/list` ownership. Focused source
commit **92ea1c858d6c22c149f7a1f0983f31e9a2087ba3** resolves the stale integrity
badge described above. It preserves the original creation JSON **byte for byte**,
the original expected SHA and all archive bytes. Separate bounded16KiB
`<backup-id>.verification.json` records store the explicit check time/outcome.
Pending/failed result writes cannot advertise a newly successful check: unknown
is persisted before reading, then replaced by the terminal result. Verification
holds the existing mutation lock and reserve/checkpoint protections.

List reads never hash an archive. They read cached outcomes and compare only
size, mtime/ctime, inode and device; changed archives become **unknown** until
explicit verification. Oversized/malformed sidecars are unknown and excluded
from the backup list. Original SHA validation bounds the ledger allocation.
The UI distinguishes a recorded **Last check** from historical **At creation**.

**10 focused tests passed** (eight new plus the two existing backup tests),
including corrupt/archive-change/reopen behavior, exact provenance preservation,
no hashing in list, reserve refusal, terminal-write failure and bounded metadata.
Independent source review found no blocking regression; both suggested bound
checks were added. Syntax/diff checks passed.

Actual browser task **e42c74163cc94707b755ce1c4e04e23e** correctly failed the
damaged fixture archive at19:42:39Z. The automatically refreshed row displayed
**failed · Last check Oct28,3:42PM**. Screenshot:
`runtime/verification/recovery-corrupt-archive-corrected.png`. The test backend
was retired after all jobs were terminal; Python44196 and port18765 were verified
gone, with no remaining child process. Its peak observed RSS was about39.5MB.
Source/fixtures/valid and damaged ZIPs/failed receipts remain preserved.

Deployment: selectively integrate **ebe9cb6** for event-driven list refresh and
**92ea1c8** for verification outcomes; the intervening **4a7eb1a** is documentation
only. Reload browser tabs after the JavaScript change. The Python change requires
a master-scheduled controller restart; do not stop the controller while it owns
a live Minecraft process. The native7068 controller still ran the prior integrated
8ef3ece implementation during this follow-up. No live backup revalidation or
native restore was dispatched by CONTROL.

## Actual integrated native51 stop / native52 start

The master granted a GET/UI-only observation window for its own stop, retained
recovery checkpoint, Java upgrade and start. The native controller stayed Python
**7068**, serving the integrated8ef3ece implementation. CONTROL issued no lifecycle
POST, command, configuration change, client input or extra JVM.

- **Stop world** job `51af474fc0324516bf6a1763e7428e27` completed
  **19:43:21.246934Z**. At19:43:44Z, actual overview state was offline, PIDnull.
  Performance cleared current tick/process/heap/chunk values and retained history;
  Atlas retained dated last-known locations and marked live observations unavailable.
- The same controller's **Start world** job
  `b15e21807d9147c5bba21907bb1cede3` was created **19:45:19.559019Z** and actually
  running at19:46:04Z and19:46:50Z. Its owned Java PID was **49072**. The browser
  stayed responsive and showed starting, with a readiness message and unavailable
  current telemetry. No new HTTP timing measurement was established in this phase.
- By the **19:48Z browser observation**, that exact start was complete; its result
  said online/PID49072, with a snapshot evaluated19:47:40.939526Z. Overview showed
  candidate.52 online and zero online players. Performance recovered current
  **20 TPS / 3.5 MSPT**, **3.77GiB RSS / 1.22GiB heap-used**, 841 holders and30
  entities. These are rounded single UI readings, not load/overhead acceptance.
  Startup briefly showed24.1MSPT before the later3.5MSPT observation.
- Atlas recovered current bridge observations and renderer availability/queue0;
  its existing26-tile cache and historical positions remained visible. Browser
  console inspection had no warnings/errors. The active observer tab was closed.

This proves a real integrated **stop -> upgrade -> start** cycle and display
recovery. The dedicated Restart button/endpoint was not invoked. Installed-game
restore, live-player teleport/return/access edits, remote tunnel joins, finished
world load and final official promotion remain unqualified. The separate test
backend's restart/session/restore proof above uses synthetic file payloads.

Private receipts: `native51-52-cycle-offline.json`,
`native51-52-cycle-starting.json`, `native51-52-cycle-browser-online.json`,
`native51-52-cycle-online.png`, `native51-52-performance-offline.png`,
`native52-performance-online.json`, and `native52-atlas-online.txt`.
At19:47:02Z the bounded16MiB C writer forecast passed, with C122,091,675,648 and
D283,824,701,440 free bytes. Owned-writer monitoring is not an OS quota and does
not constrain unrelated applications or pre-existing writers.

Automatic approval review rejected an optional read-only startup timing script,
returning only **blocked by policy**. It was not executed or substituted with a
timing claim. The permitted browser state/readiness observations above completed.

## Offline access browser qualification and accurate removal outcomes

Source commit **e9ecbfd2d4b4ff7c45117ecf5db5ffa2b93e1bec** changes only the final
level0 result in `Players.permissions`, plus three regression tests. The master
granted this narrow source-only scope. All permission/session/native-running and
snapshot concurrency gates remain intact. A confirmed operator removal returns
an operation receipt rather than re-querying an identity that may intentionally
have left all roster sources. It does not add whitelist access, recreate a roster
entry, or return an invented current presence/location.

The actual browser used `runtime/access-browser-home`, clearly labelled
**DISPOSABLE TEST**, with no game install, no world and EULAfalse. Synthetic
`ControlFixture`/`OpOnlyFixture`/`FixedOnlyFixture` identities were test file data.
Only public Mojang name/UUID lookup was used for KG's separate test whitelist
add/remove; no account authentication or actual native player change occurred.

- Operator level2 save completed **8bd1a9e1e51541169d6ba6006c2290f0**.
  Level3 with player-limit bypass subsequently completed **453dbc1eb6fc4381a56c554d9ceee10d**.
  Invalid member+bypass was rejected in the UI before submission. Offline game
  mode/XP controls were disabled and location was unavailable.
- Mojang verified KG's public name/UUID before the add confirmation. Test-only
  whitelist add **a359d29f4c384191a5274debaadfdb6d** and removal
  **fd26bf5d43804860961eb7c316e6afcf** completed. Final test whitelist retained
  only its synthetic ControlFixture entry; the native whitelist was untouched.
- The pre-fix operator-only demotion **601c195968ec462ab6c260fb883c8e5f**
  incorrectly failed after ops removal and a **19:53:14.175147Z** confirmed audit.
  That failed task and bytes were preserved. An independent in-memory review
  reproduced the same final-lookup defect.
- A separate synthetic identity tested the corrected source after restarting
  only the owned Python backend. **cf153566d20b42f6a3cd3dfe7cfc6182** completed
  with level0/persistenceconfirmed, no online/location fields, and no remaining
  operator or whitelist identity. Whitelisted ControlFixture demotion
  **9ebd821c31f649708ca71f83d6e26ae0** also completed while preserving its whitelist.

**Six focused tests passed** (three new plus existing PlayerTests), covering the
real task outcome, retained whitelist access, rejected confirmation and failed
persistence. Independent review found no regression; diff checks passed. Actual
browser console inspection showed no warnings/errors. This is actual UI and
file-backed offline qualification, not live permission enforcement acceptance.

Private evidence: `access-browser-before-result-fix.json`,
`access-browser-after-result-fix.json`, `access-operator-removal-complete.png`,
ownership records and `access-browser-retirement.json`. After all tasks became
terminal, the browser closed and both owned Python PIDs53840/52868 were retired;
port18765 was released with no child process left. Final observed helper RSS was
about39.9MB. The 19:55:08Z bounded128MiB C forecast passed with C122,084,089,856
and D283,807,010,816 free bytes; unrelated/pre-existing writers remain outside
this monitoring rule.

Source pickup queue is now **ebe9cb6**, **92ea1c8**, **e9ecbfd**, on
`codex/control-room-recovery-feedback`; documentation commits may be selected
separately. Native7068 still used the prior integrated8ef3ece Python code at this
observation. The two Python follow-ups require the master's scheduled controller
restart; Java-only upgrades do not deploy them.

## Current integration boundary, 19:58Z

The master has integrated the three follow-ups into `codex/master-integration`:
**b6b6971** (backup list refresh), **9f7bbe8** (verification outcomes) and
**9793130** (confirmed permission removal). Git blob identities for the three
implementation files and both new test files exactly matched this worktree;
those primary-checkout files had no uncommitted differences. This is source
integration, not main/public release or deployment of new Python bytecode.

The actual8766 listener was still Python7068, created19:21:07Z, predating both
Python fixes. No owned test process or18765 listener remained. The next meaningful
native step is the master's scheduled controller restart and read-only smoke of
the deployed follow-ups. CONTROL has no current native-write lease and must not
restart that controller/server to manufacture acceptance.

Full goal completion remains unproved: dedicated Restart endpoint, native
backup/restore recovery, live player movement/teleport/return/access enforcement,
remote Playit joining, final-world overhead/official promotion, and acceptance of
the explicit unverified sync/party/vehicle/population adapter limits remain open.
The same native/participant acceptance dependencies persisted across the last
three goal continuations while independent source/browser fixes were completed.
There is now no remaining independently authorized implementation correction
identified by this audit. Resume qualification when the master supplies the next
controller window or real participant evidence; do not replace these gates with
additional synthetic checks or broaden the frozen feature scope.

## Candidate.53: real controller replacement and deployed follow-ups

The master supplied a new read-only observation window. Actual stop job
**dda61adce0184f1680cb430d1b010281** completed **20:04:56.548175Z**. Old Python7068
and its8766 listener were observed gone while the game was offline. Replacement
Python **27636**, created **20:06:55.673224Z**, ran `python -B -m control_room` from
the master checkout with homeH/port8766. The three integrated files remained clean
at master **979313075cb56827b331f71685ea006591742b56**. Actual `/api/backups` now
returned **creation_integrity**, independently confirming the new list model was
running rather than only present on disk.

The existing browser visibly changed from **Connection lost / live data stale**
to **Connected locally** without reloading. All four prior native start/stop
records survived the real controller replacement. New start
**73da759b3ccf4ca9bcfb7385a3fa6918**, Java **45036**, stayed running/starting until
readiness and completed **20:10:20.488229Z**. The UI then showed candidate.53
online/zero players. This closes the previously pending controller-deployment
and real inactive-job-history recovery gates; it does not exercise a native
permission edit, verification mutation, restore, teleport or remote session.

Actual browser Performance recovered **20TPS / 3.4MSPT**, 841 holders/30entities,
3.34GiB RSS and1.33GiB heap-used. Atlas recovered current bridge/renderer/queue0,
real26-tile cache and dated historical records. Recorded CDP events contained
**zero non-GET requests and zero JavaScript exceptions**; console warnings/errors
were empty. At20:12Z, a separate GET sample reported **20.0147TPS / 3.1341MSPT**,
RSS3,647,414,272bytes and heap-used1,558,183,936bytes. These remain individual
observations, not finished-world load or attributed dashboard-overhead acceptance.

Private receipts: `native53-new-controller.json`, `native53-final-get.json`,
`native53-browser-recovery.json` and `native53-atlas-recovered.png`. The read-only
observer closed. No lifecycle/control/player/tunnel/world write was performed by
CONTROL; native operations were the master's. Public/permanent-world promotion
has not been established.

### Initial-history notification correction

Fresh native tabs also exposed a small alert defect: initial history loading
announced old completed tasks as though they had just finished. Source-only
**e77ff88c5b4f0db82dc142197a03c315676a8394** changes `app.js` (+2/-1) to seed seen
terminal jobs silently on the first successful load. Later task transitions keep
the existing alerts and event-driven backup refresh. No polling or backend change
was added; deployment needs only master integration and browser reload.

Browser repro saw **Start world finished** from historical data on fresh load.
A temporary source-asset interception attempt was unsupported by this browser;
no response body was substituted, all interception patterns were cleared and that
tab closed. The existing READ-ONLY QUALIFICATION harness then served the frozen
new frontend against actual native GET data. Corrected first load had an **empty
toast**, while all **five real history records** remained accessible. No console
warning/error occurred. Syntax/diff checks passed. This qualifies the frontend
behavior, not a new native control action.

Private receipts: `notification-history-quiet.json`, `notification-history-quiet.png`
and `notification-qa-retirement.json`. The reader used about37.6MB RSS, no game
child/lifecycle, and rejected control requests by construction. Python52060 was
retired, port18765 released, and the observer tab closed. Its bounded32MiB C
forecast passed at20:15:24Z with C122,011,160,576 and D283,501,723,648 free bytes.
Monitoring covers owned writers and does not constrain unrelated/pre-existing
writers. Remaining native/player/remote/API-limit/final-release gates above stay
open; the actual .53 controller replacement does not prove them.
