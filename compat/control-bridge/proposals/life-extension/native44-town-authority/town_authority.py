"""Read-only authored-site authority for the existing single LIFE producer."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path


def town_box(bounds):
    if len(bounds)!=6 or any(type(v) is not int for v in bounds) or any(bounds[i]>bounds[i+3] for i in range(3)):
        raise ValueError('Six exact town known bounds required')
    if any(abs(bounds[i])>30000000 for i in (0,2,3,5)) or bounds[1]<-64 or bounds[4]>319:
        raise ValueError('Finite native world bounds required')
    count=math.prod(bounds[i+3]-bounds[i]+1 for i in range(3))
    if count>4096 or any(bounds[i+3]-bounds[i]+1<5 for i in range(3)):
        raise ValueError('Complete finite five-cell minimum FULL town field required')
    return count


def _point(value):
    if not isinstance(value,list) or len(value)!=3 or any(type(v) is not int for v in value):
        raise ValueError('Literal authored town coordinate required')
    if abs(value[0])>30000000 or abs(value[2])>30000000 or not -64<=value[1]<=319:
        raise ValueError('Finite native coordinate required')
    return tuple(value)


def _inside(bounds,p):return all(bounds[i]<=p[i]<=bounds[i+3] for i in range(3))


def read_authority(home,registry,path,bounded,owned,kinds):
    """No inferred room sites. Each reviewed site names exact authored source cells.

    Source authority remains immutable across restart. A current stopped FULL
    habitat preimage/native verification is independently required by each request.
    """
    if path is None:return None,{}
    document=bounded(path,4*1024**2)
    if document.get('format')!='awft-town-life-authority:1' or any(str(document.get(k))!=str(registry[k]) for k in ('seed','world_path')):
        raise ValueError('Typed authored town authority for this actual world required')
    checkpoint=document.get('source_checkpoint_sha256','')
    if len(checkpoint)!=64 or any(c not in '0123456789abcdef' for c in checkpoint):
        raise ValueError('Exact authored source checkpoint required')
    sources=document.get('sources',[])
    if not 1<=len(sources)<=4 or not 1<=len(document.get('sites',[]))<=16:
        raise ValueError('Finite source-bound town batch required')
    masks={};total=0;raw_bytes=0
    for row in sources:
        if set(row)!={'name','kind','plan','native_verify'} or row['kind']!='AUTHORED_FULL_PLAN' or row['name'] in masks:
            raise ValueError('Distinct actual authored FULL plan/native physical verification required')
        ref=row['plan'];plan_path=home/ref['path'];actual=owned(home,plan_path)
        if actual!={k:ref[k] for k in ('path','bytes','sha256')}:raise ValueError('Authored town source changed')
        raw_bytes+=actual['bytes']
        if raw_bytes>16*1024**2:raise ValueError('Town source bytes exceed finite batch')
        plan=bounded(plan_path,8*1024**2)
        if plan.get('format')!='awft-native-settlement:1' or any(str(plan.get(k))!=str(registry[k]) for k in ('seed','world_path')):
            raise ValueError('A reservation/forest rectangle is not authored town geometry')
        blocks=plan['blocks'];total+=len(blocks)
        if not blocks or total>250000:raise ValueError('Finite complete authored source cell budget exceeded')
        proof_ref=row['native_verify'];proof_path=home/proof_ref['path']
        if owned(home,proof_path)!={k:proof_ref[k] for k in ('path','bytes','sha256')}:raise ValueError('Actual authored-source verification changed')
        proof=bounded(proof_path,512*1024);complete=proof_path.with_name(proof_path.name+'.complete')
        if complete.is_symlink() or not complete.is_file() or complete.stat().st_size>128 or complete.read_text().strip()!=proof_ref['sha256']:
            raise ValueError('Actual immutable native source completion digest required')
        if proof.get('operation')!='verify' or proof.get('plan_sha256')!=ref['sha256'] or proof.get('blocks')!=len(blocks) or proof.get('failures')!=0 or proof.get('error') or proof.get('status')!='verified actual block identities, orientation, block entities and supplied inventories' or proof.get('cleanup_required',False) or proof.get('temporary_tickets_remaining',0) or proof.get('cleanup_passed',True) is not True:
            raise ValueError('Actual source full physical verification required; no construction/function acceptance inferred')
        mask=set()
        for cell in blocks:
            if len(cell)!=4 or type(cell[3]) is not int or not 0<=cell[3]<len(plan['palette']):raise ValueError('Exact authored plan cell/palette required')
            point=_point(cell[:3])
            if point in mask:raise ValueError('Duplicate source cell')
            mask.add(point)
        masks[row['name']]=mask
    sites={};cell_budget=0
    for row in document['sites']:
        if set(row)!={'id','source_names','species','known_bounds','occupancy_cells','standing_positions'} or row['id'] in sites:
            raise ValueError('Distinct reviewed town site, without traits or claimed POI assignment, required')
        bounds=row['known_bounds'];town_box(bounds)
        if not row['source_names'] or len(set(row['source_names']))!=len(row['source_names']) or any(k not in masks for k in row['source_names']):
            raise ValueError('Town site must name authenticated authored sources')
        authored=set().union(*(masks[k] for k in row['source_names']));cells=set()
        for value in row['occupancy_cells']:
            point=_point(value);cell_budget+=1
            if point in cells or point not in authored or not _inside(bounds,point) or cell_budget>65536:
                raise ValueError('Town occupancy cannot invent an unwritten AIR/body cell')
            cells.add(point)
        standing=set()
        for value in row['standing_positions']:
            p=_point(value)
            if p not in cells or (p[0],p[1]-1,p[2]) not in authored or (p[0],p[1]+1,p[2]) not in cells or p in standing or len(standing)>=64:
                raise ValueError('Town standing route needs reviewed authored floor/body/head cells')
            standing.add(p)
        if not cells or not standing or not row['species'] or len(set(row['species']))!=len(row['species']) or any(k not in kinds for k in row['species']):
            raise ValueError('Explicit body, route and same-curation species required')
        sites[row['id']]={'known_bounds':bounds,'cells':cells,'standing':standing,'species':set(row['species'])}
    return document,sites


def member(authorities,site,feet,known):
    source=authorities.get(site['town_site'])
    if source is None or site['entity'] not in source['species'] or known!=source['known_bounds']:
        raise ValueError('Member differs from explicit authored town site')
    if tuple(math.floor(v) for v in feet) not in source['standing']:
        raise ValueError('Town seed footing was not explicitly reviewed')
    return source


def route(source,point):
    if tuple(point) not in source['standing']:raise ValueError('Town route point was not explicitly reviewed')


def cell(source,point):
    if tuple(point) not in source['cells']:raise ValueError('Town body/POI/water point is outside authored occupancy')
