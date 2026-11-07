"""Additive98 catalogue + exact native Toolbox role, preserving frozen R4."""
from pathlib import Path
import hashlib
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent/'native-relocation-uninvoked-r4/NativeRelocationSupport.java'
EXPECTED='75c1107d851a3b14c4f20c0eeaaab96a7e75644458de302a976a9d20dfdf0865'
CATALOG='698969e25fb001c21fb4a9b8301d96b7892d0affe9a9263369c74bba591d7fc5'

AUDIT=r'''
    private void auditQuarantined(MinecraftServer server)throws Exception{
        quarantined=true;JsonObject prior=ref("quarantined_move_terminal",1048576);JsonObject terminalRef=request.getAsJsonObject("quarantined_move_terminal");
        Path terminal=owned(terminalRef.get("path").getAsString());
        if(!new String(bytes(terminal.resolveSibling(terminal.getFileName()+".complete"),128),StandardCharsets.UTF_8).trim().equals(terminalRef.get("sha256").getAsString())
            ||!prior.get("transaction_id").equals(JSON.toJsonTree(report.get("transaction_id")))||!prior.get("capsule_id").getAsString().equals(capsuleId)
            ||!prior.get("operation").getAsString().equals("move")||!prior.get("clone_invoked").getAsBoolean()||!prior.get("intent_written").getAsBoolean()
            ||!prior.get("failed").getAsBoolean()||!prior.get("quarantine").getAsBoolean()||!prior.get("cleanup_passed").getAsBoolean()
            ||prior.get("owned_chunk_tickets").getAsInt()!=0||prior.get("pending_owned_futures").getAsInt()!=0||prior.get("pending_shared_chunk_futures").getAsInt()!=0
            ||prior.has("ticket_cleanup_error")||prior.has("lease_cleanup_error")||Files.exists(ledger.resolve("completed.json"),LinkOption.NOFOLLOW_LINKS))
            throw new IllegalStateException("Exact marked actually invoked quarantined move with clean resources required; no completion/retry");
        JsonObject selected=null;String chosen=null;int matches=0;
        for(String name:List.of("intent.json","intent-after-uninvoked-resolution.json")){
            Path p=ledger.resolve(name);if(!Files.exists(p,LinkOption.NOFOLLOW_LINKS))continue;JsonObject candidate=read(p,1048576);
            if(candidate.get("request_sha256").equals(prior.get("request_sha256"))&&candidate.get("transaction_id").equals(prior.get("transaction_id"))){selected=candidate;chosen=name;matches++;}
        }
        if(matches!=1)throw new IllegalStateException("One exact actual failed native intent required");
        String quarantineName=chosen.equals("intent.json")?"quarantine.json":"quarantine-after-uninvoked-resolution.json";JsonObject q=read(ledger.resolve(quarantineName),1048576);
        if(!q.get("request_sha256").equals(prior.get("request_sha256"))||!q.get("clone_invoked").getAsBoolean())throw new IllegalStateException("Actual invoked quarantine evidence differs");
        if(chosen.equals("intent-after-uninvoked-resolution.json")){
            byte[] resolution=bytes(ledger.resolve("uninvoked-resolution.json"),1048576);
            if(!selected.get("uninvoked_resolution_sha256").getAsString().equals(sha(resolution))||!sha(bytes(ledger.resolve("intent.json"),1048576)).equals(Uninvoked.INTENT)
                ||!sha(bytes(ledger.resolve("quarantine.json"),1048576)).equals(Uninvoked.QUARANTINE))throw new IllegalStateException("Original append-only uninvoked history changed");
        }
        report.put("original_failed_move_terminal_sha256",terminalRef.get("sha256").getAsString());report.put("original_clone_invoked",true);
        report.put("original_intent_sha256",sha(bytes(ledger.resolve(chosen),1048576)));report.put("original_quarantine_sha256",sha(bytes(ledger.resolve(quarantineName),1048576)));
        JsonArray sourceDifferences=new JsonArray(),destinationDifferences=new JsonArray(),survivalFailures=new JsonArray(),actual=new JsonArray();
        for(var e:source.entrySet()){
            BlockPos p=e.getKey(),d=translated(p);BlockState src=level.getBlockState(p),dst=level.getBlockState(d);
            if(!src.isAir()||level.getBlockEntity(p)!=null){JsonObject v=new JsonObject();v.add("position",JSON.toJsonTree(xyz(p)));v.addProperty("actual",src.toString());sourceDifferences.add(v);}
            JsonObject row=new JsonObject();row.add("position",JSON.toJsonTree(xyz(d)));row.addProperty("actual",dst.toString());row.addProperty("expected",e.getValue().toString());row.addProperty("canSurvive",dst.canSurvive(level,d));actual.add(row);
            if(!dst.equals(e.getValue()))destinationDifferences.add(row.deepCopy());if(!dst.canSurvive(level,d))survivalFailures.add(row.deepCopy());
        }
        report.put("source_not_AIR",sourceDifferences);report.put("source_AIR_passed",sourceDifferences.isEmpty());report.put("destination_current_full_states",actual);
        report.put("destination_state_differences",destinationDifferences);report.put("destination_survival_failures",survivalFailures);
        report.put("source_entity_count",level.getEntities((Entity)null,new AABB(LOW.getX(),LOW.getY(),LOW.getZ(),HIGH.getX()+1,HIGH.getY()+1,HIGH.getZ()+1).inflate(.25)).size());
        report.put("destination_entity_count",level.getEntities((Entity)null,new AABB(LOW.getX(),LOW.getY(),LOW.getZ(),HIGH.getX()+1,HIGH.getY()+1,HIGH.getZ()+1).move(dx,dy,dz).inflate(.25)).size());
        report.put("native_content_conservation_passed",false);
        try{JsonArray now=snapshots(true);report.put("current_native_snapshots",now);compare(selected.getAsJsonArray("before_native_snapshots"),now,true);report.put("native_content_conservation_passed",true);}
        catch(Exception|LinkageError failure){report.put("native_content_conservation_error",failure.getClass().getName()+": "+String.valueOf(failure.getMessage()));}
        ready(server);report.put("read_only_audit",true);report.put("completion_or_resolution_written",false);report.put("original_intent_and_quarantine_retained",true);
        finish("read-only actual quarantined-room audit; original failure retained; no clone/retry/completion",false);
    }
    private void windowContext(BlockPos p,BlockState state)throws Exception{
        String id=BuiltInRegistries.BLOCK.getKey(state.getBlock()).toString();if(!id.startsWith("mcwwindows:"))return;
        Property<?> facing=state.getBlock().getStateDefinition().getProperty("facing");
        for(Direction direction:Direction.values()){
            BlockPos outside=p.relative(direction);if(source.containsKey(outside))continue;BlockState neighbor=level.getBlockState(outside);
            if(neighbor.getBlock()!=state.getBlock())continue;
            if(facing!=null&&!neighbor.getValue(facing).equals(state.getValue(facing)))continue;
            BlockPos target=translated(outside);BlockState destinationNeighbor=level.getBlockState(target);
            if(level.getBlockEntity(outside)!=null||level.getBlockEntity(target)!=null||destinationNeighbor.getBlock()!=neighbor.getBlock()
                ||facing!=null&&!destinationNeighbor.getValue(facing).equals(neighbor.getValue(facing))||!destinationNeighbor.getFluidState().isEmpty()){
                JsonObject blocked=new JsonObject();blocked.add("source_context",JSON.toJsonTree(xyz(outside)));blocked.addProperty("source_state",neighbor.toString());
                blocked.add("destination_context",JSON.toJsonTree(xyz(target)));blocked.addProperty("actual_destination_state",destinationNeighbor.toString());report.put("missing_native_window_context",blocked);
                throw new IllegalStateException("Connected MCW window escapes capsule; separately admit/verify genuine matching non-BE destination partners before intent");
            }
        }
    }
'''

def change(s,old,new):
    if s.count(old)!=1:raise RuntimeError('One exact frozen source site required: '+old[:100])
    return s.replace(old,new)

def derive():
    raw=BASE.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=EXPECTED:raise RuntimeError('Frozen R4 changed')
    s=raw.decode();s=change(s,'private static final String CATALOG_SHA="db5e0fa730575ad9b0fd166dd4d52273a5105832d66636d1ca3098693199adf7";',f'private static final String CATALOG_SHA="{CATALOG}";')
    s=change(s,'List.of("inspect","move","inspect-moved")','List.of("inspect","move","inspect-moved","inspect-quarantined","record-conserved")')
    s=change(s,'if(!action.equals("inspect-moved")){proof(', 'if(!action.equals("inspect-moved")&&!action.equals("inspect-quarantined")&&!action.equals("record-conserved")){proof(')
    s=change(s,'    private void atomic(MinecraftServer server)throws Exception{',AUDIT+'\n'+(ROOT/'IndependentCustody.java.inc').read_text()+'\n    private void atomic(MinecraftServer server)throws Exception{\n            if(action.equals("inspect-quarantined")){auditQuarantined(server,true);return;}\n            if(action.equals("record-conserved")){recordConserved(server);return;}')
    s=change(s,'    private void auditQuarantined(MinecraftServer server)throws Exception{','    private JsonObject auditQuarantined(MinecraftServer server,boolean finishAfter)throws Exception{')
    s=change(s,'        finish("read-only actual quarantined-room audit; original failure retained; no clone/retry/completion",false);','        if(finishAfter)finish("read-only actual quarantined-room audit; original failure retained; no clone/retry/completion",false);return selected;')
    s=change(s,'        quarantined=true;JsonObject prior=ref("quarantined_move_terminal",1048576);JsonObject terminalRef=request.getAsJsonObject("quarantined_move_terminal");','        quarantined=true;JsonObject prior=ref("quarantined_move_terminal",1048576);Quarantined.validate(prior,report.get("transaction_id").toString(),capsuleId);JsonObject terminalRef=request.getAsJsonObject("quarantined_move_terminal");')
    s=change(s,'            BlockPos p=e.getKey();BlockState s=e.getValue();if(!s.getFluidState().isEmpty())','            BlockPos p=e.getKey();BlockState s=e.getValue();windowContext(p,s);if(!s.getFluidState().isEmpty())')
    s=change(s,'            bytes+=JSON.toJson(r).getBytes(StandardCharsets.UTF_8).length;', '            if(action.equals("inspect-quarantined"))report.put("current_partial_native_snapshots",out);\n            bytes+=JSON.toJson(r).getBytes(StandardCharsets.UTF_8).length;')
    s=change(s,'"net.mehvahdjukaar.supplementaries.common.block.tiles.BookPileBlockTile");','"net.mehvahdjukaar.supplementaries.common.block.tiles.BookPileBlockTile","com.simibubi.create.content.equipment.toolbox.ToolboxBlockEntity");')
    s=change(s,'    private JsonObject request;private String requestSha,action;','    private JsonObject toolboxAudit;\n    private JsonObject request;private String requestSha,action;')
    s=change(s,'!classHash(Uninvoked.class).equals(request.get("uninvoked_class_sha256").getAsString())','!classHash(Uninvoked.class).equals(request.get("uninvoked_class_sha256").getAsString())||!classHash(Quarantined.class).equals(request.get("quarantined_evidence_class_sha256").getAsString())||!classHash(NativeToolboxCustody.class).equals(request.get("toolbox_custody_class_sha256").getAsString())')
    s=change(s,'            CompoundTag full=be.saveWithFullMetadata(level.registryAccess());','            JsonObject toolbox=null;\n            if(be instanceof com.simibubi.create.content.equipment.toolbox.ToolboxBlockEntity actual){if(!pin.has("IItemHandler")||!pin.get("IItemHandler").getAsBoolean())throw new IllegalStateException("Explicit native toolbox handler role required");toolbox=NativeToolboxCustody.capture(actual,this::stack);}\n            else if(pin.has("IItemHandler")&&pin.get("IItemHandler").getAsBoolean())throw new IllegalStateException("Unexpected native handler role");\n            CompoundTag full=be.saveWithFullMetadata(level.registryAccess());')
    s=change(s,'            else if(be instanceof LecternBlockEntity lectern)', '            else if(toolbox!=null){r.add("native_toolbox_handler",toolbox);}\n            else if(be instanceof LecternBlockEntity lectern)')
    s=change(s,'    private JsonArray snapshots(boolean moved)throws Exception{\n        JsonArray out=new JsonArray();int bytes=0;','''    private void toolboxProfiles()throws Exception{
        if(toolboxAudit==null)return;
        BlockPos found=null;for(var e:expectedTags.entrySet())if(e.getValue().getString("id").equals("create:toolbox")){if(found!=null)throw new IllegalStateException("One exact toolbox role per capsule");found=e.getKey();}
        if(found==null)throw new IllegalStateException("Missing actual toolbox source");
        NativeToolboxCustody.profiles(level.getServer().getWorldPath(LevelResource.ROOT).toRealPath(),toolboxAudit,request.get("backup_sha256").getAsString(),found,translated(found));
    }
    private JsonArray snapshots(boolean moved)throws Exception{
        toolboxProfiles();JsonArray out=new JsonArray();int bytes=0;''')
    s=change(s,'            if(a.get("is_Container").getAsBoolean()){','            if(a.has("native_toolbox_handler")!=b.has("native_toolbox_handler")||a.has("native_toolbox_handler")&&!a.get("native_toolbox_handler").equals(b.get("native_toolbox_handler")))throw new IllegalStateException("Actual native toolbox32 slots/8 filters/UUID/connection state changed");\n            if(a.get("is_Container").getAsBoolean()){')
    s=change(s,'||catalog.getAsJsonArray("capsules").size()!=93)', '||catalog.getAsJsonArray("capsules").size()!=98||!catalog.get("inherited_original_catalog_sha256").getAsString().equals("db5e0fa730575ad9b0fd166dd4d52273a5105832d66636d1ca3098693199adf7")||!catalog.get("allocation_addendum_sha256").getAsString().equals("517c1dab4c9d467fe8d072d86b5fb759aab51d493b6c6b229cde43849457bf18"))')
    s=change(s,'catalog.get("format").getAsString().equals("awft-approved-eastern-relocation-catalog:2")','catalog.get("format").getAsString().equals("awft-approved-eastern-relocation-catalog:5")')
    s=change(s,'            int count=Math.multiplyExact(', '            boolean overlaps=true;for(int i=0;i<3;i++)overlaps&=a[i]<=b[i+3]&&b[i]<=a[i+3];if(overlaps)throw new IllegalStateException("Source/destination self-overlap cannot satisfy sourceAIR and destination preservation; genuinely disjoint allocation required");\n            int count=Math.multiplyExact(')
    s=change(s,'        lease=interlock.acquire("relocation:"+stable,true);','''        if(catalogRow.has("prior_translation_xyz")){
            JsonArray previous=catalogRow.getAsJsonArray("prior_translation_xyz");String old=sha((home.toRealPath()+"|"+BASELINE+"|"+Capsules.salt(capsuleId,Capsules.integer(previous.get(0)),Capsules.integer(previous.get(1)),Capsules.integer(previous.get(2)))).getBytes(StandardCharsets.UTF_8));
            if(!old.equals(stable)&&Files.exists(server.getWorldPath(LevelResource.ROOT).toRealPath().resolve("data/awft-relocations/"+old),LinkOption.NOFOLLOW_LINKS))
                throw new IllegalStateException("Reallocation cannot bypass any old transaction ledger; explicit reconciliation required");
        }
        toolboxAudit=null;
        if(catalogRow.has("requires_toolbox_native_handler_and_saved_profile_custody")&&catalogRow.get("requires_toolbox_native_handler_and_saved_profile_custody").getAsBoolean()){
            NativeToolboxCustody.pins(request.getAsJsonObject("toolbox_api_class_sha256"));toolboxAudit=ref("toolbox_saved_player_custody",65536);toolboxProfiles();
        }else if(request.has("toolbox_saved_player_custody"))throw new IllegalStateException("Foreign toolbox authority on unrelated room");
        lease=interlock.acquire("relocation:"+stable,true);''')
    a=s.index('            byte[] raw=bytes(path.resolve("completed.json"),1048576);',s.index('    private void dependencies()'))
    b=s.index('\n        }\n    }',a);s=s[:a]+'            completedCustody(path,key);'+s[b:]
    a=s.index('                byte[] doneBytes=bytes(ledger.resolve("completed.json"),1048576);',s.index('    private void atomic('))
    b=s.index('\n                for(BlockPos p:source.keySet())',a);s=s[:a]+'                JsonObject done=completedCustody(ledger,report.get("transaction_id").toString());'+s[b:]
    (ROOT/'NativeRelocationSupport.java').write_text(s,encoding='utf8',newline='\n');print(hashlib.sha256((ROOT/'NativeRelocationSupport.java').read_bytes()).hexdigest())

if __name__=='__main__':derive()
