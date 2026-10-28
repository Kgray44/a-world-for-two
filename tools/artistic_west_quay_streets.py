"""The crooked, human-scale public spine around the five placed quay shops.

Original modeled street furniture, exact dry paving and unchanged three-wide
walking body. Architecture only; plants/residents are separate later LIFE work.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path

from control_room.common import UserError,digest,utcnow
from tools.artistic_bridge_refinement import flatten
from tools.artistic_materials import require_material_rule,require_outdoor_rule
from tools.artistic_north_bank_east import NorthTerrain
from tools.artistic_north_bank_west import ZIPLINE_MASK,ZIPLINE_MASK_SHA
from tools.artistic_quay_prototype import WEST,WEST_SHA,KINDS,bounded,context,member,write_bundle
from tools.artistic_spawn_plaza import payload,state
from tools.playtest import guard
from tools.settlement_attractions import base,properties
from tools.artistic_pirate_spit import tag_snbt

MIB=1024**2
LANE='staging/north-bank-west-public-lane-1793153722392224900/public-lane.json'
LANE_SHA='ba79685fe7835d30d086e451485cc1f08702f50131dddb13ee0a14334ebf17e4'
SOFT={'minecraft:air','minecraft:cave_air','minecraft:void_air','minecraft:short_grass','minecraft:tall_grass',
      'regions_unexplored:grass_sprouts','supplementaries:barnacles'}
FACES={'north':(0,-1),'east':(1,0),'south':(0,1),'west':(-1,0)}
SMITH_OLD='minecraft:brick_wall[east=none,north=none,south=none,up=true,waterlogged=false,west=none]'
SMITH_NATIVE={
    (1048,y,-1267):'minecraft:brick_wall[east=none,north=tall,south=none,up=true,waterlogged=false,west=none]' for y in range(68,72)
}
SMITH_NATIVE[1048,72,-1267]='minecraft:brick_wall[east=low,north=low,south=none,up=true,waterlogged=false,west=none]'


def current_house_expectation(q,original):
    if q in SMITH_NATIVE:
        if original!=SMITH_OLD:raise UserError('Reviewed original smith chimney preimage changed')
        return SMITH_NATIVE[q]
    return original


def paving(x,z):
    # Three-by-three dressed cobbles and narrow crossed joints, with a polished
    # boss where joints meet. Every material is deliberately interrupted, not a
    # long border strip or random checker of unrelated colored stone.
    a,b=x%4==0,z%4==0
    return 'minecraft:polished_andesite'if a and b else'minecraft:andesite'if a or b else'chipped:small_stone_bricks'


class Furniture:
    def __init__(self,r):self.r=r;self.blocks={};self.parts={};self.tags=[];self.scene=None;self.features=[]
    def put(self,x,y,z,name,**props):
        q=x,y,z;value=state(self.r,name,**props)
        if q in self.blocks and self.blocks[q]!=value:raise UserError('Two authored street details overlap: '+str(q))
        self.blocks[q]=value;self.parts.setdefault(self.scene,{})[q]=value
    def post(self,x,z,*,wood='dark_oak',face='south'):
        for y in range(64,67):self.put(x,y,z,'minecraft:stripped_'+wood+'_log',axis='y')
        self.put(x,67,z,'mythrais:curved_corbel_dark_oak',facing=face,shape=0)
    def canopy(self,x,z,*,copper=False):
        for dx in range(3):
            for dz in range(3):
                self.put(x+dx,68,z+dz,'minecraft:waxed_oxidized_cut_copper_slab'if copper else'minecraft:dark_oak_slab',type='bottom',waterlogged=False)
        self.put(x+1,67,z+1,'minecraft:lantern',hanging=True,waterlogged=False)
    def bench(self,x,z,face):
        self.put(x,64,z,'handcrafted:dark_oak_bench',facing=face,shape='single',color='none',waterlogged=False)
    def planter(self,x,z):self.put(x,64,z,'supplementaries:planter',extended=False,waterlogged=False)
    def barrel(self,x,z,label):
        self.put(x,64,z,'minecraft:barrel',facing='up',open=False)
        self.tags.append({'pos':[x,64,z],'nbt':tag_snbt({'id':'minecraft:barrel','Items':[],'CustomName':json.dumps({'text':label},ensure_ascii=False,separators=(',',':'))})})


def furniture(r):
    p=Furniture(r)
    p.scene='Keelwright weather porch'
    p.post(1025,-1273,wood='oak');p.post(1027,-1273,wood='oak');p.canopy(1025,-1273,copper=True)
    p.put(1026,64,-1272,'minecraft:cartography_table');p.put(1026,65,-1272,'handcrafted:terracotta_bowl',facing='south',pieces=3,waterlogged=False)
    p.barrel(1027,-1272,'Wren’s Keel — empty street workbox');p.planter(1025,-1271)
    p.features.append('A sheltered actual chart-work counter, carved pole shoulders, aged-copper roof and a warm suspended lamp; empty new workbox.')
    p.scene='Rivet rest and tool plinth'
    p.bench(1043,-1254,'north');p.planter(1042,-1254)
    p.put(1045,64,-1254,'minecraft:polished_andesite');p.put(1045,65,-1254,'minecraft:anvil',facing='north')
    p.post(1045,-1253,face='west');p.put(1044,67,-1253,'minecraft:dark_oak_slab',type='bottom',waterlogged=False)
    p.put(1044,66,-1253,'minecraft:lantern',hanging=True,waterlogged=False)
    p.features.append('A single usable street bench with an empty planting urn, real anvil display and short cantilevered tool-lane lamp.')
    p.scene='Black Gull fitting rail'
    p.post(1038,-1250);p.put(1038,68,-1250,'minecraft:waxed_oxidized_cut_copper_slab',type='bottom',waterlogged=False)
    p.put(1038,64,-1251,'minecraft:grindstone',face='floor',facing='south')
    p.barrel(1039,-1250,'Black Gull — empty fitting supplies');p.planter(1037,-1250)
    p.features.append('A modeled timber fitting rail and real grindstone stand beside the armoury, with an empty repair barrel and planter.')
    p.scene='Lantern Wake exterior snug'
    p.post(1065,-1260);p.post(1067,-1260);p.canopy(1065,-1260)
    p.bench(1065,-1258,'east');p.bench(1067,-1258,'west')
    p.put(1066,64,-1258,'handcrafted:dark_oak_table',shape='single',color='none',waterlogged=False)
    p.put(1066,65,-1258,'handcrafted:terracotta_bowl',facing='north',pieces=2,waterlogged=False)
    p.features.append('A tiny real paired-seat tavern snug under carved, lit eaves; three-wide public passage stays outside it.')
    p.scene='Marigold pottery barrow'
    for x in (1080,1082):p.planter(x,-1255)
    p.put(1081,64,-1255,'handcrafted:oak_table',shape='single',color='none',waterlogged=False)
    p.put(1081,65,-1255,'handcrafted:terracotta_bowl',facing='south',pieces=6,waterlogged=False)
    p.post(1079,-1255,wood='oak',face='east');p.put(1080,67,-1255,'minecraft:dark_oak_slab',type='bottom',waterlogged=False)
    p.put(1080,66,-1255,'minecraft:lantern',hanging=True,waterlogged=False)
    p.features.append('A low asymmetrical florist pottery display and empty planted-urn locations, ready for the separately governed botanical LIFE pass.')
    p.scene='West landing wayfarer nook'
    p.bench(1094,-1248,'north');p.planter(1095,-1248)
    p.post(1093,-1248,wood='oak',face='east');p.put(1094,67,-1248,'minecraft:dark_oak_slab',type='bottom',waterlogged=False)
    p.put(1094,66,-1248,'minecraft:lantern',hanging=True,waterlogged=False)
    p.features.append('A compact carved arrival seat and warm bracket light that leave the real future zipline threshold and cable body untouched.')
    for label,blocks in p.parts.items():require_material_rule(blocks,'COMPLETE original public '+label)
    require_outdoor_rule(p.blocks,'Complete modeled west street furniture')
    return p


def prepare(home,output):
    reserve=guard(4*MIB,16*MIB);home,output,current,registry=context(home,output)
    lane=bounded(home/LANE)
    if digest(home/LANE)!=LANE_SHA or lane['width']!=3 or len(lane['exact_support_body'])!=324:raise UserError('Exact actual dry eleven-branch public spine required')
    source=bounded(home/WEST/'manifest.json')
    if digest(home/WEST/'manifest.json')!=WEST_SHA:raise UserError('Preserve exact five source shops')
    houses={}
    for kind in KINDS:houses.update(flatten(member(home/WEST,source,kind+'-PROPOSAL.json')))
    zp=home/ZIPLINE_MASK
    if digest(zp)!=ZIPLINE_MASK_SHA:raise UserError('Exact prospective western cable/station body mask required')
    zipline=set(flatten(bounded(zp)));p=furniture(registry)
    terrain=NorthTerrain(home,current,registry);delta={};before={};retained={};walk={};supports={}
    try:
        for row in lane['exact_support_body']:
            x,y,z=row['support'];q=x,y,z;actual=terrain.state(*q)
            if actual!=row['state'] or actual!='minecraft:gravel' or q in terrain.entities:raise UserError('Retain exact measured dry public support: '+str(q))
            supports[x,z]=y;delta[q]=state(registry,paving(x,z));before[q]=actual
            for yy in range(y+1,67):
                q=x,yy,z;actual=terrain.state(*q)
                if actual is None or base(actual)not in SOFT or 'waterlogged=true'in actual or q in terrain.entities:raise UserError('Actual public body/ordinary-cover field differs: '+str((q,actual)))
                if q in houses or q in zipline:raise UserError('Keep complete placed house/zipline ownership out of public pavement/body')
                before[q]=actual;delta[q]='minecraft:air';walk[q]='minecraft:air'
        for(x,z),y in supports.items():
            if y==62:
                directions=[face for face,(dx,dz)in FACES.items()if supports.get((x+dx,z+dz))==63]
                if not directions:raise UserError('Exact half-step must face an existing higher dry paved neighbor')
                q=x,63,z;delta[q]=state(registry,'minecraft:stone_brick_stairs',facing=directions[0],half='bottom',shape='straight',waterlogged=False);walk.pop(q,None)
        for q,value in p.blocks.items():
            x,y,z=q
            if q in houses or q in zipline or(q in walk and base(value)!='minecraft:air'):raise UserError('Furniture blocks the declared public walk, original shop or future cable body: '+str(q))
            actual=terrain.state(*q)
            if actual is None or base(actual)not in SOFT or 'waterlogged=true'in actual or q in terrain.entities:raise UserError('Retain actual tree/object/BE outside public furnishing: '+str((q,actual)))
            if q in delta:raise UserError('Street furniture/paving overlap: '+str(q))
            before[q]=actual;delta[q]=value
        for x,z in {(q[0],q[2])for q in p.blocks}:
            q=x,63,z;actual=terrain.state(*q)
            if actual!='minecraft:gravel' or q in terrain.entities:raise UserError('Every small public furnishing must have exact rooted dry gravel63: '+str((q,actual)))
            retained[q]=actual
        # All accepted complete shop source fields are verified unchanged as
        # part of the after proof; no old tag or inventory is loaded again.
        for q,expected in houses.copy().items():
            expected=current_house_expectation(q,expected)
            actual=terrain.state(*q)
            if base(actual)!=base(expected)or any(properties(actual).get(k)!=v for k,v in properties(expected).items()):
                raise UserError('Placed shop native identity/supplied property differs from accepted full geometry: '+str(q))
            # Original optional/default properties were omitted by the already
            # native-verified house source. Expand ALL of them from the real
            # current save into both BEFORE and AFTER: no critical state is
            # ignored and no verifier is weakened to handle normal defaults.
            houses[q]=actual;retained[q]=actual
        sources=terrain.snapshot.sources.copy()
    finally:terrain.close()
    require_outdoor_rule(delta,'Whole short-jointed crooked public street and original modeled furniture')
    body_before=dict(before);body_before.update(retained)
    complete=dict(houses);complete.update(delta);complete.update(retained)
    docs={'before-VERIFY-ONLY.json':payload(registry,current['sha256'],body_before,'VERIFY ONLY current public dry paving, ordinary body cover and six furnishing sites',before=True),
          'street-and-furniture-PROPOSAL.json':payload(registry,current['sha256'],delta,'PROPOSAL ONLY eleven-branch crooked west street and six modeled human-scale furnishings'),
          'complete-after-VERIFY-ONLY.json':payload(registry,current['sha256'],complete,'VERIFY ONLY complete five placed shops, public paving/body, native empty workboxes and retained furnishing roots',before=True),
          'future-walk-furniture-reservation-ONLY.json':payload(registry,current['sha256'],{q:'minecraft:air'for q in set(delta)|set(walk)|set(retained)},'RESERVATION ONLY future crooked public street and furniture, never observedAIR',before=True)}
    docs['street-and-furniture-PROPOSAL.json'].update(construction_forbidden=True,block_entities=p.tags)
    docs['complete-after-VERIFY-ONLY.json']['block_entities']=p.tags
    if bounded(home/'dashboard/settlement/backup-receipt.json').get('sha256')!=current['sha256']:raise UserError('Checkpoint advanced during current street preimage read')
    return write_bundle(output,docs,{'format':'awft-modeled-west-public-street:1','created':utcnow(),'source_sha256':digest(Path(__file__)),
        'checkpoint_id':current['id'],'checkpoint_sha256':current['sha256'],'measured_lane_sha256':LANE_SHA,'house_source_sha256':WEST_SHA,'future_zipline_mask_sha256':ZIPLINE_MASK_SHA,
        'paved_support_columns':len(supports),'retained_grade_counts':dict(Counter(supports.values())),'public_walk_body_width':3,'tiny_half_steps':2,
        'scene_features':p.features,'scene_targets':{k:len(v)for k,v in p.parts.items()},'new_empty_owned_barrels':len(p.tags),'source_only':True,
        'native_derived_prior_smith_wall_connections':[{'position':list(q),'old_source':SMITH_OLD,'actual_saved_expected':v,'scope':'Actual3c15d0 normal native joins; no placement/replay or broad verifier relaxation'}for q,v in SMITH_NATIVE.items()],
        'new_entities_or_plant_LIFE':0,'placed_shop_or_route_changes':0,'saved_sources':sources,'storage_guard':reserve,'construction_forbidden':True,'native_actions':0,'world_writes':0,
        'next_gate':'Actual current native BEFORE, parent admit exact once, native normal joins and strict complete states/inventories; actual low corner/stair/window/eye-level street and night/usable furniture review. This connects five prototypes, not a claim that the entire north-bank expansion is complete.'})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('home','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.home,a.output),indent=2))
