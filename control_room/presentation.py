"""Local, reversible camera presets for closed, explicitly owned Prism clients."""
from __future__ import annotations

import hashlib
import json
import re
import tomllib
from pathlib import Path

import psutil

from .common import REPO, UserError, atomic_write, contained, digest, read_json, utcnow, write_json

CAMERA = 'cinematic-client.toml'
AMBIENT = 'ambient_camera-client.toml'
RESPAWN = 'cinematic_respawn.properties'
FILES = (CAMERA, AMBIENT, RESPAWN)
PRESETS = {
    'high-quality': {'label': 'High Quality', 'description': 'Full station camera effects and smooth idle cuts; idle view capped at 30 FPS.',
        'camera': dict(approachSpeed=100, leaveSpeed=100, leanStrength=100, sceneZoom=100, quickMode=1, letterbox=True, livingCamera=True, cameraShake=True, screenFlash=True),
        'ambient': dict(enabled=True, hardCuts=False, sceneryFocusDistance=32.0, ambientFpsLimit=30), 'respawn': 1.0},
    'balanced': {'label': 'Balanced', 'description': 'Gentler camera motion, shorter idle focus range and fewer screen effects.',
        'camera': dict(approachSpeed=125, leaveSpeed=125, leanStrength=70, sceneZoom=70, quickMode=1, letterbox=True, livingCamera=False, cameraShake=False, screenFlash=False),
        'ambient': dict(enabled=True, hardCuts=True, sceneryFocusDistance=24.0, ambientFpsLimit=30), 'respawn': 1.25},
    'minimal': {'label': 'Minimal', 'description': 'Idle camera off, quick workstation entry, no zoom or shake, and a shorter skippable respawn.',
        'camera': dict(approachSpeed=200, leaveSpeed=200, leanStrength=0, sceneZoom=0, quickMode=2, letterbox=False, livingCamera=False, cameraShake=False, screenFlash=False),
        'ambient': dict(enabled=False, hardCuts=True, sceneryFocusDistance=24.0, ambientFpsLimit=30), 'respawn': 2.0},
}


def revision(instance):
    hashes = {}
    for name in FILES:
        path = contained(instance, '.minecraft/config/' + name)
        if path.is_file() and path.stat().st_size > 1024 * 1024:
            raise UserError('Client camera configuration exceeds its editing limit')
        hashes[name] = digest(path) if path.is_file() else None
    return hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()


def closed(instance):
    minecraft = contained(instance, '.minecraft')
    for process in psutil.process_iter(['name']):
        if (process.info['name'] or '').lower() not in ('java.exe', 'javaw.exe', 'java', 'javaw'):
            continue
        try:
            if Path(process.cwd()).resolve() == minecraft:
                raise UserError('Close this Minecraft client before changing its camera preset')
        except psutil.NoSuchProcess:
            pass
        except psutil.AccessDenied as exc:
            raise UserError('Cannot verify whether this Minecraft client is closed') from exc


def toml_update(text, section, updates):
    """Preserve all unrelated native fields and comments."""
    tomllib.loads(text)
    lines, result, active, seen = text.splitlines(True), [], False, set()
    for line in lines:
        header = re.match(r'\s*\[([^\[\]]+)\]\s*(?:#.*)?$', line.rstrip())
        if header:
            if active:
                result.extend(f'{key} = {json.dumps(value)}\n' for key, value in updates.items() if key not in seen)
            active = header[1] == section
        matched = re.match(r'(\s*)([A-Za-z][A-Za-z0-9_]*)\s*=\s*[^#\r\n]+', line) if active else None
        if matched and matched[2] in updates:
            key = matched[2]
            if key in seen:
                raise UserError('Duplicate native camera configuration field')
            seen.add(key)
            line = line[:matched.start()] + matched[1] + key + ' = ' + json.dumps(updates[key]) + ' ' + line[matched.end():]
        result.append(line if line.endswith('\n') else line + '\n')
    if active:
        result.extend(f'{key} = {json.dumps(value)}\n' for key, value in updates.items() if key not in seen)
    elif section not in tomllib.loads(text):
        result.append('\n[' + section + ']\n')
        result.extend(f'{key} = {json.dumps(value)}\n' for key, value in updates.items())
    output = ''.join(result)
    parsed = tomllib.loads(output)[section]
    if any(parsed.get(key) != value for key, value in updates.items()):
        raise UserError('The native camera configuration no longer matches the pinned preset schema')
    return output.encode()


def apply(layout, storage, ident, preset, expected):
    if preset not in PRESETS and preset != 'restore':
        raise UserError('Choose High Quality, Balanced or Minimal')
    instance = contained(layout.home, 'instances/' + str(ident))
    receipt = read_json(instance / 'awft-owned.json', {})
    if receipt.get('format') != 'awft-owned-client:1' or Path(receipt.get('root', '')).resolve() != instance:
        raise UserError('Choose an owned A World for Two client')
    with layout.mutation:
        closed(instance)
        if expected != revision(instance):
            raise UserError('Client camera settings changed. Refresh before applying this preset.')
        originals, changes = {}, {}
        for name in FILES:
            path = contained(instance, '.minecraft/config/' + name)
            if path.exists() and path.stat().st_size > 1024 * 1024:
                raise UserError('Client camera configuration exceeds its editing limit')
            originals[name] = path.read_bytes() if path.exists() else None
        prior = read_json(instance / 'awft-presentation.json', {})
        if preset == 'restore':
            if set(prior.get('previous', {})) != set(FILES):
                raise UserError('No complete prior camera configuration is available')
            for name, sha in prior['previous'].items():
                if sha is None:
                    changes[name] = None
                else:
                    if not re.fullmatch(r'[a-f0-9]{64}', sha):
                        raise UserError('Invalid camera history receipt')
                    path = contained(instance, 'awft-presentation-history/' + sha + '-' + name)
                    if not path.is_file() or path.stat().st_size > 1024 * 1024 or digest(path) != sha:
                        raise UserError('Prior camera configuration failed its integrity check')
                    changes[name] = path.read_bytes()
        else:
            p = PRESETS[preset]
            for name, table, values in ((CAMERA, 'camera', p['camera']), (AMBIENT, 'ambientCamera', p['ambient'])):
                text = (originals[name] or (REPO / 'packwiz/config' / name).read_bytes()).decode('utf-8-sig')
                changes[name] = toml_update(text, table, values)
            text = (originals[RESPAWN] or (REPO / 'packwiz/config' / RESPAWN).read_bytes()).decode('utf-8-sig')
            for key, value in {'allow_skip': 'true', 'auto_respawn': 'true', 'respawn_sequence_speed': str(p['respawn'])}.items():
                pattern = r'(?m)^\s*' + key + r'\s*=[^\r\n]*'
                text = re.sub(pattern, key + '=' + value, text) if re.search(pattern, text) else text + '\n' + key + '=' + value + '\n'
            changes[RESPAWN] = text.encode()
        history = instance / 'awft-presentation-history'
        size = sum(p.stat().st_size for p in history.glob('*') if p.is_file()) if history.exists() else 0
        if size + sum(len(v) for v in originals.values() if v is not None) > 8 * 1024 * 1024:
            raise UserError('Camera history reached its 8 MiB limit; preserve and clear old history before applying another preset')
        storage.reserve(16 * 1024 * 1024)
        previous = {}
        for name, raw in originals.items():
            sha = hashlib.sha256(raw).hexdigest() if raw is not None else None
            previous[name] = sha
            if raw is not None:
                atomic_write(contained(instance, 'awft-presentation-history/' + sha + '-' + name), raw)
        result = {'at': utcnow(), 'preset': preset, 'previous': previous, 'status': 'prepared'}
        write_json(instance / 'awft-presentation.json', result)
        try:
            for name, raw in changes.items():
                path = contained(instance, '.minecraft/config/' + name)
                path.unlink(missing_ok=True) if raw is None else atomic_write(path, raw)
        except OSError:
            for name, raw in originals.items():
                path = contained(instance, '.minecraft/config/' + name)
                path.unlink(missing_ok=True) if raw is None else atomic_write(path, raw)
            result['status'] = 'failed; original files restored'
            write_json(instance / 'awft-presentation.json', result)
            raise
        result.update(revision=revision(instance), status='Applied to this closed local client; takes effect on its next launch')
        write_json(instance / 'awft-presentation.json', result)
        return result
