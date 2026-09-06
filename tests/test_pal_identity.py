import json
import unittest
from unittest.mock import patch
from uuid import UUID

from flask_jwt_extended import create_access_token

from palworld_pal_editor.api.pal import _pal_brief, _pal_data
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
        parameter.pop("OwnerPlayerUId", None)
        return PalEntity(pal_obj)

    def test_special_suffixes_resolve_without_replacing_internal_name(self):
        for character_id, raw_key, data_key, icon_key in (
            (
                "BOSS_KingWhale_otomo",
                "KingWhale",
                "BOSS_KingWhale_otomo",
                "KingWhale",
            ),
            (
                "BOSS_LilyQueen_BossRush",
                "LilyQueen",
                "BOSS_LilyQueen_BossRush",
                "LilyQueen",
            ),
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

    def test_unknown_special_looking_id_remains_literal(self):
        pal = self.make_pal("BOSS_UnknownPal_otomo")
        self.assertEqual("BOSS_UnknownPal_otomo", pal.CharacterID)
        self.assertEqual("BOSS_UnknownPal_otomo", pal.RawSpecieKey)
        self.assertEqual("BOSS_UnknownPal_otomo", pal.DataAccessKey)
        self.assertEqual("unknown", pal.IconAccessKey)
        self.assertFalse(pal.IsBOSS)

    def test_external_no_skin_sentinel_uses_the_species_icon(self):
        pal = self.make_pal("BlackMetalDragon")
        pal._pal_param["SkinName"] = PalObjects.NameProperty("None")

        self.assertIsNone(pal.SkinName)
        self.assertEqual("BlackMetalDragon", pal.IconAccessKey)

    def test_metadata_predicates_do_not_infer_from_prefixes(self):
        boss_rush = self.make_pal("BOSS_ElecPanda_BossRush")
        self.assertFalse(boss_rush._IsBOSS)
        self.assertTrue(boss_rush.IsTower)

        predator = self.make_pal("PREDATOR_WhiteShieldDragon_Quest")
        self.assertTrue(predator.IsPREDATOR)
        self.assertEqual(
            "quest",
            data_provider.DataProvider.get_pal_variant_kind(predator.CharacterID),
        )

        self.assertTrue(self.make_pal("RAID_NightLady").IsRAID)
        self.assertTrue(self.make_pal("SUMMON_DarkAlien").IsSUMMON)
        self.assertTrue(self.make_pal("WingGolem_Oilrig").IsOilrig)
        self.assertTrue(self.make_pal("GYM_ElecPanda_Otomo").IsOtomoTower)

    def test_legacy_setters_only_select_unambiguous_family_variants(self):
        pal = self.make_pal("GrassPanda_Electric")
        pal.IsTower = True
        self.assertEqual("GrassPanda_Electric_Tower", pal.CharacterID)
        pal.IsTower = False
        self.assertEqual("GrassPanda_Electric", pal.CharacterID)

        ambiguous = self.make_pal("BlackGriffon")
        ambiguous.IsTower = True
        self.assertEqual("BlackGriffon", ambiguous.CharacterID)

    def test_rare_and_boss_toggles_preserve_alpha_behavior(self):
        pal = self.make_pal("Anubis")
        pal.IsRarePal = True
        self.assertEqual("Boss_Anubis", pal.CharacterID)
        self.assertTrue(pal.IsRarePal)
        self.assertFalse(pal.IsBOSS)
        self.assertTrue(pal._IsBOSS)

        pal.IsRarePal = False
        self.assertEqual("Anubis", pal.CharacterID)
        self.assertFalse(pal.IsRarePal)
        pal.IsBOSS = True
        self.assertEqual("Boss_Anubis", pal.CharacterID)
        self.assertTrue(pal.IsBOSS)

    def test_ordinary_alpha_list_name_uses_base_species_localization(self):
        pal = self.make_pal("BOSS_GhostRabbit_Grass")
        pal.NickName = ""

        self.assertEqual(
            data_provider.DataProvider.get_pal_i18n("GhostRabbit_Grass"),
            pal.DisplayName,
        )

        scenario = self.make_pal("BOSS_KingWhale_otomo")
        scenario.NickName = ""
        self.assertEqual(
            data_provider.DataProvider.get_pal_i18n("BOSS_KingWhale_otomo"),
            scenario.DisplayName,
        )

    def test_regular_alpha_localization_uses_base_species_name_everywhere(self):
        base_name = data_provider.DataProvider.get_pal_i18n("PinkCat")
        self.assertEqual(
            base_name,
            data_provider.DataProvider.get_pal_i18n("BOSS_PinkCat"),
        )

        pal = self.make_pal("BOSS_PinkCat")
        pal.NickName = ""
        self.assertEqual(base_name, pal.I18nName)
        self.assertEqual(base_name, pal.DisplayName)
        self.assertEqual(base_name, _pal_data(pal)["I18nName"])

    def test_owner_name_uuid_fallback_is_json_serializable(self):
        owner_id = UUID("23d87046-27f9-4399-9269-c7e9b4bac864")
        pal_obj = PalObjects.PalSaveParameter(
            PalObjects.EMPTY_UUID,
            str(owner_id),
            PalObjects.EMPTY_UUID,
            0,
            PalObjects.EMPTY_UUID,
        )
        pal = PalEntity(pal_obj)

        class Player:
            NickName = None

        class Manager:
            def get_player(self, _player_id):
                return Player()

        with patch(
            "palworld_pal_editor.core.save_manager.SaveManager",
            return_value=Manager(),
        ):
            payload = _pal_data(pal)

        self.assertEqual(str(owner_id), payload["OwnerName"])
        json.dumps(payload)

    def test_api_marks_new_pals_until_the_save_is_written(self):
        pal = self.make_pal("SheepBall")
        pal.is_new_pal = True

        payload = _pal_data(pal)

        self.assertTrue(payload["IsNewPal"])

    def test_pal_list_includes_awakened_and_new_state_before_selection(self):
        pal = self.make_pal("SheepBall")
        pal.IsAwakening = True
        pal.IsImportedCharacter = True
        pal.is_new_pal = True

        class Manager:
            @staticmethod
            def get_working_pals():
                return [pal]

        app.config["JWT_SECRET_KEY"] = "test-secret-key-with-at-least-32-bytes"
        with app.app_context():
            token = create_access_token(identity="test", expires_delta=False)
        with (
            patch("palworld_pal_editor.api.player.SaveManager", return_value=Manager()),
            app.test_client() as client,
        ):
            response = client.post(
                "/api/player/player_pals",
                json={"PlayerUId": "PAL_BASE_WORKER_BTN"},
                headers={"Authorization": f"Bearer {token}"},
            )

        pal_summary = response.get_json()["data"][0]
        self.assertTrue(pal_summary["IsAwakening"])
        self.assertTrue(pal_summary["IsImportedCharacter"])
        self.assertFalse(pal_summary["IsHuman"])
        self.assertTrue(pal_summary["IsNewPal"])

    def test_pal_list_includes_verified_location_and_priority_fields(self):
        party_id = UUID("11111111-1111-1111-1111-111111111111")
        storage_id = UUID("22222222-2222-2222-2222-222222222222")
        pal = self.make_pal("SheepBall")
        pal.InstanceId = "33333333-3333-3333-3333-333333333333"
        pal.SlotId = (str(party_id), 4)
        pal._pal_param["FavoriteIndex"] = PalObjects.IntProperty(3)

        class Player:
            OtomoCharacterContainerId = party_id
            PalStorageContainerId = storage_id

            @staticmethod
            def get_sorted_pals():
                return [pal]

        pal.set_owner_player_entity(Player())

        class Manager:
            @staticmethod
            def get_player(_player_id):
                return Player()

        app.config["JWT_SECRET_KEY"] = "test-secret-key-with-at-least-32-bytes"
        with app.app_context():
            token = create_access_token(identity="test", expires_delta=False)
        with (
            patch("palworld_pal_editor.api.player.SaveManager", return_value=Manager()),
            app.test_client() as client,
        ):
            response = client.post(
                "/api/player/player_pals",
                json={"PlayerUId": "player"},
                headers={"Authorization": f"Bearer {token}"},
            )

        pal_summary = response.get_json()["data"][0]
        self.assertEqual(str(party_id), pal_summary["ContainerId"])
        self.assertEqual(4, pal_summary["SlotIndex"])
        self.assertEqual("party", pal_summary["ContainerKind"])
        self.assertEqual(3, pal_summary["FavoriteIndex"])

        pal._pal_param["FavoriteIndex"] = PalObjects.ByteProperty(2)
        self.assertEqual(2, pal.FavoriteIndex)

    def test_priority_setter_preserves_save_property_shape(self):
        pal = self.make_pal("SheepBall")

        pal.FavoriteIndex = 1
        self.assertEqual("ByteProperty", pal._pal_param["FavoriteIndex"]["type"])
        self.assertEqual(1, pal.FavoriteIndex)

        pal._pal_param["FavoriteIndex"] = PalObjects.IntProperty(2)
        pal.FavoriteIndex = 3
        self.assertEqual("IntProperty", pal._pal_param["FavoriteIndex"]["type"])
        self.assertEqual(3, pal.FavoriteIndex)

        pal._pal_param["FavoriteIndex"] = PalObjects.ByteProperty(3)
        pal.FavoriteIndex = 0
        self.assertEqual("ByteProperty", pal._pal_param["FavoriteIndex"]["type"])
        self.assertEqual(0, pal.FavoriteIndex)

    def test_priority_setter_rejects_invalid_values(self):
        pal = self.make_pal("SheepBall")
        for value in (-1, 4, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                pal.FavoriteIndex = value

    def test_pal_detail_includes_priority(self):
        pal = self.make_pal("SheepBall")
        pal._pal_param["FavoriteIndex"] = PalObjects.ByteProperty(2)
        self.assertEqual(2, _pal_data(pal)["FavoriteIndex"])

    def test_pal_conflict_brief_includes_portrait_status_flags(self):
        pal = self.make_pal("SheepBall")
        pal.IsBOSS = True
        pal.IsAwakening = True
        pal.IsImportedCharacter = True
        pal.FavoriteIndex = 2

        brief = _pal_brief(pal)

        self.assertTrue(brief["IsBOSS"])
        self.assertFalse(brief["IsRarePal"])
        self.assertTrue(brief["IsAwakening"])
        self.assertTrue(brief["IsImportedCharacter"])
        self.assertEqual(2, brief["FavoriteIndex"])

    def test_imported_character_flag_round_trips_and_reaches_api_payloads(self):
        pal = self.make_pal("SheepBall")

        self.assertFalse(pal.IsImportedCharacter)
        self.assertFalse(_pal_data(pal)["IsImportedCharacter"])

        pal.IsImportedCharacter = True
        self.assertTrue(pal.IsImportedCharacter)
        self.assertEqual(
            "BoolProperty", pal._pal_param["bImportedCharacter"]["type"]
        )
        self.assertTrue(_pal_data(pal)["IsImportedCharacter"])

        pal.IsImportedCharacter = False
        self.assertFalse(pal.IsImportedCharacter)
        self.assertNotIn("bImportedCharacter", pal._pal_param)

    def test_rare_toggle_uses_primary_alpha_not_other_boss_tagged_variants(self):
        for character_id in ("ElecPanda", "GYM_ElecPanda"):
            with self.subTest(character_id=character_id):
                pal = self.make_pal(character_id)
                pal.IsRarePal = True
                self.assertEqual("BOSS_ElecPanda", pal.CharacterID)
                self.assertTrue(pal.IsRarePal)
                self.assertTrue(pal._IsBOSS)

    def test_exact_tower_patch_clears_rare_without_changing_target(self):
        pal = self.make_pal("BOSS_ElecPanda")
        pal.IsRarePal = True
        self.assertTrue(pal.IsRarePal)

        pal.CharacterID = "GYM_ElecPanda"

        self.assertEqual("GYM_ElecPanda", pal.CharacterID)
        self.assertFalse(pal.IsRarePal)

    def test_rare_toggle_is_noop_without_unique_primary_boss_variant(self):
        pal = self.make_pal("RAID_YakushimaBoss002")
        pal.IsRarePal = True
        self.assertEqual("RAID_YakushimaBoss002", pal.CharacterID)
        self.assertIsNone(pal.IsRarePal)

    def test_skin_target_is_compared_by_family(self):
        pal = self.make_pal("Boss_Anubis")
        pal.SkinName = "Anubis_Skin001"
        self.assertEqual("Anubis_Skin001", pal.SkinName)

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
        pal = self.make_pal("boss_kingwhale_OTOMO")
        self.assertEqual("BOSS_KingWhale_otomo", pal.DataAccessKey)
        self.assertEqual("KingWhale", pal.RawSpecieKey)
        self.assertEqual("KingWhale", pal.IconAccessKey)
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
