"""Original stock-pocket and protected-oriel cases, no copied room arrays."""
from pathlib import Path
import json,unittest
from tools import artistic_eastern_compound_sprint as e
from tools import artistic_eastern_keel_adaptation as keel


class KeelAdaptationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.registry=json.loads((Path(__file__).parent/'fixtures/eastern_compound_registry.json').read_text())

    def model(self,stories=1,stock=None,other=()):
        cells=e.rectangle(0,0,10,10);spec={'id':'synthetic-keel','name':'Synthetic divided stock workshop','program':'cooper','masses':[{'bounds_xz':[0,0,10,10],'floor_y':64,'storeys':stories,'roof':'weathered hipped clay'}],'actual_building_floor_columns_xz':[list(q)for q in sorted(cells)]}
        p=e.Compound(self.registry,spec,stock or{'fixed':{},'bes':set(),'retire':{},'moves':[]},set(other),0)
        p.mass_fields=[cells];p.mass_floors=[0];p.floor_levels=[[k*4 for k in range(stories)]];p.top_levels=[stories*4]
        for level in p.floor_levels[0]+p.top_levels:p.floor(cells,level)
        for low in p.floor_levels[0]:p.walls(cells,low+1,low+4,'minecraft:gray_terracotta')
        return p

    def test_new_real_door_reaches_divided_stock_without_deleting_any_conserved_object(self):
        fixed={(5,64+y,z):'minecraft:dark_oak_planks'for y in(1,2)for z in range(11)};fixed[1,65,3]='minecraft:barrel[facing=up,open=false]'
        stock={'fixed':fixed,'bes':{(1,65,3)},'retire':{},'moves':[]};p=self.model(stock=stock)
        p.door(10,1,5,'east');p.reserve('Original workshop entry',[(9,1,5)])
        keel.additional_workshop_entries(p,{(x,-1)for x in range(11)})
        self.assertGreater(len(p.entries),1);_,reachable=keel.reachable(p)
        self.assertTrue(any(q[1]==1 and abs(q[0]-1)+abs(q[2]-3)<=3 for q in reachable))
        self.assertTrue(all(p.blocks[p.local(q)]==v for q,v in fixed.items()))
        self.assertFalse(set(p.tags)&set(p.fixed))

    def test_real_oriel_uses_clear_face_and_preserves_the_protected_rear_skirt(self):
        protected={(x,z)for x in range(-2,13)for z in(11,12)};p=self.model(stories=2,other=protected)
        keel.rear_oriel(p);detail=p.details[-1]
        self.assertEqual(detail['outward'],'east');self.assertEqual(detail['new_ground_columns'],0)
        self.assertTrue(any((x,z)not in p.footprint for x,y,z in p.body))
        self.assertFalse(any((x,z)in protected for x,y,z in p.blocks))
        for x,y,z in p.routes[-1]['feet_local']:self.assertNotIn(e.key(p.blocks.get((x,y-1,z),'minecraft:air')),e.VOID)


if __name__=='__main__':unittest.main()
