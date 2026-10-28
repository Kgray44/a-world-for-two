"""Pure authored architecture checks; these do not substitute for native views."""
from collections import deque
import json
from pathlib import Path
import unittest

from control_room.common import UserError
from tools.artistic_materials import material_runs
from tools.artistic_west_r2_frontage import AIR, LABELS, construct, check, key
from tools.artistic_west_r2_study import flood


FIXTURE=Path(__file__).parent/'fixtures/west_r2_registry.json'


class WestR2FrontageTests(unittest.TestCase):
    def setUp(self):
        self.p=construct(json.loads(FIXTURE.read_text()))

    def test_one_dense_turn_with_three_distinct_fronts_and_reachable_rooms(self):
        proof=check(self.p)
        self.assertEqual(proof['rooms'],7)
        self.assertEqual(set(proof['three_front_directions']),{'south','west','east'})
        self.assertEqual([len(self.p.levels[k]) for k in LABELS],[2,3,2])
        self.assertLess(len(self.p.levels[LABELS[2]][1]),len(self.p.main[LABELS[2]]))
        public=next(r for r in self.p.routes if r['kind']=='public-two-wide')
        cells={(x,z) for x,y,z in public['positions']}
        visited={next(iter(cells))};todo=deque(visited)
        while todo:
            x,z=todo.popleft()
            for q in ((x-1,z),(x+1,z),(x,z-1),(x,z+1)):
                if q in cells and q not in visited:visited.add(q);todo.append(q)
        self.assertEqual(visited,cells)
        # Both sides of the retained pottery barrow have genuine two-cell-wide
        # turns, rather than a plotted centerline with blocked shoulders.
        for z in range(14,23):
            xs={x for x,zz in cells if zz==z}
            self.assertTrue(any(x+1 in xs for x in xs),str((z,xs)))
        self.assertFalse(any((x,18) in cells for x in range(7,11)))

    def test_full_material_policy_and_muted_roof_geometry(self):
        for label in LABELS:
            field={q:s for q,s in self.p.blocks.items() if self.p.owners[q]==label}
            self.assertEqual(material_runs(field),[])
        coverings={key(s) for s in self.p.blocks.values() if key(s).startswith('mcwroofs:')}
        self.assertTrue(all(any(name.startswith('mcwroofs:'+wood+'_') for wood in ('dark_oak','spruce','deepslate')) for name in coverings))
        # A true taller roof, lower rear annex and southern half hip supply
        # differences in volume; a repeated palette band cannot satisfy this.
        self.assertGreater(max(r['eave_y'] for r in self.p.roof_sections),min(r['eave_y'] for r in self.p.roof_sections)+3)
        self.assertTrue(any(r['actual_annex_level_change'] for r in self.p.roof_sections))
        self.assertTrue(any(r['southern_half_hip'] for r in self.p.roof_sections))
        for x in range(4):
            for z in range(4):
                self.p.blocks[x,18,z]='minecraft:white_concrete';self.p.owners[x,18,z]=LABELS[0]
        with self.assertRaisesRegex(ValueError,'material run rule failed'):check(self.p)

    def test_real_clearance_and_support_fail_closed(self):
        public=next(r for r in self.p.routes if r['kind']=='public-two-wide')
        q=tuple(public['positions'][0]);old=self.p.blocks[q]
        self.p.blocks[q]='minecraft:stone'
        with self.assertRaisesRegex(UserError,'route/headroom'):check(self.p)
        self.p.blocks[q]=old
        backing=tuple(self.p.supports[0]['support']);self.p.blocks[backing]=AIR
        with self.assertRaisesRegex(UserError,'no actual authored backing'):check(self.p)

    def test_interiors_have_real_trade_objects_not_empty_facade_shells(self):
        expected={'minecraft:crafting_table','minecraft:loom','minecraft:grindstone','minecraft:cartography_table',
                  'minecraft:brown_bed','handcrafted:dark_oak_counter','handcrafted:dark_oak_shelf',
                  'farmersdelight:dark_oak_cabinet','mcwlights:tavern_wall_lantern'}
        self.assertTrue(expected <= {key(s) for s in self.p.blocks.values()})
        for label in LABELS:
            actual={tuple(r['position']) for r in self.p.props if r['owner']==label and key(self.p.blocks[tuple(r['position'])])==r['block']}
            self.assertGreaterEqual(len(actual),30)
        self.assertFalse(any('Items:' in nbt for nbt in self.p.tags.values()))
        # The surviving room storage starts as normal native empty/default
        # containers, never copies contents/ownership from an existing house.
        self.assertTrue(all(key(self.p.blocks[q]).endswith('_wall_sign') for q in self.p.tags))

    def test_geographic_partition_never_infers_unknown_or_water_as_land(self):
        land={(x,z):{'kind':'dry'} for x in range(5) for z in range(3)}
        for z in range(3):land[2,z]={'kind':'unknown'}
        left=flood(land,[(0,1)],set());right=flood(land,[(4,1)],set())
        self.assertFalse(left&right)
        self.assertTrue(all(x<2 for x,z in left))
        land[2,1]={'kind':'water'}
        self.assertEqual(flood(land,[(0,1)],set()),left)
        land[2,1]={'kind':'retained_object'}
        self.assertFalse(flood(land,[(0,1)],{(2,1)})&right)
        with self.assertRaisesRegex(UserError,'anchor is unavailable'):flood(land,[(2,0)],set())


if __name__=='__main__':unittest.main()
