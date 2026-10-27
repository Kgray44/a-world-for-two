package worldfortwo.bridge;

import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.function.LongSupplier;
import java.util.function.Supplier;

/** Original lifecycle policy, independent of loader/game classes for offline race tests.
 * Its monitor encloses the ENTIRE admitted native queueFor and native cleanup.
 * It does not assert external DH executor termination or support another process seed.
 */
public final class LithostitchedSeedgenConnectionGate {
    private final LongSupplier clock;
    private Long everSeed;
    private boolean open,failed;
    private List<ExecutorService> retiring=List.of();
    private long deadline;
    public LithostitchedSeedgenConnectionGate(){this(System::nanoTime);}
    LithostitchedSeedgenConnectionGate(LongSupplier clock){this.clock=clock;}
    public synchronized void prepare(long seed,long nativeSeed,boolean integrated) {
        requireReady();
        if(integrated)throw refuse("Integrated terrain requires client restart before this remote-only adapter");
        if(everSeed!=null&&everSeed.longValue()!=seed)throw refuse("A different world seed requires a full Minecraft client restart");
        if(everSeed!=null&&everSeed.longValue()!=nativeSeed)throw refuse("Native global terrain seed changed; restart Minecraft");
        // Native class initialization is exactly zero. Do not overwrite an earlier
        // integrated/foreign seed on first remote activation either.
        if(everSeed==null&&nativeSeed!=0)throw refuse("Native terrain was initialized outside this remote adapter; restart Minecraft");
        if(everSeed==null)everSeed=seed;
    }
    public synchronized void open(long seed,long nativeSeed) {
        requireReady();
        if(everSeed==null||everSeed.longValue()!=seed||nativeSeed!=seed)throw refuse("Seeded globals do not match the guarded connection");
        open=true;
    }
    public synchronized void requirePermit(long seed,long nativeSeed,boolean integrated) {
        requireReady();
        if(!open||integrated||everSeed==null||everSeed.longValue()!=seed||nativeSeed!=seed)
            throw refuse("Native process seed/lifecycle no longer matches the guarded remote basis");
    }
    public synchronized <T>T admit(LongSupplier nativeSeed,Supplier<T> nativeQueueFor) {
        if(!open||failed||!retiring.isEmpty())return null;
        if(everSeed==null||everSeed.longValue()!=nativeSeed.getAsLong()){failed=true;open=false;return null;}
        return nativeQueueFor.get();
    }
    /** Native queued payloads can outlive their connection. Listener identity
     * and liveness must hold before running the whole original onWorld body. */
    public synchronized <T>T packet(Object offered,Object current,boolean live,Supplier<T> nativeOnWorld) {
        if(offered==null||offered!=current||!live)return null;
        return nativeOnWorld.get();
    }
    public synchronized void logout(Supplier<List<ExecutorService>> nativeCleanup) {
        open=false;
        try {
            poll();
            long previousDeadline=retiring.isEmpty()?0:deadline;
            List<ExecutorService> captured=List.copyOf(nativeCleanup.get());
            if(captured.size()>32||captured.stream().anyMatch(worker->!worker.isShutdown()))
                throw refuse("Native cleanup did not close the bounded owned queue executors");
            if(!retiring.isEmpty()) {
                var merged=new java.util.ArrayList<>(retiring);merged.addAll(captured);captured=List.copyOf(merged);
                if(captured.size()>64)throw refuse("Repeated native cleanup exceeds bounded queue custody");
            }
            retiring=captured;
            // Repeated real logout must not postpone already-retiring workers.
            deadline=previousDeadline!=0?previousDeadline:clock.getAsLong()+TimeUnit.SECONDS.toNanos(30);poll();
        }catch(Throwable failure){failed=true;throw failure;}
    }
    /** Observation only: never waits while holding the queue-admission monitor. */
    public synchronized void poll() {
        if(retiring.isEmpty())return;
        if(retiring.stream().allMatch(ExecutorService::isTerminated)){retiring=List.of();deadline=0;}
        else if(clock.getAsLong()-deadline>=0){failed=true;open=false;}
    }
    public synchronized void fail(){failed=true;open=false;}
    public synchronized boolean failed(){return failed;}
    public synchronized void requireReady() {
        poll();
        if(failed)throw new IllegalStateException("Native terrain lifecycle failed; restart Minecraft");
        if(!retiring.isEmpty())throw new IllegalStateException("Previous native queue executors have not terminated; generation remains refused");
    }
    private IllegalStateException refuse(String message){failed=true;open=false;return new IllegalStateException(message);}
}
