import threading
import unittest
from unittest.mock import patch

from flask_jwt_extended import create_access_token

from palworld_pal_editor.core.pal_entity import PalEntity
from palworld_pal_editor.core.pal_objects import PalObjects
from fakes import pal_payload, record_location, world_pal, world_record
from palworld_pal_editor.utils import data_provider
from palworld_pal_editor.utils.data_provider import DataProvider
from palworld_pal_editor.webui import app
from palworld_pal_editor.core.pal_repository import PalRepository


def make_pal_obj(character_id: str) -> dict:
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
    return pal_obj


def make_pal(character_id: str) -> PalEntity:
    return world_pal(make_pal_obj(character_id))


class PalFamilyProviderTests(unittest.TestCase):
    def test_exact_metadata_resolves_case_insensitive_save_ids(self):
        self.assertEqual(
            "KingWhale",
            DataProvider.get_pal_family_id("boss_kingwhale_OTOMO"),
        )
        self.assertEqual(
            "GrassPanda_Electric",
            DataProvider.get_pal_family_id("GrassPanda_Electric_Tower"),
        )
        self.assertEqual(
            "tower", DataProvider.get_pal_variant_kind("GYM_BlackGriffon")
        )
        self.assertEqual(
            ("boss", "otomo"),
            DataProvider.get_pal_variant_tags("BOSS_KingWhale_otomo"),
        )
        self.assertEqual(
            "KingWhale", DataProvider.get_pal_icon_key("BOSS_KingWhale_otomo")
        )

    def test_unknown_ids_are_never_token_stripped(self):
        character_id = "BOSS_UnknownPal_otomo"
        self.assertEqual(character_id, DataProvider.get_pal_family_id(character_id))
        self.assertEqual("other", DataProvider.get_pal_variant_kind(character_id))
        self.assertEqual((), DataProvider.get_pal_variant_tags(character_id))
        self.assertEqual("unknown", DataProvider.get_pal_icon_key(character_id))
        self.assertIsNone(DataProvider.get_pal_paldeck_record_id(character_id))
        self.assertEqual(
            (character_id,), DataProvider.get_family_variants(character_id)
        )
        self.assertIsNone(DataProvider.get_pal_variant(character_id, "boss"))

    def test_family_index_is_base_first_and_does_not_merge_humans(self):
        king_whale_variants = DataProvider.get_family_variants(
            "BOSS_KingWhale_otomo"
        )
        self.assertEqual(
            ("KingWhale", "BOSS_KingWhale_otomo", "BOSS_KingWhale"),
            king_whale_variants,
        )
        self.assertEqual(
            king_whale_variants,
            data_provider.PAL_VARIANTS_BY_FAMILY["KingWhale"],
        )
        self.assertEqual(
            ("Hunter_Rifle",), DataProvider.get_family_variants("Hunter_Rifle")
        )

    def test_variant_lookup_requires_one_exact_kind_match(self):
        self.assertEqual(
            "GrassPanda_Electric_Tower",
            DataProvider.get_pal_variant("GrassPanda_Electric", "tower"),
        )
        self.assertIsNone(DataProvider.get_pal_variant("BlackGriffon", "tower"))
        self.assertIsNone(DataProvider.get_pal_variant("KingWhale", "alpha"))

    def test_paldeck_record_uses_explicit_record_then_known_family(self):
        self.assertEqual(
            "BOSS_StrawHatCat",
            DataProvider.get_pal_paldeck_record_id("BOSS_StrawHatCat"),
        )
        self.assertEqual(
            "KingWhale",
            DataProvider.get_pal_paldeck_record_id("BOSS_KingWhale_otomo"),
        )
        for character_id in ("BluePlatypus", "BOSS_BluePlatypus"):
            with self.subTest(character_id=character_id):
                self.assertEqual(
                    "BluePlatypus",
                    DataProvider.get_pal_paldeck_record_id(character_id),
                )
        for character_id in ("Werewolf_Ice", "BOSS_Werewolf_Ice"):
            with self.subTest(character_id=character_id):
                self.assertEqual(
                    "WereWolf_Ice",
                    DataProvider.get_pal_paldeck_record_id(character_id),
                )
        for character_id in ("SheepBall", "Sheepball", "BOSS_SheepBall"):
            with self.subTest(character_id=character_id):
                self.assertEqual(
                    "SheepBall",
                    DataProvider.get_pal_paldeck_record_id(character_id),
                )
        self.assertIsNone(DataProvider.get_pal_paldeck_record_id("Hunter_Rifle"))
        self.assertIsNone(DataProvider.get_pal_paldeck_record_id("UnknownPal"))

    def test_pal_catalog_includes_exact_boss_rows_and_metadata(self):
        app.config["JWT_SECRET_KEY"] = "test-secret-key-with-at-least-32-bytes"
        with app.app_context():
            token = create_access_token(identity="test", expires_delta=False)
        with app.test_client() as client:
            response = client.get(
                "/api/catalogs/pals",
                headers={"Authorization": f"Bearer {token}"},
            )

        rows = {row["InternalName"]: row for row in response.get_json()["pals"]}
        self.assertEqual(len(data_provider.PAL_DATA), len(rows))
        self.assertIn("Boss_Anubis", rows)
        row = rows["BOSS_KingWhale_otomo"]
        self.assertEqual("KingWhale", row["FamilyID"])
        self.assertEqual("boss", row["VariantKind"])
        self.assertEqual(["boss", "otomo"], row["VariantTags"])
        self.assertEqual("KingWhale", row["IconKey"])
        self.assertEqual("KingWhale", row["PaldeckRecordID"])
        self.assertTrue(row["RegularlyObtainable"])
        self.assertEqual(["capture-replace"], row["ObtainMethods"])
        self.assertEqual(rows["PinkCat"]["I18n"], rows["BOSS_PinkCat"]["I18n"])

    def test_selected_pal_payload_contains_exact_metadata(self):
        payload = pal_payload(world_record(make_pal_obj("BOSS_KingWhale_otomo")))
        self.assertEqual("BOSS_KingWhale_otomo", payload["CharacterID"])
        self.assertEqual("KingWhale", payload["FamilyID"])
        self.assertEqual("boss", payload["VariantKind"])
        self.assertEqual(["boss", "otomo"], payload["VariantTags"])
        self.assertEqual("KingWhale", payload["IconKey"])
        self.assertTrue(payload["RegularlyObtainable"])

    def test_character_patch_and_refresh_keep_exact_variant(self):
        record = world_record(make_pal_obj("SheepBall"))

        class Manager:
            pal_repository = PalRepository()
            session_lock = threading.RLock()

            def get_record(self, _record_key):
                return record

            def get_player(self, _player_uid):
                return None

            def normalize_external_record(self, _record):
                pass

            def resolve_record_location(self, record):
                return record_location(record)

        app.config["JWT_SECRET_KEY"] = "test-secret-key-with-at-least-32-bytes"
        with app.app_context():
            token = create_access_token(identity="test", expires_delta=False)
        headers = {"Authorization": f"Bearer {token}"}
        manager = Manager()
        with (
            patch("palworld_pal_editor.api.pals.SaveManager", return_value=manager),
            app.test_client() as client,
        ):
            patched = client.patch(
                f"/api/pals/{record.record_key}",
                headers=headers,
                json={"CharacterID": "BOSS_KingWhale_otomo"},
            )
            refreshed = client.get(
                f"/api/pals/{record.record_key}", headers=headers
            )

        self.assertEqual(200, patched.status_code)
        self.assertEqual(
            "BOSS_KingWhale_otomo",
            refreshed.get_json()["CharacterID"],
        )


if __name__ == "__main__":
    unittest.main()
