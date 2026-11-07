# Riding with a wrench

Both the Create Wrench (`create:wrench`) and Supplementaries Wrench
(`supplementaries:wrench`, displayed as Wrench) are supported ride tools.
There is no separate `zipline:wrench` item in the installed Ziplines mod.

For Create chain conveyors, hold either wrench in either hand, aim at the
chain within reach, and right-click while standing normally. Keep the wrench
held; crouch to dismount. Crouch plus right-click is the native chain-removal
action, so use a normal right-click when boarding. Movement requires real
rotation of the conveyor and follows its speed and direction. These controls
come from the installed Create 6.0.10 handler and match the
[official Create interaction source](https://raw.githubusercontent.com/Creators-of-Create/Create/mc1.21.1/dev/src/main/java/com/simibubi/create/content/kinetics/chainConveyor/ChainConveyorInteractionHandler.java).

For Ziplines on Reconnectible Chains, hold a supported tool, point at the
cable within reach and hold right-click. Jump to detach with a launch, or
release right-click to drop. The installed settings use a 3-block click
reach and a 3.5-block hanging offset. This uses the mod's ordinary controls;
[upstream usage and item-tag documentation](https://github.com/evanbones/Ziplines-Rezipped#usage)
describe the same attachment mechanism. Create chain conveyors keep their
own native riding system.

Two additive tags in the existing `awft-integration` datapack explicitly put
both wrenches in `create:chain_rideable` and `zipline:attachment`. Both already
qualify through the installed mods' `c:tools/wrench` tag. The explicit entries
retain that pack contract while preserving other tools (`replace: false`).
They add no items, change no movement code and do not alter the completed
Hypertube. Canonical Packwiz refresh and normal datapack deployment are still
required; source JSON validation is not a completed player ride test.
