"""Narrow pinned-material and held-water source boundaries, no game claims."""
import unittest
from control_room.common import UserError
from tools.artistic_eastern_foundation_profiles import column
from tools.artistic_create_substrate import JAR_SHA,CLASS_SHA


class EasternFoundationProfileTests(unittest.TestCase):
    def zinc(self):return{'artifact_sha256':JAR_SHA,'class_sha256':CLASS_SHA,'factory_class':'net/minecraft/world/level/block/Block'}

    def test_zinc_retains_actual_id_and_needs_the_exact_reviewed_factory(self):
        result=column(lambda x,y,z:'create:zinc_ore',0,0,63,self.zinc())
        self.assertEqual(result['terminal'][-1],'create:zinc_ore')
        self.assertEqual(result['status'],'SAVED_PINNED_ZINC_TERMINAL')
        with self.assertRaises(UserError):column(lambda x,y,z:'create:zinc_ore',0,0,63,{**self.zinc(),'class_sha256':'0'*64})

    def test_water_hold_never_leaks_a_partial_air_fill_proposal(self):
        states={62:'minecraft:air',61:'minecraft:water[level=0]'}
        result=column(lambda x,y,z:states[y],0,0,63,self.zinc())
        self.assertEqual(result['status'],'HELD_WATER');self.assertEqual(result['fill_positions'],[])

    def test_other_modded_rocks_do_not_borrow_the_zinc_proof(self):
        for value in('create:limestone','create:scoria','upgrade_aquatic:embedded_ammonite[facing=north]'):
            with self.subTest(value=value):
                result=column(lambda x,y,z:value,0,0,63,self.zinc())
                self.assertEqual(result['status'],'HELD_UNQUALIFIED_BLOCK');self.assertEqual(result['fill_positions'],[])


if __name__=='__main__':unittest.main()
