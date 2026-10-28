# Fleet access and helm support proposals

These small proposals are separate from the frozen ship geometry and Wren batch.
They do not authorize a save, server or client action. The master owns admission,
installation, actual use and the quay interface. No official world was modified.

Source: `tools/grand_harbor_access_repairs.py`. Private immutable output:
`H/staging/fleet-access-f29a648280829067`, 686,667 bytes, where `H` is
`D:\A World for Two\staging\world-tests\20261027T053650Z-artistic`.
Manifest SHA-256:
`f29a64828082906734f82e52ad4e03c05c6d84edd3d43f7a2d8df1e41b6776f3`.
Every observation binds the genuinely read normal-stop checkpoint
`20261028T191243Z-6ad3a8`, SHA-256
`0ba7ad2097fb52273a37da6a76d8fc030133b79cd26d81b97531d8d74c2546c2`.
Current native states and current installed palette remain unverified.

## Retained Lark helm

The archived wheel at `(1140,80,-1425)` is actually
`create:copper_valve_handle[facing=south,waterlogged=false]`, with an existing
block entity. Both northern backing cells `(1140,79,-1426)` and
`(1140,80,-1426)` are AIR. The deck at `(1140,78,-1426)` is
`chipped:stacked_dark_oak_planks`. This resolves the earlier **saved-state**
uncertainty; actual current native state is still pending.

Pinned Create6.0.10 requires backing on the opposite side of FACING. The proposal
adds that same full timber at exactly those two AIR cells, making a connected
post. It supplies no wheel tag, block-entity write or inventory. The original
wheel is omitted from the placement plan. Do not replace the retained Lark hull
or replay its source furnishings.

`lark/two-ordinary-blocks-placement.json` SHA-256:
`68cc8091bd5b213dc495cda6bbaf687895fba01edbd17f05806c18f2a21387bb`.
Separate BEFORE, retained-support and AFTER verification documents are included.
The master must verify current exact targets/supports and read the actual wheel
block entity before admission, then compare it unchanged after placement/settle.
All existing fields and inventories must survive. Supported source geometry is
not proof of actual control behavior or steering.

## Wren water-return ladder, dependent request only

The Wren source landing needs a return route from the water. The three-cell
request is:

| World cell | Requested state |
| --- | --- |
| `(1000,63,-1349)` | `chipped:stacked_dark_oak_planks` backing below the existing source platform |
| `(1000,63,-1348)` | `minecraft:ladder[facing=south,waterlogged=false]` |
| `(1000,64,-1348)` | `minecraft:ladder[facing=south,waterlogged=false]` |

Both ladder cells have full northern backing in the prospective composition.
The three needed cells outside the old full AFTER, including upper exit
headroom, were genuinely reread as AIR from6ad3a8. The existing source platform
and old full AFTER remain explicitly **prospective**, not observed hull placement.
All nine existing Wren block-entity tags are byte-identical in the updated
verification plans. No stock, block-entity tag or entity is placed by this request.

`wren/prospective-request-NONEXECUTABLE.json` SHA-256:
`de77c5c5194ea039d26399f22453b47906ee168e510cf0aeddeaf5380d3326b2`.
No executable Wren placement document is emitted. Master must first actually
place/settle/fully verify the original Wren batch, manifest
`35a1f45207d4b1bef6581b48fb7eb832ed462bc772d9ca893fe755f82e8a69b7`.
It must then obtain current native access preimages, inventory/BE preservation
checks and a current exclusive lease before deriving the three-block placement.

The ladder consumes two old AIR probe cells. Verify the **old** full AFTER before
this addon; afterward use the prospective updated full AFTER, SHA-256
`88e7dc87e43979788de3be86f71679ac082ba2bdf8273098364ed9b7b1aaa6aa`,
once the real outcome matches it. Do not replay the original placement to satisfy
an obsolete AIR expectation. Normal swimming, climbing, boat transfer and safe
two-player passage still require actual game tests.

Seven targeted refusal/dependency tests passed in0.009 seconds. Parent review
verified all nine output hashes, the exact two-block Lark placement, the absence
of any executable Wren placement, and all nine unchanged Wren tags. These are
source results only; graphics, control interaction, multiplayer and restart are
unverified. The exporter bounds D: allocation to8MiB and uses ReserveGuard;
monitoring does not constrain external applications or existing writers.
