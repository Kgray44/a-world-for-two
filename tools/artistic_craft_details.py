"""Small screenshot-led craft-lane lighting, planting and trade-detail delta."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from control_room.common import UserError, digest, utcnow
from tools.artistic_craft_lane import construct as lane, CraftLife, check as lane_check
from tools.artistic_street import GUARD, MAX_BUNDLE, MIB
from tools.settlement_attractions import BackupWorld


R1_SHA='f155f49910211043c523309a26066fbd70c995f6edab9578950927d5e07a8244'


def construct(registry,survey,exclusions):
    d=CraftLife(lane(registry,survey,exclusions).p)
    d.scene(None,'Supported warm bracket lamps','The actual cobbler capture is dark; small actual wall lanterns light the workbench and entrances without replacing furniture or adding an oversized ceiling fixture.')
    for ident,x,y,z,facing in (('cobbler',8,3,20,'south'),('cobbler',3,3,14,'east'),('cobbler',7,3,18,'north'),
          ('luthier',17,2,15,'south'),('luthier',13,2,10,'east'),('potter',30,1,17,'south'),('potter',26,1,12,'east'),
          ('glazier',39,2,26,'south'),('glazier',35,2,21,'east'),('grocer',8,3,25,'north'),('stoneleaf',24,2,24,'north')):
        d.scene(ident,'A small warm lamp at '+ident,'Actual modelled bracket, full wall backing and preserved walking headroom.')
        dx,dz={'south':(0,-1),'north':(0,1),'east':(-1,0),'west':(1,0)}[facing]
        back=d.p.blocks.get((x+dx,y,z+dz),'minecraft:air').split('[',1)[0]
        if back=='minecraft:air' or back.startswith(('mcwwindows:','mcwdoors:')):raise UserError('Craft bracket has no full wall support')
        d.put(x,y,z,'mcwlights:bell_wall_lantern',facing=facing)
    for ident,x,z,ys,attached in (('cobbler',1,13,(2,3,4),'east'),('cobbler',9,20,(5,6,7),'north'),
          ('luthier',24,8,(0,1,2),'west'),('potter',24,12,(-1,0,1),'east'),('potter',29,18,(3,4,5),'north'),
          ('glazier',42,22,(0,1,2),'west'),('grocer',10,24,(5,6,7),'south'),('stoneleaf',29,31,(0,1,2),'west')):
        d.scene(ident,'Climbing plants at '+ident,'Three-block supported vine strips soften the blank corners seen in native street captures; no random leaf wall or blocked doorway.')
        dx,dz={'south':(0,1),'north':(0,-1),'east':(1,0),'west':(-1,0)}[attached]
        for y in ys:
            back=d.p.blocks.get((x+dx,y,z+dz),'minecraft:air').split('[',1)[0]
            if back=='minecraft:air' or back.startswith(('mcwwindows:','mcwdoors:')):raise UserError('Craft vine lacks its actual supporting wall')
            d.put(x,y,z,'minecraft:vine',**{k:k==attached for k in ('north','south','east','west','up')})
    d.scene(None,'Window trades and planted corners','Actual small item displays, supported pottery and flowers supply human-scale stories at the shopfronts.')
    for ident,x,z,flower in (('cobbler',2,20,'minecraft:potted_fern'),('luthier',12,16,'minecraft:potted_allium'),
          ('potter',24,17,'minecraft:potted_blue_orchid'),('glazier',41,26,'minecraft:potted_azure_bluet'),
          ('grocer',2,26,'minecraft:potted_fern'),('stoneleaf',18,24,'minecraft:potted_poppy')):
        d.scene(ident,'A planted corner at '+ident,'Pot rests on a real low masonry footing at the actual sampled ground.')
        g=d.p.ground(x,z);d.put(x,g,z,'minecraft:mossy_stone_bricks');d.put(x,g+1,z,flower)
    for ident,x,y,z,face,item in (('cobbler',4,1,20,'south','minecraft:leather_boots'),('potter',27,-1,17,'south','minecraft:flower_pot'),('stoneleaf',20,0,24,'north','minecraft:brick')):
        d.scene(ident,'A real windowsill sample at '+ident,'Actual item on an anchored native shelf, rather than decorative text claiming a trade.')
        d.shelf(x,y,z,face,item,'Street sample: '+ident)
    for ident,x,y,z,lines in (('cobbler',6,3,20,['Bramble','& Buckle','Boot repairs']),('grocer',5,3,25,['The Clover','Pantry','Market kitchen'])):
        d.scene(ident,'Low readable shop sign','A small hanging sign under the actual upper-floor beam keeps the trade legible from the lane.')
        if d.p.blocks.get((x,y+1,z),'minecraft:air')=='minecraft:air':raise UserError('New shop sign has no actual overhead beam')
        d.put(x,y,z,'minecraft:dark_oak_hanging_sign',attached=False,rotation=0 if ident=='cobbler' else 8,waterlogged=False)
        messages=[json.dumps(json.dumps({'text':s})) for s in (lines+['']*4)[:4]]
        d.p.tags[x,y,z]='{is_waxed:1b,front_text:{messages:['+','.join(messages)+'],color:"black",has_glowing_text:0b}}'
    for ident,x,y,z,face,lines in (('potter',30,0,17,'south',['Clay & Candle','Pottery','& wax']),('stoneleaf',21,1,24,'north',['The Stoneleaf','Stonework','& timber'])):
        d.scene(ident,'A street-level trade board','Readable small board beside the actual door, outside the preserved route.')
        d.put(x,y,z,'minecraft:oak_wall_sign',facing=face,waterlogged=False)
        messages=[json.dumps(json.dumps({'text':s})) for s in (lines+['']*4)[:4]]
        d.p.tags[x,y,z]='{is_waxed:1b,front_text:{messages:['+','.join(messages)+'],color:"black",has_glowing_text:0b}}'
    d.scene(None,'Dark stone edges and a grated cross-drain','Designed boundary courses frame the pale lane; the short closed grate sits over the retained base and keeps the walking width.')
    for x,z in sorted(d.p.path_cells):
        f=d.p.path_heights[x,z];pos=x,f,z
        if d.base.blocks.get(pos)!='minecraft:gravel' or not any((x+dx,z+dz) not in d.p.path_cells for dx,dz in ((1,0),(-1,0),(0,1),(0,-1))):continue
        d.put(x,f,z,'minecraft:mossy_cobblestone')
    for z in (22,23,24):d.put(8,0,z,'minecraft:iron_trapdoor',facing='north',half='top',open=False,powered=False,waterlogged=False)
    for x,z in ((33,29),):
        g=d.p.ground(x,z);d.put(x,g,z,'minecraft:mossy_stone_bricks');d.put(x,g+1,z,'handcrafted:spruce_bench',facing='north',shape='single',color='none',waterlogged=False)
    return d


def check(d):
    result=lane_check(d)
    changed={v for v,s in d.p.blocks.items() if d.base.blocks.get(v)!=s}
    for v in changed:
        old=d.base.blocks.get(v,'minecraft:air').split('[',1)[0]
        if old.startswith(('handcrafted:','farmersdelight:','mcwlights:')) or v in d.protected:raise UserError('Craft detail replaces furniture or inventory')
    if not 0<len(changed)<1500:raise UserError('Craft detail exceeded small scope')
    return result,changed


def prepare(home,registry_path,survey_path,r1_path,exclusion_paths,backup_id,backup_sha,output):
    home,output=Path(home).resolve(),Path(output).resolve()
    if output.exists() or output.drive.upper()!='D:' or not output.is_relative_to(Path(r'D:\A World for Two')/'staging'):raise UserError('NEW private bounded D staging output required')
    if digest(Path(r1_path))!=R1_SHA or len(exclusion_paths)!=3:raise UserError('Exact actually placed craft R1 and three original exclusions required')
    if any(Path(v).stat().st_size>8*MIB for v in (registry_path,survey_path,r1_path,*exclusion_paths)):raise UserError('Finite detail inputs required')
    registry=json.loads(Path(registry_path).read_text(encoding='utf-8'));survey=json.loads(Path(survey_path).read_text(encoding='utf-8'));placed=json.loads(Path(r1_path).read_text(encoding='utf-8'))
    ex=[(name,json.loads(Path(v).read_text(encoding='utf-8')),digest(Path(v))) for name,v in zip(('cottage','bascule','rosebridge'),exclusion_paths)]
    d=construct(registry,survey,ex);checks,changed=check(d)
    expected=d.base.serialize(backup_sha);decode=lambda p:{(x,y,z):p['palette'][i] for x,y,z,i in p['blocks']}
    if decode(expected)!=decode(placed) or expected['block_entities']!=placed['block_entities']:raise UserError('Frozen source differs from actual placed craft geometry')
    w=BackupWorld(home,{'id':backup_id,'sha256':backup_sha,'verified':True},registry)
    try:
        previous={v:w.state(tuple(v[i]+d.p.origin[i] for i in range(3))) for v in changed}
        if any(tuple(v[i]+d.p.origin[i] for i in range(3)) in w.protected for v in changed):raise UserError('Craft detail targets an actual saved BE')
        sources=w.sources.copy()
    finally:w.close()
    g=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(GUARD),'-EstimatedCBytes','0','-EstimatedDBytes',str(MAX_BUNDLE)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,check=False);guard=json.loads(g.stdout)
    if g.returncode or not guard.get('allowed'):raise UserError('Reserve guard refused finite detail output')
    native=d.p.serialize(backup_sha);ox,oy,oz=d.p.origin
    native['blocks']=[v for v in native['blocks'] if (v[0]-ox,v[1]-oy,v[2]-oz) in changed]
    native['block_entities']=[v for v in native['block_entities'] if tuple(v['pos'][i]-d.p.origin[i] for i in range(3)) in changed]
    native.update(name='Bramble Lane — lived-in light and street detail r2',baseline_sha256=R1_SHA,landmarks=[])
    data=(json.dumps(native,ensure_ascii=False,separators=(',',':'))+'\n').encode();sha=hashlib.sha256(data).hexdigest()
    before=dict(native);before['palette']=sorted(set(previous.values()));ix={v:i for i,v in enumerate(before['palette'])};before['blocks']=[[x,y,z,ix[previous[x-ox,y-oy,z-oz]]] for x,y,z,i in native['blocks']];before['block_entities']=[]
    before_data=(json.dumps(before,separators=(',',':'))+'\n').encode()
    receipt={'format':'awft-craft-detail:2','at':utcnow(),'source_sha256':digest(Path(__file__)),'baseline_sha256':R1_SHA,'backup_id':backup_id,'backup_sha256':backup_sha,'plan_sha256':sha,'before_sha256':hashlib.sha256(before_data).hexdigest(),'placements':len(changed),'new_BEs':len(native['block_entities']),'existing_inventories_replayed':0,'existing_furniture_replaced':0,'checks':checks,'groups':d.groups,'saved_sources':sources,'storage_guard':guard,'visual_inputs':['art-r2-0900/craft-street.png','art-r2-0900/potter-bend.png','art-r2-0900/cobbler-room.png'],'visual_status':'Pending actual native view and walking; no artistic acceptance inferred'}
    meta=(json.dumps(receipt,sort_keys=True,indent=2)+'\n').encode()
    if len(data)+len(before_data)+len(meta)>MAX_BUNDLE:raise UserError('Craft detail exceeded finite bundle')
    output.mkdir(parents=True,exist_ok=False);path=output/('bramble-detail-'+sha[:16]+'.json');path.write_bytes(data);(output/'before.json').write_bytes(before_data);(output/'manifest.json').write_bytes(meta)
    return {'plan':str(path),'sha256':sha,'placements':len(changed),'new_BEs':len(native['block_entities']),'before':str(output/'before.json')}


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__)
    for name in ('home','registry','survey','r1','output'):a.add_argument('--'+name,type=Path,required=True)
    a.add_argument('--exclude',type=Path,nargs=3,required=True);a.add_argument('--backup-id',required=True);a.add_argument('--backup-sha256',required=True);v=a.parse_args()
    print(json.dumps(prepare(v.home,v.registry,v.survey,v.r1,v.exclude,v.backup_id,v.backup_sha256,v.output),indent=2))
