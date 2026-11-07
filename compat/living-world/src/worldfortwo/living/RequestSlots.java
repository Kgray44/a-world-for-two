package worldfortwo.living;

import java.util.*;
import java.util.concurrent.CompletableFuture;

/** Own queued futures across shutdown, retaining physical-network permits until completion. */
public final class RequestSlots<T> {
    private final Set<Lease> leases=new HashSet<>();
    private volatile boolean open;
    private int active;

    public synchronized void open(){open=true;}
    public synchronized int active(){return active;}
    public synchronized Lease acquire(int cap){
        if(!open||active>=Math.max(1,Math.min(2,cap)))return null;
        Lease lease=new Lease();leases.add(lease);active++;return lease;
    }
    public void close(T failure){
        List<Lease> snapshot;
        synchronized(this){open=false;snapshot=List.copyOf(leases);}
        for(Lease lease:snapshot)lease.cancel(failure);
    }
    private synchronized void releasePermit(){active--;}
    private synchronized void forget(Lease lease){leases.remove(lease);}
    public final class Lease {
        private final CompletableFuture<T> future=new CompletableFuture<>();
        private boolean started,cancelled,released;
        private Lease(){}
        public CompletableFuture<T> future(){return future;}
        public synchronized boolean start(){
            if(started||cancelled||released||!open||future.isDone())return false;
            started=true;return true;
        }
        private void release(){
            synchronized(this){if(released)return;released=true;}
            RequestSlots.this.releasePermit();
        }
        private void settle(T answer){future.complete(answer);RequestSlots.this.forget(this);}
        public void complete(T answer){release();settle(answer);}
        /** Logical response deadline does not establish termination of upstream HTTP work. */
        public void timeout(T failure){settle(failure);}
        /** Keep logical ownership until the server executor delivers or shutdown cancels. */
        public void networkFinished(){release();}
        private void cancel(T failure){
            boolean queued;
            synchronized(this){cancelled=true;queued=!started;}
            // A queued request must not strand a future when shutdownNow drops its Runnable.
            // An already-started network call still owns capacity until its bounded completion.
            if(queued)release();
            settle(failure);
        }
    }
}
