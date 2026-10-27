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
import net.minecraft.nbt.*;
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

/** Isolated next-version proposal. Retires only two positively identified old
 * authored glue entities; never places geometry, programs machinery or pulses.
 * Parent integrates commands/tick/stop and the existing shared exclusive lease.
 */
public final class RefinementGlueAdmission {
    private static final Gson JSON=new GsonBuilder().disableHtmlEscaping().create();
    private static final String ORIGIN_SHA="dedfb17410b01b5996cdde1957e5f30a5f96f54a09f00cd28515da87bbf52453";
    private static final String NEW_BASE_SHA="82778b15dc4139ed149df2c26adb67dc93ff92a6c9fd5a8d33b103d0d4915404";
    private static final String CYCLE_SHA="95c4d8d4db2d464acfbe26971c56eb22f19f13ff4949ee669160982f701ba1b8";
    private static final String CYCLE_FILE="engineering-result-2fae1ceb-ae51-461b-82b2-2822e8ce3717.json";
    private static final TicketType<ChunkPos> TICKET=TicketType.create("awft_bridge_refinement_glue",Comparator.comparingLong(ChunkPos::toLong));
    private enum Phase { IDLE, WAIT, CLEANUP }
    private final String candidate,bridge;
    private final ArtisticEngineeringSupport.Interlock interlock;
    private final Path home=FMLPaths.GAMEDIR.get().resolve("..").toAbsolutePath().normalize();
    private final Path journal=home.resolve("dashboard/settlement");
    private final Map<String,Object> report=new LinkedHashMap<>();
    private final LinkedHashSet<ChunkPos> chunks=new LinkedHashSet<>(),tickets=new LinkedHashSet<>();
    private final List<CompletableFuture<?>> pending=new ArrayList<>();
    private final LinkedHashMap<BlockPos,BlockState> preimage=new LinkedHashMap<>();
    private final List<Map<String,Object>> retired=new ArrayList<>();
    private ArtisticEngineeringSupport.Lease lease;
    private ServerLevel level;
    private JsonObject request,origin;
    private Phase phase=Phase.IDLE;
    private int ticks,readySamples;

    public RefinementGlueAdmission(String candidate,String bridge,ArtisticEngineeringSupport.Interlock interlock){
        this.candidate=Objects.requireNonNull(candidate);this.bridge=Objects.requireNonNull(bridge);this.interlock=Objects.requireNonNull(interlock);
    }
    public boolean busy(){return phase!=Phase.IDLE || level!=null || lease!=null || !tickets.isEmpty();}
    public void stop(){if(busy())finish("server stopping; no geometry/setup authority granted");}
    public void commands(RegisterCommandsEvent event){
        var root=Commands.literal("awftbridgeglue").requires(s->s.getEntity()==null && s.hasPermission(4));
        root.then(Commands.literal("retire").then(Commands.argument("bundle",StringArgumentType.word()).then(Commands.argument("sha256",StringArgumentType.word()).executes(c->{
            try{begin(c.getSource().getServer(),StringArgumentType.getString(c,"bundle"),StringArgumentType.getString(c,"sha256"));return 1;}
            catch(Exception error){report.put("error",error.toString());finish("admission refused; native partial state preserved");throw new IllegalStateException("Bridge glue admission refused",error);}
        }))));
        root.then(Commands.literal("status").executes(c->{c.getSource().sendSuccess(()->Component.literal(JSON.toJson(report)),false);return 1;}));
        root.then(Commands.literal("cancel").executes(c->{finish("explicit cancellation/cleanup retry; native partial state preserved");return 1;}));
        event.getDispatcher().register(root);
    }
    private static String sha(byte[] raw)throws Exception{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(raw));}
    private Path owned(String name)throws Exception{
        Path relative=Path.of(name);if(relative.isAbsolute()||name.indexOf('\\')>=0||name.indexOf(':')>=0)throw new IllegalArgumentException("Home-relative evidence only");
        for(Path part:relative)if(part.toString().equals("..")||part.toString().equals("."))throw new IllegalArgumentException("No traversal");
        Path path=home.resolve(relative).normalize();
        for(Path p=path;p!=null&&!p.equals(home);p=p.getParent())if(Files.isSymbolicLink(p)||!p.toRealPath().equals(p.toAbsolutePath().normalize()))throw new IllegalStateException("Redirected evidence refused");
        if(!path.toRealPath().startsWith(home.toRealPath()))throw new IllegalStateException("Evidence escaped home");return path;
    }
    private static byte[] bounded(Path path,int cap)throws Exception{
        if(!Files.isRegularFile(path)||Files.size(path)<1||Files.size(path)>cap)throw new IllegalStateException("Unbounded evidence");
        try(InputStream in=Files.newInputStream(path)){byte[] raw=in.readNBytes(cap+1);if(raw.length>cap)throw new IllegalStateException("Evidence grew");return raw;}
    }
    private JsonObject ref(String key){return request.getAsJsonObject(key);}
    private JsonObject readRef(String key,int cap)throws Exception{
        JsonObject ref=ref(key);byte[] raw=bounded(owned(ref.get("path").getAsString()),cap);
        if(raw.length!=ref.get("bytes").getAsInt()||!sha(raw).equals(ref.get("sha256").getAsString()))throw new IllegalStateException("Evidence size/digest differs: "+key);
        return JsonParser.parseString(new String(raw,StandardCharsets.UTF_8)).getAsJsonObject();
    }
    private JsonObject checkpoint()throws Exception{
        if(!owned(ref("checkpoint").get("path").getAsString()).equals(journal.resolve("backup-receipt.json")))throw new IllegalStateException("Exact current checkpoint reference required");
        JsonObject row=readRef("checkpoint",4096);if(!row.get("verified").getAsBoolean())throw new IllegalStateException("Unverified checkpoint");return row;
    }
    private void freshPreimageProof()throws Exception{
        JsonObject proof=readRef("native_before",512*1024);JsonObject marker=ref("native_before_complete");
        Path file=owned(ref("native_before").get("path").getAsString()),complete=owned(marker.get("path").getAsString());byte[] raw=bounded(complete,128);
        if(!complete.equals(file.resolveSibling(file.getFileName()+".complete"))||raw.length!=marker.get("bytes").getAsInt()||!sha(raw).equals(marker.get("sha256").getAsString())||!new String(raw,StandardCharsets.UTF_8).trim().equals(ref("native_before").get("sha256").getAsString()))throw new IllegalStateException("Immutable native marker differs");
        if(!proof.get("operation").getAsString().equals("verify")||!proof.get("plan_sha256").getAsString().equals(ref("preimage").get("sha256").getAsString())||proof.get("blocks").getAsInt()!=1130||proof.get("failures").getAsInt()!=0||proof.has("error")||!proof.get("status").getAsString().equals("verified actual block identities, orientation, block entities and supplied inventories"))throw new IllegalStateException("Fresh exact zero-difference preimage required");
        Instant start=Instant.parse(proof.get("started").getAsString()),end=Instant.parse(proof.get("finished").getAsString()),now=Instant.now();
        if(start.isAfter(end)||end.isAfter(now)||end.isBefore(now.minusSeconds(300))||proof.has("cleanup_required")&&proof.get("cleanup_required").getAsBoolean()||proof.has("temporary_tickets_remaining")&&proof.get("temporary_tickets_remaining").getAsInt()!=0)throw new IllegalStateException("Preimage is stale, unordered or has pending cleanup");
    }
    @SuppressWarnings({"rawtypes","unchecked"}) private static BlockState state(String text){
        String[] parts=text.split("\\[",2);var id=ResourceLocation.parse(parts[0]);if(!BuiltInRegistries.BLOCK.containsKey(id))throw new IllegalStateException("Unknown native block");
        BlockState value=BuiltInRegistries.BLOCK.get(id).defaultBlockState();
        if(parts.length==2)for(String entry:parts[1].substring(0,parts[1].length()-1).split(",")){String[] pair=entry.split("=",2);Property property=value.getBlock().getStateDefinition().getProperty(pair[0]);if(property==null)throw new IllegalStateException("Unknown property");value=value.setValue(property,(Comparable)property.getValue(pair[1]).orElseThrow());}
        return value;
    }
    private void begin(MinecraftServer server,String bundle,String expected)throws Exception{
        if(busy()||!server.getPlayerList().getPlayers().isEmpty()||!bundle.matches("bridge-refinement-admission-[a-f0-9]{16}")||!expected.matches("[a-f0-9]{64}")||!bundle.endsWith(expected.substring(0,16)))throw new IllegalStateException("Idle exact admission and empty server required");
        report.clear();retired.clear();preimage.clear();chunks.clear();pending.clear();ticks=readySamples=0;
        byte[] raw=bounded(owned("dashboard/settlement/"+bundle+"/request.json"),128*1024);if(!sha(raw).equals(expected))throw new IllegalStateException("Request digest differs");request=JsonParser.parseString(new String(raw,StandardCharsets.UTF_8)).getAsJsonObject();
        if(!request.get("format").getAsString().equals("awft-refinement-glue-admission:1")||!request.get("candidate").getAsString().equals(candidate)||!request.get("bridge").getAsString().equals(bridge)||!ModList.get().getModContainerById("awft_control_bridge").orElseThrow().getModInfo().getVersion().toString().equals(bridge))throw new IllegalStateException("Actual candidate/bridge identity differs");
        try(InputStream in=RefinementGlueAdmission.class.getResourceAsStream("RefinementGlueAdmission.class")){if(in==null)throw new IllegalStateException("Missing native class");byte[] code=in.readNBytes(128*1024+1);if(code.length>128*1024||!sha(code).equals(request.get("native_class_sha256").getAsString()))throw new IllegalStateException("Actual helper bytes differ");}
        if(!ref("origin").get("sha256").getAsString().equals(ORIGIN_SHA)||!ref("new_full_base").get("sha256").getAsString().equals(NEW_BASE_SHA))throw new IllegalStateException("Only the exact reviewed entity provenance and corrected refinement are admitted");
        origin=readRef("origin",256*1024);JsonObject backup=checkpoint(),base=readRef("new_full_base",512*1024),current=readRef("new_full_current",512*1024);
        JsonObject allowed=base.deepCopy();allowed.addProperty("backup_sha256",backup.get("sha256").getAsString());if(!allowed.equals(current)||!request.get("new_physical_sha256").getAsString().equals(NEW_BASE_SHA))throw new IllegalStateException("Only the current checkpoint may change in the new physical plan");
        if(!current.get("seed").getAsString().equals(Long.toString(server.overworld().getSeed()))||!Path.of(current.get("world_path").getAsString()).toRealPath().equals(server.getWorldPath(LevelResource.ROOT).toRealPath()))throw new IllegalStateException("Actual world custody differs");
        byte[] cycle=bounded(owned("dashboard/settlement/"+CYCLE_FILE),512*1024);if(!sha(cycle).equals(CYCLE_SHA)||!Files.readString(owned("dashboard/settlement/"+CYCLE_FILE+".complete")).trim().equals(CYCLE_SHA))throw new IllegalStateException("Historical native authored cycle provenance differs");
        JsonObject before=readRef("preimage",256*1024);if(!before.get("backup_sha256").getAsString().equals(backup.get("sha256").getAsString())||before.getAsJsonArray("blocks").size()!=1130||before.getAsJsonArray("block_entities").size()!=0||before.getAsJsonArray("commands").size()!=0)throw new IllegalStateException("Exact non-BE moving preimage required");
        JsonArray palette=before.getAsJsonArray("palette");for(JsonElement element:before.getAsJsonArray("blocks")){JsonArray row=element.getAsJsonArray();BlockPos p=new BlockPos(row.get(0).getAsInt(),row.get(1).getAsInt(),row.get(2).getAsInt());if(row.size()!=4||p.getX()<1187||p.getX()>1198||p.getY()<69||p.getY()>74||p.getZ()< -1172||p.getZ()> -1116||preimage.put(p,state(palette.get(row.get(3).getAsInt()).getAsString()))!=null)throw new IllegalStateException("Invalid moving preimage envelope");chunks.add(new ChunkPos(p));}
        freshPreimageProof();
        for(int z:new int[]{-1172,-1116})for(int x:new int[]{1199,1203,1225})chunks.add(new ChunkPos(new BlockPos(x,70,z)));
        for(int z:new int[]{-1178,-1110})chunks.add(new ChunkPos(new BlockPos(1182,73,z)));
        if(chunks.size()>16)throw new IllegalStateException("Finite native chunk envelope exceeded");
        lease=interlock.acquire("bridge-refinement-glue:"+expected,true);if(lease==null||!lease.valid())throw new IllegalStateException("Shared exclusive maintenance lease required");level=server.overworld();
        report.put("operation","retire-old-authored-glue");report.put("request_sha256",expected);report.put("origin_sha256",ORIGIN_SHA);report.put("new_physical_base_sha256",NEW_BASE_SHA);report.put("new_physical_current_sha256",ref("new_full_current").get("sha256").getAsString());report.put("candidate",candidate);report.put("bridge",bridge);report.put("checkpoint_id",backup.get("id").getAsString());report.put("checkpoint_sha256",backup.get("sha256").getAsString());report.put("started",Instant.now().toString());report.put("native_geometry_or_controls_modified",false);phase=Phase.WAIT;
        for(ChunkPos chunk:chunks){tickets.add(chunk);ticket(chunk,true);pending.add(((worldfortwo.bridge.mixin.ChunkCacheAccess)(Object)level.getChunkSource()).awftQueueChunk(chunk.x,chunk.z,ChunkStatus.FULL,false));}
    }
    private void ticket(ChunkPos chunk,boolean add)throws Exception{level.getChunkSource().getClass().getMethod(add?"addRegionTicket":"removeRegionTicket",TicketType.class,ChunkPos.class,int.class,Object.class,boolean.class).invoke(level.getChunkSource(),TICKET,chunk,2,chunk,true);}
    private boolean ready(){
        for(var future:pending){if(!future.isDone())return false;future.getNow(null);}
        for(ChunkPos chunk:chunks){long key=chunk.toLong();if(level.getChunkSource().getChunkNow(chunk.x,chunk.z)==null||!level.getChunkSource().isPositionTicking(key)||!level.areEntitiesLoaded(key)||!level.isPositionEntityTicking(chunk.getMiddleBlockPosition(70)))return false;}
        return true;
    }
    private List<Map<String,Object>> closed()throws Exception{
        List<Map<String,Object>> values=new ArrayList<>();
        for(int z:new int[]{-1172,-1116}){
            if(!(level.getBlockEntity(new BlockPos(1199,70,z)) instanceof MechanicalBearingBlockEntity bearing)||!(level.getBlockEntity(new BlockPos(1203,70,z)) instanceof SequencedGearshiftBlockEntity gear)||!(level.getBlockEntity(new BlockPos(1225,68,z)) instanceof KineticBlockEntity wheel))throw new IllegalStateException("Actual native bridge components missing");
            if(bearing.needsSpeedUpdate()||gear.needsSpeedUpdate()||wheel.needsSpeedUpdate())throw new IllegalStateException("Native bridge kinetics not initialized");
            CompoundTag tag=gear.saveWithFullMetadata(level.registryAccess());var instructions=tag.getList("Instructions",Tag.TAG_COMPOUND);boolean negative=z== -1172;
            boolean program=instructions.size()==4 && instructions.getCompound(0).getString("Type").equals("TURN_ANGLE") && instructions.getCompound(0).getInt("Value")==55 && instructions.getCompound(0).getString("Modifier").equals(negative?"BACK":"FORWARD") && instructions.getCompound(1).getString("Type").equals("AWAIT") && instructions.getCompound(2).getString("Type").equals("TURN_ANGLE") && instructions.getCompound(2).getInt("Value")==55 && instructions.getCompound(2).getString("Modifier").equals(negative?"FORWARD":"BACK") && instructions.getCompound(3).getString("Type").equals("END");
            double angle=bearing.getInterpolatedAngle(1f),speed=bearing.getSpeed(),input=gear.getSpeed();
            if(!program||!BridgePhaseGate.ready(angle,0,false,bearing.isRunning(),speed,input,gear.isOverStressed(),bearing.isOverStressed(),false,gear.isIdle(),tag.getBoolean("PrevPowered"),0)||bearing.getMovedContraption()!=null)throw new IllegalStateException("Both actual bearings must be closed/disassembled with powered idle reversible55 programs");
            values.add(Map.of("bearing",List.of(1199,70,z),"angle",angle,"running",false,"attached",false,"sequencer_idle",true,"input_rpm",input,"reversible_degrees",55));
        }
        for(int z:new int[]{-1178,-1110}){BlockState state=level.getBlockState(new BlockPos(1182,73,z));if(!(state.getBlock() instanceof ButtonBlock)||state.getValue(ButtonBlock.POWERED))throw new IllegalStateException("Actual bank controls must be released");}
        return values;
    }
    static JsonElement canonical(Tag tag){
        JsonArray row=new JsonArray();byte kind=tag.getId();row.add(kind);
        switch(kind){
            case 1,2,3,4 -> row.add(((NumericTag)tag).getAsLong());
            case 5 -> row.add(String.format(Locale.ROOT,"%08x",Float.floatToRawIntBits(((NumericTag)tag).getAsFloat())));
            case 6 -> row.add(String.format(Locale.ROOT,"%016x",Double.doubleToRawLongBits(((NumericTag)tag).getAsDouble())));
            case 8 -> row.add(tag.getAsString());
            case 7 -> {JsonArray a=new JsonArray();for(byte v:((ByteArrayTag)tag).getAsByteArray())a.add(v);row.add(a);}
            case 11 -> {JsonArray a=new JsonArray();for(int v:((IntArrayTag)tag).getAsIntArray())a.add(v);row.add(a);}
            case 12 -> {JsonArray a=new JsonArray();for(long v:((LongArrayTag)tag).getAsLongArray())a.add(v);row.add(a);}
            case 9 -> {ListTag list=(ListTag)tag;JsonObject value=new JsonObject();value.addProperty("element_type",list.getElementType());JsonArray children=new JsonArray();for(Tag child:list)children.add(canonical(child));value.add("values",children);row.add(value);}
            case 10 -> {CompoundTag compound=(CompoundTag)tag;JsonObject values=new JsonObject();for(String key:new TreeSet<>(compound.getAllKeys()))values.add(key,canonical(compound.get(key)));row.add(values);}
            default -> throw new IllegalStateException("Unsupported complete native NBT tag");
        }
        return row;
    }
    private static AABB box(JsonArray a){if(a.size()!=6)throw new IllegalStateException("Exact saved glue box required");return new AABB(a.get(0).getAsDouble(),a.get(1).getAsDouble(),a.get(2).getAsDouble(),a.get(3).getAsDouble(),a.get(4).getAsDouble(),a.get(5).getAsDouble());}
    private Map<String,Object> describe(Entity entity)throws Exception{
        CompoundTag saved=new CompoundTag();if(!entity.save(saved))throw new IllegalStateException("Native entity did not save its complete state");JsonElement data=canonical(saved);AABB box=entity.getBoundingBox();
        return Map.of("uuid",entity.getUUID().toString(),"native_class",entity.getClass().getName(),"bounds",List.of(box.minX,box.minY,box.minZ,box.maxX,box.maxY,box.maxZ),"canonical_nbt",data,"canonical_nbt_sha256",sha(JSON.toJson(data).getBytes(StandardCharsets.UTF_8)),"alive",entity.isAlive(),"removed",entity.isRemoved());
    }
    private void retire()throws Exception{
        if(!level.getServer().isSameThread()||lease==null||!lease.valid()||!level.getServer().getPlayerList().getPlayers().isEmpty())throw new IllegalStateException("Exclusive empty-world server-thread ownership required");
        checkpoint();freshPreimageProof();report.put("closed_before",closed());
        for(var row:preimage.entrySet())if(!level.getBlockState(row.getKey()).equals(row.getValue())||level.getBlockEntity(row.getKey())!=null)throw new IllegalStateException("Exact current native moving preimage differs: "+row.getKey());
        JsonArray expected=origin.getAsJsonArray("glues");if(expected.size()!=2)throw new IllegalStateException("Only two reviewed glues admitted");
        Set<UUID> ids=new LinkedHashSet<>();List<Entity> remove=new ArrayList<>();List<Map<String,Object>> before=new ArrayList<>();AABB region=null;
        for(JsonElement value:expected){JsonObject record=value.getAsJsonObject();UUID id=UUID.fromString(record.get("uuid").getAsString());if(!ids.add(id))throw new IllegalStateException("Duplicate admitted UUID");Entity entity=level.getEntity(id);AABB bounds=box(record.getAsJsonArray("bounds"));region=region==null?bounds:region.minmax(bounds);
            if(entity==null||entity.getClass()!=SuperGlueEntity.class||!entity.isAlive()||entity.isRemoved()||!entity.getBoundingBox().equals(bounds)||entity.isPassenger()||!entity.getPassengers().isEmpty())throw new IllegalStateException("Reviewed native glue identity/bounds/passengers changed");
            Map<String,Object> witness=describe(entity);if(!record.get("canonical_nbt").equals(witness.get("canonical_nbt"))||!record.get("canonical_nbt_sha256").getAsString().equals(witness.get("canonical_nbt_sha256")))throw new IllegalStateException("Complete current native glue NBT changed; preserve both entities");before.add(witness);remove.add(entity);
        }
        Set<UUID> actual=new LinkedHashSet<>();int count=0;for(Entity entity:level.getAllEntities()){if(++count>10000)throw new IllegalStateException("Entity inventory exceeds finite bound");if(entity instanceof SuperGlueEntity && entity.isAlive())actual.add(entity.getUUID());if(region.intersects(entity.getBoundingBox())&&(!(entity instanceof SuperGlueEntity))&&(entity.isPassenger()||!entity.getPassengers().isEmpty()||entity.getClass().getName().equals("com.simibubi.create.content.contraptions.ControlledContraptionEntity")))throw new IllegalStateException("Passenger or moving contraption occupies the reviewed bridge");}
        if(!actual.equals(ids))throw new IllegalStateException("Unknown, extra or unloaded glue inventory; preserve all glue");
        // BOTH complete identities and the entire loaded glue inventory have
        // passed before either discard. No await/yield/input intervenes.
        report.put("before_glues",before);report.put("closed_rechecked",closed());
        if(!lease.valid()||!level.getServer().getPlayerList().getPlayers().isEmpty())throw new IllegalStateException("Maintenance ownership changed");
        NativeJournal.terminal(journal,"bridge-refinement-glue-before",new LinkedHashMap<>(report));
        for(Entity entity:remove){entity.discard();if(!entity.isRemoved())throw new IllegalStateException("Native discard did not retire the exact glue");retired.add(Map.of("uuid",entity.getUUID().toString(),"removed",true));}
        Set<UUID> after=new LinkedHashSet<>();for(Entity entity:level.getAllEntities())if(entity instanceof SuperGlueEntity && entity.isAlive())after.add(entity.getUUID());
        report.put("retired_glues",List.copyOf(retired));report.put("remaining_loaded_glue_uuids",after.stream().map(UUID::toString).toList());report.put("closed_after",closed());
        if(!after.isEmpty())throw new IllegalStateException("Glue remains after exact retirement");
        report.put("retirement_completed",true);
        finish("exact two old authored glue entities retired; geometry/setup/cycles remain separate");
    }
    public void tick(MinecraftServer server){
        if(phase!=Phase.WAIT)return;
        try{
            if(level==null||lease==null||!lease.valid()||!server.getPlayerList().getPlayers().isEmpty())throw new IllegalStateException("Empty-world lease changed");
            if(++ticks>900)throw new IllegalStateException("Bounded native readiness timeout");checkpoint();level.resetEmptyTime();
            if(!ready()){readySamples=0;return;}
            try{closed();}catch(IllegalStateException waiting){readySamples=0;report.put("native_readiness",waiting.getMessage());return;}
            if(++readySamples>=2)retire();
        }catch(Exception error){report.put("error",error.toString());finish("stopped; exact partial state and cleanup retained");}
    }
    private void finish(String status){
        List<Map<String,Object>> failures=new ArrayList<>();int released=0;
        if(level!=null)for(var iterator=tickets.iterator();iterator.hasNext();){ChunkPos chunk=iterator.next();try{ticket(chunk,false);iterator.remove();released++;}catch(Exception error){failures.add(Map.of("chunk",List.of(chunk.x,chunk.z),"error",error.toString()));}}
        report.put("status",status);report.put("finished",Instant.now().toString());report.put("ticks",ticks);report.put("retired_glues",List.copyOf(retired));report.put("remaining_owned_tickets",tickets.size());report.put("temporary_tickets_remaining",tickets.size());report.put("ticket_release_failures",failures);report.put("cleanup_required",!tickets.isEmpty());report.put("released_this_attempt",released);report.remove("lease_cleanup_error");
        if(tickets.isEmpty()){
            for(var future:pending)if(!future.isDone())future.cancel(false);pending.clear();
            if(lease!=null){try{lease.close();lease=null;}catch(Exception error){report.put("lease_cleanup_error",error.toString());report.put("cleanup_required",true);}}
        }
        phase=Boolean.TRUE.equals(report.get("cleanup_required"))?Phase.CLEANUP:Phase.IDLE;
        if(phase==Phase.IDLE)level=null;
        try{NativeJournal.terminal(journal,"bridge-refinement-glue",new LinkedHashMap<>(report));NativeJournal.progress(journal,"bridge-refinement-glue-status.json",report);}catch(Exception error){System.err.println("AWFT bridge glue journal: "+error);}
    }
}
