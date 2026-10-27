# A World for Two — candidate.23

Development candidate. The portable starter is prepared for release checks;
fresh Prism import, public downloads and complete multiplayer acceptance are
still pending. This is not a qualified stable release.

## Install and join

Import the `A-World-for-Two-0.1.0-candidate.23-Prism.zip` in **Prism → Add Instance →
Import from ZIP**, sign into your own licensed Minecraft Java account, select
Java 21 and launch. The instance uses Minecraft 1.21.1, NeoForge 21.1.262 and a
maximum client heap of **6 GiB**. Shaders initially stay off for baseline startup;
choose a shader after the game loads.

**Join Our World** opens Minecraft's normal multiplayer server list. The starter
provides two editable entries:

- **Public:** `malls-cup.tun.ply.gg` for players joining from another computer.
- **KG local computer only:** `127.0.0.1:25565` when Minecraft runs on the same
  computer as the dedicated server.

The host must have the server and its linked Playit game tunnel running. The
server requires a licensed Java account and the host's whitelist. Update the saved
address normally if the host gives you a new one. The client ZIP contains no
player accounts, authentication tokens, permanent world, backups or LOD databases.

## Included

- **197 enabled top-level mod JARs**, with 190 applicable to the client and 164 to
  the dedicated server; **8 shader packs** and one resource pack. These counts do
  not count embedded libraries as separate downloadable JARs.
- Cozy homes, furniture, farming and cooking; pets and wildlife; pirate and ocean
  adventures; Create transport; Xaero's navigation; workstation scenes and custom
  presentation. Exact selections and unresolved candidates remain in the
  [compatibility inventory](COMPATIBILITY.md).
- Distant Horizons + SeedGen remains the selected distant-terrain architecture.
  Voxy and Roxy remain excluded. Kappa and Bliss are included; the original
  Chocapic download remains pending rather than being silently substituted.
- The supplied menu artwork is preserved byte for byte. This starter uses the
  existing presentation assets and a normal native multiplayer action, so a
  remote player is not sent to their own localhost by the main join button.

The named settlement belongs to the hosted permanent server. It is not bundled
into the portable client. Server construction, artwork review and gameplay
acceptance have their own evidence and do not follow from a ZIP integrity check.

The compatibility source/notice accompaniment is
`A-World-for-Two-compat-candidate.23-Notices-and-Sources.zip` (4,880,566 bytes,
SHA-256 `fbf93050ee94ee4391b9496f93cb701cf085e59eeeda5407b88120be19f49fa6`).
It supplies pinned source archives, official exact-version source JARs, full
component licenses and source/relink instructions alongside the unchanged
compatibility JARs. Its [provenance record](../catalog/compat-release-provenance-candidate.23.json)
states the remaining source-build and runtime limits. Local preparation does
not assert publication or legal compliance certification.

## Candidate.23 changes

The server bridge is pinned to **0.6.9**. It adds explicit ownership and power
readiness guards to bounded native commissioning and recovery. Its source and
resources match the immutable build receipt, and the JAR includes the scoped
project MIT notice. Dedicated-server runtime, drawbridge cycles and world
construction retain their separately recorded native checks.

The source Tectonic configuration now uses LF line endings so that Git's stored
bytes match Packwiz's hashes. Its terrain settings already match the live server
configuration exactly; this does not retune world generation. The bridge metadata
and build recipe also use LF, and scoped Git attributes make future checkouts
consistent. All **283 indexed Packwiz members**, the two manifests and 24 bridge
source/resource/recipe files matched Git's cleaned bytes: **309 files, zero
differences**.

The publication proposal names only this source-frozen candidate and keeps the
stable root channel disabled. Earlier local exports remain preserved. A source
validation or ZIP check does not activate an update or qualify a stable release.

## Pinned updater

The prepared ZIP is **6,308,426 bytes**. Its SHA-256 is
`412c62ae0288fe0a9fde98f39b112baaf1960e8c7521d64bc152827ebbb73c8d`.
It binds to source Packwiz SHA-256
`9631a680f572fe7cae44cb2575f7c3ced3910611819ab948c02406e6e0700e11`.
The release's checksum sidecar must match the downloaded ZIP. Preliminary exports
are retained separately and are not the candidate.23 artifact identified here.

The portable pre-launch step runs **packwiz-installer-bootstrap v0.0.3** with the
pinned **packwiz-installer v0.5.14** supplied through `--bootstrap-main-jar`. It uses
`--bootstrap-no-update` and `-s client`, preserving the tested updater chain and
correct side selection. It does not run the full installer directly.

The versioned update manifest is
[candidate.23 Packwiz](https://kgray44.github.io/a-world-for-two/releases/0.1.0-candidate.23/pack.toml).
Each launch checks that immutable candidate tree; a later candidate uses its own
versioned manifest. The starter ZIP contains the two licensed updater JARs and
source-controlled configuration. Mods, shaders and resource packs are obtained
from their pinned author sources during pre-launch.

## Verified and pending

Local export checks cover ZIP CRC, the portable Prism layout, 6 GiB memory,
NeoForge component, pre-launch quoting/argument structure, exact updater bytes,
original artwork identity and an explicit archive allowlist that excludes runtime
accounts, worlds, logs, LODs and QA helpers. Minecraft 1.21.1's actual NBT and
`ServerData` readers accepted the two generated server entries with resource-pack
consent left at its normal prompt. That headless schema check is not a native
Prism import or a game launch.
An independent audit also matched all **76 packaged configuration files** to the
exact Packwiz index hash chain and verified the two updater binaries. The archive has **87 entries** and excludes the host setup paths from its portable
client instructions.

Before a public one-download/import claim, the exact immutable Pages tree and
owned compatibility artifacts must be published and checked, all author downloads
must succeed through authorized distribution, and a clean native Prism import
must complete pre-launch and reach the game. Public download availability for this candidate has not been qualified during
export preparation; author-download restrictions remain a release gate.

Remote two-player synchronization, full feature acceptance, final shader/world
presentation, the isolated ship-hoist commissioning and any remaining server
construction checks remain separate. The dedicated-server SeedGen fingerprint
repair does not by itself prove client/server fingerprint agreement, distant
terrain fidelity or SeedGen terrain appearing on Xaero's maps. See
[current status](STATUS.md) and [the release process](RELEASING.md) for the complete
qualification boundary.
