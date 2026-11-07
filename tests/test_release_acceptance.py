import unittest

from control_room.mod_manager import runtime_acceptance_passes


class ReleaseAcceptanceTests(unittest.TestCase):
    def test_kg_exception_is_exact_and_keeps_other_checks(self):
        pack_hash = '17d52a3b408dcdff8ae46d53412f0f3427a86547e1af7a6a978e807237384b3c'
        proposal = {'version': '0.2.0', 'pack_sha256': pack_hash}
        checks = dict.fromkeys(('dedicated_startup', 'client_startup', 'backup_restore', 'feature_smoke'), 'pass')
        receipt = {'pack_sha256': pack_hash, 'checks': checks | {'two_player_sync': 'unverified', 'kg_staging_join': 'pass'},
                   'owner_approval': '0.2.0 KG-only production and public Latest'}
        self.assertTrue(runtime_acceptance_passes(proposal, receipt))
        self.assertFalse(runtime_acceptance_passes(proposal | {'version': '0.2.1'}, receipt))
        self.assertFalse(runtime_acceptance_passes(proposal | {'pack_sha256': 'other'}, receipt | {'pack_sha256': 'other'}))
        for missing in ('backup_restore', 'feature_smoke', 'kg_staging_join'):
            self.assertFalse(runtime_acceptance_passes(proposal, receipt | {'checks': receipt['checks'] | {missing: 'pending'}}))
        self.assertFalse(runtime_acceptance_passes(proposal, receipt | {'owner_approval': None}))

    def test_owner_directed_release_can_use_prior_copied_world_play(self):
        proposal = {'version': '0.2.0', 'pack_sha256': '17d52a3b408dcdff8ae46d53412f0f3427a86547e1af7a6a978e807237384b3c'}
        checks = dict.fromkeys(('dedicated_startup', 'client_startup', 'backup_restore', 'feature_smoke'), 'pass')
        checks.update(two_player_sync='unverified', kg_staging_join='unverified', kg_copied_world_play='pass')
        receipt = {'pack_sha256': proposal['pack_sha256'], 'checks': checks,
                   'owner_approval': '0.2.0 KG-only production and public Latest',
                   'owner_release_direction': 'Release 0.2.0 without a repeat KG join'}
        self.assertTrue(runtime_acceptance_passes(proposal, receipt))
        self.assertFalse(runtime_acceptance_passes(proposal, receipt | {'owner_release_direction': None}))
        self.assertFalse(runtime_acceptance_passes(proposal, receipt | {'checks': checks | {'kg_copied_world_play': 'unverified'}}))

    def test_two_player_acceptance_remains_available_for_other_releases(self):
        proposal = {'version': '0.2.1', 'pack_sha256': 'different'}
        checks = dict.fromkeys(('dedicated_startup', 'client_startup', 'backup_restore', 'feature_smoke', 'two_player_sync'), 'pass')
        self.assertTrue(runtime_acceptance_passes(proposal, {'pack_sha256': 'different', 'checks': checks}))
