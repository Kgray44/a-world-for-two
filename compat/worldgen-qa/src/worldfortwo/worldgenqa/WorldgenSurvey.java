package worldfortwo.worldgenqa;

import com.google.gson.*;
import com.mojang.serialization.JsonOps;
import net.minecraft.core.*;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.RegistryOps;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.chunk.*;
import net.minecraft.world.level.chunk.status.ChunkStatus;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.levelgen.structure.*;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadStructurePlacement;
import net.minecraft.world.level.storage.LevelResource;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.server.ServerStartedEvent;
import net.neoforged.neoforge.event.tick.ServerTickEvent;

import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;

/** Observations only inside an explicitly marked, private, disposable A/B server. */
@Mod("awft_worldgen_qa")
public final class WorldgenSurvey {
    private static final Gson GSON=new GsonBuilder().setPrettyPrinting().create();
    private static final String PURPOSE="awft-worldgen-disposable-ab:1";
    private JsonObject plan,report;
    private Path root,output;
    private long deadline,tickStart;
    private int index=0,ticks=0,idleTicks=0;
    private boolean active=false,failed=false;
    private final JsonArray tickSamples=new JsonArray(),chunks=new JsonArray(),scans=new JsonArray();
    private final List<Runnable> work=new ArrayList<>();
    private final Map<net.minecraft.world.level.block.state.BlockState,byte[]> stateBytes=new IdentityHashMap<>();

    public WorldgenSurvey(){
        NeoForge.EVENT_BUS.addListener(this::started);
        NeoForge.EVENT_BUS.addListener(this::pre);
        NeoForge.EVENT_BUS.addListener(this::post);
    }

    private static String hash(byte[] raw)throws Exception{
        return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(raw));
    }
    private static JsonArray ints(int... values){JsonArray a=new JsonArray();for(int n:values)a.add(n);return a;}
    private static JsonArray box(BoundingBox b){return ints(b.minX(),b.minY(),b.minZ(),b.maxX(),b.maxY(),b.maxZ());}
    private static void require(boolean value,String message){if(!value)throw new IllegalStateException(message);}
    private static JsonObject read(Path path)throws Exception{
        require(Files.isRegularFile(path)&&Files.size(path)<=65536,"Missing or oversized private test plan");
        return JsonParser.parseString(Files.readString(path)).getAsJsonObject();
    }

    private void started(ServerStartedEvent event){
        MinecraftServer server=event.getServer();
        try{
            require(Boolean.getBoolean("awft.worldgen.qa"),"Test-only JVM opt-in is required");
            root=Path.of("").toRealPath();
            // A runtime copy must be outside both permanent and construction homes.
            Path allowed=Path.of("D:/A World for Two/staging/worldgen-audit").toRealPath();
            require(root.startsWith(allowed)&&!root.equals(allowed),"Not an owned worldgen test directory");
            JsonObject owner=read(root.resolve("worldgen-test-owner.json"));
            require(owner.get("purpose").getAsString().equals(PURPOSE),"Wrong disposable owner marker");
            plan=read(root.resolve("worldgen-plan.json"));
            require(owner.get("id").equals(plan.get("owner_id")),"Plan owner differs");
            require(owner.get("master_thread").getAsString().equals("01a17947-1d00-7fd1-aa5e-d1fb514f8671"),"Master lease required");
            require(owner.get("lease_id").equals(plan.get("lease_id")),"Lease identity differs");
            require(plan.get("lease_expires_at_epoch_ms").getAsLong()>System.currentTimeMillis(),"Lease expired");
            java.util.Properties properties=new java.util.Properties();
            try(var reader=Files.newBufferedReader(root.resolve("server.properties"))){properties.load(reader);}
            require(properties.getProperty("server-ip", "").equals("127.0.0.1"),"Loopback binding is required");
            require(properties.getProperty("online-mode", "").equals("true"),"Online authentication must remain enabled");
            String arm=plan.get("arm").getAsString(),phase=plan.get("phase").getAsString();
            require(Set.of("baseline","updated").contains(arm),"Unknown test arm");
            require(Set.of("scan","full","restart").contains(phase),"Unknown observation phase");
            Path expected=root.resolve("test-worlds").resolve(arm).toRealPath();
            require(server.getWorldPath(LevelResource.ROOT).toRealPath().equals(expected),"Not the exact disposable save");
            require(server.getPort()==25585,"Only the leased loopback test port is admitted");
            require(server.getPlayerList().getPlayerCount()==0,"A player is present");
            ServerLevel level=server.overworld();
            require(level.getMinBuildHeight()==-64&&level.getHeight()==384,"Dimension height changed");
            String seedHash=hash(Long.toString(level.getSeed()).getBytes(StandardCharsets.UTF_8));
            require(seedHash.equals(plan.get("seed_sha256").getAsString()),"Saved seed differs");
            String run=plan.get("run_id").getAsString();
            require(run.matches("[a-z0-9-]{1,64}"),"Invalid receipt identifier");
            output=root.resolve(run+".json");
            require(!Files.exists(output),"Never overwrite an observation or failed receipt");
            report=new JsonObject();report.addProperty("format","awft-native-worldgen-survey:1");
            report.addProperty("run_id",run);report.addProperty("arm",arm);report.addProperty("phase",phase);
            report.addProperty("tier","ACTUAL_NATIVE_OBSERVATIONS; scan feasibility is not block placement");
            report.addProperty("seed_sha256",seedHash);report.addProperty("min_y",level.getMinBuildHeight());
            report.addProperty("height",level.getHeight());report.addProperty("status","RUNNING");
            report.addProperty("plan_sha256",hash(Files.readAllBytes(root.resolve("worldgen-plan.json"))));
            try(var bytes=WorldgenSurvey.class.getResourceAsStream("WorldgenSurvey.class")){
                require(bytes!=null,"Actual loaded helper bytes unavailable");
                report.addProperty("qa_class_sha256",hash(bytes.readAllBytes()));
            }
            report.add("selected_packs",GSON.toJsonTree(server.getPackRepository().getSelectedIds()));
            report.add("registry",registry(server));report.add("chunks",chunks);report.add("scans",scans);
            report.add("observed_tick_nanoseconds",tickSamples);
            report.addProperty("entrances_and_visual_terrain_cuts","REQUIRES ACTUAL VISUAL REVIEW");
            if(phase.equals("scan"))prepareScans(level);
            else{
                JsonArray points=plan.getAsJsonArray("chunks");
                require(points!=null&&points.size()>0&&points.size()<=384,"Bounded identical chunk workload is required");
                Set<String> unique=new HashSet<>();
                for(JsonElement element:points){
                    JsonArray point=element.getAsJsonArray();require(point.size()==2,"Invalid chunk coordinate");
                    int x=point.get(0).getAsInt(),z=point.get(1).getAsInt();
                    require(Math.abs((long)x)<1000000&&Math.abs((long)z)<1000000&&unique.add(x+","+z),"Invalid/duplicate chunk");
                    work.add(()->observeChunk(level,x,z));
                }
            }
            require(work.size()<=512,"Work plan exceeds its operation bound");
            deadline=System.nanoTime()+600_000_000_000L;active=true;flush();
        }catch(Exception error){failed=true;System.err.println("AWFT_WORLDGEN_QA_REFUSED "+error);server.halt(false);}
    }

    private JsonArray registry(MinecraftServer server){
        Registry<StructureSet> sets=server.registryAccess().registryOrThrow(Registries.STRUCTURE_SET);
        Registry<Structure> structures=server.registryAccess().registryOrThrow(Registries.STRUCTURE);
        RegistryOps<JsonElement> ops=RegistryOps.create(JsonOps.INSTANCE,server.registryAccess());
        JsonArray rows=new JsonArray();
        for(var key:new TreeSet<>(sets.keySet())){
            StructureSet value=sets.get(key);JsonObject row=new JsonObject();row.addProperty("id",key.toString());
            row.add("encoded",StructureSet.DIRECT_CODEC.encodeStart(ops,value).getOrThrow());
            JsonArray members=new JsonArray();
            for(var entry:value.structures()){
                Structure structure=entry.structure().value();JsonObject member=new JsonObject();
                member.addProperty("id",Objects.requireNonNull(structures.getKey(structure)).toString());
                JsonArray biomes=new JsonArray();structure.biomes().stream()
                    .map(h->h.unwrapKey().orElseThrow().location().toString()).sorted().forEach(biomes::add);
                member.add("biomes",biomes);members.add(member);
            }
            row.add("members",members);rows.add(row);
        }
        return rows;
    }

    private void prepareScans(ServerLevel level){
        JsonArray windows=plan.getAsJsonArray("windows"),names=plan.getAsJsonArray("structure_sets");
        require(windows!=null&&windows.size()>0&&windows.size()<=8,"At most eight fixed windows");
        require(names!=null&&names.size()>0&&names.size()<=16,"At most sixteen named structure sets");
        Registry<StructureSet> sets=level.registryAccess().registryOrThrow(Registries.STRUCTURE_SET);
        for(JsonElement name:names){
            String id=name.getAsString();
            var key=net.minecraft.resources.ResourceLocation.parse(id);StructureSet set=sets.get(key);
            require(set!=null,"Requested structure set missing: "+id);
            require(set.placement() instanceof RandomSpreadStructurePlacement,"Custom placements require separate native sampling: "+id);
            for(JsonElement window:windows){
                JsonArray w=window.getAsJsonArray();require(w.size()==3,"Window must be x,z,width");
                int x=w.get(0).getAsInt(),z=w.get(1).getAsInt(),width=w.get(2).getAsInt();
                require(width>=32&&width<=512&&Math.abs((long)x)<1000000&&Math.abs((long)z)<1000000,"Unbounded native window");
                work.add(()->scan(level,id,set,x,z,width));
            }
        }
    }

    private void scan(ServerLevel level,String id,StructureSet set,int x0,int z0,int width){
        RandomSpreadStructurePlacement placement=(RandomSpreadStructurePlacement)set.placement();
        require(placement.spacing()>=32,"This scan excludes dense placements");
        var source=level.getChunkSource();var generator=source.getGenerator();var state=source.getGeneratorState();
        Registry<Structure> structures=level.registryAccess().registryOrThrow(Registries.STRUCTURE);
        JsonObject row=new JsonObject();row.addProperty("set",id);row.add("window",ints(x0,z0,width));
        JsonArray points=new JsonArray();row.add("candidates",points);long began=System.nanoTime();
        for(int rx=Math.floorDiv(x0,placement.spacing());rx<=Math.floorDiv(x0+width-1,placement.spacing());rx++){
            for(int rz=Math.floorDiv(z0,placement.spacing());rz<=Math.floorDiv(z0+width-1,placement.spacing());rz++){
                ChunkPos pos=placement.getPotentialStructureChunk(level.getSeed(),rx*placement.spacing(),rz*placement.spacing());
                if(pos.x<x0||pos.x>=x0+width||pos.z<z0||pos.z>=z0+width)continue;
                JsonObject point=new JsonObject();point.add("chunk",ints(pos.x,pos.z));
                require(System.nanoTime()<deadline,"600-second phase budget reached during scan");
                boolean admitted=placement.isStructureChunk(state,pos.x,pos.z);
                point.addProperty("placement_admitted_including_native_exclusions",admitted);
                JsonArray feasible=new JsonArray();point.add("native_feasible_members_not_placed",feasible);
                if(admitted)for(var member:set.structures()){
                    Structure structure=member.structure().value();
                    Structure.GenerationContext context=new Structure.GenerationContext(level.registryAccess(),generator,
                        generator.getBiomeSource(),source.randomState(),level.getStructureManager(),level.getSeed(),pos,level,structure.biomes()::contains);
                    if(structure.findValidGenerationPoint(context).isPresent())feasible.add(structures.getKey(structure).toString());
                }
                int bx=pos.getMiddleBlockX(),bz=pos.getMiddleBlockZ();
                int y=generator.getBaseHeight(bx,bz,Heightmap.Types.WORLD_SURFACE_WG,level,source.randomState());
                point.addProperty("base_height",y);
                var biome=generator.getBiomeSource().getNoiseBiome(bx>>2,(y-1)>>2,bz>>2,source.randomState().sampler());
                point.addProperty("noise_biome",biome.unwrapKey().orElseThrow().location().toString());points.add(point);
                require(points.size()<=512,"Candidate bound exceeded");
            }
        }
        row.addProperty("scan_nanoseconds",System.nanoTime()-began);scans.add(row);
    }

    private void observeChunk(ServerLevel level,int x,int z){
        try{
            boolean loaded=level.getChunkSource().getChunkNow(x,z)!=null;long start=System.nanoTime();
            ChunkAccess chunk=level.getChunkSource().getChunk(x,z,ChunkStatus.FULL,true);
            long duration=System.nanoTime()-start;require(chunk!=null,"Native full chunk unavailable");
            JsonObject row=new JsonObject();row.add("chunk",ints(x,z));row.addProperty("already_loaded",loaded);
            row.addProperty("full_chunk_wall_nanoseconds",duration);
            JsonArray surface=new JsonArray(),floor=new JsonArray();Map<String,Integer> biomes=new TreeMap<>();
            MessageDigest hash=MessageDigest.getInstance("SHA-256");
            for(int lx=0;lx<16;lx++)for(int lz=0;lz<16;lz++){
                surface.add(chunk.getHeight(Heightmap.Types.WORLD_SURFACE,lx,lz));
                floor.add(chunk.getHeight(Heightmap.Types.OCEAN_FLOOR,lx,lz));
                for(int y=level.getMinBuildHeight();y<level.getMaxBuildHeight();y++){
                    hash.update(stateBytes.computeIfAbsent(chunk.getBlockState(new BlockPos((x<<4)+lx,y,(z<<4)+lz)),
                        s->s.toString().getBytes(StandardCharsets.UTF_8)));hash.update((byte)0);
                }
                int y=chunk.getHeight(Heightmap.Types.WORLD_SURFACE,lx,lz);
                String biome=chunk.getNoiseBiome(lx>>2,y>>2,lz>>2).unwrapKey().orElseThrow().location().toString();
                biomes.merge(biome,1,Integer::sum);
            }
            row.add("world_surface",surface);row.add("ocean_floor",floor);row.add("surface_biomes",GSON.toJsonTree(biomes));
            row.addProperty("block_states_sha256",HexFormat.of().formatHex(hash.digest()));
            JsonArray starts=new JsonArray();Registry<Structure> registry=level.registryAccess().registryOrThrow(Registries.STRUCTURE);
            for(var entry:chunk.getAllStarts().entrySet())if(entry.getValue().isValid()){
                StructureStart value=entry.getValue();JsonObject structure=new JsonObject();
                structure.addProperty("id",registry.getKey(entry.getKey()).toString());structure.add("box",box(value.getBoundingBox()));
                structure.add("start_chunk",ints(value.getChunkPos().x,value.getChunkPos().z));
                JsonArray pieces=new JsonArray();for(var piece:value.getPieces())pieces.add(box(piece.getBoundingBox()));
                structure.add("piece_boxes",pieces);starts.add(structure);
            }
            row.add("actual_saved_starts",starts);chunks.add(row);
            row.addProperty("observation_processing_nanoseconds",System.nanoTime()-start-duration);
        }catch(Exception error){throw new IllegalStateException(error);}
    }

    private void pre(ServerTickEvent.Pre event){if(active)tickStart=System.nanoTime();}
    private void post(ServerTickEvent.Post event){
        if(!active||failed)return;
        MinecraftServer server=event.getServer();
        try{
            require(server.getPlayerList().getPlayerCount()==0,"Player arrival stops this private test");
            require(plan.get("lease_expires_at_epoch_ms").getAsLong()>System.currentTimeMillis(),"Master test lease expired");
            require(System.nanoTime()<deadline,"600-second phase budget reached");
            if(index<work.size()){work.get(index++).run();flush();}
            else if(++idleTicks>=40){
                report.addProperty("status","OBSERVATIONS_COMPLETE_NORMAL_STOP_AND_RESTART_STILL_REQUIRED");
                report.addProperty("completed_operations",index);flush();active=false;
                System.out.println("AWFT_WORLDGEN_QA_COMPLETE "+output.getFileName());
            }
            // Include this helper's work, and report its processing cost
            // separately. A pre-work timestamp would hide generation spikes.
            if(tickStart>0&&ticks++<8192)tickSamples.add(System.nanoTime()-tickStart);
        }catch(Exception error){
            failed=true;active=false;report.addProperty("status","FAILED_PRESERVE_WORLD_AND_RECEIPT");
            report.addProperty("error",error.toString());try{flush();}catch(Exception ignored){}
            System.err.println("AWFT_WORLDGEN_QA_FAILED "+error);server.halt(false);
        }
    }
    private void flush()throws Exception{
        byte[] raw=(GSON.toJson(report)+"\n").getBytes(StandardCharsets.UTF_8);
        require(raw.length<=8*1024*1024,"Native receipt exceeds its allocation bound");
        Path temporary=output.resolveSibling(output.getFileName()+".tmp");
        Files.write(temporary,raw);Files.move(temporary,output,StandardCopyOption.REPLACE_EXISTING);
    }
}
