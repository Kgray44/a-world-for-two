"""Stage an exact MapHorizons read-only multi-resolution adapter; never build/deploy."""
from __future__ import annotations

import hashlib
from pathlib import Path

from control_room.common import REPO, UserError, atomic_write, digest

VERSION = '1.1.0-awft.2'
UPSTREAM_SHA256 = '1f24205f36b5a43a180e0c65a56c91fb0bda7f9de10c2a13d84598f5591abc4a'
RELATIVE = 'src/main/java/com/volcanicmg/maphorizons/client/dh/DhSource.java'
REGION_RELATIVE = 'src/main/java/com/volcanicmg/maphorizons/client/RegionColours.java'
REGION_SHA256 = '09efcd3269d7570227d0bb535713199242f47e1e3cff106d10e3bd5ec925b8fb'


def changed_source(raw):
    if hashlib.sha256(raw).hexdigest() != UPSTREAM_SHA256:
        raise UserError('MapHorizons refresh requires the exact reviewed author source')
    text = raw.decode('utf-8')
    def replace(before, after):
        nonlocal text
        if text.count(before) != 1:
            raise UserError('MapHorizons patch anchor is ambiguous or missing')
        text = text.replace(before, after)
    replace('boolean ceiling, int minY, int ceilingY) {',
            'boolean ceiling, int minY, int ceilingY, IndexRefresh refresh) {')
    replace('private record Dirty(ResourceLocation dim, long pos) {',
            'private record Dirty(ResourceLocation dim, FullDataSourceProviderV2 provider, long pos) {')
    replace('private static long summaryAt;', '''private static long summaryAt;
    private static int attachmentTicks;
    private static long coverageRefreshAt;
    private static boolean coverageChanged;''')
    replace('    private static final Map<ResourceLocation, Long2LongOpenHashMap> INDEX = new ConcurrentHashMap<>();\n', '')
    replace('if (a == null || a.mcLevel() != mc) tryAttach(mc);',
            '''if (a != null && (++attachmentTicks % 20 == 0) && !current(a)) {
                    detach(mc.dimension().location(), a);
                    a = null;
                }
                if (a == null || a.mcLevel() != mc) tryAttach(mc);
                a = LEVELS.get(mc.dimension().location());
                if (a != null) queueIndex(mc.dimension().location(), a);''')
    before = '''            Map<ResourceLocation, Long2LongOpenHashMap> changed = new HashMap<>();
            Map<ResourceLocation, LongOpenHashSet> regions = new HashMap<>();
            for (Dirty d; (d = DIRTY.poll()) != null; ) {
                Long2LongOpenHashMap idx = changed.computeIfAbsent(d.dim(),
                        k -> new Long2LongOpenHashMap(INDEX.getOrDefault(k, new Long2LongOpenHashMap())));
                int tx = DhSectionPos.getX(d.pos()), tz = DhSectionPos.getZ(d.pos());
                long key = Bits.tileRegionKey(tx, tz);
                idx.put(key, idx.get(key) | Bits.tileBit(tx, tz));
                regions.computeIfAbsent(d.dim(), k -> new LongOpenHashSet()).add(key);
            }
            INDEX.putAll(changed);
            // One refresh per region per tick, however many sections DH streamed in.
            regions.forEach((dim, keys) -> keys.forEach((long key) ->
                    RegionColours.refresh(dim, Bits.unpackX(key), Bits.unpackZ(key))));'''
    replace(before, '''            Map<ResourceLocation, List<LodCoverage.Section>> changed = new HashMap<>();
            for (Dirty d; (d = DIRTY.poll()) != null; ) {
                Attached owner = LEVELS.get(d.dim());
                if (owner == null || owner.provider() != d.provider()) continue;
                int detail = DhSectionPos.getDetailLevel(d.pos()) - LEAF;
                if (detail < 0 || detail > LodCoverage.MAX_DETAIL) continue;
                changed.computeIfAbsent(d.dim(), ignored -> new ArrayList<>()).add(
                        new LodCoverage.Section(detail, DhSectionPos.getX(d.pos()), DhSectionPos.getZ(d.pos())));
            }
            changed.forEach((dim, sections) -> {
                Attached owner = LEVELS.get(dim);
                if (owner == null) return;
                try { coverageChanged |= owner.refresh().observe(sections); }
                catch (IllegalStateException limit) {
                    // Retain known coverage. The completion-timed SQL refresh can catch up.
                    debug("pending coverage cap reached for {}; retaining previous snapshot", dim);
                }
                RegionColours.refreshCovered(dim, (rx, rz) -> LodCoverage.intersectsAnyRegion(sections, rx, rz));
            });
            long now = System.nanoTime();
            if (coverageChanged && (coverageRefreshAt == 0 || now - coverageRefreshAt >= 1_500_000_000L)) {
                coverageChanged = false;
                coverageRefreshAt = now;
                RegionColours.permissionsChangedAll();
            }''')
    replace('if (DhSectionPos.getDetailLevel(pos) == LEAF) DIRTY.add(new Dirty(dim, pos));',
            '''int detail = DhSectionPos.getDetailLevel(pos) - LEAF;
            if (detail >= 0 && detail <= LodCoverage.MAX_DETAIL) DIRTY.add(new Dirty(dim, provider, pos));''')
    replace('type.minY(), type.logicalHeight() - 1);',
            'type.minY(), type.logicalHeight() - 1, new IndexRefresh());')
    replace('if (old != null) old.provider().removeDataSourceUpdateListener(old.listener());',
            '''if (old != null) {
            old.refresh().invalidate();
            old.provider().removeDataSourceUpdateListener(old.listener());
        }''')
    replace('RegionColours.submit(() -> buildIndex(dim, a));', 'queueIndex(dim, a);')
    replace('if (!LEVELS.remove(dim, a)) return;',
            'if (!LEVELS.remove(dim, a)) return;\n        a.refresh().invalidate();')
    replace('        INDEX.remove(dim);\n', '')
    replace('INDEX.values().stream().allMatch(Long2LongOpenHashMap::isEmpty)',
            'LEVELS.values().stream().allMatch(value -> value.refresh().snapshot().isEmpty())')
    replace('INDEX.values().stream().mapToInt(Long2LongOpenHashMap::size).sum()',
            'LEVELS.values().stream().mapToInt(value -> value.refresh().snapshot().size()).sum()')
    replace('index regions={}', 'indexed native sections={}')
    start = text.index('    /** Worker: every leaf section in the DH database becomes a tile bit. */')
    end = text.index('    /** Any thread: does DH have any leaf data', start)
    text = text[:start] + '''    private static boolean current(Attached a) {
        AbstractDhWorld world = SharedApi.getAbstractDhWorld();
        if (world == null) return false;
        for (IDhLevel level : world.getAllLoadedLevels())
            if (level == a.level() && level.getFullDataProvider() == a.provider()) return true;
        return false;
    }

    private static void queueIndex(ResourceLocation dim, Attached a) {
        long token = a.refresh().begin(System.nanoTime());
        if (token == 0) return;
        try {
            RegionColours.submit(() -> {
                try { buildIndex(dim, a, token); }
                catch (Exception failure) {
                    if (LEVELS.get(dim) == a) LOG.warn("MapHorizons: bounded index refresh failed; previous index retained", failure);
                } finally { a.refresh().finish(token, System.nanoTime()); }
            });
        } catch (RuntimeException failure) {
            a.refresh().finish(token, System.nanoTime());
            throw failure;
        }
    }

    private static void buildIndex(ResourceLocation dim, Attached a, long token) throws Exception {
        LodCoverage scanned = LodCoverage.from(IndexRefresh.read(java.nio.file.Path.of(a.provider().repo.databaseFile.toString())));
        if (LEVELS.get(dim) != a || !a.refresh().owns(token) || !a.refresh().publish(token, scanned)) return;
        LOG.info("MapHorizons: refreshed read-only multi-resolution index for {}: {} native sections, details 0..{}",
                dim, a.refresh().snapshot().size(), LodCoverage.MAX_DETAIL);
        Minecraft.getInstance().execute(() -> {
            if (LEVELS.get(dim) != a) return;
            RegionColours.dropDimension(dim);
            RegionColours.permissionsChangedAll();
        });
    }

''' + text[end:]
    replace('''        Long2LongOpenHashMap idx = INDEX.get(dim);
        return idx != null && idx.get(Bits.pack(rx, rz)) != 0;''', '''        Attached a = LEVELS.get(dim);
        return a != null && a.refresh().snapshot().hasRegion(rx, rz);''')
    replace('''        Long2LongOpenHashMap idx = INDEX.get(dim);
        if (idx == null) return false;
        int tx = cx >> 2, tz = cz >> 2;
        return (idx.get(Bits.tileRegionKey(tx, tz)) & Bits.tileBit(tx, tz)) != 0;''', '''        Attached a = LEVELS.get(dim);
        return a != null && a.refresh().snapshot().sourceForTile(cx >> 2, cz >> 2) != null;''')
    replace('''        Long2LongOpenHashMap idx = INDEX.get(dim);
        return idx != null && (idx.get(Bits.tileRegionKey(tx, tz)) & Bits.tileBit(tx, tz)) != 0;''', '''        Attached a = LEVELS.get(dim);
        return a != null && a.refresh().snapshot().sourceForTile(tx, tz) != null;''')
    replace('''        Long2LongOpenHashMap idx = INDEX.get(dim);
        if (disabled || a == null || idx == null) return NOTHING;
        long mask = idx.get(regionKey);
        if (mask == 0) return NOTHING;''', '''        if (disabled || a == null) return NOTHING;
        LodCoverage idx = a.refresh().snapshot();
        var groups = idx.groups(Bits.unpackX(regionKey), Bits.unpackZ(regionKey));
        if (groups.isEmpty()) return NOTHING;
        int indexedTiles = groups.values().stream().mapToInt(List::size).sum();''')
    replace('''            for (int t = 0; t < 64; t++) {
                if ((mask & 1L << t) == 0) continue;
                int tx = rx * TILES + (t % TILES), tz = rz * TILES + (t / TILES);
                // Fresh source per read; must be closed. Missing sections come back empty.
                try (FullDataSourceV2 src = read(a, DhSectionPos.encode(LEAF, tx, tz))) {
                    if (src == null || src.isEmpty) {
                        emptyTiles++;
                        continue;
                    }
                    paintSection(a, src, tx, tz, rx, rz, c, !xaero);
                }
            }''', '''            for (var group : groups.entrySet()) {
                LodCoverage.Section source = group.getKey();
                long pos = DhSectionPos.encode((byte)(LEAF + source.detail()), source.x(), source.z());
                try (FullDataSourceV2 src = read(a, pos)) {
                    if (src == null || src.isEmpty) {
                        emptyTiles += group.getValue().size();
                        continue;
                    }
                    var samples = new LodCoverage.Samples<Column>(src.getWidthInDataColumns(),
                            (x, z) -> Column.of(src.getApiDataPointColumn(x, z), a));
                    for (LodCoverage.Tile tile : group.getValue())
                        paintSection(a, src, tile.x(), tile.z(), rx, rz, c, !xaero, source, samples);
                }
            }''')
    replace('Long.bitCount(mask), emptyTiles, painted, coarse,', 'indexedTiles, emptyTiles, painted, coarse,')
    replace('''                                     boolean dh) {
        int w = Math.min(64, src.getWidthInDataColumns());''', '''                                     boolean dh, LodCoverage.Section source, LodCoverage.Samples<Column> samples) {
        int w = 64;''')
    replace('''                Column col = Column.of(src.getApiDataPointColumn(x, z), a);
                if (col == null) continue;
                int bx = x0 + x, bz = z0 + z;''', '''                int bx = x0 + x, bz = z0 + z;
                int columnX = source.columnX(bx), columnZ = source.columnZ(bz);
                Column col = samples.get(columnX, columnZ);
                if (col == null) continue;''')
    replace('int si = FullDataSourceV2.relativePosToIndex(x, z);', 'int si = FullDataSourceV2.relativePosToIndex(columnX, columnZ);')
    replace('if (steps != null && si < steps.size() && steps.getByte(si) < FULL_STEP) {',
            'if (source.detail() > 0 || steps != null && si < steps.size() && steps.getByte(si) < FULL_STEP) {')
    replace('private static void readApron(Attached a, Long2LongOpenHashMap idx,', 'private static void readApron(Attached a, LodCoverage idx,')
    replace('private static void edge(Attached a, Long2LongOpenHashMap idx,', 'private static void edge(Attached a, LodCoverage idx,')
    replace('''        if ((idx.get(Bits.tileRegionKey(tx, tz)) & Bits.tileBit(tx, tz)) == 0) return;
        try (FullDataSourceV2 src = read(a, DhSectionPos.encode(LEAF, tx, tz))) {''', '''        LodCoverage.Section source = idx.sourceForTile(tx, tz);
        if (source == null) return;
        long pos = DhSectionPos.encode((byte)(LEAF + source.detail()), source.x(), source.z());
        try (FullDataSourceV2 src = read(a, pos)) {''')
    replace('''            int w = Math.min(64, src.getWidthInDataColumns());
            for (int j = 0; j < w; j++) {
                Column col = southRow ? Column.of(src.getApiDataPointColumn(j, w - 1), a)
                        : Column.of(src.getApiDataPointColumn(w - 1, j), a);''', '''            var samples = new LodCoverage.Samples<Column>(src.getWidthInDataColumns(),
                    (x, z) -> Column.of(src.getApiDataPointColumn(x, z), a));
            for (int j = 0; j < 64; j++) {
                long bx = tx * 64L + (southRow ? j : 63);
                long bz = tz * 64L + (southRow ? 63 : j);
                Column col = samples.get(source.columnX(bx), source.columnZ(bz));''')
    replace('        attachTries = 0;\n    }\n\n    private static boolean current',
            '        attachTries = 0;\n        coverageChanged = false;\n        coverageRefreshAt = 0;\n        attachmentTicks = 0;\n    }\n\n    private static boolean current')
    return text.encode('utf-8')


def changed_regions(raw):
    if hashlib.sha256(raw).hexdigest() != REGION_SHA256:
        raise UserError('MapHorizons region callback requires exact reviewed author source')
    text = raw.decode('utf-8')
    anchor = '    /** Main thread, each tick: run refreshes that were held back by the debounce. */'
    if text.count(anchor) != 1:
        raise UserError('MapHorizons region patch anchor is ambiguous')
    addition = '''    /** Refresh only cached regions touched by a native LOD; never expand huge coarse extents. */
    public static void refreshCovered(ResourceLocation dim, java.util.function.BiPredicate<Integer, Integer> affected) {
        java.util.List<Key> targets;
        synchronized (CACHE) {
            targets = CACHE.keySet().stream().filter(key -> key.dim().equals(dim)
                    && affected.test(Bits.unpackX(key.region()), Bits.unpackZ(key.region()))).toList();
        }
        for (Key key : targets) refresh(dim, Bits.unpackX(key.region()), Bits.unpackZ(key.region()));
    }

'''
    return text.replace(anchor, addition + anchor).encode('utf-8')


def apply(source):
    """No fetching, Java, process launch, installed artifact or Packwiz mutation."""
    source = Path(source)
    target = source / RELATIVE
    replacement = changed_source(target.read_bytes())
    region_target = source / REGION_RELATIVE
    region_replacement = changed_regions(region_target.read_bytes())
    helper = REPO / 'compat/maphorizons/IndexRefresh.java'
    destination = target.with_name('IndexRefresh.java')
    properties = source / 'gradle.properties'
    raw = properties.read_text(encoding='utf-8')
    coverage = REPO / 'compat/maphorizons/LodCoverage.java'
    coverage_target = target.with_name('LodCoverage.java')
    if raw.count('mod_version=1.1.0\n') != 1 or destination.exists() or coverage_target.exists():
        raise UserError('Use a fresh exact author tree for the MapHorizons repair')
    raw = raw.replace('mod_version=1.1.0\n', 'mod_version=' + VERSION + '\n')
    atomic_write(target, replacement)
    atomic_write(region_target, region_replacement)
    atomic_write(destination, helper.read_bytes())
    atomic_write(coverage_target, coverage.read_bytes())
    atomic_write(properties, raw)
    for name, original in [('LICENSE.MapHorizons', source/'LICENSE'),
                           ('NOTICE.awft-map-refresh', REPO/'compat/maphorizons/NOTICE.md')]:
        atomic_write(source/'src/main/resources/META-INF'/name, original.read_bytes())
    return {'version': VERSION, 'upstream_sha256': UPSTREAM_SHA256,
            'patched_sha256': digest(target), 'helper_sha256': digest(destination),
            'coverage_sha256': digest(coverage_target), 'region_callback_sha256': digest(region_target),
            'scope': 'Source staging only; actual pinned linkage/JDBC/native Xaero view are separate gates. No discovery, generation, network or permission changes.'}
