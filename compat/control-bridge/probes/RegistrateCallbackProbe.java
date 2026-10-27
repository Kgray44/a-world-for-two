import com.google.common.collect.ForwardingMultimap;
import com.google.common.collect.Multimap;
import com.google.common.collect.Table;
import com.mojang.serialization.Lifecycle;
import com.tterrag.registrate.AbstractRegistrate;
import com.tterrag.registrate.util.entry.RegistryEntry;
import com.tterrag.registrate.util.nullness.NonNullConsumer;
import java.lang.invoke.MethodHandles;
import java.lang.invoke.MethodType;
import java.lang.management.ManagementFactory;
import java.lang.management.ThreadInfo;
import java.lang.reflect.Modifier;
import java.util.Collection;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;
import net.minecraft.core.MappedRegistry;
import net.minecraft.core.Registry;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.neoforged.neoforge.registries.RegisterEvent;

/** Exact pinned-class fixture; no FML dispatch, world, network, or game process. */
public final class RegistrateCallbackProbe {
    static final ResourceKey<Registry<Object>> KEY = ResourceKey.createRegistryKey(
        ResourceLocation.parse("fixture:callback_registry"));

    static final class Owner extends AbstractRegistrate<Owner> {
        Owner() { super("fixture"); }
        void capture(String name) {
            accept(name, KEY, null, Object::new, holder -> new RegistryEntry<>(this, holder));
        }
        boolean present(String name) { return getOptional(name, KEY).isPresent(); }
    }

    /** Pause AFTER the real callback drain and BEFORE the real registration put. */
    static final class DrainGate extends ForwardingMultimap<Object, Object> {
        final Multimap<Object, Object> original;
        final CountDownLatch drained = new CountDownLatch(1);
        final CountDownLatch release = new CountDownLatch(1);
        DrainGate(Multimap<Object, Object> original) { this.original = original; }
        @Override protected Multimap<Object, Object> delegate() { return original; }
        @Override public Collection<Object> removeAll(Object key) {
            Collection<Object> result = original.removeAll(key);
            drained.countDown();
            await(release, "accept drain release");
            return result;
        }
    }

    static void await(CountDownLatch latch, String label) {
        try {
            if (!latch.await(5, TimeUnit.SECONDS)) throw new AssertionError("Timeout: " + label);
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
            throw new AssertionError(label, interrupted);
        }
    }

    static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    @SuppressWarnings("unchecked")
    static DrainGate gate(Owner owner) throws Exception {
        var field = AbstractRegistrate.class.getDeclaredField("registerCallbacks");
        field.setAccessible(true);
        DrainGate gate = new DrainGate((Multimap<Object, Object>) field.get(owner));
        field.set(owner, gate);
        return gate;
    }

    static Object registration(Owner owner, String name) throws Exception {
        var field = AbstractRegistrate.class.getDeclaredField("registrations");
        field.setAccessible(true);
        return ((Table<?, ?, ?>) field.get(owner)).get(KEY, name);
    }

    static int attached(Object registration) throws Exception {
        var field = registration.getClass().getDeclaredField("callbacks");
        field.setAccessible(true);
        return ((List<?>) field.get(registration)).size();
    }

    static void executeRegistration(Object registration) throws Throwable {
        // A private standalone registry and direct native method call, never an event-bus post.
        var registry = new MappedRegistry<>(KEY, Lifecycle.stable());
        var constructor = MethodHandles.privateLookupIn(RegisterEvent.class, MethodHandles.lookup())
            .findConstructor(RegisterEvent.class, MethodType.methodType(void.class, ResourceKey.class, Registry.class));
        RegisterEvent event = (RegisterEvent) constructor.invoke(KEY, registry);
        MethodHandles.privateLookupIn(registration.getClass(), MethodHandles.lookup())
            .findVirtual(registration.getClass(), "register", MethodType.methodType(void.class, RegisterEvent.class))
            .invoke(registration, event);
        check(registry.size() == 1, "The real native registration body did not register its entry");
    }

    static void assertSameMonitorBlocked(Thread callback, Thread accept, Owner owner) {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(3);
        while (System.nanoTime() < deadline) {
            ThreadInfo info = ManagementFactory.getThreadMXBean().getThreadInfo(callback.threadId());
            if (info != null && info.getThreadState() == Thread.State.BLOCKED
                    && info.getLockOwnerId() == accept.threadId() && info.getLockInfo() != null
                    && info.getLockInfo().getIdentityHashCode() == System.identityHashCode(owner)) return;
            check(callback.isAlive(), "Callback escaped the shared instance monitor");
            Thread.yield();
        }
        throw new AssertionError("No JVM witness of callback blocking on the accept owner's SAME instance monitor");
    }

    static void join(Thread thread) throws Exception {
        thread.join(5000);
        check(!thread.isAlive(), "Worker did not complete: " + thread.getName());
    }

    static void round(boolean fixed, int round) throws Throwable {
        Owner owner = new Owner();
        String name = "entry_" + round;
        AtomicInteger before = new AtomicInteger(), during = new AtomicInteger(), after = new AtomicInteger();
        owner.addRegisterCallback(name, KEY, value -> before.incrementAndGet());
        DrainGate gate = gate(owner);
        AtomicReference<Throwable> failure = new AtomicReference<>();
        CountDownLatch callbackDone = new CountDownLatch(1);
        Thread accept = new Thread(() -> {
            try { owner.capture(name); } catch (Throwable thrown) { failure.compareAndSet(null, thrown); }
        }, "fixture-real-accept");
        Thread callback = new Thread(() -> {
            try { owner.addRegisterCallback(name, KEY, value -> during.incrementAndGet()); }
            catch (Throwable thrown) { failure.compareAndSet(null, thrown); }
            finally { callbackDone.countDown(); }
        }, "fixture-real-add-callback");
        accept.start();
        try {
            await(gate.drained, "native removeAll completed");
            callback.start();
            if (fixed) assertSameMonitorBlocked(callback, accept, owner);
            else await(callbackDone, "unlocked callback completed inside accept publication gap");
        } finally {
            gate.release.countDown();
            join(accept);
            if (callback.getState() != Thread.State.NEW) join(callback);
        }
        if (failure.get() != null) throw new AssertionError("Native worker failed", failure.get());
        check(owner.present(name), "Published registration is missing");
        Object registration = registration(owner, name);
        check(registration != null, "Real registrations table has no entry");
        owner.addRegisterCallback(name, KEY, value -> after.incrementAndGet());
        int pending = gate.size(), attached = attached(registration);
        check(pending == (fixed ? 0 : 1), "Unexpected pending callback count: " + pending);
        check(attached == (fixed ? 3 : 2), "Unexpected attached callback count: " + attached);
        executeRegistration(registration);
        check(before.get() == 1 && after.get() == 1, "Ordinary pre/post callbacks lost or duplicated");
        check(during.get() == (fixed ? 1 : 0), "Gap callback execution differs: " + during.get());
        check(attached(registration) == 0, "Native registration body did not clear executed callbacks");
        System.out.println("PASS round=" + round + " mode=" + (fixed ? "both" : "accept-only")
            + " present=true pending=" + pending + " attachedBeforeExecution=" + attached
            + " callbacksExecuted=" + (before.get() + during.get() + after.get())
            + " gapCallback=" + during.get() + " sameMonitorWitness=" + fixed);
    }

    static void exceptionRelease(boolean callbackMethod) throws Exception {
        Owner owner = new Owner();
        owner.capture("existing");
        boolean threw = false;
        try {
            if (callbackMethod) owner.addRegisterCallback("existing", KEY, (NonNullConsumer<Object>) null);
            else owner.capture(null);
        } catch (RuntimeException expected) { threw = true; }
        check(threw, "Native exception path was not reached");
        AtomicReference<Throwable> failure = new AtomicReference<>();
        Thread next = new Thread(() -> {
            try {
                owner.capture("after_exception");
                owner.addRegisterCallback("after_exception", KEY, value -> {});
            } catch (Throwable thrown) { failure.set(thrown); }
        }, "fixture-monitor-release");
        next.start();
        join(next);
        if (failure.get() != null) throw new AssertionError("After-exception worker failed", failure.get());
        check(owner.present("after_exception"), "Entry after exception absent");
        System.out.println("PASS JVM monitor release after native " + (callbackMethod ? "addRegisterCallback" : "accept") + " exception");
    }

    public static void main(String[] args) throws Throwable {
        check(args.length == 1 && (args[0].equals("accept-only") || args[0].equals("both")), "Mode required");
        boolean fixed = args[0].equals("both");
        net.minecraft.SharedConstants.tryDetectVersion();
        net.minecraft.server.Bootstrap.bootStrap();
        var callback = AbstractRegistrate.class.getDeclaredMethod("addRegisterCallback", String.class, ResourceKey.class, NonNullConsumer.class);
        check(Modifier.isSynchronized(callback.getModifiers()) == fixed, "Unexpected callback method flags");
        for (int i = 0; i < 10; i++) round(fixed, i);
        exceptionRelease(false);
        exceptionRelease(true);
        System.out.println("RESULT " + (fixed ? "PASS_CALLBACK_PRESERVED_SHARED_NATIVE_MONITOR" : "REPRODUCED_CALLBACK_LOST_WITH_ACCEPT_ONLY"));
    }
}
