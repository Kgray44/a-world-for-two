"""Buildable crooked WEST ground and three distinct open workspaces.

Exact stopped FULL dry land first. No old house/inventory demolition, live-world
call or generic plaza grid. This producer emits private reviewable plans only.
"""
from __future__ import annotations
import argparse
from collections import Counter
import heapq
import hashlib,json,time
from pathlib import Path

from control_room.common import UserError,digest,read_json
from tools.artistic_west_r2_frontage import Frontage,rect,canonical_joins,key
from tools.artistic_salt_petal import HALL,W3,FOREST,POTS
from tools.artistic_west_r2_study import ZIP,REJECTED
from tools.artistic_north_bank_east import NorthTerrain,native_payload,GROUND,SOFT,NORTH_SOFT,AIR as VOIDS
from tools.artistic_bridge_refinement import flatten
from tools.artistic_materials import require_material_rule,require_outdoor_rule
from tools.playtest import guard
from tools.artistic_zipline_catenary import reader_budget

MIB=1024**2
BOUNDS=(978,-1310,1072,-1250)
SALT=('staging/salt-petal-florist-SOURCE-ONLY-1793173324279127400/source-only.json','c9c60ac6e4eb60605dbbfa4917b17c8cda66ff1f1a9d7ebf784403a27af305cc')
PAIR=((1013,-1294,1020,-1283),(1024,-1292,1030,-1282))
PAIR_MASK=('staging/tortuga-trade-pair-1793195118561023300/future-pair-solid-AIR-route-reservation-ONLY.json','61c72c4fd758789e63ca1ab60ece8fdbcb193468ff171d057b30023b7281061e')
PAVERS={'minecraft:andesite','minecraft:polished_andesite','minecraft:cobblestone','chipped:small_stone_bricks','minecraft:cobbled_deepslate'}
BODY_CLEAR=VOIDS|SOFT|NORTH_SOFT
WORK_NAMES=('Old Brine fish-sorting shed','Rag & Rig sail-mending lean-to','The Crooked Cask repair canopy')


def workspaces(registry):
    result=[]
    # Cropped real water-edge sorting shed; the wet-under-gravel SE corner is
    # deliberately NOT a footing. Every useful detail belongs to the fish trade.
    p=Frontage(registry,(990,63,-1274));p.owner=WORK_NAMES[0]
    main=rect(0,0,6,4)-{(6,4),(5,4),(6,3)};p.main[p.owner]=main;p.levels[p.owner]=[main]
    p.floor(main,0)
    for x,z in ((0,0),(6,0),(0,4),(4,4)):
        for y in range(1,5):p.put(x,y,z,'minecraft:stripped_dark_oak_log',axis='y')
    for x in range(1,6):
        for y in (1,2):p.put(x,y,0,'chipped:boxed_dark_oak_planks')
        p.beam(x,3,0,'x')
    p.roof((-1,-1,7,4),4,(0,1,2,3,3,3,2,1,0),family='dark_oak')
    p.counter(1,1,1,'south','andesite',role='fish sorting and wrapping counter')
    p.counter(2,1,1,'south','andesite',role='working fish counter')
    p.put(2,2,1,'farmersdelight:cutting_board',facing='south',waterlogged=False,role='real fish-preparation board')
    p.put(4,1,1,'minecraft:water_cauldron',level=3,role='actual contained rinse water')
    p.put(5,1,1,'minecraft:barrel',facing='up',open=False,role='genuinely new empty fish-goods barrel')
    p.shelf(3,2,1,'south',books=True)
    p.put(1,1,3,'handcrafted:dark_oak_bench',facing='east',shape='single',color='brown',waterlogged=False,role='waiting/basket sorting bench')
    p.put(1,2,3,'handcrafted:terracotta_bowl',facing='east',pieces=3,waterlogged=False,role='clean sorting vessels')
    p.put(0,2,2,'minecraft:dark_oak_trapdoor',facing='west',half='top',open=True,powered=False,waterlogged=False,role='fixed weathered side shutter')
    p.put(3,3,1,'minecraft:lantern',hanging=True,waterlogged=False,role='real warm fish-work light');p.put(3,4,1,'minecraft:dark_oak_planks')
    for x in range(0,7):p.beam(x,4,1,'x',role='real fish-shed task-light roof tie')
    p.put(3,4,1,'minecraft:dark_oak_planks')
    p.sign(4,3,5,'south',['Old Brine','Sort • Mend • Trade'])
    p.put(0,1,3,POTS[4],role='contained red fern on grounded side sill')
    p.reserve('Fish shed two-wide working approach',[(x,1,z)for x in (2,3)for z in (2,3,4)])
    p.features[p.owner]=['Cropped grounded floor preserves real wet-under-gravel corner','Open sorting front, worn rear shutter/boards, distinct low roof silhouette','Real work/rinse/counter/seating and warm task light, no fake stocked loot']
    canonical_joins(p);result.append(p)
    # One-way lean-to turns WEST toward the hall-side lane. It has a real loom,
    # canvas table, restrained hung sail and working green/pottery side pocket.
    p=Frontage(registry,(1063,63,-1287));p.owner=WORK_NAMES[1]
    main=rect(0,0,5,6)-{(5,0),(5,6)};p.main[p.owner]=main;p.levels[p.owner]=[main]
    p.floor(main,0)
    for x,z in ((0,0),(4,0),(0,6),(4,6)):
        for y in range(1,6 if x==0 else 4):p.put(x,y,z,'minecraft:stripped_spruce_log',axis='y')
    for z in range(1,6):
        p.put(5,1,z,'minecraft:brown_terracotta');p.beam(5,2,z,'z',wood='dark_oak')
    for x,h in ((-1,7),(0,6),(1,6),(2,5),(3,5),(4,4),(5,4),(6,4)):
        for z in range(-1,8):p.put(x,h,z,'mcwroofs:spruce_lower_roof',facing='west',half='bottom',shape='straight')
    p.put(4,1,2,'minecraft:loom',facing='west',role='real sail and pennant loom')
    p.counter(3,1,4,'north','dark_oak_planks',role='canvas cutting and rope-splicing bench')
    p.counter(4,1,4,'north','dark_oak_planks',role='canvas repair return')
    p.put(3,2,4,'farmersdelight:cutting_board',facing='north',waterlogged=False,role='real repair/cutting surface')
    p.put(3,1,1,'minecraft:crafting_table',role='real fitting and tool bench')
    p.put(4,1,5,'farmersdelight:dark_oak_cabinet',facing='west',open=False,role='new empty canvas/tool cabinet')
    p.put(4,2,5,'handcrafted:stackable_book',facing='west',books=2,seed=4,role='repair orders and rope notes')
    p.put(4,3,1,'minecraft:white_wall_banner',facing='south',role='small real hung sail/pennant on the actual rear post')
    p.put(1,5,5,'minecraft:lantern',hanging=True,waterlogged=False,role='real repair task light');p.put(1,6,5,'minecraft:dark_oak_planks')
    p.put(0,1,5,POTS[0],role='contained plumeria on grounded working edge')
    p.sign(-1,3,0,'west',['Rag & Rig','Canvas • Splices'])
    p.reserve('Rag and Rig two-wide open side',[(x,1,z)for x in (1,2)for z in range(1,7)])
    p.features[p.owner]=['Crooked open WEST work edge faces the hall lane','One-way weathered lean-to, low rear clay/cabinet wall and small hung sail','Real loom/repair surface plus purposeful storage and task light']
    canonical_joins(p);result.append(p)
    # A crooked cask court close to the hall exit, not another enclosing house.
    p=Frontage(registry,(1028,63,-1276));p.owner=WORK_NAMES[2]
    main=rect(0,0,6,4)-{(0,4)};p.main[p.owner]=main;p.levels[p.owner]=[main]
    p.floor(main,0)
    for x,z in ((0,0),(6,0),(1,4),(6,4)):
        for y in range(1,5):p.put(x,y,z,'minecraft:stripped_dark_oak_log',axis='y')
    p.roof((0,0,6,4),4,(0,1,2,3,2,1,0),family='dark_oak',hip_south=False)
    for x in range(1,6):p.beam(x,3,0,'x')
    p.put(1,1,1,'minecraft:barrel',facing='up',open=False,role='genuinely new empty cask awaiting repair')
    p.put(2,1,1,'minecraft:barrel',facing='up',open=False,role='genuinely new empty finished cask')
    p.put(4,1,1,'minecraft:grindstone',face='floor',facing='south',role='real cooper hand-tool sharpening')
    p.counter(1,1,3,'east','dark_oak_planks',role='hoop fitting and cask-glue bench')
    p.put(1,2,3,'supplementaries:jar',facing='east',light_level=0,waterlogged=False,role='small repair glue pot')
    p.put(4,1,3,'minecraft:crafting_table',role='real repair work table')
    p.put(4,2,3,'handcrafted:wood_cup',facing='east',pieces=2,waterlogged=False,role='tools/rinse vessels beside the bench')
    for z in range(0,5):p.beam(6,4,z,'z',role='supported cask-court lamp and rope-access tie')
    p.put(6,3,3,'minecraft:lantern',hanging=True,waterlogged=False,role='real warm cask-work light');p.put(6,4,3,'minecraft:dark_oak_planks')
    for y in (1,2,3):p.put(7,y,0,'chipped:roped_ladder',facing='east',waterlogged=False,role='real post-mounted rope ladder for canopy maintenance')
    p.put(5,1,3,POTS[5],role='contained fern beside the repair table')
    p.sign(7,3,4,'east',['The Crooked Cask','Repairs • Hoops'])
    p.reserve('Cask court two-wide approach',[(x,1,z)for x in (2,3)for z in (2,3,4)]+[(x,1,2)for x in (4,5,6)])
    p.features[p.owner]=['Distinct fully open cask court beside the hall approach','Shaped little roof, grounded framing, real barrel/tool/repair story','Human route stays two wide; no old stored item is moved or respawned']
    canonical_joins(p);result.append(p)
    return result


def mask_inputs(home):
    keep={};refs=[]
    for rel,sha in (HALL,W3,ZIP,PAIR_MASK):
        if digest(home/rel)!=sha:raise UserError('Frozen hall/W3/V2 mask changed')
        keep.update(flatten(read_json(home/rel)));refs.append({'relative':rel,'sha256':sha})
    if digest(home/SALT[0])!=SALT[1]:raise UserError('Keep the new original florist untouched')
    keep.update({tuple(r[:3]):r[3]for r in read_json(home/SALT[0])['blocks']});refs.append({'relative':SALT[0],'sha256':SALT[1]})
    # Existing houses are immutable here, including their original AIR. Only
    # actual outdoor nodes outside them are candidates, never demolition volume.
    for label,rel,sha in REJECTED:
        if digest(home/rel)!=sha:raise UserError('Preserve rejected house/stock custody')
        keep.update(flatten(read_json(home/rel)));refs.append({'label':label,'relative':rel,'sha256':sha})
    if digest(home/FOREST[0])!=FOREST[1]:raise UserError('Exact next28 forest reservation required')
    forest={tuple(q)for q in read_json(home/FOREST[0])['all_growth_excluded_columns_xz']}
    return keep,forest,refs


def path_to(free,start,goal):
    """Finite two-wide A* between authored goals, over actual qualified cells."""
    def fits(q):
        x,z=q;return all((x+dx,z+dz)in free for dx,dz in((0,0),(1,0),(0,1),(1,1)))
    if not fits(start)or not fits(goal):raise UserError('Authored connector endpoint lacks its full real2x2 dry body: '+str((start,goal)))
    queue=[(0,0,start)];best={start:0};parent={};visited=0
    while queue:
        _,cost,q=heapq.heappop(queue)
        if cost!=best[q]:continue
        visited+=1
        if visited>14000:raise UserError('Finite dry-lane search exceeded; no mask expansion fallback')
        if q==goal:
            result=[q]
            while q!=start:q=parent[q];result.append(q)
            return result[::-1]
        x,z=q
        for step in((-1,0),(1,0),(0,-1),(0,1)):
            r=x+step[0],z+step[1]
            if not fits(r):continue
            new=cost+10
            if new>=best.get(r,10**12):continue
            best[r]=new;parent[r]=q
            heapq.heappush(queue,(new+10*(abs(r[0]-goal[0])+abs(r[1]-goal[1])),new,r))
    raise UserError('No real two-wide dry connector; preserve refusal rather than fill water')


def prepare(home,checkpoint_id,checkpoint_sha):
    home=Path(home).resolve();reserve=guard(8*MIB,64*MIB);budgets=[reader_budget()]
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve():raise UserError('Private artistic source only')
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    if receipt.get('verified')is not True or(receipt.get('id'),receipt.get('sha256'))!=(checkpoint_id,checkpoint_sha)or'stopped'not in receipt.get('scope','').lower():raise UserError('Exact current stopped checkpoint required')
    registry=read_json(home/'dashboard/settlement/registry.json');keep,forest,refs=mask_inputs(home);spaces=workspaces(registry)
    delta={};tags={};owners={};features={};main=set();space_routes=[]
    for p in spaces:
        require_material_rule(p.blocks,'COMPLETE '+p.owner)
        ox,oy,oz=p.origin
        for q,s in p.blocks.items():
            w=tuple(q[i]+p.origin[i]for i in range(3))
            if w in keep:raise UserError('Purposeful workspace conflicts with existing/future protected town source: '+str(w))
            delta[w]=s;owners[w]=p.owner
        for q,t in p.tags.items():tags[tuple(q[i]+p.origin[i]for i in range(3))]=t
        main.update((x+ox,z+oz)for x,z in p.main[p.owner]);features[p.owner]=p.features[p.owner]
        space_routes.extend({'id':r['id'],'points':[[q[i]+p.origin[i]for i in range(3)]for q in r['positions']]}for r in p.routes)
    # Keep Grand's two upcoming frontages while still allowing their explicitly
    # shared three-wide public lane, and hold full current/future machinery.
    reserved_columns=set()
    for x0,z0,x1,z1 in PAIR:reserved_columns.update(rect(x0,z0,x1,z1))
    # Grand's exact future pair AIR in this explicitly shared corridor is
    # retained headroom. It is never a writable floor or permission to clear a
    # future solid. All other authored AIR remains protected.
    shared_pair_air={q for q,s in flatten(read_json(home/PAIR_MASK[0])).items()
                     if 1021<=q[0]<=1023 and -1294<=q[2]<=-1282 and 64<=q[1]<=66 and key(s)in VOIDS}
    # The narrow existing strip between the rejected tavern and W3 is an
    # explicitly reviewed public connection. Preserve every source AIR cell
    # unchanged and the W3 pavers; a real coral obstruction still diverts it.
    shared_w3_air={q for q,s in keep.items()if 1068<=q[0]<=1071 and -1275<=q[2]<=-1260
                   and 64<=q[1]<=66 and key(s)in VOIDS}
    shared_air=shared_pair_air|shared_w3_air
    w3_public={(x,z)for x in(1070,1071)for z in(-1262,-1261,-1260)}
    w3_roofed_corridor={(x,z)for x in range(1068,1072)for z in range(-1275,-1259)}
    terrain=NorthTerrain(home,receipt,registry);free={};before={};support={};clearance={};routes=[];started=time.monotonic()
    try:
        x0,z0,x1,z1=BOUNDS
        for cx in range(x0//16,x1//16+1):
            for cz in range(z0//16,z1//16+1):
                for x in range(max(x0,cx*16),min(x1,cx*16+15)+1):
                    for z in range(max(z0,cz*16),min(z1,cz*16+15)+1):
                        q=(x,z)
                        if q in main or q in reserved_columns or q in forest:continue
                        col=terrain.column(x,z);floor=terrain.state(x,63,z);below=terrain.state(x,62,z)
                        ordinary=col['kind']=='dry'and col['surface_y']in(62,63)
                        # A known existing overhang is not the walking floor.
                        # Only this reviewed connector may qualify beneath it,
                        # from its literal saved dry floor/support/body cells.
                        ordinary=ordinary or q in w3_roofed_corridor and floor is not None and key(floor)in GROUND|VOIDS
                        retained=key(floor)in PAVERS and(col['surface_y']==63 or q in w3_public and floor==keep.get((x,63,z)))
                        if not(ordinary or retained)or below is None or key(below)not in GROUND:continue
                        if (x,63,z)in keep and not(q in w3_public and retained and floor==keep[x,63,z]):continue
                        if any((x,y,z)in keep and(x,y,z)not in shared_air for y in(64,65,66)):continue
                        body=[terrain.state(x,y,z)for y in(64,65,66)]
                        if any(s is None or key(s)not in BODY_CLEAR or 'waterlogged=true'in s for s in body):continue
                        if any((x,y,z)in shared_air and key(s)not in VOIDS for y,s in zip((64,65,66),body)):continue
                        if any((x,y,z)in terrain.entities for y in(62,63,64,65,66)):continue
                        free[q]={'floor':floor,'below':below,'body':body,'natural_y':col['surface_y'],'retained':retained}
                budgets.append(reader_budget())
                if time.monotonic()-started>90:raise UserError('Finite West ground study90s exceeded')
        # Crooked branches are authored by destination and intermediate turn;
        # every two-wide shoulder is qualified, not a guessed centerline.
        connections=(
            ('Hall left porch to the shared northern hook',[(1037,-1276),(1036,-1273),(1022,-1273),(1021,-1283),(1021,-1292)]),
            ('Hall east flank to Salt and Petal',[(1037,-1276),(1053,-1275),(1061,-1275),(1061,-1291),(1064,-1291)]),
            ('Hall and repair court toward W3',[(1037,-1276),(1053,-1275),(1068,-1275),(1070,-1261)]),
            ('West quay to the headland hook',[(992,-1269),(988,-1275),(1007,-1276),(1010,-1280),(1021,-1283)]),
            ('Western sea-edge walking return',[(984,-1276),(987,-1278),(997,-1277),(1007,-1276)]),
        )
        used={};legs=[]
        for name,points in connections:
            anchors=[]
            for a,b in zip(points,points[1:]):
                try:leg=path_to(free,a,b)
                except UserError as exc:raise UserError('Route '+name+' '+str(a)+' -> '+str(b)+': '+str(exc))from exc
                anchors.extend(leg[:-1]);legs.append({'name':name,'from':list(a),'to':list(b),'length':len(leg)})
            anchors.append(points[-1]);cells=set()
            for x,z in anchors:cells.update((x+dx,z+dz)for dx,dz in((0,0),(1,0),(0,1),(1,1)))
            routes.append({'name':name,'width':2,'standing_positions':[[x+.5,64,z+.5]for x,z in sorted(cells)],'cells_xz':[list(q)for q in sorted(cells)]})
            for i,(x,z)in enumerate(anchors):
                prev=anchors[max(0,i-1)];after=anchors[min(len(anchors)-1,i+1)];axis='x'if abs(after[0]-prev[0])>=abs(after[1]-prev[1])else'z'
                for dx,dz in((0,0),(1,0),(0,1),(1,1)):used.setdefault((x+dx,z+dz),set()).add(axis)
        for (x,z),axes in sorted(used.items()):
            row=free[x,z]
            if not row['retained']:
                material='chipped:small_stone_bricks'if len(axes)>1 else'minecraft:andesite'if'x'in axes else'minecraft:cobblestone'
                q=x,63,z;delta[q]=material;owners[q]='Crooked Tortuga public ground'
            for y,s in zip((64,65,66),row['body']):
                q=x,y,z;clearance[q]='minecraft:air'
                if key(s)not in VOIDS:delta[q]='minecraft:air';owners[q]='Crooked Tortuga public ground'
            support[x,62,z]=row['below']
            if row['retained']:support[x,63,z]=row['floor']
        # Exact complete main supports and every proposed shape are authenticated
        # against current saved data. No actual current BE is ever writable.
        for x,z in sorted(main):
            col=terrain.column(x,z);low=terrain.state(x,62,z)
            if col['kind']!='dry'or col['surface_y']not in(62,63)or low is None or key(low)not in GROUND:raise UserError('Workspace main footing is not real supported dry FULL land: '+str((x,z,col)))
            support[x,62,z]=low
        for n,(q,after)in enumerate(sorted(delta.items(),key=lambda r:(r[0][0]//16,r[0][2]//16,r[0][1],r[0][0],r[0][2]))):
            actual=terrain.state(*q)
            if actual is None or q in terrain.entities:raise UserError('Never replace any current BE or unknown chunk')
            if key(actual)not in VOIDS|SOFT|GROUND|NORTH_SOFT or 'waterlogged=true'in actual:raise UserError('Preserve actual object/water/old stock: '+str((q,actual)))
            if q in keep:raise UserError('No current/future protected target may be written')
            before[q]=actual
            if n%512==0:budgets.append(reader_budget())
        sources=terrain.snapshot.sources
    except UserError as exc:
        out=home/'staging'/('tortuga-west-ground-REFUSED-'+str(time.time_ns()));out.mkdir()
        data={'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'source_sha256':digest(Path(__file__)),'refusal':str(exc),
              'qualified_columns_READONLY':[[*q,v['floor'],v['below'],v['natural_y']]for q,v in sorted(free.items())],
              'workspace_main_columns':[[*q]for q in sorted(main)],'native_actions':0,'world_writes':0,'not_a_native_plan':True}
        raw=(json.dumps(data,separators=(',',':'))+'\n').encode()
        if len(raw)<=8*MIB:(out/'refusal-and-readonly-ground.json').open('xb').write(raw)
        raise UserError(str(exc)+'; preserved '+str(out))from exc
    finally:terrain.close()
    for p in spaces:
        for r in p.routes:
            for x,y,z in r['positions']:
                for h in(0,1):
                    s=p.blocks.get((x,y+h,z),'minecraft:air')
                    if s!='minecraft:air':raise UserError('Workspace working route is obstructed: '+str((p.owner,x,y+h,z,s)))
    outdoor={q:s for q,s in delta.items()if owners[q]=='Crooked Tortuga public ground'}
    outdoor_rule=require_outdoor_rule(outdoor,'Complete crooked Tortuga WEST paths')
    all_after={**delta,**clearance,**support}
    docs={'west-ground-workspaces-PROPOSAL.json':native_payload(registry,delta,checkpoint_sha,'TORTUGA WEST — actual crooked2wide lanes and3distinct useful open workspaces',tags=tags),
          'complete-before-VERIFY-ONLY.json':native_payload(registry,before,checkpoint_sha,'VERIFY ONLY — exact current ground/cover/AIR before West infill'),
          'retained-supports-VERIFY-ONLY.json':native_payload(registry,support,checkpoint_sha,'VERIFY ONLY — real dry structural/path support; no world fill'),
          'full-after-and-walkclearance-VERIFY-ONLY.json':native_payload(registry,all_after,checkpoint_sha,'VERIFY ONLY — full new West workspaces/paths and complete3high human clearance',tags=tags),
          'normal-joins-SETTLE-ONLY.json':native_payload(registry,{q:s for q,s in delta.items()if key(s)not in VOIDS},checkpoint_sha,'NORMAL JOIN ONLY — new West infill, no old inventory or state replay')}
    for name,doc in docs.items():
        if name!='west-ground-workspaces-PROPOSAL.json':doc.update(construction_forbidden=True,verification_only=True)
    raw={n:(json.dumps(d,separators=(',',':'))+'\n').encode()for n,d in docs.items()}
    manifest={'format':'awft-buildable-tortuga-west-ground:1','checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'source_sha256':digest(Path(__file__)),
      'qualified_dry_route_columns':len(free),'new_path_columns':len(used),'new_targets':len(delta),'retained_mounts':len(support),'routes':routes,'route_legs':legs,
      'purposeful_workspaces':features,'actual_main_footing_columns':[list(q)for q in sorted(main)],'retained_hall_exit':[1037,64,-1276],
      'salt_south_approach':[1064,64,-1291],'W3_existing_two_wide_ground_approach':[1070,64,-1261],
      'preserved_current_future_custody':refs,'preserved_Grand_pair_bounds':PAIR,'retained_shared_pair_AIR_cells':[list(q)for q in sorted(shared_pair_air)if q in clearance],
      'retained_W3_connector_AIR_cells':[list(q)for q in sorted(shared_w3_air)if q in clearance],'retained_W3_public_floor_columns':[list(q)for q in sorted(w3_public)if q in used],'preserved_south_forest_mask':FOREST,
      'superseded_unmodeled_concepts_only':['Master Rigging House space becomes an original open sail workshop','Part of unmodeled Cliff Gull future mass becomes a real fish quay work space'],
      'outdoor_material_rule':outdoor_rule,'raw_saved_sources':sources,'reserve_guard':reserve,'reader_peak_observed_RSS_bytes':max(b['owned_reader_rss_bytes']for b in budgets),
      'files':{n:{'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}for n,b in raw.items()},
      'native_actions':0,'world_writes':0,'old_house_or_inventory_demolition':0,'living_entity_LIFE_seeded':0,
      'status':'SOURCE/SAVED-PREIMAGE ONLY; parent current native before+support verification, one placement, ordinary joins/fullverify then actual walk/shore/workspace images required',
      'limitations':['No world-wide or full-bank density/visual acceptance from these paths','No source match authorizes removing any of the727 existing BEs','Live collision/model-overhang walking remains a native gate','All new stock models start native default/empty; no current Items are copied or forged']}
    raw['manifest.json']=(json.dumps(manifest,separators=(',',':'))+'\n').encode()
    if sum(map(len,raw.values()))>64*MIB:raise UserError('Finite West source output allocation exceeded')
    out=home/'staging'/('tortuga-west-ground-'+str(time.time_ns()));out.mkdir()
    for n,b in raw.items():(out/n).open('xb').write(b)
    return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'targets':len(delta),'path_columns':len(used),'workspaces':3,'files':manifest['files'],'native_actions':0}


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--home',type=Path,required=True);a.add_argument('--checkpoint-id',required=True);a.add_argument('--checkpoint-sha',required=True);args=a.parse_args();print(json.dumps(prepare(args.home,args.checkpoint_id,args.checkpoint_sha),indent=2))
