"""Bounded ship geometry checks; these do not claim native walking or rendering."""
import unittest

from control_room.common import UserError
from tools.settlement_ships import AIR, VESSELS, ShipPlan, hull, hull_halfwidth, rope_line


def fixture_registry():
    bools=['true','false']
    facing=['north','south','east','west','up','down']
    blocks={key:{} for key in ('minecraft:dark_oak_planks','minecraft:spruce_planks',
                                 'minecraft:blue_terracotta','minecraft:dark_oak_fence',
                                 'minecraft:glass_pane',AIR)}
    for key in ('minecraft:stripped_dark_oak_log','minecraft:stripped_spruce_log','minecraft:dark_oak_log'):
        blocks[key]={'axis':['x','y','z']}
    blocks['minecraft:dark_oak_trapdoor']={'facing':facing,'half':['top','bottom'],'open':bools,'waterlogged':bools}
    blocks['minecraft:lantern']={'hanging':bools,'waterlogged':bools}
    blocks['treasure2:skull_and_crossbones']={'facing':facing,'waterlogged':bools}
    return {'blocks':blocks,'items':[],'entities':[],'seed':'test-fixture','world_path':'synthetic-only'}


def fixture_survey(vessel,floor=20):
    cx,cz=vessel.center
    return {'samples':[{'x':x,'z':z,'y':63,'ground_y':floor,'ocean_floor_y':floor,
                        'block':'minecraft:water','fluid':True,'block_entities':[]}
                       for x in range(cx-80,cx+81,4) for z in range(cz-80,cz+81,4)]}


class HistoricShipGeometryTests(unittest.TestCase):
    def test_curved_bilge_is_sealed_on_every_face(self):
        vessel=VESSELS[0]
        p=ShipPlan(fixture_registry(),fixture_survey(vessel),vessel,'0'*64,{})
        hull(p)
        underwater=0
        for (x,y,z),state in p.blocks.items():
            if state!=AIR or y>p.sea:continue
            underwater+=1
            for dx,dy,dz in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)):
                self.assertIn((x+dx,y+dy,z+dz),p.blocks)
        self.assertGreater(underwater,100)

    def test_shallow_soundings_refuse_instead_of_excavating(self):
        vessel=VESSELS[0]
        p=ShipPlan(fixture_registry(),fixture_survey(vessel,62),vessel,'0'*64,{})
        with self.assertRaisesRegex(UserError,'shallow seabed'):
            p.require_depth()
        self.assertEqual(p.blocks,{})

    def test_air_clearance_of_completed_work_is_an_exclusion(self):
        vessel=VESSELS[0]
        fixed={(vessel.center[0],70,vessel.center[1]):AIR}
        p=ShipPlan(fixture_registry(),fixture_survey(vessel),vessel,'0'*64,fixed)
        with self.assertRaisesRegex(UserError,'completed work'):
            p.put(0,70,0,'minecraft:spruce_planks')
        p.put(0,70,0,AIR)
        self.assertEqual(p.blocks,{})

    def test_unknown_properties_fail_closed(self):
        vessel=VESSELS[0]
        p=ShipPlan(fixture_registry(),fixture_survey(vessel),vessel,'0'*64,{})
        with self.assertRaisesRegex(UserError,'properties'):
            p.state('minecraft:spruce_planks',facing='north')

    def test_diagonal_rigging_is_face_connected(self):
        points=list(rope_line((-8,70,-10),(0,112,0)))
        self.assertEqual(points[0],(-8,70,-10))
        self.assertEqual(points[-1],(0,112,0))
        self.assertTrue(all(sum(abs(a-b) for a,b in zip(p,q))==1 for p,q in zip(points,points[1:])))

    def test_four_distinct_roles_and_required_sail_states(self):
        self.assertEqual(len({(v.length,v.beam,v.masts) for v in VESSELS}),4)
        self.assertEqual([v.sail_state for v in VESSELS],
                         ['partly-unfurled','furled','furled','loose-drying'])
        flagship=VESSELS[0]
        self.assertLess(hull_halfwidth(flagship,-flagship.length//2+2,10),
                        hull_halfwidth(flagship,flagship.length//2-2,10))
        self.assertEqual(sum(v.offshore for v in VESSELS),1)


if __name__=='__main__':unittest.main()
