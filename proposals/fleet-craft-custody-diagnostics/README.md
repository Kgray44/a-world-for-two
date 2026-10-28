# Harbor craft custody refusal diagnostics

This is a **proposal**, not an active bridge change, installed runtime or sailing
repair. It preserves the existing refusal when persistent entity-region custody
changes and adds the missing evidence needed to identify that change.

Target: `compat/control-bridge/src/worldfortwo/bridge/HarborCraftSupport.java`.
Exact primary source SHA-256:
`b5e97f965a11d73c3db3f7514b2b01bf75b742e9546dd99d773c203757465d52`.
Proposed source SHA-256:
`4f48c88630a49b757bc56f7828cc4522d2d9f6e3ff42717f4450b42a6e5bbc6a`.
Patch SHA-256:
`374560671c0ea04ed702f5d04e2db0a6871718aa324acd15b29d18537bd0cf46`.

On the existing unequal-stamp refusal, `custody_change` records the dimension and
at most64 added/removed/changed region rows, their relative filenames, and old/new
byte sizes, precise modification timestamps and header hashes. The normal census
already admits at most32 files per dimension, so64 covers its complete union.
It also records the actual pending chunk keys and corresponding region filenames
from the **existing** same-tick native I/O mailbox query, bounded by the existing
4096-pending-chunk gate. It adds no mailbox future, sleep, retry, cancellation,
creation path, UUID, census exemption or cleanup rule. The5ms mailbox timeout is
unchanged. All existing count and NBT limits remain in place.

The original exception text is retained. The proposed receipt still represents
failure. A changed file is not treated as harmless because it is a placeholder;
empty/native-read creation and ordinary asynchronous saves remain hypotheses
until genuine current diagnostics identify the actual difference.

## Master integration

Only the master may apply this to the active source, build/install the next
candidate or allocate a live inspection window. Recompute the base hash first;
if it differs, review/rebase the narrow patch instead of forcing its application.

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath compat/control-bridge/src/worldfortwo/bridge/HarborCraftSupport.java
git apply --check proposals/fleet-craft-custody-diagnostics/HarborCraftSupport.patch
git apply proposals/fleet-craft-custody-diagnostics/HarborCraftSupport.patch
```

After exact hash review, build through the normal pinned bridge/candidate process
and obtain a serialized master-owned **inspect-only** window with fresh current
landing, water, body and UUID custody preimages. Preserve failed receipts and all
intent/reservation files. Do not rerun a create intent, reset identities or remove
occupants to trigger a passing result. This diagnostic patch does not resolve a
real changed census; it exposes the information needed for the next safe fix.

## Verification performed

Java21.0.10 compiled the complete proposed `HarborCraftSupport` class and a small
reflection probe against the exact cached candidate50 named compile APIs/classes.
There was no download, runtime installation, server/client start or world action.
The probe exercised unchanged stamps, changed size/mtime/header fields, added
zero-byte placeholder, removed region and the64-row cap. Both processes returned0.
`git apply --check` passed against the unchanged owned base. `verification.json`
retains exact source/patch/compiler-argument hashes and results.

The mailbox query's real server-thread/I/O behavior, actual refusal receipt,
cleanup, craft creation, sailing, boarding, multiplayer and restart are untested.
The reflection probe is source verification, not live Minecraft evidence.

To reproduce locally, first run the supplied ReserveGuard through Windows
PowerShell with8MiB C:/0D:. Then run `prepare_probe.py --primary <master-checkout>
--cached-javac-args <exact-retained-candidate50-compile-bridge/javac.args>`.
The script verifies the exact base before writing only this proposal's ignored
`.local/` probe outputs plus its patch/receipt. Earlier probe receipts are retained.
The live reserve check before this preparation passed with C118,128,959,488 and
D284,429,225,984 bytes free. Monitoring does not constrain external applications
or already-running writers.
