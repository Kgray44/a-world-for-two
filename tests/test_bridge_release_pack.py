from pathlib import Path
import hashlib,json,tempfile,unittest
from control_room.common import UserError
from tools.artistic_bridge_topside_inspection import current_pack


class BridgeReleasePackTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='awft-release-pack-');self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name).resolve();self.version='0.1.0-candidate.47'
        self.release=self.home/'packwiz/releases'/self.version/'pack.toml';self.release.parent.mkdir(parents=True)
        self.release.write_bytes(b'name = "fixture"\n');self.sha=hashlib.sha256(self.release.read_bytes()).hexdigest()
        (self.home/'server').mkdir()
        self.metadata()
    def metadata(self):
        (self.home/'packwiz/active.json').write_text(json.dumps({'version':self.version,'pack_sha256':self.sha}),encoding='utf8')
        (self.home/'server/installed.json').write_text(json.dumps({'pack_version':self.version,'pack_sha256':self.sha}),encoding='utf8')
    def test_genuine_versioned_release_works_without_any_flat_copy(self):
        self.assertFalse((self.home/'packwiz/pack.toml').exists())
        self.assertEqual(current_pack(self.home,self.version),(self.release,self.sha))
    def test_metadata_or_release_byte_mismatch_refuses(self):
        (self.home/'server/installed.json').write_text(json.dumps({'pack_version':self.version,'pack_sha256':'0'*64}),encoding='utf8')
        with self.assertRaises(UserError):current_pack(self.home,self.version)
        self.metadata();self.release.write_bytes(b'changed')
        with self.assertRaises(UserError):current_pack(self.home,self.version)
    def test_traversal_and_windows_trailing_dot_versions_refuse(self):
        for value in ('../outside','a/../../outside','a\\outside','..','safe.'):
            with self.subTest(value=value),self.assertRaises(UserError):current_pack(self.home,value)
    def test_real_symbolic_manifest_is_refused_when_supported(self):
        target=self.home/'other.toml';target.write_bytes(self.release.read_bytes());self.release.unlink()
        try:self.release.symlink_to(target)
        except OSError as error:self.skipTest('Host does not permit fixture symlink: '+str(error))
        with self.assertRaises(UserError):current_pack(self.home,self.version)
