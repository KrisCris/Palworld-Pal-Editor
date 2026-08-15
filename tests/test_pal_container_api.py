import unittest
from unittest.mock import patch

from flask_jwt_extended import create_access_token

from palworld_pal_editor.webui import app


class FakeManager:
    def __init__(self):
        self.moves = []
        self.transfers = []

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

    def test_move_endpoint_requires_ids_and_delegates_source_resolution(self):
        missing = self.client.post(
            "/api/pal/move", json={"PalGuid": "pal"}, headers=self.headers
        ).get_json()
        moved = self.client.post(
            "/api/pal/move",
            json={"PalGuid": "pal", "TargetContainerId": "target"},
            headers=self.headers,
        ).get_json()

        self.assertEqual(1, missing["status"])
        self.assertEqual(0, moved["status"])
        self.assertEqual([("pal", "target")], self.manager.moves)

    def test_transfer_endpoint_uses_storage_qualified_keys(self):
        moved = self.client.post(
            "/api/pal/move",
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


if __name__ == "__main__":
    unittest.main()
