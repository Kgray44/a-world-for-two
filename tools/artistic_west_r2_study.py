"""Measured western rebuild brief; no demolition, inventory move or world call.

The rejected extension remains evidence. Existing BE anchors are preserved as
unknown contents until fresh native custody, rather than assumed empty.
"""
from __future__ import annotations
import argparse,hashlib,json,time
from collections import Counter,deque
from pathlib import Path

from control_room.common import UserError,digest,read_json
from tools.artistic_north_bank_east import NorthTerrain,BRIDGE
from tools.artistic_bridge_refinement import flatten
from tools.artistic_zipline_catenary import reader_budget
from tools.artistic_street import designs
from tools.playtest import guard

MIB=1024**2
BOUNDS=(944,-1352,1216,-1120)
HERITAGE=(
 ('Signal Lane','staging/neighborhood-canonical-ridges-20261027T1852Z/signal-canonical-full-VERIFY-ONLY.json','89df5767701762039fc37e8803509ea5e3862512a35a64f52e9add8cf8f57139'),
 ('Drowned Rose','staging/artistic-pirate-spit-byte-slots-1793124362042040500/drowned-rose-VERIFY-ONLY.json','f646d9ed046f603dc4e55c3f564949dba3a45be733dbd8c88ebba9cf48d85486'),
 ('Ninth Knot','staging/artistic-pirate-spit-byte-slots-1793124362042040500/ninth-knot.json','731cd08a444a8b8360484856703558de39d7fd58f9ad4e7d99f7383b19adf834'),
 ('Pilot tip','staging/artistic-pirate-spit-byte-slots-1793124362042040500/pilot-tip.json','c7fe7bd83a8738fbb4895b29a87f5f4a38ec50cd9527a14e4991edbafda8206b'),
)
REJECTED=(
 ('west-five','staging/north-bank-west-five-final-20261028T0200Z/future-solid-AIR-route-reservation-ONLY.json','c5236daf51002d6297f72e56c3b49561f0ccb2b91de301b2c5a02d9d443be17a'),
 ('western-ten','staging/north-bank-western-ten-1793158436435294000/prototype.json','e8c8b3c74175d49c0d512abfcdac0d7e84a7d39f31ee92e8ad352755f2f7e2ef'),
)
ZIP=('staging/zipline-west-v2-source-1793152099836099800/all-v2-RESERVATION-ONLY.json','92ea594836795a61e00f5cc32290d49d1d47b9fd6eb55aeefc99d527acf8854d')


def flood(land,anchors,barrier):
    seen=set(anchors);todo=deque(anchors)
    if any(p not in land or land[p]['kind'] not in ('dry','retained_object') for p in seen):raise UserError('Saved bank anchor is unavailable')
    while todo:
        x,z=todo.popleft()
        for p in ((x-1,z),(x+1,z),(x,z-1),(x,z+1)):
            if p not in seen and p not in barrier and p in land and land[p]['kind'] in ('dry','retained_object'):seen.add(p);todo.append(p)
    return seen


def prepare(home,checkpoint_id,checkpoint_sha):
    home=Path(home).resolve();reserve=guard(2*MIB,16*MIB);budgets=[reader_budget()]
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve():raise UserError('Private western rebuild study only')
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    if receipt.get('verified') is not True or (receipt.get('id'),receipt.get('sha256'))!=(checkpoint_id,checkpoint_sha) or 'stopped' not in receipt.get('scope','').lower():raise UserError('Exact current verified stopped study required')
    registry=read_json(home/'dashboard/settlement/registry.json');heritage=[];owners={};custody=[]
    for label,rel,sha in (*HERITAGE,*REJECTED):
        p=home/rel
        if digest(p)!=sha:raise UserError('Frozen accepted/rejected source changed')
        cells=flatten(read_json(p));counts=Counter(s.split('[',1)[0] for s in cells.values() if s!='minecraft:air')
        if (label,rel,sha) in HERITAGE:heritage.append({'name':label,'source_sha256':sha,'source_bounds_xyz':[min(q[a] for q in cells) for a in range(3)]+[max(q[a] for q in cells) for a in range(3)],'solid_count':sum(counts.values()),'top_materials':counts.most_common(24),'roof_shape_materials':{k:v for k,v in counts.items() if 'roof' in k or 'stairs' in k}})
        else:
            for p in cells:owners.setdefault(p,[]).append(label)
        custody.append({'label':label,'path':rel,'sha256':sha,'rebuild_ownership_is_not_demolition_authority':True})
    if digest(home/ZIP[0])!=ZIP[1] or digest(home/BRIDGE[0])!=BRIDGE[1]:raise UserError('Retained endpoint/navigation masks changed')
    zip_cells=set(flatten(read_json(home/ZIP[0])));barrier={(x,z) for x,y,z in flatten(read_json(home/BRIDGE[0]))}
    mass=[]
    for b in designs():
        f=b.levels[0];mass.append({'name':b.name,'width':max(x for x,z in f)-min(x for x,z in f)+1,'depth':max(z for x,z in f)-min(z for x,z in f)+1,'main_area':len(f),'levels':len(b.levels),'front':b.front,'actual_outline_vertices_are_authored':True,'roof_sections':len(b.roofs)})
    terrain=NorthTerrain(home,receipt,registry);land={};started=time.monotonic();x0,z0,x1,z1=BOUNDS
    try:
        for cx in range(x0//16,x1//16+1):
            for cz in range(z0//16,z1//16+1):
                for x in range(max(x0,cx*16),min(x1,cx*16+15)+1):
                    for z in range(max(z0,cz*16),min(z1,cz*16+15)+1):land[x,z]=terrain.column(x,z)
                if time.monotonic()-started>120:raise UserError('Finite western geography study exceeded120s')
            budgets.append(reader_budget())
        north=flood(land,[(1032,-1257),(1100,-1252),(1136,-1220)],barrier)
        south=flood(land,[(1032,-1128)],barrier)
        if north&south:raise UserError('Main navigation bank split merged; no masterland authority')
        # Actual BE anchors belong to existing people, storage and renderer
        # models. Contents are deliberately UNKNOWN, never presumed empty.
        anchors=[{'position':list(p),'actual_block':terrain.state(*p),'rejected_source_owners':owners[p],
                  'contents':'UNKNOWN/PRESERVE_IN_PLACE; fresh native full inventory/component custody required before any rebuild',
                  'authorized_move_or_delete':False} for p in sorted(terrain.entities) if p in owners]
        sites=[]
        for origin in ((1071,64,-1274),(1072,64,-1273)):
            ox,oy,oz=origin;sample={}
            for x in range(ox-2,ox+18):
                for z in range(oz-1,oz+25):sample[x,z]=land.get((x,z),{'kind':'unknown'})
            sites.append({'candidate_origin':list(origin),'plot_field_counts':dict(Counter(v['kind'] for v in sample.values())),
                'all_main_footprints_pending_exact_prototype_shape':True,'native_placement_or_demolition_authority':False})
        actual_bounds=[min(p[0] for p in north),min(p[1] for p in north),max(p[0] for p in north),max(p[1] for p in north)]
        report={'format':'awft-western-rebuild-r2-measured-study:1','checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,
            'source_sha256':digest(Path(__file__)),'study_bounds_xz':list(BOUNDS),'counts':dict(Counter(v['kind'] for v in land.values())),
            'north_component_columns':len(north),'actual_north_component_bounds_xz':actual_bounds,'independent_south_disjoint':True,
            'accepted_original_palette_measurements':heritage,'accepted_original_10_mass_measurements':mass,'source_custody':custody,
            'rejected_existing_BE_anchors':anchors,'BE_contents_read_or_moved':False,'temporary_candidate_sites':sites,
            'zipline_reserved_3D_cells':len(zip_cells),'zipline_reservation_sha256':ZIP[1],
            'design_contract':{'one_continuous_village':True,'normal_front_offsets_metres':[1,3],'normal_between_building_gaps_metres':[0,3],'main_walk_clear_width_metres':[2,3],
                'no_grid_lawns':True,'no_periodic_bright_roof_bands':True,'roof_run_breaks':'Actual cross-gables/annex offsets/dormers/chimneys in muted matching shape/material families',
                'keep_all_original_accepted_sections':True,'native_first_three_building_visual_gate_before_replication':True},
            'source_only':True,'native_actions':0,'world_writes':0,'inventory_or_human_progress_changes':0,'raw_saved_regions':terrain.snapshot.sources,
            'reader_peak_observed_RSS_bytes':max(b['owned_reader_rss_bytes'] for b in budgets),'reserve_guard':reserve,
            'limits':['Bank membership through retained roofs/decks is not dry-main-footprint authority','Retained-object columns need original natural-dry provenance or independently reviewed existing build support','Missing/nonFULL cells remain unknown','BE contents/ownership are unknown and must be preserved in place until real custody','No current demolition or image/native acceptance is implied']}
        columns_doc={'format':'awft-west-r2-geographic-source:1','checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,
            'columns':[{'xz':list(p),'kind':land[p]['kind'],'surface_y':land[p].get('surface_y'),'surface_state':land[p].get('state'),'north_connected':p in north} for p in sorted(land)],
            'not_a_native_plan':True,'not_a_plot_or_demolition_authority':True}
    finally:terrain.close()
    raw={'study.json':(json.dumps(report,separators=(',',':'))+'\n').encode(),'geography-ONLY.json':(json.dumps(columns_doc,separators=(',',':'))+'\n').encode()}
    if sum(map(len,raw.values()))>16*MIB:raise UserError('Finite western rebuild study output exceeded')
    out=home/'staging'/('west-r2-measured-study-'+str(time.time_ns()));out.mkdir()
    for n,b in raw.items():(out/n).open('xb').write(b)
    return {'folder':str(out),'study_sha256':digest(out/'study.json'),'geography_sha256':digest(out/'geography-ONLY.json'),'northern_columns':len(north),'actual_northern_bounds':actual_bounds,'BE_anchors':len(anchors),'native_actions':0}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);p.add_argument('--checkpoint-id',required=True);p.add_argument('--checkpoint-sha',required=True);a=p.parse_args();print(json.dumps(prepare(a.home,a.checkpoint_id,a.checkpoint_sha),indent=2))
