package worldfortwo.bridge;

import com.google.gson.*;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.serialization.JsonOps;
import net.minecraft.commands.Commands;
import net.minecraft.core.*;
import net.minecraft.core.registries.*;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.*;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.*;
import net.minecraft.tags.BlockTags;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.block.*;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.grower.TreeGrower;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.Property;
import net.minecraft.world.level.chunk.status.ChunkStatus;
import net.minecraft.world.level.levelgen.feature.ConfiguredFeature;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.AABB;
import net.neoforged.fml.ModList;
import net.neoforged.fml.loading.FMLPaths;
import net.neoforged.neoforge.event.RegisterCommandsEvent;

import java.io.InputStream;
import java.lang.invoke.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.CompletableFuture;

/** ISOLATED PROPOSAL: original native-sapling inspection/growth transaction.
 * No hand-stamped tree, virtual world, fake player, invented item consumption,
 * permanent force/wake, copied feature implementation or automatic plot retry.
 */
public final class NativeTreeGrowthSupport {
    private enum Phase { IDLE,HASH,DESCRIBE,LOAD,VERIFY,GROW,CLEANUP }
    private static final Gson JSON=new Gson();
    private static final String RU_FILE="regions-unexplored-0.6.3-neoforge-21.1.jar",RU_SHA="e7f2edd7bab869c2e566b1b251ea54c6b95834205276bf3a302859d72d9d0c9b";
    private static final Set<String> SAPLINGS=Set.of("minecraft:birch_sapling","regions_unexplored:magnolia_sapling","regions_unexplored:white_magnolia_sapling","regions_unexplored:pink_magnolia_sapling","regions_unexplored:maple_sapling","regions_unexplored:silver_birch_sapling","regions_unexplored:pine_sapling","regions_unexplored:larch_sapling","regions_unexplored:golden_larch_sapling");
    private static final TicketType<ChunkPos> TICKET=TicketType.create("awft_native_tree",Comparator.comparingLong(ChunkPos::toLong));
    private static final int MAX_INPUT=8*1024*1024,MAX_CELLS=131072,MAX_TICKS=1800,MAX_ATTEMPTS=12;
    private final String candidate,bridge;
    private final ArtisticEngineeringSupport.Interlock interlock;
    private final Path home=FMLPaths.GAMEDIR.get().resolve("..").toAbsolutePath().normalize(),journal=home.resolve("dashboard/settlement");
    private ArtisticEngineeringSupport.Lease lease;
    private ServerLevel level;
    private Phase phase=Phase.IDLE;
    private JsonObject request,plan,qualification;
    private String action,outcome,planSha;
    private int ticks,cursor,rolls,successRolls,performCalls;
    private boolean terminalPublished,worldResidual,mutated,quarantineLatched;
    private InputStream hashStream;
    private MessageDigest hashDigest;
    private BasicFileAttributes hashAttrs;
    private Path modPath;
    private long hashBytes;
    private final byte[] buffer=new byte[65536];
    private final Map<String,Object> report=new LinkedHashMap<>();
    private final List<String> saplings=new ArrayList<>();
    private final Map<String,JsonObject> descriptors=new TreeMap<>();
    private final Map<BlockPos,BlockState> before=new LinkedHashMap<>();
    private List<Map.Entry<BlockPos,BlockState>> cells=List.of();
    private final Set<Long> protectedColumns=new HashSet<>();
    private final Set<ChunkPos> chunks=new LinkedHashSet<>(),tickets=new LinkedHashSet<>();
    private final List<CompletableFuture<?>> pending=new ArrayList<>();
    private BlockPos root;
    private BlockState sapling;
    private AABB writeBounds;
    private int[] knownBounds;
    public NativeTreeGrowthSupport(String candidate,String bridge,ArtisticEngineeringSupport.Interlock interlock){this.candidate=Objects.requireNonNull(candidate);this.bridge=Objects.requireNonNull(bridge);this.interlock=Objects.requireNonNull(interlock);}
    public boolean busy(){return phase!=Phase.IDLE;}
    public void commands(RegisterCommandsEvent event){
        var command=Commands.literal("awfttrees").requires(s->s.getEntity()==null&&s.hasPermission(4));
        for(String mode:List.of("describe","grow"))command.then(Commands.literal(mode).then(Commands.argument("bundle",StringArgumentType.word()).then(Commands.argument("sha256",StringArgumentType.word()).executes(c->{
            if(busy()){c.getSource().sendFailure(Component.literal("Native tree operation or resource cleanup is active"));return 0;}
            try{begin(c.getSource().getServer(),mode,StringArgumentType.getString(c,"bundle"),StringArgumentType.getString(c,"sha256"));return 1;}
            catch(Exception|LinkageError error){report.put("error",error.toString());report.put("failures",1);finish("native tree admission refused; no automatic retry");throw new IllegalStateException("Native tree request refused",error);}
        }))));
        command.then(Commands.literal("status").executes(c->{c.getSource().sendSuccess(()->Component.literal(JSON.toJson(report)),false);return 1;}));
        command.then(Commands.literal("cancel").executes(c->{if(phase==Phase.CLEANUP)cleanup(true);else finish("cancelled; native records and any quarantine retained");return 1;}));event.getDispatcher().register(command);
    }
    private static String sha(byte[] raw)throws Exception{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(raw));}
    private static byte[] bounded(Path file,int cap)throws Exception{if(!Files.isRegularFile(file,LinkOption.NOFOLLOW_LINKS)||Files.size(file)<1||Files.size(file)>cap)throw new IllegalStateException("Bounded ordinary tree evidence required");try(InputStream in=Files.newInputStream(file)){byte[] raw=in.readNBytes(cap+1);if(raw.length>cap)throw new IllegalStateException("Tree evidence grew");return raw;}}
    private Path owned(String text)throws Exception{Path relative=Path.of(text);if(relative.isAbsolute()||text.indexOf(':')>=0||text.indexOf('\\')>=0)throw new IllegalStateException("Owned relative tree evidence required");for(Path part:relative)if(part.toString().equals(".")||part.toString().equals(".."))throw new IllegalStateException("No traversal");Path file=home.resolve(relative).normalize();for(Path p=file;p!=null&&!p.equals(home);p=p.getParent())if(Files.isSymbolicLink(p)||!p.toRealPath().equals(p.toAbsolutePath().normalize()))throw new IllegalStateException("Linked tree evidence refused");if(!file.toRealPath().startsWith(home.toRealPath()))throw new IllegalStateException("Tree evidence escaped home");return file;}
    private JsonObject read(JsonObject ref,int cap)throws Exception{byte[] raw=bounded(owned(ref.get("path").getAsString()),cap);if(raw.length!=ref.get("bytes").getAsInt()||!sha(raw).equals(ref.get("sha256").getAsString()))throw new IllegalStateException("Exact tree input bytes/hash differ");return JsonParser.parseString(new String(raw,StandardCharsets.UTF_8)).getAsJsonObject();}
    private JsonObject ref(String key){return request.getAsJsonObject(key);}
    private void checkpoint()throws Exception{if(!owned(ref("current_backup").get("path").getAsString()).equals(journal.resolve("backup-receipt.json")))throw new IllegalStateException("Canonical current checkpoint required");JsonObject value=read(ref("current_backup"),4096);if(!value.get("verified").getAsBoolean()||!value.get("sha256").getAsString().equals(request.get("checkpoint_sha256").getAsString()))throw new IllegalStateException("Tree checkpoint changed");}
    private static void resource(Class<?> context,String name,String expected)throws Exception{try(InputStream in=context.getResourceAsStream(name)){if(in==null)throw new IllegalStateException("Native tree class resource absent");byte[] raw=in.readNBytes(256*1024+1);if(raw.length>256*1024||!sha(raw).equals(expected))throw new IllegalStateException("Native tree/guard class resource differs");}}
    private void begin(MinecraftServer server,String mode,String bundle,String expected)throws Exception{
        if(busy()||lease!=null||!tickets.isEmpty()||!server.isSameThread()||!bundle.matches("trees-[a-f0-9]{16}")||!expected.matches("[a-f0-9]{64}")||!bundle.endsWith(expected.substring(0,16)))throw new IllegalStateException("Busy/off-thread/invalid tree request");
        report.clear();descriptors.clear();saplings.clear();before.clear();protectedColumns.clear();chunks.clear();pending.clear();outcome=null;terminalPublished=mutated=false;worldResidual=quarantineLatched||Files.exists(journal.resolve("tree-growth-quarantine.json"));ticks=cursor=rolls=successRolls=performCalls=0;
        report.put("operation",mode);report.put("started",Instant.now().toString());report.put("request_sha256",expected);report.put("failures",0);
        if(server.getPort()!=25575||!server.getPlayerList().getPlayers().isEmpty()||!server.getServerVersion().equals("1.21.1"))throw new IllegalStateException("Owned empty private 1.21.1 server only");
        Path privateRoot=Path.of("D:/A World for Two/staging/world-tests").toRealPath();
        if(!home.getParent().toRealPath().equals(privateRoot)||!home.toRealPath().startsWith(privateRoot)
            ||!server.getWorldPath(LevelResource.ROOT).toRealPath().equals(home.resolve("world/RosewaterArtistic").toRealPath()))
            throw new IllegalStateException("Native tree admission is restricted to the owned private RosewaterArtistic staging world");
        byte[] bytes=bounded(owned("dashboard/settlement/"+bundle+"/request.json"),128*1024);if(!sha(bytes).equals(expected))throw new IllegalStateException("Tree request hash differs");request=JsonParser.parseString(new String(bytes,StandardCharsets.UTF_8)).getAsJsonObject();
        if(!request.get("format").getAsString().equals("awft-native-trees:1")||!mode.equals(request.get("allowed_operation").getAsString())||!candidate.equals(request.get("candidate_version").getAsString())||!bridge.equals(request.get("bridge_version").getAsString())
            ||!ModList.get().getModContainerById("awft_control_bridge").orElseThrow().getModInfo().getVersion().toString().equals(bridge)||!ModList.get().getModContainerById("regions_unexplored").orElseThrow().getModInfo().getVersion().toString().equals("0.6.3"))throw new IllegalStateException("Actual tree runtime versions differ");
        resource(NativeTreeGrowthSupport.class,"NativeTreeGrowthSupport.class",request.get("native_class_sha256").getAsString());resource(TreeGrowthScope.class,"TreeGrowthScope.class",request.get("native_scope_sha256").getAsString());
        JsonObject owner=JsonParser.parseString(new String(bounded(owned("dashboard/artistic-owner.json"),65536),StandardCharsets.UTF_8)).getAsJsonObject(),active=JsonParser.parseString(new String(bounded(owned("packwiz/active.json"),65536),StandardCharsets.UTF_8)).getAsJsonObject(),installed=JsonParser.parseString(new String(bounded(owned("server/installed.json"),1024*1024),StandardCharsets.UTF_8)).getAsJsonObject();
        if(!owner.get("format").getAsString().equals("awft-artistic-stage:1")||!Path.of(owner.get("home").getAsString()).toRealPath().equals(home.toRealPath())||!active.get("version").getAsString().equals(candidate)||!installed.get("pack_version").getAsString().equals(candidate)||!active.get("pack_sha256").equals(installed.get("pack_sha256"))||!active.get("pack_sha256").equals(request.get("pack_sha256")))throw new IllegalStateException("Actual owned tree pack custody differs");
        checkpoint();plan=read(ref("plan"),MAX_INPUT);planSha=ref("plan").get("sha256").getAsString();level=server.overworld();
        if(!plan.get("format").getAsString().equals("awft-native-tree-plan:1")||!plan.get("seed").getAsString().equals(Long.toString(level.getSeed()))||!Path.of(plan.get("world_path").getAsString()).toRealPath().equals(server.getWorldPath(LevelResource.ROOT).toRealPath()))throw new IllegalStateException("Actual tree world identity differs");
        for(JsonElement element:plan.getAsJsonArray("saplings")){String id=element.getAsString();if(!SAPLINGS.contains(id)||saplings.contains(id)||saplings.size()>=9)throw new IllegalStateException("Only the reviewed finite native sapling list is available");Block block=BuiltInRegistries.BLOCK.get(ResourceLocation.parse(id));if(!(block instanceof SaplingBlock)||!(block instanceof BonemealableBlock))throw new IllegalStateException("Actual selected sapling class is unsupported; never approximate it");saplings.add(id);}
        if(saplings.isEmpty())throw new IllegalStateException("At least one actual sapling required");action=mode;
        if(mode.equals("grow")){
            if(quarantineLatched||Files.exists(journal.resolve("tree-growth-quarantine.json")))throw new IllegalStateException("A previous plot needs exact parent-reviewed recovery; other construction is unaffected");
            resource(NativeTreeGrowthSupport.class,"mixin/NativeTreeGrowthGuardMixin.class",request.get("native_guard_sha256").getAsString());
            JsonObject ready=read(ref("construction_ready"),128*1024);for(String key:List.of("construction_complete","functional_commissioning_complete","visual_corrections_reviewed"))if(!ready.get(key).getAsBoolean())throw new IllegalStateException("Native planting is after completed construction/function/art");
            if(!ready.get("checkpoint_sha256").getAsString().equals(request.get("checkpoint_sha256").getAsString())||!ready.get("tree_plan_sha256").getAsString().equals(planSha))throw new IllegalStateException("Construction review is not bound to this exact tree plot");
            qualification=read(ref("qualification"),128*1024);if(!qualification.get("all_reachable_features_reviewed").getAsBoolean()||!qualification.get("derivation_sha256").getAsString().matches("[a-f0-9]{64}"))throw new IllegalStateException("Every primary/rare native variant needs a reviewed envelope derivation");
            if(saplings.size()!=1)throw new IllegalStateException("Exactly one native plot per growth transaction");
            JsonArray p=plan.getAsJsonArray("root");root=new BlockPos(p.get(0).getAsInt(),p.get(1).getAsInt(),p.get(2).getAsInt());sapling=BuiltInRegistries.BLOCK.get(ResourceLocation.parse(saplings.getFirst())).defaultBlockState();
            int[] write=box(plan.getAsJsonArray("write_bounds"));knownBounds=box(plan.getAsJsonArray("known_bounds"));writeBounds=new AABB(write[0],write[1],write[2],write[3]+1,write[4]+1,write[5]+1);
            if(volume(knownBounds)>MAX_CELLS||volume(write)>MAX_CELLS||!inside(write,root)||root.getY()<48||root.getY()>256||knownBounds[0]>write[0]-8||knownBounds[2]>write[2]-8||knownBounds[3]<write[3]+8||knownBounds[5]<write[5]+8||knownBounds[1]>write[1]-2||knownBounds[4]<write[4]+4)throw new IllegalStateException("Complete bounded known envelope and eight-block physics/read perimeter required");
            JsonObject mask=read(ref("protection"),MAX_INPUT);if(!mask.get("seed").getAsString().equals(plan.get("seed").getAsString())||!mask.get("world_path").getAsString().equals(plan.get("world_path").getAsString())||mask.get("minimum_buffer_blocks").getAsInt()<5||!mask.get("includes_latest_plaza_routes_and_walks").getAsBoolean())throw new IllegalStateException("Complete current authored/AIR/plaza/walk protection required");
            for(JsonElement value:mask.getAsJsonArray("columns")){JsonArray col=value.getAsJsonArray();if(protectedColumns.size()>200000)throw new IllegalStateException("Protection index exceeds finite scope");protectedColumns.add(TreeGrowthScope.column(col.get(0).getAsInt(),col.get(1).getAsInt()));}
            for(int x=write[0];x<=write[3];x++)for(int z=write[2];z<=write[5];z++)if(protectedColumns.contains(TreeGrowthScope.column(x,z)))throw new IllegalStateException("Whole native growth envelope conflicts with architecture, route, water channel or view protection");
            JsonObject field=read(ref("before"),MAX_INPUT);if(!field.get("seed").getAsString().equals(plan.get("seed").getAsString())||!field.get("world_path").getAsString().equals(plan.get("world_path").getAsString())||!field.get("backup_sha256").getAsString().equals(request.get("checkpoint_sha256").getAsString())||!field.getAsJsonArray("commands").isEmpty()||!field.getAsJsonArray("block_entities").isEmpty())throw new IllegalStateException("Literal current no-BE before-plan required");
            JsonArray palette=field.getAsJsonArray("palette"),rows=field.getAsJsonArray("blocks");if(rows.size()!=volume(knownBounds)||rows.size()>MAX_CELLS)throw new IllegalStateException("Every bounded known cell must be present");
            for(JsonElement value:rows){JsonArray row=value.getAsJsonArray();BlockPos pos=new BlockPos(row.get(0).getAsInt(),row.get(1).getAsInt(),row.get(2).getAsInt());if(!inside(knownBounds,pos)||before.put(pos,parse(palette.get(row.get(3).getAsInt()).getAsString()))!=null)throw new IllegalStateException("Missing/duplicate/foreign native plot preimage");}
            cells=List.copyOf(before.entrySet());for(int x=knownBounds[0]>>4;x<=knownBounds[3]>>4;x++)for(int z=knownBounds[2]>>4;z<=knownBounds[5]>>4;z++)chunks.add(new ChunkPos(x,z));if(chunks.size()>32)throw new IllegalStateException("Native plot exceeds temporary chunk budget");
        }
        modPath=owned("server/mods/"+RU_FILE);if(!ModList.get().getModFileById("regions_unexplored").getFile().getFilePath().toRealPath().equals(modPath.toRealPath()))throw new IllegalStateException("Actual loaded RU source path differs");hashAttrs=Files.readAttributes(modPath,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);if(hashAttrs.size()>16*1024*1024)throw new IllegalStateException("Bounded pinned native tree artifact required");hashStream=Files.newInputStream(modPath);hashDigest=MessageDigest.getInstance("SHA-256");hashBytes=0;
        lease=interlock.acquire("native-trees:"+expected,false);if(lease==null||!lease.valid())throw new IllegalStateException("Shared exclusive maintenance lease required");phase=Phase.HASH;report.put("candidate",candidate);report.put("bridge",bridge);report.put("plan_sha256",planSha);
    }
    private static int[] box(JsonArray a){if(a.size()!=6)throw new IllegalStateException("Six integer envelope coordinates required");int[] b=new int[6];for(int i=0;i<6;i++)b[i]=a.get(i).getAsInt();if(b[0]>b[3]||b[1]>b[4]||b[2]>b[5]||Math.abs((long)b[0])>30000000||Math.abs((long)b[3])>30000000||Math.abs((long)b[2])>30000000||Math.abs((long)b[5])>30000000||b[1]< -64||b[4]>319)throw new IllegalStateException("Finite native world envelope required");return b;}
    private static boolean inside(int[] b,BlockPos p){return p.getX()>=b[0]&&p.getX()<=b[3]&&p.getY()>=b[1]&&p.getY()<=b[4]&&p.getZ()>=b[2]&&p.getZ()<=b[5];}
    private static long volume(int[] b){return ((long)b[3]-b[0]+1)*(b[4]-b[1]+1)*((long)b[5]-b[2]+1);}
    @SuppressWarnings({"unchecked","rawtypes"}) private static BlockState parse(String text){if(!text.matches("[a-z0-9_.-]+:[a-z0-9_./-]+(?:\\[[a-z0-9_=,]+\\])?"))throw new IllegalStateException("Invalid native block state");String[] parts=text.split("\\[",2);ResourceLocation id=ResourceLocation.parse(parts[0]);if(!BuiltInRegistries.BLOCK.containsKey(id))throw new IllegalStateException("Unknown native block");BlockState state=BuiltInRegistries.BLOCK.get(id).defaultBlockState();Set<String> keys=new HashSet<>();if(parts.length==2)for(String item:parts[1].substring(0,parts[1].length()-1).split(",")){String[] pair=item.split("=",2);if(pair.length!=2||!keys.add(pair[0]))throw new IllegalStateException("Invalid property");Property property=state.getBlock().getStateDefinition().getProperty(pair[0]);if(property==null)throw new IllegalStateException("Unknown property");state=state.setValue(property,(Comparable)property.getValue(pair[1]).orElseThrow());}if(keys.size()!=state.getProperties().size())throw new IllegalStateException("Complete native preimage properties required");return state;}
    private static JsonElement sorted(JsonElement value){if(value.isJsonObject()){JsonObject result=new JsonObject();TreeSet<String> keys=new TreeSet<>(value.getAsJsonObject().keySet());for(String key:keys)result.add(key,sorted(value.getAsJsonObject().get(key)));return result;}if(value.isJsonArray()){JsonArray result=new JsonArray();for(JsonElement v:value.getAsJsonArray())result.add(sorted(v));return result;}return value;}
    private JsonObject describe(String id)throws Throwable{
        SaplingBlock block=(SaplingBlock)BuiltInRegistries.BLOCK.get(ResourceLocation.parse(id));TreeGrower grower=(TreeGrower)MethodHandles.privateLookupIn(SaplingBlock.class,MethodHandles.lookup()).findGetter(SaplingBlock.class,"treeGrower",TreeGrower.class).invoke(block);
        var lookup=MethodHandles.privateLookupIn(TreeGrower.class,MethodHandles.lookup());JsonObject value=new JsonObject(),roles=new JsonObject(),features=new JsonObject();value.addProperty("sapling",id);value.addProperty("actual_block_class",block.getClass().getName());value.addProperty("grower_name",(String)lookup.findGetter(TreeGrower.class,"name",String.class).invoke(grower));value.addProperty("secondary_chance",(float)lookup.findGetter(TreeGrower.class,"secondaryChance",float.class).invoke(grower));
        Registry<ConfiguredFeature<?,?>> registry=level.registryAccess().registryOrThrow(Registries.CONFIGURED_FEATURE);
        for(String role:List.of("megaTree","secondaryMegaTree","tree","secondaryTree","flowers","secondaryFlowers")){Optional<?> option=(Optional<?>)lookup.findGetter(TreeGrower.class,role,Optional.class).invoke(grower);if(option.isEmpty())continue;ResourceKey<?> key=(ResourceKey<?>)option.get();String name=key.location().toString();roles.addProperty(role,name);ConfiguredFeature<?,?> feature=registry.get(key.location());if(feature==null)throw new IllegalStateException("Actual configured feature absent: "+name);JsonElement encoded=ConfiguredFeature.DIRECT_CODEC.encodeStart(level.registryAccess().createSerializationContext(JsonOps.INSTANCE),feature).result().orElseThrow(()->new IllegalStateException("Actual native feature codec refused"));JsonObject row=new JsonObject();JsonElement canonical=sorted(encoded);byte[] raw=JSON.toJson(canonical).getBytes(StandardCharsets.UTF_8);if(raw.length>128*1024)throw new IllegalStateException("Native feature descriptor exceeds bound");row.add("actual_codec",canonical);row.addProperty("codec_sha256",sha(raw));row.addProperty("native_feature_class",feature.feature().getClass().getName());features.add(name,row);}
        value.add("roles",roles);value.add("features",features);value.addProperty("native_ru_sha256",RU_SHA);return (JsonObject)sorted(value);
    }
    private void ticket(ChunkPos c,boolean add)throws Exception{level.getChunkSource().getClass().getMethod(add?"addRegionTicket":"removeRegionTicket",TicketType.class,ChunkPos.class,int.class,Object.class,boolean.class).invoke(level.getChunkSource(),TICKET,c,2,c,true);}
    private boolean ready(){for(ChunkPos c:chunks)if(level.getChunkSource().getChunkNow(c.x,c.z)==null)return false;return true;}
    private void gate(MinecraftServer server)throws Exception{if(!server.isSameThread()||lease==null||!lease.valid()||!server.getPlayerList().getPlayers().isEmpty())throw new IllegalStateException("Native tree lease/thread/player changed");checkpoint();BasicFileAttributes now=Files.readAttributes(modPath,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);if(now.size()!=hashAttrs.size()||!now.lastModifiedTime().equals(hashAttrs.lastModifiedTime())||!Objects.equals(now.fileKey(),hashAttrs.fileKey()))throw new IllegalStateException("Pinned native tree artifact changed");}
    private Map<BlockPos,BlockState> snapshot(){Map<BlockPos,BlockState> result=new LinkedHashMap<>();for(BlockPos pos:before.keySet())result.put(pos,level.getBlockState(pos));return result;}
    private Map<BlockPos,String> nativeBEs(){Map<BlockPos,String> result=new LinkedHashMap<>();for(BlockPos pos:before.keySet()){BlockEntity be=level.getBlockEntity(pos);if(be==null)continue;String text=be.saveWithFullMetadata(level.registryAccess()).toString();if(text.length()>65536||result.size()>=256)throw new IllegalStateException("Native BE journal exceeds finite bounds");result.put(pos,text);}return result;}
    private static JsonArray beRows(Map<BlockPos,String> field){JsonArray rows=new JsonArray();for(var entry:field.entrySet()){JsonObject row=new JsonObject();row.add("pos",JSON.toJsonTree(List.of(entry.getKey().getX(),entry.getKey().getY(),entry.getKey().getZ())));row.addProperty("actual_native_nbt",entry.getValue());rows.add(row);}return rows;}
    private JsonObject field(Map<BlockPos,BlockState> blocks){TreeSet<String> states=new TreeSet<>();Map<BlockPos,String> texts=new LinkedHashMap<>();for(var row:blocks.entrySet()){String text=stateText(row.getValue());texts.put(row.getKey(),text);states.add(text);}List<String> palette=new ArrayList<>(states);Map<String,Integer> index=new HashMap<>();for(int i=0;i<palette.size();i++)index.put(palette.get(i),i);JsonArray rows=new JsonArray();for(var row:texts.entrySet()){JsonArray cell=new JsonArray();cell.add(row.getKey().getX());cell.add(row.getKey().getY());cell.add(row.getKey().getZ());cell.add(index.get(row.getValue()));rows.add(cell);}JsonObject value=new JsonObject();value.add("palette",JSON.toJsonTree(palette));value.add("blocks",rows);return value;}
    @SuppressWarnings({"rawtypes","unchecked"}) private static String stateText(BlockState state){TreeMap<String,String> properties=new TreeMap<>();for(Property p:state.getProperties())properties.put(p.getName(),p.getName((Comparable)state.getValue(p)));StringJoiner values=new StringJoiner(",");properties.forEach((k,v)->values.add(k+"="+v));return BuiltInRegistries.BLOCK.getKey(state.getBlock())+(properties.isEmpty()?"":"["+values+"]");}
    private void archive(Map<BlockPos,BlockState> after,String kind,Map<BlockPos,BlockState> restored,Map<BlockPos,String> beBefore,Map<BlockPos,String> beAfter,Map<BlockPos,String> beRestored)throws Exception{JsonObject value=new JsonObject();value.addProperty("format","awft-native-tree-outcome:1");value.addProperty("kind",kind);value.addProperty("construction_forbidden",true);value.addProperty("entity_nbt_replay_forbidden",true);value.addProperty("source_plan_sha256",planSha);value.add("before",field(before));if(after!=null)value.add("native_after",field(after));else value.addProperty("native_after_capture_unavailable",true);value.add("native_be_before",beRows(beBefore));if(beAfter!=null)value.add("native_be_after",beRows(beAfter));else value.addProperty("native_be_after_capture_unavailable",true);if(restored!=null)value.add("after_failed_attempt_restoration",field(restored));if(beRestored!=null)value.add("native_be_after_restoration",beRows(beRestored));value.add("native_descriptors",JSON.toJsonTree(descriptors));byte[] raw=JSON.toJson(value).getBytes(StandardCharsets.UTF_8);if(raw.length>16*1024*1024)throw new IllegalStateException("Native outcome archive exceeds bound");Files.createDirectories(journal);Path file=journal.resolve("tree-outcome-"+UUID.randomUUID()+".json");Files.write(file,raw,StandardOpenOption.CREATE_NEW);Files.writeString(file.resolveSibling(file.getFileName()+".complete"),sha(raw),StandardOpenOption.CREATE_NEW);report.put("outcome_archive",file.getFileName().toString());report.put("outcome_archive_sha256",sha(raw));}
    private void quarantine(Throwable failure){
        worldResidual=true;quarantineLatched=true;
        try{report.put("world_recovery_required",true);Files.createDirectories(journal);Path marker=journal.resolve("tree-growth-quarantine.json");
            if(!Files.exists(marker))Files.writeString(marker,JSON.toJson(Map.of("plan_sha256",planSha,"error",failure.toString(),"created",Instant.now().toString())),StandardOpenOption.CREATE_NEW);
        }catch(Throwable journalFailure){report.put("quarantine_write_error",journalFailure.toString());System.err.println("AWFT tree quarantine could not be persisted: "+journalFailure);}
    }
    private static final class FailedFields {
        Map<BlockPos,BlockState> actualAfter,restored;
        Map<BlockPos,String> beAfter,beRestored;
    }
    private void recoverGrowth(TreeGrowthScope scope,Throwable failure,Map<BlockPos,String> beBefore){
        // Latch before capture/allocation. Broken failure evidence can NEVER bypass restoration.
        worldResidual=true;FailedFields evidence=new FailedFields();
        var recovery=TreeGrowthScope.captureThenRestore(
            ()->{evidence.actualAfter=snapshot();evidence.beAfter=nativeBEs();},
            ()->{int restored=scope.restoreFailedAttempt();evidence.restored=snapshot();evidence.beRestored=nativeBEs();
                for(var row:before.entrySet())if(!row.getValue().equals(evidence.restored.get(row.getKey())))throw new IllegalStateException("Untracked native residual requires review");
                if(!beBefore.equals(evidence.beRestored))throw new IllegalStateException("Native BE restoration requires review; no replay of inventories");
                report.put("restored_owned_cells",restored);
            });
        report.put("growth_error",failure.toString());
        if(recovery.captureFailure()!=null)report.put("failed_state_capture_error",recovery.captureFailure().toString());
        if(recovery.exactRestored()){mutated=false;worldResidual=false;}
        else{quarantine(recovery.restoreFailure());report.put("restoration_error",recovery.restoreFailure().toString());}
        try{archive(evidence.actualAfter,recovery.exactRestored()?"FAILED_NATIVE_ATTEMPT_RESTORED_NOT_ACCEPTED":"FAILED_NATIVE_ATTEMPT_RESIDUAL_REQUIRES_EXACT_REVIEW",
            evidence.restored,beBefore,evidence.beAfter,evidence.beRestored);
        }catch(Throwable archiveFailure){report.put("failed_outcome_archive_error",archiveFailure.toString());}
    }
    private void grow()throws Exception{
        JsonObject descriptor=descriptors.get(saplings.getFirst());String actual=sha(JSON.toJson(sorted(descriptor)).getBytes(StandardCharsets.UTF_8));
        if(!actual.equals(qualification.get("native_descriptor_sha256").getAsString()))throw new IllegalStateException("Actual runtime grower/features differ from reviewed full descriptor");
        if(!sapling.canSurvive(level,root))throw new IllegalStateException("Native sapling cannot survive on the actual soil");
        if(!level.getEntities(null,writeBounds.inflate(1)).isEmpty())throw new IllegalStateException("Preserve actual residents, passengers and objects near native growth; choose an unoccupied plot");
        Map<BlockPos,String> beBefore=nativeBEs();TreeGrowthScope scope=new TreeGrowthScope(level,before,writeBounds,protectedColumns,root.getY()-1);
        try{
            scope.hookWitness(root);
            // Set before invocation: a native setter may throw after a partial physical write.
            mutated=true;if(!level.setBlock(root,sapling,3))throw new IllegalStateException("Native sapling placement refused");
            for(int n=0;n<MAX_ATTEMPTS;n++){
                BlockState current=level.getBlockState(root);if(current.getBlock()!=sapling.getBlock())break;
                BonemealableBlock target=(BonemealableBlock)current.getBlock();if(!target.isValidBonemealTarget(level,root,current))throw new IllegalStateException("Native bonemeal target refused");
                rolls++;if(!target.isBonemealSuccess(level,level.random,root,current))continue;successRolls++;
                int stage=current.getValue(SaplingBlock.STAGE);target.performBonemeal(level,level.random,root,current);performCalls++;
                if(scope.violation!=null)throw new IllegalStateException(scope.violation);
                BlockState next=level.getBlockState(root);if(stage==1&&next.getBlock()==sapling.getBlock())throw new IllegalStateException("Native feature did not grow; do not select another variant by repeated forcing");
            }
            if(scope.violation!=null)throw new IllegalStateException(scope.violation);
            Map<BlockPos,BlockState> after=snapshot();long logs=0,leaves=0;
            for(var row:after.entrySet())if(!row.getValue().equals(before.get(row.getKey()))){
                if(!scope.attempted.contains(row.getKey()))throw new IllegalStateException("Native change bypassed the scoped setter; quarantine rather than invent success");
                if(row.getValue().is(BlockTags.LOGS))logs++;if(row.getValue().getBlock() instanceof LeavesBlock)leaves++;
            }
            if(!level.getBlockState(root).is(BlockTags.LOGS)||logs<3||leaves<8)throw new IllegalStateException("No complete native trunk/canopy observed within bounded attempts");
            Map<BlockPos,String> beAfter=nativeBEs();for(var row:beBefore.entrySet())if(!Objects.equals(row.getValue(),beAfter.get(row.getKey())))throw new IllegalStateException("A preexisting native BE changed during growth; no inventory rewrite is permitted");
            report.put("native_changed_log_blocks",logs);report.put("native_changed_leaf_blocks",leaves);report.put("guarded_write_calls",scope.writes);report.put("guard_read_calls",scope.reads);
            archive(after,"NATIVE_GROWN_OUTCOME_NOT_VISUAL_ACCEPTANCE",null,beBefore,beAfter,null);
        }catch(Throwable failure){
            if(mutated){worldResidual=true;try{recoverGrowth(scope,failure,beBefore);}catch(Throwable recoveryFailure){quarantine(recoveryFailure);}}
            throw new IllegalStateException("Native growth failed; exact restoration or quarantine recorded",failure);
        }finally{
            try{scope.close();}catch(Throwable closeFailure){quarantine(closeFailure);throw new IllegalStateException("Native growth scope did not close cleanly; further planting blocked",closeFailure);}
        }
    }
    public void tick(MinecraftServer server){
        if(phase==Phase.IDLE)return;if(phase==Phase.CLEANUP){pending.removeIf(CompletableFuture::isDone);if(tickets.isEmpty()&&pending.isEmpty())cleanup(false);return;}long start=System.nanoTime();
        try{
            if(++ticks>MAX_TICKS||!server.isSameThread()||lease==null||!lease.valid()||!server.getPlayerList().getPlayers().isEmpty())throw new IllegalStateException("Native tree bounded ownership guard refused");
            if(phase==Phase.HASH){int n;do{n=hashStream.read(buffer);if(n>0){hashDigest.update(buffer,0,n);hashBytes+=n;}}while(n>=0&&System.nanoTime()-start<3_000_000L);if(n>=0)return;hashStream.close();hashStream=null;if(hashBytes!=hashAttrs.size()||!HexFormat.of().formatHex(hashDigest.digest()).equals(RU_SHA))throw new IllegalStateException("Pinned RU bytes differ");phase=Phase.DESCRIBE;}
            gate(server);
            if(phase==Phase.DESCRIBE){String id=saplings.get(cursor++);JsonObject value;try{value=describe(id);}catch(Throwable failure){throw new IllegalStateException("Actual native tree descriptor failed",failure);}descriptors.put(id,value);if(cursor<saplings.size())return;cursor=0;Map<String,String> hashes=new TreeMap<>();for(var entry:descriptors.entrySet())hashes.put(entry.getKey(),sha(JSON.toJson(sorted(entry.getValue())).getBytes(StandardCharsets.UTF_8)));report.put("native_descriptors",descriptors);report.put("native_descriptor_sha256s",hashes);if(action.equals("describe")){finish("actual native sapling/grower/feature descriptors captured; no world changes");return;}phase=Phase.LOAD;for(ChunkPos c:chunks){tickets.add(c);ticket(c,true);pending.add(((worldfortwo.bridge.mixin.ChunkCacheAccess)(Object)level.getChunkSource()).awftQueueChunk(c.x,c.z,ChunkStatus.FULL,false));}return;}
            if(phase==Phase.LOAD){if(pending.stream().anyMatch(f->!f.isDone()))return;for(var future:pending)future.join();pending.clear();if(!ready())return;phase=Phase.VERIFY;}
            if(!ready())throw new IllegalStateException("Native known plot unloaded");
            if(phase==Phase.VERIFY){int work=0;while(cursor<cells.size()&&work++<256&&System.nanoTime()-start<4_000_000L){var row=cells.get(cursor++);if(!row.getValue().equals(level.getBlockState(row.getKey())))throw new IllegalStateException("Actual complete plot preimage differs at "+row.getKey());if(writeBounds.contains(row.getKey().getX()+.5,row.getKey().getY()+.5,row.getKey().getZ()+.5)&&level.getBlockEntity(row.getKey())!=null)throw new IllegalStateException("Existing native BE inside growth plot");}if(cursor<cells.size())return;phase=Phase.GROW;}
            if(phase==Phase.GROW){grow();finish("native sapling grown through ordinary APIs; silhouette/visual and ecological acceptance pending");}
        }catch(Exception|LinkageError error){report.put("error",error.toString());report.put("failures",1);finish("native tree attempt refused/failed; original receipts retained, no retry or manual tree substitute");}
        report.put("last_work_ms",(System.nanoTime()-start)/1_000_000.0);
    }
    private void finish(String text){if(outcome==null)outcome=text;phase=Phase.CLEANUP;cleanup(true);}
    private void cleanup(boolean retry){List<String> errors=new ArrayList<>();if(hashStream!=null)try{hashStream.close();hashStream=null;}catch(Exception e){errors.add(e.toString());}if(retry&&level!=null)for(ChunkPos c:List.copyOf(tickets))try{ticket(c,false);tickets.remove(c);}catch(Exception|LinkageError e){errors.add(c+": "+e);}pending.removeIf(CompletableFuture::isDone);if(tickets.isEmpty()&&pending.isEmpty()&&hashStream==null&&lease!=null)try{lease.close();lease=null;}catch(Exception e){errors.add(e.toString());}boolean clean=tickets.isEmpty()&&pending.isEmpty()&&hashStream==null&&lease==null;report.put("status",outcome);report.put("cleanup_resources_passed",clean);report.put("world_recovery_required",worldResidual);report.put("cleanup_passed",clean&&!worldResidual);report.put("temporary_tickets_remaining",tickets.size());report.put("pending_shared_futures",pending.size());report.put("cleanup_errors",errors);report.put("native_bonemeal_trials",rolls);report.put("native_success_rolls",successRolls);report.put("perform_bonemeal_calls",performCalls);report.put("invented_or_claimed_consumed_bonemeal_items",0);report.put("global_wakes",0);report.put("world_mutated_after_restoration",mutated);report.put("native_visual_acceptance",false);report.put("finished",Instant.now().toString());try{if(clean||!terminalPublished){NativeJournal.progress(journal,"tree-growth-status.json",report);NativeJournal.terminal(journal,"tree-growth",report);terminalPublished=true;}}catch(Exception e){System.err.println("AWFT native tree journal: "+e);}if(clean)phase=Phase.IDLE;}
    public void stopped(){if(busy())finish("server stopping; actual tree records and any quarantine preserved");}
}
