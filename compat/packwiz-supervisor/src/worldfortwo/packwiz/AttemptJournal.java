package worldfortwo.packwiz;

import java.io.*;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.nio.charset.CodingErrorAction;
import java.nio.file.*;
import java.security.*;
import java.util.*;

/** Create-once private evidence; hashes detect later edits. No installer is launched here. */
public final class AttemptJournal {
    public static final int MAX_LOG_BYTES = 4 * 1024 * 1024;
    public static final String BOOTSTRAP_SHA256 = "a8fbb24dc604278e97f4688e82d3d91a318b98efc08d5dbfcbcbcab6443d116c";
    public static final String INSTALLER_SHA256 = "c9f646908d340d84773948a9a7d98bc1dae250d35e1016dc6e2b8459760b5598";
    public enum Mode { GUI, HEADLESS_CLI }
    public enum Role { INITIAL, RECOVERY }
    public enum Termination { NORMAL_EXIT, USER_CANCELLED, EXTERNALLY_STOPPED, UNKNOWN }
    public record Chain(String bootstrapSha256, String installerSha256, String inventorySha256) {
        public Chain { requireHash(bootstrapSha256); requireHash(installerSha256); requireHash(inventorySha256); }
        public boolean pinned() { return bootstrapSha256.equals(BOOTSTRAP_SHA256) && installerSha256.equals(INSTALLER_SHA256); }
    }
    public record Attempt(Path directory, Mode mode, Role role, Termination termination, int exitCode,
                          Chain chain, long logBytes, String logSha256, String receiptSha256) {}
    private AttemptJournal() {}
    static void requireHash(String hash) {
        if (hash == null || !hash.matches("[0-9a-f]{64}")) throw new IllegalArgumentException("Expected lowercase SHA-256");
    }
    static String sha256(byte[] bytes) { return HexFormat.of().formatHex(digest().digest(bytes)); }
    static MessageDigest digest() {
        try { return MessageDigest.getInstance("SHA-256"); }
        catch (NoSuchAlgorithmException impossible) { throw new AssertionError(impossible); }
    }
    static byte[] boundedRead(Path path, int limit) throws IOException {
        if (Files.isSymbolicLink(path) || !Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS)) throw new IOException("Not a regular evidence file");
        try (InputStream input = Files.newInputStream(path, LinkOption.NOFOLLOW_LINKS)) {
            byte[] bytes = input.readNBytes(limit + 1);
            if (bytes.length > limit) throw new IOException("Evidence exceeds bound");
            return bytes;
        }
    }
    private static byte[] receipt(Mode mode, Role role, Termination termination, int exitCode, Chain chain, long size, String hash) {
        return ("awft-packwiz-attempt:1\nmode=" + mode + "\nrole=" + role + "\ntermination=" + termination + "\nexit=" + exitCode
            + "\nbootstrap_sha256=" + chain.bootstrapSha256 + "\ninstaller_sha256=" + chain.installerSha256
            + "\ninventory_sha256=" + chain.inventorySha256 + "\nlog_bytes=" + size + "\nlog_sha256=" + hash + "\n")
            .getBytes(StandardCharsets.UTF_8);
    }
    public static Attempt seal(Path directory, Mode mode, Role role, Termination termination, int exitCode, Chain chain, InputStream input) throws IOException {
        Objects.requireNonNull(mode); Objects.requireNonNull(role); Objects.requireNonNull(termination); Objects.requireNonNull(chain);
        Files.createDirectory(directory); // Existing or partial evidence is never overwritten or removed.
        Path log = directory.resolve("installer.log");
        long length = 0; MessageDigest hash = digest();
        try (OutputStream output = Files.newOutputStream(log, StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE)) {
            byte[] chunk = new byte[16384]; int count;
            while ((count = input.read(chunk)) != -1) {
                if (length + count > MAX_LOG_BYTES) throw new IOException("Log cap reached; partial evidence retained");
                output.write(chunk, 0, count); hash.update(chunk, 0, count); length += count;
            }
        }
        String logHash = HexFormat.of().formatHex(hash.digest());
        byte[] receipt = receipt(mode, role, termination, exitCode, chain, length, logHash);
        String receiptHash = sha256(receipt);
        Files.write(directory.resolve("receipt.txt"), receipt, StandardOpenOption.CREATE_NEW);
        Files.writeString(directory.resolve("receipt.complete"), receiptHash + "\n", StandardOpenOption.CREATE_NEW);
        return new Attempt(directory.toAbsolutePath().normalize(), mode, role, termination, exitCode, chain, length, logHash, receiptHash);
    }
    public static String verifiedLog(Attempt attempt) throws IOException {
        byte[] log = boundedRead(attempt.directory.resolve("installer.log"), MAX_LOG_BYTES);
        byte[] receipt = boundedRead(attempt.directory.resolve("receipt.txt"), 2048);
        byte[] expected = receipt(attempt.mode, attempt.role, attempt.termination, attempt.exitCode, attempt.chain, attempt.logBytes, attempt.logSha256);
        String complete = new String(boundedRead(attempt.directory.resolve("receipt.complete"), 65), StandardCharsets.US_ASCII);
        if (log.length != attempt.logBytes || !sha256(log).equals(attempt.logSha256)
            || !Arrays.equals(receipt, expected) || !sha256(receipt).equals(attempt.receiptSha256)
            || !complete.equals(attempt.receiptSha256 + "\n")) throw new IOException("Attempt seal does not match");
        return StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
            .onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(log)).toString();
    }
}
