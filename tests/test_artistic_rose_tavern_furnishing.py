"""Furnishing custody tests; synthetic inputs are never native visual proof."""
import json
from pathlib import Path
from unittest import TestCase

from control_room.common import UserError
from tools.artistic_rose_tavern_furnishing import AIR, Furnishing, payload, prepare, validate


class Snapshot:
    def __init__(self, blocks=None, protected=()):
        self.blocks=dict(blocks or {});self.protected=set(protected)

    def state(self,pos):return self.blocks.get(pos,AIR)


def fixture(blocks=None,protected=(),routes=()):
    registry={'seed':'synthetic-only','world_path':'synthetic-only','blocks':{
        AIR:{},'minecraft:oak_planks':{},'chipped:detailed_dark_oak_planks':{},
        'minecraft:lantern':{'hanging':['true','false'],'waterlogged':['true','false']},
        'minecraft:dark_oak_wall_sign':{'facing':['north','south','east','west'],'waterlogged':['true','false']},
        'handcrafted:dark_oak_chair':{'facing':['north','south','east','west'],'color':['brown','green','red'],'waterlogged':['true','false']},
        'mythrais:decorated_column_middle_small_dark_oak':{'colour':['0'],'facing':['south','east']},
    }}
    return Furnishing(registry,Snapshot(blocks,protected),blocks or {},protected,routes)


def lit_fixture():
    roots={(1290+2*(n%4),65,-1287+2*(n//4)):'minecraft:oak_planks' for n in range(10)}
    p=fixture(roots)
    # The synthetic little layout has no large existing roof/floor surface.
    for x,y,z in roots:p.lamp(x,y+1,z)
    return p


class RoseFurnishingCustody(TestCase):
    def test_saved_furniture_cannot_be_replaced_even_with_same_state(self):
        pos=(1298,65,-1279);p=fixture({pos:'minecraft:oak_planks'})
        with self.assertRaisesRegex(UserError,'Do not replace existing'):
            p.put(*pos,'minecraft:oak_planks')

    def test_existing_default_or_tagged_block_entity_is_never_targeted(self):
        pos=(1298,65,-1279);p=fixture(protected={pos})
        with self.assertRaisesRegex(UserError,'block entity is immutable'):
            p.put(*pos,'minecraft:oak_planks')

    def test_central_second_lane_and_stair_approach_are_reserved(self):
        for pos in ((1302,65,-1278),(1303,66,-1270),(1307,66,-1271)):
            with self.subTest(pos=pos),self.assertRaisesRegex(UserError,'Keep central'):
                fixture().put(*pos,'minecraft:oak_planks')

    def test_manifest_service_route_has_two_high_clearance(self):
        routes=[{'floor_cells':[[1294,64,-1279]]}]
        for y in (65,66):
            with self.subTest(y=y),self.assertRaisesRegex(UserError,'Keep central'):
                fixture(routes=routes).put(1294,y,-1279,'minecraft:oak_planks')

    def test_native_middle_column_has_no_invented_mirror_property(self):
        p=fixture();p.column(1298,65,-1279,'middle','south')
        self.assertNotIn('mirrored',p.blocks[1298,65,-1279])
        with self.assertRaisesRegex(UserError,'Unsupported native'):
            p.state('mythrais:decorated_column_middle_small_dark_oak',mirrored=False)
        with self.assertRaisesRegex(UserError,'Missing actual'):
            p.state('invented:beautiful_tavern_light')

    def test_lantern_cannot_float_or_use_an_assumed_old_support(self):
        with self.assertRaisesRegex(UserError,'no real support'):
            fixture().lamp(1298,66,-1279)
        p=fixture({(1298,65,-1279):'minecraft:oak_planks'});p.lamp(1298,66,-1279)
        self.assertEqual(p.supports,{(1298,65,-1279):'minecraft:oak_planks'})

    def test_hanging_lantern_records_actual_overhead_support(self):
        pos=(1298,68,-1279);p=fixture({pos:'minecraft:oak_planks'})
        p.lamp(1298,67,-1279,hanging=True)
        self.assertIn(pos,p.supports);self.assertIn('hanging=true',p.blocks[1298,67,-1279])

    def test_disconnected_added_cluster_is_refused_even_if_lights_are_valid(self):
        p=lit_fixture();p.put(1300,72,-1273,'minecraft:oak_planks')
        with self.assertRaisesRegex(UserError,'no retained voxel support path'):validate(p)

    def test_final_seating_is_checked_after_all_chairs_are_added(self):
        p=lit_fixture();floor=(1299,64,-1277);p.snapshot.blocks[floor]='minecraft:oak_planks'
        p.chair(1299,65,-1277,'east','green');p.scene('blocked test',[],[floor])
        with self.assertRaisesRegex(UserError,'blocks an intimate scene approach'):validate(p)

    def test_material_limit_includes_retained_existing_building(self):
        before={(x,y,-1279):'minecraft:oak_planks' for x in range(1291,1295) for y in range(65,68)}
        p=fixture(before)
        for x in range(1291,1295):p.put(x,68,-1279,'minecraft:oak_planks')
        with self.assertRaisesRegex(ValueError,'complete furnished/depth composite'):validate(p)

    def test_capstan_height_and_metadata_cannot_fake_floor_lighting(self):
        p=lit_fixture();p.lights=[dict(row,pos=[*row['pos']]) for row in p.lights]
        p.lights[0]['pos']=[1300,72,-1273]
        with self.assertRaisesRegex(UserError,'actual new lantern'):validate(p)
        p=lit_fixture();p.lights=p.lights[:9]
        with self.assertRaisesRegex(UserError,'high capstan'):validate(p)

    def test_notices_are_literal_snbt_strings_with_no_old_inventory_replay(self):
        p=fixture({(1291,67,-1275):'minecraft:oak_planks'})
        p.sign(1292,67,-1275,'east',('A small notice','Food and songs','Mind the tide','Keep stairs clear'))
        after=json.loads(payload(p,p.blocks,'synthetic new signs','f'*64,tags=True))
        before=json.loads(payload(p,p.before,'synthetic exact before','f'*64))
        self.assertEqual([row[:3] for row in before['blocks']],[row[:3] for row in after['blocks']])
        self.assertEqual(before['block_entities'],[]);self.assertEqual(after['commands'],[])
        literal=after['block_entities'][0]['nbt'];self.assertIsInstance(literal,str)
        tag=json.loads(literal);self.assertEqual(len(tag['front_text']['messages']),4)
        self.assertTrue(tag['is_waxed']);self.assertNotIn('Items',tag)

    def test_inventory_payload_is_refused_in_the_furnishing_pass(self):
        p=lit_fixture();p.snapshot.blocks[1291,67,-1275]='minecraft:oak_planks'
        p.sign(1292,67,-1275,'east',('','','',''));p.tags[1292,67,-1275]['Items']=[]
        with self.assertRaisesRegex(UserError,'never adds/replays inventory'):validate(p)

    def test_qualified_light_layout_remains_proposed_not_visual_acceptance(self):
        proof=validate(lit_fixture())
        self.assertEqual(proof['voxel_rooted_new_fittings'],10)
        self.assertEqual(proof['existing_block_entity_tags_replayed'],0)
        self.assertIn('PENDING',proof['native_lighting_and_artistic_acceptance'])

    def test_official_home_refuses_before_reading_any_world(self):
        with self.assertRaisesRegex(UserError,'Owned artistic staging home only'):
            prepare(Path(r'D:\A World for Two'),'fictional-only','f'*64)
