# Native Hypertube entrance correction

Candidate37 attached both real Create stations after the scoped empty-world wake.
It then stopped before creating any tube link, water, feed or train. The first
span requests the south face of the north entrance, but the original R2 entrance
faces north. The pinned Hypertube0.6.0 `HyperEntranceBlockEntity` offers only its
`FACING` while unconnected. The south entrance has the converse mismatch. This
is an authored orientation error, not evidence of an automatic or foreign link.

`tools.artistic_mill_orientation` reads the exact original R2 plan/manifest and a
new verified stopped-world backup. It requires all seven saved native tube BEs
to be present, stopped and free of connection payloads. It refuses unknown
connection fields and active derived block states. Its only physical changes are
the two entrance `facing` values. Native connection-version fields, every BE,
inventory, other block and original systems description remain intact.

The output separates a two-cell preimage, a two-cell placement delta and a full
corrected **verification-only** plan. The placement delta loads no BE tags. The
parent must verify the preimage, place only that delta, verify the complete
corrected composition, then bind fresh exact-version native commissioning
authority. Original R2 plans and failed receipts are retained. Preparation and
unit checks are not native placement or successful travel.

The production helper keeps the occupied/unsupported-face refusal and records
actual states, available faces, bounded stored endpoint summaries and connection
counts. It never clears or follows foreign pointers. Replaying an existing link
would require exact reciprocal endpoint/direction/offset ownership and actual
filler-owner/collision-volume validation; a non-null connection alone cannot
authorize idempotence. This correction does not implement such replay.
