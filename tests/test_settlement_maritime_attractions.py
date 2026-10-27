"""Synthetic geometry/admission tests; no live world, vessel or kinetic proof."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from control_room.common import UserError
from tools.settlement_maritime_attractions import (
    AIR, BASE_BACKUP_ID, BASE_BACKUP_SHA, COG_POSITION, MaritimePlan, admit_entity_snapshot,
    berth, cog_boxes, context, proposal, sailing_cog, tender_hoist,
)


def fixture():
    bools=['true','false'];facing=['north','east','south','west']
    blocks={key:{} for key in (AIR,'minecraft:spruce_planks','minecraft:spruce_fence','minecraft:dark_oak_fence')}
    blocks['minecraft:water']={'level':[str(n) for n in range(16)]}
    blocks['minecraft:spruce_stairs']={'facing':facing,'half':['top','bottom'],'shape':['straight'],'waterlogged':bools}
    blocks['minecraft:stripped_spruce_log']={'axis':['x','y','z']}
    blocks['minecraft:oak_sign']={'rotation':[str(n) for n in range(16)],'waterlogged':bools}
    blocks['minecraft:dark_oak_slab']={'type':['top','bottom','double'],'waterlogged':bools}
    blocks['minecraft:chain']={'axis':['x','y','z'],'waterlogged':bools}
    blocks['minecraft:lantern']={'hanging':bools,'waterlogged':bools}
    blocks['minecraft:chest']={'facing':facing,'type':['single','left','right'],'waterlogged':bools}
    registry={'blocks':blocks,'items':['minecraft:emerald','minecraft:gold_nugget','minecraft:cookie'],
              'entities':['smallships:cog','smallships:ship_part','minecraft:boat'],
              'entity_categories':{},'seed':'SYNTHETIC-ONLY','world_path':'SYNTHETIC-ONLY'}
    previous={(x,75,z):'minecraft:dark_oak_slab[type=double,waterlogged=false]'
              for x in range(1154,1159) for z in range(-1442,-1437)}
    previous.update({(x,76,z):'minecraft:dark_oak_fence' for x in range(1154,1159) for z in (-1442,-1438)})
    previous.update({(1156,77,-1440):'create:rope_pulley[axis=x]',
                     (1153,77,-1440):'create:hand_crank[facing=west,waterlogged=false]',
                     (1154,77,-1440):'create:shaft[axis=x,waterlogged=false]',
                     (1155,77,-1440):'create:shaft[axis=x,waterlogged=false]'})
    previous.update({(x,65,-1249):'minecraft:spruce_planks' for x in (1189,1190,1191,1192)})
    ctx=SimpleNamespace(registry=registry,backup={'id':BASE_BACKUP_ID,'sha256':BASE_BACKUP_SHA,'verified':True},
                        previous=previous,protected=set(),headroom=set(),sources=[])
    survey={'samples':[{'x':x,'z':z,'y':63,'ground_y':30,'ocean_floor_y':30,
                        'block':'minecraft:water','fluid':True,'block_entities':[]}
                       for x in range(1136,1217,8) for z in range(-1450,-1233,8)]}
    return ctx,survey


class MaritimeAttractionTests(unittest.TestCase):
    def test_real_cog_entity_has_shared_furled_intact_native_data(self):
        ctx,survey=fixture();data,_=proposal(ctx,survey)
        commands=data['candidate_plan']['commands']
        self.assertEqual(len(commands),1)
        self.assertTrue(commands[0].startswith('summon smallships:cog 1196.5 63.1 -1264.5 '))
        self.assertIn('Sail:{State:0b,Color:"white",SailHealth:100f}',commands[0])
        self.assertIn('locked:0b,Items:[]',commands[0])
        self.assertIn('UUID:[I;',commands[0])
        self.assertNotIn('NoGravity',commands[0]);self.assertNotIn('Invulnerable',commands[0])
        self.assertEqual(data['sailing_cog']['native_parts'],6)

    def test_read_only_probe_cannot_spawn_or_reset_an_inventory(self):
        ctx,survey=fixture();data,before=proposal(ctx,survey)
        self.assertEqual(data['format'],'awft-maritime-proposal:1')
        self.assertEqual(before['format'],'awft-native-settlement:1')
        self.assertEqual(before['commands'],[])
        self.assertEqual(before['block_entities'],[])
        self.assertLess(len(before['blocks']),5000)
        self.assertEqual(len(data['candidate_plan']['block_entities']),3)
        self.assertIn('minecraft:water[level=0]',before['palette'])
        self.assertEqual(ctx.previous[(1191,65,-1249)],'minecraft:spruce_planks')

    def test_only_small_52_block_cradle_moves_and_no_original_component_is_replaced(self):
        ctx,survey=fixture();p=MaritimePlan(ctx,survey);hoist=tender_hoist(p)
        self.assertEqual(hoist['expected_moving_blocks'],52)
        self.assertEqual(hoist['unchanged_original_payload'],35)
        self.assertEqual(hoist['swept_occupied_cells'],542)
        self.assertEqual(len(p.blocks),17)
        self.assertTrue(all(pos not in ctx.previous for pos in p.blocks))
        self.assertEqual(hoist['floor_y'],{'original':75,'water_pickup':62,'fully_retracted':76})
        self.assertTrue(all(base['state'].startswith('minecraft:dark_oak_') for base in hoist['payload']))
        self.assertNotIn(tuple(hoist['pulley']),{tuple(row['pos']) for row in hoist['payload']})

    def test_new_static_obstruction_in_lift_path_refuses_instead_of_erasing(self):
        ctx,survey=fixture();pos=(1157,70,-1440);ctx.previous[pos]='minecraft:chest'
        with self.assertRaisesRegex(UserError,'strike completed'):
            tender_hoist(MaritimePlan(ctx,survey))
        self.assertEqual(ctx.previous[pos],'minecraft:chest')

    def test_inventory_and_reserved_architectural_air_are_preserved(self):
        ctx,survey=fixture();ctx.protected.add((1159,75,-1440))
        with self.assertRaisesRegex(UserError,'protected inventory'):
            tender_hoist(MaritimePlan(ctx,survey))
        ctx,survey=fixture();ctx.previous[(1190,64,-1260)]=AIR
        with self.assertRaisesRegex(UserError,'reserved air'):
            berth(MaritimePlan(ctx,survey))

    def test_shallow_launch_refuses_without_seabed_edits(self):
        ctx,survey=fixture()
        for row in survey['samples']:row['ocean_floor_y']=61
        p=MaritimePlan(ctx,survey)
        with self.assertRaisesRegex(UserError,'three-block water column'):
            sailing_cog(p)
        self.assertEqual(p.blocks,{})

    def test_actual_multipart_clearance_rejects_a_proposed_block(self):
        ctx,survey=fixture();p=MaritimePlan(ctx,survey)
        p.blocks[(1196,64,-1264)]='minecraft:spruce_planks'
        with self.assertRaisesRegex(UserError,'multipart/player clearance'):
            sailing_cog(p)
        boxes=cog_boxes()
        self.assertEqual(len(boxes),6)
        self.assertAlmostEqual(max(box[4] for box in boxes),COG_POSITION[1]+9)

    def test_unknown_entity_or_native_property_fails_closed(self):
        ctx,survey=fixture();ctx.registry['entities'].remove('smallships:cog')
        with self.assertRaisesRegex(UserError,'not registered'):
            sailing_cog(MaritimePlan(ctx,survey))
        ctx,survey=fixture()
        with self.assertRaisesRegex(UserError,'Unknown maritime native'):
            MaritimePlan(ctx,survey).state('minecraft:spruce_planks',imaginary='value')

    def test_changed_verified_backup_requires_review_before_any_staging(self):
        ctx,_=fixture();ctx.backup['id']='different-receipt'
        with patch('tools.settlement_maritime_attractions.load_context',return_value=ctx):
            with self.assertRaisesRegex(UserError,'ecd64f backup changes'):
                context('synthetic-home-only')

    def test_discovery_is_shallow_open_water_and_has_only_modest_once_only_rewards(self):
        ctx,survey=fixture();data,_=proposal(ctx,survey)
        self.assertEqual(data['discovery']['depth_below_water_surface'],4)
        self.assertEqual(data['discovery']['chest'],[1148,59,-1282])
        tags=data['candidate_plan']['block_entities']
        chest=next(v for v in tags if v['pos']==[1148,59,-1282])
        self.assertIn('count:2',chest['nbt']);self.assertIn('count:6',chest['nbt']);self.assertIn('count:8',chest['nbt'])
        self.assertNotIn('tnt',chest['nbt'])
        self.assertNotIn('gunpowder',chest['nbt'])

    def test_raised_tender_body_has_exact_block_and_be_clearance_beyond_cradle(self):
        ctx,survey=fixture();data,before=proposal(ctx,survey)
        states={tuple(row[:3]):before['palette'][row[3]] for row in before['blocks']}
        for pos in ((1158,77,-1440),(1159,77,-1440),(1158,77,-1439),(1158,78,-1440)):
            self.assertEqual(states[pos],AIR)
        self.assertGreater(data['hoist']['combined_cradle_and_tender_clearance_cells'],542)
        for protection in ('block','BE'):
            ctx,survey=fixture();pos=(1158,77,-1440)
            if protection=='block':ctx.previous[pos]='minecraft:stone'
            else:ctx.protected.add(pos)
            with self.assertRaisesRegex(UserError,'Tender body sweep'):
                tender_hoist(MaritimePlan(ctx,survey))

    def snapshot(self,contract,phase,entities):
        return {'format':'awft-native-maritime-occupancy:1','game_time':100,
                'dimension':'minecraft:overworld','all_target_chunks_entity_ready':True,
                'regions_scanned':contract['phases'][phase]['regions'],'entities':entities}

    def test_pet_boat_and_dropped_item_each_block_berth_launch_and_hoist(self):
        ctx,survey=fixture();data,_=proposal(ctx,survey);contract=data['spatial_entity_admission']
        for phase,box in (('cog-before-spawn',[1196,63,-1265,1197,64,-1264]),
                          ('cog-before-spawn',[1196,63,-1274,1197,64,-1273]),
                          ('hoist-empty-cycle',[1158,77,-1440,1159,78,-1439])):
            for kind in ('minecraft:cat','minecraft:boat','minecraft:item'):
                entity={'entity':kind,'uuid':'11111111-1111-4111-8111-111111111111','bounds':box}
                with self.assertRaisesRegex(UserError,'Unauthorized spatial entity'):
                    admit_entity_snapshot(contract,self.snapshot(contract,phase,[entity]),phase,100)

    def test_occupancy_scan_must_be_fresh_and_cover_entity_ready_regions(self):
        ctx,survey=fixture();data,_=proposal(ctx,survey);contract=data['spatial_entity_admission'];phase='cog-before-spawn'
        snapshot=self.snapshot(contract,phase,[])
        admit_entity_snapshot(contract,snapshot,phase,100)
        for changes in ({'game_time':99},{'all_target_chunks_entity_ready':False},
                        {'regions_scanned':['cog-berth']},{'dimension':'minecraft:the_nether'}):
            with self.assertRaisesRegex(UserError,'same-tick'):
                admit_entity_snapshot(contract,dict(snapshot,**changes),phase,100)

    def test_only_explicit_empty_unoccupied_native_tender_fits_lift_authority(self):
        ctx,survey=fixture();data,_=proposal(ctx,survey);contract=data['spatial_entity_admission'];phase='hoist-tender-cycle'
        ident='22222222-2222-4222-8222-222222222222'
        tender={'entity':'minecraft:boat','uuid':ident,'bounds':[1157.8,77.05,-1440.2,1159.2,77.7,-1438.8],
                'wood':'spruce','inventory_empty':True,'passengers':0}
        auth={'tender_uuid':ident}
        admit_entity_snapshot(contract,self.snapshot(contract,phase,[tender]),phase,100,auth)
        for changes in ({'inventory_empty':False},{'passengers':1},{'wood':'jungle'},
                        {'bounds':[1157.8,77.05,-1440.2,1159.2,79,-1438.8]},
                        {'entity':'minecraft:chest_boat'}):
            with self.assertRaises(UserError):
                admit_entity_snapshot(contract,self.snapshot(contract,phase,[dict(tender,**changes)]),phase,100,auth)
        with self.assertRaises(UserError):
            admit_entity_snapshot(contract,self.snapshot(contract,phase,[tender]),phase,100)
        with self.assertRaisesRegex(UserError,'not observed'):
            admit_entity_snapshot(contract,self.snapshot(contract,phase,[]),phase,100,auth)

    def test_own_cog_and_real_parts_are_permitted_only_in_launch_phase(self):
        ctx,survey=fixture();data,_=proposal(ctx,survey);contract=data['spatial_entity_admission'];phase='cog-launch'
        cog={'entity':'smallships:cog','uuid':contract['commissioned_cog_uuid'],
             'bounds':[1196,63,-1265,1197,64,-1264]}
        part={'entity':'smallships:ship_part','uuid':'33333333-3333-4333-8333-333333333333',
              'bounds':cog['bounds'],'native_parent_uuid':cog['uuid']}
        admit_entity_snapshot(contract,self.snapshot(contract,phase,[cog,part]),phase,100)
        with self.assertRaises(UserError):
            admit_entity_snapshot(contract,self.snapshot(contract,'cog-before-spawn',[cog]),'cog-before-spawn',100)
        with self.assertRaises(UserError):
            admit_entity_snapshot(contract,self.snapshot(contract,phase,[cog,dict(part,entity='minecraft:cat')]),phase,100)

    def test_hoist_entity_requires_actual_uuid_class_and_captured_payload_custody(self):
        ctx,survey=fixture();data,_=proposal(ctx,survey);contract=data['spatial_entity_admission'];phase='hoist-empty-cycle'
        ident='44444444-4444-4444-8444-444444444444'
        entity={'entity':'create:stationary_contraption','uuid':ident,'bounds':[1154,75,-1442,1161,77,-1437],
                'native_class':'com.simibubi.create.content.contraptions.ControlledContraptionEntity',
                'captured_payload_sha256':contract['owned_hoist_payload_sha256']}
        auth={'hoist_uuid':ident}
        admit_entity_snapshot(contract,self.snapshot(contract,phase,[entity]),phase,100,auth)
        with self.assertRaises(UserError):
            admit_entity_snapshot(contract,self.snapshot(contract,phase,[dict(entity,captured_payload_sha256='wrong')]),phase,100,auth)

    def test_initial_departure_blocks_are_verified_before_any_cog_launch(self):
        ctx,survey=fixture();ctx.previous[(1196,64,-1274)]='minecraft:stone'
        with self.assertRaisesRegex(UserError,'departure clearance'):
            sailing_cog(MaritimePlan(ctx,survey))


if __name__=='__main__':unittest.main()
