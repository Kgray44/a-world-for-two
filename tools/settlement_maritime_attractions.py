"""Stage maritime proposals and read-only clearance checks, never apply a world edit.

The sailing craft is a real Small Ships entity. The historic flagship remains
architecture. Cradle movement, boat retention and player use need native tests.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import time
import uuid
import zipfile
from pathlib import Path

from control_room.common import Layout, REPO, UserError, atomic_write, digest, read_json, utcnow
from control_room.storage import Storage
from tools.settlement import Plan
from tools.settlement_cinematic import verified_geometry
from tools.settlement_detail import load_context


BASE_BACKUP_ID = '20261027T034106Z-ecd64f'
BASE_BACKUP_SHA = '616f1f5eb67b0502b163f3cb756f5000d8498f46847e2fc1d58bfcf3bd752fed'
SMALLSHIPS_FILE = 'smallships-neoforge-1.21.1-2.0.2.jar'
SMALLSHIPS_SHA512 = '3ca7ec4a9f6800a5e9f90cb273e8495c5919c2d9a0707160a1d4391fa11c5525e3f76038f877023929d3e3104b3df79e8afc1138de0f7df64530649cb3b76d20'
CREATE_FILE = 'create-1.21.1-6.0.10.jar'
CREATE_SHA512 = '11cc8fc049d2f67f6548c7abfada6b82a3adb5c7ca410a742de04bbca76e03862c518721b88d806f6e6d768a4d68531fdb903a85859b25d1484d550cc7bafd4b'
SMALLSHIPS_SOURCE = 'https://github.com/talhanation/smallships/tree/4bfb8680a3fecd8c7e71506b941a79c51c49dffb'
AIR = 'minecraft:air'
WATER = 'minecraft:water[level=0]'
OUTPUT_BOUND = 8*1024**2
POSITION_BOUND = 5000
COG_POSITION = (1196.5, 63.1, -1264.5)
COG_NAME = 'The Sea Glass Promise'
PULLEY = (1156, 77, -1440)
VANILLA_BOAT_DIMENSIONS = {'width':1.375,'height':0.5625}
VANILLA_ENTITY_TYPE_SHA = 'ce88efd23c8db67ddbf421214711030ceccb56b7e9e978657cf1d897f82af59f'
# A deliberately larger empty-boat envelope, including lateral and vertical
# margin. Native admission must reject a real entity/AABB outside this bound.
TENDER_BODY_SWEEP = (1157.5,62.80,-1440.5,1159.5,78.30,-1438.5)
# Facts inspected in the pinned CogEntity and ShipPartEntity classes: keel
# offset, bottom above root, sideways offset, square width, height. The last box
# is the mast. This is a conservative block-volume check, not a native shape test.
COG_PARTS = ((-2.1,0,0,2.8,1.6),(-3.4,0,0,2.35,2.7),(0,0,0,2.3,1.6),
             (1.5,0,0,2.3,1.6),(3,1,0,.75,1.5),(0,0,0,.3,9))
CLASS_PINS = {
    'com/talhanation/smallships/world/entity/ship/Ship.class': 'fd9a31d1608f28dc5e0f83b460d9bd44741ff16237d95fefeb721548e1e9a304',
    'com/talhanation/smallships/world/entity/ship/ContainerShip.class': 'fd4dff75ec38690d67b92dfaadcd7b1d695704dae6c9f9077b8a660065974f83',
    'com/talhanation/smallships/world/entity/ship/CogEntity.class': '6448f6042c07fb30f32f81551f1e720a77a914a26224d10ba7b112e6366cc6e2',
    'com/talhanation/smallships/world/entity/ship/abilities/Sailable.class': 'd5a3d24ac51bfcfbc21a906122895f010b5cfcf145b08aa3046bf385713b3b63',
    'com/talhanation/smallships/world/entity/ship/sail/SailDamage.class': '02491d7c0065876958a945061d50a9e9d8567101d194285df50eb4e0966d3c7a',
    'com/talhanation/smallships/world/entity/ship/hitbox/ShipPartEntity.class': 'c5e21e3ed918df1b5c81076f51a896784ccf7858469cc8b3133537f8499f982b',
}
CREATE_CLASSES = {
    'com/simibubi/create/content/contraptions/pulley/PulleyBlockEntity.class': 'a2dda7747b7c19a1b23be4190073aad4203ce0bb70d94fd7c514738d4c0a65bd',
    'com/simibubi/create/content/contraptions/pulley/PulleyContraption.class': '23251c328dc9d8d0b5044b855720a97eefc67ccfa6e5032a549ae6d56f525144',
    'com/simibubi/create/content/contraptions/ContraptionCollider.class': '26e50f37935a6fcde16fb931a756cf8f6a967e767492c000e6a5b1ae06b2338f',
    'com/simibubi/create/content/contraptions/AbstractContraptionEntity.class': '07bf9b7f71de914184de9d7a647224ce6fb3cd1dc35ab71c2bb380492a0d2846',
}


def base(state):
    return state.split('[',1)[0]


def inspect_pins(home):
    """Read exact cached bytes; no upstream code, launch or downloader executes."""
    result=[]
    for filename,expected,classes in ((SMALLSHIPS_FILE,SMALLSHIPS_SHA512,CLASS_PINS),
                                     (CREATE_FILE,CREATE_SHA512,CREATE_CLASSES)):
        path=Path(home)/'caches/mods'/filename
        if not path.is_file() or path.stat().st_size>32*1024**2 or digest(path,'sha512')!=expected:
            raise UserError('The inspected immutable maritime dependency changed: '+filename)
        with zipfile.ZipFile(path) as archive:
            for name,sha in classes.items():
                if hashlib.sha256(archive.read(name)).hexdigest()!=sha:
                    raise UserError('The inspected native class changed: '+name)
        result.append({'file':filename,'sha512':expected,'class_sha256':classes})
    path=Path(home)/'server/libraries/net/minecraft/server/1.21.1-20240808.144430/server-1.21.1-20240808.144430-srg.jar'
    name='net/minecraft/world/entity/EntityType.class'
    with zipfile.ZipFile(path) as archive:
        if archive.getinfo(name).file_size>2*1024**2 or hashlib.sha256(archive.read(name)).hexdigest()!=VANILLA_ENTITY_TYPE_SHA:
            raise UserError('The inspected vanilla boat dimensions changed')
    result.append({'file':path.name,'class_sha256':{name:VANILLA_ENTITY_TYPE_SHA},
                   'inspected_boat_dimensions':VANILLA_BOAT_DIMENSIONS})
    return result


def context(home):
    """Bind all completed hulls, access, districts, routes and historical BEs."""
    ctx=load_context(home)
    if ctx.backup.get('id')!=BASE_BACKUP_ID or ctx.backup.get('sha256')!=BASE_BACKUP_SHA:
        raise UserError('Review a new maritime baseline if the verified ecd64f backup changes')
    directory=Path(home)/'dashboard/settlement'
    summary=read_json(directory/'detail-pass-candidate23-native.json',{})
    districts=summary.get('districts',[])
    if {row.get('district') for row in districts}!={'castle','village','pirate-port','south-bank','harbor-quays'}:
        raise UserError('All five exact completed detail districts are required')
    for row in districts:
        sha=row['plan_sha256'];prefix='detail-'+row['district']+'-'
        plan,source=verified_geometry(directory,{'path':str(directory/(prefix+sha+'.json')),'sha256':sha},
                                      sha,prefix+sha[:12]+'-verify.json')
        if (plan['seed'],plan['world_path'])!=(ctx.registry['seed'],ctx.registry['world_path']):
            raise UserError('A maritime exclusion belongs to a different permanent world')
        ctx.previous.update({(x,y,z):plan['palette'][i] for x,y,z,i in plan['blocks']})
        ctx.protected.update(tuple(v['pos']) for v in plan.get('block_entities',[]))
        ctx.sources.append(source)
    ctx.sources.append({'file':'detail-pass-candidate23-native.json','sha256':digest(directory/'detail-pass-candidate23-native.json')})
    return ctx


class MaritimePlan(Plan):
    def __init__(self,ctx,survey):
        super().__init__(ctx.registry,survey,(1170,-1346),ctx.backup['sha256'])
        self.ctx=ctx
        self.protected.update(ctx.protected)
        self.preconditions={}
        self.zone='Maritime attractions'

    def state(self,key,**properties):
        if key not in self.native or properties.keys()-self.native[key].keys():
            raise UserError('Unknown maritime native block/property: '+key)
        return super().state(key,**properties)

    def soundings(self,x,z):
        ox,oz=self.origin;gx=ox+math.floor((x-ox)/self.step)*self.step;gz=oz+math.floor((z-oz)/self.step)*self.step
        keys=((gx,gz),(gx+self.step,gz),(gx,gz+self.step),(gx+self.step,gz+self.step))
        if any(k not in self.samples for k in keys):raise UserError('Marine survey does not surround a proposed attraction')
        rows=[self.samples[k] for k in keys]
        if any(not row.get('fluid') or base(row.get('block',''))!='minecraft:water' or row['y']!=63 for row in rows):
            raise UserError('Relocate the attraction to surveyed open water')
        return rows

    def prior(self,pos):
        if pos in self.ctx.previous:return self.ctx.previous[pos]
        x,y,z=pos;rows=self.soundings(x,z)
        if y<max(row['ocean_floor_y'] for row in rows):
            raise UserError('Do not excavate or guess the seabed; native finer survey required')
        # A hypothesis for a READ-ONLY native verification, never permission to
        # replace seagrass, player additions, another boat or unknown inventories.
        return WATER if y<63 else AIR

    def require(self,pos):
        self.preconditions[pos]=self.prior(pos)

    def world_put(self,x,y,z,key,**properties):
        pos=x,y,z;state=self.state(key,**properties)
        if not (1138<=x<=1204 and -1446<=z<=-1249 and 58<=y<=79):
            raise UserError('Maritime addition exceeded its reviewed finite reserve')
        if pos in self.protected or pos in self.ctx.headroom:
            raise UserError('A maritime addition would touch protected inventory or circulation')
        if pos in self.ctx.previous and self.ctx.previous[pos]!=state:
            raise UserError('A maritime addition would replace completed construction, including reserved air')
        self.require(pos)
        if self.ctx.previous.get(pos)!=state:
            super().put(x-self.cx,y,z-self.cz,key,**properties)

    def put(self,x,y,z,key,**properties):
        wx,wz=self.world(x,z)
        return self.world_put(wx,y,wz,key,**properties)


def cog_boxes(position=COG_POSITION,yaw=180):
    angle=math.radians(-yaw-90);sin,cos=math.sin(angle),math.cos(angle)
    boxes=[]
    for v,y,h,width,height in COG_PARTS:
        x=position[0]+v*cos+h*sin;z=position[2]+h*cos-v*sin
        boxes.append((x-width/2,position[1]+y,z-width/2,x+width/2,position[1]+y+height,z+width/2))
    return boxes


def box_cells(box,margin=0):
    low=[math.floor(box[n]-margin) for n in range(3)]
    high=[math.ceil(box[n+3]+margin) for n in range(3)]
    return {(x,y,z) for x in range(low[0],high[0]) for y in range(low[1],high[1]) for z in range(low[2],high[2])}


def sailing_cog(p):
    if 'smallships:cog' not in p.registry['entities']:
        raise UserError('The actual native Small Ships cog entity is not registered')
    for key in ('smallships:ship_part','minecraft:boat'):
        if key not in p.registry['entities']:raise UserError('A required native maritime entity is absent')
    # Yaw180 aligns the keel north/south. Its positive local keel axis points north.
    clearance=set().union(*(box_cells(box,.35) for box in cog_boxes()))
    for x in range(1194,1199):
        for z in range(-1270,-1258):
            if max(row['ocean_floor_y'] for row in p.soundings(x,z))>60:
                raise UserError('The actual cog berth lacks the conservative three-block water column')
            clearance.update((x,y,z) for y in (61,62))
    for pos in clearance:
        if pos in p.protected or base(p.blocks.get(pos,p.ctx.previous.get(pos,AIR))) not in ('minecraft:air','minecraft:water'):
            raise UserError('Cog multipart/player clearance intersects completed or proposed construction')
        p.require(pos)
    # Reserve the first eight blocks of straight departure as well as the berth.
    # This remains a VERIFY-only water/air hypothesis, never a clearing action.
    launch_boxes=[(b[0]-.35,b[1]-.35,b[2]-8.35,b[3]+.35,b[4]+.35,b[5]+.35)
                  for b in cog_boxes()]
    launch_boxes.append((1194,61,-1278,1199,63,-1258))
    launch_cells=set().union(*(box_cells(box) for box in launch_boxes))
    for x in range(1194,1199):
        for z in range(-1278,-1258):
            if max(row['ocean_floor_y'] for row in p.soundings(x,z))>60:
                raise UserError('The cog initial departure lacks the conservative three-block water column')
    for pos in launch_cells:
        if pos in p.protected or base(p.blocks.get(pos,p.ctx.previous.get(pos,AIR))) not in ('minecraft:air','minecraft:water'):
            raise UserError('Cog initial departure clearance intersects completed or proposed construction')
        p.require(pos)
    extra=(',Tags:["awft_maritime_cog_v1"],Type:"spruce",Rotation:[180f,0f],Motion:[0d,0d,0d],'
           'Sail:{State:0b,Color:"white",SailHealth:100f},HullDamage:0f,Sunken:0b,Sinking:0b,locked:0b,Items:[]')
    p.entity('smallships:cog',1196-p.cx,63.1,-1265-p.cz,COG_NAME,extra)
    ident=str(uuid.uuid5(uuid.NAMESPACE_URL,'awft:'+p.registry['seed']+':'+COG_NAME))
    return {'entity':'smallships:cog','uuid':ident,'name':COG_NAME,'position':list(COG_POSITION),'yaw':180,
            'wood':'spruce','sail_state':'furled, intact white canvas','container':'empty, original configured size retained',
            'ownership':'unlocked shared craft; no forged account ownership or invulnerability',
            'native_parts':6,'clearance_cells':len(clearance),'driver_seat_candidate':[1196.5,64.7,-1261.5],
            'initial_departure_boxes':[list(b) for b in launch_boxes],
            'initial_departure_clearance_cells':len(launch_cells),
            'boarding_ledge':[1192.5,65,-1261.5],'initial_departure':'Head north slowly past the finger pier before turning; stop before shoals or other hulls',
            'entity_load_boat_controls_passengers_and_restart':'pending native dedicated/client check'}


def berth(p):
    if p.ctx.previous.get((1191,65,-1249))!='minecraft:spruce_planks':
        raise UserError('The reviewed existing quay connection changed')
    for x in range(1189,1192):
        p.world_put(x,64,-1250,'minecraft:spruce_planks')
        p.world_put(x,65,-1250,'minecraft:spruce_stairs',facing='south',half='bottom',shape='straight',waterlogged=False)
        for z in range(-1268,-1250):
            p.world_put(x,64,z,'minecraft:spruce_planks')
            if x in (1189,1191):p.world_put(x,62,z,'minecraft:stripped_spruce_log',axis='z')
            if z in (-1267,-1261,-1255):p.world_put(x,63,z,'minecraft:stripped_spruce_log',axis='x')
    for z in range(-1267,-1260):p.world_put(1192,64,z,'minecraft:spruce_planks')
    for z in range(-1268,-1251):p.world_put(1189,65,z,'minecraft:spruce_fence')
    p.sign(1190-p.cx,66,-1250-p.cz,['The Sea Glass Promise','Shared sailing cog','Board from the landing','Furl sails at the quay'])
    # Two-wide walking route and a clear boarding apron; all required air is a
    # native before-state check. It is never cleared automatically by this tool.
    for x in (1190,1191):
        for z in range(-1268,-1250):
            for y in (65,66,67):
                pos=x,y,z
                if pos not in p.blocks:p.require(pos)
    return {'quay_support':[1191,65,-1249],'new_stair':[1191,65,-1250],
            'pier_floor_y':64,'new_bounds':[1189,-1268,1192,-1250],
            'support':'floating timber pontoons and cross-bearers; no guessed seabed excavation',
            'actual_walking_and_boarding':'pending native check'}


def tender_hoist(p):
    required={PULLEY:'create:rope_pulley',(1153,77,-1440):'create:hand_crank',
              (1154,77,-1440):'create:shaft',(1155,77,-1440):'create:shaft'}
    for pos,kind in required.items():
        if base(p.ctx.previous.get(pos,''))!=kind:raise UserError('The original flagship hoist component changed')
        p.require(pos)
    original={(x,75,z) for x in range(1154,1159) for z in range(-1442,-1437)}
    original|={(x,76,z) for x in range(1154,1159) for z in (-1442,-1438)}
    payload={(x,75,z):'minecraft:dark_oak_slab[type=double,waterlogged=false]'
             for x in range(1154,1161) for z in range(-1442,-1437)}
    payload.update({(x,76,z):'minecraft:dark_oak_fence' for x in range(1154,1161) for z in (-1442,-1438)})
    payload.update({(1160,76,z):'minecraft:dark_oak_fence' for z in range(-1441,-1438)})
    for pos,state in payload.items():
        if pos in original:
            if p.ctx.previous.get(pos)!=state:raise UserError('The exact original 35-block cradle changed')
            p.require(pos)
        elif base(state)=='minecraft:dark_oak_slab':p.world_put(*pos,'minecraft:dark_oak_slab',type='double',waterlogged=False)
        else:p.world_put(*pos,state)
    if set(payload)&p.protected:raise UserError('Never move an inventory or protected block entity with the tender cradle')
    swept={(x,y+dy,z) for x,y,z in payload for dy in range(-13,2)}
    for pos in swept:
        if pos not in payload and base(p.ctx.previous.get(pos,AIR)) not in ('minecraft:air','minecraft:water'):
            raise UserError('Hoist swept payload would strike completed construction')
        if pos in p.protected:raise UserError('Hoist sweep crosses a protected block entity')
        p.require(pos)
    # A platform-only sweep misses the carried boat above the fully raised
    # floor. These exact additional body/BE cells must be verified beforehand.
    tender_cells=box_cells(TENDER_BODY_SWEEP)
    for pos in tender_cells:
        if pos not in payload and base(p.ctx.previous.get(pos,AIR)) not in ('minecraft:air','minecraft:water'):
            raise UserError('Tender body sweep would strike completed construction')
        if pos in p.protected:
            raise UserError('Tender body sweep crosses a protected block entity')
        p.require(pos)
    return {'pulley':list(PULLEY),'crank':[1153,77,-1440],'unchanged_original_payload':35,'new_blocks':17,
            'payload':[{'pos':list(pos),'state':state} for pos,state in sorted(payload.items())],
            'expected_moving_blocks':52,'swept_occupied_cells':len(swept),'glue_min':[1154,75,-1442],'glue_max':[1160,76,-1438],
            'tender_body_sweep_box':list(TENDER_BODY_SWEEP),'tender_body_swept_cells':len(tender_cells),
            'combined_cradle_and_tender_clearance_cells':len(swept|tender_cells),
            'native_vanilla_boat_dimensions':VANILLA_BOAT_DIMENSIONS,
            'actual_tender_must_fit_design_envelope':True,'passengers_during_first_lift':0,
            'floor_y':{'original':75,'water_pickup':62,'fully_retracted':76},
            'maximum_pulley_offset':14,'rope_gap':'The native pulley extends through its initial one-block air gap and picks up the glued floor below',
            'tender_center_at_water':[1158.5,63.05,-1439.5],'tender_center_when_raised':[1158.5,77.05,-1439.5],
            'tender':'Use one existing EMPTY vanilla spruce/oak tender, manually sailed into the cradle; no Small Ships entity on this lift',
            'raised_walkway':[1153,76,-1440],'physics_scope':'Only the small 52-block cradle. Never glue the architectural hull, rigging, pulley, shafts or operator walk.',
            'controls':'Actual hand crank; its native reverse input lowers/raises. No forged Speed NBT, teleport, or client animation substitutes.',
            'commissioning':[
                'Fresh zero-player backup, exact prior-state verification, and native glue-volume/component audit before any movement.',
                'First run empty: confirm exactly52 payload blocks and no static hull/BE attachment. Abort and recover if the captured set differs.',
                'Require a fresh native spatial entity-occupancy pass for the whole cradle/body sweep before every motion phase; no pet, other boat, dropped item or unauthorized occupant may overlap.',
                'Pulse native crank; verify signed real pulley motion and offset. Stop at offset14 (floor62), never continue toward the seabed.',
                'Bring one empty vanilla tender into the marked starboard half; rope and pulley stay west of the boat. No riders during the first lift.',
                'Raise slowly to the native fully retracted stop (floor76). Confirm the same boat UUID, no ejection, clipping, damage, or loss.',
                'Lower again to floor62, sail out, repeat; then verify unloaded and raised-boat persistence after a controlled server restart.',
                'Only after retention/restart pass, test player boarding from the upper walkway. If native retention fails, keep the lift decorative and tender at water level.'
            ],'native_assembly_lift_retention_player_use_and_restart':'unverified; this is a commissioning contract, not acceptance'}


def entity_admission(p,cog,hoist):
    """Machine-readable contract; no entity query or live-world access occurs."""
    berth_boxes=[list((b[0]-.35,b[1]-.35,b[2]-.35,b[3]+.35,b[4]+.35,b[5]+.35)) for b in cog_boxes()]
    payload=hoist['payload']
    cradle=[min(row['pos'][0] for row in payload),62,min(row['pos'][2] for row in payload),
            max(row['pos'][0] for row in payload)+1,78,max(row['pos'][2] for row in payload)+1]
    payload_sha=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return {'format':'awft-maritime-entity-admission:1','dimension':'minecraft:overworld',
        'scan_provider':'Native ServerLevel entity AABB query after all target chunks are FULL and entity-ready',
        'maximum_snapshot_age_ticks':0,'repeat_immediately_before_each_mutation_or_motion':True,
        'reject_unlisted_entities':True,'category_exemptions':[],
        'regions':{'cog-berth':berth_boxes,'cog-initial-departure':cog['initial_departure_boxes'],
                   'hoist-cradle-and-tender':[cradle,hoist['tender_body_sweep_box']]},
        'phases':{
            'cog-before-spawn':{'regions':['cog-berth','cog-initial-departure'],'allowed_roles':[]},
            'cog-launch':{'regions':['cog-berth','cog-initial-departure'],'allowed_roles':['commissioned-cog']},
            'hoist-empty-cycle':{'regions':['hoist-cradle-and-tender'],'allowed_roles':['owned-hoist-contraption']},
            'hoist-tender-cycle':{'regions':['hoist-cradle-and-tender'],'allowed_roles':['owned-hoist-contraption','selected-empty-tender']}},
        'commissioned_cog_uuid':cog['uuid'],'owned_hoist_payload_sha256':payload_sha,
        'selected_tender_rule':{'entity':'minecraft:boat','native_dimensions':VANILLA_BOAT_DIMENSIONS,
             'wood':['oak','spruce'],'explicit_uuid_required':True,'empty_inventory_required':True,
             'passengers':0,'actual_aabb_inside_verified_design_sweep_required':True},
        'multipart_rule':'Only native Small Ships ship_part with actual parent UUID equal to the commissioned cog UUID may accompany that cog',
        'duplicate_uuid_custody':'The separate moved/unloaded UUID custody check remains required; spatial occupancy does not replace it',
        'native_status':'No scan performed; this is the required fresh native admission contract'}


def overlap(first,second):
    return all(max(first[n],second[n])<min(first[n+3],second[n+3]) for n in range(3))


def admit_entity_snapshot(contract,snapshot,phase,now_tick,authorizations=None):
    """Pure gate for future native scan receipts, also used by negative tests.

    Callers must supply native observations, exact current game time and proven
    owned UUID/payload custody; synthetic inputs are never runtime evidence.
    """
    rules=contract['phases'].get(phase)
    if not rules or snapshot.get('format')!='awft-native-maritime-occupancy:1':
        raise UserError('Unknown maritime entity admission phase or native receipt')
    if (type(now_tick) is not int or snapshot.get('game_time')!=now_tick or
        snapshot.get('dimension')!=contract['dimension'] or snapshot.get('all_target_chunks_entity_ready') is not True or
        set(snapshot.get('regions_scanned',[]))!=set(rules['regions'])):
        raise UserError('A same-tick native spatial entity scan of every ready target region is required')
    authorizations=authorizations or {};boxes=[b for name in rules['regions'] for b in contract['regions'][name]]
    seen_ids=set();seen_roles=set()
    if not isinstance(snapshot.get('entities'),list):
        raise UserError('Native entity observations are missing')
    for row in snapshot['entities']:
        bounds=row.get('bounds',[])
        if len(bounds)!=6 or any(type(v) not in (int,float) or not math.isfinite(v) for v in bounds) or any(bounds[n]>=bounds[n+3] for n in range(3)):
            raise UserError('Invalid native entity bounding box')
        if not any(overlap(bounds,box) for box in boxes):
            continue
        kind,ident=row.get('entity'),row.get('uuid');roles=rules['allowed_roles'];allowed=False
        try:
            uuid.UUID(str(ident))
        except (ValueError,AttributeError) as exc:
            raise UserError('Native entity UUID is missing or invalid') from exc
        if ident in seen_ids:
            raise UserError('Native spatial observations must deduplicate entity UUIDs')
        seen_ids.add(ident)
        if 'commissioned-cog' in roles:
            expected=contract['commissioned_cog_uuid']
            allowed=(kind=='smallships:cog' and ident==expected or
                     kind=='smallships:ship_part' and row.get('native_parent_uuid')==expected)
            if kind=='smallships:cog' and ident==expected:seen_roles.add('commissioned-cog')
        if 'owned-hoist-contraption' in roles and ident==authorizations.get('hoist_uuid') and ident:
            owned=(kind in ('create:stationary_contraption','create:contraption') and
                row.get('native_class')=='com.simibubi.create.content.contraptions.ControlledContraptionEntity' and
                row.get('captured_payload_sha256')==contract['owned_hoist_payload_sha256'])
            allowed=allowed or owned
            if owned:seen_roles.add('owned-hoist-contraption')
        if 'selected-empty-tender' in roles and ident==authorizations.get('tender_uuid') and ident:
            envelope=TENDER_BODY_SWEEP
            tender=(kind=='minecraft:boat' and row.get('wood') in ('oak','spruce') and
                row.get('inventory_empty') is True and row.get('passengers')==0 and
                all(envelope[n]<=bounds[n] and bounds[n+3]<=envelope[n+3] for n in range(3)))
            allowed=allowed or tender
            if tender:seen_roles.add('selected-empty-tender')
        if not allowed:
            raise UserError('Unauthorized spatial entity blocks maritime admission: '+str(kind)+' '+str(ident))
    required=[]
    if phase=='cog-launch':required.append('commissioned-cog')
    if phase=='hoist-tender-cycle':required.append('selected-empty-tender')
    if authorizations.get('hoist_uuid') and 'owned-hoist-contraption' in rules['allowed_roles']:
        required.append('owned-hoist-contraption')
    if set(required)-seen_roles:
        raise UserError('The actual authorized maritime entity was not observed in its required ready region')
    return {'phase':phase,'game_time':now_tick,'native_observations':len(snapshot['entities']),
            'scope':'Pure gate result; source tests do not constitute a native scan'}


def sea_glass_cache(p):
    """A suspended four-block-deep cache, with an unobstructed return to air."""
    x,z=1148,-1282
    for y in range(59,67):
        for dx in (-1,0,1):
            for dz in (-1,0,1):p.require((x+dx,y,z+dz))
    for y in (60,61,62):p.world_put(x,y,z,'minecraft:chain',axis='y',waterlogged=True)
    p.world_put(x,63,z,'minecraft:stripped_spruce_log',axis='y')
    p.world_put(x,64,z,'minecraft:lantern',hanging=False,waterlogged=False)
    p.world_put(x,59,z,'minecraft:chest',facing='south',type='single',waterlogged=True)
    items=('minecraft:emerald','minecraft:gold_nugget','minecraft:cookie')
    if any(item not in p.registry['items'] for item in items):raise UserError('The modest cache reward needs registered vanilla items')
    title=json.dumps(json.dumps({'text':'The Sea Glass Cache'}))
    entries=','.join('{Slot:'+str(n)+'b,id:'+json.dumps(item)+',count:'+str(count)+'}'
                     for n,(item,count) in enumerate(zip(items,(2,6,8))))
    p.tag(x-p.cx,59,z-p.cz,'{CustomName:'+title+',Items:['+entries+']}')
    p.sign(1190-p.cx,65,-1268-p.cz,['A chart in sea glass','Find the small lantern','West: X1148 Z-1282','Cache four blocks below'])
    return {'name':'The Sea Glass Cache','buoy':[x,64,z],'chest':[x,59,z],
            'depth_below_water_surface':4,'reward':'2 emeralds, 6 gold nuggets, 8 cookies; one chest, no reset automation',
            'access':'Short open-water dive from a boat; return vertically to the surface beside the buoy. No enclosed tunnel, hostile spawn, TNT or forced loading.',
            'clues':'Waxed sign at the new cog landing; a single visible lantern buoy; named underwater chest',
            'breath_and_return_path':'Native swimming/visibility/player test pending; do not advertise safe underwater access before that check'}


def document(p,states,*,commands=(),tags=()):
    if not states or len(states)>POSITION_BOUND:raise UserError('Maritime proposal exceeded its finite cell bound')
    palette=sorted(set(states.values()));lookup={v:n for n,v in enumerate(palette)}
    return {'format':'awft-native-settlement:1','name':'Maritime attraction prior-state check' if not commands and not tags else 'Maritime attractions candidate',
            'created':utcnow(),'seed':p.registry['seed'],'world_path':p.registry['world_path'],'backup_sha256':p.backup,
            'bounds':[min(v[0] for v in states),min(v[2] for v in states),max(v[0] for v in states),max(v[2] for v in states)],
            'palette':palette,'blocks':[[*pos,lookup[state]] for pos,state in sorted(states.items(),
                key=lambda item:(item[0][0]//16,item[0][2]//16,item[0][1],item[0][0],item[0][2]))],
            'block_entities':list(tags),'commands':list(commands),'landmarks':[],
            'validation':'Staged only. Prior-state verification, native entity/kinetic checks and parent admission are mandatory.'}


def proposal(ctx,survey):
    p=MaritimePlan(ctx,survey)
    dock=berth(p);cog=sailing_cog(p);hoist=tender_hoist(p);cache=sea_glass_cache(p)
    candidate=document(p,p.blocks,commands=p.commands,tags=[{'pos':list(pos),'nbt':nbt} for pos,nbt in p.tags.items()])
    before=document(p,p.preconditions)
    return {'format':'awft-maritime-proposal:1','candidate_plan':candidate,
            'berth':dock,'sailing_cog':cog,'hoist':hoist,'discovery':cache,
            'spatial_entity_admission':entity_admission(p,cog,hoist),
            'native_world_mutation':'None; the wrapper is intentionally not an admissible native placement plan',
            'parent_admission_required':[
                'Preserve a fresh complete backup and close the server to players for native construction; never run work during a player session.',
                'Run clearance-read-only.json through native VERIFY only. Every proposed water/air cell is a hypothesis until this exact probe passes.',
                'Review current entity custody and verify no duplicate cog UUID exists, including moved/unloaded ships. Never reset a player-used entity or reward chest.',
                'Require the machine-readable same-tick spatial entity admission for berth, initial departure and hoist body/sweep regions; block verification cannot detect a pet, other boat or dropped item.',
                'Require the staged native SNBT probe pass and exact pinned dependency hashes; then explicitly extract/review candidate_plan for bounded placement.',
                'Native-create, inspect entity NBT/parts, board with both users, sail slowly and test inventory/restart; only then call the cog operational.',
                'Commission the separate hoist sequence. Actual boat retention, client shapes and restart remain unverified until recorded.'
            ]},before


def prepare(home,destination=None):
    layout=Layout(Path(home));ctx=context(layout.home)
    survey_path=layout.state/'settlement/marine-survey-0.6.5.json'
    survey=read_json(survey_path)
    pins=inspect_pins(layout.home)
    data,clearance=proposal(ctx,survey)
    raw=lambda value:(json.dumps(value,indent=2,ensure_ascii=False)+'\n').encode('utf-8')
    identity=hashlib.sha256(raw(data)).hexdigest()
    output=(layout.staging/('maritime-attractions-'+identity[:16]) if destination is None else Path(destination).resolve())
    if not output.resolve().is_relative_to(layout.staging.resolve()) or output.exists():
        raise UserError('Use a new owned staging folder; preserve earlier proposals and all failed receipts')
    Storage(layout).reserve(OUTPUT_BOUND,target=output)
    documents={'proposal.json':raw(data),'clearance-read-only.json':raw(clearance)}
    if sum(map(len,documents.values()))>OUTPUT_BOUND//2:raise UserError('Split the maritime proposal before staging')
    output.mkdir(parents=True)
    for name,content in documents.items():atomic_write(output/name,content)
    manifest={'format':'awft-maritime-manifest:1','at':utcnow(),'base_backup_id':BASE_BACKUP_ID,'base_backup_sha256':BASE_BACKUP_SHA,
              'documents':{name:{'sha256':digest(output/name),'bytes':len(content)} for name,content in documents.items()},
              'source_sha256':digest(Path(__file__)),'marine_survey_sha256':digest(survey_path),'geometry_sources':ctx.sources,
              'dependency_inspection':pins,'smallships_official_source':SMALLSHIPS_SOURCE,
              'known_composite_positions':len(ctx.previous),'protected_block_entities':len(ctx.protected),
              'new_physical_blocks':len(data['candidate_plan']['blocks']),'new_entities':len(data['candidate_plan']['commands']),
              'read_only_probe_positions':len(clearance['blocks']),'maximum_output_bytes':OUTPUT_BOUND,
              'status':'Staged only; no live command, native placement, physics assembly, or player interference performed',
              'native_snbt_probe':'pending','current_client_server_entity_use':'pending',
              'hoist_native_retention_and_restart':'pending','underwater_player_access':'pending',
              'native_spatial_entity_scan':'pending; same-tick ready-region queries required before each native phase',
              'tender_body_swept_cells':data['hoist']['tender_body_swept_cells'],
              'combined_hoist_clearance_cells':data['hoist']['combined_cradle_and_tender_clearance_cells']}
    atomic_write(output/'manifest.json',raw(manifest))
    return {'directory':str(output),'manifest_sha256':digest(output/'manifest.json'),
            'new_blocks':manifest['new_physical_blocks'],'new_entities':manifest['new_entities'],
            'read_only_positions':manifest['read_only_probe_positions'],'status':manifest['status']}


PROBE_SOURCE = r'''
import com.google.gson.*;
import net.minecraft.nbt.*;
import java.nio.file.*;
public class MaritimeNbtProbe {
  public static void main(String[] args) throws Exception {
    JsonObject wrapper=JsonParser.parseString(Files.readString(Path.of(args[0]))).getAsJsonObject();
    JsonObject plan=wrapper.getAsJsonObject("candidate_plan");int entities=0,tags=0;
    for(JsonElement value:plan.getAsJsonArray("commands")) {
      String command=value.getAsString();
      if(!command.startsWith("summon smallships:cog "))throw new IllegalStateException("Unexpected entity");
      CompoundTag tag=TagParser.parseTag(command.substring(command.indexOf('{')));
      CompoundTag sail=tag.getCompound("Sail");
      if(!tag.hasUUID("UUID") || !tag.getString("Type").equals("spruce") || tag.getBoolean("locked")
          || tag.getBoolean("Sunken") || tag.getBoolean("Sinking") || tag.getFloat("HullDamage")!=0
          || !sail.contains("State",Tag.TAG_BYTE) || sail.getByte("State")!=0
          || !sail.getString("Color").equals("white") || sail.getFloat("SailHealth")!=100
          || !tag.getList("Items",Tag.TAG_COMPOUND).isEmpty()
          || tag.getList("Rotation",Tag.TAG_FLOAT).size()!=2 || tag.getList("Motion",Tag.TAG_DOUBLE).size()!=3
          || !TagParser.parseTag(tag.toString()).equals(tag))throw new IllegalStateException("Ship NBT changed");
      entities++;
    }
    for(JsonElement value:plan.getAsJsonArray("block_entities")) {
      CompoundTag tag=TagParser.parseTag(value.getAsJsonObject().get("nbt").getAsString());
      if(!TagParser.parseTag(tag.toString()).equals(tag))throw new IllegalStateException("Block NBT changed");tags++;
    }
    if(entities!=1 || tags!=3)throw new IllegalStateException("Unexpected actor/inventory count");
    System.out.println("AWFT_MARITIME_NBT_PASS entities="+entities+" block_entities="+tags);
  }
}
'''


def native_probe(home,directory):
    """Actual Minecraft SNBT syntax/field roundtrip, never entity/world creation."""
    layout=Layout(Path(home));directory=Path(directory).resolve()
    if not directory.is_relative_to(layout.staging.resolve()):raise UserError('Probe only an owned staged maritime proposal')
    manifest=read_json(directory/'manifest.json');path=directory/'proposal.json'
    if digest(path)!=manifest['documents']['proposal.json']['sha256']:raise UserError('The staged maritime proposal changed')
    inspect_pins(layout.home)
    libraries=layout.server/'libraries';launch=libraries/'net/neoforged/neoforge/21.1.262/win_args.txt'
    lines=[v.split('=',1)[1] for v in launch.read_text(encoding='utf-8').splitlines() if v.startswith('-DlegacyClassPath=')]
    if len(lines)!=1:raise UserError('Use the exact installed server runtime classpath')
    jars=[]
    for relative in lines[0].split(';'):
        item=(layout.server/relative).resolve()
        if not item.is_relative_to(libraries.resolve()) or not item.is_file():raise UserError('Runtime dependency escaped its exact installed library tree')
        jars.append(item)
    named=sorted((libraries/'net/minecraft/server').rglob('*-srg.jar'))
    if len(named)!=1:raise UserError('Exactly one pinned named Minecraft server is required for the parser')
    cp=os.pathsep.join(map(str,dict.fromkeys([*named,*jars])))
    work=directory/('native-snbt-'+str(time.time_ns()));Storage(layout).reserve(2*1024**2,target=work);work.mkdir()
    source=work/'MaritimeNbtProbe.java';atomic_write(source,PROBE_SOURCE)
    jdk=Path(r'C:\Program Files\Java\jdk-21.0.10\bin')
    arguments=work/'javac.args'
    atomic_write(arguments,'-proc:none\n--release\n21\n-classpath\n"'+cp.replace('\\','/')+'"\n-d\n"'+work.as_posix()+'"\n"'+source.as_posix()+'"\n')
    flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
    compiled=subprocess.run([str(jdk/'javac.exe'),'-J-Xmx128m','-J-XX:-UsePerfData','@'+str(arguments)],
                            cwd=work,capture_output=True,text=True,timeout=40,creationflags=flags)
    atomic_write(work/'compile.log',(compiled.stdout+compiled.stderr)[:1024**2])
    if compiled.returncode:raise UserError('Native maritime SNBT compilation failed; preserve '+str(work))
    arguments=work/'java.args'
    atomic_write(arguments,'-Xms32M\n-Xmx192M\n-XX:-UsePerfData\n-classpath\n"'+(str(work)+os.pathsep+cp).replace('\\','/')+
                 '"\nMaritimeNbtProbe\n"'+path.as_posix()+'"\n')
    run=subprocess.run([str(jdk/'java.exe'),'@'+str(arguments)],cwd=work,capture_output=True,text=True,timeout=40,creationflags=flags)
    atomic_write(work/'native.log',(run.stdout+run.stderr)[:1024**2])
    passed=run.returncode==0 and 'AWFT_MARITIME_NBT_PASS entities=1 block_entities=3' in run.stdout
    result={'at':utcnow(),'status':'pass' if passed else 'failed','proposal_sha256':digest(path),
            'compiler_exit_code':compiled.returncode,'native_exit_code':run.returncode,'runtime_launch_sha256':digest(launch),
            'log_sha256':digest(work/'native.log'),'scope':'Actual Minecraft1.21.1 TagParser and NBT field roundtrip only; SmallShips entity loading, water placement, controls, client collisions and Create boat lifting remain unverified'}
    atomic_write(work/'result.json',json.dumps(result,indent=2)+'\n')
    if not passed:raise UserError('Native maritime SNBT probe failed; preserve '+str(work))
    return {'receipt':str(work/'result.json'),**result}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home',type=Path,default=Path('D:/A World for Two'))
    parser.add_argument('--output',type=Path)
    parser.add_argument('--native-probe',type=Path)
    args=parser.parse_args()
    print(json.dumps(native_probe(args.home,args.native_probe) if args.native_probe else prepare(args.home,args.output),indent=2))
