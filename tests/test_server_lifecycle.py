"""User-visible startup failures and backup resume outcomes, with no live JVM."""
import io
import tempfile
import unittest
from pathlib import Path

from control_room.backups import Backups
from control_room.common import Layout, UserError, read_json
from control_room.server import Server


class BoundedStorage:
    def reserve(self, additional, target=None):
        if type(additional) is not int or not 0 <= additional <= 16 * 1024**2:
            raise AssertionError("Unbounded test allocation")

    def checkpoint(self, *args):
        pass


class RecordedProcess:
    def __init__(self, text="", code=0):
        self.stdout = io.StringIO(text)
        self.code, self.exited = code, False

    def wait(self):
        self.exited = True
        return self.code

    def poll(self):
        return self.code if self.exited else None


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.layout = Layout(Path(self.temp.name))
        self.layout.create()
        self.server = Server(self.layout, BoundedStorage())

    def reader(self, text, state="starting", code=0):
        process = RecordedProcess(text, code)
        self.server.process, self.server.state = process, state
        self.server._reader(process)
        return process

    def test_native_fatal_with_zero_exit_is_failed_and_survives_dashboard_reopen(self):
        self.reader("[07:30:10] [main/ERROR] [minecraft/Main]: Failed to start the minecraft server\n")
        self.assertEqual(self.server.snapshot()["state"], "failed")
        self.assertIn("Failed to start", self.server.warning)
        receipt = read_json(self.server.owner_path)
        self.assertEqual(receipt["code"], 0)
        self.assertEqual(receipt["state"], "failed")
        reopened = Server(self.layout, BoundedStorage())
        self.assertEqual(reopened.snapshot()["state"], "failed")
        self.assertEqual(reopened.warning, self.server.warning)

    def test_silent_zero_exit_before_readiness_is_not_a_successful_start(self):
        self.reader("[main/INFO]: Loading registries\n")
        self.assertEqual(self.server.state, "failed")
        self.assertIn("before reporting readiness", self.server.warning)

    def test_graceful_stop_retains_normal_offline_outcome(self):
        self.reader("[Server thread/INFO]: All dimensions are saved\n", state="stopping")
        self.assertEqual(self.server.state, "offline")
        self.assertIsNone(self.server.warning)
        self.assertEqual(read_json(self.server.owner_path)["state"], "offline")

    def test_prior_process_output_cannot_promote_or_fail_a_new_process(self):
        prior = RecordedProcess("Done (1.0s)! For help, type help\n[main/ERROR]: Failed to start the minecraft server\n")
        current = RecordedProcess()
        self.server.process, self.server.state = current, "starting"
        self.server.identity = {"pid": 123, "created": 1234}
        self.server._reader(prior)
        self.assertEqual(self.server.state, "starting")
        self.assertEqual(self.server.identity["pid"], 123)
        self.assertFalse(self.server.owner_path.exists())
        self.assertTrue(self.server.console())  # Old output remains inspectable.

    def test_ready_line_after_native_fatal_does_not_erase_failure(self):
        self.server.state = "starting"
        self.server.record("[main/ERROR]: Failed to start the minecraft server")
        self.server.record('Done (1.0s)! For help, type "help"')
        self.assertEqual(self.server.state, "failed")

    def test_unrelated_class_warning_does_not_fail_a_ready_server(self):
        self.server.state, self.server.process = "starting", RecordedProcess()
        self.server.record("[main/WARN]: Error loading optional client-only mixin target")
        self.server.record('Done (1.0s)! For help, type "help"')
        self.assertEqual(self.server.wait_ready(.1)["state"], "online")

    def test_chat_quoting_a_failure_message_is_not_a_native_failure(self):
        self.server.state, self.server.process = "online", RecordedProcess()
        self.server.record("[Server thread/INFO]: <Player> Failed to start the minecraft server")
        self.assertEqual(self.server.state, "online")
        self.assertIsNone(self.server.warning)

    def test_readiness_timeout_does_not_terminate_or_replace_live_process(self):
        process = RecordedProcess()
        self.server.state, self.server.process = "starting", process
        with self.assertRaisesRegex(UserError, "not stopped or relaunched"):
            self.server.wait_ready(.01)
        self.assertIs(self.server.process, process)
        self.assertEqual(self.server.state, "starting")
        self.assertIsNone(process.poll())


class ResumedServer:
    def __init__(self, fail):
        self.live, self.fail = True, fail

    def running(self):
        return self.live

    def stop(self, **kwargs):
        self.live = False

    def start(self, **kwargs):
        pass  # A Java launch alone does not prove readiness.

    def wait_ready(self):
        if self.fail:
            raise UserError("Native registry initialization failed")
        self.live = True
        return {"state": "online"}


class BackupResumeTests(unittest.TestCase):
    def test_start_validation_failure_does_not_erase_the_verified_backup(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(Path(root)); layout.create()
            (layout.world / "level.dat").write_bytes(b"saved synthetic fixture")
            server = ResumedServer(fail=False)
            def reject_start(**kwargs):
                raise UserError("Installed artifact hash differs")
            server.start = reject_start
            backups = Backups(layout, BoundedStorage(), server)
            with self.assertRaisesRegex(UserError, "is verified, but Minecraft did not resume"):
                backups.create()
            receipt = backups.list()[0]
            self.assertEqual(receipt["integrity"], "verified")
            self.assertIn("artifact hash", receipt["resume"]["error"])
            self.assertFalse(server.running())

    def test_valid_archive_and_failed_resume_are_separate_preserved_results(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(Path(root)); layout.create()
            (layout.world / "level.dat").write_bytes(b"saved synthetic fixture")
            backups = Backups(layout, BoundedStorage(), ResumedServer(fail=True))
            with self.assertRaisesRegex(UserError, "is verified, but Minecraft did not resume"):
                backups.create()
            receipt = backups.list()[0]
            self.assertEqual(receipt["integrity"], "verified")
            self.assertEqual(receipt["resume"]["state"], "failed")
            backups.verify_archive(backups.path(receipt["id"]))

    def test_resume_success_requires_observed_minecraft_readiness(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(Path(root)); layout.create()
            (layout.world / "level.dat").write_bytes(b"saved synthetic fixture")
            backups = Backups(layout, BoundedStorage(), ResumedServer(fail=False))
            receipt = backups.create()
            self.assertEqual(receipt["resume"]["state"], "online")
            self.assertEqual(backups.list()[0]["resume"]["state"], "online")
