package worldfortwo.bridge;

import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.Tag;
import net.minecraft.server.level.ChunkLevel;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.chunk.status.ChunkPyramid;
import net.minecraft.world.level.chunk.status.ChunkStatus;
import java.util.*;
import java.util.concurrent.CompletableFuture;

/** Finite CURRENT persisted FULL proof before ANY patch ticket or wake.
 * Owned implementation uses the already-reviewed native ChunkStorage.read API;
 * create=false on a later load is never substituted for this proof.
 */
public final class NativeTreePatchReadiness {
    // Cumulative decoded work is not resident tag memory: each completed tag
    // is validated and discarded. The unchanged four pending reads admit at
    // most four validated 4MiB tags in their window (16MiB), not 1GiB retained.
    private static final long MAX_PROCESSED_NBT_BYTES=1024L*1024*1024;
    private final ServerLevel level;
    private final List<ChunkPos> order;
    private final Map<ChunkPos,CompletableFuture<Optional<CompoundTag>>> pending=new LinkedHashMap<>();
    private final List<Map<String,Object>> facts=new ArrayList<>();
    private final Map<String,Object> halo;
    private final long started=System.nanoTime();
    private int cursor,completed;
    private long nbtBytes;
    private boolean ready;

    public NativeTreePatchReadiness(ServerLevel level,Collection<ChunkPos> centers){
        if(!level.getServer().isSameThread()||centers.isEmpty()||centers.size()>1024)throw new IllegalStateException("Finite native patch ticket centers required");
        this.level=level;
        int full=ChunkLevel.byStatus(ChunkStatus.FULL),ticket=full-2,reach=ChunkLevel.MAX_LEVEL-ticket;
        int dependencies=ChunkPyramid.LOADING_PYRAMID.getStepTo(ChunkStatus.FULL).accumulatedDependencies().getRadius();
        int radius=Math.max(reach+1,2+dependencies+1);
        if(reach<2||dependencies<0||radius>32)throw new IllegalStateException("Unsupported pinned native ticket/dependency metadata");
        Set<Long> columns=new TreeSet<>();
        for(ChunkPos center:centers)for(int dx=-radius;dx<=radius;dx++)for(int dz=-radius;dz<=radius;dz++){
            columns.add(ChunkPos.asLong(center.x+dx,center.z+dz));
            if(columns.size()>4096)throw new IllegalStateException("Native patch current-storage footprint exceeds4096 columns");
        }
        order=columns.stream().map(ChunkPos::new).toList();
        halo=Map.of("full_level",full,"ticket_level",ticket,"native_max_level",ChunkLevel.MAX_LEVEL,"ticket_reach",reach,
            "loading_full_dependency_radius",dependencies,"extra_light_ring",1,"radius",radius,"columns",order.size());
    }

    static Map<String,Object> validate(ChunkPos p,CompoundTag tag){
        if(tag==null||!tag.contains("DataVersion",Tag.TAG_INT)||tag.getInt("DataVersion")!=3955
            ||!tag.contains("xPos",Tag.TAG_INT)||!tag.contains("zPos",Tag.TAG_INT)||tag.getInt("xPos")!=p.x||tag.getInt("zPos")!=p.z
            ||!tag.contains("Status",Tag.TAG_STRING)||!Set.of("full","minecraft:full").contains(tag.getString("Status"))
            ||!tag.contains("sections",Tag.TAG_LIST)||tag.getList("sections",Tag.TAG_COMPOUND).isEmpty()
            ||tag.getList("sections",Tag.TAG_COMPOUND).size()>64||tag.contains("below_zero_retrogen")||!tag.getBoolean("isLightOn"))
            throw new IllegalStateException("UNKNOWN/non-FULL/retrogen/light/version/coordinate persisted chunk: "+p);
        int bytes=tag.sizeInBytes();if(bytes<1||bytes>4*1024*1024)throw new IllegalStateException("Persisted chunk exceeds4MiB bounded NBT heap size");
        return Map.of("chunk",List.of(p.x,p.z),"data_version",3955,"status",tag.getString("Status"),"light_correct",true,"nbt_heap_bytes",bytes);
    }

    public boolean poll(){
        if(!level.getServer().isSameThread()||ready)throw new IllegalStateException("One current-storage proof on the server thread only");
        if(System.nanoTime()-started>120_000_000_000L)throw new IllegalStateException("Current persisted patch read exceeded120seconds");
        for(var it=pending.entrySet().iterator();it.hasNext();){
            var row=it.next();if(!row.getValue().isDone())continue;it.remove();
            Optional<CompoundTag> value=row.getValue().join();if(value.isEmpty())throw new IllegalStateException("UNKNOWN: current persisted patch halo column absent: "+row.getKey());
            Map<String,Object> fact=validate(row.getKey(),value.get());nbtBytes+=((Number)fact.get("nbt_heap_bytes")).longValue();
            if(nbtBytes>MAX_PROCESSED_NBT_BYTES)throw new IllegalStateException("Current persisted patch scan exceeds1GiB cumulative processed-NBT bound; pending tag window remains16MiB");
            facts.add(fact);completed++;
        }
        while(pending.size()<4&&cursor<order.size()){
            ChunkPos p=order.get(cursor++);
            // This is inherited public ChunkStorage.read/IOWorker.loadAsync,
            // never getChunk, a ticket, a native generator or a world setter.
            pending.put(p,level.getChunkSource().chunkMap.read(p));
        }
        ready=completed==order.size()&&pending.isEmpty();return ready;
    }
    public boolean ready(){return ready;}
    /** Cancellation cannot abandon unfinished IO; caller keeps its same lease. */
    static <K,V> boolean drainCompleted(Map<K,CompletableFuture<V>> reads){reads.entrySet().removeIf(row->row.getValue().isDone());return reads.isEmpty();}
    public boolean drained(){return drainCompleted(pending);}
    public int pending(){return pending.size();}
    public Map<String,Object> report(){return Map.of("halo",halo,"completed",completed,"pending",pending.size(),
        "nbt_heap_bytes_processed",nbtBytes,"cumulative_processed_nbt_limit_bytes",MAX_PROCESSED_NBT_BYTES,
        "pending_validated_tag_window_limit_bytes",16L*1024*1024,
        "current_persisted_FULL_before_any_ticket",ready,"facts",List.copyOf(facts));}
}
