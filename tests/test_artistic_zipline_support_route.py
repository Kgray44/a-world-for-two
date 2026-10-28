"""Small conservative source-screen contracts; no native cable acceptance."""
from unittest import TestCase
from tools.artistic_zipline_support_route import reference_clear,turn_ok


class Ground:
    def __init__(self,height=63,kind='dry'):self.height=height;self.kind=kind
    def column(self,x,z):return {'x':x,'z':z,'kind':self.kind,'surface_y':self.height,'visible':[self.height,'minecraft:stone']}


class SupportContracts(TestCase):
    def test_sea_level_navigation_clearance_is_not_silently_relaxed(self):
        refusal={};self.assertIsNone(reference_clear(Ground(62,'water'),(0,80,0),(8,80,0),refusal))
        self.assertIn('26m navigation',refusal['reason']);self.assertFalse(refusal['actual_native_curve_failure'])
        self.assertIsNotNone(reference_clear(Ground(62,'water'),(0,90,0),(8,90,0)))

    def test_highland_stream_retains_player_screen_but_is_not_ship_channel(self):
        result=reference_clear(Ground(139,'water'),(0,150,0),(8,150,0))
        self.assertIsNotNone(result);self.assertIsNone(result['straight_minimum_water_clearance'])
        self.assertFalse(result['exact_native_catenary_player_and_vessel_acceptance'])
        self.assertIsNone(reference_clear(Ground(139,'water'),(0,143,0),(8,143,0)))

    def test_unknowns_and_roofs_remain_refusals_not_provider_failures(self):
        for terrain in (Ground(63,'unknown'),Ground(77)):
            refusal={};self.assertIsNone(reference_clear(terrain,(0,80,0),(8,80,0),refusal))
            self.assertFalse(refusal['actual_native_curve_failure'])

    def test_turn_requires_real_nonzero_vectors_and_less_than45degrees(self):
        self.assertTrue(turn_ok((0,0,0),(1,0,0),(2,0,0)))
        self.assertFalse(turn_ok((0,0,0),(1,0,0),(1,0,1)))
        self.assertFalse(turn_ok((0,0,0),(0,0,0),(1,0,0)))
