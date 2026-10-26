# A World for Two

This repository is the sole development target. Inspect `Kgray44/kg-minecraft-pack` read-only.
Never commit worlds, credentials, downloaded third-party JARs, logs, or caches.
Never accept Minecraft's EULA, authenticate player/tunnel accounts, replace a permanent
world, or publish an untested pack on the owner's behalf without the required owner input.

## AERO X16 storage reserve

Keep at least 32,212,254,720 bytes free separately on C: and D:. Before a writer,
bound its maximum allocation on each drive and run Windows PowerShell with
`C:\Users\kkids\AppData\Local\AeroStorageWatch\ReserveGuard.ps1
-EstimatedCBytes <bytes> -EstimatedDBytes <bytes>`. Pass zero for an untouched drive.
Unknown or unbounded estimates fail. Recheck every five minutes during long writers
and before clones, builds, worktrees, transfers, or cache fills. Checkpoint owned work
if either reserve is reached. Preserve unrelated data, unique history, and evidence.
This monitoring instruction does not constrain external applications or existing writers.

## Verification

Use Python 3.12+ and Java 21. Run `python -m unittest discover -s tests -v`,
`python -m tools.pack validate`, and `node --check control_room/static/app.js`.
Record real runtime results separately from synthetic tests. No invented TPS, remote
sync, two-player acceptance, graphics, or benchmark claims. Every requested mod must
remain in the compatibility inventory, including unresolved and incompatible items.
