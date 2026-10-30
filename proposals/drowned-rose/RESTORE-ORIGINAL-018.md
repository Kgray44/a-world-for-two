# Final0.1.8: three exact originals and one explicit profile reconstruction

This supersedes the uninstalled0.1.7 two-original repair. Keep all earlier
artifacts, source snapshots and failed receipts. Root is the sole installer,
world writer and operator; this source chat has performed no recovery or UI.

The authoritative stopped336ba5 census found41 of45 tavern patrons and all351
LIFE entities, with no matching UUID duplicates or player UUID collisions.
That is392 physically saved managed entities. Restoring the four missing
identities would return45 tavern/351 LIFE/396 combined; it has not happened yet.

Oona, Dara and Rhea have byte-exact native compound payloads extracted from
authenticated42bdb5. Niamh has no recovered saved NBT. Root explicitly authorized
reconstructing ONLY Niamh from her original pinned45-roster profile with the
same UUID/name/skin and native defaults, preserving her ledger/preferences/
dialogue. This is reported as profile reconstruction, never exact-NBT recovery.
No guessed inventory or ownership is created. No other profile is eligible.

Final artifact:
`D:\A World for Two\staging\drowned-rose-source-20261029\compile-45-0.1.8-final\awft-tavern-0.1.8.jar`
94,782bytes, SHA256
`8bd49547621a3843740f83a896462e0fc2c7668dbae38cac0bad176de39f0aa4`.
Use the same file on server/client and retain the exactb296 config and45 ledger.

Root's exact source/destination file map and four reviewable commands are in
`compile-45-0.1.8-final/FINAL-HANDOFF.json`, SHA256
`60135c38509de63222b316a4069afbdfb0bd2597ef96270a0bc90d1f492f8ac7`.
Stage the3 gzip files plus byte-identical `336ba5-census.json` under server
`config/awft-tavern-recovery/`. Total staged payload is27,145bytes. Gzip names
are their exact source SHA256 plus `.nbt`. The fresh census SHA is
`2f01c704298f5e0d37e057134526eb6a2c70ade6b830ffb4e2543b4ae1af0e90`.

| Action | Fixed existing UUID | Required SHA |
| --- | --- | --- |
|restore-original Oona |8dfc2201-e604-367f-9e34-f2577927b13f |b07c3d8c8082d59e1e6db8adb6288a88ef2fdc6db7687f6aa4095c6c8b0259e4 |
|restore-original Dara |4a494cee-f2c4-3b5c-aa06-e52b2e4bb447 |b3149fb9adbbaf3fdff7d6ad18068ccc84c2f4ddc6c6e9d31d29995955964ead |
|restore-original Rhea |0ac83eb9-fa42-351e-b72a-136affeef0ba |95e40d2326c8f72b4383f7c015f6a274f2b54581ac859f1940c92adf07c2b87f |
|reconstruct-missing Niamh |62622710-89e4-3007-82c1-4693b3818539 |3a6f083faf2ac1147b4c8e504ff4e61fe12983bbd1415107b8335c06350ae474 |

Syntax is `awfttavern <action> <UUID> <SHA>`,129 or132 characters. Root owns
the private140-character backend allowlist and tests; no dashboard UI is added.

Both actions mechanically require the pinned fresh336ba5 absence proof, exact
admitted layout/registered ledger, saveable managed seat type, all four FULL
chunks with entity storage loaded, and no existing conflicting UUID in any
loaded dimension. Existing matching originals are preserved without insertion.
Root's full saved census covers unloaded regions; loaded lookup alone does not.

The original action authenticates each compressed8KiB-bounded file, uses native
64KiB-bounded NBT reading, and checks original ID/UUID/name/tag/AI/persistence/
single-entity payload/position. It loads without inserting, then checks the
full2,916-cell native preimage, actual noCollision and LivingEntity body margin.
It inserts that original object once, retaining its original data and position.

Niamh's original initial position is not retained: the last ledger destination
is chair12 with recent chair12/band1/floor56/floor16. The ONE proposed standing
location for Root review is exact existingfloor16 at1293.5,65,−1287.5, an original
standing-slot candidate and her earliest retained destination. The code pins
that location; no reroll is possible. It refuses a reservation or actual body
collision and never moves another resident. The factory uses her fixed original
UUID/name/skin and verifies default NoAI=false and empty held items. No ledger,
dialogue history or saved preference is reset.

Actual outcomes explicitly distinguish `Original restored/preserved/refused`
from `Missing profile reconstructed/preserved/refused`. Status has separate
counters and exact refusal reasons. A closed chunk/entity window or occupied
body is a refusal, not permission to bypass the gate or summon unguarded.

Java21 compilation and native NBT/profile/proof adversarial checks pass, as do
the native-A* synthetic detour/blocked/corner checks and45,000 policy transitions.
The0.1.6 path, persistent seat, client pose,45 roster and skin classes/assets are
unchanged. Actual restoration, native instrument music, seated appearance,
seat save/unload/reload, two clients and measured performance remain pending.
