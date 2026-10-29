# Candidate 53 access attempt: limited native proof, no placement

This records the first fleet access attempt on 2026-10-28. The four-cell helm BEFORE check passed. A subsequent loaded-only wheel inspection produced no fresh inspection artifact, admission stopped, and the lease expired during preflight. **Zero PLACE operations ran. The fleet objective and native access commissioning remain open.**

For paths below, `H` is `D:\A World for Two\staging\world-tests\20261027T053650Z-artistic`. This record was prepared from preserved files and the fleet coordinator's account; its preparation made no native/API/client/runtime calls.

## Authority and process identity

- Root lease: `H\dashboard\settlement\exclusive-fleet-access53-once.json`, SHA-256 `68d465b5f9c9412e18de23df08478e10ea1559e6c08b31d15034bb8601cdc418`.
- Exact window: `2026-10-28T20:28:18.615312+00:00` through `2026-10-28T20:38:18.615312+00:00`.
- Candidate `0.1.0-candidate.53`, bridge `0.6.39`, JAR SHA-256 `496a22cf30d517dbc2bcae2806f6412c17a0656c081d0cb8fb76d0c2c8d9c1d4`.
- Java PID `45036`, process birth `1793218109.072006`.
- The lease required actual hash-marked receipts, action outcomes, ticket/future/helper-idle status, player roster and explicit release. An error/partial preserves evidence and is never replayed/refunded.

This expired document is historical authority only. No current world lease is inferred from it, the preserved runner, later coordination messages or this record.

## What actually ran

The genuine `verify` ran from `2026-10-28T20:31:57.433611500Z` to `2026-10-28T20:31:57.545263300Z` against `H\staging\fleet-access-a3fd2c47bbfae964\lark\current-before-VERIFY-ONLY.json`, plan SHA-256 `d3eb48e741c1bd1f4c678599d3a3990d83a46fec98be6f9eb67ef86182af92b8`.

| Cell | Verified block identity/state |
| --- | --- |
| `(1140,78,-1426)` | `chipped:stacked_dark_oak_planks` |
| `(1140,79,-1426)` | `minecraft:air` |
| `(1140,80,-1426)` | `minecraft:air` |
| `(1140,80,-1425)` | `create:copper_valve_handle[facing=south,waterlogged=false]` |

Terminal: `H\dashboard\settlement\settlement-result-c178ec06-0395-4624-a65a-bf7871819094.json`, SHA-256 `f98bbe8f72868c31c203fa42566207ef2b6b5b94c20f615d2b3941381c712e14`. Its genuine `.json.complete` marker contains the matching terminal SHA-256. The marker file's own SHA-256 is `1d199ed84a55e55b11cb0ff0c29b5852e35bf4771721aeea7604e341bbc2c9ba`.

The terminal reports four blocks, zero failures, zero temporary tickets remaining, zero pending shared chunk futures, and `cleanup_required=false`. Its status is `verified actual block identities, orientation, block entities and supplied inventories`. This is the limited check's status, not proof of every wheel configuration field.

Next, **one** allowlisted loaded-only command, `awftengine inspect 1140 80 -1425`, was attempted. No fresh `engineering-inspection.json` resulted. The command error was at host `16:31:58` / `20:31:58 UTC`. Root confirmed that this was the expected loaded-only refusal after Native verify releases/unloads its chunks. No inspector retry occurred.

Admission stopped with `RuntimeError('No fresh native loaded-wheel inspection; no further admission')`. The operation's progress contains only the completed four-cell verify. The broader seven-target scope recorded in that progress file is not an executed placement count.

## Evidence limits and custody

`SettlementSupport` VERIFY compares block identities and block-entity existence, and checks supplied `Items`; it does not compare arbitrary full configuration NBT. The four-cell plan supplies no block-entity tags. Therefore the successful BEFORE check is **not a full wheel-BE preservation witness**. There is no fresh successful wheel inspection from this attempt to supply that missing proof.

Preserve `H\staging\fleet-access53-live-1793219517103502400\` intact:

- `lease-copy.json` retains the attempt's lease.
- `progress.json`, SHA-256 `abff1f01e6444925662e0fb4eb7ec871a13208a6565e148bbf37a337438bd690`, retains the successful verify and admission error.
- `wheel-saved-full-BE-BEFORE-VERIFY-ONLY.json`, SHA-256 `5f432504e6693cdb1a5765c33790d0ec1cb18c77d24ed9a259402876089710e2`, is a derived saved-wheel-BE VERIFY-only proposal. **It was not executed.** It supplies no native preservation witness and must not be relabeled as one.

Fleet reported zero PLACE, zero block/item/entity changes, and zero client/runtime/configuration changes in this attempt. Fleet explicitly released its lease to the master at `20:40:27 UTC` with a fresh empty roster `{}`, PID `45036`, bridge age `2.421` seconds, and the same clean terminal. The lease had already expired. This record does not independently re-query that release state.

Root later authorized no wheel-tag writes and the independent five targets. That message arrived after expiry and was not acted on. It does not extend the expired lease or authorize a replay.

## Next admission remains separate

The coordinator has prepared `H\staging\fleet-access53-runner\run.py`, reported syntax-checked and unexecuted. Its existence is preparation only. A fresh explicit lease and its exact SHA are required before any further admission, together with the applicable live guard/process/roster checks. No action is authorized by this document. Preserve the first attempt and all failed/limited evidence when recording any later attempt separately.

No support blocks or return ladders were placed by this attempt. Wheel configuration, native support survival/orientation, walking and skiff return, and the wider fleet commissioning remain uncompleted by this evidence.

Only this source record was written by the reporting agent. ReserveGuard allowed C `4,194,304` / D `0` estimated bytes at `2026-10-28T20:45:35.9640835Z`, with free C `120,994,009,088` / D `283,466,076,160` bytes. This monitoring instruction does not constrain external applications or existing writers. No commit, runtime test or repeated source suite was performed.
