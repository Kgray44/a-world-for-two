"""Dry west entrance retains actual trades/furnishings and physical support."""
from collections import Counter
import json
from pathlib import Path
import unittest
from tools.artistic_tortuga_west_ground import workspaces,key
from tools.artistic_tortuga_west_ground_r2 import revised_workspaces,UNSAFE_SIX
from tools.artistic_materials import require_material_rule


class TortugaGroundR2Tests(unittest.TestCase):
    def setUp(self):
        self.registry=json.loads((Path(__file__).parent/'fixtures/tortuga_west_ground_registry.json').read_text())

    def test_dry_entry_keeps_all_original_workstations_containers_and_plants(self):
        old=workspaces(self.registry);new=revised_workspaces(self.registry)
        for a,b in zip(old,new):
            self.assertEqual(a.main,b.main)
            for name in('minecraft:barrel','minecraft:water_cauldron','minecraft:grindstone','minecraft:loom','minecraft:crafting_table','minecraft:dark_oak_trapdoor','fishofthieves:potted_tropical_red_fern'):
                self.assertEqual(Counter(map(key,a.blocks.values()))[name],Counter(map(key,b.blocks.values()))[name],name)
            self.assertEqual(a.tags,b.tags)
            require_material_rule(b.blocks,b.owner)
        fish=new[0]
        self.assertEqual(fish.blocks[0,2,2],'minecraft:air')
        self.assertEqual(fish.blocks[0,1,3],'minecraft:air')
        self.assertTrue(key(fish.blocks[0,3,2]).endswith('_trapdoor'))
        self.assertEqual(fish.blocks[0,2,1],'fishofthieves:potted_tropical_red_fern')
        self.assertEqual(fish.blocks[0,1,1],'minecraft:dark_oak_planks')

    def test_actual_west_passage_is_clear_without_removing_waiting_bench(self):
        fish=revised_workspaces(self.registry)[0]
        for x in(0,1,2):
            self.assertTrue(all(fish.blocks.get((x,y,2),'minecraft:air')=='minecraft:air'for y in(1,2)))
        self.assertEqual(key(fish.blocks[1,1,3]),'handcrafted:dark_oak_bench')
        # This explicit planned small link is above a DIFFERENT cut. It cannot
        # be a hidden replacement of any six failed native ground targets.
        self.assertFalse({(x,z)for x in range(1003,1013)for z in(-1281,-1280)}&UNSAFE_SIX)


if __name__=='__main__':unittest.main()
