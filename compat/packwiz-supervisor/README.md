# Packwiz supervisor — original source candidate

This Java 21 candidate now has an executable entry, a complete build-bound release
inventory, native optional-choice observation, a bounded process harness and an
independent installed-byte gate. **It is not integrated into Prism or a published
release. Packwiz installer Main and a fresh GUI installation have not been run.**
The official bootstrap 0.0.3 and installer 0.5.14 remain unchanged and pinned by
size and SHA-256. Their classes and third-party artifacts are never bundled in the
original supervisor JAR.

## Cancellation and success

GUI attempts never retry. A GUI/native nonzero exit remains failure, including a
DNS error. The pinned [GUI handler](https://github.com/packwiz/packwiz-installer/blob/v0.5.14/src/main/kotlin/link/infra/packwiz/installer/ui/gui/GUIHandler.kt)
can return zero when the user ignores a cancelled or failed update. Zero alone is
therefore insufficient: the runner requires the exact final native success line,
rejects recognized cancel/ignore/hash/download-error output, and then performs all
cache and artifact checks below. A genuine failed/cancelled attempt is retained;
it is never relabelled as successful or silently changed to CLI mode.

The native cache is observed through an isolated loader containing only the exact
pinned installer. Its real Gson/path/hash adapters parse `packwiz.json`. Completed
pack and index hashes, client side, every indexed metadata key, selected artifact
location and metadata/download hashes must match the embedded release. Effective
optional choices are recorded from that actual cache after a successful process;
this does not claim to audit individual checkbox input events. A missing native
`optionValue` means true, as the [pinned schema](https://github.com/packwiz/packwiz-installer/blob/v0.5.14/src/main/kotlin/link/infra/packwiz/installer/metadata/ManifestFile.kt)
specifies. It is never interpreted as Essential off.

Essential remains GUI default-off. The actual pinned [CLI option API](https://github.com/packwiz/packwiz-installer/blob/v0.5.14/src/main/kotlin/link/infra/packwiz/installer/ui/cli/CLIHandler.kt)
forces optional mods on. Consequently CLI mode requires explicit
`--headless-all-options-on` consent and checks that the resulting native choices
match. CLI installation while retaining an Essential-off selection is unsupported;
the supervisor does not seed or rewrite a cache to simulate that behavior.

## Complete release binding

The builder validates the complete canonical Packwiz pack/index/lock chain and
every indexed metafile and raw configuration/Paxi payload. It checks optional
metadata against the lock independently of the existing manifest validator.
Duplicate paths, incomplete inventories, weak-only download pins, changed files
and unknown optional policies refuse the build. The original binary descriptor is
embedded in the JAR; runtime arguments cannot replace it, change the release URL or
supply an incomplete inventory. Inputs are checked again after compilation so a
concurrent candidate change produces a retained failed build.

Only the immutable public candidate URL is supported. Before installation, bounded
HTTPS reads must match the embedded pack and index SHA-256 values. Redirects and
missing/unpublished versions refuse admission. After native completion,
`IntegrityGate` independently hashes every selected artifact and every indexed
static/config/Paxi file, checking exact sizes and all supplied hashes. Unexpected
files in managed artifact/Paxi directories and present optional-off files fail.
An exit code, native cache hit or successful recovery cannot replace this check.

This is intentionally an exact release gate. A managed configuration modified by
Minecraft or its owner can fail subsequent verification; the wrapper does not
silently delete, restore or exempt it. Native first-install and relaunch behavior
must be qualified before choosing any distribution/prelaunch integration.

## One narrow CLI recovery

Only a complete recognized pinned CLI DNS-only report can claim one recovery
credit. Normal observed exit 1, complete bounded output, closed owned process
resources, exact tools/inventory, explicit CLI choices and an unchanged actual
cache are required. Missing/truncated output, mixed errors, HTTP/hash failures,
unknown output, GUI mode, cancellation and ambiguous cleanup refuse recovery.
`CREATE_NEW` makes the credit atomic and persistent for that first receipt. A
recovery attempt cannot claim another credit. Both attempts use the same instance,
cache, mode, public release and choices; no cache deletion or seeding occurs.

Recognition establishes an observed DNS failure, not the underlying cause of the
prior bulk-download failures. Earlier direct-origin/redirect transport probes and
the preserved failed installs remain separate evidence.

## Process and evidence bounds

The unchanged bootstrap/installer run in one owned child JVM using the current
Java runtime. Windows uses `javaw.exe` to avoid creating console-host processes;
stdout/stderr still flow through the bounded capture pipe. Only the child-scoped
Java option-injection environment variables are removed; host settings are not
changed. An instance lock prevents simultaneous supervisor runs.

Each attempt has a 20-minute deadline and a 4 MiB log cap. The parent-approved
original fake-child fixture exercises the exact harness, including native exit 7,
owner interruption, timeout, excess output, owned descendant cleanup and stdout
reader reaping. Production expects no descendant helpers. It preserves unadmitted
processes, stops its own root, records uncertain cleanup and refuses success or
recovery. Tests clean up only their original children using actual PID plus
creation-time custody; no protected or unrelated process is terminated.

Private create-once attempt logs, receipts and completion seals preserve partial
failures. Final result seals bind the retained failure or verification record and
attempt receipt identities. Cache presence is recorded as existing/absent; neither
case is advertised as proof of a fresh install. The original native installer still
controls artifact transfers; these source checks are not an OS disk quota or a
proved real-install memory/transport benchmark.

## Developer build and remaining gates

```powershell
python -B -m tools.build_packwiz_supervisor
```

The bounded builder verifies C:/D: reserves, exact cached official tools, compiles
with Java 21 / 64 MiB / two processors, and runs policy, complete-inventory, actual
pinned-cache and original fake-child fixtures. It writes a fresh private staging
tree, retaining all failed attempts. Declared allocation is 1 MiB C: / 16 MiB D:;
the reserve monitor does not constrain unrelated applications or existing writers.
It performs no network, installer Main, GUI, game, Prism, export or publication
operation. Test fixtures are separate and never bundled.

The launchable source candidate accepts only this development entry contract:

```text
java -jar <reviewed-supervisor.jar> --instance <owned-minecraft-directory> --mode gui
```

The instance must already contain the exact official tools in `awft-tools/`.
No runtime command, exported instance or prelaunch setting has been changed.
Before distribution, the parent must review the frozen source, publish the exact
candidate chain, test genuine GUI cancel/close/ignore and optional choices, complete
an actual unseeded Prism download and config-sensitive relaunch, and qualify any
real CLI DNS recovery. The current fixtures establish their stated source/native
API/process behavior; they do not establish those installation or player gates.
