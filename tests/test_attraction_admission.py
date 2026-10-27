"""Synthetic custody/schema tests; these never launch Java or a Minecraft world."""
import copy
import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from control_room.common import UserError
from tools import attraction_admission as admission


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class AdmissionFixture:
    def __init__(self, home):
        self.home = Path(home)
        self.directory = self.home / 'dashboard/settlement'
        self.hub = self.directory / 'synthetic-hub'
        self.hub.mkdir(parents=True)
        self.authoring = self.home / 'fixture-sources/authoring.py'
        self.native = self.home / 'fixture-sources/AttractionSupport.java'
        self.authoring.parent.mkdir()
        self.authoring.write_text('# synthetic authoring source\n')
        self.native.write_text('// synthetic native source; no compiled runtime proof\n')
        self.mods = self.home / 'server/mods'
        self.mods.mkdir(parents=True)
        self.backup = self.home / 'backups/synthetic-backup.zip'
        self.backup.parent.mkdir()
        self.backup.write_bytes(b'synthetic immutable backup identity only')
        self.plan = {'format': 'awft-native-settlement:1', 'seed': '42',
                     'world_path': 'synthetic-world', 'backup_sha256': sha(self.backup.read_bytes()),
                     'palette': ['minecraft:stone'], 'blocks': [[1300, 69, -1000, 0]],
                     'commands': [], 'block_entities': []}
        self.before = copy.deepcopy(self.plan)
        self.before['palette'] = ['minecraft:air']
        self.provenance = []
        for i in range(15):
            filename = 'fixed-' + str(i) + '.json'
            path = self.directory / filename if i < 10 else self.directory / 'synthetic-details' / filename
            self.write(path, {'format': 'awft-native-settlement:1',
                              'palette': ['minecraft:air'], 'blocks': [[1100 + i, 70, -1100, 0]]})
            record = {'file': filename, 'sha256': sha(path.read_bytes())}
            if i < 10:
                record['native_verification'] = {'finished': 'synthetic', 'failures': 0, 'receipt_sha256': 'a' * 64}
            else:
                record['role'] = 'Completed detail exclusion'
            self.provenance.append(record)
        for i in range(4):
            name = 'synthetic-mod-' + str(i) + '.jar'
            (self.mods / name).write_bytes(('synthetic pinned dependency ' + str(i)).encode())
            self.provenance.append({'role': 'Read-only pinned native API/recipe evidence',
                                    'file': name, 'sha256': sha((self.mods / name).read_bytes())})
        self.bridge = self.mods / 'synthetic-future-bridge.jar'
        class_bytes = b'synthetic class identity; not a loadable native class'
        with zipfile.ZipFile(self.bridge, 'w') as archive:
            archive.writestr(admission.CLASS_FILE, class_bytes)
        self.manifest = {'format': 'awft-settlement-attractions:1', 'placements': 1,
                         'plan_file': 'plan.json', 'preconditions_file': 'before.json',
                         'backup_id': 'synthetic-backup', 'provenance': self.provenance,
                         'source_sha256': sha(self.authoring.read_bytes())}
        self.build = {'format': 'awft-attraction-native-build:1',
                      'candidate_version': 'future.synthetic', 'bridge_version': '0.future.synthetic',
                      'pack_sha256': 'b' * 64, 'native_source_sha256': sha(self.native.read_bytes()),
                      'bridge_jar_file': 'server/mods/' + self.bridge.name,
                      'bridge_jar_sha256': sha(self.bridge.read_bytes()),
                      'attraction_class_sha256': sha(class_bytes)}
        self.build_file = self.directory / 'synthetic-build.json'
        self.before_receipt = self.directory / 'synthetic-before-result.json'
        self.after_receipt = self.directory / 'synthetic-after-result.json'
        self.write(self.directory / 'backup-receipt.json', {
            'id': 'synthetic-backup', 'sha256': self.plan['backup_sha256'], 'verified': True})
        self.write(self.home / 'packwiz/active.json', {
            'version': 'future.synthetic', 'pack_sha256': 'b' * 64})
        self.write(self.home / 'server/installed.json', {
            'pack_version': 'future.synthetic', 'pack_sha256': 'b' * 64,
            'files': [p.name for p in self.mods.iterdir()]})
        self.save()

    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, separators=(',', ':')) + '\n', encoding='utf-8')

    def terminal(self, path, plan_sha):
        before=path==self.before_receipt
        self.write(path, {'operation': 'verify', 'plan_sha256': plan_sha,
                          'blocks': self.manifest['placements'], 'failures': 0,
                          'status': admission.VERIFIED_STATUS,
                          'started': '2026-10-27T00:00:00Z' if before else '2026-10-27T00:02:00Z',
                          'finished': '2026-10-27T00:01:00Z' if before else '2026-10-27T00:03:00Z'})
        Path(str(path) + '.complete').write_text(sha(path.read_bytes()))

    def save(self):
        self.write(self.hub / 'plan.json', self.plan)
        self.write(self.hub / 'before.json', self.before)
        self.manifest.update({'plan_sha256': sha((self.hub / 'plan.json').read_bytes()),
                              'preconditions_sha256': sha((self.hub / 'before.json').read_bytes()),
                              'expected_previous': [
                                  {'position': row[:3], 'previous': self.before['palette'][old[3]],
                                   'replacement': self.plan['palette'][row[3]]}
                                  for row, old in zip(self.plan['blocks'], self.before['blocks'])]})
        self.write(self.hub / 'manifest.json', self.manifest)
        self.write(self.build_file, self.build)
        self.terminal(self.before_receipt, self.manifest['preconditions_sha256'])
        self.terminal(self.after_receipt, self.manifest['plan_sha256'])

    def args(self):
        return (self.home, self.hub / 'manifest.json', self.build_file,
                self.before_receipt, self.after_receipt)


class AttractionAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.fixture = AdmissionFixture(self.temp.name)
        self.patches = [patch.object(admission, 'NATIVE_SOURCE', self.fixture.native),
                        patch.object(admission, 'AUTHORING_SOURCE', self.fixture.authoring)]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def envelope(self):
        return admission.build_envelope(*self.fixture.args())[0]

    def test_exact_future_inputs_bind_every_dependency_and_do_not_write(self):
        value = self.envelope()
        self.assertEqual(value['permitted_actions'], ['inspect', 'admit'])
        self.assertEqual(value['unsupported_actions'], ['setup', 'assemble', 'connect', 'commission', 'run'])
        self.assertEqual(len(value['geometry']), 15)
        self.assertEqual(len(value['native_mods']), 4)
        self.assertEqual(value['native_class_sha256'], self.fixture.build['attraction_class_sha256'])
        self.assertFalse(list(self.fixture.directory.glob('attraction-admission-*')))
        self.assertFalse((self.fixture.directory / 'plan.json').exists())

    def test_no_future_build_receipt_cannot_be_manufactured(self):
        self.fixture.build_file.unlink()
        with self.assertRaisesRegex(UserError, 'Missing'):
            self.envelope()

    def test_both_native_verification_markers_and_zero_failures_are_required(self):
        for path in (self.fixture.before_receipt, self.fixture.after_receipt):
            with self.subTest(receipt=path.name):
                marker = Path(str(path) + '.complete')
                marker.unlink()
                with self.assertRaisesRegex(UserError, 'completion marker'):
                    self.envelope()
                self.fixture.save()
                row = json.loads(path.read_text()); row['failures'] = 1
                self.fixture.write(path, row); marker.write_text(sha(path.read_bytes()))
                with self.assertRaisesRegex(UserError, 'has not passed'):
                    self.envelope()
                self.fixture.save()

    def test_replaced_current_backup_candidate_or_actual_jar_fails_closed(self):
        for key, path in (
            ('sha256', self.fixture.directory / 'backup-receipt.json'),
            ('version', self.fixture.home / 'packwiz/active.json'),
            ('pack_version', self.fixture.home / 'server/installed.json')):
            original = path.read_bytes(); row = json.loads(original); row[key] = 'changed'
            self.fixture.write(path, row)
            with self.subTest(key=key), self.assertRaises(UserError):
                self.envelope()
            path.write_bytes(original)
        self.fixture.bridge.write_bytes(b'changed actual installed bridge')
        with self.assertRaisesRegex(UserError, 'digest differs'):
            self.envelope()

    def test_zero_failure_cancellation_is_not_a_completed_native_verification(self):
        path=self.fixture.after_receipt;row=json.loads(path.read_text())
        row['status']='cancelled';self.fixture.write(path,row)
        Path(str(path)+'.complete').write_text(sha(path.read_bytes()))
        with self.assertRaisesRegex(UserError,'has not passed'):
            self.envelope()

    def test_reversed_before_and_after_execution_or_missing_interval_is_refused(self):
        path=self.fixture.before_receipt;row=json.loads(path.read_text())
        row['finished']='2026-10-27T00:04:00Z';self.fixture.write(path,row)
        Path(str(path)+'.complete').write_text(sha(path.read_bytes()))
        with self.assertRaisesRegex(UserError,'must precede'):
            self.envelope()
        del row['started'];self.fixture.write(path,row)
        Path(str(path)+'.complete').write_text(sha(path.read_bytes()))
        with self.assertRaisesRegex(UserError,'execution interval'):
            self.envelope()

    def test_actual_source_and_native_class_identity_must_match_build(self):
        self.fixture.native.write_text('// changed since build')
        with self.assertRaisesRegex(UserError, 'source changed'):
            self.envelope()
        self.fixture.native.write_text('// synthetic native source; no compiled runtime proof\n')
        self.fixture.build['attraction_class_sha256'] = '0' * 64; self.fixture.save()
        with self.assertRaisesRegex(UserError, 'class differs'):
            self.envelope()

    def test_duplicate_targets_audit_and_noninteger_rows_are_refused(self):
        self.fixture.plan['blocks'] *= 2; self.fixture.before['blocks'] *= 2
        self.fixture.manifest['placements'] = 2; self.fixture.save()
        with self.assertRaisesRegex(UserError, 'Duplicate hub'):
            self.envelope()
        self.fixture.plan['blocks'] = [[1300, 69, -1000, -1]]; self.fixture.before['blocks'] = [[1300, 69, -1000, 0]]
        self.fixture.manifest['placements'] = 1
        self.fixture.write(self.fixture.hub / 'plan.json', self.fixture.plan)
        with self.assertRaisesRegex(UserError, 'Invalid exact'):
            self.envelope()

    def test_duplicate_audit_cannot_hide_an_original_inventory_target(self):
        self.fixture.manifest['expected_previous'] *= 2
        self.fixture.write(self.fixture.hub / 'manifest.json', self.fixture.manifest)
        with self.assertRaisesRegex(UserError, 'Duplicate or invalid previous'):
            self.envelope()

    def test_fixed_completed_air_is_an_exclusion(self):
        row = self.fixture.provenance[0]
        path = self.fixture.directory / row['file']
        self.fixture.write(path, {'palette': ['minecraft:air'], 'blocks': [[1300, 69, -1000, 0]]})
        row['sha256'] = sha(path.read_bytes()); self.fixture.save()
        with self.assertRaisesRegex(UserError, 'intersects completed fixed geometry'):
            self.envelope()

    def test_commands_or_prior_block_entity_writes_cannot_enter_admission(self):
        for doc, key, value in ((self.fixture.plan, 'commands', ['say unsafe']),
                                (self.fixture.before, 'block_entities', [{'pos': [1300, 69, -1000], 'nbt': '{}'}])):
            doc[key] = value; self.fixture.save()
            with self.assertRaisesRegex(UserError, 'never accepts'):
                self.envelope()
            doc[key] = []

    def test_owned_reference_rejects_escape_and_declared_oversize(self):
        with self.assertRaisesRegex(UserError, 'inside the owned runtime'):
            admission.reference(self.fixture.home, self.fixture.home.parent / 'outside')
        with self.assertRaisesRegex(UserError, 'oversized'):
            admission.reference(self.fixture.home, self.fixture.build_file, limit=1)

    def test_preparation_is_guarded_unique_and_never_an_install(self):
        with patch.object(admission, 'utcnow', return_value='synthetic-fixed-time'), \
                patch.object(admission.Storage, 'reserve') as reserve:
            value = admission.prepare(*self.fixture.args())
            reserve.assert_called_once_with(admission.MAX_OUTPUT, target=Path(value['directory']))
            path = Path(value['directory'])
            self.assertEqual({p.name for p in path.iterdir()}, {'admission.json', 'authoring_source.py', 'AttractionSupport.java'})
            self.assertEqual(sha((path / 'admission.json').read_bytes()), value['admission_sha256'])
            self.assertEqual(value['native_action'], 'Not performed')
            self.assertFalse((self.fixture.directory / 'plan.json').exists())
            with self.assertRaisesRegex(UserError, 'Preserve'):
                admission.prepare(*self.fixture.args())


if __name__ == '__main__':
    unittest.main()
