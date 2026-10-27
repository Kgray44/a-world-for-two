package worldfortwo.bridge;

import com.google.gson.*;
import com.mojang.brigadier.arguments.StringArgumentType;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtUtils;
import net.minecraft.nbt.TagParser;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.TicketType;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.Property;
import net.minecraft.world.level.chunk.status.ChunkStatus;
import net.minecraft.world.level.storage.LevelResource;
import net.neoforged.fml.ModList;
import net.neoforged.fml.loading.FMLPaths;
import net.neoforged.neoforge.event.RegisterCommandsEvent;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.CompletableFuture;

/** PROPOSAL outside active sources. Real loaded-level neighbor settling only.
 * Original source geometry is never reconstructed here, nor are old states
 * replayed. The existing exclusive maintenance lease must be wired by parent.
 */
public final class NativeImportJoins {
    private enum Phase { IDLE, LOAD, INITIAL, JOIN, WAIT, CAPTURE, WAIT_VERIFY, VERIFY, CLEANUP }
    private record Expected(BlockPos position, BlockState state, Set<String> supplied) {}
    private static final Gson JSON=new Gson();
    private static final int MAX_TICKS=1200, MAX_BYTES=4*1024*1024, MAX_EXPORT=8*1024*1024;
    private static final Map<String,String> SOURCES=Map.of(
        "tavern","e09d9d47685a36efd485bd11510c4ff65acc128d9e7ce0feb0b363e33006543c",
        "shop","b6e7e85a3747abdaf510752e2b95d7bd98d21eda685ec4dd7d443e992e38022f");
    private static final Map<String,String> PREIMAGES=Map.of(
        "tavern","1d76f2c6e586eda8cd13703ad804c8cecce973115202c5ccf17756db8e541bb3",
        "shop","79e0543773de1eb44c4d6c8f7d16b86dc73c078ff540e7fa85e1535a3a43de6f");
    private static final TicketType<ChunkPos> TICKET=TicketType.create("awft_import_joins",Comparator.comparingLong(ChunkPos::toLong));
    private final Path home=FMLPaths.GAMEDIR.get().resolve("..").toAbsolutePath().normalize();
    private final Path journal=home.resolve("dashboard/settlement");
    private final String candidate,bridge;
    private final ArtisticEngineeringSupport.Interlock interlock;
    private ArtisticEngineeringSupport.Lease lease;
    private ServerLevel level;
    private Phase phase=Phase.IDLE;
    private JsonObject request,plan;
    private String outcome,kind,planSha,exportName,exportSha;
    private int ticks,index,pass,changed,wait;
    private boolean cleanupPublished;
    private final List<Expected> targets=new ArrayList<>();
    private final Set<ChunkPos> chunks=new LinkedHashSet<>(),tickets=new LinkedHashSet<>();
    private final List<CompletableFuture<?>> pending=new ArrayList<>();
    private final Map<BlockPos,CompoundTag> beforeTags=new LinkedHashMap<>(),authoredTags=new LinkedHashMap<>();
    private final Map<BlockPos,BlockState> frozen=new LinkedHashMap<>();
    private final Map<String,Object> report=new LinkedHashMap<>();
    private final List<Integer> convergence=new ArrayList<>();

    public NativeImportJoins(String candidate,String bridge,ArtisticEngineeringSupport.Interlock interlock){
        this.candidate=Objects.requireNonNull(candidate);this.bridge=Objects.requireNonNull(bridge);
        this.interlock=Objects.requireNonNull(interlock);
    }
    public boolean busy(){return phase!=Phase.IDLE;}
    public void commands(RegisterCommandsEvent event){
        var root=Commands.literal("awftimport").requires(s->s.getEntity()==null&&s.hasPermission(4));
        root.then(Commands.literal("settle").then(Commands.argument("bundle",StringArgumentType.word())
            .then(Commands.argument("sha256",StringArgumentType.word()).executes(c->{
                if(busy()){c.getSource().sendFailure(Component.literal("An import operation or its cleanup is already active"));return 0;}
                report.clear();outcome=null;cleanupPublished=false;report.put("operation","settle");report.put("started",Instant.now().toString());
                try{begin(c.getSource().getServer(),StringArgumentType.getString(c,"bundle"),StringArgumentType.getString(c,"sha256"));return 1;}
                catch(Exception|LinkageError error){report.put("error",error.toString());report.put("failures",1);finish("native import joins refused; existing geometry retained");throw new IllegalStateException("Native import join admission refused",error);}
            }))));
        root.then(Commands.literal("status").executes(c->{c.getSource().sendSuccess(()->Component.literal(JSON.toJson(report)),false);return 1;}));
        root.then(Commands.literal("cancel").executes(c->{finish("cancelled; completed native neighbor effects retained for explicit review");return 1;}));
        event.getDispatcher().register(root);
    }
    private static String sha(byte[] raw)throws Exception{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(raw));}
    private static byte[] bounded(Path path,int cap)throws Exception{
        if(!Files.isRegularFile(path)||Files.size(path)<1||Files.size(path)>cap)throw new IllegalStateException("Unbounded evidence input");
        try(InputStream in=Files.newInputStream(path)){byte[] raw=in.readNBytes(cap+1);if(raw.length>cap)throw new IllegalStateException("Evidence grew beyond its bound");return raw;}
    }
    private Path owned(String name)throws Exception{
        Path relative=Path.of(name);if(relative.isAbsolute()||name.indexOf(':')>=0||name.indexOf('\\')>=0)throw new IllegalStateException("Owned home-relative paths required");
        for(Path part:relative)if(part.toString().equals(".")||part.toString().equals(".."))throw new IllegalStateException("No evidence traversal");
        Path file=home.resolve(relative).normalize();
        for(Path p=file;p!=null&&!p.equals(home);p=p.getParent())if(Files.isSymbolicLink(p)||!p.toRealPath().equals(p.toAbsolutePath().normalize()))throw new IllegalStateException("Linked/redirected evidence refused");
        if(!file.toRealPath().startsWith(home.toRealPath()))throw new IllegalStateException("Evidence escaped owned home");return file;
    }
    private JsonObject ref(String name){return request.getAsJsonObject(name);}
    private JsonObject read(JsonObject ref,int cap)throws Exception{
        byte[] raw=bounded(owned(ref.get("path").getAsString()),cap);
        if(raw.length!=ref.get("bytes").getAsInt()||!sha(raw).equals(ref.get("sha256").getAsString()))throw new IllegalStateException("Exact evidence size/hash differs");
        return JsonParser.parseString(new String(raw,StandardCharsets.UTF_8)).getAsJsonObject();
    }
    private JsonObject proof(String name,String operation,String expected,int count,String status)throws Exception{
        JsonObject binding=ref(name),value=read(binding,512*1024);Path path=owned(binding.get("path").getAsString());
        Path markerPath=path.resolveSibling(path.getFileName()+".complete");
        byte[] marker=bounded(owned(home.relativize(markerPath).toString().replace('\\','/')),128);
        if(!new String(marker,StandardCharsets.UTF_8).trim().equals(binding.get("sha256").getAsString())
            ||!value.get("operation").getAsString().equals(operation)||!value.get("plan_sha256").getAsString().equals(expected)
            ||value.get("blocks").getAsInt()!=count||value.get("failures").getAsInt()!=0||value.has("error")
            ||!value.get("status").getAsString().equals(status))throw new IllegalStateException("Exact completed native before/place evidence required");
        Instant start=Instant.parse(value.get("started").getAsString()),end=Instant.parse(value.get("finished").getAsString());
        if(start.isAfter(end)||end.isAfter(Instant.now())||end.isBefore(Instant.now().minusSeconds(1800)))throw new IllegalStateException("Native before/place witness is stale or unordered");
        return value;
    }
    private void checkpoint()throws Exception{
        if(!owned(ref("current_backup").get("path").getAsString()).equals(journal.resolve("backup-receipt.json")))throw new IllegalStateException("Canonical current checkpoint receipt required");
        JsonObject backup=read(ref("current_backup"),4096);
        if(!backup.get("verified").getAsBoolean()||!backup.get("sha256").getAsString().equals(plan.get("backup_sha256").getAsString()))throw new IllegalStateException("Actual current checkpoint differs");
    }
    private void begin(MinecraftServer server,String bundle,String expected)throws Exception{
        if(busy()||lease!=null||!tickets.isEmpty()||!server.isSameThread()||!bundle.matches("import-joins-[a-f0-9]{16}")
            ||!expected.matches("[a-f0-9]{64}")||!bundle.endsWith(expected.substring(0,16)))throw new IllegalStateException("Busy, off-thread or invalid immutable import request");
        report.clear();outcome=null;cleanupPublished=false;report.put("operation","settle");report.put("started",Instant.now().toString());report.put("request_sha256",expected);
        if(server.getPort()!=25575||!server.getPlayerList().getPlayers().isEmpty())throw new IllegalStateException("Owned empty private staging server required");
        byte[] raw=bounded(owned("dashboard/settlement/"+bundle+"/request.json"),128*1024);
        if(!sha(raw).equals(expected))throw new IllegalStateException("Request hash differs");request=JsonParser.parseString(new String(raw,StandardCharsets.UTF_8)).getAsJsonObject();
        kind=request.get("kind").getAsString();
        if(!request.get("format").getAsString().equals("awft-native-import-joins:1")||!SOURCES.containsKey(kind)
            ||!request.get("candidate_version").getAsString().equals(candidate)||!request.get("bridge_version").getAsString().equals(bridge)
            ||!ModList.get().getModContainerById("awft_control_bridge").orElseThrow().getModInfo().getVersion().toString().equals(bridge))throw new IllegalStateException("Exact running candidate/bridge required");
        try(InputStream in=NativeImportJoins.class.getResourceAsStream("NativeImportJoins.class")){
            if(in==null)throw new IllegalStateException("Native helper class missing");byte[] code=in.readNBytes(256*1024+1);
            if(code.length>256*1024||!sha(code).equals(request.get("native_class_sha256").getAsString()))throw new IllegalStateException("Actual native helper differs");
        }
        JsonObject owner=JsonParser.parseString(new String(bounded(owned("dashboard/artistic-owner.json"),65536),StandardCharsets.UTF_8)).getAsJsonObject();
        JsonObject active=JsonParser.parseString(new String(bounded(owned("packwiz/active.json"),65536),StandardCharsets.UTF_8)).getAsJsonObject();
        JsonObject installed=JsonParser.parseString(new String(bounded(owned("server/installed.json"),1024*1024),StandardCharsets.UTF_8)).getAsJsonObject();
        if(!owner.get("format").getAsString().equals("awft-artistic-stage:1")||!Path.of(owner.get("home").getAsString()).toRealPath().equals(home.toRealPath())
            ||!active.get("version").getAsString().equals(candidate)||!installed.get("pack_version").getAsString().equals(candidate)
            ||!active.get("pack_sha256").getAsString().equals(installed.get("pack_sha256").getAsString()))throw new IllegalStateException("Owned installed candidate custody differs");
        if(!ref("source_plan").get("sha256").getAsString().equals(SOURCES.get(kind))||!ref("source_preimage").get("sha256").getAsString().equals(PREIMAGES.get(kind)))throw new IllegalStateException("Only the two reviewed exact original adaptations are admitted");
        JsonObject original=read(ref("source_plan"),MAX_BYTES),originalBefore=read(ref("source_preimage"),MAX_BYTES);
        plan=read(ref("plan"),MAX_BYTES);JsonObject before=read(ref("preimage_plan"),MAX_BYTES);checkpoint();
        original.add("backup_sha256",plan.get("backup_sha256"));originalBefore.add("backup_sha256",plan.get("backup_sha256"));
        if(!original.equals(plan)||!originalBefore.equals(before))throw new IllegalStateException("Fresh plans may change only checkpoint binding, never source geometry or tags");
        level=server.overworld();
        if(!plan.get("seed").getAsString().equals(Long.toString(level.getSeed()))||!Path.of(plan.get("world_path").getAsString()).toRealPath().equals(server.getWorldPath(LevelResource.ROOT).toRealPath()))throw new IllegalStateException("Actual world identity differs");
        if(plan.getAsJsonArray("commands").size()!=0)throw new IllegalStateException("No commands or entity actions admitted");
        targets.clear();chunks.clear();pending.clear();beforeTags.clear();authoredTags.clear();frozen.clear();report.clear();convergence.clear();
        ticks=index=pass=changed=wait=0;outcome=exportName=exportSha=null;cleanupPublished=false;planSha=ref("plan").get("sha256").getAsString();
        JsonArray palette=plan.getAsJsonArray("palette"),rows=plan.getAsJsonArray("blocks");Set<BlockPos> unique=new HashSet<>();
        int count=kind.equals("tavern")?4406:2252;if(rows.size()!=count||palette.size()>8192)throw new IllegalStateException("Exact addressed import targets required");
        for(JsonElement entry:rows){JsonArray row=entry.getAsJsonArray();if(row.size()!=4)throw new IllegalStateException("Invalid geometry row");BlockPos pos=position(row);int n=row.get(3).getAsInt();if(!unique.add(pos)||n<0||n>=palette.size())throw new IllegalStateException("Duplicate or foreign geometry");targets.add(parse(pos,palette.get(n).getAsString()));
            for(int x=(pos.getX()-1)>>4;x<=(pos.getX()+1)>>4;x++)for(int z=(pos.getZ()-1)>>4;z<=(pos.getZ()+1)>>4;z++)chunks.add(new ChunkPos(x,z));}
        if(chunks.size()>32)throw new IllegalStateException("Finite import neighborhood exceeded");
        for(JsonElement entry:plan.getAsJsonArray("block_entities")){JsonObject row=entry.getAsJsonObject();JsonArray p=row.getAsJsonArray("pos");BlockPos pos=position(p);String text=row.get("nbt").getAsString();if(!unique.contains(pos)||text.length()>16384||authoredTags.put(pos,TagParser.parseTag(text))!=null)throw new IllegalStateException("Foreign/duplicate furnishing tag");}
        JsonObject verified=proof("native_before","verify",ref("preimage_plan").get("sha256").getAsString(),count,"verified actual block identities, orientation, block entities and supplied inventories");
        JsonObject placed=proof("native_placement","place",planSha,count,"construction actions complete; native verification and restart still required");
        if(Instant.parse(verified.get("finished").getAsString()).isAfter(Instant.parse(placed.get("started").getAsString())))throw new IllegalStateException("Placement predates its admitted preimage");
        lease=interlock.acquire("import-joins:"+expected,true);if(lease==null||!lease.valid())throw new IllegalStateException("Exclusive existing world-operation lease required");
        report.put("operation","settle");report.put("started",Instant.now().toString());report.put("request_sha256",expected);report.put("plan_sha256",planSha);report.put("blocks",count);report.put("kind",kind);report.put("candidate",candidate);report.put("bridge",bridge);report.put("source_entities_executed",0);report.put("commands_executed",0);report.put("failures",0);report.put("strict_all_state_verification",false);phase=Phase.LOAD;
        for(ChunkPos chunk:chunks){tickets.add(chunk);ticket(chunk,true);pending.add(((worldfortwo.bridge.mixin.ChunkCacheAccess)(Object)level.getChunkSource()).awftQueueChunk(chunk.x,chunk.z,ChunkStatus.FULL,false));}
    }
    private BlockPos position(JsonArray row){int x=row.get(0).getAsInt(),y=row.get(1).getAsInt(),z=row.get(2).getAsInt();boolean inside=kind.equals("tavern")?x>=1282&&x<=1309&&z>=-1337&&z<=-1297&&y>=60&&y<=107:x>=1314&&x<=1334&&z>=-1349&&z<=-1316&&y>=63&&y<=107;if(!inside)throw new IllegalStateException("Position escaped exact reserved original plot");return new BlockPos(x,y,z);}
    @SuppressWarnings({"rawtypes","unchecked"}) private static Expected parse(BlockPos pos,String text){
        if(!text.matches("[a-z0-9_.-]+:[a-z0-9_./-]+(?:\\[[a-z0-9_=,]+\\])?"))throw new IllegalStateException("Invalid block-state syntax");String[] parts=text.split("\\[",2);ResourceLocation id=ResourceLocation.parse(parts[0]);if(!BuiltInRegistries.BLOCK.containsKey(id))throw new IllegalStateException("Unregistered actual identity");BlockState state=BuiltInRegistries.BLOCK.get(id).defaultBlockState();Set<String> supplied=new HashSet<>();
        if(parts.length==2)for(String token:parts[1].substring(0,parts[1].length()-1).split(",")){String[] pair=token.split("=",2);if(pair.length!=2||!supplied.add(pair[0]))throw new IllegalStateException("Duplicate/invalid property");Property property=state.getBlock().getStateDefinition().getProperty(pair[0]);if(property==null)throw new IllegalStateException("Unknown actual property");state=state.setValue(property,(Comparable)property.getValue(pair[1]).orElseThrow());}return new Expected(pos,state,Set.copyOf(supplied));
    }
    private void intent(Expected expected,BlockState actual){
        if(actual.getBlock()!=expected.state.getBlock())throw new IllegalStateException("Imported registered identity changed at "+expected.position);
        for(Property<?> property:expected.state.getProperties())if(expected.supplied.contains(property.getName())&&!actual.getValue(property).equals(expected.state.getValue(property)))throw new IllegalStateException("Supplied architectural intent changed at "+expected.position+" "+property.getName());
    }
    private CompoundTag tag(BlockPos pos)throws Exception{BlockEntity entity=level.getBlockEntity(pos);if(entity==null)return null;CompoundTag value=entity.saveWithFullMetadata(level.registryAccess());if(value.toString().length()>16384)throw new IllegalStateException("Native furnishing exceeds bound");return value;}
    private void preserved(BlockPos pos)throws Exception{CompoundTag actual=tag(pos),expected=beforeTags.get(pos);if(!Objects.equals(expected,actual))throw new IllegalStateException("Native furnishing/inventory changed at "+pos);}
    private boolean ready(){for(ChunkPos chunk:chunks){long key=chunk.toLong();if(level.getChunkSource().getChunkNow(chunk.x,chunk.z)==null||!level.getChunkSource().isPositionTicking(key)||!level.areEntitiesLoaded(key))return false;}return true;}
    private void ticket(ChunkPos chunk,boolean add)throws Exception{level.getChunkSource().getClass().getMethod(add?"addRegionTicket":"removeRegionTicket",TicketType.class,ChunkPos.class,int.class,Object.class,boolean.class).invoke(level.getChunkSource(),TICKET,chunk,2,chunk,true);}
    private void gate(MinecraftServer server)throws Exception{if(!server.isSameThread()||lease==null||!lease.valid()||!server.getPlayerList().getPlayers().isEmpty()||!ready())throw new IllegalStateException("Empty-world ownership/readiness changed");checkpoint();}
    public void tick(MinecraftServer server){
        if(phase==Phase.IDLE)return;if(phase==Phase.CLEANUP){cleanup();return;}
        long start=System.nanoTime();
        try{
            if(++ticks>MAX_TICKS||!server.isSameThread()||lease==null||!lease.valid()||!server.getPlayerList().getPlayers().isEmpty())throw new IllegalStateException("Import lease/thread/empty-server/timeout guard refused");
            level.resetEmptyTime(); // Bounded leased normal tick window; not a permanent loader.
            if(phase==Phase.LOAD){if(pending.stream().anyMatch(f->!f.isDone()))return;for(var future:pending)future.join();pending.clear();if(!ready())return;checkpoint();phase=Phase.INITIAL;}
            gate(server);
            if(phase==Phase.WAIT||phase==Phase.WAIT_VERIFY){if(++wait<20)return;wait=index=0;phase=phase==Phase.WAIT?Phase.CAPTURE:Phase.VERIFY;}
            int work=0;
            while(work++<128&&System.nanoTime()-start<4_000_000L){
                if(index>=targets.size()){
                    index=0;
                    if(phase==Phase.INITIAL){phase=Phase.JOIN;continue;}
                    if(phase==Phase.JOIN){convergence.add(changed);if(++pass<3){changed=0;continue;}if(changed!=0)throw new IllegalStateException("Native joins did not converge within three bounded passes");phase=Phase.WAIT;break;}
                    if(phase==Phase.CAPTURE){writeExport();phase=Phase.WAIT_VERIFY;break;}
                    if(phase==Phase.VERIFY){report.put("strict_all_state_verification",true);report.put("all_native_be_inventory_equality",true);finish("verified actual converged imported identities, every state property and unchanged native furnishings");break;}
                }
                Expected expected=targets.get(index++);BlockPos pos=expected.position;BlockState current=level.getBlockState(pos);intent(expected,current);
                if(phase==Phase.INITIAL){CompoundTag value=tag(pos),authored=authoredTags.get(pos);if(authored!=null&&(value==null||!NbtUtils.compareNbt(authored,value,true)))throw new IllegalStateException("Authored literal furnishing differs at "+pos);if(value!=null){if(beforeTags.size()>=256)throw new IllegalStateException("Native furnishing count exceeds bound");beforeTags.put(pos,value.copy());}}
                else if(phase==Phase.JOIN){preserved(pos);BlockState updated=Block.updateFromNeighbourShapes(current,level,pos);intent(expected,updated);if(updated!=current){if(!level.setBlock(pos,updated,3))throw new IllegalStateException("Normal native update refused");changed++;}level.updateNeighborsAt(pos,level.getBlockState(pos).getBlock());preserved(pos);}
                else if(phase==Phase.CAPTURE){preserved(pos);frozen.put(pos,current);}
                else if(phase==Phase.VERIFY){preserved(pos);if(!current.equals(frozen.get(pos)))throw new IllegalStateException("Full native state changed after frozen readback at "+pos);}
            }
            report.put("phase",phase.name());report.put("cursor",index);report.put("pass",pass);report.put("ticks",ticks);report.put("last_work_ms",(System.nanoTime()-start)/1_000_000.0);
        }catch(Exception|LinkageError error){report.put("error",error.toString());report.put("failures",1);finish("native import joins failed; partial native effects and original evidence retained");}
    }
    @SuppressWarnings({"rawtypes","unchecked"}) private static String text(BlockState state){TreeMap<String,String> fields=new TreeMap<>();for(Property property:state.getProperties())fields.put(property.getName(),property.getName((Comparable)state.getValue(property)));StringJoiner values=new StringJoiner(",");fields.forEach((k,v)->values.add(k+"="+v));return BuiltInRegistries.BLOCK.getKey(state.getBlock()).toString()+(fields.isEmpty()?"":"["+values+"]");}
    private void writeExport()throws Exception{
        checkpoint();JsonObject output=plan.deepCopy();TreeSet<String> values=new TreeSet<>();for(BlockState state:frozen.values())values.add(text(state));List<String> palette=new ArrayList<>(values);Map<String,Integer> ids=new HashMap<>();for(int n=0;n<palette.size();n++)ids.put(palette.get(n),n);JsonArray rows=new JsonArray();
        for(var entry:frozen.entrySet()){JsonArray row=new JsonArray();row.add(entry.getKey().getX());row.add(entry.getKey().getY());row.add(entry.getKey().getZ());row.add(ids.get(text(entry.getValue())));rows.add(row);}JsonArray tags=new JsonArray();for(var entry:beforeTags.entrySet()){JsonObject row=new JsonObject();row.add("pos",JSON.toJsonTree(List.of(entry.getKey().getX(),entry.getKey().getY(),entry.getKey().getZ())));row.addProperty("nbt",entry.getValue().toString());tags.add(row);}
        output.addProperty("name","VERIFY ONLY - actual converged "+kind+" complete native states and unchanged furnishings");output.addProperty("created",Instant.now().toString());output.addProperty("construction_forbidden",true);output.addProperty("validation","VERIFY ONLY. Actual real-level state export; never replay placement or inventories.");output.add("palette",JSON.toJsonTree(palette));output.add("blocks",rows);output.add("block_entities",tags);
        byte[] raw=(JSON.toJson(output)+"\n").getBytes(StandardCharsets.UTF_8);if(raw.length>MAX_EXPORT)throw new IllegalStateException("Exact native export exceeds bound");Files.createDirectories(journal);exportName="import-verify-only-"+UUID.randomUUID()+".json";Path path=journal.resolve(exportName);Files.write(path,raw,StandardOpenOption.CREATE_NEW);exportSha=sha(raw);Files.writeString(path.resolveSibling(path.getFileName()+".complete"),exportSha,StandardOpenOption.CREATE_NEW);
        report.put("native_full_state_export",exportName);report.put("native_full_state_export_sha256",exportSha);report.put("native_block_entities",beforeTags.size());report.put("convergence_changes",List.copyOf(convergence));report.put("replayed_states",0);report.put("full_state_property_omissions",0);report.put("source_supplied_property_omissions",0);
    }
    private void finish(String status){if(outcome==null)outcome=status;phase=Phase.CLEANUP;cleanup();}
    private void cleanup(){
        List<String> errors=new ArrayList<>();if(level!=null)for(ChunkPos chunk:List.copyOf(tickets))try{ticket(chunk,false);tickets.remove(chunk);}catch(Exception error){errors.add(error.toString());}
        // These are shared Minecraft futures: never cancel them or pretend that
        // releasing a ticket means the underlying work has finished.
        pending.removeIf(CompletableFuture::isDone);
        if(tickets.isEmpty()&&pending.isEmpty()&&lease!=null)try{lease.close();lease=null;}catch(Exception error){errors.add(error.toString());}
        boolean clean=tickets.isEmpty()&&pending.isEmpty()&&lease==null;report.put("cleanup",clean?"complete":"required; shared native work or owned ticket/lease remains");report.put("owned_tickets",tickets.size());report.put("pending_shared_futures",pending.size());report.put("cleanup_errors",errors);report.put("status",outcome);report.put("finished",Instant.now().toString());
        try{NativeJournal.progress(journal,"import-joins-status.json",report);if(clean||!cleanupPublished){NativeJournal.terminal(journal,"import-joins",report);cleanupPublished=true;}}catch(Exception error){System.err.println("AWFT import journal: "+error);}
        if(clean)phase=Phase.IDLE;
    }
    public void stopped(){if(busy())finish("server stopping; partial joins retained, no automatic replay or fake cleanup acceptance");}
}
