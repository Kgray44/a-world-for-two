"""Western station regressions; numeric pinned-API excerpts, no private world."""
from pathlib import Path
import json
from unittest import TestCase
from unittest.mock import patch

from control_room.common import UserError
from tools.artistic_zipline_catenary import swept_cells, validate_nodes
from tools.artistic_zipline_west import HANG, NODES, STOCK, occupied_cells, pavilion, station_connections


def canonical(registry,name,**props):
    # Fixture geometry only. Real cached native schema validation is separate.
    return name+('['+','.join(k+'='+str(v).lower() for k,v in sorted(props.items()))+']' if props else '')


class Terrain:
    def __init__(self,ground=63,overrides=None):
        self.ground=ground;self.overrides=overrides or {};self.entities=set()

    def column(self,x,z):
        return {'kind':'dry','x':x,'z':z,'surface_y':self.ground,'state':'minecraft:grass_block'}

    def state(self,x,y,z):
        return self.overrides.get((x,y,z),'minecraft:air' if y>self.ground else 'minecraft:grass_block' if y==self.ground else 'minecraft:stone')


class WesternStationContracts(TestCase):
    def build(self,label):
        center=(1160,-760) if label=='cliff' else (1100,-1256)
        floor=160 if label=='cliff' else 64
        with patch('tools.artistic_zipline_west.state',side_effect=canonical):
            return pavilion({},Terrain(floor-1),center,set(),label,anchor_xz=center,floor_y=floor)

    def test_new_station_route_is_westward_with_exact_native_contract(self):
        self.assertEqual(NODES[-1],(1100,72,-1256));self.assertNotIn((1220,72,-1272),NODES)
        self.assertEqual(STOCK,(1101,65,-1257));self.assertEqual(HANG,3.5)
        self.assertTrue(all(angle<45 for angle in validate_nodes(NODES)[1]))

    def test_actual_numeric_curve_excerpts_clear_the_complete_station_occupancy(self):
        fixture=json.loads((Path(__file__).parent/'fixtures/zipline_v2_station_curve_points.json').read_text())
        self.assertIn('not a current-world',fixture['meaning'])
        for label,row in zip(('cliff','western-town'),fixture['segments']):
            blocks,_,_,_,roles=self.build(label)
            self.assertFalse(swept_cells(row['points'],HANG)&occupied_cells(blocks))
            self.assertFalse(roles['source_support_connectivity']['native_support_survival_shapes_and_engineering_acceptance'])

    def test_old_front_post_is_not_silently_kept_in_the_flight(self):
        blocks,_,_,_,_=self.build('cliff')
        self.assertNotIn((1162,165,-762),blocks)
        self.assertIn((1162,165,-758),blocks)

    def test_cliff_keeps_the_neighbouring_native_canopy_outside_its_sparse_targets(self):
        leaves={(1158,168,-759):'minecraft:dark_oak_leaves[distance=6,persistent=false]',
                (1163,160,-761):'minecraft:spruce_leaves[distance=1,persistent=false]'}
        with patch('tools.artistic_zipline_west.state',side_effect=canonical):
            blocks,_,_,_,_=pavilion({},Terrain(159,leaves),(1160,-760),set(),'cliff',floor_y=160)
        self.assertFalse(leaves.keys()&blocks.keys())

    def test_ridge_beam_and_kingposts_prevent_the_prior_floating_ridge(self):
        blocks,_,roots,_,_=self.build('western-town')
        self.assertEqual(station_connections(blocks,roots,'fixture')['ridge_has_actual_ridgebeam_and_kingposts'],True)
        broken={q:v for q,v in blocks.items() if not(q[0]==1100 and q[1]in(74,75))}
        with self.assertRaises(UserError):station_connections(broken,roots,'broken ridge')

    def test_native_fences_reserve_the_extra_collision_height(self):
        cells=occupied_cells({(1,2,3):'minecraft:spruce_fence[north=false]',(7,8,9):'minecraft:air'})
        self.assertEqual(cells,{(1,2,3),(1,3,3)})

    def test_current_BE_or_foreign_object_is_not_a_station_target_exception(self):
        t=Terrain();t.entities.add((1100,64,-1256))
        with patch('tools.artistic_zipline_west.state',side_effect=canonical):
            with self.assertRaises(UserError):pavilion({},t,(1100,-1256),set(),'western-town',floor_y=64)
