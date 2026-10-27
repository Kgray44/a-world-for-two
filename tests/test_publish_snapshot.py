"""Real tagged Git fixtures prove publication admission and immutable custody."""
import json
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from control_room.common import UserError, digest, write_json
from control_room.pack import generate_pack
from tools.publish_snapshot import MAX_FILE_BYTES, approved_catalog, build, extract_tag, safe_member


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base=Path(self.temporary.name)
        self.repo=self.base/'repo';self.repo.mkdir()
        self.git('init','-q')
        self.git('config','user.name','Synthetic publication fixture')
        self.git('config','user.email','fixture@example.invalid')
        self.guard=patch('tools.publish_snapshot.reserve_local')
        self.guard.start();self.addCleanup(self.guard.stop)

    def git(self,*args):
        return subprocess.run(['git','-C',str(self.repo),*args],check=True,capture_output=True,text=True).stdout.strip()

    def snapshot(self,number,text='reviewed configuration'):
        version='0.1.0-candidate.'+str(number)
        lock={'version':version,'minecraft':'1.21.1','neoforge':'21.1.262','java':21,'mods':[]}
        config=self.repo/'packwiz/config/example.toml';config.parent.mkdir(parents=True,exist_ok=True)
        config.write_text('description = '+json.dumps(text)+'\n')
        write_json(self.repo/'catalog/lock.json',lock)
        sha=generate_pack(self.repo/'packwiz',lock)
        self.git('add','packwiz','catalog/lock.json');self.git('commit','-qm','Fixture '+version)
        tag='awft-'+version;self.git('tag',tag)
        return {'version':version,'git_tag':tag,'pack_sha256':sha,'status':'prerelease'}

    def catalog(self,rows,stable=None):
        target=self.repo/'catalog/publication.json'
        write_json(target,{'format':'awft-publication:1','stable':stable,'snapshots':rows})
        return target

    def test_all_approved_old_tags_survive_and_dirty_main_is_not_published(self):
        first=self.snapshot(1,'first approved snapshot')
        second=self.snapshot(2,'second approved snapshot')
        catalog=self.catalog([first,second])
        (self.repo/'packwiz/pack.toml').write_text('UNREVIEWED DIRTY MAIN\n')
        output=self.base/'public'
        receipt=build(self.repo,catalog,output)
        for row in (first,second):
            target=output/'releases'/row['version']
            self.assertEqual(digest(target/'pack.toml'),row['pack_sha256'])
            self.assertEqual(json.loads((target/'lock.json').read_text())['version'],row['version'])
        self.assertFalse((output/'pack.toml').exists())
        self.assertFalse((output/'index.toml').exists())
        self.assertIn(first['version'],(output/'index.html').read_text())
        self.assertIn(second['version'],(output/'index.html').read_text())
        self.assertIsNone(json.loads((output/'publication.json').read_text())['stable'])
        self.assertTrue(Path(receipt['staging_retained'],'receipt.json').is_file())

    def test_missing_tag_never_creates_a_public_output(self):
        row=self.snapshot(1);self.git('tag','-d',row['git_tag'])
        output=self.base/'public'
        with self.assertRaisesRegex(UserError,'tag is missing'):
            build(self.repo,self.catalog([row]),output)
        self.assertFalse(output.exists())

    def test_changed_tagged_sha_refuses_and_retains_failure_receipt(self):
        row=self.snapshot(1);row['pack_sha256']='0'*64
        output=self.base/'public'
        with self.assertRaisesRegex(UserError,'SHA-256 changed'):
            build(self.repo,self.catalog([row]),output)
        self.assertFalse(output.exists())
        failures=list(self.base.glob('.awft-publication-*/failure.json'))
        self.assertEqual(len(failures),1)
        self.assertFalse(json.loads(failures[0].read_text())['public_output_created'])

    def test_duplicate_version_refused_before_packaging(self):
        row=self.snapshot(1)
        with self.assertRaisesRegex(UserError,'Duplicate publication version'):
            approved_catalog(self.catalog([row,row.copy()]))

    def test_stable_field_cannot_promote_a_prerelease_to_root(self):
        row=self.snapshot(1)
        with self.assertRaisesRegex(UserError,'stable must remain null'):
            build(self.repo,self.catalog([row],stable=row['version']),self.base/'public')

    def test_index_drift_inside_an_approved_pack_is_refused(self):
        row=self.snapshot(1)
        (self.repo/'packwiz/index.toml').write_text('hash-format = "sha256"\n')
        self.git('add','packwiz/index.toml');self.git('commit','-qm','Broken index fixture')
        self.git('tag','-f',row['git_tag'])
        with self.assertRaisesRegex(UserError,'hash chain/pins failed'):
            build(self.repo,self.catalog([row]),self.base/'public')

    def test_unindexed_runtime_jar_cannot_enter_public_payload(self):
        row=self.snapshot(1)
        jar=self.repo/'packwiz/mods/unapproved.jar';jar.parent.mkdir();jar.write_bytes(b'not a distributable jar')
        self.git('add','packwiz/mods/unapproved.jar');self.git('commit','-qm','Bad payload fixture')
        self.git('tag','-f',row['git_tag'])
        with self.assertRaisesRegex(UserError,'Runtime binaries'):
            build(self.repo,self.catalog([row]),self.base/'public')

    def test_safe_extract_rejects_links_traversal_and_oversize_without_allocating(self):
        for name in ('packwiz/../outside','/outside','packwiz/config/accounts.json'):
            info=tarfile.TarInfo(name);info.size=1
            with self.assertRaises(UserError):safe_member(info)
        info=tarfile.TarInfo('packwiz/config/oversize.txt');info.size=MAX_FILE_BYTES+1
        with self.assertRaisesRegex(UserError,'8 MiB'):safe_member(info)
        directory=tarfile.TarInfo('packwiz/world');directory.type=tarfile.DIRTYPE
        with self.assertRaisesRegex(UserError,'world data'):safe_member(directory)
        archive=self.base/'linked.tar'
        with tarfile.open(archive,'w') as tar:
            info=tarfile.TarInfo('packwiz/config/link.toml');info.type=tarfile.SYMTYPE;info.linkname='../../outside'
            tar.addfile(info)
        with self.assertRaisesRegex(UserError,'links'):
            extract_tag(archive,self.base/'extract')
        self.assertFalse((self.base/'outside').exists())

    def test_existing_output_is_preserved(self):
        row=self.snapshot(1);output=self.base/'public';output.mkdir()
        marker=output/'existing.txt';marker.write_text('Keep this owner data')
        with self.assertRaisesRegex(UserError,'must be new'):
            build(self.repo,self.catalog([row]),output)
        self.assertEqual(marker.read_text(),'Keep this owner data')


if __name__=='__main__':unittest.main()
