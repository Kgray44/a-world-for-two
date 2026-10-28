import unittest
from unittest.mock import patch
from tools.artistic_south_understory48 import planting_pocket,attached_vines,sector


class Ground:
    entities=set()
    def __init__(self,states=None):self.states=states or{}
    def column(self,x,z):return {'kind':'dry','surface_y':0}
    def state(self,x,y,z):return self.states.get((x,y,z),'minecraft:air')


class SouthUnderstory48Tests(unittest.TestCase):
    def test_protocol_sectors_bound_both_axes_with_attachment_margin(self):
        groups={}
        for x in range(636,1510,7):
            for z in range(-1205,-600,11):groups.setdefault(sector((x,64,z)),[]).append((x,z))
        for rows in groups.values():
            self.assertLessEqual(max(x for x,z in rows)-min(x for x,z in rows)+2,481)
            self.assertLessEqual(max(z for x,z in rows)-min(z for x,z in rows)+2,481)

    def test_tall_fern_keeps_both_halves_and_exact_extra_head_before(self):
        p=(1,1,1);root=(1,0,1)
        reg={'blocks':{'minecraft:fern':{},'minecraft:large_fern':{'half':['lower','upper']}}}
        with patch('tools.artistic_south_understory48.low.pocket',return_value=({p:'minecraft:fern'},{root:'minecraft:grass_block'},{p:'minecraft:air'},{})):
            blocks,soil,before,_=planting_pocket(Ground(),reg,(1,1),'sheltered_footwoods',0,set(),set(),{})
        self.assertEqual('minecraft:large_fern[half=lower]',blocks[p])
        self.assertEqual('minecraft:large_fern[half=upper]',blocks[1,2,1])
        self.assertEqual('minecraft:air',before[1,3,1]);self.assertEqual({root:'minecraft:grass_block'},soil)

    def test_vines_require_real_side_log_and_record_exact_support(self):
        reg={'blocks':{'minecraft:vine':{d:['false','true']for d in ('north','south','east','west','up')}}}
        terrain=Ground({(0,2,-1):'minecraft:oak_log[axis=y]'})
        vines,before=attached_vines(terrain,reg,(3,0),set(),set(),{},limit=1)
        self.assertIn((0,2,0),vines);self.assertIn('north=true',vines[0,2,0])
        self.assertEqual('minecraft:oak_log[axis=y]',before[0,2,-1])
        none,_=attached_vines(Ground(),reg,(3,0),set(),set(),{},limit=1)
        self.assertEqual({},none)


if __name__=='__main__':unittest.main()
