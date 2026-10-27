# A World for Two — candidate.23, Prism revision2

The [Prism prerelease](https://github.com/Kgray44/a-world-for-two/releases/tag/awft-0.1.0-candidate.23)
is public. The exact ZIP, versioned Packwiz manifests and fresh public file
installation passed verification. Native Prism import and real remote multiplayer
remain separate acceptance checks; this is not a qualified stable release.

## Install and join

1. Download [A-World-for-Two-0.1.0-candidate.23-Prism-r2.zip](https://github.com/Kgray44/a-world-for-two/releases/download/awft-0.1.0-candidate.23/A-World-for-Two-0.1.0-candidate.23-Prism-r2.zip).
2. In Prism choose **Add Instance → Import from ZIP**.
3. Sign into your licensed Minecraft Java account, select **Java 21**, and launch.
   The instance sets a **6 GiB** maximum heap and starts with shaders off. Keep
   Packwiz pre-launch enabled; leave optional Essential off for the normal server.
4. Choose **Join Our World → Public**. Address: **`malls-cup.tun.ply.gg`**.

The host must keep Minecraft and its linked Playit game tunnel running and
whitelist the player's Java username. The KG-local server entry is for Minecraft
running on the host computer. Accounts, worlds, backups, LOD databases and QA
helpers are excluded from the portable ZIP.

## Included and changed

- Minecraft 1.21.1, NeoForge 21.1.262, Java 21; **197 enabled top-level mod JARs**,
  with 190 applicable to the client and 164 to the server. Eight shaders and one
  resource pack are pinned separately. Embedded libraries are not counted again.
- Distant Horizons + SeedGen remains the distant-terrain architecture. Voxy and
  Roxy remain excluded. Kappa and Bliss are included; original Chocapic remains
  deferred at the owner's request. See [shader choices](SHADERS.md).
- The permanent hosted world contains the expanded 40-room castle, pirate quarter,
  south-bank village and four furnished structural sailing ships. The 55-degree
  drawbridge completed two native bank-button cycles and saved its opposed
  programs. Further railway, tube, logistics and tender-hoist demonstrations
  remain under construction/commissioning. See [current status](STATUS.md).
- Bridge 0.6.9 waits for real native attachment/ticking and power readiness before
  bounded commissioning. Failed cleanup retains exact ticket ownership for an
  explicit retry. These changes do not establish unrelated feature acceptance.
- Tectonic file line endings match the existing live server bytes; terrain
  settings are unchanged. The original menu artwork remains byte-identical.

Revision2 fixes the first-install manual-download requirement for Let's Forge
Pirates by including **one unchanged required JAR** inside the modpack ZIP under
its [author's express modpack grant](PIRATE-MODPACK-PERMISSION.md), with attribution.
Other gameplay files remain pinned author downloads. No installer, resolver or
hash validation is modified. The original 6,308,426-byte starter and its failed
fresh-install receipt remain preserved privately; they are not this revision.

## Verified distribution

The ZIP is **7,072,234 bytes**, with SHA-256
`9daf9b23ab77490f1d8ac3399d4146165248d4e9d10566b434569eba87fca218`.
It has 89 allowlisted entries, including the two exact updater JARs and the single
author-permitted gameplay JAR. Its public ZIP/checksum and archive integrity passed.

A new public installation used the unchanged **bootstrap 0.0.3 → installer 0.5.14**
chain. It validated the bundled pirate file, downloaded 199 other artifacts and
verified all 200 client files plus 76 static configurations: zero missing, changed
or server-only files. The headless installer enables optional Essential, so this
check has 191 mod JARs  + 8 shaders  + 1 resource pack. Normal GUI defaults have 190
mod JARs  + 8 shaders  + 1 resource pack with Essential off; GUI selection itself was
not exercised by that headless check.

The immutable [candidate.23 manifest](https://kgray44.github.io/a-world-for-two/releases/0.1.0-candidate.23/pack.toml)
and index match their exact hashes. Pack SHA-256:
`9631a680f572fe7cae44cb2575f7c3ced3910611819ab948c02406e6e0700e11`.
The payload is bound to the unchanged source tag; five individually reviewed,
SHA-bound historical metadata files outside its index are omitted from the public
payload. No stable root update channel is published.

All 13 [compatibility release assets](https://github.com/Kgray44/a-world-for-two/releases/tag/compat-0.1.0)
passed independent public size/hash checks. The source/notices ZIP is 4,880,566 bytes,
SHA-256 `fbf93050ee94ee4391b9496f93cb701cf085e59eeeda5407b88120be19f49fa6`.
See [provenance](../catalog/compat-release-provenance-candidate.23.json) and
[actual publication evidence](../evidence/runtime/public-release-candidate.23.json).

Source CI at exporter commit 49466ff passed 131 Python tests, 4 JavaScript session
tests, syntax and Packwiz integrity. These checks do not prove graphics, a new
Prism import, launcher component downloads, remote login or full multiplayer
functionality. Dedicated-server SeedGen fingerprint success does not establish
client fingerprint agreement or Xaero map fidelity. The hosted world and its
creative/gameplay acceptance remain separate from portable ZIP distribution.
