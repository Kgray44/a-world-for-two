import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('native44_town_prepare',HERE/'prepare.py')
native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)


class Snapshot:
    def __init__(self,unknown=None):self.unknown=unknown;self.chunks=[]
    def state(self,pos):
        if pos==self.unknown:raise ValueError('Fixture non-FULL cell')
        return 'minecraft:stone' if pos[1]==65 else 'minecraft:air'
    def chunk(self,x,z):self.chunks.append((x,z));return {}


class TownAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.data=json.loads((HERE.parent/'species-habitats.json').read_text())
        self.registry={'seed':'FIXTURE','world_path':'FIXTURE'}
        self.bounds=[1246,65,-1266,1250,69,-1262]
        self.mask={(x,y,z) for x in range(1246,1251) for y in range(65,70) for z in range(-1266,-1261)}
        self.authorities={'chandler-home':{'known_bounds':self.bounds,'cells':self.mask,'standing':{(1248,66,-1264),(1249,66,-1264)},'species':{'minecraft:allay','ribbits:ribbit','cozys-improved-cats:improved_cat'}}}

    def sites(self):
        return {**self.registry,'format':'awft-life-sites:3','population_namespace':'00000000-0000-0000-0000-000000000001',
                'sites':[{'name':'reviewed-chandler-resident','entity':'minecraft:allay','feet':[1248.5,66,-1263.5],
                          'roam_bounds':[1246,65,-1266,1250,69,-1262],'town_site':'chandler-home','habitat':{'kind':'AIR','known_bounds':self.bounds}}]}

    def run_members(self,sites,authority=None,snapshot=None,protected=None):
        return native.members(sites,self.data,self.registry,{'bank_nodes_xz':[[1100,-1000]]},snapshot or Snapshot(),protected or set(),self.authorities if authority is None else authority)

    def test_northern_town_uses_authored_authority_without_fake_forest_anchor(self):
        snap=Snapshot();namespace,rows=self.run_members(self.sites(),snapshot=snap)
        self.assertEqual(rows[0]['town_site'],'chandler-home');self.assertNotIn('bank_anchor',rows[0]);self.assertEqual(snap.chunks,[])
        self.assertEqual(len(rows[0]['preimage']),125)
        self.assertEqual(rows[0]['uuid'],self.run_members(self.sites())[1][0]['uuid'])

    def test_no_authority_rectangle_or_wrong_identity_is_refused(self):
        with self.assertRaises(ValueError):self.run_members(self.sites(),authority={})
        sites=self.sites();sites['sites'][0]['entity']='naturalist:deer';sites['sites'][0]['habitat']['kind']='DRY'
        with self.assertRaises(ValueError):self.run_members(sites)

    def test_mixed_or_forged_authority_fields_refused(self):
        sites=self.sites();sites['sites'][0]['bank_anchor']=[1248,-1264]
        with self.assertRaises(native.UserError):self.run_members(sites)
        sites=self.sites();sites['sites'][0]['NoAI']=False
        with self.assertRaises(native.UserError):self.run_members(sites)

    def test_exact_full_unknown_cell_remains_unknown_in_town(self):
        with self.assertRaises(ValueError):self.run_members(self.sites(),snapshot=Snapshot((1250,69,-1262)))

    def test_protected_machine_R5_or_cable_column_still_blocks_town(self):
        with self.assertRaises(native.UserError):self.run_members(self.sites(),protected={(1248,-1264)})

    def test_music_uses_reviewed_actual_home_route_without_profession_assignment(self):
        sites=self.sites();row=sites['sites'][0];row['entity']='ribbits:ribbit';row['habitat'].update(kind='MUSIC',roof=[1248,68,-1264],shelter_path=[[1248,66,-1264],[1249,66,-1264]])
        result=self.run_members(sites)[1][0];self.assertEqual(result['native_MobCategory'],'creature');self.assertNotIn('profession',result)
        row['habitat']['shelter_path'].append([1250,66,-1264])
        with self.assertRaises(ValueError):self.run_members(sites)

    def test_old_woodland_bounds_are_not_widened(self):
        with self.assertRaises(native.UserError):native.box(self.bounds)
        self.assertEqual(native.town.town_box(self.bounds),125)

    def test_source_authentication_and_unwritten_cells(self):
        temp=tempfile.TemporaryDirectory(prefix='awft-town-fixture-');home=Path(temp.name).resolve()
        self.assertEqual(home.parent,Path(tempfile.gettempdir()).resolve());self.assertTrue(home.name.startswith('awft-town-fixture-'))
        try:
            def write(name,value):
                f=home/name;f.write_text(json.dumps(value));return native.owned(home,f)
            plan={**self.registry,'format':'awft-native-settlement:1','palette':['minecraft:stone','minecraft:air'],
                  'blocks':[[*p,0 if p[1]==65 else 1] for p in sorted(self.mask)]}
            ref=write('fixture-plan.json',plan)
            proof={'operation':'verify','plan_sha256':ref['sha256'],'blocks':125,'failures':0,
                   'status':'verified actual block identities, orientation, block entities and supplied inventories'}
            check=write('fixture-proof.json',proof);(home/'fixture-proof.json.complete').write_text(check['sha256'])
            authority={**self.registry,'format':'awft-town-life-authority:1','source_checkpoint_sha256':'a'*64,
                       'sources':[{'name':'signal-lane-full','kind':'AUTHORED_FULL_PLAN','plan':ref,'native_verify':check}],
                       'sites':[{'id':'chandler-home','source_names':['signal-lane-full'],'species':['minecraft:allay'],
                                 'known_bounds':self.bounds,'occupancy_cells':[list(p) for p in sorted(self.mask)],
                                 'standing_positions':[[1248,66,-1264]]}]}
            path=home/'fixture-authority.json';path.write_text(json.dumps(authority))
            _,rows=native.town.read_authority(home,self.registry,path,native.bounded,native.owned,native.KINDS)
            self.assertEqual(len(rows['chandler-home']['cells']),125)
            authority['sites'][0]['occupancy_cells'].append([1251,67,-1264]);path.write_text(json.dumps(authority))
            with self.assertRaises(ValueError):native.town.read_authority(home,self.registry,path,native.bounded,native.owned,native.KINDS)
            authority['sites'][0]['occupancy_cells'].pop();path.write_text(json.dumps(authority));(home/'fixture-plan.json').write_text(json.dumps(plan)+' ')
            with self.assertRaises(ValueError):native.town.read_authority(home,self.registry,path,native.bounded,native.owned,native.KINDS)
        finally:temp.cleanup()


if __name__=='__main__':unittest.main()
