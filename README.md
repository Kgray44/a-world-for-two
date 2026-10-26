# A World for Two

**Our little corner of an endless world.**

![A quiet sunset beside the village lake](assets/menu/a-world-for-two-background.jpg)

A cozy Minecraft world for KG and Sera: cottages and gardens at home, beautiful
mountains and oceans beyond, and Create machines, trains, ships and airships to connect it all.

**Minecraft 1.21.1 · NeoForge 21.1.262 · Java 21 · Prism Launcher · Packwiz**

> The full build is being qualified. Candidate.12 has **197 enabled mod JARs**,
> **8 shader packs** and one resource pack. A local multiplayer playtest is verified;
> the complete feature matrix, remote two-player test and public Prism import are
> still in progress. A candidate is not a finished release.

## Play

Download the qualified Prism ZIP from [Releases](https://github.com/Kgray44/a-world-for-two/releases),
then use **Prism → Add Instance → Import from ZIP**. Sign into your licensed
Minecraft account, select Java 21, and launch. The configured Packwiz pre-launch
step downloads exact client files and checks for published updates.

The import ZIP and public update channel are undergoing release checks.
See [installation](docs/INSTALL.md) for details and current limitations.

## Make a home. Go on an adventure.

| Experience | Selected systems |
|---|---|
| Cozy living | Farming, cooking, furniture, usable workstations, pets and wildlife |
| Beautiful exploration | Tectonic, Terralith, Regions Unexplored, oceans, ruins and archaeology |
| Mechanical travel | Create, trains, Small Ships, Aeronautics/Sable and Hypertubes |
| Adventure at sea | Pirates, treasure, fishing, ocean monuments and naval equipment |
| Navigation | Xaero's maps, parties and claims, Waystones and browser World Atlas |
| Atmosphere | Custom menu, workstation scenes, first-join intro, weather and shaders |
| Distant landscapes | Distant Horizons + SeedGen; no Voxy or Roxy |

Every requested candidate, exclusion and unresolved integration remains in the
[compatibility inventory](docs/COMPATIBILITY.md). Exact versions, sides, hashes and
dependency constraints live in [the release lock](catalog/lock.json).

## Control Room

The local dashboard manages the server, whitelist, operator levels, player positions,
maps and waypoints, live storage, backups, mod proposals, menu artwork, graphics
choices and the installed Playit.gg tunnel service.

```powershell
python -m pip install .
python -m control_room run --home "D:\A World for Two"
```

Open **http://127.0.0.1:8765**. Worlds, downloads, credentials and backups stay outside
this source repository. The dashboard binds to loopback and checks the local origin
and session token for changes. Public tunnels carry only the Minecraft game port.

## Guides

- [Installation and updates](docs/INSTALL.md)
- [Control Room and Playit](docs/CONTROL-ROOM.md)
- [Shader choices and limitations](docs/SHADERS.md)
- [Measurements, known issues and remaining acceptance](docs/STATUS.md)
- [Release process](docs/RELEASING.md)
- [Compatibility decisions and exact files](docs/COMPATIBILITY.md)

## Develop and verify

```powershell
python -m unittest discover -s tests -v
python -m tools.pack validate
node --check control_room/static/app.js
node --test tests/session.test.mjs
```

Local work preserves **30 GiB free separately on C: and D:**. The monitor covers
managed writers, not unrelated applications. Disposable cleanup follows acceptance.
Third-party projects retain their licenses and pinned author downloads. This source
contains configuration, project code, original presentation assets, compatibility
repair sources and documented evidence. The predecessor repository was inspected
read-only; it is not modified by this build.
