package com.volcanicmg.maphorizons.client.dh;

import java.util.*;
import java.util.function.BiFunction;

/** Original read-only coverage/projection helper. A coarse LOD is never a discovered chunk. */
public final class LodCoverage {
    public static final int MAX_DETAIL = 12;
    public static final int MAX_SECTIONS = 262_144;
    public static final int MAX_PENDING = 4096;
    private static final int BORDER = 30_000_000;
    public record Tile(int x, int z) {}
    /** DH database detail, not DhSectionPos detail (which is this + 6). */
    public record Section(int detail, int x, int z) {
        public Section {
            if (detail < 0 || detail > MAX_DETAIL) throw new IllegalArgumentException("Unsupported LOD detail");
            long span = 64L << detail;
            long minimum = Math.floorDiv(-BORDER, span), maximum = Math.floorDiv(BORDER, span);
            if (x < minimum || x > maximum || z < minimum || z > maximum) throw new IllegalArgumentException("LOD outside supported world");
        }
        public long firstBlockX() { return x * (64L << detail); }
        public long firstBlockZ() { return z * (64L << detail); }
        public int columnX(long blockX) { return column(blockX, firstBlockX()); }
        public int columnZ(long blockZ) { return column(blockZ, firstBlockZ()); }
        private int column(long block, long first) {
            if (block < -BORDER || block > BORDER) return -1;
            long value = Math.floorDiv(block - first, 1L << detail);
            return value >= 0 && value < 64 ? (int) value : -1;
        }
    }
    private final List<Set<Long>> levels;
    private final Set<Section> pending;
    private final int baseSize;
    private LodCoverage(List<Set<Long>> levels, Set<Section> pending, int baseSize) {
        this.levels = levels; this.pending = Set.copyOf(pending); this.baseSize = baseSize;
    }
    private static long key(int x, int z) { return ((long) x << 32) | (z & 0xffffffffL); }
    public static LodCoverage empty() { return from(List.of()); }
    public static LodCoverage from(Collection<Section> sources) {
        if (sources.size() > MAX_SECTIONS) throw new IllegalArgumentException("LOD index exceeds source cap");
        List<Set<Long>> buckets = new ArrayList<>();
        for (int d = 0; d <= MAX_DETAIL; d++) buckets.add(new HashSet<>());
        int count = 0;
        for (Section source : sources) if (buckets.get(source.detail).add(key(source.x, source.z))) count++;
        return new LodCoverage(buckets.stream().map(Set::copyOf).toList(), Set.of(), count);
    }
    private boolean inBase(Section source) { return levels.get(source.detail).contains(key(source.x, source.z)); }
    public boolean contains(Section source) { return inBase(source) || pending.contains(source); }
    public int size() { return baseSize + pending.size(); }
    public boolean isEmpty() { return size() == 0; }
    /** Copy only the bounded unsaved overlay; the large persisted index remains shared and immutable. */
    public LodCoverage observe(Collection<Section> sources) {
        Set<Section> next = new HashSet<>(pending);
        for (Section source : sources) if (!inBase(source)) next.add(source);
        if (next.size() > MAX_PENDING || baseSize + next.size() > MAX_SECTIONS)
            throw new IllegalStateException("LOD pending overlay exceeds work cap; keep previous index");
        return next.equals(pending) ? this : new LodCoverage(levels, next, baseSize);
    }
    /** A scan cannot erase listener updates which arrived before/during it but are not persisted yet. */
    public LodCoverage reconcilePending(LodCoverage previous) {
        return observe(previous.pending);
    }
    public Section sourceForTile(int tileX, int tileZ) {
        long blockX = tileX * 64L, blockZ = tileZ * 64L;
        if (blockX > BORDER || blockX + 63 < -BORDER || blockZ > BORDER || blockZ + 63 < -BORDER) return null;
        for (int detail = 0; detail <= MAX_DETAIL; detail++) {
            int x = Math.floorDiv(tileX, 1 << detail), z = Math.floorDiv(tileZ, 1 << detail);
            if (levels.get(detail).contains(key(x, z))) return new Section(detail, x, z);
            // Lookup does not expand coarse coverage into millions of fake leaf records.
            if (!pending.isEmpty()) {
                Section candidate;
                try { candidate = new Section(detail, x, z); }
                catch (IllegalArgumentException outside) { continue; }
                if (pending.contains(candidate)) return candidate;
            }
        }
        return null;
    }
    public boolean hasRegion(int regionX, int regionZ) {
        long firstX = regionX * 8L, firstZ = regionZ * 8L;
        if (firstX < -500_000 || firstX > 500_000 || firstZ < -500_000 || firstZ > 500_000) return false;
        for (int z = 0; z < 8; z++) for (int x = 0; x < 8; x++)
            if (sourceForTile((int) firstX + x, (int) firstZ + z) != null) return true;
        return false;
    }
    public static boolean intersectsAnyRegion(Collection<Section> sources, int regionX, int regionZ) {
        long x0 = regionX * 512L, z0 = regionZ * 512L;
        for (Section source : sources) {
            long span = 64L << source.detail;
            if (source.firstBlockX() <= x0 + 511 && source.firstBlockX() + span - 1 >= x0
                && source.firstBlockZ() <= z0 + 511 && source.firstBlockZ() + span - 1 >= z0) return true;
        }
        return false;
    }
    /** At most 64 real target tiles, grouped so one coarse native DTO is read once per region. */
    public Map<Section, List<Tile>> groups(int regionX, int regionZ) {
        Map<Section, List<Tile>> groups = new LinkedHashMap<>();
        long firstX = regionX * 8L, firstZ = regionZ * 8L;
        if (firstX < -500_000 || firstX > 500_000 || firstZ < -500_000 || firstZ > 500_000) return Map.of();
        for (int z = 0; z < 8; z++) for (int x = 0; x < 8; x++) {
            Tile tile = new Tile((int) firstX + x, (int) firstZ + z);
            Section source = sourceForTile(tile.x, tile.z);
            if (source != null) groups.computeIfAbsent(source, ignored -> new ArrayList<>()).add(tile);
        }
        groups.replaceAll((source, tiles) -> List.copyOf(tiles));
        return Collections.unmodifiableMap(groups);
    }
    @Override public boolean equals(Object other) {
        return other instanceof LodCoverage value && levels.equals(value.levels) && pending.equals(value.pending);
    }
    @Override public int hashCode() { return Objects.hash(levels, pending); }

    /** Memoizes the original renderer's parsed native columns; null is a legitimate sampled hole. */
    public static final class Samples<T> {
        private final int width;
        private final Object[] values;
        private final boolean[] seen;
        private final BiFunction<Integer, Integer, T> reader;
        public Samples(int width, BiFunction<Integer, Integer, T> reader) {
            if (width < 1 || width > 64) throw new IllegalArgumentException("Unsupported native column width");
            this.width = width; this.reader = Objects.requireNonNull(reader);
            values = new Object[width * width]; seen = new boolean[width * width];
        }
        @SuppressWarnings("unchecked") public T get(int x, int z) {
            if (x < 0 || z < 0 || x >= width || z >= width) return null;
            int index = z * width + x;
            if (!seen[index]) { values[index] = reader.apply(x, z); seen[index] = true; }
            return (T) values[index];
        }
    }
}
