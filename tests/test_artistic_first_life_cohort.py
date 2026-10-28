"""Source habitat screens, not substitutes for actual native spawn predicates."""
from copy import deepcopy
import unittest

from control_room.common import UserError
from tools.artistic_first_life_cohort import habitat_field, identity, source_clear, retained_population
import hashlib
import json


class Snapshot:
    def __init__(self, values=None):
        self.values = values or {}

    def state(self, pos):
        return self.values.get(pos, 'minecraft:grass_block' if pos[1] == 63 else 'minecraft:air')


def dry_site():
    return {'name': 'first-life-test', 'entity': 'naturalist:deer', 'feet': [1000.5, 64, -1000.5],
        'roam_bounds': [995, 60, -1006, 1005, 70, -995], 'bank_anchor': [1000, -1001],
        'habitat': {'kind': 'DRY', 'known_bounds': [997, 62, -1004, 1003, 69, -998]}}


class FirstLifeSourceTests(unittest.TestCase):
    def test_same_existing_namespace_and_name_keep_exact_identity(self):
        namespace = '2d5e0218-c2f7-49c3-b9cd-a90a6a673a69'
        a = identity(namespace, dry_site())
        row = dry_site(); row['feet'][0] += 1
        self.assertEqual(identity(namespace, row), a)
        row['name'] += '-other'
        self.assertNotEqual(identity(namespace, row)['uuid'], a['uuid'])

    def test_current_retained_object_or_actor_is_not_removed_to_make_a_habitat(self):
        row = dry_site()
        with self.assertRaises(UserError):
            habitat_field(Snapshot({(1000, 64, -1001): 'minecraft:barrel'}), row, [], set(), set())
        with self.assertRaises(UserError):
            habitat_field(Snapshot(), row, [('minecraft:pig', (1000.5, 64, -1000.5))], set(), set())

    def test_roaming_approach_cannot_overlap_unfinished_native_tree_fields(self):
        with self.assertRaisesRegex(UserError, 'active tree'):
            habitat_field(Snapshot(), dry_site(), [], {(1004, -1000)}, set())

    def test_source_water_refuge_requires_real_complete_water_not_a_heightmap(self):
        row = dry_site(); row['entity'] = 'crittersandcompanions:koi_fish'
        row['feet'] = [1000.5, 61, -1000.5]
        row['habitat'] = {'kind': 'WATER', 'known_bounds': [997,60,-1004,1003,65,-998],
            'water_bounds': [998,61,-1003,1002,62,-999]}
        water = {(x,y,z): 'minecraft:water[level=0]' for x in range(998,1003)
                 for y in (61,62) for z in range(-1003,-998)}
        water.update({(x,63,z): 'minecraft:air' for x in range(998,1003) for z in range(-1003,-998)})
        _, facts = habitat_field(Snapshot(water), row, [], set(), set())
        self.assertEqual(facts['actual_source_water_cells'], 50)
        broken = deepcopy(water); broken[1000,61,-1001] = 'minecraft:stone'
        with self.assertRaises(UserError):
            habitat_field(Snapshot(broken), row, [], set(), set())
        with self.assertRaisesRegex(UserError, 'predator/occupancy'):
            habitat_field(Snapshot(water), row, [('minecraft:drowned', (1007,61,-1001))], set(), set())

    def test_leaf_species_needs_current_leaf_habitat(self):
        row = dry_site(); row['entity'] = 'crittersandcompanions:ladybug'; row['habitat']['kind'] = 'AIR'
        with self.assertRaisesRegex(UserError, 'leaf/perch'):
            habitat_field(Snapshot(), row, [], set(), set())

    def test_only_native_one_layer_snow_is_a_source_clear_collision_screen(self):
        self.assertTrue(source_clear('minecraft:dandelion'))
        self.assertTrue(source_clear('minecraft:snow[layers=1]'))
        self.assertFalse(source_clear('minecraft:snow[layers=2]'))
        self.assertFalse(source_clear('minecraft:snow_block'))

    def test_retained_intent_prevents_duplicate_even_when_entity_is_not_loaded(self):
        namespace='2d5e0218-c2f7-49c3-b9cd-a90a6a673a69';site=dry_site();ident=identity(namespace,site)['uuid']
        name='world/data/awft-life/'+namespace+'/'+ident+'.intent.json'
        raw=json.dumps({'format':'awft-life-world-intent:2','population_namespace':namespace,
            'entity':site['entity'],'uuid':ident}).encode()
        class Archive:
            def read(self,path):return raw
        class Saved:
            prefix='world/region/'
            archive=Archive()
            files={name:{'size':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}}
        with self.assertRaisesRegex(UserError,'durable intent'):
            retained_population(Saved(),namespace,[site],{'naturalist:deer':{'candidate_population_cap':6}})


if __name__ == '__main__':
    unittest.main()
