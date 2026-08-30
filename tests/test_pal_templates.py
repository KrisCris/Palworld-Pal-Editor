import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flask_jwt_extended import create_access_token

from palworld_pal_editor.config import Config
from palworld_pal_editor.core.pal_objects import PalObjects, dumps, toUUID
from palworld_pal_editor.core.pal_record import PalRecord
from palworld_pal_editor.core.pal_storage_adapters import WorldPalAdapter
from palworld_pal_editor.core.pal_templates import (
    migrate_pal_templates,
    template_source,
)
from fakes import record_location, world_record
from palworld_pal_editor.webui import app
from palworld_pal_editor.core.pal_repository import PalRepository

PLAYER_ID = toUUID("11111111-1111-1111-1111-111111111111")
PAL_ID = toUUID("22222222-2222-2222-2222-222222222222")
CLONE_ID = toUUID("33333333-3333-3333-3333-333333333333")


def make_record() -> PalRecord:
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
    return world_record(pal_obj, storage_key="world-container:test")


class FakeManager:
    def __init__(self, record):
        self.record = record
        self.added = []
        self.pal_repository = PalRepository()
        # Exporting a record is its own adapter's job, and this fake holds a World
        # record; the adapter needs no session to answer for one.
        self.world_adapter = WorldPalAdapter([], None)

    def get_unique_world_record(self, _instance_id):
        return self.record

    def get_player(self, _player_id):
        return type("Player", (), {"NickName": "Target"})()

    def resolve_record_location(self, record):
        return record_location(record)

    def _created(self, save_parameter, storage_key):
        """What the real create pipeline hands back: a fresh record in the target.

        The payload arrives on its own, so a record has to be built around it here
        the same way an adapter would -- which is also what proves the route sent a
        payload rather than a record.
        """
        result = world_record(
            WorldPalAdapter.native_record(
                save_parameter,
                instance_id=CLONE_ID,
                owner_uid=PLAYER_ID,
                container_id=PalObjects.EMPTY_UUID,
                slot_index=0,
                group_id=PalObjects.EMPTY_UUID,
            ),
            storage_key=storage_key,
        )
        self.pal_repository.register(result, created=True)
        return result

    def add_pal(self, player_id, save_parameter=None, target_container_id=None):
        self.added.append((player_id, save_parameter, target_container_id))
        return self._created(
            save_parameter, f"world-container:{target_container_id}"
        )

    def create_pal(
        self, roster_key, target_storage_key, save_parameter=None, pal_owner_uid=None
    ):
        self.added.append((roster_key, target_storage_key, save_parameter))
        return self._created(save_parameter, target_storage_key)


class PalTemplateApiTests(unittest.TestCase):
    def setUp(self):
        self.previous_templates = getattr(Config, "palTemplates", None)
        Config.palTemplates = []
        self.record = make_record()
        self.pal = self.record.pal
        self.manager = FakeManager(self.record)
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
                "PalJson": dumps(self.record.native_record),
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
                "PalJson": dumps(self.record.native_record),
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
        with patch(
            "palworld_pal_editor.api.pal._native_record",
            return_value={"not": "a pal"},
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

class PalTemplateMigrationTests(unittest.TestCase):
    """The 1.0.x upgrade, which runs once against real users saved templates.

    These are the only tests standing between a user template file and being
    rewritten wrong, so they check what actually reaches disk rather than what the
    function returned.
    """

    def setUp(self):
        self.previous_templates = getattr(Config, "palTemplates", None)
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name, "config.json")
        # Migration writes the config itself, so the only way to test what it wrote
        # is to point the write somewhere this test owns.
        self.original_save = Config.__dict__["save_to_file"]
        Config.save_to_file = lambda: self.original_save.__func__(
            Config, str(self.path)
        )
        self.addCleanup(self.directory.cleanup)
        self.addCleanup(self.restore)

    def restore(self):
        Config.save_to_file = self.original_save
        if self.previous_templates is None:
            del Config.palTemplates
        else:
            Config.palTemplates = self.previous_templates

    def old_template(self, template_id: str, name: str, nickname: str) -> dict:
        pal_obj = PalObjects.PalSaveParameter(
            PAL_ID, PLAYER_ID, PalObjects.EMPTY_UUID, 0, PalObjects.EMPTY_UUID
        )
        parameter = pal_obj["value"]["RawData"]["value"]["object"]["SaveParameter"]
        PalObjects.set_BaseType(parameter["value"]["NickName"], nickname)
        return {"Id": template_id, "Name": name, "PalData": dumps(pal_obj)}

    def test_an_old_string_template_becomes_native_and_survives_a_reload(self):
        Config.palTemplates = [self.old_template("a", "Worker", "Old Timer")]

        migrate_pal_templates()

        self.assertIsInstance(Config.palTemplates[0]["PalData"], dict)
        Config.palTemplates = []
        Config.load_from_file(str(self.path))
        self.assertEqual("Worker", Config.palTemplates[0]["Name"])
        source = template_source(Config.palTemplates[0])
        self.assertEqual("world", source.kind)
        self.assertEqual("Old Timer", source.entity().NickName)

    def test_a_template_that_cannot_be_read_is_kept_exactly_as_it_was(self):
        broken = {"Id": "b", "Name": "Broken", "PalData": "{not json"}
        Config.palTemplates = [broken, self.old_template("c", "Good", "Keeper")]

        migrate_pal_templates()

        # Deleting or blanking it would throw away the only copy the user has; the
        # entry stays put and its readable neighbour is upgraded around it.
        self.assertEqual("{not json", Config.palTemplates[0]["PalData"])
        self.assertIsInstance(Config.palTemplates[1]["PalData"], dict)
        Config.palTemplates = []
        Config.load_from_file(str(self.path))
        self.assertEqual("{not json", Config.palTemplates[0]["PalData"])

    def test_nothing_to_upgrade_writes_nothing(self):
        native = self.old_template("d", "Already", "Native")
        native["PalData"] = json.loads(native["PalData"])
        Config.palTemplates = [native, {"Id": "e", "Name": "Broken", "PalData": 7}]

        migrate_pal_templates()

        self.assertFalse(self.path.exists())

    def test_a_failed_write_leaves_the_old_templates_in_memory(self):
        old = self.old_template("f", "Worker", "Old Timer")
        Config.palTemplates = [old]
        Config.save_to_file = lambda: (_ for _ in ()).throw(OSError("disk full"))

        with self.assertRaises(OSError):
            migrate_pal_templates()

        self.assertEqual([old], Config.palTemplates)


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
