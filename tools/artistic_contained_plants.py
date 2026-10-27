"""Remove only a proven planted azalea tree; replace bridge pots with inert pots.

Reads authenticated stopped archives and writes NEW private plans. Never places
blocks or changes the bascule generator. The full physical output is VERIFY ONLY.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

from control_room.common import UserError, digest, utcnow
from tools.artistic_materials import require_material_rule
from tools.settlement_attractions import BackupWorld

AIR='minecraft:air'
GROWTH={'minecraft:oak_log','minecraft:azalea_leaves','minecraft:flowering_azalea_leaves'}
STABLE_SHA='348dee1d07e9f9f261c41c585f68267bf1885c1720e1106e947680c952bcd1ef'
OLD_ID='20261027T065242Z-738f1f'
OLD_SHA='13afd46619a6ec8407e48471f08cc9014cb2e53540361c9a8ece7bc8b6b7a6b0'
BACKUP_ID='20261027T093048Z-eafdca'
BACKUP_SHA='a9d481b7e48d19b449e5e3784d31f0ee5d61d119cd7124736486cbc4763bd067'
ROOT=(1181,69,-1105)
CENTERS={(1181,70,-1183),(1181,70,-1105),(1206,70,-1183),
         (1206,70,-1175),(1206,70,-1113),(1219,70,-1083)}
MAX_OUTPUT=8*1024**2
GUARD=Path('C:/Users/kkids/AppData/Local/AeroStorageWatch/ReserveGuard.ps1')


def decode(plan):
    return {(x,y,z):plan['palette'][i] for x,y,z,i in plan['blocks']}


def encode(template,blocks,name,backup_sha,*,tags=()):
    p=dict(template);p['name']=name;p['created']=utcnow();p['backup_sha256']=backup_sha
    p['palette']=sorted(set(blocks.values()));ix={v:i for i,v in enumerate(p['palette'])}
    p['blocks']=[[*pos,ix[s]] for pos,s in sorted(blocks.items())]
    p['block_entities']=list(tags);p['commands']=[];p['landmarks']=[]
    return p


def corrections(expected,current,prebuild,protected):
    """Fixed survey envelope, root provenance, and prior-air proof for every cell."""
    centers={p for p,s in expected.items() if s=='minecraft:flowering_azalea'}
    if centers!=CENTERS:raise UserError('Authored azalea inventory changed; review required')
    if current(ROOT)!='minecraft:rooted_dirt':raise UserError('Known planted root is absent')
    growth={}
    # Includes a generous finite empty boundary. Never walk into nearby forest.
    for x in range(1173,1192):
        for z in range(-1114,-1095):
            for y in range(70,85):
                pos=(x,y,z);state=current(pos)
                if state.split('[')[0] in GROWTH:
                    if x in (1173,1191) or z in (-1114,-1096) or y==84:
                        raise UserError('Tree touches reviewed scan boundary')
                    growth[pos]=state
    if not 1<=len(growth)<=250:raise UserError('Unexpected bounded tree size')
    trunk={p for p,s in growth.items() if s.startswith('minecraft:oak_log[')}
    start=(ROOT[0],70,ROOT[2]);seen={start};todo=[start]
    if start not in trunk:raise UserError('No trunk attached to authored planter')
    while todo:
        x,y,z=todo.pop()
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                for dz in (-1,0,1):
                    q=x+dx,y+dy,z+dz
                    if q in trunk and q not in seen:seen.add(q);todo.append(q)
    if seen!=trunk:raise UserError('Disconnected trunk cannot be attributed to planter')
    for pos,state in growth.items():
        if prebuild(pos)!=AIR:raise UserError('Tree cell was not empty before construction')
        if pos in protected:raise UserError('Tree removal targets a saved block entity')
        if pos in expected and expected[pos]!=AIR and pos not in centers:
            raise UserError('Tree intersects another authored solid; independent repair required')
        if state.split('[')[0].endswith('leaves') and not any(sum(abs(a-b) for a,b in zip(pos,t))<=7 for t in trunk):
            raise UserError('Leaf is outside native azalea support distance')
    changed={p:AIR for p in growth}
    pots=[]
    for x,y,z in sorted(centers):
        bottom=(x,y-1,z);top=(x,y,z)
        if expected.get(bottom)!='supplementaries:planter[extended=false,waterlogged=false]':
            raise UserError('Expected authored planter is absent')
        if top!=start and (current(top)!='minecraft:flowering_azalea' or current(bottom)!=expected[bottom]):
            raise UserError('Another planted pair has changed; review required')
        if current((x,y-2,z)).split('[')[0] in (AIR,'minecraft:water'):
            raise UserError('Potted bush would lack a supported stone foundation')
        changed[bottom]='minecraft:chiseled_stone_bricks'
        changed[top]='minecraft:potted_flowering_azalea_bush'
        pots.append({'plinth':list(bottom),'pot':list(top)})
    return changed,pots,Counter(s.split('[')[0] for s in growth.values())


def prepare(home,stable,output):
    home,stable,output=map(lambda v:Path(v).resolve(),(home,stable,output))
    if digest(stable)!=STABLE_SHA:raise UserError('The reviewed stable physical contract differs')
    if output.exists() or not output.is_relative_to(Path('D:/A World for Two/staging')):
        raise UserError('NEW private D staging output required')
    reg=json.loads((home/'dashboard/settlement/registry.json').read_text(encoding='utf-8'))
    for key in ('minecraft:potted_flowering_azalea_bush','minecraft:chiseled_stone_bricks'):
        if key not in reg['blocks']:raise UserError('Contained native plant palette is absent')
    original=json.loads(stable.read_text(encoding='utf-8'));expected=decode(original)
    cur=BackupWorld(home,{'id':BACKUP_ID,'verified':True,'sha256':BACKUP_SHA},reg)
    old=BackupWorld(home,{'id':OLD_ID,'verified':True,'sha256':OLD_SHA},reg)
    try:
        changes,pots,counts=corrections(expected,cur.state,old.state,cur.protected)
        before={p:cur.state(p) for p in changes}
        allowed_bes={tuple(row['plinth']) for row in pots}
        if (set(changes)&cur.protected)-allowed_bes:raise UserError('Unrelated saved BE in correction')
        sources={'current':cur.sources.copy(),'preconstruction':old.sources.copy()}
        removed_bes=sorted(set(changes)&cur.protected)
    finally:cur.close();old.close()
    after=dict(expected);after.update(changes)
    require_material_rule(changes,'Contained bridge pots and proven tree clearance')
    require_material_rule(after,'Complete bascule physical contract after contained pots')
    delta=encode(original,changes,'Contained bridge azalea correction',BACKUP_SHA)
    pre=encode(original,before,'Exact saved before-state of contained plant repair',BACKUP_SHA)
    tags=[r for r in original['block_entities'] if tuple(r['pos']) not in changes]
    full=encode(original,after,'VERIFY ONLY — contained azaleas and stable bascule physical',BACKUP_SHA,tags=tags)
    full['verification_only']=True
    files={name:(json.dumps(v,ensure_ascii=False,separators=(',',':'))+'\n').encode()
           for name,v in (('delta.json',delta),('before.json',pre),('physical-verify-only.json',full))}
    receipt={'format':'awft-contained-bridge-plants:1','at':utcnow(),'source_sha256':digest(Path(__file__)),
             'stable_sha256':STABLE_SHA,'backup_id':BACKUP_ID,'backup_sha256':BACKUP_SHA,
             'preconstruction_backup_id':OLD_ID,'preconstruction_backup_sha256':OLD_SHA,
             'placements':len(changes),'contained_pairs':pots,'removed_tree_counts':counts,
             'intentional_planter_BE_removals':[list(v) for v in removed_bes],
             'tree_proof':'Each actual tree cell was native air in verified stopped preconstruction archive; connected oak trunk roots exactly at authored planter; leaves <=7 Manhattan blocks from that trunk; no other authored solid or BE is removed.',
             'clearance_cells':[[*p,before[p],changes[p]] for p in sorted(changes)],
             'saved_sources':sources,'files':{n:{'sha256':hashlib.sha256(v).hexdigest(),'bytes':len(v)} for n,v in files.items()},
             'material_checks':'Full bascule per-material 3/9 PASS; delta 3/9 PASS',
             'acceptance':'No native placement, restart, walking, or visual acceptance claimed. Full physical file is verification only.'}
    files['manifest.json']=(json.dumps(receipt,sort_keys=True,indent=2)+'\n').encode()
    if sum(map(len,files.values()))>MAX_OUTPUT:raise UserError('Finite correction bundle exceeded')
    proc=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(GUARD),'-EstimatedCBytes','0','-EstimatedDBytes',str(MAX_OUTPUT)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
    if proc.returncode or not json.loads(proc.stdout).get('allowed'):raise UserError('Reserve guard refused output')
    output.mkdir(parents=True,exist_ok=False)
    for name,data in files.items():(output/name).write_bytes(data)
    return {'output':str(output),'placements':len(changes),'tree_counts':counts,'files':receipt['files']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('home','stable','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.home,a.stable,a.output),indent=2))
