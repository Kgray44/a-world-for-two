"""Source admission checks only; no server command or hydraulic test is run."""
import datetime as dt
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from control_room.common import UserError
from tools.artistic_fountain_commission import (
    BACKUP_ID, BACKUP_SHA, BLOCKS, CANDIDATE, PACK_SHA, PLAN_SHA, STATUS,
    check_context, check_proof, evidence, owned, sha,
)


NOW = dt.datetime(2026, 10, 27, 20, 15, tzinfo=dt.timezone.utc)


def proof():
    return {'operation': 'verify', 'status': STATUS, 'plan_sha256': PLAN_SHA,
            'blocks': BLOCKS, 'failures': 0, 'cleanup_required': False,
            'temporary_tickets_remaining': 0, 'pending_shared_chunk_futures': 0,
            'started': (NOW-dt.timedelta(seconds=20)).isoformat(),
            'finished': (NOW-dt.timedelta(seconds=10)).isoformat()}


def context(home):
    world = str(home/'world/RosewaterArtistic')
    return [
        {'format': 'awft-artistic-stage:1', 'home': str(home), 'minecraft_port': 25575,
         'active_world_path': world, 'pack_sha256': PACK_SHA,
         'backup': BACKUP_ID, 'backup_sha256': BACKUP_SHA},
        {'version': CANDIDATE, 'pack_sha256': PACK_SHA},
        {'pack_version': CANDIDATE, 'pack_sha256': PACK_SHA},
        {'port': 25575, 'permanent_world': False},
        {'world_path': world},
        {'verified': True, 'id': BACKUP_ID, 'sha256': BACKUP_SHA},
    ]


class FountainCommissionTests(unittest.TestCase):
    def test_exact_complete_zero_failure_receipt_passes_the_pure_validator(self):
        check_proof(proof(), NOW)

    def test_wrong_operation_plan_or_partial_count_is_refused(self):
        for field, value in [('operation', 'place'), ('plan_sha256', '0'*64),
                             ('blocks', 1), ('status', 'test passed')]:
            bad = proof(); bad[field] = value
            with self.subTest(field=field), self.assertRaises(UserError):
                check_proof(bad, NOW)

    def test_every_failure_cleanup_and_ticket_signal_is_fail_closed(self):
        for field, value in [('failures', 1), ('failures', False),
                             ('cleanup_required', True), ('temporary_tickets_remaining', 1),
                             ('pending_shared_chunk_futures', 1), ('cleanup_failures', 1),
                             ('error', None)]:
            bad = proof(); bad[field] = value
            with self.subTest(field=field), self.assertRaises(UserError):
                check_proof(bad, NOW)

    def test_stale_future_naive_or_out_of_order_proof_is_refused(self):
        for finished in [(NOW-dt.timedelta(minutes=31)).isoformat(),
                         (NOW+dt.timedelta(seconds=1)).isoformat(), '2026-10-27T20:14:59', 'garbage']:
            bad = proof(); bad['finished'] = finished
            with self.subTest(finished=finished), self.assertRaises(UserError):
                check_proof(bad, NOW)
        bad = proof(); bad['started'] = NOW.isoformat()
        with self.assertRaises(UserError):
            check_proof(bad, NOW)

    def test_exact_owner_candidate_world_and_checkpoint_context(self):
        with TemporaryDirectory() as temporary:
            home = Path(temporary).absolute()
            check_context(home, *context(home))
            for index, field, value in [(0, 'home', str(home/'foreign')),
                    (0, 'minecraft_port', 25565), (1, 'pack_sha256', '0'*64),
                    (2, 'pack_version', '0.1.0-candidate.41'), (3, 'permanent_world', True),
                    (4, 'world_path', str(home/'official')), (5, 'sha256', '0'*64)]:
                docs = context(home); docs[index][field] = value
                with self.subTest(field=field), self.assertRaises(UserError):
                    check_context(home, *docs)

    def test_finite_regular_owned_evidence_is_hash_and_length_bound(self):
        with TemporaryDirectory() as temporary:
            home = Path(temporary).absolute(); p = home/'native.json'; raw = b'{"proof":"synthetic fixture only"}'
            p.write_bytes(raw)
            _, actual, ref = evidence(home, p, 1024, sha(raw))
            self.assertEqual(actual, raw)
            self.assertEqual(ref, {'path': 'native.json', 'bytes': len(raw), 'sha256': sha(raw)})
            with self.assertRaises(UserError):
                evidence(home, p, len(raw)-1)
            with self.assertRaises(UserError):
                evidence(home, p, 1024, '0'*64)

    def test_foreign_traversal_directory_and_empty_evidence_are_refused(self):
        with TemporaryDirectory() as temporary:
            home = Path(temporary).absolute(); (home/'empty.json').write_bytes(b'')
            with self.assertRaises(UserError):
                owned(home, home.parent/'foreign.json')
            with self.assertRaises(UserError):
                owned(home, home/'nested/../empty.json')
            with self.assertRaises(UserError):
                owned(home, home)
            with self.assertRaises(UserError):
                evidence(home, home/'empty.json', 1024)


if __name__ == '__main__':
    unittest.main()
