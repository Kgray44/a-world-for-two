# Native drink-frame capture — private QA 0.1.10

This isolated successor copies the frozen QA 0.1.9 source. It does not install a
runtime artifact. The existing capture, map, pose and NPC-snapshot actions remain
unchanged; the new action is `capture-on-native-drink`.

Use the existing owned-instance authorization and exact loopback staging server.
An example request, with the real current UUID and camera/target coordinates, is:

```json
{
  "id": "native-mid-drink-01",
  "nonce": "CURRENT EXISTING AUTHORIZATION NONCE",
  "action": "capture-on-native-drink",
  "uuid": "ACTUAL NPC UUID",
  "expected_position": [1300, 65, -1280],
  "expected_look_at": [1302, 65, -1281],
  "timeout_seconds": 60
}
```

Only one target is accepted. There are at most two observations per launch,
each lasting 1–60 seconds. Existing owner/account/session/nonce/expiry/server and
closed-screen guards remain; the new pending request rechecks its exact request
bytes and authorization every frame. It requires native camera/target chunk
neighborhoods, the expected player position, and the named existing NPC near the
expected target. No chunks or entities are requested or forced to render.

After **30 consecutive ready frames before arming**, the observer looks for an
actual rendered EasyNPC using its native `DRINK` item with **elapsed use ticks ≥8
and remaining ticks >0**. It captures the first qualifying native frame at that
frame's `RenderFrameEvent.Post`. There is no extra 30-frame wait after the sip
starts, no timer-created animation, and no change to items, models, AI, movement,
inventories, accounts or sound.

The real PNG and a create-once SHA256-sealed JSON receipt record the frame,
native-use item ID/class, elapsed/remaining/duration ticks, UUID and pose/model
observations. PNG hashing runs in the existing screenshot save callback rather
than blocking the render thread. Post-event model fields may be restored; the
actual PNG still requires visual review for cup-to-mouth alignment. No heard
audio, multiplayer, performance or gameplay acceptance follows from compilation.

Build only after Root's client has closed and the bounded storage check passes:

```powershell
python -B proposals/qa-native-drink-capture/build.py --home 'D:\A World for Two' --npc-api-directory 'D:\A World for Two\staging\world-tests\20261027T053650Z-artistic\server\mods'
```

This helper remains release-excluded. Root owns installation and native capture.
