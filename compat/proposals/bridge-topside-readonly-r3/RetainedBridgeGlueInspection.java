package worldfortwo.bridge;

import com.google.gson.*;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.simibubi.create.content.contraptions.bearing.MechanicalBearingBlockEntity;
import com.simibubi.create.content.contraptions.glue.SuperGlueEntity;
import com.simibubi.create.content.kinetics.base.KineticBlockEntity;
import com.simibubi.create.content.kinetics.transmission.sequencer.SequencedGearshiftBlockEntity;
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
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.TicketType;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.block.ButtonBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.Property;
import net.minecraft.world.level.chunk.status.ChunkStatus;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.AABB;
import net.neoforged.fml.ModList;
import net.neoforged.fml.loading.FMLPaths;
import net.neoforged.neoforge.event.RegisterCommandsEvent;

/** Original optional46 proposal. Read-only current glue/closed bridge custody.
 * No geometry, entities, inventories, glue, programs or controls are modified.
 * Bounded simulation tickets/wake exist only during the exclusive inspection.
 */
public final class RetainedBridgeGlueInspection {
    private static final Gson JSON=new GsonBuilder().disableHtmlEscaping().create();
    private static final TicketType<ChunkPos> TICKET=TicketType.create("awft_retained_bridge_inspection",Comparator.comparingLong(ChunkPos::toLong));
    private static final String NORTH="509a0105c6b8ee45ed972ae1ff066d8f78649662abc77a383dd5820b0470e3a7";
    private static final String SOUTH="c7c9a705b7c4e15b51a71e0420108c704cd091103263a8aa0b739bc238b6eba0";
    private static final AABB[] BOXES={new AABB(1187,69,-1172,1199,74,-1143),new AABB(1187,69,-1143,1199,74,-1115)};
    private final String candidate,bridge;
    private final ArtisticEngineeringSupport.Interlock interlock;
    private final Path home=FMLPaths.GAMEDIR.get().resolve("..").toAbsolutePath().normalize();
    private final Path journal=home.resolve("dashboard/settlement");
    private final Set<ChunkPos> chunks=new LinkedHashSet<>(),tickets=new LinkedHashSet<>();
    private final List<CompletableFuture<?>> pending=new ArrayList<>();
    private final Map<BlockPos,BlockState> preimage=new LinkedHashMap<>();
    private final Map<String,Object> report=new LinkedHashMap<>();
    private JsonObject request,census;
    private ServerLevel level;
    private ArtisticEngineeringSupport.Lease lease;
    private boolean waiting,cleanup,inspected;
    private CleanupTail cleanupTail=new CleanupTail();
    private String cleanupStatus;
    private int cleanupTicks;
    private int ticks,stable;
    public RetainedBridgeGlueInspection(String candidate,String bridge,ArtisticEngineeringSupport.Interlock interlock){this.candidate=candidate;this.bridge=bridge;this.interlock=interlock;}
    public boolean busy(){return waiting||cleanup||level!=null||lease!=null||!tickets.isEmpty()||!pending.isEmpty();}
    public void stop(){if(busy()){inspected=false;cleanupTail.retryReceipt();finish("server stopping; current glue preserved");}}
    public void commands(RegisterCommandsEvent event){
        var root=Commands.literal("awftbridgetop").requires(s->s.getEntity()==null&&s.hasPermission(4));
        root.then(Commands.literal("inspect").then(Commands.argument("bundle",StringArgumentType.word()).then(Commands.argument("sha256",StringArgumentType.word()).executes(c->{
            if(busy())throw new IllegalStateException("Current inspection/cleanup is still active");
            try{begin(c.getSource().getServer(),StringArgumentType.getString(c,"bundle"),StringArgumentType.getString(c,"sha256"));return 1;}
            catch(Exception error){report.put("error",error.toString());if(busy())finish("read-only inspection refused; glue preserved");throw new IllegalStateException("Retained glue inspection refused",error);}
        }))));
        root.then(Commands.literal("status").executes(c->{c.getSource().sendSuccess(()->Component.literal(JSON.toJson(report)),false);return 1;}));
        root.then(Commands.literal("cancel").executes(c->{inspected=false;cleanupTail.retryReceipt();finish("explicit cancellation/cleanup retry; no motion admission");return 1;}));
        event.getDispatcher().register(root);
    }
    private static String sha(byte[] raw)throws Exception{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(raw));}
    private Path owned(String name)throws Exception{
        Path rel=Path.of(name);if(rel.isAbsolute()||name.indexOf('\\')>=0||name.indexOf(':')>=0)throw new IllegalStateException("Home-relative regular evidence only");
        for(Path part:rel)if(part.toString().equals(".")||part.toString().equals(".."))throw new IllegalStateException("No traversal");
        Path p=home.resolve(rel).normalize();for(Path a=p;a!=null&&!a.equals(home);a=a.getParent())if(Files.isSymbolicLink(a)||!a.toRealPath().equals(a.toAbsolutePath().normalize()))throw new IllegalStateException("Redirected evidence");
        if(!p.toRealPath().startsWith(home.toRealPath()))throw new IllegalStateException("Escaped evidence");return p;
    }
    private static byte[] bytes(Path p,int cap)throws Exception{
        if(!Files.isRegularFile(p,LinkOption.NOFOLLOW_LINKS)||Files.size(p)<1||Files.size(p)>cap)throw new IllegalStateException("Bounded regular evidence required");
        try(InputStream in=Files.newInputStream(p)){byte[] b=in.readNBytes(cap+1);if(b.length>cap)throw new IllegalStateException("Evidence grew");return b;}
    }
    private JsonObject ref(String k){return request.getAsJsonObject(k);}
    private JsonObject readRef(String k,int cap)throws Exception{
        JsonObject r=ref(k);byte[] b=bytes(owned(r.get("path").getAsString()),cap);
        if(b.length!=r.get("bytes").getAsInt()||!sha(b).equals(r.get("sha256").getAsString()))throw new IllegalStateException("Evidence size/hash differs: "+k);
        return JsonParser.parseString(new String(b,StandardCharsets.UTF_8)).getAsJsonObject();
    }
    private JsonObject checkpoint()throws Exception{
        if(!owned(ref("checkpoint").get("path").getAsString()).equals(journal.resolve("backup-receipt.json")))throw new IllegalStateException("Current canonical checkpoint required");
        JsonObject b=readRef("checkpoint",4096);if(!b.get("verified").getAsBoolean()||!b.get("id").equals(census.get("checkpoint_id"))||!b.get("sha256").equals(census.get("checkpoint_sha256")))throw new IllegalStateException("Exact stopped census checkpoint changed");return b;
    }
    @SuppressWarnings({"rawtypes","unchecked"}) private static BlockState state(String text){
        String[] parts=text.split("\\[",2);var id=ResourceLocation.parse(parts[0]);if(!BuiltInRegistries.BLOCK.containsKey(id))throw new IllegalStateException("Unknown actual block");
        BlockState s=BuiltInRegistries.BLOCK.get(id).defaultBlockState();
        if(parts.length==2)for(String entry:parts[1].substring(0,parts[1].length()-1).split(",")){String[] a=entry.split("=",2);Property p=s.getBlock().getStateDefinition().getProperty(a[0]);if(p==null)throw new IllegalStateException("Unknown property");s=s.setValue(p,(Comparable)p.getValue(a[1]).orElseThrow());}return s;
    }
    private void freshBefore()throws Exception{
        JsonObject p=readRef("native_before",256*1024);Path path=owned(ref("native_before").get("path").getAsString());JsonObject r=ref("native_before_complete");Path marker=owned(r.get("path").getAsString());byte[] b=bytes(marker,128);
        if(!marker.equals(path.resolveSibling(path.getFileName()+".complete"))||b.length!=r.get("bytes").getAsInt()||!sha(b).equals(r.get("sha256").getAsString())||!new String(b,StandardCharsets.UTF_8).trim().equals(ref("native_before").get("sha256").getAsString()))throw new IllegalStateException("Immutable actual BEFORE completion marker required");
        if(!p.get("operation").getAsString().equals("verify")||!p.get("plan_sha256").equals(ref("preimage").get("sha256"))||p.get("blocks").getAsInt()!=106||p.get("failures").getAsInt()!=0||p.has("error")||!p.get("status").getAsString().equals("verified actual block identities, orientation, block entities and supplied inventories")||p.get("cleanup_required").getAsBoolean()||p.get("temporary_tickets_remaining").getAsInt()!=0||p.get("pending_shared_chunk_futures").getAsInt()!=0||p.has("ticket_cleanup_error"))throw new IllegalStateException("Exact clean actual106 BEFORE required");
        Instant start=Instant.parse(p.get("started").getAsString()),end=Instant.parse(p.get("finished").getAsString()),now=Instant.now();if(start.isAfter(end)||end.isAfter(now)||end.isBefore(now.minusSeconds(300)))throw new IllegalStateException("Fresh ordered BEFORE required");
    }
    private void releasePack()throws Exception{
        if(!candidate.matches("[A-Za-z0-9][A-Za-z0-9_.-]{0,79}")||candidate.endsWith("."))throw new IllegalStateException("Unsafe active release candidate");
        JsonObject active=JsonParser.parseString(new String(bytes(owned("packwiz/active.json"),65536),StandardCharsets.UTF_8)).getAsJsonObject();
        JsonObject installed=JsonParser.parseString(new String(bytes(owned("server/installed.json"),2*1024*1024),StandardCharsets.UTF_8)).getAsJsonObject();
        String expected=request.get("pack_sha256").getAsString();
        if(!expected.matches("[a-f0-9]{64}")||!active.get("version").getAsString().equals(candidate)||!installed.get("pack_version").getAsString().equals(candidate)
            ||!active.get("pack_sha256").getAsString().equals(expected)||!installed.get("pack_sha256").getAsString().equals(expected)
            ||!sha(bytes(owned("packwiz/releases/"+candidate+"/pack.toml"),65536)).equals(expected))throw new IllegalStateException("Actual active installed versioned release pack differs");
    }
    private void begin(MinecraftServer server,String bundle,String expected)throws Exception{
        if(!server.getPlayerList().getPlayers().isEmpty()||server.getPort()!=25575||!bundle.matches("bridge-topside-inspection-[a-f0-9]{16}")||!expected.matches("[a-f0-9]{64}")||!bundle.endsWith(expected.substring(0,16)))throw new IllegalStateException("Exact private empty-world request required");
        Path world=server.getWorldPath(LevelResource.ROOT).toRealPath(),root=Path.of("D:/A World for Two/staging/world-tests").toRealPath();
        if(!world.startsWith(root)||world.getNameCount()!=root.getNameCount()+3||!world.getFileName().toString().equals("RosewaterArtistic")||!world.getParent().getFileName().toString().equals("world")||!home.toRealPath().equals(world.getParent().getParent()))throw new IllegalStateException("Exact private artistic ancestry required");
        report.clear();chunks.clear();pending.clear();preimage.clear();ticks=stable=cleanupTicks=0;inspected=cleanup=false;cleanupStatus=null;cleanupTail=new CleanupTail();
        byte[] b=bytes(owned("dashboard/settlement/"+bundle+"/request.json"),64*1024);if(!sha(b).equals(expected))throw new IllegalStateException("Exact request hash differs");request=JsonParser.parseString(new String(b,StandardCharsets.UTF_8)).getAsJsonObject();
        if(!request.get("format").getAsString().equals("awft-retained-bridge-inspection:1")||!request.get("candidate").getAsString().equals(candidate)||!request.get("bridge").getAsString().equals(bridge)||!ModList.get().getModContainerById("awft_control_bridge").orElseThrow().getModInfo().getVersion().toString().equals(bridge))throw new IllegalStateException("Actual candidate/bridge/pack differs");releasePack();
        try(InputStream in=RetainedBridgeGlueInspection.class.getResourceAsStream("RetainedBridgeGlueInspection.class")){if(in==null)throw new IllegalStateException("Missing actual helper class");byte[] code=in.readNBytes(128*1024+1);if(code.length>128*1024||!sha(code).equals(request.get("native_class_sha256").getAsString()))throw new IllegalStateException("Actual helper class hash differs");}
        census=readRef("census",128*1024);JsonObject current=checkpoint();
        if(!census.get("format").getAsString().equals("awft-retained-glue-saved-census:1")||!census.get("seed").getAsString().equals(Long.toString(server.overworld().getSeed()))||!Path.of(census.get("world_path").getAsString()).toRealPath().equals(world)||census.getAsJsonArray("glues").size()!=2)throw new IllegalStateException("Exact complete stopped glue census/world required");
        JsonObject owner=JsonParser.parseString(new String(bytes(owned("dashboard/artistic-owner.json"),16*1024),StandardCharsets.UTF_8)).getAsJsonObject();if(!owner.get("format").getAsString().equals("awft-artistic-stage:1")||!Path.of(owner.get("home").getAsString()).toRealPath().equals(home.toRealPath())||!owner.get("backup").equals(current.get("id"))||!owner.get("backup_sha256").equals(current.get("sha256")))throw new IllegalStateException("Actual artistic owner/checkpoint differs");
        Set<BlockPos> targets=new LinkedHashSet<>();for(String k:List.of("north_original","south_original")){
            if(!ref(k).get("sha256").getAsString().equals(k.equals("north_original")?NORTH:SOUTH))throw new IllegalStateException("Only original frozen53+53 target positions admitted");
            JsonObject original=readRef(k,64*1024);if(original.getAsJsonArray("blocks").size()!=53)throw new IllegalStateException("Exact53-cell source required");
            for(JsonElement v:original.getAsJsonArray("blocks")){JsonArray row=v.getAsJsonArray();BlockPos q=new BlockPos(row.get(0).getAsInt(),row.get(1).getAsInt(),row.get(2).getAsInt());if(!targets.add(q))throw new IllegalStateException("Duplicate original target");}
        }
        JsonObject before=readRef("preimage",256*1024);if(!before.get("backup_sha256").equals(current.get("sha256"))||!before.get("seed").equals(census.get("seed"))||!before.get("world_path").equals(census.get("world_path"))||before.getAsJsonArray("blocks").size()!=106||before.getAsJsonArray("commands").size()!=0||before.getAsJsonArray("block_entities").size()!=0||!before.get("verification_only").getAsBoolean()||!before.get("construction_forbidden").getAsBoolean())throw new IllegalStateException("Exact current nonBE106 preimage required");
        JsonArray palette=before.getAsJsonArray("palette");if(palette.size()>32)throw new IllegalStateException("Finite preimage palette required");
        for(JsonElement v:before.getAsJsonArray("blocks")){JsonArray row=v.getAsJsonArray();BlockPos q=new BlockPos(row.get(0).getAsInt(),row.get(1).getAsInt(),row.get(2).getAsInt());if(row.size()!=4||!targets.contains(q)||preimage.put(q,state(palette.get(row.get(3).getAsInt()).getAsString()))!=null)throw new IllegalStateException("Exact target set changed");chunks.add(new ChunkPos(q));}
        if(!preimage.keySet().equals(targets))throw new IllegalStateException("Complete original target coverage required");freshBefore();
        for(int z:new int[]{-1172,-1116})for(int x:new int[]{1199,1203,1225})chunks.add(new ChunkPos(new BlockPos(x,70,z)));
        for(int z:new int[]{-1178,-1110})chunks.add(new ChunkPos(new BlockPos(1182,73,z)));if(chunks.size()>16)throw new IllegalStateException("Bounded existing bridge chunks only");
        lease=interlock.acquire("retained-bridge-inspection:"+expected,true);if(lease==null||!lease.valid())throw new IllegalStateException("Shared exclusive maintenance lease required");level=server.overworld();waiting=true;
        report.put("operation","inspect-retained-current-glue");report.put("started",Instant.now().toString());report.put("candidate",candidate);report.put("bridge",bridge);report.put("request_sha256",expected);report.put("checkpoint_id",current.get("id").getAsString());report.put("checkpoint_sha256",current.get("sha256").getAsString());report.put("no_native_geometry_entity_inventory_glue_control_writes",true);
        for(ChunkPos q:chunks){tickets.add(q);ticket(q,true);pending.add(((worldfortwo.bridge.mixin.ChunkCacheAccess)(Object)level.getChunkSource()).awftQueueChunk(q.x,q.z,ChunkStatus.FULL,false));}
    }
    private void ticket(ChunkPos q,boolean add)throws Exception{level.getChunkSource().getClass().getMethod(add?"addRegionTicket":"removeRegionTicket",TicketType.class,ChunkPos.class,int.class,Object.class,boolean.class).invoke(level.getChunkSource(),TICKET,q,2,q,true);}
    private boolean ready(){for(var f:pending){if(!f.isDone())return false;f.getNow(null);}for(ChunkPos q:chunks){long k=q.toLong();if(level.getChunkSource().getChunkNow(q.x,q.z)==null||!level.getChunkSource().isPositionTicking(k)||!level.areEntitiesLoaded(k)||!level.isPositionEntityTicking(q.getMiddleBlockPosition(70)))return false;}return true;}
    private List<Map<String,Object>> closed(){
        List<Map<String,Object>> out=new ArrayList<>();for(int z:new int[]{-1172,-1116}){
            if(!(level.getBlockEntity(new BlockPos(1199,70,z))instanceof MechanicalBearingBlockEntity bearing)||!(level.getBlockEntity(new BlockPos(1203,70,z))instanceof SequencedGearshiftBlockEntity gear)||!(level.getBlockEntity(new BlockPos(1225,68,z))instanceof KineticBlockEntity wheel)||bearing.needsSpeedUpdate()||gear.needsSpeedUpdate()||wheel.needsSpeedUpdate())throw new IllegalStateException("Concrete initialized native bridge components required");
            CompoundTag t=gear.saveWithFullMetadata(level.registryAccess());var p=t.getList("Instructions",Tag.TAG_COMPOUND);boolean n=z== -1172;
            if(p.size()!=4||!p.getCompound(0).getString("Type").equals("TURN_ANGLE")||p.getCompound(0).getInt("Value")!=55||!p.getCompound(0).getString("Modifier").equals(n?"BACK":"FORWARD")||!p.getCompound(1).getString("Type").equals("AWAIT")||!p.getCompound(2).getString("Type").equals("TURN_ANGLE")||p.getCompound(2).getInt("Value")!=55||!p.getCompound(2).getString("Modifier").equals(n?"FORWARD":"BACK")||!p.getCompound(3).getString("Type").equals("END")||bearing.getMovedContraption()!=null||!BridgePhaseGate.ready(bearing.getInterpolatedAngle(1),0,false,bearing.isRunning(),bearing.getSpeed(),gear.getSpeed(),gear.isOverStressed(),bearing.isOverStressed(),false,gear.isIdle(),t.getBoolean("PrevPowered"),0))throw new IllegalStateException("Actual closed/disassembled idle reversible55-degree bridge required");
            out.add(Map.of("bearing",List.of(1199,70,z),"angle",bearing.getInterpolatedAngle(1),"running",bearing.isRunning(),"sequencer_idle",gear.isIdle(),"input_rpm",gear.getSpeed(),"wheel_rpm",wheel.getSpeed()));
        }
        for(int z:new int[]{-1178,-1110}){BlockState b=level.getBlockState(new BlockPos(1182,73,z));if(!(b.getBlock()instanceof ButtonBlock)||b.getValue(ButtonBlock.POWERED))throw new IllegalStateException("Actual bank buttons must be released");}return out;
    }
    private void inspect()throws Exception{
        checkpoint();freshBefore();report.put("closed_before",closed());
        for(var e:preimage.entrySet())if(!level.getBlockState(e.getKey()).equals(e.getValue())||level.getBlockEntity(e.getKey())!=null)throw new IllegalStateException("Strict current106 block state/preimage changed");
        Set<UUID> ids=new LinkedHashSet<>();List<Map<String,Object>> observed=new ArrayList<>();int index=0;
        for(JsonElement value:census.getAsJsonArray("glues")){
            JsonObject r=value.getAsJsonObject();UUID id=UUID.fromString(r.get("uuid").getAsString());JsonArray a=r.getAsJsonArray("bounds");if(a.size()!=6)throw new IllegalStateException("Exact saved glue AABB required");AABB box=new AABB(a.get(0).getAsDouble(),a.get(1).getAsDouble(),a.get(2).getAsDouble(),a.get(3).getAsDouble(),a.get(4).getAsDouble(),a.get(5).getAsDouble());
            if(!box.equals(BOXES[index++])||!ids.add(id)||!r.get("entity_id").getAsString().equals("create:super_glue"))throw new IllegalStateException("Only current original-size two glues admitted");
            Entity entity=level.getEntity(id);if(entity==null||entity.getClass()!=SuperGlueEntity.class||!entity.isAlive()||entity.isRemoved()||entity.isPassenger()||!entity.getPassengers().isEmpty()||!entity.getBoundingBox().equals(box))throw new IllegalStateException("Current resolved native glue identity/bounds differs");
            CompoundTag saved=new CompoundTag();if(!entity.save(saved))throw new IllegalStateException("Native glue complete save unavailable");JsonElement typed=RefinementGlueAdmission.canonical(saved);String hash=sha(JSON.toJson(typed).getBytes(StandardCharsets.UTF_8));
            if(!typed.equals(r.get("canonical_nbt"))||!hash.equals(r.get("canonical_nbt_sha256").getAsString()))throw new IllegalStateException("Complete current native glue typedNBT differs");
            observed.add(Map.of("uuid",id.toString(),"native_class",entity.getClass().getName(),"bounds",List.of(box.minX,box.minY,box.minZ,box.maxX,box.maxY,box.maxZ),"canonical_nbt",typed,"canonical_nbt_sha256",hash));
        }
        Set<UUID> actual=new LinkedHashSet<>();int count=0;AABB region=BOXES[0].minmax(BOXES[1]);for(Entity e:level.getAllEntities()){
            if(++count>10000)throw new IllegalStateException("Finite loaded entity inventory exceeded");if(e instanceof SuperGlueEntity&&e.isAlive())actual.add(e.getUUID());
            if(region.intersects(e.getBoundingBox())&&!(e instanceof SuperGlueEntity)&&(e.isPassenger()||!e.getPassengers().isEmpty()||e.getClass().getName().equals("com.simibubi.create.content.contraptions.ControlledContraptionEntity")))throw new IllegalStateException("Passenger or moving contraption interferes with closed bridge");
        }
        if(!actual.equals(ids))throw new IllegalStateException("Unknown/extra/unresolved current glue inventory; preserve everything");
        report.put("glues",observed);report.put("loaded_glue_uuids",actual.stream().map(UUID::toString).toList());report.put("loaded_entity_count",count);report.put("strict_preimage_states",preimage.size());report.put("closed_after",closed());
        report.put("inventory_scope","Complete authenticated stopped saved census plus exact loaded native two-UUID resolution; no global force loading");
        inspected=true;finish("read-only current two-glue and closed bridge custody passed; no placement or motion performed");
    }
    public void tick(MinecraftServer server){
        if(cleanup){cleanupStep();return;}
        if(!waiting)return;
        try{
            if(++ticks>600||lease==null||!lease.valid()||!server.getPlayerList().getPlayers().isEmpty())throw new IllegalStateException("Bounded exclusive empty-world inspection changed/expired");
            checkpoint();level.resetEmptyTime();if(ticks%10!=0)return;if(!ready()){stable=0;return;}
            try{closed();}catch(IllegalStateException waitingForNative){stable=0;report.put("waiting_for",waitingForNative.getMessage());return;}
            if(++stable>=2)inspect();
        }catch(Exception error){report.put("error",error.toString());inspected=false;finish("read-only custody refused; native state retained");}
    }
    /** Actual cleanup tail shared by runtime and offline future/failure fixtures.
     * Terminal attempts are bounded to once per pending/clean phase; explicit
     * cancel/stop retries a blocked publication. Shared futures are never cancelled. */
    @FunctionalInterface interface CleanupAttempt { void run()throws Exception; }
    static final class CleanupTail {
        boolean pendingAttempted,cleanAttempted,cleanPublished;
        String terminalError,progressError;
        static long unfinished(Collection<? extends CompletableFuture<?>> futures){return futures.stream().filter(f->!f.isDone()).count();}
        static boolean mayCloseLease(int tickets,long futures){return tickets==0&&futures==0;}
        static void closeLeaseWhenReady(int tickets,long futures,CleanupAttempt close)throws Exception{if(mayCloseLease(tickets,futures))close.run();}
        void retryReceipt(){pendingAttempted=cleanAttempted=cleanPublished=false;terminalError=null;}
        boolean publish(boolean resourcesClean,CleanupAttempt terminal,CleanupAttempt progress){
            boolean attempt=resourcesClean?!cleanAttempted:!pendingAttempted;
            if(attempt){
                if(resourcesClean)cleanAttempted=true;else pendingAttempted=true;
                terminalError=null;
                try{terminal.run();if(resourcesClean)cleanPublished=true;}
                catch(Exception error){terminalError=error.toString();System.err.println("AWFT retained bridge immutable journal: "+error);}
            }
            // Even a failed mutable view cannot suppress the immutable result.
            try{progress.run();progressError=null;}
            catch(Exception error){String next=error.toString();if(!next.equals(progressError))System.err.println("AWFT retained bridge progress view: "+error);progressError=next;}
            return resourcesClean&&cleanPublished;
        }
    }
    private void finish(String status){
        waiting=false;if(cleanupStatus==null)cleanupStatus=status;cleanup=true;cleanupStep();
    }
    private void cleanupStep(){
        // Cleanup retries on every tick without resetEmptyTime, loading, motion,
        // cancellation of shared futures, or any geometry/entity/control write.
        cleanupTicks++;List<Map<String,Object>> failures=new ArrayList<>();
        if(level!=null)for(var it=tickets.iterator();it.hasNext();){ChunkPos q=it.next();try{ticket(q,false);it.remove();}catch(Exception error){failures.add(Map.of("chunk",List.of(q.x,q.z),"error",error.toString()));}}
        long futures=CleanupTail.unfinished(pending);pending.removeIf(CompletableFuture::isDone);report.remove("lease_cleanup_error");
        if(lease!=null)try{CleanupTail.closeLeaseWhenReady(tickets.size(),futures,()->{lease.close();lease=null;});}catch(Exception error){report.put("lease_cleanup_error",error.toString());}
        boolean resourcesClean=tickets.isEmpty()&&pending.isEmpty()&&lease==null;
        report.put("status",cleanupStatus);report.put("finished",Instant.now().toString());report.put("ticks",ticks);report.put("cleanup_retry_ticks",cleanupTicks);report.put("cleanup_required",!resourcesClean);report.put("temporary_tickets_remaining",tickets.size());report.put("pending_shared_chunk_futures",futures);report.put("ticket_release_failures",failures);report.put("native_custody_passed",inspected&&resourcesClean&&!report.containsKey("error"));report.put("new_glue_or_motion_authority",false);report.remove("journal_error");report.remove("receipt_blocked");
        boolean complete=cleanupTail.publish(resourcesClean,
            ()->NativeJournal.terminal(journal,"bridge-topside-inspection",new LinkedHashMap<>(report)),
            ()->{
                if(cleanupTail.terminalError!=null){report.put("journal_error",cleanupTail.terminalError);report.put("receipt_blocked",true);report.put("cleanup_required",true);report.put("native_custody_passed",false);}
                NativeJournal.progress(journal,"bridge-topside-inspection-status.json",report);
            });
        // The global busy gate survives a closed lease until the final immutable
        // clean terminal exists; progress-file failure alone never holds it.
        cleanup=!complete;if(complete){level=null;pending.clear();}
    }
}
