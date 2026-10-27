# Lanternwater drawbridge: partial opening

The owner requested a **45–60°** opening. The selected default is **55°**:
the north leaf opens to **−55°**, the south leaf to **+55°**, and both return to
zero. These signs preserve the actual upward movement established by native
transformed deck observations. The two leaves face opposing banks and must not
share the same signed opening angle.

This change adjusts the real Create sequencer instructions and their native
commissioning target. It does not replace or resize the existing bridge.

## Preserved physical construction

The placed bridge's immutable physical SHA-256 remains:

`cc2bd89a14d86fc1de2236e5a4f92ca523d911bc128fcf96f91c1e6101fb8b69`

Its 12,317-position native plan, bank approaches, four towers, gearing,
water wheels, buttons, radio positions, glue volumes and existing inventories
remain. The original successful native block verification is retained. That
historical block receipt does **not** establish the current pose of a moving
contraption; the live mechanism and its final replaced deck need separate
checks.

| Leaf | Bearing | Sequencer | Existing glue bounds | New opening |
| --- | --- | --- | --- | --- |
| North | 1199,70,−1172 | 1203,70,−1172 | 1187,69,−1172 → 1198,73,−1144 | −55° |
| South | 1199,70,−1116 | 1203,70,−1116 | 1187,69,−1143 → 1198,73,−1116 | +55° |

Both water wheels remain at x1225,Y68 on their respective pivot z. The real
stone buttons on the banks and the existing four Create redstone links remain
on the compass/iron-nugget frequency.

## Prepare only the new engineering settings

After the current technical update and its verified full-world backup, run:

```powershell
python -B -m tools.settlement_drawbridge --home "D:\A World for Two" --engineering-only --open-angle 55
```

The callable equivalent is `prepare_engineering(home, angle=55,
destination=None)`. The command checks the exact immutable placed master, its
successful native physical receipt, the native registry's world identity, all
declared mechanisms/buttons/radios and every moving deck board in that master.
It binds the **current verified backup SHA** each time it runs.

It writes two unique content-addressed files inside `dashboard/settlement`:

- `drawbridge-engineering-55-<sha256>.json`
- `drawbridge-engineering-55-<sha256>-manifest.json`

The native plan retains `awft-native-engineering:1`, adds
`open_angle_degrees:55` at the top level and on each system, and declares each
signed `expected_open_angle`. The existing `open_negative` fields remain true
for north and false for south. Its construction hash is the already placed
physical hash above. All four native radio controls are declared explicitly.

Preparation performs **zero new physical placements**. It does not write
`plan.json`, `drawbridge-plan.json`, `drawbridge-manifest.json`,
`engineering-plan.json`, backup receipts or any native verification/failure
receipt. The parent workflow reviews the unique result and admits that exact
file as the current engineering plan separately. Do not use the module's legacy
physical-plan generation path to change the current bridge's opening angle.

Angles must be integers from 45 through 60, matching Create's native
`TURN_ANGLE` instruction units and the owner's requested range. Invalid input
is rejected before any output is written. The new plan and audit manifest are
bounded to 2 MiB; the live storage guard checks both drives before writing.

## Native recovery, setup and acceptance

If a previous 90° program is presently open, leave that program intact while
performing the parent's safe native close recovery. Its return instruction was
written for the old pose. Replacing it with a 55° return before closing could
leave the bridge partly raised or consume the wrong button edge.

After actual native closure and deck replacement, configure the new real
sequence for each leaf:

1. Turn 55° in that leaf's existing opening direction.
2. Await a **new** signal from a real bank button.
3. Turn 55° in the opposing closing direction.
4. End, returning to idle.

Native commissioning must distinguish arriving at the opening angle from
actually reaching the sequencer's wait instruction. The closing button must
not be pressed while the opening instruction is still finishing. Check both
bank controls, actual signed angles, real transformed deck positions, idle
program state, stress and ticket cleanup. Complete two full cycles, verify the
closed deck against the retained physical master and check a clean restart.
The generator records intent only; it does not claim those operations passed.

## Clearance is limited and still requires vessel testing

At 55°, the deck stays diagonally over more of the river than at 90°. The
pivots are 56 blocks apart. The far deck block centers lie 28 blocks from the
north axis and 27 from the south axis. Ideal centerline geometry predicts:

- North far block-center Y: approximately **93.44**.
- South far block-center Y: approximately **92.62**.
- Nominal gap between far block centers: approximately **24.45 blocks**.
- Nominal zero-thickness outer deck-edge gap: approximately **23.88 blocks**.

These are authoring calculations, **not measured navigable clearance**. They
exclude deck thickness, under-deck beams, rail/truss geometry, native transformed
collision bounds, water level, ship width, mast height and rigging. A lower
permitted angle narrows the opening further. Passing a block-level or angle
check does not prove that any specific sailing vessel can pass.

The large historic harbor ships are predominantly structural builds; their
presence does not establish mobile traversal beneath this drawbridge. Test a
specific actual movable craft against measured open geometry before advertising
safe passage. Keep the bridge's native ship-clearance status unverified until
that evidence exists.
