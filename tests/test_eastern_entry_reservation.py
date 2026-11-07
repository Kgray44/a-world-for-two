import unittest
from unittest.mock import Mock
from control_room.common import UserError
from tools import artistic_eastern_compound_sprint as e


def registry():
    faces=['north','east','south','west'];axis=['x','y','z'];boolean=['true','false']
    return {'blocks':{
      'minecraft:air':{},'minecraft:stone':{},
      'mcwdoors:dark_oak_cottage_door':{'facing':faces,'half':['lower','upper'],'hinge':['left','right'],'open':boolean,'powered':boolean},
      'mcwwindows:dark_oak_four_window':{'facing':faces,'windowstate':['locked','unlocked']},
      'minecraft:dark_oak_stairs':{'facing':faces,'half':['bottom','top'],'shape':['straight'],'waterlogged':boolean},
      'minecraft:stripped_dark_oak_log':{'axis':axis},'chipped:reinforced_dark_oak_log':{'axis':axis},'chipped:edged_stripped_dark_oak_log':{'axis':axis},
      'mythrais:curved_corbel_dark_oak':{'facing':faces,'shape':['0']}}}


def room():
    spec={'name':'Actual overlapping entry regression','program':'archive','masses':[{'bounds_xz':[0,0,10,10],'floor_y':0,'storeys':1}],
      'actual_building_floor_columns_xz':[[x,z]for x in range(11)for z in range(11)]}
    p=e.Compound(registry(),spec,{'fixed':{},'bes':set(),'retire':{}},set(),0)
    p.sign=Mock() # Sign text is independent of the actual entry/window bug.
    for x in range(11):
        for z in range(11):
            p.put(x,0,z,'minecraft:stone')
            for y in range(1,5):p.put(x,y,z,'minecraft:stone'if x in(0,10)or z in(0,10)else'minecraft:air')
    e.grounded_entry(p,(0,0,10,10),0,{(1,11)},set())
    return p


class EntryReservationTests(unittest.TestCase):
    def test_real_ground_entry_survives_later_overlapping_window_pass(self):
        p=room();self.assertEqual(p.entries[0]['local'],[1,1,10])
        expected=e.intended_entry_states(p.registry,p.entries)
        e.outer_windows(p,(0,0,10,10),0,1,0)
        self.assertEqual({q:p.blocks[q]for q in expected},expected)
        self.assertTrue(any(v.startswith('mcwwindows:')for v in p.blocks.values()))
        self.assertEqual(e.audit_entry_states(p.registry,p.entries,p.blocks)['real_matching_door_pairs'],1)

    def test_later_furnishing_cannot_block_threshold_or_replace_half(self):
        p=room();before=dict(p.blocks)
        for q in p.entry_door_states|dict.fromkeys(p.entry_clearance_points)|dict.fromkeys(p.entry_threshold_points):p.put(*q,'minecraft:stone')
        for q in p.entry_door_states|dict.fromkeys(p.entry_threshold_points):self.assertEqual(p.blocks[q],before[q])
        self.assertTrue(all(p.blocks.get(q,'minecraft:air')=='minecraft:air'for q in p.entry_clearance_points))

    def test_an_entry_name_cannot_hide_a_missing_upper_door(self):
        p=room();q=next(q for q,v in p.entry_door_states.items()if 'half=upper'in v);p.blocks[q]='minecraft:stone'
        with self.assertRaises(UserError):e.audit_entry_states(p.registry,p.entries,p.blocks)
