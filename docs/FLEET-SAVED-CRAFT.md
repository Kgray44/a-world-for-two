# Original native craft: saved custody clarification

Both original requested craft are retained **exactly once** in the authenticated
normal-stop checkpoint `20261028T191243Z-6ad3a8`, archive SHA-256
`0ba7ad2097fb52273a37da6a76d8fc030133b79cd26d81b97531d8d74c2546c2`.
The later refused inspection did not establish their absence. Preserve their
creation intents and identities; do not attempt to create these craft again.

## Genuine saved observations

`H` is `D:\A World for Two\staging\world-tests\20261027T053650Z-artistic`.
The private immutable report is
`H/staging/fleet-custody-585920e187a5fc26/saved-original-craft.json`, SHA-256
`585920e187a5fc26cf2ff67e9da4a1db9b501ec6a837f759b14c6762b02e17ef`.
The report and two complete typed original entity tags total16,207bytes.
No entity/world data is committed to Git.

The read-only scan authenticated the archive and each of its11 entity-region
entries against the saved manifest, then decoded419 populated entity chunks,
897,616NBT bytes and930 entities including passengers across the archived
dimensions. Every decoded chunk matched its stored coordinates and1.21.1
DataVersion3955. Region/header/length, compression, decoded-byte, node/depth,
chunk and entity caps were enforced. No external chunk reference or unknown
compression was silently skipped. Each original UUID matched exactly once.
This is saved custody, not a loaded/pending census of the running server.

| Craft | Original UUID | Saved position | Saved passengers |
| --- | --- | --- | ---: |
| Small Ships cog | `62cd3578-b01b-5ab4-b7e8-6f74734cb4f4` | `(1196.5,62.07772726508138,-1264.5)` | 2 |
| Spruce rowing tender | `59f253a3-00b6-576b-ae62-306aa75d8a8c` | `(1194.5,62.52334561064546,-1253.5)` | 0 |

The cog's main `Items` list is empty, its container size is108, its furled white
sail has health100, hull damage is0, and saved locked/sunken/sinking flags are0.
It currently carries an **`envelope:pigeon` in Seat7** and a
**`naturalist:butterfly` in Seat3**. Preserve those real passenger identities,
their tags and seat assignments. Do not delete, clear or replace them to make a
test easier. No human participation is inferred from these wildlife passengers.

The complete typed tags are retained privately, with SHA-256:

- Cog: `dd697bd3dc6f8947b5537b4597020cadb921b4cbca20c2da86a9e933612bbd34`.
- Tender: `407dcf7cb73e9607eb07701e915d9d2b22bef5e4fe616d8b3e04cc7d52bcc1b7`.

These are preservation records, not replacement/spawn payloads. Normal movement
changes position/motion tags; record real outcomes and preserve identities,
contents and actors without replaying the archived entity NBT.

## Historical native receipts, all preserved

| Receipt under `H/dashboard/settlement/` | Actual result |
| --- | --- |
| `harbor-craft-result-bff1ba82-9cf3-46de-a776-0e1e21b38a28.json` | Candidate26 created both original UUIDs on2026-10-27. Terminal remained incomplete because multipart initialization was not yet ready. Both created entities were preserved. |
| `harbor-craft-result-4cc28ef7-8112-4304-989c-61bfbbe661dd.json` | Candidate28 inspection on2026-10-27 found persistent=1 and loaded=1 for each original UUID, cog parts8/8 ready, normal tender and clean resource release. It claimed no controls/boarding/sailing acceptance. |
| `harbor-craft-result-f1994113-768f-44e2-abc1-64a0f4944dc7.json` | Candidate41 inspection later refused because persistent entity-region custody changed; no new creation occurred. The cause remains UNKNOWN. |

The exact receipt SHA-256 values, in the same order, are
`5f2fd286bdbaa1a0aea275faee19b47a02cdb240d267c919aa506f213050b831`,
`57cd83061a8f9e31487592a5a3254544749b717580112631b26a10d32e37a700`,
and `b8f6911477a71b01707ddfa5f4373dfe2e94919eea394d88bff8d5042e818a29`.
The proposed bounded custody diagnostics remain unapplied: the master's active
`HarborCraftSupport.java` still matched base
`b5e97f965a11d73c3db3f7514b2b01bf75b742e9546dd99d773c203757465d52`
when reread on2026-10-28.

## Next master action

Inspect the **existing original identities**, current native parts, actual
passengers, contents, body clearance and controls in the master's serialized
window. Resolve and retain any failed custody diagnostic; never weaken a
creation gate or infer entity absence from a refused operation. No second create
operation is appropriate for these original craft.

Actual departure/return, cargo use, tender-to-Lark transfer, graphics, two human
players, controlled normal reload and harbor performance remain unverified by
this fleet workstream. Archived retention is not successful native restart or
gameplay acceptance. The saved audit performed zero native calls and zero world,
inventory or entity writes. Its private D: allocation was capped at8MiB and
admitted by ReserveGuard; monitoring does not constrain external applications or
existing writers.
