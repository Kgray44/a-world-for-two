"""Custody-bound muted roofs and actual exterior depth for the rejected West15.

No inventory relocation, source replay, native command or running-world read.
Every changed old solid must still exactly match its original construction.
Unattributed state deltas are retained. Full typed current NBT stays private.
"""
from __future__ import annotations
import argparse,hashlib,json,time,math,html
from collections import Counter,defaultdict
from pathlib import Path
from types import SimpleNamespace

from control_room.common import UserError,digest,read_json
from tools.artistic_north_rebuild_custody import load_batches,decoded_chunk,typed,inventory_facts
from tools.artistic_north_bank_east import NorthTerrain,native_payload,preservation
from tools.artistic_tortuga_frontages import AIR,POTS,key
from tools.artistic_spawn_plaza import state
from tools.artistic_west_r2_frontage import canonical_joins
from tools.settlement_attractions import properties
from tools.artistic_materials import require_material_rule
from tools import artistic_tortuga_fill as fill
from tools import artistic_tortuga_west_approved_blocks as previous
from tools import artistic_tortuga_western_spit as spit
from tools.artistic_zipline_catenary import reader_budget
from tools.playtest import guard

MIB=1024**2
OPAQUE_MAP={
 'dawnoftimebuilder:yellow_plastered_stone':'minecraft:brown_terracotta',
 'dawnoftimebuilder:red_plastered_stone':'minecraft:brown_terracotta',
 'dawnoftimebuilder:blue_plastered_stone':'minecraft:gray_terracotta',
 'dawnoftimebuilder:green_plastered_stone':'minecraft:gray_terracotta',
 'minecraft:cyan_terracotta':'minecraft:gray_terracotta',
}
FULL_BACKING={'minecraft:stone_bricks','minecraft:mossy_stone_bricks','minecraft:bricks',
 'minecraft:dark_oak_planks','minecraft:spruce_planks','minecraft:stripped_dark_oak_log','minecraft:stripped_spruce_log',
 'minecraft:brown_terracotta','minecraft:gray_terracotta','minecraft:green_terracotta','minecraft:red_terracotta','minecraft:light_gray_terracotta',
 *OPAQUE_MAP}
# Exact BlockInit supplier -> BaseRoof mappings from the pinned 2.3.2 JAR.
# RoofGlass, Lower, Steep and the ridge class are deliberately not guessed
# to share BaseRoof's updateShape rule.
BASE_ROOF_IDS={'mcwroofs:'+family+'_roof'for family in('spruce','dark_oak','bricks','brown_terracotta','red_terracotta','stone_bricks')}
PINNED_ROOF_SHA512='c0e82a3d0a3ab2f2fac5fb0bdd7c7c228f084feaa816540d3d9524f341c8b108c3bb1afecadae2e8118e6c93f0e73280c62da1af4349aca87b6aa337e5e22ae4'
FUTURE=(
 ('staging/tortuga-western-spit-1793215072699978000/manifest.json','cbb7810513c9718345cff6440878508f529b3d1394aab854cd47bd3b5c5b9293'),
 ('staging/tortuga-fill-inner-west-current-9-1793215653202868100/manifest.json','c42ad52915b0984087bcfd27e7665fd306527a833fbc96c4b3595b4870450cdc'),
)


def roof_axis(value):
    face=properties(value).get('facing')
    return'ew'if face in('east','west')else'ns'if face in('north','south')else None


def owned_surface_origin(expected,actual,independent_canonical):
    if actual==expected:return'EXACT_ORIGINAL_SOURCE_STATE'
    ident=key(expected)
    if ident!=key(actual):return None
    old,new=properties(expected),properties(actual)
    differing={k for k in set(old)|set(new)if old.get(k)!=new.get(k)}
    if ident.startswith('mcwroofs:')and ident.endswith('_top_roof')and differing=={'part'}and actual==independent_canonical:
        return'EXACT_PRIMARY_ID_AND_INDEPENDENT_PINNED_NATIVE_RIDGE_PART'
    if ident in BASE_ROOF_IDS and differing=={'shape'}and actual==independent_canonical:
        return'EXACT_PRIMARY_ID_FACING_HALF_AND_INDEPENDENT_PINNED_NATIVE_BASE_ROOF_SHAPE'
    return None


def native_base_shape(mask,q):
    """Original interop recipe for pinned BaseRoof.getStairsShape.

    Unlike vanilla stairs, canTakeShape compares a side neighbor with
    the front/back roof, not the centre state. All classes here are
    positively identified BlockInit BaseRoof suppliers, not ID guesses.
    """
    value=mask[q];props=properties(value);face=props['facing'];half=props['half']
    order=('north','east','south','west');idx=order.index(face)
    def opposite(d):return order[(order.index(d)+2)%4]
    def neighbor(d):
        dx,dz=VEC[d];return mask.get((q[0]+dx,q[1],q[2]+dz),AIR)
    def base(v):
        ident=key(v)
        if ident in BASE_ROOF_IDS:return True
        if ident.startswith('mcwroofs:')and ident.endswith('_roof')and not ident.endswith(('_lower_roof','_attic_roof','_steep_roof'))and set(properties(v))>={'facing','half','shape'}:
            raise UserError('Unqualified Macaw base-roof class in the actual corner neighborhood: '+ident)
        return False
    def allowed(d,other):
        side=neighbor(d)
        return not(base(side)and properties(side).get('facing')==properties(other).get('facing')and properties(side).get('half')==properties(other).get('half'))
    front=neighbor(face)
    if base(front)and properties(front).get('half')==half:
        other=properties(front)['facing']
        if order.index(other)%2!=idx%2 and allowed(opposite(other),front):
            return'outer_left'if other==order[(idx-1)%4]else'outer_right'
    back=neighbor(opposite(face))
    if base(back)and properties(back).get('half')==half:
        other=properties(back)['facing']
        if order.index(other)%2!=idx%2 and allowed(other,back):
            return'inner_left'if other==order[(idx-1)%4]else'inner_right'
    return'straight'


def canonical_base_roofs(registry,mask,targets):
    edits={}
    for q in targets:
        value=mask[q]
        if key(value)not in BASE_ROOF_IDS:continue
        props=properties(value);props['shape']=native_base_shape(mask,q)
        new=state(registry,key(value),**props)
        if new!=value:edits[q]=new
    mask.update(edits)
    return edits


def palette_recipe(registry,field,house):
    """One muted material per actual main/cross roof plane, never stripes."""
    counts=Counter(roof_axis(v)for v in field.values()if key(v).startswith('mcwroofs:')and not key(v).endswith('_top_roof'))
    dominant='ew'if counts['ew']>=counts['ns']else'ns'
    primary='spruce'if house['id'].endswith(('/ferryman','/weaver'))else'dark_oak'
    secondary='dark_oak'if primary=='spruce'else'spruce'
    tops={q for q,v in field.items()if key(v).startswith('mcwroofs:')and key(v).endswith('_top_roof')}
    roof_z={q[2]for q,v in field.items()if key(v).startswith('mcwroofs:')}
    half_hip=house['id'].endswith(('/baker','/soup-kitchen'))
    result={};roles={}
    for q,value in field.items():
        ident=key(value);target=ident;reason=None
        if ident.startswith('mcwroofs:'):
            suffix=next((s for s in('_top_roof','_lower_roof','_roof')if ident.endswith(s)),None)
            if suffix:
                axis=roof_axis(value)
                if suffix=='_top_roof':
                    x,y,z=q;ew=any((x+d,y,z)in tops for d in(-1,1));ns=any((x,y,z+d)in tops for d in(-1,1))
                    axis='ns'if ew and not ns else'ew'if ns and not ew else dominant
                if half_hip and q[2]in(min(roof_z),max(roof_z)):axis='ns'if dominant=='ew'else'ew'
                target='mcwroofs:'+(primary if axis==dominant else secondary)+suffix
                reason='actual main/cross roof-plane family; no periodic material courses'
        elif ident.startswith('mythrais:roof_')and ident.endswith('bright_copper'):
            target=ident.removesuffix('bright_copper')+'moss_slate';reason='quiet original native roof profile, same state schema'
        elif ident=='minecraft:oxidized_cut_copper_stairs':
            target='minecraft:'+('spruce'if house['id'].endswith('/smith')else'dark_oak')+'_stairs';reason='remove original periodic copper roof stripe, retaining the actual stair geometry'
        elif ident=='minecraft:waxed_cut_copper_slab'and q[1]>=house['floor_y']+8:
            target='minecraft:stone_brick_slab';reason='quiet shaped crest coping instead of the original periodic bright-copper course'
        elif ident in OPAQUE_MAP and q[1]>house['floor_y']:
            target=OPAQUE_MAP[ident];reason='muted opaque plaster without touching furniture or native backing shape'
        if target!=ident:
            result[q]=state(registry,target,**properties(value));roles[q]=reason
    return result,roles,{'primary_roof_family':primary,'cross_roof_family':secondary,'dominant_slope_axis':dominant,'plane_counts':dict(counts)}


def house_fields(home):
    expected,prior,tags,before_tags,owners,houses,refs=load_batches(home)
    houses=[h for h in houses if h['batch'].startswith('west')or h['batch']=='western-ten']
    if len(houses)!=15:raise UserError('Exactly the rejected15 western source houses required')
    result={h['id']:{}for h in houses};main={h['id']:set(map(tuple,h['main_footprint']))for h in houses}
    for q,value in expected.items():
        candidates=[]
        for h in houses:
            if h['batch']not in owners[q]or q[1]<h['floor_y']:continue
            distance=min(max(abs(q[0]-x),abs(q[2]-z))for x,z in main[h['id']])
            if distance<=1:candidates.append((distance,h['id']))
        if not candidates:continue
        candidates.sort()
        if len(candidates)>1 and candidates[0][0]==candidates[1][0]:continue
        result[candidates[0][1]][q]=value
    return houses,result,refs


def audit_palette(home):
    home=fill.private_home(home);reader_budget();registry=read_json(home/'dashboard/settlement/registry.json')
    houses,fields,refs=house_fields(home);rows=[]
    for house in houses:
        field=fields[house['id']];edits,roles,recipe=palette_recipe(registry,field,house)
        p=SimpleNamespace(registry=registry,blocks={**field,**edits});canonical_joins(p)
        try:material=require_material_rule(p.blocks,'COMPLETE rejected West15 '+house['id']);error=None
        except (UserError,ValueError)as exc:material=None;error=str(exc)
        rows.append({'id':house['id'],'authored_cells':len(field),'palette_changes':len(edits),'material_error':error,'recipe':recipe})
    return rows


VEC={'north':(0,-1),'east':(1,0),'south':(0,1),'west':(-1,0)}


def candidate_features(field,house):
    """Describe two real high window/gable layers; source coordinates only."""
    main=set(map(tuple,house['main_footprint']));floor=house['floor_y'];candidates=[]
    windows=[]
    for q,value in field.items():
        if not key(value).startswith('mcwwindows:'):continue
        x,y,z=q
        for face,(dx,dz)in VEC.items():
            if(x+dx,z+dz)not in main and(x,z)in main:
                # An actual header above all contiguous native window cells.
                header=y+1
                while key(field.get((x,header,z),AIR)).startswith('mcwwindows:'):header+=1
                windows.append((-(y-floor),x,header,z,face,y))
    seen=set()
    for _,x,header,z,face,bottom in sorted(windows):
        marker=x,header,z,face
        if marker in seen:continue
        seen.add(marker);dx,dz=VEC[face];tx,tz=(1,0)if dz else(0,1)
        # Project the actual header with rooted carved knees, a small light
        # and a continuous timber head. Nothing is cleared inside the room.
        cells={};backs=[]
        for side in(-1,1):
            a=(x+side*tx,header,z+side*tz);q=(a[0]+dx,header,a[2]+dz)
            cells[q]=('mythrais:curved_corbel_dark_oak',{'facing':face,'shape':0});backs.append((q,a))
        for side in(-1,0,1):
            q=x+dx+side*tx,header+1,z+dz+side*tz
            cells[q]=('dawnoftimebuilder:charred_spruce_beam'if tx else'dawnoftimebuilder:dark_oak_beam',
                      {'axis_x':bool(tx),'axis_y':False,'axis_z':bool(tz),'bottom':True,'waterlogged':False})
        lamp=x+dx,header,z+dz;cells[lamp]=('mcwlights:tavern_wall_lantern',{'facing':face});backs.append((lamp,(x,header,z)))
        candidates.append({'kind':'projected real casement head, carved knees and small warm light','cells':cells,'backs':backs,'face':face})
        if bottom>=floor+5:
            ledge={};ledge_backs=[]
            for side in(0,1):
                q=x+dx+side*tx,bottom-1,z+dz+side*tz
                ledge[q]=('minecraft:dark_oak_planks',{});ledge_backs.append((q,(x+side*tx,bottom-1,z+side*tz)))
                ledge[q[0],q[1]+1,q[2]]=(POTS[0 if side==0 else 4],{})
            candidates.append({'kind':'actual supported upper window ledge with two contained flowers/ferns','cells':ledge,'backs':ledge_backs,'face':face})
    # A real projecting gable truss adds silhouette depth even where the old
    # fancy window hood is already fully occupied and cannot be replaced.
    roofs=[q[1]for q,v in field.items()if key(v).startswith(('mcwroofs:','mythrais:roof_'))or key(v)=='minecraft:oxidized_cut_copper_stairs']
    base_y=min(roofs)if roofs else floor+6
    for (x,y,z),value in sorted(field.items(),key=lambda r:(-r[0][1],r[0][0],r[0][2])):
        if not base_y+1<=y<=floor+14 or key(value)not in FULL_BACKING:continue
        for face,(dx,dz)in VEC.items():
            if(x,z)not in main or(x+dx,z+dz)in main:continue
            tx,tz=(1,0)if dz else(0,1);cells={};backs=[]
            for side in(-1,0,1):
                q=x+dx+side*tx,y,z+dz+side*tz
                cells[q]=('dawnoftimebuilder:charred_spruce_beam'if tx else'dawnoftimebuilder:dark_oak_beam',
                          {'axis_x':bool(tx),'axis_y':False,'axis_z':bool(tz),'bottom':True,'waterlogged':False})
            for side in(-1,1):
                q=x+dx+side*tx,y-1,z+dz+side*tz
                cells[q]=('mythrais:curved_corbel_dark_oak',{'facing':face,'shape':0})
                backs.append((q,(x+side*tx,y-1,z+side*tz)))
            candidates.append({'kind':'projecting supported gable truss and carved high knees','cells':cells,'backs':backs,'face':face})
        if len(candidates)>50:break
    return candidates


def carved_gable(registry,original,house,current,blocked,before,delta):
    """Real half-block recess/cornice geometry within a known old gable.

    This does not intrude into a tight new alley. Exact original non-BE
    opaque gable blocks above the furnished ceiling are shaped; no floor,
    furniture, stored item or current unproved state is substituted.
    """
    floor=house['floor_y'];main=set(map(tuple,house['main_footprint']))
    roofs=[q[1]for q,v in original.items()if key(v).startswith(('mcwroofs:','mythrais:roof_'))or key(v)=='minecraft:oxidized_cut_copper_stairs']
    low=min(roofs)if roofs else floor+6;candidates=[]
    for q,value in original.items():
        x,y,z=q
        minimum=low if house['id'].endswith(('/baker','/soup-kitchen'))else low+1
        if not minimum<=y<=floor+14 or key(value)not in FULL_BACKING or q in blocked or current(q)!=value:continue
        faces=[face for face,(dx,dz)in VEC.items()if(x,z)in main and(x+dx,z+dz)not in main]
        if not faces:continue
        face=sorted(faces,key=lambda f:(f not in('north','south'),f))[0]
        neighbors=[current((x+dx,y+dy,z+dz))for dx,dy,dz in((1,0,0),(-1,0,0),(0,0,1),(0,0,-1),(0,1,0),(0,-1,0))]
        if any(key(v).endswith('_stairs')and properties(v).get('half')=='top'for v in neighbors):continue
        # A partial cornice must not change support for a pot, sign,
        # hanging object, other fragile model or current inventory.
        if any(v!=AIR and key(v)not in FULL_BACKING and not key(v).startswith(('mcwroofs:','mythrais:roof_'))and not key(v).endswith(('_stairs','_slab'))for v in neighbors):continue
        candidates.append((-y,x,z,q,face))
    chosen=[];edits={}
    wood='dark_oak'if house['id'].endswith('/smith')else'spruce'
    for _,x,z,q,face in sorted(candidates):
        if any(sum(abs(q[i]-r[i])for i in range(3))<3 for r in chosen):continue
        value=state(registry,'minecraft:'+wood+'_stairs',facing=face,half='top',shape='straight',waterlogged=False)
        trial={**before,**delta,**edits,q:value}
        try:require_material_rule(trial,'complete '+house['id']+' with actually recessed high gable')
        except ValueError:continue
        edits[q]=value;chosen.append(q)
        if len(chosen)==4:break
    return edits,{'kind':'carved half-depth high-gable or hipped cornice recesses below the retained roof','cells':len(edits),'positions':[list(q)for q in chosen],
       'no_old_BE_furnished_storey_floor_furniture_or_room_body_touched':True}if edits else None


def raised_hip_ridge(registry,original,house,current,blocked,before,delta):
    """A short structural timber crest broadens an existing hipped ridge."""
    if not house['id'].endswith(('/baker','/soup-kitchen')):return{},None
    tops=[q for q,v in original.items()if key(v).startswith('mcwroofs:')and key(v).endswith('_top_roof')and q not in blocked and current(q)==v]
    if not tops:return{},None
    peak=max(q[1]for q in tops);row=sorted(q for q in tops if q[1]==peak)
    chosen=row[max(0,len(row)//2-1):len(row)//2+1]
    if len(chosen)!=2 or sum(abs(chosen[0][i]-chosen[1][i])for i in range(3))!=1:return{},None
    axis='x'if chosen[0][0]!=chosen[1][0]else'z'
    edits={q:state(registry,'minecraft:stripped_dark_oak_log',axis=axis)for q in chosen}
    try:require_material_rule({**before,**delta,**edits},'complete '+house['id']+' with structural raised hip-ridge timber')
    except ValueError:return{},None
    return edits,{'kind':'short broad structural timber crest on the existing hipped roof; actual cube/crest geometry changes','cells':2,'positions':[list(q)for q in chosen],
                  'no_old_BE_furnished_storey_floor_furniture_or_room_body_touched':True}


def correction_map(group,delta):
    cells={tuple(q)for r in group for q in r['main_footprint']};touched={(x,z)for x,y,z in delta}
    x0=min(x for x,z in cells)-3;x1=max(x for x,z in cells)+3;z0=min(z for x,z in cells)-3;z1=max(z for x,z in cells)+3
    scale=min(8,1200/max(1,x1-x0+1));width=max(620,int((x1-x0+1)*scale)+40);height=int((z1-z0+1)*scale)+125
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',f'<rect width="{width}" height="{height}" fill="#171e20"/>',
      '<text x="16" y="25" fill="#eee3c6" font-family="sans-serif" font-size="17">Retained-stock Tortuga shell correction — PLANNING ONLY</text>',
      '<text x="16" y="46" fill="#d0c8b8" font-family="sans-serif" font-size="12">North up · existing main footprints retained · not a native screenshot or artist acceptance</text>']
    for x,z in sorted(cells):parts.append(f'<rect x="{20+(x-x0)*scale:g}" y="{65+(z-z0)*scale:g}" width="{scale:g}" height="{scale:g}" fill="#67513d"/>')
    for x,z in sorted(touched):parts.append(f'<rect x="{20+(x-x0)*scale:g}" y="{65+(z-z0)*scale:g}" width="{scale:g}" height="{scale:g}" fill="#a79266" fill-opacity=".85"/>')
    for r in group:
        points=list(map(tuple,r['main_footprint']));x=sum(p[0]for p in points)/len(points);z=sum(p[1]for p in points)/len(points)
        parts.append(f'<text x="{20+(x-x0)*scale:g}" y="{65+(z-z0)*scale:g}" fill="white" font-family="sans-serif" font-size="10" text-anchor="middle">{html.escape(r["name"])}</text>')
    parts.append(f'<text x="16" y="{height-18}" fill="#d0c8b8" font-family="sans-serif" font-size="12">Gold: roof/plaster/depth targets. No inventory relocation; native before/after maps and actual views remain required.</text></svg>')
    return''.join(parts).encode()


def prepare(home,checkpoint_id,checkpoint_sha):
    reserve=guard(8*MIB,96*MIB);budgets=[reader_budget()]
    home=fill.private_home(home);receipt=fill.stopped(home,checkpoint_id,checkpoint_sha)
    roof_jar=Path('D:/A World for Two/caches/mods/mcw-roofs-2.3.2-mc1.21.1neoforge.jar')
    with roof_jar.open('rb')as stream:roof_sha=hashlib.file_digest(stream,'sha512').hexdigest()
    if roof_sha!=PINNED_ROOF_SHA512:raise UserError('The exact bytecode-inspected native Macaw roof artifact changed')
    registry=read_json(home/'dashboard/settlement/registry.json');houses,fields,source_refs=house_fields(home)
    keep,_,heritage,_,_,other_refs=fill.retained_context(home,registry)
    prior,prior_refs,_=previous.construction_targets(home,previous.coast.FIVE+spit.QUEUED+FUTURE)
    future=set(prior)
    owned={q:v for field in fields.values()for q,v in field.items()}
    non_owned_keep=set(keep)-set(owned)
    all_main={h['id']:set(map(tuple,h['main_footprint']))for h in houses}
    out=home/'staging'/('west15-shells-'+str(time.time_ns()));out.mkdir()
    terrain=None;began=time.monotonic();actual={};bes={};records=[];all_deltas={};after_by_house={};before_by_house={};new_feature_cells=set()
    try:
        terrain=NorthTerrain(home,receipt,registry)
        def current(q):
            if q not in actual:
                value=terrain.state(*q)
                if value is None:raise UserError('Every roof, projection and stock context must be saved FULL')
                actual[q]=value
            return actual[q]
        for i,q in enumerate(sorted(owned,key=lambda q:(q[0]//16,q[2]//16,q[1],q[0],q[2]))):
            current(q)
            if i%512==0:budgets.append(reader_budget())
            if time.monotonic()-began>120:raise UserError('Finite120s current shell reader expired')
        # Resolve only independently derived native ridge parts and BaseRoof
        # corners from primary identity/facing/half plus actual neighbors.
        # Different IDs/primary properties never become owned this way.
        for(x,y,z),value in owned.items():
            if key(value)in BASE_ROOF_IDS or key(value).startswith('mcwroofs:')and key(value).endswith('_top_roof'):
                for dx,dz in((1,0),(-1,0),(0,1),(0,-1)):current((x+dx,y,z+dz))
        canonical_original=SimpleNamespace(registry=registry,blocks={**actual,**owned})
        canonical_joins(canonical_original)
        canonical_base_roofs(registry,canonical_original.blocks,owned)
        ridge_primary_intact=set()
        for(x,y,z),value in owned.items():
            if key(value)in BASE_ROOF_IDS or key(value).startswith('mcwroofs:')and key(value).endswith('_top_roof'):
                neighbors=[(x+dx,y,z+dz)for dx,dz in((1,0),(-1,0),(0,1),(0,-1))]
                def primary(v):return key(v),{k:p for k,p in properties(v).items()if k not in('part','shape')}
                if all(q not in owned or primary(current(q))==primary(owned[q])for q in neighbors):ridge_primary_intact.add((x,y,z))
        for cx,cz in list(terrain.statuses):
            document=decoded_chunk(terrain.snapshot.regions[cx//32,cz//32],cx,cz)
            for be in document.get('block_entities',[]):
                q=int(be['x']),int(be['y']),int(be['z'])
                if q in owned or any((q[0],q[2])in all_main[h['id']]and h['floor_y']<=q[1]<=h['floor_y']+18 for h in houses):
                    bes[q]=be;current(q)
        protected=set(bes)|{(x,y-1,z)for x,y,z in bes}
        for house in houses:
            budgets.append(reader_budget())
            if time.monotonic()-began>180:raise UserError('Finite180s shell/feature/typed-custody bound exceeded')
            ident=house['id'];original=fields[ident];before={q:current(q)for q in original}
            for q in bes:
                if(q[0],q[2])in all_main[ident]:before[q]=current(q)
            proposed,roles,recipe=palette_recipe(registry,original,house);delta={};skips=[];features=[];surface_origins=Counter()
            for q,value in proposed.items():
                if q in protected or q in future or(q[0],q[2])in heritage:
                    skips.append({'position':list(q),'reason':'retained BE/support, accepted heritage or current/future construction'});continue
                origin=owned_surface_origin(original[q],current(q),canonical_original.blocks.get(q)if q in ridge_primary_intact else None)
                if origin is None:
                    skips.append({'position':list(q),'reason':'current state differs; native/human origin remains unproved and is retained'});continue
                delta[q]=value;surface_origins[origin]+=1
            be_neighbors={tuple(q[i]+d[i]for i in range(3))for q in bes for d in((0,0,0),(1,0,0),(-1,0,0),(0,0,1),(0,0,-1),(0,1,0),(0,-1,0))}
            carving_blocked=protected|future|be_neighbors|{q for q in original if(q[0],q[2])in heritage}
            carvings,carving=carved_gable(registry,original,house,current,carving_blocked,before,delta)
            if carving is None:carvings,carving=raised_hip_ridge(registry,original,house,current,carving_blocked,before,delta)
            if carving:delta.update(carvings);features.append(carving)
            others=set().union(*(v for k,v in all_main.items()if k!=ident))
            def permitted(q):
                return(q not in owned or q in original)and q not in protected|future|non_owned_keep and(q[0],q[2])not in heritage|others and q[1]>=house['floor_y']+3 and current(q)==AIR and q not in terrain.entities
            # At most two different genuinely dimensional fittings per house.
            # A failed fitting is omitted with a reason, never cleared/retried
            # into the existing furniture, window model or unknown progress.
            for feature in candidate_features(original,house):
                if len(features)>=3:break
                qs=feature['cells']
                if set(qs)&(set(all_deltas)|new_feature_cells|set(delta)):continue
                if not all(permitted(q)for q in qs):continue
                if not all(key(delta.get(back,current(back)))in FULL_BACKING and back not in bes for q,back in feature['backs']):continue
                additions={q:state(registry,name,**props)for q,(name,props)in qs.items()}
                trial={**before,**delta,**additions}
                try:require_material_rule(trial,'complete current '+ident+' with actual new exterior depth')
                except ValueError:continue
                for q in additions:before[q]=current(q)
                delta.update(additions);new_feature_cells.update(additions)
                features.append({'kind':feature['kind'],'face':feature['face'],'cells':len(additions),'positions':[list(q)for q in sorted(additions)],'actual_supports':[{'detail':list(q),'backing':list(back),'state':delta.get(back,current(back))}for q,back in feature['backs']]})
            after={**before,**delta}
            # Part derivation is from the complete physical identity mask,
            # not a copy of an observed post-placement failure.
            mask=SimpleNamespace(registry=registry,blocks={**keep,**prior,**actual,**all_deltas,**after})
            changes=canonical_joins(mask)
            base_changes=canonical_base_roofs(registry,mask.blocks,after)
            if any(q not in delta for q in base_changes):
                raise UserError('A retained non-target base roof would require a separate normally-derived shape operation')
            for q in after:after[q]=mask.blocks[q]
            for q in delta:delta[q]=after[q]
            proof=require_material_rule(after,'complete current rejected '+ident+' with muted roof planes and supported depth')
            if set(delta)&set(bes):raise UserError('No actual BE may be placed, recreated, cleared or moved')
            before_by_house[ident]=before;after_by_house[ident]=after;all_deltas.update(delta)
            records.append({'id':ident,'name':house['name'],'main_footprint':house['main_footprint'],'floor_y':house['floor_y'],
                'delta_cells':len(delta),'palette_owned_exact_changes':sum(q in proposed for q in delta),'new_3D_features':features,
                'preserved_unknown_or_unproven_state_cells':skips,'roof_recipe':recipe,'material_rule':proof,
                'positive_surface_origins':dict(surface_origins),
                'actual_BEs_retained':sum(q in bes for q in before),'stock_or_building_relocation_required_for_this_layer':False,
                'retained_furniture_and_floor_writes':0,'geometry_status':'Existing main mass retained; this is a bounded exterior/roof correction, not proof of the whole approved city rebuild'})
        sources=terrain.snapshot.sources;terrain.close();terrain=None
        raw={};bundles=[]
        for index in range(3):
            group=records[index*5:(index+1)*5];ids=[r['id']for r in group]
            before={q:v for ident in ids for q,v in before_by_house[ident].items()};after={q:v for ident in ids for q,v in after_by_house[ident].items()}
            delta={q:all_deltas[q]for q in after if q in all_deltas}
            after.update(delta)
            owned_bes={q:be for q,be in bes.items()if q in before}
            if not delta or len(delta)>12000:raise UserError('Each real correction group must be nonempty and below12K targets')
            prefix='west15-'+str(index+1)
            docs={
              prefix+'-before-VERIFY-ONLY.json':native_payload(registry,before,checkpoint_sha,'VERIFY ONLY — current shell/context and retained full typed BE custody'),
              prefix+'-PROPOSAL.json':native_payload(registry,delta,checkpoint_sha,'TORTUGA — exact owned non-BE roofs/plaster and supported new exterior depth'),
              prefix+'-full-VERIFY-ONLY.json':native_payload(registry,after,checkpoint_sha,'VERIFY ONLY — proposed shell plus unchanged actual furniture and full typed inventory context'),
              prefix+'-normal-SETTLE-ONLY.json':native_payload(registry,{q:after[q]for q in delta if key(after[q])!=AIR},checkpoint_sha,'NORMAL JOINS ONLY — no existing furniture or NBT replay'),
            }
            for name,doc in docs.items():
                if not name.endswith('-PROPOSAL.json'):
                    doc.update(construction_forbidden=True,verification_only=True)
                    if'normal'not in name:doc['block_entities']=[{'pos':list(q),'nbt':be.snbt()}for q,be in sorted(owned_bes.items())]
                raw[name]=(json.dumps(doc,separators=(',',':'))+'\n').encode()
            map_name=prefix+'-map-PLAN-ONLY.svg';raw[map_name]=correction_map(group,delta)
            if len(raw[map_name])>MIB:raise UserError('Finite1MiB shell source-map cap exceeded')
            bundles.append({'group':index+1,'houses':ids,'delta_cells':len(delta),'full_cells':len(after),'actual_BEs_retained':len(owned_bes),'files':list(docs)+[map_name]})
        typed_records=[]
        for q,be in sorted(bes.items()):
            data=typed(be);encoded=json.dumps(data,sort_keys=True,separators=(',',':')).encode()
            typed_records.append({'position':list(q),'actual_full_typed_NBT':data,'sha256':hashlib.sha256(encoded).hexdigest(),'inventory_facts':inventory_facts(be),'action':'PRESERVE IN PLACE; no tag, item, slot or owner writes'})
        raw['retained-BEs-FULL-TYPED-PRIVATE.json']=(json.dumps(typed_records,separators=(',',':'))+'\n').encode()
        manifest={'format':'awft-west15-owned-shell-correction:1','source_sha256':digest(Path(__file__)),'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,
          'houses':records,'bundles':bundles,'native_actions':0,'world_writes':0,'inventory_or_NBT_targets':0,'old_buildings_demolished':0,'main_footprints_relocated':0,
          'existing_contents_can_remain_in_place_for_this_layer':True,'complete_city_layout_or_art_acceptance':False,'current_typed_BEs':len(bes),
          'positive_original_sources':source_refs,'accepted_preservation_sources':other_refs,'later_construction_keepouts':prior_refs,'saved_sources':sources,
          'native_roof_corner_source':{'jar':'mcw-roofs-2.3.2-mc1.21.1neoforge.jar','sha512':PINNED_ROOF_SHA512,'class':'com.mcwroofs.kikoz.objects.roofs.BaseRoof',
            'methods':['getStairsShape','canTakeShape','isBaseRoof'],'six_original_and_muted_block_classes_confirmed_by':'BlockInit supplier bytecode; spruce7,dark_oak35,brown_terracotta196,red_terracotta210,bricks444,stone_bricks591',
            'rule':'front/back same-half BaseRoof perpendicular facing; side veto compares the candidate neighbor, independent of material family'},
          'reader_peak_RSS_bytes':max(b['owned_reader_rss_bytes']for b in budgets),'reserve_guard':reserve,
          'status':'SOURCE ONLY; fresh Native full before/custody, parent placement/normal-settle/full verification, maps and actual art views remain required',
          'limits':['No palette correction turns a source state delta into proven Codex ownership','Unknown/current extra items and all actual BEs remain in place','Existing main footprints are reused; this does not claim the rejected old layout accepted','No native, graphical, functional, crafting or resident acceptance from local plans'],
          'files':{n:{'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}for n,b in raw.items()}}
        raw['manifest.json']=(json.dumps(manifest,separators=(',',':'))+'\n').encode()
        if sum(map(len,raw.values()))>64*MIB:raise UserError('Finite64MiB legacy-shell output cap exceeded')
        for name,data in raw.items():(out/name).open('xb').write(data)
        return{'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'groups':bundles,'total_delta':len(all_deltas),'BEs_preserved':len(bes),'new_3D_features':sum(len(r['new_3D_features'])for r in records),'native_actions':0}
    except Exception as exc:
        (out/'refusal.json').open('x',encoding='utf-8').write(json.dumps({'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'source_sha256':digest(Path(__file__)),'reason':type(exc).__name__+': '+str(exc),'native_actions':0,'world_writes':0,'request_emitted':False})+'\n')
        raise UserError(str(exc)+'; preserved '+str(out))from exc
    finally:
        if terrain is not None:terrain.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--home',type=Path,required=True)
    parser.add_argument('--checkpoint-id');parser.add_argument('--checkpoint-sha')
    args=parser.parse_args()
    if bool(args.checkpoint_id)!=bool(args.checkpoint_sha):parser.error('Both exact checkpoint arguments required')
    print(json.dumps(prepare(args.home,args.checkpoint_id,args.checkpoint_sha)if args.checkpoint_id else audit_palette(args.home),indent=2))
