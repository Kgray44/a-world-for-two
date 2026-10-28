import copy
import tempfile
import unittest
from pathlib import Path

import plan


class LifeExtensionPlanTests(unittest.TestCase):
    def group(self, **values):
        return dict(slot='quiet_glade', entity='naturalist:deer', habitat='dry_woodland_glade', count=2, **values)

    def test_complete_curated_population_includes_old_species_and_is_never_executable(self):
        data = plan.catalog(); result = plan.propose(data['candidate_groups'], data)
        self.assertEqual(result['population_budget'], 64)
        self.assertTrue(result['includes_original_four_species'])
        self.assertFalse(result['seed_authorized'])
        self.assertIsNone(result['world_coordinates']); self.assertIsNone(result['UUIDs'])
        self.assertNotEqual(result['format'], 'awft-habitat-life-recipe:1')

    def test_unknown_fairy_hostile_or_projectile_category_never_grants_admission(self):
        for key in ('fairytales:fairy', 'simplyswords:soul_pyre_wisp', 'minecraft:zombie', 'doggytalents:dog_beam'):
            row = self.group(); row['entity'] = key
            with self.subTest(key=key), self.assertRaises(ValueError): plan.propose([row])

    def test_villager_is_exact_misc_exception_not_permission_for_every_misc_entity(self):
        row = dict(slot='town_beds', entity='minecraft:villager', habitat='inhabited_home_and_job', count=2)
        result = plan.propose([row]); self.assertEqual(result['groups'][0]['native_category'], 'misc')
        row['entity'] = 'minecraft:item'
        with self.assertRaises(ValueError): plan.propose([row])

    def test_water_and_town_species_cannot_be_relabelled_dry_glade(self):
        for key in ('crittersandcompanions:koi_fish', 'fishofthieves:pondie', 'minecraft:villager'):
            row = self.group(); row['entity'] = key
            with self.subTest(key=key), self.assertRaises(ValueError): plan.propose([row])

    def test_ownership_NoAI_or_fake_native_success_fields_are_rejected(self):
        for key in ('NoAI', 'owner_uuid', 'tamed', 'profession', 'native_spawn_passed', 'feet', 'NBT'):
            row = self.group(); row[key] = True
            with self.subTest(key=key), self.assertRaises(ValueError): plan.propose([row])

    def test_duplicate_slots_boolean_counts_and_species_overallocation_are_refused(self):
        with self.assertRaises(ValueError): plan.propose([self.group(), self.group()])
        row = self.group(); row['count'] = True
        with self.assertRaises(ValueError): plan.propose([row])
        rows = [self.group(), self.group(), self.group(), self.group()]
        for n, row in enumerate(rows): row['slot'] = 'glade_' + str(n)
        with self.assertRaises(ValueError): plan.propose(rows)

    def test_global_cap_cannot_be_doubled_by_combining_original_and_extension_groups(self):
        data = copy.deepcopy(plan.catalog())
        for row in data['species']: row['candidate_population_cap'] = 128
        groups = copy.deepcopy(data['candidate_groups'])
        groups.append(dict(slot='extra_original_deer', entity='naturalist:deer', habitat='dry_woodland_glade', count=2))
        with self.assertRaisesRegex(ValueError, 'Whole-population'): plan.propose(groups, data)

    def test_artifact_hash_check_is_real_and_read_only(self):
        import hashlib
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'fixture.jar'; path.write_bytes(b'actual fixture bytes')
            data = {'artifacts': [{'kind': 'selected_mod', 'filename': path.name, 'bytes': path.stat().st_size,
                                   'sha512': hashlib.sha512(path.read_bytes()).hexdigest()}]}
            self.assertEqual(plan.verify_pins(folder, data)['read_only_selected_artifact_pins'], ['fixture.jar'])
            path.write_bytes(b'x' * path.stat().st_size)
            with self.assertRaises(ValueError): plan.verify_pins(folder, data)


if __name__ == '__main__': unittest.main()
