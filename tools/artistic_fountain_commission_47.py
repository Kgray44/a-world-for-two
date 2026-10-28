"""New exact47 request source; previous45 sources and failed receipts stay intact.

Only a genuine fresh native2532 verification of a separately prepared actual
stopped dry bundle can produce a request. No command or live-world action runs.
"""
from __future__ import annotations
import argparse
import hashlib,json,re,tomllib,zipfile
from pathlib import Path

from control_room.common import UserError,digest,utcnow
from tools.artistic_bridge_refinement import flatten
from tools.artistic_bridge_topside_inspection import current_pack,owned_regular
from tools.artistic_fountain_dry_binding import INTAKE,MARS,NICHE,SOURCE_GEOMETRY,parts
from tools.artistic_fountain_parking import POSITIONS,classify,context
from tools.artistic_quay_prototype import bounded,fresh_proof,member,same_world
from tools.playtest import guard

CANDIDATE='0.1.0-candidate.47'
BRIDGE='0.6.33'
PACK_SHA='ea6b4ff61da8ec6c0f8ce39131852c11b824a72ee3b3b9c6abfe195c6801d972'
JAR_SHA='25b1642f5d1e07856e43350507166599134c88eeb1632357e3928ad87b24d2cc'
CLASS='worldfortwo/bridge/NativeFountainSupport.class'
MIB=1024**2


def require_actual_dry(manifest,geometry,registry,checkpoint):
    if (manifest.get('format')!='awft-r5-cohesive-guardian-fountain:1'or manifest.get('actual_dry_checkpoint')is not True
            or manifest.get('previous_actual_R5_geometry_sha256')!=SOURCE_GEOMETRY
            or (manifest.get('checkpoint_id'),manifest.get('checkpoint_sha256'))!=(checkpoint['id'],checkpoint['sha256'])
            or 'actual-dry-native-BEFORE.json'not in manifest.get('files',{})):
        raise UserError('A genuinely actual current stopped dry R5 binding is mandatory')
    same_world(geometry,registry)
    if (geometry.get('backup_sha256')!=checkpoint['sha256']or geometry.get('verification_only')is not True
            or geometry.get('construction_forbidden')is not True or geometry.get('commands')!=[]
            or geometry.get('block_entities')!=[]or geometry.get('prospective_only')is True):
        raise UserError('Current actual read-only geometry only; no prospective/source replay')
    cells=flatten(geometry)
    if len(cells)!=2532 or not POSITIONS<=set(cells)or classify({p:cells[p]for p in POSITIONS})!='ALREADY_PARKED':
        raise UserError('Exact2532 complete dry geometry and retained14 parked gate required')
    if (cells.get(INTAKE)!='minecraft:water[level=0]'
            or any(cells.get(p)!='minecraft:air'for p in (*NICHE,(1145,67,-1131),(1145,68,-1131)))):
        raise UserError('Retain plain extractable intake and the genuinely drained wheel niche/runoff')
    for n in range(3):
        if parts(cells.get((1138,75+n,-1129),''))!=(MARS,{'facing':'west','multiblock':str(n),'waterlogged':'false'}):
            raise UserError('All three actual native statue parts must remain exact')
    speeds=manifest.get('actual_saved_zero_speeds')
    if not isinstance(speeds,dict)or len(speeds)!=2 or any(type(v)not in(int,float)or v!=0 for v in speeds.values()):
        raise UserError('Both actual saved zero-speed witnesses required')


def prepare(home,dry_bundle,dry_manifest_sha,native_verify):
    home,owner,registry,checkpoint=context(home)
    dry_bundle=Path(dry_bundle).absolute()
    if dry_bundle.parent!=home/'staging':raise UserError('New actual private dry bundle required')
    manifest_path=owned_regular(home,dry_bundle/'manifest.json',2*MIB)
    manifest=bounded(manifest_path,2*MIB)
    if digest(manifest_path)!=dry_manifest_sha:raise UserError('Exact reviewed actual dry manifest required')
    geometry=member(dry_bundle,manifest,'plaza.json');same=member(dry_bundle,manifest,'actual-dry-native-BEFORE.json')
    if geometry!=same:raise UserError('Actual dry source and full preimage must be the same observed field')
    require_actual_dry(manifest,geometry,registry,checkpoint)
    native_verify=owned_regular(home,Path(native_verify).absolute(),65536)
    if native_verify.parent!=home/'dashboard/settlement'or not re.fullmatch(r'settlement-result-[a-f0-9-]{36}\.json',native_verify.name):
        raise UserError('Genuine owned native verification journal required')
    geometry_path=dry_bundle/'plaza.json'
    proof,marker=fresh_proof(native_verify,digest(geometry_path),2532)
    release,pack_sha=current_pack(home,CANDIDATE)
    if pack_sha!=PACK_SHA:raise UserError('Actual47 pack differs from its immutable compiled pin')
    jar=owned_regular(home,home/'server/mods'/('awft-control-bridge-'+BRIDGE+'.jar'),16*MIB)
    installed=bounded(home/'server/installed.json',2*MIB)
    if jar.stat().st_size!=562634 or digest(jar)!=JAR_SHA or installed.get('files',{}).get(jar.name)!=JAR_SHA:
        raise UserError('Actual installed47 bridge JAR differs from the reviewed build')
    with zipfile.ZipFile(jar)as archive:
        info=archive.getinfo(CLASS);descriptor=archive.getinfo('META-INF/neoforge.mods.toml')
        if not 0<info.file_size<=256*1024 or not 0<descriptor.file_size<=65536:raise UserError('Finite exact native helper/descriptor required')
        class_sha=hashlib.sha256(archive.read(info)).hexdigest();meta=tomllib.loads(archive.read(descriptor).decode('utf8'))
        if not any(m.get('modId')=='awft_control_bridge'and m.get('version')==BRIDGE for m in meta.get('mods',[])):
            raise UserError('Actual installed47 helper version differs')
    if owner.get('pack_sha256')!=PACK_SHA:raise UserError('Actual owner47 pack pin differs')
    def ref(path):
        path=owned_regular(home,path,2*MIB)
        return {'path':path.relative_to(home).as_posix(),'bytes':path.stat().st_size,'sha256':digest(path)}
    request={'format':'awft-native-fountain:1','candidate':CANDIDATE,'bridge':BRIDGE,'pack_sha256':PACK_SHA,
        'seed':str(registry['seed']),'world_path':registry['world_path'],'backup_sha256':checkpoint['sha256'],
        'native_class_sha256':class_sha,'geometry':ref(geometry_path),'native_verify':ref(native_verify)}
    raw=(json.dumps(request,separators=(',',':'))+'\n').encode()
    if len(raw)>65536:raise UserError('Bounded exact native request exceeded')
    sha=hashlib.sha256(raw).hexdigest();output=home/'dashboard/settlement'/('fountain-'+sha[:16])
    if output.exists():raise UserError('Preserve prior request/receipt; no automatic replay or unchanged retry')
    reserve=guard(2*MIB,MIB)
    fresh_proof(native_verify,digest(geometry_path),2532)
    if bounded(home/'dashboard/settlement/backup-receipt.json').get('sha256')!=checkpoint['sha256']:
        raise UserError('Current stopped checkpoint changed before request publication')
    receipt={'format':'awft-fountain47-request-owner:1','created':utcnow(),'source_sha256':digest(Path(__file__)),
        'request_sha256':sha,'dry_manifest':ref(manifest_path),'actual_pack_manifest':ref(release),
        'actual_installed_JAR_sha256':JAR_SHA,'actual_native_class_sha256':class_sha,
        'native_verify_marker':ref(marker),'actual_native_verify_finished':proof['finished'],
        'storage_guard':reserve,'header_source_or_NBT_pressure_or_RPM_writes':0,'native_actions':0,'world_writes':0,
        'next_gate':'Parent serialized typed commission: real single wheel feed, pumped fill, normal STOP/drain/reopen; no header seed/pressure NBT/forced RPM; actual result and restart remain pending'}
    output.mkdir();(output/'request.json').write_bytes(raw)
    (output/'ownership.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')
    return {'output':str(output),'request_sha256':sha,'native_class_sha256':class_sha,
        'typed_console_command_parent_only':'awftfountain commission '+output.name+' '+sha,'native_actions':0}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('home','dry-bundle','native-verify'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--dry-manifest-sha',required=True);a=p.parse_args()
    print(json.dumps(prepare(a.home,a.dry_bundle,a.dry_manifest_sha,a.native_verify),indent=2))
