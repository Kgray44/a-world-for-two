"""Pure small station/straight-reference safety tests; no chain or game APIs."""
from unittest import TestCase
from tools.artistic_zipline_geography import station_site,straight_corridor,growth_reservation
from tools.artistic_whole_bank_forest import CHECKPOINT_SHA


class Ground:
    def __init__(self,changes=None,states=None):self.changes=changes or {};self.states=states or {};self.entities=set()
    def column(self,x,z):return {'x':x,'z':z,'kind':'dry','surface_y':63,'state':'minecraft:grass_block','visible':[63,'minecraft:grass_block']}|self.changes.get((x,z),{})
    def state(self,x,y,z):return self.states.get((x,y,z),'minecraft:air')


class ZiplineGeographyContracts(TestCase):
    def test_station_is_actual_dry_compact_support_and_twelve_high(self):
        site=station_site(Ground(),(0,0),set())
        self.assertEqual(site['bounds'],[-1,-2,1,2]);self.assertEqual(site['proposed_floor_y'],64)
        self.assertEqual(len(site['exact_saved_support_and_clearance']),15)
        self.assertTrue(all(len(r['floor_and_twelve_high_states'])==12 for r in site['exact_saved_support_and_clearance']))

    def test_water_tree_native_unknown_or_protected_plot_refuses(self):
        for terrain,protected in ((Ground({(1,0):{'kind':'water'}}),set()),(Ground({(0,0):{'kind':'unknown'}}),set()),(Ground(states={(0,70,0):'minecraft:spruce_leaves[distance=1,persistent=false]'}),set()),(Ground(),{(0,1)})):
            self.assertIsNone(station_site(terrain,(0,0),protected))

    def test_station_does_not_hide_a_saved_inventory(self):
        terrain=Ground();terrain.entities.add((1,63,0))
        self.assertIsNone(station_site(terrain,(0,0),set()))

    def test_real_roof_or_canopy_is_a_straight_reference_blocker(self):
        result=straight_corridor(Ground({(2,0):{'visible':[75,'minecraft:oak_leaves']}}),(0,72,0),(4,72,0))
        self.assertFalse(result['source_clear_straight_reference']);self.assertGreater(result['blocked_columns'],0)
        self.assertFalse(result['provider_length_sag_player_AABB_native_acceptance'])

    def test_unknown_corridor_never_becomes_clear(self):
        result=straight_corridor(Ground({(2,0):{'kind':'unknown'}}),(0,72,0),(4,72,0))
        self.assertFalse(result['source_clear_straight_reference']);self.assertEqual(result['unknown_columns'],1)

    def test_clear_reference_is_explicitly_not_native_chain_acceptance(self):
        result=straight_corridor(Ground(),(0,72,0),(4,72,0))
        self.assertTrue(result['source_clear_straight_reference']);self.assertFalse(result['provider_length_sag_player_AABB_native_acceptance'])

    def test_growth_mask_rejects_unbound_or_obstructed_source(self):
        with self.assertRaisesRegex(Exception,'Exact saved'):growth_reservation({},0,0)

    def test_future_corridor_is_an_explicit_keepout_not_fake_air_or_cable_proof(self):
        site=station_site(Ground(),(0,0),set());other=station_site(Ground(),(8,0),set())
        proof=straight_corridor(Ground(),(0,72,0),(8,72,0))
        data={'format':'awft-saved-zipline-geography:1','checkpoint_sha256':CHECKPOINT_SHA,
              'launch_candidates_highest_qualified_footprint_first':[site],
              'town_dry_landing_candidates':[other],
              'straight_reference_pairs':[{'launch_index':0,'landing_index':0,'reference_anchors':[[0,72,0],[8,72,0]],'reference_corridor':proof}]}
        result=growth_reservation(data,0,0)
        self.assertFalse(result['native_plan']);self.assertFalse(result['growth_authority'])
        self.assertNotIn('blocks',result);self.assertNotIn('palette',result)
        self.assertIn([0,0],result['all_growth_excluded_columns_xz'])
        self.assertIn([4,9],result['all_growth_excluded_columns_xz'])
        proof['source_clear_straight_reference']=False
        with self.assertRaisesRegex(Exception,'obstructed'):growth_reservation(data,0,0)
