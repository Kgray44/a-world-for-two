"""Build only reviewed, tag-bound Packwiz snapshots; never publish current main.

No network, tags, pushes, Pages configuration or deployment happens here. The
manual workflow consumes this bounded static tree. Failed owned staging/receipts
are retained outside the public output; an existing output is never replaced.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import tarfile
import threading
import uuid
from pathlib import Path, PurePosixPath

from control_room.common import REPO, UserError, digest, utcnow, write_json
from control_room.pack import validate_pack

MAX_SNAPSHOT_BYTES = 64*1024**2
MAX_FILE_BYTES = 8*1024**2
MAX_SNAPSHOTS = 16
MAX_MEMBERS = 5000
MAX_METADATA_EXCLUSIONS = 32
VERSION = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,79}')
SECRET_FIELDS = {'accounts','account','accesstoken','refreshtoken','clienttoken',
                 'password','privatekey','apikey','sessiontoken','credentials'}
RUNTIME_NAMES = {'world','worlds','saves','logs','backups','cache','caches','accounts','accounts.json',
                 'launcher_accounts.json','usercache.json','session.lock','credentials','secrets','playerdata'}


def approved_catalog(path):
    if path.stat().st_size>64*1024:raise UserError('Publication catalog exceeds 64 KiB')
    data=json.loads(path.read_text(encoding='utf-8-sig'))
    if set(data)!={'format','stable','snapshots'} or data['format']!='awft-publication:1':
        raise UserError('Unsupported publication catalog')
    # Stable activation needs its own qualification flow. This publisher cannot
    # turn a candidate into a root update channel by changing a JSON string.
    if data['stable'] is not None:
        raise UserError('Root stable publication is disabled; stable must remain null')
    rows=data['snapshots']
    if not isinstance(rows,list) or not 1<=len(rows)<=MAX_SNAPSHOTS:
        raise UserError('Approve between one and sixteen immutable snapshots')
    seen=set();tags=set()
    for row in rows:
        required={'version','git_tag','pack_sha256','status'}
        if (not isinstance(row,dict) or not required<=set(row)
                or set(row)-required-{'tagged_metadata_exclusions'}):
            raise UserError('Invalid snapshot approval')
        metadata_exclusions(row.get('tagged_metadata_exclusions',{}))
        version=row['version']
        if not isinstance(version,str) or not VERSION.fullmatch(version):
            raise UserError('Invalid publication version')
        if version.casefold() in seen:raise UserError('Duplicate publication version: '+version)
        seen.add(version.casefold())
        if row['git_tag']!='awft-'+version or row['git_tag'].casefold() in tags:
            raise UserError('Snapshot must name its unique explicit awft version tag')
        tags.add(row['git_tag'].casefold())
        if not isinstance(row['pack_sha256'],str) or not re.fullmatch('[a-f0-9]{64}',row['pack_sha256']):
            raise UserError('Snapshot needs an exact lowercase SHA-256')
        if row['status'] not in ('prerelease','qualified'):
            raise UserError('Unknown approved snapshot status')
    return data


def metadata_exclusions(value):
    """Only individually reviewed, byte-bound stale mod metadata may be omitted."""
    if not isinstance(value,dict) or len(value)>MAX_METADATA_EXCLUSIONS:
        raise UserError('Approve at most 32 explicit tagged metadata exclusions')
    for name,review in value.items():
        if (not isinstance(name,str) or not re.fullmatch(r'mods/[A-Za-z0-9][A-Za-z0-9._-]{0,127}\.pw\.toml',name)
                or not isinstance(review,dict) or set(review)!={'sha256','reason'}
                or not isinstance(review['sha256'],str) or not re.fullmatch('[a-f0-9]{64}',review['sha256'])
                or not isinstance(review['reason'],str) or not review['reason'].strip()
                or len(review['reason'])>1024):
            raise UserError('Tagged metadata exclusion needs an explicit mods/*.pw.toml path, SHA-256 and review reason')
    return value


def git_commit(repo,tag):
    result=subprocess.run(['git','-C',str(repo),'rev-parse','--verify','refs/tags/'+tag+'^{commit}'],
                          capture_output=True,text=True,timeout=20)
    if result.returncode or not re.fullmatch(r'[a-f0-9]{40,64}',result.stdout.strip()):
        raise UserError('Approved Git tag is missing or does not resolve to a commit: '+tag)
    return result.stdout.strip()


def archive_tag(repo,commit,target):
    """Bound the actual git-archive stream, including malformed or huge tags."""
    env=os.environ|{'GIT_NO_LAZY_FETCH':'1','GIT_TERMINAL_PROMPT':'0'}
    process=subprocess.Popen(['git','-C',str(repo),'archive','--format=tar',commit,'--','packwiz','catalog/lock.json'],
                             stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=env)
    timer=threading.Timer(45,lambda: process.kill() if process.poll() is None else None)
    timer.daemon=True;timer.start();size=0
    try:
        with target.open('xb') as output:
            while chunk:=process.stdout.read(1024**2):
                size+=len(chunk)
                if size>MAX_SNAPSHOT_BYTES:
                    raise UserError('Tagged git archive exceeds its 64 MiB bound')
                output.write(chunk)
        if process.wait(timeout=5):raise UserError('git archive failed for approved commit '+commit)
    finally:
        timer.cancel()
        if process.poll() is None:process.kill()
        process.wait(timeout=5)
        process.stdout.close()
    return size


def safe_member(member):
    name=member.name.rstrip('/')
    path=PurePosixPath(name)
    if (not name or name.startswith('/') or '\\' in name or ':' in name or '\x00' in name
            or any(part in ('','.','..') for part in name.split('/')) or len(name)>512):
        raise UserError('Unsafe tagged archive path')
    if member.issym() or member.islnk() or not (member.isdir() or member.isfile()) or member.sparse:
        raise UserError('Tagged archive links, devices and sparse files are forbidden')
    if member.size<0 or member.size>MAX_FILE_BYTES:raise UserError('Tagged member exceeds 8 MiB')
    if any(part.casefold() in RUNTIME_NAMES for part in path.parts):
        raise UserError('Runtime/account/world data cannot be published')
    if member.isdir():
        if name not in ('catalog','packwiz') and not name.startswith('packwiz/'):
            raise UserError('Unapproved directory in tagged archive')
        return path
    if name=='catalog/lock.json':return path
    if not name.startswith('packwiz/'):raise UserError('Unapproved tagged file')
    relative=PurePosixPath(*path.parts[1:]);parts=relative.parts
    if relative.suffix.casefold() in ('.jar','.class','.zip','.dat','.mca','.sqlite','.db','.nbt'):
        raise UserError('Runtime binaries or databases cannot be published')
    if relative.as_posix() in ('pack.toml','index.toml','options.txt'):return path
    if (len(parts)==2 and parts[0] in ('mods','shaderpacks','resourcepacks')
            and relative.name.endswith('.pw.toml')):return path
    if parts[0] in ('config','defaultconfigs') and relative.suffix.casefold() in (
            '.toml','.json','.txt','.yml','.yaml','.properties','.png','.jpg','.jpeg','.webp','.mcmeta'):
        return path
    raise UserError('Unapproved Packwiz payload path: '+str(relative))


def extract_tag(archive,directory):
    directory.mkdir();seen=set();total=0
    with tarfile.open(archive,mode='r:') as source:
        for count,member in enumerate(source,1):
            if count>MAX_MEMBERS:raise UserError('Too many tagged archive members')
            path=safe_member(member)
            name=path.as_posix().casefold()
            if name in seen:raise UserError('Duplicate or case-colliding archive path')
            seen.add(name)
            target=directory.joinpath(*path.parts)
            if not target.resolve().is_relative_to(directory.resolve()):raise UserError('Tagged archive escaped staging')
            if member.isdir():target.mkdir(parents=True,exist_ok=True);continue
            total+=member.size
            if total>MAX_SNAPSHOT_BYTES:raise UserError('Tagged payload exceeds its 64 MiB bound')
            target.parent.mkdir(parents=True,exist_ok=True)
            with source.extractfile(member) as incoming,target.open('xb') as output:
                remaining=member.size
                while remaining:
                    chunk=incoming.read(min(remaining,1024**2))
                    if not chunk:raise UserError('Truncated tagged payload')
                    output.write(chunk);remaining-=len(chunk)
    return total


def no_account_fields(value):
    if isinstance(value,dict):
        for key,item in value.items():
            if re.sub('[^a-z]','',key.casefold()) in SECRET_FIELDS:
                raise UserError('Account or credential field cannot enter a public lock')
            no_account_fields(item)
    elif isinstance(value,list):
        for item in value:no_account_fields(item)


def snapshot_payload(pack,index,row):
    expected={'pack.toml','index.toml'}|{entry['file'] for entry in index['files']}
    if len(expected)!=2+len(index['files']):raise UserError('Duplicate Packwiz index entry')
    excluded=metadata_exclusions(row.get('tagged_metadata_exclusions',{}))
    if set(excluded)&expected:
        raise UserError('Indexed Packwiz files cannot be excluded from publication')
    actual={p.relative_to(pack).as_posix() for p in pack.rglob('*') if p.is_file()}
    if actual!=expected|set(excluded):
        raise UserError('Unindexed tagged files must exactly match reviewed metadata exclusions')
    proofs=[]
    for name,review in sorted(excluded.items()):
        path=pack/name
        if digest(path)!=review['sha256']:
            raise UserError('Approved excluded metadata SHA-256 changed: '+name)
        proofs.append({'file':name,'sha256':review['sha256'],'bytes':path.stat().st_size,
                       'reason':review['reason'],'indexed':False,'published':False})
    return expected,proofs


def validate_snapshot(directory,row):
    pack=directory/'packwiz';lock_path=directory/'catalog/lock.json'
    if not (pack/'pack.toml').is_file() or not lock_path.is_file():raise UserError('Tag lacks packwiz and release lock')
    if digest(pack/'pack.toml')!=row['pack_sha256']:raise UserError('Approved pack SHA-256 changed: '+row['version'])
    lock=json.loads(lock_path.read_text(encoding='utf-8-sig'));no_account_fields(lock)
    if (lock.get('version')!=row['version'] or lock.get('minecraft')!='1.21.1'
            or lock.get('neoforge')!='21.1.262' or lock.get('java')!=21):
        raise UserError('Tagged version/runtime differs from its approval and pinned platform')
    errors=validate_pack(pack,lock)
    if errors:raise UserError('Tagged Packwiz hash chain/pins failed: '+'; '.join(errors))
    import tomllib
    manifest=tomllib.loads((pack/'pack.toml').read_text())
    index=tomllib.loads((pack/'index.toml').read_text())
    if (manifest.get('index',{}).get('file')!='index.toml' or manifest['index'].get('hash-format')!='sha256'
            or index.get('hash-format')!='sha256' or len(index.get('files',[]))>3000):
        raise UserError('Unsupported tagged Packwiz index')
    expected,_=snapshot_payload(pack,index,row)
    for relative in sorted(expected):
        if not relative.endswith('.pw.toml'):continue
        path=pack/relative
        meta=tomllib.loads(path.read_text());download=meta['download'];algorithm=download.get('hash-format')
        lengths={'sha1':40,'sha256':64,'sha512':128}
        if algorithm not in lengths or not re.fullmatch('[a-f0-9]{'+str(lengths[algorithm])+'}',download.get('hash','')):
            raise UserError('Unpinned tagged author download')
        if meta['filename'] in ('.','..','') or '/' in meta['filename'] or '\\' in meta['filename'] or ':' in meta['filename']:
            raise UserError('Unsafe downloaded filename')
        if 'url' in download:
            from urllib.parse import urlsplit
            url=urlsplit(download['url'])
            if url.scheme!='https' or not url.hostname or url.username or url.password:
                raise UserError('Author downloads require public HTTPS without credentials')
        elif download.get('mode')!='metadata:curseforge':raise UserError('Unknown pinned download mode')
    return lock,len(expected)


def reserve_local(output,count):
    if os.name!='nt':return
    # Archive, extracted staging and public copy are each separately capped.
    total=count*3*MAX_SNAPSHOT_BYTES+2*1024**2
    drive=output.resolve().drive.casefold()
    c=2*1024**2+(total if drive=='c:' else 0);d=total if drive=='d:' else 0
    if drive not in ('c:','d:'):raise UserError('Use a reviewed C: or D: output on this Windows host')
    result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
        r'C:\Users\kkids\AppData\Local\AeroStorageWatch\ReserveGuard.ps1',
        '-EstimatedCBytes',str(c),'-EstimatedDBytes',str(d)],capture_output=True,text=True,timeout=30,
        creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:raise UserError('Host storage reserve refused publication build')
    if not json.loads(result.stdout.strip().splitlines()[-1]).get('allowed'):
        raise UserError('Host storage reserve refused publication build')


def index_html(rows):
    entries=''.join('<tr><td>'+html.escape(row['version'])+'</td><td>'+html.escape(row['status'])+
        '</td><td><a href="releases/'+html.escape(row['version'],quote=True)+'/pack.toml">Packwiz manifest</a> · '+
        '<a href="releases/'+html.escape(row['version'],quote=True)+'/lock.json">Exact lock</a></td><td><code>'+
        row['pack_sha256']+'</code></td></tr>' for row in rows)
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        '<title>A World for Two — approved snapshots</title><style>body{font:17px system-ui;max-width:1100px;margin:3rem auto;padding:0 1rem;line-height:1.6;color:#20382d;background:#fffaf0}'
        'table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:.7rem;border-bottom:1px solid #b9c4b6}code{overflow-wrap:anywhere;font-size:.8em}a{color:#225f49}</style>'
        '<h1>A World for Two</h1><p>Reviewed, immutable Packwiz snapshots. Experimental candidates may still require fresh Prism import, public-download, graphics and multiplayer qualification.</p>'
        '<p><strong>No stable root update channel is published.</strong> Source CI does not activate a playable update. Each listed snapshot comes from its approved Git tag and exact hash.</p>'
        '<table><thead><tr><th>Version</th><th>Status</th><th>Files</th><th>Pack SHA-256</th></tr></thead><tbody>'+entries+'</tbody></table>'
        '<p><a href="https://github.com/Kgray44/a-world-for-two/releases">Release downloads</a> · '
        '<a href="https://github.com/Kgray44/a-world-for-two/blob/main/docs/INSTALL.md">Install guide</a> · '
        '<a href="https://github.com/Kgray44/a-world-for-two/blob/main/docs/RELEASING.md">Qualification policy</a></p></html>\n')


def build(repo=REPO,catalog=None,output=None):
    repo=Path(repo).resolve();catalog=Path(catalog or repo/'catalog/publication.json')
    if output is None:raise UserError('Choose a new private output directory outside the source repository')
    output=Path(output).resolve()
    if output.exists() or output.is_relative_to(repo):raise UserError('Publication output must be new and outside the source repository')
    approval=approved_catalog(catalog)
    # Resolve every tag before creating any public output. Archive immutable
    # commit IDs after resolution so a concurrently moved tag cannot win a race.
    resolved=[(row,git_commit(repo,row['git_tag'])) for row in approval['snapshots']]
    reserve_local(output,len(resolved))
    output.parent.mkdir(parents=True,exist_ok=True)
    work=output.parent/('.awft-publication-'+uuid.uuid4().hex);work.mkdir()
    stage=work/'public';stage.mkdir();rows=[]
    try:
        for number,(row,commit) in enumerate(resolved):
            # Recheck per bounded writer; this also covers long multi-tag runs.
            reserve_local(output,len(resolved))
            archive=work/(str(number)+'.tar');archive_bytes=archive_tag(repo,commit,archive)
            extracted=work/str(number);payload_bytes=extract_tag(archive,extracted)
            _,files=validate_snapshot(extracted,row)
            import tomllib
            members,exclusion_proofs=snapshot_payload(extracted/'packwiz',
                tomllib.loads((extracted/'packwiz/index.toml').read_text()),row)
            destination=stage/'releases'/row['version']
            destination.mkdir(parents=True)
            for relative in sorted(members):
                target=destination/relative;target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(extracted/'packwiz'/relative,target)
            shutil.copyfile(extracted/'catalog/lock.json',destination/'lock.json')
            rows.append(row|{'git_commit':commit,'files':files,'archive_bytes':archive_bytes,'payload_bytes':payload_bytes,
                             'tagged_metadata_exclusions_verified':exclusion_proofs})
        if (stage/'pack.toml').exists() or (stage/'index.toml').exists():raise UserError('Stable root manifest must remain absent')
        (stage/'index.html').write_text(index_html(rows),encoding='utf-8')
        (stage/'.nojekyll').touch()
        write_json(stage/'publication.json',{'format':'awft-publication:1','stable':None,
                   'snapshots':[{k:row[k] for k in ('version','git_tag','git_commit','pack_sha256','status')} for row in rows]})
        if output.exists():raise UserError('Publication output appeared during packaging; preserve it and choose another path')
        stage.rename(output)
        receipt={'at':utcnow(),'output':str(output),'staging_retained':str(work),'snapshots':rows,
                 'stable_root_manifest':'absent','status':'Built approved static snapshots; no deployment performed'}
        write_json(work/'receipt.json',receipt)
        return receipt
    except Exception as error:
        write_json(work/'failure.json',{'at':utcnow(),'error':str(error),'public_output_created':output.exists(),
                   'boundary':'Owned failed staging retained; no deployment performed'})
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,default=REPO)
    parser.add_argument('--catalog',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(build(args.repo,args.catalog,args.output),indent=2))
