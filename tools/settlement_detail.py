"""Prepare small architectural deltas against the exact deployed settlement.

No native command, region writer, renderer or deployment lives here. Every changed
voxel has a known previous construction state; unknown air is never permission.
The parent must freshly verify the companion precondition plan before placement.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from control_room.common import Layout, UserError, atomic_write, digest, read_json, utcnow
from control_room.storage import Storage
from tools.settlement_cinematic import (
    ACCESS_SHA, CASTLE_SHA, CORE_SHA, DRAWBRIDGE_SHA, PORT_SHA, SOUTH_SHA,
    final_harbor_geometry, verified_geometry,
)
from tools.settlement_live import native_read


AIR = 'minecraft:air'
MAX_OUTPUT_BYTES = 16 * 1024**2
MAX_POSITIONS = 40000
DISTRICTS = {'castle': (1155, -1043, 1290, -919),
             'village': (1018, -1142, 1276, -988),
             'pirate-port': (1013, -1241, 1240, -1143),
             'south-bank': (864, -1168, 1072, -944),
             'harbor-quays': (987, -1390, 1260, -1242)}
QUAY_POCKETS = (('Fish packers shade',1039),('Netmenders work stop',1075),
               ('Sea lavender resting place',1183),('Harbor dispatch shelter',1237))


def base(state):
    return state.split('[', 1)[0] if isinstance(state, str) else None


def roof(state):
    key = base(state) or ''
    return (key.startswith('mcwroofs:') and key.endswith('_roof') or
            key in {'minecraft:'+wood+'_stairs' for wood in
                    ('dark_oak', 'spruce', 'oak', 'birch', 'dark_prismarine')})


def neighbors(pos):
    x, y, z = pos
    return ((x+1,y,z),(x-1,y,z),(x,y+1,z),(x,y-1,z),(x,y,z+1),(x,y,z-1))


@dataclass
class Context:
    registry: dict
    backup: dict
    previous: dict
    sources: list = field(default_factory=list)
    protected: set = field(default_factory=set)
    headroom: set = field(default_factory=set)
    immutable: set = field(default_factory=set)
    plans: dict = field(default_factory=dict)
    south: dict = field(default_factory=dict)
    castle: dict = field(default_factory=dict)
    port: dict = field(default_factory=dict)
    tile_sources: list = field(default_factory=list)
    roof_columns: dict = field(default_factory=dict)
    air_admitted: set = field(default_factory=set)


def load_context(home, clearance_manifest=None, clearance_receipt=None):
    directory = Path(home)/'dashboard/settlement'
    registry_path, backup_path = directory/'registry.json', directory/'backup-receipt.json'
    registry, backup = read_json(registry_path), native_read(backup_path, {})
    if not backup.get('verified') or len(backup.get('sha256', '')) != 64:
        raise UserError('A current verified complete-world backup is required')
    bindings = []
    fixed = [
        ('core', 'master-'+CORE_SHA+'.json', CORE_SHA, 'core-verification-pass.json'),
        ('port', 'pirate-port-master-'+PORT_SHA+'.json', PORT_SHA, 'pirate-port-verification-pass.json'),
        ('bridge', 'drawbridge-master-'+DRAWBRIDGE_SHA+'.json', DRAWBRIDGE_SHA, 'drawbridge-block-verification.json'),
        ('castle', 'rosewater-castle-plan-'+CASTLE_SHA+'.json', CASTLE_SHA, 'rosewater-castle-'+CASTLE_SHA[:12]+'-verify.json'),
        ('south', 'south-bank-plan.json', SOUTH_SHA, 'south-bank-'+SOUTH_SHA[:12]+'-verify-shared-read.json'),
    ]
    plans = {}
    for label, name, sha, receipt in fixed:
        plan, source = verified_geometry(directory, {'path': str((directory/name).resolve()), 'sha256': sha}, sha, receipt)
        plans[label] = plan
        bindings.append((plan, source))
    vessels, marine = final_harbor_geometry(directory, native_read(directory/'grand-harbor-prepared-final.json', {}))
    bindings.extend(marine)
    ctx = Context(registry, backup, {}, plans=plans)
    for plan, source in bindings:
        if (plan['seed'], plan['world_path']) != (registry['seed'], registry['world_path']):
            raise UserError('Detail sources belong to different permanent worlds')
        ctx.previous.update({(x,y,z):plan['palette'][i] for x,y,z,i in plan['blocks']})
        ctx.protected.update(tuple(row['pos']) for row in plan.get('block_entities', []))
        ctx.sources.append(source)
    for plan in [plans['bridge'], *(v['_plan'] for v in vessels)]:
        ctx.immutable.update((x,y,z) for x,y,z,i in plan['blocks'])
    # Union historical protections; unloading a BE cannot revoke its custody.
    for path in sorted({*directory.glob('*survey*.json'), *directory.glob('terrain-before-core-*.json')}):
        if path.stat().st_size > 16*1024**2:
            raise UserError('A survey exceeds the bounded protection scan')
        survey = native_read(path, {})
        for row in survey.get('samples', []):
            ctx.protected.update(tuple(p) for p in row.get('block_entities', []))
        ctx.sources.append({'file':path.name,'sha256':digest(path),'role':'Historical BE custody'})
    ctx.south = read_json(directory/'south-bank-manifest.json')
    ctx.castle = read_json(directory/('rosewater-castle-manifest-'+CASTLE_SHA+'.json'))
    ctx.port = read_json(directory/'pirate-port-manifest.json')
    if ctx.south.get('sha256') != SOUTH_SHA or ctx.port.get('sha256') != PORT_SHA or ctx.castle.get('plan_sha256') != CASTLE_SHA:
        raise UserError('Detail lot/route metadata differs from exact deployed geometry')
    for x,y,z in ctx.south.get('walk_surface', []):
        ctx.headroom.update((x,y+n,z) for n in (1,2,3))
    for route in ctx.castle.get('routes', []):
        for x,y,z in route['standing_positions']:
            # Conservative allowance for the recorded three-wide promenades.
            ctx.headroom.update((x+dx,y+dy,z+dz) for dx in (-1,0,1)
                                for dz in (-1,0,1) for dy in (0,1,2))
    # Doors and glazing remain fixed, with a one-block buffer against new clutter.
    for pos, state in ctx.previous.items():
        key = base(state)
        if any(word in key for word in ('_door', '_window', 'glass_pane')):
            x,y,z = pos
            ctx.immutable.update((x+dx,y+dy,z+dz) for dx in (-1,0,1)
                                 for dy in (-1,0,1) for dz in (-1,0,1))
    # Inventories, signs, stations and all discovered BEs keep access and clearance.
    for x,y,z in ctx.protected:
        ctx.immutable.update((x+dx,y+dy,z+dz) for dx in (-1,0,1)
                             for dy in (-1,0,1,2) for dz in (-1,0,1))
    for label in ('castle', 'south', 'port'):
        name = {'castle':'rosewater-castle-manifest-'+CASTLE_SHA+'.json',
                'south':'south-bank-manifest.json', 'port':'pirate-port-manifest.json'}[label]
        ctx.sources.append({'file':name,'sha256':digest(directory/name),'role':'Architectural metadata and route custody'})
    ctx.sources.extend([{'file':registry_path.name,'sha256':digest(registry_path),'role':'Native blockstate palette'},
                        {'file':backup_path.name,'sha256':digest(backup_path),'role':'Current verified backup'}])
    for name in ('2_-2.png','2_-3.png'):
        path = Path(home)/'server/squaremap/web/tiles/minecraft_overworld/3'/name
        if not path.is_file():
            raise UserError('Review the actual current Squaremap overview tiles')
        ctx.tile_sources.append({'file':str(path),'sha256':digest(path),
                                 'review':'Top-down overview only; no shader or interior acceptance'})
    if clearance_manifest is not None or clearance_receipt is not None:
        admit_clearance(ctx,directory,clearance_manifest,clearance_receipt)
    return ctx


def clearance_states(ctx):
    states={};pockets=[]
    for name,center in QUAY_POCKETS:
        positions=[]
        for x in range(center-2,center+3):
            for z in (-1249,-1248):
                pos=(x,65,z);old=ctx.previous.get(pos)
                if base(old)!='minecraft:spruce_planks' or pos in ctx.immutable:
                    raise UserError('A quay pocket lacks its unchanged actual deck support: '+str(pos))
                states[pos]=old
                for y in range(66,71):
                    pos=(x,y,z)
                    if ctx.previous.get(pos,AIR)!=AIR or pos in ctx.immutable or pos in ctx.headroom:
                        raise UserError('A quay clearance probe would cross known existing construction: '+str(pos))
                    states[pos]=AIR;positions.append(list(pos))
        pockets.append({'name':name,'bounds':[center-2,66,-1249,center+2,70,-1248],
                        'air_targets':positions,'walkway_preserved':'All six rows z -1247 through -1242 remain clear'})
    return states,pockets


def admit_clearance(ctx,directory,manifest_path,receipt_path):
    if manifest_path is None or receipt_path is None:
        raise UserError('Both immutable clearance manifest and exact completed native receipt are required')
    paths=[Path(manifest_path).resolve(),Path(receipt_path).resolve()]
    if any(not p.is_relative_to(Path(directory).resolve()) for p in paths):
        raise UserError('Clearance evidence must stay in the owned settlement directory')
    manifest,proof=(native_read(p,{}) for p in paths)
    source=(paths[0].parent/manifest.get('plan_file','')).resolve()
    if source.parent!=paths[0].parent or not source.is_file() or digest(source)!=manifest.get('plan_sha256'):
        raise UserError('Clearance plan identity differs from the preserved probe')
    document=read_json(source)
    states,pockets=clearance_states(ctx)
    actual={(x,y,z):document['palette'][i] for x,y,z,i in document['blocks']}
    if actual!=states or len(document['blocks'])!=len(states) or document.get('commands') or document.get('block_entities'):
        raise UserError('The native clearance probe does not match the exact four empty pockets and supports')
    if (document.get('seed'),document.get('world_path')) != (ctx.registry['seed'],ctx.registry['world_path']):
        raise UserError('Clearance evidence belongs to another current world')
    old_backup=document.get('backup_sha256','')
    if len(old_backup)!=64 or old_backup!=manifest.get('backup_sha256') or not ctx.backup.get('verified'):
        raise UserError('Preserve the clearance probe original backup and current verified design backup')
    if (proof.get('operation')!='verify' or proof.get('plan_sha256')!=manifest['plan_sha256'] or
        proof.get('blocks')!=len(states) or proof.get('failures')!=0 or proof.get('error') or not proof.get('finished')):
        raise UserError('The exact air/support probe has not completed native verification without failures')
    ctx.air_admitted={pos for pos,state in states.items() if state==AIR}
    ctx.previous.update(states)
    ctx.sources.append({'file':source.name,'sha256':digest(source),'role':'Native air/support admission',
                        'receipt_sha256':digest(paths[1]),'finished':proof['finished'],'failures':0,
                        'new_air_positions':len(ctx.air_admitted),'probe_backup_sha256':old_backup,
                        'current_design_backup_sha256':ctx.backup['sha256'],
                        'scope':'Historical known-air receipt only; fresh full per-district preconditions verification is required before placement'})


def prepare_clearance(home,destination=None):
    layout=Layout(Path(home));ctx=load_context(layout.home)
    states,pockets=clearance_states(ctx);at=utcnow();p=DetailPlan(ctx,'harbor-quays')
    document=p.payload(states,'VERIFY ONLY: four quay pocket air clearances and actual deck supports',at)
    raw=(json.dumps(document,separators=(',',':'))+'\n').encode();sha=hashlib.sha256(raw).hexdigest()
    directory=layout.state/'settlement'
    output=directory/('detail-clearance-'+sha[:16]) if destination is None else Path(destination).resolve()
    if not output.resolve().is_relative_to(directory.resolve()) or output.exists():
        raise UserError('Preserve previous clearance probes; select a fresh private settlement directory')
    name='quay-air-clearance-'+sha+'.json'
    manifest={'format':'awft-detail-clearance-probe:1','at':at,'plan_file':name,'plan_sha256':sha,
              'operation':'verify only','world_path':ctx.registry['world_path'],'seed':ctx.registry['seed'],
              'backup_sha256':ctx.backup['sha256'],'positions':len(states),
              'unproved_air_targets':sum(v==AIR for v in states.values()),'actual_deck_supports':sum(v!=AIR for v in states.values()),
              'pockets':pockets,'provenance':ctx.sources,
              'must_never_place':'This document tests current air; it grants no permission to clear or place any block',
              'native_activation':'Not performed; return exact zero-failure native verify receipt to admit these air positions'}
    encoded=(json.dumps(manifest,indent=2)+'\n').encode()
    if len(raw)+len(encoded)>1024**2:
        raise UserError('The finite clearance probe exceeds its 1 MiB allocation')
    Storage(layout).reserve(1024**2,target=output);output.mkdir(parents=True)
    atomic_write(output/name,raw);atomic_write(output/'manifest.json',encoded)
    return {'directory':str(output),'plan':str(output/name),'sha256':sha,
            'manifest':str(output/'manifest.json'),'positions':len(states),'air_targets':200,'known_deck_supports':40,
            'native_operation':'VERIFY ONLY; never place this plan'}


class DetailPlan:
    """Transactional features: one conflict defers the whole feature, never half."""
    def __init__(self, ctx, district):
        self.ctx, self.district = ctx, district
        self.blocks, self.features, self.deferred, self.supports = {}, [], [], {}
        self.stage = None
        if not ctx.roof_columns:
            for (x,y,z),state in ctx.previous.items():
                if roof(state):
                    ctx.roof_columns.setdefault((x,z), []).append((y,state))

    def state(self, key, **properties):
        native = self.ctx.registry['blocks']
        if key not in native or properties.keys()-native[key].keys():
            raise UserError('Unknown native detail block or property: '+key)
        selected = {k:str(v).lower() for k,v in properties.items()}
        for k,v in selected.items():
            if v not in [str(n).lower() for n in native[key][k]]:
                raise UserError('Unknown native detail state: '+key+' '+k+'='+v)
        return key+('['+','.join(k+'='+v for k,v in sorted(selected.items()))+']' if selected else '')

    def put(self, x, y, z, key, *, allow=(), **properties):
        pos = (x,y,z)
        lowx,lowz,highx,highz = DISTRICTS[self.district]
        if not lowx <= x <= highx or not lowz <= z <= highz or not -64 <= y < 320:
            raise UserError('Feature exceeded its reviewed district: '+str(pos))
        old = self.ctx.previous.get(pos)
        if old is None:
            raise UserError('Unknown previous state, including unproved air: '+str(pos))
        new = self.state(key, **properties)
        if old == new:
            return
        if pos in self.ctx.protected or pos in self.ctx.immutable or pos in self.ctx.headroom:
            raise UserError('Protected inventory, route, ship, bridge, door or window: '+str(pos))
        if old != AIR and base(old) not in allow:
            raise UserError('Unreviewed cosmetic replacement: '+str(pos)+' '+old)
        if pos in self.blocks and self.blocks[pos] != new:
            raise UserError('Detail features intersect each other: '+str(pos))
        if pos in self.stage and self.stage[pos] != new:
            raise UserError('A detail feature overwrites its own design: '+str(pos))
        self.stage[pos] = new

    def support(self, pos):
        state = self.ctx.previous.get(pos)
        if state is None or base(state) in (AIR, 'minecraft:water'):
            raise UserError('Unknown or missing detail support: '+str(pos))
        self._support_stage[pos] = state

    def feature(self, name, kind, action):
        self.stage, self._support_stage = {}, {}
        try:
            action()
            pending = set(self.stage)
            while pending:
                component, queue = set(), [pending.pop()]
                rooted = False
                while queue:
                    pos = queue.pop();component.add(pos)
                    for near in neighbors(pos):
                        if near in pending:
                            pending.remove(near);queue.append(near)
                        elif near not in self.stage and base(self.ctx.previous.get(near)) not in (None, AIR, 'minecraft:water'):
                            rooted = True
                            self._support_stage[near] = self.ctx.previous[near]
                if not rooted:
                    raise UserError('A detail component has no known existing attachment')
            if not self.stage:
                raise UserError('No admitted state changes in this feature')
            if len(self.blocks.keys() | self.stage.keys()) > MAX_POSITIONS:
                raise UserError('Split the finite detail allocation')
            self.blocks.update(self.stage);self.supports.update(self._support_stage)
            xs,ys,zs = zip(*self.stage)
            self.features.append({'name':name,'kind':kind,'positions':len(self.stage),
                                  'bounds':[min(xs),min(ys),min(zs),max(xs),max(ys),max(zs)]})
            return True
        except UserError as error:
            self.deferred.append({'name':name,'kind':kind,'reason':str(error)})
            return False
        finally:
            self.stage = None

    def roof_at(self, x, z, minimum):
        choices = [(y,state) for y,state in self.ctx.roof_columns.get((x,z), []) if y >= minimum]
        if not choices:
            raise UserError('No known existing roof surface at '+str((x,z)))
        return max(choices)

    def payload(self, states, name, at):
        palette = sorted(set(states.values()));indices = {v:i for i,v in enumerate(palette)}
        positions = sorted(states, key=lambda p:(p[0]//16,p[2]//16,p[1],p[0],p[2]))
        xs,ys,zs = zip(*positions)
        if max(xs)-min(xs) > 511 or max(zs)-min(zs) > 511:
            raise UserError('Split detail districts before the 512-block native bound')
        return {'format':'awft-native-settlement:1','name':name,'created':at,
                'seed':self.ctx.registry['seed'],'world_path':self.ctx.registry['world_path'],
                'backup_sha256':self.ctx.backup['sha256'],
                'bounds':[min(xs),min(zs),max(xs),max(zs)],'palette':palette,
                'blocks':[[*p,indices[states[p]]] for p in positions],
                'block_entities':[],'commands':[],'landmarks':[],
                'coverage':{'architectural-detail':[r['name'] for r in self.features]},
                'validation':'Source/registry preflight only; native prior-state verification and 3D review required'}


def dormer(p, name, x, z, floor, inward=1, wood='dark_oak', *, halfwidth=2, form='gable'):
    """Small hipped attic dormer; native roof/window blocks, no furniture removal."""
    def action():
        y, old = p.roof_at(x,z,floor+6)
        allowed = {base(old)}
        if halfwidth not in (1,2,3) or form not in ('gable','shed'):
            raise UserError('Unreviewed dormer proportions')
        # Three widths and two roof families; their intersections follow the
        # actual existing roof height, rather than identical pasted boxes.
        for depth in range(4):
            px = x+depth*inward
            existing, state = p.roof_at(px,z,floor+6)
            allowed.add(base(state))
            edge=y+3+(depth//2 if form=='shed' else 0)
            for side in (-halfwidth,halfwidth):
                for py in range(existing+1,edge):
                    p.put(px,py,z+side,'minecraft:'+wood+'_planks',allow=allowed)
            for side in range(-halfwidth,halfwidth+1):
                py = edge if form=='shed' else y+3+halfwidth-abs(side)
                if form=='shed':
                    p.put(px,py,z+side,'mcwroofs:'+wood+'_roof',allow=allowed,
                          facing='east' if inward==1 else 'west',half='bottom',shape='straight')
                elif side:
                    p.put(px,py,z+side,'minecraft:'+wood+'_stairs',allow=allowed,
                          facing='south' if side < 0 else 'north',half='bottom',shape='straight',waterlogged=False)
                else:
                    p.put(px,py,z,'minecraft:'+wood+'_slab',allow=allowed,type='bottom',waterlogged=False)
        for side in range(-halfwidth+1,halfwidth):
            for py in range(y+1,y+4):
                key = 'minecraft:glass' if side == 0 and py < y+3 else 'minecraft:'+wood+'_planks'
                # Shed roof has its front eave at y+3, sharing no voxel with
                # the front glazing/frame. A gable fills its triangular head.
                if form!='shed' or py<y+3:
                    p.put(x,py,z+side,key,allow=allowed)
            if form=='gable':
                for py in range(y+4,y+3+halfwidth-abs(side)):
                    p.put(x,py,z+side,'minecraft:'+wood+'_planks',allow=allowed)
        p.support((x,y,z))
    return p.feature(name,f'projecting {2*halfwidth+1}-wide {form} attic dormer',action)


def rooflight(p, name, x, z, direction, minimum):
    def action():
        for depth in range(5):
            px=x+direction*depth
            for across in range(-2,3):
                py,old=p.roof_at(px,z+across,minimum)
                frame=depth in (0,4) or abs(across)==2
                if frame:
                    p.put(px,py,z+across,'minecraft:quartz_stairs',allow={base(old)},
                          facing='east' if direction == 1 else 'west',half='bottom',shape='straight',waterlogged=False)
                else:
                    p.put(px,py,z+across,'minecraft:light_blue_stained_glass',allow={base(old)})
    return p.feature(name,'framed sloping rooflight',action)


def rosette(p, name, x, y, z, masonry):
    def action():
        for dx in range(-3,4):
            for dy in range(-3,4):
                distance=abs(dx)+abs(dy)
                if distance>3:
                    continue
                key = ('minecraft:quartz_bricks' if distance == 3 else
                       'minecraft:pink_stained_glass' if distance == 2 else
                       'minecraft:light_blue_stained_glass' if distance == 1 else
                       'minecraft:magenta_stained_glass')
                p.put(x+dx,y+dy,z,key,allow=masonry)
    return p.feature(name,'rose and sea-glass gable window',action)


def chimney_crowns(p, name, bounds):
    x1,z1,x2,z2=bounds
    caps=[pos for pos,state in p.ctx.previous.items() if x1<=pos[0]<=x2 and z1<=pos[2]<=z2
          and base(state)=='minecraft:brick_slab']
    for number,pos in enumerate(sorted(caps)):
        def action(pos=pos,number=number):
            x,y,z=pos
            form=('upper','round','square')[(sum(map(ord,name))+number//2)%3]
            p.put(x,y,z,'mythrais:tudor_chimney_'+form+'_red_brick',allow={'minecraft:brick_slab'},
                  colour=0,facing='north')
            p.put(x,y+1,z,'mythrais:chimneypot_small_stone' if number%2 else 'mythrais:chimneypot_large_stone',
                  colour=0,facing='north')
            p.support((x,y-1,z))
        p.feature(name+' flue '+str(number+1),'paired sculpted chimney crowns',action)


def facade_panel(p, name, x, y, z, *, axis='z', facing='north'):
    def action():
        for offset in (-1,0,1):
            for rise in range(5):
                px,pz=(x,z+offset) if axis == 'z' else (x+offset,z)
                key=('rechiseled:quartz_block_chiseled_pillar' if abs(offset)==1 else
                     'chipped:carved_calcite' if rise in (0,4) else
                     'mythrais:tracery_panel_centre_stone' if rise==2 else 'chipped:carved_calcite')
                properties={'facing':facing,'colour':0,'shape':0} if key.startswith('mythrais:') else {}
                p.put(px,y+rise,pz,key,allow={'chipped:small_calcite_bricks'},**properties)
    return p.feature(name,'framed rose masonry relief',action)


def window_hood(p, name, x, y, z, *, facing='north', wood='spruce'):
    def action():
        for dx in (-1,0,1):
            p.put(x+dx,y,z,'mcwroofs:'+wood+'_roof',facing=facing,half='bottom',shape='straight')
            p.support((x+dx,y,z+(1 if facing == 'north' else -1)))
    return p.feature(name,'projecting timber window hood',action)


def castle_details(p):
    # Deliberately staggered groups, not a roof-wide repeating checker texture.
    for name,x,z,direction in (
        ('Library northern atlas light',1163,-1013,1),('Library southern reading light',1181,-994,-1),
        ('Ballroom sea-glass lantern',1243,-1010,1),('Ballroom evening light',1269,-1002,-1),
        ('Royal suite rooflight',1243,-985,1),('Royal bath rooflight',1269,-970,-1),
        ('Chapel lantern rooflight',1278,-962,1)):
        rooflight(p,name,x,z,direction,76)
    for name,x,y,z in (('Moonlit Library rose window',1172,90,-1022),
                        ('Library garden gable',1172,90,-984),
                        ('Ballroom north rose window',1256,91,-1028),
                        ('Royal wing south rose window',1256,91,-958)):
        rosette(p,name,x,y,z,{'chipped:small_calcite_bricks'})
    for wall,label,z_values in ((1160,'Library western',(-1014,-1007,-1000,-993)),
                                (1272,'Royal eastern',(-986,-979,-972,-965))):
        for z in z_values:
            facade_panel(p,label+' rose relief '+str(z),wall,69,z,facing='west' if wall==1160 else 'east')
    for x in (1246,1252,1258,1264):
        facade_panel(p,'Ballroom north relief '+str(x),x,69,-1028,axis='x')
    # Two intimate paved pockets away from the main three-wide promenade.
    for name,x,z,facing in (('Court west conversation seat',1200,-976,'south'),
                             ('Court east conversation seat',1227,-976,'south')):
        def action(x=x,z=z,facing=facing):
            for dx in (-1,0,1):
                p.support((x+dx,67,z))
                p.put(x+dx,68,z,'handcrafted:cherry_bench',facing=facing,
                      color='pink',shape='left' if dx == -1 else 'right' if dx == 1 else 'middle',waterlogged=False)
            p.put(x-2,68,z,'minecraft:quartz_bricks')
            p.put(x-2,69,z,'minecraft:potted_pink_tulip')
        p.feature(name,'rose-court conversation pocket',action)


def village_details(p):
    dormer(p,'Cottage lakeside paired attic bay',1152,-1088,66,1,'spruce')
    dormer(p,'Cottage garden attic bay',1174,-1077,66,-1,'spruce',halfwidth=1,form='shed')
    dormer(p,'Bramble Barn hayloft dormer',1024,-1068,76,1,'dark_oak',halfwidth=3)
    for x in (1157,1167,1177):
        window_hood(p,'Cottage lake window hood '+str(x),x,71,-1095)
    chimney_crowns(p,'Lakeside Cottage',(1149,-1095,1180,-1070))


def pirate_details(p):
    # Actual port lot rectangles are rotated 180 degrees from local authoring.
    names=set()
    for lot in p.ctx.port['lots']:
        name=lot['name'];a,b,c,d=lot['local_bounds']
        if name in names or name == 'Lanternwater quays and market' or c-a<12 or d-b<10:
            continue
        names.add(name)
        x1,x2,z1,z2=1120-c,1120-a,-1120-d,-1120-b
        center=z1+(z2-z1)//2+(2 if len(names)%2 else -2)
        if x2-x1 >=18:
            halfwidth=(2,3,1)[len(names)%3]
            dormer(p,name+' sea-facing loft',x1+3,center,lot['floor'],1,'dark_oak',
                   halfwidth=halfwidth,form='shed' if len(names)%3==0 else 'gable')
        chimney_crowns(p,name,(x1,z1,x2,z2))


def south_details(p):
    for number,lot in enumerate(p.ctx.south['lots']):
        x,z,w,d=lot['x'],lot['z'],lot['width'],lot['depth']
        if lot['role'] in ('customs','cottage','bakehouse','bindery','mill','guildhall','guesthouse','press','pottery') and w>=15:
            inward=1 if number%2 == 0 else -1
            dormer(p,lot['name']+' working attic',x+3 if inward == 1 else x+w-4,
                   z+3 if d<=11 else z+d//2,lot['floor'],inward,
                   'spruce' if number%3 else 'dark_oak',halfwidth=1 if number%3==0 else 2,
                   form='shed' if number%4==0 else 'gable')
        chimney_crowns(p,lot['name'],(x,z,x+w-1,z+d-1))
        if lot['role'] in ('customs','netter','supply','weaver','pottery','bindery','apothecary'):
            window_hood(p,lot['name']+' trade window hood',x+3,lot['floor']+5,z-1)


def quay_details(p):
    # The eight-wide promenade keeps its full solid walking plane. Dark bands
    # mark distinct loading bays and terminate at the existing mooring rhythm.
    for center,width in ((1001,3),(1028,2),(1052,3),(1081,2),(1144,3),(1177,2),(1210,3),(1241,2)):
        def action(center=center,width=width):
            for x in range(center-width//2,center+(width+1)//2):
                for z in range(-1249,-1241):
                    old=p.ctx.previous.get((x,65,z))
                    if base(old) not in ('minecraft:spruce_planks','minecraft:dark_oak_planks'):
                        raise UserError('A loading-bay band would change an existing step or crossing')
                    p.put(x,65,z,'minecraft:dark_oak_planks',allow={'minecraft:spruce_planks'})
        p.feature('Harbor loading-bay threshold '+str(center),'solid timber quay inlay',action)
    if p.ctx.air_admitted:
        for number,(name,x) in enumerate(QUAY_POCKETS):
            def action(number=number,x=x):
                for px in range(x-2,x+3):
                    for z in (-1249,-1248):
                        p.support((px,65,z))
                if number==2:
                    for dx in (-1,0,1):
                        p.put(x+dx,66,-1248,'handcrafted:dark_oak_bench',facing='south',color='blue',
                              shape='left' if dx==-1 else 'right' if dx==1 else 'middle',waterlogged=False)
                    for dx,flower in ((-2,'fern'),(2,'pink_tulip')):
                        p.put(x+dx,66,-1249,'minecraft:quartz_bricks')
                        p.put(x+dx,67,-1249,'minecraft:potted_'+flower)
                    return
                high=69 if number==3 else 70
                for dx in (-2,2):
                    for y in range(66,high-(1 if number==1 else 0)):
                        p.put(x+dx,y,-1249,'minecraft:stripped_dark_oak_log',axis='y')
                if number==1:
                    for dx in range(-2,3):
                        p.put(x+dx,69,-1249,'minecraft:dark_oak_log',axis='x')
                    p.put(x-1,68,-1249,'minecraft:chain',axis='y',waterlogged=False)
                    p.put(x-1,67,-1249,'minecraft:lantern',hanging=True,waterlogged=False)
                    p.put(x,66,-1249,'minecraft:crafting_table')
                    p.put(x+1,66,-1249,'minecraft:spruce_planks')
                    p.put(x+1,67,-1249,'minecraft:spruce_trapdoor',facing='south',half='bottom',open=False,waterlogged=False)
                else:
                    for dx in range(-2,3):
                        for z in (-1249,-1248):
                            p.put(x+dx,high,z,'minecraft:'+('blue' if number==3 else 'yellow')+'_wool'
                                  if dx in (-2,0,2) else 'minecraft:white_wool')
                    for dx in (-1,1):
                        p.put(x+dx,high-1,-1248,'minecraft:lantern',hanging=True,waterlogged=False)
                        p.put(x+dx,66,-1249,'minecraft:dark_oak_planks')
                    p.put(x,66,-1249,'minecraft:cartography_table' if number==3 else 'minecraft:spruce_planks')
                    if number==0:
                        p.put(x,67,-1249,'minecraft:potted_fern')
            p.feature(name,'native-clearance-admitted quay work/rest pocket',action)


def construct(ctx):
    plans={slug:DetailPlan(ctx,slug) for slug in DISTRICTS}
    for slug,build in (('castle',castle_details),('village',village_details),
                       ('pirate-port',pirate_details),('south-bank',south_details),('harbor-quays',quay_details)):
        build(plans[slug])
    if any(not p.blocks for p in plans.values()):
        raise UserError('Every detail district must contain an actual admitted complete feature')
    validate_independence(plans)
    return plans


def validate_independence(plans):
    owners={}
    for slug,p in plans.items():
        for pos in p.blocks:
            if pos in owners:
                raise UserError('Independent detail districts share a changed position: '+str(pos))
            owners[pos]=slug
    for slug,p in plans.items():
        for pos,old in p.supports.items():
            owner=owners.get(pos)
            if owner is not None and owner!=slug and plans[owner].blocks[pos]!=old:
                raise UserError('A district changes another district\'s native precondition attachment: '+str(pos))


def prepare(home, destination=None, *, clearance_manifest=None,clearance_receipt=None):
    layout=Layout(Path(home));ctx=load_context(layout.home,clearance_manifest,clearance_receipt);plans=construct(ctx)
    at=utcnow();documents={};districts=[]
    for slug,p in plans.items():
        plan=p.payload(p.blocks,'Architectural detail: '+slug,at)
        expected={pos:ctx.previous[pos] for pos in p.blocks}
        expected.update({pos:state for pos,state in p.supports.items() if pos not in p.blocks})
        before=p.payload(expected,'VERIFY ONLY: prior states for '+slug,at)
        raw=(json.dumps(plan,separators=(',',':'),ensure_ascii=False)+'\n').encode()
        sha=hashlib.sha256(raw).hexdigest();stem=slug+'-'+sha
        before_raw=(json.dumps(before,separators=(',',':'),ensure_ascii=False)+'\n').encode()
        before_sha=hashlib.sha256(before_raw).hexdigest()
        documents[stem+'.json']=raw;documents[stem+'-preconditions.json']=before_raw
        manifest={'format':'awft-architectural-detail:1','at':at,'district':slug,'plan_file':stem+'.json',
                  'plan_sha256':sha,'preconditions_file':stem+'-preconditions.json',
                  'preconditions_sha256':before_sha,'placements':len(p.blocks),'bounds':plan['bounds'],
                  'features':p.features,'deferred_features':p.deferred,
                  'expected_previous':[{'position':list(pos),'previous':ctx.previous[pos],'replacement':new}
                                       for pos,new in sorted(p.blocks.items())],
                  'provenance':ctx.sources,'map_review':ctx.tile_sources,
                  'protected_block_entities':len(ctx.protected),'protected_route_cells':len(ctx.headroom),
                  'commands':0,'entity_summons':0,'simulation_systems':0,'air_removals':0,
                  'preservation':'Existing BE/access, documented routes, doors/windows, all bridge and original vessel geometry fixed',
                  'required_native_order':'Fresh verify exact preconditions SHA; if zero failures, place exact plan SHA; then verify and map',
                  'status':'Private source-preflight design only; no native placement, current-state verification or 3D/shader acceptance'}
        documents[stem+'-manifest.json']=(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n').encode()
        districts.append({k:manifest[k] for k in ('district','plan_file','plan_sha256','preconditions_file',
                                                'preconditions_sha256','placements','bounds','features','deferred_features')})
    index={'format':'awft-settlement-detail-bundle:1','at':at,'districts':districts,
           'backup_sha256':ctx.backup['sha256'],'source_sha256':digest(Path(__file__)),
           'native_activation':'Not performed','shader_review':'Pending; owner is using another game'}
    documents['index.json']=(json.dumps(index,indent=2,ensure_ascii=False)+'\n').encode()
    if sum(map(len,documents.values()))>MAX_OUTPUT_BYTES:
        raise UserError('Split the detail plan and complete previous-state audit before any write')
    identity=hashlib.sha256(documents['index.json']).hexdigest()
    output=(layout.state/'settlement'/('detail-pass-'+identity[:16]) if destination is None else Path(destination).resolve())
    if not output.resolve().is_relative_to((layout.state/'settlement').resolve()) or output.exists():
        raise UserError('Use a fresh private directory inside dashboard/settlement; preserve prior evidence')
    Storage(layout).reserve(MAX_OUTPUT_BYTES,target=output)
    output.mkdir(parents=True)
    for name,raw in documents.items():
        atomic_write(output/name,raw)
    return {'directory':str(output),'districts':len(districts),'placements':sum(len(p.blocks) for p in plans.values()),
            'features':sum(len(p.features) for p in plans.values()),'index':str(output/'index.json'),
            'native_activation':'Not performed'}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--home',type=Path,default=Path(r'D:\A World for Two'))
    parser.add_argument('--destination',type=Path);parser.add_argument('--dry-run',action='store_true')
    parser.add_argument('--clearance-probe',action='store_true')
    parser.add_argument('--clearance-manifest',type=Path);parser.add_argument('--clearance-receipt',type=Path)
    args=parser.parse_args()
    if args.clearance_probe:
        print(json.dumps(prepare_clearance(args.home,args.destination),indent=2))
    elif args.dry_run:
        built=construct(load_context(args.home,args.clearance_manifest,args.clearance_receipt))
        print(json.dumps({slug:{'placements':len(p.blocks),'features':p.features,'deferred':p.deferred}
                          for slug,p in built.items()},indent=2))
    else:
        print(json.dumps(prepare(args.home,args.destination,clearance_manifest=args.clearance_manifest,
                                 clearance_receipt=args.clearance_receipt),indent=2))
