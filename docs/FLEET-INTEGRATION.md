# Grand Harbor fleet: sprint integration checkpoint

2026-10-28. Workstream owner: **Build historic harbor fleet**, chat
`01a183b8-3be2-7f93-8f23-f2e914745038`. Master: **Build It!**, chat
`01a17947-1d00-7fd1-aa5e-d1fb514f8671`.

The governing primary-checkout `docs/coordination/WORKSTREAMS.md` and
`docs/coordination/handoffs/FLEET.md` reserve every save/runtime/client action
for the master. No fleet live lease has been granted or exercised. The hard
sprint handover is **2026-10-29 00:26:08 UTC / October28 20:26:08 EDT**.

## Delivered source checkpoints

Branch: `codex/historic-harbor-fleet`; base
`3333bc60646cc594093063ed514a3e51246e35b0`.
[Draft PR3](https://github.com/Kgray44/a-world-for-two/pull/3).

| Commit | Reviewable change |
| --- | --- |
| `2c280de9a869b6e4a2f9da66f013b4f2ac0b8732` | Four major original structure templates, complete belowdecks and immutable NBT/JSON/view exports |
| `8994b749b18875a4b2026daee39676ebfe543e2f` | Three distinct small vessels; connected manual cargo derricks, guarded operator access, backed-ladder graph and explicit load sweep |
| `20d8870dfa4bc539c2bfca7f97b8aae9b8ef3ed3` | Correct sea-level waterlogging, detailed commissioning report and separately proposed custody diagnostics |

The subsequent waterline correction keeps fittings at localY0 dry: the existing
native harbor survey defines water as worldY<63, and the proposed waterline
origin isY63. Older immutable exports remain preserved; use the latest batch
and exact source hashes rather than rebinding an older manifest.

Scoped active files are `tools/grand_harbor_fleet.py`,
`tools/grand_harbor_smallcraft.py`, their two test files, this report and
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
python -B -m tools.grand_harbor_fleet --registry 'D:\A World for Two\staging\world-tests\20261027T053650Z-artistic\dashboard\settlement\registry.json' --output 'D:\A World for Two\staging\world-tests\20261027T053650Z-artistic\staging\fleet-NEW-IMMUTABLE-ID'
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
passed. The latest sprint directive requests targeted checks, so the full suite
was not repeated. After the waterline and fitting-support corrections,
**24 affected tests passed in8.743seconds**. Normal tests use sanitized native property-enum
fixtures; all seven designs were also built against the actual exported native
registry read-only.

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

The retained Lark source also has an unsupported south-facing wheel at local
`(0,17,25)`: required north backing`(0,17,24)` is AIR. The actual current-world
wheel state is UNKNOWN. The master should inspect it and, only with exact current
preimages, consider connected backing at`(0,16,24)` and`(0,17,24)`. No current
Lark geometry or contents were overwritten. All six new templates passed the
subsequent read-only support audit for controls, lanterns, beds and doors.

## Integration and remaining acceptance

The first-berth source must bind the actual30624d archive, registry, source hashes,
world, candidate and origin/rotation. Require saved exact clear targets and
under-keel depth, then **fresh actual native BEFORE verification** immediately
before any master placement. Unknown chunks, natural terrain, construction,
inventories, occupants and protected routes are conflicts, not replaceable AIR.
Preserve candidate50 startup and the master's serialized test windows.

After placement, normal block updates, full native state/BE checks and actual
bow/stern/broadside/elevated/deck/belowdeck photographs decide corrections. Then
walk the real routes and board actual craft; demonstrate ordinary controls and
safe cargo/cannon interactions. Two real players, normal save/stop/restart and
matched bounded harbor performance samples remain separate requirements.

| Acceptance dimension | Fleet lane state |
| --- | --- |
| Original source structures and belowdecks | Implemented; targeted source checks pass |
| Current new structure placement and graphic quality | Pending master batch and actual Minecraft views |
| Actual cog/skiff creation and sailing | Pending current custody diagnosis and native admission |
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
