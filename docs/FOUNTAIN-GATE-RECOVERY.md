# One-lever fountain gate recovery

The exact stopped checkpoint `20261027T231434Z-a631c0`, SHA-256
`974382f0ad39b1730ebce96fb91f154789ec1616f23d46405f136ea7bcc0cea2`,
contains a correctly phased OFF circuit: lever false, six torches
ON/OFF/ON/OFF/ON/OFF, dust power0 and a south-facing unpowered repeater.
The sticky piston is **retracted**. Its original ordinary quartz plug remains
two cells in front, at the closed port, while the first front cell is AIR.
The high source/header and four jet witnesses are naturally dry.

This is a detached plug, not evidence of a currently powered extended piston or
a proven torch-feedback loop. A transient prior control/orientation transition
could account for sticky block dropping, but its exact cause is unproved. The
currently correct circuit is preserved; no four-torch replacement is emitted.

`tools/artistic_fountain_gate_recovery.py` emits a finite source-only bundle:

1. Verify all21 exact saved gate/control/dry observations before any action.
2. Place **only** the normal lever's ON state.
3. Use the two-cell SETTLE-ONLY plan to perform normal neighbor notifications at
   both the lever and its unchanged attached source block. This matches the
   existing native helper's lever/source update pattern. Never PLACE that source
   or set torch, dust, diode, piston, head, plug, fluid or kinetic data directly.
4. Obtain actual structural ON verification **and independent current dynamic
   property observations**, hold for at least20 native tick events with actual
   dimension/block-entity progress, and verify ON again. Expected ON requires the extended north-facing sticky
   piston, actual sticky head, port plug, correct six-torch parity and dry highs.
5. Change only the lever to OFF, perform the same normal notifications, and obtain
   strict stable OFF proofs before/after another native tick hold. The plug must
   now be back at its original OPEN position and the port AIR.

The existing `awftbuild verify` checks block identity and selected structural
properties; it does **not** prove exact `lit`, `power` or `extended` values from
these desired state strings. Fresh saved or explicit native property observations
must supply that separate proof. Actual43 exposed a moving piston after100 server
ticks because the empty dimension suspended its moving block entity. The parent
uses the real licensed client to wake normal simulation; no fake player, manual
piston NBT or forced completion is introduced.

The raw native `server-metrics.json` tick sample can prove server-tick elapsed hold if its entire
sampling interval begins **after** the successful settle terminal, belongs to the
same owned PID/create-time/server session, is current, and contains at least20
actual `ServerTickEvent` observations. Preserve that exact sample and hash with
the following successful strict verification. A wall-clock delay alone does not
prove20 actual game ticks or stability. Server tick events alone also do not prove
moving-block-entity progress in a suspended empty dimension. Normal cleanup and operation-specific player guards
remain mandatory. The parent owns every runtime action and this evidence.

Both ON and recovered-OFF plan states are clearly **prospective** until actual
native verification. The immutable actual-before file is kept separately. Failed
or partial stages retain their receipts and stop; there is no blind replay or
direct piston/plug correction. No art, fluid source, inventory, block-entity or
kinetic NBT is replayed. A new stopped dry checkpoint must precede the existing
R5 art producer's `--dry-checkpoint` run. The already corrected south-facing R4
baseline remains the input; no R6 artistic baseline is introduced here.
