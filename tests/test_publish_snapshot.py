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

    def snapshot(self,number,text='reviewed configuration',mods=()):
        version='0.1.0-candidate.'+str(number)
        lock={'version':version,'minecraft':'1.21.1','neoforge':'21.1.262','java':21,'mods':list(mods)}
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

    def add_tagged_metadata(self,row,name='retired'):
        relative='mods/'+name+'.pw.toml'
        path=self.repo/'packwiz'/relative;path.parent.mkdir(exist_ok=True)
        path.write_text('name = "Retired synthetic fixture"\nfilename = "retired.jar"\nside = "both"\n'
                        '[download]\nurl = "https://example.invalid/retired.jar"\nhash-format = "sha256"\n'
                        'hash = "'+'0'*64+'"\n')
        self.git('add','packwiz/'+relative);self.git('commit','-qm','Retired synthetic metadata')
        self.git('tag','-f',row['git_tag'])
        return relative,{'sha256':digest(path),'reason':'Synthetic reviewed leftover; absent from this fixture lock and index'}

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

    def test_reviewed_unindexed_metadata_is_proved_and_never_copied(self):
        row=self.snapshot(1);relative,review=self.add_tagged_metadata(row)
        row['tagged_metadata_exclusions']={relative:review}
        output=self.base/'public'
        receipt=build(self.repo,self.catalog([row]),output)
        target=output/'releases'/row['version']
        self.assertFalse((target/relative).exists())
        self.assertEqual({p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_file()},
                         {'pack.toml','index.toml','config/example.toml','lock.json'})
        self.assertEqual(digest(target/'pack.toml'),row['pack_sha256'])
        proof=receipt['snapshots'][0]['tagged_metadata_exclusions_verified']
        self.assertEqual(len(proof),1)
        self.assertEqual(proof[0]['file'],relative)
        self.assertEqual(proof[0]['sha256'],review['sha256'])
        self.assertEqual(proof[0]['reason'],review['reason'])
        self.assertFalse(proof[0]['indexed'])
        self.assertFalse(proof[0]['published'])
        self.assertEqual(digest(self.repo/'packwiz'/relative),review['sha256'])

    def test_tampered_reviewed_metadata_fails_closed(self):
        row=self.snapshot(1);relative,review=self.add_tagged_metadata(row)
        row['tagged_metadata_exclusions']={relative:review}
        path=self.repo/'packwiz'/relative
        path.write_text(path.read_text()+'# changed after review\n')
        self.git('add','packwiz/'+relative);self.git('commit','-qm','Tampered synthetic metadata')
        self.git('tag','-f',row['git_tag'])
        output=self.base/'public'
        with self.assertRaisesRegex(UserError,'excluded metadata SHA-256 changed'):
            build(self.repo,self.catalog([row]),output)
        self.assertFalse(output.exists())

    def test_unknown_or_missing_exclusion_path_cannot_be_ignored(self):
        row=self.snapshot(1);relative,review=self.add_tagged_metadata(row)
        row['tagged_metadata_exclusions']={relative:review}
        unknown,unknown_review=self.add_tagged_metadata(row,'unknown')
        output=self.base/'public'
        with self.assertRaisesRegex(UserError,'exactly match reviewed'):
            build(self.repo,self.catalog([row]),output)
        self.assertFalse(output.exists())
        row['tagged_metadata_exclusions'][unknown]=unknown_review
        row['tagged_metadata_exclusions']['mods/not-in-tag.pw.toml']=review.copy()
        with self.assertRaisesRegex(UserError,'exactly match reviewed'):
            build(self.repo,self.catalog([row]),output)

    def test_indexed_mod_metadata_cannot_be_excluded(self):
        mod={'project_id':'fixture','version_id':'fixture.1','slug':'indexed','name':'Indexed synthetic fixture',
             'filename':'indexed.jar','kind':'mod','side':'both','url':'https://example.invalid/indexed.jar',
             'hashes':{'sha256':'0'*64},'dependencies':[]}
        row=self.snapshot(1,mods=[mod])
        relative='mods/indexed.pw.toml'
        row['tagged_metadata_exclusions']={relative:{'sha256':digest(self.repo/'packwiz'/relative),
                                                   'reason':'Synthetic attempted removal of an active indexed pin'}}
        output=self.base/'public'
        with self.assertRaisesRegex(UserError,'Indexed Packwiz files cannot be excluded'):
            build(self.repo,self.catalog([row]),output)
        self.assertFalse(output.exists())

    def test_exclusion_catalog_is_finite_and_only_explicit_mod_metadata(self):
        row=self.snapshot(1)
        review={'sha256':'0'*64,'reason':'Synthetic review'}
        for name in ('config/example.toml','mods/*.pw.toml','mods/../outside.pw.toml',
                     'shaderpacks/retired.pw.toml','mods/retired.jar'):
            with self.subTest(path=name):
                row['tagged_metadata_exclusions']={name:review}
                with self.assertRaisesRegex(UserError,'explicit mods'):
                    approved_catalog(self.catalog([row]))
        row['tagged_metadata_exclusions']={'mods/retired'+str(n)+'.pw.toml':review for n in range(33)}
        with self.assertRaisesRegex(UserError,'at most 32'):
            approved_catalog(self.catalog([row]))

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
