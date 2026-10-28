"""Prepare a reviewed tick-telemetry diff and a tiny Java 21 fixture, not a pack.

Only a new private source/receipt directory is written. The master integrates
active bridge sources and builds candidates. No Minecraft JVM is started.
"""
from pathlib import Path
import argparse
import difflib
import json
import os
import subprocess
import time

from control_room.common import REPO, digest, utcnow
from tools.playtest import guard


BRIDGE = 'compat/control-bridge/src/worldfortwo/bridge/ControlBridge.java'


def patched_bridge(text):
    changes = (
        ('    private int ticks;\n', '    private int ticks;\n    private final TickWindow performanceTicks = new TickWindow();\n'),
        ('        ticks = 0; tickNanos = 0; lastSample = System.nanoTime();\n',
         '        ticks = 0; tickNanos = 0; lastSample = System.nanoTime();\n        performanceTicks.resetLifecycle();\n'),
        ('    private void before(ServerTickEvent.Pre event) { beforeTick = System.nanoTime(); }',
         '    private void before(ServerTickEvent.Pre event) { beforeTick = System.nanoTime(); performanceTicks.started(beforeTick); }'),
        ('        tickNanos += now - beforeTick;\n',
         '        tickNanos += now - beforeTick;\n        performanceTicks.finished(now - beforeTick);\n'),
        ('        data.put("ticks_sampled", ticks);\n',
         '        data.put("ticks_sampled", ticks);\n        data.put("tick_window", performanceTicks.snapshotAndReset());\n'),
    )
    for before, after in changes:
        if text.count(before) != 1:
            raise ValueError('Bridge telemetry integration context changed; review instead of guessing')
        text = text.replace(before, after)
    return text


def prepare(home):
    home = Path(home).resolve()
    if home.parent != Path('D:/A World for Two/staging/world-tests').resolve():
        raise ValueError('Existing owned construction source-staging home required')
    reserve = guard(0, 8 * 1024 * 1024)
    output = home / 'staging' / ('terrain-performance-source-' + str(time.time_ns()))
    output.mkdir()
    classes = output / 'classes'
    classes.mkdir()
    before = (REPO / BRIDGE).read_text(encoding='utf-8')
    after = patched_bridge(before)
    diff = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                       fromfile='a/' + BRIDGE, tofile='b/' + BRIDGE))
    (output / 'ControlBridge.integration.diff').write_text(diff, encoding='utf-8', newline='\n')
    sources = [REPO / 'compat/performance' / name for name in ('TickWindow.java', 'TickWindowProbe.java')]
    for path in sources:
        (output / path.name).write_bytes(path.read_bytes())
    receipt = dict(format='awft-performance-source-handoff:1', at=utcnow(), reserve_guard=reserve,
                   passed=False, native_game_actions=0, active_source_changes=0,
                   source_sha256={str(p.relative_to(REPO)): digest(p) for p in sources},
                   bridge_base_sha256=digest(REPO / BRIDGE))
    env = {k: v for k, v in os.environ.items() if k not in ('JAVA_TOOL_OPTIONS', '_JAVA_OPTIONS', 'JDK_JAVA_OPTIONS')}
    try:
        commands = [('compile', ['javac', '-J-Xmx64m', '-J-XX:ActiveProcessorCount=2', '-J-XX:-UsePerfData',
                                 '--release', '21', '-d', str(classes), *map(str, sources)]),
                    ('fixture', ['java', '-Xmx64m', '-XX:ActiveProcessorCount=2', '-XX:-UsePerfData',
                                 '-cp', str(classes), 'worldfortwo.bridge.TickWindowProbe'])]
        for label, command in commands:
            result = subprocess.run(command, capture_output=True, timeout=30, cwd=output, env=env,
                                    creationflags=subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS)
            raw = result.stdout + result.stderr
            if len(raw) > 1024 * 1024:
                raise ValueError('Finite fixture output exceeded')
            (output / (label + '.txt')).write_bytes(raw)
            receipt[label + '_exit'] = result.returncode
            if result.returncode:
                raise RuntimeError(label + ' failed; private output preserved')
        receipt['passed'] = True
    except BaseException as error:
        receipt['error_class'] = type(error).__name__
        raise
    finally:
        (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    return {'directory': str(output), 'receipt_sha256': digest(output / 'receipt.json'),
            'passed': True, 'native_game_actions': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, required=True)
    print(json.dumps(prepare(parser.parse_args().home), indent=2))
