# A World for Two

**Final server status:** the fresh world is saved, but the server is currently offline. A subsequent startup failed in Create 6.0.10 while accessing unbound `create:chocolate_bucket`. The earlier online measurements are historical. Recovery start was rejected by automatic approval review with only the reason "blocked by policy"; it was not retried through another route.

**Fresh-install blocker:** two independent public installer attempts failed DNS lookups, including official redirect hosts. Each verified 195/201 CLI artifacts and all 80 configuration files, but six required downloads remain missing. A clean one-import installation is not yet qualified.

Private candidate **38** starts and joins normally. The mill's six real tube
connections, furnished mill, castle audience room and fixed drawbridge architecture
have native results and actual game captures. The moving bridge redesign, mill
commissioning, strict SeedGen parity and inhabited pirate spit remain in progress.
See the [latest native results](docs/NATIVE-CANDIDATE38.md).

**Our little corner of an endless world.**

![A quiet sunset beside the village lake](assets/menu/a-world-for-two-background.jpg)

A cozy Minecraft home for KG and Sera: cottage gardens and kitchens, a winding
pirate waterfront, Rosewater Castle, sailing adventures and Create machinery.

**Minecraft 1.21.1 · NeoForge 21.1.262 · Java 21 · Prism Launcher · Packwiz**

Published prerelease **0.1.0-candidate.31** retains **197 enabled mods**: **191 on the client** and
**164 on the server**, with shared mods counted on each side. Eight shader choices
and one resource pack are included. Essential is optional and disabled; enabling
it brings the total mod selection to 198.

**Current checkpoint:** candidate.31 is published and the authorized fresh-world
handoff is complete; the server is offline as described above. The rebuilt settlement has actual in-game screenshot
reviews; owner artistic acceptance remains pending. See [current status](docs/STATUS.md).

## Install and join

1. Download the [candidate.31 Prism ZIP](https://github.com/Kgray44/a-world-for-two/releases/download/awft-0.1.0-candidate.31/A-World-for-Two-0.1.0-candidate.31-Prism.zip)
   from the published candidate.31 release.
2. In [Prism Launcher](https://prismlauncher.org/), choose **Add Instance → Import
   from ZIP**. Sign into your licensed Minecraft Java account and use **Java 21**.
3. Set maximum memory to **6 GiB for KG** or the conservative **4 GiB for Sera**.
   Launch with the included Packwiz pre-launch step enabled; it installs the pinned
   client files. Start with shaders off, then choose a preset after joining.
4. Choose **Join Our World**, then the **public server** entry. The KG-local entry
   is for a client running on the server's own computer.

Public address: **`malls-cup.tun.ply.gg`**. The host must keep the server and Playit
running and add each licensed Java username to the whitelist. Leave optional
Essential off for the normal dedicated-server setup.

The starter includes one unchanged pirate mod under its author's
[modpack permission](docs/PIRATE-MODPACK-PERMISSION.md); the updater retrieves the
remaining files from pinned sources. Accounts, worlds, backups and LOD databases
stay out of the client ZIP. See [installation and troubleshooting](docs/INSTALL.md).

## From the actual game

![Bramble Lane's lanterns, shopfronts and planted windows](docs/images/artistic-recovery/bramble-lane.png)

![Books, seating and the Rose & Lantern cottage hearth](docs/images/artistic-recovery/rose-lantern-hearth.png)

Unchanged Minecraft captures from the artistic staging world, using Complementary
Reimagined. These show the current work; owner visual acceptance remains pending.
[Capture provenance](evidence/runtime/artistic-recovery-detail-20261027.json).

## Explore together

| At home | Out exploring |
| --- | --- |
| Furnished cottages, gardens, pets, kitchens and music | Mountains, oceans, ruins and archaeology |
| Rosewater Castle and intimate craft lanes | Pirate waterfronts, sailing ships and belowdecks |
| Stocked shops, courts and warm evening lighting | Fishing, treasure, weather and ocean wildlife |
| Custom menu and animated workstation interactions | Xaero's maps, parties/claims, Waystones and browser Atlas |
| Create workshops and a powered river drawbridge | Trains, Small Ships, Aeronautics/Sable and Hypertubes |

The new town was built and reviewed in a fresh staging world and installed as
the official save, with authored
streets, dry-bank homes, layered interiors, harbor approaches and original river
crossings. [Artistic recovery](docs/ARTISTIC-RECOVERY.md) records the visual work.

The rebuilt bascule completed native powered opening/closing cycles after a
restart. Other Create attractions still require installation or commissioning;
the full addendum scope and artistic acceptance are **not complete**.

**Distant Horizons + SeedGen** remains the distant-terrain architecture. Voxy and
Roxy are excluded. Kappa, Bliss and six other shaders are pinned; Chocapic remains
deferred. The [compatibility inventory](docs/COMPATIBILITY.md) retains every
requested candidate and unresolved integration; [the lock](catalog/lock.json)
records exact versions, file hashes and client/server sides.

Candidate.31 delivers the same cinematic datapack through Packwiz/Paxi and corrects
the client-side ordering of Tectonic's built-in terrain pack. Actual native testing
still failed strict fingerprint agreement: SeedGen client generation stays off,
with DH server-download fallback. [The remaining gap is documented](docs/SEEDGEN-RUNTIME-GAP.md).

## Control Room

The local dashboard manages server controls, whitelist, operator levels, player
coordinates, Atlas waypoints, live storage, backups, mod proposals, menu artwork,
graphics choices and the installed Playit.gg tunnel service.

```powershell
python -m pip install -e .
python -m control_room run --home "D:\A World for Two"
```

Open **http://127.0.0.1:8765**. Changes require the local origin and current session
token. Worlds, downloads, credentials and backups stay outside this repository;
public game tunnels carry the Minecraft port. See [the dashboard guide](docs/CONTROL-ROOM.md).

## Guides

- [Installation](docs/INSTALL.md), [current status](docs/STATUS.md) and [shader choices](docs/SHADERS.md)
- [Artistic recovery](docs/ARTISTIC-RECOVERY.md) and [landmark prototypes](docs/ARTISTIC-LANDMARK-PROTOTYPES.md)
- [Waterfront street](docs/ARTISTIC-STREET-PROTOTYPE.md), [cottage court](docs/ARTISTIC-COTTAGE-COURT.md),
  [craft lane](docs/ARTISTIC-CRAFT-LANE.md) and [connecting grounds](docs/ARTISTIC-CONNECTING-GROUNDS.md)
- [Harbor craft](docs/ARTISTIC-HARBOR-CRAFT.md) and [cinematics](docs/SETTLEMENT-CINEMATIC.md)
- [Create attractions](docs/SETTLEMENT-ATTRACTIONS.md), [maritime attractions](docs/MARITIME-ATTRACTIONS.md)
  and [showcase coverage](docs/SHOWCASE-COVERAGE.md)
- [Release process](docs/RELEASING.md) and [third-party notices](docs/THIRD-PARTY.md)

## Develop and verify

```powershell
python -m unittest discover -s tests -v
python -m tools.pack validate
node --check control_room/static/app.js
node --test tests/session.test.mjs
```

This repository contains source, configuration, original presentation artwork and
sanitized evidence. Runtime saves, credentials, downloaded third-party JARs, logs
and caches remain private. The predecessor repository is inspected read-only.
Local work reserves **30 GiB free separately on C: and D:**; monitoring does not
constrain unrelated applications. Cleanup follows acceptance and preserves useful
recovery snapshots and failed receipts.
