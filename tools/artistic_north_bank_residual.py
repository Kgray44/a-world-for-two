"""Bounded saved-land residual study, never proof the whole village is finished."""
from __future__ import annotations
import argparse,hashlib,json,time
from collections import deque,Counter
from pathlib import Path
from control_room.common import UserError,digest,read_json
from tools.artistic_north_bank_east import NorthTerrain,preservation,AIR,SOFT,NORTH_SOFT,GROUND,MIB,BRIDGE
from tools.artistic_bridge_refinement import flatten
from tools.artistic_north_bank_east_infills import COMPASS,COMPASS_SHA,ROSE_REL,ROSE_SHA
from tools.artistic_north_bank_west import ZIPLINE_MASK,ZIPLINE_MASK_SHA
from tools.playtest import guard

EAST22=('staging/north-bank-eastern22-1793157301590833400/prototype.json','956b58ce5a68a008fb7e3e099962c3f51712af604072a77fd2f81d6b7668375c')
WEST=('staging/north-bank-west-five-final-20261028T0200Z/future-solid-AIR-route-reservation-ONLY.json','c5236daf51002d6297f72e56c3b49561f0ccb2b91de301b2c5a02d9d443be17a')
STREET=('staging/west-street-stock-SNBT-fixed-20261028T0317Z/future-walk-furniture-reservation-ONLY.json','59e708726681c29ef962f632f3572369ec1db0299d58e11b454b6259b09be905')
LATER_WEST=(
 ('staging/north-bank-western-ten-1793158436435294000/prototype.json','e8c8b3c74175d49c0d512abfcdac0d7e84a7d39f31ee92e8ad352755f2f7e2ef'),
 ('staging/north-bank-western-connections-r2-1793159711602697500/connections.json','b658552ec91b6cd681a3e847dfe9613f51fcf59ca584642a3b184ba7c4e2956a'),
 ('staging/north-bank-quay-courts-1793159316245611100/prototype.json','6fdbe38c3e4ebb8d2a2f16f9ecdecf59cb977fe7f6d645756ff7f0e47dd97fe0'),
)
BOUNDS=(984,-1320,1392,-1120)


def prepare(home,checkpoint_id,checkpoint_sha):
    home=Path(home).resolve();reserve=guard(MIB,16*MIB)
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve():raise UserError('Owned private study only')
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    if receipt.get('verified') is not True or receipt.get('id')!=checkpoint_id or receipt.get('sha256')!=checkpoint_sha:raise UserError('Exact current stopped study checkpoint required')
    registry=read_json(home/'dashboard/settlement/registry.json');protected,existing=preservation(home,registry);protected=set(protected);sources=[]
    for relative,expected in ((ROSE_REL,ROSE_SHA),(COMPASS,COMPASS_SHA),EAST22,WEST,STREET,*LATER_WEST):
        path=home/relative
        if not 0<path.stat().st_size<=4*MIB or digest(path)!=expected:raise UserError('Exact existing/frozen future town source required')
        cells=flatten(read_json(path));columns={(x,z) for x,y,z in cells}
        protected.update((x+dx,z+dz) for x,z in columns for dx in (-1,0,1) for dz in (-1,0,1))
        sources.append({'path':relative,'sha256':expected,'role':'All addressed authored/future solids, AIR, lanes and model skirt — not a native placement claim'})
    cable_path=home/ZIPLINE_MASK
    if digest(cable_path)!=ZIPLINE_MASK_SHA:raise UserError('Exact future cable body required')
    cable=set(flatten(read_json(cable_path)));by_column={}
    for x,y,z in cable:by_column.setdefault((x,z),[]).append(y)
    terrain=NorthTerrain(home,receipt,registry);land={};x0,z0,x1,z1=BOUNDS
    try:
        for cx in range(x0//16,x1//16+1):
            for cz in range(z0//16,z1//16+1):
                for x in range(max(x0,cx*16),min(x1,cx*16+15)+1):
                    for z in range(max(z0,cz*16),min(z1,cz*16+15)+1):
                        land[x,z]=terrain.column(x,z)
                terrain.check()
        # A study rectangle also includes some SOUTH-shore forest. Do not
        # count it as spare village land. Remove the bridge's authored crossing
        # (including its AIR hull) from the land graph, then flood only from
        # actual northern town/quay anchor columns. Source roofs may connect
        # urban columns but may not turn the cross-river bridge into land.
        bridge_path=home/BRIDGE[0]
        if digest(bridge_path)!=BRIDGE[1]:raise UserError('Exact cross-river barrier source required')
        crossing={(x,z) for x,y,z in flatten(read_json(bridge_path))}
        connected=set();queue=deque()
        for anchor in ((1032,-1257),(1100,-1252),(1136,-1220),(1292,-1240),(1326,-1233)):
            if anchor not in land or land[anchor]['kind'] not in ('dry','retained_object'):raise UserError('Actual northern anchor is not saved land')
            queue.append(anchor);connected.add(anchor)
        while queue:
            x,z=queue.popleft()
            for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)):
                q=x+dx,z+dz
                if q not in connected and q not in crossing and q in land and land[q]['kind'] in ('dry','retained_object'):
                    connected.add(q);queue.append(q)
        south_anchor=(1032,-1128);south={south_anchor};queue=deque([south_anchor])
        if land.get(south_anchor,{}).get('kind') not in ('dry','retained_object'):raise UserError('Actual known SOUTH anchor is not saved land')
        while queue:
            x,z=queue.popleft()
            for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)):
                q=x+dx,z+dz
                if q not in south and q not in crossing and q in land and land[q]['kind'] in ('dry','retained_object'):
                    south.add(q);queue.append(q)
        if south&connected:raise UserError('North/south anchor flood merged; do not issue a bank mask')
        dry={q for q,r in land.items() if q in connected and r['kind']=='dry' and q not in protected and not any(r['surface_y']<=y<=r['surface_y']+24 for y in by_column.get(q,()))}
        centres=[]
        for x,z in sorted(dry):
            square={(x+a,z+b) for a in range(-4,5) for b in range(-4,5)}
            if not square.issubset(dry):continue
            heights=[land[q]['surface_y'] for q in square]
            if max(heights)-min(heights)<=2:centres.append((x,z))
        long_centres=[]
        for x,z in centres:
            cells={(x+a,z+b) for a in range(-4,5) for b in range(-5,6)}
            if cells.issubset(dry) and max(land[q]['surface_y'] for q in cells)-min(land[q]['surface_y'] for q in cells)<=2:long_centres.append((x,z))
        # Show the residual components rather than simply asserting37 houses
        # fill a broad circled polygon. Morphological nine-wide windows include
        # a seven-wide main field plus the one-metre architectural edge skirt.
        remaining=set(centres);patches=[]
        while remaining:
            root=min(remaining);remaining.remove(root);todo=deque([root]);part=[]
            while todo:
                p=todo.popleft();part.append(p)
                for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)):
                    q=p[0]+dx,p[1]+dz
                    if q in remaining:remaining.remove(q);todo.append(q)
            patches.append(part)
        patches.sort(key=len,reverse=True);representatives=[]
        for part in patches:
            representative=part[len(part)//2];x,z=representative;floor=max(land[x+a,z+b]['surface_y'] for a in range(-4,5) for b in range(-4,5))+1
            failures=[];checked=0
            for a in range(-4,5):
                for b in range(-4,5):
                    for y in range(floor,floor+20):
                        q=x+a,y,z+b;actual=terrain.state(*q);checked+=1
                        if actual is None or q in terrain.entities or q in cable or actual.split('[',1)[0] not in AIR|SOFT|NORTH_SOFT or 'waterlogged=true' in actual:
                            if len(failures)<5:failures.append({'position':list(q),'state':actual})
            representatives.append({'candidate_center_xz':list(representative),'candidate_center_component':len(part),
                'center_bounds_xz':[min(q[0] for q in part),min(q[1] for q in part),max(q[0] for q in part),max(q[1] for q in part)],
                'floor_y':floor,'complete_representative_body_cells':checked,'body_status':'SAVED FULL clear field only' if not failures else 'REFUSED representative body; other shapes/sites not inferred',
                'refusals':failures,'placement_or_art_authority':False})
            terrain.check()
        saved=terrain.snapshot.sources
    finally:terrain.close()
    document={'format':'awft-north-bank-residual-study:1','checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,
        'study_bounds_xz':list(BOUNDS),'samples':len(land),'counts':dict(Counter(r['kind'] for r in land.values())),
        'actual_northern_land_component_columns':len(connected),'cross_river_bridge_barrier_sha256':BRIDGE[1],
        'modeled_eastern_buildings':37,'modeled_western_shops':5,'claims_entire_blue_area_filled':False,
        'dry_unreserved_columns':len(dry),'nine_wide_centres':len(centres),'candidate_patches':representatives,
        'seven_by_nine_main_plus_model_skirt_centres_xz':[list(q) for q in long_centres],
        'profile_limit':'9x11 saved dry surface/relief only. Every complete native body/tree/BE/preimage and actual original architecture still must be individually qualified.',
        'actual_water_and_unknown_excluded':True,'existing_source_custody':existing,'new_source_custody':sources,
        'prospective_cable_sha256':ZIPLINE_MASK_SHA,'saved_sources':saved,'reserve_guard':reserve,
        'limitations':['The study rectangle is not a georeferenced screenshot permission polygon','Representative clear fields do not authorize a whole component or any house','Narrow residual strips/courtyards below seven metres still need public-lane/planting and eye-level review','Frozen22 source is not called native placed; west10 candidate fields are not modeled houses here'],
        'source_sha256':digest(Path(__file__)),'world_actions':0}
    queries={}
    for name,q in (('pink-magnolia',(1016,-1176)),('known-south',(1032,-1128)),('known-north',(1032,-1257)),('pine-outside-study',(1024,-904))):
        queries[name]={'position_xz':list(q),'classification':'NORTH_CONNECTED' if q in connected else 'SOUTH_CONNECTED' if q in south else 'OUTSIDE_NORTHERN_STUDY' if q not in land else 'UNCONNECTED_UNKNOWN_BANK',
            'actual_saved_column_kind':land.get(q,{}).get('kind'),'not_north_is_not_an_automatic_south_growth_authority':True}
    mask={'format':'awft-north-connected-preservation-mask:1','seed':registry['seed'],'world_path':registry['world_path'],
        'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'source_sha256':digest(Path(__file__)),
        'study_bounds_xz':list(BOUNDS),'bridge_barrier':{'path':BRIDGE[0],'sha256':BRIDGE[1]},
        'connected_columns_xz':[list(q) for q in sorted(connected)],'connected_columns':len(connected),'queries':queries,
        'independent_south_anchor_xz':list(south_anchor),'north_south_components_disjoint':True,
        'native_plan':False,'observed_AIR_claim':False,'growth_or_placement_authority':False,
        'purpose':'Exclude every exact saved northern land column from SOUTH forest roots and complete feature WRITE/crown footprints. Unknown/outside columns remain unknown; do not substitute a rectangular keepout or infer SOUTH from absence.',
        'extra_skirt_metres_in_file':0,'required_tree_guard':'Apply complete native growth/crown plus required5m distance against this exact mask; no native tree guard relaxation'}
    mask_raw=(json.dumps(mask,separators=(',',':'))+'\n').encode()
    document['north_connected_column_mask']={'file':'north-connected-columns-ONLY.json','bytes':len(mask_raw),'sha256':hashlib.sha256(mask_raw).hexdigest()}
    raw=(json.dumps(document,indent=2)+'\n').encode()
    if len(raw)>16*MIB:raise UserError('Finite residual study output exceeded')
    out=home/'staging'/('north-bank-residual-'+str(time.time_ns()));out.mkdir();(out/'residual-study.json').open('xb').write(raw);(out/'north-connected-columns-ONLY.json').open('xb').write(mask_raw)
    return {'folder':str(out),'sha256':hashlib.sha256(raw).hexdigest(),'north_mask':document['north_connected_column_mask'],'queries':queries,'samples':len(land),'dry_unreserved_columns':len(dry),'nine_wide_centres':len(centres),'candidate_patches':representatives,'world_actions':0}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--home',type=Path,required=True);parser.add_argument('--checkpoint-id',required=True);parser.add_argument('--checkpoint-sha',required=True);a=parser.parse_args()
    print(json.dumps(prepare(a.home,a.checkpoint_id,a.checkpoint_sha),indent=2))
