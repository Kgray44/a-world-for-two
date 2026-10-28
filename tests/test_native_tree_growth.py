import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from control_room.common import UserError
from tools import native_tree_growth as trees


class SavedPlot:
    """Small saved-state fixture; no Minecraft or fake Level is created."""
    def __init__(self,changes=None,unknown=None,protected=()):
        self.changes=changes or {};self.unknown=unknown;self.protected=set(protected)
        self.sources=[{'file':'fixture-saved-field','sha256':'a'*64}]
    def state(self,pos):
        if pos==self.unknown:raise UserError('fixture chunk is not FULL')
        return self.changes.get(pos,'minecraft:grass_block[snowy=false]' if pos[1]==65 else 'minecraft:air')
    def close(self):pass


class NativeTreeGrowthTests(unittest.TestCase):
    def test_envelope_includes_whole_crown_and_known_physics_perimeter(self):
        write,known=trees.envelopes((1100,66,-1000),(-4,-1,-4,4,14,4))
        self.assertEqual(write,[1096,65,-1004,1104,80,-996])
        self.assertEqual(known,[1088,63,-1012,1112,84,-988])
        with self.assertRaises(UserError):trees.protect_envelope(write,{(1104,-996)})
        trees.protect_envelope(write,{(1105,-996)})

    def test_malformed_oversized_or_height_unknown_envelopes_fail_closed(self):
        for root,relative in (((True,66,0),(-1,-1,-1,1,3,1)),((0,66,0),(0,0,0,-1,3,1)),
                              ((0,66,0),(1,0,1,3,3,3)),((0,66,0),(-40,-1,-40,40,50,40)),
                              ((0,310,0),(-3,-1,-3,3,10,3))):
            with self.subTest(root=root,relative=relative),self.assertRaises(UserError):trees.envelopes(root,relative)

    def test_complete_saved_preimage_keeps_properties_and_unknown_perimeter_is_not_air(self):
        known=(-2,64,-2,2,70,2);write=(-1,65,-1,1,69,1);root=(0,66,0)
        field,soil=trees.collect_known(SavedPlot(),known,write,root)
        self.assertEqual(len(field),175);self.assertEqual(soil,{'minecraft:grass_block':9})
        self.assertEqual(field[0,65,0],'minecraft:grass_block[snowy=false]')
        with self.assertRaises(UserError):trees.collect_known(SavedPlot(unknown=(2,70,2)),known,write,root)

    def test_existing_trees_water_rising_terrain_and_native_BE_are_retained(self):
        known=(-2,64,-2,2,72,2);write=(-1,65,-1,1,71,1);root=(0,66,0)
        fixtures=[SavedPlot({(1,69,1):'minecraft:oak_leaves[persistent=false,distance=1,waterlogged=false]'}),
                  SavedPlot({(1,65,1):'minecraft:water[level=0]'}),
                  SavedPlot({(1,65,1):'minecraft:oak_slab[type=bottom,waterlogged=true]'}),
                  SavedPlot({(1,70,1):'minecraft:stone'}),SavedPlot(protected={(1,66,1)})]
        for snapshot in fixtures:
            with self.subTest(snapshot=snapshot),self.assertRaises(UserError):trees.collect_known(snapshot,known,write,root)

    def test_protection_includes_AIR_unwritten_BE_plaza_and_walk_skirts(self):
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder);reg={'seed':'private-fixture','world_path':'fixture-world'}
            authored={**reg,'palette':['minecraft:air'],'blocks':[[10,90,10,0]],'block_entities':[{'pos':[30,65,30]}]}
            target=home/'authored.json';target.write_text(json.dumps(authored))
            index=home/'index.json';index.write_text(json.dumps({'plans':[{'name':'all authored AIR','path':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}]}))
            walk=home/'walk.json';walk.write_text(json.dumps({'walk_columns_with_five_metre_growth_skirt':[[50,50]]}))
            plaza=home/'plaza.json';plaza.write_text(json.dumps({**reg,'blocks':[[70,65,70,0]],'palette':['minecraft:air']}))
            mask=trees.protection(reg,index,walk,plaza);cols={tuple(row) for row in mask['columns']}
            for point in ((15,15),(35,35),(50,50),(75,75)):self.assertIn(point,cols)
            self.assertNotIn((76,75),cols)
            with self.assertRaises(UserError):trees.protection({**reg,'seed':'other'},index,walk,plaza)

    def fixture(self,home):
        for name in ('dashboard/settlement','packwiz','classes/worldfortwo/bridge/mixin'):(home/name).mkdir(parents=True,exist_ok=True)
        registry={'seed':'fixture','world_path':str(home/'world/Fixture'),'blocks':list(trees.SAPLINGS)}
        (home/'dashboard/settlement/registry.json').write_text(json.dumps(registry))
        (home/'dashboard/settlement/backup-receipt.json').write_text(json.dumps({'verified':True,'id':'20261027T000000Z-abcdef','sha256':'a'*64}))
        (home/'packwiz/active.json').write_text(json.dumps({'pack_sha256':'b'*64}))
        for name in ('NativeTreeGrowthSupport.class','TreeGrowthScope.class','mixin/NativeTreeGrowthGuardMixin.class'):
            (home/'classes/worldfortwo/bridge'/name).write_bytes(b'fixture: compile provenance is checked separately')
        return registry

    def arguments(self,home,mode='describe'):
        return dict(home=home,output=home/'staging'/mode,native_classes=home/'classes',candidate='candidate-fixture',bridge='bridge-fixture',mode=mode)

    def test_describe_preparation_has_no_plot_or_world_writer_and_binds_real_input_hashes(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(trees,'guard',return_value={'allowed':True}),patch.object(trees,'BackupWorld',side_effect=AssertionError('describe must not read world')):
            home=Path(folder);self.fixture(home);result=trees.prepare(**self.arguments(home))
            request=json.loads((Path(result['output'])/result['bundle']/'request.json').read_text())
            self.assertEqual(request['allowed_operation'],'describe');self.assertEqual(request['candidate_version'],'candidate-fixture')
            self.assertNotIn('before',request);self.assertNotIn('construction_ready',request)
            self.assertEqual(request['native_scope_sha256'],hashlib.sha256((home/'classes/worldfortwo/bridge/TreeGrowthScope.class').read_bytes()).hexdigest())
            self.assertFalse(result['native_actions'])

    def test_review_prepares_concrete_tree_hash_without_an_executable_request(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(trees,'guard',return_value={'allowed':True}),patch.object(trees,'BackupWorld',return_value=SavedPlot()):
            home=Path(folder);registry=self.fixture(home);q=home/'qualification.json'
            q.write_text(json.dumps({'sapling':trees.SAPLINGS[0],'all_reachable_features_reviewed':True,'derivation_sha256':'c'*64,'native_descriptor_sha256':'d'*64,'relative_write_bounds':[-1,-1,-1,1,6,1]}))
            mask={'columns':[]};args=self.arguments(home,'review')
            args.update(saplings=[trees.SAPLINGS[0]],root=(0,66,0),qualification=q,index_path=home/'index',composition_path=home/'walk',plaza_path=home/'plaza')
            with patch.object(trees,'protection',return_value=mask):result=trees.prepare(**args)
            manifest=json.loads((Path(result['output'])/'manifest.json').read_text())
            self.assertIsNone(result['bundle']);self.assertIsNone(manifest['command_only_after_parent_review_and_explicit_install'])
            self.assertFalse(list(Path(result['output']).rglob('request.json')))
            self.assertEqual(manifest['tree_plan_sha256_for_concrete_review'],hashlib.sha256((Path(result['output'])/'tree-plan.json').read_bytes()).hexdigest())

    def test_grow_rejects_generic_or_stale_approval_and_preserves_failed_receipt(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(trees,'guard',return_value={'allowed':True}),patch.object(trees,'BackupWorld',return_value=SavedPlot()):
            home=Path(folder);self.fixture(home);q=home/'qualification.json';ready=home/'ready.json'
            q.write_text(json.dumps({'sapling':trees.SAPLINGS[0],'all_reachable_features_reviewed':True,'derivation_sha256':'c'*64,'native_descriptor_sha256':'d'*64,'relative_write_bounds':[-1,-1,-1,1,6,1]}))
            ready.write_text(json.dumps({'construction_complete':True,'functional_commissioning_complete':True,'visual_corrections_reviewed':True,'checkpoint_sha256':'a'*64,'tree_plan_sha256':'e'*64}))
            args=self.arguments(home,'grow');args.update(saplings=[trees.SAPLINGS[0]],root=(0,66,0),qualification=q,index_path=home/'index',composition_path=home/'walk',plaza_path=home/'plaza',construction_ready=ready)
            with patch.object(trees,'protection',return_value={'columns':[]}),self.assertRaisesRegex(UserError,'exact qualified tree-plan SHA'):trees.prepare(**args)
            failed=json.loads((home/'staging/grow/failed-receipt.json').read_text());self.assertFalse(failed['native_actions'])
            self.assertFalse(list((home/'staging/grow').rglob('request.json')))

    def test_concrete_review_hash_can_be_approved_without_circular_request_identity(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(trees,'guard',return_value={'allowed':True}),patch.object(trees,'BackupWorld',return_value=SavedPlot()):
            home=Path(folder);self.fixture(home);q=home/'qualification.json';ready=home/'ready.json'
            q.write_text(json.dumps({'sapling':trees.SAPLINGS[0],'all_reachable_features_reviewed':True,'derivation_sha256':'c'*64,'native_descriptor_sha256':'d'*64,'relative_write_bounds':[-1,-1,-1,1,6,1]}))
            args=self.arguments(home,'review');args.update(saplings=[trees.SAPLINGS[0]],root=(0,66,0),qualification=q,index_path=home/'index',composition_path=home/'walk',plaza_path=home/'plaza')
            with patch.object(trees,'protection',return_value={'columns':[]}):review=trees.prepare(**args)
            review_manifest=json.loads((Path(review['output'])/'manifest.json').read_text())
            approved=review_manifest['tree_plan_sha256_for_concrete_review']
            ready.write_text(json.dumps({'construction_complete':True,'functional_commissioning_complete':True,'visual_corrections_reviewed':True,'checkpoint_sha256':'a'*64,'tree_plan_sha256':approved}))
            args.update(mode='grow',output=home/'staging/grow',construction_ready=ready)
            with patch.object(trees,'protection',return_value={'columns':[]}):growth=trees.prepare(**args)
            request=json.loads((Path(growth['output'])/growth['bundle']/'request.json').read_text())
            self.assertEqual(request['plan']['sha256'],approved)
            self.assertEqual(request['construction_ready']['sha256'],hashlib.sha256(ready.read_bytes()).hexdigest())
            self.assertEqual(request['before']['sha256'],hashlib.sha256((Path(growth['output'])/'tree-before-VERIFY-ONLY.json').read_bytes()).hexdigest())
            self.assertFalse(growth['native_actions'])


if __name__=='__main__':unittest.main()
