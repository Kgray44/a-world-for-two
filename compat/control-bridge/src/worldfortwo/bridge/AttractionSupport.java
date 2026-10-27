package worldfortwo.bridge;

import com.google.gson.*;
import com.google.gson.stream.JsonReader;
import com.google.gson.stream.JsonToken;
import com.mojang.brigadier.arguments.StringArgumentType;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.TagParser;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.TicketType;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.Property;
import net.minecraft.world.level.chunk.ChunkAccess;
import net.minecraft.world.level.chunk.status.ChunkStatus;
import net.minecraft.world.level.storage.LevelResource;
import net.neoforged.fml.ModList;
import net.neoforged.fml.loading.FMLPaths;
import net.neoforged.neoforge.capabilities.Capabilities;
import net.neoforged.neoforge.event.RegisterCommandsEvent;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.DigestInputStream;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.CompletableFuture;

/** Future-candidate slice: real read-only hub inspection and admission, not setup.
 * No block/item/entity write, network creation, assembly, connection setter or
 * simulated motion lives here. Parent wiring must supply a shared world lease.
 */
public final class AttractionSupport {
    public interface Lease extends AutoCloseable {
        boolean valid();
        void close() throws Exception;
    }
    public interface Interlock {
        Lease acquire(String owner, boolean temporarySimulation) throws Exception;
    }
    private enum Phase { IDLE, HASH_INPUTS, GEOMETRY_CUSTODY, READY, VERIFY_LIVE, OBSERVE, CLEANUP_REQUIRED }
    private static final TicketType<ChunkPos> TICKET=TicketType.create("awft_attraction_admission",Comparator.comparingLong(ChunkPos::toLong));
    private static final int MAX_POSITIONS=45000, MAX_CHUNKS=32, MAX_TICKS=3600, READY_TICKS=400;
    private static final long WORK_NS=4_000_000L;
    private static final String VERIFIED_STATUS="verified actual block identities, orientation, block entities and supplied inventories";
    private static final Gson JSON=new Gson();
    private final Path home=FMLPaths.GAMEDIR.get().resolve("..").toAbsolutePath().normalize();
    private final Path directory=home.resolve("dashboard/settlement");
    private final String expectedCandidate,expectedBridgeVersion;
    private final Interlock interlock;
    private final Map<String,Object> report=new LinkedHashMap<>();
    private final List<JsonObject> hashInputs=new ArrayList<>(),geometry=new ArrayList<>();
    private final Set<Path> hashedPaths=new HashSet<>();
    private final LinkedHashMap<BlockPos,Expected> targets=new LinkedHashMap<>();
    private final LinkedHashSet<ChunkPos> chunks=new LinkedHashSet<>(),tickets=new LinkedHashSet<>();
    private final List<Map<String,Object>> differences=new ArrayList<>();
    private JsonObject envelope,manifest,plan;
    private Path bundle;
    private ServerLevel level;
    private Lease lease;
    private Phase phase=Phase.IDLE;
    private String action="idle",requestedOutcome;
    private int elapsed,phaseTicks,hashIndex,geometryIndex,liveIndex,failures;
    private long nextWrite,tickStarted;
    private HashCursor hashing;
    private GeometryCursor scanning;
    private List<Expected> live;
    private final Map<ChunkPos,CompletableFuture<?>> pending=new LinkedHashMap<>();

    public AttractionSupport(String expectedCandidate,String expectedBridgeVersion,Interlock interlock) {
        this.expectedCandidate=Objects.requireNonNull(expectedCandidate);
        this.expectedBridgeVersion=Objects.requireNonNull(expectedBridgeVersion);
        this.interlock=Objects.requireNonNull(interlock,"An explicit shared world-operation interlock is mandatory");
        if(expectedCandidate.isBlank() || expectedBridgeVersion.isBlank())throw new IllegalArgumentException("Pin the future candidate and bridge version in parent wiring");
    }
    public boolean busy(){return phase!=Phase.IDLE;}

    public void commands(RegisterCommandsEvent event) {
        var root=Commands.literal("awftattractions").requires(s->s.getEntity()==null && s.hasPermission(4));
        for(String operation:List.of("inspect","admit"))root.then(Commands.literal(operation)
            .then(Commands.argument("bundle",StringArgumentType.word())
            .then(Commands.argument("sha256",StringArgumentType.word()).executes(c->{
                try {begin(c.getSource().getServer(),operation,StringArgumentType.getString(c,"bundle"),StringArgumentType.getString(c,"sha256"));return 1;}
                catch(Exception error){throw new RuntimeException(error);}
            }))));
        for(String unsupported:List.of("setup","assemble","connect","commission","run"))root.then(Commands.literal(unsupported).executes(c->{
            throw new IllegalStateException("Unsupported in this source slice; no attraction mutation was performed");
        }));
        root.then(Commands.literal("status").executes(c->{c.getSource().sendSuccess(()->Component.literal(JSON.toJson(report)),false);return 1;}));
        root.then(Commands.literal("cancel").executes(c->{finish("cancelled; native hub preserved");return 1;}));
        event.getDispatcher().register(root);
    }

    private static String sha(byte[] raw)throws Exception{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(raw));}
    private static int integer(JsonElement value){return value.getAsBigDecimal().intValueExact();}
    private static BlockPos position(JsonArray row) {
        if(row==null || row.size()!=3)throw new IllegalArgumentException("Expected one exact hub position");
        int x=integer(row.get(0)),y=integer(row.get(1)),z=integer(row.get(2));
        if(x<1292 || x>1320 || z< -1030 || z> -904 || y<56 || y>88)throw new IllegalArgumentException("Position escaped the reviewed hub reserve");
        return new BlockPos(x,y,z);
    }
    private Path owned(String relative)throws Exception {
        Path input=Path.of(relative);
        if(input.isAbsolute() || relative.indexOf('\\')>=0 || relative.indexOf(':')>=0 || relative.isBlank())throw new IllegalArgumentException("Use an owned home-relative path");
        for(Path part:input)if(part.toString().equals("..") || part.toString().equals("."))throw new IllegalArgumentException("Parent path is not admission evidence");
        Path result=home.resolve(input).normalize();
        for(Path current=result;current!=null && !current.equals(home);current=current.getParent())
            if(Files.isSymbolicLink(current) || !current.toRealPath().equals(current.toAbsolutePath().normalize()))
                throw new IllegalArgumentException("Linked or redirected admission evidence is refused");
        if(!result.toRealPath().startsWith(home.toRealPath()) || !Files.isRegularFile(result))throw new IllegalArgumentException("Evidence escaped the owned runtime");
        return result;
    }
    private Path file(JsonObject ref,long cap)throws Exception {
        String expected=ref.get("sha256").getAsString();long bytes=ref.get("bytes").getAsLong();
        if(!expected.matches("[a-f0-9]{64}") || bytes<1 || bytes>cap)throw new IllegalArgumentException("Unbounded or unidentified evidence");
        Path result=owned(ref.get("path").getAsString());
        if(Files.size(result)!=bytes)throw new IllegalStateException("Evidence size changed: "+result.getFileName());
        return result;
    }
    private JsonObject read(JsonObject ref,long cap)throws Exception {
        Path path=file(ref,cap);byte[] raw=boundedRead(path,ref.get("bytes").getAsLong());
        if(!sha(raw).equals(ref.get("sha256").getAsString()))throw new IllegalStateException("Exact evidence digest changed: "+path.getFileName());
        return JsonParser.parseString(new String(raw,StandardCharsets.UTF_8)).getAsJsonObject();
    }
    private static byte[] boundedRead(Path path,long bytes)throws Exception {
        if(bytes<1 || bytes>32*1024*1024)throw new IllegalStateException("Unbounded direct evidence read");
        try(InputStream stream=Files.newInputStream(path)){
            byte[] raw=stream.readNBytes((int)bytes+1);
            if(raw.length!=bytes)throw new IllegalStateException("Evidence changed during bounded read");return raw;
        }
    }
    private JsonObject ref(String key){return envelope.getAsJsonObject(key);}
    private void queue(JsonObject ref,long cap)throws Exception {
        Path path=file(ref,cap);
        if(hashedPaths.add(path))hashInputs.add(ref);
    }
    private void copiedSource(String name,String expected)throws Exception {
        JsonObject copy=envelope.getAsJsonObject("source_copies").getAsJsonObject(name);
        if(!copy.get("sha256").getAsString().equals(expected))throw new IllegalStateException("Source custody differs");
        JsonObject binding=copy.deepCopy();binding.addProperty("path",home.relativize(bundle.resolve(name)).toString().replace('\\','/'));
        queue(binding,256*1024);
    }
    private JsonObject verification(String name,String expected,int count)throws Exception {
        JsonObject binding=envelope.getAsJsonObject(name),proof=read(binding.getAsJsonObject("receipt"),512*1024);
        JsonObject complete=binding.getAsJsonObject("complete");Path marker=file(complete,128);
        if(!marker.equals(file(binding.getAsJsonObject("receipt"),512*1024).resolveSibling(
            file(binding.getAsJsonObject("receipt"),512*1024).getFileName()+".complete")))
            throw new IllegalStateException("Completion marker must be the exact receipt's immutable companion");
        byte[] raw=boundedRead(marker,complete.get("bytes").getAsLong());
        if(!sha(raw).equals(complete.get("sha256").getAsString()) || !new String(raw,StandardCharsets.UTF_8).trim().equals(binding.getAsJsonObject("receipt").get("sha256").getAsString()))
            throw new IllegalStateException("An immutable native completion marker is required");
        if(!proof.get("operation").getAsString().equals("verify") || !proof.get("plan_sha256").getAsString().equals(expected) ||
           integer(proof.get("blocks"))!=count || integer(proof.get("failures"))!=0 || !proof.has("finished") ||
           !proof.get("status").getAsString().equals(VERIFIED_STATUS) || proof.has("error") ||
           Instant.parse(proof.get("finished").getAsString()).isBefore(Instant.parse(proof.get("started").getAsString())))
            throw new IllegalStateException("The exact hub native before/after verification has not passed");
        return proof;
    }
    private void begin(MinecraftServer server,String operation,String name,String expected)throws Exception {
        if(busy() || lease!=null || !tickets.isEmpty() || !name.matches("attraction-admission-[a-f0-9]{16}") || !expected.matches("[a-f0-9]{64}"))
            throw new IllegalStateException("Admission tool busy, cleanup outstanding or invalid immutable bundle");
        if(!name.equals("attraction-admission-"+expected.substring(0,16)))throw new IllegalStateException("The immutable bundle name does not match its exact envelope");
        if(operation.equals("admit") && !server.getPlayerList().getPlayers().isEmpty())throw new IllegalStateException("Native admission with temporary simulation requires an empty server");
        Path request=owned("dashboard/settlement/"+name+"/admission.json");bundle=request.getParent();
        long requestBytes=Files.size(request);if(requestBytes<1 || requestBytes>256*1024)throw new IllegalStateException("Invalid bounded admission bundle");
        byte[] raw=boundedRead(request,requestBytes);if(!sha(raw).equals(expected))throw new IllegalStateException("Exact admission envelope digest differs");
        envelope=JsonParser.parseString(new String(raw,StandardCharsets.UTF_8)).getAsJsonObject();
        if(!envelope.get("format").getAsString().equals("awft-attraction-admission:1") ||
           !envelope.get("candidate_version").getAsString().equals(expectedCandidate) ||
           !envelope.get("bridge_version").getAsString().equals(expectedBridgeVersion) ||
           !ModList.get().getModContainerById("awft_control_bridge").orElseThrow().getModInfo().getVersion().toString().equals(expectedBridgeVersion))
            throw new IllegalStateException("This envelope does not match the running future candidate/bridge");
        try(InputStream stream=AttractionSupport.class.getResourceAsStream("AttractionSupport.class")) {
            if(stream==null)throw new IllegalStateException("Native admission class identity unavailable");
            byte[] code=stream.readNBytes(256*1024+1);
            if(code.length>256*1024 || !sha(code).equals(envelope.get("native_class_sha256").getAsString()))throw new IllegalStateException("Actual running admission class differs from the built candidate");
        }
        reset();level=Objects.requireNonNull(server.overworld());action=operation;phase=Phase.HASH_INPUTS;
        long bindingStarted=System.nanoTime();
        report.put("operation",operation);report.put("started",Instant.now().toString());report.put("admission_sha256",expected);
        report.put("candidate_version",expectedCandidate);report.put("bridge_version",expectedBridgeVersion);
        report.put("unsupported_actions",List.of("setup","assemble","connect","commission","run"));
        try {
            lease=interlock.acquire("attractions/"+operation,operation.equals("admit"));
            if(lease==null || !lease.valid())throw new IllegalStateException("The shared world-operation lease was not granted");
            loadBindings(server);phase=Phase.HASH_INPUTS;report.put("status","hashing exact owned evidence; no hub mutation");
            report.put("bounded_binding_read_ms",(System.nanoTime()-bindingStarted)/1_000_000.0);
            NativeJournal.progress(directory,"attraction-status.json",report);
        }catch(Exception error){report.put("error",error.toString());finish("admission refused; native hub preserved");throw error;}
    }

    private void reset() {
        hashInputs.clear();geometry.clear();hashedPaths.clear();targets.clear();chunks.clear();pending.clear();differences.clear();report.clear();
        elapsed=phaseTicks=hashIndex=geometryIndex=liveIndex=failures=0;requestedOutcome=null;nextWrite=tickStarted=0;
    }
    private void loadBindings(MinecraftServer server)throws Exception {
        manifest=read(ref("hub_manifest"),4*1024*1024);plan=read(ref("plan"),4*1024*1024);
        JsonObject before=read(ref("preconditions"),4*1024*1024),build=read(ref("build_receipt"),256*1024);
        if(!manifest.get("format").getAsString().equals("awft-settlement-attractions:1") ||
           !manifest.get("plan_sha256").getAsString().equals(ref("plan").get("sha256").getAsString()) ||
           !manifest.get("preconditions_sha256").getAsString().equals(ref("preconditions").get("sha256").getAsString()))throw new IllegalStateException("The frozen hub bindings differ");
        if(!build.get("format").getAsString().equals("awft-attraction-native-build:1") ||
           !build.get("candidate_version").getAsString().equals(expectedCandidate) || !build.get("bridge_version").getAsString().equals(expectedBridgeVersion) ||
           !build.get("attraction_class_sha256").getAsString().equals(envelope.get("native_class_sha256").getAsString()) ||
            !build.get("bridge_jar_file").getAsString().equals(ref("bridge_jar").get("path").getAsString()) ||
           !build.get("bridge_jar_sha256").getAsString().equals(ref("bridge_jar").get("sha256").getAsString()))throw new IllegalStateException("Native build attestation differs");
        copiedSource("authoring_source.py",manifest.get("source_sha256").getAsString());
        copiedSource("AttractionSupport.java",build.get("native_source_sha256").getAsString());
        for(JsonObject doc:List.of(plan,before)) {
            if(!doc.get("format").getAsString().equals("awft-native-settlement:1") ||
               !doc.get("seed").getAsString().equals(Long.toString(level.getSeed())) ||
               !Path.of(doc.get("world_path").getAsString()).toAbsolutePath().normalize().equals(server.getWorldPath(LevelResource.ROOT).toAbsolutePath().normalize()) ||
               !doc.getAsJsonArray("commands").isEmpty())throw new IllegalStateException("Wrong world or unexpected native action");
        }
        if(!before.getAsJsonArray("block_entities").isEmpty())throw new IllegalStateException("Prior-state checks cannot load BE data");
        JsonObject backup=read(ref("backup_receipt"),4096),active=read(ref("active_receipt"),65536),installed=read(ref("installed_receipt"),1024*1024);
        String pack=envelope.get("pack_sha256").getAsString();
        if(!backup.get("verified").getAsBoolean() || !backup.get("id").getAsString().equals(manifest.get("backup_id").getAsString()) ||
           !backup.get("sha256").getAsString().equals(ref("backup_archive").get("sha256").getAsString()) ||
           !backup.get("sha256").getAsString().equals(plan.get("backup_sha256").getAsString()) ||
           !backup.get("sha256").getAsString().equals(before.get("backup_sha256").getAsString()) ||
           !active.get("version").getAsString().equals(expectedCandidate) || !installed.get("pack_version").getAsString().equals(expectedCandidate) ||
           !active.get("pack_sha256").getAsString().equals(pack) || !installed.get("pack_sha256").getAsString().equals(pack) || !build.get("pack_sha256").getAsString().equals(pack))
            throw new IllegalStateException("Current verified backup or actual installed candidate differs");
        requireCanonical(ref("backup_receipt"),"dashboard/settlement/backup-receipt.json");requireCanonical(ref("active_receipt"),"packwiz/active.json");requireCanonical(ref("installed_receipt"),"server/installed.json");
        JsonArray rows=plan.getAsJsonArray("blocks"),palette=plan.getAsJsonArray("palette");
        if(rows.size()<1 || rows.size()>MAX_POSITIONS || palette.size()>8192 || rows.size()!=integer(manifest.get("placements")))throw new IllegalStateException("Unbounded hub geometry");
        for(JsonElement value:rows){JsonArray row=value.getAsJsonArray();if(row.size()!=4)throw new IllegalStateException("Invalid block row");
            BlockPos pos=position(new JsonArrayBuilder().add(row.get(0)).add(row.get(1)).add(row.get(2)).array);
            int index=integer(row.get(3));if(index<0 || index>=palette.size())throw new IllegalStateException("Invalid palette index");
            Expected item=parse(pos,palette.get(index).getAsString());if(targets.put(pos,item)!=null)throw new IllegalStateException("Duplicate hub target");chunks.add(new ChunkPos(pos));}
        if(chunks.size()>MAX_CHUNKS || plan.getAsJsonArray("block_entities").size()>64)throw new IllegalStateException("Hub chunk/BE bound exceeded");
        validateSystems();
        Set<BlockPos> entityTags=new HashSet<>();for(JsonElement value:plan.getAsJsonArray("block_entities")){
            JsonObject tag=value.getAsJsonObject();BlockPos pos=position(tag.getAsJsonArray("pos"));String nbt=tag.get("nbt").getAsString();
            if(!targets.containsKey(pos) || !entityTags.add(pos) || nbt.length()>16384)throw new IllegalStateException("Unbounded or unowned native BE declaration");
            TagParser.parseTag(nbt);
        }
        Map<BlockPos,String> previous=rawStates(before);Set<BlockPos> audited=new HashSet<>();
        for(JsonElement value:manifest.getAsJsonArray("expected_previous")){JsonObject row=value.getAsJsonObject();BlockPos pos=position(row.getAsJsonArray("position"));
            Expected item=targets.get(pos);if(item==null || !audited.add(pos) || !row.get("replacement").getAsString().equals(item.text) || !row.get("previous").getAsString().equals(previous.get(pos)))throw new IllegalStateException("Exact prior-state custody differs");}
        if(!audited.equals(targets.keySet()) || !previous.keySet().equals(targets.keySet()))throw new IllegalStateException("Every target needs its exact before-state custody");
        JsonObject beforeProof=verification("before_verification",ref("preconditions").get("sha256").getAsString(),targets.size());
        JsonObject afterProof=verification("after_verification",ref("plan").get("sha256").getAsString(),targets.size());
        if(Instant.parse(beforeProof.get("finished").getAsString()).isAfter(Instant.parse(afterProof.get("started").getAsString())))
            throw new IllegalStateException("The completed native before-state check must precede the completed after-state check");
        Set<String> sourceGeometry=new HashSet<>(),provided=new HashSet<>();
        for(JsonElement value:manifest.getAsJsonArray("provenance")){JsonObject row=value.getAsJsonObject();
            if(row.has("native_verification") || row.has("role") && row.get("role").getAsString().equals("Completed detail exclusion"))sourceGeometry.add(row.get("file").getAsString()+":"+row.get("sha256").getAsString());}
        for(JsonElement value:envelope.getAsJsonArray("geometry")){JsonObject row=value.getAsJsonObject();Path path=file(row,32*1024*1024);provided.add(path.getFileName()+":"+row.get("sha256").getAsString());geometry.add(row);queue(row,32*1024*1024);}
        if(geometry.size()!=15 || !provided.equals(sourceGeometry))throw new IllegalStateException("All ten masters and five detail sources must remain fixed");
        Set<String> installedFiles=new HashSet<>();for(JsonElement value:installed.getAsJsonArray("files"))installedFiles.add(value.getAsString());
        JsonArray mods=envelope.getAsJsonArray("native_mods");if(mods.size()!=4)throw new IllegalStateException("Four exact attraction mod pins are required");
        Set<String> pinned=new HashSet<>();for(JsonElement value:manifest.getAsJsonArray("provenance")){JsonObject row=value.getAsJsonObject();if(row.has("role") && row.get("role").getAsString().equals("Read-only pinned native API/recipe evidence"))pinned.add(row.get("file").getAsString()+":"+row.get("sha256").getAsString());}
        Set<String> actual=new HashSet<>();for(JsonElement value:mods){JsonObject row=value.getAsJsonObject();Path path=file(row,32*1024*1024);if(!path.getParent().equals(home.resolve("server/mods")) || !installedFiles.contains(path.getFileName().toString()))throw new IllegalStateException("The pinned native mod is not actually installed");actual.add(path.getFileName()+":"+row.get("sha256").getAsString());queue(row,32*1024*1024);}
        if(!actual.equals(pinned))throw new IllegalStateException("Native dependency API pins differ");
        Path jar=file(ref("bridge_jar"),32*1024*1024);if(!jar.getParent().equals(home.resolve("server/mods")) || !installedFiles.contains(jar.getFileName().toString()))throw new IllegalStateException("Bridge is not installed");
        for(String key:List.of("bridge_jar","hub_manifest","plan","preconditions","build_receipt","backup_receipt","active_receipt","installed_receipt"))queue(ref(key),32*1024*1024);
        queue(ref("backup_archive"),256*1024*1024);
        live=new ArrayList<>(targets.values());report.put("targets",targets.size());report.put("chunks",chunks.size());report.put("hub_plan_sha256",ref("plan").get("sha256").getAsString());
    }
    private void requireCanonical(JsonObject ref,String name)throws Exception {if(!file(ref,1024*1024).equals(home.resolve(name)))throw new IllegalStateException("Current receipt cannot be substituted by an archived copy");}
    private BlockPos targetPosition(JsonArray value) {
        BlockPos pos=position(value);if(!targets.containsKey(pos))throw new IllegalStateException("Native component escaped the verified target set");return pos;
    }
    private void validateSystems() {
        JsonObject systems=manifest.getAsJsonObject("systems"),mill=systems.getAsJsonObject("watermill"),air=systems.getAsJsonObject("pneumatic"),
            tube=systems.getAsJsonObject("hypertube"),rail=systems.getAsJsonObject("railway");
        for(String key:List.of("clutch","stop_lever","millstone","gearbox","grain_chest","press","depot","starter_chest"))targetPosition(mill.getAsJsonArray(key));
        for(String key:List.of("extractor","pump","drive_cog","inserter","output_chest"))targetPosition(air.getAsJsonArray(key));
        if(mill.getAsJsonArray("wheels").size()!=3 || tube.getAsJsonArray("entrances").size()!=2 || rail.getAsJsonArray("stations").size()!=2)
            throw new IllegalStateException("The bounded native hub component inventory differs");
        for(JsonElement value:mill.getAsJsonArray("wheels"))targetPosition(value.getAsJsonArray());
        for(JsonElement value:tube.getAsJsonArray("entrances"))targetPosition(value.getAsJsonArray());
        targetPosition(tube.getAsJsonArray("midpoint_anchor"));
        for(JsonElement value:rail.getAsJsonArray("stations")){JsonObject station=value.getAsJsonObject();targetPosition(station.getAsJsonArray("position"));targetPosition(station.getAsJsonArray("target_track"));}
    }
    private static final class JsonArrayBuilder {final JsonArray array=new JsonArray();JsonArrayBuilder add(JsonElement value){array.add(value);return this;}}
    private Map<BlockPos,String> rawStates(JsonObject doc){Map<BlockPos,String> result=new HashMap<>();JsonArray palette=doc.getAsJsonArray("palette");
        if(doc.getAsJsonArray("blocks").size()>MAX_POSITIONS || palette.size()>8192)throw new IllegalStateException("Unbounded prior states");
        for(JsonElement value:doc.getAsJsonArray("blocks")){JsonArray row=value.getAsJsonArray();if(row.size()!=4)throw new IllegalStateException("Invalid prior state row");BlockPos pos=position(new JsonArrayBuilder().add(row.get(0)).add(row.get(1)).add(row.get(2)).array);int index=integer(row.get(3));if(index<0 || index>=palette.size() || result.put(pos,palette.get(index).getAsString())!=null)throw new IllegalStateException("Duplicate/invalid prior state");}return result;}
    private record Expected(BlockPos pos,BlockState state,Map<String,String> explicit,String text) {}
    @SuppressWarnings({"rawtypes","unchecked"})
    private Expected parse(BlockPos pos,String text) {
        if(text.length()>1024)throw new IllegalStateException("Oversized block state");int bracket=text.indexOf('[');String key=bracket<0?text:text.substring(0,bracket);
        ResourceLocation id=ResourceLocation.parse(key);if(!BuiltInRegistries.BLOCK.containsKey(id))throw new IllegalStateException("Unregistered actual block "+key);
        BlockState state=BuiltInRegistries.BLOCK.get(id).defaultBlockState();Map<String,String> explicit=new LinkedHashMap<>();
        if(bracket>=0){if(!text.endsWith("]"))throw new IllegalStateException("Malformed exact block state");for(String pair:text.substring(bracket+1,text.length()-1).split(",")){String[] parts=pair.split("=",-1);if(parts.length!=2 || explicit.put(parts[0],parts[1])!=null)throw new IllegalStateException("Invalid property");Property property=state.getBlock().getStateDefinition().getProperty(parts[0]);if(property==null)throw new IllegalStateException("Unknown property");Optional value=property.getValue(parts[1]);if(value.isEmpty())throw new IllegalStateException("Unknown property value");state=(BlockState)state.setValue(property,(Comparable)value.get());}}
        return new Expected(pos,state,explicit,text);
    }
    @SuppressWarnings({"rawtypes","unchecked"})
    private boolean matches(BlockState actual,Expected expected) {
        if(actual.getBlock()!=expected.state.getBlock())return false;
        for(String name:expected.explicit.keySet()){Property property=actual.getBlock().getStateDefinition().getProperty(name);if(property==null || !actual.getValue(property).equals(expected.state.getValue(property)))return false;}return true;
    }

    private final class HashCursor implements AutoCloseable {
        final JsonObject ref;final InputStream stream;final MessageDigest digest=MessageDigest.getInstance("SHA-256");final byte[] buffer=new byte[65536];long bytes;
        HashCursor(JsonObject ref)throws Exception{this.ref=ref;stream=Files.newInputStream(file(ref,256*1024*1024));}
        boolean step()throws Exception {int n=stream.read(buffer);if(n<0){if(bytes!=ref.get("bytes").getAsLong() || !HexFormat.of().formatHex(digest.digest()).equals(ref.get("sha256").getAsString()))throw new IllegalStateException("Evidence changed while hashing");close();return true;}bytes+=n;if(bytes>ref.get("bytes").getAsLong())throw new IllegalStateException("Evidence grew beyond its declared byte bound");digest.update(buffer,0,n);return false;}
        public void close()throws Exception{stream.close();}
    }
    private final class GeometryCursor implements AutoCloseable {
        final JsonObject ref;final MessageDigest digest=MessageDigest.getInstance("SHA-256");final JsonReader reader;boolean started,inBlocks,sawBlocks;int rows;
        GeometryCursor(JsonObject ref)throws Exception{this.ref=ref;reader=new JsonReader(new InputStreamReader(new DigestInputStream(new BoundedInput(Files.newInputStream(file(ref,32*1024*1024)),ref.get("bytes").getAsLong()),digest),StandardCharsets.UTF_8));}
        boolean step()throws Exception {
            // Parse only after the owner stores this cursor, so a malformed
            // initial token cannot strand an untracked file handle.
            if(!started){reader.beginObject();started=true;return false;}
            if(inBlocks){if(reader.hasNext()){reader.beginArray();int x=reader.nextInt(),y=reader.nextInt(),z=reader.nextInt();reader.nextInt();if(reader.hasNext())throw new IllegalStateException("Malformed fixed geometry row");reader.endArray();if(++rows>550000)throw new IllegalStateException("Fixed geometry exceeds its declared finite maximum");if(targets.containsKey(new BlockPos(x,y,z)))throw new IllegalStateException("Hub intersects completed fixed geometry, including authored air");return false;}reader.endArray();inBlocks=false;}
            if(reader.hasNext()){String name=reader.nextName();if(name.equals("blocks")){if(sawBlocks)throw new IllegalStateException("Duplicate fixed block collection");sawBlocks=true;reader.beginArray();inBlocks=true;}else reader.skipValue();return false;}
            reader.endObject();
            // Force the parser through trailing whitespace to the underlying EOF
            // before comparing its streaming byte digest; buffered decoding alone
            // must never accidentally leave a suffix outside the custody check.
            if(reader.peek()!=JsonToken.END_DOCUMENT || rows==0 ||
                !HexFormat.of().formatHex(digest.digest()).equals(ref.get("sha256").getAsString()))
                throw new IllegalStateException("Fixed geometry changed during custody scan");close();return true;
        }
        public void close()throws Exception{reader.close();}
    }
    private static final class BoundedInput extends FilterInputStream {
        final long maximum;long consumed;
        BoundedInput(InputStream stream,long maximum){super(stream);this.maximum=maximum;}
        private int counted(int count)throws IOException {if(count>0 && (consumed+=count)>maximum)throw new IOException("Evidence grew during bounded custody scan");return count;}
        public int read()throws IOException {int value=in.read();counted(value<0?-1:1);return value;}
        public int read(byte[] value,int offset,int length)throws IOException {
            if(length==0)return 0;int request=(int)Math.min(length,maximum-consumed+1);
            return counted(in.read(value,offset,request));
        }
    }

    private void simulationTicket(ChunkPos chunk,boolean add)throws Exception {
        level.getChunkSource().getClass().getMethod(add?"addRegionTicket":"removeRegionTicket",TicketType.class,ChunkPos.class,int.class,Object.class,boolean.class).invoke(level.getChunkSource(),TICKET,chunk,2,chunk,true);
    }
    private boolean ready(ChunkPos chunk) {
        BlockPos center=new BlockPos(chunk.getMinBlockX()+8,68,chunk.getMinBlockZ()+8);long key=chunk.toLong();
        return level.getChunkSource().getChunkNow(chunk.x,chunk.z)!=null && BridgePhaseGate.simulationReady(level.getChunkSource().isPositionTicking(key),level.isPositionEntityTicking(center),level.areEntitiesLoaded(key),false);
    }
    private void requestChunks()throws Exception {
        if(action.equals("inspect"))return;
        for(ChunkPos chunk:chunks){tickets.add(chunk);simulationTicket(chunk,true);
            pending.put(chunk,((worldfortwo.bridge.mixin.ChunkCacheAccess)(Object)level.getChunkSource()).awftQueueChunk(chunk.x,chunk.z,ChunkStatus.FULL,false));}
        report.put("temporary_simulation_tickets",tickets.size());
    }
    private boolean loaded() {
        List<List<Integer>> missing=new ArrayList<>();for(ChunkPos chunk:chunks)if(!ready(chunk))missing.add(List.of(chunk.x,chunk.z));
        report.put("unready_chunks",missing);return missing.isEmpty();
    }
    private boolean ready(BlockPos pos,boolean needsSpeedUpdate) {
        long key=ChunkPos.asLong(pos);
        return level.getChunkSource().getChunkNow(pos.getX()>>4,pos.getZ()>>4)!=null &&
            BridgePhaseGate.simulationReady(level.getChunkSource().isPositionTicking(key),
                level.isPositionEntityTicking(pos),level.areEntitiesLoaded(key),needsSpeedUpdate);
    }
    private void recordWork() {
        if(tickStarted==0)return;double ms=(System.nanoTime()-tickStarted)/1_000_000.0;
        report.put("last_work_ms",ms);report.put("max_work_ms",Math.max(ms,((Number)report.getOrDefault("max_work_ms",0d)).doubleValue()));
    }

    public void tick(MinecraftServer server) {
        if(phase==Phase.IDLE || phase==Phase.CLEANUP_REQUIRED)return;long begin=System.nanoTime();tickStarted=begin;
        try {
            if(lease==null || !lease.valid())throw new IllegalStateException("Shared world-operation lease was lost");
            if(action.equals("admit") && !server.getPlayerList().getPlayers().isEmpty())throw new IllegalStateException("Player joined; native admission stopped without hub mutation");
            if(++elapsed>MAX_TICKS)throw new IllegalStateException("Bounded native admission timed out");phaseTicks++;
            int work=0;
            while(work++<512 && System.nanoTime()-begin<WORK_NS) {
                if(phase==Phase.HASH_INPUTS){if(hashIndex==hashInputs.size()){phase=Phase.GEOMETRY_CUSTODY;phaseTicks=0;continue;}if(hashing==null)hashing=new HashCursor(hashInputs.get(hashIndex));if(hashing.step()){hashing=null;hashIndex++;}}
                else if(phase==Phase.GEOMETRY_CUSTODY){if(geometryIndex==geometry.size()){requestChunks();phase=Phase.READY;phaseTicks=0;continue;}if(scanning==null)scanning=new GeometryCursor(geometry.get(geometryIndex));if(scanning.step()){scanning=null;geometryIndex++;}}
                else if(phase==Phase.READY){for(CompletableFuture<?> future:pending.values())if(future.isCompletedExceptionally())throw new IllegalStateException("Native target chunk load failed");if(!loaded()){if(action.equals("inspect") || phaseTicks>READY_TICKS)throw new IllegalStateException("Every target must already be FULL, block/entity ticking and entity-loaded; inspect does not add tickets");break;}phase=Phase.VERIFY_LIVE;phaseTicks=0;}
                else if(phase==Phase.VERIFY_LIVE){if(!loaded())throw new IllegalStateException("Chunk/entity readiness changed during native verification");if(liveIndex==live.size()){phase=Phase.OBSERVE;phaseTicks=0;continue;}
                    Expected item=live.get(liveIndex++);BlockState actual=level.getChunkSource().getChunkNow(item.pos.getX()>>4,item.pos.getZ()>>4).getBlockState(item.pos);
                    if(!matches(actual,item)){failures++;if(differences.size()<32)differences.add(Map.of("position",List.of(item.pos.getX(),item.pos.getY(),item.pos.getZ()),"expected",item.text,"actual",actual.toString()));}}
                else if(phase==Phase.OBSERVE){if(!loaded())throw new IllegalStateException("Chunk/entity readiness changed before final native observations");observe(server);return;}
            }
            report.put("phase",phase.name());report.put("ticks",elapsed);report.put("verified_targets",liveIndex);report.put("geometry_failures",failures);report.put("differences",differences);
            recordWork();
            if(System.nanoTime()>nextWrite){NativeJournal.progress(directory,"attraction-status.json",report);nextWrite=System.nanoTime()+5_000_000_000L;}
        }catch(Exception error){report.put("error",error.toString());finish("native admission refused; hub preserved");}
        finally{recordWork();tickStarted=0;}
    }

    private Object getter(Object entity,String method)throws Exception {
        try{return entity.getClass().getMethod(method).invoke(entity);}
        catch(java.lang.reflect.InvocationTargetException error){
            throw new IllegalStateException("Native read-only query failed: "+entity.getClass().getName()+"."+method+": "+error.getCause(),error.getCause());
        }
    }
    private Map<String,Object> component(BlockPos pos)throws Exception {
        if(!targets.containsKey(pos) || !ready(pos,false))throw new IllegalStateException("Component query is not a verified, ready hub target");
        Map<String,Object> row=new LinkedHashMap<>();row.put("position",List.of(pos.getX(),pos.getY(),pos.getZ()));row.put("state",level.getBlockState(pos).toString());
        long chunk=ChunkPos.asLong(pos);row.put("block_ticking",level.getChunkSource().isPositionTicking(chunk));
        row.put("entity_ticking",level.isPositionEntityTicking(pos));row.put("entities_loaded",level.areEntitiesLoaded(chunk));
        BlockEntity entity=level.getBlockEntity(pos);if(entity==null)return row;String type=entity.getClass().getName();row.put("native_class",type);
        for(String name:List.of("getSpeed","getTheoreticalSpeed","hasNetwork","isOverStressed","needsSpeedUpdate","isRunning"))try{row.put(name,getter(entity,name));}catch(NoSuchMethodException ignored){}
        if(type.equals("com.hwmods.overpressure.PneumaticConnectionBlockEntity")){ItemStack filter=(ItemStack)getter(entity,"getFilter");row.put("filter",filter.isEmpty()?"empty":BuiltInRegistries.ITEM.getKey(filter.getItem()).toString());}
        if(type.equals("com.simibubi.create.content.trains.station.StationBlockEntity")){Object point=entity.getClass().getField("edgePoint").get(entity);row.put("valid_track",getter(point,"hasValidTrack"));row.put("target_position",String.valueOf(getter(point,"getGlobalPosition")));Object direction=getter(point,"getTargetDirection");row.put("target_direction",direction instanceof Enum<?> e?e.name():String.valueOf(direction));}
        if(type.startsWith("com.pedrorok.hypertube.blocks.blockentities.")){Object values=getter(entity,"getConnections");row.put("native_connections",((Collection<?>)values).size());}
        String nbt=entity.saveWithFullMetadata(level.registryAccess()).toString();if(nbt.length()>16384)throw new IllegalStateException("A hub BE saved state exceeds the private evidence bound");row.put("native_saved_state",nbt);
        return row;
    }
    private int inventory(BlockPos pos)throws Exception {
        if(!targets.containsKey(pos) || !ready(pos,false))throw new IllegalStateException("Inventory query is not a verified, ready hub target");
        var handler=((net.neoforged.neoforge.common.extensions.ILevelExtension)(Object)level).getCapability(Capabilities.ItemHandler.BLOCK,pos,null);if(handler==null || handler.getSlots()>256)throw new IllegalStateException("Native active inventory capability unavailable or unbounded at "+pos);
        int count=0;for(int i=0;i<handler.getSlots();i++)count+=handler.getStackInSlot(i).getCount();return count;
    }
    private boolean powered(BlockPos pos) {
        BlockState state=level.getBlockState(pos);for(Property<?> property:state.getProperties())if(property.getName().equals("powered"))return Boolean.TRUE.equals(state.getValue(property));return false;
    }
    private void observe(MinecraftServer server)throws Exception {
        // These current files are revalidated immediately before the final
        // snapshot. A completed snapshot is evidence, never a reusable authority
        // token for a later mutation or another world-operation lease.
        read(ref("backup_receipt"),4096);read(ref("active_receipt"),65536);read(ref("installed_receipt"),1024*1024);
        List<Map<String,Object>> rows=new ArrayList<>();List<String> refusals=new ArrayList<>();
        for(JsonElement value:plan.getAsJsonArray("block_entities")){JsonObject tag=value.getAsJsonObject();BlockPos pos=position(tag.getAsJsonArray("pos"));if(level.getBlockEntity(pos)==null)refusals.add("Expected native BE missing at "+pos);TagParser.parseTag(tag.get("nbt").getAsString());}
        JsonObject systems=manifest.getAsJsonObject("systems"),mill=systems.getAsJsonObject("watermill"),air=systems.getAsJsonObject("pneumatic"),tube=systems.getAsJsonObject("hypertube"),rail=systems.getAsJsonObject("railway");
        LinkedHashSet<BlockPos> positions=new LinkedHashSet<>();
        for(String key:List.of("clutch","stop_lever","millstone","gearbox","grain_chest","press","depot","starter_chest"))positions.add(position(mill.getAsJsonArray(key)));
        for(JsonElement value:mill.getAsJsonArray("wheels"))positions.add(position(value.getAsJsonArray()));
        for(String key:List.of("extractor","pump","drive_cog","inserter","output_chest"))positions.add(position(air.getAsJsonArray(key)));
        positions.add(position(tube.getAsJsonArray("midpoint_anchor")));for(JsonElement value:tube.getAsJsonArray("entrances"))positions.add(position(value.getAsJsonArray()));
        for(JsonElement value:rail.getAsJsonArray("stations"))positions.add(position(value.getAsJsonObject().getAsJsonArray("position")));
        for(BlockPos pos:positions)rows.add(component(pos));
        if(!powered(position(mill.getAsJsonArray("clutch"))) || !powered(position(mill.getAsJsonArray("stop_lever"))))refusals.add("The actual main clutch and stop lever must both be powered/stopped");
        LinkedHashSet<BlockPos> stopped=new LinkedHashSet<>();for(String key:List.of("millstone","press"))stopped.add(position(mill.getAsJsonArray(key)));stopped.add(position(air.getAsJsonArray("pump")));for(JsonElement value:tube.getAsJsonArray("entrances"))stopped.add(position(value.getAsJsonArray()));
        for(BlockPos pos:stopped){BlockEntity entity=level.getBlockEntity(pos);if(entity==null){refusals.add("Stopped native kinetic BE missing at "+pos);continue;}double speed=((Number)getter(entity,"getSpeed")).doubleValue();boolean simulation=ready(pos,Boolean.TRUE.equals(getter(entity,"needsSpeedUpdate")));if(!simulation || !Double.isFinite(speed) || Math.abs(speed)>.001 || Boolean.TRUE.equals(getter(entity,"isOverStressed")))refusals.add("Stopped native kinetic readiness not established at "+pos);}
        LinkedHashSet<BlockPos> active=new LinkedHashSet<>();active.add(position(mill.getAsJsonArray("grain_chest")));active.add(position(mill.getAsJsonArray("millstone")));active.add(position(mill.getAsJsonArray("depot")));active.add(position(air.getAsJsonArray("output_chest")));
        for(Expected item:live)if(BuiltInRegistries.BLOCK.getKey(item.state.getBlock()).toString().equals("minecraft:hopper"))active.add(item.pos);
        List<Map<String,Object>> inventories=new ArrayList<>();for(BlockPos pos:active){int count=inventory(pos);inventories.add(Map.of("position",List.of(pos.getX(),pos.getY(),pos.getZ()),"items",count));if(count!=0)refusals.add("Native active inventory is not empty at "+pos);}
        List<Map<String,Object>> cargo=new ArrayList<>();
        for(Expected item:live)if(BuiltInRegistries.BLOCK.getKey(item.state.getBlock()).getNamespace().equals("overpressure")){
            BlockEntity entity=level.getBlockEntity(item.pos);
            if(entity==null){refusals.add("Expected native pneumatic BE missing at "+item.pos);continue;}
            // Public pinned PneumaticTubeBlockEntity getter, inherited by the
            // connector and pump. A non-null cargo record is conservatively busy;
            // do not eject, rewrite or serialize an invented empty inventory.
            boolean occupied=getter(entity,"getMovingItem")!=null;
            cargo.add(Map.of("position",List.of(item.pos.getX(),item.pos.getY(),item.pos.getZ()),"native_cargo_present",occupied));
            if(occupied)refusals.add("Native in-flight pneumatic cargo is not empty at "+item.pos);
        }
        BlockEntity extractor=level.getBlockEntity(position(air.getAsJsonArray("extractor")));if(extractor==null || !extractor.getClass().getName().equals("com.hwmods.overpressure.PneumaticConnectionBlockEntity"))refusals.add("Native flour extractor class is missing");else {ItemStack filter=(ItemStack)getter(extractor,"getFilter");if(filter.isEmpty() || !BuiltInRegistries.ITEM.getKey(filter.getItem()).toString().equals(air.get("filter").getAsString()))refusals.add("The actual native extractor filter differs");}
        for(JsonElement value:rail.getAsJsonArray("stations")){JsonObject station=value.getAsJsonObject();BlockEntity entity=level.getBlockEntity(position(station.getAsJsonArray("position")));if(entity==null || !entity.getClass().getName().equals("com.simibubi.create.content.trains.station.StationBlockEntity")){refusals.add("Actual native station missing");continue;}Object point=entity.getClass().getField("edgePoint").get(entity),target=getter(point,"getGlobalPosition"),direction=getter(point,"getTargetDirection");String expected=station.get("target_direction_positive").getAsBoolean()?"POSITIVE":"NEGATIVE";if(!Boolean.TRUE.equals(getter(point,"hasValidTrack")) || !position(station.getAsJsonArray("target_track")).equals(target) || !(direction instanceof Enum<?> e) || !e.name().equals(expected))refusals.add("Actual native station target/graph/direction differs");}
        report.put("components",rows);report.put("active_inventories",inventories);report.put("pneumatic_cargo",cargo);report.put("admission_refusals",refusals);report.put("geometry_failures",failures);report.put("differences",differences);report.put("observation_game_time",level.getGameTime());
        report.put("hub_mutation_calls",0);report.put("explicit_network_creation_calls",0);report.put("train_assembly_and_motion","not implemented or executed");report.put("tube_connection_setup_and_player_travel","not implemented or executed");
        boolean passed=failures==0 && refusals.isEmpty();report.put("native_admission_snapshot_passed",passed);
        if(action.equals("admit") && !passed)throw new IllegalStateException("Actual native hub is not admitted; inspect recorded differences and predicates");
        finish(action.equals("inspect")?"native read-only inspection complete; no setup authority granted":"native admission snapshot passed; future mutations must revalidate in their own same-tick lease");
    }

    private void finish(String outcome) {
        if(phase==Phase.IDLE && lease==null && tickets.isEmpty())return;
        if(requestedOutcome==null)requestedOutcome=outcome;List<String> cleanup=new ArrayList<>();
        try{if(hashing!=null)hashing.close();hashing=null;}catch(Exception e){cleanup.add(e.toString());}
        try{if(scanning!=null)scanning.close();scanning=null;}catch(Exception e){cleanup.add(e.toString());}
        for(ChunkPos chunk:new ArrayList<>(tickets))try{simulationTicket(chunk,false);tickets.remove(chunk);}catch(Exception e){cleanup.add("ticket "+chunk+": "+e);}
        report.put("remaining_owned_tickets",tickets.size());report.put("native_chunk_futures_still_pending",pending.values().stream().filter(v->!v.isDone()).count());
        // Native chunk futures are shared engine work, not cancellable owned
        // worker processes. Release only our identical tickets; never cancel them.
        if(tickets.isEmpty() && hashing==null && scanning==null && lease!=null)try{lease.close();lease=null;}catch(Exception e){cleanup.add("shared lease: "+e);}
        boolean clean=tickets.isEmpty() && hashing==null && scanning==null && lease==null;
        report.put("cleanup_required",!clean);report.put("cleanup_errors",cleanup);report.put("finished",Instant.now().toString());
        report.put("status",clean?requestedOutcome:"cleanup_required; owned handles retained for explicit cancel/stop retry");
        report.put("terminal_phase",phase.name());report.put("ticks",elapsed);report.put("verified_targets",liveIndex);
        report.put("geometry_failures",failures);report.put("differences",differences);report.put("terminal_cleanup_passed",clean);
        phase=clean?Phase.IDLE:Phase.CLEANUP_REQUIRED;
        report.put("phase",phase.name());
        recordWork();
        try{NativeJournal.terminal(directory,"attraction",report);NativeJournal.progress(directory,"attraction-status.json",report);}catch(Exception e){System.err.println("AWFT attraction journal: "+e);}
        if(clean){level=null;pending.clear();}
    }
    public void stopped(){finish("server stopping; no hub mutation; owned handles cleaned where possible");}
}
