"""Pinned native bytecode/API and offline pack-order fixture; never reload a game/cache."""
from pathlib import Path
import hashlib,json,os,struct,subprocess,sys,time,zipfile
import psutil

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from control_room.common import digest,utcnow
from tools.playtest import guard
from tools.artistic_eastern_support_protocol import class_parts,instructions

MOON='4a9f15108607cc70273f8a0b6eb24e1e99af8eef44bc3ae8681767ca7ce21b0f'
SEED='58469f92f7cf13ff3c2928659ce1a57d7d05314b30e0779cb187b6fbfdb43b4e'

def run(home):
    home=Path(home).resolve();source=Path(__file__).resolve().parent
    if home!=Path('D:/A World for Two/staging/world-tests/20261027T053650Z-artistic').resolve():
        raise ValueError('Exact owned private API stage required')
    reserve=guard(0,16*1024**2)
    if psutil.virtual_memory().available<=1536*1024**2:raise ValueError('RAM gate refused before writer/process')
    provider=home/'server/mods/moonlight-1.21.1-3.7.2-neoforge.jar'
    seed=home/'server/mods/Distant Horizons SeedGen 0.9.1 for 1.21.1 NeoForge.jar'
    if provider.stat().st_size!=2299162 or digest(provider)!=MOON:raise ValueError('Pinned Moonlight differs')
    if seed.stat().st_size!=1355029 or digest(seed)!=SEED:raise ValueError('Pinned SeedGen differs')
    with zipfile.ZipFile(seed)as jar:
        raw=jar.read('mobius/seedrenderer/dh/ClientWorldgen.class')
    if hashlib.sha256(raw).hexdigest()!='d352c1c7fa607f2ba29eac97364eda8ed126984161386acdab693acdbebc4c19':raise ValueError('Pinned native target differs')
    cp,_,methods=class_parts(raw)
    def name(i):
        tag,value=cp[i]
        if tag==1:return value
        if tag in(7,8):return name(int.from_bytes(value,'big'))
        if tag in(9,10,11,12):
            a,b=struct.unpack('>HH',value);return name(a)+'::'+name(b)
        return repr(tag)
    code=methods['attempt','(ZZ)Lnet/minecraft/core/RegistryAccess$Frozen;']
    if hashlib.sha256(code).hexdigest()!='a59964aed4ad9e9812c971fd642762400467f4865575b30645725f0066d10aab':raise ValueError('Pinned method differs')
    calls=[(at,name(struct.unpack('>H',arg[:2])[0]))for at,op,arg in instructions(code)if op in(182,183,184,185)]
    manager=[at for at,n in calls if n=='net/minecraft/server/packs/resources/MultiPackResourceManager::<init>::(Lnet/minecraft/server/packs/PackType;Ljava/util/List;)V']
    injection=[at for at,n in calls if n=='net/minecraft/core/RegistryAccess::fromRegistryOfRegistries::(Lnet/minecraft/core/Registry;)Lnet/minecraft/core/RegistryAccess$Frozen;']
    loads=[at for at,n in calls if n.startswith('net/minecraft/resources/RegistryDataLoader::load::')]
    if manager!=[387]or injection!=[395]or loads!=[442,533]or not manager[0]<injection[0]<min(loads):raise ValueError('Native resource/registry call order differs')
    if any('executeEarlyReloadBlocking' in n for _,n in calls):raise ValueError('Native target already has an early reload; review duplicate integration')
    with zipfile.ZipFile(provider)as jar:
        entry=jar.read('net/mehvahdjukaar/moonlight/core/misc/ReloadInstanceWrapper.class')
    if len(entry)!=6448 or hashlib.sha256(entry).hexdigest()!='83a3f999f0d4887d8765e4164b7bef559d5e33eaee239db44e05280278e047b8':raise ValueError('Native lifecycle entry differs')
    _,_,entry_methods=class_parts(entry)
    method=entry_methods['executeEarlyReloadBlocking','(Lnet/minecraft/server/packs/PackType;Lnet/minecraft/server/packs/resources/ResourceManager;Lnet/mehvahdjukaar/moonlight/api/misc/IProgressTracker;)V']
    if hashlib.sha256(method).hexdigest()!='9c3a9bd530b06e46baec909b1a31d768c050883bb155830806264fc174e754ec':raise ValueError('Native early-event entry differs')
    libraries=home/'server/libraries';named=list((libraries/'net/minecraft/server').rglob('*-srg.jar'))
    if len(named)!=1:raise ValueError('Exact named native server API required')
    recipe=libraries/'net/neoforged/neoforge/21.1.262/win_args.txt';lines=recipe.read_text().splitlines()
    legacy=[r.split('=',1)[1]for r in lines if r.startswith('-DlegacyClassPath=')];modules=[r[3:]for r in lines if r.startswith('-p ')]
    if len(legacy)!=1 or len(modules)!=1:raise ValueError('Exact installed dependency order required')
    dependencies=[]
    for text in(modules[0]+';'+legacy[0]).split(';'):
        path=(home/'server'/text).resolve()
        if not path.is_relative_to(libraries.resolve())or not path.is_file():raise ValueError('Ordinary pinned runtime dependency required')
        dependencies.append(path)
    universal=libraries/'net/neoforged/neoforge/21.1.262/neoforge-21.1.262-universal.jar'
    classpath=os.pathsep.join(p.as_posix()for p in dict.fromkeys([provider,*named,named[0].with_name(named[0].name.replace('-srg.jar','-extra.jar')),universal,*dependencies]))
    if len(classpath)>65536:raise ValueError('Finite API classpath exceeded')
    output=home/'staging'/('moonlight-early-reload-offline-'+str(time.time_ns()));output.mkdir();classes=output/'classes';classes.mkdir();(output/'tmp').mkdir()
    sources=[source/n for n in('MoonlightSeedgenEarlyReload.java','SeedgenMoonlightEarlyReloadMixin.java','MoonlightEarlyReloadOrderProbe.java')]
    sources.append(ROOT/'compat/control-bridge/src/worldfortwo/bridge/MoonlightCachePackCustody.java')
    record={'format':'awft-moonlight-early-reload-offline:1','created':utcnow(),'passed':False,'reserve_guard':reserve,
        'native_jar_sha256':{'moonlight':digest(provider),'seedgen':digest(seed)},'native_call_offsets':{'manager_construct':manager,'injection':injection,'registry_loads':loads},
        'source_hashes':{p.relative_to(ROOT).as_posix():digest(p)for p in sources},'runtime_recipe_sha256':digest(recipe),
        'heap_MiB':256,'CPU':2,'native_lifecycle_executions':0,'game_world_cache_network_actions':0}
    jdk=Path('C:/Program Files/Java/jdk-21.0.10/bin');env={k:v for k,v in os.environ.items()if k not in('JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVA_OPTIONS')}
    def invoke(binary,args,log):
        if psutil.virtual_memory().available<=1536*1024**2:raise ValueError('RAM gate refused next owned process')
        result=subprocess.run([str(jdk/binary),*args],cwd=output,env=env,capture_output=True,timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
        data=result.stdout+result.stderr
        if len(data)>1024**2:raise ValueError('Finite process log exceeded')
        (output/log).write_bytes(data);return result.returncode
    try:
        args=output/'javac.args';args.write_text('-proc:none\n--release\n21\n-Xmaxerrs\n20\n-classpath\n"'+classpath+'"\n-d\n"'+classes.as_posix()+'"\n'+'\n'.join('"'+p.as_posix()+'"'for p in sources)+'\n')
        record['compile_exit']=invoke('javac.exe',['-J-Xmx256m','-J-XX:ActiveProcessorCount=2','-J-XX:-UsePerfData','-J-Djava.io.tmpdir='+(output/'tmp').as_posix(),'@'+str(args)],'javac.log')
        if record['compile_exit']:raise RuntimeError('Pinned API compile failed; original log retained')
        args=output/'java.args';args.write_text('-Xmx256m\n-XX:ActiveProcessorCount=2\n-XX:-UsePerfData\n"-Djava.io.tmpdir='+(output/'tmp').as_posix()+'"\n"-XX:ErrorFile='+(output/'hs_err_pid%p.log').as_posix()+'"\n-classpath\n"'+classes.as_posix()+os.pathsep+classpath+'"\nworldfortwo.bridge.MoonlightEarlyReloadOrderProbe\n')
        record['fixture_exit']=invoke('java.exe',['@'+str(args)],'fixture.log')
        if record['fixture_exit']:raise RuntimeError('Offline identity fixture failed; original log retained')
        record['passed']=True
    except BaseException as failure:
        record['failure']=type(failure).__name__+': '+str(failure);raise
    finally:(output/'result.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
    return {'output':str(output),'passed':True,'receipt_sha256':digest(output/'result.json')}

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--home',type=Path,required=True)
    print(json.dumps(run(parser.parse_args().home),indent=2))
