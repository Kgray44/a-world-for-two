import json
from pathlib import Path
import unittest

from tools.artistic_cottage_lights import construct


class CottageLightScaleTests(unittest.TestCase):
    def test_compact_fixtures_preserve_exact_supports_furniture_and_inventories(self):
        root=Path(__file__).parent/'fixtures'
        d,changed,checks=construct(json.loads((root/'artistic_street_registry.json').read_text()),
                                   json.loads((root/'artistic_cottage_terrain.json').read_text()))
        self.assertTrue(changed)
        self.assertEqual(d.base.tags,d.p.tags)
        for pos,state in d.p.blocks.items():
            if pos in changed:
                self.assertTrue(d.base.blocks[pos].startswith('mcwlights:copper_small_chandelier'))
                self.assertEqual('minecraft:lantern[hanging=true,waterlogged=false]',state)
            else:
                self.assertEqual(d.base.blocks[pos],state)
        self.assertEqual([],checks['cottage']['blocked'])
        self.assertEqual(4,len(checks['cottage']['materials']))


if __name__=='__main__':
    unittest.main()
