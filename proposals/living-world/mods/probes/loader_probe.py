"""Bounded real NeoForge loader probe, with EULA explicitly false and no world acceptance.

Existing installed libraries are read through absolute paths. No installer, account,
world or public channel is touched. All generated files stay in a fresh output folder.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from control_room.common import UserError, digest
from living_world.defaults import configuration
from tools.build_living_world import PINS
from tools.living_world_upstream import bundle_files, reserve_allocation


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed-home',type=Path,required=True)
    parser.add_argument('--dependencies',type=Path,required=True)
    parser.add_argument('--adapter',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    output=args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'.local'):
        raise UserError('Use a fresh output directory under this worktree .local')
    for parent in output.parents:
        if parent.is_symlink() or parent.is_junction():
            raise UserError('Linked output paths refused')
    installed=args.installed_home.resolve()/'server'
    original=(installed/'libraries/net/neoforged/neoforge/21.1.262/win_args.txt').read_text()
    library=str(installed/'libraries').replace('\\','/')
    arguments=[]
    for line in original.splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        line=line.replace('libraries/',library+'/').replace('-DlibraryDirectory=libraries','-DlibraryDirectory='+library)
        if line.startswith('-') and ' ' in line and not line.startswith('-D'):
            arguments.extend(line.split(' ',1))
        else:
            arguments.append(line)
    inputs=[]
    for name,expected in PINS.items():
        source=args.dependencies/name
        if not source.is_file() or digest(source)!=expected:
            raise UserError('Compile dependency differs: '+name)
        inputs.append(source)
    if not args.adapter.is_file() or args.adapter.stat().st_size>1024**2:
        raise UserError('Owned adapter missing or oversized')
    # Reserve a finite 64 MiB on C, and no D writes. Probe refuses all other destinations.
    if output.drive.upper()!='C:':
        raise UserError('This reviewed probe allocates only on C:')
    guard=Path(r'C:\Users\kkids\AppData\Local\AeroStorageWatch\ReserveGuard.ps1')
    checked=subprocess.run(['powershell.exe','-NoProfile','-File',str(guard),'-EstimatedCBytes','67108864','-EstimatedDBytes','0'],capture_output=True,text=True,timeout=20)
    if checked.returncode or json.loads(checked.stdout).get('allowed') is not True:
        raise UserError('Storage guard refused probe allocation')
    output.mkdir()
    server=output/'server';server.mkdir();(server/'mods').mkdir();(server/'temp').mkdir()
    for source in [*inputs,args.adapter]:
        shutil.copyfile(source,server/'mods'/source.name)
    for relative,content in bundle_files(configuration()['districts']).items():
        if relative.startswith('config/'):
            target=server/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(content,encoding='utf8')
    (server/'config/awft-living-world.json').write_text(json.dumps(configuration()),encoding='utf8')
    (server/'eula.txt').write_text('eula=false\n',encoding='ascii')
    (server/'server.properties').write_text('server-ip=127.0.0.1\nserver-port=25587\nenable-rcon=false\nonline-mode=true\nlevel-name=NeverCreated\n',encoding='ascii')
    java=Path(r'C:\Program Files\Java\jdk-21.0.10\bin\java.exe')
    command=[str(java),'-Xms128m','-Xmx768m','-XX:ActiveProcessorCount=2','-XX:-HeapDumpOnOutOfMemoryError',
        '-Djava.awt.headless=true','-Dmixin.debug.export=true','-Djava.io.tmpdir='+str(server/'temp'),*arguments,'nogui']
    (output/'command.json').write_text(json.dumps(command,indent=2),encoding='utf8')
    started=time.monotonic();total=[0];overflow=threading.Event()
    process=subprocess.Popen(command,cwd=server,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW)
    identity={'pid':process.pid,'created_at':time.time(),'cwd':str(server)}
    (output/'owner.json').write_text(json.dumps(identity,indent=2),encoding='utf8')
    def collect():
        with (output/'stdout.txt').open('wb') as target:
            while True:
                block=process.stdout.read(8192)
                if not block:
                    break
                total[0]+=len(block)
                if total[0]>2*1024**2:
                    overflow.set();break
                target.write(block)
    reader=threading.Thread(target=collect,daemon=True);reader.start();reason='exited'
    while process.poll() is None:
        size=sum(p.stat().st_size for p in output.rglob('*') if p.is_file())
        if time.monotonic()-started>90 or size>48*1024**2 or overflow.is_set():
            reason='bounded_probe_stopped';process.terminate();break
        time.sleep(.25)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill();process.wait(timeout=10)
    reader.join(5)
    text=(output/'stdout.txt').read_text(encoding='utf8',errors='replace')
    eula=(server/'eula.txt').read_text().strip()
    transformed=list((server/'.mixin.out').rglob('*.class'))
    receipt={'tier':'real NeoForge loader only; not server/world/gameplay acceptance','returncode':process.returncode,
             'elapsed_seconds':round(time.monotonic()-started,3),'terminal':reason,'process_terminal':process.poll() is not None,
             'adapter_sha256':digest(args.adapter),'eula':eula,'world_created':(server/'NeverCreated').exists(),
             'mixin_exported_classes':[p.relative_to(server).as_posix() for p in transformed],
             'eula_refusal_observed':'eula' in text.lower() and ('agree' in text.lower() or 'agreement' in text.lower()),
             'inputs':PINS}
    (output/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
    print(json.dumps(receipt,indent=2))
    print(text[-16000:])
    if eula!='eula=false' or receipt['world_created']:
        raise UserError('Probe boundary was not preserved; inspect all retained files')


if __name__=='__main__':
    main()
