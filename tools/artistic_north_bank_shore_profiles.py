"""Additional authored sea-edge/court infill, with every refused site retained.

Exact saved geography and full old/future source custody precede construction.
No command, world write, acceptance score or whole-village completion claim.
"""
from __future__ import annotations
import argparse,hashlib,json,time
from pathlib import Path
from control_room.common import UserError,digest,read_json
from tools.artistic_north_bank_west_infills import (WestPlan as BaseWestPlan,coastal_shell,furnish,RESERVE,Lot,NorthTerrain,AIR,GROUND,SOFT,NORTH_SOFT,MIB,FACES,base,native_payload,preservation)
from tools.artistic_north_bank_west_connections import TEN,TEN_SHA,STREET,STREET_SHA
from tools.artistic_north_bank_residual import WEST
from tools.artistic_north_bank_west import ZIPLINE_MASK,ZIPLINE_MASK_SHA
from tools.artistic_north_bank_east import canonical_parts
from tools.artistic_bridge_refinement import flatten
from tools.artistic_materials import require_material_rule,require_outdoor_rule
from tools.playtest import guard

CONNECTIONS=('staging/north-bank-western-connections-r2-1793159711602697500/connections.json','b658552ec91b6cd681a3e847dfe9613f51fcf59ca584642a3b184ba7c4e2956a')
SHORE_BOUNDS=(984,-1320,1392,-1120)
PROFILE='staging/north-bank-residual-1793159933733952500/residual-study.json'
PROFILE_SHA='817e58f7314b44390d2006db38d69b0ad3c7f87227b61173ca4649cac75d46d7'
QUAY6=('staging/north-bank-quay-courts-1793159316245611100/prototype.json','6fdbe38c3e4ebb8d2a2f16f9ecdecf59cb977fe7f6d645756ff7f0e47dd97fe0')
EAST22=('staging/north-bank-eastern22-1793157301590833400/prototype.json','956b58ce5a68a008fb7e3e099962c3f51712af604072a77fd2f81d6b7668375c')

class WestPlan(BaseWestPlan):
    def put(self,p,key,*,priority=50,**props):
        p=tuple(p);x,y,z=p
        if not SHORE_BOUNDS[0]<=x<=SHORE_BOUNDS[2] or not SHORE_BOUNDS[1]<=z<=SHORE_BOUNDS[3] or not 59<=y<=105:raise UserError('Profiled shore escaped exact bounded study')
        if (x,z) in self.protected or p in self.saved_BEs:raise UserError('Retain actual protected architecture/AIR/model or savedBE')
        if priority<self.priority.get(p,-1):return
        value=self.state(key,**props);old=self.blocks.get(p)
        if old is not None and base(old) not in AIR and base(value) not in AIR and self.owners.get(p)!=self.group and old!=value:raise UserError('Two authored shore solids collide')
        self.blocks[p]=value;self.priority[p]=priority;self.owners[p]=self.group;self.tags.pop(p,None)
        if len(self.blocks)>150000:raise UserError('Finite individual shore source cap exceeded')

# Coordinates are candidate actual world origins, never screenshot projections.
# Programs vary deliberately; failed envelopes remain failed, not flattened or
# moved through a blind sequence until a cheap box fits.
COURTS=(('gull-thimble', 'Gull & Thimble', (993, -1268), (7, 9), 'recess_ne', 'gambrel', 'south', 'dawnoftimebuilder:blue_plastered_stone', 'minecraft:loom', 'Compact mending shop, canvas and galley', 'Seamstress bed and sunny linen desk'), ('caper-rose', 'Caper Rose', (1017, -1300), (7, 9), 'cropped_nw', 'saltbox', 'south', 'dawnoftimebuilder:red_plastered_stone', 'minecraft:smoker', 'Supper room, provisions and family hearth', 'Sailor household and memory shelf'), ('beacon-book', 'Beacon & Book', (1037, -1304), (7, 9), 'recess_sw', 'cross_gable', 'south', 'dawnoftimebuilder:yellow_plastered_stone', 'minecraft:lectern', 'Sea library, bindings and little reading counter', 'Bookkeeper bed and roof desk'), ('brine-harp', 'Brine Harp', (1057, -1304), (7, 9), 'cropped_ne', 'half_hip', 'south', 'dawnoftimebuilder:green_plastered_stone', 'minecraft:crafting_table', 'Instrument case repair and galley', 'Quiet household room and music shelf'), ('goldfinch-steps', 'Goldfinch Steps', (1073, -1272), (7, 9), 'cropped_sw', 'gambrel', 'south', 'minecraft:cyan_terracotta', 'minecraft:cartography_table', 'Tide charts, tea and instrument corner', 'Harbor family bedroom and account desk'), ('palm-fold', 'Palm Fold', (1085, -1272), (7, 9), 'recess_ne', 'cross_gable', 'south', 'dawnoftimebuilder:plastered_stone', 'minecraft:loom', 'Cloth folding, small stock counter and supper', 'Linen bedroom and candlelit book desk'), ('otter-pantry', 'Otter Pantry', (1173, -1236), (7, 9), 'cropped_ne', 'half_hip', 'south', 'dawnoftimebuilder:red_plastered_stone', 'minecraft:smoker', 'Waterside pantry, soup pot and shared table', 'Warm kitchen-keeper bedroom'), ('gannet-home', 'Gannet House', (1189, -1220), (7, 9), 'recess_sw', 'saltbox', 'north', 'dawnoftimebuilder:blue_plastered_stone', 'minecraft:cartography_table', 'Harbor worker galley and quiet maps', 'Family bed, instruments and reading nook'), ('tide-spool', 'Tide Spool', (1209, -1276), (7, 9), 'cropped_nw', 'gambrel', 'south', 'dawnoftimebuilder:green_plastered_stone', 'minecraft:loom', 'Canvas stock, measuring counter and tea', 'Sailcloth merchant household'), ('vetch-window', 'Vetch Window', (1249, -1142), (7, 9), 'recess_ne', 'cross_gable', 'north', 'dawnoftimebuilder:yellow_plastered_stone', 'minecraft:composter', 'Gardener window, seed pantry and supper', 'Contained flowers and household bedroom'), ('morning-cod', 'Morning Cod', (1257, -1132), (7, 9), 'cropped_sw', 'half_hip', 'north', 'dawnoftimebuilder:blue_plastered_stone', 'minecraft:smoker', 'Fisher household, galley and preparation counter', 'Sea-view bedroom and chart shelf'), ('pearl-linen', 'Pearl & Linen', (1269, -1132), (7, 9), 'recess_nw', 'gambrel', 'north', 'dawnoftimebuilder:plastered_stone', 'minecraft:loom', 'Linen counter and folding workroom', 'Weaver household and supper seat'), ('willow-quill', 'Willow Quill', (1281, -1132), (7, 9), 'cropped_ne', 'cross_gable', 'north', 'minecraft:green_terracotta', 'minecraft:lectern', 'Scribe and sea ledgers, little tea desk', 'Bedroom and private reading corner'), ('blue-pantry', 'Blue Pantry', (1293, -1132), (7, 9), 'recess_se', 'saltbox', 'north', 'dawnoftimebuilder:blue_plastered_stone', 'minecraft:smoker', 'Coastal family kitchen and pantry group', 'Warm bedroom and contained flowers'), ('coral-bell', 'Coral Bell', (1305, -1132), (7, 9), 'cropped_nw', 'half_hip', 'north', 'dawnoftimebuilder:red_plastered_stone', 'minecraft:smithing_table', 'Small metalwork, instrument fittings and supper', 'Artisan bed and account desk'), ('rosy-keel', 'Rosy Keel', (1317, -1132), (7, 9), 'recess_ne', 'gambrel', 'north', 'dawnoftimebuilder:yellow_plastered_stone', 'minecraft:crafting_table', 'Toy boats, hand tools and family table', 'Carver household and book corner'), ('sea-mallow', 'Sea Mallow', (1349, -1132), (7, 9), 'cropped_se', 'cross_gable', 'north', 'dawnoftimebuilder:green_plastered_stone', 'minecraft:composter', 'Flower counter, potting corner and galley', 'Gardener bed and quiet desk'), ('tern-tail', 'Tern Tail', (1365, -1136), (7, 9), 'recess_nw', 'saltbox', 'north', 'minecraft:cyan_terracotta', 'minecraft:cartography_table', 'Quiet coastal chart room and family supper', 'Narrow sea-view bedroom and memory shelf'))


def build_one(registry,fine,program):
    ident,name,(ox,oz),(w,d),shape,roof,face,upper,work,a,b=program
    lot=Lot(ident,name,work.removeprefix('minecraft:').replace('_',' '),(ox+w//2,oz+d//2),(w,d),2,face,shape,roof,
        ('minecraft:bricks' if ident in ('sea-kite','bell-court','plum-lantern','clover-porch','tallow-petal') else 'minecraft:stone_bricks',upper),(a,b),
        name+' — separate carved court house with actual projecting windows, recessed corner and small pitched silhouette')
    p=WestPlan(registry,fine)
    from tools.artistic_north_bank_east import outline
    candidate=outline(lot)
    if any(max(abs(x-a),abs(z-b))<8 for x,z in candidate for a,b in p.lava):raise UserError('Retain eight-metre separation from actual native lava')
    cells,floor,door=coastal_shell(p,lot);furnish(p,lot,cells,floor,work)
    x,feet,z=p.lots[0]['door'];dx,dz=FACES[face];row=p.land[x+dx,z+dz];rise=floor-row['surface_y']
    if row['kind']!='dry' or not 1<=rise<=3:raise UserError('Entrance has no real dry grade')
    for n in range(1,rise+1):
        xx,zz=x+n*dx,z+n*dz;y=floor-n+1;support=p.land[xx,zz]
        if support['kind']!='dry':raise UserError('Entrance would enter water/ice/retained object')
        for yy in range(support['surface_y']+1,y):p.put((xx,yy,zz),'minecraft:stone_bricks',priority=97)
        p.put((xx,y,zz),'minecraft:stone_brick_stairs',priority=98,facing={'north':'south','south':'north','west':'east'}[face],half='bottom',shape='straight',waterlogged=False)
    xx,zz=x+(rise+1)*dx,z+(rise+1)*dz;outer=p.land[xx,zz]
    if outer['kind']!='dry':raise UserError('Complete exterior threshold is not dry')
    p.lots[0]['exterior_threshold_feet']=[xx,outer['surface_y']+1,zz]
    canonical_parts(p);require_material_rule(p.blocks,name+' complete furnished court house')
    blocked=[q for q in set(p.walk) if base(p.blocks.get(q,'minecraft:air')) not in AIR and not any(v in base(p.blocks[q]) for v in ('door','stairs'))]
    if blocked:raise UserError('Actual two-high room/landing blocked '+str(blocked[:3]))
    return p


def encode(d):return (json.dumps(d,separators=(',',':'),ensure_ascii=False)+'\n').encode()


def prepare(home,checkpoint_id,checkpoint_sha):
    home=Path(home).resolve();reserve=guard(2*MIB,32*MIB);receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve() or receipt.get('verified') is not True or receipt.get('id')!=checkpoint_id or receipt.get('sha256')!=checkpoint_sha:raise UserError('Exact stopped court source required')
    registry=read_json(home/'dashboard/settlement/registry.json');protected,custody=preservation(home,registry);prior={};sources=[]
    if digest(home/PROFILE)!=PROFILE_SHA:raise UserError('Exact measured residual profiles required')
    profiles=set(map(tuple,read_json(home/PROFILE)['seven_by_nine_main_plus_model_skirt_centres_xz']))
    for relative,expected in ((TEN+'/prototype.json',TEN_SHA),(STREET,STREET_SHA),WEST,CONNECTIONS,QUAY6,EAST22):
        path=home/relative
        if digest(path)!=expected:raise UserError('Exact prior/future court source changed')
        prior.update(flatten(read_json(path)));sources.append({'path':relative,'sha256':expected})
    cable_path=home/ZIPLINE_MASK
    if digest(cable_path)!=ZIPLINE_MASK_SHA:raise UserError('Future cable custody changed')
    cable=set(flatten(read_json(cable_path)));terrain=NorthTerrain(home,receipt,registry);delta={};before={};retained={};supports={};tags={};lots=[];rooms=[];fixtures=[];refused=[]
    try:
        field=[];x0,z0,x1,z1=SHORE_BOUNDS
        for cx in range(x0//16,x1//16+1):
            for cz in range(z0//16,z1//16+1):
                for x in range(max(x0,cx*16),min(x1,cx*16+15)+1):
                    for z in range(max(z0,cz*16),min(z1,cz*16+15)+1):field.append(terrain.column(x,z))
                terrain.check()
        fine={'samples':field,'saved_BEs':[list(q) for q in terrain.entities],'protected_columns_xz':[list(q) for q in protected]}
        for program in COURTS:
            try:
                center=program[2][0]+3,program[2][1]+4
                if center not in profiles:raise UserError('Centre lacks its exact saved9x11 dry profile; no guessed component-bounds site')
                p=build_one(registry,fine,program);new={};old={};adopt={};under={}
                for q,s in sorted(p.blocks.items(),key=lambda v:(v[0][0]//16,v[0][2]//16,v[0][1])):
                    if q in cable:raise UserError('Keep every exact future frame/cable/boarding cell')
                    if q in prior:
                        if prior[q]!=s:raise UserError('Preserve previous authored AIR/solid/inventory '+str(q))
                        adopt[q]=s;continue
                    actual=terrain.state(*q)
                    if actual is None or q in terrain.entities or base(actual) not in AIR|GROUND|SOFT|NORTH_SOFT or 'waterlogged=true' in actual:raise UserError('Keep real water/ice/tree/BE/foreign cell '+str((q,actual)))
                    new[q]=s;old[q]=actual
                for row in p.lots[0]['dry_proof']['actual_dry_columns']:
                    x,y,z=row['support'];q=x,y-2,z;actual=terrain.state(*q)
                    if actual is None or q in terrain.entities or q in new or base(actual) not in GROUND|{'minecraft:copper_ore','minecraft:coal_ore'}:raise UserError('Unchanged geological support missing')
                    under[q]=actual
                for q,s in new.items():
                    if q in delta and delta[q]!=s:raise UserError('Two independently authored new courts intersect')
                delta.update(new);before.update(old);retained.update(adopt);supports.update(under);tags.update({q:s for q,s in p.tags.items() if q in new});lots.extend(p.lots);rooms.extend(p.rooms);fixtures.extend(p.fixtures)
                prior.update(p.blocks)
            except UserError as failure:refused.append({'id':program[0],'name':program[1],'original_origin_xz':list(program[2]),'reason':str(failure),'status':'REFUSED candidate retained; no construction or native acceptance'})
            terrain.check()
        saved=terrain.snapshot.sources
    finally:terrain.close()
    if not delta:raise UserError('No entire court house qualified; retain refusals without placement')
    require_outdoor_rule(delta,'All newly qualified court houses and entrances')
    docs={'prototype.json':native_payload(registry,delta,checkpoint_sha,'Qualified additional original northwest sea-edge and bridge-arm court houses',tags=tags),
        'before-VERIFY-ONLY.json':native_payload(registry,before,checkpoint_sha,'VERIFY ONLY — exact stopped new court target states'),
        'supports-VERIFY-ONLY.json':native_payload(registry,supports,checkpoint_sha,'VERIFY ONLY — unchanged actual geological court supports')}
    if retained:docs['retained-prior-VERIFY-ONLY.json']=native_payload(registry,retained,checkpoint_sha,'VERIFY ONLY — preserved exact prior/future source; no replay')
    solids=sorted((q,s) for q,s in delta.items() if base(s) not in AIR)
    for n,start in enumerate(range(0,len(solids),15000),1):
        d=native_payload(registry,dict(solids[start:start+15000]),checkpoint_sha,'NORMAL SHAPES ONLY — newly qualified court solids');d.update(construction_forbidden=True,verification_only=True);docs['normal-joins-'+str(n)+'-SETTLE-ONLY.json']=d
    raw={n:encode(v) for n,v in docs.items()};manifest={'format':'awft-profiled-original-shore-houses:1','checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,
        'source_sha256':digest(Path(__file__)),'candidate_count':len(COURTS),'qualified_buildings':len(lots),'lots':lots,'rooms':rooms,'fixtures':fixtures,'refused_candidates':refused,
        'previous_sources':sources,'older_town_custody':custody,'saved_sources':saved,'reserve_guard':reserve,'native_actions':0,'world_writes':0,
        'scope':'Qualified houses only; separate dry public connections and eye-level native review still required. Other residual patches remain; no blanket North-land completion claim.',
        'files':{n:{'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()} for n,v in raw.items()}}
    raw['manifest.json']=encode(manifest)
    if sum(map(len,raw.values()))>32*MIB:raise UserError('Bounded original court output exceeded')
    out=home/'staging'/('north-bank-profiled-shore-'+str(time.time_ns()));out.mkdir()
    for n,v in raw.items():(out/n).open('xb').write(v)
    return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'qualified_buildings':len(lots),'rooms':len(rooms),'fixtures':len(fixtures),'refused_candidates':refused,'files':manifest['files'],'native_actions':0}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);p.add_argument('--checkpoint-id',required=True);p.add_argument('--checkpoint-sha',required=True);a=p.parse_args()
    print(json.dumps(prepare(a.home,a.checkpoint_id,a.checkpoint_sha),indent=2))
