"""Bounded actual installed resource APIs; no modloader, game, world or network."""
from pathlib import Path
import argparse, json, os, subprocess, time
from control_room.common import REPO, UserError, digest, utcnow
from tools.playtest import guard

JDK = Path(r'C:\Program Files\Java\jdk-21.0.10\bin')
SOURCES = ['compat/control-bridge/proposals/resource-custody43/LithostitchedSeedgenResources.java',
           'compat/seedgen/ResourceCustody43Probe.java']

def run(home):
    home = Path(home).resolve()
    if not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests')):
        raise UserError('Owned private staging only')
    reserve = guard(1024**2, 32*1024**2)
    work = home/'staging'/('resource-custody43-offline-'+str(time.time_ns()))
    work.mkdir(); (work/'classes').mkdir()
    libraries = home/'server/libraries'
    named = sorted((libraries/'net/minecraft/server').rglob('*-srg.jar'))
    if len(named) != 1:
        raise UserError('One exact installed named API required')
    launch = (libraries/'net/neoforged/neoforge/21.1.262/win_args.txt').read_text().splitlines()
    legacy = [v.split('=', 1)[1] for v in launch if v.startswith('-DlegacyClassPath=')]
    modules = [v[3:] for v in launch if v.startswith('-p ')]
    if len(legacy) != 1 or len(modules) != 1:
        raise UserError('Exact installed dependency list required')
    deps = []
    for relative in (modules[0]+';'+legacy[0]).split(';'):
        path = (home/'server'/relative).resolve()
        if not path.is_relative_to(libraries.resolve()) or not path.is_file():
            raise UserError('Dependency escaped installed libraries')
        deps.append(path)
    universal = libraries/'net/neoforged/neoforge/21.1.262/neoforge-21.1.262-universal.jar'
    if not universal.is_file():
        raise UserError('Exact installed NeoForge resource API required')
    cp = os.pathsep.join(p.as_posix() for p in dict.fromkeys([
        *named, named[0].with_name(named[0].name.replace('-srg.jar', '-extra.jar')), universal, *deps]))
    def write(name, value):
        if len(value.encode('utf-8')) > 2*1024**2:
            raise UserError('Finite original probe output exceeded')
        with (work/name).open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(value)
    def invoke(binary, args, name):
        try:
            result = subprocess.run([str(JDK/binary), *args], cwd=work, capture_output=True,
                                    text=True, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
        except subprocess.TimeoutExpired:
            write(name, 'TIMEOUT: original owned offline process terminated; failed receipt retained\n')
            raise
        write(name, result.stdout+result.stderr)
        return result.returncode
    write('javac.args', '-proc:none\n--release\n21\n-classpath\n"'+cp+'"\n-d\n"'+
          (work/'classes').as_posix()+'"\n'+'\n'.join('"'+(REPO/name).as_posix()+'"' for name in SOURCES))
    result = {'at': utcnow(), 'reserve': reserve, 'sources': {name: digest(REPO/name) for name in SOURCES},
              'api_sha256': digest(named[0]), 'neoforge_sha256': digest(universal),
              'evidence_scope': 'untransformed installed APIs only; no native modloader acceptance'}
    result['compile_exit'] = invoke('javac.exe', ['-J-Xmx256m', '-J-XX:-UsePerfData', '@'+str(work/'javac.args')], 'javac.log')
    if result['compile_exit'] == 0:
        write('java.args', '-Xms32m\n-Xmx256m\n-XX:-UsePerfData\n"-Djava.io.tmpdir='+work.as_posix()+
              '"\n"-XX:ErrorFile='+(work/'hs_err_pid%p.log').as_posix()+'"\n-classpath\n"'+
              (work/'classes').as_posix()+os.pathsep+cp+'"\nworldfortwo.bridge.ResourceCustody43Probe\n')
        result['probe_exit'] = invoke('java.exe', ['@'+str(work/'java.args')], 'probe.log')
    result['status'] = 'PASS offline exact APIs only' if result['compile_exit'] == result.get('probe_exit') == 0 else 'FAIL preserved'
    write('result.json', json.dumps(result, indent=2)+'\n')
    return {'directory': str(work), 'status': result['status'], 'result_sha256': digest(work/'result.json')}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, required=True)
    result = run(parser.parse_args().home)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['status'].startswith('PASS') else 1)
