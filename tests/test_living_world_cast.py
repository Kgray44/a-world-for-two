"""Protect existing character edits and UUID custody during source preparation."""
from copy import deepcopy
import unittest
import uuid

from control_room.common import UserError
from living_world.defaults import configuration
from tools.living_world_cast import prepare


def recipe(key='barnacle-bill', offset=0):
    p = [offset, 65, 0]
    return {'format': 'awft-habitat-life-recipe:4', 'copied_entity_NBT': False,
            'population_namespace': '0af036d5-43fd-4f66-a30b-21e3d99ce018', 'seed': '123',
            'world_path': 'test-only', 'dimension': 'minecraft:overworld', 'members': [
                {'uuid': str(uuid.uuid5(uuid.NAMESPACE_OID, key)), 'entity': 'minecraft:villager',
                 'native_class': 'net.minecraft.world.entity.npc.Villager', 'native_MobCategory': 'misc',
                 'source_group_id': 'character-' + key, 'town_site': 'test-fixture-room', 'feet': p,
                 'habitat': {'kind': 'HOME', 'bed': [offset, 65, 2], 'job': [offset, 65, 3],
                             'roof': [offset, 69, 0], 'bed_path': [p], 'job_path': [p]}}]}


class CastPreparationTests(unittest.TestCase):
    def setUp(self):
        self.registry = {'config': configuration()}

    def test_preserves_owner_name_model_dialogue_and_ai_settings(self):
        p = next(p for p in self.registry['config']['characters'] if p['id'] == 'barnacle-bill')
        p['name'] = 'Bill, edited by owner'
        p['ai']['model'] = 'gpt-6.1-sol'
        p['dialogue']['lines']['weather'] = ['Owner-authored weather line']
        before = deepcopy(self.registry)
        drafts, report = prepare(self.registry, [recipe()])
        result = drafts['barnacle-bill']['character']
        self.assertEqual(result['name'], p['name'])
        self.assertEqual(result['ai'], p['ai'])
        self.assertEqual(result['personality'], p['personality'])
        self.assertEqual(result['dialogue']['lines']['weather'], ['Owner-authored weather line'])
        self.assertEqual(result['location']['status'], 'assigned')
        self.assertIsNone(result['location']['measured_at'])
        self.assertEqual(self.registry, before)
        self.assertEqual(len(report['pending_site_ids']), 9)
        self.assertFalse(report['runtime_installed'])

    def test_refuses_replacing_existing_resident_or_double_binding(self):
        target = next(p for p in self.registry['config']['characters'] if p['id'] == 'barnacle-bill')
        target['entity_uuid'] = str(uuid.uuid4())
        with self.assertRaises(UserError):
            prepare(self.registry, [recipe()])
        target['entity_uuid'] = None
        self.registry['config']['characters'][1]['entity_uuid'] = recipe()['members'][0]['uuid']
        with self.assertRaises(UserError):
            prepare(self.registry, [recipe()])

    def test_refuses_shared_home_and_foreign_world(self):
        second = recipe('old-finn', 10)
        second['members'][0]['habitat']['bed'] = recipe()['members'][0]['habitat']['bed']
        with self.assertRaises(UserError):
            prepare(self.registry, [recipe(), second])
        second = recipe('old-finn', 10)
        second['world_path'] = 'another-world'
        with self.assertRaises(UserError):
            prepare(self.registry, [recipe(), second])

    def test_missing_rooms_remain_pending_without_invented_coordinates(self):
        drafts, report = prepare(self.registry, [])
        self.assertEqual(drafts, {})
        self.assertEqual(len(report['pending_site_ids']), 10)
        self.assertTrue(all('uuid' not in p and 'bed' not in p for p in report['configured_cast']))

    def test_refuses_fake_home_and_duplicate_recipe(self):
        bad = recipe()
        bad['members'][0]['habitat']['kind'] = 'DRY'
        with self.assertRaises(UserError):
            prepare(self.registry, [bad])
        with self.assertRaises(UserError):
            prepare(self.registry, [recipe(), recipe()])


if __name__ == '__main__':
    unittest.main()
