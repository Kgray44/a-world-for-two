"""Source staging for one reviewed native Pippin room move.

No runtime request is installed. Preparing geometry is not owner approval.
Binding an inspect/move additionally requires the owner's actual city-map review,
real current native geometry proofs and the actual compiled helper/game classes.
"""
from __future__ import annotations
import argparse,copy,hashlib,json,time,zipfile
from pathlib import Path

from control_room.common import UserError,digest,read_json,utcnow
from tools.artistic_bridge_refinement import flatten
from tools.artistic_captains_hall import native_payload
from tools.artistic_east_tortuga_retrofit import checked
from tools.artistic_eastern_urban_custody import CHECKPOINT_SHA,canonical
from tools.artistic_maritime_depth import admit_owner
from tools.artistic_north_rebuild_custody import decoded_chunk,typed
from tools.artistic_zipline_catenary import reader_budget
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld

MIB=1024**2
MAX_OUTPUT=4*MIB
BASE='staging/eastern-native-move-blueprint-1793206068437799400'
BASE_SHA='ae927974ffa8e200979f98b079bfa4911f3bd78a4cca1664888e958894e3adc7'
LAYOUT_SHA='6f24640d9efefae3340be80d34bcd0e4788f2ded695aefe03d1d6815761a12a4'
SOURCE=(1236,64,-1194);COVER=(1224,64,-1194)
CLASS_MAP={
 'handcrafted:container':('handcrafted-neoforge-1.21.1-4.0.3.jar','earth.terrarium.handcrafted.common.blockentities.ContainerBlockEntity',True),
 'supplementaries:globe':('supplementaries-1.21.1-4.0.2-neoforge.jar','net.mehvahdjukaar.supplementaries.common.block.tiles.GlobeBlockTile',False),
 'supplementaries:item_shelf':('supplementaries-1.21.1-4.0.2-neoforge.jar','net.mehvahdjukaar.supplementaries.common.block.tiles.ItemShelfBlockTile',True),
 'minecraft:smoker':('GAME','net.minecraft.world.level.block.entity.SmokerBlockEntity',True),
 'minecraft:sign':('GAME','net.minecraft.world.level.block.entity.SignBlockEntity',False)}


def reference(home,path):
    path=Path(path).resolve()
    if not path.is_relative_to(home) or path.is_symlink() or not path.is_file():raise UserError('Owned exact regular evidence only')
    return {'path':path.relative_to(home).as_posix(),'sha256':digest(path),'bytes':path.stat().st_size}


def unchanged_saved_capture(home,receipt,registry,source,destination,supports,tag_rows):
    """Reread the current stopped archive; never just rebind old metadata.

    Exact original06 states and typed tags remain the conservation baseline.
    A subsequent change is held, not silently adopted as new expected data.
    Runtime entity/model/slot custody remains a separate native gate.
    """
    import nbtlib
    budget=[reader_budget()];snapshot=None;started=time.monotonic()
    try:
        snapshot=BackupWorld(home,receipt,registry)
        for cx in range(75,79):
            for cz in range(-76,-73):snapshot.chunk(cx,cz)
        wanted={**source,**destination,**supports}
        actual={q:snapshot.state(q) for q in sorted(wanted)}
        differences=[q for q in wanted if actual[q]!=wanted[q]]
        if differences:raise UserError('Current stopped source/destination/support state changed; preserve it instead of rebinding: '+str(differences[:8]))
        expected={tuple(row['pos']):nbtlib.parse_nbt(row['nbt']) for row in tag_rows}
        if len(expected)!=7 or not set(expected)<=set(source):raise UserError('Exact original seven-object tag capture required')
        bes={}
        for cx,cz in sorted({(q[0]//16,q[2]//16) for q in source}):
            raw=snapshot.regions[cx//32,cz//32];doc=decoded_chunk(raw,cx,cz)
            for be in doc.get('block_entities',[]):
                q=tuple(int(be[v]) for v in ('x','y','z'))
                if q in source:
                    if q in bes:raise UserError('Duplicate saved source BE position')
                    bes[q]=be
            del doc;budget.append(reader_budget())
        if set(bes)!=set(expected) or snapshot.protected & (set(destination)|set(supports)):
            raise UserError('Actual current source/destination/support BE membership changed; no overwrite authority')
        tag_hashes=[]
        for q in sorted(expected):
            if typed(expected[q])!=typed(bes[q]):raise UserError('Current full typed native object data changed; preserve actual contents: '+str(q))
            tag_hashes.append({'position':list(q),'full_typed_saved_NBT_sha256':hashlib.sha256(canonical(typed(bes[q]))).hexdigest()})
        if time.monotonic()-started>60:raise UserError('Finite sixty-second current room recapture exceeded')
        return {'format':'awft-current-pippin-saved-recapture:1','checkpoint_id':receipt['id'],'checkpoint_sha256':receipt['sha256'],
            'original_capture_backup_sha256':CHECKPOINT_SHA,'actual_saved_states_compared':len(wanted),'unchanged_states':len(wanted),
            'source_BE_count':len(bes),'seven_full_typed_tags_unchanged':True,'tag_hashes':tag_hashes,
            'saved_FULL_neighbor_chunks':12,'saved_sources':snapshot.sources,'current_native_entity_readiness_proved':False,
            'peak_owned_reader_RSS':max(b['owned_reader_rss_bytes'] for b in budget),'native_actions':0}
    finally:
        if snapshot:snapshot.close()


def geometry(home):
    home=Path(home).resolve();reserve=guard(MIB,MAX_OUTPUT)
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve():raise UserError('Only the separately owned artistic staging home')
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json');admit_owner(home,read_json(home/'dashboard/artistic-owner.json'),receipt,receipt['id'],receipt['sha256'])
    base=checked(home/BASE/'manifest.json',BASE_SHA,MIB)
    docs={}
    for name in ('first-source-full-before-VERIFY-ONLY.json','first-destination-current-before-VERIFY-ONLY.json','first-destination-retained-supports-VERIFY-ONLY.json'):
        row=base['files'][name];docs[name]=checked(home/BASE/name,row['sha256'],MIB)
    source=flatten(docs['first-source-full-before-VERIFY-ONLY.json']);dest=flatten(docs['first-destination-current-before-VERIFY-ONLY.json']);supports=flatten(docs['first-destination-retained-supports-VERIFY-ONLY.json'])
    if len(source)!=320 or len(dest)!=320 or len(supports)!=80 or source[SOURCE]!='regions_unexplored:grass_sprouts' or not dest[COVER].startswith('supplementaries:barnacles['):raise UserError('Exact two ordinary cover targets and complete room required')
    registry=read_json(home/'dashboard/settlement/registry.json');sha=receipt['sha256']
    capture=unchanged_saved_capture(home,receipt,registry,source,dest,supports,docs['first-source-full-before-VERIFY-ONLY.json']['block_entities'])
    after=dict(source);after[SOURCE]='minecraft:air';empty={q:'minecraft:air' for q in dest}
    a=json.loads(native_payload(registry,after,sha,'PROSPECTIVE exact source after separately approved original grass-cover preparation; no move'))
    a['block_entities']=copy.deepcopy(docs['first-source-full-before-VERIFY-ONLY.json']['block_entities'])
    current=json.loads(native_payload(registry,source,sha,'Actual current stopped source; full typed seven-object tags independently reread unchanged'))
    current['block_entities']=copy.deepcopy(a['block_entities'])
    outputs={
        'current-source-full-before-VERIFY-ONLY.json':canonical(current)+b'\n',
        'current-destination-full-before-VERIFY-ONLY.json':native_payload(registry,dest,sha,'Actual current stopped destination including original retained barnacle'),
        'current-saved-recapture-PRIVATE.json':canonical(capture)+b'\n',
        'source-after-cover-FUTURE-VERIFY-ONLY.json':canonical(a)+b'\n',
        'destination-after-cover-FUTURE-VERIFY-ONLY.json':native_payload(registry,empty,sha,'PROSPECTIVE exact destination after separately approved original barnacle-cover preparation; no move'),
        'destination-retained-supports-VERIFY-ONLY.json':native_payload(registry,supports,sha,'Current expected destination retained supports; requires real fresh native proof'),
        'two-original-cover-before-VERIFY-ONLY.json':native_payload(registry,{SOURCE:source[SOURCE],COVER:dest[COVER]},sha,'Expected exact two unchanged original ordinary cover cells; requires actual native before'),
        'two-original-cover-clear-PROPOSAL.json':native_payload(registry,{SOURCE:'minecraft:air',COVER:'minecraft:air'},sha,'SOURCE proposal two exact original ordinary cover cells ONLY; no BE/block-body/clone action'),
    }
    if sum(map(len,outputs.values()))>MAX_OUTPUT:raise UserError('Finite current native-move geometry output exceeded')
    out=home/'staging'/('pippin-native-relocation-geometry-'+str(time.time_ns()));out.mkdir()
    for name,raw in outputs.items():(out/name).open('xb').write(raw)
    manifest={'format':'awft-pippin-native-relocation-geometry:1','source_sha256':digest(Path(__file__)),'checkpoint_id':receipt['id'],'checkpoint_sha256':sha,
        'baseline_capture_backup_sha256':CHECKPOINT_SHA,'base_blueprint_manifest_sha256':BASE_SHA,'eastern_layout_sha256':LAYOUT_SHA,
        'original_source':reference(home,home/BASE/'first-source-full-before-VERIFY-ONLY.json'),
        'original_destination':reference(home,home/BASE/'first-destination-current-before-VERIFY-ONLY.json'),
        'source_BEs_unchanged':7,'cover_preparation_targets':2,'current_saved_archive_reread':True,'current_native_before_proved':False,
        'owner_city_map_review':'NOT supplied; no authority inferred from prepared geometry','native_actions':0,'construction_forbidden':True,'reserve_guard':reserve,
        'files':{p.name:{'bytes':p.stat().st_size,'sha256':digest(p)} for p in out.iterdir()}}
    (out/'manifest.json').write_bytes(canonical(manifest)+b'\n')
    return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'cover_targets':2,'native_actions':0,'owner_review_required':True}


def native_proof(home,path,sha,geometry_sha,count):
    p=Path(path).resolve();r=checked(p,sha,131072)
    if not p.is_relative_to(home/'dashboard/settlement') or p.with_name(p.name+'.complete').read_text().strip()!=sha:
        raise UserError('Exact real marked native terminal required')
    if r.get('operation')!='verify' or r.get('plan_sha256')!=geometry_sha or r.get('blocks')!=count or r.get('failures')!=0 or r.get('cleanup_required') is not False or r.get('temporary_tickets_remaining')!=0 or r.get('pending_shared_chunk_futures')!=0 or 'ticket_cleanup_error'in r or 'error'in r or r.get('status')!='verified actual block identities, orientation, block entities and supplied inventories':
        raise UserError('Exact successful native geometry proof required, no future/stale copied proof')
    return reference(home,p)


def class_hash(jar,classname):
    jar=Path(jar)
    if jar.is_symlink() or not jar.is_file() or not 0<jar.stat().st_size<=64*MIB:raise UserError('Exact finite actual class archive required')
    with zipfile.ZipFile(jar) as z:
        name=classname.replace('.','/')+'.class'
        if sum(v.filename==name for v in z.infolist())!=1:raise UserError('A class archive must contain exactly one actual named class')
        member=z.getinfo(name)
        if not 0<member.file_size<=262144:raise UserError('Finite native class resource required')
        return hashlib.sha256(z.read(member)).hexdigest()


def owner_review(review):
    if review.get('format')!='awft-owner-city-plan-review:1' or review.get('approved') is not True or review.get('eastern_layout_sha256')!=LAYOUT_SHA or 'pippin-native-relocation-prototype' not in review.get('allowed_operations',[]):
        raise UserError('Actual owner city-map review required; this producer cannot manufacture it')
    return review


def admitted_cover_preparation(home,geometry_manifest,geometry_sha,proof,proof_sha,review,review_sha):
    """Explicitly reviewed two-cell DELTA, after real current native before.

    The immutable geometry producer intentionally remains non-executable.
    No existing supplied BE/tag or room geometry is admitted by this function.
    """
    from datetime import datetime,timezone
    home=Path(home).resolve();reserve=guard(MIB,MIB);manifest=checked(Path(geometry_manifest),geometry_sha,MIB)
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json');admit_owner(home,read_json(home/'dashboard/artistic-owner.json'),receipt,receipt['id'],receipt['sha256'])
    if manifest.get('format')!='awft-pippin-native-relocation-geometry:1' or manifest.get('checkpoint_sha256')!=receipt['sha256']:
        raise UserError('Actual current two-cover geometry/checkpoint required')
    owner_review(checked(Path(review),review_sha,65536));folder=Path(geometry_manifest).resolve().parent
    old=manifest['files']['two-original-cover-before-VERIFY-ONLY.json'];before=checked(folder/'two-original-cover-before-VERIFY-ONLY.json',old['sha256'],MIB)
    if flatten(before)!={SOURCE:'regions_unexplored:grass_sprouts',COVER:'supplementaries:barnacles[down=true,east=false,north=false,south=false,up=false,waterlogged=false,west=false]'} or before.get('block_entities') or before.get('commands'):
        raise UserError('Only exact two original ordinary cover targets, without data/commands')
    terminal=native_proof(home,proof,proof_sha,old['sha256'],2);native=read_json(proof)
    at=datetime.fromisoformat(native['finished'].replace('Z','+00:00'));age=(datetime.now(timezone.utc)-at).total_seconds()
    if not 0<=age<=1200:raise UserError('Actual two-cell native-before proof must be fresh')
    registry=read_json(home/'dashboard/settlement/registry.json')
    delta=native_payload(registry,{SOURCE:'minecraft:air',COVER:'minecraft:air'},receipt['sha256'],
        'ADMITTED exact two original ordinary-cover cells ONLY after actual owner review and native-before; no room/BE replay',placement=True)
    out=home/'staging'/('pippin-two-cover-ADMITTED-DELTA-'+str(time.time_ns()));out.mkdir();(out/'two-cover-delta.json').write_bytes(delta)
    record={'format':'awft-pippin-two-cover-admission:1','geometry_manifest_sha256':geometry_sha,'current_backup_sha256':receipt['sha256'],
        'actual_native_before':terminal,'actual_owner_review':reference(home,review),'delta':reference(home,out/'two-cover-delta.json'),
        'cells':2,'BE_writes':0,'native_actions':0,'automatic_operation':False,'reserve_guard':reserve}
    (out/'manifest.json').write_bytes(canonical(record)+b'\n')
    return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'delta_sha256':digest(out/'two-cover-delta.json'),'native_actions':0}


def bind(home,geometry_manifest,geometry_sha,bridge_jar,review,review_sha,proofs,action='inspect',inspection=None,inspection_sha=None):
    home=Path(home).resolve();reserve=guard(MIB,MAX_OUTPUT);manifest=checked(Path(geometry_manifest),geometry_sha,MIB)
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json');admit_owner(home,read_json(home/'dashboard/artistic-owner.json'),receipt,receipt['id'],receipt['sha256'])
    if manifest.get('format')!='awft-pippin-native-relocation-geometry:1' or manifest['checkpoint_sha256']!=receipt['sha256']:raise UserError('Exact current geometry/checkpoint required')
    owner_review(checked(Path(review),review_sha,65536))
    folder=Path(geometry_manifest).resolve().parent;active=read_json(home/'packwiz/active.json');installed=read_json(home/'server/installed.json')
    if active['version']!=installed['pack_version'] or active['pack_sha256']!=installed['pack_sha256']:raise UserError('Actual candidate/pack custody differs')
    bridge_jar=Path(bridge_jar).resolve();native=class_hash(bridge_jar,'worldfortwo.bridge.NativeRelocationSupport')
    ledger_hash=class_hash(bridge_jar,'worldfortwo.bridge.NativeRelocationSupport$Ledger')
    # Exact server API; the client compile signature JAR is deliberately excluded.
    games=list((home/'server/libraries/net/minecraft/server').rglob('*-srg.jar'))
    if len(games)!=1:raise UserError('One exact actual named server-game JAR required')
    game=games[0];clone_sha=class_hash(game,'net.minecraft.server.commands.CloneCommands')
    with zipfile.ZipFile(bridge_jar) as z:
        import tomllib
        metadata=tomllib.loads(z.read('META-INF/neoforge.mods.toml').decode())
        bridge=next(r['version'] for r in metadata['mods'] if r['modId']=='awft_control_bridge')
    registry=read_json(home/'dashboard/settlement/registry.json')
    req={'format':'awft-native-pippin-relocation:1','created':utcnow(),'candidate_version':active['version'],'bridge_version':bridge,
        'pack_sha256':active['pack_sha256'],'native_class_sha256':native,'ledger_class_sha256':ledger_hash,'vanilla_clone_class_sha256':clone_sha,
        'seed':registry['seed'],'world_path':registry['world_path'],'backup_sha256':receipt['sha256'],'baseline_capture_backup_sha256':CHECKPOINT_SHA,
        'current_backup':reference(home,home/'dashboard/settlement/backup-receipt.json'),'original_source':manifest['original_source'],'original_destination':manifest['original_destination'],
        'owner_city_plan_review':reference(home,review),'eastern_layout_sha256':LAYOUT_SHA,
        'transaction_id':hashlib.sha256((str(home).replace('\\','/')+'|'+CHECKPOINT_SHA+'|PIPPIN320|-13,0,0').encode()).hexdigest()}
    # Java Path.toRealPath().toString() uses the native Windows separator.
    req['transaction_id']=hashlib.sha256((str(home)+'|'+CHECKPOINT_SHA+'|PIPPIN320|-13,0,0').encode()).hexdigest()
    geom_keys=(('source_geometry','source-after-cover-FUTURE-VERIFY-ONLY.json',320),('destination_geometry','destination-after-cover-FUTURE-VERIFY-ONLY.json',320),('destination_supports','destination-retained-supports-VERIFY-ONLY.json',80))
    for key,name,count in geom_keys:
        record=manifest['files'][name];checked(folder/name,record['sha256'],MIB);req[key]=reference(home,folder/name)
        if action!='inspect-moved':
            p,sha=proofs[key];proofkey={'source_geometry':'source_native_verify','destination_geometry':'destination_native_verify','destination_supports':'supports_native_verify'}[key]
            req[proofkey]=native_proof(home,p,sha,record['sha256'],count)
    import nbtlib
    source=read_json(folder/'source-after-cover-FUTURE-VERIFY-ONLY.json');pins=[]
    for row in source['block_entities']:
        data=nbtlib.parse_nbt(row['nbt']);ident=str(data['id']);archive,klass,container=CLASS_MAP[ident];jar=game if archive=='GAME' else home/'server/mods'/archive
        pins.append({'source_position':row['pos'],'BE_id':ident,'class':klass,'class_sha256':class_hash(jar,klass),'Container':container})
    req['BE_class_pins']=pins
    if action=='move':
        inspect=checked(Path(inspection),inspection_sha,MIB)
        if inspect.get('operation')!='inspect' or inspect.get('status')!='inspected exact current native source/destination; no move' or inspect.get('cleanup_passed') is not True or inspect.get('clone_invoked') is not False:
            raise UserError('Real fresh clean seven-object native inspect required before move')
        req['native_inspect']=reference(home,inspection)
    elif action not in ('inspect','inspect-moved'):raise UserError('Only inspect, separately bound move, and read-only post-move inspection')
    raw=canonical(req)+b'\n'
    if len(raw)>131072:raise UserError('Finite native request envelope exceeded')
    sha=hashlib.sha256(raw).hexdigest();out=home/'staging'/('relocation-'+sha[:16]+'-SOURCE-'+str(time.time_ns()));out.mkdir();(out/'request.json').write_bytes(raw)
    result={'source_sha256':digest(Path(__file__)),'request_sha256':sha,'runtime_bundle_name':'relocation-'+sha[:16],
        'operation':action,'native_actions':0,'runtime_request_installed':False,'automatic_operation':False,'reserve_guard':reserve}
    (out/'manifest.json').write_bytes(canonical(result)+b'\n')
    return {'folder':str(out),**result}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--home',type=Path,required=True);parser.add_argument('operation',choices=['geometry'])
    args=parser.parse_args();print(json.dumps(geometry(args.home),indent=2))
