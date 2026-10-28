# Private candidate.46: startup recovery and durability audit

Candidate.46 is a private development build. It reached native readiness around
**04:35 UTC on 2026-10-28**, completed a normal save/stop, and restarted for a
private preview last observed **ONLINE on port 25575**. The licensed owner client
authenticated and joined this private server at 04:56 UTC. No final release, full multiplayer,
forest completion or artistic acceptance follows from this startup.

[Curated evidence](../evidence/runtime/candidate46-recovery.json) contains aggregate
facts and hashes only. Private paths, seeds, world/player data, credentials and raw
logs remain outside this repository.

## Exact build and source checks

| Component | Recorded pin |
| --- | --- |
| Minecraft / NeoForge / Java | 1.21.1 / 21.1.262 / 21 |
| Enabled mods | 198 total; 192 client; 165 server |
| Owned bridge | 0.6.32; 558,236 bytes |
| Bridge SHA-256 | `5a40c5a968645d10a94efde647c197f73f1f3381a972f29fd04fe24a200eb6ce` |
| Pack manifest SHA-256 | `0daa15709f5300f42c64f4e794418ffb06c38b270c4e612c34ef67c18aeae370` |

The complete source suite passed **754 Python tests in 69.998 seconds**. Packwiz
manifest validation passed for 208 files, and Control Room JavaScript syntax
checking passed. These checks remain separate from actual gameplay.

The preceding candidate.45 watchdog stopped in tree-scope snapshot construction
on regular-grid keys. Candidate.46 replaces the problematic compact immutable
collection copies with guarded hash-backed snapshots while retaining immutability,
null refusal and ownership boundaries. Watchdog limits were not raised.

The exact production scope source SHA-256 is
`eeacf850d6cb4eb43732b83c847143819df6953b1ba89ad2aaf842034dc69ed1`.
A collection-only Java 21 probe checked 131,072 regular-grid keys, map values,
immutability, null rejection and independence from caller collections. Production
copy/membership work took **158.380 ms** with **two CPUs and a 256 MiB heap**.
It created no Minecraft Level, server or world; this is a source/API probe rather
than an in-game tree-generation or server-performance benchmark.

## Actual startup and clean recovery checkpoint

The first recovery JVM reached ONLINE without observed startup errors. One
startup-warmup interval recorded **20 TPS and 2.12 ms/tick**. A single interval
does not establish sustained performance, travel responsiveness or multiplayer.

Normal stop/save produced verified checkpoint **20261028T043630Z-e55a8c**:

- SHA-256: `4384206f639659b09b2d332d2eb058241ca6dc15298f3808745025ed85992fac`
- Archive: 225,852,113 bytes; source: 313,695,186 bytes across 637 files.

A subsequent preview restart reached ONLINE. The matching owner client authenticated and joined at 04:56 UTC.
This proves one current private connection, not two-player or public-import acceptance.

## Saved-world durability after the earlier crash

The unclean crash files and failed receipts were preserved before recovery. A
read-only saved-state comparison found the following architecture durable:

- All **37 eastern houses** and **10 western buildings**.
- Western public streets and the **118-target Rose exterior addition**.
- Only **two already authorized bed cells** differ within those compared
  architecture groups; no other differences or unknown chunks were found there.

This is saved block-state evidence, not a new client visual review, complete
inventory audit or broad ecological acceptance.

Eight earlier native tree-growth outcomes were compared against persisted data.
**Seven are durable. The eighth lost all 36 owned changed cells: seven log cells
and 29 leaf cells.** Its original receipt remains preserved and it has not been
automatically replayed. A completed growth receipt alone is not proof that its
changes survived a crash. No curated living LIFE cohort has been spawned.

## Continuing implementation

The build includes the guarded western cable preparation/creation controller and
read-only retained bridge inspection with automatic resource cleanup. They still
need their own real native admissions: prepared curves or compiled APIs do not
establish cable creation, riding, streaming, bridge motion or restart acceptance.

The refined R5 fountain sculpture has native geometry verification. Its complete
powered fill/flow/STOP/drain/reopen and restart test remains pending. Earlier real
candidate.42 pump flow belongs to that older run and geometry.

Continue the dense north-bank village, whole-settlement 3D architecture, botanical
greenery and native woodland, followed by the separately admitted living LIFE
population. Mill/transport commissioning, strict current SeedGen parity, current
client/graphics/travel measurements and a clean public Prism import remain open.
The owner's accepted small pirate area stays the visual reference; full-world
artistic acceptance is not claimed.

The published public **candidate.31** remains immutable; a clean fresh Prism
import is still unqualified. Its [release evidence](../evidence/runtime/artistic-release-candidate.31.json),
[Create startup/approval history](CREATE-STARTUP-RECOVERY.md) and earlier
[candidate.43 record](NATIVE-CANDIDATE43.md) retain their original scope.

## Subsequent owner preview and tree continuation

The current owner client opened with the 6 GiB setting and authenticated normally
to the private server. Its old menu target was corrected to the preview port;
public pack files retain their separate published target. The usual Control Room
address now redirects to the active preview dashboard. No API proxy or session
security change was introduced.

A new ordinary sapling transaction grew seven log blocks and 30 leaf blocks in
6.618 seconds, including loading and full before-state checks. Resources cleared
with zero remaining tickets/futures. A separate plot failed normally and its
owned changes were restored; it was not retried. Four requests remain unperformed.
The new successful canopy still requires a later stopped persistence check.
This is one operation observation, not a sustained server benchmark or full forest.

The current client still reported a SeedGen worldgen-data read failure and strict
fingerprint disagreement on join. Client generation remained off. Current
client/server parity is therefore still an open requirement.

## Stationary connected resource observation

During a 125.6-second connected observation, all 25 five-second samples were
fresh and one owner was online. Sampled player movement was zero, so this does
not measure fast travel, world generation, active shader load or two players.
Development continued and foreground/render load was not controlled.

- Server: median 20.00 TPS and 5.06 ms/tick (range 4.64–6.64 ms/tick).
- Server physical working set: about 4.65 GiB; median used Java heap 2.83 GiB.
- Client physical working set: median 7.84 GiB (range 7.83–8.69 GiB); its heap limit remains 6 GiB.
- Loaded chunk holders: 1,521 throughout; this is not a count of chunks actively simulating.

Raw samples remain private. The curated record preserves aggregate values and
hashes; this observation does not close travel, idle-disconnect or performance gates.

A subsequent complete source run passed **788 Python tests in 45.285 seconds**,
with Packwiz validation and JavaScript syntax checks also passing. Native
function, artistic and release gates retain their separate status above.
