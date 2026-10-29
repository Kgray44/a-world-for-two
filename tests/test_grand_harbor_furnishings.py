"""Combined additive fleet correction; source proof is not Minecraft acceptance."""
from copy import deepcopy
import unittest
from unittest.mock import patch

import nbtlib

from control_room.common import UserError
from tests.test_grand_harbor_smallcraft_furnishings import original
from tools import grand_harbor_furnishings as details
from tools.grand_harbor_berth import rotate_point
from tools.grand_harbor_fleet import AIR


def registry():
    r = original('tern-pilot-cutter').registry
    for color in ('green', 'red'):
        r['blocks']['minecraft:'+color+'_carpet'] = {}
    r['blocks']['minecraft:lectern'] = {
        'facing': ['north', 'south', 'west', 'east'],
        'has_book': ['true', 'false'], 'powered': ['true', 'false'],
    }
    return r


class FleetFurnishingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = registry()
        cls.models = {key: details.decorate(cls.registry, key) for key in details.POSES}

    def test_six_corrections_preserve_hulls_original_stock_and_room_routes(self):
        roles = []
        for key, (p, d) in self.models.items():
            with self.subTest(ship=key):
                self.assertEqual(set(p.blocks), set(d['before_design']))
                self.assertTrue(all(d['before_design'][pos] == AIR for pos in d['delta']))
                for pos, state in d['before_design'].items():
                    if state != AIR:
                        self.assertEqual(p.blocks[pos], state)
                self.assertEqual({pos: p.tags[pos] for pos in d['original_tags']}, d['original_tags'])
                self.assertFalse(set(d['delta']) & set(d['original_tags']))
                self.assertEqual(set(d['checks']['circulation']['rooms_reached']), {r['name'] for r in p.rooms})
                self.assertTrue(all(p.blocks[pos[0], pos[1]-1, pos[2]] != AIR for pos in d['delta']))
                self.assertEqual(d['visual_owner_acceptance'], 'NOT ACCEPTED')
                roles.append(tuple(group['name'] for group in d['groups']))
        self.assertEqual(len(set(roles)), 6)

    def test_native_packets_only_propose_new_cells_and_never_replay_existing_tags(self):
        for key in self.models:
            with self.subTest(ship=key):
                docs = details.packets(self.registry, key)
                proposal = docs['delta-PROPOSED-NOT-ADMITTED.json']
                source = docs['source-detail.json']
                origin, rotation = details.POSES[key]
                expected = {rotate_point(tuple(row['pos']), origin, rotation) for row in source['delta']}
                actual = {tuple(row[:3]) for row in proposal['blocks']}
                self.assertEqual(actual, expected)
                self.assertNotIn(AIR, proposal['palette'])
                self.assertEqual(proposal['commands'], [])
                original_world_tags = {rotate_point(tuple(pos), origin, rotation)
                                       for pos in source['retained_original_explicit_tags']}
                self.assertFalse(original_world_tags & {tuple(row['pos']) for row in proposal['block_entities']})
                for name, doc in docs.items():
                    if name != 'source-detail.json':
                        self.assertTrue(doc['construction_forbidden'])
                        self.assertTrue(doc['verification_only'])
                self.assertEqual(source['mercy_dryness_dependency'], key == 'mercy-of-the-tide')
                self.assertEqual(source['native_deployment'], 'NOT RUN')

    def test_new_supplies_have_no_explosive_or_projectile_inventory(self):
        for p, d in self.models.values():
            for tag in d['new_tags'].values():
                for item in nbtlib.parse_nbt(tag).get('Items', []):
                    name = str(item['id'])
                    self.assertNotIn(name, {'minecraft:gunpowder', 'minecraft:tnt', 'minecraft:fire_charge'})
                    self.assertFalse(name.startswith('createbigcannons:'))

    def test_combined_guard_refuses_an_unwritten_addition(self):
        def bad(p):
            p.blocks[31, 72, 0] = 'minecraft:oak_planks'
            return []
        with patch('tools.grand_harbor_deck_furnishings.decorate', bad):
            with self.assertRaisesRegex(UserError, 'unknown space'):
                details.decorate(self.registry, 'golden-petrel')

    def test_combined_guard_refuses_silent_original_inventory_replacement(self):
        def bad(p):
            pos = next(iter(p.tags))
            p.tags[pos] = '{Items:[]}'
            return []
        with patch('tools.grand_harbor_deck_furnishings.decorate', bad):
            with self.assertRaisesRegex(UserError, 'original inventory tag'):
                details.decorate(self.registry, 'golden-petrel')

    def test_cabin_authoring_refuses_occupied_or_unwritten_targets(self):
        for occupied in (None, 'minecraft:stone'):
            p = details.existing_model(self.registry, 'golden-petrel')
            if occupied is None:
                del p.blocks[-8, 9, 21]
            else:
                p.blocks[-8, 9, 21] = occupied
            before, tags = dict(p.blocks), deepcopy(p.tags)
            with self.assertRaisesRegex(UserError, 'explicit unused design AIR'):
                details.petrel_counting_cabin(p)
            self.assertEqual(p.blocks, before)
            self.assertEqual(p.tags, tags)


if __name__ == '__main__':
    unittest.main()
