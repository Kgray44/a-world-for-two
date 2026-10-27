import unittest

from control_room.common import UserError
from tools.artistic_neighborhood_roofs import PARTS,derive,ridge_part


class NativeRidgeRuleTests(unittest.TestCase):
    def test_native_semantic_anchors_and_rotation_cover_all_sixteen_masks(self):
        self.assertEqual(ridge_part(False,False,False,False),'switched_0')
        self.assertEqual(ridge_part(True,False,True,False),'switched_0')
        self.assertEqual(ridge_part(False,True,False,True),'switched_90')
        self.assertEqual(ridge_part(True,False,False,False),'top_end_0')
        self.assertEqual(ridge_part(True,False,False,True),'top_outer_0')
        self.assertEqual(ridge_part(True,True,True,False),'three_way_0')
        self.assertEqual(ridge_part(True,True,True,True),'four_way')
        for bits in range(1,15):
            values=[bool(bits&(1<<n)) for n in range(4)]
            before=ridge_part(*values)
            rotated=ridge_part(values[3],values[0],values[1],values[2])
            stem,angle=before.rsplit('_',1)
            expected=(int(angle)+90)%(180 if stem=='switched' else 360)
            self.assertEqual(rotated,stem+'_'+str(expected))

    def test_same_identity_only_and_only_part_expectation_changes(self):
        a,b='mcwroofs:spruce_top_roof','mcwroofs:dark_oak_top_roof'
        palette=[a+'[part=switched_0]',b+'[part=switched_0]','minecraft:red_bed[part=head,facing=north]']
        original={'palette':palette,'blocks':[[0,70,0,0],[1,70,0,0],[0,70,-1,1],[4,71,3,2]],
                  'block_entities':[{'pos':[4,70,3],'nbt':'{Items:[]}'}],'commands':[]}
        registry={'blocks':{a:{'part':list(PARTS)},b:{'part':list(PARTS)}}}
        fixed,changes,ridges=derive(registry,original)
        self.assertEqual(ridges[0,70,0],a+'[part=top_end_90]')
        self.assertEqual(ridges[1,70,0],a+'[part=top_end_270]')
        self.assertEqual(fixed['blocks'][-1],original['blocks'][-1])
        self.assertEqual(fixed['block_entities'],original['block_entities'])
        self.assertEqual(fixed['commands'],[])
        self.assertEqual(len(changes),2)
        self.assertTrue(fixed['construction_forbidden'])

    def test_unknown_native_part_and_ambiguous_neighbor_values_fail_closed(self):
        with self.assertRaisesRegex(UserError,'booleans'):ridge_part(1,False,False,False)
        key='mcwroofs:spruce_top_roof'
        plan={'palette':[key+'[part=switched_0]'],'blocks':[[0,70,0,0],[1,70,0,0]],'block_entities':[],'commands':[]}
        with self.assertRaisesRegex(UserError,'registered'):derive({'blocks':{key:{'part':['switched_0']}}},plan)


if __name__=='__main__':unittest.main()
