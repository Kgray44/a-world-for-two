"""Photo-led finish correction for the built promenade; no live world actions."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from control_room.common import UserError, digest, read_json, utcnow
from tools.artistic_lavender_promenade import (
    AIR, BOUNDS, GRAPE, POSTS, Promenade, WALK_SOURCE, decode, floor, payload,
)
from tools.artistic_materials import require_material_rule
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld, base, properties

MIB=1024**2
MAX_OUTPUT=8*MIB
PREVIOUS='castle-lavender-promenade-FRESH-8d3957-20261029'
PREVIOUS_SHA='3d7ca1526493fe34473a8b9e92e414d7db395ce153891ebbbfeb31cb1dd454f3'
PALETTE={
    'chipped:pink_terracotta_tiles':'chipped:pink_concrete_tiles',
    'chipped:pink_terracotta_tile':'chipped:pink_concrete_panel',
    'chipped:pink_terracotta_pillar':'chipped:pink_concrete_pillar',
    'regions_unexplored:lavender_wisteria_leaves':'minecraft:flowering_azalea_leaves',
}
SURFACES={'minecraft:dirt_path','minecraft:gravel','minecraft:cobblestone',
          'minecraft:polished_andesite','minecraft:stone_brick_stairs'}
SUBSTRATE={'minecraft:dirt','minecraft:grass_block','minecraft:stone',
           'minecraft:mossy_stone_bricks','chipped:calcite_bricks',
           'chipped:small_calcite_bricks'}
PHOTO_PINS={
 'promenade-north-day.png':'cbff14c2a591ea6dae54f00d92a11773cd7cc922d3e6bf3e73fb112e4b36452e',
 'promenade-south-day.png':'1841a807159fe0194b08146c56efb71a9fa8b8fb49fbe15c89aab08b702788a5',
}


def paving(x,z):
    return ('chipped:bordered_calcite' if x in (1287,1289,1299,1301)
            else 'chipped:checkered_calcite_tiles' if z in POSTS
            else 'chipped:blank_calcite_carving' if x in (1292,1295)
            else 'chipped:tiled_calcite')


def correction(registry,snapshot,placed,full,walk):
    """Only known accent identities, intrusive leaf planes and original floors."""
    factory=Promenade(registry,snapshot)
    delta,before,support,groups={},{},{},Counter()
    for p,expected in full.items():
        if snapshot.state(p)!=expected:
            raise UserError('Built promenade changed; preserve and review: '+str(p))
    def add(p,old,new,group):
        x,y,z=p
        if not (BOUNDS[0]<=x<=BOUNDS[2] and BOUNDS[1]<=z<=BOUNDS[3]):
            raise UserError('Finish escaped the original footprint')
        if full.get(p)!=old or snapshot.state(p)!=old or p in snapshot.protected:
            raise UserError('Unowned/changed/BE finish target: '+str(p))
        if p in delta:raise UserError('Overlapping finish groups')
        before[p],delta[p]=old,new;groups[group]+=1
    for p,old in placed.items():
        if base(old) in PALETTE:
            key=PALETTE[base(old)]
            add(p,old,factory.state(key,**properties(old)),
                'green_foliage' if base(old).endswith('_leaves') else 'soft_pink_accents')
    grape_floor=GRAPE[0],GRAPE[1]-1,GRAPE[2]
    for p,old in walk.items():
        x,y,z=p
        if not (1287<=x<=1301 and -996<=z<=-952) or base(old) not in SURFACES:
            continue
        if p==grape_floor:continue  # Preserve the existing plant's exact root.
        if full.get(p)!=old:raise UserError('Original route floor is no longer retained: '+str(p))
        for dy in (1,2):
            # The original path producer stores changed cells only, so an
            # omitted body entry is unknown until this authenticated read.
            q=x,y+dy,z;s=snapshot.state(q)
            if base(s) not in AIR:
                raise UserError('Original route body is occupied: '+str(p))
            support[q]=s
        q=x,y-1,z;s=snapshot.state(q)
        if base(s) not in SUBSTRATE or q in snapshot.protected:
            raise UserError('Unqualified retained floor substrate: '+str((q,s)))
        support[q]=s
        key='create:cut_calcite_stairs' if base(old)=='minecraft:stone_brick_stairs' else paving(x,z)
        new=factory.state(key,**(properties(old) if base(old).endswith('_stairs') else {}))
        add(p,old,new,'pale_route_floor')
    for p in (GRAPE,grape_floor):support[p]=snapshot.state(p)
    final=full|delta|support
    # Keep exact positions and native half-step anatomy; there is no new rise,
    # excavation, actor, inventory, plant root or entrance reconstruction.
    for p,new in delta.items():
        if base(before[p]).endswith('_stairs') and properties(new)!=properties(before[p]):
            raise UserError('Stair grade/facing changed')
    for z in range(-996,-951):
        for x in range(1290,1296):
            for y in range(floor(z)+1,floor(z)+4):
                if base(final.get((x,y,z),snapshot.state((x,y,z)))) not in AIR:
                    raise UserError('Finish obstructs the principal aisle')
    if not 1<=len(delta)<=512:raise UserError('Keep the photo correction below512 targets')
    rule=require_material_rule(placed|delta,'Grand Lavender Promenade — photo finish')
    return delta,before,support,final,dict(groups),rule


def prepare(home,output,backup_id,backup_sha256):
    home,output=Path(home).resolve(),Path(output).resolve()
    if not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests')) or output.exists() or not output.is_relative_to(home/'staging'):
        raise UserError('New bounded private output under the existing home required')
    reserve=guard(8*MIB,MAX_OUTPUT)
    previous=home/'staging'/PREVIOUS;manifest=read_json(previous/'manifest.json')
    if digest(previous/'manifest.json')!=PREVIOUS_SHA:raise UserError('Original built source changed')
    for name in ('place.json','full.json'):
        if digest(previous/name)!=manifest['packets'][name]['sha256']:raise UserError('Immutable built packet changed')
    walk_path=home/'staging'/WALK_SOURCE
    pin=next(v for v in manifest['exclusions'] if v['file']==WALK_SOURCE)
    if digest(walk_path)!=pin['sha256']:raise UserError('Original walking source changed')
    photos=home/'logs/visual-review/after65-day-1793288210'
    for name,sha in PHOTO_PINS.items():
        if digest(photos/name)!=sha:raise UserError('Actual photo reference changed')
    registry_path=home/'dashboard/settlement/registry.json';registry=read_json(registry_path)
    custody=read_json(home/'dashboard/settlement/backup-receipt.json')
    if custody.get('verified') is not True:raise UserError('Canonical custody receipt required')
    receipt={'id':backup_id,'sha256':backup_sha256,'verified':True}
    snapshot=BackupWorld(home,receipt,registry)
    try:
        delta,before,support,final,groups,rule=correction(registry,snapshot,
            decode(read_json(previous/'place.json')),decode(read_json(previous/'full.json')),decode(read_json(walk_path)))
        sources=snapshot.sources.copy()
    finally:snapshot.close()
    docs={};files={}
    for name,cells,title in (
        ('before.json',before,'VERIFY ONLY — exact retained photo-finish preimage'),
        ('support.json',support,'VERIFY ONLY — unchanged route substrate and grape/root'),
        ('place.json',delta,'Photo-led soft pink, living foliage and pale route finish'),
        ('normal.json',delta,'NORMAL ONLY — photo finish'),
        ('full.json',final,'VERIFY ONLY — complete promenade after photo finish')):
        raw=(json.dumps(payload(registry,custody['sha256'],cells,title),separators=(',',':'))+'\n').encode()
        docs[name]=raw;files[name]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'cells':len(cells)}
    meta={'format':'awft-promenade-photo-finish:1','at':utcnow(),'source_sha256':digest(Path(__file__)),
          'previous_manifest_sha256':PREVIOUS_SHA,'observed_checkpoint':receipt,'canonical_custody':custody,
          'registry_sha256':digest(registry_path),'actual_photos':PHOTO_PINS,'groups':groups,
          'targets':len(delta),'files':files,'saved_sources':sources,'material_rule':rule,'reserve_guard':reserve,
          'unchanged':['all positions and structural geometry','all original floor block Y levels and stair properties',
            'both entrances and six-wide clear route','original grape and exact root state','all native BEs and inventories',
            'all 24 white pendants and their real attachment points'],
          'native_actions':0,'world_writes':0,'acceptance':'Source only; fresh native before/support, once place, normal/full and actual repeated photos required'}
    docs['manifest.json']=(json.dumps(meta,indent=2)+'\n').encode()
    if sum(map(len,docs.values()))>MAX_OUTPUT:raise UserError('Finite finish output exceeded')
    output.mkdir(parents=True,exist_ok=False)
    for name,raw in docs.items():(output/name).open('xb').write(raw)
    return {'output':str(output),'manifest_sha256':digest(output/'manifest.json'),'targets':len(delta),'groups':groups,'files':files,'native_actions':0}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('home','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--backup-id',required=True);p.add_argument('--backup-sha256',required=True)
    print(json.dumps(prepare(**vars(p.parse_args())),indent=2))
