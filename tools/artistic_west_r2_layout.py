"""Measured, individually composed western R2 massing/lanes; never construction.

The first W3 native preview and its photo correction establish the style. These
further masses remain unmodeled pending that review and real inventory custody.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib,json,time
from pathlib import Path

from control_room.common import UserError,digest,read_json
from tools.artistic_west_r2_frontage import rect,construct,LABELS,DEFAULT_ORIGIN
from tools.artistic_west_r2_study import ZIP
from tools.artistic_bridge_refinement import flatten
from tools.playtest import guard

MIB=1024**2
GEOGRAPHY=('staging/west-r2-measured-study-1793167023600466100/geography-ONLY.json','c3ff3b9e91f7afd82728d76a9f80a730d056b92b53d9aab56b71761d61268453')
HALL={'name':'Grand’s Captain’s Head-inspired hall','bounds_xz':[1032,-1294,1059,-1277],
      'status':'Exact final575 SOURCE reservation; native construction and art acceptance still pending',
      'source_reservation':'staging/artistic-captains-rest-1793170982583234800/future-solid-AIR-route-reservation-ONLY.json',
      'source_reservation_sha256':'b4716f849de37fa9b887b5531ff93d53ce3300814f885cc93da11c007a95da54',
      'thresholds':[[1037.5,64,-1276.5],[1038.5,64,-1276.5]],
      'hollow_preserved':'Keep1042/1043,-1277 natural gravel with AIR below; no new floor/porch support there'}


def masses():
    """Explicit distinct plans follow real coast notches; no lot/grid generator."""
    return [
      ('gullwatch','Gullwatch lantern home',rect(1018,-1308,1025,-1298)-rect(1024,-1304,1025,-1301),3,'south','Narrow hooked sea-end home, lower stair wing around the real eastern inlet; one steep muted slate gable.'),
      ('needle-hook','Needle Hook',rect(1013,-1294,1020,-1283)-{(1013,-1294),(1013,-1293),(1013,-1292)},2,'east','Chamfered needleworker home, broad side casement and low open work porch turning into the headland lane.'),
      ('bilge-books','The Bilge Book',rect(1024,-1292,1030,-1282)-{(1030,-1282),(1029,-1282)},3,'west','Slender bookbinder with a tucked entry, upper reading oriel and stepped rear roof facing Needle Hook across three metres.'),
      ('sea-fen','Sea Fen remedies',rect(1056,-1305,1067,-1296)|rect(1063,-1295,1067,-1294),2,'south','Substantial bent herbal shop/house, one lower glazed east workroom and a shared forecourt pocket beside the hall reserve, not one rectangular roof slab.'),
      ('rigging','The Rigging House',rect(1063,-1290,1069,-1278)-{(1063,-1278),(1063,-1279)},3,'west','Narrow tall ropeworker’s house faces the hall flank; shallow side stair bow and irregular high window.'),
      ('cliff-gull','The Cliff Gull',rect(984,-1277,992,-1270)-{(984,-1277),(985,-1277),(984,-1276)},2,'east','Western quay-edge sailor home with a cut corner, dark shingled low annex and sheltered street-side bench.'),
      ('net-mender','Net Mender’s Window',rect(996,-1280,1003,-1274)-{(996,-1280),(1003,-1274)},2,'south','Shallow net-and-canvas workshop set NORTH of the real wet inlet; its work hatch meets the crooked quay lane.'),
      ('lost-tide','The Lost Tide',rect(1006,-1275,1013,-1266)-{(1013,-1275),(1013,-1274)},3,'west','Asymmetric ship’s carpenter home with a lower open tool bay and one real projecting upper reading window.'),
      ('blue-gull','Blue Gull pantry',rect(1105,-1252,1112,-1245)-{(1112,z) for z in range(-1250,-1246)},2,'east','Bent pantry turns its east wall back from the measured water nib; a low kitchen wing meets the station approach.'),
      ('small-salt','Small Salt',rect(1115,-1264,1123,-1256)-{(1115,-1264),(1116,-1264),(1123,-1256)},2,'south','Uneven seaward cottage, broad weathered upper casement and a little recessed front shelter.'),
      ('kettle-bend','Kettle Bend',rect(1118,-1252,1125,-1245)-{(1118,-1245),(1118,-1246)},3,'west','Tall small chandlery with an angled porch, narrow high dormer and a lower repair room; two-wide lane wraps the real inlet.'),
      ('lantern-ferry','Lantern Ferry',rect(1104,-1242,1112,-1235)-{(1104,-1242),(1112,-1235)},2,'east','Lower crooked ferry home/workroom; existing weaver inventory anchors must be retained inside its integrated redesign or real custody completed.'),
      ('reed-lookout','Reed Lookout',rect(1116,-1242,1123,-1233)-{(1123,-1233),(1123,-1234),(1116,-1242)},3,'west','Taller opposite return, fine projecting window and a chamfered stair corner; forms a two-to-three-metre lane with Lantern Ferry.'),
      ('mugs-mending','Mugs & Mending',rect(1126,-1230,1133,-1221)-{(1126,-1230),(1127,-1230),(1133,-1221)},2,'east','A turned mender/tea room at the neck bend, lower snug and corner shop window; no broad empty arrival lawn.'),
    ]


# These are authored directional intentions, not approved exact walking masks.
# Any wet shoulder is reported, never paved or silently narrowed to obtain pass.
LANES=(
 ('western-crooked-quay',3,[(993,-1274),(1004,-1274),(1006,-1266),(1014,-1265),(1026,-1265),(1027,-1261),(1035,-1261),(1037,-1256),(1047,-1256),(1054,-1254),(1066,-1256),(1070,-1261)]),
 ('headland-hook',2,[(1014,-1265),(1012,-1276),(1022,-1283),(1022,-1294),(1021,-1305)]),
 ('hall-porch-turn',2,[(1022,-1286),(1028,-1286),(1028,-1275),(1036,-1275),(1037,-1277)]),
 ('hall-east-lane',2,[(1046,-1275),(1059,-1275),(1061,-1278),(1062,-1288),(1061,-1292),(1062,-1294)]),
 ('west-station-approach',2,[(1080,-1251),(1085,-1252),(1093,-1252),(1096,-1251),(1100,-1252)]),
 ('neck-inlet-turn',2,[(1100,-1252),(1105,-1253),(1116,-1253),(1122,-1253),(1122,-1244),(1113,-1243),(1110,-1238),(1110,-1230),(1124,-1227),(1144,-1225),(1160,-1224),(1170,-1216),(1186,-1216)]),
)


def stroked(points,width):
    cells=set();start=-(width//2) if width%2 else 0
    for (ax,az),(bx,bz) in zip(points,points[1:]):
        steps=max(abs(ax-bx),abs(az-bz))
        for n in range(steps+1):
            x=round(ax+(bx-ax)*n/max(1,steps));z=round(az+(bz-az)*n/max(1,steps))
            cells.update((x+dx,z+dz) for dx in range(start,start+width) for dz in range(start,start+width))
    return cells


def prepare(home):
    home=Path(home).resolve();reserve=guard(2*MIB,16*MIB)
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve():raise UserError('Private layout study only')
    if digest(home/GEOGRAPHY[0])!=GEOGRAPHY[1]:raise UserError('Exact saved one-metre locator required')
    if digest(home/HALL['source_reservation'])!=HALL['source_reservation_sha256']:raise UserError('Retain Grand’s exact final hall/left-exit reservation')
    data=read_json(home/GEOGRAPHY[0]);land={tuple(r['xz']):r for r in data['columns']};north={q for q,r in land.items() if r['north_connected']}
    current=read_json(home/'dashboard/settlement/backup-receipt.json');registry=read_json(home/'dashboard/settlement/registry.json')
    if digest(home/ZIP[0])!=ZIP[1]:raise UserError('Retain the exact placed western zipline/flight reservation')
    zip_field=set(flatten(read_json(home/ZIP[0])))
    p=construct(registry);ox,oy,oz=p.origin
    fixed={k:{(x+ox,z+oz) for x,z in v} for k,v in p.main.items()}
    fixed['Grand hall']=rect(*HALL['bounds_xz'])
    plots=[];assigned=set()
    for ident,name,cells,levels,face,story in masses():
        failures=[list(q) for q in sorted(cells) if q not in north]
        conflicts={k:len(cells&other) for k,other in fixed.items() if cells&other}
        zip_conflict=[q for q in zip_field if (q[0],q[2]) in cells and 63<=q[1]<=64+4*levels+6]
        if zip_conflict:raise UserError('Future main mass conflicts with placed zipline/flight height envelope: '+ident)
        if failures or conflicts:raise UserError('Explicit authored mass needs redesign, not water infill/retained prototype demolition: '+str((ident,failures[:8],conflicts)))
        if cells&assigned:raise UserError('Authored future masses overlap')
        assigned.update(cells)
        plots.append({'id':ident,'name':name,'main_cells_xz':[list(q) for q in sorted(cells)],'storeys':levels,'front':face,'design':story,
            'north_connected_locator_membership':'PASS exact1m historical locator only','current_kinds':dict(Counter(land[q]['kind'] for q in cells)),
            'native_body_dry_support_and_inventory_custody':'PENDING actual current preimage and native class/slot check','geometry_modeled':False,'replication_held':True})
    routes=[]
    for ident,width,points in LANES:
        cells=stroked(points,width);bad=[list(q) for q in sorted(cells) if q not in north]
        routes.append({'id':ident,'desired_width':width,'waypoints_xz':points,'all_desired_shoulder_columns':[list(q) for q in sorted(cells)],
            'non_north_or_water_or_unknown_shoulders':bad,'status':'NOT WALK ADMISSION; preserve/report every failing shoulder, contour-refine after modeled mass/stock review',
            'terrain_or_source_writes':0})
    result={'format':'awft-western-r2-authored-master-massing:1','source_sha256':digest(Path(__file__)),
        'historical_locator':{'relative':GEOGRAPHY[0],'sha256':GEOGRAPHY[1],'checkpoint_id':data['checkpoint_id'],'checkpoint_sha256':data['checkpoint_sha256']},
        'latest_parent_canonical_checkpoint':{'id':current.get('id'),'sha256':current.get('sha256'),'is_not_automatic_authority_for_older_locator':True},
        'entire_north_component_columns':len(north),'first_native_W3_main_outlines':{k:[list(q) for q in sorted(v)] for k,v in fixed.items() if k!='Grand hall'},
        'reserved_separate_hall':HALL,'fourteen_individually_authored_future_masses':plots,'crooked_lane_intentions':routes,
        'placed_zipline_reservation_sha256':ZIP[1],'future_main_coarse_height_envelopes_avoid_all_zipline_positions':True,
        'masterplan_contract':['ONE continuous pirate village over the whole north dry land to the shore','Normal frontage gaps0..3m;2..3m busy crooked lanes and small purposeful courts','Muted original small pirate section palette and fully articulated3D faces/interiors','No periodic bright roof stripes; real roof offsets, hips, dormers, levels and low annexes','Current stock anchors retained inside redesigned rooms or moved only by reviewed real custody','All native zipline body/frames/stations and accepted old town/river/bridge navigation preserved'],
        'completion':'INCOMPLETE; these14masses plus W3/hall do not yet fill all11,571columns. Existing15west houses need inventory-safe redesigned envelopes, western tips/east-neck gaps need further individual design. No count quota proves coverage.',
        'status':'LAYOUT SOURCE ONLY; no added modeled houses or route construction permitted before the real W3 photo-refinement gate','native_actions':0,'world_writes':0,'inventory_transfers':0,'reserve_guard':reserve}
    raw=(json.dumps(result,separators=(',',':'))+'\n').encode()
    if len(raw)>16*MIB:raise UserError('Finite masterlayout output exceeded')
    out=home/'staging'/('west-r2-master-massing-'+str(time.time_ns()));out.mkdir();(out/'layout-ONLY.json').open('xb').write(raw)
    return {'folder':str(out),'sha256':digest(out/'layout-ONLY.json'),'future_masses':len(plots),'unqualified_lane_shoulders':{r['id']:len(r['non_north_or_water_or_unknown_shoulders']) for r in routes},'not_a_native_plan':True}


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--home',type=Path,required=True);args=a.parse_args();print(json.dumps(prepare(args.home),indent=2))
