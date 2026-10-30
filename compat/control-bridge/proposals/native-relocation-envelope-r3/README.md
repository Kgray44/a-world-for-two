# Native relocation R3: storage-envelope boundary

The native51 Pippin inspection refused cleanly before intent or clone. Every
original MCA tag contained `keepPacked:0b`, which the actual native block entity's
`saveWithFullMetadata` does not contain. This is a chunk-storage envelope field,
not inventory data.

The exact pinned1.21.1 `LevelChunk.getBlockEntityNbtForSaving(BlockPos,
HolderLookup.Provider)` first calls the real BE's `saveWithFullMetadata`, then
adds `putBoolean("keepPacked",false)`. Its pending packed-tag branch instead
copies the pending tag and adds `true`. The inspected class SHA is
`933d0e1b83ba01e7b3fc0a4e1b6c0d4572a921f39ffc3a83baf0ce2777af8805`.
The complete bytecode witness stays in private staging; upstream class bytes
are not rewritten or redistributed here.

R3 preserves every original typed raw catalogue/geometry tag. A separate expected
runtime copy removes **only** the top-level field when its real NBT type is Byte
and its value is exactlyfalse. Packedtrue, a wrong type such as Int0, or a real
native BE producing a field of that name refuses. Every other unknown/custom
field and numeric width stays intact. This is not a general NBT normalizer.

The native before/after conservation snapshots remain the actual unfiltered
`saveWithFullMetadata` results, with all native slots and persistent components.
Only the existing explicit XYZ relocation changes in the after comparison.
On a mismatch, the bounded private terminal records raw storage, derived runtime
expectation, actual native full tag, top-level type IDs and position before the
manual ItemStack-component iteration. It does not print stock to public logs.

Copy this proposal's `NativeRelocationSupport.java` only after Root's review;
all previous files and artifacts remain immutable. The constructor/hooks and
db5e catalogue are unchanged. New request pins are `runtime_tags_class_sha256`
and `level_chunk_class_sha256`. First use the R2 source binder, then
`tools.native_eastern_relocation_r3.seal(...)` with the actual new built JAR.
It emits a new uninstalled request and checksum, never edits the old request.

Pinned API compilation and a real-NBT fixture pass: falseByte-only removal,
immutable raw data, preserved unknown/nested numeric widths, true/int/string/
native-collision refusals and an unrelated typed mismatch that remains unequal.
The fixture creates no world and initializes no Server/Level/LevelChunk class.
Actual native inspection, once-only clone, conservation and restart remain
runtime gates; the fixture does not claim them.
