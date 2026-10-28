"""Assemble a reviewed resume-only successor outside active bridge sources.

No compiler/installer/runtime entry point. Every replacement is exact and the
input source is hash pinned. Call derive(bytes) then store in a NEW private
staging folder after ReserveGuard. Parent owns candidate integration/compile.
"""
from __future__ import annotations
import hashlib
from contract import ACTIVE_SOURCE_SHA, GEOMETRY_SHA, PARTIAL_SHA, SOURCE_SHAS

def derive(raw):
    if hashlib.sha256(raw).hexdigest()!=ACTIVE_SOURCE_SHA:raise ValueError('Original active engineering source changed; review before deriving')
    text=raw.decode().replace('\r\n','\n')
    def replace(old,new):
        nonlocal text
        if text.count(old)!=1:raise ValueError('Unique reviewed source anchor required: '+old[:100])
        text=text.replace(old,new)
    def span(first,last,new):
        nonlocal text
        if text.count(first)!=1 or text.count(last)!=1:raise ValueError('Unique reviewed source section required')
        start,end=text.index(first),text.index(last)
        if start>=end:raise ValueError('Source section ordering differs')
        text=text[:start]+new+text[end:]
    replace('IDLE, HASH, READY, VERIFY, INITIALIZE, WAIT_STOP, WAIT_STATIONS, TUBES, WATER, WAIT_MODE',
            'IDLE, HASH, READY, VERIFY, WAIT_STOP, WAIT_STATIONS, RESUME_ATTACH, WAIT_MODE')
    replace('private static final String PLAN_SHA="'+SOURCE_SHAS[0]+'";',
            'private static final String PLAN_SHA="'+GEOMETRY_SHA+'"; // source geometry signature, not a placement-plan digest\n'+
            '    private static final String PARTIAL_SHA="'+PARTIAL_SHA+'";\n'+
            '    private static final String[] SOURCE_SHA={'+','.join('"'+s+'"' for s in SOURCE_SHAS)+'};')
    replace('private JsonObject request,manifest,plan,systems;',
            'private JsonObject request,manifest,plan,systems,resumePartial,stockProof;\n    private final Map<BlockPos,BlockState> currentTargets=new LinkedHashMap<>();\n    private NativeMillResumeAttachments resume;\n    private String resumeContract;')
    replace('for(String op:List.of("inspect","commission"))','for(String op:List.of("inspect","resume"))')
    replace('!name.matches("mill-commission-[a-f0-9]{16}")','!name.matches("mill-resume-[a-f0-9]{16}")')
    replace('awft-artistic-mill-live:1','awft-artistic-mill-resume:1')
    replace('request=JsonParser.parseString(new String(raw,StandardCharsets.UTF_8)).getAsJsonObject();',
            'request=JsonParser.parseString(new String(raw,StandardCharsets.UTF_8)).getAsJsonObject();if(!request.get("intended_operation").getAsString().equals(operation))throw new IllegalStateException("Request is not admitted for this operation");')
    span('        if(!ref("plan").get("sha256").getAsString().equals(PLAN_SHA)',
         '        targets.clear();chunks.clear();',ADMISSION)
    replace('if(targets.size()!=7710||chunks.size()>32)','if(targets.size()!=7941||chunks.size()>32)')
    replace('report.put("historical_before_finished",beforeProof.get("finished").getAsString());',
            'report.put("historical_partial_finished",resumePartial.get("finished").getAsString());report.put("current_backup_sha256",checkpoint.get("sha256").getAsString());report.put("resume_contract_sha256",resumeContract);report.put("source_geometry_sha256",PLAN_SHA);report.put("native_class_sha256",request.get("native_class_sha256").getAsString());report.put("native_attachment_class_sha256",request.get("native_attachment_class_sha256").getAsString());')
    replace('report.put("plan_sha256",PLAN_SHA);','report.put("plan_sha256",ref("plan").get("sha256").getAsString());')
    replace('    private static BlockPos pos(int x,int y,int z)',SUPPORT+'    private static BlockPos pos(int x,int y,int z)')
    span('    private void connect(int n){','    private static float nativeFloat(', '')
    span('    private void manualModes(){','    private boolean processed(){','')
    replace('if(action.equals("commission")){level.resetEmptyTime();','if(action.equals("resume")){level.resetEmptyTime();')
    replace('if(actual.getBlock()!=row.getValue().getBlock())throw new IllegalStateException("Native physical/air target differs at "+row.getKey());',
            'if(!actual.equals(currentTargets.get(row.getKey())))throw new IllegalStateException("Fresh exact native preimage changed at "+row.getKey());validateRetainedStructure(row.getKey(),row.getValue(),actual);')
    replace('if(index==rows.size()){emptyInputs();if(action.equals("inspect")){report.put("source_only_geometry_verified",targets.size());sample();finish("native dry mill inspected; no commissioning mutation");}else next(Phase.INITIALIZE);}',
            'if(index==rows.size()){emptyInputs();resume=new NativeMillResumeAttachments(level,lease,fillerCells,resumePartial,stockProof,resumeContract,action.equals("inspect"),()->mutated=true,report);links.addAll(resume.retainedLinks());requireHydraulics();if(action.equals("inspect")){resume.preflight(stopped(),stationsReady());report.put("source_and_current_preimage_targets_verified",targets.size());sample();finish("native retained mill inspected; no resume mutation");}else next(Phase.WAIT_STOP);}')
    span('            else if(phase==Phase.INITIALIZE)', '            else if(phase==Phase.WAIT_STOP)', '')
    replace('if(stationsReady())next(Phase.TUBES);','if(stationsReady()){resume.preflight(stopped(),true);next(Phase.RESUME_ATTACH);}')
    span('            else if(phase==Phase.TUBES)', '            else if(phase==Phase.WAIT_MODE)',
         '            else if(phase==Phase.RESUME_ATTACH){gate(server);if(!stopped()||!stationsReady())throw new IllegalStateException("Actual stopped stations changed before attachment");requireHydraulics();if(index<2)resume.installOne(index++);else{resume.notifyManual();next(Phase.WAIT_MODE);}}\n')
    replace('if(manualModeReady())','if(resume.manualReady())')
    replace('gate(server);feed();next(Phase.PROCESS);','gate(server);resume.intent("feed");feed();resume.completed("feed");next(Phase.PROCESS);')
    replace('gate(server);assemble();next(Phase.WAIT_TRAIN);','gate(server);resume.intent("assembly");assemble();resume.completed("assembly");next(Phase.WAIT_TRAIN);')
    replace('native stationary commissioning passed; actual passenger trips and restart acceptance pending',
            'native resumed stationary commissioning passed; actual passenger trips and restart acceptance pending')
    return text.encode()

ADMISSION='''        if(!ref("manifest").get("sha256").getAsString().equals(MANIFEST_SHA))throw new IllegalStateException("Reviewed original systems manifest required");
        manifest=readRef(ref("manifest"),2*1024*1024);systems=manifest.getAsJsonObject("systems");plan=readRef(ref("plan"),2*1024*1024);level=server.overworld();
        Path world=server.getWorldPath(LevelResource.ROOT).toRealPath(),stage=Path.of("D:/A World for Two/staging/world-tests").toRealPath();
        if(!world.startsWith(stage)||world.getNameCount()!=stage.getNameCount()+3||!world.getParent().getFileName().toString().equals("world")||!world.getFileName().toString().equals("RosewaterArtistic")||server.getPort()!=25575||!world.equals(Path.of(plan.get("world_path").getAsString()).toRealPath())||!home.toRealPath().equals(world.getParent().getParent()))throw new IllegalStateException("Exact private RosewaterArtistic world/home ancestry required");
        JsonArray sources=request.getAsJsonArray("source_plans");if(sources.size()!=3)throw new IllegalStateException("All three exact mill sources required");Map<BlockPos,BlockState> authored=new LinkedHashMap<>();
        for(int n=0;n<3;n++){JsonObject r=sources.get(n).getAsJsonObject();if(!r.get("sha256").getAsString().equals(SOURCE_SHA[n]))throw new IllegalStateException("Reviewed mill source differs");JsonObject source=readRef(r,2*1024*1024);if(!source.get("seed").equals(plan.get("seed"))||!source.get("world_path").equals(plan.get("world_path")))throw new IllegalStateException("Source world differs");authored.putAll(states(source));}
        if(authored.size()!=7941||!authored.equals(states(plan)))throw new IllegalStateException("Complete R3 plus94 canonical geometry required; never replay placement");
        JsonObject checkpoint=readRef(ref("current_backup"),4096);
        if(!checkpoint.get("verified").getAsBoolean()||!checkpoint.get("sha256").getAsString().matches("[a-f0-9]{64}")||!owned(ref("current_backup").get("path").getAsString()).equals(home.resolve("dashboard/settlement/backup-receipt.json")))throw new IllegalStateException("Actual current verified backup receipt required");
        JsonObject afterPlan=readRef(ref("native_after_plan"),2*1024*1024);currentTargets.clear();currentTargets.putAll(states(afterPlan));
        if(!afterPlan.get("backup_sha256").equals(checkpoint.get("sha256"))||!afterPlan.get("world_path").equals(plan.get("world_path"))||!afterPlan.get("seed").equals(plan.get("seed"))||!currentTargets.keySet().equals(authored.keySet()))throw new IllegalStateException("Fresh complete same-world exact-target preimage required");
        JsonObject afterProof=nativeProof("native_after",ref("native_after_plan").get("sha256").getAsString(),7941,true);
        if(!ref("native_partial").get("sha256").getAsString().equals(PARTIAL_SHA))throw new IllegalStateException("Exact retained original WAIT_MODE failure required");resumePartial=completedRef("native_partial");
        resumeContract=sha(("awft:mill-resume:1\\n"+world+"\\n"+PLAN_SHA+"\\n"+PARTIAL_SHA+"\\n"+MANIFEST_SHA+"\\n").getBytes(StandardCharsets.UTF_8));stockProof=null;
        try(InputStream code=NativeMillResumeAttachments.class.getResourceAsStream("NativeMillResumeAttachments.class")){if(code==null||!sha(code.readNBytes(256*1024+1)).equals(request.get("native_attachment_class_sha256").getAsString()))throw new IllegalStateException("Exact compiled native attachment collaborator required");}
        if(operation.equals("resume")){JsonObject inspection=completedRef("native_inventory_inspection");Instant measured=Instant.parse(inspection.get("finished").getAsString());if(inspection.has("error")||!inspection.get("operation").getAsString().equals("inspect")||!inspection.get("cleanup_passed").getAsBoolean()||inspection.get("remaining_owned_tickets").getAsInt()!=0||!inspection.get("candidate").getAsString().equals(expectedCandidate)||!inspection.get("bridge").getAsString().equals(expectedBridge)||!inspection.get("native_class_sha256").equals(request.get("native_class_sha256"))||!inspection.get("native_attachment_class_sha256").equals(request.get("native_attachment_class_sha256"))||!inspection.get("native_after_plan_sha256").equals(ref("native_after_plan").get("sha256"))||!inspection.get("resume_contract_sha256").getAsString().equals(resumeContract)||!inspection.get("current_backup_sha256").equals(checkpoint.get("sha256"))||Instant.parse(inspection.get("started").getAsString()).isBefore(Instant.parse(afterProof.get("finished").getAsString()))||measured.isAfter(Instant.now())||measured.isBefore(Instant.now().minusSeconds(1200)))throw new IllegalStateException("Fresh exact current-candidate native inventory inspection required");stockProof=inspection.getAsJsonObject("native_resume_stock");}
'''

SUPPORT='''    private JsonObject completedRef(String key)throws Exception{JsonObject value=readRef(ref(key),512*1024);Path file=owned(ref(key).get("path").getAsString()),marker=owned(ref(key+"_complete").get("path").getAsString());byte[] raw=readBounded(marker,128);if(!marker.equals(file.resolveSibling(file.getFileName()+".complete"))||!sha(raw).equals(ref(key+"_complete").get("sha256").getAsString())||!new String(raw,StandardCharsets.UTF_8).trim().equals(ref(key).get("sha256").getAsString()))throw new IllegalStateException("Exact immutable native completion marker required");return value;}
    private static Map<BlockPos,BlockState> states(JsonObject source){if(source.getAsJsonArray("commands").size()!=0)throw new IllegalStateException("No construction commands in resume evidence");Map<BlockPos,BlockState> result=new LinkedHashMap<>();JsonArray palette=source.getAsJsonArray("palette");for(JsonElement entry:source.getAsJsonArray("blocks")){JsonArray row=entry.getAsJsonArray();if(row.size()!=4)throw new IllegalStateException("Exact source row required");BlockPos p=pos(row.get(0).getAsInt(),row.get(1).getAsInt(),row.get(2).getAsInt());if(result.put(p,state(palette.get(row.get(3).getAsInt()).getAsString()))!=null)throw new IllegalStateException("Duplicate source/preimage target");}return result;}
    private void validateRetainedStructure(BlockPos p,BlockState source,BlockState actual){
        if(source.isAir()&&actual.getBlock() instanceof TubePathBlock&&fillerCells.contains(p))return;
        if(source.isAir()&&actual.is(Blocks.WATER)&&p.getX()>=1306&&p.getX()<=1308&&p.getY()>=68&&p.getY()<=73&&p.getZ()>=-1001&&p.getZ()<=-999)return;
        if(source.getBlock()!=actual.getBlock())throw new IllegalStateException("Unrelated source identity/air drift at "+p);
        boolean entrance=p.getX()==1331&&p.getY()==71&&(p.getZ()==-991||p.getZ()==-943),modeLever=p.getX()==1330&&p.getY()==71&&(p.getZ()==-991||p.getZ()==-943);
        for(Property<?> property:source.getProperties()){String key=property.getName();if(entrance&&Set.of("locked","powered","connected","open","has_block_in_front").contains(key)||modeLever&&key.equals("powered"))continue;if(!source.getValue(property).equals(actual.getValue(property)))throw new IllegalStateException("Retained structural state differs at "+p+" "+key);}
    }
    private void requireHydraulics(){for(JsonElement e:systems.getAsJsonObject("watermill").getAsJsonArray("water_sources")){BlockState value=level.getBlockState(position(e));if(!value.is(Blocks.WATER)||!value.getFluidState().isSource())throw new IllegalStateException("Original real hydraulic source missing; resume never replaces water");}ItemStack filter=be(component("pneumatic","extractor"),PneumaticConnectionBlockEntity.class).getFilter();if(filter.isEmpty()||filter.getCount()!=1||!BuiltInRegistries.ITEM.getKey(filter.getItem()).toString().equals("create:wheat_flour"))throw new IllegalStateException("Original native flour filter missing/changed; resume never initializes it");report.put("existing_native_filter_preserved",true);}
'''
