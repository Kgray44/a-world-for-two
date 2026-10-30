# Native drink-frame capture owner-bound repair — private QA 0.1.11

This isolated successor preserves frozen QA 0.1.10. It fixes the actual native
drink request failure: its blanket 4 KiB reader rejected the legitimate 38,452-byte
`awft-owned.json` marker. The unchanged main QA helper limits authorization and
request files to 4 KiB but has no explicit owner-marker byte limit. This repair
uses a separate finite 64 KiB owner-marker limit and retains the 4 KiB limit for
authorization and requests. All owner format, nonce, session, server, expiry,
request schema, position, rendering and native-use gates remain unchanged.

The actual file reader checks regular files without following links, reads at
most the relevant limit plus one byte, and rejects malformed UTF-8. The old QA
actions and their helper classes remain unchanged. No runtime artifact is
installed by this proposal; `capture-on-native-drink` is the same existing action.

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
python -B proposals/qa-native-drink-owner-bound/build.py --home 'D:\A World for Two' --npc-api-directory 'D:\A World for Two\staging\world-tests\20261027T053650Z-artistic\server\mods'
```

The build runs the actual reader's 38,452-byte regression fixture, inclusive and
over-limit boundaries, unchanged small-file limits, byte versus character limits,
strict UTF-8, missing/directory inputs and no-link checks where the host permits
creating a test symlink. It also retains all 23 existing map-readiness fixtures.
These are filesystem/source fixtures; no game, Native command, or image fallback
is used. Native drink capture still requires a real client run and visual review.

This helper remains release-excluded. Root owns installation and native capture.
