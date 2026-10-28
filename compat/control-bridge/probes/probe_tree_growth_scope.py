"""Compile only TreeGrowthScope and its bounded collection probe; never start a loader."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(output: Path, classpath_args: Path, bridge: Path, expected_bridge_sha256: str) -> dict:
    root = Path(__file__).resolve().parents[3]
    source = root / 'compat/control-bridge/src/worldfortwo/bridge/TreeGrowthScope.java'
    probe = Path(__file__).with_name('TreeGrowthScopeGridProbe.java')
    jdk = Path(r'C:\Program Files\Java\jdk-21.0.10\bin')
    output = output.resolve()
    output.relative_to(Path(r'D:\A World for Two\staging').resolve())
    if output.exists() or sha(bridge) != expected_bridge_sha256:
        raise ValueError('Fresh owned output and exact reviewed bridge compile dependency required')
    if classpath_args.stat().st_size > 128 * 1024:
        raise ValueError('Classpath recipe exceeds finite input')
    lines = classpath_args.read_text(encoding='utf-8').splitlines()
    classpath = lines[lines.index('-classpath') + 1].strip('"')
    if len(classpath) > 64 * 1024:
        raise ValueError('Classpath exceeds finite input')
    guard = subprocess.run(['powershell.exe', '-NoProfile', '-File',
        r'C:\Users\kkids\AppData\Local\AeroStorageWatch\ReserveGuard.ps1',
        '-EstimatedCBytes', '0', '-EstimatedDBytes', str(16 * 1024**2)],
        capture_output=True, text=True, check=True, timeout=20)
    allowed = json.loads(guard.stdout.strip())
    if not allowed.get('allowed'):
        raise ValueError('Storage reserve refused')
    output.mkdir()
    classes = output / 'classes'
    classes.mkdir()
    receipt = {'format': 'awft-tree-scope-grid-probe:1', 'passed': False,
               'native_world_actions': False, 'source_sha256': sha(source), 'probe_sha256': sha(probe),
               'bridge_dependency_sha256': expected_bridge_sha256, 'classpath_recipe_sha256': sha(classpath_args),
               'limits': {'heap_mib': 256, 'active_processors': 2, 'compile_seconds': 45, 'probe_seconds': 30},
               'storage_guard': allowed}
    env = {key: value for key, value in os.environ.items()
           if key not in ('JAVA_TOOL_OPTIONS', '_JAVA_OPTIONS', 'JDK_JAVA_OPTIONS')}
    flags = subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS if os.name == 'nt' else 0
    try:
        cp = bridge.as_posix() + os.pathsep + classpath
        args = output / 'javac.args'
        args.write_text('-proc:none\n--release\n21\n-Xmaxerrs\n20\n-Xmaxwarns\n20\n-classpath\n"' + cp +
                        '"\n-d\n"' + classes.as_posix() + '"\n"' + source.as_posix() + '"\n"' +
                        probe.as_posix() + '"\n', encoding='utf-8')
        started = time.monotonic()
        compile_result = subprocess.run([str(jdk / 'javac.exe'), '-J-Xmx256m',
            '-J-XX:ActiveProcessorCount=2', '@' + str(args)], capture_output=True, text=True,
            timeout=45, env=env, creationflags=flags)
        (output / 'javac.log').write_text(compile_result.stdout + compile_result.stderr, encoding='utf-8')
        receipt['compile_exit'] = compile_result.returncode
        receipt['compile_seconds'] = round(time.monotonic() - started, 3)
        if compile_result.returncode:
            raise RuntimeError('Isolated scope compile failed; retained javac.log')
        java_args = output / 'java.args'
        java_args.write_text('-Xmx256m\n-XX:ActiveProcessorCount=2\n-classpath\n"' +
                             classes.as_posix() + os.pathsep + cp +
                             '"\nworldfortwo.bridge.TreeGrowthScopeGridProbe\n', encoding='utf-8')
        result = subprocess.run([str(jdk / 'java.exe'), '@' + str(java_args)],
                                capture_output=True, text=True, timeout=30, env=env, creationflags=flags)
        (output / 'probe.log').write_text(result.stdout + result.stderr, encoding='utf-8')
        receipt['probe_exit'] = result.returncode
        if result.returncode:
            raise RuntimeError('Collection probe failed; retained probe.log')
        receipt['result'] = json.loads(result.stdout)
        receipt['compiled_scope_sha256'] = sha(classes / 'worldfortwo/bridge/TreeGrowthScope.class')
        receipt['passed'] = receipt['result']['passed'] is True
    except BaseException as failure:
        receipt['failure'] = type(failure).__name__ + ': ' + str(failure)
        raise
    finally:
        (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--classpath-args', type=Path, required=True)
    parser.add_argument('--bridge', type=Path, required=True)
    parser.add_argument('--expected-bridge-sha256', required=True)
    args = parser.parse_args()
    print(json.dumps(run(**vars(args)), indent=2))
