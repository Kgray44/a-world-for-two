package worldfortwo.bridge;

import com.evandev.connectiblechains.CommonClass;
import com.evandev.connectiblechains.entity.ChainKnotEntity;
import com.evandev.connectiblechains.entity.Chainable;
import com.evandev.connectiblechains.tag.ModTagRegistry;
import com.google.gson.*;
import com.mojang.brigadier.arguments.StringArgumentType;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.TicketType;
import net.minecraft.server.level.ChunkLevel;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.Tag;
import net.minecraft.world.Container;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.properties.Property;
import net.minecraft.world.level.chunk.status.ChunkStatus;
import net.minecraft.world.level.chunk.status.ChunkPyramid;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.neoforged.fml.ModList;
import net.neoforged.fml.loading.FMLPaths;
import net.neoforged.neoforge.event.RegisterCommandsEvent;

import java.io.InputStream;
import java.lang.management.ManagementFactory;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.CompletableFuture;

/** ISOLATED PROPOSAL. Normal native knots/links and real construction stock only.
 * No fake player/item-use, UUID/NBT replay, movement, geometry writes or idle forcing.
 * Failure preserves partial entities, debits and durable intents; no automatic replay.
 */
public final class NativeChainRouteSupport {
    private enum Phase { IDLE,READ_PERSISTED,LOAD,VALIDATE,PREPARE,ADD,LINK,STABLE,CLEANUP,RECEIPT_BLOCKED }
    private static final class ResolutionPending extends IllegalStateException { ResolutionPending(String text){super(text);} }
    private static final Gson JSON=new Gson();
    private static final String ROUTE="rosewater-cliff-west-town-v2";
    private static final String CHAINS_FILE="connectiblechains-2.4.4+1.21.1-neoforge.jar";
    private static final String CHAINS_SHA="70d9f048e6f358c83b2d35f8a69000ec7827023efcc6d3b75346b4e34238bbd0";
    private static final int MAX_TICKS=600,MAX_CHUNKS=16,MAX_BYTES=2*1024*1024;
    private static final int READY_TICKS=1800,READY_WALL_SECONDS=90,READ_WALL_SECONDS=45;
    private static final int MAX_READY_COLUMNS=4096,MAX_HALO_RADIUS=16,READ_CONCURRENCY=4;
    private static final int MAX_NBT_HEAP_BYTES=4*1024*1024,MAX_TOTAL_NBT_HEAP_BYTES=256*1024*1024;
    private static final String READY_MODE="CURRENT_PERSISTED_FULL_BEFORE_ANY_TICKET";
    private static final double HANG=3.5,SLACK=16,MAX_SPAN=80;
    private static final int[][] NODES={{1160,168,-760},{1168,159,-784},{1144,152,-840},{1128,150,-848},
        {1120,147,-864},{1120,146,-880},{1112,142,-920},{1088,132,-968},{1064,125,-1008},
        {1048,116,-1064},{1056,108,-1112},{1048,100,-1176},{1048,91,-1232},{1064,86,-1248},{1100,72,-1256}};
    private static final BlockPos STOCK=new BlockPos(1101,65,-1257);
    private static final TicketType<ChunkPos> TICKET=TicketType.create("awft_chain_route",Comparator.comparingLong(ChunkPos::toLong));
    private final String candidate,bridge;
    private final ArtisticEngineeringSupport.Interlock interlock;
    private final Path home=FMLPaths.GAMEDIR.get().resolve("..").toAbsolutePath().normalize();
    private final Path journal=home.resolve("dashboard/settlement");
    private final List<ChainKnotEntity> knots=new ArrayList<>();
    private final List<UUID> ids=new ArrayList<>();
    private final Set<ChunkPos> chunks=new LinkedHashSet<>(),tickets=new LinkedHashSet<>();
    private final Set<ChunkPos> savedEndpointNeighborhood=new LinkedHashSet<>();
    private final Set<ChunkPos> persistedReadColumns=new LinkedHashSet<>();
    private final List<ChunkPos> persistedReadOrder=new ArrayList<>();
    private final Map<ChunkPos,CompletableFuture<Optional<CompoundTag>>> persistedReads=new LinkedHashMap<>();
    private final List<Map<String,Object>> persistedFacts=new ArrayList<>();
    private final List<CompletableFuture<?>> pending=new ArrayList<>();
    private final Map<BlockPos,BlockState> critical=new LinkedHashMap<>();
    private final Map<String,Object> report=new LinkedHashMap<>();
    private final List<Map<String,Object>> observations=new ArrayList<>();
    private ArtisticEngineeringSupport.Lease lease;
    private ServerLevel level;
    private Phase phase=Phase.IDLE;
    private JsonObject request,route,intent;
    private Path ledger;
    private String operation,requestSha,routeSha,outcome;
    private int ticks,cursor,stable,added,attached,debited;
    private int readCursor,readCompleted,haloRadius,readyTicks;
    private long beganNanos,readBeganNanos,totalNbtHeapBytes;
    private boolean persistedReady,readyFullQueued;
    private boolean cleanupPublished;

    public NativeChainRouteSupport(String candidate,String bridge,ArtisticEngineeringSupport.Interlock interlock){
        this.candidate=Objects.requireNonNull(candidate);this.bridge=Objects.requireNonNull(bridge);this.interlock=Objects.requireNonNull(interlock);
        if(candidate.isBlank()||bridge.isBlank())throw new IllegalArgumentException("Exact chain-route candidate/bridge required");
    }
    public boolean busy(){return phase!=Phase.IDLE;}
    public void commands(RegisterCommandsEvent event){
        var root=Commands.literal("awftchains").requires(s->s.getEntity()==null&&s.hasPermission(4));
        for(String op:List.of("create","prepare-create","inspect","verify-restart"))root.then(Commands.literal(op)
            .then(Commands.argument("bundle",StringArgumentType.word()).then(Commands.argument("sha256",StringArgumentType.word()).executes(c->{
                if(busy()){c.getSource().sendFailure(Component.literal("A chain-route transaction or its cleanup is already active"));return 0;}
                try{begin(c.getSource().getServer(),op,StringArgumentType.getString(c,"bundle"),StringArgumentType.getString(c,"sha256"));return 1;}
                catch(Exception|LinkageError error){report.put("error",error.toString());report.put("failures",1);finish("chain route admission refused; no automatic replay");return 0;}
            }))));
        root.then(Commands.literal("status").executes(c->{c.getSource().sendSuccess(()->Component.literal(JSON.toJson(report)),false);return 1;}));
        root.then(Commands.literal("cancel").executes(c->{if(busy()){
            if(phase==Phase.RECEIPT_BLOCKED){report.put("error","Immutable terminal publication failed; completed ledger is not creation acceptance");report.put("failures",1);outcome="receipt publication blocked; explicit cleanup only, no replay/adoption authority";}
            finish("cancelled; actual stock/entities and intents retained");}return 1;}));
        event.getDispatcher().register(root);
    }
    private static String hash(byte[] bytes)throws Exception{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));}
    private static byte[] bounded(Path path,int limit)throws Exception{
        if(!Files.isRegularFile(path,LinkOption.NOFOLLOW_LINKS)||Files.size(path)<1||Files.size(path)>limit)throw new IllegalStateException("Missing/linked/unbounded chain-route artifact");
        try(InputStream in=Files.newInputStream(path)){byte[] raw=in.readNBytes(limit+1);if(raw.length>limit)throw new IllegalStateException("Chain-route input grew");return raw;}
    }
    private Path owned(String relative)throws Exception{
        Path r=Path.of(relative);if(r.isAbsolute()||relative.indexOf(':')>=0||relative.indexOf('\\')>=0)throw new IllegalStateException("Owned home-relative path required");
        for(Path p:r)if(p.toString().equals("..")||p.toString().equals("."))throw new IllegalStateException("No chain-route traversal");
        Path result=home.resolve(r).normalize();
        for(Path p=result;p!=null&&!p.equals(home);p=p.getParent())if(Files.isSymbolicLink(p)||!p.toRealPath().equals(p.toAbsolutePath().normalize()))throw new IllegalStateException("No linked/redirected chain-route evidence");
        if(!result.toRealPath().startsWith(home.toRealPath()))throw new IllegalStateException("Chain-route input escaped owned home");return result;
    }
    private JsonObject read(JsonObject ref,int cap)throws Exception{
        if(!Set.of("path","bytes","sha256").equals(ref.keySet()))throw new IllegalStateException("Exact immutable reference fields required");
        byte[] raw=bounded(owned(ref.get("path").getAsString()),cap);
        if(raw.length!=ref.get("bytes").getAsInt()||!hash(raw).equals(ref.get("sha256").getAsString()))throw new IllegalStateException("Exact chain-route artifact bytes/hash differ");
        return JsonParser.parseString(new String(raw,StandardCharsets.UTF_8)).getAsJsonObject();
    }
    private void archive(String name,String expected)throws Exception{
        if(!name.matches("[A-Za-z0-9+._-]+\\.jar")||!expected.matches("[a-f0-9]{64}"))throw new IllegalStateException("Exact installed mod archive required");
        byte[] raw=bounded(owned("server/mods/"+name),16*1024*1024);
        JsonObject installed=JsonParser.parseString(new String(bounded(owned("server/installed.json"),MAX_BYTES),StandardCharsets.UTF_8)).getAsJsonObject();
        if(!hash(raw).equals(expected)||!installed.getAsJsonObject("files").has(name)||!installed.getAsJsonObject("files").get(name).getAsString().equals(expected))throw new IllegalStateException("Installed chain-route JAR differs");
    }
    private void classHash()throws Exception{
        try(InputStream in=NativeChainRouteSupport.class.getResourceAsStream("NativeChainRouteSupport.class")){
            if(in==null)throw new IllegalStateException("Actual chain helper missing");byte[] raw=in.readNBytes(256*1024+1);
            if(raw.length>256*1024||!hash(raw).equals(request.get("native_class_sha256").getAsString()))throw new IllegalStateException("Actual loaded chain helper differs");
        }
    }
    private void checkpoint()throws Exception{
        JsonObject current=JsonParser.parseString(new String(bounded(owned("dashboard/settlement/backup-receipt.json"),8192),StandardCharsets.UTF_8)).getAsJsonObject();
        if(!current.get("verified").getAsBoolean()||!current.get("id").getAsString().equals(request.get("checkpoint_id").getAsString())
            ||!current.get("sha256").getAsString().equals(request.get("checkpoint_sha256").getAsString()))throw new IllegalStateException("Current exact stopped checkpoint changed");
    }
    private boolean creating(){return operation.equals("create")||operation.equals("prepare-create");}
    private void readyPolicy(){
        JsonObject p=request.getAsJsonObject("ready_policy");
        if(!Set.of("mode","io_concurrency","max_nbt_heap_bytes","max_total_nbt_heap_bytes","max_read_columns","max_halo_radius","light_neighbor_halo","max_total_ticks","max_total_wall_seconds","max_read_wall_seconds").equals(p.keySet())
            ||!p.get("mode").getAsString().equals(READY_MODE)||p.get("io_concurrency").getAsInt()!=READ_CONCURRENCY
            ||p.get("max_nbt_heap_bytes").getAsInt()!=MAX_NBT_HEAP_BYTES||p.get("max_total_nbt_heap_bytes").getAsInt()!=MAX_TOTAL_NBT_HEAP_BYTES
            ||p.get("max_read_columns").getAsInt()!=MAX_READY_COLUMNS||p.get("max_halo_radius").getAsInt()!=MAX_HALO_RADIUS||p.get("light_neighbor_halo").getAsInt()!=1
            ||p.get("max_total_ticks").getAsInt()!=READY_TICKS||p.get("max_total_wall_seconds").getAsInt()!=READY_WALL_SECONDS||p.get("max_read_wall_seconds").getAsInt()!=READ_WALL_SECONDS)throw new IllegalStateException("Exact bounded persisted READY policy required");
    }
    private void configs()throws Exception{
        for(String name:List.of("chains_config","zipline_config")){
            JsonObject ref=request.getAsJsonObject(name);String path=name.equals("chains_config")?"server/config/connectiblechains.json":"server/config/zipline.json";
            if(!owned(ref.get("path").getAsString()).equals(home.resolve(path)))throw new IllegalStateException("Actual canonical config required");
            JsonObject cfg=read(ref,65536);
            if(name.equals("chains_config")){
                if(cfg.get("maxChainRange").getAsInt()!=96||!cfg.get("collisionsEnabled").getAsBoolean()||!cfg.get("hangingBlockCollisions").getAsBoolean())throw new IllegalStateException("Reviewed chain range/collision settings differ");
            }else if(Double.compare(cfg.get("hangOffset").getAsDouble(),HANG)!=0||Double.compare(cfg.get("speedMultiplier").getAsDouble(),1)!=0
                ||cfg.get("realisticPhysics").getAsBoolean()||Double.compare(cfg.get("maxTurnAngle").getAsDouble(),.707)!=0)throw new IllegalStateException("Reviewed native rider settings differ");
        }
        if(CommonClass.runtimeConfig==null||CommonClass.runtimeConfig.getMaxChainRange()!=96||!CommonClass.runtimeConfig.isCollisionsEnabled()||!CommonClass.runtimeConfig.isHangingBlockCollisionsEnabled())throw new IllegalStateException("Actual loaded Chains settings differ from reviewed files");
        var zip=com.evandev.zipline.config.ModConfig.get();
        if(Double.compare(zip.hangOffset,HANG)!=0||Double.compare(zip.speedMultiplier,1)!=0||zip.realisticPhysics||Double.compare(zip.maxTurnAngle,.707)!=0)throw new IllegalStateException("Actual loaded rider settings differ");
    }
    private static void disk()throws Exception{
        long reserve=32_212_254_720L;
        if(Files.getFileStore(Path.of("C:\\")).getUsableSpace()<reserve+2*1024*1024L||Files.getFileStore(Path.of("D:\\")).getUsableSpace()<reserve+2*1024*1024L)throw new IllegalStateException("Finite chain-route journal would exceed either drive reserve");
    }
    private void releasePack()throws Exception{
        if(!candidate.matches("[A-Za-z0-9][A-Za-z0-9_.-]{0,79}")||candidate.endsWith("."))throw new IllegalStateException("Unsafe active release candidate");
        JsonObject active=JsonParser.parseString(new String(bounded(owned("packwiz/active.json"),65536),StandardCharsets.UTF_8)).getAsJsonObject();
        JsonObject installed=JsonParser.parseString(new String(bounded(owned("server/installed.json"),2*1024*1024),StandardCharsets.UTF_8)).getAsJsonObject();
        String expected=request.get("pack_sha256").getAsString();
        if(!expected.matches("[a-f0-9]{64}")||!active.get("version").getAsString().equals(candidate)||!installed.get("pack_version").getAsString().equals(candidate)
            ||!active.get("pack_sha256").getAsString().equals(expected)||!installed.get("pack_sha256").getAsString().equals(expected)
            ||!hash(bounded(owned("packwiz/releases/"+candidate+"/pack.toml"),65536)).equals(expected))throw new IllegalStateException("Actual active installed versioned release pack differs");
    }
    private void begin(MinecraftServer server,String op,String bundle,String expected)throws Exception{
        if(busy()||lease!=null||!tickets.isEmpty()||!pending.isEmpty())throw new IllegalStateException("A chain-route transaction or cleanup already owns its lease");
        report.clear();observations.clear();knots.clear();ids.clear();chunks.clear();savedEndpointNeighborhood.clear();persistedReadColumns.clear();persistedReadOrder.clear();persistedReads.clear();persistedFacts.clear();critical.clear();outcome=null;cleanupPublished=false;
        readCursor=readCompleted=haloRadius=readyTicks=0;totalNbtHeapBytes=0;persistedReady=readyFullQueued=false;beganNanos=System.nanoTime();
        ticks=cursor=stable=added=attached=debited=0;operation=op;requestSha=expected;report.put("started",Instant.now().toString());report.put("operation",op);report.put("request_sha256",expected);
        report.put("failures",0);
        if(!server.isSameThread()||!bundle.matches("chains-[a-f0-9]{16}")||!expected.matches("[a-f0-9]{64}")||!bundle.endsWith(expected.substring(0,16)))throw new IllegalStateException("Exact typed main-thread chain request required");
        Path actualHome=home.toRealPath(),stages=Path.of("D:\\A World for Two\\staging\\world-tests").toRealPath();
        if(!actualHome.equals(home)||!actualHome.getParent().equals(stages)||!server.getWorldPath(LevelResource.ROOT).toRealPath().equals(home.resolve("world/RosewaterArtistic").toRealPath())
            ||server.getPort()!=25575||!server.getServerVersion().equals("1.21.1")||!server.getPlayerList().getPlayers().isEmpty())throw new IllegalStateException("Only the exact empty private artistic world is admitted");
        byte[] raw=bounded(owned("dashboard/settlement/"+bundle+"/request.json"),128*1024);
        if(!hash(raw).equals(expected))throw new IllegalStateException("Exact chain-route request hash differs");request=JsonParser.parseString(new String(raw,StandardCharsets.UTF_8)).getAsJsonObject();
        if(!request.get("format").getAsString().equals(op.equals("prepare-create")?"awft-native-chain-route:2":"awft-native-chain-route:1")||!request.get("allowed_operation").getAsString().equals(op)
            ||!request.get("candidate_version").getAsString().equals(candidate)||!request.get("bridge_version").getAsString().equals(bridge)
            ||!ModList.get().getModContainerById("awft_control_bridge").orElseThrow().getModInfo().getVersion().toString().equals(bridge)
            ||!ModList.get().getModContainerById("connectiblechains").orElseThrow().getModInfo().getVersion().toString().equals("2.4.4+1.21.1")
            ||!ModList.get().getModContainerById("zipline").orElseThrow().getModInfo().getVersion().toString().equals("1.5.3+1.21.1"))throw new IllegalStateException("Exact candidate/bridge/native API versions differ");
        classHash();checkpoint();
        JsonObject owner=JsonParser.parseString(new String(bounded(owned("dashboard/artistic-owner.json"),65536),StandardCharsets.UTF_8)).getAsJsonObject();
        JsonObject active=JsonParser.parseString(new String(bounded(owned("packwiz/active.json"),65536),StandardCharsets.UTF_8)).getAsJsonObject();
        JsonObject installed=JsonParser.parseString(new String(bounded(owned("server/installed.json"),MAX_BYTES),StandardCharsets.UTF_8)).getAsJsonObject();
        if(!owner.get("format").getAsString().equals("awft-artistic-stage:1")||!Path.of(owner.get("home").getAsString()).toRealPath().equals(home)
            ||!active.get("version").getAsString().equals(candidate)||!installed.get("pack_version").getAsString().equals(candidate)
            ||!active.get("pack_sha256").getAsString().equals(request.get("pack_sha256").getAsString())
            ||!installed.get("pack_sha256").getAsString().equals(request.get("pack_sha256").getAsString()))throw new IllegalStateException("Owned active/installed pack custody differs");releasePack();
        archive(CHAINS_FILE,CHAINS_SHA);archive("zipline-1.5.3+1.21.1-neoforge.jar",request.get("zipline_jar_sha256").getAsString());
        archive("awft-control-bridge-"+bridge+".jar",request.get("bridge_jar_sha256").getAsString());configs();
        route=read(request.getAsJsonObject("route"),MAX_BYTES);routeSha=request.getAsJsonObject("route").get("sha256").getAsString();level=server.overworld();
        if(!route.get("format").getAsString().equals("awft-owned-native-chain-route:1")||!route.get("route_id").getAsString().equals(ROUTE)
            ||!route.get("seed").getAsString().equals(Long.toString(level.getSeed()))
            ||!route.get("dimension").getAsString().equals("minecraft:overworld")||!Path.of(route.get("world_path").getAsString()).toRealPath().equals(server.getWorldPath(LevelResource.ROOT).toRealPath())
            // Route checkpoint is the genuine construction BEFORE baseline.
            // Current FULL/census can be from a later stopped save after the
            // already-owned stations/barrel were placed. Paired evidence below
            // proves exact coverage and native chronology; it is never rebound.
            ||route.get("copied_entity_NBT").getAsBoolean()||route.get("idle_forced_chunks").getAsInt()!=0||route.get("native_ride_acceptance").getAsBoolean()
            ||Double.compare(route.get("slack").getAsDouble(),SLACK)!=0||Double.compare(route.get("hang_offset_required").getAsDouble(),HANG)!=0)throw new IllegalStateException("Exact reviewed original route/config/world required; no fabricated acceptance");
        JsonArray nodes=route.getAsJsonArray("nodes"),edges=route.getAsJsonArray("links");
        if(nodes.size()!=NODES.length||edges.size()!=NODES.length-1)throw new IllegalStateException("Only the reviewed fifteen-knot fourteen-link route is admitted");
        for(int i=0;i<NODES.length;i++){
            JsonObject row=nodes.get(i).getAsJsonObject();JsonArray pos=row.getAsJsonArray("block");
            if(!Set.of("block","face","anchor_state").equals(row.keySet())||pos.size()!=3||!row.get("face").getAsString().equals("north"))throw new IllegalStateException("No entity fields or alternate faces are admitted");
            for(int k=0;k<3;k++)if(pos.get(k).getAsInt()!=NODES[i][k])throw new IllegalStateException("Exact native curve node differs");
            BlockPos p=point(i);critical.put(p,parse(row.get("anchor_state").getAsString()));chunks.add(new ChunkPos(p));
            if(i>0){JsonArray edge=edges.get(i-1).getAsJsonArray();if(edge.size()!=2||edge.get(0).getAsInt()!=i-1||edge.get(1).getAsInt()!=i)throw new IllegalStateException("Only directed consecutive shared-knot links admitted");
                Vec3 a=anchor(i-1),b=anchor(i);if(a.distanceTo(b)>MAX_SPAN||a.distanceTo(b)<.01)throw new IllegalStateException("Engine cap80m exceeded");}
            if(i>1){Vec3 a=anchor(i-1).subtract(anchor(i-2)).normalize(),b=anchor(i).subtract(anchor(i-1)).normalize();if(a.dot(b)<=.7071067811865476)throw new IllegalStateException("Actual chord turn must remain strictly below45 degrees");}
        }
        if(!route.getAsJsonArray("stock").equals(JsonParser.parseString("[1101,65,-1257]"))||route.get("stock_slot").getAsInt()!=0||route.get("chain_cost").getAsInt()!=14)throw new IllegalStateException("New reviewed explicit fourteen-chain stock required");
        critical.put(STOCK,parse(route.get("stock_state").getAsString()));chunks.add(new ChunkPos(STOCK));if(chunks.size()>MAX_CHUNKS)throw new IllegalStateException("Bounded actual endpoint chunk set exceeded");
        if(!critical.get(STOCK).is(Blocks.BARREL))throw new IllegalStateException("Actual native BARREL identity required, not an arbitrary27-slot container");
        geometryEvidence();bodyEvidence();savedEndpointEvidence();
        ledger=server.getWorldPath(LevelResource.ROOT).toRealPath().resolve("data/awft-chains/"+ROUTE);
        for(Path p=ledger;p!=null&&!p.equals(server.getWorldPath(LevelResource.ROOT).toRealPath());p=p.getParent())if(Files.exists(p,LinkOption.NOFOLLOW_LINKS)&&(Files.isSymbolicLink(p)||!p.toRealPath().equals(p)))throw new IllegalStateException("No linked chain-route ledger");
        if(creating()){disk();if(Files.exists(ledger,LinkOption.NOFOLLOW_LINKS))throw new IllegalStateException("Existing or partial route intent refuses create/replay");}
        else loadIntent(op);
        census(op);
        // The data-only preflight acquires the SAME exclusive lease without
        // requesting simulation. No ticket, chunk promotion or wake occurs yet.
        lease=interlock.acquire("native-chain-route-"+op,!op.equals("inspect")&&!op.equals("prepare-create"));if(lease==null||!lease.valid())throw new IllegalStateException("Shared maintenance lease refused");
        if(op.equals("inspect")){if(!ready())throw new IllegalStateException("UNKNOWN: endpoint chunks/entities are not already loaded; passive inspection will not load them");phase=Phase.VALIDATE;}
        else if(op.equals("prepare-create")){
            readyPolicy();derivePersistedReadColumns();readBeganNanos=System.nanoTime();phase=Phase.READ_PERSISTED;
            report.put("persisted_ready_mode",READY_MODE);report.put("tickets_before_persisted_validation",tickets.size());report.put("simulation_wakes_before_persisted_validation",0);
        }
        else{
            // Region level31 can retain a5x5 FULL neighborhood per endpoint. Refuse
            // if any such column is not ALREADY FULL now: no generation authority.
            for(ChunkPos c:savedEndpointNeighborhood)if(level.getChunkSource().getChunkNow(c.x,c.z)==null)throw new IllegalStateException("UNKNOWN: reviewed saved endpoint neighborhood is not already FULL; no generation/loading relaxation");
            report.put("already_FULL_endpoint_neighborhood_columns",savedEndpointNeighborhood.size());phase=Phase.LOAD;
            for(ChunkPos c:chunks){tickets.add(c);ticket(c,true);pending.add(((worldfortwo.bridge.mixin.ChunkCacheAccess)(Object)level.getChunkSource()).awftQueueChunk(c.x,c.z,ChunkStatus.FULL,false));}
        }
        report.put("route_sha256",routeSha);report.put("endpoint_chunks",chunks.size());report.put("native_ride_acceptance",false);report.put("engine_span_cap",80);report.put("restart_loading_preference",48);
    }
    private void bodyEvidence()throws Exception{
        JsonObject proof=read(request.getAsJsonObject("physical_frame_source"),MAX_BYTES);
        if(!proof.get("all_saved_AIR_clear").getAsBoolean()||!proof.get("physical_frames_clear").getAsBoolean()
            ||!proof.get("checkpoint_sha256").getAsString().equals(route.get("checkpoint_sha256").getAsString())
            ||Double.compare(proof.get("hang_offset").getAsDouble(),HANG)!=0||Double.compare(proof.get("slack").getAsDouble(),SLACK)!=0
            ||proof.get("native_ride_acceptance").getAsBoolean())throw new IllegalStateException("Complete reviewed3.5 saved terrain/frame envelope required; source is not a ride");
        JsonArray n=proof.getAsJsonArray("nodes");if(n.size()!=NODES.length)throw new IllegalStateException("Body source route size differs");
        for(int i=0;i<NODES.length;i++)for(int k=0;k<3;k++)if(n.get(i).getAsJsonArray().get(k).getAsInt()!=NODES[i][k])throw new IllegalStateException("Body source exact route differs");
    }
    private void census(String op)throws Exception{
        JsonObject census=read(request.getAsJsonObject("chain_census"),MAX_BYTES);
        if(!census.get("format").getAsString().equals("awft-stopped-chain-knot-census:1")||!census.get("all_entity_regions_scanned").getAsBoolean()
            ||!census.get("checkpoint_sha256").getAsString().equals(request.get("checkpoint_sha256").getAsString())
            ||!census.get("world_path").getAsString().equals(route.get("world_path").getAsString()))throw new IllegalStateException("Actual complete stopped-backup chain-knot census required");
        JsonArray rows=census.getAsJsonArray("knots");if(rows.size()>4096)throw new IllegalStateException("Finite saved chain census exceeded");
        Set<UUID> unique=new HashSet<>(),ownedSeen=new HashSet<>();
        for(JsonElement element:rows){JsonObject row=element.getAsJsonObject();UUID uuid=UUID.fromString(row.get("uuid").getAsString());JsonArray pos=row.getAsJsonArray("block");
            if(!unique.add(uuid)||pos.size()!=3)throw new IllegalStateException("Saved duplicate/invalid chain-knot UUID refuses custody");
            BlockPos p=new BlockPos(pos.get(0).getAsInt(),pos.get(1).getAsInt(),pos.get(2).getAsInt());boolean near=false;
            for(int i=0;i<NODES.length;i++)if(p.distSqr(point(i))<=97*97)near=true;
            int index=ids.indexOf(uuid);
            if(index>=0){if(!p.equals(point(index)))throw new IllegalStateException("Saved owned UUID moved; no blind rebind");ownedSeen.add(uuid);}
            else if(near)throw new IllegalStateException("Foreign/unresolved saved chain knot is near the proposed route; preserve it and refuse");
        }
        if(!creating()&&ownedSeen.size()!=NODES.length)throw new IllegalStateException("Stopped backup omits an actual owned knot; never replace it");
    }
    private void geometryEvidence()throws Exception{
        JsonArray sets=request.getAsJsonArray("geometry_sets");if(sets.isEmpty()||sets.size()>18)throw new IllegalStateException("Finite reviewed full/before geometry sets required");
        Map<BlockPos,BlockState> verified=new HashMap<>();int count=0;boolean stockOriginallyAir=false;
        for(JsonElement element:sets){JsonObject set=element.getAsJsonObject();
            if(!Set.of("before","native_before","full","native_full").equals(set.keySet()))throw new IllegalStateException("Exact before/full native references required");
            Map<BlockPos,BlockState> original=new LinkedHashMap<>(),complete=new LinkedHashMap<>();
            JsonObject beforeReceipt=null,fullReceipt=null;
            for(String stage:List.of("before","full")){
                JsonObject ref=set.getAsJsonObject(stage),plan=read(ref,MAX_BYTES),proof=read(set.getAsJsonObject("native_"+stage),MAX_BYTES);
                if(!plan.get("format").getAsString().equals("awft-native-settlement:1")||!plan.getAsJsonArray("commands").isEmpty()
                    ||!plan.get("seed").getAsString().equals(route.get("seed").getAsString())||!plan.get("world_path").getAsString().equals(route.get("world_path").getAsString())
                    ||!plan.get("backup_sha256").getAsString().equals(stage.equals("before")?route.get("checkpoint_sha256").getAsString():request.get("checkpoint_sha256").getAsString()))throw new IllegalStateException("Verified geometry plan world/contents/checkpoint differs");
                verifyReceipt(set.getAsJsonObject("native_"+stage),proof,ref.get("sha256").getAsString(),plan.getAsJsonArray("blocks").size(),stage.equals("full"));
                Map<BlockPos,BlockState> target=stage.equals("before")?original:complete;JsonArray palette=plan.getAsJsonArray("palette");
                for(JsonElement e:plan.getAsJsonArray("blocks")){JsonArray row=e.getAsJsonArray();if(++count>65536||row.size()!=4)throw new IllegalStateException("Finite paired native geometry exceeded");
                    BlockPos pos=new BlockPos(row.get(0).getAsInt(),row.get(1).getAsInt(),row.get(2).getAsInt());BlockState state=parse(palette.get(row.get(3).getAsInt()).getAsString());
                    if(target.putIfAbsent(pos,state)!=null)throw new IllegalStateException("Duplicate addressed geometry cell");
                    if(stage.equals("full")){BlockState old=verified.putIfAbsent(pos,state);if(old!=null&&!old.equals(state))throw new IllegalStateException("Conflicting verified geometry cell");}
                }
                if(stage.equals("before")){
                    beforeReceipt=proof;
                    for(JsonElement tag:plan.getAsJsonArray("block_entities")){JsonArray p=tag.getAsJsonObject().getAsJsonArray("pos");if(p.get(0).getAsInt()==STOCK.getX()&&p.get(1).getAsInt()==STOCK.getY()&&p.get(2).getAsInt()==STOCK.getZ())throw new IllegalStateException("Original AIR stock witness cannot carry an old-container tag");}
                }else fullReceipt=proof;
            }
            if(!original.keySet().equals(complete.keySet()))throw new IllegalStateException("Actual BEFORE and FULL must cover the same exact target field");
            if(Instant.parse(beforeReceipt.get("finished").getAsString()).isAfter(Instant.parse(fullReceipt.get("started").getAsString())))throw new IllegalStateException("Actual FULL verification predates completion of its paired original BEFORE");
            if(complete.containsKey(STOCK)){
                if(!original.get(STOCK).is(Blocks.AIR)||!complete.get(STOCK).is(Blocks.BARREL))throw new IllegalStateException("New construction barrel requires genuine original native AIR then actual BARREL at STOCK");
                stockOriginallyAir=true;
            }
        }
        if(!stockOriginallyAir)throw new IllegalStateException("Full geometry cannot invent ownership of an existing container; original AIR stock coverage missing");
        for(var row:critical.entrySet())if(!row.getValue().equals(verified.get(row.getKey())))throw new IllegalStateException("Actual full geometry proofs must cover every exact anchor and owned stock block");
    }
    private void verifyReceipt(JsonObject ref,JsonObject proof,String plan,int count,boolean fresh)throws Exception{
        Path path=owned(ref.get("path").getAsString());
        if(!new String(bounded(path.resolveSibling(path.getFileName()+".complete"),128),StandardCharsets.UTF_8).trim().equals(ref.get("sha256").getAsString())
            ||!proof.get("operation").getAsString().equals("verify")||proof.get("failures").getAsInt()!=0||proof.has("error")
            ||!proof.get("plan_sha256").getAsString().equals(plan)||proof.get("blocks").getAsInt()!=count
            ||!proof.get("status").getAsString().equals("verified actual block identities, orientation, block entities and supplied inventories")
            ||proof.get("cleanup_required").getAsBoolean()||proof.get("temporary_tickets_remaining").getAsInt()!=0
            ||proof.get("pending_shared_chunk_futures").getAsInt()!=0||proof.has("ticket_cleanup_error"))throw new IllegalStateException("Actual completed strict native geometry proof required");
        Instant start=Instant.parse(proof.get("started").getAsString()),done=Instant.parse(proof.get("finished").getAsString());if(start.isAfter(done)||done.isAfter(Instant.now())||(fresh&&creating()&&done.isBefore(Instant.now().minusSeconds(1800))))throw new IllegalStateException("Actual completed geometry verification is stale/future/unordered");
    }
    private void savedEndpointEvidence()throws Exception{
        for(ChunkPos c:chunks)for(int dx=-2;dx<=2;dx++)for(int dz=-2;dz<=2;dz++)savedEndpointNeighborhood.add(new ChunkPos(c.x+dx,c.z+dz));
        if(savedEndpointNeighborhood.size()>400)throw new IllegalStateException("Finite5x5 endpoint envelope exceeded");
        JsonObject proof=read(request.getAsJsonObject("saved_endpoint_chunks"),MAX_BYTES);
        if(!proof.get("format").getAsString().equals("awft-stopped-zipline-endpoint-chunks:1")||!proof.get("all_required_saved_FULL").getAsBoolean()
            ||!proof.get("checkpoint_sha256").equals(request.get("checkpoint_sha256"))||!proof.get("world_path").equals(route.get("world_path"))
            ||!proof.get("seed").equals(route.get("seed")))throw new IllegalStateException("Complete actual stopped saved FULL endpoint-neighborhood source proof required");
        JsonArray rows=proof.getAsJsonArray("chunks");if(rows.size()!=savedEndpointNeighborhood.size()||proof.get("required_count").getAsInt()!=savedEndpointNeighborhood.size()||!proof.getAsJsonArray("unknown").isEmpty())throw new IllegalStateException("Exact all5x5 saved chunk coverage required;3x3 geometry evidence is insufficient");
        Set<ChunkPos> observed=new LinkedHashSet<>();String prefix=home.relativize(Path.of(route.get("world_path").getAsString()).toAbsolutePath().normalize()).toString().replace('\\','/')+"/region/";
        for(JsonElement e:rows){JsonObject r=e.getAsJsonObject();JsonArray a=r.getAsJsonArray("chunk");if(a.size()!=2)throw new IllegalStateException("Exact saved chunk coordinate required");ChunkPos c=new ChunkPos(a.get(0).getAsInt(),a.get(1).getAsInt());
            if(!savedEndpointNeighborhood.contains(c)||!observed.add(c)||!Set.of("full","minecraft:full").contains(r.get("status").getAsString())
                ||!r.get("source_member").getAsString().equals(prefix+"r."+Math.floorDiv(c.x,32)+"."+Math.floorDiv(c.z,32)+".mca")
                ||!r.get("region_sha256").getAsString().matches("[a-f0-9]{64}")||!r.get("chunk_nbt_sha256").getAsString().matches("[a-f0-9]{64}"))throw new IllegalStateException("Unproved/duplicate/unknown saved endpoint FULL chunk");
        }
        if(!observed.equals(savedEndpointNeighborhood))throw new IllegalStateException("Missing saved endpoint neighborhood");
        report.put("saved_FULL_endpoint_neighborhood_columns",observed.size());report.put("saved_endpoint_chunks_sha256",request.getAsJsonObject("saved_endpoint_chunks").get("sha256").getAsString());
    }
    /** Synthetic NBT fixtures can call only this nested validator, without a
     * Level/fake player, outer controller construction or native world action. */
    static final class ReadyNbtFacts {
        static Map<String,Object> validate(ChunkPos p,CompoundTag tag){
            if(tag==null||!tag.contains("DataVersion",Tag.TAG_INT)||tag.getInt("DataVersion")!=3955
                ||!tag.contains("xPos",Tag.TAG_INT)||!tag.contains("zPos",Tag.TAG_INT)||tag.getInt("xPos")!=p.x||tag.getInt("zPos")!=p.z
                ||!tag.contains("Status",Tag.TAG_STRING)||!Set.of("full","minecraft:full").contains(tag.getString("Status"))
                ||!tag.contains("sections",Tag.TAG_LIST)||tag.getList("sections",Tag.TAG_COMPOUND).isEmpty()
                ||tag.getList("sections",Tag.TAG_COMPOUND).size()>64||tag.contains("below_zero_retrogen")
                ||!tag.getBoolean("isLightOn"))throw new IllegalStateException("UNKNOWN/non-FULL/retrogen/lighting/version/coordinate persisted chunk at "+p);
            int size=tag.sizeInBytes();if(size<1||size>MAX_NBT_HEAP_BYTES)throw new IllegalStateException("Persisted NBT exceeds reviewed4MiB heap-size bound at "+p);
            return Map.of("chunk",List.of(p.x,p.z),"data_version",3955,"status",tag.getString("Status"),"light_correct",true,"nbt_heap_bytes",size);
        }
    }
    private void derivePersistedReadColumns(){
        // A region ticket of distance2 uses FULL-level minus2. Its complete
        // tracked footprint can exceed the five-by-five FULL neighborhood.
        // Prove that entire footprint plus a light-neighbor ring from CURRENT
        // storage before adding even the first ticket. Loading-pyramid radius
        // is also included; actual pinned metadata is read, not guessed.
        int fullLevel=ChunkLevel.byStatus(ChunkStatus.FULL),ticketLevel=fullLevel-2;
        int ticketReach=ChunkLevel.MAX_LEVEL-ticketLevel;
        int loadRadius=ChunkPyramid.LOADING_PYRAMID.getStepTo(ChunkStatus.FULL).accumulatedDependencies().getRadius();
        if(ticketReach<2||loadRadius<0)throw new IllegalStateException("Unsupported actual ticket/loading dependency metadata");
        haloRadius=Math.max(ticketReach+1,2+loadRadius+1);
        if(haloRadius>MAX_HALO_RADIUS)throw new IllegalStateException("Actual required ticket/light halo exceeds reviewed finite radius");
        TreeSet<Long> sorted=new TreeSet<>();
        for(ChunkPos c:chunks)for(int dx=-haloRadius;dx<=haloRadius;dx++)for(int dz=-haloRadius;dz<=haloRadius;dz++){
            sorted.add(ChunkPos.asLong(c.x+dx,c.z+dz));if(sorted.size()>MAX_READY_COLUMNS)throw new IllegalStateException("Actual required persisted halo exceeds4096 columns");
        }
        for(long packed:sorted){ChunkPos c=new ChunkPos(packed);persistedReadColumns.add(c);persistedReadOrder.add(c);}
        if(!persistedReadColumns.containsAll(savedEndpointNeighborhood))throw new IllegalStateException("Persisted READY omitted the required5x5 set");
        report.put("ready_halo",Map.of("full_level",fullLevel,"ticket_level",ticketLevel,"native_max_level",ChunkLevel.MAX_LEVEL,"ticket_reach",ticketReach,"loading_full_dependency_radius",loadRadius,"extra_light_neighbor_ring",1,"derived_radius",haloRadius,"required_read_columns",persistedReadColumns.size()));
    }
    private void persistedStep(MinecraftServer server)throws Exception{
        checkpoint();configs();
        if(!tickets.isEmpty()||persistedReady)throw new IllegalStateException("No ticket/second READY pass is admitted during current storage validation");
        if(System.nanoTime()-readBeganNanos>READ_WALL_SECONDS*1_000_000_000L)throw new IllegalStateException("Bounded current persisted read deadline expired");
        for(var it=persistedReads.entrySet().iterator();it.hasNext();){
            var entry=it.next();CompletableFuture<Optional<CompoundTag>> f=entry.getValue();if(!f.isDone())continue;
            // Remove completed result handles before validation, so rejected
            // large tags are not retained in the controller's future maps.
            it.remove();pending.remove(f);
            Optional<CompoundTag> value=f.join();if(value.isEmpty())throw new IllegalStateException("UNKNOWN: current persisted chunk is absent at "+entry.getKey());
            Map<String,Object> fact=ReadyNbtFacts.validate(entry.getKey(),value.get());
            totalNbtHeapBytes=Math.addExact(totalNbtHeapBytes,((Number)fact.get("nbt_heap_bytes")).longValue());
            if(totalNbtHeapBytes>MAX_TOTAL_NBT_HEAP_BYTES)throw new IllegalStateException("Bounded total persisted NBT scan budget exceeded");
            persistedFacts.add(fact);readCompleted++;
        }
        while(persistedReads.size()<READ_CONCURRENCY&&readCursor<persistedReadOrder.size()){
            ChunkPos c=persistedReadOrder.get(readCursor++);
            // Public inherited ChunkStorage.read delegates to IOWorker.loadAsync.
            // It performs a persisted data read, not a live getChunk request.
            CompletableFuture<Optional<CompoundTag>> f=level.getChunkSource().chunkMap.read(c);
            if(persistedReads.put(c,f)!=null)throw new IllegalStateException("Duplicate current persisted read");pending.add(f);
        }
        report.put("persisted_read_completed",readCompleted);report.put("persisted_reads_pending",persistedReads.size());report.put("persisted_nbt_heap_bytes_processed",totalNbtHeapBytes);
        if(readCompleted!=persistedReadOrder.size()||!persistedReads.isEmpty())return;
        if(!pending.isEmpty()||!lease.valid()||!server.getPlayerList().getPlayers().isEmpty())throw new IllegalStateException("Persisted READY ownership changed before promotion");
        // SAME lease, no release/reacquire gap. Recheck the original artifacts
        // and ledger before the first native ticket. Unknown terrain never
        // reaches this phase; create=false alone is not a no-generation proof.
        checkpoint();configs();geometryEvidence();bodyEvidence();census(operation);
        if(Files.exists(ledger,LinkOption.NOFOLLOW_LINKS))throw new IllegalStateException("Route intent appeared during READY; no replay/adoption");
        persistedReady=true;report.put("current_persisted_FULL_before_tickets",List.copyOf(persistedFacts));
        report.put("persisted_ready_completed",Instant.now().toString());report.put("tickets_at_persisted_ready_completion",tickets.size());
        phase=Phase.LOAD;
        for(ChunkPos c:chunks){tickets.add(c);ticket(c,true);}
        // LOAD waits for actual suitable native holders before queuing once.
        // No fixed sleep or repeated load request substitutes for readiness.
    }
    private static BlockState parse(String text){
        int split=text.indexOf('[');String name=split<0?text:text.substring(0,split);ResourceLocation id=ResourceLocation.parse(name);
        if(!BuiltInRegistries.BLOCK.containsKey(id))throw new IllegalStateException("Unregistered native anchor/stock state");BlockState state=BuiltInRegistries.BLOCK.get(id).defaultBlockState();
        if(split>=0){if(!text.endsWith("]"))throw new IllegalStateException("Malformed state");Set<String> seen=new HashSet<>();
            for(String part:text.substring(split+1,text.length()-1).split(",")){String[] kv=part.split("=",-1);Property<?> p=state.getBlock().getStateDefinition().getProperty(kv[0]);
                if(kv.length!=2||p==null||!seen.add(kv[0]))throw new IllegalStateException("Unknown/duplicate native state property");state=property(state,p,kv[1]);}}
        return state;
    }
    private static <T extends Comparable<T>> BlockState property(BlockState s,Property<T> p,String v){return s.setValue(p,p.getValue(v).orElseThrow());}
    private static BlockPos point(int i){int[] p=NODES[i];return new BlockPos(p[0],p[1],p[2]);}
    private static Vec3 anchor(int i){int[] p=NODES[i];return new Vec3(p[0]+.5,p[1]+.5,p[2]+.25);}
    private void ticket(ChunkPos c,boolean add)throws Exception{level.getChunkSource().getClass().getMethod(add?"addRegionTicket":"removeRegionTicket",TicketType.class,ChunkPos.class,int.class,Object.class,boolean.class).invoke(level.getChunkSource(),TICKET,c,2,c,true);}
    private boolean ready(){for(ChunkPos c:savedEndpointNeighborhood)if(level.getChunkSource().getChunkNow(c.x,c.z)==null)return false;for(ChunkPos c:chunks)if(level.getChunkSource().getChunkNow(c.x,c.z)==null||!level.areEntitiesLoaded(c.toLong()))return false;return true;}
    private void gate(MinecraftServer server)throws Exception{
        if(!server.isSameThread()||!server.getPlayerList().getPlayers().isEmpty()||lease==null||!lease.valid()||!ready())throw new IllegalStateException("Chain route thread/lease/empty-server/readiness changed");
        checkpoint();configs();for(var row:critical.entrySet())if(!level.getBlockState(row.getKey()).equals(row.getValue()))throw new IllegalStateException("Actual critical anchor/stock state changed");
        if(!Items.CHAIN.getDefaultInstance().is(ModTagRegistry.CATENARY_ITEMS))throw new IllegalStateException("Actual chain item lost its native catenary tag");
        for(int i=0;i<NODES.length;i++)if(!level.getBlockState(point(i)).is(ModTagRegistry.CHAIN_CONNECTIBLE))throw new IllegalStateException("Actual anchor lost its native chain-connectible tag");
    }
    private Container stock(int expected){
        if(!level.getBlockState(STOCK).is(Blocks.BARREL)||!(level.getBlockEntity(STOCK) instanceof Container inventory)||inventory.getContainerSize()!=27)throw new IllegalStateException("Actual native BARREL at the genuinely new owned stock position required");
        for(int i=0;i<inventory.getContainerSize();i++){ItemStack s=inventory.getItem(i);
            if(i==0&&expected>0){if(s.getCount()!=expected||!ItemStack.isSameItemSameComponents(s,Items.CHAIN.getDefaultInstance()))throw new IllegalStateException("Exact native chain stock count/components changed");}
            else if(!s.isEmpty())throw new IllegalStateException("No foreign or extra stock is admitted");}
        return inventory;
    }
    private List<ChainKnotEntity> at(int i){
        BlockPos p=point(i);List<ChainKnotEntity> result=level.getEntitiesOfClass(ChainKnotEntity.class,new AABB(p).inflate(1),e->!e.isRemoved()&&e.blockPosition().equals(p));
        if(result.size()>1)throw new IllegalStateException("Duplicate knots at a reviewed anchor");return result;
    }
    private void allAbsent(){for(int i=0;i<NODES.length;i++)if(!at(i).isEmpty())throw new IllegalStateException("Foreign/existing knot refuses creation; no blind adoption");}
    private void identity(int i,ChainKnotEntity knot){
        if(knot.isRemoved()||knot.level()!=level||!knot.getUUID().equals(ids.get(i))||level.getEntity(ids.get(i))!=knot
            ||!knot.blockPosition().equals(point(i))||knot.attachedFace!=Direction.NORTH||knot.getSourceItem()!=Items.CHAIN||knot.position().distanceToSqr(anchor(i))>1e-10
            ||at(i).size()!=1||at(i).getFirst()!=knot)throw new IllegalStateException("Actual native knot UUID/position/face/source or uniqueness differs");
    }
    private void graph(){
        stock(0);
        for(int i=0;i<NODES.length;i++){
            ChainKnotEntity knot=knots.get(i);identity(i,knot);int expected=i<NODES.length-1?1:0;
            if(knot.getChainDataSet().size()!=expected)throw new IllegalStateException("Unexpected/unresolved/foreign outgoing chain count");
            if(expected==1){ChainKnotEntity next=knots.get(i+1);Chainable.ChainData link=knot.getChainDataSet().iterator().next();
                if(!link.isAlive()||link.sourceItem!=Items.CHAIN||Float.compare(link.getSlack(),(float)SLACK)!=0
                    ||!link.buntings.isEmpty()||!link.banners.isEmpty()||!link.hangings.isEmpty())throw new IllegalStateException("Actual directed native link identity/decorations differ");
                BlockPos relative=point(i+1).subtract(point(i));
                if(knot.getChainHolder(link)==null&&link.unresolvedChainData!=null&&link.unresolvedChainData.right().filter(relative::equals).isPresent())throw new ResolutionPending("Normal saved relative holder resolution is pending at owned node "+i);
                if(knot.getChainHolder(link)!=next||link.unresolvedChainData!=null)throw new IllegalStateException("Actual directed native holder is missing or different");
            }
        }
        // Incoming foreign chains need a local scan too; only endpoint chunks are admitted.
        int scanned=0;
        for(int i=0;i<NODES.length;i++)for(ChainKnotEntity owner:level.getEntitiesOfClass(ChainKnotEntity.class,new AABB(point(i)).inflate(96),e->!e.isRemoved())){
            if(++scanned>2048)throw new IllegalStateException("Bounded loaded incoming-link inspection exceeded");
            if(knots.contains(owner))continue;
            for(Chainable.ChainData link:owner.getChainDataSet()){
                if(knots.contains(owner.getChainHolder(link)))throw new IllegalStateException("Foreign incoming link touches owned route");
                if(link.unresolvedChainData!=null){
                    if(link.unresolvedChainData.left().filter(ids::contains).isPresent())throw new IllegalStateException("Unresolved foreign UUID link may touch owned route");
                    Optional<BlockPos> relative=link.unresolvedChainData.right();
                    if(relative.isPresent()){BlockPos target=owner.blockPosition().offset(relative.get());for(int k=0;k<NODES.length;k++)if(target.equals(point(k)))throw new IllegalStateException("Unresolved foreign relative link may touch owned route");}
                }
            }
        }
    }
    private static void durable(Path path,JsonObject value)throws Exception{
        byte[] bytes=(JSON.toJson(value)+"\n").getBytes(StandardCharsets.UTF_8);if(bytes.length>32768)throw new IllegalStateException("Finite chain intent exceeded");
        try(FileChannel out=FileChannel.open(path,StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE)){ByteBuffer b=ByteBuffer.wrap(bytes);while(b.hasRemaining())out.write(b);out.force(true);}
    }
    private JsonObject fact(String kind,int i){JsonObject row=new JsonObject();row.addProperty("kind",kind);row.addProperty("index",i);row.addProperty("route_sha256",routeSha);row.addProperty("request_sha256",requestSha);row.addProperty("at",Instant.now().toString());return row;}
    private void prepareIntent(MinecraftServer server)throws Exception{
        allAbsent();stock(14);ids.clear();knots.clear();JsonArray members=new JsonArray();
        for(int i=0;i<NODES.length;i++){
            ChainKnotEntity knot=new ChainKnotEntity(level,point(i),Items.CHAIN,Direction.NORTH);
            if(knot.getUUID()==null||ids.contains(knot.getUUID())||server.getPlayerList().getPlayer(knot.getUUID())!=null||level.getEntity(knot.getUUID())!=null
                ||!knot.blockPosition().equals(point(i))||knot.position().distanceToSqr(anchor(i))>1e-10||knot.attachedFace!=Direction.NORTH)throw new IllegalStateException("Genuine unregistered native knot identity differs");
            ids.add(knot.getUUID());knots.add(knot);JsonObject row=new JsonObject();row.addProperty("uuid",knot.getUUID().toString());row.add("block",JSON.toJsonTree(NODES[i]));row.addProperty("face","north");row.addProperty("source_item","minecraft:chain");members.add(row);
        }
        intent=fact("native-generated-route-uuid-intent",0);intent.addProperty("route_id",ROUTE);intent.addProperty("checkpoint_sha256",request.get("checkpoint_sha256").getAsString());
        intent.addProperty("candidate_version",candidate);intent.addProperty("bridge_version",bridge);intent.addProperty("pack_sha256",request.get("pack_sha256").getAsString());
        intent.addProperty("world_path",server.getWorldPath(LevelResource.ROOT).toRealPath().toString());intent.addProperty("jvm_start_millis",ManagementFactory.getRuntimeMXBean().getStartTime());intent.addProperty("pid",ProcessHandle.current().pid());
        intent.addProperty("chains_config_sha256",request.getAsJsonObject("chains_config").get("sha256").getAsString());intent.addProperty("zipline_config_sha256",request.getAsJsonObject("zipline_config").get("sha256").getAsString());
        intent.addProperty("stock_before",14);intent.addProperty("cost_per_link",1);intent.addProperty("knot_item_cost",0);intent.add("members",members);
        // All fifteen genuine UUIDs become durable BEFORE the first entity addition.
        disk();Files.createDirectories(ledger.getParent());Files.createDirectory(ledger);durable(ledger.resolve("route.intent.json"),intent);
    }
    private void loadIntent(String op)throws Exception{
        if(!Files.isDirectory(ledger,LinkOption.NOFOLLOW_LINKS)||Files.isSymbolicLink(ledger))throw new IllegalStateException("No completed owned route ledger; never recreate/adopt uncertain knots");
        intent=JsonParser.parseString(new String(bounded(ledger.resolve("route.intent.json"),32768),StandardCharsets.UTF_8)).getAsJsonObject();
        JsonObject complete=JsonParser.parseString(new String(bounded(ledger.resolve("route.complete.json"),32768),StandardCharsets.UTF_8)).getAsJsonObject();
        if(!intent.get("route_id").getAsString().equals(ROUTE)||!intent.get("route_sha256").getAsString().equals(routeSha)
            ||!intent.get("candidate_version").getAsString().equals(candidate)||!intent.get("pack_sha256").getAsString().equals(request.get("pack_sha256").getAsString())
            ||!complete.get("route_sha256").getAsString().equals(routeSha)||!complete.get("creation_request_sha256").getAsString().equals(intent.get("request_sha256").getAsString())
            ||complete.get("native_added").getAsInt()!=15||complete.get("native_attached").getAsInt()!=14||complete.get("chain_debits").getAsInt()!=14
            ||!intent.get("chains_config_sha256").getAsString().equals(request.getAsJsonObject("chains_config").get("sha256").getAsString())
            ||!intent.get("zipline_config_sha256").getAsString().equals(request.getAsJsonObject("zipline_config").get("sha256").getAsString()))throw new IllegalStateException("Completed exact original route custody/config differs");
        if(op.equals("verify-restart")&&intent.get("jvm_start_millis").getAsLong()==ManagementFactory.getRuntimeMXBean().getStartTime())throw new IllegalStateException("A real restarted JVM is required; same-session inspection is not restart proof");
        JsonObject receiptRef=request.getAsJsonObject("creation_receipt"),receipt=read(receiptRef,MAX_BYTES);Path receiptPath=owned(receiptRef.get("path").getAsString());
        if(!new String(bounded(receiptPath.resolveSibling(receiptPath.getFileName()+".complete"),128),StandardCharsets.UTF_8).trim().equals(receiptRef.get("sha256").getAsString())
            ||!Set.of("create","prepare-create").contains(receipt.get("operation").getAsString())||!receipt.get("request_sha256").getAsString().equals(intent.get("request_sha256").getAsString())
            ||!receipt.get("route_sha256").getAsString().equals(routeSha)||receipt.has("error")||receipt.get("failures").getAsInt()!=0
            ||!receipt.get("cleanup_passed").getAsBoolean()||receipt.get("cleanup_required").getAsBoolean()||receipt.get("temporary_tickets_remaining").getAsInt()!=0
            ||receipt.get("pending_shared_chunk_futures").getAsInt()!=0||receipt.get("native_added").getAsInt()!=15||receipt.get("native_attached").getAsInt()!=14||receipt.get("chain_debits").getAsInt()!=14)throw new IllegalStateException("Actual completed creation/cleanup receipt is required, not a partial ledger");
        JsonArray members=intent.getAsJsonArray("members");if(members.size()!=NODES.length)throw new IllegalStateException("Exact generated UUID member ledger differs");
        for(int i=0;i<NODES.length;i++){JsonObject row=members.get(i).getAsJsonObject();UUID id=UUID.fromString(row.get("uuid").getAsString());if(ids.contains(id))throw new IllegalStateException("Duplicate ledger UUID");
            JsonArray p=row.getAsJsonArray("block");for(int k=0;k<3;k++)if(p.get(k).getAsInt()!=NODES[i][k])throw new IllegalStateException("Recorded native anchor differs");ids.add(id);}
    }
    public void tick(MinecraftServer server){
        if(phase==Phase.IDLE||phase==Phase.RECEIPT_BLOCKED)return;if(phase==Phase.CLEANUP){cleanup(true);return;}
        try{
            if(++ticks>(operation.equals("prepare-create")?READY_TICKS:MAX_TICKS)||lease==null||!lease.valid()||!server.isSameThread()||!server.getPlayerList().getPlayers().isEmpty()
                ||(operation.equals("prepare-create")&&System.nanoTime()-beganNanos>READY_WALL_SECONDS*1_000_000_000L))throw new IllegalStateException("Bounded chain-route lease/thread/player/deadline guard refused");
            if(phase==Phase.READ_PERSISTED){persistedStep(server);return;}
            if(operation.equals("prepare-create")&&!persistedReady)throw new IllegalStateException("Current stored FULL proof must precede every ticket/wake/entity action");
            // Only these explicit create/restart leases wake already-saved endpoint chunks.
            if(!operation.equals("inspect"))level.resetEmptyTime();
            if(phase==Phase.LOAD){
                if(operation.equals("prepare-create")&&!readyFullQueued){
                    // Pinned hasChunk checks actual visible holder and its
                    // ticket level, not merely a fixed elapsed delay.
                    for(ChunkPos c:savedEndpointNeighborhood)if(!level.getChunkSource().hasChunk(c.x,c.z))return;
                    for(ChunkPos c:savedEndpointNeighborhood)pending.add(((worldfortwo.bridge.mixin.ChunkCacheAccess)(Object)level.getChunkSource()).awftQueueChunk(c.x,c.z,ChunkStatus.FULL,false));
                    readyFullQueued=true;report.put("proved_saved_FULL_load_promises",savedEndpointNeighborhood.size());return;
                }
                if(pending.stream().anyMatch(f->!f.isDone()))return;for(var f:pending)f.join();pending.clear();if(!ready())return;
                if(operation.equals("prepare-create")){checkpoint();configs();geometryEvidence();bodyEvidence();census(operation);allAbsent();stock(14);report.put("actual_FULL_ready_after_persisted_validation",savedEndpointNeighborhood.size());}
                phase=Phase.VALIDATE;
            }
            gate(server);
            if(phase==Phase.VALIDATE){
                if(creating()){allAbsent();stock(14);phase=Phase.PREPARE;}
                else{knots.clear();for(int i=0;i<NODES.length;i++){Entity e=level.getEntity(ids.get(i));if(!(e instanceof ChainKnotEntity k))throw new IllegalStateException("UNKNOWN/missing native owned UUID; never replace it");knots.add(k);identity(i,k);}phase=Phase.STABLE;}
                return;
            }
            if(phase==Phase.PREPARE){prepareIntent(server);cursor=0;phase=Phase.ADD;return;}
            if(phase==Phase.ADD){
                stock(14);for(int i=0;i<NODES.length;i++){if(i<cursor)identity(i,knots.get(i));else if(!at(i).isEmpty())throw new IllegalStateException("Anchor changed after durable intent; no duplicate creation");}
                ChainKnotEntity knot=knots.get(cursor);durable(ledger.resolve(String.format("node-%02d.add-intent.json",cursor)),fact("normal-addFreshEntity",cursor));
                if(!level.addFreshEntity(knot))throw new IllegalStateException("Normal native addFreshEntity refused; intent retained");added++;identity(cursor,knot);
                JsonObject actual=fact("native-entity-registered",cursor);actual.addProperty("uuid",knot.getUUID().toString());durable(ledger.resolve(String.format("node-%02d.added.json",cursor)),actual);
                if(++cursor==NODES.length){cursor=0;phase=Phase.LINK;}return;
            }
            if(phase==Phase.LINK){
                for(int i=0;i<NODES.length;i++)identity(i,knots.get(i));ChainKnotEntity a=knots.get(cursor),b=knots.get(cursor+1);
                Container inventory=stock(14-cursor);if(!a.getChainDataSet().isEmpty()||b.getChainData(a)!=null||!a.canAttachTo(b))throw new IllegalStateException("Normal native attachment rejects changed/duplicate endpoint");
                JsonObject edge=fact("one-real-chain-debit-before-normal-link",cursor);edge.addProperty("owner_uuid",a.getUUID().toString());edge.addProperty("holder_uuid",b.getUUID().toString());edge.addProperty("stock_before",14-cursor);edge.addProperty("stock_after",13-cursor);
                durable(ledger.resolve(String.format("edge-%02d.intent.json",cursor)),edge);
                ItemStack removed=inventory.removeItem(0,1);inventory.setChanged();if(removed.getCount()!=1||!ItemStack.isSameItemSameComponents(removed,Items.CHAIN.getDefaultInstance()))throw new IllegalStateException("Actual one-chain debit differs; preserve uncertainty");debited++;
                durable(ledger.resolve(String.format("edge-%02d.debited.json",cursor)),edge);
                Chainable.ChainData link=new Chainable.ChainData(b,Items.CHAIN);link.customSlack=(float)SLACK;
                // Null means no PREVIOUS HOLDER Entity. This is not item-use with a null Player.
                a.attachChain(link,null,true);attached++;
                if(a.getChainData(b)!=link||a.getChainHolder(link)!=b||!link.isAlive())throw new IllegalStateException("Actual normal link readback differs; no detach/refund/retry");stock(13-cursor);
                durable(ledger.resolve(String.format("edge-%02d.attached.json",cursor)),edge);
                if(++cursor==NODES.length-1){phase=Phase.STABLE;stable=0;}return;
            }
            if(phase==Phase.STABLE){
                try{graph();stable++;}catch(ResolutionPending e){if(operation.equals("verify-restart")&&ticks<MAX_TICKS-40){stable=0;report.put("normal_resolution_pending",e.toString());return;}throw e;}
                if(stable<40)return;
                if(creating()){JsonObject complete=fact("normal-native-route-complete",0);complete.addProperty("creation_request_sha256",requestSha);complete.addProperty("native_added",added);complete.addProperty("native_attached",attached);complete.addProperty("chain_debits",debited);complete.addProperty("native_ride_acceptance",false);durable(ledger.resolve("route.complete.json"),complete);}
                for(int i=0;i<NODES.length;i++)observations.add(Map.of("index",i,"uuid",knots.get(i).getUUID().toString(),"block",List.of(NODES[i][0],NODES[i][1],NODES[i][2]),"face","north","resolved_outgoing_links",i<NODES.length-1?1:0));
                finish(creating()?"actual native UUIDs/links and fourteen-chain stock debit stable; riding/streaming/art remain pending":operation.equals("verify-restart")?"same native UUIDs and links resolved after actual JVM restart; riding/streaming remain pending":"same native UUIDs/links inspected without chunk loading or world writes");
            }
        }catch(Exception|LinkageError error){report.put("error",error.toString());report.put("failures",1);finish("chain route failed; actual partial entities, stock debits and intents retained");}
        report.put("phase",phase.name());report.put("ticks",ticks);
    }
    private void finish(String status){if(outcome==null)outcome=status;phase=Phase.CLEANUP;cleanup(true);}
    private void cleanup(boolean retry){
        List<String> errors=new ArrayList<>();if(retry&&level!=null)for(ChunkPos c:List.copyOf(tickets))try{ticket(c,false);tickets.remove(c);}catch(Exception|LinkageError e){errors.add(c+": "+e);}
        pending.removeIf(CompletableFuture::isDone);persistedReads.entrySet().removeIf(e->e.getValue().isDone());
        if(tickets.isEmpty()&&pending.isEmpty()&&persistedReads.isEmpty()&&lease!=null)try{lease.close();lease=null;}catch(Exception e){errors.add(e.toString());}
        boolean clean=tickets.isEmpty()&&pending.isEmpty()&&persistedReads.isEmpty()&&lease==null;
        report.put("status",outcome);report.put("finished",Instant.now().toString());report.put("cleanup_passed",clean);report.put("cleanup_required",!clean);report.put("temporary_tickets_remaining",tickets.size());report.put("pending_shared_chunk_futures",pending.size());report.put("cleanup_errors",errors);
        report.put("native_added",added);report.put("native_attached",attached);report.put("chain_debits",debited);report.put("stock_cost_per_link",1);report.put("knot_item_cost",0);report.put("observations",List.copyOf(observations));
        report.put("native_ride_acceptance",false);report.put("automatic_entity_cleanup_or_refund",false);report.put("idle_forced_chunks",0);report.put("helper_world_mutations",added+attached+debited);
        report.put("current_persisted_reads_pending",persistedReads.size());report.put("current_persisted_reads_completed",readCompleted);report.put("current_persisted_halo_columns",persistedReadColumns.size());report.put("ready_tickets_added_only_after_all_CURRENT_FULL",persistedReady);report.put("ready_policy_no_generation_fallback",true);
        // The immutable result is authoritative. A mutable status-view failure
        // must never suppress it or silently discard a completed route receipt.
        boolean published=true;
        if(clean||!cleanupPublished)try{NativeJournal.terminal(journal,"chain-route",new LinkedHashMap<>(report));cleanupPublished=true;}
        catch(Exception e){published=false;report.put("receipt_publication_error",e.toString());System.err.println("AWFT chain-route IMMUTABLE receipt blocked: "+e);}
        try{NativeJournal.progress(journal,"chain-route-status.json",report);}catch(Exception e){System.err.println("AWFT chain-route progress view: "+e);}
        if(clean){if(published){phase=Phase.IDLE;knots.clear();level=null;}else phase=Phase.RECEIPT_BLOCKED;}
    }
    public void stopped(){if(busy())finish("server stopping; actual route/intents/stock and uncertainty retained");}
}
