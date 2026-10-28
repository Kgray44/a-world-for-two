"""Six natural pavers join the already-existing accepted three-wide stairs.

No active world call. Original stairs, pavers, structures and every BE stay
untouched. The old generic 'new stairs needed' assumption was wrong: the exact
current save already contains the graded accepted threshold.
"""
from __future__ import annotations
import hashlib,json,time
from pathlib import Path
from control_room.common import UserError,digest,read_json
from tools.artistic_north_bank_east import NorthTerrain,native_payload,preservation,AIR,SOFT,NORTH_SOFT,GROUND
from tools.artistic_bridge_refinement import flatten
from tools.artistic_materials import require_outdoor_rule
from tools.playtest import guard
from tools.settlement_attractions import base,properties

PROTOTYPE_SHA='831a8e6eb1e757502328d259d0846fff14e325e8ed704dae527cd7fc90cdbc37'
MIB=1024**2

def authored_cells(home,custody):
    cells={}
    for row in custody:
        p=Path(home)/row['relative']
        if digest(p)!=row['sha256']:raise UserError('Exact retained source changed')
        d=read_json(p);cells.update(flatten(d.get('physical_plan',d)))
    return cells

def checked_connector(actual,authored):
    delta={}
    for x in (1289,1290):
        for z in (-1241,-1240,-1239):
            p=(x,63,z)
            if base(actual[p]) not in GROUND:raise UserError('Exact natural dry63-level gap required')
            delta[p]='minecraft:andesite' if z==-1240 else 'minecraft:stone_bricks' if x==1289 else 'minecraft:cobblestone'
            for y in (64,65):
                q=x,y,z
                if base(actual[q]) not in AIR|SOFT|NORTH_SOFT or 'waterlogged=true' in actual[q]:raise UserError('Only ordinary grass/air may be cleared from the narrow gap')
                delta[q]='minecraft:air'
    for q,value in delta.items():
        if q in authored and (base(authored[q]) not in AIR or value!='minecraft:air'):raise UserError('Connector must preserve every accepted authored solid/AIR expectation')
    require_outdoor_rule(delta,'six natural threshold pavers and twelve grass/headroom cells')
    return delta

def prepare(home,prototype,checkpoint_id,checkpoint_sha):
    home=Path(home).resolve();prototype=Path(prototype).resolve()
    if not home.is_relative_to(Path('D:/A World for Two/staging/world-tests').resolve()) or not prototype.is_relative_to(home/'staging'):raise UserError('Private artistic proposal only')
    reserve=guard(MIB,4*MIB);receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    if receipt.get('verified') is not True or receipt.get('id')!=checkpoint_id or receipt.get('sha256')!=checkpoint_sha or digest(prototype)!=PROTOTYPE_SHA:raise UserError('Exact current stopped checkpoint and frozen Rose ReachR1b required')
    registry=read_json(home/'dashboard/settlement/registry.json');_,custody=preservation(home,registry);old=authored_cells(home,custody);future=flatten(read_json(prototype));terrain=NorthTerrain(home,receipt,registry);actual={};retained={}
    try:
        for x in (1289,1290):
            for z in (-1241,-1240,-1239):
                for y in (63,64,65):
                    q=x,y,z;actual[q]=terrain.state(*q)
                    if actual[q] is None or q in terrain.entities:raise UserError('Exact FULL gap without saved BE required')
        delta=checked_connector(actual,old)
        for z in (-1241,-1240,-1239):
            for x,y in ((1284,66),(1285,65),(1286,64)):
                q=x,y,z;state=terrain.state(*q);fields=properties(state)
                if base(state)!='minecraft:stone_brick_stairs' or any(fields.get(k)!=v for k,v in {'facing':'west','half':'bottom','shape':'straight','waterlogged':'false'}.items()):raise UserError('Existing accepted graded staircase differs; no replacement allowed')
                retained[q]=state
            q=1288,63,z;retained[q]=terrain.state(*q)
            if base(retained[q]) not in GROUND|{'minecraft:stone_bricks','minecraft:andesite','minecraft:cobblestone'}:raise UserError('Retained lower landing support differs')
            for x in range(1284,1291):
                for y in range(67,69):
                    q=x,y,z;state=terrain.state(*q)
                    if base(state) not in AIR:raise UserError('Existing full stair passage has a new obstruction')
                    retained[q]=state
        sources=terrain.snapshot.sources
    finally:terrain.close()
    target=retained|delta
    target.update({(1291,63,z):future[1291,63,z] for z in (-1241,-1240,-1239)})
    documents={'gap-before-VERIFY-ONLY.json':native_payload(registry,actual,checkpoint_sha,'VERIFY ONLY — six natural gap columns'),
               'retained-stairs-VERIFY-ONLY.json':native_payload(registry,retained,checkpoint_sha,'VERIFY ONLY — accepted stairs/landing/headroom, never place'),
               'six-paver-connector.json':native_payload(registry,delta,checkpoint_sha,'PLACE ONLY six natural pavers and twelve exact grass/air cells; no stair/source replay'),
               'connected-threshold-VERIFY-ONLY.json':native_payload(registry,target,checkpoint_sha,'VERIFY ONLY — unchanged accepted stairs joined to actual Rose ReachR1b')}
    raw={n:(json.dumps(d,separators=(',',':'))+'\n').encode() for n,d in documents.items()}
    manifest={'format':'awft-six-paver-north-town-connector:1','checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'prototype_sha256':PROTOTYPE_SHA,'source_sha256':digest(Path(__file__)),'targets':18,'new_pavers':6,'old_stair_or_paver_changes':0,'old_BEs_or_tags_replayed':0,'world_actions':0,'sources':sources,'reserve':reserve,'native_sequence':'Verify exact gap and retained stairs, place frozenR1bprototype and18-cell connector once, verify connected threshold. Actual native walking/art still pending.','files':{n:{'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()} for n,v in raw.items()}}
    raw['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    if sum(map(len,raw.values()))>4*MIB:raise UserError('Finite connector proof exceeded')
    out=home/'staging'/('north-bank-six-paver-connector-'+str(time.time_ns()));out.mkdir()
    for name,value in raw.items():
        with (out/name).open('xb') as f:f.write(value)
    return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'files':manifest['files'],'world_actions':0}
