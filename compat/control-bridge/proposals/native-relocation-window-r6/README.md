# Exact native MCW context witness (R6 proposal)

Source-only additive correction to the frozen R5 helper. No world action,
inventory edit, candidate build or active-source installation is performed here.
Catalogue698969 / allocation517 and every transaction/ledger rule stay unchanged.

Copy `NativeRelocationSupport.java` and `NativeWindowStateWitness.java` together
into the next coordinated bridge build. Retain the unchanged R5
`NativeToolboxCustody.java`. Constructor, commands, tick/stop and shared lease
hooks remain the same. Use `tools.native_eastern_relocation_r6.bind` in place of
R5 bind, or seal an already R5-sealed request with R6 `seal`; it adds the actual
compiled witness class hash and creates a new immutable request. No request may
omit this pin or reuse a request for another helper.

The input is the original captured full BlockState, not the observed cloned
result. Only the exact pinned NON-BE MCW2.4.2 `ConnectedWindow` class is admitted.
Its actual native `updateShape` dispatches `WindowState` against six actual
neighbor states captured in the same server tick. A finite read-only accessor
exposes only those six states: own-result reads, unrelated APIs and writes fail.
After calculation all six actual neighbors must remain identical. Block object,
facing and every non-part property must remain identical; actual full state must
equal the independently returned native state and retain actual native survival.
Unknown MCW classes keep the original conservative outside-context admission.
No existing fingerprint, typed-NBT, slots/components, source-AIR, lease, intent,
cleanup, quarantine or once-only checks are relaxed.

Read-only INSPECT runs a positive real registered source-window calculation and
four immutable argument counterfactuals before any intent: changed actual part,
wrong source class, replacement actual block and wrong actual facing must each
refuse for their specific reason. These use real source neighbors without placing
or constructing a block/entity. Their actual native result appears in
`native_MCW_read_only_counterfactuals`. This remains pending until the next
native INSPECT; source compilation is not their execution.

The moved-state verification, independent quarantined audit and restart inspection
all use the same exact native calculation. Full real BE tags, every slot and
component still compare with the immutable pre-move native snapshots. Pippin's
actually invoked failed transaction remains quarantined: use read-only audit and
the separately reviewed current-custody record only; never replay its clone.

Final named-API compilation passed in 1.968s with Java21, two processors and
256MiB, no world calls. Private receipt:
`D:/A World for Two/staging/relocation-r6-FINAL-1793225055683521700/receipt.json`
SHA256 `3285d3542ab6185de928970c0ce8008b4d9f44fc6730a85a8e2d303c4ca9c55b`.
The two earlier standalone constructor probes failed and remain preserved. One
had a fixture-only old Guava duplicate; the corrected classpath then correctly
refused construction after vanilla froze intrusive holders. No registry unfreeze,
Unsafe allocation, copied native algorithm, upstream JAR patch or fabricated
passing fixture was used. Actual next-loader INSPECT and a legitimate new move,
full custody audit and restart remain required native gates.
