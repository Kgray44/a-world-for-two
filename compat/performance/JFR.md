# Retained JFR measurements

`python -B -m tools.performance_jfr --home <owned construction home> --recording <private stopped.jfr> --pid <native PID> --process-start-ms <native JVM birth>`
reads an existing recording without attaching to a game or starting/stopping any
recording. The expected PID and start are independently obtained from the master's
runtime receipt. Embedded `jdk.JVMInformation` must agree; absent or conflicting
information refuses. This check does not authenticate a user-authored recording or
prove its candidate/workload. Retain the master's capture provenance separately.

The reader requires a stable ordinary file of at most64MiB inside the owned
construction home. It hashes before and after, caps250,000 events/128 status groups,
uses a30-second cooperative reader deadline and a45-second owned-process limit.
Its compiler uses128MiB and reader96MiB, each with two processors;1.5GiB physical
and Windows commit headroom is required before either starts. Each invocation
forecasts4MiB C:/64MiB D: through ReserveGuard and writes a unique private staging
folder. Failed receipts and inputs remain preserved. It does not copy or delete
recordings, change configuration, control Minecraft, or use a modloader/network.
The storage monitor does not constrain external applications/existing game writers.

`--self-test` creates only a small **synthetic JDK** recording in that new private
folder, then exercises the same reader. Its events use the native field schema but
are not Minecraft observations. The fixture checks exact embedded PID/birth,
missing provenance, invalid input, absent timing metrics, status/read event counts,
private-coordinate exclusion and distribution overflow. Over4096 retained samples
per group withholds percentiles while preserving observed count/sum/maximum.

Reported scopes:

- `minecraft.ChunkGeneration`: individual native generation-status durations by
  dimension/status, using the actual JFR field names `level` and `status`. These
  names differ from the Java `targetStatus` member. Parallel statuses overlap;
  summing them cannot establish elapsed time to a FULL chunk or packet arrival.
- `jdk.GarbageCollection`: recorded collection-event durations, which can include
  concurrent work. Root `jdk.GCPhasePause` events are reported separately as pause
  scopes. Server recordings cannot substitute for client GC observations.
- `minecraft.ChunkRegionRead`: observed read count and compressed-byte count.
  **Minecraft1.21.1 commits this event immediately without begin/end timing. Its
  duration cannot be used as chunk-load latency.** The installed `JfrProfiler`
  bytecode establishes that native behavior.
- `jdk.FileRead`: recorded individual `.mca`/`.mcc` file-read operation durations.
  These exclude queues, decompression, chunk publication and client arrival; they
  are not complete chunk-load times. Other file paths are discarded from output.

Missing events do not prove zero activity. Event-type registration alone does not
prove that a recording enabled the event throughout its workload. Empty duration
distributions keep mean/max/sum unavailable. No global FPS, chunk-load, gameplay or
strict-parity acceptance is inferred. No paths, coordinates, player data or JVM
arguments are emitted by the summary. Raw JFR files can contain such private
material and must stay outside Git, alongside original capture/settings receipts.

`measurements.jfc` supplies a source-only, low-stack event selection for review.
It starts nothing. The master owns recording control and an exclusive runtime
window, binds the exact candidate/processes/workload and settings hashes, and
establishes bounded repository, duration and output allocations before starting.
The reader's64MiB input cap is not a quota for a live recording. Use a separate
approved recording for the client to collect its own GC/pause data. Existing tick
windows and client render telemetry remain necessary for gameplay context.
