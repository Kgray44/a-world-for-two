# Enchanted expansion

The unpublished **0.2.0** stable-release build starts from private candidate.65, preserving Create
6.0.10, Sable 2.0.6, NeoForge 21.1.262, BSL 10.1.8, DH 3.3.3 and SeedGen 0.9.1.
The requested final delivery is a stable public release and rebuilt latest Prism
package. Source/staging work does not by itself authorize an acceptance claim.

## Exact additions

| Addition | Pin | Installation |
|---|---|---|
| Ancient Remnants | 1.5.2 / R7lHZHzN | Both |
| Fragmentum | 5.4.0 / kCXNhuIV, full NeoForge file | Both; one variant only |
| Create: Octo Arms | Author GitHub v1.6.0+mc1.21.1 | Both; mod ID `tentaworks` |
| DecoCraft | 3.0.11 / Z8xm2POI | Both |
| AstikorCarts Redux | 1.2.4 / JtPCk233 | Both |
| Diorama | 0.7.0+awft.1-neoforge-1.21.1 | Client only; native model API repair |
| Stylista LabPBR | 128x A26 / QSlyhOZA | Client resource pack |
| Roundista LabPBR | 128x R32 / k9qKuU9l | Client resource pack |
| Nautilus 3D | V2.2 / BYoL3YKt | Client resource pack |

The lock and Packwiz metadata contain the complete sizes, upstream URLs and
hashes. Official downloads are fetched unchanged. No resource ZIPs or third-party
JARs belong in Git. Stylista/Roundista retain their restricted licenses; public
128x availability does not grant redistribution. Nautilus remains AGPL-3.0-only;
its source is <https://github.com/FabianMPunkt/Nautilus3D>. The pack references the
author's platform download rather than repackaging or modifying the archive.

Production also contains bridge **0.6.64**, Tavern **0.1.14** and Easy NPC Core
**7.17.1** that the older repository lock omitted. Their exact installed bytes
are retained in 0.2.0 on both sides. The historical generic bridge builder still
targets candidate.65/bridge0.6.51; do not use it to replace the retained artifact.
Current source proposals and the native64 evidence preserve the later repairs.
The Tavern's existing server configuration is retained; its patron roster is
not recreated or replaced by this update. QA helpers stay outside the release.

Diorama's two legacy model call sites are repaired under MIT, with its license
and every other upstream class/resource retained. The source and native evidence
are in [the repair record](../compat/diorama/README.md). The exact patched JAR and
provenance are distributed as a pinned project compatibility asset.

Inventory Expanded 0.2.1 is pinned separately in
`catalog/enchanted-expansion.json`, outside the active lock and exports. Its actual
JAR requires NeoForge >=21.1.264 on both sides. Inspected older 0.2.0 and 1.0.6
files have the same minimum. The current ecosystem remains on 21.1.262; do not
silently upgrade it or run inventory experiments on a player's real save. A
separate 21.1.264 sandbox passed the full static graph and actual server startup,
save and shutdown with the beta, using a new world with no copied players. Client
inventory behavior and integrity remain unqualified, so it stays excluded. The
platform license and embedded MIT declaration also differ; neither is treated as
a redistribution grant. Qualification needs disposable inventories, Curios,
backpacks, crafting/containers/drag/stack operations, reconnect, restart and
removal recovery after a separately tested loader upgrade.

No verified public Loconautics release was found. The
[Ferronautics author](https://www.curseforge.com/minecraft/mc-mods/ferronautics)
identifies it as the intended successor, without providing a verified compatible
download. Ferronautics is not substituted. No railway construction is included.

## Select a texture preset

In Minecraft's Resource Packs screen, use this top-to-bottom order:

1. Nautilus3D-V2.2.zip
2. **Either** Stylista 128x A26.zip (Enchanted Fantasy) **or** Roundista 128x R32.zip
   (Soft & Rounded).
3. Preserve other desired packs and the base game underneath.

Both alternatives are downloaded by Packwiz; only one LabPBR base is enabled.
Existing users select their packs normally. No managed `options.txt` overwrites
their preferences. For a closed owned local test client, the source checkout also
provides a verified selector:

```powershell
python -m tools.graphics_preset --home "D:\A World for Two" --client AWFT_Check_YYYYMMDD_HHMMSS --bsl-materials enchanted-fantasy
python -m tools.graphics_preset --home "D:\A World for Two" --client AWFT_Check_YYYYMMDD_HHMMSS soft-rounded
```

Use the actual owned client's home and ID. The selector verifies both archives,
backs up the original options, removes the other base from the selection, and
preserves unrelated packs/settings. It retains existing shader and DH choices.
Without `--bsl-materials`, existing shader settings are preserved. That explicit
flag selects pinned BSL and saves restrained LabPBR settings, backing up both
the Iris choice and BSL material options while retaining unrelated values. The
same material profile serves both bases; a material difference requiring two
separate shader profiles has not been demonstrated. The selector does not modify
an open client, download assets, or certify rendered results.
To restore preferences, close Minecraft and copy the exact `previous` file in
`awft-texture-preset.json` back to `.minecraft/options.txt`.

In BSL's shader options, start with Medium, enable Advanced Materials and select
LabPBR (`MATERIAL_FORMAT=1`). Start parallax at depth 0.10, quality 32 and distance
32; reduce/disable it on thin model geometry if gaps or shimmer appear. Keep
normal/specular effects restrained, soft shadows and AO; measure before raising
quality. Preserve the established DH settings and caches. These are test starting
values, not measured optimized profiles. A separate shader profile is not claimed
until native rendering establishes a meaningful difference between the bases.

Archive inspection found one overlapping block model with Stylista (hay) and
seven with Roundista (crafting table, flower pots and candle templates). Nautilus
wins those model conflicts at the initial priority. Inspect their UVs and PBR
surfaces in-game; do not assume ZIP compatibility proves visual compatibility.

Diorama preserves Xaero and Control Room Atlas. Fresh owned clients bind its map
to F8, waypoint creation to F9 and waypoint list to F10. Existing clients can set
these in Controls > Diorama without changing other bindings. Use Diorama's Xaero
waypoint import when desired; this is not continuous bidirectional synchronization.
Hide one minimap overlay if the two compete for screen space.

## World and deployment

Ancient Remnants' source-confirmed config is
`config/obscuria/ancient_remnants-common.toml`. Each structure family uses spacing
128 and separation 32 chunks, compared with author defaults 100/20. Author biome
eligibility, loot, research, blessings and progression remain intact. This lowers
potential placement density to roughly 61% of the default per family before biome
filtering. It affects future generation; no existing regions are reset or edited
to force structures into Tortuga or Rosewater Castle.

The owner confirmed the candidate.65 Tortuga runtime at
`D:\A World for Two\staging\world-tests\20261027T053650Z-artistic` is production.
The older root candidate.31 is not the deployment target. No Ubuntu migration is
assumed. A verified offline backup and independent restore are retained under
`D:\A World for Two\staging\enchanted-expansion-20261106`; raw worlds, configs,
inventories and logs stay private. Restored bytes were verified against all 5,517
archived source files. The archive includes world/dimensions/player data and server
deployment/configuration; logs and crash reports remain in their original custody.

The updated restored server uses localhost:25585, a distinct world directory and
178 server mod JARs after production reconciliation. Client-only files are excluded. Preserve the private backup
receipt and archive checksum. Rollback uses that exact pre-update archive and
deployment inventory in an independent restore first; stop/save the target before
restoring it and never merge modded player data from an incompatible downgrade.

Production activation requires successful staging qualification and a coordinated
maintenance window. Use the existing Control Room installation/backup and exact
release publication workflow in [RELEASING.md](RELEASING.md). Public clients and
server must receive the same qualified immutable manifest. Do not redirect the
stable channel to a mutable branch or mark an untested ZIP as latest.

## Verification boundary

Automated dependency checks and actual native runtime results are recorded
separately in the expansion evidence. Test server startup/save/shutdown, decorative
block restart persistence, structure generation, carts and Octo Arms before
activation. Native client rendering, BSL/PBR and DH, texture switching, Create
machinery/ships, dense-city frame times and the matching multiplayer join remain
separate checks. KG is available; Sera is unavailable for the requested two-player
acceptance. No two-player, benchmark or complete visual acceptance is inferred
from a title screen, static manifests, model registration or successful startup.

### Current release gates

The reconciled 178-JAR server copy passed startup, save and clean shutdown. The
stopped preservation audit retained all 7,446 original overworld entity UUIDs,
left all three player-data files byte-identical, and found identical section
block states in all 42,557 original overworld chunks. This does not establish
NPC schedules, machine operation, other-dimension geometry or multiplayer play.

The final headless installation/update verified all 218 required client files.
It also enabled the existing optional Essential file despite its declared
`default=false`; the native GUI optional-choice workflow remains unqualified.
No obsolete bridge or Diorama JAR remained. Essential remains excluded from the
normal managed server and owned test-client defaults.

A 6 GiB Enchanted Fantasy/BSL run created its world render pipeline but reached
heap pressure and severe frame stalls. A fresh instance confirmed an actual
8 GiB heap, then stopped at accessibility onboarding; desktop testing was stopped
with Escape before world/render qualification. Neither result is a controlled
benchmark. Soft & Rounded with BSL/DH and dense-city/interior visual acceptance
remain open. The source build is 0.2.0, but no stable/latest publication or
production activation is claimed.
