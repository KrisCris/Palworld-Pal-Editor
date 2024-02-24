from .save_manager import SaveManager
from .utils import Logger

LOGGER = Logger()

if __name__ == "__main__":
    LOGGER.info("> Please provide the path to Level.sav")
    input_path = input()
    sm = SaveManager()
    sm.open(input_path)

    # player_list = sm.list_players()
    # random_player = sm.get_player(player_list[-1].PlayerUId)
    # pal_list = random_player.list_pals()
    # random_pal = random_player.get_pal(pal_list[-1].InstanceId)
    # random_pal.pprint_pal_stats()
