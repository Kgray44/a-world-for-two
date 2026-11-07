# Deploy the configured cast through existing LIFE and Character Studio

The current official Control Room registry was read on October 29, 2026. Its ten
figures are Barnacle Bill, Old Finn, Captain Blackthorn, Mara Keel, Steward
Pembroke, Librarian Elm, Captain Thimble, Poppy Green, Foreman Rivet and Mercy
Tide. All ten were unbound. The global model was Luna; external AI was disabled.
This observation is a source input, not evidence that a villager exists.

`living_world/cast.py` gives each existing identity a suitable room, vanilla job
and job block. It never changes their names, authored professions or personality.
In particular, a vanilla weaponsmith supports Thimble's guardhouse role; it does
not make him a combat guard. A toolsmith does not build ships or operate Create.

## Smallest deployment

Keep the already installed Living World 0.2.0, Chatting Villagers 1.1.0 and Smart
Villagers 2.0.0. No new JAR, provider, controller or construction framework is
required. Master remains the only official world and runtime writer.

1. Start with **Barnacle Bill alone**. Reuse existing native LIFE preparation:
   one `minecraft:villager` HOME member, `source_group_id: character-barnacle-bill`,
   an authenticated actual tavern site, a distinct genuine vanilla bed HEAD,
   a smoker job POI, a roof and both complete body-clear routes. Preserve the
   current population namespace, UUID census and durable intents. Real authored
   rooms must supply the coordinates; this tool supplies none.
2. Use the existing habitat verification, LIFE inspect and seed operations under
   the master lease. No alternate `/summon` path bypasses those transactions.
   Preserve failed receipts and uncertain intents. A failed or unloaded resident
   is not permission to create a replacement.
3. Prepare a private Studio draft with the command below. The source tool reads
   the **current** registry and existing LIFE recipe(s); it writes only a new
   staging folder. It never installs configuration or claims that spawning worked.
   The same recipe naming rule applies to the other nine existing IDs.

   ```powershell
   python -B -m tools.living_world_cast --registry "$stage/dashboard/characters/registry.json" --recipe "$recipe" --output "$newPrivateStagingFolder"
   ```

4. After genuine native admission, verify Bill's exact UUID/type with the existing
   read-only `/awftcharacters inspect <entity>` and the native LIFE terminal.
   Fetch his current Studio detail/revision, submit the draft's `character` to
   the existing `/api/characters/save` with that revision, then call existing
   `/api/characters/apply` with the resulting current revision. **Use Save**, not
   Import: Import intentionally refuses existing IDs and clears entity bindings.
   If an owner edit occurred after staging, regenerate the draft first. Do not
   copy an old registry/runtime file over the live one. No secret is included.
5. Check the exact exported hash in the native acknowledgement. With a real
   player nearby, use Smart Villagers' installed normal conversation interaction
   and observe Bill's custom reply in Minecraft and its configured bubble. A
   preview or successful Apply alone does not satisfy this check. Change a line
   in Studio, Save/Apply, verify the new exact acknowledgement and see that new
   line in another real conversation. At night/rain the draft fills only empty
   contextual categories, preserving all owner-authored lines.
6. Observe ordinary villager work/rest: actual compatible job/HOME memories,
   profession, pathing, sleeping and waking. LIFE checks free POIs but does not
   assign them. Do not claim these behaviors merely from the spawn flags. Keep
   villagers on normal AI; do not pin them with NoAI, perpetual teleports or
   fabricated brain NBT. Add a native visible name only through the master lane's
   normal entity operation after the exact UUID check; the adapter already uses
   the profile name for dialogue/persona.
7. Perform a normal master-controlled restart. Verify the same UUID, retained
   profile/line, real HOME/job behavior and another conversation. With two real
   consenting players, check one conversation lock, no reply to the wrong player,
   bubble visibility and cooldown. Two accounts are required for two-player
   acceptance. Keep the finished scripted demonstration independent of credentials.

Once Bill works, admit the other nine in small source-bound batches. Each gets
its own actual bed/job and room routes; no decorative Handcrafted bed substitutes
for a vanilla HOME. The legacy policy permits only four villagers. Use the
**existing authorized v4 scaled-budget/ramp path** for all ten; never enlarge or
silently bypass the legacy policy. This source supplies no scale authorization.

## Ordinary inhabitants and wildlife

The small **first cohort** target is **56 managed residents total**, including retained
intents and the ten named figures. `TARGETS` contains 16 villagers (ten named and
at most six ordinary), deer, birds, shima enaga, butterflies, ladybugs, the already
curated Critters dragonfly, koi, pondies, ducks, fireflies and improved cats. The
held Naturalist dragonfly remains held. These are total targets, not an extra
cohort or a deletion instruction. Count existing identities and uncertainty
before deriving any new members. Preserve all existing and player-owned life.

Reuse the current native HOME/DRY/AIR/WATER/SHORE habitat rules and actual measured
fields. Aquatics need complete connected source water with real swimming volume;
ducks also need a dry exit. Insects/birds need species-appropriate leaves/flowers,
flight space and actual darkness where required. No pets get assigned/tamed to a
player by this source. Do not spawn wildlife into a named villager's interior.

Spread additions across suitable habitats in batches of at most eight new
residents after the first named figure. Use the current global, per-species,
per-32-metre habitat and native per-operation budgets; the smallest applicable
limit wins. Compare real behavior, current loaded chunks/entities, MSPT, CPU and
RAM before and after each batch. Stop additions if pathing, despawn/survival or
resource behavior deteriorates. Existing managed caps do not cap unrelated
natural spawns or guarantee frame rate. No new permanent chunk tickets or large
local model. Ordinary ambient speech stays scripted; external requests remain
intentional, asynchronous and subject to the existing consent and allowance.
This first cohort is not a replacement or final ceiling for the owner's broader
Living LIFE population. Continue later measured cohorts through the existing
authorized scale/ramp path, preserving the seven previously admitted actors.

## Current city premises, source-only

`tools.living_world_tortuga_sites` reads the coordinator-pinned completed25 seal
and current14 full plan, resolves each actual native25 verification to its exact
authored after-plan, and proposes ten separate premises. It reads no world. It
only adds beds/job stations to explicitly known AIR with genuine source floor,
headroom and roof cells and connected same-floor adult paths. Unknown cells are
refused. This source screen is not native collision/POI or room acceptance.

Bill uses Anchor & Dice; Finn uses Tidefish Hall; Blackthorn uses Tide
Broker's House; Mara uses Sandbar Carpenter; Pembroke uses Crooked Customs; Elm
uses The Worn Book; Thimble uses Shoal Warden's Quay; Poppy uses River Stone Rooms;
Rivet uses Pelican Forge; Mercy uses Old Rum Warehouse. Existing room objects and
inventories stay in place. Source reports list preserved chairs, desks, books,
plants and lights around each proposed resident. Character names already appear
through the configured persona/dialogue system; no additional sign operation
delays the first conversation. The initially screened Lantern Harbor
Inn ground bed was identified as a retained player anchor and withdrawn. All
three private Inn room capsules, player anchor columns and unknown/private BE
positions are excluded from assignments, new fixtures and routes. Old source
candidate sets remain retained and superseded; use the final custody-corrected
set supplied by the development lane.

Five visitors retain their original role, backstory, knowledge, personality and
model. Proposed `district` and `home_location` changes are explicit in each site
record; no live profile is edited. After master prepares real LIFE recipes using
these sites, pass `--sites cast-sites-SOURCE-ONLY.json` to `tools.living_world_cast`
to include only those explicit premise edits in the staged Save drafts. Generate
fresh drafts if an owner changes the district or home before deployment.

## Concrete prerequisites still missing

The registry supplied names and text, **no entity UUIDs or assigned coordinates**.
The current city source proposals now supply ten concrete room/HOME/job/route
candidates and minimal AIR-only fit-outs. They still require fresh actual
native inspection and the existing LIFE recipes before ten live binding drafts
can be submitted. Pending acceptance is never filled with invented evidence or
claimed complete from authored plans. Master supplies current
native habitat/POI results and actual gameplay observations. No additional source
capability is needed for scripted dialogue. Bespoke guard, shipwright, captain or
Create-worker behavior would be separate work; this delivery uses normal native
villager schedules, jobs and trades.

External AI is still unverified until an authorized dedicated credential is
configured through the existing masked Control Room entry and a genuine selected
model request succeeds. Do not use ambient account credentials or send a key to
Codex. No provider request is made by this preparation.
