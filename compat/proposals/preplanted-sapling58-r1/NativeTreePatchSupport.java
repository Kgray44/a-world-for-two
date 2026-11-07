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
public final class NativeTreePatchSupport {
    private enum Phase { IDLE,HASH,DESCRIBE,READ_SAVED,LOAD,CAPTURE,GROW,NEXT,CLEANUP }
    private static final Gson JSON=new Gson();
    private static final String RU_FILE="regions-unexplored-0.6.3-neoforge-21.1.jar",RU_SHA="e7f2edd7bab869c2e566b1b251ea54c6b95834205276bf3a302859d72d9d0c9b";
    private static final Set<String> SAPLINGS=Set.of("minecraft:birch_sapling","regions_unexplored:magnolia_sapling","regions_unexplored:white_magnolia_sapling","regions_unexplored:pink_magnolia_sapling","regions_unexplored:maple_sapling","regions_unexplored:silver_birch_sapling","regions_unexplored:pine_sapling","regions_unexplored:larch_sapling","regions_unexplored:golden_larch_sapling");
    private static final TicketType<ChunkPos> TICKET=TicketType.create("awft_native_tree_patch",Comparator.comparingLong(ChunkPos::toLong));
    private static final int MAX_INPUT=16*1024*1024,MAX_CELLS=131072,MAX_TICKS=7200,MAX_ATTEMPTS=12;
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
    private final List<JsonObject> patchRoots=new ArrayList<>();
    private final List<Map<String,Object>> rootOutcomes=new ArrayList<>();
    private final Set<String> patchIds=new HashSet<>();
    private final Set<BlockPos> heldRoots=new HashSet<>(),approvedFoliage=new HashSet<>();
    private final Set<String> leafIds=new HashSet<>();
    private boolean naturalCanopyReviewed,naturalCanopyRoot,ownedPreplantedReviewed,ownedPreplantedRoot;
    private Set<BlockState> ownedPreplantedOutputs=Set.of();
    private Set<BlockState> naturalTreeOutputs=Set.of();
    private final Set<Long> eligibleColumns=new HashSet<>();
    private int rootIndex,captureCursor;
    private String rootId,currentSaplingId,requestSha,capturedSha,capturedName;
    private JsonObject rootPlan;
    private Path rootIntent;
    private boolean anyMutated;
    private long archiveBytes;
    private NativeTreePatchReadiness savedReadiness;
    private static final int MAX_ROOTS=32;
    private static final long MAX_ARCHIVE_BYTES=576L*1024*1024;

    private int[] knownBounds;
    public NativeTreePatchSupport(String candidate,String bridge,ArtisticEngineeringSupport.Interlock interlock){this.candidate=Objects.requireNonNull(candidate);this.bridge=Objects.requireNonNull(bridge);this.interlock=Objects.requireNonNull(interlock);}
    public boolean busy(){return phase!=Phase.IDLE;}
    public void commands(RegisterCommandsEvent event){
        var command=Commands.literal("awfttreepatch").requires(s->s.getEntity()==null&&s.hasPermission(4));
        for(String mode:List.of("inspect","grow"))command.then(Commands.literal(mode).then(Commands.argument("bundle",StringArgumentType.word()).then(Commands.argument("sha256",StringArgumentType.word()).executes(c->{
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
        if(busy()||lease!=null||!tickets.isEmpty()||!server.isSameThread()||!bundle.matches("treepatch-[a-f0-9]{16}")||!expected.matches("[a-f0-9]{64}")||!bundle.endsWith(expected.substring(0,16)))throw new IllegalStateException("Busy/off-thread/invalid tree request");
        patchRoots.clear();rootOutcomes.clear();patchIds.clear();heldRoots.clear();eligibleColumns.clear();approvedFoliage.clear();leafIds.clear();rootIndex=0;archiveBytes=0;anyMutated=false;requestSha=expected;savedReadiness=null;
        report.clear();descriptors.clear();saplings.clear();before.clear();protectedColumns.clear();chunks.clear();pending.clear();outcome=null;terminalPublished=mutated=false;worldResidual=quarantineLatched||Files.exists(journal.resolve("tree-growth-quarantine.json"));ticks=cursor=rolls=successRolls=performCalls=0;
        report.put("operation",mode);report.put("started",Instant.now().toString());report.put("request_sha256",expected);report.put("failures",0);
        if(server.getPort()!=25575||!server.getPlayerList().getPlayers().isEmpty()||!server.getServerVersion().equals("1.21.1"))throw new IllegalStateException("Owned empty private 1.21.1 server only");
        Path privateRoot=Path.of("D:/A World for Two/staging/world-tests").toRealPath();
        if(!home.getParent().toRealPath().equals(privateRoot)||!home.toRealPath().startsWith(privateRoot)
            ||!server.getWorldPath(LevelResource.ROOT).toRealPath().equals(home.resolve("world/RosewaterArtistic").toRealPath()))
            throw new IllegalStateException("Native tree admission is restricted to the owned private RosewaterArtistic staging world");
        byte[] bytes=bounded(owned("dashboard/settlement/"+bundle+"/request.json"),128*1024);if(!sha(bytes).equals(expected))throw new IllegalStateException("Tree request hash differs");request=JsonParser.parseString(new String(bytes,StandardCharsets.UTF_8)).getAsJsonObject();
        if(!request.get("format").getAsString().equals("awft-native-tree-patch:1")||!mode.equals(request.get("allowed_operation").getAsString())||!candidate.equals(request.get("candidate_version").getAsString())||!bridge.equals(request.get("bridge_version").getAsString())
            ||!ModList.get().getModContainerById("awft_control_bridge").orElseThrow().getModInfo().getVersion().toString().equals(bridge)||!ModList.get().getModContainerById("regions_unexplored").orElseThrow().getModInfo().getVersion().toString().equals("0.6.3"))throw new IllegalStateException("Actual tree runtime versions differ");
        resource(NativeTreePatchSupport.class,"NativeTreePatchSupport.class",request.get("native_class_sha256").getAsString());resource(TreeGrowthScope.class,"TreeGrowthScope.class",request.get("native_scope_sha256").getAsString());
        JsonObject owner=JsonParser.parseString(new String(bounded(owned("dashboard/artistic-owner.json"),65536),StandardCharsets.UTF_8)).getAsJsonObject(),active=JsonParser.parseString(new String(bounded(owned("packwiz/active.json"),65536),StandardCharsets.UTF_8)).getAsJsonObject(),installed=JsonParser.parseString(new String(bounded(owned("server/installed.json"),1024*1024),StandardCharsets.UTF_8)).getAsJsonObject();
        if(!owner.get("format").getAsString().equals("awft-artistic-stage:1")||!Path.of(owner.get("home").getAsString()).toRealPath().equals(home.toRealPath())||!active.get("version").getAsString().equals(candidate)||!installed.get("pack_version").getAsString().equals(candidate)||!active.get("pack_sha256").equals(installed.get("pack_sha256"))||!active.get("pack_sha256").equals(request.get("pack_sha256")))throw new IllegalStateException("Actual owned tree pack custody differs");
        checkpoint();plan=read(ref("plan"),MAX_INPUT);planSha=ref("plan").get("sha256").getAsString();level=server.overworld();
        if(!plan.get("format").getAsString().equals("awft-native-tree-patch-plan:1")||!plan.get("seed").getAsString().equals(Long.toString(level.getSeed()))||!Path.of(plan.get("world_path").getAsString()).toRealPath().equals(server.getWorldPath(LevelResource.ROOT).toRealPath()))throw new IllegalStateException("Actual tree world identity differs");
        for(JsonElement element:plan.getAsJsonArray("saplings")){String id=element.getAsString();if(!SAPLINGS.contains(id)||saplings.contains(id)||saplings.size()>=9)throw new IllegalStateException("Only the reviewed finite native sapling list is available");Block block=BuiltInRegistries.BLOCK.get(ResourceLocation.parse(id));if(!(block instanceof SaplingBlock)||!(block instanceof BonemealableBlock))throw new IllegalStateException("Actual selected sapling class is unsupported; never approximate it");saplings.add(id);}
        if(saplings.isEmpty())throw new IllegalStateException("At least one actual sapling required");action=mode;
        if(quarantineLatched||Files.exists(journal.resolve("tree-growth-quarantine.json")))throw new IllegalStateException("Existing native tree quarantine requires exact review; never retry held roots");
        if(Files.getFileStore(home).getUsableSpace()<32212254720L+640L*1024*1024
            ||Files.getFileStore(Path.of("C:/")).getUsableSpace()<32212254720L+32L*1024*1024)
            throw new IllegalStateException("Both independent30GiB reserves plus the bounded native patch allocation are required");
        for(var pin:Map.of("native_guard_sha256","mixin/NativeTreeGrowthGuardMixin.class",
                "bee_audit_sha256","TreeBeeAudit.class","bee_facts_sha256","BeeNestFacts.class",
                "pre_mutation_field_check_sha256","PreMutationFieldCheck.class","native_readiness_sha256","NativeTreePatchReadiness.class").entrySet())
            resource(NativeTreePatchSupport.class,pin.getValue(),request.get(pin.getKey()).getAsString());
        JsonObject ready=read(ref("patch_authority"),128*1024);
        if(!ready.get("format").getAsString().equals("awft-reviewed-native-tree-patch:1")
            ||!ready.get("patch_plan_sha256").getAsString().equals(planSha)
            ||!ready.get("checkpoint_sha256").getAsString().equals(request.get("checkpoint_sha256").getAsString())
            ||!ready.get("native_capture_each_root").getAsBoolean()
            ||!ready.get("allow_only_reviewed_native_foliage_overlap").getAsBoolean()
            ||!ready.get("preserve_all_existing_trunks_BEs_and_hives").getAsBoolean()
            ||!ready.get("bare_patch_construction_clearance_reviewed").getAsBoolean())
            throw new IllegalStateException("Exact parent-reviewed bare patch/live-capture authority required; not whole-town art acceptance");
        naturalCanopyReviewed=optionalFlag(ready,"allow_natural_leaf_to_descriptor_tree_materials");
        ownedPreplantedReviewed=optionalFlag(ready,"allow_owned_preplanted_saplings")&&optionalFlag(ready,"owned_planting_provenance_reviewed");
        JsonObject mask=read(ref("protection"),MAX_INPUT);
        if(!mask.get("seed").getAsString().equals(plan.get("seed").getAsString())
            ||!mask.get("world_path").getAsString().equals(plan.get("world_path").getAsString())
            ||mask.get("minimum_buffer_blocks").getAsInt()<5
            ||!mask.get("includes_latest_plaza_routes_and_walks").getAsBoolean()
            ||!mask.get("includes_current_bridge_fountain_zipline_and_north_partition").getAsBoolean())
            throw new IllegalStateException("Complete current construction/AIR/routes/flow/flight/north partition protection required");
        for(JsonElement value:mask.getAsJsonArray("columns")){
            JsonArray col=value.getAsJsonArray();if(col.size()!=2||protectedColumns.size()>=500000)throw new IllegalStateException("Finite current protection required");
            protectedColumns.add(TreeGrowthScope.column(col.get(0).getAsInt(),col.get(1).getAsInt()));
        }
        JsonObject eligibility=read(ref("eligible_land"),MAX_INPUT);
        if(!eligibility.get("format").getAsString().equals("awft-measured-south-eligible-land:1")
            ||!eligibility.get("checkpoint_sha256").getAsString().equals(request.get("checkpoint_sha256").getAsString())
            ||!eligibility.get("eastmost_north_land_edge_measured").getAsBoolean()
            ||!eligibility.get("connected_south_shore_to_cliff_foot_measured").getAsBoolean()
            ||!eligibility.get("seed").getAsString().equals(plan.get("seed").getAsString())
            ||!eligibility.get("world_path").getAsString().equals(plan.get("world_path").getAsString()))
            throw new IllegalStateException("Actual expanded connected eligible-land measurement required; rectangle/old clipped forest is not authority");
        for(JsonElement row:eligibility.getAsJsonArray("eligible_columns_xz")){
            JsonArray p=row.getAsJsonArray();if(p.size()!=2||eligibleColumns.size()>=500000)throw new IllegalStateException("Finite measured southern land required");
            eligibleColumns.add(TreeGrowthScope.column(p.get(0).getAsInt(),p.get(1).getAsInt()));
        }
        JsonObject held=read(ref("prior_root_custody"),MAX_INPUT);
        if(!held.get("format").getAsString().equals("awft-current-tree-root-custody:1")
            ||!held.get("checkpoint_sha256").getAsString().equals(request.get("checkpoint_sha256").getAsString())
            ||!held.get("all_attempted_failed_held_lost_and_successful_roots_included").getAsBoolean())
            throw new IllegalStateException("Every original attempt/hold must remain in current root custody");
        for(JsonElement value:held.getAsJsonArray("roots")){
            JsonArray p=value.getAsJsonArray();if(p.size()!=3||heldRoots.size()>=65536)throw new IllegalStateException("Finite retained root custody required");
            heldRoots.add(new BlockPos(p.get(0).getAsInt(),p.get(1).getAsInt(),p.get(2).getAsInt()));
        }
        Set<BlockPos> uniqueRoots=new HashSet<>();
        for(JsonElement value:plan.getAsJsonArray("roots")){
            JsonObject row=value.getAsJsonObject();String id=row.get("id").getAsString();JsonArray pos=row.getAsJsonArray("root");
            if(!id.matches("[a-z0-9][a-z0-9-]{0,63}")||!patchIds.add(id)||pos.size()!=3||patchRoots.size()>=MAX_ROOTS)
                throw new IllegalStateException("One finite unique 1..32-root patch required");
            BlockPos p=new BlockPos(pos.get(0).getAsInt(),pos.get(1).getAsInt(),pos.get(2).getAsInt());
            if(!uniqueRoots.add(p)||heldRoots.contains(p)||!eligibleColumns.contains(TreeGrowthScope.column(p.getX(),p.getZ()))
                ||!saplings.contains(row.get("sapling").getAsString()))throw new IllegalStateException("Unmeasured/duplicate/previously attempted root refused");
            JsonObject q=row.getAsJsonObject("qualification");
            if(!q.get("all_reachable_features_reviewed").getAsBoolean()||!q.get("derivation_sha256").getAsString().matches("[a-f0-9]{64}"))
                throw new IllegalStateException("All normal/rare/flower/root variants require sealed envelope derivation");
            int[] write=box(row.getAsJsonArray("write_bounds")),known=box(row.getAsJsonArray("known_bounds")),relative=boxRelative(q.getAsJsonArray("relative_write_bounds"));
            for(int i=0;i<6;i++){int axis=i%3,origin=axis==0?p.getX():axis==1?p.getY():p.getZ();if(write[i]!=origin+relative[i])throw new IllegalStateException("Never clip a qualified native variant envelope");}
            if(volume(known)>MAX_CELLS||volume(write)>MAX_CELLS||!inside(write,p)||p.getY()<48||p.getY()>256
                ||known[0]>write[0]-8||known[2]>write[2]-8||known[3]<write[3]+8||known[5]<write[5]+8||known[1]>write[1]-2||known[4]<write[4]+4)
                throw new IllegalStateException("Complete finite native write/read physics envelope required");
            for(int x=write[0];x<=write[3];x++)for(int z=write[2];z<=write[5];z++)
                if(protectedColumns.contains(TreeGrowthScope.column(x,z)))throw new IllegalStateException("Preserve full architecture/AIR/path/flight/flow/view masks");
            parse(row.get("expected_root").getAsString());parse(row.get("expected_soil").getAsString());
            if(optionalFlag(row,"allow_owned_preplanted_sapling")){
                BlockState recorded=parse(row.get("expected_root").getAsString());Block selected=BuiltInRegistries.BLOCK.get(ResourceLocation.parse(row.get("sapling").getAsString()));
                if(!ownedPreplantedReviewed||recorded.getBlock()!=selected||!(selected instanceof SaplingBlock)||!recorded.hasProperty(SaplingBlock.STAGE)
                    ||recorded.hasBlockEntity()||!recorded.getFluidState().isEmpty()||recorded.is(BlockTags.LOGS))
                    throw new IllegalStateException("Exact reviewed owned preplanted sapling state/species required");
            }
            boolean leafOnly=literalFlag(row,"allow_native_leaf_to_leaf_only"),treeMaterials=optionalFlag(row,"allow_natural_leaf_to_native_tree_materials");
            if(leafOnly==treeMaterials||treeMaterials&&!naturalCanopyReviewed)
                throw new IllegalStateException("Exactly one reviewed leaf-only or explicit natural-tree-material mode required");
            JsonArray leaves=row.getAsJsonArray("native_leaf_block_ids");if(leaves.size()>32)throw new IllegalStateException("Finite reviewed native foliage identities required");
            for(JsonElement leaf:leaves){ResourceLocation key=ResourceLocation.parse(leaf.getAsString());if(!BuiltInRegistries.BLOCK.containsKey(key)
                ||!(BuiltInRegistries.BLOCK.get(key)instanceof LeavesBlock))throw new IllegalStateException("Actual reviewed LeavesBlock required");}
            patchRoots.add(row);
        }
        if(patchRoots.isEmpty())throw new IllegalStateException("An empty patch cannot claim density");
        if(mode.equals("grow")){
            JsonObject proof=read(ref("native_inspect"),2*1024*1024);Path proofPath=owned(ref("native_inspect").get("path").getAsString());
            if(!new String(bounded(proofPath.resolveSibling(proofPath.getFileName()+".complete"),128),StandardCharsets.UTF_8).strip().equals(ref("native_inspect").get("sha256").getAsString())
                ||!proof.get("operation").getAsString().equals("inspect")||proof.get("failures").getAsInt()!=0||proof.has("error")
                ||!proof.get("cleanup_passed").getAsBoolean()||proof.get("world_recovery_required").getAsBoolean()
                ||proof.get("temporary_tickets_remaining").getAsInt()!=0||proof.get("pending_shared_futures").getAsInt()!=0
                ||!proof.get("candidate").getAsString().equals(candidate)||!proof.get("bridge").getAsString().equals(bridge)
                ||!proof.get("plan_sha256").getAsString().equals(planSha)
                ||!proof.get("checkpoint_sha256").getAsString().equals(request.get("checkpoint_sha256").getAsString())
                ||!proof.get("native_class_sha256").getAsString().equals(request.get("native_class_sha256").getAsString())
                ||proof.get("root_count").getAsInt()!=patchRoots.size())throw new IllegalStateException("Genuine complete clean current-class native patch INSPECT required");
            long age=java.time.Duration.between(Instant.parse(proof.get("finished").getAsString()),Instant.now()).toSeconds();
            if(age< -30||age>1800||proof.getAsJsonArray("roots").size()!=patchRoots.size())throw new IllegalStateException("Native patch INSPECT expired or incomplete");
            Set<String> inspected=new HashSet<>();for(JsonElement value:proof.getAsJsonArray("roots")){
                JsonObject row=value.getAsJsonObject();if(!row.get("status").getAsString().equals("CURRENT_NATIVE_FIELD_CAPTURED_NO_MUTATION")
                    ||!inspected.add(row.get("root_id").getAsString()))throw new IllegalStateException("No repeated/missing/failed inspection root");
            }
            if(!inspected.equals(patchIds))throw new IllegalStateException("Native INSPECT covers different roots");
        }
        report.put("checkpoint_sha256",request.get("checkpoint_sha256").getAsString());report.put("native_class_sha256",request.get("native_class_sha256").getAsString());
        report.put("root_count",patchRoots.size());report.put("source_spacing_goal_metres",plan.get("spacing_goal_metres"));
        report.put("density_or_ecological_acceptance",false);
        modPath=owned("server/mods/"+RU_FILE);if(!ModList.get().getModFileById("regions_unexplored").getFile().getFilePath().toRealPath().equals(modPath.toRealPath()))throw new IllegalStateException("Actual loaded RU source path differs");hashAttrs=Files.readAttributes(modPath,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);if(hashAttrs.size()>16*1024*1024)throw new IllegalStateException("Bounded pinned native tree artifact required");hashStream=Files.newInputStream(modPath);hashDigest=MessageDigest.getInstance("SHA-256");hashBytes=0;
        lease=interlock.acquire("native-trees:"+expected,false);if(lease==null||!lease.valid())throw new IllegalStateException("Shared exclusive maintenance lease required");phase=Phase.HASH;report.put("candidate",candidate);report.put("bridge",bridge);report.put("plan_sha256",planSha);
    }

    private static int[] boxRelative(JsonArray values){
        if(values.size()!=6)throw new IllegalStateException("Six qualified relative bounds required");int[] out=new int[6];
        for(int i=0;i<6;i++){out[i]=values.get(i).getAsInt();if(out[i]<-64||out[i]>64)throw new IllegalStateException("Finite sealed native envelope required");}
        if(out[0]>out[3]||out[1]>out[4]||out[2]>out[5])throw new IllegalStateException("Ordered qualified native envelope required");return out;
    }
    private void selectRoot()throws Exception{
        if(savedReadiness==null||!savedReadiness.ready())throw new IllegalStateException("Actual complete current persisted FULL halo proof must precede the first ticket");
        rootPlan=patchRoots.get(rootIndex);rootId=rootPlan.get("id").getAsString();currentSaplingId=rootPlan.get("sapling").getAsString();
        qualification=rootPlan.getAsJsonObject("qualification");JsonArray p=rootPlan.getAsJsonArray("root");
        naturalCanopyRoot=optionalFlag(rootPlan,"allow_natural_leaf_to_native_tree_materials");naturalTreeOutputs=Set.of();
        ownedPreplantedRoot=optionalFlag(rootPlan,"allow_owned_preplanted_sapling");ownedPreplantedOutputs=Set.of();
        if(naturalCanopyRoot){
            JsonObject descriptor=descriptors.get(currentSaplingId);
            if(!sha(JSON.toJson(sorted(descriptor)).getBytes(StandardCharsets.UTF_8)).equals(qualification.get("native_descriptor_sha256").getAsString()))
                throw new IllegalStateException("Natural canopy output set requires the exact sealed native feature descriptor");
            naturalTreeOutputs=qualifiedNaturalTreeOutputs(descriptor);
        }
        root=new BlockPos(p.get(0).getAsInt(),p.get(1).getAsInt(),p.get(2).getAsInt());sapling=BuiltInRegistries.BLOCK.get(ResourceLocation.parse(currentSaplingId)).defaultBlockState();
        if(ownedPreplantedRoot){
            JsonObject descriptor=descriptors.get(currentSaplingId);
            if(!sha(JSON.toJson(sorted(descriptor)).getBytes(StandardCharsets.UTF_8)).equals(qualification.get("native_descriptor_sha256").getAsString()))
                throw new IllegalStateException("Owned root outputs require the exact sealed native feature descriptor");
            Set<BlockState> outputs=new HashSet<>(qualifiedNaturalTreeOutputs(descriptor));BlockState recorded=parse(rootPlan.get("expected_root").getAsString());
            outputs.add(Blocks.AIR.defaultBlockState());outputs.add(recorded.setValue(SaplingBlock.STAGE,0));outputs.add(recorded.setValue(SaplingBlock.STAGE,1));
            ownedPreplantedOutputs=TreeGrowthScope.snapshotSet(outputs);
        }
        int[] write=box(rootPlan.getAsJsonArray("write_bounds"));knownBounds=box(rootPlan.getAsJsonArray("known_bounds"));
        writeBounds=new AABB(write[0],write[1],write[2],write[3]+1,write[4]+1,write[5]+1);
        before.clear();approvedFoliage.clear();leafIds.clear();chunks.clear();capturedSha=capturedName=null;captureCursor=0;mutated=false;rolls=successRolls=performCalls=0;
        for(JsonElement leaf:rootPlan.getAsJsonArray("native_leaf_block_ids"))leafIds.add(leaf.getAsString());
        String identity=sha((Long.toString(level.getSeed())+"|"+root.getX()+"|"+root.getY()+"|"+root.getZ()).getBytes(StandardCharsets.UTF_8));
        Path intents=journal.resolve("tree-patch-root-intents");Files.createDirectories(intents);rootIntent=intents.resolve(identity+".json");
        if(Files.exists(rootIntent,LinkOption.NOFOLLOW_LINKS))throw new IllegalStateException("A prior dense-patch root intent remains; never replay or select a new random variant");
        for(int x=knownBounds[0]>>4;x<=knownBounds[3]>>4;x++)for(int z=knownBounds[2]>>4;z<=knownBounds[5]>>4;z++)chunks.add(new ChunkPos(x,z));
        if(chunks.size()>32)throw new IllegalStateException("Per-root temporary native chunk budget exceeded");
        for(ChunkPos c:chunks){tickets.add(c);ticket(c,true);pending.add(((worldfortwo.bridge.mixin.ChunkCacheAccess)(Object)level.getChunkSource()).awftQueueChunk(c.x,c.z,ChunkStatus.FULL,false));}
        report.put("root_id",rootId);report.put("root_index",rootIndex);phase=Phase.LOAD;
    }
    private void captureRoot(long start)throws Exception{
        int width=knownBounds[3]-knownBounds[0]+1,depth=knownBounds[5]-knownBounds[2]+1,total=(int)volume(knownBounds),work=0;
        while(captureCursor<total&&work++<2048&&System.nanoTime()-start<4_000_000L){
            int cell=captureCursor++,x=knownBounds[0]+cell%width,z=knownBounds[2]+cell/width%depth,y=knownBounds[1]+cell/(width*depth);
            BlockPos p=new BlockPos(x,y,z);BlockState state=level.getBlockState(p);before.put(p,state);
            if(writeBounds.contains(x+.5,y+.5,z+.5)&&state.getBlock()instanceof LeavesBlock&&state.is(BlockTags.LEAVES)
                &&leafIds.contains(BuiltInRegistries.BLOCK.getKey(state.getBlock()).toString())&&!state.hasBlockEntity()
                &&state.getFluidState().isEmpty()&&level.getBlockEntity(p)==null
                &&(!naturalCanopyRoot||state.hasProperty(LeavesBlock.PERSISTENT)&&!state.getValue(LeavesBlock.PERSISTENT)))approvedFoliage.add(p);
        }
        if(captureCursor<total)return;
        if(!before.get(root).equals(parse(rootPlan.get("expected_root").getAsString()))
            ||!before.get(root.below()).equals(parse(rootPlan.get("expected_soil").getAsString())))
            throw new IllegalStateException("Measured root/soil authority changed; do not choose a new plot automatically");
        JsonObject value=new JsonObject();value.addProperty("format","awft-native-tree-patch-live-preimage:1");
        value.addProperty("construction_forbidden",true);value.addProperty("request_sha256",requestSha);value.addProperty("source_patch_sha256",planSha);
        value.addProperty("root_id",rootId);value.add("root",rootPlan.get("root"));value.addProperty("captured",Instant.now().toString());
        value.add("actual_complete_field",field(before));value.add("actual_native_BEs",beRows(nativeBEs()));
        value.addProperty("approved_current_native_foliage_cells",approvedFoliage.size());value.addProperty("ordinary_feature_not_yet_called",true);
        Path file=writeArchive(value,"tree-patch-preimage");capturedName=file.getFileName().toString();capturedSha=sha(bounded(file,8*1024*1024));
        report.put("live_preimage",capturedName);report.put("live_preimage_sha256",capturedSha);report.put("live_preimage_cells",before.size());
        report.put("explicit_natural_canopy_mode",naturalCanopyRoot);report.put("descriptor_qualified_output_states",naturalTreeOutputs.size());
        if(action.equals("inspect")){rootOutcomes.add(Map.of("root_id",rootId,"status","CURRENT_NATIVE_FIELD_CAPTURED_NO_MUTATION","preimage",capturedName,"preimage_sha256",capturedSha));phase=Phase.NEXT;return;}
        phase=Phase.GROW;
    }
    private Path writeArchive(JsonObject value,String family)throws Exception{
        byte[] raw=JSON.toJson(value).getBytes(StandardCharsets.UTF_8);if(raw.length>16*1024*1024)throw new IllegalStateException("Finite exact native archive required");
        var bytes=new java.io.ByteArrayOutputStream();try(var zip=new java.util.zip.GZIPOutputStream(bytes)){zip.write(raw);}
        byte[] compressed=bytes.toByteArray();if(compressed.length>8*1024*1024||archiveBytes+compressed.length>MAX_ARCHIVE_BYTES)
            throw new IllegalStateException("Finite patch allocation refused before archive/write");
        Files.createDirectories(journal);Path file=journal.resolve(family+"-"+UUID.randomUUID()+".json.gz");
        durable(file,compressed);durable(file.resolveSibling(file.getFileName()+".complete"),sha(compressed).getBytes(StandardCharsets.UTF_8));archiveBytes+=compressed.length;return file;
    }
    private static void durable(Path path,byte[] bytes)throws Exception{
        try(var channel=java.nio.channels.FileChannel.open(path,StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE)){
            var buffer=java.nio.ByteBuffer.wrap(bytes);while(buffer.hasRemaining())channel.write(buffer);channel.force(true);
        }
    }
    private void rootIntent()throws Exception{
        if(capturedSha==null||capturedName==null)throw new IllegalStateException("A durable current complete field must precede every owned setter");
        JsonObject value=new JsonObject();value.addProperty("format","awft-dense-native-root-intent:1");value.addProperty("request_sha256",requestSha);
        value.addProperty("patch_plan_sha256",planSha);value.addProperty("root_id",rootId);value.add("root",rootPlan.get("root"));
        value.addProperty("native_preimage",capturedName);value.addProperty("native_preimage_sha256",capturedSha);value.addProperty("created",Instant.now().toString());
        durable(rootIntent,JSON.toJson(value).getBytes(StandardCharsets.UTF_8));
    }
    private void nextRoot()throws Exception{
        for(ChunkPos c:List.copyOf(tickets)){ticket(c,false);tickets.remove(c);}
        pending.removeIf(CompletableFuture::isDone);if(!pending.isEmpty())return;
        before.clear();approvedFoliage.clear();rootIndex++;
        if(rootIndex>=patchRoots.size()){report.put("roots",List.copyOf(rootOutcomes));finish("finite native patch completed; mature coverage/visual ecology remains measured separately");return;}
        selectRoot();
    }

    private static int[] box(JsonArray a){if(a.size()!=6)throw new IllegalStateException("Six integer envelope coordinates required");int[] b=new int[6];for(int i=0;i<6;i++)b[i]=a.get(i).getAsInt();if(b[0]>b[3]||b[1]>b[4]||b[2]>b[5]||Math.abs((long)b[0])>30000000||Math.abs((long)b[3])>30000000||Math.abs((long)b[2])>30000000||Math.abs((long)b[5])>30000000||b[1]< -64||b[4]>319)throw new IllegalStateException("Finite native world envelope required");return b;}
    private static boolean inside(int[] b,BlockPos p){return p.getX()>=b[0]&&p.getX()<=b[3]&&p.getY()>=b[1]&&p.getY()<=b[4]&&p.getZ()>=b[2]&&p.getZ()<=b[5];}
    private static long volume(int[] b){return ((long)b[3]-b[0]+1)*(b[4]-b[1]+1)*((long)b[5]-b[2]+1);}
    @SuppressWarnings({"unchecked","rawtypes"}) private static BlockState parse(String text){if(!text.matches("[a-z0-9_.-]+:[a-z0-9_./-]+(?:\\[[a-z0-9_=,]+\\])?"))throw new IllegalStateException("Invalid native block state");String[] parts=text.split("\\[",2);ResourceLocation id=ResourceLocation.parse(parts[0]);if(!BuiltInRegistries.BLOCK.containsKey(id))throw new IllegalStateException("Unknown native block");BlockState state=BuiltInRegistries.BLOCK.get(id).defaultBlockState();Set<String> keys=new HashSet<>();if(parts.length==2)for(String item:parts[1].substring(0,parts[1].length()-1).split(",")){String[] pair=item.split("=",2);if(pair.length!=2||!keys.add(pair[0]))throw new IllegalStateException("Invalid property");Property property=state.getBlock().getStateDefinition().getProperty(pair[0]);if(property==null)throw new IllegalStateException("Unknown property");state=state.setValue(property,(Comparable)property.getValue(pair[1]).orElseThrow());}if(keys.size()!=state.getProperties().size())throw new IllegalStateException("Complete native preimage properties required");return state;}
    private static JsonElement sorted(JsonElement value){if(value.isJsonObject()){JsonObject result=new JsonObject();TreeSet<String> keys=new TreeSet<>(value.getAsJsonObject().keySet());for(String key:keys)result.add(key,sorted(value.getAsJsonObject().get(key)));return result;}if(value.isJsonArray()){JsonArray result=new JsonArray();for(JsonElement v:value.getAsJsonArray())result.add(sorted(v));return result;}return value;}
    private static boolean literalFlag(JsonObject row,String key){JsonElement v=row.get(key);if(v==null||!v.isJsonPrimitive()||!v.getAsJsonPrimitive().isBoolean())throw new IllegalStateException("Literal canopy permission boolean required: "+key);return v.getAsBoolean();}
    private static boolean optionalFlag(JsonObject row,String key){return row.has(key)&&literalFlag(row,key);}
    private static final Map<String,String> MATERIAL_CLASSES=Map.ofEntries(
        Map.entry("net.minecraft.world.level.block.RotatedPillarBlock","24b5dd143485aedee9c2669baa6989d8fab7c4e7dd73717a22e49245e571b6a2"),
        Map.entry("net.minecraft.world.level.block.LeavesBlock","65d07f0a9abde031caac6a013efe04a28a2fc3e599e4ec5faf09aa989c884bdd"),
        Map.entry("net.regions_unexplored.block.type.wood.PineLogBlock","c4f04fa2469055e34db9bac750c4fa6276e2acba1ecf0653acd717771b3fca37"),
        Map.entry("net.regions_unexplored.block.type.wood.AspenLogBlock","2aedfbdeff1df830ab27f234cb55d8bd7557e356f39b2ca133e1a7714dacbf9f"),
        Map.entry("net.regions_unexplored.block.type.wood.BranchBlock","b56b2cedaabf1ef1dbb92791bc0c86e76eb604955e2c10a2646fa98ee32180a8"),
        Map.entry("net.regions_unexplored.block.type.leaves.RUTintedParticlesLeavesBlock","79f4070b32979914d923021a6b907af770503305e88f5b6ed3cc5c0fc86653b2"),
        Map.entry("net.regions_unexplored.block.type.leaves.RUUntintedParticlesLeavesBlock","6ace5c846c20b0d1b5d2dbf729661d9d03d2a1dec91657c24aed8232e6352b57"));
    /** Only named material roles in the already sealed codecs; never a recursive Name walk. */
    private static Set<BlockState> qualifiedNaturalTreeOutputs(JsonObject descriptor)throws Exception{
        JsonObject features=descriptor.getAsJsonObject("features");if(features.size()<1||features.size()>16)throw new IllegalStateException("Finite sealed features required");
        Set<BlockState> states=new HashSet<>();
        for(var item:features.entrySet()){
            JsonObject codec=item.getValue().getAsJsonObject().getAsJsonObject("actual_codec");String type=codec.get("type").getAsString();
            if(!Set.of("minecraft:tree","regions_unexplored:larch_tree","regions_unexplored:sakura_tree","regions_unexplored:aspen_tree").contains(type))throw new IllegalStateException("Unknown natural tree codec qualification");
            JsonObject config=codec.getAsJsonObject("config");materialProvider(config.getAsJsonObject("trunk_provider"),"log",states);materialProvider(config.getAsJsonObject("foliage_provider"),"leaf",states);
            if(config.has("branch_provider"))materialProvider(config.getAsJsonObject("branch_provider"),"branch",states);
            JsonArray decorators=config.has("decorators")?config.getAsJsonArray("decorators"):new JsonArray();if(decorators.size()>32)throw new IllegalStateException("Finite tree decorators required");
            for(JsonElement element:decorators){JsonObject d=element.getAsJsonObject();String kind=d.get("type").getAsString();
                if(Set.of("regions_unexplored:random_branch","regions_unexplored:group_branch").contains(kind)){
                    JsonObject branch=new JsonObject();branch.addProperty("Name",d.get("branch_block").getAsString());materialState(branch,"branch",states);
                    JsonObject log=new JsonObject();log.addProperty("Name",d.get("log_block").getAsString());materialState(log,"log",states);
                    if(d.has("leaves_provider"))materialProvider(d.getAsJsonObject("leaves_provider"),"leaf",states);
                }else if(!Set.of("minecraft:beehive","regions_unexplored:place_on_ground").contains(kind))throw new IllegalStateException("Unknown native decorator qualification");
                // Hives/ground decorations are NOT added to canopy output permission.
            }
        }
        if(states.isEmpty()||states.size()>256)throw new IllegalStateException("Finite exact descriptor output set required");return TreeGrowthScope.snapshotSet(states);
    }
    private static void materialProvider(JsonObject provider,String role,Set<BlockState> states)throws Exception{
        if(provider==null||!provider.keySet().equals(Set.of("type","state"))||!provider.get("type").getAsString().equals("minecraft:simple_state_provider"))throw new IllegalStateException("Only qualified literal simple-state tree providers are admitted");
        materialState(provider.getAsJsonObject("state"),role,states);
    }
    @SuppressWarnings({"rawtypes","unchecked"}) private static void materialState(JsonObject value,String role,Set<BlockState> output)throws Exception{
        if(!value.has("Name")||!Set.of("Name","Properties").containsAll(value.keySet()))throw new IllegalStateException("Exact tree material state required");
        ResourceLocation key=ResourceLocation.parse(value.get("Name").getAsString());if(!BuiltInRegistries.BLOCK.containsKey(key))throw new IllegalStateException("Unregistered tree material");
        Block block=BuiltInRegistries.BLOCK.get(key);BlockState base=block.defaultBlockState();String name=block.getClass().getName(),pin=MATERIAL_CLASSES.get(name);
        if(pin==null)throw new IllegalStateException("Unqualified tree material class: "+name);resource(block.getClass(),"/"+name.replace('.','/')+".class",pin);
        if(value.has("Properties"))for(var property:value.getAsJsonObject("Properties").entrySet()){
            Property p=block.getStateDefinition().getProperty(property.getKey());if(p==null)throw new IllegalStateException("Unknown provider property");base=base.setValue(p,(Comparable)p.getValue(property.getValue().getAsString()).orElseThrow());
        }
        Set<String> dynamic;
        if(role.equals("leaf")){
            if(!(block instanceof LeavesBlock)||!base.is(BlockTags.LEAVES)||!base.hasProperty(LeavesBlock.PERSISTENT)||base.getValue(LeavesBlock.PERSISTENT))throw new IllegalStateException("Only natural nonpersistent native leaves");
            dynamic=Set.of("distance");
        }else if(role.equals("branch")){
            if(!name.equals("net.regions_unexplored.block.type.wood.BranchBlock")||!base.is(BlockTags.LOGS)||!base.getProperties().stream().map(Property::getName).collect(java.util.stream.Collectors.toSet()).equals(Set.of("facing")))throw new IllegalStateException("Only pinned directional natural BranchBlock");
            dynamic=Set.of("facing");
        }else{
            if(!base.is(BlockTags.LOGS)||!(name.equals("net.minecraft.world.level.block.RotatedPillarBlock")||name.equals("net.regions_unexplored.block.type.wood.PineLogBlock")||name.equals("net.regions_unexplored.block.type.wood.AspenLogBlock")))throw new IllegalStateException("Only pinned native trunk/wood classes");
            dynamic=name.endsWith("PineLogBlock")?Set.of("axis","transition_block"):name.endsWith("AspenLogBlock")?Set.of("axis","is_base"):Set.of("axis");
        }
        var possible=block.getStateDefinition().getPossibleStates();if(possible.size()>4096)throw new IllegalStateException("Finite material state definition required");
        for(BlockState candidate:possible){boolean matches=true;for(Property p:base.getProperties())if(!dynamic.contains(p.getName())&&!candidate.getValue(p).equals(base.getValue(p)))matches=false;
            if(matches&&!candidate.hasBlockEntity()&&candidate.getFluidState().isEmpty()){output.add(candidate);if(output.size()>256)throw new IllegalStateException("Qualified material state budget exceeded");}
        }
    }
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
    private void archive(Map<BlockPos,BlockState> after,String kind,Map<BlockPos,BlockState> restored,Map<BlockPos,String> beBefore,Map<BlockPos,String> beAfter,Map<BlockPos,String> beRestored)throws Exception{JsonObject value=new JsonObject();value.addProperty("format","awft-native-tree-outcome:1");value.addProperty("kind",kind);value.addProperty("construction_forbidden",true);value.addProperty("entity_nbt_replay_forbidden",true);value.addProperty("source_plan_sha256",planSha);value.add("before",field(before));if(after!=null)value.add("native_after",field(after));else value.addProperty("native_after_capture_unavailable",true);value.add("native_be_before",beRows(beBefore));if(beAfter!=null)value.add("native_be_after",beRows(beAfter));else value.addProperty("native_be_after_capture_unavailable",true);if(restored!=null)value.add("after_failed_attempt_restoration",field(restored));if(beRestored!=null)value.add("native_be_after_restoration",beRows(beRestored));value.add("native_descriptors",JSON.toJsonTree(descriptors));byte[] raw=JSON.toJson(value).getBytes(StandardCharsets.UTF_8);if(raw.length>16*1024*1024)throw new IllegalStateException("Native outcome archive exceeds bound");value.addProperty("root_id",rootId);value.add("root",rootPlan.get("root"));value.addProperty("live_preimage_sha256",capturedSha);value.addProperty("approved_native_leaf_overlap_cells",approvedFoliage.size());Path file=writeArchive(value,"tree-patch-outcome");report.put("outcome_archive",file.getFileName().toString());report.put("outcome_archive_sha256",sha(bounded(file,8*1024*1024)));}
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
    private void recoverGrowth(TreeGrowthScope scope,Throwable failure,Map<BlockPos,String> beBefore,TreeBeeAudit beeAudit){
        // Latch before capture/allocation. Broken failure evidence can NEVER bypass restoration.
        worldResidual=true;FailedFields evidence=new FailedFields();
        var recovery=TreeGrowthScope.captureThenRestore(
            ()->{evidence.actualAfter=snapshot();evidence.beAfter=nativeBEs();},
            ()->{beeAudit.beforeRollback(scope.attempted);int restored=scope.restoreFailedAttempt();evidence.restored=snapshot();evidence.beRestored=nativeBEs();
                for(var row:before.entrySet())if(!row.getValue().equals(evidence.restored.get(row.getKey())))throw new IllegalStateException("Untracked native residual requires review");
                if(!beBefore.equals(evidence.beRestored))throw new IllegalStateException("Native BE restoration requires review; no replay of inventories");
                beeAudit.restored();report.put("restored_owned_cells",restored);
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
        JsonObject descriptor=descriptors.get(currentSaplingId);String actual=sha(JSON.toJson(sorted(descriptor)).getBytes(StandardCharsets.UTF_8));
        if(!actual.equals(qualification.get("native_descriptor_sha256").getAsString()))throw new IllegalStateException("Actual runtime grower/features differ from reviewed full descriptor");
        if(!sapling.canSurvive(level,root))throw new IllegalStateException("Native sapling cannot survive on the actual soil");
        if(!level.getEntities(null,writeBounds.inflate(1)).isEmpty())throw new IllegalStateException("Preserve actual residents, passengers and objects near native growth; choose an unoccupied plot");
        Map<BlockPos,String> beBefore=nativeBEs();
        TreeBeeAudit beeAudit;
        try{beeAudit=new TreeBeeAudit(level,before,writeBounds,TreeBeeAudit.mayCreateNest(descriptor),true);}
        catch(Throwable auditInitializationFailure){
            report.put("native_bee_audit_initialization_error",auditInitializationFailure.toString());
            report.put("this_growth_owned_setter_invoked",false);
            if(mutated||worldResidual)quarantine(auditInitializationFailure);
            throw new IllegalStateException("Native bee audit initialization failed before this growth's owned setter",auditInitializationFailure);
        }
        TreeGrowthScope scope=ownedPreplantedRoot?new TreeGrowthScope(level,before,writeBounds,protectedColumns,root.getY()-1,TreeBeeAudit.mayCreateNest(descriptor),approvedFoliage,
                naturalCanopyRoot?naturalTreeOutputs:Set.of(),root,parse(rootPlan.get("expected_root").getAsString()),ownedPreplantedOutputs)
            :naturalCanopyRoot?new TreeGrowthScope(level,before,writeBounds,protectedColumns,root.getY()-1,TreeBeeAudit.mayCreateNest(descriptor),approvedFoliage,naturalTreeOutputs)
            :new TreeGrowthScope(level,before,writeBounds,protectedColumns,root.getY()-1,TreeBeeAudit.mayCreateNest(descriptor),approvedFoliage);
        try{
            report.put("this_growth_owned_setter_invoked",false);
            long recheckStarted=System.nanoTime();
            int rechecked=PreMutationFieldCheck.requireUnchanged(before,level::getBlockState,drift->{
                report.put("pre_mutation_full_preimage_passed",false);
                report.put("pre_mutation_drift",Map.of("position",List.of(drift.position().getX(),drift.position().getY(),drift.position().getZ()),
                    "expected",stateText(drift.expected()),"actual",drift.actual()==null?"UNKNOWN_OR_UNAVAILABLE":stateText(drift.actual()),
                    "checked_cells",drift.checkedCells()));
            });
            report.put("pre_mutation_full_preimage_passed",true);report.put("pre_mutation_rechecked_cells",rechecked);
            report.put("pre_mutation_recheck_ms",(System.nanoTime()-recheckStarted)/1_000_000.0);
            // Same server-thread call: no tick/yield between this WHOLE pass,
            // the nonmutating hook witness, and the first owned physical setter.
            scope.hookWitness(root);
            rootIntent(); // durable native field/intent precedes the first physical setter
            // Set before invocation: a native setter may throw after a partial physical write.
            if(!ownedPreplantedRoot){
                report.put("this_growth_owned_setter_invoked",true);
                mutated=true;anyMutated=true;if(!level.setBlock(root,sapling,3))throw new IllegalStateException("Native sapling placement refused");
            } // A pre-existing root keeps its actual stage; no reset or AIR workaround.
            report.put("owned_preplanted_sapling",ownedPreplantedRoot);
            for(int n=0;n<MAX_ATTEMPTS;n++){
                BlockState current=level.getBlockState(root);if(current.getBlock()!=sapling.getBlock())break;
                BonemealableBlock target=(BonemealableBlock)current.getBlock();if(!target.isValidBonemealTarget(level,root,current))throw new IllegalStateException("Native bonemeal target refused");
                rolls++;if(!target.isBonemealSuccess(level,level.random,root,current))continue;successRolls++;
                if(ownedPreplantedRoot){report.put("this_growth_owned_setter_invoked",true);mutated=true;anyMutated=true;}
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
            report.put("native_bee_audit",beeAudit.success(scope.attempted));report.put("native_changed_log_blocks",logs);report.put("native_changed_leaf_blocks",leaves);report.put("guarded_write_calls",scope.writes);report.put("guard_read_calls",scope.reads);
            archive(after,"NATIVE_GROWN_OUTCOME_NOT_VISUAL_ACCEPTANCE",null,beBefore,beAfter,null);
        }catch(Throwable failure){
            if(mutated){
                worldResidual=true;try{recoverGrowth(scope,failure,beBefore,beeAudit);}catch(Throwable recoveryFailure){quarantine(recoveryFailure);}
                throw new IllegalStateException("Native growth failed; exact restoration or quarantine recorded",failure);
            }
            report.put("refused_before_owned_mutation",true);
            throw new IllegalStateException("Native tree refused before its first owned mutation; unowned drift preserved without restoration",failure);
        }finally{
            try{scope.close();}catch(Throwable closeFailure){quarantine(closeFailure);throw new IllegalStateException("Native growth scope did not close cleanly; further planting blocked",closeFailure);}
        }
    }
    public void tick(MinecraftServer server){
        if(phase==Phase.IDLE)return;if(phase==Phase.CLEANUP){cleanup(true);return;}long start=System.nanoTime();
        try{
            if(++ticks>MAX_TICKS||!server.isSameThread()||lease==null||!lease.valid()||!server.getPlayerList().getPlayers().isEmpty())throw new IllegalStateException("Native patch finite deadline/thread/empty-server lease refused");
            if(phase==Phase.HASH){int n;do{n=hashStream.read(buffer);if(n>0){hashDigest.update(buffer,0,n);hashBytes+=n;}}while(n>=0&&System.nanoTime()-start<3_000_000L);if(n>=0)return;hashStream.close();hashStream=null;if(hashBytes!=hashAttrs.size()||!HexFormat.of().formatHex(hashDigest.digest()).equals(RU_SHA))throw new IllegalStateException("Pinned RU bytes differ");phase=Phase.DESCRIBE;}
            gate(server);
            if(phase==Phase.DESCRIBE){String id=saplings.get(cursor++);JsonObject value;try{value=describe(id);}catch(Throwable failure){throw new IllegalStateException("Actual native descriptor failed",failure);}descriptors.put(id,value);if(cursor<saplings.size())return;cursor=0;
                Set<ChunkPos> all=new HashSet<>();for(JsonObject row:patchRoots){int[] b=box(row.getAsJsonArray("known_bounds"));for(int x=b[0]>>4;x<=b[3]>>4;x++)for(int z=b[2]>>4;z<=b[5]>>4;z++)all.add(new ChunkPos(x,z));}
                savedReadiness=new NativeTreePatchReadiness(level,all);phase=Phase.READ_SAVED;return;}
            if(phase==Phase.READ_SAVED){if(!tickets.isEmpty())throw new IllegalStateException("No ticket before stored FULL validation");if(!savedReadiness.poll())return;report.put("current_storage_readiness",savedReadiness.report());checkpoint();selectRoot();return;}
            if(phase==Phase.LOAD){if(pending.stream().anyMatch(f->!f.isDone()))return;for(var future:pending)future.join();pending.clear();if(!ready())return;phase=Phase.CAPTURE;}
            if(phase==Phase.NEXT){nextRoot();return;}
            if(!ready())throw new IllegalStateException("Current root FULL known envelope unloaded");
            if(phase==Phase.CAPTURE){captureRoot(start);return;}
            if(phase==Phase.GROW){
                grow();rootOutcomes.add(Map.of("root_id",rootId,"status","NATIVE_MATURE_TRUNK_CANOPY_OBSERVED_NOT_VISUAL_ACCEPTANCE",
                    "preimage",capturedName,"preimage_sha256",capturedSha,"outcome",report.get("outcome_archive"),"outcome_sha256",report.get("outcome_archive_sha256")));
                phase=Phase.NEXT;
            }
        }catch(Exception|LinkageError error){report.put("error",error.toString());report.put("failures",1);report.put("roots",List.copyOf(rootOutcomes));finish("native patch stopped at first refusal/failure; successful prior roots and exact failed-root evidence retained, no retry");}
        report.put("last_work_ms",(System.nanoTime()-start)/1_000_000.0);
    }
    private void finish(String text){if(outcome==null)outcome=text;phase=Phase.CLEANUP;cleanup(true);}
    private void cleanup(boolean retry){
        List<String> errors=new ArrayList<>();if(hashStream!=null)try{hashStream.close();hashStream=null;}catch(Exception e){errors.add(e.toString());}
        if(level!=null)for(ChunkPos c:List.copyOf(tickets))try{ticket(c,false);tickets.remove(c);}catch(Exception|LinkageError e){errors.add(c+": "+e);}
        pending.removeIf(CompletableFuture::isDone);
        boolean savedIOClean=savedReadiness==null||savedReadiness.drained();
        if(tickets.isEmpty()&&pending.isEmpty()&&hashStream==null&&savedIOClean&&lease!=null)try{lease.close();lease=null;}catch(Exception e){errors.add(e.toString());}
        boolean clean=tickets.isEmpty()&&pending.isEmpty()&&hashStream==null&&savedIOClean&&lease==null;
        report.put("status",outcome);report.put("cleanup_resources_passed",clean);report.put("world_recovery_required",worldResidual);report.put("cleanup_passed",clean&&!worldResidual);
        report.put("temporary_tickets_remaining",tickets.size());report.put("pending_shared_futures",pending.size());report.put("cleanup_errors",errors);
        report.put("pending_persisted_read_futures",savedReadiness==null?0:savedReadiness.pending());
        report.put("native_bonemeal_trials_current_root",rolls);report.put("native_success_rolls_current_root",successRolls);report.put("perform_bonemeal_calls_current_root",performCalls);
        report.put("archive_bytes",archiveBytes);report.put("invented_or_claimed_consumed_bonemeal_items",0);report.put("global_wakes",0);
        report.put("any_root_setter_invoked",anyMutated);report.put("native_visual_or_density_acceptance",false);report.put("finished",Instant.now().toString());
        if(clean&&!terminalPublished)try{NativeJournal.terminal(journal,"tree-patch",report);terminalPublished=true;}
        catch(Exception failure){report.put("terminal_publication_blocked",failure.toString());}
        try{NativeJournal.progress(journal,"tree-patch-status.json",report);}catch(Exception failure){report.put("progress_publication_warning",failure.toString());}
        if(clean&&terminalPublished)phase=Phase.IDLE;
    }
    public void stopped(){if(busy())finish("server stopping; per-root records/owned native outcomes and any quarantine retained");}
}
