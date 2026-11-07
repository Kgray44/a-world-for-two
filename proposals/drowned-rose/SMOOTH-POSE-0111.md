#0.1.11 review candidate: pose after Smooth's NPC override

The07:50:30UTC QA9 native snapshot resolves the standing-seat failure. Arlo is
the actual HumanoidNPC, with the correct resource skin, native ManagedSeat
vehicle and VANILLA/HUMANOID/SMART model settings. The renderer is EasyNPC's
standard PlayerRenderer, but its actual model is Smooth Player Animations'
final NpcPlayerModel subclass. All six leg rotation components remain zero
after rendering. This is real client evidence, not a compilation inference.

The installed Smooth JAR is409,534 bytes, mod version1.1.0+1.21.1, SHA256
`81f0486a5bce113072c248922834166882f6c0b67e0b9d4558a0507ce1ad4d67`.
Its exact bytecode shows:

1. NpcPlayerModel.setupAnim calls PlayerModel.setupAnim, including our old TAIL.
2. It then calls EasyNpcCompat.poseShadow.
3. That pass resets model parts and applies a shadow player's animation to the
   head, arms, legs and body, overwriting the preceding seat/sip pose.

This is a later overwrite. The actual entity passed to our hooks is the NPC;
there is no missing NPC-resolution bridge or PlayerModel HEAD cancellation.

## Narrow correction

A client-only @Pseudo mixin targets precisely
`com.huaxiaosheng.smoothplayeranimations.anim.NpcPlayerModel`. Its exact
setupAnim TAIL invokes the existing seatedPose and native-DRINK sip functions
after Smooth's shadow pass. Those functions still require the local tavern skin
and actual native seat/use state. Players and other NPCs retain their existing
behavior. Smooth's normal walking and idle pass still runs.

The existing vanilla PlayerModel seat/sip hooks defer only for this exact final
subclass, so a sip is blended once. Other PlayerModel users retain the earlier
hooks. The optional target has no direct foreign Java type dependency; it can
be absent without requiring Smooth on the server or a different client.

No entity, inventory, hand-item, server movement or playback state is written
by this correction. It adds no proxy matching, reflection, ThreadLocal or render
context framework. The combined candidate also contains the reviewed native
chair-exit guard documented in SAFE-DISMOUNT-0111.md.

## Evidence and remaining acceptance

The complete candidate compiles against Java21 and the pinned APIs. All four
existing Java suites pass, including45,000 synthetic policy transitions, native
A* on a synthetic floor, fake recovery-window lifecycle tests and native NBT
admission tests. The separate14-scenario dismount fixture and two focused
Python roster/dashboard tests pass. Roster and all45 skin payloads are unchanged.
These checks do not prove that the new optional mixin applies in the real game.

The next actual client trial must verify the new hook's application, bent legs
and appropriate cushion height in a side-on framebuffer, clothing alignment,
native DRINK hand motion, and blocked/clear chair exits. Native instrument arm
poses, audible playback and two-client synchronization remain separate checks;
no instrument-animation correction is included here. The QA9 snapshot's Arlo
frame had empty hands and no existing melody progress, so it was not a music
test. Installed0.1.10 and the saved396 checkpoint remain retained for comparison.

Private source proof and the sealed QA snapshot are in
`D:\A World for Two\staging\drowned-rose-source-20261029\pose-0111-review`.
PINNED-SMOOTH-BYTECODE.txt SHA256:
`ead31364a646211c2d3d92878a48480b9e93e39ac98269fdceda90cbad486f68`.
QA snapshot SHA256:
`c38495723fa469252948eeacff4fbab6d8a8520742a5c9b8464a2fa1d9e1b835`.
