"""The one-time upgrade of templates saved by 1.0.x, and the config write itself.

What the template routes do lives in `test_rest_templates.py`. What is here runs
against a user's own config file, once, on the launch after they upgrade -- so it
checks what reaches disk rather than what a function returned.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from palworld_pal_editor.config import Config
from palworld_pal_editor.core.pal_objects import PalObjects, dumps, toUUID
from palworld_pal_editor.core.templates import (
    migrate_pal_templates,
    template_source,
)

PLAYER_ID = toUUID("11111111-1111-1111-1111-111111111111")
PAL_ID = toUUID("22222222-2222-2222-2222-222222222222")


class PalTemplateMigrationTests(unittest.TestCase):
    """The 1.0.x upgrade, which runs once against real users saved templates.

    These are the only tests standing between a user template file and being
    rewritten wrong, so they check what actually reaches disk rather than what the
    function returned.
    """

    def setUp(self):
        self.previous_templates = getattr(Config, "palTemplates", None)
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name, "config.json")
        # Migration writes the config itself, so the only way to test what it wrote
        # is to point the write somewhere this test owns.
        self.original_save = Config.__dict__["save_to_file"]
        Config.save_to_file = lambda: self.original_save.__func__(
            Config, str(self.path)
        )
        self.addCleanup(self.directory.cleanup)
        self.addCleanup(self.restore)

    def restore(self):
        Config.save_to_file = self.original_save
        if self.previous_templates is None:
            del Config.palTemplates
        else:
            Config.palTemplates = self.previous_templates

    def old_template(self, template_id: str, name: str, nickname: str) -> dict:
        pal_obj = PalObjects.PalSaveParameter(
            PAL_ID, PLAYER_ID, PalObjects.EMPTY_UUID, 0, PalObjects.EMPTY_UUID
        )
        parameter = pal_obj["value"]["RawData"]["value"]["object"]["SaveParameter"]
        PalObjects.set_BaseType(parameter["value"]["NickName"], nickname)
        return {"Id": template_id, "Name": name, "PalData": dumps(pal_obj)}

    def test_an_old_string_template_becomes_native_and_survives_a_reload(self):
        Config.palTemplates = [self.old_template("a", "Worker", "Old Timer")]

        migrate_pal_templates()

        self.assertIsInstance(Config.palTemplates[0]["PalData"], dict)
        Config.palTemplates = []
        Config.load_from_file(str(self.path))
        self.assertEqual("Worker", Config.palTemplates[0]["Name"])
        source = template_source(Config.palTemplates[0])
        self.assertEqual("world", source.kind)
        self.assertEqual("Old Timer", source.entity().NickName)

    def test_a_template_that_cannot_be_read_is_kept_exactly_as_it_was(self):
        broken = {"Id": "b", "Name": "Broken", "PalData": "{not json"}
        Config.palTemplates = [broken, self.old_template("c", "Good", "Keeper")]

        migrate_pal_templates()

        # Deleting or blanking it would throw away the only copy the user has; the
        # entry stays put and its readable neighbour is upgraded around it.
        self.assertEqual("{not json", Config.palTemplates[0]["PalData"])
        self.assertIsInstance(Config.palTemplates[1]["PalData"], dict)
        Config.palTemplates = []
        Config.load_from_file(str(self.path))
        self.assertEqual("{not json", Config.palTemplates[0]["PalData"])

    def test_nothing_to_upgrade_writes_nothing(self):
        native = self.old_template("d", "Already", "Native")
        native["PalData"] = json.loads(native["PalData"])
        Config.palTemplates = [native, {"Id": "e", "Name": "Broken", "PalData": 7}]

        migrate_pal_templates()

        self.assertFalse(self.path.exists())

    def test_a_failed_write_leaves_the_old_templates_in_memory(self):
        old = self.old_template("f", "Worker", "Old Timer")
        Config.palTemplates = [old]
        Config.save_to_file = lambda: (_ for _ in ()).throw(OSError("disk full"))

        with self.assertRaises(OSError):
            migrate_pal_templates()

        self.assertEqual([old], Config.palTemplates)


class ConfigPersistenceTests(unittest.TestCase):
    def test_config_write_replaces_the_previous_file_only_after_serializing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "config.json")
            path.write_text('{"keep": true}', encoding="utf-8")
            with patch(
                "palworld_pal_editor.config.json.dump",
                side_effect=OSError("serialization failed"),
            ):
                with self.assertRaises(OSError):
                    Config.save_to_file(str(path))
            self.assertEqual({"keep": True}, json.loads(path.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
