"""Build a portable Prism import ZIP from exact source and updater pins."""
from __future__ import annotations
import argparse
import json
import re
import shlex
import struct
import urllib.parse
import zipfile
from pathlib import Path
from control_room.common import REPO, Layout, UserError, atomic_write, digest, read_json, utcnow, write_json
from control_room.pack import validate_pack
from control_room.storage import Storage, tree_size
from .playtest import guard


PUBLIC_SERVER = 'malls-cup.tun.ply.gg'
LOCAL_SERVER = '127.0.0.1:25565'
SERVER_CHOICES = (('A World for Two - Public (KG and Sera)', PUBLIC_SERVER),
                  ('A World for Two - KG local computer only', LOCAL_SERVER))


def server_list():
    """Minecraft 1.21.1 ServerList's uncompressed Compound/List NBT format.

    Resource-pack acceptance is omitted, leaving Minecraft's normal prompt.
    This is fresh portable data, never copied from a player's real server list.
    """
    def text(value):
        raw=value.encode('ascii')
        return struct.pack('>H',len(raw))+raw
    def string(name,value):return b'\x08'+text(name)+text(value)
    entries=[]
    for name,address in SERVER_CHOICES:
        entries.append(string('name',name)+string('ip',address)+b'\x01'+text('hidden')+b'\x00\x00')
    return b'\x0a\x00\x00\x09'+text('servers')+b'\x0a'+struct.pack('>i',len(entries))+b''.join(entries)+b'\x00'


def verify_archive(path,prelaunch,pins,artwork):
    """Static custody/layout checks; this does not launch or import Prism."""
    import hashlib
    with zipfile.ZipFile(path) as archive:
        names=archive.namelist()
        if archive.testzip() or len(names)!=len(set(names)):
            raise UserError('Export ZIP CRC or duplicate-entry validation failed')
        allowed={'instance.cfg','mmc-pack.json','INSTALL.txt','CONNECT.txt','awft-export.json',
                 '.minecraft/options.txt','.minecraft/config/iris.properties','.minecraft/servers.dat',
                 '.minecraft/awft-tools/LICENSE.txt'}
        allowed.update('.minecraft/awft-tools/'+pin['filename'] for pin in pins)
        allowed.update('.minecraft/'+file.relative_to(REPO/'packwiz').as_posix()
                       for file in (REPO/'packwiz/config').rglob('*') if file.is_file())
        if set(names)!=allowed or any(name.startswith('/') or '..' in name.split('/') or '\\' in name for name in names):
            raise UserError('Export contains an unexpected or unsafe archive path')
        config=archive.read('instance.cfg').decode()
        stored=next(line.split('=',1)[1] for line in config.splitlines() if line.startswith('PreLaunchCommand='))
        if stored.replace('\\"','"')!=prelaunch:
            raise UserError('Portable QSettings pre-launch quoting differs from the approved command')
        arguments=shlex.split(prelaunch)
        if (arguments[:3]!=['$INST_JAVA','-jar','$INST_MC_DIR/awft-tools/'+pins[0]['filename']]
                or arguments[3:6]!=['--bootstrap-no-update','--bootstrap-main-jar','$INST_MC_DIR/awft-tools/'+pins[1]['filename']]
                or arguments[6:8]!=['-s','client'] or len(arguments)!=9):
            raise UserError('Unexpected portable pre-launch argument structure')
        if 'MaxMemAlloc=6144\n' not in config or 'OverrideJavaLocation=false\n' not in config:
            raise UserError('Portable client memory/Java settings changed')
        components=json.loads(archive.read('mmc-pack.json'))['components']
        if not any(c.get('uid')=='net.neoforged' and c.get('version')=='21.1.262' for c in components):
            raise UserError('Portable NeoForge component does not match the pinned version')
        for pin in pins:
            raw=archive.read('.minecraft/awft-tools/'+pin['filename'])
            if len(raw)!=pin['size'] or hashlib.sha256(raw).hexdigest()!=pin['hashes']['sha256']:
                raise UserError('Packwiz updater bytes changed inside the archive')
        if archive.read('.minecraft/servers.dat')!=server_list():
            raise UserError('Portable public/local server choices changed')
        original=archive.read('.minecraft/config/fancymenu/assets/awft-background.png')
        if hashlib.sha256(original).hexdigest()!=artwork['sha256']:
            raise UserError('Original menu artwork changed inside the export')
        title=archive.read('.minecraft/config/fancymenu/customization/awft_title.txt').decode()
        if ('[action_type:joinserver]' in title or title.count('instance_identifier = mc_titlescreen_multiplayer_button')!=1
                or not re.search(r'vanilla_button\s*\{\s*label = Join Our World\s*hoverlabel = Join Our World\s*is_hidden = false',title)):
            raise UserError('Public export must expose the native multiplayer server list')
        return {'archive_entries':len(names),'uncompressed_bytes':sum(info.file_size for info in archive.infolist()),
                'archive_crc':'pass','portable_prism_layout':'pass','pinned_bootstrap_chain':'pass',
                'prelaunch_static_syntax':'pass','original_artwork_identity':'pass','portable_server_choices':'pass',
                'no_runtime_account_world_or_qa_files':'pass'}


def command(url):
    parsed=urllib.parse.urlsplit(url)
    if (parsed.scheme!='https' or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.hostname!='kgray44.github.io' or not parsed.path.startswith('/a-world-for-two/')
            or not re.fullmatch(r'https://kgray44\.github\.io/a-world-for-two/(?:releases/[A-Za-z0-9._-]+/)?pack\.toml',url)):
        raise UserError('Use this project’s public HTTPS Packwiz manifest URL')
    return ('"$INST_JAVA" -jar "$INST_MC_DIR/awft-tools/packwiz-installer-bootstrap-v0.0.3.jar" '
        '--bootstrap-no-update --bootstrap-main-jar "$INST_MC_DIR/awft-tools/packwiz-installer-v0.5.14.jar" '
        '-s client '+url)


def build(home,url=None,revision=1):
    if type(revision) is not int or not 1<=revision<=99:raise UserError('Choose export revision 1–99')
    layout=Layout(home);lock=read_json(REPO/'catalog/lock.json')
    errors=validate_pack(REPO/'packwiz',lock)
    if errors:raise UserError('Pack integrity failed: '+'; '.join(errors))
    url=url or 'https://kgray44.github.io/a-world-for-two/releases/'+lock['version']+'/pack.toml'
    if '/releases/' in url and url!='https://kgray44.github.io/a-world-for-two/releases/'+lock['version']+'/pack.toml':
        raise UserError('The immutable updater channel must match this exact candidate version')
    prelaunch=command(url);pins=read_json(REPO/'catalog/tools.lock.json')
    artwork=read_json(REPO/'catalog/menu-artwork.json')
    for original in (REPO/'assets/menu/a-world-for-two-background.jpg',REPO/'packwiz/config/fancymenu/assets/awft-background.png'):
        if not original.is_file() or original.stat().st_size!=artwork['bytes'] or digest(original)!=artwork['sha256']:
            raise UserError('Original owner artwork custody failed before export')
    tools=[pins['packwiz_bootstrap'],pins['packwiz_installer']]
    for pin in tools:
        path=layout.caches/pin['filename']
        if not path.is_file() or path.stat().st_size!=pin['size'] or digest(path)!=pin['hashes']['sha256']:
            raise UserError('Pinned updater missing or changed: '+pin['filename'])
    allocation=tree_size(REPO/'packwiz/config')+sum(p['size'] for p in tools)+2*1024*1024
    if allocation>32*1024*1024:raise UserError('Split an export larger than 32 MiB')
    reserve=guard(2*1024*1024,allocation);Storage(layout).reserve(allocation)
    suffix='' if revision==1 else '-r'+str(revision)
    path=layout.home/'exports'/('A-World-for-Two-'+lock['version']+'-Prism'+suffix+'.zip')
    if path.exists():raise UserError('Preserve the existing immutable export and use a new version')
    path.parent.mkdir(parents=True,exist_ok=True)
    cfg=('[General]\nInstanceType=OneSix\nname=A World for Two\nOverrideMemory=true\n'
        'MinMemAlloc=1024\nMaxMemAlloc=6144\nOverrideJavaLocation=false\nOverrideCommands=true\n'
        'PreLaunchCommand='+prelaunch.replace('"','\\"')+'\nWrapperCommand=\nPostExitCommand=\nOverrideWindow=true\n'
        'MinecraftWinWidth=1280\nMinecraftWinHeight=800\n')
    components={'formatVersion':1,'components':[
        {'uid':'org.lwjgl3','version':'3.3.3','dependencyOnly':True},
        {'uid':'net.minecraft','version':'1.21.1','important':True},
        {'uid':'net.neoforged','version':lock['neoforge']}]}
    with zipfile.ZipFile(path,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        archive.writestr('instance.cfg',cfg)
        archive.writestr('mmc-pack.json',json.dumps(components,indent=2)+'\n')
        archive.writestr('.minecraft/options.txt','renderDistance:8\nsimulationDistance:5\nmaxFps:60\nenableVsync:true\n')
        archive.writestr('.minecraft/config/iris.properties','enableShaders=false\n')
        archive.writestr('.minecraft/servers.dat',server_list())
        for pin in tools:archive.write(layout.caches/pin['filename'],'.minecraft/awft-tools/'+pin['filename'])
        for file in sorted((REPO/'packwiz/config').rglob('*')):
            if file.is_file():archive.write(file,'.minecraft/'+file.relative_to(REPO/'packwiz').as_posix())
        archive.writestr('INSTALL.txt',
            'A World for Two '+lock['version']+' - portable Prism client\n\n'
            '1. In Prism Launcher choose Add Instance, then Import from ZIP, and select this ZIP.\n'
            '2. Sign into your own licensed Minecraft Java account and select Java 21.\n'
            '3. Launch the instance. Maximum client heap is 6 GiB; shaders initially stay off.\n'
            '4. Leave the pinned Packwiz pre-launch command enabled. It downloads exact client files.\n'
            '5. Choose Join Our World, then the Public server entry when joining from another computer.\n'
            '   The KG local entry is only for Minecraft on the dedicated server computer itself.\n'
            '6. Ask the host to whitelist your exact Java username. See CONNECT.txt for address details.\n\n'
            'This version checks the immutable manifest on each launch:\n'+url+'\n\n'
            'The host must publish that exact manifest and its dependencies before first installation can work.\n'
            'This development candidate still requires fresh native Prism import/download qualification.\n'
            'No account, world, logs or LOD databases are included. Choose shaders in Video Settings after baseline startup.\n'
            'Hosting documentation: https://github.com/Kgray44/a-world-for-two/blob/main/docs/INSTALL.md\n')
        archive.writestr('CONNECT.txt',
            'A World for Two - connection choices\n\n'
            'Click Join Our World to open Minecraft multiplayer.\n'
            'KG and Sera on different computers: choose Public ('+PUBLIC_SERVER+').\n'
            'Only on the computer actually hosting the server: choose KG local ('+LOCAL_SERVER+').\n'
            'The host must have the server and the linked Playit game tunnel running.\n'
            'Use your own licensed Minecraft Java account and ask the host to whitelist your exact username.\n'
            'Edit or add servers normally if the host gives you a new address.\n'
            'This candidate still requires fresh native Prism import/download and remote two-player qualification.\n')
        archive.write(REPO/'docs/UPDATER-LICENSE.txt','.minecraft/awft-tools/LICENSE.txt')
        archive.writestr('awft-export.json',json.dumps({'format':'awft-prism-export:1','version':lock['version'],
            'pack_sha256':digest(REPO/'packwiz/pack.toml'),'pack_url':url,'original_artwork_sha256':artwork['sha256'],
            'status':'candidate; fresh import and public download qualification pending'}))
    checks=verify_archive(path,prelaunch,tools,artwork)
    report={'at':utcnow(),'version':lock['version'],'export_revision':revision,'pack_sha256':digest(REPO/'packwiz/pack.toml'),
        'path':str(path),'size':path.stat().st_size,'sha256':digest(path),'guard':reserve,
        'original_artwork_sha256':artwork['sha256'],'public_server':PUBLIC_SERVER,'updater_url':url,
        'checks':checks|{'fresh_prism_import':'pending','public_updater_install':'pending','client_startup':'pending'},
        'boundary':'Candidate artifact; not a published or qualified release.'}
    write_json(path.with_suffix('.json'),report)
    atomic_write(path.with_suffix('.sha256'),report['sha256']+'  '+path.name+'\n')
    print(json.dumps(report),flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--home',type=Path,default=Path(r'D:\A World for Two'))
    parser.add_argument('--pack-url',default=None,help='Defaults to this exact version\'s immutable public Packwiz channel')
    parser.add_argument('--revision',type=int,default=1)
    args=parser.parse_args();build(args.home,args.pack_url,args.revision)
