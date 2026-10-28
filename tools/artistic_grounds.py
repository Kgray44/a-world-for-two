"""A narrow, saved-ground-verified northern town connection; no world operations."""
from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
from pathlib import Path
import subprocess

from control_room.common import UserError, digest, utcnow
from tools.artistic_street import StreetPlan, GUARD, MAX_BUNDLE, MIB
from tools.artistic_materials import require_outdoor_rule
from tools.settlement_attractions import BackupWorld


ROAD=((1193,-1203),(1195,-1208),(1202,-1213),(1205,-1217),(1207,-1220),(1218,-1220),(1221,-1223),(1221,-1226),(1223,-1228),(1223,-1240))
GROUND={'minecraft:grass_block','minecraft:dirt','minecraft:sand','minecraft:gravel','minecraft:coarse_dirt','minecraft:rooted_dirt','minecraft:stone','minecraft:clay'}
SOFT={'minecraft:air','minecraft:cave_air','minecraft:void_air','minecraft:short_grass','minecraft:tall_grass','minecraft:fern','minecraft:large_fern','minecraft:dandelion','minecraft:poppy','minecraft:cornflower','minecraft:azure_bluet','minecraft:allium','minecraft:oxeye_daisy','minecraft:dead_bush','regions_unexplored:grass_sprouts','farm_and_charm:wild_carrots','farm_and_charm:wild_barley','farm_and_charm:wild_corn'}
PAVERS=GROUND|{'minecraft:andesite','minecraft:polished_andesite','minecraft:stone_bricks','minecraft:mossy_stone_bricks','minecraft:chiseled_stone_bricks','minecraft:cobblestone','minecraft:polished_deepslate','minecraft:cobbled_deepslate'}
X_JOINTS={1199,1208,1217,1226};Z_JOINTS={-1207,-1216,-1225,-1234}


class Grounds(StreetPlan):
    def __init__(self,registry,snapshot,exclusions):
        super().__init__(registry,(0,0,0))
        self.snapshot=snapshot;self.solid=set();self.old_air=set();self.previous={};self.required_air=set();self.adopted={};self.path={};self.dry_columns={}
        self.exclusions=[]
        for name,plan,sha in exclusions:
            if 'physical_plan' in plan:plan=plan['physical_plan']
            if plan['world_path']!=registry['world_path'] or plan['seed']!=registry['seed']:raise UserError('Grounds exclusion belongs to another world')
            self.exclusions.append({'name':name,'sha256':sha})
            for x,y,z,i in plan['blocks']:
                (self.old_air if plan['palette'][i].split('[',1)[0]=='minecraft:air' else self.solid).add((x,y,z))
            self.solid.update(tuple(v['pos']) for v in plan.get('block_entities',[]))
        self.zone='Northern harbor walk and small garden pockets'

    def put(self,x,y,z,key,*,priority=50,**props):
        if not (1188<=x<=1226 and -1242<=z<=-1202 and 55<=y<=78):raise UserError('Grounds escaped its finite north-bank envelope')
        pos=x,y,z;state=self.state(key,**props);old=self.snapshot.state(pos)
        if state==old:return
        if pos in self.solid or pos in self.snapshot.protected:raise UserError('Grounds would replace an existing authored solid/BE: '+str(pos))
        oldkey=old.split('[',1)[0]
        if oldkey=='minecraft:water' or 'waterlogged=true' in old:raise UserError('Grounds must never replace water: '+str(pos))
        if oldkey not in SOFT|GROUND:raise UserError('Grounds would replace a non-natural saved object: '+str((pos,old)))
        if pos in self.old_air:self.required_air.add(pos)
        self.blocks[pos]=state;self.previous[pos]=old;self.priority[pos]=priority;self.owners[pos]=self.zone
        if key!='minecraft:air':self.uses.setdefault(key.split(':')[0],set()).add(self.zone)
        if len(self.blocks)>4096:raise UserError('Grounds exceeded finite 4096-position scope')

    def ground(self,x,z):
        for y in range(68,54,-1):
            old=self.snapshot.state((x,y,z));key=old.split('[',1)[0]
            if key in SOFT:continue
            if key=='minecraft:water' or 'waterlogged=true' in old:raise UserError('Garden/path column is wet: '+str((x,z)))
            if key not in GROUND:raise UserError('Garden column contains a retained object: '+str((x,y,z,key)))
            self.dry_columns[x,z]={'ground_y':y,'actual_block':old};return y
        raise UserError('No bounded actual native ground for a north-bank detail')

    def pave(self,x,z,f):
        # Every original authored paving block is adopted as a reference, never
        # rewritten. The headroom still has to be actual saved air/soft plants.
        pos=x,f,z;old=self.snapshot.state(pos)
        if pos in self.solid:
            if old.split('[',1)[0] not in PAVERS:raise UserError('Existing object is not an adopted full paving surface: '+str((pos,old)))
            self.adopted[pos]=old
        else:
            g=self.ground(x,z)
            if g>f or f-g>3:raise UserError('Path needs an unreviewed terrain cut/high platform: '+str((x,z,g,f)))
            for y in range(g,f):
                self.put(x,y,z,'minecraft:polished_deepslate' if x in X_JOINTS else 'minecraft:mossy_stone_bricks' if z in Z_JOINTS else 'minecraft:cobbled_deepslate')
            key='minecraft:chiseled_stone_bricks' if x in X_JOINTS and z in Z_JOINTS else 'minecraft:polished_andesite' if x in X_JOINTS else 'minecraft:stone_bricks' if z in Z_JOINTS else 'minecraft:gravel'
            self.put(x,f,z,key)
        for dy in (1,2):
            old=self.snapshot.state((x,f+dy,z))
            if old.split('[',1)[0] not in SOFT:raise UserError('Existing north path headroom is blocked: '+str((x,f+dy,z,old)))
            self.put(x,f+dy,z,'minecraft:air')
        self.path[x,z]=f

    def base(self,x,z,key='minecraft:mossy_stone_bricks'):
        g=self.ground(x,z);self.put(x,g,z,key);return g

    def signpost(self,x,z,lines):
        g=self.base(x,z)
        for dy in (1,2,3):self.put(x,g+dy,z,'minecraft:stripped_dark_oak_log',axis='y')
        self.put(x,g+4,z,'minecraft:dark_oak_slab',type='bottom',waterlogged=False)
        self.put(x,g+3,z+1,'minecraft:oak_wall_sign',facing='south',waterlogged=False)
        messages=[json.dumps(json.dumps({'text':s})) for s in (lines+['']*4)[:4]]
        self.tags[x,g+3,z+1]='{is_waxed:1b,front_text:{messages:['+','.join(messages)+'],color:"black",has_glowing_text:0b}}'
        self.put(x,g+3,z-1,'mcwlights:bell_wall_lantern',facing='north')


def construct(registry,snapshot,exclusions):
    p=Grounds(registry,snapshot,exclusions)
    for (ax,az),(bx,bz) in zip(ROAD,ROAD[1:]):
        count=max(abs(bx-ax),abs(bz-az));side=(0,1) if abs(bx-ax)>=abs(bz-az) else (1,0)
        for n in range(count+1):
            x,z=round(ax+(bx-ax)*n/max(1,count)),round(az+(bz-az)*n/max(1,count))
            for offset in (0,1):
                xx,zz=x+side[0]*offset,z+side[1]*offset
                p.pave(xx,zz,65 if zz<=-1225 else 64)
    for x in (1221,1222):
        # Two actual north-facing half steps supply the single-level rise.
        p.put(x,65,-1225,'minecraft:stone_brick_stairs',facing='north',half='bottom',shape='straight',waterlogged=False)
    p.signpost(1197,-1205,['Signal Lane ->','West Quay ->','Harbor Walk'])
    p.signpost(1216,-1217,['<- Drawbridge','Shipwright ->','Signal Lane ->'])
    # An actual seated pocket beside the path, not an unused paved plaza.
    for x in (1204,1206):
        g=p.base(x,-1210);p.put(x,g+1,-1210,'handcrafted:dark_oak_bench',facing='north',color='none',shape='single',waterlogged=False)
    g=p.base(1205,-1210);p.put(1205,g+1,-1210,'handcrafted:dark_oak_side_table');p.put(1205,g+2,-1210,'handcrafted:wood_cup',facing='north',waterlogged=False)
    for x,z in ((1203,-1209),(1204,-1209),(1205,-1209),(1206,-1209),(1207,-1209),(1203,-1208),(1207,-1208)):
        g=p.base(x,z);p.put(x,g+1,z,'minecraft:mossy_stone_brick_wall',up=True,waterlogged=False)
    for x,z,flower in ((1204,-1208,'minecraft:rose_bush'),(1206,-1208,'minecraft:lilac'),(1216,-1224,'minecraft:peony')):
        g=p.base(x,z,'minecraft:grass_block')
        for dy,half in ((1,'lower'),(2,'upper')):p.put(x,g+dy,z,flower,half=half)
    for x,z in ((1191,-1206),(1208,-1211),(1214,-1222),(1218,-1224)):
        g=p.base(x,z);p.put(x,g+1,z,'mcwlights:covered_garden_light',lit=True,powered=False)
    for x,z in ((1217,-1224),(1217,-1225)):
        g=p.base(x,z);p.put(x,g+1,z,'supplementaries:planter',extended=False,waterlogged=False);p.put(x,g+2,z,'minecraft:fern')
    for x,z in ((1189,-1204),(1190,-1204),(1191,-1204),(1189,-1205),(1189,-1206)):
        g=p.base(x,z);p.put(x,g+1,z,'mcwfences:dark_oak_picket_fence',waterlogged=False)
    check(p);return p


def check(p):
    require_outdoor_rule(p.blocks,'outdoor grounds')
    for (x,z),f in p.path.items():
        for y in (f+1,f+2):
            if p.blocks.get((x,y,z),p.snapshot.state((x,y,z)))!='minecraft:air':raise UserError('A garden detail obstructs the actual two-wide route')
    start,goal=(1193,-1203),(1223,-1240);q,seen=deque([start]),{start}
    while q and goal not in seen:
        x,z=q.popleft()
        for v in ((x-1,z),(x+1,z),(x,z-1),(x,z+1)):
            if v in p.path and v not in seen and abs(p.path[v]-p.path[x,z])<=1:seen.add(v);q.append(v)
    if goal not in seen:raise UserError('North grounds route is not connected')
    if p.blocks.keys() & p.solid:raise UserError('Grounds overwrites an authored solid')
    return {'all_authored_runs_at_most_nine':True,'connected':True,'path_columns':len(p.path),'dry_columns':len(p.dry_columns),'existing_solids_replaced':0,'existing_BEs_replayed':0,'native_walking_and_visual_acceptance':'pending'}


def prepare(home,registry_path,backup_id,backup_sha,exclude_paths,output,allowed_air_sha=None):
    home,output=Path(home).resolve(),Path(output).resolve()
    if output.drive.upper()!='D:' or output.exists() or not output.is_relative_to(Path(r'D:\A World for Two')/'staging'):raise UserError('NEW bounded D staging output required')
    if not 1<=len(exclude_paths)<=16 or any(Path(v).stat().st_size>8*MIB for v in (registry_path,*exclude_paths)):raise UserError('Finite exact authored exclusions required')
    registry=json.loads(Path(registry_path).read_text(encoding='utf-8'))
    if not Path(registry['world_path']).resolve().is_relative_to(home/'world') or not home.is_relative_to(Path(r'D:\A World for Two')/'staging'):raise UserError('Actual staging home required')
    exclusions=[(Path(v).stem,json.loads(Path(v).read_text(encoding='utf-8')),digest(Path(v))) for v in exclude_paths]
    w=BackupWorld(home,{'id':backup_id,'sha256':backup_sha,'verified':True},registry)
    try:p=construct(registry,w,exclusions);sources=w.sources.copy()
    finally:w.close()
    cells=[list(v) for v in sorted(p.required_air)];air_raw=(json.dumps(cells,separators=(',',':'))+'\n').encode();air_sha=hashlib.sha256(air_raw).hexdigest()
    if p.required_air and allowed_air_sha!=air_sha:
        return {'status':'AIR_MASK_REVIEW_REQUIRED','required_air_sha256':air_sha,'required_air_cells':cells,'placements':len(p.blocks),'saved_sources':sources,'checks':check(p)}
    g=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(GUARD),'-EstimatedCBytes','0','-EstimatedDBytes',str(MAX_BUNDLE)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,check=False);guard=json.loads(g.stdout)
    if g.returncode or not guard.get('allowed'):raise UserError('Reserve guard refused bounded grounds output')
    native=p.serialize(backup_sha);native.update(name='Northern Harbor Walk — dry town connection',bounds=[1188,-1242,1226,-1202],landmarks=[])
    data=(json.dumps(native,ensure_ascii=False,separators=(',',':'))+'\n').encode();sha=hashlib.sha256(data).hexdigest()
    before=dict(native);before['palette']=sorted(set(p.previous.values()));index={v:i for i,v in enumerate(before['palette'])};before['blocks']=[[x,y,z,index[p.previous[x,y,z]]] for x,y,z,i in native['blocks']];before['block_entities']=[];before['name']='North grounds exact saved before state'
    before_data=(json.dumps(before,separators=(',',':'))+'\n').encode()
    receipt={'format':'awft-north-grounds:1','at':utcnow(),'source_sha256':digest(Path(__file__)),'backup_id':backup_id,'backup_sha256':backup_sha,'plan_sha256':sha,'before_sha256':hashlib.sha256(before_data).hexdigest(),'placements':len(p.blocks),'new_signs':len(p.tags),'saved_sources':sources,'exclusions':p.exclusions,'reviewed_air_sha256':air_sha,'reviewed_air_cells':cells,'adopted_existing_pavers':[{'position':list(v),'actual':s} for v,s in sorted(p.adopted.items())],'checks':check(p),'storage_guard':guard,'visual_status':'Pending actual native capture and walking; no appearance acceptance inferred'}
    receipt_data=(json.dumps(receipt,sort_keys=True,indent=2)+'\n').encode()
    if len(data)+len(before_data)+len(receipt_data)>MAX_BUNDLE:raise UserError('Grounds bundle exceeds finite allocation')
    output.mkdir(parents=True,exist_ok=False);path=output/('north-harbor-walk-'+sha[:16]+'.json');path.write_bytes(data);(output/'before.json').write_bytes(before_data);(output/'manifest.json').write_bytes(receipt_data)
    return {'plan':str(path),'sha256':sha,'placements':len(p.blocks),'before':str(output/'before.json'),'visual_status':'pending'}


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__)
    for name in ('home','registry','output'):a.add_argument('--'+name,type=Path,required=True)
    a.add_argument('--backup-id',required=True);a.add_argument('--backup-sha256',required=True);a.add_argument('--exclude',type=Path,nargs='+',required=True);a.add_argument('--allow-air-sha256')
    v=a.parse_args();print(json.dumps(prepare(v.home,v.registry,v.backup_id,v.backup_sha256,v.exclude,v.output,v.allow_air_sha256),indent=2))
