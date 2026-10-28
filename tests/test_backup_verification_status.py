from __future__ import annotations

from unittest.mock import patch

from control_room.backups import Backups
from control_room.common import UserError, read_json, write_json
from tests.test_safety import Fixture


class BackupVerificationStatusTests(Fixture):
    def setUp(self):
        super().setUp()
        world = self.layout.world / "SyntheticFixture"
        world.mkdir()
        (world / "level.dat").write_bytes(b"synthetic backup payload" * 40)
        self.backups = Backups(self.layout, self.storage, self.server)
        self.receipt = self.backups.create()
        self.ident = self.receipt["id"]
        self.archive = self.backups.path(self.ident)
        self.original_archive = self.archive.read_bytes()
        self.original_receipt = self.archive.with_suffix(".json").read_bytes()

    def test_corruption_is_reported_after_reopen_without_rehashing_lists(self):
        damaged = self.original_archive + b"intentional corruption"
        self.archive.write_bytes(damaged)
        with self.assertRaisesRegex(UserError, "hash mismatch"):
            self.backups.verify(self.ident)
        reopened = Backups(self.layout, self.storage, self.server)
        with patch("control_room.backups.digest", side_effect=AssertionError("list must not hash")):
            row = reopened.list()[0]
        self.assertEqual(row["integrity"], "failed")
        self.assertEqual(row["creation_integrity"], "verified")
        self.assertTrue(row["checked_at"])
        self.assertEqual(self.archive.read_bytes(), damaged)
        self.assertEqual(self.archive.with_suffix(".json").read_bytes(), self.original_receipt)
        self.assertEqual(row["sha256"], self.receipt["sha256"])

    def test_changed_archive_loses_cached_success_until_explicit_reverification(self):
        result = self.backups.verify(self.ident)
        self.assertEqual(self.backups.list()[0]["integrity"], "verified")
        self.archive.write_bytes(self.original_archive + b"changed")
        row = self.backups.list()[0]
        self.assertEqual(row["integrity"], "unknown")
        self.assertEqual(row["checked_at"], result["checked_at"])
        self.archive.write_bytes(self.original_archive)
        self.backups.verify(self.ident)
        self.assertEqual(self.backups.list()[0]["integrity"], "verified")

    def test_change_during_verification_never_qualifies_the_new_file(self):
        original = self.backups.verify_archive
        def change_after_read(path):
            result = original(path)
            path.write_bytes(self.original_archive + b"concurrent change")
            return result
        with patch.object(self.backups, "verify_archive", side_effect=change_after_read):
            with self.assertRaisesRegex(UserError, "changed during verification"):
                self.backups.verify(self.ident)
        self.assertEqual(self.backups.list()[0]["integrity"], "unknown")

    def test_result_write_failure_leaves_durable_unknown_instead_of_success(self):
        writes = 0
        def fail_terminal_write(path, value):
            nonlocal writes
            writes += 1
            if writes == 2:
                raise OSError("synthetic final write failure")
            write_json(path, value)
        with patch("control_room.backups.write_json", side_effect=fail_terminal_write):
            with self.assertRaisesRegex(UserError, "could not be recorded"):
                self.backups.verify(self.ident)
        reopened = Backups(self.layout, self.storage, self.server)
        self.assertEqual(reopened.list()[0]["integrity"], "unknown")
        self.assertEqual(self.archive.with_suffix(".json").read_bytes(), self.original_receipt)

    def test_reserve_refusal_does_not_read_the_archive_or_return_success(self):
        with patch.object(self.storage, "reserve", side_effect=UserError("reserve refused")):
            with patch("control_room.backups.digest", side_effect=AssertionError("must reserve first")):
                with self.assertRaisesRegex(UserError, "reserve refused"):
                    self.backups.verify(self.ident)
        self.assertFalse(self.archive.with_suffix(".verification.json").exists())

    def test_malformed_outcome_is_unknown_and_sidecars_are_not_extra_backups(self):
        sidecar = self.archive.with_suffix(".verification.json")
        sidecar.write_text("not JSON", encoding="utf-8")
        rows = self.backups.list()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["integrity"], "unknown")
        self.assertEqual(read_json(self.archive.with_suffix(".json"))["sha256"], self.receipt["sha256"])

    def test_oversized_outcome_is_not_parsed(self):
        self.archive.with_suffix(".verification.json").write_bytes(b" " * (16 * 1024 + 1))
        original = read_json
        def bounded_read(path, default=None):
            self.assertFalse(path.name.endswith(".verification.json"))
            return original(path, default)
        with patch("control_room.backups.read_json", side_effect=bounded_read):
            self.assertEqual(self.backups.list()[0]["integrity"], "unknown")

    def test_invalid_original_hash_cannot_expand_the_verification_ledger(self):
        for invalid in ("a" * 65, "not a digest", "a" * (20 * 1024)):
            receipt = read_json(self.archive.with_suffix(".json"))
            receipt["sha256"] = invalid
            write_json(self.archive.with_suffix(".json"), receipt)
            with self.assertRaisesRegex(UserError, "valid original integrity receipt"):
                self.backups.verify(self.ident)
            self.assertFalse(self.archive.with_suffix(".verification.json").exists())
