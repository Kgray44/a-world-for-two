"""Bounded artwork history and local client presentation management."""
from __future__ import annotations

import hashlib
import io
import re
import time
import zipfile
import uuid
from datetime import datetime
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from .common import REPO, UserError, atomic_write, contained, digest, read_json, utcnow, write_json

MAX_IMAGE = 8 * 1024 * 1024


def validate_telemetry(value):
    if not isinstance(value, dict) or type(value.get('available')) is not bool:
        raise ValueError('Invalid cinematic telemetry')
    clean = {'available': value['available'], 'scenes': [], 'first_joins': {}, 'executions': []}
    scenes, seen, executions = value.get('scenes', []), value.get('first_joins', {}), value.get('executions', [])
    if not isinstance(scenes, list) or len(scenes) > 64 or not isinstance(seen, dict) or len(seen) > 128 or not isinstance(executions, list) or len(executions) > 50:
        raise ValueError('Cinematic telemetry exceeds its limits')
    for scene in scenes:
        if not isinstance(scene, dict) or not re.fullmatch(r'[a-z0-9_.-]+:[a-z0-9_/.-]{1,100}', scene.get('id', '')):
            raise ValueError('Invalid cinematic identifier')
        if type(scene.get('duration_ticks')) is not int or not 1 <= scene['duration_ticks'] <= 72000 or type(scene.get('events')) is not int or not 0 <= scene['events'] <= 10000 or scene.get('camera_mode') not in ('ABSOLUTE', 'RELATIVE_TO_ANCHOR'):
            raise ValueError('Invalid cinematic metadata')
        clean['scenes'].append(scene)
    for ident, at in seen.items():
        if not re.fullmatch(r'[a-f0-9-]{36}', ident) or not isinstance(at, str) or len(at) > 40:
            raise ValueError('Invalid cinematic first-join record')
        clean['first_joins'][ident] = at
    for execution in executions:
        if not isinstance(execution, dict):
            raise ValueError('Invalid cinematic journal')
        row = {}
        for key, limit in (('at', 40), ('player', 16), ('scene', 120), ('reason', 80), ('status', 300)):
            text = execution.get(key)
            if not isinstance(text, str) or len(text) > limit:
                raise ValueError('Invalid cinematic journal label')
            row[key] = text
        clean['executions'].append(row)
    for key in ('error', 'configuration_error'):
        if key in value:
            clean[key] = str(value[key])[:500]
    return clean


def inspect_image(raw):
    if not 0 < len(raw) <= MAX_IMAGE:
        raise UserError('Choose a JPEG or PNG image no larger than 8 MiB')
    try:
        with Image.open(io.BytesIO(raw)) as image:
            if image.format not in ('JPEG', 'PNG') or getattr(image, 'n_frames', 1) != 1:
                raise UserError('Use a still JPEG or PNG image')
            if not 320 <= image.width <= 8192 or not 180 <= image.height <= 8192 or image.width * image.height > 16_777_216:
                raise UserError('Use an image between 320 × 180 and 16 megapixels, with each side at most 8192 pixels')
            result = {'width': image.width, 'height': image.height, 'format': image.format,
                      'extension': '.png' if image.format == 'PNG' else '.jpg'}
            image.verify()
        with Image.open(io.BytesIO(raw)) as image:
            image.load()
    except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise UserError('The image could not be verified as a complete JPEG or PNG') from exc
    return dict(result, sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


class Cinematics:
    def __init__(self, layout, storage, server, players, measurements=lambda: {}):
        self.layout, self.storage, self.server, self.players = layout, storage, server, players
        self.measurements = measurements
        self.path = layout.state / 'cinematic-background.json'
        self.folder = layout.state / 'menu-artwork'
        self.settings_path = layout.state / 'cinematics.json'

    def configuration(self):
        return read_json(self.settings_path, {'enabled': True, 'first_join': True, 'intro_scene': 'awft:intro', 'triggers': []})

    def revision(self):
        return digest(self.settings_path) if self.settings_path.exists() else 'empty'

    def settings(self, changes, expected):
        if not isinstance(changes, dict) or set(changes) - {'enabled', 'first_join', 'intro_scene'}:
            raise UserError('Choose a supported server cinematic setting')
        for key, value in changes.items():
            if key == 'intro_scene':
                if not isinstance(value, str) or not re.fullmatch(r'[a-z0-9_.-]+:[a-z0-9_/.-]{1,100}', value):
                    raise UserError('Choose a valid namespaced scene identifier')
            elif type(value) is not bool:
                raise UserError('Cinematic switches must be true or false')
        with self.layout.mutation:
            if expected != self.revision():
                raise UserError('Cinematic settings changed. Refresh before saving.')
            self.storage.reserve(1024 * 1024)
            updated = self.configuration() | changes
            write_json(self.settings_path, updated)
            return updated

    def trigger(self, location, scene, expected, ident=None, enabled=False):
        from .atlas import Atlas
        point = Atlas(self.layout, self.storage, self.server, self.players, None).validate(dict(location, category='Cinematic trigger')) if isinstance(location, dict) else None
        if not point or not isinstance(scene, str) or not re.fullmatch(r'[a-z0-9_.-]+:[a-z0-9_/.-]{1,100}', scene) or type(enabled) is not bool:
            raise UserError('Choose a valid Atlas location and scene')
        radius = location.get('radius', 32)
        if type(radius) is not int or not 16 <= radius <= 128:
            raise UserError('Location trigger radius must be 16–128 blocks')
        with self.layout.mutation:
            if expected != self.revision():
                raise UserError('Cinematic settings changed. Refresh before saving.')
            config = self.configuration()
            if ident and not any(t['id'] == ident for t in config['triggers']):
                raise UserError('Trigger not found')
            if not ident and len(config['triggers']) >= 64:
                raise UserError('At most 64 location triggers can be configured')
            self.storage.reserve(1024 * 1024)
            value = {k: point[k] for k in ('name', 'dimension', 'x', 'y', 'z')}
            value.update(id=ident or uuid.uuid4().hex, scene=scene, radius=radius, enabled=enabled)
            config['triggers'] = [t for t in config['triggers'] if t['id'] != ident] + [value]
            write_json(self.settings_path, config)
            return value

    def remove_trigger(self, ident, expected, confirmed=False):
        with self.layout.mutation:
            if confirmed is not True or expected != self.revision():
                raise UserError('Confirm removal against the current trigger settings')
            config = self.configuration()
            if not any(t['id'] == ident for t in config['triggers']):
                raise UserError('Trigger not found')
            self.storage.reserve(1024 * 1024)
            config['triggers'] = [t for t in config['triggers'] if t['id'] != ident]
            write_json(self.settings_path, config)
            return {'removed': ident}

    def runtime(self):
        sample = self.measurements()
        try:
            age = time.time() - datetime.fromisoformat((sample.get('tick_at') or '').replace('Z', '+00:00')).timestamp()
            if self.server.running() and -2 <= age <= 15:
                return sample.get('cinematics', {})
        except ValueError:
            pass
        return {}

    def action(self, name, action, scene=None, notify=lambda _: None):
        who = self.players.details(name)
        if not who['online'] or 'cinematics' not in who['capabilities'] or not self.runtime().get('available'):
            raise UserError('Replay and stop require an online player and fresh Lumiera bridge telemetry')
        if action not in ('play', 'stop', 'skip'):
            raise UserError('Choose play, skip, or stop')
        if action == 'play' and not any(s['id'] == scene for s in self.runtime().get('scenes', [])):
            raise UserError('Choose a scene actually loaded by Lumiera')
        self.storage.reserve(2 * 1024 * 1024)
        ident = uuid.uuid4().hex
        path = self.layout.state / 'cinematic-requests' / (ident + '.json')
        write_json(path, {'id': ident, 'at': utcnow(), 'uuid': who['uuid'], 'action': action, 'scene': scene})
        self.server._write('awft cinematic ' + ident)
        end = time.monotonic() + 10
        while time.monotonic() < end:
            result = read_json(path.with_suffix('.result.json'))
            if result:
                if result['status'] == 'refused':
                    raise UserError(result.get('error', 'Lumiera refused the request'))
                return result
            time.sleep(.1)
        raise UserError('The cinematic command is pending. Inspect the console before retrying.')

    def current(self):
        saved = read_json(self.path)
        if saved:
            return saved
        source = read_json(REPO / 'catalog/menu-artwork.json')
        return dict(source, extension='.png' if source.get('format') == 'PNG' else '.jpg', source='supplied artwork', updated=source.get('updated', source['added']))

    def image(self, ident=None):
        current = self.current()
        if ident is None or ident == current['sha256']:
            candidate = contained(self.layout.state, 'menu-artwork/' + current['sha256'] + current['extension'])
            if candidate.is_file():
                return candidate
            if self.path.exists():
                raise UserError('The selected artwork file is missing. Restore a saved version from history.')
            return REPO / 'assets/menu/a-world-for-two-background.jpg'
        if not isinstance(ident, str) or not re.fullmatch(r'[a-f0-9]{64}', ident):
            raise UserError('Choose an artwork version from history')
        for extension in ('.png', '.jpg'):
            candidate = contained(self.layout.state, 'menu-artwork/' + ident + extension)
            if candidate.is_file():
                return candidate
        raise UserError('Artwork version not found')

    def history(self):
        rows = []
        for path in self.folder.glob('*.json'):
            if re.fullmatch(r'[a-f0-9]{64}\.json', path.name) and path.stat().st_size < 4096:
                rows.append(read_json(path))
        return sorted(rows, key=lambda r: r['updated'], reverse=True)

    def upload(self, raw, expected):
        info = inspect_image(raw)
        with self.layout.mutation:
            if expected != self.current()['sha256']:
                raise UserError('The background changed. Refresh its preview before applying another image.')
            existing = self.history()
            if len(existing) >= 20 and not any(r['sha256'] == info['sha256'] for r in existing):
                raise UserError('Artwork history contains 20 versions. Export and remove an unused version before adding another.')
            self.storage.reserve(3 * MAX_IMAGE + 1024 * 1024)
            # Preserve the prior original once, with its real format and unchanged bytes.
            previous = self.current()
            previous_bytes = self.image().read_bytes()
            previous_info = inspect_image(previous_bytes)
            previous_info.update(updated=previous.get('updated', utcnow()), source='previous background')
            atomic_write(self.folder / (previous_info['sha256'] + previous_info['extension']), previous_bytes)
            write_json(self.folder / (previous_info['sha256'] + '.json'), previous_info)
            info.update(updated=utcnow(), source='Control Room upload')
            atomic_write(self.folder / (info['sha256'] + info['extension']), raw)
            write_json(self.folder / (info['sha256'] + '.json'), info)
            write_json(self.path, info)
            return dict(info, note='Background saved without altering the image. Apply it to a local client or export the menu update.')

    def restore(self, ident, expected):
        return self.upload(self.image(ident).read_bytes(), expected)

    def remove(self, ident, confirmed=False):
        if confirmed is not True or ident == self.current()['sha256']:
            raise UserError('Choose and confirm an inactive artwork version')
        with self.layout.mutation:
            path = self.image(ident)
            if not path.is_relative_to(self.folder.resolve()):
                raise UserError('Only saved inactive artwork can be removed')
            path.unlink()
            contained(self.layout.state, 'menu-artwork/' + ident + '.json').unlink(missing_ok=True)
        return {'removed': ident}

    def clients(self):
        from .presentation import revision
        rows = []
        root = self.layout.home / 'instances'
        for folder in root.iterdir():
            if folder.is_symlink() or folder.is_junction() or not folder.is_dir():
                continue
            receipt = read_json(folder / 'awft-owned.json', {})
            if receipt.get('format') != 'awft-owned-client:1' or Path(receipt.get('root', '')).resolve() != folder.resolve():
                continue
            applied = read_json(folder / 'awft-menu.json', {})
            ready = any((folder / '.minecraft/mods').glob('fancymenu*.jar')) and any((folder / '.minecraft/mods').glob('drippy*.jar'))
            presentation = read_json(folder / 'awft-presentation.json', {})
            rows.append({'id': folder.name, 'player': receipt.get('player'), 'ready': ready, 'background_sha256': applied.get('background_sha256'), 'applied': applied.get('at'),
                         'presentation_revision': revision(folder), 'presentation_preset': presentation.get('preset', 'custom / pack default')})
        return rows

    def presentation(self, ident, preset, expected, notify=lambda _: None):
        from .presentation import apply
        return apply(self.layout, self.storage, ident, preset, expected)

    def files(self):
        info = self.current()
        files = {}
        folder = REPO / 'packwiz/config/fancymenu'
        for path in folder.rglob('*'):
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(folder).as_posix()
            if relative.startswith('assets/awft-background.'):
                continue
            if path.stat().st_size > 2 * 1024 * 1024:
                raise UserError('A menu asset exceeds its export limit')
            raw = path.read_bytes()
            if path.suffix == '.txt':
                raw = raw.replace(b'assets/awft-background.png', ('assets/awft-background' + info['extension']).encode())
                address = self.layout.settings().get('tunnel_address') or '127.0.0.1:' + str(self.layout.settings()['port'])
                raw = raw.replace(b'AWFT_JOIN_ADDRESS', address.encode('ascii'))
                raw = raw.replace(b'[action_type:joinserver] = 127.0.0.1:25565', b'[action_type:joinserver] = ' + address.encode('ascii'))
            files['config/fancymenu/' + relative] = raw
        files['config/fancymenu/assets/awft-background' + info['extension']] = self.image().read_bytes()
        if sum(map(len, files.values())) > 24 * 1024 * 1024:
            raise UserError('Menu export exceeds its 24 MiB asset limit')
        return files

    def apply(self, ident, expected, notify=lambda _: None):
        with self.layout.mutation:
            if expected != self.current()['sha256'] or not any(c['id'] == ident and c['ready'] for c in self.clients()):
                raise UserError('Refresh and choose an owned A World for Two client')
            instance = contained(self.layout.home, 'instances/' + ident)
            files = self.files()
            owner = read_json(instance / 'awft-owned.json', {})
            test_port = owner.get('test_server_port')
            if test_port is not None:
                if type(test_port) is not int or not 1024 <= test_port <= 65535:
                    raise UserError('Owned client has an invalid test server port')
                relative = 'config/fancymenu/customization/awft_title.txt'
                files[relative] = re.sub(rb'(\[action_type:joinserver\]\s*=\s*)[^\r\n]+', lambda m:m[1]+('127.0.0.1:'+str(test_port)).encode(), files[relative])
            self.storage.reserve(32 * 1024 * 1024)
            for relative, raw in files.items():
                target = contained(instance, '.minecraft/' + relative)
                if target.is_file() and target.read_bytes() != raw:
                    old = target.read_bytes()
                    history = contained(instance, 'awft-menu-history/' + hashlib.sha256(old).hexdigest() + '-' + target.name)
                    if not history.exists():
                        atomic_write(history, old)
                atomic_write(target, raw)
            applied = {'at': utcnow(), 'background_sha256': self.current()['sha256'], 'files': len(files), 'status': 'installed; reopen the main menu or restart Minecraft to load changed textures'}
            write_json(instance / 'awft-menu.json', applied)
            return applied

    def export(self):
        files = self.files()
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, raw in files.items():
                archive.writestr(name, raw)
            archive.writestr('README.txt', 'A World for Two menu update. Close Minecraft, then copy the config folder into your A World for Two instance. This contains the original artwork unchanged. It does not update gameplay mods.\n')
        return output.getvalue()

    def snapshot(self):
        from .presentation import PRESETS
        config = self.configuration()
        core = {'fancymenu', 'drippy-loading-screen', 'lumiera', 'cinematic-respawn', 'ambient-camera'}
        mods = [{'name': m['name'], 'slug': m['slug'], 'version': m['version'], 'side': m['side'], 'status': m['status']} for m in read_json(REPO / 'catalog/lock.json')['mods'] if m['slug'] in core]
        return {'background': self.current(), 'history': self.history(), 'clients': self.clients(), 'configuration': config,
                'revision': self.revision(), 'runtime': self.runtime(), 'players': self.players.snapshot()['members'],
                'executions': read_json(self.layout.state / 'cinematic-executions.json', []) if not (self.layout.state / 'cinematic-executions.json').exists() or (self.layout.state / 'cinematic-executions.json').stat().st_size <= 65536 else [],
                'primary_mods': mods,
                'presets': [{'id': ident, 'label': preset['label'], 'description': preset['description']} for ident, preset in PRESETS.items()],
                'boundary': 'Applying artwork updates only the selected owned local instance. Other computers need the exported menu update or a tested published pack update. Runtime changes to remote client camera settings are not synchronized.',
                'max_upload_bytes': MAX_IMAGE}
