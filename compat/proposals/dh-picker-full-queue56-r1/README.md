# DH 3.3.3 full-queue yield compatibility candidate

This original compatibility transform changes one branch in the pinned native
`PriorityTaskPicker.startNextTask(boolean)`. It leaves the official DH JAR intact.
No upstream class or method body is packaged in the bridge.

The observed running pool had one active worker and sixteen queued tasks. Its
worker was constructing `RejectedExecutionException` instances while owning the
picker lock; the requeue scheduler waited for that same lock. The native catch
puts the exact rejected task back, then immediately retries without returning to
the worker's queue. The compatibility transform redirects that retry to the
method's existing normal unlock/return epilogue. It adds no return inside the try,
no rejection suppression, queue limit, worker count, or executor policy change.
Native task ownership, counters, shutdown handling and exception finalizers remain.

The plugin attests the complete local DH archive, original class digest and exact
executable method before mutation. It refuses an unknown archive, method, requeue
or finally structure. The sole changed instruction is the catch's existing GOTO
destination (native bytecode offset 162: old target 65, new target 223). The native
try/catch table and stack frames remain unchanged. The new target executes the
original `ReentrantLock.unlock()` and return.

The finite offline fixture loads the actual pinned native picker, executor and
tracked runnable. The original reproduces a lock-held full-queue rejection loop.
The repaired class drains all four commands exactly once, releases the lock,
returns counters/queues idle, runs work after a command exception and retains
normal shutdown rejection. It also verifies the sole branch change, unchanged
other methods, refusal without partial mutation and encoded NeoForge union-origin
attestation. A fixture-only silent config gate change establishes the full-queue
state; it changes no game configuration. The actual JVM verifier accepts the
transformed native class. This is offline evidence, not an in-game performance or
rendering acceptance.

Integrate only into a private mirror of exact bridge 0.6.55: add the plugin to
`src/worldfortwo/bridge`, the empty marker to `src/worldfortwo/bridge/mixin`, and
the separate JSON to resources. Add a second `[[mixins]]` entry for
`awft-dh-picker.mixins.json` in the private TOML. The config applies on the client.
Bump the private builder, TOML, manifest and thirteen helper authority strings to
0.6.56. Keep the original mixin configuration and all unrelated source unchanged.
The qualified private build preserves all 200 previous classes other than the
version-bearing `ControlBridge.class` byte for byte. Runtime installation and a
matched native trial belong to the parent; no installation was performed here.

The private qualification retains initial preparation/import failures, a native
config-initialization fixture failure, and a later extended-fixture 20-second
timeout. The final instrumented fixture passes all stated checks; the earlier
timeout remains an unexplained offline timing limit, not erased evidence.
