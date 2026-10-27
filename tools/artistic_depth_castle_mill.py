"""A separate physical-depth layer for the saved palace and Copper Wren mill.

Only NEW private plans and exact saved preimages are written. No game, world,
machine, entity, account or construction command is operated by this authoring
tool. Texture changes alone never count toward its depth coverage.
"""
from __future__ import annotations

import argparse
from collections import Counter, deque
import hashlib
import json
from pathlib import Path

from control_room.common import UserError, digest, read_json, utcnow
from tools.artistic_landmarks import MASONRY
from tools.artistic_materials import require_material_rule, require_outdoor_rule
from tools.artistic_mill_detail import Finish as MillProtection, joined_window_part
from tools.playtest import guard
from tools.settlement_attractions import AIR, BackupWorld, base, properties

MAX_OUTPUT=16*1024**2
MAX_TARGETS=6000
CASTLE_OFFSET=(1214,4,-1008)
MACAW_JOIN_API_SHA='8970c40ec622edd34c9b055226b403af08ab441c77303a6dc625ae18005f8184'
INPUTS={
 'castle':(
  ('prototype-castle-palace-e6ffcde57520b8cb/prototype.json','e6ffcde57520b8cb75798548ce6f8683f147c8b47f05d5bc3c9be46746159931'),
  ('prototype-castle-palace-e6ffcde57520b8cb/combined-final-delta.json','99cf7c97a2ab1ea1fce07d83f584e3a46380f74f905ea825d27a8ff9447d2bc1'),
  ('prototype-castle-palace-e6ffcde57520b8cb/mount-support-delta.json','977fe1610e28e320cb75ca51a08d20f98f2b658e40bb95c07646c1bfa8db3aae'),
  ('artistic-castle-interior-r4-20261027T1701Z/castle-interior.json','01cb2654a8078b6a99875d350ac40318f9fe74576ded56b7bafbb7a0471abd91')),
 'mill':(
  ('artistic-engineering-r2-1793106029261770100/mill-quarter.json','181e2191572846967c41e77bf5b406d0dddcc484488aa60d6725728ba651b199'),
  ('artistic-mill-r3-native-joined-20261027T1716Z/mill-detail-native-verify-only.json','747f4b1175fb6f525ecbfd5a51a7586119279f852264a383afafc88273d2973d')),
}
NORMAL={'north':(0,-1),'south':(0,1),'west':(-1,0),'east':(1,0)}
SOFT={AIR,'minecraft:cave_air','minecraft:void_air'}
FIXED_PREFIX=('handcrafted:','mcwfurnitures:','mcwlights:','supplementaries:','xercamusic:',
              'create:','create_hypertube:','overpressure:','railways:')
STRUCTURAL=set(MASONRY)|{'minecraft:'+k for k in ('quartz_block','chiseled_quartz_block',
    'smooth_quartz','quartz_pillar','polished_diorite','polished_andesite','smooth_sandstone',
    'stone_bricks','chiseled_stone_bricks','mossy_cobblestone','cobblestone','bricks','white_terracotta',
    'stripped_dark_oak_log','dark_oak_wood','stripped_spruce_wood','spruce_wood','birch_wood',
    'dark_oak_log','spruce_log','spruce_planks','dark_oak_planks','pink_terracotta')}


def decode(plan):return {tuple(row[:3]):plan['palette'][row[3]] for row in plan['blocks']}
def world(x,y,z):return x+1214,y+4,z-1008
def architectural(state):
    key=base(state)
    return (key in STRUCTURAL or key.startswith(('mcwroofs:','rechiseled:','chipped:'))
            or key.startswith('dawnoftimebuilder:limestone_')
            or key.startswith('minecraft:') and key.endswith(('_stairs','_slab')))


class Depth:
    def __init__(self,kind,registry,original,snapshot,fixed=()):
        self.kind,self.registry,self.original,self.snapshot=kind,registry,original,snapshot
        self.blocks,self.previous,self.features,self.groups,self.adopted={},{},[],{},{}
        self.joints={}
        self.group='Depth';self.fixed=set(fixed);self.relocated=set();self.real_added=set()
        self.pending=[];self.routes=[];self.bays=[];self.access=[];self.canonical_window_parts=[]
        for p,value in original.items():
            key=base(value)
            if (key.startswith(FIXED_PREFIX) or key.endswith(('_door','_bed','_wall_banner'))
                    or key in ('minecraft:chain','minecraft:chest','minecraft:barrel','minecraft:lectern',
                               'minecraft:enchanting_table','minecraft:furnace')):self.fixed.add(p)
    def actual(self,p):return self.snapshot.state(p)
    def at(self,p):return self.blocks.get(p,self.actual(p))
    def state(self,key,**fields):
        schema=self.registry['blocks'].get(key)
        if schema is None or any(str(v).lower() not in schema.get(k,()) for k,v in fields.items()):
            raise UserError('Unregistered actual depth component '+key+' '+str(fields))
        return key+('['+','.join(k+'='+str(v).lower() for k,v in sorted(fields.items()))+']' if fields else '')
    def bounded(self,p):
        x,y,z=p
        if any(type(v) is not int for v in p):raise UserError('Exact authored depth coordinates required')
        if self.kind=='castle':ok=1170<=x<=1295 and 64<=y<=134 and -1048<=z<=-960
        else:ok=1301<=x<=1325 and 66<=y<=84 and -1009<=z<=-985
        if not ok:raise UserError('Depth component escaped its owned building envelope: '+str(p))
    def set(self,p,value,*,air_only=False,replace_glazing=False):
        self.bounded(p);old=self.actual(p);current=self.at(p)
        if p in self.snapshot.protected:raise UserError('Preserve every saved block entity: '+str(p))
        if p in self.fixed:raise UserError('Preserve a machine, route, inventory, furnishing or door: '+str(p))
        if current==value:return False
        if base(current) not in SOFT:
            if not replace_glazing:
                if not air_only and architectural(current):
                    (self.joints if p in self.blocks else self.adopted)[p]=current;return False
                # Existing genuine glazing, shutter and carved window detail
                # remains depth in its own right. No new beam may cover it.
                if not air_only and base(current).startswith('mcwwindows:'):
                    self.adopted[p]=current;return False
                raise UserError('Physical depth conflicts with retained architecture: '+str((p,current)))
            if not base(old).startswith('mcwwindows:') or p not in self.original:
                raise UserError('Only an explicitly recorded saved glazing relocation may open an old cell')
        elif replace_glazing:raise UserError('A glazing relocation lost its actual source cell')
        if p not in self.previous:self.previous[p]=old
        self.blocks[p]=value;self.groups.setdefault(self.group,set()).add(p)
        if base(old) in SOFT and base(value) not in SOFT:self.real_added.add(p)
        if len(self.blocks)>MAX_TARGETS:raise UserError('Split the bounded physical-depth layer')
        return True
    def put(self,p,key,**fields):return self.set(p,self.state(key,**fields))
    def stone(self,p):
        x,y,z=p;key=MASONRY[(1 if (y-4)%4==0 else 0)+(2 if (x-1214)%4==0 else 0)+(4 if (z+1008)%10==0 else 0)]
        return self.put(p,key)
    def stair(self,p,face,key='dawnoftimebuilder:limestone_bricks_stairs'):
        self.pending.append({'pos':list(p),'native_property':'shape','reason':'Actual native corner joining, with intended facing/half preserved'})
        return self.put(p,key,facing=face,half='top',waterlogged=False)
    def route(self,name,feet,width=1,headroom=3):
        for x,y,z in feet:
            for dx in range(-(width//2),width-width//2):
                for dy in range(-1,headroom):self.fixed.add((x+dx,y+dy,z))
            self.routes.append({'name':name,'feet':[x,y,z],'headroom_blocks':headroom})
    def feature(self,name):
        self.features.append({'group':self.group,'name':name})


def basis(center,face):
    x,y,z=center;dx,dz=NORMAL[face];tx,tz=(1,0) if dz else (0,1)
    return lambda u,dy=0,d=0:(x+tx*u+dx*d,y+dy,z+tz*u+dz*d)


def canonical_window_joins(states,targets,registry):
    """Recompute only actual ConnectedWindow parts from the final geometry.

    A saved predecessor can retain an old KNOWN_SHAPE placeholder. Carrying its
    part to a moved plane does not qualify that placeholder as canonical. The
    pinned Macaw native rule names the increasing-coordinate first edge R.
    Every identity, position, plane and other supplied property stays unchanged.
    """
    updates={};changes=[]
    for pos in sorted(targets):
        prior=states.get(pos,AIR);key=base(prior);fields=properties(prior)
        schema=registry['blocks'].get(key,{})
        if not key.startswith('mcwwindows:') or 'single_r' not in schema.get('part',()):continue
        if fields.get('facing') not in ('north','east') or 'part' not in fields:
            raise UserError('Exact native resizable window plane and part are required')
        x,y,z=pos;same=lambda q:base(states.get(q,AIR))==key
        negative,positive=((x-1,y,z),(x+1,y,z)) if fields['facing']=='north' else ((x,y,z-1),(x,y,z+1))
        part=joined_window_part(same((x,y+1,z)),same((x,y-1,z)),same(negative),same(positive))
        if part==fields['part']:continue
        if part not in schema['part']:raise UserError('Canonical native window part is unavailable')
        fields['part']=part;value=key+'['+','.join(k+'='+v for k,v in sorted(fields.items()))+']'
        updates[pos]=value;changes.append({'pos':list(pos),'before':prior,'after':value,'changed_properties':['part']})
    return updates,changes


def oriel(p,center,face,height,group,*,move=True,timber=False):
    p.group=group;q=basis(center,face);copied=[]
    if move:
        for u in (-1,0,1):
            for dy in range(height):
                pos=q(u,dy);state=p.actual(pos)
                if not base(state).startswith('mcwwindows:') or 'window' not in base(state):
                    raise UserError('A real saved complete window bay is required: '+str((pos,state)))
                copied.append((pos,q(u,dy,1),state))
        for old,new,state in copied:
            p.set(new,state,air_only=True);p.set(old,AIR,replace_glazing=True);p.relocated.add(old)
    # Continuous cheeks join the proud sill to the arched canopy. Their
    # backing remains the existing building, not a freestanding facade panel.
    for side in (-2,2):
        for dy in range(height+3):
            pos=q(side,dy,1)
            if timber:p.put(pos,'chipped:reinforced_spruce_log',axis='y')
            else:p.put(pos,'dawnoftimebuilder:limestone_sided_column',facing=face,
                       vertical_connection='under' if dy==height+2 else 'both',waterlogged=False)
        p.stair(q(side,-2,2),face,'minecraft:dark_oak_stairs' if timber else 'minecraft:quartz_stairs')
    for u in range(-2,3):
        if u==0:
            p.put(q(u,-1,2),'chipped:carved_stripped_spruce_log',axis='x' if face in ('north','south') else 'z') if timber else p.stone(q(u,-1,2))
        else:
            key='minecraft:dark_oak_slab' if timber else 'minecraft:smooth_quartz_slab' if face in ('north','south') else 'minecraft:polished_andesite_slab'
            p.put(q(u,-1,2),key,type='top',waterlogged=False)
        bottom=height if abs(u)==2 else height+1 if abs(u)==1 else height+2
        for dy in range(bottom,height+3):
            arch_face=(('east' if u<0 else 'west') if face in ('north','south') else
                       ('south' if u<0 else 'north'))
            if dy==bottom and u:p.stair(q(u,dy,2),arch_face,
                'minecraft:dark_oak_stairs' if timber else 'dawnoftimebuilder:limestone_bricks_stairs')
            elif timber:p.put(q(u,dy,2),'chipped:boxed_spruce_planks' if u==0 else 'chipped:framed_spruce_planks')
            else:p.stone(q(u,dy,2))
    p.bays.append({'group':group,'source_center':list(center),'outward':face,'window_cells_relocated':len(copied),
                   'front_glazing_depth':1 if move else 0,'corbelled_sill_and_crown_depth':2,'silhouette':'Preserved main mass with a supported shallow oriel/housing'})
    p.feature('One-block glazing recess with joined two-block corbelled sill and arched crown' if move else
              'Retained working glazing with a real two-block timber window housing')


def cornice(p,center,face,start,end,levels,group):
    p.group=group
    for y in levels:
        q=basis((center[0],y,center[1]),face)
        for u in range(start,end+1):
            back=q(u)
            if not architectural(p.at(back)):continue  # Actual apertures retain their own dressed heads.
            if u%4==0:p.stone(q(u,0,1))
            else:p.stair(q(u,0,1),face)
    p.feature('Undercut attached string course following the actual wall; apertures and existing cornices remain articulated')


def pier(p,center,face,floors,group):
    p.group=group
    for floor,top in floors:
        q=basis((center[0],floor,center[1]),face)
        for dy in range(1,top-floor+1):
            if not architectural(p.at(q(0,dy))):continue  # A portal or window is not a buttress backing.
            p.put(q(0,dy,1),'dawnoftimebuilder:limestone_sided_column',facing=face,
                  vertical_connection='under' if dy==top-floor else 'both',waterlogged=False)
        if architectural(p.at(q(0))):p.stair(q(0,0,1),face,'minecraft:quartz_stairs')
    p.feature('Corbel-rooted engaged pilaster: actual projecting column model tied to retained ashlar')


def lodge_hood(p,center,face,group,opening='door'):
    p.group=group;q=basis(center,face)
    # All three original standing/headroom cells in the door lane are retained.
    for u in (-1,0,1):
        for d in (0,1,2):
            for dy in (0,1,2):p.fixed.add(q(u,dy,d))
    for side in (-2,2):p.stair(q(side,2,1),face,'minecraft:spruce_stairs')
    for u in range(-2,3):
        for d in (1,2):
            if u==0:p.put(q(u,3,d),'chipped:reinforced_stripped_spruce_log',axis='x' if face in ('north','south') else 'z')
            else:p.put(q(u,3,d),'minecraft:dark_oak_slab',type='bottom',waterlogged=False)
    p.feature('Two-block timber '+opening+' hood with wall-rooted brackets and untouched existing opening clearance')


def castle(p):
    # Distinct oriels, not a multiplied replacement house template.
    for x,y,z,face,height,group in (
        (49,81,-33,'north',5,'Royal structure'),(25,81,-35,'north',4,'North guest wing'),
        (75,81,-25,'east',4,'Service wing'),(52,71,18,'south',5,'Ballroom and music bay'),
        (-23,80,7,'south',4,'Archive and gate ensemble')):
        oriel(p,world(x,y,z),face,height,group)
    specifications=(
        ('Royal structure',(52,-33),'north',-6,5,(77,87,97)),
        ('Royal structure',(52,-14),'south',-6,5,(77,87,97)),
        ('Royal structure',(42,-23),'west',-4,3,(77,87,97)),
        ('Royal structure',(61,-23),'east',-4,3,(77,87,97)),
        ('Grand stair rotunda',(31,-14),'west',-3,2,(77,87)),
        ('Grand stair rotunda',(38,-8),'south',-3,2,(77,87)),
        ('North guest wing',(30,-35),'north',-9,8,(77,84)),
        ('Service wing',(75,-19),'east',-6,12,(77,84)),
        ('Service wing',(68,9),'south',-4,3,(77,84)),
        ('Ballroom and music bay',(55,13),'south',-9,12,(77,84)),
        ('Archive and gate ensemble',(0,5),'south',-6,6,(83,)),
    )
    for group,(x,z),face,start,end,levels in specifications:
        cornice(p,(x+1214,z-1008),face,start,end,[y+4 for y in levels],group)
    for x,z,face in ((52,-33,'north'),(61,-23,'east'),(42,-23,'west')):
        pier(p,(x+1214,z-1008),face,((72,81),(82,91),(92,101)),'Royal structure')
    lodge_hood(p,world(-9,65,30),'east','Rosekeeper lodge')
    lodge_hood(p,world(7,65,36),'west','Candlekeeper lodge')


def mill(p):
    p.group='Copper Wren upper balcony'
    # Two existing paired attic windows become an operable, two-wide French
    # door. Every old source cell is addressed; no partial Macaw join is left.
    for x,hinge in ((1315,'left'),(1316,'right')):
        for y,half in ((76,'lower'),(77,'upper')):
            pos=x,y,-990
            if not base(p.actual(pos)).startswith('mcwwindows:dark_oak_plank_window'):
                raise UserError('Actual saved four-cell attic glazing required')
            p.set(pos,p.state('mcwdoors:dark_oak_glass_door',facing='south',half=half,
                  hinge=hinge,open=False,powered=False),replace_glazing=True)
            p.relocated.add(pos)
    # The original hall is open to its roof; the old high window had no floor
    # behind it. A supported internal ladder and guarded landing make this a
    # reachable balcony instead of putting doors above an inaccessible void.
    for y in range(68,76):
        p.put((1315,y,-991),'chipped:reinforced_stripped_spruce_log',axis='y')
        p.put((1314,y,-991),'minecraft:ladder',facing='west',waterlogged=False)
    for x in range(1315,1318):
        for z in (-992,-991):p.put((x,75,z),'chipped:boxed_spruce_planks')
        p.put((x,76,-992),'minecraft:birch_fence',waterlogged=False)
    p.put((1317,76,-991),'minecraft:birch_fence',waterlogged=False)
    p.access.append({'name':'Upper balcony ladder and guarded landing',
        'ladder_cells':[[1314,y,-991] for y in range(68,76)],
        'load_post':[[1315,y,-991] for y in range(68,76)],
        'walking_feet':[[1314,76,-991],[1315,76,-991],[1316,76,-991],
                        [1315,76,-990],[1316,76,-990],[1315,76,-989],[1316,76,-989]],
        'door_use':'Open the ordinary paired glass doors; no teleport or fabricated movement',
        'native_player_travel':'PENDING actual normal climb/walk inspection'})
    for x in range(1314,1318):
        for z in (-989,-988):
            if x==1316:p.put((x,75,z),'chipped:boxed_spruce_planks')
            else:p.put((x,75,z),'minecraft:dark_oak_slab',type='double',waterlogged=False)
        p.put((x,76,-988),'minecraft:birch_fence',waterlogged=False)
    for x in (1314,1317):
        p.put((x,76,-989),'minecraft:birch_fence',waterlogged=False)
        for z in (-989,-988):p.stair((x,74,z),'south','minecraft:spruce_stairs')
        p.put((x,77,-988),'minecraft:stripped_birch_log',axis='y')
        p.put((x,78,-988),'minecraft:dark_oak_slab',type='bottom',waterlogged=False)
        p.put((x,77,-987),'mcwlights:tavern_wall_lantern',facing='south')
    p.feature('Reachable paired attic glass doors, supported ladder, guarded interior landing, two-block balcony floor, rooted brackets and post-mounted lights')
    # This facade borders the two-wide castle-to-mill yard. Its lower volume
    # stays completely clear: articulate above the window, not across the path.
    lodge_hood(p,(1312,69,-990),'south','Copper Wren window housings',opening='window')
    p.group='Copper Wren ceiling depth'
    for x in (1313,1319):
        for z in range(-1005,-990):
            key='chipped:carved_stripped_spruce_log' if z%4==0 else 'rechiseled:spruce_planks_beams'
            p.put((x,74,z),key,**({'axis':'z'} if key.startswith('chipped:') else {}))
    p.feature('Secondary actual timber joists above the original transverse trusses; roof, chandelier and machine clearance stay intact')


def supported_geometry(p):
    # All added non-fluid geometry must have a finite face-connected route to
    # retained solid construction. This is a support-path check, not a native
    # collision model or proof that a particular decorative model looks good.
    new={q for q in p.real_added if base(p.blocks[q]) not in SOFT};remaining=set(new);queue=deque()
    def neighbors(q):
        x,y,z=q
        return ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1))
    for q in new:
        if any(base(p.blocks.get(v,p.original.get(v,AIR))) not in SOFT|{'minecraft:water'} and v not in new for v in neighbors(q)):
            remaining.remove(q);queue.append(q)
    while queue:
        for q in neighbors(queue.popleft()):
            if q in remaining:remaining.remove(q);queue.append(q)
    if remaining:raise UserError('A new depth component has no retained structural support path: '+str(sorted(remaining)[:6]))
    return new


def validate(p):
    if set(p.blocks)!=set(p.previous) or set(p.blocks)&p.fixed or set(p.blocks)&p.snapshot.protected:
        raise UserError('A fixed native block, inventory or walking envelope entered the depth layer')
    composed=p.original|p.blocks
    if p.kind=='castle':building=composed
    else:building={q:s for q,s in composed.items() if 1301<=q[0]<=1325 and -1012<=q[2]<=-985}
    rule=require_material_rule(building,'Complete '+p.kind+' including physical-depth layer')
    outside=require_outdoor_rule(composed,'Authored '+p.kind+' composition plus physical-depth layer')
    new=supported_geometry(p)
    if len(new)<60:raise UserError('A depth layer must contain actual projecting geometry, not a flat recolor')
    required=({'Royal structure','North guest wing','Service wing','Ballroom and music bay',
        'Archive and gate ensemble','Grand stair rotunda','Rosekeeper lodge','Candlekeeper lodge'}
        if p.kind=='castle' else {'Copper Wren upper balcony','Copper Wren window housings','Copper Wren ceiling depth'})
    coverage={group:len(p.groups.get(group,set())&new) for group in sorted(required)}
    if any(count<6 for count in coverage.values()):
        raise UserError('A named building mass lacks an actual new physical-depth component')
    for access in p.access:
        for q in map(tuple,access['ladder_cells']):
            if base(p.at(q))!='minecraft:ladder' or properties(p.at(q)).get('facing')!='west':
                raise UserError('The balcony lost its actual supported climbing route')
            if base(p.at((q[0]+1,q[1],q[2])))!='chipped:reinforced_stripped_spruce_log':
                raise UserError('A climbing ladder has no full retained load post')
        for q in map(tuple,access['walking_feet']):
            for dy in (0,1):
                state=p.at((q[0],q[1]+dy,q[2]));key=base(state)
                if key not in SOFT and key!='mcwdoors:dark_oak_glass_door':
                    raise UserError('The new balcony climbing exit/landing has insufficient normal headroom')
    return {'complete_building_material_rule':rule,'complete_authored_outdoor_rule':outside,
            'actual_new_occupied_positions':len(new),'removed_or_relocated_glazing_cells':len(p.relocated),
            'physical_depth_by_building_mass':coverage,
            'saved_BE_targets':0,'machine_and_route_targets':0,'unsupported_new_positions':0,
            'state_facing_is_not_a_material_break':True,'native_model_and_art_acceptance':'PENDING actual game views and normal native joins'}


def prepare(home,registry_path,backup_id,backup_sha,output):
    home,registry_path,output=(Path(v).resolve() for v in (home,registry_path,output))
    if (not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests'))
            or not output.is_relative_to(home/'staging') or output.exists()):raise UserError('Owned artistic home and NEW private output required')
    admission=guard(8*1024**2,MAX_OUTPUT)
    if digest(home/'server/mods/mcw-mcwwindows-2.4.2-mc1.21.1neoforge.jar')!=MACAW_JOIN_API_SHA:
        raise UserError('The exact pinned native Macaw joining API is required')
    registry=read_json(registry_path);receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    if receipt.get('verified') is not True or receipt.get('id')!=backup_id or receipt.get('sha256')!=backup_sha:
        raise UserError('Exact current stopped checkpoint required')
    snapshot=BackupWorld(home,receipt,registry);documents={};summaries=[]
    def emit(name,value):
        raw=(json.dumps(value,separators=(',',':'),ensure_ascii=False)+'\n').encode();documents[name]=raw
        if sum(map(len,documents.values()))>MAX_OUTPUT:raise UserError('Finite physical-depth output exceeded')
        return hashlib.sha256(raw).hexdigest()
    try:
        for kind,records in INPUTS.items():
            original={};sources=[];plans=[]
            for relative,sha in records:
                path=home/'staging'/relative
                if path.stat().st_size>16*1024**2 or digest(path)!=sha:raise UserError('Exact previously placed geometry required')
                value=read_json(path)
                if any(value[k]!=registry[k] for k in ('seed','world_path')):raise UserError('Actual source world differs')
                original.update(decode(value));plans.append(value);sources.append({'file':relative,'sha256':sha})
            fixed=set();native_changes=Counter()
            if kind=='mill':
                manifest_path=home/'staging/artistic-engineering-r2-1793106029261770100/manifest.json'
                manifest=read_json(manifest_path)
                if digest(manifest_path)!='4339bb54a05d9c5a478b471db880c7d80dc1f6c0f25081824c7c54b75f49f408':raise UserError('Exact mill operating envelope required')
                fixed=MillProtection(registry,plans[0],manifest).fixed
                collisions={tuple(v) for v in manifest['systems']['hypertube']['native_collision_cells']}
            for q,expected in original.items():
                actual=snapshot.state(q)
                if base(actual)==base(expected):continue
                if kind=='castle' and base(expected)==AIR and base(actual)=='minecraft:vine' and q in {(1182,69,-1026),(1182,70,-1026)}:
                    fixed.add(q);native_changes['Retained natural vine growth']+=1;continue
                if (kind=='mill' and base(expected)==AIR and
                    (base(actual)=='create_hypertube:tube_path' and q in collisions
                     or base(actual)=='minecraft:water' and 1306<=q[0]<=1308 and 68<=q[1]<=73 and -1001<=q[2]<=-999)):
                    fixed.add(q);native_changes[base(actual)]+=1;continue
                raise UserError('Unreviewed predecessor identity changed: '+str((q,expected,actual)))
            p=Depth(kind,registry,original,snapshot,fixed)
            if kind=='castle':
                master=read_json(home/'staging/prototype-castle-palace-e6ffcde57520b8cb/manifest.json')
                p.route('Existing authored palace circulation',[r['point'] for r in master['world_routes']],3)
                castle(p)
            else:
                # The reviewed mill routes preserve their original floor and
                # two standing/body blocks. A ceiling joist may sit above that
                # clearance; adding a third-body restriction here would invent
                # a different operating envelope from the original commission.
                for route in manifest['routes']:p.route(route['name'],route['standing_positions'],headroom=2)
                mill(p)
            updates,p.canonical_window_parts=canonical_window_joins(p.original|p.blocks,p.blocks,registry)
            p.blocks.update(updates)
            checks=validate(p)
            def payload(states,name):
                palette=sorted(set(states.values()));ids={s:n for n,s in enumerate(palette)}
                return {'format':'awft-native-settlement:1','name':name,'created':utcnow(),
                    'seed':registry['seed'],'world_path':registry['world_path'],'backup_sha256':backup_sha,
                    'bounds':[min(q[0] for q in states),min(q[2] for q in states),max(q[0] for q in states),max(q[2] for q in states)],
                    'palette':palette,'blocks':[[*q,ids[v]] for q,v in sorted(states.items())],
                    'block_entities':[],'commands':[],'landmarks':[],
                    'validation':'SEPARATE PHYSICAL-DEPTH PROPOSAL ONLY; actual preimage, native joins/readback and game art required'}
            plan_sha=emit(kind+'-depth.json',payload(p.blocks,'Physical architectural depth: '+kind))
            before_sha=emit(kind+'-depth-native-before.json',payload(p.previous,'VERIFY ONLY - exact saved physical-depth preimage'))
            summaries.append({'kind':kind,'placements':len(p.blocks),'plan_sha256':plan_sha,'before_sha256':before_sha,
                'sources':sources,'native_partial_context_preserved':dict(native_changes),'checks':checks,
                'features':p.features,'bays':p.bays,'feature_counts':{g:len(v) for g,v in p.groups.items()},
                'adopted_existing_structure':len(p.adopted),'explicit_new_component_joints':len(p.joints),
                'native_join_properties_pending':p.pending,
                'native_canonical_window_part_corrections':p.canonical_window_parts,
                'new_access_routes':p.access,
                'new_geometry_positions':sorted(map(list,p.real_added)),
                'preserved_context':'Existing R4 audience coffers, all BEs/inventories, machinery, hydraulic seals, cargo lids and circulation remain intact. No texture-only change is counted as depth.'})
        saved_sources=snapshot.sources.copy()
    finally:snapshot.close()
    manifest={'format':'awft-physical-depth-layer:1','created':utcnow(),'source_sha256':digest(Path(__file__)),
        'registry_sha256':digest(registry_path),'native_macaw_join_api_sha256':MACAW_JOIN_API_SHA,
        'checkpoint_id':backup_id,'checkpoint_sha256':backup_sha,
        'buildings':summaries,'saved_sources':saved_sources,'reserve_guard':admission,'native_actions':0,
        'world_writes':0,'entity_spawns':0,'visual_acceptance':'Pending actual graphical review; geometric support and material checks do not establish artistic quality'}
    sha=emit('manifest.json',manifest);output.mkdir()
    for name,raw in documents.items():(output/name).write_bytes(raw)
    return {'output':str(output),'manifest_sha256':sha,'buildings':[{k:v[k] for k in ('kind','placements','plan_sha256','before_sha256')} for v in summaries],'bytes':sum(map(len,documents.values())),'native_actions':0}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('home','registry','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--backup-id',required=True);p.add_argument('--backup-sha256',required=True)
    a=p.parse_args();print(json.dumps(prepare(a.home,a.registry,a.backup_id,a.backup_sha256,a.output),indent=2))
