"""Bounded offline API compile and policy fixture. No Minecraft/modloader/world execution."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from control_room.common import digest, utcnow
from tools.playtest import guard
from tools.performance_windows import memory_pressure
from native_api import inspect, ARTIFACTS


def admission():
    state = memory_pressure()
    if not state.get('available') or min(state['physical_available_bytes'], state['commit_headroom_bytes']) < 1536*1024**2:
        raise ValueError('Host RAM/commit guard refused before owned JVM')
    return state


def run(home):
    source = Path(__file__).resolve().parent
    home = Path(home).resolve()
    if home.parent != Path('D:/A World for Two/staging/world-tests').resolve():
        raise ValueError('Exact owned private staging home required')
    reserve = guard(2*1024**2, 64*1024**2)
    initial_memory = admission()
    api = inspect(home/'server/mods')
    libraries = home/'server/libraries'
    named = list((libraries/'net/minecraft/server').rglob('*-srg.jar'))
    bridges = list((home/'server/mods').glob('awft-control-bridge-*.jar'))
    if len(named) != 1 or len(bridges) != 1:
        raise ValueError('One actual installed named API and bridge reference required')
    recipe = libraries/'net/neoforged/neoforge/21.1.262/win_args.txt'
    lines = recipe.read_text().splitlines()
    legacy = [line.split('=', 1)[1] for line in lines if line.startswith('-DlegacyClassPath=')]
    modules = [line[3:] for line in lines if line.startswith('-p ')]
    if len(legacy) != 1 or len(modules) != 1:
        raise ValueError('Exact native dependency order required')
    deps = []
    for name in (modules[0]+';'+legacy[0]).split(';'):
        path = (home/'server'/name).resolve()
        if not path.is_relative_to(libraries.resolve()) or not path.is_file():
            raise ValueError('Dependency escaped installed libraries')
        deps.append(path)
    universal = libraries/'net/neoforged/neoforge/21.1.262/neoforge-21.1.262-universal.jar'
    work = home/'staging'/('moonlight-init-offline-'+str(time.time_ns()))
    work.mkdir(); (work/'classes').mkdir(); (work/'tmp').mkdir()
    sources = sorted(source.glob('*.java'))
    if not 1 <= len(sources) <= 20 or any(p.stat().st_size > 128*1024 for p in sources):
        raise ValueError('Bounded proposal sources required')
    receipt = {'format': 'awft-moonlight-init-offline:1', 'at': utcnow(), 'passed': False,
               'native_world_actions': False, 'modloader_or_mixin_execution': False,
               'strict_parity_proved': False, 'reserve': reserve, 'initial_memory': initial_memory,
               'source_sha256': {p.name: digest(p) for p in sources},
               'reference_bridge_sha256': digest(bridges[0]), 'reference_bridge_name': bridges[0].name,
               'runtime_recipe_sha256': digest(recipe), 'named_api_sha256': digest(named[0]),
               'neoforge_universal_sha256': digest(universal), 'heap_MiB': 256, 'processors': 2}
    jdk = Path('C:/Program Files/Java/jdk-21.0.10/bin')
    env = {k: v for k, v in os.environ.items() if k not in ('JAVA_TOOL_OPTIONS', '_JAVA_OPTIONS', 'JDK_JAVA_OPTIONS')}
    env.update(TEMP=str(work/'tmp'), TMP=str(work/'tmp'))

    def invoke(binary, arguments, log):
        admission()
        result = subprocess.run([str(jdk/binary), *arguments], cwd=work, env=env, capture_output=True,
                                timeout=60, creationflags=subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS)
        raw = result.stdout+result.stderr
        if len(raw) > 2*1024**2:
            raise ValueError('Offline diagnostic output exceeded bound')
        (work/log).write_bytes(raw)
        return result.returncode

    try:
        with zipfile.ZipFile(universal) as jar:
            info = jar.getinfo('META-INF/jarjar/mixinextras-neoforge-0.5.5.jar')
            if not 0 < info.file_size <= 2*1024**2:
                raise ValueError('Bounded installed MixinExtras required')
            extras = work/'mixinextras-native.jar'; extras.write_bytes(jar.read(info))
        receipt['mixinextras_sha256'] = digest(extras)
        cp = os.pathsep.join(p.as_posix() for p in dict.fromkeys([
            *[home/'server/mods'/row[0] for row in ARTIFACTS.values()], bridges[0], *named,
            named[0].with_name(named[0].name.replace('-srg.jar', '-extra.jar')), universal, extras, *deps]))
        if len(cp) > 65536:
            raise ValueError('Finite installed API classpath exceeded')
        (work/'native-api.json').write_text(json.dumps(api, indent=2)+'\n', encoding='utf-8')
        args = work/'javac.args'
        args.write_text('-proc:none\n--release\n21\n-Xmaxerrs\n20\n-classpath\n"'+cp+'"\n-d\n"'+(work/'classes').as_posix()+'"\n'+
                        '\n'.join('"'+p.as_posix()+'"' for p in sources)+'\n', encoding='utf-8')
        receipt['compile_exit'] = invoke('javac.exe', ['-J-Xmx256m', '-J-XX:ActiveProcessorCount=2', '-J-XX:-UsePerfData',
             '-J-Djava.io.tmpdir='+str(work/'tmp'), '-J-XX:ErrorFile='+str(work/'hs_err_pid%p.log'), '@'+str(args)], 'javac.log')
        if receipt['compile_exit']:
            raise RuntimeError('Original API compile failed; retained javac.log')
        # Fixture runs the small Java policy only. No mod classes enter its classpath.
        receipt['budget_fixture_exit'] = invoke('java.exe', ['-Xmx64m', '-XX:ActiveProcessorCount=2', '-XX:-UsePerfData',
              '-Djava.io.tmpdir='+str(work/'tmp'), '-XX:ErrorFile='+str(work/'hs_err_pid%p.log'),
              '-cp', str(work/'classes'), 'worldfortwo.bridge.MoonlightBudgetProbe'], 'budget.log')
        if receipt['budget_fixture_exit']:
            raise RuntimeError('Policy regression fixture failed; retained budget.log')
        receipt['passed'] = True
    except BaseException as error:
        receipt['failure'] = type(error).__name__+': '+str(error)
        raise
    finally:
        (work/'result.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
    return {'output': str(work), 'passed': True, 'receipt_sha256': digest(work/'result.json')}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', required=True, type=Path)
    print(json.dumps(run(parser.parse_args().home), indent=2))
