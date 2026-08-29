"""What the Pal write resources promise (spec §8.3).

`test_rest_session_api.py` covers reading a Pal and is read-only by design; these
are the writes. The rules they hold down are the ones the RPCs they replace either
broke or could not state:

- the allowlist is an allowlist, not "any property with a setter";
- every write answers with the one operation result, carrying the new detail;
- a skill list the game cannot resolve is refused before it reaches the save, and
  replacing the mastered list never leaves an unmastered skill equipped;
- healing everything reaches the Pals that do not live in the world save.

`test_webui_bootstrap.py`'s heal-all, batch-suitability and `FavoriteIndex` cases
are here now: S2b deleted the route they asked, and the rules they held are real.

The fixture save is opened once and mutated in memory only; nothing is written
back to disk.
"""

from pathlib import Path
import unittest

from flask_jwt_extended import create_access_token

from palworld_pal_editor.core.pal_objects import PalObjects
from palworld_pal_editor.core.save_manager import SaveManager
from palworld_pal_editor.webui import app


SAVE = Path(__file__).parents[1] / "tests/saves/1.0/8C439FF04713B5F986F9CAB485575089"
OPERATION_KEYS = {
    "resultRecord",
    "deletedRecordKeys",
    "affectedRosterKeys",
    "affectedStorageKeys",
}
KNOWN_PASSIVE = "PAL_ALLAttack_up2"
KNOWN_ATTACK = "EPalWazaID::FireBall"


class PalWriteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous_manager = SaveManager._instance
        SaveManager._instance = None
        cls.manager = SaveManager()
        assert cls.manager.open(str(SAVE)) is not None
        app.config["JWT_SECRET_KEY"] = "test-secret-key-with-at-least-32-bytes"
        with app.app_context():
            cls.token = create_access_token(identity="test", expires_delta=False)

    @classmethod
    def tearDownClass(cls):
        SaveManager._instance = cls.previous_manager

    def setUp(self):
        self.client = app.test_client()
        self.headers = {"Authorization": f"Bearer {self.token}"}
        # Every test asks what one edit did, so none of them may inherit the change
        # marks of whichever test happened to run first.
        self.manager.pal_repository.clear_modified()

    def record(self, offset: int = 0):
        """A different Pal per test, so one test's edits are not another's subject."""
        return self.manager.pal_repository.records()[offset]

    def global_record(self):
        """A Pal in the Global Palbox: nobody owns it and it is not in the world save."""
        return next(
            record
            for record in self.manager.pal_repository.records()
            if record.storage_kind == "global_palbox"
        )

    def patch(self, record, body: dict):
        return self.client.patch(
            f"/api/pals/{record.record_key}", json=body, headers=self.headers
        )

    def put_skills(self, record, group: str, skills: list):
        return self.client.put(
            f"/api/pals/{record.record_key}/skills/{group}",
            json={"skills": skills},
            headers=self.headers,
        )

    def heal(self, body: dict):
        return self.client.post("/api/pal-heals", json=body, headers=self.headers)

    def test_a_settable_field_the_allowlist_does_not_name_is_refused(self):
        # `Exp` is a `PalEntity` property with a setter, so the route this replaces
        # would have written it on the client's say-so. Being settable is no longer
        # what makes a field writable.
        record = self.record()
        before = record.pal.Exp
        response = self.patch(record, {"Exp": 1})

        self.assertEqual(400, response.status_code)
        error = response.get_json()["error"]
        self.assertEqual("PAL_FIELD_UNKNOWN", error["code"])
        self.assertNotIn("Exp", error["details"]["writable"])
        self.assertEqual(before, record.pal.Exp)

    def test_a_write_answers_with_the_operation_result_and_the_new_detail(self):
        record = self.record(1)
        response = self.patch(record, {"NickName": "Renamed By Test"})

        self.assertEqual(200, response.status_code)
        result = response.get_json()
        self.assertEqual(OPERATION_KEYS, set(result))
        self.assertEqual("Renamed By Test", result["resultRecord"]["NickName"])
        self.assertEqual("Renamed By Test", record.pal.NickName)
        # The change-set mark the frontend used to keep for itself.
        self.assertEqual("modified", result["resultRecord"]["changeState"])

    def test_a_pal_created_this_session_stays_created_when_it_is_edited(self):
        record = self.record(2)
        created = self.manager.pal_repository.snapshot_created()
        self.manager.pal_repository.restore_created(created | {record})
        try:
            result = self.patch(record, {"Level": 12}).get_json()
        finally:
            self.manager.pal_repository.restore_created(created)

        self.assertEqual("created", result["resultRecord"]["changeState"])

    def test_suitabilities_are_written_as_one_partial_map(self):
        # "Max every suitability" is one request, not one per work type.
        record = self.record(3)
        names = list(record.pal.MinimumWorkSuitabilities)[:2]
        self.assertEqual(2, len(names))

        result = self.patch(
            record, {"Suitabilities": {name: 4 for name in names}}
        ).get_json()

        for name in names:
            self.assertEqual(4, result["resultRecord"]["Suitabilities"][name])

    def test_the_pal_list_priority_is_a_writable_field(self):
        # `FavoriteIndex` is the Pal list's priority badge, and the only editor
        # control whose value is neither a number the UI computed nor a toggle.
        record = self.record(9)
        result = self.patch(record, {"FavoriteIndex": 3}).get_json()

        self.assertEqual(3, result["resultRecord"]["FavoriteIndex"])
        self.assertEqual(3, record.pal.FavoriteIndex)

    def test_a_skill_list_the_game_cannot_resolve_is_refused(self):
        record = self.record(4)
        before = list(record.pal.PassiveSkillList or [])

        unknown = self.put_skills(record, "passive", ["NotASkillInThisGame"])
        self.assertEqual(400, unknown.status_code)
        self.assertEqual("SKILL_UNKNOWN", unknown.get_json()["error"]["code"])

        twice = self.put_skills(record, "passive", [KNOWN_PASSIVE, KNOWN_PASSIVE])
        self.assertEqual(400, twice.status_code)
        self.assertEqual("SKILL_LIST_INVALID", twice.get_json()["error"]["code"])

        self.assertEqual(before, record.pal.PassiveSkillList or [])

    def test_the_passive_list_is_replaced_by_the_one_submitted(self):
        record = self.record(5)
        result = self.put_skills(record, "passive", [KNOWN_PASSIVE]).get_json()

        self.assertEqual([KNOWN_PASSIVE], result["resultRecord"]["PassiveSkillList"])
        self.assertEqual([KNOWN_PASSIVE], record.pal.PassiveSkillList)

    def test_unlearning_a_skill_unequips_it(self):
        # A Pal with an active slot holding a skill it has not mastered is a Pal the
        # game reads back wrong, so the mastered list can never be replaced alone.
        record = self.record(6)
        self.put_skills(record, "equipped", [KNOWN_ATTACK])
        self.assertIn(KNOWN_ATTACK, record.pal.MasteredWaza)

        result = self.put_skills(record, "mastered", []).get_json()

        self.assertEqual([], result["resultRecord"]["MasteredWaza"])
        self.assertEqual([], result["resultRecord"]["EquipWaza"])

    def maximize(self, record):
        return self.client.post(
            f"/api/pals/{record.record_key}/maximization", headers=self.headers
        )

    def test_maximization_raises_every_normal_upgrade_at_once(self):
        record = self.record(7)
        pal = record.pal
        response = self.maximize(record)

        self.assertEqual(200, response.status_code)
        detail = response.get_json()["resultRecord"]
        self.assertEqual(pal.MAX_LEVEL, detail["Level"])
        self.assertEqual(pal.MAX_FRIENDSHIP_LEVEL, detail["FriendshipLevel"])
        self.assertEqual(pal.MAX_CONDENSATION_RANK, detail["Rank"])
        self.assertEqual(pal.MAX_SOUL_RANK, detail["Rank_CraftSpeed"])
        self.assertEqual(pal.MAX_TALENT, detail["Talent_HP"])
        self.assertTrue(detail["IsAwakening"])
        self.assertTrue(all(level == 10 for level in detail["Suitabilities"].values()))
        self.assertEqual("modified", detail["changeState"])

    def test_a_pal_nobody_owns_can_be_maximized(self):
        # A record key is a record key: the route this replaces had to be told
        # which roster the Pal belonged to, and refused one it did not recognise.
        record = self.global_record()

        response = self.maximize(record)

        self.assertEqual(200, response.status_code)
        self.assertIsNone(response.get_json()["resultRecord"]["OwnerPlayerUId"])
        self.assertEqual(record.pal.MAX_LEVEL, record.pal.Level)

    def test_healing_one_pal_clears_its_sickness_and_its_faint(self):
        record = self.record(8)
        pal = record.pal
        pal.pal_param["WorkerSick"] = PalObjects.EnumProperty(
            "EPalBaseCampWorkerSickType",
            "EPalBaseCampWorkerSickType::DepressionSprain",
        )
        pal.pal_param["PalReviveTimer"] = PalObjects.FloatProperty(100.0)
        self.assertTrue(pal.HasWorkerSick and pal.IsFaintedPal)

        detail = self.heal(
            {"scope": "record", "recordKey": record.record_key}
        ).get_json()["resultRecord"]

        self.assertFalse(detail["HasWorkerSick"])
        self.assertFalse(detail["IsFaintedPal"])

    def test_healing_everything_reaches_the_pals_outside_the_world_save(self):
        # Nothing has to be selected first -- there is no roster or player in the
        # request. A Global Palbox Pal is also a copy that only reaches disk if its
        # storage is dirty, so a heal that skips normalization is silently undone.
        global_record = self.global_record()
        global_record.pal.SanityValue = 10.0
        self.manager._global_palbox.dirty = False

        result = self.heal({"scope": "all"}).get_json()

        self.assertEqual(100.0, global_record.pal.SanityValue)
        self.assertTrue(self.manager._global_palbox.dirty)
        self.assertIsNone(result["resultRecord"])
        # No single record answers for a heal that touched every list, so the
        # rosters to redraw are named instead.
        self.assertTrue(result["affectedRosterKeys"])

    def test_a_heal_must_say_what_it_is_healing(self):
        response = self.heal({})

        self.assertEqual(400, response.status_code)
        self.assertEqual("HEAL_SCOPE_INVALID", response.get_json()["error"]["code"])
