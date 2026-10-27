"""An authored, saved-state-bound finish for Rosewater's audience chamber.

Only new private proposal/preimage files are emitted. This module never starts a
game, issues a command, edits an active world or qualifies its own appearance.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from control_room.common import UserError, digest, read_json, utcnow
from tools.artistic_materials import require_material_rule
from tools.playtest import guard
from tools.settlement_attractions import AIR, BackupWorld, base, properties


PALACE_PLAN_SHA = 'e6ffcde57520b8cb75798548ce6f8683f147c8b47f05d5bc3c9be46746159931'
PALACE_MANIFEST_SHA = '0804d6fa1d67082907f84c5e1671601ff1061d8d3c5d83bfe94ab394e581e082'
BOUNDS = (1257, 73, -1040, 1274, 81, -1023)
MAX_TARGETS = 1600
MAX_OUTPUT = 8*1024**2
FIXED_FAMILIES = ('mcwwindows:', 'mcwdoors:', 'mcwlights:', 'handcrafted:',
                  'supplementaries:', 'xercamusic:', 'create:', 'railways:')


def decode(plan):
    return {tuple(row[:3]): plan['palette'][row[3]] for row in plan['blocks']}


def state(registry, key, **fields):
    native = registry['blocks'].get(key)
    if native is None:
        raise UserError('Unregistered actual audience-chamber material: '+key)
    for name, value in fields.items():
        if str(value).lower() not in native.get(name, ()):
            raise UserError('Unregistered exact audience-chamber state: '+key+' '+name+'='+str(value))
    return key+('['+','.join(k+'='+str(v).lower() for k,v in sorted(fields.items()))+']' if fields else '')


class Interior:
    def __init__(self, registry, original, snapshot=None):
        self.registry, self.original, self.snapshot = registry, original, snapshot
        self.blocks, self.previous, self.groups, self.features = {}, {}, {}, []
        self.family = 'Audience chamber'
        self.fixed = {p for p,v in original.items() if base(v).startswith(FIXED_FAMILIES)
                      or base(v) in ('minecraft:chain', 'minecraft:chest', 'minecraft:barrel',
                                     'minecraft:lectern', 'minecraft:enchanting_table')
                      or base(v).endswith(('_wall_banner', '_door', '_bed'))}
        # Keep the paired throne seats/backings and raised dais unchanged. The
        # ceiling articulation frames this existing focal point from above.
        self.fixed.update((x,y,z) for x in range(1261,1272) for y in range(73,79)
                          for z in range(-1040,-1036))
        self.routes = [
            {'name':'Processional runner', 'feet':(x,74,z)}
            for x in range(1263,1270) for z in range(-1035,-1023)]
        self.routes += [
            {'name':'Eastern gallery connection', 'feet':(x,74,z)}
            for x in range(1270,1275) for z in range(-1033,-1029)]
        self.routes += [
            {'name':'Western rotunda threshold', 'feet':(x,74,z)}
            for x in range(1257,1260) for z in range(-1027,-1023)]
        for route in self.routes:
            x,y,z=route['feet']
            self.fixed.update((x,y+dy,z) for dy in (-1,0,1))

    def actual(self, p):
        return self.snapshot.state(p) if self.snapshot else self.original.get(p, AIR)

    def put(self, x,y,z,key, *, overlay=False, **fields):
        p=(x,y,z)
        if any(type(v) is not int or not BOUNDS[n]<=v<=BOUNDS[n+3] for n,v in enumerate(p)):
            raise UserError('Interior detail escaped the reviewed audience chamber: '+str(p))
        if p not in self.original:
            raise UserError('No exact authored palace predecessor: '+str(p))
        if p in self.fixed:
            raise UserError('Preserve throne, furnishing, light, glazing or circulation: '+str(p))
        old=self.actual(p)
        if self.snapshot and p in self.snapshot.protected:
            raise UserError('Preserve existing saved block entity: '+str(p))
        planned=self.original[p]
        if base(old)!=base(planned) or any(properties(old).get(k)!=v for k,v in properties(planned).items()):
            raise UserError('The saved architectural predecessor changed: '+str(p))
        value=state(self.registry,key,**fields)
        if p in self.blocks and self.blocks[p]!=value and not overlay:
            raise UserError('Two new detail families overlap without an explicit design joint: '+str(p))
        if value==old:
            return
        self.blocks[p],self.previous[p]=value,old
        self.groups.setdefault(self.family,set()).add(p)
        if len(self.blocks)>MAX_TARGETS:
            raise UserError('Split the bounded audience-chamber finish')

    def fresh(self, x,y,z,key, **fields):
        if base(self.actual((x,y,z)))!=AIR:
            raise UserError('New decoration requires saved air: '+str((x,y,z)))
        self.put(x,y,z,key,**fields)

    def stair(self,x,y,z,facing,**extra):
        self.put(x,y,z,'dawnoftimebuilder:limestone_bricks_stairs',facing=facing,
                 half='top',shape='straight',waterlogged=False,**extra)


def coffered_soffit(p):
    p.family='Joined timber coffers, ivory recesses and carved bosses'
    # Full timber frames sit below the original unmodified upper floor. Their
    # three-block members meet carved joints, rather than one long brown slab.
    for z in (-1039,-1035,-1031,-1027,-1023):
        for x in range(1258,1274):
            q=(x,81,z)
            if q not in p.original or base(p.original[q])!=AIR or q in p.fixed:
                continue  # Exact octagonal wall/retained chandelier, not a hole.
            key='chipped:engraved_calcite' if (x-1258)%4==3 else 'rechiseled:dark_oak_planks_beams'
            p.put(*q,key)
    for x in (1258,1262,1270,1273):
        for z in range(-1038,-1023):
            q=(x,81,z)
            if q not in p.original or base(p.original[q])!=AIR or q in p.fixed or q in p.blocks:
                continue
            key='chipped:inlayed_calcite' if (z+1039)%4==0 else 'rechiseled:spruce_planks_beams'
            p.put(*q,key)
    # Shallow pale panels are recessed half a block above the full frame's
    # underside. Small separated 2x2 fields preserve the ceiling's timber rhythm.
    for cx in (1259,1263,1271):
        for cz in (-1038,-1034,-1030,-1026):
            for x in (cx,cx+1):
                for z in (cz,cz+1):
                    q=(x,81,z)
                    if q in p.original and base(p.original[q])==AIR and q not in p.fixed and q not in p.blocks:
                        p.put(*q,'minecraft:smooth_quartz_slab',type='top',waterlogged=False)
    p.features.append('A real shallow coffered soffit: joined timber members, ivory recessed panels and separate carved joints; existing upper floor and chandelier remain intact')


def ribbed_arches(p):
    p.family='Three-dimensional limestone springers and paired audience arches'
    # Two complete transverse arches frame the audience zone and its entrance.
    # The central chandelier hangs between them; its native mount is untouched.
    for z in (-1037,-1025):
        for x in range(1258,1274):
            distance=min(x-1258,1273-x)
            y=78 if distance==0 else 79 if distance<=2 else 80 if distance<=4 else 81
            if (x,y,z) in p.fixed:
                continue
            if distance>=5:
                key='chipped:engraved_calcite' if x in (1264,1267) else 'chipped:inlayed_calcite'
                p.put(x,y,z,key,overlay=True)
            else:
                p.stair(x,y,z,'east' if x<1266 else 'west',overlay=True)
        for x,face in ((1258,'east'),(1273,'west')):
            for y in (76,77):
                p.fresh(x,y,z,'dawnoftimebuilder:limestone_sided_column',facing=face,
                        vertical_connection='both' if y==76 else 'under',waterlogged=False)
            # An engaged pendant springer reaches its actual masonry backing;
            # it is not a freestanding floating column. Keep an existing solid
            # backing at the chamfered corner rather than repainting it.
            anchor=(x-1 if x==1258 else x+1,77,z)
            if base(p.original.get(anchor,AIR))==AIR:
                p.fresh(*anchor,'chipped:engraved_calcite')
    p.features.append('Two shaped audience arches with engaged springers and a stepped curved profile; no new pillar occupies the procession or gallery connection')


def textiles_and_wall_bays(p):
    p.family='Rose and gold textile bays and layered wall-side cornices'
    # Tied side panels leave the central throne and its actual glazing visible.
    for x in (1259,1272):
        for y in range(75,79):
            p.fresh(x,y,-1038,'mcwwindows:pink_curtain',facing='south',
                    tied='half_single' if y==75 else 'single' if y==76 else 'none')
        p.fresh(x,79,-1038,'mcwwindows:golden_curtain_rod',facing='south')
        p.stair(x,80,-1038,'south')
    # Small wall-side bracket pairs give each tall elevation a human-scale bay.
    # Their top slabs are structural shelves; ornaments rest directly on them.
    for x,z,face in ((1257,-1036,'east'),(1273,-1036,'west'),(1273,-1027,'west')):
        p.fresh(x,76,z,'minecraft:polished_diorite_slab',type='top',waterlogged=False)
        p.fresh(x,77,z,'minecraft:potted_flowering_azalea_bush')
        p.stair(x,75,z,face)
    p.features.append('Actual tied rose curtains, golden rods, layered corbels and stable potted flowering shrubs; all original banner/light block entities are preserved')


def inhabited_edges(p):
    p.family='Reachable archive, tea and writing corners'
    for x,z,face in ((1258,-1034,'east'),(1258,-1030,'east')):
        p.fresh(x,73,z,'handcrafted:cherry_cupboard',facing=face,type=1)
    p.fresh(1258,74,-1034,'handcrafted:terracotta_bowl',facing='east',pieces=3,waterlogged=False)
    p.fresh(1258,74,-1030,'handcrafted:stackable_book',facing='east',books=3,seed=4)
    p.fresh(1260,73,-1030,'handcrafted:cherry_side_table',facing='east',color='white',waterlogged=False)
    p.fresh(1260,74,-1030,'mcwlights:golden_low_candle_holder',lit=True)
    for z in (-1028,-1027):
        p.fresh(1273,73,z,'handcrafted:cherry_side_table',facing='west',color='white',waterlogged=False)
    p.fresh(1273,74,-1028,'handcrafted:white_plate',facing='west',pieces=3,waterlogged=False)
    p.fresh(1273,74,-1027,'handcrafted:berry_jam_jar',facing='west',jars=2,waterlogged=False)
    p.features.append('Low fitted book cupboards, a candlelit side desk and a laid refreshment corner keep daily activity at the room edges while its main aisle stays open')


def construct(registry,source,snapshot=None):
    p=Interior(registry,decode(source),snapshot)
    coffered_soffit(p);ribbed_arches(p);textiles_and_wall_bays(p);inhabited_edges(p)
    validate(p)
    return p


def validate(p):
    if set(p.blocks)!=set(p.previous) or set(p.blocks)&p.fixed:
        raise UserError('Exact preimage custody or a fixed operating envelope was lost')
    if p.snapshot and set(p.blocks)&p.snapshot.protected:
        raise UserError('An existing saved block entity entered the placement delta')
    composed=p.original|p.blocks
    checks=require_material_rule(composed,'Complete authored palace including the audience-chamber finish')
    for route in p.routes:
        x,y,z=route['feet']
        for dy in (-1,0,1):
            if composed.get((x,y+dy,z),AIR)!=p.original.get((x,y+dy,z),AIR):
                raise UserError('An audience, rotunda or gallery route changed')
    return {'complete_palace_material_rule':checks,'existing_furnishing_and_route_targets':0,
            'saved_block_entity_targets':0,'commands':0,'visual_acceptance':'Pending actual native shader inspection'}


def payload(p,states,backup_sha,name):
    palette=sorted(set(states.values()));ids={v:n for n,v in enumerate(palette)}
    return {'format':'awft-native-settlement:1','name':name,'created':utcnow(),
            'seed':p.registry['seed'],'world_path':p.registry['world_path'],'backup_sha256':backup_sha,
            'bounds':[BOUNDS[0],BOUNDS[2],BOUNDS[3],BOUNDS[5]],'palette':palette,
            'blocks':[[*q,ids[v]] for q,v in sorted(states.items())],
            'block_entities':[],'commands':[],'landmarks':[],
            'validation':'PROPOSAL ONLY; exact current native preimage/placement/readback and graphical review remain required'}


def prepare(home,registry_path,source_path,manifest_path,backup_id,backup_sha,output):
    home,registry_path,source_path,manifest_path,output=map(lambda x:Path(x).resolve(),
        (home,registry_path,source_path,manifest_path,output))
    if (not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests'))
            or not output.is_relative_to(home/'staging') or output.exists()):
        raise UserError('Use a separate artistic home and a unique private proposal directory')
    if not re.fullmatch(r'\d{8}T\d{6}Z-[a-f0-9]{6}',backup_id) or not re.fullmatch('[a-f0-9]{64}',backup_sha):
        raise UserError('An exact explicitly verified stopped checkpoint is required')
    if digest(source_path)!=PALACE_PLAN_SHA or digest(manifest_path)!=PALACE_MANIFEST_SHA:
        raise UserError('The exact current authored palace master is required')
    if any(x.stat().st_size>16*1024**2 for x in (registry_path,source_path,manifest_path)):
        raise UserError('Bounded actual registry and source geometry are required')
    reserve=guard(4*1024**2,MAX_OUTPUT)
    registry,source=read_json(registry_path),read_json(source_path)
    if any(str(source[k])!=str(registry[k]) for k in ('seed','world_path')) or not Path(registry['world_path']).resolve().is_relative_to(home/'world'):
        raise UserError('Source and registry world identity differ')
    receipt={'verified':True,'id':backup_id,'sha256':backup_sha}
    snapshot=BackupWorld(home,receipt,registry)
    try:
        p=construct(registry,source,snapshot)
        sources=snapshot.sources.copy()
        protected=len(snapshot.protected)
    finally:snapshot.close()
    documents={}
    def emit(name,value):
        raw=(json.dumps(value,separators=(',',':'),ensure_ascii=False)+'\n').encode()
        documents[name]=raw
        return hashlib.sha256(raw).hexdigest()
    after=emit('castle-interior.json',payload(p,p.blocks,backup_sha,'Rosewater audience chamber: ribbed ivory and timber finish'))
    before=emit('native-before.json',payload(p,p.previous,backup_sha,'VERIFY ONLY - exact saved audience-chamber finish preimage'))
    current=read_json(home/'dashboard/settlement/backup-receipt.json',{})
    details={'format':'awft-artistic-castle-interior:1','created':utcnow(),'source_sha256':digest(Path(__file__)),
             'registry_sha256':digest(registry_path),'palace_plan_sha256':PALACE_PLAN_SHA,'palace_manifest_sha256':PALACE_MANIFEST_SHA,
             'checkpoint_id':backup_id,'checkpoint_sha256':backup_sha,'checkpoint_is_current':current.get('id')==backup_id and current.get('sha256')==backup_sha,
             'plan_sha256':after,'before_sha256':before,'placements':len(p.blocks),'block_entities_loaded':0,
             'existing_saved_block_entities_preserved':protected,'features':p.features,'checks':validate(p),
             'groups':{k:len(v) for k,v in p.groups.items()},'block_counts':dict(Counter(base(v) for v in p.blocks.values())),
             'changes':[{'pos':list(q),'old':p.previous[q],'new':v} for q,v in sorted(p.blocks.items())],
             'operating_routes':p.routes,'saved_sources':sources,'reserve_guard':reserve,
             'cameras':[{'name':'Matching audience arrival','feet':[1266,74,-1025],'look_at':[1266,77,-1038]},
                        {'name':'Vault and throne setting','feet':[1268,75,-1029],'look_at':[1264,80,-1036]},
                        {'name':'Archive and tea edges','feet':[1265,74,-1030],'look_at':[1258,74,-1033]}],
             'scope':'Proposal only; reprepare against the parent-reviewed current stopped checkpoint before fresh native admission; no game or world actions performed'}
    manifest_sha=emit('manifest.json',details)
    if sum(map(len,documents.values()))>MAX_OUTPUT:
        raise UserError('Proposal output exceeds its finite allocation')
    output.mkdir(parents=True,exist_ok=False)
    for name,raw in documents.items():(output/name).write_bytes(raw)
    return {'output':str(output),'manifest_sha256':manifest_sha,'plan_sha256':after,'before_sha256':before,
            'placements':len(p.blocks),'bytes':sum(map(len,documents.values())),'native_actions':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('home','registry','source','manifest','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--backup-id',required=True);parser.add_argument('--backup-sha256',required=True)
    a=parser.parse_args()
    print(json.dumps(prepare(a.home,a.registry,a.source,a.manifest,a.backup_id,a.backup_sha256,a.output)))
