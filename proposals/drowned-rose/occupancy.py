"""Inspect authenticated saved residents and UUID collisions before tavern admission.

Only immutable backup members are read; results never establish current live
positions, POI ownership or safe native placement. No raw inventories are exported.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tools.habitat_life import decode_entity_chunks,entity_rows,entity_uuid
from tools.settlement_attractions import BackupWorld


def inside(position):
    if not isinstance(position,list)or len(position)!=3 or any(type(v)not in(int,float)or not math.isfinite(v)for v in position):return False
    x,y,z=position
    return 64<=y<=85 and ((1291<=x<1313 and -1291<=z< -1268)or(1288<=x<1293 and -1286<=z< -1277))


def inspect(home,ident,sha,roster):
    registry=json.loads((home/'dashboard/settlement/registry.json').read_bytes())
    snapshot=BackupWorld(home,{'id':ident,'sha256':sha,'verified':True},registry)
    try:
        wanted={r['uuid']:r['id']for r in roster}
        if not 1<=len(wanted)<=45 or len(wanted)!=len(roster):raise ValueError('One to45 unique proposed resident identities required')
        prefix=snapshot.prefix.removesuffix('region/')
        names=[n for n in snapshot.files if n.startswith(prefix)and re.search(r'/entities/r\.-?\d+\.-?\d+\.mca$',n)]
        if len(names)>64 or sum(snapshot.files[n]['size']for n in names)>64*1024**2:raise ValueError('Saved entity census exceeds64MiB/64regions')
        nearby=[];memories=[];collisions=[];sources=[];count=0
        for name in sorted(names):
            record=snapshot.files[name]
            if snapshot.archive.getinfo(name).file_size!=record['size']:raise ValueError('Archive entity entry size differs')
            raw=snapshot.archive.read(name)
            if hashlib.sha256(raw).hexdigest()!=record['sha256']:raise ValueError('Archive entity region digest differs')
            match=re.fullmatch(r'r\.(-?\d+)\.(-?\d+)\.mca',Path(name).name)
            if match is None:raise ValueError('Unexpected entity region name')
            relative=name[len(prefix):];overworld=relative.startswith('entities/')
            for doc in decode_entity_chunks(raw,tuple(map(int,match.groups()))):
                for root in doc['Entities']:
                    for row in entity_rows(root):
                        count+=1
                        if count>100000:raise ValueError('Saved entity count exceeds finite bound')
                        uuid=entity_uuid(row)
                        if uuid in wanted:collisions.append({'resident':wanted[uuid],'uuid':uuid,'species':row.get('id'),'saved_file':relative})
                        if overworld and inside(row.get('Pos')):
                            nearby.append({'uuid':uuid,'species':row.get('id'),'name':row.get('CustomName'),
                                           'position':row['Pos'],'managed_life':'awft_life'in row.get('Tags',[])})
                        for key in ['minecraft:home','minecraft:job_site','minecraft:potential_job_site']:
                            value=row.get('Brain',{}).get('memories',{}).get(key,{}).get('value',{})
                            if isinstance(value,dict)and value.get('dimension')=='minecraft:overworld'and inside(value.get('pos')):
                                memories.append({'uuid':uuid,'species':row.get('id'),'name':row.get('CustomName'),
                                                 'memory':key,'position':value['pos']})
            sources.append({'file':relative,'bytes':len(raw),'sha256':record['sha256']})
        player_collisions=[Path(n).stem for n in snapshot.files if n.startswith(prefix+'playerdata/')and n.endswith('.dat')and Path(n).stem in wanted]
        return {'format':'awft-drowned-rose-saved-occupancy:1','checkpoint_id':ident,'checkpoint_sha256':sha,
                'saved_entity_rows_inspected':count,'source_regions':sources,'existing_entities_in_envelope':nearby,
                'saved_home_job_memories_in_envelope':memories,'proposed_identity_collisions':collisions,
                'proposed_player_uuid_collisions':player_collisions,'native_or_world_writes':0,'current_live_positions_proved':False,
                'scope':'Historical stopped-world saved occupancy, including passengers; preserve all existing entities and memories. Fresh native census and exact geometry still required.'}
    finally:snapshot.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--home',type=Path,required=True);p.add_argument('--checkpoint-id',required=True);p.add_argument('--checkpoint-sha',required=True);p.add_argument('--roster',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh private output path required')
    if a.roster.stat().st_size>128*1024:raise ValueError('Bounded source roster required')
    report=inspect(a.home,a.checkpoint_id,a.checkpoint_sha,json.loads(a.roster.read_bytes()))
    raw=(json.dumps(report,indent=2)+'\n').encode()
    if len(raw)>2*1024**2:raise ValueError('Census output exceeds2MiB')
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(raw)
    print(json.dumps({'output':str(a.output),'sha256':hashlib.sha256(raw).hexdigest(),'saved_rows':report['saved_entity_rows_inspected'],
                      'existing_in_envelope':len(report['existing_entities_in_envelope']),
                      'species_in_envelope':dict(Counter(r['species']for r in report['existing_entities_in_envelope'])),
                      'saved_home_job_memories_in_envelope':len(report['saved_home_job_memories_in_envelope']),
                      'proposed_uuid_collisions':len(report['proposed_identity_collisions'])+len(report['proposed_player_uuid_collisions']),
                      'native_or_world_writes':0}))
