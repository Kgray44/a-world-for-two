import copy
import json
import shutil
import tempfile
import tomllib
import unittest
from pathlib import Path

from control_room.common import REPO, UserError, read_json, write_json
from control_room.pack import generate_pack, validate_pack
from tools.compatibility import build_inventory
from tools.cozy_pets import PROPOSAL, apply_source, plan, proposal_data, stage
from tools.cozy_pet_habitats import BED, build_habitats


class CozyPetsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        lock = read_json(REPO / "catalog/lock.json")
        keep = {"animal-garden-sugar-glider", "architectury-api", "geckolib", "fzzy-config", "kotlin-for-forge"}
        lock["mods"] = [m for m in lock["mods"] if m["slug"] in keep]
        self.original = copy.deepcopy(lock["mods"])
        write_json(self.root / "catalog/lock.json", lock)
        write_json(self.root / "catalog/selection.json", {"version": lock["version"], "mods": []})
        write_json(self.root / "catalog/requests.json", {"requests": [
            ["flying-squirrels", "Flying squirrels", "animals"],
            ["still-unresolved", "Still unresolved", "animals"]]})
        generate_pack(self.root / "packwiz", lock)

    def alter_lock(self, change):
        lock = read_json(self.root / "catalog/lock.json")
        change(lock)
        write_json(self.root / "catalog/lock.json", lock)
        generate_pack(self.root / "packwiz", lock)

    def test_additive_integration_preserves_every_existing_pin_and_request(self):
        result = apply_source(self.root, "0.1.0-pets-test")
        lock = read_json(self.root / "catalog/lock.json")
        actual = {m["project_id"]: m for m in lock["mods"]}
        self.assertTrue(all(actual[m["project_id"]] == m for m in self.original))
        self.assertEqual(set(result["new_mods"]), {"adorable-hamster-pets", "aquarius-libs", "patchouli"})
        self.assertEqual(validate_pack(self.root / "packwiz", lock), [])
        inventory = build_inventory(self.root)
        rows = {r["id"]: r for r in inventory["requests"]}
        self.assertEqual(rows["still-unresolved"]["status"], "Unresolved, with investigation details")
        self.assertEqual(rows["flying-squirrels"]["status"], "Alternative selected")
        self.assertTrue(rows["animal-garden-sugar-glider"]["selected_by_default"])
        self.assertEqual(rows["animal-garden-sugar-glider"]["file_pin"]["project_id"], "WktWffF9")
        for key in ("adorable-hamster-pets", "aquarius-libs"):
            self.assertTrue(rows[key]["selected_by_default"])
            self.assertEqual(rows[key]["runtime"], "not run")
            self.assertEqual(rows[key]["status"], "Integrated but awaiting runtime validation")
        again = plan(self.root)
        self.assertEqual(again["new_mods"], [])
        self.assertEqual(len(again["lock"]["mods"]), len(lock["mods"]))

    def test_read_only_plan_does_not_write(self):
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        plan(self.root)
        after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_master_candidate_and_existing_validation_are_preserved_in_plan(self):
        def change(lock):
            lock["version"] = "0.1.0-candidate.999"
            lock["mods"][0]["validation"]["runtime"] = "older scoped observation; not current acceptance"
        self.alter_lock(change)
        before = read_json(self.root / "catalog/lock.json")
        proposed = plan(self.root)
        self.assertEqual(proposed["lock"]["version"], before["version"])
        self.assertEqual(proposed["lock"]["mods"][:len(before["mods"])], before["mods"])

    def test_changed_or_disabled_glider_is_held(self):
        for key, value in (("version_id", "unreviewed"), ("side", "client"), ("default", False)):
            with self.subTest(key=key):
                original = read_json(self.root / "catalog/lock.json")
                def change(lock):
                    next(m for m in lock["mods"] if m["slug"] == "animal-garden-sugar-glider")[key] = value
                self.alter_lock(change)
                with self.assertRaisesRegex(UserError, "Sugar Glider"):
                    plan(self.root)
                write_json(self.root / "catalog/lock.json", original)
                generate_pack(self.root / "packwiz", original)

    def test_native_dependency_version_and_server_side_are_required(self):
        for key, value in (("version", "1.0.0"), ("side", "client")):
            with self.subTest(key=key):
                original = read_json(self.root / "catalog/lock.json")
                def change(lock):
                    next(m for m in lock["mods"] if m["slug"] == "architectury-api")[key] = value
                self.alter_lock(change)
                with self.assertRaisesRegex(UserError, "Native hamster dependency"):
                    plan(self.root)
                write_json(self.root / "catalog/lock.json", original)
                generate_pack(self.root / "packwiz", original)

    def test_conflicting_pet_pin_is_not_replaced(self):
        item = copy.deepcopy(proposal_data()["additions"][0])
        item["version_id"] = "unreviewed"
        self.alter_lock(lambda lock: lock["mods"].append(item))
        with self.assertRaisesRegex(UserError, "Refusing to replace"):
            plan(self.root)

    def test_config_overwrite_and_payload_tampering_are_refused(self):
        path = self.root / "packwiz/config/adorablehamsterpets/main.toml"
        path.parent.mkdir(parents=True)
        path.write_text("enableHamsterThrowing = true\n")
        generate_pack(self.root / "packwiz", read_json(self.root / "catalog/lock.json"))
        with self.assertRaisesRegex(UserError, "overwrite"):
            plan(self.root)
        proposal = self.root / "proposal"
        shutil.copytree(PROPOSAL, proposal)
        (proposal / "packwiz/config/adorablehamsterpets/main.toml").write_text("enableHamsterThrowing = true\n")
        with self.assertRaisesRegex(UserError, "reviewed manifest"):
            proposal_data(proposal)

    def test_spawn_override_replaces_native_resource_and_keeps_real_entities(self):
        path = PROPOSAL / "packwiz/config/paxi/datapacks/awft-cozy-pets"
        data = read_json(path / "data/animalgarden_sugarglider/neoforge/biome_modifier/spawn_sugarglider.json")
        audit = read_json(PROPOSAL / "static-audit.json")["sugar_glider_spawn"]
        self.assertEqual(data["biomes"], audit["upstream"]["biomes"])
        self.assertEqual(data["spawners"], [{"type": "animalgarden_sugarglider:sugarglider", "weight": 2,
                                            "minCount": 1, "maxCount": 1}])
        self.assertEqual(read_json(path / "pack.mcmeta")["pack"]["pack_format"], 48)

    def test_safe_fields_remain_native_and_breeding_is_bounded(self):
        proposal_data()
        config = tomllib.loads((PROPOSAL / "packwiz/config/adorablehamsterpets/main.toml").read_text())
        for key in ("enableHamsterThrowing", "enableRedstoneFever", "enableItemStealing", "enableCropSnacking"):
            self.assertIs(config[key], False)
        self.assertTrue(config["enableBreeding"])
        self.assertEqual(config["litterSizeMax"], 1)
        self.assertTrue(config["preventOwnerFriendlyFire"])
        self.assertTrue(config["enableRespawnInBed"])
        self.assertTrue(config["freeBedRespawns"])
        self.assertTrue(config["allowSleepInBed"])

    def test_stage_cannot_target_world_or_existing_directory(self):
        with self.assertRaisesRegex(UserError, "new directory"):
            stage(self.root, self.root / "world")
        existing = self.root / ".local/existing"
        existing.mkdir(parents=True)
        with self.assertRaisesRegex(UserError, "new directory"):
            stage(self.root, existing)

    def test_life_schematics_are_relative_bounded_real_entities_and_air_is_explicit(self):
        proposal = build_habitats()
        self.assertEqual(proposal, read_json(PROPOSAL / "life-habitats.json"))
        self.assertEqual(proposal["world_write_authority"], "NONE")
        self.assertEqual(proposal["initial_total"], 4)
        self.assertEqual(proposal["managed_admission_ceiling_total"], 8)
        self.assertEqual({h["residents"]["entity_type"] for h in proposal["habitats"]},
                         {"adorablehamsterpets:hamster", "animalgarden_sugarglider:sugarglider"})
        for h in proposal["habitats"]:
            self.assertIsNone(h["anchor"])
            self.assertIsNone(h["residents"]["owner_uuid"])
            self.assertIs(h["residents"]["NoAI"], False)
            self.assertIs(h["residents"]["Invulnerable"], False)
            self.assertLess(len(h["blocks"]), 1500)
            coords = {tuple(b[:3]) for b in h["blocks"]}
            self.assertEqual(len(coords), len(h["blocks"]))
            self.assertFalse(coords & {tuple(p) for p in h["required_existing_air"]})
            self.assertTrue(h["required_existing_solid_support"])
            self.assertTrue(h["required_existing_air"])
        self.assertEqual(sum(b[3] == BED for b in proposal["habitats"][0]["blocks"]), 2)


if __name__ == "__main__":
    unittest.main()
