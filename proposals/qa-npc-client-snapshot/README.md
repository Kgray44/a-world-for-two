# Bounded NPC client snapshot — private QA helper

This is an isolated extension of the existing, release-excluded Settlement QA
helper. The active helper and runtime are not changed by this proposal or build.
`BASELINE.json` records the actual installed QA 0.1.8 artifact and copied source.

The only new action is `npc-client-snapshot`. It runs after the existing owned
instance, nonce, expiry, KG account/player, ready-world, closed-screen and exact
loopback staging-server checks. A request supplies one to five distinct UUIDs:

```json
{
  "id": "tavern-seat-music-01",
  "nonce": "CURRENT EXISTING AUTHORIZATION NONCE",
  "action": "npc-client-snapshot",
  "uuids": ["ACTUAL NPC UUID"]
}
```

The existing `awft-qa` request/receipt paths apply. Receipts are create-once JSON
and SHA256 `.complete` seals, bounded to 64 KiB. At most 16 snapshots are allowed
per launch. One request observes at least one subsequent render frame and expires
after ten seconds; failed requests are terminal, with no automatic retry.

The snapshot searches at most 4,096 **existing** client entities. It records NPC
and backing-Mob identity, vehicle/passenger state, position and camera distance,
existing held/use-item state, only the named instrument components, skin type and
resource texture, and the pinned EasyNPC model-pose getters. It excludes skin URLs,
external skin UUIDs, credentials, entity NBT and inventories beyond the held items.

An observer records the first actual `RenderLivingEvent.Post` for each requested
entity while authorized. It records renderer/model classes and humanoid part
pivots/angles without writing them or forcing rendering. **Post-event fields can
already have been restored by the renderer. They are not proof of pixels drawn.**
An entity that was not rendered is explicitly reported as unobserved.

Music inspection reads only an existing entry from the exact pinned
`MelodyProgressManager.progress` map. It never calls `getProgress`, `getMelody`,
`tick`, `play`, synchronization, or a sound-producing method. It records existing
time, last-note age, track indices, animation values, native audibility predicate,
and configured master/neutral volumes. This does not prove audible hardware output.

Build using the existing Java21 QA builder flow, with only explicit compile-only
EasyNPC 7.17.1 and Immersive Melodies 0.8.0 API pins added:

```powershell
python -B proposals/qa-npc-client-snapshot/build.py --home 'D:\A World for Two' --npc-api-directory 'D:\A World for Two\staging\world-tests\20261027T053650Z-artistic\server\mods'
```

No dependency JAR is packaged. No installation, world write, client launch or
native acceptance occurs in the builder. Existing map-readiness fixtures remain
the original 23 checks, with their evidence limit unchanged.

Root subsequently installed QA 0.1.9 and obtained actual client observations on
2026-10-30. [Native evidence](NATIVE-EVIDENCE.md) records the four musicians'
existing active playback/note state and Arlo's real seat attachment with standing
leg angles. This is not proof of heard audio or final visual acceptance. Root
owns installation and in-game verification; this proposal does not change the
active helper or runtime itself.
