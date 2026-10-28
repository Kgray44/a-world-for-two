# A World for Two — authoritative workstream coordination

Updated 2026-10-28 UTC by the master chat **Build It!**
(`01a17947-1d00-7fd1-aa5e-d1fb514f8671`). The owner's Master Coordination &
Permanent-World Ownership instruction governs this document. Finish the existing
vision; new workstreams do not authorize feature expansion.

## Authority and save identity

**The master is the sole official-world writer and integration owner.** Specialists
produce source, plans, configurations and evidence in their own code worktrees.
No specialist may edit either save, install runtime artifacts/configuration,
start/restart a server or client, or run a competing live test without a specific
master-issued exclusive lease. A region reservation is not a write lease.

| Resource | Verified identity and current state |
| --- | --- |
| Master development checkout | `C:\Users\kkids\Documents\A World for Two`, branch `codex/master-integration`; based on main `3333bc60646cc594093063ed514a3e51246e35b0`. Concurrent source work is retained. |
| Active town construction save | `D:\A World for Two\staging\world-tests\20261027T053650Z-artistic\world\RosewaterArtistic`. This contains the town KG reviewed and the current construction. It is the authoritative construction candidate, not a disposable replacement to regenerate. |
| Construction runtime home, abbreviated **H** | `D:\A World for Two\staging\world-tests\20261027T053650Z-artistic`; loopback game port **25575**, Control Room **8766**. Its existing settings still say `permanent_world=false` because the native construction tools deliberately admit this private runtime only. |
| Configured permanent runtime | `D:\A World for Two`, world `world\AWorldForTwo`, game port **25565**, `permanent_world=true`, immutable public candidate.31. It has not received the new town work and must not be overwritten or silently relabelled. Controlled final promotion remains a master-owned integration task. |
| Latest construction checkpoint | **20261028T180051Z-30624d**, SHA-256 **3cb269d28ae1ccbac882a44d35277d82c83582274abad2f1cf3b41566d3e9b24**. Verified normal-stop archive: 243,223,697 bytes, 330,830,813 source bytes, 665 files. Includes the 32 new native trees and five new city buildings. No history was pruned. |
| Installed construction pack | candidate.49, bridge **0.6.35**, pack `750dc6e324246300f45649f4d94093c4384576cbb9cce9d247bd8dfaeff55c6c`. |
| Next private integration | candidate.50 / bridge **0.6.36** built, not yet installed or runtime accepted. JAR SHA `13d1b1ff7c2405fadb750d57aa2d58231496f560fd4880c0a7153265be164aac`, 660,685 bytes; pack `052a736c2b9445454eb3ea8490734ab4730e2b34c190cfe31f6c6ed418ab07c9`. Adds the narrowly bounded room mover. Gameplay pins are retained. |
| Current live window | Construction server is **offline**, prior PID40416 stopped normally; master client is closed. No external live-test window or external world-write lease has been granted. Master reserves the next installation/startup/native-inspection window. Revalidate this before any action. |
| Client | One existing KG Prism instance: `D:\A World for Two\instances\AWFT_Check_20261026_214756`; KG heap6GiB. Master owns native camera/inspection input only while the owner's handoff remains active. Never authenticate accounts, use fake players, or replace current player data. |

There is deliberately one active construction runtime and one client. Source
worktrees are permitted; complete extra Minecraft installations/world copies are
not implicitly authorized. The configured permanent save and construction save
are distinct. No record may claim current work is integrated into the configured
permanent runtime until an actual verified promotion has occurred.

## Owners, branches and handoffs

| ID | Owner | Scope | Branch / PR / current handoff |
| --- | --- | --- | --- |
| MASTER | **Build It!**, master chat above | Integration queue, shared files, runtime, official/save writes, backups, deployments, test windows and final acceptance | `codex/master-integration`; main currently `3333bc6`. No open PR existed at initial coordination audit. |
| CITY | Master, with internal `grand_harbor_ships` and `south_bank_district` agents | Whole west/east pirate city and spit, matching the approved footprint layout and original accepted architectural style; interiors, façades, roofs, details and per-addition progress maps | Internal proposals remain in the master checkout; active native edits are master-only. First five additional buildings placed/settled/verified in49. |
| LAND-LIFE | Master, internal `castle_detail` agent | Full south forest, greenery, living residents, habitat/POI correctness and measured population ramps | First32 tree patch completed; first64 normal-AI residents prepared against306, budget reviewed; no cohort spawned yet. Internal agent currently has no live write lease. |
| CASTLE-PLAZA-BRIDGE | Master | Castle/wider-settlement finish, centerpiece fountain, ornate drawbridge, landscape, restart/traversal/visual checks | Current source/native records under `docs/`; no separate external owner assigned. |
| TRANSPORT | **Commission transport and Create**, chat `01a183b6-8091-7453-8f0d-bde8101d7a31` | Railway/station/trains/route/schedules; Hypertubes; western zipline; watermill, press and pneumatic logistics; prepare operation/acceptance tooling | Owned code checkout `C:\Users\kkids\.codex\worktrees\transport-create-commission\A World for Two`, based on3333bc6; branch/PR to be reported by owner. [Current deployment handoff](handoffs/TRANSPORT.md). No live lease. |
| FLEET | **Build historic harbor fleet**, chat `01a183b8-3be2-7f93-8f23-f2e914745038` | Historic ships, explorable belowdecks, harbor/naval mechanics and deployment-ready artifacts | Owned checkout `C:\Users\kkids\.codex\worktrees\historic-harbor-fleet\A World for Two`, branch `codex/historic-harbor-fleet`, based on3333bc6. [Initial boundaries](handoffs/FLEET.md). No live lease. |
| WORLDGEN | **Refine future world generation**, chat `01a183b8-961e-77b3-bf51-077fc8b7a610` | Finish modest future-terrain structure frequency change; preserve generated terrain and SeedGen parity | Owned worktree `worldgen-future-terrain`, branch `codex/worldgen-future-terrain`, base3333bc6. Comparing the existing isolated four-set `proposals/future-structure-frequency/`; the broader pre-coordination comparison is held/unselected. No install/test lease. |
| TERRAIN-PERFORMANCE | **Validate SeedGen parity and DH**, chat `01a183b9-759d-7161-b786-b9149472d8b0` | Strict DH+SeedGen parity, real MapHorizons/Xaero integration, graphics/travel/resource qualification | Owned worktree `seedgen-performance`, branch `codex/seedgen-performance`, base3333bc6. Preserve DH+SeedGen; no Voxy/Roxy. Moonlight provider source repair is installed49 but current client/server parity remains unqualified. No live test lease. |
| CONTROL | **Complete Control Room and WorldAtlas**, chat `01a183b9-ca05-7ef2-8006-14b1d1d648e1` | Atlas freshness/cache/polling, durable task history, restart recovery and browser qualification | Owned worktree `control-room-world-atlas`, branch `codex/control-room-world-atlas`, base3333bc6. Lightweight isolated blank-home dashboard18765 has no Minecraft install/EULA or native evidence. Existing8766 GET-only inspection permitted; no mutations. |
| RELEASE-QA | Master pending specialist assignment | Compatibility reconciliation, current multiplayer qualification, clean Prism import and final release | Shared runtime/config/Packwiz changes require master integration. Public candidate.31 remains unchanged. |

New chats must identify their owner, source worktree, `codex/` branch, exact base
commit, shared files and proposed scope here through a master handoff. Do not
claim unassigned work or change another lane's files. The master serializes PR
integration into main; never blindly cherry-pick an entire branch with unrelated
or overlapping work. Preserve existing dirty work and failed receipts.

## Shared file and runtime ownership

| Exclusive integration resource | Owner / rule |
| --- | --- |
| `catalog/*`, `packwiz/**`, version pins and release manifests | Master only. Specialists submit proposed diffs; no simultaneous generation, installation or publication. |
| Active `compat/control-bridge/src/**`, mod metadata, `tools/candidate.py`, build versions | Master only during candidate50 integration. Specialists use isolated branches/proposals and provide actual API/class pins. |
| `control_room/server.py`, runtime command allowlists, runtime configs | Master integrates serialized changes. No broad command bypass for construction. |
| `H/server/**`, `H/packwiz/**`, `H/dashboard/settlement/**`, client mods/configs | Master only. Separate `H/staging/<owned-source-folder>` read-only-source outputs may be prepared within a declared bounded allocation; never overwrite another source or fabricate native terminals/markers. |
| Coordination document and integration queue | Master maintains the authoritative copy; workstream owners submit updates rather than racing edits. |
| City geometry helpers / room-move proposal | Internal city agents own their named proposal files; master owns active code/deployment. Exact sources are frozen before installation. |
| Forest/LIFE source and audits | Internal LAND-LIFE agent; no further native calls until a new single-use master slot is granted. |
| Transport proposals | TRANSPORT exclusively owns new `compat/control-bridge/proposals/transport-commission-r1/**`, `tools/transport_commission.py`, associated test and `docs/TRANSPORT-CREATE-COMMISSIONING.md`. Conductor-fit changes stay separate from the existing resume contract. |
| Fleet proposals | FLEET exclusively owns new `tools/grand_harbor_fleet.py` and its declared tests/templates. Internal `grand_harbor_ships` now works on city/mover only. |
| Control Room specialist files | CONTROL proposes isolated changes to `control_room/{atlas,jobs,web,storage}.py`, static `{app,atlas,session}.js`, new polling/Atlas-state helpers and scoped tests. Possible narrow metrics freshness changes require agreement with TERRAIN-PERFORMANCE/master first. Master retains `server.py` admission and active Java integration. |

## Spatial reservations

These broad envelopes prevent collisions; exact authored solid/AIR, flight, flow,
POI, entity-body and contraption-sweep masks still govern every deployment.
Unknown terrain is not AIR. Coordinates use Minecraft X/Y/Z; north is decreasingZ.

| Area | Reservation and dependency |
| --- | --- |
| Pirate city / whole northern shore | Master. Measured map context X968..1424, Z−1376..−1008; actual northern natural eastern limitX1415. Follow the approved land shapes, not a blanket rectangle. No houses in water or under the bridge. Small designed docks/stilt edges require exact review. |
| South forest and nature walks | Master LAND-LIFE. Full requested south shore to the cliff, extending east toX1415; current known/eligible component and protected walks decide each site. Approximate inspection envelope X800..1424/Z−1120..−560 is a reservation, not full surveyed land or planting permission. |
| Drawbridge / river navigation | Master. Existing spans X1187..1199/Z−1172..−1115; protect actual55° sweeps, approaches, radio controls, water and ship clearance. Coordinate transport and harbor crossings explicitly. |
| Fountain | Master. Center1138,−1127; pump1140,66,−1129; wheel1145,66,−1130. Preserve the full current wet/flow/body/AIR composition and moving parts, not just those points. |
| Castle / mill boundary | Master castle, coordinated TRANSPORT systems. Mill/rail/tube working reservation roughly X1288..1350/Z−1020..−910. It overlaps forest/castle protections and does not grant excavation or clearance. |
| Existing Hypertubes | TRANSPORT designs, master deploys. Actual entrance positions1331,71,−991 and1331,71,−943; preserve all six native curves,42 filler cells and their collision volumes. |
| Western zipline | TRANSPORT designs/commissions through master deployment. Exact15-node route from1160,168,−760 to1100,72,−1256, source/flight masks in handoff. Keep every span,3.5m hanging body, stations and cliff walk protected during planting/building. |
| Harbor / fleet | FLEET designs, master deploys. Existing flagship reference center1140,−1450; other source-only vessel centers1000,−1350 /1110,−1344 /1230,−1376 are historical proposals, not evidence of placed finished ships. Preserve current actual hulls, waterfront shops, city land and river channel; submit exact hull/rig/sweep/boarding bounds before reserving new berths. |

## Write leases and test windows

Current external lease: **NONE**. Master owns the next candidate50 installation,
startup, current-preimage checks, city room move and selected building deployment.
No specialist may infer permission from server being empty/offline or a lock file.

Every temporary delegation must name the exact chat/worker, save, current verified
checkpoint, candidate/JAR, allowed single operation/region, start/expiry, resource
forecast, player exclusion, expected outcomes and cleanup/release conditions.
Only one world/config/runtime writer may hold that lease. Verify the real process,
actual roster, native maintenance state and pending resource cleanup; a journal,
advisory lock or stale timeout is not proof that an operation has ended.

Never edit while KG/Sera play unless the specific action/window was coordinated.
Player arrival stops admission. Preserve human inventory/progress. Normal stop,
verified retained checkpoint and exact fresh before states precede destructive
work. Uncertain native partials preserve intent, evidence and world state; never
retry, refund, replace UUIDs or regenerate a save to hide the failure.

Keep at least32,212,254,720bytes free **on each** C: andD:. Bound additional writes
and run the supplied ReserveGuard before writers and every5minutes of long work.
No extra full server/client copies, large cache fills or unrelated process kills.
This coordination/monitoring is not an OS quota or a lock on external applications.

## Integration-ready queue and blockers

| Item | State / next authoritative action |
| --- | --- |
| Candidate50 bounded room mover | Exact source/API/ledger fixture passed; independent cleanup/proof review passed. Actual owner map approval recorded. Build exists; install/startup and fresh native inspect/move remain pending. No clone has run. |
| First Pippin room | Fresh306 exact720 saved states and seven typed BE tags equal the retained06 capture. Two separately bounded ordinary-cover cells need genuine before/clear/after proof. Move preserves all source furniture/slots/components through real native vanilla clone, no raw MCA or fabricated inventory. |
| Next three west buildings | Fresh306 sources ready: long ropewalk, wide divided galley, narrow quay cookshop; final seal/checks pending. Each needs genuine native before/support/place/settle/full and actual visual review. |
| First64 scaled LIFE cohort | Fresh306 source:16ladybugs/16deer/32birds,27chunks/23,050cells, seven old managed intents retained. Master reviewed exact4000 global/64-cohort caps and initial128 ramp; additive authority exists. No native actor added yet; installed50 binding, full habitat verification, inspect and one seed remain required. |
| Further forest/greenery | Next native32 pine/larch stand is source-only and held:325 required radius14 halo columns are unqualified. Never weaken the no-generation gate or dispatch it as ready. Additional512 plant pockets/7,241 states in four sectors are source-only and need native before/support/place/settle/full checks. |
| First32 tree patch | Native49 all32 grew; zero failures/recovery, clean resource release. Actual archives recorded two native hives/five stored bees.306 retains them. Full forest density, visual, multiplayer and restart acceptance remain open. |
| First five city additions | Native49 two+three buildings placed/settled/full-verified and mapped separately.306 retains them. Per-addition maps are mandatory for every future set: whole city land, existing buildings/features, newly added buildings, truthful timestamp/provenance. |
| Transport | Preserve existing WAIT_MODE partial; no feed/train assembly or successful ride may be inferred. Zipline frames already exist; native cable graph/ride/restart are pending. |
| Future structures | Small isolated proposal exists; exact spacing/biome/native template and compatibility review precede any integration. Do not regenerate explored terrain. |

## Evidence states and acceptance

Each major item must retain **separate** implemented, runtime, visual, multiplayer,
restart, official-world integration and owner-acceptance states. `Scoped` proves
only its named result. A saved checkpoint is not a successful native restart;
source tests/API probes are not gameplay, graphics or owner approval.

| Major item | Implemented | Runtime | Visual | Multiplayer | Restart | Official integration | Owner acceptance |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Full pirate city | Partial | Scoped additions49 | Partial / new batches pending | Pending current city | Saved; reload pending | Pending promotion | **Layout approved**, full art pending |
| Dense south forest | Partial | Scoped32 new trees49 + prior outcomes | Pending full forest | Pending |306saved; reload pending | Pending | Pending |
| Greenery LIFE | Partial | Scoped3,284 additions48 + earlier plants | Partial | Pending current extent | Pending current extent | Pending | Pending |
| Living LIFE | Partial | Seven curated actors48; five native stored bees recorded49; new64unspawned | Pending current cohort | Pending | Partial saved census; gameplay pending | Pending | Pending |
| Castle/wider settlement | Partial | Scoped construction | Partial | Pending final | Pending current finish | Pending | Partial earlier areas only |
| Fountain | Partial | Scoped pump/four cascades/STOP-drain-reopen47; ornament48 | Final pending | Pending | Current pending | Pending | Pending centerpiece |
| Drawbridge | Partial | Two real55° cycles48 | Final finish pending | Pending current | Current ornaments pending | Pending | Pending full result |
| Railway/tubes/logistics/zipline | Partial | Partial links/infrastructure; commissioning pending | Partial infrastructure | Pending travel | Pending current | Pending | Pending |
| Fleet/harbor/sailing | Partial | Static/source evidence; real sailing pending | Partial | Pending | Pending | Pending | Pending |
| Final pack, DH/SeedGen/maps/performance | Partial | Startup/scoped tests; parity/current complete gameplay pending | Pending current final | Historical two-player only | Pending final | Public31only | Pending final |

Outstanding whole-project criteria include every original requested feature or an
explicitly accepted documented limitation, real two-player travel/gameplay and
performance, complete visual review, matching clean Prism import/release,
controlled official-save promotion and selective staging cleanup. Do not mark the
project finished from passing source tests or these partial rows.
