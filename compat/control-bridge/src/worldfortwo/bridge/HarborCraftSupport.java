package worldfortwo.bridge;

import com.google.gson.*;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.datafixers.util.Either;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.*;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.TicketType;
import net.minecraft.world.Container;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.Property;
import net.minecraft.world.level.chunk.status.ChunkStatus;
import net.minecraft.world.level.chunk.storage.EntityStorage;
import net.minecraft.world.level.chunk.storage.IOWorker;
import net.minecraft.world.level.chunk.storage.SimpleRegionStorage;
import net.minecraft.world.level.dimension.DimensionType;
import net.minecraft.world.level.entity.PersistentEntitySectionManager;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.AABB;
import net.neoforged.fml.ModList;
import net.neoforged.fml.loading.FMLPaths;
import net.neoforged.neoforge.event.RegisterCommandsEvent;

import java.io.*;
import java.lang.invoke.MethodHandle;
import java.lang.invoke.MethodHandles;
import java.lang.invoke.MethodType;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.nio.file.attribute.FileTime;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;
import java.util.function.Supplier;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Two reviewed real craft only. No block writer, command execution, arbitrary
 * NBT loader, artificial drive, teleport, entity deletion or physics substitute.
 * Parent must wire a shared operation lease, tick and pre-level-close stop hook.
 */
public final class HarborCraftSupport {
    public interface Lease extends AutoCloseable { boolean valid(); void close() throws Exception; }
    public interface Interlock { Lease acquire(String owner,boolean temporarySimulation) throws Exception; }
    private enum Phase { IDLE, HASH_MOD, READY, CUSTODY_KEYS, CUSTODY_READ, FINAL_KEYS, OBSERVE, CLEANUP_REQUIRED }
    private static final Gson JSON=new Gson();
    private static final String COG="smallships:cog",BOAT="minecraft:boat";
    private static final String COG_NAME="The Sea Glass Promise",BOAT_NAME="Wren harbor tender";
    private static final String COG_CLASS="com.talhanation.smallships.world.entity.ship.CogEntity";
    private static final String PART_CLASS="com.talhanation.smallships.world.entity.ship.hitbox.ShipPartEntity";
    private static final String MOD_SHA="3ca7ec4a9f6800a5e9f90cb273e8495c5919c2d9a0707160a1d4391fa11c5525e3f76038f877023929d3e3104b3df79e8afc1138de0f7df64530649cb3b76d20";
    private static final String COG_SHA="6448f6042c07fb30f32f81551f1e720a77a914a26224d10ba7b112e6366cc6e2";
    private static final String PART_SHA="c5e21e3ed918df1b5c81076f51a896784ccf7858469cc8b3133537f8499f982b";
    private static final TicketType<ChunkPos> TICKET=TicketType.create("awft_harbor_craft",Comparator.comparingLong(ChunkPos::toLong));
    private static final int MAX_TARGETS=6000,MAX_CHUNKS=16,MAX_TICKS=2400,MAX_STORAGE_CHUNKS=4096;
    private static final long WORK_NS=4_000_000L;
    private static MethodHandle shipPartsGetter;
    private final Path home=FMLPaths.GAMEDIR.get().resolve("..").toAbsolutePath().normalize();
    private final Path directory=home.resolve("dashboard/settlement");
    private final String expectedCandidate,expectedBridgeVersion;
    private final Interlock interlock;
    private final Map<String,Object> report=new LinkedHashMap<>();
    private final Map<BlockPos,Expected> physical=new LinkedHashMap<>(),clearance=new LinkedHashMap<>();
    private final Map<String,List<AABB>> regions=new LinkedHashMap<>();
    private final LinkedHashSet<ChunkPos> chunks=new LinkedHashSet<>(),tickets=new LinkedHashSet<>();
    private final Map<ChunkPos,CompletableFuture<?>> pendingChunks=new LinkedHashMap<>();
    private final List<Store> stores=new ArrayList<>();
    private final Map<String,Integer> diskMatches=new LinkedHashMap<>();
    private final List<Entity> created=new ArrayList<>();
    private final Map<String,UUID> ids=new LinkedHashMap<>();
    private final Map<String,Entity> candidates=new LinkedHashMap<>();
    private JsonObject manifest,proposal,waterAir;
    private Path bundle,modPath;
    private String manifestSha,proposalSha,clearanceSha,backupSha,packSha,action="idle",requestedOutcome;
    private ServerLevel level;
    private Lease lease;
    private Phase phase=Phase.IDLE;
    private int ticks,readyTicks,observeTicks,storageReadCount,storageBytes;
    private long nextProgress,modBytes,modSize,modModified;
    private InputStream modStream;
    private MessageDigest modDigest;

    public HarborCraftSupport(String candidate,String bridgeVersion,Interlock interlock) {
        expectedCandidate=Objects.requireNonNull(candidate);expectedBridgeVersion=Objects.requireNonNull(bridgeVersion);
        this.interlock=Objects.requireNonNull(interlock,"A shared world-operation lease is required");
        if(candidate.isBlank()||bridgeVersion.isBlank())throw new IllegalArgumentException("Pin candidate and bridge identity");
    }
    public boolean busy(){return phase!=Phase.IDLE;}
    public void commands(RegisterCommandsEvent event) {
        var root=Commands.literal("awftharborcraft").requires(s->s.getEntity()==null&&s.hasPermission(4));
        for(String op:List.of("inspect","create"))root.then(Commands.literal(op)
            .then(Commands.argument("bundle",StringArgumentType.word()).then(Commands.argument("sha256",StringArgumentType.word()).executes(c->{
                try{begin(c.getSource().getServer(),op,StringArgumentType.getString(c,"bundle"),StringArgumentType.getString(c,"sha256"));return 1;}
                catch(Exception error){throw new IllegalStateException(error.getMessage(),error);}
            }))));
        root.then(Commands.literal("status").executes(c->{c.getSource().sendSuccess(()->Component.literal(JSON.toJson(report)),false);return 1;}));
        root.then(Commands.literal("cancel").executes(c->{finish("cancelled; created craft, if any, preserved");return 1;}));
        event.getDispatcher().register(root);
    }
    private static String hex(byte[] bytes){return HexFormat.of().formatHex(bytes);}
    private static String hash(byte[] bytes)throws Exception{return hex(MessageDigest.getInstance("SHA-256").digest(bytes));}
    private static int integer(JsonElement value){return value.getAsBigDecimal().intValueExact();}
    private static Field field(Class<?> type,String name)throws Exception{Field f=type.getDeclaredField(name);f.setAccessible(true);return f;}
    static MethodHandle resolveShipPartsGetter(Class<?> ship)throws ReflectiveOperationException {
        // Resolve this one exact member in the VM. Class.getDeclaredField can
        // enumerate all Ship fields and link its unrelated client CameraType.
        return MethodHandles.privateLookupIn(ship,MethodHandles.lookup()).findGetter(ship,"parts",List.class)
            .asType(MethodType.methodType(List.class,Object.class));
    }
    private static List<?> nativeShipParts(Entity ship)throws Exception {
        if(shipPartsGetter==null)shipPartsGetter=resolveShipPartsGetter(Class.forName("com.talhanation.smallships.world.entity.ship.Ship",false,ship.getClass().getClassLoader()));
        try{return List.copyOf((List<?>)shipPartsGetter.invokeExact((Object)ship));}
        catch(Exception error){throw error;}
        catch(Error error){throw error;} // Includes VM/OOM: never swallowed.
        catch(Throwable error){throw new IllegalStateException("Native ship child getter failed",error);}
    }
    private static UUID identity(long seed,String name)throws Exception {
        UUID namespace=UUID.fromString("6ba7b811-9dad-11d1-80b4-00c04fd430c8");
        MessageDigest digest=MessageDigest.getInstance("SHA-1");
        digest.update(ByteBuffer.allocate(16).putLong(namespace.getMostSignificantBits()).putLong(namespace.getLeastSignificantBits()).array());
        byte[] bytes=digest.digest(("awft-artistic:"+seed+":"+name).getBytes(StandardCharsets.UTF_8));
        bytes[6]=(byte)((bytes[6]&15)|80);bytes[8]=(byte)((bytes[8]&63)|128);
        ByteBuffer values=ByteBuffer.wrap(bytes);return new UUID(values.getLong(),values.getLong());
    }
    private Path owned(Path path)throws Exception {
        Path result=path.toAbsolutePath().normalize();
        if(!result.startsWith(home)||!Files.isRegularFile(result))throw new IllegalArgumentException("Evidence escaped the owned staging runtime");
        for(Path current=result;current!=null&&!current.equals(home);current=current.getParent())
            if(Files.isSymbolicLink(current)||!current.toRealPath().equals(current.toAbsolutePath().normalize()))throw new IllegalArgumentException("Linked/redirected evidence is refused");
        return result;
    }
    private byte[] bounded(Path path,long maximum)throws Exception {
        owned(path);long size=Files.size(path);if(size<1||size>maximum)throw new IllegalArgumentException("Evidence is empty or exceeds its bound");
        try(InputStream stream=Files.newInputStream(path)){byte[] bytes=stream.readNBytes((int)size+1);if(bytes.length!=size)throw new IllegalStateException("Evidence changed during read");return bytes;}
    }
    private JsonObject read(Path path,long maximum,String expected)throws Exception {
        byte[] bytes=bounded(path,maximum);if(expected!=null&&!hash(bytes).equals(expected))throw new IllegalStateException("Evidence hash differs: "+path.getFileName());
        return JsonParser.parseString(new String(bytes,StandardCharsets.UTF_8)).getAsJsonObject();
    }
    private JsonObject document(String name)throws Exception {
        JsonObject ref=manifest.getAsJsonObject("documents").getAsJsonObject(name);String expected=ref.get("sha256").getAsString();
        Path path=bundle.resolve(name);if(!expected.matches("[a-f0-9]{64}")||Files.size(path)!=ref.get("bytes").getAsLong())throw new IllegalStateException("Bound document size/hash missing");
        return read(path,2*1024*1024,expected);
    }
    private void currentReceipts(MinecraftServer server)throws Exception {
        JsonObject backup=read(directory.resolve("backup-receipt.json"),16384,null),active=read(home.resolve("packwiz/active.json"),65536,null),installed=read(home.resolve("server/installed.json"),1024*1024,null);
        JsonObject owner=read(home.resolve("dashboard/artistic-owner.json"),16384,null);
        if(!owner.get("format").getAsString().equals("awft-artistic-stage:1")
                ||!Path.of(owner.get("home").getAsString()).toAbsolutePath().normalize().equals(home)
                ||!owner.get("backup_sha256").getAsString().equals(backupSha)
                ||!home.toString().replace('\\','/').contains("/staging/"))throw new IllegalStateException("Only the explicitly owned isolated artistic prototype runtime is admitted");
        if(!backup.get("verified").getAsBoolean()||!backup.get("sha256").getAsString().equals(backupSha)
                ||!active.get("version").getAsString().equals(expectedCandidate)||!installed.get("pack_version").getAsString().equals(expectedCandidate)
                ||!active.get("pack_sha256").getAsString().equals(installed.get("pack_sha256").getAsString()))throw new IllegalStateException("Current verified backup or installed candidate differs");
        String actual=active.get("pack_sha256").getAsString();if(packSha!=null&&!packSha.equals(actual))throw new IllegalStateException("Installed pack changed during craft admission");packSha=actual;
        if(!ModList.get().getModContainerById("awft_control_bridge").orElseThrow().getModInfo().getVersion().toString().equals(expectedBridgeVersion)
                ||!ModList.get().getModContainerById("smallships").orElseThrow().getModInfo().getVersion().toString().equals("2.0.2"))throw new IllegalStateException("Actual bridge/Small Ships version differs");
        for(JsonObject doc:List.of(proposal.getAsJsonObject("physical_plan"),waterAir))
            if(!doc.get("seed").getAsString().equals(Long.toString(level.getSeed()))
                    ||!Path.of(doc.get("world_path").getAsString()).toAbsolutePath().normalize().equals(server.getWorldPath(LevelResource.ROOT).toAbsolutePath().normalize())
                    ||!doc.get("backup_sha256").getAsString().equals(backupSha)||!doc.getAsJsonArray("commands").isEmpty())throw new IllegalStateException("Wrong world or unexpected plan commands");
    }
    private void classPin(String name,String expected)throws Exception {
        try(InputStream stream=Class.forName(name).getResourceAsStream(name.substring(name.lastIndexOf('.')+1)+".class")) {
            if(stream==null)throw new IllegalStateException("Native class resource missing");byte[] code=stream.readNBytes(256*1024+1);
            if(code.length>256*1024||!hash(code).equals(expected))throw new IllegalStateException("Pinned native class differs: "+name);
        }
    }
    private void begin(MinecraftServer server,String op,String name,String expected)throws Exception {
        if(busy()||lease!=null||!tickets.isEmpty()||!server.isSameThread())throw new IllegalStateException("Craft support busy, cleanup outstanding or off server thread");
        if(!name.matches("artistic-harbor-craft-[a-f0-9]{16}")||!expected.matches("[a-f0-9]{64}"))throw new IllegalArgumentException("Use one exact immutable craft bundle and manifest SHA");
        if(!server.getPlayerList().getPlayers().isEmpty())throw new IllegalStateException("Craft commissioning requires an empty server; player craft are never reset");
        reset();action=op;manifestSha=expected;level=server.overworld();bundle=home.resolve("staging").resolve(name);
        report.put("operation",op);report.put("started",Instant.now().toString());report.put("manifest_sha256",expected);
        report.put("candidate_version",expectedCandidate);report.put("bridge_version",expectedBridgeVersion);phase=Phase.HASH_MOD;
        try {
            lease=interlock.acquire("harbor-craft/"+op,true);if(lease==null||!lease.valid())throw new IllegalStateException("Shared world-operation lease refused");
            manifest=read(bundle.resolve("manifest.json"),256*1024,expected);
            if(!manifest.get("format").getAsString().equals("awft-artistic-harbor-craft:1")||integer(manifest.get("commands"))!=0||integer(manifest.get("typed_entity_requests"))!=2)throw new IllegalStateException("Not the two reviewed command-free craft requests");
            proposal=document("proposal.json");waterAir=document("water-air-verify-only.json");
            proposalSha=manifest.getAsJsonObject("documents").getAsJsonObject("proposal.json").get("sha256").getAsString();
            clearanceSha=manifest.getAsJsonObject("documents").getAsJsonObject("water-air-verify-only.json").get("sha256").getAsString();
            if(!name.endsWith(proposalSha.substring(0,16))||!proposal.get("format").getAsString().equals("awft-artistic-harbor-craft-proposal:1")||!waterAir.getAsJsonArray("block_entities").isEmpty())throw new IllegalStateException("Immutable proposal identity differs");
            backupSha=manifest.get("backup_sha256").getAsString();currentReceipts(server);
            loadGeometry(proposal.getAsJsonObject("physical_plan"),physical,true);loadGeometry(waterAir,clearance,false);loadRegions();
            if(chunks.size()>MAX_CHUNKS||physical.size()!=integer(manifest.get("physical_positions"))||clearance.size()!=integer(manifest.get("clearance_positions")))throw new IllegalStateException("Bound craft geometry/chunk count differs");
            validateRequests();classPin(COG_CLASS,COG_SHA);classPin(PART_CLASS,PART_SHA);
            modPath=owned(home.resolve("server/mods/smallships-neoforge-1.21.1-2.0.2.jar"));modSize=Files.size(modPath);modModified=Files.getLastModifiedTime(modPath).toMillis();
            if(modSize<1||modSize>32*1024*1024)throw new IllegalStateException("Unbounded native Small Ships JAR");
            modStream=Files.newInputStream(modPath);modDigest=MessageDigest.getInstance("SHA-512");
            report.put("proposal_sha256",proposalSha);report.put("water_air_sha256",clearanceSha);report.put("physical_positions",physical.size());report.put("clearance_positions",clearance.size());
            report.put("status","hashing pinned native dependency; no entity created");NativeJournal.progress(directory,"harbor-craft-status.json",report);
        }catch(Exception error){report.put("error",error.toString());finish("craft admission refused; existing entities and blocks preserved");throw error;}
    }
    private void reset(){report.clear();physical.clear();clearance.clear();regions.clear();chunks.clear();pendingChunks.clear();stores.clear();diskMatches.clear();created.clear();ids.clear();candidates.clear();packSha=null;requestedOutcome=null;ticks=readyTicks=observeTicks=storageReadCount=storageBytes=0;modBytes=0;nextProgress=0;}
    private record Expected(BlockPos pos,BlockState state,Map<String,String> properties,String text){}
    @SuppressWarnings({"rawtypes","unchecked"})
    private Expected parse(BlockPos pos,String text) {
        if(text.length()>512)throw new IllegalArgumentException("Oversized block state");int split=text.indexOf('[');String key=split<0?text:text.substring(0,split);
        ResourceLocation id=ResourceLocation.parse(key);if(!BuiltInRegistries.BLOCK.containsKey(id))throw new IllegalArgumentException("Unknown native block");BlockState state=BuiltInRegistries.BLOCK.get(id).defaultBlockState();Map<String,String> explicit=new LinkedHashMap<>();
        if(split>=0){if(!text.endsWith("]"))throw new IllegalArgumentException("Malformed native state");for(String field:text.substring(split+1,text.length()-1).split(",")){String[] pair=field.split("=",-1);if(pair.length!=2||explicit.put(pair[0],pair[1])!=null)throw new IllegalArgumentException("Duplicate native property");Property property=state.getBlock().getStateDefinition().getProperty(pair[0]);if(property==null)throw new IllegalArgumentException("Unknown native property");state=state.setValue(property,(Comparable)property.getValue(pair[1]).orElseThrow());}}
        return new Expected(pos,state,explicit,text);
    }
    private void loadGeometry(JsonObject doc,Map<BlockPos,Expected> output,boolean landing) {
        if(!doc.get("format").getAsString().equals("awft-native-settlement:1")||!doc.getAsJsonArray("commands").isEmpty())throw new IllegalArgumentException("Only command-free native geometry is admissible");
        JsonArray palette=doc.getAsJsonArray("palette"),rows=doc.getAsJsonArray("blocks");if(rows.isEmpty()||rows.size()>MAX_TARGETS||palette.size()>128)throw new IllegalArgumentException("Unbounded craft geometry");
        for(JsonElement value:rows){JsonArray row=value.getAsJsonArray();if(row.size()!=4)throw new IllegalArgumentException("Invalid craft position");int x=integer(row.get(0)),y=integer(row.get(1)),z=integer(row.get(2)),index=integer(row.get(3));
            if(x<(landing?1194:1180)||x>(landing?1201:1204)||y<(landing?61:60)||y>(landing?67:74)||z<(landing?-1264:-1284)||z>(landing?-1251:-1248)||index<0||index>=palette.size())throw new IllegalArgumentException("Craft geometry escaped the reviewed harbor reserve");
            BlockPos pos=new BlockPos(x,y,z);Expected item=parse(pos,palette.get(index).getAsString());String key=BuiltInRegistries.BLOCK.getKey(item.state.getBlock()).toString();
            if(!landing&&!Set.of("minecraft:air","minecraft:water").contains(key))throw new IllegalArgumentException("Body/departure probes may contain only actual air and source water");
            if(output.put(pos,item)!=null)throw new IllegalArgumentException("Duplicate craft target");chunks.add(new ChunkPos(pos));}
        if(landing){JsonArray tags=doc.getAsJsonArray("block_entities");if(tags.size()!=1)throw new IllegalArgumentException("Only the new empty shore-spares barrel is allowed");JsonArray pos=tags.get(0).getAsJsonObject().getAsJsonArray("pos");if(pos.size()!=3||integer(pos.get(0))!=1200||integer(pos.get(1))!=65||integer(pos.get(2))!=-1261)throw new IllegalArgumentException("Unknown inventory tag");}
    }
    private void loadRegions() {
        JsonObject admission=proposal.getAsJsonObject("admission");if(!admission.get("format").getAsString().equals("awft-artistic-craft-admission:1")||!admission.get("required_water_air_sha256").getAsString().equals(clearanceSha))throw new IllegalArgumentException("Craft admission probe identity differs");
        JsonObject value=admission.getAsJsonObject("regions");Set<String> names=Set.of("cog-berth","cog-north-departure","tender-berth","tender-west-departure");if(!value.keySet().equals(names))throw new IllegalArgumentException("Exact four craft body/departure regions are required");
        for(String name:names){List<AABB> boxes=new ArrayList<>();JsonArray list=value.getAsJsonArray(name);if(list.isEmpty()||list.size()>12)throw new IllegalArgumentException("Unbounded region set");
            for(JsonElement entry:list){JsonArray row=entry.getAsJsonArray();if(row.size()!=6)throw new IllegalArgumentException("Malformed AABB");double[] v=new double[6];for(int i=0;i<6;i++){v[i]=row.get(i).getAsDouble();if(!Double.isFinite(v[i]))throw new IllegalArgumentException("Non-finite AABB");}
                AABB box=new AABB(v[0],v[1],v[2],v[3],v[4],v[5]);if(v[0]>=v[3]||v[1]>=v[4]||v[2]>=v[5]||box.minX<1180||box.maxX>1204||box.minY<60||box.maxY>74||box.minZ< -1284||box.maxZ> -1248)throw new IllegalArgumentException("AABB escaped the reviewed harbor reserve");
                for(int x=(int)Math.floor(box.minX);x<Math.ceil(box.maxX);x++)for(int y=(int)Math.floor(box.minY);y<Math.ceil(box.maxY);y++)for(int z=(int)Math.floor(box.minZ);z<Math.ceil(box.maxZ);z++)if(!clearance.containsKey(new BlockPos(x,y,z)))throw new IllegalArgumentException("Every actual body/departure AABB cell needs an exact native water/air check");boxes.add(box);}
            regions.put(name,boxes);}
    }
    private void validateRequests()throws Exception {
        JsonArray requests=proposal.getAsJsonArray("entity_requests");if(requests.size()!=2)throw new IllegalArgumentException("Exactly cog and tender are supported");
        for(JsonElement value:requests){JsonObject row=value.getAsJsonObject();String kind=row.get("entity").getAsString();boolean cog=kind.equals(COG);if(!cog&&!kind.equals(BOAT)||ids.containsKey(kind))throw new IllegalArgumentException("Unreviewed native entity type");
            String name=cog?COG_NAME:BOAT_NAME;double[] position=cog?new double[]{1196.5,63.1,-1264.5}:new double[]{1194.5,63.1,-1253.5};JsonArray pos=row.getAsJsonArray("position");
            if(!row.get("name").getAsString().equals(name)||!row.get("wood").getAsString().equals("spruce")||row.get("yaw").getAsDouble()!=(cog?180:90)||pos.size()!=3)throw new IllegalArgumentException("The reviewed fixed craft recipe differs");for(int i=0;i<3;i++)if(pos.get(i).getAsDouble()!=position[i])throw new IllegalArgumentException("Unreviewed craft position");
            UUID id=identity(level.getSeed(),name);if(!row.get("uuid").getAsString().equals(id.toString()))throw new IllegalArgumentException("Stable native UUID identity differs");ids.put(kind,id);
            diskMatches.put(id.toString(),0);
        }
    }
    private void simulationTicket(ChunkPos chunk,boolean add)throws Exception {level.getChunkSource().getClass().getMethod(add?"addRegionTicket":"removeRegionTicket",TicketType.class,ChunkPos.class,int.class,Object.class,boolean.class).invoke(level.getChunkSource(),TICKET,chunk,2,chunk,true);}
    private boolean ready(){for(ChunkPos chunk:chunks){BlockPos center=new BlockPos(chunk.getMinBlockX()+8,65,chunk.getMinBlockZ()+8);if(level.getChunkSource().getChunkNow(chunk.x,chunk.z)==null||!BridgePhaseGate.simulationReady(level.getChunkSource().isPositionTicking(chunk.toLong()),level.isPositionEntityTicking(center),level.areEntitiesLoaded(chunk.toLong()),false))return false;}return true;}
    private void requestChunks()throws Exception {for(ChunkPos chunk:chunks){tickets.add(chunk);simulationTicket(chunk,true);pendingChunks.put(chunk,((worldfortwo.bridge.mixin.ChunkCacheAccess)(Object)level.getChunkSource()).awftQueueChunk(chunk.x,chunk.z,ChunkStatus.FULL,false));}report.put("temporary_tickets",tickets.size());}

    private static final Pattern REGION=Pattern.compile("r\\.(-?[0-9]+)\\.(-?[0-9]+)\\.mca");
    private record DiskStamp(Path path,long bytes,FileTime modified,String offsets){}
    static Set<ChunkPos> regionOffsets(long bytes,byte[] offsets,int rx,int rz) {
        // RegionFile opens CREATE/READ/WRITE and accepts an immediate EOF with
        // its zeroed in-memory offset table. Until a real write, that perfectly
        // valid native placeholder remains exactly zero bytes on disk.
        if(bytes==0){if(offsets.length!=0)throw new IllegalStateException("An empty native region changed during custody");return Set.of();}
        if(bytes<8192||offsets.length!=4096)throw new IllegalStateException("Truncated nonempty entity region header");
        Set<ChunkPos> result=new LinkedHashSet<>();ByteBuffer entries=ByteBuffer.wrap(offsets);
        for(int index=0;index<1024;index++)if(entries.getInt()!=0)result.add(new ChunkPos(Math.addExact(Math.multiplyExact(rx,32),index%32),Math.addExact(Math.multiplyExact(rz,32),index/32)));
        return result;
    }
    private final class Store {
        final ServerLevel dimension;
        final PersistentEntitySectionManager<Entity> manager;
        final SimpleRegionStorage storage;
        final IOWorker worker;
        final Path path;
        final LinkedHashSet<ChunkPos> positions=new LinkedHashSet<>();
        final List<DiskStamp> files=new ArrayList<>();
        final Map<ChunkPos,CompletableFuture<Optional<CompoundTag>>> reads=new LinkedHashMap<>();
        CompletableFuture<List<ChunkPos>> keys;
        Iterator<ChunkPos> cursor;
        @SuppressWarnings("unchecked") Store(ServerLevel dimension)throws Exception {
            this.dimension=dimension;manager=(PersistentEntitySectionManager<Entity>)field(ServerLevel.class,"entityManager").get(dimension);
            Object nativeStorage=field(PersistentEntitySectionManager.class,"permanentStorage").get(manager);if(!(nativeStorage instanceof EntityStorage))throw new IllegalStateException("Unreviewed native entity storage implementation");
            storage=(SimpleRegionStorage)field(EntityStorage.class,"simpleRegionStorage").get(nativeStorage);worker=(IOWorker)field(SimpleRegionStorage.class,"worker").get(storage);
            path=DimensionType.getStorageFolder(dimension.dimension(),dimension.getServer().getWorldPath(LevelResource.ROOT)).resolve("entities").toAbsolutePath().normalize();
            files.addAll(diskFiles(path,positions));keys=pendingKeys(worker);
        }
    }
    @SuppressWarnings({"unchecked","rawtypes"})
    private static CompletableFuture<List<ChunkPos>> pendingKeys(IOWorker worker)throws Exception {
        Method submit=IOWorker.class.getDeclaredMethod("submitTask",Supplier.class);submit.setAccessible(true);Field pending=field(IOWorker.class,"pendingWrites");
        // The native I/O mailbox, rather than this server thread, owns the map.
        Supplier<Either<List<ChunkPos>,Exception>> snapshot=()->{try{return Either.left(List.copyOf(((Map<ChunkPos,?>)pending.get(worker)).keySet()));}catch(Exception error){return Either.right(error);}};
        return (CompletableFuture)submit.invoke(worker,snapshot);
    }
    private static void pendingUuid(CompoundTag tag,Map<UUID,Integer> counts,int depth,int[] visited) {
        if(depth>16||++visited[0]>16384)throw new IllegalStateException("Pending entity nesting/count exceeds custody bound");
        if(tag.hasUUID("UUID")){UUID id=tag.getUUID("UUID");if(counts.containsKey(id))counts.put(id,counts.get(id)+1);}
        ListTag passengers=tag.getList("Passengers",Tag.TAG_COMPOUND);if(passengers.size()>256)throw new IllegalStateException("Unbounded pending passengers");for(Tag passenger:passengers)pendingUuid((CompoundTag)passenger,counts,depth+1,visited);
    }
    @SuppressWarnings({"unchecked","rawtypes"})
    private static CompletableFuture<Map<UUID,Integer>> pendingUuidCounts(IOWorker worker,Set<UUID> identities)throws Exception {
        Method submit=IOWorker.class.getDeclaredMethod("submitTask",Supplier.class);submit.setAccessible(true);
        Field pending=field(IOWorker.class,"pendingWrites"),data=field(Class.forName("net.minecraft.world.level.chunk.storage.IOWorker$PendingStore"),"data");
        Supplier<Either<Map<UUID,Integer>,Exception>> query=()->{
            try{Map<UUID,Integer> counts=new LinkedHashMap<>();for(UUID id:identities)counts.put(id,0);
                Map<ChunkPos,?> writes=(Map<ChunkPos,?>)pending.get(worker);if(writes.size()>MAX_STORAGE_CHUNKS)throw new IllegalStateException("Pending entity writes exceed finite bound");int bytes=0;int[] visited={0};
                for(Object write:writes.values()){CompoundTag tag=(CompoundTag)data.get(write);if(tag==null)continue;int size=tag.sizeInBytes();if(size<0||size>2*1024*1024||(bytes+=size)>32*1024*1024)throw new IllegalStateException("Pending entity NBT exceeds finite bound");ListTag list=tag.getList("Entities",Tag.TAG_COMPOUND);for(Tag entity:list)pendingUuid((CompoundTag)entity,counts,0,visited);}
                return Either.left(counts);
            }catch(Exception error){return Either.right(error);}
        };
        return (CompletableFuture)submit.invoke(worker,query);
    }
    private List<DiskStamp> diskFiles(Path path,Set<ChunkPos> positions)throws Exception {
        List<DiskStamp> result=new ArrayList<>();if(!Files.exists(path))return result;
        Path world=level.getServer().getWorldPath(LevelResource.ROOT).toAbsolutePath().normalize();
        if(!path.startsWith(world)||Files.isSymbolicLink(path)||!path.toRealPath().equals(path))throw new IllegalStateException("Entity storage path is redirected");
        List<Path> all;try(var stream=Files.list(path)){all=stream.toList();}
        if(all.stream().anyMatch(p->p.getFileName().toString().endsWith(".mcc")))throw new IllegalStateException("External entity chunks require separate bounded custody review; no creation performed");
        List<Path> files=all.stream().filter(p->REGION.matcher(p.getFileName().toString()).matches()).sorted().toList();
        if(files.size()>32)throw new IllegalStateException("Entity-region custody exceeds the reviewed finite scan bound");long total=0;
        for(Path file:files){Matcher name=REGION.matcher(file.getFileName().toString());if(!name.matches()||Files.isSymbolicLink(file)||!Files.isRegularFile(file))throw new IllegalStateException("Invalid entity region");long bytes=Files.size(file);if((total+=bytes)>128*1024*1024)throw new IllegalStateException("Entity storage exceeds finite custody byte bound");
            byte[] offsets;try(InputStream stream=Files.newInputStream(file)){offsets=stream.readNBytes(4096);}
            int rx=Integer.parseInt(name.group(1)),rz=Integer.parseInt(name.group(2));positions.addAll(regionOffsets(bytes,offsets,rx,rz));
            if(positions.size()>MAX_STORAGE_CHUNKS)throw new IllegalStateException("Persistent UUID custody exceeds finite chunk bound");
            result.add(new DiskStamp(file,bytes,Files.getLastModifiedTime(file),hash(offsets)));}
        return result;
    }
    private void startCustody(MinecraftServer server)throws Exception {for(ServerLevel dim:server.getAllLevels()){if(stores.size()>=16)throw new IllegalStateException("Too many dimensions for bounded custody");report.put("custody_reading_dimension",dim.dimension().location().toString());Store store=new Store(dim);stores.add(store);report.put("custody_storage",stores.stream().map(s->Map.of("dimension",s.dimension.dimension().location().toString(),"region_files",s.files.size(),"region_bytes",s.files.stream().mapToLong(DiskStamp::bytes).sum(),"zero_byte_placeholders",s.files.stream().filter(f->f.bytes()==0).count())).toList());}report.put("custody_dimensions",stores.size());phase=Phase.CUSTODY_KEYS;}
    private void countNbt(CompoundTag tag,int depth)throws Exception {
        if(depth>16)throw new IllegalStateException("Persistent passenger nesting exceeds custody bound");
        if(tag.hasUUID("UUID")){String id=tag.getUUID("UUID").toString();if(diskMatches.containsKey(id))diskMatches.put(id,diskMatches.get(id)+1);}
        ListTag passengers=tag.getList("Passengers",Tag.TAG_COMPOUND);if(passengers.size()>256)throw new IllegalStateException("Unbounded passenger storage");for(Tag passenger:passengers)countNbt((CompoundTag)passenger,depth+1);
    }
    private boolean readCustody()throws Exception {
        int work=0;boolean finished=true;long started=System.nanoTime();
        for(Store store:stores){
            while(store.reads.size()<8&&store.cursor.hasNext()&&work++<32){ChunkPos pos=store.cursor.next();store.reads.put(pos,store.storage.read(pos));}
            for(var entry:new ArrayList<>(store.reads.entrySet())){if(!entry.getValue().isDone()){finished=false;continue;}Optional<CompoundTag> value=entry.getValue().join();store.reads.remove(entry.getKey());storageReadCount++;
                if(value.isPresent()){CompoundTag tag=value.get();int bytes=tag.sizeInBytes();if(bytes<0||bytes>2*1024*1024||(storageBytes+=bytes)>32*1024*1024)throw new IllegalStateException("Persistent NBT exceeds finite custody allocation");ListTag list=tag.getList("Entities",Tag.TAG_COMPOUND);if(list.size()>8192)throw new IllegalStateException("Too many stored entities");for(Tag entity:list)countNbt((CompoundTag)entity,0);}
                if(System.nanoTime()-started>WORK_NS)return false;}
            if(store.cursor.hasNext()||!store.reads.isEmpty())finished=false;
        }
        return finished;
    }
    private boolean matches(Expected item) {
        var chunk=level.getChunkSource().getChunkNow(item.pos.getX()>>4,item.pos.getZ()>>4);if(chunk==null)return false;BlockState actual=chunk.getBlockState(item.pos);if(actual.getBlock()!=item.state.getBlock())return false;
        for(String key:item.properties.keySet()){Property<?> property=actual.getBlock().getStateDefinition().getProperty(key);if(property==null||!actual.getValue(property).equals(item.state.getValue(property)))return false;}return true;
    }
    static CompoundTag fixedTag(String kind,UUID identity) {
        if(!Set.of(COG,BOAT).contains(kind)||identity==null)throw new IllegalArgumentException("Only the exact cog/tender native recipes are supported");
        boolean cog=kind.equals(COG);CompoundTag tag=new CompoundTag();tag.putString("id",kind);tag.putUUID("UUID",identity);tag.putString("Type","spruce");tag.putString("CustomName",JSON.toJson(Map.of("text",cog?COG_NAME:BOAT_NAME)));
        tag.putBoolean("PersistenceRequired",true);ListTag position=new ListTag();for(double v:cog?new double[]{1196.5,63.1,-1264.5}:new double[]{1194.5,63.1,-1253.5})position.add(DoubleTag.valueOf(v));tag.put("Pos",position);
        ListTag rotation=new ListTag();rotation.add(FloatTag.valueOf(cog?180:90));rotation.add(FloatTag.valueOf(0));tag.put("Rotation",rotation);ListTag motion=new ListTag();for(int i=0;i<3;i++)motion.add(DoubleTag.valueOf(0));tag.put("Motion",motion);
        if(cog){CompoundTag sail=new CompoundTag();sail.putByte("State",(byte)0);sail.putString("Color","white");sail.putFloat("SailHealth",100);tag.put("Sail",sail);tag.putFloat("HullDamage",0);tag.putBoolean("Sunken",false);tag.putBoolean("Sinking",false);tag.putBoolean("locked",false);tag.put("Items",new ListTag());}
        return tag;
    }
    private Entity candidate(String kind)throws Exception {
        boolean cog=kind.equals(COG);CompoundTag tag=fixedTag(kind,ids.get(kind));
        // Only this fixed safe CompoundTag is loaded. Supplied nbt_snbt is never
        // parsed, executed or applied; no caller can add passengers or inventory.
        Entity entity=EntityType.loadEntityRecursive(tag,level,e->e);if(entity==null||!entity.getUUID().equals(ids.get(kind))||!BuiltInRegistries.ENTITY_TYPE.getKey(entity.getType()).toString().equals(kind)||!entity.getPassengers().isEmpty()||entity.isInvulnerable())throw new IllegalStateException("Native typed craft factory refused the fixed recipe");
        if(cog&&!entity.getClass().getName().equals(COG_CLASS))throw new IllegalStateException("Wrong native cog implementation");
        if(!cog&&(entity.getBbWidth()!=1.375f||entity.getBbHeight()!=.5625f))throw new IllegalStateException("Actual vanilla boat dimensions changed");
        List<AABB> bodies=new ArrayList<>();bodies.add(entity.getBoundingBox());if(cog){Class<?> ship=Class.forName("com.talhanation.smallships.world.entity.ship.Ship");Object boxes=Class.forName(PART_CLASS).getMethod("hullBoxes",ship).invoke(null,entity);for(Object box:(List<?>)boxes)bodies.add((AABB)box);}
        List<AABB> reserved=regions.get(cog?"cog-berth":"tender-berth");for(AABB body:bodies)if(reserved.stream().noneMatch(b->contains(b,body)))throw new IllegalStateException("Actual native craft body exceeds the verified berth envelope");
        report.put(cog?"native_cog_factory_boxes":"native_tender_factory_boxes",bodies.stream().map(HarborCraftSupport::box).toList());return entity;
    }
    private static boolean contains(AABB outer,AABB inner){double epsilon=.00001;return inner.minX>=outer.minX-epsilon&&inner.minY>=outer.minY-epsilon&&inner.minZ>=outer.minZ-epsilon&&inner.maxX<=outer.maxX+epsilon&&inner.maxY<=outer.maxY+epsilon&&inner.maxZ<=outer.maxZ+epsilon;}
    private static List<Double> box(AABB b){return List.of(b.minX,b.minY,b.minZ,b.maxX,b.maxY,b.maxZ);}
    private List<Map<String,Object>> occupancy(boolean creating)throws Exception {
        LinkedHashMap<UUID,Entity> seen=new LinkedHashMap<>();for(List<AABB> values:regions.values())for(AABB box:values)for(Entity entity:level.getEntities((Entity)null,box,e->!e.isRemoved()))seen.put(entity.getUUID(),entity);
        if(seen.size()>128)throw new IllegalStateException("The berth is crowded beyond the finite native observation bound; no entities changed");
        List<Map<String,Object>> rows=new ArrayList<>();for(Entity entity:seen.values()){String type=BuiltInRegistries.ENTITY_TYPE.getKey(entity.getType()).toString();Map<String,Object> row=new LinkedHashMap<>();row.put("entity",type);row.put("uuid",entity.getUUID().toString());row.put("bounds",box(entity.getBoundingBox()));boolean owned=ids.containsValue(entity.getUUID());
            if(entity.getClass().getName().equals(PART_CLASS)){Entity parent=(Entity)entity.getClass().getMethod("getParent").invoke(entity);if(parent!=null){row.put("native_parent_uuid",parent.getUUID().toString());owned=ids.get(COG).equals(parent.getUUID());}}
            row.put("commissioned_identity",owned);rows.add(row);if(creating){report.put("spatial_entities",rows);throw new IllegalStateException("Native AABB occupied by "+type+"; preserve that entity, do not clear the berth");}}
        return rows;
    }
    private void reserveUuid(UUID id)throws Exception {
        Path folder=directory.resolve("harbor-craft-custody");Files.createDirectories(folder);Path target=folder.resolve(id+".json");
        byte[] bytes=JSON.toJson(Map.of("format","awft-native-craft-reservation:1","uuid",id.toString(),"manifest_sha256",manifestSha,"world_path",level.getServer().getWorldPath(LevelResource.ROOT).toString(),"game_time",level.getGameTime(),"at",Instant.now().toString(),"status","reserved before native creation; never silently retry a missing/moved/unloaded craft")).getBytes(StandardCharsets.UTF_8);
        try(FileChannel channel=FileChannel.open(target,StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE)){ByteBuffer data=ByteBuffer.wrap(bytes);while(data.hasRemaining())channel.write(data);channel.force(true);}
    }
    private void commit(MinecraftServer server)throws Exception {
        long begin=System.nanoTime(),gameTime=level.getGameTime();if(!ready()||!server.isSameThread())throw new IllegalStateException("Actual block/entity readiness changed");currentReceipts(server);
        if(Files.size(modPath)!=modSize||Files.getLastModifiedTime(modPath).toMillis()!=modModified)throw new IllegalStateException("Pinned mod changed during custody");
        boolean create=action.equals("create");Map<Store,CompletableFuture<Map<UUID,Integer>>> fresh=new LinkedHashMap<>();
        for(Store store:stores)fresh.put(store,pendingUuidCounts(store.worker,Set.copyOf(ids.values())));
        Map<String,Integer> queued=new LinkedHashMap<>();for(UUID id:ids.values())queued.put(id.toString(),0);
        // These native I/O mailbox queries run during this same server tick.
        // The timeout is finite; no server-thread entity unload can occur while
        // this atomic method validates the returned pending NBT and disk stamps.
        for(var item:fresh.entrySet())for(var count:item.getValue().get(5,TimeUnit.MILLISECONDS).entrySet())queued.put(count.getKey().toString(),queued.get(count.getKey().toString())+count.getValue());
        report.put("same_tick_pending_uuid_matches",queued);
        Map<String,Integer> loaded=new LinkedHashMap<>();for(UUID id:ids.values())loaded.put(id.toString(),0);
        for(Store store:stores){if(!store.files.equals(diskFiles(store.path,new LinkedHashSet<>())))throw new IllegalStateException("Persistent entity region custody changed; no creation performed");
            if(!store.positions.containsAll(store.keys.join()))throw new IllegalStateException("New pending persistent entity write escaped the completed scan");
            for(UUID id:ids.values())if(store.manager.isLoaded(id))loaded.put(id.toString(),loaded.get(id.toString())+1);}
        report.put("persistent_uuid_matches",diskMatches);report.put("loaded_uuid_matches",loaded);report.put("persistent_entity_chunks_read",storageReadCount);report.put("persistent_nbt_bytes",storageBytes);
        if(create&&(diskMatches.values().stream().anyMatch(n->n!=0)||queued.values().stream().anyMatch(n->n!=0)||loaded.values().stream().anyMatch(n->n!=0)))throw new IllegalStateException("A requested UUID already exists loaded, pending or persistently; never duplicate/reset it");
        for(Expected item:physical.values())if(!matches(item))throw new IllegalStateException("Actual landing differs at "+item.pos);
        for(Expected item:clearance.values())if(!matches(item)||level.getBlockEntity(item.pos)!=null)throw new IllegalStateException("Actual body/water/departure clearance differs at "+item.pos);
        if(create){BlockEntity barrel=level.getBlockEntity(new BlockPos(1200,65,-1261));if(!(barrel instanceof Container inventory)||!inventory.isEmpty())throw new IllegalStateException("The new shore-spares barrel must be native and empty before initial commissioning");
            for(UUID id:ids.values())if(Files.exists(directory.resolve("harbor-craft-custody").resolve(id+".json")))throw new IllegalStateException("Prior craft reservation exists; inspect/reconcile rather than respawn");}
        // Query actual AABBs after the full exact air/source-water check, on this
        // same server tick. Unknown fish/items/pets are preserved and refuse use.
        report.put("spatial_entities",occupancy(create));report.put("same_tick_admission_game_time",gameTime);
        report.put("same_tick_gate_ms",(System.nanoTime()-begin)/1_000_000.0);
        if(System.nanoTime()-begin>40_000_000L||level.getGameTime()!=gameTime)throw new IllegalStateException("The bounded atomic admission exceeded its tick budget; no creation performed");
        if(!create){observe();finish("native inspection complete; no control, boarding or sailing acceptance implied");return;}
        // Durable one-shot custody precedes every add, including unknown-outcome
        // failures. No automatic rollback deletes a successfully created entity.
        for(UUID id:ids.values())reserveUuid(id);
        report.put("creation_intent_persisted",true);report.put("creation_game_time",gameTime);
        for(String kind:List.of(COG,BOAT)){Entity entity=candidates.get(kind);if(!level.tryAddFreshEntityWithPassengers(entity))throw new IllegalStateException("Native entity add refused; partial craft, if any, preserved for inspection");created.add(entity);}
        report.put("created_native_entities",created.stream().map(e->e.getUUID().toString()).toList());phase=Phase.OBSERVE;observeTicks=0;
    }
    private void observe()throws Exception {
        List<Map<String,Object>> rows=new ArrayList<>();boolean partsReady=true;
        for(String kind:List.of(COG,BOAT)){Entity entity=null;for(Store store:stores){Entity found=store.dimension.getEntity(ids.get(kind));if(found!=null){if(entity!=null)throw new IllegalStateException("Duplicate native UUID observed across dimensions");entity=found;}}
            Map<String,Object> row=new LinkedHashMap<>();row.put("entity",kind);row.put("uuid",ids.get(kind).toString());row.put("loaded",entity!=null);if(entity==null){rows.add(row);if(action.equals("create"))throw new IllegalStateException("Created craft no longer loaded; preserved for custody inspection");continue;}
            CompoundTag tag=entity.saveWithoutId(new CompoundTag());row.put("native_class",entity.getClass().getName());row.put("position",List.of(entity.getX(),entity.getY(),entity.getZ()));row.put("yaw",entity.getYRot());row.put("bounds",box(entity.getBoundingBox()));row.put("native_dimensions",List.of(entity.getBbWidth(),entity.getBbHeight()));row.put("native_tick_count",entity.tickCount);row.put("passengers",entity.getPassengers().size());row.put("wood",tag.getString("Type"));row.put("velocity",List.of(entity.getDeltaMovement().x,entity.getDeltaMovement().y,entity.getDeltaMovement().z));
            if(entity instanceof Container inventory){row.put("native_container_slots",inventory.getContainerSize());row.put("native_container_empty",inventory.isEmpty());}
            if(kind.equals(COG)){CompoundTag sail=tag.getCompound("Sail");row.put("native_sail",Map.of("state",sail.getByte("State"),"color",sail.getString("Color"),"health",sail.getFloat("SailHealth")));row.put("native_hull_damage",tag.getFloat("HullDamage"));row.put("native_locked",tag.getBoolean("locked"));row.put("native_sunken",tag.getBoolean("Sunken"));row.put("native_sinking",tag.getBoolean("Sinking"));
                // This pinned SmallShips build uses ordinary Entity children,
                // not NeoForge PartEntity[]. getParts() is the definition list;
                // Ship.parts is the actual native list updated by ship ticks.
                List<?> definitions=(List<?>)entity.getClass().getMethod("getParts").invoke(entity);
                List<?> split=(List<?>)Class.forName(PART_CLASS).getMethod("split",List.class).invoke(null,definitions);
                List<?> children=nativeShipParts(entity);
                if(split.size()>64||children.size()>64)throw new IllegalStateException("Native child inspection exceeds the reviewed finite bound");
                List<Map<String,Object>> details=new ArrayList<>();Set<UUID> seen=new HashSet<>();int valid=0;
                for(int n=0;n<children.size();n++){
                    Object child=children.get(n);if(!(child instanceof Entity part)||!part.getClass().getName().equals(PART_CLASS))throw new IllegalStateException("Unreviewed native ship child type");
                    boolean parent=part.getClass().getMethod("getParent").invoke(part)==entity;
                    boolean registered=part.level()==level&&level.getEntity(part.getUUID())==part;
                    boolean dimensions=Float.isFinite(part.getBbWidth())&&Float.isFinite(part.getBbHeight())&&part.getBbWidth()>0&&part.getBbHeight()>0;
                    boolean expectedBox=false;if(n<split.size()){
                        Object definition=split.get(n);AABB expected=(AABB)definition.getClass().getMethod("boxAt",double.class,double.class,double.class,float.class).invoke(definition,entity.getX(),entity.getY(),entity.getZ(),entity.getYRot());
                        AABB actual=part.getBoundingBox();expectedBox=Math.abs(expected.minX-actual.minX)<=.01&&Math.abs(expected.minY-actual.minY)<=.01&&Math.abs(expected.minZ-actual.minZ)<=.01&&Math.abs(expected.maxX-actual.maxX)<=.01&&Math.abs(expected.maxY-actual.maxY)<=.01&&Math.abs(expected.maxZ-actual.maxZ)<=.01;
                    }
                    boolean unique=seen.add(part.getUUID());boolean ready=parent&&registered&&dimensions&&expectedBox&&unique&&!part.isRemoved()&&part.isAlive()&&part.tickCount>0;
                    if(ready)valid++;Map<String,Object> detail=new LinkedHashMap<>();detail.put("uuid",part.getUUID().toString());detail.put("parent_identity",parent);detail.put("loaded_native_identity",registered);detail.put("removed",part.isRemoved());detail.put("alive",part.isAlive());detail.put("native_tick_count",part.tickCount);detail.put("bounds",box(part.getBoundingBox()));detail.put("native_dimensions",List.of(part.getBbWidth(),part.getBbHeight()));detail.put("matches_native_split_definition_box",expectedBox);detail.put("ready",ready);details.add(detail);
                }
                row.put("native_part_definitions",definitions.size());row.put("native_split_parts_expected",split.size());row.put("native_parts_observed",children.size());row.put("native_parts_verified",valid);row.put("native_part_details",details);row.put("native_parts_source","Pinned Ship.parts ordinary Entity children, native parent and level UUID identity, split definition boxes");partsReady=children.size()==split.size()&&valid==split.size()&&valid>0;
                if(action.equals("create")&&(!tag.getString("Type").equals("spruce")||tag.getBoolean("locked")||tag.getBoolean("Sunken")||tag.getBoolean("Sinking")||tag.getFloat("HullDamage")!=0||sail.getByte("State")!=0||!sail.getString("Color").equals("white")||sail.getFloat("SailHealth")!=100))throw new IllegalStateException("Loaded native initial ship state differs; preserve and inspect craft");}
            rows.add(row);}
        report.put("native_entities",rows);report.put("native_parts_ready",partsReady);report.put("observation_game_time",level.getGameTime());report.put("boarding_controls_cargo_sailing_restart","UNVERIFIED; actual owner actions and restart receipts required");
        if(action.equals("create")&&!partsReady)throw new IllegalStateException("Native multipart initialization incomplete; no visual or gameplay acceptance claimed");
    }

    public void tick(MinecraftServer server) {
        if(phase==Phase.IDLE||phase==Phase.CLEANUP_REQUIRED)return;long start=System.nanoTime();
        try {
            if(lease==null||!lease.valid()||!server.isSameThread())throw new IllegalStateException("Shared craft-operation lease/thread lost");
            if(!server.getPlayerList().getPlayers().isEmpty())throw new IllegalStateException("Player joined; commissioning stopped and all craft preserved");
            // Vanilla suspends entity ticking after 300 empty ticks even with
            // custom chunk tickets. Wake only this leased bounded operation;
            // native Ship.tick creates/positions its own children naturally.
            level.resetEmptyTime();report.put("native_simulation_wake","bounded leased operation only; ordinary idle resumes after cleanup");
            if(++ticks>MAX_TICKS)throw new IllegalStateException("Bounded craft operation timed out");
            if(phase==Phase.HASH_MOD){byte[] buffer=new byte[65536];while(System.nanoTime()-start<WORK_NS){int n=modStream.read(buffer);if(n<0){modStream.close();modStream=null;if(modBytes!=modSize||!hex(modDigest.digest()).equals(MOD_SHA))throw new IllegalStateException("Actual installed native Small Ships JAR differs");candidates.put(COG,candidate(COG));candidates.put(BOAT,candidate(BOAT));requestChunks();phase=Phase.READY;break;}modDigest.update(buffer,0,n);if((modBytes+=n)>modSize)throw new IllegalStateException("Native mod grew during hash");}}
            else if(phase==Phase.READY){for(CompletableFuture<?> future:pendingChunks.values())if(future.isCompletedExceptionally())throw new IllegalStateException("Native target FULL-chunk request failed");if(ready())startCustody(server);else if(++readyTicks>400)throw new IllegalStateException("Native body/departure chunks never became FULL and entity-ready");}
            else if(phase==Phase.CUSTODY_KEYS){boolean done=true;int total=0;for(Store store:stores){if(!store.keys.isDone()){done=false;continue;}store.positions.addAll(store.keys.join());total+=store.positions.size();}if(total>MAX_STORAGE_CHUNKS)throw new IllegalStateException("Global persistent UUID custody exceeds finite chunk bound");if(done){for(Store store:stores)store.cursor=store.positions.iterator();phase=Phase.CUSTODY_READ;}}
            else if(phase==Phase.CUSTODY_READ){if(readCustody()){for(Store store:stores)store.keys=pendingKeys(store.worker);phase=Phase.FINAL_KEYS;}}
            else if(phase==Phase.FINAL_KEYS){if(stores.stream().allMatch(s->s.keys.isDone()))commit(server);}
            else if(phase==Phase.OBSERVE){if(!ready())throw new IllegalStateException("Native readiness lost after creation; entities preserved");if(++observeTicks>=30){observe();finish("native cog and tender created and inspected; actual boarding/sailing/restart still unverified");}}
            report.put("phase",phase.name());report.put("ticks",ticks);report.put("storage_chunks_read",storageReadCount);report.put("last_work_ms",(System.nanoTime()-start)/1_000_000.0);
            if(phase!=Phase.IDLE&&System.nanoTime()>nextProgress){NativeJournal.progress(directory,"harbor-craft-status.json",report);nextProgress=System.nanoTime()+5_000_000_000L;}
        }catch(LinkageError error){report.put("error",error.toString());finish("native helper linkage unavailable; owned tickets released and all craft preserved");}
        catch(Exception error){report.put("error",error.toString());finish("native craft operation refused or incomplete; all existing/created craft preserved");}
    }
    private void finish(String outcome) {
        if(phase==Phase.IDLE&&lease==null&&tickets.isEmpty())return;if(requestedOutcome==null)requestedOutcome=outcome;List<String> errors=new ArrayList<>();
        if(modStream!=null)try{modStream.close();modStream=null;}catch(Exception error){errors.add("mod input: "+error);}
        for(ChunkPos chunk:new ArrayList<>(tickets))try{simulationTicket(chunk,false);tickets.remove(chunk);}catch(Exception error){errors.add("ticket "+chunk+": "+error);}
        if(tickets.isEmpty()&&modStream==null&&lease!=null)try{lease.close();lease=null;}catch(Exception error){errors.add("shared lease: "+error);}
        boolean clean=tickets.isEmpty()&&modStream==null&&lease==null;
        report.put("finished",Instant.now().toString());report.put("remaining_owned_tickets",tickets.size());report.put("cleanup_errors",errors);report.put("terminal_cleanup_passed",clean);
        report.put("shared_native_futures_pending",pendingChunks.values().stream().filter(f->!f.isDone()).count()+stores.stream().mapToLong(s->s.reads.values().stream().filter(f->!f.isDone()).count()+(s.keys!=null&&!s.keys.isDone()?1:0)).sum());
        report.put("created_native_entities",created.stream().map(e->e.getUUID().toString()).toList());report.put("status",clean?requestedOutcome:"cleanup_required; retain ownership and retry cancel/stop");report.put("world_block_mutations",0);report.put("forced_motion_or_entity_deletions",0);
        phase=clean?Phase.IDLE:Phase.CLEANUP_REQUIRED;report.put("phase",phase.name());
        try{NativeJournal.terminal(directory,"harbor-craft",report);NativeJournal.progress(directory,"harbor-craft-status.json",report);}catch(Exception error){phase=Phase.CLEANUP_REQUIRED;report.put("journal_error",error.toString());System.err.println("AWFT harbor craft journal: "+error);}
        if(phase==Phase.IDLE){level=null;pendingChunks.clear();stores.clear();candidates.clear();}
    }
    public void stopped(){finish("server stopping; owned tickets released and all actual craft preserved");}
}
