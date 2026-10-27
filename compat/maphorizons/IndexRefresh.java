package com.volcanicmg.maphorizons.client.dh;

import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.DriverManager;
import java.util.ArrayList;
import java.util.List;

/** Read-only DH3.3 metadata scan, one refresh lease and provider-owned immutable coverage. */
public final class IndexRefresh {
    public static final String JDBC_PREFIX = "jdbc:dh_sqlite:";
    public static final long INTERVAL_NANOS = 30_000_000_000L;
    public static final int MAX_TILES = 262_144;
    private long sequence;
    private long active;
    private long completedAt;
    private boolean completed;
    private volatile LodCoverage coverage = LodCoverage.empty();

    public synchronized long begin(long now) {
        if (active != 0 || completed && now - completedAt < INTERVAL_NANOS) return 0;
        active = ++sequence;
        return active;
    }

    public synchronized boolean owns(long token) {
        return token != 0 && active == token;
    }

    public synchronized boolean finish(long token, long now) {
        if (!owns(token)) return false;
        active = 0;
        completedAt = now;
        completed = true;
        return true;
    }

    public synchronized void invalidate() {
        active = 0;
        sequence++;
        completed = false;
        coverage = LodCoverage.empty();
    }

    public LodCoverage snapshot() { return coverage; }
    public synchronized boolean observe(List<LodCoverage.Section> sections) {
        LodCoverage next = coverage.observe(sections);
        if (coverage == next) return false;
        coverage = next;
        return true;
    }
    public synchronized boolean publish(long token, LodCoverage scanned) {
        if (!owns(token)) return false;
        LodCoverage next = scanned.reconcilePending(coverage);
        if (next.equals(coverage)) return false;
        coverage = next;
        return true;
    }

    /**
     * DH3.3 stores section detail6 as DetailLevel0 in FullData. Read only positions;
     * never open a world, decompress terrain, send a request or generate chunks.
     * URI mode=ro prevents creating a missing database or modifying an existing one.
     * The row cap is enforced in SQL, before materializing the returned positions.
     */
    public static List<LodCoverage.Section> read(Path database) throws Exception {
        if (!Files.isRegularFile(database) || Files.isSymbolicLink(database)) throw new IllegalStateException("DH database is unavailable");
        List<LodCoverage.Section> tiles = new ArrayList<>();
        long deadline = System.nanoTime() + 250_000_000L;
        Class.forName("dh_sqlite.JDBC");
        try (var connection = DriverManager.getConnection(JDBC_PREFIX + database.toAbsolutePath().toUri() + "?mode=ro");
             var statement = connection.createStatement()) {
            statement.setQueryTimeout(1);
            statement.execute("PRAGMA query_only=ON");
            statement.execute("PRAGMA busy_timeout=250");
            try (var rows = statement.executeQuery("SELECT DetailLevel, PosX, PosZ FROM FullData WHERE DetailLevel BETWEEN 0 AND " + LodCoverage.MAX_DETAIL + " LIMIT " + (MAX_TILES + 1))) {
                while (rows.next()) {
                    if (System.nanoTime() > deadline) throw new IllegalStateException("DH metadata scan exceeded its work deadline");
                    if (tiles.size() == MAX_TILES) throw new IllegalStateException("DH metadata exceeds the reviewed tile limit");
                    Object detail = rows.getObject(1), x = rows.getObject(2), z = rows.getObject(3);
                    if (!(detail instanceof Number d) || !(x instanceof Number px) || !(z instanceof Number pz))
                        throw new IllegalStateException("DH metadata contains a null/noninteger coordinate");
                    long dx = px.longValue(), dz = pz.longValue(), level = d.longValue();
                    if (dx < Integer.MIN_VALUE || dx > Integer.MAX_VALUE || dz < Integer.MIN_VALUE || dz > Integer.MAX_VALUE
                        || level < 0 || level > LodCoverage.MAX_DETAIL || d.doubleValue() != level || px.doubleValue() != dx || pz.doubleValue() != dz)
                        throw new IllegalStateException("DH metadata coordinate is not a supported integer");
                    tiles.add(new LodCoverage.Section((int)level, (int)dx, (int)dz));
                }
            }
        }
        return List.copyOf(tiles);
    }
}
