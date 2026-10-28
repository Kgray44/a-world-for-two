import copy
import importlib.util
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('tree_envelope_derivation', HERE/'derive.py')
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class NativeEnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.native = json.loads((HERE/'native-descriptors.json').read_text())
        proof = json.loads((HERE/'source-provenance.json').read_text())
        self.resources = {r['class']: r['sha256'] for r in proof['pinned_ru_classes']+proof['pinned_native_classes']}

    def test_all_nine_keep_every_reachable_role_and_fit_existing_budget(self):
        for sapling, actual in self.native['native_descriptors'].items():
            with self.subTest(sapling=sapling):
                row = module.qualify(self.native, sapling, self.resources)
                self.assertEqual(set(actual['roles'].values()), set(row['derivation']['variants']))
                self.assertLessEqual(row['derivation']['known_cells'], module.MAX_KNOWN)
                self.assertFalse(row['growth_authorized'])
                self.assertFalse(row['native_growth_tested'])

    def test_rare_feature_removal_cannot_qualify_primary_only(self):
        key = 'regions_unexplored:larch_sapling'
        del self.native['native_descriptors'][key]['roles']['secondaryTree']
        with self.assertRaisesRegex(ValueError, 'Every actual primary'):
            module.qualify(self.native, key, self.resources)

    def test_subtle_rare_height_change_refuses_even_with_old_claimed_hash(self):
        key = 'regions_unexplored:maple_sapling'
        self.native['native_descriptors'][key]['features']['regions_unexplored:tree/big_maple']['actual_codec']['config']['trunk_placer']['height_rand_a'] = 12
        with self.assertRaises(ValueError):
            module.qualify(self.native, key, self.resources)

    def test_actual_birch_override_is_not_vanilla_straight_tree(self):
        row = module.qualify(self.native, 'minecraft:birch_sapling', self.resources)
        feature = row['derivation']['variants']['minecraft:birch']
        self.assertEqual(feature['direct_bounds'], [-2, -4, -2, 2, 10, 2])
        self.assertTrue(row['native_bee_nest_possible'])

    def test_large_larch_roots_and_top_are_included(self):
        row = module.qualify(self.native, 'regions_unexplored:larch_sapling', self.resources)
        self.assertEqual(row['derivation']['variants']['regions_unexplored:tree/larch_large']['direct_bounds'], [-4, -6, -4, 4, 25, 4])
        self.assertEqual(row['relative_write_bounds'][1], -7)
        self.assertEqual(row['relative_write_bounds'][4], 26)

    def test_white_magnolia_actual_extra_height_not_assumed_equal_to_pink(self):
        white = module.qualify(self.native, 'regions_unexplored:white_magnolia_sapling', self.resources)
        pink = module.qualify(self.native, 'regions_unexplored:pink_magnolia_sapling', self.resources)
        self.assertEqual(white['derivation']['variants']['regions_unexplored:tree/white_magnolia']['direct_bounds'][4], 10)
        self.assertEqual(pink['derivation']['variants']['regions_unexplored:tree/pink_magnolia']['direct_bounds'][4], 9)

    def test_silver_birch_rare_fork_and_litter_are_bounded(self):
        row = module.qualify(self.native, 'regions_unexplored:silver_birch_sapling', self.resources)
        self.assertEqual(row['derivation']['variants']['regions_unexplored:tree/silver_birch_tall']['direct_bounds'], [-3, -4, -3, 3, 15, 3])

    def test_pine_rare_height_and_offset_compose_once(self):
        row = module.qualify(self.native, 'regions_unexplored:pine_sapling', self.resources)
        self.assertEqual(row['derivation']['variants']['regions_unexplored:tree/pine_tall']['direct_bounds'][4], 22)
        self.assertTrue(row['native_bee_nest_possible'])

    def test_nonbee_species_and_native_bee_species_remain_distinct(self):
        for key in ('maple', 'silver_birch', 'larch', 'golden_larch'):
            self.assertFalse(module.qualify(self.native, 'regions_unexplored:'+key+'_sapling', self.resources)['native_bee_nest_possible'])
        for key in ('magnolia', 'pink_magnolia', 'white_magnolia'):
            self.assertTrue(module.qualify(self.native, 'regions_unexplored:'+key+'_sapling', self.resources)['native_bee_nest_possible'])

    def test_missing_or_changed_algorithm_class_cannot_reuse_review(self):
        key = next(iter(self.resources))
        self.resources[key] = '0'*64
        with self.assertRaisesRegex(ValueError, 'class-resource'):
            module.qualify(self.native, 'minecraft:birch_sapling', self.resources)

    def test_native_edge_and_known_read_margin_are_separate(self):
        row = module.qualify(self.native, 'regions_unexplored:maple_sapling', self.resources)
        direct = row['derivation']['direct_union']
        write = row['relative_write_bounds']
        known = row['derivation']['relative_known_bounds']
        self.assertEqual(write, [v-1 if i < 3 else v+1 for i, v in enumerate(direct)])
        self.assertEqual(known, [write[0]-8, write[1]-2, write[2]-8, write[3]+8, write[4]+4, write[5]+8])
        self.assertEqual(row['derivation_sha256'], module.sha(module.canonical(row['derivation'])))


if __name__ == '__main__':
    unittest.main()
