"""Additive original R2 from the exact frozen reviewed R1; never active source."""
from pathlib import Path
import hashlib

ROOT=Path(__file__).resolve().parent
old=ROOT.parent/'native-relocation-pippin-r1/NativeRelocationSupport.java'
text=old.read_text(encoding='utf8')
assert hashlib.sha256(old.read_bytes()).hexdigest()=='a08ed778ac5692f401e9691f3d49560ed2cb21a532f5785112e5723e7500eee7'
def replace(a,b):
    global text
    assert text.count(a)==1,a[:120]
    text=text.replace(a,b)
def span(a,b,new):
    global text
    first=text.index(a);last=text.index(b,first);text=text[:first]+new+text[last:]

replace('import java.util.*;','import java.util.*;\nimport java.util.concurrent.CompletableFuture;\nimport net.minecraft.server.level.TicketType;\nimport net.minecraft.world.level.block.entity.LecternBlockEntity;')
span('    private static final BlockPos LOW=', '    private static final String BASELINE=', '''    private BlockPos LOW,HIGH,DEST;
    private int dx,dy,dz,sourceCount,objectCount,supportCount;
    private String capsuleId;
    private JsonObject catalogRow,catalog;
    private static final String CATALOG_SHA="db5e0fa730575ad9b0fd166dd4d52273a5105832d66636d1ca3098693199adf7";
    private static final TicketType<ChunkPos> TICKET=TicketType.create("awft_relocation",Comparator.comparingLong(ChunkPos::toLong));
    private final Set<ChunkPos> chunks=new LinkedHashSet<>(),tickets=new LinkedHashSet<>(),centers=new LinkedHashSet<>();
    private final List<CompletableFuture<?>> pending=new ArrayList<>();
    private NativeTreePatchReadiness persisted;
    private String phase;
    private int loadingTicks;
    private long syncStarted;
''')
span('    private static final String ORIGINAL_SOURCE=', '    private static final String EASTERN_LAYOUT=', '')
replace('"net.minecraft.world.level.block.entity.SmokerBlockEntity","net.minecraft.world.level.block.entity.SignBlockEntity");','''"net.minecraft.world.level.block.entity.SmokerBlockEntity","net.minecraft.world.level.block.entity.SignBlockEntity",
        "net.minecraft.world.level.block.entity.BarrelBlockEntity","net.minecraft.world.level.block.entity.ChiseledBookShelfBlockEntity",
        "net.minecraft.world.level.block.entity.LecternBlockEntity","net.minecraft.world.level.block.entity.BedBlockEntity",
        "net.mehvahdjukaar.supplementaries.common.block.tiles.BookPileBlockTile");''')
replace('perform(c.getSource().getServer(),op,StringArgumentType.getString(c,"bundle"),StringArgumentType.getString(c,"sha256"));return busy()?0:1;','begin(c.getSource().getServer(),op,StringArgumentType.getString(c,"bundle"),StringArgumentType.getString(c,"sha256"));return 1;')
span('    /** Never repeats a world operation.', '    private static String sha(', '''    /** Read persisted data first; then normal bounded native loading, never a managed wait. */
    public void tick(MinecraftServer server){
        if(!server.isSameThread())return;
        if(running)try{
            if(!server.getPlayerList().getPlayers().isEmpty()||lease==null||!lease.valid())throw new IllegalStateException("Actual player/lease custody changed; no move");
            if(System.nanoTime()-started>180_000_000_000L)throw new IllegalStateException("Finite relocation readiness expired");
            checkpoint();
            if(phase.equals("persisted")){
                if(!persisted.poll())return;
                report.put("current_persisted_before_tickets",persisted.report());
                for(ChunkPos c:centers){tickets.add(c);ticket(c,true);}
                phase="load";return;
            }
            if(phase.equals("load")){
                if(++loadingTicks>600)throw new IllegalStateException("Finite FULL/entity readiness timeout");
                if(pending.isEmpty()){
                    for(ChunkPos c:chunks)if(!level.getChunkSource().hasChunk(c.x,c.z))return;
                    for(ChunkPos c:chunks)pending.add(((worldfortwo.bridge.mixin.ChunkCacheAccess)(Object)level.getChunkSource()).awftQueueChunk(c.x,c.z,ChunkStatus.FULL,false));
                }
                for(var f:pending){if(!f.isDone())return;Object v=f.getNow(null);if(!(v instanceof net.minecraft.server.level.ChunkResult<?> r)||r.orElse(null)==null)throw new IllegalStateException("Native existing FULL chunk unavailable");}
                if(!loaded())return;
                pending.clear();phase="atomic";syncStarted=System.nanoTime();ready(server);atomic(server);return;
            }
        }catch(Exception|LinkageError error){failed(error);return;}
        if(!running&&busy()&&cleanupAttempts<3&&++cleanupDelay>=20){cleanupDelay=0;retryCleanup();}
    }
    private void ticket(ChunkPos c,boolean add)throws Exception{
        level.getChunkSource().getClass().getMethod(add?"addRegionTicket":"removeRegionTicket",TicketType.class,ChunkPos.class,int.class,Object.class,boolean.class).invoke(level.getChunkSource(),TICKET,c,2,c,true);
    }
    private boolean loaded(){for(ChunkPos c:chunks){var actual=level.getChunkSource().getChunkNow(c.x,c.z);if(actual==null||!actual.getPersistedStatus().isOrAfter(ChunkStatus.FULL)||!level.areEntitiesLoaded(c.toLong()))return false;}return true;}
''')
replace('    private static BlockPos translated(BlockPos p){return p.offset(-13,0,0);}','    private BlockPos translated(BlockPos p){return p.offset(dx,dy,dz);}')
replace('!request.get("format").getAsString().equals("awft-native-pippin-relocation:1")','!request.get("format").getAsString().equals("awft-native-approved-capsule-relocation:2")')
replace('!classHash(Ledger.class).equals(request.get("ledger_class_sha256").getAsString())','!classHash(Ledger.class).equals(request.get("ledger_class_sha256").getAsString())||!classHash(Capsules.class).equals(request.get("catalog_class_sha256").getAsString())')
replace('contains(new JsonPrimitive("pippin-native-relocation-prototype"))','contains(new JsonPrimitive("approved-north-bank-city-rebuild"))')
span('        if(!request.get("baseline_capture_backup_sha256")', '        ledger=server.getWorldPath', '''        if(!request.get("baseline_capture_backup_sha256").getAsString().equals(BASELINE)||!request.getAsJsonObject("catalog").get("sha256").getAsString().equals(CATALOG_SHA))throw new IllegalStateException("Only the exact sealed approved room catalogue");
        catalog=ref("catalog",2*1024*1024);capsuleId=request.get("capsule_id").getAsString();catalogRow=Capsules.select(catalog,capsuleId);
        int[] a=Capsules.box(catalogRow.get("source_bounds_xyz")),b=Capsules.box(catalogRow.get("destination_bounds_xyz"));
        LOW=new BlockPos(a[0],a[1],a[2]);HIGH=new BlockPos(a[3],a[4],a[5]);DEST=new BlockPos(b[0],b[1],b[2]);dx=b[0]-a[0];dy=b[1]-a[1];dz=b[2]-a[2];
        sourceCount=Capsules.integer(catalogRow.get("cells"));objectCount=Capsules.integer(catalogRow.get("objects"));supportCount=Capsules.integer(catalogRow.get("support_cells"));
        for(String k:List.of("original_source","original_destination")){String name=k.equals("original_source")?"source_original":"destination_original";if(!request.getAsJsonObject(k).equals(catalogRow.getAsJsonObject(name)))throw new IllegalStateException("Selected original capture reference differs");}
        JsonObject original=ref("original_source",131072),prior=ref("original_destination",131072),after=ref("source_geometry",131072),dest=ref("destination_geometry",131072),support=ref("destination_supports",131072);
        Map<BlockPos,BlockState> originalStates=plan(original,sourceCount),priorStates=plan(prior,sourceCount);source.putAll(plan(after,sourceCount));destination.putAll(plan(dest,sourceCount));supports.putAll(plan(support,supportCount));
        if(!after.get("backup_sha256").equals(request.get("backup_sha256"))||!dest.get("backup_sha256").equals(request.get("backup_sha256"))||!support.get("backup_sha256").equals(request.get("backup_sha256")))throw new IllegalStateException("Fresh current-checkpoint proofs required");
        Map<BlockPos,BlockState> preparations=new HashMap<>();for(JsonElement e:catalogRow.getAsJsonArray("source_cover_preparations")){JsonObject r=e.getAsJsonObject();preparations.put(pos(r.get("position")),parse(r.get("before").getAsString()));}
        for(BlockPos q:BlockPos.betweenClosed(LOW,HIGH)){
            BlockPos p=q.immutable(),d=translated(p);BlockState before=originalStates.get(p);
            if(before==null||source.get(p)==null||destination.get(d)==null||!destination.get(d).isAir()||!source.get(p).equals(preparations.containsKey(p)?parse("minecraft:air"):before))throw new IllegalStateException("Only exact source capsule/approved cover and completely AIR destination");
            if(preparations.containsKey(p)&&!preparations.get(p).equals(before))throw new IllegalStateException("Original ordinary cover differs");
        }
        if(after.getAsJsonArray("block_entities").size()!=objectCount||dest.getAsJsonArray("block_entities").size()!=0||support.getAsJsonArray("block_entities").size()!=0)throw new IllegalStateException("Exact complete original object custody required");
        Map<BlockPos,CompoundTag> originalTags=new HashMap<>();for(JsonElement e:original.getAsJsonArray("block_entities")){JsonObject r=e.getAsJsonObject();if(originalTags.put(pos(r.get("pos")),TagParser.parseTag(r.get("nbt").getAsString()))!=null)throw new IllegalStateException("Duplicate original tag");}
        for(JsonElement e:after.getAsJsonArray("block_entities")){JsonObject r=e.getAsJsonObject();BlockPos p=pos(r.get("pos"));if(!source.containsKey(p)||expectedTags.put(p,TagParser.parseTag(r.get("nbt").getAsString()))!=null)throw new IllegalStateException("BE capture coordinates differ");}
        if(!expectedTags.equals(originalTags))throw new IllegalStateException("Every full typed tag remains unchanged");
        for(JsonElement e:request.getAsJsonArray("BE_class_pins")){JsonObject r=e.getAsJsonObject();BlockPos p=pos(r.get("source_position"));if(!expectedTags.containsKey(p)||!CLASSES.contains(r.get("class").getAsString())||classPins.put(p,r)!=null)throw new IllegalStateException("Unexpected/missing native BE class pin");}
        if(classPins.size()!=objectCount)throw new IllegalStateException("Complete native class custody required");
        for(BlockPos p:supports.keySet())if(p.getY()!=b[1]-1||p.getX()<b[0]||p.getX()>b[3]||p.getZ()<b[2]||p.getZ()>b[5])throw new IllegalStateException("Foreign support plane");
        if(!action.equals("inspect-moved")){proof("source_native_verify","source_geometry",sourceCount);proof("destination_native_verify","destination_geometry",sourceCount);proof("supports_native_verify","destination_supports",supportCount);}
        String stable=sha((home.toRealPath()+"|"+BASELINE+"|"+Capsules.salt(capsuleId,dx,dy,dz)).getBytes(StandardCharsets.UTF_8));
        if(!stable.equals(request.get("transaction_id").getAsString()))throw new IllegalStateException("Stable once-only transaction identity differs");
''')
replace('report.put("transaction_id",stable);','report.put("capsule_id",capsuleId);report.put("transaction_id",stable);')
span('        for(int cx=75;cx<=78;', '    private void states(', '''        if(!loaded())throw new IllegalStateException("Actual retained FULL/entity-loaded capsule neighbors required");
        if(System.nanoTime()-syncStarted>2_000_000_000L)throw new IllegalStateException("Bounded synchronous native transaction expired");
    }
    private void dependencies()throws Exception{
        for(JsonElement e:catalogRow.getAsJsonArray("dependencies")){
            String id=e.getAsString();JsonObject dep=Capsules.select(catalog,id);int[] a=Capsules.box(dep.get("source_bounds_xyz")),b=Capsules.box(dep.get("destination_bounds_xyz"));
            String key=sha((home.toRealPath()+"|"+BASELINE+"|"+Capsules.salt(id,b[0]-a[0],b[1]-a[1],b[2]-a[2])).getBytes(StandardCharsets.UTF_8));Path path=level.getServer().getWorldPath(LevelResource.ROOT).toRealPath().resolve("data/awft-relocations/"+key);
            byte[] raw=bytes(path.resolve("completed.json"),1048576);if(!new String(bytes(path.resolve("completed.json.sha256"),128),StandardCharsets.UTF_8).trim().equals(sha(raw)))throw new IllegalStateException("Durable dependency completion missing/changed");
            JsonObject done=JsonParser.parseString(new String(raw,StandardCharsets.UTF_8)).getAsJsonObject();if(!done.get("transaction_id").getAsString().equals(key)||!done.get("intent_sha256").getAsString().equals(sha(bytes(path.resolve("intent.json"),1048576))))throw new IllegalStateException("Foreign dependency completion");
        }
    }
''')
replace('b=a.move(-13,0,0);','b=a.move(dx,dy,dz);')
# Native complete bed-pair closure is required in addition to original doors.
replace('            for(var shape:List.of(s.getShape(level,p),s.getCollisionShape(level,p)))', '''            if(blockId.startsWith("minecraft:")&&blockId.endsWith("_bed")){
                var part=s.getBlock().getStateDefinition().getProperty("part");var facing=s.getBlock().getStateDefinition().getProperty("facing");
                String v=s.getValue(part).toString().toLowerCase(Locale.ROOT),f=s.getValue(facing).toString().toLowerCase(Locale.ROOT);Direction d=Direction.byName(f);if(d==null)throw new IllegalStateException("Unknown bed direction");
                BlockPos q=p.relative(v.equals("head")?d.getOpposite():d);BlockState pair=source.get(q);if(pair==null||pair.getBlock()!=s.getBlock()||pair.getValue(part).equals(s.getValue(part))||!pair.getValue(facing).equals(s.getValue(facing)))throw new IllegalStateException("A genuine bed pair escapes the capsule");
            }
            for(var shape:List.of(s.getShape(level,p),s.getCollisionShape(level,p)))''')
replace('else if(!Set.of("net.minecraft.world.level.block.entity.SignBlockEntity","net.mehvahdjukaar.supplementaries.common.block.tiles.GlobeBlockTile").contains(be.getClass().getName()))throw new IllegalStateException("Non-Container role is not reviewed");', '''else if(be instanceof LecternBlockEntity lectern){JsonArray books=new JsonArray();books.add(stack(lectern.getBook()));r.add("additional_native_stacks",books);}
            else if(!Set.of("net.minecraft.world.level.block.entity.SignBlockEntity","net.mehvahdjukaar.supplementaries.common.block.tiles.GlobeBlockTile","net.minecraft.world.level.block.entity.BedBlockEntity").contains(be.getClass().getName()))throw new IllegalStateException("Non-Container role is not reviewed");''')
replace('if(before.size()!=7||after.size()!=7)throw new IllegalStateException("Seven native instances required");','if(before.size()!=objectCount||after.size()!=objectCount)throw new IllegalStateException("Exact complete native instances required");')
assert text.count('for(int i=0;i<7;i++){')==2
text=text.replace('for(int i=0;i<7;i++){','for(int i=0;i<objectCount;i++){')
replace('            if(a.get("is_Container").getAsBoolean()){','''            if(a.has("additional_native_stacks")!=b.has("additional_native_stacks")||a.has("additional_native_stacks")&&!a.get("additional_native_stacks").equals(b.get("additional_native_stacks")))throw new IllegalStateException("Native non-Container book stack/components changed");
            if(a.get("is_Container").getAsBoolean()){''')
# Separate asynchronous read/load admission from the original atomic body.
first=text.index('            if(action.equals("inspect-moved")){',text.index('    private void perform('))
last=text.index('        }catch(Exception|LinkageError error){',first)
atomic=text[first:last]
atomic=atomic.replace('result>320','result>sourceCount').replace('for(int i=0;i<7;i++)','for(int i=0;i<objectCount;i++)')
atomic=atomic.replace('String command="clone 1236 64 -1194 1243 67 -1185 1223 64 -1194 replace move";', 'String command="clone "+LOW.getX()+" "+LOW.getY()+" "+LOW.getZ()+" "+HIGH.getX()+" "+HIGH.getY()+" "+HIGH.getZ()+" "+DEST.getX()+" "+DEST.getY()+" "+DEST.getZ()+" replace move";')
atomic=atomic.replace('states(source);states(destination);states(supports);spatialAndModel();JsonArray before=', 'dependencies();states(source);states(destination);states(supports);spatialAndModel();JsonArray before=')
atomic=atomic.replace('intent.addProperty("format","awft-native-pippin-clone-intent:1");','intent.addProperty("format","awft-native-approved-clone-intent:2");intent.addProperty("capsule_id",capsuleId);intent.addProperty("catalog_sha256",CATALOG_SHA);')
atomic=atomic.replace('JsonArray after=snapshots(true);','if(!level.getEntities((Entity)null,new AABB(LOW.getX(),LOW.getY(),LOW.getZ(),HIGH.getX()+1,HIGH.getY()+1,HIGH.getZ()+1).inflate(.25)).isEmpty()||!level.getEntities((Entity)null,new AABB(LOW.getX(),LOW.getY(),LOW.getZ(),HIGH.getX()+1,HIGH.getY()+1,HIGH.getZ()+1).move(dx,dy,dz).inflate(.25)).isEmpty())throw new IllegalStateException("Unexpected actual entity after clone; quarantine without deleting it");JsonArray after=snapshots(true);')
atomic=atomic.replace('seven native object contents conserved','all selected native object contents conserved')
start=text.index('    private void perform(');end=text.index('    private void finish(',start)
text=text[:start]+'''    private void begin(MinecraftServer server,String op,String bundle,String expected)throws Exception{
        action=op;running=true;admitted=terminalPending=false;cleanupAttempts=cleanupDelay=loadingTicks=0;intentAttempted=intentWritten=cloneInvoked=quarantined=false;started=System.nanoTime();report.clear();report.put("operation",op);report.put("started",Instant.now().toString());report.put("pack_sha256","unadmitted");report.put("request_sha256",expected.matches("[a-f0-9]{64}")?expected:"invalid");
        chunks.clear();centers.clear();pending.clear();persisted=null;
        try{admit(server,bundle,expected);report.put("pack_sha256",request.get("pack_sha256").getAsString());
            for(BlockPos p:List.of(LOW,HIGH,DEST,translated(HIGH)))centers.add(new ChunkPos(p));
            for(ChunkPos c:centers)for(int x=-1;x<=1;x++)for(int z=-1;z<=1;z++)chunks.add(new ChunkPos(c.x+x,c.z+z));
            if(chunks.size()>64||centers.size()>8)throw new IllegalStateException("Finite capsule neighbors exceeded");
            persisted=new NativeTreePatchReadiness(level,centers);phase="persisted";
        }catch(Exception|LinkageError error){failed(error);throw error;}
    }
    private void atomic(MinecraftServer server)throws Exception{
'''+atomic+'''    }
    private void failed(Throwable error){
        if(intentAttempted||cloneInvoked){quarantined=true;try{JsonObject q=new JsonObject();q.addProperty("request_sha256",requestSha);q.addProperty("at",Instant.now().toString());q.addProperty("clone_invoked",cloneInvoked);q.addProperty("error_class",error.getClass().getName());q.addProperty("reason",String.valueOf(error.getMessage()));durable(ledger.resolve("quarantine.json"),q);}catch(Exception|LinkageError secondary){report.put("quarantine_publication_failed",secondary.getClass().getName());}}
        report.put("error_class",error.getClass().getName());report.put("private_error",String.valueOf(error.getMessage()));finish("refused or uncertain partial; preserve exact world and durable intent; no replay",true);
    }
'''+text[end:]
replace('cleanupAttempts++;boolean clean=true;if(lease!=null)try{','''cleanupAttempts++;boolean clean=true;
        for(var it=tickets.iterator();it.hasNext();){ChunkPos c=it.next();try{ticket(c,false);it.remove();}catch(Exception error){clean=false;report.put("ticket_cleanup_error",error.getClass().getName());}}
        pending.removeIf(CompletableFuture::isDone);boolean drained=pending.isEmpty()&&(persisted==null||persisted.drained());
        if(!tickets.isEmpty()||!drained)clean=false;
        if(clean&&lease!=null)try{''')
replace('report.put("owned_chunk_tickets",0);report.put("generation_requests",0);report.put("pending_owned_futures",0);','report.put("owned_chunk_tickets",tickets.size());report.put("generation_requests",0);report.put("pending_owned_futures",pending.size()+(persisted==null?0:persisted.pending()));report.put("pending_shared_chunk_futures",pending.size());')
# Pure production parser fixture runs without initializing Minecraft classes.
at=text.index('    /** Pure finite durable-file primitive')
text=text[:at]+'''    static final class Capsules {
        static int integer(JsonElement value){return value.getAsBigDecimal().intValueExact();}
        static int[] box(JsonElement value){JsonArray a=value.getAsJsonArray();if(a.size()!=6)throw new IllegalStateException("Exact box");int[] b=new int[6];for(int i=0;i<6;i++)b[i]=integer(a.get(i));
            for(int i=0;i<3;i++)if(b[i]>b[i+3]||b[i+3]-b[i]>31)throw new IllegalStateException("Finite closed bounds");return b;}
        static String salt(String id,int x,int y,int z){return id.equals("eastern22/pippins-net:room:0")?"PIPPIN320|-13,0,0":id+"|"+x+","+y+","+z;}
        static JsonObject select(JsonObject catalog,String id){
            if(!catalog.get("format").getAsString().equals("awft-approved-eastern-relocation-catalog:2")||!catalog.get("eastern_layout_sha256").getAsString().equals("6f24640d9efefae3340be80d34bcd0e4788f2ded695aefe03d1d6815761a12a4")||catalog.getAsJsonArray("capsules").size()!=93)throw new IllegalStateException("Exact approved finite catalogue");
            JsonObject found=null;for(JsonElement e:catalog.getAsJsonArray("capsules")){JsonObject r=e.getAsJsonObject();if(r.get("id").getAsString().equals(id)){if(found!=null)throw new IllegalStateException("Duplicate capsule");found=r;}}
            if(found==null||!found.get("supported").getAsBoolean())throw new IllegalStateException("Unknown/held capsule, no authority inferred");
            int[] a=box(found.get("source_bounds_xyz")),b=box(found.get("destination_bounds_xyz"));JsonArray d=found.getAsJsonArray("translation_xyz");if(d.size()!=3)throw new IllegalStateException("Exact translation");boolean same=true;
            for(int i=0;i<3;i++){int delta=integer(d.get(i));same&=delta==0;if(b[i]-a[i]!=delta||b[i+3]-a[i+3]!=delta)throw new IllegalStateException("Cardinal unchanged box required");}
            int count=Math.multiplyExact(Math.multiplyExact(a[3]-a[0]+1,a[4]-a[1]+1),a[5]-a[2]+1),objects=integer(found.get("objects"));
            if(same||a[4]-a[1]!=3||count<1||count>512||count!=integer(found.get("cells"))||objects<1||objects>32||integer(found.get("support_cells"))!=(b[3]-b[0]+1)*(b[5]-b[2]+1))throw new IllegalStateException("Identity/resized/oversized/incomplete capsule refused");return found;
        }
    }
'''+text[at:]
assert 'perform(' not in text
(ROOT/'NativeRelocationSupport.java').write_text(text,encoding='utf8',newline='\n')
