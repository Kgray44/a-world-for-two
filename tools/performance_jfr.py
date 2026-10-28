"""Compile a small JDK reader and summarize an existing private bounded JFR file.

No attach, recording start/stop, Minecraft command, configuration or world action.
--self-test runs only a synthetic JDK recording in a new private probe directory.
"""
from pathlib import Path
import argparse
import json
import os
import subprocess
import time

from control_room.common import digest, utcnow
from tools.playtest import guard
from tools.performance_windows import memory_pressure


def admission():
    memory = memory_pressure()
    if not memory.get('available') or min(memory['physical_available_bytes'], memory['commit_headroom_bytes']) < 1536*1024**2:
        raise ValueError('Physical/commit headroom refused before owned JDK process')
    return memory


def run(home, recording=None, pid=None, process_start_ms=None, self_test=False):
    home = Path(home).resolve()
    if home.parent != Path('D:/A World for Two/staging/world-tests').resolve():
        raise ValueError('Owned private staging home required')
    if self_test == (recording is not None):
        raise ValueError('Choose a retained recording or a synthetic self-test')
    if recording is not None:
        recording = Path(recording)
        if (recording.is_symlink() or recording.is_junction() or not recording.is_file()
                or not 8 <= recording.stat().st_size <= 64*1024**2 or recording.suffix.lower() != '.jfr'
                or type(pid) is not int or pid <= 0 or type(process_start_ms) is not int or process_start_ms <= 0):
            raise ValueError('Bounded ordinary JFR and expected native PID/start epoch milliseconds required')
        if not recording.resolve().is_relative_to(home):
            raise ValueError('Retained recording must be inside the private construction home')
    reserve = guard(4*1024**2, 64*1024**2)
    memory = admission()
    work = home/'staging'/('retained-jfr-'+str(time.time_ns()))
    work.mkdir(); (work/'classes').mkdir(); (work/'tmp').mkdir(); (work/'repository').mkdir()
    source = Path(__file__).resolve().parents[1]/'compat/performance'
    sources = [source/name for name in ('JfrSummary.java', 'JfrSummaryProbe.java')]
    receipt = {'format': 'awft-retained-jfr-reader:1', 'at': utcnow(), 'passed': False,
               'synthetic_only': self_test, 'minecraft_or_attach_actions': False, 'strict_parity_proved': False,
               'reserve': reserve, 'memory': memory, 'source_sha256': {p.name: digest(p) for p in sources},
               'reader_heap_MiB': 96, 'compiler_heap_MiB': 128, 'processors': 2}
    jdk = Path('C:/Program Files/Java/jdk-21.0.10/bin')
    env = {k: v for k, v in os.environ.items() if k not in ('JAVA_TOOL_OPTIONS', '_JAVA_OPTIONS', 'JDK_JAVA_OPTIONS')}
    env.update(TEMP=str(work/'tmp'), TMP=str(work/'tmp'))

    def invoke(binary, args, name):
        admission()
        result = subprocess.run([str(jdk/binary), *args], cwd=work, env=env, capture_output=True, timeout=45,
                                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS)
        raw = result.stdout+result.stderr
        if len(raw) > 2*1024**2:
            raise ValueError('Reader output exceeded its bound')
        (work/name).write_bytes(raw)
        return result

    try:
        args = work/'javac.args'
        args.write_text('-proc:none\n--release\n21\n-Xmaxerrs\n10\n-d\n"'+(work/'classes').as_posix()+'"\n'+
                        '\n'.join('"'+p.as_posix()+'"' for p in sources)+'\n', encoding='utf-8')
        compiled = invoke('javac.exe', ['-J-Xmx128m', '-J-XX:ActiveProcessorCount=2', '-J-XX:-UsePerfData',
                          '-J-Djava.io.tmpdir='+str(work/'tmp'), '-J-XX:ErrorFile='+str(work/'hs_err_pid%p.log'), '@'+str(args)], 'javac.log')
        receipt['compile_exit'] = compiled.returncode
        if compiled.returncode:
            raise RuntimeError('JDK reader compile failed; retained javac.log')
        flags = ['-Xmx96m', '-XX:ActiveProcessorCount=2', '-XX:-UsePerfData', '-Djava.io.tmpdir='+str(work/'tmp'),
                 '-XX:ErrorFile='+str(work/'hs_err_pid%p.log'), '-XX:FlightRecorderOptions=repository='+str(work/'repository'),
                 '-cp', str(work/'classes')]
        if self_test:
            read = invoke('java.exe', [*flags, 'worldfortwo.performance.JfrSummaryProbe'], 'fixture.log')
            receipt['fixture_exit'] = read.returncode
        else:
            before = recording.stat()
            receipt['input_sha256'] = digest(recording)
            read = invoke('java.exe', [*flags, 'worldfortwo.performance.JfrSummary', str(recording.resolve()), str(pid), str(process_start_ms)], 'reader.log')
            receipt['reader_exit'] = read.returncode
            after = recording.stat()
            if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino) or receipt['input_sha256'] != digest(recording):
                raise ValueError('Recording changed during custody')
            if read.returncode == 0:
                summary = json.loads(read.stdout)
                if summary.get('strict_parity_proved') is not False or summary.get('native_gameplay_qualified') is not False:
                    raise ValueError('Reader must never grant gameplay/parity acceptance')
                (work/'summary.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
        if read.returncode:
            raise RuntimeError('JDK recording read/fixture refused; original private log retained')
        receipt['passed'] = True
    except BaseException as error:
        receipt['failure'] = type(error).__name__+': '+str(error)
        raise
    finally:
        (work/'result.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
    return {'output': str(work), 'passed': True, 'receipt_sha256': digest(work/'result.json')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', required=True, type=Path)
    parser.add_argument('--recording', type=Path)
    parser.add_argument('--pid', type=int)
    parser.add_argument('--process-start-ms', type=int)
    parser.add_argument('--self-test', action='store_true')
    print(json.dumps(run(**vars(parser.parse_args())), indent=2))


if __name__ == '__main__':
    main()
