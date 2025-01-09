import sys
import threading
import traceback
from typing import Optional
from palworld_pal_editor.core import *
from palworld_pal_editor.utils import *
from palworld_pal_editor.config import *

# InteractThread: Credit to MagicBear. I was just too lazy to write it, lol.
class InteractThread(threading.Thread):
    _instance = None
    banner_message = ColorConsoleFormatter.get_colored_msg(f"\n!Interactive Mode Enabled!\nThank you for using Palworld Pal Editor, made by _connlost with ❤.\nType pal_help() for Pal Editor help message\nType help(object) for help about object.")

    def __init__(self):
        super().__init__(daemon=True)

    @staticmethod
    def load():
        if InteractThread._instance is None:
            InteractThread._instance = InteractThread()
            InteractThread._instance.start()
        return InteractThread._instance

    def interact_readfunc(self, prompt):
        print(prompt, end="", flush=True)
        line = sys.stdin.readline()
        if line.strip() == "quit()":
            return None
        return line

    def run(self):
        LOGGER.info(f"Palworld Pal Editor, made by _connlost with ❤.")
        import code
        try:
            code.interact(banner=InteractThread.banner_message, readfunc=self.interact_readfunc, local=globals())
        except Exception as e:
            traceback.print_exception(e)
        InteractThread._instance = None

def main():
    LOGGER.info("Palworld Pal Editor, made by _connlost with ❤.")
    save_manager = SaveManager()
    try:
        if Config.path and save_manager.open(Config.path):
            pass
        else:
            while True:
                msg = ColorConsoleFormatter.get_colored_msg("> Please provide the path to the dir containing Level.sav")
                LOGGER.info(msg)
                input_path = input(ColorConsoleFormatter.get_colored_msg("> "))
                if save_manager.open(input_path) is not None:
                    break
    except Exception as e:
        LOGGER.warning(f"{e}")

    InteractThread.load().join()


def list_player() -> list[PlayerEntity]:
    """
    List all players.
    """
    players = SaveManager().get_players()
    for player in players:
        LOGGER.info(f" - {player}")
    return players

def get_player(uid: str) -> PlayerEntity:
    """
    Get player by player uid.
    """
    player = SaveManager().get_player(uid)
    LOGGER.info(f" - {player}")
    return player

def get_players_by_name(name: str) -> list[PlayerEntity]:
    """
    Try get players by name, can be duplicated, or empty.
    """
    players = SaveManager().get_players_by_name(name)
    for player in players:
        LOGGER.info(f" - {player}")
    return players

def list_player_pals(player: PlayerEntity | str) -> list[PalEntity]:
    """
    List pals of the given PlayerEntity | player name | PlayerUId
    Note that if Player Name is provided, only the first matched player will be used.
    """
    if isinstance(player, PlayerEntity):
        pass
    elif players := get_players_by_name(player):
        player = players[0]
    elif isUUIDStr(player):
        player = get_player(player)
    pals = player.get_sorted_pals()
    for pal in pals:
        LOGGER.info(f" - {pal}")
    return pals

def get_pal(guid: str) -> Optional[PalEntity]:
    pal = SaveManager().get_pal(guid)
    LOGGER.info(f" - {pal}")
    return pal

def delete_pal(guid: str):
    SaveManager().delete_pal(guid)

def batch_pal_delete(guid_list: list[str]):
    for guid in guid_list:
        delete_pal(guid, yes=True)

def add_pal(player_uid: str) -> Optional[PalEntity]:
    return SaveManager().add_pal(player_uid)

def dupe_pal(player_uid: str, pal_guid: str) -> Optional[PalEntity]:
    player = SaveManager().get_player(player_uid)
    pal_obj = player.get_pal(pal_guid)._pal_obj
    if not pal_obj:
        LOGGER.warning("Unable to find the target pal.")
        return

    return SaveManager().add_pal(player_uid, pal_obj)


def list_attacks():
    sorted_list = DataProvider.get_sorted_attacks()
    for item in sorted_list:
        LOGGER.info(
            " - [{}][{}]{} {}: {} ".format(
                item["Element"],
                item["Power"],
                (
                    "[🍎]"
                    if DataProvider.has_skill_fruit(item["InternalName"])
                    else ""
                ),
                DataProvider.get_attack_i18n(item["InternalName"])[0],
                item["InternalName"]))

def list_passives():
    sorted_list = DataProvider.get_sorted_passives()
    for item in sorted_list:
        internal_name = item["InternalName"]
        name, desc = DataProvider.get_passive_i18n(item["InternalName"])
        LOGGER.info(
            " -  {}  |  {}  |  {}"
            .format(name, internal_name, desc))

def lang(i18n_code):
    if DataProvider.is_valid_i18n(i18n_code):
        Config.i18n = i18n_code
    else:
        LOGGER.warning(f"I18n code {i18n_code} not available. Select from {DataProvider.get_i18n_options()}")

def save():
    SaveManager().save(SaveManager()._file_path)

def print_example():
    msg = r"""
    ##########################################################
    #  - ** Examples **
    #  >>> list_player()
    #  [INFO] player_name - f010f436-0000-0000-0000-000000000000 - 3a54133f-74e2-4e6d-9b3f-39bd81178be2
    #  [INFO] ...
    #  >>> list_player_pals("f010f436-0000-0000-0000-000000000000")
    #  [INFO] Foxcicle♂ - OwnerName - 66dbae51-1da3-43cb-ab62-44f2177a474e
    #  [INFO] ...
    #  >>> pal = get_pal("66dbae51-1da3-43cb-ab62-44f2177a474e")
    #  >>> pal.IsBOSS
    #  False or True
    #  >>> pal.IsBOSS = True
    #  [INFO] 💀Foxcicle♂ - OwnerName - 66dbae51-1da3-43cb-ab62-44f2177a474e | CharacterID: IceFox -> BOSS_IceFox
    #  [INFO] 💀Foxcicle♂ - OwnerName - 66dbae51-1da3-43cb-ab62-44f2177a474e | IsBOSS: False -> True
    #  ...
    #  >>> pal.MasteredWaza
    #  ['EPalWazaID::AirCanon', 'EPalWazaID::IceMissile']
    #  >>> list_attacks()
    #  [INFO]  - [Dark][30][🍎] Poison Blast: EPalWazaID::PoisonShot
    #  ...
    #  >>> pal.add_MasteredWaza("EPalWazaID::PoisonShot")
    #  [INFO] 💀Foxcicle♂ - OwnerName - 66dbae51-1da3-43cb-ab62-44f2177a474e | MasteredWaza: ['EPalWazaID::AirCanon', 'EPalWazaID::IceMissile'] -> ['EPalWazaID::AirCanon', 'EPalWazaID::IceMissile', 'EPalWazaID::PoisonShot']
    #  >>> ...
    #  >>> save_manager.save(r"D:\gamesave\Level_new.sav")
    ##########################################################
    """
    msg = ColorConsoleFormatter.get_colored_msg(msg)
    LOGGER.info(msg)

def pal_help():
    msg = r"""
    Helper Functions:
        - pal_help()
        - print_example()

        - list_player() -> list[PlayerEntity]
        - get_player(uid: str) -> PlayerEntity
        - get_players_by_name(name: str) -> list[PlayerEntity]

        - list_player_pals(player: PlayerEntity | str) -> list[PalEntity]
        - get_pal(guid: str) -> Optional[PalEntity]

        - add_pal(player_uid: str) -> Optional[PalEntity]
        - dupe_pal(player_uid: str, pal_guid: str) -> Optional[PalEntity]
        - delete_pal(guid: str)
        - batch_pal_delete(guid_list: list[str])

        - list_attacks()
        - list_passives()
        - lang(i18n_code)
        - save()

    Step To Modify a Pal (You can run `print_example()` to see a real example):
      1. Get the pal: `pal = get_pal(pal_id)`
      2. Check PalEntity usage by calling: `help(PalEntity)`
      2. Set the pal's property: `pal.[ property name ] = [ property value ]`, e.g. `pal.Hp = 200`

    Learn more about each class, call `help(class_name)`:
    Useful Classes:
        - PalEntity
        - PlayerEntity
        - SaveManager
        - ...
    """
    msg = ColorConsoleFormatter.get_colored_msg(msg)
    LOGGER.info(msg)