"""Ordinary Keel/Cask plans after the three real native room moves.

Templates remain construction-forbidden. Admission additionally needs all three
marked native move/conservation receipts and a fresh real full-before proof.
No old stock is ever supplied in the architecture DELTA.
"""
from __future__ import annotations
import argparse,copy,hashlib,json,time
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
import nbtlib
from control_room.common import UserError,digest,read_json
from tools.artistic_captains_hall import native_payload
from tools.artistic_east_tortuga_retrofit import checked,with_exact_be_tags
from tools.artistic_eastern_urban_custody import canonical
from tools.artistic_maritime_depth import admit_owner
from tools.artistic_north_rebuild_custody import decoded_chunk
from tools.native_eastern_relocation import FIRST_THREE,LAYOUT,checked_row
from tools.native_relocation_request import native_proof,reference
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld,unpack_section

MIB=1024**2
DESIGN=('staging/keel-cask-original-urban-block-1793211496281941800/building-SOURCE-ONLY.json','476dc2c4d1da9e101384c12b9c76d6d85703b3274df774128f1996a1dd822c74')


def prepare(home,catalog_path,catalog_sha):
    home=Path(home).resolve();reserve=guard(MIB,8*MIB);receipt=read_json(home/'dashboard/settlement/backup-receipt.json');registry=read_json(home/'dashboard/settlement/registry.json')
    admit_owner(home,read_json(home/'dashboard/artistic-owner.json'),receipt,receipt['id'],receipt['sha256'])
    design=checked(home/DESIGN[0],DESIGN[1],4*MIB);catalog=checked(Path(catalog_path),catalog_sha,2*MIB)
    wanted={tuple(r[:3]):r[3] for r in design['blocks']};grouped=defaultdict(list)
    for q in wanted:grouped[q[0]//16,q[2]//16].append(q)
    snapshot=None;before={};current_bes={}
    try:
        snapshot=BackupWorld(home,receipt,registry);name=snapshot.prefix+'r.2.-3.mca';meta=snapshot.files[name]
        if not 8192<=meta['size']<=48*MIB:raise UserError('Finite actual saved preimage region')
        raw=snapshot.archive.read(name)
        if hashlib.sha256(raw).hexdigest()!=meta['sha256']:raise UserError('Saved region digest differs')
        for (cx,cz),positions in grouped.items():
            doc=decoded_chunk(raw,cx,cz);sections={int(s['Y']):s for s in doc.get('sections',[])}
            for q in positions:before[q]=unpack_section(sections.get(q[1]//16,{}),*q)
            for be in doc.get('block_entities',[]):
                q=tuple(int(be[k]) for k in ('x','y','z'))
                if q in wanted:current_bes[q]=be
            del doc,sections
    finally:
        if snapshot:snapshot.close()
    # Prospective state, explicitly distinguished from an observed preimage.
    # Only genuine completed moves can later make this expectation current.
    virtual=dict(before);tags=dict(current_bes);retained={};rows=[]
    for ident in FIRST_THREE:
        row=checked_row(catalog,ident);source=checked(home/row['source_original']['path'],row['source_original']['sha256'],MIB)
        field={tuple(r[:3]):source['palette'][r[3]] for r in source['blocks']};d=row['translation_xyz']
        for r in row['source_cover_preparations']:field[tuple(r['position'])]='minecraft:air'
        for q in field:
            if q in virtual:virtual[q]='minecraft:air';tags.pop(q,None)
        for q,state in field.items():
            dest=tuple(q[i]+d[i] for i in range(3))
            if dest in virtual:virtual[dest]=state
        for r in source['block_entities']:
            old=tuple(r['pos']);q=tuple(old[i]+d[i] for i in range(3));tag=nbtlib.parse_nbt(r['nbt'])
            for i,k in enumerate(('x','y','z')):tag[k]=nbtlib.Int(q[i])
            if q in virtual:tags[q]=tag;retained[q]=tag
        rows.append({'capsule_id':ident,'source_original_sha256':row['source_original']['sha256'],'translation_xyz':d})
    expected={tuple(q) for q in design['retained_current_BE_points']}
    if set(retained)!=expected or len(retained)!=17:raise UserError('All seventeen actual future native object positions required')
    changed={q:v for q,v in wanted.items() if virtual[q]!=v};foreign=[]
    for q in tags:
        if q in changed:foreign.append(list(q))
    if foreign:raise UserError('The architecture would replace an actual or moved BE; hold: '+str(foreign))
    newtags={tuple(r['pos']):nbtlib.parse_nbt(r['nbt']) for r in design['new_fixture_tags_ONLY']}
    if set(newtags)&set(tags) or not set(newtags)<=set(changed):raise UserError('New fixture may not overwrite existing native data')
    if any(q in changed for q in expected):raise UserError('Do not replay even the block state of a conserved native object')
    prior={q:virtual[q] for q in changed};fulltags={**tags,**newtags}
    outputs={
        'after-three-moves-full-before-PROSPECTIVE-VERIFY-ONLY.json':with_exact_be_tags(native_payload(registry,virtual,receipt['sha256'],'PROSPECTIVE after three genuine conserved room moves; NOT observed current state'),tags),
        'architecture-delta-before-PROSPECTIVE-VERIFY-ONLY.json':native_payload(registry,prior,receipt['sha256'],'Prospective exact architectural targets only, no old BE target'),
        'architecture-DELTA-SOURCE-ONLY.json':with_exact_be_tags(native_payload(registry,changed,receipt['sha256'],'SOURCE architecture delta after actual three moves/full-before; NOT admitted'),newtags),
        'architecture-full-after-VERIFY-ONLY.json':with_exact_be_tags(native_payload(registry,wanted,receipt['sha256'],'Verification-only complete new compound including conserved actual stock; NEVER place this file'),fulltags)}
    out=home/'staging'/('keel-cask-post-native-moves-ordinary-'+str(time.time_ns()));out.mkdir()
    for name,data in outputs.items():(out/name).open('xb').write(data)
    manifest={'format':'awft-keel-cask-post-native-move-templates:1','design':reference(home,home/DESIGN[0]),'catalog':reference(home,catalog_path),
        'checkpoint_id':receipt['id'],'checkpoint_sha256':receipt['sha256'],'required_native_moves':rows,
        'source_cells':len(wanted),'delta_cells':len(changed),'conserved_BE_points':17,'old_BE_or_stock_writes_in_delta':0,'new_supplied_fixture_tags':len(newtags),
        'preimage_status':'PROSPECTIVE; requires three actual native conservation completions plus fresh native full-before',
        'source_sha256':digest(Path(__file__)),'files':{n:reference(home,out/n) for n in outputs},'construction_forbidden':True,'native_actions':0,'reserve_guard':reserve}
    (out/'manifest.json').write_bytes(canonical(manifest)+b'\n');return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'delta_cells':len(changed),'full_cells':len(wanted),'old_BE_writes':0}


def admit(home,manifest_path,manifest_sha,move_receipts,before_proof,before_sha,review,review_sha):
    home=Path(home).resolve();reserve=guard(MIB,4*MIB);m=checked(Path(manifest_path),manifest_sha,MIB);receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    admit_owner(home,read_json(home/'dashboard/artistic-owner.json'),receipt,receipt['id'],receipt['sha256'])
    if m['checkpoint_sha256']!=receipt['sha256']:raise UserError('Exact current architecture/checkpoint required')
    a=checked(Path(review),review_sha,65536)
    if a.get('approved') is not True or a.get('eastern_layout_sha256')!=LAYOUT[1] or 'approved-north-bank-city-rebuild' not in a.get('allowed_operations',[]):raise UserError('Actual reviewed city layout approval required')
    if set(move_receipts)!=set(FIRST_THREE):raise UserError('All three real conserved moves required; no inferred completion')
    for ident,(path,sha) in move_receipts.items():
        r=checked(Path(path),sha,MIB)
        if Path(path).with_name(Path(path).name+'.complete').read_text().strip()!=sha or r.get('capsule_id')!=ident or r.get('operation')!='move' or r.get('failed') is not False or r.get('clone_invoked') is not True or r.get('cleanup_passed') is not True or r.get('quarantine') is not False or r.get('owned_chunk_tickets')!=0 or r.get('pending_owned_futures')!=0:
            raise UserError('Marked clean exact native movement/conservation required: '+ident)
    rec=m['files']['after-three-moves-full-before-PROSPECTIVE-VERIFY-ONLY.json'];native_proof(home,before_proof,before_sha,rec['sha256'],m['source_cells'])
    proof=read_json(before_proof);age=(datetime.now(timezone.utc)-datetime.fromisoformat(proof['finished'].replace('Z','+00:00'))).total_seconds()
    if not 0<=age<=1200:raise UserError('Fresh actual post-move full-before proof required')
    src=m['files']['architecture-DELTA-SOURCE-ONLY.json'];doc=checked(home/src['path'],src['sha256'],4*MIB)
    doc['construction_forbidden']=False;doc.pop('verification_only',None);doc['name']='ADMITTED Keel/Cask architecture DELTA only after three genuine native conserved moves and actual full-before'
    out=home/'staging'/('keel-cask-architecture-ADMITTED-'+str(time.time_ns()));out.mkdir();(out/'architecture-DELTA.json').write_bytes(canonical(doc)+b'\n')
    admission={'source_manifest_sha256':manifest_sha,'native_before_sha256':before_sha,'actual_move_receipts':{k:{'path':str(v[0]),'sha256':v[1]} for k,v in move_receipts.items()},'native_actions':0,'reserve_guard':reserve}
    (out/'admission.json').write_bytes(canonical(admission)+b'\n');return {'folder':str(out),'delta_sha256':digest(out/'architecture-DELTA.json'),'native_actions':0}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);p.add_argument('--catalog',type=Path,required=True);p.add_argument('--catalog-sha256',required=True)
    a=p.parse_args();print(json.dumps(prepare(a.home,a.catalog,a.catalog_sha256),indent=2))
