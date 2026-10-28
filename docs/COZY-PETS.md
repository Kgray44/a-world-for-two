# Hamsters and sugar gliders

This is a **source-ready proposal**, owned by the pets chat
`01a18485-d67f-7b31-bebc-1367f120a17f`. Build It! remains the only integration,
runtime and official-world writer. The isolated branch is
`codex/hamsters-sugar-gliders`, based on `3d337e4305006d4745ba6ba85c458accf54ef1f1`.
The committed baseline contains candidate.53; candidate.55 was already being
prepared in the master's dirty checkout. No master pins are copied back wholesale.

| Component | Exact author pin | Review |
| --- | --- | --- |
| Adorable Hamster Pets | `LmrhZdK2 / LyCV3JSL`, `3.7.0-1.21.1+neoforge`, 20,292,862 bytes | Explicit reviewed beta exception; all compatible NeoForge releases listed in this query are beta. Actual JAR requires Architectury >=13.0.8, GeckoLib >=4.8.3, Fzzy Config >=0.7.6 and Patchouli >=93. |
| Animal Garden: Sugar Glider | Existing `WktWffF9 / uHLwVY2K`, `1.0.0-neoforge-1.21.1-21.1.214`, 317,381 bytes | Both sides/default enabled in Packwiz; exact SHA-512 matched the construction server and KG's existing Prism instance. Startup log lists the mod. No new entity interaction was tested. |
| Aquarius Libs | `KkHnyaL6 / sPrpmle3`, `1.2.0-neoforge-1.21.1-21.1.217`, 234,187 bytes | New explicit both-side pin. Author requires it; absent from the existing lock/install. This older glider JAR is self-contained and declares no native/API dependency, so absence alone did not prove a broken existing startup. |
| Patchouli | `nU0bVIaL / BIogJv2D`, `1.21.1-93-neoforge`, 646,777 bytes | New both-side native hamster dependency. |

All filenames, sizes, SHA-512 values and licenses are in
[`manifest.json`](../proposals/cozy-pets/manifest.json). New downloads total
21,173,826 bytes. Upstream binaries are never committed or redistributed here.
Hamster metadata identifies a custom license; its native descriptor says All Rights
Reserved. Aquarius is ARR; Patchouli's metadata is CC-BY-NC-SA-3.0. Keep author CDN
links and the original licenses. Source availability is not a redistribution grant.

The author API omits dependencies for both pet pins. Do not trust those empty
arrays: all three additions are explicit selection records. The existing
Architectury13.0.11, GeckoLib4.9.3, Fzzy0.7.7+fix1 and Kotlin5.12 pins are retained.
An eight-JAR native dependency check passed on both sides with zero errors or
warnings. The complete proposed201-enabled-JAR graph subsequently passed with
zero errors/warnings after exact file size/hash verification against the baseline
lock and additions. Existing cache bytes were read in place. This is static
metadata compatibility, not a full-pack game launch or animal-behavior test.

## Cozy defaults

The proposal has 37 main and six worldgen settings, each checked against fields
in the hash-verified3.7.0 JAR and the matching
[first-party source commit](https://github.com/DawsonBodenhamer/AdorableHamsterPets-Source/tree/585d2b5063735f1a7e9573010dae25d024e6ce67).
Fzzy uses top-level TOML fields; GUI groups do not become TOML tables. Separate
`main.toml` and `worldgen.toml` are used. Effective server/client loading and sync
still require native verification.

- Disable throwing at the server-side guard, throw friendly fire, throw damage,
  redstone fever, crop snacking, item theft, independent diamond seeking,
  player-chasing tag, hide-and-seek and hostile-mob scare overrides.
- Enable owner friendly-fire protection, following-pet teleport rescue, End portal
  protection, retained shoulder pets on owner death, and free recovery at a valid
  linked Hamster Bed. Acorn Rings may protect other players' pets through the
  mod's normal contract; this is not universal invulnerability.
- Retain tameable/breedable pets, ordinary AI, petting, grooming, daytime bed sleep,
  shoulder idle animations and hamster-to-hamster play. No optional Punchy or
  second player-animation controller is added.
- One baby per litter,20-minute cooldown, two litters per player per real-world
  day, eight lifetime litters per hamster; offspring use normal inherited ownership.
  Maximum two shoulder mounts; initial bed wander radius four blocks.
- Hamster natural spawn weight3 and groups of one, in forest-tagged biomes plus
  plains/meadow/cherry settings. Gliders retain the author's exact biome tag and
  singleton groups; a Paxi datapack replaces the **same** native modifier resource
  to lower weight8 to2. It does not add a second overlapping spawn entry.

Weights and breeding limits are not an absolute entity cap. Actual habitat,
biome-cap competition, breeder activity and loaded chunks decide counts. Measure
with existing animals before accepting these defaults.

The [glider author](https://modrinth.com/mod/animal-garden-sugar-glider) describes
food-based taming/breeding, three behavior modes, climbing and gliding. The pinned
bytecode contains breeding, climbing, floating, saved behavior/home and inherited
tameable data. It does not establish hamster-like bed recovery or configurable
friendly-fire immunity for gliders. No such glider settings are invented. Hamster
assets include cleaning and natural sleep animations; actual rendering alongside
Smooth Player Animations/Cinematic Interactions remains untested.

## LIFE placement

[`life-habitats.json`](../proposals/cozy-pets/life-habitats.json) is generated by
`python -m tools.cozy_pet_habitats`. It contains two detailed relative schematics,
with no absolute anchor, native commands, player UUIDs or world authority:

| Place | Source design | Living residents |
| --- | --- | --- |
| Near the homestead | 11x9 conservatory with mossy foundations, spruce frames, clear roof, flowers, low climbing steps, two shaded wooden sleeping alcoves and **real Hamster Bed blocks** | Two `adorablehamsterpets:hamster`, master admission ceiling four |
| South-shore forest | 15x15 wooded aviary with two staggered branch trees, separated glide space, moss landing pads, layered leaf canopies and two roofed nesting shelters at different heights | Two `animalgarden_sugarglider:sugarglider`, master admission ceiling four |

The four initial animals and ceiling of eight are admission budgets for these two
managed sites, not an automatic global breeding/spawn cap. Nest shelters are
ordinary usable wood architecture; the residents must be actual modded entities.
Never substitute an armor stand, plushie, display, NoAI animal or invulnerable prop.

Gliders climb ordinary walls/fences. Both schematics therefore have continuous
enclosures, covered entrances and two separately operated vestibule doors. The
forest enclosure must be fitted around the surveyed landscape; do not flatten the
forest or clear existing trees just to fit this rectangular source. Existing solid
support and interior/flight AIR masks are explicit requirements. These designs
still need terrain fitting, native block/BE/containment checks and eye-level visual
refinement. The master may adapt them under the normal construction rules.

Before any admission: master lease and retained verified checkpoint; current
roster exclusion; actual native entity/block registry, position/support/air and
protection/POI/contraption masks; install matching mods/config on server and client;
then habitat-before-resident verification. Do not replace either save. Normal
owner taming and bed linking establish ownership, not guessed account UUIDs.
Neither pet currently appears in the native LIFE species policy. The separate
[`life-species-review.json`](../proposals/cozy-pets/life-species-review.json)
supplies exact class, JAR, body-dimension and bed/resource hashes for the master's
reviewed additive admission. No active whitelist or safety policy is modified.
Hamster Beds are not fabricated vanilla villager bed/job POIs.

**Recovery identity matters:** the mod's `HamsterBedUtil` creates a new UUID,
copies custom hamster data and owner, updates the bed link, and returns the pet
asleep at5% health. External LIFE tags may not survive. Keep each managed slot
held until its observed old/new UUID, owner, name, bed and inventory are reconciled.
Do not automatically refill a missing UUID, assign a new owner, or fabricate a
respawn. Keep the bed intact with safe surrounding space and heal the recovered
pet normally. For gliders, use enclosed habitat, normal ownership/name persistence,
predator separation and retained checkpoints; no native resurrection is claimed.

## Master integration and qualification

The standalone preview is safe to inspect:

```powershell
python -m tools.cozy_pets
python -m tools.cozy_pets --stage .local/pets-preview
```

The first command is read-only; the second requires a new stage directory and
writes only source under this worktree's `.local`. It updates Packwiz, direct
pet/dependency request records and both compatibility views inside that preview.
The direct glider request coexists with the retained flying-squirrel alternative;
sugar gliders are marsupials. All unresolved/incompatible requests remain.

After the master integrates this focused source PR and chooses its next version:

```powershell
# Integration owner, in the master source checkout, during the serialized window:
python -m tools.cozy_pets --apply-source --version <next-private-candidate>
python -m unittest discover -s tests -v
python -m tools.pack validate
node --check control_room/static/app.js
```

The source integration refuses changed glider pins, conflicting pet pins,
out-of-range/client-only dependencies, changed payloads, existing different pet
configs or an invalid current Packwiz index. It retains every other current mod
record, including the master's latest bridge; it never broadly re-resolves the pack.
It does not install JARs, launch Minecraft, manipulate a world or publish anything.
The master also incorporates the three new license records into release notices.

Recorded source verification is in
[`verification.json`](../proposals/cozy-pets/verification.json): twelve focused pet
tests pass, Packwiz baseline208 and preview211 validate, and JavaScript syntax
passes. The required full suite ran1,105 tests in73.289seconds, with three import
errors and one skip. The errors are existing city tests importing
`artistic_tortuga_coast_batches` or `artistic_tortuga_west_approved_blocks`, both
absent from committed baseline3d337e4 and present only as unrelated untracked
master work at inspection. That failed receipt is retained; those files were
neither borrowed nor repaired in this pet branch. Full-suite qualification remains
open for the master's complete integrated checkout.

Run the cases in [`qualification.json`](../proposals/cozy-pets/qualification.json)
in the exclusive master test window. Retain exact candidate/pack/config/JAR hashes,
real roster and before/after measurements. Each result has its own runtime,
animation/visual, ownership, multiplayer, persistence, performance and permanent
integration state. Do not promote static checks to any of those states.

Storage writers were admitted with bounded C: allocations and D:0; both live
drives were above32,212,254,720 bytes. The source CLI repeats ReserveGuard for
writers with a64MiB bound. Test execution uses a separate bounded check. These
instructions and checks do not constrain external applications or pre-existing
writers. No save, runtime/client configuration or permanent-world entity was
changed by this specialist.
