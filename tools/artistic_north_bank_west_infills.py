"""Ten compact original western households/trades, exact saved-land admission.

Source only. No complete-village, native walk, rendering or resident acceptance
is inferred from their number. Additional residual shore gaps remain recorded.
"""
from __future__ import annotations
import argparse
from collections import deque
import hashlib,json,time
from pathlib import Path

from control_room.common import UserError,digest,read_json
from tools.artistic_bridge_refinement import flatten
from tools.artistic_north_bank_east import (EastPlan,Lot,NorthTerrain,canonical_parts,outline,boundary,dry_footprint,facade_windows,make_roof,
    AIR,GROUND,SOFT,NORTH_SOFT,MIB,FACES,base,native_payload,preservation)
from tools.artistic_north_bank_compass_bend import furniture as base_furniture,clear_fixture
from tools.artistic_north_bank_west import ZIPLINE_MASK,ZIPLINE_MASK_SHA
from tools.artistic_north_bank_residual import WEST,STREET
from tools.artistic_materials import require_material_rule,require_outdoor_rule
from tools.playtest import guard

RESERVE=(984,-1320,1216,-1180)
# Origins were independently surveyed by the western author. These new main
# outlines are independently requalified; their former L/notch study is not
# borrowed as proof of these final cropped/recessed fields.
PROGRAMS=(
 ('sailmaker','The Lark’s Canvas',(1004,-1262),(7,8),'recess_ne','gambrel','minecraft:bricks','dawnoftimebuilder:yellow_plastered_stone','minecraft:loom','Canvas cutting and net pantry','Sailmaker bedroom and folded linen'),
 ('ferryman','The Oar & Feather',(1038,-1240),(5,8),'cropped_nw','saltbox','minecraft:stone_bricks','dawnoftimebuilder:blue_plastered_stone','minecraft:barrel','Compact ferryman galley, cot and quiet reading seat',''),
 ('apothecary','Juniper’s Remedy',(1052,-1241),(8,8),'recess_sw','cross_gable','minecraft:bricks','dawnoftimebuilder:green_plastered_stone','minecraft:brewing_stand','Herb workroom, careful remedies and tea pantry','Herbalist household with a planted window'),
 ('baker','The Copper Crust',(1063,-1240),(8,8),'cropped_ne','half_hip','minecraft:stone_bricks','dawnoftimebuilder:red_plastered_stone','minecraft:smoker','Bakery counter, oven hood and flour pantry','Baker household and supper corner'),
 ('stargazer','The Small Astrolabe',(1094,-1239),(8,8),'recess_nw','steep','minecraft:bricks','minecraft:cyan_terracotta','minecraft:cartography_table','Seafarer chart study, supper and instruments','Sky-reader bedroom and lantern window'),
 ('weaver','Wren & Willow',(1111,-1238),(9,9),'cropped_se','gambrel','minecraft:stone_bricks','dawnoftimebuilder:yellow_plastered_stone','minecraft:loom','Textile counter, cutting corner and colorful cloth','Family bedroom, linen cupboard and window desk'),
 ('mariner','The Two Tides',(1136,-1220),(8,8),'cropped_nw','cross_gable','minecraft:bricks','dawnoftimebuilder:blue_plastered_stone','minecraft:cartography_table','Mariner sitting room, galley and sea-chest nook','Travel bedroom, memory shelf and tea seat'),
 ('bookbinder','The Bent Page',(1151,-1218),(8,8),'recess_ne','gambrel','minecraft:stone_bricks','minecraft:green_terracotta','minecraft:lectern','Book bindings, ink desk and little reading shop','Binder household and quiet book-lined bedroom'),
 ('soup-kitchen','The Kindly Kettle',(1165,-1222),(8,8),'cropped_se','half_hip','minecraft:bricks','dawnoftimebuilder:plastered_stone','minecraft:smoker','Public soup galley, food counter and supper seating','Cook’s private bed, desk and herb shelf'),
 ('fish-curer','Silverfin & Smoke',(1107,-1268),(8,10),'recess_sw','saltbox','minecraft:stone_bricks','dawnoftimebuilder:blue_plastered_stone','minecraft:smoker','Fish preparation, empty stock chest and smoker hood','Merchant household, charts and sheltered bedroom'),
)


class WestPlan(EastPlan):
    def put(self,p,key,*,priority=50,**props):
        p=tuple(p);x,y,z=p
        if not RESERVE[0]<=x<=RESERVE[2] or not RESERVE[1]<=z<=RESERVE[3] or not 59<=y<=105:raise UserError('Western original geometry escaped its finite reviewed study')
        if (x,z) in self.protected or p in self.saved_BEs:raise UserError('Preserve western architecture/model/AIR or saved BE '+str(p))
        if priority<self.priority.get(p,-1):return
        value=self.state(key,**props);old=self.blocks.get(p)
        if old is not None and base(old) not in AIR and base(value) not in AIR and self.owners.get(p)!=self.group and old!=value:raise UserError('Two original western solids collide '+str(p))
        self.blocks[p]=value;self.priority[p]=priority;self.owners[p]=self.group;self.tags.pop(p,None)
        if len(self.blocks)>150000:raise UserError('Finite western source target cap exceeded')


def furniture(p,q,key,*,support=None,**props):
    if support is not None and base(p.blocks.get(tuple(support),'minecraft:air')) in AIR:return False
    return base_furniture(p,q,key,support=support,**props)


def coastal_shell(p,lot):
    cells=outline(lot)
    proof=dry_footprint(type('Saved',(),{'entities':p.saved_BEs,'column':lambda _,x,z:p.land.get((x,z),{'kind':'unknown'})})(),cells,p.protected)
    p.group=lot.name;floor=proof['floor_y'];x0,x1=min(x for x,z in cells),max(x for x,z in cells);z0,z1=min(z for x,z in cells),max(z for x,z in cells)
    skirt={(x+dx,z+dz) for x,z in cells for dx in (-1,0,1) for dz in (-1,0,1)}
    # All main feet are real dry land. At the shore the owner's explicitly
    # permitted tiny cantilever may be a one-block eave ABOVE water/ice, never
    # a filled/coerced ground column. Its actual complete preimage is checked.
    for x,z in skirt:
        row=p.land.get((x,z),{})
        if row.get('kind') not in ('dry','water','retained_object'):raise UserError('Unknown coastal overhang column')
        for y in range(floor,floor+lot.levels*4+8):p.put((x,y,z),'minecraft:air',priority=10)
    for x,z in cells:
        for y in range(p.land[x,z]['surface_y']-1,floor):
            key='minecraft:polished_andesite' if (x-x0)%4==0 else 'minecraft:stone_bricks'
            if (z-z0)%8==7:key='minecraft:chiseled_stone_bricks' if (x-x0)%4==0 else 'minecraft:mossy_stone_bricks'
            p.put((x,y,z),key,priority=35)
    edge=boundary(cells)
    for level in range(lot.levels):
        f=floor+4*level;p.floor(cells,f)
        for x,z in edge:
            post=(x-x0)%3==0 if z in (z0,z1) else (z-z0)%3==0
            for dy in (1,2,3):p.put((x,f+dy,z),'minecraft:stripped_dark_oak_log' if post else lot.finish[level],**({'axis':'y'} if post else {}))
            cap='minecraft:dark_oak_wood' if z in (z0,z1) else 'minecraft:stripped_oak_wood' if (z-z0)%8==7 else 'minecraft:oak_wood'
            p.put((x,f+4,z),cap,priority=60,axis='x' if z in (z0,z1) else 'z')
        facade_windows(p,lot,cells,f,level)
        if x1-x0+1==8:
            # Even-width houses have a deliberate central structural mullion,
            # so two adjacent glazed bays do not become a flat four-wide wall
            # in both Cartesian planes under the complete-building3/9 rule.
            for z in (z0,z1):
                for dy in (2,3):
                    q=x0+4,f+dy,z
                    if base(p.blocks.get(q,'minecraft:air'))=='mcwwindows:dark_oak_plank_window':p.put(q,'minecraft:stripped_dark_oak_log',priority=80,axis='y')
        p.rooms.append({'building':lot.ident,'level':level,'floor_y':f,'floor_cells':[list(q) for q in sorted(cells)],'program':lot.rooms[level]})
    p.floor(cells,floor+lot.levels*4);make_roof(p,lot,cells,floor+lot.levels*4)
    face=lot.face;dx,dz=FACES[face];door=(x0,lot.center[1]) if face=='west' else (lot.center[0],z0 if face=='north' else z1)
    for dy,half in ((1,'lower'),(2,'upper')):p.put((door[0],floor+dy,door[1]),'mcwdoors:dark_oak_cottage_door',priority=98,facing={'north':'south','south':'north','west':'east'}[face],half=half,hinge='left',open=False,powered=False)
    for n in (-1,0,1):
        for dy in (1,2):p.walk.append((door[0]+n*dx,floor+dy,door[1]+n*dz))
    p.text((door[0]+dx,floor+3,door[1]+dz),(lot.name,lot.trade[:20],'Western Quay',''),face)
    p.lots.append({'id':lot.ident,'name':lot.name,'trade':lot.trade,'floor_y':floor,'main_footprint':[list(q) for q in sorted(cells)],
        'dry_proof':proof,'front':face,'door':[door[0],floor+1,door[1]],'storeys':lot.levels,'motif':lot.motif,
        'shore_rule':'All main cells dry; one-block roof/eave skirt above exact known water/ice may remain, no underwater target/fill'})
    return cells,floor,door


def furnish(p,lot,cells,floor,work):
    x0,x1=min(x for x,z in cells),max(x for x,z in cells);z0,z1=min(z for x,z in cells),max(z for x,z in cells);cx=lot.center[0]
    # Short eight-metre houses use the whole available run, with an actual
    # westward upper landing. No top riser cuts the rear external wall.
    stairx=x1-2 if lot.outline.endswith('ne') else x1-1;entry=z1-2;exit=entry-4
    if lot.levels>1:
        for n in range(1,5):
            q=stairx,floor+n,entry-n;p.put(q,'minecraft:spruce_stairs',priority=99,facing='north',half='bottom',shape='straight',waterlogged=False)
            for dy in (1,2,3):p.put((q[0],q[1]+dy,q[2]),'minecraft:air',priority=100)
    for level in range(lot.levels):
        f=floor+4*level;room=next(r for r in p.rooms if r['building']==lot.ident and r['level']==level)
        aisle={(cx,z) for z in range(z0+1,z1)}
        if lot.face=='west':aisle|={(x,lot.center[1]) for x in range(x0+1,cx+1)}
        if level==0 and lot.levels>1:aisle|={(x,entry) for x in range(cx,stairx+1)}
        if level:aisle|={(x,exit) for x in range(cx,stairx+1)}
        for x,z in aisle:
            for dy in (1,2):p.walk.append((x,f+dy,z))
        begin=len(p.fixtures)
        for x in range(x0+1,x1):p.put((x,f+3,z0+3),'dawnoftimebuilder:spruce_beam',priority=76,axis_x=True,axis_y=False,axis_z=False,bottom=True,waterlogged=False)
        for z in range(z0+1,z1):p.put((cx-1,f+3,z),'dawnoftimebuilder:spruce_support_slab',priority=77,pillar_connection='nothing',waterlogged=False)
        for x,z,face in ((x0+1,z0+1,'east'),(x1-1,z1-1,'west')):
            back=x+(-1 if face=='east' else 1),f+3,z
            if base(p.blocks.get(back,'minecraft:air')) not in AIR:furniture(p,(x,f+3,z),'mcwlights:bell_wall_lantern',support=back,facing=face)
        # Working equipment sits on a real floor with an unblocked central
        # aisle; new empty containers never impersonate existing inventory.
        q=x0+1,f+1,z0+1
        key=work if level==0 else 'handcrafted:oak_desk'
        props=({'facing':'east','color':'none','waterlogged':False} if level else
            {'facing':'east','lit':False} if key=='minecraft:smoker' else
            {'facing':'east','has_book':False,'powered':False} if key=='minecraft:lectern' else
            {'facing':'east'} if key=='minecraft:loom' else {'facing':'up','open':False} if key=='minecraft:barrel' else {})
        for x,z in ((x0+1,z0+1),(x0+1,z0+2),(x1-2,z0+1),(x1-2,z0+2)):
            candidate=x,f+1,z
            if furniture(p,candidate,key,support=(x,f,z),**props):q=candidate;break
        else:raise UserError('Every actual room needs a physically supported accessible work/desk corner')
        if level:furniture(p,(q[0],f+2,q[2]),'handcrafted:stackable_book',support=q,books=3,facing='east',seed=level+3)
        # Independent pantry/book counter, seated corner and visible stock.
        for z in (z0+2,z0+3):
            q=x0+1,f+1,z
            furniture(p,q,'handcrafted:spruce_counter',support=(q[0],f,z),facing='east',counter='dark_oak_planks',type='1')
        furniture(p,(x0+1,f+2,z0+2),'handcrafted:berry_jam_jar',support=(x0+1,f+1,z0+2),facing='east',jars=2,waterlogged=False)
        furniture(p,(x0+1,f+2,z0+3),'minecraft:potted_allium',support=(x0+1,f+1,z0+3))
        if lot.size[0]>=7:
            tx,tz=x1-2,z1-2
            for pos,name,fields in (((tx,f+1,tz),'handcrafted:spruce_table',dict(color='none',shape='single',waterlogged=False)),
                ((tx,f+2,tz),'handcrafted:wood_cup',dict(facing='west',pieces=2,waterlogged=False)),
                ((tx-1,f+1,tz),'handcrafted:spruce_chair',dict(facing='east',color='none',waterlogged=False))):
                furniture(p,pos,name,support=(pos[0],pos[1]-1,pos[2]),**fields)
        else:
            furniture(p,(x1-1,f+1,z0+2),'dawnoftimebuilder:birch_footstool',support=(x1-1,f,z0+2),facing='west',waterlogged=False)
        # Sleeping accommodation is actually present even in the single-storey
        # ferryman cottage; the wider trades sleep in their true upper rooms.
        if level or lot.levels==1:
            bx,bz=x0+1,z1-3
            for dz,part in ((0,'head'),(1,'foot')):furniture(p,(bx,f+1,bz+dz),'minecraft:blue_bed',support=(bx,f,bz+dz),facing='north',occupied=False,part=part)
        else:
            furniture(p,(x0+1,f+1,z1-2),'handcrafted:spruce_couch',support=(x0+1,f,z1-2),facing='east',color='green',shape='single',waterlogged=False)
        for x,z,face in ((x0+1,z1-1,'east'),(x1-1,z0+1,'west')):
            q=x,f+2,z;dx,dz=FACES[face];back=x-dx,f+2,z-dz
            if clear_fixture(p,q) and base(p.blocks.get(back,'minecraft:air')) not in AIR:p.display(q,'minecraft:book' if level else 'minecraft:paper',lot.name+' — '+room['program'],face)
        room.update(furnishing_objects=len(p.fixtures)-begin,circulation_reserved=True,ceiling='Actual half-height timber coffers and supported compact wall lamps')


def construct(registry,fine):
    p=WestPlan(registry,fine)
    for ident,name,(ox,oz),(w,d),shape,roof,lower,upper,work,a,b in PROGRAMS:
        levels=1 if ident=='ferryman' else 2;face='west' if ident=='fish-curer' else 'north' if ident=='mariner' else 'south'
        lot=Lot(ident,name,work.removeprefix('minecraft:').replace('_',' '),(ox+w//2,oz+d//2),(w,d),levels,face,shape,roof,(lower,upper)[:levels],(a,b)[:levels],name+' — separate dry-fit cropped house, true window projections and modeled trade interior')
        cells,floor,door=coastal_shell(p,lot);furnish(p,lot,cells,floor,work)
        for q,tag in list(p.tags.items()):
            if p.owners.get(q)==lot.name:p.tags[q]=tag.replace('Rose Reach','Western Quay')
        # Supported contained flowers on a shallow side sill avoid bulky
        # awnings over the narrow public lane.
        x,z=min(x for x,z in cells),lot.center[1]+(2 if lot.face=='west' else 0)
        if (x,z) in cells:
            p.put((x-1,floor+1,z),'minecraft:dark_oak_slab',priority=82,type='top',waterlogged=False)
            p.put((x-1,floor,z),'mythrais:small_curved_corbel_dark_oak',priority=82,facing='west',shape=0)
            furniture(p,(x-1,floor+2,z),'minecraft:potted_cornflower',support=(x-1,floor+1,z))
        x,feet,z=p.lots[-1]['door'];dx,dz=FACES[face];row=p.land[x+dx,z+dz];rise=floor-row['surface_y']
        if row['kind']!='dry' or not 1<=rise<=3:raise UserError('Western doorstep needs a dry actual grade '+str((ident,[x,floor,z+dz],row)))
        for n in range(1,rise+1):
            xx,zz=x+n*dx,z+n*dz;y=floor-n+1;ground=p.land[xx,zz]
            if ground['kind']!='dry':raise UserError('No main entrance on water, ice or a retained foreign object '+str((ident,[x,y,zz],ground)))
            for yy in range(ground['surface_y']+1,y):p.put((xx,yy,zz),'minecraft:stone_bricks',priority=97)
            p.put((xx,y,zz),'minecraft:stone_brick_stairs',priority=98,facing={'north':'south','south':'north','west':'east'}[face],half='bottom',shape='straight',waterlogged=False)
        xx,zz=x+(rise+1)*dx,z+(rise+1)*dz;outer=p.land[xx,zz]
        if outer['kind']!='dry':raise UserError('Public entrance threshold must remain actual dry land')
        p.lots[-1]['exterior_threshold_feet']=[xx,outer['surface_y']+1,zz]
    canonical_parts(p)
    return p


def prepare(home,checkpoint_id,checkpoint_sha):
    home=Path(home).resolve();reserve=guard(4*MIB,32*MIB);receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve() or receipt.get('verified') is not True or receipt.get('id')!=checkpoint_id or receipt.get('sha256')!=checkpoint_sha:raise UserError('Exact current authorized stopped western source required')
    registry=read_json(home/'dashboard/settlement/registry.json');protected,custody=preservation(home,registry);prior={}
    for relative,sha in (WEST,STREET):
        path=home/relative
        if digest(path)!=sha:raise UserError('Current western shops/streets preservation source changed')
        prior.update(flatten(read_json(path)))
    cable=home/ZIPLINE_MASK
    if digest(cable)!=ZIPLINE_MASK_SHA:raise UserError('Current future western cable body changed')
    forbidden=set(prior)|set(flatten(read_json(cable)));terrain=NorthTerrain(home,receipt,registry);field=[]
    try:
        x0,z0,x1,z1=RESERVE
        for cx in range(x0//16,x1//16+1):
            for cz in range(z0//16,z1//16+1):
                for x in range(max(x0,cx*16),min(x1,cx*16+15)+1):
                    for z in range(max(z0,cz*16),min(z1,cz*16+15)+1):field.append(terrain.column(x,z))
                terrain.check()
        fine={'samples':field,'saved_BEs':[list(q) for q in terrain.entities],'protected_columns_xz':[list(q) for q in protected]}
        p=construct(registry,fine);materials=[require_material_rule({q:s for q,s in p.blocks.items() if p.owners[q]==lot['name']},lot['name']+' whole furnished western infill') for lot in p.lots]
        require_outdoor_rule(p.blocks,'Complete western households and botanical sills')
        bad=[q for q in set(p.walk) if base(p.blocks.get(q,'minecraft:air')) not in AIR and not any(v in base(p.blocks[q]) for v in ('door','stairs'))]
        if bad:raise UserError('A real western two-high route is blocked '+str([(q,p.blocks[q]) for q in bad[:5]]))
        before={};supports={}
        for q,s in sorted(p.blocks.items(),key=lambda v:(v[0][0]//16,v[0][2]//16,v[0][1])):
            old=terrain.state(*q)
            if q in forbidden:raise UserError('Keep every previous western street/shop/source AIR and exact future cable '+str(q))
            if old is None or q in terrain.entities or base(old) not in AIR|GROUND|SOFT|NORTH_SOFT or 'waterlogged=true' in old:raise UserError('Keep current tree/water/BE/foreign source '+str((q,old)))
            before[q]=old
        for lot in p.lots:
            for row in lot['dry_proof']['actual_dry_columns']:
                x,y,z=row['support'];q=x,y-2,z;actual=terrain.state(*q)
                if q in p.blocks or q in terrain.entities or actual is None or base(actual) not in GROUND|{'minecraft:coal_ore','minecraft:copper_ore'}:raise UserError('Preserve actual unchanged load-bearing geological support '+str((q,actual)))
                supports[q]=actual
        saved=terrain.snapshot.sources
    finally:terrain.close()
    docs={'prototype.json':native_payload(registry,p.blocks,checkpoint_sha,'Ten new original western households and trades',tags=p.tags),
        'before-VERIFY-ONLY.json':native_payload(registry,before,checkpoint_sha,'VERIFY ONLY — exact saved western original house targets'),
        'supports-VERIFY-ONLY.json':native_payload(registry,supports,checkpoint_sha,'VERIFY ONLY — retained actual western dry edge supports')}
    solids={q:s for q,s in p.blocks.items() if base(s) not in AIR}
    if len(solids)>20000:raise UserError('Split actual new normal-join targets')
    docs['normal-joins-SETTLE-ONLY.json']=native_payload(registry,solids,checkpoint_sha,'NORMAL SHAPES ONLY — new western house solids; no replay');docs['normal-joins-SETTLE-ONLY.json'].update(construction_forbidden=True,verification_only=True)
    raw={n:(json.dumps(v,separators=(',',':'),ensure_ascii=False)+'\n').encode() for n,v in docs.items()}
    manifest={'format':'awft-western-ten-house-source:1','checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'source_sha256':digest(Path(__file__)),
        'lots':p.lots,'rooms':p.rooms,'fixtures':p.fixtures,'supports':p.supports,'two_high_source_body':[list(q) for q in sorted(set(p.walk))],
        'material_checks':materials,'outdoor9':True,'previous_sources':custody,'future_cable_sha256':ZIPLINE_MASK_SHA,'saved_sources':saved,'reserve_guard':reserve,
        'external_routes':'Thresholds are exact source only; separate connected2–3wide public lane must be authored/native verified before calling these connected homes',
        'native_actions':0,'world_writes':0,'whole_north_shore_complete':False,'native_or_visual_acceptance':False,
        'files':{n:{'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()} for n,v in raw.items()}}
    raw['manifest.json']=(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n').encode()
    if sum(map(len,raw.values()))>32*MIB:raise UserError('Finite western output cap exceeded')
    out=home/'staging'/('north-bank-western-ten-'+str(time.time_ns()));out.mkdir()
    for n,v in raw.items():(out/n).open('xb').write(v)
    return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'buildings':len(p.lots),'rooms':len(p.rooms),'furnishings':len(p.fixtures),'targets':len(p.blocks),'files':manifest['files'],'native_actions':0}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--home',type=Path,required=True);parser.add_argument('--checkpoint-id',required=True);parser.add_argument('--checkpoint-sha',required=True);a=parser.parse_args()
    print(json.dumps(prepare(a.home,a.checkpoint_id,a.checkpoint_sha),indent=2))
