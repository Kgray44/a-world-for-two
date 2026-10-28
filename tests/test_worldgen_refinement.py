import copy
import hashlib
import json
import unittest

from control_room.common import REPO, UserError
from tools.worldgen_refinement import BIOMES, BASE, SPACING, refine, resource_path


class WorldgenRefinementTests(unittest.TestCase):
    def setUp(self):
        self.rows = json.loads((REPO / 'catalog/worldgen-policy.json').read_bytes())['placements']

    def test_only_the_reviewed_minor_spacings_change(self):
        changed = set()
        for row in self.rows:
            key = row['structure_set']
            path = REPO / BASE / row['file']
            before = json.loads(path.read_bytes())
            original = copy.deepcopy(before)
            after = refine(key, before)
            self.assertEqual(before, original)
            if before != after:
                changed.add(key)
                expected = copy.deepcopy(before)
                expected['placement']['spacing'] = SPACING[key][1]
                self.assertEqual(after, expected)
                ratio = (SPACING[key][0] / SPACING[key][1]) ** 2
                self.assertGreater(ratio, 1.08)
                self.assertLess(ratio, 1.12)
        self.assertEqual(changed, set(SPACING))
        self.assertEqual(len(changed), 4)

    def test_unknown_placement_and_rare_landmarks_are_preserved(self):
        for key in ('epic:epic_temple', 'ruinarium:aztecjungletemple',
                    'ancientstructures:german_buildings', 'dungeons_arise:major_structures',
                    'philipsruins:lost_soul_city', 'philipsruins:ocean_fortress_main'):
            row = next(row for row in self.rows if row['structure_set'] == key)
            before = {'placement': row['after'], 'structures': [{'structure': key, 'weight': 1}]}
            self.assertEqual(refine(key, before), before)
        rings = {'placement': {'type': 'minecraft:concentric_rings', 'distance': 32}}
        self.assertEqual(refine('minecraft:strongholds', rings), rings)

    def test_drift_fails_instead_of_silently_retargeting(self):
        for placement in ({'spacing': 79, 'separation': 40, 'type': 'minecraft:random_spread'},
                          {'spacing': 80, 'separation': 76, 'type': 'minecraft:random_spread'},
                          {'spacing': 80, 'separation': 40, 'type': 'custom:spread'}):
            with self.assertRaises(UserError):
                refine('archaeology_ruins:adoberuins', {'placement': placement})

    def test_biome_expansion_is_minor_only_and_paths_are_bounded(self):
        self.assertTrue(BIOMES.keys() <= SPACING.keys())
        self.assertNotIn('ruinarium:aztecjungletemple', BIOMES)
        self.assertEqual(resource_path('ruinarium:aztec_jungle_ruins_1', 'structure'),
                         'data/ruinarium/worldgen/structure/aztec_jungle_ruins_1.json')
        for key in ('../world:seed', 'a:../../world', 'A:invalid'):
            with self.assertRaises(UserError):
                resource_path(key, 'structure')

    def test_frozen_master_and_generated_payload_bytes_keep_their_seals(self):
        base = REPO / 'proposals/future-structure-frequency'
        for name, ref in json.loads((base / 'seal.json').read_bytes())['files'].items():
            raw = (base / name).read_bytes()
            self.assertEqual(len(raw), ref['bytes'], name)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), ref['sha256'], name)
        base = REPO / 'proposals/worldgen-four-set-v1'
        for name, ref in json.loads((base / 'manifest.json').read_bytes())['files'].items():
            raw = (base / 'datapack' / name).read_bytes()
            self.assertEqual(len(raw), ref['size'], name)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), ref['sha256'], name)


if __name__ == '__main__':
    unittest.main()
