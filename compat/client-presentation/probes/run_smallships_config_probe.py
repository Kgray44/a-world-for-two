"""Deferred, bounded actual-class probe. Never starts Minecraft or changes its files.

Default invocation reports pending without writing or launching Java. Execute only
after the owner grants a safe resource window, with a separately built 0.2.2 JAR.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import threading
import time
import tomllib
import uuid
import zipfile


REPO = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).with_name('SmallShipsConfigProbe.java')
GUARD = Path(r'C:\Users\kkids\AppData\Local\AeroStorageWatch\ReserveGuard.ps1')
JDK = Path(r'C:\Program Files\Java\jdk-21.0.10\bin')
MIB = 1024**2
STAGE_LIMIT = 16*MIB
SMALLSHIPS = ('smallships-neoforge-1.21.1-2.0.2.jar', 2815793,
              'aed11c65cd44a62309f52528727f83d05f74cced5cd93951692972273c340796')
NESTED = ('META-INF/jars/forgeconfigapiport-neoforge-21.1.0.jar', 105212,
          '355bc608ced2a7007b0f6d8108230cb26f7fbd3b7a1cee7b0c4b56eccf57b85a')
CRITICAL_LIBRARIES = {
    'net/neoforged/fancymodloader/loader/4.0.45/loader-4.0.45.jar':
        '8390398e67df23e72d85ed809685be2752c8ec545b7cbb6ad4b70fdc81e4dcd4',
    'net/neoforged/bus/8.0.5/bus-8.0.5.jar':
        '705e24f37752809499a5cd0c7dd31eaabf3d933c5d3b2060168e94e9ef62593a',
    'com/electronwill/night-config/core/3.8.3/core-3.8.3.jar':
        '971dc88c1c22085611ee1c300f5bbf8595938178e819befbb5e98c3cbd272b79',
    'com/electronwill/night-config/toml/3.8.3/toml-3.8.3.jar':
        'ccb92882264bf071e3916ab122fe5ea3e211b8ebf199201698a1324f151f928f',
    'com/google/guava/guava/32.1.2-jre/guava-32.1.2-jre.jar':
        'bc65dea7cfd9e4dacf8419d8af0e741655857d27885bb35d943d7187fc3a8fce',
    'net/neoforged/neoforge/21.1.262/neoforge-21.1.262-universal.jar':
        '4070305f97a08409d9b4e714f619f0ec2d97d29c9939ef43a89d927259942f98',
}
RUNTIME_ARGS = 'net/neoforged/neoforge/21.1.262/win_args.txt'
RUNTIME_ARGS_SHA256 = '50688960e135f97c4dbb43a15fc069586b68fc073d267cd6513ed0c702bf738b'
EXPECTED_CASES = {
    'remote-non-default-applied', 'original-remote-callback-negative-control',
    'second-remote-payload-invalidates-getter-cache', 'out-of-range-remote-value-corrected-by-real-spec',
    'wrong-type-remote-value-corrected-by-real-spec', 'pathless-server-loading-retains-values',
    'unloading-detaches-and-clears-real-cache', 'file-server-loading-runs-original-old-schema-migration',
    'file-server-reloading-runs-original-migration-and-retains-backups', 'file-client-loading-remains-original',
    'file-client-reloading-remains-original',
    'client-unloading-detaches-without-disk-callback', 'detached-loading-and-reloading-are-not-silenced',
    'missing-file-path-still-reaches-original-callback', 'common-and-other-mod-configs-remain-outside-policy',
    'unrelated-and-forged-message-path-errors-are-rethrown',
}


def digest(path, algorithm='sha256'):
    value = hashlib.new(algorithm)
    with path.open('rb') as reader:
        for chunk in iter(lambda: reader.read(MIB), b''):
            value.update(chunk)
    return value.hexdigest()


def json_write(path, value):
    encoded = (json.dumps(value, indent=2, sort_keys=True)+'\n').encode()
    if len(encoded) > MIB:
        raise RuntimeError('Probe receipt exceeds its finite allocation')
    path.write_bytes(encoded)


def stage_bytes(stage):
    return sum(path.stat().st_size for path in stage.rglob('*') if path.is_file())


def checked_inputs(home, presentation):
    if os.name != 'nt' or home.drive.upper() != 'D:':
        raise RuntimeError('Use the owned D: runtime on the reviewed Windows host')
    lock_path = REPO/'catalog/lock.json'
    if lock_path.stat().st_size > 2*MIB:
        raise RuntimeError('Lock exceeds its read bound')
    lock = json.loads(lock_path.read_text(encoding='utf-8'))
    pin = next(mod for mod in lock['mods'] if mod['slug'] == 'small-ships')
    smallships = home/'caches/mods'/SMALLSHIPS[0]
    if (pin['filename'] != SMALLSHIPS[0] or smallships.stat().st_size != SMALLSHIPS[1]
            or digest(smallships) != SMALLSHIPS[2]
            or any(digest(smallships, kind) != value for kind, value in pin['hashes'].items())):
        raise RuntimeError('The actual Small Ships JAR is not the reviewed exact lock pin')
    if not presentation.is_file() or presentation.stat().st_size > 4*MIB:
        raise RuntimeError('Provide a separately built, bounded presentation 0.2.2 JAR')
    with zipfile.ZipFile(presentation) as archive:
        if archive.getinfo('META-INF/neoforge.mods.toml').file_size > 65536:
            raise RuntimeError('Presentation metadata exceeds its bounded read size')
        metadata = tomllib.loads(archive.read('META-INF/neoforge.mods.toml').decode())
        if not any(mod.get('modId') == 'awft_client_presentation' and mod.get('version') == '0.2.2'
                   for mod in metadata['mods']):
            raise RuntimeError('The supplied presentation artifact is not version 0.2.2')
        if 'worldfortwo/presentation/SmallShipsConfigLifecycle.class' not in archive.namelist():
            raise RuntimeError('Built presentation artifact has no reviewed lifecycle policy')
    libraries = home/'server/libraries'
    for relative, expected in CRITICAL_LIBRARIES.items():
        if digest(libraries/relative) != expected:
            raise RuntimeError('Pinned critical dependency changed: '+relative)
    named = Path(os.environ['APPDATA'])/'PrismLauncher/libraries/net/minecraft/client/1.21.1-20240808.144430/client-1.21.1-20240808.144430-srg.jar'
    if not named.is_file():
        raise RuntimeError('The already installed pinned named client library is required; no download is attempted')
    runtime_args = libraries/RUNTIME_ARGS
    if runtime_args.stat().st_size > 65536 or digest(runtime_args) != RUNTIME_ARGS_SHA256:
        raise RuntimeError('The exact pinned runtime dependency declaration changed')
    declarations = [line.removeprefix('-DlegacyClassPath=') for line in runtime_args.read_text().splitlines()
                    if line.startswith('-DlegacyClassPath=')]
    if len(declarations) != 1:
        raise RuntimeError('Expected one actual runtime classpath declaration')
    jars = [home/'server'/part for part in declarations[0].split(';')]
    if (len(jars) > 256 or any(not path.resolve().is_relative_to(libraries.resolve())
                              or path.suffix != '.jar' or not path.is_file() for path in jars)
            or sum(path.stat().st_size for path in jars) > 512*MIB):
        raise RuntimeError('Actual runtime dependency read set exceeds its finite bounds')
    # Do not add installer-only dependencies such as Guava 20.0 from rglob().
    jars.insert(0, libraries/'net/neoforged/neoforge/21.1.262/neoforge-21.1.262-universal.jar')
    source_files = [*sorted((REPO/'compat/client-presentation/src').rglob('*.java')),
                    *sorted((REPO/'compat/client-presentation/resources').rglob('*')),
                    REPO/'tools/build_presentation.py', Path(__file__).resolve(), SOURCE]
    source_files = [path for path in source_files if path.is_file()]
    if len(source_files) > 64 or sum(path.stat().st_size for path in source_files) > 2*MIB:
        raise RuntimeError('Source identity set exceeds its finite read bound')
    return {'lock_sha256': digest(lock_path), 'candidate': lock['version'],
            'smallships': {'path': str(smallships), 'sha256': SMALLSHIPS[2]},
            'presentation': {'path': str(presentation), 'sha256': digest(presentation)},
            'runtime_args_sha256': digest(runtime_args),
            'runtime_classpath': [path.relative_to(home/'server').as_posix() for path in jars],
            'source_files_sha256': {path.relative_to(REPO).as_posix(): digest(path) for path in source_files},
            'probe_source_sha256': digest(SOURCE), 'critical_libraries_sha256': CRITICAL_LIBRARIES}, smallships, named, jars


def child(command, name, stage, receipt, environment):
    log = stage/(name+'.log')
    command = [str(value) for value in command]
    flags = subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS
    process = subprocess.Popen(command, cwd=stage, env=environment, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, creationflags=flags)
    record = {'name': name, 'pid': process.pid, 'command': command, 'log': log.name, 'status': 'running'}
    receipt['processes'].append(record)
    json_write(stage/'receipt.json', receipt)
    truncated = threading.Event()
    drain_errors = []

    def drain():
        try:
            # An unexpected noisy child cannot grow its output file beyond 1 MiB.
            with log.open('xb') as writer:
                remaining = MIB
                while data := process.stdout.read(16384):
                    accepted = min(remaining, len(data))
                    writer.write(data[:accepted])
                    remaining -= accepted
                    if accepted < len(data):
                        truncated.set()
        except BaseException as error:
            drain_errors.append(str(error))

    reader = threading.Thread(target=drain, name='awft-config-probe-log', daemon=True)
    reader.start()
    try:
        code = process.wait(timeout=90)
    except subprocess.TimeoutExpired:
        record['status'] = 'bounded wait expired; owned child not killed; no further Java phase admitted'
        json_write(stage/'receipt.json', receipt)
        raise RuntimeError(f'Owned {name} PID {process.pid} did not exit; preserve stage and inspect before another attempt')
    reader.join(timeout=5)
    record.update(status='exited', exit_code=code, log_truncated=truncated.is_set())
    if reader.is_alive() or drain_errors or truncated.is_set() or code:
        raise RuntimeError(name+' did not complete cleanly; its bounded log and failed receipt are preserved')
    if stage_bytes(stage) > STAGE_LIMIT:
        raise RuntimeError('Probe stage exceeded its reviewed allocation; no further phase admitted')


def execute(home, presentation):
    if any(not (JDK/name).is_file() for name in ('javac.exe', 'java.exe')):
        raise RuntimeError('The reviewed JDK 21.0.10 must already be installed')
    inputs, smallships, named, jars = checked_inputs(home, presentation)
    checked = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(GUARD),
        '-EstimatedCBytes', str(MIB), '-EstimatedDBytes', str(STAGE_LIMIT)], capture_output=True, text=True,
        creationflags=subprocess.CREATE_NO_WINDOW, check=False)
    guard = json.loads(checked.stdout)
    if checked.returncode or not guard.get('allowed'):
        raise RuntimeError('Storage reserve refused the bounded private probe')
    root = home/'staging'
    stage = root/('smallships-config-probe-'+str(time.time_ns())+'-'+uuid.uuid4().hex[:6])
    if not stage.resolve().is_relative_to(root.resolve()) or stage.exists():
        raise RuntimeError('Probe must use a fresh private owned staging child')
    stage.mkdir(parents=True, exist_ok=False)
    receipt = {'format': 'awft-smallships-config-harness:1', 'status': 'running', 'inputs': inputs,
               'processes': [], 'storage_check': guard, 'maximum_stage_bytes': STAGE_LIMIT,
               'boundary': 'No Minecraft startup, mixin transformation, live config edit, or native reconnect; these remain pending'}
    json_write(stage/'receipt.json', receipt)
    try:
        with zipfile.ZipFile(smallships) as archive:
            entry = archive.getinfo(NESTED[0])
            if entry.file_size != NESTED[1]:
                raise RuntimeError('Nested ForgeConfigApiPort exceeds or differs from the reviewed exact size')
            data = archive.read(entry)
        if hashlib.sha256(data).hexdigest() != NESTED[2]:
            raise RuntimeError('Nested ForgeConfigApiPort differs from the reviewed exact bytes')
        adapter = stage/'forgeconfigapiport-neoforge-21.1.0.jar'
        adapter.write_bytes(data)
        classes, temporary = stage/'classes', stage/'tmp'
        classes.mkdir(); temporary.mkdir()
        # javac @files treat backslashes as escapes even inside quoted arguments.
        cp = os.pathsep.join(path.as_posix() for path in [presentation, adapter, smallships, named, *jars])
        args = '-proc:none\n-implicit:none\n--release\n21\n-classpath\n"'+cp+'"\n-d\n"'+classes.as_posix()+'"\n"'+SOURCE.as_posix()+'"\n'
        if len(args.encode()) > MIB:
            raise RuntimeError('Compiler argument allocation exceeds bound')
        argument_file = stage/'javac.args'
        argument_file.write_text(args, encoding='utf-8')
        environment = dict(os.environ, TEMP=str(temporary), TMP=str(temporary))
        for name in ('JAVA_TOOL_OPTIONS', '_JAVA_OPTIONS', 'JDK_JAVA_OPTIONS'):
            environment.pop(name, None)
        child([JDK/'javac.exe', '-J-Xmx128m', '-J-XX:ActiveProcessorCount=2',
               '-J-XX:MaxMetaspaceSize=96m', '-J-XX:-UsePerfData', '-J-Djava.io.tmpdir='+str(temporary),
               '@'+str(argument_file)], 'compile-probe-only', stage, receipt, environment)
        compiled = list(classes.rglob('*.class'))
        if (not compiled or len(compiled) > 8 or sum(path.stat().st_size for path in compiled) > 2*MIB
                or any(not path.name.startswith('SmallShipsConfigProbe') for path in compiled)):
            raise RuntimeError('Probe compilation produced unexpected implementation classes')
        logging = stage/'console-only-log4j2.xml'
        logging.write_text('<Configuration status="ERROR"><Appenders><Console name="Console" target="SYSTEM_OUT">'
            '<PatternLayout pattern="%level %logger: %msg%n"/></Console></Appenders><Loggers><Root level="warn">'
            '<AppenderRef ref="Console"/></Root></Loggers></Configuration>', encoding='utf-8')
        child([JDK/'java.exe', '-Xms16m', '-Xmx128m', '-XX:ActiveProcessorCount=2',
               '-XX:MaxMetaspaceSize=96m', '-XX:-UsePerfData', '-Djava.awt.headless=true',
               '-Djava.io.tmpdir='+str(temporary), '-Dlog4j.configurationFile='+str(logging),
               '-cp', os.pathsep.join([str(classes), cp]), 'net.neoforged.fml.config.SmallShipsConfigProbe', stage],
              'actual-pinned-config-classes', stage, receipt, environment)
        result = json.loads((stage/'java-result.json').read_text(encoding='utf-8'))
        cases = result.get('cases', [])
        if (result.get('status') != 'pass' or result.get('passed_cases') != len(EXPECTED_CASES)
                or len(cases) != len(EXPECTED_CASES) or {row.get('case') for row in cases} != EXPECTED_CASES
                or any(row.get('status') != 'pass' for row in cases)):
            raise RuntimeError('Actual Java probe did not pass every required semantic case')
        expected_sources = {'policy': presentation, 'smallships': smallships, 'original_callback': smallships,
                            'adapter': adapter, 'fml': home/'server/libraries'/next(iter(CRITICAL_LIBRARIES)),
                            'guava': home/'server/libraries/com/google/guava/guava/32.1.2-jre/guava-32.1.2-jre.jar'}
        if any(os.path.normcase(str(Path(result['class_sources'][key]).resolve()))
               != os.path.normcase(str(path.resolve())) for key, path in expected_sources.items()):
            raise RuntimeError('A tested implementation class came from different bytes than the exact inputs')
        again, *_ = checked_inputs(home, presentation)
        if inputs != again:
            raise RuntimeError('Pinned inputs changed during the probe; result cannot be accepted')
        receipt.update(status='pass: actual pinned config semantics only', result=result,
                       result_sha256=digest(stage/'java-result.json'), actual_stage_bytes=stage_bytes(stage))
    except BaseException as error:
        receipt.update(status='failed; private stage, logs and partial result preserved', error=str(error))
        json_write(stage/'receipt.json', receipt)
        raise RuntimeError(str(error)+'; receipt='+str(stage/'receipt.json')) from error
    json_write(stage/'receipt.json', receipt)
    return {'receipt': str(stage/'receipt.json'), 'sha256': digest(stage/'receipt.json'),
            'status': receipt['status'], 'passed_cases': receipt['result']['passed_cases'], 'boundary': receipt['boundary']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path(r'D:\A World for Two'))
    parser.add_argument('--presentation-jar', type=Path)
    parser.add_argument('--execute-after-resource-window', action='store_true')
    arguments = parser.parse_args()
    if not arguments.execute_after_resource_window:
        print(json.dumps({'status': 'pending: not executed', 'java_launched': False, 'writes': False,
              'required_artifact': 'separately built awft-client-presentation-0.2.2.jar',
              'execute_gate': '--execute-after-resource-window', 'estimated_c_bytes': MIB,
              'estimated_d_bytes': STAGE_LIMIT, 'java_heap_bytes': 128*MIB, 'active_processors': 2,
              'transformation_and_native_reconnect': 'separate pending gates'}))
    elif arguments.presentation_jar is None:
        parser.error('--presentation-jar is required for execution')
    else:
        print(json.dumps(execute(arguments.home.resolve(), arguments.presentation_jar.resolve())))
