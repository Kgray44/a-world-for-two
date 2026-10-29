"""Small lush western Tortuga pockets after the owner's map review.

Two different open shelters, rooted modded shrubs/flowers and contained
greens. No tree imitation, greenhouse grid, fauna, world call or stock write.
"""
from __future__ import annotations
import argparse,hashlib,json,time,zipfile,html
from collections import Counter
from pathlib import Path

from control_room.common import UserError,digest,read_json
from tools import artistic_tortuga_west_narrow_workrooms as narrow
from tools.artistic_tortuga_frontages import AIR,POTS,key,rect
from tools.artistic_west_r2_frontage import Frontage,canonical_joins
from tools.artistic_north_bank_east import NorthTerrain,native_payload,GROUND,SOFT,NORTH_SOFT,AIR as VOIDS
from tools.artistic_bridge_refinement import flatten
from tools.artistic_spawn_plaza import state
from tools.artistic_materials import require_material_rule,require_outdoor_rule
from tools.artistic_create_substrate import verify_zinc_factory,qualified_mount
from tools.artistic_zipline_catenary import reader_budget
from tools.playtest import guard

MIB=1024**2
NARROW=('staging/tortuga-narrow-workrooms-1793219506153531200/manifest.json','8b39adfbdab0ceaffe848fc8a5f208e4990a4a282a2c5a7fb0356e39f6e0da4d')
FIELD=('staging/tortuga-narrow-workrooms-1793219506153531200/field-READONLY.json','e59a92bbec943588438782c8ed7fdd4ebacc80f422861766e709e2a5aa1b8880')
ORIGINAL_SOURCE_SHA='bc7af0598925642e2a35245ace4dd776afcc6e4823a91c89180b74c0d34dc4f8'
INNER_FIELD=('staging/tortuga-current-field-1793214975847021000/field-READONLY.json','52b3bfded391a9ef1363acd57ffd859068dfdbe50280a08b8daa3a8ce7649e75')
INNER_STREET=('staging/west-street-stock-SNBT-fixed-20261028T0317Z/future-walk-furniture-reservation-ONLY.json','59e708726681c29ef962f632f3572369ec1db0299d58e11b454b6259b09be905')
SHRUBS=('regions_unexplored:lavender_wisteria_shrub','regions_unexplored:cherry_shrub','regions_unexplored:pink_magnolia_shrub','regions_unexplored:salmon_wisteria_shrub')
FLOWERS=('regions_unexplored:blue_lupine','regions_unexplored:pink_lupine','regions_unexplored:purple_lupine','regions_unexplored:aster')
POTTED=('regions_unexplored:potted_blue_lupine','regions_unexplored:potted_pink_lupine',POTS[4],POTS[0])

# These are individual dry-land compositions, not an automatic planting raster.
BEDS=(
 ("Tavern's narrow side garden",0,((1052,-1272),(1052,-1269),(1052,-1266),(1052,-1263),(1052,-1260)),((1052,-1271),(1052,-1268),(1052,-1265),(1052,-1262))),
 ('Hall-side flowering return',1,((1024,-1279),(1027,-1279),(1030,-1279),(1033,-1279)),((1025,-1279),(1028,-1279),(1031,-1279))),
 ("Captain's quiet northern border",2,((1035,-1298),(1037,-1297),(1040,-1296),(1044,-1296),(1047,-1296)),((1036,-1297),(1038,-1296),(1042,-1296),(1046,-1296))),
 ("Western landing's low garden",3,((1090,-1259),(1092,-1259),(1095,-1259),(1097,-1258),(1088,-1257),(1086,-1256)),((1091,-1259),(1093,-1259),(1096,-1258),(1087,-1256))),
 ("Ferryman's sheltered flower nook",2,((1034,-1241),(1036,-1241),(1035,-1239),(1036,-1236)),((1035,-1241),(1034,-1239),(1036,-1238))),
 ('Old sea-edge fern and blossom pocket',1,((984,-1268),(986,-1267),(985,-1265),(986,-1263),(989,-1268),(991,-1269)),((985,-1268),(984,-1266),(987,-1267),(990,-1269))),
 ("Northern pennant-maker's garden",0,((1014,-1303),(1015,-1306),(1016,-1306)),((1014,-1302),(1015,-1305))),
 ("Gull shelter's eastern flowers",3,((1008,-1266),(1011,-1266),(1014,-1265)),((1009,-1266),(1012,-1266),(1013,-1265))),
 ("Low tavern step's warm corner",2,((1050,-1272),(1051,-1270)),((1050,-1271),(1051,-1271))),
)
BENCHES=(
 ("Captain's northern reading perch",(1035,64,-1296),'east'),
 ("Gull shelter's sunny sorting seat",(1008,64,-1264),'north'),
 ("Tavern's little waiting perch",(1050,64,-1273),'north'),
)


def shelter(registry,origin,*,lean=False):
    depth=4 if lean else 5;p=Frontage(registry,origin);p.owner='Gull’s Rest arbor'if lean else'The Splice Garden pavilion'
    cells=rect(0,0,4,depth-1);p.main[p.owner]=cells;p.levels[p.owner]=[set(cells)];p.floor(cells,0)
    for x,z in cells:
        for y in(1,2,3):p.put(x,y,z,AIR)
    for x,z in((0,0),(4,0),(0,depth-1),(4,depth-1)):
        for y in(1,2,3):p.put(x,y,z,'minecraft:stripped_dark_oak_log',axis='y',role='three-high rooted open-pavilion post')
    for x in range(5):
        for z in(0,depth-1):p.beam(x,4,z,'x',wood='charred_spruce',role='supported shallow open-pavilion eave tie')
    for z in range(1,depth-1):
        for x in(0,4):p.beam(x,4,z,'z',wood='dark_oak',role='continuous supported side eave')
    if lean:
        for x in range(5):
            for z in range(depth):p.put(x,4+(2-x//2),z,'mcwroofs:spruce_lower_roof',facing='west',half='bottom',shape='straight',role='quiet one-way low arbor roof')
        passage=[(x,1,z)for x in(2,3)for z in range(0,3)]
        p.put(1,1,2,'handcrafted:dark_oak_bench',facing='east',shape='single',color='brown',waterlogged=False,role='actual sheltered sea-edge waiting bench')
        plants=((0,1,1,POTTED[2]),(4,1,1,POTTED[0]),(3,1,3,POTTED[1]))
        light=(3,3,1);outside={(origin[0]+x,origin[2]+z)for x in(2,3)for z in(-2,-1)}
    else:
        p.roof((0,0,4,4),4,(0,1,2,1,0),family='dark_oak',annex=True)
        passage=[(x,1,z)for x in(1,2)for z in range(1,5)]
        p.put(3,1,2,'handcrafted:dark_oak_bench',facing='west',shape='single',color='brown',waterlogged=False,role='actual small pavilion conversation bench')
        plants=((0,1,2,POTTED[2]),(3,1,1,POTTED[0]),(3,1,3,POTTED[3]))
        light=(2,3,1);outside={(origin[0]+x,origin[2]+z)for x in(1,2)for z in(5,6)}
    p.reserve('Actual two-wide open-shelter passage',passage)
    for x,y,z,pot in plants:p.put(x,y,z,pot,role='contained native flower or fern on the full founded deck')
    x,y,z=light;p.put(x,y,z,'minecraft:lantern',hanging=True,waterlogged=False,role='small practical warm shelter light');p.put(x,y+1,z,'minecraft:dark_oak_planks',role='actual full native lantern mount')
    p.supports.append({'detail':list(light),'support':[x,y+1,z],'role':'warm task light attached to the real roof tie'})
    canonical_joins(p);proof=require_material_rule(p.blocks,p.owner+' complete deck/frame/roof')
    for route in p.routes:
        for x,y,z in route['positions']:
            if any(p.blocks.get((x,y+h,z),AIR)!=AIR for h in(0,1))or p.blocks.get((x,y-1,z),AIR)==AIR:raise UserError('An open shelter needs a real clear founded two-wide passage')
    for q,s in p.blocks.items():
        if key(s)in POTTED and p.blocks.get((q[0],q[1]-1,q[2]),AIR)==AIR:raise UserError('Every contained plant needs an actual full deck')
    return p,proof,outside


def construct(registry):
    states={};objects=[];walks=set();roots=set();contexts=[];proofs=[]
    def put(q,name,role,**props):
        value=state(registry,name,**props)
        if q in states and states[q]!=value:raise UserError('Distinct garden compositions overlap: '+str((q,states[q],value)))
        states[q]=value;objects.append({'position':list(q),'block':name,'role':role})
    for origin,lean in(((1059,63,-1254),False),((1001,63,-1267),True)):
        p,proof,outside=shelter(registry,origin,lean=lean);proofs.append(proof)
        for q,s in p.blocks.items():
            w=tuple(q[i]+origin[i]for i in range(3))
            if w in states and states[w]!=s:raise UserError('Keep the two actual shelters distinct')
            states[w]=s
        objects.extend({'position':[r['position'][i]+origin[i]for i in range(3)],'block':r['block'],'role':r['role']}for r in p.props)
        walks|=outside|{(x+origin[0],z+origin[2])for r in p.routes for x,y,z in r['positions']}
        contexts.append({'name':p.owner,'type':'small open garden shelter, not a dwelling','origin':list(origin),'columns':len(p.main[p.owner]),'two_wide_entry_columns':[list(q)for q in sorted(outside)]})
    for name,family,shrubs,flowers in BEDS:
        for x,z in shrubs:
            roots.add((x,z));put((x,63,z),'minecraft:dirt','native shrub root soil on a verified stable dry stack')
            for half,y in(('lower',64),('upper',65)):put((x,y,z),SHRUBS[family],'real rooted double-height '+name,half=half)
        for x,z in flowers:
            roots.add((x,z));put((x,63,z),'minecraft:dirt','native flower root soil on a verified stable dry stack')
            put((x,64,z),FLOWERS[family],'rooted modded flower in '+name)
        contexts.append({'name':name,'type':'individually composed shrub/flower pocket','root_columns':[list(q)for q in shrubs+flowers],'native_saplings':0})
    for name,q,face in BENCHES:
        x,y,z=q;put((x,63,z),'minecraft:mossy_stone_bricks','small full founded sitting plinth')
        put(q,'handcrafted:dark_oak_bench',name,facing=face,shape='single',color='brown',waterlogged=False)
        contexts.append({'name':name,'type':'one small real sitting place','position':list(q)})
    # Keep a literal two-wide shoulder alongside the long side garden.
    walks|={(x,z)for x in(1053,1054)for z in range(-1272,-1258)}
    require_outdoor_rule({q:s for q,s in states.items()if not any(q[0]in range(r[0],r[0]+5)and q[2]in range(r[2],r[2]+d)for r,d in(((1059,63,-1254),5),((1001,63,-1267),4)))},'Rooted western garden pockets and isolated sitting plinths')
    if roots&walks:raise UserError('No shrub or flower may occupy the protected two-wide garden shoulder')
    return states,objects,walks,roots,contexts,proofs


def garden_map(states,roots,walks,contexts,field):
    points={(x,z)for x,y,z in states}|walks
    x0=min(x for x,z in points)-3;z0=min(z for x,z in points)-3;x1=max(x for x,z in points)+3;z1=max(z for x,z in points)+3
    scale=9;width=(x1-x0+1)*scale;height=(z1-z0+1)*scale+112
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="#f3efe3"/>',
      '<g font-family="sans-serif" fill="#30382d"><text x="12" y="23" font-size="16">WEST GARDEN POCKETS — SOURCE PLANNING ONLY</text>',
      '<text x="12" y="42" font-size="10">North up; gray retained source, brown two small shelters, green rooted gardens, gold clear walking body.</text>',
      '<text x="12" y="57" font-size="10">Not a Native screenshot. Blank areas confer no dry-ground, demolition or placement authority.</text></g>']
    def tile(x,z,color,opacity=1):return f'<rect x="{(x-x0)*scale}" y="{72+(z-z0)*scale}" width="{scale}" height="{scale}" fill="{color}" opacity="{opacity}"/>'
    for cells in field['retained_source_main_footprints'].values():
        for x,z in cells:
            if x0<=x<=x1 and z0<=z<=z1:out.append(tile(x,z,'#a7a79a',.6))
    for x,z in walks:out.append(tile(x,z,'#d2b776'))
    for x,y,z in states:
        if(x,z)not in roots and y>=67:out.append(tile(x,z,'#665442',.7))
    for x,z in roots:out.append(tile(x,z,'#668c52'))
    for c in contexts:
        cells=c.get('root_columns')
        if not cells:continue
        x=sum(q[0]for q in cells)/len(cells);z=sum(q[1]for q in cells)/len(cells)
        out.append(f'<text x="{(x-x0)*scale+5:g}" y="{72+(z-z0)*scale-3:g}" fill="#28402b" font-family="sans-serif" font-size="8">{html.escape(c["name"])}</text>')
    shade_count=sum(c.get('type','').startswith('small open')for c in contexts);seat_count=sum('sitting place'in c.get('type','')for c in contexts)
    out.append(f'<text x="12" y="{height-12}" font-family="sans-serif" font-size="10">{shade_count} open shelters · {len(roots)} root columns · {seat_count} small seats · fresh Native admission and actual visual review pending.</text></svg>')
    return''.join(out).encode()


def own_shelter_walk_before(observed,planned):
    """Natural soft cover may be cleared only inside the new shelter target.

    Unwritten outside walking context must already be actual AIR. The
    exact natural cover remains in the before proof; it is not rewritten
    as an expected old AIR state.
    """
    if observed is None or'waterlogged=true'in observed:return False
    return key(observed)in(VOIDS|SOFT|NORTH_SOFT if planned==AIR else VOIDS)


def inner_recipe(path):
    """Data-only additive design; bridge-approach land remains another owner."""
    path=Path(path).resolve();root=Path(__file__).resolve().parents[1]/'proposals/inner-west-gardens'
    if not path.is_relative_to(root)or not path.is_file()or path.stat().st_size>64*1024:raise UserError('Bounded repository-owned inner garden recipe required')
    data=read_json(path)
    if data.get('format')!='awft-inner-west-garden-design:1'or data.get('scope_x')!=[1100,1185]or data.get('original_garden_source_sha256')!=ORIGINAL_SOURCE_SHA:
        raise UserError('Exact additive inner-West design scope/provenance required')
    if not 1<=len(data.get('shelters',()))<=2 or not 1<=len(data.get('beds',()))<=16 or len(data.get('benches',()))>6 or len(data.get('potted_plinths',()))>8:raise UserError('Finite inner garden design counts exceeded')
    coordinates=[]
    for row in data['shelters']:
        if type(row.get('lean'))is not bool or len(row.get('origin',()))!=3 or row['origin'][1]!=63:raise UserError('Actual low-land native shelter origin required')
        x,y,z=row['origin'];coordinates.extend((xx,z)for xx in range(x,x+5))
        coordinates+=list(map(tuple,row.get('entry_centres',())))
    for row in data['beds']:
        if type(row.get('family'))is not int or not 0<=row['family']<len(SHRUBS):raise UserError('Selected native shrub family required')
        coordinates+=list(map(tuple,row.get('shrubs',())))+list(map(tuple,row.get('flowers',())))
    for row in list(data.get('benches',()))+list(data.get('potted_plinths',())):coordinates.append(tuple(row['xz']))
    for row in data.get('entry_steps',()):coordinates.append(tuple(row['xz']))
    coordinates+=list(map(tuple,data.get('walking_columns',())))
    if len(coordinates)>300 or any(len(q)!=2 or any(type(v)is not int for v in q)or not 1100<=q[0]<=1185 or not-1310<=q[1]<=-1185 for q in coordinates):
        raise UserError('Keep finite inner-West authored cells; no bridge-approach permission')
    return data,{'relative':str(path.relative_to(Path(__file__).resolve().parents[1])),'sha256':digest(path),'original_garden_source_sha256':ORIGINAL_SOURCE_SHA}


def construct_inner(registry,data):
    """Reuse the frozen native shelters and palettes; only design data varies."""
    states={};objects=[];walks=set();roots=set();contexts=[];proofs=[]
    def put(q,name,role,**props):
        value=state(registry,name,**props)
        if q in states and states[q]!=value:raise UserError('Inner garden designs overlap: '+str(q))
        states[q]=value;objects.append({'position':list(q),'block':name,'role':role})
    for row in data['shelters']:
        origin=tuple(row['origin']);p,proof,outside=shelter(registry,origin,lean=row['lean']);proofs.append(proof)
        for q,s in p.blocks.items():
            w=tuple(q[i]+origin[i]for i in range(3))
            if w in states and states[w]!=s:raise UserError('Inner shelters overlap')
            states[w]=s
        objects.extend({'position':[r['position'][i]+origin[i]for i in range(3)],'block':r['block'],'role':r['role']}for r in p.props)
        internal={(x+origin[0],z+origin[2])for r in p.routes for x,y,z in r['positions']}
        if row.get('entry_centres'):
            centres=list(map(tuple,row['entry_centres']))
            if not 2<=len(centres)<=4 or any(abs(a[0]-b[0])+abs(a[1]-b[1])!=1 for a,b in zip(centres,centres[1:])):raise UserError('A bent two-wide entry needs finite adjacent orthogonal centres')
            outside={(x+dx,z+dz)for x,z in centres for dx,dz in((0,0),(1,0),(0,1),(1,1))}
            if len(outside&internal)<2:raise UserError('The bent entry must actually meet the two-wide shelter passage')
        walks|=outside|internal
        contexts.append({'name':row['name'],'type':'small open garden shelter, not a dwelling','origin':list(origin),'columns':len(p.main[p.owner]),'two_wide_entry_columns':[list(q)for q in sorted(outside)]})
    for row in data['beds']:
        name=row['name'];family=row['family'];shrubs=list(map(tuple,row['shrubs']));flowers=list(map(tuple,row['flowers']))
        for x,z in shrubs:
            roots.add((x,z));put((x,63,z),'minecraft:dirt','literal stable native root soil')
            for half,y in(('lower',64),('upper',65)):put((x,y,z),SHRUBS[family],'real rooted '+name,half=half)
        for x,z in flowers:
            roots.add((x,z));put((x,63,z),'minecraft:dirt','literal stable native flower soil');put((x,64,z),FLOWERS[family],'rooted modded '+name)
        contexts.append({'name':name,'type':'individually composed inner garden','root_columns':[list(q)for q in shrubs+flowers],'native_saplings':0})
    for row in data.get('benches',()):
        x,z=row['xz'];put((x,63,z),'minecraft:mossy_stone_bricks','small actual full sitting plinth')
        put((x,64,z),'handcrafted:dark_oak_bench',row['name'],facing=row['face'],shape='single',color='brown',waterlogged=False)
        contexts.append({'name':row['name'],'type':'one real small sitting place','position':[x,64,z]})
    for row in data.get('potted_plinths',()):
        x,z=row['xz'];family=row['family']
        if type(family)is not int or not 0<=family<len(POTTED):raise UserError('Real selected contained flower required')
        put((x,63,z),'minecraft:mossy_stone_bricks','full contained-plant plinth on verified native substrate')
        put((x,64,z),POTTED[family],row['name'])
        contexts.append({'name':row['name'],'type':'one contained flower/fern with full rooted plinth','position':[x,64,z]})
    for row in data.get('entry_steps',()):
        x,z=row['xz']
        if row['face']not in('north','south','west','east'):raise UserError('Actual normal threshold-stair direction required')
        put((x,63,z),'minecraft:dark_oak_stairs','normal half-step from literal lower ground to the founded shelter',facing=row['face'],half='bottom',shape='straight',waterlogged=False)
    walks.update(map(tuple,data.get('walking_columns',())))
    if roots&walks:raise UserError('Rooted plants must preserve the real two-wide inner shoulders')
    if any(not 1100<=x<=1185 or not-1310<=z<=-1185 for x,y,z in states)or any(not 1100<=x<=1185 or not-1310<=z<=-1185 for x,z in walks):raise UserError('No target or visiting body may enter Root bridge approach or leave the inner design limit')
    outside={q:s for q,s in states.items()if not any(ox<=q[0]<=ox+4 and oz<=q[2]<=oz+(3 if row['lean']else 4)for row in data['shelters']for ox,oy,oz in(tuple(row['origin']),))}
    require_outdoor_rule(outside,'Inner-West rooted garden borders and small full plinths')
    return states,objects,walks,roots,contexts,proofs


def prepare(home,checkpoint_id,checkpoint_sha,*,inner_recipe_path=None):
    reserve=guard(8*MIB,32*MIB);budgets=[reader_budget()]
    home=narrow.fill.private_home(home);receipt=narrow.fill.stopped(home,checkpoint_id,checkpoint_sha)
    design,design_ref=inner_recipe(inner_recipe_path)if inner_recipe_path is not None else(None,None)
    field_spec=INNER_FIELD if design is not None else FIELD;scope=(1100,1185)if design is not None else(968,1099)
    for relative,sha in(field_spec,NARROW):
        if digest(home/relative)!=sha:raise UserError('Exact four-workroom source and its field required')
    field=read_json(home/field_spec[0]);nm=read_json(home/NARROW[0])
    if(field['checkpoint_id'],field['checkpoint_sha256'])!=(checkpoint_id,checkpoint_sha):raise UserError('No old garden before-state rebind')
    registry=read_json(home/'dashboard/settlement/registry.json');states,objects,walks,roots,contexts,proofs=construct_inner(registry,design)if design is not None else construct(registry)
    keep,forest,heritage,_,_,refs=narrow.fill.retained_context(home,registry)
    prior,prior_refs,_=narrow.previous.construction_targets(home,narrow.coast.FIVE+narrow.spit.QUEUED+narrow.FUTURE+(NARROW,));keep.update(prior);refs+=prior_refs
    sm=read_json(home/narrow.SHELLS[0])
    for i in range(1,4):
        p=(home/narrow.SHELLS[0]).parent/f'west15-{i}-PROPOSAL.json'
        if digest(p)!=sm['files'][p.name]['sha256']:raise UserError('Keep every exact later roof/depth target')
        keep.update(flatten(read_json(p)))
    source_route_columns=set()
    for relative,sha in narrow.coast.FIVE+narrow.spit.QUEUED+narrow.FUTURE+(NARROW,):
        doc=read_json(home/relative)
        for r in doc.get('routes',[]):source_route_columns.update(map(tuple,r.get('columns_xz',())))
    if design is not None:
        street=home/INNER_STREET[0]
        if digest(street)!=INNER_STREET[1]:raise UserError('Keep exact old three-wide streets, furnishings and body mask')
        keep.update(flatten(read_json(street)));refs.append({'relative':INNER_STREET[0],'sha256':INNER_STREET[1],'role':'Preserve current324-column streets/furnishings/body; not placement ownership'})
    free={tuple(r[:2])for r in field['eligible_columns_READONLY']};narrow_main={tuple(q)for b in nm['buildings']for q in b['main_columns_xz']};free-=narrow_main
    if design is not None:free-={(x,z)for x,y,z in keep}|heritage|forest
    touched={(x,z)for x,y,z in states}
    if not touched<=free:raise UserError('Garden remains within the actual saved dry unused fields: '+str(sorted(touched-free)[:12]))
    if touched&source_route_columns:raise UserError('Keep every actual authored public route: '+str(sorted(touched&source_route_columns)[:12]))
    collision=[q for q in states if q in keep or(q[0],q[2])in heritage|forest or not scope[0]<=q[0]<=scope[1]]
    if collision:raise UserError('Keep all old/new architecture, BEs, room AIR and zipline: '+str(collision[:12]))
    zinc=verify_zinc_factory(home);terrain=NorthTerrain(home,receipt,registry);before={};supports={};clearance={};began=time.monotonic();out=home/'staging'/(('tortuga-inner-west-gardens-'if design is not None else'tortuga-west-garden-pockets-')+str(time.time_ns()));out.mkdir()
    try:
        for x,z in sorted(touched|walks):
            mount=qualified_mount(terrain.state,x,z,zinc)
            if not mount['stable']:raise UserError('No planting or shelter on an unsafe gravity stack: '+str((x,z,mount)))
            for xx,y,zz,s in mount['stack']:
                if(xx,y,zz)in terrain.entities:raise UserError('No BE may become a garden support')
                supports[xx,y,zz]=s
        for i,q in enumerate(sorted(states,key=lambda q:(q[0]//16,q[2]//16,q[1],q[0],q[2]))):
            current=terrain.state(*q)
            if q in terrain.entities or current is None or'waterlogged=true'in current or key(current)not in(GROUND|VOIDS|SOFT|NORTH_SOFT if q[1]==63 else VOIDS|SOFT|NORTH_SOFT):
                raise UserError('Preserve every saved water/object/tree/BE/unknown: '+str((q,current)))
            before[q]=current
            if i%128==0:budgets.append(reader_budget())
            if time.monotonic()-began>90:raise UserError('Finite90s garden reader exceeded')
        explicit_soft_walk_clear=[];actual_walk_surfaces=[]
        for x,z in walks:
            if(x,z)in roots:raise UserError('A real rooted garden must leave its two-wide visiting shoulder')
            floor_y=63;floor=states.get((x,63,z),terrain.state(x,63,z))
            if design is not None and floor is not None and key(floor)in VOIDS:
                floor_y=62;floor=terrain.state(x,62,z)
            if floor is None or key(floor)in VOIDS or'waterlogged=true'in floor:raise UserError('A sheltered walking shoulder must have literal dry flooring')
            if design is not None and(x,floor_y,z)not in states:
                if(x,floor_y,z)in terrain.entities or key(floor)not in GROUND|{'minecraft:dirt','minecraft:cobblestone','minecraft:stone_bricks','minecraft:mossy_stone_bricks','minecraft:polished_andesite','chipped:small_stone_bricks','minecraft:cobbled_deepslate'}:
                    raise UserError('An unchanged inner visiting floor needs an exact native full-floor identity, not an unknown block or BE')
                before[x,floor_y,z]=floor;supports[x,floor_y,z]=floor
            actual_walk_surfaces.append({'xz':[x,z],'floor_y':floor_y,'floor_state':floor,'headroom_y':[floor_y+1,floor_y+2],
               'surface_kind':'native normal half-stair transition'if key(floor).endswith('_stairs')else'literal unchanged full floor'if(x,floor_y,z)not in states else'new founded shelter deck'})
            for y in(floor_y+1,floor_y+2):
                q=x,y,z;observed=terrain.state(*q)
                # A finite, newly authored walking shoulder can explicitly
                # remove its exact natural non-waterlogged cover. Existing
                # source AIR/fixtures are not newly owned by this clause.
                if q not in states and q not in keep and(x,z)in free and observed is not None and key(observed)in SOFT|NORTH_SOFT and'waterlogged=true'not in observed and q not in terrain.entities:
                    states[q]=AIR;explicit_soft_walk_clear.append({'position':list(q),'exact_before':observed,'after':AIR})
                if not own_shelter_walk_before(observed,states.get(q))or q in terrain.entities or states.get(q,AIR)!=AIR:raise UserError('Protect genuine two-high walking body: '+str((q,observed,states.get(q))))
                before[q]=observed;clearance[q]=AIR
        saved=terrain.snapshot.sources;terrain.close();terrain=None
        full={**supports,**states,**clearance};documents={
          'garden-PROPOSAL.json':native_payload(registry,states,checkpoint_sha,'TORTUGA INNER WEST — rooted garden continuation and small open shelters'if design is not None else'TORTUGA WEST — two small open shelters and nine rooted lush pockets'),
          'before-VERIFY-ONLY.json':native_payload(registry,before,checkpoint_sha,'VERIFY ONLY — actual garden/shelter targets and retained walking body'),
          'stable-supports-VERIFY-ONLY.json':native_payload(registry,supports,checkpoint_sha,'VERIFY ONLY — complete current native footing stacks'),
          'complete-after-VERIFY-ONLY.json':native_payload(registry,full,checkpoint_sha,'VERIFY ONLY — new rooted plants/shelters and unchanged walking/support context'),
          'normal-joins-SETTLE-ONLY.json':native_payload(registry,{q:s for q,s in states.items()if s!=AIR},checkpoint_sha,'NORMAL UPDATE ONLY — native plant support and geometry; no inventory replay')}
        raw={}
        for name,doc in documents.items():
            if name!='garden-PROPOSAL.json':doc.update(verification_only=True,construction_forbidden=True)
            raw[name]=(json.dumps(doc,separators=(',',':'))+'\n').encode()
        ru=home/'server/mods/regions-unexplored-0.6.3-neoforge-21.1.jar'
        with zipfile.ZipFile(ru)as jar:
            shrub=jar.read('net/regions_unexplored/block/type/shrub/ShrubBlock.class');tag=jar.read('data/regions_unexplored/tags/block/supports/shrubs.json');ids=json.loads(jar.read('data/regions_unexplored/tags/block/shrubs.json'))['values']
        if hashlib.sha256(shrub).hexdigest()!='ac0153170c56c14785ab262f7c70a088ddb50634857b23dcd7eac4d13882f710'or not set(SHRUBS)<=set(ids)or json.loads(tag)['values']!=['#minecraft:dirt']:
            raise UserError('Exact pinned native rooted-shrub anatomy/support witness changed')
        manifest={'format':'awft-tortuga-west-garden-pockets:1','source_sha256':digest(Path(__file__)),'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,
          'contexts':contexts,'root_columns':len(roots),'shelters':2,'new_targets':len(states),'actual_existing_BE_targets':0,'inventory_writes':0,'native_actions':0,'world_writes':0,
          'botanical_species':dict(Counter(key(s)for s in states.values()if key(s).startswith(('regions_unexplored:','fishofthieves:')))),
          'contained_supports_and_no_new_trees':True,'full_shelter_material_rule':proofs,'objects':objects,'protected_walking_columns':[list(q)for q in sorted(walks)],
          'bounded_new_shoulders_explicit_natural_cover_clear':explicit_soft_walk_clear,
          'source_dependencies':refs,'future_west15':narrow.SHELLS,'four_occupied_workrooms':NARROW,'saved_sources':saved,'pinned_zinc_factory':zinc,
          'native_shrub_support_witness':{'jar':ru.name,'jar_sha256':digest(ru),'class_sha256':hashlib.sha256(shrub).hexdigest(),'class':'ShrubBlock extends ordinary DoublePlantBlock; mayPlaceOn uses SUPPORTS_SHRUBS','support_tag_sha256':hashlib.sha256(tag).hexdigest(),'support_values':['#minecraft:dirt'],'selected_registered_shrub_ids':list(SHRUBS),'no_bonemeal_tree_or_SaplingBlock':True,'native_concrete_species_survival_still_pending':True},
          'reserve_guard':reserve,'reader_peak_RSS_bytes':max(b['owned_reader_rss_bytes']for b in budgets),'status':'SOURCE ONLY; fresh native before/support, placement/normal-survival/full verification and actual art views remain required',
          'limits':['Finite pockets do not claim every city gap landscaped','Actual two-high public source routes, flight, current objects and all retained stock remain protected','No sapling/bonemeal/default tree imitation, entities, tamed ownership or automatic planter','Snapshot6ad does not confer authority over later human changes; fresh native before must match']}
        if design is not None:manifest.update(format='awft-tortuga-inner-west-gardens:1',design_source=design_ref,scope_x=list(scope),original_west_packet_immutable=True,
           original_west_source_sha256=ORIGINAL_SOURCE_SHA,bridge_approach_X_above1185_has_no_authority=True,
           literal_walking_surfaces=actual_walk_surfaces,three_half_stair_transitions=design.get('entry_steps',()),shelters=len(design['shelters']))
        raw['garden-map-PLAN-ONLY.svg']=garden_map(states,roots,walks,contexts,field)
        manifest['files']={name:{'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}for name,data in raw.items()}
        raw['manifest.json']=(json.dumps(manifest,separators=(',',':'))+'\n').encode()
        if sum(map(len,raw.values()))>16*MIB:raise UserError('Finite16MiB garden output exceeded')
        for name,data in raw.items():(out/name).open('xb').write(data)
        return{'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'targets':len(states),'root_columns':len(roots),'files':manifest['files'],'native_actions':0}
    except Exception as exc:
        (out/'refusal.json').open('x',encoding='utf-8').write(json.dumps({'reason':type(exc).__name__+': '+str(exc),'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'source_sha256':digest(Path(__file__)),'native_actions':0,'world_writes':0})+'\n')
        raise UserError(str(exc)+'; retained '+str(out))from exc
    finally:
        if terrain is not None:terrain.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--home',type=Path,required=True);parser.add_argument('--checkpoint-id',required=True);parser.add_argument('--checkpoint-sha',required=True);parser.add_argument('--inner-recipe',type=Path)
    args=parser.parse_args();print(json.dumps(prepare(args.home,args.checkpoint_id,args.checkpoint_sha,inner_recipe_path=args.inner_recipe),indent=2))
