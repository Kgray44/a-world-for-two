import copy
import json
from pathlib import Path
import unittest

from control_room.common import UserError
from tools.artistic_craft_details import construct,check


class CraftDetailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        f=Path(__file__).parent/'fixtures'
        cls.d=construct(json.loads((f/'artistic_street_registry.json').read_text()),json.loads((f/'artistic_craft_terrain.json').read_text()),[])

    def test_small_detail_preserves_furniture_inventory_and_all_routes(self):
        result,changed=check(self.d)
        self.assertEqual(6,len(result['materials']))
        self.assertEqual(12,len(result['furnished_room_access']))
        self.assertEqual(5,result['complete_beds'])
        self.assertFalse(changed & self.d.protected)
        for p,tag in self.d.base.tags.items():self.assertEqual(tag,self.d.p.tags[p])
        self.assertTrue(any('leather_boots' in tag for p,tag in self.d.p.tags.items() if p not in self.d.base.tags))

    def test_a_seat_in_the_road_is_rejected(self):
        d=copy.deepcopy(self.d);d.p.blocks[1,1,22]='handcrafted:spruce_bench'
        with self.assertRaisesRegex(UserError,'body route'):check(d)


if __name__=='__main__':unittest.main()
