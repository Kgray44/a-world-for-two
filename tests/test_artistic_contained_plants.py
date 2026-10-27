import unittest

from control_room.common import UserError
from tools.artistic_contained_plants import AIR,CENTERS,ROOT,corrections


class ContainedPlantProofTests(unittest.TestCase):
    def setUp(self):
        self.expected={}
        self.actual={}
        for x,y,z in CENTERS:
            self.expected[x,y,z]='minecraft:flowering_azalea'
            self.expected[x,y-1,z]='supplementaries:planter[extended=false,waterlogged=false]'
            self.actual[x,y-2,z]='minecraft:stone_bricks'
        self.actual.update(self.expected)
        self.actual[ROOT]='minecraft:rooted_dirt'
        self.actual[1181,70,-1105]='minecraft:oak_log[axis=y]'
        self.actual[1181,71,-1105]='minecraft:oak_log[axis=y]'
        self.actual[1182,71,-1105]='minecraft:flowering_azalea_leaves[distance=1,persistent=false,waterlogged=false]'

    def run_proof(self,old=None,protected=()):
        return corrections(self.expected,lambda p:self.actual.get(p,AIR),
                           lambda p:(old or {}).get(p,AIR),set(protected))

    def test_proven_tree_and_all_bank_pots(self):
        changed,pots,counts=self.run_proof()
        self.assertEqual(len(pots),6)
        self.assertEqual(sum(v=='minecraft:potted_flowering_azalea_bush' for v in changed.values()),6)
        self.assertEqual(changed[ROOT],'minecraft:chiseled_stone_bricks')
        self.assertEqual(changed[1181,71,-1105],AIR)
        self.assertEqual(counts['minecraft:oak_log'],2)
        self.assertNotIn((1193,70,-1113),changed)

    def test_preexisting_natural_tree_cell_is_not_deleted(self):
        with self.assertRaisesRegex(UserError,'not empty'):
            self.run_proof({(1182,71,-1105):'minecraft:oak_leaves[distance=1,persistent=false,waterlogged=false]'})

    def test_unrelated_disconnected_trunk_refuses_all_output(self):
        self.actual[1189,74,-1102]='minecraft:oak_log[axis=y]'
        with self.assertRaisesRegex(UserError,'Disconnected trunk'):
            self.run_proof()

    def test_tree_cell_containing_be_is_protected(self):
        with self.assertRaisesRegex(UserError,'saved block entity'):
            self.run_proof(protected={(1182,71,-1105)})

    def test_intersection_with_another_authored_solid_is_not_weakened(self):
        self.expected[1182,71,-1105]='minecraft:stone_bricks'
        with self.assertRaisesRegex(UserError,'another authored solid'):
            self.run_proof()


if __name__=='__main__':unittest.main()
