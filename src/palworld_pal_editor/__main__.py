import code
import sys
from palworld_pal_editor.save_manager import SaveManager
from palworld_pal_editor.utils import Logger
from palworld_pal_editor.config import Config

LOGGER = Logger()

def help():
    print("""
          - class SaveManager:
          > Singleton Class so you can call SaveManager() multiple times.
          -     `SaveManager()`: Get the SaveManager Instance
          -     `SaveManager().open(path: str)`: Open a new file
          -     `SaveManager().save(path: str)`: Save to a new file
          -     `SaveManager().list_players() -> list[PlayerEntity]`: Print and get the players list
          -     `SaveManager().get_player(uuid: str)`: Get a PlayerEntity via a PlayerUId str

          - class PlayerEntity: 
          > Note: First retrieve a player_entity via SaveManager().get_player(uuid: str)
          -     `player_entity.PlayerUId`: Getter
          -     `player_entity.list_pals() -> list[PalEntity]`: Print and get the player palbox 
          -     `player_entity.get_pal(guid: str) -> PalEntity`: Get a pal_entity via guid

          - class PalEntity:
          > Unless specified, most pal stats are made computed properties, 
          > i.e. `pal_entity.Exp` gives you the value, while `pal_entity.Exp` = 0 sets the value.
          - `pal_entity.PlayerUId`: Getter
          - `pal_entity.InstanceId`: Getter
          - `pal_entity.OwnerPlayerUId`: Getter
          - `pal_entity.OwnerName`: Getter
          - `pal_entity.OldOwnerPlayerUIds`: Getter
          - `pal_entity.CharacterID`: Getter, Setter
          - `pal_entity.DisplayName`: Getter
          - `pal_entity.IsBOSS`: Getter, Setter
          - `pal_entity.IsRarePal`: Getter, Setter
          - `pal_entity.NickName`: Getter, Setter
          - `pal_entity.Level`: Getter, Setter
          - `pal_entity.Exp`: Getter, Setter
          - `pal_entity.HP`: Getter, Setter
          - `pal_entity.pprint_pal_stats()`: print out stats
    """) 

if __name__ == "__main__":
    Config.i18n = "zh-CN"
    LOGGER.info("Palworld Pal Editor, made by _connlost with ❤.")
    LOGGER.info("> Please provide the path to Level.sav")
    input_path = input("> ")
    sm = SaveManager()
    sm.open(input_path)
    
    
    # if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    print("Entering interactive mode. Press Ctrl+D (Unix) or Ctrl+Z (Windows) to exit.")
    print("Run `help()` to view helper info")
    help()
    code.interact(local=locals())

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