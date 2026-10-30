# Client-only motion and riding-pose integration

The combined0.1.6 correction additionally includes the supplied PlayerModel
TAIL hook. Easy NPC can cancel the superclass vanilla HumanoidModel setup at
HEAD, bypassing native riding legs and the earlier TAIL callback. The new
client hook runs after PlayerModel's clothing copy and restores exact vanilla
riding-leg angles for actual Handcrafted Seat passengers (including the
saveable subclass), without replacing arm/head/instrument rotations. Body
lowering uses the native player versus NPC vehicle-attachment difference;
model pivots use initial values so repeated calls do not accumulate lowering.
This changes only rendered model coordinates, never the real entity position.
The native A* and managed-seat changes are in PATH-AND-SEAT-CORRECTION.md.

The master supplied the independently authored two-class patch from
`proposals/drowned-rose-motion`. Those sources and its mixin JSON are copied
unchanged into this additive component. NeoForge registers the config through
`[[mixins]]`; its only mixin is in the JSON `client` array. TavernMod does not
reference client classes. The same artifact belongs on client and server.
Dedicated-server startup now passes with fresh0.1.3 telemetry and no adapter
fault. Actual client Mixin application and visuals still need verification.

The hook injects at the return of pinned Easy NPC7.17.1's own static
`EasyNPCModel.setupAnimationEnd`, with remapping disabled for that mod method.
It selects synced local tavern skin resources, rather than unsynced tags.
Small UUID-staggered breathing, head motion, stance shifts, empty-hand gestures
and seated upper-body adjustments operate on model rotations only. Vanilla
model setup resets the model before the next render. This changes no entity
root position, paths, hitbox, reservations, legs, seat or persisted state.

Held items, active use/swings, custom poses, requested animations, airborne
nonseated entities and non-Handcrafted vehicles skip the pass. Native music
and drink poses therefore take priority. Hat/skin layers follow Easy NPC's
model synchronization. This supplies no unsupported lounging preset: proper
bar-edge leaning still requires a supported pose and surveyed body clearance.

Compilation and metadata/package inspection cannot establish that the mixin
applies successfully or looks natural. The master must check standing,
Handcrafted seated, walking, drinking and all4 instrument poses in the running
client, including consecutive renders of different NPCs. This chat uses no UI.
