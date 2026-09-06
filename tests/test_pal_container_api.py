import copy
import unittest
from unittest.mock import patch

from flask_jwt_extended import create_access_token

from palworld_pal_editor.webui import app
from palworld_pal_editor.core.pal_entity import PalEntity
from palworld_pal_editor.core.pal_objects import PalObjects, toUUID
from palworld_pal_editor.core.pal_storage import PalRecordRef


class FakeManager:
    def __init__(self):
        self.moves = []
        self.transfers = []
        instance_id = toUUID("10000000-0000-0000-0000-000000000001")
        world_pal = PalEntity(
            PalObjects.PalSaveParameter(
                instance_id,
                PalObjects.EMPTY_UUID,
                PalObjects.EMPTY_UUID,
                0,
                PalObjects.EMPTY_UUID,
            )
        )
        world_pal.set_owner_player_uid(None)
        world_pal.NickName = "World copy"
        gps_pal = PalEntity(copy.deepcopy(world_pal._pal_obj))
        gps_pal.NickName = "GPS copy"
        self.records = {
            f"world:{instance_id}": PalRecordRef(
                f"world:{instance_id}",
                "world-container:box",
                "world",
                0,
                world_pal,
            ),
            "gps:0": PalRecordRef(
                "gps:0", "global-palbox", "global_palbox", 0, gps_pal
            ),
        }

    def get_container_registry(self):
        return [
            {
                "ContainerId": "target",
                "ContainerKind": "base",
                "ContainerLabel": "Main Base",
                "Size": 50,
                "Occupied": 12,
                "MovableInto": True,
            }
        ]

    def move_pal(self, pal_id, target_container_id):
        self.moves.append((pal_id, target_container_id))
        return True

    def transfer_pal(self, source_key, target_key, action, expected_key=None):
        self.transfers.append((source_key, target_key, action, expected_key))
        return {"RecordKey": "dps:owner:0", "StorageKey": target_key}

    def get_pal(self, _pal_id):
        return None

    def get_record(self, record_key):
        return self.records.get(record_key)

    def get_unique_world_record(self, instance_id):
        return self.records.get(f"world:{instance_id}")

    def resolve_record_location(self, record):
        return {
            "RecordedContainerId": None,
            "RecordedSlotIndex": record.pal.SlotIndex,
            "ActualContainerId": None,
            "ActualSlotIndex": record.slot_index,
            "ActualLocations": [],
            "LocationStatus": "ok",
            "LocationAnomaly": None,
            "ContainerKind": record.storage_kind,
            "ContainerLabel": record.storage_key,
        }


class PalContainerApiTests(unittest.TestCase):
    def setUp(self):
        self.manager = FakeManager()
        self.client = app.test_client()
        with app.app_context():
            token = create_access_token(identity="test")
        self.headers = {"Authorization": f"Bearer {token}"}
        self.patch = patch(
            "palworld_pal_editor.api.pal.SaveManager", return_value=self.manager
        )
        self.patch.start()

    def tearDown(self):
        self.patch.stop()

    def test_container_registry_endpoint_returns_normalized_descriptors(self):
        response = self.client.get(
            "/api/pal/containers", headers=self.headers
        ).get_json()

        self.assertEqual(0, response["status"])
        self.assertEqual("target", response["data"][0]["ContainerId"])
        self.assertEqual("Main Base", response["data"][0]["ContainerLabel"])

    def test_transfer_endpoint_requires_storage_qualified_keys(self):
        missing = self.client.post(
            "/api/pal/transfer",
            json={"SourceRecordKey": "world:pal"},
            headers=self.headers,
        ).get_json()
        self.assertEqual(1, missing["status"])

    def test_transfer_endpoint_uses_storage_qualified_keys(self):
        moved = self.client.post(
            "/api/pal/transfer",
            json={
                "SourceRecordKey": "world:pal",
                "TargetStorageKey": "dps:owner",
                "Action": "move",
            },
            headers=self.headers,
        ).get_json()

        self.assertEqual(0, moved["status"])
        self.assertEqual("dps:owner:0", moved["data"]["RecordKey"])
        self.assertEqual(
            [("world:pal", "dps:owner", "move", None)],
            self.manager.transfers,
        )

    def test_paldata_selects_record_key_when_instance_id_is_shared(self):
        gps = self.client.post(
            "/api/pal/paldata",
            json={"RecordKey": "gps:0"},
            headers=self.headers,
        ).get_json()
        world = self.client.post(
            "/api/pal/paldata",
            json={"RecordKey": next(iter(self.manager.records))},
            headers=self.headers,
        ).get_json()

        self.assertEqual("GPS copy", gps["data"]["NickName"])
        self.assertEqual("World copy", world["data"]["NickName"])
        self.assertEqual("gps:0", gps["data"]["RecordKey"])


if __name__ == "__main__":
    unittest.main()
