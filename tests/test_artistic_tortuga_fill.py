"""Real orientation, occupied geometry and preservation gates; not art scores."""
import json,math
from pathlib import Path
import unittest
from unittest.mock import patch

from control_room.common import UserError
from tools.artistic_tortuga_frontages import RECIPES,AIR,key,check
from tools.artistic_tortuga_variants import variant,FACES
from tools.artistic_tortuga_fill import BATCHES,modeled,rich_workscene,route_geometry,lane_materials,stopped
from tools.settlement_attractions import properties


class TortugaFillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=json.loads((Path(__file__).parent/'fixtures/tortuga_fill_registry.json').read_text())

    def test_all_native_bed_halves_rotate_with_their_actual_facing_and_stair_routes(self):
        for recipe in RECIPES:
            for turn in range(4):
                p=variant(self.registry,recipe,turn)
                for q,s in p.blocks.items():
                    props=properties(s)
                    if key(s).endswith('_bed')and props['part']=='foot':
                        dx,dz=((0,-1),(1,0),(0,1),(-1,0))[FACES.index(props['facing'])]
                        head=p.blocks[q[0]+dx,q[1],q[2]+dz]
                        self.assertEqual(properties(head)['part'],'head')
                        self.assertEqual(properties(head)['facing'],props['facing'])
                check(p)

    def test_trimming_sky_never_removes_a_named_real_room_or_walking_body(self):
        full=variant(self.registry,'gullwatch',1,trim_sky=False)
        trim=variant(self.registry,'gullwatch',1)
        self.assertLess(len(trim.blocks),len(full.blocks))
        self.assertEqual({q:s for q,s in trim.blocks.items()if s!=AIR},{q:s for q,s in full.blocks.items()if s!=AIR})
        for r in trim.routes:
            if r['kind']=='stairs':continue
            for x,y,z in r['positions']:
                self.assertIn((x,y,z),trim.blocks)
                self.assertIn((x,y+1,z),trim.blocks)

    def test_new_wall_storage_cannot_destroy_an_existing_object_or_lose_its_mount(self):
        p=RECIPES['quarter-tide'](self.registry)
        p.put(1,1,5,'minecraft:barrel',facing='up',open=False)
        with self.assertRaisesRegex(UserError,'must not overwrite'):
            rich_workscene(p,'quarter-tide')
        p=rich_workscene(RECIPES['lost-tide'](self.registry),'lost-tide')
        p.blocks[2,2,8]=AIR
        with self.assertRaisesRegex(UserError,'actual authored support'):check(p)

    def test_five_differently_composed_new_houses_have_real_task_views_and_clear_doors(self):
        buildings=[]
        for definition in BATCHES.values():
            states,tags,rows,main=modeled(self.registry,definition);buildings+=rows
            self.assertTrue(main)
            self.assertFalse(any('Items:'in tag or'Owner:'in tag for tag in tags.values()))
            for row in rows:
                self.assertEqual(row['proof']['material']['violations'],[])
                for view in row['scene_views']:
                    self.assertGreaterEqual(math.dist(view['feet'],view['look_at']),2)
                    self.assertNotEqual(view['actual_source_object'],AIR)
                for entry in row['entries']:
                    self.assertTrue(key(states[tuple(entry['world_door'])]).endswith('_door'))
        self.assertEqual(len(buildings),5)
        self.assertEqual(len({b['recipe']for b in buildings}),5)
        self.assertEqual(sum(b['proof']['rooms']for b in buildings),12)

    def test_two_wide_route_cannot_ignore_a_real_barrel_or_bridge_water_gap(self):
        field={(x,z):[]for x in range(8)for z in range(5)}
        definition={'links':(('narrow actual test route',((0,1),(6,1))),)}
        lane,_=route_geometry({},set(),field,definition)
        self.assertTrue(all(q in field for q in lane))
        wall={(3,y,z):'minecraft:barrel[facing=up,open=false]'for y in(64,65)for z in range(5)}
        with self.assertRaisesRegex(UserError,'No real two-wide'):route_geometry(wall,set(),field,definition)
        no_floor={q:v for q,v in field.items()if q[0]!=3}
        with self.assertRaisesRegex(UserError,'No real two-wide'):route_geometry({},set(),no_floor,definition)

    def test_an_old_stopped_receipt_does_not_authorize_a_new_preimage(self):
        with patch('tools.artistic_tortuga_fill.read_json',return_value={'verified':True,'id':'old','sha256':'old','scope':'stopped'}):
            with self.assertRaisesRegex(UserError,'no automatic old-proof rebind'):stopped(Path('.'),'new','new')

    def test_opposite_house_eaves_are_not_one_street_material_but_a_broad_paved_square_still_refuses(self):
        lane={(x,z)for x in range(12)for z in range(12)}
        states={(x,75,0):'mcwroofs:deepslate_roof'for x in range(12)}
        states.update({(0,75,z):'mcwroofs:deepslate_roof'for z in range(12)})
        states.update({(x,63,z):'minecraft:cobblestone'for x in range(12)for z in(0,1)})
        self.assertEqual(lane_materials(states,lane,'two-wide actual lane')['violations'],[])
        states.update({(x,63,z):'minecraft:cobblestone'for x,z in lane})
        with self.assertRaisesRegex(ValueError,'multi-axis material run'):lane_materials(states,lane,'unwanted broad paved square')


if __name__=='__main__':unittest.main()
