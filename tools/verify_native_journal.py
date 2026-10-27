"""Prove NativeJournal's Windows reader-lock behavior without starting Minecraft.

Only a package-local probe is compiled. The actual NativeJournal implementation is
loaded from the exact bridge JAR in catalog/lock.json, with Gson as its only library.
Every attempt has a unique private D: stage and retains failed receipts/logs.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
import uuid
from pathlib import Path

from control_room.common import Layout, REPO, UserError, digest, read_json, utcnow, write_json


MIB = 1024**2
GUARD = Path(r'C:\Users\kkids\AppData\Local\AeroStorageWatch\ReserveGuard.ps1')
JDK = Path(r'C:\Program Files\Java\jdk-21.0.10\bin')


def reserve():
    checked = subprocess.run(
        ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(GUARD),
         '-EstimatedCBytes', str(16*MIB), '-EstimatedDBytes', str(16*MIB)],
        capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW, check=False)
    if checked.returncode:
        raise UserError('Storage reserve check failed: '+checked.stderr[:2000])
    result = json.loads(checked.stdout)
    if not result.get('allowed'):
        raise UserError('Storage reserve refused the bounded journal probe: '+str(result.get('reason')))
    return result


def child(command, stage, name, receipt, timeout):
    """Bound waits while preserving ownership; never kill an overdue child."""
    stdout_path, stderr_path = stage/(name+'.stdout.log'), stage/(name+'.stderr.log')
    with stdout_path.open('xb') as stdout, stderr_path.open('xb') as stderr:
        process = subprocess.Popen(command, stdout=stdout, stderr=stderr,
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS)
        record = {'phase': name, 'pid': process.pid, 'started': utcnow(),
                  'stdout': stdout_path.name, 'stderr': stderr_path.name}
        receipt['processes'].append(record)
        write_json(stage/'probe-receipt.json', receipt)
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            record['status'] = 'Still running at bounded wait deadline; not terminated'
            raise UserError(f'Owned {name} PID {process.pid} exceeded the wait deadline; preserved and not killed')
        record.update(exit_code=code, finished=utcnow())
    if code:
        raise UserError(name+' failed; exact stdout/stderr and process receipt remain in '+str(stage))
    return stdout_path.read_text(encoding='utf-8', errors='replace')


def verify(home):
    if os.name != 'nt':
        raise UserError('This regression requires actual Windows file-sharing semantics')
    layout = Layout(home)
    if layout.home.drive.upper() != 'D:':
        raise UserError('Use the explicitly owned D: runtime for private journal-probe stages')
    guard = reserve()
    stage = layout.staging/('native-journal-probe-'+str(time.time_ns())+'-'+uuid.uuid4().hex[:6])
    if not stage.resolve().is_relative_to(layout.staging.resolve()) or stage.exists():
        raise UserError('Probe stage must be a fresh child of the owned staging directory')
    lock_path = REPO/'catalog/lock.json'
    lock_sha = digest(lock_path)
    lock = read_json(lock_path)
    mod = next((m for m in lock['mods'] if m['slug'] == 'awft-control-bridge'), None)
    if not mod or mod['version'] != '0.6.7':
        raise UserError('This reviewed probe requires the immutable bridge 0.6.7 pin')
    jar = layout.caches/'mods'/mod['filename']
    if not jar.is_file() or digest(jar) != mod['hashes']['sha256']:
        raise UserError('Cached bridge bytes do not match the exact current lock pin')
    gson = layout.server/'libraries/com/google/code/gson/gson/2.10.1/gson-2.10.1.jar'
    if not gson.is_file() or any(not (JDK/name).is_file() for name in ('javac.exe', 'java.exe')):
        raise UserError('Installed Gson 2.10.1 and the tested JDK 21.0.10 are required')
    source = REPO/'compat/probes/NativeJournalProbe.java'
    source_sha = digest(source)
    stage.mkdir(parents=True, exist_ok=False)
    classes = stage/'classes'
    classes.mkdir()
    probe_id = uuid.uuid4().hex
    receipt = {'format': 'awft-native-journal-probe:1', 'started': utcnow(), 'status': 'running',
               'candidate': lock['version'], 'source_lock_sha256': lock_sha,
               'probe_id': probe_id, 'probe_source_sha256': source_sha,
               'bridge': {'version': mod['version'], 'filename': jar.name, 'sha256': digest(jar)},
               'gson': {'version': '2.10.1', 'sha256': digest(gson)},
               'storage_check': guard, 'processes': [],
               'boundary': 'Actual Windows + pinned NativeJournal class; no Minecraft startup, server, client, world, multiplayer or final mechanism acceptance'}
    write_json(stage/'probe-receipt.json', receipt)
    try:
        cp = os.pathsep.join([str(jar), str(gson)])
        child([str(JDK/'javac.exe'), '-J-Xmx128m', '-J-XX:ActiveProcessorCount=2',
               '-proc:none', '-implicit:none', '--release', '21', '-classpath', cp,
               '-d', str(classes), str(source)], stage, 'compile-probe', receipt, 45)
        compiled = list(classes.rglob('*.class'))
        if len(compiled) != 1 or compiled[0].name != 'NativeJournalProbe.class':
            raise UserError('Probe compilation unexpectedly produced implementation classes')

        progress = stage/'status.json'
        old = (json.dumps({'probe_id': probe_id, 'state': 'old-reader-held-view'}, sort_keys=True)+'\n').encode()
        progress.write_bytes(old)
        old_sha = digest(progress)
        receipt['old_progress_sha256'] = old_sha
        # The ordinary Windows CRT reader used by Python omits delete sharing.
        # Prove the actual replacement denial before attributing Java's warning
        # to this handle, rather than assuming the platform's sharing behavior.
        with progress.open('rb') as reader:
            control = stage/'replacement-negative-control.tmp'
            control.write_bytes(b'{"state":"replacement-negative-control"}\n')
            try:
                os.replace(control, progress)
            except PermissionError as error:
                receipt['reader_lock'] = {'api': "Python open(path, 'rb')", 'replacement_denied': True,
                                          'winerror': getattr(error, 'winerror', None), 'error': str(error)}
            else:
                raise UserError('The ordinary reader allowed replacement; reader-lock regression was not exercised')
            if progress.read_bytes() != old or reader.read() != old:
                raise UserError('Negative control altered the original progress view')
            command = [str(JDK/'java.exe'), '-Xms32m', '-Xmx128m', '-XX:ActiveProcessorCount=2',
                       '-Djava.awt.headless=true', '-classpath', os.pathsep.join([str(classes), cp]),
                       'worldfortwo.bridge.NativeJournalProbe', str(stage), probe_id, old_sha, source_sha]
            output = child(command, stage, 'run-pinned-journal', receipt, 30)
            summary = json.loads(output.strip())
            if summary.get('state') != 'terminal-call-returned' or summary.get('probe_id') != probe_id:
                raise UserError('Headless Java did not return the actual terminal-call marker')
            if Path(summary['native_journal_code_source']).resolve() != jar.resolve():
                raise UserError('NativeJournal came from a different class source than the pinned bridge JAR')
            reader.seek(0)
            if reader.read() != old or progress.read_bytes() != old:
                raise UserError('Pinned NativeJournal altered the reader-held old progress bytes')

            terminals = list(stage.glob('journal-lock-probe-result-*.json'))
            if len(terminals) != 1:
                raise UserError('Expected one unique native immutable terminal JSON receipt')
            terminal = terminals[0]
            complete = terminal.with_name(terminal.name+'.complete')
            if not complete.is_file() or complete.read_text().strip() != digest(terminal):
                raise UserError('Native immutable terminal SHA sidecar is missing or invalid')
            actual = read_json(terminal)
            if (actual.get('probe_id') != probe_id or actual.get('state') != 'terminal-reached-after-reader-lock'
                or actual.get('previous_progress_sha256') != old_sha
                or actual.get('probe_source_sha256') != source_sha
                or actual.get('progress_call_returned') is not True
                or 'AccessDeniedException' not in actual.get('progress_publication_warning', '')):
                raise UserError('Native terminal contents do not prove continuation after the actual reader lock')
            temporary = read_json(stage/'status.json.tmp')
            if temporary.get('state') != 'progress-attempt' or temporary.get('probe_id') != probe_id:
                raise UserError('The attempted native mutable progress payload is not retained')
            receipt['verification'] = {'negative_control_replacement_denied': True,
                'ordinary_reader_open_during_progress_and_terminal': True,
                'native_access_denied_warning': actual['progress_publication_warning'],
                'progress_call_returned': True, 'old_progress_preserved': True,
                'immutable_terminal': terminal.name, 'terminal_sha256': digest(terminal),
                'complete_sidecar': complete.name, 'complete_sha_matches': True,
                'terminal_actual_state': actual['state'], 'pinned_native_class_source': summary['native_journal_code_source']}
        if digest(jar) != mod['hashes']['sha256'] or digest(lock_path) != lock_sha:
            raise UserError('The reviewed bridge or source lock changed during the probe')
        receipt.update(status='pass: actual pinned NativeJournal survived the Windows reader lock', finished=utcnow())
    except BaseException as error:
        receipt.update(status='failed; all stage files and process receipts preserved', error=str(error), finished=utcnow())
        write_json(stage/'probe-receipt.json', receipt)
        raise
    write_json(stage/'probe-receipt.json', receipt)
    print(json.dumps({'receipt': str(stage/'probe-receipt.json'), 'status': receipt['status'],
                      'bridge_sha256': receipt['bridge']['sha256'], 'verification': receipt['verification'],
                      'boundary': receipt['boundary']}), flush=True)
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path(r'D:\A World for Two'))
    args = parser.parse_args()
    try:
        verify(args.home)
    except (UserError, OSError, ValueError, AssertionError) as error:
        raise SystemExit(str(error))
