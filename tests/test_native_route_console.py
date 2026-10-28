"""Real console dispatch boundaries; no native world or cable acceptance."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from control_room.common import Layout, UserError, write_json
from control_room.server import Server


class NativeRouteConsoleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='awft-native-route-console-')
        self.addCleanup(self.temp.cleanup)
        self.layout = Layout(Path(self.temp.name))
        self.layout.create()
        self.server = Server(self.layout, object())
        self.sha = 'a' * 64

    def private(self):
        write_json(self.layout.state / 'artistic-owner.json',
                   {'format': 'awft-artistic-stage:1', 'home': str(self.layout.home)})
        self.layout.save_settings(self.layout.settings() | {'permanent_world': False, 'port': 25575})

    def chain(self, operation):
        return 'awftchains ' + operation + ' chains-' + self.sha[:16] + ' ' + self.sha

    def bridge(self):
        return 'awftbridgetop inspect bridge-topside-inspection-' + self.sha[:16] + ' ' + self.sha

    def test_create_and_prepare_create_require_explicit_confirmation(self):
        self.private()
        with patch.object(self.server, '_write') as write:
            for operation in ('create', 'prepare-create'):
                with self.subTest(operation=operation):
                    command = self.chain(operation)
                    with self.assertRaisesRegex(UserError, 'Confirm'):
                        self.server.command(command)
                    self.server.command(command, confirmed=True)
                    self.assertEqual(write.call_args.args, (command,))
            self.assertEqual(write.call_count, 2)

    def test_current_inspection_and_restart_dispatch_without_mutation_confirmation(self):
        self.private()
        with patch.object(self.server, '_write') as write:
            for command in (self.chain('inspect'), self.chain('verify-restart'), self.bridge(),
                            'awftchains status', 'awftbridgetop status'):
                self.server.command(command)
                self.assertEqual(write.call_args.args, (command,))
            self.assertEqual(write.call_count, 5)

    def test_both_families_refuse_missing_foreign_or_permanent_stage(self):
        with patch.object(self.server, '_write') as write:
            for command in (self.chain('prepare-create'), self.bridge(), 'awftchains status'):
                with self.assertRaises(UserError):
                    self.server.command(command, confirmed=True)
            self.private()
            for settings in ({'port': 25565}, {'port': 25575, 'permanent_world': True}):
                self.layout.save_settings(self.layout.settings() | settings)
                for command in (self.chain('create'), self.bridge()):
                    with self.assertRaises(UserError):
                        self.server.command(command, confirmed=True)
            self.private()
            write_json(self.layout.state / 'artistic-owner.json',
                       {'format': 'awft-artistic-stage:1', 'home': str(self.layout.home / 'foreign')})
            with self.assertRaises(UserError):
                self.server.command(self.chain('prepare-create'), confirmed=True)
            write.assert_not_called()

    def test_cancellation_requires_confirmation_and_exact_command(self):
        self.private()
        with patch.object(self.server, '_write') as write:
            for command in ('awftchains cancel', 'awftbridgetop cancel'):
                with self.assertRaisesRegex(UserError, 'Confirm'):
                    self.server.command(command)
                self.server.command(command, confirmed=True)
            self.assertEqual(write.call_count, 2)

    def test_route_control_never_admits_arbitrary_entity_or_glue_commands(self):
        self.private()
        with patch.object(self.server, '_write') as write:
            good = self.chain('prepare-create')
            invalid = (good + ' extra', good.replace(self.sha, 'not-a-hash'),
                       good.replace('chains-', '../'), good + '\nstop',
                       'awftchains summon minecraft:boat',
                       self.bridge().replace(' inspect ', ' retire '),
                       self.bridge().replace('bridge-topside-inspection-', 'bridge-refinement-admission-'))
            for command in invalid:
                with self.subTest(command=command), self.assertRaises(UserError):
                    self.server.command(command, confirmed=True)
            write.assert_not_called()


if __name__ == '__main__':
    unittest.main()
