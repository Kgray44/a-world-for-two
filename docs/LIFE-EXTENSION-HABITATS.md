# LIFE beyond the initial four species

This separate source proposal extends the woodland's **candidate** population to birds, insects, freshwater life, town pets, villagers and peaceful musical/magical residents. Nothing has been spawned by this work. The sealed tree/fauna proposals and active bridge remain unchanged. The current four-species policy does not accept these additional identities.

The source [species table](../compat/control-bridge/proposals/life-extension/species-habitats.json) records sixteen exact entity identities, their actual registry categories, pinned artifact/class hashes, inspected behavior, risks and required native observations. Twenty-eight pinned classes were inspected privately, alongside the earlier sealed four-species review. No upstream JAR, class, raw entity NBT or bytecode dump is copied into this source proposal.

The example contains 23 symbolic habitat groups and **64 residents total, including the original four species**. It replaces the old unspawned 57-member composition as a design example; it is not 64 additional residents. Its overall and per-species limits are planning bounds, not a measured carrying capacity or a final population. Actual habitats may admit fewer groups. No world coordinates or UUIDs are invented before the final geography, construction and census are available.

| Candidate | Native category | Proposed setting and material risk |
| --- | --- | --- |
| Naturalist deer | creature | Connected grassy woodland clearings; real grazing changes grass. |
| Naturalist birds | creature | Seed meadows and shrub edges with actual perches/flight space. |
| Naturalist butterflies | ambient | Flower glades; pollination/crop effects need separation from authored growing displays. |
| Naturalist fireflies | ambient | Damp grass margins; glow/night behavior still needs native views. |
| Shima Enaga | creature | Leafy birch perches; leave the native bird untamed and unowned. |
| Ladybugs | ambient | Flowers/leaf understory; native healing aura requires taming and is not supplied by this plan. |
| Naturalist ducks | creature | Gentle reed shores with a real walkable dry exit and native brightness/footing checks. |
| Critters dragonflies | ambient | Open reed airspace; owned combat goals exist, so category alone is not peacefulness proof. |
| Critters koi | water_ambient | Quiet connected freshwater; native koi explicitly avoid otters. |
| Fish of Thieves Pondies | water_ambient | Freshwater candidate, conditional on the actual registered biome/depth/dimension spawn rules. |
| Cozy's Improved Cats | creature | Inhabited courtyards, apart from prey nurseries; inherited cat targets include rabbits/baby turtles. |
| Doggy Talents dog | creature | One unadopted shelter dog; actual default is untamed, ownerless and DOCILE. |
| Villagers | misc | Real homes and reachable bed/workplace POIs; this exact living type is the only proposed MISC exception. |
| Ribbits | creature | A dry reed-side music home, using the real default NITWIT profession and native home initialization. |
| Vanilla allay | creature | One optional fairy-like glade resident, empty-handed and without copied player/note-block memories. |

Naturalist dragonflies are a sixteenth, unselected alternate. Their passive flight does not reveal the whole interaction contract: feeding chorus fruit creates a radius-0.5, 200-tick cloud carrying HARM. That explicit player action is not spontaneous hostility, but it deserves a separate location/risk decision rather than a silent homestead inclusion. Critters dragonflies also have owner-related combat code; neither species receives a blanket safety claim.

Fairy Tales supplies bonds and powers rather than a roaming fairy entity; its author explicitly describes unseen spirits. There is no registered `fairytales:fairy` to seed. The musical [Ribbits](https://modrinth.com/mod/ribbits) are the installed mod's peaceful resident option, while the allay is honestly labelled vanilla. A source plan must not rename a spell/projectile or particle entity into an invented fairy. See the [Fairy Tales author description](https://modrinth.com/mod/fairy-tales).

## Native defaults and player ownership

The pinned Doggy Talents constructor sets tame false and owner null. Its synchronized default DOCILE mode has attack disabled and wandering disabled; hunger, rest, avoidance and other AI still exist. A quiet unadopted dog is not permission to forge an owner, change its mode, or toggle NoAI to manufacture activity. Later adoption belongs to normal player interaction.

Cozy cats call the vanilla Cat initializer and retain its normal behavior. Bowl seeking requires a tamed cat; the plan adds no bowl stock or progression. Ladybug healing likewise returns immediately while untamed. Existing player taming, ownership, commands, jobs, trades and ordinary variant changes must be observed and preserved on future inspection. New-factory checks must never be reapplied as resets to existing residents.

The pinned Ribbit initializer establishes its current position as its home. Default NITWIT behavior plays music; this proposal does not set a sorcerer or merchant profession. Other native professions really fish, bonemeal blocks tagged CROPS, or buff players. Their behavior is not decorative, and later role changes need their ordinary native mechanism and habitat review. An empty-handed allay cannot pick up loot; later player-given matching items can enable normal collection. No item loadout or liked-player memory is supplied.

## Required integration, not a request to seed

The new [source planner](../compat/control-bridge/proposals/life-extension/plan.py) validates the curated counts and habitat kinds. It deliberately emits a different, non-executable format with `seed_authorized=false`, no coordinates and no UUIDs. It rejects arbitrary entity IDs, category-based permission, owner/tame/NoAI/profession/NBT fields and claimed native-success fields. It can verify the exact already-cached selected JAR hashes read-only. It never downloads, installs, launches Minecraft or changes a world.

A later parent-owned bridge change must retain the existing shared lease, exact private-world/candidate/checkpoint/artifact custody, console authorization, complete UUID census and durable per-UUID intent ledger. Normal native factories, `SpawnPlacements` checks, NeoForge spawn/finalize hooks, cancellation and `addFreshEntity` remain mandatory. Types must be actual living `Mob` instances with the exact reviewed class/category and no `Enemy` identity. Do not allow every CREATURE, AMBIENT or MISC type. There is no replacement or deletion when a legitimate resident has wandered or a prior intent is unresolved.

The current dry 45-cell footing witness cannot authorize fish. Aquatics need complete actual connected source-water volume, sufficient depth, refuge, native water/biome/spawn checks and no pump, turbine, fountain-plumbing, ship or bridge-navigation conflict. Amphibious ducks need both water and an actual dry exit. Flying species need a field that covers their real native dimensions and flight clearance; insect names do not imply tiny models. Villagers need actual native bed and workplace POI availability plus traversable routes, shelter and normal brain acquisition. Their jobs/trades must not be fabricated to compensate for unsuitable buildings.

All plots must come from Grand's final continuous saved **FULL** shore-to-cliff terrain and the new postconstruction stopped checkpoint. Protect the complete final R5 plaza/fountain AIR, statue, plumbing, arrival sightline and routes, including its five-metre skirt; the R5 reservation is `c3914908a029ce58ee55124016933f8aa8a850b300da6c269076253b30a9ff3b`. Trees and understory, final art and functional work come first. Unknown cells, sparse survey interpolation and an Atlas image never authorize habitat filling.

Roaming bounds are an observation envelope, not an invisible fence. Do not teleport, pin or disable AI to retain composition. Begin with a small reviewed native pilot, then verify ordinary player-observed movement, rest/feeding/schooling, predator coexistence, idempotence, save/restart and zero leftover temporary tickets. Counts, CPU/RAM/MSPT and client appearance are separate measurements; source inspection proves none of them.
