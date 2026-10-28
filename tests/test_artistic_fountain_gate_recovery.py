"""Pure control/expected-state contracts; no saved world or native action."""
from unittest import TestCase
from tools.artistic_fountain_gate_recovery import expected_states,replace_property,TORCHES,WIRES,SOURCE,DIODE
from tools.artistic_spawn_plaza import STOP_LEVER,PISTON,PLUG_OPEN,OUTLET


class GateRecoveryContracts(TestCase):
    def fixture(self):
        registry={'blocks':{'minecraft:sticky_piston':{'extended':['true','false'],'facing':['north']},
                            'minecraft:piston_head':{'facing':['north'],'short':['false'],'type':['sticky']}}}
        observed={STOP_LEVER:'minecraft:lever[face=wall,facing=east,powered=false]',SOURCE:'minecraft:chiseled_quartz_block',
                  DIODE:'minecraft:repeater[delay=1,facing=south,locked=false,powered=false]',
                  PISTON:'minecraft:sticky_piston[extended=false,facing=north]',PLUG_OPEN:'minecraft:air',OUTLET:'minecraft:chiseled_quartz_block'}
        for n,p in enumerate(TORCHES):observed[p]='minecraft:redstone_torch[lit='+str(n%2==0).lower()+']'
        for p in WIRES:observed[p]='minecraft:redstone_wire[east=none,north=side,power=0,south=side,west=none]'
        return registry,observed

    def test_four_control_directions_and_source_are_not_replaced(self):
        registry,observed=self.fixture();on=expected_states(registry,observed,True)
        self.assertEqual(on[SOURCE],observed[SOURCE]);self.assertIn('facing=east',on[STOP_LEVER])
        self.assertIn('facing=south',on[DIODE]);self.assertIn('facing=north',on[PISTON])
        self.assertEqual(set(on),set(observed))

    def test_prospective_on_requires_real_head_and_port_plug_with_six_inversions(self):
        registry,observed=self.fixture();on=expected_states(registry,observed,True)
        self.assertIn('extended=true',on[PISTON]);self.assertIn('type=sticky',on[PLUG_OPEN])
        self.assertEqual(on[OUTLET],'minecraft:chiseled_quartz_block')
        self.assertEqual(['lit=true' in on[p] for p in TORCHES],[False,True,False,True,False,True])
        self.assertEqual([int(on[p].split('power=')[1].split(',')[0]) for p in WIRES],[15,14,13])

    def test_returned_plug_differs_from_actual_saved_orphaned_off_state(self):
        registry,observed=self.fixture();off=expected_states(registry,observed,False)
        self.assertEqual(off[PLUG_OPEN],'minecraft:chiseled_quartz_block');self.assertEqual(off[OUTLET],'minecraft:air')
        self.assertNotEqual(off[PLUG_OPEN],observed[PLUG_OPEN]);self.assertNotEqual(off[OUTLET],observed[OUTLET])
        self.assertEqual(['lit=true' in off[p] for p in TORCHES],[True,False,True,False,True,False])

    def test_property_change_preserves_other_native_control_properties(self):
        s='minecraft:repeater[delay=1,facing=south,locked=false,powered=false]'
        self.assertEqual(replace_property(s,'powered',True),'minecraft:repeater[delay=1,facing=south,locked=false,powered=true]')
        with self.assertRaisesRegex(Exception,'absent'):replace_property(s,'invented',True)
