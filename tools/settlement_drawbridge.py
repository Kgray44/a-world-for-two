"""A real two-leaf, water-powered Create bascule bridge across the surveyed river.

The physical build, glue/program setup, native control cycle, ship clearance and
restart checks are separate operations. No animation or speed is fabricated here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

from control_room.common import Layout, UserError, atomic_write, digest, read_json, write_json, utcnow
from control_room.storage import Storage
from tools.settlement import Plan
from tools.settlement_port import PortPlan


FREQUENCY = ('minecraft:compass', 'minecraft:iron_nugget')
X_OFFSET = -7  # The surveyed lane between the finished chandlery and tavern annex.
DEFAULT_OPEN_ANGLE = 55
PHYSICAL_SHA = 'cc2bd89a14d86fc1de2236e5a4f92ca523d911bc128fcf96f91c1e6101fb8b69'
ENGINEERING_OUTPUT_BOUND = 2*1024**2


def open_angle(value):
    """Create's native TURN_ANGLE value is an integer; the owner chose 45–60°."""
    if type(value) is not int or not 45 <= value <= 60:
        raise UserError('Choose an integer opening angle from 45 to 60 degrees')
    return value


def placed_systems(angle=DEFAULT_OPEN_ANGLE):
    angle = open_angle(angle)
    return [
        {'name':'North bascule leaf','bearing':[1199,70,-1172],
         'sequencer':[1203,70,-1172],'wheel':[1225,68,-1172],
         'glue_min':[1187,69,-1172],'glue_max':[1198,73,-1144],
         'open_negative':True,'open_angle_degrees':angle,'expected_open_angle':-angle},
        {'name':'South bascule leaf','bearing':[1199,70,-1116],
         'sequencer':[1203,70,-1116],'wheel':[1225,68,-1116],
         'glue_min':[1187,69,-1143],'glue_max':[1198,73,-1116],
         'open_negative':False,'open_angle_degrees':angle,'expected_open_angle':angle},
    ]


def placed_radios():
    return [{'position':list(position),'first':FREQUENCY[0],'last':FREQUENCY[1]}
            for position in ((1183,72,-1178),(1183,72,-1110),(1203,71,-1172),(1203,71,-1116))]


def clearance_estimate(angle=DEFAULT_OPEN_ANGLE):
    angle = open_angle(angle)
    radians = math.radians(angle)
    return {'angle_degrees':angle,'pivot_separation_blocks':56,
            'north_far_block_center_radius':28,'south_far_block_center_radius':27,
            'nominal_north_far_center_y':round(70.5+28*math.sin(radians),4),
            'nominal_south_far_center_y':round(70.5+27*math.sin(radians),4),
            'nominal_centerline_gap_blocks':round(56-55*math.cos(radians),4),
            'nominal_deck_outer_edge_gap_blocks':round(56-56*math.cos(radians),4),
            'scope':'Ideal zero-thickness deck geometry only; excludes thickness, trusses, native '
                    'contraption/model bounds, collision margins, water level and vessel rigging',
            'ship_clearance':'Unverified; partial opening does not establish safe passage for a vessel'}


def engineering_configuration(registry,backup,proof,physical,angle=DEFAULT_OPEN_ANGLE):
    """Pure settings for the exact placed bridge; no deck placement or file writes."""
    angle=open_angle(angle)
    if not backup.get('verified') or not re.fullmatch('[a-f0-9]{64}',backup.get('sha256','')):
        raise UserError('A current verified complete-world backup receipt is required')
    if (proof.get('operation')!='verify' or proof.get('plan_sha256')!=PHYSICAL_SHA
            or proof.get('failures')!=0 or not proof.get('finished')):
        raise UserError('The exact placed physical bridge must retain its successful native verification')
    if (physical.get('seed')!=registry.get('seed')
            or physical.get('world_path')!=registry.get('world_path')):
        raise UserError('The physical bridge and registry belong to different permanent worlds')
    blocks={(x,y,z):physical['palette'][i] for x,y,z,i in physical['blocks']}
    systems=placed_systems(angle)
    expected=[]
    for system in systems:
        expected.extend((system[key],block) for key,block in (
            ('bearing','create:mechanical_bearing'),('sequencer','create:sequenced_gearshift'),
            ('wheel','create:water_wheel')))
        low,high=system['glue_min'],system['glue_max']
        for x in range(low[0],high[0]+1):
            for z in range(low[2],high[2]+1):
                expected.append(([x,70,z],'minecraft:stripped_dark_oak_log'
                                 if z==system['bearing'][2] else 'minecraft:dark_oak_planks'))
    buttons=[[1182,73,-1178],[1182,73,-1110]]
    expected.extend((position,'minecraft:stone_button') for position in buttons)
    radios=placed_radios()
    expected.extend((row['position'],'create:redstone_link') for row in radios)
    for position,block in expected:
        if blocks.get(tuple(position),'').split('[')[0]!=block:
            raise UserError('The declared engineering components differ from the exact physical bridge: '+str(position))
    for item in FREQUENCY:
        if item not in registry['items']:
            raise UserError('The existing bridge radio frequency is not in the native item registry')
    return {'format':'awft-native-engineering:1','created':utcnow(),
            'seed':registry['seed'],'world_path':registry['world_path'],
            'backup_sha256':backup['sha256'],'construction_sha256':PHYSICAL_SHA,
            'open_angle_degrees':angle,'systems':systems,'buttons':buttons,'radios':radios,
            'clearance_estimate':clearance_estimate(angle)}


def prepare_engineering(home,angle=DEFAULT_OPEN_ANGLE,destination=None):
    """Write a unique engineering-only plan, preserving every current generic file.

    The parent may admit this exact file as engineering-plan.json after reviewing
    it. This function never programs a sequencer, rebuilds a leaf, issues a native
    command, or replaces physical plans, verification, backup or failed receipts.
    """
    layout=Layout(Path(home));angle=open_angle(angle)
    directory=layout.state/'settlement'
    target=directory.resolve() if destination is None else Path(destination).resolve()
    if not target.is_relative_to(directory.resolve()) or target.suffix:
        raise UserError('Choose an owned settlement directory for the engineering-only artifacts')
    master=directory/('drawbridge-master-'+PHYSICAL_SHA+'.json')
    if not master.is_file() or digest(master)!=PHYSICAL_SHA:
        raise UserError('The exact immutable placed drawbridge master is required; do not regenerate the deck')
    registry_path=directory/'registry.json';backup_path=directory/'backup-receipt.json'
    proof_path=directory/'drawbridge-block-verification.json'
    registry=read_json(registry_path,{})
    backup=read_json(backup_path,{})
    proof=read_json(proof_path,{})
    physical=read_json(master)
    data=engineering_configuration(registry,backup,proof,physical,angle)
    raw=(json.dumps(data,indent=2,ensure_ascii=False)+'\n').encode('utf-8')
    if len(raw)>256*1024:
        raise UserError('The engineering-only plan exceeds native admission limits')
    sha=hashlib.sha256(raw).hexdigest()
    path=target/('drawbridge-engineering-'+str(angle)+'-'+sha+'.json')
    manifest_path=target/('drawbridge-engineering-'+str(angle)+'-'+sha+'-manifest.json')
    manifest={'format':'awft-drawbridge-engineering-only:1','at':data['created'],
              'plan_file':path.name,'plan_sha256':sha,'open_angle_degrees':angle,
              'construction_sha256':PHYSICAL_SHA,'physical_plan_placements':len(physical['blocks']),
              'new_physical_placements':0,'backup_id':backup.get('id'),
              'backup_sha256':backup['sha256'],
              'physical_verification_file_sha256':digest(proof_path),
              'physical_verification_finished':proof['finished'],
              'sources':{p.name:digest(p) for p in (master,registry_path,backup_path,proof_path)},
              'targets':[{'name':s['name'],'open_angle':s['expected_open_angle'],'closed_angle':0}
                         for s in data['systems']],
              'native_program_intent':['TURN_ANGLE '+str(angle)+' in each declared opening direction',
                                       'AWAIT a new physical bank-button signal',
                                       'TURN_ANGLE '+str(angle)+' in the opposed closing direction','END'],
              'clearance_estimate':data['clearance_estimate'],
              'status':'Prepared only; no physical blocks placed and no native program changed',
              'current_pose':'Not inferred from the historical physical-block receipt',
              'required_sequence':['Safely close any currently open old-program leaf using native recovery',
                                   'Confirm actual zero angle and disassembled/replaced deck',
                                   'Configure the new plan through native setup',
                                   'Commission both bank buttons through two complete cycles',
                                   'Reverify the closed deck and restart persistence'],
              'acceptance_pending':['Actual signed 55-degree targets' if angle==55 else 'Actual signed target angles',
                                    'Await/button race resolution','Closed physical verification',
                                    'Restart persistence','Vessel-specific collision and rigging clearance']}
    metadata=(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n').encode('utf-8')
    if len(raw)+len(metadata)>ENGINEERING_OUTPUT_BOUND:
        raise UserError('Engineering artifacts exceeded their bounded allocation')
    Storage(layout).reserve(ENGINEERING_OUTPUT_BOUND,target=target)
    for output,content in ((path,raw),(manifest_path,metadata)):
        if output.exists():
            if output.read_bytes()!=content:
                raise UserError('Refusing to replace an existing engineering-only artifact')
        else:
            atomic_write(output,content)
    return {'path':str(path),'sha256':sha,'manifest':str(manifest_path),
            'open_angle_degrees':angle,'construction_sha256':PHYSICAL_SHA,
            'new_physical_placements':0,'status':'Prepared only; native recovery/setup/commissioning pending'}


class SurveyedWorldPlan(PortPlan):
    """This template uses surveyed world coordinates, with the same radius checks."""
    def world(self, x, z):
        return x+X_OFFSET, z

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.port_connections={}
        self.adapted=[]

    def put(self,x,y,z,key,**properties):
        wx,wz=self.world(x,z)
        position=wx,y,wz
        old=self.port_connections.get(position)
        # Only explicitly recorded, inventory-free quay decking/support/clearance
        # may become a stone bridge approach. The original settlement remains fixed.
        if old is not None and self.state(key,**properties)!=old:
            allowed=old.split('[')[0] in ('minecraft:air','minecraft:spruce_planks','minecraft:dark_oak_log',
                                         'minecraft:cobblestone','minecraft:gravel')
            if not allowed or position in self.protected:
                raise UserError('Bridge connection would erase a completed furnishing: '+str(position))
            self.adapted.append({'position':list(position),'previous':old})
            self.fixed.pop(position,None)
        return super().put(x,y,z,key,**properties)


def radio(p, x, y, z, receiver, facing='up'):
    p.put(x, y, z, 'create:redstone_link', receiver=receiver, powered=False, facing=facing)
    p.tag(x, y, z, '{Transmitter:'+('0b' if receiver else '1b')+
          ',FrequencyFirst:{id:"'+FREQUENCY[0]+'",count:1},FrequencyLast:{id:"'+FREQUENCY[1]+'",count:1}}')


def leaf(p, pivot, direction, length):
    p.zone = 'Lanternwater Mechanical Drawbridge'
    y=70
    for n in range(length):
        z=pivot+direction*n
        for x in range(1194,1206):
            p.put(x,y,z,'minecraft:dark_oak_planks')
        for x in (1194,1205):
            p.put(x,y+1,z,'minecraft:dark_oak_fence')
            # Alternating triangulated side trusses are attached to each leaf.
            if n%6 in (0,1,5):
                for dy in range(2,4):p.put(x,y+dy,z,'minecraft:stripped_dark_oak_log',axis='y')
            elif n%6==3:
                p.put(x,y+2,z,'minecraft:dark_oak_slab',type='bottom',waterlogged=False)
        if n%6==0:
            for x in range(1195,1205):p.put(x,y-1,z,'minecraft:dark_oak_log',axis='x')
    # Root crossbeam transmits rotation from the side-mounted bearing to the deck.
    p.box(1194,y,pivot,1205,y,pivot,'minecraft:stripped_dark_oak_log',axis='x')


def power_house(p, pivot, negative):
    y=70
    # Native water wheel -> two small/large diagonal reductions -> 2 RPM sequencer.
    # Water is contained by a full-block channel and returned to a solid catch basin.
    p.zone='Lanternwater Mechanical Drawbridge'
    p.box(1230,65,pivot-3,1234,72,pivot+3,'minecraft:stone_bricks')
    p.box(1231,66,pivot-2,1233,71,pivot+2,'minecraft:air')
    p.box(1231,65,pivot-2,1233,65,pivot+2,'minecraft:stone_bricks')
    p.put(1232,68,pivot,'create:water_wheel',facing='west')
    # A falling stream at the rim, rather than water source blocks around a wheel.
    p.put(1232,71,pivot-1,'minecraft:water')
    for x in range(1229,1232):p.put(x,68,pivot,'create:shaft',axis='x',waterlogged=False)
    p.put(1230,68,pivot,'create:andesite_encased_shaft',axis='x')
    p.put(1228,68,pivot,'create:cogwheel',axis='x',waterlogged=False)
    p.put(1228,69,pivot-1,'create:large_cogwheel',axis='x',waterlogged=False)
    for x in range(1223,1228):p.put(x,69,pivot-1,'create:shaft',axis='x',waterlogged=False)
    p.put(1222,69,pivot-1,'create:cogwheel',axis='x',waterlogged=False)
    p.put(1222,70,pivot,'create:large_cogwheel',axis='x',waterlogged=False)
    for x in range(1211,1222):p.put(x,70,pivot,'create:shaft',axis='x',waterlogged=False)
    p.put(1210,70,pivot,'create:sequenced_gearshift',axis='x',vertical=False,state=0)
    for x in (1207,1208,1209):p.put(x,70,pivot,'create:shaft',axis='x',waterlogged=False)
    p.put(1206,70,pivot,'create:mechanical_bearing',facing='west')
    radio(p,1210,71,pivot,True)
    # Exposed gears sit behind a low railing and a covered maintenance walkway.
    for x in range(1221,1236):
        p.put(x,66,pivot-3,'minecraft:spruce_planks')
        p.put(x,67,pivot-4,'minecraft:iron_bars')
    return {'name':('North' if negative else 'South')+' bascule leaf',
            'bearing':[1206,70,pivot], 'sequencer':[1210,70,pivot], 'wheel':[1232,68,pivot],
            'open_negative':negative,
            'glue_min':[1194,69,min(pivot,pivot+(28 if negative else -27))],
            'glue_max':[1205,73,max(pivot,pivot+(28 if negative else -27))]}


def abutment(p, north):
    p.zone='Lanternwater Mechanical Drawbridge'
    start,end=(-1184,-1173) if north else (-1115,-1104)
    for x in range(1194,1207):
        for z in range(start,end+1):
            p.box(x,62,z,x,69,z,'minecraft:stone_bricks')
            p.put(x,70,z,'minecraft:polished_andesite')
            p.box(x,71,z,x,75,z,'minecraft:air')
    for x in (1194,1206):
        for z in range(start,end+1):p.put(x,71,z,'minecraft:stone_brick_wall')
    tower_z=-1180 if north else -1107
    for x in (1189,1211):
        for dx in range(-2,3):
            for dz in range(-3,4):
                shell=abs(dx)==2 or abs(dz)==3
                p.box(x+dx,62,tower_z+dz,x+dx,85,tower_z+dz,
                      'minecraft:stone_bricks' if shell else 'minecraft:air')
                p.put(x+dx,70,tower_z+dz,'minecraft:stone_bricks')
                p.put(x+dx,80,tower_z+dz,'minecraft:dark_oak_planks')
                p.put(x+dx,86,tower_z+dz,'minecraft:dark_prismarine_slab',type='bottom',waterlogged=False)
        for dy in (74,82):
            for dz in (-3,3):p.put(x,dy,tower_z+dz,'minecraft:iron_bars')
        p.box(x,71,tower_z+3,x,72,tower_z+3,'minecraft:air')
        p.put(x,73,tower_z+4,'mcwlights:tavern_wall_lantern',facing='south')
        # Visible balance machinery and suspended weights are outside the moving leaves.
        p.box(x,82,tower_z-1,x,84,tower_z-1,'minecraft:chain',axis='y',waterlogged=False)
        p.box(x-1,78,tower_z-2,x+1,81,tower_z,'minecraft:polished_andesite')
        for dy in range(71,80):p.put(x+1,dy,tower_z+1,'minecraft:ladder',facing='west',waterlogged=False)
    approach=range(-1200,-1184) if north else range(-1103,-1087)
    for n,z in enumerate(approach):
        y=min(70,64+n//2) if north else max(64,70-n//2)
        for x in range(1196,1205):
            wx,wz=p.world(x,z)
            clearable=('minecraft:air','minecraft:spruce_planks','minecraft:dark_oak_log','minecraft:cobblestone','minecraft:gravel')
            if any(p.fixed.get((wx,py,wz),'minecraft:air').split('[')[0] not in clearable
                   for py in range(y-1,y+5)):
                continue
            p.box(x,max(58,y-5),z,x,y-1,z,'minecraft:stone_bricks')
            # Retain a known existing path lamp beside the southern approach;
            # its post leaves ample walking width in this nine-block roadway.
            old=p.fixed.get((wx,y,wz))
            if old is None or (wx,y,wz) in p.port_connections:
                p.put(x,y,z,'minecraft:stone_brick_stairs',facing='south' if north else 'north',half='bottom',shape='straight',waterlogged=False)
            for py in range(y+1,y+5):
                old=p.fixed.get((wx,py,wz))
                if old is None or (wx,py,wz) in p.port_connections:p.put(x,py,z,'minecraft:air')
    z=-1178 if north else -1110
    p.put(1189,72,z,'minecraft:chiseled_stone_bricks')
    p.put(1189,73,z,'minecraft:stone_button',face='floor',facing='north',powered=False)
    radio(p,1190,72,z,False,facing='east')
    p.sign(1187,72,z+2,['River drawbridge','Press: open / close','Wait on the stone bank','Keep the spans clear'])
    return [1189,73,z]


def build_bridge(home,angle=DEFAULT_OPEN_ANGLE):
    angle=open_angle(angle)
    layout=Layout(home);Storage(layout).reserve(64*1024**2)
    directory=layout.state/'settlement'
    if not read_json(directory/'status.json',{}).get('finished'):raise UserError('Wait for the current native operation')
    core=read_json(directory/'master-45e88a165ed60ce438ec5d87094ed476faeebdaa68693ae6d1835a11eeea6aeb.json')
    port=read_json(directory/'pirate-port-master-3bcc8f6bdfaf4d4ff44805e9fc5e5dee1b5b8b07d50916dba04af20a67ba72ba.json')
    registry=read_json(directory/'registry.json');backup=read_json(directory/'backup-receipt.json')
    if not backup.get('verified'):raise UserError('Verified complete world backup required')
    # Survey includes both real banks and the estuary, not an invented flat demo site.
    survey=read_json(directory/'survey-after-core.json')
    p=SurveyedWorldPlan(registry,survey,(1200+X_OFFSET,-1144),backup['sha256'],core,rotation=0)
    port_blocks={(x,y,z):port['palette'][i] for x,y,z,i in port['blocks']}
    p.fixed.update(port_blocks)
    p.port_connections={pos:state for pos,state in port_blocks.items()
        if 1170<=pos[0]<=1235 and -1200<=pos[2]<=-1088}
    # The southern ramp grades into one known, owner-built public footpath.
    # No building, inventory or natural structure receives this exception.
    p.port_connections.update({pos:state for pos,state in p.fixed.items()
        if 1194+X_OFFSET<=pos[0]<=1206+X_OFFSET and -1104<=pos[2]<=-1088 and 60<=pos[1]<=74
        and state.split('[')[0] in ('minecraft:air','minecraft:cobblestone','minecraft:gravel')})
    for previous in directory.glob('terrain-before-core-*.json'):
        for row in read_json(previous)['samples']:p.protected.update(tuple(v) for v in row['block_entities'])
    p.landmark('Lanternwater Mechanical Drawbridge',1200,71,-1110,'Transport',
               ['Two lifting spans', 'Water-powered reduction gearing', 'Native button controls on both banks', 'Commissioning pending'])
    north=abutment(p,True);south=abutment(p,False)
    systems=[power_house(p,-1172,True),power_house(p,-1116,False)]
    leaf(p,-1172,1,29);leaf(p,-1116,-1,28)
    for system in systems:
        for key in ('bearing','sequencer','wheel','glue_min','glue_max'):
            system[key][0]+=X_OFFSET
        system['open_angle_degrees']=angle
        system['expected_open_angle']=-angle if system['open_negative'] else angle
    for button in (north,south):button[0]+=X_OFFSET
    target=directory/'drawbridge-plan.json'
    if target.exists():
        prior=directory/('drawbridge-plan-'+digest(target)+'.json')
        if not prior.exists():target.rename(prior)
    result=p.save(target)
    engineering={'format':'awft-native-engineering:1','created':utcnow(),'seed':registry['seed'],
        'world_path':registry['world_path'],'backup_sha256':backup['sha256'],
        'construction_sha256':result['sha256'],'open_angle_degrees':angle,
        'systems':systems,'buttons':[north,south],'radios':placed_radios()}
    write_json(directory/'engineering-plan.json',engineering)
    result.update(engineering_sha256=digest(directory/'engineering-plan.json'),
                  adapted_port_connections=p.adapted,
                  status='Physical plan generated; native placement and mechanical operation pending')
    write_json(directory/'drawbridge-manifest.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='adapted_port_connections'} |
          {'adapted_port_connections':len(result['adapted_port_connections'])}),flush=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home',type=Path,default=Path(r'D:\A World for Two'))
    parser.add_argument('--open-angle',type=int,default=DEFAULT_OPEN_ANGLE,
                        help='Integer opening angle45–60 degrees; default55')
    parser.add_argument('--engineering-only',action='store_true',
                        help='Prepare settings for the exact placed bridge; never regenerate its deck')
    parser.add_argument('--destination',type=Path,help='Engineering-only output directory inside owned settlement state')
    args=parser.parse_args()
    if args.engineering_only:
        print(json.dumps(prepare_engineering(args.home,args.open_angle,args.destination)),flush=True)
    else:
        if args.destination is not None:
            parser.error('--destination requires --engineering-only')
        build_bridge(args.home,args.open_angle)
