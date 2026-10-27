import tempfile
import unittest
import json
from unittest.mock import Mock,patch
from pathlib import Path
import warnings
import zipfile
import nbtlib as n
from control_room.common import UserError,digest
from tools.artistic_deploy import (CINEMATIC_ENTRIES,CINEMATIC_PACK_ID,cinematic_entries,
    prepare_level,retire_world_cinematics,retire_world_dashboard,stopped,verify_cinematic_folder)


class FreshArrivalTests(unittest.TestCase):
    def test_player_state_and_old_scene_are_removed_without_changing_generation(self):
        with tempfile.TemporaryDirectory() as root:
            p=Path(root)/'level.dat'
            generation=n.Compound({'seed':n.Long(1234),'generate_features':n.Byte(1)})
            n.File({'Data':n.Compound({'Player':n.Compound({'XpLevel':n.Int(99)}),
                'WorldGenSettings':generation,'Time':n.Long(23456),'GameType':n.Int(3),
                'GameRules':n.Compound({'doDaylightCycle':n.String('false'),'keepInventory':n.String('true')}),
                'DataPacks':n.Compound({'Enabled':n.List[n.String](['vanilla','mod:example',
                    'file/awft-settlement-cinematic-old.zip','file/awft-settlement-cinematic.zip',
                    'file/other-build.zip',CINEMATIC_PACK_ID,CINEMATIC_PACK_ID]),
                    'Disabled':n.List[n.String](['file/awft-settlement-cinematic.zip',
                        'file/awft-settlement-cinematic-new.zip',CINEMATIC_PACK_ID,'mod:disabled'])})})},gzipped=True).save(p)
            prepare_level(p)
            data=n.load(p)['Data']
            self.assertNotIn('Player',data)
            self.assertEqual(data['WorldGenSettings'],generation)
            self.assertEqual(int(data['Time']),23456)
            self.assertEqual(int(data['GameType']),0)
            self.assertEqual(data['GameRules']['keepInventory'],'true')
            self.assertEqual(data['GameRules']['doDaylightCycle'],'true')
            self.assertEqual(data['GameRules']['doWeatherCycle'],'true')
            self.assertEqual(list(map(str,data['DataPacks']['Enabled'])),
                ['vanilla','mod:example','file/other-build.zip',CINEMATIC_PACK_ID])
            self.assertEqual(list(map(str,data['DataPacks']['Disabled'])),['mod:disabled'])

    def test_unknown_global_id_is_refused_without_editing_level(self):
        with tempfile.TemporaryDirectory() as root:
            p=Path(root)/'level.dat';p.write_bytes(b'original untouched input')
            with self.assertRaisesRegex(UserError,'native-verified'):
                prepare_level(p,'file/awft-settlement-cinematic.zip')
            self.assertEqual(p.read_bytes(),b'original untouched input')

    def test_absent_known_id_does_not_invent_an_activation(self):
        with tempfile.TemporaryDirectory() as root:
            p=Path(root)/'level.dat'
            n.File({'Data':n.Compound({'DataPacks':n.Compound({
                'Enabled':n.List[n.String](['vanilla','file/awft-settlement-cinematic.zip']),
                'Disabled':n.List[n.String](['mod:disabled'])})})},gzipped=True).save(p)
            prepare_level(p,None)
            self.assertEqual(list(map(str,n.load(p)['Data']['DataPacks']['Enabled'])),['vanilla'])

    def test_live_owned_java_still_blocks_handoff(self):
        layout=Mock();layout.server=Path.cwd().resolve()
        process=Mock();process.info={'name':'java.exe'};process.cwd.return_value=str(layout.server)
        with patch('tools.artistic_deploy.psutil.process_iter',return_value=[process]), \
                patch('tools.artistic_deploy.Backups') as backups:
            with self.assertRaisesRegex(UserError,'Stop both dedicated servers'):
                stopped(layout)
            backups.assert_not_called()


class CanonicalPaxiCustodyTests(unittest.TestCase):
    def files(self):
        return {name:('{"source":"'+name+'"}\n').encode() for name in CINEMATIC_ENTRIES}

    def archive(self,root,files=None):
        path=Path(root)/'reviewed.zip'
        with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as archive:
            for name,data in (files or self.files()).items():archive.writestr(name,data)
        return path

    def raw_folder(self,root,files=None):
        folder=Path(root)/'config/paxi/datapacks/awft-settlement-cinematic'
        for name,data in (files or self.files()).items():
            p=folder/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        return folder

    def test_raw_folder_matches_each_original_zip_entry(self):
        with tempfile.TemporaryDirectory() as root:
            archive=self.archive(root);folder=self.raw_folder(root)
            expected=cinematic_entries(archive,digest(archive))
            self.assertEqual(len(expected),4)
            self.assertEqual(verify_cinematic_folder(folder,expected),expected)

    def test_missing_tampered_or_extra_raw_entry_is_refused(self):
        for change in ('missing','changed','extra'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as root:
                archive=self.archive(root);folder=self.raw_folder(root)
                expected=cinematic_entries(archive,digest(archive))
                if change=='missing':(folder/'pack.mcmeta').unlink()
                elif change=='changed':(folder/'pack.mcmeta').write_bytes(b'newer unreviewed source')
                else:(folder/'unrelated.json').write_bytes(b'{}')
                with self.assertRaisesRegex(UserError,'entries differ'):
                    verify_cinematic_folder(folder,expected)

    def test_changed_source_zip_and_unexpected_entries_are_refused(self):
        with tempfile.TemporaryDirectory() as root:
            archive=self.archive(root)
            with self.assertRaisesRegex(UserError,'ZIP differs'):cinematic_entries(archive,'0'*64)
            bad=self.files();bad['../outside.json']=b'{}';archive=self.archive(root,bad)
            with self.assertRaisesRegex(UserError,'unexpected archive'):
                cinematic_entries(archive,digest(archive))

    def test_duplicate_zip_entry_does_not_hide_an_alternative_scene(self):
        with tempfile.TemporaryDirectory() as root:
            archive=self.archive(root)
            with warnings.catch_warnings(),zipfile.ZipFile(archive,'a') as z:
                warnings.simplefilter('ignore',UserWarning);z.writestr('pack.mcmeta',b'alternative')
            with self.assertRaisesRegex(UserError,'unexpected archive'):
                cinematic_entries(archive,digest(archive))

    def test_symlink_zip_payload_is_refused(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'reviewed.zip'
            with zipfile.ZipFile(path,'w') as z:
                for name,data in self.files().items():
                    entry=zipfile.ZipInfo(name)
                    if name=='pack.mcmeta':entry.create_system=3;entry.external_attr=0o120777<<16
                    z.writestr(entry,data)
            with self.assertRaisesRegex(UserError,'unexpected archive'):
                cinematic_entries(path,digest(path))

    def test_uncompressed_zip_is_bounded_before_entry_reads(self):
        with tempfile.TemporaryDirectory() as root:
            files=self.files();files['pack.mcmeta']=b'0'*(2*1024**2+1)
            archive=self.archive(root,files)
            with self.assertRaisesRegex(UserError,'unexpected archive'):
                cinematic_entries(archive,digest(archive))

    def test_all_matching_world_zips_are_retained_outside_save(self):
        with tempfile.TemporaryDirectory() as root:
            root=Path(root);world=root/'prepared';datapacks=world/'datapacks';datapacks.mkdir(parents=True)
            retired=root/'retired';retired.mkdir()
            names=['awft-settlement-cinematic.zip','awft-settlement-cinematic-old.zip',
                   'AWFT-SETTLEMENT-CINEMATIC-new.ZIP']
            for name in names:(datapacks/name).write_bytes(name.encode())
            (datapacks/'other-build.zip').write_bytes(b'unrelated pack')
            (datapacks/'awft-integration').mkdir()
            originals={name:digest(datapacks/name) for name in names}
            self.assertEqual(set(retire_world_cinematics(world,retired)),set(names))
            self.assertEqual({name:digest(retired/name) for name in names},originals)
            self.assertEqual(sorted(p.name for p in datapacks.iterdir()),['awft-integration','other-build.zip'])


class DashboardAdmissionRetirementTests(unittest.TestCase):
    def arrange(self,root):
        root=Path(root);state=root/'dashboard';state.mkdir()
        previous=root/'private-handoff/previous-dashboard';previous.mkdir(parents=True)
        identity={'handoff_id':'fresh-world-handoff','target_world':str(root/'world/AWorldForTwo'),
            'source_stage_world':str(root/'staging/world/RosewaterArtistic'),
            'candidate':'reviewed-candidate','pack_sha256':'a'*64}
        return state,previous,identity

    def test_whole_old_admission_tree_is_preserved_and_new_namespace_is_unadmitted(self):
        with tempfile.TemporaryDirectory() as root:
            state,previous,identity=self.arrange(root)
            files={'plan.json':b'old world plan','backup-receipt.json':b'old verified backup',
                'engineering-plan.json':b'old bridge admission',
                'harbor-craft-custody/entity.json':b'old entity identity',
                'native-journal/private.complete':b'immutable old completion'}
            for name,data in files.items():
                p=state/'settlement'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
            unrelated={'settings.json':b'{"heap_gib":8}','client-reports.json':b'pack sync custody',
                'eula-acceptance.json':b'owner input','menu-artwork/original.png':b'original art'}
            for name,data in unrelated.items():
                p=state/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
            (state/'atlas-control.json').write_bytes(b'old world cache limit')
            (state/'official-initialization.json').write_bytes(b'old world initialization')
            result=retire_world_dashboard(state,previous,identity)
            for name,data in files.items():self.assertEqual((previous/'settlement'/name).read_bytes(),data)
            for name,data in unrelated.items():self.assertEqual((state/name).read_bytes(),data)
            self.assertEqual(sorted(p.name for p in (state/'settlement').iterdir()),['handoff-identity.json'])
            marker=json.loads((state/'settlement/handoff-identity.json').read_text())
            self.assertEqual(marker['identity'],identity)
            self.assertFalse(marker['construction_admitted'])
            self.assertFalse(marker['registry_admitted'])
            self.assertFalse(marker['backup_receipt_admitted'])
            self.assertFalse(marker['source_stage_proofs_copied'])
            self.assertEqual(marker['status'],'NO CONSTRUCTION ADMISSION')
            self.assertEqual(set(result['retired']),{'settlement','atlas-control.json','official-initialization.json'})

    def test_claim_cache_and_sync_retire_only_for_explicit_matching_world(self):
        with tempfile.TemporaryDirectory() as root:
            state,previous,identity=self.arrange(root)
            related={'claims-proposals.json':{'world_path':identity['target_world'],'status':'proposal'},
                'dashboard-sync.json':{'world':identity['target_world'],'cached':True}}
            retained={'claim-cache.json':{'world_path':str(Path(root)/'different-world'),'cached':True},
                'claims-cache.json':{'cached':True},'world-sync.json':['unbound history']}
            for name,value in (related|retained).items():(state/name).write_text(json.dumps(value))
            (state/'claim-proposals.json').write_bytes(b'malformed history retained')
            result=retire_world_dashboard(state,previous,identity)
            for name,value in related.items():
                self.assertFalse((state/name).exists());self.assertEqual(json.loads((previous/name).read_text()),value)
            for name,value in retained.items():self.assertEqual(json.loads((state/name).read_text()),value)
            self.assertEqual((state/'claim-proposals.json').read_bytes(),b'malformed history retained')
            self.assertEqual(set(result['preserved_unbound_or_foreign_metadata']),set(retained)|{'claim-proposals.json'})

    def test_retirement_collision_fails_before_moving_any_active_files(self):
        with tempfile.TemporaryDirectory() as root:
            state,previous,identity=self.arrange(root)
            (state/'settlement').mkdir();(state/'settlement/plan.json').write_bytes(b'old plan')
            (state/'atlas-control.json').write_bytes(b'cache')
            (previous/'atlas-control.json').write_bytes(b'earlier preserved copy')
            with self.assertRaisesRegex(UserError,'preservation target'):
                retire_world_dashboard(state,previous,identity)
            self.assertEqual((state/'settlement/plan.json').read_bytes(),b'old plan')
            self.assertEqual((state/'atlas-control.json').read_bytes(),b'cache')
            self.assertFalse((previous/'settlement').exists())

    def test_active_dashboard_cannot_be_its_own_retirement_destination(self):
        with tempfile.TemporaryDirectory() as root:
            state,_,identity=self.arrange(root);nested=state/'private';nested.mkdir()
            with self.assertRaisesRegex(UserError,'separate'):
                retire_world_dashboard(state,nested,identity)

    def test_unreviewed_proof_fields_are_not_copied_into_handoff_identity(self):
        with tempfile.TemporaryDirectory() as root:
            state,previous,identity=self.arrange(root);identity['verified']=True
            with self.assertRaisesRegex(UserError,'identity is required'):
                retire_world_dashboard(state,previous,identity)
            self.assertFalse((state/'settlement').exists())
