# Native relocation R4: callback admission and one reviewed uninvoked intent

R3 native52 inspected all seven real Pippin objects successfully. Its MOVE then
refused before `dispatcher.execute`, with `clone_invoked=false`, after writing
the intent. The exact failed terminal is SHA36bc9697b81bf0c7ca760a1cfbc3178eeef151f3d507741199d8049d7f5a159b.
The original R3 source, terminal, intent and quarantine remain immutable.

R4 resolves the actual parsed callback during INSPECT and again before any
intent. It traverses at most eight real Brigadier contexts and requires one
synthetic hidden lambda whose prefix is `CloneCommands$$Lambda` and whose real
nest host, module and class loader are the pinned native CloneCommands class.
This handles Java21's `$$Lambda/0x...` name without trusting a name alone.
The actual callback class/module/loader/nest is recorded privately. The native
CloneCommands class hash remains mandatory. No command is executed by the probe.

Normal transactions keep their existing IDs and `intent.json`. A narrowly
scoped optional `uninvoked_resolution_review` reference admits only the one
Pippin transaction compiled in this proposal. Root must separately create and
review a JSON with format `awft-explicit-uninvoked-relocation-review:1`, created
timestamp, approved=true, allow_exactly_one_new_intent=true, transaction_id,
prior_intent_sha256, prior_quarantine_sha256 and prior_terminal reference.
The exact required hashes are constants in the original source and producer;
the producer never manufactures approval.

The helper verifies the immutable marked original terminal, exact old ledger
hashes, original callback-only error, zero owned/shared futures and tickets,
cleanup success and `clone_invoked=false`. Fresh actual full native tags, all
slots/components and object classes must equal both original snapshots. All
ordinary FULL/empty-server/geometry/model/entity/support/inspection gates still
apply. Only then can a new explicit MOVE append `uninvoked-resolution.json` and
one `intent-after-uninvoked-resolution.json`. Original files are not deleted,
renamed or overwritten. A second resolution or any invoked/uncertain clone is
refused. A partial append remains held; it is never automatically retried.

Completed/dependency checks use an allowlisted active-intent filename and its
exact hash, retaining compatibility with prior normal completion records.
Future uncertain failures use a separate quarantine file. Cleanup/publication
retained-busy behavior is unchanged.

New nested pins are clone_binding_class_sha256 and uninvoked_class_sha256. Use
the existing R2 binder followed by tools.native_eastern_relocation_r4.seal with
the actual built JAR and optional separately reviewed record. R4 calls the
current R3 resolver, including Root's patched-native-class selection. It only
emits an uninstalled immutable request; Root owns installation and execution.

The bounded fixture uses actual Brigadier and JVM hidden lambdas, including a
redirected context. It tests refusal of foreign and anonymous callbacks,
trailing/unresolved input, invoked/unclean/unfinished old outcomes, changed full
snapshots and stale/wrong transaction reviews. This is source/API evidence;
native callback inspection, explicit resolution and real clone remain unproved.
