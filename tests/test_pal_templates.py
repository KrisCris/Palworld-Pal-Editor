import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flask_jwt_extended import create_access_token

from palworld_pal_editor.config import Config
from palworld_pal_editor.core.pal_entity import PalEntity
from palworld_pal_editor.core.pal_objects import PalObjects, toUUID
from palworld_pal_editor.core.pal_storage import PalRecordRef
from palworld_pal_editor.webui import app

PLAYER_ID = toUUID("11111111-1111-1111-1111-111111111111")
PAL_ID = toUUID("22222222-2222-2222-2222-222222222222")


def make_pal() -> PalEntity:
    pal_obj = PalObjects.PalSaveParameter(
        PAL_ID,
        PLAYER_ID,
        PalObjects.EMPTY_UUID,
        0,
        PalObjects.EMPTY_UUID,
    )
    parameter = pal_obj["value"]["RawData"]["value"]["object"]["SaveParameter"][
        "value"
    ]
    PalObjects.set_BaseType(parameter["NickName"], "Template Lamball")
    return PalEntity(pal_obj)


class FakeManager:
    def __init__(self, pal):
        self.pal = pal
        self.added = []

    def get_unique_world_record(self, _instance_id):
        return PalRecordRef(
            f"world:{self.pal.InstanceId}",
            "world-container:test",
            "world",
            0,
            self.pal,
        )

    def get_player(self, _player_id):
        return type("Player", (), {"NickName": "Target"})()

    def add_pal(self, player_id, pal_obj=None, target_container_id=None):
        self.added.append((player_id, pal_obj, target_container_id))
        result = PalEntity(copy.deepcopy(pal_obj or self.pal._pal_obj))
        result.is_new_pal = True
        return result

    def create_pal(self, roster_key, target_storage_key, pal_obj=None, pal_owner_uid=None):
        self.added.append((roster_key, target_storage_key, pal_obj))
        result = PalEntity(copy.deepcopy(pal_obj or self.pal._pal_obj))
        result.is_new_pal = True
        return PalRecordRef(
            f"world:{result.InstanceId}",
            target_storage_key,
            "world",
            0,
            result,
        )


class PalTemplateApiTests(unittest.TestCase):
    def setUp(self):
        self.previous_templates = getattr(Config, "palTemplates", None)
        Config.palTemplates = []
        self.pal = make_pal()
        self.manager = FakeManager(self.pal)
        self.client = app.test_client()
        with app.app_context():
            token = create_access_token(identity="test")
        self.headers = {"Authorization": f"Bearer {token}"}
        self.patches = [
            patch("palworld_pal_editor.api.pal.SaveManager", return_value=self.manager),
            patch("palworld_pal_editor.core.save_manager.SaveManager", return_value=self.manager),
            patch.object(Config, "save_to_file"),
        ]
        self.started_patches = [item.start() for item in self.patches]
        self.save_config = self.started_patches[-1]

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        if self.previous_templates is None:
            del Config.palTemplates
        else:
            Config.palTemplates = self.previous_templates

    def test_template_crud_returns_metadata_without_raw_save_data(self):
        response = self.client.post(
            "/api/pal/templates",
            json={"PlayerUId": str(PLAYER_ID), "PalGuid": str(PAL_ID), "Name": "Worker"},
            headers=self.headers,
        ).get_json()

        self.assertEqual(0, response["status"])
        template_id = response["data"]["Id"]
        listing = self.client.get("/api/pal/templates", headers=self.headers).get_json()
        self.assertEqual("Worker", listing["data"][0]["Name"])
        self.assertEqual("SheepBall", listing["data"][0]["CharacterID"])
        self.assertNotIn("PalData", listing["data"][0])

        created = self.client.post(
            "/api/pal/add_pal",
            json={
                "PlayerUId": str(PLAYER_ID),
                "RosterKey": str(PLAYER_ID),
                "TargetStorageKey": "world-container:test",
                "Mode": "template",
                "TemplateId": template_id,
            },
            headers=self.headers,
        ).get_json()
        self.assertEqual(0, created["status"])
        self.assertIsInstance(self.manager.added[-1][2], dict)

        deleted = self.client.delete(
            f"/api/pal/templates/{template_id}", headers=self.headers
        ).get_json()
        self.assertEqual(0, deleted["status"])
        self.assertEqual([], Config.palTemplates)

    def test_json_import_accepts_dump_data_and_rejects_invalid_objects(self):
        imported = self.client.post(
            "/api/pal/add_pal",
            json={
                "PlayerUId": str(PLAYER_ID),
                "RosterKey": str(PLAYER_ID),
                "TargetStorageKey": "world-container:test",
                "Mode": "json",
                "PalJson": self.pal.dump_obj(),
            },
            headers=self.headers,
        ).get_json()
        self.assertEqual(0, imported["status"])
        self.assertIsInstance(self.manager.added[-1][2], dict)

        calls = len(self.manager.added)
        invalid = self.client.post(
            "/api/pal/add_pal",
            json={
                "PlayerUId": str(PLAYER_ID),
                "RosterKey": str(PLAYER_ID),
                "TargetStorageKey": "world-container:test",
                "Mode": "json",
                "PalJson": '{"not": "a pal"}',
            },
            headers=self.headers,
        ).get_json()
        self.assertEqual(1, invalid["status"])
        self.assertEqual(calls, len(self.manager.added))

    def test_add_pal_forwards_an_explicit_storage_target(self):
        created = self.client.post(
            "/api/pal/add_pal",
            json={
                "PlayerUId": str(PLAYER_ID),
                "RosterKey": str(PLAYER_ID),
                "TargetStorageKey": "world-container:target",
                "Mode": "json",
                "PalJson": self.pal.dump_obj(),
            },
            headers=self.headers,
        ).get_json()

        self.assertEqual(0, created["status"])
        self.assertEqual("world-container:target", self.manager.added[-1][1])

    def test_base_worker_add_requires_a_storage_target(self):
        rejected = self.client.post(
            "/api/pal/add_pal",
            json={"PlayerUId": "PAL_BASE_WORKER_BTN", "Mode": "default"},
            headers=self.headers,
        ).get_json()
        self.assertEqual(1, rejected["status"])
        self.assertIn("base container", (rejected["msg"] or "").lower())

        created = self.client.post(
            "/api/pal/add_pal",
            json={
                "PlayerUId": "PAL_BASE_WORKER_BTN",
                "RosterKey": "PAL_BASE_WORKER_BTN",
                "TargetStorageKey": "world-container:base",
                "Mode": "default",
            },
            headers=self.headers,
        ).get_json()
        self.assertEqual(0, created["status"])
        self.assertEqual("PAL_BASE_WORKER_BTN", self.manager.added[-1][0])
        self.assertEqual("world-container:base", self.manager.added[-1][1])

    def test_template_names_and_import_sizes_are_bounded(self):
        invalid_name = self.client.post(
            "/api/pal/templates",
            json={"PlayerUId": str(PLAYER_ID), "PalGuid": str(PAL_ID), "Name": " "},
            headers=self.headers,
        ).get_json()
        self.assertEqual(1, invalid_name["status"])

        oversized = self.client.post(
            "/api/pal/add_pal",
            json={
                "PlayerUId": str(PLAYER_ID),
                "Mode": "json",
                "PalJson": "x" * (2 * 1024 * 1024 + 1),
            },
            headers=self.headers,
        ).get_json()
        self.assertEqual(1, oversized["status"])
        self.assertEqual([], self.manager.added)

    def test_invalid_and_failed_template_writes_do_not_leave_ghost_entries(self):
        with patch.object(
            self.pal,
            "dump_obj",
            return_value="x" * (2 * 1024 * 1024 + 1),
        ):
            invalid = self.client.post(
                "/api/pal/templates",
                json={"PlayerUId": str(PLAYER_ID), "PalGuid": str(PAL_ID), "Name": "Huge"},
                headers=self.headers,
            ).get_json()
        self.assertEqual(1, invalid["status"])
        self.assertEqual([], Config.palTemplates)
        self.save_config.assert_not_called()

        self.save_config.side_effect = OSError("disk full")
        failed = self.client.post(
            "/api/pal/templates",
            json={"PlayerUId": str(PLAYER_ID), "PalGuid": str(PAL_ID), "Name": "Worker"},
            headers=self.headers,
        )
        self.assertEqual(500, failed.status_code)
        self.assertEqual([], Config.palTemplates)

    def test_failed_template_delete_restores_the_in_memory_entry(self):
        created = self.client.post(
            "/api/pal/templates",
            json={"PlayerUId": str(PLAYER_ID), "PalGuid": str(PAL_ID), "Name": "Worker"},
            headers=self.headers,
        ).get_json()
        template_id = created["data"]["Id"]
        self.save_config.side_effect = OSError("disk full")

        failed = self.client.delete(
            f"/api/pal/templates/{template_id}", headers=self.headers
        )

        self.assertEqual(500, failed.status_code)
        self.assertEqual(template_id, Config.palTemplates[0]["Id"])

class ConfigPersistenceTests(unittest.TestCase):
    def test_config_write_replaces_the_previous_file_only_after_serializing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "config.json")
            path.write_text('{"keep": true}', encoding="utf-8")
            with patch(
                "palworld_pal_editor.config.json.dump",
                side_effect=OSError("serialization failed"),
            ):
                with self.assertRaises(OSError):
                    Config.save_to_file(str(path))
            self.assertEqual({"keep": True}, json.loads(path.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
