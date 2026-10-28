# Living World compatibility and upstream integration

Checked October 28, 2026 against this lane's Minecraft **1.21.1**, NeoForge
**21.1.262**, and Java **21**. These are isolated installation proposals. The
canonical catalog, active Packwiz channel, official server and saves were not
changed. Source and artifact inspection do not establish native compatibility.

The machine guard passed before bounded downloads and generated files. This
instruction monitors this lane; it does not constrain external applications or
writers already running elsewhere.

## Exact selections

All nine requested mod relationships remain in
`proposals/living-world/mods/inventory.json`, including held and unverified ones.
That inventory records complete author URLs, artifact sizes and SHA-512 pins.

| Request | Exact candidate | Result |
| --- | --- | --- |
| Chatting Villagers | 1.1.0, CurseForge file 9064041, 316,142 bytes | Native NeoForge metadata inspected and the official download measured/pinned by SHA-512; both-side installation proposed because upstream has not verified NeoForge server-only use. |
| Smart Villagers AI | 2.0.0+neoforge-1.21.1, Modrinth bGNaqTaL, 285,498 bytes | Downloaded SHA-512 and native NeoForge metadata verified; client and server required by author distribution metadata. |
| Simple Voice Chat | neoforge-1.21.1-2.6.22, Modrinth 2s7zUspF | Optional, disabled. Latest stable matching release selected; current 2.6.27 is a beta. Pin is author metadata; voice JAR download/runtime not qualified. |
| CreaturePals | 1.3.15+1.21.1-forge, Modrinth PKx9rt8i, 9,457,441 bytes | Downloaded SHA-512 verified, **held**. It is Fabric code using Connector/Forgified Fabric API; embedded NeoForge placeholder instead demands Forge 47 and Minecraft 1.20.1. |
| Naturalist | 2.0.7+1.21.1-neoforge | Existing pin retained; AI support for its entity classes unverified. |
| Critters and Companions | Existing exact lock pin retained in inventory | No assumed CreaturePals entity support. |
| Ribbits | 4.1.6 | Existing pin retained; its special NPCs have no verified talking-animal adapter. |
| Doggy Talents Next | 1.19.1 | Existing pin retained; ownership, commands and custom dog AI require native coexistence tests. |
| Cozy's Improved Cats | 2.1.0-Neoforge-1.21.1 | Existing pin retained; no assumption that custom cats behave like vanilla cats. |

Author release sources: [Chatting Villagers 1.1.0](https://www.curseforge.com/minecraft/mc-mods/chatting-villagers/files/9064041),
[Smart Villagers 2.0.0](https://modrinth.com/mod/smart-villagers-ai/version/bGNaqTaL),
[Simple Voice Chat stable pin](https://modrinth.com/mod/simple-voice-chat/version/2s7zUspF),
[CreaturePals advertised file](https://modrinth.com/mod/creaturepals/version/PKx9rt8i).

Both native villager JARs require NeoForge at least 21.1.80, satisfied by the
existing 21.1.262 pin. This confirms declared dependency ranges only. Neither
JAR adds a mandatory gameplay library. Smart Villagers lists Voice Chat as
optional. CreaturePals lists Connector and Forgified Fabric API as required;
neither is added by this proposal.

## Ambient dialogue contract

Chatting Villagers loads arrays from
`config/chattingvillagers/dialogue/en_us/*.json`. Files beginning with
`conversations` hold two-villager exchanges; `reactions` hold click reactions;
other filenames hold solo remarks. Each row has `id`, `type`, `category`,
`conditions`, `weight`, and `text` (or conversation `lines`). The author supports
reload through `/chattingvillagers reload`.

The shipped district files contain **121 original lines** exported from the
editable Living World district catalog. A Java 21 probe deserialized every row
into the **exact downloaded 1.1.0 NeoForge JAR's** native `SoloLine` class using
the installed Gson 2.10.1 library. All 121 passed structural checks. This was
an isolated class/schema probe; no Minecraft process was started. A second
Java 21 probe passed the proposed TOML through the exact Smart Villagers 2.0.0
`readSnapshot` method using installed NightConfig 3.8.3, verifying privacy,
scripted fallback, response/concurrency limits and disabled voice/rewards.
Probe sources are retained under `proposals/living-world/mods/probes/`.

The native condition fields are `profession`, `timeOfDay`, `biome`, `weather`,
and `state`. Geographic districts are absent upstream. The Living World adapter
must inject `awft_district_<id>` state markers for configured district bounds.
The native `state` list uses **OR**, so each generated row uses exactly one
district marker; weather and time restrictions use their separate fields.
Installing only the JSON files without the adapter intentionally yields no
district matches. Never remove district conditions to make a test pass.

The quiet profile has 90-second villager cooldowns, a three-message player
budget per minute, quieter nights, bubbles enabled and ambient chat disabled.
`builtInDialogue=false` prevents re-seeding stock jokes. On an existing install,
master must preserve its prior catalog and disable or remove only confirmed
stock pools through a reviewed migration; the exporter deletes nothing.
Named AI profiles require the adapter's Chatting exclusion hook to prevent
overlapping ambient and AI bubbles. Its behavior remains a native test gate.

The public Chatting GitHub main commit
`5be7f1facb63031af7457320b27652ce10c60dae` contains older Fabric-only code.
The release-specific class signatures were inspected from the NeoForge JAR
using `javap`; the stale repository was not treated as release source parity.
[Author configuration description](https://www.curseforge.com/minecraft/mc-mods/chatting-villagers).

## Conversational AI contract

Smart Villagers source inspected at
`a619f2b577277246b353894d77140ff78f8c9c03`, with the downloaded release's
public APIs checked separately. Its existing asynchronous provider is retained.

`VillagerAiData.get(Villager)` exposes `setPersonaOverride`, `memory`, and
`setMemory`. `PersonaOverride` supports `name`, `trait`, `speechStyle`, and
`backstory` as optional strings. The adapter composes richer Studio personality
fields into these supported values and supplies relevant lore at the prompt
boundary. Names alone are never entity identity.

`AiProvider.complete(AiRequest)` returns `CompletableFuture<AiResponse>`.
`AiRequest` contains `VillagerContext` and the player's message. The context
holds persona, recent exchanges, rapport, profession, language, world facts,
relationship and request context. Native prompt text is never interpreted as
an administrative command by this lane.

Upstream config is `config/smartvillagers/config.toml` and has a public
`SmartVillagersConfig.refresh()` reload. Credentials can use the upstream
environment/secrets mechanism; the proposal contains no key and no selected
model. Native scripted fallback therefore works without external AI. The
proposal requires explicit `!` interactions and player privacy consent,
limits concurrency to two and global requests to twelve per minute, caps
replies at 180 characters, and disables voice and gameplay requests/rewards.
The addon adds profile-level privacy/knowledge limits; native settings alone
do not provide those Studio features.

Upstream has a fixed eight-exchange per-player memory limit. It does not expose
per-NPC retention, model or voice controls through this config. Studio-side
memory and supported adapter controls must remain explicit about their scope.
The `/villagerai test` path bypasses the ordinary chat consent check upstream;
the adapter's independent provider gate must cover that path too.
[Pinned Smart Villagers source](https://github.com/MeherBenSalem/CivilizationAI/tree/a619f2b577277246b353894d77140ff78f8c9c03/1.21.1).

## Optional voices and animals

Smart Villagers includes a Simple Voice Chat backend and text fallback. Its
voice settings expose global enabled state, volume and range; arbitrary
per-NPC voice, pitch and speed controls are not promised. Voice Chat also needs
a separately reachable UDP endpoint, normally 24454. The existing Minecraft
TCP tunnel is not evidence that UDP works. This lane changes no network,
firewall or tunnel setting. Voice stays disabled until owner setup and a real
hearing/failure-fallback check.
[Voice Chat setup](https://modrinth.com/mod/simple-voice-chat).

CreaturePals' advertised source link is stale; its embedded Fabric metadata
points to the accessible `elefant-ai/creature-pals` repository. Source checked
at `0d38c75dd1faec58b6c7a2748668b858a0f11ac8`. `BehaviorApplier` applies
AI-generated FOLLOW, FLEE, ATTACK, PROTECT and LEAD behaviors to entities.
No verified text-only behavior switch was found; whitelist/blacklist commands
describe bubble visibility, not a restriction on AI action. Player2 account/app
setup and external data consent also remain owner actions. CreaturePals is
kept in the inventory and omitted from executable Packwiz output. Resolving
its metadata and dependency issues alone would not resolve those behavior and
privacy boundaries. Named cat/dog/frog/sheep personas may be authored without
claiming those entities have a working native adapter.
[Current CreaturePals source](https://github.com/elefant-ai/creature-pals/tree/0d38c75dd1faec58b6c7a2748668b858a0f11ac8).

## Installation, qualification and rollback

1. Master reviews the dedicated PR, resolves narrow shared-file hooks, and
   chooses one exact candidate. `Kgray44/kg-minecraft-pack` was read only;
   its manifests and runtime are not targets.
2. Run the host reserve guard for bounded downloads/builds. Export into a
   **new** proposal directory with
   `python -m tools.living_world_upstream --output <new-owned-directory>`.
   This writes at most 2 MiB, verifies the guard and refuses existing outputs.
   It installs no mod or world.
3. Master reviews the three Packwiz metafiles, merges the two native pins and
   defaults into a private candidate, adds the built addon, and regenerates the
   canonical index/hash chain using the existing tools. Optional Voice Chat
   remains disabled. Do not copy the held CreaturePals artifact.
4. Qualify only under an exclusive master test lease and existing owner EULA
   authority. Bind named profiles to verified entity UUIDs and configure measured
   district bounds; never infer locations from lore. Verify native startup,
   two-player bubble sync, trading/jobs/movement, different simultaneous NPC
   chats, disconnection, request failure/timeout, save/apply, and restart
   persistence. Record actual CPU/RSS/MSPT and network/latency observations.
5. Preserve pre-change configs, the profile registry and private memory as part
   of the owner's normal backup. For rollback, restore the previous immutable
   candidate and its configuration/registry revision under the same master
   deployment workflow. Exporter writes no world data and deletes nothing.

Focused Python exporter tests and the exact-JAR JSON probe passed. Native
coexistence, multiplayer, external-provider, Voice Chat, animal support and
game performance remain **not run**, requiring the coordinated runtime window.
