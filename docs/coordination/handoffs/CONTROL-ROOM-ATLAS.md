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
