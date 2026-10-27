# Candidate.12 release draft

Development candidate; not a finished stable release.

- Minecraft 1.21.1, NeoForge 21.1.262, Java 21.
- 197 enabled mod JARs, 8 shader packs, one resource pack.
- Full Control Room source, original menu artwork, pinned Packwiz metadata and compatibility decisions are on main.
- Playit service controls are integrated and native stop/start tested.
- Local client/server join and the new crafting-table animation are owner-confirmed.
- Controlled chunk-ticket testing attributes the old 1,682 holders to spawn plus nine deliberate force-load tickets; no persistent leak was observed after removal.

The attached Prism starter r2 passes archive and pinned-updater checks. Fresh Prism import, public updater downloads, complete feature acceptance and remote two-player sync remain pending. SeedGen's modded registry loading is repaired, but a server fingerprint serialization failure currently disables client prediction. Do not promote this draft into a permanent world or present it as a qualified release.
