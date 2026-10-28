"""Original source-only4000 population/64-member cohort extension.

Preserves legacy64 and all native factory/spawn/AI/POI/identity guards. No actors
or authority are manufactured and no active source, game or ledger is changed.
"""
from pathlib import Path
import difflib,json
from control_room.common import UserError,digest,utcnow
from tools.playtest import guard

BASE='f7bcc9844ea6b25bab24349b8f7c9030b6feaef764b03ebb0557509a6687678a'


def once(text,old,new):
    if text.count(old)!=1:raise UserError('Frozen LIFE boundary differs: '+old[:95])
    return text.replace(old,new)


FIELDS='''
    private boolean scaledPopulation,scaleProjectionReady;
    private int cohortLimit=MAX_MEMBERS,blockLimit=MAX_BLOCKS,planByteLimit=MAX_PLAN;
    private ScaledLifeBudget scaleBudget;
    private JsonObject scaleSpec;
    private BasicFileAttributes scaleLedgerStamp;
    private final Map<String,Integer> scaleCounts=new HashMap<>(),scaleHabitats=new HashMap<>();
    private final Map<String,Integer> savedHabitatEntities=new HashMap<>();
    private final Set<UUID> cohortAddedUUIDs=new HashSet<>();
    private record ScaleIntentStamp(Path path,BasicFileAttributes attributes) {}
    private final List<ScaleIntentStamp> scaleIntentStamps=new ArrayList<>();
    private int scaleAuditCursor;
    private boolean scaleAuditComplete;
'''

AUTHORITY='''        if(scaledPopulation){
            nativeCode(ScaledLifeBudget.class,request.get("native_scale_policy_sha256").getAsString());
            if(!plan.get("population_budget_sha256").getAsString().equals(reference("population_budget").get("sha256").getAsString()))
                throw new IllegalStateException("Exact reviewed scaled population budget required");
            scaleSpec=read(reference("population_budget"),128*1024);
            if(!scaleSpec.get("seed").getAsString().equals(plan.get("seed").getAsString())
                ||!scaleSpec.get("world_path").getAsString().equals(plan.get("world_path").getAsString()))throw new IllegalStateException("Scaled budget belongs to another actual world");
            JsonObject ramp=read(reference("population_ramp"),128*1024);
            scaleBudget=new ScaledLifeBudget(scaleSpec,ramp,namespace,HabitatLifePolicy.CURATION_SHA256,
                request.get("checkpoint_sha256").getAsString(),recipeSha,reference("population_budget").get("sha256").getAsString());
            if(ramp.getAsJsonArray("native_measurement_refs").size()>8)throw new IllegalStateException("Finite real ramp measurement references required");
            for(JsonElement value:ramp.getAsJsonArray("native_measurement_refs")){
                JsonObject ref=value.getAsJsonObject();byte[] measurementBytes=bounded(owned(ref.get("path").getAsString()),2*1024*1024);
                if(measurementBytes.length!=ref.get("bytes").getAsInt()||!sha(measurementBytes).equals(ref.get("sha256").getAsString()))throw new IllegalStateException("Actual reviewed ramp measurement bytes differ");
            }
            report.put("explicit_managed_population_maximum",4000);report.put("cohort_maximum",64);report.put("reviewed_ramp_ceiling",scaleBudget.ramp());
            report.put("normal_native_AI_required",true);report.put("population_scale_native_performance_acceptance",false);
        }
'''

METHODS='''
    private void scaleLedgerSlice()throws Exception{
        requireScaleStamp();long start=System.nanoTime();int work=0;
        while(scaleAuditCursor<scaleIntentStamps.size()&&work++<256&&System.nanoTime()-start<2_000_000L){
            ScaleIntentStamp row=scaleIntentStamps.get(scaleAuditCursor++);
            if(!sameFile(row.attributes,Files.readAttributes(row.path,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS)))
                throw new IllegalStateException("Retained immutable population intent changed during the cohort lease");
        }
        if(scaleAuditCursor==scaleIntentStamps.size()){scaleAuditComplete=true;scaleAuditCursor=0;}
    }
    private static String tile(double x,double z){return Math.floorDiv((int)Math.floor(x),32)+"|"+Math.floorDiv((int)Math.floor(z),32);}
    private void scaledCrowding(Resident member){
        if(!scaledPopulation)return;
        String key=tile(member.x,member.z);Integer saved=savedHabitatEntities.get(key);
        if(saved==null)throw new IllegalStateException("Complete actual stopped habitat census omitted this tile");
        int projected=0;for(var entry:scaleHabitats.entrySet())if(entry.getKey().substring(entry.getKey().indexOf('|')+1).equals(key))projected+=entry.getValue();
        int loaded=0,newMembers=0;
        for(Entity entity:level.getAllEntities())if(!entity.isRemoved()&&!cohortAddedUUIDs.contains(entity.getUUID())&&tile(entity.getX(),entity.getZ()).equals(key))loaded++;
        for(Resident row:residents)if(tile(row.x,row.z).equals(key))newMembers++;
        // Saved ALL entities plus projected managed intents deliberately double
        // counts some retained actors: conservative occupancy, not a fake census.
        // A second current loaded census catches later unmanaged arrivals.
        int bound=Math.max(Math.addExact(saved,projected),Math.addExact(loaded,newMembers));
        if(bound>scaleBudget.habitatCap(member.site.kind.name()))throw new IllegalStateException("Actual saved/current/conservative managed habitat occupancy exceeds reviewed local cap");
    }
    private void scaleStamp()throws Exception{
        scaleLedgerStamp=Files.exists(ledger,LinkOption.NOFOLLOW_LINKS)?Files.readAttributes(ledger,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS):null;
    }
    private void requireScaleStamp()throws Exception{
        boolean exists=Files.exists(ledger,LinkOption.NOFOLLOW_LINKS);
        if(exists!=(scaleLedgerStamp!=null)||exists&&!sameFile(scaleLedgerStamp,Files.readAttributes(ledger,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS)))
            throw new IllegalStateException("Private LIFE ledger changed outside this cohort's own durable writes");
    }
    private void scaledPopulation(boolean create)throws Exception{
        Path root=ledger.getParent(),original=root.resolve("population.json"),overlay=root.resolve("scale-budget.json");
        if(!Files.isRegularFile(original,LinkOption.NOFOLLOW_LINKS)
            ||!sha(bounded(original,8192)).equals(scaleBudget.originalIdentitySha()))
            throw new IllegalStateException("Preserve exact original world population identity; no new namespace or implicit migration");
        if(!JsonParser.parseString(new String(bounded(original,8192),StandardCharsets.UTF_8)).getAsJsonObject().equals(populationIdentity()))
            throw new IllegalStateException("Original legacy identity differs; do not rewrite it");
        if(Files.exists(overlay,LinkOption.NOFOLLOW_LINKS)
            &&!JsonParser.parseString(new String(bounded(overlay,128*1024),StandardCharsets.UTF_8)).getAsJsonObject().equals(scaleBudget.identity()))
            throw new IllegalStateException("Retained explicit scaled budget differs; no automatic authority replacement");
        if(scaleProjectionReady){
            requireScaleStamp();scaleBudget.check(scaleCounts,scaleHabitats);
            if(create&&!Files.exists(overlay,LinkOption.NOFOLLOW_LINKS)){dataWriteAttempted=true;durable(overlay,scaleBudget.identity());populationAuthoritiesWritten++;}
            return;
        }
        if(!Files.isDirectory(root,LinkOption.NOFOLLOW_LINKS)||Files.isSymbolicLink(root))throw new IllegalStateException("Ordinary retained population directory required");
        int directories=0;try(var entries=Files.newDirectoryStream(root)){for(Path path:entries){
            if(++directories>3||Files.isSymbolicLink(path)||!path.equals(original)&&!path.equals(overlay)&&!path.equals(ledger))
                throw new IllegalStateException("Preserve foreign population namespace/authority for review");
        }}
        Map<BlockPos,UUID> beds=new HashMap<>(),jobs=new HashMap<>();int retained=0;
        if(Files.exists(ledger))try(var files=Files.newDirectoryStream(ledger,"*.intent.json")){for(Path path:files){
            if(++retained>4000||Files.isSymbolicLink(path))throw new IllegalStateException("Actual retained4000 managed-intent budget exceeded");
            BasicFileAttributes stamp=Files.readAttributes(path,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
            JsonObject value=JsonParser.parseString(new String(bounded(path,8192),StandardCharsets.UTF_8)).getAsJsonObject();
            if(!sameFile(stamp,Files.readAttributes(path,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS)))throw new IllegalStateException("Retained intent changed during exact population scan");
            scaleIntentStamps.add(new ScaleIntentStamp(path,stamp));
            String id=value.get("entity").getAsString(),kind=value.get("habitat_kind").getAsString();
            HabitatLifePolicy.species(id,value.get("native_class").getAsString(),value.get("native_category").getAsString(),kind);
            if(!value.get("format").getAsString().equals("awft-life-world-intent:2")||!value.get("population_namespace").getAsString().equals(namespace))throw new IllegalStateException("Retain unknown legacy intent; never adopt another population");
            JsonArray feet=value.getAsJsonArray("feet");if(feet.size()!=3)throw new IllegalStateException("Typed retained native position required");
            scaleCounts.merge(id,1,Integer::sum);scaleHabitats.merge(ScaledLifeBudget.habitat(kind,feet.get(0).getAsDouble(),feet.get(2).getAsDouble()),1,Integer::sum);
            if(kind.equals("HOME")){
                UUID owner=UUID.fromString(value.get("uuid").getAsString());
                if(beds.put(point(value.get("planned_bed")),owner)!=null||jobs.put(point(value.get("planned_job")),owner)!=null)throw new IllegalStateException("Preserve retained bed/job claims; never overbook POIs");
            }
        }}
        for(Resident row:residents){
            if(row.site.bed!=null){UUID bedOwner=beds.get(row.site.bed),jobOwner=jobs.get(row.site.job);
                if(bedOwner!=null&&!bedOwner.equals(row.uuid)||jobOwner!=null&&!jobOwner.equals(row.uuid))throw new IllegalStateException("A retained villager already owns this planned HOME POI");}
            if(!hasIntent(row)){scaleCounts.merge(row.id,1,Integer::sum);scaleHabitats.merge(ScaledLifeBudget.habitat(row.site.kind.name(),row.x,row.z),1,Integer::sum);}
        }
        scaleBudget.check(scaleCounts,scaleHabitats);scaleProjectionReady=true;scaleStamp();
        report.put("retained_intents_at_cohort_admission",retained);
        report.put("projected_managed_population_if_cohort_complete",scaleCounts.values().stream().mapToInt(Integer::intValue).sum());
        report.put("actual_ambient_unmanaged_population_included_in_this_budget",false);
        if(create){dataWriteAttempted=true;durable(overlay,scaleBudget.identity());populationAuthoritiesWritten++;}
    }
'''


def transform(old):
    text=once(old,'    private TownLifeAuthority townAuthority;','    private TownLifeAuthority townAuthority;'+FIELDS)
    text=once(text,'        report.clear();observed.clear();','        scaledPopulation=scaleProjectionReady=scaleAuditComplete=false;scaleAuditCursor=0;scaleIntentStamps.clear();cohortLimit=MAX_MEMBERS;blockLimit=MAX_BLOCKS;planByteLimit=MAX_PLAN;scaleBudget=null;scaleSpec=null;scaleLedgerStamp=null;scaleCounts.clear();scaleHabitats.clear();savedHabitatEntities.clear();cohortAddedUUIDs.clear();\n        report.clear();observed.clear();')
    text=once(text,'        if(!request.get("format").getAsString().equals("awft-native-habitat-life:3")',
        '''        scaledPopulation=request.get("format").getAsString().equals("awft-native-habitat-life:4");
        if(scaledPopulation){cohortLimit=64;blockLimit=262144;planByteLimit=32*1024*1024;}
        if(!(request.get("format").getAsString().equals("awft-native-habitat-life:3")||scaledPopulation)''')
    text=once(text,'plan=read(reference("recipe"),MAX_PLAN)','plan=read(reference("recipe"),planByteLimit)')
    text=once(text,'!plan.get("format").getAsString().equals("awft-habitat-life-recipe:3")',
        '!plan.get("format").getAsString().equals(scaledPopulation?"awft-habitat-life-recipe:4":"awft-habitat-life-recipe:3")')
    text=once(text,'JsonObject woodland=read(reference("woodland"),4*1024*1024);',
        'JsonObject woodland=read(reference("woodland"),scaledPopulation?16*1024*1024:4*1024*1024);')
    text=once(text,'        for(JsonElement node:woodland.getAsJsonArray("bank_nodes_xz"))',
        '''        if(scaledPopulation&&(!woodland.get("format").getAsString().equals("awft-measured-south-life-extent:1")
            ||!woodland.get("checkpoint_sha256").getAsString().equals(request.get("checkpoint_sha256").getAsString())
            ||!woodland.get("eastmost_north_land_edge_measured").getAsBoolean()
            ||!woodland.get("connected_south_shore_to_cliff_foot_measured").getAsBoolean()
            ||woodland.get("eligibility_stride_metres").getAsInt()!=1))throw new IllegalStateException("Actual expanded1m habitat extent required; no old clipped coordinate fallback");
        for(JsonElement node:woodland.getAsJsonArray("bank_nodes_xz"))''')
    text=text.replace('bankColumns.size()>8192','bankColumns.size()>(scaledPopulation?500000:8192)')
    text=once(text,'        if(!plan.get("curation_sha256").getAsString().equals(HabitatLifePolicy.CURATION_SHA256))throw new IllegalStateException("Exact reviewed16-species curation required");',
        '        if(!plan.get("curation_sha256").getAsString().equals(HabitatLifePolicy.CURATION_SHA256))throw new IllegalStateException("Exact reviewed16-species curation required");\n'+AUTHORITY)
    text=text.replace('censusMembers.size()>MAX_MEMBERS','censusMembers.size()>cohortLimit').replace('members.size()>MAX_MEMBERS','members.size()>cohortLimit').replace('++cells>MAX_BLOCKS','++cells>blockLimit').replace('rows.size()>MAX_BLOCKS','rows.size()>blockLimit')
    text=text.replace('A finite LIFE batch has 1..16 members','Finite legacy1..16 or explicitly scaled1..64 LIFE members required')
    text=text.replace('habitatPlan=read(reference("habitat_plan"),MAX_PLAN)','habitatPlan=read(reference("habitat_plan"),planByteLimit)')
    text=text.replace('if(town)HabitatLifePolicy.coordinateTown','if(town||scaledPopulation)HabitatLifePolicy.coordinateTown')
    text=text.replace('if(town){HabitatLifePolicy.coordinateTown(habitat.minX','if(town||scaledPopulation){HabitatLifePolicy.coordinateTown(habitat.minX')
    text=once(text,'Math.abs(ax-Math.floor(x))>16||Math.abs(az-Math.floor(z))>16',
        'Math.abs(ax-Math.floor(x))>(scaledPopulation?0:16)||Math.abs(az-Math.floor(z))>(scaledPopulation?0:16)')
    text=once(text,'            JsonArray box=row.getAsJsonArray("roam_bounds");',
        '''            if(scaledPopulation&&!town)for(int xx=site.known.minX();xx<=site.known.maxX();xx++)for(int zz=site.known.minZ();zz<=site.known.maxZ();zz++)
                if(!bankColumns.contains(column(xx,zz)))throw new IllegalStateException("Complete scaled habitat field crosses unmeasured eligible land/water");
            JsonArray box=row.getAsJsonArray("roam_bounds");''')
    text=once(text,'routes.size(),town);','routes.size(),town||scaledPopulation);')
    text=text.replace('if(++count>1024||Files.isSymbolicLink(file)','if(++count>(scaledPopulation?8016:1024)||Files.isSymbolicLink(file)')
    text=once(text,'        population(false);',
        '''        if(scaledPopulation){
            JsonObject aggregate=read(reference("habitat_census"),512*1024);
            if(!aggregate.get("format").getAsString().equals("awft-stopped-world-habitat-census:1")
                ||!aggregate.get("checkpoint_sha256").getAsString().equals(request.get("checkpoint_sha256").getAsString())
                ||!aggregate.get("recipe_sha256").getAsString().equals(recipeSha)||!aggregate.get("all_world_entity_regions_scanned").getAsBoolean())
                throw new IllegalStateException("Exact current complete stopped habitat entity census required");
            for(JsonElement value:aggregate.getAsJsonArray("tiles")){
                JsonObject row=value.getAsJsonObject();JsonArray p=row.getAsJsonArray("tile_xz");
                if(p.size()!=2||savedHabitatEntities.size()>=64)throw new IllegalStateException("Finite per-cohort habitat census required");
                int count=literal(row.get("saved_entity_count"));String key=literal(p.get(0))+"|"+literal(p.get(1));
                if(count<0||count>100000||savedHabitatEntities.put(key,count)!=null)throw new IllegalStateException("Unknown or duplicate saved habitat count");
            }
            for(Resident row:residents)if(!savedHabitatEntities.containsKey(tile(row.x,row.z)))throw new IllegalStateException("Actual habitat census omitted a requested member tile");
        }
        population(false);''')
    text=once(text,'    private void population(boolean create)throws Exception{','    private void population(boolean create)throws Exception{\n        if(scaledPopulation){scaledPopulation(create);return;}')
    text=once(text,'    @SuppressWarnings({"rawtypes","unchecked"}) private static BlockState parse',METHODS+'\n    @SuppressWarnings({"rawtypes","unchecked"}) private static BlockState parse')
    text=once(text,'    private Mob preview(Resident row)throws Exception{','    private Mob preview(Resident row)throws Exception{\n        scaledCrowding(row);')
    text=once(text,'            // No resetEmptyTime: this helper does not manufacture AI progress.',
        '            if(scaledPopulation&&scaleProjectionReady)scaleLedgerSlice();\n            // No resetEmptyTime: this helper does not manufacture AI progress.')
    text=once(text,'            if(phase==Phase.WORK){Resident row=',
        '            if(phase==Phase.WORK&&scaledPopulation&&!scaleAuditComplete)return;\n            if(phase==Phase.WORK){Resident row=')
    line='durable(ledger.resolve(row.uuid+".admitted.json"),admitted);observed.add('
    text=once(text,line,'durable(ledger.resolve(row.uuid+".admitted.json"),admitted);if(scaledPopulation){cohortAddedUUIDs.add(row.uuid);scaleStamp();}observed.add(')
    text=once(text,'if(phase==Phase.CLEANUP){pending.removeIf(CompletableFuture::isDone);if(tickets.isEmpty()&&pending.isEmpty())cleanup(false);return;}',
        'if(phase==Phase.CLEANUP){cleanup(true);return;}')
    text=once(text,'        try{if(clean||!cleanupPublished){NativeJournal.progress(journal,"life-status.json",report);NativeJournal.terminal(journal,"habitat-life",report);cleanupPublished=true;}}catch(Exception error){System.err.println("AWFT LIFE journal: "+error);}\n        if(clean){phase=Phase.IDLE;previews.clear();}',
        '''        if(clean&&!cleanupPublished)try{NativeJournal.terminal(journal,"habitat-life",report);cleanupPublished=true;}catch(Exception error){report.put("terminal_publication_blocked",error.toString());}
        try{NativeJournal.progress(journal,"life-status.json",report);}catch(Exception error){report.put("progress_publication_warning",error.toString());}
        if(clean&&cleanupPublished){phase=Phase.IDLE;previews.clear();}''')
    return text


def prepare():
    root=Path(__file__).resolve().parents[1];base=root/'compat/proposals/life-spawn-diagnostics-r1/NativeHabitatLifeSupport.java'
    output=root/'compat/proposals/life-scale49'
    if digest(base)!=BASE:raise UserError('Exact frozen diagnostic-only48 LIFE base required')
    if(output/'NativeHabitatLifeSupport.java').exists():raise UserError('Preserve proposed original; no automatic rebase')
    reserve=guard(8*1024**2,0);output.mkdir(exist_ok=True);old=base.read_text();text=transform(old)
    (output/'NativeHabitatLifeSupport48-diagnostic-base.java.txt').write_bytes(base.read_bytes())
    (output/'NativeHabitatLifeSupport.java').write_text(text,encoding='utf-8',newline='\n')
    patch=''.join(difflib.unified_diff(old.splitlines(True),text.splitlines(True),fromfile='frozen48-diagnostics/NativeHabitatLifeSupport.java',tofile='proposal/NativeHabitatLifeSupport.java'))
    (output/'integration.diff').write_text(patch,encoding='utf-8',newline='\n')
    (output/'initial-custody.json').write_text(json.dumps({'format':'awft-scaled-LIFE-source:1','created':utcnow(),'base_sha256':BASE,'generator_sha256':digest(Path(__file__)),'reserve_guard':reserve,'native_actions':0,'API_compile':'PENDING'},indent=2)+'\n',encoding='utf-8')
    return {'output':str(output),'proposed_sha256':digest(output/'NativeHabitatLifeSupport.java')}


if __name__=='__main__':print(json.dumps(prepare(),indent=2))
