"""Small W3 refinement drawn from the actual native47 images, not a new batch.

North Cooper face: a supported real oriel and recessed gable casement. Wick:
practical normal lanterns and contained planting. No old furniture/BE/roof replay.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import time

from control_room.common import UserError,digest,read_json
from tools.artistic_spawn_plaza import state
from tools.artistic_bridge_refinement import flatten
from tools.artistic_west_r2_frontage import construct as original_construct,LABELS,DEFAULT_ORIGIN,key
from tools.artistic_materials import require_material_rule
from tools.artistic_mill_detail import joined_window_part
from tools.settlement_attractions import properties

MIB=1024**2
AIR='minecraft:air'
BASE=('staging/west-r2-three-frontage-preview-1793168582590227200/three-frontages-PROPOSAL.json','336363fd0adeb0043117ce4e3ed68b32d3e7c2305d895daa68a9a027124ff5c9')
BASE_PROOF=('dashboard/settlement/settlement-result-ac528755-ba2d-46a3-a5d4-a1e090ec0fcd.json','a6aa196bcc0460874c5d1b4f3840642823ba26b884bfbb2c1dad3dd87580f73b')
IMAGES={'wick-bend':'3521d506134671ae00d6516b14b62039099b03a79a14931a7e29dad11a69e52f',
        'cooper-barrow':'98636b257fe1480d3de9a7b571d2d0923f660d5e4f5eb5c1bcdcb82a4e4fa7d8',
        'three-roofs':'73ce24a07176d5bf6344de2732d7ed7e65f64edaafa853ceeb54ac18647df222',
        'wick-shop':'dc29e83f1dc405fb94caa44affbf249a12560d1315bf98def7f4d18dc3cf1f27'}
STRUCTURE={'minecraft:gray_terracotta','minecraft:light_gray_terracotta','minecraft:brown_terracotta',
    'minecraft:stripped_dark_oak_log','minecraft:stripped_spruce_log','minecraft:dark_oak_planks',
    'minecraft:spruce_planks','minecraft:dark_oak_wood','minecraft:stripped_spruce_wood',
    'minecraft:andesite','minecraft:stone_bricks','minecraft:cobblestone','chipped:detailed_dark_oak_planks'}


class Refinement:
    def __init__(self,registry,original=None):
        self.registry=registry;self.p=original_construct(registry);self.origin=self.p.origin
        ox,oy,oz=self.origin
        pure={(x+ox,y+oy,z+oz):s for (x,y,z),s in self.p.blocks.items()}
        self.original=dict(pure if original is None else original)
        self.blocks={};self.before={};self.reasons={};self.owners={};self.supports=[]
        self.owner=LABELS[0]

    def world(self,q):return tuple(a+b for a,b in zip(q,self.origin))

    def current(self,q):return self.blocks.get(q,self.original.get(q,AIR))

    def put(self,x,y,z,name,reason,**props):
        q=self.world((x,y,z));old=self.original.get(q,AIR)
        if key(old)!=AIR and key(old) not in STRUCTURE:
            raise UserError('Never replace W3 furniture, windows, roof, BE or stock: '+str((q,old)))
        value=state(self.registry,name,**props)
        if q in self.blocks and self.blocks[q]!=value:raise UserError('Two refinement roles conflict')
        self.blocks[q]=value;self.before[q]=old;self.reasons[q]=reason;self.owners[q]=self.owner
        if len(self.blocks)>150:raise UserError('Keep the first photo-led delta small')

    def beam(self,x,y,z,reason):
        self.put(x,y,z,'dawnoftimebuilder:charred_spruce_beam',reason,axis_x=True,axis_y=False,axis_z=False,bottom=True,waterlogged=False)

    def support(self,detail,backing,reason):
        self.supports.append({'detail':list(self.world(detail)),'backing':list(self.world(backing)),'reason':reason})


def construct(registry,original=None):
    d=Refinement(registry,original);d.owner=LABELS[1]
    # A genuine one-metre projecting window room; the old opaque front is
    # opened behind it, so it has depth/use inside rather than an applied decal.
    for x in range(11,15):
        d.put(x,8,2,'minecraft:dark_oak_planks','supported oriel floor')
        d.beam(x,12,2,'continuous load-bearing oriel head')
        d.support((x,8,2),(x,8,3),'oriel floor tied back into the existing upper floor')
    for x in (11,14):
        d.put(x,7,2,'mythrais:curved_corbel_dark_oak','real carved oriel knee',facing='north',shape=0)
        d.support((x,7,2),(x,7,3),'carved knee backed by the real lower-storey wall')
        for y in (9,10,11):d.put(x,y,2,'minecraft:stripped_dark_oak_log','oriel corner post',axis='y')
    for x in (12,13):
        for y in (9,10,11):
            d.put(x,y,2,'mcwwindows:dark_oak_plank_window','real tall oriel glazing',facing='north',part='base')
            d.put(x,y,3,AIR,'real opening behind the new projecting oriel')
    for x in (13,14):
        for y in (13,14):d.put(x,y,3,'mcwwindows:dark_oak_plank_window','inset high gable casement below the retained roof',facing='north',part='base')
    for x in (12,15):
        d.put(x,13,2,'dawnoftimebuilder:charred_spruce_roof_support','small shaped gable shoulder below existing eaves',facing='north',shape='straight',type='top',waterlogged=False)
        d.support((x,13,2),(x,13,3),'shoulder backed by actual framed gable')
    # Contained plants cannot grow an unreviewed tree into the flight clearance.
    for x in range(11,15):
        d.put(x,8,1,'minecraft:dark_oak_slab','narrow supported oriel planting ledge',type='top',waterlogged=False)
        d.support((x,8,1),(x,8,2),'ledge connected to real oriel sill')
    d.put(12,9,1,'minecraft:potted_fern','contained green window planting')
    d.put(13,9,1,'minecraft:potted_red_tulip','contained warm flower accent')
    d.owner=LABELS[0]
    for x,z in ((3,4),(2,6)):
        d.put(x,3,z,'minecraft:lantern','real warm task light under an existing full floor joist',hanging=True,waterlogged=False)
        d.support((x,3,z),(x,4,z),'normal native hanging-lantern upper support')
    for x in (0,1,2):
        d.put(x,0,11,'minecraft:dark_oak_slab','small planted shop-window ledge outside the two-wide core',type='top',waterlogged=False)
        d.support((x,0,11),(x,0,10),'window ledge tied into the existing ground-floor front')
    d.put(0,1,11,'handcrafted:terracotta_thin_pot','small inert pottery alongside living plants')
    d.put(1,1,11,'minecraft:potted_fern','contained shop-window greenery')
    d.put(2,1,11,'minecraft:potted_oxeye_daisy','contained bright shop-window flowers')
    merged={**d.original,**d.blocks}
    # Exact native window mask; never accept whatever part happens to be saved.
    for q,value in tuple(d.blocks.items()):
        if key(value)!='mcwwindows:dark_oak_plank_window':continue
        x,y,z=q;same=lambda other:key(merged.get(other,AIR))==key(value)
        fields=properties(value)
        fields['part']=joined_window_part(same((x,y+1,z)),same((x,y-1,z)),same((x-1,y,z)),same((x+1,y,z)))
        d.blocks[q]=state(registry,key(value),**fields)
    return d


def check(d):
    merged={**d.original,**d.blocks};ox,oy,oz=d.origin
    owners={d.world(q):owner for q,owner in d.p.owners.items()};owners.update(d.owners)
    # Retain measured shallow base footings in the COMPLETE material audit.
    for q in merged:
        if q in owners:continue
        local=(q[0]-ox,q[2]-oz)
        for owner,cells in d.p.main.items():
            if local in cells:owners[q]=owner;break
    rules=[require_material_rule({q:s for q,s in merged.items() if owners.get(q)==owner},'W3 photo-led COMPLETE '+owner) for owner in LABELS]
    for row in d.supports:
        if key(merged.get(tuple(row['backing']),AIR))==AIR:raise UserError('No real structural support for a proposed detail: '+str(row))
    # Existing whole two-wide routes and all original room circulation survive.
    for route in d.p.routes:
        for x,y,z in route['positions']:
            for h in (0,1):
                q=d.world((x,y+h,z));s=merged.get(q,AIR)
                if s!=AIR and not key(s).endswith('_door'):raise UserError('No relief/plant/light may obstruct the actual route: '+str(q))
    untouched={q:s for q,s in d.original.items() if q not in d.blocks}
    if any(key(s).startswith(('handcrafted:','supplementaries:','mcwdoors:')) for q,s in d.before.items()):raise UserError('All original furniture and utility blocks must remain untouched')
    return {'targets':len(d.blocks),'complete_building_material_rules':rules,'all_original_roof_cells_retained':True,
            'existing_BE_or_inventory_targets':0,'original_route_points_retained':sum(len(r['positions']) for r in d.p.routes),
            'unchanged_original_addresses':len(untouched),'native_render_and_artistic_acceptance':'PENDING new actual photos'}


def prepare(home,checkpoint_id,checkpoint_sha):
    from tools.playtest import guard
    from tools.artistic_north_bank_east import NorthTerrain,native_payload
    from tools.artistic_west_r2_study import ZIP
    from tools.artistic_zipline_catenary import reader_budget
    home=Path(home).resolve();reserve=guard(2*MIB,8*MIB);memory=reader_budget()
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve():raise UserError('Private artistic preview only')
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    if receipt.get('verified') is not True or (receipt.get('id'),receipt.get('sha256'))!=(checkpoint_id,checkpoint_sha) or 'stopped' not in receipt.get('scope','').lower():raise UserError('Fresh stopped POST-W3 checkpoint is required')
    registry=read_json(home/'dashboard/settlement/registry.json')
    for rel,sha in (BASE,BASE_PROOF,ZIP):
        if digest(home/rel)!=sha:raise UserError('Exact placed W3 proof and placed zipline custody required')
    proof=read_json(home/BASE_PROOF[0])
    if proof.get('failures')!=0 or proof.get('plan_sha256')!=BASE[1] or proof.get('temporary_tickets_remaining')!=0:raise UserError('Prior W3 native strict proof is not complete/clean')
    if digest(Path(str(home/BASE_PROOF[0])+'.complete'))!='1920231ed0a8267412cc61bfa6cdf03ab72872a5bf2456ed06c18a7b72e75fbf':raise UserError('Exact immutable native completion marker required')
    saved_at=datetime.fromisoformat(receipt['at'].replace('Z','+00:00'))
    verified_at=datetime.fromisoformat(proof['finished'].replace('Z','+00:00'))
    if saved_at<=verified_at:raise UserError('An older checkpoint cannot contain the later native-verified W3 build')
    for name,sha in IMAGES.items():
        if digest(home/'logs/visual-review/r47-west3-a'/(name+'.png'))!=sha:raise UserError('Actual image reference changed')
    plan=read_json(home/BASE[0])
    if Path(registry['world_path']).resolve()!=home/'world'/'RosewaterArtistic' or plan['world_path']!=registry['world_path'] or str(plan['seed'])!=str(registry['seed']):raise UserError('Exact private artistic world/source identity required')
    d=construct(registry,flatten(plan));checks=check(d)
    if set(d.blocks)&set(flatten(read_json(home/ZIP[0]))):raise UserError('Retain all current V2 structure, stock and flight space')
    terrain=NorthTerrain(home,receipt,registry);before={};retained={}
    try:
        for q,after in d.blocks.items():
            actual=terrain.state(*q)
            if actual is None or q in terrain.entities:raise UserError('Every new target must be FULL and cannot be ANY current BE')
            wanted=d.original.get(q,AIR)
            if key(actual)!=key(wanted) or any(properties(actual).get(k)!=v for k,v in properties(wanted).items()):raise UserError('Preserve changed current block/player progress: '+str((q,wanted,actual)))
            before[q]=actual
        for row in d.supports:
            q=tuple(row['backing'])
            if q in d.blocks:continue
            actual=terrain.state(*q);expected=d.original.get(q,AIR)
            if actual is None or key(actual)!=key(expected) or any(properties(actual).get(k)!=v for k,v in properties(expected).items()):raise UserError('Actual retained structural support changed')
            retained[q]=actual
        sources=terrain.snapshot.sources
    finally:terrain.close()
    merged={**d.original,**d.blocks}
    docs={'delta-PROPOSAL.json':native_payload(registry,d.blocks,checkpoint_sha,'W3 PHOTO-LED — Cooper oriel/gable and Wick task lighting/contained plants'),
          'before-VERIFY-ONLY.json':native_payload(registry,before,checkpoint_sha,'VERIFY ONLY — actual post-W3 sparse relief/light preimage'),
          'retained-supports-VERIFY-ONLY.json':native_payload(registry,retained,checkpoint_sha,'VERIFY ONLY — current retained real wall/floor support'),
          'full-after-VERIFY-ONLY.json':native_payload(registry,merged,checkpoint_sha,'VERIFY ONLY — complete W3 with photo-led relief/light layer',tags={tuple(r['pos']):r['nbt'] for r in plan['block_entities']}),
          'normal-joins-SETTLE-ONLY.json':native_payload(registry,{q:s for q,s in d.blocks.items() if key(s)!=AIR},checkpoint_sha,'NORMAL JOIN ONLY — sparse actual neighbor settle, no inventory replay')}
    for name,doc in docs.items():
        if name!='delta-PROPOSAL.json':doc.update(verification_only=True,construction_forbidden=True)
    raw={n:(json.dumps(v,separators=(',',':'))+'\n').encode() for n,v in docs.items()}
    manifest={'format':'awft-w3-photo-led-refinement:1','checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'source_sha256':digest(Path(__file__)),
        'prior_placed_native_plan':BASE,'prior_exact_native_strict_proof':BASE_PROOF,'actual_native_images':IMAGES,'checks':checks,
        'details':[{'position':list(q),'before':before[q],'after':s,'reason':d.reasons[q]} for q,s in sorted(d.blocks.items())],
        'supports':d.supports,'saved_sources':sources,'reserve_guard':reserve,'reader_budget':memory,
        'files':{n:{'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)} for n,b in raw.items()},
        'camera_proposals':[{'feet':[1070.5,64,-1260.5],'look_at':[1076.5,67,-1263],'purpose':'open two-wide lane, outside glazing model'},
            {'feet':[1083.5,64,-1254.5],'look_at':[1081.5,68,-1262],'purpose':'barrow-free walking shoulder facing the taller side entry'},
            {'feet':[1075.5,65,-1266.5],'look_at':[1073.5,66,-1270],'purpose':'real Wick task lights/work counter'},
            {'feet':[1083.5,64,-1274.5],'look_at':[1085,75,-1271],'purpose':'new North oriel/gable; actual outside dry feet must be checked before posing'}],
        'native_actions':0,'world_writes':0,'inventory_replayed':False,'wider_replication_held_until_actual_visual_review':True}
    raw['manifest.json']=(json.dumps(manifest,separators=(',',':'))+'\n').encode()
    if sum(map(len,raw.values()))>8*MIB:raise UserError('Small refinement output allocation exceeded')
    out=home/'staging'/('west3-photo-refine-'+str(time.time_ns()));out.mkdir()
    for n,b in raw.items():(out/n).open('xb').write(b)
    return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'targets':len(d.blocks),'files':manifest['files'],'native_actions':0}


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--home',type=Path,required=True);a.add_argument('--checkpoint-id',required=True);a.add_argument('--checkpoint-sha',required=True);args=a.parse_args()
    print(json.dumps(prepare(args.home,args.checkpoint_id,args.checkpoint_sha),indent=2))
