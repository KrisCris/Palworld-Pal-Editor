from .save_manager import SaveManager
from .utils import Logger
from .config import Config

LOGGER = Logger()

if __name__ == "__main__":
    Config.i18n = "zh-CN"
    LOGGER.info("> Please provide the path to Level.sav")
    input_path = input()
    sm = SaveManager()
    sm.open(input_path)

    # player_list = sm.list_players()
    # random_player = sm.get_player(player_list[0].PlayerUId)
    # pal_list = random_player.list_pals()
    # target_pal = None
    # for pal in pal_list:
    #     if "BOSS_" in pal.CharacterID:
    #         target_pal = pal
    #         break
    # random_pal = random_player.get_pal(pal_list[0].InstanceId)
    # print(pal._pal_obj)
    # target_pal.pprint_pal_stats()
    # target_pal.IsBOSS = False