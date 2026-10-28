"""Occupied architecture and actual retained clearances, not beauty scores."""
import json
from pathlib import Path
import unittest
from control_room.common import UserError
from tools.artistic_tortuga_frontages import RECIPES,check,key,AIR
from tools.artistic_tortuga_headland_pair import construct


class TortugaFrontagesTests(unittest.TestCase):
    def setUp(self):
        self.registry=json.loads((Path(__file__).parent/'fixtures/tortuga_frontages_registry.json').read_text())

    def test_thirteen_actual_individual_recipes_have_occupied_scenes_and_real_volume(self):
        outlines=[];directions=set();rooms=0;highest=set()
        for name,fn in RECIPES.items():
            p=fn(self.registry);proof=check(p)
            self.assertGreaterEqual(proof['surviving_purposeful_objects'],60,name)
            self.assertEqual(proof['material']['violations'],[])
            outlines.append(frozenset(p.main[p.owner]));directions|={r['outward']for r in p.entries}
            rooms+=len(p.rooms);highest.add(max(q[1]for q,s in p.blocks.items()if s!=AIR))
            self.assertTrue(any('occupied' in r.get('role','')or'oriel' in r.get('role','')for r in p.props),name)
            roofs={key(s)for s in p.blocks.values()if key(s).startswith('mcwroofs:')}
            self.assertTrue(all(any(k.startswith('mcwroofs:'+f+'_')for f in('dark_oak','spruce','deepslate'))for k in roofs))
            self.assertTrue(all(key(p.blocks[q]).endswith('_wall_sign')for q in p.tags))
            self.assertFalse(any('Items:'in nbt or'Owner:'in nbt for nbt in p.tags.values()))
        self.assertEqual(len(set(outlines)),13)
        self.assertEqual(directions,{'north','south','east','west'})
        self.assertEqual(rooms,29)
        self.assertGreaterEqual(len(highest),3)

    def test_doors_cannot_be_cleared_by_a_later_room_reservation(self):
        p=RECIPES['gullwatch'](self.registry);q=tuple(p.entries[0]['door']);p.blocks[q]=AIR
        with self.assertRaisesRegex(UserError,'door halves'):check(p)

    def test_real_route_blockage_and_unmounted_task_light_refuse(self):
        p=RECIPES['tideglass'](self.registry);p.blocks[4,1,6]='minecraft:barrel[facing=up,open=false]'
        with self.assertRaisesRegex(UserError,'walking passage obstructed'):check(p)
        p=RECIPES['tideglass'](self.registry)
        row=next(r for r in p.supports if'lantern'in r['role']);p.blocks[tuple(row['support'])]=AIR
        with self.assertRaisesRegex(UserError,'actual authored support'):check(p)

    def test_furniture_cannot_silently_replace_the_house_wall(self):
        p=RECIPES['gullwatch'](self.registry);p.blocks[6,5,5]='handcrafted:dark_oak_desk[color=brown,facing=south,waterlogged=false]'
        with self.assertRaisesRegex(UserError,'shell wall with floor furniture'):check(p)

    def test_two_different_headland_frontages_keep_real_two_wide_lane(self):
        states,_,buildings,main,lane=construct(self.registry)
        self.assertEqual(len(buildings),2);self.assertNotEqual(buildings[0]['proof']['main_columns'],buildings[1]['proof']['main_columns'])
        self.assertFalse(main&lane)
        for x,z in lane:
            self.assertNotEqual(states[x,63,z],AIR)
            self.assertTrue(all(states.get((x,y,z),AIR)==AIR for y in(64,65)))
        # The smaller shop's cheeks remain inside its own body; an upper
        # projecting casement must not turn into a low lane obstruction.
        for z in range(-1307,-1301):
            for x in(1044,1045):self.assertTrue(all(states.get((x,y,z),AIR)==AIR for y in(64,65)))


if __name__=='__main__':unittest.main()
