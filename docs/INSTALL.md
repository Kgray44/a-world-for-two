# Install A World for Two

The public download is the immutable **candidate.31 prerelease**. Its ZIP and
checksum were verified; a clean native Prism import remains unqualified.
**Private candidate.46 has reached native startup and restarted for a preview**,
with further client, multiplayer and feature validation still pending. The public
candidate.31 ZIP does not contain that private work. See [current status](STATUS.md)
and [the candidate.46 recovery record](NATIVE-CANDIDATE46.md).

## Client

1. Install [Prism Launcher](https://prismlauncher.org/) and sign into your licensed Minecraft Java account.
2. Download [A-World-for-Two-0.1.0-candidate.31-Prism.zip](https://github.com/Kgray44/a-world-for-two/releases/download/awft-0.1.0-candidate.31/A-World-for-Two-0.1.0-candidate.31-Prism.zip)
   from the [candidate.31 release](https://github.com/Kgray44/a-world-for-two/releases/tag/awft-0.1.0-candidate.31).
3. Choose **Add Instance → Import from ZIP** and select the file. Import as a new
   instance so an older installation cannot supply stale mods or configuration.
4. Select **Java 21**. Set maximum memory to **6 GiB for KG** or the conservative
   **4 GiB for Sera**. Sera's complete measured graphics profile remains open.
5. Launch with the Packwiz pre-launch step enabled. It retrieves exact client
   files from pinned author sources. Start with shaders off, then choose one in
   **Video Settings → Shader Packs** after baseline startup.
6. Join only when the host confirms that the matching server and tunnel are
   available and your licensed Java username is whitelisted. The public starter's
   configured address is **`malls-cup.tun.ply.gg`**; this is not a live availability
   check. Its KG-local entry is for a client on the host computer.

Private previews require the separately supplied matching instance and preview
entry. Candidate.31 and candidate.46 are different packs; do not use the public
starter as proof of compatibility with the private preview. A current authenticated
candidate.46 client join has not yet been recorded.

Accounts, worlds, backups and host-specific Java paths stay out of the ZIP. The
starter includes one unchanged Let's Forge Pirates JAR under the
[author's modpack grant](PIRATE-MODPACK-PERMISSION.md); other mods come from their
pinned sources. Leave optional Essential off for the normal dedicated-server setup.

## Updates and troubleshooting

The pre-launch command invokes **packwiz-installer-bootstrap** and supplies the
pinned full installer with `--bootstrap-main-jar`. Running the full installer
directly causes the “must be run through packwiz-installer-bootstrap” error.
Keep the supplied Paxi cinematic data intact and relaunch the matching gameplay
pack after server content changes. Local shader choices can differ.

Verify the [published checksum](https://github.com/Kgray44/a-world-for-two/releases/tag/awft-0.1.0-candidate.31)
for the public starter. Fresh download, Packwiz installation and native Prism
import are separate checks. Two historical headless candidate.31 installations
left six downloads missing after DNS errors; the unchanged
[release record](../evidence/runtime/artistic-release-candidate.31.json) preserves
those failures. They do not establish the cause of a new installation problem.

If a server reports incompatible mods, first verify that its candidate matches
the imported instance. Public tunneling also requires the intended game server
and Playit service to be running. Candidate.31's older Create registration failure
and rejected unchanged recovery attempt remain in the
[startup history](CREATE-STARTUP-RECOVERY.md); candidate.46 has its own successful
private startup record.

Strict SeedGen client/server parity remains unresolved. DH server LOD downloads
remain the fallback; no relaxed fingerprint setting is selected. See the
[recorded gap](SEEDGEN-RUNTIME-GAP.md).

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
