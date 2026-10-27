package worldfortwo.packwiz;

import java.io.*;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** Complete, build-bound index/lock inventory. Never accepted from runtime arguments. */
public record ReleaseSpec(String version, URI packUrl, String packSha256, String indexSha256,
                          String lockSha256, String inventorySha256, List<Entry> entries) {
    static final int MAX_SPEC = 2 * 1024 * 1024;
    public record Entry(String metadata, String metadataSha256, boolean metafile,
                        IntegrityGate.Pin pin, String side, String downloadHashFormat, String downloadHash) {
        public Entry {
            new IntegrityGate.Pin(metadata, 0, Map.of("SHA-256", metadataSha256), false, true);
            if (!Set.of("client", "both", "server").contains(side)) throw new IllegalArgumentException("Unknown side");
            if (!Set.of("sha256", "sha512").contains(downloadHashFormat)
                || !downloadHash.equals(pin.hashes().get(downloadHashFormat.equals("sha512") ? "SHA-512" : "SHA-256")))
                throw new IllegalArgumentException("Exact strong native download hash required");
            if (!metafile && (!metadata.equals(pin.path()) || !side.equals("both") || pin.optional()
                || !downloadHash.equals(metadataSha256))) throw new IllegalArgumentException("Raw config identity differs");
        }
        boolean client() { return !side.equals("server"); }
    }
    public ReleaseSpec {
        Objects.requireNonNull(packUrl); entries = List.copyOf(entries);
        for (String hash : List.of(packSha256, indexSha256, lockSha256, inventorySha256)) AttemptJournal.requireHash(hash);
        if (!version.matches("0\\.1\\.0-candidate\\.[1-9][0-9]{0,4}")
            || !packUrl.toString().equals("https://kgray44.github.io/a-world-for-two/releases/" + version + "/pack.toml"))
            throw new IllegalArgumentException("Exact immutable public candidate URL required");
        if (entries.isEmpty() || entries.size() > 8192) throw new IllegalArgumentException("Finite complete inventory required");
        Set<String> metadata = new HashSet<>(), destinations = new HashSet<>(); int optional = 0;
        for (Entry entry : entries) {
            if (!metadata.add(entry.metadata().toLowerCase(Locale.ROOT))
                || !destinations.add(entry.pin().path().toLowerCase(Locale.ROOT))) throw new IllegalArgumentException("Duplicate/case-ambiguous release member");
            if (entry.pin().optional()) {
                optional++;
                if (!entry.metadata().equals("mods/essential.pw.toml") || entry.pin().defaultSelected() || !entry.side().equals("client"))
                    throw new IllegalArgumentException("Only reviewed Essential default-off policy is supported");
            }
        }
        if (optional != 1) throw new IllegalArgumentException("Explicit Essential default-off policy required");
        new IntegrityGate.Inventory(inventorySha256, entries.stream().filter(Entry::client).map(Entry::pin).toList(),
            Set.of("mods", "shaderpacks", "resourcepacks", "config/paxi/datapacks"), 4L * 1024 * 1024 * 1024);
    }
    public IntegrityGate.Inventory inventory() {
        List<IntegrityGate.Pin> selected = entries.stream().filter(Entry::client).map(Entry::pin).toList();
        return new IntegrityGate.Inventory(inventorySha256, selected,
            Set.of("mods", "shaderpacks", "resourcepacks", "config/paxi/datapacks"), 4L * 1024 * 1024 * 1024);
    }
    static String text(DataInputStream input) throws IOException {
        int size = input.readInt(); if (size < 0 || size > 4096) throw new IOException("Oversized inventory string");
        byte[] bytes = input.readNBytes(size); if (bytes.length != size) throw new EOFException("Truncated inventory string");
        String value = new String(bytes, StandardCharsets.UTF_8);
        if (!Arrays.equals(value.getBytes(StandardCharsets.UTF_8), bytes)) throw new IOException("Invalid UTF-8 inventory");
        return value;
    }
    public static ReleaseSpec read(byte[] raw) throws IOException {
        if (raw.length > MAX_SPEC) throw new IOException("Inventory resource exceeds bound");
        try (DataInputStream input = new DataInputStream(new ByteArrayInputStream(raw))) {
            if (!text(input).equals("awft-supervisor-release:1")) throw new IOException("Unknown inventory format");
            String version = text(input), url = text(input), pack = text(input), index = text(input), lock = text(input);
            int count = input.readInt(); if (count < 1 || count > 8192) throw new IOException("Unbounded inventory count");
            List<Entry> entries = new ArrayList<>();
            for (int n = 0; n < count; n++) {
                String metadata = text(input), metadataHash = text(input); boolean metafile = input.readBoolean();
                String destination = text(input); long bytes = input.readLong(); String side = text(input);
                boolean optional = input.readBoolean(), defaultSelected = input.readBoolean();
                String downloadFormat = text(input), downloadHash = text(input); int hashes = input.readInt();
                if (hashes < 1 || hashes > 3) throw new IOException("Unbounded hash count");
                Map<String, String> pins = new HashMap<>();
                for (int h = 0; h < hashes; h++) if (pins.put(text(input), text(input)) != null) throw new IOException("Duplicate hash pin");
                entries.add(new Entry(metadata, metadataHash, metafile,
                    new IntegrityGate.Pin(destination, bytes, pins, optional, defaultSelected), side, downloadFormat, downloadHash));
            }
            if (input.read() != -1) throw new IOException("Trailing inventory payload");
            return new ReleaseSpec(version, URI.create(url), pack, index, lock, AttemptJournal.sha256(raw), entries);
        }
    }
    public static ReleaseSpec embedded() throws IOException {
        try (InputStream input = ReleaseSpec.class.getResourceAsStream("/awft-release.bin")) {
            if (input == null) throw new IOException("This JAR has no complete approved release inventory");
            return read(input.readNBytes(MAX_SPEC + 1));
        }
    }
}
