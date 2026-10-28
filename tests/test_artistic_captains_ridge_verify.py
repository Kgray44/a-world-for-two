import copy
import unittest

from control_room.common import UserError
from tools.artistic_captains_ridge_verify import ROOF, canonical
from tools.artistic_neighborhood_roofs import PARTS


class CaptainsRidgeTests(unittest.TestCase):
    def source(self):
        return {'palette':[ROOF+'[part=switched_0]'],
            'blocks':[[1042,79,z,0] for z in range(-1294,-1279)],
            'block_entities':[{'pos':[1040,65,-1281],'nbt':'{Items:[{Slot:0b,id:"minecraft:bread",count:3}]}'}],
            'commands':[],'construction_forbidden':True,'backup_sha256':'a'*64,'name':'immutable original'}

    def test_only_two_part_properties_change_and_all_tags_metadata_stay_identical(self):
        source=self.source();original=copy.deepcopy(source)
        corrected,changes,context=canonical({'blocks':{ROOF:{'part':list(PARTS)}}},source,lambda p:'minecraft:air')
        self.assertEqual(len(changes),2)
        self.assertEqual(source,original)
        self.assertEqual(corrected['block_entities'],source['block_entities'])
        self.assertEqual(corrected['backup_sha256'],source['backup_sha256'])
        self.assertTrue(corrected['construction_forbidden'])
        self.assertEqual([r[:3] for r in corrected['blocks']],[r[:3] for r in source['blocks']])
        self.assertGreater(len(context),0)

    def test_unwritten_same_roof_neighbor_is_not_assumed_air(self):
        with self.assertRaisesRegex(UserError,'never infer AIR'):
            canonical({'blocks':{ROOF:{'part':list(PARTS)}}},self.source(),lambda p:ROOF+'[part=switched_0]')

    def test_additional_native_ridge_branch_refuses_two_end_only_derivation(self):
        row=self.source();row['blocks'].append([1043,79,-1287,0])
        with self.assertRaises(UserError):
            canonical({'blocks':{ROOF:{'part':list(PARTS)}}},row,lambda p:'minecraft:air')


if __name__=='__main__':unittest.main()
