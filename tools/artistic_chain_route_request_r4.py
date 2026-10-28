"""Saved-custody studies and gated R4 prepare-create requests.

No runtime calls, stock creation, entities, copied entity NBT or automatic retry.
Unknown FULL chunks, absent real proofs or missing installed helper refuse.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path
import re
import uuid
import zipfile
import zlib

from control_room.common import UserError,digest,utcnow
from tools.artistic_bridge_refinement import flatten
from tools.artistic_quay_prototype import bounded,context,write_bundle
from tools.artistic_engineering import checked_native_proof,native_proof_times
from tools.artistic_maritime_depth import admit_owner
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld,NBTReader,MAX_CHUNK,base

MIB=1024**2
NODES=((1160,168,-760),(1168,159,-784),(1144,152,-840),(1128,150,-848),(1120,147,-864),
       (1120,146,-880),(1112,142,-920),(1088,132,-968),(1064,125,-1008),(1048,116,-1064),
       (1056,108,-1112),(1048,100,-1176),(1048,91,-1232),(1064,86,-1248),(1100,72,-1256))
STOCK=(1101,65,-1257)
ROUTE='rosewater-cliff-west-town-v2'
CLASS='worldfortwo/bridge/NativeChainRouteSupport.class'
CHAINS='connectiblechains-2.4.4+1.21.1-neoforge.jar'
CHAINS_SHA='70d9f048e6f358c83b2d35f8a69000ec7827023efcc6d3b75346b4e34238bbd0'
READY_POLICY={'mode':'CURRENT_PERSISTED_FULL_BEFORE_ANY_TICKET','io_concurrency':4,'max_nbt_heap_bytes':4*MIB,
              'max_total_nbt_heap_bytes':256*MIB,'max_read_columns':4096,'max_halo_radius':16,'light_neighbor_halo':1,
              'max_total_ticks':1800,'max_total_wall_seconds':90,'max_read_wall_seconds':45}


def endpoint_chunks():
    centers={(x//16,z//16)for x,y,z in (*NODES,STOCK)}
    if len(centers)>16:raise UserError('Finite actual endpoint set exceeded')
    cells={(x+dx,z+dz)for x,z in centers for dx in range(-2,3)for dz in range(-2,3)}
    if len(cells)>400:raise UserError('Finite five-by-five endpoint neighborhood exceeded')
    return centers,cells


def chunk_document(raw,cx,cz):
    if len(raw)<8192:raise UserError('Nonempty region has a truncated header')
    i=((cz&31)*32+(cx&31))*4;loc=int.from_bytes(raw[i:i+4],'big');sector,count=loc>>8,loc&255
    if not sector:raise UserError('No SAVED chunk at this actual endpoint-neighborhood position')
    if sector<2 or not count or(sector+count)*4096>len(raw):raise UserError('Invalid saved region sector')
    off=sector*4096;length=int.from_bytes(raw[off:off+4],'big')
    if not 1<length<=count*4096-4:raise UserError('Invalid saved chunk length')
    mode,packed=raw[off+4],raw[off+5:off+4+length]
    if mode==3:decoded=packed
    elif mode in(1,2):
        d=zlib.decompressobj(31 if mode==1 else 15);decoded=d.decompress(packed,MAX_CHUNK+1)
        if d.unconsumed_tail or not d.eof:raise UserError('Saved chunk compression is unbounded/truncated')
    else:raise UserError('Unsupported/external saved chunk compression')
    if len(decoded)>MAX_CHUNK:raise UserError('Saved chunk exceeds its finite NBT bound')
    return NBTReader(decoded).read(),hashlib.sha256(decoded).hexdigest()


def study(home,output):
    reserve=guard(4*MIB,8*MIB);home,output,current,registry=context(home,output)
    if not 0<(home/'backups'/(current['id']+'.zip')).stat().st_size<=512*MIB:raise UserError('Finite actual stopped archive required')
    snapshot=BackupWorld(home,current,registry);centers,required=endpoint_chunks();rows=[];unknown=[];regions={};raw_total=0
    knots=[];entity_sources=[];ids=set()
    try:
        for cx,cz in sorted(required):
            rx,rz=cx//32,cz//32;name=snapshot.prefix+f'r.{rx}.{rz}.mca';record=snapshot.files.get(name)
            try:
                if not record or not 8192<=record['size']<=64*MIB:raise UserError('No finite saved source region')
                if name not in regions:
                    raw=snapshot.archive.read(name);raw_total+=len(raw)
                    if raw_total>128*MIB or len(raw)!=record['size']or hashlib.sha256(raw).hexdigest()!=record['sha256']:raise UserError('Saved region size/hash/allocation differs')
                    regions[name]=raw
                doc,sha=chunk_document(regions[name],cx,cz)
                if(doc.get('xPos'),doc.get('zPos'))!=(cx,cz)or doc.get('Status')not in('full','minecraft:full'):raise UserError('Actual SAVED chunk is not FULL at its expected coordinates')
                rows.append({'chunk':[cx,cz],'status':doc['Status'],'source_member':name,'region_sha256':record['sha256'],'chunk_nbt_sha256':sha})
            except UserError as error:unknown.append({'chunk':[cx,cz],'reason':str(error)})
        prefix=Path(registry['world_path']).resolve().relative_to(home).as_posix()+'/entities/'
        records=[r for r in snapshot.files.values()if r['path'].startswith(prefix)and r['path'].endswith('.mca')]
        if len(records)>16 or sum(r['size']for r in records)>32*MIB:raise UserError('Complete stopped chain census exceeds finite entity-region bound')
        for r in sorted(records,key=lambda r:r['path']):
            raw=snapshot.archive.read(r['path'])
            if len(raw)!=r['size']or hashlib.sha256(raw).hexdigest()!=r['sha256']:raise UserError('Entity region bytes differ from the authenticated checkpoint')
            entity_sources.append({'path':r['path'],'bytes':len(raw),'sha256':r['sha256']})
            if not raw:continue
            if len(raw)<8192:raise UserError('Truncated nonempty saved entity region')
            match=re.fullmatch(r'r\.(-?\d+)\.(-?\d+)\.mca',Path(r['path']).name)
            if not match:raise UserError('Unexpected entity region naming')
            rx,rz=map(int,match.groups())
            for slot in range(1024):
                if not int.from_bytes(raw[slot*4:slot*4+4],'big'):continue
                doc,_=chunk_document(raw,rx*32+(slot%32),rz*32+(slot//32))
                for entity in doc.get('Entities',[]):
                    if entity.get('id')!='connectiblechains:chain_knot':continue
                    numbers=entity.get('UUID',[]);pos=entity.get('Pos',[])
                    if len(numbers)!=4 or len(pos)!=3 or not all(type(v)in(int,float)and math.isfinite(v)for v in pos):raise UserError('Unknown saved chain-knot identity/position')
                    ident=str(uuid.UUID(bytes=b''.join((v&0xffffffff).to_bytes(4,'big')for v in numbers)))
                    if ident in ids:raise UserError('Duplicate saved chain-knot UUID')
                    ids.add(ident);knots.append({'uuid':ident,'block':[math.floor(v)for v in pos],'entity_id':entity['id']})
                    if len(knots)>4096:raise UserError('Finite stopped chain-knot census exceeded')
        level_sources=snapshot.sources.copy()
    finally:snapshot.close()
    docs={'saved-endpoint-chunks.json':{'format':'awft-stopped-zipline-endpoint-chunks:1','created':utcnow(),'seed':registry['seed'],'world_path':registry['world_path'],
          'checkpoint_id':current['id'],'checkpoint_sha256':current['sha256'],'required_count':len(required),'all_required_saved_FULL':not unknown and len(rows)==len(required),
          'chunks':rows,'unknown':unknown,'actual_live_loaded_readiness':False,'source_sha256':digest(Path(__file__))},
          'chain-knot-census.json':{'format':'awft-stopped-chain-knot-census:1','created':utcnow(),'checkpoint_id':current['id'],'checkpoint_sha256':current['sha256'],
          'world_path':registry['world_path'],'all_entity_regions_scanned':True,'knots':knots,'entity_region_sources':entity_sources,'source_sha256':digest(Path(__file__))}}
    if bounded(home/'dashboard/settlement/backup-receipt.json').get('sha256')!=current['sha256']:raise UserError('Checkpoint advanced during immutable saved custody scan')
    return write_bundle(output,docs,{'format':'awft-chain-route-stopped-inputs:1','created':utcnow(),'source_sha256':digest(Path(__file__)),
        'checkpoint_id':current['id'],'checkpoint_sha256':current['sha256'],'source_identity':level_sources,'endpoint_chunks':len(centers),'required_saved_neighborhood_chunks':len(required),
        'actual_saved_FULL':len(rows),'unknown_saved_chunks':len(unknown),'saved_chain_knots':len(knots),'world_writes':0,'native_actions':0,'storage_guard':reserve,
        'gate':'UNKNOWN saved chunks refuse requests; actual native5x5 already-loaded readiness remains independent. No loading/generation action or successful ride is claimed.'})


def clean_geometry_receipt(home,ref,plan_ref,count,fresh):
    path=home/ref['path'];proof,marker=checked_native_proof(path,plan_ref['sha256'],count,maximum_age=1800 if fresh else None)
    if path.stat().st_size!=ref['bytes']or digest(path)!=ref['sha256']or proof.get('cleanup_required')is not False or proof.get('temporary_tickets_remaining')!=0 or proof.get('pending_shared_chunk_futures')!=0 or proof.get('ticket_cleanup_error'):
        raise UserError('Actual clean geometry receipt bytes/native schema required')
    return proof


def prepare(home,study_folder,study_sha,physical_frame,geometry_sets,output,operation='create',route_path=None,creation_receipt=None):
    reserve=guard(4*MIB,8*MIB);home,output,current,registry=context(home,output)
    study_folder,physical_frame,geometry_sets=map(lambda p:Path(p).resolve(),(study_folder,physical_frame,geometry_sets))
    if study_folder.parent!=home/'staging'or not physical_frame.is_relative_to(home/'staging')or not geometry_sets.is_relative_to(home/'staging'):raise UserError('Private bounded source geometry/custody only')
    sm=bounded(study_folder/'manifest.json')
    if digest(study_folder/'manifest.json')!=study_sha or sm['checkpoint_sha256']!=current['sha256']:raise UserError('Exact current stopped saved input study required')
    saved=bounded(study_folder/'saved-endpoint-chunks.json');census=bounded(study_folder/'chain-knot-census.json')
    for name,doc in(('saved-endpoint-chunks.json',saved),('chain-knot-census.json',census)):
        if digest(study_folder/name)!=sm['files'][name]['sha256']:raise UserError('Stopped source evidence bytes changed')
    if saved.get('all_required_saved_FULL')is not True or saved.get('unknown')or len(saved['chunks'])!=len(endpoint_chunks()[1]):raise UserError('UNKNOWN saved endpoint5x5 chunks; preserve the study and do not fabricate readiness')
    physical=bounded(physical_frame,2*MIB)
    if physical.get('nodes')!=[list(q)for q in NODES]or physical.get('hang_offset')!=3.5 or physical.get('slack')!=16 or physical.get('all_saved_AIR_clear')is not True or physical.get('physical_frames_clear')is not True or physical.get('native_ride_acceptance')is not False:
        raise UserError('Exact reviewed west-v2 terrain/body/frame source required; source is not native ride acceptance')
    sets=bounded(geometry_sets,2*MIB)
    if not isinstance(sets,list)or not 1<=len(sets)<=18:raise UserError('Actual paired BEFORE/FULL geometry-set references required')
    critical={};baseline=None;stock_air=False
    def read_ref(r):
        if set(r)!={'path','bytes','sha256'}:raise UserError('Exact immutable reference fields required')
        p=home/r['path'];p=p.resolve()
        if not p.is_relative_to(home)or p.is_symlink()or p.stat().st_size!=r['bytes']or digest(p)!=r['sha256']:raise UserError('Owned regular referenced bytes differ')
        return bounded(p,2*MIB)
    for item in sets:
        if set(item)!={'before','native_before','full','native_full'}:raise UserError('Exact four paired geometry references required')
        a,b=read_ref(item['before']),read_ref(item['full']);aa,bb=flatten(a),flatten(b)
        if set(aa)!=set(bb):raise UserError('Paired BEFORE/FULL must cover the same exact addressed field')
        for doc in(a,b):
            if doc.get('seed')!=registry['seed']or doc.get('world_path')!=registry['world_path']or doc.get('commands')!=[]:raise UserError('Actual same-world bounded geometry only')
        if baseline is None:baseline=a['backup_sha256']
        if a['backup_sha256']!=baseline or b['backup_sha256']!=current['sha256']:raise UserError('Original BEFORE baseline and current FULL checkpoints must stay distinct and exact')
        pa=clean_geometry_receipt(home,item['native_before'],item['before'],len(aa),False);pb=clean_geometry_receipt(home,item['native_full'],item['full'],len(bb),operation in('create','prepare-create'))
        if native_proof_times(pa)[1]>native_proof_times(pb)[0]:raise UserError('FULL verification predates completion of original BEFORE')
        for q,v in bb.items():
            if q in critical and critical[q]!=v:raise UserError('Conflicting FULL geometry expectations')
            critical[q]=v
        if STOCK in bb:
            if aa[STOCK]!='minecraft:air'or base(bb[STOCK])!='minecraft:barrel':raise UserError('Genuine original AIR then actual BARREL required at new stock')
            stock_air=True
    if not stock_air or not set(NODES)<=set(critical):raise UserError('Native geometry must cover original stockAIR and every exact real anchor')
    if physical.get('checkpoint_sha256')!=baseline:raise UserError('Rebind/requalify the actual physical source to its genuine original BEFORE baseline, never invent a substitute')
    if operation in('create','prepare-create'):
        route={'format':'awft-owned-native-chain-route:1','route_id':ROUTE,'seed':registry['seed'],'world_path':registry['world_path'],'dimension':'minecraft:overworld',
               'checkpoint_sha256':baseline,'slack':16,'hang_offset_required':3.5,'copied_entity_NBT':False,'idle_forced_chunks':0,'native_ride_acceptance':False,
               'nodes':[{'block':list(q),'face':'north','anchor_state':critical[q]}for q in NODES],'links':[[i,i+1]for i in range(14)],
               'stock':list(STOCK),'stock_state':critical[STOCK],'stock_slot':0,'chain_cost':14}
    else:
        if route_path is None or creation_receipt is None:raise UserError('A real immutable original route and clean CREATE receipt are required; no adoption/replay')
        route=bounded(Path(route_path),2*MIB)
        if route.get('route_id')!=ROUTE or route.get('nodes')!=[{'block':list(q),'face':'north','anchor_state':critical[q]}for q in NODES]or route.get('stock')!=list(STOCK):raise UserError('Original exact route identity differs')
    active=bounded(home/'packwiz/active.json');installed=bounded(home/'server/installed.json',2*MIB)
    if active['version']!=installed['pack_version']or active['pack_sha256']!=installed['pack_sha256']:raise UserError('Actual installed candidate pack custody differs')
    chains_cfg=bounded(home/'server/config/connectiblechains.json');zip_cfg=bounded(home/'server/config/zipline.json')
    if chains_cfg.get('maxChainRange')!=96 or chains_cfg.get('collisionsEnabled')is not True or chains_cfg.get('hangingBlockCollisions')is not True:
        raise UserError('Actual native chain96-range/collision configuration differs')
    if zip_cfg.get('hangOffset')!=3.5 or zip_cfg.get('speedMultiplier')!=1 or zip_cfg.get('realisticPhysics')is not False or zip_cfg.get('maxTurnAngle')!=.707:
        raise UserError('Actual reviewed3.5-hang/rider configuration differs')
    def ref(p):
        p=Path(p).resolve()
        if not p.is_relative_to(home)or p.is_symlink():raise UserError('Owned regular evidence only')
        return {'path':p.relative_to(home).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)}
    # Output is a preparation directory, not a native command bundle. The
    # request writer must be run after the actual installed46 helper exists.
    jars=list((home/'server/mods').glob('awft-control-bridge-*.jar'))
    if len(jars)!=1:raise UserError('Exactly one actual installed bridge archive required')
    jar=jars[0];bridge=jar.name.removeprefix('awft-control-bridge-').removesuffix('.jar')
    if not re.fullmatch(r'\d+\.\d+\.\d+',bridge)or jar.stat().st_size>16*MIB:raise UserError('Actual bridge archive/version required')
    with zipfile.ZipFile(jar)as z:
        if CLASS not in z.namelist():raise UserError('Installed helper has no native chain controller yet')
        code=z.read(CLASS)
        if not 0<len(code)<=256*1024:raise UserError('Bounded actual native chain class required')
        if any(token not in code for token in (b'rosewater-cliff-west-town-v2',b'saved_endpoint_chunks',b'RECEIPT_BLOCKED',b'prepare-create',b'CURRENT_PERSISTED_FULL_BEFORE_ANY_TICKET')):raise UserError('Installed class is not the reviewed R4 west-v2 READY protocol; do not send new operations to an older controller')
    for name,sha in((CHAINS,CHAINS_SHA),(jar.name,digest(jar))):
        if installed['files'].get(name)!=sha or digest(home/'server/mods'/name)!=sha:raise UserError('Pinned installed native dependency/bridge bytes differ')
    request={'format':'awft-native-chain-route:2'if operation=='prepare-create'else'awft-native-chain-route:1','allowed_operation':operation,'candidate_version':active['version'],'bridge_version':bridge,
             'pack_sha256':active['pack_sha256'],'native_class_sha256':hashlib.sha256(code).hexdigest(),'checkpoint_id':current['id'],'checkpoint_sha256':current['sha256'],
             'bridge_jar_sha256':digest(jar),'zipline_jar_sha256':digest(home/'server/mods/zipline-1.5.3+1.21.1-neoforge.jar'),
             'chains_config':ref(home/'server/config/connectiblechains.json'),'zipline_config':ref(home/'server/config/zipline.json'),
             'physical_frame_source':ref(physical_frame),'geometry_sets':sets,'chain_census':ref(study_folder/'chain-knot-census.json'),
             'saved_endpoint_chunks':ref(study_folder/'saved-endpoint-chunks.json')}
    if operation=='prepare-create':request['ready_policy']=READY_POLICY.copy()
    # Stage a route first so the exact immutable byte reference can be included.
    raw=(json.dumps(route,separators=(',',':'))+'\n').encode()if operation in('create','prepare-create')else Path(route_path).read_bytes()
    if operation not in('create','prepare-create'):
        cr=Path(creation_receipt).resolve();d=bounded(cr,2*MIB);marker=cr.with_name(cr.name+'.complete')
        if not cr.is_relative_to(home/'dashboard/settlement')or not marker.is_file()or marker.read_text().strip()!=digest(cr):raise UserError('Real immutable CREATE terminal marker required')
        if(d.get('operation')not in('create','prepare-create')or d.get('route_sha256')!=hashlib.sha256(raw).hexdigest()or d.get('failures')!=0 or d.get('error')
           or d.get('cleanup_passed')is not True or d.get('cleanup_required')is not False or d.get('temporary_tickets_remaining')!=0
           or d.get('pending_shared_chunk_futures')!=0 or d.get('native_added')!=15 or d.get('native_attached')!=14 or d.get('chain_debits')!=14):
            raise UserError('Only actual completed creation/cleanup may authorize inspect/restart; a partial ledger is not acceptance')
    if output.exists():raise UserError('Preserve existing prepared route/request; no unchanged automatic retry')
    output.mkdir();(output/'route.json').write_bytes(raw);request['route']=ref(output/'route.json')
    if operation not in('create','prepare-create'):request['creation_receipt']=ref(Path(creation_receipt))
    encoded=(json.dumps(request,separators=(',',':'))+'\n').encode();sha=hashlib.sha256(encoded).hexdigest();bundle=home/'dashboard/settlement'/('chains-'+sha[:16])
    if bundle.exists():raise UserError('Existing immutable chain request refuses automatic replay')
    bundle.mkdir();(bundle/'request.json').write_bytes(encoded)
    receipt={'format':'awft-chain-request-owner:1','created':utcnow(),'source_sha256':digest(Path(__file__)),'request_sha256':sha,'route_sha256':digest(output/'route.json'),
             'native_actions':0,'world_writes':0,'storage_guard':reserve,'actual_native_5x5_loaded_or_ride_acceptance':False}
    if operation=='prepare-create':receipt.update(current_persisted_halo_preflight_or_loading_acceptance=False,ready_policy=READY_POLICY)
    (output/'ownership.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')
    return {'prepared':str(output),'request':str(bundle/'request.json'),'request_sha256':sha,'typed_console_command':'awftchains '+operation+' '+bundle.name+' '+sha,'native_actions':0}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='action',required=True)
    a=s.add_parser('study')
    for k in('home','output'):a.add_argument('--'+k,type=Path,required=True)
    b=s.add_parser('prepare')
    for k in('home','study-folder','physical-frame','geometry-sets','output'):b.add_argument('--'+k,type=Path,required=True)
    b.add_argument('--study-sha',required=True);b.add_argument('--operation',choices=('create','prepare-create','inspect','verify-restart'),default='create')
    b.add_argument('--route-path',type=Path);b.add_argument('--creation-receipt',type=Path)
    a=p.parse_args();result=study(a.home,a.output)if a.action=='study'else prepare(a.home,a.study_folder,a.study_sha,a.physical_frame,a.geometry_sets,a.output,a.operation,a.route_path,a.creation_receipt)
    print(json.dumps(result,indent=2))
