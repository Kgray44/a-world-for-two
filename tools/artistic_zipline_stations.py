"""Original compact rigging pavilions. Source plans only, not a qualified ride."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from control_room.common import UserError,digest,read_json,utcnow
from tools.artistic_materials import require_material_rule
from tools.artistic_spawn_plaza import AIR,key,state,payload
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld

GEOGRAPHY='zipline-saved-geography-1793142410871093200/proposal.json'
GEOGRAPHY_SHA='92fd4d395052f3549b10c7589a7630b5f1696bc9d38eee7c4c2cbe447e369ce1'


def station(registry,site,label):
    cx,cz=site['center_xz'];floor=site['proposed_floor_y'];blocks={};roles={}
    bounds=[cx-1,cz-2,cx+1,cz+2]
    if site['bounds']!=bounds:raise UserError('Only the actual saved compact3x5 dry footprint is admitted')
    def put(dx,dy,dz,name,**props):
        pos=cx+dx,floor+dy,cz+dz
        if not(bounds[0]<=pos[0]<=bounds[2] and bounds[1]<=pos[2]<=bounds[3] and -3<=dy<=11):
            raise UserError('Compact station escaped its exact saved footprint')
        blocks[pos]=state(registry,name,**props)
    for dx in (-1,0,1):
        for dz in range(-2,3):
            for dy in range(12):put(dx,dy,dz,AIR)
            put(dx,0,dz,'minecraft:spruce_planks')
            put(dx,4,dz,'minecraft:dark_oak_planks')
    put(0,0,2,'minecraft:spruce_stairs',facing='north',half='bottom',shape='straight',waterlogged=False)
    # Footings stop ABOVE the exact retained natural support; no terrain paste.
    supports={(r['support'][0],r['support'][2]):r['support'][1]
              for r in site['exact_saved_support_and_clearance']}
    for dx in (-1,1):
        for dz in (-2,2):
            ground=supports[cx+dx,cz+dz]
            if not floor-3<=ground<floor:raise UserError('A modest rooted station footing is required')
            for y in range(ground+1,floor):put(dx,y-floor,dz,'minecraft:stone_bricks' if y%2 else 'minecraft:andesite')
            for dy in range(1,8):
                put(dx,dy,dz,'chipped:carved_stripped_spruce_log' if dy==4 else 'minecraft:stripped_spruce_log',axis='y')
            put(dx,8,dz,'minecraft:dark_oak_stairs',facing='east' if dx==-1 else 'west',half='top',shape='straight',waterlogged=False)
    # The4m internal service ladder is backed by a real carved upright. The
    # boarding floor has one explicit side hatch, outside the central flight.
    for dy in (1,2,3):put(0,dy,0,'chipped:reinforced_stripped_spruce_log',axis='y')
    for dy in range(1,5):put(1,dy,0,'minecraft:ladder',facing='east',waterlogged=False)
    put(1,5,0,'minecraft:spruce_trapdoor',facing='east',half='bottom',open=True,powered=False,waterlogged=False)
    for dx in (-1,1):
        for dz in (-1,1):
            put(dx,5,dz,'minecraft:spruce_fence',north=dz==-1,south=dz==1,east=False,west=False,waterlogged=False)
    # Modeled shelf/books, louvered service casement, equipment locker and cup.
    put(-1,1,0,'handcrafted:dark_oak_shelf',facing='west',shape='single',type='2')
    put(-1,2,0,'handcrafted:stackable_book',facing='west',books=2,seed=7)
    put(-1,3,0,'mcwwindows:dark_oak_louvered_shutter',facing='west',hinge='left',open=True)
    put(1,1,-1,'minecraft:barrel',facing='south',open=False)
    put(1,2,-1,'handcrafted:wood_cup',facing='south',pieces=1,waterlogged=False)
    # Actual underside coffers, knee braces and a shallow pitched roof.
    for dz in (-1,1):
        put(0,3,dz,'minecraft:dark_oak_trapdoor',facing='north',half='top',open=False,powered=False,waterlogged=False)
        for dx in (-1,1):
            put(dx,3,dz,'minecraft:spruce_stairs',facing='east' if dx==-1 else 'west',half='top',shape='straight',waterlogged=False)
            put(dx,8,dz,'minecraft:dark_oak_stairs',facing='east' if dx==-1 else 'west',half='top',shape='straight',waterlogged=False)
    for dz in (-2,0,2):
        for dx in (-1,0,1):put(dx,9,dz,'minecraft:stripped_dark_oak_log',axis='x')
    for dx in (-1,1):
        for dz in range(-2,3):put(dx,9,dz,'minecraft:stripped_dark_oak_log',axis='z')
    for dz in range(-2,3):
        put(-1,10,dz,'minecraft:dark_oak_stairs',facing='east',half='bottom',shape='straight',waterlogged=False)
        put(1,10,dz,'minecraft:dark_oak_stairs',facing='west',half='bottom',shape='straight',waterlogged=False)
        put(0,11,dz,'minecraft:dark_oak_slab',type='bottom',waterlogged=False)
    put(-1,7,-1,'mcwlights:tavern_wall_lantern',facing='south')
    put(1,7,1,'mcwlights:covered_wall_lantern',facing='north')
    # This real tag-compatible fence is bolted below the full gantry beam. No
    # entity or fictional line is created by the architecture producer.
    put(0,8,0,'minecraft:spruce_fence',north=False,south=False,east=False,west=False,waterlogged=False)
    roles.update(anchor_block=[cx,floor+8,cz],boarding_floor_y=floor+4,
        ladder=[[cx+1,floor+dy,cz]for dy in range(1,5)],
        locker=[cx+1,floor+1,cz-1],native_stock='EMPTY until normal inventory stock is separately verified',
        lower_approach_required=[cx,floor+1,cz+2],entry_stair=[cx,floor,cz+2],
        exterior_arrival_feet=[cx+.5,floor,cz+3.5],anchor_face='north',hang_offset_required=3.0)
    validate(blocks,roles,label)
    return blocks,roles


def validate(blocks,roles,label):
    x,y,z=roles['anchor_block'];floor=y-8
    if key(blocks[x,y,z])!='minecraft:spruce_fence' or key(blocks[x,y+1,z])!='minecraft:stripped_dark_oak_log':
        raise UserError('A real supported #fences anchor is required')
    for zz in range(z-2,z+3):
        for yy in range(floor+5,floor+8):
            if blocks[x,yy,zz]!=AIR:raise UserError('Preserve the central hanging-player body corridor')
    for p in roles['ladder']:
        if key(blocks[tuple(p)])!='minecraft:ladder' or 'facing=east' not in blocks[tuple(p)]:raise UserError('Preserve the real side ladder')
        if blocks.get((p[0]-1,p[1],p[2]),AIR)==AIR:raise UserError('A real side ladder needs its retained solid backing')
    top=roles['ladder'][-1];hatch=blocks.get((top[0],top[1]+1,top[2]),AIR)
    if key(hatch)!='minecraft:spruce_trapdoor' or 'facing=east'not in hatch or 'open=true'not in hatch:
        raise UserError('The open ladder hatch must face the same way as the native ladder')
    return require_material_rule(blocks,'Complete '+label+' pavilion including footings/roof/interior')


def admit_saved_target(pos,actual,protected):
    if pos in protected or not(actual==AIR or key(actual)in{'minecraft:short_grass','minecraft:tall_grass','minecraft:snow','regions_unexplored:grass_sprouts'}):
        raise UserError('Preserve a saved BE/tree/object at station target: '+str((pos,actual)))


def prepare(home,registry_path,backup_id,backup_sha,output,launch_index=0):
    home,output=Path(home).resolve(),Path(output).resolve()
    if output.exists()or not output.is_relative_to(home/'staging'):raise UserError('A NEW owned station proposal directory is required')
    reserve=guard(4*1024**2,8*1024**2);registry=read_json(registry_path)
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    if receipt.get('verified')is not True or (receipt.get('id'),receipt.get('sha256'))!=(backup_id,backup_sha):raise UserError('Current exact retained checkpoint required')
    geography=home/'staging'/GEOGRAPHY
    if digest(geography)!=GEOGRAPHY_SHA:raise UserError('Actual dry footprint geography differs')
    geo=read_json(geography)
    if launch_index not in (0,1):raise UserError('Choose one of the2 qualified cliff-facing endpoint plots')
    sites={'cliff':geo['launch_candidates_highest_qualified_footprint_first'][launch_index],
           'town':geo['town_dry_landing_candidates'][2]}
    snapshot=BackupWorld(home,receipt,registry);docs={};details={};mask={}
    try:
        for label,site in sites.items():
            blocks,roles=station(registry,site,label);before={}
            # Retained roots are verification targets, never construction fill.
            for saved in site['exact_saved_support_and_clearance']:
                pos=tuple(saved['support']);actual=snapshot.state(pos)
                if actual!=saved['support_state'] or pos in snapshot.protected:
                    raise UserError('Retain the exact saved natural station support: '+str(pos))
                before[pos]=actual
            for pos in blocks:
                actual=snapshot.state(pos);before[pos]=actual
                admit_saved_target(pos,actual,snapshot.protected)
            docs[label+'-station.json']=payload(registry,backup_sha,blocks,'PROPOSAL ONLY original compact '+label+' zipline pavilion')
            docs[label+'-station.json']['construction_forbidden']=True
            docs[label+'-before.json']=payload(registry,backup_sha,before,'VERIFY ONLY actual saved '+label+' station preimage',before=True)
            details[label]={'roles':roles,'source_material_check':validate(blocks,roles,label),'targets':len(blocks),
                'external_access':'UNPROVED: author and verify actual approach connection before use',
                'native_climb_boarding_collision_and_art':'PENDING',
                'anchor_entity_UUIDs':[],'line_entities_created':0}
            mask.update({pos:AIR for pos in blocks})
            cx,cz=site['center_xz'];floor=site['proposed_floor_y']
            mask.update({(cx+dx,floor+dy,cz+3):AIR for dx in (-1,0,1)for dy in (0,1,2)})
        sources=snapshot.sources[:]
    finally:snapshot.close()
    docs['station-reservation-ONLY.json']=payload(registry,backup_sha,mask,'RESERVATION ONLY both detailed station solids/AIR/routes',before=True)
    raw={name:(json.dumps(doc,separators=(',',':'))+'\n').encode()for name,doc in docs.items()}
    manifest={'format':'awft-zipline-station-proposal:1','created':utcnow(),'source_sha256':digest(Path(__file__)),
        'checkpoint_id':backup_id,'checkpoint_sha256':backup_sha,'geography_sha256':GEOGRAPHY_SHA,
        'details':details,'native_actions':0,'world_writes':0,'existing_trees_removed':0,
        'route_status':'UNPLACED; no continuous route or walkable cliff access qualified',
        'sources':sources,'reserve_guard':reserve,'files':{n:{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}for n,b in raw.items()}}
    raw['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    if sum(map(len,raw.values()))>4*1024**2:raise UserError('Finite station output exceeded')
    output.mkdir()
    for name,data in raw.items():(output/name).write_bytes(data)
    return {'output':str(output),'manifest_sha256':digest(output/'manifest.json'),'details':details}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('home','registry','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--backup-id',required=True);p.add_argument('--backup-sha256',required=True);p.add_argument('--launch-index',type=int,default=0)
    a=p.parse_args();print(json.dumps(prepare(a.home,a.registry,a.backup_id,a.backup_sha256,a.output,a.launch_index),indent=2))
