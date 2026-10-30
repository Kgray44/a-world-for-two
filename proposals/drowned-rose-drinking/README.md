# Actual mugs and a client drinking pose — source proposal

No installation, artifact release, mod version change or TavernMod edit is made.
Root's current music/chair client qualification remains independent.

## Installed items

| Exact item ID | Installed behavior and appearance |
| --- | --- |
| `farmersdelight:apple_cider` | Recommended tavern drink. Native `DrinkableItem`, `UseAnim.DRINK`, 32-tick use. Its model inherits `farmersdelight:item/mug` with dedicated third-person hand transforms. |
| `farmersdelight:hot_cocoa` | Functional mug alternative. `HotCocoaItem` extends the same native drink class; its item model also inherits `item/mug`. |
| `farm_and_charm:strawberry_tea_cup`, `nettle_tea_cup`, `ribwort_tea_cup` | Functional tea cups registered as Foundation `EffectDrinkItem`, whose actual implementation returns `UseAnim.DRINK`. Food effects and native returned containers remain mod-controlled. |
| Vinery wine/juice drink items | `DrinkBlockItem` inherits Foundation `PlaceableDrinkItem`, with native DRINK use and container handling. These are bottles, rather than the requested mug. |
| `handcrafted:wood_cup`, `terracotta_cup` and colored cups | Decorative ordinary `BlockItem`s. Do not label these functional drinks or pretend that `startUsingItem` makes them consumable. |

The Farmer's Delight mug is a held item sprite with native hand-display
transforms, not a newly authored 3D tankard. `farmersdelight:mug` is the model
parent name, **not an item registry ID**. No compatible standalone tankard/beer
item was found in the installed item-model/class-name scan.

The pinned offline inputs are Farmer's Delight1.3.4, Farm & Charm1.1.29,
Vinery1.5.6, their embedded Foundation1.0.7 and Handcrafted4.0.3. The audit JSON
records their actual JAR hashes. No new drink mod or external assets are needed.

## Why the current potion does not visibly sip

EasyNPC7.17.1's `ModelArmPoseUtils.getArmPoseWhileUsingItem` handles bow, crossbow,
spyglass and spear, but DRINK falls through to DEFAULT. Its standard humanoid
renderer is not the vanilla player renderer that selects player item-use arm
poses. `EasyNPCItemAttachmentLayer` follows the humanoid's ordinary hand; it does
not independently move a drinking hand to the mouth. Native `startUsingItem`
therefore supplies real use state and duration, but does not establish a visible
third-person sip for these patrons.

The two proposed client classes add a smooth, modest arm lift only during actual
native DRINK use. They inspect the real using hand and duration, and handle either
handedness. Only that arm and its sleeve change. A real mug remains in its native
hand attachment. Instrument use, held idle items, legs, seats, root position,
entity state and inventories remain untouched. The PlayerModel TAIL hook survives
EasyNPC's cancellable superclass setup and commutes with the separate seat fix:
the seat correction preserves arm rotation, and this drinking pass preserves
arm position and all seated geometry.

## Integration reserved to the Tavern author

After Root finishes the current music/chair check, include these two source
classes and the client-only Mixin JSON in the existing build and metadata.
In the existing drink activity, select a real `farmersdelight:apple_cider` or
`hot_cocoa` stack, verify its native animation is DRINK and duration is positive,
then call the existing `startUsingItem` on that hand. Never use the model-parent
name as an item ID, attach food components to decorative cups, or fake a
permanent drinking flag. Preserve native effects/container handling and the
existing policy for temporary social props; do not draw from private stock.

The installed consumable code has player-specific statistics/container branches;
actual Mob completion, retained cup/container behavior, audio and inventory
semantics still need a representative in-game observation. The client proposal
does not claim to repair server item-consumption behavior.

Root should check standing and genuinely seated right/left-hand sipping, the
start/end transitions, visible mug placement and an unaffected playing musician.
Arm angles and item-model placement remain visual candidates until that check.
Source/API compilation is not a working-sip claim.

Lounging remains held: no supported standard-humanoid lounging clip or reviewed
bar-edge/body-clearance setup is established. Do not turn an unverified animation
name or arbitrary entity teleport into a claimed lounging interaction.

Primary author references: [Farmer's Delight drinks](https://github.com/vectorwing/FarmersDelight/wiki/Drinks)
and [EasyNPC pose modes](https://github.com/MarkusBordihn/BOs-Easy-NPC/wiki/Pose).
The pinned local JAR implementations, rather than newer documentation, establish
the item types and missing DRINK arm branch described here.
