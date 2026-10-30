"""Fresh Pippin saved recapture after the two actual native50 cover changes.

The db5e catalogue, original06 custody and all old source files stay immutable.
No native call, request installation or metadata-only checkpoint rebind.
"""
from __future__ import annotations
import argparse,copy,json,time
from datetime import datetime,timezone
from pathlib import Path
from control_room.common import UserError,digest,read_json
from tools.artistic_bridge_refinement import flatten
from tools.artistic_captains_hall import native_payload
from tools.artistic_east_tortuga_retrofit import checked
from tools.artistic_eastern_urban_custody import canonical
from tools.artistic_maritime_depth import admit_owner
from tools.native_eastern_relocation import PIPPIN,SEALED_CATALOG_SHA,checked_row
from tools.native_relocation_request import reference,unchanged_saved_capture
from tools.playtest import guard

MIB=1024**2
OPERATIONS=('staging/pippin-native50-cover-admission-1793213153163483300/operations.json','b9bbee66f19248efb167d4e66a2f92ff2fa420198acff7eb0522700189e3bec8')
CATALOG='staging/eastern-approved-capsule-catalog-1793213199055341700/approved-capsules-PRIVATE.json'
EXPECTED_COUNTS=(2,2,320,320,80)
EXPECTED_OPS=('verify','place','verify','verify','verify')


def cover_history(home):
    rows=checked(home/OPERATIONS[0],OPERATIONS[1],65536)
    if len(rows)!=5:raise UserError('Exact native50 before/place/source/destination/support history required')
    last=None;docs=[]
    for row,kind,count in zip(rows,EXPECTED_OPS,EXPECTED_COUNTS):
        planref,ref=row['plan'],row['terminal'];plan=checked(home/planref['path'],planref['sha256'],MIB);terminal=checked(home/ref['path'],ref['sha256'],131072)
        if (home/ref['path']).with_name(Path(ref['path']).name+'.complete').read_text().strip()!=ref['sha256'] or terminal.get('operation')!=kind or terminal.get('plan_sha256')!=planref['sha256'] or terminal.get('blocks')!=count or terminal.get('failures')!=0 or terminal.get('cleanup_required') is not False or terminal.get('temporary_tickets_remaining')!=0 or terminal.get('pending_shared_chunk_futures')!=0 or 'error' in terminal or 'ticket_cleanup_error' in terminal:
            raise UserError('Exact genuine clean native cover history required')
        if kind=='verify' and terminal.get('status')!='verified actual block identities, orientation, block entities and supplied inventories':raise UserError('Real completed verification required')
        if kind=='place' and terminal.get('status')!='construction actions complete; native verification and restart still required':raise UserError('Real completed two-cell placement required')
        at=datetime.fromisoformat(terminal['finished'].replace('Z','+00:00'))
        if at>datetime.now(timezone.utc) or last is not None and at<last:raise UserError('Genuine ordered, nonfuture native history required')
        last=at;docs.append(plan)
    source=(1236,64,-1194);dest=(1224,64,-1194)
    if flatten(docs[0])!={source:'regions_unexplored:grass_sprouts',dest:'supplementaries:barnacles[down=true,east=false,north=false,south=false,up=false,waterlogged=false,west=false]'} or flatten(docs[1])!={source:'minecraft:air',dest:'minecraft:air'} or docs[1].get('block_entities') or docs[1].get('commands') or docs[1].get('construction_forbidden') is not False:
        raise UserError('Only the two genuinely authorized ordinary cover cells may differ')
    return rows,docs


def prepare(home,checkpoint_id,checkpoint_sha):
    home=Path(home).resolve();reserve=guard(MIB,4*MIB);receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    admit_owner(home,read_json(home/'dashboard/artistic-owner.json'),receipt,checkpoint_id,checkpoint_sha)
    rows,docs=cover_history(home);catalog=checked(home/CATALOG,SEALED_CATALOG_SHA,2*MIB);row=checked_row(catalog,PIPPIN)
    original=checked(home/row['source_original']['path'],row['source_original']['sha256'],MIB)
    if original['block_entities']!=docs[2]['block_entities']:raise UserError('All seven original supplied tag strings remain immutable')
    source,dest,supports=map(flatten,docs[2:]);registry=read_json(home/'dashboard/settlement/registry.json')
    captured=unchanged_saved_capture(home,receipt,registry,source,dest,supports,original['block_entities'])
    if source[1236,64,-1194]!='minecraft:air' or dest[1224,64,-1194]!='minecraft:air' or any(s!='minecraft:air' for s in dest.values()):raise UserError('The actual authorized cover changes and empty destination must persist')
    doc=json.loads(native_payload(registry,source,checkpoint_sha,'Actual NEW saved source after authenticated native50 cover delta; seven typed tags independently unchanged'))
    doc['block_entities']=copy.deepcopy(original['block_entities'])
    outputs={'source-prepared-FUTURE-VERIFY-ONLY.json':canonical(doc)+b'\n',
        'destination-empty-FUTURE-VERIFY-ONLY.json':native_payload(registry,dest,checkpoint_sha,'Actual NEW saved destination AIR after authenticated native50 cover delta'),
        'retained-supports-VERIFY-ONLY.json':native_payload(registry,supports,checkpoint_sha,'Actual NEW saved retained destination supports'),
        'actual-current-saved-recapture-PRIVATE.json':canonical(captured)+b'\n'}
    out=home/'staging'/('pippin-current-native50-recapture-'+str(time.time_ns()));out.mkdir()
    for name,data in outputs.items():(out/name).open('xb').write(data)
    manifest={'format':'awft-approved-capsule-geometry:2','capsule_id':PIPPIN,'catalog':reference(home,home/CATALOG),
        'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'source_sha256':digest(Path(__file__)),
        'original_source':row['source_original'],'original_destination':row['destination_original'],
        'historical_native50_cover_operations':reference(home,home/OPERATIONS[0]),'historical_native50_receipts':[r['terminal'] for r in rows],
        'files':{n:reference(home,out/n) for n in outputs},'all720actual_saved_states_reread':True,'all7typed_original_tags_unchanged':True,
        'authorized_cover_changes':2,'catalog_rewritten':False,'current_native_before_proved':False,'native_actions':0,'reserve_guard':reserve}
    (out/'manifest.json').write_bytes(canonical(manifest)+b'\n');return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'source_BE_count':7,'states_compared':720,'native_actions':0}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);p.add_argument('--checkpoint-id',required=True);p.add_argument('--checkpoint-sha256',required=True);a=p.parse_args();print(json.dumps(prepare(a.home,a.checkpoint_id,a.checkpoint_sha256),indent=2))
