"""Saved Pal and skill templates over REST (spec §8.5, §6.2).

Templates are the one thing this API stores outside the save file, so the rules
that matter are about what reaches the template file and what a template can do
to a Pal:

- a saved Pal is the native DOM, an object rather than JSON encoded twice, and it
  creates back into a different storage format than the one it came out of;
- a write that cannot be persisted leaves no entry behind in memory;
- applying an active template equips *and* learns, which is the invariant the
  skills PUT already holds, because both go through `pals.SKILL_GROUPS`;
- a template naming a skill this build has no data for is refused before it
  touches the Pal -- templates outlive game updates.

The fixture save is copied to a temp directory and mutated in memory only, and
both template lists are restored around every test.
"""

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flask_jwt_extended import create_access_token

from palworld_pal_editor.core.templates import pal_templates, skill_templates
from palworld_pal_editor.core.pal_storage_adapters import WorldPalAdapter
from palworld_pal_editor.core.save_manager import SaveManager
from palworld_pal_editor.webui import app


WORLD_FIXTURE = Path(__file__).parents[1] / "tests/saves/1.0/AF518B19A47340B8A55BC58137981393"
GPS_FIXTURE = Path(__file__).parents[1] / "tests/saves/1.0/GlobalPalStorage.sav"
LOSSY_UID = "a18b721d-0000-0000-0000-000000000000"
KNOWN_ATTACK = "EPalWazaID::FireBall"
OTHER_ATTACK = "EPalWazaID::AirCanon"
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
        self.previous = (list(pal_templates()), list(skill_templates()))
        pal_templates()[:] = []
        skill_templates()[:] = []
        self.saved_config = patch(
            "palworld_pal_editor.api.templates.save_templates"
        ).start()
        self.addCleanup(patch.stopall)
        self.addCleanup(self.restore)

    def restore(self):
        pal_templates()[:], skill_templates()[:] = self.previous

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
        self.assertIsInstance(pal_templates()[0]["PalData"], dict)
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
        self.assertEqual([], pal_templates())

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
        self.assertEqual([], skill_templates())

    def test_a_template_naming_a_skill_this_game_lacks_does_not_touch_the_pal(self):
        target = self.world_records()[0]
        target.pal.replace_PassiveSkillList([KNOWN_PASSIVE])
        skill_templates()[:] = [
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


    def test_a_template_saved_before_this_release_still_equips_what_it_named(self):
        """A skill template is user data older than any of this code.

        Templates saved by earlier versions also stored `MasteredWaza`, and
        replaying that list would hand a Pal skills its owner had unlearned. The
        equipped list is the whole template; learning follows from equipping.
        """
        target = self.world_records()[0]
        target.pal.replace_EquipWaza([])
        target.pal.replace_MasteredWaza([KNOWN_ATTACK])
        skill_templates()[:] = [
            {
                "Id": "legacy",
                "Name": "Legacy combat",
                "Type": "active",
                "EquipWaza": [OTHER_ATTACK],
                "MasteredWaza": ["EPalWazaID::PowerShot"],
            }
        ]

        listed = self.client.get("/api/skill-templates", headers=self.headers).get_json()
        self.assertNotIn("MasteredWaza", listed[0])

        applied = self.client.post(
            f"/api/pals/{target.record_key}/skill-template-applications",
            json={"templateId": "legacy"},
            headers=self.headers,
        )
        self.assertEqual(200, applied.status_code, applied.get_json())
        result = applied.get_json()["resultRecord"]

        self.assertEqual([OTHER_ATTACK], result["EquipWaza"])
        # What the Pal already knew stays known, what it now equips is learned,
        # and the template's own stale mastered list reaches nothing.
        self.assertEqual([KNOWN_ATTACK, OTHER_ATTACK], result["MasteredWaza"])

    def test_a_template_applies_to_a_pal_whose_save_has_no_skill_lists(self):
        """A Pal that has never had a skill has no array to replace.

        The save file omits these properties entirely rather than storing an empty
        one, so applying a template has to create them.
        """
        target = self.world_records()[0]
        original = {
            key: target.pal.pal_param.pop(key)
            for key in ("PassiveSkillList", "EquipWaza", "MasteredWaza")
            if key in target.pal.pal_param
        }
        self.addCleanup(target.pal.pal_param.update, original)
        skill_templates()[:] = [
            {
                "Id": "passive",
                "Name": "Worker",
                "Type": "passive",
                "PassiveSkillList": [KNOWN_PASSIVE],
            },
            {
                "Id": "active",
                "Name": "Combat",
                "Type": "active",
                "EquipWaza": [KNOWN_ATTACK],
            },
        ]

        for template_id in ("passive", "active"):
            response = self.client.post(
                f"/api/pals/{target.record_key}/skill-template-applications",
                json={"templateId": template_id},
                headers=self.headers,
            )
            self.assertEqual(200, response.status_code, response.get_json())

        self.assertEqual([KNOWN_PASSIVE], target.pal.PassiveSkillList)
        self.assertEqual([KNOWN_ATTACK], target.pal.EquipWaza)
        self.assertEqual([KNOWN_ATTACK], target.pal.MasteredWaza)

    def test_a_template_this_editor_cannot_store_is_refused_before_config_is_touched(self):
        record = self.world_records()[0]
        cases = (
            ({"name": "  ", "type": "passive"}, "TEMPLATE_NAME_REQUIRED"),
            ({"name": "x" * 65, "type": "passive"}, "TEMPLATE_NAME_TOO_LONG"),
            ({"name": "Fine", "type": "sideways"}, "SKILL_TEMPLATE_TYPE_UNKNOWN"),
        )
        for body, code in cases:
            with self.subTest(code=code):
                response = self.client.post(
                    "/api/skill-templates",
                    json={**body, "recordKey": record.record_key},
                    headers=self.headers,
                )
                self.assertEqual(400, response.status_code)
                self.assertEqual(code, response.get_json()["error"]["code"])

        # The list is bounded because it is written back to the config file whole.
        skill_templates()[:] = [
            {"Id": str(index), "Name": str(index), "Type": "passive"}
            for index in range(50)
        ]
        full = self.client.post(
            "/api/skill-templates",
            json={"name": "One more", "type": "passive", "recordKey": record.record_key},
            headers=self.headers,
        )
        self.assertEqual(400, full.status_code)
        self.assertEqual("TEMPLATE_LIMIT_REACHED", full.get_json()["error"]["code"])
        self.assertEqual(50, len(skill_templates()))

        missing = self.client.post(
            f"/api/pals/{record.record_key}/skill-template-applications",
            json={"templateId": "no-such-template"},
            headers=self.headers,
        )
        self.assertEqual(404, missing.status_code)
        self.assertEqual(
            "SKILL_TEMPLATE_NOT_FOUND", missing.get_json()["error"]["code"]
        )
        self.assertFalse(self.saved_config.called)

    def test_a_delete_that_cannot_be_persisted_keeps_the_template(self):
        record = self.world_records()[0]
        template_id = self.client.post(
            "/api/pal-templates",
            json={"name": "Worker", "recordKey": record.record_key},
            headers=self.headers,
        ).get_json()["templateId"]
        self.saved_config.side_effect = OSError("disk full")

        response = self.client.delete(
            f"/api/pal-templates/{template_id}", headers=self.headers
        )

        self.assertEqual(500, response.status_code)
        # The file still has it, so the list the user is looking at must too --
        # the same rule as a failed create, in the other direction.
        self.assertEqual([template_id], [item["Id"] for item in pal_templates()])


if __name__ == "__main__":
    unittest.main()
