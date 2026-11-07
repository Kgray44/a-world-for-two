"""Freeze revised approved-XZ room allocations and their complete source order.

This is a source handoff, not a replacement runtime catalogue or native proof.
"""
from __future__ import annotations
import argparse,copy,json,time
from collections import defaultdict
from pathlib import Path
from control_room.common import UserError,digest
from tools.artistic_east_tortuga_retrofit import checked
from tools.artistic_eastern_urban_custody import canonical
from tools.native_eastern_relocation import LAYOUT,SEALED_CATALOG_SHA
from tools.native_eastern_relocation_current import CATALOG
from tools.playtest import guard

MIB=1024**2
NEW=('staging/eastern-required-policy-relocations-1793216708724099400/new-destinations-SOURCE-ONLY.json','862e6e8707062908d15a6639b493d6b098257df7fa40dae90731d967b9f0fb69')
TAGS=('staging/eastern-urban-current-custody-1793210273627204600/current-BEs-FULL-TYPED-PRIVATE.jsonl','80faa996611be38973cd41dcf222da95f6a763758df34e9612da13652b706848')
OVERRIDES={
 'rose-reach/curios:room:2':([1322,69,-1242,1329,72,-1234],[0,-3,-4]),
 'rose-reach/outfitter:room:1':([1321,74,-1242,1328,77,-1234],[14,6,-4]),
 'eastern22/blue-quilt:room:1':([1274,64,-1197,1282,67,-1191],[9,-4,-7]),
}

def overlaps(a,b):return all(a[k]<=b[k+3] and b[k]<=a[k+3] for k in range(3))

def prepare(home):
    home=Path(home).resolve();reserve=guard(MIB,2*MIB)
    catalog=checked(home/CATALOG,SEALED_CATALOG_SHA,2*MIB);layout=checked(home/LAYOUT[0],LAYOUT[1],8*MIB);new=checked(home/NEW[0],NEW[1],2*MIB)
    origin={r['pod_id']:r for r in layout['exact_proposed_native_pod_transfers']}
    rows={r['id']:{'id':r['id'],'source_bounds_xyz':copy.deepcopy(r['source_bounds_xyz']),'destination_bounds_xyz':copy.deepcopy(r['destination_bounds_xyz']),
        'translation_xyz':copy.deepcopy(r['translation_xyz']),'destination_building':origin[r['id']]['destination_building'],
        'destination_mass':origin[r['id']]['destination_mass'],'native_inventory_reviewed':r['supported']} for r in catalog['capsules']}
    for ident,(bounds,delta) in OVERRIDES.items():
        rows[ident]['destination_bounds_xyz']=list(bounds);rows[ident]['translation_xyz']=list(delta)
        if ident=='eastern22/blue-quilt:room:1':rows[ident]['destination_mass']=1
    for r in new['genuine_proposed_relocations']:
        if r['id'] in rows:raise UserError('New policy allocations must not replace old transaction rows')
        rows[r['id']]={'id':r['id'],'source_bounds_xyz':r['source'],'destination_bounds_xyz':r['destination_bounds_xyz'],
            'translation_xyz':r['translation_xyz'],'destination_building':r['destination_building'],'destination_mass':r['destination_mass'],
            'native_inventory_reviewed':False,'reason':'Fresh full source/typed bed closure and new catalogue review required'}
    if len(rows)!=98:raise UserError('Exactly98 genuine room allocations required')
    for i,r in rows.items():
        a,b,d=r['source_bounds_xyz'],r['destination_bounds_xyz'],r['translation_xyz']
        if not any(d) or any(b[k]-a[k]!=d[k] or b[k+3]-a[k+3]!=d[k] for k in range(3)):
            raise UserError('Resized/identity/noncardinal room allocation')
        house=next(h for h in layout['buildings'] if h['id']==r['destination_building']);m=house['masses'][r['destination_mass']];x0,z0,x1,z1=m['bounds_xz']
        if not(x0<=b[0]<=b[3]<=x1 and z0<=b[2]<=b[5]<=z1):raise UserError('Allocation escaped the exact approved XZ mass')
        if any(overlaps(b,s['destination_bounds_xyz']) for j,s in rows.items() if i<j):raise UserError('Future destination overlap')
    if digest(home/TAGS[0])!=TAGS[1]:raise UserError('Exact original typed BE position custody required')
    positions=[]
    with (home/TAGS[0]).open(encoding='utf8') as stream:
        for line in stream:positions.append(tuple(json.loads(line)['position']))
    source_owner={};future=defaultdict(set);future_rows=[]
    for ident,r in rows.items():
        a=r['source_bounds_xyz'];d=r['translation_xyz'];r['expected_source_BE_positions']=[]
        for p in positions:
            if all(a[k]<=p[k]<=a[k+3] for k in range(3)):
                if p in source_owner:raise UserError('One actual BE cannot belong to two source captures')
                source_owner[p]=ident;r['expected_source_BE_positions'].append(list(p));q=tuple(p[k]+d[k] for k in range(3));future[q].add(ident)
                future_rows.append({'source':list(p),'destination':list(q),'capsule_id':ident})
    deps={i:set() for i in rows};reasons=[]
    for ident,r in rows.items():
        b=r['destination_bounds_xyz']
        for other,s in rows.items():
            if ident!=other and overlaps(b,s['source_bounds_xyz']):deps[ident].add(other);reasons.append({'before':other,'after':ident,'reason':'Closed FULL source box including AIR must remain unchanged until capture'})
        for x in range(b[0],b[3]+1):
            for z in range(b[2],b[5]+1):
                p=(x,b[1]-1,z)
                if p in source_owner and source_owner[p]!=ident:deps[ident].add(source_owner[p])
                for lower in future[p]:
                    if lower!=ident:deps[lower].add(ident)
    remain=set(rows);ordered=[]
    while remain:
        ready=sorted((i for i in remain if not(deps[i]&remain)),key=lambda i:(-rows[i]['destination_bounds_xyz'][1],i))
        if not ready:raise UserError('Revised complete source/support graph is cyclic: '+','.join(sorted(remain)))
        ident=ready[0];ordered.append(ident);remain.remove(ident)
    for ident,r in rows.items():r['required_preceding_native_capture_ids']=sorted(deps[ident])
    record={'format':'awft-eastern-room-allocation-addendum:4','original_immutable_catalog_sha256':SEALED_CATALOG_SHA,'approved_XZ_layout_sha256':LAYOUT[1],
        'new_owner_policy_addendum_sha256':NEW[1],'original_source_BE_positions_sha256':TAGS[1],'room_allocations':list(rows.values()),'native_move_order':ordered,
        'future_BE_positions':future_rows,'source_box_dependency_reasons':reasons,'changes_to_existing_destinations':OVERRIDES,
        'architecture_height_contract':{'tin-whistle':{'retained_room_floors':[64,69,74],'upper_ceiling_and_roof_raise':2,'actual_stair_risers_between_floors':5},
            'net-mender':{'room_blue_quilt1':'Approved low annex, floor64; main ground remains a new authored furnished room','retained_upper_room_floor':68}},
        'all_155_approved_floor_mass_XZ_unchanged':True,'original_transactions_and_ledgers_unchanged':True,
        'new_runtime_catalogue_and_all_fresh_native_guards_required':True,'toolbox_role':'Actual IItemHandler/filter/UUID/offline-link review still required; no keep exemption or empty assumption',
        'construction_forbidden':True,'native_actions':0,'source_sha256':digest(Path(__file__)),'reserve_guard':reserve}
    out=home/'staging'/('eastern-allocation-r4-'+str(time.time_ns()));out.mkdir();p=out/'allocation-SOURCE-ONLY.json';p.write_bytes(canonical(record)+b'\n')
    return {'folder':str(out),'sha256':digest(p),'rooms':len(rows),'acyclic_order':len(ordered),'destination_overlaps':0,'native_actions':0}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.home),indent=2))
