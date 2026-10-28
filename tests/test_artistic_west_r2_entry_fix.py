import json
from pathlib import Path
import unittest
from tools.artistic_west_r2_entry_fix import corrections
from tools.artistic_west_r2_frontage import construct,LABELS,key
from tools.artistic_west_r2_refine import construct as photo_construct,check


class WestEntryCorrectionTests(unittest.TestCase):
    def setUp(self):
        folder=Path(__file__).parent/'fixtures'
        a=json.loads((folder/'west_r2_refine_registry.json').read_text())
        b=json.loads((folder/'salt_petal_registry.json').read_text())
        self.reg={'blocks':{**a['blocks'],**b['blocks']}}

    def test_all_three_declared_entries_have_real_native_halves_after_sparse_fix(self):
        p=construct(self.reg);feet,doors=corrections(self.reg)
        self.assertEqual((len(feet),len(doors)),(2,4))
        world={tuple(q[i]+p.origin[i]for i in range(3)):s for q,s in p.blocks.items()}
        self.assertTrue(all(world[q]=='minecraft:air'for q in feet|doors))
        world.update(doors)
        for entry in p.entries:
            x,y,z=(entry['door'][i]+p.origin[i]for i in range(3))
            self.assertTrue(key(world[x,y,z]).endswith('_door'))
            self.assertTrue(key(world[x,y+1,z]).endswith('_door'))
            self.assertIn('half=lower',world[x,y,z]);self.assertIn('half=upper',world[x,y+1,z])

    def test_complete_photo_plus_entry_and_feet_keeps_rule_and_routes(self):
        d=photo_construct(self.reg);feet,doors=corrections(self.reg);d.blocks.update(feet|doors)
        d.owners.update({q:LABELS[0]for q in feet})
        d.owners.update({q:LABELS[0]if q[0]==1077 else LABELS[1]for q in doors})
        self.assertEqual(check(d)['existing_BE_or_inventory_targets'],0)
        for q in feet:
            self.assertEqual(key(d.blocks[q]),'minecraft:stone_bricks')
            self.assertNotEqual(d.original[q[0],q[1]-1,q[2]],'minecraft:air')


if __name__=='__main__':unittest.main()
