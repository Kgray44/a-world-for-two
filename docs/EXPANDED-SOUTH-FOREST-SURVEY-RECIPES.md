# Exact southern forest survey recipes

These are proposed console operations for the parent to run on the empty owned
artistic server. No operation has been submitted by this source lane. The current
native `awftbuild survey x z radius step` grammar samples a square, not a rectangle.
The following five squares cover the requested rectangles exactly at eight-metre
sample spacing, without sampling outside either rectangle.

| Job | Exact console command | Sample bounds X / Z | Observations |
| --- | --- | --- | ---: |
| A1 | `awftbuild survey 1104 -736 96 8` |1008..1200 / −832..−640|625|
| A2 | `awftbuild survey 1232 -736 96 8` |1136..1328 / −832..−640|625|
| B1 | `awftbuild survey 976 -1072 48 8` |928..1024 / −1120..−1024|169|
| B2 | `awftbuild survey 976 -1016 48 8` |928..1024 / −1064..−968|169|
| B3 | `awftbuild survey 976 -960 48 8` |928..1024 / −1008..−912|169|

A has 1,250 observations, 225 deliberate overlap observations, and exactly 1,025
unique columns: X1008..1328/Z−832..−640. B has 507 observations, 156 deliberate
overlap observations, and exactly 351 unique columns:
X928..1024/Z−1120..−912. Two and three squares respectively are the minimum
numbers of squares that fit these rectangles and cover their longer dimensions.
Each command remains below the native 5,000-column and radius-256 survey bounds.

## Native chunk and generation cost

The distinct directly sampled chunk counts are 273 for A and 98 for B. The current
helper explicitly requires a FULL 3×3 neighborhood around each sampled chunk:

| Group | Direct chunk range X / Z | Explicit FULL-neighborhood union | Count |
| --- | --- | --- | ---: |
| A |63..83 / −52..−40|62..84 / −53..−39|345|
| B |58..64 / −70..−57|57..65 / −71..−56|144|

These two neighborhood unions are disjoint, totaling 489 explicit FULL chunk
addresses. Their block envelopes are X992..1359/Z−848..−609 and
X912..1055/Z−1136..−881. Each active operation owns at most one temporary ticket
and nine shared FULL futures. This does not claim that all internally required
generation/protochunk work, normal background systems or final process memory is
bounded to those 489 chunks. Native FULL requests can generate previously absent
terrain, persist normal generation output and encounter normal native features;
these commands are not a zero-write saved-world read.

Run the jobs strictly serially. For each job, preserve its unique native terminal
receipt and copy/hash the completed generic `survey.json` to a fresh private
run directory **before** starting the next command. Confirm the correct native
operation, expected cursor/sample count, zero failures, completion status,
`cleanup_required=false`, zero remaining temporary tickets and zero pending
shared chunk futures. Preserve partial/failure receipts and stop dependent work
if those gates fail. Never reinterpret a partial result as complete geography.
The source helper's actual column cursor is row-major Z, then X.

## Combining observations and future LIFE authority

Validate each result against its command's exact square lattice. Combine A1/A2
and B1/B2/B3 by `(x,z)` only after recording every original observation and
receipt. All samples in their overlaps must agree on the actual surface, fluid,
ground and ocean-floor heights and biome; a disagreement remains a temporal
observation requiring review rather than last-write-wins terrain. Block-entity
observations are whole-chunk lists and must retain their actual scope.

These surveys give sparse native surface/height/biome/BE evidence. They do not
establish every unsampled support column, canopy, root or whole-growth volume.
Native growth still needs its own exact envelope and mutation admission; water,
architecture, authored AIR, paths, mechanisms and protected terrain remain out.

The historical saved study bound checkpoint `20261027T191930Z-f306da`. The current
post-42 stopped checkpoint is `20261027T204224Z-012e63`, SHA-256
`ac863a5f04dd91ca88494c59ed27f138b0b87fdaefea45707b3c55e688365c05`.
Neither automatically becomes the final planting checkpoint. After these surveys
and all remaining construction, retain a new stopped verified checkpoint and
rebuild the forest/LIFE masks against the **final R5 centerpiece** and its actual
current all-block/AIR/routes/BE envelope plus five metres. The older R2 plaza mask
is historical provenance, not current planting authority. Retain corrected Court
and Bramble context, all other building and river exclusions, and the contour-walk
growth skirts. No tree, undergrowth or animal is admitted by this recipe alone.
