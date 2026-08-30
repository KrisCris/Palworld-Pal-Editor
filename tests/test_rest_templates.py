"""Saved Pal and skill templates over REST (spec §8.5, §6.2).

Templates are the one thing this API stores outside the save file, so the rules
that matter are about what reaches `Config` and what a template can do to a Pal:

- a saved Pal is the native DOM, an object rather than JSON encoded twice, and it
  creates back into a different storage format than the one it came out of;
- a write that cannot be persisted leaves no entry behind in memory;
- applying an active template equips *and* learns, which is the invariant the
  skills PUT already holds, because both go through `pals.SKILL_GROUPS`;
- a template naming a skill this build has no data for is refused before it
  touches the Pal -- templates outlive game updates.

The fixture save is copied to a temp directory and mutated in memory only, and
`Config.palTemplates` / `Config.skillTemplates` are restored around every test.
"""

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flask_jwt_extended import create_access_token

from palworld_pal_editor.config import Config
from palworld_pal_editor.core.pal_storage_adapters import WorldPalAdapter
from palworld_pal_editor.core.save_manager import SaveManager
from palworld_pal_editor.webui import app


WORLD_FIXTURE = Path(__file__).parents[1] / "tests/saves/1.0/AF518B19A47340B8A55BC58137981393"
GPS_FIXTURE = Path(__file__).parents[1] / "tests/saves/1.0/GlobalPalStorage.sav"
LOSSY_UID = "a18b721d-0000-0000-0000-000000000000"
KNOWN_ATTACK = "EPalWazaID::FireBall"
KNOWN_PASSIVE = "PAL_ALLAttack_up2"


class TemplateApiTests(unittest.TestCase):
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
        self.previous = (Config.palTemplates, Config.skillTemplates)
        Config.palTemplates = []
        Config.skillTemplates = []
        self.saved_config = patch.object(Config, "save_to_file").start()
        self.addCleanup(patch.stopall)
        self.addCleanup(self.restore)

    def restore(self):
        Config.palTemplates, Config.skillTemplates = self.previous

    def world_records(self) -> list:
        return [
            record
            for record in self.manager.pal_repository.records()
            if record.storage_kind == "world"
            and str(record.pal.OwnerPlayerUId) == LOSSY_UID
        ]

    def test_a_global_palbox_pal_saved_as_a_template_creates_into_a_world_palbox(self):
        source = next(
            record
            for record in self.manager.pal_repository.records()
            if record.storage_kind == "global_palbox"
        )
        source.pal.NickName = "Kept"

        saved = self.client.post(
            "/api/pal-templates",
            json={"name": "Worker", "recordKey": source.record_key},
            headers=self.headers,
        )
        self.assertEqual(200, saved.status_code, saved.get_json())
        template_id = saved.get_json()["templateId"]

        # The stored payload is the native DOM, not JSON encoded a second time
        # into a string: that second encoding is what §6.2 deletes.
        self.assertIsInstance(Config.palTemplates[0]["PalData"], dict)
        listing = self.client.get("/api/pal-templates", headers=self.headers).get_json()
        self.assertEqual(["Worker"], [item["name"] for item in listing])
        self.assertNotIn("PalData", listing[0])

        created = self.client.post(
            f"/api/storages/{self.palbox}/pals",
            json={
                "source": {"kind": "template", "templateId": template_id},
                "ownerUid": LOSSY_UID,
            },
            headers=self.headers,
        )
        self.assertEqual(200, created.status_code, created.get_json())
        record = created.get_json()["resultRecord"]
        # Out of the Global Palbox and into a World container: the template carries
        # the payload, the target builds its own envelope.
        self.assertEqual("world", record["storageKind"])
        self.assertEqual("Kept", record["NickName"])
        self.assertEqual(source.pal.CharacterID, record["CharacterID"])

        deleted = self.client.delete(
            f"/api/pal-templates/{template_id}", headers=self.headers
        )
        self.assertEqual(204, deleted.status_code)
        self.assertEqual([], self.client.get(
            "/api/pal-templates", headers=self.headers
        ).get_json())

    def test_a_template_that_cannot_be_persisted_leaves_nothing_behind(self):
        record = self.world_records()[0]
        self.saved_config.side_effect = OSError("disk full")

        response = self.client.post(
            "/api/pal-templates",
            json={"name": "Worker", "recordKey": record.record_key},
            headers=self.headers,
        )

        self.assertEqual(500, response.status_code)
        # A template the user cannot see on the next launch must not be in the
        # list they are looking at now.
        self.assertEqual([], Config.palTemplates)

    def test_an_active_skill_template_equips_and_learns_on_the_pal_it_is_applied_to(self):
        source, target = self.world_records()[:2]
        source.pal.replace_EquipWaza([KNOWN_ATTACK])
        target.pal.replace_MasteredWaza([])

        saved = self.client.post(
            "/api/skill-templates",
            json={"name": "Fire", "type": "active", "recordKey": source.record_key},
            headers=self.headers,
        )
        self.assertEqual(200, saved.status_code, saved.get_json())
        self.assertEqual([KNOWN_ATTACK], saved.get_json()["EquipWaza"])

        applied = self.client.post(
            f"/api/pals/{target.record_key}/skill-template-applications",
            json={"templateId": saved.get_json()["templateId"]},
            headers=self.headers,
        )
        self.assertEqual(200, applied.status_code, applied.get_json())
        result = applied.get_json()["resultRecord"]

        # An equipped skill is always a mastered one; the template goes through the
        # same `replace_EquipWaza` the skills PUT uses, so it cannot forget that.
        self.assertEqual([KNOWN_ATTACK], result["EquipWaza"])
        self.assertIn(KNOWN_ATTACK, result["MasteredWaza"])
        self.assertEqual("modified", result["changeState"])

    def test_renaming_a_skill_template_keeps_the_skills_it_saved(self):
        record = self.world_records()[0]
        record.pal.replace_PassiveSkillList([KNOWN_PASSIVE])
        template_id = self.client.post(
            "/api/skill-templates",
            json={"name": "Old", "type": "passive", "recordKey": record.record_key},
            headers=self.headers,
        ).get_json()["templateId"]

        renamed = self.client.patch(
            f"/api/skill-templates/{template_id}",
            json={"name": "New"},
            headers=self.headers,
        ).get_json()

        self.assertEqual("New", renamed["name"])
        self.assertEqual([KNOWN_PASSIVE], renamed["PassiveSkillList"])
        self.assertEqual(
            204,
            self.client.delete(
                f"/api/skill-templates/{template_id}", headers=self.headers
            ).status_code,
        )
        self.assertEqual([], Config.skillTemplates)

    def test_a_template_naming_a_skill_this_game_lacks_does_not_touch_the_pal(self):
        target = self.world_records()[0]
        target.pal.replace_PassiveSkillList([KNOWN_PASSIVE])
        Config.skillTemplates = [
            {
                "Id": "stale",
                "Name": "From a later patch",
                "Type": "passive",
                "PassiveSkillList": ["PAL_SkillFromAFutureUpdate"],
            }
        ]

        response = self.client.post(
            f"/api/pals/{target.record_key}/skill-template-applications",
            json={"templateId": "stale"},
            headers=self.headers,
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual("SKILL_UNKNOWN", response.get_json()["error"]["code"])
        self.assertEqual([KNOWN_PASSIVE], target.pal.PassiveSkillList)


if __name__ == "__main__":
    unittest.main()
