"""Current eastern-room custody for a source-only Tortuga urban re-layout.

Only reads the explicitly owned stopped backup. Lossless typed inventories stay
in private D: output. No entity, item, block or template is placed or removed.
Native instance/slot/component inspection remains an independent execution gate.
"""
from __future__ import annotations

import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import time

from control_room.common import UserError,digest,read_json
from tools.artistic_bridge_refinement import flatten
from tools.artistic_east_tortuga_retrofit import LEDGER,LEDGER_SHA,checked
from tools.artistic_maritime_depth import admit_owner
from tools.artistic_north_rebuild_custody import BATCHES,decoded_chunk,typed,inventory_facts
from tools.artistic_zipline_catenary import reader_budget
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld,unpack_section

MIB=1024**2
CHECKPOINT='20261028T161905Z-06e1e7'
CHECKPOINT_SHA='b0315f548e55a389bb01a3caeb4c5a8532abb3e6599f6a0a77785c6c4916dece'
BOUNDS=(1217,-1296,1392,-1120)
MAX_OUTPUT=64*MIB
MAX_SECONDS=150
OVERLAYS=(
 ('seabird','staging/seabird-tortuga-retrofit-1793196434552931800/seabird-shell-PROPOSAL.json','f2122e0cc6e29948867ad53039d9d2820a1d63e5f120b63ea2aba6a82e1a42f0',321),
 ('density','staging/eastern-tortuga-density-1793200403515761500/cluster-density-PROPOSAL.json','8a647689c571e48de0e666f279e3903220c84f962b0df4c400865bc9f7dd1c8b',1808),
)
PRIVATE_ANCHORS={(1296,65,-1250),(1296,65,-1249),(1300,65,-1255)}
VOID={'minecraft:air','minecraft:cave_air','minecraft:void_air'}


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def in_study(q):return BOUNDS[0]<=q[0]<=BOUNDS[2] and BOUNDS[1]<=q[2]<=BOUNDS[3]


def apply_authored_delta(expected,delta,exact_count):
    if len(delta)!=exact_count:raise UserError('Only exact actually authored DELTA targets confer source ownership; read-only full context is excluded')
    expected.update(delta)


def classify_current(expected,actual,is_be,private=False):
    if private:return 'PRIVATE_HUMAN_ANCHOR_RETAIN_IN_PLACE'
    if is_be:return 'CURRENT_NATIVE_BE_REQUIRES_LOSSLESS_CUSTODY'
    if expected is None:return 'UNOWNED_CURRENT_STATE_HOLD'
    if expected==actual:return 'EXACT_OWNED_AIR' if actual.split('[',1)[0] in VOID else 'EXACT_OWNED_NON_BE_SOURCE'
    return 'CURRENT_SOURCE_DIFFERENCE_HOLD_NATIVE_OR_HUMAN_ORIGIN_UNPROVEN'


def before_sources(home):
    legacy=checked(home/LEDGER/'manifest.json',LEDGER_SHA,2*MIB)
    houses=[dict(r) for r in legacy['houses'] if r['batch'] in ('rose-reach','compass-bend','eastern22')]
    if len(houses)!=37:raise UserError('Exact original eastern37 association is required')
    expected={};original={};refs=[];outside={}
    for batch,rel,name,sha,prior,prior_sha,count in BATCHES[:3]:
        doc=checked(home/rel/name,sha,4*MIB);old=checked(home/rel/prior,prior_sha,4*MIB)
        provenance=next(r for r in legacy['frozen_rejected_source_custody'] if r['batch']==batch)
        author=checked(home/rel/'manifest.json',provenance['manifest_sha256'],2*MIB)
        for lot in author['buildings']:
            house=next(r for r in houses if r['id']==batch+'/'+lot['id'])
            if set(map(tuple,house['main_footprint']))!=set(map(tuple,lot['main_footprint'])):raise UserError('House association changed')
            house.update(front=lot['front'],door=lot['door'])
            dx,dz={'north':(0,-1),'south':(0,1),'east':(1,0),'west':(-1,0)}[lot['front']]
            q=(lot['door'][0]+dx,lot['floor_y']+3,lot['door'][2]+dz)
            if q in outside:raise UserError('Two original house signs claim one position')
            outside[q]=house['id']
        now=flatten(doc);was=flatten(old)
        if not set(now)<=set(was):raise UserError('Full original preimage must contain its whole source')
        for q,s in now.items():
            if q in expected and expected[q]!=s:raise UserError('Original source ownership is ambiguous')
            expected[q]=s;original[q]=s
        refs.append({'id':batch,'path':rel+'/'+name,'sha256':sha,'original_before_sha256':prior_sha})
    for label,rel,sha,count in OVERLAYS:
        doc=checked(home/rel,sha,2*MIB);apply_authored_delta(expected,flatten(doc),count)
        refs.append({'id':label,'path':rel,'sha256':sha,'authored_delta_cells':count,'full_VERIFY_ONLY_context_never_confers_authorship':True})
    # This is the exact newly native-placed infill room, not an old-grid proxy.
    houses.append({'id':'density/bent-needle','name':'The Bent Needle','batch':'native48-density',
        'main_footprint':[[x,z] for x in range(1255,1260) for z in range(-1212,-1204)],'floor_y':64,'storeys':2})
    # Exact original batch-common stock points, not guessed nearest houses.
    for ident,points in (
        ('compass-bend/shared-repair-court',((1272,64,-1206),(1275,64,-1206))),
        ('compass-bend/shared-produce-counter',((1286,64,-1206),(1286,64,-1205)))):
        houses.append({'id':ident,'name':ident,'batch':'compass-bend','main_footprint':[],
            'floor_y':63,'storeys':1})
        for q in points:
            if q not in expected or q in outside:raise UserError('Exact original shared fixture ownership is required')
            outside[q]=ident
    return houses,{q:s for q,s in expected.items() if in_study(q)},original,refs,outside


def associations(houses):
    cols=defaultdict(list)
    for row in houses:
        for p in row['main_footprint']:cols[tuple(p)].append(row['id'])
    return cols


def pods_from_current(rows,houses):
    """Keep complete actual BE records; ambiguous/added/private data never moves."""
    by_id={r['id']:r for r in houses};pods={};holds=[]
    for row in rows:
        owners=row['main_outline_associations'];q=row['position']
        if tuple(q) in PRIVATE_ANCHORS or row['classification']!='CURRENT_NATIVE_BE_REQUIRES_LOSSLESS_CUSTODY':
            holds.append({'position':q,'reason':row['classification']});continue
        if len(owners)!=1:
            holds.append({'position':q,'reason':'No unique exact room association; retain current instance and contents'});continue
        house=by_id[owners[0]]
        if not house['floor_y']<q[1]<house['floor_y']+4*house['storeys']:
            holds.append({'position':q,'reason':'Outside the explicit room-height interval; no guessed floor ownership'});continue
        level=(q[1]-house['floor_y']-1)//4;ident=house['id']+':room:'+str(level)
        pod=pods.setdefault(ident,{'id':ident,'source_house':house['id'],'source_floor_y':house['floor_y']+4*level,'records':[]})
        pod['records'].append({'source_position':q,'saved_block':row['saved_block'],'saved_BE_id':row['saved_BE_id'],
            'current_full_typed_NBT_sha256':row['actual_full_typed_NBT_sha256'],
            'current_native_class_all_slots_all_components':'PENDING independent native read-only instance inspection'})
    for pod in pods.values():
        pts=[r['source_position'] for r in pod['records']]
        # A conservative real support capsule. The executable controller must
        # still prove multi-block models/attachments fit this captured volume.
        pod['source_support_bounds_xyz']=[min(p[0] for p in pts)-1,pod['source_floor_y'],min(p[2] for p in pts)-1,
            max(p[0] for p in pts)+1,pod['source_floor_y']+3,max(p[2] for p in pts)+1]
        if any(not pod['source_support_bounds_xyz'][1]<=p[1]<=pod['source_support_bounds_xyz'][4] for p in pts):raise UserError('A BE escaped its actual four-block room capsule')
        pod['native_capture_scope']='Exact current source BE/support capsule; full model/dependency/unknown actor/entity/ownership review REQUIRED before native capture'
        pod['source_floor_and_furniture_are_not_demolition_authority']=True
    return list(pods.values()),holds


def prepare(home):
    home=Path(home).resolve();reserve=guard(4*MIB,MAX_OUTPUT);budgets=[reader_budget()];started=time.monotonic()
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve():raise UserError('Explicit separately owned artistic home only')
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json');owner=read_json(home/'dashboard/artistic-owner.json')
    admit_owner(home,owner,receipt,CHECKPOINT,CHECKPOINT_SHA)
    registry=read_json(home/'dashboard/settlement/registry.json')
    houses,expected,original,refs,outside=before_sources(home);cols=associations(houses)
    out=home/'staging'/('eastern-urban-current-custody-'+str(time.time_ns()));out.mkdir();total=0;rows=[];stats=Counter();source_chunks=defaultdict(list)
    for q in expected:source_chunks[q[0]//16,q[2]//16].append(q)
    snapshot=None;success=False;be_types=Counter();full_chunks=0
    def write(stream,row):
        nonlocal total
        data=canonical(row)+b'\n';total+=len(data)
        if total>MAX_OUTPUT:raise UserError('Finite private custody allocation reached; partials remain')
        stream.write(data)
    try:
        snapshot=BackupWorld(home,receipt,registry)
        name=snapshot.prefix+'r.2.-3.mca';entry=snapshot.files.get(name)
        if not entry or not 8192<=entry['size']<=48*MIB or snapshot.archive.getinfo(name).file_size!=entry['size']:raise UserError('Exact single finite eastern MCA member required')
        raw=snapshot.archive.read(name)
        if hashlib.sha256(raw).hexdigest()!=entry['sha256']:raise UserError('Stopped region member content changed')
        sources=snapshot.sources+[{'file':'r.2.-3.mca','sha256':entry['sha256'],'bytes':len(raw),'role':'Current06 FULL typed eastern custody only; never a live read'}]
        with (out/'current-cells-READONLY-PRIVATE.jsonl').open('xb') as cells,(out/'current-BEs-FULL-TYPED-PRIVATE.jsonl').open('xb') as bes:
            for cx in range(BOUNDS[0]//16,BOUNDS[2]//16+1):
                for cz in range(BOUNDS[1]//16,BOUNDS[3]//16+1):
                    doc=decoded_chunk(raw,cx,cz);full_chunks+=1
                    if int(doc.get('DataVersion',0))!=3955:raise UserError('Exact Minecraft1.21.1 saved DataVersion required')
                    sections={int(s['Y']):s for s in doc.get('sections',[])}
                    actual_bes={(int(v['x']),int(v['y']),int(v['z'])):v for v in doc.get('block_entities',[])}
                    def actual(q):
                        s=sections.get(q[1]//16)
                        return unpack_section(s,*q) if s is not None else 'minecraft:air'
                    for q in sorted(source_chunks.get((cx,cz),())):
                        now=actual(q);category=classify_current(expected[q],now,q in actual_bes,q in PRIVATE_ANCHORS);stats[category]+=1
                        write(cells,{'position':list(q),'current_saved':now,'expected_last_authored_source':expected[q],
                            'original_rejected_source':original.get(q),'classification':category,'BE_present':q in actual_bes,
                            'demolition_or_relocation_authorized':False})
                    for q,be in sorted(actual_bes.items()):
                        if not in_study(q):continue
                        data=typed(be);encoded=canonical(data)
                        if len(encoded)>2*MIB:raise UserError('Individual private typedBE exceeds2MiB')
                        now=actual(q);exp=expected.get(q);owners=list(cols.get((q[0],q[2]),[]))
                        if q in outside:
                            if owners and owners!=[outside[q]]:raise UserError('A declared outside fixture overlaps another room')
                            owners=[outside[q]]
                        if q in PRIVATE_ANCHORS:category='PRIVATE_HUMAN_ANCHOR_RETAIN_IN_PLACE'
                        elif not exp or exp.split('[',1)[0]!=now.split('[',1)[0]:category='UNOWNED_OR_CHANGED_BE_RETAIN_IN_PLACE'
                        else:category='CURRENT_NATIVE_BE_REQUIRES_LOSSLESS_CUSTODY'
                        row={'position':list(q),'saved_block':now,'saved_BE_id':str(be.get('id','UNKNOWN')),
                            'main_outline_associations':owners,'classification':category,'within_last_authored_source':exp is not None,
                            'actual_full_typed_NBT':data,'actual_full_typed_NBT_sha256':hashlib.sha256(encoded).hexdigest(),
                            'inventory_facts':inventory_facts(be),'action':'RETAIN until independent actual native instance/slot/all-component capture and reviewed lossless transaction'}
                        be_types[row['saved_BE_id']]+=1;write(bes,row);rows.append({k:v for k,v in row.items() if k not in ('actual_full_typed_NBT','inventory_facts')})
                    del doc,sections,actual_bes
                    budgets.append(reader_budget())
                    if time.monotonic()-started>MAX_SECONDS:raise UserError('Finite current custody150s read exceeded')
        pods,holds=pods_from_current(rows,houses)
        captured={};by_capture=defaultdict(list);all_be={tuple(r['position']):r for r in rows}
        for pod in pods:
            b=pod['source_support_bounds_xyz'];own={tuple(r['source_position']) for r in pod['records']}
            points={(x,y,z) for x in range(b[0],b[3]+1) for y in range(b[1],b[4]+1) for z in range(b[2],b[5]+1)}
            foreign=sorted(p for p in points if p in all_be and p not in own)
            if foreign and pod['source_house']!='rose-reach/compass':raise UserError('A movable capsule contains a foreign retained BE; explicit dependency review is required')
            pod['retained_foreign_BE_positions']=[list(p) for p in foreign]
            pod['capture_cells']=len(points)
            for p in points:
                if p in captured:
                    if p in all_be:raise UserError('A native BE would be captured twice; no duplication')
                    captured[p].append(pod['id'])
                else:
                    captured[p]=[pod['id']];by_capture[p[0]//16,p[2]//16].append(p)
        with (out/'capsule-source-cells-FULL-READONLY-PRIVATE.jsonl').open('xb') as stream:
            for (cx,cz),positions in sorted(by_capture.items()):
                doc=decoded_chunk(raw,cx,cz);sections={int(s['Y']):s for s in doc.get('sections',[])}
                for p in sorted(positions):
                    s=sections.get(p[1]//16);actual=unpack_section(s,*p) if s is not None else 'minecraft:air'
                    write(stream,{'position':list(p),'pod_ids':captured[p],'current_saved':actual,
                        'classification':classify_current(expected.get(p),actual,p in all_be,p in PRIVATE_ANCHORS),
                        'source_cell_removal_authorized':False})
                del doc,sections
                budgets.append(reader_budget())
                if time.monotonic()-started>MAX_SECONDS:raise UserError('Finite complete capsule capture read exceeded')
        with (out/'room-capsules-SOURCE-ONLY.json').open('xb') as stream:write(stream,{'format':'awft-current-eastern-room-capsules:1',
            'checkpoint_id':CHECKPOINT,'checkpoint_sha256':CHECKPOINT_SHA,'source_sha256':digest(Path(__file__)),
            'pods':pods,'held_current_BEs':holds,'all_current_BE_records':rows,'relocation_execution_forbidden':True})
        success=True
    finally:
        if snapshot:snapshot.close()
        if not success:(out/'FAILED-READONLY.json').write_bytes(canonical({'status':'FAILED_PARTIAL_NO_NATIVE_ACTION','checkpoint_id':CHECKPOINT,'output_bytes':total,'native_actions':0,'partials_preserved':True})+b'\n')
    manifest={'format':'awft-current-eastern-urban-custody:1','checkpoint_id':CHECKPOINT,'checkpoint_sha256':CHECKPOINT_SHA,
        'source_sha256':digest(Path(__file__)),'source_refs':refs,'historical52_727_ledger_sha256':LEDGER_SHA,
        'FULL_chunks':full_chunks,'current_saved_BE_count_in_eastern_study':len(rows),'current_BE_types':dict(be_types),
        'source_classifications':dict(stats),'room_capsules':len(pods),'held_current_BE_count':len(holds),
        'complete_source_capsule_cells':len(captured),'capsule_cells_are_current_capture_preimages_not_demolition_authority':True,
        'shared_non_BE_support_or_AIR_capture_cells':sum(len(v)>1 for v in captured.values()),
        'shared_source_support_removal_gate':'Do not retire a shared source support until every dependent actual native capture is durable and conserved',
        'raw_saved_sources':sources,'reserve_guard':reserve,'peak_owned_reader_RSS':max(r['owned_reader_rss_bytes'] for r in budgets),
        'native_class_slots_components_proof':'PENDING; saved typed data never implies actual Container size, loot resolution or component readiness',
        'native_actions':0,'world_writes':0,'inventory_writes':0,'relocation_execution_forbidden':True,
        'files':{p.name:{'sha256':digest(p),'bytes':p.stat().st_size} for p in out.iterdir() if p.is_file()}}
    raw=canonical(manifest)+b'\n'
    if total+len(raw)>MAX_OUTPUT:raise UserError('Final finite custody manifest exceeded')
    (out/'manifest.json').write_bytes(raw)
    return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'current_BEs':len(rows),'room_capsules':len(pods),'held_BEs':len(holds),'bytes':total+len(raw),'native_actions':0}


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--home',type=Path,required=True);args=a.parse_args();print(json.dumps(prepare(args.home),indent=2))
