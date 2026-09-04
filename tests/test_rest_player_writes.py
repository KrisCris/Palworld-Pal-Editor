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
from palworld_pal_editor.utils.data_provider import DataProvider
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

    def test_placing_a_weapon_writes_the_dynamic_entry_it_needs(self):
        """A weapon is two records: the slot, and a dynamic item the slot points at.

        Nothing else covered this branch. A slot whose `dynamic_id` names no entry
        is the "dangling dynamic item GUID" the reader warns about, so writing one
        without the other is a broken inventory rather than a missing feature.
        """
        response = self.client.patch(
            f"/api/players/{self.uid}/inventory/1",
            json={"containerKind": "weapons", "itemId": "YakushimaBlade", "count": 1},
            headers=self.headers,
        )

        self.assertEqual(200, response.status_code)
        slot = response.get_json()["containers"]["weapons"]["slots"][1]
        self.assertEqual("YakushimaBlade", slot["static_id"])
        self.assertEqual("weapon", slot["dynamic_type"])
        self.assertIsNotNone(slot["dynamic_id"])
        self.assertIsNone(slot["warning"])
        # A new weapon arrives whole, and with the magazine the game data gives it.
        self.assertEqual(2222.0, slot["durability"])
        self.assertEqual(
            DataProvider.get_item("YakushimaBlade")["MagazineSize"], slot["ammo"]
        )

    def test_placing_armor_writes_a_dynamic_entry_without_the_weapon_fields(self):
        """Armor shares the durability half of the shape and none of the ammo half."""
        response = self.client.patch(
            f"/api/players/{self.uid}/inventory/4",
            json={"containerKind": "armor", "itemId": "Shield_03", "count": 1},
            headers=self.headers,
        )

        self.assertEqual(200, response.status_code)
        # Armor slots are group-constrained: ARMOR_SLOT_GROUPS puts Shield at 4.
        slot = response.get_json()["containers"]["armor"]["slots"][4]
        self.assertEqual("Shield_03", slot["static_id"])
        self.assertEqual("armor", slot["dynamic_type"])
        self.assertEqual(2250.0, slot["durability"])
        self.assertIsNone(slot["ammo"])
        self.assertIsNone(slot["warning"])

        raw = self.manager.item_container_data.dynamic_items[slot["dynamic_id"]]
        self.assertEqual(
            {"type", "id", "leading_bytes", "durability", "trailing_bytes"},
            set(raw["RawData"]["value"]),
        )

    def test_an_item_the_game_data_gives_no_durability_is_created_broken(self):
        """A known gap, pinned so it is a decision rather than a surprise.

        `MaxDurability` is 0 in the game data for grappling guns, sphere launchers
        and every NPC weapon, while real ones in a save carry 150-450. The NPC
        weapons are unreachable -- `_validate_item` refuses anything not `Legal` or
        `Disabled` -- but a grappling gun is neither, so it can be placed, and it is
        written with no durability at all. There is no better value available: the
        real maximum is in a game table this editor does not read.
        """
        self.assertEqual(0, DataProvider.get_item("GrapplingGun2")["MaxDurability"])

        response = self.client.patch(
            f"/api/players/{self.uid}/inventory/2",
            json={"containerKind": "weapons", "itemId": "GrapplingGun2", "count": 1},
            headers=self.headers,
        )

        self.assertEqual(200, response.status_code)
        slot = response.get_json()["containers"]["weapons"]["slots"][2]
        self.assertEqual(0.0, slot["durability"])

    def test_an_egg_cannot_be_placed_because_it_carries_a_pal(self):
        """The third dynamic type, and the one creation does not implement.

        An egg's dynamic entry holds a whole `PalIndividualCharacterSaveParameter`
        and 28 trailing bytes rather than 4, so there is nothing to build it from
        the way a weapon or a piece of armor is built. `_validate_item` refuses it
        up front, which is why `_new_dynamic_entry`'s own guard against it is
        unreachable from here -- this pins the reachable refusal.
        """
        self.assertEqual("egg", DataProvider.get_item("PalEgg_Dark_02")["DynamicType"])

        response = self.client.patch(
            f"/api/players/{self.uid}/inventory/3",
            json={"containerKind": "common", "itemId": "PalEgg_Dark_02", "count": 1},
            headers=self.headers,
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual(
            "INVENTORY_SLOT_INVALID", response.get_json()["error"]["code"]
        )

    def _place(self, container_kind, slot_index, item_id):
        response = self.client.patch(
            f"/api/players/{self.uid}/inventory/{slot_index}",
            json={"containerKind": container_kind, "itemId": item_id, "count": 1},
            headers=self.headers,
        )
        self.assertEqual(200, response.status_code)
        return response.get_json()["containers"][container_kind]["slots"][slot_index]

    def _wear_down(self, slot, to=1.0):
        """Damage the item in place, the way the game would have."""
        dynamic = self.manager.item_container_data.dynamic_items[slot["dynamic_id"]]
        dynamic["RawData"]["value"]["durability"] = to

    def test_repairing_restores_durability_without_replacing_the_item(self):
        """A repair is an edit to the dynamic entry, not a fresh item.

        Re-placing the item would restore durability too, and would also mint a new
        dynamic id and discard the weapon's ammunition and passive skills. Keeping
        the same dynamic id is what makes this a repair.
        """
        placed = self._place("weapons", 5, "YakushimaBlade")
        dynamic_id = placed["dynamic_id"]
        self._wear_down(placed, to=12.0)

        response = self.client.post(
            f"/api/players/{self.uid}/inventory/5/repairs",
            json={"containerKind": "weapons"},
            headers=self.headers,
        )

        self.assertEqual(200, response.status_code)
        slot = response.get_json()["containers"]["weapons"]["slots"][5]
        self.assertEqual(2222.0, slot["durability"])
        self.assertEqual(dynamic_id, slot["dynamic_id"])
        self.assertIsNone(slot["warning"])

    def test_repairing_armor_works_the_same_way(self):
        placed = self._place("armor", 4, "Shield_03")
        self._wear_down(placed, to=3.0)

        response = self.client.post(
            f"/api/players/{self.uid}/inventory/4/repairs",
            json={"containerKind": "armor"},
            headers=self.headers,
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            2250.0, response.get_json()["containers"]["armor"]["slots"][4]["durability"]
        )

    def test_an_item_with_no_known_maximum_is_refused_rather_than_zeroed(self):
        """The grappling gun case, which is why this is not `durability = max`.

        The game data gives it no maximum, so restoring one would mean writing 0
        over whatever durability the item actually has. Saying so is the only
        honest answer available.
        """
        placed = self._place("weapons", 3, "GrapplingGun2")
        self._wear_down(placed, to=40.0)

        response = self.client.post(
            f"/api/players/{self.uid}/inventory/3/repairs",
            json={"containerKind": "weapons"},
            headers=self.headers,
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual(
            "INVENTORY_REPAIR_REFUSED", response.get_json()["error"]["code"]
        )
        slot = self.manager.item_container_data.dynamic_items[placed["dynamic_id"]]
        self.assertEqual(40.0, slot["RawData"]["value"]["durability"])

    def test_repairing_something_with_no_durability_is_refused(self):
        """A piece of food is not a worn item: it has no dynamic entry at all."""
        self._place("food", 2, "BakedMeat_Boar")

        response = self.client.post(
            f"/api/players/{self.uid}/inventory/2/repairs",
            json={"containerKind": "food"},
            headers=self.headers,
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual(
            "INVENTORY_REPAIR_REFUSED", response.get_json()["error"]["code"]
        )

    def test_reading_the_inventory_of_a_player_who_is_not_there_is_a_404(self):
        response = self.client.get(
            "/api/players/not-a-player/inventory", headers=self.headers
        )

        self.assertEqual(404, response.status_code)
        self.assertEqual("PLAYER_NOT_FOUND", response.get_json()["error"]["code"])
