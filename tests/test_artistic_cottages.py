import copy
import json
from pathlib import Path
import unittest

from control_room.common import UserError
from tools.artistic_cottages import construct, check


class CottageCourtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).parent/'fixtures'
        cls.registry = json.loads((root/'artistic_street_registry.json').read_text())
        cls.survey = json.loads((root/'artistic_cottage_terrain.json').read_text())
        cls.p = construct(cls.registry, cls.survey)

    def test_complete_buildings_paths_and_actual_doors_are_retained(self):
        result = check(self.p)
        self.assertEqual(4, len(result['materials']))
        self.assertEqual([], result['blocked'])
        self.assertEqual(6, len(self.p.rooms))
        for lot in self.p.lots:
            x, y, z = lot['door']
            self.assertTrue(self.p.blocks[x, y+1, z].startswith('mcwdoors:'))
            self.assertTrue(self.p.blocks[x, y+2, z].startswith('mcwdoors:'))

    def test_west_path_is_two_wide_across_its_direction(self):
        route = next(row for row in self.p.routes if row['id'] == 'west-garden-entry')
        cells = {(int(x), int(z)) for x, y, z in route['local_player_feet']}
        for x in range(2, 9):
            self.assertIn((x, 20), cells)
            self.assertIn((x, 21), cells)
        # Ground outside the intended paths, homes and pond is not paved into a
        # flat plane; only a vegetation-clearance prism is described there.
        self.assertIsNone(self.p.blocks.get((40, self.p.terrain[40, 3], 3)))

    def test_unknown_water_or_large_slope_refuses_instead_of_flattening(self):
        for key, value in (('fluid', True), ('y', 90)):
            survey = copy.deepcopy(self.survey)
            for row in survey['samples']:
                row[key] = value
            with self.assertRaises(UserError):
                construct(self.registry, survey)


if __name__ == '__main__':
    unittest.main()
