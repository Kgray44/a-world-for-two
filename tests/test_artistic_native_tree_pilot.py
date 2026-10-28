import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from control_room.common import UserError
from tools import artistic_native_tree_pilot as pilot
from tools.native_tree_growth import envelopes


class ActualRuntimePinTests(unittest.TestCase):
    def runtime_fixture(self, home):
        (home/'packwiz').mkdir()
        (home/'server/mods').mkdir(parents=True)
        pack = 'a'*64
        (home/'packwiz/active.json').write_text(json.dumps({'version': pilot.NATIVE_CANDIDATE, 'pack_sha256': pack}))
        (home/'server/installed.json').write_text(json.dumps({'pack_version': pilot.NATIVE_CANDIDATE, 'pack_sha256': pack}))
        names = {'native_class_sha256': 'NativeTreeGrowthSupport.class', 'native_scope_sha256': 'TreeGrowthScope.class',
                 'native_guard_sha256': 'mixin/NativeTreeGrowthGuardMixin.class',
                 'bee_audit_sha256': 'TreeBeeAudit.class', 'bee_facts_sha256': 'BeeNestFacts.class'}
        jar = home/'server/mods'/('awft-control-bridge-'+pilot.NATIVE_BRIDGE+'.jar')
        classpins = {}
        with zipfile.ZipFile(jar, 'x') as archive:
            for key, name in names.items():
                raw = ('synthetic pin fixture '+name).encode()
                archive.writestr('worldfortwo/bridge/'+name, raw)
                classpins[key] = hashlib.sha256(raw).hexdigest()
        return {'NATIVE_PACK_SHA': pack, 'NATIVE_JAR_SHA': hashlib.sha256(jar.read_bytes()).hexdigest(),
                'NATIVE_JAR_BYTES': jar.stat().st_size, 'NATIVE_CLASS_PINS': classpins}

    def test_exact_fixture_runtime_binds_five_actual_members_without_activation_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            values = self.runtime_fixture(home)
            with patch.multiple(pilot, **values):
                pins = pilot.runtime_pins(home)
            self.assertEqual(pins['classes'], values['NATIVE_CLASS_PINS'])
            self.assertFalse(pins['native_activation_proved_by_this_read'])

    def test_matching_but_unreviewed_pack_and_old_candidate_are_refused(self):
        for change in ('pack_sha256', 'version'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                home = Path(directory)
                values = self.runtime_fixture(home)
                active = json.loads((home/'packwiz/active.json').read_text())
                installed = json.loads((home/'server/installed.json').read_text())
                if change == 'pack_sha256':
                    active[change] = installed[change] = 'b'*64
                else:
                    active['version'] = installed['pack_version'] = '0.1.0-candidate.45'
                (home/'packwiz/active.json').write_text(json.dumps(active))
                (home/'server/installed.json').write_text(json.dumps(installed))
                with patch.multiple(pilot, **values), self.assertRaisesRegex(UserError, 'private46 pack'):
                    pilot.runtime_pins(home)

    def test_scope_identity_stays_pinned_even_when_outer_fixture_jar_is_reviewed(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            values = self.runtime_fixture(home)
            values['NATIVE_CLASS_PINS']['native_scope_sha256'] = 'c'*64
            with patch.multiple(pilot, **values), self.assertRaisesRegex(UserError, 'compiled class pins differ'):
                pilot.runtime_pins(home)


class SavedTerrain:
    """Literal saved-state unit fixture, never a simulated Minecraft Level."""
    def __init__(self, changes=None, unknown=None, entities=()):
        self.changes = changes or {}
        self.unknown = unknown
        self.entities = set(entities)

    def column(self, x, z):
        return {'kind': 'dry', 'surface_y': 65, 'existing_canopy_y': None}

    def state(self, x, y, z):
        if (x, y, z) == self.unknown:
            return None
        return self.changes.get((x, y, z), 'minecraft:grass_block[snowy=false]' if y == 65 else 'minecraft:air')


def qualification(relative=(-3, -5, -3, 3, 11, 3), bee=True):
    _, known = envelopes((0, 66, 0), relative)
    return {'relative_write_bounds': list(relative), 'native_bee_nest_possible': bee,
            'derivation': {'relative_known_bounds': [v-(0, 66, 0)[i % 3] for i, v in enumerate(known)]}}


class NativePilotTests(unittest.TestCase):
    def review(self, terrain, q=None, protected=()):
        return pilot.review_plot(terrain, {}, {}, q or qualification(), (0, 66, 0), set(protected))

    def test_entire_rare_crown_deep_root_and_read_perimeter_are_retained(self):
        field, facts = self.review(SavedTerrain(), qualification((-11, -5, -11, 11, 19, 11)))
        self.assertEqual(facts['known_cells'], 47151)
        self.assertIn((-19, 59, -19), field)
        self.assertIn((19, 89, 19), field)
        self.assertEqual(facts['reserved_native_bee_slots'], 3)
        self.assertFalse(facts['native_growth_tested'])
        self.assertTrue(facts['current_runtime_rebinding_required'])

    def test_unknown_far_corner_is_not_air(self):
        with self.assertRaisesRegex(UserError, 'Unknown native plot cell'):
            self.review(SavedTerrain(unknown=(11, 81, 11)))

    def test_block_entity_in_read_perimeter_outside_crown_is_preserved(self):
        with self.assertRaisesRegex(UserError, 'complete read/physics perimeter'):
            self.review(SavedTerrain(entities={(10, 67, 10)}))

    def test_air_route_and_future_mask_column_blocks_whole_crown(self):
        with self.assertRaisesRegex(UserError, 'retained building/AIR/route'):
            self.review(SavedTerrain(), protected={(3, -3)})

    def test_crops_paths_and_buried_fluids_are_not_cleared_for_a_pilot(self):
        for pos, state in (((1, 66, 1), 'vinery:red_grape_bush[age=3]'),
                           ((1, 65, 1), 'minecraft:dirt_path'),
                           ((1, 63, 1), 'minecraft:water[level=0]'),
                           ((1, 64, 1), 'minecraft:oak_slab[type=bottom,waterlogged=true]')):
            with self.subTest(state=state), self.assertRaises(UserError):
                self.review(SavedTerrain(changes={pos: state}))

    def test_r3_known_bounds_cannot_be_shrunk_to_avoid_an_obstruction(self):
        q = qualification()
        q['derivation']['relative_known_bounds'][0] += 1
        with self.assertRaisesRegex(UserError, 'R3 read/physics perimeter changed'):
            self.review(SavedTerrain(), q)

    def test_root_must_be_actual_ground_plus_one_and_replaceable(self):
        with self.assertRaisesRegex(UserError, 'actual replaceable ground cover'):
            self.review(SavedTerrain(changes={(0, 66, 0): 'minecraft:barrel[facing=north,open=false]'}))
        terrain = SavedTerrain()
        terrain.column = lambda x, z: {'kind': 'dry', 'surface_y': 64, 'existing_canopy_y': None}
        with self.assertRaisesRegex(UserError, 'immediately above'):
            self.review(terrain)

    def fixture_binding(self, home):
        folder = home/'staging/source'
        folder.mkdir(parents=True)
        backup = home/'dashboard/settlement/backup-receipt.json'
        backup.parent.mkdir(parents=True)
        backup.write_text(json.dumps({'id': pilot.CHECKPOINT, 'sha256': pilot.CHECKPOINT_SHA, 'verified': True}))
        files = {}
        plots = []
        for ident, species, root in pilot.PLOTS:
            plot = {'id': ident, 'tree_plan_sha256': hashlib.sha256(ident.encode()).hexdigest()}
            plots.append(plot)
            for name in ('tree-plan.json', 'tree-before-VERIFY-ONLY.json', 'native-qualification.json'):
                path = folder/ident/name
                path.parent.mkdir(exist_ok=True)
                path.write_text(json.dumps({'fixture': name}))
                files[ident+'/'+name] = {'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        protection = folder/'tree-protection.json'
        protection.write_text('{"fixture":"protection"}')
        files[protection.name] = {'bytes': protection.stat().st_size, 'sha256': hashlib.sha256(protection.read_bytes()).hexdigest()}
        manifest = folder/'manifest.json'
        manifest.write_text(json.dumps({'format': 'awft-three-native-sapling-pilot-receipt:1',
            'checkpoint_id': pilot.CHECKPOINT, 'checkpoint_sha256': pilot.CHECKPOINT_SHA,
            'world_writes': 0, 'files': files, 'plots': plots}))
        pins = {'candidate_version': pilot.NATIVE_CANDIDATE, 'bridge_version': pilot.NATIVE_BRIDGE,
                'pack_sha256': 'a'*64, 'classes': {'native_class_sha256': 'b'*64,
                    'native_scope_sha256': 'c'*64, 'native_guard_sha256': 'd'*64}}
        return manifest, hashlib.sha256(manifest.read_bytes()).hexdigest(), pins, plots

    def test_binding_without_owner_review_never_emits_an_executable_request(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            manifest, sha, pins, _ = self.fixture_binding(home)
            with patch.object(pilot, 'guard', return_value={'allowed': True}), patch.object(pilot, 'runtime_pins', return_value=pins):
                result = pilot.bind_requests(home, manifest, sha, home/'staging/bindings')
            self.assertFalse(result['generation_requests_created'])
            self.assertFalse(list((home/'staging/bindings').rglob('request.json')))
            receipt = json.loads((home/'staging/bindings/binding-receipt.json').read_text())
            self.assertEqual(receipt['requests'], [])
            self.assertFalse(receipt['approval_created'])
            self.assertEqual(receipt['native_actions'], 0)

    def test_stale_or_generic_review_cannot_be_turned_into_grow_authority(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            manifest, sha, pins, plots = self.fixture_binding(home)
            reviews = {}
            for plot in plots:
                path = home/(plot['id']+'-review.json')
                path.write_text(json.dumps({'checkpoint_sha256': pilot.CHECKPOINT_SHA,
                    'tree_plan_sha256': plot['tree_plan_sha256'], 'construction_complete': True,
                    'functional_commissioning_complete': True, 'visual_corrections_reviewed': True}))
                reviews[plot['id']] = path
            with patch.object(pilot, 'guard', return_value={'allowed': True}), patch.object(pilot, 'runtime_pins', return_value=pins):
                with self.assertRaisesRegex(UserError, 'plot-scoped readiness'):
                    pilot.bind_requests(home, manifest, sha, home/'staging/refused', reviews)
            self.assertFalse((home/'staging/refused').exists())

    def test_explicit_review_binds_one_native_request_per_exact_plot(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            manifest, sha, pins, plots = self.fixture_binding(home)
            reviews = {}
            for plot in plots:
                path = home/(plot['id']+'-review.json')
                path.write_text(json.dumps({'approval_scope': 'one-exact-saved-tree-plot',
                    'checkpoint_sha256': pilot.CHECKPOINT_SHA, 'tree_plan_sha256': plot['tree_plan_sha256'],
                    'construction_complete': True, 'functional_commissioning_complete': True, 'visual_corrections_reviewed': True}))
                reviews[plot['id']] = path
            with patch.object(pilot, 'guard', return_value={'allowed': True}), patch.object(pilot, 'runtime_pins', return_value=pins):
                result = pilot.bind_requests(home, manifest, sha, home/'staging/requests', reviews)
            self.assertTrue(result['generation_requests_created'])
            paths = list((home/'staging/requests').rglob('request.json'))
            self.assertEqual(len(paths), 3)
            for path in paths:
                request = json.loads(path.read_text())
                self.assertEqual(request['native_guard_sha256'], 'd'*64)
                self.assertEqual(request['checkpoint_sha256'], pilot.CHECKPOINT_SHA)
                self.assertEqual(request['allowed_operation'], 'grow')
                self.assertIn('/staging/source/', '/'+request['before']['path'])

    def test_exact_source_hash_failure_is_not_a_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)/'member.json'
            p.write_text('{"value":1}', encoding='utf-8')
            sha = hashlib.sha256(p.read_bytes()).hexdigest()
            self.assertEqual(pilot.checked(p, sha, 128), {'value': 1})
            p.write_text('{"value":2}', encoding='utf-8')
            with self.assertRaisesRegex(UserError, 'source member differs'):
                pilot.checked(p, sha, 128)

    def test_two_native_bee_capacities_are_reserved_not_claimed_spawns(self):
        _, birch = self.review(SavedTerrain(), qualification(bee=True))
        _, larch = self.review(SavedTerrain(), qualification(bee=False))
        self.assertEqual((birch['reserved_native_nest_slots'], birch['reserved_native_bee_slots']), (1, 3))
        self.assertEqual((larch['reserved_native_nest_slots'], larch['reserved_native_bee_slots']), (0, 0))


if __name__ == '__main__':
    unittest.main()
