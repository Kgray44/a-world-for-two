# Living World and Character Studio

This lane adds district dialogue, ten authored villager profiles and the **Characters**
page to Control Room. It is a source integration proposal, with native qualification
still required. Neither the official server nor the permanent/construction saves
were changed. Coordination starts in [issue #10](https://github.com/Kgray44/a-world-for-two/issues/10).

## Use the Studio

Open Control Room Ã¢â€ â€™ **Characters**, search for Barnacle Bill, and open his card.
The editor has Overview, Personality, Knowledge, Dialogue, AI & Memory, Voice,
Location and History sections. All portraits are locally rendered character icons.

1. Edit identity, freeform personality instructions, traits, speaking style and humor.
2. In Knowledge, add sourced facts, clearly fictional rumors, personal lore or unknowns.
   Secret entries never enter provider prompts. Edit shared district knowledge separately.
3. In Dialogue, add one short line per row. Empty personal categories inherit the
   district catalog. Shared district dialogue is editable without source-file changes.
4. **Save** validates and persists the registry, checks its revision against newer
   edits, and retains the previous profile in History. Revert Changes discards the
   draft. Restore Defaults is a draft until saved. Duplicate/import creates a new,
   unbound identity, with AI disabled; removing a registry profile never deletes an entity.
5. Test Conversation uses the **saved** profile. Scripted previews need no provider.
   Try Scripted Dialogue tests a selected category. Neither sends dialogue into Minecraft.
6. **Save and Apply** writes a bounded, validated runtime snapshot. The installed
   adapter watches atomic file changes, validates off the tick thread, then swaps the
   configuration on Minecraft's executor. Until its exact hash is acknowledged, the
   UI reports staged/pending. An acknowledgement for an older snapshot never claims
   a newer edit was applied. New mods require the owner's normal restart workflow.

Authored profiles start **unbound**. They do not establish that an entity has been
placed. An operator can inspect an existing entity with
`/awftcharacters inspect <entity>` and bind its returned UUID in Location. No spawn,
teleport, deletion or command execution is performed by the Studio. District bounds
must come from the owner's actual layout; unset bounds never become made-up map areas.
The district API accepts a dimension and explicit min/max X/Y/Z coordinates.

## What runs where

| Capability | Implemented behavior and qualification boundary |
| --- | --- |
| Ambient villagers | Chatting Villagers 1.1.0; 121 original district lines plus 16 two-speaker exchanges. Dynamic selection uses current personal/district data, weather/time conditions, native anti-repeat IDs and quiet global limits. Native behavior remains unqualified. |
| Named conversations | Smart Villagers 2.0.0; the adapter selects enabled, UUID-bound villager profiles. Native asynchronous HTTP and text displays are retained. Names, personality instructions and relevant approved lore are composed at the request boundary. |
| Global game AI | Studio's global **OpenAI** provider/model policy reaches upstream through the adapter after Apply. `SMARTVILLAGERS_API_KEY` stays in the server process environment. Per-character provider/model overrides and Anthropic currently configure dashboard previews only. |
| Scripted fallback | Personal/district dialogue works without a provider. Missing consent, configuration, pricing, capacity or provider availability falls back to text. |
| Bubbles | Enabled by default. Per-character enable/disable is supported by adapter source. Native bubble distance/lifetime are global upstream settings; per-character controls are visibly unavailable. |
| Memories | Dashboard preview memory has bounded retention, correction, removal and reset. Native memory can be disabled and context is capped at eight upstream exchanges; native retention/correction UI is unavailable. Previously persisted upstream memories are not deleted merely by disabling future storage. |
| Atlas | Stable profile links, character layer, type-aware search and known-position focus. Assigned homes remain assigned; expired native samples become last known. Current presence requires the exact owned PID/start time/cwd and a fresh sample. |
| Backups | Existing world backup includes registry and staged runtime snapshot. Restore preserves the current character folder in the recovery directory before replacing saved profiles. Credentials are not in these files. |
| Voice | Optional Simple Voice Chat pin is proposed, disabled. Audible TTS and its UDP route require owner setup and a real hearing/fallback test. The current adapter leaves voice disabled. |
| Animals | Animal/custom profiles can be authored and previewed. Native animal AI is unavailable. CreaturePals is held for dependency/metadata and AI-directed entity-action conflicts; no unsupported animal is silently enabled. |

The initial characters are Barnacle Bill, Old Finn, Captain Blackthorn, Mara Keel,
Steward Pembroke, Librarian Elm, Captain Thimble, Poppy Green, Foreman Rivet and
Mercy Tide. Their backstories are authored fiction, distinct from sourced project facts.
The eight templates also include a judgmental cat and a loyal, ridiculous dog.

## Privacy, costs and resource limits

External AI starts disabled, with no model selected. Configure current model rates
and a server-side environment variable before enabling it. Each dashboard external
test requires explicit consent; normal game chat requires upstream player consent,
and the adapter independently checks consent even for the upstream operator test path.
No large local language model is launched.

Only relevant non-secret facts/rumors are retrieved. Unknowns and forbidden topics
are excluded, and missing facts require an admission of uncertainty. Obvious unsupported
coordinate-shaped replies are refused. These guards do not prove arbitrary generated
prose true; owner review remains necessary. AI output is never a server command or action.

Native requests have a hard cap of two concurrent calls, per-character cooldowns,
persisted hourly admission and a conservative daily cost reservation. The adapter
rechecks the exact configuration, player consent, loaded entity and proximity after
disk admission, immediately before upstream's nonblocking network call. The native
token ceiling is 120 and upstream display ceiling is 180 characters. Native ledger
reservations are not refunded on failures. Dashboard previews and native game requests
enforce their budgets **separately**; the configured amount is not a pooled account cap.
Administrator-entered rates are estimates, and provider billing is authoritative.

The registry permits 64 profiles, a 1 MiB runtime export and an 8 MiB retained registry.
History retains twelve versions per profile. Preview memories are separate from authored
lore. Existing Task history may retain generated preview responses among its last fifty
jobs even when conversational memory is disabled; do not use private player information
in test prompts unnecessarily. Credentials and provider error bodies are not returned.

Profiles load on demand; display/navigation makes no AI requests. Atlas uses its existing
poller. Native telemetry checks only configured UUIDs every 300 ticks, without generating
or loading chunks. A bounded I/O worker and filesystem events handle configuration changes.
Owned writers use the AERO reserve guard and check both drives. This instruction does not
constrain other applications or pre-existing writers and is not an OS quota.

## Integration contract

The feature branch starts at `3d337e4305006d4745ba6ba85c458accf54ef1f1` from
`codex/master-integration`. New feature code is in `control_room/characters.py`,
`control_room/character_atlas.py`, `living_world/`, `static/characters.*` and
`compat/living-world/`. Shared changes are narrow hooks in `web.py`, navigation,
the Atlas frontend, backup inclusion/restore and packaging `living_world*`.
There are no changes to `server.py`, the active control bridge, canonical
`catalog/*`, canonical `packwiz/**`, release channels or world saves.

The runtime contract is `awft-living-world:1` in
`dashboard/characters/runtime.json`. `registry.json` remains private dashboard state.
The adapter publishes `awft-living-world-state:1` in `native.json`, including
the config SHA-256, revision, observation time, process identity and up to 64 loaded
entity observations. Native pricing/admission reservations live in `native-budget.json`.
No API key is exported. `native.json` is telemetry, not proof of player acceptance.

All HTTP routes retain Control Room's loopback/origin/session protections. GET routes
are `/api/characters`, `/detail?id=Ã¢â‚¬Â¦`, `/export?id=Ã¢â‚¬Â¦`. POST operations under
`/api/characters/` are `save`, `remove`, `duplicate`, `import`, `restore`, `defaults`,
`district`, `settings`, `memory`, `preview`, `ambient` and `apply`. Mutations use
the supplied `expected` revision. Conversation previews run as existing background Jobs.

## Install and roll back through the main lane

1. Master reviews this branch and serializes the shared hooks with current Control Room work.
   Review every exact pin and retained exclusion in the compatibility inventory.
2. Export a fresh proposal with `python -m tools.living_world_upstream --output <new-directory>`.
   It refuses overwrites and writes no world. Build the owned addon with Java 21:

   ```powershell
   python -m tools.build_living_world --home <existing-compile-home> --dependencies <verified-author-jars> --output <fresh-owned-addon.jar>
   ```

   Compiler APIs are read only; this does not install the addon. Never commit downloaded JARs.
3. Master retains a verified backup, creates a private matching candidate containing the
   two native mods, adapter and proposed defaults, then regenerates Packwiz's complete
   hash chain. Keep voice/animal AI off. Preserve any existing stock/custom dialogue
   before disabling overlapping pools. Install client-side files as specified by the
   exact author metadata; an advertised loader match is not a compatibility result.
4. Under a coordinated runtime window with the owner's EULA/account authority, bind
   actual NPC UUIDs, set measured district bounds and apply the snapshot. Check its exact
   acknowledgement, then test edited dialogue in game and again after a normal restart.
5. Test two real players, simultaneous different-NPC chats, bubbles/overlap, trading,
   jobs/movement, unloaded chunks, disconnects, consent, provider failures/timeouts and
   crowded areas. Measure real server CPU/RSS/MSPT, response latency and network behavior.
6. Roll back through the master's existing candidate/config backup workflow. Restore the
   prior registry from History or a verified world backup; retain the newer registry and
   failed receipts. A profile removal is not entity deletion. Publish no unqualified pack.

## Current evidence and remaining acceptance

The focused registry, HTTP, backup, frontend, upstream-schema and JVM checks pass.
The full inherited suite ran 1,137 tests with three import errors and one skip: the
starting commit references absent `tools/artistic_tortuga_coast_batches.py` and
`tools/artistic_tortuga_west_approved_blocks.py` through three unchanged artistic tests.
Both modules were already absent at base `3d337e4`;
this lane does not copy the main owner's uncommitted construction work to hide the gap.

[The sanitized qualification receipt](../evidence/living-world/qualification.json) records the exact build and checks.

A real NeoForge loader probe discovered all three mods, retained `eula=false`, exited
at the EULA refusal and created no world. No target classes were exported by Mixin
before that refusal. It therefore proves discovery, not Mixin application, native
startup, in-game dialogue or coexistence. The reproducible bounded probe is retained
under `proposals/living-world/mods/probes/loader_probe.py`.

Actual isolated browser checks saved Barnacle Bill's speaking style and a custom joke,
ran a scripted conversation and reproduced the saved joke through ambient preview.
An early warm development preview measured 24 loopback summary/detail requests: median
15.144 ms, p95 27.106 ms, RSS 39,424,000 Ã¢â€ â€™ 39,624,704 bytes and 0.0469 CPU seconds over
0.3585 seconds. Its source was still changing; this is a scoped dashboard observation,
not final-head feature overhead, a sustained benchmark, or Minecraft performance.

Real in-game end-to-end, restart persistence, two-player synchronization, external-provider
responses and server performance remain **NOT RUN**. They require the coordinated owner
window and provider configuration/consent. Source completion and a draft PR do not satisfy
those acceptance criteria. Full upstream/dependency findings are in
[the compatibility record](LIVING-WORLD-COMPATIBILITY.md).

![Actual Character Studio and a saved custom joke, captured in the isolated development preview](images/living-world/character-studio.png)

Actual browser capture; this does not establish in-game or final-head browser acceptance.

The owner selected the **main development lane** to coordinate and execute the remaining
in-game tests. Exact-head [CI run 40776960802](https://github.com/Kgray44/a-world-for-two/actions/runs/40776960802)
confirmed the same three inherited import errors (1,137 tests, three platform/input skips).
No source check was bypassed. A subsequent current-source browser check reloaded the saved
joke after a dashboard restart, reproduced it in ambient preview, checked visibly disabled
unsupported bubble controls and checked the 390 × 844 mobile breakpoint without document
overflow. The temporary viewport was restored.

![Current-source Character Studio desktop check](images/living-world/character-studio-desktop.png)
