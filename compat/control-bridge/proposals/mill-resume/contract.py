"""Finite resume contract. This module never reads/writes a world or invokes Java.

The emitted source composite is VERIFY-ONLY. A fresh stopped-save preimage and
native inspection must be supplied later; historical source is not that proof.
"""
from __future__ import annotations
import copy
import hashlib
import json

SOURCE_SHAS=(
 '89fa2079962dedb7888aaf62ae2f18d094c373421a80ce0f91bda23ddb415af1',
 '747f4b1175fb6f525ecbfd5a51a7586119279f852264a383afafc88273d2973d',
 'bae3e86205a4cd64f509ec2beba1ef3f3fc905a280fdc0c73bbdf1fa114c304b')
MANIFEST_SHA='f4f9bd4cd1d3bc4ff100cfe9ba417b591e7e8ede23bb1b4e3c03deb7f600d2f5'
PARTIAL_SHA='e4f627a9baa367a267537504d017893f64537841a0d608eef5b1b8b4925bc239'
ACTIVE_SOURCE_SHA='4eba4ddfcb56d12b67ba4a6610447a5f4d4061e43a264762a1920571a9ba7d16'
GEOMETRY_SHA='ceeeabfc3ed1aee751074134edccc6de9ed3b0cf4308001203a9027e952a71af'
COUNT=7941
DETECTOR='create_hypertube:redstone_detector_tube_attachment'
ENTRANCES=((1331,71,-991),(1331,71,-943))
LEVERS={(1330,71,-991),(1330,71,-943)}
SOURCE_WATER={(x,73,-1001) for x in range(1306,1309)}
HYDRAULIC_AIR={(x,y,z) for x in range(1306,1309) for y in range(68,74) for z in range(-1001,-998)}

def encoded(value):
    return (json.dumps(value,separators=(',',':'),ensure_ascii=False)+'\n').encode()

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def flatten(plan):
    if plan.get('commands')!=[] or not isinstance(plan.get('block_entities'),list):
        raise ValueError('No construction commands; explicit verification-only BE list required')
    result={}
    for row in plan['blocks']:
        if len(row)!=4 or any(type(v) is not int for v in row):raise ValueError('Exact integer geometry rows required')
        p=tuple(row[:3])
        if p in result or not(1300<=p[0]<=1340 and 59<=p[1]<=85 and -1020<=p[2]<=-928):raise ValueError('Duplicate or escaped mill target')
        result[p]=plan['palette'][row[3]]
    return result

def geometry_sha(cells):
    return digest(''.join(','.join(map(str,p))+'\t'+state+'\n' for p,state in sorted(cells.items())).encode())

def composite(raw_sources):
    if len(raw_sources)!=3 or tuple(map(digest,raw_sources))!=SOURCE_SHAS:raise ValueError('All three exact reviewed sources required')
    documents=list(map(json.loads,raw_sources));cells={};tags={}
    for plan in documents:
        if any(plan.get(k)!=documents[0].get(k) for k in ('seed','world_path')):raise ValueError('Source world custody differs')
        cells.update(flatten(plan))
        for row in plan['block_entities']:tags[tuple(row['pos'])]=copy.deepcopy(row)
    if len(cells)!=COUNT or geometry_sha(cells)!=GEOMETRY_SHA:raise ValueError('Exact complete R3+94 mill source required')
    result=copy.deepcopy(documents[0]);result['palette']=sorted(set(cells.values()))
    lookup={s:n for n,s in enumerate(result['palette'])}
    result['blocks']=[[*p,lookup[s]] for p,s in sorted(cells.items())]
    result['block_entities']=[v for p,v in sorted(tags.items())]
    result['validation']='VERIFY ONLY - retained R3 architecture plus94 depth; never replay this plan or its original BE stocks'
    return result

def state_parts(value):
    name,_,tail=value.partition('[')
    return name,dict(pair.split('=',1) for pair in tail.rstrip(']').split(',')) if tail else {}

def qualify_preimage(source,current,manifest):
    """Recognize only documented native water/fillers/input flags, not arbitrary drift."""
    expected,actual=flatten(source),flatten(current)
    if expected.keys()!=actual.keys() or current.get('world_path')!=source.get('world_path') or current.get('seed')!=source.get('seed'):raise ValueError('Exact same source target set/world required')
    allowed={tuple(p) for p in manifest['systems']['hypertube']['native_collision_cells']}
    fillers=[];water=[]
    for pos,before in expected.items():
        a,props=state_parts(actual[pos]);b,fields=state_parts(before)
        if a!=b:
            if b=='minecraft:air' and a=='create_hypertube:tube_path' and pos in allowed:fillers.append(pos);continue
            if b=='minecraft:air' and a=='minecraft:water' and pos in HYDRAULIC_AIR and props.keys()<= {'level'} and 0<=int(props.get('level','0'))<=15:water.append(pos);continue
            raise ValueError('Unrelated current native identity/air drift: '+str(pos))
        variable={'locked','powered'} if pos in ENTRANCES else {'powered'} if pos in LEVERS else set()
        if any(props.get(k)!=v for k,v in fields.items() if k not in variable):raise ValueError('Current structural state differs: '+str(pos))
        if any(props.get(k) not in ('true','false') for k in variable):raise ValueError('Native input flags must be real booleans')
        if pos in ENTRANCES and (props.get('power','0')!='0' or props.get('locked')!=props.get('powered')):raise ValueError('Uncertain native input memory must not be toggled')
    if len(fillers)!=42:raise ValueError('The exact six persisted seven-cell native fillers are required')
    for p in SOURCE_WATER:
        if state_parts(actual[p])!=('minecraft:water',{'level':'0'}):raise ValueError('Original native hydraulic source is missing')
    return {'targets':len(actual),'retained_filler_cells':42,'hydraulic_water_cells':len(water),'source_geometry_sha256':GEOMETRY_SHA}

def qualify_partial(partial):
    if partial.get('phase')!='WAIT_MODE' or partial.get('actual_wheat_feed_performed') is not False or partial.get('train_created') is not False or partial.get('cleanup_passed') is not True or partial.get('remaining_owned_tickets')!=0:raise ValueError('Only clean pre-feed WAIT_MODE partial is eligible')
    rows=partial.get('native_tube_links',[])
    if len(rows)!=6 or len({r['uuid'] for r in rows})!=6:raise ValueError('Six distinct retained native links required')
    for n,row in enumerate(rows):
        if row['from']!=[1331,71,-991+n*8] or row['to']!=[1331,71,-983+n*8] or row['native_collision_cells']!=7 or row.get('native_filler_owner_and_shape_verified') is not True or row.get('native_distance')!=8:raise ValueError('Retained native link provenance differs')

def require_resume_stock(inspection):
    if inspection.get('operation')!='inspect' or inspection.get('cleanup_passed') is not True or inspection.get('remaining_owned_tickets')!=0 or 'error' in inspection:raise ValueError('Fresh clean native resume inspection required')
    missing=inspection.get('missing_owned_detectors')
    if missing not in (0,1,2) or inspection.get('actual_detector_stock',-1)<missing or inspection.get('actual_wheat_stock')!=16 or inspection.get('actual_single_16_wheat_stack') is not True or inspection.get('actual_iron_stock',0)<1:raise ValueError('Actual detector/input stocks are insufficient; no synthetic stock is allowed')
    stock=inspection.get('native_resume_stock')
    if not isinstance(stock,dict) or stock.get('position')!=[1313,68,-994] or len(stock.get('slots',[]))!=27:raise ValueError('Actual complete native starter inventory snapshot required')
    return copy.deepcopy(stock)
