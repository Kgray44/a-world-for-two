package worldfortwo.packwiz;

import java.io.*;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.security.*;
import java.util.*;

/** Read-only exact inventory/config verification, independent of installer exit/cache claims. */
public final class IntegrityGate {
    private IntegrityGate() {}
    public record Pin(String path, long bytes, Map<String, String> hashes, boolean optional, boolean defaultSelected) {
        public Pin {
            relative(path); hashes = Map.copyOf(hashes);
            if (bytes < 0 || hashes.isEmpty()) throw new IllegalArgumentException("Finite size and hashes required");
            for (var entry : hashes.entrySet()) {
                int length = switch (entry.getKey()) { case "SHA-256" -> 64; case "SHA-512" -> 128; case "SHA-1" -> 40; default -> throw new IllegalArgumentException("Unsupported hash"); };
                if (!entry.getValue().matches("[0-9a-f]{" + length + "}")) throw new IllegalArgumentException("Invalid hash");
            }
            if (!hashes.containsKey("SHA-256") && !hashes.containsKey("SHA-512")) throw new IllegalArgumentException("Strong pinned hash required");
        }
    }
    public record Inventory(String sha256, List<Pin> files, Set<String> exactDirectories, long maxTotalBytes) {
        public Inventory {
            AttemptJournal.requireHash(sha256); files = List.copyOf(files); exactDirectories = Set.copyOf(exactDirectories);
            if (files.isEmpty() || files.size() > 8192 || maxTotalBytes < 0) throw new IllegalArgumentException("Finite inventory required");
            Set<String> names = new HashSet<>(); long total = 0;
            for (Pin pin : files) {
                if (!names.add(pin.path.toLowerCase(Locale.ROOT))) throw new IllegalArgumentException("Duplicate/case-ambiguous pin");
                total = Math.addExact(total, pin.bytes);
            }
            if (total > maxTotalBytes) throw new IllegalArgumentException("Inventory exceeds byte cap");
            exactDirectories.forEach(IntegrityGate::relative);
        }
    }
    public record Result(boolean pass, int verifiedFiles, long verifiedBytes, String inventorySha256, List<String> errors) {
        public Result { errors = List.copyOf(errors); }
    }
    private static Path relative(String value) {
        if (value == null || value.isEmpty() || value.contains("\\") || value.contains(":") || value.contains("//") || value.chars().anyMatch(c -> c < 32))
            throw new IllegalArgumentException("Unsafe inventory path");
        Path path = Path.of(value);
        if (path.isAbsolute() || !path.normalize().equals(path) || path.startsWith("..") || value.equals(".")) throw new IllegalArgumentException("Unsafe inventory path");
        for (Path part : path) if (part.toString().endsWith(".") || part.toString().endsWith(" ")
            || part.toString().matches("(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\\..*)?")) throw new IllegalArgumentException("Ambiguous Windows path");
        return path;
    }
    private static Path safe(Path root, String relative) throws IOException {
        Path path = root; boolean absent = false;
        for (Path part : relative(relative)) {
            path = path.resolve(part);
            if (absent || !Files.exists(path, LinkOption.NOFOLLOW_LINKS)) { absent = true; continue; }
            BasicFileAttributes attributes = Files.readAttributes(path, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
            if (attributes.isSymbolicLink() || attributes.isOther() || !path.toRealPath().startsWith(root)) throw new IOException("Linked/nonregular inventory path");
        }
        return path;
    }
    public static Result verify(Path instance, Inventory inventory, Map<String, Boolean> optionalChoices) throws IOException {
        // Choices are an explicit input, never guessed from a CLI warning or a missing cache field.
        // A future integration must attest the real GUI/cache snapshot before supplying overrides.
        Path root = instance.toRealPath(); Map<String, Pin> all = new HashMap<>();
        Map<String, Boolean> choices = new HashMap<>(optionalChoices);
        Set<String> selected = new HashSet<>(); List<String> errors = new ArrayList<>();
        int verified = 0; long bytes = 0;
        for (Pin pin : inventory.files) {
            all.put(pin.path, pin);
        }
        for (var choice : choices.entrySet()) {
            if (!all.containsKey(choice.getKey()) || !all.get(choice.getKey()).optional || choice.getValue() == null)
                throw new IllegalArgumentException("Choice is not an optional inventory file");
        }
        for (Pin pin : inventory.files) if (!pin.optional || choices.getOrDefault(pin.path, pin.defaultSelected)) selected.add(pin.path);
        for (Pin pin : inventory.files) {
            try {
                Path path = safe(root, pin.path);
                if (!selected.contains(pin.path)) {
                    if (Files.exists(path, LinkOption.NOFOLLOW_LINKS)) errors.add("Optional-off file present: " + pin.path);
                    continue;
                }
                if (!Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS)) { errors.add("Missing/nonregular: " + pin.path); continue; }
                BasicFileAttributes before = Files.readAttributes(path, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
                if (before.size() != pin.bytes) { errors.add("Size mismatch: " + pin.path); continue; }
                Map<String, MessageDigest> digests = new HashMap<>();
                for (String algorithm : pin.hashes.keySet()) digests.put(algorithm, MessageDigest.getInstance(algorithm));
                long read = 0;
                try (InputStream input = Files.newInputStream(path, LinkOption.NOFOLLOW_LINKS)) {
                    byte[] chunk = new byte[65536]; int count;
                    while ((count = input.read(chunk)) != -1) {
                        read += count;
                        if (read > pin.bytes) throw new IOException("File grew beyond pin");
                        for (MessageDigest digest : digests.values()) digest.update(chunk, 0, count);
                    }
                }
                BasicFileAttributes after = Files.readAttributes(path, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
                boolean match = read == pin.bytes && before.size() == after.size()
                    && before.lastModifiedTime().equals(after.lastModifiedTime()) && Objects.equals(before.fileKey(), after.fileKey());
                for (var entry : digests.entrySet()) match &= HexFormat.of().formatHex(entry.getValue().digest()).equals(pin.hashes.get(entry.getKey()));
                if (!match) errors.add("Hash/change mismatch: " + pin.path);
                else { verified++; bytes = Math.addExact(bytes, read); }
            } catch (IOException | NoSuchAlgorithmException ex) { errors.add("Unreadable/unsafe: " + pin.path); }
        }
        int discovered = 0;
        for (String directory : inventory.exactDirectories) {
            Path base = safe(root, directory);
            if (!Files.exists(base, LinkOption.NOFOLLOW_LINKS)) continue;
            try (var paths = Files.walk(base)) { // Does not follow symbolic directories.
                for (Path path : (Iterable<Path>) paths::iterator) {
                    if (++discovered > 32768) throw new IOException("Managed inventory scan exceeds bound");
                    String name = root.relativize(path).toString().replace('\\', '/');
                    safe(root, name);
                    if (Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS) && !selected.contains(name)) errors.add("Unexpected managed file: " + name);
                }
            }
        }
        return new Result(errors.isEmpty(), verified, bytes, inventory.sha256, errors);
    }
}
