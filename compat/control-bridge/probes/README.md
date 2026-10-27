# Registrate construction regression fixture

These first-party probes exercise the exact pinned Registrate `1.3.0+67` implementation without starting a mod loader, Minecraft server, client, or world. They are outside `src/` and are excluded from the bridge JAR.

The control fixture reproduced entries that remain available through `getOptional(name)` but disappear from `getAll(registry)`, matching a planned item that registration iteration never binds. It does not identify the first caller in the failed live boot. The fixture using the production transformation retains all 2,048 entries in ten concurrent rounds and verifies that the JVM releases the instance monitor after an exception.

Use Java 21, the pinned installed named Minecraft/NeoForge libraries, the unchanged Registrate JAR nested in Create, and the original NeoForge access-transformer configuration. No dependency binaries or upstream configuration are included here. Perform the repository's storage admission first and use a new private staging folder; budget 16 MiB on its drive. Keep all diagnostic output private.

1. Compile these three Java files and `src/worldfortwo/bridge/RegistrateConcurrencyPlugin.java` against the installed libraries. Preserve the native launch file's `legacyClassPath` ordering. The installed named client API is also needed at the end of the classpath for Registrate's menu generic signatures; no client is launched.
2. Run `NativeATFixture <named-runtime.jar> <original-neoforge-at.cfg> <fresh-native-overlay>`. This applies actual NeoForge access rules only to private fixture classes, preserving installed JARs.
3. Run `TransformPinnedRegistrate <fresh-production-overlay>` with the original Registrate JAR on the classpath. It calls the production guard, emits one private transformed class, and rejects changed bodies, flags, descriptors, archive origins, and missing resources.
4. Run `RegistrateConcurrencyProbe` with the production overlay first, the native AT overlay second, then compiled probes and the original dependencies. The unwrapped concurrent calls must preserve every entry; exception cleanup must pass.

For an unmodified control, omit only the production overlay. The probe prints lookup and iteration losses and then fails its preservation assertion when the race reproduces. The ten-round bound is fixed; this is not an automatic retry or parameter sweep. All output classes, original dependencies and logs stay outside the repository.

Runtime activation and subsequent native startup remain separate acceptance checks. No probe changes registry order, bypasses holder binding, creates missing items, suppresses registration errors, or starts/restarts a server.
