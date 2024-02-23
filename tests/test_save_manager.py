import unittest
import copy
from pathlib import Path

from palworld_pal_editor.save_manager import SaveManager

class TestSaveManager(unittest.TestCase):
    def setUp(self):
        self.input_path = "./gamesave/Level.sav"
        self.output_path = "./test_outputs/Level.sav"

    def test_read_and_save(self):
        sm = SaveManager()
        sm.open(self.input_path)
        raw_gvas_1 = copy.deepcopy(sm._raw_gvas)
        sm.save(self.output_path, _create_dir=True)

        sm.open(self.output_path)
        self.assertEqual(raw_gvas_1, sm._raw_gvas)

    def tearDown(self) -> None:
        Path(self.output_path).unlink()
        return super().tearDown()
    

if __name__ == '__main__':
    unittest.main()