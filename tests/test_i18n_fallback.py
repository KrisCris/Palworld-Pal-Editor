import copy
import unittest

from palworld_pal_editor.config import Config
from palworld_pal_editor.utils import data_provider


class SkillI18nFallbackTests(unittest.TestCase):
    def test_incomplete_locale_fields_fall_back_to_english(self):
        cases = (
            (
                data_provider.PAL_ATTACKS,
                next(iter(data_provider.PAL_ATTACKS)),
                data_provider.DataProvider.get_attack_i18n,
            ),
            (
                data_provider.PAL_PASSIVES,
                next(iter(data_provider.PAL_PASSIVES)),
                data_provider.DataProvider.get_passive_i18n,
            ),
        )
        original_locale = Config.i18n
        try:
            Config.i18n = "ja"
            for rows, key, getter in cases:
                original = copy.deepcopy(rows[key]["I18n"])
                try:
                    rows[key]["I18n"] = {
                        "en": {"Name": "English name", "Description": "English text"},
                        "ja": {"Name": "", "Description": ""},
                    }
                    self.assertEqual(
                        ("English name", "English text"), getter(key)
                    )
                finally:
                    rows[key]["I18n"] = original
        finally:
            Config.i18n = original_locale

    def test_content_fallback_order_is_selected_english_japanese_then_id(self):
        key = next(iter(data_provider.TECH_DATA))
        original_locale = Config.i18n
        original = copy.deepcopy(data_provider.TECH_DATA[key]["I18n"])
        try:
            Config.i18n = "de"
            data_provider.TECH_DATA[key]["I18n"] = {
                "ja": {
                    "Name": "Japanese",
                    "Description": "Japanese",
                    "Type": "Japanese",
                }
            }
            self.assertEqual(
                {"Name": "Japanese", "Description": "Japanese", "Type": "Japanese"},
                data_provider.DataProvider.get_tech_i18n(key),
            )
            data_provider.TECH_DATA[key]["I18n"] = {}
            self.assertEqual(key, data_provider.DataProvider.get_tech_i18n(key))
        finally:
            data_provider.TECH_DATA[key]["I18n"] = original
            Config.i18n = original_locale


if __name__ == "__main__":
    unittest.main()
