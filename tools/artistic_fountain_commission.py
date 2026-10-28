"""Bind one real, fresh native R5 verification to a private fountain request.

This producer writes only an immutable request and its ownership receipt. It
never invokes a command, reads region files, seeds water, or operates the server.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tomllib
import zipfile

from control_room.common import UserError
from tools.playtest import guard

HOME = Path(r'D:\A World for Two\staging\world-tests\20261027T053650Z-artistic')
CANDIDATE = '0.1.0-candidate.45'
BRIDGE = '0.6.31'
PACK_SHA = '93237c82beee383d85a532df178d51d29646d168f6e322ed3baeeba986cbdce1'
BRIDGE_SHA = 'd5126437fb6e041d9a6f2bb021cb81f9721092b76399fc34156ccd111a02e815'
CLASS_SHA = 'ac53fb7efee4c95d26cd813a8189de0384a3ad79f15fbe1fbe148ecb66e823ae'
BACKUP_ID = '20261028T022348Z-3c15d0'
BACKUP_SHA = '0ae2cd00d57269b35d15ecc96a6d9d7e2c44f88f8e39d3ec5522cee4037229e8'
PLAN_SHA = 'ce85c167a6c3e831bdbb33996d17352c6902329858b4f65d8349ac222f1942be'
MANIFEST_SHA = '28d03159a83ba4d3f3fa7d7b58e1c559a6698ac2c2c4d447aa34b8e8f7895145'
BUNDLE = 'staging/artistic-fountain-r5-ACTUAL-DRY45-1793155163050141000'
STATUS = 'verified actual block identities, orientation, block entities and supplied inventories'
BLOCKS = 2532


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def owned(home, name, *, regular=True):
    """Reject lexical escape, symlinks and Windows junction/reparse ancestors."""
    home = Path(home).absolute()
    p = Path(name)
    if any(part in ('.', '..') for part in p.parts):
        raise UserError('Evidence traversal refused')
    if not p.is_absolute():
        p = home/p
    p = p.absolute()
    if not p.is_relative_to(home):
        raise UserError('Evidence must stay inside the actual owned home')
    for q in [p, *list(p.parents)[:len(p.parents)-len(home.parents)]]:
        info = os.lstat(q)
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise UserError('Redirected evidence or directory refused')
    if p.resolve(strict=True) != p or home.resolve(strict=True) != home:
        raise UserError('Evidence resolves through a foreign path')
    if regular and not stat.S_ISREG(os.lstat(p).st_mode):
        raise UserError('Evidence must be a regular file')
    return p


def evidence(home, name, limit, expected=None):
    p = owned(home, name)
    if not 0 < p.stat().st_size <= limit:
        raise UserError('Evidence size exceeds its finite bound')
    with p.open('rb') as stream:
        raw = stream.read(limit+1)
    if not 0 < len(raw) <= limit or expected is not None and sha(raw) != expected:
        raise UserError('Exact evidence bytes differ')
    return p, raw, {'path': p.relative_to(home).as_posix(), 'bytes': len(raw), 'sha256': sha(raw)}


def document(home, name, limit, expected=None):
    p, raw, ref = evidence(home, name, limit, expected)
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, ValueError) as exc:
        raise UserError('Evidence is not bounded valid JSON') from exc
    if not isinstance(value, dict):
        raise UserError('Evidence must be a JSON object')
    return value, ref


def instant(value):
    try:
        parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            raise ValueError('naive timestamp')
        return parsed.astimezone(dt.timezone.utc)
    except (AttributeError, TypeError, ValueError) as exc:
        raise UserError('Actual native proof needs a valid timezone-qualified instant') from exc


def check_proof(proof, now):
    if (proof.get('operation') != 'verify' or proof.get('status') != STATUS
            or proof.get('plan_sha256') != PLAN_SHA or proof.get('blocks') != BLOCKS
            or type(proof.get('blocks')) is not int or 'error' in proof
            or proof.get('cleanup_required') is not False):
        raise UserError('A successful complete actual R5 native verification is required')
    for field in ('failures', 'temporary_tickets_remaining', 'pending_shared_chunk_futures'):
        if type(proof.get(field)) is not int or proof[field] != 0:
            raise UserError('Native verification has unresolved failure/cleanup/ticket custody')
    if 'cleanup_failures' in proof and (type(proof['cleanup_failures']) is not int or proof['cleanup_failures'] != 0):
        raise UserError('Native cleanup failure remains')
    started, finished = instant(proof.get('started')), instant(proof.get('finished'))
    if started > finished or finished > now or now-finished > dt.timedelta(minutes=30):
        raise UserError('Native verification is stale, future-dated or out of order')


def check_context(home, owner, active, installed, settings, registry, checkpoint):
    world = home/'world/RosewaterArtistic'
    if (owner.get('format') != 'awft-artistic-stage:1' or Path(owner.get('home', '')).absolute() != home
            or owner.get('minecraft_port') != 25575 or settings.get('port') != 25575
            or settings.get('permanent_world') is not False
            or Path(owner.get('active_world_path', '')).absolute() != world
            or Path(registry.get('world_path', '')).absolute() != world):
        raise UserError('Exact disposable artistic owner, world and private port required')
    if (active.get('version') != CANDIDATE or installed.get('pack_version') != CANDIDATE
            or active.get('pack_sha256') != PACK_SHA or installed.get('pack_sha256') != PACK_SHA
            or owner.get('pack_sha256') != PACK_SHA):
        raise UserError('Actual candidate45 ownership/installed pack custody differs')
    if (checkpoint.get('verified') is not True or checkpoint.get('id') != BACKUP_ID
            or checkpoint.get('sha256') != BACKUP_SHA or owner.get('backup') != BACKUP_ID
            or owner.get('backup_sha256') != BACKUP_SHA):
        raise UserError('Exact retained checkpoint and owner binding required')


def require_dry_manifest(manifest):
    if manifest.get('actual_dry_checkpoint') is not True or 'actual-dry-native-BEFORE.json' not in manifest.get('files',{}):
        raise UserError('A fresh actual stopped dry R5 bundle is required; a wet/prospective reset bundle cannot commission')


def prepare(home, native_verify):
    home = Path(home).absolute()
    if home != HOME:
        raise UserError('This helper admits only the exact private artistic home')
    owned(home, home, regular=False)
    proof_path = owned(home, native_verify)
    if (proof_path.parent != home/'dashboard/settlement'
            or not re.fullmatch(r'settlement-result-[a-f0-9-]{36}\.json', proof_path.name)):
        raise UserError('Actual native proof must originate in this owned server journal')
    # Read and reject absent/failed/stale evidence BEFORE admitting any writer.
    proof, proof_ref = document(home, proof_path, 65536)
    check_proof(proof, dt.datetime.now(dt.timezone.utc))
    _, marker, marker_ref = evidence(home, proof_path.with_name(proof_path.name+'.complete'), 128)
    if marker.decode('ascii').strip() != proof_ref['sha256']:
        raise UserError('Actual native completion marker differs')
    owner, _ = document(home, 'dashboard/artistic-owner.json', 65536)
    active, _ = document(home, 'packwiz/active.json', 65536)
    installed, _ = document(home, 'server/installed.json', 1024**2)
    settings, _ = document(home, 'dashboard/settings.json', 65536)
    registry, _ = document(home, 'dashboard/settlement/registry.json', 8*1024**2)
    checkpoint, _ = document(home, 'dashboard/settlement/backup-receipt.json', 4096)
    check_context(home, owner, active, installed, settings, registry, checkpoint)
    owned(home, home/'world/RosewaterArtistic', regular=False)
    geometry, geometry_ref = document(home, BUNDLE+'/plaza.json', 4*1024**2, PLAN_SHA)
    manifest, manifest_ref = document(home, BUNDLE+'/manifest.json', 2*1024**2, MANIFEST_SHA)
    require_dry_manifest(manifest)
    if (len(geometry.get('blocks', [])) != BLOCKS or geometry.get('commands') != []
            or geometry.get('block_entities') != [] or geometry.get('backup_sha256') != BACKUP_SHA
            or geometry.get('world_path') != registry['world_path'] or geometry.get('seed') != registry['seed']
            or manifest.get('checkpoint_sha256') != BACKUP_SHA
            or manifest.get('files', {}).get('plaza.json') != {'sha256': PLAN_SHA, 'bytes': geometry_ref['bytes']}):
        raise UserError('Reviewed complete actual dry R5 geometry and manifest differ')
    jar_name = 'awft-control-bridge-'+BRIDGE+'.jar'
    if installed.get('files', {}).get(jar_name) != BRIDGE_SHA:
        raise UserError('Installed bridge journal differs')
    jar_path, _, jar_ref = evidence(home, 'server/mods/'+jar_name, 4*1024**2, BRIDGE_SHA)
    with zipfile.ZipFile(jar_path) as archive:
        entry = 'worldfortwo/bridge/NativeFountainSupport.class'
        if not 0 < archive.getinfo(entry).file_size <= 256*1024:
            raise UserError('Finite installed native helper required')
        if sha(archive.read(entry)) != CLASS_SHA:
            raise UserError('Actual installed fountain helper class differs')
        entry = 'META-INF/neoforge.mods.toml'
        if archive.getinfo(entry).file_size > 65536:
            raise UserError('Finite bridge metadata required')
        meta = tomllib.loads(archive.read(entry).decode())
        if not any(m.get('modId') == 'awft_control_bridge' and m.get('version') == BRIDGE for m in meta.get('mods', [])):
            raise UserError('Actual installed bridge version differs')
    request = {'format': 'awft-native-fountain:1', 'candidate': CANDIDATE, 'bridge': BRIDGE,
               'pack_sha256': PACK_SHA, 'seed': str(registry['seed']), 'world_path': registry['world_path'],
               'backup_sha256': BACKUP_SHA, 'native_class_sha256': CLASS_SHA,
               'geometry': geometry_ref, 'native_verify': proof_ref}
    raw = (json.dumps(request, separators=(',', ':'))+'\n').encode()
    if len(raw) > 65536:
        raise UserError('Request exceeded its finite native protocol bound')
    request_sha = sha(raw)
    journal = owned(home, home/'dashboard/settlement', regular=False)
    output = journal/('fountain-'+request_sha[:16])
    if output.exists():
        raise UserError('Preserve the existing immutable request; do not recreate/replay it')
    reserve = guard(4*1024**2, 1024**2)
    # Recheck freshness and exact receipt bytes immediately before the bounded writer.
    check_proof(document(home, proof_path, 65536, proof_ref['sha256'])[0], dt.datetime.now(dt.timezone.utc))
    receipt = {'format': 'awft-fountain-request-owner:1', 'created': dt.datetime.now(dt.timezone.utc).isoformat(),
               'home': str(home), 'request_sha256': request_sha, 'bundle': output.name,
               'producer_source_sha256': sha(Path(__file__).read_bytes()), 'geometry_manifest': manifest_ref,
               'native_completion_marker': marker_ref, 'installed_bridge': jar_ref,
               'storage_guard': reserve, 'native_actions': 0, 'world_writes': 0,
               'authority': 'REQUEST ONLY. Parent must serialize typed inspect/commission after current shared native maintenance; no operation was invoked.'}
    receipt_raw = (json.dumps(receipt, indent=2)+'\n').encode()
    if len(raw)+len(receipt_raw) > 128*1024:
        raise UserError('Finite request allocation exceeded')
    output.mkdir()
    for name, content in (('request.json', raw), ('ownership-receipt.json', receipt_raw)):
        with (output/name).open('xb') as stream:
            stream.write(content)
    (output/'ownership-receipt.json.complete').write_text(sha(receipt_raw)+'\n', encoding='ascii')
    return {'request': str(output/'request.json'), 'bundle': output.name, 'sha256': request_sha,
            'native_command_parent_only': 'awftfountain commission '+output.name+' '+request_sha,
            'native_actions': 0, 'world_writes': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=HOME)
    parser.add_argument('--native-verify', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.home, args.native_verify), indent=2))
