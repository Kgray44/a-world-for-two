"""A cohesive marble guardian fountain, derived from the actual42 photographs.

Source/prospective-precondition producer only. No native command or world write.
The current wet snapshot and the expected post-reset precondition are deliberately
different evidence: the latter needs a fresh zero-difference native admission.
"""
from __future__ import annotations

import argparse
from collections import deque
import copy
import hashlib
import json
from pathlib import Path
import zlib

from control_room.common import UserError, digest, read_json, utcnow
from tools.artistic_materials import require_material_rule, require_outdoor_rule
from tools.artistic_spawn_plaza import (AIR, CENTER, HEADER, OUTLET, PISTON,
    PLUG_OPEN, PUMP, WHEEL, WHEEL_SOURCE, WHEEL_BAFFLE, STOP_LEVER, JET_WITNESSES,
    DIR, SOFT, state, key, octagon, rect, payload)
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld, NBTReader, MAX_CHUNK

BASE_REL = 'artistic-spawn-plaza-r4-repeater-20261027T2037Z/plaza.json'
BASE_SHA = '6ae428127da4bd98223fad546e6b00588f547c456b080198ff1b42dca2945d4a'
ROUTES_REL = 'artistic-spawn-plaza-r2-20261027T2002Z/manifest.json'
MARS = 'dawnoftimebuilder:marble_statue_mars'
INTAKE = (1139, 65, -1129)
INTAKE_PIPE = (1139, 66, -1129)
OUTPUT_PATH = ((1141,66,-1129),(1141,67,-1129),(1141,68,-1129),(1140,68,-1129),
               (1139,68,-1129),(1139,68,-1130),(1139,69,-1130),(1139,70,-1130),
               (1139,71,-1130),(1139,72,-1130),(1139,73,-1130),(1139,73,-1129))
FULL_WHITE = ('minecraft:quartz_bricks','dawnoftimebuilder:marble',
              'dawnoftimebuilder:marble_coffer','rechiseled:quartz_block_bordered',
              'minecraft:chiseled_quartz_block','chipped:inlayed_calcite')
CURB = {(1138+dx,70,-1128+dz) for dx,dz in
        ((-1,-1),(-1,1),(1,-1),(1,1),(-2,-1),(-2,1),(2,-1),(2,1),
         (-1,-2),(1,-2),(-1,2),(1,2))}
WATER_CROSS = {(1138+dx,70,-1128+dz) for dx,dz in
               ((0,0),(-1,0),(1,0),(0,-1),(0,1),(-2,0),(2,0),(0,-2),(0,2))}


def decode(doc):
    return {tuple(row[:3]): doc['palette'][row[3]] for row in doc['blocks']}


def border(cells):
    return {p for p in cells if any((p[0]+x,p[1]+z) not in cells
            for x,z in ((1,0),(-1,0),(0,1),(0,-1)))}


def masonry(x,y,z):
    """Pale masonry courses and three-wide carved panels, not colored noise."""
    a,b=(x-1138)%3==0,(z+1128)%3==0
    if y%3==0:
        return 'chipped:inlayed_calcite' if a and b else 'rechiseled:quartz_block_bordered' if a or b else 'minecraft:quartz_bricks'
    return 'minecraft:chiseled_quartz_block' if a and b else 'dawnoftimebuilder:marble_coffer' if a else 'minecraft:quartz_bricks' if b else 'dawnoftimebuilder:marble'


def control_positions():
    result={STOP_LEVER,PISTON,PLUG_OPEN,OUTLET,HEADER,INTAKE,INTAKE_PIPE,PUMP,WHEEL,WHEEL_SOURCE,WHEEL_BAFFLE}
    result|={(x,66,-1130) for x in range(1140,1146)}
    result|={(1141,66,-1125),(1141,67,-1125)}
    for y in range(68,74):
        x=1141 if y%2==0 else 1140;result.add((x,y,-1125))
        if y<73:result.add((1140 if x==1141 else 1141,y,-1125))
    result|={(x,y,z) for x,z in ((1139,-1125),(1139,-1124),(1138,-1124),(1138,-1125)) for y in (72,73)}
    return result


class Sculpture:
    def __init__(self,registry,base,routes):
        self.registry,self.base=registry,dict(base)
        self.blocks=dict(base);self.routes=routes;self.joints=[]
        self.fixed=control_positions();self.pipe_nodes=set(OUTPUT_PATH)
        self.jet_columns={(x,y,z) for x,_,z in JET_WITNESSES for y in range(66,71)}
        self.torches={p for p,s in base.items() if key(s) in ('minecraft:redstone_torch','minecraft:redstone_wall_torch')}

    def put(self,pos,name,**props):
        pos=tuple(pos);x,y,z=pos
        if not (1117<=x<=1149 and 63<=y<=78 and -1138<=z<=-1108):
            raise UserError('Sculptural fountain escaped its owned finite envelope')
        value=state(self.registry,name,**props)
        if pos in self.fixed and value!=self.base[pos]:
            raise UserError('Do not move a proven fountain/control point: '+str(pos))
        if (x,z) in self.routes and y in (self.routes[x,z]+1,self.routes[x,z]+2) and value!=AIR:
            raise UserError('Sculpture must preserve actual public body/headroom')
        if pos in self.jet_columns and value!=AIR:
            raise UserError('A sculptural detail blocks a proven single ribbon')
        self.blocks[pos]=value

    def clear_old(self):
        for p in self.base:
            x,y,z=p
            if 1133<=x<=1143 and 66<=y<=75 and -1132<=z<=-1123 and p not in self.fixed:
                self.put(p,AIR)

    def stone(self,pos):
        self.put(pos,masonry(*pos))

    def safe_shell(self,pos,name,**props):
        # Additional conducting masonry beside a torch can change the circuit.
        if any(sum(abs(pos[i]-t[i]) for i in range(3))==1 for t in self.torches):
            return
        if pos not in self.fixed:self.put(pos,name,**props)


def palette_and_lower_basin(p):
    # Retain the original joints, but remove the orange crossing-bar contrast.
    for pos,s in list(p.blocks.items()):
        if pos[1]<=65 and pos not in p.fixed:
            if key(s)=='minecraft:cut_copper':p.put(pos,'rechiseled:quartz_block_bordered')
            elif key(s)=='minecraft:smooth_sandstone':p.put(pos,'dawnoftimebuilder:marble')
    foot=octagon(*CENTER,5,7);edge=border(foot)
    oldfoot=octagon(*CENTER,5,8)
    for x,z in oldfoot-foot:
        if (x,65,z) not in p.fixed:p.stone((x,65,z))
        if (x,66,z) not in p.fixed:p.put((x,66,z),AIR)
    for x,z in foot:
        if (x,z) in edge:
            if (x,65,z) not in p.fixed:p.stone((x,65,z))
            dx,dz=x-1138,z+1127
            face=('east' if dx>0 else 'west') if abs(dx)>=abs(dz) else ('south' if dz>0 else 'north')
            if (x,66,z) in p.fixed:continue
            if (x+z)%3==0:
                p.put((x,66,z),'dawnoftimebuilder:marble_edge',facing=face,half='top',shape='straight',waterlogged=False)
            else:p.put((x,66,z),'dawnoftimebuilder:marble_coffer_slab' if dx%2 else 'minecraft:smooth_quartz_slab',type='bottom',waterlogged=False)


def carved_pedestal(p):
    foot=octagon(1138,-1128,3,5);edge=border(foot)
    intake_pool=rect(1139,-1130,1140,-1129)
    for x,z in foot:
        if (x,z) not in intake_pool and (x,65,z) not in p.fixed and (x,68,z) not in p.jet_columns:
            p.stone((x,65,z))
        for y in (66,67,68):
            pos=(x,y,z)
            if pos in p.fixed or pos in p.jet_columns:continue
            if (x,z) in edge:
                if y==68:p.put(pos,'dawnoftimebuilder:marble_coffer_slab',type='top',waterlogged=False)
                else:p.stone(pos)
    for x,z,face in ((1136,-1130,'west'),(1140,-1130,'east'),(1136,-1126,'west'),(1140,-1126,'east')):
        for y in (66,67,68):
            pos=x,y,z
            if pos in p.fixed:continue
            p.put(pos,'dawnoftimebuilder:marble_sided_column',facing=face,
                  vertical_connection='under' if y==68 else 'both',waterlogged=False)
        if z==-1126:
            p.put((x,69,z),'dawnoftimebuilder:limestone_gargoyle',facing=face,
                  humidity=0,persistent=True,waterlogged=False)
        else:p.put((x,69,z),'dawnoftimebuilder:iron_fancy_lantern',facing='up',waterlogged=False)
    for x in (1136,1140):
        for z in (-1129,-1127):
            if (x,68,z) in OUTPUT_PATH:continue
            p.put((x,68,z),'mythrais:corbel_scroll_centre_stone',
                  facing='west' if x==1136 else 'east',shape='0')


def backed_bowl(p):
    foot=octagon(1138,-1128,2,3)
    for x,z in foot:p.stone((x,69,z))
    for pos in CURB:p.stone(pos)
    for pos in WATER_CROSS:p.put(pos,AIR)
    for x,_,z in JET_WITNESSES:
        for y in range(66,71):p.put((x,y,z),AIR)


def crown_and_statue(p):
    # A sculptural neck encloses a SINGLE controlled descent. Merely wrapping
    # a larger hollow room would let the header fan sideways into new falls.
    neck=octagon(1138,-1129,2,3)
    for y in (71,72,73):
        for x,z in neck:
            pos=x,y,z
            if pos in p.jet_columns or pos in p.fixed:continue
            if pos in OUTPUT_PATH or x==1138 and z==-1128:
                p.put(pos,AIR);continue
            p.safe_shell(pos,masonry(x,y,z))
    p.stone((1138,72,-1129))
    # Modeled fluted pilasters stand on the FULL basin curbs, with masonry
    # backing on the header side. They give the drum a sculpted depth profile.
    for x,face in ((1136,'west'),(1140,'east')):
        for y in (71,72,73):
            p.put((x,y,-1129),'dawnoftimebuilder:marble_sided_column',facing=face,
                  vertical_connection='above' if y==71 else 'under' if y==73 else 'both',waterlogged=False)
    # Keep the crown narrower than the reflecting pool and lower pedestal;
    # the former oversized upper shelf read like a second utility platform.
    crown=octagon(1138,-1129,2,3)
    for x,z in crown:
        pos=x,74,z
        if pos in p.fixed:continue
        family='dawnoftimebuilder:marble_coffer_slab' if (x-1138)%3 else 'minecraft:smooth_quartz_slab'
        if (z+1128)%3==0:family='dawnoftimebuilder:marble_slab'
        p.put(pos,family,type='top',waterlogged=False)
    p.put((1138,74,-1129),'minecraft:chiseled_quartz_block')
    for x in (1136,1140):
        p.put((x,75,-1129),'dawnoftimebuilder:iron_fancy_lantern',facing='up',waterlogged=False)
    for n in range(3):
        p.put((1138,75+n,-1129),MARS,facing='west',multiblock=str(n),waterlogged=False)


def internal_feed(p):
    nodes=set(OUTPUT_PATH)
    for pos in OUTPUT_PATH:
        ports={d:tuple(pos[i]+v[i] for i in range(3)) in nodes|{PUMP}
               or pos==OUTPUT_PATH[-1] and d=='west' for d,v in DIR.items()}
        if pos in ((1139,70,-1130),OUTPUT_PATH[-1]):
            # Full non-waterloggable casing backs the upper-bowl curb and the
            # side-fed header. A waterloggable open pipe beside a world source
            # would create a second uncontrolled source at the header boundary.
            p.put(pos,'create:encased_fluid_pipe',**ports)
        elif pos==(1140,68,-1129):p.put(pos,'create:glass_fluid_pipe',axis='x',alt=False,waterlogged=False)
        elif pos[0]==1139 and pos[2]==-1130 and pos[1] in (69,72):
            p.put(pos,'create:glass_fluid_pipe',axis='y',alt=False,waterlogged=False)
        else:p.put(pos,'create:fluid_pipe',waterlogged=False,**ports)


def open_service_niche(p):
    # Retain full containment beside the one-sided fall, reveal the actual wheel
    # and eliminate the broad eye-level checker wall seen in the east photo.
    for x in (1144,1146):
        for y in range(65,70):
            for z in (-1130,-1129,-1128):
                pos=x,y,z
                if pos in p.fixed:continue
                if z==-1130 and y in (68,69):p.stone(pos)
                elif x==1144 and key(p.base.get(pos,AIR)).startswith('mcwwindows:'):continue
                else:p.put(pos,AIR)
    for y in range(64,70):
        for x,z in ((1144,-1131),(1146,-1131),(1145,-1132)):
            p.stone((x,y,z))
    for x in range(1144,1147):
        for z in range(-1132,-1127):
            if z<=-1130:
                p.put((x,70,z),'dawnoftimebuilder:marble_coffer_slab' if x!=1145 else
                      'minecraft:waxed_weathered_cut_copper_slab',type='bottom',waterlogged=False)
            else:p.put((x,70,z),AIR)
    # The proven one-sided full baffle and its north source remain exact.
    for y in range(64,70):p.put((1145,y,-1131),AIR)
    for z in (-1129,-1128):
        p.put((1146,65,z),'dawnoftimebuilder:limestone_baluster',facing='east',shape='straight',waterlogged=False)


def validate(p):
    for pos in p.fixed:
        if p.blocks[pos]!=p.base[pos]:raise UserError('A proven core/control point changed')
    if key(p.blocks[1138,73,-1125])!='minecraft:repeater' or 'facing=south' not in p.blocks[1138,73,-1125]:
        raise UserError('Retain the corrected south-input diode')
    for n in range(3):
        if key(p.blocks[1138,75+n,-1129])!=MARS or 'multiblock='+str(n) not in p.blocks[1138,75+n,-1129]:
            raise UserError('One complete supported three-part central figure is required')
    if key(p.blocks[1138,74,-1129])!='minecraft:chiseled_quartz_block':raise UserError('Statue needs a full sturdy crown')
    if any(key(s) in ('mythrais:single_lancet_arch_upper_stone','supplementaries:statue')
           for pos,s in p.blocks.items() if 1133<=pos[0]<=1143 and pos[1]>=71):
        raise UserError('Remove the isolated window-antenna and miniature crest figures')
    full_seals=set(FULL_WHITE)|{'create:encased_fluid_pipe'}
    if any(key(p.blocks.get(pos,AIR)) not in full_seals for pos in CURB):
        raise UserError('Every rill-tip side needs a full non-waterloggable backing curb')
    if any(p.blocks.get(pos)!=AIR for pos in WATER_CROSS|p.jet_columns):raise UserError('Four narrow ribbons must remain clear')
    if any(key(p.blocks.get(pos,AIR)) not in full_seals for pos in
           ((1137,73,-1129),(1138,73,-1130),(1139,73,-1129),
            (1137,73,-1128),(1139,73,-1128),(1138,72,-1129))):
        raise UserError('The actual single header and outlet must have full sealed side walls')
    if any(p.blocks.get((1138,y,-1128))!=AIR for y in (71,72)):
        raise UserError('A single enclosed downspout must reach the four-rill basin')
    for (x,z),floor in p.routes.items():
        if any(p.blocks.get((x,y,z),AIR)!=AIR for y in (floor+1,floor+2)):
            raise UserError('Public arrival/promenade clearance changed')
    output=set(OUTPUT_PATH)
    if len(output)!=len(OUTPUT_PATH) or any(sum(abs(a[i]-b[i]) for i in range(3))!=1 for a,b in zip((PUMP,)+OUTPUT_PATH,OUTPUT_PATH+(HEADER,))):
        raise UserError('Connected bounded real pipe path required')
    if any(sum(abs(a[i]-INTAKE_PIPE[i]) for i in range(3))==1 for a in output):
        raise UserError('The output must not autojoin the intake and short-circuit the pump')
    material=require_material_rule(p.blocks,'Complete R5 guardian fountain/plaza and retained machinery')
    outdoor=require_outdoor_rule(p.blocks,'Complete R5 authored plaza surfaces')
    return {'material':material,'outdoor':outdoor,'pump_to_header_edges':len(OUTPUT_PATH)+1,
            'four_full_backed_single_outlets':True,'proven_core_controls_unchanged':True,
            'native_model_flow_collision_and_art_acceptance':'PENDING actual game review'}


def compose(registry,base,routes):
    p=Sculpture(registry,base,routes);p.clear_old();palette_and_lower_basin(p)
    carved_pedestal(p);backed_bowl(p);crown_and_statue(p);internal_feed(p);open_service_niche(p)
    validate(p);return p


def block_entities(snapshot,positions):
    result={}
    for cx,cz in sorted({(p[0]//16,p[2]//16) for p in positions}):
        snapshot.chunk(cx,cz);raw=snapshot.regions[cx//32,cz//32]
        location=int.from_bytes(raw[((cz&31)*32+(cx&31))*4:((cz&31)*32+(cx&31))*4+4],'big')
        offset=(location>>8)*4096;length=int.from_bytes(raw[offset:offset+4],'big');compression=raw[offset+4];packed=raw[offset+5:offset+4+length]
        if compression==3:decoded=packed
        else:
            decoder=zlib.decompressobj(31 if compression==1 else 15);decoded=decoder.decompress(packed,MAX_CHUNK+1)
            if len(decoded)>MAX_CHUNK or not decoder.eof or decoder.unconsumed_tail:raise UserError('Finite native BE custody exceeded')
        document=NBTReader(decoded).read()
        for row in document.get('block_entities',[]):
            pos=row['x'],row['y'],row['z']
            if pos in positions:result[pos]=row
    return result


def has_items(value):
    if isinstance(value,dict):
        for k,v in value.items():
            if k.lower() in ('items','inventory','item','stack','customname','loottable') and v not in ({},[],None,''):
                if not isinstance(v,dict) or v.get('id') not in (None,'minecraft:air') or v.get('count',v.get('Count',0)):
                    return True
            if has_items(v):return True
    elif isinstance(value,list):return any(has_items(v) for v in value)
    return False


def post_reset_precondition(pos,actual,base):
    """Classify a saved observation without claiming a dry state was observed."""
    previous=base.get(pos,AIR)
    if pos not in base and key(actual) not in SOFT:
        raise UserError('A new sculptural target is not saved air/soft vegetation: '+str((pos,actual)))
    if pos in base and key(actual)!=key(previous) and not (key(actual)=='minecraft:water' and previous==AIR):
        raise UserError('An owned predecessor changed outside normal fountain flow: '+str((pos,actual,previous)))
    return AIR if key(actual)=='minecraft:water' and previous==AIR else actual


def admit_checkpoint_mode(registry,base,observed,wet,expected,*,dry_checkpoint):
    if dry_checkpoint:
        if any(actual!=base[pos] for pos,actual in observed.items()):
            raise UserError('A FRESH actual dry checkpoint must retain retracted piston/plug and corrected unpowered controls, with source/header/PORT/all4jets AIR')
        if any(wet[pos]!=value for pos,value in expected.items()):
            raise UserError('A dry checkpoint cannot claim prospective fluid drainage as observed')
    else:
        if any(observed[pos]!=state(registry,'minecraft:water',level=0) for pos in (WHEEL_SOURCE,HEADER)):
            raise UserError('This reset recipe requires the actually wet native source/header')
        if 'powered=true' not in observed[STOP_LEVER] or 'facing=north' not in observed[1138,73,-1125]:
            raise UserError('R5 requires the preserved R3 STOP/diode failure before any repair')


def prepare(home,registry_path,backup_id,backup_sha,output,*,dry_checkpoint=False):
    home,output=Path(home).resolve(),Path(output).resolve()
    if output.exists() or not output.is_relative_to(home/'staging'):raise UserError('A new private R5 proposal directory is required')
    reserve=guard(16*1024**2,32*1024**2);registry=read_json(registry_path)
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    if receipt.get('verified')is not True or (receipt.get('id'),receipt.get('sha256'))!=(backup_id,backup_sha):raise UserError('Exact new stopped checkpoint required')
    path=home/'staging'/BASE_REL
    if digest(path)!=BASE_SHA:raise UserError('Frozen corrected R4 source differs')
    baseline=read_json(path);base=decode(baseline);route_doc=read_json(home/'staging'/ROUTES_REL)
    routes={(x,z):y for x,y,z in route_doc['routes']};p=compose(registry,base,routes)
    changed={pos:s for pos,s in p.blocks.items() if s!=base.get(pos,AIR)}
    snapshot=BackupWorld(home,receipt,registry);wet={};expected={};ledger=[]
    try:
        for pos,desired in changed.items():
            actual=snapshot.state(pos);wet[pos]=actual
            expected[pos]=post_reset_precondition(pos,actual,base)
            if expected[pos]!=actual:
                ledger.append({'pos':list(pos),'observed':actual,'expected_after_normal_owned_reset':AIR,'status':'EXPECTED, not observed; native zero-difference comparison mandatory'})
        reset_observed={pos:snapshot.state(pos) for pos in
            (WHEEL_SOURCE,HEADER,STOP_LEVER,(1138,73,-1125),PISTON,PLUG_OPEN,OUTLET,*JET_WITNESSES)}
        admit_checkpoint_mode(registry,base,reset_observed,wet,expected,dry_checkpoint=dry_checkpoint)
        bes=block_entities(snapshot,set(changed))
        for pos,nbt in bes.items():
            oldkey=key(base.get(pos,AIR))
            if oldkey not in ('create:fluid_pipe','create:glass_fluid_pipe','create:encased_fluid_pipe','supplementaries:statue') or has_items(nbt):
                raise UserError('Preserve a foreign/occupied native BE at sculpture target: '+str((pos,oldkey)))
            ledger.append({'pos':list(pos),'owned_replaced_BE':nbt,'authority':'Only existing owned transport/default empty crest; no inventory/kinetic NBT replay','exact_typed_original':'Retained in authenticated checkpoint chunk; decoded ledger is not a restore payload'})
        saved=snapshot.sources[:]
    finally:snapshot.close()
    checks=validate(p);full=payload(registry,backup_sha,p.blocks,'VERIFY ONLY complete R5 marble guardian fountain',before=True)
    docs={'sculpture-DELTA.json':payload(registry,backup_sha,changed,'R5 sculpture/plumbing DELTA ONLY AFTER FRESH DRY CHECKPOINT'),
          'current-wet-observed-BEFORE-ONLY.json':payload(registry,backup_sha,wet,'OBSERVED wet saved preimage; before reset only',before=True),
          'expected-post-reset-native-BEFORE.json':payload(registry,backup_sha,expected,'EXPECTED post-reset precondition; requires actual zero-difference native admission',before=True),
          'plaza.json':full}
    docs['current-wet-observed-BEFORE-ONLY.json']['construction_forbidden']=True
    docs['expected-post-reset-native-BEFORE.json']['prospective_precondition_only']=True
    docs['owned-reset-current-observations-ONLY.json']=payload(registry,backup_sha,reset_observed,
        'ONLY actual saved wet source/header/manual STOP/north diode; not a future preimage',before=True)
    docs['owned-reset-intent-ONLY.json']={
        'format':'awft-fountain-owned-reset-intent:1','checkpoint_id':backup_id,'backup_sha256':backup_sha,
        'construction_forbidden':True,'native_actions':0,
        'phases':[
            {'step':1,'normal_block_changes':[{'pos':list(WHEEL_SOURCE),'state':AIR}],
             'admission':'Exact actual saved source matches current native source; then normal neighbor updates',
             'wait_for':'Actual wheel and pump RPM zero; no manual kinetic NBT'},
            {'step':2,'normal_block_changes':[{'pos':list(HEADER),'state':AIR}],
             'admission':'Only after zero RPM; independently read the actual owned pumped source again',
             'wait_for':'Normal downstream nonsource drainage; do not clear fluid graphs'},
            {'step':3,'normal_block_changes':[{'pos':list(STOP_LEVER),'state':base[STOP_LEVER]},
                                             {'pos':[1138,73,-1125],'state':base[1138,73,-1125]}],
             'admission':'Fresh exact native before comparison; normal updates, no direct piston or plug writes',
             'wait_for':'Source/header dry, original plug at OPEN_PLUG, piston retracted, PORT dry, all4jets dry'}],
        'then':'FRESH stopped dry checkpoint REQUIRED. Rerun producer with --dry-checkpoint; it must bind actual dry MCA targets. No art placement from this wet bundle; do not present prospective AIR as saved evidence.'}
    if dry_checkpoint:
        docs['actual-dry-native-BEFORE.json']=payload(registry,backup_sha,wet,
            'VERIFY ONLY exact actual fresh stopped dry MCA art preimage',before=True)
        for name in ('current-wet-observed-BEFORE-ONLY.json','expected-post-reset-native-BEFORE.json',
                     'owned-reset-current-observations-ONLY.json','owned-reset-intent-ONLY.json'):
            del docs[name]
    else:
        docs['sculpture-DELTA.json']['construction_forbidden']=True
        docs['sculpture-DELTA.json']['requires_fresh_stopped_dry_checkpoint']=True
        steps=(
            ('1-wheel-off',{WHEEL_SOURCE:AIR},{WHEEL_SOURCE:reset_observed[WHEEL_SOURCE]},
             'Normal neighbor updates then actual wheel and pump0RPM'),
            ('2-owned-header-off',{HEADER:AIR},{HEADER:reset_observed[HEADER]},
             'REQUIRES actual0RPM and fresh header before comparison; normal updates and downstream drain'),
            ('3-normal-controls',{STOP_LEVER:base[STOP_LEVER],(1138,73,-1125):base[1138,73,-1125]},
             {pos:reset_observed[pos] for pos in (STOP_LEVER,(1138,73,-1125))},
             'Normal updates and retraction ONLY; no piston/plug state writes'))
        for name,after,previous,native_gate in steps:
            docs['reset-'+name+'-DELTA.json']=payload(registry,backup_sha,after,'Owned normal reset '+name)
            docs['reset-'+name+'-BEFORE.json']=payload(registry,backup_sha,previous,
                'Observed stopped wet states; fresh native comparison required at reset phase '+name,before=True)
            docs['reset-'+name+'-DELTA.json']['native_gate']=native_gate
            docs['reset-'+name+'-DELTA.json']['manual_controller_only']=True
            docs['reset-'+name+'-BEFORE.json']['fresh_native_phase_comparison_required']=True
    reserved=set(p.blocks)
    for n in range(21):
        x=round(1120+18*n/20);z=round(-1130+2*n/20)
        reserved|={(x+dx,y,z) for dx in (-1,0,1) for y in range(67,80)}
    docs['forest-reservation-ONLY.json']=payload(registry,backup_sha,{pos:AIR for pos in reserved},'RESERVATION ONLY R5 geometry/body/arrival/crown sightline',before=True)
    raw={n:(json.dumps(d,separators=(',',':'))+'\n').encode() for n,d in docs.items()}
    manifest={'format':'awft-r5-cohesive-guardian-fountain:1','created':utcnow(),'source_sha256':digest(Path(__file__)),
        'basis_R4_sha256':BASE_SHA,'checkpoint_id':backup_id,'checkpoint_sha256':backup_sha,
        'checks':checks,'changed_positions':len(changed),'saved_sources':saved,'actual_native_BE_and_normal_drain_custody':ledger,
        'routes_preserved':len(routes),'pipe_path':[list(pos) for pos in OUTPUT_PATH],
        'new_header_feed_face':'east side, endpoint1139,73,-1129 openwest; actual HEADER unchanged',
        'actual_dry_checkpoint':dry_checkpoint,
        'reset_first':'Normal owned wheel source AIR→0RPM; pumped header AIR→upperdrain; normalleverfalse+repeaterS; no direct piston/plug or fluid graph edits. A FRESH stopped dry checkpoint is required before executable art output.',
        'BE_policy':'No tags/inventories are replayed. Only listed owned empty transport/default decorative BEs may be replaced; all others are excluded.',
        'cameras':copy.deepcopy(route_doc.get('cameras',[])),'reserve_guard':reserve,'native_actions':0,'world_writes':0,'artistic_acceptance':False,
        'files':{n:{'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)} for n,b in raw.items()}}
    for camera in manifest['cameras']:
        if camera['name']=='fountain-crown':
            camera.update(feet=[1131,73,-1136],look_at=[1138,75,-1129])
        elif camera['name']!='fountain-wheel-service':camera['look_at']=[1138,72,-1128]
    raw['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    if sum(map(len,raw.values()))>16*1024**2:raise UserError('Finite R5 output exceeded')
    output.mkdir()
    for n,b in raw.items():(output/n).write_bytes(b)
    (output/'manifest.json.complete').write_text(hashlib.sha256(raw['manifest.json']).hexdigest()+'\n',encoding='ascii')
    return {'output':str(output),'manifest_sha256':digest(output/'manifest.json'),'changed_positions':len(changed),'checks':checks}


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('home','registry','output'):ap.add_argument('--'+name,type=Path,required=True)
    ap.add_argument('--backup-id',required=True);ap.add_argument('--backup-sha256',required=True)
    ap.add_argument('--dry-checkpoint',action='store_true')
    a=ap.parse_args();print(json.dumps(prepare(a.home,a.registry,a.backup_id,a.backup_sha256,a.output,dry_checkpoint=a.dry_checkpoint),indent=2))
