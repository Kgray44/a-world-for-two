"""Original Lanternwater topside ornament. Source proposals, never world actions.

The working native bridge is an immutable historical input, not permission to
reuse its glue/cycle authority after changing a leaf. All outputs are forbidden
for construction until the parent admits that separate physical transaction.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from control_room.common import UserError, digest, read_json, utcnow
from tools.artistic_bridge_refinement import (
    AIR, LEAVES, flatten, payload, saved_closed_bearings,
)
from tools.artistic_materials import require_material_rule, require_outdoor_rule
from tools.artistic_maritime_depth import admit_owner
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld, base, properties

MIB=1024**2
MAX_OUTPUT=16*MIB
BASE='staging/bridge-tower-native-settle-20261027T1823Z/full-verification.json'
BASE_SHA='5500bf6e11c36d4b0dca9bcdeac555b3bf9b600db8763c80d091c1e0194317b0'
ENGINEERING_SHA='7e82c7d49754c61be08788f659e0865492be8b7238eef1004de1e5fdaec0ea9b'
CYCLE='engineering-result-c4e5b8e2-5e2b-4ffe-9878-141f43af0725.json'
POSTS=((1186,-1185),(1200,-1185),(1186,-1103),(1200,-1103))
VOID={AIR,'minecraft:cave_air','minecraft:void_air'}
FIXTURES={'minecraft:lantern','minecraft:stone_button','minecraft:lever','minecraft:chest','minecraft:barrel',
          'minecraft:cartography_table','minecraft:bookshelf','minecraft:potted_flowering_azalea_bush'}
CAMERAS=(
    {'name':'north-walk-topside','feet':[1193.5,71,-1189.5],'look_at':[1193,73,-1152]},
    {'name':'south-walk-topside','feet':[1193.5,71,-1099.5],'look_at':[1193,73,-1135]},
    {'name':'leaf-side-carving','feet':[1180,75,-1157],'look_at':[1187,72,-1157]},
    {'name':'north-lantern-hood','feet':[1190,72,-1192],'look_at':[1186,75,-1185]},
    {'name':'river-full-55-OPEN-pending','feet':[1168,64,-1144],'look_at':[1193,83,-1144]},
)


def moving_owner(pos):
    x,y,z=pos
    if not(1187<=x<=1198 and 69<=y<=73):return None
    return 'north' if -1172<=z<=-1144 else 'south' if -1143<=z<=-1116 else None


def pedestrian(pos):
    x,y,z=pos
    return 1188<=x<=1197 and 71<=y<=74 and -1185<=z<=-1103


def fixed_envelope(pos):
    x,y,z=pos
    return 1185<=x<=1201 and 71<=y<=76 and any(abs(z-c)<=1 for c in (-1185,-1103))


def swept_glue_hits(pos,label):
    """Conservative continuous voxel envelope, NOT a native collision result.

    0.5degree samples are inflated0.15m. The farthest vertex radius is below30m,
    so half-step displacement is <0.131m; that inflation encloses interpolation.
    Actual models/contraption collision and vessel rigging remain native gates.
    """
    pivot,direction,length=next((v,d,n)for name,v,d,n in LEAVES if name==label)
    cy,cz=70.5,pivot+.5;sign=-1 if label=='north'else 1
    lo,hi=sorted((pivot,pivot+direction*(length-1)))
    if not(pos[0]+1>1187-.15 and pos[0]<1199+.15):return False
    vertices=[(y-cy,z-cz)for y in(69,74)for z in(lo,hi+1)]
    if max(math.hypot(y,z)for y,z in vertices)>=30:raise UserError('Re-derive the finite rotation enclosure for a changed leaf')
    for half_degrees in range(111):
        a=math.radians(sign*half_degrees/2);c,s=math.cos(a),math.sin(a)
        points=[(cy+y*c-z*s,cz+y*s+z*c)for y,z in vertices]
        low_y=min(y for y,z in points)-.15;high_y=max(y for y,z in points)+.15
        low_z=min(z for y,z in points)-.15;high_z=max(z for y,z in points)+.15
        if pos[1]+1>low_y and pos[1]<high_y and pos[2]+1>low_z and pos[2]<high_z:return True
    return False


class Topside:
    def __init__(self,registry,original,protected=()):
        self.registry,self.original=registry,dict(original)
        self.blocks={};self.owners={};self.features=[]
        self.protected=set(protected)
        for pos,value in self.original.items():
            key=base(value)
            if key in FIXTURES or key.startswith(('handcrafted:','mcwwindows:','mcwdoors:')) or (key.startswith('create:') and not moving_owner(pos)):
                self.protected.add(pos)
        # State-level whitelist, not just ID-level: each proposed moving state
        # must already exist on the actual historically cycled leaf palette.
        self.moving_states={value for pos,value in self.original.items() if moving_owner(pos) and base(value) not in VOID}

    def state(self,name,**props):
        schema=self.registry['blocks'].get(name)
        if schema is None or any(str(v).lower()not in schema.get(k,())for k,v in props.items()):
            raise UserError('Exact registered topside block/property required: '+name+' '+str(props))
        return name+('['+','.join(k+'='+str(v).lower()for k,v in sorted(props.items()))+']'if props else'')

    def at(self,pos):return self.blocks.get(pos,self.original.get(pos,AIR))

    def put(self,pos,name,*,owner,**props):
        pos=tuple(pos);value=self.state(name,**props)
        if any(type(n)is not int for n in pos)or pedestrian(pos):
            raise UserError('Preserve the complete ten-wide pedestrian body corridor')
        if pos in self.protected and value!=self.original.get(pos,AIR):
            raise UserError('Preserve exact BE, machinery, control, window, furniture or existing light')
        if owner in ('north','south'):
            if moving_owner(pos)!=owner or value not in self.moving_states or pos[1]<70:
                raise UserError('Moving ornament must use an already-cycled exact state inside its old leaf volume')
            pivot,direction,length=next((p,d,n)for label,p,d,n in LEAVES if label==owner)
            n=(pos[2]-pivot)*direction
            if not 2<=n<=length-3:
                raise UserError('Keep complete bearing attachment and final nose rows unchanged')
            if pos[1]==70 and (not base(value).endswith('_slab') or properties(value).get('type')!='top'):
                raise UserError('Deck inlay retains the same thin top slab and Y71 walking surface')
        elif owner=='fixed':
            if not fixed_envelope(pos)or moving_owner(pos):raise UserError('Fixed carving escaped its four finite bank lantern standards')
            old=self.original.get(pos,AIR)
            # The two southern light plinths gain a full top before their new
            # lantern. Every other structural core and existing lamp is kept.
            allowed_plinth=pos in{(x,73,z)for x,z in POSTS if z==-1103}and base(old)=='minecraft:stone_brick_slab'
            if base(old)not in VOID and value!=old and not allowed_plinth:
                raise UserError('Fixed ornament preserves original structural cores and useful fixtures')
        else:raise UserError('Explicit fixed or moving ownership required')
        if pos in self.blocks and self.blocks[pos]!=value:raise UserError('Two topside details conflict')
        if value!=self.original.get(pos,AIR):self.blocks[pos]=value;self.owners[pos]=owner
        if len(self.blocks)>1200:raise UserError('Split this bounded topside proposal')


def construct(registry,original,protected=()):
    p=Topside(registry,original,protected)
    for label,pivot,direction,length in LEAVES:
        def put(wx,wy,n,name,**props):p.put((wx,wy,pivot+direction*n),name,owner=label,**props)
        # Narrow oak lozenges are actual flush top slabs, not full blocks or a
        # raised rug which changes walking/collision or the thin underside.
        for n in (4,11,18,24):
            if n>=length-2:continue
            for x in (1189,1190,1195,1196):
                put(x,70,n,'minecraft:oak_slab',type='top',waterlogged=False)
        for dn in (-1,0,1):
            for x in range(1191,1195):
                light=(dn==0 and x in(1191,1194))or(dn!=0 and x in(1192,1193))
                put(x,70,14+dn,'minecraft:oak_slab'if light else'minecraft:dark_oak_slab',type='top',waterlogged=False)
        # Three different short structural motifs per side break the current
        # repeating single-height rail. All are old proven movable state forms.
        for x in (1187,1198):
            for n in (3,4,5):
                put(x,72,n,'create:metal_girder',axis='z',x=False,z=True,top=False,bottom=False,waterlogged=False)
            for n in (10,11,12):
                put(x,72,n,'dawnoftimebuilder:dark_oak_support_beam',axis='x',pillar_connection='nothing',subaxis=False,waterlogged=False)
            for n in (17,18,19):put(x,72,n,'createdeco:industrial_iron_support',facing='up',waterlogged=False)
            # Quarterspan lamps remain exactly in place. Their carved cheek
            # blocks attach to their real steel standards; the central standard
            # receives one additional real supported light, not a dummy glow.
            for n in(6,8,20,22):
                put(x,72,n,'dawnoftimebuilder:dark_oak_support_beam',axis='x',pillar_connection='nothing',subaxis=False,waterlogged=False)
            put(x,72,14,'minecraft:iron_bars',north=False,south=False,east=False,west=False,waterlogged=False)
            put(x,73,14,'minecraft:lantern',hanging=False,waterlogged=False)
        p.features.append({'owner':label,'composition':'Three short steel/curved-timber/cast-iron crest bays, retained quarterspan lights with carved cheeks, supported centre lantern standards and a flush oak compass lozenge',
                           'unchanged':'Ten-wide body lane; roots/nose rows; thin slab height and underside; every drive/control block',
                           'new_motion_authority':False})
    for x,z in POSTS:
        facing='west'if x==1186 else'east'
        if z==-1103:
            p.put((x,73,z),'minecraft:stone_brick_slab',owner='fixed',type='double',waterlogged=False)
            p.put((x,74,z),'minecraft:lantern',owner='fixed',hanging=False,waterlogged=False)
        for dz in(-1,1):
            p.put((x,72,z+dz),'mythrais:corbel_scroll_centre_stone',owner='fixed',facing='north'if dz<0 else'south',shape=0)
            for y,part in((73,'lower'),(74,'middle'),(75,'upper')):
                props={'colour':0,'facing':facing}
                if part!='middle':props['mirrored']=False
                p.put((x,y,z+dz),'mythrais:decorated_column_'+part+'_small_dark_oak',owner='fixed',**props)
        p.put((x,75,z),'dawnoftimebuilder:limestone_bricks_edge',owner='fixed',facing=facing,half='top',shape='straight',waterlogged=False)
        p.put((x,76,z),'dawnoftimebuilder:limestone_gargoyle',owner='fixed',facing=facing,humidity=0,persistent=True,waterlogged=False)
        p.put((x+(-1 if x==1186 else 1),72,z),'mcwlights:covered_wall_lantern',owner='fixed',facing=facing)
        p.features.append({'owner':'fixed','at':[x,71,z],'composition':'Existing stone post/lantern preserved within a cantilevered scroll-and-carved-timber hood, molded limestone crest and outward guardian; separate wall lantern rooted on the retained full core',
                           'moving_leaf_attachment':False})
    validate(p)
    return p


def validate(p):
    full=dict(p.original);full.update(p.blocks)
    if any(p.at(pos)!=p.original.get(pos,AIR)for pos in p.protected):raise UserError('An existing fixture or actual block entity changed')
    checks=[]
    for label,pivot,direction,length in LEAVES:
        leaf={pos:value for pos,value in full.items()if moving_owner(pos)==label}
        checks.append(require_material_rule(leaf,label+' COMPLETE ornamented moving leaf'))
        for n in range(length):
            z=pivot+direction*n
            for x in range(1188,1198):
                for y in range(71,75):
                    if base(full.get((x,y,z),AIR))not in VOID:raise UserError('Closed pedestrian body clearance changed')
            for x in range(1187,1199):
                pos=x,70,z
                if n<=1 or n>=length-2:
                    for y in range(69,74):
                        q=x,y,z
                        if full.get(q,AIR)!=p.original.get(q,AIR):raise UserError('Root or nose row changed')
                elif not base(full.get(pos,AIR)).endswith('_slab')or properties(full[pos]).get('type')!='top':
                    raise UserError('Every thin moving deck bay keeps its original walking plane')
    checks.append(require_material_rule(full,'COMPLETE bridge including towers, machinery lodges, banks and new topside'))
    outdoors=require_outdoor_rule(full,'Complete bridge and approaches')
    # A source envelope check is deliberately separate from actual contraption
    # collision, rigging clearance or native assembly acceptance.
    moving={pos:value for pos,value in p.blocks.items()if p.owners[pos]in('north','south')}
    fixed={pos:value for pos,value in p.blocks.items()if p.owners[pos]=='fixed'}
    if not moving or not fixed:raise UserError('Both modeled moving relief and fixed sculptural standards are required')
    if any(swept_glue_hits(pos,label)for pos in fixed for label,_,_,_ in LEAVES):
        raise UserError('A new fixed ornament intersects the conservative55-degree moving-volume sweep')
    return {'material_checks':checks,'outdoor_rule':outdoors,'moving_targets':len(moving),'fixed_targets':len(fixed),
            'unchanged_ten_wide_pedestrian_body':True,'all_moving_states_from_cycled_palette':True,
            'existing_glue_bounds_unchanged':True,'fixed_solids_clear_of_conservative_55degree_voxel_sweep':True,
            'native_new_glue_cycles_restart_or_vessel_acceptance':False}


def historical_motion(home):
    plan=home/'dashboard/settlement/engineering-plan.json'
    if digest(plan)!=ENGINEERING_SHA:raise UserError('Inspect and review the changed actual engineering source before ornamenting')
    engineering=read_json(plan);proof_path=home/'dashboard/settlement'/CYCLE;proof=read_json(proof_path)
    if(proof.get('operation')!='commission'or proof.get('plan_sha256')!=ENGINEERING_SHA or proof.get('cycles')!=2
       or proof.get('cleanup_required')is not False or proof.get('temporary_tickets_remaining')!=0
       or proof.get('temporary_ticket_chunks_remaining')!=[] or proof.get('ticket_release_failures')!=[] or proof.get('error')
       or proof_path.with_name(proof_path.name+'.complete').read_text().strip()!=digest(proof_path)
       or engineering.get('open_angle_degrees')!=55):raise UserError('Exact historical actual two-cycle55-degree provenance required')
    return {'engineering_sha256':ENGINEERING_SHA,'actual_old_cycle_sha256':digest(proof_path),'old_cycle_finished':proof['finished'],
            'old_authority_inherited':False,'engineering':engineering}


def prepare(home,output,checkpoint_id,checkpoint_sha):
    home,output=Path(home).resolve(),Path(output).resolve()
    if output.exists()or output.parent!=home/'staging'or home.parent!=Path(r'D:\A World for Two\staging\world-tests'):
        raise UserError('New immediate owned private topside proposal directory required')
    reserve=guard(2*MIB,MAX_OUTPUT)
    current=read_json(home/'dashboard/settlement/backup-receipt.json')
    if current.get('verified')is not True or(current.get('id'),current.get('sha256'))!=(checkpoint_id,checkpoint_sha):
        raise UserError('Exact current verified stopped checkpoint required')
    admit_owner(home,read_json(home/'dashboard/artistic-owner.json'),current,checkpoint_id,checkpoint_sha)
    path=home/BASE
    if digest(path)!=BASE_SHA:raise UserError('The exact native-canonical full bridge source changed')
    template=read_json(path);registry=read_json(home/'dashboard/settlement/registry.json')
    if template.get('seed')!=registry.get('seed')or template.get('world_path')!=registry.get('world_path'):
        raise UserError('Actual bridge/registry world differs')
    motion=historical_motion(home);snapshot=BackupWorld(home,current,registry)
    try:
        closed=saved_closed_bearings(snapshot)
        original={pos:snapshot.state(pos)for pos in flatten(template)}
        # Outside the older sparse plan, actual saved AIR is never inferred.
        for x in range(1185,1202):
            for y in range(71,77):
                for z in(*range(-1186,-1183),*range(-1104,-1101)):
                    original.setdefault((x,y,z),snapshot.state((x,y,z)))
        p=construct(registry,original,snapshot.protected);proof=validate(p)
        before={pos:snapshot.state(pos)for pos in p.blocks}
        if any(pos in snapshot.protected for pos in p.blocks):raise UserError('No saved/default block entity may enter the ornament delta')
        # Independently witness every exact proposed moving state on a real
        # saved representative, with no BE. Old assembly does not prove every
        # arbitrary instance of a similar ID is safe.
        representatives={}
        for pos,value in original.items():
            if moving_owner(pos)and value in{v for q,v in p.blocks.items()if moving_owner(q)}and pos not in snapshot.protected:
                representatives.setdefault(value,pos)
        required={v for q,v in p.blocks.items()if moving_owner(q)}
        if set(representatives)!=required:raise UserError('Every exact moving state needs a real saved non-BE representative from the cycled palette')
        full=dict(original);full.update(p.blocks);sources=snapshot.sources.copy()
    finally:snapshot.close()
    docs={}
    docs['before.json']=payload(template,before,checkpoint_sha,'VERIFY ONLY exact saved bridge topside preimage')
    docs['before.json'].update(verification_only=True,construction_forbidden=True)
    for label in('north','south','fixed'):
        blocks={pos:value for pos,value in p.blocks.items()if p.owners[pos]==label}
        docs[label+'-ornament-PROPOSAL.json']=payload(template,blocks,checkpoint_sha,'FORBIDDEN pending reviewed glue/admission: '+label+' topside')
        docs[label+'-ornament-PROPOSAL.json']['construction_forbidden']=True
    # No old inventory/control/kinetic payload is replayed from the historical
    # template. Existing BE positions are immutable and excluded from the delta;
    # ordinary kinetic network metadata may change during normal future cycles.
    docs['complete-future-VERIFY-ONLY.json']=payload(template,full,checkpoint_sha,'VERIFY ONLY future complete bridge topside, existing BEs untouched')
    docs['complete-future-VERIFY-ONLY.json'].update(verification_only=True,construction_forbidden=True)
    mask={pos:AIR for pos in p.blocks}
    mask.update({(x,y,z):AIR for x in range(1188,1198)for z in range(-1185,-1102)for y in range(71,75)})
    docs['future-reservation-ONLY.json']=payload(template,mask,checkpoint_sha,'RESERVATION ONLY ornament and retained walk body')
    docs['future-reservation-ONLY.json'].update(verification_only=True,construction_forbidden=True)
    raw={name:(json.dumps(doc,separators=(',',':'))+'\n').encode()for name,doc in docs.items()}
    manifest={'format':'awft-bridge-topside-proposal:1','created':utcnow(),'source_sha256':digest(Path(__file__)),
              'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'native_canonical_base_sha256':BASE_SHA,
              'historical_motion':{k:v for k,v in motion.items()if k!='engineering'},'closed_native_bearings':closed,
              'moving_nonBE_saved_representatives':[{'state':s,'at':list(q),'saved_BE':False}for s,q in sorted(representatives.items())],
              'features':p.features,'proof':proof,'cameras':list(CAMERAS),'saved_sources':sources,'storage_guard':reserve,
              'new_glue_entities_or_program_writes':0,'native_actions':0,'world_writes':0,'construction_forbidden':True,
              'next_gates':['Parent-reviewed exact closed preimage and temporary ownership of both real moving leaves',
                            'Fresh saved glue census/custody and explicit admission; no generic setup replay',
                            'Place/reverify fixed and moving proposals only after that admission',
                            'Normal shape settlement, fresh appropriate glue, actual signed55-degree two bank-button cycles, closed readback and restart',
                            'Eye-level/night/art review, retained drive/control use and vessel-specific collision/rigging checks'],
              'files':{name:{'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}for name,data in raw.items()}}
    raw['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    if sum(map(len,raw.values()))>MAX_OUTPUT:raise UserError('Finite topside output exceeded')
    output.mkdir()
    for name,data in raw.items():(output/name).write_bytes(data)
    return {'output':str(output),'manifest_sha256':digest(output/'manifest.json'),'proof':proof,'native_actions':0}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in('home','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--checkpoint-id',required=True);parser.add_argument('--checkpoint-sha256',required=True)
    a=parser.parse_args();print(json.dumps(prepare(a.home,a.output,a.checkpoint_id,a.checkpoint_sha256),indent=2))
