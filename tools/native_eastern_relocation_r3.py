"""Seal an uninstalled R2 source request with exact R3 envelope/API classes."""
from pathlib import Path
import hashlib,time,re,zipfile
from control_room.common import UserError,digest,read_json
from tools.artistic_eastern_urban_custody import canonical
from tools.native_relocation_request import class_hash
from tools.playtest import guard


def seal(home,request_path,request_sha,bridge_jar):
    home=Path(home).resolve();request_path=Path(request_path).resolve();guard(1048576,1048576)
    if not request_path.is_relative_to(home/'staging') or digest(request_path)!=request_sha:raise UserError('One exact uninstalled source request only')
    req=read_json(request_path)
    if req.get('format')!='awft-native-approved-capsule-relocation:2' or req['native_class_sha256']!=class_hash(bridge_jar,'worldfortwo.bridge.NativeRelocationSupport'):raise UserError('Actual new helper bytes differ')
    games=list((home/'server/libraries/net/minecraft/server').rglob('*-srg.jar'))
    if len(games)!=1:raise UserError('One exact actual native game archive required')
    version=read_json(home/'server/installed.json')['neoforge']
    if not isinstance(version,str) or not re.fullmatch(r'21\.1\.\d+',version):raise UserError('Exact installed NeoForge API version required')
    patched=home/f'server/libraries/net/neoforged/neoforge/{version}/neoforge-{version}-server.jar'
    if not patched.is_file() or patched.is_symlink():raise UserError('Exact installed patched game API required')
    def runtime_class(name):
        with zipfile.ZipFile(patched) as z:
            override=name.replace('.','/')+'.class' in z.namelist()
        return class_hash(patched if override else games[0],name)
    req['runtime_tags_class_sha256']=class_hash(bridge_jar,'worldfortwo.bridge.NativeRelocationSupport$RuntimeTags')
    req['level_chunk_class_sha256']=runtime_class('net.minecraft.world.level.chunk.LevelChunk')
    req['vanilla_clone_class_sha256']=runtime_class('net.minecraft.server.commands.CloneCommands')
    for row in req['BE_class_pins']:
        if row['class'].startswith('net.minecraft.'):
            row['class_sha256']=runtime_class(row['class'])
    raw=canonical(req)+b'\n';sha=hashlib.sha256(raw).hexdigest();out=home/'staging'/('relocation-'+sha[:16]+'-R3-SOURCE-'+str(time.time_ns()));out.mkdir();(out/'request.json').write_bytes(raw)
    return {'folder':str(out),'request_sha256':sha,'runtime_bundle_name':'relocation-'+sha[:16],'native_actions':0,'request_installed':False}
