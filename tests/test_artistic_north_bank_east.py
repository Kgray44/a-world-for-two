"""Static geometry/admission fixtures; not native/render/owner acceptance."""
from pathlib import Path
import json
import unittest

from control_room.common import UserError
from tools.artistic_north_bank_east import (EAST_STUDY,ROSE_REACH,EastPlan,authored_rose_reach,
    dry_footprint,check_quarter,outline)


class Surface:
    def __init__(self,rows,entities=()):self.rows=rows;self.entities=set(entities)
    def column(self,x,z):return self.rows.get((x,z),{'kind':'unknown'})


class GroundAdmission(unittest.TestCase):
    def setUp(self):self.row={'kind':'dry','surface_y':63,'state':'minecraft:grass_block'}
    def test_every_main_column_must_be_dry_not_coarse_interpolated(self):
        terrain=Surface({(1,1):self.row,(2,1):{'kind':'water','surface_y':63,'state':'minecraft:water[level=0]'}})
        with self.assertRaises(UserError):dry_footprint(terrain,{(1,1),(2,1)})
    def test_unknown_full_gap_never_becomes_land(self):
        with self.assertRaises(UserError):dry_footprint(Surface({(1,1):self.row}),{(1,1),(2,1)})
    def test_source_air_and_model_column_is_preserved(self):
        with self.assertRaises(UserError):dry_footprint(Surface({(1,1):self.row}),{(1,1)},{(1,1)})
    def test_be_in_the_real_foundation_body_is_preserved(self):
        with self.assertRaises(UserError):dry_footprint(Surface({(1,1):self.row},[(1,62,1)]),{(1,1)})
    def test_deep_unmodified_be_is_not_reloaded_or_dug_to(self):
        proof=dry_footprint(Surface({(1,1):self.row},[(1,-20,1)]),{(1,1)})
        self.assertEqual(proof['support_y_range'],[63,63])
    def test_large_relief_requires_a_deliberate_different_plot(self):
        with self.assertRaises(UserError):dry_footprint(Surface({(1,1):self.row,(2,1):dict(self.row,surface_y=68)}),{(1,1),(2,1)})


class QuarterGeometry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=json.loads((Path(__file__).parent/'fixtures/artistic_north_bank_east_registry.json').read_text())
        x0,z0,x1,z1=EAST_STUDY
        cls.fine={'samples':[{'x':x,'z':z,'kind':'dry','surface_y':63,'state':'minecraft:grass_block'} for x in range(x0,x1+1) for z in range(z0,z1+1)],'protected_columns_xz':[],'saved_BEs':[]}
        cls.plan=authored_rose_reach(cls.registry,cls.fine)
    def test_seven_authored_outlines_and_distinct_homes(self):
        self.assertEqual(len(self.plan.lots),7);self.assertEqual(len({q.name for q in ROSE_REACH}),7)
        self.assertEqual(len({(q.outline,q.roof,q.finish) for q in ROSE_REACH}),7)
    def test_complete_material_and_body_routes(self):
        check=check_quarter(self.plan);self.assertEqual(check['fully_furnished_rooms'],19);self.assertTrue(check['outdoor_nine_cap'])
    def test_decoration_is_real_and_rooms_are_not_empty(self):
        self.assertGreaterEqual(len(self.plan.fixtures),300)
        self.assertGreaterEqual(min(q['furnishing_objects'] for q in self.plan.rooms),12)
        self.assertTrue(any(s.startswith('mythrais:roof_low_straight_67_') for s in self.plan.blocks.values()))
        self.assertTrue(any(s.startswith('dawnoftimebuilder:spruce_support_slab') for s in self.plan.blocks.values()))
    def test_unsupported_fixture_is_rejected(self):
        p=EastPlan(self.registry,self.fine)
        with self.assertRaises(UserError):p.fixture((1320,66,-1241),'handcrafted:wood_cup',support=(1320,65,-1241),facing='east',pieces=1,waterlogged=False)
    def test_a_fixture_cannot_quietly_overwrite_stair_headroom(self):
        p=EastPlan(self.registry,self.fine);p.walk.append((1320,65,-1241))
        with self.assertRaises(UserError):p.fixture((1320,65,-1241),'handcrafted:wood_cup',facing='east',pieces=1,waterlogged=False)
    def test_foundations_do_not_include_a_deep_be(self):
        self.assertGreaterEqual(min(q[1] for q in self.plan.blocks),62)


if __name__=='__main__':unittest.main()
