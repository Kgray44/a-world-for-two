package worldfortwo.bridge;

import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.net.URL;
import java.net.URLClassLoader;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;
import java.util.Queue;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.locks.ReentrantLock;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.JumpInsnNode;
import org.objectweb.asm.tree.MethodNode;

/** One finite reproduction using the actual pinned native picker, executor and tracked runnable. */
public final class DhPickerFullQueueProbe {
    private static final String BASE = "com.seibel.distanthorizons.core.";

    public static void main(String[] args) throws Exception {
        if (args.length != 2) throw new IllegalArgumentException("DH archive and original|repaired required");
        boolean repaired = "repaired".equals(args[1]);
        if (!repaired && !"original".equals(args[1])) throw new IllegalArgumentException("Unknown mode");
        try (NativeLoader loader = new NativeLoader(Path.of(args[0]).toUri().toURL(), repaired)) {
            // Native preset initialization resolves the preset/config mutual references.
            Class.forName(BASE + "config.eventHandlers.presets.ThreadPresetConfigEventHandler", true, loader);
            Class<?> config = Class.forName(BASE + "config.Config$Common$MultiThreading", true, loader);
            Object entry = config.getField("numberOfThreads").get(null);
            var setGate = entry.getClass().getMethod("setWithoutFiringEvents", Object.class);
            setGate.invoke(entry, 1); // isolated fixture only: no config file, no listeners, no live JVM
            Class<?> pickerType = Class.forName(BASE + "util.threading.PriorityTaskPicker", true, loader);
            Object picker = pickerType.getConstructor().newInstance();
            Object executor = pickerType.getMethod("createExecutor", String.class).invoke(picker, "AWFT isolated full queue");
            Class<?> executorType = executor.getClass();
            var execute = executorType.getMethod("execute", Runnable.class);
            ThreadPoolExecutor pool = (ThreadPoolExecutor)field(executor, "threadPoolExecutor");
            Queue<?> waiting = (Queue<?>)field(executor, "taskQueue");
            AtomicInteger occupied = (AtomicInteger)field(picker, "occupiedThreadsRef");
            ReentrantLock lock = (ReentrantLock)field(picker, "taskPickerLock");
            AtomicInteger rejections = new AtomicInteger();
            String[] firstMessage = new String[1];
            pool.setRejectedExecutionHandler(new ThreadPoolExecutor.AbortPolicy() {
                @Override public void rejectedExecution(Runnable task, ThreadPoolExecutor owner) {
                    rejections.incrementAndGet();
                    try { super.rejectedExecution(task, owner); }
                    catch (RejectedExecutionException nativeFailure) {
                        if (firstMessage[0] == null) firstMessage[0] = nativeFailure.getMessage();
                        throw nativeFailure;
                    }
                }
            });
            int capacity = pool.getQueue().remainingCapacity();
            if (pool.getMaximumPoolSize() != 1 || capacity != 2)
                throw new AssertionError("Fixture requires one worker and native two-CPU queue capacity");
            CountDownLatch active = new CountDownLatch(1), release = new CountDownLatch(1);
            CountDownLatch all = new CountDownLatch(capacity + 2);
            AtomicInteger[] runs = new AtomicInteger[capacity + 2];
            for (int i = 0; i < runs.length; i++) runs[i] = new AtomicInteger();
            // Create the proved state deterministically: all queued commands are
            // native TrackedRunnable instances with coherent native counters. A
            // fixture-only silent gate change leaves the existing one-worker pool
            // intact. This is a FULL-queue reproduction, not a game config trial.
            setGate.invoke(entry, capacity + 1);
            execute.invoke(executor, (Runnable)() -> {
                runs[0].incrementAndGet(); active.countDown();
                try { if (!release.await(3, TimeUnit.SECONDS)) throw new AssertionError("Release deadline"); }
                catch (InterruptedException failure) { throw new AssertionError(failure); }
                all.countDown();
            });
            if (!active.await(2, TimeUnit.SECONDS)) throw new AssertionError("Worker did not start");
            for (int i = 1; i <= capacity; i++) {
                int slot = i;
                execute.invoke(executor, (Runnable)() -> { runs[slot].incrementAndGet(); all.countDown(); });
            }
            int last = capacity + 1;
            execute.invoke(executor, (Runnable)() -> { runs[last].incrementAndGet(); all.countDown(); });
            if (pool.getActiveCount() != 1 || pool.getQueue().size() != capacity
                || waiting.size() != 1 || occupied.get() != capacity + 1)
                throw new AssertionError("Native FULL-queue precondition not established");
            setGate.invoke(entry, capacity + 2);
            release.countDown();
            boolean drained = all.await(repaired ? 3 : 0, TimeUnit.SECONDS);
            if (!repaired) {
                long end = System.nanoTime() + TimeUnit.SECONDS.toNanos(1);
                while (rejections.get() < 64 && System.nanoTime() < end) Thread.onSpinWait();
                boolean acquired = lock.tryLock();
                if (acquired) lock.unlock();
                if (rejections.get() < 64 || acquired || runs[last].get() != 0)
                    throw new AssertionError("Original native retry did not reproduce lock-held FULL rejection loop");
                ((AtomicBoolean)field(picker, "isShutDownRef")).set(true);
                pickerType.getMethod("shutdownNow").invoke(picker);
                System.out.println("PROBE_RESULT {\"mode\":\"original\",\"reproduced\":true,\"minimum_rejections_observed\":64,\"pending_ran_before_shutdown\":false,\"native_queue_capacity\":" + capacity + "}");
                return;
            }
            if (!drained) throw new AssertionError("Repaired native work failed to drain");
            for (AtomicInteger count : runs) if (count.get() != 1) throw new AssertionError("Task lost or duplicated");
            awaitIdle(pool, executor, occupied);
            if (!lock.tryLock()) throw new AssertionError("Picker lock remained held");
            lock.unlock();
            if (rejections.get() < 1 || firstMessage[0] == null || !firstMessage[0].contains("[Running,"))
                throw new AssertionError("Fixture did not exercise actual FULL rejection");
            // The native command-exception finally must also leave the lock and
            // counters usable. Its exception remains visible to the worker handler.
            CountDownLatch boom = new CountDownLatch(1), following = new CountDownLatch(1);
            execute.invoke(executor, (Runnable)() -> { boom.countDown(); throw new IllegalStateException("Expected isolated command failure"); });
            if (!boom.await(2, TimeUnit.SECONDS)) throw new AssertionError("Failure task did not run");
            execute.invoke(executor, (Runnable)following::countDown);
            if (!following.await(2, TimeUnit.SECONDS)) throw new AssertionError("Work after command failure did not run");
            awaitIdle(pool, executor, occupied);
            if (!lock.tryLock()) throw new AssertionError("Exception path stranded picker lock");
            lock.unlock();
            pickerType.getMethod("shutdownNow").invoke(picker);
            try {
                execute.invoke(executor, (Runnable)() -> { throw new AssertionError("Executed after shutdown"); });
                throw new AssertionError("Native shutdown no longer rejects new work");
            } catch (InvocationTargetException expected) {
                if (!(expected.getCause() instanceof RejectedExecutionException)) throw expected;
            }
            if (!pool.isTerminated()) throw new AssertionError("Fixture pool did not terminate");
            System.out.println("PROBE_RESULT {\"mode\":\"repaired\",\"tasks_ran_exactly_once\":" + runs.length
                + ",\"full_rejections\":" + rejections.get() + ",\"native_queue_capacity\":" + capacity
                + ",\"lock_released\":true,\"native_counters_idle\":true,\"exception_followup\":true,\"shutdown_preserved\":true,\"only_one_branch_changed\":true}");
        }
    }

    private static void awaitIdle(ThreadPoolExecutor pool, Object executor, AtomicInteger occupied) throws Exception {
        long end = System.nanoTime() + TimeUnit.SECONDS.toNanos(2);
        while (System.nanoTime() < end) {
            if (occupied.get() == 0 && ((AtomicInteger)field(executor, "runningTasksRef")).get() == 0
                && ((Queue<?>)field(executor, "taskQueue")).isEmpty() && pool.getQueue().isEmpty()) return;
            Thread.yield();
        }
        throw new AssertionError("Native counters/queues did not return idle");
    }

    private static Object field(Object owner, String name) throws Exception {
        Field field = owner.getClass().getDeclaredField(name); field.setAccessible(true); return field.get(owner);
    }

    private static final class NativeLoader extends URLClassLoader {
        private final boolean repaired;
        NativeLoader(URL jar, boolean repaired) { super(new URL[]{jar}, DhPickerFullQueueProbe.class.getClassLoader()); this.repaired = repaired; }
        @Override protected Class<?> loadClass(String name, boolean resolve) throws ClassNotFoundException {
            if (!name.startsWith("com.seibel.distanthorizons.")) return super.loadClass(name, resolve);
            synchronized (getClassLoadingLock(name)) {
                Class<?> result = findLoadedClass(name);
                if (result == null) result = findClass(name);
                if (resolve) resolveClass(result); return result;
            }
        }
        @Override protected Class<?> findClass(String name) throws ClassNotFoundException {
            if (!DhPickerQueueYieldPlugin.TARGET.equals(name) || !repaired) return super.findClass(name);
            URL origin = findResource(name.replace('.', '/') + ".class");
            try (var stream = origin.openStream()) {
                byte[] raw = stream.readNBytes(16385);
                ClassNode node = new ClassNode(); new ClassReader(raw).accept(node, 0);
                ClassNode original = new ClassNode(); new ClassReader(raw).accept(original, 0);
                Map<String,String> before = methods(node);
                String witness = DhPickerQueueYieldPlugin.repairExact(node, origin);
                System.out.println("TRANSFORM_WITNESS " + witness);
                System.err.println("FIXTURE_STAGE native branch attested");
                String originalCwd = System.getProperty("user.dir");
                try {
                    var jar = (java.net.JarURLConnection)origin.openConnection();
                    Path archive = Path.of(jar.getJarFileURL().toURI());
                    System.setProperty("user.dir", archive.getParent().getParent().toString());
                    URL union = new URL(null, "union:" + archive.toUri().getRawPath() + "%231!/" + DhPickerQueueYieldPlugin.RESOURCE,
                        new java.net.URLStreamHandler() {
                            @Override protected java.net.URLConnection openConnection(URL url) {
                                return new java.net.URLConnection(url) {
                                    @Override public void connect() {}
                                    @Override public java.io.InputStream getInputStream() throws java.io.IOException { return origin.openStream(); }
                                };
                            }
                        });
                    ClassNode unionNode = new ClassNode(); new ClassReader(raw).accept(unionNode, 0);
                    DhPickerQueueYieldPlugin.repairExact(unionNode, union);
                } finally { System.setProperty("user.dir", originalCwd); }
                System.err.println("FIXTURE_STAGE union origin attested");
                Map<String,String> after = methods(node);
                long changed = before.keySet().stream().filter(key -> !before.get(key).equals(after.get(key))).count();
                if (changed != 1 || before.get("startNextTask(Z)V").equals(after.get("startNextTask(Z)V")))
                    throw new AssertionError("Unrelated native method changed");
                MethodNode a = original.methods.stream().filter(m -> "startNextTask".equals(m.name)).findFirst().orElseThrow();
                MethodNode b = node.methods.stream().filter(m -> "startNextTask".equals(m.name)).findFirst().orElseThrow();
                if (a.instructions.size() != b.instructions.size()) throw new AssertionError("Native instructions were inserted/deleted");
                int branchChanges = 0;
                for (int i = 0; i < a.instructions.size(); i++) {
                    if (!(a.instructions.get(i) instanceof JumpInsnNode oldJump)) continue;
                    if (!(b.instructions.get(i) instanceof JumpInsnNode newJump)) throw new AssertionError("Native branch replaced");
                    int oldTarget = a.instructions.indexOf(oldJump.label), newTarget = b.instructions.indexOf(newJump.label);
                    if (oldTarget == newTarget) continue;
                    branchChanges++;
                    var destination = newJump.label;
                    newJump.label = (org.objectweb.asm.tree.LabelNode)b.instructions.get(oldTarget);
                    if (!before.get("startNextTask(Z)V").equals(DhPickerQueueYieldPlugin.methodDigest(b)))
                        throw new AssertionError("Repair changes more than the sole branch destination");
                    newJump.label = destination;
                }
                if (branchChanges != 1) throw new AssertionError("Exactly one native branch must change");
                System.err.println("FIXTURE_STAGE sole branch independently checked");
                ClassNode drift = new ClassNode(); new ClassReader(raw).accept(drift, 0);
                MethodNode driftMethod = drift.methods.stream().filter(m -> "startNextTask".equals(m.name)).findFirst().orElseThrow();
                driftMethod.access ^= org.objectweb.asm.Opcodes.ACC_SYNCHRONIZED;
                String driftBefore = DhPickerQueueYieldPlugin.methodDigest(driftMethod);
                try { DhPickerQueueYieldPlugin.repairExact(drift, origin); throw new AssertionError("Unknown method accepted"); }
                catch (IllegalStateException expected) { /* fail closed before the sole mutation */ }
                if (!driftBefore.equals(DhPickerQueueYieldPlugin.methodDigest(driftMethod)))
                    throw new AssertionError("Refusal partially mutated the target");
                System.err.println("FIXTURE_STAGE unknown method refused without mutation");
                ClassWriter writer = new ClassWriter(0); node.accept(writer);
                byte[] bytes = writer.toByteArray();
                return defineClass(name, bytes, 0, bytes.length);
            } catch (java.io.IOException | java.net.URISyntaxException failure) { throw new ClassNotFoundException(name, failure); }
        }
        private static Map<String,String> methods(ClassNode node) {
            Map<String,String> result = new HashMap<>();
            for (MethodNode method : node.methods) result.put(method.name + method.desc, DhPickerQueueYieldPlugin.methodDigest(method));
            return result;
        }
    }
}
