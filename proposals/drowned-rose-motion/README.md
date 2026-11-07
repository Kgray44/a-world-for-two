# Drowned Rose client micro-motion proposal

Source only. No installation, world edit, entity change, runtime acceptance or
visual acceptance is claimed. TavernMod, activity policy, configuration and the
Tavern author's build remain untouched.

The pinned EasyNPC 7.17.1 JAR exposes `EasyNPCModel.setupAnimationEnd` and the
public `EasyNPCModelManager.getModelPart` API. Its HumanoidModel mixin calls this
method after ordinary pose/arm setup, and resets model parts before each new
entity render. This gives a narrow hook without accumulating offsets or changing
server entity positions, AI, paths, equipment, seats or persistent data.

The proposed client mixins add slow, UUID-staggered weight shifts, breathing,
small head turns, modest empty-hand gestures and frequent seated upper-body
adjustments. Real Handcrafted Seat passengers keep their riding pose and legs.
Walking fades the idle offsets out. Held items, drinking, swings, explicit custom
poses, disabled animations and animation requests take precedence over idle
adjustments. Existing
instrument poses are left entirely to their native integration.

The seated correction is separate from idle adjustments and runs even while
holding an instrument or drinking. EasyNPC can cancel vanilla HumanoidModel
setup at HEAD, bypassing vanilla riding legs and its own TAIL animation callback.
The additional PlayerModel TAIL hook runs after that superclass call and clothing
copy, restoring vanilla riding-leg angles for actual `instanceof Handcrafted
Seat` passengers, including the persistent subclass. It preserves arm/head/item
rotations. Render-only body lowering is derived from the difference between
`Player.DEFAULT_VEHICLE_ATTACHMENT` and the NPC's actual vehicle attachment,
rather than a guessed chair height. Model pivots use their initial values each
time, preventing accumulated lowering. No passenger position is changed.

Selection uses EasyNPC's synced `SkinDataEntry.texture` with the existing
`awft_tavern:textures/entity/` prefix. It does not assume server scoreboard tags
are synced to the client, and it does not infer ownership from names.

## Integration by the Tavern source owner

Include all three Java files and `awft-tavern-motion.mixins.json` in the existing
Tavern build. Register the client-only mixin configuration in that mod's existing
metadata with a `[[mixins]]` entry naming this JSON. Keep the dependency pinned to
the tested EasyNPC 7.17.1 API. No new gameplay controller or mod entrypoint is
needed. Root owns candidate matching, installation and the restart window.

The public `ModelAnimationAPI.playAnimation` is unsuitable for these standard
humanoid patrons: the actual 7.17.1 implementation requires an `EasyModelNPC`
and Easy Model Entities. Do not claim it supplies lounging clips for this model.
No supported lounging preset or geometry-specific bar-edge support has yet been
verified; this proposal therefore adds no invented lounging/sitting pose. A later
supported lean needs an actual furnished location and body-clearance review.

## Required live review

Root should inspect a standing idle patron, an actual seated patron, walking,
drinking and a playing musician with the matching client. Check that hats and
skin layers follow, legs remain seated, item poses remain intact, movements are
subtle and offsets do not bleed into the next NPC. A successful compile proves
API compatibility only; appearance and Mixin application need that real client.

Author references: [pose modes](https://github.com/MarkusBordihn/BOs-Easy-NPC/wiki/Pose)
and [public API](https://github.com/MarkusBordihn/BOs-Easy-NPC/wiki/API).
Pinned local 7.17.1 source and JAR bytecode, rather than newer wiki examples,
determine the concrete hook and animation limitation above.
