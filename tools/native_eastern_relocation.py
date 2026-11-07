"""Sealed approved-room catalogue and bounded source-only relocation requests.

No requests are installed and no native actions are performed. A catalogue row
is not permission to retire a shell: actual AIR/sturdy/native-stock proofs and
the durable dependency completions are independent runtime gates.
"""
from __future__ import annotations
import argparse,copy,hashlib,json,time,zipfile
from collections import defaultdict
from pathlib import Path
import nbtlib
from control_room.common import UserError,digest,read_json,utcnow
from tools.artistic_bridge_refinement import flatten
from tools.artistic_captains_hall import native_payload
from tools.artistic_east_tortuga_retrofit import checked,with_exact_be_tags
from tools.artistic_eastern_move_blueprint import cells
from tools.artistic_eastern_urban_custody import CHECKPOINT_SHA,canonical
from tools.artistic_eastern_urban_layout import FINE
from tools.artistic_maritime_depth import admit_owner
from tools.artistic_north_rebuild_custody import decoded_chunk,typed
from tools.artistic_zipline_catenary import reader_budget
from tools.native_relocation_request import CLASS_MAP,class_hash,native_proof,reference
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld,unpack_section

MIB=1024**2
LAYOUT=('staging/eastern-coast-urban-layout-1793205607174241200/urban-plan-REVIEW-ONLY.json','6f24640d9efefae3340be80d34bcd0e4788f2ded695aefe03d1d6815761a12a4')
CUSTODY=('staging/eastern-urban-current-custody-1793210273627204600/manifest.json','ebed9164e2ee363c706c6b84a7af437e65f902bd67dab3f0d9ea7e8039de3f02')
PIPPIN='eastern22/pippins-net:room:0'
FIRST_THREE=(PIPPIN,'rose-reach/tea:room:1','density/bent-needle:room:0')
SEALED_CATALOG_SHA='db5e0fa730575ad9b0fd166dd4d52273a5105832d66636d1ca3098693199adf7'
EXTRA_CLASSES={
 'minecraft:barrel':('GAME','net.minecraft.world.level.block.entity.BarrelBlockEntity',True),
 'minecraft:chiseled_bookshelf':('GAME','net.minecraft.world.level.block.entity.ChiseledBookShelfBlockEntity',True),
 'minecraft:lectern':('GAME','net.minecraft.world.level.block.entity.LecternBlockEntity',False),
 'minecraft:bed':('GAME','net.minecraft.world.level.block.entity.BedBlockEntity',False),
 'supplementaries:book_pile':('supplementaries-1.21.1-4.0.2-neoforge.jar','net.mehvahdjukaar.supplementaries.common.block.tiles.BookPileBlockTile',True)}
CLASSES={**CLASS_MAP,**EXTRA_CLASSES}
AIR={'minecraft:air','minecraft:cave_air','minecraft:void_air'}
SOFT={'minecraft:short_grass','minecraft:tall_grass','minecraft:fern','minecraft:large_fern','regions_unexplored:grass_sprouts'}


def transaction(home,ident,delta):
    salt='PIPPIN320|-13,0,0' if ident==PIPPIN else ident+'|'+','.join(map(str,delta))
    return hashlib.sha256((str(Path(home).resolve())+'|'+CHECKPOINT_SHA+'|'+salt).encode()).hexdigest()


def checked_row(catalog,ident):
    rows=[r for r in catalog['capsules'] if r['id']==ident]
    if len(rows)!=1:raise UserError('One exact approved capsule is required')
    r=rows[0];a,b=r['source_bounds_xyz'],r['destination_bounds_xyz'];delta=r['translation_xyz']
    if not any(delta) or len(cells(a))!=r['cells'] or len(cells(b))!=r['cells'] or any(b[i]-a[i]!=delta[i] or b[i+3]-a[i+3]!=delta[i] for i in range(3)):
        raise UserError('Identity, resized or malformed capsule is not a native move')
    if not r['supported']:raise UserError('This actual capsule is held: '+str(r['holds']))
    return r


def prepare_catalog(home):
    home=Path(home).resolve();reserve=guard(2*MIB,24*MIB);budgets=[reader_budget()];started=time.monotonic()
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json');registry=read_json(home/'dashboard/settlement/registry.json')
    admit_owner(home,read_json(home/'dashboard/artistic-owner.json'),receipt,receipt['id'],receipt['sha256'])
    layout=checked(home/LAYOUT[0],LAYOUT[1],8*MIB);cm=checked(home/CUSTODY[0],CUSTODY[1],2*MIB);cf=(home/CUSTODY[0]).parent
    rm=cm['files']['room-capsules-SOURCE-ONLY.json'];pods={r['id']:r for r in checked(cf/'room-capsules-SOURCE-ONLY.json',rm['sha256'],2*MIB)['pods']}
    moves=[r for r in layout['exact_proposed_native_pod_transfers'] if any(r['translation_xyz'])]
    if len(moves)!=93:raise UserError('Exactly93 reviewed nonidentity eastern transfers required')
    byid={r['pod_id']:r for r in moves};deps={r['pod_id']:r['required_completed_move_ids'] for r in layout['native_transfer_dependencies'] if r['pod_id'] in byid}
    baseline={};tag_baseline={};wanted=set()
    path=cf/'capsule-source-cells-FULL-READONLY-PRIVATE.jsonl';rec=cm['files'][path.name]
    if digest(path)!=rec['sha256']:raise UserError('Exact original complete capsule field required')
    with path.open(encoding='utf8') as stream:
        for line in stream:
            r=json.loads(line);baseline[tuple(r['position'])]=r['current_saved']
    path=cf/'current-BEs-FULL-TYPED-PRIVATE.jsonl'
    if digest(path)!=cm['files'][path.name]['sha256']:raise UserError('Exact typed stock baseline required')
    with path.open(encoding='utf8') as stream:
        for line in stream:
            r=json.loads(line);tag_baseline[tuple(r['position'])]=r['actual_full_typed_NBT']
    for m in moves:
        a,b=m['source_support_bounds_xyz'],m['destination_support_bounds_xyz'];wanted|=cells(a)|cells(b)
        wanted|={(x,b[1]-1,z) for x in range(b[0],b[3]+1) for z in range(b[2],b[5]+1)}
    if len(wanted)>80000:raise UserError('Finite catalogue field exceeds80k cells')
    grouped=defaultdict(list)
    for q in wanted:grouped[q[0]//16,q[2]//16].append(q)
    snapshot=None;saved={};bes={}
    try:
        snapshot=BackupWorld(home,receipt,registry);name=snapshot.prefix+'r.2.-3.mca';record=snapshot.files[name]
        if not 8192<=record['size']<=48*MIB:raise UserError('One finite authenticated MCA required')
        raw=snapshot.archive.read(name)
        if len(raw)!=record['size'] or hashlib.sha256(raw).hexdigest()!=record['sha256']:raise UserError('Saved region identity differs')
        for (cx,cz),positions in sorted(grouped.items()):
            doc=decoded_chunk(raw,cx,cz)
            if int(doc.get('DataVersion',0))!=3955:raise UserError('Actual1.21.1 source data required')
            sections={int(s['Y']):s for s in doc.get('sections',[])}
            for q in positions:saved[q]=unpack_section(sections.get(q[1]//16,{}),*q)
            for be in doc.get('block_entities',[]):
                q=tuple(int(be[k]) for k in ('x','y','z'))
                if q in wanted:bes[q]=be
            del doc,sections;budgets.append(reader_budget())
            if time.monotonic()-started>90:raise UserError('Finite catalogue read exceeded90seconds')
        region_ref={'file':name.rsplit('/',1)[-1],'bytes':len(raw),'sha256':record['sha256']}
    finally:
        if snapshot:snapshot.close()
    fine=checked(home/FINE[0],FINE[1],8*MIB);original_cover={}
    for r in fine['samples']:
        v=r.get('visible')
        if r['kind']=='dry' and not r['authored_keepout'] and v:
            q=r['x'],v[0],r['z'];original_cover[q]=v[1]
            if v[1] in ('minecraft:tall_grass[half=upper]','minecraft:large_fern[half=upper]'):
                original_cover[q[0],q[1]-1,q[2]]=v[1].replace('upper','lower')
    out=home/'staging'/('eastern-approved-capsule-catalog-'+str(time.time_ns()));out.mkdir();rows=[];written=0
    def write(name,data):
        nonlocal written
        written+=len(data)
        if written>24*MIB:raise UserError('Finite catalogue allocation exceeded; partials retained')
        (out/name).open('xb').write(data);return reference(home,out/name)
    for index,m in enumerate(moves):
        ident=m['pod_id'];a,b=m['source_support_bounds_xyz'],m['destination_support_bounds_xyz'];sp,dp=cells(a),cells(b);support={(x,b[1]-1,z) for x in range(b[0],b[3]+1) for z in range(b[2],b[5]+1)}
        tags={q:bes[q] for q in sp if q in bes};expected={tuple(r['source_position']) for r in pods[ident]['records']};holds=[]
        if set(tags)!=expected:holds.append('Saved native BE membership changed or foreign object present')
        if any(q not in tag_baseline or typed(tags[q])!=tag_baseline[q] for q in tags):holds.append('Full typed stock differs from exact06 baseline')
        if any(saved[q]!=baseline.get(q) for q in sp):holds.append('Source complete state changed since reviewed original capture')
        if any(str(tag['id']) not in CLASSES for tag in tags.values()):holds.append('Unreviewed native inventory role, including linked Create toolbox; no assumed empty storage')
        if any(q in sp or q in dp for q in ((1296,65,-1250),(1296,65,-1249),(1300,65,-1255))):holds.append('Private human bed/job anchor remains in place')
        source_preps={q:saved[q] for q in sp if saved[q].split('[',1)[0] in SOFT and original_cover.get(q)==saved[q] and q not in tags}
        dest_preps={q:saved[q] for q in dp if original_cover.get(q)==saved[q] and saved[q].split('[',1)[0] in SOFT and q not in bes}
        if ident==PIPPIN:dest_preps[(1224,64,-1194)]=saved[1224,64,-1194]
        source_ref=write(f'{index:03d}-source-original.json',with_exact_be_tags(native_payload(registry,{q:saved[q] for q in sp},receipt['sha256'],'Actual sealed stopped source capsule; NOT a move'),tags))
        dest_ref=write(f'{index:03d}-destination-original.json',with_exact_be_tags(native_payload(registry,{q:saved[q] for q in dp},receipt['sha256'],'Actual sealed stopped destination; NOT empty authority'),{q:bes[q] for q in dp if q in bes}))
        support_ref=write(f'{index:03d}-supports-original.json',with_exact_be_tags(native_payload(registry,{q:saved[q] for q in support},receipt['sha256'],'Actual sealed retained destination supports'),{q:bes[q] for q in support if q in bes}))
        rows.append({'id':ident,'source_bounds_xyz':a,'destination_bounds_xyz':b,'translation_xyz':m['translation_xyz'],'cells':len(sp),'objects':len(tags),'support_cells':len(support),
            'source_original':source_ref,'destination_original':dest_ref,'supports_original':support_ref,
            'source_cover_preparations':[{'position':list(q),'before':s} for q,s in sorted(source_preps.items())],
            'destination_cover_preparations':[{'position':list(q),'before':s} for q,s in sorted(dest_preps.items())],
            'dependencies':deps[ident],'supported':not holds,'holds':holds})
    catalog={'format':'awft-approved-eastern-relocation-catalog:2','eastern_layout_sha256':LAYOUT[1],'baseline_capture_backup_sha256':CHECKPOINT_SHA,
        'catalog_capture_checkpoint_id':receipt['id'],'catalog_capture_checkpoint_sha256':receipt['sha256'],'capsules':rows,'native_actions':0}
    cref=write('approved-capsules-PRIVATE.json',canonical(catalog)+b'\n')
    manifest={'format':'awft-approved-eastern-relocation-catalog-bundle:2','catalog':cref,'capsules':len(rows),'supported':sum(r['supported'] for r in rows),
        'held':[{'id':r['id'],'reasons':r['holds']} for r in rows if not r['supported']],'checkpoint_id':receipt['id'],'checkpoint_sha256':receipt['sha256'],
        'source_sha256':digest(Path(__file__)),'saved_region':region_ref,'peak_reader_RSS':max(r['owned_reader_rss_bytes'] for r in budgets),'native_actions':0,'reserve_guard':reserve}
    (out/'manifest.json').write_bytes(canonical(manifest)+b'\n')
    return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'catalog_sha256':cref['sha256'],'capsules':len(rows),'supported':manifest['supported'],'held':manifest['held']}


def prepare_geometry(home,catalog_path,catalog_sha,ident):
    home=Path(home).resolve();reserve=guard(MIB,4*MIB);catalog=checked(Path(catalog_path),catalog_sha,2*MIB);row=checked_row(catalog,ident)
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json');registry=read_json(home/'dashboard/settlement/registry.json')
    admit_owner(home,read_json(home/'dashboard/artistic-owner.json'),receipt,receipt['id'],receipt['sha256'])
    original=checked(home/row['source_original']['path'],row['source_original']['sha256'],MIB);prior=checked(home/row['destination_original']['path'],row['destination_original']['sha256'],MIB)
    support=checked(home/row['supports_original']['path'],row['supports_original']['sha256'],MIB)
    source=flatten(original);dest=flatten(prior);supports=flatten(support);preps={tuple(r['position']):r['before'] for r in row['source_cover_preparations']}
    # Every call reads the current immutable saved source and complete typed
    # tags again. Future AIR is still separately proved by real native verify.
    snapshot=None
    try:
        snapshot=BackupWorld(home,receipt,registry)
        for q,s in source.items():
            seen=snapshot.state(q)
            if seen!=s and not(q in preps and seen=='minecraft:air'):raise UserError('Current source changed; held instead of stale rebinding: '+str(q))
        for q,s in supports.items():
            # A legitimately built new upper-floor support is current context,
            # not immutable old stock. Read its ACTUAL current state; the fresh
            # native proof and same-tick isFaceSturdy/fluid/BE gates still apply.
            supports[q]=snapshot.state(q)
            if q in snapshot.protected:raise UserError('Retained support contains a real BE')
        for rowtag in original['block_entities']:
            q=tuple(rowtag['pos']);raw=snapshot.regions[q[0]//512,q[2]//512];doc=decoded_chunk(raw,q[0]//16,q[2]//16)
            actual=[v for v in doc.get('block_entities',[]) if tuple(int(v[k]) for k in ('x','y','z'))==q]
            if len(actual)!=1 or typed(actual[0])!=typed(nbtlib.parse_nbt(rowtag['nbt'])):raise UserError('Actual current full typed source contents changed')
        for q in preps:source[q]='minecraft:air'
    finally:
        if snapshot:snapshot.close()
    outputs={'source-prepared-FUTURE-VERIFY-ONLY.json':with_exact_be_tags(native_payload(registry,source,receipt['sha256'],'Exact future source after separately verified listed source-cover preparation'),{tuple(r['pos']):nbtlib.parse_nbt(r['nbt']) for r in original['block_entities']}),
        'destination-empty-FUTURE-VERIFY-ONLY.json':native_payload(registry,{q:'minecraft:air' for q in dest},receipt['sha256'],'Future empty destination requires actual dependency conservation and native AIR proof'),
        'retained-supports-VERIFY-ONLY.json':native_payload(registry,supports,receipt['sha256'],'Exact current retained destination supports')}
    out=home/'staging'/('approved-capsule-geometry-'+str(time.time_ns()));out.mkdir()
    for n,data in outputs.items():(out/n).open('xb').write(data)
    manifest={'format':'awft-approved-capsule-geometry:2','capsule_id':ident,'catalog':reference(home,catalog_path),'checkpoint_id':receipt['id'],'checkpoint_sha256':receipt['sha256'],
        'original_source':row['source_original'],'original_destination':row['destination_original'],'files':{n:reference(home,out/n) for n in outputs},'native_actions':0,'current_native_before_proved':False,'reserve_guard':reserve}
    (out/'manifest.json').write_bytes(canonical(manifest)+b'\n');return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'capsule_id':ident,'objects':row['objects']}


def bind(home,catalog_path,catalog_sha,geometry_manifest,geometry_sha,bridge_jar,review,review_sha,proofs,*,action='inspect',inspection=None,inspection_sha=None):
    home=Path(home).resolve();reserve=guard(MIB,4*MIB)
    if catalog_sha!=SEALED_CATALOG_SHA:raise UserError('Only the compiled exact catalogue, no unreviewed replacement')
    catalog=checked(Path(catalog_path),catalog_sha,2*MIB);gm=checked(Path(geometry_manifest),geometry_sha,MIB)
    legacy=gm.get('format')=='awft-pippin-native-relocation-geometry:1';ident=PIPPIN if legacy else gm['capsule_id'];row=checked_row(catalog,ident)
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json');admit_owner(home,read_json(home/'dashboard/artistic-owner.json'),receipt,receipt['id'],receipt['sha256'])
    if gm['checkpoint_sha256']!=receipt['sha256']:raise UserError('Exact current geometry/checkpoint required')
    approval=checked(Path(review),review_sha,65536)
    if approval.get('format')!='awft-owner-city-plan-review:1' or approval.get('approved') is not True or approval.get('eastern_layout_sha256')!=LAYOUT[1] or 'approved-north-bank-city-rebuild' not in approval.get('allowed_operations',[]):raise UserError('Actual exact city-map approval required')
    active=read_json(home/'packwiz/active.json');installed=read_json(home/'server/installed.json')
    if active['version']!=installed['pack_version'] or active['pack_sha256']!=installed['pack_sha256']:raise UserError('Actual installed candidate/pack differs')
    bridge_jar=Path(bridge_jar);games=list((home/'server/libraries/net/minecraft/server').rglob('*-srg.jar'))
    if len(games)!=1:raise UserError('One actual server game archive required')
    game=games[0]
    with zipfile.ZipFile(bridge_jar) as z:
        import tomllib
        metadata=tomllib.loads(z.read('META-INF/neoforge.mods.toml').decode());bridge=next(r['version'] for r in metadata['mods'] if r['modId']=='awft_control_bridge')
    registry=read_json(home/'dashboard/settlement/registry.json');req={'format':'awft-native-approved-capsule-relocation:2','created':utcnow(),
        'candidate_version':active['version'],'bridge_version':bridge,'pack_sha256':active['pack_sha256'],'capsule_id':ident,
        'native_class_sha256':class_hash(bridge_jar,'worldfortwo.bridge.NativeRelocationSupport'),'ledger_class_sha256':class_hash(bridge_jar,'worldfortwo.bridge.NativeRelocationSupport$Ledger'),
        'catalog_class_sha256':class_hash(bridge_jar,'worldfortwo.bridge.NativeRelocationSupport$Capsules'),'vanilla_clone_class_sha256':class_hash(game,'net.minecraft.server.commands.CloneCommands'),
        'seed':registry['seed'],'world_path':registry['world_path'],'backup_sha256':receipt['sha256'],'current_backup':reference(home,home/'dashboard/settlement/backup-receipt.json'),
        'baseline_capture_backup_sha256':CHECKPOINT_SHA,'catalog':reference(home,catalog_path),'original_source':row['source_original'],'original_destination':row['destination_original'],
        'owner_city_plan_review':reference(home,review),'eastern_layout_sha256':LAYOUT[1],'transaction_id':transaction(home,ident,row['translation_xyz'])}
    folder=Path(geometry_manifest).resolve().parent
    names=('source-after-cover-FUTURE-VERIFY-ONLY.json','destination-after-cover-FUTURE-VERIFY-ONLY.json','destination-retained-supports-VERIFY-ONLY.json') if legacy else ('source-prepared-FUTURE-VERIFY-ONLY.json','destination-empty-FUTURE-VERIFY-ONLY.json','retained-supports-VERIFY-ONLY.json')
    for key,name,count in zip(('source_geometry','destination_geometry','destination_supports'),names,(row['cells'],row['cells'],row['support_cells'])):
        rec=gm['files'][name];checked(folder/name,rec['sha256'],MIB);req[key]=reference(home,folder/name)
        if action!='inspect-moved':
            path,sha=proofs[key];req[{'source_geometry':'source_native_verify','destination_geometry':'destination_native_verify','destination_supports':'supports_native_verify'}[key]]=native_proof(home,path,sha,rec['sha256'],count)
    plan=read_json(home/req['source_geometry']['path']);pins=[]
    for r in plan['block_entities']:
        data=nbtlib.parse_nbt(r['nbt']);kind=str(data['id'])
        if kind not in CLASSES:raise UserError('Unknown native inventory role is held, never assumed empty')
        archive,klass,container=CLASSES[kind];jar=game if archive=='GAME' else home/'server/mods'/archive
        pins.append({'source_position':r['pos'],'BE_id':kind,'class':klass,'class_sha256':class_hash(jar,klass),'Container':container})
    req['BE_class_pins']=pins
    if action=='move':
        inspected=checked(Path(inspection),inspection_sha,MIB)
        if inspected.get('operation')!='inspect' or inspected.get('cleanup_passed') is not True or inspected.get('clone_invoked') is not False or inspected.get('capsule_id')!=ident or inspected.get('status')!='inspected exact current native source/destination; no move':raise UserError('Actual clean exact native capsule inspection required')
        req['native_inspect']=reference(home,inspection)
    elif action not in ('inspect','inspect-moved'):raise UserError('Only inspect/move/inspect-moved')
    data=canonical(req)+b'\n'
    if len(data)>131072:raise UserError('Finite request envelope exceeded')
    sha=hashlib.sha256(data).hexdigest();out=home/'staging'/('relocation-'+sha[:16]+'-R2-SOURCE-'+str(time.time_ns()));out.mkdir();(out/'request.json').write_bytes(data)
    manifest={'format':'awft-approved-relocation-request-source:2','source_sha256':digest(Path(__file__)),'operation':action,'capsule_id':ident,'runtime_bundle_name':'relocation-'+sha[:16],'request_sha256':sha,'native_actions':0,'request_installed':False,'reserve_guard':reserve}
    (out/'manifest.json').write_bytes(canonical(manifest)+b'\n');return {'folder':str(out),**manifest}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);p.add_argument('operation',choices=['catalog','geometry']);p.add_argument('--catalog',type=Path);p.add_argument('--catalog-sha256');p.add_argument('--capsule')
    a=p.parse_args();print(json.dumps(prepare_catalog(a.home) if a.operation=='catalog' else prepare_geometry(a.home,a.catalog,a.catalog_sha256,a.capsule),indent=2))
