package worldfortwo.bridge;

import com.google.gson.*;
import com.mojang.brigadier.arguments.StringArgumentType;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.tags.PoiTypeTags;
import net.minecraft.world.entity.ai.village.poi.PoiTypes;
import net.minecraft.world.entity.ai.village.poi.PoiManager;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.entity.animal.allay.Allay;
import net.minecraft.world.entity.ai.memory.MemoryModuleType;
import net.minecraft.world.level.block.BedBlock;
import net.minecraft.world.level.block.LeavesBlock;
import net.minecraft.world.level.block.state.properties.BedPart;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.TicketType;
import net.minecraft.tags.FluidTags;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.MobSpawnType;
import net.minecraft.world.entity.SpawnPlacements;
import net.minecraft.world.entity.TamableAnimal;
import net.minecraft.world.entity.monster.Enemy;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.Property;
import net.minecraft.world.level.chunk.status.ChunkStatus;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.AABB;
import net.neoforged.fml.ModList;
import net.neoforged.fml.loading.FMLPaths;
import net.neoforged.neoforge.event.EventHooks;
import net.neoforged.neoforge.event.RegisterCommandsEvent;

import java.io.InputStream;
import java.lang.invoke.MethodHandles;
import java.lang.invoke.MethodType;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.CompletableFuture;

/** ISOLATED PROPOSAL, not wired into active bridge sources.
 * Only reviewed peaceful native classes; no copied entity NBT, ownership, fake
 * player, NoAI switches, teleport, rollback deletion, permanent forcing or wake.
 * Existing/uncertain UUIDs are never replaced. Ordinary AI needs later players.
 */
public final class NativeHabitatLifeSupport {
    private enum Phase { IDLE,HASH,LOAD,VALIDATE,WORK,CLEANUP }
    private record Habitat(HabitatLifePolicy.Kind kind,HabitatLifePolicy.Box known,HabitatLifePolicy.Box water,List<List<BlockPos>> routes,BlockPos bed,BlockPos job,BlockPos roof) {}
    private record Resident(UUID uuid,String id,String tag,EntityType<?> type,String nativeClass,String category,
                            double x,double y,double z,AABB habitat,Habitat site,HabitatLifePolicy.Species species,Map<BlockPos,BlockState> before) {}
    private record ArtifactState(HabitatLifePolicy.Artifact specification,Path path,BasicFileAttributes before) {}
    private static final Gson JSON=new Gson();
    private static final TicketType<ChunkPos> TICKET=TicketType.create("awft_habitat_life",Comparator.comparingLong(ChunkPos::toLong));
    private static final int MAX_TICKS=1800,MAX_PLAN=8*1024*1024,MAX_MEMBERS=16,MAX_BLOCKS=32768,MAX_CHUNKS=32;
    private final String candidate,bridge;
    private final ArtisticEngineeringSupport.Interlock interlock;
    private final Path home=FMLPaths.GAMEDIR.get().resolve("..").toAbsolutePath().normalize();
    private final Path journal=home.resolve("dashboard/settlement");
    private ArtisticEngineeringSupport.Lease lease;
    private ServerLevel level;
    private Phase phase=Phase.IDLE;
    private JsonObject request,plan,habitatPlan,habitatVerify;
    private String action,outcome,recipeSha,namespace;
    private TownLifeAuthority townAuthority;
    private boolean scaledPopulation,scaleProjectionReady;
    private int cohortLimit=MAX_MEMBERS,blockLimit=MAX_BLOCKS,planByteLimit=MAX_PLAN;
    private ScaledLifeBudget scaleBudget;
    private JsonObject scaleSpec;
    private BasicFileAttributes scaleLedgerStamp;
    private final Map<String,Integer> scaleCounts=new HashMap<>(),scaleHabitats=new HashMap<>();
    private final Map<String,Integer> savedHabitatEntities=new HashMap<>();
    private final Set<UUID> cohortAddedUUIDs=new HashSet<>();
    private record ScaleIntentStamp(Path path,BasicFileAttributes attributes) {}
    private final List<ScaleIntentStamp> scaleIntentStamps=new ArrayList<>();
    private int scaleAuditCursor;
    private boolean scaleAuditComplete;

    private final Map<UUID,TownLifeAuthority.Site> townResidents=new HashMap<>();
    private int ticks,index,spawned,preserved,intentsWritten,finalized,artifactIndex,populationAuthoritiesWritten;
    private boolean cleanupPublished,dataWriteAttempted,entityAddAttempted;
    private Path ledger;
    private InputStream hashStream;
    private MessageDigest hashDigest;
    private BasicFileAttributes hashBefore;
    private Path hashPath;
    private long hashed;
    private final byte[] hashBuffer=new byte[65536];
    private final List<ArtifactState> artifactSources=new ArrayList<>();
    private final Set<Long> excludedColumns=new HashSet<>(),bankColumns=new HashSet<>();
    private final List<Map<String,Object>> artifactProofs=new ArrayList<>();
    private final Set<BlockPos> proposedBeds=new HashSet<>(),proposedJobs=new HashSet<>();
    private final List<Resident> residents=new ArrayList<>();
    private final Map<UUID,JsonObject> censusMembers=new LinkedHashMap<>();
    private final List<Mob> previews=new ArrayList<>();
    private final Set<ChunkPos> chunks=new LinkedHashSet<>(),tickets=new LinkedHashSet<>();
    private final List<CompletableFuture<?>> pending=new ArrayList<>();
    private final Map<String,Object> report=new LinkedHashMap<>();
    private final List<Map<String,Object>> observed=new ArrayList<>();

    public NativeHabitatLifeSupport(String candidate,String bridge,ArtisticEngineeringSupport.Interlock interlock){
        this.candidate=Objects.requireNonNull(candidate);this.bridge=Objects.requireNonNull(bridge);this.interlock=Objects.requireNonNull(interlock);
        if(candidate.isBlank()||bridge.isBlank())throw new IllegalArgumentException("Exact candidate/bridge required");
    }
    public boolean busy(){return phase!=Phase.IDLE;}
    public void commands(RegisterCommandsEvent event){
        var root=Commands.literal("awftlife").requires(s->s.getEntity()==null&&s.hasPermission(4));
        for(String operation:List.of("inspect","seed"))root.then(Commands.literal(operation)
            .then(Commands.argument("bundle",StringArgumentType.word()).then(Commands.argument("sha256",StringArgumentType.word()).executes(c->{
                if(busy()){c.getSource().sendFailure(Component.literal("A LIFE transaction or exact cleanup still owns its lease"));return 0;}
                try{begin(c.getSource().getServer(),operation,StringArgumentType.getString(c,"bundle"),StringArgumentType.getString(c,"sha256"));return 1;}
                catch(Exception|LinkageError error){report.put("error",error.toString());report.put("failures",1);finish("LIFE admission refused; no automatic replay");throw new IllegalStateException("LIFE admission refused",error);}
            }))));
        root.then(Commands.literal("status").executes(c->{c.getSource().sendSuccess(()->Component.literal(JSON.toJson(report)),false);return 1;}));
        root.then(Commands.literal("cancel").executes(c->{if(phase==Phase.CLEANUP)cleanup(true);else finish("cancelled; any real residents and durable intents retained");return 1;}));
        event.getDispatcher().register(root);
    }
    private static String sha(byte[] raw)throws Exception{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(raw));}
    private static byte[] bounded(Path path,int cap)throws Exception{
        if(!Files.isRegularFile(path,LinkOption.NOFOLLOW_LINKS)||Files.size(path)<1||Files.size(path)>cap)throw new IllegalStateException("Unbounded/linked LIFE input");
        try(InputStream in=Files.newInputStream(path)){byte[] raw=in.readNBytes(cap+1);if(raw.length>cap)throw new IllegalStateException("LIFE input grew");return raw;}
    }
    private Path owned(String name)throws Exception{
        Path relative=Path.of(name);if(relative.isAbsolute()||name.indexOf(':')>=0||name.indexOf('\\')>=0)throw new IllegalStateException("Owned home-relative LIFE input required");
        for(Path part:relative)if(part.toString().equals(".")||part.toString().equals(".."))throw new IllegalStateException("No traversal");
        Path path=home.resolve(relative).normalize();
        for(Path p=path;p!=null&&!p.equals(home);p=p.getParent())if(Files.isSymbolicLink(p)||!p.toRealPath().equals(p.toAbsolutePath().normalize()))throw new IllegalStateException("Linked/redirected LIFE input");
        if(!path.toRealPath().startsWith(home.toRealPath()))throw new IllegalStateException("LIFE input escaped home");return path;
    }
    private JsonObject reference(String key){return request.getAsJsonObject(key);}
    private JsonObject read(JsonObject ref,int cap)throws Exception{
        byte[] raw=bounded(owned(ref.get("path").getAsString()),cap);
        if(raw.length!=ref.get("bytes").getAsInt()||!sha(raw).equals(ref.get("sha256").getAsString()))throw new IllegalStateException("Exact LIFE evidence bytes/hash differ");
        return JsonParser.parseString(new String(raw,StandardCharsets.UTF_8)).getAsJsonObject();
    }
    /** Small receipt policy only; no archive hashing or Minecraft state access. */
    static final class CheckpointReceipt {
        static final String CANONICAL="dashboard/settlement/backup-receipt.json",LIFE="dashboard/settlement/life-backup-receipt.json";
        static boolean retained(String path){
            if(CANONICAL.equals(path))return false;if(LIFE.equals(path))return true;
            throw new IllegalStateException("Only canonical or explicit LIFE checkpoint receipt allowed");
        }
        static boolean habitatBackup(String selection,String actual,String current){
            // checkpoint() already verifies the retained receipt and its exact
            // canonical link. The construction verifier keeps that original
            // custody header while freshly checking every current habitat cell.
            return current.equals(actual)||(LIFE.equals(selection)
                &&"0ba7ad2097fb52273a37da6a76d8fc030133b79cd26d81b97531d8d74c2546c2".equals(actual));
        }
        private static String string(JsonObject doc,String key){
            JsonElement value=doc.get(key);return value!=null&&value.isJsonPrimitive()&&value.getAsJsonPrimitive().isString()?value.getAsString():"";
        }
        private static boolean verified(JsonObject doc){
            JsonElement value=doc.get("verified");return value!=null&&value.isJsonPrimitive()&&value.getAsJsonPrimitive().isBoolean()&&value.getAsBoolean();
        }
        static JsonObject custody(JsonObject backup){
            JsonObject ref=backup.getAsJsonObject("source_custody");
            if(ref==null||!CANONICAL.equals(string(ref,"path"))||!string(ref,"sha256").matches("[a-f0-9]{64}"))throw new IllegalStateException("Pinned canonical custody receipt required");
            JsonElement bytes=ref.get("bytes");
            if(bytes==null||!bytes.isJsonPrimitive()||!bytes.getAsJsonPrimitive().isNumber())throw new IllegalStateException("Bounded custody receipt bytes required");
            int count=bytes.getAsBigDecimal().intValueExact();if(count<1||count>4096)throw new IllegalStateException("Bounded custody receipt bytes required");
            return ref;
        }
        static void validate(String path,String selection,JsonObject backup,String id,String sha,JsonObject canonical){
            boolean life=retained(path);
            if(!selection.isEmpty()&&!selection.equals(path))throw new IllegalStateException("Explicit checkpoint selection differs");
            // Keep the legacy canonical contract unchanged.
            if(!backup.get("verified").getAsBoolean()||!backup.get("sha256").getAsString().equals(sha))throw new IllegalStateException("Current LIFE checkpoint differs");
            if(!life)return;
            if(!LIFE.equals(selection)||!verified(backup)||!"awft-life-retained-checkpoint:1".equals(string(backup,"format"))
                ||!string(backup,"id").matches("[0-9]{8}T[0-9]{6}Z-[a-f0-9]{6}")||!string(backup,"id").equals(id)
                ||!string(backup,"sha256").matches("[a-f0-9]{64}"))throw new IllegalStateException("Verified retained LIFE checkpoint identity/selection differs");
            custody(backup);
            if(canonical==null||!verified(canonical)||!"20261028T191243Z-6ad3a8".equals(string(canonical,"id"))
                ||!"0ba7ad2097fb52273a37da6a76d8fc030133b79cd26d81b97531d8d74c2546c2".equals(string(canonical,"sha256")))throw new IllegalStateException("Verified canonical6ad custody identity differs");
        }
    }
    private void checkpoint()throws Exception{
        String path=reference("current_backup").get("path").getAsString();boolean life=CheckpointReceipt.retained(path);
        if(!owned(path).equals(journal.resolve(life?"life-backup-receipt.json":"backup-receipt.json")))throw new IllegalStateException("Owned checkpoint receipt required");
        JsonObject backup=read(reference("current_backup"),4096),canonical=null;
        if(life){
            JsonObject custody=CheckpointReceipt.custody(backup);
            if(!owned(custody.get("path").getAsString()).equals(journal.resolve("backup-receipt.json")))throw new IllegalStateException("Canonical source custody required");
            canonical=read(custody,4096);
        }
        CheckpointReceipt.validate(path,request.has("checkpoint_receipt")?request.get("checkpoint_receipt").getAsString():"",backup,
            request.has("checkpoint_id")?request.get("checkpoint_id").getAsString():"",request.get("checkpoint_sha256").getAsString(),canonical);
    }
    private static void nativeCode(Class<?> type,String expected)throws Exception{
        try(InputStream in=type.getResourceAsStream(type.getSimpleName()+".class")){
            if(in==null)throw new IllegalStateException("Native LIFE class missing");byte[] raw=in.readNBytes(256*1024+1);
            if(raw.length>256*1024||!sha(raw).equals(expected))throw new IllegalStateException("Actual loaded LIFE helper/policy differs");
        }
    }
    private void begin(MinecraftServer server,String operation,String bundle,String expected)throws Exception{
        if(busy()||lease!=null||!tickets.isEmpty()||!server.isSameThread()||!bundle.matches("life-[a-f0-9]{16}")||!expected.matches("[a-f0-9]{64}")||!bundle.endsWith(expected.substring(0,16)))throw new IllegalStateException("Busy/off-thread/invalid LIFE request");
        scaledPopulation=scaleProjectionReady=scaleAuditComplete=false;scaleAuditCursor=0;scaleIntentStamps.clear();cohortLimit=MAX_MEMBERS;blockLimit=MAX_BLOCKS;planByteLimit=MAX_PLAN;scaleBudget=null;scaleSpec=null;scaleLedgerStamp=null;scaleCounts.clear();scaleHabitats.clear();savedHabitatEntities.clear();cohortAddedUUIDs.clear();
        report.clear();observed.clear();townAuthority=null;townResidents.clear();outcome=null;cleanupPublished=dataWriteAttempted=entityAddAttempted=false;habitatPlan=habitatVerify=null;ticks=index=spawned=preserved=intentsWritten=finalized=artifactIndex=populationAuthoritiesWritten=0;artifactSources.clear();artifactProofs.clear();excludedColumns.clear();bankColumns.clear();proposedBeds.clear();proposedJobs.clear();report.put("operation",operation);report.put("started",Instant.now().toString());report.put("request_sha256",expected);
        Path stages=Path.of("D:\\A World for Two\\staging\\world-tests").toRealPath(),actualHome=home.toRealPath();
        if(!actualHome.getParent().equals(stages)||!actualHome.equals(home)
            ||!server.getWorldPath(LevelResource.ROOT).toRealPath().equals(home.resolve("world/RosewaterArtistic").toRealPath())
            ||server.getPort()!=25575||!server.getPlayerList().getPlayers().isEmpty()||!server.getServerVersion().equals("1.21.1"))throw new IllegalStateException("Exact owned empty private Minecraft 1.21.1 staging only");
        byte[] raw=bounded(owned("dashboard/settlement/"+bundle+"/request.json"),128*1024);
        if(!sha(raw).equals(expected))throw new IllegalStateException("LIFE request differs");request=JsonParser.parseString(new String(raw,StandardCharsets.UTF_8)).getAsJsonObject();
        scaledPopulation=request.get("format").getAsString().equals("awft-native-habitat-life:4");
        if(scaledPopulation){cohortLimit=64;blockLimit=262144;planByteLimit=32*1024*1024;}
        if(!(request.get("format").getAsString().equals("awft-native-habitat-life:3")||scaledPopulation)||!operation.equals(request.get("allowed_operation").getAsString())||!candidate.equals(request.get("candidate_version").getAsString())||!bridge.equals(request.get("bridge_version").getAsString())
            ||!ModList.get().getModContainerById("awft_control_bridge").orElseThrow().getModInfo().getVersion().toString().equals(bridge)
            ||!request.get("neoforge_version").getAsString().equals("21.1.262")||Runtime.version().feature()!=21
            ||!ModList.get().getModContainerById("neoforge").orElseThrow().getModInfo().getVersion().toString().equals(request.get("neoforge_version").getAsString()))throw new IllegalStateException("Exact runtime candidate/bridge/platform required");
        nativeCode(NativeHabitatLifeSupport.class,request.get("native_class_sha256").getAsString());nativeCode(HabitatLifePolicy.class,request.get("native_policy_sha256").getAsString());nativeCode(TownLifeAuthority.class,request.get("native_town_authority_sha256").getAsString());
        JsonObject owner=JsonParser.parseString(new String(bounded(owned("dashboard/artistic-owner.json"),65536),StandardCharsets.UTF_8)).getAsJsonObject();
        JsonObject active=JsonParser.parseString(new String(bounded(owned("packwiz/active.json"),65536),StandardCharsets.UTF_8)).getAsJsonObject();
        JsonObject installed=JsonParser.parseString(new String(bounded(owned("server/installed.json"),1024*1024),StandardCharsets.UTF_8)).getAsJsonObject();
        if(!owner.get("format").getAsString().equals("awft-artistic-stage:1")||!Path.of(owner.get("home").getAsString()).toRealPath().equals(home.toRealPath())
            ||!active.get("version").getAsString().equals(candidate)||!installed.get("pack_version").getAsString().equals(candidate)
            ||!active.get("pack_sha256").getAsString().equals(installed.get("pack_sha256").getAsString())||!active.get("pack_sha256").getAsString().equals(request.get("pack_sha256").getAsString()))throw new IllegalStateException("Actual owned installed pack custody differs");
        checkpoint();plan=read(reference("recipe"),planByteLimit);recipeSha=reference("recipe").get("sha256").getAsString();
        if(!plan.get("format").getAsString().equals(scaledPopulation?"awft-habitat-life-recipe:4":"awft-habitat-life-recipe:3")||plan.get("copied_entity_NBT").getAsBoolean()
            ||!plan.get("source_woodland_proposal_sha256").getAsString().equals(request.get("source_woodland_proposal_sha256").getAsString()))throw new IllegalStateException("Exact reviewed original population recipe required; no entity NBT");
        level=server.overworld();if(!plan.get("seed").getAsString().equals(Long.toString(level.getSeed()))||!Path.of(plan.get("world_path").getAsString()).toRealPath().equals(server.getWorldPath(LevelResource.ROOT).toRealPath())
            ||!plan.get("dimension").getAsString().equals("minecraft:overworld"))throw new IllegalStateException("Actual native world/dimension differs");
        JsonObject woodland=read(reference("woodland"),scaledPopulation?16*1024*1024:4*1024*1024);if(!reference("woodland").get("sha256").getAsString().equals(plan.get("source_woodland_proposal_sha256").getAsString()))throw new IllegalStateException("Actual reviewed whole-bank source artifact required; a rectangle is not authority");
        if(scaledPopulation&&(!woodland.get("format").getAsString().equals("awft-measured-south-life-extent:1")
            ||!woodland.get("checkpoint_sha256").getAsString().equals(request.get("checkpoint_sha256").getAsString())
            ||!woodland.get("eastmost_north_land_edge_measured").getAsBoolean()
            ||!woodland.get("connected_south_shore_to_cliff_foot_measured").getAsBoolean()
            ||woodland.get("eligibility_stride_metres").getAsInt()!=1))throw new IllegalStateException("Actual expanded1m habitat extent required; no old clipped coordinate fallback");
        for(JsonElement node:woodland.getAsJsonArray("bank_nodes_xz")){JsonArray pair=node.getAsJsonArray();if(pair.size()!=2||bankColumns.size()>(scaledPopulation?500000:8192))throw new IllegalStateException("Bounded actual bank source required");bankColumns.add(column(literal(pair.get(0)),literal(pair.get(1))));}if(bankColumns.isEmpty())throw new IllegalStateException("No actual dry-bank component proof");
        if(request.has("town_authority")!=plan.has("town_authority_sha256"))throw new IllegalStateException("Town source authority must be explicit in request and immutable recipe");
        if(request.has("town_authority")){
            if(!reference("town_authority").get("sha256").getAsString().equals(plan.get("town_authority_sha256").getAsString()))throw new IllegalStateException("Town authority differs from retained recipe");
            townAuthority=new TownLifeAuthority(read(reference("town_authority"),4*1024*1024),plan.get("seed").getAsString(),plan.get("world_path").getAsString(),plan.get("town_authority_source_checkpoint_sha256").getAsString(),this::read,
                ref->{Path file=owned(ref.get("path").getAsString());String complete=new String(bounded(file.resolveSibling(file.getFileName()+".complete"),128),StandardCharsets.UTF_8).strip();if(!complete.equals(ref.get("sha256").getAsString()))throw new IllegalStateException("Authored source native completion digest differs");});
        }
        namespace=UUID.fromString(plan.get("population_namespace").getAsString()).toString();
        if(!plan.get("curation_sha256").getAsString().equals(HabitatLifePolicy.CURATION_SHA256))throw new IllegalStateException("Exact reviewed16-species curation required");
        if(scaledPopulation){
            nativeCode(ScaledLifeBudget.class,request.get("native_scale_policy_sha256").getAsString());
            if(!plan.get("population_budget_sha256").getAsString().equals(reference("population_budget").get("sha256").getAsString()))
                throw new IllegalStateException("Exact reviewed scaled population budget required");
            scaleSpec=read(reference("population_budget"),128*1024);
            if(!scaleSpec.get("seed").getAsString().equals(plan.get("seed").getAsString())
                ||!scaleSpec.get("world_path").getAsString().equals(plan.get("world_path").getAsString()))throw new IllegalStateException("Scaled budget belongs to another actual world");
            JsonObject ramp=read(reference("population_ramp"),128*1024);
            scaleBudget=new ScaledLifeBudget(scaleSpec,ramp,namespace,HabitatLifePolicy.CURATION_SHA256,
                request.get("checkpoint_sha256").getAsString(),recipeSha,reference("population_budget").get("sha256").getAsString());
            if(ramp.getAsJsonArray("native_measurement_refs").size()>8)throw new IllegalStateException("Finite real ramp measurement references required");
            for(JsonElement value:ramp.getAsJsonArray("native_measurement_refs")){
                JsonObject ref=value.getAsJsonObject();byte[] measurementBytes=bounded(owned(ref.get("path").getAsString()),2*1024*1024);
                if(measurementBytes.length!=ref.get("bytes").getAsInt()||!sha(measurementBytes).equals(ref.get("sha256").getAsString()))throw new IllegalStateException("Actual reviewed ramp measurement bytes differ");
            }
            report.put("explicit_managed_population_maximum",4000);report.put("cohort_maximum",64);report.put("reviewed_ramp_ceiling",scaleBudget.ramp());
            report.put("normal_native_AI_required",true);report.put("population_scale_native_performance_acceptance",false);
        }

        if(!plan.get("r5_reservation_sha256").getAsString().equals(reference("r5_reservation").get("sha256").getAsString())||!plan.get("safety_index_sha256").getAsString().equals(reference("safety_index").get("sha256").getAsString()))throw new IllegalStateException("Exact reviewed recipe must bind its full current protection inputs");
        protection();
        JsonObject census=read(reference("uuid_census"),512*1024);
        if(!census.get("checkpoint_sha256").getAsString().equals(request.get("checkpoint_sha256").getAsString())||!census.get("recipe_sha256").getAsString().equals(recipeSha)
            ||!census.get("all_world_entity_regions_scanned").getAsBoolean())throw new IllegalStateException("Fresh complete world UUID census required");
        censusMembers.clear();for(JsonElement entry:census.getAsJsonArray("members")){JsonObject row=entry.getAsJsonObject();UUID id=UUID.fromString(row.get("uuid").getAsString());if(censusMembers.put(id,row)!=null||censusMembers.size()>cohortLimit)throw new IllegalStateException("Duplicate/unbounded census member");}
        if(operation.equals("seed")){
            JsonObject approval=read(reference("life_ready"),128*1024);
            for(String key:List.of("construction_complete","functional_commissioning_complete","visual_corrections_reviewed","habitat_plan_reviewed"))if(!approval.get(key).getAsBoolean())throw new IllegalStateException("LIFE is after construction/function/art: "+key);
            boolean approved=false;for(JsonElement value:approval.getAsJsonArray("approved_recipe_sha256s"))if(value.getAsString().equals(recipeSha))approved=true;
            if(!approval.get("checkpoint_sha256").getAsString().equals(request.get("checkpoint_sha256").getAsString())||!approved)throw new IllegalStateException("LIFE approval is not bound to this checkpoint/recipe");
            JsonObject verify=read(reference("native_habitat_verify"),512*1024);Path file=owned(reference("native_habitat_verify").get("path").getAsString());
            habitatVerify=verify;habitatPlan=read(reference("habitat_plan"),planByteLimit);
            if(!reference("habitat_plan").get("sha256").getAsString().equals(request.get("habitat_plan_sha256").getAsString()))throw new IllegalStateException("Exact actual footing/headroom plan required");
            if(!new String(bounded(file.resolveSibling(file.getFileName()+".complete"),128),StandardCharsets.UTF_8).trim().equals(reference("native_habitat_verify").get("sha256").getAsString())
                ||!verify.get("operation").getAsString().equals("verify")||verify.get("failures").getAsInt()!=0||verify.has("error")
                ||!verify.get("status").getAsString().equals("verified actual block identities, orientation, block entities and supplied inventories")
                ||!verify.get("plan_sha256").getAsString().equals(request.get("habitat_plan_sha256").getAsString())
                ||(verify.has("temporary_tickets_remaining")&&verify.get("temporary_tickets_remaining").getAsInt()!=0)
                ||(verify.has("cleanup_passed")&&!verify.get("cleanup_passed").getAsBoolean())
                ||(verify.has("cleanup_required")&&verify.get("cleanup_required").getAsBoolean())
                ||(verify.has("pending_shared_chunk_futures")&&verify.get("pending_shared_chunk_futures").getAsInt()!=0))throw new IllegalStateException("Fresh completed actual habitat block verification required");
            Instant done=Instant.parse(verify.get("finished").getAsString());if(done.isAfter(Instant.now())||done.isBefore(Instant.now().minusSeconds(1800)))throw new IllegalStateException("Actual habitat verification is stale");
        }
        action=operation;residents.clear();previews.clear();chunks.clear();pending.clear();index=ticks=spawned=preserved=0;
        JsonArray members=plan.getAsJsonArray("members");if(members.isEmpty()||members.size()>cohortLimit)throw new IllegalStateException("Finite legacy1..16 or explicitly scaled1..64 LIFE members required");
        Set<UUID> unique=new HashSet<>();int cells=0;
        for(JsonElement value:members){JsonObject row=value.getAsJsonObject();UUID uuid=UUID.fromString(row.get("uuid").getAsString());String id=row.get("entity").getAsString(),cls=row.get("native_class").getAsString(),category=row.get("native_MobCategory").getAsString();
            boolean town=row.has("town_site");if(town==row.has("bank_anchor"))throw new IllegalStateException("Exactly one typed WOODLAND or TOWN source authority required");
            Set<String> memberKeys=new HashSet<>(Set.of("uuid","entity","native_class","native_MobCategory","member_tag","feet","roam_bounds","source_group_id","preimage","habitat"));memberKeys.add(town?"town_site":"bank_anchor");
            if(!memberKeys.equals(row.keySet()))throw new IllegalStateException("No extra entity NBT, ownership, NoAI, passenger or untyped source authority admitted");
            Habitat site=parseHabitat(id,row.getAsJsonObject("habitat"),town);HabitatLifePolicy.Species species=HabitatLifePolicy.species(id,cls,category,site.kind.name());ResourceLocation key=ResourceLocation.parse(id);if(!BuiltInRegistries.ENTITY_TYPE.containsKey(key)||!unique.add(uuid))throw new IllegalStateException("Unregistered/duplicate native resident");
            EntityType<?> type=BuiltInRegistries.ENTITY_TYPE.get(key);if(!type.getCategory().getName().equals(category))throw new IllegalStateException("Actual native category differs");
            JsonArray p=row.getAsJsonArray("feet");double x=p.get(0).getAsDouble(),y=p.get(1).getAsDouble(),z=p.get(2).getAsDouble();if(town||scaledPopulation)HabitatLifePolicy.coordinateTown(x,y,z);else HabitatLifePolicy.coordinate(x,y,z);
            if(town){
                if(townAuthority==null)throw new IllegalStateException("Town resident has no explicit authenticated authored site authority");
                TownLifeAuthority.Site source=townAuthority.site(row.get("town_site").getAsString());source.member(id,site.known,x,y,z);townResidents.put(uuid,source);
                for(List<BlockPos> route:site.routes)for(BlockPos location:route)source.standing(location.getX(),location.getY(),location.getZ());
                for(BlockPos location:new BlockPos[]{site.bed,site.job,site.roof})if(location!=null)source.cell(location.getX(),location.getY(),location.getZ());
            }else{
                JsonArray anchor=row.getAsJsonArray("bank_anchor");if(anchor.size()!=2)throw new IllegalStateException("Actual connected-bank anchor required");int ax=literal(anchor.get(0)),az=literal(anchor.get(1));if(!bankColumns.contains(column(ax,az))||Math.abs(ax-Math.floor(x))>(scaledPopulation?0:16)||Math.abs(az-Math.floor(z))>(scaledPopulation?0:16))throw new IllegalStateException("Site is not tied to the actual bank component; bounding rectangle is insufficient");
            }
            if(scaledPopulation&&!town)for(int xx=site.known.minX();xx<=site.known.maxX();xx++)for(int zz=site.known.minZ();zz<=site.known.maxZ();zz++)
                if(!bankColumns.contains(column(xx,zz)))throw new IllegalStateException("Complete scaled habitat field crosses unmeasured eligible land/water");
            JsonArray box=row.getAsJsonArray("roam_bounds");AABB habitat=new AABB(box.get(0).getAsDouble(),box.get(1).getAsDouble(),box.get(2).getAsDouble(),box.get(3).getAsDouble(),box.get(4).getAsDouble(),box.get(5).getAsDouble());
            if(town||scaledPopulation){HabitatLifePolicy.coordinateTown(habitat.minX,habitat.minY,habitat.minZ);HabitatLifePolicy.coordinateTown(habitat.maxX,habitat.maxY,habitat.maxZ);}else{HabitatLifePolicy.coordinate(habitat.minX,habitat.minY,habitat.minZ);HabitatLifePolicy.coordinate(habitat.maxX,habitat.maxY,habitat.maxZ);}if(!habitat.contains(x,y,z)||habitat.getSize()>512)throw new IllegalStateException("Finite roaming habitat required");
            String tag=row.get("member_tag").getAsString();if(!tag.matches("awft_life_[a-f0-9]{24}"))throw new IllegalStateException("Exact unique member tag required");
            Map<BlockPos,BlockState> before=new LinkedHashMap<>();for(JsonElement entry:row.getAsJsonArray("preimage")){JsonArray cell=entry.getAsJsonArray();if(cell.size()!=4)throw new IllegalStateException("Four literal actual block-state cell fields required");BlockPos pos=new BlockPos(literal(cell.get(0)),literal(cell.get(1)),literal(cell.get(2)));
                if(!site.known.contains(pos.getX(),pos.getY(),pos.getZ())||before.put(pos,parse(cell.get(3).getAsString()))!=null||++cells>blockLimit)throw new IllegalStateException("Foreign/duplicate/unbounded footing/headroom witness");}
            if(before.size()!=site.known.volume()||!site.known.contains((int)Math.floor(x),(int)Math.floor(y),(int)Math.floor(z)))throw new IllegalStateException("Complete per-kind FULL known field required; no dry45-cell shortcut");
            for(int xx=site.known.minX();xx<=site.known.maxX();xx++)for(int zz=site.known.minZ();zz<=site.known.maxZ();zz++)for(int yy=site.known.minY();yy<=site.known.maxY();yy++)if(!before.containsKey(new BlockPos(xx,yy,zz)))throw new IllegalStateException("Habitat witness omits actual full-volume cells");
            residents.add(new Resident(uuid,id,tag,type,cls,category,x,y,z,habitat,site,species,Map.copyOf(before)));
            JsonObject saved=censusMembers.get(uuid);if(saved==null)throw new IllegalStateException("Census omits a requested UUID");
            if(saved.get("present").getAsBoolean()){
                JsonArray current=saved.getAsJsonArray("position");double cx=current.get(0).getAsDouble(),cy=current.get(1).getAsDouble(),cz=current.get(2).getAsDouble();if(town||scaledPopulation)HabitatLifePolicy.coordinateTown(cx,cy,cz);else HabitatLifePolicy.coordinate(cx,cy,cz);
                if(!saved.get("entity").getAsString().equals(id)||!saved.get("expected_tags_present").getAsBoolean()||!saved.get("dimension").getAsString().equals("minecraft:overworld")||!habitat.contains(cx,cy,cz))throw new IllegalStateException("Saved UUID identity or roaming habitat differs; preserve resident");
                for(int qx=(((int)Math.floor(cx))-2)>>4;qx<=(((int)Math.floor(cx))+2)>>4;qx++)for(int qz=(((int)Math.floor(cz))-2)>>4;qz<=(((int)Math.floor(cz))+2)>>4;qz++)chunks.add(new ChunkPos(qx,qz));
            }
            for(int cx=site.known.minX()>>4;cx<=site.known.maxX()>>4;cx++)for(int cz=site.known.minZ()>>4;cz<=site.known.maxZ()>>4;cz++)chunks.add(new ChunkPos(cx,cz));
        }
        if(censusMembers.size()!=residents.size()||chunks.size()>MAX_CHUNKS)throw new IllegalStateException("LIFE batch/census crosses its finite identity/chunk limits");
        if(habitatPlan!=null){
            if(!habitatPlan.get("format").getAsString().equals("awft-native-settlement:1")||!habitatPlan.get("seed").getAsString().equals(plan.get("seed").getAsString())
                ||!habitatPlan.get("world_path").getAsString().equals(plan.get("world_path").getAsString())||!CheckpointReceipt.habitatBackup(request.has("checkpoint_receipt")?request.get("checkpoint_receipt").getAsString():"",habitatPlan.get("backup_sha256").getAsString(),request.get("checkpoint_sha256").getAsString())
                ||!habitatPlan.getAsJsonArray("commands").isEmpty()||!habitatPlan.getAsJsonArray("block_entities").isEmpty())throw new IllegalStateException("Verified habitat plan identity/contents differ");
            Map<BlockPos,BlockState> verified=new HashMap<>();JsonArray palette=habitatPlan.getAsJsonArray("palette"),rows=habitatPlan.getAsJsonArray("blocks");
            if(rows.size()>blockLimit||rows.size()!=habitatVerify.get("blocks").getAsInt())throw new IllegalStateException("Exact verified habitat cell count differs");
            for(JsonElement entry:rows){JsonArray row=entry.getAsJsonArray();BlockPos pos=new BlockPos(row.get(0).getAsInt(),row.get(1).getAsInt(),row.get(2).getAsInt());if(verified.put(pos,parse(palette.get(row.get(3).getAsInt()).getAsString()))!=null)throw new IllegalStateException("Duplicate verified habitat cell");}
            for(Resident member:residents)for(var entry:member.before.entrySet())if(!entry.getValue().equals(verified.get(entry.getKey())))throw new IllegalStateException("Native verification does not cover this member's exact complete footing/body cells");
        }
        ledger=server.getWorldPath(LevelResource.ROOT).toRealPath().resolve("data/awft-life/"+namespace);
        for(Path p=ledger;p!=null&&!p.equals(server.getWorldPath(LevelResource.ROOT).toRealPath());p=p.getParent())if(Files.exists(p,LinkOption.NOFOLLOW_LINKS)&&Files.isSymbolicLink(p))throw new IllegalStateException("No linked world ledger ancestry");
        Path ancestor=ledger;while(ancestor!=null&&!Files.exists(ancestor))ancestor=ancestor.getParent();if(ancestor==null||Files.isSymbolicLink(ancestor)||!ancestor.toRealPath().startsWith(server.getWorldPath(LevelResource.ROOT).toRealPath()))throw new IllegalStateException("Ledger escaped actual world");
        if(Files.exists(ledger)){if(!Files.isDirectory(ledger,LinkOption.NOFOLLOW_LINKS))throw new IllegalStateException("Ledger is not an ordinary directory");int count=0;try(var files=Files.newDirectoryStream(ledger)){for(Path file:files)if(++count>(scaledPopulation?8016:1024)||Files.isSymbolicLink(file)||!file.getFileName().toString().matches("[a-f0-9-]{36}\\.(intent|admitted)\\.json"))throw new IllegalStateException("Unbounded/foreign world LIFE ledger");}}
        if(scaledPopulation){
            JsonObject aggregate=read(reference("habitat_census"),512*1024);
            if(!aggregate.get("format").getAsString().equals("awft-stopped-world-habitat-census:1")
                ||!aggregate.get("checkpoint_sha256").getAsString().equals(request.get("checkpoint_sha256").getAsString())
                ||!aggregate.get("recipe_sha256").getAsString().equals(recipeSha)||!aggregate.get("all_world_entity_regions_scanned").getAsBoolean())
                throw new IllegalStateException("Exact current complete stopped habitat entity census required");
            for(JsonElement value:aggregate.getAsJsonArray("tiles")){
                JsonObject row=value.getAsJsonObject();JsonArray p=row.getAsJsonArray("tile_xz");
                if(p.size()!=2||savedHabitatEntities.size()>=64)throw new IllegalStateException("Finite per-cohort habitat census required");
                int count=literal(row.get("saved_entity_count"));String key=literal(p.get(0))+"|"+literal(p.get(1));
                if(count<0||count>100000||savedHabitatEntities.put(key,count)!=null)throw new IllegalStateException("Unknown or duplicate saved habitat count");
            }
            for(Resident row:residents)if(!savedHabitatEntities.containsKey(tile(row.x,row.z)))throw new IllegalStateException("Actual habitat census omitted a requested member tile");
        }
        population(false);
        for(HabitatLifePolicy.Artifact artifact:HabitatLifePolicy.ARTIFACTS){
            Path path=owned("server/mods/"+artifact.filename());BasicFileAttributes attrs=Files.readAttributes(path,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
            if(attrs.size()!=artifact.bytes()||attrs.size()>16*1024*1024||!ModList.get().getModFileById(artifact.modId()).getFile().getFilePath().toRealPath().equals(path.toRealPath()))throw new IllegalStateException("Exact loaded species source differs: "+artifact.modId());
            artifactSources.add(new ArtifactState(artifact,path,attrs));
        }
        openArtifact();
        lease=interlock.acquire("habitat-life:"+expected,false);if(lease==null||!lease.valid())throw new IllegalStateException("Shared exclusive world-operation lease required");
        report.put("candidate",candidate);report.put("bridge",bridge);report.put("recipe_sha256",recipeSha);report.put("failures",0);report.put("members",residents.size());report.put("native_AI_behavior_acceptance",false);phase=Phase.HASH;
    }
    private static int literal(JsonElement value){try{return value.getAsBigDecimal().intValueExact();}catch(Exception error){throw new IllegalStateException("Literal finite integer coordinate required",error);}}
    private static BlockPos point(JsonElement value){JsonArray a=value.getAsJsonArray();if(a.size()!=3)throw new IllegalStateException("Three integer point coordinates required");return new BlockPos(literal(a.get(0)),literal(a.get(1)),literal(a.get(2)));}
    private static HabitatLifePolicy.Box box(JsonElement value){JsonArray a=value.getAsJsonArray();if(a.size()!=6)throw new IllegalStateException("Six literal known bounds required");return new HabitatLifePolicy.Box(literal(a.get(0)),literal(a.get(1)),literal(a.get(2)),literal(a.get(3)),literal(a.get(4)),literal(a.get(5)));}
    private static List<BlockPos> route(JsonElement value){JsonArray a=value.getAsJsonArray();if(a.isEmpty()||a.size()>64)throw new IllegalStateException("A finite actual route is required");List<BlockPos> rows=new ArrayList<>();for(JsonElement p:a)rows.add(point(p));return List.copyOf(rows);}
    private Habitat parseHabitat(String id,JsonObject value,boolean town){
        HabitatLifePolicy.Kind kind=HabitatLifePolicy.Kind.valueOf(value.get("kind").getAsString());
        Set<String> keys=new HashSet<>(Set.of("kind","known_bounds"));List<List<BlockPos>> routes=new ArrayList<>();
        HabitatLifePolicy.Box water=null;BlockPos bed=null,job=null,roof=null;
        if(kind==HabitatLifePolicy.Kind.WATER||kind==HabitatLifePolicy.Kind.SHORE){keys.add("water_bounds");water=box(value.get("water_bounds"));}
        if(kind==HabitatLifePolicy.Kind.SHORE){keys.add("shore_path");routes.add(route(value.get("shore_path")));}
        if(kind==HabitatLifePolicy.Kind.HOME){keys.addAll(Set.of("bed","job","roof","bed_path","job_path"));bed=point(value.get("bed"));job=point(value.get("job"));roof=point(value.get("roof"));routes.add(route(value.get("bed_path")));routes.add(route(value.get("job_path")));if(bed.equals(job)||!proposedBeds.add(bed)||!proposedJobs.add(job))throw new IllegalStateException("Distinct available native beds/jobs per resident required");}
        boolean shelter=kind==HabitatLifePolicy.Kind.MUSIC||id.equals("doggytalents:dog")||id.equals("cozys-improved-cats:improved_cat");
        if(shelter){keys.addAll(Set.of("roof","shelter_path"));roof=point(value.get("roof"));routes.add(route(value.get("shelter_path")));}
        if(!keys.equals(value.keySet()))throw new IllegalStateException("No traits, forged POI claims, owner, NoAI or extra habitat authority accepted");
        HabitatLifePolicy.Species p=HabitatLifePolicy.SPECIES.get(id);if(p==null)throw new IllegalStateException("Unreviewed living identity");
        HabitatLifePolicy.Box known=box(value.get("known_bounds"));HabitatLifePolicy.geometry(p,known,water,bed!=null,job!=null,routes.size(),town||scaledPopulation);
        return new Habitat(kind,known,water,List.copyOf(routes),bed,job,roof);
    }
    private static boolean sameFile(BasicFileAttributes a,BasicFileAttributes b){return a.size()==b.size()&&a.lastModifiedTime().equals(b.lastModifiedTime())&&Objects.equals(a.fileKey(),b.fileKey());}
    private void openArtifact()throws Exception{ArtifactState next=artifactSources.get(artifactIndex);hashPath=next.path;hashBefore=next.before;hashStream=Files.newInputStream(hashPath);hashDigest=MessageDigest.getInstance("SHA-256");hashed=0;}
    private static long column(int x,int z){return ((long)x<<32)|(z&0xffffffffL);}
    private void protect(int x,int z,int margin){for(int dx=-margin;dx<=margin;dx++)for(int dz=-margin;dz<=margin;dz++){if(excludedColumns.size()>200000)throw new IllegalStateException("Bounded LIFE protection index required");excludedColumns.add(column(x+dx,z+dz));}}
    private void protection()throws Exception{
        JsonObject mask=read(reference("r5_reservation"),8*1024*1024);
        if(!mask.get("seed").getAsString().equals(plan.get("seed").getAsString())||!mask.get("world_path").getAsString().equals(plan.get("world_path").getAsString())||!mask.get("construction_forbidden").getAsBoolean())throw new IllegalStateException("Exact final R5 reservation/world required");
        TreeSet<BlockPos> positions=new TreeSet<>(Comparator.<BlockPos>comparingInt(p->p.getX()).thenComparingInt(p->p.getY()).thenComparingInt(p->p.getZ()));
        for(JsonElement value:mask.getAsJsonArray("blocks")){JsonArray a=value.getAsJsonArray();positions.add(new BlockPos(literal(a.get(0)),literal(a.get(1)),literal(a.get(2))));}
        JsonArray canonical=new JsonArray();for(BlockPos p:positions){canonical.add(JSON.toJsonTree(List.of(p.getX(),p.getY(),p.getZ())));protect(p.getX(),p.getZ(),5);}
        if(!sha(JSON.toJson(canonical).getBytes(StandardCharsets.UTF_8)).equals(HabitatLifePolicy.R5_COORDINATES_SHA256))throw new IllegalStateException("Independently frozen complete2760-cell R5 footprint changed; never trim protection to fit residents");
        JsonObject safety=read(reference("safety_index"),2*1024*1024);
        if(!safety.get("format").getAsString().equals("awft-life-safety-index:1")||!safety.get("seed").getAsString().equals(plan.get("seed").getAsString())||!safety.get("world_path").getAsString().equals(plan.get("world_path").getAsString())||!safety.get("includes_current_motion_navigation_and_future_cable").getAsBoolean())throw new IllegalStateException("Current reviewed navigation/motion/cable source protection required");
        JsonArray sources=safety.getAsJsonArray("sources");if(sources.isEmpty()||sources.size()>32)throw new IllegalStateException("Finite exact protection source references required");boolean cable=false;
        for(JsonElement item:sources){JsonObject source=item.getAsJsonObject();JsonObject doc=read(source,16*1024*1024);String format=doc.get("format").getAsString();
            if(format.equals("awft-prospective-growth-exclusion:1")){JsonArray columns=doc.getAsJsonArray("all_growth_excluded_columns_xz");if(columns.isEmpty()||columns.size()>50000||doc.get("whole_crown_extra_skirt_metres").getAsInt()<5)throw new IllegalStateException("Complete explicit future cable/station mask required");for(JsonElement row:columns){JsonArray pair=row.getAsJsonArray();protect(literal(pair.get(0)),literal(pair.get(1)),0);}cable=true;}
            else if(format.equals("awft-native-settlement:1")){if(!doc.get("seed").getAsString().equals(plan.get("seed").getAsString())||!doc.get("world_path").getAsString().equals(plan.get("world_path").getAsString()))throw new IllegalStateException("Foreign mechanism/navigation protection");for(JsonElement row:doc.getAsJsonArray("blocks")){JsonArray a=row.getAsJsonArray();protect(literal(a.get(0)),literal(a.get(2)),5);}for(JsonElement row:doc.getAsJsonArray("block_entities")){BlockPos p=point(row.getAsJsonObject().get("pos"));protect(p.getX(),p.getZ(),5);}}
            else throw new IllegalStateException("Unknown safety source; do not invent AIR for an X/Z reservation");
        }
        if(!cable)throw new IllegalStateException("Retain the explicit future cable/station reservation");
        report.put("r5_protected_cells",positions.size());report.put("protected_columns_including_five_metre_skirts",excludedColumns.size());
    }
    private void classPin(Resident row,Mob mob)throws Exception{
        String name="/"+row.nativeClass.replace('.','/')+".class";byte[] raw;
        try(InputStream in=mob.getClass().getResourceAsStream(name)){if(in==null)throw new IllegalStateException("Native resident class resource missing");raw=in.readNBytes(256*1024+1);}
        String actual=sha(raw);if(raw.length>256*1024||!row.species.nativeResourceSha256().contains(actual))throw new IllegalStateException("Actual native species class resource differs: "+row.id+" observed="+actual);
    }
    private Object call(Object receiver,String method,String returnType)throws Throwable{return MethodHandles.publicLookup().findVirtual(receiver.getClass(),method,MethodType.methodType(Class.forName(returnType,false,receiver.getClass().getClassLoader()))).invoke(receiver);}
    private void factoryTraits(Resident row,Mob mob,boolean finalized)throws Exception{
        try{
            if(row.id.equals("doggytalents:dog")){Object mode=call(mob,"getMode","doggytalents.api.feature.DogMode");boolean attack=(boolean)MethodHandles.publicLookup().findVirtual(mode.getClass(),"shouldAttack",MethodType.methodType(boolean.class)).invoke(mode);if(!(mode instanceof Enum<?> e)||!e.name().equals("DOCILE")||attack)throw new IllegalStateException("Preserve ordinary ownerless DOCILE dog default; do not set mode/tame/owner");}
            if(row.id.equals("ribbits:ribbit")){Object data=call(mob,"getRibbitData","com.yungnickyoung.minecraft.ribbits.data.RibbitData");Object profession=call(data,"getProfession","com.yungnickyoung.minecraft.ribbits.data.RibbitProfession");ClassLoader loader=mob.getClass().getClassLoader();Class<?> type=Class.forName("com.yungnickyoung.minecraft.ribbits.data.RibbitProfession",false,loader),module=Class.forName("com.yungnickyoung.minecraft.ribbits.module.RibbitProfessionModule",false,loader);Object ordinary=MethodHandles.publicLookup().findStaticGetter(module,"NITWIT",type).invoke();if(!profession.equals(ordinary))throw new IllegalStateException("No fabricated Ribbit sorcerer/trader role");if(finalized&&!((BlockPos)call(mob,"getHomePosition","net.minecraft.core.BlockPos")).equals(mob.blockPosition()))throw new IllegalStateException("Native finalize did not establish actual Ribbit home");}
            if(mob instanceof Allay allay&&(!allay.getMainHandItem().isEmpty()||!allay.getInventory().isEmpty()
                ||allay.getBrain().hasMemoryValue(MemoryModuleType.LIKED_PLAYER)||allay.getBrain().hasMemoryValue(MemoryModuleType.LIKED_NOTEBLOCK_POSITION)))throw new IllegalStateException("New allay must retain ordinary empty-handed/unbonded native default");
        }catch(Throwable failure){throw new IllegalStateException("Exact native new-factory traits refused; no trait mutation attempted",failure);}
    }
    private void covered(Resident row,BlockPos point,int margin){HabitatLifePolicy.Box b=row.site.known;if(!b.contains(point.getX()-margin,point.getY()-margin,point.getZ()-margin)||!b.contains(point.getX()+margin,point.getY()+margin,point.getZ()+margin))throw new IllegalStateException("Native body/route/POI escaped complete FULL preimage");}
    private void body(Resident row,Mob mob,AABB box,boolean water){
        int minX=(int)Math.floor(box.minX),minY=(int)Math.floor(box.minY),minZ=(int)Math.floor(box.minZ),maxX=(int)Math.floor(box.maxX-1e-7),maxY=(int)Math.floor(box.maxY-1e-7),maxZ=(int)Math.floor(box.maxZ-1e-7);
        covered(row,new BlockPos(minX,minY,minZ),1);covered(row,new BlockPos(maxX,maxY,maxZ),1);
        for(int x=minX;x<=maxX;x++)for(int z=minZ;z<=maxZ;z++){if(excludedColumns.contains(column(x,z)))throw new IllegalStateException("Native resident/route overlaps protected R5, navigation or machinery");for(int y=minY;y<=maxY;y++){TownLifeAuthority.Site source=townResidents.get(row.uuid);if(source!=null)source.cell(x,y,z);var fluid=level.getFluidState(new BlockPos(x,y,z));if(water?(!fluid.is(FluidTags.WATER)||!fluid.isSource()):!fluid.isEmpty())throw new IllegalStateException("Native body air/water medium differs");}}
        if(!level.noCollision(mob,box))throw new IllegalStateException("Native model/entity collision in actual habitat");
    }
    private void footing(Resident row,Mob mob,BlockPos feet){TownLifeAuthority.Site source=townResidents.get(row.uuid);if(source!=null)source.standing(feet.getX(),feet.getY(),feet.getZ());covered(row,feet,1);BlockPos below=feet.below();if(!level.getFluidState(feet).isEmpty()||!level.getBlockState(below).isFaceSturdy(level,below,Direction.UP))throw new IllegalStateException("Actual dry supported footing required");AABB box=mob.getBoundingBox().move(feet.getX()+.5-mob.getX(),feet.getY()-mob.getY(),feet.getZ()+.5-mob.getZ());body(row,mob,box,false);}
    private void walk(Resident row,Mob mob,List<BlockPos> route){
        if(!route.getFirst().equals(mob.blockPosition()))throw new IllegalStateException("Actual route must begin at the admitted footing");BlockPos prior=null;
        for(BlockPos p:route){if(prior!=null&&(Math.abs(p.getX()-prior.getX())+Math.abs(p.getZ()-prior.getZ())!=1||Math.abs(p.getY()-prior.getY())>1))throw new IllegalStateException("Disconnected/steep actual route");footing(row,mob,p);prior=p;}
    }
    private void roof(Resident row){BlockPos p=row.site.roof;if(p==null)return;covered(row,p,1);BlockPos root=BlockPos.containing(row.x,row.y,row.z);BlockState state=level.getBlockState(p);if(Math.abs(p.getX()-root.getX())>1||Math.abs(p.getZ()-root.getZ())>1||p.getY()<root.getY()+3||p.getY()>root.getY()+8||state.getBlock() instanceof LeavesBlock||state.getCollisionShape(level,p).isEmpty()||!state.getFluidState().isEmpty())throw new IllegalStateException("Actual supported human-scale shelter roof required; no fabricated home memory");}
    private void water(Resident row){HabitatLifePolicy.Box b=row.site.water;if(b==null)return;
        for(int x=b.minX();x<=b.maxX();x++)for(int z=b.minZ();z<=b.maxZ();z++){if(excludedColumns.contains(column(x,z)))throw new IllegalStateException("Protected channel/pump/plumbing/cable water volume");for(int y=b.minY();y<=b.maxY();y++){BlockPos p=new BlockPos(x,y,z);TownLifeAuthority.Site source=townResidents.get(row.uuid);if(source!=null)source.cell(x,y,z);var fluid=level.getFluidState(p);if(!fluid.is(FluidTags.WATER)||!fluid.isSource()||!level.getBlockState(p).getCollisionShape(level,p).isEmpty())throw new IllegalStateException("Actual contiguous unblocked source-water volume required");}BlockPos surface=new BlockPos(x,b.maxY()+1,z);if(!level.getFluidState(surface).isEmpty()||!level.getBlockState(surface).getCollisionShape(level,surface).isEmpty())throw new IllegalStateException("Actual accessible water surface required; heightmaps do not prove depth");}
    }
    private void habitat(Resident row,Mob mob){
        boolean aquatic=row.site.kind==HabitatLifePolicy.Kind.WATER;body(row,mob,mob.getBoundingBox(),aquatic);water(row);
        if(aquatic){if(!row.site.water.contains(mob.blockPosition().getX(),mob.blockPosition().getY(),mob.blockPosition().getZ()))throw new IllegalStateException("Fish body outside proved swimming volume");}
        else if(row.site.kind!=HabitatLifePolicy.Kind.AIR)footing(row,mob,mob.blockPosition());
        if(row.site.kind==HabitatLifePolicy.Kind.AIR){for(int dx=-1;dx<=1;dx++)for(int dz=-1;dz<=1;dz++)for(int dy=0;dy<=2;dy++)body(row,mob,mob.getBoundingBox().move(dx,dy,dz),false);}
        for(List<BlockPos> route:row.site.routes)walk(row,mob,route);roof(row);
        if(row.site.kind==HabitatLifePolicy.Kind.SHORE){var b=row.site.water;BlockPos root=mob.blockPosition();if(root.getX()<b.minX()-3||root.getX()>b.maxX()+3||root.getZ()<b.minZ()-3||root.getZ()>b.maxZ()+3||row.site.routes.getFirst().size()<3)throw new IllegalStateException("Connected gentle shore and genuine dry exit required");}
        if(row.site.kind==HabitatLifePolicy.Kind.HOME){BlockPos bed=row.site.bed,job=row.site.job;covered(row,bed,1);covered(row,job,1);BlockState actual=level.getBlockState(bed);
            if(!(mob instanceof Villager)||!(actual.getBlock() instanceof BedBlock)||actual.getValue(BedBlock.PART)!=BedPart.HEAD||!level.getPoiManager().existsAtPosition(PoiTypes.HOME,bed)
                ||level.getPoiManager().findAll(h->h.is(PoiTypes.HOME),p->p.equals(bed),bed,0,PoiManager.Occupancy.HAS_SPACE).findFirst().isEmpty()
                ||level.getPoiManager().findAll(h->h.is(PoiTypeTags.ACQUIRABLE_JOB_SITE),p->p.equals(job),job,0,PoiManager.Occupancy.HAS_SPACE).findFirst().isEmpty())throw new IllegalStateException("Actual free native HOME and compatible job-site POIs required; no POI tickets claimed");
            if(row.site.routes.get(0).getLast().distManhattan(bed)>2||row.site.routes.get(1).getLast().distManhattan(job)>2)throw new IllegalStateException("Real body-clear routes must reach bed/job adjacency");
        }
        for(Mob other:previews)if(other!=null&&!other.getUUID().equals(row.uuid)&&other.getBoundingBox().intersects(mob.getBoundingBox()))throw new IllegalStateException("Planned residents overlap before adding either");
    }
    private JsonObject populationIdentity(){JsonObject value=new JsonObject();value.addProperty("format","awft-life-world-population:2");value.addProperty("population_namespace",namespace);value.addProperty("dimension","minecraft:overworld");value.addProperty("curation_sha256",HabitatLifePolicy.CURATION_SHA256);value.addProperty("maximum_residents",HabitatLifePolicy.WORLD_POPULATION_CAP);return value;}
    private void population(boolean create)throws Exception{
        if(scaledPopulation){scaledPopulation(create);return;}
        Path root=ledger.getParent(),authority=root.resolve("population.json");Map<String,Integer> counts=new HashMap<>();Map<BlockPos,UUID> beds=new HashMap<>(),jobs=new HashMap<>();
        if(Files.exists(root)){if(!Files.isDirectory(root,LinkOption.NOFOLLOW_LINKS)||Files.isSymbolicLink(root))throw new IllegalStateException("Ordinary actual world population directory required");int directories=0;try(var files=Files.newDirectoryStream(root)){for(Path file:files){if(++directories>3||Files.isSymbolicLink(file))throw new IllegalStateException("Bounded non-linked population namespace required");if(!file.equals(authority)&&!file.equals(ledger))throw new IllegalStateException("A different/legacy population namespace needs explicit review; never create another cohort");}}
            if(Files.exists(authority)){JsonObject value=JsonParser.parseString(new String(bounded(authority,8192),StandardCharsets.UTF_8)).getAsJsonObject();if(!value.equals(populationIdentity()))throw new IllegalStateException("Retained population authority differs; never multiply cohorts");}
            else if(Files.exists(ledger)){try(var files=Files.newDirectoryStream(ledger)){if(files.iterator().hasNext())throw new IllegalStateException("Legacy intents without population authority need explicit review");}}
        }
        if(Files.exists(ledger)){int count=0;try(var files=Files.newDirectoryStream(ledger,"*.intent.json")){for(Path path:files){if(++count>64)throw new IllegalStateException("Finite whole population intent budget exceeded");JsonObject value=JsonParser.parseString(new String(bounded(path,8192),StandardCharsets.UTF_8)).getAsJsonObject();String id=value.get("entity").getAsString();HabitatLifePolicy.species(id,value.get("native_class").getAsString(),value.get("native_category").getAsString(),value.get("habitat_kind").getAsString());if(!value.get("format").getAsString().equals("awft-life-world-intent:2")||!value.get("population_namespace").getAsString().equals(namespace))throw new IllegalStateException("Retain unknown legacy intent for review");if(value.get("habitat_kind").getAsString().equals("HOME")){UUID owner=UUID.fromString(value.get("uuid").getAsString());if(beds.put(point(value.get("planned_bed")),owner)!=null||jobs.put(point(value.get("planned_job")),owner)!=null)throw new IllegalStateException("Retained residents already share a planned POI; preserve for review");}counts.merge(id,1,Integer::sum);}}}
        for(Resident row:residents){if(row.site.bed!=null){UUID bedOwner=beds.get(row.site.bed),jobOwner=jobs.get(row.site.job);if(bedOwner!=null&&!bedOwner.equals(row.uuid)||jobOwner!=null&&!jobOwner.equals(row.uuid))throw new IllegalStateException("Do not overbook retained NPC bed/job sites before real AI claims them");}if(!hasIntent(row))counts.merge(row.id,1,Integer::sum);}HabitatLifePolicy.budget(counts);
        if(create&&!Files.exists(authority)){dataWriteAttempted=true;Files.createDirectories(root);durable(authority,populationIdentity());populationAuthoritiesWritten++;}
        report.put("whole_population_including_intents",counts.values().stream().mapToInt(Integer::intValue).sum());
    }

    private void scaleLedgerSlice()throws Exception{
        requireScaleStamp();long start=System.nanoTime();int work=0;
        while(scaleAuditCursor<scaleIntentStamps.size()&&work++<256&&System.nanoTime()-start<2_000_000L){
            ScaleIntentStamp row=scaleIntentStamps.get(scaleAuditCursor++);
            if(!sameFile(row.attributes,Files.readAttributes(row.path,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS)))
                throw new IllegalStateException("Retained immutable population intent changed during the cohort lease");
        }
        if(scaleAuditCursor==scaleIntentStamps.size()){scaleAuditComplete=true;scaleAuditCursor=0;}
    }
    private static String tile(double x,double z){return Math.floorDiv((int)Math.floor(x),32)+"|"+Math.floorDiv((int)Math.floor(z),32);}
    private void scaledCrowding(Resident member){
        if(!scaledPopulation)return;
        String key=tile(member.x,member.z);Integer saved=savedHabitatEntities.get(key);
        if(saved==null)throw new IllegalStateException("Complete actual stopped habitat census omitted this tile");
        int projected=0;for(var entry:scaleHabitats.entrySet())if(entry.getKey().substring(entry.getKey().indexOf('|')+1).equals(key))projected+=entry.getValue();
        int loaded=0,newMembers=0;
        for(Entity entity:level.getAllEntities())if(!entity.isRemoved()&&!cohortAddedUUIDs.contains(entity.getUUID())&&tile(entity.getX(),entity.getZ()).equals(key))loaded++;
        for(Resident row:residents)if(tile(row.x,row.z).equals(key))newMembers++;
        // Saved ALL entities plus projected managed intents deliberately double
        // counts some retained actors: conservative occupancy, not a fake census.
        // A second current loaded census catches later unmanaged arrivals.
        int bound=Math.max(Math.addExact(saved,projected),Math.addExact(loaded,newMembers));
        if(bound>scaleBudget.habitatCap(member.site.kind.name()))throw new IllegalStateException("Actual saved/current/conservative managed habitat occupancy exceeds reviewed local cap");
    }
    private void scaleStamp()throws Exception{
        scaleLedgerStamp=Files.exists(ledger,LinkOption.NOFOLLOW_LINKS)?Files.readAttributes(ledger,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS):null;
    }
    private void requireScaleStamp()throws Exception{
        boolean exists=Files.exists(ledger,LinkOption.NOFOLLOW_LINKS);
        if(exists!=(scaleLedgerStamp!=null)||exists&&!sameFile(scaleLedgerStamp,Files.readAttributes(ledger,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS)))
            throw new IllegalStateException("Private LIFE ledger changed outside this cohort's own durable writes");
    }
    private void scaledPopulation(boolean create)throws Exception{
        Path root=ledger.getParent(),original=root.resolve("population.json"),overlay=root.resolve("scale-budget.json");
        if(!Files.isRegularFile(original,LinkOption.NOFOLLOW_LINKS)
            ||!sha(bounded(original,8192)).equals(scaleBudget.originalIdentitySha()))
            throw new IllegalStateException("Preserve exact original world population identity; no new namespace or implicit migration");
        if(!JsonParser.parseString(new String(bounded(original,8192),StandardCharsets.UTF_8)).getAsJsonObject().equals(populationIdentity()))
            throw new IllegalStateException("Original legacy identity differs; do not rewrite it");
        if(Files.exists(overlay,LinkOption.NOFOLLOW_LINKS)
            &&!JsonParser.parseString(new String(bounded(overlay,128*1024),StandardCharsets.UTF_8)).getAsJsonObject().equals(scaleBudget.identity()))
            throw new IllegalStateException("Retained explicit scaled budget differs; no automatic authority replacement");
        if(scaleProjectionReady){
            requireScaleStamp();scaleBudget.check(scaleCounts,scaleHabitats);
            if(create&&!Files.exists(overlay,LinkOption.NOFOLLOW_LINKS)){dataWriteAttempted=true;durable(overlay,scaleBudget.identity());populationAuthoritiesWritten++;}
            return;
        }
        if(!Files.isDirectory(root,LinkOption.NOFOLLOW_LINKS)||Files.isSymbolicLink(root))throw new IllegalStateException("Ordinary retained population directory required");
        int directories=0;try(var entries=Files.newDirectoryStream(root)){for(Path path:entries){
            if(++directories>3||Files.isSymbolicLink(path)||!path.equals(original)&&!path.equals(overlay)&&!path.equals(ledger))
                throw new IllegalStateException("Preserve foreign population namespace/authority for review");
        }}
        Map<BlockPos,UUID> beds=new HashMap<>(),jobs=new HashMap<>();int retained=0;
        if(Files.exists(ledger))try(var files=Files.newDirectoryStream(ledger,"*.intent.json")){for(Path path:files){
            if(++retained>4000||Files.isSymbolicLink(path))throw new IllegalStateException("Actual retained4000 managed-intent budget exceeded");
            BasicFileAttributes stamp=Files.readAttributes(path,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
            JsonObject value=JsonParser.parseString(new String(bounded(path,8192),StandardCharsets.UTF_8)).getAsJsonObject();
            if(!sameFile(stamp,Files.readAttributes(path,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS)))throw new IllegalStateException("Retained intent changed during exact population scan");
            scaleIntentStamps.add(new ScaleIntentStamp(path,stamp));
            String id=value.get("entity").getAsString(),kind=value.get("habitat_kind").getAsString();
            HabitatLifePolicy.species(id,value.get("native_class").getAsString(),value.get("native_category").getAsString(),kind);
            if(!value.get("format").getAsString().equals("awft-life-world-intent:2")||!value.get("population_namespace").getAsString().equals(namespace))throw new IllegalStateException("Retain unknown legacy intent; never adopt another population");
            JsonArray feet=value.getAsJsonArray("feet");if(feet.size()!=3)throw new IllegalStateException("Typed retained native position required");
            scaleCounts.merge(id,1,Integer::sum);scaleHabitats.merge(ScaledLifeBudget.habitat(kind,feet.get(0).getAsDouble(),feet.get(2).getAsDouble()),1,Integer::sum);
            if(kind.equals("HOME")){
                UUID owner=UUID.fromString(value.get("uuid").getAsString());
                if(beds.put(point(value.get("planned_bed")),owner)!=null||jobs.put(point(value.get("planned_job")),owner)!=null)throw new IllegalStateException("Preserve retained bed/job claims; never overbook POIs");
            }
        }}
        for(Resident row:residents){
            if(row.site.bed!=null){UUID bedOwner=beds.get(row.site.bed),jobOwner=jobs.get(row.site.job);
                if(bedOwner!=null&&!bedOwner.equals(row.uuid)||jobOwner!=null&&!jobOwner.equals(row.uuid))throw new IllegalStateException("A retained villager already owns this planned HOME POI");}
            if(!hasIntent(row)){scaleCounts.merge(row.id,1,Integer::sum);scaleHabitats.merge(ScaledLifeBudget.habitat(row.site.kind.name(),row.x,row.z),1,Integer::sum);}
        }
        scaleBudget.check(scaleCounts,scaleHabitats);scaleProjectionReady=true;scaleStamp();
        report.put("retained_intents_at_cohort_admission",retained);
        report.put("projected_managed_population_if_cohort_complete",scaleCounts.values().stream().mapToInt(Integer::intValue).sum());
        report.put("actual_ambient_unmanaged_population_included_in_this_budget",false);
        if(create){dataWriteAttempted=true;durable(overlay,scaleBudget.identity());populationAuthoritiesWritten++;}
    }

    @SuppressWarnings({"rawtypes","unchecked"}) private static BlockState parse(String value){
        if(!value.matches("[a-z0-9_.-]+:[a-z0-9_./-]+(?:\\[[a-z0-9_=,]+\\])?"))throw new IllegalStateException("Invalid complete habitat block state");String[] parts=value.split("\\[",2);ResourceLocation id=ResourceLocation.parse(parts[0]);if(!BuiltInRegistries.BLOCK.containsKey(id))throw new IllegalStateException("Unknown native habitat block");BlockState state=BuiltInRegistries.BLOCK.get(id).defaultBlockState();Set<String> supplied=new HashSet<>();
        if(parts.length==2)for(String token:parts[1].substring(0,parts[1].length()-1).split(",")){String[] pair=token.split("=",2);Property property=state.getBlock().getStateDefinition().getProperty(pair[0]);if(pair.length!=2||property==null||!supplied.add(pair[0]))throw new IllegalStateException("Invalid native habitat property");state=state.setValue(property,(Comparable)property.getValue(pair[1]).orElseThrow());}
        if(supplied.size()!=state.getProperties().size())throw new IllegalStateException("Full native habitat properties must be supplied");return state;
    }
    private boolean ready(){for(ChunkPos c:chunks)if(level.getChunkSource().getChunkNow(c.x,c.z)==null||!level.areEntitiesLoaded(c.toLong()))return false;return true;}
    private void ticket(ChunkPos chunk,boolean add)throws Exception{level.getChunkSource().getClass().getMethod(add?"addRegionTicket":"removeRegionTicket",TicketType.class,ChunkPos.class,int.class,Object.class,boolean.class).invoke(level.getChunkSource(),TICKET,chunk,2,chunk,true);}
    private void gate(MinecraftServer server)throws Exception{
        if(!server.isSameThread()||lease==null||!lease.valid()||!server.getPlayerList().getPlayers().isEmpty()||!ready())throw new IllegalStateException("Native LIFE lease/thread/player/readiness changed");checkpoint();
        for(ArtifactState source:artifactSources){BasicFileAttributes actual=Files.readAttributes(source.path,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);if(!sameFile(actual,source.before))throw new IllegalStateException("Pinned species source changed after hashing: "+source.specification.modId());}
        Path world=server.getWorldPath(LevelResource.ROOT).toRealPath();for(Path p=ledger;p!=null&&!p.equals(world);p=p.getParent())if(Files.exists(p,LinkOption.NOFOLLOW_LINKS)&&(Files.isSymbolicLink(p)||!p.toRealPath().equals(p.toAbsolutePath().normalize())))throw new IllegalStateException("World LIFE ledger path changed/redirected");
    }
    private JsonObject intent(Resident row){JsonObject value=new JsonObject();value.addProperty("format","awft-life-world-intent:2");value.addProperty("recipe_sha256",recipeSha);value.addProperty("population_namespace",namespace);value.addProperty("uuid",row.uuid.toString());value.addProperty("entity",row.id);value.addProperty("native_class",row.nativeClass);value.addProperty("native_category",row.category);value.addProperty("member_tag",row.tag);value.addProperty("habitat_kind",row.site.kind.name());if(row.site.bed!=null){value.add("planned_bed",JSON.toJsonTree(List.of(row.site.bed.getX(),row.site.bed.getY(),row.site.bed.getZ())));value.add("planned_job",JSON.toJsonTree(List.of(row.site.job.getX(),row.site.job.getY(),row.site.job.getZ())));}value.add("feet",JSON.toJsonTree(List.of(row.x,row.y,row.z)));value.add("roam_bounds",JSON.toJsonTree(List.of(row.habitat.minX,row.habitat.minY,row.habitat.minZ,row.habitat.maxX,row.habitat.maxY,row.habitat.maxZ)));return value;}
    private boolean hasIntent(Resident row)throws Exception{Path path=ledger.resolve(row.uuid+".intent.json");if(!Files.exists(path))return false;JsonObject actual=JsonParser.parseString(new String(bounded(path,8192),StandardCharsets.UTF_8)).getAsJsonObject();if(!actual.equals(intent(row)))throw new IllegalStateException("Retained world intent differs; never replace resident");return true;}
    private boolean identity(Resident row,Entity entity){return entity instanceof Mob&&entity.level()==level&&entity.getType()==row.type&&entity.getClass().getName().equals(row.nativeClass)&&entity.getTags().contains("awft_life")&&entity.getTags().contains(row.tag)&&row.habitat.contains(entity.position());}
    private Entity current(MinecraftServer server,UUID uuid){Entity found=null;for(ServerLevel dimension:server.getAllLevels()){Entity value=dimension.getEntity(uuid);if(value!=null){if(found!=null)throw new IllegalStateException("UUID is loaded in more than one dimension; preserve both");found=value;}}return found;}
    private void flags(Mob mob,boolean newborn){boolean tame=false,owner=false;if(mob instanceof TamableAnimal pet){tame=pet.isTame();owner=pet.getOwnerUUID()!=null;}HabitatLifePolicy.live(mob.isNoAi(),mob.isPassenger()||!mob.getPassengers().isEmpty(),mob.isAlive(),newborn,tame,owner);if(mob instanceof Enemy)throw new IllegalStateException("Hostile native class refused");}
    /** Failure-only observations; do not rerun a predicate or consume random. */
    private IllegalStateException spawnRefusal(Resident row,Mob mob,String step){
        Map<String,Object> facts=new LinkedHashMap<>();
        facts.put("uuid",row.uuid.toString());facts.put("entity",row.id);facts.put("rejected_step",step);
        facts.put("spawn_type","STRUCTURE");facts.put("predicates_reexecuted_for_diagnostics",0);
        try{
            BlockPos p=mob.blockPosition();BlockState below=level.getBlockState(p.below());
            facts.put("block_position",List.of(p.getX(),p.getY(),p.getZ()));facts.put("below_state",below.toString());
            facts.put("sky_light",level.getBrightness(net.minecraft.world.level.LightLayer.SKY,p));
            facts.put("block_light",level.getBrightness(net.minecraft.world.level.LightLayer.BLOCK,p));
            facts.put("raw_brightness_zero_sky_darken",level.getRawBrightness(p,0));
            facts.put("max_local_raw_brightness",level.getMaxLocalRawBrightness(p));
            facts.put("sky_darken",level.getSkyDarken());facts.put("day_time",level.getDayTime());
            facts.put("is_day",level.isDay());facts.put("is_thundering",level.isThundering());
            facts.put("can_see_sky",level.canSeeSky(p));
            facts.put("biome",level.getBiome(p).unwrapKey().map(key->key.location().toString()).orElse("unregistered"));
            if(row.id.equals("naturalist:firefly"))facts.put("below_in_native_firefly_spawn_tag",below.is(net.minecraft.tags.TagKey.<Block>create(net.minecraft.core.registries.Registries.BLOCK,ResourceLocation.parse("naturalist:fireflies_spawnable_on"))));
        }catch(RuntimeException diagnosticError){facts.put("context_read_error",diagnosticError.toString());}
        report.put("spawn_hook_failure",facts);
        return new IllegalStateException("Ordinary native species spawn/position hook refused "+row.uuid+" at "+step);
    }
    private Mob preview(Resident row)throws Exception{
        scaledCrowding(row);
        Entity created=row.type.create(level);if(!(created instanceof Mob mob)||!created.getClass().getName().equals(row.nativeClass))throw new IllegalStateException("Native entity factory/class differs");
        mob.setUUID(row.uuid);mob.moveTo(row.x,row.y,row.z,0,0);flags(mob,true);classPin(row,mob);factoryTraits(row,mob,false);
        for(var entry:row.before.entrySet())if(!level.getBlockState(entry.getKey()).equals(entry.getValue()))throw new IllegalStateException("Actual FULL habitat preimage changed at "+entry.getKey());
        habitat(row,mob);
        if(!mob.checkSpawnObstruction(level))throw spawnRefusal(row,mob,"mob.checkSpawnObstruction");
        if(!SpawnPlacements.checkSpawnRules(row.type,level,MobSpawnType.STRUCTURE,mob.blockPosition(),level.random))throw spawnRefusal(row,mob,"SpawnPlacements.checkSpawnRules");
        if(!EventHooks.checkSpawnPosition(mob,level,MobSpawnType.STRUCTURE))throw spawnRefusal(row,mob,"EventHooks.checkSpawnPosition");
        return mob;
    }
    private Map<String,Object> observation(Resident row,Mob mob,boolean existing)throws Exception{CompoundTag tag=mob.saveWithoutId(new CompoundTag());byte[] raw=tag.toString().getBytes(StandardCharsets.UTF_8);if(raw.length>65536)throw new IllegalStateException("Native resident NBT exceeds diagnostic bound");boolean owner=mob instanceof TamableAnimal pet&&pet.getOwnerUUID()!=null;return Map.of("uuid",row.uuid.toString(),"type",BuiltInRegistries.ENTITY_TYPE.getKey(mob.getType()).toString(),"native_class",mob.getClass().getName(),"position",List.of(mob.getX(),mob.getY(),mob.getZ()),"existing_preserved",existing,"NoAI",mob.isNoAi(),"has_native_owner",owner,"native_nbt_sha256",sha(raw));}
    private static void durable(Path path,JsonObject value)throws Exception{byte[] raw=(JSON.toJson(value)+"\n").getBytes(StandardCharsets.UTF_8);if(raw.length>8192)throw new IllegalStateException("LIFE ledger row exceeds bound");try(FileChannel out=FileChannel.open(path,StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE)){ByteBuffer bytes=ByteBuffer.wrap(raw);while(bytes.hasRemaining())out.write(bytes);out.force(true);}}
    public void tick(MinecraftServer server){
        if(phase==Phase.IDLE)return;
        if(phase==Phase.CLEANUP){cleanup(true);return;}
        long start=System.nanoTime();
        try{
            if(++ticks>MAX_TICKS||!server.isSameThread()||lease==null||!lease.valid()||!server.getPlayerList().getPlayers().isEmpty())throw new IllegalStateException("LIFE lease/thread/empty-server/deadline guard refused");
            if(scaledPopulation&&scaleProjectionReady)scaleLedgerSlice();
            // No resetEmptyTime: this helper does not manufacture AI progress.
            if(phase==Phase.HASH){
                int n;do{n=hashStream.read(hashBuffer);if(n>0){hashDigest.update(hashBuffer,0,n);hashed+=n;}}while(n>=0&&System.nanoTime()-start<3_000_000L);
                if(n>=0)return;hashStream.close();hashStream=null;ArtifactState source=artifactSources.get(artifactIndex);
                if(hashed!=source.specification.bytes()||!sameFile(Files.readAttributes(hashPath,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS),source.before)||!HexFormat.of().formatHex(hashDigest.digest()).equals(source.specification.sha256()))throw new IllegalStateException("Exact pinned species JAR changed: "+source.specification.modId());
                artifactProofs.add(Map.of("mod",source.specification.modId(),"bytes",hashed,"sha256",source.specification.sha256()));
                if(++artifactIndex<artifactSources.size()){openArtifact();return;}
                checkpoint();report.put("actual_hashed_species_artifacts",List.copyOf(artifactProofs));phase=Phase.LOAD;
                for(ChunkPos c:chunks){tickets.add(c);ticket(c,true);pending.add(((worldfortwo.bridge.mixin.ChunkCacheAccess)(Object)level.getChunkSource()).awftQueueChunk(c.x,c.z,ChunkStatus.FULL,false));}return;
            }
            if(phase==Phase.LOAD){if(pending.stream().anyMatch(f->!f.isDone()))return;for(var future:pending)future.join();pending.clear();if(!ready())return;phase=Phase.VALIDATE;}
            gate(server);
            if(phase==Phase.VALIDATE){
                Resident row=residents.get(index++);Entity existing=current(server,row.uuid);boolean owned=hasIntent(row);if(censusMembers.get(row.uuid).get("present").getAsBoolean()&&!owned)throw new IllegalStateException("Stopped-world UUID exists without this retained world intent; never duplicate/adopt blindly");HabitatLifePolicy.Existing choice=HabitatLifePolicy.existing(owned,existing!=null,existing!=null&&identity(row,existing));
                if(choice==HabitatLifePolicy.Existing.PRESERVE){flags((Mob)existing,false);classPin(row,(Mob)existing);previews.add(null);}else previews.add(preview(row));
                if(index==residents.size()){index=0;phase=Phase.WORK;}return;
            }
            if(phase==Phase.WORK&&scaledPopulation&&!scaleAuditComplete)return;
            if(phase==Phase.WORK){Resident row=residents.get(index);Mob mob=previews.get(index);Entity existing=current(server,row.uuid);
                if(mob==null){if(existing==null||!identity(row,existing)||!hasIntent(row))throw new IllegalStateException("Existing native resident changed; preserve uncertainty");flags((Mob)existing,false);observed.add(observation(row,(Mob)existing,true));preserved++;}
                else if(action.equals("inspect")){if(existing!=null||hasIntent(row))throw new IllegalStateException("UUID changed during inspection");preview(row);observed.add(Map.of("uuid",row.uuid.toString(),"type",row.id,"native_class",row.nativeClass,"new_habitat_currently_admissible",true,"spawned",false));}
                else{
                    if(existing!=null||hasIntent(row))throw new IllegalStateException("UUID changed before native spawn");mob=preview(row);
                    // The fifth argument is ordinary SpawnGroupData, not a player. No fake player is constructed/passed.
                    EventHooks.finalizeMobSpawn(mob,level,level.getCurrentDifficultyAt(mob.blockPosition()),MobSpawnType.STRUCTURE,null);
                    finalized++;
                    boolean cancelled;try{cancelled=(boolean)MethodHandles.publicLookup().findVirtual(Mob.class,"isSpawnCancelled",MethodType.methodType(boolean.class)).invoke(mob);}catch(Throwable error){throw new IllegalStateException("Pinned native spawn-cancellation API unavailable",error);}
                    flags(mob,true);classPin(row,mob);factoryTraits(row,mob,true);habitat(row,mob);if(cancelled||!mob.getUUID().equals(row.uuid)||!level.noCollision(mob,mob.getBoundingBox()))throw new IllegalStateException("Native finalize event/UUID/body refused; no add");
                    if(!mob.addTag("awft_life")||!mob.addTag(row.tag))throw new IllegalStateException("Native unique population tags refused");mob.setPersistenceRequired();
                    population(true);dataWriteAttempted=true;Files.createDirectories(ledger);durable(ledger.resolve(row.uuid+".intent.json"),intent(row));intentsWritten++;
                    entityAddAttempted=true;if(!level.addFreshEntity(mob))throw new IllegalStateException("Native addFreshEntity refused; intent retained, never retry blindly");
                    spawned++;
                    if(level.getEntity(row.uuid)!=mob||!identity(row,mob))throw new IllegalStateException("Actual native entity identity readback differs");flags(mob,true);factoryTraits(row,mob,true);body(row,mob,mob.getBoundingBox(),row.site.kind==HabitatLifePolicy.Kind.WATER);
                    JsonObject admitted=intent(row);admitted.addProperty("native_added",Instant.now().toString());durable(ledger.resolve(row.uuid+".admitted.json"),admitted);if(scaledPopulation){cohortAddedUUIDs.add(row.uuid);scaleStamp();}observed.add(observation(row,mob,false));
                }
                index++;report.put("cursor",index);report.put("spawned",spawned);report.put("existing_preserved",preserved);if(index==residents.size())finish(action.equals("seed")?"native resident identities and ordinary AI flags admitted; behavior/visual/performance acceptance remains pending":"native habitats inspected; no resident or ledger writes");
            }
        }catch(Exception|LinkageError error){report.put("error",error.toString());report.put("failures",1);finish("LIFE failed; real residents/intents preserved, no replacement or automatic retry");}
        report.put("phase",phase.name());report.put("ticks",ticks);report.put("last_work_ms",(System.nanoTime()-start)/1_000_000.0);
    }
    private void finish(String status){if(outcome==null)outcome=status;phase=Phase.CLEANUP;cleanup(true);}
    private void cleanup(boolean retry){
        List<String> errors=new ArrayList<>();if(hashStream!=null)try{hashStream.close();hashStream=null;}catch(Exception error){errors.add(error.toString());}
        if(retry&&level!=null)for(ChunkPos c:List.copyOf(tickets))try{ticket(c,false);tickets.remove(c);}catch(Exception|LinkageError error){errors.add(c+": "+error);}
        pending.removeIf(CompletableFuture::isDone);
        if(tickets.isEmpty()&&pending.isEmpty()&&hashStream==null&&lease!=null)try{lease.close();lease=null;}catch(Exception error){errors.add(error.toString());}
        boolean clean=tickets.isEmpty()&&pending.isEmpty()&&hashStream==null&&lease==null;
        report.put("status",outcome);report.put("cleanup_passed",clean);report.put("cleanup_required",!clean);report.put("temporary_tickets_remaining",tickets.size());report.put("pending_shared_futures",pending.size());report.put("cleanup_errors",errors);report.put("observations",List.copyOf(observed));report.put("finished",Instant.now().toString());report.put("NoAI_or_ownership_writes",0);report.put("global_wakes",0);report.put("spawned",spawned);report.put("intents_written",intentsWritten);report.put("native_finalizations",finalized);report.put("population_authorities_written",populationAuthoritiesWritten);report.put("world_or_ledger_write_attempted",dataWriteAttempted);report.put("entity_add_attempted",entityAddAttempted);report.put("world_mutation_possible",dataWriteAttempted||entityAddAttempted);report.put("world_mutated",spawned>0||intentsWritten>0||populationAuthoritiesWritten>0);
        if(clean&&!cleanupPublished)try{NativeJournal.terminal(journal,"habitat-life",report);cleanupPublished=true;}catch(Exception error){report.put("terminal_publication_blocked",error.toString());}
        try{NativeJournal.progress(journal,"life-status.json",report);}catch(Exception error){report.put("progress_publication_warning",error.toString());}
        if(clean&&cleanupPublished){phase=Phase.IDLE;previews.clear();}
    }
    public void stopped(){if(busy())finish("server stopping; native residents and uncertainty retained");}
}
