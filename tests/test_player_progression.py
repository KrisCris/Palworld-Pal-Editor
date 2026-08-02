import copy
from pathlib import Path
import unittest

from palworld_pal_editor.api.player import player_to_dict
from palworld_pal_editor.core.pal_objects import PalObjects
from palworld_pal_editor.core.player_entity import PlayerEntity
from palworld_pal_editor.core.save_manager import SaveManager


ROOT = Path(__file__).parents[1]
SAVE = ROOT / "tests/saves/1.0/8C439FF04713B5F986F9CAB485575089"


class PlayerProgressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manager = SaveManager()
        if cls.manager.open(str(SAVE)) is None:
            raise AssertionError("1.0 fixture failed to load")
        cls.player = cls.manager.get_player(
            "00000000-0000-0000-0000-000000000001"
        )

    def test_level_80_assignment_preserves_existing_exp(self):
        self.assertEqual(80, PlayerEntity.MAX_LEVEL)
        original = copy.deepcopy(self.player._player_param)
        original_exp = self.player.Exp
        try:
            self.player.Level = self.player.Level
            self.assertEqual(original_exp, self.player.Exp)
        finally:
            self.player._player_param = original

    def test_all_status_upgrades_are_editable_and_clamped(self):
        original = copy.deepcopy(self.player._player_param)
        try:
            self.assertEqual(18, len(self.player.StatusPoints))
            self.assertEqual(87, self.player.StatusPoints["移動速度アップ"])
            self.player.set_StatusPoint("移動速度アップ", 999)
            self.player.set_StatusPoint("最大HP", 999)
            self.assertEqual(92, self.player.StatusPoints["移動速度アップ"])
            self.assertEqual(38, self.player.StatusPoints["最大HP"])
            self.assertEqual(
                self.player.StatusPoints,
                player_to_dict(self.player)["StatusPoints"],
            )
        finally:
            self.player._player_param = original

    def test_shared_stat_total_changes_only_item_points(self):
        original = copy.deepcopy(self.player._player_param)
        try:
            normal_hp = self.player.StatusPoints["最大HP"]
            unused = self.player.UnusedStatusPoint
            self.assertEqual(50, self.player.StatusPointTotals["最大HP"])
            self.assertEqual(normal_hp, self.player.StatusPointMinimums["最大HP"])

            self.player.set_TotalStatusPoint("最大HP", normal_hp + 4)
            self.assertEqual(normal_hp, self.player.StatusPoints["最大HP"])
            self.assertEqual(4, self.player.ExStatusPoints["最大HP"])
            self.assertEqual(normal_hp + 4, self.player.StatusPointTotals["最大HP"])
            self.assertEqual(unused, self.player.UnusedStatusPoint)

            self.player.set_TotalStatusPoint("最大HP", -1)
            self.assertEqual(normal_hp, self.player.StatusPointTotals["最大HP"])
            self.player.set_TotalStatusPoint("最大HP", 999)
            self.assertEqual(50, self.player.StatusPointTotals["最大HP"])
            with self.assertRaisesRegex(ValueError, "does not support item points"):
                self.player.set_TotalStatusPoint("捕獲率", 1)
        finally:
            self.player._player_param = original

    def test_player_payload_exposes_total_and_game_derived_metadata(self):
        payload = player_to_dict(self.player)
        self.assertEqual(50, payload["StatusPointTotals"]["最大HP"])
        self.assertEqual(38, payload["StatusPointMinimums"]["最大HP"])
        self.assertEqual(50, payload["StatusPointTotalMaximums"]["最大HP"])
        self.assertEqual("stat-health", payload["StatusPointMetadata"]["最大HP"]["icon"])
        self.assertEqual(
            45,
            payload["StatusPointMetadata"]["移動速度アップ"]["values"][90],
        )
        self.assertEqual(
            50,
            payload["StatusPointMetadata"]["移動速度アップ"]["values"][92],
        )

    def test_status_limits_match_1_0_game_data(self):
        expected = {
            "最大HP": 50,
            "最大SP": 50,
            "攻撃力": 50,
            "所持重量": 50,
            "捕獲率": 15,
            "作業速度": 50,
            "空腹率低減": 20,
            "泳ぎ速度": 20,
            "食料腐敗低減": 20,
            "ジャンプ力": 20,
            "崖登り速度": 20,
            "状態異常耐性": 20,
            "スタミナ消費軽減": 20,
            "パルスフィアホーミング": 4,
            "移動速度アップ": 92,
            "滑空速度": 20,
            "経験値ボーナス": 4,
            "虹パッシブ率": 4,
        }
        self.assertEqual(expected, PalObjects.StatusPointMaximums)
        self.assertEqual(38, self.player.StatusPointMaximums["最大HP"])

    def test_status_labels_use_normal_i18n_files(self):
        component = (
            ROOT
            / "frontend/palworld-pal-editor-webui/src/components/PlayerEditor.vue"
        ).read_text("utf-8")
        self.assertIn('getTranslatedText(`StatusPoint_${name}`)', component)
        for locale in ("en", "fr", "ja", "zh-CN"):
            translations = (
                ROOT / f"frontend/palworld-pal-editor-webui/src/i18n/{locale}.js"
            ).read_text("utf-8")
            for name in PalObjects.StatusNames:
                with self.subTest(locale=locale, status=name):
                    self.assertIn(f'"StatusPoint_{name}"', translations)


if __name__ == "__main__":
    unittest.main()
