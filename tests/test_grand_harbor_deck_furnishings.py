"""Portable source checks; these do not establish native collision or visual quality."""
from copy import deepcopy
import unittest
from unittest.mock import patch

import nbtlib

from control_room.common import UserError
from tests.test_grand_harbor_fleet import registry
from tools import grand_harbor_fleet as fleet
from tools import grand_harbor_deck_furnishings as furnishings


class DeckFurnishingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.originals, cls.decorated, cls.groups = {}, {}, {}
        r = registry()
        for key, spec in fleet.SPECS.items():
            p = fleet.FleetShip(r, spec)
            for operation in (fleet.hull, fleet.raised_decks, fleet.magazine_and_stores,
                              fleet.berthing, fleet.galley_and_guns, fleet.captain,
                              fleet.working_deck, fleet.companionways, fleet.rig):
                operation(p)
            p.finish_ropes()
            cls.originals[key] = p
            cls.decorated[key] = deepcopy(p)
            cls.groups[key] = furnishings.decorate(cls.decorated[key])

    def test_only_explicit_air_changes_and_every_delta_has_a_named_group(self):
        for key, before in self.originals.items():
            with self.subTest(ship=key):
                after = self.decorated[key]
                self.assertEqual(before.blocks.keys(), after.blocks.keys())
                changed = {q for q in before.blocks if before.blocks[q] != after.blocks[q]}
                self.assertTrue(changed)
                self.assertTrue(all(before.blocks[q] == fleet.AIR for q in changed))
                described = [tuple(q) for g in self.groups[key] for q in g['local_cells']]
                self.assertEqual(set(described), changed)
                self.assertEqual(len(described), len(set(described)))
                self.assertTrue(all(g['name'] and g['purpose'] for g in self.groups[key]))
                # All three assigned areas receive detail; hold/captain furniture does not.
                levels = {q[1] for q in changed}
                self.assertTrue({before.spec.decks[2]+1, before.spec.decks[2]+2,
                                 before.spec.decks[1]+2, before.spec.weather+1} <= levels)
                self.assertTrue(levels <= {before.spec.decks[2]+1, before.spec.decks[2]+2,
                                          before.spec.decks[1]+2, before.spec.weather+1})
        self.assertEqual(len({tuple(g['name'] for g in groups) for groups in self.groups.values()}), 3)

    def test_original_stocks_guns_commands_and_all_room_routes_survive(self):
        for key, before in self.originals.items():
            after = self.decorated[key]
            self.assertTrue(all(after.tags[q] == tag for q, tag in before.tags.items()))
            self.assertEqual(before.commands, after.commands)
            self.assertEqual(before.guns, after.guns)
            self.assertEqual(before.rooms, after.rooms)
            self.assertEqual(fleet.circulation(before)['rooms_reached'],
                             fleet.circulation(after)['rooms_reached'])
            for q in before.route_clearance | before.hatch_clearance:
                self.assertEqual(before.blocks.get(q), after.blocks.get(q))
            for q in before.blocks:
                if before.blocks[q] != fleet.AIR:
                    self.assertEqual(before.blocks[q], after.blocks[q])

    def test_new_storage_is_empty_and_no_ammunition_or_new_inventory_is_seeded(self):
        for key, before in self.originals.items():
            after = self.decorated[key]
            for q in after.tags.keys() - before.tags.keys():
                self.assertEqual(before.blocks[q], fleet.AIR)
                tag = nbtlib.parse_nbt(after.tags[q])
                self.assertEqual(list(tag['Items']), [])
                self.assertNotIn('LootTable', tag)
                self.assertIn('empty', str(tag['CustomName']))
            changed = {after.blocks[q] for q in before.blocks if before.blocks[q] != after.blocks[q]}
            self.assertFalse(any(any(term in state for term in ('gunpowder', 'tnt', 'cannon', 'ammunition'))
                                 for state in changed))

    def test_occupied_missing_and_reserved_target_refuse_without_partial_decoration(self):
        for variant in ('occupied', 'missing', 'reserved'):
            with self.subTest(variant=variant):
                p = deepcopy(self.originals['resolute-wren'])
                q = tuple(self.groups['resolute-wren'][0]['local_cells'][0])
                if variant == 'occupied':
                    p.blocks[q] = 'minecraft:stone_bricks'
                elif variant == 'missing':
                    del p.blocks[q]
                else:
                    p.route_clearance.add(q)
                blocks, tags = dict(p.blocks), dict(p.tags)
                with self.assertRaisesRegex(UserError, 'explicit baseline AIR'):
                    furnishings.decorate(p)
                self.assertEqual(p.blocks, blocks)
                self.assertEqual(p.tags, tags)

    def test_a_missing_counter_floor_refuses_instead_of_floating_props(self):
        p = deepcopy(self.originals['golden-petrel'])
        x,y,z = self.groups['golden-petrel'][0]['local_cells'][0]
        p.blocks[x,y-1,z] = fleet.AIR
        blocks, tags = dict(p.blocks), dict(p.tags)
        with self.assertRaisesRegex(UserError, 'lacks a full floor or intended tabletop'):
            furnishings.decorate(p)
        self.assertEqual(p.blocks, blocks)
        self.assertEqual(p.tags, tags)
        # The real station11 table is absent after the original companionway.
        self.assertEqual(self.decorated['golden-petrel'].blocks[-4,0,11], fleet.AIR)

    def test_failed_final_circulation_restores_the_source_object(self):
        p = deepcopy(self.originals['mercy-of-the-tide'])
        blocks, tags = dict(p.blocks), dict(p.tags)
        required = set(p.required_ids)
        with patch.object(furnishings, 'circulation', side_effect=[{}, UserError('fixture disconnected')]) as check:
            with self.assertRaisesRegex(UserError, 'fixture disconnected'):
                furnishings.decorate(p)
        self.assertEqual(check.call_count, 2)
        self.assertEqual(p.blocks, blocks)
        self.assertEqual(p.tags, tags)
        self.assertEqual(p.required_ids, required)


if __name__ == '__main__':
    unittest.main()
