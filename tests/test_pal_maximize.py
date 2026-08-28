import unittest
from unittest.mock import patch

from flask_jwt_extended import create_access_token

from palworld_pal_editor.core.pal_entity import PalEntity
from palworld_pal_editor.core.pal_objects import PalObjects, toUUID
from fakes import record_location, world_record
from palworld_pal_editor.webui import app


PLAYER_ID = toUUID("11111111-1111-1111-1111-111111111111")
PAL_ID = toUUID("22222222-2222-2222-2222-222222222222")


def make_pal(character_id: str = "SheepBall") -> PalEntity:
    pal_obj = PalObjects.PalSaveParameter(
        PAL_ID,
        PLAYER_ID,
        PalObjects.EMPTY_UUID,
        0,
        PalObjects.EMPTY_UUID,
    )
    parameter = pal_obj["value"]["RawData"]["value"]["object"]["SaveParameter"][
        "value"
    ]
    PalObjects.set_BaseType(parameter["CharacterID"], character_id)
    parameter.pop("OwnerPlayerUId", None)
    pal = PalEntity(pal_obj)
    pal.Level = 5
    pal.FriendshipLevel = 1
    pal.Rank = 2
    pal.RankUpExp = 9
    pal.Rank_HP = 1
    pal.Rank_Attack = 2
    pal.Rank_Defence = 3
    pal.Rank_CraftSpeed = 4
    pal.Talent_HP = 10
    pal.Talent_Melee = 17
    pal.Talent_Shot = 20
    pal.Talent_Defense = 30
    return pal


class FakeManager:
    def __init__(self, pal):
        self.pal = pal

    def get_unique_world_record(self, _instance_id):
        return world_record(self.pal, storage_key="world-container:test")

    def get_player(self, _player_id):
        return type("Player", (), {"NickName": "Target"})()

    def normalize_external_record(self, _record):
        pass

    def resolve_record_location(self, record):
        return record_location(record)


class PalMaximizeTests(unittest.TestCase):
    def setUp(self):
        self.pal = make_pal()

    def test_maximize_progression_uses_only_normal_gameplay_limits(self):
        original_character_id = self.pal.CharacterID
        original_melee = self.pal.Talent_Melee
        suitability_keys = set(self.pal.MinimumWorkSuitabilities or {})
        self.assertTrue(suitability_keys)

        self.pal.maximize_progression()

        self.assertEqual(PalEntity.MAX_LEVEL, self.pal.Level)
        self.assertEqual(PalEntity.MAX_FRIENDSHIP_LEVEL, self.pal.FriendshipLevel)
        self.assertEqual(PalEntity.MAX_CONDENSATION_RANK, self.pal.Rank)
        self.assertEqual(0, self.pal.RankUpExp)
        self.assertEqual(
            [PalEntity.MAX_SOUL_RANK] * 4,
            [
                self.pal.Rank_HP,
                self.pal.Rank_Attack,
                self.pal.Rank_Defence,
                self.pal.Rank_CraftSpeed,
            ],
        )
        self.assertEqual(
            [PalEntity.MAX_TALENT] * 3,
            [self.pal.Talent_HP, self.pal.Talent_Shot, self.pal.Talent_Defense],
        )
        self.assertEqual(original_melee, self.pal.Talent_Melee)
        self.assertTrue(self.pal.IsAwakening)
        self.assertEqual(suitability_keys, set(self.pal.WorkSuitabilities or {}))
        self.assertTrue(
            all(value == 10 for value in (self.pal.WorkSuitabilities or {}).values())
        )
        self.assertEqual(original_character_id, self.pal.CharacterID)

    def test_maximize_endpoint_returns_the_complete_updated_pal(self):
        manager = FakeManager(self.pal)
        client = app.test_client()
        with app.app_context():
            token = create_access_token(identity="test")
        headers = {"Authorization": f"Bearer {token}"}

        with (
            patch("palworld_pal_editor.api.pal.SaveManager", return_value=manager),
            patch(
                "palworld_pal_editor.core.save_manager.SaveManager",
                return_value=manager,
            ),
        ):
            response = client.post(
                "/api/pal/maximize",
                json={"PlayerUId": str(PLAYER_ID), "PalGuid": str(PAL_ID)},
                headers=headers,
            ).get_json()

        self.assertEqual(0, response["status"])
        self.assertEqual(80, response["data"]["Level"])
        self.assertEqual(10, response["data"]["FriendshipLevel"])
        self.assertEqual(5, response["data"]["Rank"])
        self.assertEqual(20, response["data"]["Rank_CraftSpeed"])
        self.assertEqual(100, response["data"]["Talent_HP"])
        self.assertTrue(response["data"]["IsAwakening"])
        self.assertTrue(
            all(value == 10 for value in response["data"]["Suitabilities"].values())
        )

    def test_maximize_endpoint_supports_base_workers(self):
        manager = FakeManager(self.pal)
        client = app.test_client()
        with app.app_context():
            token = create_access_token(identity="test")

        with (
            patch("palworld_pal_editor.api.pal.SaveManager", return_value=manager),
            patch(
                "palworld_pal_editor.core.save_manager.SaveManager",
                return_value=manager,
            ),
        ):
            response = client.post(
                "/api/pal/maximize",
                json={"PlayerUId": "PAL_BASE_WORKER_BTN", "PalGuid": str(PAL_ID)},
                headers={"Authorization": f"Bearer {token}"},
            ).get_json()

        self.assertEqual(0, response["status"])
        self.assertEqual(80, self.pal.Level)

    def test_maximize_does_not_add_pal_only_awakening_to_humans(self):
        human = make_pal("SalesPerson_Wander")
        self.assertTrue(human.IsHuman)

        human.maximize_progression()

        self.assertFalse(human.IsAwakening)


if __name__ == "__main__":
    unittest.main()
