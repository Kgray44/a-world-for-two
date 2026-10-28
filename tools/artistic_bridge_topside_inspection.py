"""Private request producer for the inspect-only optional46 bridge helper.

Requires actual installed helper bytes and a fresh genuine native106 BEFORE.
Never starts a server, modifies an entity, or submits the resulting command.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

from control_room.common import UserError,digest,utcnow
from tools.artistic_bridge_topside_custody import exact_glues
from tools.artistic_quay_prototype import bounded,member,fresh_proof,same_world
from tools.artistic_maritime_depth import admit_owner
from tools.playtest import guard

CLASS='worldfortwo/bridge/RetainedBridgeGlueInspection.class'
MIB=1024**2


def owned_regular(home,path,limit):
    """Reject redirected ancestry before resolving a bounded owned file."""
    home,path=Path(home).absolute(),Path(path).absolute()
    if home.resolve()!=home or not path.is_relative_to(home):
        raise UserError('Canonical owned home-relative artifact required')
    for p in (path,*path.parents):
        if p==home:break
        if p.is_symlink()or getattr(p,'is_junction',lambda:False)():
            raise UserError('No symbolic/junction pack or evidence path')
    if not path.is_file()or not 0<path.stat().st_size<=limit or path.resolve()!=path:
        raise UserError('Bounded regular unredirected artifact required')
    return path


def current_pack(home,candidate):
    home=Path(home).absolute()
    if (not isinstance(candidate,str)or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}',candidate)
            or candidate.endswith('.')):
        raise UserError('A safe exact active candidate version required')
    active=bounded(owned_regular(home,home/'packwiz/active.json',65536))
    installed=bounded(owned_regular(home,home/'server/installed.json',2*MIB))
    expected=active.get('pack_sha256')
    if (active.get('version')!=candidate or installed.get('pack_version')!=candidate
            or not isinstance(expected,str)or not re.fullmatch(r'[a-f0-9]{64}',expected)
            or installed.get('pack_sha256')!=expected):
        raise UserError('Actual active/installed candidate and pack hash differ')
    release=owned_regular(home,home/'packwiz/releases'/candidate/'pack.toml',65536)
    if digest(release)!=expected:
        raise UserError('The genuine active versioned pack manifest hash differs')
    return release,expected


def prepare(home,study,study_sha,native_before,bridge_jar,candidate,bridge):
    reserve=guard(MIB,2*MIB)
    home,study,native_before,bridge_jar=map(lambda p:Path(p).resolve(),(home,study,native_before,bridge_jar))
    if home.parent!=Path(r'D:\A World for Two\staging\world-tests')or study.parent!=home/'staging'or not native_before.is_relative_to(home/'dashboard/settlement')or bridge_jar.parent!=home/'server/mods':
        raise UserError('Exact private owned study, native receipt and installed helper JAR required')
    current=bounded(home/'dashboard/settlement/backup-receipt.json');registry=bounded(home/'dashboard/settlement/registry.json',16*MIB)
    admit_owner(home,bounded(home/'dashboard/artistic-owner.json'),current,current['id'],current['sha256'])
    release,pack_sha=current_pack(home,str(candidate))
    source=bounded(study/'manifest.json')
    if digest(study/'manifest.json')!=study_sha or source.get('format')!='awft-retained-glue-next-proof:1'or(source['checkpoint_id'],source['checkpoint_sha256'])!=(current['id'],current['sha256']):
        raise UserError('Fresh exact current stopped census/preimage study required')
    census=member(study,source,'current-saved-glue-census-READONLY.json');before=member(study,source,'moving106-before-VERIFY-ONLY.json')
    same_world(census,registry);same_world(before,registry);exact_glues(census['glues'])
    if len(before['blocks'])!=106 or before.get('backup_sha256')!=current['sha256']or before.get('block_entities')!=[]or before.get('commands')!=[]:
        raise UserError('Exact current nonBE106 preimage required')
    proof,marker=fresh_proof(native_before,digest(study/'moving106-before-VERIFY-ONLY.json'),106)
    if bridge_jar.is_symlink()or not bridge_jar.is_file()or not 0<bridge_jar.stat().st_size<=32*MIB:
        raise UserError('A finite regular installed helper JAR is required')
    with zipfile.ZipFile(bridge_jar)as archive:
        if CLASS not in archive.namelist():raise UserError('The installed helper has no read-only inspection class yet; do not fabricate class provenance')
        info=archive.getinfo(CLASS)
        if not 0<info.file_size<=128*1024:raise UserError('Bounded actual native class required')
        native=archive.read(CLASS)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}',str(candidate))or not re.fullmatch(r'\d+\.\d+\.\d+',bridge):
        raise UserError('Exact explicit candidate/bridge identities required; native helper independently checks installed identity')
    def ref(path):
        path=Path(path).resolve()
        if not path.is_relative_to(home)or path.is_symlink():raise UserError('Owned regular evidence only')
        return {'path':path.relative_to(home).as_posix(),'bytes':path.stat().st_size,'sha256':digest(path)}
    originals=census['original_moving_plans']
    if len(originals)!=2:raise UserError('Two original moving plan references required')
    original_refs={}
    for label,row in zip(('north_original','south_original'),originals):
        path=home/row['relative']
        if digest(path)!=row['sha256']:raise UserError('Frozen original moving source changed')
        original_refs[label]=ref(path)
    request={'format':'awft-retained-bridge-inspection:1','candidate':str(candidate),'bridge':bridge,
             'native_class_sha256':hashlib.sha256(native).hexdigest(),'pack_sha256':pack_sha,
             'checkpoint':ref(home/'dashboard/settlement/backup-receipt.json'),'census':ref(study/'current-saved-glue-census-READONLY.json'),
             'preimage':ref(study/'moving106-before-VERIFY-ONLY.json'),'native_before':ref(native_before),'native_before_complete':ref(marker),**original_refs}
    raw=(json.dumps(request,separators=(',',':'))+'\n').encode();sha=hashlib.sha256(raw).hexdigest()
    output=home/'dashboard/settlement'/('bridge-topside-inspection-'+sha[:16])
    if output.exists():raise UserError('Preserve the existing immutable request; no unchanged automatic retry')
    receipt={'format':'awft-inspection-request-ownership:1','created':utcnow(),'source_sha256':digest(Path(__file__)),'request_sha256':sha,
             'installed_helper_jar_sha256':digest(bridge_jar),'study_sha256':study_sha,'actual_native_before_finished':proof['finished'],
             'actual_pack_manifest':ref(release),
             'native_actions':0,'world_writes':0,'storage_guard':reserve,'next_gate':'Parent reviewed typed local-console INSPECT only; this producer submits nothing'}
    output.mkdir();(output/'request.json').write_bytes(raw);(output/'ownership.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')
    return {'output':str(output),'request_sha256':sha,'native_class_sha256':request['native_class_sha256'],'typed_console_command':'awftbridgetop inspect '+output.name+' '+sha,'native_actions':0}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('home','study','native-before','bridge-jar'):p.add_argument('--'+k,type=Path,required=True)
    for k in ('study-sha','candidate','bridge'):p.add_argument('--'+k,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.home,a.study,a.study_sha,a.native_before,a.bridge_jar,a.candidate,a.bridge),indent=2))
