# 0.1.12 candidate: native instrument pose after Smooth

This separate successor retains the frozen0.1.11 artifact. It adds one client
helper and one call from the existing optional Smooth NPC model TAIL, plus
version metadata. Native dismount, seating, sip, navigation, ledger, roster,
skins and playback behavior remain as in0.1.11.

Pinned Immersive Melodies0.8.0 injects EntityModelAnimator.setAngles at the
HumanoidModel setup TAIL. Smooth1.1.0 subsequently resets head/arm/leg/body
parts in its NpcPlayerModel override. The new final pass calls that same public
native instrument animator after Smooth, using its public ArmsAndHeadAccessor.
BipedModelAccessor is exactly that accessor plus getModel; none of the native
vielle, lute, flute or tiny-drum animators uses a model-specific cast.

The helper requires a live client EasyNPC with a local tavern skin, no active
item use, and a held native InstrumentItem whose actual native isPlaying flag
is true. It runs once, then synchronizes sleeves and hat with the affected
parts. Native sitting legs/pivots are applied first, and actual DRINK sipping
remains exclusive through the item-use guard. Other models retain their
existing Immersive Melodies hook; other NPCs retain Smooth behavior.

There are no copied keyframes, alternate animations, reflection, proxy matching,
playback calls, world/inventory writes or ledger migration. The native renderer
does update its normal visual envelope through getProgress/visualTick. This is
a rendering operation, not read-only telemetry and not fresh audio evidence.
The earlier superclass pass uses the same native per-frame time; the subsequent
visual-envelope delta is normally zero after it has already advanced.

The coordinating chat independently observed native playback progress and
recent notes for four actual instruments before this successor. That evidence
does not prove heard audio or correct visible poses. ArmPose enum EMPTY alone
also does not prove an animation failure: native instrument animators write
rotation fields without changing that enum. Actual framebuffer/native rotation
checks remain necessary after matched installation by the coordinating chat.

Exact pinned API/animator bytecode is retained privately under
`D:\A World for Two\staging\drowned-rose-source-20261029\instrument-0112-review`.
This source worker does not install, join, move patrons or invoke Native actions.
