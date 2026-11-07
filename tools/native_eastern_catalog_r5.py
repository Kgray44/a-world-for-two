"""Additive98-room catalogue: unchanged legacy identities plus reviewed reallocations.

Reads one authenticated stopped region. Never installs a catalogue or request.
"""
from __future__ import annotations
import argparse,copy,hashlib,json,time
from collections import defaultdict
from pathlib import Path
import nbtlib
from control_room.common import UserError,digest,read_json
from tools.artistic_captains_hall import native_payload
from tools.artistic_east_tortuga_retrofit import checked,with_exact_be_tags
from tools.artistic_eastern_move_blueprint import cells
from tools.artistic_eastern_urban_custody import canonical
from tools.artistic_maritime_depth import admit_owner
from tools.artistic_north_rebuild_custody import decoded_chunk
from tools.artistic_zipline_catenary import reader_budget
from tools.native_eastern_relocation import SEALED_CATALOG_SHA,LAYOUT,SOFT
from tools.native_eastern_relocation_current import CATALOG,cover_history
from tools.native_relocation_request import reference
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld,unpack_section

MIB=1024**2
ALLOCATION=('staging/eastern-self-overlap23-disjoint-DAG-1793219467452176700/allocation-SOURCE-ONLY.json','517c1dab4c9d467fe8d072d86b5fb759aab51d493b6c6b229cde43849457bf18')

def prepare(home):
    home=Path(home).resolve();reserve=guard(2*MIB,16*MIB);budget=[reader_budget()];started=time.monotonic()
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json');registry=read_json(home/'dashboard/settlement/registry.json')
    admit_owner(home,read_json(home/'dashboard/artistic-owner.json'),receipt,receipt['id'],receipt['sha256'])
    base=checked(home/CATALOG,SEALED_CATALOG_SHA,2*MIB);alloc=checked(home/ALLOCATION[0],ALLOCATION[1],2*MIB);old={r['id']:r for r in base['capsules']};rows=alloc['room_allocations']
    if len(rows)!=98:raise UserError('Exact98 allocations required')
    for r in rows:
        a,b=r['source_bounds_xyz'],r['destination_bounds_xyz']
        if all(a[k]<=b[k+3] and b[k]<=a[k+3] for k in range(3)):raise UserError('Own source/destination must be genuinely disjoint')
    wanted=set();prepared={}
    for r in rows:
        a,b=r['source_bounds_xyz'],r['destination_bounds_xyz'];sp,dp=cells(a),cells(b);supports={(x,b[1]-1,z) for x in range(b[0],b[3]+1) for z in range(b[2],b[5]+1)}
        wanted|=sp|dp|supports;prepared[r['id']]=(sp,dp,supports)
    if len(wanted)>100000:raise UserError('Finite shared catalogue field')
    grouped=defaultdict(list)
    for q in wanted:grouped[q[0]//16,q[2]//16].append(q)
    saved={};bes={};snapshot=None
    try:
        snapshot=BackupWorld(home,receipt,registry);name=snapshot.prefix+'r.2.-3.mca';meta=snapshot.files[name]
        if not 8192<=meta['size']<=48*MIB:raise UserError('One finite exact saved region')
        raw=snapshot.archive.read(name)
        if hashlib.sha256(raw).hexdigest()!=meta['sha256']:raise UserError('Archived region digest differs')
        for (cx,cz),positions in sorted(grouped.items()):
            doc=decoded_chunk(raw,cx,cz);sections={int(s['Y']):s for s in doc.get('sections',[])}
            for q in positions:saved[q]=unpack_section(sections.get(q[1]//16,{}),*q)
            for tag in doc.get('block_entities',[]):
                q=tuple(int(tag[k]) for k in ('x','y','z'))
                if q in wanted:bes[q]=tag
            budget.append(reader_budget())
            if time.monotonic()-started>120:raise UserError('Catalogue source read exceeded finite120seconds')
        region={'name':name.rsplit('/',1)[-1],'sha256':meta['sha256'],'bytes':len(raw)}
    finally:
        if snapshot:snapshot.close()
    cover_history(home)
    out=home/'staging'/('eastern-catalog-r5-'+str(time.time_ns()));out.mkdir();written=0;result=[]
    def write(name,field,tags):
        nonlocal written
        raw=with_exact_be_tags(native_payload(registry,field,receipt['sha256'],'Current original R5 custody only; native operation not authorized'),tags);written+=len(raw)
        if written>12*MIB:raise UserError('Finite catalogue output exceeded')
        p=out/name;p.write_bytes(raw);return reference(home,p)
    for index,r in enumerate(rows):
        ident=r['id'];prior=old.get(ident);a,b=r['source_bounds_xyz'],r['destination_bounds_xyz'];sp,dp,support=prepared[ident];tags={q:bes[q] for q in sp if q in bes}
        if set(tags)!={tuple(q) for q in r['expected_source_BE_positions']}:raise UserError('Fresh complete source BE closure differs: '+ident)
        if prior:
            row=copy.deepcopy(prior);original=checked(home/prior['source_original']['path'],prior['source_original']['sha256'],MIB)
            expected={tuple(q['pos']):nbtlib.parse_nbt(q['nbt']) for q in original['block_entities']}
            if expected!=tags:raise UserError('Actual current full typed source stock changed: '+ident)
            from tools.artistic_bridge_refinement import flatten
            field=flatten(original);preps={tuple(q['position']) for q in prior['source_cover_preparations']}
            if any(saved[q]!=s and not(q in preps and saved[q]=='minecraft:air') for q,s in field.items()):raise UserError('Full original source changed outside actual reviewed cover: '+ident)
            changed=b!=prior['destination_bounds_xyz']
        else:
            row={'id':ident,'source_original':write(f'{index:03d}-source-original.json',{q:saved[q] for q in sp},tags),
                'cells':len(sp),'objects':len(tags),'source_cover_preparations':[{'position':list(q),'before':saved[q]} for q in sorted(sp) if saved[q].split('[',1)[0] in SOFT and q not in bes],
                'supported':True,'holds':[]};changed=True
        if changed:
            row['prior_translation_xyz']=prior['translation_xyz'] if prior else [0,0,0]
            row['destination_original']=write(f'{index:03d}-destination-original.json',{q:saved[q] for q in dp},{q:bes[q] for q in dp if q in bes})
            row['supports_original']=write(f'{index:03d}-supports-original.json',{q:saved[q] for q in support},{q:bes[q] for q in support if q in bes})
            row['destination_cover_preparations']=[]
        row.update(source_bounds_xyz=a,destination_bounds_xyz=b,translation_xyz=r['translation_xyz'],support_cells=len(support),dependencies=r['required_preceding_native_capture_ids'],destination_building=r['destination_building'],destination_mass=r['destination_mass'])
        if ident=='compass-bend/shared-repair-court:room:0':
            if prior['holds']!=['Unreviewed native inventory role, including linked Create toolbox; no assumed empty storage']:raise UserError('Toolbox has additional unexplained original holds')
            row.update(supported=True,holds=[],requires_toolbox_native_handler_and_saved_profile_custody=True)
        result.append(row)
    record={'format':'awft-approved-eastern-relocation-catalog:5','eastern_layout_sha256':LAYOUT[1],'inherited_original_catalog_sha256':SEALED_CATALOG_SHA,
        'allocation_addendum_sha256':ALLOCATION[1],'baseline_capture_backup_sha256':base['baseline_capture_backup_sha256'],'catalog_capture_checkpoint_id':receipt['id'],
        'catalog_capture_checkpoint_sha256':receipt['sha256'],'capsules':result,'native_move_order':alloc['native_move_order'],'native_actions':0}
    p=out/'approved98-capsules-PRIVATE.json';p.write_bytes(canonical(record)+b'\n')
    manifest={'format':'awft-additive-eastern-catalogue-bundle:5','catalog':reference(home,p),'capsules':98,'inherited_unchanged_IDs':93,'new_genuine_allocations':5,
        'reallocated_existing_destinations':sorted(r['id'] for r in rows if r['id'] in old and r['destination_bounds_xyz']!=old[r['id']]['destination_bounds_xyz']),'original_catalog_untouched':True,'saved_region':region,
        'native_toolbox_custody_and_all_current_guards_required':True,'source_sha256':digest(Path(__file__)),'reader_peak_RSS':max(v['owned_reader_rss_bytes'] for v in budget),'reserve_guard':reserve,'native_actions':0}
    mp=out/'manifest.json';mp.write_bytes(canonical(manifest)+b'\n');return {'folder':str(out),'catalog_sha256':digest(p),'manifest_sha256':digest(mp),'capsules':98,'native_actions':0}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.home),indent=2))
