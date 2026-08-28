import unittest
from unittest.mock import patch

from flask_jwt_extended import create_access_token

from palworld_pal_editor.config import Config
from palworld_pal_editor.core.pal_entity import PalEntity
from palworld_pal_editor.core.pal_objects import PalObjects, toUUID
from palworld_pal_editor.core.pal_record import PalRecord
from fakes import record_location, world_record
from palworld_pal_editor.webui import app


PLAYER_ID = toUUID("11111111-1111-1111-1111-111111111111")
PAL_ID = toUUID("22222222-2222-2222-2222-222222222222")


def make_record() -> PalRecord:
    pal_obj = PalObjects.PalSaveParameter(
        PAL_ID,
        PLAYER_ID,
        PalObjects.EMPTY_UUID,
        0,
        PalObjects.EMPTY_UUID,
    )
    record = world_record(pal_obj, storage_key="world-container:test")
    pal = record.pal
    pal.PassiveSkillList.append("CraftSpeed_up1")
    pal.MasteredWaza.append("EPalWazaID::AirCanon")
    pal.EquipWaza.append("EPalWazaID::AirCanon")
    return record


class FakeManager:
    def __init__(self, record):
        self.record = record

    def get_unique_world_record(self, _instance_id):
        return self.record

    def get_player(self, _player_id):
        return type("Player", (), {"NickName": "Target"})()

    def normalize_external_record(self, _record):
        pass

    def resolve_record_location(self, record):
        return record_location(record)


class SkillTemplateApiTests(unittest.TestCase):
    def setUp(self):
        self.previous_templates = getattr(Config, "skillTemplates", None)
        Config.skillTemplates = []
        self.record = make_record()
        self.pal = self.record.pal
        self.manager = FakeManager(self.record)
        self.client = app.test_client()
        with app.app_context():
            token = create_access_token(identity="test")
        self.headers = {"Authorization": f"Bearer {token}"}
        self.patches = [
            patch("palworld_pal_editor.api.pal.SaveManager", return_value=self.manager),
            patch(
                "palworld_pal_editor.core.save_manager.SaveManager",
                return_value=self.manager,
            ),
            patch.object(Config, "save_to_file"),
        ]
        self.started_patches = [item.start() for item in self.patches]

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        if self.previous_templates is None:
            del Config.skillTemplates
        else:
            Config.skillTemplates = self.previous_templates

    def request_data(self, **extra):
        return {
            "PlayerUId": str(PLAYER_ID),
            "PalGuid": str(PAL_ID),
            **extra,
        }

    def test_passive_template_can_be_created_renamed_applied_and_deleted(self):
        created = self.client.post(
            "/api/pal/skill_templates",
            json=self.request_data(Name="Worker passives", Type="passive"),
            headers=self.headers,
        ).get_json()
        self.assertEqual(0, created["status"])
        template_id = created["data"]["Id"]
        self.assertEqual(["CraftSpeed_up1"], created["data"]["PassiveSkillList"])
        self.assertNotIn("EquipWaza", created["data"])

        renamed = self.client.patch(
            f"/api/pal/skill_templates/{template_id}",
            json={"Name": "Base worker"},
            headers=self.headers,
        ).get_json()
        self.assertEqual("Base worker", renamed["data"]["Name"])

        self.pal.PassiveSkillList.clear()
        applied = self.client.post(
            f"/api/pal/skill_templates/{template_id}/apply",
            json=self.request_data(),
            headers=self.headers,
        ).get_json()
        self.assertEqual(0, applied["status"])
        self.assertEqual(["CraftSpeed_up1"], self.pal.PassiveSkillList)
        self.assertEqual(["CraftSpeed_up1"], applied["data"]["PassiveSkillList"])

        deleted = self.client.delete(
            f"/api/pal/skill_templates/{template_id}", headers=self.headers
        ).get_json()
        self.assertEqual(0, deleted["status"])
        self.assertEqual([], Config.skillTemplates)

    def test_active_template_records_equipped_and_preserves_learned_skills(self):
        self.pal.MasteredWaza.append("EPalWazaID::PowerShot")
        self.pal.EquipWaza.append("EPalWazaID::PowerShot")
        created = self.client.post(
            "/api/pal/skill_templates",
            json=self.request_data(Name="Combat", Type="active"),
            headers=self.headers,
        ).get_json()
        template_id = created["data"]["Id"]
        equipped = list(self.pal.EquipWaza)
        self.assertNotIn("MasteredWaza", created["data"])
        self.assertNotIn("MasteredWaza", Config.skillTemplates[0])

        self.pal.EquipWaza.clear()
        self.pal.MasteredWaza.clear()
        self.pal.MasteredWaza.append("EPalWazaID::WindCutter")
        self.pal.EquipWaza.append("EPalWazaID::WindCutter")
        applied = self.client.post(
            f"/api/pal/skill_templates/{template_id}/apply",
            json=self.request_data(),
            headers=self.headers,
        ).get_json()

        self.assertEqual(0, applied["status"])
        self.assertEqual(equipped, self.pal.EquipWaza)
        self.assertEqual(
            ["EPalWazaID::WindCutter", *equipped],
            self.pal.MasteredWaza,
        )
        self.assertEqual(equipped, applied["data"]["EquipWaza"])
        self.assertEqual(self.pal.MasteredWaza, applied["data"]["MasteredWaza"])

    def test_legacy_active_template_ignores_saved_mastered_skills(self):
        Config.skillTemplates = [
            {
                "Id": "legacy",
                "Name": "Legacy combat",
                "Type": "active",
                "EquipWaza": ["EPalWazaID::AirCanon"],
                "MasteredWaza": ["EPalWazaID::PowerShot"],
            }
        ]
        self.pal.EquipWaza.clear()
        self.pal.MasteredWaza.clear()
        self.pal.MasteredWaza.append("EPalWazaID::WindCutter")

        listed = self.client.get(
            "/api/pal/skill_templates", headers=self.headers
        ).get_json()
        self.assertNotIn("MasteredWaza", listed["data"][0])

        applied = self.client.post(
            "/api/pal/skill_templates/legacy/apply",
            json=self.request_data(),
            headers=self.headers,
        ).get_json()

        self.assertEqual(0, applied["status"])
        self.assertEqual(["EPalWazaID::AirCanon"], self.pal.EquipWaza)
        self.assertEqual(
            ["EPalWazaID::WindCutter", "EPalWazaID::AirCanon"],
            self.pal.MasteredWaza,
        )
        self.assertNotIn("EPalWazaID::PowerShot", self.pal.MasteredWaza)

    def test_base_worker_templates_are_supported(self):
        response = self.client.post(
            "/api/pal/skill_templates",
            json={
                "PlayerUId": "PAL_BASE_WORKER_BTN",
                "PalGuid": str(PAL_ID),
                "Name": "Camp",
                "Type": "passive",
            },
            headers=self.headers,
        ).get_json()
        self.assertEqual(0, response["status"])

    def test_templates_initialize_missing_skill_arrays(self):
        Config.skillTemplates = [
            {
                "Id": "passive",
                "Name": "Worker",
                "Type": "passive",
                "PassiveSkillList": ["CraftSpeed_up1"],
            },
            {
                "Id": "active",
                "Name": "Combat",
                "Type": "active",
                "EquipWaza": ["EPalWazaID::AirCanon"],
            },
        ]
        for key in ("PassiveSkillList", "EquipWaza", "MasteredWaza"):
            self.pal.pal_param.pop(key)

        for template_id in ("passive", "active"):
            response = self.client.post(
                f"/api/pal/skill_templates/{template_id}/apply",
                json=self.request_data(),
                headers=self.headers,
            ).get_json()
            self.assertEqual(0, response["status"])

        self.assertEqual(["CraftSpeed_up1"], self.pal.PassiveSkillList)
        self.assertEqual(["EPalWazaID::AirCanon"], self.pal.EquipWaza)
        self.assertEqual(["EPalWazaID::AirCanon"], self.pal.MasteredWaza)

    def test_invalid_template_requests_do_not_change_config_or_pal(self):
        original_passives = list(self.pal.PassiveSkillList)
        for payload in (
            self.request_data(Name="", Type="passive"),
            self.request_data(Name="Unknown", Type="other"),
        ):
            response = self.client.post(
                "/api/pal/skill_templates", json=payload, headers=self.headers
            ).get_json()
            self.assertEqual(1, response["status"])
        self.assertEqual([], Config.skillTemplates)
        self.assertEqual(original_passives, self.pal.PassiveSkillList)

        missing = self.client.post(
            "/api/pal/skill_templates/missing/apply",
            json=self.request_data(),
            headers=self.headers,
        ).get_json()
        self.assertEqual(1, missing["status"])
        self.assertEqual(original_passives, self.pal.PassiveSkillList)


if __name__ == "__main__":
    unittest.main()
