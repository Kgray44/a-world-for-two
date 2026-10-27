# Build and acceptance status

Candidate **0.1.0-candidate.23**, 2026-10-27 UTC checkpoint. The permanent settlement
expansions are installed and have native block/inventory verification receipts.
Functional commissioning, graphical refinement and release qualification continue.

## Current build

Minecraft 1.21.1, NeoForge 21.1.262, Java 21; bridge **0.6.9**. There are **197 enabled
top-level mod JARs**, **eight shader packs** and **one resource pack**. The lock has
207 file records, including the optional Essential client fallback disabled by
default. The compatibility inventory retains all **223 requested candidates**.

Pack SHA-256:
`9631a680f572fe7cae44cb2575f7c3ced3910611819ab948c02406e6e0700e11`.
Exact component pins and sides are in [the lock](../catalog/lock.json).

The published exporter/source checkpoint passed **131 Python tests in GitHub CI**,
**four JavaScript session tests**, JavaScript syntax and Packwiz integrity for
207 entries. The later Control Room cache source checkpoint passed **157 Python
tests in GitHub CI**, plus the same JavaScript and Packwiz checks. Further attraction
source work has its own local checks. These
source checks are separate from graphics, gameplay and remote acceptance.

The official save remains the existing permanent world. It was not regenerated or
replaced by a test save. Tectonic uses vertical scale 1.4 and elevation boost 0.1
within the existing −64..319 build range. Candidate.23 normalizes Tectonic file
line endings to the existing runtime bytes; its generation settings are unchanged.
Verified backups, unique saves and failed receipts remain preserved.

## What is actually built

| Area | Planned placements | Native result |
| --- | ---: | --- |
| Original plaza, cottage, gardens, barn, tree and harbor core | 96,019 | Earlier block/state/inventory verification passed |
| Lanternwater pirate quarter | 104,341 | Earlier block/state/inventory verification passed |
| River drawbridge structure | 12,317 | Closed-state verification and two native 55° cycles passed; saved programs verified |
| South-bank Bramble Steps and Willow Crown | 139,635 | Placed; 19 furnished buildings, 21 landmarks; verification passed |
| Expanded Rosewater Castle | 134,821 | Placed; 40 named rooms; verification passed |
| Offshore Rosewater Resolute | 23,735 | Placed; verification passed |
| Docked Amberwake | 17,323 | Placed; verification passed |
| Docked Nightingale's Debt | 13,281 | Placed; verification passed |
| Docked Sea Lavender | 12,476 | Placed; verification passed |
| Harbor approaches, two small cutters and service boats | 4,148 | Placed; block/inventory verification passed; four native boat-placement commands completed |

The newer expansion checks ran on candidate.20 with zero reported differences.
Earlier core and port receipts are retained. Castle masonry and connecting public
paths have explicit reviewed adaptations; preserved inventories are not reset.
Counts include clearance air and overlapping deltas, so they are not a count of
unique solid blocks or an artistic-quality score. Exact plan hashes, timings and
sanitized receipts are in [the construction record](../evidence/runtime/permanent-settlement-construction.json).

The south-bank source plan checks 28 connected routes and 2,353 walking columns.
The castle source checks 50 recorded routes. Ship plans check named-room corridor
reachability, hull sealing and surveyed depth. These are geometry checks, followed
by actual block verification; real walking, native collision shapes, fluid behavior
and mod interactions still need review.

The four large ships are distinct original structural builds with furnished
belowdecks: the flagship has partly unfurled drying sails, Amberwake and
Nightingale's Debt have furled sails, and Sea Lavender has loosened drying canvas.
They are not assembled giant physics ships. The isolated tender hoist still needs
glue/motion, safe boat retention and restart commissioning. Actual tender boarding,
gangway walking and wet-hull checks remain pending. See [harbor design](GRAND-HARBOR-SHIPS-DESIGN.md),
[castle design](ROSEWATER-CASTLE-DESIGN.md) and [south-bank design](SOUTH-BANK-DESIGN.md).

The drawbridge's real water wheels measured 8 RPM, with 2 RPM at both sequencers
and no overstress. Both bank buttons and the native radio network completed two
full opposed 55° opening/closing cycles. All 11 temporary simulation tickets were
released. Exact closed-state verification checked 12,317 positions with zero
differences. An independent verified stopped-save audit confirmed both 55°
reversible programs, closed/disassembled bearings and radio/power data persisted.
Direct post-restart cycles and fully rigged vessel passage remain separate;
automated mechanism tests are paused while the owner explores. Failed attempts
remain preserved. See [the native checkpoint](../evidence/runtime/drawbridge-candidate.23.json).

The candidate.22 restart recovery attempt stopped before sending an input because
the saved bearings had no live contraption attachment. Its failed receipt is
preserved, with zero temporary tickets remaining. Both actual contraption entities
and their 523/508-block structures were present in the verified pre-restart backup.

Candidate.23 uses bridge 0.6.9 and opposed 55° targets. Before an input, it requires
native entity loading and ticking, completed kinetic initialization, actual live
controller attachment, nonzero finite input RPM and no overstress. Failed ticket
cleanup retains the exact handles and blocks further admission until an explicit
cleanup succeeds. **48 regression checks passed against the actual built JAR's
phase, power, stress, simulation and attachment predicates.** Subsequent actual
Minecraft results established native attachment readiness, safe 90° recovery,
55° cycles and button/radio operation. The earlier dry-channel expectation failed
at 80 cells: all were naturally flowing water within the two authored wheel
channels. A finite verify-only derivative corrected those expectations; it found
no missing solid blocks or orientation differences and passed all 12,317 checks.
The original plan and failed receipt remain preserved. That derivative must never
be placed. Java predicate checks remain separate from the native results.

The five-district architectural detail pass added 1,593 changes in 165 feature
groups. Native before/place/after checks passed, and an independent stopped-backup
audit matched every final position with zero identity or orientation differences.
This verifies saved construction, not 3D beauty. A bounded, dry watermill,
processing line, Hypertube and passenger railway plan is staged with 16,843 targets,
14 block-entity tags and exact saved before states. A separate maritime proposal
contains 154 blocks, one proposed Small Ships cog, a shallow clue/reward cache and
the tender lift's complete body/sweep and spatial entity admission contracts.
Neither addition has been installed or commissioned. Their mod installation and
source checks do not establish operating attractions. See [the engineering hub](SETTLEMENT-ATTRACTIONS.md)
and [maritime proposal](MARITIME-ATTRACTIONS.md).

The [per-mod showcase audit](SHOWCASE-COVERAGE.md) binds all 197 enabled JARs,
223 requests and 16 exact native construction sources. It finds 30 mods with
historical mod-owned blocks and 13 with supplied items. Of 95 gameplay-content
mods, 63 have no mod-owned block/item/entity evidence in these construction plans.
This is not a live census or proof that naturally generated wildlife/content is
absent. Envelope, framed construction, wildlife/fairies, zipline, wagon and actual
sailing/physics demonstrations remain explicit gaps; scenery and stocked items
do not qualify those gameplay loops.

Construction is budgeted, but a single engine action can exceed the soft work
slice: south-bank placement recorded a 4,155 ms maximum slice while loading/placing.
This is a construction observation, not a steady-state MSPT benchmark. Expanded
settlement idle and nearby-player performance still need measurement.

## Cinematics and visual review

Seven new settlement scenes passed the pinned Lumiera JSON parser and native NBT
roundtrip probe. The prepared first-join scene is 24 seconds around the actual
core; castle, port and four ships have separate local tours. The scene ZIP is now
installed in the official save's datapacks directory. **The restarted server's
actual Lumiera registry contains all seven scenes plus the earlier intro.**
The verified stopped backup contains the exact 14,942-byte scene ZIP in the
correct save. Delivery, real client rendering and
skip/return behavior for these scenes remain pending.

The refreshed geometry manifest binds all ten verified construction sources,
including the final 4,148-position harbor access and placed flagship. Its ZIP is
byte-identical to the data checked by the exact Lumiera parser/NBT probe at
02:03:40 UTC, so that format evidence remains applicable. No new JVM probe or
game rendering is claimed by the geometry-provenance correction.

A core camera packet does not prove that the distant castle and offshore ships
are present on the client's screen. Full castle-to-offshore first-join coverage
needs a verified terrain-delivery solution and actual rendering review. Distant
Horizons/SeedGen LODs are not assumed to contain newly built structures. See the
[cinematic coverage contract](SETTLEMENT-CINEMATIC.md).

KG and Sera are playing the official world. Automated native construction and
mechanism tests remain paused during their session. Intended-shader street,
interior, harbor, sunset and night screenshots and a complete visual refinement
pass are pending. Block counts do not establish cinematic beauty.

The exact bridge 0.6.7 JAR passed a separate headless Windows regression: an ordinary
reader denied mutable status replacement, progress returned an AccessDenied warning,
the old view stayed intact, and an immutable terminal JSON plus SHA sidecar was
published and verified. That proves file-publication resilience, not a Minecraft
mechanism or multiplayer pass.

## Earlier observed gameplay and remaining integration limits

- Earlier licensed one-player tests confirmed the intro returned control and the
  furnace scene worked. The owner confirmed candidate.12's newly placed vanilla
  crafting table animated with responsive chat/search. These observations do not
  qualify every new scene, existing converted workstation or current candidate.
- Earlier gameplay commonly measured about 20 TPS, 7–14 ms/tick and focused
  59–60 FPS. Fast-travel terrain arrival remained slow; some samples had under
  1 GiB free system RAM. No new full-settlement performance improvement is claimed.
- A new five-minute official-world session with KG connected and both server and
  client running recorded 31 samples: median 20.00 TPS, median 12.82 ms/tick and
  22.16 ms/tick at the 95th percentile of sampled means. Server RSS median was
  3.55 GiB and heap use 2.11 GiB. The Complementary Reimagined client measured
  18–33 FPS (median 26), RSS 8.71 GiB and a 6 GiB maximum Java heap. Available host
  RAM ranged 0.36–1.63 GiB. These are current observations, not a performance
  improvement or a two-player benchmark. Shader/client cost still needs tuning.
  See [the measured session](../evidence/runtime/owner-play-candidate.23.json).
- Sera's actual login and simultaneous official-world play with KG are now observed.
  A later five-minute recording contains 31 observations: 26 fresh two-player
  samples, four stale snapshots excluded, and one final Sera-only sample. Fresh
  two-player samples measured median 20.00 TPS, 11.74 ms/tick, 19.98 ms/tick at the
  95th percentile of sampled means, server RSS 5.42 GiB and 0.50 GiB available host
  RAM. KG's 19 focused game-screen samples measured 14–27 FPS (median 22); menu
  samples are separate and Sera's client is not instrumented. KG's shader reload
  subsequently timed out, so this is not uninterrupted multiplayer acceptance.
  See [the two-player record](../evidence/runtime/two-player-session-candidate.23.json).
- The idle investigation reproduced 1,682 chunk holders with nine deliberately
  forced chunks, then returned to 841 after removal and five minutes idle. Baseline
  was 49 full, 25 block-ticking, nine entity-ticking, zero forced and one spawn
  ticket. Holders are not the fully simulated count; no persistent leak was proved.
- SeedGen's dedicated-server fingerprint passed with actual modded registries on
  candidate.17. Fresh client agreement, active generation fidelity and SeedGen
  terrain appearing on Xaero through MapHorizons remain unverified.
- Playit service stop/start retained the existing account and tunnel. Control Room
  provides player permissions, whitelist, coordinates, Atlas, background storage
  scans and session-token recovery. A source fix removes whole-mod hashing from
  every overview request and retains strict startup/deploy/health checks; it needs
  the next safe Control Room restart and a live latency measurement. No supported
  dashboard-only Python reload currently preserves Java's console ownership.
  Remote login is observed; complete two-player feature acceptance remains separate.
- Eight shaders are pinned, including Kappa and Bliss. Chocapic is deferred at the
  owner's request. Advanced pirate/physics experiments remain isolated.

## Distribution and remaining acceptance

The candidate.23 revision2 **Prism** starter is
[public](https://github.com/Kgray44/a-world-for-two/releases/tag/awft-0.1.0-candidate.23):
**7,072,234 bytes**, SHA-256
`9daf9b23ab77490f1d8ac3399d4146165248d4e9d10566b434569eba87fca218`.
It configures a 6 GiB client heap and opens the normal multiplayer list from
**Join Our World**, with separate public and KG-local entries. Packaging and native
server-list, archive integrity, bootstrap chain and original artwork identity checks
passed. The exact revision2 public ZIP and checksum passed unauthenticated download
verification. A fresh public Packwiz installation passed: 199 downloads plus the
single author-permitted bundled pirate JAR, all 200 client artifacts and 76 static
configurations matched, with zero missing/changed files or server-only leakage.
The headless installer enabled optional Essential; the normal GUI-default set has
199 artifacts with Essential off. Native Prism import and startup from the exact
public starter remain separate. KG's existing owned client matched all current client artifact pins and
joined the official server; its local direct-connect menu override and already
installed files do not establish a fresh public-starter import.
See [the release process](RELEASING.md).

The compatibility prerelease is public at
[compat-0.1.0](https://github.com/Kgray44/a-world-for-two/releases/tag/compat-0.1.0).
All 13 assets passed independent unauthenticated public size/hash checks, including
the four exact custom-artifact URLs used by Packwiz. Source CI passed after its
test fixture was made independent of ignored private receipts. The immutable
candidate.23 source tag is retained; publication caught five obsolete metadata
records outside the active index. Their explicit, hash-bound publication exclusions
now pass 14 publisher tests; the packaged tree contains only indexed files and
manifests, with omission proofs retained. Pages deployment passed; the immutable
public manifest and index match their exact hashes. The stable root manifest
remains absent, and no active mod pins changed. The public game tunnel also
answered a Minecraft status ping from the host. Sera then logged in and played
alongside KG, as recorded separately; her exact public-starter import and client
file hashes were not independently inspected. See [the publication evidence](../evidence/runtime/public-release-candidate.23.json)
and [later two-player observations](../evidence/runtime/two-player-session-candidate.23.json).

Finish direct post-restart drawbridge cycles, hoist and other transport/logistics commissioning, current-world
restart and restore checks, complete mod-feature coverage, multiplayer feature tests,
shader review, terrain-arrival measurements and full visual refinement. Source,
Pages and public release artifacts are now published and checked; native Prism
and full gameplay acceptance are still required before a qualified stable release.

Cleanup remains conditional on a working, accepted build. Useful recovery snapshots,
unique worlds and failed receipts stay preserved. Local writers reserve 30 GiB
separately on C: and D:. This is a monitoring instruction, not an operating-system
quota; external applications and already-running writers are outside its coverage.
