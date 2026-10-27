package worldfortwo.packwiz;

import com.google.gson.*;
import java.io.StringReader;
import java.lang.reflect.*;
import java.nio.file.Path;
import java.util.*;
import java.util.concurrent.atomic.AtomicBoolean;

/** Calls actual pinned installer cache/Gson/CLI APIs. Does not invoke installer Main or GUI. */
public final class PinnedCacheProbe {
    private static int checks;
    private static void check(boolean value, String reason) { checks++; if (!value) throw new AssertionError(reason); }
    private static Object call(Object target, String name, Class<?>[] types, Object... values) throws Exception {
        return target.getClass().getMethod(name, types).invoke(target, values);
    }
    public static void main(String[] args) throws Exception {
        Class<?> manifestType = Class.forName("link.infra.packwiz.installer.metadata.ManifestFile");
        Class<?> fileType = Class.forName("link.infra.packwiz.installer.metadata.ManifestFile$File");
        Class<?> pathType = Class.forName("link.infra.packwiz.installer.target.path.PackwizFilePath");
        Class<?> parentPathType = Class.forName("link.infra.packwiz.installer.target.path.PackwizPath");
        Class<?> okioPath = Class.forName("okio.Path");
        Object okioCompanion = okioPath.getField("Companion").get(null);
        Object base = call(okioCompanion, "get", new Class<?>[]{String.class, boolean.class}, Path.of(args[0]).toAbsolutePath().toString(), false);
        Object folder = pathType.getConstructor(okioPath, String.class).newInstance(base, "");
        Object key = parentPathType.getMethod("resolve", String.class).invoke(folder, "mods/essential.pw.toml");
        Object location = parentPathType.getMethod("resolve", String.class).invoke(folder, "mods/essential.jar");
        Object pathsCompanion = parentPathType.getField("Companion").get(null);
        Object pathAdapter = call(pathsCompanion, "adapterRelativeTo", new Class<?>[]{parentPathType}, folder);
        Class<?> hashType = Class.forName("link.infra.packwiz.installer.metadata.hash.Hash");
        Class<?> hashFormatType = Class.forName("link.infra.packwiz.installer.metadata.hash.HashFormat");
        Object formatCompanion = hashFormatType.getField("Companion").get(null);
        Object format = call(formatCompanion, "fromName", new Class<?>[]{String.class}, "sha256");
        Object hash = hashFormatType.getMethod("fromString", String.class).invoke(format, "a".repeat(64));
        Object hashAdapter = Class.forName("link.infra.packwiz.installer.metadata.hash.Hash$TypeHandler").getConstructor().newInstance();
        Gson gson = new GsonBuilder().registerTypeAdapter(hashType, hashAdapter)
            .registerTypeAdapter(pathType, pathAdapter).enableComplexMapKeySerialization().create();
        Object manifest = manifestType.getConstructor().newInstance(), file = fileType.getConstructor().newInstance();
        check((Boolean) call(file, "getOptionValue", new Class<?>[]{}), "Native missing option defaults true; never infer false");
        call(file, "setOptional", new Class<?>[]{boolean.class}, true);
        call(file, "setOptionValue", new Class<?>[]{boolean.class}, false);
        call(file, "setHash", new Class<?>[]{hashType}, hash);
        call(file, "setLinkedFileHash", new Class<?>[]{hashType}, hash);
        call(file, "setCachedLocation", new Class<?>[]{pathType}, location);
        call(manifest, "setCachedFiles", new Class<?>[]{Map.class}, new HashMap<>(Map.of(key, file)));
        String serialized = gson.toJson(manifest, manifestType);
        Object restored = gson.fromJson(new StringReader(serialized), manifestType);
        Map<?, ?> cached = (Map<?, ?>) call(restored, "getCachedFiles", new Class<?>[]{});
        check(cached.size() == 1 && cached.containsKey(key), "Native path adapter preserves metadata key");
        Object restoredFile = cached.get(key);
        check((Boolean) call(restoredFile, "isOptional", new Class<?>[]{}) && !(Boolean) call(restoredFile, "getOptionValue", new Class<?>[]{}), "Native Gson preserves Essential-off choice");
        check(location.equals(call(restoredFile, "getCachedLocation", new Class<?>[]{})), "Actual cached artifact location preserved");
        check(hash.equals(call(restoredFile, "getHash", new Class<?>[]{})) && hash.equals(call(restoredFile, "getLinkedFileHash", new Class<?>[]{})), "Native metadata and linked-file hashes preserved");
        call(restoredFile, "backup", new Class<?>[]{});
        Object revert = call(restoredFile, "getRevert", new Class<?>[]{});
        check(!(Boolean) call(revert, "getOptionValue", new Class<?>[]{}), "Native rollback preserves optional false");
        Object absent = gson.fromJson(new StringReader("{}"), fileType);
        check((Boolean) call(absent, "getOptionValue", new Class<?>[]{}), "Absent JSON option is not a default-off selection");
        Set<String> fields = new HashSet<>();
        for (Field field : fileType.getDeclaredFields()) fields.add(field.getName());
        check(fields.equals(Set.of("revert", "hash", "linkedFileHash", "cachedLocation", "isOptional", "optionValue", "onlyOtherSide")), "Actual cache has no GUI/cancel provenance field");
        Class<?> optionType = Class.forName("link.infra.packwiz.installer.ui.data.IOptionDetails");
        AtomicBoolean choice = new AtomicBoolean(false);
        Object option = Proxy.newProxyInstance(optionType.getClassLoader(), new Class<?>[]{optionType}, (proxy, method, values) -> switch (method.getName()) {
            case "getName" -> "Essential fixture";
            case "getOptionDescription" -> "Fixture only";
            case "getOptionValue" -> choice.get();
            case "setOptionValue" -> { choice.set((Boolean) values[0]); yield null; }
            default -> throw new UnsupportedOperationException(method.getName());
        });
        Object cli = Class.forName("link.infra.packwiz.installer.ui.cli.CLIHandler").getConstructor().newInstance();
        Object cancelled = call(cli, "showOptions", new Class<?>[]{List.class}, List.of(option));
        check(choice.get() && Boolean.FALSE.equals(cancelled), "Actual CLI forces optional true without user choice");
        Object syntheticCancel = call(cli, "showExceptions", new Class<?>[]{List.class, int.class, boolean.class}, List.of(), 0, false);
        check(syntheticCancel.toString().equals("CANCEL"), "Actual CLI emits CANCEL with no GUI or user action");
        System.out.println("PINNED_CACHE_CHECKS=" + checks + " PASS; native cache API only, no install/GUI/network");
    }
}
