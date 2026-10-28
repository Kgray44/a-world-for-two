import copy
from pathlib import Path
import unittest

from control_room.common import UserError
from tools import artistic_tree_residual_review47 as r


class TreeResidualReviewBoundaries(unittest.TestCase):
    def setUp(self):
        self.registry={'blocks':{'minecraft:water':{'level':['0','1']},'minecraft:ice':{},
                                'minecraft:tall_grass':{'half':['lower','upper']}}}

    def test_complete_properties_are_mandatory_not_selected_property_matching(self):
        self.assertEqual(r.state_checked('minecraft:water[level=0]',self.registry),'minecraft:water[level=0]')
        for bad in ('minecraft:water','minecraft:water[level=0,level=1]',
                    'minecraft:water[level=9]','minecraft:ice[level=0]'):
            with self.subTest(state=bad),self.assertRaises(UserError):r.state_checked(bad,self.registry)

    def test_complete_unique_integer_field_refuses_missing_duplicate_and_negative_index(self):
        bounds=[0,62,0,1,62,0]
        doc={'palette':['minecraft:ice','minecraft:water[level=0]'],'blocks':[[0,62,0,1],[1,62,0,0]]}
        self.assertEqual(len(r.field_checked(doc,self.registry,bounds)),2)
        for rows in ([[0,62,0,1]],[[0,62,0,1],[0,62,0,0]],[[0,62,0,-1],[1,62,0,0]],
                     [[False,62,0,1],[1,62,0,0]]):
            with self.subTest(rows=rows),self.assertRaises(UserError):
                r.field_checked({'palette':doc['palette'],'blocks':rows},self.registry,bounds)

    def test_comparison_records_ambient_transition_without_restoration(self):
        before={(1226,62,-1091):'minecraft:water[level=0]',(1244,62,-1088):'minecraft:ice'}
        after={(1226,62,-1091):'minecraft:ice',(1244,62,-1088):'minecraft:water[level=0]'}
        untouched=copy.deepcopy(after)
        self.assertEqual(len(r.changes(before,after)),2)
        self.assertEqual(after,untouched)

    def test_whole_recheck_precedes_even_nonmutating_hook_and_latches_stay_original(self):
        root=Path(__file__).resolve().parents[1]
        proposed=(root/'compat/proposals/tree-pre-mutation-r1/NativeTreeGrowthSupport.java').read_text(encoding='utf-8')
        original=(root/'compat/proposals/tree-pre-mutation-r1/NativeTreeGrowthSupport47-base.java.txt').read_text(encoding='utf-8')
        grow=proposed.split('private void grow()',1)[1].split('public void tick(',1)[0]
        self.assertLess(grow.index('PreMutationFieldCheck.requireUnchanged'),grow.index('scope.hookWitness(root)'))
        self.assertLess(grow.index('PreMutationFieldCheck.requireUnchanged'),grow.index('mutated=true'))
        self.assertIn('refused_before_owned_mutation',grow)
        old_latch=original.split('private void quarantine(',1)[1].split('private static final class FailedFields',1)[0]
        new_latch=proposed.split('private void quarantine(',1)[1].split('private static final class FailedFields',1)[0]
        self.assertEqual(old_latch,new_latch)
        self.assertNotIn('Files.delete',proposed)


if __name__=='__main__':unittest.main()
