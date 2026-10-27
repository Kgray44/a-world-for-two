import io
import os
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

from PIL import Image

from control_room.atlas import Atlas, prepare_renderer, validate_claims, validate_telemetry
from control_room.cinematics import Cinematics, inspect_image
from control_room.common import UserError, read_json, utcnow, write_json
from control_room.pack import generate_pack, public_pack_file
from test_safety import Fixture


class AtlasSafetyTests(Fixture):
    def setUp(self):
        super().setUp()
        self.atlas = Atlas(self.layout, self.storage, self.server, Mock(), Mock())

    def test_surface_teleport_requires_supported_bridge_and_explicit_nether_height(self):
        self.atlas.players.details.return_value = {'online': True, 'capabilities': ['safe_teleport']}
        self.atlas.metrics.latest.return_value = {'bridge_capabilities': ['safe_teleport']}
        point = dict(dimension='minecraft:overworld', x=128, y=None, z=256, landing='surface')
        with self.assertRaisesRegex(UserError, 'Update the server Control Bridge'):
            self.atlas.teleport('KgAmazing44', point, confirmed=True)
        self.atlas.metrics.latest.return_value = {'bridge_capabilities': ['safe_teleport', 'surface_teleport']}
        with self.assertRaisesRegex(UserError, 'known safe Y'):
            self.atlas.teleport('KgAmazing44', dict(point, dimension='minecraft:the_nether'), confirmed=True)
        with self.assertRaisesRegex(UserError, 'known safe Y'):
            self.atlas.teleport('KgAmazing44', dict(point, landing='near-y'), confirmed=True)
        with self.assertRaises(UserError):
            self.atlas.teleport('KgAmazing44', dict(point, landing='disable-safety'), confirmed=True)
        self.assertFalse((self.layout.state / 'atlas-requests').exists())

    def test_claims_are_bounded_and_do_not_imply_that_chunks_are_loaded(self):
        claim = dict(dimension='minecraft:overworld', chunk_x=-12, chunk_z=20,
                     owner='32650cdf-2aaa-4f47-bb27-42ef0d1249fd', name='Our cottage', color='#abc123', forceloadable=False)
        sample = dict(at=utcnow(), available=True, measurement_ms=.2, items=[claim], truncated=True)
        clean = validate_claims(sample)
        self.assertTrue(clean['truncated'])
        self.assertNotIn('loaded', clean['items'][0])
        self.assertEqual(clean['items'][0]['chunk_x'], -12)
        for change in (dict(items=[claim]*2), dict(items=[claim]*2049), dict(available=False),
                       dict(items=[dict(claim, chunk_x=True)]), dict(measurement_ms=float('nan'))):
            with self.assertRaises(ValueError):
                validate_claims(sample | change)

    def test_waypoint_edits_reject_stale_revision_and_nonfinite_positions(self):
        value = dict(name='Our cottage', category='Home', dimension='minecraft:overworld', x=10, y=70, z=20)
        saved = self.atlas.save(value, 'empty')
        with self.assertRaises(UserError):
            self.atlas.save(dict(value, x=30), 'empty')
        self.assertEqual(self.atlas.waypoints()[0]['x'], 10)
        with self.assertRaises(UserError):
            self.atlas.save(dict(value, x=float('nan')), self.atlas.revision())
        self.assertEqual(self.atlas.waypoints()[0]['id'], saved['id'])

    def test_import_is_atomic_and_private_exports_are_separate(self):
        value = dict(name='Private home', dimension='minecraft:overworld', x=10, y=70, z=20, collection='KG')
        self.atlas.save(value, 'empty')
        self.assertEqual(self.atlas.export('shared')['waypoints'], [])
        self.assertEqual(len(self.atlas.export('KG')['waypoints']), 1)
        with self.assertRaises(UserError):
            self.atlas.import_collection({'format':'awft-waypoints:1', 'waypoints':[value, dict(value, dimension='invalid')]}, self.atlas.revision())
        self.assertEqual(len(self.atlas.waypoints()), 1)

    def test_landmark_notes_preserve_server_evidence_and_reject_invented_locations(self):
        record = dict(id='structure:test:1', name='ruinarium:aztecjungletemple', kind='structure',
                      dimension='minecraft:overworld', x=128, y=80, z=256, at='2026-10-26T20:00:00Z',
                      evidence='Valid structure start in a loaded chunk')
        write_json(self.layout.state / 'atlas-index.json', [record])
        notes = dict(category='Temples', civilization='Aztec inspired', notes='Check the lower chamber together.', exploration='unexplored', x=99999)
        self.atlas.annotate(record['id'], notes, 'empty')
        observed = self.atlas.locations()[0]
        self.assertEqual((observed['x'], observed['at'], observed['evidence']), (128, record['at'], record['evidence']))
        self.assertEqual(observed['exploration'], 'unexplored')
        with self.assertRaises(UserError):
            self.atlas.annotate(record['id'], notes, 'empty')
        with self.assertRaises(UserError):
            self.atlas.annotate('made-up-pyramid', notes, self.atlas.annotations_revision())
        waypoint = self.atlas.save(dict(record, id=None, provenance='server observed', category='Temples'), 'empty')
        self.assertEqual(waypoint['provenance'], 'manual waypoint')

    def test_pack_delivery_serves_indexed_binary_assets_and_rejects_changed_or_private_files(self):
        folder = self.layout.home / 'public-pack'
        (folder / 'config').mkdir(parents=True)
        image = folder / 'config/background.png'
        image.write_bytes(b'indexed image bytes')
        generate_pack(folder, dict(name='Test', version='test', neoforge='21.1.262', mods=[]))
        (folder / 'lock.json').write_text('{"private":"not public"}')
        self.assertEqual(public_pack_file(folder, 'config/background.png').read_bytes(), b'indexed image bytes')
        with self.assertRaises(UserError):
            public_pack_file(folder, 'lock.json')
        with self.assertRaises(UserError):
            public_pack_file(folder, '../settings.json')
        image.write_bytes(b'changed image')
        with self.assertRaises(UserError):
            public_pack_file(folder, 'config/background.png')

    def test_tile_requests_cannot_traverse_or_generate_a_missing_chunk(self):
        self.assertIsNone(self.atlas.tile('minecraft_overworld', '3', '0_0.png'))
        for args in [('minecraft_overworld', '3', '../world.png'), ('../world', '3', '0_0.png'), ('minecraft_overworld', '20', '0_0.png')]:
            with self.assertRaises(UserError):
                self.atlas.tile(*args)
        self.assertFalse(self.layout.world.joinpath('region').exists())

    def test_cleanup_refuses_linked_ancestor_without_deleting_target(self):
        target = self.layout.home / 'keep-me'
        target.mkdir()
        (target / '0').mkdir()
        sentinel = target / '0/0_0.png'
        sentinel.write_bytes(b'unique tile')
        link = self.atlas.root / 'minecraft_overworld'
        link.parent.mkdir(parents=True)
        try:
            os.symlink(target, link, target_is_directory=True)
        except OSError:
            if os.name != 'nt':
                self.skipTest('Creating a test directory link is unavailable')
            # Windows junction creation needs no symlink privilege. Both exact
            # paths are inside this owned fixture; only the junction is removed.
            result = subprocess.run(['powershell.exe','-NoProfile','-Command',
                '& { param($link,$target) New-Item -ItemType Junction -Path $link -Target $target -ErrorAction Stop | Out-Null }',
                str(link),str(target)],capture_output=True,text=True,timeout=20,
                creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode:
                self.skipTest('Creating a test directory junction is unavailable')
        try:
            with self.assertRaises(UserError):
                self.atlas.clear_cache(True)
            self.assertEqual(sentinel.read_bytes(), b'unique tile')
        finally:
            link.rmdir() if link.is_junction() else link.unlink()

    def test_renderer_listener_is_refused_before_server_start(self):
        mods = self.layout.server / 'mods'
        mods.mkdir()
        (mods / 'squaremap-test.jar').write_bytes(b'test')
        folder = self.layout.server / 'squaremap'
        folder.mkdir()
        (folder / 'config.yml').write_text('settings:\n  internal-webserver:\n    enabled: true\n    bind: 0.0.0.0\n')
        with self.assertRaises(UserError):
            prepare_renderer(self.layout, self.storage)

    def test_telemetry_cannot_insert_unbounded_or_nonfinite_objects(self):
        value = dict(objects=[], locations=[], renderer={'queued_chunks': 4, 'paused': False}, index_full=False)
        self.assertEqual(validate_telemetry(value)['renderer']['queued_chunks'], 4)
        with self.assertRaises(ValueError):
            validate_telemetry(dict(value, renderer={'queued_chunks':float('nan')}))
        with self.assertRaises(ValueError):
            validate_telemetry(dict(value, objects=[{}]*257))


class ArtworkSafetyTests(Fixture):
    def setUp(self):
        super().setUp()
        self.cinematics = Cinematics(self.layout, self.storage, self.server, Mock())

    def picture(self, color):
        output = io.BytesIO()
        Image.new('RGB', (640, 360), color).save(output, 'PNG')
        return output.getvalue()

    def test_artwork_preserves_exact_bytes_and_restores_history(self):
        original = self.cinematics.image().read_bytes()
        original_hash = self.cinematics.current()['sha256']
        raw = self.picture('#654321')
        saved = self.cinematics.upload(raw, original_hash)
        self.assertEqual(self.cinematics.image().read_bytes(), raw)
        self.assertEqual(self.cinematics.image(original_hash).read_bytes(), original)
        self.cinematics.restore(original_hash, saved['sha256'])
        self.assertEqual(self.cinematics.image().read_bytes(), original)

    def test_invalid_upload_and_stale_edit_leave_current_image_unchanged(self):
        before = self.cinematics.current()['sha256']
        with self.assertRaises(UserError):
            self.cinematics.upload(b'<svg>not a raster image</svg>', before)
        with self.assertRaises(UserError):
            self.cinematics.upload(self.picture('red'), 'outdated')
        self.assertEqual(self.cinematics.current()['sha256'], before)
        self.assertFalse(self.cinematics.path.exists())


    def test_decompression_and_history_deletion_limits(self):
        with self.assertRaises(UserError):
            inspect_image(b'x'*(8*1024*1024+1))
        with self.assertRaises(UserError):
            self.cinematics.remove(self.cinematics.current()['sha256'], True)
        with self.assertRaises(UserError):
            self.cinematics.apply('../some-other-client', self.cinematics.current()['sha256'])


class CameraPresetTests(Fixture):
    def test_nested_native_toml_edits_preserve_other_tables_and_create_missing_tables(self):
        import tomllib
        from control_room.presentation import toml_update
        original = ('[client]\nname = "KG"\n'
                    '\t[client.advanced.graphics.quality]\n'
                    '\t\tlodChunkRenderDistanceRadius = 256 # native comment\n'
                    '\t\totherQuality = 3\n'
                    '[server]\nport = 25575\n')
        changed = toml_update(original, 'client.advanced.graphics.quality', {'lodChunkRenderDistanceRadius':128})
        parsed = tomllib.loads(changed.decode())
        self.assertEqual(parsed['client']['advanced']['graphics']['quality'],
                         {'lodChunkRenderDistanceRadius':128, 'otherQuality':3})
        self.assertEqual(parsed['server']['port'], 25575)
        self.assertEqual(parsed['client']['name'], 'KG')
        self.assertIn('# native comment', changed.decode())
        added = tomllib.loads(toml_update(original, 'client.advanced.worker', {'threads':2}).decode())
        self.assertEqual(added['client']['advanced']['worker']['threads'], 2)

    def test_local_presets_preserve_unrelated_fields_restore_exact_bytes_and_refuse_stale_edits(self):
        from control_room.presentation import apply, revision
        instance = self.layout.home / 'instances/test-client'
        config = instance / '.minecraft/config'
        config.mkdir(parents=True)
        write_json(instance / 'awft-owned.json', {'format':'awft-owned-client:1', 'root':str(instance)})
        original = b'[camera]\nleanStrength = 55 # keep my comment\n[interface]\ncontrolHints = false\n'
        (config / 'cinematic-client.toml').write_bytes(original)
        before = revision(instance)
        with patch('control_room.presentation.psutil.process_iter', return_value=[]):
            result = apply(self.layout, self.storage, instance.name, 'minimal', before)
            import tomllib
            camera = tomllib.loads((config / 'cinematic-client.toml').read_text())
            self.assertFalse(camera['interface']['controlHints'])
            self.assertEqual(camera['camera']['leanStrength'], 0)
            self.assertIn('# keep my comment', (config / 'cinematic-client.toml').read_text())
            with self.assertRaises(UserError):
                apply(self.layout, self.storage, instance.name, 'balanced', before)
            apply(self.layout, self.storage, instance.name, 'restore', result['revision'])
        self.assertEqual((config / 'cinematic-client.toml').read_bytes(), original)
        self.assertFalse((config / 'ambient_camera-client.toml').exists())
        self.assertFalse((config / 'cinematic_respawn.properties').exists())



class SceneControlTests(Fixture):
    def setUp(self):
        super().setUp()
        self.players=Mock()
        self.cinematics=Cinematics(self.layout,self.storage,self.server,self.players)

    def test_trigger_validation_is_atomic_and_new_triggers_are_disabled(self):
        location=dict(name='Our garden',dimension='minecraft:overworld',x=24,y=72,z=-40)
        result=self.cinematics.trigger(location,'awft:intro','empty')
        self.assertFalse(result['enabled'])
        current=self.cinematics.revision()
        with self.assertRaises(UserError):
            self.cinematics.trigger(dict(location,x=float('inf')),'awft:intro',current)
        with self.assertRaises(UserError):
            self.cinematics.trigger(location,'awft:intro','empty')
        self.assertEqual(len(self.cinematics.configuration()['triggers']),1)
        with self.assertRaises(UserError):
            self.cinematics.remove_trigger(result['id'],current,False)
        self.assertEqual(len(self.cinematics.configuration()['triggers']),1)

    def test_replay_requires_fresh_online_native_telemetry(self):
        self.players.details.return_value={'online':False,'capabilities':['cinematics']}
        with self.assertRaises(UserError):
            self.cinematics.action('KgAmazing44','play','awft:intro')
        self.assertFalse((self.layout.state/'cinematic-requests').exists())

