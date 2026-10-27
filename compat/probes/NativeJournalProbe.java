package worldfortwo.bridge;

import com.google.gson.Gson;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.Map;

/** Headless probe of the exact packaged NativeJournal; no Minecraft classes. */
public final class NativeJournalProbe {
    private static String sha256(byte[] bytes) throws Exception {
        return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 4) {
            throw new IllegalArgumentException("directory, probe ID, old-view SHA and probe-source SHA required");
        }
        if (!"21".equals(System.getProperty("java.specification.version"))) {
            throw new IllegalStateException("The tested Java 21 runtime is required");
        }
        Path directory = Path.of(args[0]).toAbsolutePath().normalize();
        Path old = directory.resolve("status.json");
        String before = sha256(Files.readAllBytes(old));
        if (!before.equals(args[2])) {
            throw new AssertionError("Initial progress file differs from the Python-owned old view");
        }
        String codeSource = Path.of(NativeJournal.class.getProtectionDomain().getCodeSource()
            .getLocation().toURI()).toAbsolutePath().normalize().toString();
        Map<String, Object> report = new LinkedHashMap<>();
        report.put("operation", "headless-native-journal-reader-lock-probe");
        report.put("probe_id", args[1]);
        report.put("state", "progress-attempt");
        report.put("previous_progress_sha256", before);
        report.put("probe_source_sha256", args[3]);
        report.put("native_journal_code_source", codeSource);
        report.put("scope", "NativeJournal file publication only; no Minecraft server, world, player or game verification");

        // This resolves the package-private method from the pinned bridge JAR.
        // The Python process continues to hold the old file without delete share.
        NativeJournal.progress(directory, "status.json", report);
        Object warning = report.get("progress_publication_warning");
        if (!(warning instanceof String) || !((String) warning).contains("AccessDeniedException")) {
            throw new AssertionError("The native progress call did not return the expected AccessDenied warning");
        }
        if (!sha256(Files.readAllBytes(old)).equals(before)) {
            throw new AssertionError("A failed mutable publication altered the old progress view");
        }
        report.put("state", "terminal-reached-after-reader-lock");
        report.put("progress_call_returned", true);
        NativeJournal.terminal(directory, "journal-lock-probe", report);
        System.out.println(new Gson().toJson(Map.of(
            "probe_id", args[1], "state", "terminal-call-returned",
            "native_journal_code_source", codeSource,
            "previous_progress_sha256", before,
            "progress_publication_warning", warning)));
    }
}
