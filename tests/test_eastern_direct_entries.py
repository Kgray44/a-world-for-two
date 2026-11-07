import unittest

from control_room.common import UserError
from tools.artistic_eastern_direct_build import require_physical_entries


class PhysicalEntries(unittest.TestCase):
    def source(self):
        return {'id':'entry-regression','origin':[1250,64,-1202],
                'entries':[{'local':[1,1,1],'outward':'south'}],
                'complete_expected_state_context_ONLY':[
                    [1251,65,-1201,'mcwdoors:dark_oak_cottage_door[facing=north,half=lower,hinge=left,open=false,powered=false]'],
                    [1251,66,-1201,'mcwdoors:dark_oak_cottage_door[facing=north,half=upper,hinge=left,open=false,powered=false]']]}

    def test_actual_door_pair_passes(self):
        self.assertEqual(require_physical_entries(self.source()),1)

    def test_metadata_with_actual_window_blocks_refuses(self):
        source=self.source()
        for row in source['complete_expected_state_context_ONLY']:
            row[3]='mcwwindows:dark_oak_four_window[facing=south,windowstate=locked]'
        with self.assertRaises(UserError):require_physical_entries(source)

    def test_missing_or_wrong_facing_upper_half_refuses(self):
        source=self.source();source['complete_expected_state_context_ONLY'][1][3]='mcwdoors:dark_oak_cottage_door[facing=east,half=upper,hinge=left,open=false,powered=false]'
        with self.assertRaises(UserError):require_physical_entries(source)

    def test_native_after_field_must_retain_real_door(self):
        source=self.source();field={tuple(v[:3]):v[3]for v in source['complete_expected_state_context_ONLY']}
        field[1251,65,-1201]='minecraft:air'
        with self.assertRaises(UserError):require_physical_entries(source,field)

    def test_low_adjacent_window_knee_cannot_block_entry(self):
        source=self.source();source['complete_expected_state_context_ONLY'].append(
            [1251,66,-1200,'mythrais:curved_corbel_dark_oak[facing=south,shape=0]'])
        with self.assertRaises(UserError):require_physical_entries(source)


if __name__=='__main__':unittest.main()
