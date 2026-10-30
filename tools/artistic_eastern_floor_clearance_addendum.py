"""Pure-source held-room height correction; no archive/native/world operations.

Keeps all approved XZ masses and the other93 allocations literally unchanged.
Actual saved capture/catalogue, native ledger absence and architecture overlays
remain separate required gates; this file grants no construction permission.
"""
from __future__ import annotations
import argparse,copy,hashlib,json,time
from pathlib import Path
from control_room.common import UserError,digest,utcnow
from tools.artistic_east_tortuga_retrofit import checked
from tools.artistic_eastern_urban_custody import canonical
from tools.playtest import guard

MIB=1024**2
BASE='staging/eastern-self-overlap23-disjoint-DAG-1793219467452176700/allocation-SOURCE-ONLY.json'
BASE_SHA='517c1dab4c9d467fe8d072d86b5fb759aab51d493b6c6b229cde43849457bf18'
LIFT={
 'compass-bend/three-kestrels:room:1':(72,73,'worn-book',0),
 'eastern22/marigold-steps:room:1':(72,73,'lampblack',0),
 'eastern22/starlings-rest:room:0':(68,69,'navy-blue',0),
 'eastern22/roseate-corner:room:0':(68,69,'keel-store',0),
 'eastern22/starlings-rest:room:2':(64,68,'navy-blue',1),
}

def inside(p,b):return all(b[k]<=p[k]<=b[k+3] for k in range(3))
def intersects(a,b):return all(a[k]<=b[k+3] and b[k]<=a[k+3] for k in range(3))
def plane(p,b):return p[1]==b[1]-1 and b[0]<=p[0]<=b[3] and b[2]<=p[2]<=b[5]

def derive(base):
    data=copy.deepcopy(base);rows={r['id']:r for r in data['room_allocations']}
    if len(rows)!=98:raise UserError('Exact98 original rows required')
    changed=[]
    for ident,(old,new,building,mass) in LIFT.items():
        r=rows[ident];b=r['destination_bounds_xyz']
        if b[1]!=old or b[4]!=old+3 or r['destination_building']!=building or r['destination_mass']!=mass:
            raise UserError('Exact original held allocation required')
        before=copy.deepcopy(r);b[1]+=new-old;b[4]+=new-old;r['translation_xyz'][1]+=new-old
        r['prior_destination_bounds_xyz']=before['destination_bounds_xyz']
        r['prior_translation_xyz']=before['translation_xyz']
        r['changed_from_catalogue']=True
        changed.append({'id':ident,'building':building,'mass':mass,'before':before['destination_bounds_xyz'],'after':list(b),'floor_raise':new-old,
            'architecture':'Preserve other room levels; actual1-riser split-level links. KeelStore:5-riser primary stair/roof+1. NavyBlue annex: genuine ground+upper68/roof+4, split-level1-riser to main69.'})
    future=[];current=[]
    for r in rows.values():
        a,b=r['source_bounds_xyz'],r['destination_bounds_xyz']
        if any(a[k+3]-a[k]!=b[k+3]-b[k] for k in range(3)) or intersects(a,b):raise UserError('Dimensions/orientation/own-source closure failed')
        for p in r['expected_source_BE_positions']:
            current.append((r['id'],p));future.append({'capsule_id':r['id'],'source':p,'destination':[p[k]+r['translation_xyz'][k] for k in range(3)]})
    if len(future)!=610 or len({tuple(v['destination']) for v in future})!=610:raise UserError('Complete unique610 future BE positions required')
    ids=list(rows);overlaps=[]
    for i,ident in enumerate(ids):
        for other in ids[i+1:]:
            if intersects(rows[ident]['destination_bounds_xyz'],rows[other]['destination_bounds_xyz']):overlaps.append([ident,other])
    if overlaps:raise UserError('Future full destination collision')
    deps={ident:set() for ident in ids};reasons=[]
    def edge(after,before,why):
        if after==before:raise UserError('Own support/BE/source dependency remains')
        deps[after].add(before);reasons.append({'after':after,'before':before,'reason':why})
    for r in rows.values():
        ident=r['id'];b=r['destination_bounds_xyz']
        for other in rows.values():
            if ident!=other['id'] and intersects(b,other['source_bounds_xyz']):edge(ident,other['id'],'Closed full original source including AIR requires prior capture')
        for owner,p in current:
            if plane(p,b):edge(ident,owner,'Actual source BE before upper support preparation')
        for v in future:
            if plane(v['destination'],b):edge(v['capsule_id'],ident,'Upper support before lower destination introduces BE')
    ordered=[];remaining=set(ids)
    while remaining:
        ready=sorted(v for v in remaining if not(deps[v]&remaining))
        if not ready:
            internal=[r for r in reasons if r['after'] in remaining and r['before'] in remaining]
            raise UserError('Actual source/destination/BE-support dependency cycle: '+json.dumps(internal[:20],separators=(',',':')))
        ordered.extend(ready);remaining.difference_update(ready)
    for r in rows.values():r['required_preceding_native_capture_ids']=sorted(deps[r['id']])
    for ident in LIFT:
        r=rows[ident];a,b=r['source_bounds_xyz'],r['destination_bounds_xyz']
        if a[1]<=b[1]-1<=a[4] and not(b[3]<a[0] or a[3]<b[0] or b[5]<a[2] or a[5]<b[2]):
            raise UserError('Changed support plane still touches own source')
    original={r['id']:r for r in base['room_allocations']}
    if any(rows[v]['destination_bounds_xyz']!=original[v]['destination_bounds_xyz'] or rows[v]['translation_xyz']!=original[v]['translation_xyz'] for v in ids if v not in LIFT):
        raise UserError('Unrelated allocation changed')
    data.update(format='awft-eastern-floor-clearance-proposal:1',created=utcnow(),prior_allocation_sha256=BASE_SHA,
        future_BE_positions=future,native_move_order=ordered,source_box_dependency_reasons=reasons,
        lifted_rooms=changed,unchanged_other_destinations=98-len(LIFT),self_source_intersections=0,future_destination_intersections=0,
        exact_BE_support_DAG_nodes=98,own_source_support_intersections_for_changed_rows=0,
        runtime_catalogue_updated=False,actual_current_state_captured=False,native_actions=0,world_writes=0,construction_forbidden=True)
    data['native_gates']=['Root confirms none of the changed old/new transaction IDs has intent/completion/quarantine',
        'New bounded actual saved destination/support capture, retaining all raw source tags/contents',
        'Coordinated exact catalogue/main class pins and four split-level architecture overlays',
        'Fresh actual Native before/INSPECT/one MOVE with full NBT+slots, native part and survival proofs']
    return data

def prepare(home):
    home=Path(home).resolve();reserve=guard(MIB,4*MIB);base=checked(home/BASE,BASE_SHA,2*MIB);data=derive(base)
    out=home/'staging'/('eastern-floor-clearance-'+str(time.time_ns()));out.mkdir();p=out/'allocation-SOURCE-ONLY.json';p.write_bytes(canonical(data)+b'\n')
    manifest={'format':'awft-eastern-floor-clearance-bundle:1','allocation_sha256':digest(p),'bytes':p.stat().st_size,
        'source_sha256':digest(Path(__file__)),'prior_allocation_sha256':BASE_SHA,'changed_rooms':list(LIFT),'unchanged_other_destinations':98-len(LIFT),
        'DAG98':True,'native_actions':0,'construction_forbidden':True,'reserve_guard':reserve}
    (out/'manifest.json').write_bytes(canonical(manifest)+b'\n')
    return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),**manifest}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.home),indent=2))
