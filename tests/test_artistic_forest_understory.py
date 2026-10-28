import unittest
import json
import re
from pathlib import Path

from control_room.common import UserError
from tools import artistic_forest_understory as plants


class SavedGround:
    def __init__(self, changes=None, unknown=None, entities=()):
        self.changes = changes or {}
        self.unknown = unknown
        self.entities = set(entities)

    def column(self, x, z):
        return {'kind': 'dry', 'surface_y': 65, 'state': 'minecraft:grass_block[snowy=false]',
                'existing_canopy_y': 72 if x < 0 else None}

    def state(self, x, y, z):
        p = x, y, z
        if p == self.unknown:
            return None
        return self.changes.get(p, 'minecraft:grass_block[snowy=false]' if y == 65 else 'minecraft:air')


class ForestUnderstoryTests(unittest.TestCase):
    def registry(self):
        return {'blocks': {name: {} for name in plants.FLOWERS+('minecraft:fern', 'minecraft:short_grass')}}

    def pocket(self, terrain, protected=(), forbidden=(), occupied=()):
        return plants.pocket(terrain, self.registry(), (0, 0), set(protected), set(forbidden), set(occupied))

    def test_every_plant_has_literal_ground_and_headroom_preimages(self):
        blocks, roots, before, retained = self.pocket(SavedGround())
        self.assertEqual(len(blocks), len(plants.OFFSETS))
        for x, y, z in blocks:
            self.assertEqual(roots[x, y-1, z], 'minecraft:grass_block[snowy=false]')
            self.assertEqual(before[x, y, z], 'minecraft:air')
            self.assertEqual(before[x, y+1, z], 'minecraft:air')
        self.assertGreater(len(set(blocks.values())), 3)

    def test_old_grass_flower_and_inventory_are_preserved(self):
        terrain = SavedGround(changes={(0, 66, 0): 'minecraft:short_grass',
            (1, 66, 0): 'minecraft:cornflower'}, entities={(2, 66, 1)})
        blocks, roots, before, retained = self.pocket(terrain)
        for pos in ((0, 66, 0), (1, 66, 0), (2, 66, 1)):
            self.assertNotIn(pos, blocks)
        self.assertGreater(retained['existing native grass/flower/canopy or object'], 0)

    def test_unknown_support_refuses_whole_pocket_instead_of_treating_it_as_air(self):
        with self.assertRaisesRegex(UserError, 'entire plant pocket'):
            self.pocket(SavedGround(unknown=(3, 65, 1)))

    def test_mechanism_cable_walk_and_previous_pocket_cells_are_retained(self):
        blocks, _, _, _ = self.pocket(SavedGround(), protected={(0, 0)}, forbidden={(1, 67, 0)}, occupied={(2, 66, 1)})
        for pos in ((0, 66, 0), (1, 66, 0), (2, 66, 1)):
            self.assertNotIn(pos, blocks)

    def test_sparse_or_blocked_patch_is_not_a_token_single_flower_scene(self):
        protected = set(plants.OFFSETS)-set(plants.OFFSETS[:3])
        with self.assertRaisesRegex(UserError, 'coherent pocket'):
            self.pocket(SavedGround(), protected=protected)

    def test_adapter_has_every_direct_field_read_by_the_real_native_admission(self):
        source = Path(__file__).resolve().parents[1]/'compat/control-bridge/src/worldfortwo/bridge/SettlementSupport.java'
        required = set(re.findall(r'candidate\.get(?:AsJsonArray)?\("([^\"]+)"\)', source.read_text(encoding='utf-8')))
        doc = plants.settlement_plan({'seed': 'fixture', 'world_path': 'fixture-world'}, {'sha256': 'a'*64},
            {(10, 66, 20): 'minecraft:fern'}, 'fixture generic native plan')
        self.assertIn('bounds', required)
        self.assertTrue(required <= doc.keys(), required-doc.keys())
        self.assertEqual(doc['bounds'], [10, 20, 10, 20])
        self.assertTrue(doc['construction_forbidden'])

    def test_real_512_native_footprint_limit_is_not_raised_for_whole_bank(self):
        registry = {'seed': 'fixture', 'world_path': 'fixture-world'}
        plants.settlement_plan(registry, {'sha256': 'a'*64}, {(0, 66, 0): 'minecraft:fern', (512, 66, 0): 'minecraft:fern'}, 'boundary')
        with self.assertRaisesRegex(UserError, '512 footprint'):
            plants.settlement_plan(registry, {'sha256': 'a'*64}, {(0, 66, 0): 'minecraft:fern', (513, 66, 0): 'minecraft:fern'}, 'oversize')

    def test_coherent_bounded_parts_preserve_geometry_and_do_not_replay_prototype(self):
        blocks, roots, before, scenes = {}, {}, {}, []
        for cx, cz in ((1000, -1160), (1000, -640)):
            for index, (dx, dz) in enumerate(plants.OFFSETS):
                p = (cx+dx, 66, cz+dz)
                blocks[p] = plants.FLOWERS[index % len(plants.FLOWERS)]
                roots[p[0], 65, p[2]] = 'minecraft:grass_block[snowy=false]'
                before.update({(p[0], 65, p[2]): roots[p[0], 65, p[2]], p: 'minecraft:air', (p[0], 67, p[2]): 'minecraft:air'})
            scenes.append({'center_xz': [cx, cz], 'new_rooted_plants': len(plants.OFFSETS)})
        docs, parts, prototype = plants.protocol_parts({'seed': 'fixture', 'world_path': 'fixture-world'},
            {'sha256': 'a'*64}, blocks, before, roots, scenes)
        self.assertEqual(prototype['targets'], 12)
        all_deltas = {}
        prototype_positions = set()
        for part in parts:
            doc = json.loads(docs[part['files']['DELTA']])
            field = plants.flatten(doc)
            self.assertFalse(all_deltas.keys() & field.keys())
            all_deltas.update(field)
            if part['label'] == 'prototype12':
                prototype_positions = set(field)
            else:
                self.assertFalse(prototype_positions & field.keys())
            for name in part['files'].values():
                member = json.loads(docs[name])
                self.assertLessEqual(member['bounds'][2]-member['bounds'][0], 512)
                self.assertLessEqual(member['bounds'][3]-member['bounds'][1], 512)
        self.assertEqual(all_deltas, blocks)


if __name__ == '__main__':
    unittest.main()
