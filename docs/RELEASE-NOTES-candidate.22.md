# A World for Two — candidate.22

Development candidate. The portable starter is prepared for release checks;
fresh Prism import, public downloads and complete multiplayer acceptance are
still pending. This is not a qualified stable release.

## Install and join

Import the `A-World-for-Two-0.1.0-candidate.22-Prism.zip` in **Prism → Add Instance →
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
`A-World-for-Two-compat-candidate.22-Notices-and-Sources.zip` (4,878,500 bytes,
SHA-256 `64974abab2229e61fed1dab59239c3e754db1af60a0aedfe8ad0380470ed500c`).
It supplies pinned source archives, official exact-version source JARs, full
component licenses and source/relink instructions alongside the unchanged
compatibility JARs. Its [provenance record](../catalog/compat-release-provenance-candidate.22.json)
states the remaining source-build and runtime limits. Local preparation does
not assert publication or legal compliance certification.

## Candidate.22 changes

The server bridge is pinned to **0.6.8**, including a project MIT notice and
corrections to bounded native commissioning, empty-world wake-up and recovery
receipts. Its server runtime and drawbridge commissioning checks have separate
results; the portable client archive does not qualify those world changes.

The unpublished candidate.21 Pages proposal was superseded before any tag or
deployment. Local candidate.21 exports remain preserved as historical checks.
The approved publication proposal now names only candidate.22 and keeps the
stable root update channel disabled.

## Pinned updater

The prepared ZIP is **6,308,435 bytes**. Its SHA-256 is
`0170e711b3380bcb711c2efb3dd591134e80965631d3e5f206d86b9a2724f021`.
It binds to source Packwiz SHA-256
`f03607be53e708c01ee01c3f214bf3cf850a9eb84d0400f57f4b76afb9bab449`.
The release's checksum sidecar must match the downloaded ZIP. Preliminary exports
are retained separately and are not the candidate.22 artifact identified here.

The portable pre-launch step runs **packwiz-installer-bootstrap v0.0.3** with the
pinned **packwiz-installer v0.5.14** supplied through `--bootstrap-main-jar`. It uses
`--bootstrap-no-update` and `-s client`, preserving the tested updater chain and
correct side selection. It does not run the full installer directly.

The versioned update manifest is
[candidate.22 Packwiz](https://kgray44.github.io/a-world-for-two/releases/0.1.0-candidate.22/pack.toml).
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
must complete pre-launch and reach the game. Public URLs checked during export
preparation were not yet downloadable. Restricted author downloads remain a
release gate.

Remote two-player synchronization, full feature acceptance, final shader/world
presentation, the isolated ship-hoist commissioning and any remaining server
construction checks remain separate. The dedicated-server SeedGen fingerprint
repair does not by itself prove client/server fingerprint agreement, distant
terrain fidelity or SeedGen terrain appearing on Xaero's maps. See
[current status](STATUS.md) and [the release process](RELEASING.md) for the complete
qualification boundary.
