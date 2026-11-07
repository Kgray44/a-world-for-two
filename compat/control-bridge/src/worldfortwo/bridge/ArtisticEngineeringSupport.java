package worldfortwo.bridge;

import com.google.gson.*;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.hwmods.overpressure.ItemPumpBlockEntity;
import com.hwmods.overpressure.PneumaticConnectionBlockEntity;
import com.hwmods.overpressure.PneumaticTubeBlockEntity;
import com.pedrorok.hypertube.blocks.TubePathBlock;
import com.pedrorok.hypertube.blocks.blockentities.TubePathBlockEntity;
import com.pedrorok.hypertube.core.collision.TubeCollision;
import com.pedrorok.hypertube.core.connection.BezierConnection;
import com.pedrorok.hypertube.core.connection.SimpleConnection;
import com.pedrorok.hypertube.core.connection.interfaces.IConnection;
import com.pedrorok.hypertube.core.connection.interfaces.ITubeConnectionEntity;
import com.pedrorok.hypertube.utils.TubeUtils;
import com.simibubi.create.Create;
import com.simibubi.create.content.contraptions.glue.SuperGlueEntity;
import com.simibubi.create.content.kinetics.base.KineticBlockEntity;
import com.simibubi.create.content.kinetics.millstone.MillstoneBlockEntity;
import com.simibubi.create.content.kinetics.waterwheel.WaterWheelBlockEntity;
import com.simibubi.create.content.logistics.chute.ChuteBlockEntity;
import com.simibubi.create.content.logistics.depot.DepotBlockEntity;
import com.simibubi.create.content.trains.entity.Train;
import com.simibubi.create.content.trains.station.StationBlockEntity;
import com.simibubi.create.content.trains.track.TrackPropagator;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.TicketType;
import net.minecraft.world.Container;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.block.state.properties.Property;
import net.minecraft.world.level.chunk.status.ChunkStatus;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.shapes.BooleanOp;
import net.minecraft.world.phys.shapes.Shapes;
import net.neoforged.fml.ModList;
import net.neoforged.fml.loading.FMLPaths;
import net.neoforged.neoforge.event.RegisterCommandsEvent;

import java.io.*;
import java.lang.invoke.MethodHandles;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.CompletableFuture;

/** Original, explicitly admitted server-side artistic mill commissioning.
 * One admitted empty-world transaction, normal pinned native APIs, no fabricated
 * power, inventory, connection NBT, train speed, passenger movement or screenshots.
 */
public final class ArtisticEngineeringSupport {
    public interface Lease extends AutoCloseable { boolean valid(); void close() throws Exception; }
    public interface Interlock { Lease acquire(String owner, boolean simulation) throws Exception; }
    private enum Phase { IDLE, HASH, READY, VERIFY, WAIT_STOP, WAIT_STATIONS, RESUME_ATTACH, WAIT_MODE, WAIT_RUN, FEED, PROCESS, STOP, ASSEMBLE, WAIT_TRAIN, CLEANUP_REQUIRED }
    private static final Gson JSON=new Gson();
    private static final String PLAN_SHA="ceeeabfc3ed1aee751074134edccc6de9ed3b0cf4308001203a9027e952a71af"; // source geometry signature, not a placement-plan digest
    private static final String PARTIAL_SHA="e4f627a9baa367a267537504d017893f64537841a0d608eef5b1b8b4925bc239";
    private static final String[] SOURCE_SHA={"89fa2079962dedb7888aaf62ae2f18d094c373421a80ce0f91bda23ddb415af1","747f4b1175fb6f525ecbfd5a51a7586119279f852264a383afafc88273d2973d","bae3e86205a4cd64f509ec2beba1ef3f3fc905a280fdc0c73bbdf1fa114c304b"};
    private static final String MANIFEST_SHA="f4f9bd4cd1d3bc4ff100cfe9ba417b591e7e8ede23bb1b4e3c03deb7f600d2f5";
    private static final String BEFORE_SHA="042d7717761b938bd13150aae2d58483156cd5a243bd8950c7ade247d3ee775a";
    private static final String[] MODS={"create-1.21.1-6.0.10.jar","overpressure-0.1.7.4.jar","create_hypertube-0.6.0-NEOFORGE.jar","railways-0.2.1+neoforge-mc1.21.1.jar"};
    private static final String[] MOD_SHA={"ef87fe5709f1ba1f5b8bb20a2925b5afb4669e178fd6d8bf10c167759eefe37a","9c03c26bc50c637dbe1d8b9e19e9c10218687c61d335b36588f11e54805c4cf7","7bdb8979c7ff7d3b29f7a23771b6ae4870a6dcb7ce2e4a3214fdd6059aacace8","b7636c8b1b0352ed1a130dfe67f8bb574e2fc08803ed1cda4d3ea00505193914"};
    private static final TicketType<ChunkPos> TICKET=TicketType.create("awft_artistic_mill",Comparator.comparingLong(ChunkPos::toLong));
    private static final int MAX_TICKS=7200;
    private final Path home=FMLPaths.GAMEDIR.get().resolve("..").toAbsolutePath().normalize();
    private final Path journal=home.resolve("dashboard/settlement");
    private final String expectedCandidate,expectedBridge;
    private final Interlock interlock;
    private final Map<String,Object> report=new LinkedHashMap<>();
    private final LinkedHashMap<BlockPos,BlockState> targets=new LinkedHashMap<>();
    private final LinkedHashSet<ChunkPos> chunks=new LinkedHashSet<>(),tickets=new LinkedHashSet<>();
    private final List<CompletableFuture<?>> pending=new ArrayList<>();
    private final List<HashInput> hashes=new ArrayList<>();
    private final Set<BlockPos> fillerCells=new LinkedHashSet<>();
    private final List<KineticBlockEntity> kinetics=new ArrayList<>();
    private final List<PneumaticTubeBlockEntity> pneumaticCargo=new ArrayList<>();
    private final List<ChuteBlockEntity> chuteCargo=new ArrayList<>();
    private final List<net.minecraft.world.level.block.entity.HopperBlockEntity> hopperCargo=new ArrayList<>();
    private List<Map.Entry<BlockPos,BlockState>> live=List.of();
    private final List<BlockPos> tracks=new ArrayList<>();
    private final List<Map<String,Object>> samples=new ArrayList<>(),links=new ArrayList<>();
    private JsonObject request,manifest,plan,systems,resumePartial,stockProof;
    private final Map<BlockPos,BlockState> currentTargets=new LinkedHashMap<>();
    private NativeMillResumeAttachments resume;
    private String resumeContract;
    private ServerLevel level;
    private Lease lease;
    private Phase phase=Phase.IDLE;
    private String action,outcome;
    private int ticks,phaseTicks,index,linkIndex,initIndex,dimensionWakeTicks;
    private HashInput hash;
    private boolean running,mutated,fed,assembled;
    private boolean nativeFilterChecked;
    private UUID glueUUID,trainUUID;
    private Set<UUID> priorTrains=Set.of();
    private StationBlockEntity assemblyStation;

    public ArtisticEngineeringSupport(String candidate,String bridge,Interlock interlock){
        expectedCandidate=Objects.requireNonNull(candidate);expectedBridge=Objects.requireNonNull(bridge);
        this.interlock=Objects.requireNonNull(interlock);
        if(candidate.isBlank()||bridge.isBlank())throw new IllegalArgumentException("Exact candidate and bridge required");
    }
    public boolean busy(){return phase!=Phase.IDLE;}
    public void commands(RegisterCommandsEvent event){
        var root=Commands.literal("awftmill").requires(s->s.getEntity()==null&&s.hasPermission(4));
        for(String op:List.of("inspect","resume"))root.then(Commands.literal(op).then(Commands.argument("bundle",StringArgumentType.word())
            .then(Commands.argument("sha256",StringArgumentType.word()).executes(c->{
                try{begin(c.getSource().getServer(),op,StringArgumentType.getString(c,"bundle"),StringArgumentType.getString(c,"sha256"));return 1;}
                catch(Exception|LinkageError e){report.put("error",e.getClass().getSimpleName()+": "+e.getMessage());finish("mill admission refused; no setup authority granted");throw new IllegalStateException("Mill admission refused",e);}
            }))));
        root.then(Commands.literal("status").executes(c->{c.getSource().sendSuccess(()->Component.literal(JSON.toJson(report)),false);return 1;}));
        root.then(Commands.literal("cancel").executes(c->{finish("cancelled; completed native work retained for explicit review");return 1;}));
        event.getDispatcher().register(root);
    }
    private static String sha(byte[] bytes)throws Exception{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));}
    private static byte[] readBounded(Path p,int cap)throws Exception{
        if(!Files.isRegularFile(p)||Files.size(p)<1||Files.size(p)>cap)throw new IllegalStateException("Unbounded evidence input");
        try(InputStream in=Files.newInputStream(p)){byte[] raw=in.readNBytes(cap+1);if(raw.length>cap)throw new IllegalStateException("Evidence grew");return raw;}
    }
    private Path owned(String path)throws Exception{
        Path relative=Path.of(path);if(relative.isAbsolute()||path.indexOf('\\')>=0||path.indexOf(':')>=0)throw new IllegalArgumentException("Home-relative evidence only");
        for(Path part:relative)if(part.toString().equals("..")||part.toString().equals("."))throw new IllegalArgumentException("No parent traversal");
        Path file=home.resolve(relative).normalize();
        for(Path p=file;!p.equals(home)&&p!=null;p=p.getParent())if(Files.isSymbolicLink(p)||!p.toRealPath().equals(p.toAbsolutePath().normalize()))throw new IllegalStateException("Linked/redirected evidence refused");
        if(!file.toRealPath().startsWith(home.toRealPath()))throw new IllegalStateException("Evidence escaped owned home");return file;
    }
    private JsonObject readRef(JsonObject ref,int cap)throws Exception{
        Path p=owned(ref.get("path").getAsString());byte[] raw=readBounded(p,cap);
        if(raw.length!=ref.get("bytes").getAsInt()||!sha(raw).equals(ref.get("sha256").getAsString()))throw new IllegalStateException("Immutable evidence digest/size differs");
        return JsonParser.parseString(new String(raw,StandardCharsets.UTF_8)).getAsJsonObject();
    }
    private JsonObject ref(String name){return request.getAsJsonObject(name);}
    private JsonObject nativeProof(String key,String expected,int count,boolean current)throws Exception{
        JsonObject proof=readRef(ref(key),512*1024);JsonObject marker=ref(key+"_complete");
        Path path=owned(marker.get("path").getAsString()),original=owned(ref(key).get("path").getAsString());
        byte[] complete=readBounded(path,128);
        if(!path.equals(original.resolveSibling(original.getFileName()+".complete"))||!sha(complete).equals(marker.get("sha256").getAsString())||!new String(complete,StandardCharsets.UTF_8).trim().equals(ref(key).get("sha256").getAsString()))throw new IllegalStateException("Exact native completion marker required");
        if(!proof.get("operation").getAsString().equals("verify")||!proof.get("plan_sha256").getAsString().equals(expected)||proof.get("failures").getAsInt()!=0||proof.get("blocks").getAsInt()!=count||proof.has("error")||!proof.has("finished")||!proof.get("status").getAsString().equals("verified actual block identities, orientation, block entities and supplied inventories"))throw new IllegalStateException("Zero-failure immutable native proof required");
        Instant started=Instant.parse(proof.get("started").getAsString()),finished=Instant.parse(proof.get("finished").getAsString()),now=Instant.now();
        if(started.isAfter(finished)||finished.isAfter(now))throw new IllegalStateException("Future/unordered native measurement refused");
        if(current&&finished.isBefore(now.minusSeconds(1200)))throw new IllegalStateException("Reverify actual current geometry immediately before commissioning");
        return proof;
    }
    private void begin(MinecraftServer server,String operation,String name,String expected)throws Exception{
        if(busy()||lease!=null||!tickets.isEmpty()||!name.matches("mill-resume-[a-f0-9]{16}")||!expected.matches("[a-f0-9]{64}")||!name.endsWith(expected.substring(0,16)))throw new IllegalStateException("Busy or invalid immutable mill request");
        if(!server.getPlayerList().getPlayers().isEmpty())throw new IllegalStateException("An explicit empty-world commissioning window is required");
        byte[] raw=readBounded(owned("dashboard/settlement/"+name+"/request.json"),128*1024);
        if(!sha(raw).equals(expected))throw new IllegalStateException("Request digest differs");
        request=JsonParser.parseString(new String(raw,StandardCharsets.UTF_8)).getAsJsonObject();if(!request.get("intended_operation").getAsString().equals(operation))throw new IllegalStateException("Request is not admitted for this operation");
        if(!request.get("format").getAsString().equals("awft-artistic-mill-resume:1")||!request.get("candidate_version").getAsString().equals(expectedCandidate)||!request.get("bridge_version").getAsString().equals(expectedBridge)||!ModList.get().getModContainerById("awft_control_bridge").orElseThrow().getModInfo().getVersion().toString().equals(expectedBridge))throw new IllegalStateException("Running candidate/bridge identity differs");
        try(InputStream in=ArtisticEngineeringSupport.class.getResourceAsStream("ArtisticEngineeringSupport.class")){
            if(in==null)throw new IllegalStateException("Running native helper unavailable");byte[] code=in.readNBytes(256*1024+1);if(code.length>256*1024||!sha(code).equals(request.get("native_class_sha256").getAsString()))throw new IllegalStateException("Running native helper differs");
        }
        if(!ref("manifest").get("sha256").getAsString().equals(MANIFEST_SHA))throw new IllegalStateException("Reviewed original systems manifest required");
        manifest=readRef(ref("manifest"),2*1024*1024);systems=manifest.getAsJsonObject("systems");plan=readRef(ref("plan"),2*1024*1024);level=server.overworld();
        Path world=server.getWorldPath(LevelResource.ROOT).toRealPath(),stage=Path.of("D:/A World for Two/staging/world-tests").toRealPath();
        if(!world.startsWith(stage)||world.getNameCount()!=stage.getNameCount()+3||!world.getParent().getFileName().toString().equals("world")||!world.getFileName().toString().equals("RosewaterArtistic")||server.getPort()!=25575||!world.equals(Path.of(plan.get("world_path").getAsString()).toRealPath())||!home.toRealPath().equals(world.getParent().getParent()))throw new IllegalStateException("Exact private RosewaterArtistic world/home ancestry required");
        JsonArray sources=request.getAsJsonArray("source_plans");if(sources.size()!=3)throw new IllegalStateException("All three exact mill sources required");Map<BlockPos,BlockState> authored=new LinkedHashMap<>();
        for(int n=0;n<3;n++){JsonObject r=sources.get(n).getAsJsonObject();if(!r.get("sha256").getAsString().equals(SOURCE_SHA[n]))throw new IllegalStateException("Reviewed mill source differs");JsonObject source=readRef(r,2*1024*1024);if(!source.get("seed").equals(plan.get("seed"))||!source.get("world_path").equals(plan.get("world_path")))throw new IllegalStateException("Source world differs");authored.putAll(states(source));}
        if(authored.size()!=7941||!authored.equals(states(plan)))throw new IllegalStateException("Complete R3 plus94 canonical geometry required; never replay placement");
        JsonObject checkpoint=readRef(ref("current_backup"),4096);
        if(!checkpoint.get("verified").getAsBoolean()||!checkpoint.get("sha256").getAsString().matches("[a-f0-9]{64}")||!owned(ref("current_backup").get("path").getAsString()).equals(home.resolve("dashboard/settlement/backup-receipt.json")))throw new IllegalStateException("Actual current verified backup receipt required");
        JsonObject afterPlan=readRef(ref("native_after_plan"),2*1024*1024);currentTargets.clear();currentTargets.putAll(states(afterPlan));
        if(!afterPlan.get("backup_sha256").equals(checkpoint.get("sha256"))||!afterPlan.get("world_path").equals(plan.get("world_path"))||!afterPlan.get("seed").equals(plan.get("seed"))||!currentTargets.keySet().equals(authored.keySet()))throw new IllegalStateException("Fresh complete same-world exact-target preimage required");
        JsonObject afterProof=nativeProof("native_after",ref("native_after_plan").get("sha256").getAsString(),7941,true);
        if(!ref("native_partial").get("sha256").getAsString().equals(PARTIAL_SHA))throw new IllegalStateException("Exact retained original WAIT_MODE failure required");resumePartial=completedRef("native_partial");
        resumeContract=sha(("awft:mill-resume:1\n"+world+"\n"+PLAN_SHA+"\n"+PARTIAL_SHA+"\n"+MANIFEST_SHA+"\n").getBytes(StandardCharsets.UTF_8));stockProof=null;
        try(InputStream code=NativeMillResumeAttachments.class.getResourceAsStream("NativeMillResumeAttachments.class")){if(code==null||!sha(code.readNBytes(256*1024+1)).equals(request.get("native_attachment_class_sha256").getAsString()))throw new IllegalStateException("Exact compiled native attachment collaborator required");}
        if(operation.equals("resume")){JsonObject inspection=completedRef("native_inventory_inspection");Instant measured=Instant.parse(inspection.get("finished").getAsString());if(inspection.has("error")||!inspection.get("operation").getAsString().equals("inspect")||!inspection.get("cleanup_passed").getAsBoolean()||inspection.get("remaining_owned_tickets").getAsInt()!=0||!inspection.get("candidate").getAsString().equals(expectedCandidate)||!inspection.get("bridge").getAsString().equals(expectedBridge)||!inspection.get("native_class_sha256").equals(request.get("native_class_sha256"))||!inspection.get("native_attachment_class_sha256").equals(request.get("native_attachment_class_sha256"))||!inspection.get("native_after_plan_sha256").equals(ref("native_after_plan").get("sha256"))||!inspection.get("resume_contract_sha256").getAsString().equals(resumeContract)||!inspection.get("current_backup_sha256").equals(checkpoint.get("sha256"))||Instant.parse(inspection.get("started").getAsString()).isBefore(Instant.parse(afterProof.get("finished").getAsString()))||measured.isAfter(Instant.now())||measured.isBefore(Instant.now().minusSeconds(1200)))throw new IllegalStateException("Fresh exact current-candidate native inventory inspection required");stockProof=inspection.getAsJsonObject("native_resume_stock");}
        targets.clear();chunks.clear();pending.clear();hashes.clear();fillerCells.clear();kinetics.clear();pneumaticCargo.clear();chuteCargo.clear();hopperCargo.clear();tracks.clear();samples.clear();links.clear();report.clear();
        ticks=phaseTicks=index=linkIndex=initIndex=dimensionWakeTicks=0;hash=null;outcome=null;running=mutated=fed=assembled=nativeFilterChecked=false;glueUUID=trainUUID=null;assemblyStation=null;
        JsonArray palette=plan.getAsJsonArray("palette");
        for(JsonElement entry:plan.getAsJsonArray("blocks")){JsonArray row=entry.getAsJsonArray();if(row.size()!=4)throw new IllegalStateException("Invalid geometry row");BlockPos p=pos(row.get(0).getAsInt(),row.get(1).getAsInt(),row.get(2).getAsInt());if(targets.put(p,state(palette.get(row.get(3).getAsInt()).getAsString()))!=null)throw new IllegalStateException("Duplicate geometry");chunks.add(new ChunkPos(p));}
        if(targets.size()!=7941||chunks.size()>32)throw new IllegalStateException("Unexpected finite geometry size");
        live=List.copyOf(targets.entrySet());
        for(JsonElement cell:systems.getAsJsonObject("hypertube").getAsJsonArray("native_collision_cells"))fillerCells.add(position(cell));
        for(int n=0;n<MODS.length;n++)hashes.add(new HashInput(owned("server/mods/"+MODS[n]),MOD_SHA[n],32*1024*1024));
        Set<String> requiredConfigs=new HashSet<>(Set.of("overpressure-common.toml","create_hypertube-server.toml","create-server.toml"));
        for(JsonElement source:request.getAsJsonArray("configuration")){JsonObject binding=source.getAsJsonObject();Path p=owned(binding.get("path").getAsString());String file=p.getFileName().toString();if(!p.equals(home.resolve("server/config").resolve(file))||!requiredConfigs.remove(file))throw new IllegalStateException("Exact three distinct native config bindings required");String approved=null;for(JsonElement provenance:manifest.getAsJsonArray("sources")){JsonObject row=provenance.getAsJsonObject();if(row.has("file")&&row.get("file").getAsString().equals(file))approved=row.get("sha256").getAsString();}if(approved==null||(!approved.equals(binding.get("sha256").getAsString())&&!approveOwnerChain128(file,approved,binding)))throw new IllegalStateException("Native configuration differs from the authored contract");hashes.add(new HashInput(p,binding.get("sha256").getAsString(),1024*1024));}
        if(!requiredConfigs.isEmpty())throw new IllegalStateException("Missing native configuration custody");
        if(request.has("owner_create_chain_limit_delta")&&!report.containsKey("owner_create_chain_limit_delta"))throw new IllegalStateException("Unused owner delta refused");
        action=operation;lease=interlock.acquire("artistic-mill:"+expected,!operation.equals("inspect"));if(lease==null||!lease.valid())throw new IllegalStateException("Exclusive shared operation lease required");
        report.put("started",Instant.now().toString());report.put("operation",operation);report.put("request_sha256",expected);report.put("plan_sha256",ref("plan").get("sha256").getAsString());report.put("native_after_plan_sha256",ref("native_after_plan").get("sha256").getAsString());report.put("historical_partial_finished",resumePartial.get("finished").getAsString());report.put("current_backup_sha256",checkpoint.get("sha256").getAsString());report.put("resume_contract_sha256",resumeContract);report.put("source_geometry_sha256",PLAN_SHA);report.put("native_class_sha256",request.get("native_class_sha256").getAsString());report.put("native_attachment_class_sha256",request.get("native_attachment_class_sha256").getAsString());report.put("current_after_finished",afterProof.get("finished").getAsString());report.put("candidate",expectedCandidate);report.put("bridge",expectedBridge);report.put("player_travel_and_train_driving","UNTESTED; no automated passenger movement");phase=Phase.HASH;
    }
    private JsonObject completedRef(String key)throws Exception{JsonObject value=readRef(ref(key),512*1024);Path file=owned(ref(key).get("path").getAsString()),marker=owned(ref(key+"_complete").get("path").getAsString());byte[] raw=readBounded(marker,128);if(!marker.equals(file.resolveSibling(file.getFileName()+".complete"))||!sha(raw).equals(ref(key+"_complete").get("sha256").getAsString())||!new String(raw,StandardCharsets.UTF_8).trim().equals(ref(key).get("sha256").getAsString()))throw new IllegalStateException("Exact immutable native completion marker required");return value;}
    private static Map<BlockPos,BlockState> states(JsonObject source){if(source.getAsJsonArray("commands").size()!=0)throw new IllegalStateException("No construction commands in resume evidence");Map<BlockPos,BlockState> result=new LinkedHashMap<>();JsonArray palette=source.getAsJsonArray("palette");for(JsonElement entry:source.getAsJsonArray("blocks")){JsonArray row=entry.getAsJsonArray();if(row.size()!=4)throw new IllegalStateException("Exact source row required");BlockPos p=pos(row.get(0).getAsInt(),row.get(1).getAsInt(),row.get(2).getAsInt());if(result.put(p,state(palette.get(row.get(3).getAsInt()).getAsString()))!=null)throw new IllegalStateException("Duplicate source/preimage target");}return result;}
    private void validateRetainedStructure(BlockPos p,BlockState source,BlockState actual){
        if(source.isAir()&&actual.getBlock() instanceof TubePathBlock&&fillerCells.contains(p))return;
        if(source.isAir()&&actual.is(Blocks.WATER)&&p.getX()>=1306&&p.getX()<=1308&&p.getY()>=68&&p.getY()<=73&&p.getZ()>=-1001&&p.getZ()<=-999)return;
        if(source.getBlock()!=actual.getBlock())throw new IllegalStateException("Unrelated source identity/air drift at "+p);
        boolean entrance=p.getX()==1331&&p.getY()==71&&(p.getZ()==-991||p.getZ()==-943),modeLever=p.getX()==1330&&p.getY()==71&&(p.getZ()==-991||p.getZ()==-943);
        for(Property<?> property:source.getProperties()){String key=property.getName();if(entrance&&Set.of("locked","powered","connected","open","has_block_in_front").contains(key)||modeLever&&key.equals("powered"))continue;if(!source.getValue(property).equals(actual.getValue(property)))throw new IllegalStateException("Retained structural state differs at "+p+" "+key);}
    }
    private boolean approveOwnerChain128(String file,String original,JsonObject binding)throws Exception{
        if(!file.equals("create-server.toml")||!original.equals("36216a05f3ed63106ba587c8c24ed6315385829e7f3dae695dcf545aba41a270")||!binding.get("sha256").getAsString().equals("240471ba821bd0f5208ea11960d79aacdfeb25a40c6a689a2d6518d689d890ac"))return false;
        if(!request.has("owner_create_chain_limit_delta"))return false;
        JsonObject delta=request.getAsJsonObject("owner_create_chain_limit_delta");
        if(!delta.keySet().equals(Set.of("before","receipt")))throw new IllegalStateException("Closed exact owner config delta required");
        JsonObject before=delta.getAsJsonObject("before"),receiptRef=delta.getAsJsonObject("receipt");
        if(!before.get("path").getAsString().equals("staging/owner-chain-conveyor128-1793230774200615600/create-server-before.toml")||!before.get("sha256").getAsString().equals("36216a05f3ed63106ba587c8c24ed6315385829e7f3dae695dcf545aba41a270")
            ||!receiptRef.get("path").getAsString().equals("staging/owner-chain-conveyor128-1793230774200615600/receipt.json")||!receiptRef.get("sha256").getAsString().equals("2d1d800d95cbb249587fe8d00d8794a425da4e4f2952ccc74196cfe7936ecc20"))throw new IllegalStateException("Exact retained owner provenance required");
        byte[] originalBytes=readBounded(owned(before.get("path").getAsString()),65536);
        if(originalBytes.length!=before.get("bytes").getAsInt()||!sha(originalBytes).equals("36216a05f3ed63106ba587c8c24ed6315385829e7f3dae695dcf545aba41a270"))throw new IllegalStateException("Retained complete original Create config differs");
        JsonObject approval=readRef(receiptRef,4096);
        if(!approval.get("format").getAsString().equals("awft-owner-create-chain-limit:1")||!approval.get("only_changed_setting").getAsString().equals("kinetics.maxChainConveyorLength")
            ||approval.get("old_value").getAsInt()!=32||approval.get("new_value").getAsInt()!=128
            ||!approval.get("before_sha256").getAsString().equals("36216a05f3ed63106ba587c8c24ed6315385829e7f3dae695dcf545aba41a270")||!approval.get("after_sha256").getAsString().equals("240471ba821bd0f5208ea11960d79aacdfeb25a40c6a689a2d6518d689d890ac"))throw new IllegalStateException("Exact approved32-to128 delta required");
        report.put("owner_create_chain_limit_delta",Map.of("before_sha256","36216a05f3ed63106ba587c8c24ed6315385829e7f3dae695dcf545aba41a270","after_sha256","240471ba821bd0f5208ea11960d79aacdfeb25a40c6a689a2d6518d689d890ac","all_other_config_bytes_preserved",true,"runtime_effective_value_observed",false));
        return true;
    }
    private void requireHydraulics(){for(JsonElement e:systems.getAsJsonObject("watermill").getAsJsonArray("water_sources")){BlockState value=level.getBlockState(position(e));if(!value.is(Blocks.WATER)||!value.getFluidState().isSource())throw new IllegalStateException("Original real hydraulic source missing; resume never replaces water");}ItemStack filter=be(component("pneumatic","extractor"),PneumaticConnectionBlockEntity.class).getFilter();if(filter.isEmpty()||filter.getCount()!=1||!BuiltInRegistries.ITEM.getKey(filter.getItem()).toString().equals("create:wheat_flour"))throw new IllegalStateException("Original native flour filter missing/changed; resume never initializes it");report.put("existing_native_filter_preserved",true);}
    private static BlockPos pos(int x,int y,int z){if(x<1300||x>1340||y<59||y>85||z< -1020||z> -928)throw new IllegalArgumentException("Position outside reviewed mill reserve");return new BlockPos(x,y,z);}
    private static BlockPos position(JsonElement e){JsonArray a=e.getAsJsonArray();if(a.size()!=3)throw new IllegalArgumentException("Exact position required");return pos(a.get(0).getAsInt(),a.get(1).getAsInt(),a.get(2).getAsInt());}
    private BlockPos component(String system,String key){return position(systems.getAsJsonObject(system).get(key));}
    @SuppressWarnings({"unchecked","rawtypes"}) private static BlockState state(String text){
        String[] parts=text.split("\\[",2);var id=ResourceLocation.parse(parts[0]);if(!BuiltInRegistries.BLOCK.containsKey(id))throw new IllegalStateException("Unknown native block");BlockState value=BuiltInRegistries.BLOCK.get(id).defaultBlockState();
        if(parts.length==2){for(String item:parts[1].substring(0,parts[1].length()-1).split(",")){String[] pair=item.split("=",2);Property property=value.getBlock().getStateDefinition().getProperty(pair[0]);if(property==null)throw new IllegalStateException("Unknown native property");value=value.setValue(property,(Comparable)property.getValue(pair[1]).orElseThrow());}}return value;
    }
    private boolean ready(BlockPos p){long chunk=ChunkPos.asLong(p);return level.getChunkSource().getChunkNow(p.getX()>>4,p.getZ()>>4)!=null&&BridgePhaseGate.simulationReady(level.getChunkSource().isPositionTicking(chunk),level.isPositionEntityTicking(p),level.areEntitiesLoaded(chunk),false);}
    private boolean allReady(){for(ChunkPos c:chunks)if(!ready(c.getMiddleBlockPosition(68)))return false;return true;}
    private void ticket(ChunkPos chunk,boolean add)throws Exception{level.getChunkSource().getClass().getMethod(add?"addRegionTicket":"removeRegionTicket",TicketType.class,ChunkPos.class,int.class,Object.class,boolean.class).invoke(level.getChunkSource(),TICKET,chunk,2,chunk,true);}
    private void requestChunks()throws Exception{if(action.equals("inspect"))return;for(ChunkPos c:chunks){tickets.add(c);ticket(c,true);pending.add(((worldfortwo.bridge.mixin.ChunkCacheAccess)(Object)level.getChunkSource()).awftQueueChunk(c.x,c.z,ChunkStatus.FULL,false));}}
    private void gate(MinecraftServer server)throws Exception{if(lease==null||!lease.valid()||!server.getPlayerList().getPlayers().isEmpty()||!allReady())throw new IllegalStateException("Empty-world ownership/readiness changed");readRef(ref("current_backup"),4096);}
    private <T> T be(BlockPos p,Class<T> type){if(!targets.containsKey(p)||!ready(p)||!type.isInstance(level.getBlockEntity(p)))throw new IllegalStateException("Native component missing/unready at "+p);return type.cast(level.getBlockEntity(p));}
    private static int count(Container inventory,String id){int total=0;for(int n=0;n<inventory.getContainerSize();n++){ItemStack stack=inventory.getItem(n);if(!stack.isEmpty()&&(id==null||BuiltInRegistries.ITEM.getKey(stack.getItem()).toString().equals(id)))total+=stack.getCount();}return total;}
    private boolean stopped(){for(BlockPos p:driven()){KineticBlockEntity k=be(p,KineticBlockEntity.class);if(k.needsSpeedUpdate()||k.isOverStressed()||Math.abs(k.getSpeed())>.001)return false;}return true;}
    private List<BlockPos> driven(){List<BlockPos> p=new ArrayList<>(List.of(component("watermill","millstone"),component("watermill","press"),component("pneumatic","pump")));for(JsonElement e:systems.getAsJsonObject("hypertube").getAsJsonArray("entrances"))p.add(position(e));return p;}
    private void emptyInputs(){
        for(BlockPos p:List.of(component("watermill","grain_chest"),component("pneumatic","output_chest")))if(count(be(p,Container.class),null)!=0)throw new IllegalStateException("Active inventory must be empty");
        MillstoneBlockEntity mill=be(component("watermill","millstone"),MillstoneBlockEntity.class);for(var handler:List.of(mill.inputInv,mill.outputInv))for(int slot=0;slot<handler.getSlots();slot++)if(!handler.getStackInSlot(slot).isEmpty())throw new IllegalStateException("Native mill inventory busy");
        for(PneumaticTubeBlockEntity tube:pneumaticCargo)if(tube.getMovingItem()!=null)throw new IllegalStateException("Preserve existing pneumatic cargo");for(ChuteBlockEntity chute:chuteCargo)if(!chute.getItem().isEmpty())throw new IllegalStateException("Preserve chute cargo");for(var hopper:hopperCargo)if(count(hopper,null)!=0)throw new IllegalStateException("Preserve hopper cargo");
        if(!be(component("watermill","depot"),DepotBlockEntity.class).getHeldItem().isEmpty())throw new IllegalStateException("Preserve depot cargo");
    }
    private void lever(boolean stop){BlockPos p=component("watermill","stop_lever"),clutch=component("watermill","clutch");BlockState s=level.getBlockState(p);if(!s.is(Blocks.LEVER)||!p.north().equals(clutch)||!s.hasProperty(BlockStateProperties.POWERED)||!ready(p))throw new IllegalStateException("Exact direct wall lever custody lost");if(s.getValue(BlockStateProperties.POWERED)!=stop&&!level.setBlock(p,s.setValue(BlockStateProperties.POWERED,stop),3))throw new IllegalStateException("Native lever state update refused");level.updateNeighborsAt(p,s.getBlock());level.updateNeighborsAt(clutch,level.getBlockState(clutch).getBlock());mutated=true;running=!stop;}
    private void stations(){for(JsonElement e:systems.getAsJsonObject("railway").getAsJsonArray("stations")){JsonObject row=e.getAsJsonObject();StationBlockEntity station=be(position(row.get("position")),StationBlockEntity.class);if(!station.edgePoint.hasValidTrack()||!station.edgePoint.getGlobalPosition().equals(position(row.get("target_track")))||station.edgePoint.getTargetDirection()!=(row.get("target_direction_positive").getAsBoolean()?Direction.AxisDirection.POSITIVE:Direction.AxisDirection.NEGATIVE)||station.getStation()==null)throw new IllegalStateException("Real station graph/target/direction not ready");}}
    private boolean stationsReady(){
        boolean ready=true;List<Map<String,Object>> witnesses=new ArrayList<>();
        for(JsonElement e:systems.getAsJsonObject("railway").getAsJsonArray("stations")){
            JsonObject row=e.getAsJsonObject();BlockPos pos=position(row.get("position")),target=position(row.get("target_track"));
            StationBlockEntity station=be(pos,StationBlockEntity.class);
            boolean track=station.edgePoint.hasValidTrack(),location=station.edgePoint.getGlobalPosition().equals(target);
            boolean direction=station.edgePoint.getTargetDirection()==(row.get("target_direction_positive").getAsBoolean()?Direction.AxisDirection.POSITIVE:Direction.AxisDirection.NEGATIVE);
            boolean graphLocation=track && station.edgePoint.determineGraphLocation()!=null,point=station.getStation()!=null;
            witnesses.add(Map.of("position",List.of(pos.getX(),pos.getY(),pos.getZ()),"valid_track",track,
                "actual_target",List.of(station.edgePoint.getGlobalPosition().getX(),station.edgePoint.getGlobalPosition().getY(),station.edgePoint.getGlobalPosition().getZ()),
                "target_matches",location,"actual_direction",station.edgePoint.getTargetDirection().name(),"direction_matches",direction,
                "graph_location_ready",graphLocation,"station_point_ready",point));
            ready &= track && location && direction && graphLocation && point;
        }
        report.put("station_readiness",witnesses);report.put("native_track_graphs",Create.RAILWAYS.trackNetworks.size());return ready;
    }
    private static Map<String,Object> tubeConnectionWitness(IConnection connection){
        if(connection==null)return Map.of("kind","empty");
        Map<String,Object> row=new LinkedHashMap<>();row.put("native_class",connection.getClass().getName());
        // Describe only stored native endpoints. Never follow a foreign pointer
        // or resolve arbitrary connections while reporting why a face is refused.
        if(connection instanceof SimpleConnection simple)row.put("stored_endpoint",tubeEndpoint(simple));
        else if(connection instanceof BezierConnection curve){row.put("from",tubeEndpoint(curve.getFromPos()));row.put("to",tubeEndpoint(curve.getToPos()));row.put("uuid",String.valueOf(curve.getUuid()));}
        else row.put("kind","unknown; preserved");
        return row;
    }
    private static Map<String,Object> tubeEndpoint(SimpleConnection endpoint){
        if(endpoint==null)return Map.of("kind","missing");
        Map<String,Object> row=new LinkedHashMap<>();BlockPos p=endpoint.pos();
        row.put("position",p==null?"unknown":List.of(p.getX(),p.getY(),p.getZ()));row.put("direction",endpoint.direction()==null?"unknown":endpoint.direction().getSerializedName());
        row.put("offset",Float.isFinite(endpoint.offset())?endpoint.offset():"non-finite; preserved");return row;
    }
    private Map<String,Object> tubeFaceWitness(BlockPos position,ITubeConnectionEntity entity,Direction face,List<Direction> available,IConnection occupied){
        var connections=entity.getConnections();Map<String,Object> row=new LinkedHashMap<>();
        row.put("position",List.of(position.getX(),position.getY(),position.getZ()));row.put("requested_face",face.getSerializedName());
        row.put("actual_block_state",level.getBlockState(position).toString());row.put("native_class",entity.getClass().getName());
        row.put("native_available_faces",available.stream().map(Direction::getSerializedName).toList());row.put("requested_face_supported",available.contains(face));
        row.put("requested_face_connection",tubeConnectionWitness(occupied));row.put("native_connection_count",connections.size());
        row.put("native_connections",connections.stream().limit(8).map(ArtisticEngineeringSupport::tubeConnectionWitness).toList());
        row.put("connections_truncated",connections.size()>8);return row;
    }
    private static float nativeFloat(KineticBlockEntity entity,String member)throws Exception{
        // Exact single-member resolution avoids enumerating unrelated client
        // signatures and does not create a network while taking a measurement.
        try{return (float)MethodHandles.privateLookupIn(KineticBlockEntity.class,MethodHandles.lookup()).findGetter(KineticBlockEntity.class,member,float.class).invoke(entity);}
        catch(Exception e){throw e;}catch(Error error){throw error;}catch(Throwable checked){throw new IllegalStateException("Native kinetic witness failed",checked);}
    }
    private void sample()throws Exception{List<Map<String,Object>> rows=new ArrayList<>();for(BlockPos p:driven()){KineticBlockEntity k=be(p,KineticBlockEntity.class);rows.add(Map.of("position",List.of(p.getX(),p.getY(),p.getZ()),"rpm",k.getSpeed(),"needs_update",k.needsSpeedUpdate(),"overstressed",k.isOverStressed(),"capacity",nativeFloat(k,"capacity"),"stress",nativeFloat(k,"stress")));}samples.add(Map.of("game_time",level.getGameTime(),"kinetics",rows));}
    private void feed(){
        emptyInputs();Container stock=be(component("watermill","starter_chest"),Container.class),grain=be(component("watermill","grain_chest"),Container.class);DepotBlockEntity depot=be(component("watermill","depot"),DepotBlockEntity.class);
        int wheat=-1,iron=-1;for(int n=0;n<stock.getContainerSize();n++){ItemStack stack=stock.getItem(n);String id=BuiltInRegistries.ITEM.getKey(stack.getItem()).toString();if(id.equals("minecraft:wheat")&&stack.getCount()==16)wheat=n;if(id.equals("minecraft:iron_ingot")&&stack.getCount()>=1)iron=n;}
        if(wheat<0||iron<0||!grain.getItem(0).isEmpty())throw new IllegalStateException("Exact native demonstration stock/empty inputs required");
        // Transfer real supplied goods; never generate wheat, flour or sheets.
        ItemStack wheatStack=stock.removeItem(wheat,16);grain.setItem(0,wheatStack);ItemStack ingot=stock.removeItem(iron,1);depot.setHeldItem(ingot);stock.setChanged();grain.setChanged();depot.setChanged();fed=mutated=true;report.put("actual_test_input",Map.of("wheat",16,"iron_ingot",1));
    }
    private boolean processed(){
        Container grain=be(component("watermill","grain_chest"),Container.class),out=be(component("pneumatic","output_chest"),Container.class);MillstoneBlockEntity mill=be(component("watermill","millstone"),MillstoneBlockEntity.class);
        boolean idle=count(grain,null)==0&&mill.inputInv.getStackInSlot(0).isEmpty()&&mill.timer<=0;for(int slot=0;slot<mill.outputInv.getSlots();slot++){ItemStack stack=mill.outputInv.getStackInSlot(slot);if(!stack.isEmpty()&&BuiltInRegistries.ITEM.getKey(stack.getItem()).toString().equals("create:wheat_flour"))idle=false;}for(PneumaticTubeBlockEntity tube:pneumaticCargo)if(tube.getMovingItem()!=null)idle=false;for(ChuteBlockEntity chute:chuteCargo)if(!chute.getItem().isEmpty())idle=false;for(var hopper:hopperCargo)if(count(hopper,null)!=0)idle=false;
        int flour=count(out,"create:wheat_flour");ItemStack pressed=be(component("watermill","depot"),DepotBlockEntity.class).getHeldItem();boolean sheet=!pressed.isEmpty()&&BuiltInRegistries.ITEM.getKey(pressed.getItem()).toString().equals("create:iron_sheet")&&pressed.getCount()==1;
        report.put("actual_dispatch_flour",flour);report.put("actual_dispatch_other_items",count(out,null)-flour);report.put("native_input_and_transit_empty",idle);report.put("actual_pressed_iron_sheet",sheet);
        return idle&&flour>=16&&count(out,null)==flour&&sheet;
    }
    private void assemble(){
        stations();JsonObject rail=systems.getAsJsonObject("railway");BlockPos lo=position(rail.get("carriage_glue_min")),hi=position(rail.get("carriage_glue_max"));
        if(!lo.equals(pos(1335,70,-993))||!hi.equals(pos(1337,75,-985)))throw new IllegalStateException("Exact carriage-only glue custody differs");AABB box=SuperGlueEntity.span(lo,hi);
        if(!level.getEntities((Entity)null,box.inflate(.25)).isEmpty())throw new IllegalStateException("Preserve entity occupying carriage assembly envelope");
        glueUUID=UUID.nameUUIDFromBytes(("awft:mill-glue:"+PLAN_SHA).getBytes(StandardCharsets.UTF_8));for(ServerLevel world:level.getServer().getAllLevels())if(world.getEntity(glueUUID)!=null)throw new IllegalStateException("Existing native glue UUID requires explicit review");
        SuperGlueEntity glue=new SuperGlueEntity(level,box);glue.setUUID(glueUUID);if(!level.addFreshEntity(glue))throw new IllegalStateException("Native owned glue insertion refused");mutated=true;
        JsonObject row=rail.getAsJsonArray("stations").get(0).getAsJsonObject();assemblyStation=be(position(row.get("position")),StationBlockEntity.class);
        if(!assemblyStation.tryEnterAssemblyMode())throw new IllegalStateException("Native station declined assembly mode; owned glue retained");assemblyStation.refreshAssemblyInfo();
        if(assemblyStation.getAssemblyDirection()!=Direction.SOUTH||!assemblyStation.isValidBogeyOffset(2)||!assemblyStation.isValidBogeyOffset(8))throw new IllegalStateException("Native assembly direction/bogey offsets refused");
        priorTrains=new HashSet<>(Create.RAILWAYS.trains.keySet());assemblyStation.assemble(UUID.fromString(rail.get("native_owner_uuid").getAsString()));
        Set<UUID> created=new HashSet<>(Create.RAILWAYS.trains.keySet());created.removeAll(priorTrains);if(created.size()!=1)throw new IllegalStateException("Native assembly did not produce exactly one train; inspect station exception without recreating");trainUUID=created.iterator().next();assembled=true;
        if(!assemblyStation.exitAssemblyMode())throw new IllegalStateException("Native station did not exit assembly mode; actual train retained");
    }
    private boolean trainReady(){Train train=Create.RAILWAYS.trains.get(trainUUID);if(train==null||train.invalid||train.derailed||train.carriages.size()!=1||!train.doubleEnded||Math.abs(train.speed)>.001||!train.carriages.getFirst().isOnTwoBogeys())return false;var entity=train.carriages.getFirst().anyAvailableEntity();if(entity==null||entity.isRemoved()||entity.level()!=level||entity.getContraption()==null||entity.getContraption().getSeats().size()!=3)return false;report.put("actual_train_uuid",train.id.toString());report.put("actual_carriage_entity_uuid",entity.getUUID().toString());report.put("native_carriage_seats",entity.getContraption().getSeats().size());report.put("native_carriage_blocks",entity.getContraption().getBlocks().size());report.put("native_two_bogeys",true);report.put("native_double_ended",true);report.put("native_stationary_speed",train.speed);report.put("actual_train_assembled",true);return true;}
    private void next(Phase value){phase=value;phaseTicks=0;index=0;}
    public void tick(MinecraftServer server){
        if(phase==Phase.IDLE||phase==Phase.CLEANUP_REQUIRED)return;long started=System.nanoTime();
        try{
            if(lease==null||!lease.valid()||!server.getPlayerList().getPlayers().isEmpty())throw new IllegalStateException("Commissioning lease/empty-world gate lost");
            if(++ticks>MAX_TICKS)throw new IllegalStateException("Finite native commissioning window expired");phaseTicks++;
            // Temporary region tickets make holders simulation-ready but do
            // not satisfy ServerLevel's saved forced-chunk idle branch. Wake
            // native entity/BE ticks only within this admitted finite run;
            // read-only inspect, idle and failed cleanup never keep it awake.
            if(action.equals("resume")){level.resetEmptyTime();report.put("native_dimension_empty_timer_resets",++dimensionWakeTicks);}
            if(phase!=Phase.HASH&&phase!=Phase.READY&&!allReady())throw new IllegalStateException("Actual simulation/BE/entity readiness lost");
            if(phase==Phase.HASH){while(System.nanoTime()-started<4_000_000L){if(index==hashes.size()){requestChunks();next(Phase.READY);break;}if(hash==null)hash=hashes.get(index);if(hash.step()){hash=null;index++;}}}
            else if(phase==Phase.READY){if(pending.stream().anyMatch(CompletableFuture::isCompletedExceptionally))throw new IllegalStateException("Native chunk request failed");if(allReady())next(Phase.VERIFY);else if(action.equals("inspect")||phaseTicks>400)throw new IllegalStateException("Native FULL/block/entity readiness not established");}
            else if(phase==Phase.VERIFY){List<Map.Entry<BlockPos,BlockState>> rows=live;while(index<rows.size()&&System.nanoTime()-started<4_000_000L){var row=rows.get(index++);BlockState actual=level.getBlockState(row.getKey());if(!actual.equals(currentTargets.get(row.getKey())))throw new IllegalStateException("Fresh exact native preimage changed at "+row.getKey());validateRetainedStructure(row.getKey(),row.getValue(),actual);for(Property<?> property:List.of(BlockStateProperties.AXIS,BlockStateProperties.HORIZONTAL_AXIS,BlockStateProperties.FACING,BlockStateProperties.HORIZONTAL_FACING))if(row.getValue().hasProperty(property)&&actual.hasProperty(property)&&!actual.getValue(property).equals(row.getValue().getValue(property)))throw new IllegalStateException("Native orientation differs");BlockEntity entity=level.getBlockEntity(row.getKey());if(entity instanceof KineticBlockEntity k)kinetics.add(k);if(entity instanceof PneumaticTubeBlockEntity tube)pneumaticCargo.add(tube);if(entity instanceof ChuteBlockEntity chute)chuteCargo.add(chute);if(entity instanceof net.minecraft.world.level.block.entity.HopperBlockEntity hopper)hopperCargo.add(hopper);if(BuiltInRegistries.BLOCK.getKey(actual.getBlock()).toString().startsWith("railways:track_"))tracks.add(row.getKey());}if(index==rows.size()){emptyInputs();resume=new NativeMillResumeAttachments(level,lease,fillerCells,resumePartial,stockProof,resumeContract,action.equals("inspect"),()->mutated=true,report);links.addAll(resume.retainedLinks());requireHydraulics();if(action.equals("inspect")){resume.preflight(stopped(),stationsReady());report.put("source_and_current_preimage_targets_verified",targets.size());sample();finish("native retained mill inspected; no resume mutation");}else next(Phase.WAIT_STOP);}}
            else if(phase==Phase.WAIT_STOP){if(stopped()){if(!level.getBlockState(component("watermill","stop_lever")).getValue(BlockStateProperties.POWERED)||!level.getBlockState(component("watermill","clutch")).getValue(BlockStateProperties.POWERED))throw new IllegalStateException("Real direct lever/clutch stop state disagrees");next(Phase.WAIT_STATIONS);}else if(phaseTicks>400)throw new IllegalStateException("Actual stopped/kinetic readiness not established");}
            else if(phase==Phase.WAIT_STATIONS){if(stationsReady()){resume.preflight(stopped(),true);next(Phase.RESUME_ATTACH);}else if(phaseTicks>400)throw new IllegalStateException("Actual station graph/target/direction readiness not established; native witness retained");}
            else if(phase==Phase.RESUME_ATTACH){gate(server);if(!stopped()||!stationsReady())throw new IllegalStateException("Actual stopped stations changed before attachment");requireHydraulics();if(index<2)resume.installOne(index++);else{resume.notifyManual();next(Phase.WAIT_MODE);}}
            else if(phase==Phase.WAIT_MODE){if(resume.manualReady()){report.put("native_entrances_manual_sneak_mode",true);lever(false);next(Phase.WAIT_RUN);}else if(phaseTicks>100)throw new IllegalStateException("Native locked/manual entry mode not ready; drive remains stopped");}
            else if(phase==Phase.WAIT_RUN){if(ticks%20==0)sample();boolean active=true;for(BlockPos p:driven()){KineticBlockEntity k=be(p,KineticBlockEntity.class);float minimum=level.getBlockEntity(p) instanceof ItemPumpBlockEntity?1:systems.getAsJsonObject("hypertube").getAsJsonArray("entrances").asList().stream().anyMatch(e->position(e).equals(p))?16:1;if(k.needsSpeedUpdate()||k.isOverStressed()||Math.abs(k.getSpeed())<minimum)active=false;}if(active)next(Phase.FEED);else if(phaseTicks>600)throw new IllegalStateException("Real flow/kinetic RPM/stress failed; no fabricated speed applied");}
            else if(phase==Phase.FEED){gate(server);resume.intent("feed");feed();resume.completed("feed");next(Phase.PROCESS);}
            else if(phase==Phase.PROCESS){if(ticks%20==0){sample();if(processed()){lever(true);next(Phase.STOP);}}if(phaseTicks>5600)throw new IllegalStateException("Actual milling/routing/press completion timed out; real inventory retained");}
            else if(phase==Phase.STOP){if(stopped()){sample();next(Phase.ASSEMBLE);}else if(phaseTicks>400)throw new IllegalStateException("Actual native stop did not settle");}
            else if(phase==Phase.ASSEMBLE){gate(server);resume.intent("assembly");assemble();resume.completed("assembly");next(Phase.WAIT_TRAIN);}
            else if(phase==Phase.WAIT_TRAIN){if(trainReady()){report.put("native_tube_links",links);report.put("actual_mill_dispatch_and_press_passed",true);finish("native resumed stationary commissioning passed; actual passenger trips and restart acceptance pending");}else if(phaseTicks>400)throw new IllegalStateException("Native assembled carriage entity/two-bogey readback not ready; train retained");}
            report.put("phase",phase.name());report.put("ticks",ticks);report.put("world_mutated",mutated);report.put("actual_wheat_feed_performed",fed);report.put("kinetic_samples",samples);report.put("max_work_ms",Math.max(((Number)report.getOrDefault("max_work_ms",0d)).doubleValue(),(System.nanoTime()-started)/1e6));
        }catch(Exception|LinkageError error){report.put("error",error.getClass().getSimpleName()+": "+error.getMessage());finish("native commissioning stopped; partial native state preserved for review");}
    }
    private void finish(String status){
        if(phase==Phase.IDLE&&lease==null&&tickets.isEmpty())return;if(outcome==null)outcome=status;List<String> cleanup=new ArrayList<>();
        if(running&&level!=null&&lease!=null&&lease.valid())try{lever(true);}catch(Exception|LinkageError e){cleanup.add("Cannot verify/stop owned drive: "+e);}
        try{if(hash!=null)hash.close();hash=null;for(HashInput input:hashes)input.close();}catch(Exception e){cleanup.add("Hash handle: "+e);}
        for(ChunkPos c:new ArrayList<>(tickets))try{ticket(c,false);tickets.remove(c);}catch(Exception|LinkageError e){cleanup.add("Ticket "+c+": "+e);}
        if(tickets.isEmpty()&&hash==null&&lease!=null)try{lease.close();lease=null;}catch(Exception e){cleanup.add("Shared lease: "+e);}
        boolean clean=tickets.isEmpty()&&lease==null&&hash==null&&!running;report.put("remaining_owned_tickets",tickets.size());report.put("cleanup_errors",cleanup);report.put("cleanup_passed",clean);report.put("world_mutated",mutated);report.put("train_created",assembled);report.put("native_tube_links",links);report.put("kinetic_samples",samples);report.put("finished",Instant.now().toString());report.put("status",clean?outcome:"cleanup_required; owned references retained");
        if(trainUUID!=null)report.put("actual_train_uuid",trainUUID.toString());if(glueUUID!=null)report.put("owned_glue_uuid",glueUUID.toString());
        try{NativeJournal.terminal(journal,"artistic-mill",report);}catch(Exception e){report.put("receipt_error",e.toString());}
        phase=clean?Phase.IDLE:Phase.CLEANUP_REQUIRED;
    }
    public void stop(){finish("server stop; completed native work and all inventories preserved");}
    private static final class HashInput implements AutoCloseable{
        final Path path;final String expected;final int cap;InputStream in;final MessageDigest digest;long bytes;
        HashInput(Path path,String expected,int cap)throws Exception{this.path=path;this.expected=expected;this.cap=cap;digest=MessageDigest.getInstance("SHA-256");if(!expected.matches("[a-f0-9]{64}")||Files.size(path)<1||Files.size(path)>cap)throw new IllegalStateException("Unbounded/unidentified native dependency");}
        boolean step()throws Exception{if(in==null)in=Files.newInputStream(path);byte[] b=new byte[32768];int n=in.read(b);if(n<0){close();if(!HexFormat.of().formatHex(digest.digest()).equals(expected))throw new IllegalStateException("Actual native dependency/config digest differs: "+path.getFileName());return true;}bytes+=n;if(bytes>cap)throw new IllegalStateException("Native dependency grew beyond bound");digest.update(b,0,n);return false;}
        public void close()throws IOException{if(in!=null){in.close();in=null;}}
    }
}
