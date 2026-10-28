# Native tree protection snapshot repair

The private candidate45 server watchdog trace stopped in Java21
`ImmutableCollections.SetN.probe`, reached from the `TreeGrowthScope` constructor.
The protected columns are packed `(x,z)` longs. Regular coordinate grids produce
many equal or adjacent `Long.hashCode` values; `Set.copyOf` places them in a
linear-probed immutable table. The constructor also used `Map.copyOf` for known
preimages, which has the same open-addressed collection risk.

The scope now copies into fresh `HashSet` and `HashMap` collections and exposes
unmodifiable wrappers. Both copies explicitly reject null inputs, keys and values,
preserving the old admission behavior. Caller collection mutation cannot change
the snapshots; map entries and collection iterators cannot mutate them. Exact
membership remains authoritative. No coordinate, protection, bee, rollback,
write-budget, thread-ownership, latched-refusal or scope-cleanup guard changed.
Both snapshots still finish before the scope is armed.

The remaining scope collections were reviewed: attempted writes use a
`LinkedHashSet`, expected states a `HashMap`, and rollback uses a bounded
`ArrayList`; the small constant soft-material set is not derived from grid keys.
The repair does not change the watchdog or allow a larger tree envelope.

The executable probe compiles the actual changed scope against the pinned Java21
and installed named Minecraft compile APIs, using the unchanged candidate45 bridge
only as a compile dependency. It creates no Level, entity, modloader or server.
Its instrumented comparable keys use the exact packed-column long hash. The old
Java21 `SetN` and `MapN` are exercised only on a bounded1,024-key grid; the large
path calls the production snapshot methods, never the old large immutable copy.

| Offline observation | Result |
| --- | --- |
| Old `SetN`,1,024 keys |514,144 equality calls |
| Hash-backed set snapshot, same keys |6,249 equality calls |
| Old `MapN`,1,024 keys |507,904 equality calls |
| Hash-backed map snapshot, same keys |6,180 equality calls |
| Production set+map copy and every membership/value check,131,072 keys |158.380ms |
| Caller isolation, mutation refusal, null refusal, foreign keys, empty input |Passed |
| JVM heap / reported processors |256MiB /2 |
| Focused source guard contracts |2 passed |

These are bounded offline collection results, not a Minecraft growth benchmark or
native candidate46 acceptance. The large map probe deliberately stresses generic
grid-key collisions; it does not instantiate native `BlockPos` or `BlockState`.
Native constructor/growth/cleanup still require the next reviewed runtime.

Reproduce with `compat/control-bridge/probes/probe_tree_growth_scope.py`, passing a
fresh owned D staging output, the reviewed bridge dependency SHA, and an existing
exact bridge `javac.args` classpath recipe. The runner checks the30GiB reserve,
sets Java heap256MiB and processor count2, bounds compilation45seconds and
execution30seconds, and retains failure logs and receipts. Its first isolated
compile failed on Windows argument-file path escaping; that failed output was
preserved. The corrected runner completed the probe without changing the runtime
JAR. The JVM heap bound is not a total-process RSS quota, and the reserve check
does not constrain unrelated applications or existing writers.
