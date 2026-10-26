# Build and acceptance status

2026-10-26 snapshot, candidate.12. Exact pins and hashes: `catalog/lock.json`.

## Observed

- 197 enabled mod JARs, eight shader packs and one resource pack. Client and server
  subsets differ by side; the overall count is not the dedicated-server JAR count.
- 53 local Python tests and four JavaScript session tests pass; Packwiz integrity passes.
- One licensed player joined candidate.9 and confirmed the intro returned control
  and the furnace interaction scene worked.
- Gameplay commonly measured ~20 TPS, 7â€“14 ms/tick and focused 59â€“60 FPS. Some samples
  had under 1 GiB system RAM free. This is one laptop/player, not remote two-player acceptance.
- A `/locate biome` search took ~23.3 seconds. Minecraft typing/item-search delays
  and slow terrain arrival during fast travel remain under investigation.
- Clean post-disconnect idle: 841 Overworld holders, 49 full chunks, 25 block-ticking,
  nine entity-ticking, zero forced chunks and one spawn ticket; Nether/End zero.
  About 20 TPS / 1.15 ms per tick. Holder counts are not fully simulated chunk counts.
- Native Playit 1.0.10 service stop/start passed with the account and tunnel retained.
- Candidate.12 owner confirmed responsive chat/search and a working newly placed
  vanilla crafting-table animation. The controlled nine-chunk ticket experiment
  reproduced 1,682 holders exactly and returned to 841 five minutes after removal.

## Updated candidate repairs

SeedGen's earlier vanilla fallback followed missing client worldgen codecs/mods.
Nine exact worldgen mods now install on both sides. Candidate.12 successfully reads
253 biomes and fingerprints the client's modded data. A second server-side failure,
`Calling .codec() on HolderHolder`, prevents a matching server fingerprint. SeedGen
therefore stands down on the client and DH downloads terrain. That failure remains unresolved.
Visual Workbench converted vanilla tables into its own block, preventing Cinematic
Interactions' vanilla match. A native tag now preserves new vanilla tables, and the
owner verified the new table animation; existing tables/inventories are not replaced. The generic CI server reminder is marked seen
while full client/server mode stays selected.

Atlas surface landing now searches real terrain height within one chunk. SQLite
history commits before checkpointing and closes handles. Storage scans run in the background.

## Remaining

Native repaired SeedGen/table/teleport acceptance; taller mountains/deeper valleys
within -64..319 in disposable terrain comparisons; chunk-generation and input-stall
profiling; shader/weather/Create/Sable rendering; transport/logistics multiplayer,
restart and chunk crossings; worldgen, structures, loot and traps; claims, pets and
giant trees; remote two-player sync; restored-world restart; fresh Prism import and
public updates. Advanced pirate/physics candidates remain isolated pending tests.

The permanent world has not been replaced or promoted. Staging cleanup waits for
acceptance; unique worlds and failed receipts remain preserved.
