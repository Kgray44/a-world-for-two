# A World for Two

**Our little corner of an endless world.**

![A quiet sunset beside the village lake](assets/menu/a-world-for-two-background.jpg)

A cozy Minecraft home for KG and Sera, with gardens, fairytale rooms and working
crafts close by, and mountains, pirate harbors and mechanical adventures beyond.

**Minecraft 1.21.1 · NeoForge 21.1.262 · Java 21 · Prism Launcher · Packwiz**

Candidate **0.1.0-candidate.23** contains **197 enabled mod JARs**, **eight shaders**
and one resource pack. The permanent server now contains the expanded castle,
south-bank village and sailing harbor. **KG and Sera rejected the settlement's
visual quality after exploring it. The town, ships, bridges and castle are now
undergoing an artistic rebuild, beginning with actual in-game visual prototypes.**
Earlier block and drawbridge checks establish technical facts, not artistic quality.
See [the recovery direction](docs/ARTISTIC-RECOVERY.md).
The official server is currently stopped for that rebuild. A separate fresh world
is being reviewed through real shader screenshots before deployment.
The Prism prerelease is public and its fresh Packwiz download check passed.
KG and Sera have both joined the official server; KG confirms Sera used the public
Prism-r2 ZIP. This is user-reported import/launch evidence, not a remote file-hash
inspection or full multiplayer feature acceptance. See [current status](docs/STATUS.md).

## Play

Download the [Prism instance ZIP](https://github.com/Kgray44/a-world-for-two/releases/download/awft-0.1.0-candidate.23/A-World-for-Two-0.1.0-candidate.23-Prism-r2.zip)
from the [current prerelease](https://github.com/Kgray44/a-world-for-two/releases/tag/awft-0.1.0-candidate.23).

1. In Prism, choose **Add Instance → Import from ZIP** and select the starter.
2. Sign into your licensed Minecraft Java account and select Java 21. The instance
   configures a **6 GiB** maximum client heap; its Packwiz pre-launch step downloads
   the exact client files from the pinned release manifest.
3. Choose **Join Our World**, then the supplied public server entry. The KG-local
   entry is for Minecraft running on the server's own computer.

Public address: **`malls-cup.tun.ply.gg`**. The ZIP starts with shaders off and
includes the one unchanged pirate mod covered by its author's modpack grant;
the pinned updater downloads the remaining files. Leave optional Essential off
for the normal dedicated-server setup.

The host runs the server and linked Playit game tunnel and adds players to the
whitelist. Accounts, worlds, backups and LOD databases are not bundled in the
client ZIP. [Installation](docs/INSTALL.md) and [current release status](docs/STATUS.md#distribution-and-remaining-acceptance)
explain updates and the remaining distribution checks.

## The world we are building

These are the pack's intended experiences. The showcase architecture is being
rebuilt and remains subject to the visual review described above.

| Around home | Beyond the doorstep |
| --- | --- |
| Cottage, kitchens, gardens, pets and music | Mountains, ocean exploration, ruins and archaeology |
| Rosewater Castle, inhabited rooms and gardens | Age-of-sail ships and furnished belowdecks |
| Dense south-bank businesses and homes | Lanternwater pirate quarter, quays, smaller craft and fishing |
| Create workshops and mechanical attractions | Trains, Small Ships, Aeronautics/Sable and Hypertubes |
| Weather, custom presentation and workstation scenes | Xaero's maps, parties/claims, Waystones and browser World Atlas |

The large harbor ships are detailed structural builds. Rideable craft and native
boat tenders complement them. The drawbridge uses real water-wheel power and
opposed 55° programs; the isolated tender hoist still needs commissioning.
The railway, Hypertube and pneumatic logistics settlement demonstrations have
reviewed source/staging plans and still require native installation and commissioning.
Seven actual-settlement cinematics are registered by the
running server; their client rendering and full settlement coverage still need review.

Distant Horizons + SeedGen is the selected distant-terrain architecture. Voxy and
Roxy remain excluded. Kappa, Bliss and six other shader choices are pinned;
Chocapic remains deferred. Every requested candidate, alternative and unresolved
integration is retained in the [compatibility inventory](docs/COMPATIBILITY.md).
[The lock](catalog/lock.json) records exact versions, file hashes and client/server sides.

## Control Room

The host's local dashboard manages server controls, whitelist, operator levels,
player coordinates, Atlas waypoints, live storage, backups, mod proposals, menu
artwork, graphics choices and the installed Playit.gg tunnel service.

```powershell
python -m pip install -e .
python -m control_room run --home "D:\A World for Two"
```

Open **http://127.0.0.1:8765**. Worlds, downloads, credentials and backups stay outside
this source repository. Changes require the local origin and current session token;
public game tunnels carry the Minecraft port. See [the Control Room guide](docs/CONTROL-ROOM.md).

## Guides

- [Installation and updates](docs/INSTALL.md)
- [Measurements, known issues and remaining acceptance](docs/STATUS.md)
- [Shaders and compatibility limits](docs/SHADERS.md)
- [Castle](docs/ROSEWATER-CASTLE-DESIGN.md), [south-bank village](docs/SOUTH-BANK-DESIGN.md),
  [harbor](docs/GRAND-HARBOR-SHIPS-DESIGN.md) and [cinematics](docs/SETTLEMENT-CINEMATIC.md)
- [Staged watermill and transport](docs/SETTLEMENT-ATTRACTIONS.md) and [maritime attractions](docs/MARITIME-ATTRACTIONS.md)
- [Per-mod showcase evidence and remaining demonstrations](docs/SHOWCASE-COVERAGE.md)
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
constrain unrelated applications. Disposable cleanup follows acceptance and keeps
useful recovery material.
