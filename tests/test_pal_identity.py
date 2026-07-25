import unittest

from flask_jwt_extended import create_access_token

from palworld_pal_editor.core.pal_entity import PalEntity
from palworld_pal_editor.core.pal_objects import PalObjects
from palworld_pal_editor.utils import data_provider
from palworld_pal_editor.webui import app


class PalIdentityTests(unittest.TestCase):
    @staticmethod
    def make_pal(character_id: str) -> PalEntity:
        pal_obj = PalObjects.PalSaveParameter(
            PalObjects.EMPTY_UUID,
            PalObjects.EMPTY_UUID,
            PalObjects.EMPTY_UUID,
            0,
            PalObjects.EMPTY_UUID,
        )
        parameter = pal_obj["value"]["RawData"]["value"]["object"][
            "SaveParameter"
        ]["value"]
        PalObjects.set_BaseType(parameter["CharacterID"], character_id)
        return PalEntity(pal_obj)

    def test_special_suffixes_resolve_without_replacing_internal_name(self):
        for character_id, raw_key, data_key, icon_key in (
            ("BOSS_KingWhale_otomo", "KingWhale", "KingWhale", "KingWhale"),
            ("BOSS_LilyQueen_BossRush", "LilyQueen", "LilyQueen", "LilyQueen"),
            (
                "PREDATOR_WhiteShieldDragon_Quest",
                "WhiteShieldDragon",
                "PREDATOR_WhiteShieldDragon_Quest",
                "WhiteShieldDragon",
            ),
        ):
            with self.subTest(character_id=character_id):
                pal = self.make_pal(character_id)
                self.assertEqual(character_id, pal.CharacterID)
                self.assertEqual(raw_key, pal.RawSpecieKey)
                self.assertEqual(data_key, pal.DataAccessKey)
                self.assertEqual(icon_key, pal.IconAccessKey)

    def test_generated_data_resolves_save_id_casing(self):
        resolve = data_provider.DataProvider.resolve_pal_key
        for source, expected in {
            "Sheepball": "SheepBall",
            "LazyCatFish": "LazyCatfish",
            "WereWolf_Ice": "Werewolf_Ice",
            "Thunderdog_Ice": "ThunderDog_Ice",
        }.items():
            with self.subTest(source=source):
                self.assertEqual(expected, resolve(source))
        self.assertEqual("UnknownPal", resolve("UnknownPal"))
        self.assertIsNone(resolve(None))

    def test_technology_api_supplies_canonical_icon_key(self):
        app.config["JWT_SECRET_KEY"] = "test-secret-key-with-at-least-32-bytes"
        with app.app_context():
            token = create_access_token(identity="test", expires_delta=False)
        with app.test_client() as client:
            response = client.get(
                "/api/save/tech_data",
                headers={"Authorization": f"Bearer {token}"},
            )

        items = [
            item
            for level in response.get_json()["data"]["techLvDict"].values()
            for item in level
        ]
        item = next(
            item
            for item in items
            if item["InternalName"] == "SkillUnlock_Thunderdog_Ice"
        )
        self.assertEqual("ThunderDog_Ice", item["IconAccessKey"])


if __name__ == "__main__":
    unittest.main()
