"""The contract of the app-level and catalog resources (spec §8.4, §8.6).

Four rules worth pinning, all of them about what the backend refuses to do:
browsing for a save does not move any server-side cursor, a config PATCH writes
only the two preferences it names, the bootstrap read answers before there is a
token to answer with, and the catalogs answer with no save open at all. The
guild-research cases cover the route's own scope validation;
`test_guild_lab_research.py` owns what completion does to the save. What each
catalog's rows actually contain belongs to the tests for that data --
`test_pal_family_provider.py`, `test_game_skill_data.py`, `test_pal_identity.py`.
"""

from pathlib import Path
import unittest
from unittest.mock import patch

from flask_jwt_extended import create_access_token

from palworld_pal_editor.config import Config
from palworld_pal_editor.core.save_manager import SaveManager
from palworld_pal_editor.webui import app


SAVES = Path(__file__).parents[1] / "tests/saves/1.0"
RESEARCH_SAVE = SAVES / "AF518B19A47340B8A55BC58137981393"

APP_CONFIG_KEYS = {
    "i18n", "i18nOptions", "defaultSavePath", "hasPassword", "version",
    "isOfficialBuild", "donationPromptDismissed",
}
SAVE_PATH_KEYS = {"currentPath", "parentPath", "children", "isPalDir"}


class AppResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["JWT_SECRET_KEY"] = "test-secret-key-with-at-least-32-bytes"
        with app.app_context():
            cls.token = create_access_token(identity="test", expires_delta=False)

    def setUp(self):
        self.client = app.test_client()
        self.headers = {"Authorization": f"Bearer {self.token}"}
        # Every write below goes through Config; none of them may reach the real
        # config.json, and none may outlive its own test.
        self.addCleanup(setattr, Config, "i18n", Config.i18n)
        self.addCleanup(setattr, Config, "path", Config.path)
        self.addCleanup(
            setattr, Config, "shownDonateInfo", dict(Config.shownDonateInfo)
        )
        saving = patch.object(Config, "save_to_file")
        self.saved_config = saving.start()
        self.addCleanup(saving.stop)

    def get(self, path):
        return self.client.get(path, headers=self.headers)

    def test_browsing_for_a_save_never_moves_the_servers_own_path(self):
        """The bug §8.6 names: a read used to write `Config.path`.

        That made "go up one level" a cursor every client shared, so two browsers
        open at once walked each other's directories. Walking down and back up
        here has to leave the server exactly where it started.
        """
        Config.path = str(RESEARCH_SAVE)

        down = self.get(f"/api/save-paths?path={SAVES}")
        self.assertEqual(200, down.status_code)
        listing = down.get_json()
        self.assertEqual(SAVE_PATH_KEYS, set(listing))
        self.assertEqual(SAVES.resolve(), Path(listing["currentPath"]))
        self.assertIn(str(RESEARCH_SAVE.resolve()), listing["children"])

        # Up is the client asking for the parent it was just told about -- the
        # only thing that replaces the old PATCH-to-go-back route.
        parent = listing["parentPath"]
        up = self.get(f"/api/save-paths?path={parent}")
        self.assertEqual(200, up.status_code)
        self.assertEqual(
            SAVES.parent.resolve(), Path(up.get_json()["currentPath"])
        )

        self.assertEqual(str(RESEARCH_SAVE), Config.path)
        self.saved_config.assert_not_called()

    def test_a_directory_that_is_not_there_is_a_404_and_not_a_crash(self):
        missing = self.get(f"/api/save-paths?path={SAVES / 'no-such-save'}")
        self.assertEqual(404, missing.status_code)
        self.assertEqual("PATH_NOT_FOUND", missing.get_json()["error"]["code"])

    def test_the_bootstrap_read_answers_without_a_token(self):
        """It is how the client learns whether it has to authenticate at all."""
        response = self.client.get("/api/app-config")
        self.assertEqual(200, response.status_code)
        body = response.get_json()
        self.assertEqual(APP_CONFIG_KEYS, set(body))
        self.assertEqual(bool(Config.password), body["hasPassword"])

    def test_app_config_writes_only_the_two_preferences_it_names(self):
        """A PATCH that reflected onto Config attributes would also write these."""
        for field, value in (
            ("password", "hunter2"),
            ("JWT_SECRET_KEY", "stolen"),
            ("port", 1),
        ):
            with self.subTest(field=field):
                before = getattr(Config, field)
                response = self.client.patch(
                    "/api/app-config", json={field: value}, headers=self.headers
                )
                self.assertEqual(400, response.status_code)
                self.assertEqual(
                    "APP_CONFIG_FIELD_UNKNOWN", response.get_json()["error"]["code"]
                )
                self.assertEqual(before, getattr(Config, field))
        self.saved_config.assert_not_called()

    def test_app_config_accepts_the_preferences_and_reports_them_back(self):
        response = self.client.patch(
            "/api/app-config",
            json={"i18n": "ja", "donationPromptDismissed": True},
            headers=self.headers,
        )
        self.assertEqual(200, response.status_code)
        body = response.get_json()
        self.assertEqual("ja", body["i18n"])
        self.assertTrue(body["donationPromptDismissed"])
        self.assertEqual("ja", Config.i18n)
        self.saved_config.assert_called()

        rejected = self.client.patch(
            "/api/app-config", json={"i18n": "not-a-locale"}, headers=self.headers
        )
        self.assertEqual(400, rejected.status_code)
        self.assertEqual("I18N_NOT_AVAILABLE", rejected.get_json()["error"]["code"])
        self.assertEqual("ja", Config.i18n)


class GuildResearchResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous_manager = SaveManager._instance
        SaveManager._instance = None
        cls.manager = SaveManager()
        # The research tree only exists for a loaded save, and completing it is a
        # write -- so this fixture is opened once and mutated in memory only.
        assert cls.manager.open(str(RESEARCH_SAVE)) is not None
        app.config["JWT_SECRET_KEY"] = "test-secret-key-with-at-least-32-bytes"
        with app.app_context():
            cls.token = create_access_token(identity="test", expires_delta=False)

    @classmethod
    def tearDownClass(cls):
        SaveManager._instance = cls.previous_manager

    def setUp(self):
        self.client = app.test_client()
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def guild_id(self) -> str:
        research = self.client.get("/api/guild-research", headers=self.headers)
        self.assertEqual(200, research.status_code)
        return research.get_json()["Guilds"][0]["GuildId"]

    def test_completing_a_scope_reports_what_it_moved_and_the_new_tree(self):
        guild_id = self.guild_id()
        response = self.client.patch(
            f"/api/guild-research/{guild_id}",
            json={"all": True},
            headers=self.headers,
        )
        self.assertEqual(200, response.status_code)
        body = response.get_json()
        self.assertGreater(body["changed"], 0)

        guild = next(
            entry
            for entry in body["research"]["Guilds"]
            if entry["GuildId"] == guild_id
        )
        for category in guild["Categories"]:
            with self.subTest(category=category["Category"]):
                self.assertEqual(category["Total"], category["Completed"])

        # Nothing is left to do, so a repeat moves nothing -- and still answers
        # with the tree rather than an error.
        again = self.client.patch(
            f"/api/guild-research/{guild_id}",
            json={"all": True},
            headers=self.headers,
        )
        self.assertEqual(200, again.status_code)
        self.assertEqual(0, again.get_json()["changed"])

    def test_a_request_must_name_exactly_one_completion_scope(self):
        guild_id = self.guild_id()
        for payload in ({}, {"all": True, "category": "Handcraft"}, {"all": False}):
            with self.subTest(payload=payload):
                response = self.client.patch(
                    f"/api/guild-research/{guild_id}",
                    json=payload,
                    headers=self.headers,
                )
                self.assertEqual(400, response.status_code)
                self.assertEqual(
                    "RESEARCH_SCOPE_INVALID", response.get_json()["error"]["code"]
                )

    def test_an_unknown_guild_or_research_id_is_a_404_envelope(self):
        for guild_id, payload in (
            ("not-a-guild", {"all": True}),
            (self.guild_id(), {"researchId": "NotAResearch"}),
            (self.guild_id(), {"category": "NotACategory"}),
        ):
            with self.subTest(guild_id=guild_id, payload=payload):
                response = self.client.patch(
                    f"/api/guild-research/{guild_id}",
                    json=payload,
                    headers=self.headers,
                )
                self.assertEqual(404, response.status_code)
                self.assertEqual(
                    "RESEARCH_NOT_AVAILABLE", response.get_json()["error"]["code"]
                )


class CatalogResourceTests(unittest.TestCase):
    """§8.4's one real rule: the catalogs are the game's data, not the save's.

    Every one of them used to be reachable only from a `/api/save/` route, which
    said nothing about whether opening a save was a precondition. It never was,
    and this is what keeps it that way.
    """

    CATALOG_KEYS = {
        "pals": {"pals"},
        "skills": {"passive", "active"},
        "items": {"items"},
        "technologies": {"byLevel"},
        "skins": {"skins"},
    }

    @classmethod
    def setUpClass(cls):
        cls.previous_manager = SaveManager._instance
        SaveManager._instance = None
        app.config["JWT_SECRET_KEY"] = "test-secret-key-with-at-least-32-bytes"
        with app.app_context():
            cls.token = create_access_token(identity="test", expires_delta=False)

    @classmethod
    def tearDownClass(cls):
        SaveManager._instance = cls.previous_manager

    def test_every_catalog_answers_with_no_save_loaded(self):
        client = app.test_client()
        headers = {"Authorization": f"Bearer {self.token}"}
        for name, keys in self.CATALOG_KEYS.items():
            with self.subTest(catalog=name):
                response = client.get(f"/api/catalogs/{name}", headers=headers)
                self.assertEqual(200, response.status_code)
                body = response.get_json()
                self.assertEqual(keys, set(body))
                self.assertTrue(all(body[key] for key in keys))
