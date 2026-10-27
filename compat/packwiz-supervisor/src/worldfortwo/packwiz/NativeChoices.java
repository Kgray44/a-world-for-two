package worldfortwo.packwiz;

import java.io.*;
import java.lang.reflect.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.*;
import java.util.*;

/** Reads the actual unchanged installer cache through its exact pinned adapters. */
public final class NativeChoices {
    private NativeChoices() {}
    public record Attestation(String cacheSha256, Map<String, Boolean> choices, int nativeCacheEntries) {
        public Attestation { AttemptJournal.requireHash(cacheSha256); choices = Map.copyOf(choices); }
    }
    static Object call(Object target, String name, Class<?>[] types, Object... values) throws Exception {
        return target.getClass().getMethod(name, types).invoke(target, values);
    }
    static void tool(Path path, long bytes, String hash) throws Exception {
        if (Files.isSymbolicLink(path) || !Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS) || Files.size(path) != bytes)
            throw new IOException("Pinned official tool size/custody differs");
        try (InputStream input = Files.newInputStream(path, LinkOption.NOFOLLOW_LINKS)) {
            if (!HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(input.readNBytes((int) bytes + 1))).equals(hash))
                throw new IOException("Pinned official tool SHA-256 differs");
        }
    }
    public static Attestation attest(Path instance, Path installer, ReleaseSpec release) throws Exception {
        tool(installer, 4378828, AttemptJournal.INSTALLER_SHA256);
        Path root = instance.toRealPath(), cache = root.resolve("packwiz.json");
        byte[] raw = AttemptJournal.boundedRead(cache, 4 * 1024 * 1024);
        String value = StandardCharsets.UTF_8.newDecoder().onMalformedInput(java.nio.charset.CodingErrorAction.REPORT)
            .onUnmappableCharacter(java.nio.charset.CodingErrorAction.REPORT).decode(java.nio.ByteBuffer.wrap(raw)).toString();
        try (URLClassLoader loader = new URLClassLoader(new URL[]{installer.toUri().toURL()}, ClassLoader.getPlatformClassLoader())) {
            Class<?> pathType = loader.loadClass("link.infra.packwiz.installer.target.path.PackwizFilePath");
            Class<?> parentPath = loader.loadClass("link.infra.packwiz.installer.target.path.PackwizPath");
            Class<?> okioPath = loader.loadClass("okio.Path");
            Object base = call(okioPath.getField("Companion").get(null), "get", new Class<?>[]{String.class, boolean.class}, root.toString(), false);
            Object folder = pathType.getConstructor(okioPath, String.class).newInstance(base, "");
            Object adapter = call(parentPath.getField("Companion").get(null), "adapterRelativeTo", new Class<?>[]{parentPath}, folder);
            Class<?> hashType = loader.loadClass("link.infra.packwiz.installer.metadata.hash.Hash");
            Class<?> formatType = loader.loadClass("link.infra.packwiz.installer.metadata.hash.HashFormat");
            Object formatCompanion = formatType.getField("Companion").get(null);
            Class<?> builderType = loader.loadClass("com.google.gson.GsonBuilder");
            Object builder = builderType.getConstructor().newInstance();
            call(builder, "registerTypeAdapter", new Class<?>[]{java.lang.reflect.Type.class, Object.class}, hashType,
                loader.loadClass("link.infra.packwiz.installer.metadata.hash.Hash$TypeHandler").getConstructor().newInstance());
            call(builder, "registerTypeAdapter", new Class<?>[]{java.lang.reflect.Type.class, Object.class}, pathType, adapter);
            call(builder, "enableComplexMapKeySerialization", new Class<?>[]{});
            Object gson = call(builder, "create", new Class<?>[]{});
            Class<?> manifestType = loader.loadClass("link.infra.packwiz.installer.metadata.ManifestFile");
            Object manifest = call(gson, "fromJson", new Class<?>[]{Reader.class, Class.class}, new StringReader(value), manifestType);
            Object clientSide = loader.loadClass("link.infra.packwiz.installer.target.Side").getField("CLIENT").get(null);
            if (manifest == null || !clientSide.equals(call(manifest, "getCachedSide", new Class<?>[]{}))) throw new IOException("Native cache side is not client");
            if (!nativeHash(formatType, formatCompanion, "sha256", release.packSha256()).equals(call(manifest, "getPackFileHash", new Class<?>[]{}))
                || !nativeHash(formatType, formatCompanion, "sha256", release.indexSha256()).equals(call(manifest, "getIndexFileHash", new Class<?>[]{})))
                throw new IOException("Native completed pack/index hashes differ; ignored errors cannot count as success");
            Map<?, ?> files = (Map<?, ?>) call(manifest, "getCachedFiles", new Class<?>[]{});
            if (files == null || files.size() != release.entries().size()) throw new IOException("Native cache is not the complete exact release index");
            Map<Path, Object> rows = new HashMap<>();
            for (var entry : files.entrySet()) {
                Path key = ((Path) pathType.getMethod("getNioPath").invoke(entry.getKey())).toAbsolutePath().normalize();
                if (!key.startsWith(root) || rows.put(key, entry.getValue()) != null) throw new IOException("Unsafe/duplicate native cache key");
            }
            Map<String, Boolean> choices = new TreeMap<>();
            for (ReleaseSpec.Entry entry : release.entries()) {
                Object file = rows.remove(root.resolve(entry.metadata()));
                if (file == null) throw new IOException("Missing exact native metadata entry: " + entry.metadata());
                boolean optional = (Boolean) call(file, "isOptional", new Class<?>[]{}), otherSide = (Boolean) call(file, "getOnlyOtherSide", new Class<?>[]{});
                if (optional != entry.pin().optional() || otherSide == entry.client()) throw new IOException("Native optional/side policy differs");
                boolean selected = !optional || (Boolean) call(file, "getOptionValue", new Class<?>[]{});
                if (optional && entry.client()) choices.put(entry.pin().path(), selected);
                Object location = call(file, "getCachedLocation", new Class<?>[]{});
                Object metadataHash = call(file, "getHash", new Class<?>[]{}), linkedHash = call(file, "getLinkedFileHash", new Class<?>[]{});
                if (entry.client() && selected) {
                    if (location == null || !((Path) pathType.getMethod("getNioPath").invoke(location)).toAbsolutePath().normalize().equals(root.resolve(entry.pin().path()))
                        || !nativeHash(formatType, formatCompanion, "sha256", entry.metadataSha256()).equals(metadataHash)
                        || (entry.metafile() && !nativeHash(formatType, formatCompanion, entry.downloadHashFormat(), entry.downloadHash()).equals(linkedHash)))
                        throw new IOException("Native selected-file provenance differs: " + entry.metadata());
                } else {
                    if (location != null) throw new IOException("Disabled/wrong-side native file retains an artifact location");
                    if (metadataHash != null && !nativeHash(formatType, formatCompanion, "sha256", entry.metadataSha256()).equals(metadataHash))
                        throw new IOException("Disabled native metadata hash differs");
                    if (linkedHash != null && entry.metafile() && !nativeHash(formatType, formatCompanion, entry.downloadHashFormat(), entry.downloadHash()).equals(linkedHash))
                        throw new IOException("Disabled native linked hash differs");
                }
            }
            if (!rows.isEmpty() || !Arrays.equals(raw, AttemptJournal.boundedRead(cache, 4 * 1024 * 1024))) throw new IOException("Native choice cache changed during read");
            return new Attestation(AttemptJournal.sha256(raw), choices, files.size());
        }
    }
    private static Object nativeHash(Class<?> formatType, Object companion, String name, String hex) throws Exception {
        Object format = call(companion, "fromName", new Class<?>[]{String.class}, name);
        return formatType.getMethod("fromString", String.class).invoke(format, hex);
    }
}
