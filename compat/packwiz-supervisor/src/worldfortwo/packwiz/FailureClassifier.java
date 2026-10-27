package worldfortwo.packwiz;

import java.util.*;
import java.util.regex.*;

/** Deliberately narrow parser for the pinned 0.5.14 CLI download-error report. */
public final class FailureClassifier {
    private FailureClassifier() {}
    public enum Kind { DNS_ONLY, NOT_PROVEN_DNS_ONLY }
    public record Report(Kind kind, int failedFiles, Set<String> hosts, String reason) {
        public Report { hosts = Set.copyOf(hosts); }
    }
    static final String MARKER = "Failed to download modpack, the following errors were encountered:";
    static final String CANCEL = "Update cancelled by user!";
    private static final Pattern PROGRESS = Pattern.compile("\\((\\d+)/(\\d+)\\) (.+)");
    private static final Pattern HEADER = Pattern.compile("(.{1,160}): link\\.infra\\.packwiz\\.installer\\.request\\.RequestException\\$Internal\\$HTTP\\$RequestFailed: HTTP request failed");
    private static final Pattern HOST = Pattern.compile("[A-Za-z0-9][A-Za-z0-9.-]{0,252}[A-Za-z0-9]|[A-Za-z0-9]");
    private static final Set<String> PHASES = Set.of("Loading manifest file...", "Loading pack file...",
        "Loading MultiMC pack file...", "Loaded MultiMC config", "Checking local files...",
        "Comparing new files...", "Validating existing files...", "Resolving CurseForge metadata...");
    private static Report no(String reason) { return new Report(Kind.NOT_PROVEN_DNS_ONLY, 0, Set.of(), reason); }

    public static Report classify(String text) {
        if (text == null || text.length() > AttemptJournal.MAX_LOG_BYTES || text.indexOf('\0') >= 0)
            return no("Absent, oversized or binary log");
        String[] lines = text.replace("\r\n", "\n").split("\n", -1);
        int marker = -1, total = -1;
        Set<Integer> ordinals = new HashSet<>();
        Set<String> failed = new LinkedHashSet<>();
        for (int i = 0; i < lines.length; i++) {
            String line = lines[i];
            if (line.equals(MARKER)) { marker = i; break; }
            if (line.isBlank() || PHASES.contains(line) || line.matches("Modpack name: [^\\p{Cntrl}]{1,160}")
                || line.matches("\\[Warning] Accepting option [^\\p{Cntrl}]{1,160} as option choosing is not implemented in the CLI")) continue;
            Matcher progress = PROGRESS.matcher(line);
            if (!progress.matches()) return no("Unrecognized pre-report output");
            int ordinal, count;
            try { ordinal = Integer.parseInt(progress.group(1)); count = Integer.parseInt(progress.group(2)); }
            catch (NumberFormatException ex) { return no("Invalid progress count"); }
            if (count < 1 || count > 8192 || ordinal < 1 || ordinal > count
                || (total != -1 && total != count) || !ordinals.add(ordinal)) return no("Inconsistent progress");
            total = count;
            String message = progress.group(3);
            if (message.startsWith("Failed to download ") && message.endsWith(": HTTP request failed")) {
                String name = message.substring(19, message.length() - 21);
                if (name.isBlank() || !failed.add(name)) return no("Ambiguous failed-file identity");
            } else if (!(message.matches("Downloaded [^\\p{Cntrl}]+")
                || message.matches("[^\\p{Cntrl}]+ already exists \\((?:validated|cached)\\)")
                || message.matches("(?:Skipped|Deleted) [^\\p{Cntrl}]+ \\((?:disabled|wrong side)\\)"))) return no("Non-DNS or unknown progress failure");
        }
        if (marker < 0 || total < 1 || ordinals.size() != total || failed.isEmpty()) return no("Incomplete download report");
        Set<String> reported = new LinkedHashSet<>(), hosts = new LinkedHashSet<>();
        String current = null;
        boolean rootSeen = false, downloadFrame = false, dnsFrame = false, ended = false;
        for (int i = marker + 1; i < lines.length; i++) {
            String line = lines[i];
            if (ended) { if (!line.isBlank()) return no("Output after terminal report"); continue; }
            Matcher header = HEADER.matcher(line);
            if (header.matches() || line.equals(CANCEL)) {
                if (current != null && !(rootSeen && downloadFrame && dnsFrame)) return no("Incomplete DNS cause chain");
                if (line.equals(CANCEL)) { ended = true; continue; }
                current = header.group(1);
                if (!failed.contains(current) || !reported.add(current)) return no("Unmatched failure identity");
                rootSeen = downloadFrame = dnsFrame = false;
            } else if (line.startsWith("Caused by: java.net.UnknownHostException: ") && current != null && !rootSeen) {
                String diagnostic = line.substring(42);
                if (diagnostic.startsWith("No such host is known (")) {
                    if (!diagnostic.endsWith(")")) return no("Truncated DNS diagnostic");
                    diagnostic = diagnostic.substring(23, diagnostic.length() - 1);
                }
                Matcher host = HOST.matcher(diagnostic);
                if (!host.matches()) return no("Unknown DNS diagnostic format");
                hosts.add(diagnostic.toLowerCase(Locale.ROOT)); rootSeen = true;
            } else if (current != null && (line.matches("\\tat [^\\p{Cntrl}]+") || line.matches("\\t\\.\\.\\. \\d+ more"))) {
                downloadFrame |= line.contains("link.infra.packwiz.installer.DownloadTask.download(");
                dnsFrame |= line.contains("okhttp3.Dns$Companion$DnsSystem.lookup(");
            } else return no("Mixed, unknown, suppressed or truncated exception report");
        }
        if (!ended || !reported.equals(failed)) return no("Incomplete terminal report");
        // CANCEL is CLI's synthetic result here. It is never evidence of a GUI user's intent.
        return new Report(Kind.DNS_ONLY, reported.size(), hosts, "Complete pinned CLI DNS-only report");
    }
}
