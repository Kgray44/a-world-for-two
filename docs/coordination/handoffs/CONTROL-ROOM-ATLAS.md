# Control Room and World Atlas integration handoff

Owner: **Complete Control Room and WorldAtlas**, chat
`01a183b9-ca05-7ef2-8006-14b1d1d648e1`.
Branch: `codex/control-room-world-atlas`, based on
`3333bc60646cc594093063ed514a3e51246e35b0`.

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

Shared dependency reported to master: `Server.start` holds the status lock during
long preflight; `Players.snapshot` waits on the world mutation lock. These can
block HTTP reads during jobs. Narrow lifecycle/read-path fixes require serialized
file ownership and remain pending delegation.

Both C: and D: reserves were checked before writers and periodically. Most recent
pre-check at 18:25:57Z: C **118,559,727,616** free bytes; D **284,446,781,440**;
bounded C allocation **268,435,456**, D allocation **0**. Monitoring covers owned
writers only; external applications and pre-existing unrelated writers are
outside its enforcement.
