"""Original-AIR furnishing custody tests; no native or visual acceptance."""
from copy import deepcopy
import unittest

from control_room.common import UserError
from tests.test_grand_harbor_fleet import registry
from tools.grand_harbor_fleet import AIR, circulation
from tools.grand_harbor_smallcraft import SmallCraft, SPECS, hull, boarding, cabin, equipment, rig
from tools.grand_harbor_smallcraft_furnishings import TARGETS, decorate


def original(key):
    r = registry()
    r['blocks']['minecraft:crafting_table'] = {}
    # Exact property enums from the preserved native export; additions only.
    r['blocks']['supplementaries:hourglass'] = {
        'facing': ['north', 'east', 'south', 'west', 'up', 'down'],
        'light_level': [str(i) for i in range(16)], 'waterlogged': ['true', 'false'],
    }
    r['blocks']['farmersdelight:cutting_board'] = {
        'facing': ['north', 'south', 'west', 'east'], 'waterlogged': ['true', 'false'],
    }
    r['blocks']['farmersdelight:cooking_pot'] = {
        'facing': ['north', 'south', 'west', 'east'], 'support': ['none', 'tray', 'handle'],
        'waterlogged': ['true', 'false'],
    }
    r['items'] = sorted(set(r['items']) | {
        'minecraft:lead', 'minecraft:clock', 'minecraft:fishing_rod', 'farmersdelight:iron_knife',
    })
    p = SmallCraft(r, SPECS[key])
    for operation in (hull, boarding, cabin, equipment, rig):
        operation(p)
    return p


class SmallCraftFurnishingTests(unittest.TestCase):
    def test_all_three_preserve_original_non_air_tags_rooms_and_routes(self):
        groups = []
        for key in SPECS:
            with self.subTest(key=key):
                p = original(key)
                before, tags, rooms, commands = dict(p.blocks), deepcopy(p.tags), deepcopy(p.rooms), list(p.commands)
                proof = decorate(p)
                changed = {pos for pos, state in p.blocks.items() if before[pos] != state}
                self.assertEqual(changed, TARGETS[key])
                self.assertTrue(all(before[pos] == AIR for pos in changed))
                self.assertEqual(set(before), set(p.blocks))
                self.assertTrue(all(p.blocks[pos] == state for pos, state in before.items() if state != AIR))
                self.assertTrue(all(p.tags[pos] == tag for pos, tag in tags.items()))
                self.assertTrue(all(before[pos] == AIR for pos in p.tags.keys()-tags.keys()))
                self.assertEqual(p.rooms, rooms)
                self.assertEqual(p.commands, commands)
                self.assertEqual(len(circulation(p)['rooms_reached']), len(rooms))
                self.assertEqual(proof['materials']['violations'], [])
                self.assertGreaterEqual(len(proof['visual_groups']), 4)
                groups.append(tuple(proof['visual_groups']))
        self.assertEqual(len(set(groups)), 3)

    def test_original_stock_container_at_a_furnishing_site_is_preserved(self):
        p = original('tern-pilot-cutter')
        site = (2, 2, 7)
        p.chest(*site, 'Existing owner stock must survive', ['minecraft:bread'])
        before, tags = dict(p.blocks), deepcopy(p.tags)
        with self.assertRaisesRegex(UserError, 'original authored AIR'):
            decorate(p)
        self.assertEqual(p.blocks, before)
        self.assertEqual(p.tags, tags)

    def test_air_with_an_existing_tag_is_preserved(self):
        p = original('salt-marigold-ketch')
        site = (-3, 2, -5)
        p.tags[site] = '{CustomName:"retained source custody",Items:[]}'
        before, tags = dict(p.blocks), deepcopy(p.tags)
        with self.assertRaisesRegex(UserError, 'original authored AIR'):
            decorate(p)
        self.assertEqual(p.blocks, before)
        self.assertEqual(p.tags, tags)

    def test_unwritten_site_is_never_assumed_air(self):
        p = original('reed-fin-river-lighter')
        del p.blocks[2, 2, -5]
        before = dict(p.blocks)
        with self.assertRaisesRegex(UserError, 'original authored AIR'):
            decorate(p)
        self.assertEqual(p.blocks, before)

    def test_second_call_refuses_instead_of_reinitializing_new_supplies(self):
        p = original('tern-pilot-cutter')
        decorate(p)
        before, tags = dict(p.blocks), deepcopy(p.tags)
        with self.assertRaisesRegex(UserError, 'original authored AIR'):
            decorate(p)
        self.assertEqual(p.blocks, before)
        self.assertEqual(p.tags, tags)


if __name__ == '__main__':
    unittest.main()
