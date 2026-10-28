"""Exact current source/destination readback for proposed native clone-moves.

No clone, command, runtime or world write is performed here. The native wrapper
must independently prove full model closure, live class/slots/components, entity
clearance and durable exactly-once custody before invoking vanilla CloneCommands.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import hashlib,json,time
from pathlib import Path

from control_room.common import UserError,digest,read_json
from tools.artistic_captains_hall import native_payload
from tools.artistic_east_tortuga_retrofit import checked,with_exact_be_tags
from tools.artistic_eastern_urban_custody import CHECKPOINT,CHECKPOINT_SHA,canonical
from tools.artistic_eastern_urban_layout import FINE
from tools.artistic_maritime_depth import admit_owner
from tools.artistic_north_rebuild_custody import decoded_chunk
from tools.artistic_zipline_catenary import reader_budget
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld,unpack_section,properties

MIB=1024**2
MAX_OUTPUT=16*MIB
AIR={'minecraft:air','minecraft:cave_air','minecraft:void_air'}
GROUND={'minecraft:gravel','minecraft:dirt','minecraft:coarse_dirt','minecraft:grass_block',
        'minecraft:stone','minecraft:andesite','minecraft:cobblestone','minecraft:stone_bricks',
        'minecraft:mossy_cobblestone','minecraft:mossy_stone_bricks','minecraft:polished_andesite'}


def cells(box):
    if len(box)!=6 or any(type(v)is not int for v in box) or any(box[i]>box[i+3] for i in range(3)):raise UserError('Exact finite integer capsule bounds required')
    if any(box[i+3]-box[i]>31 for i in range(3)):raise UserError('Split a capsule exceeding its finite32-block axis')
    return {(x,y,z) for x in range(box[0],box[3]+1) for y in range(box[1],box[4]+1) for z in range(box[2],box[5]+1)}


def closed_vanilla_pairs(field,box):
    own=cells(box);failures=[]
    for q,s in field.items():
        if q not in own:continue
        ident=s.split('[',1)[0];props=properties(s)
        if ident.endswith('_door') and not ident.endswith('_trapdoor'):
            half=props.get('half')
            if half not in ('lower','upper'):failures.append({'position':list(q),'reason':'unknown door half'});continue
            other=(q[0],q[1]+(1 if half=='lower' else -1),q[2]);wanted='upper' if half=='lower' else 'lower'
            if other not in own or field.get(other,'').split('[',1)[0]!=ident or properties(field.get(other,'' )).get('half')!=wanted:
                failures.append({'position':list(q),'reason':'door pair escapes capsule'})
        if ident.startswith('minecraft:') and ident.endswith('_bed'):
            f=props.get('facing');part=props.get('part')
            if f not in ('north','south','east','west') or part not in ('head','foot'):
                failures.append({'position':list(q),'reason':'unknown vanilla bed pair'});continue
            dx,dz={'north':(0,-1),'south':(0,1),'east':(1,0),'west':(-1,0)}[f]
            if part=='head':dx,dz=-dx,-dz
            other=(q[0]+dx,q[1],q[2]+dz);o=field.get(other,'')
            if other not in own or o.split('[',1)[0]!=ident or properties(o).get('facing')!=f or properties(o).get('part')==part:
                failures.append({'position':list(q),'reason':'vanilla bed pair escapes capsule'})
    return failures


def prepare(home,layout_manifest,layout_sha):
    home=Path(home).resolve();reserve=guard(2*MIB,MAX_OUTPUT);budgets=[reader_budget()];start=time.monotonic()
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve():raise UserError('Explicit private artistic source study only')
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json');registry=read_json(home/'dashboard/settlement/registry.json')
    admit_owner(home,read_json(home/'dashboard/artistic-owner.json'),receipt,CHECKPOINT,CHECKPOINT_SHA)
    mpath=Path(layout_manifest).resolve()
    if not mpath.is_relative_to(home/'staging'):raise UserError('Reviewed private source layout required')
    manifest=checked(mpath,layout_sha,2*MIB);file=manifest['files']['urban-plan-REVIEW-ONLY.json']
    layout=checked(mpath.parent/'urban-plan-REVIEW-ONLY.json',file['sha256'],8*MIB)
    if (layout['current_stopped_checkpoint_id'],layout['current_stopped_checkpoint_sha256'])!=(CHECKPOINT,CHECKPOINT_SHA):raise UserError('Exact current06 layout binding required')
    custody=checked(home/layout['current_custody_manifest_relative'],layout['current_custody_manifest_sha256'],2*MIB)
    cp=home/layout['current_custody_manifest_relative'];r=custody['files']['room-capsules-SOURCE-ONLY.json']
    capsules=checked(cp.parent/'room-capsules-SOURCE-ONLY.json',r['sha256'],2*MIB);byid={r['id']:r for r in capsules['pods']}
    fine=checked(home/FINE[0],FINE[1],8*MIB);original_cover={}
    for sample in fine['samples']:
        if sample['kind']!='dry' or sample['authored_keepout']:continue
        for item in sample.get('ordinary_natural_soft_cover',[]):original_cover[tuple(item['position'])]=item['state']
        visible=sample.get('visible')
        if visible and visible[1].split('[',1)[0] in {'minecraft:short_grass','minecraft:tall_grass','minecraft:fern','minecraft:large_fern','regions_unexplored:grass_sprouts'}:
            original_cover[(sample['x'],visible[0],sample['z'])]=visible[1]
    moves=layout['exact_proposed_native_pod_transfers'];deps={r['pod_id']:r['required_completed_move_ids'] for r in layout['native_transfer_dependencies']}
    wanted=set()
    for row in moves:
        for b in (row['source_support_bounds_xyz'],row['destination_support_bounds_xyz']):
            wanted|=cells(b)
            wanted|={(x,b[1]-1,z) for x in range(b[0],b[3]+1) for z in range(b[2],b[5]+1)}
    if len(wanted)>80000:raise UserError('Finite proposed source/destination readback exceeded80k cells')
    bychunk=defaultdict(list)
    for q in wanted:bychunk[q[0]//16,q[2]//16].append(q)
    saved={};bes={};snapshot=None
    try:
        snapshot=BackupWorld(home,receipt,registry);name=snapshot.prefix+'r.2.-3.mca';record=snapshot.files.get(name)
        if not record or not 8192<=record['size']<=48*MIB or snapshot.archive.getinfo(name).file_size!=record['size']:raise UserError('Exact single finite MCA required')
        raw=snapshot.archive.read(name)
        if hashlib.sha256(raw).hexdigest()!=record['sha256']:raise UserError('Current stopped region bytes differ')
        for (cx,cz),positions in sorted(bychunk.items()):
            doc=decoded_chunk(raw,cx,cz);sections={int(v['Y']):v for v in doc.get('sections',[])}
            if int(doc.get('DataVersion',0))!=3955:raise UserError('Current native1.21.1 DataVersion required')
            for q in positions:
                section=sections.get(q[1]//16);saved[q]=unpack_section(section,*q) if section is not None else 'minecraft:air'
            for be in doc.get('block_entities',[]):
                q=tuple(int(be[v]) for v in ('x','y','z'))
                if q in wanted:bes[q]=be
            del doc,sections;budgets.append(reader_budget())
            if time.monotonic()-start>90:raise UserError('Bounded90s destination readback exceeded')
        source_ref={'file':'r.2.-3.mca','sha256':record['sha256'],'bytes':len(raw)}
    finally:
        if snapshot:snapshot.close()
    assessed=[];first=[];identities=[]
    for row in moves:
        ident=row['pod_id'];source=row['source_support_bounds_xyz'];dest=row['destination_support_bounds_xyz'];sp=cells(source);dp=cells(dest)
        pairs=closed_vanilla_pairs(saved,source)
        if row['translation_xyz']==[0,0,0]:identities.append(ident)
        fluids=[q for q in sp if saved[q].split('[',1)[0] in ('minecraft:water','minecraft:lava') or properties(saved[q]).get('waterlogged')=='true']
        bepoints={tuple(r['source_position']) for r in byid[ident]['records']}
        foreign=[q for q in sp if q in bes and q not in bepoints]
        blockers=[q for q in dp if saved[q].split('[',1)[0] not in AIR]
        ordinary=[q for q in blockers if saved[q]==original_cover.get(q) and q not in bes]
        hard=[q for q in blockers if q not in ordinary]
        support={(x,dest[1]-1,z) for x in range(dest[0],dest[3]+1) for z in range(dest[2],dest[5]+1)}
        badsupport=[q for q in support if saved[q].split('[',1)[0] not in GROUND or properties(saved[q]).get('waterlogged')=='true']
        data={'pod_id':ident,'source_bounds_xyz':source,'destination_bounds_xyz':dest,'translation_xyz':row['translation_xyz'],
            'required_completed_move_ids':deps[ident],'all_BE_point_transfers':row['BE_point_transfers'],
            'source_saved_vanilla_door_bed_pair_failures':pairs,'source_saved_fluid_cells':[list(q) for q in fluids],
            'foreign_source_BE_positions':[list(q) for q in foreign],'destination_current_nonAIR_count':len(blockers),
            'destination_current_nonAIR_first':[list(q) for q in sorted(blockers)[:8]],
            'exact_unchanged_original_natural_cover_preparation':[{'position':list(q),'before':saved[q],'proposed_after':'minecraft:air','authority':'Exact original1m pre-grid ordinary cover; no BE; limited new room footprint only'} for q in sorted(ordinary)],
            'destination_other_nonAIR_count':len(hard),
            'destination_below_floor_not_whitelisted_solid_count':len(badsupport),
            'first_live_native_move_eligible':False,'native_model_closure_live_entities_class_slots_components':'PENDING mandatory actual native inspection',
            'execution_forbidden':True}
        eligible=not(deps[ident] or pairs or fluids or foreign or hard or badsupport or row['translation_xyz']==[0,0,0])
        data['saved_field_only_independent_empty_supported_candidate']=eligible and not blockers
        data['saved_candidate_REQUIRING_EXACT_NATURAL_COVER_PREPARATION']=eligible and bool(blockers)
        if eligible:first.append(data)
        assessed.append(data)
    # Large enough to exercise real multi-object item conservation, but ground
    # level with an exact empty destination. It remains merely a SOURCE choice.
    first.sort(key=lambda r:(len(r['exact_unchanged_original_natural_cover_preparation']),-len(r['all_BE_point_transfers']),r['pod_id']))
    if not first:
        failed=home/'staging'/('eastern-native-move-blueprint-HELD-'+str(time.time_ns()));failed.mkdir()
        report={'checkpoint_id':CHECKPOINT,'checkpoint_sha256':CHECKPOINT_SHA,'status':'NO qualified first saved capsule; no native action',
            'assessments':assessed,'native_actions':0,'execution_forbidden':True}
        (failed/'FAILED-READONLY.json').write_bytes(canonical(report)+b'\n')
        raise UserError('No dependency-free actual AIR/supported first capsule; bounded reasons preserved in '+str(failed))
    selected=first[0];source=selected['source_bounds_xyz'];dest=selected['destination_bounds_xyz'];sp=cells(source);dp=cells(dest)
    support={(x,dest[1]-1,z) for x in range(dest[0],dest[3]+1) for z in range(dest[2],dest[5]+1)}
    source_bes={q:b for q,b in bes.items() if q in sp}
    prepare_cover={tuple(r['position']):saved[tuple(r['position'])] for r in selected['exact_unchanged_original_natural_cover_preparation']}
    outputs={
        'first-source-full-before-VERIFY-ONLY.json':with_exact_be_tags(native_payload(registry,{q:saved[q] for q in sp},CHECKPOINT_SHA,'Actual06 source room only; no clone or removal approval'),source_bes),
        'first-destination-current-before-VERIFY-ONLY.json':native_payload(registry,{q:saved[q] for q in dp},CHECKPOINT_SHA,'Actual06 destination including explicitly retained ordinary cover before any approved preparation'),
        'first-destination-after-cover-FUTURE-VERIFY-ONLY.json':native_payload(registry,{q:'minecraft:air' for q in dp},CHECKPOINT_SHA,'PROSPECTIVE empty destination ONLY AFTER real one-cell natural-cover preparation and native proof; not observed AIR'),
        'first-destination-retained-supports-VERIFY-ONLY.json':native_payload(registry,{q:saved[q] for q in support},CHECKPOINT_SHA,'Actual06 destination retained solid supports; native sturdy-face proof still required'),
        'move-dependencies-and-current-fields-SOURCE-ONLY.json':canonical({'format':'awft-eastern-native-clone-move-blueprint:1',
            'checkpoint_id':CHECKPOINT,'checkpoint_sha256':CHECKPOINT_SHA,'layout_manifest_sha256':layout_sha,
            'current_custody_manifest_sha256':layout['current_custody_manifest_sha256'],
            'source_sha256':digest(Path(__file__)),'ordered_move_ids':[v for v in layout['ordered_native_transfer_ids'] if v not in identities],
            'identity_translations_MUST_NOT_EXECUTE':identities,'capsule_assessments':assessed,
            'first_saved_candidate':selected,'other_dependency_free_saved_AIR_supported_candidates':[r['pod_id'] for r in first[1:]],
            'native_actions':0,'execution_forbidden':True,'native_mover_gates':[
                'Exact source/destination current FULL readiness, private world/pack/checkpoint ownership and no live entities',
                'Native complete multi-block furniture/door/bed/support/model dependency closure; unknown FAILS',
                'Actual class/slot/all ItemStack component snapshots, plus durable once-only intent before CloneCommands',
                'Vanilla cardinal replace move ONLY; inspect actual relocated data/conservation before retiring old source shell',
                'Partial or uncertain command/result quarantines; no replay, fake success or silent source restoration',
                'Shared source supports retained until every dependent capture is durable; accepted/human anchors never moved'],
            'saved_source':source_ref,'observed_owned_reader_peak_RSS':max(r['owned_reader_rss_bytes'] for r in budgets),'reserve_guard':reserve})+b'\n'}
    if prepare_cover:
        outputs['first-exact-natural-cover-before-VERIFY-ONLY.json']=native_payload(registry,prepare_cover,CHECKPOINT_SHA,'Actual original ordinary cover at new-room target; verify only')
        outputs['first-exact-natural-cover-clear-PROPOSAL.json']=native_payload(registry,{q:'minecraft:air' for q in prepare_cover},CHECKPOINT_SHA,'SOURCE PROPOSAL limited exact original ordinary cover preparation; no clone/body/inventory writes')
    if sum(map(len,outputs.values()))>MAX_OUTPUT:raise UserError('Finite private blueprint output exceeded')
    out=home/'staging'/('eastern-native-move-blueprint-'+str(time.time_ns()));out.mkdir()
    for name,raw in outputs.items():(out/name).open('xb').write(raw)
    manifest={'format':'awft-eastern-native-move-blueprint-bundle:1','checkpoint_id':CHECKPOINT,'checkpoint_sha256':CHECKPOINT_SHA,
        'source_sha256':digest(Path(__file__)),'first_saved_candidate_id':selected['pod_id'],
        'saved_independent_supported_candidates':len(first),'first_requires_exact_natural_cover_preparation':len(prepare_cover),'identity_noop_capsules':len(identities),
        'live_native_qualification':'NOT RUN','native_actions':0,'execution_forbidden':True,
        'files':{p.name:{'sha256':digest(p),'bytes':p.stat().st_size} for p in out.iterdir()}}
    (out/'manifest.json').write_bytes(canonical(manifest)+b'\n')
    return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'first_candidate':selected['pod_id'],
        'source':source,'destination':dest,'BE_objects':len(source_bes),'independent_saved_candidates':len(first),'noops':len(identities),'native_actions':0}


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--home',type=Path,required=True)
    a.add_argument('--layout-manifest',type=Path,required=True);a.add_argument('--layout-sha256',required=True)
    args=a.parse_args();print(json.dumps(prepare(args.home,args.layout_manifest,args.layout_sha256),indent=2))
