"""Original two-level room fixtures; no saved room or inventory arrays."""
from pathlib import Path
import json,unittest
from tools import artistic_eastern_compound_sprint as e
from tools import artistic_eastern_height_clearance as height


class EasternHeightClearanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.registry=json.loads((Path(__file__).parent/'fixtures/eastern_compound_registry.json').read_text())

    def make(self):
        cells=e.rectangle(0,0,11,14);spec={'id':'synthetic-stepped-loft','name':'Synthetic stepped workshop loft','program':'archive','masses':[{'bounds_xz':[0,0,11,14],'floor_y':64,'storeys':2,'occupied_floor_offsets':[0,5],'roof':'weathered hipped clay'}],'actual_building_floor_columns_xz':[list(q)for q in sorted(cells)]}
        fixed={(3,69,4):'minecraft:barrel[facing=up,open=false]',(8,70,9):'minecraft:cartography_table'}
        stock={'fixed':fixed,'bes':{(3,69,4)},'retire':{},'moves':[]};zone={'mass':0,'level':4,'cells':e.rectangle(2,3,5,6),'room_id':'synthetic-lower-room'}
        p=height.build(self.registry,spec,stock,set(),{(x,-2)for x in range(12)},0,[zone]);e.validate(p);return p,fixed,zone

    def test_native_stock_and_lower_room_height_remain_literal_beside_real_raised_gallery(self):
        p,fixed,zone=self.make()
        self.assertTrue(all(p.blocks[p.local(q)]==v for q,v in fixed.items()))
        self.assertEqual(p.declared[3,4],[0,4]);self.assertEqual(p.declared[8,9],[0,5])
        self.assertTrue(any(r['kind']=='native ordinary stair'and r['risers']==1 for r in p.vertical))
        self.assertTrue(any(r['kind']=='native ordinary stair'and r['risers']==5 for r in p.vertical))
        self.assertFalse(set(p.tags)&set(p.fixed))

    def test_floor_graph_cannot_invent_gallery_landing_on_top_of_lower_room_barrel(self):
        p,_,_=self.make();graph=e.walking_graph(p)
        self.assertNotIn((3,6,4),graph)
        self.assertTrue(any(q[1]==5 for q in graph))
        self.assertTrue(any(q[1]==6 for q in graph))
        self.assertTrue(p.circulation['reserved_supported_feet'])

    def test_internal_lower_zone_does_not_fill_the_facade_mullions_with_glass(self):
        p,_,_=self.make()
        # These are the actual two six-pane bands from the failed fixture,
        # on perpendicular faces at the raised gallery's window height.
        for line in ([(x,6,14)for x in range(1,7)],[(0,6,z)for z in range(6,12)]):
            self.assertFalse(all(e.key(p.blocks[q])=='mcwwindows:dark_oak_four_window'for q in line))
            self.assertTrue(any(e.key(p.blocks[q])=='minecraft:stripped_dark_oak_log'for q in line))
        # The retained lower room is internal; its floor4 is not a second
        # exterior level running across the raised floor5 facade.
        self.assertFalse(any(row['floor']==4 for row in p.endwall_relief))


if __name__=='__main__':unittest.main()
