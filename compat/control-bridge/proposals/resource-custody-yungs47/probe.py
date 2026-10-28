"""Bounded original offline YUNG native-pack probe; never launch a game or loader."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from control_room.common import digest, utcnow
from tools.playtest import guard


def run(home):
    home=Path(home).resolve();source=Path(__file__).resolve().parent
    if not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests').resolve()):
        raise ValueError('An owned private D staging home is required')
    reserve=guard(1024**2,32*1024**2)
    jar=home/'server/mods/YungsApi-1.21.1-NeoForge-5.1.9.jar'
    if jar.stat().st_size!=413763 or digest(jar)!='375e0b2f988ab4f5bde182166c0f0b102377adc8f823660c24ade08b0b3cde56':
        raise ValueError('Exact installed native YUNG API required')
    # Use the installed runtime dependency order, not all cached JARs: old
    # historical Guava copies are legitimate cache entries but not this runtime.
    libraries=home/'server/libraries'
    named=list((libraries/'net/minecraft/server').rglob('*-srg.jar'))
    if len(named)!=1:raise ValueError('One installed named Minecraft server API required')
    win=libraries/'net/neoforged/neoforge/21.1.262/win_args.txt'
    lines=win.read_text().splitlines()
    legacy=[line.split('=',1)[1] for line in lines if line.startswith('-DlegacyClassPath=')]
    modules=[line[3:] for line in lines if line.startswith('-p ')]
    if len(legacy)!=1 or len(modules)!=1:raise ValueError('Exact installed runtime classpath required')
    deps=[]
    for relative in (modules[0]+';'+legacy[0]).split(';'):
        path=(home/'server'/relative).resolve()
        if not path.is_relative_to(libraries.resolve()) or not path.is_file():raise ValueError('Runtime dependency escaped installed libraries')
        deps.append(path)
    universal=libraries/'net/neoforged/neoforge/21.1.262/neoforge-21.1.262-universal.jar'
    cp=os.pathsep.join(p.as_posix() for p in dict.fromkeys([jar,*named,named[0].with_name(named[0].name.replace('-srg.jar','-extra.jar')),universal,*deps]))
    if len(cp)>65536:raise ValueError('Finite compiler classpath required')
    work=home/'staging'/('resource-yungs47-offline-'+str(time.time_ns()))
    work.mkdir();classes=work/'classes';classes.mkdir();(work/'tmp').mkdir()
    sources=[source/name for name in ('LithostitchedSeedgenResources.java','YungLocatePackCustody.java','YungRuntimePackProbe.java')]
    result={'format':'awft-original-yung-custody-probe:1','created':utcnow(),'passed':False,
        'scope':'untransformed installed APIs only; no modloader/game/Level/network/accounts',
        'native_world_actions':False,'reserve':reserve,'provider_jar_sha256':digest(jar),
        'runtime_recipe_sha256':digest(win),'named_api_sha256':digest(named[0]),
        'source_sha256':{p.name:digest(p) for p in sources}}
    jdk=Path(r'C:\Program Files\Java\jdk-21.0.10\bin')
    env={k:v for k,v in os.environ.items() if k not in ('JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVA_OPTIONS')}
    flags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS
    def invoke(binary,args,name):
        proc=subprocess.run([str(jdk/binary),*args],cwd=work,capture_output=True,timeout=60,env=env,creationflags=flags)
        raw=proc.stdout+proc.stderr
        if len(raw)>2*1024**2:raise ValueError('Bounded offline log exceeded')
        (work/name).write_bytes(raw)
        return proc.returncode
    try:
        args=work/'javac.args'
        args.write_text('-proc:none\n--release\n21\n-Xmaxerrs\n20\n-classpath\n"'+cp+'"\n-d\n"'+classes.as_posix()+'"\n'+
                        '\n'.join('"'+p.as_posix()+'"' for p in sources)+'\n',encoding='utf-8')
        result['compile_exit']=invoke('javac.exe',['-J-Xmx256m','-J-XX:ActiveProcessorCount=2','-J-XX:-UsePerfData','@'+str(args)],'javac.log')
        if result['compile_exit']:raise RuntimeError('Original proposal compile failed; retained javac.log')
        args=work/'java.args'
        args.write_text('-Xmx256m\n-XX:ActiveProcessorCount=2\n-XX:-UsePerfData\n"-Djava.io.tmpdir='+(work/'tmp').as_posix()+
            '"\n"-XX:ErrorFile='+(work/'hs_err_pid%p.log').as_posix()+'"\n-classpath\n"'+classes.as_posix()+os.pathsep+cp+
            '"\nworldfortwo.bridge.YungRuntimePackProbe\n"'+jar.as_posix()+'"\n',encoding='utf-8')
        result['probe_exit']=invoke('java.exe',['@'+str(args)],'probe.log')
        if result['probe_exit']:raise RuntimeError('Original exact native pack probe failed; retained probe.log')
        result['passed']=True
    except BaseException as failure:
        result['failure']=type(failure).__name__+': '+str(failure)
        raise
    finally:
        (work/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return {'directory':str(work),'result_sha256':digest(work/'result.json'),'passed':True}


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home',type=Path,required=True)
    print(json.dumps(run(**vars(parser.parse_args())),indent=2))
