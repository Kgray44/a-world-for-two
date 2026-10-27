import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from control_room.common import UserError, digest, write_json
from tools.settlement_cinematic import final_harbor_geometry, verified_geometry


class CinematicGeometryBindingTests(unittest.TestCase):
    def geometry(self, root, name, x):
        path = root/(name+'.json')
        write_json(path, {'format': 'awft-native-settlement:1', 'seed': 'synthetic',
                          'world_path': 'synthetic-world', 'palette': ['minecraft:stone'],
                          'blocks': [[x, 70, 0, 0]]})
        return {'path': str(path), 'sha256': digest(path)}

    def proof(self, root, name, sha, **changes):
        value = {'operation': 'verify', 'plan_sha256': sha, 'blocks': 1,
                 'failures': 0, 'finished': '2026-10-27T00:00:00Z'}
        value.update(changes)
        write_json(root/name, value)

    def fixture(self, root):
        slugs = ('rosewater-resolute', 'amberwake', 'nightingales-debt', 'sea-lavender')
        vessels, pins = [], {}
        for x, slug in enumerate(slugs):
            metadata = self.geometry(root, slug, x)
            metadata['ship'] = {'slug': slug}
            pins[slug] = metadata['sha256']
            self.proof(root, 'ship-'+slug+'-'+metadata['sha256'][:12]+'-verify.json', metadata['sha256'])
            vessels.append(metadata)
        access = self.geometry(root, 'placed-access', 10)
        write_json(root/'grand-harbor-access-final.json', access)
        self.proof(root, 'grand-harbor-access-'+access['sha256'][:12]+'-verify.json', access['sha256'])
        harbor = {'vessels': vessels,
                  'access': {'path': str(root/'stale-unplaced-access.json'), 'sha256': '0'*64}}
        return harbor, pins, access

    def test_final_placed_access_wins_over_stale_aggregate_without_opening_old_plan(self):
        with tempfile.TemporaryDirectory(prefix='awft-scene-geometry-') as folder:
            root = Path(folder)
            harbor, pins, access = self.fixture(root)
            with patch('tools.settlement_cinematic.SHIP_SHAS', pins), patch('tools.settlement_cinematic.ACCESS_SHA', access['sha256']):
                vessels, bindings = final_harbor_geometry(root, harbor)
            self.assertEqual(len(vessels), 4)
            self.assertEqual(len(bindings), 5)
            self.assertEqual(bindings[-1][1]['sha256'], access['sha256'])
            self.assertFalse((root/'stale-unplaced-access.json').exists())
            self.assertEqual(harbor['access']['sha256'], '0'*64)

    def test_missing_final_access_never_falls_back_to_an_old_preparation(self):
        with tempfile.TemporaryDirectory(prefix='awft-scene-geometry-') as folder:
            root = Path(folder)
            harbor, pins, access = self.fixture(root)
            (root/'grand-harbor-access-final.json').unlink()
            with patch('tools.settlement_cinematic.SHIP_SHAS', pins), patch('tools.settlement_cinematic.ACCESS_SHA', access['sha256']):
                with self.assertRaises(UserError):
                    final_harbor_geometry(root, harbor)

    def test_flagship_must_match_the_reviewed_placed_hash(self):
        with tempfile.TemporaryDirectory(prefix='awft-scene-geometry-') as folder:
            root = Path(folder)
            harbor, pins, access = self.fixture(root)
            harbor['vessels'][0]['sha256'] = '0'*64
            with patch('tools.settlement_cinematic.SHIP_SHAS', pins), patch('tools.settlement_cinematic.ACCESS_SHA', access['sha256']):
                with self.assertRaises(UserError):
                    final_harbor_geometry(root, harbor)

    def test_pending_failed_or_mismatched_native_receipts_cannot_qualify_geometry(self):
        with tempfile.TemporaryDirectory(prefix='awft-scene-geometry-') as folder:
            root = Path(folder)
            geometry = self.geometry(root, 'reviewed', 1)
            for changes in ({'finished': None}, {'failures': 1}, {'blocks': 2},
                            {'plan_sha256': '0'*64}, {'operation': 'place'}):
                with self.subTest(changes=changes):
                    self.proof(root, 'verify.json', geometry['sha256'], **changes)
                    with self.assertRaises(UserError):
                        verified_geometry(root, geometry, geometry['sha256'], 'verify.json')

    def test_matching_plan_and_completed_native_receipt_retain_exact_provenance(self):
        with tempfile.TemporaryDirectory(prefix='awft-scene-geometry-') as folder:
            root = Path(folder)
            geometry = self.geometry(root, 'reviewed', 1)
            self.proof(root, 'verify.json', geometry['sha256'])
            _, source = verified_geometry(root, geometry, geometry['sha256'], 'verify.json')
            self.assertEqual(source['sha256'], geometry['sha256'])
            self.assertEqual(source['native_verification']['receipt_sha256'], digest(root/'verify.json'))
            self.assertEqual(source['native_verification']['failures'], 0)


if __name__ == '__main__':
    unittest.main()
