# A WORLD FOR TWO
## Ancient Civilizations, Lost Temples, Ruins & Archaeology Expansion

**Repository:** https://github.com/Kgray44/a-world-for-two

**Project:** A World for Two

**Directive:** Expand the existing Minecraft 1.21.1 NeoForge modpack with spectacular naturally generated ancient temples, lost civilizations, archaeological sites, ruins, and massive adventure structures.

This addendum supplements all existing requirements. Implement it within the current build, preserving the existing mods, optimizations, and Control Room functionality.

**Primary objective:** Make exploration genuinely breathtaking. We want enormous ancient pyramids emerging from jungles, mysterious forgotten civilizations, underground chambers, intricate traps, puzzles, hidden treasure, and rare discoveries that feel truly special.

## 1. High-priority additions

Investigate and prioritize integration of all the following:

### Epic Structures: Jungle Temples
- Massive Aztec/Mayan-inspired jungle pyramids
- Ancient temple complexes
- Multiple structure sizes
- Rare, impressive world-generation landmarks

### Aztec Temple & Ruins
- Ancient temples and settlements
- Overgrown jungle ruins
- Lost villages and structures
- Hidden rooms and treasure

### YUNG's Better Jungle Temples
- Expanded jungle temples
- Traps, puzzles, and secret rooms
- Better treasure and exploration
- Existing Create/Supplementaries integrations where supported

### YUNG's Better Desert Temples
- Large redesigned desert temples
- Complex interiors and challenges
- Traps, puzzles, and distinctive loot

### Archaeology Ruins
- Abandoned archaeological sites
- Ancient structures and excavation areas
- Buried chambers and secrets
- More rewarding exploration

**These five are the primary implementation priorities.**

## 2. Additional structure mods

Also investigate and attempt to integrate:

### Ancient Structures
- Mayan, Roman, Japanese, and other civilization-inspired structures
- Themed guardians and treasure
- Ancient architectural variety

### Philip's Ruins
- Numerous naturally generated ruins
- Buried structures and hidden treasures
- Atmospheric abandoned locations

### When Dungeons Arise
- Massive dungeons, fortresses, palaces, and towers
- Large-scale exploration challenges
- Unique landmarks and adventure opportunities

### Moog's Temples Reimagined
- Additional redesigned temples
- Larger and more elaborate structures
- Expanded adventure locations

Include these where compatible and reasonably efficient.

**Important:** Do not install multiple incompatible replacements for the same vanilla structure. For example, investigate overlap between YUNG's temple overhauls and Moog's Temples Reimagined, then select the best functioning combination.

Every named mod must remain accounted for in the compatibility inventory.

## 3. World-generation integration

Verify compatibility with:

- Minecraft 1.21.1 + NeoForge
- Tectonic
- Terralith
- Regions Unexplored
- Existing biome expansions
- Existing pirate structures
- Existing castle and fortress generation
- Existing ocean structures
- Distant Horizons + SeedGen

Test structure generation in disposable worlds before enabling the final configuration.

Prevent:
- Overlapping structures
- Temples spawning incorrectly inside mountains
- Floating or buried entrances
- Structures cutting through unrelated landmarks
- Excessively frequent large structures
- Broken terrain or biome placement
- World-generation crashes

Prefer **rare, enormous, memorable structures** over constant small repetitive discoveries.

Configure structure spacing and frequency where supported.

Do not assume that distant visual LOD generation includes accurate structure representations.

## 4. Performance requirements

The server and Minecraft client run simultaneously on KG's 32 GB gaming laptop.

Performance remains a critical requirement.

- Minimize unnecessary background processing.
- Benchmark fresh-chunk generation.
- Measure server TPS/MSPT during exploration.
- Test the impact of generating enormous structures.
- Limit unnecessarily expensive structure and mob spawns.
- Avoid generating huge unexplored regions just for structure indexing.
- Ensure structure mods do not conflict with server optimization mods.
- Preserve normal Minecraft gameplay performance after structures have generated.

Structure generation should be efficient and appropriately distributed.

Do not sacrifice stability merely to install every available structure mod.

## 5. Control Room: World Atlas integration

Expand the existing World Atlas system to support these new structures.

Desired features:

- Display genuinely discovered temples and ruins.
- Show actual structure coordinates.
- Identify structure types.
- Search and filter ancient locations.
- Create custom waypoints for discoveries.
- Organize landmarks by civilization or structure category.
- Track discovery dates where available.
- Allow KG and Sera to save notes about explored locations.
- Mark locations as explored or unexplored.
- Support safe administrator teleportation using the existing World Atlas permissions system.

If reliable server-side structure discovery hooks exist, use them to index locations automatically.

Do not repeatedly scan unloaded chunks or entire dimensions.

Never display guessed locations as confirmed structures.

Distinguish actual discovered locations from predicted or manually entered waypoints.

## 6. Preservation and compatibility

Keep every previously approved feature, including:

- Create machinery and trains
- Ships and pirate content
- Fairytale castles and fairies
- Wildlife and animals
- Advanced Weather
- Cozy building and homesteading
- Photography and letters
- Distant Horizons + SeedGen
- Server optimizations
- Custom cinematics
- Control Room
- Existing mapping and navigation systems

Do not reintroduce Roxy or Voxy.

Do not remove unrelated content to make room for the new structures.

If an unavoidable incompatibility occurs, document the conflicting mods, attempted solutions, and selected alternative.

## 7. Testing and deployment

For each candidate:

1. Confirm exact NeoForge 1.21.1 compatibility.
2. Identify dependencies and installation requirements.
3. Pin a compatible release.
4. Add it to the Packwiz configuration.
5. Verify client/server separation.
6. Generate disposable test worlds.
7. Confirm the structures actually appear.
8. Verify loot, traps, and encounters where feasible.
9. Measure generation performance.
10. Test server startup, shutdown, and world persistence.
11. Verify compatibility with the complete modpack.
12. Update the compatibility inventory and Control Room mod manager.

**World integrity is extremely important.**

New structures may only generate in newly created chunks. Preserve existing world data and create backups before changing world generation.

Do not reset or regenerate the permanent world without explicit authorization.

## 8. Final vision

KG and Sera should be able to travel through enormous jungles, discover gigantic ancient pyramids, explore ruined civilizations, solve puzzles, navigate hidden chambers, recover legendary treasure, and document their discoveries.

Some temples should be so enormous and rare that discovering one feels like a major adventure.

The world should reward exploration with genuine surprises and memorable places.

**Prioritize the five primary mods, evaluate all additional candidates, and integrate the largest stable and performant combination possible.**

Preserve all previous requirements, keep everything properly synchronized through Packwiz, and maintain reliable multiplayer.

Implement this expansion as part of the current A World for Two build.