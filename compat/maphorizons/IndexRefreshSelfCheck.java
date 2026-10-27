package com.volcanicmg.maphorizons.client.dh;

import java.nio.file.Path;
import java.sql.DriverManager;
import java.util.List;
import java.util.Collections;
import java.util.concurrent.atomic.AtomicReference;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicInteger;

/** Actual Java lease and SQLite checks; no Minecraft or graphics startup. */
public final class IndexRefreshSelfCheck {
    private static int checks;
    private static void check(boolean value) {
        checks++;
        if (!value) throw new AssertionError("Index refresh contract failed");
    }

    public static void main(String[] args) throws Exception {
        var lease = new IndexRefresh();
        long first = lease.begin(0);
        check(first != 0 && lease.owns(first));
        check(lease.begin(120_000_000_000L) == 0);
        check(lease.finish(first, 120_000_000_000L));
        check(lease.begin(149_999_999_999L) == 0);
        long second = lease.begin(150_000_000_000L);
        check(second != 0 && second != first);
        check(!lease.finish(first, 151_000_000_000L));
        lease.invalidate();
        check(!lease.owns(second) && !lease.finish(second, 151_000_000_000L));
        check(lease.begin(151_000_000_000L) != 0);

        var coarse = new LodCoverage.Section(3, -1, -1);
        var fine = new LodCoverage.Section(0, -1, -1);
        var coverage = LodCoverage.from(List.of(coarse, fine));
        check(coverage.sourceForTile(-8, -8).equals(coarse));
        check(coverage.sourceForTile(-1, -1).equals(fine));
        check(coverage.sourceForTile(0, 0) == null && coverage.sourceForTile(-9, -1) == null);
        check(coverage.hasRegion(-1, -1) && !coverage.hasRegion(0, 0));
        check(LodCoverage.intersectsAnyRegion(List.of(coarse), -1, -1) && !LodCoverage.intersectsAnyRegion(List.of(coarse), 0, -1));
        var groups = coverage.groups(-1, -1);
        check(groups.size() == 2 && groups.get(coarse).size() == 63 && groups.get(fine).size() == 1);
        check(groups.values().stream().mapToInt(List::size).sum() == 64);
        check(coarse.firstBlockX() == -512 && coarse.columnX(-512) == 0 && coarse.columnX(-1) == 63);
        check(coarse.columnX(0) == -1 && coarse.columnX(-513) == -1 && coarse.columnX(Long.MIN_VALUE) == -1);
        for (int detail=0; detail<=LodCoverage.MAX_DETAIL; detail++) {
            var section = new LodCoverage.Section(detail, -1, 1);
            long firstBlock = section.firstBlockX(), scale = 1L << detail;
            check(section.columnX(firstBlock) == 0 && section.columnX(firstBlock + scale - 1) == 0);
            check(section.columnX(firstBlock + 63 * scale) == 63 && section.columnX(firstBlock + 64 * scale) == -1);
        }
        check(new LodCoverage.Section(12, 114, 0).columnX(30_000_001) == -1);
        check(coverage.sourceForTile(Integer.MAX_VALUE, Integer.MIN_VALUE) == null);
        var huge = LodCoverage.from(List.of(new LodCoverage.Section(12, 0, 0)));
        check(huge.size() == 1 && huge.groups(100,100).size() == 1 && huge.groups(100,100).values().iterator().next().size() == 64);
        boolean immutable = false;
        try { groups.get(coarse).add(new LodCoverage.Tile(0, 0)); } catch (UnsupportedOperationException expected) { immutable = true; }
        check(immutable);
        var calls = new AtomicInteger();
        var sampled = new LodCoverage.Samples<Integer>(64, (x,z) -> { calls.incrementAndGet(); return x + z * 64; });
        for (int x=-512; x < -504; x++) check(sampled.get(coarse.columnX(x), 0) == 0);
        check(calls.get() == 1); // Coarse pixels reuse the one actual sampled column.
        var nullCalls = new AtomicInteger();
        var holes = new LodCoverage.Samples<Integer>(64, (x,z) -> { nullCalls.incrementAndGet(); return null; });
        check(holes.get(0,0) == null && holes.get(0,0) == null && holes.get(-1,0) == null && nullCalls.get() == 1);
        boolean rejected = false;
        try { LodCoverage.from(Collections.nCopies(LodCoverage.MAX_SECTIONS + 1, fine)); } catch (IllegalArgumentException expected) { rejected = true; }
        check(rejected);

        // Deterministic stale-scan race: a listener adds an unsaved fine section after scan capture.
        var raced = new IndexRefresh();
        long scan = raced.begin(0);
        var captured = new CountDownLatch(1);
        var publish = new CountDownLatch(1);
        var failure = new AtomicReference<Throwable>();
        Thread scanner = new Thread(() -> {
            try { var stale = LodCoverage.from(List.of(coarse)); captured.countDown(); publish.await(); raced.publish(scan, stale); }
            catch (Throwable error) { failure.set(error); }
        });
        scanner.start(); captured.await();
        check(raced.observe(List.of(fine))); publish.countDown(); scanner.join();
        check(failure.get() == null && raced.snapshot().sourceForTile(-1,-1).equals(fine));
        check(raced.finish(scan, 10) && raced.snapshot().size() == 2);
        long replacement = raced.begin(IndexRefresh.INTERVAL_NANOS + 10);
        check(raced.publish(replacement, LodCoverage.from(List.of(coarse, fine))));
        check(raced.snapshot().size() == 2 && raced.snapshot().sourceForTile(-1,-1).equals(fine));
        raced.invalidate();
        check(!raced.publish(replacement, coverage) && raced.snapshot().isEmpty());

        var shared = new IndexRefresh();
        var ready = new CountDownLatch(1);
        var winners = new AtomicInteger();
        Thread[] workers = new Thread[16];
        for (int i=0; i<workers.length; i++) {
            workers[i] = new Thread(() -> {
                try { ready.await(); } catch (InterruptedException e) { throw new RuntimeException(e); }
                if (shared.begin(0) != 0) winners.incrementAndGet();
            });
            workers[i].start();
        }
        ready.countDown();
        for (Thread worker : workers) worker.join();
        check(winners.get() == 1);

        // Optional pinned SQLite-driver lane, supplied explicitly by the probe runner.
        if (args.length != 0) {
            Path db = Path.of(args[0]);
            Class.forName("dh_sqlite.JDBC");
            check(DriverManager.getDriver(IndexRefresh.JDBC_PREFIX).getClass().getName().equals("dh_sqlite.JDBC"));
            try (var connection = DriverManager.getConnection(IndexRefresh.JDBC_PREFIX + db.toAbsolutePath());
                 var statement = connection.createStatement()) {
                statement.execute("CREATE TABLE FullData(DetailLevel INTEGER, PosX INTEGER, PosZ INTEGER)");
                statement.execute("INSERT INTO FullData VALUES(0,-1,-9),(0,20,-18),(1,999,999),(13,0,0)");
            }
            long size = java.nio.file.Files.size(db);
            byte[] before = java.security.MessageDigest.getInstance("SHA-256").digest(java.nio.file.Files.readAllBytes(db));
            var rows = IndexRefresh.read(db);
            check(rows.size() == 3 && rows.stream().anyMatch(row -> row.detail() == 1 && row.x() == 999 && row.z() == 999));
            check(rows.stream().anyMatch(row -> row.detail() == 0 && row.x() == -1 && row.z() == -9));
            check(java.nio.file.Files.size(db) == size);
            check(java.util.Arrays.equals(before, java.security.MessageDigest.getInstance("SHA-256").digest(java.nio.file.Files.readAllBytes(db))));
            try (var connection = DriverManager.getConnection(IndexRefresh.JDBC_PREFIX + db.toAbsolutePath().toUri() + "?mode=ro");
                 var statement = connection.createStatement()) {
                boolean readonly = false;
                try { statement.execute("INSERT INTO FullData VALUES(0,1,1)"); } catch (java.sql.SQLException expected) { readonly = true; }
                check(readonly);
            }
            for (String malformed : List.of("(0,NULL,1)", "(0,1,NULL)", "(0,-9223372036854775808,1)", "(0,1.5,1)")) {
                try (var connection = DriverManager.getConnection(IndexRefresh.JDBC_PREFIX + db.toAbsolutePath()); var statement = connection.createStatement()) {
                    statement.execute("DELETE FROM FullData"); statement.execute("INSERT INTO FullData VALUES" + malformed);
                }
                boolean invalid = false;
                try { IndexRefresh.read(db); } catch (IllegalStateException | IllegalArgumentException expected) { invalid = true; }
                check(invalid);
            }
            Path missing = db.resolveSibling("must-not-be-created.sqlite");
            boolean refused = false;
            try { IndexRefresh.read(missing); } catch (IllegalStateException e) { refused = true; }
            check(refused && !java.nio.file.Files.exists(missing));
        }
        System.out.println("LOD_ADAPTER_CHECKS=" + checks + " PASS; SQLite lane=" + (args.length != 0) + "; no Minecraft/graphics/network");
    }
}
