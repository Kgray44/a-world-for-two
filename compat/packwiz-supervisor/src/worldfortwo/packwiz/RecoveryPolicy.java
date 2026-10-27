package worldfortwo.packwiz;

import java.io.IOException;
import java.nio.file.*;

/** Policy only: no process runner, GUI interception, sleeps or automatic installation. */
public final class RecoveryPolicy {
    public enum Decision { ONE_HEADLESS_RECOVERY_CLAIMED, GUI_DECISION_UNOBSERVABLE, NOT_INITIAL_ATTEMPT, CANCELLED_OR_UNPROVEN_EXIT,
        UNPINNED_CHAIN, UNSEALED_ATTEMPT, NOT_DNS_ONLY, RECOVERY_ALREADY_CLAIMED }
    private RecoveryPolicy() {}
    public static Decision claim(AttemptJournal.Attempt first) {
        if (first.mode() == AttemptJournal.Mode.GUI) return Decision.GUI_DECISION_UNOBSERVABLE;
        if (first.role() != AttemptJournal.Role.INITIAL) return Decision.NOT_INITIAL_ATTEMPT;
        if (first.termination() != AttemptJournal.Termination.NORMAL_EXIT || first.exitCode() != 1)
            return Decision.CANCELLED_OR_UNPROVEN_EXIT;
        if (!first.chain().pinned()) return Decision.UNPINNED_CHAIN;
        String log;
        try { log = AttemptJournal.verifiedLog(first); }
        catch (IOException ex) { return Decision.UNSEALED_ATTEMPT; }
        if (FailureClassifier.classify(log).kind() != FailureClassifier.Kind.DNS_ONLY) return Decision.NOT_DNS_ONLY;
        try {
            // CREATE_NEW is atomic across threads and fresh policy objects/processes using this attempt.
            Files.writeString(first.directory().resolve("recovery.claim"), first.receiptSha256() + "\n", StandardOpenOption.CREATE_NEW);
            return Decision.ONE_HEADLESS_RECOVERY_CLAIMED;
        } catch (FileAlreadyExistsException ex) { return Decision.RECOVERY_ALREADY_CLAIMED; }
        catch (IOException ex) { return Decision.UNSEALED_ATTEMPT; }
    }
}
