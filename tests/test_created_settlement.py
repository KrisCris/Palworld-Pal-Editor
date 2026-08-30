"""Save-time settlement of Pals created in this session.

What a created Pal owes its owner -- a capture count, a paldeck flag, a skill unlock
-- is folded in at save time and nowhere else, so these are the rules about when
that happens and to whom. What happens to it when the save itself fails belongs with
the rest of the failure path, in `test_save_transaction.py`.
"""

from pathlib import Path
import tempfile
import unittest

from palworld_pal_editor.core.save_manager import SaveManager
from palworld_pal_editor.utils import DataProvider


SAVE = (
    Path(__file__).parents[1]
    / "tests/saves/1.0/8C439FF04713B5F986F9CAB485575089"
)
PLAYER_UID = "00000000-0000-0000-0000-000000000001"


class CreatedSettlementTests(unittest.TestCase):
    def setUp(self):
        self.previous_manager = SaveManager._instance
        SaveManager._instance = None
        self.manager = SaveManager()
        self.assertIsNotNone(self.manager.open(str(SAVE)))
        self.player = self.manager.get_player(PLAYER_UID)

    def tearDown(self):
        SaveManager._instance = self.previous_manager

    def capture_count(self, paldeck_key):
        # Read the MapProperty the way `inc_pal_capture_count` writes it: a list of
        # {key, value} entries, not a dict. (`PlayerEntity.get_pal_capture_count`
        # subscripts that list with the name and swallows the TypeError, so it
        # answers 0 for everything -- pre-existing, and it has no other caller.)
        for entry in self.player.PalCaptureCount or []:
            if entry["key"].lower() == paldeck_key.lower():
                return entry["value"]
        return 0

    def paldeck_unlocked(self, paldeck_key):
        return any(
            entry["key"].lower() == paldeck_key.lower() and entry["value"]
            for entry in self.player.PaldeckUnlockFlag or []
        )

    def test_a_successful_save_settles_each_created_pal_exactly_once(self):
        record = self.manager.add_pal(PLAYER_UID)
        self.assertIsNotNone(record)
        paldeck_key = DataProvider.get_pal_paldeck_record_id(record.pal.CharacterID)
        before = self.capture_count(paldeck_key)

        with tempfile.TemporaryDirectory(prefix="pal-editor-settled-save-") as directory:
            self.assertTrue(self.manager.save(directory))
            self.assertEqual(before + 1, self.capture_count(paldeck_key))

            # Nothing is created between the two saves, so the second one must not
            # settle the same Pal again.
            self.assertTrue(self.manager.save(directory))

        self.assertEqual(before + 1, self.capture_count(paldeck_key))
        self.assertTrue(self.paldeck_unlocked(paldeck_key))
        self.assertEqual([], self.manager.pal_repository.created_records())

    def test_a_deleted_pal_stops_being_settled(self):
        record = self.manager.add_pal(PLAYER_UID)
        self.assertIsNotNone(record)
        paldeck_key = DataProvider.get_pal_paldeck_record_id(record.pal.CharacterID)
        before = self.capture_count(paldeck_key)

        self.assertTrue(self.manager.delete_pal(record.record_key))
        self.assertFalse(self.manager.pal_repository.is_created(record))

        with tempfile.TemporaryDirectory(prefix="pal-editor-deleted-save-") as directory:
            self.assertTrue(self.manager.save(directory))

        self.assertEqual(before, self.capture_count(paldeck_key))


if __name__ == "__main__":
    unittest.main()
