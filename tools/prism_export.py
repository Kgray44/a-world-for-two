"""Build a portable Prism import ZIP from exact source and updater pins."""
from __future__ import annotations
import argparse
import json
import re
import urllib.parse
import zipfile
from pathlib import Path
from control_room.common import REPO, Layout, UserError, digest, read_json, utcnow, write_json
from control_room.pack import validate_pack
from control_room.storage import Storage, tree_size
from .playtest import guard


def command(url):
    parsed=urllib.parse.urlsplit(url)
    if (parsed.scheme!='https' or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.hostname!='kgray44.github.io' or not parsed.path.startswith('/a-world-for-two/')
            or not re.fullmatch(r'https://kgray44\.github\.io/a-world-for-two/(?:releases/[A-Za-z0-9._-]+/)?pack\.toml',url)):
        raise UserError('Use this project’s public HTTPS Packwiz manifest URL')
    return ('"$INST_JAVA" -jar "$INST_MC_DIR/awft-tools/packwiz-installer-bootstrap-v0.0.3.jar" '
        '--bootstrap-no-update --bootstrap-main-jar "$INST_MC_DIR/awft-tools/packwiz-installer-v0.5.14.jar" '
        '-s client '+url)


def build(home,url,revision=1):
    if type(revision) is not int or not 1<=revision<=99:raise UserError('Choose export revision 1–99')
    layout=Layout(home);lock=read_json(REPO/'catalog/lock.json')
    errors=validate_pack(REPO/'packwiz',lock)
    if errors:raise UserError('Pack integrity failed: '+'; '.join(errors))
    prelaunch=command(url);pins=read_json(REPO/'catalog/tools.lock.json')
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
        for pin in tools:archive.write(layout.caches/pin['filename'],'.minecraft/awft-tools/'+pin['filename'])
        for file in sorted((REPO/'packwiz/config').rglob('*')):
            if file.is_file():archive.write(file,'.minecraft/'+file.relative_to(REPO/'packwiz').as_posix())
        archive.write(REPO/'docs/INSTALL.md','INSTALL.txt')
        archive.write(REPO/'docs/UPDATER-LICENSE.txt','.minecraft/awft-tools/LICENSE.txt')
        archive.writestr('awft-export.json',json.dumps({'format':'awft-prism-export:1','version':lock['version'],
            'pack_sha256':digest(REPO/'packwiz/pack.toml'),'pack_url':url,'status':'candidate; fresh import and public download qualification pending'}))
    with zipfile.ZipFile(path) as archive:
        if archive.testzip():raise UserError('Export ZIP failed CRC verification')
        if not {'instance.cfg','mmc-pack.json'}.issubset(archive.namelist()):raise UserError('Invalid Prism archive layout')
    report={'at':utcnow(),'version':lock['version'],'export_revision':revision,'pack_sha256':digest(REPO/'packwiz/pack.toml'),
        'path':str(path),'size':path.stat().st_size,'sha256':digest(path),'guard':reserve,
        'checks':{'archive_crc':'pass','portable_prism_layout':'pass','pinned_bootstrap_chain':'pass',
            'fresh_prism_import':'pending','public_updater_install':'pending','client_startup':'pending'},
        'boundary':'Candidate artifact; not a published or qualified release.'}
    write_json(path.with_suffix('.json'),report);print(json.dumps(report),flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--home',type=Path,default=Path(r'D:\A World for Two'))
    parser.add_argument('--pack-url',default='https://kgray44.github.io/a-world-for-two/pack.toml')
    parser.add_argument('--revision',type=int,default=1)
    args=parser.parse_args();build(args.home,args.pack_url,args.revision)
