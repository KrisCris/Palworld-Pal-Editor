"""Creating, copying and deleting a Pal over REST (spec §8.3, §5.4).

The rules worth holding down here are the ones a save file pays for when they
break:

- a pasted Global Palbox record becomes a World Pal carrying its whole payload,
  because the target builds its own envelope rather than the source keeping one;
- a target that is not this owner's, and a record this editor cannot name, are
  both refused before anything is written -- a half-created Pal is a corrupt save;
- every write says which lists and storages it disturbed, so the client never
  guesses; a delete is the one whose `resultRecord` is null.

The fixture save is copied to a temp directory and mutated in memory only.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from flask_jwt_extended import create_access_token

from palworld_pal_editor.core.pal_storage_adapters import WorldPalAdapter
from palworld_pal_editor.core.save_manager import SaveManager
from palworld_pal_editor.webui import app


WORLD_FIXTURE = Path(__file__).parents[1] / "tests/saves/1.0/AF518B19A47340B8A55BC58137981393"
GPS_FIXTURE = Path(__file__).parents[1] / "tests/saves/1.0/GlobalPalStorage.sav"
LOSSY_UID = "a18b721d-0000-0000-0000-000000000000"
PLAYER_ROSTER = f"player:{LOSSY_UID}"
OPERATION_KEYS = {
    "resultRecord",
    "deletedRecordKeys",
    "affectedRosterKeys",
    "affectedStorageKeys",
}


class PalCreationApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous_manager = SaveManager._instance
        cls._temp = tempfile.TemporaryDirectory()
        world = Path(cls._temp.name, "world")
        shutil.copytree(WORLD_FIXTURE, world)
        shutil.copy2(GPS_FIXTURE, Path(cls._temp.name, "GlobalPalStorage.sav"))

        SaveManager._instance = None
        cls.manager = SaveManager()
        assert cls.manager.open(str(world)) is not None
        app.config["JWT_SECRET_KEY"] = "test-secret-key-with-at-least-32-bytes"
        with app.app_context():
            cls.token = create_access_token(identity="test", expires_delta=False)

    @classmethod
    def tearDownClass(cls):
        SaveManager._instance = cls.previous_manager
        cls._temp.cleanup()

    def setUp(self):
        self.client = app.test_client()
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.player = self.manager.get_player(LOSSY_UID)
        self.palbox = WorldPalAdapter.storage_key(self.player.PalStorageContainerId)

    def records(self, storage_kind: str) -> list:
        return [
            record
            for record in self.manager.pal_repository.records()
            if record.storage_kind == storage_kind
        ]

    def create(self, storage_key: str, source: dict, **body):
        return self.client.post(
            f"/api/storages/{storage_key}/pals",
            json={"source": source, **body},
            headers=self.headers,
        )

    def test_a_global_palbox_export_pasted_back_in_becomes_a_world_pal(self):
        source_record = self.records("global_palbox")[0]
        exported = self.client.get(
            f"/api/pals/{source_record.record_key}/native-record",
            headers=self.headers,
        )
        self.assertEqual(200, exported.status_code)

        response = self.create(
            self.palbox,
            {"kind": "native-record", "record": exported.get_json()},
            ownerUid=LOSSY_UID,
        )
        self.assertEqual(200, response.status_code, response.get_json())
        result = response.get_json()

        self.assertEqual(OPERATION_KEYS, set(result))
        created = result["resultRecord"]
        # The payload crossed formats whole; everywhere it now lives was written by
        # the target, and the source is still in the Global Palbox.
        self.assertEqual("world", created["storageKind"])
        self.assertEqual("created", created["changeState"])
        self.assertEqual(source_record.pal.CharacterID, created["CharacterID"])
        self.assertNotEqual(str(source_record.pal.InstanceId), created["InstanceId"])
        self.assertEqual(LOSSY_UID, created["OwnerPlayerUId"])
        self.assertEqual(self.palbox, created["storageKey"])
        self.assertEqual([PLAYER_ROSTER], result["affectedRosterKeys"])
        self.assertEqual([self.palbox], result["affectedStorageKeys"])
        self.assertEqual([], result["deletedRecordKeys"])
        self.assertIsNotNone(self.manager.get_record(source_record.record_key))

    def test_a_default_global_palbox_pal_belongs_to_the_storage_not_a_player(self):
        response = self.create("global-palbox", {"kind": "default"})
        self.assertEqual(200, response.status_code, response.get_json())
        result = response.get_json()

        self.assertEqual("global_palbox", result["resultRecord"]["storageKind"])
        self.assertIsNone(result["resultRecord"]["OwnerPlayerUId"])
        self.assertEqual(["global-palbox"], result["affectedRosterKeys"])
        self.assertEqual(["global-palbox"], result["affectedStorageKeys"])

    def test_a_container_that_is_not_this_owners_is_refused(self):
        before = len(self.records("world"))

        response = self.create(
            self.palbox,
            {"kind": "default"},
            ownerUid="00000000-0000-0000-0000-0000000000ff",
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual(
            "PAL_CREATE_REFUSED", response.get_json()["error"]["code"]
        )
        self.assertEqual(before, len(self.records("world")))

    def test_a_record_this_editor_cannot_name_creates_nothing(self):
        before = len(self.records("world"))

        response = self.create(
            self.palbox,
            {"kind": "native-record", "record": {"value": {"SaveParameter": {}}}},
            ownerUid=LOSSY_UID,
        )

        # Guessing here would write a Global Palbox entry into
        # CharacterSaveParameterMap, or the other way round.
        self.assertEqual(400, response.status_code)
        self.assertEqual(
            "PAL_RECORD_UNRECOGNISED", response.get_json()["error"]["code"]
        )
        self.assertEqual(before, len(self.records("world")))

    def test_a_duplicate_needs_no_target_and_leaves_its_source_alone(self):
        source = next(
            record
            for record in self.records("world")
            if str(record.pal.OwnerPlayerUId) == LOSSY_UID
        )

        response = self.client.post(
            f"/api/pals/{source.record_key}/duplicates",
            headers=self.headers,
        )
        self.assertEqual(200, response.status_code, response.get_json())
        result = response.get_json()
        clone = result["resultRecord"]

        # The roster comes from the Pal, not from whatever list the client had
        # open: the copy button is on the Pal and the two cannot disagree.
        self.assertEqual([PLAYER_ROSTER], result["affectedRosterKeys"])
        self.assertEqual(source.pal.CharacterID, clone["CharacterID"])
        self.assertNotEqual(str(source.pal.InstanceId), clone["InstanceId"])
        self.assertEqual("created", clone["changeState"])
        self.assertIsNotNone(self.manager.get_record(source.record_key))

    def test_deleting_a_pal_answers_with_what_is_gone(self):
        created = self.create(
            self.palbox, {"kind": "default"}, ownerUid=LOSSY_UID
        ).get_json()["resultRecord"]
        record_key = created["recordKey"]

        response = self.client.delete(
            f"/api/pals/{record_key}", headers=self.headers
        )
        self.assertEqual(200, response.status_code, response.get_json())
        result = response.get_json()

        # A delete is the one operation with no record to answer for, so the keys
        # it names are all the client has to act on.
        self.assertIsNone(result["resultRecord"])
        self.assertEqual([record_key], result["deletedRecordKeys"])
        self.assertEqual([PLAYER_ROSTER], result["affectedRosterKeys"])
        self.assertEqual([self.palbox], result["affectedStorageKeys"])
        self.assertIsNone(self.manager.get_record(record_key))
        self.assertEqual(
            404,
            self.client.get(f"/api/pals/{record_key}", headers=self.headers).status_code,
        )


if __name__ == "__main__":
    unittest.main()
