package worldfortwo.packwiz;

import java.awt.GraphicsEnvironment;
import java.io.*;
import java.net.*;
import java.net.http.*;
import java.nio.ByteBuffer;
import java.nio.charset.*;
import java.nio.channels.*;
import java.nio.file.*;
import java.time.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;

/** Original bounded launcher. No GUI retry, cache rewrite, seeded install or exit-code override. */
public final class SupervisorMain {
    private SupervisorMain() {}
    private static final Duration ATTEMPT_LIMIT = Duration.ofMinutes(20);
    record Exit(AttemptJournal.Termination termination, int code, boolean cleanup, boolean logComplete) {}
    record Observed(ProcessHandle handle, Instant start) {}

    static boolean successfulTerminal(Exit result, byte[] raw) throws IOException {
        if (result.termination() != AttemptJournal.Termination.NORMAL_EXIT || result.code() != 0
            || !result.cleanup() || !result.logComplete()) return false;
        String value;
        try { value = StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
            .onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(raw)).toString(); }
        catch (CharacterCodingException error) { throw new IOException("Untrusted installer output encoding", error); }
        List<String> lines = value.replace("\r\n", "\n").lines().filter(line -> !line.isBlank()).toList();
        if (lines.isEmpty() || !lines.getLast().equals("Finished successfully!")) return false;
        for (String line : lines) if (line.contains("Update cancelled by user!")
            || line.contains("User selected to continue without installing/updating")
            || line.contains(FailureClassifier.MARKER) || line.contains("Invalid hash for ") || line.contains("Hash invalid!")) return false;
        return true;
    }
    static boolean mayRecover(AttemptJournal.Mode mode, Exit exit, AttemptJournal.Attempt attempt,
                              String priorCache, String retainedCache, boolean allOptionsOn) {
        return mode == AttemptJournal.Mode.HEADLESS_CLI && allOptionsOn && exit.cleanup() && exit.logComplete()
            && priorCache.equals(retainedCache)
            && RecoveryPolicy.claim(attempt) == RecoveryPolicy.Decision.ONE_HEADLESS_RECOVERY_CLAIMED;
    }
    static String cacheFingerprint(Path root) throws IOException {
        Path cache = root.resolve("packwiz.json");
        return Files.exists(cache, LinkOption.NOFOLLOW_LINKS)
            ? AttemptJournal.sha256(AttemptJournal.boundedRead(cache, 4 * 1024 * 1024)) : "ABSENT";
    }
    static void publicPins(ReleaseSpec release) throws Exception {
        ExecutorService worker = Executors.newSingleThreadExecutor(task -> {
            Thread thread = new Thread(task, "awft-bounded-public-pin-check");thread.setDaemon(true);return thread;
        });
        Future<?> task = worker.submit(() -> {try {checkPublicPins(release);}catch(Exception error){throw new CompletionException(error);}});
        try {task.get(100, TimeUnit.SECONDS);}
        catch(TimeoutException timeout){task.cancel(true);throw new IOException("Public metadata verification deadline exceeded; no installer admission",timeout);}
        finally {
            worker.shutdownNow();
            if(!worker.awaitTermination(2,TimeUnit.SECONDS))throw new IOException("Public metadata reader did not close; no installer admission");
        }
    }
    private static void checkPublicPins(ReleaseSpec release) throws Exception {
        HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(15))
            .followRedirects(HttpClient.Redirect.NEVER).build();
        for (int n = 0; n < 2; n++) {
            URI url = n == 0 ? release.packUrl() : release.packUrl().resolve("index.toml");
            int cap = n == 0 ? 65536 : 2 * 1024 * 1024;
            String expected = n == 0 ? release.packSha256() : release.indexSha256();
            HttpResponse<InputStream> response = client.send(HttpRequest.newBuilder(url).timeout(Duration.ofSeconds(45))
                .header("Accept-Encoding", "identity").GET().build(), HttpResponse.BodyHandlers.ofInputStream());
            try (InputStream body = response.body()) {
                if (response.statusCode() != 200 || response.headers().firstValueAsLong("Content-Length").orElse(0) > cap)
                    throw new IOException("Exact public release unavailable or oversized");
                byte[] bytes = body.readNBytes(cap + 1);
                if (bytes.length > cap || !AttemptJournal.sha256(bytes).equals(expected)) throw new IOException("Public pack/index SHA-256 differs");
            }
        }
    }
    private static List<String> command(Path root, AttemptJournal.Mode mode, ReleaseSpec release) {
        Path java = Path.of(System.getProperty("java.home"), "bin", System.getProperty("os.name").startsWith("Windows") ? "javaw.exe" : "java");
        Path tools = root.resolve("awft-tools");
        List<String> command = new ArrayList<>(List.of(java.toString(), "-Xmx512m", "-XX:ActiveProcessorCount=2",
            "-Djava.awt.headless=" + (mode == AttemptJournal.Mode.HEADLESS_CLI), "-jar",
            tools.resolve("packwiz-installer-bootstrap-v0.0.3.jar").toString(), "--bootstrap-no-update",
            "--bootstrap-main-jar", tools.resolve("packwiz-installer-v0.5.14.jar").toString(), "--side", "client",
            "--pack-folder", root.toString(), "--multimc-folder", root.getParent().toString()));
        if (mode == AttemptJournal.Mode.HEADLESS_CLI) command.add("--no-gui");
        command.add(release.packUrl().toString()); return List.copyOf(command);
    }
    private static boolean same(Observed process) {
        return process.handle().info().startInstant().map(process.start()::equals).orElse(false);
    }
    private static boolean stopOwned(Process child, Collection<Observed> descendants) {
        for (Observed process : descendants) if (same(process) && process.handle().isAlive()) process.handle().destroy();
        if (child.isAlive()) child.destroy();
        try { if (!child.waitFor(5, TimeUnit.SECONDS)) { child.destroyForcibly(); child.waitFor(5, TimeUnit.SECONDS); } }
        catch (InterruptedException error) { child.destroyForcibly(); Thread.currentThread().interrupt(); }
        for (Observed process : descendants) if (same(process) && process.handle().isAlive()) process.handle().destroyForcibly();
        long deadline=System.nanoTime()+TimeUnit.SECONDS.toNanos(5);
        while(descendants.stream().anyMatch(process->same(process)&&process.handle().isAlive())&&System.nanoTime()<deadline){
            try{Thread.sleep(10);}catch(InterruptedException interrupted){Thread.currentThread().interrupt();break;}
        }
        return !child.isAlive() && descendants.stream().noneMatch(process -> same(process) && process.handle().isAlive());
    }
    private static Exit execute(Path root, AttemptJournal.Mode mode, ReleaseSpec release, Path attempt) throws Exception {
        // Pinned bootstrap/installer have no expected child-process helper.
        // A browser or another unexpected process is not ours to terminate.
        return executeOwned(root, mode, command(root, mode, release), attempt, ATTEMPT_LIMIT, child->false);
    }
    static Exit executeOwned(Path root,AttemptJournal.Mode mode,List<String> command,Path attempt,Duration limit,
                             java.util.function.Predicate<ProcessHandle> descendantCustody)throws Exception{
        if(limit.isNegative()||limit.isZero()||limit.compareTo(ATTEMPT_LIMIT)>0)throw new IllegalArgumentException("Finite child-process deadline required");
        Files.createDirectory(attempt);
        ProcessBuilder builder=new ProcessBuilder(command).directory(root.toFile()).redirectErrorStream(true);
        for(String option:List.of("JAVA_TOOL_OPTIONS","_JAVA_OPTIONS","JDK_JAVA_OPTIONS"))builder.environment().remove(option);
        Process child = builder.start();
        Map<Long, Observed> descendants = new ConcurrentHashMap<>();
        Map<Long, Observed> unadmitted = new ConcurrentHashMap<>();
        AtomicBoolean complete = new AtomicBoolean(), interrupted = new AtomicBoolean();
        AtomicReference<Exception> readerError = new AtomicReference<>();
        Path log = attempt.resolve("process.log");
        Thread shutdown = new Thread(() -> { interrupted.set(true); stopOwned(child, descendants.values()); }, "awft-installer-owned-shutdown");
        try {
            Runtime.getRuntime().addShutdownHook(shutdown);
            Files.writeString(attempt.resolve("process.txt"), "pid=" + child.pid() + "\nstarted="
                + child.info().startInstant().orElseThrow() + "\nmode=" + mode + "\n", StandardOpenOption.CREATE_NEW);
        } catch (Exception error) {
            stopOwned(child, descendants.values());
            try { Runtime.getRuntime().removeShutdownHook(shutdown); } catch (IllegalStateException ignored) {}
            throw error;
        }
        Thread reader = new Thread(() -> {
            try (InputStream input = child.getInputStream(); OutputStream output = Files.newOutputStream(log, StandardOpenOption.CREATE_NEW)) {
                byte[] buffer = new byte[16384]; int n, count = 0;
                while ((n = input.read(buffer)) != -1) {
                    if (count + n > AttemptJournal.MAX_LOG_BYTES) throw new IOException("Installer output cap reached; partial log retained");
                    output.write(buffer, 0, n); output.flush(); count += n;
                }
                complete.set(true);
            } catch (Exception error) { readerError.set(error); }
        }, "awft-installer-bounded-output-"+attempt.getFileName());
        reader.setDaemon(true);reader.start(); boolean stopped = false, clean = false,restoreInterrupt=false; int code = -1;
        try {
            long deadline = System.nanoTime() + limit.toNanos();
            while (!child.waitFor(100, TimeUnit.MILLISECONDS)) {
                try (var stream = child.descendants()) {
                    for (ProcessHandle handle : stream.limit(17).toList()) {
                        Instant start = handle.info().startInstant().orElseThrow(() -> new IOException("Unidentified child process"));
                        (descendantCustody.test(handle)?descendants:unadmitted).putIfAbsent(handle.pid(), new Observed(handle, start));
                    }
                }
                // The exact pinned bootstrap loads the installer in the same JVM.
                // An unexpected descendant is not accepted as trusted installer work.
                if (!descendants.isEmpty() || !unadmitted.isEmpty() || readerError.get() != null || System.nanoTime() >= deadline || interrupted.get()) { stopped = true; break; }
            }
            if (stopped) clean = stopOwned(child, descendants.values());
            else { code = child.exitValue(); clean = descendants.values().stream().noneMatch(process -> same(process) && process.handle().isAlive()); }
        } catch (InterruptedException error) {
            stopped = true; interrupted.set(true); clean = stopOwned(child, descendants.values());restoreInterrupt=true;
        } finally {
            if (child.isAlive()) { stopped = true; clean = stopOwned(child, descendants.values()); }
            try { reader.join(5000); } catch (InterruptedException error) {restoreInterrupt=true;}
            if (reader.isAlive()) {
                // Do not block the owner on a pipe inherited by an unowned
                // descendant. The incomplete daemon reader prevents success.
                stopped = true; complete.set(false);reader.interrupt();
                try { reader.join(1000); } catch (InterruptedException error) {restoreInterrupt=true;}
                clean &= !reader.isAlive();
            }
            try { Runtime.getRuntime().removeShutdownHook(shutdown); } catch (IllegalStateException shuttingDown) { interrupted.set(true); }
        }
        boolean logComplete = complete.get() && readerError.get() == null;
        clean &= !child.isAlive()&&!reader.isAlive()&&unadmitted.values().stream().noneMatch(process->same(process)&&process.handle().isAlive());
        Files.writeString(attempt.resolve("process-observation.txt"),"root_pid="+child.pid()+"\nroot_alive="+child.isAlive()
            +"\nreader_alive="+reader.isAlive()+"\nreader_name="+reader.getName()+"\nadmitted_descendants="+descendants.size()
            +"\nunadmitted_descendants="+unadmitted.size()+"\nadmitted_alive="+descendants.values().stream().filter(process->same(process)&&process.handle().isAlive()).count()
            +"\nunadmitted_alive="+unadmitted.values().stream().filter(process->same(process)&&process.handle().isAlive()).count()
            +"\nadmitted_pids="+descendants.values().stream().map(process->process.handle().pid()+"@"+process.start()).toList()
            +"\nunadmitted_pids="+unadmitted.values().stream().map(process->process.handle().pid()+"@"+process.start()).toList()+"\n",StandardOpenOption.CREATE_NEW);
        if (readerError.get() != null) Files.writeString(attempt.resolve("capture-error.txt"), readerError.get().toString(), StandardOpenOption.CREATE_NEW);
        if(restoreInterrupt)Thread.currentThread().interrupt();
        return new Exit(stopped || interrupted.get() ? AttemptJournal.Termination.EXTERNALLY_STOPPED : AttemptJournal.Termination.NORMAL_EXIT,
            code, clean, logComplete);
    }
    private static void tools(Path root) throws Exception {
        NativeChoices.tool(root.resolve("awft-tools/packwiz-installer-bootstrap-v0.0.3.jar"), 98989, AttemptJournal.BOOTSTRAP_SHA256);
        NativeChoices.tool(root.resolve("awft-tools/packwiz-installer-v0.5.14.jar"), 4378828, AttemptJournal.INSTALLER_SHA256);
    }
    static int install(Path root, AttemptJournal.Mode mode, boolean allOptionsOn, ReleaseSpec release, Path evidence) throws Exception {
        tools(root); publicPins(release);
        String initialCache = cacheFingerprint(root);
        Files.writeString(evidence.resolve("initial-state.txt"), "inventory_sha256=" + release.inventorySha256()
            + "\ncache=" + initialCache + "\nmode=" + mode + "\nheadless_all_options_on=" + allOptionsOn
            + "\ninstall_state=" + (initialCache.equals("ABSENT") ? "CACHE_ABSENT_NOT_A_FRESHNESS_CLAIM" : "EXISTING_CACHE_RETAINED") + "\n", StandardOpenOption.CREATE_NEW);
        AttemptJournal.Chain chain = new AttemptJournal.Chain(AttemptJournal.BOOTSTRAP_SHA256, AttemptJournal.INSTALLER_SHA256, release.inventorySha256());
        for (int n = 0; n < 2; n++) {
            Path attempt = evidence.resolve(n == 0 ? "initial" : "recovery");
            tools(root); Exit exit = execute(root, mode, release, attempt);
            byte[] raw = AttemptJournal.boundedRead(attempt.resolve("process.log"), AttemptJournal.MAX_LOG_BYTES);
            AttemptJournal.Attempt sealed = AttemptJournal.seal(attempt.resolve("sealed"), mode,
                n == 0 ? AttemptJournal.Role.INITIAL : AttemptJournal.Role.RECOVERY, exit.termination(), exit.code(), chain, new ByteArrayInputStream(raw));
            Files.writeString(attempt.resolve("lifecycle.txt"), "owned_root_reaped=" + exit.cleanup() + "\ncomplete_output=" + exit.logComplete() + "\n", StandardOpenOption.CREATE_NEW);
            if (!successfulTerminal(exit, raw)) {
                if (n == 0 && mayRecover(mode, exit, sealed, initialCache, cacheFingerprint(root), allOptionsOn)) {
                    // No cache deletion/seeding, mode switch, option substitution or GUI retry.
                    tools(root); publicPins(release); continue;
                }
                throw new IOException("Installer failed/cancelled/unproven; no verified successful installation");
            }
            NativeChoices.Attestation choices = NativeChoices.attest(root, root.resolve("awft-tools/packwiz-installer-v0.5.14.jar"), release);
            if (mode == AttemptJournal.Mode.HEADLESS_CLI && choices.choices().values().stream().anyMatch(value -> !value))
                throw new IOException("Native CLI choices do not match explicit all-options-on request");
            IntegrityGate.Result verified = IntegrityGate.verify(root, release.inventory(), choices.choices());
            if (!verified.pass()) throw new IOException("Independent complete inventory/config verification failed: " + verified.errors());
            if (!choices.cacheSha256().equals(cacheFingerprint(root))) throw new IOException("Choices changed while verifying installed bytes");
            Files.writeString(evidence.resolve("verified-install.txt"), "version=" + release.version() + "\npack_sha256=" + release.packSha256()
                + "\nindex_sha256=" + release.indexSha256() + "\ninventory_sha256=" + release.inventorySha256()
                + "\nnative_cache_sha256=" + choices.cacheSha256() + "\nchoices=" + choices.choices()
                + "\nverified_files=" + verified.verifiedFiles() + "\nverified_bytes=" + verified.verifiedBytes()
                + "\ninstaller_exit=0\nsource_of_choices=ACTUAL_PINNED_NATIVE_CACHE_AFTER_SUCCESS\n", StandardOpenOption.CREATE_NEW);
            return 0;
        }
        throw new IOException("Finite recovery credit exhausted");
    }
    public static int run(String[] args) throws Exception {
        if (args.length != 4 && args.length != 5 || !args[0].equals("--instance") || !args[2].equals("--mode"))
            throw new IllegalArgumentException("Usage: --instance <minecraft-directory> --mode gui|cli [--headless-all-options-on]");
        AttemptJournal.Mode mode = switch (args[3]) { case "gui" -> AttemptJournal.Mode.GUI; case "cli" -> AttemptJournal.Mode.HEADLESS_CLI; default -> throw new IllegalArgumentException("Explicit GUI or CLI mode required"); };
        boolean allOn = args.length == 5 && args[4].equals("--headless-all-options-on");
        if (args.length == 5 && !allOn || mode == AttemptJournal.Mode.HEADLESS_CLI && !allOn || mode == AttemptJournal.Mode.GUI && allOn)
            throw new IllegalArgumentException("CLI requires explicit consent to its native all-options-on behavior; GUI retains Essential default-off");
        if (mode == AttemptJournal.Mode.GUI && GraphicsEnvironment.isHeadless()) throw new IOException("GUI unavailable; never silently switch to CLI");
        Path requested = Path.of(args[1]).toAbsolutePath().normalize();
        if (Files.isSymbolicLink(requested) || !Files.isDirectory(requested, LinkOption.NOFOLLOW_LINKS)) throw new IOException("Real instance directory required");
        Path root = requested.toRealPath(), journal = root.resolve(".awft-supervisor");
        if (!Files.exists(journal, LinkOption.NOFOLLOW_LINKS)) Files.createDirectory(journal);
        if (Files.isSymbolicLink(journal) || !journal.toRealPath().equals(journal)) throw new IOException("Linked evidence directory refused");
        Path lock = journal.resolve("instance.lock");
        if (Files.isSymbolicLink(lock)) throw new IOException("Linked lock refused");
        try (FileChannel channel = FileChannel.open(lock, StandardOpenOption.CREATE, StandardOpenOption.WRITE); FileLock held = channel.tryLock()) {
            if (held == null) throw new IOException("An updater already owns this instance");
            Path evidence = journal.resolve("run-" + UUID.randomUUID()); Files.createDirectory(evidence);
            int result = 1;
            try { result = install(root, mode, allOn, ReleaseSpec.embedded(), evidence); return result; }
            catch (Exception | LinkageError error) {
                Files.writeString(evidence.resolve("failure.txt"), error.getClass().getName() + ": " + error.getMessage() + "\n", StandardOpenOption.CREATE_NEW);
                throw error;
            } finally {
                StringBuilder sealed = new StringBuilder("awft-supervisor-run:1\nexit=" + result + "\nfinished=" + Instant.now() + "\n");
                for(String file:List.of("verified-install.txt","failure.txt","initial-state.txt","initial/sealed/receipt.txt","recovery/sealed/receipt.txt")){
                    Path retained=evidence.resolve(file);if(Files.exists(retained,LinkOption.NOFOLLOW_LINKS))sealed.append("sha256 ").append(file).append('=').append(AttemptJournal.sha256(AttemptJournal.boundedRead(retained,4*1024*1024))).append('\n');
                }
                byte[] receipt = sealed.toString().getBytes(StandardCharsets.UTF_8);
                Files.write(evidence.resolve("result.txt"), receipt, StandardOpenOption.CREATE_NEW);
                Files.writeString(evidence.resolve("result.complete"), AttemptJournal.sha256(receipt) + "\n", StandardOpenOption.CREATE_NEW);
            }
        }
    }
    public static void main(String[] args) {
        int result = 1;
        try { result = run(args); }
        catch (Exception | LinkageError error) { System.err.println("AWFT updater refused: " + error.getClass().getSimpleName() + ": " + error.getMessage()); }
        System.exit(result);
    }
}
