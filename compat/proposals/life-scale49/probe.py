"""Bounded actual Java21/API compile and pure transaction probe; no game/Level."""
from pathlib import Path
import json,os,subprocess,sys,time
import psutil

sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from control_room.common import digest,utcnow
from tools.playtest import guard


def run(home):
    home=Path(home).resolve();source=Path(__file__).resolve().parent
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve():raise ValueError('Exact owned private stage required')
    reserve=guard(2*1024**2,64*1024**2)
    available=psutil.virtual_memory().available
    if available<=1536*1024**2:raise ValueError('RAM guard refused before output or process')
    bridge=home/'server/mods/awft-control-bridge-0.6.34.jar'
    if digest(bridge)!='071fe778b27c9450c6a9a7b602825ee2ff19bfcdba9f23ba3cb24302bd6b4b1d':raise ValueError('Exact unchanged installed48 API required')
    libraries=home/'server/libraries';named=list((libraries/'net/minecraft/server').rglob('*-srg.jar'))
    if len(named)!=1:raise ValueError('Exact installed named Minecraft API required')
    recipe=libraries/'net/neoforged/neoforge/21.1.262/win_args.txt'
    lines=recipe.read_text().splitlines();legacy=[v.split('=',1)[1]for v in lines if v.startswith('-DlegacyClassPath=')];modules=[v[3:]for v in lines if v.startswith('-p ')]
    if len(legacy)!=1 or len(modules)!=1:raise ValueError('Actual native dependency order required')
    dependencies=[]
    for name in(modules[0]+';'+legacy[0]).split(';'):
        path=(home/'server'/name).resolve()
        if not path.is_relative_to(libraries.resolve())or not path.is_file():raise ValueError('Ordinary installed dependency required')
        dependencies.append(path)
    universal=libraries/'net/neoforged/neoforge/21.1.262/neoforge-21.1.262-universal.jar'
    cp=os.pathsep.join(p.as_posix()for p in dict.fromkeys([bridge,*named,named[0].with_name(named[0].name.replace('-srg.jar','-extra.jar')),universal,*dependencies]))
    if len(cp)>65536:raise ValueError('Finite API classpath exceeded')
    output=home/'staging'/('life-scale49-offline-'+str(time.time_ns()));output.mkdir();classes=output/'classes';classes.mkdir();(output/'tmp').mkdir()
    sources=[source/n for n in('NativeHabitatLifeSupport.java','ScaledLifeBudget.java','LifeScaleBudgetProbe.java')]
    record={'format':'awft-scaled-life-API-probe:1','created':utcnow(),'passed':False,'available_RAM_bytes':available,
        'installed_bridge_sha256':digest(bridge),'runtime_recipe_sha256':digest(recipe),'source_hashes':{p.name:digest(p)for p in sources},
        'reserve_guard':reserve,'heap_MiB':256,'CPUs':2,'native_world_loader_or_network_actions':0}
    jdk=Path(r'C:\Program Files\Java\jdk-21.0.10\bin')
    env={k:v for k,v in os.environ.items()if k not in('JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVA_OPTIONS')}
    def invoke(binary,arguments,name):
        if psutil.virtual_memory().available<=1536*1024**2:raise ValueError('RAM guard refused next owned process')
        process=subprocess.run([str(jdk/binary),*arguments],cwd=output,env=env,capture_output=True,timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
        data=process.stdout+process.stderr
        if len(data)>2*1024**2:raise ValueError('Finite process output exceeded')
        (output/name).write_bytes(data);return process.returncode
    try:
        args=output/'javac.args';args.write_text('-proc:none\n--release\n21\n-Xmaxerrs\n20\n-classpath\n"'+cp+'"\n-d\n"'+classes.as_posix()+'"\n'+'\n'.join('"'+p.as_posix()+'"'for p in sources)+'\n')
        record['compile_exit']=invoke('javac.exe',['-J-Xmx256m','-J-XX:ActiveProcessorCount=2','-J-XX:-UsePerfData','@'+str(args)],'javac.log')
        if record['compile_exit']:raise RuntimeError('Isolated exact API compile failed; original sources/log retained')
        args=output/'java.args';args.write_text('-Xmx256m\n-XX:ActiveProcessorCount=2\n-XX:-UsePerfData\n"-Djava.io.tmpdir='+(output/'tmp').as_posix()+'"\n"-XX:ErrorFile='+(output/'hs_err_pid%p.log').as_posix()+'"\n-classpath\n"'+classes.as_posix()+os.pathsep+cp+'"\nworldfortwo.bridge.LifeScaleBudgetProbe\n')
        record['probe_exit']=invoke('java.exe',['@'+str(args)],'probe.log')
        if record['probe_exit']:raise RuntimeError('Pure transaction probe failed; original evidence retained')
        record['passed']=True
    except BaseException as error:
        record['error']=str(error)
        saved=output/'failed-source-copies';saved.mkdir()
        for path in sources:
            if digest(path)!=record['source_hashes'][path.name]:raise RuntimeError('Source changed during failed probe')
            (saved/path.name).write_bytes(path.read_bytes())
        raise
    finally:
        (output/'result.json').write_text(json.dumps(record,indent=2)+'\n')
        print(json.dumps({'output':str(output),'result_sha256':digest(output/'result.json'),'passed':record['passed']},indent=2))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--home',required=True);run(parser.parse_args().home)
