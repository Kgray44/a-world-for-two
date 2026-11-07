# West Tortuga: three small useful shop processes

Phase2 adds ten hardware cells inside three already-built western shops. The
earlier five shop source packages remain frozen and retain first deployment
priority. This packet uses the existing Native BEFORE/support/PLACE/normal-join/
full-AFTER pipeline. It adds no runtime, observer, configuration, Packwiz, stock,
inventory NBT or world command. Root remains the sole actual world writer.

The stopped source is `20261029T052317Z-89312d`, SHA256
`ab64b9e7b4fa0e5dad2b77deb41a6ee8344ad46c6d522a4ef2048116d7e1017a`.
Later timber repairs/water removal are Root's separate actual operations; this
packet neither replays them nor pretends the older source save contains them.
Root must freshly verify every current predecessor before deployment.

| Existing shop / process | New hardware and actual operating feet |
| --- | --- |
| The Crooked Kettle: cold dough mixer | Basin `(1024,64,-1307)` facing down; mixer `(1024,66,-1307)`; small cog `(1025,66,-1307)` axisY; downward crank `(1025,65,-1307)`. Stand `(1024,64,-1306)`. |
| Low Water Kitchen: hand flour mill | Millstone `(1037,64,-1266)`; small cog `(1037,64,-1265)` axisY; upward crank `(1037,65,-1265)`. Stand `(1036,64,-1266)` in the retained working passage. |
| Bent Spar Repairs: paper-pattern press | Depot `(1071,64,-1247)`; east-facing press `(1071,66,-1247)`; east-facing crank `(1072,66,-1247)`. Approach through AIR at X1073/Y64/Z-1247..-1244. The old barrel/cabinet stays intact. |

All ten target cells are literal AIR in both accepted original Source and the
authenticated893 save, with no saved BE at a target. Existing floorY63, the
press's overhead backing, furniture, façade, roof, inventories, room masks and
new outdoor details remain unchanged. Every target lies strictly inside its
existing main footprint, away from the owner zipline/Hypertube reservations.

## Exact existing-room custody

The accepted western-spit manifest is
`staging/tortuga-western-spit-1793215072699978000/manifest.json`, SHA256
`cbb7810513c9718345cff6440878508f529b3d1394aab854cd47bd3b5c5b9293`.
Its complete Native Source is `complete-after-VERIFY-ONLY.json`, SHA256
`756f1cbc2bbe4e245237b0ec069ad8658815fdd02cb6b5d12e48cf9db9edb1eb`.

The producer reuses the exact accepted pure recipe/rotation/workscene factories.
It requires every reconstructed cell to equal that full Source:891 for Crooked
Kettle,654 for Low Water Kitchen and1,118 for Bent Spar. No roof/property mismatch
is ignored to obtain route metadata. The richer workscene must be applied before
the original rotation; the simpler Bent Spar model correctly failed equality.
No house is rebuilt or regenerated in Minecraft by this Python reconstruction.

Literal working, stair, entry and scene masks come from those same models. Some
old masks include real doors, slabs or other partial shapes. They are retained
with their actual states, never rewritten as assumed AIR or represented as a
new successful walking test. New service positions and machine gaps separately
require actual two-high AIR. Native player walking/model access remains a gate.

## Real item/fluid commissioning

For each unit independently: fresh Native BEFORE and retained-support checks,
one additive PLACE, native normal joins, then strict complete AFTER before any
inputs. All new native BEs start with genuine defaults; no inventory/fluid payload
is supplied. A refusal preserves that unit and its receipt, without replaying
or blocking already successful independent units.

**Crooked Kettle — cold dough.** The actual installed recipe is
`create:mixing/dough_by_mixing`: **one wheat flour +1,000mB water ->one dough**.
It has no heat requirement. Bring one legitimate water bucket and one actual
flour. Use ordinary basin fluid/item interaction; record1,000mB actually entered
and the returned empty bucket. Crank until real mixer motion consumes the flour
and water and yields one genuine dough. Require flour0, water0, dough1, the
actual bucket retained, and no unaccounted actor/basin/dropped copies. Do not
fake a tank, write fluid NBT, or assume bucket interaction succeeded.

The pinned mixer is a **small cog with no shaft ports**, axisY. A direct top
shaft/crank would not power it. Its neighboring same-Y small cog is driven from
below by the downward-facing crank. This keeps the nominal32RPM ratio and needs
no floor/ceiling removal. Its native minimum level is MEDIUM; current configured
threshold30 is below the nominal32. Actual RPM, capacity and stress must still
be observed. The real basin lies exactly two blocks below the mixer. Cold dough
needs no burner, open fire or world-water source. Optional subsequent baking
uses an actual existing cooking station and its current real loaded recipe/fuel;
no baked output is supplied or claimed by this packet.

**Low Water Kitchen — flour.** Drop one legitimate wheat onto the open mill input,
crank and retrieve the real flour/seeds through normal empty-hand interaction.
Installed milling guarantees one flour with a possible two-flour bonus and
possible seed, so a single wheat yields one or three flour, plus zero or one
seed. A16-wheat batch yields16..48 flour, with even excess over16, and0..16 seeds.
Record actual counts and timing; do not predict an exact randomized outcome.
Account for actor, mill and drops; existing kitchen pantry contents are not
cleared, recreated or automatically mixed into the demonstration counts.

**Bent Spar — repair templates and order paper.** The actual installed pressing
recipe is **one sugar cane ->one paper**. Put one real cane on the depot and crank
the genuine press. Require cane0/paper1 after the stroke; collect it and account
for depot/actor/drops. Repeat a small counted batch. This is paper production,
not sugar, a fabricated stock replacement or a copied book inventory. The earlier
nearby standing candidate was an existing barrel/cabinet and was rejected; the
fixed X1073 access strip preserves both. Native reach past retained furniture
and the actual press model must be checked in Minecraft.

For all three: release the actual crank and observe native speed return to zero.
Record completed input/output and any remaining basin fluid before a coordinated
normal save/restart, then actually repeat a process. Current gameplay, restart,
multiplayer, artistic acceptance and TPS/MSPT/CPU/RAM/FPS remain **unverified**.
Source equality and passing unit tests do not establish those outcomes.

## Source invocation

After integrating only this producer, its focused test and this document into
Root's checkout, run the producer there so its already-present frozen West pure
factories are available. The specialist branch intentionally does not copy or
modify another workstream's factory files.

```powershell
python -B -m tools.transport_create_west `
  --home 'D:\A World for Two\staging\world-tests\20261027T053650Z-artistic' `
  --checkpoint-id 20261029T052317Z-89312d `
  --checkpoint-sha ab64b9e7b4fa0e5dad2b77deb41a6ee8344ad46c6d522a4ef2048116d7e1017a `
  --create-jar 'D:\A World for Two\staging\world-tests\20261027T053650Z-artistic\server\mods\create-1.21.1-6.0.10.jar'
```

Output is bounded to2MiB in a unique private `H/staging/transport-create-west-*`
folder, with five independent Native plan files per shop and one provenance
manifest. It never installs anything, supplies items or invokes Native commands.
The original accepted factory/source bytes and the earlier five shop packets
remain unchanged. A later checkpoint needs a real new source/predecessor read,
not a marker replacement or claim that these files already passed Native tests.
