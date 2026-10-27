import copy
import json
from pathlib import Path
import unittest

from control_room.common import UserError
from tools.artistic_craft_lane import construct, check, CraftPlan


class CraftLaneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures=Path(__file__).parent/'fixtures'
        cls.registry=json.loads((fixtures/'artistic_street_registry.json').read_text())
        cls.survey=json.loads((fixtures/'artistic_craft_terrain.json').read_text())
        cls.d=construct(cls.registry,cls.survey,[])

    def test_furnished_rooms_materials_beds_and_connected_lane(self):
        checks=check(self.d)
        self.assertEqual(6,len(checks['materials']))
        self.assertEqual(12,len(checks['furnished_room_access']))
        self.assertEqual(5,checks['complete_beds'])
        self.assertTrue(checks['all_authored_outdoor_runs_at_most_nine'])
        path=checks['continuous_cottage_to_bascule_path']['local_floor_path']
        self.assertEqual([52,-1,24],path[-1])
        self.assertTrue(any('immersive_melodies:lute' in tag for tag in self.d.p.tags.values()))

    def test_bridge_air_is_an_absolute_exclusion(self):
        plan={'world_path':self.registry['world_path'],'seed':self.registry['seed'],
              'palette':['minecraft:air'],'blocks':[[1188,68,-1094,0]]}
        p=CraftPlan(self.registry,self.survey,[('bascule',plan,'a'*64)])
        with self.assertRaisesRegex(UserError,'existing bascule'):
            p.put(52,1,24,'minecraft:air')

    def test_connector_can_replace_only_the_exact_authorized_cottage_air(self):
        plan={'world_path':self.registry['world_path'],'seed':self.registry['seed'],
              'palette':['minecraft:air'],'blocks':[[1130,67,-1094,0]]}
        p=CraftPlan(self.registry,self.survey,[('cottage',plan,'b'*64)])
        p.put(-6,0,24,'minecraft:gravel')
        self.assertEqual({(1130,67,-1094)},p.connector_overrides)
        plan['palette']=['minecraft:stone']
        p=CraftPlan(self.registry,self.survey,[('cottage',plan,'c'*64)])
        with self.assertRaisesRegex(UserError,'existing cottage'):
            p.put(-6,0,24,'minecraft:gravel')

    def test_confirmed_water_is_not_interpolated_into_dry_land(self):
        survey=copy.deepcopy(self.survey)
        survey['samples'].append({'x':1138,'z':-1109,'y':63,'ground_y':60,'block':'minecraft:water','fluid':True})
        with self.assertRaisesRegex(UserError,'water sample'):
            construct(self.registry,survey,[])


if __name__=='__main__':
    unittest.main()
