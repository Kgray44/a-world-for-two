"""Bounded offline API/registry contract checks; never launch a game or server."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import time

from control_room.common import REPO, UserError, atomic_write, digest, utcnow

JDK=Path(r'C:\Program Files\Java\jdk-21.0.10\bin')
GUARD=Path(r'C:\Users\kkids\AppData\Local\AeroStorageWatch\ReserveGuard.ps1')
FILES={
    'hybrid_aquatic-neoforge-1.21.1-1.7.4.jar':'c71f952db5416b019007c71175c151c443a1724acce20e1a0ed7be9e4c88a68061b5cf18d57625414941928e5a21ac1f141ca922cc45ff627ecad9039e5f2a2b',
    'Distant Horizons SeedGen 0.9.1 for 1.21.1 NeoForge.jar':'4b0bbb0426d0d600fcef2deb0580f458bbf16b90440b84b9d28fe377a3107cf22ff9f166eec85b802cb5386d5af39d5b0a12ac6bf7ca04fad427206d1405c61d',
}
SOURCES=('compat/control-bridge/src/worldfortwo/bridge/HybridAquaticSeedgenCompat.java',
    'compat/control-bridge/src/worldfortwo/bridge/mixin/HybridAquaticSeedgenMixin.java',
    'compat/seedgen/HybridAquaticSeedgenProbe.java')


def run(home):
    home=Path(home).resolve()
    if home!=Path(r'D:\A World for Two'):raise UserError('Use the named owned runtime for this private offline probe')
    for name,sha in FILES.items():
        if digest(home/'server/mods'/name,'sha512')!=sha:raise UserError('Pinned offline probe dependency changed: '+name)
    command=['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(GUARD),
        '-EstimatedCBytes',str(16*1024**2),'-EstimatedDBytes',str(32*1024**2)]
    flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
    reserve=subprocess.run(command,capture_output=True,text=True,timeout=30,creationflags=flags)
    admitted=json.loads(reserve.stdout.strip().splitlines()[-1])
    if reserve.returncode or not admitted.get('allowed'):raise UserError('Offline probe reserve refused')
    work=home/'staging'/('seedgen-hybrid-contract-'+str(time.time_ns()));work.mkdir();(work/'classes').mkdir()
    libraries=home/'server/libraries';named=sorted((libraries/'net/minecraft/server').rglob('*-srg.jar'))
    if len(named)!=1:raise UserError('Require the unique named Minecraft API before the obfuscated intermediates')
    launch=libraries/'net/neoforged/neoforge/21.1.262/win_args.txt'
    if not launch.is_file() or launch.stat().st_size>128*1024:raise UserError('Exact bounded installed launch list required')
    lines=launch.read_text().splitlines();legacy=[v.split('=',1)[1] for v in lines if v.startswith('-DlegacyClassPath=')]
    modules=[v[3:] for v in lines if v.startswith('-p ')]
    if len(legacy)!=1 or len(modules)!=1:raise UserError('Installed runtime dependency lists are ambiguous')
    dependencies=[]
    for relative in (modules[0]+';'+legacy[0]).split(';'):
        dependency=(home/'server'/relative).resolve()
        if not dependency.is_relative_to(libraries.resolve()) or not dependency.is_file():raise UserError('A selected runtime dependency escaped libraries')
        dependencies.append(dependency)
    resources=named[0].with_name(named[0].name.replace('-srg.jar','-extra.jar'))
    universal=libraries/'net/neoforged/neoforge/21.1.262/neoforge-21.1.262-universal.jar'
    if not resources.is_file() or not universal.is_file():raise UserError('Named runtime resources or exact NeoForge runtime missing')
    # Installer intermediates and old tool Guava/ASM caches are not runtime.
    jars=list(dict.fromkeys([*named,resources,universal,*dependencies,*sorted((home/'server/mods').glob('*.jar'))]))
    cp=os.pathsep.join(p.as_posix() for p in jars)
    def invoke(binary,args,log):
        try:
            result=subprocess.run([str(JDK/binary),*args],cwd=work,capture_output=True,text=True,
                timeout=60,creationflags=flags)
        except subprocess.TimeoutExpired as error:
            atomic_write(work/log,'TIMEOUT; offline child killed by subprocess.run. Preserve this failed stage.\n')
            raise UserError('Offline contract timed out; preserve '+str(work)) from error
        atomic_write(work/log,result.stdout+result.stderr)
        return result.returncode
    javac=work/'javac.args'
    atomic_write(javac,'-proc:none\n--release\n21\n-classpath\n"'+cp+'"\n-d\n"'+(work/'classes').as_posix()+'"\n'+
        '\n'.join('"'+(REPO/name).as_posix()+'"' for name in SOURCES)+'\n')
    compiled=invoke('javac.exe',['-J-Xms32m','-J-Xmx256m','-J-XX:-UsePerfData','@'+str(javac)],'javac.log')
    receipt={'format':'awft-seedgen-hybrid-offline:1','at':utcnow(),'source_sha256':{name:digest(REPO/name) for name in SOURCES},
        'dependency_sha512':FILES,'reserve':admitted,'compilation_exit':compiled,
        'native_hybrid_execution':'NOT RUN; requires initialized NeoForge ModList',
        'strict_paired_fingerprint':'pending actual authorized runtime comparison'}
    if compiled:
        atomic_write(work/'result.json',json.dumps(receipt,indent=2)+'\n')
        raise UserError('Offline compilation failed; preserved '+str(work))
    java=work/'java.args'
    atomic_write(java,'-Xms32M\n-Xmx384M\n-XX:-UsePerfData\n"-Djava.io.tmpdir='+work.as_posix()+'"\n'+
        '"-XX:ErrorFile='+(work/'hs_err_pid%p.log').as_posix()+'"\n-classpath\n"'+(work/'classes').as_posix()+os.pathsep+cp+'"\n'+
        'worldfortwo.bridge.HybridAquaticSeedgenProbe\n'+
        '\n'.join('"'+(home/'server/mods'/name).as_posix()+'"' for name in FILES)+'\n')
    receipt['probe_exit']=invoke('java.exe',['@'+str(java)],'probe.log')
    receipt['status']='PASS offline Minecraft contracts and installed bytecode tables' if not receipt['probe_exit'] else 'FAIL offline contract; preserve receipt'
    atomic_write(work/'result.json',json.dumps(receipt,indent=2)+'\n')
    if receipt['probe_exit']:raise UserError('Offline contract failed; preserved '+str(work))
    return {'directory':str(work),'status':receipt['status'],'native_hybrid_execution':receipt['native_hybrid_execution'],
        'strict_paired_fingerprint':receipt['strict_paired_fingerprint']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--home',type=Path,required=True)
    print(json.dumps(run(parser.parse_args().home),indent=2))
