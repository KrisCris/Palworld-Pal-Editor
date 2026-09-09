"""The contract of the session, player, roster and Pal-detail resources (spec §8).

One representative test per resource rather than one per field: what matters to the
frontend is that a roster answers with record keys it can then fetch details for,
and that the summary's key set is fixed. Read-only apart from the session load, and
the save it loads is the checked-in fixture.
"""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from flask_jwt_extended import create_access_token

from palworld_pal_editor.config import Config
from palworld_pal_editor.core.save_io import SaveFailed
from palworld_pal_editor.core.save_manager import SaveManager
from palworld_pal_editor.webui import app


SAVE = Path(__file__).parents[1] / "tests/saves/1.0/8C439FF04713B5F986F9CAB485575089"

SESSION_KEYS = {"loaded", "path", "warnings"}
ROSTER_ENTRY_KEYS = {"rosterKey", "kind", "label", "playerUid"}
SUMMARY_KEYS = {
    "recordKey", "InstanceId", "CharacterID", "OwnerPlayerUId", "I18nName",
    "DisplayName", "IconAccessKey", "DataAccessKey", "Paldeck", "Gender",
    "FavoriteIndex", "IsBOSS", "IsRarePal", "IsTower", "IsAwakening",
    "IsImportedCharacter", "IsHuman", "IsExpeditionPal", "storageKey",
    "storageKind", "storageOwnerPlayerUid", "ContainerId", "SlotIndex",
    "containerKind", "containerLabel", "isAway", "changeState",
}


class RestContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous_manager = SaveManager._instance
        SaveManager._instance = None
        cls.manager = SaveManager()
        app.config["JWT_SECRET_KEY"] = "test-secret-key-with-at-least-32-bytes"
        with app.app_context():
            cls.token = create_access_token(identity="test", expires_delta=False)

    @classmethod
    def tearDownClass(cls):
        SaveManager._instance = cls.previous_manager

    def setUp(self):
        # The session tests leave a loaded save behind, but nothing may depend on
        # having run after them.
        if self.manager.gvas_file is None:
            self.assertIsNotNone(self.manager.open(str(SAVE)))
        self.client = app.test_client()
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def get(self, path):
        return self.client.get(path, headers=self.headers)

    def test_the_session_resource_reports_and_replaces_what_is_loaded(self):
        self.manager.reset()
        empty = self.get("/api/session")
        self.assertEqual(200, empty.status_code)
        self.assertEqual(
            {"loaded": False, "path": None, "warnings": []}, empty.get_json()
        )

        # Loading also remembers the path for next launch; that write is the config
        # file's business and not this test's.
        with patch.object(Config, "save_to_file"):
            loaded = self.client.put(
                "/api/session", json={"path": str(SAVE)}, headers=self.headers
            )

        self.assertEqual(200, loaded.status_code)
        body = loaded.get_json()
        self.assertEqual(SESSION_KEYS, set(body))
        self.assertTrue(body["loaded"])
        self.assertEqual(SAVE.resolve(), Path(body["path"]))
        self.assertEqual(body, self.get("/api/session").get_json())

    def test_saving_writes_where_it_is_told_without_moving_the_session(self):
        """`POST /api/session/saves` is one save, not a change of session.

        A save-as answers with the path it wrote and leaves the session pointing at
        the save that is open, so the next reload opens that one and not the copy.
        """
        loaded = self.get("/api/session").get_json()["path"]

        with tempfile.TemporaryDirectory(prefix="pal-editor-rest-save-") as directory:
            response = self.client.post(
                "/api/session/saves", json={"path": directory}, headers=self.headers
            )

            self.assertEqual(201, response.status_code)
            self.assertEqual({"path": directory}, response.get_json())
            self.assertTrue((Path(directory) / "Level.sav").exists())

        self.assertEqual(loaded, self.get("/api/session").get_json()["path"])

    def test_a_save_that_failed_says_where_the_untouched_copy_is(self):
        """The one thing the error envelope has to carry that a message cannot.

        When the restore failed too, that backup folder is the only complete copy of
        the save left, so the code alone is not enough for the frontend to say what
        the user must do next.
        """
        failure = SaveFailed(
            "disk full", backup_path=Path("/backups/2026-08-30"), restored=False
        )
        with patch.object(SaveManager, "save", side_effect=failure):
            response = self.client.post(
                "/api/session/saves", json={"path": "/somewhere"}, headers=self.headers
            )

        self.assertEqual(400, response.status_code)
        error = response.get_json()["error"]
        self.assertEqual("SAVE_FAILED", error["code"])
        self.assertEqual(str(Path("/backups/2026-08-30")), error["details"]["backupPath"])
        self.assertFalse(error["details"]["restored"])

    def test_players_are_listed_and_fetched_by_uid(self):
        listed = self.get("/api/players").get_json()
        self.assertTrue(listed)

        first = listed[0]
        fetched = self.get(f"/api/players/{first['InstanceId']}")
        self.assertEqual(200, fetched.status_code)
        self.assertEqual(first, fetched.get_json())

    def test_a_roster_answers_with_summaries_whose_keys_fetch_details(self):
        rosters = self.get("/api/rosters").get_json()
        self.assertTrue(rosters)
        for entry in rosters:
            self.assertEqual(ROSTER_ENTRY_KEYS, set(entry))

        player_roster = next(e for e in rosters if e["kind"] == "player")
        summaries = self.get(f"/api/rosters/{player_roster['rosterKey']}/pals")
        self.assertEqual(200, summaries.status_code)
        rows = summaries.get_json()
        self.assertTrue(rows)
        for row in rows:
            self.assertEqual(SUMMARY_KEYS, set(row))

        # The list carries record keys and nothing more; the editor's fields arrive
        # only when one Pal is asked for.
        row = rows[0]
        detail = self.get(f"/api/pals/{row['recordKey']}")
        self.assertEqual(200, detail.status_code)
        body = detail.get_json()
        self.assertEqual(row, {key: body[key] for key in SUMMARY_KEYS})
        for field in ("PassiveSkillList", "EquipWaza", "Talent_HP", "Suitabilities"):
            self.assertIn(field, body)

    def test_every_roster_the_listing_offers_can_be_read(self):
        for entry in self.get("/api/rosters").get_json():
            with self.subTest(entry["rosterKey"]):
                response = self.get(f"/api/rosters/{entry['rosterKey']}/pals")
                self.assertEqual(200, response.status_code)

    def test_a_failure_comes_back_as_the_error_envelope(self):
        for path, status, code in (
            ("/api/pals/world:not-a-pal", 404, "PAL_NOT_FOUND"),
            ("/api/rosters/not-a-roster/pals", 404, "ROSTER_NOT_FOUND"),
            ("/api/players/not-a-player", 404, "PLAYER_NOT_FOUND"),
        ):
            with self.subTest(path):
                response = self.get(path)
                self.assertEqual(status, response.status_code)
                error = response.get_json()["error"]
                self.assertEqual(code, error["code"])
                self.assertEqual({"code", "message", "details"}, set(error))

        with self.subTest("a path that is not a save"):
            with patch.object(Config, "save_to_file"):
                response = self.client.put(
                    "/api/session",
                    json={"path": str(SAVE / "Players")},
                    headers=self.headers,
                )
            self.assertEqual(400, response.status_code)
            self.assertEqual("SAVE_LOAD_FAILED", response.get_json()["error"]["code"])

    def test_an_unexpected_failure_returns_its_traceback_to_the_reporter(self):
        """Spec §8.7: the user filing the report is the one who needs the trace."""
        with patch.object(
            SaveManager, "get_players", side_effect=RuntimeError("boom")
        ):
            response = self.get("/api/players")

        self.assertEqual(500, response.status_code)
        error = response.get_json()["error"]
        self.assertEqual("UNEXPECTED_ERROR", error["code"])
        self.assertIn("RuntimeError: boom", error["details"]["traceback"])


if __name__ == "__main__":
    unittest.main()
