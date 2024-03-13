import unittest
from pathlib import Path

from palworld_pal_editor.utils import DataProvider
from palworld_pal_editor.core import SaveManager
from palworld_pal_editor.utils import LOGGER

class Tests(unittest.TestCase):
    def setUp(self):
        self.input_path = r"/Volumes/home/ContainerFiles/GameServers/Palworld-Proton/server/PalServer/Pal/Saved/SaveGames/0/AF518B19A47340B8A55BC58137981393"
        self.output_path = "./test_outputs"       

    def _test_pal_num(self):
        sm = SaveManager()
        sm.open(self.input_path) 
        players = sm.get_players()
        player_num = len(players)
        pal_num = sum(len(player.get_pals()) for player in players)
        worker_num = len(sm.get_working_pals())
        dangling = len(sm._dangling_pals.values())
        self.assertEqual(len(sm._entities_list), player_num + pal_num + worker_num + dangling)

    def test_hp_scaling_calc(self):
        sm = SaveManager()
        sm.open(self.input_path) 
        players = sm.get_players()
        LOGGER.newline()
        for player in players:
            for pal in player.get_pals():
                computed_scaling = pal._derived_hp_scaling
                scaling = DataProvider.get_pal_scaling(pal.DataAccessKey, "HP", pal.IsBOSS)
                if scaling is None:
                    LOGGER.info(f" - {pal}: Computed Scaling = {computed_scaling}")
                    continue
                if scaling != computed_scaling:
                    LOGGER.info(f" - {pal}   :   {computed_scaling} : {scaling}")

        for pal in sm.get_working_pals():
            computed_scaling = pal._derived_hp_scaling
            scaling = DataProvider.get_pal_scaling(pal.DataAccessKey, "HP", pal.IsBOSS)
            if scaling is None:
                LOGGER.info(f" - {pal}: Computed Scaling = {computed_scaling}")
                continue
            if scaling != computed_scaling:
                LOGGER.info(f" - {pal}   :   {computed_scaling} : {scaling}")


    def tearDown(self) -> None:
        Path(self.output_path).unlink(missing_ok=True)
        return super().tearDown()
    

if __name__ == '__main__':
    unittest.main()