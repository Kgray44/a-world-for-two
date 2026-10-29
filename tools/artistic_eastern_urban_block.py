"""The Keel & Cask: one fully authored three-mass eastern urban compound.

This is post-move architectural source, not a directly executable native plan.
Existing room contents must arrive through the reviewed vanilla native mover;
no saved inventory is replayed and no current source data is assumed empty.
"""
from __future__ import annotations
import argparse
from collections import Counter,deque
import hashlib,json,time
from pathlib import Path

from control_room.common import UserError,digest,read_json
from tools.artistic_captains_hall import boundary,rectangle
from tools.artistic_east_tortuga_retrofit import checked
from tools.artistic_eastern_urban_custody import canonical
from tools.artistic_eastern_urban_layout import FINE
from tools.artistic_fisherman_interior import snbt
from tools.artistic_maritime_depth import key
from tools.artistic_materials import require_material_rule
from tools.artistic_spawn_plaza import state
from tools.artistic_tortuga_pair import TradeHouse,hip
from tools.playtest import guard
from tools.settlement_attractions import properties

MIB=1024**2
MAX_OUTPUT=8*MIB
ID='bridge-cooper'
ORIGIN=(1217,64,-1213)
CORRECTED_CUSTODY=('staging/eastern-urban-current-custody-1793210273627204600/manifest.json',
    'ebed9164e2ee363c706c6b84a7af437e65f902bd67dab3f0d9ea7e8039de3f02')
ARCH={'minecraft:spruce_planks','minecraft:dark_oak_planks','minecraft:oak_wood','minecraft:dark_oak_wood',
      'minecraft:stripped_oak_wood','minecraft:stripped_spruce_log','minecraft:stripped_dark_oak_log',
      'minecraft:stone_bricks','minecraft:polished_andesite','minecraft:bricks',
      'dawnoftimebuilder:blue_plastered_stone','dawnoftimebuilder:yellow_plastered_stone',
      'dawnoftimebuilder:red_plastered_stone','dawnoftimebuilder:plastered_stone',
      'minecraft:white_terracotta','minecraft:green_terracotta','minecraft:light_gray_terracotta'}
ARCH.update({'minecraft:spruce_stairs','minecraft:dark_oak_slab','minecraft:stone_brick_stairs',
    'dawnoftimebuilder:chiseled_plastered_stone','dawnoftimebuilder:spruce_beam','dawnoftimebuilder:spruce_support_slab'})


class UrbanHouse(TradeHouse):
    def __init__(self,registry,copied,be_positions,unproven):
        super().__init__(registry,'The Keel & Cask',ORIGIN)
        self.blocks=dict(copied);self.copied=dict(copied);self.current_BE_points=set(be_positions);self.unproven=set(unproven)
        self.inherited_roles={q:'Native-moved retained room contents; no tag supplied' for q in copied}
        self.roles.update(self.inherited_roles);self.inherited_shell_retirement=[]

    def put(self,x,y,z,material,*,role='authored architecture',**props):
        q=x,y,z
        if not(-1<=x<=15 and -2<=y<=18 and -1<=z<=30):raise UserError('The one compound escaped its finite authored envelope')
        value=state(self.registry,material,**props)
        if q in self.current_BE_points and value!=self.blocks[q]:raise UserError('Preserve an actually moved native block entity and all contents: '+str(q))
        if q in self.unproven and value!=self.blocks[q]:raise UserError('A captured current-state difference still requires explicit origin review: '+str(q))
        if q in self.body and material not in {'minecraft:air','minecraft:cave_air','minecraft:void_air'} and not material.endswith('_door'):
            raise UserError('Do not block the actual designed compound walking body: '+str((q,material)))
        self.blocks[q]=value;self.roles[q]=role
        if q not in self.current_BE_points:self.tags.pop(q,None)
        if len(self.blocks)>16000:raise UserError('Keep the one detailed compound finite')

    def clear_owned_capture_shell(self):
        for q,old in tuple(self.copied.items()):
            if q in self.current_BE_points or q in self.unproven:continue
            name=key(old)
            if name in ARCH or name.startswith(('mcwwindows:','mcwroofs:','mythrais:roof_')):
                self.blocks[q]='minecraft:air';self.roles[q]='Retire positively owned captured NON-BE shell after native conservation only'
                self.inherited_shell_retirement.append({'local':list(q),'expected_native_moved_source':old})

    def maintain_inherited_fixture(self,q,value):
        """Restore a real moved fixture whose support was never stock fabrication."""
        if q not in self.copied or self.copied[q]!=value:raise UserError('Exact copied source fixture required')
        self.blocks[q]=value


def local(q):return tuple(q[i]-ORIGIN[i] for i in range(3))
def world(q):return tuple(q[i]+ORIGIN[i] for i in range(3))


def styled_table(p,x,y,z,face='north'):
    p.put(x,y,z,'handcrafted:dark_oak_table',color='none',waterlogged=False,shape='single',role='real small intimate dining/work table')
    p.put(x,y+1,z,'handcrafted:wood_cup',facing='south',pieces=2,waterlogged=False,role='small vessels on actual table')


def chair(p,x,y,z,face):
    p.put(x,y,z,'handcrafted:dark_oak_chair',facing=face,waterlogged=False,color='brown',role='actual usable dining/work chair; native use still untested')


def build(registry,copied,be_positions,unproven):
    p=UrbanHouse(registry,copied,be_positions,unproven);p.clear_owned_capture_shell()
    main=rectangle(3,11,14,29);warehouse=rectangle(0,0,14,10);return_bay=rectangle(0,24,2,28)
    p.footprint=main|warehouse|return_bay
    inherited_furniture={q:v for q,v in p.blocks.items() if key(v)!='minecraft:air'}
    # Three unequal interlocking masses. The broad low sail/cask warehouse
    # joins the tall narrow house; a small rear bay gives it a genuine notch.
    for cells,height,panel in ((main,8,'dawnoftimebuilder:plastered_stone'),
        (warehouse,4,'minecraft:gray_terracotta'),(return_bay,8,'minecraft:light_gray_terracotta')):
        for x,z in cells:
            for y in range(height+1):
                if (x,y,z) not in p.blocks:p.put(x,y,z,'minecraft:air',role='explicit future room envelope')
        p.floor(cells,0);p.walls(cells,1,height,panel)
        for y in range(4,height+1,4):p.ring(cells,y)
    p.floor(main|return_bay,4);p.floor(main|return_bay,8);p.floor(warehouse,4)
    # Respect every actual moved furniture instance, not just supplied tags.
    for q,value in inherited_furniture.items():
        if key(value) not in ARCH and not key(value).startswith(('mcwroofs:','mcwwindows:')):
            p.maintain_inherited_fixture(q,value)
    # The low-to-tall joint is an actual two-wide open internal arch.
    for z in (10,11):
        for x in (4,5,10,11):
            for y in (1,2,3):p.put(x,y,z,'minecraft:air',role='real warehouse-to-house timber-framed doorway')
    for x in (3,6,9,12):
        for y in (1,2,3):p.beam(x,y,11,'y',role='deep inner joint pier')
    for x in range(3,13):p.beam(x,4,11,'x',role='real open-joint bressummer')
    # Main front is east to the crooked alley, with a sheltered recessed entry.
    p.door(14,1,16,'east')
    for z in (15,16,17):
        p.put(15,0,z,'minecraft:dark_oak_stairs',facing='west',half='bottom',shape='straight',waterlogged=False,
            role='actual modest raised-floor entry steps; current/alley native proof required')
        p.beam(15,4,z,'z',role='deep porch head beneath upper jettied room')
    for z in (14,18):
        for y in range(1,5):p.beam(15,y,z,'y',role='rooted porch standard beyond recessed real entry')
        p.put(15,3,z,'mythrais:curved_corbel_dark_oak',facing='east',shape=0,role='carved porch brace')
    p.casement(14,2,21,'east',width=3,height=2)
    p.casement(3,2,15,'west',width=3,height=2)
    p.casement(14,6,23,'east',width=3,height=2)
    p.casement(3,6,19,'west',width=3,height=2)
    # The real low northern workroom has broad, differently proportioned lights.
    p.casement(3,2,0,'north',width=3,height=2)
    p.casement(10,2,0,'north',width=3,height=2)
    # A small rear oriel/reading bay is joined through the old wall, not pasted on.
    for z in range(25,28):
        for y in (1,2,3,5,6,7):
            for x in (2,3):p.put(x,y,z,'minecraft:air',role='real main-to-rear-bay opening through both joined walls')
    for z in (24,28):
        for y in range(1,9):p.beam(2,y,z,'y',role='rear-bay carved cheek')
    p.casement(0,6,25,'west',width=2,height=2)
    # Two-wide four-riser native stair, with literal intermediate headroom and
    # an actual top landing. It leaves the west ground-floor through route open.
    for n in range(4):
        for x in (10,11):
            z=12+n;y=1+n
            for yy in range(y+1,8):p.put(x,yy,z,'minecraft:air',role='actual upper stair headroom')
            for yy in range(1,y):p.put(x,yy,z,'chipped:boxed_dark_oak_planks',role='proper enclosed stair carriage')
            p.put(x,y,z,'minecraft:dark_oak_stairs',facing='south',half='bottom',shape='straight',waterlogged=False,role='genuine two-wide household stair')
            p.stairs.append((x,y,z))
    p.reserve('upper landing',[(x,5,16) for x in (10,11)])
    p.reserve('east recessed door to west lower through passage',[(x,1,16) for x in range(4,15)])
    p.reserve('west lower through passage',[(x,1,z) for x in (4,5) for z in range(11,29)])
    p.reserve('warehouse south counter circulation',[(x,1,10) for x in range(1,14)])
    p.reserve('upstairs room access',[(x,5,z) for x in (8,9) for z in range(17,29)])
    # Separate upper bedchambers, separated from a warm common-room/ledger nook.
    for x in (4,5,6,7,10,11,12,13):
        for y in (5,6,7):
            p.put(x,y,24,'minecraft:dark_oak_trapdoor',facing='north',half='bottom',open=True,powered=False,waterlogged=False,
                role='real pierced timber berth screen with clear middle passage')
    for x in (6,11):
        for y in range(5,8):p.beam(x,y,25,'y',role='deep berth-screen shoulder')
    p.bed(6,5,26,'south');p.bed(12,5,26,'south')
    p.barrel(4,5,25,'West loft sea chest',[('minecraft:bread',3),('minecraft:paper',3)])
    p.barrel(13,5,25,'East loft sea chest',[('minecraft:bread',3),('minecraft:string',3)])
    p.put(4,5,28,'handcrafted:dark_oak_side_table',facing='east',waterlogged=False,color='none',role='cozy bed-side table')
    p.put(4,6,28,'minecraft:lantern',hanging=False,waterlogged=False,role='small warm bedside lamp')
    p.put(13,5,28,'handcrafted:dark_oak_side_table',facing='west',waterlogged=False,color='none',role='separate cozy east-bed table')
    p.put(13,6,28,'handcrafted:stackable_book',facing='west',books=2,seed=7,role='mariner bedtime books')
    styled_table(p,6,5,21);chair(p,5,5,21,'east');chair(p,7,5,21,'west')
    p.put(6,6,20,'handcrafted:stackable_book',facing='south',books=2,seed=9,role='small common-room logbooks on a rooted shelf')
    p.put(6,5,20,'handcrafted:dark_oak_side_table',facing='south',color='none',waterlogged=False,role='ledger side table')
    styled_table(p,12,5,20);chair(p,11,5,20,'east');chair(p,13,5,20,'west')
    p.put(12,6,19,'handcrafted:wood_plate',facing='south',pieces=2,waterlogged=False,role='supper plates beside window')
    p.put(12,5,19,'handcrafted:dark_oak_side_table',facing='south',color='none',waterlogged=False,role='plate-bearing side table')
    p.put(1,5,26,'handcrafted:dark_oak_couch',facing='east',shape='single',color='gray',waterlogged=False,role='quiet real rear-oriel reading seat')
    p.put(1,6,25,'handcrafted:stackable_book',facing='east',books=3,seed=4,role='small rear-bay books on a real shelf')
    p.put(1,5,25,'handcrafted:dark_oak_side_table',facing='east',color='none',waterlogged=False,role='rear-oriel reading table')
    p.put(4,5,18,'minecraft:potted_fern',role='contained greenery in the lit west casement nook')
    p.put(2,5,26,'minecraft:potted_fern',role='small living plant beside the rear reading seat')
    p.put(2,5,25,'handcrafted:dark_oak_shelf',facing='north',shape='single',type=3,role='carved alcove display shelf')
    p.put(2,6,25,'handcrafted:wood_cup',facing='north',pieces=1,waterlogged=False,role='quiet alcove tankard')
    p.reserve('connected upper rear-oriel approach',[(x,5,28) for x in (8,7,6,5)]+[(5,5,27),(4,5,27),(3,5,27),(2,5,27),(1,5,27)])
    # Ground-floor fore room is a real cooper's workshop, before the conserved
    # merchant-stock backroom. No old moved container is resupplied or renamed.
    p.put(7,1,13,'minecraft:crafting_table',role='native cooper crafting station')
    p.put(7,1,14,'minecraft:anvil',facing='north',role='real iron-hoop repair anvil')
    p.put(8,1,13,'handcrafted:dark_oak_counter',facing='west',counter='dark_oak_planks',type=1,role='deep actual cooper counter')
    p.put(8,2,13,'handcrafted:wood_cup',facing='west',pieces=3,waterlogged=False,role='small test tankards')
    p.put(8,1,14,'handcrafted:dark_oak_side_table',facing='west',color='none',waterlogged=False,role='actual hand-tool table')
    p.put(8,2,14,'handcrafted:stackable_book',facing='west',books=1,seed=3,role='cooper measurement ledger')
    p.put(6,1,13,'handcrafted:dark_oak_chair',facing='east',color='brown',waterlogged=False,role='real work stool/chair')
    # Lived-in ceiling relief: real shallow tie/joist bays, without a giant lamp.
    for z in (18,23,28):
        for x in range(4,14):p.beam(x,8,z,'x',role='expressed common-room ceiling tie')
        for x in range(5,13):p.slab(x,7,z,'spruce',role='actual shallow dropped ceiling rib beneath the coffer plane')
        for x in (4,13):p.put(x,7,z,'mythrais:curved_corbel_dark_oak',facing='east' if x==4 else 'west',shape=0,role='carved actual coffer/tie knee')
    for x,z in ((6,18),(12,23),(8,28),(1,26)):
        p.put(x,7,z,'minecraft:lantern',hanging=True,waterlogged=False,role='low warm real-emission upper-room lamp')
        if key(p.blocks.get((x,8,z),'minecraft:air'))=='minecraft:air':p.beam(x,8,z,'x',role='real lamp support')
        p.supports.append(((x,7,z),(x,8,z)))
    for x,z,face in ((13,14,'west'),(6,13,'south'),(7,17,'north'),(5,19,'west')):
        # A short dark wall pad makes every low fitting physically supported.
        dx,dz={'west':(-1,0),'east':(1,0),'north':(0,-1),'south':(0,1)}[face]
        pad=x-dx,3,z-dz
        if pad not in p.current_BE_points and pad not in p.body:
            p.beam(*pad,'y',role='small supported warm wall-lamp pad');p.lamp(x,3,z,face)
    # Broad low shingle hip and a higher, narrow weathered clay house. Real
    # four-sided facets meet the taller wall; no repeated flat roof bands.
    hip(p,(2,10,15,30),8,'brown_terracotta')
    hip(p,(-1,-1,15,11),4,'spruce','minecraft:spruce_stairs')
    # Rear bay has a lower separate short hip, deliberately different skyline.
    hip(p,(-1,23,2,29),8,'dark_oak','minecraft:dark_oak_stairs')
    p.sign(15,3,19,'east',['THE KEEL & CASK','Cooper / Canvas','Rooms above','Harbor Fold'])
    # The moved sign/shelf instances retain their exact original positions and
    # facings. Deep display piers replace retired old-shell backings, rather
    # than leaving real stocked fixtures floating in the larger rooms.
    for q in sorted(p.current_BE_points):
        value=p.blocks[q]
        if key(value).endswith('_wall_sign') or key(value)=='supplementaries:item_shelf':
            face=properties(value)['facing'];dx,dz={'east':(1,0),'west':(-1,0),'north':(0,-1),'south':(0,1)}[face]
            for y in range(1,q[1]+1):
                p.beam(q[0]-dx,y,q[2]-dz,'y',role='real rooted backing pier for an unchanged native-moved stocked shelf or sign')
            p.supports.append((q,(q[0]-dx,q[1],q[2]-dz)))
    p.rooms=[
        {'name':'Low warehouse with real relocated canvas/tea stock rooms','local_floor_y':0,'program':'Conserved Bent Needle/tea fixtures; wide joined southern work aisle'},
        {'name':'Cooper fore-room','local_floor_y':0,'program':'Real crafting/anvil/counter and actual two-wide upper stair'},
        {'name':'Conserved Pippin stock room','local_floor_y':0,'program':'Native moved actual seven BEs; no supply replay or renaming'},
        {'name':'Upper window common room','local_floor_y':4,'program':'Two distinct real dining/ledger groups with low warm light'},
        {'name':'Two real household berths','local_floor_y':4,'program':'Genuine vanilla HOME beds, lockers and clear common access; no resident assigned'},
        {'name':'Small rear-oriel reading bay','local_floor_y':4,'program':'Couch, books, tankard and a supported warm lamp'}]
    return p


def stock_context(home,layout,compound):
    original=checked(home/layout['current_custody_manifest_relative'],layout['current_custody_manifest_sha256'],2*MIB)
    manifest=checked(home/CORRECTED_CUSTODY[0],CORRECTED_CUSTODY[1],2*MIB)
    # This additive correction restricts ownership to the true321/1808 DELTAs.
    # It never changes the approved footprints or actual typed saved contents.
    if original['files']['current-BEs-FULL-TYPED-PRIVATE.jsonl']['sha256']!=manifest['files']['current-BEs-FULL-TYPED-PRIVATE.jsonl']['sha256']:
        raise UserError('The corrected authorship proof may not replace actual saved contents')
    folder=(home/CORRECTED_CUSTODY[0]).parent;member=manifest['files']['capsule-source-cells-FULL-READONLY-PRIVATE.jsonl']
    path=folder/'capsule-source-cells-FULL-READONLY-PRIVATE.jsonl'
    if path.stat().st_size!=member['bytes'] or digest(path)!=member['sha256']:raise UserError('Exact current complete capsule source field required')
    moves=[r for r in layout['exact_proposed_native_pod_transfers'] if r['destination_building']==compound]
    lookup={r['pod_id']:r for r in moves};copied={};unproven=set();preparations=[]
    be_positions={local(r['destination']) for m in moves for r in m['BE_point_transfers']}
    fine=checked(home/FINE[0],FINE[1],8*MIB);visible={(r['x'],r['z']):r.get('visible') for r in fine['samples'] if r['kind']=='dry' and not r['authored_keepout']}
    with path.open(encoding='utf-8') as stream:
        for line in stream:
            row=json.loads(line)
            for ident in row['pod_ids']:
                if ident not in lookup:continue
                move=lookup[ident];q=local([row['position'][i]+move['translation_xyz'][i] for i in range(3)])
                if q in copied and copied[q]!=row['current_saved']:raise UserError('Two retained native-moved capsules conflict')
                copied[q]=row['current_saved']
                if row['classification']=='CURRENT_SOURCE_DIFFERENCE_HOLD_NATIVE_OR_HUMAN_ORIGIN_UNPROVEN' or row['classification']=='UNOWNED_CURRENT_STATE_HOLD' and key(row['current_saved']) not in {'minecraft:air','minecraft:cave_air','minecraft:void_air'}:
                    seen=visible.get((row['position'][0],row['position'][2]));same=seen==[row['position'][1],row['current_saved']]
                    lower=(row['current_saved']=='minecraft:tall_grass[half=lower]' and seen==[row['position'][1]+1,'minecraft:tall_grass[half=upper]'])
                    if row['classification']=='UNOWNED_CURRENT_STATE_HOLD' and key(row['current_saved']) in {'regions_unexplored:grass_sprouts','minecraft:short_grass','minecraft:tall_grass'} and (same or lower) and q not in be_positions:
                        preparations.append({'pod_id':ident,'actual_original_source_position':row['position'],'original_saved_before':row['current_saved'],
                            'proposed_after':'minecraft:air','future_local':list(q),
                            'gate':'SEPARATE exact current native before/ordinary-cover clear/AIR proof BEFORE native capture; not already performed',
                            'original_fine_field_sha256':FINE[1]})
                        copied[q]='minecraft:air'
                    else:unproven.add(q)
    if len(moves)!=3 or len(be_positions)!=17:raise UserError('The exact three current room destinations must be retained')
    return copied,be_positions,unproven,moves,preparations


def validate(p):
    proof=require_material_rule(p.blocks,'The Keel & Cask — entire connected three-mass compound with conserved actual furniture')
    for q in p.current_BE_points:
        if p.blocks[q]!=p.copied[q]:raise UserError('A native-moved current BE would be replaced')
    for q in p.body:
        if key(p.blocks.get(q,'minecraft:air'))!='minecraft:air' and not key(p.blocks[q]).endswith('_door'):raise UserError('Compound route obstructed')
    for q,support in p.supports:
        if key(p.blocks.get(support,'minecraft:air'))=='minecraft:air':raise UserError('A real small fitting is unsupported')
    solid={q for q,s in p.blocks.items() if key(s)!='minecraft:air'};rooted={(x,0,z) for x,z in p.footprint if (x,0,z) in solid};queue=deque(rooted)
    while queue:
        q=queue.popleft()
        for d in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)):
            t=tuple(q[i]+d[i] for i in range(3))
            if t in solid and t not in rooted:rooted.add(t);queue.append(t)
    if solid-rooted:raise UserError('Unrooted authored/captured compound solids: '+str(sorted(solid-rooted)[:5]))
    return {'material':proof,'solids':len(solid),'footprint':len(p.footprint),'walking_body_cells':len(p.body),
        'real_two_wide_stair_cells':len(p.stairs),'preserved_moved_BE_points':len(p.current_BE_points),'new_literal_tagged_fixtures':len(p.tags),'all_source_solids_rooted':True}


def prepare(home,layout_path,layout_sha):
    home=Path(home).resolve();reserve=guard(2*MIB,MAX_OUTPUT)
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve():raise UserError('Only the separately owned private artistic home')
    m=checked(Path(layout_path),layout_sha,2*MIB);r=m['files']['urban-plan-REVIEW-ONLY.json'];layout=checked(Path(layout_path).parent/'urban-plan-REVIEW-ONLY.json',r['sha256'],8*MIB)
    registry=read_json(home/'dashboard/settlement/registry.json');copied,bes,held,moves,preparations=stock_context(home,layout,ID)
    p=build(registry,copied,bes,held);proof=validate(p)
    approved=next(v for v in layout['buildings'] if v['id']==ID)
    if {(x+ORIGIN[0],z+ORIGIN[2]) for x,z in p.footprint}!=set(map(tuple,approved['actual_building_floor_columns_xz'])):
        raise UserError('The first authored compound must use the exact owner-approved floor masses')
    record={'format':'awft-post-native-move-original-urban-building-design:1','name':p.name,'building_id':ID,
        'status':'SOURCE ARCHITECTURAL DESIGN ONLY; not a native-admissible placement format',
        'source_sha256':digest(Path(__file__)),'layout_manifest_sha256':layout_sha,'approved_layout_original_custody_manifest_sha256':layout['current_custody_manifest_sha256'],
        'current_custody_manifest_sha256':CORRECTED_CUSTODY[1],
        'checkpoint_id_of_original_current_capture':layout['current_stopped_checkpoint_id'],'checkpoint_sha256':layout['current_stopped_checkpoint_sha256'],
        'origin':list(ORIGIN),'blocks':[[*world(q),s] for q,s in sorted(p.blocks.items())],
        'exact_approved_floor_masses':approved['masses'],'approved_ground_floor_columns_unchanged':True,
        'new_fixture_tags_ONLY':[{'pos':list(world(q)),'nbt':snbt(tag)} for q,tag in sorted(p.tags.items())],
        'existing_BE_tags_or_items_written':0,'required_native_completed_conserved_moves':[r['pod_id'] for r in moves],
        'separately_required_pre_clone_ordinary_cover_preparations':preparations,
        'retained_current_BE_points':[list(world(q)) for q in sorted(p.current_BE_points)],
        'positively_owned_captured_NONBE_shell_retirement':[{'position':list(world(r['local'])),'expected_native_moved_source':r['expected_native_moved_source']} for r in p.inherited_shell_retirement],
        'routes':p.routes,'rooms':p.rooms,'geometry_proof':proof,'role_counts':dict(Counter(p.roles.values())),
        'native_cameras':[
            {'name':'keel-cask-east-alley','feet':[1236.5,65,-1196.5],'look_at':[1228,71,-1199]},
            {'name':'low-shingle-warehouse-joint','feet':[1225.5,65,-1222.5],'look_at':[1226,70,-1207]},
            {'name':'cooper-front-workroom','feet':[1230.5,65,-1196.5],'look_at':[1224,67,-1199]},
            {'name':'upper-ledger-common','feet':[1226.5,69,-1194.5],'look_at':[1225,70,-1191]},
            {'name':'real-household-berths','feet':[1225.5,69,-1189.5],'look_at':[1227,70,-1186]}],
        'native_next_gates':['Actual native clone model/class/slots/components/conservation for all three rooms',
            'Actual positive-owned old-shell retirement after all dependent stocks captured; preserve all unknown/human/accepted material',
            'Fresh stopped/native after-move full preimage before producing any actual native architectural delta',
            'Current original/bridge/zipline/navigation/AIR model custody; actual door/stair/seating/roof join checks',
            'Real framebuffer exterior and all interior views, then source iteration before propagation'],
        'construction_forbidden':True,'native_actions':0,'world_writes':0,'reserve_guard':reserve}
    raw=canonical(record)+b'\n'
    if len(raw)>MAX_OUTPUT:raise UserError('Bounded compound design output exceeded')
    out=home/'staging'/('keel-cask-original-urban-block-'+str(time.time_ns()));out.mkdir();(out/'building-SOURCE-ONLY.json').write_bytes(raw)
    return {'folder':str(out),'sha256':digest(out/'building-SOURCE-ONLY.json'),'source_cells':len(p.blocks),'rooms':len(p.rooms),'new_tags':len(p.tags),'preserved_native_BE_points':len(p.current_BE_points),'proof':proof,'native_actions':0}


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--home',type=Path,required=True);a.add_argument('--layout-manifest',type=Path,required=True);a.add_argument('--layout-sha256',required=True)
    args=a.parse_args();print(json.dumps(prepare(args.home,args.layout_manifest,args.layout_sha256),indent=2))
