import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from control_room.common import Layout, UserError
from tools.settlement_detail import (
    AIR, MAX_OUTPUT_BYTES, QUAY_POCKETS, Context, DetailPlan, admit_clearance,
    clearance_states, prepare,
    validate_independence,
)


def fixture():
    return Context({'blocks':{'minecraft:air':{},'minecraft:stone':{},'minecraft:quartz_bricks':{},
                              'minecraft:spruce_planks':{},'minecraft:oak_stairs':{
                                  'facing':['north','south','east','west']}},
                    'seed':'test-seed','world_path':'test-world'},
                   {'verified':True,'sha256':'a'*64},
                   {(1160,66,-1000):'minecraft:stone',
                    (1160,67,-1000):AIR,(1161,67,-1000):AIR})


class DetailPassTests(unittest.TestCase):
    def test_unknown_air_is_not_construction_permission_and_feature_rolls_back(self):
        ctx=fixture();p=DetailPlan(ctx,'castle')
        def action():
            p.put(1160,67,-1000,'minecraft:quartz_bricks')
            p.put(1162,67,-1000,'minecraft:quartz_bricks')
        self.assertFalse(p.feature('Rejected two-part feature','synthetic',action))
        self.assertEqual(p.blocks,{})
        self.assertIn('Unknown previous state',p.deferred[0]['reason'])
        self.assertEqual(ctx.previous[(1160,67,-1000)],AIR)

    def test_complete_connected_feature_retains_exact_previous_values(self):
        ctx=fixture();p=DetailPlan(ctx,'castle')
        def action():
            p.put(1160,67,-1000,'minecraft:quartz_bricks')
            p.put(1161,67,-1000,'minecraft:quartz_bricks')
        self.assertTrue(p.feature('Attached pair','synthetic',action))
        self.assertEqual(len(p.blocks),2)
        self.assertEqual(p.supports[(1160,66,-1000)],'minecraft:stone')
        self.assertEqual(p.features[0]['positions'],2)

    def test_inventory_route_and_immutable_protections_each_reject_the_whole_feature(self):
        for collection in ('protected','headroom','immutable'):
            ctx=fixture();getattr(ctx,collection).add((1160,67,-1000));p=DetailPlan(ctx,'castle')
            self.assertFalse(p.feature(collection,'synthetic',lambda:p.put(1160,67,-1000,'minecraft:quartz_bricks')))
            self.assertFalse(p.blocks)

    def test_unreviewed_solid_replacement_and_unsupported_component_are_rejected(self):
        ctx=fixture();p=DetailPlan(ctx,'castle')
        self.assertFalse(p.feature('Masonry erasure','synthetic',lambda:p.put(1160,66,-1000,'minecraft:quartz_bricks')))
        ctx.previous[(1170,90,-1000)]=AIR
        self.assertFalse(p.feature('Floating detail','synthetic',lambda:p.put(1170,90,-1000,'minecraft:quartz_bricks')))
        self.assertIn('attachment',p.deferred[-1]['reason'])

    def test_native_properties_are_strict_including_unknown_names(self):
        p=DetailPlan(fixture(),'castle')
        for props in ({'invented':'yes'},{'facing':'up'}):
            with self.assertRaises(UserError):
                p.state('minecraft:oak_stairs',**props)
        self.assertEqual(p.state('minecraft:oak_stairs',facing='west'),'minecraft:oak_stairs[facing=west]')

    def test_conflicting_detail_families_cannot_silently_rewrite_each_other(self):
        p=DetailPlan(fixture(),'castle')
        self.assertTrue(p.feature('First','synthetic',lambda:p.put(1160,67,-1000,'minecraft:quartz_bricks')))
        self.assertFalse(p.feature('Second','synthetic',lambda:p.put(1160,67,-1000,'minecraft:stone')))
        self.assertEqual(p.blocks[(1160,67,-1000)],'minecraft:quartz_bricks')

    def test_independent_districts_cannot_invalidate_each_others_targets_or_attachments(self):
        ctx=fixture();first=DetailPlan(ctx,'castle');second=DetailPlan(ctx,'village')
        first.blocks[(1160,67,-1000)]='minecraft:quartz_bricks'
        second.blocks[(1160,67,-1000)]='minecraft:stone'
        with self.assertRaisesRegex(UserError,'share a changed position'):
            validate_independence({'castle':first,'village':second})
        second.blocks.clear();second.supports[(1160,67,-1000)]=AIR
        with self.assertRaisesRegex(UserError,'precondition attachment'):
            validate_independence({'castle':first,'village':second})

    def test_clearance_probe_is_exactly_four_bounded_empty_pockets_and_known_deck(self):
        ctx=fixture()
        for _,x in QUAY_POCKETS:
            for px in range(x-2,x+3):
                for z in (-1249,-1248):
                    ctx.previous[(px,65,z)]='minecraft:spruce_planks'
        states,pockets=clearance_states(ctx)
        self.assertEqual(len(states),240)
        self.assertEqual(sum(v==AIR for v in states.values()),200)
        self.assertEqual(len(pockets),4)
        self.assertTrue(all(pos[2]<-1247 for pos in states))
        ctx.previous[(1039,67,-1249)]='minecraft:stone'
        with self.assertRaises(UserError):
            clearance_states(ctx)

    def test_clearance_admission_requires_exact_hash_world_original_backup_and_finished_zero_failure_receipt(self):
        ctx=fixture()
        for _,x in QUAY_POCKETS:
            for px in range(x-2,x+3):
                for z in (-1249,-1248):ctx.previous[(px,65,z)]='minecraft:spruce_planks'
        states,_=clearance_states(ctx);p=DetailPlan(ctx,'harbor-quays')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'probe.json';manifest=root/'manifest.json';receipt=root/'receipt.json'
            source.write_text(json.dumps(p.payload(states,'VERIFY ONLY','synthetic')))
            sha=hashlib.sha256(source.read_bytes()).hexdigest()
            manifest.write_text(json.dumps({'plan_file':source.name,'plan_sha256':sha,'backup_sha256':'a'*64}))
            proof={'operation':'verify','plan_sha256':sha,'blocks':240,'failures':1,'finished':'synthetic'}
            receipt.write_text(json.dumps(proof))
            with self.assertRaises(UserError):admit_clearance(ctx,root,manifest,receipt)
            self.assertFalse(ctx.air_admitted)
            proof['failures']=0;receipt.write_text(json.dumps(proof))
            admit_clearance(ctx,root,manifest,receipt)
            self.assertEqual(len(ctx.air_admitted),200)
            self.assertEqual(ctx.previous[(1039,70,-1249)],AIR)
            ctx.backup['sha256']='b'*64
            admit_clearance(ctx,root,manifest,receipt)
            self.assertEqual(ctx.sources[-1]['probe_backup_sha256'],'a'*64)
            self.assertEqual(ctx.sources[-1]['current_design_backup_sha256'],'b'*64)
            ctx.registry['world_path']='another-world'
            with self.assertRaisesRegex(UserError,'current world'):admit_clearance(ctx,root,manifest,receipt)

    def test_writer_creates_only_fresh_private_bundle_with_all_before_states_and_preserves_evidence(self):
        ctx=fixture();p=DetailPlan(ctx,'castle')
        p.feature('One attached detail','synthetic',lambda:p.put(1160,67,-1000,'minecraft:quartz_bricks'))
        with tempfile.TemporaryDirectory() as tmp:
            layout=Layout(Path(tmp));output=layout.state/'settlement'/'owned-test-detail'
            with patch('tools.settlement_detail.load_context',return_value=ctx), \
                 patch('tools.settlement_detail.construct',return_value={'castle':p}), \
                 patch('tools.settlement_detail.Storage.reserve') as reserve:
                result=prepare(layout.home,output)
                reserve.assert_called_once_with(MAX_OUTPUT_BYTES,target=output)
                index=json.loads((output/'index.json').read_text());district=index['districts'][0]
                before=json.loads((output/district['preconditions_file']).read_text())
                previous={(x,y,z):before['palette'][i] for x,y,z,i in before['blocks']}
                self.assertEqual(previous[(1160,67,-1000)],AIR)
                self.assertEqual(previous[(1160,66,-1000)],'minecraft:stone')
                self.assertEqual(result['native_activation'],'Not performed')
                self.assertFalse((layout.state/'settlement'/'plan.json').exists())
                old={path.name:path.read_bytes() for path in output.iterdir()}
                with self.assertRaises(UserError):prepare(layout.home,output)
                self.assertEqual(old,{path.name:path.read_bytes() for path in output.iterdir()})

    def test_storage_rejection_precedes_any_private_output_creation(self):
        ctx=fixture();p=DetailPlan(ctx,'castle')
        p.feature('One','synthetic',lambda:p.put(1160,67,-1000,'minecraft:quartz_bricks'))
        with tempfile.TemporaryDirectory() as tmp:
            layout=Layout(Path(tmp));output=layout.state/'settlement'/'must-not-exist'
            with patch('tools.settlement_detail.load_context',return_value=ctx), \
                 patch('tools.settlement_detail.construct',return_value={'castle':p}), \
                 patch('tools.settlement_detail.Storage.reserve',side_effect=UserError('reserve rejected')):
                with self.assertRaisesRegex(UserError,'reserve rejected'):prepare(layout.home,output)
            self.assertFalse(output.exists())


if __name__=='__main__':
    unittest.main()
