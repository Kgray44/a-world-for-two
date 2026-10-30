# 0.1.13 candidate: retain existing micro-movements after Smooth

The existing breath/shift/glance/settle/gesture math and eligibility guards are
unchanged. Its early EasyNPC setup-end hook precedes Smooth's shadow-pose reset,
so the exact Smooth primary model now defers that pass until its final TAIL.
Final order is native seated pose, eligible existing micro-motion, native
instrument pose, then native-use sip. No new gesture, keyframe or animation
framework is added.

The early static hook receives an NPC and model manager, not the concrete model.
A read-only public renderer lookup matches both the exact final NpcPlayerModel
class name and the same model-manager object. Only that primary pass defers;
ordinary models, other manager passes and other NPC skins retain their earlier
behavior. The lookup neither constructs a renderer nor stores render context.

The original apply method now returns whether it actually changed parts. After
a successful final pass, jacket and sleeves copy their respective upper-body
parts; the existing function already copies head to hat. This explicit clothing
sync is necessary because pinned EasyNPC7.17.1 syncModelParts immediately returns
for VANILLA. Its other branches only adjust outer visibility/hat copying and do
not reset inner-part positions. The existing seated height and leg rotations
therefore remain intact; held items, active use, swings, walking, unsupported
mounts and custom animations retain the original exclusion guards.

Frozen0.1.12 is retained. Server behavior, native dismount, persistent seats,
roster,45 skins, ledger and instrument/sip helpers remain unchanged. TavernMod's
only source change is the reported adapter version. No Native/UI/world operation,
resident recovery or installation is performed by this source work.

Actual final-hook application and visible subtle motion still need the next
matched client trial. Compilation and simulated model tests are not framebuffer,
audio, multiplayer or performance acceptance.
