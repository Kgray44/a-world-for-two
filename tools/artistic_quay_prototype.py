"""Additive admission for frozen quay shops and FIXED bridge ornament only.

Reads authenticated stopped saves and writes private proposals/receipts. It never
starts Minecraft, sends a command, edits a live world or admits moving geometry.
The old construction-forbidden source artifacts remain byte-for-byte intact.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from control_room.common import UserError, digest, read_json, utcnow
from tools.artistic_bridge_refinement import flatten
from tools.artistic_engineering import checked_native_proof
from tools.artistic_maritime_depth import admit_owner
from tools.artistic_materials import require_material_rule, require_outdoor_rule
from tools.artistic_spawn_plaza import payload
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld, base, properties

MIB = 1024**2
MAX_OUTPUT = 16*MIB
WEST = 'staging/north-bank-west-five-final-20261028T0200Z'
WEST_SHA = '7e8f392abbb71eec606cc7b2158a541d6689744cea22c125571a5214427c4254'
TOPSIDE = 'staging/artistic-bridge-topside-20261028T0128Z'
TOPSIDE_SHA = '10055afe6f11dcb6587b65c742e2b4f909dcf1972d73e26fd1fecd6a137883ff'
KINDS = ('shipwright', 'smith', 'armoury', 'tavern', 'florist')
FACES = {'north': (0,-1), 'south': (0,1), 'west': (-1,0), 'east': (1,0)}
VOID = {'minecraft:air','minecraft:cave_air','minecraft:void_air'}
APRON_COVER = {'regions_unexplored:grass_sprouts','supplementaries:barnacles'}


def bounded(path, limit=4*MIB):
    path = Path(path)
    if not path.is_file() or path.is_symlink() or not 0 < path.stat().st_size <= limit:
        raise UserError('A bounded regular owned source file is required')
    for parent in path.parents:
        if parent.is_symlink():
            raise UserError('Symbolic source ancestry is not admitted')
    return read_json(path)


def member(folder, manifest, name):
    p = folder/name
    row = manifest['files'][name]
    value = bounded(p)
    if p.stat().st_size != row['bytes'] or digest(p) != row['sha256']:
        raise UserError('Frozen member bytes changed: '+name)
    return value


def context(home, output):
    home, output = Path(home).resolve(), Path(output).resolve()
    if home.parent != Path(r'D:\A World for Two\staging\world-tests') or output.parent != home/'staging' or output.exists():
        raise UserError('New immediate private artistic output directory required')
    current = bounded(home/'dashboard/settlement/backup-receipt.json')
    admit_owner(home, bounded(home/'dashboard/artistic-owner.json'), current, current['id'], current['sha256'])
    return home, output, current, bounded(home/'dashboard/settlement/registry.json', 16*MIB)


def same_world(plan, registry):
    if str(plan.get('seed')) != str(registry.get('seed')) or plan.get('world_path') != registry.get('world_path'):
        raise UserError('Frozen source belongs to another actual world')


def approach_columns(after, threshold):
    """Three-wide, two-deep NATURAL outside standing apron, not a new street."""
    q = tuple(threshold)
    value = after[q]
    f = properties(value)
    if base(value) != 'minecraft:spruce_stairs' or f.get('half') != 'bottom' or f.get('facing') not in FACES:
        raise UserError('Retain the exact authored bottom-half threshold stair')
    dx,dz = FACES[f['facing']]
    # Stair facing points inward/upward; exterior is the opposite direction.
    return {(q[0]-dx*n+dz*side, q[2]-dz*n-dx*side) for n in (1,2) for side in (-1,0,1)}


def exact_preimage(snapshot, expected):
    actual = {}
    for q, old in expected.items():
        value = snapshot.state(q)
        if value != old or q in snapshot.protected:
            raise UserError('Actual current saved preimage/BE differs: '+str(q))
        actual[q] = value
    return actual


def apron_clearance(value):
    if base(value) in VOID:
        return False
    if base(value) in APRON_COVER and 'waterlogged=true' not in value:
        return True
    raise UserError('Preserve a nonordinary/wet exterior object rather than silently clearing it')


def write_bundle(output, docs, manifest):
    raw = {name:(json.dumps(value,separators=(',',':'))+'\n').encode() for name,value in docs.items()}
    manifest['files'] = {n:{'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()} for n,v in raw.items()}
    raw['manifest.json'] = (json.dumps(manifest,indent=2)+'\n').encode()
    if sum(map(len,raw.values())) > MAX_OUTPUT:
        raise UserError('Finite prototype output allocation exceeded')
    output.mkdir()
    for name,value in raw.items():
        (output/name).write_bytes(value)
    return {'output':str(output),'manifest_sha256':digest(output/'manifest.json'),'files':manifest['files'],'native_actions':0}


def prepare(home, output, group):
    reserve = guard(4*MIB,32*MIB)
    home, output, current, registry = context(home,output)
    folder = home/(WEST if group == 'west' else TOPSIDE)
    expected = WEST_SHA if group == 'west' else TOPSIDE_SHA
    source = bounded(folder/'manifest.json')
    if digest(folder/'manifest.json') != expected:
        raise UserError('Exact original forbidden source manifest required')
    snapshot = BackupWorld(home,current,registry)
    docs,preimages,retained,full,source_refs = {},{},{},{},[]
    apron_clear={}
    checks=[]
    try:
        if group == 'west':
            for kind in KINDS:
                after = member(folder,source,kind+'-PROPOSAL.json')
                old = member(folder,source,kind+'-before.json')
                same_world(after,registry);same_world(old,registry)
                changes = flatten(after);old_states = flatten(old)
                if set(changes) != set(old_states) or preimages.keys() & old_states.keys():
                    raise UserError('Each exact frozen shop field must be disjoint and paired')
                preimages.update(exact_preimage(snapshot,old_states))
                lot = source['lots'][kind]
                for row in lot['actual_dry']['actual_dry_columns']:
                    q = tuple(row['support']);value=snapshot.state(q)
                    if value != row['state'] or q in snapshot.protected:
                        raise UserError('Retain each exact dry natural building support')
                    retained[q]=value
                for x,z in approach_columns(changes,lot['primary_threshold']):
                    # All five sites have actual gravel63. No grading, imported
                    # platform, inferred support or artificial street elevation.
                    q=(x,63,z);value=snapshot.state(q)
                    if value != 'minecraft:gravel' or q in snapshot.protected:
                        raise UserError('The exterior three-wide natural apron is not exact dry gravel63: '+str(q))
                    retained[q]=value
                    for y in (64,65,66):
                        q=(x,y,z);value=snapshot.state(q)
                        if q in snapshot.protected:
                            raise UserError('Exterior natural standing/body clearance differs: '+str(q))
                        clear=apron_clearance(value)
                        if q in changes:
                            raise UserError('The external apron must stay outside authored house geometry')
                        if clear:
                            apron_clear[q]='minecraft:air';preimages[q]=value
                        else:retained[q]=value
                checks.append(require_material_rule(changes,'UNCHANGED COMPLETE '+kind+' prototype'))
                docs[kind+'-PENDING-NATIVE.json']=dict(after,backup_sha256=current['sha256'])
                source_refs.append({'name':kind,'relative':(folder/(kind+'-PROPOSAL.json')).relative_to(home).as_posix(),'sha256':digest(folder/(kind+'-PROPOSAL.json'))})
                full.update(changes)
        else:
            after=member(folder,source,'fixed-ornament-PROPOSAL.json');same_world(after,registry)
            changes=flatten(after)
            old=flatten(member(folder,source,'before.json'))
            if len(changes)!=48 or not set(changes).issubset(old):
                raise UserError('Only the frozen48 FIXED ornaments are admitted; no moving targets')
            preimages.update(exact_preimage(snapshot,{q:old[q] for q in changes}))
            complete=flatten(member(folder,source,'complete-future-VERIFY-ONLY.json'))
            # Re-read the actual COMPLETE bridge, not the future moving design.
            for q in complete:
                full[q]=snapshot.state(q)
            for x,z in ((1186,-1185),(1200,-1185),(1186,-1103),(1200,-1103)):
                for y in range(69,77):
                    q=x,y,z;value=snapshot.state(q)
                    if q in snapshot.protected:
                        raise UserError('Fixed supporting post unexpectedly contains a native BE')
                    if q not in changes:retained[q]=value
            full.update(changes)
            checks=[require_material_rule(full,'COMPLETE actual bridge with FIXED48 only'),require_outdoor_rule(full,'Complete fixed-only bridge prototype')]
            docs['fixed-ornament-PENDING-NATIVE.json']=dict(after,backup_sha256=current['sha256'])
            source_refs=[{'name':'fixed','relative':(folder/'fixed-ornament-PROPOSAL.json').relative_to(home).as_posix(),'sha256':digest(folder/'fixed-ornament-PROPOSAL.json')}]
        sources=snapshot.sources.copy()
    finally:
        snapshot.close()
    for q,value in retained.items():
        if q in preimages and preimages[q]!=value:
            raise UserError('Retained support conflicts with the exact owned target preimage')
    before=dict(preimages);before.update(retained)
    if apron_clear:
        docs['apron-cover-clear-PENDING-NATIVE.json']=payload(registry,current['sha256'],apron_clear,'Only exact dry ordinary barnacles/grass_sprouts cover removed for the outside walking apron',before=True)
    docs['before-targets-supports-VERIFY-ONLY.json']=payload(registry,current['sha256'],before,'VERIFY ONLY exact prototype targets, retained supports and outside natural standing/body apron',before=True)
    after_full=dict(full);after_full.update(retained)
    after_full.update(apron_clear)
    docs['complete-after-VERIFY-ONLY.json']=payload(registry,current['sha256'],after_full,'VERIFY ONLY complete prototype and retained dry supports/aprons',before=True)
    if group=='west':
        docs['complete-after-VERIFY-ONLY.json']['block_entities']=[row for n,d in docs.items() if n.endswith('-PENDING-NATIVE.json') for row in d['block_entities']]
    if bounded(home/'dashboard/settlement/backup-receipt.json').get('sha256') != current['sha256']:
        raise UserError('Checkpoint advanced during read; preserve and rebind rather than infer equality')
    return write_bundle(output,docs,{'format':'awft-additive-prototype-admission:1','created':utcnow(),'source_sha256':digest(Path(__file__)),
        'group':group,'checkpoint_id':current['id'],'checkpoint_sha256':current['sha256'],'original_manifest_relative':(folder/'manifest.json').relative_to(home).as_posix(),
        'original_manifest_sha256':expected,'original_members':source_refs,'target_count':len(preimages),'retained_support_body_count':len(retained),'before_count':len(before),
        'ancillary_exact_dry_cover_clear':[list(q) for q in sorted(apron_clear)],'building_geometry_changes':0,
        'masterplan_site_agreement':('South accepted the exact five frozen sites/thresholds; public crooked3wide street remains separate' if group=='west' else 'Existing fixed post positions only; moving106 separately held'),
        'authorised_scope':'Parallel exact standalone native prototype; no first-LIFE prerequisite, no moving geometry, no world action by producer',
        'source_checks':checks,'saved_sources':sources,'storage_guard':reserve,'native_actions':0,'world_writes':0,'construction_forbidden':True,
        'next_gate':'Fresh actual current native zero-failure BEFORE proof covering every target/support/apron, then bind; actual place/normal-settle/strict full verify and complete exterior/interior game review remain required'})


def fresh_proof(path, expected_sha, count, *, now=None):
    proof,marker=checked_native_proof(path,expected_sha,count,now=now,maximum_age=300)
    if (proof.get('cleanup_required') is not False or proof.get('temporary_tickets_remaining') != 0
            or proof.get('pending_shared_chunk_futures') != 0 or proof.get('ticket_cleanup_error')):
        raise UserError('Fresh native receipt must use actual clean SettlementSupport schema')
    return proof,marker


def pending_member_name(name):
    return 'fixed-ornament-PENDING-NATIVE.json' if name=='fixed' else name+'-PENDING-NATIVE.json'


def bind(home, prepared, prepared_sha, native_before, output):
    reserve=guard(2*MIB,MAX_OUTPUT)
    home,output,current,registry=context(home,output)
    prepared,native_before=Path(prepared).resolve(),Path(native_before).resolve()
    if prepared.parent!=home/'staging' or not native_before.is_relative_to(home/'dashboard/settlement'):
        raise UserError('Owned prepared source and actual settlement terminal proof required')
    data=bounded(prepared/'manifest.json')
    if digest(prepared/'manifest.json')!=prepared_sha or data.get('format')!='awft-additive-prototype-admission:1':
        raise UserError('Exact newly reviewed prepared manifest required')
    if (data.get('checkpoint_id'),data.get('checkpoint_sha256'))!=(current['id'],current['sha256']):
        raise UserError('Fresh stopped checkpoint requires new source preimage comparison')
    before=member(prepared,data,'before-targets-supports-VERIFY-ONLY.json');same_world(before,registry)
    proof,marker=fresh_proof(native_before,digest(prepared/'before-targets-supports-VERIFY-ONLY.json'),len(before['blocks']))
    original_path=home/data['original_manifest_relative']
    original=bounded(original_path)
    if digest(original_path)!=data['original_manifest_sha256']:
        raise UserError('Original forbidden source was changed; preserve it')
    docs={}
    for ref in data['original_members']:
        path=home/ref['relative'];old=bounded(path)
        if digest(path)!=ref['sha256']:raise UserError('Frozen original geometry changed')
        name=ref['name'];pending=member(prepared,data,pending_member_name(name))
        if pending!=dict(old,backup_sha256=current['sha256']):raise UserError('Pending geometry may only rebind its backup reference')
        admitted=deepcopy(pending);admitted.pop('construction_forbidden',None)
        admitted['name']='Exact admitted standalone prototype: '+old['name']
        admitted['validation']='Fresh real native BEFORE targets/supports/apron proof bound by additive manifest; strict after and actual art review pending'
        docs[name+'-PLACE-ONCE.json']=admitted
        settle=deepcopy(admitted);settle['block_entities']=[]
        settle.update(name='SETTLE ONLY normal current native joins, never tag/inventory replay: '+name,verification_only=True,construction_forbidden=True)
        docs[name+'-NORMAL-SETTLE-ONLY.json']=settle
    if data.get('ancillary_exact_dry_cover_clear'):
        name='apron-cover-clear-PENDING-NATIVE.json';clear=member(prepared,data,name);clear_states=flatten(clear)
        if set(clear_states)!={tuple(q) for q in data['ancillary_exact_dry_cover_clear']} or len(clear_states)>90:
            raise UserError('Only the exact bounded dry apron cover cells may enter the ancillary plan')
        before_states=flatten(before)
        if any(v!='minecraft:air' or q not in before_states or not apron_clearance(before_states[q]) for q,v in clear_states.items()):
            raise UserError('Ancillary apron clearance must have actual original ordinary dry cover proof')
        clear=deepcopy(clear);clear.pop('construction_forbidden',None);clear.pop('verification_only',None)
        docs['apron-cover-clear-PLACE-ONCE.json']=clear
        docs['apron-cover-clear-NORMAL-SETTLE-ONLY.json']=dict(clear,block_entities=[],verification_only=True,construction_forbidden=True)
    docs['complete-after-VERIFY-ONLY.json']=member(prepared,data,'complete-after-VERIFY-ONLY.json')
    return write_bundle(output,docs,{'format':'awft-admitted-standalone-prototypes:1','created':utcnow(),'source_sha256':digest(Path(__file__)),
        'group':data['group'],'checkpoint_id':current['id'],'checkpoint_sha256':current['sha256'],'prepared_relative':prepared.relative_to(home).as_posix(),'prepared_sha256':prepared_sha,
        'actual_before_receipt':{'relative':native_before.relative_to(home).as_posix(),'sha256':digest(native_before),'complete_sha256':digest(marker),'finished':proof['finished']},
        'source_geometry_changes':0,'original_forbidden_artifacts_changed':False,'native_actions':0,'world_writes':0,
        'moving_leaf_admission':False,'scope':'Parent may place exact admitted standalone prototypes once, normal settle each, strict verify whole+retained supports, then actual day/night exterior/interior/approach review; public streets/moving cycles remain separate','storage_guard':reserve})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='action',required=True)
    a=s.add_parser('prepare');a.add_argument('--group',choices=('west','fixed'),required=True)
    for n in ('home','output'):a.add_argument('--'+n,type=Path,required=True)
    b=s.add_parser('bind')
    for n in ('home','prepared','native-before','output'):b.add_argument('--'+n,type=Path,required=True)
    b.add_argument('--prepared-sha',required=True)
    a=p.parse_args()
    result=prepare(a.home,a.output,a.group) if a.action=='prepare' else bind(a.home,a.prepared,a.prepared_sha,a.native_before,a.output)
    print(json.dumps(result,indent=2))
