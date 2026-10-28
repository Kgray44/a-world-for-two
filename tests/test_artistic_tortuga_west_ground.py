"""Actual walking shoulders and authored support, not a native visual claim."""
import json
from pathlib import Path
import unittest

from control_room.common import UserError
from tools.artistic_materials import require_material_rule
from tools.artistic_tortuga_west_ground import key,path_to,workspaces
from tools.settlement_attractions import properties


class TortugaWestGroundTests(unittest.TestCase):
    def setUp(self):
        registry=json.loads((Path(__file__).parent/'fixtures/tortuga_west_ground_registry.json').read_text())
        self.spaces=workspaces(registry)

    def test_two_wide_route_never_accepts_a_centerline_across_a_wet_shoulder(self):
        free={(x,z)for x in range(7)for z in range(5)}
        free-={(3,z)for z in range(2,5)}
        route=path_to(free,(0,1),(5,1))
        self.assertIn((2,0),route)
        for x,z in route:
            self.assertTrue({(x,z),(x+1,z),(x,z+1),(x+1,z+1)}<=free)
        free.remove((3,0))
        with self.assertRaisesRegex(UserError,'No real two-wide dry connector'):
            path_to(free,(0,1),(5,1))

    def test_distinct_trade_stories_keep_working_width_and_complete_material_rule(self):
        trades=[]
        for p in self.spaces:
            require_material_rule(p.blocks,p.owner)
            trades.append(frozenset(p.main[p.owner]))
            for r in p.routes:
                self.assertGreaterEqual(len(r['positions']),6)
                for x,y,z in r['positions']:
                    self.assertEqual(p.blocks.get((x,y,z),'minecraft:air'),'minecraft:air')
                    self.assertEqual(p.blocks.get((x,y+1,z),'minecraft:air'),'minecraft:air')
            # Signs alone carry authored text: no stocked Items, fake craft
            # receipt, ownership or actor/entity NBT is introduced.
            self.assertTrue(all(key(p.blocks[q]).endswith('_wall_sign')for q in p.tags))
            self.assertFalse(any('Items:'in s or'Owner:'in s for s in p.tags.values()))
        self.assertEqual(len(set(trades)),3)
        all_ids={key(s)for p in self.spaces for s in p.blocks.values()}
        self.assertTrue({'minecraft:loom','minecraft:water_cauldron','minecraft:grindstone',
                         'chipped:roped_ladder','farmersdelight:cutting_board'}<=all_ids)

    def test_real_sign_ladder_backings_and_task_light_mounts(self):
        offset={'north':(0,-1),'south':(0,1),'west':(-1,0),'east':(1,0)}
        for p in self.spaces:
            for (x,y,z),state in p.blocks.items():
                name=key(state)
                if name.endswith('_wall_sign')or name=='chipped:roped_ladder':
                    dx,dz=offset[properties(state)['facing']]
                    self.assertNotEqual(p.blocks.get((x-dx,y,z-dz),'minecraft:air'),'minecraft:air')
                if name=='minecraft:lantern':
                    self.assertEqual(properties(state)['hanging'],'true')
                    self.assertTrue(key(p.blocks.get((x,y+1,z),'' )).endswith('_planks'))


if __name__=='__main__':unittest.main()
