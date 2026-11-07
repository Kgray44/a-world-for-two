import unittest
from pathlib import Path
from control_room.common import read_json
from tools.artistic_eastern_lived_interiors import finish,AIR


def room():
    source={'name':'Literal prospective test room','origin':[0,0,0],
      'masses':[{'bounds_xz':[0,0,10,15],'floor_y':0,'storeys':1}],
      'routes':[{'feet_local':[[5,1,z]for z in range(1,15)]+[[x,1,7]for x in range(1,10)]}],
      'geometry_proof':{'vertical_routes':[]}}
    base={}
    for x in range(11):
        for z in range(16):
            for y in range(5):base[x,y,z]='minecraft:spruce_planks'if y in(0,4)else'minecraft:stone'if x in(0,10)or z in(0,15)else'minecraft:air'
    base[1,1,2]='minecraft:crafting_table'
    return source,base


class LivedInteriorsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.registry=read_json(Path(__file__).parent/'fixtures/eastern-lived-properties.json')

    def test_real_clusters_preserve_stock_and_literal_three_wide_corridor(self):
        source,base=room();original=dict(base)
        delta,scenes,roles,mounts=finish(self.registry,source,base,'archive')
        self.assertGreater(len(delta),45);self.assertGreaterEqual(len(scenes[0]['clusters']),4)
        self.assertEqual(base,original);self.assertNotIn((1,1,2),delta)
        self.assertTrue(all(base[q]in AIR for q in delta))
        post=base|delta
        self.assertGreaterEqual(scenes[0]['literal_wide_corridor_width'],3)
        self.assertTrue(all(post[tuple(q)]in AIR for q in scenes[0]['literal_wide_corridor_two_high_cells']))
        self.assertTrue(all(post[back]not in AIR for _,back in mounts))
        self.assertTrue(any('book' in v for v in delta.values()))

    def test_different_trades_have_real_different_working_stations(self):
        source,base=room()
        hardware=finish(self.registry,source,base,'hardware')[0]
        galley=finish(self.registry,source,base,'galley')[0]
        self.assertTrue(any(v.startswith('minecraft:smithing_table')for v in hardware.values()))
        self.assertTrue(any(v.startswith('farmersdelight:stove')for v in galley.values()))
        self.assertNotEqual(hardware,galley)

    def test_existing_body_and_station_top_cannot_be_overwritten(self):
        source,base=room();base[1,2,2]='minecraft:potted_fern'
        delta,scenes,_,_=finish(self.registry,source,base,'warehouse',4)
        self.assertNotIn((1,1,2),delta);self.assertNotIn((1,2,2),delta)
        for q in source['routes'][0]['feet_local']:
            self.assertNotIn(tuple(q),delta);self.assertNotIn((q[0],q[1]+1,q[2]),delta)
        post=base|delta
        for scene in scenes:
            for group in scene['clusters']:
                x,y,z=group['visitor_feet']
                self.assertIn(post[x,y,z],AIR);self.assertIn(post[x,y+1,z],AIR)
                self.assertNotIn(post[x,y-1,z],AIR)

    def test_playable_note_instrument_matches_wood_and_has_clear_air_above(self):
        source,base=room();delta,_,_,_=finish(self.registry,source,base,'music',2);post=base|delta
        notes=[q for q,v in delta.items()if v.startswith('minecraft:note_block')]
        self.assertTrue(notes)
        for x,y,z in notes:
            self.assertIn('instrument=bass',post[x,y,z]);self.assertEqual(post[x,y-1,z],'minecraft:spruce_planks')
            self.assertIn(post[x,y+1,z],AIR)
