# Install A World for Two

1. Install [Prism Launcher](https://prismlauncher.org/) and sign in with your Minecraft Java account.
2. Download the auto-updating Prism ZIP from the [Latest release](https://github.com/Kgray44/a-world-for-two/releases/latest).
3. Choose **Add Instance → Import** in Prism and select the ZIP. Use **Java 21**.
4. Press **Play**. Packwiz downloads the files for the approved production pack.
5. Choose **Join Our World → Public**. The host needs to whitelist your exact Java username before you connect.

Keep this Prism instance. Every launch checks the
[stable Packwiz channel](https://kgray44.github.io/a-world-for-two/pack.toml)
and applies approved modpack updates automatically. Ordinary mod changes only
require a relaunch. Prism manages the Minecraft and NeoForge versions separately.

If you imported the earlier 0.2.0 r5 ZIP, edit that instance's **Settings →
Custom commands**. In the pre-launch command, replace only the URL ending in
`/releases/0.2.0/pack.toml` with
`https://kgray44.github.io/a-world-for-two/pack.toml`. Keep the rest of the
command and the same instance so your local settings stay in place.

Start with shaders off. The 12 GiB setting in the ZIP was tested on the owner's
32 GiB computer. Leave optional Essential off for the dedicated server.
The ZIP includes one unchanged Let's Forge Pirates JAR under the
[author's modpack grant](PIRATE-MODPACK-PERMISSION.md). Other mods come from their
pinned sources.

## Host

Use Java 21 and Python 3.12+:

```powershell
python -m pip install -e .
python -m control_room run --home "D:\A World for Two"
```

Open `http://127.0.0.1:8765`, complete setup, accept Minecraft's EULA for your own
server and enter the licensed Java usernames. Qualify and back up a candidate
before creating a permanent world. The normal host game port is 25565; the owned
private preview uses 25575. Public tunnels must target only the intended game port.
