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
    private static final BlockPos LOW=new BlockPos(1236,64,-1194),HIGH=new BlockPos(1243,67,-1185),DEST=new BlockPos(1223,64,-1194);
    private static final BlockPos SOURCE_COVER=new BlockPos(1236,64,-1194),DEST_COVER=new BlockPos(1224,64,-1194);
    private static final String BASELINE="b0315f548e55a389bb01a3caeb4c5a8532abb3e6599f6a0a77785c6c4916dece";
    private static final String ORIGINAL_SOURCE="248b037d48da62bf31d209b0bb1ba48703c3cf697248139237b89a436b82ce39";
    private static final String ORIGINAL_DEST="b584443733234c2a6ca5edea7c9fc7bf9c0d178a4ad29f4145b99f409d778d1c";
    private static final String EASTERN_LAYOUT="6f24640d9efefae3340be80d34bcd0e4788f2ded695aefe03d1d6815761a12a4";
    private static final Set<String> CLASSES=Set.of(
        "earth.terrarium.handcrafted.common.blockentities.ContainerBlockEntity",
        "net.mehvahdjukaar.supplementaries.common.block.tiles.GlobeBlockTile",
        "net.mehvahdjukaar.supplementaries.common.block.tiles.ItemShelfBlockTile",
        "net.minecraft.world.level.block.entity.SmokerBlockEntity","net.minecraft.world.level.block.entity.SignBlockEntity");
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
                try{perform(c.getSource().getServer(),op,StringArgumentType.getString(c,"bundle"),StringArgumentType.getString(c,"sha256"));return busy()?0:1;}
                catch(Exception|LinkageError error){return 0;}
            }))));
        root.then(Commands.literal("status").executes(c->{c.getSource().sendSuccess(()->Component.literal("relocation busy="+busy()+"; private receipt only; clone invoked="+cloneInvoked+"; quarantine="+quarantined),false);return 1;}));
        root.then(Commands.literal("cleanup").executes(c->{if(running||!busy())return 0;retryCleanup();return busy()?0:1;}));
        event.getDispatcher().register(root);
    }
    public void stop(){if(running)finish("server stopped; uncertain intent retained",true);else if(busy())retryCleanup();}
    /** Never repeats a world operation. Only retries owned close/publication. */
    public void tick(MinecraftServer server){if(!server.isSameThread()||running||!busy()||cleanupAttempts>=3)return;if(++cleanupDelay>=20){cleanupDelay=0;retryCleanup();}}
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
    private static BlockPos translated(BlockPos p){return p.offset(-13,0,0);}
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
        if(!request.get("format").getAsString().equals("awft-native-pippin-relocation:1")||!request.get("candidate_version").getAsString().equals(candidate)||!request.get("bridge_version").getAsString().equals(bridge)
            ||!ModList.get().getModContainerById("awft_control_bridge").orElseThrow().getModInfo().getVersion().toString().equals(bridge)
            ||!active.get("version").getAsString().equals(candidate)||!installed.get("pack_version").getAsString().equals(candidate)
            ||!active.get("pack_sha256").equals(installed.get("pack_sha256"))||!active.get("pack_sha256").equals(request.get("pack_sha256")))throw new IllegalStateException("Actual candidate/bridge/pack differs");
        if(!classHash(NativeRelocationSupport.class).equals(request.get("native_class_sha256").getAsString())||!classHash(Ledger.class).equals(request.get("ledger_class_sha256").getAsString())||!classHash(CloneCommands.class).equals(request.get("vanilla_clone_class_sha256").getAsString()))throw new IllegalStateException("Exact native helper/game API bytes differ");
        level=server.overworld();if(!request.get("seed").getAsString().equals(Long.toString(level.getSeed()))||!Path.of(request.get("world_path").getAsString()).toRealPath().equals(server.getWorldPath(LevelResource.ROOT).toRealPath()))throw new IllegalStateException("Actual world identity differs");
        checkpoint();source.clear();destination.clear();supports.clear();expectedTags.clear();classPins.clear();
        JsonObject review=ref("owner_city_plan_review",65536);
        if(!review.get("format").getAsString().equals("awft-owner-city-plan-review:1")||!review.get("approved").getAsBoolean()
            ||!request.get("eastern_layout_sha256").getAsString().equals(EASTERN_LAYOUT)
            ||!review.get("eastern_layout_sha256").equals(request.get("eastern_layout_sha256"))
            ||!review.getAsJsonArray("allowed_operations").contains(new JsonPrimitive("pippin-native-relocation-prototype")))throw new IllegalStateException("Actual owner city-map review is required before an urban move; producer cannot invent approval");
        if(!request.get("baseline_capture_backup_sha256").getAsString().equals(BASELINE)||!request.getAsJsonObject("original_source").get("sha256").getAsString().equals(ORIGINAL_SOURCE)
            ||!request.getAsJsonObject("original_destination").get("sha256").getAsString().equals(ORIGINAL_DEST))throw new IllegalStateException("Exact original06 room capture required");
        JsonObject original=ref("original_source",131072),prior=ref("original_destination",131072),after=ref("source_geometry",131072),dest=ref("destination_geometry",131072),support=ref("destination_supports",131072);
        Map<BlockPos,BlockState> originalStates=plan(original,320),priorStates=plan(prior,320);source.putAll(plan(after,320));destination.putAll(plan(dest,320));supports.putAll(plan(support,80));
        if(!after.get("backup_sha256").equals(request.get("backup_sha256"))||!dest.get("backup_sha256").equals(request.get("backup_sha256"))||!support.get("backup_sha256").equals(request.get("backup_sha256")))throw new IllegalStateException("Fresh current-checkpoint proofs required");
        for(BlockPos q:BlockPos.betweenClosed(LOW,HIGH)){
            BlockPos p=q.immutable(),d=translated(p);BlockState before=originalStates.get(p);
            if(before==null||source.get(p)==null||destination.get(d)==null||!destination.get(d).isAir()||!source.get(p).equals(p.equals(SOURCE_COVER)?parse("minecraft:air"):before))throw new IllegalStateException("Only exact one-source-cover/AIR-destination preparation is admitted");
            BlockState was=priorStates.get(d);if(was==null||(!d.equals(DEST_COVER)&&!was.isAir()))throw new IllegalStateException("Unexpected original destination content");
        }
        if(!originalStates.get(SOURCE_COVER).equals(parse("regions_unexplored:grass_sprouts"))||!priorStates.get(DEST_COVER).equals(parse("supplementaries:barnacles[down=true,east=false,north=false,south=false,up=false,waterlogged=false,west=false]")))throw new IllegalStateException("Original ordinary-cover identity differs");
        if(!original.getAsJsonArray("block_entities").equals(after.getAsJsonArray("block_entities"))||after.getAsJsonArray("block_entities").size()!=7||dest.getAsJsonArray("block_entities").size()!=0||support.getAsJsonArray("block_entities").size()!=0)throw new IllegalStateException("All seven original actual tags must be retained unchanged");
        for(JsonElement e:after.getAsJsonArray("block_entities")){JsonObject r=e.getAsJsonObject();BlockPos p=pos(r.get("pos"));if(!source.containsKey(p)||expectedTags.put(p,TagParser.parseTag(r.get("nbt").getAsString()))!=null)throw new IllegalStateException("BE capture coordinates differ");}
        for(JsonElement e:request.getAsJsonArray("BE_class_pins")){JsonObject r=e.getAsJsonObject();BlockPos p=pos(r.get("source_position"));if(!expectedTags.containsKey(p)||!CLASSES.contains(r.get("class").getAsString())||classPins.put(p,r)!=null)throw new IllegalStateException("Unexpected/missing native BE class pin");}
        if(classPins.size()!=7)throw new IllegalStateException("Complete seven-object native class custody required");
        for(BlockPos p:supports.keySet())if(p.getY()!=63||p.getX()<1223||p.getX()>1230||p.getZ()<-1194||p.getZ()>-1185)throw new IllegalStateException("Foreign support plane");
        if(!action.equals("inspect-moved")){proof("source_native_verify","source_geometry",320);proof("destination_native_verify","destination_geometry",320);proof("supports_native_verify","destination_supports",80);}
        String stable=sha((home.toRealPath()+"|"+BASELINE+"|PIPPIN320|-13,0,0").getBytes(StandardCharsets.UTF_8));
        if(!stable.equals(request.get("transaction_id").getAsString()))throw new IllegalStateException("Stable once-only transaction identity differs");
        ledger=server.getWorldPath(LevelResource.ROOT).toRealPath().resolve("data/awft-relocations/"+stable);
        for(Path p=ledger;p!=null&&!p.equals(server.getWorldPath(LevelResource.ROOT).toRealPath());p=p.getParent())if(Files.exists(p,LinkOption.NOFOLLOW_LINKS)&&(Files.isSymbolicLink(p)||!p.toRealPath().equals(p)))throw new IllegalStateException("Redirected relocation ledger");
        lease=interlock.acquire("relocation:"+stable,true);if(lease==null||!lease.valid())throw new IllegalStateException("Exclusive native operation lease unavailable");
        admitted=true;
        report.put("transaction_id",stable);report.put("request_sha256",requestSha);report.put("candidate",candidate);report.put("bridge",bridge);
        report.put("native_runtime_id",runtimeId);report.put("current_backup_sha256",request.get("backup_sha256").getAsString());
        report.put("source_geometry_sha256",request.getAsJsonObject("source_geometry").get("sha256").getAsString());report.put("destination_geometry_sha256",request.getAsJsonObject("destination_geometry").get("sha256").getAsString());
    }
    private static String classHash(Class<?> c)throws Exception{String path="/"+c.getName().replace('.','/')+".class";try(InputStream in=c.getResourceAsStream(path)){if(in==null)throw new IllegalStateException("Class resource unavailable");byte[] raw=in.readNBytes(262145);if(raw.length==0||raw.length>262144)throw new IllegalStateException("Bounded class bytes required");return sha(raw);}}
    private void ready(MinecraftServer server)throws Exception{
        if(!server.isSameThread()||lease==null||!lease.valid()||!server.getPlayerList().getPlayers().isEmpty())throw new IllegalStateException("Current exclusive empty-server/thread custody lost");checkpoint();
        for(int cx=75;cx<=78;cx++)for(int cz=-76;cz<=-74;cz++){
            var c=level.getChunkSource().getChunkNow(cx,cz);
            if(c==null||!c.getPersistedStatus().isOrAfter(ChunkStatus.FULL)||!level.areEntitiesLoaded(ChunkPos.asLong(cx,cz)))throw new IllegalStateException("All twelve persisted FULL/entity-loaded neighbor chunks required; controller never loads/generates");
        }
        if(System.nanoTime()-started>2_000_000_000L)throw new IllegalStateException("Bounded synchronous native transaction expired");
    }
    private void states(Map<BlockPos,BlockState> expected)throws Exception{for(var e:expected.entrySet())if(!level.getBlockState(e.getKey()).equals(e.getValue()))throw new IllegalStateException("Actual complete state changed at "+e.getKey());}
    private void spatialAndModel()throws Exception{
        AABB a=new AABB(LOW.getX(),LOW.getY(),LOW.getZ(),HIGH.getX()+1,HIGH.getY()+1,HIGH.getZ()+1),b=a.move(-13,0,0);
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
    private JsonArray snapshots(boolean moved)throws Exception{
        JsonArray out=new JsonArray();int bytes=0;
        for(var e:expectedTags.entrySet()){
            BlockPos sourcePos=e.getKey(),p=moved?translated(sourcePos):sourcePos;BlockEntity be=level.getBlockEntity(p);JsonObject pin=classPins.get(sourcePos);
            if(be==null||be.isRemoved()||!be.getClass().getName().equals(pin.get("class").getAsString())||!classHash(be.getClass()).equals(pin.get("class_sha256").getAsString())
                ||!BuiltInRegistries.BLOCK_ENTITY_TYPE.getKey(be.getType()).toString().equals(pin.get("BE_id").getAsString()))throw new IllegalStateException("Actual pinned BE class/type identity differs");
            CompoundTag full=be.saveWithFullMetadata(level.registryAccess());if(be instanceof RandomizableContainerBlockEntity loot&&loot.getLootTable()!=null)throw new IllegalStateException("Never resolve or inspect unresolved loot by getItem");
            if(!moved&&!full.equals(expectedTags.get(sourcePos)))throw new IllegalStateException("Current complete native data changed; preserve it before inspecting any component codec");
            JsonObject r=new JsonObject();r.add("source_position",JSON.toJsonTree(xyz(sourcePos)));r.addProperty("class",be.getClass().getName());r.addProperty("class_sha256",classHash(be.getClass()));r.addProperty("BE_id",BuiltInRegistries.BLOCK_ENTITY_TYPE.getKey(be.getType()).toString());
            r.addProperty("full_native_NBT",full.toString());boolean container=be instanceof Container;r.addProperty("is_Container",container);
            if(container!=pin.get("Container").getAsBoolean())throw new IllegalStateException("Pinned native inventory role differs; never infer empty from a missing Items field");
            if(container){Container inv=(Container)be;int n=inv.getContainerSize();if(n<0||n>128)throw new IllegalStateException("Bounded actual slot census required");r.addProperty("native_slots",n);JsonArray slots=new JsonArray();for(int i=0;i<n;i++)slots.add(stack(inv.getItem(i)));r.add("all_slots",slots);}
            else if(!Set.of("net.minecraft.world.level.block.entity.SignBlockEntity","net.mehvahdjukaar.supplementaries.common.block.tiles.GlobeBlockTile").contains(be.getClass().getName()))throw new IllegalStateException("Non-Container role is not reviewed");
            bytes+=JSON.toJson(r).getBytes(StandardCharsets.UTF_8).length;if(bytes>262144)throw new IllegalStateException("Complete native snapshot exceeds finite256KiB UTF8");out.add(r);
        }return out;
    }
    private static CompoundTag tag(String value)throws Exception{return TagParser.parseTag(value);}
    private void compare(JsonArray before,JsonArray after,boolean moved)throws Exception{
        if(before.size()!=7||after.size()!=7)throw new IllegalStateException("Seven native instances required");
        for(int i=0;i<7;i++){
            JsonObject a=before.get(i).getAsJsonObject(),b=after.get(i).getAsJsonObject();
            for(String k:List.of("source_position","class","class_sha256","BE_id","is_Container"))if(!a.get(k).equals(b.get(k)))throw new IllegalStateException("Native object identity/role changed");
            CompoundTag expected=tag(a.get("full_native_NBT").getAsString());if(moved){BlockPos p=translated(pos(a.get("source_position")));expected.putInt("x",p.getX());expected.putInt("y",p.getY());expected.putInt("z",p.getZ());}
            if(!expected.equals(tag(b.get("full_native_NBT").getAsString())))throw new IllegalStateException("Full typed native custom data differs beyond the explicit native XYZ relocation");
            if(a.get("is_Container").getAsBoolean()){
                if(!a.get("native_slots").equals(b.get("native_slots")))throw new IllegalStateException("Actual native slot size changed");JsonArray x=a.getAsJsonArray("all_slots"),y=b.getAsJsonArray("all_slots");if(x.size()!=y.size())throw new IllegalStateException("Incomplete slot census");
                for(int n=0;n<x.size();n++){JsonObject u=x.get(n).getAsJsonObject(),v=y.get(n).getAsJsonObject();if(!u.equals(v))throw new IllegalStateException("Actual ItemStack count or any encoded native component changed");}
            }
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
    private void perform(MinecraftServer server,String op,String bundle,String expected)throws Exception{
        action=op;running=true;admitted=terminalPending=false;cleanupAttempts=cleanupDelay=0;intentAttempted=intentWritten=cloneInvoked=quarantined=false;started=System.nanoTime();report.clear();report.put("operation",op);report.put("started",Instant.now().toString());report.put("pack_sha256","unadmitted");report.put("request_sha256",expected.matches("[a-f0-9]{64}")?expected:"invalid");
        try{
            admit(server,bundle,expected);report.put("pack_sha256",request.get("pack_sha256").getAsString());ready(server);
            if(action.equals("inspect-moved")){
                byte[] doneBytes=bytes(ledger.resolve("completed.json"),1048576);
                if(!new String(bytes(ledger.resolve("completed.json.sha256"),128),StandardCharsets.UTF_8).trim().equals(sha(doneBytes)))throw new IllegalStateException("Durable completion marker differs");
                JsonObject done=JsonParser.parseString(new String(doneBytes,StandardCharsets.UTF_8)).getAsJsonObject();if(!done.get("transaction_id").equals(JSON.toJsonTree(report.get("transaction_id")))||!done.get("intent_sha256").getAsString().equals(sha(bytes(ledger.resolve("intent.json"),1048576))))throw new IllegalStateException("Foreign/mismatched durable completion and original intent");
                for(BlockPos p:source.keySet())if(!level.getBlockState(p).isAir()||level.getBlockEntity(p)!=null)throw new IllegalStateException("Source is no longer the saved completed AIR state; preserve current changes");
                for(var e:source.entrySet())if(!level.getBlockState(translated(e.getKey())).equals(e.getValue()))throw new IllegalStateException("Moved geometry changed after completion");
                JsonArray current=snapshots(true);compare(done.getAsJsonArray("before_native_snapshots"),current,true);report.put("moved_native_snapshots",current);
                boolean differentProcess=done.get("native_process_pid").getAsLong()!=ProcessHandle.current().pid()||!done.get("native_process_started_at").getAsString().equals(ProcessHandle.current().info().startInstant().orElseThrow().toString());
                report.put("native_restart_persistence_checked",differentProcess);finish("inspected actual conserved moved room; no replay",false);return;
            }
            if(Files.exists(ledger.resolve("intent.json"),LinkOption.NOFOLLOW_LINKS)||Files.exists(ledger.resolve("completed.json"),LinkOption.NOFOLLOW_LINKS)||Files.exists(ledger.resolve("quarantine.json"),LinkOption.NOFOLLOW_LINKS))throw new IllegalStateException("A durable move intent already exists; never replay or automatically repair");
            states(source);states(destination);states(supports);spatialAndModel();JsonArray before=snapshots(false);
            for(int i=0;i<7;i++){JsonObject row=before.get(i).getAsJsonObject();if(!expectedTags.get(pos(row.get("source_position"))).equals(tag(row.get("full_native_NBT").getAsString())))throw new IllegalStateException("Actual full native tag differs from captured current source");}
            report.put("before_native_snapshots",before);
            if(action.equals("inspect")){finish("inspected exact current native source/destination; no move",false);return;}
            JsonObject originalInspect=inspection();compare(originalInspect.getAsJsonArray("before_native_snapshots"),before,false);ready(server);
            JsonObject intent=new JsonObject();intent.addProperty("format","awft-native-pippin-clone-intent:1");intent.addProperty("transaction_id",report.get("transaction_id").toString());intent.addProperty("request_sha256",requestSha);
            intent.addProperty("native_runtime_id",runtimeId);
            intent.addProperty("native_process_pid",ProcessHandle.current().pid());intent.addProperty("native_process_started_at",ProcessHandle.current().info().startInstant().orElseThrow().toString());
            intent.addProperty("created",Instant.now().toString());intent.add("before_native_snapshots",before);intent.addProperty("source_geometry_sha256",request.getAsJsonObject("source_geometry").get("sha256").getAsString());
            intentAttempted=true;durable(ledger.resolve("intent.json"),intent);intentWritten=true;
            states(source);states(destination);states(supports);spatialAndModel();compare(before,snapshots(false),false);ready(server);
            String command="clone 1236 64 -1194 1243 67 -1185 1223 64 -1194 replace move";
            var console=server.createCommandSourceStack().withLevel(level).withSuppressedOutput();if(console.getEntity()!=null||!console.hasPermission(4))throw new IllegalStateException("Real permission4 native console only");
            var parsed=server.getCommands().getDispatcher().parse(command,console);var nativeCommand=parsed.getContext().getCommand();
            if(nativeCommand==null||!nativeCommand.getClass().getName().startsWith("net.minecraft.server.commands.CloneCommands$$Lambda$"))throw new IllegalStateException("Pinned real native CloneCommands implementation required");
            cloneInvoked=true;int result=server.getCommands().getDispatcher().execute(parsed);report.put("native_clone_return",result);
            if(result<=0||result>320)throw new IllegalStateException("Native clone did not report a finite real operation");
            for(BlockPos p:source.keySet())if(!level.getBlockState(p).isAir()||level.getBlockEntity(p)!=null)throw new IllegalStateException("Native move source not completely AIR");
            for(var e:source.entrySet()){BlockPos q=translated(e.getKey());if(!level.getBlockState(q).equals(e.getValue())||!level.getBlockState(q).canSurvive(level,q))throw new IllegalStateException("Native move destination full state/survival differs; retain evidence without fitting expected states");}
            JsonArray after=snapshots(true);compare(before,after,true);ready(server);report.put("after_native_snapshots",after);
            JsonObject done=intent.deepCopy();done.addProperty("completed",Instant.now().toString());done.addProperty("native_clone_return",result);done.add("after_native_snapshots",after);
            done.addProperty("intent_sha256",sha(bytes(ledger.resolve("intent.json"),1048576)));
            durable(ledger.resolve("completed.json"),done);Ledger.create(ledger.resolve("completed.json.sha256"),(sha(bytes(ledger.resolve("completed.json"),1048576))+"\n").getBytes(StandardCharsets.UTF_8));finish("moved real vanilla room; seven native object contents conserved; source AIR",false);
        }catch(Exception|LinkageError error){
            if(intentAttempted||cloneInvoked){quarantined=true;try{JsonObject q=new JsonObject();q.addProperty("request_sha256",requestSha);q.addProperty("at",Instant.now().toString());q.addProperty("clone_invoked",cloneInvoked);q.addProperty("error_class",error.getClass().getName());q.addProperty("reason",String.valueOf(error.getMessage()));durable(ledger.resolve("quarantine.json"),q);}catch(Exception|LinkageError secondary){report.put("quarantine_publication_failed",secondary.getClass().getName());}}
            report.put("error_class",error.getClass().getName());report.put("private_error",String.valueOf(error.getMessage()));finish("refused or uncertain partial; preserve exact world and durable intent; no replay",true);throw error;
        }finally{if(running)finish("aborted; durable intent and exact world retained",true);}
    }
    private void finish(String status,boolean failure){
        running=admitted=false;terminalPending=true;finalStatus=status;finalFailure=failure;
        report.put("finished",Instant.now().toString());retryCleanup();
    }
    private void retryCleanup(){
        cleanupAttempts++;boolean clean=true;if(lease!=null)try{lease.close();lease=null;report.remove("lease_cleanup_error");}catch(Exception error){clean=false;report.put("lease_cleanup_error",error.getClass().getName());}
        report.put("status",clean?finalStatus:"cleanup_required; exact world/intent retained");report.put("failed",finalFailure);report.put("clone_invoked",cloneInvoked);report.put("quarantine",quarantined);report.put("intent_written",intentWritten);
        report.put("cleanup_passed",clean&&lease==null);report.put("cleanup_attempts",cleanupAttempts);report.put("cleanup_finished",Instant.now().toString());report.put("owned_chunk_tickets",0);report.put("generation_requests",0);report.put("pending_owned_futures",0);
        try{NativeJournal.terminal(journal,"relocation",report);terminalPending=false;report.remove("terminal_publication_failed");}catch(Exception error){terminalPending=true;report.put("terminal_publication_failed",error.getClass().getName());}
    }
}
