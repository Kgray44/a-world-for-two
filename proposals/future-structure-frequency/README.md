# Moderate future-structure frequency — review proposal

This is an uninstalled parameter patch for four existing structure sets. It changes no mod version, template, loot, biome, salt, structure weight, spawn override, terrain noise or dimension. It is outside every active datapack directory. Existing explored chunks must not be regenerated or repopulated.

| Selected set | Canonical spacing → proposal, chunks | Separation, chunks | Frequency | Candidate-opportunity increase |
|---|---:|---:|---:|---:|
| Castle Shift castle | 96 → 92 | 32 unchanged | implicit 1 unchanged | 8.88% |
| Archaeology Ruins adobe ruins | 80 → 76 | 40 unchanged | implicit 1 unchanged | 10.80% |
| Archaeology Ruins mud potter ruin | 80 → 76 | 40 unchanged | implicit 1 unchanged | 10.80% |
| Archaeology Ruins mud school ruin | 80 → 76 | 40 unchanged | implicit 1 unchanged | 10.80% |

These are grid opportunities, not guaranteed buildings or a measured world density. Random-spread candidate cells have area `(16 × spacing)²`; the ratio is `(old spacing / new spacing)²` because frequency is unchanged. Biome eligibility, terrain fit, existing structure starts and exclusion checks reduce successful placement. A weighted structure set chooses among its entries; it does not place every entry per cell. Separation is an offset constraint within the placement algorithm, not a universal cross-mod exclusion radius.

The castle grid side changes from 1,536 to 1,472 blocks. The three archaeological grid sides change from 1,280 to 1,216 blocks. Both remain far apart compared with individual room templates. Castle Shift's existing ten-chunk village exclusion is retained. Adobe ruins remain restricted to their existing badlands biomes; pottery and school ruins remain restricted to the existing swamp/mangrove-swamp filters. This adds quiet smaller discoveries alongside a very modest increase in distinctive castles. Castle Shift's author describes configurable datapack placement and varied modular castles; Archaeology Ruins' author describes ruined buildings and excavations without changing vanilla structures. [Castle Shift](https://modrinth.com/mod/castle-shift), [Archaeology Ruins](https://modrinth.com/mod/archaeology-ruins).

The exact pinned JAR audit is in `source-audit.json`. The selected structure JSON has empty spawn overrides. The examined reachable templates contain no embedded entities or listed spawner, TNT, lava, fire, command or infested blocks. That is static source evidence, not proof that ordinary dark-room mobs cannot spawn or that every custom processor/terrain fit is safe. Mod-native materials and processors remain unchanged.

No increase is proposed for Japanese Ancient Structures templates that embed hostile mobs, Philip's hostile ancient/tower/field-stone ruins, giant Dungeons Arise structures, pirate camps, ocean fortresses, monuments, temples or settlements in general. Philip's decorative rock pool also uses a processor capable of producing infested stone bricks, so it was excluded from a cozy discovery increase. A strict Python gzip inspection of an Ancient Structures template failed; that uncertain family is held unchanged rather than bypassing its check. This does not establish a Minecraft runtime failure. These choices preserve the existing rare-adventure balance and avoid expanding hostile pressure near future homes.

`integration.diff` proposes only the four JSON spacing edits and the same four named changes in the existing `tools/worldgen_policy.py` generator. The generator must be changed with the overrides; otherwise an ordinary regeneration would restore the old values. Every other structure set and every existing exclusion stays unchanged. This patch adds no new placement set or global override.

Before any future integration:

1. Recheck the pinned mods and all canonical structure-set hashes using the read-only verifier below. A changed input requires a reviewed new proposal.
2. Deliver the identical Paxi datapack bytes to client and server through Packwiz. Preserve the terrain stack and strict SeedGen comparison. The existing SeedGen provider/parity gap remains independent; this proposal cannot establish or repair parity.
3. In a disposable same-seed copy, inspect the actual loaded registry values and generate a bounded, previously ungenerated test area. Check entrances, terrain fit, other-mod overlaps, entity pressure and generation cost against the unchanged profile. No runtime numbers are claimed here.
4. Preserve all existing FULL chunks, saved starts, explored terrain and player data. No chunk deletion, retrogen, feature replay or permanent-world generation is included. Changed grids can shift future starts near old frontiers and can change locate results; cross-chunk edges and untouched explored chunks need a real comparison before rollout.
5. Requalify the same client/server worldgen resources with strict SeedGen. Existing distant previews may reflect the old placement profile; do not silently clear personal maps or claim cached LOD fidelity. Use only an explicitly reviewed normal cache transition if one is needed.

```powershell
python -B proposals/future-structure-frequency/verify_proposal.py
# Optional exact installed-JAR pin check; read-only:
python -B proposals/future-structure-frequency/verify_proposal.py --cache "D:/A World for Two/caches/mods"
```

No native game, server, world, active config, Packwiz manifest or release is changed by either command. The storage reserve covers owned work only; it does not constrain unrelated applications or pre-existing writers.
