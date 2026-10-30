# QA 0.1.9 actual client observations

Root installed the private QA helper; these are observations from that runtime,
not results of the source builder. The helper artifact SHA256 is
`c3d90ee6dee6003dee7618bb9e98e7161f9eb6d225857a33c21ff44c4bda01a6`.

## Four musicians: existing native playback state

At **2026-10-30 08:01:59 UTC**, the snapshot observed Cass Flint (vielle), Penny
Marl (flute), Oskar Bell (lute), and Hedda Stern (tiny drum). Each held the actual
Immersive Melodies instrument with `PLAYING=true` and the Monkey Island MIDI.
Each already had a native `MelodyProgress` entry at 3,550 ms, `isPlaying=true`,
and a last-note age of 40 ms. No progress entry was created by the probe.

All four were 4.9–6.3 blocks from the camera. The native audibility predicate was
true, with master volume 0.3165563, neutral volume 1.0, and maximum audible distance
48. Empty explicit track-component lists do not mean there were no playing notes;
the probe reports track indices only for that explicit list. Instrument items
need not use the vanilla use-item animation.

The actual renderer was EasyNPC's `standard.PlayerRenderer`; the model was
Smooth Player Animations' `NpcPlayerModel`. Observed post-render arm poses were
`EMPTY`. **Native playback and recent-note state are verified; audible output was
not recorded or listened to.** Two-client synchronization, visible instrument
performance, and performance acceptance remain unverified by this receipt.

Receipt: `D:/A World for Two/staging/world-tests/20261027T053650Z-artistic/staging/bridge55-QA9-ROOT-native-review/ACTUAL-MUSIC-CLIENT-SNAPSHOT.json`

SHA256: `38fe935ff2ef459bdb2a02c96d0fb4f97e380ac9df327618e2a8fcc6254f01f0`.

## Arlo: actual mounted state and pose overwrite

At **2026-10-30 07:50:30 UTC**, Arlo Ink was genuinely a passenger of
`awft_tavern:persistent_seat` (`worldfortwo.tavern.ManagedSeat`). The observed
Smooth model had `riding=true`, but both legs had zero rotation on all axes.
This rules out missing seat attachment as the cause of this observation.

Pinned Smooth 1.1.0 bytecode calls `PlayerModel.setupAnim` and then
`EasyNpcCompat.poseShadow`. Thus an earlier PlayerModel-tail pose can be
overwritten afterward. Tavern 0.1.11's proposed exact Smooth-tail hook addresses
that ordering for seating and sipping. Its source presence is not runtime visual
acceptance. Other requested NPCs that were not rendered have no observed pose.

Receipt: `D:/A World for Two/instances/AWFT_Check_20261026_214756/.minecraft/awft-qa/qa9-arlo-seat-snapshot-0750.json`

SHA256: `c38495723fa469252948eeacff4fbab6d8a8520742a5c9b8464a2fa1d9e1b835`.

Post-render model fields may already have been restored. They are state evidence,
not framebuffer proof. Real chair side-view screenshots, drinking and music
observations, clear/occupied native dismounts, and restart checks remain Root's
runtime acceptance work.
