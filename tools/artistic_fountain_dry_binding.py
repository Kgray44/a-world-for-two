"""Bind the already-built R5 fountain to a genuinely current stopped dry save.

This observes the real complete geometry. It never replays the old sculpture,
sets a piston/kinetic field, seeds a header, or operates Minecraft.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

from control_room.common import Layout, UserError, digest, read_json, utcnow
from control_room.server import Server
from control_room.storage import Storage
from tools.artistic_fountain_centerpiece import (
    INTAKE, MARS, block_entities, decode, normal_owned_copper_aging,
)
from tools.artistic_fountain_parking import POSITIONS, classify, context
from tools.artistic_materials import require_material_rule, require_outdoor_rule
from tools.artistic_spawn_plaza import PUMP, WHEEL, payload
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld

SOURCE = 'staging/artistic-fountain-r5-ACTUAL-DRY45-1793155163050141000'
SOURCE_MANIFEST = '28d03159a83ba4d3f3fa7d7b58e1c559a6698ac2c2c4d447aa34b8e8f7895145'
SOURCE_GEOMETRY = 'ce85c167a6c3e831bdbb33996d17352c6902329858b4f65d8349ac222f1942be'
CRITICAL = frozenset(('facing','axis','half','type','part','hinge','multiblock',
                      'waterlogged','powered','extended','locked','delay','level'))
NICHE = ((1145,64,-1131),(1145,64,-1130),(1145,64,-1129),
         (1145,65,-1131),(1145,65,-1130),(1145,66,-1131))


def parts(text):
    name, sep, tail = text.partition('[')
    return name, dict(p.split('=',1) for p in tail[:-1].split(',')) if sep else {}


def compare_owned(expected, actual):
    en, ep = parts(expected); an, ap = parts(actual)
    if en != an and not normal_owned_copper_aging(expected, actual):
        raise UserError('Current fountain material differs from the actually built R5 source')
    if any(ap.get(k) != v for k,v in ep.items() if k in CRITICAL):
        raise UserError('Current fountain orientation, multiblock, fluid or control state differs')
    return actual


def prepare(home, output):
    home, owner, registry, checkpoint = context(home)
    output = Path(output).absolute()
    if output.parent != home/'staging' or output.exists():
        raise UserError('A new immediate private binding folder is required')
    if Server(Layout(home), Storage(Layout(home))).running():
        raise UserError('A normal stopped checkpoint is required before rebinding')
    if (owner.get('backup'),owner.get('backup_sha256')) != (checkpoint['id'],checkpoint['sha256']):
        raise UserError('Current stopped checkpoint and owned world binding differ')
    folder = home/SOURCE
    if digest(folder/'manifest.json') != SOURCE_MANIFEST or digest(folder/'plaza.json') != SOURCE_GEOMETRY:
        raise UserError('The retained actually-built R5 source bytes differ')
    source = read_json(folder/'plaza.json'); expected = decode(source)
    # Restore the original extractable plain-pool intake, already repaired by
    # a separately retained normal native placement. Never recreate the stray
    # waterlogged transport pipe that had no open source beneath it.
    expected[INTAKE] = 'minecraft:water[level=0]'
    reserve = guard(4*1024**2,16*1024**2)
    snapshot = BackupWorld(home,checkpoint,registry); actual={}; derivations=[]
    try:
        for pos, wanted in expected.items():
            observed = compare_owned(wanted,snapshot.state(pos)); actual[pos]=observed
            if observed != wanted:
                derivations.append({'pos':list(pos),'authored':wanted,'actual_saved':observed,
                                    'role':'Preserved actual normal joins/defaults or forward copper aging; no write'})
        baseline = classify({p: snapshot.state(p) for p in POSITIONS})
        if baseline != 'ALREADY_PARKED' or any(snapshot.state(p) != 'minecraft:air' for p in NICHE):
            raise UserError('A genuinely parked dry gate and drained owned niche are required')
        if INTAKE in snapshot.protected:
            raise UserError('Preserve an unexpected intake BE; plain source water is required')
        kinetic = block_entities(snapshot,{PUMP,WHEEL})
        speeds={}
        for pos in (PUMP,WHEEL):
            value=kinetic.get(pos,{}).get('Speed')
            if type(value) not in (int,float) or not math.isfinite(value) or value != 0:
                raise UserError('Actual stopped saved wheel/pump Speed must be present and zero')
            speeds[str(pos)]=value
        saved_sources=snapshot.sources.copy()
    finally:
        snapshot.close()
    checks={'material':require_material_rule(actual,'Actual complete current R5 fountain'),
            'outdoor':require_outdoor_rule(actual,'Actual current R5 plaza surfaces')}
    for n in range(3):
        if parts(actual[(1138,75+n,-1129)]) != (MARS,{'facing':'west','multiblock':str(n),'waterlogged':'false'}):
            raise UserError('All three actual native statue parts must retain their real topology')
    plan=payload(registry,checkpoint['sha256'],actual,'VERIFY ONLY actual stopped complete R5 fountain',before=True)
    raw=(json.dumps(plan,separators=(',',':'))+'\n').encode()
    documents={'plaza.json':raw,'actual-dry-native-BEFORE.json':raw}
    manifest={'format':'awft-r5-cohesive-guardian-fountain:1','created':utcnow(),
              'source_sha256':digest(Path(__file__)),'checkpoint_id':checkpoint['id'],
              'checkpoint_sha256':checkpoint['sha256'],'actual_dry_checkpoint':True,
              'previous_actual_R5_geometry_sha256':SOURCE_GEOMETRY,
              'retained_actual_native_state_derivations':derivations,'saved_sources':saved_sources,
              'actual_saved_zero_speeds':speeds,'checks':checks,'world_writes':0,'native_actions':0,
              'artistic_acceptance':False,'storage_guard':reserve,
              'files':{name:{'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest()}
                       for name,content in documents.items()}}
    documents['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    if sum(map(len,documents.values())) > 16*1024**2:
        raise UserError('Finite current dry binding output exceeded')
    output.mkdir()
    for name,content in documents.items():(output/name).write_bytes(content)
    (output/'manifest.json.complete').write_text(digest(output/'manifest.json')+'\n')
    return {'folder':str(output),'manifest_sha256':digest(output/'manifest.json'),
            'plan_sha256':digest(output/'plaza.json'),'blocks':len(actual),'native_actions':0,'world_writes':0}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(prepare(args.home,args.output)))
