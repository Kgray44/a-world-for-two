"""Original architectural depth overlays, never a world editor or native caller.

The exact completed structures remain immutable inputs. A current stopped backup
supplies every proposed preimage; no synthetic future placement is called saved.
"""
from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
from pathlib import Path
import time

from control_room.backups import Backups
from control_room.common import Layout, UserError, digest, read_json, utcnow
from tools.artistic_materials import require_material_rule, require_outdoor_rule
from tools.artistic_pirate_spit import RESERVATIONS, reserved
from tools.artistic_harbor_craft import regions as craft_regions
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld


AIR = 'minecraft:air'
VOID = {AIR, 'minecraft:cave_air', 'minecraft:void_air'}
MAX_OUTPUT = 32 * 1024**2
MAX_POSITIONS = 8_000
SPIT = 'staging/artistic-pirate-spit-byte-slots-1793124362042040500'
BASES = {
    'drowned-rose': (SPIT+'/drowned-rose-VERIFY-ONLY.json', 'f646d9ed046f603dc4e55c3f564949dba3a45be733dbd8c88ebba9cf48d85486'),
    'ninth-knot': (SPIT+'/ninth-knot.json', '731cd08a444a8b8360484856703558de39d7fd58f9ad4e7d99f7383b19adf834'),
    'pilot-tip': (SPIT+'/pilot-tip.json', 'c7fe7bd83a8738fbb4895b29a87f5f4a38ec50cd9527a14e4991edbafda8206b'),
    'lanes': (SPIT+'/lanes.json', '342e2d17d8dd6845b680459181a0938e3d0857ad71d6b1e480aed77b482d6683'),
    'east-repair': (SPIT+'/east-repair.json', '797b7cb7733ac9cac2e434013200f66d87c394adda4a7476397b920503733238'),
    'harbor': ('staging/artistic-harbor-651ac8f3e0f20997/prototype.json', 'c7b8aae43f63369cd574bbe889556c9823fd27254cfec85b6c06d1a8a8347ca1'),
    'flagship': ('staging/artistic-ship-2c8c6d503fe92246/prototype.json', 'bf8ae618cb4aadaa08fddce0d0a7a0d1901f3fc06d09e16f60184fc05f3eb48c'),
}
ENVELOPES = {
    'drowned-rose': (1287, 64, -1292, 1314, 88, -1265),
    'ninth-knot': (1276, 65, -1289, 1287, 76, -1277),
    'pilot-tip': (1308, 65, -1368, 1316, 76, -1359),
    'harbor': (1198, 62, -1258, 1223, 76, -1229),
    'flagship': (1128, 73, -1425, 1152, 79, -1401),
}
PLINTH_SUPPORTS={(1313,63,z) for z in (-1286,-1282,-1278,-1274)}
ORDINARY_GRASS_CLEARANCE={(1313,y,z):'minecraft:tall_grass[half='+half+']'
                          for z in (-1282,-1278) for y,half in ((64,'lower'),(65,'upper'))}
CRAFT_CLEARANCE=tuple(box for boxes in craft_regions().values() for box in boxes)


def key(state):
    return state.split('[', 1)[0]


def states(plan):
    palette=plan['palette']
    if len(plan['blocks'])>70_000 or len(palette)>4096:
        raise UserError('Bounded immutable base geometry required')
    result={tuple(row[:3]):palette[row[3]] for row in plan['blocks']}
    if len(result)!=len(plan['blocks']):raise UserError('Duplicate immutable base positions')
    return result


def structural(state):
    value=key(state)
    if value in VOID:return True
    if value.startswith('mcwwindows:'):return True
    return (value.startswith(('minecraft:', 'chipped:')) and
            any(token in value for token in ('planks','_log','_wood','_stairs','_slab','_bricks',
                                             'terracotta','glass','deepslate','_trapdoor','_fence')))


class DepthPlan:
    def __init__(self, registry, bases, *, protected=(), clearance=()):
        self.registry,self.bases=registry,bases
        self.all={};self.base_owner={}
        for owner,blocks in bases.items():
            for pos,state in blocks.items():
                if pos in self.all and self.all[pos]!=state:
                    raise UserError('Immutable base plans overlap with different states')
                self.all[pos]=state;self.base_owner[pos]=owner
        self.protected=set(protected);self.clearance=set(clearance)
        self.blocks={};self.owners={};self.group=None
        self.features=[];self.cameras=[]

    def state(self, value, **props):
        actual=self.registry['blocks'].get(value)
        if actual is None:raise UserError('Missing exact native architectural block: '+value)
        for name,choice in props.items():
            if name not in actual or str(choice).lower() not in actual[name]:
                raise UserError('Unsupported native architectural state: '+value+' '+name)
        return value+('['+','.join(name+'='+str(choice).lower() for name,choice in sorted(props.items()))+']' if props else '')

    def at(self,pos):
        return self.blocks.get(pos,self.all.get(pos,AIR))

    def put(self,x,y,z,value,**props):
        pos=x,y,z
        if self.group not in ENVELOPES:raise UserError('Explicit architectural owner required')
        a,b,c,d,e,f=ENVELOPES[self.group]
        if any(type(n) is not int for n in pos) or not(a<=x<=d and b<=y<=e and c<=z<=f):
            raise UserError('Depth layer exceeds its finite structure envelope: '+str(pos))
        if reserved(x,z):raise UserError('Downloaded original footprint is an exclusion')
        if any(x<box[3] and x+1>box[0] and y<box[4] and y+1>box[1] and z<box[5] and z+1>box[2]
               for box in CRAFT_CLEARANCE):
            raise UserError('Real cog/tender body, passenger and departure volumes are exclusions')
        if pos in self.protected:raise UserError('Depth layer may not rewrite an existing block entity')
        after=self.state(value,**props)
        if pos in self.clearance and key(after) not in VOID:
            raise UserError('Architectural depth obstructs protected circulation: '+str(pos))
        old=self.all.get(pos,AIR)
        other=self.base_owner.get(pos,self.group)
        if other!=self.group and key(old) not in VOID:
            raise UserError('A separate authored structure owns this target: '+str(pos))
        if not structural(old):raise UserError('Preserve existing furniture/machinery/lighting: '+str(pos)+' '+key(old))
        self.blocks[pos]=after;self.owners[pos]=self.group
        if len(self.blocks)>MAX_POSITIONS:raise UserError('Split the finite architectural depth proposal')

    def stair(self,x,y,z,facing,material='dark_oak',half='top'):
        self.put(x,y,z,'minecraft:'+material+'_stairs',facing=facing,half=half,shape='straight',waterlogged='false')

    def slab(self,x,y,z,material='dark_oak',half='top'):
        self.put(x,y,z,'minecraft:'+material+'_slab',type=half,waterlogged='false')

    def window(self,x,y,z,facing,height=3,*,gothic=False):
        for n in range(height):
            if gothic:self.put(x,y+n,z,'mcwwindows:blackstone_brick_gothic',facing=facing,open='false',
                               part='bottom' if n==0 else 'top' if n==height-1 else 'middle')
            else:self.put(x,y+n,z,'mcwwindows:dark_oak_window2',facing=facing,windowstate='closed')

    def feature(self,name,description,**evidence):
        self.features.append({'structure':self.group,'name':name,'description':description,**evidence})


def drowned_rose(p):
    p.group='drowned-rose'
    # Three actual one-block setbacks. Thick shadowed reveals replace flush
    # glazing, while all existing ribs, gallery walking and bar stock stay put.
    for z in (-1284,-1280,-1276):
        for y in range(66,70):p.put(1312,y,z,AIR)
        p.put(1311,65,z,'chipped:detailed_dark_oak_planks')
        p.window(1311,66,z,'east',4,gothic=True)
        for side in (-1,1):
            for y in range(66,70):p.stair(1312,y,z+side,'south' if side<0 else 'north','polished_blackstone_brick')
        for dz in (-1,0,1):p.slab(1312,70,z+dz,'polished_blackstone_brick')
        p.feature('Recessed sea-facing lancet','Glazing moves into the wall; carved side reveals and a projecting hood cast real shadows.',
                  original_plane_x=1312,recess_plane_x=1311,recess_blocks=1,window_bottom=[1311,66,z])
    for z in (-1286,-1282,-1278,-1274):
        for y in range(64,72):
            p.put(1313,y,z,'minecraft:polished_blackstone_bricks' if y<68 else 'minecraft:deepslate_bricks')
        p.stair(1313,72,z,'east','polished_blackstone_brick')
        p.stair(1312,73,z,'east','dark_oak')
    # Bracketed porch has no posts in the actual entrance path. Each rising
    # knee connects the solid facade to the canopy, above all body clearances.
    for x in (1298,1305):
        p.stair(x,68,-1268,'south')
        p.put(x,69,-1268,'chipped:detailed_dark_oak_planks')
        p.stair(x,69,-1267,'south')
    for x in range(1298,1306):
        rise=min(x-1298,1305-x)
        for z in (-1268,-1267,-1266):
            p.stair(x,70+rise,z,'east' if x<1302 else 'west','dark_prismarine',half='bottom')
    # Paired upper gable reveals: the original tall nave remains open behind.
    for x in (1300,1303):
        for y in range(76,79):p.put(x,y,-1269,AIR)
        p.put(x,75,-1270,'chipped:cross_laced_dark_oak_planks')
        p.window(x,76,-1270,'south',3,gothic=True)
        for dx in (-1,1):
            for y in (76,77):p.stair(x+dx,y,-1268,'east' if dx<0 else 'west','polished_deepslate')
        p.stair(x,79,-1268,'south','polished_deepslate')
    # The high nave already has four curved ship-rib vaults. Add smaller real
    # soffit coffers only under the mezzanine; do not conceal that open volume.
    for z in (-1286,-1283,-1281,-1278):
        for x in range(1308,1311):p.stair(x,68,z,'north','spruce')
    for z in (-1285,-1284,-1280,-1279):
        for x,facing in ((1308,'east'),(1310,'west')):
            if z%4==0:p.put(x,68,z,'chipped:crossed_dark_oak_planks')
            else:p.stair(x,68,z,facing,'spruce')
    p.feature('Bracketed entrance and clerestory','A three-deep small gable projects over the entry on rising timber knees; paired high lancets sit behind carved reveals.',
              canopy_z=[-1268,-1266],body_clearance_min_y=68)
    p.feature('Gallery soffit and open nave','Short stair-profile coffer rails sit below the gallery; four existing pointed nave frames and capstan remain visible.')
    p.cameras += [{'name':'rose-depth-east','feet':[1317.5,65,-1280.5],'look_at':[1312,70,-1280]},
                  {'name':'rose-depth-porch','feet':[1302.5,64,-1263.5],'look_at':[1302,75,-1269]}]


def ninth_knot(p):
    p.group='ninth-knot'
    # Window backplane inside the west wall, with a bracketed outside sill.
    for y in range(66,69):p.put(1277,y,-1284,AIR)
    p.put(1278,65,-1284,'chipped:detailed_dark_oak_planks')
    p.window(1278,66,-1284,'west',3,gothic=True)
    for z in (-1285,-1283):
        for y in (66,67,68):p.stair(1276,y,z,'south' if z==-1285 else 'north')
    p.slab(1276,65,-1284,'spruce')
    p.stair(1276,69,-1284,'west','spruce')
    # A shallow pent hood on compact diagonal knees frames the actual east
    # workroom door without building a new support in its walking threshold.
    for z in (-1285,-1281):
        p.stair(1285,67,z,'east')
        p.stair(1286,68,z,'east')
    for z in range(-1285,-1280):
        p.stair(1285,69,z,'west','dark_oak' if z==-1283 else 'spruce',half='bottom')
        p.slab(1286,69,z,'dark_oak',half='bottom')
    for z in (-1286,-1280):
        for x in range(1278,1284):
            if x==1281:p.put(x,69,z,'chipped:cross_laced_dark_oak_planks')
            else:p.stair(x,69,z,'north','jungle')
    p.feature('Net-mender recessed work light','A real one-block west setback and low corbelled sill give the loom room a deep window.',recess_blocks=1)
    p.feature('Sailmaker door hood and ceiling ribs','A shallow two-deep pent hood rests on short timber knees; two interior coffer beams frame the working bays.')


def pilot_tip(p):
    p.group='pilot-tip'
    for y in range(66,69):p.put(1311,y,-1366,AIR)
    p.put(1311,65,-1365,'chipped:detailed_dark_oak_planks')
    p.window(1311,66,-1365,'north',3,gothic=True)
    for x in (1310,1312):
        for y in (66,67,68):p.stair(x,y,-1367,'east' if x==1310 else 'west','polished_deepslate')
    p.slab(1311,69,-1367,'polished_deepslate')
    # The lantern's actual roof suspension becomes visible and supported.
    for y in (69,70,71):p.put(1310,y,-1364,'minecraft:chain',axis='y',waterlogged='false')
    for z in (-1365,-1361):
        for x in range(1309,1314):
            if x==1311:p.put(x,69,z,'chipped:crossed_dark_oak_planks')
            else:p.stair(x,69,z,'north','jungle')
    p.feature('Storm-facing pilot window','The north glazing is set back one block behind a thick, hooded stone reveal; roof members shelter the chart room.',recess_blocks=1)
    p.feature('Small shelter interior','Two short raised soffit ribs and the real three-link lantern suspension add overhead depth without lowering the central route.')


def harbor(p):
    p.group='harbor'
    # Existing west-facing workshop windows gain real backplanes and deep
    # wooden casings. Their brackets bear into the dry workshop wall, not water.
    for z in (-1237,-1232):
        back=1217 if z==-1237 else 1216
        if back==1217:
            for y in (67,68):p.put(1216,y,z,AIR)
            p.put(1217,66,z,'chipped:detailed_dark_oak_planks')
        # The second opening frames the existing pot/counter, which remain
        # exactly where they are instead of being replaced by a new sill.
        p.window(back,67,z,'west',2)
        for dz in (-1,1):
            for y in (67,68):p.stair(1215,y,z+dz,'south' if dz<0 else 'north','spruce')
        p.slab(1215,66,z,'dark_oak')
        for dz in (-1,0,1):p.stair(1215,69,z+dz,'west','dark_oak')
    for z in (-1233,-1230):
        for x in range(1217,1221):
            if x==1219:p.put(x,68,z,'chipped:crossed_dark_oak_planks')
            else:p.stair(x,68,z,'north','jungle')
    # Two under-pier knees connect existing piles/transverse beams. Nothing
    # touches the cargo passage, crane controls, craft body or departure water.
    for x in (1200,1208):
        for z in (-1256,-1252):
            p.stair(x+1,63,z,'west','spruce')
            p.stair(x-1,63,z,'east','spruce')
    p.feature('Shipwright deep casement','One native framed timber window moves behind the old face; the other retains its pot/counter and gains a projecting casing and hood.',recess_blocks=1)
    p.feature('Loft soffit and pier knees','Small coffer beams articulate the loft underside; paired structural knees sit below the existing deck, clear of hoist and boarding space.')


def flagship(p):
    p.group='flagship'
    # This vessel already has a curved hull, sheer, wales and wing galleries.
    # Concentrate new depth in its flat great-cabin front and ceiling, preserving
    # all rigging, lower hull, deck equipment, cannons and original inventories.
    for x in (-2,6):
        for y in (11,12,13):p.put(1140+x,63+y,-1422,AIR)
        p.window(1140+x,74,-1421,'north',3)
        for dx in (-1,1):
            for y in (74,75,76):p.stair(1140+x+dx,y,-1423,'east' if dx<0 else 'west','dark_oak')
        for dx in (-1,0,1):p.slab(1140+x+dx,77,-1423,'spruce')
    for z in (-1417,-1413,-1409):
        for x in range(1137,1144):
            if x==1140:p.put(x,77,z,'chipped:cross_laced_dark_oak_planks')
            else:p.stair(x,77,z,'north','spruce')
    for z in range(-1417,-1408):
        if z in (-1417,-1413,-1409):continue
        for x,facing in ((1137,'east'),(1143,'west')):
            if z%4==0:p.put(x,77,z,'chipped:crossed_dark_oak_planks')
            else:p.stair(x,77,z,facing,'spruce')
    p.feature('Great-cabin recessed lights','Two front casements move behind their original plane with carved outer pilasters and cornice; the paired entrance remains two-wide.',recess_blocks=1)
    p.feature('Captain ceiling coffers','Three short transverse coffer rails meet interrupted longitudinal rails below the quarterdeck; existing lamps and furniture remain intact.')
    p.cameras += [{'name':'ship-depth-cabin-front','feet':[1142.5,74,-1426.5],'look_at':[1138,76,-1422]},
                  {'name':'ship-depth-cabin-ceiling','feet':[1141.5,74,-1418.5],'look_at':[1140,77,-1413]}]


def build(registry,bases,*,protected=(),clearance=()):
    p=DepthPlan(registry,bases,protected=protected,clearance=clearance)
    drowned_rose(p);ninth_knot(p);pilot_tip(p);harbor(p);flagship(p)
    return p


def support_proof(p):
    # Voxel adjacency is deliberately weaker than native model/support behavior.
    # It catches floating authored groups without claiming shape survival proof.
    added={pos for pos,value in p.blocks.items() if key(value) not in VOID}
    fixed={pos for pos,value in p.all.items() if key(value) not in VOID and structural(value) and pos not in p.blocks}
    seen=set();queue=deque(pos for pos in added if any((pos[0]+dx,pos[1]+dy,pos[2]+dz) in fixed
                    for dx,dy,dz in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1))))
    seen.update(queue)
    while queue:
        x,y,z=queue.popleft()
        for dx,dy,dz in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)):
            pos=x+dx,y+dy,z+dz
            if pos in added and pos not in seen:seen.add(pos);queue.append(pos)
    if seen!=added:raise UserError('A depth assembly has no voxel support path: '+str(sorted(added-seen)[:8]))
    return {'voxel_supported_positions':len(seen),'native_shapes_and_survival':'UNVERIFIED; actual native review required'}


def validate(p):
    proofs=[]
    for owner in ENVELOPES:
        composite=dict(p.bases[owner]);composite.update({pos:value for pos,value in p.blocks.items() if p.owners[pos]==owner})
        if owner=='harbor':
            building={pos:value for pos,value in composite.items() if 1215<=pos[0]<=1223 and -1240<=pos[2]<=-1229}
        else:building=composite
        proofs.append(require_material_rule(building,owner+' complete depth composite'))
    complete=dict(p.all);complete.update(p.blocks)
    require_outdoor_rule(complete,'Every authored maritime surface after depth overlay')
    for pos in p.clearance:
        if key(p.blocks.get(pos,AIR)) not in VOID:raise UserError('Final depth layer obstructs circulation')
    return {'materials':proofs,'support':support_proof(p),'positions':len(p.blocks),'entities':0,'commands':0,
            'architectural_acceptance':'PENDING actual native support, walking and matched views'}


def payload(registry,backup_sha,blocks,name):
    palette=sorted(set(blocks.values()));lookup={value:n for n,value in enumerate(palette)}
    result={'format':'awft-native-settlement:1','name':name,'created':utcnow(),
            'seed':registry['seed'],'world_path':registry['world_path'],'backup_sha256':backup_sha,
            'bounds':[min(x for x,y,z in blocks),min(z for x,y,z in blocks),max(x for x,y,z in blocks),max(z for x,y,z in blocks)],
            'palette':palette,'blocks':[[*pos,lookup[value]] for pos,value in sorted(blocks.items())],
            'block_entities':[],'commands':[],'landmarks':[]}
    return (json.dumps(result,separators=(',',':'),ensure_ascii=False)+'\n').encode()


def admit_owner(home,owner,receipt,checkpoint_id,checkpoint_sha):
    if owner.get('format')!='awft-artistic-stage:1' or Path(owner.get('home','')).resolve()!=home:
        raise UserError('Explicit artistic ownership is required')
    pair=checkpoint_id,checkpoint_sha
    if receipt.get('verified') is not True or (receipt.get('id'),receipt.get('sha256'))!=pair:
        raise UserError('Current stopped checkpoint differs from the requested immutable read')
    if (owner.get('backup'),owner.get('backup_sha256'))!=pair:
        raise UserError('Artistic owner and stopped checkpoint are not reconciled')


def prepare(home,checkpoint_id,checkpoint_sha,output=None):
    home=Path(home).resolve();layout=Layout(home)
    if not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests')):
        raise UserError('Only the separately owned artistic staging home is admitted')
    owner=read_json(home/'dashboard/artistic-owner.json',{});receipt=read_json(home/'dashboard/settlement/backup-receipt.json',{})
    admit_owner(home,owner,receipt,checkpoint_id,checkpoint_sha)
    backups=Backups(layout,None,None);archive=backups.path(checkpoint_id)
    if digest(archive)!=checkpoint_sha:raise UserError('Stopped checkpoint archive bytes differ')
    manifest,total=backups.verify_archive(archive)
    if total>512*1024**2 or len(manifest['files'])>4096:raise UserError('Finite stopped archive admission exceeded')
    registry=read_json(home/'dashboard/settlement/registry.json')
    bases={};protected=set();source_refs={}
    for group,(relative,expected) in BASES.items():
        path=home/relative
        if path.stat().st_size>16*1024**2 or digest(path)!=expected:raise UserError('Exact completed base plan differs: '+group)
        plan=read_json(path)
        if str(plan['seed'])!=str(registry['seed']) or plan['world_path']!=registry['world_path']:
            raise UserError('Completed base belongs to another native world')
        bases[group]=states(plan);protected.update(tuple(row['pos']) for row in plan.get('block_entities',[]))
        source_refs[group]={'relative':relative,'sha256':expected}
    spit_manifest=read_json(home/SPIT/'manifest.json')
    clearance={tuple((x,y+dy,z)) for route in spit_manifest['routes'] for x,y,z in route['floor_cells'] for dy in (1,2)}
    # Existing two-wide harbor/ship circulation and live craft space are hard exclusions.
    clearance.update((x,y,z) for x in range(1202,1218) for z in (-1254,-1253) for y in (65,66))
    clearance.update((x,y,z) for x in range(1216,1221) for z in (-1235,-1234) for y in (66,67))
    clearance.update((1140+x,63+y,-1450+z) for x in (2,3) for z in range(28,46) for y in (11,12))
    p=build(registry,bases,protected=protected,clearance=clearance)
    proof=validate(p);snapshot=BackupWorld(home,receipt,registry)
    try:
        before={};supports={}
        for pos in sorted(PLINTH_SUPPORTS):
            value=snapshot.state(pos)
            if value!='minecraft:grass_block[snowy=false]' or pos in snapshot.protected:
                raise UserError('Tavern buttress needs its exact unchanged dry soil support')
            supports[pos]=value
        for pos,value in sorted(p.blocks.items()):
            old=snapshot.state(pos)
            if pos in snapshot.protected:raise UserError('Actual saved block entity is a depth exclusion: '+str(pos))
            expected=p.all.get(pos,AIR)
            if pos in p.all:
                if key(old)!=key(expected):raise UserError('Actual saved base differs at depth target: '+str(pos))
            elif key(old) not in VOID and ORDINARY_GRASS_CLEARANCE.get(pos)!=old:
                raise UserError('New depth target is not actual saved air; preserve terrain/trees/construction: '+str(pos))
            before[pos]=old
        outputs={}
        for group in sorted(ENVELOPES):
            after={pos:value for pos,value in p.blocks.items() if p.owners[pos]==group}
            outputs[group+'-depth.json']=payload(registry,checkpoint_sha,after,group+' architectural depth')
            outputs[group+'-depth-before.json']=payload(registry,checkpoint_sha,{pos:before[pos] for pos in after},group+' exact saved depth preimage')
        outputs['buttress-ground-VERIFY-ONLY.json']=payload(registry,checkpoint_sha,supports,'Unchanged dry soil under four tavern buttresses — VERIFY ONLY')
        record={'format':'awft-maritime-depth:1','status':'STAGED ONLY; no native apply or visual acceptance',
                'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'source_sha256':digest(Path(__file__)),
                'base_plans':source_refs,'sources':snapshot.sources,'features':p.features,'cameras':p.cameras,
                'craft_clearance_source_sha256':digest(Path(__file__).with_name('artistic_harbor_craft.py')),
                'proof':proof,'reservations':list(RESERVATIONS),'preservation':'No inventories, BEs, machinery, lower hull, original import plots, route body cells, terrain or entities changed.',
                'ordinary_grass_removed':[{'pos':list(pos),'saved_state':value} for pos,value in sorted(ORDINARY_GRASS_CLEARANCE.items())],
                'verification_only_files':['buttress-ground-VERIFY-ONLY.json'],
                'native_sequence':'Verify unchanged buttress soil, current native craft occupancy and every exact before plan; paired after place; settled block verification; actual walking, support and matching exterior/interior screenshots. No acceptance from block counts.',
                'files':{name:{'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)} for name,raw in outputs.items()}}
        outputs['manifest.json']=(json.dumps(record,indent=2,ensure_ascii=False)+'\n').encode()
        if sum(map(len,outputs.values()))>MAX_OUTPUT:raise UserError('Depth bundle exceeds its finite allocation')
        output=Path(output).resolve() if output else home/'staging'/('artistic-maritime-depth-'+str(time.time_ns()))
        if not output.is_relative_to(home/'staging') or output.exists():raise UserError('A new private immutable depth directory is required')
        guard(16*1024**2,MAX_OUTPUT);output.mkdir(parents=True,exist_ok=False)
        for name,raw in outputs.items():
            with (output/name).open('xb') as stream:stream.write(raw)
        return {'directory':str(output),'manifest_sha256':digest(output/'manifest.json'),'positions':len(p.blocks),'proof':proof,'files':record['files']}
    finally:snapshot.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home',type=Path,required=True);parser.add_argument('--checkpoint-id',required=True)
    parser.add_argument('--checkpoint-sha',required=True);parser.add_argument('--output',type=Path)
    args=parser.parse_args();print(json.dumps(prepare(args.home,args.checkpoint_id,args.checkpoint_sha,args.output),indent=2))
