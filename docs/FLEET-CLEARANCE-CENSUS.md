# Prospective Wren, Tern and Salt clearance census

2026-10-28. This source-only census genuinely read the authenticated
`20261028T191243Z-6ad3a8` archive, SHA-256
`0ba7ad2097fb52273a37da6a76d8fc030133b79cd26d81b97531d8d74c2546c2`.
It does not assert that any prospective hull currently exists. No native call,
client action, save/runtime edit, placement, clearing, inventory replay or
geometry/producer change was performed. No test suite was repeated.

The original saved states resolve the UNWRITTEN cells from the source circulation
audit. Authored cells use the existing conditional full-AFTER state. All other
checked cells use this census's observed original saved state. Original states
were also read at authored cells to screen for existing BEs and retain honest
before/after provenance. Planned timber/AIR does not become an observed hull.

## Frozen inputs

| Input | SHA-256 |
| --- | --- |
| Wren `fleet-berth-wren-169d2faf9ba9224f/manifest.json` | `35a1f45207d4b1bef6581b48fb7eb832ed462bc772d9ca893fe755f82e8a69b7` |
| Smallcraft `fleet-smallcraft-6c3aa58711e9a7b2/manifest.json` | `6c3aa58711e9a7b2032e559ba8e16c04419bbf40c9721acb3011f4850a59079f` |
| Accepted camera-only `proposals/fleet-camera-overrides/accepted-smallcraft.json` | `e53bb6cbf851a9dd58b70851ea7940da560f7c29e3757a5ffde3734b65d1b4bf` |
| Wren full-AFTER | `2064645686e03e530d04ba66be8c3074e2617769155bdae5b0dcaca0917d3229` |
| Tern full-AFTER | `9156014c9acea8f2b58f9dadce4442fc299f861155a36ff0c9827f4f53e7229e` |
| Salt full-AFTER | `8d642c4af450920455b95984b29f2bd5d4c63f404f7e127d64ed212383d802ce` |

All input bytes were checked against their pins. The historical registry is the
preserved `8cfa5ae77e20b8b5c1730b2928c55156557ebecb7e84480142088bda04ef92c4`
export from 2026-10-27 23:11:56 UTC, bridge0.6.29. It is authoring context and
save-identity input, with current native palette acceptance still pending.

Only the accepted override's two `deck` replacements were applied when evaluating
the existing camera recipes. Every other current frame stayed exact. No optional
fractional-centering shift was applied. Intended room anchors were checked
separately at their rotated voxel centers; those probes are not camera edits.

## Measured source result

The audit checked exact voxel intersections of a **0.6-by-1.8-block standing
body**, including feet/head cells, and the horizontal supporting footprint.
There were **61 pose records**: 37 existing camera frames, 20 intended named room
anchors and four ladder exits. Fourteen exterior camera frames were explicitly
treated as spectator poses, without a walking-floor requirement.

| Craft | Camera / anchor / exit records | Newly observed UNWRITTEN cells | Unique prospective cells | Body conflicts | Required support conflicts |
| --- | --- | --- | --- | --- | --- |
| Wren | 21 / 14 / 2 | 95, all AIR | 171 | 0 | 0 |
| Tern | 8 / 3 / 1 | 55, all AIR | 69 | 0 | **1**, existing `boarding-landing` camera |
| Salt Marigold | 8 / 3 / 1 | 52, all AIR | 60 | 0 | 0 |

There were **300 unique genuine saved-state reads**, including the original
states at prospective authored positions. All 202 previously unwritten checked
cells were observed as `minecraft:air`; zero unknown/unavailable cells, original
BEs or non-AIR effective body cells were found. The 98 remaining unique cells
are conditional authored full-AFTER cells. These counts establish saved/source
occupancy only. Native collision shapes, player climbing, boat embarkation and
current-world clearance remain unverified.

The saved inputs were read without extraction:

- `level.dat`: `7bf4077758d94b77532bb9270245e9b7c8dc4f22f432278eae330e53783a3abd`.
- `r.2.-3.mca`, 9,818,112 bytes: `f0d6251bd0e7e4ea4518ce849605e8712e298d3c663724865fa1b328b15d1d60`.
- `r.1.-3.mca`, 5,971,968 bytes: `9f824140d3f371a6a4997dfe9dce2e545f82b1403e9bd48596718385021d4cf1`.

## Tern boarding camera: exact remaining support defect

The existing `boarding-landing` frame is body-clear but beside the prospective
platform. It has original saved AIR below its feet. Preserve the original source
camera and the accepted `e53bb6cb…` deck override.

| Frame | Feet | Look-at |
| --- | --- | --- |
| Exact existing `boarding-landing` | `(1162.5,65,-1339.5)` | `(1165,66,-1343)` |
| Separately checked intended landing-anchor center | `(1163.5,65,-1338.5)` | `(1166,66,-1342)` preserves the original look direction |

The existing frame's supporting cell `(1162,64,-1340)` is observed original
`minecraft:air`, remains AIR in the prospective composition, and lies outside
the authored platform. It is suitable only as an unsupported spectator view.

For the independently checked intended anchor:

- Floor `(1163,64,-1339)` is **prospective authored** `minecraft:spruce_planks`;
  its observed original saved state is AIR.
- Feet cell `(1163,65,-1339)` and head cell `(1163,66,-1339)` are both genuinely
  observed original AIR, with no original BE.

The master may record a separate camera-only boarding override referencing these
facts. This census did not change either frame, an accepted override, or a
placement batch. The new look-at is a derived target for that one independently
checked anchor; it is not a global pose correction.
The parent subsequently supplied that
[separate boarding override](../proposals/fleet-camera-overrides/tern-boarding.json),
preserving the original deck override and all input manifest hashes.

## Supplemental records and limits

Immutable output:
`H/staging/fleet-clearance-cd525b931ecb7225`, **100,829 bytes**.
Manifest SHA-256:
`0522e1dda5cd3b42f0652f8264354314284796b093dd9397a6092dc7af94dfe3`.

Each craft has a detailed `*-census.json`, an observed-unwritten
`*-current-original-VERIFY-ONLY.json` and a conditional
`*-prospective-clearance-VERIFY-ONLY.json`. All six supplemental native-format
records have `verification_only=true`, `construction_forbidden=true`, empty
commands and empty block-entity tags. Every output hash was independently
checked. No PLACE file, clearing operation or inventory replay was emitted.

The Tern supplemental deliberately retains the observed AIR below the old
boarding camera. A successful state comparison would leave that standing-support
defect unresolved. The prospective records depend on actual admitted hull
placement/full-AFTER verification and a fresh master-owned native check; they
are not current-hull or walking evidence. The major water-return add-on remains
the separate dependency recorded in the earlier circulation/access documents.

ReserveGuard passed before the D: writer with an8MiB bound and before this report
with a4MiB C: bound. The report check measured C:122,069,336,064 and
D:283,517,030,400 free bytes. This monitoring does not constrain external
applications or already-running writers.
