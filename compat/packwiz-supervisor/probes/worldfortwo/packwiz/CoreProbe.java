package worldfortwo.packwiz;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.*;
import java.util.*;
import java.util.concurrent.*;

/** Filesystem/policy fixtures, not an installer or GUI test. All writes stay under argv[0]. */
public final class CoreProbe {
    private static int checks;
    private static void check(boolean value, String reason) { checks++; if (!value) throw new AssertionError(reason); }
    private static void rejects(Runnable task, String reason) {
        boolean rejected = false;
        try { task.run(); } catch (IllegalArgumentException ex) { rejected = true; }
        check(rejected, reason);
    }
    static final String DNS = "Loading manifest file...\nLoading pack file...\nModpack name: Fixture\n"
        + "(1/2) Downloaded Good\n(2/2) Failed to download Broken: HTTP request failed\n"
        + FailureClassifier.MARKER + "\nBroken: link.infra.packwiz.installer.request.RequestException$Internal$HTTP$RequestFailed: HTTP request failed\n"
        + "\tat link.infra.packwiz.installer.DownloadTask.download(SourceFile:244)\n"
        + "Caused by: java.net.UnknownHostException: No such host is known (example.invalid)\n"
        + "\tat okhttp3.Dns$Companion$DnsSystem.lookup(SourceFile:49)\n\t... 10 more\n" + FailureClassifier.CANCEL + "\n";
    private static AttemptJournal.Attempt seal(Path root, String name, String log, AttemptJournal.Mode mode,
                                              AttemptJournal.Termination termination, int code, boolean pinned) throws IOException {
        return AttemptJournal.seal(root.resolve(name), mode, AttemptJournal.Role.INITIAL, termination, code,
            new AttemptJournal.Chain(pinned ? AttemptJournal.BOOTSTRAP_SHA256 : "0".repeat(64), AttemptJournal.INSTALLER_SHA256, "1".repeat(64)),
            new ByteArrayInputStream(log.getBytes(StandardCharsets.UTF_8)));
    }
    private static Map<String, String> hashes(byte[] bytes) throws Exception {
        return Map.of("SHA-256", HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes)),
                      "SHA-512", HexFormat.of().formatHex(MessageDigest.getInstance("SHA-512").digest(bytes)));
    }
    private static void put(Path root, String path, byte[] bytes) throws IOException {
        Path file = root.resolve(path); Files.createDirectories(file.getParent()); Files.write(file, bytes);
    }
    public static void main(String[] args) throws Exception {
        if (args.length < 1) throw new IllegalArgumentException("Owned fresh fixture directory required");
        Path root = Path.of(args[0]); Files.createDirectory(root);
        check(FailureClassifier.classify(DNS).kind() == FailureClassifier.Kind.DNS_ONLY, "Complete DNS fixture");
        check(FailureClassifier.classify(DNS).hosts().equals(Set.of("example.invalid")), "Exact DNS host");
        for (String status : List.of("Good already exists (validated)", "Good already exists (cached)", "Skipped Good (wrong side)", "Skipped Good (disabled)", "Deleted Good (wrong side)", "Deleted Good (disabled)"))
            check(FailureClassifier.classify(DNS.replace("Downloaded Good", status)).kind() == FailureClassifier.Kind.DNS_ONLY, "Native nonfailure completion status");
        for (String bad : List.of(DNS.replace("UnknownHostException", "SocketTimeoutException"),
                DNS.replace("HTTP request failed", "HTTP 403"), DNS.replace("(2/2)", "(2/3)"),
                DNS.replace("example.invalid)", "example.invalid"), DNS.replace("\t... 10 more", "Suppressed: java.io.IOException: failure"),
                DNS.replace(FailureClassifier.CANCEL, ""), DNS + "Hash mismatch!\n", "user cancelled\n" + DNS,
                DNS.replace("\tat okhttp3.Dns$Companion$DnsSystem.lookup(SourceFile:49)", "")))
            check(FailureClassifier.classify(bad).kind() == FailureClassifier.Kind.NOT_PROVEN_DNS_ONLY, "Mixed/truncated/unknown error must stop");

        var normal = AttemptJournal.Termination.NORMAL_EXIT;
        var cli = AttemptJournal.Mode.HEADLESS_CLI;
        var first = seal(root, "first", DNS, cli, normal, 1, true);
        check(AttemptJournal.verifiedLog(first).equals(DNS), "Sealed exact log");
        var gui = seal(root, "gui", DNS, AttemptJournal.Mode.GUI, normal, 1, true);
        check(RecoveryPolicy.claim(gui) == RecoveryPolicy.Decision.GUI_DECISION_UNOBSERVABLE, "DNS does not override GUI cancellation ambiguity");
        check(!Files.exists(gui.directory().resolve("recovery.claim")), "GUI never consumes a retry or launches anything");
        for (var termination : List.of(AttemptJournal.Termination.USER_CANCELLED, AttemptJournal.Termination.EXTERNALLY_STOPPED, AttemptJournal.Termination.UNKNOWN))
            check(RecoveryPolicy.claim(seal(root, termination.name(), DNS, cli, termination, 1, true)) == RecoveryPolicy.Decision.CANCELLED_OR_UNPROVEN_EXIT, "Cancellation/provenance must stop");
        check(RecoveryPolicy.claim(seal(root, "zero", DNS, cli, normal, 0, true)) == RecoveryPolicy.Decision.CANCELLED_OR_UNPROVEN_EXIT, "Exit zero is not recovery or integrity");
        check(RecoveryPolicy.claim(seal(root, "unpinned", DNS, cli, normal, 1, false)) == RecoveryPolicy.Decision.UNPINNED_CHAIN, "Exact official chain required");
        check(RecoveryPolicy.claim(seal(root, "mixed", DNS.replace("UnknownHostException", "IOException"), cli, normal, 1, true)) == RecoveryPolicy.Decision.NOT_DNS_ONLY, "NonDNS never retries");
        var recovery = AttemptJournal.seal(root.resolve("recovery"), cli, AttemptJournal.Role.RECOVERY, normal, 1, first.chain(), new ByteArrayInputStream(DNS.getBytes(StandardCharsets.UTF_8)));
        check(RecoveryPolicy.claim(recovery) == RecoveryPolicy.Decision.NOT_INITIAL_ATTEMPT, "A failed recovery is never retried again");
        var invalidEncoding = AttemptJournal.seal(root.resolve("encoding"), cli, AttemptJournal.Role.INITIAL, normal, 1, first.chain(), new ByteArrayInputStream(new byte[]{(byte) 0xc3, (byte) 0x28}));
        check(RecoveryPolicy.claim(invalidEncoding) == RecoveryPolicy.Decision.UNSEALED_ATTEMPT, "Malformed UTF-8 is not silently repaired into evidence");
        var changed = seal(root, "changed", DNS, cli, normal, 1, true);
        Files.writeString(changed.directory().resolve("installer.log"), DNS + " ");
        check(RecoveryPolicy.claim(changed) == RecoveryPolicy.Decision.UNSEALED_ATTEMPT, "Tampered first failure cannot authorize retry");
        boolean collision = false;
        try { seal(root, "first", DNS, cli, normal, 1, true); } catch (FileAlreadyExistsException ex) { collision = true; }
        check(collision && AttemptJournal.verifiedLog(first).equals(DNS), "Never overwrite a failed attempt");
        boolean bounded = false;
        try { AttemptJournal.seal(root.resolve("oversize"), cli, AttemptJournal.Role.INITIAL, normal, 1, first.chain(), new ByteArrayInputStream(new byte[AttemptJournal.MAX_LOG_BYTES + 1])); }
        catch (IOException ex) { bounded = true; }
        check(bounded && Files.size(root.resolve("oversize/installer.log")) <= AttemptJournal.MAX_LOG_BYTES
            && !Files.exists(root.resolve("oversize/receipt.complete")), "Capped partial failure retained without completion");
        ExecutorService executor = Executors.newFixedThreadPool(4);
        try {
            List<Callable<RecoveryPolicy.Decision>> jobs = new ArrayList<>();
            for (int i = 0; i < 16; i++) jobs.add(() -> RecoveryPolicy.claim(first));
            int claimed = 0;
            for (var result : executor.invokeAll(jobs)) if (result.get() == RecoveryPolicy.Decision.ONE_HEADLESS_RECOVERY_CLAIMED) claimed++;
            check(claimed == 1, "One atomic retry credit across competing requests");
        } finally { executor.shutdown(); check(executor.awaitTermination(5, TimeUnit.SECONDS), "Owned probe executor closed"); }
        check(RecoveryPolicy.claim(first) == RecoveryPolicy.Decision.RECOVERY_ALREADY_CLAIMED, "Credit persists across policy reconstruction");

        Path instance = root.resolve("instance"); Files.createDirectory(instance);
        byte[] body = "locked-artifact".getBytes(StandardCharsets.UTF_8), config = "scene=locked\n".getBytes(StandardCharsets.UTF_8);
        List<IntegrityGate.Pin> pins = new ArrayList<>();
        pins.add(new IntegrityGate.Pin("mods/required.jar", body.length, hashes(body), false, true));
        pins.add(new IntegrityGate.Pin("mods/essential.jar", body.length, hashes(body), true, false));
        pins.add(new IntegrityGate.Pin("config/paxi/datapacks/awft/data/awft/scene.json", config.length, hashes(config), false, true));
        var inventory = new IntegrityGate.Inventory("2".repeat(64), pins, Set.of("mods", "config/paxi/datapacks"), 1024);
        put(instance, pins.get(0).path(), body); put(instance, pins.get(2).path(), config);
        var valid = IntegrityGate.verify(instance, inventory, Map.of());
        check(valid.pass() && valid.verifiedFiles() == 2 && valid.verifiedBytes() == body.length + config.length, "Mandatory artifacts and raw Paxi checked; Essential stays off");
        put(instance, pins.get(1).path(), body);
        check(!IntegrityGate.verify(instance, inventory, Map.of()).pass(), "Essential present while default-off must fail");
        check(IntegrityGate.verify(instance, inventory, Map.of(pins.get(1).path(), true)).pass(), "Explicit separate selection inventory verifies all three");
        Files.delete(instance.resolve(pins.get(1).path()));
        put(instance, pins.get(0).path(), "tamper-artifact".getBytes(StandardCharsets.UTF_8));
        check(!IntegrityGate.verify(instance, inventory, Map.of()).pass(), "Same-sized artifact tampering fails");
        put(instance, pins.get(0).path(), body); put(instance, pins.get(2).path(), "scene=forged\n".getBytes(StandardCharsets.UTF_8));
        check(!IntegrityGate.verify(instance, inventory, Map.of()).pass(), "Config/Paxi mismatch fails independently");
        put(instance, pins.get(2).path(), config); put(instance, "mods/server-only.jar", body);
        check(!IntegrityGate.verify(instance, inventory, Map.of()).pass(), "Unexpected/server-only artifact fails");
        Files.delete(instance.resolve("mods/server-only.jar")); Files.delete(instance.resolve(pins.get(0).path()));
        check(!IntegrityGate.verify(instance, inventory, Map.of()).pass(), "Missing mandatory file fails even with hypothetical exit zero");
        put(instance, pins.get(0).path(), body);
        Map<String, String> wrong = new HashMap<>(hashes(body)); wrong.put("SHA-512", "0".repeat(128));
        var badHashes = new IntegrityGate.Inventory("3".repeat(64), List.of(new IntegrityGate.Pin("mods/required.jar", body.length, wrong, false, true)), Set.of("mods"), 1024);
        check(!IntegrityGate.verify(instance, badHashes, Map.of()).pass(), "Every supplied hash is mandatory, not first hash only");
        for (String path : List.of("../outside.jar", "C:/outside.jar", "mods/../outside.jar", "mods/evil.jar:stream", "mods/NUL.jar", "mods/end. "))
            rejects(() -> new IntegrityGate.Pin(path, 1, Map.of("SHA-256", "0".repeat(64)), false, true), "Unsafe Windows path");
        rejects(() -> new IntegrityGate.Inventory("4".repeat(64), List.of(pins.get(0), new IntegrityGate.Pin("MODS/required.jar", body.length, pins.get(0).hashes(), false, true)), Set.of("mods"), 1024), "Case collision");
        rejects(() -> new IntegrityGate.Inventory("5".repeat(64), pins, Set.of("mods"), 1), "Finite byte cap");
        boolean invalidChoice = false;
        try { IntegrityGate.verify(instance, inventory, Map.of(pins.get(0).path(), false)); } catch (IllegalArgumentException ex) { invalidChoice = true; }
        check(invalidChoice, "Choice cannot disable a mandatory file");
        for (int i = 1; i < args.length; i++) {
            byte[] log = AttemptJournal.boundedRead(Path.of(args[i]), AttemptJournal.MAX_LOG_BYTES);
            var report = FailureClassifier.classify(new String(log, StandardCharsets.UTF_8));
            check(report.kind() == FailureClassifier.Kind.DNS_ONLY && report.failedFiles() == 6, "Exact preserved six-file native failure report: " + report.reason());
            System.out.println("ACTUAL_LOG_SHA256=" + AttemptJournal.sha256(log) + " DNS_FILES=" + report.failedFiles());
        }
        System.out.println("CORE_FIXTURE_CHECKS=" + checks + " PASS; no installer/network/game invoked");
    }
}
