import json
from pathlib import Path
import unittest

from tools.artistic_materials import material_runs
from tools.artistic_street import designs
from tools.artistic_street_surfaces import construct


class OutdoorStreetRunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d, cls.changes, cls.checks = construct(json.loads((Path(__file__).parent/'fixtures'/'artistic_street_registry.json').read_text()))

    def test_complete_outdoor_plan_obeys_nine_including_buried_foundations(self):
        self.assertFalse([r for r in material_runs(self.d.p.blocks) if r['exceeds_nine']])
        self.assertTrue(any(p[1] < 0 for p in self.changes))
        self.assertTrue(any(v['purpose'] == 'garden bed division' for v in self.changes.values()))

    def test_every_building_and_existing_inventory_is_preserved(self):
        names = {b.name for b in designs()}
        self.assertFalse(self.changes.keys() & self.d.protected)
        self.assertFalse(any(self.d.base.owners[p] in names for p in self.changes))
        self.assertEqual(self.d.base.tags, self.d.p.tags)
        self.assertEqual(10, len(self.checks['materials']))
        self.assertEqual([], self.checks['planned_clearance']['blocked'])


if __name__ == '__main__':
    unittest.main()
