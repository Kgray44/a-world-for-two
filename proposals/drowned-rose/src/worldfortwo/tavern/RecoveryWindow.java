package worldfortwo.tavern;

import com.google.gson.*;
import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.function.LongSupplier;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.TicketType;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.chunk.status.ChunkStatus;

/** One recovery-only, nonrenewable20s native entity-load window. */
final class RecoveryWindow {
    static final List<ChunkPos> CENTERS=List.of(new ChunkPos(80,-81),new ChunkPos(80,-80),new ChunkPos(81,-81),new ChunkPos(81,-80));
    static final long TTL_NANOS=20_000_000_000L;
    interface Access {
        CompletableFuture<?> savedFull(ChunkPos p);
        void ticket(ChunkPos p,boolean add)throws Exception;
        CompletableFuture<?> requestFull(ChunkPos p);
        boolean full(ChunkPos p);
        boolean entities(ChunkPos p);
    }
    static final class NativeAccess implements Access {
        static final TicketType<ChunkPos> TICKET=TicketType.create("awft_tavern_recovery",Comparator.comparingLong(ChunkPos::toLong),400);
        final ServerLevel level;
        final java.lang.reflect.Method add,remove;
        NativeAccess(ServerLevel level)throws Exception{
            this.level=level;Class<?> cache=level.getChunkSource().getClass();
            add=cache.getMethod("addRegionTicket",TicketType.class,ChunkPos.class,int.class,Object.class,boolean.class);
            remove=cache.getMethod("removeRegionTicket",TicketType.class,ChunkPos.class,int.class,Object.class,boolean.class);
        }
        public CompletableFuture<?> savedFull(ChunkPos p){
            // Native async disk read, no generation. The required support halo
            // is already saved FULL in336ba5 and stays inside region2/-3.
            return level.getChunkSource().chunkMap.read(p).thenApply(tag->{
                var n=tag.orElseThrow(()->new IllegalStateException("saved_chunk_missing:"+p));
                String status=n.getString("Status");
                if(n.getInt("xPos")!=p.x||n.getInt("zPos")!=p.z||!(status.equals("minecraft:full")||status.equals("full")))
                    throw new IllegalStateException("saved_chunk_not_full:"+p);
                return true;
            });
        }
        public void ticket(ChunkPos p,boolean adding)throws Exception{(adding?add:remove).invoke(level.getChunkSource(),TICKET,p,2,p,true);}
        public CompletableFuture<?> requestFull(ChunkPos p){return level.getChunkSource().getChunkFuture(p.x,p.z,ChunkStatus.FULL,false);}
        public boolean full(ChunkPos p){return level.getChunkSource().getChunkNow(p.x,p.z)!=null;}
        public boolean entities(ChunkPos p){return level.areEntitiesLoaded(p.toLong());}
    }
    final Access access;
    final LongSupplier clock;
    final Set<ChunkPos> tickets=new LinkedHashSet<>();
    final List<CompletableFuture<?>> pending=new ArrayList<>();
    long deadline;
    boolean active,ready;
    String phase="idle",outcome="",error="";
    RecoveryWindow(ServerLevel level)throws Exception{this(new NativeAccess(level),System::nanoTime);}
    RecoveryWindow(Access access,LongSupplier clock){this.access=access;this.clock=clock;}

    void start(boolean paused,boolean empty){
        if(!paused||!empty)throw new IllegalStateException("recovery_requires_paused_scheduler_and_empty_server");
        if(active||!tickets.isEmpty())throw new IllegalStateException("recovery_window_active_or_cleanup_pending");
        drain();if(!pending.isEmpty())throw new IllegalStateException("recovery_window_active_or_cleanup_pending");
        active=true;ready=false;error="";outcome="";phase="checking_saved_full";deadline=clock.getAsLong()+TTL_NANOS;
        try{for(int x=78;x<=83;x++)for(int z=-83;z<=-78;z++)pending.add(access.savedFull(new ChunkPos(x,z)));}
        catch(Exception e){fault("saved_full_request_failed:"+e.getClass().getSimpleName());}
    }
    void poll(boolean paused,boolean empty){
        if(!active){releaseTickets();drain();return;}
        if(!paused||!empty){finish("context_changed");return;}
        if(clock.getAsLong()>=deadline){finish("expired_20s");return;}
        if(pending.stream().anyMatch(f->f.isCompletedExceptionally()||f.isCancelled())){fault("native_future_failed_in:"+phase);return;}
        if(phase.equals("checking_saved_full")){
            if(pending.stream().anyMatch(f->!f.isDone()))return;
            pending.clear();phase="loading_entities";
            try{
                for(ChunkPos p:CENTERS){tickets.add(p);access.ticket(p,true);}
                for(ChunkPos p:CENTERS)pending.add(access.requestFull(p));
            }catch(Exception e){fault("native_ticket_or_request_failed:"+e.getClass().getSimpleName());return;}
        }
        try{ready=tickets.size()==4&&pending.stream().allMatch(CompletableFuture::isDone)&&CENTERS.stream().allMatch(p->access.full(p)&&access.entities(p));if(ready)phase="ready";}
        catch(Exception e){fault("native_readiness_failed:"+e.getClass().getSimpleName());}
    }
    void requireReady(boolean paused,boolean empty){
        poll(paused,empty);
        if(!active||!ready||clock.getAsLong()>=deadline)throw new IllegalStateException("recovery_window_not_ready_or_expired");
    }
    void fault(String reason){error=reason;finish("fault");}
    void finish(String reason){active=false;ready=false;phase="finished";outcome=reason;releaseTickets();drain();}
    private void releaseTickets(){
        for(ChunkPos p:new ArrayList<>(tickets))try{access.ticket(p,false);tickets.remove(p);}catch(Exception e){error="native_ticket_cleanup_failed:"+p+":"+e.getClass().getSimpleName();}
    }
    private void drain(){pending.removeIf(CompletableFuture::isDone);}
    JsonObject status(){
        JsonObject n=new JsonObject();n.addProperty("active",active);n.addProperty("ready",ready);n.addProperty("phase",phase);n.addProperty("outcome",outcome);n.addProperty("error",error);
        n.addProperty("remaining_ms",active?Math.max(0,(deadline-clock.getAsLong())/1_000_000):0);n.addProperty("temporary_tickets_remaining",tickets.size());
        n.addProperty("pending_native_futures",pending.stream().filter(f->!f.isDone()).count());n.addProperty("cleanup_required",!active&&(!tickets.isEmpty()||pending.stream().anyMatch(f->!f.isDone())));
        JsonArray rows=new JsonArray();for(ChunkPos p:CENTERS){JsonObject row=new JsonObject();row.addProperty("chunk_x",p.x);row.addProperty("chunk_z",p.z);row.addProperty("ticket_owned",tickets.contains(p));
            try{row.addProperty("full",access.full(p));row.addProperty("entity_storage_loaded",access.entities(p));}catch(Exception e){row.addProperty("read_error",e.getClass().getSimpleName());}rows.add(row);
        }n.add("chunks",rows);return n;
    }
}
