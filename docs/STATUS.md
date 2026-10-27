# Build and acceptance status

**2026-10-27 UTC · release target 0.1.0-candidate.31**

The pack and rebuilt settlement remain a candidate. The bridge 0.6.17 build,
publication of the new Prism
starter and the owner-authorized fresh-world handoff are in progress; none is
recorded as complete at this checkpoint. The earlier town failed KG and Sera's
visual review, so individually authored streets, cottages, ships, bridges, harbor
works and palace wings now replace it in staging. Actual Minecraft screenshots
guide revisions; owner artistic acceptance remains pending.

Other Create attractions still need native installation or commissioning, and
complete multiplayer, performance and addendum acceptance remain open. Technical
receipts qualify only the specific checks they record.

## Current build

| Component | Current selection |
| --- | --- |
| Minecraft / loader / Java | 1.21.1 / NeoForge 21.1.262 / Java 21 |
| Enabled mods | 197 total; 191 client, 164 server, with shared mods on both sides |
| Optional fallback | Essential disabled; 198 mod records including it |
| Graphics | Eight shaders and one resource pack |
| Client heap | KG: 6 GiB; Sera: conservative 4 GiB |
| Owned helpers | Control Bridge 0.6.17 build target; client Presentation 0.2.2 |
| Catalog | 207 file records; all 223 requested candidates retained |
| Distant terrain | Distant Horizons + SeedGen; Voxy/Roxy excluded |

Exact versions, sides and hashes are in [the current lock](../catalog/lock.json).
The lock is updated when the candidate.31 build is finalized; its current version
is authoritative for completed artifacts. The latest full local run passed
**319 Python tests in 60.749 seconds**, 207-entry Packwiz validation and four Node
session tests. Final candidate.31 CI and runtime acceptance remain separate.
Source checks are separate from native gameplay and release acceptance.
[Compatibility](COMPATIBILITY.md) retains unresolved alternatives and
feature-specific runtime gates.

Candidate.27's harbor inspection failed on the dedicated server because reflective
field enumeration resolved a client-only camera type. Bridge 0.6.17 retains direct
MethodHandles access for that specific inspection; its native dedicated-server
probe and candidate.31 runtime acceptance remain pending. The failed receipt is
preserved.

Tectonic retains vertical scale 1.4 and elevation boost 0.1 within Minecraft's
existing −64..319 build range. The owner authorized discarding the rejected
world's player changes and starting fresh; final official-save handoff is pending
here. Verified checkpoints, failed receipts and unique recovery material remain
preserved.

## Rebuilt settlement and native review

The new staging world contains Signal Lane's winding waterfront street, the
Rose & Lantern cottage court, Bramble Lane's craft shops, harbor approaches,
an original furnished sailing ship, Rosewater palace wings and two river crossings.
Interiors and streets received successive furnishing, lighting, plant,
shop-display and circulation passes based on actual eye-level game captures.

The final-art capture batch began around 09:50 UTC. Reviewed craft-lane and
throne-hall frames are actual native game output. This is work in progress visual
evidence, not owner approval or a promise that every district and camera angle
passes. See [the recovery record](ARTISTIC-RECOVERY.md),
[landmark prototypes](ARTISTIC-LANDMARK-PROTOTYPES.md), [street](ARTISTIC-STREET-PROTOTYPE.md),
[cottages](ARTISTIC-COTTAGE-COURT.md), [craft lane](ARTISTIC-CRAFT-LANE.md)
and [grounds](ARTISTIC-CONNECTING-GROUNDS.md).

The rebuilt bascule's full native physical verification passed after a planter
correction. A growable azalea had formed an oak trunk and leaves in the bridge
clearance; a finite repair replaced six active planted pairs with native potted
bushes on stone plinths. Every removed tree cell was proven air in a verified
preconstruction backup. Other trees, architecture and the eight existing control
block entities were preserved. Full 3/9 material checks and five focused
correction regressions passed.

Following an actual restart, two complete button/radio-driven 55° opening and
closing cycles succeeded at **09:46:53 UTC**, with all temporary tickets released.
Receipt: `2fae1ceb-ae51-461b-82b2-2822e8ce3717`, bridge **0.6.12**. These are actual
artistic-staging mechanism results; they do not establish candidate.31
native acceptance or safe passage of every vessel.

The large sailing ship remains a structural build. Watermill, rail, Hypertube,
pneumatic logistics and tender-hoist demonstrations have separate source/staging
contracts and still need the appropriate installation, interaction, restart and
safety checks. See [Create attractions](SETTLEMENT-ATTRACTIONS.md),
[maritime attractions](MARITIME-ATTRACTIONS.md) and [showcase gaps](SHOWCASE-COVERAGE.md).
Stocked items and decorative machines do not establish operating gameplay loops.

Earlier rejected-world construction counts and receipts are historical only,
retained in [the construction record](../evidence/runtime/permanent-settlement-construction.json)
and [candidate.23 mechanism record](../evidence/runtime/drawbridge-candidate.23.json).
They are not the new staging inventory or a visual-quality score.

## Dragon, client and cinematic checks

The dragon repair delivered **seven species and 75 variants** during an actual
candidate.25 dedicated-client login. Later actual candidate.26 screenshots and
client resource witnesses show distinct **black, nebula and leucistic Night Fury
base textures**, with no texture aliases or entity/variant writes. The earlier
purple/black base-texture failure is corrected for these observed cases. Optional
upstream glow masks that are absent remain a separate limit; other species,
adult/baby layers, saddles/tails, resource reloads and reconnects are not blanket
qualified. See [the diagnosis](DRAGON-RENDER-REPAIR.md) and
[actual capture evidence](../evidence/runtime/artistic-recovery-detail-20261027.json).

Presentation 0.2.2 contains the narrow Small Ships remote-config lifecycle repair.
Its focused actual-pinned regression harness passed; full current-client reconnect
and rendering acceptance remain separate. Earlier gameplay confirmed the intro
returned control, furnace scenes worked, and a newly placed vanilla crafting table
animated with responsive input. These observations retain their earlier scope.

Seven earlier settlement scenes passed the pinned Lumiera parser/NBT probe and
were present in the earlier server's actual registry. Those coordinates refer to
the previous settlement; fresh-world scene geometry, delivery, skip/return and
complete castle-to-offshore coverage require review. SeedGen LODs are not assumed
to contain newly built structures. See [cinematic constraints](SETTLEMENT-CINEMATIC.md).

Actual candidate.29 and candidate.30 logins still produced different strict
SeedGen fingerprints despite matching cinematic data. Tectonic's built-in pack
was already present: the actual gap is priority. The client opened it before raw
mod roots, allowing Terralith to override 16 overlapping resources; the server
selected Tectonic after mod data. Candidate.31 reuses and moves that exact existing
pack after raw roots and before explicit extras, preserving native metadata,
overlays and fingerprint code. Actual candidate.31 paired agreement remains
pending. See [the corrected diagnosis and limits](SEEDGEN-RUNTIME-GAP.md).

Eight shaders are pinned, including Kappa and Bliss. Chocapic remains deferred at
the owner's request. Switching shaders caused a real client freeze/disconnection
during earlier play, so preset quality and reload responsiveness remain active
limits. See [shader choices](SHADERS.md).

## Measured gameplay and performance limits

These measurements belong to the earlier candidate.23 official world. They are
not benchmarks of the rebuilt town or candidate.31.

| Five-minute session | Server TPS / tick time | Client and memory observations |
| --- | --- | --- |
| KG, 31 samples | Median 20.00 TPS; 12.82 ms/tick; sampled-mean p95 22.16 ms/tick | Complementary Reimagined: 18–33 FPS, median 26; server RSS 3.55 GiB; client RSS 8.71 GiB; available host RAM 0.36–1.63 GiB |
| KG + Sera, 26 fresh two-player samples | Median 20.00 TPS; 11.74 ms/tick; sampled-mean p95 19.98 ms/tick | KG's 19 focused samples: 14–27 FPS, median 22; server RSS 5.42 GiB; median available host RAM 0.50 GiB; Sera's client uninstrumented |

The two-player recording excluded four stale snapshots and kept the final
Sera-only sample separate. KG's later shader reload timed out, so it is not
uninterrupted multiplayer acceptance. Exact scope is in the
[one-player](../evidence/runtime/owner-play-candidate.23.json) and
[two-player](../evidence/runtime/two-player-session-candidate.23.json) records.

Fast travel still exposed slow terrain arrival. The idle investigation reproduced
1,682 chunk holders with nine deliberately forced chunks, then returned to 841
after removal and five minutes idle: 49 full, 25 block-ticking and nine
entity-ticking chunks, zero forced and one spawn ticket. Holders are not the fully
simulated count; no persistent loading leak was proved. SeedGen's earlier native
server fingerprint passed, while current client agreement, generation fidelity
and Xaero/MapHorizons population remain unverified.

Control Room has source support for a bounded background integrity scan instead
of hashing every installed mod on each overview poll; strict startup/deploy/health
verification remains. Live reload/latency measurements require their own evidence.
Playit service stop/start and actual remote login were observed earlier; complete
current-world remote gameplay acceptance remains separate.

## Distribution and remaining acceptance

The planned **candidate.31 Prism ZIP** is not yet recorded as published or
freshly imported. Its [release page](https://github.com/Kgray44/a-world-for-two/releases/tag/awft-0.1.0-candidate.31)
and [direct ZIP link](https://github.com/Kgray44/a-world-for-two/releases/download/awft-0.1.0-candidate.31/A-World-for-Two-0.1.0-candidate.31-Prism.zip)
are prepared destinations; publication and the exact public checksum remain
pending. Do not treat the older candidate.23 starter as the matching release.

Historical candidate.23 Prism-r2 public download hashes, fresh Packwiz installation
and Sera's reported Prism import/actual login remain recorded in
[publication evidence](../evidence/runtime/public-release-candidate.23.json).
Those results do not qualify the new archive. Candidate.31 still needs exact
public-asset verification and a fresh install/import check; accounts, worlds,
backups and caches remain excluded from the starter. See [release procedure](RELEASING.md).

Before a qualified stable release: finish the fresh-world handoff and restart
checks, current artifact/Prism verification, Create commissioning, multiplayer
feature coverage, dragon/shader/cinematic review, terrain-arrival measurements and
owner visual assessment. Cleanup follows a working, accepted build and preserves
useful recovery snapshots and failed receipts. Local writers reserve 30 GiB
separately on C: and D:; this monitoring rule does not constrain external
applications or already-running writers.
