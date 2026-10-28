package worldfortwo.bridge;

import com.google.gson.*;
import com.mojang.brigadier.arguments.StringArgumentType;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
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
    private record Resident(UUID uuid,String id,String tag,EntityType<?> type,String nativeClass,String category,
                            double x,double y,double z,AABB habitat,Map<BlockPos,BlockState> before) {}
    private static final Gson JSON=new Gson();
    private static final String MOD_FILE="naturalist-2.0.7-neoforge-1.21.1.jar";
    private static final String MOD_SHA="2740593710eba0a917f862e535f3e2ef06c39ccdd6441986da02f9dd4394f03a";
    private static final TicketType<ChunkPos> TICKET=TicketType.create("awft_habitat_life",Comparator.comparingLong(ChunkPos::toLong));
    private static final int MAX_TICKS=1200,MAX_PLAN=2*1024*1024,MAX_MEMBERS=16,MAX_BLOCKS=4096,MAX_CHUNKS=32;
    private final String candidate,bridge;
    private final ArtisticEngineeringSupport.Interlock interlock;
    private final Path home=FMLPaths.GAMEDIR.get().resolve("..").toAbsolutePath().normalize();
    private final Path journal=home.resolve("dashboard/settlement");
    private ArtisticEngineeringSupport.Lease lease;
    private ServerLevel level;
    private Phase phase=Phase.IDLE;
    private JsonObject request,plan,habitatPlan,habitatVerify;
    private String action,outcome,recipeSha,namespace;
    private int ticks,index,spawned,preserved,intentsWritten,finalized;
    private boolean cleanupPublished;
    private Path ledger;
    private InputStream hashStream;
    private MessageDigest hashDigest;
    private BasicFileAttributes hashBefore;
    private Path hashPath;
    private long hashed;
    private final byte[] hashBuffer=new byte[65536];
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
    private void checkpoint()throws Exception{
        if(!owned(reference("current_backup").get("path").getAsString()).equals(journal.resolve("backup-receipt.json")))throw new IllegalStateException("Canonical current checkpoint required");
        JsonObject backup=read(reference("current_backup"),4096);
        if(!backup.get("verified").getAsBoolean()||!backup.get("sha256").getAsString().equals(request.get("checkpoint_sha256").getAsString()))throw new IllegalStateException("Current LIFE checkpoint differs");
    }
    private static void nativeCode(Class<?> type,String expected)throws Exception{
        try(InputStream in=type.getResourceAsStream(type.getSimpleName()+".class")){
            if(in==null)throw new IllegalStateException("Native LIFE class missing");byte[] raw=in.readNBytes(256*1024+1);
            if(raw.length>256*1024||!sha(raw).equals(expected))throw new IllegalStateException("Actual loaded LIFE helper/policy differs");
        }
    }
    private void begin(MinecraftServer server,String operation,String bundle,String expected)throws Exception{
        if(busy()||lease!=null||!tickets.isEmpty()||!server.isSameThread()||!bundle.matches("life-[a-f0-9]{16}")||!expected.matches("[a-f0-9]{64}")||!bundle.endsWith(expected.substring(0,16)))throw new IllegalStateException("Busy/off-thread/invalid LIFE request");
        report.clear();observed.clear();outcome=null;cleanupPublished=false;habitatPlan=habitatVerify=null;ticks=index=spawned=preserved=intentsWritten=finalized=0;report.put("operation",operation);report.put("started",Instant.now().toString());report.put("request_sha256",expected);
        Path stages=Path.of("D:\\A World for Two\\staging\\world-tests").toRealPath(),actualHome=home.toRealPath();
        if(!actualHome.getParent().equals(stages)||!actualHome.equals(home)
            ||!server.getWorldPath(LevelResource.ROOT).toRealPath().equals(home.resolve("world/RosewaterArtistic").toRealPath())
            ||server.getPort()!=25575||!server.getPlayerList().getPlayers().isEmpty()||!server.getServerVersion().equals("1.21.1"))throw new IllegalStateException("Exact owned empty private Minecraft 1.21.1 staging only");
        byte[] raw=bounded(owned("dashboard/settlement/"+bundle+"/request.json"),128*1024);
        if(!sha(raw).equals(expected))throw new IllegalStateException("LIFE request differs");request=JsonParser.parseString(new String(raw,StandardCharsets.UTF_8)).getAsJsonObject();
        if(!request.get("format").getAsString().equals("awft-native-habitat-life:1")||!operation.equals(request.get("allowed_operation").getAsString())||!candidate.equals(request.get("candidate_version").getAsString())||!bridge.equals(request.get("bridge_version").getAsString())
            ||!ModList.get().getModContainerById("awft_control_bridge").orElseThrow().getModInfo().getVersion().toString().equals(bridge)
            ||!ModList.get().getModContainerById("neoforge").orElseThrow().getModInfo().getVersion().toString().equals(request.get("neoforge_version").getAsString()))throw new IllegalStateException("Exact runtime candidate/bridge/platform required");
        nativeCode(NativeHabitatLifeSupport.class,request.get("native_class_sha256").getAsString());nativeCode(HabitatLifePolicy.class,request.get("native_policy_sha256").getAsString());
        JsonObject owner=JsonParser.parseString(new String(bounded(owned("dashboard/artistic-owner.json"),65536),StandardCharsets.UTF_8)).getAsJsonObject();
        JsonObject active=JsonParser.parseString(new String(bounded(owned("packwiz/active.json"),65536),StandardCharsets.UTF_8)).getAsJsonObject();
        JsonObject installed=JsonParser.parseString(new String(bounded(owned("server/installed.json"),1024*1024),StandardCharsets.UTF_8)).getAsJsonObject();
        if(!owner.get("format").getAsString().equals("awft-artistic-stage:1")||!Path.of(owner.get("home").getAsString()).toRealPath().equals(home.toRealPath())
            ||!active.get("version").getAsString().equals(candidate)||!installed.get("pack_version").getAsString().equals(candidate)
            ||!active.get("pack_sha256").getAsString().equals(installed.get("pack_sha256").getAsString())||!active.get("pack_sha256").getAsString().equals(request.get("pack_sha256").getAsString()))throw new IllegalStateException("Actual owned installed pack custody differs");
        checkpoint();plan=read(reference("recipe"),MAX_PLAN);recipeSha=reference("recipe").get("sha256").getAsString();
        if(!plan.get("format").getAsString().equals("awft-habitat-life-recipe:1")||plan.get("copied_entity_NBT").getAsBoolean()
            ||!plan.get("source_woodland_proposal_sha256").getAsString().equals(request.get("source_woodland_proposal_sha256").getAsString()))throw new IllegalStateException("Exact reviewed original population recipe required; no entity NBT");
        level=server.overworld();if(!plan.get("seed").getAsString().equals(Long.toString(level.getSeed()))||!Path.of(plan.get("world_path").getAsString()).toRealPath().equals(server.getWorldPath(LevelResource.ROOT).toRealPath())
            ||!plan.get("dimension").getAsString().equals("minecraft:overworld"))throw new IllegalStateException("Actual native world/dimension differs");
        namespace=UUID.fromString(plan.get("population_namespace").getAsString()).toString();
        JsonObject census=read(reference("uuid_census"),512*1024);
        if(!census.get("checkpoint_sha256").getAsString().equals(request.get("checkpoint_sha256").getAsString())||!census.get("recipe_sha256").getAsString().equals(recipeSha)
            ||!census.get("all_world_entity_regions_scanned").getAsBoolean())throw new IllegalStateException("Fresh complete world UUID census required");
        censusMembers.clear();for(JsonElement entry:census.getAsJsonArray("members")){JsonObject row=entry.getAsJsonObject();UUID id=UUID.fromString(row.get("uuid").getAsString());if(censusMembers.put(id,row)!=null||censusMembers.size()>MAX_MEMBERS)throw new IllegalStateException("Duplicate/unbounded census member");}
        if(operation.equals("seed")){
            JsonObject approval=read(reference("life_ready"),128*1024);
            for(String key:List.of("construction_complete","functional_commissioning_complete","visual_corrections_reviewed","habitat_plan_reviewed"))if(!approval.get(key).getAsBoolean())throw new IllegalStateException("LIFE is after construction/function/art: "+key);
            boolean approved=false;for(JsonElement value:approval.getAsJsonArray("approved_recipe_sha256s"))if(value.getAsString().equals(recipeSha))approved=true;
            if(!approval.get("checkpoint_sha256").getAsString().equals(request.get("checkpoint_sha256").getAsString())||!approved)throw new IllegalStateException("LIFE approval is not bound to this checkpoint/recipe");
            JsonObject verify=read(reference("native_habitat_verify"),512*1024);Path file=owned(reference("native_habitat_verify").get("path").getAsString());
            habitatVerify=verify;habitatPlan=read(reference("habitat_plan"),MAX_PLAN);
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
        JsonArray members=plan.getAsJsonArray("members");if(members.isEmpty()||members.size()>MAX_MEMBERS)throw new IllegalStateException("A finite LIFE batch has 1..16 members");
        Set<UUID> unique=new HashSet<>();int cells=0;
        for(JsonElement value:members){JsonObject row=value.getAsJsonObject();UUID uuid=UUID.fromString(row.get("uuid").getAsString());String id=row.get("entity").getAsString(),cls=row.get("native_class").getAsString(),category=row.get("native_MobCategory").getAsString();
            if(!Set.of("uuid","entity","native_class","native_MobCategory","member_tag","feet","roam_bounds","source_group_id","preimage").equals(row.keySet()))throw new IllegalStateException("No extra entity NBT, ownership, NoAI or passenger fields admitted");
            HabitatLifePolicy.species(id,cls,category);ResourceLocation key=ResourceLocation.parse(id);if(!BuiltInRegistries.ENTITY_TYPE.containsKey(key)||!unique.add(uuid))throw new IllegalStateException("Unregistered/duplicate native resident");
            EntityType<?> type=BuiltInRegistries.ENTITY_TYPE.get(key);if(!type.getCategory().getName().equals(category))throw new IllegalStateException("Actual native category differs");
            JsonArray p=row.getAsJsonArray("feet");double x=p.get(0).getAsDouble(),y=p.get(1).getAsDouble(),z=p.get(2).getAsDouble();HabitatLifePolicy.coordinate(x,y,z);
            JsonArray box=row.getAsJsonArray("roam_bounds");AABB habitat=new AABB(box.get(0).getAsDouble(),box.get(1).getAsDouble(),box.get(2).getAsDouble(),box.get(3).getAsDouble(),box.get(4).getAsDouble(),box.get(5).getAsDouble());
            HabitatLifePolicy.coordinate(habitat.minX,habitat.minY,habitat.minZ);HabitatLifePolicy.coordinate(habitat.maxX,habitat.maxY,habitat.maxZ);if(!habitat.contains(x,y,z)||habitat.getSize()>512)throw new IllegalStateException("Finite roaming habitat required");
            String tag=row.get("member_tag").getAsString();if(!tag.matches("awft_life_[a-f0-9]{24}"))throw new IllegalStateException("Exact unique member tag required");
            Map<BlockPos,BlockState> before=new LinkedHashMap<>();for(JsonElement entry:row.getAsJsonArray("preimage")){JsonArray cell=entry.getAsJsonArray();BlockPos pos=new BlockPos(cell.get(0).getAsInt(),cell.get(1).getAsInt(),cell.get(2).getAsInt());
                if(pos.distManhattan(BlockPos.containing(x,y,z))>8||before.put(pos,parse(cell.get(3).getAsString()))!=null||++cells>MAX_BLOCKS)throw new IllegalStateException("Foreign/duplicate/unbounded footing/headroom witness");}
            BlockPos feet=BlockPos.containing(x,y,z);if(before.size()!=45)throw new IllegalStateException("Complete 45-cell actual footing/body preimage required");
            for(int xx=feet.getX()-1;xx<=feet.getX()+1;xx++)for(int zz=feet.getZ()-1;zz<=feet.getZ()+1;zz++)for(int yy=feet.getY()-1;yy<=feet.getY()+3;yy++)if(!before.containsKey(new BlockPos(xx,yy,zz)))throw new IllegalStateException("Actual footing/body witness omits a required cell");
            residents.add(new Resident(uuid,id,tag,type,cls,category,x,y,z,habitat,Map.copyOf(before)));
            JsonObject saved=censusMembers.get(uuid);if(saved==null)throw new IllegalStateException("Census omits a requested UUID");
            if(saved.get("present").getAsBoolean()){
                JsonArray current=saved.getAsJsonArray("position");double cx=current.get(0).getAsDouble(),cy=current.get(1).getAsDouble(),cz=current.get(2).getAsDouble();HabitatLifePolicy.coordinate(cx,cy,cz);
                if(!saved.get("entity").getAsString().equals(id)||!saved.get("expected_tags_present").getAsBoolean()||!saved.get("dimension").getAsString().equals("minecraft:overworld")||!habitat.contains(cx,cy,cz))throw new IllegalStateException("Saved UUID identity or roaming habitat differs; preserve resident");
                for(int qx=(((int)Math.floor(cx))-2)>>4;qx<=(((int)Math.floor(cx))+2)>>4;qx++)for(int qz=(((int)Math.floor(cz))-2)>>4;qz<=(((int)Math.floor(cz))+2)>>4;qz++)chunks.add(new ChunkPos(qx,qz));
            }
            for(int cx=(((int)Math.floor(x))-2)>>4;cx<=(((int)Math.floor(x))+2)>>4;cx++)for(int cz=(((int)Math.floor(z))-2)>>4;cz<=(((int)Math.floor(z))+2)>>4;cz++)chunks.add(new ChunkPos(cx,cz));
        }
        if(censusMembers.size()!=residents.size()||chunks.size()>MAX_CHUNKS)throw new IllegalStateException("LIFE batch/census crosses its finite identity/chunk limits");
        if(habitatPlan!=null){
            if(!habitatPlan.get("format").getAsString().equals("awft-native-settlement:1")||!habitatPlan.get("seed").getAsString().equals(plan.get("seed").getAsString())
                ||!habitatPlan.get("world_path").getAsString().equals(plan.get("world_path").getAsString())||!habitatPlan.get("backup_sha256").getAsString().equals(request.get("checkpoint_sha256").getAsString())
                ||!habitatPlan.getAsJsonArray("commands").isEmpty()||!habitatPlan.getAsJsonArray("block_entities").isEmpty())throw new IllegalStateException("Verified habitat plan identity/contents differ");
            Map<BlockPos,BlockState> verified=new HashMap<>();JsonArray palette=habitatPlan.getAsJsonArray("palette"),rows=habitatPlan.getAsJsonArray("blocks");
            if(rows.size()>MAX_BLOCKS||rows.size()!=habitatVerify.get("blocks").getAsInt())throw new IllegalStateException("Exact verified habitat cell count differs");
            for(JsonElement entry:rows){JsonArray row=entry.getAsJsonArray();BlockPos pos=new BlockPos(row.get(0).getAsInt(),row.get(1).getAsInt(),row.get(2).getAsInt());if(verified.put(pos,parse(palette.get(row.get(3).getAsInt()).getAsString()))!=null)throw new IllegalStateException("Duplicate verified habitat cell");}
            for(Resident member:residents)for(var entry:member.before.entrySet())if(!entry.getValue().equals(verified.get(entry.getKey())))throw new IllegalStateException("Native verification does not cover this member's exact complete footing/body cells");
        }
        ledger=server.getWorldPath(LevelResource.ROOT).toRealPath().resolve("data/awft-life/"+namespace);
        for(Path p=ledger;p!=null&&!p.equals(server.getWorldPath(LevelResource.ROOT).toRealPath());p=p.getParent())if(Files.exists(p,LinkOption.NOFOLLOW_LINKS)&&Files.isSymbolicLink(p))throw new IllegalStateException("No linked world ledger ancestry");
        Path ancestor=ledger;while(ancestor!=null&&!Files.exists(ancestor))ancestor=ancestor.getParent();if(ancestor==null||Files.isSymbolicLink(ancestor)||!ancestor.toRealPath().startsWith(server.getWorldPath(LevelResource.ROOT).toRealPath()))throw new IllegalStateException("Ledger escaped actual world");
        if(Files.exists(ledger)){if(!Files.isDirectory(ledger,LinkOption.NOFOLLOW_LINKS))throw new IllegalStateException("Ledger is not an ordinary directory");int count=0;try(var files=Files.newDirectoryStream(ledger)){for(Path file:files)if(++count>1024||Files.isSymbolicLink(file)||!file.getFileName().toString().matches("[a-f0-9-]{36}\\.(intent|admitted)\\.json"))throw new IllegalStateException("Unbounded/foreign world LIFE ledger");}}
        if(!ModList.get().getModContainerById("naturalist").orElseThrow().getModInfo().getVersion().toString().equals("2.0.7"))throw new IllegalStateException("Pinned native wildlife version differs");
        hashPath=owned("server/mods/"+MOD_FILE);hashBefore=Files.readAttributes(hashPath,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);if(hashBefore.size()>16*1024*1024)throw new IllegalStateException("Pinned native wildlife input exceeds bound");
        if(!ModList.get().getModFileById("naturalist").getFile().getFilePath().toRealPath().equals(hashPath.toRealPath()))throw new IllegalStateException("Actual loaded native wildlife source path differs");
        hashStream=Files.newInputStream(hashPath);hashDigest=MessageDigest.getInstance("SHA-256");hashed=0;
        lease=interlock.acquire("habitat-life:"+expected,false);if(lease==null||!lease.valid())throw new IllegalStateException("Shared exclusive world-operation lease required");
        report.put("candidate",candidate);report.put("bridge",bridge);report.put("recipe_sha256",recipeSha);report.put("failures",0);report.put("members",residents.size());report.put("native_AI_behavior_acceptance",false);phase=Phase.HASH;
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
        BasicFileAttributes actual=Files.readAttributes(hashPath,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
        if(actual.size()!=hashBefore.size()||!actual.lastModifiedTime().equals(hashBefore.lastModifiedTime())||!Objects.equals(actual.fileKey(),hashBefore.fileKey()))throw new IllegalStateException("Pinned native wildlife source changed after hashing");
        Path world=server.getWorldPath(LevelResource.ROOT).toRealPath();for(Path p=ledger;p!=null&&!p.equals(world);p=p.getParent())if(Files.exists(p,LinkOption.NOFOLLOW_LINKS)&&(Files.isSymbolicLink(p)||!p.toRealPath().equals(p.toAbsolutePath().normalize())))throw new IllegalStateException("World LIFE ledger path changed/redirected");
    }
    private JsonObject intent(Resident row){JsonObject value=new JsonObject();value.addProperty("format","awft-life-world-intent:1");value.addProperty("recipe_sha256",recipeSha);value.addProperty("population_namespace",namespace);value.addProperty("uuid",row.uuid.toString());value.addProperty("entity",row.id);value.addProperty("native_class",row.nativeClass);value.addProperty("native_category",row.category);value.addProperty("member_tag",row.tag);value.add("feet",JSON.toJsonTree(List.of(row.x,row.y,row.z)));value.add("roam_bounds",JSON.toJsonTree(List.of(row.habitat.minX,row.habitat.minY,row.habitat.minZ,row.habitat.maxX,row.habitat.maxY,row.habitat.maxZ)));return value;}
    private boolean hasIntent(Resident row)throws Exception{Path path=ledger.resolve(row.uuid+".intent.json");if(!Files.exists(path))return false;JsonObject actual=JsonParser.parseString(new String(bounded(path,8192),StandardCharsets.UTF_8)).getAsJsonObject();if(!actual.equals(intent(row)))throw new IllegalStateException("Retained world intent differs; never replace resident");return true;}
    private boolean identity(Resident row,Entity entity){return entity instanceof Mob&&entity.level()==level&&entity.getType()==row.type&&entity.getClass().getName().equals(row.nativeClass)&&entity.getTags().contains("awft_life")&&entity.getTags().contains(row.tag)&&row.habitat.contains(entity.position());}
    private Entity current(MinecraftServer server,UUID uuid){Entity found=null;for(ServerLevel dimension:server.getAllLevels()){Entity value=dimension.getEntity(uuid);if(value!=null){if(found!=null)throw new IllegalStateException("UUID is loaded in more than one dimension; preserve both");found=value;}}return found;}
    private void flags(Mob mob,boolean newborn){boolean tame=false,owner=false;if(mob instanceof TamableAnimal pet){tame=pet.isTame();owner=pet.getOwnerUUID()!=null;}HabitatLifePolicy.live(mob.isNoAi(),mob.isPassenger()||!mob.getPassengers().isEmpty(),mob.isAlive(),newborn,tame,owner);if(mob instanceof Enemy)throw new IllegalStateException("Hostile native class refused");}
    private Mob preview(Resident row)throws Exception{
        Entity created=row.type.create(level);if(!(created instanceof Mob mob)||!created.getClass().getName().equals(row.nativeClass))throw new IllegalStateException("Native entity factory/class differs");mob.setUUID(row.uuid);mob.moveTo(row.x,row.y,row.z,0,0);flags(mob,true);
        for(var entry:row.before.entrySet())if(!level.getBlockState(entry.getKey()).equals(entry.getValue()))throw new IllegalStateException("Actual habitat preimage changed at "+entry.getKey());
        if(!level.getFluidState(mob.blockPosition()).isEmpty()||!level.getBlockState(mob.blockPosition().below()).isFaceSturdy(level,mob.blockPosition().below(),net.minecraft.core.Direction.UP)
            ||!level.noCollision(mob,mob.getBoundingBox())||!mob.checkSpawnObstruction(level)||!SpawnPlacements.checkSpawnRules(row.type,level,MobSpawnType.STRUCTURE,mob.blockPosition(),net.minecraft.util.RandomSource.create(row.uuid.getLeastSignificantBits()))
            ||!EventHooks.checkSpawnPosition(mob,level,MobSpawnType.STRUCTURE))throw new IllegalStateException("Current native footing/water/collision/spawn rules refused "+row.uuid);
        return mob;
    }
    private Map<String,Object> observation(Resident row,Mob mob,boolean existing)throws Exception{CompoundTag tag=mob.saveWithoutId(new CompoundTag());byte[] raw=tag.toString().getBytes(StandardCharsets.UTF_8);if(raw.length>65536)throw new IllegalStateException("Native resident NBT exceeds diagnostic bound");boolean owner=mob instanceof TamableAnimal pet&&pet.getOwnerUUID()!=null;return Map.of("uuid",row.uuid.toString(),"type",BuiltInRegistries.ENTITY_TYPE.getKey(mob.getType()).toString(),"native_class",mob.getClass().getName(),"position",List.of(mob.getX(),mob.getY(),mob.getZ()),"existing_preserved",existing,"NoAI",mob.isNoAi(),"has_native_owner",owner,"native_nbt_sha256",sha(raw));}
    private static void durable(Path path,JsonObject value)throws Exception{byte[] raw=(JSON.toJson(value)+"\n").getBytes(StandardCharsets.UTF_8);if(raw.length>8192)throw new IllegalStateException("LIFE ledger row exceeds bound");try(FileChannel out=FileChannel.open(path,StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE)){ByteBuffer bytes=ByteBuffer.wrap(raw);while(bytes.hasRemaining())out.write(bytes);out.force(true);}}
    public void tick(MinecraftServer server){
        if(phase==Phase.IDLE)return;
        if(phase==Phase.CLEANUP){pending.removeIf(CompletableFuture::isDone);if(tickets.isEmpty()&&pending.isEmpty())cleanup(false);return;}
        long start=System.nanoTime();
        try{
            if(++ticks>MAX_TICKS||!server.isSameThread()||lease==null||!lease.valid()||!server.getPlayerList().getPlayers().isEmpty())throw new IllegalStateException("LIFE lease/thread/empty-server/deadline guard refused");
            // No resetEmptyTime: this helper does not manufacture AI progress.
            if(phase==Phase.HASH){int n;do{n=hashStream.read(hashBuffer);if(n>0){hashDigest.update(hashBuffer,0,n);hashed+=n;}}while(n>=0&&System.nanoTime()-start<3_000_000L);if(n>=0)return;hashStream.close();hashStream=null;BasicFileAttributes after=Files.readAttributes(hashPath,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);if(hashed!=hashBefore.size()||after.size()!=hashBefore.size()||!after.lastModifiedTime().equals(hashBefore.lastModifiedTime())||!Objects.equals(after.fileKey(),hashBefore.fileKey())||!HexFormat.of().formatHex(hashDigest.digest()).equals(MOD_SHA))throw new IllegalStateException("Exact pinned wildlife JAR changed");phase=Phase.LOAD;for(ChunkPos c:chunks){tickets.add(c);ticket(c,true);pending.add(((worldfortwo.bridge.mixin.ChunkCacheAccess)(Object)level.getChunkSource()).awftQueueChunk(c.x,c.z,ChunkStatus.FULL,false));}return;}
            if(phase==Phase.LOAD){if(pending.stream().anyMatch(f->!f.isDone()))return;for(var future:pending)future.join();pending.clear();if(!ready())return;phase=Phase.VALIDATE;}
            gate(server);
            if(phase==Phase.VALIDATE){
                Resident row=residents.get(index++);Entity existing=current(server,row.uuid);boolean owned=hasIntent(row);if(censusMembers.get(row.uuid).get("present").getAsBoolean()&&!owned)throw new IllegalStateException("Stopped-world UUID exists without this retained world intent; never duplicate/adopt blindly");HabitatLifePolicy.Existing choice=HabitatLifePolicy.existing(owned,existing!=null,existing!=null&&identity(row,existing));
                if(choice==HabitatLifePolicy.Existing.PRESERVE){flags((Mob)existing,false);previews.add(null);}else previews.add(preview(row));
                if(index==residents.size()){index=0;phase=Phase.WORK;}return;
            }
            if(phase==Phase.WORK){Resident row=residents.get(index);Mob mob=previews.get(index);Entity existing=current(server,row.uuid);
                if(mob==null){if(existing==null||!identity(row,existing)||!hasIntent(row))throw new IllegalStateException("Existing native resident changed; preserve uncertainty");flags((Mob)existing,false);observed.add(observation(row,(Mob)existing,true));preserved++;}
                else if(action.equals("inspect")){if(existing!=null||hasIntent(row))throw new IllegalStateException("UUID changed during inspection");preview(row);observed.add(Map.of("uuid",row.uuid.toString(),"type",row.id,"native_class",row.nativeClass,"new_habitat_currently_admissible",true,"spawned",false));}
                else{
                    if(existing!=null||hasIntent(row))throw new IllegalStateException("UUID changed before native spawn");mob=preview(row);
                    EventHooks.finalizeMobSpawn(mob,level,level.getCurrentDifficultyAt(mob.blockPosition()),MobSpawnType.STRUCTURE,null);
                    finalized++;
                    boolean cancelled;try{cancelled=(boolean)MethodHandles.publicLookup().findVirtual(Mob.class,"isSpawnCancelled",MethodType.methodType(boolean.class)).invoke(mob);}catch(Throwable error){throw new IllegalStateException("Pinned native spawn-cancellation API unavailable",error);}
                    flags(mob,true);if(cancelled||!mob.getUUID().equals(row.uuid)||!level.noCollision(mob,mob.getBoundingBox()))throw new IllegalStateException("Native finalize event/UUID/body refused; no add");
                    if(!mob.addTag("awft_life")||!mob.addTag(row.tag))throw new IllegalStateException("Native unique population tags refused");mob.setPersistenceRequired();
                    Files.createDirectories(ledger);durable(ledger.resolve(row.uuid+".intent.json"),intent(row));intentsWritten++;
                    if(!level.addFreshEntity(mob))throw new IllegalStateException("Native addFreshEntity refused; intent retained, never retry blindly");
                    spawned++;
                    if(level.getEntity(row.uuid)!=mob||!identity(row,mob))throw new IllegalStateException("Actual native entity identity readback differs");flags(mob,false);
                    JsonObject admitted=intent(row);admitted.addProperty("native_added",Instant.now().toString());durable(ledger.resolve(row.uuid+".admitted.json"),admitted);observed.add(observation(row,mob,false));
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
        report.put("status",outcome);report.put("cleanup_passed",clean);report.put("cleanup_required",!clean);report.put("temporary_tickets_remaining",tickets.size());report.put("pending_shared_futures",pending.size());report.put("cleanup_errors",errors);report.put("observations",List.copyOf(observed));report.put("finished",Instant.now().toString());report.put("NoAI_or_ownership_writes",0);report.put("global_wakes",0);report.put("spawned",spawned);report.put("intents_written",intentsWritten);report.put("native_finalizations",finalized);report.put("world_mutated",spawned>0||intentsWritten>0);
        try{if(clean||!cleanupPublished){NativeJournal.progress(journal,"life-status.json",report);NativeJournal.terminal(journal,"habitat-life",report);cleanupPublished=true;}}catch(Exception error){System.err.println("AWFT LIFE journal: "+error);}
        if(clean){phase=Phase.IDLE;previews.clear();}
    }
    public void stopped(){if(busy())finish("server stopping; native residents and uncertainty retained");}
}
