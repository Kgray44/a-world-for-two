"""Bounded dry castle walks from authenticated stopped terrain; no world actions."""
from __future__ import annotations

import argparse
from collections import deque
import hashlib
import heapq
import json
from pathlib import Path

from control_room.common import Layout, UserError, atomic_write, digest, read_json, utcnow
from control_room.storage import Storage
from tools.artistic_grounds import Grounds, GROUND, SOFT, PAVERS
from tools.artistic_materials import require_outdoor_rule
from tools.settlement_attractions import BackupWorld


BOUNDS=(1188,-1086,1304,-950)
MAX_OUTPUT=8*1024**2
CHECKPOINT_ID='20261027T093048Z-eafdca'
CHECKPOINT_SHA256='a9d481b7e48d19b449e5e3784d31f0ee5d61d119cd7124736486cbc4763bd067'
EXTRA_PAVERS={'chipped:tiled_calcite','chipped:checkered_calcite_tiles','chipped:bordered_calcite',
              'chipped:blank_calcite_carving','minecraft:stone_brick_stairs'}


class CastleWalk(Grounds):
    def __init__(self,registry,snapshot,exclusions):
        super().__init__(registry,snapshot,exclusions)
        self.zone='Castle garden arrival and dry perimeter walk'
        self.cache={};self.pads={};self.sections=[];self.stations=[]
        self.interfaces={(x,-962) for x in (1213,1214)}
        self.interfaces|={(x,z) for x in range(1259,1286) for z in (-988,-987)}
        self.interfaces|={(x,-994) for x in (1253,1254)}

    def put(self,x,y,z,key,*,priority=50,**props):
        if not(BOUNDS[0]<=x<=BOUNDS[2] and BOUNDS[1]<=z<=BOUNDS[3] and 55<=y<=80):raise UserError('Castle walk left its bounded site')
        pos=x,y,z;state=self.state(key,**props);old=self.snapshot.state(pos)
        if old==state:return
        if pos in self.solid or pos in self.old_air or pos in self.snapshot.protected:
            raise UserError('Castle walk would change an authored solid, air room or native BE: '+str(pos))
        if old.split('[',1)[0] not in SOFT|GROUND or 'waterlogged=true' in old:raise UserError('Castle walk would change retained/wet saved state: '+str((pos,old)))
        self.blocks[pos]=state;self.previous[pos]=old;self.priority[pos]=priority;self.owners[pos]=self.zone
        if len(self.blocks)>8192:raise UserError('Split the bounded castle walk')

    def ground(self,x,z):
        if (x,z) not in self.cache:
            try:self.cache[x,z]=super().ground(x,z)
            except UserError:self.cache[x,z]=None
        if self.cache[x,z] is None:raise UserError('Retained object or wet/outside ground')
        return self.cache[x,z]

    def pad(self,x,z):
        if (x,z) in self.pads:return self.pads[x,z]
        if not(BOUNDS[0]<=x<BOUNDS[2] and BOUNDS[1]<=z<BOUNDS[3]):return None
        try:
            heights=[self.ground(xx,zz) for xx in (x,x+1) for zz in (z,z+1)];floor=max(heights)
            if floor-min(heights)>1:return None
            for xx in (x,x+1):
                for zz in (z,z+1):
                    for y in range(floor,floor+4):
                        pos=xx,y,zz
                        if pos in self.solid or pos in self.old_air or pos in self.snapshot.protected:return None
                        if y>floor and self.snapshot.state(pos).split('[',1)[0] not in SOFT:return None
        except UserError:return None
        self.pads[x,z]=floor;return floor

    def route(self,start,end):
        if self.pad(*start) is None or self.pad(*end) is None:raise UserError('Road waypoint has no dry two-wide standing pad: '+str((start,end)))
        queue=[(0,start)];cost={start:0};previous={};visited=set()
        while queue:
            _,q=heapq.heappop(queue)
            if q in visited:continue
            visited.add(q)
            if q==end:break
            if len(visited)>16000:raise UserError('Dry road search exceeded its finite site')
            x,z=q;h=self.pad(x,z)
            for v in ((x+1,z),(x-1,z),(x,z+1),(x,z-1)):
                f=self.pad(*v)
                if f is None or abs(f-h)>1:continue
                score=cost[q]+1+abs(f-h)*3
                if score>=cost.get(v,10**9):continue
                cost[v]=score;previous[v]=q
                heapq.heappush(queue,(score+abs(v[0]-end[0])+abs(v[1]-end[1]),v))
        if end not in visited:raise UserError('No actual dry two-wide route between '+str((start,end)))
        nodes=[end]
        while nodes[-1]!=start:nodes.append(previous[nodes[-1]])
        nodes.reverse()
        for x,z in nodes:
            for xx in (x,x+1):
                for zz in (z,z+1):self.path[xx,zz]=max(self.path.get((xx,zz),55),self.pad(x,z))
        self.sections.append({'start':list(start),'end':list(end),'nodes':len(nodes),'maximum_grade':1})

    def pave(self,x,z,f):
        old=self.snapshot.state((x,f,z))
        if (x,f,z) in self.solid:
            if (x,z) not in self.interfaces or old.split('[',1)[0] not in PAVERS|EXTRA_PAVERS:raise UserError('No reviewed outdoor paving interface: '+str((x,f,z)))
            self.adopted[x,f,z]=old
        else:
            g=self.ground(x,z)
            if g>f or f-g>3:raise UserError('Unreviewed terrain cut or high retaining wall')
            for y in range(g,f):self.put(x,y,z,'minecraft:mossy_stone_bricks' if y%4 else 'minecraft:polished_andesite')
            key='minecraft:polished_andesite' if x%8==0 and z%8==0 else 'minecraft:gravel' if x%8==0 else 'minecraft:cobblestone' if z%8==0 else 'minecraft:dirt_path'
            self.put(x,f,z,key)
        for y in (f+1,f+2):
            if self.snapshot.state((x,y,z)).split('[',1)[0] not in SOFT:raise UserError('Road headroom occupied')
            self.put(x,y,z,'minecraft:air')
        self.path[x,z]=f

    def station(self,x,z,lines):
        # No fallback edits: a whole pocket is omitted if retained objects,
        # water, a room mask or the route occupies any part of its small group.
        footprint={(x+dx,z+dz) for dx in range(-1,3) for dz in range(-1,3)}
        if footprint&self.path.keys():return
        try:
            floors={v:self.ground(*v) for v in footprint}
            if max(floors.values())-min(floors.values())>1:return
            for xx,zz in footprint:
                for y in range(floors[xx,zz],floors[xx,zz]+5):
                    if (xx,y,zz) in self.solid|self.old_air|self.snapshot.protected:return
                    if y>floors[xx,zz] and self.snapshot.state((xx,y,zz)).split('[',1)[0] not in SOFT:return
        except UserError:return
        g=floors[x,z];self.put(x,g,z,'minecraft:polished_andesite')
        self.put(x,g+1,z,'handcrafted:cherry_bench',facing='south',color='pink',shape='single',waterlogged=False)
        gg=floors[x+1,z];self.put(x+1,gg,z,'minecraft:gravel');self.put(x+1,gg+1,z,'handcrafted:cherry_side_table')
        self.put(x+1,gg+2,z,'minecraft:potted_pink_tulip')
        sg=floors[x,z+1]
        for dy in (0,1,2):self.put(x,sg+dy,z+1,'minecraft:stripped_dark_oak_log',axis='y')
        self.put(x,sg+3,z+1,'mcwlights:tavern_lantern',hanging=False,waterlogged=False)
        self.put(x,sg+2,z+2,'minecraft:oak_wall_sign',facing='south',waterlogged=False)
        msgs=[json.dumps(json.dumps({'text':s})) for s in (lines+['']*4)[:4]]
        self.tags[x,sg+2,z+2]='{is_waxed:1b,front_text:{messages:['+','.join(msgs)+'],color:"black",has_glowing_text:0b}}'
        self.stations.append({'position':[x,g+1,z],'lines':lines})


def construct(registry,snapshot,exclusions):
    p=CastleWalk(registry,snapshot,exclusions)
    points=[(1192,-1084),(1244,-1064),(1288,-1048),(1296,-1018),(1296,-956),(1213,-958)]
    for a,b in zip(points,points[1:]):p.route(a,b)
    # Exact existing primary gate interface, with two ordinary half-step rises.
    for z,f in ((-959,66),(-960,67),(-961,68),(-962,68)):
        for x in (1213,1214):p.path[x,z]=f
    # A real lower court entry, reached around the outside of the ballroom.
    for x in range(1286,1297):
        for z in (-988,-987):p.path[x,z]=68 if x==1286 else 67 if x==1287 else 66 if x==1288 else 65
    for x in range(1253,1286):
        for z in (-988,-987):p.path[x,z]=68
    for z in range(-994,-987):
        for x in (1253,1254):p.path[x,z]=68
    for (x,z),f in list(p.path.items()):p.pave(x,z,f)
    # Stairs face the next higher tread, preserving a clear two-wide corridor.
    for (x,z),f in p.path.items():
        if (x,f,z) in p.solid:continue
        higher=[(dx,dz) for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)) if p.path.get((x+dx,z+dz))==f+1]
        if higher:
            dx,dz=higher[0];face='east' if dx==1 else 'west' if dx==-1 else 'south' if dz==1 else 'north'
            p.put(x,f,z,'minecraft:stone_brick_stairs',facing=face,half='bottom',shape='straight',waterlogged=False)
    for x,z,lines in [(1204,-1073,['Rosewater Palace','Garden walk ->','<- Drawbridges']),
                       (1265,-1054,['Rosewater Palace','South gate ->','Garden court ->']),
                       (1299,-1004,['Castle gardens','Follow the shore','South gate ->']),
                       (1246,-954,['<- Palace gate','Garden court ->','Rosewater Walk'])]:p.station(x,z,lines)
    require_outdoor_rule(p.blocks,'Castle arrival walk')
    start=(1192,-1084);todo=deque([start]);seen={start}
    while todo:
        x,z=todo.popleft()
        for q in ((x+1,z),(x-1,z),(x,z+1),(x,z-1)):
            if q in p.path and q not in seen and abs(p.path[q]-p.path[x,z])<=1:seen.add(q);todo.append(q)
    if not {(1213,-962),(1253,-994)}<=seen:raise UserError('Castle gate/court is not linked by ordinary steps')
    for (x,z),f in p.path.items():
        for y in (f+1,f+2):
            if p.blocks.get((x,y,z),snapshot.state((x,y,z)))!='minecraft:air':raise UserError('Detail blocks the walk')
    return p


def prepare(home,output,exclude,checkpoint_id=CHECKPOINT_ID,checkpoint_sha256=CHECKPOINT_SHA256):
    home,output=Path(home).resolve(),Path(output).resolve()
    if not home.is_relative_to(Path(r'D:\A World for Two\staging')) or not output.is_relative_to(home/'staging') or output.exists():raise UserError('Unique private staging output required')
    registry=read_json(home/'dashboard/settlement/registry.json');receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    if receipt.get('id')!=checkpoint_id or receipt.get('sha256')!=checkpoint_sha256:raise UserError('Stopped checkpoint changed; require an explicit fresh binding before preparation')
    exclusions=[(str(Path(v)),read_json(Path(v)),digest(Path(v))) for v in exclude]
    w=BackupWorld(home,receipt,registry)
    try:p=construct(registry,w,exclusions);sources=w.sources[:]
    finally:w.close()
    value=p.serialize(receipt['sha256']);value.update(name='Rosewater Palace — actual dry garden arrival',bounds=list(BOUNDS),landmarks=[])
    raw=(json.dumps(value,separators=(',',':'))+'\n').encode();sha=hashlib.sha256(raw).hexdigest()
    old=value|{'name':'Exact stopped preimage — Rosewater garden arrival','palette':sorted(set(p.previous.values())),'block_entities':[]}
    ix={v:i for i,v in enumerate(old['palette'])};old['blocks']=[[*q,ix[v]] for q,v in sorted(p.previous.items())]
    before=(json.dumps(old,separators=(',',':'))+'\n').encode()
    manifest={'format':'awft-castle-arrival:1','at':utcnow(),'source_sha256':digest(Path(__file__)),'checkpoint_id':receipt['id'],'checkpoint_sha256':receipt['sha256'],'plan_sha256':sha,'before_sha256':hashlib.sha256(before).hexdigest(),'placements':len(p.blocks),'path_columns':len(p.path),'stations':p.stations,'sections':p.sections,'exclusions':p.exclusions,'existing_pavers_adopted_without_mutation':len(p.adopted),'authored_solids_airrooms_or_BEs_replaced':0,'all_authored_runs_at_most_nine':True,'route':'East arrival uses the existing fixed Rosebridge to its western landing and existing south bank stairs; new dry walk skirts the north/east shore, then reaches the real south gate and rose court. No nonexistent NE door claimed.','sources':sources,'native_walking_and_visual_acceptance':'pending'}
    meta=(json.dumps(manifest,indent=2)+'\n').encode()
    if len(raw)+len(before)+len(meta)>MAX_OUTPUT:raise UserError('Bounded castle walk output exceeded')
    Storage(Layout(home)).reserve(MAX_OUTPUT,target=output);output.mkdir(parents=True)
    for name,data in (('prototype.json',raw),('before.json',before),('manifest.json',meta)):atomic_write(output/name,data)
    return {'plan':str(output/'prototype.json'),'sha256':sha,'before_sha256':manifest['before_sha256'],'placements':len(p.blocks),'path_columns':len(p.path),'stations':len(p.stations),'native_action':'not performed'}


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--home',type=Path,required=True);a.add_argument('--output',type=Path,required=True);a.add_argument('--exclude',type=Path,nargs='+',required=True)
    a.add_argument('--checkpoint-id',default=CHECKPOINT_ID);a.add_argument('--checkpoint-sha256',default=CHECKPOINT_SHA256)
    print(json.dumps(prepare(**vars(a.parse_args())),indent=2))
