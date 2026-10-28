"""Exact-source v3 LIFE extension recipe; no active source or runtime changes."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'native44'
PINS={'NativeHabitatLifeSupport.java':'177debd09313941d947e57f98a37ec289cafdcddc396c540891947aa0b11620b',
      'HabitatLifePolicy.java':'a1a026a14d1b772d40fd62eca08f6280bc37d71247921fe6785ac1dd36ff1d40',
      'prepare.py':'88a80a1211119357a04141a650dac2234b2d719ce8c49c156d875acb0383c6f6'}


def replace(text,before,after,count=1):
    if text.count(before)!=count:raise ValueError('Frozen native44 anchor changed: '+before[:90])
    return text.replace(before,after)


def producer_source():
    raw=(BASE/'prepare.py').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PINS['prepare.py']:raise ValueError('Frozen producer changed')
    text=raw.decode()
    text=replace(text,'from tools.settlement_attractions import BackupWorld, base',
                 'from tools.settlement_attractions import BackupWorld, base\nsys.path.insert(0,str(Path(__file__).resolve().parent))\nimport town_authority as town')
    text=replace(text,"'awft-life-sites:2'","'awft-life-sites:3'")
    text=replace(text,"'awft-habitat-life-recipe:2'","'awft-habitat-life-recipe:3'",2)
    text=replace(text,"'awft-native-habitat-life:2'","'awft-native-habitat-life:3'")
    text=replace(text,'def members(sites, data, registry, bank, snapshot, protected):','def members(sites, data, registry, bank, snapshot, protected, towns=None):')
    text=replace(text,"        if set(site) != {'name','entity','feet','roam_bounds','habitat','bank_anchor'}:",
                 "        is_town='town_site' in site\n        if is_town==('bank_anchor' in site):raise UserError('Exactly one typed town or woodland authority required')\n        if set(site) != {'name','entity','feet','roam_bounds','habitat',('town_site' if is_town else 'bank_anchor')}:")
    text=replace(text,"bounds = habitat['known_bounds']; count = box(bounds); total += count", "bounds = habitat['known_bounds']; count = town.town_box(bounds) if is_town else box(bounds); total += count")
    text=replace(text,"        if not all(math.isfinite(v) for v in feet) or not 912 <= math.floor(feet[0]) <= 1352 or not -1200 <= math.floor(feet[2]) <= -616 or not 48 <= feet[1] <= 240:\n            raise UserError('Outside the actual finite shore-to-cliff study')",
                 "        if not all(math.isfinite(v) for v in feet) or not 48<=feet[1]<=240:raise UserError('Finite native habitat coordinate required')\n        if is_town:\n            if abs(feet[0])>30000000 or abs(feet[2])>30000000:raise UserError('Finite native town coordinate required')\n        elif not 912<=math.floor(feet[0])<=1352 or not -1200<=math.floor(feet[2])<=-616:raise UserError('Outside actual woodland study')")
    text=replace(text,"        anchor = tuple(site['bank_anchor'])\n        if anchor not in nodes or abs(anchor[0]-feet[0]) > 16 or abs(anchor[1]-feet[2]) > 16:\n            raise UserError('Actual connected-bank anchor required; rectangle is not authority')\n        snapshot.chunk(anchor[0]//16,anchor[1]//16)  # Saved FULL source, not map interpolation.",
                 "        source=town.member(towns or {},site,feet,bounds) if is_town else None\n        anchor=None\n        if not is_town:\n            anchor=tuple(site['bank_anchor'])\n            if anchor not in nodes or abs(anchor[0]-feet[0])>16 or abs(anchor[1]-feet[2])>16:raise UserError('Actual connected-bank anchor required; rectangle is not authority')\n            snapshot.chunk(anchor[0]//16,anchor[1]//16)")
    text=replace(text,"                occupied.add((pos[0],pos[2]))", "                if source is not None:town.cell(source,pos)\n                occupied.add((pos[0],pos[2]))")
    text=replace(text,"                occupied.update((pos[0]+dx,pos[2]+dz) for dx in (-1,0,1) for dz in (-1,0,1))", "                if source is not None:town.route(source,pos)\n                occupied.update((pos[0]+dx,pos[2]+dz) for dx in (-1,0,1) for dz in (-1,0,1))")
    text=replace(text,"        if occupied & protected: raise UserError('Retain R5/plumbing/views, machine/navigation and future cable protection')", "                if source is not None:town.cell(source,pos)\n        if occupied & protected: raise UserError('Retain R5/plumbing/views, machine/navigation and future cable protection')")
    text=replace(text,"'habitat':habitat,'bank_anchor':list(anchor)})", "'habitat':habitat,**({'town_site':site['town_site']} if is_town else {'bank_anchor':list(anchor)})})")
    text=replace(text,"retained_recipe=None, operation='inspect', life_ready=None, native_verify=None):", "retained_recipe=None, operation='inspect', life_ready=None, native_verify=None, town_authority=None):")
    text=replace(text,"    protected = protection(home,registry,r5_mask,safety_index)", "    protected = protection(home,registry,r5_mask,safety_index)\n    town_doc,towns=town.read_authority(home,registry,town_authority,bounded,owned,KINDS)")
    text=replace(text,"                if row['entity'] not in KINDS: raise UserError('Unreviewed retained species')", "                if row['entity'] not in KINDS: raise UserError('Unreviewed retained species')\n                for x,y,z,state in row['preimage']:\n                    if snapshot.state((x,y,z))!=state:raise UserError('Current stopped FULL habitat differs; preserve original resident/intent, no silent recipe replacement')")
    text=replace(text,"namespace,residents = members(bounded(sites,256*1024),data,registry,bank,snapshot,protected)", "namespace,residents = members(bounded(sites,256*1024),data,registry,bank,snapshot,protected,towns)")
    text=replace(text,"        raw_recipe = encoded(recipe); recipe_sha = hashlib.sha256(raw_recipe).hexdigest()", """        if any('town_site' in row for row in recipe['members']):
            if town_doc is None:raise UserError('Actual typed authored-town authority required')
            authority_sha=digest(Path(town_authority))
            if retained_recipe and (recipe.get('town_authority_sha256')!=authority_sha or recipe.get('town_authority_source_checkpoint_sha256')!=town_doc['source_checkpoint_sha256']):raise UserError('Retained town authority must remain byte-identical for durable identity')
            recipe.update(town_authority_sha256=authority_sha,town_authority_source_checkpoint_sha256=town_doc['source_checkpoint_sha256'])
        raw_recipe = encoded(recipe); recipe_sha = hashlib.sha256(raw_recipe).hexdigest()""")
    text=replace(text,"for filename in ('NativeHabitatLifeSupport.class','HabitatLifePolicy.class'):", "for filename in ('NativeHabitatLifeSupport.class','HabitatLifePolicy.class','TownLifeAuthority.class'):")
    text=replace(text,"'native_class_sha256':digest(classes/'NativeHabitatLifeSupport.class'),'native_policy_sha256':digest(classes/'HabitatLifePolicy.class'),", "'native_class_sha256':digest(classes/'NativeHabitatLifeSupport.class'),'native_policy_sha256':digest(classes/'HabitatLifePolicy.class'),'native_town_authority_sha256':digest(classes/'TownLifeAuthority.class'),")
    text=replace(text,"    if operation == 'seed':", "    if 'town_authority_sha256' in recipe:request['town_authority']=owned(home,town_authority)\n    if operation == 'seed':")
    text=replace(text,"('sites','retained-recipe','life-ready','native-verify')", "('sites','retained-recipe','life-ready','native-verify','town-authority')")
    return text.encode()


def sources():
    docs={}
    for name,pin in PINS.items():
        raw=(BASE/name).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=pin:raise ValueError('Frozen079e source changed: '+name)
        docs[name]=raw.decode()
    policy=docs['HabitatLifePolicy.java']
    anchor='    public static void geometry(Species p,Box known,Box water,boolean hasBed,boolean hasJob,int routes){\n        known(known);'
    policy=replace(policy,anchor,'''    public static void coordinateTown(double x,double y,double z){
        if(!Double.isFinite(x)||!Double.isFinite(y)||!Double.isFinite(z)||Math.abs(x)>30000000||Math.abs(z)>30000000||y<48||y>240)
            throw new IllegalStateException("Finite native town coordinate required; explicit authored authority still mandatory");
    }
    public static void knownTown(Box b){
        if(b.minX>b.maxX||b.minY>b.maxY||b.minZ>b.maxZ||Math.abs((long)b.minX)>30000000||Math.abs((long)b.maxX)>30000000
            ||Math.abs((long)b.minZ)>30000000||Math.abs((long)b.maxZ)>30000000||b.minY< -64||b.maxY>319||b.volume()<1||b.volume()>MAX_WITNESS_CELLS)
            throw new IllegalStateException("Complete finite native town FULL field required; a rectangle alone gives no admission");
    }
    public static void geometry(Species p,Box known,Box water,boolean hasBed,boolean hasJob,int routes){geometry(p,known,water,hasBed,hasJob,routes,false);}
    public static void geometry(Species p,Box known,Box water,boolean hasBed,boolean hasJob,int routes,boolean town){
        if(town)knownTown(known);else known(known);''')
    native=docs['NativeHabitatLifeSupport.java']
    for old,new in [('awft-native-habitat-life:2','awft-native-habitat-life:3'),('awft-habitat-life-recipe:2','awft-habitat-life-recipe:3')]:native=replace(native,old,new)
    native=replace(native,'private String action,outcome,recipeSha,namespace;','private String action,outcome,recipeSha,namespace;\n    private TownLifeAuthority townAuthority;\n    private final Map<UUID,TownLifeAuthority.Site> townResidents=new HashMap<>();')
    native=replace(native,'report.clear();observed.clear();','report.clear();observed.clear();townAuthority=null;townResidents.clear();')
    native=replace(native,'nativeCode(HabitatLifePolicy.class,request.get("native_policy_sha256").getAsString());',
                   'nativeCode(HabitatLifePolicy.class,request.get("native_policy_sha256").getAsString());nativeCode(TownLifeAuthority.class,request.get("native_town_authority_sha256").getAsString());')
    native=replace(native,'        namespace=UUID.fromString(plan.get("population_namespace").getAsString()).toString();','''        if(request.has("town_authority")!=plan.has("town_authority_sha256"))throw new IllegalStateException("Town source authority must be explicit in request and immutable recipe");
        if(request.has("town_authority")){
            if(!reference("town_authority").get("sha256").getAsString().equals(plan.get("town_authority_sha256").getAsString()))throw new IllegalStateException("Town authority differs from retained recipe");
            townAuthority=new TownLifeAuthority(read(reference("town_authority"),4*1024*1024),plan.get("seed").getAsString(),plan.get("world_path").getAsString(),plan.get("town_authority_source_checkpoint_sha256").getAsString(),this::read,
                ref->{Path file=owned(ref.get("path").getAsString());String complete=new String(bounded(file.resolveSibling(file.getFileName()+".complete"),128),StandardCharsets.UTF_8).strip();if(!complete.equals(ref.get("sha256").getAsString()))throw new IllegalStateException("Authored source native completion digest differs");});
        }
        namespace=UUID.fromString(plan.get("population_namespace").getAsString()).toString();''')
    old='            if(!Set.of("uuid","entity","native_class","native_MobCategory","member_tag","feet","roam_bounds","source_group_id","preimage","habitat","bank_anchor").equals(row.keySet()))throw new IllegalStateException("No extra entity NBT, ownership, NoAI or passenger fields admitted");'
    native=replace(native,old,'''            boolean town=row.has("town_site");if(town==row.has("bank_anchor"))throw new IllegalStateException("Exactly one typed WOODLAND or TOWN source authority required");
            Set<String> memberKeys=new HashSet<>(Set.of("uuid","entity","native_class","native_MobCategory","member_tag","feet","roam_bounds","source_group_id","preimage","habitat"));memberKeys.add(town?"town_site":"bank_anchor");
            if(!memberKeys.equals(row.keySet()))throw new IllegalStateException("No extra entity NBT, ownership, NoAI, passenger or untyped source authority admitted");''')
    native=replace(native,'parseHabitat(id,row.getAsJsonObject("habitat"))','parseHabitat(id,row.getAsJsonObject("habitat"),town)')
    native=replace(native,'HabitatLifePolicy.coordinate(x,y,z);','if(town)HabitatLifePolicy.coordinateTown(x,y,z);else HabitatLifePolicy.coordinate(x,y,z);')
    old='            JsonArray anchor=row.getAsJsonArray("bank_anchor");if(anchor.size()!=2)throw new IllegalStateException("Actual connected-bank anchor required");int ax=literal(anchor.get(0)),az=literal(anchor.get(1));if(!bankColumns.contains(column(ax,az))||Math.abs(ax-Math.floor(x))>16||Math.abs(az-Math.floor(z))>16)throw new IllegalStateException("Site is not tied to the actual bank component; bounding rectangle is insufficient");'
    native=replace(native,old,'''            if(town){
                if(townAuthority==null)throw new IllegalStateException("Town resident has no explicit authenticated authored site authority");
                TownLifeAuthority.Site source=townAuthority.site(row.get("town_site").getAsString());source.member(id,site.known,x,y,z);townResidents.put(uuid,source);
                for(List<BlockPos> route:site.routes)for(BlockPos location:route)source.standing(location.getX(),location.getY(),location.getZ());
                for(BlockPos location:new BlockPos[]{site.bed,site.job,site.roof})if(location!=null)source.cell(location.getX(),location.getY(),location.getZ());
            }else{
                JsonArray anchor=row.getAsJsonArray("bank_anchor");if(anchor.size()!=2)throw new IllegalStateException("Actual connected-bank anchor required");int ax=literal(anchor.get(0)),az=literal(anchor.get(1));if(!bankColumns.contains(column(ax,az))||Math.abs(ax-Math.floor(x))>16||Math.abs(az-Math.floor(z))>16)throw new IllegalStateException("Site is not tied to the actual bank component; bounding rectangle is insufficient");
            }''')
    native=replace(native,'HabitatLifePolicy.coordinate(habitat.minX,habitat.minY,habitat.minZ);HabitatLifePolicy.coordinate(habitat.maxX,habitat.maxY,habitat.maxZ);',
                   'if(town){HabitatLifePolicy.coordinateTown(habitat.minX,habitat.minY,habitat.minZ);HabitatLifePolicy.coordinateTown(habitat.maxX,habitat.maxY,habitat.maxZ);}else{HabitatLifePolicy.coordinate(habitat.minX,habitat.minY,habitat.minZ);HabitatLifePolicy.coordinate(habitat.maxX,habitat.maxY,habitat.maxZ);}')
    native=replace(native,'HabitatLifePolicy.coordinate(cx,cy,cz);','if(town)HabitatLifePolicy.coordinateTown(cx,cy,cz);else HabitatLifePolicy.coordinate(cx,cy,cz);')
    native=replace(native,'private Habitat parseHabitat(String id,JsonObject value){','private Habitat parseHabitat(String id,JsonObject value,boolean town){')
    native=replace(native,'HabitatLifePolicy.geometry(p,known,water,bed!=null,job!=null,routes.size());','HabitatLifePolicy.geometry(p,known,water,bed!=null,job!=null,routes.size(),town);')
    native=replace(native,'var fluid=level.getFluidState(new BlockPos(x,y,z));if(water?',
                   'TownLifeAuthority.Site source=townResidents.get(row.uuid);if(source!=null)source.cell(x,y,z);var fluid=level.getFluidState(new BlockPos(x,y,z));if(water?')
    native=replace(native,'private void footing(Resident row,Mob mob,BlockPos feet){covered(row,feet,1);',
                   'private void footing(Resident row,Mob mob,BlockPos feet){TownLifeAuthority.Site source=townResidents.get(row.uuid);if(source!=null)source.standing(feet.getX(),feet.getY(),feet.getZ());covered(row,feet,1);')
    native=replace(native,'BlockPos p=new BlockPos(x,y,z);var fluid=level.getFluidState(p);',
                   'BlockPos p=new BlockPos(x,y,z);TownLifeAuthority.Site source=townResidents.get(row.uuid);if(source!=null)source.cell(x,y,z);var fluid=level.getFluidState(p);')
    return {'HabitatLifePolicy.java':policy.encode(),'NativeHabitatLifeSupport.java':native.encode(),
            'TownLifeAuthority.java':(HERE/'TownLifeAuthority.java').read_bytes(),'prepare.py':producer_source(),
            'town_authority.py':(HERE/'town_authority.py').read_bytes()}


def prepare(output):
    output=Path(output).resolve()
    if output.exists() or not output.is_relative_to(Path('D:/A World for Two/staging').resolve()):raise ValueError('New private D staging output required')
    subprocess.run(['powershell.exe','-NoProfile','-File','C:/Users/kkids/AppData/Local/AeroStorageWatch/ReserveGuard.ps1','-EstimatedCBytes','0','-EstimatedDBytes',str(4*1024*1024)],check=True)
    docs=sources();output.mkdir()
    for name,raw in docs.items():(output/name).write_bytes(raw)
    receipt={'status':'SOURCE_ONLY_NO_DEPLOYMENT','base079e_source_pins':PINS,'one_controller_one_cohort_ledger':True,
             'files':{n:{'bytes':len(r),'sha256':hashlib.sha256(r).hexdigest()} for n,r in docs.items()},'native_admission_or_spawn':False}
    (output/'recipe.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True);print(json.dumps(prepare(parser.parse_args().output)))
