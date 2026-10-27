import json
from pathlib import Path
import unittest

from control_room.common import UserError
from tools.artistic_materials import require_material_rule
from tools.artistic_neighborhood_depth import AIR,DESIGNS,STRUCTURE,check,construct
from tools.settlement_attractions import base,properties


class NeighborhoodDepthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures=Path(__file__).parent/'fixtures'
        registry=json.loads((fixtures/'artistic_street_registry.json').read_text())
        registry['blocks'].update(json.loads((fixtures/'artistic_neighborhood_depth_registry.json').read_text())['blocks'])
        cls.districts=construct(registry,json.loads((fixtures/'artistic_cottage_terrain.json').read_text()),
                               json.loads((fixtures/'artistic_craft_terrain.json').read_text()),[])

    def test_all_twenty_have_distinct_actual_geometric_depth_and_complete_material_checks(self):
        result=check(self.districts)
        self.assertEqual([10,4,6],[result[n]['buildings'] for n in ('signal','court','bramble')])
        signatures=set()
        for design in DESIGNS:
            d=self.districts[design.district]
            changed={p:s for p,s in d.p.blocks.items() if d.changed_by.get(p)==design.ident and s!=d.base.blocks.get(p,AIR)}
            self.assertGreater(len(changed),15)
            origin=tuple(min(p[n] for p in changed) for n in range(3))
            signatures.add(tuple(sorted((tuple(p[n]-origin[n] for n in range(3)),s) for p,s in changed.items())))
            self.assertTrue(all(base(s).endswith('_stairs') or base(s).startswith(('dawnoftimebuilder:','mythrais:')) for s in changed.values()))
        self.assertEqual(20,len(signatures))
        self.assertTrue(all(len(v['material_checks'])==v['buildings'] for v in result.values()))

    def test_all_current_furniture_windows_stairs_body_routes_and_tagged_or_default_inventory_survive(self):
        unwritten=0
        for d in self.districts.values():
            self.assertEqual(d.base.tags,d.p.tags)
            for pos in d.protected|d.body:
                self.assertEqual(d.base.blocks.get(pos,AIR),d.p.blocks.get(pos,AIR))
            for pos,state in d.base.blocks.items():
                if base(state) in ('minecraft:chest','minecraft:barrel','minecraft:furnace','minecraft:brewing_stand') and pos not in d.base.tags:
                    unwritten+=1
                    self.assertEqual(state,d.p.blocks[pos])
                if 'glass' in base(state) or base(state).startswith(('mcwwindows:','mcwdoors:','handcrafted:')):
                    self.assertEqual(state,d.p.blocks[pos])
            for row in d.supports:
                pos=tuple(row['existing_support'])
                self.assertEqual(d.base.blocks[pos],d.p.blocks[pos])
        self.assertGreater(unwritten,0)

    def test_blind_recesses_have_opposed_sill_head_and_continuous_interior_back_half(self):
        pairs=0
        for d in self.districts.values():
            for effect in d.effects:
                cells=effect['changes'].get('half-block blind wall recess between the retained original posts',[])
                for raw in cells:
                    pos=tuple(raw);props=properties(d.p.blocks[pos])
                    if props['half']!='bottom':continue
                    above=(pos[0],pos[1]+1,pos[2]);other=properties(d.p.blocks[above])
                    self.assertEqual(other['half'],'top')
                    self.assertEqual(other['facing'],props['facing'])
                    self.assertEqual(base(d.p.blocks[pos]),base(d.p.blocks[above]))
                    self.assertIn(base(d.base.blocks[pos]),STRUCTURE)
                    self.assertIn(base(d.base.blocks[above]),STRUCTURE)
                    # Normal bottom/top stairs retain their full-height back
                    # half; the two shaped front halves form a blind recess.
                    pairs+=1
        self.assertGreater(pairs,100)

    def test_every_ceiling_rib_has_retained_real_support_and_greenhouse_glazing_is_exact(self):
        ribs=0
        for d in self.districts.values():
            for support in d.supports:
                if 'ceiling coffer' not in support['reason']:continue
                p=tuple(support['detail']);above=tuple(support['existing_support'])
                self.assertEqual(above,(p[0],p[1]+1,p[2]))
                self.assertEqual(d.base.blocks.get(p,AIR),AIR)
                self.assertIn(base(d.p.blocks[above]),STRUCTURE)
                self.assertNotIn(p,d.body)
                ribs+=1
        self.assertGreater(ribs,500)
        d=self.districts['court'];glass=next(e for e in d.effects if e['id']=='glasshouse')
        self.assertTrue(glass['protected_entrance_lintel_retained'])
        self.assertGreater(len(glass['changes']['modeled original opaque greenhouse rafter; all skylight glass retained']),30)

    def test_post_authoring_inventory_or_route_mutation_is_rejected(self):
        d=self.districts['signal'];pos=next(iter(d.body));old=d.p.blocks.get(pos)
        try:
            d.p.blocks[pos]='minecraft:stone_bricks'
            with self.assertRaisesRegex(UserError,'Protected|walking|architectural role'):check(self.districts)
        finally:
            if old is None:d.p.blocks.pop(pos,None)
            else:d.p.blocks[pos]=old
        pos=next(iter(d.p.tags));old=d.p.tags[pos]
        try:
            d.p.tags[pos]='{}'
            with self.assertRaisesRegex(UserError,'payload changed'):check(self.districts)
        finally:d.p.tags[pos]=old

    def test_a_flat_uniform_plane_cannot_pass_the_complete_building_rule(self):
        d=self.districts['court'];name=DESIGNS[10].name
        building={p:s for p,s in d.p.blocks.items() if d.p.owners[p]==name}
        for x in range(5,9):
            for z in range(5,9):building[x,25,z]='minecraft:oak_planks'
        with self.assertRaisesRegex(ValueError,'material run rule'):require_material_rule(building,name)


if __name__=='__main__':unittest.main()
