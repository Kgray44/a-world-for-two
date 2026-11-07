# White Clam: real pneumatic receiving and dispatch

This eight-cell additive source uses the existing Native construction pipeline.
It creates no goods, filter item, BE inventory tags, runtime controller or new
observer. It is source-qualified against the authenticated d72 recovery, not
deployed or functionally accepted. Root owns the actual world-write window.

| Part | Exact coordinates / native orientation |
| --- | --- |
| New receiving barrel | `(1319,65,-1136)`, up-facing, empty native default |
| Extracting connector | `(1318,65,-1136)`, facing/arrow west, mode extract |
| Item pump | `(1317,65,-1136)`, facing west, rotation axisX |
| Real straight tube | `(1316,65,-1136)`, east/west connections; native west functional rim |
| Inserting connector | `(1315,65,-1136)`, facing/arrow west, mode insert |
| New dispatch barrel | `(1314,65,-1136)`, up-facing, empty native default |
| Actual small drive cog | `(1317,65,-1135)`, axisX, beside pump |
| Actual hand crank | `(1318,65,-1135)`, facing east, drives cog from west shaft |
| Operating feet | `(1319,65,-1135)` and `(1314,65,-1135)` |

All eight positions are literal AIR in both the fixed built-shop source and
the actual d72 save. Existing furniture, inventories, walking routes, floors,
ceiling and owner-completed tube/zipline mechanisms remain unchanged. Before
and AFTER include real service space, barrel access and six-face neighbor context.

The installed Overpressure0.1.7.4 JAR is pinned at
`9c03c26bc50c637dbe1d8b9e19e9c10218687c61d335b36588f11e54805c4cf7`.
Its actual current `pneumaticTubes.packagersOnly=false` admits raw items without
a config change. Primary native code establishes pump rotation axis=facing axis;
it is a small cog, so the adjacent same-axis small cog supplies power without
blocking an item port. `getFlowDirection` returns the pump facing while its real
BE reports running; flow direction is not inferred from the crank speed sign.
The inserted barrel lies west of its insertion connector; the receiving barrel
lies east of its extraction connector. Native inventory lookup respects mode.

The real tube uses complete native properties, including `has_connection=true`,
west rim, and no second rim. These come from the pinned normal connector/rim
rules, not a broad property-ignore policy. Normal settlement and strict Native
AFTER must still verify actual modes, attachments and the derived tube fields.
If those fail, preserve the receipt and diagnose that small native difference;
never replay all eight cells or remove expectations to manufacture a pass.

## Actual commissioning order

1. Freshly verify `before-VERIFY-ONLY.json` and `supports-VERIFY-ONLY.json`.
   Place `additions-PROPOSAL.json` once, run
   `normal-joins-SETTLE-ONLY.json`, then strictly verify
   `complete-after-VERIFY-ONLY.json`. Source d72 is historical; current Root
   cleanup/player changes require actual new admission. Native defaults create
   the two empty barrels and machinery. No stock or stored item tags are loaded.
2. With the lane empty, operate the actual hand crank and observe genuine pump
   RPM, stress and running/flow state. Stop and observe zero speed after native
   crank activity expires. The nominal32RPM/10 active ticks are pinned API facts,
   not an observed runtime benchmark or a successful transfer.
3. Count one legitimate plain wheat into the actual receiving barrel. Crank
   until one identical wheat actually arrives in the dispatch barrel. Inspect
   both barrels, extractor, pump, tube, inserter, actor and nearby item entities.
   Require input0/output1, transit0 and no unaccounted copy. Movement particles
   or an empty receiving barrel alone do not prove correctness.
4. Repeat with16 wheat, requiring exactly16 unchanged wheat in dispatch and no
   remaining input/transit/dropped goods. This is transport, not a milling recipe;
   never report produced flour or invent transport losses/outputs.
5. Through the genuine normal Create filtering UI, configure the extractor from
   a legitimate wheat sample. No filter NBT is authored in this packet. Record
   actual native filter identity/configuration; a filter template is excluded
   from cargo totals. Feed eight wheat plus one iron ingot. Require eight wheat
   delivered, the iron retained in receiving, no iron in dispatch and no transit
   or dropped items. This is the first selective-extraction/sorting receipt.
6. Record actor and all lane contents before/after. Preserve exact item IDs,
   counts and components. Stop only after actual transit drains; no reset,
   refund, inventory replay or replacement UUID hides a stalled item. Native
   pump/crank failure keeps the actual partial state for recovery.
7. Stop using the crank and verify zero kinetic speed. In Root's coordinated
   normal save/restart, retain all counts/filter state, then run another real
   transfer. Measure current resource impact during idle and active operation.
   No current multiplayer, restart, TPS/MSPT, graphics or owner claim exists yet.

Run `python -B -m tools.transport_create_warehouse` using the explicit source
home/checkpoint/JAR arguments documented for the [first shops](TORTUGA-CREATE-SHOPS.md).
Private output is capped at1MiB in a unique `H/staging/transport-create-warehouse-*`
directory. It contains the same five Native plan roles and a provenance manifest.
It is independent of the33-cell continuous Keel Store motor and first29 shop cells.

For the retained Copper Wren mill, d72 also confirms its old output connector at
`1311,68,-1007` is currently `mode=disabled`. Its actual output chest is north at
`1311,68,-1008`. That connector requires fresh native inspection and ordinary
insertion-mode configuration before feeding real wheat. Do not trust the older
manifest's intended `insert` value or replay historical whole-mill commissioning.
