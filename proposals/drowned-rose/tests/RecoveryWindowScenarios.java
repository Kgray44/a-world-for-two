package worldfortwo.tavern;

import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.atomic.AtomicLong;
import net.minecraft.world.level.ChunkPos;

/** Lifecycle/fault tests with controllable native futures, no live world/tickets. */
public final class RecoveryWindowScenarios {
    static void require(boolean condition,String message){if(!condition)throw new AssertionError(message);}
    interface Attempt{void run();}
    static void refused(Attempt a){try{a.run();throw new AssertionError("Expected refusal");}catch(IllegalStateException expected){}}
    static final class Native implements RecoveryWindow.Access {
        Set<ChunkPos> held=new HashSet<>(),saved=new HashSet<>();
        List<CompletableFuture<?>> reads=new ArrayList<>();Map<ChunkPos,CompletableFuture<?>> loads=new HashMap<>();
        boolean full,entities,waitDisk,failDisk,failAdd,failRemove;
        public CompletableFuture<?> savedFull(ChunkPos p){saved.add(p);CompletableFuture<Boolean> f=new CompletableFuture<>();if(failDisk)f.completeExceptionally(new IllegalStateException("missing"));else if(!waitDisk)f.complete(true);reads.add(f);return f;}
        public void ticket(ChunkPos p,boolean adding){require(RecoveryWindow.CENTERS.contains(p),"No other ticket center");if(adding){if(failAdd&&held.size()==2)throw new IllegalStateException("add failure");held.add(p);}else{if(failRemove)throw new IllegalStateException("remove failure");held.remove(p);}}
        public CompletableFuture<?> requestFull(ChunkPos p){CompletableFuture<Boolean> f=new CompletableFuture<>();loads.put(p,f);return f;}
        public boolean full(ChunkPos p){return full;}
        public boolean entities(ChunkPos p){return entities;}
        void complete(){full=true;entities=true;for(var f:loads.values())((CompletableFuture<Object>)f).complete(true);}
    }
    static RecoveryWindow ready(Native n,AtomicLong time){RecoveryWindow w=new RecoveryWindow(n,time::get);w.start(true,true);w.poll(true,true);n.complete();w.poll(true,true);require(w.ready,"Full and entity-ready after native futures complete");return w;}
    public static void main(String[] args){
        AtomicLong time=new AtomicLong();Native n=new Native();RecoveryWindow w=new RecoveryWindow(n,time::get);
        refused(()->w.start(false,true));refused(()->w.start(true,false));require(n.held.isEmpty(),"No tickets on invalid context");
        w.start(true,true);require(n.held.isEmpty(),"No ticket before saved-FULL proof");require(n.saved.size()==36,"Finite saved support halo");
        for(ChunkPos p:n.saved)require(Math.floorDiv(p.x,32)==2&&Math.floorDiv(p.z,32)==-3,"No other saved region");
        w.poll(true,true);require(n.held.size()==4&&!w.ready,"Only4 tickets, pending native loading");
        n.full=true;n.entities=true;w.poll(true,true);require(!w.ready,"Readiness cannot bypass incomplete futures");
        n.complete();w.poll(true,true);w.requireReady(true,true);long deadline=w.deadline;refused(()->w.start(true,true));require(w.deadline==deadline,"Repeated prepare cannot renew lease");
        w.finish("operator_finish");require(n.held.isEmpty()&&w.pending.isEmpty()&&!w.status().get("cleanup_required").getAsBoolean(),"Finish cleans all owned tickets/futures");
        Native ttl=new Native();RecoveryWindow expiring=ready(ttl,time);time.addAndGet(RecoveryWindow.TTL_NANOS);refused(()->expiring.requireReady(true,true));require(ttl.held.isEmpty()&&!expiring.active,"TTL refuses insertion and releases all");
        Native players=new Native();RecoveryWindow context=ready(players,time);context.poll(true,false);require(players.held.isEmpty()&&!context.active,"Player arrival cleans window");
        Native disk=new Native();disk.failDisk=true;RecoveryWindow failedDisk=new RecoveryWindow(disk,time::get);failedDisk.start(true,true);refused(()->failedDisk.start(true,true));failedDisk.poll(true,true);require(disk.held.isEmpty()&&!failedDisk.active,"Repeated prepare cannot erase failed disk proof");
        Native adding=new Native();adding.failAdd=true;RecoveryWindow failedAdd=new RecoveryWindow(adding,time::get);failedAdd.start(true,true);failedAdd.poll(true,true);require(adding.held.isEmpty()&&!failedAdd.active,"Partial ticket-add failure cleans all attempts");
        Native removal=new Native();RecoveryWindow cleanup=ready(removal,time);removal.failRemove=true;cleanup.finish("server_stopping");require(cleanup.status().get("cleanup_required").getAsBoolean(),"Failed removal remains visible");removal.failRemove=false;cleanup.poll(true,true);require(removal.held.isEmpty()&&!cleanup.status().get("cleanup_required").getAsBoolean(),"Cleanup can drain without renewing");
        Native pending=new Native();RecoveryWindow drain=new RecoveryWindow(pending,time::get);drain.start(true,true);drain.poll(true,true);drain.finish("operator_finish");require(drain.status().get("cleanup_required").getAsBoolean(),"Pending native futures reported, never cancelled");pending.complete();drain.poll(true,true);require(!drain.status().get("cleanup_required").getAsBoolean(),"Completed native futures drain");
        System.out.println("PASS:4-center ownership,36 saved-FULL checks,async readiness,no renewal,20s TTL,player/future/add/remove faults,stop/finish and pending-future cleanup. Fake native access only; no live tickets.");
    }
}
