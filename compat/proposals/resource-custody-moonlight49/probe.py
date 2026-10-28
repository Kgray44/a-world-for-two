"""Bounded native resource API fixture; never start a game, loader or world."""
from pathlib import Path
import json,os,subprocess,sys,time
import psutil

sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from control_room.common import digest,utcnow
from tools.playtest import guard


def run(home):
    home=Path(home).resolve();source=Path(__file__).resolve().parent
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve():raise ValueError('Exact owned private stage required')
    reserve=guard(2*1024**2,32*1024**2)
    if psutil.virtual_memory().available<=1536*1024**2:raise ValueError('RAM guard refused before output/process')
    provider=home/'server/mods/moonlight-1.21.1-3.7.2-neoforge.jar'
    bridge=home/'server/mods/awft-control-bridge-0.6.34.jar'
    if provider.stat().st_size!=2299162 or digest(provider)!='4a9f15108607cc70273f8a0b6eb24e1e99af8eef44bc3ae8681767ca7ce21b0f':raise ValueError('Exact pinned Moonlight required')
    if digest(bridge)!='071fe778b27c9450c6a9a7b602825ee2ff19bfcdba9f23ba3cb24302bd6b4b1d':raise ValueError('Exact installed48 API bridge required')
    libraries=home/'server/libraries';named=list((libraries/'net/minecraft/server').rglob('*-srg.jar'))
    if len(named)!=1:raise ValueError('Exact named installed Minecraft API required')
    recipe=libraries/'net/neoforged/neoforge/21.1.262/win_args.txt'
    lines=recipe.read_text().splitlines();legacy=[r.split('=',1)[1]for r in lines if r.startswith('-DlegacyClassPath=')];modules=[r[3:]for r in lines if r.startswith('-p ')]
    if len(legacy)!=1 or len(modules)!=1:raise ValueError('Actual native runtime dependency order required')
    dependencies=[]
    for name in(modules[0]+';'+legacy[0]).split(';'):
        path=(home/'server'/name).resolve()
        if not path.is_relative_to(libraries.resolve())or not path.is_file():raise ValueError('Ordinary installed dependency required')
        dependencies.append(path)
    universal=libraries/'net/neoforged/neoforge/21.1.262/neoforge-21.1.262-universal.jar'
    cp=os.pathsep.join(p.as_posix()for p in dict.fromkeys([provider,bridge,*named,named[0].with_name(named[0].name.replace('-srg.jar','-extra.jar')),universal,*dependencies]))
    if len(cp)>65536:raise ValueError('Finite exact API classpath exceeded')
    output=home/'staging'/('resource-moonlight49-offline-'+str(time.time_ns()));output.mkdir();classes=output/'classes';classes.mkdir();(output/'tmp').mkdir()
    sources=[source/n for n in('MoonlightCachePackCustody.java','LithostitchedSeedgenResources.java','MoonlightRuntimePackProbe.java')]
    # Also compile the already frozen diagnostic-only LIFE proposal. It does
    # not run, replace a class in the game or change the resource fixture.
    diagnostic=source.parent/'life-spawn-diagnostics-r1/NativeHabitatLifeSupport.java'
    if diagnostic.is_file():sources.append(diagnostic)
    record={'format':'awft-moonlight-native-resource-probe:1','created':utcnow(),'passed':False,
        'provider_sha256':digest(provider),'installed_bridge_sha256':digest(bridge),'runtime_recipe_sha256':digest(recipe),
        'source_hashes':{str(p.relative_to(source.parents[2])):digest(p)for p in sources},
        'reserve_guard':reserve,'heap_MiB':256,'CPU':2,'native_world_loader_or_network_actions':0}
    jdk=Path(r'C:\Program Files\Java\jdk-21.0.10\bin')
    env={k:v for k,v in os.environ.items()if k not in('JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVA_OPTIONS')}
    def invoke(binary,arguments,log):
        if psutil.virtual_memory().available<=1536*1024**2:raise ValueError('RAM guard refused next owned process')
        run=subprocess.run([str(jdk/binary),*arguments],cwd=output,env=env,capture_output=True,timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
        data=run.stdout+run.stderr
        if len(data)>2*1024**2:raise ValueError('Bounded output exceeded')
        (output/log).write_bytes(data);return run.returncode
    try:
        args=output/'javac.args';args.write_text('-proc:none\n--release\n21\n-Xmaxerrs\n20\n-classpath\n"'+cp+'"\n-d\n"'+classes.as_posix()+'"\n'+'\n'.join('"'+p.as_posix()+'"'for p in sources)+'\n')
        record['compile_exit']=invoke('javac.exe',['-J-Xmx256m','-J-XX:ActiveProcessorCount=2','-J-XX:-UsePerfData','@'+str(args)],'javac.log')
        if record['compile_exit']:raise RuntimeError('Isolated API compile failed; original log retained')
        args=output/'java.args';args.write_text('-Xmx256m\n-XX:ActiveProcessorCount=2\n-XX:-UsePerfData\n"-Djava.io.tmpdir='+(output/'tmp').as_posix()+'"\n"-XX:ErrorFile='+(output/'hs_err_pid%p.log').as_posix()+'"\n-classpath\n"'+classes.as_posix()+os.pathsep+cp+'"\nworldfortwo.bridge.MoonlightRuntimePackProbe\n"'+provider.as_posix()+'"\n')
        record['probe_exit']=invoke('java.exe',['@'+str(args)],'probe.log')
        if record['probe_exit']:raise RuntimeError('Actual native resource fixture failed; original log retained')
        record['passed']=True
    except BaseException as error:
        record['failure']=type(error).__name__+': '+str(error);raise
    finally:(output/'result.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    return {'output':str(output),'passed':True,'receipt_sha256':digest(output/'result.json')}


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True)
    print(json.dumps(run(p.parse_args().home),indent=2))
