"""Read finite revision preimages from an authenticated, stopped-world checkpoint.

This never reads live region files or assumes an unspecified target is air. A
native comparison of the resulting plan still precedes each revision. Artistic
quality is decided from the real client, independently of this short check.
"""
from collections import Counter
import argparse
import json
from pathlib import Path

from control_room.common import UserError, read_json, digest, utcnow
from .settlement_attractions import BackupWorld
from .playtest import guard


def prepare(home, target, output, predecessor=None):
    home, target, output = Path(home).resolve(), Path(target).resolve(), Path(output).resolve()
    if (not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests'))
            or not output.is_relative_to(home/'staging') or output.exists()
            or target.stat().st_size > 16*1024**2):
        raise UserError('A unique, bounded private staging preimage is required')
    guard(0, 16*1024**2)
    owner = read_json(home/'dashboard/artistic-owner.json', {})
    receipt = read_json(home/'dashboard/settlement/backup-receipt.json', {})
    registry = read_json(home/'dashboard/settlement/registry.json')
    plan = read_json(target)
    if (owner.get('format')!='awft-artistic-stage:1' or receipt.get('verified') is not True
            or plan['backup_sha256'] != receipt['sha256']
            or plan['world_path'] != registry['world_path']):
        raise UserError('Native world and current stopped checkpoint differ')
    if not 0 < len(plan['blocks']) <= 180_000:
        raise UserError('Split the revision into finite authored sections')
    old = read_json(predecessor) if predecessor else None
    previous = {(x,y,z):old['palette'][i] for x,y,z,i in old['blocks']} if old else {}
    # Native furniture and windows can create empty block entities without an
    # explicit NBT tag. Their custody still comes from the immutable placed R1
    # position, never from assuming an unknown BE contains no inventory.
    old_bes = {pos for pos,state in previous.items()
               if state.split('[',1)[0] not in {'minecraft:air','minecraft:cave_air','minecraft:void_air','minecraft:water'}}
    snapshot = BackupWorld(home, receipt, registry)
    states, native_bes = {}, set()
    try:
        for x,y,z,_ in plan['blocks']:
            pos=x,y,z
            states[pos]=snapshot.state(pos)
            if pos in snapshot.protected:
                native_bes.add(pos)
        unknown_bes = {pos for pos in native_bes if pos not in old_bes
                       or states[pos].split('[',1)[0] != previous[pos].split('[',1)[0]}
        if unknown_bes:
            raise UserError('An unreviewed block entity occupies revision targets: '+str(sorted(unknown_bes)[:12]))
        sources = snapshot.sources[:]
    finally:
        snapshot.close()
    palette=sorted(set(states.values())); index={state:i for i,state in enumerate(palette)}
    before=plan | {'name':'Stopped checkpoint preimage — '+plan.get('name','authored revision'),
                  'palette':palette,'blocks':[[*p,index[state]] for p,state in sorted(states.items())],
                  'block_entities':[],'commands':[],'landmarks':[]}
    raw=(json.dumps(before,separators=(',',':'))+'\n').encode()
    if len(raw)>8*1024**2:raise UserError('Preimage exceeds its finite allocation')
    output.mkdir(parents=True,exist_ok=False)
    path=output/'before.json'; path.write_bytes(raw)
    manifest={'format':'awft-artistic-preimage:1','at':utcnow(),'target_sha256':digest(target),
              'predecessor_sha256':digest(Path(predecessor)) if predecessor else None,
              'checkpoint_id':receipt['id'],'checkpoint_sha256':receipt['sha256'],
              'before_sha256':digest(path),'positions':len(states),'sources':sources,
              'saved_state_histogram':dict(Counter(s.split('[',1)[0] for s in states.values())),
              'new_position_histogram':dict(Counter(s.split('[',1)[0] for p,s in states.items() if p not in previous)),
              'known_authored_block_entities':len(native_bes),'unreviewed_block_entities':0,
              'saved_differences_from_predecessor':[[*p,previous[p],s] for p,s in states.items()
                  if p in previous and previous[p].split('[',1)[0]!=s.split('[',1)[0]],
              'gate':'Real native verify of this exact preimage must pass; saved-state reading alone does not admit a live edit'}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'before':str(path),'sha256':digest(path),'positions':len(states),
        'saved_differences':len(manifest['saved_differences_from_predecessor']),
        'new_position_histogram':manifest['new_position_histogram']}),flush=True)
    return path


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home',required=True,type=Path)
    parser.add_argument('--target',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--predecessor',type=Path)
    args=parser.parse_args()
    prepare(args.home,args.target,args.output,args.predecessor)
