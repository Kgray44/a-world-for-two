"""Additional authored sea-edge/court infill, with every refused site retained.

Exact saved geography and full old/future source custody precede construction.
No command, world write, acceptance score or whole-village completion claim.
"""
from __future__ import annotations
import argparse,hashlib,json,time
from pathlib import Path
from control_room.common import UserError,digest,read_json
from tools.artistic_north_bank_west_infills import (WestPlan,coastal_shell,furnish,RESERVE,Lot,NorthTerrain,AIR,GROUND,SOFT,NORTH_SOFT,MIB,FACES,base,native_payload,preservation)
from tools.artistic_north_bank_west_connections import TEN,TEN_SHA,STREET,STREET_SHA
from tools.artistic_north_bank_residual import WEST
from tools.artistic_north_bank_west import ZIPLINE_MASK,ZIPLINE_MASK_SHA
from tools.artistic_north_bank_east import canonical_parts
from tools.artistic_bridge_refinement import flatten
from tools.artistic_materials import require_material_rule,require_outdoor_rule
from tools.playtest import guard

CONNECTIONS=('staging/north-bank-western-connections-1793159092875816300/connections.json','d3b47b50e28611969e12543b35ef88cc1a22a09127a1f8794d13747cb66b35df')
# Coordinates are candidate actual world origins, never screenshot projections.
# Programs vary deliberately; failed envelopes remain failed, not flattened or
# moved through a blind sequence until a cheap box fits.
COURTS=(
 ('sea-kite','Sea-Kite House',(1016,-1287),(7,9),'cropped_sw','saltbox','south','dawnoftimebuilder:plastered_stone','minecraft:loom','Sailcloth workroom and galley','Mariner bedroom and bright linen shelf'),
 ('cask-star','Cask & Star',(1027,-1290),(9,9),'recess_ne','gambrel','south','dawnoftimebuilder:yellow_plastered_stone','minecraft:crafting_table','Cooper’s tool bench, staves and shared supper','Cooper household with curved window display'),
 ('albatross-ink','Albatross Ink',(1039,-1289),(7,9),'cropped_ne','cross_gable','south','dawnoftimebuilder:blue_plastered_stone','minecraft:cartography_table','Map engraving, paper and instrument counter','Navigator bed, desk and book nook'),
 ('bell-court','The Bronze Wren',(1051,-1288),(8,9),'recess_nw','half_hip','south','dawnoftimebuilder:red_plastered_stone','minecraft:smithing_table','Small bell repair and brass display','Artisan kitchen and warm bedroom'),
 ('sedge-rope','Sedge & Rope',(1002,-1274),(7,8),'cropped_ne','half_hip','south','minecraft:green_terracotta','minecraft:loom','Rope and canvas corner beside the shore','Compact rope-maker household'),
 ('plum-lantern','The Plum Lantern',(1083,-1229),(8,8),'recess_sw','gambrel','south','dawnoftimebuilder:red_plastered_stone','minecraft:smoker','Household galley, pottery shelf and guest seat','Family bed, quiet desk and contained flowers'),
 ('citrine-court','Citrine Court',(1101,-1215),(8,8),'cropped_nw','saltbox','north','dawnoftimebuilder:yellow_plastered_stone','minecraft:cartography_table','Retired sailor study and sunny supper','Little bedroom and maritime memory shelf'),
 ('coral-button','Coral & Button',(1122,-1218),(8,8),'recess_ne','cross_gable','south','dawnoftimebuilder:blue_plastered_stone','minecraft:loom','Buttons, mending and cloth-fitting corner','Dressmaker kitchen and reading bed'),
 ('clover-porch','Clover Porch',(1142,-1206),(8,8),'cropped_sw','half_hip','north','dawnoftimebuilder:green_plastered_stone','minecraft:composter','Potting corner, pantry and shared hearth','Gardener bedroom, seeds and morning desk'),
 ('indigo-nook','The Indigo Nook',(1161,-1201),(8,8),'recess_nw','gambrel','north','minecraft:cyan_terracotta','minecraft:loom','Dyer’s dry textile display and supper','Cozy linen bedroom and desk'),
 ('tallow-petal','Tallow & Petal',(1175,-1217),(8,8),'cropped_se','cross_gable','south','dawnoftimebuilder:plastered_stone','minecraft:crafting_table','Candles, household flowers and tea counter','Candlemaker bed and small book gallery'),
 ('pilot-kin','Pilot’s Kin',(1187,-1232),(8,8),'recess_sw','saltbox','south','dawnoftimebuilder:blue_plastered_stone','minecraft:cartography_table','Harbor pilot instruments, map desk and galley','Family bed, sea-chest and writing corner'),
)


def build_one(registry,fine,program):
    ident,name,(ox,oz),(w,d),shape,roof,face,upper,work,a,b=program
    lot=Lot(ident,name,work.removeprefix('minecraft:').replace('_',' '),(ox+w//2,oz+d//2),(w,d),2,face,shape,roof,
        ('minecraft:bricks' if ident in ('sea-kite','bell-court','plum-lantern','clover-porch','tallow-petal') else 'minecraft:stone_bricks',upper),(a,b),
        name+' — separate carved court house with actual projecting windows, recessed corner and small pitched silhouette')
    p=WestPlan(registry,fine);cells,floor,door=coastal_shell(p,lot);furnish(p,lot,cells,floor,work)
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
    for relative,expected in ((TEN+'/prototype.json',TEN_SHA),(STREET,STREET_SHA),WEST,CONNECTIONS):
        path=home/relative
        if digest(path)!=expected:raise UserError('Exact prior/future court source changed')
        prior.update(flatten(read_json(path)));sources.append({'path':relative,'sha256':expected})
    cable_path=home/ZIPLINE_MASK
    if digest(cable_path)!=ZIPLINE_MASK_SHA:raise UserError('Future cable custody changed')
    cable=set(flatten(read_json(cable_path)));terrain=NorthTerrain(home,receipt,registry);delta={};before={};retained={};supports={};tags={};lots=[];rooms=[];fixtures=[];refused=[]
    try:
        field=[];x0,z0,x1,z1=RESERVE
        for cx in range(x0//16,x1//16+1):
            for cz in range(z0//16,z1//16+1):
                for x in range(max(x0,cx*16),min(x1,cx*16+15)+1):
                    for z in range(max(z0,cz*16),min(z1,cz*16+15)+1):field.append(terrain.column(x,z))
                terrain.check()
        fine={'samples':field,'saved_BEs':[list(q) for q in terrain.entities],'protected_columns_xz':[list(q) for q in protected]}
        for program in COURTS:
            try:
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
    raw={n:encode(v) for n,v in docs.items()};manifest={'format':'awft-extra-original-quay-courts:1','checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,
        'source_sha256':digest(Path(__file__)),'candidate_count':len(COURTS),'qualified_buildings':len(lots),'lots':lots,'rooms':rooms,'fixtures':fixtures,'refused_candidates':refused,
        'previous_sources':sources,'older_town_custody':custody,'saved_sources':saved,'reserve_guard':reserve,'native_actions':0,'world_writes':0,
        'scope':'Qualified houses only; separate dry public connections and eye-level native review still required. Other residual patches remain; no blanket North-land completion claim.',
        'files':{n:{'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()} for n,v in raw.items()}}
    raw['manifest.json']=encode(manifest)
    if sum(map(len,raw.values()))>32*MIB:raise UserError('Bounded original court output exceeded')
    out=home/'staging'/('north-bank-quay-courts-'+str(time.time_ns()));out.mkdir()
    for n,v in raw.items():(out/n).open('xb').write(v)
    return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'qualified_buildings':len(lots),'rooms':len(rooms),'fixtures':len(fixtures),'refused_candidates':refused,'files':manifest['files'],'native_actions':0}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);p.add_argument('--checkpoint-id',required=True);p.add_argument('--checkpoint-sha',required=True);a=p.parse_args()
    print(json.dumps(prepare(a.home,a.checkpoint_id,a.checkpoint_sha),indent=2))
