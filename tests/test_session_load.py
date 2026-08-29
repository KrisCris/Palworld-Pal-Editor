"""What is left behind when opening a save fails.

The risk this guards is not the failure itself -- a save can be missing, truncated
or simply not a save -- but what the session holds afterwards. A load that stops
half way through has already built players, containers and Pal records out of the
new file while the old file's are still there; anything the UI shows from that
point is a mix of two saves, and saving it writes that mix to disk.
"""

from collections.abc import Sized
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from palworld_pal_editor.core.save_manager import SaveManager


SAVE = Path(__file__).parents[1] / "tests/saves/1.0/8C439FF04713B5F986F9CAB485575089"


def session_state(manager: SaveManager) -> dict:
    """Every field the session owns, described so two empty sessions compare equal.

    Read out of `vars()` rather than a list written here, so a field added to the
    session later is covered without anyone remembering this test exists. Sized
    values collapse to their length because two empty repositories are different
    objects; everything else is `None` in an empty session and compares directly.
    """
    return {
        name: len(value) if isinstance(value, Sized) else value
        for name, value in vars(manager).items()
        if name not in ("session_lock", "initialized")
    }


class SessionLoadFailureTests(unittest.TestCase):
    def setUp(self):
        self.previous_manager = SaveManager._instance
        SaveManager._instance = None
        self.manager = SaveManager()
        # An untouched session, which is what a failed load must leave behind. Taken
        # from a manager that has never opened anything, so a field `reset()` forgets
        # is a mismatch here rather than a value this test agrees to ignore.
        self.empty = session_state(self.manager)

    def tearDown(self):
        SaveManager._instance = self.previous_manager

    def test_a_load_failure_leaves_no_trace_of_the_previous_save(self):
        """The dangerous case: the second load fails after it has built most of a session."""
        self.assertIsNotNone(self.manager.open(str(SAVE)))
        self.assertNotEqual(self.empty, session_state(self.manager))

        with patch.object(
            SaveManager,
            "_load_external_storages",
            side_effect=RuntimeError("DPS storage is unreadable"),
        ):
            self.assertIsNone(self.manager.open(str(SAVE)))

        self.assertEqual(self.empty, session_state(self.manager))

    def test_every_load_failure_ends_with_an_empty_session(self):
        """Both ways `open()` can fail: a step that reports failure, and one that raises."""
        with tempfile.TemporaryDirectory(prefix="pal-editor-not-a-save-") as directory:
            with self.subTest("the directory holds no Level.sav"):
                self.assertIsNone(self.manager.open(directory))
                self.assertEqual(self.empty, session_state(self.manager))

        with self.subTest("a parser fails after the GVAS file is read"):
            with patch(
                "palworld_pal_editor.core.save_manager.ContainerData",
                side_effect=ValueError("container array is not a container array"),
            ):
                self.assertIsNone(self.manager.open(str(SAVE)))
            self.assertEqual(self.empty, session_state(self.manager))


if __name__ == "__main__":
    unittest.main()
