"""Genuine disjoint destinations for the superseded identities/private holds.

Keeps every approved ground mass unchanged. No native command, active catalogue
rewrite or invented inventory is emitted. Root must review a new catalogue seal.
"""
from __future__ import annotations
import argparse,json,time
from pathlib import Path
from control_room.common import UserError,digest
from tools.artistic_east_tortuga_retrofit import checked
from tools.artistic_eastern_urban_custody import canonical
from tools.native_eastern_relocation import LAYOUT
from tools.playtest import guard

MIB=1024**2


def overlaps(a,b):return all(a[i]<=b[i+3] and b[i]<=a[i+3] for i in range(3))
def horizontal(a,b):return a[0]<=b[3] and b[0]<=a[3] and a[2]<=b[5] and b[2]<=a[5]


def prepare(home):
    home=Path(home).resolve();reserve=guard(MIB,2*MIB);layout=checked(home/LAYOUT[0],LAYOUT[1],8*MIB)
    identities=[r for r in layout['exact_proposed_native_pod_transfers'] if not any(r['translation_xyz'])]
    retained=layout['retained_in_place_private_anchor_Inn_room_capsules']
    if len(identities)!=2 or len(retained)!=3:raise UserError('Exact two identities and three former private holds required')
    requests=[{'id':r['pod_id'],'source':r['source_support_bounds_xyz'],'old_building':r['destination_building'],'kind':'OLD_IDENTITY_MUST_RELOCATE'} for r in identities]
    requests+=[{'id':r['id'],'source':r['source_support_bounds_xyz'],'old_building':'lantern-harbor-inn','kind':'FORMER_PRIVATE_HOLD_MUST_RELOCATE','native_full_custody':'Include every actual BE/bed part/door and the real cartographer within this exact box; fresh saved/native census required'} for r in retained]
    # The actual retained ground-room bound already includes BOTH bluebed
    # parts and the real cartographer. Preserve this exact larger104-column
    # room instead of clipping it to the old inventory-only inner box.
    first=next(r for r in requests if r['id']=='rose-reach/compass:room:0')
    if not all(first['source'][i]<=q[i]<=first['source'][i+3] for q in ((1296,65,-1250),(1296,65,-1249),(1300,65,-1255)) for i in range(3)):
        raise UserError('Actual bed/job closure must remain inside its real source box')
    occupied=[r['destination_support_bounds_xyz'] for r in layout['exact_proposed_native_pod_transfers'] if any(r['translation_xyz'])]
    candidates=[]
    for house in layout['buildings']:
        for index,m in enumerate(house['masses']):
            for level in range(m['storeys']):candidates.append((house,index,m,level,m['floor_y']+level*4))
    results=[]
    # Allocate the largest genuine room first, not a small-room packing that
    # later forces a truncated bed/stock capsule.
    requests.sort(key=lambda r:-((r['source'][3]-r['source'][0]+1)*(r['source'][5]-r['source'][2]+1)))
    for request in requests:
        a=request['source'];w,l=a[3]-a[0]+1,a[5]-a[2]+1;possible=[]
        for house,index,m,level,y in candidates:
            x0,z0,x1,z1=m['bounds_xz']
            for x in range(x0,x1-w+2):
                for z in range(z0,z1-l+2):
                    b=[x,y,z,x+w-1,y+3,z+l-1]
                    if horizontal(a,b) or any(overlaps(b,v) for v in occupied):continue
                    compatible=house['program'] in ('inn','galley','archive','charts','warehouse')
                    score=(0 if request['kind'].startswith('FORMER') and house['program']=='inn' else 1 if compatible else 2,
                        abs(x-a[0])+abs(z-a[2]),abs(y-a[1]),house['id'],x,z)
                    possible.append((score,b,house,index,level))
        if not possible:raise UserError('No genuine disjoint unoccupied approved-mass destination for '+request['id'])
        _,b,house,index,level=min(possible,key=lambda v:v[0]);occupied.append(b)
        results.append({**request,'destination_building':house['id'],'destination_mass':index,'destination_floor':level,'destination_bounds_xyz':b,
            'translation_xyz':[b[i]-a[i] for i in range(3)],'rotation':'NONE','horizontal_source_destination_disjoint':True,'approved_floor_mass_unchanged':True,
            'current_destination_FULL_air_support_entity_proof':'NOT RUN; actual readback and dependency/source closure required',
            'native_action_authorized_by_this_file':False})
    out=home/'staging'/('eastern-required-policy-relocations-'+str(time.time_ns()));out.mkdir();record={'format':'awft-eastern-owner-all-old-buildings-relocate-addendum:1',
        'original_approved_floor_layout_sha256':LAYOUT[1],'all_floor_masses_unchanged':True,'new_owner_rule':'No rejected Eastern old building remains; three large original north works and original approved core only are protected',
        'protected_northern_structures':[{'name':'The Drowned Rose','main_xz':[1291,-1290,1312,-1269],'galley_xz':[1288,-1286,1292,-1278]},
            {'name':'Evgesha765 original pirate tavern','bounds_xz':[1282,-1337,1309,-1297]}, {'name':'Shabani1 original fisherman shop','bounds_xz':[1314,-1349,1334,-1316]}],
        'genuine_proposed_relocations':results,'old_db5e_catalogue_rewritten':False,'new_catalogue_and_native_guard_review_required':True,
        'toolbox':'REQUIRES actual native handler/link/drop-semantic review; no assumption empty and no permanent keep exemption',
        'source_sha256':digest(Path(__file__)),'construction_forbidden':True,'native_actions':0,'reserve_guard':reserve}
    (out/'new-destinations-SOURCE-ONLY.json').write_bytes(canonical(record)+b'\n');return {'folder':str(out),'sha256':digest(out/'new-destinations-SOURCE-ONLY.json'),'moves':[{k:r[k] for k in ('id','source','destination_building','destination_bounds_xyz','translation_xyz')} for r in results]}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.home),indent=2))
