package worldfortwo.bridge;

import com.google.gson.*;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.AABB;
import net.neoforged.fml.ModList;
import java.nio.file.*;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.*;

/** SOURCE PROPOSAL: deliberately limited to static AIR-to-cube shells.
 * No tickets, generated/read-ahead chunks, BE tags, inventories or entities.
 * Does not turn rich offline construction plans into live plans automatically.
 */
final class LiveOrdinaryPolicy {
    static final class Conflict extends IllegalStateException { Conflict(String message){super(message);} }
    private final Path file;private final long size,modified;private final Instant expires;
    private final Set<Long> reserved;private int ticks;
    private SableAccess sable;
    private LiveOrdinaryPolicy(Path p,long n,long m,Instant end,Set<Long> chunks){file=p;size=n;modified=m;expires=end;reserved=Set.copyOf(chunks);}

    static LiveOrdinaryPolicy admit(MinecraftServer server,Path directory,String mode,JsonObject plan,List<BlockState> palette)throws Exception{
        if(!Set.of("place","verify","settle","map").contains(mode)||plan.getAsJsonArray("blocks").size()>256
            ||plan.getAsJsonArray("commands").size()!=0||plan.getAsJsonArray("block_entities").size()!=0||palette.size()>16)
            throw new IllegalStateException("Live lane permits <=256 static targets, <=16 states and NO commands or BE data");
        Path file=directory.resolve("human-construction-session.json");
        if(Files.isSymbolicLink(file)||!Files.isRegularFile(file,LinkOption.NOFOLLOW_LINKS)||Files.size(file)>131072)
            throw new IllegalStateException("Owned bounded immutable human reservation file required");
        byte[] raw=Files.readAllBytes(file);String sha=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(raw));
        if(!plan.has("live_policy_sha256")||!sha.equals(plan.get("live_policy_sha256").getAsString()))throw new IllegalStateException("Exact current live policy SHA required");
        JsonObject policy=JsonParser.parseString(new String(raw,java.nio.charset.StandardCharsets.UTF_8)).getAsJsonObject();
        if(!policy.get("format").getAsString().equals("awft-human-construction-session:1")
            ||!policy.get("active").getAsBoolean()||!policy.get("live_ordinary_placement_enabled").getAsBoolean()
            ||!policy.get("no_uncoordinated_restart").getAsBoolean()
            ||!Path.of(policy.get("authoritative_world").getAsString()).toAbsolutePath().normalize().equals(server.getWorldPath(LevelResource.ROOT).toAbsolutePath().normalize()))
            throw new IllegalStateException("Existing exact-world human session must explicitly enable only the narrow live lane");
        Path activeFile=directory.getParent().getParent().resolve("packwiz/active.json");
        if(Files.isSymbolicLink(activeFile)||!Files.isRegularFile(activeFile,LinkOption.NOFOLLOW_LINKS)||Files.size(activeFile)>65536)
            throw new IllegalStateException("Bounded actual active-candidate custody required");
        String actualCandidate=JsonParser.parseString(Files.readString(activeFile)).getAsJsonObject().get("version").getAsString();
        if(!actualCandidate.matches("0\\.1\\.0-candidate\\.[1-9][0-9]{0,3}")||!actualCandidate.equals(policy.get("runtime_candidate").getAsString()))
            throw new IllegalStateException("Human session candidate must match actual active pack");
        Instant end=Instant.parse(policy.get("live_ordinary_expires").getAsString());
        if(!end.isAfter(Instant.now())||end.isAfter(Instant.now().plusSeconds(43200)))throw new IllegalStateException("Finite current human session required");
        Set<Long> chunks=new TreeSet<>();JsonArray rows=policy.getAsJsonArray("human_regions");
        if(rows.isEmpty()||rows.size()>64)throw new IllegalStateException("Finite existing human regions required");
        for(JsonElement e:rows){JsonArray row=e.getAsJsonObject().getAsJsonArray("bounds_xyz");
            if(row.size()!=6)throw new IllegalStateException("Human region requires six XYZ bounds");
            for(JsonElement v:row)if(!v.getAsString().matches("-?\\d{1,8}"))throw new IllegalStateException("Integer human region bound required");
            int minX=row.get(0).getAsInt(),minY=row.get(1).getAsInt(),minZ=row.get(2).getAsInt();
            int maxX=row.get(3).getAsInt(),maxY=row.get(4).getAsInt(),maxZ=row.get(5).getAsInt();
            if(minX>maxX||minY>maxY||minZ>maxZ||maxX-minX>1024||maxZ-minZ>1024||minY< -64||maxY>320)
                throw new IllegalStateException("Finite ordered human region required");
            reserve(chunks,minX,maxX,minZ,maxZ);
            if(chunks.size()>8192)throw new IllegalStateException("Human reservation chunk bound exceeded");
        }
        // Every target is a unique finite address; duplicates cannot turn a later
        // AIR-only operation into a partial duplicate write.
        Set<BlockPos> unique=new HashSet<>();
        for(JsonElement element:plan.getAsJsonArray("blocks")){
            JsonArray row=element.getAsJsonArray();
            if(!unique.add(new BlockPos(row.get(0).getAsInt(),row.get(1).getAsInt(),row.get(2).getAsInt())))
                throw new IllegalStateException("Duplicate live target address");
        }
        // Minimum owner-reserved envelopes cannot be removed by session JSON.
        reserve(chunks,1024,1199,-1296,-720); // complete western cable route/frames/landing
        reserve(chunks,1296,1359,-1024,-912); // existing tubes, entrances and controls
        for(BlockState state:palette)if(!simple(state))throw new IllegalStateException("Live rich/modded/BE/mechanical palette remains offline");
        LiveOrdinaryPolicy admitted=new LiveOrdinaryPolicy(file,raw.length,Files.getLastModifiedTime(file).toMillis(),end,chunks);
        if(ModList.get().isLoaded("sable")){
            if(!ModList.get().getModContainerById("sable").orElseThrow().getModInfo().getVersion().toString().equals("2.0.6"))
                throw new IllegalStateException("Live virtual-body guard requires reviewed pinned Sable2.0.6 API");
            try{admitted.sable=new SableAccess();}
            catch(ReflectiveOperationException|LinkageError error){throw new IllegalStateException("Pinned virtual-body API unavailable; live admission refused",error);}
        }
        return admitted;
    }

    private static void reserve(Set<Long> chunks,int minX,int maxX,int minZ,int maxZ){
        for(int x=minX>>4;x<=maxX>>4;x++)for(int z=minZ>>4;z<=maxZ>>4;z++)chunks.add(ChunkPos.asLong(x,z));
    }

    /** Exact pinned native broad-phase API, read only: the iterable filters
     * every loaded SubLevel.boundingBox against the requested world-space box.
     * Resolve once per admission, not by loading or assembling a sublevel.
     */
    private static final class SableAccess {
        final java.lang.invoke.MethodHandle container,count,query,box;
        SableAccess()throws ReflectiveOperationException{
            ClassLoader loader=LiveOrdinaryPolicy.class.getClassLoader();
            Class<?> type=Class.forName("dev.ryanhcode.sable.api.sublevel.SubLevelContainer",false,loader);
            Class<?> serverType=Class.forName("dev.ryanhcode.sable.api.sublevel.ServerSubLevelContainer",false,loader);
            Class<?> bounds=Class.forName("dev.ryanhcode.sable.companion.math.BoundingBox3dc",false,loader);
            Class<?> mutable=Class.forName("dev.ryanhcode.sable.companion.math.BoundingBox3d",false,loader);
            // Exact descriptors: getMethod/getConstructor may enumerate
            // unrelated client overloads and trigger the dedicated distcleaner.
            // Pinned getContainer(ServerLevel) returns ServerSubLevelContainer,
            // not the base return type used by the Level overload.
            var lookup=java.lang.invoke.MethodHandles.lookup();
            container=lookup.findStatic(type,"getContainer",java.lang.invoke.MethodType.methodType(serverType,ServerLevel.class));
            count=lookup.findVirtual(type,"getLoadedCount",java.lang.invoke.MethodType.methodType(int.class));
            query=lookup.findVirtual(type,"queryIntersecting",java.lang.invoke.MethodType.methodType(Iterable.class,bounds));
            box=lookup.findConstructor(mutable,java.lang.invoke.MethodType.methodType(void.class,AABB.class));
        }
    }

    private void virtualBodies(ServerLevel level,AABB area){
        if(sable==null)return;
        try{
            Object container=sable.container.invoke(level);
            if(container==null)throw new Conflict("Actual Sable container unavailable");
            int count=((Number)sable.count.invoke(container)).intValue();
            if(count<0||count>128)throw new Conflict("Virtual-body query exceeds finite128-loaded-body live bound");
            Object result=sable.query.invoke(container,sable.box.invoke(area));
            if(!(result instanceof Iterable<?> hits))throw new Conflict("Actual Sable native query result differs");
            if(hits.iterator().hasNext())throw new Conflict("Preserve actual Sable virtual/kinematic body bounds");
        }catch(Conflict conflict){throw conflict;}
        catch(Throwable error){throw new Conflict("Actual pinned Sable query unavailable; live work paused: "+error);}
    }

    static boolean simple(BlockState state){
        return state.isAir()||state.getBlock().getClass()==Block.class
            &&BuiltInRegistries.BLOCK.getKey(state.getBlock()).getNamespace().equals("minecraft")
            &&!state.hasBlockEntity()&&state.getFluidState().isEmpty();
    }

    void current()throws Exception{
        if(++ticks>1800||Files.isSymbolicLink(file)||!Files.isRegularFile(file,LinkOption.NOFOLLOW_LINKS)||!expires.isAfter(Instant.now())||Files.size(file)!=size||Files.getLastModifiedTime(file).toMillis()!=modified)
            throw new Conflict("Human reservation/session changed or finite live window ended; explicit new admission required");
    }

    void target(ServerLevel level,BlockPos pos,BlockState expected,String mode){
        int cx=pos.getX()>>4,cz=pos.getZ()>>4;
        for(int dx=-1;dx<=1;dx++)for(int dz=-1;dz<=1;dz++){
            int x=cx+dx,z=cz+dz;long key=ChunkPos.asLong(x,z);BlockPos center=new BlockPos((x<<4)+8,64,(z<<4)+8);
            if(reserved.contains(key)||level.getChunkSource().getChunkNow(x,z)==null||!level.areEntitiesLoaded(key)||!level.isPositionEntityTicking(center))
                throw new Conflict("Human-reserved or not already FULL/entity-ready chunk; no load/generation/ticket attempt");
        }
        AABB area=new AABB(pos).inflate(2);
        for(var player:level.getServer().getPlayerList().getPlayers())if(player.serverLevel()==level
            &&(player.getBoundingBox().inflate(8).intersects(area)||Math.abs(player.chunkPosition().x-cx)<=1&&Math.abs(player.chunkPosition().z-cz)<=1))
            throw new Conflict("Actual same-tick human body/chunk protection");
        if(!level.getEntities((Entity)null,area,e->!e.isRemoved()).isEmpty())throw new Conflict("Preserve every actual entity/contraption AABB");
        virtualBodies(level,area);
        // This conservative closure rejects attached/modded/redstone/fluid,
        // gravity and BE neighbors. Normal settle cannot touch their hooks.
        for(BlockPos p:BlockPos.betweenClosed(pos.offset(-2,-2,-2),pos.offset(2,2,2))){
            BlockState state=level.getBlockState(p);
            if(level.getBlockEntity(p)!=null||!simple(state))throw new Conflict("Existing BE/inventory/dynamic-neighbor closure stays offline");
        }
        BlockState actual=level.getBlockState(pos);
        if(!simple(expected)||expected.hasBlockEntity())throw new Conflict("Only static new vanilla cubes in live lane");
        if(mode.equals("place")&&(!actual.isAir()||expected.isAir()))throw new Conflict("Live place is AIR-to-static-block only; never overwrite a human/current block");
        if(mode.equals("settle")&&actual.getBlock()!=expected.getBlock())throw new Conflict("Live settle cannot replace current structures");
    }
}
