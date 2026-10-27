package worldfortwo.bridge;

import com.google.gson.*;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.simibubi.create.content.kinetics.base.KineticBlockEntity;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.CompletableFuture;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.*;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.*;
import net.minecraft.world.level.chunk.status.ChunkStatus;
import net.minecraft.world.level.material.Fluids;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.AABB;
import net.neoforged.fml.ModList;
import net.neoforged.fml.loading.FMLPaths;
import net.neoforged.neoforge.event.RegisterCommandsEvent;

/** Real pump fill and physical gate commissioning, only in the owned empty stage.
 * Never seeds header/cascade water or writes kinetic/fluid/inventory NBT. The
 * Create pump normally deadheads at a full header; gravity drives the cascades.
 */
public final class NativeFountainSupport {
    private enum Phase { IDLE, LOAD, GEOMETRY, DRY, FILL, STOP, RESTART, CLEANUP }
    private record Target(BlockPos pos,BlockState state){}
    private static final Gson JSON=new Gson();
    private static final BlockPos WHEEL=new BlockPos(1145,66,-1130),PUMP=new BlockPos(1140,66,-1129),
        WHEEL_SOURCE=new BlockPos(1145,69,-1131),HEADER=new BlockPos(1138,73,-1129),
        LEVER=new BlockPos(1142,66,-1125),PISTON=new BlockPos(1138,73,-1126),PORT=new BlockPos(1138,73,-1128),
        OPEN_PLUG=new BlockPos(1138,73,-1127),INTAKE=new BlockPos(1139,65,-1129);
    private static final List<BlockPos> JETS=List.of(new BlockPos(1135,68,-1128),new BlockPos(1141,68,-1128),
        new BlockPos(1138,68,-1131),new BlockPos(1138,68,-1125));
    private static final TicketType<ChunkPos> TICKET=TicketType.create("awft_fountain",Comparator.comparingLong(ChunkPos::toLong));
    private final Path home=FMLPaths.GAMEDIR.get().resolve("..").toAbsolutePath().normalize(),journal=home.resolve("dashboard/settlement");
    private final String candidate,bridge;
    private final ArtisticEngineeringSupport.Interlock interlock;
    private ArtisticEngineeringSupport.Lease lease;
    private final Set<ChunkPos> chunks=new LinkedHashSet<>(),tickets=new LinkedHashSet<>();
    private final List<CompletableFuture<?>> pending=new ArrayList<>();
    private final List<Target> targets=new ArrayList<>();
    private final Map<String,Object> report=new LinkedHashMap<>();
    private final List<Map<String,Object>> observations=new ArrayList<>();
    private ServerLevel level;private JsonObject request;private BlockState nativePlug;
    private Phase phase=Phase.IDLE;private String operation,outcome;
    private int ticks,phaseTicks,index,stable,wakeTicks;private boolean seeded,failed,terminalPublished;
    public NativeFountainSupport(String candidate,String bridge,ArtisticEngineeringSupport.Interlock interlock){this.candidate=candidate;this.bridge=bridge;this.interlock=interlock;}
    public boolean busy(){return phase!=Phase.IDLE;}
    public void commands(RegisterCommandsEvent event){
        var root=Commands.literal("awftfountain").requires(s->s.getEntity()==null&&s.hasPermission(4));
        for(String action:List.of("inspect","commission"))root.then(Commands.literal(action)
            .then(Commands.argument("bundle",StringArgumentType.word()).then(Commands.argument("sha256",StringArgumentType.word()).executes(c->{
                if(busy())return 0;
                try{begin(c.getSource().getServer(),action,StringArgumentType.getString(c,"bundle"),StringArgumentType.getString(c,"sha256"));return 1;}
                catch(Exception|LinkageError error){report.put("error",error.toString());finish("fountain admission refused; no hydraulic acceptance",true);throw new IllegalStateException("Fountain admission refused",error);}
            }))));
        root.then(Commands.literal("status").executes(c->{c.getSource().sendSuccess(()->Component.literal(JSON.toJson(report)),false);return 1;}));
        root.then(Commands.literal("cancel").executes(c->{if(!busy())return 0;finish("cancelled; partial actual hydraulic state retained",true);return 1;}));
        event.getDispatcher().register(root);
    }
    private static String sha(byte[] raw)throws Exception{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(raw));}
    private static byte[] bounded(Path p,int maximum)throws Exception{
        if(!Files.isRegularFile(p)||Files.isSymbolicLink(p)||Files.size(p)<1||Files.size(p)>maximum)throw new IllegalStateException("Finite regular evidence required");
        try(InputStream in=Files.newInputStream(p)){byte[] raw=in.readNBytes(maximum+1);if(raw.length>maximum)throw new IllegalStateException("Evidence exceeded allocation");return raw;}
    }
    private Path owned(String name)throws Exception{
        Path relative=Path.of(name);if(relative.isAbsolute()||name.contains(":")||name.contains("\\"))throw new IllegalStateException("Owned home-relative evidence required");
        for(Path part:relative)if(Set.of(".","..").contains(part.toString()))throw new IllegalStateException("Evidence traversal refused");
        Path p=home.resolve(relative).normalize();if(!p.startsWith(home)||!p.toRealPath().startsWith(home.toRealPath()))throw new IllegalStateException("Foreign evidence refused");
        for(Path q=p;q!=null&&!q.equals(home);q=q.getParent())if(Files.isSymbolicLink(q)||!q.toRealPath().equals(q))throw new IllegalStateException("Redirected evidence refused");return p;
    }
    private JsonObject read(String name,int bound)throws Exception{return JsonParser.parseString(new String(bounded(owned(name),bound),StandardCharsets.UTF_8)).getAsJsonObject();}
    private JsonObject reference(String name,int maximum)throws Exception{
        JsonObject ref=request.getAsJsonObject(name);byte[] raw=bounded(owned(ref.get("path").getAsString()),maximum);
        if(raw.length!=ref.get("bytes").getAsInt()||!sha(raw).equals(ref.get("sha256").getAsString()))throw new IllegalStateException("Exact evidence bytes differ");return JsonParser.parseString(new String(raw,StandardCharsets.UTF_8)).getAsJsonObject();
    }
    private void begin(MinecraftServer server,String action,String bundle,String expected)throws Exception{
        if(busy()||lease!=null||!tickets.isEmpty()||!pending.isEmpty()||!server.isSameThread())throw new IllegalStateException("Busy or off-thread");
        operation=action;report.clear();observations.clear();targets.clear();chunks.clear();ticks=phaseTicks=index=stable=wakeTicks=0;seeded=failed=terminalPublished=false;outcome=null;
        report.put("operation",action);report.put("started",Instant.now().toString());
        if(!bundle.matches("fountain-[a-f0-9]{16}")||!expected.matches("[a-f0-9]{64}")||!bundle.endsWith(expected.substring(0,16)))throw new IllegalStateException("Immutable fountain binding required");
        if(server.getPort()!=25575||!server.getPlayerList().getPlayers().isEmpty())throw new IllegalStateException("Empty private artistic stage required");
        byte[] raw=bounded(owned("dashboard/settlement/"+bundle+"/request.json"),65536);if(!sha(raw).equals(expected))throw new IllegalStateException("Request hash differs");request=JsonParser.parseString(new String(raw,StandardCharsets.UTF_8)).getAsJsonObject();
        JsonObject owner=read("dashboard/artistic-owner.json",65536),active=read("packwiz/active.json",65536),installed=read("server/installed.json",1024*1024);
        if(!request.get("format").getAsString().equals("awft-native-fountain:1")||!request.get("candidate").getAsString().equals(candidate)||!request.get("bridge").getAsString().equals(bridge)
            ||!ModList.get().getModContainerById("awft_control_bridge").orElseThrow().getModInfo().getVersion().toString().equals(bridge)
            ||!owner.get("format").getAsString().equals("awft-artistic-stage:1")||!Path.of(owner.get("home").getAsString()).toRealPath().equals(home.toRealPath())
            ||!active.get("version").getAsString().equals(candidate)||!installed.get("pack_version").getAsString().equals(candidate)
            ||!active.get("pack_sha256").getAsString().equals(installed.get("pack_sha256").getAsString())
            ||!active.get("pack_sha256").equals(request.get("pack_sha256")))throw new IllegalStateException("Actual owned candidate custody differs");
        try(InputStream in=NativeFountainSupport.class.getResourceAsStream("NativeFountainSupport.class")){if(in==null||!sha(in.readNBytes(256*1024)).equals(request.get("native_class_sha256").getAsString()))throw new IllegalStateException("Native helper class differs");}
        level=server.overworld();if(!request.get("seed").getAsString().equals(Long.toString(level.getSeed()))||!Path.of(request.get("world_path").getAsString()).toRealPath().equals(server.getWorldPath(LevelResource.ROOT).toRealPath()))throw new IllegalStateException("Actual world identity differs");
        checkpoint();
        if(action.equals("commission")){
            JsonObject geometry=reference("geometry",4*1024*1024),proof=reference("native_verify",65536);
            String geometrySha=request.getAsJsonObject("geometry").get("sha256").getAsString();
            Path proofPath=owned(request.getAsJsonObject("native_verify").get("path").getAsString());
            byte[] marker=bounded(proofPath.resolveSibling(proofPath.getFileName()+".complete"),128);
            if(!new String(marker,StandardCharsets.UTF_8).trim().equals(request.getAsJsonObject("native_verify").get("sha256").getAsString())
                ||!proof.get("operation").getAsString().equals("verify")||!proof.get("plan_sha256").getAsString().equals(geometrySha)
                ||!proof.get("status").getAsString().equals("verified actual block identities, orientation, block entities and supplied inventories")
                ||proof.has("error")||proof.get("failures").getAsInt()!=0||proof.get("cleanup_required").getAsBoolean()
                ||!geometry.get("backup_sha256").equals(request.get("backup_sha256"))
                ||!geometry.get("seed").equals(request.get("seed"))||!geometry.get("world_path").equals(request.get("world_path"))
                ||geometry.getAsJsonArray("commands").size()!=0)throw new IllegalStateException("Exact clean geometry verification required");
            Instant completed=Instant.parse(proof.get("finished").getAsString());if(completed.isAfter(Instant.now())||completed.isBefore(Instant.now().minusSeconds(1800)))throw new IllegalStateException("Reverify current fountain geometry");
            JsonArray palette=geometry.getAsJsonArray("palette"),rows=geometry.getAsJsonArray("blocks");
            if(rows.size()<100||rows.size()>20000||palette.size()>1024||proof.get("blocks").getAsInt()!=rows.size())throw new IllegalStateException("Finite complete fountain required");
            Set<BlockPos> unique=new HashSet<>();for(JsonElement entry:rows){JsonArray row=entry.getAsJsonArray();BlockPos p=new BlockPos(row.get(0).getAsInt(),row.get(1).getAsInt(),row.get(2).getAsInt());
                if(row.size()!=4||p.getX()<1104||p.getX()>1164||p.getZ()<-1144||p.getZ()>-1100||p.getY()<60||p.getY()>82||!unique.add(p))throw new IllegalStateException("Foreign or duplicate fountain geometry");
                targets.add(new Target(p,parse(palette.get(row.get(3).getAsInt()).getAsString())));
            }
        }
        for(int x=1119>>4;x<=1149>>4;x++)for(int z=-1136>>4;z<=-1120>>4;z++)chunks.add(new ChunkPos(x,z));
        for(Target target:targets)chunks.add(new ChunkPos(target.pos));if(chunks.size()>16)throw new IllegalStateException("Finite fountain chunk envelope exceeded");
        lease=interlock.acquire("fountain:"+expected,true);if(lease==null||!lease.valid())throw new IllegalStateException("Exclusive native lease required");
        report.put("request_sha256",expected);report.put("candidate",candidate);report.put("bridge",bridge);report.put("header_water_seeded",0);report.put("inventory_or_kinetic_NBT_writes",0);report.put("failures",0);phase=Phase.LOAD;
        for(ChunkPos chunk:chunks){tickets.add(chunk);ticket(chunk,true);pending.add(((worldfortwo.bridge.mixin.ChunkCacheAccess)(Object)level.getChunkSource()).awftQueueChunk(chunk.x,chunk.z,ChunkStatus.FULL,false));}
    }
    @SuppressWarnings({"rawtypes","unchecked"})private static BlockState parse(String text){
        String[] parts=text.split("\\[",2);ResourceLocation id=ResourceLocation.parse(parts[0]);if(!BuiltInRegistries.BLOCK.containsKey(id))throw new IllegalStateException("Unregistered fountain block");BlockState state=BuiltInRegistries.BLOCK.get(id).defaultBlockState();
        if(parts.length==2)for(String token:parts[1].substring(0,parts[1].length()-1).split(",")){String[] pair=token.split("=",2);Property prop=state.getBlock().getStateDefinition().getProperty(pair[0]);if(prop==null)throw new IllegalStateException("Unknown fountain property");state=state.setValue(prop,(Comparable)prop.getValue(pair[1]).orElseThrow());}return state;
    }
    private void checkpoint()throws Exception{JsonObject value=read("dashboard/settlement/backup-receipt.json",4096);if(!value.get("verified").getAsBoolean()||!value.get("sha256").equals(request.get("backup_sha256")))throw new IllegalStateException("Current retained checkpoint differs");}
    private void ticket(ChunkPos chunk,boolean add)throws Exception{level.getChunkSource().getClass().getMethod(add?"addRegionTicket":"removeRegionTicket",TicketType.class,ChunkPos.class,int.class,Object.class,boolean.class).invoke(level.getChunkSource(),TICKET,chunk,2,chunk,true);}
    private boolean ready(){for(ChunkPos p:chunks)if(level.getChunkSource().getChunkNow(p.x,p.z)==null||!level.getChunkSource().isPositionTicking(p.toLong())||!level.areEntitiesLoaded(p.toLong()))return false;return true;}
    private KineticBlockEntity kinetic(BlockPos pos,String id){if(!BuiltInRegistries.BLOCK.getKey(level.getBlockState(pos).getBlock()).toString().equals(id)||!(level.getBlockEntity(pos) instanceof KineticBlockEntity k))throw new IllegalStateException("Actual fountain kinetic differs: "+pos);return k;}
    private boolean water(BlockPos p){return level.getFluidState(p).getType().isSame(Fluids.WATER);}
    private boolean source(BlockPos p){return water(p)&&level.getFluidState(p).isSource();}
    private boolean jets(boolean flowing){return JETS.stream().allMatch(p->water(p)==flowing);}
    private void stopLever(boolean stop){BlockState old=level.getBlockState(LEVER);if(!old.is(Blocks.LEVER)||!old.hasProperty(BlockStateProperties.POWERED))throw new IllegalStateException("Actual manual fountain lever missing");BlockState next=old.setValue(BlockStateProperties.POWERED,stop);if(next!=old&&!level.setBlock(LEVER,next,3))throw new IllegalStateException("Normal lever update refused");level.updateNeighborsAt(LEVER,old.getBlock());level.updateNeighborsAt(LEVER.west(),old.getBlock());}
    private void next(Phase p){phase=p;phaseTicks=stable=0;}
    private void sample(String label){KineticBlockEntity wheel=kinetic(WHEEL,"create:water_wheel"),pump=kinetic(PUMP,"create:mechanical_pump");Map<String,Object> row=new LinkedHashMap<>();row.put("at",Instant.now().toString());row.put("phase",label);row.put("wheel_rpm",wheel.getSpeed());row.put("pump_rpm",pump.getSpeed());row.put("wheel_overstressed",wheel.isOverStressed());row.put("pump_overstressed",pump.isOverStressed());row.put("header_is_source",source(HEADER));row.put("jet_water",JETS.stream().map(this::water).toList());row.put("port_block",BuiltInRegistries.BLOCK.getKey(level.getBlockState(PORT).getBlock()).toString());row.put("manual_stop",level.getBlockState(LEVER).getValue(BlockStateProperties.POWERED));if(observations.size()<32)observations.add(row);report.put("observations",List.copyOf(observations));}
    public void tick(MinecraftServer server){
        if(phase==Phase.IDLE)return;if(phase==Phase.CLEANUP){cleanup();return;}long began=System.nanoTime();
        try{
            if(++ticks>2400||!server.isSameThread()||lease==null||!lease.valid()||!server.getPlayerList().getPlayers().isEmpty())throw new IllegalStateException("Native fountain lease/empty-server/thread/deadline refused");
            phaseTicks++;if(operation.equals("commission")){level.resetEmptyTime();report.put("bounded_native_empty_timer_resets",++wakeTicks);}
            if(phase==Phase.LOAD){if(pending.stream().anyMatch(f->!f.isDone()))return;for(var f:pending)f.join();pending.clear();if(!ready())return;next(Phase.GEOMETRY);}
            if(!ready())throw new IllegalStateException("Actual ticking fountain chunks unavailable");checkpoint();
            if(phase==Phase.GEOMETRY){while(index<targets.size()&&System.nanoTime()-began<4_000_000L){Target t=targets.get(index++);BlockState actual=level.getBlockState(t.pos);if(actual.getBlock()!=t.state.getBlock())throw new IllegalStateException("Fountain geometry changed at "+t.pos);for(Property<?> p:t.state.getProperties())if(Set.of("facing","axis","half","type","part","hinge").contains(p.getName())&&!actual.getValue(p).equals(t.state.getValue(p)))throw new IllegalStateException("Fountain orientation changed at "+t.pos);}
                if(index==targets.size()){if(operation.equals("inspect")){sample("read_only_inspection");finish("actual fountain snapshot; no mutation or commissioning acceptance",false);}else next(Phase.DRY);}return;}
            if(phase==Phase.DRY){
                if(!level.getBlockState(WHEEL_SOURCE).isAir()||level.getBlockEntity(WHEEL_SOURCE)!=null||!level.getEntities((Entity)null,new AABB(WHEEL_SOURCE)).isEmpty()||water(HEADER)||!jets(false))throw new IllegalStateException("Actual wheel-source/header/jet dry baseline is absent; do not replay commissioning");
                if(kinetic(WHEEL,"create:water_wheel").getSpeed()!=0||kinetic(PUMP,"create:mechanical_pump").getSpeed()!=0||!source(INTAKE))throw new IllegalStateException("Unexpected pre-powered fountain or missing real basin intake");
                if(!level.getBlockState(PISTON).is(Blocks.STICKY_PISTON)||level.getBlockState(PISTON).getValue(BlockStateProperties.FACING)!=net.minecraft.core.Direction.NORTH)throw new IllegalStateException("Actual gate piston differs");
                nativePlug=level.getBlockState(OPEN_PLUG);if(nativePlug.isAir()||nativePlug.hasBlockEntity()||!nativePlug.getFluidState().isEmpty())throw new IllegalStateException("Actual dry solid piston plug missing");
                stopLever(false);sample("native_dry_before_single_wheel_feed");
                if(!level.setBlock(WHEEL_SOURCE,Blocks.WATER.defaultBlockState(),3))throw new IllegalStateException("Normal independent waterwheel feed refused");seeded=true;report.put("independent_wheel_sources_seeded",1);next(Phase.FILL);
            }else if(phase==Phase.FILL||phase==Phase.RESTART){
                KineticBlockEntity wheel=kinetic(WHEEL,"create:water_wheel"),pump=kinetic(PUMP,"create:mechanical_pump");
                if(wheel.isOverStressed()||pump.isOverStressed())throw new IllegalStateException("Actual fountain kinetic network is overstressed");
                if(wheel.getSpeed()!=0&&pump.getSpeed()!=0&&source(HEADER)&&source(INTAKE)&&jets(true))stable++;else stable=0;
                if(stable>=40){sample(phase==Phase.FILL?"actual_pumped_header_and_gravity_cascades":"actual_restart_gravity_cascades");
                    if(phase==Phase.RESTART){report.put("actual_pump_fill_and_physical_gate_cycle",true);report.put("continuous_pump_circulation_claimed",false);report.put("hydraulics","Create fills the header; gravity feeds cascades; a full-source header normally backpressures the pump");finish("actual pumped fill and physical stop/restart passed; persistence and player use remain separate",false);}
                    else{stopLever(true);next(Phase.STOP);}}
                else if(phaseTicks>800)throw new IllegalStateException("Real wheel/pump/header/cascades did not become ready; partial world retained");
            }else if(phase==Phase.STOP){
                if(!source(HEADER)||!source(INTAKE))throw new IllegalStateException("Gate operation lost upstream source or reflecting-pool intake");
                boolean closed=level.getBlockState(PISTON).getValue(BlockStateProperties.EXTENDED)&&level.getBlockState(PORT).getBlock()==nativePlug.getBlock()&&!water(PORT);
                if(closed&&jets(false))stable++;else stable=0;
                if(stable>=40){sample("actual_gate_closed_and_lower_jets_drained");stopLever(false);next(Phase.RESTART);}
                else if(phaseTicks>600)throw new IllegalStateException("Physical OFF gate or downstream drain did not complete");
            }
            report.put("phase",phase.name());report.put("ticks",ticks);report.put("phase_ticks",phaseTicks);
            if(phase!=Phase.IDLE&&phase!=Phase.CLEANUP){
                if(ticks%100==0&&Set.of(Phase.FILL,Phase.STOP,Phase.RESTART).contains(phase))sample("periodic_"+phase.name());
                if(ticks%40==0)NativeJournal.progress(journal,"fountain-status.json",report);
            }
        }catch(Exception|LinkageError error){report.put("error",error.toString());report.put("failures",1);finish("native fountain stopped; actual partial hydraulic state and receipts retained",true);}
    }
    private void finish(String status,boolean failure){if(failure){outcome=status;report.put("failures",1);}else if(outcome==null)outcome=status;failed|=failure;if(failed&&seeded&&level!=null)try{stopLever(true);report.put("normal_STOP_requested",true);}catch(Exception error){report.put("STOP_request_error",error.toString());}phase=Phase.CLEANUP;cleanup();}
    private void cleanup(){
        List<String> errors=new ArrayList<>();if(level!=null)for(ChunkPos p:List.copyOf(tickets))try{ticket(p,false);tickets.remove(p);}catch(Exception error){errors.add(error.toString());}
        pending.removeIf(CompletableFuture::isDone);if(tickets.isEmpty()&&pending.isEmpty()&&lease!=null)try{lease.close();lease=null;}catch(Exception error){errors.add(error.toString());}
        boolean clean=tickets.isEmpty()&&pending.isEmpty()&&lease==null;report.put("cleanup_required",!clean);report.put("temporary_tickets_remaining",tickets.size());report.put("pending_shared_chunk_futures",pending.size());report.put("cleanup_errors",errors);report.put("status",outcome);report.put("finished",Instant.now().toString());
        try{NativeJournal.progress(journal,"fountain-status.json",report);if(clean||!terminalPublished){NativeJournal.terminal(journal,"fountain",report);terminalPublished=true;}}catch(Exception error){System.err.println("AWFT fountain journal: "+error);}
        if(clean)phase=Phase.IDLE;
    }
    public void stopped(){if(busy())finish("server stopping; fountain partial state retained without automatic replay",true);}
}
