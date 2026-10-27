# Create startup failure and backup reporting

The official candidate.31 world started successfully at 11:24:30 UTC on
2026-10-27. It stopped normally at 11:29:23 for the scheduled six-hour backup.
All dimensions saved before the archive was created. The subsequent automatic
resume failed during Create 6.0.10 registration at 11:30:10. This was a failed
restart after a successful save, rather than a crash while players were building.

The verified archive is `20261027T112924Z-6caa88`, 134,089,235 bytes, SHA-256
`a02992c61d3dda5740686fff384dd8d86bd590d051c65f4ebe6bdef314afb4f8`.
The preserved native crash report has SHA-256
`3f0ebcf949b652726ab6628ab81087234ea988660fea54f35d96a368bd3dd2d7`.
It reports an unbound `create:chocolate_bucket` while Create initializes its
advancement triggers. The item registry event occurred before the trigger event;
the logs do not establish an event-order reversal.

## Control Room correction

NeoForge returned Java exit code zero despite its native startup error. Control
Room previously replaced that failure with an ordinary offline state, and backup
creation observed only Java launch when reporting resume success.

The corrected reader retains recognized native startup failures, persists the
warning across a dashboard reopen, and prevents a draining former JVM reader
from changing a newer process's state. Backup resume now waits for Minecraft's
actual readiness message. A valid backup and a failed resume are recorded as
separate outcomes. A timeout leaves a still-running owned JVM alone.

The full local suite passed **330 Python tests**, 207-entry Packwiz manifest
validation, JavaScript syntax validation and four Node session tests. Eleven
focused lifecycle tests cover these failure cases without launching a JVM. These
checks do not prove a repaired native Create startup.

## Registration investigation

The pinned Registrate `+67` registration table has a single writer method,
`AbstractRegistrate.accept`, and an unsynchronized table. A fixture using the
actual installed class reproduced planned entries being available by lookup but
absent from registration iteration under concurrent writers. Sequential writers
did not lose entries. This establishes a concrete race mechanism; the exact
concurrent caller in the failed full modloader run is still unisolated.

A proposed compatibility plugin adds only the JVM synchronized method flag to
that exact per-instance writer. It verifies the original class, method descriptor,
access flags and executable body first. It preserves the method body and uses
the JVM's exception-safe monitor release. Production-transformer fixtures passed
ten concurrent rounds without missing entries and rejected changed targets.
Native modloader activation remains a separate commissioning step.

The unchanged official recovery start was rejected by automatic approval review
with only `blocked by policy`; it was not executed or retried through another
route. The saved world, original failure, backup and isolated diagnostic receipts
remain preserved. A materially changed candidate needs its own bounded test
before any official deployment.
