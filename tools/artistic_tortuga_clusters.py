"""Fixed, individually composed linked Tortuga clusters from the thirteen recipes.

Finite saved preimages only. No current inventory removal, runtime calls or
automatic parcel packing; each cluster has its own authored offsets and lanes.
"""
from __future__ import annotations
import argparse,hashlib,json,time,re
from pathlib import Path
from control_room.common import UserError,digest,read_json
from tools.artistic_tortuga_frontages import RECIPES,check,key,AIR,door,window
from tools.artistic_west_r2_frontage import VEC
from tools.artistic_tortuga_headland_pair import COVERAGE,GROUND_CONTEXT
from tools.artistic_tortuga_west_ground import mask_inputs,path_to
from tools.artistic_ground_stability import natural_mount
from tools.artistic_create_substrate import verify_zinc_factory,qualified_mount
from tools.artistic_north_bank_east import NorthTerrain,native_payload,GROUND,SOFT,NORTH_SOFT,AIR as VOIDS,preservation
from tools.artistic_bridge_refinement import flatten
from tools.artistic_materials import require_outdoor_rule
from tools.artistic_zipline_catenary import reader_budget
from tools.playtest import guard

MIB=1024**2
RECIPE_SHA='d3b0181e88535ee678471e3c60f86042e006b01403baf0a1ec33809ec2a924ba'
HEADLAND=('staging/tortuga-headland-pair-1793199900323997200/complete-after-VERIFY-ONLY.json','ddf8dbc81d8e231b8951b34859754a3c6fc79c55a22373f557c914114447bf06')
CLUSTERS={
 'quill-court':{
   'parcels':(('kettle-bend',(1162,63,-1234)),('keel-quill',(1172,63,-1235)),
              ('mugs-mending',(1185,63,-1231)),('needlewake',(1175,63,-1221))),
   'west_public_entry':('mugs-mending',(0,5)),
   'taller_alley_casement':('keel-quill',(1,10,'south',2)),
   'links':(('Supper threshold to bookbinder lane',((1165,-1224),(1173,-1224),(1181,-1227))),
            ('Opposite bookbinder and tea-house doors',((1181,-1227),(1182,-1227))),
            ('Bookbinder to seamstress turn',((1181,-1227),(1183,-1223),(1184,-1214)))),
   'design':'Four tightly offset inhabited masses; the tea shop has an additional west entrance opposite the bookbinder so a tiny internal alley replaces a north-door perimeter walk. The seamstress turns its east door into the southern return.'},
 'station-bend':{
   'parcels':(('briny-hearth',(1118,63,-1265)),('quarter-tide',(1118,63,-1253)),('moon-rigging',(1122,63,-1230))),
   'links':(('Bread door to tiny tavern',((1115,-1258),(1115,-1255),(1122,-1256))),
            ('Tavern around retained weaver to mariner',((1122,-1256),(1128,-1254),(1129,-1243),(1129,-1234),(1119,-1223)))),
   'design':'A west-facing bakehouse and north-facing little music tavern share a worn cross-lane; the return threads around the preserved weaver instead of a bare lawn.'},
}


def raise_alley_casement(p,x,z,face,width):
    """A real taller fancy window, not ignored low collision geometry.

The old low hood and two low knees are replaced by a new framed head one
block higher. Every carving remains; the actual two-high alley is now clear.
"""
    dx,dz=VEC[face];tx,tz=(1,0)if dz else(0,1)
    old_heads={(x+n*tx+dx,3,z+n*tz+dz)for n in range(-1,width+1)}
    old_knees={(x+n*tx+dx,2,z+n*tz+dz)for n in(-1,width)}
    for q in old_heads:
        if not key(p.blocks.get(q,AIR)).startswith('dawnoftimebuilder:'):raise UserError('Exact old casement head required before the original-source variant')
        p.blocks.pop(q);p.owners.pop(q,None)
    for q in old_knees:
        if key(p.blocks.get(q,AIR))!='mythrais:curved_corbel_dark_oak':raise UserError('Exact old lower casement knees required')
        p.blocks.pop(q);p.owners.pop(q,None)
    p.supports=[r for r in p.supports if tuple(r['detail'])not in old_heads]
    for n in(-1,width):p.put(x+n*tx,3,z+n*tz,'minecraft:stripped_dark_oak_log',axis='y',role='tall casement jamb under its actual higher head')
    window(p,x,1,z,face,width=width,height=3)


def construct(registry,definition,free,*,walk_free=None,skip_routes=False):
    states={};tags={};buildings=[];main=set()
    for recipe,origin in definition['parcels']:
        p=RECIPES[recipe](registry)
        taller=definition.get('taller_alley_casement')
        if taller and taller[0]==recipe:raise_alley_casement(p,*taller[1])
        extra=definition.get('west_public_entry')
        if extra and extra[0]==recipe:
            x,z=extra[1]
            aisle=[(xx,1,z)for xx in range(x+1,x+5)]
            if any(p.blocks.get((xx,yy+h,zz),AIR)!=AIR for xx,yy,zz in aisle for h in(0,1)):raise UserError('Do not remove any story furniture to force a second entrance')
            p.reserve('Actual added west public-door aisle',aisle);door(p,x,z,'west')
        proof=check(p);world={tuple(q[i]+origin[i]for i in range(3)):s for q,s in p.blocks.items()}
        conflicts=[q for q,s in world.items()if q in states and not(s==AIR and states[q]==AIR)]
        if conflicts:raise UserError('Fix the actual composed masses, not expected-state acceptance: '+str((recipe,conflicts[:4])))
        cells={(x+origin[0],z+origin[2])for x,z in p.main[p.owner]}
        if not cells<=free:raise UserError('Actual fixed main outline is not completely qualified: '+str((recipe,sorted(cells-free)[:8])))
        states.update(world);tags.update({tuple(q[i]+origin[i]for i in range(3)):v for q,v in p.tags.items()});main|=cells
        buildings.append({'name':p.owner,'recipe':recipe,'origin':list(origin),'main_columns_xz':[list(q)for q in sorted(cells)],'proof':proof,
                          'rooms':[{**r,'world_standing_point':[r['standing_point'][i]+origin[i]for i in range(3)]}for r in p.rooms],
                          'entries':[{**r,'world_door':[r['door'][i]+origin[i]for i in range(3)]}for r in p.entries]})
    # Literal saved columns plus complete future two-high body. A generated
    # casement/post is an obstruction, never hand-waved out of the lane.
    if skip_routes:return states,tags,buildings,main,{},[]
    walking={q for q in(free if walk_free is None else walk_free)if q not in main and all(states.get((q[0],y,q[1]),AIR)==AIR for y in(64,65))}
    used={};routes=[]
    for name,points in definition['links']:
        anchors=[]
        for a,b in zip(points,points[1:]):
            try:leg=path_to(walking,a,b)
            except UserError as exc:raise UserError(name+' '+str(a)+' → '+str(b)+': '+str(exc))from exc
            anchors.extend(leg[:-1])
        anchors.append(points[-1]);cells=set()
        for i,(x,z)in enumerate(anchors):
            a=anchors[max(0,i-1)];b=anchors[min(len(anchors)-1,i+1)];axis='x'if abs(b[0]-a[0])>=abs(b[1]-a[1])else'z'
            for dx,dz in((0,0),(1,0),(0,1),(1,1)):
                q=x+dx,z+dz;cells.add(q);used.setdefault(q,set()).add(axis)
        routes.append({'name':name,'width':2,'cells_xz':[list(q)for q in sorted(cells)],'standing_positions':[[x+.5,64,z+.5]for x,z in sorted(cells)]})
    for(x,z),axes in used.items():
        q=x,63,z
        if q in states and states[q]!=AIR:raise UserError('No public lane through an authored main/stoop')
        states[q]='chipped:small_stone_bricks'if len(axes)>1 else'minecraft:andesite'if'x'in axes else'minecraft:cobblestone'
    return states,tags,buildings,main,used,routes


def prepare(home,checkpoint_id,checkpoint_sha,cluster,*,definition=None,definition_source=None):
    home=Path(home).resolve();reserve=guard(8*MIB,32*MIB)
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve()or not re.fullmatch('[a-z0-9-]{1,48}',cluster):raise UserError('Exact private authored cluster required')
    if definition is None:
        if cluster not in CLUSTERS:raise UserError('Exact authored cluster definition required')
        definition=CLUSTERS[cluster];definition_source=Path(__file__)
    else:
        definition_source=Path(definition_source).resolve()
        if definition_source.parent!=Path(__file__).resolve().parent or not definition_source.is_file():raise UserError('An additive cluster requires its actual owned source file')
    definition_sha=hashlib.sha256(json.dumps(definition,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    try:budgets=[reader_budget()]
    except UserError as exc:
        o=home/'staging'/('tortuga-'+cluster+'-REFUSED-'+str(time.time_ns()));o.mkdir();(o/'refusal.json').open('x').write(json.dumps({'reason':str(exc),'reader_opened':False,'native_actions':0})+'\n');raise UserError(str(exc)+'; retained '+str(o))from exc
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    if receipt.get('verified')is not True or(receipt.get('id'),receipt.get('sha256'))!=(checkpoint_id,checkpoint_sha)or'stopped'not in receipt.get('scope','').lower():raise UserError('Exact stopped cluster checkpoint required')
    for rel,sha in(COVERAGE,GROUND_CONTEXT,HEADLAND):
        if digest(home/rel)!=sha:raise UserError('Retain exact residual/current future geometry source')
    if digest(Path(__file__).with_name('artistic_tortuga_frontages.py'))!=RECIPE_SHA:raise UserError('Frozen thirteen original recipes changed')
    data=read_json(home/COVERAGE[0])
    if(data['checkpoint_id'],data['checkpoint_sha256'])!=(checkpoint_id,checkpoint_sha):raise UserError('No automatic rebinding of old habitat/ground proof')
    free={tuple(r[:2])for r in data['eligible_columns_READONLY']};registry=read_json(home/'dashboard/settlement/registry.json')
    states,tags,buildings,main,lane,routes=construct(registry,definition,free,skip_routes=True)
    keep,forest,refs=mask_inputs(home)
    for rel,sha in(GROUND_CONTEXT,HEADLAND):keep.update(flatten(read_json(home/rel)));refs.append({'relative':rel,'sha256':sha})
    heritage,old_refs=preservation(home,registry);refs+=old_refs
    if any(q in keep or(q[0],q[2])in heritage for q in states):raise UserError('Keep all current/future town/stock/AIR/flight and original accepted section')
    if(main|set(lane))&forest:raise UserError('Keep all native woodland growth reservations')
    # A building requires its full21-high clear volume; a PUBLIC ground lane
    # may legitimately pass below a retained old eave. Qualify that distinct
    # two-high volume literally, outside EVERY existing/future main footprint.
    old_mains={tuple(q)for row in data['footprints'].values()for q in row['main_cells_xz']}
    from tools.artistic_west_r2_layout import GEOGRAPHY
    if digest(home/GEOGRAPHY[0])!=GEOGRAPHY[1]:raise UserError('Exact measured bank locator required')
    north={tuple(r['xz'])for r in read_json(home/GEOGRAPHY[0])['columns']if r['north_connected']}
    zinc_proof=verify_zinc_factory(home)
    terrain=NorthTerrain(home,receipt,registry);before={};supports={};clearance={};started=time.monotonic();walk_field={};retained_walk_air=set()
    try:
        x0=min(x for x,z in main)-5;x1=max(x for x,z in main)+5;z0=min(z for x,z in main)-5;z1=max(z for x,z in main)+5
        if(x1-x0+1)*(z1-z0+1)>4096:raise UserError('Finite4096-column composed public-lane field exceeded')
        for x in range(x0,x1+1):
            for z in range(z0,z1+1):
                q=x,z
                if q not in north or q in old_mains|main|heritage|forest:continue
                floor=terrain.state(x,63,z);body=[terrain.state(x,y,z)for y in(64,65)]
                if floor is None or key(floor)not in GROUND|VOIDS|{'minecraft:polished_andesite','chipped:small_stone_bricks','minecraft:cobbled_deepslate'}or'waterlogged=true'in floor:continue
                if any(s is None or key(s)not in VOIDS|SOFT|NORTH_SOFT or'waterlogged=true'in s for s in body):continue
                if any((x,y,z)in terrain.entities for y in(62,63,64,65)):continue
                if(x,63,z)in keep and floor!=keep[x,63,z]:continue
                if any((x,y,z)in keep and(keep[x,y,z]!=AIR or s!=AIR)for y,s in zip((64,65),body)):continue
                mount=qualified_mount(terrain.state,x,z,zinc_proof)
                if not mount['stable']:continue
                walk_field[q]={'floor':floor,'body':body,'mount':mount,'retained':(x,63,z)in keep}
        states,tags,buildings,main,lane,routes=construct(registry,definition,free,walk_free=walk_field)
        # Retained source pavers/AIR are witnesses, never replay targets.
        for x,z in lane:
            if walk_field[x,z]['retained']:
                states.pop((x,63,z));supports[x,63,z]=walk_field[x,z]['floor']
            retained_walk_air|={(x,y,z)for y in(64,65)if(x,y,z)in keep}
        for x,z in sorted(main|set(lane)):
            col=terrain.column(x,z)
            if(x,z)in main and(col['kind']!='dry'or col['surface_y']not in(62,63)):raise UserError('Literal current complete main footing is not dry '+str((x,z,col)))
            mount=qualified_mount(terrain.state,x,z,zinc_proof)
            if not mount['stable']:raise UserError('No supported native substrate '+str((x,z,mount)))
            for xx,yy,zz,s in mount['stack']:supports[xx,yy,zz]=s
        for i,q in enumerate(sorted(states,key=lambda q:(q[0]//16,q[2]//16,q[1],q[0],q[2]))):
            old=terrain.state(*q)
            if old is None or q in terrain.entities or key(old)not in VOIDS|SOFT|GROUND|NORTH_SOFT or'waterlogged=true'in old:raise UserError('Preserve actual BE/object/unknown/water '+str((q,old)))
            before[q]=old
            if i%512==0:budgets.append(reader_budget())
            if time.monotonic()-started>90:raise UserError('Finite90s cluster source reader exceeded')
        for x,z in lane:
            for y in(64,65):
                q=x,y,z;old=terrain.state(*q)
                if old is None or key(old)not in VOIDS|SOFT|NORTH_SOFT or'waterlogged=true'in old or q in terrain.entities:raise UserError('Actual lane body is not clear '+str((q,old)))
                before[q]=old;clearance[q]=AIR
                if key(old)not in VOIDS:
                    if q in keep:raise UserError('Retain the authored walking AIR without any source replay')
                    states[q]=AIR
        sources=terrain.snapshot.sources
    except UserError as exc:
        o=home/'staging'/('tortuga-'+cluster+'-REFUSED-'+str(time.time_ns()));o.mkdir();(o/'refusal.json').open('x',encoding='utf-8').write(json.dumps({'reason':str(exc),'checkpoint':checkpoint_id,'source_sha256':digest(Path(__file__)),'native_actions':0,'world_writes':0,'reader_closed_by_finally':True})+'\n');raise UserError(str(exc)+'; retained '+str(o))from exc
    finally:terrain.close()
    rule=require_outdoor_rule({q:s for q,s in states.items()if(q[0],q[2])in lane},cluster+' complete public lanes')
    full={**states,**supports,**clearance};docs={
     'cluster-PROPOSAL.json':native_payload(registry,states,checkpoint_sha,'TORTUGA '+cluster+' — individually composed linked furnished frontages',tags=tags),
     'before-VERIFY-ONLY.json':native_payload(registry,before,checkpoint_sha,'VERIFY ONLY — full current cluster before including retained public walking body'),
     'stable-supports-VERIFY-ONLY.json':native_payload(registry,supports,checkpoint_sha,'VERIFY ONLY — entire dry gravel chains to qualified native substrate'),
     'complete-after-VERIFY-ONLY.json':native_payload(registry,full,checkpoint_sha,'VERIFY ONLY — complete furnished cluster, actual floors/stack supports and lanes',tags=tags),
     'normal-joins-SETTLE-ONLY.json':native_payload(registry,{q:s for q,s in states.items()if key(s)not in VOIDS},checkpoint_sha,'NORMAL JOINS ONLY — new composed Tortuga cluster, no current inventory replay')}
    raw={}
    for n,d in docs.items():
        if n!='cluster-PROPOSAL.json':d.update(construction_forbidden=True,verification_only=True)
        raw[n]=(json.dumps(d,separators=(',',':'))+'\n').encode()
    manifest={'format':'awft-tortuga-linked-cluster:1','cluster':cluster,'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'source_sha256':digest(Path(__file__)),
              'recipe_source_sha256':RECIPE_SHA,'definition_source':definition_source.name,'definition_source_sha256':digest(definition_source),'definition_sha256':definition_sha,'design':definition['design'],'buildings':buildings,'main_columns':len(main),'lane_columns':len(lane),'routes':routes,'targets':len(states),'pinned_zinc_substrate_factory':zinc_proof,
              'retained_full_stack_cells':len(supports),'retained_existing_source_walking_AIR':[list(q)for q in sorted(retained_walk_air)],'literal_ground_route_candidates':len(walk_field),'kept_sources':refs,'saved_sources':sources,'outdoor_rule':rule,'reader_peak_RSS_bytes':max(q['owned_reader_rss_bytes']for q in budgets),'reserve_guard':reserve,
              'files':{n:{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}for n,b in raw.items()},'native_actions':0,'world_writes':0,'old_houses_or_inventories_removed':0,
              'native_cameras':[{'name':b['name']+' actual furnished '+room['name'],'feet':[room['world_standing_point'][0]+.5,room['world_standing_point'][1],room['world_standing_point'][2]+.5],'look_at':[b['origin'][0]+2,b['origin'][1]+room['standing_point'][1]+1,b['origin'][2]+3]}for b in buildings for room in b['rooms']],
              'status':'SOURCE/SAVED PREIMAGE ONLY; fresh native before/support, placement/joins/full verification and actual street/interior views required',
              'density_revision':'Unplaced first Quill5827/264-lane proposal retained; this explicit additional west entrance removes the unnecessary perimeter route and prioritizes building footprint',
              'limits':['No array-generated lots or native replication approval from local checks','No density-complete assertion from this bounded cluster','Native models/stairs/survival/AI/beauty remain separate real-world gates']}
    raw['manifest.json']=(json.dumps(manifest,separators=(',',':'))+'\n').encode()
    if sum(map(len,raw.values()))>32*MIB:raise UserError('Finite32MiB cluster output cap')
    o=home/'staging'/('tortuga-'+cluster+'-'+str(time.time_ns()));o.mkdir()
    for n,b in raw.items():(o/n).open('xb').write(b)
    return {'folder':str(o),'manifest_sha256':digest(o/'manifest.json'),'targets':len(states),'buildings':len(buildings),'rooms':sum(len(b['rooms'])for b in buildings),'lane_columns':len(lane),'files':manifest['files'],'native_actions':0}


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--home',type=Path,required=True);a.add_argument('--checkpoint-id',required=True);a.add_argument('--checkpoint-sha',required=True);a.add_argument('--cluster',choices=CLUSTERS,required=True);args=a.parse_args();print(json.dumps(prepare(args.home,args.checkpoint_id,args.checkpoint_sha,args.cluster),indent=2))
