"""Only five revised destination captures, one historical6ad MCA read, no native action."""
from __future__ import annotations
import copy,hashlib,json,time
from collections import defaultdict
from pathlib import Path
from control_room.common import UserError,digest,read_json
from tools.artistic_east_tortuga_retrofit import checked,with_exact_be_tags
from tools.artistic_eastern_urban_custody import canonical
from tools.artistic_captains_hall import native_payload
from tools.artistic_eastern_move_blueprint import cells
from tools.artistic_north_rebuild_custody import decoded_chunk
from tools.native_eastern_relocation import transaction
from tools.native_relocation_request import reference
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld,unpack_section

MIB=1024**2
BASE='staging/eastern-catalog-r5-1793219566430973900/approved98-capsules-PRIVATE.json'
BASE_SHA='698969e25fb001c21fb4a9b8301d96b7892d0affe9a9263369c74bba591d7fc5'
ALLOCATION='staging/eastern-floor-clearance-1793225532335615700/allocation-SOURCE-ONLY.json'
ALLOCATION_SHA='ad2d190159c0913c84b1585494067060da1b76a32c0da862ba44bfd8b0f4b87b'
CHECKPOINT='0ba7ad2097fb52273a37da6a76d8fc030133b79cd26d81b97531d8d74c2546c2'

def prepare(home):
    home=Path(home).resolve();reserve=guard(2*MIB,16*MIB);base=checked(home/BASE,BASE_SHA,2*MIB);allocation=checked(home/ALLOCATION,ALLOCATION_SHA,2*MIB)
    registry=read_json(home/'dashboard/settlement/registry.json');receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    if receipt.get('sha256')!=CHECKPOINT or receipt.get('verified') is not True:raise UserError('Only immutable6ad source capture here, no blind rebind')
    original={r['id']:r for r in base['capsules']};selected={r['id']:r for r in allocation['room_allocations']};changed=[r['id'] for r in allocation['lifted_rooms']]
    if len(changed)!=5 or len(set(changed))!=5 or len(original)!=98:raise UserError('Exact5/98 source allocation required')
    ledger_root=Path(registry['world_path']).resolve()/'data/awft-relocations';checks=[]
    for ident in changed:
        for label,translation in [('prior',original[ident]['translation_xyz']),('new',selected[ident]['translation_xyz'])]:
            tx=transaction(home,ident,translation);p=ledger_root/tx
            if p.exists():raise UserError('Preserve existing changed-room ledger; no reallocation: '+ident+' '+label)
            checks.append({'capsule_id':ident,'variant':label,'transaction_id':tx,'ledger_directory_absent':True})
    wanted=set();prepared={}
    for ident in changed:
        b=selected[ident]['destination_bounds_xyz'];dest=cells(b);support={(x,b[1]-1,z) for x in range(b[0],b[3]+1) for z in range(b[2],b[5]+1)}
        wanted|=dest|support;prepared[ident]=(dest,support)
    grouped=defaultdict(list)
    for q in wanted:grouped[q[0]//16,q[2]//16].append(q)
    saved={};bes={};world=None
    try:
        world=BackupWorld(home,receipt,registry);name=world.prefix+'r.2.-3.mca';meta=world.files[name]
        if not 8192<=meta['size']<=48*MIB:raise UserError('Finite exact saved member required')
        raw=world.archive.read(name)
        if hashlib.sha256(raw).hexdigest()!=meta['sha256']:raise UserError('Saved region changed')
        for (cx,cz),positions in grouped.items():
            doc=decoded_chunk(raw,cx,cz);sections={int(s['Y']):s for s in doc.get('sections',[])}
            for q in positions:saved[q]=unpack_section(sections.get(q[1]//16,{}),*q)
            for tag in doc.get('block_entities',[]):
                q=tuple(int(tag[k]) for k in ('x','y','z'))
                if q in wanted:bes[q]=tag
        region={'name':name.rsplit('/',1)[-1],'sha256':meta['sha256'],'bytes':len(raw)}
    finally:
        if world:world.close()
    out=home/'staging'/('eastern-final-floor-catalog-'+str(time.time_ns()));out.mkdir();result=copy.deepcopy(base);rows=[]
    for index,old in enumerate(base['capsules']):
        r=copy.deepcopy(old);ident=r['id'];a=selected[ident]
        if ident in changed:
            if 'prior_translation_xyz' in r:raise UserError('Multiple historical variants need explicit separate guards')
            r['prior_translation_xyz']=list(r['translation_xyz'])
            for label,positions in zip(('destination','supports'),prepared[ident]):
                p=out/(f'{index:03d}-{label}-historical6ad.json');p.write_bytes(with_exact_be_tags(native_payload(registry,{q:saved[q] for q in positions},CHECKPOINT,'Historical6ad actual states ONLY; fresh real native before still required'),{q:bes[q] for q in positions if q in bes}));r[label+'_original']=reference(home,p)
            r.update(destination_bounds_xyz=a['destination_bounds_xyz'],translation_xyz=a['translation_xyz'],destination_cover_preparations=[])
        r['dependencies']=a['required_preceding_native_capture_ids'];rows.append(r)
    for r in rows:
        old=original[r['id']]
        if r['source_original']!=old['source_original'] or r['source_bounds_xyz']!=old['source_bounds_xyz']:raise UserError('Raw source custody changed')
        if r['id'] not in changed and any(r[k]!=old[k] for k in ('destination_bounds_xyz','translation_xyz','destination_original','supports_original')):raise UserError('Unrelated93 destination changed')
    result.update(capsules=rows,allocation_addendum_sha256=ALLOCATION_SHA,native_move_order=allocation['native_move_order'],prior_catalogue_sha256=BASE_SHA,
        capture_role='Historical immutable6ad source only; current native before/once-only gates required')
    p=out/'approved98-capsules-PRIVATE.json';p.write_bytes(canonical(result)+b'\n')
    manifest={'format':'awft-final-five-floor-catalogue:1','catalog':reference(home,p),'allocation_sha256':ALLOCATION_SHA,'prior_catalogue_sha256':BASE_SHA,
        'unchanged93_destinations':True,'all98_raw_source_refs_unchanged':True,'changed5_ledger_absence_point_in_time':checks,'saved_region':region,
        'no_current_state_claim':True,'native_actions':0,'source_sha256':digest(Path(__file__)),'reserve_guard':reserve}
    (out/'manifest.json').write_bytes(canonical(manifest)+b'\n');return {'folder':str(out),'catalog_sha256':digest(p),'manifest_sha256':digest(out/'manifest.json'),'changed5_ledger_directories_absent':True,'native_actions':0}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.home),indent=2))
