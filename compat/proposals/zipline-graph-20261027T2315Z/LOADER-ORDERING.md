# Exact FML constructor ordering

This is a source and local archive audit, without launching another JVM or
claiming client startup or a successful ride. The installed `loader-4.0.45.jar`
manifest declares build4.0.45 and Git commit `44982c69`.

At that exact commit, [ModSorter.addDependency](https://github.com/neoforged/FancyModLoader/blob/44982c69/loader/src/main/java/net/neoforged/fml/loading/ModSorter.java#L148)
adds an edge from the declaring mod to its present BEFORE target. It does not
limit these edges to required dependencies. Missing optional targets add no edge.
The loading dependency map contains the graph's predecessors. The corresponding
[LoadingModList.getDependencies](https://github.com/neoforged/FancyModLoader/blob/44982c69/loader/src/main/java/net/neoforged/fml/loading/LoadingModList.java#L174)
returns those predecessors, including another mod's BEFORE constraint.

[ModLoader.constructMods and dispatchParallelTask](https://github.com/neoforged/FancyModLoader/blob/44982c69/loader/src/main/java/net/neoforged/fml/ModLoader.java#L136)
run constructor tasks on the parallel executor, but each target task waits on
`CompletableFuture.allOf` its predecessor tasks. Therefore a present Chains
AFTER / Presentation BEFORE Zipline chain serializes these three constructors;
unrelated mods can still construct concurrently. Register directly inside the
guarded CLIENT presentation constructor. Registration in deferred work or a later
setup event would not inherit this guarantee.

The exact installed Ziplines1.5.3 `ZiplineMod.class`, SHA256
`071af18c5a0f98907a95093481e391b9b090da5f1eb5c00eef85e0fc084b3c29`,
has no static initializer and invokes `Zipline.init()V` directly in its constructor
via `invokestatic` constant-pool entry26. The bytecode was read without executing
the class. This supports the constructor ordering conclusion for the pinned
versions. Keep both optional version constraints, presence checks and lazy
provider loading. Do not place a Chains or Ziplines type in a common entrypoint.

No new mixin is necessary for these exact versions. If a future loader or mod
moves initialization outside this ordered constructor, re-audit it. A narrow
CLIENT-only optional `@Pseudo` injection at the stock
`ConnectibleChainsCompat.register()V` HEAD is the fallback registration point;
it must be separately reviewed, compiled and tested before use. A distance bias
would change provider selection and is not a substitute for correct ordering.

This audit does not establish that the graph provider has been selected in a
loaded client, that both endpoints are tracked/ticking, or that boarding,
handoffs, collision, multiplayer or restart persistence works. Those remain
native player gates.
