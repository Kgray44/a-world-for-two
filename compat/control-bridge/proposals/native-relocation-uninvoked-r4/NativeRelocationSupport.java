package worldfortwo.bridge;

import com.google.gson.*;
import com.mojang.brigadier.arguments.StringArgumentType;
import java.io.*;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.CompletableFuture;
import net.minecraft.server.level.TicketType;
import net.minecraft.world.level.block.entity.LecternBlockEntity;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.component.TypedDataComponent;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.*;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.RegistryOps;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.commands.CloneCommands;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.Container;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.RandomizableContainerBlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.Property;
import net.minecraft.world.level.chunk.status.ChunkStatus;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.AABB;
import net.neoforged.fml.ModList;
import net.neoforged.fml.loading.FMLPaths;
import net.neoforged.neoforge.event.RegisterCommandsEvent;

/** ONE real vanilla clone-move only. No NBT loader, setBlock, summoning, fake
 * player, generation request, ticket, inventory writer, retry or rollback API.
 * All operations run synchronously on the actual empty server thread. */
public final class NativeRelocationSupport {
    private static final Gson JSON=new Gson();
    private BlockPos LOW,HIGH,DEST;
    private int dx,dy,dz,sourceCount,objectCount,supportCount;
    private String capsuleId;
    private String intentName="intent.json";
    private JsonObject catalogRow,catalog;
    private static final String CATALOG_SHA="db5e0fa730575ad9b0fd166dd4d52273a5105832d66636d1ca3098693199adf7";
    private static final TicketType<ChunkPos> TICKET=TicketType.create("awft_relocation",Comparator.comparingLong(ChunkPos::toLong));
    private final Set<ChunkPos> chunks=new LinkedHashSet<>(),tickets=new LinkedHashSet<>(),centers=new LinkedHashSet<>();
    private final List<CompletableFuture<?>> pending=new ArrayList<>();
    private NativeTreePatchReadiness persisted;
    private String phase;
    private int loadingTicks;
    private long syncStarted;
    private static final String BASELINE="b0315f548e55a389bb01a3caeb4c5a8532abb3e6599f6a0a77785c6c4916dece";
    private static final String EASTERN_LAYOUT="6f24640d9efefae3340be80d34bcd0e4788f2ded695aefe03d1d6815761a12a4";
    private static final Set<String> CLASSES=Set.of(
        "earth.terrarium.handcrafted.common.blockentities.ContainerBlockEntity",
        "net.mehvahdjukaar.supplementaries.common.block.tiles.GlobeBlockTile",
        "net.mehvahdjukaar.supplementaries.common.block.tiles.ItemShelfBlockTile",
        "net.minecraft.world.level.block.entity.SmokerBlockEntity","net.minecraft.world.level.block.entity.SignBlockEntity",
        "net.minecraft.world.level.block.entity.BarrelBlockEntity","net.minecraft.world.level.block.entity.ChiseledBookShelfBlockEntity",
        "net.minecraft.world.level.block.entity.LecternBlockEntity","net.minecraft.world.level.block.entity.BedBlockEntity",
        "net.mehvahdjukaar.supplementaries.common.block.tiles.BookPileBlockTile");
    private final String candidate,bridge;
    private final ArtisticEngineeringSupport.Interlock interlock;
    private ArtisticEngineeringSupport.Lease lease;
    private final Path home=FMLPaths.GAMEDIR.get().resolve("..").toAbsolutePath().normalize(),journal=home.resolve("dashboard/settlement");
    private final Map<String,Object> report=new LinkedHashMap<>();
    private final Map<BlockPos,BlockState> source=new LinkedHashMap<>(),destination=new LinkedHashMap<>(),supports=new LinkedHashMap<>();
    private final Map<BlockPos,CompoundTag> expectedTags=new LinkedHashMap<>();
    private final Map<BlockPos,JsonObject> classPins=new LinkedHashMap<>();
    private JsonObject request;private String requestSha,action;private ServerLevel level;private Path ledger;
    private boolean running,admitted,terminalPending,intentAttempted,intentWritten,cloneInvoked,quarantined;private long started;
    private int cleanupAttempts,cleanupDelay;private String finalStatus;private boolean finalFailure;
    private final String runtimeId=UUID.randomUUID().toString();

    public NativeRelocationSupport(String candidate,String bridge,ArtisticEngineeringSupport.Interlock interlock){
        this.candidate=Objects.requireNonNull(candidate);this.bridge=Objects.requireNonNull(bridge);this.interlock=Objects.requireNonNull(interlock);
    }
    public boolean busy(){return running&&admitted||lease!=null||terminalPending;}
    public void commands(RegisterCommandsEvent event){
        var root=Commands.literal("awftrelocate").requires(s->s.getEntity()==null&&s.hasPermission(4));
        for(String op:List.of("inspect","move","inspect-moved"))root.then(Commands.literal(op)
            .then(Commands.argument("bundle",StringArgumentType.word()).then(Commands.argument("sha256",StringArgumentType.word()).executes(c->{
                if(busy())return 0;
                try{begin(c.getSource().getServer(),op,StringArgumentType.getString(c,"bundle"),StringArgumentType.getString(c,"sha256"));return 1;}
                catch(Exception|LinkageError error){return 0;}
            }))));
        root.then(Commands.literal("status").executes(c->{c.getSource().sendSuccess(()->Component.literal("relocation busy="+busy()+"; private receipt only; clone invoked="+cloneInvoked+"; quarantine="+quarantined),false);return 1;}));
        root.then(Commands.literal("cleanup").executes(c->{if(running||!busy())return 0;retryCleanup();return busy()?0:1;}));
        event.getDispatcher().register(root);
    }
    public void stop(){if(running)finish("server stopped; uncertain intent retained",true);else if(busy())retryCleanup();}
    /** Read persisted data first; then normal bounded native loading, never a managed wait. */
    public void tick(MinecraftServer server){
        if(!server.isSameThread())return;
        if(running)try{
            if(!server.getPlayerList().getPlayers().isEmpty()||lease==null||!lease.valid())throw new IllegalStateException("Actual player/lease custody changed; no move");
            if(System.nanoTime()-started>180_000_000_000L)throw new IllegalStateException("Finite relocation readiness expired");
            checkpoint();
            if(phase.equals("persisted")){
                if(!persisted.poll())return;
                report.put("current_persisted_before_tickets",persisted.report());
                for(ChunkPos c:centers){tickets.add(c);ticket(c,true);}
                phase="load";return;
            }
            if(phase.equals("load")){
                if(++loadingTicks>600)throw new IllegalStateException("Finite FULL/entity readiness timeout");
                if(pending.isEmpty()){
                    for(ChunkPos c:chunks)if(!level.getChunkSource().hasChunk(c.x,c.z))return;
                    for(ChunkPos c:chunks)pending.add(((worldfortwo.bridge.mixin.ChunkCacheAccess)(Object)level.getChunkSource()).awftQueueChunk(c.x,c.z,ChunkStatus.FULL,false));
                }
                for(var f:pending){if(!f.isDone())return;Object v=f.getNow(null);if(!(v instanceof net.minecraft.server.level.ChunkResult<?> r)||r.orElse(null)==null)throw new IllegalStateException("Native existing FULL chunk unavailable");}
                if(!loaded())return;
                pending.clear();phase="atomic";syncStarted=System.nanoTime();ready(server);atomic(server);return;
            }
        }catch(Exception|LinkageError error){failed(error);return;}
        if(!running&&busy()&&cleanupAttempts<3&&++cleanupDelay>=20){cleanupDelay=0;retryCleanup();}
    }
    private void ticket(ChunkPos c,boolean add)throws Exception{
        level.getChunkSource().getClass().getMethod(add?"addRegionTicket":"removeRegionTicket",TicketType.class,ChunkPos.class,int.class,Object.class,boolean.class).invoke(level.getChunkSource(),TICKET,c,2,c,true);
    }
    private boolean loaded(){for(ChunkPos c:chunks){var actual=level.getChunkSource().getChunkNow(c.x,c.z);if(actual==null||!actual.getPersistedStatus().isOrAfter(ChunkStatus.FULL)||!level.areEntitiesLoaded(c.toLong()))return false;}return true;}
    private static String sha(byte[] bytes)throws Exception{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));}
    private static byte[] bytes(Path file,int max)throws Exception{
        if(Files.isSymbolicLink(file)||!Files.isRegularFile(file,LinkOption.NOFOLLOW_LINKS)||Files.size(file)<1||Files.size(file)>max)throw new IllegalStateException("Finite regular evidence required");
        try(InputStream in=Files.newInputStream(file)){byte[] b=in.readNBytes(max+1);if(b.length>max)throw new IllegalStateException("Evidence allocation exceeded");return b;}
    }
    private Path owned(String text)throws Exception{
        Path rel=Path.of(text);if(rel.isAbsolute()||text.contains(":")||text.contains("\\"))throw new IllegalStateException("Home-relative evidence only");
        for(Path p:rel)if(p.toString().equals("..")||p.toString().equals("."))throw new IllegalStateException("No evidence traversal");
        Path p=home.resolve(rel).normalize();if(!p.startsWith(home)||!p.toRealPath().startsWith(home.toRealPath()))throw new IllegalStateException("Foreign evidence");
        for(Path q=p;q!=null&&!q.equals(home);q=q.getParent())if(Files.isSymbolicLink(q)||!q.toRealPath().equals(q))throw new IllegalStateException("Redirected evidence");return p;
    }
    private JsonObject read(Path path,int max)throws Exception{return JsonParser.parseString(new String(bytes(path,max),StandardCharsets.UTF_8)).getAsJsonObject();}
    private JsonObject ref(String key,int max)throws Exception{
        JsonObject r=request.getAsJsonObject(key);byte[] raw=bytes(owned(r.get("path").getAsString()),max);
        if(raw.length!=r.get("bytes").getAsInt()||!sha(raw).equals(r.get("sha256").getAsString()))throw new IllegalStateException("Exact reference changed: "+key);
        return JsonParser.parseString(new String(raw,StandardCharsets.UTF_8)).getAsJsonObject();
    }
    private static BlockPos pos(JsonElement v){JsonArray a=v.getAsJsonArray();if(a.size()!=3)throw new IllegalStateException("Exact position");return new BlockPos(a.get(0).getAsBigDecimal().intValueExact(),a.get(1).getAsBigDecimal().intValueExact(),a.get(2).getAsBigDecimal().intValueExact());}
    private static List<Integer> xyz(BlockPos p){return List.of(p.getX(),p.getY(),p.getZ());}
    private BlockPos translated(BlockPos p){return p.offset(dx,dy,dz);}
    private static boolean inside(BlockPos p,BlockPos a,BlockPos b){return p.getX()>=a.getX()&&p.getX()<=b.getX()&&p.getY()>=a.getY()&&p.getY()<=b.getY()&&p.getZ()>=a.getZ()&&p.getZ()<=b.getZ();}
    @SuppressWarnings({"rawtypes","unchecked"}) private static BlockState parse(String text){
        String[] parts=text.split("\\[",2);ResourceLocation id=ResourceLocation.parse(parts[0]);if(!BuiltInRegistries.BLOCK.containsKey(id))throw new IllegalStateException("Unknown block");
        BlockState s=BuiltInRegistries.BLOCK.get(id).defaultBlockState();Set<String> seen=new HashSet<>();
        if(parts.length==2){if(!parts[1].endsWith("]"))throw new IllegalStateException("Malformed complete state");for(String bit:parts[1].substring(0,parts[1].length()-1).split(",")){
            String[] pair=bit.split("=",2);if(pair.length!=2||!seen.add(pair[0]))throw new IllegalStateException("Duplicate state property");Property p=s.getBlock().getStateDefinition().getProperty(pair[0]);if(p==null)throw new IllegalStateException("Unknown state property");s=s.setValue(p,(Comparable)p.getValue(pair[1]).orElseThrow());}}
        if(seen.size()!=s.getValues().size())throw new IllegalStateException("Full actual state properties required, no unspecified defaults");return s;
    }
    private Map<BlockPos,BlockState> plan(JsonObject p,int count)throws Exception{
        if(!p.get("format").getAsString().equals("awft-native-settlement:1")||!p.get("construction_forbidden").getAsBoolean()
            ||!p.get("seed").equals(request.get("seed"))||!p.get("world_path").equals(request.get("world_path"))||p.getAsJsonArray("commands").size()!=0)throw new IllegalStateException("Exact non-executable world proof required");
        JsonArray palette=p.getAsJsonArray("palette"),rows=p.getAsJsonArray("blocks");if(rows.size()!=count||palette.size()>512)throw new IllegalStateException("Exact finite complete geometry required");
        Map<BlockPos,BlockState> result=new LinkedHashMap<>();for(JsonElement e:rows){JsonArray a=e.getAsJsonArray();if(a.size()!=4)throw new IllegalStateException("Exact geometry row");
            BlockPos q=new BlockPos(a.get(0).getAsBigDecimal().intValueExact(),a.get(1).getAsBigDecimal().intValueExact(),a.get(2).getAsBigDecimal().intValueExact());int n=a.get(3).getAsBigDecimal().intValueExact();if(n<0||n>=palette.size()||result.put(q,parse(palette.get(n).getAsString()))!=null)throw new IllegalStateException("Duplicate/invalid geometry");}return result;
    }
    private void proof(String key,String geometry,int count)throws Exception{
        JsonObject r=request.getAsJsonObject(key),p=ref(key,131072);Path file=owned(r.get("path").getAsString());
        if(!new String(bytes(file.resolveSibling(file.getFileName()+".complete"),128),StandardCharsets.UTF_8).trim().equals(r.get("sha256").getAsString())
            ||!p.get("operation").getAsString().equals("verify")||!p.get("plan_sha256").equals(request.getAsJsonObject(geometry).get("sha256"))
            ||p.get("blocks").getAsInt()!=count||p.get("failures").getAsInt()!=0||p.has("error")||p.get("cleanup_required").getAsBoolean()
            ||p.get("temporary_tickets_remaining").getAsInt()!=0||p.get("pending_shared_chunk_futures").getAsInt()!=0||p.has("ticket_cleanup_error")||!p.get("status").getAsString().equals("verified actual block identities, orientation, block entities and supplied inventories"))throw new IllegalStateException("Actual clean native geometry proof required");
        Instant at=Instant.parse(p.get("finished").getAsString());if(at.isAfter(Instant.now())||at.isBefore(Instant.now().minusSeconds(1200)))throw new IllegalStateException("Native before proof stale");
    }
    private void checkpoint()throws Exception{
        JsonObject cp=ref("current_backup",65536),owner=read(owned("dashboard/artistic-owner.json"),65536);
        if(!cp.get("verified").getAsBoolean()||!cp.get("sha256").equals(request.get("backup_sha256"))
            ||!owner.get("backup_sha256").equals(request.get("backup_sha256"))||!owner.get("backup").equals(cp.get("id"))
            ||!owner.get("format").getAsString().equals("awft-artistic-stage:1")||!Path.of(owner.get("home").getAsString()).toRealPath().equals(home.toRealPath()))throw new IllegalStateException("Current stopped owner/checkpoint changed");
    }
    private void admit(MinecraftServer server,String bundle,String expected)throws Exception{
        if(!server.isSameThread()||!bundle.matches("relocation-[a-f0-9]{16}")||!expected.matches("[a-f0-9]{64}")||!bundle.endsWith(expected.substring(0,16)))throw new IllegalStateException("Bounded immutable typed request only");
        Path root=Path.of("D:/A World for Two/staging/world-tests").toRealPath();Path actual=home.toRealPath();
        if(!actual.equals(home)||!actual.startsWith(root)||actual.equals(root)||server.getPort()!=25575
            ||!server.getWorldPath(LevelResource.ROOT).toRealPath().equals(home.resolve("world/RosewaterArtistic").toRealPath())
            ||!server.getPlayerList().getPlayers().isEmpty())throw new IllegalStateException("Only the actual owned empty private artistic stage");
        byte[] raw=bytes(owned("dashboard/settlement/"+bundle+"/request.json"),131072);if(!sha(raw).equals(expected))throw new IllegalStateException("Request digest differs");
        request=JsonParser.parseString(new String(raw,StandardCharsets.UTF_8)).getAsJsonObject();requestSha=expected;
        JsonObject active=read(owned("packwiz/active.json"),65536),installed=read(owned("server/installed.json"),2*1024*1024);
        if(!request.get("format").getAsString().equals("awft-native-approved-capsule-relocation:2")||!request.get("candidate_version").getAsString().equals(candidate)||!request.get("bridge_version").getAsString().equals(bridge)
            ||!ModList.get().getModContainerById("awft_control_bridge").orElseThrow().getModInfo().getVersion().toString().equals(bridge)
            ||!active.get("version").getAsString().equals(candidate)||!installed.get("pack_version").getAsString().equals(candidate)
            ||!active.get("pack_sha256").equals(installed.get("pack_sha256"))||!active.get("pack_sha256").equals(request.get("pack_sha256")))throw new IllegalStateException("Actual candidate/bridge/pack differs");
        if(!classHash(NativeRelocationSupport.class).equals(request.get("native_class_sha256").getAsString())||!classHash(Ledger.class).equals(request.get("ledger_class_sha256").getAsString())||!classHash(Capsules.class).equals(request.get("catalog_class_sha256").getAsString())||!classHash(RuntimeTags.class).equals(request.get("runtime_tags_class_sha256").getAsString())||!classHash(CloneBinding.class).equals(request.get("clone_binding_class_sha256").getAsString())||!classHash(Uninvoked.class).equals(request.get("uninvoked_class_sha256").getAsString())||!classHash(net.minecraft.world.level.chunk.LevelChunk.class).equals(request.get("level_chunk_class_sha256").getAsString())||!classHash(CloneCommands.class).equals(request.get("vanilla_clone_class_sha256").getAsString()))throw new IllegalStateException("Exact native helper/game API bytes differ");
        level=server.overworld();if(!request.get("seed").getAsString().equals(Long.toString(level.getSeed()))||!Path.of(request.get("world_path").getAsString()).toRealPath().equals(server.getWorldPath(LevelResource.ROOT).toRealPath()))throw new IllegalStateException("Actual world identity differs");
        checkpoint();source.clear();destination.clear();supports.clear();expectedTags.clear();classPins.clear();
        JsonObject review=ref("owner_city_plan_review",65536);
        if(!review.get("format").getAsString().equals("awft-owner-city-plan-review:1")||!review.get("approved").getAsBoolean()
            ||!request.get("eastern_layout_sha256").getAsString().equals(EASTERN_LAYOUT)
            ||!review.get("eastern_layout_sha256").equals(request.get("eastern_layout_sha256"))
            ||!review.getAsJsonArray("allowed_operations").contains(new JsonPrimitive("approved-north-bank-city-rebuild")))throw new IllegalStateException("Actual owner city-map review is required before an urban move; producer cannot invent approval");
        if(!request.get("baseline_capture_backup_sha256").getAsString().equals(BASELINE)||!request.getAsJsonObject("catalog").get("sha256").getAsString().equals(CATALOG_SHA))throw new IllegalStateException("Only the exact sealed approved room catalogue");
        catalog=ref("catalog",2*1024*1024);capsuleId=request.get("capsule_id").getAsString();catalogRow=Capsules.select(catalog,capsuleId);
        int[] a=Capsules.box(catalogRow.get("source_bounds_xyz")),b=Capsules.box(catalogRow.get("destination_bounds_xyz"));
        LOW=new BlockPos(a[0],a[1],a[2]);HIGH=new BlockPos(a[3],a[4],a[5]);DEST=new BlockPos(b[0],b[1],b[2]);dx=b[0]-a[0];dy=b[1]-a[1];dz=b[2]-a[2];
        sourceCount=Capsules.integer(catalogRow.get("cells"));objectCount=Capsules.integer(catalogRow.get("objects"));supportCount=Capsules.integer(catalogRow.get("support_cells"));
        for(String k:List.of("original_source","original_destination")){String name=k.equals("original_source")?"source_original":"destination_original";if(!request.getAsJsonObject(k).equals(catalogRow.getAsJsonObject(name)))throw new IllegalStateException("Selected original capture reference differs");}
        JsonObject original=ref("original_source",131072),prior=ref("original_destination",131072),after=ref("source_geometry",131072),dest=ref("destination_geometry",131072),support=ref("destination_supports",131072);
        Map<BlockPos,BlockState> originalStates=plan(original,sourceCount),priorStates=plan(prior,sourceCount);source.putAll(plan(after,sourceCount));destination.putAll(plan(dest,sourceCount));supports.putAll(plan(support,supportCount));
        if(!after.get("backup_sha256").equals(request.get("backup_sha256"))||!dest.get("backup_sha256").equals(request.get("backup_sha256"))||!support.get("backup_sha256").equals(request.get("backup_sha256")))throw new IllegalStateException("Fresh current-checkpoint proofs required");
        Map<BlockPos,BlockState> preparations=new HashMap<>();for(JsonElement e:catalogRow.getAsJsonArray("source_cover_preparations")){JsonObject r=e.getAsJsonObject();preparations.put(pos(r.get("position")),parse(r.get("before").getAsString()));}
        for(BlockPos q:BlockPos.betweenClosed(LOW,HIGH)){
            BlockPos p=q.immutable(),d=translated(p);BlockState before=originalStates.get(p);
            if(before==null||source.get(p)==null||destination.get(d)==null||!destination.get(d).isAir()||!source.get(p).equals(preparations.containsKey(p)?parse("minecraft:air"):before))throw new IllegalStateException("Only exact source capsule/approved cover and completely AIR destination");
            if(preparations.containsKey(p)&&!preparations.get(p).equals(before))throw new IllegalStateException("Original ordinary cover differs");
        }
        if(after.getAsJsonArray("block_entities").size()!=objectCount||dest.getAsJsonArray("block_entities").size()!=0||support.getAsJsonArray("block_entities").size()!=0)throw new IllegalStateException("Exact complete original object custody required");
        Map<BlockPos,CompoundTag> originalTags=new HashMap<>();for(JsonElement e:original.getAsJsonArray("block_entities")){JsonObject r=e.getAsJsonObject();if(originalTags.put(pos(r.get("pos")),TagParser.parseTag(r.get("nbt").getAsString()))!=null)throw new IllegalStateException("Duplicate original tag");}
        for(JsonElement e:after.getAsJsonArray("block_entities")){JsonObject r=e.getAsJsonObject();BlockPos p=pos(r.get("pos"));if(!source.containsKey(p)||expectedTags.put(p,TagParser.parseTag(r.get("nbt").getAsString()))!=null)throw new IllegalStateException("BE capture coordinates differ");}
        if(!expectedTags.equals(originalTags))throw new IllegalStateException("Every full typed tag remains unchanged");
        for(JsonElement e:request.getAsJsonArray("BE_class_pins")){JsonObject r=e.getAsJsonObject();BlockPos p=pos(r.get("source_position"));if(!expectedTags.containsKey(p)||!CLASSES.contains(r.get("class").getAsString())||classPins.put(p,r)!=null)throw new IllegalStateException("Unexpected/missing native BE class pin");}
        if(classPins.size()!=objectCount)throw new IllegalStateException("Complete native class custody required");
        for(BlockPos p:supports.keySet())if(p.getY()!=b[1]-1||p.getX()<b[0]||p.getX()>b[3]||p.getZ()<b[2]||p.getZ()>b[5])throw new IllegalStateException("Foreign support plane");
        if(!action.equals("inspect-moved")){proof("source_native_verify","source_geometry",sourceCount);proof("destination_native_verify","destination_geometry",sourceCount);proof("supports_native_verify","destination_supports",supportCount);}
        String stable=sha((home.toRealPath()+"|"+BASELINE+"|"+Capsules.salt(capsuleId,dx,dy,dz)).getBytes(StandardCharsets.UTF_8));
        if(!stable.equals(request.get("transaction_id").getAsString()))throw new IllegalStateException("Stable once-only transaction identity differs");
        ledger=server.getWorldPath(LevelResource.ROOT).toRealPath().resolve("data/awft-relocations/"+stable);
        for(Path p=ledger;p!=null&&!p.equals(server.getWorldPath(LevelResource.ROOT).toRealPath());p=p.getParent())if(Files.exists(p,LinkOption.NOFOLLOW_LINKS)&&(Files.isSymbolicLink(p)||!p.toRealPath().equals(p)))throw new IllegalStateException("Redirected relocation ledger");
        lease=interlock.acquire("relocation:"+stable,true);if(lease==null||!lease.valid())throw new IllegalStateException("Exclusive native operation lease unavailable");
        admitted=true;
        report.put("capsule_id",capsuleId);report.put("transaction_id",stable);report.put("request_sha256",requestSha);report.put("candidate",candidate);report.put("bridge",bridge);
        report.put("native_runtime_id",runtimeId);report.put("current_backup_sha256",request.get("backup_sha256").getAsString());
        report.put("source_geometry_sha256",request.getAsJsonObject("source_geometry").get("sha256").getAsString());report.put("destination_geometry_sha256",request.getAsJsonObject("destination_geometry").get("sha256").getAsString());
    }
    private static String classHash(Class<?> c)throws Exception{String path="/"+c.getName().replace('.','/')+".class";try(InputStream in=c.getResourceAsStream(path)){if(in==null)throw new IllegalStateException("Class resource unavailable");byte[] raw=in.readNBytes(262145);if(raw.length==0||raw.length>262144)throw new IllegalStateException("Bounded class bytes required");return sha(raw);}}
    private void ready(MinecraftServer server)throws Exception{
        if(!server.isSameThread()||lease==null||!lease.valid()||!server.getPlayerList().getPlayers().isEmpty())throw new IllegalStateException("Current exclusive empty-server/thread custody lost");checkpoint();
        if(!loaded())throw new IllegalStateException("Actual retained FULL/entity-loaded capsule neighbors required");
        if(System.nanoTime()-syncStarted>2_000_000_000L)throw new IllegalStateException("Bounded synchronous native transaction expired");
    }
    private void dependencies()throws Exception{
        for(JsonElement e:catalogRow.getAsJsonArray("dependencies")){
            String id=e.getAsString();JsonObject dep=Capsules.select(catalog,id);int[] a=Capsules.box(dep.get("source_bounds_xyz")),b=Capsules.box(dep.get("destination_bounds_xyz"));
            String key=sha((home.toRealPath()+"|"+BASELINE+"|"+Capsules.salt(id,b[0]-a[0],b[1]-a[1],b[2]-a[2])).getBytes(StandardCharsets.UTF_8));Path path=level.getServer().getWorldPath(LevelResource.ROOT).toRealPath().resolve("data/awft-relocations/"+key);
            byte[] raw=bytes(path.resolve("completed.json"),1048576);if(!new String(bytes(path.resolve("completed.json.sha256"),128),StandardCharsets.UTF_8).trim().equals(sha(raw)))throw new IllegalStateException("Durable dependency completion missing/changed");
            JsonObject done=JsonParser.parseString(new String(raw,StandardCharsets.UTF_8)).getAsJsonObject();if(!done.get("transaction_id").getAsString().equals(key)||!done.get("intent_sha256").getAsString().equals(sha(bytes(path.resolve(activeIntent(done)),1048576))))throw new IllegalStateException("Foreign dependency completion");
        }
    }
    private void states(Map<BlockPos,BlockState> expected)throws Exception{for(var e:expected.entrySet())if(!level.getBlockState(e.getKey()).equals(e.getValue()))throw new IllegalStateException("Actual complete state changed at "+e.getKey());}
    private void spatialAndModel()throws Exception{
        AABB a=new AABB(LOW.getX(),LOW.getY(),LOW.getZ(),HIGH.getX()+1,HIGH.getY()+1,HIGH.getZ()+1),b=a.move(dx,dy,dz);
        if(!level.getEntities((Entity)null,a.inflate(.25)).isEmpty()||!level.getEntities((Entity)null,b.inflate(.25)).isEmpty())throw new IllegalStateException("Preserve actual entity occupying source/destination/model envelope");
        for(var e:source.entrySet()){
            BlockPos p=e.getKey();BlockState s=e.getValue();if(!s.getFluidState().isEmpty())throw new IllegalStateException("No fluid-bearing source cell");
            if(!s.canSurvive(level,p))throw new IllegalStateException("A retained source fixture has no real native survival/support state");
            String blockId=BuiltInRegistries.BLOCK.getKey(s.getBlock()).toString();
            if(blockId.endsWith("_door")&&!blockId.endsWith("_trapdoor")){
                Property<?> half=s.getBlock().getStateDefinition().getProperty("half");String value=half==null?"":s.getValue(half).toString().toLowerCase(Locale.ROOT);
                BlockPos other=value.equals("lower")?p.above():p.below();BlockState pair=source.get(other);
                if(!Set.of("lower","upper").contains(value)||pair==null||pair.getBlock()!=s.getBlock()||pair.getValue(half).toString().equalsIgnoreCase(value))throw new IllegalStateException("A genuine door pair escapes the source capsule");
            }
            if(blockId.startsWith("minecraft:")&&blockId.endsWith("_bed")){
                var part=s.getBlock().getStateDefinition().getProperty("part");var facing=s.getBlock().getStateDefinition().getProperty("facing");
                String v=s.getValue(part).toString().toLowerCase(Locale.ROOT),f=s.getValue(facing).toString().toLowerCase(Locale.ROOT);Direction d=Direction.byName(f);if(d==null)throw new IllegalStateException("Unknown bed direction");
                BlockPos q=p.relative(v.equals("head")?d.getOpposite():d);BlockState pair=source.get(q);if(pair==null||pair.getBlock()!=s.getBlock()||pair.getValue(part).equals(s.getValue(part))||!pair.getValue(facing).equals(s.getValue(facing)))throw new IllegalStateException("A genuine bed pair escapes the capsule");
            }
            for(var shape:List.of(s.getShape(level,p),s.getCollisionShape(level,p))){if(shape.isEmpty())continue;AABB box=shape.bounds().move(p);
                if(box.minX<a.minX||box.minY<a.minY||box.minZ<a.minZ||box.maxX>a.maxX||box.maxY>a.maxY||box.maxZ>a.maxZ)throw new IllegalStateException("Native source model/collision shape escapes capsule; expand and review instead of truncating");}
            if(s.hasBlockEntity()!=expectedTags.containsKey(p))throw new IllegalStateException("Foreign/missing native BE in complete capsule");
            BlockEntity be=level.getBlockEntity(p);if(s.hasBlockEntity()&&(be==null||be.isRemoved()))throw new IllegalStateException("Actual native BE unavailable");
        }
        for(BlockPos p:destination.keySet())if(level.getBlockEntity(p)!=null)throw new IllegalStateException("Destination BE is never overwritten");
        for(BlockPos p:supports.keySet())if(!level.getBlockState(p).isFaceSturdy(level,p,Direction.UP)||!level.getBlockState(p).getFluidState().isEmpty()||level.getBlockEntity(p)!=null)throw new IllegalStateException("Real retained destination full-face support required");
    }
    private JsonObject stack(ItemStack item)throws Exception{
        JsonObject r=new JsonObject();r.addProperty("empty",item.isEmpty());
        if(item.isEmpty()){
            if(item.getCount()!=0||item.getComponents().iterator().hasNext())throw new IllegalStateException("Noncanonical empty slot data is not proven cloneable; preserve it");
            r.addProperty("count",0);r.addProperty("item",BuiltInRegistries.ITEM.getKey(item.getItem()).toString());r.add("all_components",new JsonObject());return r;
        }
        r.addProperty("item",BuiltInRegistries.ITEM.getKey(item.getItem()).toString());r.addProperty("count",item.getCount());
        String saved=item.save(level.registryAccess()).toString();if(saved.length()>65536)throw new IllegalStateException("Bounded real ItemStack data required");r.addProperty("native_saved_stack",saved);
        JsonObject components=new JsonObject();for(TypedDataComponent<?> c:item.getComponents()){
            ResourceLocation id=BuiltInRegistries.DATA_COMPONENT_TYPE.getKey(c.type());if(id==null||c.type().isTransient()||c.type().codec()==null)throw new IllegalStateException("Unknown/transient component cannot be proven losslessly cloneable; hold actual stock");
            Tag tag=c.encodeValue(RegistryOps.create(NbtOps.INSTANCE,level.registryAccess())).getOrThrow();String value=tag.toString();if(value.length()>65536||components.size()>128)throw new IllegalStateException("Bounded complete components required");
            JsonObject valueRow=new JsonObject();valueRow.addProperty("class",c.value().getClass().getName());valueRow.addProperty("typed_native_NBT",value);components.add(id.toString(),valueRow);
        }r.add("all_components",components);return r;
    }
    private void tagMismatch(BlockPos p,CompoundTag raw,CompoundTag expected,CompoundTag actual){
        Map<String,Object> d=new LinkedHashMap<>();d.put("position",xyz(p));
        for(var e:Map.of("raw_catalog_storage_tag",raw,"actual_native_full_tag",actual).entrySet()){
            String value=e.getValue().toString();d.put(e.getKey(),value.length()<=65536?value:"TOO_LARGE; retained source reference and byte types below");}
        if(expected!=null){String value=expected.toString();d.put("expected_runtime_tag",value.length()<=65536?value:"TOO_LARGE");}
        Map<String,Integer> wanted=new TreeMap<>(),seen=new TreeMap<>();for(String k:raw.getAllKeys())wanted.put(k,(int)raw.get(k).getId());for(String k:actual.getAllKeys())seen.put(k,(int)actual.get(k).getId());
        d.put("raw_top_level_tag_types",wanted);d.put("actual_top_level_tag_types",seen);d.put("manual_item_component_iteration_started",false);report.put("private_runtime_tag_mismatch",d);
    }
    /** Native LevelChunk storage envelope, never a BE/custom-data normalizer. */
    static final class RuntimeTags {
        static CompoundTag expected(CompoundTag raw,CompoundTag nativeFull){
            if(raw==null||nativeFull==null)throw new IllegalStateException("Actual typed raw/native tags required");
            if(nativeFull.contains("keepPacked"))throw new IllegalStateException("Native BE writes keepPacked: storage-envelope collision, preserve without guessing");
            CompoundTag expected=raw.copy();
            if(raw.contains("keepPacked")){
                if(!raw.contains("keepPacked",Tag.TAG_BYTE)||raw.getByte("keepPacked")!=0)throw new IllegalStateException("Only exact native Byte false storage envelope is supported; no packed/wrong-width admission");
                expected.remove("keepPacked");
            }
            return expected;
        }
    }
    private JsonArray snapshots(boolean moved)throws Exception{
        JsonArray out=new JsonArray();int bytes=0;
        for(var e:expectedTags.entrySet()){
            BlockPos sourcePos=e.getKey(),p=moved?translated(sourcePos):sourcePos;BlockEntity be=level.getBlockEntity(p);JsonObject pin=classPins.get(sourcePos);
            if(be==null||be.isRemoved()||!be.getClass().getName().equals(pin.get("class").getAsString())||!classHash(be.getClass()).equals(pin.get("class_sha256").getAsString())
                ||!BuiltInRegistries.BLOCK_ENTITY_TYPE.getKey(be.getType()).toString().equals(pin.get("BE_id").getAsString()))throw new IllegalStateException("Actual pinned BE class/type identity differs");
            CompoundTag full=be.saveWithFullMetadata(level.registryAccess());if(be instanceof RandomizableContainerBlockEntity loot&&loot.getLootTable()!=null)throw new IllegalStateException("Never resolve or inspect unresolved loot by getItem");
            if(!moved){CompoundTag raw=expectedTags.get(sourcePos);CompoundTag expected;
                try{expected=RuntimeTags.expected(raw,full);}catch(IllegalStateException storage){tagMismatch(p,raw,null,full);throw storage;}
                if(!full.equals(expected)){tagMismatch(p,raw,expected,full);throw new IllegalStateException("Current complete native data differs from exact chunk-envelope-derived runtime expectation at "+p+"; private raw/native typed witness retained before component iteration");}}

            JsonObject r=new JsonObject();r.add("source_position",JSON.toJsonTree(xyz(sourcePos)));r.addProperty("class",be.getClass().getName());r.addProperty("class_sha256",classHash(be.getClass()));r.addProperty("BE_id",BuiltInRegistries.BLOCK_ENTITY_TYPE.getKey(be.getType()).toString());
            r.addProperty("full_native_NBT",full.toString());boolean container=be instanceof Container;r.addProperty("is_Container",container);
            if(container!=pin.get("Container").getAsBoolean())throw new IllegalStateException("Pinned native inventory role differs; never infer empty from a missing Items field");
            if(container){Container inv=(Container)be;int n=inv.getContainerSize();if(n<0||n>128)throw new IllegalStateException("Bounded actual slot census required");r.addProperty("native_slots",n);JsonArray slots=new JsonArray();for(int i=0;i<n;i++)slots.add(stack(inv.getItem(i)));r.add("all_slots",slots);}
            else if(be instanceof LecternBlockEntity lectern){JsonArray books=new JsonArray();books.add(stack(lectern.getBook()));r.add("additional_native_stacks",books);}
            else if(!Set.of("net.minecraft.world.level.block.entity.SignBlockEntity","net.mehvahdjukaar.supplementaries.common.block.tiles.GlobeBlockTile","net.minecraft.world.level.block.entity.BedBlockEntity").contains(be.getClass().getName()))throw new IllegalStateException("Non-Container role is not reviewed");
            bytes+=JSON.toJson(r).getBytes(StandardCharsets.UTF_8).length;if(bytes>262144)throw new IllegalStateException("Complete native snapshot exceeds finite256KiB UTF8");out.add(r);
        }return out;
    }
    private static CompoundTag tag(String value)throws Exception{return TagParser.parseTag(value);}
    private void compare(JsonArray before,JsonArray after,boolean moved)throws Exception{
        if(before.size()!=objectCount||after.size()!=objectCount)throw new IllegalStateException("Exact complete native instances required");
        for(int i=0;i<objectCount;i++){
            JsonObject a=before.get(i).getAsJsonObject(),b=after.get(i).getAsJsonObject();
            for(String k:List.of("source_position","class","class_sha256","BE_id","is_Container"))if(!a.get(k).equals(b.get(k)))throw new IllegalStateException("Native object identity/role changed");
            CompoundTag expected=tag(a.get("full_native_NBT").getAsString());if(moved){BlockPos p=translated(pos(a.get("source_position")));expected.putInt("x",p.getX());expected.putInt("y",p.getY());expected.putInt("z",p.getZ());}
            if(!expected.equals(tag(b.get("full_native_NBT").getAsString())))throw new IllegalStateException("Full typed native custom data differs beyond the explicit native XYZ relocation");
            if(a.has("additional_native_stacks")!=b.has("additional_native_stacks")||a.has("additional_native_stacks")&&!a.get("additional_native_stacks").equals(b.get("additional_native_stacks")))throw new IllegalStateException("Native non-Container book stack/components changed");
            if(a.get("is_Container").getAsBoolean()){
                if(!a.get("native_slots").equals(b.get("native_slots")))throw new IllegalStateException("Actual native slot size changed");JsonArray x=a.getAsJsonArray("all_slots"),y=b.getAsJsonArray("all_slots");if(x.size()!=y.size())throw new IllegalStateException("Incomplete slot census");
                for(int n=0;n<x.size();n++){JsonObject u=x.get(n).getAsJsonObject(),v=y.get(n).getAsJsonObject();if(!u.equals(v))throw new IllegalStateException("Actual ItemStack count or any encoded native component changed");}
            }
        }
    }
    static final class Capsules {
        static int integer(JsonElement value){return value.getAsBigDecimal().intValueExact();}
        static int[] box(JsonElement value){JsonArray a=value.getAsJsonArray();if(a.size()!=6)throw new IllegalStateException("Exact box");int[] b=new int[6];for(int i=0;i<6;i++)b[i]=integer(a.get(i));
            for(int i=0;i<3;i++)if(b[i]>b[i+3]||b[i+3]-b[i]>31)throw new IllegalStateException("Finite closed bounds");return b;}
        static String salt(String id,int x,int y,int z){return id.equals("eastern22/pippins-net:room:0")?"PIPPIN320|-13,0,0":id+"|"+x+","+y+","+z;}
        static JsonObject select(JsonObject catalog,String id){
            if(!catalog.get("format").getAsString().equals("awft-approved-eastern-relocation-catalog:2")||!catalog.get("eastern_layout_sha256").getAsString().equals("6f24640d9efefae3340be80d34bcd0e4788f2ded695aefe03d1d6815761a12a4")||catalog.getAsJsonArray("capsules").size()!=93)throw new IllegalStateException("Exact approved finite catalogue");
            JsonObject found=null;for(JsonElement e:catalog.getAsJsonArray("capsules")){JsonObject r=e.getAsJsonObject();if(r.get("id").getAsString().equals(id)){if(found!=null)throw new IllegalStateException("Duplicate capsule");found=r;}}
            if(found==null||!found.get("supported").getAsBoolean())throw new IllegalStateException("Unknown/held capsule, no authority inferred");
            int[] a=box(found.get("source_bounds_xyz")),b=box(found.get("destination_bounds_xyz"));JsonArray d=found.getAsJsonArray("translation_xyz");if(d.size()!=3)throw new IllegalStateException("Exact translation");boolean same=true;
            for(int i=0;i<3;i++){int delta=integer(d.get(i));same&=delta==0;if(b[i]-a[i]!=delta||b[i+3]-a[i+3]!=delta)throw new IllegalStateException("Cardinal unchanged box required");}
            int count=Math.multiplyExact(Math.multiplyExact(a[3]-a[0]+1,a[4]-a[1]+1),a[5]-a[2]+1),objects=integer(found.get("objects"));
            if(same||a[4]-a[1]!=3||count<1||count>512||count!=integer(found.get("cells"))||objects<1||objects>32||integer(found.get("support_cells"))!=(b[3]-b[0]+1)*(b[5]-b[2]+1))throw new IllegalStateException("Identity/resized/oversized/incomplete capsule refused");return found;
        }
    }
    /** Pure finite durable-file primitive, also used by the real adversarial
     * ledger fixture. Does not initialize Minecraft or create world objects. */
    static final class Ledger {
        static void create(Path path,byte[] raw)throws Exception{
            if(raw.length==0||raw.length>1048576||Files.isSymbolicLink(path))throw new IllegalStateException("Bounded new ledger bytes only");
            try(FileChannel f=FileChannel.open(path,StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE,LinkOption.NOFOLLOW_LINKS)){ByteBuffer b=ByteBuffer.wrap(raw);while(b.hasRemaining())f.write(b);f.force(true);}
        }
    }
    private void durable(Path path,JsonObject value)throws Exception{
        if(!level.getServer().isSameThread()||lease==null||!lease.valid())throw new IllegalStateException("Durable write without current native custody refused");
        Files.createDirectories(ledger);byte[] raw=(JSON.toJson(value)+"\n").getBytes(StandardCharsets.UTF_8);if(raw.length>1048576)throw new IllegalStateException("Bounded durable ledger required");
        Ledger.create(path,raw);
    }
    private JsonObject inspection()throws Exception{
        JsonObject p=ref("native_inspect",1048576);Path file=owned(request.getAsJsonObject("native_inspect").get("path").getAsString());
        if(!new String(bytes(file.resolveSibling(file.getFileName()+".complete"),128),StandardCharsets.UTF_8).trim().equals(request.getAsJsonObject("native_inspect").get("sha256").getAsString())
            ||!p.get("operation").getAsString().equals("inspect")||!p.get("status").getAsString().equals("inspected exact current native source/destination; no move")||!p.get("cleanup_passed").getAsBoolean()
            ||!p.get("transaction_id").equals(report.get("transaction_id")==null?JsonNull.INSTANCE:JSON.toJsonTree(report.get("transaction_id")))||!p.get("pack_sha256").equals(request.get("pack_sha256"))||p.get("clone_invoked").getAsBoolean())throw new IllegalStateException("Exact clean original native inspection required");
        if(!p.get("native_runtime_id").getAsString().equals(runtimeId)||!p.get("current_backup_sha256").equals(request.get("backup_sha256"))
            ||!p.get("source_geometry_sha256").equals(request.getAsJsonObject("source_geometry").get("sha256"))||!p.get("destination_geometry_sha256").equals(request.getAsJsonObject("destination_geometry").get("sha256")))throw new IllegalStateException("Same actual runtime/checkpoint/geometry inspection required");
        Instant finished=Instant.parse(p.get("finished").getAsString());if(finished.isAfter(Instant.now())||finished.isBefore(Instant.now().minusSeconds(120)))throw new IllegalStateException("Native inventory inspection stale");return p;
    }
    private void begin(MinecraftServer server,String op,String bundle,String expected)throws Exception{
        intentName="intent.json";action=op;running=true;admitted=terminalPending=false;cleanupAttempts=cleanupDelay=loadingTicks=0;intentAttempted=intentWritten=cloneInvoked=quarantined=false;started=System.nanoTime();report.clear();report.put("operation",op);report.put("started",Instant.now().toString());report.put("pack_sha256","unadmitted");report.put("request_sha256",expected.matches("[a-f0-9]{64}")?expected:"invalid");
        chunks.clear();centers.clear();pending.clear();persisted=null;
        try{admit(server,bundle,expected);report.put("pack_sha256",request.get("pack_sha256").getAsString());
            for(BlockPos p:List.of(LOW,HIGH,DEST,translated(HIGH)))centers.add(new ChunkPos(p));
            for(ChunkPos c:centers)for(int x=-1;x<=1;x++)for(int z=-1;z<=1;z++)chunks.add(new ChunkPos(c.x+x,c.z+z));
            if(chunks.size()>64||centers.size()>8)throw new IllegalStateException("Finite capsule neighbors exceeded");
            persisted=new NativeTreePatchReadiness(level,centers);phase="persisted";
        }catch(Exception|LinkageError error){failed(error);throw error;}
    }

    /** Resolve only the actual registered vanilla callback, before any intent. */
    static final class CloneBinding {
        static Class<?> callback(com.mojang.brigadier.ParseResults<?> parsed,Class<?> host){
            if(parsed.getReader().canRead())throw new IllegalStateException("Native clone command has unconsumed input");
            var context=parsed.getContext();com.mojang.brigadier.Command<?> selected=null;int depth=0;
            while(context!=null){
                if(++depth>8)throw new IllegalStateException("Bounded command context chain required");
                var command=context.getCommand();
                if(command!=null){if(selected!=null&&selected!=command)throw new IllegalStateException("Ambiguous native clone callbacks");selected=command;}
                context=context.getChild();
            }
            if(selected==null)throw new IllegalStateException("No selected real native clone callback");
            Class<?> c=selected.getClass();
            if(!c.getName().startsWith(host.getName()+"$$Lambda")||!c.isSynthetic()||!c.isHidden()
                ||c.getNestHost()!=host||c.getClassLoader()!=host.getClassLoader()||c.getModule()!=host.getModule())
                throw new IllegalStateException("Pinned real native CloneCommands callback/module/loader/nest required");
            return c;
        }
    }
    private com.mojang.brigadier.ParseResults<net.minecraft.commands.CommandSourceStack> nativeClone(MinecraftServer server)throws Exception{
        String command="clone "+LOW.getX()+" "+LOW.getY()+" "+LOW.getZ()+" "+HIGH.getX()+" "+HIGH.getY()+" "+HIGH.getZ()+" "+DEST.getX()+" "+DEST.getY()+" "+DEST.getZ()+" replace move";
        var console=server.createCommandSourceStack().withLevel(level).withSuppressedOutput();
        if(console.getEntity()!=null||!console.hasPermission(4))throw new IllegalStateException("Real permission4 native console only");
        if(!classHash(CloneCommands.class).equals(request.get("vanilla_clone_class_sha256").getAsString()))throw new IllegalStateException("Actual native clone host bytes changed");
        var parsed=server.getCommands().getDispatcher().parse(command,console);Class<?> callback=CloneBinding.callback(parsed,CloneCommands.class);
        Map<String,Object> binding=new LinkedHashMap<>();binding.put("class",callback.getName());binding.put("module",callback.getModule().getName());
        binding.put("loader_class",callback.getClassLoader()==null?"bootstrap":callback.getClassLoader().getClass().getName());
        binding.put("nest_host",callback.getNestHost().getName());binding.put("hidden",callback.isHidden());binding.put("synthetic",callback.isSynthetic());
        report.put("actual_native_clone_callback",binding);return parsed;
    }
    private JsonObject exactRef(JsonObject ref,int max)throws Exception{
        byte[] raw=bytes(owned(ref.get("path").getAsString()),max);
        if(raw.length!=ref.get("bytes").getAsInt()||!sha(raw).equals(ref.get("sha256").getAsString()))throw new IllegalStateException("Exact nested evidence changed");
        return JsonParser.parseString(new String(raw,StandardCharsets.UTF_8)).getAsJsonObject();
    }
    static final class Uninvoked {
        static final String TX="537132d7dc65e7758179b56109d518e8990cc422222b48f163a77a953178249b";
        static final String TERMINAL="36bc9697b81bf0c7ca760a1cfbc3178eeef151f3d507741199d8049d7f5a159b";
        static final String INTENT="a29842d7a1be6dd8f1ce557cd2d2daa0467539f7fce20059c09a8f8280a76bdd";
        static final String QUARANTINE="38723688b0abb171264e938a7ff79b47cd44c757a95431ed5c31e7a271bedf50";
        static void validate(JsonObject review,JsonObject prior,JsonObject intent,JsonObject quarantine,JsonArray fresh){
            if(!review.get("format").getAsString().equals("awft-explicit-uninvoked-relocation-review:1")||!review.get("approved").getAsBoolean()
                ||!review.get("allow_exactly_one_new_intent").getAsBoolean()||!review.get("transaction_id").getAsString().equals(TX)
                ||!review.get("prior_intent_sha256").getAsString().equals(INTENT)||!review.get("prior_quarantine_sha256").getAsString().equals(QUARANTINE)
                ||!review.getAsJsonObject("prior_terminal").get("sha256").getAsString().equals(TERMINAL))throw new IllegalStateException("Explicit exact uninvoked transaction review required");
            if(!prior.get("transaction_id").getAsString().equals(TX)||!intent.get("transaction_id").getAsString().equals(TX)
                ||!prior.get("capsule_id").getAsString().equals("eastern22/pippins-net:room:0")||!prior.get("operation").getAsString().equals("move")
                ||prior.get("clone_invoked").getAsBoolean()||!prior.get("intent_written").getAsBoolean()||!prior.get("quarantine").getAsBoolean()
                ||!prior.get("failed").getAsBoolean()||!prior.get("cleanup_passed").getAsBoolean()
                ||prior.get("owned_chunk_tickets").getAsInt()!=0||prior.get("pending_owned_futures").getAsInt()!=0||prior.get("pending_shared_chunk_futures").getAsInt()!=0
                ||prior.has("ticket_cleanup_error")||prior.has("lease_cleanup_error")
                ||!prior.get("private_error").getAsString().equals("Pinned real native CloneCommands implementation required")
                ||quarantine.get("clone_invoked").getAsBoolean()||!quarantine.get("request_sha256").equals(prior.get("request_sha256"))
                ||!intent.get("request_sha256").equals(prior.get("request_sha256")))throw new IllegalStateException("Only the proven never-invoked callback-admission failure is resolvable");
            if(!prior.getAsJsonArray("before_native_snapshots").equals(fresh)||!intent.getAsJsonArray("before_native_snapshots").equals(fresh))
                throw new IllegalStateException("Fresh real native full data/slots/components differ from original uninvoked intent");
            Instant created=Instant.parse(review.get("created").getAsString()),finished=Instant.parse(prior.get("finished").getAsString());
            if(created.isAfter(Instant.now())||created.isBefore(finished)||created.isBefore(Instant.now().minusSeconds(1200)))throw new IllegalStateException("Fresh explicit review ordering required");
        }
    }
    private JsonObject uninvokedResolution(JsonArray before)throws Exception{
        boolean prior=Files.exists(ledger.resolve("intent.json"),LinkOption.NOFOLLOW_LINKS)||Files.exists(ledger.resolve("quarantine.json"),LinkOption.NOFOLLOW_LINKS);
        if(Files.exists(ledger.resolve("completed.json"),LinkOption.NOFOLLOW_LINKS))throw new IllegalStateException("Completed transaction never replays");
        if(!prior){if(request.has("uninvoked_resolution_review"))throw new IllegalStateException("No original uninvoked intent for this review");return null;}
        if(!request.has("uninvoked_resolution_review")||!report.get("transaction_id").equals(Uninvoked.TX))throw new IllegalStateException("Existing intent/quarantine retained; no automatic replay");
        for(String name:List.of("uninvoked-resolution.json","intent-after-uninvoked-resolution.json","quarantine-after-uninvoked-resolution.json"))
            if(Files.exists(ledger.resolve(name),LinkOption.NOFOLLOW_LINKS))throw new IllegalStateException("One reviewed resolution already attempted; no second attempt");
        JsonObject review=ref("uninvoked_resolution_review",65536),terminal=exactRef(review.getAsJsonObject("prior_terminal"),1048576);
        Path terminalPath=owned(review.getAsJsonObject("prior_terminal").get("path").getAsString());
        if(!new String(bytes(terminalPath.resolveSibling(terminalPath.getFileName()+".complete"),128),StandardCharsets.UTF_8).trim().equals(Uninvoked.TERMINAL)
            ||!sha(bytes(ledger.resolve("intent.json"),1048576)).equals(Uninvoked.INTENT)||!sha(bytes(ledger.resolve("quarantine.json"),1048576)).equals(Uninvoked.QUARANTINE))
            throw new IllegalStateException("Original immutable uninvoked ledger/terminal differs");
        Uninvoked.validate(review,terminal,read(ledger.resolve("intent.json"),1048576),read(ledger.resolve("quarantine.json"),1048576),before);
        report.put("uninvoked_resolution_review_sha256",request.getAsJsonObject("uninvoked_resolution_review").get("sha256").getAsString());
        report.put("prior_uninvoked_intent_preserved",true);return review;
    }
    private static String activeIntent(JsonObject done){
        String name=done.has("active_intent_file")?done.get("active_intent_file").getAsString():"intent.json";
        if(!name.equals("intent.json")&&!name.equals("intent-after-uninvoked-resolution.json"))throw new IllegalStateException("Unknown durable intent filename");return name;
    }

    private void atomic(MinecraftServer server)throws Exception{
            if(action.equals("inspect-moved")){
                byte[] doneBytes=bytes(ledger.resolve("completed.json"),1048576);
                if(!new String(bytes(ledger.resolve("completed.json.sha256"),128),StandardCharsets.UTF_8).trim().equals(sha(doneBytes)))throw new IllegalStateException("Durable completion marker differs");
                JsonObject done=JsonParser.parseString(new String(doneBytes,StandardCharsets.UTF_8)).getAsJsonObject();if(!done.get("transaction_id").equals(JSON.toJsonTree(report.get("transaction_id")))||!done.get("intent_sha256").getAsString().equals(sha(bytes(ledger.resolve(activeIntent(done)),1048576))))throw new IllegalStateException("Foreign/mismatched durable completion and original intent");
                for(BlockPos p:source.keySet())if(!level.getBlockState(p).isAir()||level.getBlockEntity(p)!=null)throw new IllegalStateException("Source is no longer the saved completed AIR state; preserve current changes");
                for(var e:source.entrySet())if(!level.getBlockState(translated(e.getKey())).equals(e.getValue()))throw new IllegalStateException("Moved geometry changed after completion");
                JsonArray current=snapshots(true);compare(done.getAsJsonArray("before_native_snapshots"),current,true);report.put("moved_native_snapshots",current);
                boolean differentProcess=done.get("native_process_pid").getAsLong()!=ProcessHandle.current().pid()||!done.get("native_process_started_at").getAsString().equals(ProcessHandle.current().info().startInstant().orElseThrow().toString());
                report.put("native_restart_persistence_checked",differentProcess);finish("inspected actual conserved moved room; no replay",false);return;
            }
            dependencies();states(source);states(destination);states(supports);spatialAndModel();JsonArray before=snapshots(false);
            for(int i=0;i<objectCount;i++){JsonObject row=before.get(i).getAsJsonObject();if(!RuntimeTags.expected(expectedTags.get(pos(row.get("source_position"))),tag(row.get("full_native_NBT").getAsString())).equals(tag(row.get("full_native_NBT").getAsString())))throw new IllegalStateException("Actual full native tag differs from captured current source");}
            report.put("before_native_snapshots",before);
            JsonObject resolution=uninvokedResolution(before);var parsed=nativeClone(server);
            if(action.equals("inspect")){finish("inspected exact current native source/destination; no move",false);return;}
            JsonObject originalInspect=inspection();compare(originalInspect.getAsJsonArray("before_native_snapshots"),before,false);ready(server);
            JsonObject intent=new JsonObject();intent.addProperty("format","awft-native-approved-clone-intent:2");intent.addProperty("capsule_id",capsuleId);intent.addProperty("catalog_sha256",CATALOG_SHA);intent.addProperty("transaction_id",report.get("transaction_id").toString());intent.addProperty("request_sha256",requestSha);
            intent.addProperty("native_runtime_id",runtimeId);
            intent.addProperty("native_process_pid",ProcessHandle.current().pid());intent.addProperty("native_process_started_at",ProcessHandle.current().info().startInstant().orElseThrow().toString());
            intent.addProperty("created",Instant.now().toString());intent.add("before_native_snapshots",before);intent.addProperty("source_geometry_sha256",request.getAsJsonObject("source_geometry").get("sha256").getAsString());
            intentName=resolution==null?"intent.json":"intent-after-uninvoked-resolution.json";
            intent.addProperty("active_intent_file",intentName);if(resolution!=null)uninvokedResolution(before);intentAttempted=true;
            if(resolution!=null){JsonObject record=new JsonObject();record.addProperty("format","awft-native-uninvoked-intent-resolution:1");record.addProperty("transaction_id",Uninvoked.TX);
                record.addProperty("created",Instant.now().toString());record.add("explicit_review",request.get("uninvoked_resolution_review").deepCopy());record.addProperty("original_intent_sha256",Uninvoked.INTENT);
                record.addProperty("original_quarantine_sha256",Uninvoked.QUARANTINE);record.addProperty("prior_terminal_sha256",Uninvoked.TERMINAL);record.addProperty("fresh_inspection_sha256",request.getAsJsonObject("native_inspect").get("sha256").getAsString());
                record.add("fresh_native_snapshots",before);durable(ledger.resolve("uninvoked-resolution.json"),record);intent.addProperty("uninvoked_resolution_sha256",sha(bytes(ledger.resolve("uninvoked-resolution.json"),1048576)));}
            durable(ledger.resolve(intentName),intent);intentWritten=true;
            states(source);states(destination);states(supports);spatialAndModel();compare(before,snapshots(false),false);ready(server);
            cloneInvoked=true;int result=server.getCommands().getDispatcher().execute(parsed);report.put("native_clone_return",result);
            if(result<=0||result>sourceCount)throw new IllegalStateException("Native clone did not report a finite real operation");
            for(BlockPos p:source.keySet())if(!level.getBlockState(p).isAir()||level.getBlockEntity(p)!=null)throw new IllegalStateException("Native move source not completely AIR");
            for(var e:source.entrySet()){BlockPos q=translated(e.getKey());if(!level.getBlockState(q).equals(e.getValue())||!level.getBlockState(q).canSurvive(level,q))throw new IllegalStateException("Native move destination full state/survival differs; retain evidence without fitting expected states");}
            if(!level.getEntities((Entity)null,new AABB(LOW.getX(),LOW.getY(),LOW.getZ(),HIGH.getX()+1,HIGH.getY()+1,HIGH.getZ()+1).inflate(.25)).isEmpty()||!level.getEntities((Entity)null,new AABB(LOW.getX(),LOW.getY(),LOW.getZ(),HIGH.getX()+1,HIGH.getY()+1,HIGH.getZ()+1).move(dx,dy,dz).inflate(.25)).isEmpty())throw new IllegalStateException("Unexpected actual entity after clone; quarantine without deleting it");JsonArray after=snapshots(true);compare(before,after,true);ready(server);report.put("after_native_snapshots",after);
            JsonObject done=intent.deepCopy();done.addProperty("completed",Instant.now().toString());done.addProperty("native_clone_return",result);done.add("after_native_snapshots",after);
            done.addProperty("intent_sha256",sha(bytes(ledger.resolve(intentName),1048576)));
            durable(ledger.resolve("completed.json"),done);Ledger.create(ledger.resolve("completed.json.sha256"),(sha(bytes(ledger.resolve("completed.json"),1048576))+"\n").getBytes(StandardCharsets.UTF_8));finish("moved real vanilla room; all selected native object contents conserved; source AIR",false);
    }
    private void failed(Throwable error){
        if(intentAttempted||cloneInvoked){quarantined=true;try{JsonObject q=new JsonObject();q.addProperty("request_sha256",requestSha);q.addProperty("at",Instant.now().toString());q.addProperty("clone_invoked",cloneInvoked);q.addProperty("error_class",error.getClass().getName());q.addProperty("reason",String.valueOf(error.getMessage()));durable(ledger.resolve(intentName.equals("intent.json")?"quarantine.json":"quarantine-after-uninvoked-resolution.json"),q);}catch(Exception|LinkageError secondary){report.put("quarantine_publication_failed",secondary.getClass().getName());}}
        report.put("error_class",error.getClass().getName());report.put("private_error",String.valueOf(error.getMessage()));finish("refused or uncertain partial; preserve exact world and durable intent; no replay",true);
    }
    private void finish(String status,boolean failure){
        running=admitted=false;terminalPending=true;finalStatus=status;finalFailure=failure;
        report.put("finished",Instant.now().toString());retryCleanup();
    }
    private void retryCleanup(){
        cleanupAttempts++;boolean clean=true;
        for(var it=tickets.iterator();it.hasNext();){ChunkPos c=it.next();try{ticket(c,false);it.remove();}catch(Exception error){clean=false;report.put("ticket_cleanup_error",error.getClass().getName());}}
        pending.removeIf(CompletableFuture::isDone);boolean drained=pending.isEmpty()&&(persisted==null||persisted.drained());
        if(!tickets.isEmpty()||!drained)clean=false;
        if(clean&&lease!=null)try{lease.close();lease=null;report.remove("lease_cleanup_error");}catch(Exception error){clean=false;report.put("lease_cleanup_error",error.getClass().getName());}
        report.put("status",clean?finalStatus:"cleanup_required; exact world/intent retained");report.put("failed",finalFailure);report.put("clone_invoked",cloneInvoked);report.put("quarantine",quarantined);report.put("intent_written",intentWritten);
        report.put("cleanup_passed",clean&&lease==null);report.put("cleanup_attempts",cleanupAttempts);report.put("cleanup_finished",Instant.now().toString());report.put("owned_chunk_tickets",tickets.size());report.put("generation_requests",0);report.put("pending_owned_futures",pending.size()+(persisted==null?0:persisted.pending()));report.put("pending_shared_chunk_futures",pending.size());
        try{NativeJournal.terminal(journal,"relocation",report);terminalPending=false;report.remove("terminal_publication_failed");}catch(Exception error){terminalPending=true;report.put("terminal_publication_failed",error.getClass().getName());}
    }
}
