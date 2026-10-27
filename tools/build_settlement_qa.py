"""Build the separate, release-excluded native framebuffer QA helper."""
from __future__ import annotations

import os
import subprocess
import time
import zipfile
from pathlib import Path

from control_room.common import Layout, REPO, UserError, digest, write_json
from control_room.storage import Storage


def build(home=Path(r'D:\A World for Two')):
    layout=Layout(home)
    Storage(layout).reserve(16*1024**2)
    work=layout.staging/('settlement-qa-build-'+str(time.time_ns()))
    classes=work/'classes';classes.mkdir(parents=True)
    source=REPO/'compat/qa-client'
    named=Path(os.environ['APPDATA'])/'PrismLauncher/libraries/net/minecraft/client/1.21.1-20240808.144430/client-1.21.1-20240808.144430-srg.jar'
    if not named.is_file():raise UserError('The pinned, normally prepared client is required')
    jars=[named]+sorted((layout.server/'libraries').rglob('*.jar'))
    args=work/'javac.args'
    args.write_text('-proc:none\n--release\n21\n-classpath\n"'+os.pathsep.join(p.as_posix() for p in jars)+'"\n-d\n"'+classes.as_posix()+'"\n'+'\n'.join('"'+p.as_posix()+'"' for p in sorted((source/'src').rglob('*.java'))),encoding='utf-8')
    result=subprocess.run([r'C:\Program Files\Java\jdk-21.0.10\bin\javac.exe','-J-Xmx256m','-J-XX:ActiveProcessorCount=2','@'+str(args)],capture_output=True,text=True,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
    (work/'javac.log').write_text(result.stdout+result.stderr,encoding='utf-8')
    if result.returncode:raise UserError('Native QA compilation failed: '+result.stderr[:2000])
    target=work/'awft-settlement-qa-0.1.3.jar'
    with zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED) as archive:
        for folder in (classes,source/'resources'):
            for path in sorted(folder.rglob('*')):
                if path.is_file():archive.write(path,path.relative_to(folder).as_posix())
    write_json(work/'build.json',{'artifact':str(target),'sha256':digest(target),'release_excluded':True,
        'sources':{p.relative_to(REPO).as_posix():digest(p) for p in source.rglob('*') if p.is_file()}})
    print(target,flush=True)
    return target


if __name__=='__main__':build()
