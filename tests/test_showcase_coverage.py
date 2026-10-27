"""Coverage receipts are evidence-scoped, exact-pin-bound, and safe to publish."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from control_room.common import UserError, digest
from tools import showcase_coverage as coverage


class ShowcaseCoverageTests(unittest.TestCase):
    def fixture(self):
        def pin(slug, filename, **extra):
            return {'slug': slug, 'filename': filename, 'name': slug.title(), 'version': '1.0',
                    'size': 40, 'hashes': {'sha512': 'a'*128}, 'side': 'both', 'kind': 'mod',
                    'project_id': slug+'-project', 'version_id': 'v1', **extra}
        pins = [pin('misleading-project-name', 'ship.jar'),
                pin('support-project', 'support.jar'),
                pin('optional-project', 'optional.jar', optional=True, default=False)]
        lock = {'version': 'candidate-test', 'generated': 'fixed-lock-time', 'mods': pins}
        compat = {'source_lock': {'sha256': '1'*64, 'pack_sha256': '2'*64}, 'requests': [
            {'id': 'sailing', 'name': 'Sailing', 'group': 'ships', 'status': 'selected',
             'file_pin': {key: pins[0][key] for key in
                          ('filename', 'size', 'hashes', 'project_id', 'version_id')}},
            {'id': 'unavailable-candidate', 'name': 'Unresolved request', 'status': 'unresolved'},
        ]}
        policy = [{'id': 'base-01', 'name': 'Harbor', 'sha256': '3'*64,
                   'positions': 6, 'receipt_sha256': '4'*64}]
        source = {'id': 'base-01', 'name': 'Harbor', 'sha256': '3'*64, 'positions': 6,
                  'native_verification': {'operation': 'verify', 'plan_sha256': '3'*64,
                                          'positions': 6, 'receipt_sha256': '4'*64,
                                          'failures': 0, 'finished': 'native-time'}}
        artifacts = []
        for pin, ident in zip(pins, ('smallships', 'almanac', None)):
            artifacts.append({'filename': pin['filename'], 'size': pin['size'], 'hashes': pin['hashes'],
                              'declared_mods': [{'id': ident, 'name': ident, 'version': '1.0'}] if ident else [],
                              'embedded_mods': [], 'fml_mod_type': 'LIBRARY' if ident is None else None,
                              'metadata': [{'member': 'META-INF/neoforge.mods.toml', 'sha256': '5'*64}]})
        inputs = {'format': coverage.FORMAT, 'candidate': lock['version'],
                  'lock_sha256': '1'*64, 'pack_sha256': '2'*64, 'registry_sha256': '6'*64,
                  'artifacts': artifacts, 'native_namespaces': {'smallships': {'blocks': 0, 'items': 9, 'entities': 4}},
                  'geometry': {'sources': [source], 'blocks': [], 'supplied_items': [],
                               'construction_summons': [], 'landmarks': [], 'warnings': [],
                               'composite_mod_block_positions': 0}, 'staged': [], 'functional': []}
        return lock, compat, inputs, policy

    def report(self, fixture, functional_policies=()):
        lock, compat, inputs, policy = fixture
        return coverage.build_report(lock, compat, inputs, lock_sha='1'*64,
                                     pack_sha='2'*64, policies=policy,
                                     functional_policies=functional_policies)

    def test_every_pin_and_disabled_optional_have_separate_rows(self):
        report = self.report(self.fixture())
        self.assertEqual(report['totals']['enabled_mod_jars'], 2)
        self.assertEqual(len(report['disabled_optional_mods']), 1)
        self.assertFalse(report['disabled_optional_mods'][0]['enabled_by_default'])
        self.assertEqual(report['canonical_request_coverage'][1]['selected_files'], [])

    def test_actual_native_id_not_project_slug_owns_namespace(self):
        fixture = self.fixture()
        fixture[2]['geometry']['blocks'] = [
            {'namespace': 'smallships', 'source': 'base-01', 'exhibit': 'Actual harbor',
             'exhibit_position': [10, 64, -40], 'blocks': 1,
             'block_types': {'smallships:synthetic_test_block': 1}, 'sample_positions': [[10, 64, -40]]},
            {'namespace': 'misleading-project-name', 'source': 'base-01', 'exhibit': 'Wrong namespace',
             'exhibit_position': [11, 64, -40], 'blocks': 2,
             'block_types': {'misleading-project-name:fake': 2}, 'sample_positions': [[11, 64, -40]]}]
        fixture[2]['geometry']['composite_mod_block_positions'] = 3
        report = self.report(fixture)
        ship = report['mods'][0]
        self.assertEqual(ship['feature_namespaces'], ['smallships'])
        self.assertEqual(ship['historical_mod_blocks'], 1)
        self.assertEqual(report['unattributed_namespaces'], ['misleading-project-name'])
        self.assertEqual(ship['coverage'], 'partial_presence_only')
        self.assertEqual(ship['canonical_requests'][0]['id'], 'sailing')

    def test_changed_jar_or_canonical_mapping_pin_is_rejected(self):
        for change in ('artifact', 'mapping', 'lock', 'missing', 'duplicate'):
            fixture = self.fixture()
            if change == 'artifact':
                fixture[2]['artifacts'][0]['hashes'] = {'sha512': 'b'*128}
            elif change == 'mapping':
                fixture[1]['requests'][0]['file_pin']['version_id'] = 'new-unreviewed-version'
            elif change == 'lock':
                fixture[2]['lock_sha256'] = '9'*64
            elif change == 'missing':
                fixture[2]['artifacts'].pop()
            else:
                fixture[2]['artifacts'].append(deepcopy(fixture[2]['artifacts'][0]))
            with self.subTest(change=change), self.assertRaises(UserError):
                self.report(fixture)

    def test_exact_receipt_hash_plan_and_source_set_are_required(self):
        for key, value in (('receipt_sha256', '9'*64), ('failures', 1),
                           ('plan_sha256', '8'*64), ('finished', ''), ('positions', 5)):
            fixture = self.fixture()
            fixture[2]['geometry']['sources'][0]['native_verification'][key] = value
            with self.subTest(key=key), self.assertRaises(UserError):
                self.report(fixture)
        fixture = self.fixture()
        fixture[2]['geometry']['sources'].append({**fixture[2]['geometry']['sources'][0], 'id': 'unknown'})
        with self.assertRaises(UserError):
            self.report(fixture)

    def test_source_only_smallship_and_vanilla_clue_are_not_sailing_or_treasure_acceptance(self):
        fixture = self.fixture()
        stage = {'id': 'cog', 'name': 'Real cog proposal', 'namespace': 'smallships',
                 'position': [10, 63, -40], 'status': 'staged', 'native_placed': False,
                 'manifest_sha256': '7'*64, 'plan_sha256': '8'*64,
                 'features': ['actual smallships:cog'], 'remaining': ['sail it']}
        fixture[2]['staged'] = [stage, {**stage, 'id': 'clue', 'namespace': 'minecraft'}]
        report = self.report(fixture)
        ship = report['mods'][0]
        self.assertEqual(ship['historical_mod_blocks'], 0)
        self.assertEqual(ship['coverage'], 'missing_actual_demonstration')
        self.assertEqual(len(ship['staged_attractions']), 1)
        self.assertEqual(ship['scoped_functional_checks'], [])
        fixture[2]['staged'][0]['native_placed'] = True
        with self.assertRaises(UserError):
            self.report(fixture)

    def test_stocked_item_and_static_summon_do_not_complete_gameplay(self):
        fixture = self.fixture()
        fixture[2]['geometry']['supplied_items'] = [
            {'id': 'smallships:synthetic_item', 'count': 2, 'source': 'base-01',
             'exhibit': 'Dockyard', 'containers': [[1, 65, 3]], 'exhibit_position': [1, 65, 3]}]
        fixture[2]['geometry']['construction_summons'] = [
            {'entity': 'smallships:cog', 'source': 'base-01', 'position': [3, 63, 4],
             'exhibit': 'Dockyard', 'no_ai': True}]
        row = self.report(fixture)['mods'][0]
        self.assertEqual(row['supplied_item_count'], 2)
        self.assertEqual(row['construction_summon_count'], 1)
        self.assertEqual(row['coverage'], 'partial_presence_only')
        self.assertEqual(row['scoped_functional_checks'], [])
        self.assertIn('real Small Ships entity', row['demonstration_goals'][0])

    def test_unknown_identity_or_known_unclassified_feature_is_not_exempt(self):
        for identities, mode, expected in (([], None, 'needs_identity_review'),
                                           ([{'id': 'new_feature'}], None, 'needs_feature_review')):
            fixture = self.fixture()
            fixture[2]['artifacts'][0]['declared_mods'] = identities
            fixture[2]['artifacts'][0]['fml_mod_type'] = mode
            row = self.report(fixture)['mods'][0]
            self.assertEqual(row['role'], expected)
            self.assertTrue(row['physical_exhibit_expected'])
            self.assertEqual(row['coverage'], 'needs_review')
        row = self.report(self.fixture())['mods'][1]
        self.assertEqual(row['role'], 'library')
        self.assertFalse(row['physical_exhibit_expected'])

    def test_bundle_namespace_requires_actual_embedded_declarations(self):
        fixture = self.fixture()
        fixture[2]['artifacts'][0]['declared_mods'] = [{'id': 'aeronautics_bundled'}]
        with self.assertRaises(UserError):
            self.report(fixture)
        fixture[2]['artifacts'][0]['embedded_mods'] = [
            {'id': value, 'file': 'native-child.jar'} for value in ('aeronautics', 'offroad', 'simulated')]
        row = self.report(fixture)['mods'][0]
        self.assertEqual(row['feature_namespaces'], ['aeronautics', 'aeronautics_bundled', 'offroad', 'simulated'])

    def test_order_is_stable_and_unknown_source_is_rejected(self):
        fixture = self.fixture()
        original = self.report(fixture)
        fixture[0]['mods'].reverse()
        fixture[1]['requests'].reverse()
        fixture[2]['artifacts'].reverse()
        # Input custody hash intentionally changes if raw input order changes.
        shuffled = self.report(fixture)
        self.assertEqual(original['mods'], shuffled['mods'])
        self.assertEqual(original['canonical_request_coverage'], shuffled['canonical_request_coverage'])
        self.assertEqual(coverage.encoded(shuffled), coverage.encoded(self.report(fixture)))
        fixture[2]['geometry']['supplied_items'].append({'id': 'smallships:any', 'count': 1, 'source': 'forged'})
        with self.assertRaises(UserError):
            self.report(fixture)

    def test_supplied_snbt_reader_ignores_item_text_inside_a_book(self):
        value = coverage.SNBT('{Items:[{Slot:0b,id:"minecraft:written_book",count:1,components:{text:"id:smallships:fake,count:999"}}],UUID:[I;1,-2,3,4],NoAI:1b}').read()
        self.assertEqual(value['Items'][0]['id'], 'minecraft:written_book')
        self.assertEqual(value['Items'][0]['count'], 1)
        self.assertEqual(value['UUID'], [1, -2, 3, 4])
        with self.assertRaises(UserError):
            coverage.SNBT('{Items:[{id:"minecraft:stone",count:1},garbage}').read()

    def test_related_vanilla_station_does_not_fabricate_a_mod_block_or_function_pass(self):
        fixture = self.fixture()
        fixture[2]['artifacts'][0]['declared_mods'] = [{'id': 'cinematic'}]
        fixture[2]['geometry']['vanilla_stations'] = [
            {'block': 'minecraft:crafting_table', 'source': 'base-01', 'exhibit': 'Kitchen',
             'count': 2, 'exhibit_position': [10, 65, -5], 'sample_positions': [[10, 65, -5]]}]
        row = self.report(fixture)['mods'][0]
        self.assertEqual(row['related_vanilla_station_count'], 2)
        self.assertEqual(row['historical_mod_blocks'], 0)
        self.assertEqual(row['scoped_functional_checks'], [])

    def test_inconsistent_composite_cannot_inflate_presence(self):
        fixture = self.fixture()
        fixture[2]['geometry']['blocks'] = [
            {'namespace': 'smallships', 'source': 'base-01', 'exhibit': 'Dockyard',
             'blocks': 6, 'block_types': {'smallships:test': 2}}]
        fixture[2]['geometry']['composite_mod_block_positions'] = 6
        with self.assertRaises(UserError):
            self.report(fixture)

    def test_identity_reads_pinned_native_metadata_without_slug_guessing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'misleading.jar'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('META-INF/neoforge.mods.toml',
                                 'modLoader="javafml"\n[[mods]]\nmodId="smallships"\ndisplayName="Actual native name"\nversion="1.0"\n')
            pin = {'filename': path.name, 'size': path.stat().st_size,
                   'hashes': {'sha512': hashlib.sha512(path.read_bytes()).hexdigest()}}
            identity = coverage.read_jar_identity(path, pin)
            self.assertEqual(identity['declared_mods'][0]['id'], 'smallships')
            self.assertEqual(identity['declared_mods'][0]['name'], 'Actual native name')
            path.write_bytes(path.read_bytes()+b'changed')
            with self.assertRaises(UserError):
                coverage.read_jar_identity(path, pin)

    def test_last_writer_composite_removes_replaced_blocks_and_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            registry = {'seed': 123, 'world_path': 'private-world',
                        'blocks': {'minecraft:air': {}, 'smallships:test': {}},
                        'items': {'smallships:item'}, 'entities': set()}
            policies = []
            for index, palette, block, entities in (
                    (1, ['smallships:test'], [0, 64, 0, 0],
                     [{'pos': [0, 64, 0], 'nbt': '{Items:[{id:"smallships:item",count:2}]}'}]),
                    (2, ['minecraft:air'], [0, 64, 0, 0], [])):
                path = directory/f'plan-{index}.json'
                plan = {'format': 'awft-native-settlement:1', 'seed': 123, 'world_path': 'private-world',
                        'palette': palette, 'blocks': [block], 'block_entities': entities,
                        'commands': [], 'landmarks': []}
                path.write_bytes(coverage.encoded(plan))
                receipt = directory/f'verify-{index}.json'
                receipt.write_bytes(coverage.encoded({'operation': 'verify', 'plan_sha256': digest(path),
                                                      'blocks': 1, 'failures': 0, 'finished': 'time'}))
                policies.append({'id': str(index), 'name': 'Test', 'file': path.name, 'sha256': digest(path),
                                 'positions': 1, 'receipt_file': receipt.name,
                                 'receipt_sha256': digest(receipt), 'tier': 'historical_native_geometry'})
            result = coverage.aggregate_geometry(directory, registry, policies)
            self.assertEqual(result['blocks'], [])
            self.assertEqual(result['supplied_items'], [])
            self.assertEqual(result['composite_mod_block_positions'], 0)
            receipt.write_bytes(receipt.read_bytes()+b' ')
            with self.assertRaises(UserError):
                coverage.aggregate_geometry(directory, registry, policies)

    def test_public_output_rejects_private_data_and_native_function_scope_is_not_global(self):
        for private in ({'seed': 123}, {'file': r'C:\Users\owner\account.json'},
                        {'nested': [{'base_backup_sha256': 'a'*64}]}):
            with self.subTest(private=private), self.assertRaises(UserError):
                coverage.assert_public(private)
        fixture = self.fixture()
        fixture[2]['functional'] = [{'id': 'real-scoped-test', 'mod_ids': ['smallships'],
                                    'status': 'passed_scoped_native_behavior', 'pack_sha256': '2'*64,
                                    'receipt_sha256': '9'*64}]
        with self.assertRaises(UserError):
            self.report(fixture)
        admitted = deepcopy(fixture[2]['functional'])
        report = self.report(fixture, functional_policies=admitted)
        self.assertEqual(report['mods'][0]['coverage'], 'scoped_behavior_passed_other_features_pending')
        self.assertEqual(report['totals']['fully_accepted_mods'], 0)
        fixture[2]['functional'][0]['pack_sha256'] = '8'*64
        with self.assertRaises(UserError):
            self.report(fixture, functional_policies=admitted)


if __name__ == '__main__':
    unittest.main()
