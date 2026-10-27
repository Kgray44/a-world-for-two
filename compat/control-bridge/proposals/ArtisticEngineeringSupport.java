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

/** ORIGINAL SERVER-ONLY PROPOSAL; intentionally outside src and every frozen JAR.
 * One admitted empty-world transaction, normal pinned native APIs, no fabricated
 * power, inventory, connection NBT, train speed, passenger movement or screenshots.
 */
public final class ArtisticEngineeringSupport {
    public interface Lease extends AutoCloseable { boolean valid(); void close() throws Exception; }
    public interface Interlock { Lease acquire(String owner, boolean simulation) throws Exception; }
    private enum Phase { IDLE, HASH, READY, VERIFY, INITIALIZE, WAIT_STOP, TUBES, WATER, WAIT_MODE, WAIT_RUN, FEED, PROCESS, STOP, ASSEMBLE, WAIT_TRAIN, CLEANUP_REQUIRED }
    private static final Gson JSON=new Gson();
    private static final String PLAN_SHA="181e2191572846967c41e77bf5b406d0dddcc484488aa60d6725728ba651b199";
    private static final String MANIFEST_SHA="4339bb54a05d9c5a478b471db880c7d80dc1f6c0f25081824c7c54b75f49f408";
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
    private JsonObject request,manifest,plan,systems;
    private ServerLevel level;
    private Lease lease;
    private Phase phase=Phase.IDLE;
    private String action,outcome;
    private int ticks,phaseTicks,index,linkIndex,initIndex;
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
        for(String op:List.of("inspect","commission"))root.then(Commands.literal(op).then(Commands.argument("bundle",StringArgumentType.word())
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
        if(busy()||lease!=null||!tickets.isEmpty()||!name.matches("mill-commission-[a-f0-9]{16}")||!expected.matches("[a-f0-9]{64}")||!name.endsWith(expected.substring(0,16)))throw new IllegalStateException("Busy or invalid immutable mill request");
        if(!server.getPlayerList().getPlayers().isEmpty())throw new IllegalStateException("An explicit empty-world commissioning window is required");
        byte[] raw=readBounded(owned("dashboard/settlement/"+name+"/request.json"),128*1024);
        if(!sha(raw).equals(expected))throw new IllegalStateException("Request digest differs");
        request=JsonParser.parseString(new String(raw,StandardCharsets.UTF_8)).getAsJsonObject();
        if(!request.get("format").getAsString().equals("awft-artistic-mill-live:1")||!request.get("candidate_version").getAsString().equals(expectedCandidate)||!request.get("bridge_version").getAsString().equals(expectedBridge)||!ModList.get().getModContainerById("awft_control_bridge").orElseThrow().getModInfo().getVersion().toString().equals(expectedBridge))throw new IllegalStateException("Running candidate/bridge identity differs");
        try(InputStream in=ArtisticEngineeringSupport.class.getResourceAsStream("ArtisticEngineeringSupport.class")){
            if(in==null)throw new IllegalStateException("Running native helper unavailable");byte[] code=in.readNBytes(256*1024+1);if(code.length>256*1024||!sha(code).equals(request.get("native_class_sha256").getAsString()))throw new IllegalStateException("Running native helper differs");
        }
        if(!ref("plan").get("sha256").getAsString().equals(PLAN_SHA)||!ref("manifest").get("sha256").getAsString().equals(MANIFEST_SHA))throw new IllegalStateException("This native helper admits only the reviewed R2 dry geometry");
        manifest=readRef(ref("manifest"),2*1024*1024);plan=readRef(ref("plan"),2*1024*1024);systems=manifest.getAsJsonObject("systems");
        level=server.overworld();
        if(!Path.of(plan.get("world_path").getAsString()).toRealPath().equals(server.getWorldPath(LevelResource.ROOT).toRealPath()))throw new IllegalStateException("Actual native world custody differs");
        JsonObject checkpoint=readRef(ref("current_backup"),4096);
        if(!checkpoint.get("verified").getAsBoolean()||!checkpoint.get("sha256").getAsString().matches("[a-f0-9]{64}")||!owned(ref("current_backup").get("path").getAsString()).equals(home.resolve("dashboard/settlement/backup-receipt.json")))throw new IllegalStateException("Actual current verified backup receipt required");
        JsonObject afterPlan=readRef(ref("native_after_plan"),2*1024*1024),expectedAfter=plan.deepCopy();expectedAfter.addProperty("backup_sha256",checkpoint.get("sha256").getAsString());
        if(!afterPlan.equals(expectedAfter))throw new IllegalStateException("Fresh verification plan may change only current backup SHA, never R2 geometry or other payload");
        JsonObject beforeProof=nativeProof("native_before",BEFORE_SHA,manifest.get("preconditions").getAsInt(),false),afterProof=nativeProof("native_after",ref("native_after_plan").get("sha256").getAsString(),plan.getAsJsonArray("blocks").size(),true);
        if(Instant.parse(beforeProof.get("finished").getAsString()).isAfter(Instant.parse(afterProof.get("started").getAsString())))throw new IllegalStateException("After proof predates historical preimage admission");
        targets.clear();chunks.clear();pending.clear();hashes.clear();fillerCells.clear();kinetics.clear();pneumaticCargo.clear();chuteCargo.clear();hopperCargo.clear();tracks.clear();samples.clear();links.clear();report.clear();
        ticks=phaseTicks=index=linkIndex=initIndex=0;hash=null;outcome=null;running=mutated=fed=assembled=nativeFilterChecked=false;glueUUID=trainUUID=null;assemblyStation=null;
        JsonArray palette=plan.getAsJsonArray("palette");
        for(JsonElement entry:plan.getAsJsonArray("blocks")){JsonArray row=entry.getAsJsonArray();if(row.size()!=4)throw new IllegalStateException("Invalid geometry row");BlockPos p=pos(row.get(0).getAsInt(),row.get(1).getAsInt(),row.get(2).getAsInt());if(targets.put(p,state(palette.get(row.get(3).getAsInt()).getAsString()))!=null)throw new IllegalStateException("Duplicate geometry");chunks.add(new ChunkPos(p));}
        if(targets.size()!=7710||chunks.size()>32)throw new IllegalStateException("Unexpected finite geometry size");
        live=List.copyOf(targets.entrySet());
        for(JsonElement cell:systems.getAsJsonObject("hypertube").getAsJsonArray("native_collision_cells"))fillerCells.add(position(cell));
        for(int n=0;n<MODS.length;n++)hashes.add(new HashInput(owned("server/mods/"+MODS[n]),MOD_SHA[n],32*1024*1024));
        Set<String> requiredConfigs=new HashSet<>(Set.of("overpressure-common.toml","create_hypertube-server.toml","create-server.toml"));
        for(JsonElement source:request.getAsJsonArray("configuration")){JsonObject binding=source.getAsJsonObject();Path p=owned(binding.get("path").getAsString());String file=p.getFileName().toString();if(!p.equals(home.resolve("server/config").resolve(file))||!requiredConfigs.remove(file))throw new IllegalStateException("Exact three distinct native config bindings required");String approved=null;for(JsonElement provenance:manifest.getAsJsonArray("sources")){JsonObject row=provenance.getAsJsonObject();if(row.has("file")&&row.get("file").getAsString().equals(file))approved=row.get("sha256").getAsString();}if(approved==null||!approved.equals(binding.get("sha256").getAsString()))throw new IllegalStateException("Native configuration differs from the authored contract");hashes.add(new HashInput(p,binding.get("sha256").getAsString(),1024*1024));}
        if(!requiredConfigs.isEmpty())throw new IllegalStateException("Missing native configuration custody");
        action=operation;lease=interlock.acquire("artistic-mill:"+expected,!operation.equals("inspect"));if(lease==null||!lease.valid())throw new IllegalStateException("Exclusive shared operation lease required");
        report.put("started",Instant.now().toString());report.put("operation",operation);report.put("request_sha256",expected);report.put("plan_sha256",PLAN_SHA);report.put("native_after_plan_sha256",ref("native_after_plan").get("sha256").getAsString());report.put("historical_before_finished",beforeProof.get("finished").getAsString());report.put("current_after_finished",afterProof.get("finished").getAsString());report.put("candidate",expectedCandidate);report.put("bridge",expectedBridge);report.put("player_travel_and_train_driving","UNTESTED; no automated passenger movement");phase=Phase.HASH;
    }
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
    private void connect(int n){
        JsonObject link=systems.getAsJsonObject("hypertube").getAsJsonArray("native_links").get(n).getAsJsonObject();BlockPos a=position(link.get("from")),b=position(link.get("to"));
        ITubeConnectionEntity from=be(a,ITubeConnectionEntity.class),to=be(b,ITubeConnectionEntity.class);Direction first=Direction.SOUTH,last=Direction.NORTH;
        if(from.getConnectionInDirection(first)!=null||to.getConnectionInDirection(last)!=null||!from.getFacesConnectable().contains(first)||!to.getFacesConnectable().contains(last))throw new IllegalStateException("Preserve occupied or unsupported native tube face");
        SimpleConnection start=new SimpleConnection(a,first,from.getConnectionOffsetOnDirection(first));SimpleConnection end=new SimpleConnection(b,last.getOpposite(),-to.getConnectionOffsetOnDirection(last));BezierConnection curve=new BezierConnection(start,end);
        if(!curve.getValidation().valid()||!TubeUtils.checkBlockCollision(level,curve).valid())throw new IllegalStateException("Native Bezier/collision validation refused span");
        var points=curve.getBezierPoints(level,a);LinkedHashSet<BlockPos> writes=new LinkedHashSet<>();for(BlockPos cell:TubeCollision.occupiedVolume(points)){if(cell.equals(a)||cell.equals(b))continue;if(!fillerCells.contains(cell)||!ready(cell)||!level.getBlockState(cell).isAir()||level.getBlockEntity(cell)!=null||!level.getEntities((Entity)null,new AABB(cell)).isEmpty())throw new IllegalStateException("Native collision write escaped admitted empty air or contains an entity: "+cell);writes.add(cell);}
        // Both endpoint setters follow the exact pinned TubePlacement pattern.
        // There is no await/yield between the final air/entity scan and setters.
        mutated=true;from.setConnection(curve,first);to.setConnection(curve.getFromPos(),last);
        if(from.getConnectionInDirection(first)==null||to.getConnectionInDirection(last)==null)throw new IllegalStateException("Native reciprocal tube readback failed; partial connection retained");
        for(BlockPos cell:writes){
            if(!(level.getBlockState(cell).getBlock() instanceof TubePathBlock)||!(level.getBlockEntity(cell) instanceof TubePathBlockEntity actual)||!a.equals(actual.owner())||actual.shape().isEmpty())throw new IllegalStateException("Native tube filler/owner missing after setter; partial span retained: "+cell);
            // An unattached native BE runs the pinned box normalization without
            // touching the world. Compare voxel volumes, not list partitioning.
            TubePathBlockEntity expected=new TubePathBlockEntity(actual.getType(),cell,actual.getBlockState());expected.bind(a,TubeCollision.boxes(points,cell));
            if(expected.shape().isEmpty()||Shapes.joinIsNotEmpty(actual.shape(),expected.shape(),BooleanOp.NOT_SAME))throw new IllegalStateException("Native tube filler collision geometry differs; partial span retained: "+cell);
        }
        links.add(Map.of("from",List.of(a.getX(),a.getY(),a.getZ()),"to",List.of(b.getX(),b.getY(),b.getZ()),"uuid",curve.getUuid().toString(),"native_collision_cells",writes.size(),"native_filler_owner_and_shape_verified",true,"native_distance",curve.distance()));
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
    private void manualModes(){
        for(int z:new int[]{-991,-943}){BlockPos p=pos(1330,71,z);BlockState value=level.getBlockState(p);if(!targets.containsKey(p)||!value.is(Blocks.LEVER)||!ready(p))throw new IllegalStateException("Owned tube mode lever unavailable");if(!value.getValue(BlockStateProperties.POWERED)&&!level.setBlock(p,value.setValue(BlockStateProperties.POWERED,true),3))throw new IllegalStateException("Native manual-entry lever refused");level.updateNeighborsAt(p,value.getBlock());mutated=true;}
    }
    private boolean manualModeReady(){for(JsonElement value:systems.getAsJsonObject("hypertube").getAsJsonArray("entrances")){BlockState state=level.getBlockState(position(value));Property<?> locked=state.getBlock().getStateDefinition().getProperty("locked");if(locked==null||!state.getValue(locked).equals(Boolean.TRUE))return false;}return true;}
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
            if(phase!=Phase.HASH&&phase!=Phase.READY&&!allReady())throw new IllegalStateException("Actual simulation/BE/entity readiness lost");
            if(phase==Phase.HASH){while(System.nanoTime()-started<4_000_000L){if(index==hashes.size()){requestChunks();next(Phase.READY);break;}if(hash==null)hash=hashes.get(index);if(hash.step()){hash=null;index++;}}}
            else if(phase==Phase.READY){if(pending.stream().anyMatch(CompletableFuture::isCompletedExceptionally))throw new IllegalStateException("Native chunk request failed");if(allReady())next(Phase.VERIFY);else if(action.equals("inspect")||phaseTicks>400)throw new IllegalStateException("Native FULL/block/entity readiness not established");}
            else if(phase==Phase.VERIFY){List<Map.Entry<BlockPos,BlockState>> rows=live;while(index<rows.size()&&System.nanoTime()-started<4_000_000L){var row=rows.get(index++);BlockState actual=level.getBlockState(row.getKey());if(actual.getBlock()!=row.getValue().getBlock())throw new IllegalStateException("Native physical/air target differs at "+row.getKey());for(Property<?> property:List.of(BlockStateProperties.AXIS,BlockStateProperties.HORIZONTAL_AXIS,BlockStateProperties.FACING,BlockStateProperties.HORIZONTAL_FACING))if(row.getValue().hasProperty(property)&&actual.hasProperty(property)&&!actual.getValue(property).equals(row.getValue().getValue(property)))throw new IllegalStateException("Native orientation differs");BlockEntity entity=level.getBlockEntity(row.getKey());if(entity instanceof KineticBlockEntity k)kinetics.add(k);if(entity instanceof PneumaticTubeBlockEntity tube)pneumaticCargo.add(tube);if(entity instanceof ChuteBlockEntity chute)chuteCargo.add(chute);if(entity instanceof net.minecraft.world.level.block.entity.HopperBlockEntity hopper)hopperCargo.add(hopper);if(BuiltInRegistries.BLOCK.getKey(actual.getBlock()).toString().startsWith("railways:track_"))tracks.add(row.getKey());}if(index==rows.size()){emptyInputs();if(action.equals("inspect")){report.put("source_only_geometry_verified",targets.size());sample();finish("native dry mill inspected; no commissioning mutation");}else next(Phase.INITIALIZE);}}
            else if(phase==Phase.INITIALIZE){gate(server);if(!nativeFilterChecked){var extractor=be(component("pneumatic","extractor"),PneumaticConnectionBlockEntity.class);ItemStack filter=extractor.getFilter();if(!filter.isEmpty()&&!BuiltInRegistries.ITEM.getKey(filter.getItem()).toString().equals("create:wheat_flour"))throw new IllegalStateException("Preserve unexpected native filter");if(filter.isEmpty()){mutated=true;extractor.setFilter(new ItemStack(BuiltInRegistries.ITEM.get(ResourceLocation.parse("create:wheat_flour")),1));}nativeFilterChecked=true;}if(initIndex<kinetics.size()){mutated=true;kinetics.get(initIndex++).attachKinetics();report.put("native_kinetic_initializations",initIndex);}else if(initIndex-kinetics.size()<tracks.size()){BlockPos p=tracks.get(initIndex++-kinetics.size());mutated=true;TrackPropagator.onRailAdded(level,p,level.getBlockState(p));report.put("native_track_initializations",initIndex-kinetics.size());}else next(Phase.WAIT_STOP);}
            else if(phase==Phase.WAIT_STOP){if(stopped()){if(!level.getBlockState(component("watermill","stop_lever")).getValue(BlockStateProperties.POWERED)||!level.getBlockState(component("watermill","clutch")).getValue(BlockStateProperties.POWERED))throw new IllegalStateException("Real direct lever/clutch stop state disagrees");stations();next(Phase.TUBES);}else if(phaseTicks>400)throw new IllegalStateException("Actual stopped/kinetic readiness not established");}
            else if(phase==Phase.TUBES){gate(server);if(linkIndex<6)connect(linkIndex++);else{report.put("native_tube_links",links);next(Phase.WATER);}}
            else if(phase==Phase.WATER){gate(server);emptyInputs();for(JsonElement e:systems.getAsJsonObject("watermill").getAsJsonArray("water_sources")){BlockPos p=position(e);if(!level.getBlockState(p).isAir()||level.getBlockEntity(p)!=null||!level.getEntities((Entity)null,new AABB(p)).isEmpty())throw new IllegalStateException("Water source target is no longer empty owned air");}for(JsonElement e:systems.getAsJsonObject("watermill").getAsJsonArray("water_sources")){if(!level.setBlock(position(e),Blocks.WATER.defaultBlockState(),3))throw new IllegalStateException("Native water source placement refused");mutated=true;}manualModes();next(Phase.WAIT_MODE);}
            else if(phase==Phase.WAIT_MODE){if(manualModeReady()){report.put("native_entrances_manual_sneak_mode",true);lever(false);next(Phase.WAIT_RUN);}else if(phaseTicks>100)throw new IllegalStateException("Native locked/manual entry mode not ready; drive remains stopped");}
            else if(phase==Phase.WAIT_RUN){if(ticks%20==0)sample();boolean active=true;for(BlockPos p:driven()){KineticBlockEntity k=be(p,KineticBlockEntity.class);float minimum=level.getBlockEntity(p) instanceof ItemPumpBlockEntity?1:systems.getAsJsonObject("hypertube").getAsJsonArray("entrances").asList().stream().anyMatch(e->position(e).equals(p))?16:1;if(k.needsSpeedUpdate()||k.isOverStressed()||Math.abs(k.getSpeed())<minimum)active=false;}if(active)next(Phase.FEED);else if(phaseTicks>600)throw new IllegalStateException("Real flow/kinetic RPM/stress failed; no fabricated speed applied");}
            else if(phase==Phase.FEED){gate(server);feed();next(Phase.PROCESS);}
            else if(phase==Phase.PROCESS){if(ticks%20==0){sample();if(processed()){lever(true);next(Phase.STOP);}}if(phaseTicks>5600)throw new IllegalStateException("Actual milling/routing/press completion timed out; real inventory retained");}
            else if(phase==Phase.STOP){if(stopped()){sample();next(Phase.ASSEMBLE);}else if(phaseTicks>400)throw new IllegalStateException("Actual native stop did not settle");}
            else if(phase==Phase.ASSEMBLE){gate(server);assemble();next(Phase.WAIT_TRAIN);}
            else if(phase==Phase.WAIT_TRAIN){if(trainReady()){report.put("native_tube_links",links);report.put("actual_mill_dispatch_and_press_passed",true);finish("native stationary commissioning passed; actual passenger trips and restart acceptance pending");}else if(phaseTicks>400)throw new IllegalStateException("Native assembled carriage entity/two-bogey readback not ready; train retained");}
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
