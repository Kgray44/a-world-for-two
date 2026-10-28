from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import zipfile
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from control_room.backups import Backups
from control_room.common import Layout, UserError, atomic_write, contained, digest, read_json, utcnow, write_json
from control_room.jobs import Jobs
from control_room.mod_manager import ModManager
from control_room.metrics import Metrics
from control_room.players import Players
from control_room.pack import generate_pack, in_range, jar_metadata, loader_supports, validate_graph, validate_pack
from control_room.server import Server
from control_room.settings import Settings, properties
from control_room.storage import Storage, scan_path, tree_size
from control_room.web import Application, HTTPServer, make_handler


class TestStorage:
    def __init__(self):
        self.calls = []

    def reserve(self, additional, target=None):
        if type(additional) is not int or additional < 0:
            raise UserError("Unbounded allocation")
        self.calls.append(additional)
        return {"allowed": True}

    def checkpoint(self, *args, **kwargs):
        pass


class Offline:
    state = "offline"
    tick = {"tps": None, "mspt": None, "at": None}

    def running(self):
        return False

    def snapshot(self):
        return {"state": self.state, "status": None, "events": []}


def mod(slug="sample", side="both"):
    return {"project_id": slug, "version_id": "exact-v1", "slug": slug, "name": "Sample",
            "version": "1.0", "filename": slug + ".jar", "side": side, "kind": "mod",
            "url": "https://cdn.modrinth.com/data/test/v1/" + slug + ".jar", "size": 10,
            "hashes": {"sha512": "a" * 128}, "dependencies": [], "world_sensitive": True,
            "optional": False, "default": True, "selection_reason": "test fixture", "license": {"id": "MIT"},
            "validation": {"runtime": "not run"}}


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="awft-test-")
        self.layout = Layout(Path(self.temp.name))
        self.layout.create()
        self.storage = TestStorage()
        self.server = Offline()
        self.settings = Settings(self.layout, self.storage, self.server)
        self.settings.initialize()

    def tearDown(self):
        self.temp.cleanup()


class ManifestTests(Fixture):
    def test_new_configuration_cannot_be_silently_omitted_from_index(self):
        pack = self.layout.home / "pack"
        lock = {"version": "1.0", "neoforge": "21.1.255", "mods": [mod()]}
        generate_pack(pack, lock)
        atomic_write(pack / "config/new.toml", "enabled = true\n")
        self.assertTrue(any("payload inventory" in e for e in validate_pack(pack, lock)))

    def test_nested_native_jarjar_dependencies_are_discovered(self):
        def archive_bytes(entries):
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, "w") as z:
                for key, value in entries.items():
                    z.writestr(key, value)
            return stream.getvalue()
        leaf = archive_bytes({"META-INF/neoforge.mods.toml": '[[mods]]\nmodId="nested_api"\nversion="1.0"\n'})
        metadata = json.dumps({"jars": [{"path": "META-INF/jars/api.jar"}]})
        middle = archive_bytes({"META-INF/jarjar/metadata.json": metadata, "META-INF/jars/api.jar": leaf,
            "META-INF/neoforge.mods.toml": '[[mods]]\nmodId="runtime"\nversion="1.0"\n'})
        path = self.layout.home / "outer.jar"
        path.write_bytes(archive_bytes({"META-INF/jarjar/metadata.json": json.dumps({"jars": [{"path": "runtime.jar"}]}), "runtime.jar": middle}))
        self.assertEqual({m["id"] for m in jar_metadata(path)["embedded"]}, {"runtime", "nested_api"})

    def test_canonical_hash_chain_and_lock_drift(self):
        pack = self.layout.home / "pack"
        lock = {"version": "1.0", "neoforge": "21.1.255", "mods": [mod()]}
        generate_pack(pack, lock)
        self.assertEqual(validate_pack(pack, lock), [])
        atomic_write(pack / "mods/sample.pw.toml", "changed")
        self.assertTrue(any("hash mismatch" in x for x in validate_pack(pack, lock)))

    def test_required_and_incompatible_dependencies(self):
        a, b = mod("a"), mod("b")
        a["dependencies"] = [{"project_id": "b", "version_id": None, "dependency_type": "required"}]
        self.assertTrue(validate_graph([a]))
        self.assertEqual(validate_graph([a, b]), [])
        a["dependencies"][0]["dependency_type"] = "incompatible"
        self.assertTrue(validate_graph([a, b]))

    def test_disjoint_lod_renderers_rejected(self):
        self.assertTrue(validate_graph([mod("roxy", "client"), mod("distanthorizons", "both")]))

    def test_maven_ranges_and_actual_loader_alias(self):
        self.assertTrue(in_range("15.0.140", "[15.0.0, )"))
        self.assertFalse(in_range("1.21.1", "[1.21,1.21.1)"))
        self.assertTrue(loader_supports("minecraft", "1.21.1", "[1.21,1.21.1)", "21.1.255"))
        self.assertFalse(loader_supports("sodium", "0.6.13", "[0.8.12,)", "21.1.255"))
        self.assertFalse(in_range("21.1.255", "[21.1.262,)"))
        self.assertTrue(in_range("21.1.255", "21.1.228"))  # Maven recommendation, not [exact].
        self.assertFalse(in_range("21.1.255", "[21.1.228]"))

    def test_library_jar_is_not_a_missing_mod(self):
        path = self.layout.home / "library.jar"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\r\nFMLModType: LIBRARY\r\n\r\n")
        self.assertTrue(jar_metadata(path)["library"])


class ConfigurationTests(Fixture):
    def test_mod_forms_preserve_unrelated_toml_and_reject_stale_json(self):
        path = self.layout.server / "config/DistantHorizons.toml"
        atomic_write(path, '# Keep this comment\n[common.multiThreading]\nnumberOfThreads = 8 # generated default\nthreadPriority = 5\n')
        field = next(s for s in self.settings.mod_forms() if s["id"] == "dh-threads")
        self.assertTrue(field["available"])
        self.settings.update_mod("dh-threads", 2, field["expected"])
        self.assertIn("threadPriority = 5", path.read_text())
        self.assertIn("# Keep this comment", path.read_text())
        with self.assertRaises(UserError):
            self.settings.update_mod("dh-threads", 1, field["expected"])
        config = self.layout.server / "config/advancedweather-common.json"
        write_json(config, {"hailDamageCrops": True, "unrelated": {"keep": 3}})
        weather = next(s for s in self.settings.mod_forms() if s["id"] == "weather-hailDamageCrops")
        self.settings.update_mod(weather["id"], False, weather["expected"])
        self.assertEqual(read_json(config), {"hailDamageCrops": False, "unrelated": {"keep": 3}})

    def test_default_security_world_path_and_unaccepted_eula(self):
        props = self.settings.get_properties()
        self.assertEqual(props["online-mode"], "true")
        self.assertEqual(props["enable-rcon"], "false")
        self.assertEqual(props["server-ip"], "127.0.0.1")
        self.assertEqual(props["level-name"], (self.layout.world / "AWorldForTwo").as_posix())
        self.assertEqual(properties((self.layout.server / "eula.txt").read_text())["eula"], "false")

    def test_schema_rejects_invalid_values_and_records_previous(self):
        with self.assertRaises(UserError):
            self.settings.update("server", {"view-distance": 100})
        prior = self.settings.props_path.read_bytes()
        self.settings.update("server", {"view-distance": 10})
        history = self.settings.history()
        self.assertEqual(len(history), 1)
        self.assertEqual(self.settings.get_properties()["view-distance"], "10")
        self.settings.restore(history[0]["id"])
        self.assertEqual(self.settings.props_path.read_bytes(), prior)

    def test_existing_world_seed_and_online_restart_setting_are_protected(self):
        (self.layout.world / "level.dat").write_bytes(b"synthetic fixture")
        with self.assertRaises(UserError):
            self.settings.update("server", {"level-seed": "other"})
        with patch.object(self.server, "running", return_value=True):
            with self.assertRaises(UserError):
                self.settings.update("server", {"view-distance": 10})

    def test_raw_editor_requires_current_hash_and_preserves_network(self):
        old = self.settings.raw("server.properties")
        content = old["content"].replace("online-mode=true", "online-mode=false")
        with self.assertRaises(UserError):
            self.settings.raw_proposal("server.properties", content, old["sha256"])
        with self.assertRaises(UserError):
            self.settings.raw_proposal("server.properties", old["content"], "wrong hash")
        with self.assertRaises(UserError):
            self.settings.allowed_config("../../outside.json")

    def test_console_allowlist_rejects_newline_execute_and_unconfirmed_op(self):
        server = Server(self.layout, self.storage)
        for command in ["say okay\nstop", "execute run stop", "op TestPlayer"]:
            with self.assertRaises(UserError):
                server.command(command)

    def test_typed_native_harbor_commands_bind_identity_and_confirmation(self):
        server = Server(self.layout, self.storage)
        digest = 'a' * 64
        command = 'awftharborcraft create artistic-harbor-craft-1234567890abcdef ' + digest
        with patch.object(server, '_write') as write:
            with self.assertRaises(UserError):
                server.command(command)
            server.command(command, confirmed=True)
            write.assert_called_once_with(command)
            for invalid in [command.replace(digest, 'bad'), command + ' extra',
                            command.replace('artistic-harbor-craft-', '../'),
                            'awftharborcraft summon minecraft:boat',
                            'awftattractions run hub ' + digest]:
                with self.assertRaises(UserError):
                    server.command(invalid, confirmed=True)

    def test_private_worldgen_export_admits_only_typed_unique_ids(self):
        server = Server(self.layout, self.storage)
        with patch.object(server, '_write') as write:
            command = 'awftbuild worldgen-inputs c35-server-1 true'
            server.command(command)
            write.assert_called_once_with(command)
            for command in ['awftbuild worldgen-inputs ../outside true',
                            'awftbuild worldgen-inputs ' + 'a' * 65 + ' true',
                            'awftbuild worldgen-inputs id true extra',
                            'awftbuild worldgen-inputs id 1']:
                with self.assertRaises(UserError):
                    server.command(command)

    def test_retained_mill_resume_requires_confirmation_and_typed_bundle(self):
        server = Server(self.layout, self.storage)
        write_json(self.layout.state / 'artistic-owner.json',
                   {'format': 'awft-artistic-stage:1', 'home': str(self.layout.home)})
        self.layout.save_settings(self.layout.settings() | {'permanent_world': False, 'port': 25575})
        command = 'awftmill resume mill-resume-1234567890abcdef ' + 'b' * 64
        with patch.object(server, '_write') as write:
            with self.assertRaises(UserError):
                server.command(command)
            server.command(command, confirmed=True)
            write.assert_called_once_with(command)
            for bad in [command + ' extra', command.replace('b' * 64, 'invalid'),
                        command.replace('mill-resume-', '../')]:
                with self.assertRaises(UserError):
                    server.command(bad, confirmed=True)

    def test_bridge_glue_requires_private_stage_typed_bundle_and_confirmation(self):
        server = Server(self.layout, self.storage)
        command = 'awftbridgeglue retire bridge-refinement-admission-' + 'a' * 16 + ' ' + 'a' * 64
        with patch.object(server, '_write') as write:
            with self.assertRaises(UserError):
                server.command(command, confirmed=True)
            write_json(self.layout.state / 'artistic-owner.json',
                       {'format': 'awft-artistic-stage:1', 'home': str(self.layout.home)})
            self.layout.save_settings(self.layout.settings() | {'permanent_world': False, 'port': 25575})
            with self.assertRaises(UserError):
                server.command(command)
            server.command(command, confirmed=True)
            write.assert_called_once_with(command)
            for bad in [command + ' extra', command.replace('bridge-refinement-admission-', '../'),
                        command.replace('a' * 64, 'invalid')]:
                with self.assertRaises(UserError):
                    server.command(bad, confirmed=True)
            self.layout.save_settings(self.layout.settings() | {'permanent_world': True})
            with self.assertRaises(UserError):
                server.command(command, confirmed=True)

    def test_import_joins_are_private_confirmed_and_exactly_typed(self):
        server = Server(self.layout, self.storage)
        command = 'awftimport settle import-joins-' + 'b' * 16 + ' ' + 'b' * 64
        with patch.object(server, '_write') as write:
            with self.assertRaises(UserError):
                server.command(command, confirmed=True)
            write_json(self.layout.state / 'artistic-owner.json',
                       {'format': 'awft-artistic-stage:1', 'home': str(self.layout.home)})
            self.layout.save_settings(self.layout.settings() | {'permanent_world': False, 'port': 25575})
            with self.assertRaises(UserError):
                server.command(command)
            server.command(command, confirmed=True)
            write.assert_called_once_with(command)
            for bad in [command + ' extra', command.replace('import-joins-', '../'),
                        command.replace('b' * 64, 'invalid')]:
                with self.assertRaises(UserError):
                    server.command(bad, confirmed=True)
            self.layout.save_settings(self.layout.settings() | {'permanent_world': True})
            with self.assertRaises(UserError):
                server.command(command, confirmed=True)


    def test_native_shape_settle_requires_exact_hash_and_confirmation(self):
        server = Server(self.layout, self.storage)
        command = 'awftbuild settle ' + 'c' * 64
        with patch.object(server, '_write') as write:
            with self.assertRaises(UserError):
                server.command(command)
            server.command(command, confirmed=True)
            write.assert_called_once_with(command)
            for bad in [command + ' extra', command.replace('c' * 64, 'invalid')]:
                with self.assertRaises(UserError):
                    server.command(bad, confirmed=True)

    def test_fountain_commissioning_is_private_typed_and_confirmed(self):
        server = Server(self.layout, self.storage)
        command = 'awftfountain commission fountain-' + 'd' * 16 + ' ' + 'd' * 64
        with patch.object(server, '_write') as write:
            with self.assertRaises(UserError):
                server.command(command, confirmed=True)
            write_json(self.layout.state / 'artistic-owner.json',
                       {'format': 'awft-artistic-stage:1', 'home': str(self.layout.home)})
            self.layout.save_settings(self.layout.settings() | {'permanent_world': False, 'port': 25575})
            with self.assertRaises(UserError):
                server.command(command)
            server.command(command, confirmed=True)
            write.assert_called_once_with(command)
            for bad in (command + ' extra', command.replace('fountain-', '../'),
                        command.replace('d' * 64, 'not-a-hash')):
                with self.assertRaises(UserError):
                    server.command(bad, confirmed=True)
            self.layout.save_settings(self.layout.settings() | {'port': 25565})
            with self.assertRaises(UserError):
                server.command(command, confirmed=True)
            self.layout.save_settings(self.layout.settings() | {'port': 25575, 'permanent_world': True})
            with self.assertRaises(UserError):
                server.command(command, confirmed=True)


    def test_native_growth_and_life_commands_keep_private_scope_and_mutation_confirmation(self):
        server = Server(self.layout, self.storage)
        commands = [('awfttrees', 'grow', 'describe', 'trees-'),
                    ('awfttreepatch', 'grow', 'inspect', 'treepatch-'),
                    ('awftrelocate', 'move', 'inspect', 'relocation-'),
                    ('awftlife', 'seed', 'inspect', 'life-'),
                    ('awftfountain', 'reset', 'inspect', 'fountain-'),
                    ('awftfountain', 'recover-gate', 'inspect', 'fountain-'),
                    ('awftfountain', 'park-gate', 'inspect', 'fountain-'),
                    ('awftmill', 'resume', 'inspect', 'mill-resume-')]
        for family, mutation, observation, prefix in commands:
            command = family + ' ' + mutation + ' ' + prefix + 'e' * 16 + ' ' + 'e' * 64
            with self.subTest(family=family), patch.object(server, '_write') as write:
                self.layout.save_settings(self.layout.settings() | {'permanent_world': True, 'port': 25565})
                with self.assertRaises(UserError):
                    server.command(command, confirmed=True)
                write_json(self.layout.state / 'artistic-owner.json',
                           {'format': 'awft-artistic-stage:1', 'home': str(self.layout.home)})
                self.layout.save_settings(self.layout.settings() | {'permanent_world': False, 'port': 25575})
                with self.assertRaises(UserError):
                    server.command(command)
                server.command(command, confirmed=True)
                server.command(command.replace(' ' + mutation + ' ', ' ' + observation + ' '))
                self.assertEqual(write.call_count, 2)
                for bad in (command + ' extra', command.replace(prefix, '../'),
                            command.replace('e' * 64, 'invalid'), command + '\nstop'):
                    with self.assertRaises(UserError):
                        server.command(bad, confirmed=True)
                self.layout.save_settings(self.layout.settings() | {'port': 25565})
                with self.assertRaises(UserError):
                    server.command(command, confirmed=True)
                self.layout.save_settings(self.layout.settings() | {'port': 25575, 'permanent_world': True})
                with self.assertRaises(UserError):
                    server.command(command, confirmed=True)


class PlayerTests(Fixture):
    def setUp(self):
        super().setUp()
        self.who = {"uuid": "32650cdf-2aaa-4f47-bb27-42ef0d1249fd", "name": "KgAmazing44"}
        write_json(self.layout.server / "whitelist.json", [self.who])
        self.players = Players(self.layout, self.storage, self.server, self.settings)

    def test_permission_levels_persist_and_require_explicit_confirmation(self):
        with self.assertRaises(UserError):
            self.players.permissions("KgAmazing44", 4)
        for invalid in [-1, 5, True, "3"]:
            with self.assertRaises(UserError):
                self.players.permissions("KgAmazing44", invalid, confirmed=True)
        with self.assertRaises(UserError):
            self.players.permissions("KgAmazing44", 0, bypass=True, confirmed=True)
        saved = self.players.permissions("kgamazing44", 2, confirmed=True)
        self.assertEqual(saved["operator_level"], 2)
        self.assertFalse(saved["bypass_player_limit"])
        self.players.permissions("KgAmazing44", 4, bypass=True, confirmed=True)
        self.assertTrue(read_json(self.layout.server / "ops.json")[0]["bypassesPlayerLimit"])
        self.players.permissions("KgAmazing44", 0, confirmed=True)
        self.assertEqual(read_json(self.layout.server / "ops.json"), [])
        self.assertEqual(read_json(self.layout.server / "whitelist.json"), [self.who])
        self.assertTrue(self.settings.history())

    def test_locations_expire_and_are_labelled_last_seen_after_disconnect(self):
        data = {"tick_at": utcnow(), "players": {self.who["uuid"]: dict(self.who, x=123.5, y=70, z=-20)},
                "bridge_capabilities": ["player_locations", "surface_minimap"]}
        self.players.telemetry = lambda: data
        with patch.object(self.server, "state", "online"):
            live = self.players.details("KgAmazing44")
            self.assertTrue(live["online"])
            self.assertEqual(live["location_state"], "live")
            data["tick_at"] = "2020-01-01T00:00:00Z"
            stale = self.players.details("KgAmazing44")
            self.assertFalse(stale["online"])
            self.assertEqual(stale["location_state"], "last seen")
            self.assertEqual(stale["location"]["x"], 123.5)
            self.assertEqual(stale["capabilities"], [])
        with self.assertRaises(UserError):
            self.players.game_action("KgAmazing44", "game-mode", "creative", confirmed=True)
        with self.assertRaises(UserError):
            self.players.details("UnknownPlayer")

    def test_live_permissions_refuse_an_old_or_missing_bridge(self):
        with patch.object(self.server, "running", return_value=True):
            with self.assertRaisesRegex(UserError, "fresh Control Bridge"):
                self.players.permissions("KgAmazing44", 3, confirmed=True)
        self.assertFalse((self.layout.server / "ops.json").exists())


class BackupTests(Fixture):
    def saved_world(self):
        world = self.layout.world / "TestWorld"
        world.mkdir()
        (world / "level.dat").write_bytes(b"synthetic world fixture\0" * 80)
        (world / "region.mca").write_bytes(os.urandom(4096))
        return world

    def test_verified_restore_preserves_current_world_and_refuses_online(self):
        world = self.saved_world()
        backups = Backups(self.layout, self.storage, self.server)
        original = (world / "level.dat").read_bytes()
        receipt = backups.create()
        (world / "level.dat").write_bytes(b"newer unique data")
        with patch.object(self.server, "running", return_value=True):
            with self.assertRaises(UserError):
                backups.restore(receipt["id"], "RESTORE " + receipt["id"])
        with self.assertRaises(UserError):
            backups.restore(receipt["id"], "yes")
        result = backups.restore(receipt["id"], "RESTORE " + receipt["id"])
        self.assertEqual((world / "level.dat").read_bytes(), original)
        self.assertEqual((Path(result["previous_world"]) / "world/TestWorld/level.dat").read_bytes(), b"newer unique data")

    def test_corrupted_backup_and_zip_traversal_rejected(self):
        self.saved_world()
        backups = Backups(self.layout, self.storage, self.server)
        receipt = backups.create()
        path = backups.path(receipt["id"])
        with path.open("ab") as stream:
            stream.write(b"corrupted")
        with self.assertRaises(UserError):
            backups.verify(receipt["id"])
        dangerous = self.layout.home / "unsafe.zip"
        with zipfile.ZipFile(dangerous, "w") as archive:
            archive.writestr("awft-backup.json", json.dumps({"format": 1, "files": [{"path": "../outside", "size": 1, "sha256": "0"}]}))
            archive.writestr("../outside", "x")
        with self.assertRaises(UserError):
            backups.verify_archive(dangerous)


class StorageTests(Fixture):
    def test_slow_inventory_does_not_block_live_requests_or_duplicate_scans(self):
        storage = Storage(self.layout)
        entered, release = threading.Event(), threading.Event()
        measured = {"measured_at": utcnow(), "bytes": 123, "categories": []}
        def scan():
            entered.set()
            release.wait(2)
            storage._breakdown = measured
            return measured
        with patch.object(storage, "breakdown", side_effect=scan) as scanning, patch.object(storage, "associated", return_value={"rows": []}), patch('control_room.storage.time.monotonic', return_value=5):
            try:
                first = storage.snapshot()
                self.assertTrue(entered.wait(1))
                second = storage.snapshot()
                self.assertIsNone(first["project_bytes"])
                self.assertIsNone(second["breakdown"]["measured_at"])
                self.assertTrue(second["breakdown"]["updating"])
                self.assertEqual(scanning.call_count, 1)
            finally:
                release.set()
                storage._inventory_worker.join(2)
            self.assertEqual(storage.snapshot()["project_bytes"], 123)

    @unittest.skipUnless(os.name == "nt", "Windows extended path regression")
    def test_long_cache_paths_remain_visible_to_guards_and_live_totals(self):
        cache = self.layout.caches
        self.assertTrue(cache.is_relative_to(self.layout.home))
        nested = scan_path(cache / ("a" * 80) / ("b" * 80) / ("c" * 80))
        try:
            nested.mkdir(parents=True)
            (nested / "dependency.pom").write_bytes(b"actual cached dependency")
            self.assertEqual(tree_size(cache), 24)
            report = Storage(self.layout).breakdown(force=True)
            self.assertTrue(report["complete"])
            self.assertEqual(next(c["bytes"] for c in report["categories"] if c["key"] == "caches"), 24)
        finally:
            shutil.rmtree(scan_path(cache))

    def test_live_inventory_includes_world_backups_staging_and_growth(self):
        storage = Storage(self.layout)
        (self.layout.world / "level.dat").write_bytes(b"x" * 1000)
        (self.layout.backups / "sample.zip").write_bytes(b"y" * 500)
        (self.layout.staging / "failed.partial").write_bytes(b"z" * 200)
        first = storage.breakdown(force=True)
        sizes = {r["key"]: r["bytes"] for r in first["categories"]}
        self.assertEqual(sizes["world"], 1000)
        self.assertEqual(sizes["backups"], 500)
        self.assertEqual(sizes["staging"], 200)
        (self.layout.world / "level.dat").write_bytes(b"x" * 2000)
        second = storage.breakdown(force=True)
        self.assertEqual(second["bytes"] - first["bytes"], 1000)
        self.assertTrue(second["complete"])

    def test_unbounded_or_over_budget_allocation_rejected_before_host_guard(self):
        storage = Storage(self.layout)
        for value in [None, -1, 1.5, 101 * 1024 ** 3]:
            with self.assertRaises(UserError):
                storage.reserve(value)


class MetricsHistoryTests(Fixture):
    def test_live_samples_commit_before_checkpoint_and_survive_reopening(self):
        server = Mock()
        server.snapshot.return_value = {"pid": None, "state": "offline", "tick": {
            "tps": None, "mspt": None, "at": None, "source": "not sampled"}}
        metrics = Metrics(self.layout, self.storage, server)
        with metrics.connect() as connection:
            connection.execute("CREATE TABLE samples (at REAL PRIMARY KEY, data TEXT NOT NULL)")
        with patch.object(metrics, "alerts", return_value=[]), patch.object(metrics.clients, "collect", return_value=[]):
            first = metrics.collect()
            second = metrics.collect()
        reopened = Metrics(self.layout, self.storage, server).history()
        self.assertEqual(len(reopened), 1)
        self.assertEqual(reopened[0]["at"], second["at"])
        self.assertGreaterEqual(second["at"], first["at"])
        self.assertIsNone(reopened[0]["tps"])
        self.assertNotIn("collection_error", reopened[0])

    def test_current_neoforge_console_reports_only_overall_measurements(self):
        server = Server(self.layout, self.storage)
        server.record("[Server thread/INFO]: Overworld: 20.000 TPS (8.407 ms/tick)")
        self.assertIsNone(server.tick["tps"])
        server.record("[Server thread/INFO]: Overall: 19.875 TPS (9.949 ms/tick)")
        self.assertEqual(server.tick["tps"], 19.875)
        self.assertEqual(server.tick["mspt"], 9.949)
        self.assertIn("Overall", server.tick["source"])


class JobTests(unittest.TestCase):
    def test_world_start_job_fails_when_java_exits_before_minecraft_is_ready(self):
        app = Application.__new__(Application)
        app.active_test = lambda: None
        app.server = SimpleNamespace(state="offline", start=lambda **kwargs: None,
                                     running=lambda: False, snapshot=lambda: {"state": "offline"})
        jobs = Jobs()
        jobs.submit("Start world", app.start_world)
        jobs.close()
        self.assertEqual(jobs.list()[0]["status"], "failed")
        self.assertIn("did not finish starting", jobs.list()[0]["error"])

    def test_world_start_job_completes_after_minecraft_reports_online(self):
        app = Application.__new__(Application)
        app.active_test = lambda: None
        app.server = SimpleNamespace(state="online", start=lambda **kwargs: None,
                                     running=lambda: True, snapshot=lambda: {"state": "online"})
        jobs = Jobs()
        jobs.submit("Start world", app.start_world)
        jobs.close()
        self.assertEqual(jobs.list()[0]["status"], "complete")

    def test_background_error_is_visible_and_other_requests_remain_possible(self):
        jobs = Jobs()
        gate = threading.Event()
        def work(notify):
            notify("checkpoint")
            gate.wait(1)
            raise UserError("preserved failure")
        ident = jobs.submit("test", work)["job"]
        self.assertEqual(jobs.list()[0]["id"], ident)
        gate.set()
        jobs.close()
        self.assertEqual(jobs.list()[0]["status"], "failed")
        self.assertEqual(jobs.list()[0]["error"], "preserved failure")


class HTTPTests(unittest.TestCase):
    def test_mutations_require_loopback_host_origin_and_session_token(self):
        class App:
            token = "session-secret"
            def get(self, path, query):
                return {"ok": True}
            def post(self, path, body):
                return {"saved": True}
        http = HTTPServer(("127.0.0.1", 0), make_handler(App()))
        worker = threading.Thread(target=http.serve_forever, daemon=True)
        worker.start()
        base = "http://127.0.0.1:" + str(http.server_port)
        def send(headers):
            request = urllib.request.Request(base + "/api/test", data=b"{}", headers={"Content-Type": "application/json"} | headers)
            try:
                with urllib.request.urlopen(request, timeout=2) as response:
                    return response.status
            except urllib.error.HTTPError as exc:
                return exc.code
        try:
            self.assertEqual(send({}), 403)
            self.assertEqual(send({"X-AWFT-CSRF": App.token, "Origin": "https://elsewhere.example"}), 403)
            self.assertEqual(send({"X-AWFT-CSRF": App.token, "Host": "evil.example"}), 403)
            self.assertEqual(send({"X-AWFT-CSRF": App.token}), 200)
        finally:
            http.shutdown()
            http.server_close()
            worker.join(2)


if __name__ == "__main__":
    unittest.main()
