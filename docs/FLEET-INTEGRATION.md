# Grand Harbor fleet: sprint integration checkpoint

2026-10-28. Workstream owner: **Build historic harbor fleet**, chat
`01a183b8-3be2-7f93-8f23-f2e914745038`. Master: **Build It!**, chat
`01a17947-1d00-7fd1-aa5e-d1fb514f8671`.

**Actual deployment update, 2026-10-28 22:21 UTC:** Resolute Wren, Tern Pilot
Cutter and Salt Marigold Ketch now exist in the authoritative construction
world. Under a new exclusive master lease, each passed fresh native BEFORE and
support checks, one placement, normal settling, full unchanged AFTER checks and
map queuing. All18 genuine terminal markers were independently authenticated;
cleanup/tickets/futures/failures were zero. The lease was explicitly released
early. See [actual deployment evidence](FLEET-NATIVE-DEPLOYMENT55.md).
Earlier source-only/no-placement statements below describe the earlier
checkpoints. Client views, walking, sailing, two-player use, restart and
permanent-save promotion remain unqualified.

The governing primary-checkout `docs/coordination/WORKSTREAMS.md` and
`docs/coordination/handoffs/FLEET.md` reserve every save/runtime/client action
for the master. The first bounded fleet lease produced one genuine four-cell
native BEFORE check and no placement; it expired during preflight and was
explicitly released. See [the preserved attempt](FLEET-NATIVE-ACCESS53.md).
Any new operation needs fresh authority. The hard
sprint handover is **2026-10-29 00:26:08 UTC / October28 20:26:08 EDT**.

## Delivered source checkpoints

Branch: `codex/historic-harbor-fleet`; base
`3333bc60646cc594093063ed514a3e51246e35b0`.
[Draft PR3](https://github.com/Kgray44/a-world-for-two/pull/3).
Current feature-code checkpoint: `28a354f6efe4382664a3af7d6a1468e6adbe4270`.
Subsequent report-only changes preserve those tested source bytes.

| Commit | Reviewable change |
| --- | --- |
| `2c280de9a869b6e4a2f9da66f013b4f2ac0b8732` | Four major original structure templates, complete belowdecks and immutable NBT/JSON/view exports |
| `8994b749b18875a4b2026daee39676ebfe543e2f` | Three distinct small vessels; connected manual cargo derricks, guarded operator access, backed-ladder graph and explicit load sweep |
| `20d8870dfa4bc539c2bfca7f97b8aae9b8ef3ed3` | Correct sea-level waterlogging, detailed commissioning report and separately proposed custody diagnostics |
| `c267f850a01cbdd009772b4407a47f3b2334f6b1` | Supported wheel handles and cabin models; retained Lark support issue identified |
| `cec9f378f17f8a7a58c265cafe124a7dbceae623` | Keep the brig's mess ration locker beside its bulkhead; regression verifies it survives construction |

The subsequent waterline correction keeps fittings at localY0 dry: the existing
native harbor survey defines water as worldY<63, and the proposed waterline
origin isY63. Older immutable exports remain preserved; use the latest batch
and exact source hashes rather than rebinding an older manifest.

The [first exact Wren deployment batch](FLEET-WREN-BATCH.md) supplies the selected
saved-world berth, exact before/support/place/after hashes and21 actual-camera
recipes. Its construction-world/native deployment remains master-only.
The [fresh berth census](FLEET-BERTH-CENSUS.md) also supplies passing Tern and
Salt Marigold batches and the exact unresolved Petrel, Mercy and Reed Fin blockers.
The [circulation audit](FLEET-CIRCULATION-AUDIT.md) records source camera fixes,
unqualified body cells and the remaining major-ship water-return dependencies.
The [saved native-craft audit](FLEET-SAVED-CRAFT.md) confirms both original craft
are retained exactly once; their next step is current inspection and use. The
later refused inspection is not evidence that the craft need creation.
The [pinned craft controls](FLEET-CRAFT-CONTROLS.md) identify actual persisted
bindings, driver-seat checks, sail/cargo behavior and the cannon-fire key.
The [supplemental clearance census](FLEET-CLEARANCE-CENSUS.md) resolves unwritten
body cells and supplies a second small camera correction. A
[finite three-skiff supply proposal](FLEET-SKIFF-KITS.md) preserves the original
craft while preparing the requested additional boats for ordinary player launch.

Scoped active files are `tools/grand_harbor_fleet.py`,
`tools/grand_harbor_smallcraft.py`, `tools/grand_harbor_berth.py`,
`tools/grand_harbor_remaining_berths.py`, `tools/grand_harbor_smallcraft_berths.py`,
`tools/grand_harbor_access_repairs.py`,
`tools/grand_harbor_hoist_demo.py`,
their scoped test files, this report and
`docs/FLEET-MARITIME-COMMISSIONING.md`. The custody patch under
`proposals/fleet-craft-custody-diagnostics/` is a proposed shared-bridge change;
the active bridge, pack manifests, runtime and saves are untouched.

## Fleet and interfaces

Coordinates below are inclusive **local X/Y/Z bounds**, with Y0 at the waterline
and increasingZ aft. They include authored AIR, rigs, boarding structures and
derricks. They are not world placements or navigable-water approvals.

| Design / role | Required berth and sail state | Local minimum → maximum |
| --- | --- | --- |
| Rosewater Lark, retained original frigate | One offshore ship, partial drying canvas | `(-18,-8,-67) → (19,68,48)` |
| Golden Petrel, grain fluyt | Dockside, furled; broad cargo body, narrow pear stern, three masts | `(-17,-8,-60) → (21,61,36)` |
| Resolute Wren, dispatch brig | Dockside, furled; finer low hull, two masts | `(-14,-6,-56) → (17,51,32)` |
| Mercy of the Tide, relief storeship | Dockside, hanging drying canvas; fuller body and glazed galleries | `(-18,-9,-67) → (20,68,44)` |
| Tern, pilot cutter | Harbor-mouth proposal, one mast | `(-4,-3,-20) → (7,25,14)` |
| Salt Marigold, coastal ketch | Harbor-mouth proposal, two masts | `(-5,-3,-23) → (7,29,17)` |
| Reed Fin, shallow river lighter | River proposal, sweeps and cargo; no standing rig | `(-3,-1,-12) → (6,5,11)` |

Names are proposed authoring identities; the master maps them to any retained
approved ship identities. Historical source-only centers are not proof of placed
ships. Preserve the current Lark and its actual overlays/inventories; its neutral
export is a design reference and does not authorize replacement.

Each new major ship includes captain, officer/lieutenant berths, wardroom, crew
hammocks and mess, galley, gun deck, distinct cargo, separated empty magazine,
sail/rope stores, switchback stairs and an independent backed ladder. Cargo,
accommodation arrangement, armament, hull stations, afterbody and rigs differ.
The fluyt is minimally armed; no powder or projectiles are supplied. Their
gun-service contents remain tools and supplies.

New-major boarding floor anchors are Petrel`(20,1,0)`, Wren`(16,1,0)`,
Mercy`(19,1,0)`. Two-wide attached stairs reach the weather decks. No gangway
extends into an assumed quay. The master must approve the actual ship/quay/skiff
interface and preserve cargo routes, the river and all existing infrastructure.

The new cargo derricks have a real contiguous X shaft to the tip pulley. Pinned
Create6.0.10 requires the crank to face away from that shaft: these east-side
cranks face east. A backed ladder reaches a guarded service platform. The
source checks require an empty reserved descending-load volume. They remain
**unassembled and uncommissioned**; no cargo movement or boat retention is proved.

## Reproduce the private original structures

From the owned fleet source checkout, with Python3.12+ and installed pinned
dependencies:

```powershell
python -B -m tools.grand_harbor_fleet --registry 'D:\A World for Two\staging\world-tests\20261027T053650Z-artistic\staging\fleet-registry-provenance-8cfa5ae7\registry-original.json' --output 'D:\A World for Two\staging\world-tests\20261027T053650Z-artistic\staging\fleet-NEW-IMMUTABLE-ID'
```

The exporter checks live ReserveGuard after serialization and before its first
write, capped at32MiB on the destination drive and0 on the other. It creates a
new directory containing seven local-coordinate JSON templates, seven original
standard structure NBT files, seven real-camera recipes and a hash manifest.
No seed, save path, runtime authority, entity or executable command is in a
template. NBT is original authored geometry, not a world/save export or downloaded
schematic. It retains inventories supplied by the source. DataVersion3955 was
confirmed in the existing1.21.1 save.

NBT uses nonnegative coordinates: its minimum corner is displaced by the JSON
template's lower bounds relative to the waterline origin. Rotate around the
same waterline origin, including all facing/axis/rope-connection states and
block-entity positions. The existing native builder consumes its own bound
`awft-native-settlement:1` plans; the neutral JSON format intentionally cannot be
mistaken for such a plan. The master-requested first-berth batch supplies the
actual bound native documents and exact saved preimages separately.

## Verification and failures

The focused combined regression run passed **45 tests in11.222seconds**:

```powershell
python -B -m unittest tests.test_grand_harbor_fleet tests.test_grand_harbor_smallcraft tests.test_artistic_ship tests.test_artistic_harbor_craft -v
python -B -m tools.pack validate
node --check control_room/static/app.js
```

Pack validation passed with208 manifest records and no errors; JavaScript syntax
passed. Focused checks were used during implementation. After the waterline,
fitting-support and locker corrections,
**35 focused fleet/smallcraft/berth tests passed in14.488seconds**. The berth's
10 tests also passed independently in1.140seconds before the final locker update.
Normal tests use sanitized native property-enum
fixtures; all seven designs were also built against the actual exported native
registry read-only.

The final feature-code checkpoint `28a354f` passed full discovery on2026-10-28:
**1,021 tests in126.333seconds, no failures, one skipped**. The Windows symlink
fixture remains skipped for WinError1314; no privilege or gate was bypassed.
Pack validation again passed208 records/no errors, and JavaScript syntax passed.
The private full output is `.local/fleet-verification/unittest-20261028T1953Z.txt`.
Its SHA-256 is `c09ebb98101b7b2e1551694886ca8c6530e68110bd67ff3b6800daa5b7c0f2cf`.
This final source run launches no Minecraft instance and proves no gameplay.

The earlier replacement AGENTS instructions required full unittest discovery.
That exact command completed on2026-10-28: **988 tests in148.598seconds, no
failures, one skipped**. The skipped test is the real symlink fixture in
`test_bridge_release_pack`: Windows refused creation with WinError1314. No
privilege or fixture gate was bypassed. Pack validation and JavaScript syntax
also passed again. The retained full output is private at
`.local/fleet-verification/unittest-20261028T1901Z.txt`; it is not committed.

The frozen registry has explicit historical provenance: native export
`2026-10-27T23:11:56.377525200Z`, bridge`0.6.29`, SHA-256
`8cfa5ae77e20b8b5c1730b2928c55156557ebecb7e84480142088bda04ef92c4`.
It is not a fresh candidate49/50 registry. Its exact3,375,094bytes are preserved
at`H/staging/fleet-registry-provenance-8cfa5ae7/registry-original.json` before any
master refresh of the mutable runtime pointer. Native enum/source checks against
that file do not prove current runtime palette, block survival or gameplay.
Current native validation remains mandatory. This correction changes no hull,
inventory, protected mask or frozen deployment batch.

During development, source checks correctly refused bilge-intersecting stores,
unanchored or construction-intersecting rope, material-run violations and wrong
drive/load/ladder arrangements. Those source failures were corrected before
their checkpoint. A maintenance worm in the retained Lark was explicitly allowed
as a tool; ammunition remains excluded. No failing runtime test was erased.

The historical real craft inspection remains refused with
`Persistent entity region custody changed; no creation performed`. Its exact
cause remains UNKNOWN. The proposed diagnostics patch preserves refusal and
existing original UUIDs and records the missing bounded before/after differences.
Java21 compilation and a focused reflection probe passed; no modified bridge was
installed. See [commissioning and custody details](FLEET-MARITIME-COMMISSIONING.md).

The retained Lark source has an unsupported south-facing wheel at local
`(0,17,25)`. Genuine6ad3a8 reads confirmed that saved wheel and its existing BE,
the two missing northern support cells and the actual deck below. The
[two-block helm support, four-block Lark water return and dependent Wren ladder](FLEET-ACCESS-REPAIRS.md)
preserve existing BEs/inventories. Current native state and behavior remain
unverified. No current Lark geometry or contents were overwritten. All six new
templates passed the read-only support audit for controls, lanterns, beds and doors.

## Integration and remaining acceptance

The current first-berth source binds the actual6ad3a8 archive, retained historical
registry and source hashes. Native admission must additionally bind the current
world, candidate and origin/rotation. Require saved exact clear targets and
under-keel depth, then **fresh actual native BEFORE verification** immediately
before any master placement. Unknown chunks, natural terrain, construction,
inventories, occupants and protected routes are conflicts, not replaceable AIR.
Preserve the current installed candidate and the master's serialized test windows.

After placement, normal block updates, full native state/BE checks and actual
bow/stern/broadside/elevated/deck/belowdeck photographs decide corrections. Then
walk the real routes and board actual craft; demonstrate ordinary controls and
safe cargo/cannon interactions. Two real players, normal save/stop/restart and
matched bounded harbor performance samples remain separate requirements.

| Acceptance dimension | Fleet lane state |
| --- | --- |
| Original source structures and belowdecks | Implemented; targeted source checks pass |
| Current new structure placement and graphic quality | Pending master batch and actual Minecraft views |
| Original cog/tender retention | Each original UUID is saved once in6ad3a8; preserve intents, tags and actual wildlife passengers |
| Actual sailing, rowing and cargo use | Pending current native inspection and player use; no repeat creation |
| Embarkation, collision, hoist, cannon interaction | Pending actual operation |
| Two-player use | Pending KG and Sera participation |
| Restart persistence | Pending current normal restart and reinspection |
| Full-harbor performance | No fleet-lane TPS/MSPT/FPS measurements yet |
| Configured permanent-save integration | Master-owned, pending controlled promotion |
| Owner visual/gameplay acceptance | Pending |

All local writers were admitted above the separate30GiB C:/D: reserves. This is
monitoring of owned work, not an OS quota; it cannot constrain external apps or
already-running writers. No world, credentials, third-party JAR, cache or runtime
log is committed. Keep the goal open until the native, visual and gameplay work
is completed or a limitation is explicitly accepted by the owner.
