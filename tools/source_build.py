"""Fetch a pinned author tree and run a private, disk-bounded Gradle build.

Source bytes are checked against Git blob IDs; dependencies stay in the D: cache.
The output is a candidate, never an automatically published pack update.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import subprocess
import time
import urllib.request
import zipfile
from pathlib import Path

import psutil

from control_room.common import GiB, Layout, REPO, UserError, digest, read_json, utcnow, write_json
from control_room.storage import Storage, tree_size


def fetch_tree(pin, destination):
    if destination.exists():
        raise UserError("Source destination must be new")
    url = f"https://codeload.github.com/{pin['repository']}/zip/{pin['commit']}"
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "a-world-for-two/source-build"}), timeout=30) as response:
        raw = response.read(8 * 1024 * 1024 + 1)
    if len(raw) > 8 * 1024 * 1024:
        raise UserError("Source archive exceeded its allocation")
    expected = {v['path']: v for v in pin['tree'] if v['type'] == 'blob'}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        files = [v for v in archive.infolist() if not v.is_dir()]
        if len(files) != len(expected) or sum(v.file_size for v in files) > 4 * 1024 * 1024:
            raise UserError("Source archive differs from the reviewed tree or allocation")
        for member in files:
            relative = member.filename.split('/', 1)[1]
            item = expected.get(relative)
            if not item or Path(relative).is_absolute() or '..' in Path(relative).parts or ':' in relative:
                raise UserError("Unexpected source archive path")
            data = archive.read(member)
            git_hash = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            if len(data) != item['size'] or git_hash != item['sha']:
                raise UserError("Source Git blob integrity failed: " + relative)
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)


def run_gradle(home, key):
    layout = Layout(home)
    storage = Storage(layout)
    storage.reserve(8 * GiB)
    pin = read_json(REPO / 'catalog/source-builds.json')[key]
    work = layout.staging / 'source-builds' / (key + '-' + str(time.time_ns()))
    source = work / 'source'
    fetch_tree(pin, source)
    # Exact compile-only files are copied from their already verified local cache.
    libs = source / 'libs'
    libs.mkdir(exist_ok=True)
    for target, slug in pin.get('libraries', {}).items():
        item = next(m for m in read_json(REPO / 'catalog/lock.json')['mods'] if m['slug'] == slug)
        cached = layout.caches / 'mods' / item['filename']
        alg = 'sha512' if 'sha512' in item['hashes'] else 'sha256'
        if digest(cached, alg) != item['hashes'][alg]:
            raise UserError('Compile dependency failed integrity: ' + slug)
        (libs / target).write_bytes(cached.read_bytes())
        if slug == 'xaeros-world-map':
            with zipfile.ZipFile(cached) as archive:
                nested = [n for n in archive.namelist() if n.endswith('.jar') and 'xaerolib' in n]
                if len(nested) != 1:
                    raise UserError('Expected one exact bundled Xaero library')
                (libs / Path(nested[0]).name).write_bytes(archive.read(nested[0]))
    for item in pin.get('compile_only', []):
        cached = layout.caches / 'build-libs' / item['filename']
        if not cached.is_file() or cached.stat().st_size != item['size'] or digest(cached) != item['sha256']:
            raise UserError('Import the reviewed compile-only author download: ' + item['source'])
        (libs / item['filename']).write_bytes(cached.read_bytes())
    env = dict(os.environ, JAVA_HOME=r'C:\Program Files\Java\jdk-21.0.10',
               GRADLE_USER_HOME=str(layout.caches / 'gradle'), TEMP=str(work / 'temp'), TMP=str(work / 'temp'))
    Path(env['TEMP']).mkdir()
    env['PATH'] = env['JAVA_HOME'] + r'\bin;' + env['PATH']
    watched = [work, layout.caches / 'gradle']
    before = sum(tree_size(p) for p in watched)
    receipt = {'at': utcnow(), 'source': pin['repository'], 'commit': pin['commit'], 'work': str(work),
               'maximum_additional_bytes': 8 * GiB, 'status': 'running'}
    write_json(work / 'build-receipt.json', receipt)
    children = {}
    with (work / 'gradle.log').open('x', encoding='utf-8') as log:
        process = subprocess.Popen(['cmd.exe', '/d', '/c', 'gradlew.bat', '--no-daemon', '--max-workers=2', 'build'],
            cwd=source, env=env, stdout=log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        owned = psutil.Process(process.pid)
        receipt['pid'], receipt['created'] = process.pid, owned.create_time()
        write_json(work / 'build-receipt.json', receipt)
        deadline = time.monotonic() + 1200
        try:
            while process.poll() is None:
                children.update({p.pid: p.create_time() for p in owned.children(recursive=True)})
                storage.checkpoint(8 * GiB)
                if time.monotonic() > deadline or sum(tree_size(p) for p in watched) - before > 6 * GiB:
                    raise UserError('Source build reached its time or disk checkpoint; files and logs preserved')
                time.sleep(1)
            if process.returncode:
                raise UserError('Source build failed; inspect ' + str(work / 'gradle.log'))
            receipt['status'] = 'built candidate; runtime unverified'
            receipt['outputs'] = [{'path': str(p), 'bytes': p.stat().st_size, 'sha256': digest(p)}
                                  for p in sorted((source / 'build/libs').glob('*.jar'))]
            return receipt
        except Exception as exc:
            receipt['status'], receipt['error'] = 'failed', str(exc)
            for pid, created in reversed(list(children.items()) + [(owned.pid, owned.create_time())]):
                with contextlib.suppress(psutil.Error):
                    child = psutil.Process(pid)
                    if child.create_time() == created:
                        child.terminate()
            raise
        finally:
            write_json(work / 'build-receipt.json', receipt)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('key')
    parser.add_argument('--home', type=Path, default=Path(r'D:\A World for Two'))
    args = parser.parse_args()
    print(json.dumps(run_gradle(args.home, args.key), indent=2))
