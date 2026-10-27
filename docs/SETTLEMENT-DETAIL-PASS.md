# Settlement architectural detail pass

This pass refines the existing permanent settlement in place. It uses the actual
Squaremap overview tiles `minecraft_overworld/3/2_-2.png` and `2_-3.png` and all
ten exact, previously native-verified construction sources: core, pirate port,
drawbridge, castle, south bank, four final vessels, and final shared harbor access.
The authoritative access source is the final 4,148-position delta; the obsolete
access entry in the earlier harbor aggregate is never used.

The top-down review identified long teal castle roof planes and pale end walls,
repeated domestic gables, and a long uninterrupted timber promenade. These are
overview observations, not a shader or interior review. The generator does not
claim that this pass completes the owner's cinematic artistic requirements.

## Designed changes

The final in-memory assembly against the actual registry and deployed source
composite admits **1,593 changed positions in five independent district plans**.
Its 165 feature records include individual chimney flues; that number does not
mean 165 buildings or 165 large interventions.

| District | Changed positions | Features | Composition |
| --- | ---: | ---: | --- |
| Rosewater Castle | 465 | 25 | Seven framed sloping rooflights, four rose/sea-glass gable windows, twelve framed masonry/tracery relief panels, two conversation pockets |
| Original village | 114 | 4 | A five-wide gabled cottage dormer, three-wide shed dormer, seven-wide barn hayloft dormer, one projecting timber window hood |
| Lanternwater pirate port | 288 | 42 | Six differently proportioned attic dormers, plus sculpted flues on existing chimneys |
| Willow Crown south bank | 498 | 82 | Selected gabled/shed dormers, trade-window hoods, and varied flue crowns; several trades receive no dormer |
| Grand Harbor quays | 228 | 12 | Eight solid loading-bay thresholds, two different work shelters, a netmender's work stop, and a maritime bench/planter pocket |

Dormers use three-, five- and seven-block widths, gabled and shed roofs, alternate
roof faces, and the actual underlying roof height. Flues use round, square or
sculpted upper sections with paired small/large chimney pots. Variation belongs
to architectural groups; there is no random block-noise pass.

The castle keeps its pale stone, rose, teal and warm timber palette. Its large
rooflights interrupt different parts of each roof plane, rather than forming a
roof-wide repeated stripe. The carved panels use Chipped calcite, Rechiseled
quartz and native Mythrais tracery. Macaw roof blocks form smaller projecting
window hoods, and Handcrafted benches furnish two small paved court pockets.

Two proposed cottage hoods are deliberately deferred: their positions contain
the existing upper porch deck. That deck is preserved instead of being silently
replaced to force the detail into place.

## Coordinate inventory

- Castle rooflights: x1163–1167/z−1015–−1011;
  x1177–1181/z−996–−992; x1243–1247/z−1012–−1008;
  x1265–1269/z−1004–−1000; x1243–1247/z−987–−983;
  x1265–1269/z−972–−968; and x1278–1282/z−964–−960.
- Rose gables: centers (1172,Y90,−1022), (1172,Y90,−984),
  (1256,Y91,−1028), and (1256,Y91,−958).
- Framed castle wall panels: western library wall x1160 at z−1014, −1007,
  −1000, −993; eastern royal wall x1272 at z−986, −979, −972, −965;
  northern ballroom wall z−1028 at x1246, 1252, 1258, 1264. Each is three wide,
  Y69–73, between existing glazed bays.
- Court seating: centers (1200,Y68,−976) and (1227,Y68,−976).
- Four harbor pockets: x1037–1041, x1073–1077, x1181–1185, and x1235–1239,
  all at z−1249–−1248, on unchanged Y65 decks, with new details limited to
  Y66–70. All six promenade rows z−1247–−1242 remain clear.
- Harbor loading thresholds: centered on x1001, 1028, 1052, 1081, 1144,
  1177, 1210 and 1241, crossing z−1249–−1242 at Y65. They retain a solid,
  uninterrupted walking plane and avoid existing stairs and crossing geometry.

Every final per-feature coordinate bound, old state and replacement is recorded
in its private manifest. Those exact manifests, rather than this summary, govern
native admission.

## Native air admission

The old quay plan did not record most air above its deck. Unknown air is therefore
not accepted as construction permission. A separate **VERIFY-ONLY** probe checks
200 exact air positions and 40 known deck supports around the four pockets.
It must never be placed: doing so would clear the very space it is meant to test.

The initial probe is SHA-256
`bcccb9be80e392ea7781da65b5407d93bfc9d4922795cb440c42f39e5d6332d9`.
The parent reported a native candidate22 verification with 240 positions and zero
failures, finished `2026-10-27T02:56:28.566766600Z`. The generator independently
requires that completed, exact-hash receipt, the same world/seed, the probe's
original backup binding, and unchanged probe bytes before admitting any of these
air cells. A later verified backup does not rewrite the historical probe. The
resulting detail plans bind the new current backup; their companion precondition
plans freshly verify every target again before any placement.
The receipt establishes air/deck state only; it does not establish the artistic
quality, usability, or performance of the later furniture.

## Preparation and preservation contract

Run the source-only in-memory check:

```powershell
python -B -m tools.settlement_detail --home "D:\A World for Two" --dry-run `
  --clearance-manifest "D:\A World for Two\dashboard\settlement\detail-clearance-bcccb9be80e392ea\manifest.json" `
  --clearance-receipt "D:\A World for Two\dashboard\settlement\detail-quay-air-clearance-candidate22-verify.json"
```

Remove `--dry-run` to prepare a new unique private `detail-pass-<identity>`
directory under `dashboard/settlement`. This writes an index and, for each
district, an immutable construction plan, full previous-state audit manifest,
and **VERIFY-ONLY precondition plan**. All outputs combined are capped at
16 MiB, with at most 40,000 positions per district and a 512-block footprint.
The live storage guard checks C: and D: before the first output write. Existing
directories, plans, failed probes and receipts are never replaced.

The public Python interfaces are:

```python
load_context(home, clearance_manifest=None, clearance_receipt=None)
construct(context)  # in memory; no world/API/file writes
prepare(home, destination=None, *, clearance_manifest=None, clearance_receipt=None)
prepare_clearance(home, destination=None)  # small verify-only probe, no placement
```

Each architectural feature is transactional. An unknown previous state,
unapproved solid replacement, unsupported component, overlapping feature,
protected inventory, doorway/window buffer, existing vessel/drawbridge voxel,
or recorded route conflict rejects that entire feature. The actual assembly
protects 1,047 historically discovered/supplied block entities and 15,302
recorded route-clearance cells. Existing inventories, signs, furniture,
machines, moving bridge geometry, ships and cannons are preserved. Existing
full-block deck inlays keep their solid walking surface. No mobs, explosives,
world commands, permanent tickets, physics assembly, or continuously running
networks are added. Useful new quay stations are ordinary crafting/cartography
tables; their interaction remains subject to native play review.

The module has no server, API, client, shader or region-file launch path. It never
changes generic `plan.json`, native receipts, Packwiz, the world, or Control Room.
The parent remains the sole live-world writer.

## Parent deployment and remaining proof

For each district, in order:

1. Bind the current verified backup and freshly verify the exact companion
   precondition SHA against the real world. It includes **every replacement
   target and new target**, plus known attachments. Any failure stops that
   district; preserve the receipt and revise the complete affected feature.
2. Place only the corresponding exact construction-plan SHA.
3. Verify the new states, preserve the receipt, then queue the changed map area.
4. Inspect actual exterior/interior model shapes, daylight/night lighting,
   overhang and roof junctions, window visibility, routes and working stations.

Native placement, fresh before/after verification, restart persistence,
walkthrough, measured performance and shader review of this detail pass are
pending. Top-down map review and synthetic tests cannot prove cinematic quality.
No Minecraft client is launched while the owner is playing another game.

Storage compliance here covers these bounded owned writers and live reserve
checks. It is a monitoring rule; it does not impose a quota on external games,
other applications or pre-existing processes.
