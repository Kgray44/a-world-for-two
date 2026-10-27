# Install A World for Two

**Final server status:** the fresh world is saved, but the server is currently offline. A subsequent startup failed in Create 6.0.10 while accessing unbound `create:chocolate_bucket`. The earlier online measurements are historical. Recovery start was rejected by automatic approval review with only the reason "blocked by policy"; it was not retried through another route.

**Fresh-install blocker:** two independent public installer attempts failed DNS lookups, including official redirect hosts. Each verified 195/201 CLI artifacts and all 80 configuration files, but six required downloads remain missing. A clean one-import installation is not yet qualified.

Candidate.31 is published; the official fresh world is installed but the server is offline.

## Client

1. Install [Prism Launcher](https://prismlauncher.org/) and sign into your licensed Minecraft Java account.
2. Download [A-World-for-Two-0.1.0-candidate.31-Prism.zip](https://github.com/Kgray44/a-world-for-two/releases/download/awft-0.1.0-candidate.31/A-World-for-Two-0.1.0-candidate.31-Prism.zip)
   from the [candidate.31 release](https://github.com/Kgray44/a-world-for-two/releases/tag/awft-0.1.0-candidate.31).
3. Choose **Add Instance → Import from ZIP** and select the file. Import as a new
   instance so an older installation cannot supply stale mods or configuration.
4. Select **Java 21**. Set maximum memory to **6 GiB for KG** or the conservative
   **4 GiB for Sera**. Sera's hardware has no complete measured graphics profile.
5. Launch. The Packwiz pre-launch step downloads exact client files from pinned
   author sources. Keep it enabled for future published updates.
6. Choose a shader in **Video Settings → Shader Packs** after baseline startup.
   A fresh portable export starts with shaders off; existing owner clients keep their choice.
7. Choose **Join Our World → Public**. The current address is **`malls-cup.tun.ply.gg`**.
   Authentication and the whitelist stay enabled; the host must keep the server and
   Playit running. The KG-local entry is only for Minecraft on the host's own computer.

No account credentials, worlds or host-specific Java path belongs in the ZIP.
The starter includes exactly one unchanged Let's Forge Pirates JAR under the
[author's modpack grant](PIRATE-MODPACK-PERMISSION.md), avoiding its manual API
download requirement. Other mods come from their pinned sources. Leave the
optional Essential fallback off unless it is deliberately needed.

The Packwiz update includes the same cinematic datapack for both clients and the
server, loaded through Paxi. Keep this supplied data intact. Candidate.31 also
corrects Tectonic's terrain-pack ordering, but its actual native client/server
comparison still failed. Strict SeedGen client generation stays off, with DH
server-download fallback; no relaxed fingerprint setting is selected. See
[the runtime gap and repair scope](SEEDGEN-RUNTIME-GAP.md).

## Updates and troubleshooting

The pre-launch command invokes **packwiz-installer-bootstrap** and supplies the
pinned full installer with `--bootstrap-main-jar`. Running the full installer directly
causes the "must be run through packwiz-installer-bootstrap" error.

Both players relaunch the matching gameplay pack after server content changes.
Local shader differences do not change server gameplay content. Fresh public
download, Packwiz installation and native Prism import are separate checks for
each released starter. Candidate.31's public ZIP/checksum passed, but two fresh
headless installations failed DNS and native fresh Prism import remains unqualified. Use the
[published checksum](https://github.com/Kgray44/a-world-for-two/releases/tag/awft-0.1.0-candidate.31)
to verify your download.

If the server reports incompatible mods, check that both the imported instance
and server use candidate.31. The public tunnel can connect only while the host is
running the intended server. The authorized fresh-world handoff is complete;
the server is offline as described at the top of this guide.

## Host

Use Java 21 and Python 3.12+:

```powershell
python -m pip install -e .
python -m control_room run --home "D:\A World for Two"
```

Open `http://127.0.0.1:8765`, complete setup, explicitly accept the Minecraft EULA
for your own server and enter the licensed Java usernames. Qualify and back up a
candidate before creating the permanent world.

The owner's disposable test uses dashboard 8766 / Minecraft 25575. The normal host
uses Minecraft 25565. Public tunnels must target only the intended game port.
