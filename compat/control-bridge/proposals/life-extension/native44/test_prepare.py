import importlib.util
import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('native44_prepare',Path(__file__).with_name('prepare.py'))
native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)


class Snapshot:
    def __init__(self,unknown=None,water=False):self.unknown=unknown;self.water=water
    def chunk(self,x,z):return {}
    def state(self,pos):
        if pos==self.unknown:raise native.UserError('Fixture non-FULL cell')
        return 'minecraft:water[level=0]' if self.water else ('minecraft:grass_block[snowy=false]' if pos[1]==65 else 'minecraft:air')


class Native44PreparationTests(unittest.TestCase):
    def data(self):return json.loads(Path(__file__).parent.parent.joinpath('species-habitats.json').read_text())
    def site(self):
        return {'format':'awft-life-sites:2','seed':'private-fixture','world_path':'private-fixture','population_namespace':'00000000-0000-0000-0000-000000000001',
                'sites':[{'name':'actual-reviewed-glade-member','entity':'naturalist:deer','feet':[1100.5,66,-999.5],'roam_bounds':[1090,64,-1010,1110,72,-990],
                          'habitat':{'kind':'DRY','known_bounds':[1098,65,-1002,1102,70,-998]},'bank_anchor':[1100,-1000]}]}
    def run_members(self,sites,snapshot=None,protected=None,bank=None):
        return native.members(sites,self.data(),{'seed':'private-fixture','world_path':'private-fixture'},bank or {'bank_nodes_xz':[[1100,-1000]]},snapshot or Snapshot(),protected or set())

    def test_literal_full_field_preserves_properties_and_stable_UUID(self):
        namespace,rows=self.run_members(self.site());again=self.run_members(self.site())[1]
        self.assertEqual(rows[0]['uuid'],again[0]['uuid']);self.assertEqual(len(rows[0]['preimage']),150)
        self.assertIn([1100,65,-1000,'minecraft:grass_block[snowy=false]'],rows[0]['preimage'])
        self.assertNotIn('NoAI',rows[0]);self.assertNotIn('owner_uuid',rows[0])

    def test_unknown_perimeter_is_not_air(self):
        with self.assertRaises(native.UserError):self.run_members(self.site(),Snapshot(unknown=(1102,70,-998)))

    def test_rectangle_without_actual_bank_anchor_cannot_admit_site(self):
        with self.assertRaises(native.UserError):self.run_members(self.site(),bank={'bank_nodes_xz':[[1200,-800]]})

    def test_protected_R5_or_future_cable_column_blocks_site(self):
        with self.assertRaises(native.UserError):self.run_members(self.site(),protected={(1101,-999)})

    def test_no_forged_ownership_or_disabled_dragonfly(self):
        site=self.site();site['sites'][0]['NoAI']=False
        with self.assertRaises(native.UserError):self.run_members(site)
        site=self.site();site['sites'][0]['entity']='naturalist:dragonfly'
        with self.assertRaises(native.UserError):self.run_members(site)

    def test_fish_requires_real_literal_source_water_and_v2_kind(self):
        site=self.site();row=site['sites'][0];row['entity']='crittersandcompanions:koi_fish';row['habitat']['kind']='WATER';row['habitat']['known_bounds']=[1097,64,-1003,1103,70,-997];row['habitat']['water_bounds']=[1098,65,-1002,1102,66,-998]
        with self.assertRaises(native.UserError):self.run_members(site)
        rows=self.run_members(site,Snapshot(water=True))[1]
        self.assertEqual(rows[0]['native_MobCategory'],'water_ambient')

    def test_dry45_shortcut_and_unbounded_known_field_refused(self):
        with self.assertRaises(native.UserError):native.box([1100,65,-1000,1102,69,-998])
        with self.assertRaises(native.UserError):native.box([900,0,-1200,1352,300,-616])

    def test_complete_R5_AIR_skirt_and_explicit_cable_mask_are_retained(self):
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder);reg={'seed':'fixture','world_path':'fixture'}
            r5=home/'r5.json';r5.write_text(json.dumps({**reg,'blocks':[[1100,65,-1000,0]],'palette':['minecraft:air']}))
            cable=home/'cable.json';cable.write_text(json.dumps({'format':'awft-prospective-growth-exclusion:1','whole_crown_extra_skirt_metres':5,'all_growth_excluded_columns_xz':[[1200,-900]]}))
            machinery=home/'machine.json';machinery.write_text(json.dumps({**reg,'format':'awft-native-settlement:1','blocks':[[1150,80,-950,0]],'palette':['minecraft:air'],'block_entities':[]}))
            refs=[native.owned(home,p) for p in (cable,machinery)]
            index=home/'safety.json';index.write_text(json.dumps({**reg,'format':'awft-life-safety-index:1','includes_current_motion_navigation_and_future_cable':True,'sources':refs}))
            footprint=hashlib.sha256(json.dumps([(1100,65,-1000)],separators=(',',':')).encode()).hexdigest()
            with patch.object(native,'R5_COORDS',footprint):cols=native.protection(home,reg,r5,index)
            for p in ((1105,-995),(1200,-900),(1155,-945)):self.assertIn(p,cols)
            self.assertNotIn((1106,-995),cols)
            cable.write_text(cable.read_text()+' ')
            with patch.object(native,'R5_COORDS',footprint),self.assertRaises(native.UserError):native.protection(home,reg,r5,index)

    def test_nested_habitat_trait_override_cannot_become_authority(self):
        sites=self.site();sites['sites'][0]['habitat']['NoAI']=False
        with self.assertRaises(native.UserError):self.run_members(sites)


if __name__=='__main__':unittest.main()
