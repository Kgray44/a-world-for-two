# Fleet63: two verified ships and one placed ship requiring correction

On October28,2026 at20:43-20:47EDT (October29,00:43-00:47UTC), this workstream
actually placed Reed Fin, Golden Petrel and Mercy of the Tide in the construction
save. Reed Fin and Petrel completed native settling, full-target AFTER checks and
map queuing. Mercy completed placement and its first settling partition, then
stopped at a real structural-preimage mismatch in the second partition.
**Mercy is partial, not accepted. No original ship placement was replayed.**

`H` means `D:\A World for Two\staging\world-tests\20261027T053650Z-artistic`.
The save is `H/world/RosewaterArtistic`; no configured permanent save was changed.
Together with the earlier Wren, Tern and Salt job, six new vessel structures now
exist. None of this is a sailing, walking, visual, multiplayer or owner acceptance.

## Authority

Master delegated the exclusive job after Grand's eight-building batch released.
Lease: `H/dashboard/settlement/exclusive-fleet63-three-ready-ships.json`.
Original lease SHA256 `2f100168509638f1a10d6f463a883674d289c16fa2a1f0a6979dba5a233d9664`.
Root explicitly corrected the coarse minimum Y55 toY52 to cover the already
approved full source hull/probe arrays. Corrected lease SHA256
`1e8319c10b0cfcd01badabd4e99a08b36777dd760ac65a039438c93af0dfb81e`.
Both versions are preserved. Reed was within the original box; deeper writes
waited for Root's correction. The exact source/plant scope was unchanged.

Candidate63, bridge0.6.49, Java43108/birth1793233452.202239. Bridge SHA256:
`3087e224a5d62179c76d9304c8d76c5991d4fe0fae0f647c0e91bfc65f9514cf`.
Canonical Native checkpoint remains6ad3a8; supplemental c33037 retains KG's
accepted mechanisms and the first three ships. Root held source/Git only while
Fleet owned this job. No client, runtime, configuration, quay or other lane changed.

## Actual placement results

| Vessel | Origin / rotation | Targets / new source fixtures | Outcome |
| --- | --- | --- | --- |
| Reed Fin | `(1336,63,-1044)`,0 | 549 /1 | BEFORE/support, one PLACE, normal SETTLE, AFTER and map passed |
| Golden Petrel | `(1110,63,-1360)`,1 | 26,156 /8 | BEFORE,114 approved marine cells, support, one ship PLACE, two SETTLE partitions, AFTER and map passed |
| Mercy of the Tide | `(1230,63,-1392)`,1 | 32,786 /14 | BEFORE,535 approved marine cells, support, one ship PLACE and SETTLE1 passed; SETTLE2 failed |

Only the exact649 approved marine-plant cells were replaced with water. No hard
terrain, seabed, ice, existing block entity, old inventory or original craft UUID
was cleared or rewritten. New source fixture tags were applied; Mercy's14 tags
have not yet passed the intended full AFTER inventory check.

The Native verifier checks block identity and facing/axis/half/part/type/hinge,
plus source BE existence and supplied Items. It does not compare every state
property or full arbitrary NBT. Settling changes ordinary native join shapes.
Map results mean queued native map updates, not screenshots or artistic review.

## Exact outcome receipts

Filenames below are under `H/dashboard/settlement/`, prefix
`settlement-result-`, suffix `.json`, each with a genuine matching completion marker.

| Vessel | PLACE | AFTER or failure |
| --- | --- | --- |
| Reed | `24317d9c-d68b-4ec0-b3fb-ab081dfc7b45` | AFTER `eb584a7f-d7d5-4acb-81ce-f5ea98329970` |
| Petrel | `814c2cc9-4134-4418-b331-3c4eab3e18e1` | AFTER `c61101f0-214c-49a3-8633-8ea05358c503` |
| Mercy | `d253f622-a093-44f7-93af-6943580638c2` | SETTLE1 `ecc824ec-6bd8-49ae-8f52-4e0d895a3189`; failed SETTLE2 `7a87cf41-b959-454e-8df5-0944f50b7948` |

There were20 genuine operations:19 completed and one errored. The failed terminal
has SHA256 `02290c2d78f8e21ba498811fa5068674c607544ccc82c639847380996dbc1ce7`.
It finished at00:47:23.127494700UTC, cursor2319/12,786, phase0:
`Neighbor reconciliation structural preimage differs at BlockPos{x=1241,y=56,z=-1398}`.
Its `failures=0` counter does not cancel the non-null error or failed status.
No Mercy AFTER or map was run after the error; no rollback or placement replay ran.

## Concrete unresolved defect

The intended block at `(1241,56,-1398)` is AIR, with no source BE. It is local
`(-6,-7,-11)` inside the lower ship. Below is a full dark-oak log atY55; the
neighbor atZ-1399 is a full dark-oak plank; Z-1397 is a spruce crate. Other cardinal
neighbors are intended AIR. Because AIR has no orientation properties, this is
an actual block-identity mismatch before that settle step, not merely a rope or
table join change. **The actual replacement identity is not yet observed.**
Trapped construction water is a hypothesis, not a reported fact or acceptance.

Root requested source-only diagnosis until the next empty repair window. Fleet
prepared a one-cell VERIFY-only diagnostic and did not execute it. Its actual SHA256
is `b7945a7ac8803e72cd8a3aaa693204fdc1562e6ffdee66e8aa3b9b96ab19e73e`.
An initially incorrect handoff SHA was promptly corrected; no Native command used
that incorrect hash.

Root then executed the genuine read-only diagnostic
`907dd22b-a6a9-4615-afbf-7811f4215958`. Its terminal/completion SHA256 was
independently authenticated as
`8edd9620d56dd7d938b918aaf4c79b5c69f072964df51617b98a55c3771d5bfb`.
The actual block is **`minecraft:water[level=6]`**, not intended AIR. This proves
flowing water, not whether it was trapped during construction or enters through
a current leak. Do not restore furniture, rerun the hull or accept water as AIR.

Focused source diagnosis reused the exact existing hull operations. All7,493
authored submerged AIR cells, including the failing7,114-cell AIR component,
are enclosed by the source's2,583 protected full-timber skin cells. Zero such
AIR cells reach the exterior in the conservative source flood. Zero source
states below sea intentionally have `waterlogged=true`. This is source closure,
not a current Native seal witness.

Private existing-schema inputs are in
`H/staging/fleet-mercy-water-repair-1793235786407947200/`. The actual shell must
pass `hull-seal-VERIFY-ONLY.json` before any bounded dry-out. Separate unadmitted
AIR-only proposals contain zero tags/commands and intersect none of14 stock
fixture positions. They do not replay the hull or furnishings. No new general
drain tool or feature code was added. The master owns the next repair window,
actual boundary proof, exact dry-out admission and post-fluid/AFTER checks.

## Cleanup and release

Fleet stopped on the actual error and explicitly released at00:48:19UTC
(20:48:19EDT October28). All20 terminal markers were independently authenticated;
all had zero remaining tickets/futures and `cleanup_required=false`. Fresh roster
was `{}`, PID43108/birth unchanged, bridge age7.186seconds.

Private execution folder:
`H/staging/fleet63-three-ships-execution-1793234569364722600/`.
Release witness SHA256:
`1471ba467a27452cebd56a96e22a4bbc3bef0ddf27ec3839f029d62efd32c8ee`.
All20 terminal references/hashes and outcomes are in `actual-native-results.json`,
SHA256 `1e7153897b56a49f13869acae174315b1f39024b7f57f7f5adbdc88496dcf393`.

## Remaining acceptance

Mercy's demonstrated defect and full AFTER remain open. Actual Minecraft views,
walkthroughs, approved dock/gangway links, skiff transfer, original cog sailing,
hoist/cannon operation, two-player use, normal saved/reloaded checks and occupied
harbor performance remain required. The master owns the next repair/client slots
and normal backup; existing3/new3 placement records are never replay payloads.

No new tests were run: this commit records actual runtime evidence and changes
no feature code. Windows ReserveGuard admitted C32MiB/D4MiB for this small record;
Native job forecasts were C0/D1GiB. Monitoring is not an OS quota and cannot
constrain unrelated applications or existing writers.
