"""Small synthetic safety contracts, separate from native/visual acceptance."""
import json
from pathlib import Path
import unittest

from control_room.common import UserError
from tools.artistic_pirate_spit import (
    AIR, RESERVATIONS, SavedCoast, SpitPlan, dry_detour, payload, prepare,
    rectangle, reserved, tag_snbt, validate,
)


class SavedFixture:
    def __init__(self, overrides=None):
        self.overrides=overrides or {};self.protected=set()

    def state(self,pos):
        return self.overrides.get(pos,'minecraft:grass_block' if pos[1]==63 else
                                  'minecraft:dirt' if pos[1]<63 else AIR)


def registry():
    return {'seed':'fictional-test-world','world_path':'fixture-only',
            'blocks':{AIR:{},'minecraft:stone_bricks':{},'minecraft:barrel':{'facing':['up'],'open':['false']}}}


class StreetProof:
    def __init__(self):
        self.blocks={};self.tags={};self.buildings={};self.routes=[]
        self.walks={(1287,-1240):63,(1288,-1240):63}
        for x,y in ((1284,66),(1285,65),(1286,64)):
            for z in range(-1241,-1238):self.blocks[x,y,z]='minecraft:stone_bricks'
        for (x,z),y in self.walks.items():self.blocks[x,y,z]='minecraft:stone_bricks'
        self.owners={pos:'lanes' for pos in self.blocks}
        self.routes=[{'name':'fixture walk','floor_cells':[[x,y,z] for (x,z),y in self.walks.items()]}]

    def at(self,x,y,z):return self.blocks.get((x,y,z),AIR)


class PirateSpitContracts(unittest.TestCase):
    def test_current_native_palette_is_required(self):
        p=SpitPlan(registry(),SavedFixture(),'f'*64)
        with self.assertRaisesRegex(UserError,'Missing actual native block'):
            p.put(1288,64,-1240,'imagined:fancy_window')
        with self.assertRaisesRegex(UserError,'Unsupported native state'):
            p.put(1288,64,-1240,'minecraft:stone_bricks',facing='north')

    def test_an_existing_block_entity_never_becomes_a_blank_target(self):
        snapshot=SavedFixture();snapshot.protected.add((1288,64,-1240))
        p=SpitPlan(registry(),snapshot,'f'*64)
        with self.assertRaisesRegex(UserError,'Existing native block entity'):
            p.put(1288,64,-1240,'minecraft:stone_bricks')

    def test_no_house_foundation_on_water_or_deep_fill(self):
        c=SavedCoast(SavedFixture({(1290,64,-1280):'minecraft:water'}))
        with self.assertRaisesRegex(UserError,'actual dry natural ground'):
            c.require_dry({(1290,-1280)},'house',64)
        c=SavedCoast(SavedFixture())
        with self.assertRaisesRegex(UserError,'without flattening'):
            c.require_dry({(1290,-1280)},'house',67)

    def test_tree_canopy_is_reported_not_silently_accepted_for_new_house(self):
        c=SavedCoast(SavedFixture({(1290,70,-1280):'minecraft:oak_leaves'}))
        with self.assertRaisesRegex(UserError,'retained tree'):
            c.require_dry({(1290,-1280)},'new house',64)
        rows=c.require_dry({(1290,-1280)},'reserved imported original',64,allow_tree_canopy=True)
        self.assertEqual(rows[0]['ground_y'],63)
        self.assertEqual(c.ground(1290,-1280)['trees'][0]['pos'],[1290,70,-1280])

    def test_exact_original_reservations_are_real_holes(self):
        self.assertEqual([r['size_xz'] for r in RESERVATIONS],[[28,41],[21,34]])
        a,b=(rectangle(*r['bounds']) for r in RESERVATIONS)
        self.assertFalse(a & b)
        p=SpitPlan(registry(),SavedFixture(),'f'*64)
        with self.assertRaisesRegex(UserError,'downloaded original'):
            p.put(1290,64,-1320,'minecraft:stone_bricks')
        self.assertFalse(reserved(1311,-1320))

    def test_saved_terrain_detour_cannot_cross_a_wet_shortcut(self):
        class Coast:
            def ground(self,x,z):return {'kind':'water' if x==1288 and z!=-1282 else 'dry','y':63}
        class Plan:
            coast=Coast();buildings={}
            def at(self,x,y,z):return AIR
        route=dry_detour(Plan(),(1286,-1280),(1290,-1280),(1285,-1283,1291,-1279))
        self.assertIn((1288,-1282),route)
        self.assertNotIn((1288,-1280),route)
        self.assertEqual(route[0],(1286,-1280));self.assertEqual(route[-1],(1290,-1280))

    def test_detour_requires_actual_clear_headroom(self):
        class Coast:
            def ground(self,x,z):return {'kind':'dry','y':63}
        class Plan:
            coast=Coast();buildings={}
            def at(self,x,y,z):return 'minecraft:oak_log' if x==1288 else AIR
        with self.assertRaisesRegex(UserError,'No connected dry route'):
            dry_detour(Plan(),(1286,-1280),(1290,-1280),(1285,-1283,1291,-1279))

    def test_late_decoration_cannot_reuse_an_earlier_route_pass(self):
        p=StreetProof();validate(p)
        p.blocks[1287,64,-1240]='minecraft:barrel';p.owners[1287,64,-1240]='lanes'
        with self.assertRaisesRegex(UserError,'Final decoration obstructs'):
            validate(p)

    def test_unsupported_and_disconnected_walks_fail(self):
        p=StreetProof();del p.blocks[1287,63,-1240]
        with self.assertRaisesRegex(UserError,'floor support'):validate(p)
        p=StreetProof();p.walks[1294,-1240]=63;p.blocks[1294,63,-1240]='minecraft:stone_bricks';p.owners[1294,63,-1240]='lanes'
        with self.assertRaisesRegex(UserError,'disconnected or over-steep'):validate(p)

    def test_outdoor_nine_cap_is_not_hidden_by_owner_groups(self):
        p=StreetProof()
        for x in range(1290,1300):p.blocks[x,63,-1250]='minecraft:andesite';p.owners[x,63,-1250]='different-group'
        with self.assertRaisesRegex(ValueError,'outdoor nine-block'):validate(p)

    def test_before_and_after_share_exact_positions_without_commands(self):
        p=SpitPlan(registry(),SavedFixture(),'f'*64)
        p.put(1288,64,-1240,'minecraft:stone_bricks')
        before=json.loads(payload(p,p.before,'synthetic preimage'))
        after=json.loads(payload(p,p.blocks,'synthetic proposal',tags=True))
        self.assertEqual([row[:3] for row in before['blocks']],[row[:3] for row in after['blocks']])
        self.assertEqual(after['commands'],[]);self.assertEqual(before['commands'],[])
        self.assertEqual(after['backup_sha256'],'f'*64)
        self.assertEqual(before['palette'],[AIR])

    def test_native_block_entities_are_literal_snbt_strings_with_intact_items_and_text(self):
        p=SpitPlan(registry(),SavedFixture(),'f'*64)
        pos=1288,64,-1240
        p.put(*pos,'minecraft:barrel',facing='up',open='false')
        tag={'CustomName':json.dumps({'text':'The Rose — pantry'},ensure_ascii=False),
             'Items':[{'Slot':0,'id':'minecraft:bread','count':8}],
             'front_text':{'messages':[json.dumps({'text':'Ale / charts / music'})]},
             'is_waxed':True}
        p.tags[pos]=tag
        result=json.loads(payload(p,p.blocks,'synthetic native admission',tags=True))
        actual=result['block_entities'][0]
        self.assertEqual(actual['pos'],list(pos))
        self.assertIsInstance(actual['nbt'],str)
        self.assertIn('"Slot":0b',actual['nbt'])
        self.assertIn('"count":8',actual['nbt'])
        self.assertNotIn('"count":8b',actual['nbt'])
        untyped=actual['nbt'].replace('"Slot":0b','"Slot":0')
        self.assertEqual(json.loads(untyped),tag)
        for invalid in (-1,128,True,'0'):
            with self.assertRaisesRegex(UserError,'Slot must be'):
                tag_snbt({'Items':[{'Slot':invalid}]})

    def test_official_home_is_refused_before_any_file_write(self):
        with self.assertRaisesRegex(UserError,'separate owned artistic'):
            prepare(Path(r'D:\A World for Two'),'fictional-id','f'*64)


if __name__=='__main__':unittest.main()
