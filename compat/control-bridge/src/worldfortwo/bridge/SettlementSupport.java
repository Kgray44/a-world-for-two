package worldfortwo.bridge;

import com.google.gson.*;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.arguments.BoolArgumentType;
import net.minecraft.commands.Commands;
import net.minecraft.core.*;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.TagParser;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.*;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.Property;
import net.minecraft.world.level.chunk.ChunkAccess;
import net.minecraft.world.level.chunk.status.ChunkStatus;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.storage.LevelResource;
import net.neoforged.fml.ModList;
import net.neoforged.fml.loading.FMLPaths;
import net.neoforged.neoforge.event.RegisterCommandsEvent;

import java.nio.file.*;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.CompletableFuture;
import net.minecraft.world.level.ChunkPos;

/** Console-only, bounded native construction. No live region-file editing or permanent chunk tickets.
 * Plans are admitted by their exact SHA-256, seed, world path and verified backup receipt.
 * Every action is journaled; restart never silently resumes a partially executed plan.
 */
public final class SettlementSupport {
    private static final Gson JSON = new GsonBuilder().create();
    private static final int MAX_BLOCKS=600_000, MAX_PLAN_BYTES=32*1024*1024;
    private final Path directory=FMLPaths.GAMEDIR.get().resolve("../dashboard/settlement").toAbsolutePath().normalize();
    private final Map<String,Object> report=new LinkedHashMap<>();
    private final List<Map<String,Object>> samples=new ArrayList<>();
    private JsonObject plan;
    private List<BlockState> palette;
    private String operation="idle";
    private int cursor, phase, centerX, centerZ, radius, step, columns, failures;
    private int settlePass,settleChanges,neighborWait;
    private final List<Integer> settlePassChanges=new ArrayList<>();
    private final Set<BlockPos> settleSkippedBlockEntities=new HashSet<>();
    private long nextWrite;
    private CompletableFuture<ChunkResult<ChunkAccess>> pending;
    private final List<CompletableFuture<ChunkResult<ChunkAccess>>> neighborhood=new ArrayList<>();
    private int pendingX, pendingZ;
    private ChunkAccess ready;
    private static final TicketType<ChunkPos> BUILD_TICKET=TicketType.create("awft_settlement",Comparator.comparingLong(ChunkPos::toLong));
    private ServerLevel ticketLevel;
    private ChunkPos ticketPos;
    private final Set<Long> mapChunks=new HashSet<>();
    private Object mapWorld;
    private java.util.function.BooleanSupplier admissionGate=()->true;
    public void admissionGate(java.util.function.BooleanSupplier gate){admissionGate=Objects.requireNonNull(gate);}
    public boolean busy(){return !operation.equals("idle") || ticketLevel!=null || ticketPos!=null || pending!=null || !neighborhood.isEmpty();}
    public void stopped(){if(busy())finish("server stopping; existing construction retained");}

    public void commands(RegisterCommandsEvent event) {
        var root=Commands.literal("awftbuild").requires(s->s.getEntity()==null && s.hasPermission(4) && admissionGate.getAsBoolean());
        root.then(Commands.literal("registry").executes(c->{
            try { registry(c.getSource().getServer()); success(c.getSource(),"Native registry exported");return 1; }
            catch(Exception e){throw new RuntimeException(e);}
        }));
        root.then(Commands.literal("fingerprint").executes(c->{
            try {
                Class<?> target=Class.forName("mobius.seedrenderer.net.SeedSharing");
                var lookup=java.lang.invoke.MethodHandles.privateLookupIn(target,java.lang.invoke.MethodHandles.lookup());
                var method=lookup.findStatic(target,"computePrint",java.lang.invoke.MethodType.methodType(String.class,RegistryAccess.class));
                Object value=method.invoke(c.getSource().getServer().registryAccess());
                write("fingerprint.json",Map.of("at",Instant.now().toString(),"fingerprint",String.valueOf(value),"source","Actual transformed SeedGen computePrint on this dedicated server"));
                success(c.getSource(),"SeedGen native fingerprint: "+value); return 1;
            }catch(Throwable e){
                e.printStackTrace();
                try {write("fingerprint.json",Map.of("at",Instant.now().toString(),"status","failed; safe SeedGen refusal remains active","error",e.toString()));}catch(Exception ignored){}
                c.getSource().sendFailure(Component.literal("Native fingerprint probe failed; exact error preserved"));return 0;
            }
        }));
        root.then(Commands.literal("worldgen-inputs")
            .then(Commands.argument("id",StringArgumentType.word())
            .then(Commands.argument("full",BoolArgumentType.bool()).executes(c->{
                try {
                    MinecraftServer server=c.getSource().getServer();
                    Path home=directory.getParent().getParent().toRealPath();
                    JsonObject owner=JsonParser.parseString(Files.readString(home.resolve("dashboard/artistic-owner.json"))).getAsJsonObject();
                    if(!owner.get("format").getAsString().equals("awft-artistic-stage:1")
                        || !Path.of(owner.get("home").getAsString()).toRealPath().equals(home)
                        || server.getPort()!=25575 || !server.getPlayerList().getPlayers().isEmpty())
                        throw new IllegalStateException("A measured empty, owned private staging server is required");
                    Path output=directory.resolve("worldgen-inputs");
                    Files.createDirectories(output);
                    Path receipt=WorldgenFingerprintDiagnostics.write(server.registryAccess(),output,
                        StringArgumentType.getString(c,"id"),"server_registry_access",BoolArgumentType.getBool(c,"full"));
                    if(ModList.get().isLoaded("lithostitched")){
                        RegistryAccess actual=server.registryAccess();
                        var generators=new LinkedHashMap<net.minecraft.resources.ResourceKey<net.minecraft.world.level.Level>,net.minecraft.world.level.chunk.ChunkGenerator>();
                        for(ServerLevel current:server.getAllLevels())generators.put(current.dimension(),current.getChunkSource().getGenerator());
                        var captured=Map.copyOf(generators);
                        NativeWorldgenWitnessTask.start(actual,captured,output,StringArgumentType.getString(c,"id"),"actual_server_levels",server::execute,()->{
                            if(!server.isSameThread()||server.registryAccess()!=actual)return false;
                            var now=new LinkedHashMap<net.minecraft.resources.ResourceKey<net.minecraft.world.level.Level>,net.minecraft.world.level.chunk.ChunkGenerator>();
                            for(ServerLevel current:server.getAllLevels())now.put(current.dimension(),current.getChunkSource().getGenerator());
                            return now.equals(captured);
                        });
                    }
                    success(c.getSource(),"Read-only worldgen inputs exported; inspect private status "+receipt.getFileName());return 1;
                } catch(Exception|LinkageError error){
                    error.printStackTrace();
                    c.getSource().sendFailure(Component.literal("Worldgen diagnostic failed; existing inputs and strict SeedGen comparison remain unchanged"));return 0;
                }
            }))));
        for(String mode:List.of("noise","survey")) {
            root.then(Commands.literal(mode).then(Commands.argument("x",IntegerArgumentType.integer(-25000000,25000000))
                .then(Commands.argument("z",IntegerArgumentType.integer(-25000000,25000000))
                .then(Commands.argument("radius",IntegerArgumentType.integer(16,4096))
                .then(Commands.argument("step",IntegerArgumentType.integer(4,256)).executes(c->{
                    if(busy())return 0;
                    centerX=IntegerArgumentType.getInteger(c,"x");centerZ=IntegerArgumentType.getInteger(c,"z");
                    radius=IntegerArgumentType.getInteger(c,"radius");step=IntegerArgumentType.getInteger(c,"step");
                    columns=radius*2/step+1;
                    if(columns*columns>5000 || mode.equals("survey") && radius>256)return 0;
                    start(mode); return 1;
                }))))));
        }
        for(String mode:List.of("place","verify","map","settle")) root.then(Commands.literal(mode)
            .then(Commands.argument("sha256",StringArgumentType.word()).executes(c->{
                try { admit(c.getSource().getServer(),mode,StringArgumentType.getString(c,"sha256"));return 1; }
                catch(Exception e){e.printStackTrace();throw new RuntimeException(e);}
            })));
        root.then(Commands.literal("cancel").executes(c->{finish("cancelled; existing work retained");return 1;}));
        root.then(Commands.literal("status").executes(c->{success(c.getSource(),JSON.toJson(report));return 1;}));
        event.getDispatcher().register(root);
    }

    private void success(net.minecraft.commands.CommandSourceStack source,String message){source.sendSuccess(()->Component.literal("AWFT settlement: "+message),true);}
    private void write(String name,Object value)throws Exception {
        Files.createDirectories(directory);
        Path target=directory.resolve(name), temporary=directory.resolve(name+".tmp");
        Files.writeString(temporary,JSON.toJson(value));
        Files.move(temporary,target,StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.ATOMIC_MOVE);
    }
    private static String sha(byte[] raw)throws Exception{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(raw));}
    private void registry(MinecraftServer server)throws Exception {
        Map<String,Object> blocks=new TreeMap<>();
        for(Block block:BuiltInRegistries.BLOCK){
            Map<String,Object> properties=new TreeMap<>();
            for(Property<?> property:block.getStateDefinition().getProperties())
                properties.put(property.getName(),serializedValues(property));
            blocks.put(BuiltInRegistries.BLOCK.getKey(block).toString(),properties);
        }
        Map<String,Object> output=new LinkedHashMap<>();
        output.put("at",Instant.now().toString()); output.put("blocks",blocks);
        output.put("items",BuiltInRegistries.ITEM.keySet().stream().map(Object::toString).sorted().toList());
        output.put("entities",BuiltInRegistries.ENTITY_TYPE.keySet().stream().map(Object::toString).sorted().toList());
        Map<String,String> categories=new TreeMap<>();
        BuiltInRegistries.ENTITY_TYPE.forEach(type->categories.put(BuiltInRegistries.ENTITY_TYPE.getKey(type).toString(),type.getCategory().getName()));
        output.put("entity_categories",categories);
        output.put("mods",ModList.get().getMods().stream().map(m->Map.of("id",m.getModId(),"name",m.getDisplayName(),"version",m.getVersion().toString())).toList());
        output.put("seed",Long.toString(server.overworld().getSeed()));
        output.put("world_path",server.getWorldPath(LevelResource.ROOT).toAbsolutePath().normalize().toString());
        output.put("spawn",List.of(server.overworld().getSharedSpawnPos().getX(),server.overworld().getSharedSpawnPos().getY(),server.overworld().getSharedSpawnPos().getZ()));
        if(JSON.toJson(output).length()>16*1024*1024)throw new IllegalStateException("Registry export exceeds bound");
        write("registry.json",output);
    }

    @SuppressWarnings({"unchecked","rawtypes"})
    private BlockState state(String text) {
        String id=text.split("\\[",2)[0]; ResourceLocation key=ResourceLocation.parse(id);
        if(!BuiltInRegistries.BLOCK.containsKey(key))throw new IllegalArgumentException("Unknown actual block: "+id);
        BlockState state=BuiltInRegistries.BLOCK.get(key).defaultBlockState();
        if(text.contains("[")) {
            if(!text.endsWith("]"))throw new IllegalArgumentException("Invalid state "+text);
            for(String entry:text.substring(text.indexOf('[')+1,text.length()-1).split(",")){
                String[] pair=entry.split("=",2);
                Property property=state.getBlock().getStateDefinition().getProperty(pair[0]);
                if(property==null || pair.length!=2)throw new IllegalArgumentException("Unknown state property "+entry);
                Optional valueOption=property.getValue(pair[1]);
                if(valueOption.isEmpty())throw new IllegalArgumentException("Invalid state value "+entry);
                Comparable value=(Comparable)valueOption.get();
                state=state.setValue(property,value);
            }
        }
        return state;
    }
    private void admit(MinecraftServer server,String mode,String expected)throws Exception {
        if(busy() || !expected.matches("[a-f0-9]{64}"))throw new IllegalStateException("Another operation or shared chunk cleanup is active, or invalid hash");
        if(!server.getPlayerList().getPlayers().isEmpty())throw new IllegalStateException("Construction needs an empty server");
        Path file=directory.resolve("plan.json");
        if(Files.isSymbolicLink(file) || Files.size(file)>MAX_PLAN_BYTES)throw new IllegalStateException("Plan exceeds bound or is linked");
        byte[] raw=Files.readAllBytes(file);
        if(!sha(raw).equals(expected))throw new IllegalStateException("Exact plan hash differs");
        JsonObject candidate=JsonParser.parseString(new String(raw,java.nio.charset.StandardCharsets.UTF_8)).getAsJsonObject();
        if(mode.equals("place") && candidate.has("construction_forbidden") && candidate.get("construction_forbidden").getAsBoolean())
            throw new IllegalStateException("A native verification-only export cannot replay geometry or inventories");
        if(!candidate.get("seed").getAsString().equals(Long.toString(server.overworld().getSeed())))throw new IllegalStateException("World seed differs");
        if(!Path.of(candidate.get("world_path").getAsString()).toAbsolutePath().normalize().equals(server.getWorldPath(LevelResource.ROOT).toAbsolutePath().normalize()))throw new IllegalStateException("Actual world path differs");
        JsonObject backup=JsonParser.parseString(Files.readString(directory.resolve("backup-receipt.json"))).getAsJsonObject();
        if(!backup.get("verified").getAsBoolean() || !backup.get("sha256").getAsString().equals(candidate.get("backup_sha256").getAsString()))throw new IllegalStateException("Verified pre-construction backup required");
        List<BlockState> states=new ArrayList<>();
        for(JsonElement entry:candidate.getAsJsonArray("palette"))states.add(state(entry.getAsString()));
        JsonArray blocks=candidate.getAsJsonArray("blocks");
        if(blocks.size()>MAX_BLOCKS || states.size()>8192)throw new IllegalStateException("Construction exceeds bound");
        if(mode.equals("settle") && (blocks.size()>20_000 || candidate.getAsJsonArray("commands").size()!=0))
            throw new IllegalStateException("Neighbor reconciliation requires at most20000 exact targets and no commands");
        int[] bounds=new int[4];for(int i=0;i<4;i++)bounds[i]=candidate.getAsJsonArray("bounds").get(i).getAsInt();
        if(bounds[2]-bounds[0]>512 || bounds[3]-bounds[1]>512)throw new IllegalStateException("Footprint exceeds bound");
        for(JsonElement entry:blocks){
            JsonArray row=entry.getAsJsonArray();int x=row.get(0).getAsInt(),y=row.get(1).getAsInt(),z=row.get(2).getAsInt(),p=row.get(3).getAsInt();
            if(row.size()!=4 || x<bounds[0] || x>bounds[2] || z<bounds[1] || z>bounds[3] || y<-64 || y>=320 || p<0 || p>=states.size())throw new IllegalStateException("Invalid bounded block placement");
        }
        JsonArray tags=candidate.getAsJsonArray("block_entities");
        if(tags.size()>4096)throw new IllegalStateException("Block entity bound exceeded");
        for(JsonElement entry:tags){
            JsonObject row=entry.getAsJsonObject();JsonArray p=row.getAsJsonArray("pos");
            int x=p.get(0).getAsInt(),y=p.get(1).getAsInt(),z=p.get(2).getAsInt();
            if(x<bounds[0] || x>bounds[2] || z<bounds[1] || z>bounds[3] || y<-64 || y>=320)throw new IllegalStateException("Block entity outside reviewed footprint");
            String nbt=row.get("nbt").getAsString();
            if(nbt.length()>16384)throw new IllegalStateException("Block entity data exceeds bound");
            TagParser.parseTag(nbt);
        }
        JsonArray commands=candidate.getAsJsonArray("commands");
        if(commands.size()>256)throw new IllegalStateException("Entity/action bound exceeded");
        for(JsonElement entry:commands){
            String command=entry.getAsString();
            if(command.length()>4096 || command.contains("\n") || !command.matches("(?:summon |item replace block |data merge block |setworldspawn |gamerule spawnRadius ).+"))throw new IllegalStateException("Unapproved construction action");
            var parsed=server.getCommands().getDispatcher().parse(command,server.createCommandSourceStack());
            if(!parsed.getExceptions().isEmpty() || parsed.getReader().canRead())throw new IllegalStateException("Native command did not parse: "+command);
        }
        plan=candidate;palette=states;start(mode);report.put("plan_sha256",expected);report.put("blocks",blocks.size());
    }
    private void start(String mode){operation=mode;cursor=phase=failures=0;pending=null;ready=null;neighborWait=settlePass=settleChanges=0;settlePassChanges.clear();settleSkippedBlockEntities.clear();mapChunks.clear();mapWorld=null;samples.clear();report.clear();report.put("operation",mode);report.put("started",Instant.now().toString());report.put("status","running");}
    private void finish(String status){
        try{releaseTicket();report.remove("ticket_cleanup_error");}
        catch(Exception error){report.put("ticket_cleanup_error",error.toString());}
        neighborhood.removeIf(CompletableFuture::isDone);
        if(pending!=null && pending.isDone())pending=null;
        boolean cleanup=ticketLevel!=null || ticketPos!=null || pending!=null || !neighborhood.isEmpty();
        report.put("status",status);report.put("finished",Instant.now().toString());report.put("cursor",cursor);report.put("failures",failures);
        report.put("cleanup_required",cleanup);report.put("temporary_tickets_remaining",ticketPos==null?0:1);
        report.put("pending_shared_chunk_futures",neighborhood.size());
        try {if(operation.equals("survey")||operation.equals("noise"))write(operation+".json",Map.of("report",new LinkedHashMap<>(report),"samples",samples));NativeJournal.terminal(directory,"settlement",report);NativeJournal.progress(directory,"status.json",report);}
        catch(Exception error){System.err.println("AWFT settlement journal: "+error);}
        operation=cleanup?"cleanup_required":"idle";ready=null;
    }
    @SuppressWarnings({"rawtypes","unchecked"})
    private static List<String> serializedValues(Property property){
        List<String> result=new ArrayList<>();
        for(Object value:property.getPossibleValues())result.add(property.getName((Comparable)value));
        return result;
    }
    private void releaseTicket(){
        if(ticketLevel!=null && ticketPos!=null)ticketLevel.getChunkSource().removeRegionTicket(BUILD_TICKET,ticketPos,1,ticketPos);
        ticketLevel=null;ticketPos=null;
    }
    private ChunkAccess chunk(ServerLevel level,int x,int z){
        int cx=Math.floorDiv(x,16),cz=Math.floorDiv(z,16);
        if(ready!=null && ready.getPos().x==cx && ready.getPos().z==cz && ticketLevel==level
                && ticketPos!=null && ticketPos.x==cx && ticketPos.z==cz && fullNeighborhood(level,cx,cz))return ready;
        ready=null;
        if(pending==null || pendingX!=cx || pendingZ!=cz){
            releaseTicket();ticketLevel=level;ticketPos=new ChunkPos(cx,cz);
            level.getChunkSource().addRegionTicket(BUILD_TICKET,ticketPos,1,ticketPos);
            pendingX=cx;pendingZ=cz;
            neighborWait=0;
            // Native placement hooks (notably wither-skull structure matching)
            // inspect adjacent chunks. A FULL center alone is insufficient.
            // One finite radius-one ticket and nine actual FULL futures cover
            // vanilla structure-pattern reads up to four blocks across every
            // chunk edge, without skipping the actual golem/wither checks.
            neighborhood.clear();
            for(int dx=-1;dx<=1;dx++)for(int dz=-1;dz<=1;dz++){
                var future=((worldfortwo.bridge.mixin.ChunkCacheAccess)(Object)level.getChunkSource()).awftQueueChunk(cx+dx,cz+dz,ChunkStatus.FULL,true);
                neighborhood.add(future);if(dx==0 && dz==0)pending=future;
            }
        }
        if(++neighborWait>600)throw new IllegalStateException("Finite native neighbor readiness timeout");
        if(neighborhood.stream().anyMatch(future->!future.isDone()))return null;
        for(var future:neighborhood)if(future.join().orElse(null)==null)throw new IllegalStateException("Native placement neighbor could not be loaded");
        if(!fullNeighborhood(level,cx,cz))return null;
        ready=pending.join().orElse(null);pending=null;neighborhood.clear();
        if(ready==null)throw new IllegalStateException("Native chunk could not be loaded");
        return ready;
    }
    private boolean fullNeighborhood(ServerLevel level,int cx,int cz){
        for(int dx=-1;dx<=1;dx++)for(int dz=-1;dz<=1;dz++)if(level.getChunkSource().getChunkNow(cx+dx,cz+dz)==null)return false;
        return true;
    }
    public void tick(MinecraftServer server){
        if(operation.equals("cleanup_required")){
            if(ticketLevel==null && ticketPos==null && neighborhood.stream().allMatch(CompletableFuture::isDone)
                    && (pending==null || pending.isDone()))finish("shared native chunk work completed; prior partial operation remains unaccepted");
            return;
        }
        if(operation.equals("idle"))return;
        if(!server.getPlayerList().getPlayers().isEmpty()){finish("paused; player joined, explicit resume/restart required");return;}
        long begin=System.nanoTime();int work=0;
        try{
            ServerLevel level=server.overworld();
            while(work++<192 && System.nanoTime()-begin<4_000_000L){
                if(operation.equals("noise")||operation.equals("survey")){
                    if(cursor>=columns*columns){finish("complete");break;}
                    int x=centerX-radius+(cursor%columns)*step,z=centerZ-radius+(cursor/columns)*step,y;
                    Map<String,Object> row=new LinkedHashMap<>();row.put("x",x);row.put("z",z);
                    if(operation.equals("noise")){
                        y=level.getChunkSource().getGenerator().getBaseHeight(x,z,Heightmap.Types.WORLD_SURFACE_WG,level,level.getChunkSource().randomState());
                        var biome=level.getChunkSource().getGenerator().getBiomeSource().getNoiseBiome(Math.floorDiv(x,4),Math.floorDiv(y,4),Math.floorDiv(z,4),level.getChunkSource().randomState().sampler());
                        row.put("biome",biome.unwrapKey().map(k->k.location().toString()).orElse("unknown"));
                        row.put("source","native generator base-height estimate; not a generated surface or build inspection");
                    }else{
                        ChunkAccess chunk=chunk(level,x,z);if(chunk==null)break;
                        y=chunk.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES,Math.floorMod(x,16),Math.floorMod(z,16))+1;
                        BlockPos pos=new BlockPos(x,y-1,z);
                        row.put("block",BuiltInRegistries.BLOCK.getKey(chunk.getBlockState(pos).getBlock()).toString());
                        row.put("fluid",!chunk.getFluidState(pos).isEmpty());
                        int ground=y-1;
                        while(ground>level.getMinBuildHeight()){
                            BlockPos groundPos=new BlockPos(x,ground,z);var state=chunk.getBlockState(groundPos);
                            if(state.blocksMotion() && !state.is(net.minecraft.tags.BlockTags.LOGS) && !state.is(net.minecraft.tags.BlockTags.LEAVES))break;
                            ground--;
                        }
                        row.put("ground_y",ground+1);
                        row.put("ocean_floor_y",chunk.getHeight(Heightmap.Types.OCEAN_FLOOR,Math.floorMod(x,16),Math.floorMod(z,16))+1);
                        row.put("block_entities",chunk.getBlockEntitiesPos().stream().map(p->List.of(p.getX(),p.getY(),p.getZ())).toList());
                        var biome=chunk.getNoiseBiome(Math.floorDiv(x,4),Math.floorDiv(y,4),Math.floorDiv(z,4));
                        row.put("biome",biome.unwrapKey().map(k->k.location().toString()).orElse("unknown"));
                        row.put("source","actual generated native chunk surface");
                    }
                    row.put("y",y);samples.add(row);cursor++;
                }else{
                    JsonArray blocks=plan.getAsJsonArray("blocks");
                    if(operation.equals("map")){
                        if(cursor>=blocks.size()){report.put("queued_chunks",mapChunks.size());finish("existing construction chunks queued through squaremap's native update mechanism");break;}
                        JsonArray row=blocks.get(cursor++).getAsJsonArray();int cx=row.get(0).getAsInt()>>4,cz=row.get(2).getAsInt()>>4;
                        if(mapChunks.add(ChunkPos.asLong(cx,cz))){
                            if(mapWorld==null){
                                Object api=Class.forName("xyz.jpenilla.squaremap.api.SquaremapProvider").getMethod("get").invoke(null);
                                Class<?> apiType=Class.forName("xyz.jpenilla.squaremap.api.Squaremap");
                                for(Object candidate:(Iterable<?>)apiType.getMethod("mapWorlds").invoke(api))
                                    if(candidate.getClass().getMethod("serverLevel").invoke(candidate)==level){mapWorld=candidate;break;}
                                if(mapWorld==null)throw new IllegalStateException("squaremap has no active Overworld");
                            }
                            Class<?> coordinate=Class.forName("xyz.jpenilla.squaremap.common.data.ChunkCoordinate");
                            Object chunk=coordinate.getConstructor(int.class,int.class).newInstance(cx,cz);
                            mapWorld.getClass().getMethod("chunkModified",coordinate).invoke(mapWorld,chunk);
                        }
                        continue;
                    }
                    if(phase==0 && cursor<blocks.size()){
                        JsonArray row=blocks.get(cursor).getAsJsonArray();BlockPos pos=new BlockPos(row.get(0).getAsInt(),row.get(1).getAsInt(),row.get(2).getAsInt());
                        ChunkAccess chunk=chunk(level,pos.getX(),pos.getZ());if(chunk==null)break;
                        BlockState expected=palette.get(row.get(3).getAsInt());
                        if(operation.equals("place"))level.setBlock(pos,expected,2|16);
                        else if(operation.equals("settle")){
                            BlockState current=level.getBlockState(pos);
                            if(!sameStructure(current,expected))throw new IllegalStateException("Neighbor reconciliation structural preimage differs at "+pos);
                            // Read current native states. Never replay source states,
                            // block-entity data, inventories or plan commands.
                            if(current.hasBlockEntity() || level.getBlockEntity(pos)!=null)settleSkippedBlockEntities.add(pos);
                            else{
                                BlockState updated=Block.updateFromNeighbourShapes(current,level,pos);
                                if(!sameStructure(updated,expected))throw new IllegalStateException("Normal neighbor shape would remove or reorient the authored structure at "+pos);
                                if(updated!=current){if(!level.setBlock(pos,updated,3))throw new IllegalStateException("Normal native neighbor update refused");settleChanges++;}
                                level.updateNeighborsAt(pos,level.getBlockState(pos).getBlock());
                                if(!sameStructure(level.getBlockState(pos),expected))throw new IllegalStateException("Native neighbor effects changed authored identity/orientation at "+pos);
                            }
                        }
                        else if(!samePlacement(chunk.getBlockState(pos),expected)){
                            failures++;if(failures<=30)System.err.println("AWFT settlement verification differs at "+pos+": "+chunk.getBlockState(pos)+" vs "+expected);
                        }
                        cursor++;
                    }else if(phase==0 && operation.equals("settle")){
                        settlePassChanges.add(settleChanges);report.put("normal_shape_changes_per_pass",List.copyOf(settlePassChanges));
                        report.put("block_entity_targets_skipped",settleSkippedBlockEntities.size());
                        if(++settlePass<3){settleChanges=cursor=0;continue;}
                        if(settleChanges!=0)throw new IllegalStateException("Native neighbor shapes did not converge within three bounded passes");
                        finish("normal native neighbor shapes reconciled; no source state, inventory or command replay");break;
                    }else if(phase==0){phase=1;cursor=0;}
                    else if(phase==1){
                        JsonArray tags=plan.getAsJsonArray("block_entities");
                        if(cursor>=tags.size()){
                            if(operation.equals("verify")){finish(failures==0?"verified actual block identities, orientation, block entities and supplied inventories":"verification failed; inspect differences");break;}
                            phase=2;cursor=0;continue;
                        }
                        JsonObject row=tags.get(cursor).getAsJsonObject();JsonArray p=row.getAsJsonArray("pos");BlockPos pos=new BlockPos(p.get(0).getAsInt(),p.get(1).getAsInt(),p.get(2).getAsInt());
                        if(chunk(level,pos.getX(),pos.getZ())==null)break;
                        var entity=level.getBlockEntity(pos);if(entity==null)throw new IllegalStateException("No actual block entity at "+pos);
                        var tag=TagParser.parseTag(row.get("nbt").getAsString());
                        if(operation.equals("verify")){
                            var saved=entity.saveWithFullMetadata(level.registryAccess());
                            if(tag.contains("Items") && !net.minecraft.nbt.NbtUtils.compareNbt(tag.get("Items"),saved.get("Items"),true)){
                                failures++;System.err.println("AWFT settlement inventory verification differs at "+pos);
                            }
                        }else{entity.loadWithComponents(tag,level.registryAccess());entity.setChanged();}
                        cursor++;
                    }else{
                        JsonArray commands=plan.getAsJsonArray("commands");
                        if(cursor>=commands.size()){finish("construction actions complete; native verification and restart still required");break;}
                        String command=commands.get(cursor).getAsString();
                        if(!command.startsWith("gamerule ")){
                            String[] words=command.split(" ");int offset=command.startsWith("summon ")?2:command.startsWith("setworldspawn ")?1:3;
                            int x=(int)Math.floor(Double.parseDouble(words[offset])),z=(int)Math.floor(Double.parseDouble(words[offset+2]));
                            if(chunk(level,x,z)==null)break;
                            if(command.startsWith("summon ") && command.contains("{")){
                                var tag=TagParser.parseTag(command.substring(command.indexOf('{')));
                                if(!tag.hasUUID("UUID"))throw new IllegalStateException("Showcase entities need a stable UUID for idempotent placement");
                                if(level.getEntity(tag.getUUID("UUID"))!=null){cursor++;continue;}
                            }
                        }
                        boolean[] result={false,false};
                        var source=server.createCommandSourceStack().withCallback((success,value)->{result[0]=true;result[1]=success;});
                        server.getCommands().performPrefixedCommand(source,command);
                        if(!result[0] || !result[1])throw new IllegalStateException("Native construction command failed or did not report success at index "+cursor);
                        cursor++;
                    }
                }
            }
            report.put("cursor",cursor);report.put("phase",phase);report.put("failures",failures);
            double ms=(System.nanoTime()-begin)/1_000_000.0;
            report.put("last_work_ms",ms);report.put("max_work_ms",Math.max(ms,((Number)report.getOrDefault("max_work_ms",0)).doubleValue()));
            if(System.nanoTime()>nextWrite){NativeJournal.progress(directory,"status.json",report);nextWrite=System.nanoTime()+5_000_000_000L;}
        }catch(Exception error){report.put("error",error.toString());finish("failed; partial world and exact plan preserved, use pre-construction backup for rollback");}
    }

    private boolean samePlacement(BlockState actual,BlockState expected){
        if(actual.getBlock()!=expected.getBlock())return false;
        for(var property:expected.getProperties()){
            if(List.of("facing","axis","half","part","type","hinge").contains(property.getName()) && !actual.getValue(property).equals(expected.getValue(property)))return false;
        }
        return true;
    }
    private boolean sameStructure(BlockState actual,BlockState expected){
        if(actual.getBlock()!=expected.getBlock())return false;
        ResourceLocation id=BuiltInRegistries.BLOCK.getKey(actual.getBlock());
        String nativeClass=actual.getBlock().getClass().getName();
        // These two pinned native classes derive only their join geometry from
        // real neighbors. Beds and every other authored part remain structural.
        // Strict verification below still compares the canonical final part.
        boolean derivedPart=nativeClass.equals("com.mcwwindows.kikoz.objects.ConnectedWindow")
            && id.getNamespace().equals("mcwwindows")
            || nativeClass.equals("com.mcwroofs.kikoz.objects.roofs.RoofTopNew")
            && id.getNamespace().equals("mcwroofs") && id.getPath().endsWith("_top_roof");
        for(var property:expected.getProperties()){
            boolean structural=List.of("facing","axis","half","type","hinge","rotation").contains(property.getName())
                || property.getName().equals("part") && !derivedPart;
            if(structural && !actual.getValue(property).equals(expected.getValue(property)))return false;
        }
        return true;
    }
}
