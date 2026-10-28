"""Original source-only dense native-tree batch proposal; never operate a world.

The immutable legacy controller is copied only as an owned implementation base.
Native growth remains the ordinary pinned sapling/bonemeal call, one root once.
"""
from pathlib import Path
import difflib
import json

from control_room.common import UserError,digest,utcnow
from tools.playtest import guard

BASES={
    'NativeTreeGrowthSupport':'cce647921a1a6bb07751e8883556ec71804306b053b6f9ba0ae9936832ffff77',
    'TreeGrowthScope':'eeacf850d6cb4eb43732b83c847143819df6953b1ba89ad2aaf842034dc69ed1',
    'TreeBeeAudit':'12dac3641b71c4af83a14183f3a0ec231eba244b5683f2f172b77f3380848c87',
}


def once(text,old,new):
    if text.count(old)!=1:raise UserError('Frozen native tree boundary differs: '+old[:90])
    return text.replace(old,new)


PATCH_FIELDS='''
    private final List<JsonObject> patchRoots=new ArrayList<>();
    private final List<Map<String,Object>> rootOutcomes=new ArrayList<>();
    private final Set<String> patchIds=new HashSet<>();
    private final Set<BlockPos> heldRoots=new HashSet<>(),approvedFoliage=new HashSet<>();
    private final Set<String> leafIds=new HashSet<>();
    private final Set<Long> eligibleColumns=new HashSet<>();
    private int rootIndex,captureCursor;
    private String rootId,currentSaplingId,requestSha,capturedSha,capturedName;
    private JsonObject rootPlan;
    private Path rootIntent;
    private boolean anyMutated;
    private long archiveBytes;
    private NativeTreePatchReadiness savedReadiness;
    private static final int MAX_ROOTS=32;
    private static final long MAX_ARCHIVE_BYTES=576L*1024*1024;
'''

PATCH_ADMISSION='''        if(quarantineLatched||Files.exists(journal.resolve("tree-growth-quarantine.json")))throw new IllegalStateException("Existing native tree quarantine requires exact review; never retry held roots");
        if(Files.getFileStore(home).getUsableSpace()<32212254720L+640L*1024*1024
            ||Files.getFileStore(Path.of("C:/")).getUsableSpace()<32212254720L+32L*1024*1024)
            throw new IllegalStateException("Both independent30GiB reserves plus the bounded native patch allocation are required");
        for(var pin:Map.of("native_guard_sha256","mixin/NativeTreeGrowthGuardMixin.class",
                "bee_audit_sha256","TreeBeeAudit.class","bee_facts_sha256","BeeNestFacts.class",
                "pre_mutation_field_check_sha256","PreMutationFieldCheck.class","native_readiness_sha256","NativeTreePatchReadiness.class").entrySet())
            resource(NativeTreePatchSupport.class,pin.getValue(),request.get(pin.getKey()).getAsString());
        JsonObject ready=read(ref("patch_authority"),128*1024);
        if(!ready.get("format").getAsString().equals("awft-reviewed-native-tree-patch:1")
            ||!ready.get("patch_plan_sha256").getAsString().equals(planSha)
            ||!ready.get("checkpoint_sha256").getAsString().equals(request.get("checkpoint_sha256").getAsString())
            ||!ready.get("native_capture_each_root").getAsBoolean()
            ||!ready.get("allow_only_reviewed_native_foliage_overlap").getAsBoolean()
            ||!ready.get("preserve_all_existing_trunks_BEs_and_hives").getAsBoolean()
            ||!ready.get("bare_patch_construction_clearance_reviewed").getAsBoolean())
            throw new IllegalStateException("Exact parent-reviewed bare patch/live-capture authority required; not whole-town art acceptance");
        JsonObject mask=read(ref("protection"),MAX_INPUT);
        if(!mask.get("seed").getAsString().equals(plan.get("seed").getAsString())
            ||!mask.get("world_path").getAsString().equals(plan.get("world_path").getAsString())
            ||mask.get("minimum_buffer_blocks").getAsInt()<5
            ||!mask.get("includes_latest_plaza_routes_and_walks").getAsBoolean()
            ||!mask.get("includes_current_bridge_fountain_zipline_and_north_partition").getAsBoolean())
            throw new IllegalStateException("Complete current construction/AIR/routes/flow/flight/north partition protection required");
        for(JsonElement value:mask.getAsJsonArray("columns")){
            JsonArray col=value.getAsJsonArray();if(col.size()!=2||protectedColumns.size()>=500000)throw new IllegalStateException("Finite current protection required");
            protectedColumns.add(TreeGrowthScope.column(col.get(0).getAsInt(),col.get(1).getAsInt()));
        }
        JsonObject eligibility=read(ref("eligible_land"),MAX_INPUT);
        if(!eligibility.get("format").getAsString().equals("awft-measured-south-eligible-land:1")
            ||!eligibility.get("checkpoint_sha256").getAsString().equals(request.get("checkpoint_sha256").getAsString())
            ||!eligibility.get("eastmost_north_land_edge_measured").getAsBoolean()
            ||!eligibility.get("connected_south_shore_to_cliff_foot_measured").getAsBoolean()
            ||!eligibility.get("seed").getAsString().equals(plan.get("seed").getAsString())
            ||!eligibility.get("world_path").getAsString().equals(plan.get("world_path").getAsString()))
            throw new IllegalStateException("Actual expanded connected eligible-land measurement required; rectangle/old clipped forest is not authority");
        for(JsonElement row:eligibility.getAsJsonArray("eligible_columns_xz")){
            JsonArray p=row.getAsJsonArray();if(p.size()!=2||eligibleColumns.size()>=500000)throw new IllegalStateException("Finite measured southern land required");
            eligibleColumns.add(TreeGrowthScope.column(p.get(0).getAsInt(),p.get(1).getAsInt()));
        }
        JsonObject held=read(ref("prior_root_custody"),MAX_INPUT);
        if(!held.get("format").getAsString().equals("awft-current-tree-root-custody:1")
            ||!held.get("checkpoint_sha256").getAsString().equals(request.get("checkpoint_sha256").getAsString())
            ||!held.get("all_attempted_failed_held_lost_and_successful_roots_included").getAsBoolean())
            throw new IllegalStateException("Every original attempt/hold must remain in current root custody");
        for(JsonElement value:held.getAsJsonArray("roots")){
            JsonArray p=value.getAsJsonArray();if(p.size()!=3||heldRoots.size()>=65536)throw new IllegalStateException("Finite retained root custody required");
            heldRoots.add(new BlockPos(p.get(0).getAsInt(),p.get(1).getAsInt(),p.get(2).getAsInt()));
        }
        Set<BlockPos> uniqueRoots=new HashSet<>();
        for(JsonElement value:plan.getAsJsonArray("roots")){
            JsonObject row=value.getAsJsonObject();String id=row.get("id").getAsString();JsonArray pos=row.getAsJsonArray("root");
            if(!id.matches("[a-z0-9][a-z0-9-]{0,63}")||!patchIds.add(id)||pos.size()!=3||patchRoots.size()>=MAX_ROOTS)
                throw new IllegalStateException("One finite unique 1..32-root patch required");
            BlockPos p=new BlockPos(pos.get(0).getAsInt(),pos.get(1).getAsInt(),pos.get(2).getAsInt());
            if(!uniqueRoots.add(p)||heldRoots.contains(p)||!eligibleColumns.contains(TreeGrowthScope.column(p.getX(),p.getZ()))
                ||!saplings.contains(row.get("sapling").getAsString()))throw new IllegalStateException("Unmeasured/duplicate/previously attempted root refused");
            JsonObject q=row.getAsJsonObject("qualification");
            if(!q.get("all_reachable_features_reviewed").getAsBoolean()||!q.get("derivation_sha256").getAsString().matches("[a-f0-9]{64}"))
                throw new IllegalStateException("All normal/rare/flower/root variants require sealed envelope derivation");
            int[] write=box(row.getAsJsonArray("write_bounds")),known=box(row.getAsJsonArray("known_bounds")),relative=boxRelative(q.getAsJsonArray("relative_write_bounds"));
            for(int i=0;i<6;i++){int axis=i%3,origin=axis==0?p.getX():axis==1?p.getY():p.getZ();if(write[i]!=origin+relative[i])throw new IllegalStateException("Never clip a qualified native variant envelope");}
            if(volume(known)>MAX_CELLS||volume(write)>MAX_CELLS||!inside(write,p)||p.getY()<48||p.getY()>256
                ||known[0]>write[0]-8||known[2]>write[2]-8||known[3]<write[3]+8||known[5]<write[5]+8||known[1]>write[1]-2||known[4]<write[4]+4)
                throw new IllegalStateException("Complete finite native write/read physics envelope required");
            for(int x=write[0];x<=write[3];x++)for(int z=write[2];z<=write[5];z++)
                if(protectedColumns.contains(TreeGrowthScope.column(x,z)))throw new IllegalStateException("Preserve full architecture/AIR/path/flight/flow/view masks");
            parse(row.get("expected_root").getAsString());parse(row.get("expected_soil").getAsString());
            if(!row.get("allow_native_leaf_to_leaf_only").getAsBoolean())throw new IllegalStateException("Dense patch must explicitly bind narrow native foliage overlap policy");
            JsonArray leaves=row.getAsJsonArray("native_leaf_block_ids");if(leaves.size()>32)throw new IllegalStateException("Finite reviewed native foliage identities required");
            for(JsonElement leaf:leaves){ResourceLocation key=ResourceLocation.parse(leaf.getAsString());if(!BuiltInRegistries.BLOCK.containsKey(key)
                ||!(BuiltInRegistries.BLOCK.get(key)instanceof LeavesBlock))throw new IllegalStateException("Actual reviewed LeavesBlock required");}
            patchRoots.add(row);
        }
        if(patchRoots.isEmpty())throw new IllegalStateException("An empty patch cannot claim density");
        if(mode.equals("grow")){
            JsonObject proof=read(ref("native_inspect"),2*1024*1024);Path proofPath=owned(ref("native_inspect").get("path").getAsString());
            if(!new String(bounded(proofPath.resolveSibling(proofPath.getFileName()+".complete"),128),StandardCharsets.UTF_8).strip().equals(ref("native_inspect").get("sha256").getAsString())
                ||!proof.get("operation").getAsString().equals("inspect")||proof.get("failures").getAsInt()!=0||proof.has("error")
                ||!proof.get("cleanup_passed").getAsBoolean()||proof.get("world_recovery_required").getAsBoolean()
                ||proof.get("temporary_tickets_remaining").getAsInt()!=0||proof.get("pending_shared_futures").getAsInt()!=0
                ||!proof.get("candidate").getAsString().equals(candidate)||!proof.get("bridge").getAsString().equals(bridge)
                ||!proof.get("plan_sha256").getAsString().equals(planSha)
                ||!proof.get("checkpoint_sha256").getAsString().equals(request.get("checkpoint_sha256").getAsString())
                ||!proof.get("native_class_sha256").getAsString().equals(request.get("native_class_sha256").getAsString())
                ||proof.get("root_count").getAsInt()!=patchRoots.size())throw new IllegalStateException("Genuine complete clean current-class native patch INSPECT required");
            long age=java.time.Duration.between(Instant.parse(proof.get("finished").getAsString()),Instant.now()).toSeconds();
            if(age< -30||age>1800||proof.getAsJsonArray("roots").size()!=patchRoots.size())throw new IllegalStateException("Native patch INSPECT expired or incomplete");
            Set<String> inspected=new HashSet<>();for(JsonElement value:proof.getAsJsonArray("roots")){
                JsonObject row=value.getAsJsonObject();if(!row.get("status").getAsString().equals("CURRENT_NATIVE_FIELD_CAPTURED_NO_MUTATION")
                    ||!inspected.add(row.get("root_id").getAsString()))throw new IllegalStateException("No repeated/missing/failed inspection root");
            }
            if(!inspected.equals(patchIds))throw new IllegalStateException("Native INSPECT covers different roots");
        }
        report.put("checkpoint_sha256",request.get("checkpoint_sha256").getAsString());report.put("native_class_sha256",request.get("native_class_sha256").getAsString());
        report.put("root_count",patchRoots.size());report.put("source_spacing_goal_metres",plan.get("spacing_goal_metres"));
        report.put("density_or_ecological_acceptance",false);
'''

PATCH_METHODS='''
    private static int[] boxRelative(JsonArray values){
        if(values.size()!=6)throw new IllegalStateException("Six qualified relative bounds required");int[] out=new int[6];
        for(int i=0;i<6;i++){out[i]=values.get(i).getAsInt();if(out[i]<-64||out[i]>64)throw new IllegalStateException("Finite sealed native envelope required");}
        if(out[0]>out[3]||out[1]>out[4]||out[2]>out[5])throw new IllegalStateException("Ordered qualified native envelope required");return out;
    }
    private void selectRoot()throws Exception{
        if(savedReadiness==null||!savedReadiness.ready())throw new IllegalStateException("Actual complete current persisted FULL halo proof must precede the first ticket");
        rootPlan=patchRoots.get(rootIndex);rootId=rootPlan.get("id").getAsString();currentSaplingId=rootPlan.get("sapling").getAsString();
        qualification=rootPlan.getAsJsonObject("qualification");JsonArray p=rootPlan.getAsJsonArray("root");
        root=new BlockPos(p.get(0).getAsInt(),p.get(1).getAsInt(),p.get(2).getAsInt());sapling=BuiltInRegistries.BLOCK.get(ResourceLocation.parse(currentSaplingId)).defaultBlockState();
        int[] write=box(rootPlan.getAsJsonArray("write_bounds"));knownBounds=box(rootPlan.getAsJsonArray("known_bounds"));
        writeBounds=new AABB(write[0],write[1],write[2],write[3]+1,write[4]+1,write[5]+1);
        before.clear();approvedFoliage.clear();leafIds.clear();chunks.clear();capturedSha=capturedName=null;captureCursor=0;mutated=false;rolls=successRolls=performCalls=0;
        for(JsonElement leaf:rootPlan.getAsJsonArray("native_leaf_block_ids"))leafIds.add(leaf.getAsString());
        String identity=sha((Long.toString(level.getSeed())+"|"+root.getX()+"|"+root.getY()+"|"+root.getZ()).getBytes(StandardCharsets.UTF_8));
        Path intents=journal.resolve("tree-patch-root-intents");Files.createDirectories(intents);rootIntent=intents.resolve(identity+".json");
        if(Files.exists(rootIntent,LinkOption.NOFOLLOW_LINKS))throw new IllegalStateException("A prior dense-patch root intent remains; never replay or select a new random variant");
        for(int x=knownBounds[0]>>4;x<=knownBounds[3]>>4;x++)for(int z=knownBounds[2]>>4;z<=knownBounds[5]>>4;z++)chunks.add(new ChunkPos(x,z));
        if(chunks.size()>32)throw new IllegalStateException("Per-root temporary native chunk budget exceeded");
        for(ChunkPos c:chunks){tickets.add(c);ticket(c,true);pending.add(((worldfortwo.bridge.mixin.ChunkCacheAccess)(Object)level.getChunkSource()).awftQueueChunk(c.x,c.z,ChunkStatus.FULL,false));}
        report.put("root_id",rootId);report.put("root_index",rootIndex);phase=Phase.LOAD;
    }
    private void captureRoot(long start)throws Exception{
        int width=knownBounds[3]-knownBounds[0]+1,depth=knownBounds[5]-knownBounds[2]+1,total=(int)volume(knownBounds),work=0;
        while(captureCursor<total&&work++<2048&&System.nanoTime()-start<4_000_000L){
            int cell=captureCursor++,x=knownBounds[0]+cell%width,z=knownBounds[2]+cell/width%depth,y=knownBounds[1]+cell/(width*depth);
            BlockPos p=new BlockPos(x,y,z);BlockState state=level.getBlockState(p);before.put(p,state);
            if(writeBounds.contains(x+.5,y+.5,z+.5)&&state.getBlock()instanceof LeavesBlock&&state.is(BlockTags.LEAVES)
                &&leafIds.contains(BuiltInRegistries.BLOCK.getKey(state.getBlock()).toString())&&!state.hasBlockEntity()
                &&state.getFluidState().isEmpty()&&level.getBlockEntity(p)==null)approvedFoliage.add(p);
        }
        if(captureCursor<total)return;
        if(!before.get(root).equals(parse(rootPlan.get("expected_root").getAsString()))
            ||!before.get(root.below()).equals(parse(rootPlan.get("expected_soil").getAsString())))
            throw new IllegalStateException("Measured root/soil authority changed; do not choose a new plot automatically");
        JsonObject value=new JsonObject();value.addProperty("format","awft-native-tree-patch-live-preimage:1");
        value.addProperty("construction_forbidden",true);value.addProperty("request_sha256",requestSha);value.addProperty("source_patch_sha256",planSha);
        value.addProperty("root_id",rootId);value.add("root",rootPlan.get("root"));value.addProperty("captured",Instant.now().toString());
        value.add("actual_complete_field",field(before));value.add("actual_native_BEs",beRows(nativeBEs()));
        value.addProperty("approved_current_native_foliage_cells",approvedFoliage.size());value.addProperty("ordinary_feature_not_yet_called",true);
        Path file=writeArchive(value,"tree-patch-preimage");capturedName=file.getFileName().toString();capturedSha=sha(bounded(file,8*1024*1024));
        report.put("live_preimage",capturedName);report.put("live_preimage_sha256",capturedSha);report.put("live_preimage_cells",before.size());
        if(action.equals("inspect")){rootOutcomes.add(Map.of("root_id",rootId,"status","CURRENT_NATIVE_FIELD_CAPTURED_NO_MUTATION","preimage",capturedName,"preimage_sha256",capturedSha));phase=Phase.NEXT;return;}
        phase=Phase.GROW;
    }
    private Path writeArchive(JsonObject value,String family)throws Exception{
        byte[] raw=JSON.toJson(value).getBytes(StandardCharsets.UTF_8);if(raw.length>16*1024*1024)throw new IllegalStateException("Finite exact native archive required");
        var bytes=new java.io.ByteArrayOutputStream();try(var zip=new java.util.zip.GZIPOutputStream(bytes)){zip.write(raw);}
        byte[] compressed=bytes.toByteArray();if(compressed.length>8*1024*1024||archiveBytes+compressed.length>MAX_ARCHIVE_BYTES)
            throw new IllegalStateException("Finite patch allocation refused before archive/write");
        Files.createDirectories(journal);Path file=journal.resolve(family+"-"+UUID.randomUUID()+".json.gz");
        durable(file,compressed);durable(file.resolveSibling(file.getFileName()+".complete"),sha(compressed).getBytes(StandardCharsets.UTF_8));archiveBytes+=compressed.length;return file;
    }
    private static void durable(Path path,byte[] bytes)throws Exception{
        try(var channel=java.nio.channels.FileChannel.open(path,StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE)){
            var buffer=java.nio.ByteBuffer.wrap(bytes);while(buffer.hasRemaining())channel.write(buffer);channel.force(true);
        }
    }
    private void rootIntent()throws Exception{
        if(capturedSha==null||capturedName==null)throw new IllegalStateException("A durable current complete field must precede every owned setter");
        JsonObject value=new JsonObject();value.addProperty("format","awft-dense-native-root-intent:1");value.addProperty("request_sha256",requestSha);
        value.addProperty("patch_plan_sha256",planSha);value.addProperty("root_id",rootId);value.add("root",rootPlan.get("root"));
        value.addProperty("native_preimage",capturedName);value.addProperty("native_preimage_sha256",capturedSha);value.addProperty("created",Instant.now().toString());
        durable(rootIntent,JSON.toJson(value).getBytes(StandardCharsets.UTF_8));
    }
    private void nextRoot()throws Exception{
        for(ChunkPos c:List.copyOf(tickets)){ticket(c,false);tickets.remove(c);}
        pending.removeIf(CompletableFuture::isDone);if(!pending.isEmpty())return;
        before.clear();approvedFoliage.clear();rootIndex++;
        if(rootIndex>=patchRoots.size()){report.put("roots",List.copyOf(rootOutcomes));finish("finite native patch completed; mature coverage/visual ecology remains measured separately");return;}
        selectRoot();
    }
'''


def transform_controller(old):
    text=old.replace('NativeTreeGrowthSupport','NativeTreePatchSupport')
    text=once(text,'IDLE,HASH,DESCRIBE,LOAD,VERIFY,GROW,CLEANUP','IDLE,HASH,DESCRIBE,READ_SAVED,LOAD,CAPTURE,GROW,NEXT,CLEANUP')
    text=once(text,'MAX_INPUT=8*1024*1024,MAX_CELLS=131072,MAX_TICKS=1800','MAX_INPUT=16*1024*1024,MAX_CELLS=131072,MAX_TICKS=7200')
    text=once(text,'private AABB writeBounds;','private AABB writeBounds;'+PATCH_FIELDS)
    text=text.replace('awft_native_tree','awft_native_tree_patch').replace('"awfttrees"','"awfttreepatch"').replace('"describe","grow"','"inspect","grow"')
    text=text.replace('"trees-[a-f0-9]{16}"','"treepatch-[a-f0-9]{16}"').replace('"awft-native-trees:1"','"awft-native-tree-patch:1"').replace('"awft-native-tree-plan:1"','"awft-native-tree-patch-plan:1"')
    text=once(text,'        report.clear();descriptors.clear();','        patchRoots.clear();rootOutcomes.clear();patchIds.clear();heldRoots.clear();eligibleColumns.clear();approvedFoliage.clear();leafIds.clear();rootIndex=0;archiveBytes=0;anyMutated=false;requestSha=expected;savedReadiness=null;\n        report.clear();descriptors.clear();')
    start=text.index('        if(mode.equals("grow")){')
    end=text.index('        modPath=owned(',start)
    text=text[:start]+PATCH_ADMISSION+text[end:]
    text=once(text,'    private static int[] box(JsonArray a)',PATCH_METHODS+'\n    private static int[] box(JsonArray a)')
    text=once(text,'JsonObject descriptor=descriptors.get(saplings.getFirst());','JsonObject descriptor=descriptors.get(currentSaplingId);')
    text=once(text,'new TreeBeeAudit(level,before,writeBounds,TreeBeeAudit.mayCreateNest(descriptor))','new TreeBeeAudit(level,before,writeBounds,TreeBeeAudit.mayCreateNest(descriptor),true)')
    text=once(text,'new TreeGrowthScope(level,before,writeBounds,protectedColumns,root.getY()-1,TreeBeeAudit.mayCreateNest(descriptor))','new TreeGrowthScope(level,before,writeBounds,protectedColumns,root.getY()-1,TreeBeeAudit.mayCreateNest(descriptor),approvedFoliage)')
    text=once(text,'            scope.hookWitness(root);','            scope.hookWitness(root);\n            rootIntent(); // durable native field/intent precedes the first physical setter')
    text=once(text,'            mutated=true;if(!level.setBlock','            mutated=true;anyMutated=true;if(!level.setBlock')
    old_archive='Files.createDirectories(journal);Path file=journal.resolve("tree-outcome-"+UUID.randomUUID()+".json");Files.write(file,raw,StandardOpenOption.CREATE_NEW);Files.writeString(file.resolveSibling(file.getFileName()+".complete"),sha(raw),StandardOpenOption.CREATE_NEW);report.put("outcome_archive",file.getFileName().toString());report.put("outcome_archive_sha256",sha(raw));'
    new_archive='value.addProperty("root_id",rootId);value.add("root",rootPlan.get("root"));value.addProperty("live_preimage_sha256",capturedSha);value.addProperty("approved_native_leaf_overlap_cells",approvedFoliage.size());Path file=writeArchive(value,"tree-patch-outcome");report.put("outcome_archive",file.getFileName().toString());report.put("outcome_archive_sha256",sha(bounded(file,8*1024*1024)));'
    text=once(text,old_archive,new_archive)
    start=text.index('    public void tick(MinecraftServer server){')
    text=text[:start]+'''    public void tick(MinecraftServer server){
        if(phase==Phase.IDLE)return;if(phase==Phase.CLEANUP){cleanup(true);return;}long start=System.nanoTime();
        try{
            if(++ticks>MAX_TICKS||!server.isSameThread()||lease==null||!lease.valid()||!server.getPlayerList().getPlayers().isEmpty())throw new IllegalStateException("Native patch finite deadline/thread/empty-server lease refused");
            if(phase==Phase.HASH){int n;do{n=hashStream.read(buffer);if(n>0){hashDigest.update(buffer,0,n);hashBytes+=n;}}while(n>=0&&System.nanoTime()-start<3_000_000L);if(n>=0)return;hashStream.close();hashStream=null;if(hashBytes!=hashAttrs.size()||!HexFormat.of().formatHex(hashDigest.digest()).equals(RU_SHA))throw new IllegalStateException("Pinned RU bytes differ");phase=Phase.DESCRIBE;}
            gate(server);
            if(phase==Phase.DESCRIBE){String id=saplings.get(cursor++);JsonObject value;try{value=describe(id);}catch(Throwable failure){throw new IllegalStateException("Actual native descriptor failed",failure);}descriptors.put(id,value);if(cursor<saplings.size())return;cursor=0;
                Set<ChunkPos> all=new HashSet<>();for(JsonObject row:patchRoots){int[] b=box(row.getAsJsonArray("known_bounds"));for(int x=b[0]>>4;x<=b[3]>>4;x++)for(int z=b[2]>>4;z<=b[5]>>4;z++)all.add(new ChunkPos(x,z));}
                savedReadiness=new NativeTreePatchReadiness(level,all);phase=Phase.READ_SAVED;return;}
            if(phase==Phase.READ_SAVED){if(!tickets.isEmpty())throw new IllegalStateException("No ticket before stored FULL validation");if(!savedReadiness.poll())return;report.put("current_storage_readiness",savedReadiness.report());checkpoint();selectRoot();return;}
            if(phase==Phase.LOAD){if(pending.stream().anyMatch(f->!f.isDone()))return;for(var future:pending)future.join();pending.clear();if(!ready())return;phase=Phase.CAPTURE;}
            if(phase==Phase.NEXT){nextRoot();return;}
            if(!ready())throw new IllegalStateException("Current root FULL known envelope unloaded");
            if(phase==Phase.CAPTURE){captureRoot(start);return;}
            if(phase==Phase.GROW){
                grow();rootOutcomes.add(Map.of("root_id",rootId,"status","NATIVE_MATURE_TRUNK_CANOPY_OBSERVED_NOT_VISUAL_ACCEPTANCE",
                    "preimage",capturedName,"preimage_sha256",capturedSha,"outcome",report.get("outcome_archive"),"outcome_sha256",report.get("outcome_archive_sha256")));
                phase=Phase.NEXT;
            }
        }catch(Exception|LinkageError error){report.put("error",error.toString());report.put("failures",1);report.put("roots",List.copyOf(rootOutcomes));finish("native patch stopped at first refusal/failure; successful prior roots and exact failed-root evidence retained, no retry");}
        report.put("last_work_ms",(System.nanoTime()-start)/1_000_000.0);
    }
    private void finish(String text){if(outcome==null)outcome=text;phase=Phase.CLEANUP;cleanup(true);}
    private void cleanup(boolean retry){
        List<String> errors=new ArrayList<>();if(hashStream!=null)try{hashStream.close();hashStream=null;}catch(Exception e){errors.add(e.toString());}
        if(level!=null)for(ChunkPos c:List.copyOf(tickets))try{ticket(c,false);tickets.remove(c);}catch(Exception|LinkageError e){errors.add(c+": "+e);}
        pending.removeIf(CompletableFuture::isDone);
        boolean savedIOClean=savedReadiness==null||savedReadiness.drained();
        if(tickets.isEmpty()&&pending.isEmpty()&&hashStream==null&&savedIOClean&&lease!=null)try{lease.close();lease=null;}catch(Exception e){errors.add(e.toString());}
        boolean clean=tickets.isEmpty()&&pending.isEmpty()&&hashStream==null&&savedIOClean&&lease==null;
        report.put("status",outcome);report.put("cleanup_resources_passed",clean);report.put("world_recovery_required",worldResidual);report.put("cleanup_passed",clean&&!worldResidual);
        report.put("temporary_tickets_remaining",tickets.size());report.put("pending_shared_futures",pending.size());report.put("cleanup_errors",errors);
        report.put("pending_persisted_read_futures",savedReadiness==null?0:savedReadiness.pending());
        report.put("native_bonemeal_trials_current_root",rolls);report.put("native_success_rolls_current_root",successRolls);report.put("perform_bonemeal_calls_current_root",performCalls);
        report.put("archive_bytes",archiveBytes);report.put("invented_or_claimed_consumed_bonemeal_items",0);report.put("global_wakes",0);
        report.put("any_root_setter_invoked",anyMutated);report.put("native_visual_or_density_acceptance",false);report.put("finished",Instant.now().toString());
        if(clean&&!terminalPublished)try{NativeJournal.terminal(journal,"tree-patch",report);terminalPublished=true;}
        catch(Exception failure){report.put("terminal_publication_blocked",failure.toString());}
        try{NativeJournal.progress(journal,"tree-patch-status.json",report);}catch(Exception failure){report.put("progress_publication_warning",failure.toString());}
        if(clean&&terminalPublished)phase=Phase.IDLE;
    }
    public void stopped(){if(busy())finish("server stopping; per-root records/owned native outcomes and any quarantine retained");}
}
'''
    return text


def transform_scope(old):
    text=once(old,'    final boolean allowNativeNest;','    final boolean allowNativeNest;\n    final Set<BlockPos> approvedNativeFoliage;')
    constructor='''        if(ACTIVE.get()!=null||!level.getServer().isSameThread())'''
    text=once(text,constructor,'''        this(level,before,writeBounds,protectedColumns,soilY,allowNativeNest,Set.of());
    }
    /** Dense-patch-only permission: exact captured native leaves to native leaves.
     * Legacy calls keep the empty permission set and their original refusals. */
    public TreeGrowthScope(ServerLevel level,Map<BlockPos,BlockState> before,AABB writeBounds,Set<Long> protectedColumns,int soilY,boolean allowNativeNest,Set<BlockPos> approvedNativeFoliage){
        if(approvedNativeFoliage.size()>65536)throw new IllegalStateException("Finite exact native foliage overlap required");
        this.approvedNativeFoliage=snapshotSet(approvedNativeFoliage);
        for(BlockPos p:this.approvedNativeFoliage){BlockState state=before.get(p);if(state==null||!(state.getBlock()instanceof LeavesBlock)||!state.is(BlockTags.LEAVES)
            ||state.hasBlockEntity()||!state.getFluidState().isEmpty()||!writeBounds.contains(p.getX()+.5,p.getY()+.5,p.getZ()+.5)
            ||protectedColumns.contains(column(p.getX(),p.getZ())))throw new IllegalStateException("Unreviewed or protected overlap cell");}
        if(ACTIVE.get()!=null||!level.getServer().isSameThread())''')
    text=once(text,'    public static void write(Level level,BlockPos position,BlockState desired){',
        '''    static boolean foliageOverlap(boolean approved,boolean oldLeaves,boolean oldLog,boolean oldBE,boolean oldFluid,
            boolean newLeaves,boolean newLog,boolean newBE,boolean newFluid){
        return approved&&oldLeaves&&!oldLog&&!oldBE&&!oldFluid&&newLeaves&&!newLog&&!newBE&&!newFluid;
    }
    public static void write(Level level,BlockPos position,BlockState desired){''')
    text=once(text,'        if(original.hasBlockEntity()||',
        '''        boolean nativeFoliageOnly=foliageOverlap(scope.approvedNativeFoliage.contains(position),
            original.getBlock()instanceof LeavesBlock&&original.is(BlockTags.LEAVES),original.is(BlockTags.LOGS),original.hasBlockEntity(),!original.getFluidState().isEmpty(),
            desired.getBlock()instanceof LeavesBlock&&desired.is(BlockTags.LEAVES),desired.is(BlockTags.LOGS),desired.hasBlockEntity(),!desired.getFluidState().isEmpty());
        if(original.hasBlockEntity()||''')
    text=once(text,'||original.getBlock() instanceof LeavesBlock||original.is(BlockTags.LOGS)',
        '||original.getBlock() instanceof LeavesBlock&&!nativeFoliageOnly||original.is(BlockTags.LOGS)')
    text=once(text,'||!(original.isAir()||SOFT.contains(id)',
        '||!(nativeFoliageOnly||original.isAir()||SOFT.contains(id)')
    return text


def transform_bees(old):
    text=once(old,'        if(!level.getServer().isSameThread()||before.isEmpty()',
        '''        this(level,before,write,allowNativeNest,false);
    }
    /** Dense patches may read/preserve existing BEs; scoped setters cannot touch
     * them and the complete exact before/after BE census must remain equal. */
    public TreeBeeAudit(ServerLevel level,Map<BlockPos,BlockState> before,AABB write,boolean allowNativeNest,boolean preserveExistingBEsInWrite)throws Exception{
        if(!level.getServer().isSameThread()||before.isEmpty()''')
    text=once(text,'this.before=Map.copyOf(before);','this.before=TreeGrowthScope.snapshotMap(before);')
    text=once(text,'for(BlockPos p:blockEntitiesBefore.keySet())if(inside(p))',
        'for(BlockPos p:blockEntitiesBefore.keySet())if(inside(p)&&!preserveExistingBEsInWrite)')
    return text


def prepare():
    root=Path(__file__).resolve().parents[1];output=root/'compat/proposals/dense-tree-patch49'
    if output.exists():raise UserError('Preserve original proposal; use an additive revision')
    sources={name:root/'compat/control-bridge/src/worldfortwo/bridge'/f'{name}.java'for name in BASES}
    if any(digest(path)!=BASES[name]for name,path in sources.items()):raise UserError('Exact reviewed48 tree base required')
    reserve=guard(8*1024**2,0);output.mkdir()
    transforms={'NativeTreeGrowthSupport':('NativeTreePatchSupport',transform_controller),'TreeGrowthScope':('TreeGrowthScope',transform_scope),'TreeBeeAudit':('TreeBeeAudit',transform_bees)}
    for name,path in sources.items():
        old=path.read_text();target,fn=transforms[name];text=fn(old)
        (output/f'{name}48-base.java.txt').write_bytes(path.read_bytes())
        (output/f'{target}.java').write_text(text,encoding='utf-8',newline='\n')
        patch=''.join(difflib.unified_diff(old.splitlines(True),text.splitlines(True),fromfile=f'native48/{name}.java',tofile=f'proposal/{target}.java'))
        (output/f'{target}.diff').write_text(patch,encoding='utf-8',newline='\n')
    receipt={'format':'awft-dense-tree-patch-source:1','created':utcnow(),'base_sources':BASES,'reserve_guard':reserve,
             'native_actions':0,'native_or_density_acceptance':False,'API_compile':'PENDING','generator_sha256':digest(Path(__file__))}
    (output/'initial-custody.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    return {'output':str(output),'files':{p.name:digest(p)for p in output.iterdir()if p.is_file()}}


if __name__=='__main__':print(json.dumps(prepare(),indent=2))
