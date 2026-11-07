"""Root-delegated event-bounded eastern city execution, existing native tools only.

No operation runs on import. Every send has an immutable local intent; failed or
ambiguous sends are never retried automatically. First human arrival stops work.
"""
from __future__ import annotations
import argparse,copy,hashlib,json,os,re,time
from datetime import datetime,timezone,timedelta
from pathlib import Path
import psutil
import nbtlib
from control_room.common import UserError,digest,read_json,utcnow
from tools.artistic_review import request,native,construction_header
from tools.artistic_east_tortuga_retrofit import checked
from tools.artistic_eastern_urban_custody import canonical
from tools.native_relocation_request import reference
from tools.settlement_live import native_read
from tools.playtest import guard
from tools import native_eastern_relocation_r7 as producer
from tools.artistic_bridge_refinement import flatten
from tools.artistic_captains_hall import native_payload
from tools.native_eastern_relocation import transaction
from tools.settlement_attractions import properties

MIB=1024**2
PACKET='staging/eastern98-ordinary-pipeline-1793227155056271700/manifest.json'
PACKET_SHA='f7ce3f69236dcac1b984ad44d9a0e945c8f1aeee59804a187482c697814779c3'
LEASE='dashboard/settlement/exclusive-east-city58-real-execution.json'
LEASE_SHA='1d208c65422fdc3915f80152b648468796502e5de3a23c737c173923ff017e15'
PIPPIN='eastern22/pippins-net:room:0'
REVIEW='dashboard/settlement/city-map-owner-approval-1793210090127655900.json'
REVIEW_SHA='6a3101f6dbddf260e196a21554d93627dd44ca46963737f5e25af2fb09e259b2'
ARCH='staging/eastern39-architecture-source-index-1793227833374305600/architecture39-SOURCE-INDEX.json'
ARCH_SHA='3d8ac94dbb62c64154290e71584d5d0627667705f1852dd5188c48865344fb08'
BACKINGS='staging/eastern-approved-outside-backings-1793230541394652600/backing-protocol-SOURCE-ONLY.json'
BACKINGS_SHA='2d781c7221e57e5907aa2c33b0824d53b3c58066a7a06b03c7e32137c1b76d89'

def immutable(path,value):
    raw=canonical(value)+b'\n'
    with Path(path).open('xb')as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())

class RoomHold(UserError):pass

def clean_relocation_result(action,r):
    historical_audit=(action=='inspect-quarantined'and r.get('operation')==action
        and r.get('status')=='read-only actual quarantined-room audit; original failure retained; no clone/retry/completion'
        and r.get('clone_invoked')is False and r.get('intent_written')is False)
    return(not r.get('failed')and(not r.get('quarantine')or historical_audit)and r.get('cleanup_passed')is True
        and r.get('owned_chunk_tickets')==0 and r.get('pending_owned_futures')==0 and r.get('pending_shared_chunk_futures')==0
        and not r.get('ticket_cleanup_error')and not r.get('lease_cleanup_error'))

def exact_native_contents_payload(registry,backup,states,contents):
    """VERIFY-only whole native snapshots; SNBT preserves every tag's type."""
    if not contents or set(states)!=set(contents):raise UserError('Exact nonempty native object/state set required')
    result=json.loads(native_payload(registry,states,backup,'VERIFY ONLY exact complete native ledger tags/classes; no inventory writes'))
    result.update(verification_only=True,construction_forbidden=True,exact_native_tags=True)
    rows=[]
    for q,(klass,tag)in sorted(contents.items()):
        if not isinstance(klass,str)or len(klass)>256 or not re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]*(?:\.[A-Za-z_$][A-Za-z0-9_$]*)+',klass):raise UserError('Exact captured native Java class required')
        if not isinstance(tag,nbtlib.Compound)or any(k not in tag for k in('x','y','z'))or tuple(int(tag[k])for k in('x','y','z'))!=q:raise UserError('Entire captured native tag must retain its real current coordinates')
        rows.append({'pos':list(q),'native_class':klass,'nbt':tag.snbt()})
    result['block_entities']=rows
    return result

def require_exact_native_tag_receipt(result,expected_rows):
    # An older helper ignores unfamiliar fields and may report Items-only pass.
    # Only the new native receipt can attest this full-class/full-tag comparison.
    if result.get('exact_native_tags')is not True or type(result.get('exact_native_tag_rows'))is not int or result['exact_native_tag_rows']!=expected_rows:
        raise UserError('Actual exact native class/full-tag verification acknowledgement missing; legacy Items-only success is not sufficient')

class City:
    def __init__(self,home,lease=LEASE,lease_sha=LEASE_SHA):
        self.home=Path(home).resolve();self.lease_path=self.home/lease;self.lease_sha=lease_sha;self.lease=checked(self.lease_path,lease_sha,65536)
        if not self.lease_path.resolve().is_relative_to(self.home/'dashboard/settlement'):raise UserError('Root private local lease path only')
        if self.lease.get('format')!='awft-exclusive-world-write-lease:2'or self.lease.get('worker')!='/root/grand_harbor_ships'or Path(self.lease['home']).resolve()!=self.home:raise UserError('Exact Root event lease required')
        self.folder=self.home/'staging'/('east-city58-execution-'+str(time.time_ns()));guard(8*MIB,256*MIB);self.folder.mkdir()
        immutable(self.folder/'lease-custody.json',{'lease':reference(self.home,self.lease_path),'runner_sha256':digest(Path(__file__)),'started':utcnow(),'native_actions':0})
        m=checked(self.home/PACKET,PACKET_SHA,2*MIB);self.pipeline=checked((self.home/PACKET).parent/'pipeline-SOURCE-ONLY.json',m['pipeline_sha256'],16*MIB)
        self.rows={r['capsule_id']:r for r in self.pipeline['room_assessments']};self.counter=0;self.results=[]
        self.catalog=checked(self.home/producer.CATALOG,producer.CATALOG_SHA,2*MIB);self.capsules={r['id']:r for r in self.catalog['capsules']}
        backing=checked(self.home/BACKINGS,BACKINGS_SHA,2*MIB)
        if backing.get('format')!='awft-approved-eastern-outside-capsule-backing-source:1'or backing.get('catalog_sha256')!=producer.CATALOG_SHA or backing.get('architecture_index_sha256')!=ARCH_SHA:raise UserError('Exact final approved backing/capsule structures required')
        self.backings={r['capsule_id']:r for r in backing['records']};self.backing_order=backing['topological_with_backing_custody']
        self.backing_cycle_holds=backing['additional_dependency_cycle_holds']
        if len(self.backing_order)+len(self.backing_cycle_holds)!=len(self.capsules)or(set(self.backing_order)|set(self.backing_cycle_holds))!=set(self.capsules):raise UserError('Complete explicit backing custody order/holds required')
        self.registry=read_json(self.home/'dashboard/settlement/registry.json');self.backup=read_json(self.home/'dashboard/settlement/backup-receipt.json')['sha256']
        self.authored={};self.building_results=[];self.virtual=None
        self.bridge=self.home/f"server/mods/awft-control-bridge-{self.lease['bridge']}.jar"
        self.guard()

    def guard(self):
        if digest(self.lease_path)!=self.lease_sha or self.lease_path.with_name(self.lease_path.stem+'.RELEASED.json').exists()or(self.home/'dashboard/settlement/east-city58-STOP').exists():raise UserError('Root lease changed/stopped/released')
        p=psutil.Process(self.lease['pid'])
        if abs(p.create_time()-self.lease['birth'])>.001 or not p.name().lower().startswith('java'):raise UserError('Exact native server process changed')
        if digest(self.bridge)!=self.lease['bridge_sha256']:raise UserError('Installed bridge changed')
        active=read_json(self.home/'packwiz/active.json');installed=read_json(self.home/'server/installed.json')
        if active['version']!=self.lease['candidate']or installed['pack_version']!=active['version']or installed['pack_sha256']!=active['pack_sha256']:raise UserError('Actual installed pack changed')
        metrics=request(self.home,'metrics');overview=request(self.home,'overview')['server']
        if overview.get('state')!='online'or overview.get('pid')!=self.lease['pid']or metrics.get('players')!={}or metrics.get('players_available')is not True or metrics.get('bridge_age_seconds',999)>15:raise UserError('First human arrival, unavailable roster or stale runtime; stop and release')
        return metrics

    def step(self,label,op,plan,*,allow_read_mismatch=False):
        self.guard();self.counter+=1;guard(MIB,256*MIB)
        if op in('place','settle'):self.protect(flatten(read_json(plan)))
        label=re.sub('[^a-zA-Z0-9_-]','_',label)[:100];prefix=self.folder/f'{self.counter:04d}-{label}'
        intent=prefix.with_suffix('.intent.json');immutable(intent,{'operation':op,'plan':reference(self.home,Path(plan)),'at':utcnow(),'sent_once_only':True})
        before=set((self.home/'dashboard/settlement').glob('settlement-result-*.json.complete'))
        try:
            result=native(self.home,'awftbuild '+op+' '+digest(plan),plan_path=plan,timeout=300)
            immutable(prefix.with_suffix('.result.json'),result);self.guard();return result
        except BaseException as e:
            if op=='verify'and allow_read_mismatch:
                for marker in set((self.home/'dashboard/settlement').glob('settlement-result-*.json.complete'))-before:
                    p=marker.with_suffix('');r=native_read(p,{})
                    if(r.get('operation')=='verify'and r.get('plan_sha256')==digest(plan)and r.get('failures',0)>0
                            and not r.get('error')and r.get('cleanup_required')is False and r.get('temporary_tickets_remaining')==0
                            and r.get('pending_shared_chunk_futures')==0 and digest(p)==marker.read_text().strip()):
                        immutable(prefix.with_suffix('.read-only-mismatch.json'),r);self.guard();return r
            immutable(prefix.with_suffix('.FAILED.json'),{'error':str(e),'at':utcnow(),'retry_forbidden':True});raise

    def terminal(self,result,family):
        folder=self.home/'dashboard/settlement'
        for p in folder.glob(family+'-result-*.json'):
            if p.stat().st_size>8*MIB:continue
            r=native_read(p,{})
            if r.get('finished')==result.get('finished')and r.get('operation')==result.get('operation')and r.get('plan_sha256')==result.get('plan_sha256'):
                sha=digest(p)
                if p.with_name(p.name+'.complete').read_text().strip()==sha:return p,sha
        raise UserError('Exact marked immutable native terminal not located')

    def relocate(self,label,action,bound):
        self.guard();path=Path(bound['folder'])/'request.json';raw=path.read_bytes();sha=hashlib.sha256(raw).hexdigest()
        if sha!=bound['request_sha256']:raise UserError('Sealed request changed')
        req=json.loads(raw)
        for name in('source_geometry','destination_geometry','destination_supports'):
            r=req[name];self.protect(flatten(checked(self.home/r['path'],r['sha256'],MIB)))
        folder=self.home/'dashboard/settlement'/('relocation-'+sha[:16]);folder.mkdir(exist_ok=False)
        with(folder/'request.json').open('xb')as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        self.counter+=1;prefix=self.folder/f'{self.counter:04d}-{label}-{action}';started=datetime.now(timezone.utc)
        immutable(prefix.with_suffix('.intent.json'),{'request':reference(self.home,path),'operation':action,'at':utcnow(),'sent_once_only':True})
        before=set((self.home/'dashboard/settlement').glob('relocation-result-*.json.complete'))
        try:
            self.guard();request(self.home,'console',{'command':f'awftrelocate {action} relocation-{sha[:16]} {sha}','confirmed':True})
            deadline=time.monotonic()+300
            while time.monotonic()<deadline:
                for marker in set((self.home/'dashboard/settlement').glob('relocation-result-*.json.complete'))-before:
                    p=marker.with_suffix('');r=native_read(p,{})
                    if r.get('request_sha256')!=sha or r.get('operation')!=action:continue
                    if digest(p)!=marker.read_text().strip():raise UserError('Native relocation marker changed')
                    immutable(prefix.with_suffix('.result.json'),r)
                    if not clean_relocation_result(action,r):raise UserError('Native relocation refused/partial; preserve '+str(p))
                    self.guard();return p,digest(p),r
                time.sleep(.25)
            raise UserError('Ambiguous native relocation outcome; no resend')
        except BaseException as e:
            immutable(prefix.with_suffix('.FAILED.json'),{'error':str(e),'at':utcnow(),'retry_forbidden':True});raise

    def room_ready_move(self,ident):
        if ident==PIPPIN:raise UserError('Pippin was actually invoked; never move again')
        row=self.rows[ident];gm=row['geometry_manifest'];g=checked(self.home/gm['path'],gm['sha256'],MIB);proofs={}
        for key,name in [('source_geometry','source-prepared-FUTURE-VERIFY-ONLY.json'),('destination_geometry','destination-empty-FUTURE-VERIFY-ONLY.json'),('destination_supports','retained-supports-VERIFY-ONLY.json')]:
            member=g['files'][name];p=self.home/member['path'];r=self.step(ident+'-'+key,'verify',p);proofs[key]=self.terminal(r,'settlement')
        bound=producer.bind(self.home,self.home/gm['path'],gm['sha256'],self.bridge,self.home/REVIEW,REVIEW_SHA,proofs,action='inspect')
        inspected,isha,info=self.relocate(ident.replace('/','_').replace(':','_'),'inspect',bound)
        bound=producer.bind(self.home,self.home/gm['path'],gm['sha256'],self.bridge,self.home/REVIEW,REVIEW_SHA,proofs,action='move',inspection=inspected,inspection_sha=isha)
        terminal,sha,result=self.relocate(ident.replace('/','_').replace(':','_'),'move',bound)
        if result.get('clone_invoked')is not True or result.get('intent_written')is not True or result.get('status')!='moved real vanilla room; all selected native object contents conserved; source AIR':raise UserError('Actual complete native conservation required')
        self.results.append({'capsule_id':ident,'terminal':reference(self.home,terminal),'actually_moved':True});immutable(self.folder/(f'room-{len(self.results):03d}-completed.json'),self.results[-1]);return self.results[-1]

    def saved_conserved(self,ident):
        row=self.capsules[ident];tx=transaction(self.home,ident,row['translation_xyz']);folder=Path(self.lease['world'])/'data/awft-relocations'/tx
        for name in('completed.json','conserved-after-independent-repair.json'):
            p=folder/name;marker=p.with_name(p.name+'.sha256')
            if p.is_file()and marker.is_file()and marker.read_text().strip()==digest(p):
                d=read_json(p);intent=d.get('active_intent_file','intent.json')
                if intent not in('intent.json','intent-after-uninvoked-resolution.json')or d.get('transaction_id')!=tx or d.get('capsule_id')!=ident or not(folder/intent).is_file()or digest(folder/intent)!=d.get('intent_sha256'):raise UserError('Actual native custody/intent identity differs')
                if name=='conserved-after-independent-repair.json':
                    if d.get('format')!='awft-native-independent-custody-resolution:1'or d.get('original_move_passed')is not False or d.get('clone_or_retry_invoked')is not False or not all(d.get(k)is True for k in('source_AIR_passed','current_destination_full_states_and_survival_passed','native_content_conservation_passed')):raise UserError('Independent custody cannot relabel a failed move')
                elif not d.get('completed')or not 0<d.get('native_clone_return',0)<=row['cells']:raise UserError('Genuine completed native clone required')
                return True
        return False

    def ordinary(self,label,before,delta):
        """Only sealed pipeline NONBE deltas, after exact fresh native before."""
        a=checked(self.home/before['path'],before['sha256'],4*MIB);b=checked(self.home/delta['path'],delta['sha256'],4*MIB)
        fa,fb=flatten(a),flatten(b)
        if set(fa)!=set(fb)or not fb or a.get('block_entities')or b.get('block_entities')or a.get('commands')or b.get('commands'):raise UserError('Exact no-inventory ordinary target pair required')
        for d in(a,b):
            if d.get('backup_sha256')!=self.backup or d.get('seed')!=self.registry['seed']or Path(d.get('world_path','')).resolve()!=Path(self.lease['world']).resolve():raise UserError('Ordinary world/checkpoint differs')
        already=self.step(label+'-desired-current-check','verify',self.home/delta['path'],allow_read_mismatch=True)
        if already.get('failures')==0:return self.home/delta['path'],already
        self.step(label+'-before','verify',self.home/before['path'])
        admitted=copy.deepcopy(b);admitted.pop('verification_only',None);admitted.pop('construction_forbidden',None);admitted['name']='ADMITTED exact ordinary '+label+' after real native before; no tags/commands'
        p=self.folder/(f'{self.counter:04d}-'+re.sub('[^a-zA-Z0-9_-]','_',label)[:90]+'-PLACE.json');immutable(p,admitted)
        result=self.step(label+'-place','place',p);self.step(label+'-after','verify',p);self.authored.update(fb);return p,result

    def protect(self,points):
        p=self.home/'dashboard/human-construction-session.json'
        if not p.exists():return
        data=native_read(p,{})
        if data.get('format')!='awft-human-construction-session:1'or Path(data.get('authoritative_world','')).resolve()!=Path(self.lease['world']).resolve():raise UserError('Unknown actual human reservation authority')
        for region in data.get('human_regions',[]):
            b=region['bounds_xyz']
            if any(all(b[k]<=q[k]<=b[k+3]for k in range(3))for q in points):raise UserError('Actual human region wins: '+region['id'])

    def field_pair(self,label,before,after):
        if set(before)!=set(after):raise UserError('Exact ordinary paired field required')
        stem=re.sub('[^a-zA-Z0-9_-]','_',label)[:80]+'-'+str(time.time_ns());a=self.folder/(stem+'-before.json');b=self.folder/(stem+'-delta.json')
        a.write_bytes(native_payload(self.registry,before,self.backup,'FORECAST expected before '+label+'; actual Native proof required'))
        b.write_bytes(native_payload(self.registry,after,self.backup,'FORBIDDEN ordinary '+label+'; no NBT or command replay'))
        return reference(self.home,a),reference(self.home,b)

    def source_custody_for(self,points):
        required=set()
        for ident,r in self.capsules.items():
            b=r['source_bounds_xyz']
            if any(all(b[k]<=q[k]<=b[k+3]for k in range(3))for q in points):required.add(ident)
        if not all(self.saved_conserved(x)for x in required):raise UserError('An uncaptured full source snapshot forbids this ordinary retirement')

    def native_tick_hold(self,after):
        end=datetime.fromisoformat(after.replace('Z','+00:00'));deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            self.guard();m=native_read(self.home/'dashboard/server-metrics.json',{})
            try:
                at=datetime.fromisoformat(m['at'].replace('Z','+00:00'));start=at-timedelta(milliseconds=m['interval_ms'])
                good=m['pid']==self.lease['pid']and abs(datetime.fromisoformat(m['process_started'].replace('Z','+00:00')).timestamp()-self.lease['birth'])<.01
                if good and start>=end and m['ticks_sampled']>=20:
                    p=self.folder/f'{self.counter:04d}-actual-native-tick-hold.json';immutable(p,m);return reference(self.home,p)
            except(KeyError,TypeError,ValueError):pass
            time.sleep(.25)
        raise UserError('Fresh actual native20-tick hold unavailable; no invented wall-time proof')

    def prepare_backings(self,ident):
        """Ordinary final ceiling/backing pieces, after real prior room custody."""
        if ident in self.backing_cycle_holds:raise RoomHold('Outside-backing custody cycle remains; no MOVE: '+ident)
        row=self.backings.get(ident)
        if row is None:return
        if row['holds']:raise RoomHold('Unqualified final backing point; no fixture loss accepted: '+ident)
        if not all(self.saved_conserved(x)for x in row['required_conserved_source_or_destination_ids']):raise RoomHold('Actual other-room custody required before its final ceiling/backing: '+ident)
        files=row['files']
        if 'retained-fixed-backing-VERIFY-ONLY'in files:
            ref=files['retained-fixed-backing-VERIFY-ONLY'];self.step(ident+'-retained-backing','verify',self.home/ref['path'])
        if 'approved-backing-SOURCE-DELTA'not in files:return
        ref=files['approved-backing-SOURCE-DELTA'];after=flatten(checked(self.home/ref['path'],ref['sha256'],MIB))
        ref=files['historical-before-EXPECTED-ONLY'];historical=flatten(checked(self.home/ref['path'],ref['sha256'],MIB))
        self.seed_virtual();before={q:self.virtual.get(q,historical[q])for q in after}
        self.source_custody_for(after);self.protect(after)
        a,b=self.field_pair('approved-final-outside-backing-'+ident,before,after)
        self.ordinary('approved-final-outside-backing-'+ident,a,b)
        self.virtual.update(after)

    def prepare_room(self,ident):
        row=self.rows[ident]
        if ident==PIPPIN:raise UserError('Never prepare/replay Pippin again')
        if not all(self.saved_conserved(x)for x in row['required_preceding_native_captures']):raise RoomHold('Actual preceding native inventory custody incomplete')
        counts=row['classification_counts']
        if any(n for k,n in counts.items()if k.endswith('_HOLD')):
            # A forecast hold is not permission to destroy it. An independently
            # passed CURRENT empty-target/support proof may establish that the
            # forecast obstacle is already absent; otherwise preserve it.
            gm=row['geometry_manifest'];g=checked(self.home/gm['path'],gm['sha256'],MIB)
            for key in('destination-empty-FUTURE-VERIFY-ONLY.json','retained-supports-VERIFY-ONLY.json'):
                ref=g['files'][key];result=self.step('held-forecast-current-proof-'+key,'verify',self.home/ref['path'],allow_read_mismatch=True)
                if result.get('failures')and key.startswith('destination-empty'):
                    # Root delegates only exact natural dry cover and our own
                    # earlier proven temporary structural writes. Unknown hard
                    # blocks, fluids, inventories and uncaptured sources stay held.
                    ref=row['files']['destination-current-before'];current=flatten(checked(self.home/ref['path'],ref['sha256'],MIB))
                    known=set()
                    for name in('destination-cover-DELTA','owned-skin-DELTA'):
                        if name in row['files']:
                            rr=row['files'][name];known.update(flatten(checked(self.home/rr['path'],rr['sha256'],MIB)))
                    unknown={q:s for q,s in current.items()if not s.startswith(('minecraft:air','minecraft:cave_air','minecraft:void_air'))and q not in known}
                    cover={'minecraft:short_grass','minecraft:tall_grass','minecraft:dandelion','regions_unexplored:grass_sprouts','supplementaries:barnacles'}
                    if unknown:
                        probe=self.folder/(f'{self.counter:04d}-forecast-unknown-current-AIR.json');probe.write_bytes(native_payload(self.registry,{q:'minecraft:air'for q in unknown},self.backup,'Read-only currentAIR check for merely forecast obstructions; no mutation authority'))
                        actual=self.step('forecast-obstruction-current-AIR','verify',probe,allow_read_mismatch=True)
                        if actual.get('failures')==0:unknown={}
                    if unknown and any('waterlogged=true'in s or(s.split('[',1)[0]not in cover and self.authored.get(q)!=s)for q,s in unknown.items()):raise RoomHold('Current unknown hard/inventory obstruction remains; preserve '+ident)
                    if unknown:
                        self.source_custody_for(unknown);a,b=self.field_pair('Root-exact-dry-cover-'+ident,unknown,{q:'minecraft:air'for q in unknown});self.ordinary('routine-dry-cover',a,b)
                elif result.get('failures'):
                    raise RoomHold('Current foundation obstruction remains; preserve '+ident)
        for key in('source-cover-DELTA','source-shared-structure-DELTA','destination-cover-DELTA','owned-skin-DELTA','support-plane-DELTA'):
            if key not in row['files']:continue
            self.ordinary(ident.replace('/','_').replace(':','_')+'-'+key,row['files'][key+'-before'],row['files'][key])

    def run_room(self,ident,*,prepared=False):
        if self.saved_conserved(ident):return {'capsule_id':ident,'already_conserved_native_record':True,'move_not_replayed':True}
        row=self.capsules[ident];tx=transaction(self.home,ident,row['translation_xyz']);ledger=Path(self.lease['world'])/'data/awft-relocations'/tx
        if any((ledger/name).exists()for name in('intent.json','intent-after-uninvoked-resolution.json','quarantine.json','quarantine-after-uninvoked-resolution.json')):
            raise RoomHold('Existing attempted/quarantined transaction: no ordinary re-preparation or MOVE replay; independent current-custody review only: '+ident)
        if not prepared:self.prepare_room(ident)
        # --already-prepared cannot skip the final literal ceiling/backing.
        # It precedes the three fresh proofs and the actual native survival gate.
        self.prepare_backings(ident)
        result=self.room_ready_move(ident);row=self.rows[ident]
        if 'temporary-support-release-DELTA'in row['files']:
            self.ordinary(ident.replace('/','_').replace(':','_')+'-restore-original-support',row['files']['temporary-support-release-before'],row['files']['temporary-support-release-DELTA'])
            path=self.home/row['files']['temporary-support-release-DELTA']['path'];settle=self.step('restored-support-normal-neighbors','settle',path)
            # Expect contextual windows from the actual independent native
            # calculation, never use an observed result as expected state.
            capsule=self.capsules[ident];gm=row['geometry_manifest'];definition=checked(self.home/gm['path'],gm['sha256'],MIB);prepared=definition['files']['source-prepared-FUTURE-VERIFY-ONLY.json'];source=flatten(checked(self.home/prepared['path'],prepared['sha256'],MIB));d=capsule['translation_xyz'];field={tuple(q[k]+d[k]for k in range(3)):state for q,state in source.items()}
            terminal=read_json(self.home/result['terminal']['path'])
            for w in terminal.get('native_MCW_part_derivations',[]):
                if w.get('expected_from_actual_result')is not False or w.get('state_or_inventory_writes')!=0:raise UserError('Independent native window derivation required')
                q=tuple(w['position']);value=w['native_expected_full_state'];match=re.fullmatch(r'Block\{([a-z0-9_:]+)\}(\[[a-z0-9_=,]+\])?',value)
                if not match or q not in field:raise UserError('Exact bounded native BlockState encoding required')
                field[q]=match[1]+(match[2]or'')
            p=self.folder/f'{self.counter:04d}-moved-room-derived-states.json';p.write_bytes(native_payload(self.registry,field,self.backup,'VERIFY/NORMAL SETTLE actual native independently derived moved states; NO NBT replay'))
            settle=self.step('moved-room-normal-neighbors','settle',p);result['actual_tick_hold']=self.native_tick_hold(settle['finished']);self.step('moved-room-stable-state','verify',p)
            gm=row['geometry_manifest'];bound=producer.bind(self.home,self.home/gm['path'],gm['sha256'],self.bridge,self.home/REVIEW,REVIEW_SHA,{},action='inspect-moved')
            path,sha,_=self.relocate('restored-support-full-native-custody','inspect-moved',bound);result['actual_post_restore_native_custody']=reference(self.home,path)
        return result

    @staticmethod
    def state(text):
        m=re.fullmatch(r'Block\{([a-z0-9_:]+)\}(\[[a-z0-9_=,]+\])?',text)
        if not m:raise UserError('Exact native BlockState representation required')
        return m[1]+(m[2]or'')

    def inspect_loaded(self,q):
        self.guard();self.counter+=1;now=datetime.now(timezone.utc);path=self.home/'dashboard/settlement/engineering-inspection.json'
        request(self.home,'console',{'command':'awftengine inspect '+' '.join(map(str,q)),'confirmed':True})
        deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            value=native_read(path,{})
            if value.get('position')==list(q)and datetime.fromisoformat(value.get('at','1970-01-01T00:00:00Z').replace('Z','+00:00'))>=now:
                p=self.folder/f'{self.counter:04d}-actual-native-inspection.json';immutable(p,value);self.guard();return value
            time.sleep(.02)
        raise UserError('Native read-only loaded-chunk inspection unavailable; no load/generation workaround')

    def expected_current_before(self,label,field):
        """Measured join-only retirement preimages, not relocation expectations.

        Unknown identities/facing/inventories never become deletion authority.
        This uses the existing loaded-only native inspection, no new evaluator.
        """
        p=self.folder/(re.sub('[^a-zA-Z0-9_-]','_',label)[:70]+'-known-before-'+str(time.time_ns())+'.json')
        p.write_bytes(native_payload(self.registry,field,self.backup,'Known forecast before; native proof/observations remain separate'))
        first=self.step(label+'-known-before','verify',p,allow_read_mismatch=True)
        if first.get('failures')==0:return field
        changed=dict(field);dynamic={'part','shape','north','east','south','west','up','down'}
        for q,old in field.items():
            props=properties(old)
            if not set(props)&dynamic:continue
            actual=self.inspect_loaded(q)
            if 'type'in actual or 'nbt'in actual:raise UserError('An actual inventory/BE cannot be ordinary retirement')
            state=self.state(actual['state'])
            if state.split('[',1)[0]!=old.split('[',1)[0]or'waterlogged=true'in state:raise UserError('Actual hard identity/fluid changed; preserve it')
            if any(properties(state).get(k)!=v for k,v in props.items()if k not in dynamic):raise UserError('Actual static orientation changed; preserve it')
            changed[q]=state
        # Exact fresh Native proof is still required after those read-only
        # observations. No altered after-result is ever a conservation witness.
        return changed

    def seed_virtual(self):
        index=checked(self.home/ARCH,ARCH_SHA,2*MIB);virtual={}
        for r in index['compounds']:
            for key in('actual-current-blockstates-VERIFY-ONLY','actual-current-supports-VERIFY-ONLY'):
                ref=r['files'][key];d=flatten(checked(self.home/ref['path'],ref['sha256'],8*MIB))
                for q,s in d.items():
                    if q in virtual and virtual[q]!=s:raise UserError('Historical6ad architecture source fields conflict')
                    virtual[q]=s
        for row in self.capsules.values():
            for name in('source_original','destination_original','supports_original'):
                r=row[name]
                for q,s in flatten(checked(self.home/r['path'],r['sha256'],MIB)).items():virtual.setdefault(q,s)
        # Root explicitly retained/verified these six already placed partners.
        # Every later mutation still gets a real CURRENT native before proof.
        for x,y,z,part in [(1230,66,-1184,'bot_l'),(1230,67,-1184,'top_l'),(1226,66,-1213,'bot_r'),(1226,67,-1213,'top_r'),(1227,66,-1213,'bot_l'),(1227,67,-1213,'top_l')]:
            facing='east'if x==1230 else'north';virtual[x,y,z]=f'mcwwindows:dark_oak_plank_window[facing={facing},part={part}]'
        for ident,row in self.capsules.items():
            if not self.saved_conserved(ident):continue
            ref=row['source_original'];field=flatten(checked(self.home/ref['path'],ref['sha256'],MIB))
            for cover in row['source_cover_preparations']:field[tuple(cover['position'])]='minecraft:air'
            for q in field:virtual[q]='minecraft:air'
            d=row['translation_xyz']
            for q,s in field.items():virtual[tuple(q[k]+d[k]for k in range(3))]=s
        virtual.update(self.authored);self.virtual=virtual;return index

    def retire_old_skin(self):
        if not all(self.saved_conserved(x)for x in self.capsules):raise UserError('All affected inventories must be conserved before bulk old-grid skin retirement')
        if self.virtual is None:self.seed_virtual()
        for group in self.pipeline['old_skin_batches']:
            r=group['delta'];target=flatten(checked(self.home/r['path'],r['sha256'],8*MIB));ref=group['before'];fallback=flatten(checked(self.home/ref['path'],ref['sha256'],8*MIB))
            before={q:self.virtual.get(q,fallback[q])for q in target};before={q:s for q,s in before.items()if not s.startswith(('minecraft:air','minecraft:cave_air','minecraft:void_air'))}
            if not before:continue
            self.source_custody_for(before);before=self.expected_current_before('old-owned-skin-'+group['group'],before)
            a,b=self.field_pair('owned-old-grid-retirement-'+group['group'],before,{q:'minecraft:air'for q in before});self.ordinary('owned-old-grid-retirement',a,b);self.virtual.update({q:'minecraft:air'for q in before})

    def retire_skin_for(self,points):
        if self.virtual is None:self.seed_virtual()
        scope=set(points)
        for group in self.pipeline['old_skin_batches']:
            ref=group['delta'];field=flatten(checked(self.home/ref['path'],ref['sha256'],8*MIB));targets=set(field)&scope
            if not targets:continue
            if not all(self.saved_conserved(x)for x in group['required_completed_native_capsules']):raise RoomHold('Current old-house stock not all conserved for '+group['group'])
            ref=group['before'];fallback=flatten(checked(self.home/ref['path'],ref['sha256'],8*MIB));before={q:self.virtual.get(q,fallback[q])for q in targets};before={q:s for q,s in before.items()if not s.startswith(('minecraft:air','minecraft:cave_air','minecraft:void_air'))}
            if not before:continue
            self.source_custody_for(before);before=self.expected_current_before('scoped-old-owned-skin',before);a,b=self.field_pair('scoped-owned-grid-retirement',before,{q:'minecraft:air'for q in before});self.ordinary('scoped-owned-grid-retirement',a,b);self.virtual.update({q:'minecraft:air'for q in before})

    def native_contents(self,ids):
        result={}
        for ident in ids:
            row=self.capsules[ident];tx=transaction(self.home,ident,row['translation_xyz']);folder=Path(self.lease['world'])/'data/awft-relocations'/tx
            name='completed.json'if(folder/'completed.json').exists()else'conserved-after-independent-repair.json';p=folder/name
            if p.with_name(p.name+'.sha256').read_text().strip()!=digest(p):raise UserError('Exact genuine native contents marker differs')
            d=read_json(p);snapshots=d.get('after_native_snapshots',d.get('current_native_snapshots'))
            if not snapshots:raise UserError('No complete actual native contents snapshots')
            for s in snapshots:
                tag=nbtlib.parse_nbt(s['full_native_NBT']);q=tuple(int(tag[k])for k in('x','y','z'));result[q]=(s['class'],tag)
        return result

    def architecture(self,ident):
        if self.virtual is None:index=self.seed_virtual()
        else:index=checked(self.home/ARCH,ARCH_SHA,2*MIB)
        selected=[r for r in index['compounds']if r['id']==ident]
        if len(selected)!=1:raise UserError('One exact final39 architecture required')
        row=selected[0]
        # Root already placed/settled/verified these exact three. Never replay
        # their default/new-stock tags merely to populate this worker's journal.
        if ident in('east-coal','shoal-warden','thin-sail'):return {'id':ident,'Root_already_built_preserved':True,'placed_again':False}
        needed=set(row['incoming_native_capture_ids'])|set(row['all_original_capture_ids_intersected_by_architecture_writes'])
        if not all(self.saved_conserved(x)for x in needed):raise RoomHold('Actual complete room/source custody not ready for '+ident)
        source=checked(self.home/row['files']['SOURCE-ONLY']['path'],row['files']['SOURCE-ONLY']['sha256'],8*MIB)
        delta=checked(self.home/row['files']['architecture-PROSPECTIVE-FORBIDDEN']['path'],row['files']['architecture-PROSPECTIVE-FORBIDDEN']['sha256'],8*MIB);field=flatten(delta)
        fixed=set(map(tuple,source.get('retained_native_BE_positions',source.get('retained_BE_positions',[]))))
        if set(field)&fixed:raise UserError('Architecture may never replay a conserved native BE')
        self.source_custody_for(field);self.protect(field)
        self.retire_skin_for(field)
        contents=self.native_contents(row['incoming_native_capture_ids'])
        stockpath=None;stock_before=None;stock_after=None
        if contents:
            stockfield={q:self.virtual[q]for q in contents};stockpath=self.folder/(ident+'-retained-native-full-tags-VERIFY-ONLY.json')
            immutable(stockpath,exact_native_contents_payload(self.registry,self.backup,stockfield,contents))
            result=self.step(ident+'-complete-native-tags-before','verify',stockpath);require_exact_native_tag_receipt(result,len(contents));stock_before=reference(self.home,self.terminal(result,'settlement')[0])
        extra={tuple(r['position']):r['exact_old_state']for r in source['required_owned_NONBE_shell_retirements']if tuple(r['position'])not in field}
        if extra:
            before={q:self.virtual.get(q,s)for q,s in extra.items()};before=self.expected_current_before(ident+'-copied-owned-shell',before);a,b=self.field_pair('retire-copied-owned-shell-'+ident,before,{q:'minecraft:air'for q in before});self.ordinary('copied-owned-shell',a,b);self.virtual.update({q:'minecraft:air'for q in before})
        missing=set(field)-set(self.virtual)
        if missing:raise UserError('Unknown actual/historical architecture target; no inventedAIR')
        before={q:self.virtual[q]for q in field};before=self.expected_current_before(ident+'-architecture',before)
        beforepath=self.folder/(ident+'-fresh-expected-before.json');beforepath.write_bytes(native_payload(self.registry,before,self.backup,'Exact architecture before; historical/actual operations source basis, realNativeproofrequired'))
        self.step(ident+'-architecture-before','verify',beforepath)
        admitted=copy.deepcopy(delta);admitted.pop('verification_only',None);admitted.pop('construction_forbidden',None);admitted['name']='ADMITTED final furnished '+ident+' after actual complete custody/native before'
        path=self.folder/(ident+'-PLACE-ONCE.json');immutable(path,admitted);placed=self.step(ident+'-PLACE','place',path)
        ref=row['files']['normal-joins-PROSPECTIVE-ONLY'];self.step(ident+'-normal-neighbors','settle',self.home/ref['path'])
        ref=row['files']['full-after-PROSPECTIVE-VERIFY-ONLY'];verified=self.step(ident+'-complete-native-after','verify',self.home/ref['path'])
        if stockpath is not None:
            result=self.step(ident+'-complete-native-tags-after','verify',stockpath);require_exact_native_tag_receipt(result,len(contents));stock_after=reference(self.home,self.terminal(result,'settlement')[0])
        self.virtual.update(field);self.authored.update(field);proof=self.terminal(verified,'settlement');result={'id':ident,'native_full_after':reference(self.home,proof[0]),'native_full_tags_before':stock_before,'native_full_tags_after':stock_after,'actually_placed':True,'retained_native_contents_unchanged':len(contents),'native_visual_acceptance':False};self.building_results.append(result);immutable(self.folder/(ident+'-BUILT.json'),result);return result

def execute(home,rooms,*,lease=LEASE,lease_sha=LEASE_SHA,prepared=False,all_ready=False,build=False):
    job=City(home,lease,lease_sha)
    holds=[];built=set(('east-coal','shoal-warden','thin-sail'))
    try:
        selected=job.backing_order+sorted(job.backing_cycle_holds)if all_ready else rooms
        if not selected:raise UserError('Explicit rooms or all-ready selection required')
        for ident in selected:
            if ident==PIPPIN:
                if not job.saved_conserved(ident):raise UserError('Pippin genuine separate custody is required; never clone it again')
                continue
            try:job.run_room(ident,prepared=prepared)
            except RoomHold as e:holds.append({'capsule_id':ident,'held_before_move':str(e)});immutable(job.folder/(f'held-{len(holds):03d}.json'),holds[-1]);continue
            if build:
                job.virtual=None;index=job.seed_virtual()
                for row in index['compounds']:
                    if row['id']in built:continue
                    required=set(row['incoming_native_capture_ids'])|set(row['all_original_capture_ids_intersected_by_architecture_writes'])
                    if not all(job.saved_conserved(x)for x in required):continue
                    try:job.architecture(row['id']);built.add(row['id'])
                    except RoomHold as e:holds.append({'building':row['id'],'held_before_place':str(e)})
        if build and all(job.saved_conserved(x)for x in job.capsules):job.retire_old_skin()
        immutable(job.folder/'phase-complete.json',{'results':job.results,'buildings':job.building_results,'holds':holds,'at':utcnow(),'all_city_complete':False,'lease_release_not_inferred':True})
        return {'folder':str(job.folder),'actual_moves':job.results,'actual_buildings':job.building_results,'holds':holds,'lease_still_requires_explicit_safe_release':True}
    except BaseException as e:
        immutable(job.folder/'STOPPED.json',{'error':str(e),'at':utcnow(),'actual_moves':job.results,'no_retry':True});raise

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);p.add_argument('--rooms',nargs='*',default=[]);p.add_argument('--all-ready',action='store_true');p.add_argument('--build-ready',action='store_true');p.add_argument('--lease',default=LEASE);p.add_argument('--lease-sha',default=LEASE_SHA);p.add_argument('--already-prepared',action='store_true');a=p.parse_args();print(json.dumps(execute(a.home,a.rooms,lease=a.lease,lease_sha=a.lease_sha,prepared=a.already_prepared,all_ready=a.all_ready,build=a.build_ready),indent=2))
