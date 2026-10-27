# Install A World for Two

The current [Prism prerelease](https://github.com/Kgray44/a-world-for-two/releases/tag/awft-0.1.0-candidate.23)
is public. Exact public download hashes and a fresh headless Packwiz installation
passed. Native Prism import and remote multiplayer acceptance remain separate.

## Client

1. Install [Prism Launcher](https://prismlauncher.org/) and sign into your licensed Minecraft Java account.
2. Download [A-World-for-Two-0.1.0-candidate.23-Prism-r2.zip](https://github.com/Kgray44/a-world-for-two/releases/download/awft-0.1.0-candidate.23/A-World-for-Two-0.1.0-candidate.23-Prism-r2.zip).
3. Choose **Add Instance → Import from ZIP** and select the file.
4. Select Java 21. The instance requests 6 GiB maximum client heap; review available
   system memory on smaller computers. Sera's hardware is still unmeasured.
5. Launch. The Packwiz pre-launch step downloads exact client files from pinned
   author sources. Keep it enabled for future published updates.
6. Choose a shader in **Video Settings → Shader Packs** after baseline startup.
   A fresh portable export starts with shaders off; existing owner clients keep their choice.
7. Choose **Join Our World → Public**. The current address is **`malls-cup.tun.ply.gg`**.
   Authentication and the whitelist stay enabled; the host must keep the server and
   Playit running. The KG-local entry is only for Minecraft on the host's own computer.

No account credentials, worlds or host-specific Java path belongs in the ZIP.
Revision2 includes exactly one unchanged Let's Forge Pirates JAR under the
[author's modpack grant](PIRATE-MODPACK-PERMISSION.md), avoiding its manual API
download requirement. Other mods come from their pinned sources. Leave the
optional Essential fallback off unless it is deliberately needed.

## Updates and troubleshooting

The pre-launch command invokes **packwiz-installer-bootstrap** and supplies the
pinned full installer with `--bootstrap-main-jar`. Running the full installer directly
causes the "must be run through packwiz-installer-bootstrap" error.

Both players relaunch the matching gameplay pack after server content changes.
Local shader differences do not change server gameplay content. The public update
installation and any restricted CurseForge downloads must pass before the release
is described as one download and import.

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
