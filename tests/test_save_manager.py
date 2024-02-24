import unittest
import copy
from pathlib import Path

from palworld_pal_editor.save_manager import SaveManager

class TestSaveManager(unittest.TestCase):
    def setUp(self):
        self.input_path = "./gamesave/Level.sav"
        self.output_path = "./test_outputs/Level.sav"

    def test_save_loading(self):
        sm = SaveManager()
        sm.open(self.input_path)

    def tearDown(self) -> None:
        Path(self.output_path).unlink(missing_ok=True)
        return super().tearDown()
    

if __name__ == '__main__':
    unittest.main()