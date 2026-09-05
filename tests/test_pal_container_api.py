import threading
import unittest
from unittest.mock import patch

from flask_jwt_extended import create_access_token

from palworld_pal_editor.webui import app
import copy

from palworld_pal_editor.core.pal_objects import PalObjects, toUUID
from palworld_pal_editor.core.pal_mutations import set_owner
from palworld_pal_editor.core.pal_record import PalRecord
from palworld_pal_editor.core.pal_storage_adapters import GpsPalAdapter
from palworld_pal_editor.core.pal_repository import PalRepository
from fakes import FakeStorageDirectory, world_record


class FakeManager:
    def __init__(self):
        self.session_lock = threading.RLock()
        self.pal_repository = PalRepository()
        instance_id = toUUID("10000000-0000-0000-0000-000000000001")
        world_obj = PalObjects.PalSaveParameter(
            instance_id,
            PalObjects.EMPTY_UUID,
            PalObjects.EMPTY_UUID,
            0,
            PalObjects.EMPTY_UUID,
        )
        world_entry = world_record(world_obj, storage_key="world-container:box")
        set_owner(world_entry.pal, None)
        world_entry.pal.NickName = "World copy"
        gps_entry = {
            "InstanceId": {
                "value": {"InstanceId": PalObjects.Guid(instance_id)},
            },
            "SaveParameter": copy.deepcopy(
                world_obj["value"]["RawData"]["value"]["object"]["SaveParameter"]
            ),
        }
        gps_record = PalRecord(
            record_key="gps:0",
            storage_kind="global_palbox",
            storage_key="global-palbox",
            slot_index=0,
            native_record=gps_entry,
            pal=GpsPalAdapter.entity(gps_entry),
        )
        gps_record.pal.NickName = "GPS copy"
        self.records = {
            f"world:{instance_id}": world_entry,
            "gps:0": gps_record,
        }

    def get_pal(self, _pal_id):
        return None

    def get_player(self, _player_uid):
        return None

    def get_record(self, record_key):
        return self.records.get(record_key)

    @property
    def storage_directory(self):
        return FakeStorageDirectory()


class PalContainerApiTests(unittest.TestCase):
    def setUp(self):
        self.manager = FakeManager()
        self.client = app.test_client()
        with app.app_context():
            token = create_access_token(identity="test")
        self.headers = {"Authorization": f"Bearer {token}"}
        self.patches = [
            patch(f"{module}.SaveManager", return_value=self.manager)
            # Every module that reaches for the session, not just the route one:
            # `require_record` and `pal_detail` each look it up in their own.
            for module in (
                "palworld_pal_editor.api.operations",
                "palworld_pal_editor.api.pal_serializers",
                "palworld_pal_editor.api.pal_transfers",
                "palworld_pal_editor.api.pals",
            )
        ]
        for started in self.patches:
            started.start()

    def tearDown(self):
        for started in self.patches:
            started.stop()

    def test_a_transfer_names_one_record_and_one_storage_or_it_is_refused(self):
        """Both halves of a transfer are keys, and neither has a default.

        An Instance ID is not an address and a container id is not a storage key, so
        a request missing either half is refused before the session is touched
        rather than resolved to whatever the Pal happens to be nearest to.
        """
        for payload in (
            {"sourceRecordKey": "world:pal"},
            {"targetStorageKey": "dps:owner"},
            {},
        ):
            with self.subTest(payload=payload):
                response = self.client.post(
                    "/api/pal-transfers", json=payload, headers=self.headers
                )

                self.assertEqual(400, response.status_code)
                self.assertEqual(
                    "PAL_TRANSFER_INVALID",
                    response.get_json()["error"]["code"],
                )

    def test_pal_detail_selects_record_key_when_instance_id_is_shared(self):
        """The premise the whole design rests on: an Instance ID is not an address.

        Both of these Pals carry the same `InstanceId` -- one in the World, one in
        the Global Palbox -- so only the record key can say which one is meant.
        """
        gps = self.client.get(
            "/api/pals/gps:0", headers=self.headers
        ).get_json()
        world_key = next(iter(self.manager.records))
        world = self.client.get(
            f"/api/pals/{world_key}", headers=self.headers
        ).get_json()

        self.assertEqual("GPS copy", gps["NickName"])
        self.assertEqual("World copy", world["NickName"])
        self.assertEqual("gps:0", gps["recordKey"])


if __name__ == "__main__":
    unittest.main()
