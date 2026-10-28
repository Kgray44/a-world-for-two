"""Expanded native neighbor reconciliation for the frozen West15 proposals.

No expected-state correction or geometry/NBT replay. Unchanged neighboring
ridge blocks need their own normal shape update after a roof material changes.
"""
from __future__ import annotations
import argparse,hashlib,json,time
from pathlib import Path

from control_room.common import UserError,digest,read_json
from tools.artistic_bridge_refinement import flatten
from tools.artistic_north_bank_east import native_payload
from tools.artistic_neighborhood_roofs import ridge_part
from tools.artistic_tortuga_frontages import key
from tools.playtest import guard

MIB=1024**2
ORIGINAL=('staging/west15-shells-1793218803041549500/manifest.json','52669f6d5ae92e82a18c1577a99a56e2648fc2dc570a3ff8b33987659b404f42')


def normal_scope(full,delta,be_positions):
    selected={}
    for q,s in full.items():
        if q in be_positions:continue
        name=key(s)
        join=(name.startswith('mcwroofs:')and name.endswith('_top_roof'))or(name.startswith('mcwwindows:')and name.endswith('_plank_window'))
        if join or q in delta and name!='minecraft:air':selected[q]=s
    return selected


def validate_ridges(full):
    proof=[]
    for(x,y,z),s in full.items():
        name=key(s)
        if not(name.startswith('mcwroofs:')and name.endswith('_top_roof')):continue
        neighbors=((x,y,z-1),(x+1,y,z),(x,y,z+1),(x-1,y,z))
        bits=[key(full.get(q,''))==name for q in neighbors]
        part=ridge_part(*bits)
        if s!=name+'[part='+part+']':
            raise UserError('Complete physical mask does not prove this frozen expectation: '+str((x,y,z)))
        proof.append({'position':[x,y,z],'independently_required':s,'same_id_cardinal_mask':bits})
    return proof


def prepare(home):
    reserve=guard(1*MIB,2*MIB);home=Path(home).resolve()
    source=home/ORIGINAL[0]
    if digest(source)!=ORIGINAL[1]:raise UserError('Frozen West15 source manifest changed')
    manifest=read_json(source);base=source.parent;registry=read_json(home/'dashboard/settlement/registry.json')
    out=home/'staging'/('west15-expanded-native-normal-'+str(time.time_ns()));out.mkdir();raw={};groups=[]
    for index in range(1,4):
        fullp=base/f'west15-{index}-full-VERIFY-ONLY.json';deltap=base/f'west15-{index}-PROPOSAL.json'
        for p in(fullp,deltap):
            if digest(p)!=manifest['files'][p.name]['sha256']:raise UserError('Frozen original proposal/full changed')
        full_doc=read_json(fullp);full=flatten(full_doc);delta=flatten(read_json(deltap))
        bes={tuple(row['pos'])for row in full_doc['block_entities']}
        normal=normal_scope(full,delta,bes);proof=validate_ridges(full)
        doc=native_payload(registry,normal,manifest['checkpoint_sha256'],'NORMAL SETTLE ONLY — full ridge/window neighborhood plus owned delta; NEVER PLACE')
        doc.update(verification_only=True,construction_forbidden=True)
        name=f'west15-{index}-expanded-native-normal-SETTLE-ONLY.json'
        raw[name]=(json.dumps(doc,separators=(',',':'))+'\n').encode()
        groups.append({'group':index,'normal_targets':len(normal),'roof_top_targets':len(proof),'window_targets':sum(key(s).startswith('mcwwindows:')for s in normal.values()),
            'original_full_verification':str(fullp),'original_full_sha256_UNCHANGED':digest(fullp),'independent_ridge_mask_proof':proof})
    receipt={'format':'awft-west15-expanded-native-normal:1','source_sha256':digest(Path(__file__)),'frozen_source_manifest':ORIGINAL,'groups':groups,
       'checkpoint_id':manifest['checkpoint_id'],'checkpoint_sha256':manifest['checkpoint_sha256'],'reserve_guard':reserve,'native_actions':0,'existing_BE_targets':0,
       'purpose':'Normal neighbor-shape reconciliation only. Frozen canonical expected states remain byte-identical; actual inherited endcaps must settle to the independently required complete-mask shape.',
       'no_geometry_NBT_or_inventory_replay':True,'files':{n:{'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}for n,b in raw.items()}}
    raw['derivation.json']=(json.dumps(receipt,indent=2)+'\n').encode()
    if sum(map(len,raw.values()))>MIB:raise UserError('Finite1MiB native-normal bundle cap exceeded')
    for name,data in raw.items():(out/name).open('xb').write(data)
    return{'folder':str(out),'receipt_sha256':digest(out/'derivation.json'),'groups':[{k:v for k,v in r.items()if k!='independent_ridge_mask_proof'}for r in groups],'files':receipt['files']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--home',type=Path,required=True)
    print(json.dumps(prepare(parser.parse_args().home),indent=2))
