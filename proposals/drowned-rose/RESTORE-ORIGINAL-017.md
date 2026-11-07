# Private original-two native body gate in0.1.7

The two existing original profiles are already registered in the retained45
ledger. Initialization deliberately skips them and is not a recovery method.
No source chat recovery, live command, install or UI action has occurred.

The fresh verified stopped336ba5 archive
SHA256 `cdeaff96b090dfa559ff05e1712c69850d9764f3c6271f58f0b40cdf378a9e46`
contains41 of45 tavern patrons and all351 LIFE entities (1,472 entity rows
including passengers). No matching UUID duplicates or player UUID collisions
were found. Missing patrons are Oona Kelp, Dara Moss, Rhea Hook and Niamh Wick.
The scoped command below can restore ONLY the authenticated Oona/Dara payloads.
The additional two require Root's separate evidence and scope decision; never
recreate45 blindly or call a roster reconstruction exact-original NBT recovery.
Receipt: `D:\A World for Two\staging\drowned-rose-source-20261029\stopped336ba5-tavern45-life351-census.json`,
SHA256 `2f01c704298f5e0d37e057134526eb6a2c70ade6b830ffb4e2543b4ae1af0e90`.

Root stages the byte-exact original gzip files under server
`config/awft-tavern-recovery/<gzipSHA>.nbt`. Only these fixed UUID/hash pairs
are admitted:

| Original | UUID | Original gzip SHA256 |
| --- | --- | --- |
| Oona Kelp |8dfc2201-e604-367f-9e34-f2577927b13f |b07c3d8c8082d59e1e6db8adb6288a88ef2fdc6db7687f6aa4095c6c8b0259e4 |
| Dara Moss |4a494cee-f2c4-3b5c-aa06-e52b2e4bb447 |b3149fb9adbbaf3fdff7d6ad18068ccc84c2f4ddc6c6e9d31d29995955964ead |

```text
awfttavern restore-original 8dfc2201-e604-367f-9e34-f2577927b13f b07c3d8c8082d59e1e6db8adb6288a88ef2fdc6db7687f6aa4095c6c8b0259e4
awfttavern restore-original 4a494cee-f2c4-3b5c-aa06-e52b2e4bb447 b3149fb9adbbaf3fdff7d6ad18068ccc84c2f4ddc6c6e9d31d29995955964ead
```

Each command is129 characters and requires Minecraft permission2. Root owns
the private backend exact allowlist; there is no new dashboard button or UI.

The component requires the admittedb296 config/existing ledger and a saveable
managed Seat type. All four tavern chunks must be FULL with their actual entity
storage loaded. It checks UUID presence across every loaded dimension without
force-loading other regions. Root's fresh whole-world saved census separately
proves absence from unloaded regions; loaded lookup alone cannot prove that.

For an absent original it reads at most8KiB, rejects linked paths, authenticates
the fixed gzip bytes, and bounds native NBT accounting to64KiB. Entity type,
original UUID/name/tag, persistence/AI flags, single-entity payload and finite
approved position must match. The full2,916-cell native preimage is rechecked.
Native EntityType loading creates an object WITHOUT insertion. Its real body
must pass native noCollision plus a LivingEntity test with0.1-block margin.
Only then is the original added once. UUID/name/skin/inventory/position remain
the original payload; the registered ledger is not reset.

Existing matching originals produce `Original preserved` with no insertion;
foreign collisions or any failed prerequisite produce `Original refused` and
the exact reason. A successful insertion produces `Original restored` and the
UUID/source SHA. Status exposes separate restored/preserved/refusal counters.
A closed Native read window or occupied original position is a refusal, not
permission to remove inhabitants, change identity or bypass the body gate.

Focused native NBT tests accept both genuine payloads and refuse foreign UUIDs,
hash/path changes, altered entity/name/tag/UUID, passengers and oversized or
changed files. Actual command insertion, seat persistence/pose, music and runtime
performance still require Root's controlled game verification.
