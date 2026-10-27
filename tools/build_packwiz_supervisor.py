"""Bounded original Java 21 supervisor build; never runs installer Main or a game."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import time
import tomllib
import uuid
import zipfile

REPO = Path(__file__).resolve().parents[1]
HOME = Path('D:/A World for Two')
SOURCE = REPO / 'compat/packwiz-supervisor'
JDK = Path('C:/Program Files/Java/jdk-21.0.10/bin')
BOUND = 16 * 1024 * 1024


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def guard():
    command = ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
               'C:/Users/kkids/AppData/Local/AeroStorageWatch/ReserveGuard.ps1',
               '-EstimatedCBytes', str(1024 * 1024), '-EstimatedDBytes', str(BOUND)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=30,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    value = json.loads(result.stdout.strip().splitlines()[-1])
    if result.returncode or not value.get('allowed'):
        raise RuntimeError('Storage reserve refused: ' + value.get('reason', 'unavailable'))
    return value


def release_inventory(pack_root, lock_path):
    """Bind every index member to original bytes and the full compatibility lock.

    Returns a deterministic original binary descriptor, never JARs/assets or a
    mutable current-main URL. This does not contact a public server.
    """
    from control_room.pack import validate_pack
    pack_root, lock_path = Path(pack_root), Path(lock_path)
    lock_raw = lock_path.read_bytes()
    lock = json.loads(lock_raw)
    errors = validate_pack(pack_root, lock)
    if errors:
        raise ValueError('Complete release source validation failed: ' + '; '.join(errors))
    pack_raw, index_raw = [(pack_root/name).read_bytes() for name in ('pack.toml', 'index.toml')]
    if len(pack_raw) > 65536 or len(index_raw) > 2*1024*1024 or len(lock_raw) > 2*1024*1024:
        raise ValueError('Release metadata exceeds finite input bounds')
    pack, index = [tomllib.loads(raw.decode('utf-8')) for raw in (pack_raw, index_raw)]
    if (not re.fullmatch(r'0\.1\.0-candidate\.[1-9][0-9]{0,4}', lock['version'])
            or pack.get('pack-format') != 'packwiz:1.1.0'
            or pack.get('index', {}).get('file') != 'index.toml'
            or pack['index'].get('hash-format') != 'sha256' or index.get('hash-format') != 'sha256'):
        raise ValueError('Exact supported immutable candidate and SHA-256 index required')
    expected, rows = {}, []
    folders = {'mod': 'mods', 'shader': 'shaderpacks', 'resourcepack': 'resourcepacks'}
    for item in lock['mods']:
        name = folders[item['kind']]+'/'+item['slug']+'.pw.toml'
        if name in expected:
            raise ValueError('Duplicate locked metadata identity')
        expected[name] = item
    seen, destinations = set(), set()
    source_hashes = {'pack.toml': hashlib.sha256(pack_raw).hexdigest(),
                     'index.toml': hashlib.sha256(index_raw).hexdigest(),
                     'lock.json': hashlib.sha256(lock_raw).hexdigest()}
    for entry in index['files']:
        name = entry['file']
        parts = name.split('/')
        if (not name or name.startswith('/') or '\\' in name or ':' in name
                or any(p in ('', '.', '..') or p.endswith((' ', '.')) for p in parts)
                or any(ord(c) < 32 for c in name) or name.casefold() in seen):
            raise ValueError('Unsafe/duplicate release member')
        seen.add(name.casefold())
        path = pack_root/name
        if path.is_symlink() or not path.resolve().is_relative_to(pack_root.resolve()) or path.stat().st_size > 8*1024*1024:
            raise ValueError('Linked/oversized release member')
        raw = path.read_bytes()
        source_hashes[name] = hashlib.sha256(raw).hexdigest()
        if source_hashes[name] != entry['hash']:
            raise ValueError('Release member changed during inventory binding')
        metafile = entry.get('metafile', False)
        if type(metafile) is not bool:
            raise ValueError('Invalid metafile flag')
        if metafile:
            item = expected.pop(name, None)
            if item is None:
                raise ValueError('Untracked/wrong-folder metafile')
            meta = tomllib.loads(raw.decode('utf-8'))
            optional = item.get('optional', False)
            default = item.get('default', True)
            if type(optional) is not bool or type(default) is not bool:
                raise ValueError('Invalid locked optional policy')
            options = meta.get('option', {})
            if (options.get('optional', False) != optional or (optional and options.get('default', True) != default)):
                raise ValueError('Actual Packwiz optional policy differs from lock')
            if optional and (name != 'mods/essential.pw.toml' or default or item['side'] != 'client'):
                raise ValueError('Only exact Essential GUI default-off policy is reviewed')
            algorithm, download = meta['download']['hash-format'], meta['download']['hash']
            if algorithm not in ('sha256', 'sha512') or download != item['hashes'].get(algorithm):
                raise ValueError('Exact strong download hash required')
            destination = folders[item['kind']]+'/'+item['filename']
            if '/' in item['filename'] or '\\' in item['filename']:
                raise ValueError('Artifact filename must be one basename')
            hashes = {k.upper().replace('SHA', 'SHA-'): v for k, v in item['hashes'].items()}
            if set(hashes)-{'SHA-1', 'SHA-256', 'SHA-512'}:
                raise ValueError('Unknown strong inventory algorithm')
            size, side = item['size'], item['side']
        else:
            if not (name.startswith(('config/', 'defaultconfigs/')) or name == 'options.txt'):
                raise ValueError('Unreviewed raw release payload')
            destination, size, side, optional, default = name, len(raw), 'both', False, True
            algorithm, download = 'sha256', entry['hash']
            hashes = {'SHA-256': entry['hash']}
        if destination.casefold() in destinations or type(size) is not int or not 0 <= size <= 256*1024*1024:
            raise ValueError('Duplicate or oversized destination')
        destinations.add(destination.casefold())
        rows.append((name, entry['hash'], metafile, destination, size, side, optional, default, algorithm, download, hashes))
    if expected or not rows or len(rows) > 8192 or sum(row[4] for row in rows) > 4*1024**3:
        raise ValueError('Incomplete or unbounded release inventory')
    if sum(row[6] for row in rows) != 1:
        raise ValueError('Explicit Essential optional inventory required')
    data = bytearray()
    def text(value):
        raw = value.encode('utf-8')
        if len(raw) > 4096 or '\0' in value:
            raise ValueError('Invalid bounded inventory string')
        data.extend(struct.pack('>I', len(raw))); data.extend(raw)
    for value in ('awft-supervisor-release:1', lock['version'],
                  'https://kgray44.github.io/a-world-for-two/releases/'+lock['version']+'/pack.toml',
                  source_hashes['pack.toml'], source_hashes['index.toml'], source_hashes['lock.json']):
        text(value)
    data.extend(struct.pack('>I', len(rows)))
    for name, metadata_hash, metafile, destination, size, side, optional, default, algorithm, download, hashes in sorted(rows):
        text(name); text(metadata_hash); data.extend(struct.pack('>?', metafile)); text(destination)
        data.extend(struct.pack('>q', size)); text(side); data.extend(struct.pack('>??', optional, default))
        text(algorithm); text(download); data.extend(struct.pack('>I', len(hashes)))
        for key, value in sorted(hashes.items()):
            text(key); text(value)
    if len(data) > 2*1024*1024:
        raise ValueError('Complete release inventory exceeds resource bound')
    return bytes(data), {'version': lock['version'], 'entries': len(rows),
                         'metadata_entries': sum(row[2] for row in rows),
                         'raw_entries': sum(not row[2] for row in rows),
                         'all_artifact_bytes': sum(row[4] for row in rows),
                         'sha256': hashlib.sha256(data).hexdigest(), 'source_hashes': source_hashes}


def build(output, actual_logs=()):
    if len(actual_logs) > 2:
        raise ValueError('At most two bounded actual failure-log fixtures')
    reserve = guard()
    output = Path(output).resolve()
    output.relative_to((HOME / 'staging').resolve())
    output.mkdir()  # Refuse existing trees, including any failed attempt.
    receipt = {'format': 'awft-packwiz-supervisor-core:1', 'status': 'FAILED',
               'gui_automatic_recovery': 'BLOCKED_UNOBSERVABLE_USER_DECISION',
               'installer_invoked': False, 'network_invoked': False, 'reserve': reserve}
    try:
        pins = json.loads((REPO / 'catalog/tools.lock.json').read_text(encoding='utf-8'))
        tools = {}
        for key in ('packwiz_bootstrap', 'packwiz_installer'):
            pin = pins[key]
            path = HOME / 'caches' / pin['filename']
            if path.stat().st_size != pin['size'] or sha256(path) != pin['hashes']['sha256']:
                raise RuntimeError('Exact cached official tool pin mismatch: ' + key)
            tools[key] = {'version': pin['version'], 'bytes': pin['size'], 'sha256': sha256(path)}
        installer = HOME / 'caches' / pins['packwiz_installer']['filename']
        receipt['unchanged_official_tools'] = tools
        release, binding = release_inventory(REPO/'packwiz', REPO/'catalog/lock.json')
        receipt['release_inventory'] = binding
        receipt['native_installer_execution'] = 'NOT_RUN; executable candidate requires parent review and fresh native qualification'
        sources = sorted((SOURCE / 'src').rglob('*.java'))
        probes = sorted((SOURCE / 'probes').rglob('*.java'))
        if sum(path.stat().st_size for path in sources + probes) > 1024 * 1024:
            raise RuntimeError('Source exceeds bounded compiler input')
        receipt['source_sha256'] = {path.relative_to(REPO).as_posix(): sha256(path) for path in sources + probes}
        receipt['source_sha256']['compat/packwiz-supervisor/README.md'] = sha256(SOURCE / 'README.md')
        receipt['source_sha256']['tools/build_packwiz_supervisor.py'] = sha256(Path(__file__))
        for name in ('LICENSE', 'probes/test_inventory.py'):
            receipt['source_sha256']['compat/packwiz-supervisor/'+name] = sha256(SOURCE/name)
        receipt['actual_log_sha256'] = []
        for path in map(Path, actual_logs):
            if path.stat().st_size > 4 * 1024 * 1024:
                raise RuntimeError('Diagnostic input log exceeds bound')
            receipt['actual_log_sha256'].append(sha256(path))
        classes, probe_classes, temp = output / 'classes', output / 'probe-classes', output / 'temp'
        for folder in (classes, probe_classes, temp):
            folder.mkdir()
        (classes/'awft-release.bin').write_bytes(release)
        (output/'release-inventory.json').write_text(json.dumps(binding, indent=2)+'\n', encoding='utf-8')
        flags = (subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS) if os.name == 'nt' else 0
        commands = [
            ('compile-core', [str(JDK / 'javac.exe'), '-J-Xmx64m', '-J-XX:ActiveProcessorCount=2', '-J-XX:+PerfDisableSharedMem',
                              '-J-Djava.io.tmpdir=' + str(temp), '-proc:none', '--release', '21', '-d', str(classes), *map(str, sources)]),
            ('compile-probes', [str(JDK / 'javac.exe'), '-J-Xmx64m', '-J-XX:ActiveProcessorCount=2', '-J-XX:+PerfDisableSharedMem',
                                '-J-Djava.io.tmpdir=' + str(temp), '-proc:none', '--release', '21', '-cp', os.pathsep.join(map(str, (classes, installer))),
                                '-d', str(probe_classes), *map(str, probes)]),
        ]
        java = [str(JDK / 'java.exe'), '-Xmx64m', '-XX:ActiveProcessorCount=2', '-XX:+PerfDisableSharedMem',
                '-Djava.awt.headless=true', '-Djava.io.tmpdir=' + str(temp)]
        cp = os.pathsep.join(map(str, (classes, probe_classes)))
        commands += [
            ('core-probe', java + ['-cp', cp, 'worldfortwo.packwiz.CoreProbe', str(output / 'fixtures'), *map(str, actual_logs)]),
            ('pinned-cache-probe', java + ['-cp', cp + os.pathsep + str(installer), 'worldfortwo.packwiz.PinnedCacheProbe', str(output / 'fixtures')]),
            ('supervisor-probe', java + ['-cp', cp, 'worldfortwo.packwiz.SupervisorProbe', str(output / 'supervisor-fixtures')]),
            ('native-choice-probe', java + ['-cp', cp + os.pathsep + str(installer), 'worldfortwo.packwiz.NativeChoicesProbe', str(output / 'choice-fixtures'), str(installer)]),
            ('process-probe', java + ['-cp', cp, 'worldfortwo.packwiz.ProcessProbe', str(output/'process-fixtures')]),
            ('inventory-tests', [__import__('sys').executable, '-B', str(SOURCE/'probes/test_inventory.py'), str(output/'inventory-fixtures')]),
        ]
        receipt['steps'] = []
        for name, command in commands:
            started = time.monotonic()
            log = output / (name + '.log')
            try:
                result = subprocess.run(command, capture_output=True, text=True, timeout=60, creationflags=flags)
            except subprocess.TimeoutExpired as error:
                def text(value):
                    return value.decode('utf-8', errors='replace') if isinstance(value, bytes) else value or ''
                with log.open('x', encoding='utf-8') as stream:
                    stream.write(text(error.stdout) + text(error.stderr))
                receipt['steps'].append({'name': name, 'timed_out': True, 'log_sha256': sha256(log)})
                raise RuntimeError(name + ' timed out; owned process reaped and partial output preserved') from error
            with log.open('x', encoding='utf-8') as stream:
                stream.write(result.stdout + result.stderr)
            receipt['steps'].append({'name': name, 'exit_code': result.returncode, 'seconds': round(time.monotonic() - started, 3), 'log_sha256': sha256(log)})
            if result.returncode:
                raise RuntimeError(name + ' failed; exact private log preserved')
            if name.endswith('probe'):
                match = re.search(r'(CORE_FIXTURE|PINNED_CACHE|SUPERVISOR|NATIVE_CHOICE|PROCESS)_CHECKS=(\d+) PASS', result.stdout)
                if not match:
                    raise RuntimeError(name + ' did not report complete checks')
                receipt['steps'][-1]['checks'] = int(match.group(2))
        jar = output / 'awft-packwiz-supervisor-core-0.0.1-source-candidate.jar'
        with zipfile.ZipFile(jar, 'x', zipfile.ZIP_DEFLATED) as archive:
            # Core API only: probes and upstream classes/JARs are never bundled. No Main-Class.
            for path in sorted(classes.rglob('*.class')):
                entry = zipfile.ZipInfo(path.relative_to(classes).as_posix(), (2026, 1, 1, 0, 0, 0))
                entry.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(entry, path.read_bytes())
        receipt['core_jar'] = {'bytes': jar.stat().st_size, 'sha256': sha256(jar), 'launchable': False}
        current_release, current_binding = release_inventory(REPO/'packwiz', REPO/'catalog/lock.json')
        if current_release != release or current_binding != binding:
            raise RuntimeError('Canonical inputs changed during build; retain this failed snapshot and rebuild separately')
        executable = output/'awft-packwiz-supervisor-0.1.0-source-candidate.jar'
        with zipfile.ZipFile(executable, 'x', zipfile.ZIP_DEFLATED) as archive:
            contents = {'META-INF/MANIFEST.MF': b'Manifest-Version: 1.0\r\nMain-Class: worldfortwo.packwiz.SupervisorMain\r\n\r\n',
                        'awft-release.bin': release,
                        'LICENSE-awft.txt': (SOURCE/'LICENSE').read_bytes()}
            contents.update({path.relative_to(classes).as_posix(): path.read_bytes() for path in sorted(classes.rglob('*.class'))})
            for name, body in sorted(contents.items()):
                entry = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0));entry.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(entry, body)
        receipt['executable_jar'] = {'bytes': executable.stat().st_size, 'sha256': sha256(executable), 'launchable': True,
                                     'inventory_sha256': binding['sha256'], 'version': binding['version'],
                                     'distribution_integrated': False, 'native_installer_qualification': 'NOT_RUN'}
        # Exercise our packaged entry with invalid arguments only. Parsing must
        # refuse before any instance, GUI, public read or installer can be used.
        smoke = subprocess.run(java+['-jar', str(executable), '--invalid-source-fixture-entry'],
                               capture_output=True, text=True, timeout=15, creationflags=flags)
        smoke_log = output/'entry-smoke.log'
        smoke_log.write_text(smoke.stdout+smoke.stderr, encoding='utf-8')
        receipt['steps'].append({'name': 'entry-smoke', 'exit_code': smoke.returncode, 'expected_exit_code': 1,
                                 'log_sha256': sha256(smoke_log), 'installer_invoked': False})
        if smoke.returncode != 1 or 'AWFT updater refused: IllegalArgumentException: Usage:' not in smoke.stderr:
            raise RuntimeError('Packaged original entry failed to refuse invalid invocation')
        receipt['status'] = 'PASS_CORE_FIXTURES_AND_PINNED_CACHE_ONLY_NOT_INSTALLER_RECOVERY'
    except Exception as error:
        receipt['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        files = [path for path in output.rglob('*') if path.is_file()]
        receipt['owned_bytes_before_receipt'] = sum(path.stat().st_size for path in files)
        if receipt['owned_bytes_before_receipt'] > BOUND - 65536:
            receipt['status'] = 'FAILED_ALLOCATION_BOUND'
        target = output / 'receipt.json'
        with target.open('x', encoding='utf-8') as stream:
            json.dump(receipt, stream, indent=2); stream.write('\n')
        with (output / 'receipt.complete').open('x', encoding='ascii') as stream:
            stream.write(sha256(target) + '\n')
    if receipt['status'] != 'PASS_CORE_FIXTURES_AND_PINNED_CACHE_ONLY_NOT_INSTALLER_RECOVERY':
        raise RuntimeError('Build did not pass; private receipt preserved')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HOME / 'staging' / ('packwiz-supervisor-core-' + time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-' + uuid.uuid4().hex[:8]))
    parser.add_argument('--actual-log', action='append', type=Path, default=[])
    args = parser.parse_args()
    value = build(args.output, args.actual_log)
    print(json.dumps({'output': str(args.output), 'status': value['status'], 'core_jar': value.get('core_jar'),
                      'executable_jar': value.get('executable_jar'), 'steps': value['steps']}))


if __name__ == '__main__':
    main()
