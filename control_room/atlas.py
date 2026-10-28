"""Local atlas administration. Tile reads never query or generate Minecraft chunks."""
from __future__ import annotations

import contextlib
import hashlib
import json
import math
import re
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

from .common import REPO, UserError, atomic_write, contained, digest, read_json, utcnow, write_json
from .storage import tree_size

DIMENSIONS = {'minecraft:overworld': 'minecraft_overworld', 'minecraft:the_nether': 'minecraft_the_nether', 'minecraft:the_end': 'minecraft_the_end'}
ICONS = ('home', 'heart', 'anchor', 'tree', 'treasure', 'train', 'star', 'danger', 'grave', 'pin')
DEFAULTS = {'refresh_seconds': 5, 'cache_limit_mib': 512, 'paused': False, 'chunks_per_interval': 32, 'interval_seconds': 30}
EXPLORATION = ('unknown', 'unexplored', 'explored')


def journal_fields(value):
    if not isinstance(value, dict):
        raise UserError('Landmark notes must be an object')
    clean = {}
    for key, limit in (('notes', 2000), ('civilization', 60)):
        text = value.get(key, '')
        if not isinstance(text, str) or len(text) > limit or any(ord(c) < 32 and c not in '\n\t' for c in text):
            raise UserError('Use a short, printable landmark ' + key)
        clean[key] = text.strip()
    clean['exploration'] = value.get('exploration', 'unknown')
    if clean['exploration'] not in EXPLORATION:
        raise UserError('Choose unknown, unexplored or explored')
    return clean


def structure_category(value):
    """Labels describe registry names; they never predict a structure location."""
    name = value.get('type') or value.get('name', '')
    namespace, _, path = name.partition(':')
    if namespace in ('epic', 'ruinarium', 'betterjungletemples', 'betterdeserttemples', 'archaeology_ruins', 'ancientstructures', 'philipsruins', 'mtr'):
        category = 'Temples' if any(s in path for s in ('temple', 'pyramid')) else 'Archaeology & ruins'
    elif 'castle' in name or namespace in ('emberscastles', 'castleshift'):
        category = 'Castles & keeps'
    elif namespace == 'dungeons_arise':
        category = 'Dungeons & landmarks'
    else:
        category = 'Structures'
    # A name can establish a theme, not an archaeological identity for generic ruins.
    civilization = next((label for token, label in (('mayan', 'Mayan inspired'), ('aztec', 'Aztec inspired'), ('roman', 'Roman inspired'), ('japanese', 'Japanese inspired'), ('german', 'Germanic inspired')) if token in path), '')
    return {'category': category, 'civilization': civilization}


def validate_claims(value):
    if not isinstance(value, dict) or type(value.get('available')) is not bool:
        raise ValueError('Invalid claim availability')
    stamp = value.get('at')
    if not isinstance(stamp, str) or len(stamp) > 40:
        raise ValueError('Invalid claim timestamp')
    datetime.fromisoformat(stamp.replace('Z', '+00:00'))
    rows = value.get('items', [])
    elapsed = value.get('measurement_ms')
    if not isinstance(rows, list) or len(rows) > 2048 or type(elapsed) not in (int, float) or not math.isfinite(elapsed) or not 0 <= elapsed <= 10000:
        raise ValueError('Claim snapshot exceeds its bounded workload')
    items, seen = [], set()
    for row in rows:
        if not isinstance(row, dict) or row.get('dimension') not in DIMENSIONS:
            raise ValueError('Invalid claim dimension')
        if any(type(row.get(key)) is not int or abs(row[key]) > 1_875_000 for key in ('chunk_x', 'chunk_z')):
            raise ValueError('Invalid claim chunk coordinates')
        if not re.fullmatch(r'[a-f0-9-]{36}', row.get('owner', '')) or not re.fullmatch(r'#[0-9a-fA-F]{6}', row.get('color', '')):
            raise ValueError('Invalid claim owner or color')
        name = row.get('name')
        if not isinstance(name, str) or len(name) > 80 or any(ord(c) < 32 for c in name) or type(row.get('forceloadable')) is not bool:
            raise ValueError('Invalid claim label or force-loading flag')
        key = (row['dimension'], row['chunk_x'], row['chunk_z'])
        if key in seen:
            raise ValueError('Ambiguous duplicate claim boundary')
        seen.add(key)
        items.append({key: row[key] for key in ('dimension', 'chunk_x', 'chunk_z', 'owner', 'name', 'color', 'forceloadable')})
    clean = {'at': stamp, 'available': value['available'], 'items': items, 'measurement_ms': elapsed, 'truncated': value.get('truncated') is True}
    for key in ('source', 'unavailable'):
        text = value.get(key, '')
        if not isinstance(text, str) or len(text) > 500:
            raise ValueError('Invalid claim source')
        clean[key] = text
    if not clean['available'] and items:
        raise ValueError('Unavailable claims cannot be presented as confirmed boundaries')
    return clean


def validate_telemetry(value):
    """Bound event-index data before it reaches disk or the browser."""
    if not isinstance(value, dict):
        raise ValueError('Invalid atlas telemetry')
    cleaned = {}
    for key, maximum in (('objects', 256), ('locations', 2000)):
        rows = value.get(key, [])
        if not isinstance(rows, list) or len(rows) > maximum:
            raise ValueError('Atlas index exceeds its limit')
        cleaned[key] = []
        for row in rows:
            if not isinstance(row, dict) or row.get('dimension') not in DIMENSIONS:
                raise ValueError('Invalid atlas dimension')
            item = {'dimension': row['dimension']}
            for field, limit in (('id', 300), ('name', 80), ('kind', 40), ('type', 200), ('at', 40), ('last_seen', 40), ('state', 40), ('evidence', 256)):
                if field in row:
                    text = row[field]
                    if not isinstance(text, str) or len(text) > limit or any(ord(c) < 32 for c in text):
                        raise ValueError('Invalid atlas label')
                    item[field] = text
            if not all(item.get(field) for field in ('id', 'name', 'kind', 'at')):
                raise ValueError('Incomplete atlas location')
            for field, bound in (('x', 30_000_000), ('y', 2048), ('z', 30_000_000), ('yaw', 10**12)):
                if field == 'yaw' and field not in row:
                    continue
                number = row.get(field)
                if type(number) not in (int, float) or not math.isfinite(number) or abs(number) > bound:
                    raise ValueError('Invalid atlas coordinates')
                item[field] = number
            cleaned[key].append(item)
    renderer = value.get('renderer', {})
    if not isinstance(renderer, dict):
        raise ValueError('Invalid renderer telemetry')
    clean_renderer = {}
    for key in ('paused', 'overloaded'):
        if key in renderer:
            if type(renderer[key]) is not bool:
                raise ValueError('Invalid renderer state')
            clean_renderer[key] = renderer[key]
    for key in ('queued_chunks', 'worlds', 'chunks_per_interval', 'cpu_percent_one_core'):
        if key in renderer:
            number = renderer[key]
            if type(number) not in (int, float) or not math.isfinite(number) or not 0 <= number <= 10_000_000:
                raise ValueError('Invalid renderer measurement')
            clean_renderer[key] = number
    for key in ('source', 'unavailable'):
        if key in renderer:
            if not isinstance(renderer[key], str) or len(renderer[key]) > 500:
                raise ValueError('Invalid renderer source')
            clean_renderer[key] = renderer[key]
    cleaned['renderer'] = clean_renderer
    if 'claims' in value:
        cleaned['claims'] = validate_claims(value['claims'])
    cleaned['index_full'] = value.get('index_full') is True
    return cleaned


def prepare_renderer(layout, storage):
    if not any((layout.server / 'mods').glob('squaremap-*.jar')):
        return
    path = layout.server / 'squaremap/config.yml'
    if not path.exists():
        storage.reserve(1024 * 1024)
        atomic_write(path, (REPO / 'packwiz/config/awft/squaremap.yml').read_bytes())
    text = path.read_text(encoding='utf-8')
    # The bundled web listener must stay off; tiles use the existing local app.
    section = re.search(r'internal-webserver:\s*\n((?:[ \t]+[^\n]*\n?)+)', text)
    if not section or not re.search(r'enabled:\s*false', section[1]):
        raise UserError('Disable squaremap’s internal-webserver in squaremap/config.yml. World Atlas serves its tiles through the local Control Room.')
    interval = read_json(layout.state / 'atlas-settings.json', {}).get('interval_seconds', 30)
    if type(interval) is not int or not 15 <= interval <= 120:
        raise UserError('Atlas render interval must be between 15 and 120 seconds')
    updated = re.sub(r'(interval-seconds:\s*)\d+', lambda m: m[1] + str(interval), text)
    if updated != text:
        storage.reserve(1024 * 1024)
        atomic_write(path, updated.encode('utf-8'))


class Atlas:
    def __init__(self, layout, storage, server, players, metrics):
        self.layout, self.storage, self.server, self.players, self.metrics = layout, storage, server, players, metrics
        self.path = layout.state / 'atlas-waypoints.json'
        self.annotations_path = layout.state / 'atlas-landmark-notes.json'
        self.options_path = layout.state / 'atlas-settings.json'
        self.root = layout.server / 'squaremap/web/tiles'
        self._scan_at = self._attempt_at = 0
        self._cache = {'bytes': None, 'tiles': None, 'last_update': None, 'measured_at': None, 'revision': 'pending'}
        self._inventory_lock = threading.Lock()
        self._inventory_worker = None
        self._inventory_error = None
        self._inventory_epoch = 0
        self._stop = threading.Event()
        self._last_index_at = None

    def options(self):
        return DEFAULTS | read_json(self.options_path, {})

    def waypoints(self):
        return read_json(self.path, [])

    def revision(self):
        return digest(self.path) if self.path.exists() else 'empty'

    def annotations_revision(self):
        return digest(self.annotations_path) if self.annotations_path.exists() else 'empty'

    def locations(self):
        notes = read_json(self.annotations_path, {})
        rows = read_json(self.layout.state / 'atlas-index.json', [])
        return [row | (structure_category(row) if row.get('kind') == 'structure' else {}) |
                {'exploration': 'unknown'} | notes.get(row['id'], {}) | {'provenance': 'server observed'} for row in rows]

    def annotate(self, ident, value, expected):
        clean = journal_fields(value)
        category = value.get('category', 'Structures')
        if not isinstance(category, str) or not category.strip() or len(category) > 40 or any(ord(c) < 32 for c in category):
            raise UserError('Use a short printable landmark category')
        clean.update(category=category.strip(), updated=utcnow())
        with self.layout.mutation:
            if expected != self.annotations_revision():
                raise UserError('Landmark notes changed. Refresh the atlas before saving.')
            known = {row['id'] for row in read_json(self.layout.state / 'atlas-index.json', [])}
            if ident not in known:
                raise UserError('Choose a server-observed landmark before adding notes')
            rows = read_json(self.annotations_path, {})
            if ident not in rows and len(rows) >= 2000:
                raise UserError('The atlas holds at most 2,000 annotated landmarks')
            self.storage.reserve(16 * 1024 * 1024)
            rows[ident] = clean
            write_json(self.annotations_path, rows)
        return clean

    def validate(self, value):
        if not isinstance(value, dict):
            raise UserError('Each waypoint must be an object')
        clean = {}
        for key, limit in (('name', 80), ('category', 40)):
            v = value.get(key, 'Places' if key == 'category' else '')
            if not isinstance(v, str) or not v.strip() or len(v) > limit or any(ord(c) < 32 for c in v):
                raise UserError('Use a short printable waypoint ' + key)
            clean[key] = v.strip()
        dimension = value.get('dimension')
        if dimension not in DIMENSIONS:
            raise UserError('Choose the Overworld, Nether or End')
        clean['dimension'] = dimension
        for key, bound in (('x', 29_999_984), ('z', 29_999_984), ('y', 2048)):
            v = value.get(key)
            if key == 'y' and v is None:
                clean[key] = None
                continue
            if type(v) not in (int, float) or not math.isfinite(v) or abs(v) > bound:
                raise UserError('Waypoint coordinates must be finite and inside Minecraft’s limits')
            clean[key] = round(v, 2)
        clean['collection'] = value.get('collection', 'shared')
        if clean['collection'] not in ('shared', 'KG', 'Sera'):
            raise UserError('Choose the shared, KG or Sera collection')
        clean['icon'] = value.get('icon', 'pin')
        if clean['icon'] not in ICONS:
            raise UserError('Choose a supported icon')
        clean['color'] = value.get('color', '#bc985b')
        if not isinstance(clean['color'], str) or not re.fullmatch(r'#[a-fA-F0-9]{6}', clean['color']):
            raise UserError('Choose a six-digit color')
        clean.update(journal_fields(value))
        # Imported or hand-entered coordinates cannot become confirmed structures.
        clean['provenance'] = 'manual waypoint'
        return clean

    def save(self, value, expected, notify=lambda _: None):
        clean = self.validate(value)
        with self.layout.mutation:
            if expected != self.revision():
                raise UserError('Waypoints changed. Refresh the atlas before saving.')
            rows = self.waypoints()
            ident = value.get('id')
            existing = next((r for r in rows if r['id'] == ident), None)
            if ident and not existing:
                raise UserError('The selected waypoint no longer exists')
            if not existing and len(rows) >= 2000:
                raise UserError('The atlas holds at most 2,000 saved waypoints')
            clean.update(id=ident or uuid.uuid4().hex, updated=utcnow())
            self.storage.reserve(16 * 1024 * 1024)
            write_json(self.path, [r for r in rows if r['id'] != clean['id']] + [clean])
            return clean

    def remove(self, ident, expected, confirmed=False):
        with self.layout.mutation:
            if confirmed is not True or expected != self.revision():
                raise UserError('Confirm deletion against the current waypoint revision')
            rows = self.waypoints()
            if not any(r['id'] == ident for r in rows):
                raise UserError('Waypoint not found')
            self.storage.reserve(16 * 1024 * 1024)
            write_json(self.path, [r for r in rows if r['id'] != ident])
            return {'removed': ident}

    def import_collection(self, data, expected):
        if not isinstance(data, dict) or data.get('format') != 'awft-waypoints:1' or not isinstance(data.get('waypoints'), list) or len(data['waypoints']) > 500:
            raise UserError('Import an A World for Two waypoint collection with at most 500 entries')
        values = [self.validate(v) for v in data['waypoints']]
        with self.layout.mutation:
            if expected != self.revision():
                raise UserError('Waypoints changed. Refresh before importing.')
            rows = self.waypoints()
            if len(rows) + len(values) > 2000:
                raise UserError('Import would exceed the 2,000-waypoint limit')
            self.storage.reserve(16 * 1024 * 1024)
            write_json(self.path, rows + [dict(v, id=uuid.uuid4().hex, updated=utcnow()) for v in values])
        return {'imported': len(values)}

    def export(self, collection='shared'):
        if collection not in ('shared', 'KG', 'Sera'):
            raise UserError('Choose a collection to export')
        return {'format': 'awft-waypoints:1', 'collection': collection, 'exported': utcnow(),
                'waypoints': [w for w in self.waypoints() if w['collection'] == collection]}

    def settings(self, changes):
        if not isinstance(changes, dict) or set(changes) - set(DEFAULTS):
            raise UserError('Unknown atlas setting')
        specs = {'refresh_seconds': (2, 5), 'cache_limit_mib': (64, 2048), 'chunks_per_interval': (1, 64), 'interval_seconds': (15, 120)}
        for key, value in changes.items():
            if key == 'paused':
                if type(value) is not bool:
                    raise UserError('Pause must be true or false')
            elif type(value) is not int or not specs[key][0] <= value <= specs[key][1]:
                raise UserError('Atlas setting is outside its supported range: ' + key)
        with self.layout.mutation:
            self.storage.reserve(1024 * 1024)
            options = self.options() | changes
            write_json(self.options_path, options)
            self.monitor(self.metrics.latest(), force=True)
            return options

    def cache(self, force=False):
        """HTTP requests return a timestamped sample; one owned worker reads metadata."""
        with self._inventory_lock:
            updating = bool(self._inventory_worker and self._inventory_worker.is_alive())
            if not self._stop.is_set() and not updating and (force or not self._attempt_at or time.monotonic() - self._attempt_at >= 30):
                epoch = self._inventory_epoch
                self._inventory_worker = threading.Thread(target=self._measure_cache, args=(epoch,), daemon=True, name='awft-atlas-inventory')
                self._inventory_worker.start()
                updating = True
            age = max(0, time.monotonic() - self._scan_at) if self._scan_at else None
            return dict(self._cache, updating=updating, scan_error=self._inventory_error,
                        age_seconds=round(age, 2) if age is not None else None,
                        current=age is not None and age < 60 and not self._inventory_error and not self._stop.is_set(), refresh_seconds=30)

    def _measure_cache(self, epoch):
        started = time.monotonic()
        total = tiles = latest = fingerprint = 0
        try:
            for slug in DIMENSIONS.values():
                for level in range(6):
                    if self._stop.is_set():
                        return
                    zoom = contained(self.layout.server, f'squaremap/web/tiles/{slug}/{level}')
                    if not zoom.is_dir():
                        continue
                    for path in zoom.glob('*.png'):
                        if self._stop.is_set():
                            return
                        if time.monotonic() - started > 8:
                            raise UserError('Atlas inventory exceeded its eight-second metadata budget; rendering stays paused until a complete sample is available')
                        if path.is_symlink() or not re.fullmatch(r'-?\d{1,8}_-?\d{1,8}\.png', path.name):
                            raise UserError('Unexpected linked or invalid map tile')
                        try:
                            stat = path.stat(); total += stat.st_size; tiles += 1; latest = max(latest, stat.st_mtime_ns)
                            metadata = f'{slug}/{level}/{path.name}:{stat.st_size}:{stat.st_mtime_ns}:{stat.st_ctime_ns}:{stat.st_ino}'.encode()
                            fingerprint ^= int.from_bytes(hashlib.blake2s(metadata).digest(), 'big')
                        except FileNotFoundError:
                            pass
                        if tiles > 100_000:
                            raise UserError('Atlas cache inventory reached its file limit; rendering must stay paused')
            with self._inventory_lock:
                if epoch == self._inventory_epoch and not self._stop.is_set():
                    self._cache = {'bytes': total, 'tiles': tiles, 'last_update': latest / 1e9 if latest else None,
                                   'measured_at': utcnow(), 'scan_ms': round((time.monotonic() - started) * 1000, 2),
                                   'revision': f'{tiles}-{total}-{fingerprint:064x}'}
                    self._scan_at = time.monotonic()
                    self._inventory_error = None
        except (OSError, UserError) as exc:
            with self._inventory_lock:
                if epoch == self._inventory_epoch and not self._stop.is_set():
                    self._inventory_error = str(exc)[:400]
        finally:
            with self._inventory_lock:
                self._attempt_at = time.monotonic()

    def close(self):
        self._stop.set()
        if self._inventory_worker:
            self._inventory_worker.join(timeout=2)

    def monitor(self, measurements, force=False):
        options = self.options()
        cache = self.cache()
        at_limit = cache['bytes'] is not None and cache['bytes'] >= options['cache_limit_mib'] * 1024 * 1024
        desired = {'paused': options['paused'] or at_limit or not cache['current'], 'cache_limit_reached': at_limit,
                   'chunks_per_interval': options['chunks_per_interval'], 'interval_seconds': options['interval_seconds']}
        path = self.layout.state / 'atlas-control.json'
        if force or read_json(path) != desired:
            self.storage.reserve(65536)
            write_json(path, desired)

    def snapshot(self):
        worlds = []
        for dim, slug in DIMENSIONS.items():
            settings = read_json(self.root / slug / 'settings.json', {})
            worlds.append({'id': dim, 'slug': slug, 'rendered': bool(settings),
                           'spawn': settings.get('spawn'), 'zoom': settings.get('zoom', {'max': 3, 'def': 3, 'extra': 2})})
        measurements = self.metrics.latest()
        roster = self.players.snapshot()
        returns = read_json(self.layout.state / 'atlas-returns.json', {})
        history = self.return_history()
        return {'backend': 'squaremap 1.3.2', 'worlds': worlds, 'waypoints': self.waypoints(), 'revision': self.revision(),
                'freshness': measurements.get('freshness', {}),
                'return_locations': returns, 'return_history': history[-100:][::-1],
                'players': roster['members'], 'players_state': roster.get('online_state'), 'players_measured_at': utcnow(),
                'options': self.options(), 'cache': self.cache(),
                'renderer': measurements.get('atlas_renderer'), 'objects': measurements.get('atlas_objects', []),
                'claims': measurements.get('atlas_claims', {'available': False, 'items': [], 'unavailable': 'Claim boundaries need the updated server bridge.'}),
                'teleport_modes': ['near-y', 'surface'] if 'surface_teleport' in measurements.get('bridge_capabilities', []) else ['near-y'],
                'locations': self.locations(), 'icons': ICONS, 'annotations_revision': self.annotations_revision(),
                'index_bytes': (self.layout.state / 'atlas-index.json').stat().st_size if (self.layout.state / 'atlas-index.json').exists() else 0,
                'interval_note': 'Changing the background interval takes effect at the next server start. Pause and chunk budget apply on the next bridge sample.',
                'boundary': 'Tiles show real rendered chunks. Blank areas are unrendered or unexplored; SeedGen visual LODs are separate. Personal collections are excluded from shared exports; this local administrator can inspect all collections.',
                'xaero_sync': 'No automatic Xaero waypoint adapter has been verified. Atlas JSON import/export does not synchronize client waypoint files.',
                'integrations': [
                    {'name': 'Squaremap terrain', 'status': 'configured' if any(w['rendered'] for w in worlds) else 'unavailable',
                     'detail': 'Existing server-rendered PNG tiles only. Tile timestamps describe the render cache; they do not prove every recent world edit is rendered.'},
                    {'name': 'Players, structures and named entities', 'status': 'current' if 'atlas_index' in measurements.get('bridge_capabilities', []) else 'unavailable',
                     'detail': 'Owned bridge observations in loaded chunks. Structures and unloaded objects retain their observation times; distant entities are not searched.'},
                    {'name': 'Open Parties and Claims', 'status': 'current' if measurements.get('atlas_claims', {}).get('available') else 'unavailable',
                     'detail': 'Bounded claim records from the server bridge. Party membership and party permission editing have no verified dashboard adapter.'},
                    {'name': 'Trains, ships and airships', 'status': 'partial',
                     'detail': 'Loaded ship and contraption entities can be observed. Create railway-network and virtual airship positions have no verified dashboard adapter; API suitability remains to be qualified with the transport owner.'},
                    {'name': 'Xaero and MapHorizons synchronization', 'status': 'unverified',
                     'detail': 'Client mapping and DH terrain are separate from Squaremap. No automatic shared-waypoint or tile synchronization is verified.'},
                ]}

    def tile(self, dimension, zoom, name):
        if dimension not in DIMENSIONS.values() or not re.fullmatch(r'[0-5]', str(zoom)) or not re.fullmatch(r'-?\d{1,8}_-?\d{1,8}\.png', name):
            raise UserError('Invalid map tile')
        path = contained(self.layout.server, 'squaremap/web/tiles/' + dimension + '/' + str(zoom) + '/' + name)
        if not path.is_file():
            return None
        if path.stat().st_size > 4 * 1024 * 1024:
            raise UserError('Map tile exceeds its allocation')
        return path

    def clear_cache(self, confirmed=False, notify=lambda _: None):
        if confirmed is not True or self.server.running():
            raise UserError('Stop the server and confirm cache cleanup first')
        count = released = 0
        for slug in DIMENSIONS.values():
            for zoom in range(6):
                folder = contained(self.layout.server, f'squaremap/web/tiles/{slug}/{zoom}')
                if not folder.exists():
                    continue
                if folder.is_symlink() or folder.is_junction():
                    raise UserError('Linked cache folders cannot be cleaned')
                for path in folder.iterdir():
                    if re.fullmatch(r'-?\d{1,8}_-?\d{1,8}\.png', path.name) and path.is_file() and not path.is_symlink():
                        released += path.stat().st_size; path.unlink(); count += 1
        with self._inventory_lock:
            self._inventory_epoch += 1
            self._scan_at = self._attempt_at = 0
            self._cache = {'bytes': None, 'tiles': None, 'last_update': None, 'measured_at': None, 'revision': 'pending'}
        write_json(self.layout.logs / ('atlas-cache-cleanup-' + str(time.time_ns()) + '.json'), {'at': utcnow(), 'tiles': count, 'bytes': released, 'world_files_touched': False})
        return {'removed_tiles': count, 'released_bytes': released}

    def teleport(self, name, destination, confirmed=False, notify=lambda _: None):
        if confirmed is not True:
            raise UserError('Confirm the selected player and destination before teleporting')
        if not isinstance(destination, dict):
            raise UserError('Choose a teleport destination')
        who = self.players.details(name)
        if not who['online'] or 'safe_teleport' not in who['capabilities']:
            raise UserError('Safe teleport needs an online player and fresh updated Control Bridge telemetry')
        if destination.get('return') is True:
            destination = {'return': True}
        elif destination.get('player'):
            target = self.players.details(destination['player'])
            if not target['online']:
                raise UserError('The destination player must be online')
            destination = {key: target['location'][key] for key in ('dimension', 'x', 'y', 'z')}
            destination['landing'] = 'near-y'
        else:
            mode = destination.get('landing', 'surface' if destination.get('y') is None else 'near-y')
            if mode not in ('surface', 'near-y'):
                raise UserError('Choose surface landing or a known Y coordinate')
            if mode == 'surface' and 'surface_teleport' not in self.metrics.latest().get('bridge_capabilities', []):
                raise UserError('Update the server Control Bridge before using the new surface landing search')
            if mode == 'surface' and destination.get('dimension') == 'minecraft:the_nether':
                raise UserError('Choose a known safe Y coordinate in the Nether')
            if mode == 'near-y' and destination.get('y') is None:
                raise UserError('Enter a known safe Y coordinate, or choose surface landing')
            validated = self.validate(dict(destination, name='Teleport', category='Admin'))
            destination = {key: validated[key] for key in ('dimension', 'x', 'y', 'z')}
            destination['landing'] = mode
        with self.layout.mutation:
            self.storage.reserve(64 * 1024 * 1024)
            history = self.return_history()  # Refuse damaged audit state before any native action.
            ident = uuid.uuid4().hex
            request = {'id': ident, 'at': utcnow(), 'uuid': who['uuid'], 'name': who['name'], 'destination': destination}
            path = self.layout.state / 'atlas-requests' / (ident + '.json')
            write_json(path, request)
            self.server._write('awft teleport ' + ident)
            result_path = path.with_suffix('.result.json')
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                if result_path.exists():
                    result = read_json(result_path)
                    receipt_error = None
                    try:
                        write_json(self.layout.logs / ('teleport-' + ident + '.json'), dict(request, result=result))
                    except OSError:
                        receipt_error = 'The local teleport receipt could not be saved.'
                    if result.get('status') != 'complete':
                        raise UserError(result.get('error', 'Destination safety check refused teleportation'))
                    history_path = self.layout.state / 'atlas-return-history.json'
                    history.append({'id': ident, 'at': result.get('at', utcnow()), 'name': who['name'], 'uuid': who['uuid'],
                                    'previous': result.get('previous'), 'destination': result.get('destination')})
                    try:
                        write_json(history_path, history[-100:])
                    except OSError:
                        receipt_error = 'The local return-history audit could not be saved.'
                    if receipt_error:
                        result = dict(result, history_warning='Native teleport completed. ' + receipt_error + ' Inspect server state before retrying; do not repeat the move to repair history.')
                    return result
                time.sleep(.1)
            raise UserError('Teleport result is pending. Inspect task history and the console before retrying.')

    def return_history(self):
        path = self.layout.state / 'atlas-return-history.json'
        try:
            if path.exists() and path.stat().st_size > 512 * 1024:
                raise ValueError('Return history is too large')
            rows = read_json(path, [])
            if not isinstance(rows, list) or len(rows) > 100 or not all(isinstance(row, dict) for row in rows):
                raise ValueError('Invalid return history')
            return rows
        except (ValueError, TypeError) as exc:
            raise UserError('Return history needs local inspection. Existing records were preserved; no native command was sent by this request.') from exc
