# Isolated material probe

Read-only diagnosis for Stylista grass/oak appearing flat after a pack switch,
despite the author archives containing height maps and BSL retaining its settings.
This helper is not part of the pack lock or public Prism export.

Build with `python -m tools.material_probe --client <owned instance> --libraries
<staging server libraries> --output <new build directory>`. It requires the exact
locked Iris artifact and the existing named 1.21.1 client. Build output includes
an example request; installation and starting a client are separate actions.

The helper only observes an `AWFT_Check_YYYYMMDD_HHMMSS` instance with a matching
owned-client receipt and an explicit local request. Every ten seconds in a loaded
world it records selected PNG providers/hashes, actual atlas sprite sizes and
whether the existing Iris normal atlas contains each expected sprite. It uses
`getHolder`, never `getOrLoadHolder`, and does not create or rebind textures,
change shader settings, move the camera/player, or edit world data. Only a bounded
local JSON snapshot and temporary file are written. No player identifiers appear.
An explicit `exit_after_sample=true` request uses Minecraft's normal stop path
after the receipt, allowing a bounded one-shot test and normal copied-world save.

Compilation and archive checks are not a runtime or visual pass. Keep the helper
outside production and the release package. Source is project-owned MIT code;
third-party classes/assets are compile-only and are not included in its JAR.
