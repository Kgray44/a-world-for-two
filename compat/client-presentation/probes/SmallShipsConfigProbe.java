package net.neoforged.fml.config;

import com.electronwill.nightconfig.core.CommentedConfig;
import com.electronwill.nightconfig.core.UnmodifiableCommentedConfig;
import com.electronwill.nightconfig.core.io.ParsingMode;
import com.electronwill.nightconfig.core.concurrent.SynchronizedConfig;
import com.electronwill.nightconfig.core.InMemoryCommentedFormat;
import com.electronwill.nightconfig.toml.TomlFormat;
import com.google.gson.GsonBuilder;
import com.talhanation.smallships.config.SmallShipsConfig;
import com.talhanation.smallships.neoforge.common.CommonModBus;
import fuzs.forgeconfigapiport.neoforge.impl.forge.ForgeConfigSpecAdapter;
import net.minecraftforge.common.ForgeConfigSpec;
import net.neoforged.bus.api.BusBuilder;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.ModContainer;
import net.neoforged.fml.event.config.ModConfigEvent;
import net.neoforged.neoforgespi.language.IModInfo;
import worldfortwo.presentation.SmallShipsConfigLifecycle;

import java.io.ByteArrayInputStream;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Proxy;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.locks.ReentrantLock;
import java.util.function.Consumer;

/**
 * Actual pinned FML/Small Ships/ForgeConfigApiPort regression, without a game.
 * The test container/event listener are harness code. Config parsing, acceptance,
 * corrections, value caches, and the original disk migration are the real classes.
 * This does not run the Mixin transformer or demonstrate a native reconnect.
 */
public final class SmallShipsConfigProbe {
    private static final List<Map<String, Object>> cases = new ArrayList<>();
    private static int skipped, diskCallbacks;

    private static void require(boolean condition, String reason) {
        if (!condition) throw new AssertionError(reason);
    }

    private static void passed(String name, Object detail) {
        cases.add(Map.of("case", name, "status", "pass", "observed", detail));
    }

    private static CommentedConfig parse(String text) {
        var data = new SynchronizedConfig(InMemoryCommentedFormat.defaultInstance(), LinkedHashMap::new);
        data.bulkCommentedUpdate(view -> {
            TomlFormat.instance().createParser().parse(
                    new ByteArrayInputStream(text.getBytes(StandardCharsets.UTF_8)), view, ParsingMode.REPLACE);
        });
        return data;
    }

    private static String serverToml(Object cooldown, int schema) {
        String value = cooldown instanceof String ? "\"" + cooldown + "\"" : cooldown.toString();
        return "schematicVersion = " + schema + "\n[Ship.General]\nshipGeneralSailCooldown = " + value + "\n";
    }

    private static ModConfig config(ModConfig.Type type, RecordingSpec spec, Container container, String name) {
        return new ModConfig(type, spec, container, name, new ReentrantLock());
    }

    private static void dispatch(ModConfigEvent event) {
        if (SmallShipsConfigLifecycle.skipFileCallback(event)) {
            skipped++;
            return;
        }
        diskCallbacks++;
        originalCallback(event);
    }

    private static void originalCallback(ModConfigEvent event) {
        try {
            // The actual pinned handler is package-private; invoke its original
            // bytes without supplying a replacement handler implementation.
            var callback = CommonModBus.class.getDeclaredMethod("initRegisterConfigs", ModConfigEvent.class);
            callback.setAccessible(true);
            callback.invoke(null, event);
        } catch (InvocationTargetException wrapped) {
            Throwable actual = wrapped.getCause();
            if (actual instanceof RuntimeException runtime) throw runtime;
            if (actual instanceof Error error) throw error;
            throw new IllegalStateException("Original callback threw a checked failure", actual);
        } catch (ReflectiveOperationException error) {
            throw new IllegalStateException("Cannot inspect actual original callback", error);
        }
    }

    private static void synced(ModConfig config, Object cooldown) {
        ConfigTracker.acceptSyncedConfig(config, serverToml(cooldown, 6).getBytes(StandardCharsets.UTF_8));
    }

    private static void expectPathFailure(ModConfig config) {
        try {
            originalCallback(new ModConfigEvent.Reloading(config));
            throw new AssertionError("Negative control did not exercise the original non-file failure");
        } catch (IllegalStateException expected) {
            require(expected.getMessage().startsWith("Cannot call getFullPath() on non-file config "),
                    "Original callback failed for a different reason");
            passed("original-remote-callback-negative-control", "actual original getFullPath exception");
        }
    }

    private static void run(Path stage) throws Exception {
        var container = new Container("smallships");
        var spec = new RecordingSpec(SmallShipsConfig.SERVER_SPEC);
        ModConfig server = config(ModConfig.Type.SERVER, spec, container, "smallships-server.toml");
        container.listener = SmallShipsConfigProbe::dispatch;

        synced(server, 37);
        require(SmallShipsConfig.Server.shipGeneralSailCooldown.get() == 37, "Remote non-default value was lost");
        require(skipped == 1 && diskCallbacks == 0 && spec.accepted == 1, "Unexpected remote dispatch order");
        passed("remote-non-default-applied", SmallShipsConfig.Server.shipGeneralSailCooldown.get());
        expectPathFailure(server);

        synced(server, 73);
        require(SmallShipsConfig.Server.shipGeneralSailCooldown.get() == 73, "Previously cached value survived reload");
        require(spec.accepted == 2 && skipped == 2 && diskCallbacks == 0, "Second payload was not accepted first");
        passed("second-remote-payload-invalidates-getter-cache", SmallShipsConfig.Server.shipGeneralSailCooldown.get());

        synced(server, -999);
        int corrected = SmallShipsConfig.Server.shipGeneralSailCooldown.get();
        require(corrected >= 0 && corrected <= 1000 && corrected != -999, "Out-of-range value was not corrected");
        require(spec.isCorrect(server.getLoadedConfig().config()), "Corrected remote data does not satisfy real spec");
        require(server.getLoadedConfig().config().getInt("Ship.General.shipGeneralSailCooldown") == corrected,
                "Getter does not match accepted data");
        passed("out-of-range-remote-value-corrected-by-real-spec", corrected);

        synced(server, "wrong type");
        require(SmallShipsConfig.Server.shipGeneralSailCooldown.get() == 30, "Wrong type was not corrected to real default");
        passed("wrong-type-remote-value-corrected-by-real-spec", SmallShipsConfig.Server.shipGeneralSailCooldown.get());

        server.setConfig(new LoadedConfig(parse(serverToml(82, 6)), null, server), ModConfigEvent.Loading::new);
        require(SmallShipsConfig.Server.shipGeneralSailCooldown.get() == 82, "Pathless Loading lost its applied value");
        require(skipped == 5 && diskCallbacks == 0, "Pathless Loading reached disk callback");
        passed("pathless-server-loading-retains-values", SmallShipsConfig.Server.shipGeneralSailCooldown.get());

        Field cached = ForgeConfigSpec.ConfigValue.class.getDeclaredField("cachedValue");
        cached.setAccessible(true);
        require(cached.get(SmallShipsConfig.Server.shipGeneralSailCooldown) != null, "Cache negative control not primed");
        server.setConfig(null, ModConfigEvent.Unloading::new);
        require(!SmallShipsConfig.SERVER_SPEC.isLoaded(), "Real spec remains attached after Unloading");
        require(cached.get(SmallShipsConfig.Server.shipGeneralSailCooldown) == null, "Unloading retained stale cache");
        require(skipped == 6 && diskCallbacks == 0, "Unloading reached disk callback");
        passed("unloading-detaches-and-clears-real-cache", true);

        Path fixture = Files.createDirectory(stage.resolve("fixtures"));
        Path local = fixture.resolve("smallships-server.toml");
        byte[] first = serverToml(91, 1).getBytes(StandardCharsets.UTF_8);
        Files.write(local, first);
        var localSpec = new RecordingSpec(SmallShipsConfig.SERVER_SPEC);
        ModConfig disk = config(ModConfig.Type.SERVER, localSpec, container, local.getFileName().toString());
        disk.setConfig(new LoadedConfig(parse(new String(first, StandardCharsets.UTF_8)), local, disk), ModConfigEvent.Loading::new);
        Path backup = fixture.resolve("smallships-server-sv1.toml.bak");
        require(Files.isRegularFile(backup) && Arrays.equals(Files.readAllBytes(backup), first),
                "Original disk migration did not preserve exact old-schema backup");
        require(localSpec.lastDiskCorrection != null && localSpec.lastDiskCorrection.getInt("schematicVersion") == 2,
                "Original old-schema migration did not execute");
        require(SmallShipsConfig.Server.shipGeneralSailCooldown.get() == 91, "Disk Loading's applied value changed");
        require(Arrays.equals(Files.readAllBytes(local), first), "Probe changed original callback's disk write behavior");
        passed("file-server-loading-runs-original-old-schema-migration", Map.of("backup_exact", true, "migrated_schema", 2));

        byte[] second = serverToml(92, 1).getBytes(StandardCharsets.UTF_8);
        Files.write(local, second);
        localSpec.lastDiskCorrection = null;
        disk.setConfig(new LoadedConfig(parse(new String(second, StandardCharsets.UTF_8)), local, disk), ModConfigEvent.Reloading::new);
        Path secondBackup = fixture.resolve("smallships-server-sv1-1.toml.bak");
        require(Files.isRegularFile(secondBackup) && Arrays.equals(Files.readAllBytes(secondBackup), second)
                && Arrays.equals(Files.readAllBytes(backup), first), "Original Reloading migration backup behavior changed");
        require(localSpec.lastDiskCorrection != null && localSpec.lastDiskCorrection.getInt("schematicVersion") == 2,
                "Original Reloading migration was skipped");
        require(SmallShipsConfig.Server.shipGeneralSailCooldown.get() == 92, "Disk Reloading retained stale value");
        passed("file-server-reloading-runs-original-migration-and-retains-backups", true);

        Path clientPath = fixture.resolve("smallships-client.toml");
        String clientToml = "schematicVersion = 3\n[Ship]\nshipModSpeedUnit = 2\n";
        Files.writeString(clientPath, clientToml, StandardCharsets.UTF_8);
        var clientSpec = new RecordingSpec(SmallShipsConfig.CLIENT_SPEC);
        ModConfig client = config(ModConfig.Type.CLIENT, clientSpec, container, clientPath.getFileName().toString());
        client.setConfig(new LoadedConfig(parse(clientToml), clientPath, client), ModConfigEvent.Loading::new);
        require(clientSpec.lastDiskCorrection != null && SmallShipsConfig.Client.shipModSpeedUnit.get() == 2,
                "Legitimate file-backed CLIENT Loading was intercepted");
        passed("file-client-loading-remains-original", SmallShipsConfig.Client.shipModSpeedUnit.get());
        clientToml = "schematicVersion = 3\n[Ship]\nshipModSpeedUnit = 3\n";
        Files.writeString(clientPath, clientToml, StandardCharsets.UTF_8);
        clientSpec.lastDiskCorrection = null;
        client.setConfig(new LoadedConfig(parse(clientToml), clientPath, client), ModConfigEvent.Reloading::new);
        require(clientSpec.lastDiskCorrection != null && SmallShipsConfig.Client.shipModSpeedUnit.get() == 3,
                "Legitimate CLIENT Reloading was intercepted or retained a cached value");
        passed("file-client-reloading-remains-original", SmallShipsConfig.Client.shipModSpeedUnit.get());
        client.setConfig(null, ModConfigEvent.Unloading::new);
        require(!SmallShipsConfig.CLIENT_SPEC.isLoaded() && cached.get(SmallShipsConfig.Client.shipModSpeedUnit) == null,
                "Client Unloading did not detach or clear its real cache");
        passed("client-unloading-detaches-without-disk-callback", true);

        // Predicate boundaries use real ModConfig objects but deliberately do not
        // call the original broken handler for these invalid/unsupported states.
        container.listener = null;
        ModConfig detached = config(ModConfig.Type.SERVER, spec, container, "detached.toml");
        require(!SmallShipsConfigLifecycle.skipFileCallback(new ModConfigEvent.Reloading(detached)), "Detached Reloading silenced");
        require(!SmallShipsConfigLifecycle.skipFileCallback(new ModConfigEvent.Loading(detached)), "Detached Loading silenced");
        passed("detached-loading-and-reloading-are-not-silenced", true);

        Path missing = fixture.resolve("missing-server.toml");
        detached.setConfig(new LoadedConfig(parse(serverToml(95, 6)), missing, detached), ModConfigEvent.Loading::new);
        require(!Files.exists(missing) && !SmallShipsConfigLifecycle.skipFileCallback(new ModConfigEvent.Reloading(detached)),
                "Missing legitimate file path was misclassified as remote");
        passed("missing-file-path-still-reaches-original-callback", true);

        ModConfig common = config(ModConfig.Type.COMMON, spec, container, "common.toml");
        common.setConfig(new LoadedConfig(parse(serverToml(96, 6)), null, common), ModConfigEvent.Loading::new);
        require(!SmallShipsConfigLifecycle.skipFileCallback(new ModConfigEvent.Reloading(common)), "Non-file COMMON was intercepted");
        client.setConfig(new LoadedConfig(parse(clientToml), null, client), ModConfigEvent.Loading::new);
        require(!SmallShipsConfigLifecycle.skipFileCallback(new ModConfigEvent.Reloading(client)), "Non-file CLIENT was intercepted");
        var unrelated = new Container("unrelated_probe");
        ModConfig foreign = config(ModConfig.Type.SERVER, spec, unrelated, "other.toml");
        foreign.setConfig(new LoadedConfig(parse(serverToml(97, 6)), null, foreign), ModConfigEvent.Loading::new);
        require(!SmallShipsConfigLifecycle.skipFileCallback(new ModConfigEvent.Reloading(foreign))
                && !SmallShipsConfigLifecycle.skipFileCallback(new ModConfigEvent.Unloading(foreign)), "Foreign config intercepted");
        passed("common-and-other-mod-configs-remain-outside-policy", true);

        ModConfig exceptional = config(ModConfig.Type.SERVER, spec, container, "exceptional.toml");
        exceptional.setConfig(new LoadedConfig(parse(serverToml(98, 6)), null, exceptional), ModConfigEvent.Loading::new);
        // ModConfig is final. A throw-once value exercises an unrelated failure
        // while its real getFullPath formats the loaded record, without mocking
        // or replacing that implementation or a final class.
        var fault = new FormatFault();
        exceptional.getLoadedConfig().config().set("probeFormattingFault", fault);
        var unrelatedFailure = new IllegalStateException("unrelated path failure");
        fault.arm(unrelatedFailure);
        requireRethrown(exceptional, unrelatedFailure);
        var forgedMessage = new IllegalStateException("Cannot call getFullPath() on non-file config "
                + exceptional.getLoadedConfig() + " at path " + exceptional.getFileName());
        fault.arm(forgedMessage);
        requireRethrown(exceptional, forgedMessage);
        exceptional.getLoadedConfig().config().remove("probeFormattingFault");
        passed("unrelated-and-forged-message-path-errors-are-rethrown", true);
        require(diskCallbacks == 4, "Unexpected callbacks entered or legitimate file callbacks were skipped");
        require(spec.accepted >= 7, "Real adapter acceptance was not exercised");
    }

    private static void requireRethrown(ModConfig config, IllegalStateException failure) {
        try {
            SmallShipsConfigLifecycle.skipFileCallback(new ModConfigEvent.Reloading(config));
            throw new AssertionError("Unrelated getFullPath failure was swallowed");
        } catch (IllegalStateException actual) {
            require(actual == failure, "Original unrelated failure was replaced");
        }
    }

    private static final class FormatFault {
        private IllegalStateException failure;
        void arm(IllegalStateException value) { failure = value; }
        @Override public String toString() {
            if (failure != null) {
                IllegalStateException actual = failure;
                failure = null;
                throw actual;
            }
            return "probe-safe-formatting-value";
        }
    }

    /** A delegating spy; all validation/application is the actual pinned adapter. */
    private static final class RecordingSpec implements IConfigSpec {
        final ForgeConfigSpecAdapter actual;
        int accepted;
        CommentedConfig lastDiskCorrection;
        RecordingSpec(ForgeConfigSpec spec) { actual = new ForgeConfigSpecAdapter(spec); }
        @Override public boolean isEmpty() { return actual.isEmpty(); }
        @Override public void validateSpec(ModConfig config) { actual.validateSpec(config); }
        @Override public boolean isCorrect(UnmodifiableCommentedConfig config) { return actual.isCorrect(config); }
        @Override public void correct(CommentedConfig config) { actual.correct(config); lastDiskCorrection = config; }
        @Override public void acceptConfig(ILoadedConfig config) { actual.acceptConfig(config); accepted++; }
    }

    /** A real FML container and event bus with a test-owned listener. */
    private static final class Container extends ModContainer {
        final IEventBus bus = BusBuilder.builder().build();
        Consumer<ModConfigEvent> listener;
        Container(String id) {
            super((IModInfo) Proxy.newProxyInstance(IModInfo.class.getClassLoader(), new Class<?>[]{IModInfo.class},
                    (proxy, method, args) -> {
                        if (method.getName().equals("getModId") || method.getName().equals("toString")) return id;
                        if (method.getName().equals("hashCode")) return System.identityHashCode(proxy);
                        if (method.getName().equals("equals")) return proxy == args[0];
                        throw new UnsupportedOperationException("Unexpected test ModInfo access: " + method.getName());
                    }));
            bus.addListener(this::onConfig);
        }
        void onConfig(ModConfigEvent event) { if (listener != null) listener.accept(event); }
        @Override public IEventBus getEventBus() { return bus; }
    }

    private static String source(Class<?> type) throws Exception {
        return Path.of(type.getProtectionDomain().getCodeSource().getLocation().toURI()).toAbsolutePath().toString();
    }

    public static void main(String[] args) throws Throwable {
        Path stage = Path.of(args[0]).toAbsolutePath();
        var result = new LinkedHashMap<String, Object>();
        result.put("format", "awft-smallships-config-probe:1");
        result.put("cases", cases);
        result.put("boundary", "Actual pinned config classes and original migration; mixin transformation and native reconnect NOT exercised");
        try {
            net.neoforged.fml.loading.FMLPaths.loadAbsolutePaths(stage);
            result.put("class_sources", Map.of("policy", source(SmallShipsConfigLifecycle.class),
                    "smallships", source(SmallShipsConfig.class), "original_callback", source(CommonModBus.class),
                    "adapter", source(ForgeConfigSpecAdapter.class), "fml", source(ModConfig.class),
                    "guava", source(com.google.common.base.Splitter.class)));
            run(stage);
            result.put("status", "pass");
            result.put("passed_cases", cases.size());
            result.put("skipped_file_callbacks", skipped);
            result.put("original_disk_callbacks", diskCallbacks);
        } catch (Throwable error) {
            result.put("status", "failed");
            result.put("error_type", error.getClass().getName());
            result.put("error", String.valueOf(error.getMessage()));
            throw error;
        } finally {
            Files.writeString(stage.resolve("java-result.json"), new GsonBuilder().setPrettyPrinting().create().toJson(result)
                    + "\n", StandardCharsets.UTF_8);
        }
    }
}
