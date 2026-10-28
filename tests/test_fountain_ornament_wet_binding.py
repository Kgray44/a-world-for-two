import copy
import unittest
from control_room.common import UserError
from tools import artistic_fountain_ornament_wet_binding as f


class WetBindingBoundaries(unittest.TestCase):
    def field(self):
        field={p:'minecraft:water[level=8]' for p in (f.OUTLET,*f.JET_WITNESSES)}
        field.update({f.HEADER:'minecraft:water[level=0]',f.WHEEL_SOURCE:'minecraft:water[level=0]',
            f.STOP_LEVER:'minecraft:lever[face=wall,facing=east,powered=false]',
            f.PISTON:'minecraft:sticky_piston[extended=false,facing=north]',
            f.PLUG_OPEN:'minecraft:chiseled_quartz_block'})
        return field

    def test_actual_wet_source_is_observed_without_mutation(self):
        field=self.field();before=copy.deepcopy(field)
        f.saved_wet_gate(field)
        self.assertEqual(field,before)

    def test_no_substitute_dry_source_or_missing_jet(self):
        for pos in (f.HEADER,f.WHEEL_SOURCE,f.JET_WITNESSES[0],f.OUTLET):
            field=self.field();field[pos]='minecraft:air'
            with self.subTest(position=pos),self.assertRaises(UserError):f.saved_wet_gate(field)

    def test_piston_control_or_plug_is_never_reset_to_make_binding_pass(self):
        for pos,value in ((f.STOP_LEVER,'minecraft:lever[face=wall,facing=east,powered=true]'),
                          (f.PISTON,'minecraft:sticky_piston[extended=true,facing=north]'),
                          (f.PLUG_OPEN,'minecraft:moving_piston[facing=north,type=sticky]')):
            field=self.field();field[pos]=value;before=copy.deepcopy(field)
            with self.subTest(position=pos),self.assertRaises(UserError):f.saved_wet_gate(field)
            self.assertEqual(field,before)


if __name__=='__main__':unittest.main()
