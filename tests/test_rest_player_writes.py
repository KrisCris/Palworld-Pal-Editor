"""What `PATCH /api/players/{playerUid}` and its inventory sub-resource promise.

`test_rest_session_api.py` covers reading a player and is read-only by design;
these are the writes. Four rules, each of which the routes these replace either
broke or could not state:

- the allowlist is an allowlist, not "any property with a setter";
- a write answers with the resource, so the client never reads back what it
  just wrote;
- writing the technology list leaves the spelling the save already uses alone;
- patching one inventory slot answers with the whole inventory.

The fixture save is opened once and mutated in memory only; nothing is written
back to disk.
"""

from pathlib import Path
import unittest

from flask_jwt_extended import create_access_token

from palworld_pal_editor.core.save_manager import SaveManager
from palworld_pal_editor.webui import app


SAVE = Path(__file__).parents[1] / "tests/saves/1.0/8C439FF04713B5F986F9CAB485575089"
INVENTORY_KEYS = {"containers", "warnings"}


class PlayerWriteTests(unittest.TestCase):
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
        self.player = self.manager.get_players()[0]
        self.uid = str(self.player.PlayerUId)

    def patch(self, body: dict):
        return self.client.patch(
            f"/api/players/{self.uid}", json=body, headers=self.headers
        )

    def test_a_settable_field_the_allowlist_does_not_name_is_refused(self):
        # `Exp` is a `PlayerEntity` property with a setter, so the route this
        # replaces would have written it on the client's say-so. Being settable
        # is no longer what makes a field writable.
        before = self.player.Exp
        response = self.patch({"Exp": 1})

        self.assertEqual(400, response.status_code)
        error = response.get_json()["error"]
        self.assertEqual("PLAYER_FIELD_UNKNOWN", error["code"])
        self.assertNotIn("Exp", error["details"]["writable"])
        self.assertEqual(before, self.player.Exp)

    def test_a_write_answers_with_the_player_it_changed(self):
        response = self.patch({"NickName": "Renamed By Test"})

        self.assertEqual(200, response.status_code)
        self.assertEqual("Renamed By Test", response.get_json()["NickName"])
        self.assertEqual("Renamed By Test", self.player.NickName)

    def test_writing_the_technology_list_keeps_the_spelling_in_the_save(self):
        stored = self.player.UnlockedRecipeTechnologyNames[0]
        dropped = self.player.UnlockedRecipeTechnologyNames[1]
        keep = [
            tech
            for tech in self.player.UnlockedRecipeTechnologyNames
            if tech != dropped
        ]

        response = self.patch(
            {
                "UnlockedRecipeTechnologyNames": (
                    # The same technology, spelled the way a catalog would.
                    [stored.upper() if stored.islower() else stored.lower()]
                    + keep[1:]
                    + ["PalCondenser"]
                ),
            }
        )

        self.assertEqual(200, response.status_code)
        unlocked = response.get_json()["UnlockedRecipeTechnologyNames"]
        self.assertIn(stored, unlocked)
        self.assertNotIn(dropped, unlocked)
        self.assertIn("PalCondenser", unlocked)
        # And the request's own spelling did not become a second entry.
        self.assertEqual(
            len(unlocked), len({tech.casefold() for tech in unlocked})
        )

    def test_patching_one_slot_answers_with_the_whole_inventory(self):
        response = self.client.patch(
            f"/api/players/{self.uid}/inventory/0",
            json={"containerKind": "food", "itemId": "Curry", "count": 42},
            headers=self.headers,
        )

        self.assertEqual(200, response.status_code)
        inventory = response.get_json()
        self.assertEqual(INVENTORY_KEYS, set(inventory))
        slot = inventory["containers"]["food"]["slots"][0]
        self.assertEqual("Curry", slot["static_id"])
        self.assertEqual(42, slot["count"])

    def test_reading_the_inventory_of_a_player_who_is_not_there_is_a_404(self):
        response = self.client.get(
            "/api/players/not-a-player/inventory", headers=self.headers
        )

        self.assertEqual(404, response.status_code)
        self.assertEqual("PLAYER_NOT_FOUND", response.get_json()["error"]["code"])
