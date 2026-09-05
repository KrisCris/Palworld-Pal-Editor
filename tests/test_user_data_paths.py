"""Where the program writes its own files, and the one-time move that got them there.

Writing beside the executable fails or is silently redirected on a normal install,
so settings, templates and logs now live under the platform's per-user directories.
The move runs once, unattended, against the only copy a user has of their saved
templates -- so what is checked here is that it never destroys the old file and
never runs twice.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from palworld_pal_editor import config as config_module
from palworld_pal_editor.config import (
    APP_NAME,
    migrate_legacy_user_data,
    user_config_dir,
    user_data_dir,
)


class UserDirectoryTests(unittest.TestCase):
    """One directory per platform, and the two XDG variables actually honoured."""

    def resolve(self, system: str, environment: dict) -> tuple[Path, Path]:
        with patch("platform.system", return_value=system), patch.dict(
            os.environ, environment, clear=True
        ):
            return user_config_dir(), user_data_dir()

    def test_windows_keeps_config_and_data_together_under_local_appdata(self):
        config, data = self.resolve("Windows", {"LOCALAPPDATA": r"C:\Users\p\AppData\Local"})
        self.assertEqual(Path(r"C:\Users\p\AppData\Local") / APP_NAME, config)
        self.assertEqual(config, data)

    def test_macos_keeps_config_and_data_together_under_application_support(self):
        with patch("pathlib.Path.home", return_value=Path("/Users/p")):
            config, data = self.resolve("Darwin", {})
        self.assertEqual(Path("/Users/p/Library/Application Support") / APP_NAME, config)
        self.assertEqual(config, data)

    def test_linux_separates_them_the_way_freedesktop_does(self):
        with patch("pathlib.Path.home", return_value=Path("/home/p")):
            config, data = self.resolve("Linux", {})
        self.assertEqual(Path("/home/p/.config") / APP_NAME, config)
        self.assertEqual(Path("/home/p/.local/share") / APP_NAME, data)

    def test_the_xdg_variables_win_where_they_apply(self):
        config, data = self.resolve(
            "Linux", {"XDG_CONFIG_HOME": "/x/cfg", "XDG_DATA_HOME": "/x/dat"}
        )
        self.assertEqual(Path("/x/cfg") / APP_NAME, config)
        self.assertEqual(Path("/x/dat") / APP_NAME, data)


class LegacyMigrationTests(unittest.TestCase):
    """The move out of the program directory, which runs on real user data."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        root = Path(self.directory.name)
        self.legacy = root / "program" / "config.json"
        self.config = root / "config" / "config.json"
        self.templates = root / "data" / "templates.json"
        self.legacy.parent.mkdir(parents=True)
        patch.object(config_module, "LEGACY_CONFIG_PATH", self.legacy).start()
        patch.object(config_module, "CONFIG_PATH", self.config).start()
        patch.object(config_module, "TEMPLATES_PATH", self.templates).start()
        self.addCleanup(patch.stopall)
        self.addCleanup(self.directory.cleanup)

    def write_legacy(self, **extra) -> dict:
        data = {"i18n": "zh-CN", "port": 12345, **extra}
        self.legacy.write_text(json.dumps(data), encoding="utf-8")
        return data

    def test_settings_move_and_templates_are_split_into_their_own_file(self):
        pal = [{"Id": "a", "Name": "Worker", "PalData": {"deep": "payload"}}]
        skill = [{"Id": "b", "Name": "Rush", "Skills": ["Legend"]}]
        self.write_legacy(palTemplates=pal, skillTemplates=skill)

        migrate_legacy_user_data()

        moved = json.loads(self.config.read_text(encoding="utf-8"))
        self.assertEqual("zh-CN", moved["i18n"])
        self.assertEqual(12345, moved["port"])
        # The whole point of the split: a settings change must stop rewriting every
        # saved Pal, so the templates cannot still be in here.
        self.assertNotIn("palTemplates", moved)
        self.assertNotIn("skillTemplates", moved)
        self.assertEqual(
            {"pal": pal, "skill": skill},
            json.loads(self.templates.read_text(encoding="utf-8")),
        )

    def test_the_old_file_is_left_exactly_where_it_was(self):
        original = self.write_legacy(palTemplates=[{"Id": "a"}])

        migrate_legacy_user_data()

        # A user who downgrades still has their templates, and a move that half
        # worked has destroyed nothing.
        self.assertTrue(self.legacy.exists())
        self.assertEqual(original, json.loads(self.legacy.read_text(encoding="utf-8")))

    def test_it_does_not_run_again_once_the_new_config_exists(self):
        self.write_legacy(palTemplates=[{"Id": "a"}])
        self.config.parent.mkdir(parents=True)
        self.config.write_text('{"i18n": "en"}', encoding="utf-8")

        migrate_legacy_user_data()

        # Re-running would undo whatever the user changed since the first launch.
        self.assertEqual({"i18n": "en"}, json.loads(self.config.read_text(encoding="utf-8")))
        self.assertFalse(self.templates.exists())

    def test_a_fresh_install_has_nothing_to_move(self):
        migrate_legacy_user_data()

        self.assertFalse(self.config.exists())
        self.assertFalse(self.templates.exists())

    def test_no_templates_means_no_template_file(self):
        self.write_legacy()

        migrate_legacy_user_data()

        self.assertTrue(self.config.exists())
        self.assertFalse(self.templates.exists())


if __name__ == "__main__":
    unittest.main()
