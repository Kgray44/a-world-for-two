# Lanternwater: roofs, bays and occupied depth

This is a separate fixed-only artwork proposal built on the corrected future
bridge physical base `82778b15dc4139ed149df2c26adb67dc93ff92a6c9fd5a8d33b103d0d4915404`.
It does not alter the frozen moving-leaf admission, place anything, or reuse an
earlier native cycle as acceptance of new geometry. Current-save admission waits
for the parent's completed moving transaction and verified stopped checkpoint.

The actual candidate38 `bridge-control.png` shows a broad dark eave hiding the
roof silhouette, flat framed wall panels and a blank middle storey. The primary
comparison keeps the real camera: feet 1180,72,-1190, yaw -12.9946165,
pitch -18.174744. Its native image SHA256 is
`11f444917cf2857f08498bd0c169609c55e3213931b294fdfc139d4879c69f29`.

The new design changes physical structure:

- The north tower receives a steep copper hip and a genuinely open three-by-three
  lantern cupola. Its small hanging light sits under a solid roof crown. Corner
  posts retain open sky between them; this is not another plaster attic box.
- The south tower has a lower half-hip with two recessed attic transoms and a
  short ridge, plus a separate small bell canopy. The real vanilla bell hangs
  from a full solid crossbeam tied into the wall. Placement creates its ordinary
  default BE; the proposal injects no NBT or artificial bell interaction.
- Both main-storey windows project one block into supported bays. Original flat
  window cells open into those bays. Actual joined Macaw glass, carved jambs,
  corbels, sill ledges and pointed upper details create multiple depths. Their
  native horizontal edge parts follow increasing-coordinate right then left.
- Dressed lower corner feet become narrow carved supports above. Contained
  flowers sit on real projecting ledges; warm wall-bracket lamps attach to the
  retained corner walls. Framed middle panels supplement the bays rather than
  standing in for structural depth.
- Lower-room coffer ribs and a longitudinal trimmer sit below the real floor,
  stopping before the stairs. Upper gallery ribs span wall to wall beneath the
  roof. Existing stairs, their headroom, lamps, furniture, controls and every
  original BE payload stay exact.
- Four existing authored solid cells on the dry upper bank faces become normal
  recessed stair profiles. This reduces opaque volume; it adds no solid into
  water or the navigation channel. Moving girders and their glue/sweep remain
  outside this fixed proposal and are not silently redesigned again.

The steep slopes use the installed Mythrais `roof_low_straight_67_*` and
`roof_up_67_*` pair, not painted cubic stairs pretending to have a steep pitch.
Pinned model inspection found separate lower and upper components, inherited
copper/oxidised variants and a small amount of model overhang. The source uses
only original block IDs and public state schemas; no author model or texture
bytes are copied. Native model scale, joins, corner appearance and collisions
remain visual/runtime checks. Copper end slopes, oxidised flanks and central
bright standing seams are deliberate architectural surfaces.

`tools.artistic_bridge_towers.author` emits an artwork geometry document and a
full **unbound verification-only** proposal in a new private folder. Its separate
`prepare` function binds the exact frozen geometry to a current verified stopped
checkpoint, authenticates the saved complete bridge and all changed target
states, refuses actual BEs, and emits before/delta/full/recovery artifacts. It
does not invoke a native command or overwrite a generic plan.
Both complete towers pass the conservative three/nine material rule, and all
authored bridge surfaces pass the absolute nine-block cap. The focused tests
also reject a new BE at a proposed bay, unknown block schemas, changes to the
moving leaf and a broad uniform plane.

After a fresh stopped checkpoint, the next binding must authenticate exact
actual states at every target, refuse unrelated solids/BEs at new air targets,
preserve the completed mechanical envelopes, and retain a reversible delta.
Fresh native before/after verification, matched real screenshots, normal walking
and model/leaf-sweep clearance must precede acceptance. Any resulting new full
physical hash must be rebound into later commissioning receipts. No geometry
count or synthetic test establishes beauty or owner approval.

The first native candidate40 placement retained twelve construction-time window
part differences. All six authored masks are intact two-by-two windows. Pinned
Macaw `ConnectedWindow.onPlace` performs an inner normal shape update only when
its computed state differs; the bulk builder's known-shape outer write suppresses
the final neighbor update when the last upper-right pane is already correct.
This leaves two stale parts per bay. The failed receipt is preserved. The
canonical final-neighbor expectation remains unchanged; the residue is not
accepted as the correct window design. Normal native neighbor reconciliation
and a fresh strict full verification are required separately.
