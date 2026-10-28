"""Synthetic source-boundary checks; none is Minecraft growth evidence."""
import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch

from control_room.common import UserError
from tools import artistic_forest47 as f


class Forest47Boundaries(unittest.TestCase):
    def test_remaining_is_exact_unperformed_subset(self):
        self.assertEqual([r[0] for r in f.REMAINING], ['copse-115', 'copse-158', 'copse-188', 'copse-206'])
        self.assertEqual([r[2] for r in f.REMAINING], [(1054,142,-881),(1223,66,-1046),(1191,124,-854),(1048,166,-824)])
        self.assertTrue({'copse-40','copse-92','copse-2','copse-37'}.isdisjoint(r[0] for r in f.REMAINING))

    def test_all_nine_use_authenticated_complete_derivation(self):
        descriptors = {s: 'a'*64 for s in f.SAPLINGS}
        member = {s.replace(':','--')+'.json': {'sha256':'b'*64} for s in f.SAPLINGS}
        derivation = {'relative_write_bounds':[-12,-5,-12,12,26,12]}
        def checked(path, expected, cap):
            name = Path(path).name
            if name == 'source-freeze.json':
                return {'qualification_receipt_sha256':'c'*64}
            if name == 'receipt.json':
                return {'files':member}
            if name == Path(f.pilot.DESCRIBE).name:
                return {'native_descriptor_sha256s':descriptors}
            species = name[:-5].replace('--',':')
            return {'sapling':species,'all_reachable_features_reviewed':True,
                'native_descriptor_sha256':descriptors[species], 'derivation':derivation,
                'derivation_sha256':hashlib.sha256(f.pilot.canonical(derivation)).hexdigest(),
                'relative_write_bounds':derivation['relative_write_bounds']}
        with patch.object(f.pilot,'qualifications'), patch.object(f.pilot,'checked',side_effect=checked):
            self.assertEqual(set(f.qualifications(Path('test-home'))), set(f.SAPLINGS))
        def truncated(path, expected, cap):
            row = checked(path,expected,cap)
            if 'derivation' in row:
                row['relative_write_bounds'] = [-3,-5,-3,3,11,3]
            return row
        with patch.object(f.pilot,'qualifications'), patch.object(f.pilot,'checked',side_effect=truncated):
            with self.assertRaises(UserError):
                f.qualifications(Path('test-home'))

    def test_write_known_disjointness_is_symmetric(self):
        old = {'write_bounds':[20,0,0,25,8,5],'known_bounds':[12,-2,-8,33,12,13]}
        self.assertTrue(f.conflict([10,0,0,13,8,3],[2,-2,-8,21,12,11],[old]))
        self.assertTrue(f.conflict([1,0,0,3,8,3],[-7,-2,-8,21,12,11],[old]))
        self.assertFalse(f.conflict([-20,0,0,-18,8,3],[-28,-2,-8,-10,12,11],[old]))

    def test_unknown_wet_canopy_and_cliff_are_not_empty_plot(self):
        class Terrain:
            def __init__(self,row): self.row=row
            def column(self,x,z): return self.row
        for row in ({'kind':'unknown'}, {'kind':'water','surface_y':63},
                    {'kind':'dry','surface_y':63,'existing_canopy_y':90},
                    {'kind':'dry','surface_y':67,'existing_canopy_y':None}):
            with self.subTest(row=row), self.assertRaises(UserError):
                f.quick_field(Terrain(row),(0,64,0),[-1,59,-1,1,75,1])
        f.quick_field(Terrain({'kind':'dry','surface_y':63,'existing_canopy_y':None}),
                      (0,64,0),[-1,59,-1,1,75,1])

    def test_wrong_pack_refuses_before_class_or_request_reads(self):
        with patch.object(f,'current_pack',return_value=(Path('unused'),'f'*64)):
            with self.assertRaisesRegex(UserError,'actual47 release'):
                f.runtime_pins(Path('unused'))


if __name__ == '__main__':
    unittest.main()
