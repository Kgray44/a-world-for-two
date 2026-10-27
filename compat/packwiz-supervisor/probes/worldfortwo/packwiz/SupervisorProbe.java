package worldfortwo.packwiz;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

/** Pure admission/orchestration policy checks. No process launcher, HTTP or installer Main. */
public final class SupervisorProbe {
    private static int checks;
    private static void check(boolean value, String reason) { checks++; if (!value) throw new AssertionError(reason); }
    public static void main(String[] args) throws Exception {
        Path root = Path.of(args[0]); Files.createDirectory(root);
        ReleaseSpec release = ReleaseSpec.embedded();
        check(release.entries().size() == release.entries().stream().map(ReleaseSpec.Entry::metadata).distinct().count(), "Embedded complete unique source index");
        check(release.entries().stream().filter(row -> row.pin().optional()).allMatch(row -> row.metadata().equals("mods/essential.pw.toml") && !row.pin().defaultSelected()), "Real release Essential GUI default remains off");
        check(release.entries().stream().anyMatch(row -> row.pin().path().startsWith("config/paxi/datapacks/awft-settlement-cinematic/")), "Real raw Paxi included in independent gate");
        try (InputStream input = ReleaseSpec.class.getResourceAsStream("/awft-release.bin")) {
            byte[] raw = input.readAllBytes();
            for (byte[] bad : List.of(Arrays.copyOf(raw, raw.length - 1), Arrays.copyOf(raw, raw.length + 1))) {
                boolean refused = false; try { ReleaseSpec.read(bad); } catch (Exception expected) { refused = true; }
                check(refused, "Truncated or trailing trusted inventory refuses");
            }
        }
        byte[] success = "Loading pack file...\nFinished successfully!\n".getBytes(StandardCharsets.UTF_8);
        var normal = AttemptJournal.Termination.NORMAL_EXIT;
        var zero = new SupervisorMain.Exit(normal, 0, true, true);
        check(SupervisorMain.successfulTerminal(zero, success), "Normal zero plus exact final native success grammar");
        for (var exit : List.of(new SupervisorMain.Exit(normal, 1, true, true),
                new SupervisorMain.Exit(AttemptJournal.Termination.EXTERNALLY_STOPPED, 0, true, true),
                new SupervisorMain.Exit(normal, 0, false, true), new SupervisorMain.Exit(normal, 0, true, false)))
            check(!SupervisorMain.successfulTerminal(exit, success), "Native nonzero, interrupted, unclosed or truncated never succeeds");
        for (String bad : List.of("Update cancelled by user! Continuing to start game...\n", "User selected to continue without installing/updating, exiting with code 0...\n",
                "Update cancelled by user!\nFinished successfully!\n", FailureClassifier.MARKER + "\nFinished successfully!\n",
                "Finished successfully!\nExtra untrusted terminal\n", "Invalid hash for item\nFinished successfully!\n"))
            check(!SupervisorMain.successfulTerminal(zero, bad.getBytes(StandardCharsets.UTF_8)), "GUI ignore/cancel, errors and changed terminal grammar refuse");
        boolean encoding = false;
        try { SupervisorMain.successfulTerminal(zero, new byte[]{(byte) 0xc3, 0x28}); } catch (IOException expected) { encoding = true; }
        check(encoding, "Malformed native output does not become success");
        var chain = new AttemptJournal.Chain(AttemptJournal.BOOTSTRAP_SHA256, AttemptJournal.INSTALLER_SHA256, release.inventorySha256());
        var cli = AttemptJournal.Mode.HEADLESS_CLI;
        var failure = new SupervisorMain.Exit(normal, 1, true, true);
        for (String reason : List.of("gui", "changed-cache", "no-choice-consent", "unclosed")) {
            Path folder = root.resolve(reason);
            var attempt = AttemptJournal.seal(folder, reason.equals("gui") ? AttemptJournal.Mode.GUI : cli,
                AttemptJournal.Role.INITIAL, normal, 1, chain, new ByteArrayInputStream(CoreProbe.DNS.getBytes(StandardCharsets.UTF_8)));
            boolean allowed = SupervisorMain.mayRecover(reason.equals("gui") ? AttemptJournal.Mode.GUI : cli,
                reason.equals("unclosed") ? new SupervisorMain.Exit(normal, 1, false, true) : failure,
                attempt, "initial-cache", reason.equals("changed-cache") ? "changed" : "initial-cache", !reason.equals("no-choice-consent"));
            check(!allowed && !Files.exists(folder.resolve("recovery.claim")), "No credit for " + reason);
        }
        var first = AttemptJournal.seal(root.resolve("eligible"), cli, AttemptJournal.Role.INITIAL, normal, 1,
            chain, new ByteArrayInputStream(CoreProbe.DNS.getBytes(StandardCharsets.UTF_8)));
        check(SupervisorMain.mayRecover(cli, failure, first, "retained", "retained", true), "One explicitly headless DNS-only credit with unchanged actual cache");
        check(!SupervisorMain.mayRecover(cli, failure, first, "retained", "retained", true), "No second credit across calls");
        System.out.println("SUPERVISOR_CHECKS=" + checks + " PASS; no installer Main, HTTP, GUI or child process executed");
    }
}
