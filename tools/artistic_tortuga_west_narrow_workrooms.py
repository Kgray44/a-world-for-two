"""Occupied, individually composed workrooms in the literal narrow West gaps.

Four low unequal trade masses, not courts/paving counted as buildings.
Source-only recipes and exact stopped-save admission; no runtime actions.
"""
from __future__ import annotations
import argparse,hashlib,json,time
from contextlib import contextmanager
from pathlib import Path

from control_room.common import UserError,digest,read_json
from tools import artistic_tortuga_fill as fill
from tools import artistic_tortuga_western_spit as spit
from tools import artistic_tortuga_west_approved_blocks as previous
from tools import artistic_tortuga_coast_batches as coast
from tools.artistic_tortuga_western_spit import complete_native_joins,public_floor_write
from tools.artistic_tortuga_frontages import RECIPES,AIR,POTS,key,rect,window,light,joists,check
from tools.artistic_west_r2_frontage import Frontage,canonical_joins
from tools.artistic_bridge_refinement import flatten
from tools.artistic_north_bank_east import NorthTerrain,native_payload,GROUND,SOFT,NORTH_SOFT,AIR as VOIDS
from tools.artistic_create_substrate import verify_zinc_factory,qualified_mount
from tools.artistic_zipline_catenary import reader_budget
from tools.playtest import guard

MIB=1024**2
FUTURE=(
 ('staging/tortuga-western-spit-1793215072699978000/manifest.json','cbb7810513c9718345cff6440878508f529b3d1394aab854cd47bd3b5c5b9293'),
 ('staging/tortuga-fill-inner-west-current-9-1793215653202868100/manifest.json','c42ad52915b0984087bcfd27e7665fd306527a833fbc96c4b3595b4870450cdc'),
)
SHELLS=('staging/west15-shells-1793218803041549500/manifest.json','52669f6d5ae92e82a18c1577a99a56e2648fc2dc570a3ff8b33987659b404f42')


def recessed_entry(p,width,z,face):
    """The complete threshold stays inside the literal dry main mass."""
    x=width-2 if face=='east'else 1;outside=width-1 if face=='east'else 0
    for y in(1,2):p.put(outside,y,z,AIR)
    for zz in(z-1,z+1):
        for y in(1,2,3):p.put(outside,y,zz,'dawnoftimebuilder:charred_spruce_timber_frame_pillar',axis='y',role='rooted recessed trade-door cheek')
        p.put(x,3,zz,'mythrais:curved_corbel_dark_oak',facing='west'if face=='east'else'east',shape=0,role='inset lintel knee within the actual narrow mass')
    p.put(x,3,z,'minecraft:dark_oak_planks',role='full native sign and recessed-door head backing')
    for y,half in((1,'lower'),(2,'upper')):
        p.put(x,y,z,'mcwdoors:dark_oak_cottage_door',facing='west'if face=='east'else'east',half=half,hinge='left',open=False,powered=False)
    p.sign(outside,3,z,face,[p.owner,'Working trade • Orders'])
    p.entries.append({'owner':p.owner,'door':[x,1,z],'outward':face,'outside_step':[outside,0,z]})


def inset_display(p,width,start,face):
    """A real one-block-deep fancy casement niche, no outward alley bulk."""
    outside=0 if face=='west'else width-1;plane=1 if face=='west'else width-2
    for z in(start,start+1):
        for y in(1,2):p.put(outside,y,z,AIR)
    for z in(start-1,start+2):
        for y in(1,2,3):p.put(plane,y,z,'minecraft:stripped_dark_oak_log',axis='y',role='grounded jamb behind the actually recessed display')
    window(p,plane,1,start,face,width=2,height=2)
    for z in(start,start+1):
        p.put(outside,0,z,'minecraft:dark_oak_planks',role='full founded display-niche sill')
    p.put(outside,1,start,POTS[4],role='contained fern inside the recessed window niche on its actual full sill')


def workroom(registry,*,width,length,kind,entry,face='east'):
    """Finite narrow anatomy; every trade has an authored room/roof story."""
    if(width,length,kind,entry,face)not in((4,16,'cordage',4,'east'),(5,13,'pennants',10,'west'),(4,14,'crates',6,'east'),(4,14,'tea',11,'east'),(5,8,'keys',4,'east')):
        raise UserError('Only the five literal individually measured workroom compositions are allowed')
    main=rect(0,0,width-1,length-1)
    if kind in('pennants','keys'):main.remove((0,0))
    p=Frontage(registry,(0,63,0));p.owner={'cordage':'The Long Splice','pennants':'The Folded Jack','crates':'The Bent Crate','tea':'Last-Kettle Galley','keys':'The Little Brass Key'}[kind]
    p.main[p.owner]=main;p.levels[p.owner]=[set(main)]
    for x,z in main:
        for y in range(1,10):p.put(x,y,z,AIR)
    p.floor(main,0);p.walls(main,0,'minecraft:brown_terracotta'if kind in('cordage','tea','keys')else'minecraft:gray_terracotta')
    # Low stepped/hipped roof masses, with silhouette changes instead of bands.
    profile=(0,1,1,0)if width==4 else(0,1,2,1,0)
    split={'cordage':9,'pennants':7,'crates':8,'tea':6,'keys':4}[kind]
    p.roof((0,0,width-1,split),4,profile,family='dark_oak',annex=True)
    p.roof((0,split+1,width-1,length-1),5 if kind in('cordage','pennants','keys')else 4,profile,
       family='spruce'if kind in('crates','tea')else'dark_oak',hip_south=kind in('tea','keys'),annex=True)
    aisle=2
    p.reserve('Actual single-level working passage',[(aisle,1,z)for z in range(1,length-1)])
    if width==5:p.reserve('Short second-width entry shoulder',[(3,1,z)for z in range(max(1,entry-1),min(length-1,entry+2))])
    for z in sorted({2,max(3,split-1),length-2}):
        for x in range(width):p.beam(x,4,z,'x',wood='charred_spruce',role='visible supported low-workroom ceiling tie')
    joists(p,1,width-2,(2,length-3))
    displayface='west'if face=='east'else'east'
    inset_display(p,width,3,displayface)
    # The unglazed wall contains trade-specific furniture rather than bare panels.
    benchx=1
    for z in(1,6,length-2):
        if z in(entry-1,entry,entry+1)and face=='west':continue
        p.put(benchx,1,z,'minecraft:dark_oak_planks',role='full-depth fixed work/display plinth')
    if kind=='cordage':
        p.put(1,1,1,'minecraft:loom',facing='east',role='real small cordage-pattern and pennant loom')
        p.put(1,1,6,'minecraft:crafting_table',role='real fastener fitting and splice bench')
        p.counter(1,1,9,'east',role='long-splice measurement and repair counter')
        p.put(1,2,9,'farmersdelight:cutting_board',facing='east',waterlogged=False,role='actual splice measuring/cutting surface')
        p.put(1,1,12,'farmersdelight:dark_oak_cabinet',facing='east',open=False,role='native-default fixed pattern and fitting cupboard')
        p.put(1,1,14,'minecraft:barrel',facing='up',open=False,role='new native-default finished cordage orders; no copied Items')
        p.room('Loom and measuring front',0,(2,1,2),'A literal narrow woven-pattern workroom with a real loom and fitting bench beside a deeply recessed fern casement.')
        p.room('Splice and finished-order rear',0,(2,1,11),'An actual long measurement counter, cutting board, fixed patterns cupboard and new default stock fill the rear under a raised low roof.')
    elif kind=='pennants':
        p.put(1,1,1,'minecraft:loom',facing='east',role='real folded-jack sail pennant loom')
        p.put(1,1,6,'farmersdelight:dark_oak_cabinet',facing='east',open=False,role='native-default tailoring notions and pattern cabinet')
        p.counter(1,1,8,'east',role='real long pennant cutting and collection counter')
        p.put(1,2,8,'farmersdelight:cutting_board',facing='east',waterlogged=False,role='actual cloth cutting surface')
        p.put(1,1,11,'minecraft:barrel',facing='up',open=False,role='new unfilled returned-pennant stock vessel')
        p.room('Sail-cloth front',0,(2,1,3),'The deep fancy display sits opposite an actual loom and cloth work; the narrow silhouette rises at the rear rather than carrying colored roof stripes.')
        p.room('Tailoring collection rear',0,(2,1,9),'The recessed north-side entrance reaches the real counter, cutting board and ordinary stock without a paved courtyard being counted as architecture.')
    elif kind=='crates':
        p.put(1,1,1,'minecraft:crafting_table',role='real crate assembly and fastener workbench')
        p.put(1,1,6,'minecraft:stonecutter',facing='east',role='real native fitting and sharpening station; no automated machinery claim')
        p.counter(1,1,9,'east',role='actual long repair-order counter')
        p.put(1,2,9,'handcrafted:wood_cup',facing='east',pieces=3,waterlogged=False,role='ordinary vessels sorting small work orders')
        p.put(1,1,11,'farmersdelight:dark_oak_cabinet',facing='east',open=False,role='real native-default fixed repair tool cupboard')
        p.put(1,1,12,'minecraft:barrel',facing='up',open=False,role='new ordinary repaired-order stock')
        p.room('Crate fitting front',0,(2,1,2),'A real workbench and fitting station occupy this low deep shop immediately behind the quay lane.')
        p.room('Order and repair rear',0,(2,1,10),'The back room has its real counter, tool cupboard, stock and a different low hipped roof return; no dwelling or automated workshop is invented.')
    elif kind=='tea':
        p.put(1,1,1,'minecraft:smoker',facing='east',lit=False,role='ordinary safe unlit galley cooking station')
        p.put(1,1,6,'farmersdelight:dark_oak_cabinet',facing='east',open=False,role='real native-default tea and serving pantry')
        p.counter(1,1,8,'east',role='actual narrow crew supper serving counter')
        p.put(1,2,8,'handcrafted:terracotta_bowl',facing='east',pieces=3,waterlogged=False,role='ordinary serving bowls on their fixed counter')
        p.put(1,1,10,'handcrafted:dark_oak_chair',facing='east',color='brown',waterlogged=False,role='small actual crew waiting seat opposite the recessed door')
        p.put(1,1,12,'minecraft:barrel',facing='up',open=False,role='new native-default galley supplies')
        p.room('Warm galley front',0,(2,1,3),'A small working galley with an ordinary unlit cooking station, contained green display and actual fixed pantry.')
        p.room('Supper collection end',0,(2,1,9),'The compact serving counter, bowls, waiting chair and ordinary stock are lit below a low stepped roof; there is no ceremonial empty plaza.')
    else:
        p.put(1,1,1,'minecraft:stonecutter',facing='east',role='real small key-fitting work station')
        p.counter(1,1,5,'east',role='actual small-key repair and order counter')
        p.put(1,2,5,'handcrafted:terracotta_bowl',facing='east',pieces=3,waterlogged=False,role='ordinary small repair-order sorting bowls')
        p.put(1,1,6,'minecraft:barrel',facing='up',open=False,role='new default key-repair stock, no fabricated contents')
        p.room('Key fitting front',0,(2,1,2),'A real stonecutter/fitting station and deep fancy display occupy the short clipped-corner shop.')
        p.room('Order counter rear',0,(2,1,4),'The same useful little shop has a real order counter, sorting bowls and ordinary stock under a raised short roof; not an invented second dwelling.')
    # Finite real-backed objects at different depths, not a bare-wall count.
    shelfz=length-3 if kind not in('keys','tea')else 5 if kind=='tea'else 2
    if p.blocks.get((1,2,shelfz),AIR)==AIR and p.blocks.get((1,3,shelfz),AIR)==AIR:
        p.put(0,2,shelfz,'minecraft:dark_oak_planks',role='full grounded-sidewall account-shelf backing')
        p.shelf(1,2,shelfz,'east',books=True)
        p.supports.append({'detail':[1,2,shelfz],'support':[0,2,shelfz],'role':'actual fixed trade-account shelf'})
    light(p,2,3,2,'small supported entrance/task lantern over the actual work passage')
    if length>=13:light(p,2,3,length-4,'small supported rear trade-counter task lantern')
    recessed_entry(p,width,entry,face)
    canonical_joins(p);return p


EXTRA={
 'narrow-long-splice':lambda r:workroom(r,width=4,length=16,kind='cordage',entry=4),
 'narrow-folded-jack':lambda r:workroom(r,width=5,length=13,kind='pennants',entry=10,face='west'),
 'narrow-bent-crate':lambda r:workroom(r,width=4,length=14,kind='crates',entry=6),
 'narrow-last-kettle':lambda r:workroom(r,width=4,length=14,kind='tea',entry=11),
 'narrow-little-key':lambda r:workroom(r,width=5,length=8,kind='keys',entry=4),
}


@contextmanager
def source_recipes():
    with spit.source_recipes():
        if set(EXTRA)&set(RECIPES):raise UserError('Never replace a frozen original recipe')
        RECIPES.update(EXTRA)
        try:yield
        finally:
            for name in EXTRA:RECIPES.pop(name,None)


BATCH={
 'buildings':(
  {'recipe':'narrow-long-splice','turn':0,'name':'The Long Splice','trade':'Cordage • Repairs','origin':(1024,63,-1257)},
  {'recipe':'narrow-folded-jack','turn':1,'name':'The Folded Jack','trade':'Sail Pennants • Cutting','origin':(1013,63,-1300)},
  {'recipe':'narrow-bent-crate','turn':1,'name':'The Bent Crate','trade':'Crate Fittings • Repairs','origin':(1047,63,-1279)},
  {'recipe':'narrow-last-kettle','turn':1,'name':'Last-Kettle Galley','trade':'Crew Supper • Tea','origin':(1053,63,-1309)},
 ),
 'links':(
  ('Long Splice meets the retained northern armoury approach',((1028,-1253),(1028,-1253))),
  ('Folded Jack northern actual dry threshold',((1015,-1302),(1015,-1302))),
  ('Bent Crate actual south-facing public threshold',((1054,-1275),(1054,-1275))),
  ('Last-Kettle actual south-side crew threshold',((1055,-1305),(1055,-1305))),
 ),
 'design':'Four unequal occupied low trade masses in actual4-by16,13-by5 and14-by4 gaps. Recessed fancy displays, real deep door niches, stepped/hipped roofs and trade-specific lit work scenes fit inside the tight dry footprint. Only genuine two-wide thresholds are paved; no court or lawn is counted as a building. The fifth small-key shop is held because later construction context blocks its proposed site.',
 'street_views':(),
}


def current_field(home,checkpoint_id,checkpoint_sha,field_path,field_sha):
    data,prior,refs=spit.current_field(home,checkpoint_id,checkpoint_sha,field_path,field_sha)
    more,more_refs,buildings=previous.construction_targets(home,FUTURE);prior.update(more);refs+=more_refs
    shell_manifest=home/SHELLS[0]
    if digest(shell_manifest)!=SHELLS[1]:raise UserError('Retained exact West15 correction source changed')
    sm=read_json(shell_manifest)
    for index in range(1,4):
        name=f'west15-{index}-PROPOSAL.json';p=shell_manifest.parent/name
        if digest(p)!=sm['files'][name]['sha256']:raise UserError('Retained West15 correction delta changed')
        prior.update(flatten(read_json(p)))
    refs.append({'relative':SHELLS[0],'sha256':SHELLS[1],'protection':'Only exact three construction deltas, never full verification context'})
    blocked={(x,z)for x,y,z in prior}
    data['eligible_columns_READONLY']=[r for r in data['eligible_columns_READONLY']if tuple(r[:2])not in blocked]
    data['two_high_walk_columns_READONLY']=[r for r in data['two_high_walk_columns_READONLY']if all(prior.get((r[0],y,r[1]),AIR)==AIR for y in(64,65))]
    for b in buildings:data['retained_source_main_footprints']['placed-or-queued '+b['name']]=b['main_columns_xz']
    data['narrow_workroom_source_sha256']=digest(Path(__file__));data['added_buildable_authority_columns']=0
    return data,prior,refs


def prepare(home,checkpoint_id,checkpoint_sha,field_path,field_sha,batch='narrow-workrooms'):
    reserve=guard(8*MIB,96*MIB)
    budgets=[reader_budget()]  # A refusal stops before readers or output allocation.
    home=fill.private_home(home);receipt=fill.stopped(home,checkpoint_id,checkpoint_sha)
    field_path=Path(field_path).resolve()
    if not field_path.is_relative_to(home/'staging')or digest(field_path)!=field_sha or field_path.stat().st_size>32*MIB:
        raise UserError('Exact bounded current stopped-save field required')
    source_field=read_json(field_path)
    if(source_field.get('checkpoint_id'),source_field.get('checkpoint_sha256'))!=(checkpoint_id,checkpoint_sha):
        raise UserError('A changed save requires fresh fields and native before proofs, not a hash rebind')
    if batch!='narrow-workrooms':raise UserError('Exact finite individually composed spit batch required')
    out=home/'staging'/('tortuga-narrow-workrooms-'+str(time.time_ns()));out.mkdir()
    terrain=None
    try:
        field,prior,prior_refs=current_field(home,checkpoint_id,checkpoint_sha,field_path,field_sha)
        registry=read_json(home/'dashboard/settlement/registry.json')
        with source_recipes():states,tags,buildings,mains=fill.modeled(registry,BATCH)
        if not 1<=len(buildings)<=12 or len(states)+2048>12000:raise UserError('Finite12K native-target batch cap exceeded')
        free={tuple(r[:2])for r in field['eligible_columns_READONLY']}
        if not mains<=free:raise UserError('No main mass in saved water, existing source, unsupported soil or unknown: '+str(sorted(mains-free)[:10]))
        keep,forest,heritage,_,_,refs=fill.retained_context(home,registry);keep.update(prior)
        overlap=[q for q in states if q in keep or(q[0],q[2])in heritage or not 968<=q[0]<=1099]
        if overlap or mains&forest:raise UserError('Keep every retained/queued construction target, flight and habitat: '+str(overlap[:8]))
        walking={tuple(r[:2]):r[2:]for r in field['two_high_walk_columns_READONLY']}
        lane,routes=fill.route_geometry(states,mains,walking,BATCH)
        zinc=verify_zinc_factory(home);terrain=NorthTerrain(home,receipt,registry)
        before={};supports={};clearance={};retained_floors={};began=time.monotonic()
        for x,z in sorted(mains|set(lane)):
            col=terrain.column(x,z)
            if(x,z)in mains and(col['kind']!='dry'or col['surface_y']not in(62,63)):
                raise UserError('A complete main floor must be literal low dry land: '+str((x,z,col)))
            mount=qualified_mount(terrain.state,x,z,zinc)
            if not mount['stable']:raise UserError('Stable complete native foundation required: '+str((x,z,mount)))
            for xx,yy,zz,value in mount['stack']:
                if(xx,yy,zz)in terrain.entities:raise UserError('No existing BE may become a new foundation')
                supports[xx,yy,zz]=value
            if(x,z)in lane:
                q=x,63,z;value=terrain.state(*q)
                if q in terrain.entities or value is None or 'waterlogged=true'in value:raise UserError('Retain current water/BE/unknown at a public threshold')
                new_floor=public_floor_write(value,walking[x,z][0],keep.get(q),lane[x,z])
                if new_floor is None:retained_floors[q]=value
                else:states[q]=new_floor
        for i,q in enumerate(sorted(states,key=lambda q:(q[0]//16,q[2]//16,q[1],q[0],q[2]))):
            current=terrain.state(*q)
            if q in keep or q in terrain.entities or current is None or key(current)not in GROUND|VOIDS|SOFT|NORTH_SOFT or'waterlogged=true'in current:
                raise UserError('Keep actual saved objects, water, BEs, canopy and unknown: '+str((q,current)))
            before[q]=current
            if i%256==0:budgets.append(reader_budget())
            if time.monotonic()-began>120:raise UserError('Finite120s stopped-save reader bound exceeded')
        for x,z in lane:
            floor=x,63,z
            if floor in retained_floors:before[floor]=retained_floors[floor]
            for y in(64,65):
                q=x,y,z;current=terrain.state(*q)
                if q in terrain.entities or current is None or key(current)not in VOIDS|SOFT|NORTH_SOFT or'waterlogged=true'in current:
                    raise UserError('A real two-wide public body is obstructed: '+str((q,current)))
                if q in keep:
                    if keep[q]!=AIR or current!=AIR:raise UserError('No clearing or furniture replacement in a retained route')
                elif key(current)not in VOIDS:states[q]=AIR
                before[q]=current;clearance[q]=AIR
        saved=terrain.snapshot.sources;terrain.close();terrain=None
        states,old_join_expectations=complete_native_joins(registry,states,keep)
        outdoor=fill.lane_materials(states,lane,batch+' short real public approaches')
        if len(states)>12000:raise UserError('Retain proposal but refuse native admission above12K targets')
        full={**states,**supports,**clearance,**retained_floors}
        documents={
          'cluster-PROPOSAL.json':native_payload(registry,states,checkpoint_sha,'TORTUGA WEST — four individually composed narrow trade workrooms',tags=tags),
          'before-VERIFY-ONLY.json':native_payload(registry,before,checkpoint_sha,'VERIFY ONLY — exact saved targets and retained real public approaches'),
          'stable-supports-VERIFY-ONLY.json':native_payload(registry,{**supports,**retained_floors},checkpoint_sha,'VERIFY ONLY — complete stable native substrate and unchanged public pavers'),
          'complete-after-VERIFY-ONLY.json':native_payload(registry,full,checkpoint_sha,'VERIFY ONLY — all new occupied geometry, actual short routes and retained foundations',tags=tags),
          'normal-joins-SETTLE-ONLY.json':native_payload(registry,{q:s for q,s in states.items()if key(s)not in VOIDS},checkpoint_sha,'NORMAL JOINS ONLY — bounded actual neighbor shapes; no old furniture/NBT replay'),
        }
        raw={}
        for name,doc in documents.items():
            if name!='cluster-PROPOSAL.json':doc.update(construction_forbidden=True,verification_only=True)
            raw[name]=(json.dumps(doc,separators=(',',':'))+'\n').encode()
        manifest={'format':'awft-tortuga-narrow-workrooms:1','batch':batch,'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,
          'source_sha256':digest(Path(__file__)),'field_source':str(field_path.relative_to(home)),'field_sha256':field_sha,
          'definition':BATCH,'buildings':buildings,'rooms':sum(len(b['rooms'])for b in buildings),
          'main_columns':len(mains),'lane_columns':len(lane),'targets':len(states),'native_target_cap':12000,'routes':routes,
          'retained_public_floor_cells':len(retained_floors),'public_floor_replacement_writes':0,'existing_BE_targets':0,
          'read_only_neighbor_part_derivations_NOT_PLACEMENT_AUTHORITY':old_join_expectations,
          'approved_west_concept':{'relative':coast.APPROVED[0],'sha256':coast.APPROVED[1]},'retained_construction_sources':prior_refs,
          'other_preservation_sources':refs,'source_dependency_sha256':{p.name:digest(p)for p in(Path(fill.__file__),Path(coast.__file__),Path(previous.__file__))},
          'raw_saved_sources':saved,'pinned_zinc_factory':zinc,'outdoor_material_rule':outdoor,'reserve_guard':reserve,
          'reader_peak_RSS_bytes':max(b['owned_reader_rss_bytes']for b in budgets),'native_actions':0,'world_writes':0,
          'native_cameras':[v for b in buildings for v in b['scene_views']]+[{'name':n,'feet':list(q),'look_at':list(t),'source_only_native_walk_render_pending':True}for n,q,t in BATCH['street_views']],
          'status':'SOURCE + EXACT STOPPED PREIMAGE; fresh Native admission, map, placement/normal-settle/full verification and actual artist review pending',
          'limits':['Four narrow occupied workrooms do not prove entire western coverage','These low workshops have eight activity scenes across four actual working floors; no invented homes','Observed public pavers are verification context only, never construction ownership','Every changed checkpoint requires fresh field/preimage; no silent rebinding','No old stock, container Items, owner, NPC or human data is copied or moved']}
        field_bytes=(json.dumps(field,separators=(',',':'))+'\n').encode()
        raw['field-READONLY.json']=field_bytes
        map_bytes=coast.batch_map(manifest,field)
        if len(map_bytes)>MIB:raise UserError('Finite1MiB source map bound exceeded')
        raw['batch-map-PLAN-ONLY.svg']=map_bytes
        manifest['files']={name:{'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}for name,data in raw.items()}
        raw['manifest.json']=(json.dumps(manifest,separators=(',',':'))+'\n').encode()
        if sum(map(len,raw.values()))>64*MIB:raise UserError('Finite64MiB final bundle cap exceeded')
        for name,data in raw.items():(out/name).open('xb').write(data)
        return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'buildings':len(buildings),'scenes':manifest['rooms'],
          'main_columns':len(mains),'lane_columns':len(lane),'targets':len(states),'files':manifest['files'],'native_actions':0}
    except Exception as exc:
        (out/'refusal.json').open('x',encoding='utf-8').write(json.dumps({'source_sha256':digest(Path(__file__)),'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'reason':type(exc).__name__+': '+str(exc),'native_actions':0,'world_writes':0,'request_emitted':False})+'\n')
        raise UserError(str(exc)+'; preserved '+str(out))from exc
    finally:
        if terrain is not None:terrain.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home',type=Path,required=True);parser.add_argument('--checkpoint-id',required=True);parser.add_argument('--checkpoint-sha',required=True)
    parser.add_argument('--field',type=Path,required=True);parser.add_argument('--field-sha',required=True)
    args=parser.parse_args()
    print(json.dumps(prepare(args.home,args.checkpoint_id,args.checkpoint_sha,args.field,args.field_sha),indent=2))
