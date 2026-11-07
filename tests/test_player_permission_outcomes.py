from __future__ import annotations

import time
from unittest.mock import patch

from control_room.common import UserError, read_json, write_json
from control_room.jobs import Jobs
from control_room.players import Players
from control_room.web import Application
from tests.test_safety import Fixture


class PlayerPermissionOutcomeTests(Fixture):
    def setUp(self):
        super().setUp()
        self.who = {"uuid": "00000000-0000-4000-8000-000000000002", "name": "OpOnlyFixture"}
        write_json(self.layout.server / "whitelist.json", [])
        write_json(self.layout.server / "ops.json", [dict(self.who, level=3, bypassesPlayerLimit=False)])
        self.players = Players(self.layout, self.storage, self.server, self.settings)

    def submit(self, **body):
        app = Application.__new__(Application)
        app.players = self.players
        app.jobs = Jobs()
        self.addCleanup(app.jobs.close)
        ident = app.post("/api/player/permissions", body)["job"]
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            job = next(j for j in app.jobs.list() if j["id"] == ident)
            if job["status"] not in ("queued", "running"):
                return job
            time.sleep(.01)
        self.fail("Permission task did not finish")

    def test_last_operator_removal_completes_without_recreating_roster_or_whitelist(self):
        self.assertEqual(self.players.details(self.who["name"])["operator_level"], 3)
        job = self.submit(name=self.who["name"], level=0, confirmed=True)
        self.assertEqual(job["status"], "complete", job)
        self.assertIsNone(job["error"])
        self.assertEqual(job["result"]["persistence"], "confirmed")
        self.assertEqual(job["result"]["operator_level"], 0)
        self.assertNotIn("online", job["result"])
        self.assertNotIn("location", job["result"])
        self.assertEqual(read_json(self.layout.server / "ops.json"), [])
        self.assertEqual(read_json(self.layout.server / "whitelist.json"), [])
        self.assertEqual(self.players.snapshot()["members"], [])
        with self.assertRaises(UserError):
            self.players.details(self.who["name"])
        audit = read_json(next(self.layout.logs.glob("player-permissions-*.json")))
        self.assertEqual(audit["persistence"], "confirmed")

    def test_whitelisted_member_removal_keeps_access_without_claiming_current_presence(self):
        write_json(self.layout.server / "whitelist.json", [self.who])
        result = self.players.permissions(self.who["name"], 0, confirmed=True)
        self.assertEqual(result["persistence"], "confirmed")
        self.assertNotIn("online", result)
        self.assertEqual(read_json(self.layout.server / "whitelist.json"), [self.who])
        self.assertEqual(self.players.details(self.who["name"])["operator_level"], 0)

    def test_unconfirmed_and_failed_persistence_never_report_success_or_change_access(self):
        original = (self.layout.server / "ops.json").read_bytes()
        rejected = self.submit(name=self.who["name"], level=0, confirmed=False)
        self.assertEqual(rejected["status"], "failed")
        with patch("control_room.players.write_json", side_effect=OSError("synthetic write refusal")):
            with self.assertRaises(OSError):
                self.players.permissions(self.who["name"], 0, confirmed=True)
        self.assertEqual((self.layout.server / "ops.json").read_bytes(), original)
        self.assertEqual(list(self.layout.logs.glob("player-permissions-*.json")), [])
