from __future__ import annotations

import copy
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from control_room.backups import Backups
from control_room.common import GiB, Layout, UserError, digest, read_json, write_json
from control_room.server import Server
from control_room.service import RestartPolicy, ServiceServer, Supervisor, internal_command
from control_room.settings import format_properties, properties
from control_room.storage import Storage
from control_room.web import Application, HTTPServer, make_handler
from tools import snowfall, snowfall_host


class BoundedStorage:
    def reserve(self, additional, target=None):
        if type(additional) is not int or additional < 0:
            raise AssertionError("Unbounded fixture allocation")
        return {"allowed": True}

    def checkpoint(self, *args, **kwargs):
        pass


class SnowfallFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="snowfall-")
        self.root = Path(self.temp.name)
        self.layout = Layout(self.root / "source")
        self.layout.create()
        self.storage = BoundedStorage()
        self.storage_patch = patch("tools.snowfall.Storage", return_value=self.storage)
        self.storage_patch.start()
        self.addCleanup(self.storage_patch.stop)
        self.addCleanup(self.temp.cleanup)
        self.world = self.layout.world / "SeparateSave"
        self.world.mkdir()
        (self.world / "level.dat").write_bytes(b"disposable world fixture")
        (self.world / "DIM-1").mkdir()
        (self.world / "DIM-1/r.0.0.mca").write_bytes(b"all dimensions retained")
        (self.world / "playerdata").mkdir()
        (self.world / "playerdata/player.dat").write_bytes(b"inventories and progress")
        (self.layout.server / "mods").mkdir()
        (self.layout.server / "mods/fixture.jar").write_bytes(b"synthetic bytes, no downloaded jar")
        pack_hash = "a" * 64
        write_json(self.layout.server / "installed.json", {"neoforge": "21.1.262", "pack_sha256": pack_hash,
                   "files": {"fixture.jar": digest(self.layout.server / "mods/fixture.jar")}})
        write_json(self.layout.home / "packwiz/active.json", {"version": "fixture", "pack_sha256": pack_hash})
        self.lock = {"minecraft": "1.21.1", "neoforge": "21.1.262", "mods": [{"filename": "fixture.jar", "side": "server", "kind": "mod"}]}
        write_json(self.layout.releases / "fixture/lock.json", self.lock)
        write_json(self.layout.state / "server-process.json", {"pid": 0, "created": 1, "state": "historical"})
        write_json(self.layout.state / "atlas-waypoints.json", {"places": ["retained"]})
        self.layout.save_settings({"prism_path": r"C:\Prism\Prism.exe", "java": r"C:\Java\java.exe"})
        (self.layout.server / "server.properties").write_text(format_properties({
            "level-name": "D:/previous/world/SeparateSave", "online-mode": True, "enable-rcon": False,
            "server-ip": "127.0.0.1", "white-list": True, "enforce-whitelist": True}))

    def bundle(self):
        target = self.root / "bundle"
        result = snowfall.export(self.layout, target, GiB, "EXPORT STOPPED " + str(self.layout.home))
        return target, result["manifest_sha256"]


class MigrationTests(SnowfallFixture):
    def test_inventory_preserves_separate_world_dimensions_playerdata_mods_and_atlas(self):
        result = snowfall.inventory(self.layout, GiB)
        paths = {r["path"] for r in result["files"]}
        self.assertIn("world/SeparateSave/DIM-1/r.0.0.mca", paths)
        self.assertIn("world/SeparateSave/playerdata/player.dat", paths)
        self.assertIn("server/mods/fixture.jar", paths)
        self.assertIn("dashboard/atlas-waypoints.json", paths)
        self.assertNotIn("dashboard/server-process.json", paths)
        self.assertEqual(sum(r["size"] for r in result["files"]), result["source_bytes"])

    def test_inventory_wrong_game_or_loader_and_missing_mod_are_refused(self):
        path = self.layout.releases / "fixture/lock.json"
        for value in ({"minecraft": "1.21.2", "neoforge": "21.1.262"}, {"minecraft": "1.21.1", "neoforge": "21.1.261"}):
            write_json(path, value)
            with self.assertRaises(UserError):
                snowfall.inventory(self.layout, GiB)
        write_json(path, self.lock)
        (self.layout.server / "mods/fixture.jar").unlink()
        with self.assertRaisesRegex(UserError, "integrity"):
            snowfall.inventory(self.layout, GiB)

    def test_inventory_allocation_is_bounded(self):
        for bound in (0, -1, 1, None):
            with self.assertRaises(UserError):
                snowfall.inventory(self.layout, bound)

    def test_cross_platform_traversal_is_rejected(self):
        for path in ("/tmp/file", "../outside", "world/../outside", "C:/secret", r"world\..\outside", "world//file", "world/./file"):
            with self.subTest(path=path), self.assertRaises(UserError):
                snowfall.safe_relative(path)

    def test_possible_credentials_require_review_without_exposing_values(self):
        secret = self.layout.server / "config/provider.toml"
        secret.parent.mkdir()
        secret.write_text('api_key="example-private-credential"\n')
        with self.assertRaises(UserError) as error:
            snowfall.inventory(self.layout, GiB)
        self.assertNotIn("example-private-credential", str(error.exception))

    def test_known_machine_secrets_are_excluded(self):
        write_json(self.layout.state / "credentials.json", {"example": "secret fixture"})
        result = snowfall.inventory(self.layout, GiB)
        self.assertNotIn("dashboard/credentials.json", {r["path"] for r in result["files"]})
        self.assertTrue(any(x["path"] == "dashboard/credentials.json" for x in result["excluded"]))

    def test_export_needs_exact_stopped_source_confirmation(self):
        with self.assertRaises(UserError):
            snowfall.export(self.layout, self.root / "bundle", GiB, "yes")
        self.assertFalse((self.root / "bundle").exists())

    def test_live_recorded_process_cannot_be_exported(self):
        import psutil
        process = psutil.Process()
        write_json(self.layout.state / "server-process.json", {"pid": process.pid, "created": process.create_time()})
        with self.assertRaisesRegex(UserError, "still running"):
            self.bundle()

    def test_stage_is_fresh_inactive_preserves_world_bytes_and_rebinds_host_state(self):
        bundle, sha = self.bundle()
        target = self.root / "ubuntu-stage"
        result = snowfall.stage(bundle, target, sha, GiB)
        self.assertFalse(result["activated"])
        self.assertEqual((target / "world/SeparateSave/level.dat").read_bytes(), (self.world / "level.dat").read_bytes())
        self.assertFalse((target / "dashboard/server-process.json").exists())
        settings = Layout(target).settings()
        self.assertEqual(settings["server_backend"], "unix-service")
        self.assertEqual(settings["prism_path"], "")
        self.assertFalse(settings["service_autostart"])
        self.assertIn("eula=false", (target / "server/eula.txt").read_text())
        props = properties((target / "server/server.properties").read_text())
        self.assertEqual(props["level-name"], (target / "world/SeparateSave").as_posix())
        self.assertTrue(snowfall.verify_staged(Layout(target)))
        with self.assertRaises(UserError):
            snowfall.stage(bundle, target, sha, GiB)

    def test_existing_and_overlapping_destinations_are_never_written(self):
        for destination in (self.layout.home, self.layout.home / "new", self.root):
            with self.assertRaises(UserError):
                snowfall.new_destination(destination, self.layout.home)

    def test_changed_missing_and_unexpected_files_fail_verification(self):
        bundle, sha = self.bundle()
        target = bundle / "data/world/SeparateSave/level.dat"
        target.write_bytes(b"corrupted")
        with self.assertRaises(UserError):
            snowfall.verify(bundle, sha)
        target.write_bytes((self.world / "level.dat").read_bytes())
        target.unlink()
        with self.assertRaises((UserError, OSError)):
            snowfall.verify(bundle, sha)
        target.write_bytes((self.world / "level.dat").read_bytes())
        (bundle / "data/unexpected").write_bytes(b"extra")
        with self.assertRaises(UserError):
            snowfall.verify(bundle, sha)

    def test_mismatched_manifest_identity_and_duplicates_are_rejected(self):
        bundle, sha = self.bundle()
        with self.assertRaises(UserError):
            snowfall.verify(bundle, "b" * 64)
        value = read_json(bundle / "manifest.json")
        value["files"].append(value["files"][0])
        write_json(bundle / "manifest.json", value)
        with self.assertRaisesRegex(UserError, "Duplicate"):
            snowfall.verify(bundle, digest(bundle / "manifest.json"))

    def test_changed_source_preserves_incomplete_export(self):
        original = snowfall.inventory
        calls = 0
        def changing(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                (self.world / "new.dat").write_bytes(b"new data")
            return original(*args)
        with patch.object(snowfall, "inventory", side_effect=changing), self.assertRaises(UserError):
            self.bundle()
        self.assertTrue((self.root / "bundle/INCOMPLETE.json").is_file())
        self.assertFalse((self.root / "bundle/COMPLETE.json").exists())

    def test_insufficient_storage_prevents_destination_creation(self):
        self.storage.reserve = Mock(side_effect=UserError("reserve rejected"))
        with self.assertRaises(UserError):
            self.bundle()
        self.assertFalse((self.root / "bundle").exists())

    @unittest.skipUnless(os.name == "posix", "Native Linux link test")
    def test_linked_files_and_directories_are_rejected(self):
        (self.world / "link").symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(UserError, "link"):
            snowfall.inventory(self.layout, GiB)


class ServiceTests(SnowfallFixture):
    def test_bounded_restart_policy_is_durable_across_supervisor_recreation(self):
        policy = RestartPolicy(self.layout)
        self.assertTrue(policy.admit(1000))
        self.assertFalse(policy.admit(1001))
        self.assertTrue(RestartPolicy(self.layout).admit(1031))
        self.assertTrue(RestartPolicy(self.layout).admit(1062))
        self.assertFalse(RestartPolicy(self.layout).admit(1100))
        self.assertTrue(RestartPolicy(self.layout).admit(2000))

    def test_invalid_restart_settings_fail_closed(self):
        self.layout.save_settings({"service_restart_limit": 100})
        with self.assertRaises(UserError):
            RestartPolicy(self.layout).admit(1000)

    def test_service_routes_keep_console_allowlist_and_confirmations(self):
        native = Server(self.layout, self.storage)
        native._write = Mock()
        owner = Supervisor(self.layout, self.storage, native)
        for request in ({"action": "shell", "command": "id"}, {"action": "write", "command": "execute run stop"},
                        {"action": "command", "command": "op KG", "confirmed": False},
                        {"action": "command", "command": "list\nstop"}):
            with self.assertRaises(UserError):
                owner.dispatch(request)
        native._write.assert_not_called()
        owner.dispatch({"action": "command", "command": "list"})
        native._write.assert_called_once_with("list")

    def test_internal_controls_allow_only_existing_bounded_actions(self):
        for value in ("stop", "neoforge tps", "awft teleport " + "a" * 32, "gamemode survival KG", "experience set KG 1000 levels"):
            self.assertEqual(internal_command(value), value)
        for value in ("stop\nlist", "gamemode survival @a", "experience set KG 1001 levels", "bash -c id"):
            with self.assertRaises(UserError):
                internal_command(value)

    def test_manual_stop_is_durable_and_start_failure_does_not_loop(self):
        native = Mock(identity=None)
        native.stop.return_value = {"state": "offline"}
        owner = Supervisor(self.layout, self.storage, native)
        owner.dispatch({"action": "stop"})
        self.assertFalse(read_json(owner.desired_path)["running"])
        native.start.side_effect = UserError("test start refusal")
        with self.assertRaises(UserError):
            owner.dispatch({"action": "start"})
        self.assertFalse(Supervisor(self.layout, self.storage, native).desired)

    def test_dashboard_close_leaves_independent_service_alone(self):
        app = Application.__new__(Application)
        for name in ("characters", "mods", "playit", "backups", "metrics", "jobs", "atlas"):
            setattr(app, name, Mock())
        app.server = Mock(independent=True)
        app.close()
        app.server.running.assert_not_called()
        app.server.stop.assert_not_called()

    def test_windows_child_backend_close_still_saves_world(self):
        app = Application.__new__(Application)
        for name in ("characters", "mods", "playit", "backups", "metrics", "jobs", "atlas"):
            setattr(app, name, Mock())
        app.server = Mock(independent=False)
        app.server.running.return_value = True
        app.close()
        app.server.stop.assert_called_once()

    @unittest.skipUnless(sys.platform == "linux", "Native Linux process lease")
    def test_java_inherited_descriptor_blocks_a_replacement_after_owner_closes(self):
        from control_room.ownership import ProcessLease
        path = self.layout.state / "fixture-writer.lock"
        lease = ProcessLease(path)
        child = subprocess.Popen([sys.executable, "-c", "import sys; print('ready',flush=True); sys.stdin.readline()"],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, pass_fds=(lease.fd,))
        try:
            self.assertEqual(child.stdout.readline().strip(), "ready")
            lease.close()
            with self.assertRaises(UserError):
                ProcessLease(path)
        finally:
            child.communicate("stop\n", timeout=10)
        recovered = ProcessLease(path)
        recovered.close()

    @unittest.skipUnless(sys.platform == "linux", "Native Linux Unix socket")
    def test_service_loss_is_unknown_and_cannot_enable_offline_mutation(self):
        adapter = ServiceServer(self.layout, self.storage)
        with self.assertRaisesRegex(UserError, "unknown"):
            adapter.running()

    def test_staged_migration_needs_separate_activation_before_eula_or_java_probe(self):
        write_json(self.layout.home / "MIGRATION-STAGED.json", {"manifest_sha256": "a" * 64})
        native = Server(self.layout, self.storage)
        with patch("control_room.server.subprocess.Popen") as spawn, self.assertRaisesRegex(UserError, "activation"):
            native.start()
        spawn.assert_not_called()

    @unittest.skipUnless(sys.platform == "linux" and os.geteuid() != 0, "Native nonroot Linux service transport with a disposable console fixture")
    def test_native_socket_owner_survives_dashboard_reconnection_and_saves_on_stop(self):
        from control_room import service
        from control_room.ownership import ProcessLease
        self.layout.save_settings({"hosting_mode": "dedicated-ubuntu", "server_backend": "unix-service"})
        owners, errors = [], []
        script = "import sys; print('Done (0.1s)! For help, type help',flush=True)\nfor line in sys.stdin:\n print('Saved fixture world' if line.strip()=='stop' else 'echo:'+line.strip(),flush=True)\n if line.strip()=='stop': break\n"
        class ConsoleFixture(Server):
            def _start_owned(inner, notify=lambda _: None):
                with inner.layout.mutation:
                    command = [sys.executable, "-u", "-c", script]
                    inner.process = subprocess.Popen(command, cwd=inner.layout.server, stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, pass_fds=(inner._launch_lease.fd,))
                    inner.process._awft_lease = inner._launch_lease
                    import psutil
                    proc = psutil.Process(inner.process.pid)
                    inner.identity = {"pid": proc.pid, "created": proc.create_time(), "command": command, "cwd": str(inner.layout.server)}
                    inner.started, inner.state = time.time(), "starting"
                    inner._reader_thread = threading.Thread(target=inner._reader, args=(inner.process,), daemon=True)
                    inner._reader_thread.start()
                    return {"state": inner.state}
            def probe(inner):
                pass  # Fixture has no Minecraft status port or invented TPS.
        original = Supervisor
        def owner_factory(*args):
            owner = original(*args)
            owners.append(owner)
            return owner
        def run():
            try:
                service.serve(self.layout.home)
            except BaseException as exc:
                errors.append(exc)
        with patch("control_room.service.Storage", return_value=self.storage, create=True):
            # Storage is imported by serve; patch its source too.
            with patch("control_room.storage.Storage", return_value=self.storage), patch("control_room.server.Server", ConsoleFixture), patch("control_room.service.Supervisor", side_effect=owner_factory), patch("control_room.service.signal.signal"):
                thread = threading.Thread(target=run)
                thread.start()
                try:
                    deadline = time.monotonic() + 10
                    while not service.socket_path(self.layout).exists() and not errors and time.monotonic() < deadline:
                        time.sleep(.05)
                    self.assertFalse(errors)
                    first = ServiceServer(self.layout, self.storage)
                    first.start()
                    initial = first.wait_ready(10)
                    birth = first.identity["created"]
                    second = ServiceServer(self.layout, self.storage)
                    self.assertEqual(second.snapshot()["pid"], initial["pid"])
                    self.assertEqual(second.identity["created"], birth)
                    with self.assertRaises(UserError):
                        second.start()
                    with self.assertRaises(UserError):
                        ProcessLease(self.layout.state / "console-owner.lock")
                    self.assertEqual(second.stop()["state"], "offline")
                    deadline = time.monotonic() + 2
                    while time.monotonic() < deadline and not any("Saved fixture world" in x["text"] for x in second.console()):
                        time.sleep(.05)
                    self.assertTrue(any("Saved fixture world" in x["text"] for x in second.console()))
                finally:
                    if owners:
                        owners[0].stop_event.set()
                    thread.join(timeout=15)
                self.assertFalse(thread.is_alive())
                self.assertEqual(errors, [])


class ForwardingSecurityTests(unittest.TestCase):
    def test_loopback_forwarding_retains_origin_session_and_nonlocal_rejection(self):
        app = SimpleNamespace(token="fixture-csrf", get=lambda *args: {"app_id": "awft-control-room"}, post=lambda *args: {"sent": True})
        handler = make_handler(app)
        http = HTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=http.serve_forever, daemon=True)
        thread.start()
        port = http.server_port
        base = "http://127.0.0.1:" + str(port)
        try:
            # A local forward delivers a loopback request preserving the browser's port/Host.
            request = urllib.request.Request(base + "/api/console", data=b'{}', headers={"Content-Type": "application/json", "Origin": base, "X-AWFT-CSRF": app.token})
            with urllib.request.urlopen(request, timeout=3) as response:
                self.assertEqual(response.status, 200)
            for headers in ({"Origin": "https://example.invalid", "X-AWFT-CSRF": app.token},
                            {"Origin": base}, {"Origin": base, "X-AWFT-CSRF": app.token, "Sec-Fetch-Site": "cross-site"},
                            {"Host": "127.0.0.1:" + str(port+1), "X-AWFT-CSRF": app.token}):
                request = urllib.request.Request(base + "/api/console", data=b'{}', headers={"Content-Type": "application/json", **headers})
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(request, timeout=3)
                self.assertEqual(error.exception.code, 403)
            fake = SimpleNamespace(server=SimpleNamespace(server_port=port), headers={"Host": "127.0.0.1:" + str(port)}, client_address=("192.0.2.1", 12345))
            self.assertEqual(handler.security_error(fake), "local_origin_required")
        finally:
            http.shutdown()
            http.server_close()
            thread.join(timeout=3)


class DeploymentTests(SnowfallFixture):
    def config(self):
        return {"home": "/srv/awft/data", "source": "/opt/awft/source", "python": "/opt/awft/venv/bin/python", "user": "awft", "group": "awft"}

    def test_render_is_nonactivating_keeps_service_boundaries_and_nonroot_account(self):
        destination = self.root / "units"
        with patch("tools.snowfall_host.Storage", return_value=self.storage):
            snowfall_host.render(self.config(), destination)
        minecraft = (destination / "awft-minecraft.service").read_text()
        dashboard = (destination / "awft-control-room.service").read_text()
        self.assertIn("User=awft", minecraft)
        self.assertIn("SendSIGKILL=no", minecraft)
        self.assertIn("Restart=no", minecraft)
        self.assertNotIn("PartOf=", dashboard)
        self.assertNotIn("BindsTo=", dashboard)
        self.assertFalse(read_json(destination / "PREPARED.json")["activated"])
        self.assertFalse((destination / "host.json").read_text().find('"autostart": true') >= 0)

    def test_invalid_accounts_unit_specifiers_and_overlapping_paths_fail(self):
        for changes in ({"user": "root"}, {"source": "/tmp/%n"}, {"home": "/"}, {"home": "/opt/awft"}, {"python": "/bin/python\nExecStart=sh"}):
            with self.subTest(changes=changes), self.assertRaises(UserError):
                snowfall_host.configuration(self.config() | changes)

    def test_prepared_artifact_tampering_is_rejected(self):
        destination = self.root / "units"
        with patch("tools.snowfall_host.Storage", return_value=self.storage):
            snowfall_host.render(self.config(), destination)
        (destination / "awft-minecraft.service").write_text("tampered")
        with self.assertRaises(UserError):
            snowfall_host.prepared(destination)

    def test_linux_storage_uses_selected_volume_policy_and_preserves_windows_floor(self):
        storage = Storage(self.layout)
        self.layout.save_settings({"storage_reserve_gib": 5})
        with patch("control_room.storage.os.name", "posix"):
            self.assertEqual(storage.floor(), 5 * GiB)
        with patch("control_room.storage.os.name", "nt"):
            self.assertEqual(storage.floor(), 30 * GiB)


class BackupRecoveryTests(SnowfallFixture):
    def test_backup_retains_atlas_history_and_access_without_process_ownership(self):
        native = Mock()
        native.running.return_value = False
        write_json(self.layout.home / "configs/history/example/record.json", {"path": "server/config/example.toml"})
        write_json(self.layout.server / "ops.json", [{"name": "KG"}])
        backup = Backups(self.layout, self.storage, native)
        result = backup.create()
        manifest, _ = backup.verify_archive(backup.path(result["id"]))
        paths = {x["path"] for x in manifest["files"]}
        self.assertIn("dashboard/atlas-waypoints.json", paths)
        self.assertIn("configs/history/example/record.json", paths)
        self.assertIn("server/ops.json", paths)
        self.assertNotIn("dashboard/server-process.json", paths)

    def test_restore_failure_rolls_back_world_and_config_without_deleting_evidence(self):
        native = Mock()
        native.running.return_value = False
        config = self.layout.server / "config/example.toml"
        config.parent.mkdir()
        config.write_text('value="backup"')
        backup = Backups(self.layout, self.storage, native)
        result = backup.create()
        config.write_text('value="current"')
        (self.world / "level.dat").write_bytes(b"current world must survive failure")
        original_replace = os.replace
        def fail_config(source, target):
            if Path(source).name == "config" and Path(source).is_relative_to(self.layout.staging) and Path(target) == self.layout.server / "config":
                raise OSError("Injected configuration swap failure")
            return original_replace(source, target)
        with patch("control_room.backups.os.replace", side_effect=fail_config), self.assertRaises(OSError):
            backup.restore(result["id"], "RESTORE " + result["id"])
        self.assertEqual((self.world / "level.dat").read_bytes(), b"current world must survive failure")
        self.assertEqual(config.read_text(), 'value="current"')
        self.assertTrue(backup.path(result["id"]).exists())
        journal = next(self.layout.home.glob("pre-restore-*/transaction.json"))
        self.assertEqual(read_json(journal)["state"], "rolled-back")


if __name__ == "__main__":
    unittest.main()
