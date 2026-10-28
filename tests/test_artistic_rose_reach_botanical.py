"""Source admission regressions, never native survival/visual acceptance."""
import json
from pathlib import Path
import unittest

from control_room.common import UserError
from tools import artistic_rose_reach_botanical as art

REGISTRY=json.loads((Path(__file__).parent/'fixtures/rose_reach_botanical_registry.json').read_text())


class Field:
    def __init__(self):self.entities=set();self.changed={}
    def state(self,x,y,z):return self.changed.get((x,y,z),'minecraft:grass_block[snowy=false]' if y==63 else 'minecraft:air')


class RosePilotChecks(unittest.TestCase):
    def test_two_wide_return_has_real_floor_and_records_true_grass_preimages(self):
        field=Field();field.changed[1285,64,-1246]='minecraft:short_grass'
        delta,before,retained,paths=art.pave_saved_routes(field,set(),{})
        self.assertEqual(before[1285,64,-1246],'minecraft:short_grass')
        self.assertEqual(delta[1285,64,-1246],'minecraft:air')
        self.assertTrue(all(row['width']==2 for row in paths))
        for row in paths:
            for x,z in art.columns(row['centres_xz']):
                self.assertIn((x,63,z),delta|retained)
                self.assertEqual((delta|retained)[x,64,z],'minecraft:air')
                self.assertEqual((delta|retained)[x,65,z],'minecraft:air')
        # The retained fern stand at1292,-1245 is deliberately outside the turn.
        self.assertNotIn((1292,-1245),art.columns(art.SIDE_CENTRES))

    def test_player_object_water_and_authored_soil_cannot_be_overwritten(self):
        for changed in ('minecraft:barrel[facing=north,open=false]','minecraft:water[level=0]'):
            field=Field();field.changed[1285,64,-1246]=changed
            with self.assertRaises(UserError):art.pave_saved_routes(field,set(),{})
        field=Field();field.entities.add((1285,63,-1246))
        with self.assertRaises(UserError):art.pave_saved_routes(field,set(),{})
        field=Field()
        with self.assertRaises(UserError):art.pave_saved_routes(field,set(),{(1285,63,-1246):'minecraft:grass_block[snowy=false]'})

    def test_preservation_snapshot_does_not_accept_changed_identity_or_orientation(self):
        q=(1300,79,-1249);old={q:'mcwroofs:dark_oak_roof[facing=west,half=bottom,shape=straight]'}
        notes=art.audited_owner({q:'mcwroofs:dark_oak_roof[facing=west,half=bottom,shape=outer_left]'},old)
        self.assertIn('not a canonical acceptance',notes[0]['kind'])
        with self.assertRaises(UserError):art.audited_owner({q:'mcwroofs:dark_oak_roof[facing=east,half=bottom,shape=outer_left]'},old)
        with self.assertRaises(UserError):art.audited_owner({q:'minecraft:gold_block'},old)

    def test_only_exact_authorized_real_bed_is_retained(self):
        q=(1296,65,-1250)
        self.assertEqual(len(art.audited_owner({q:art.BED[q]},{q:'minecraft:air'})),1)
        with self.assertRaises(UserError):art.audited_owner({q:'minecraft:red_bed[facing=north,occupied=false,part=head]'},{q:'minecraft:air'})

    def test_double_grass_clearance_is_explicit_and_does_not_fake_air(self):
        low=(1284,64,-1246);high=(1284,65,-1246)
        raw={low:'minecraft:tall_grass[half=lower]',high:'minecraft:tall_grass[half=upper]'}
        g=art.RoseGarden(REGISTRY,raw.get,set(),set(),set())
        g.put(art.STREET,low,'regions_unexplored:aster');g.complete_double_cover()
        self.assertEqual(g.previous,raw)
        self.assertEqual(g.blocks[high],'minecraft:air')
        with self.assertRaises(UserError):art.RoseGarden(REGISTRY,raw.get,set(),{low},set()).put(art.STREET,low,'regions_unexplored:aster')

    def test_full_packed_mud_support_is_distinct_from_low_mud_or_a_be(self):
        q=(1283,64,-1247)
        g=art.RoseGarden(REGISTRY,lambda p:'minecraft:packed_mud',set(),set(),set())
        self.assertEqual(g.root(q),'minecraft:packed_mud')
        for value,bes in [('minecraft:mud',set()),('minecraft:packed_mud',{q})]:
            g=art.RoseGarden(REGISTRY,lambda p:value,bes,set(),set())
            with self.assertRaises(UserError):g.root(q)


if __name__=='__main__':unittest.main()
