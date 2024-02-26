import code
from typing import Optional
from palworld_pal_editor.pal_entity import PalEntity
from palworld_pal_editor.player_entity import PlayerEntity
from palworld_pal_editor.utils import LOGGER
from palworld_pal_editor.config import Config
from palworld_pal_editor.pal_objects import isUUIDStr
from palworld_pal_editor.data_provider import DataProvider


def main():
    from palworld_pal_editor.save_manager import SaveManager

    LOGGER.info("Palworld Pal Editor, made by _connlost with ❤.")
    save_manager = SaveManager()
    while True:
        LOGGER.info("> Please provide the path to Level.sav")
        input_path = input("> ")
        try:
            if save_manager.open(input_path) is not None:
                break
        except Exception as e:
            LOGGER.warning(f"{e}")

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

    def get_player_by_name(name: str) -> list[PlayerEntity]:
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
        elif players := get_player_by_name(player):
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

    def list_attacks():
        sorted_list = DataProvider.get_sorted_attacks()
        for item in sorted_list:
            LOGGER.info(
                " - [%s][%s]%s %s: %s "
                % (
                    item["Type"],
                    item["Power"],
                    (
                        "[🍎]"
                        if DataProvider.attack_has_skill_fruit(item["CodeName"])
                        else ""
                    ),
                    DataProvider.attack_i18n(item["CodeName"]),
                    item["CodeName"],
                )
            )

    def pal_help():
        LOGGER.info(
"""
- class SaveManager:
> Singleton Class so you can call SaveManager() multiple times.
-     `SaveManager()`: Get the SaveManager Instance
-     `SaveManager().open(path: str)`: Open a new file
-     `SaveManager().save(path: str)`: Save to a new file
-     `SaveManager().get_players() -> list[PlayerEntity]`: Print and get the players list
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
- `pal_entity.Rank`: Getter, Setter 
-     (from palworld_pal_editor.pal_object import PalRank, PalRank.Rank1/2/3/4)
- `pal_entity.MasteredWaza`
- `pal_entity.add_MasteredWaza(internal_waza_name)`
-     (try use list_attacks() to see all waza)
- `pal_entity.pop_MasteredWaza(idx=None, item=None)`
-     (Use either idx or Waza name)
- `pal_entity.HP`: Getter, Setter
- ... 
- ...refer to the code
- `pal_entity.print_stats()`: print out stats

- ** Functions You May Want to Try First **
- pal_help()
- list_player()
- get_player(uid: str) -> PlayerEntity
- get_player_by_name(name: str) -> list[PlayerEntity]
- list_player_pals(player: PlayerEntity | str) -> list[PalEntity]
- get_pal(guid: str) -> Optional[PalEntity]
- list_attacks(): print out all sorted pal attacks

- ** Examples **
>>> list_player()
[INFO] player_name - f010f436-0000-0000-0000-000000000000 - 3a54133f-74e2-4e6d-9b3f-39bd81178be2
[INFO] ...
>>> list_player_pals("f010f436-0000-0000-0000-000000000000")
[INFO] Foxcicle♂ - OwnerName - 66dbae51-1da3-43cb-ab62-44f2177a474e
[INFO] ...
>>> pal = get_pal("66dbae51-1da3-43cb-ab62-44f2177a474e")
>>> pal.IsBOSS
False or True
>>> pal.IsBOSS = True
[INFO] 💀Foxcicle♂ - OwnerName - 66dbae51-1da3-43cb-ab62-44f2177a474e | CharacterID: IceFox -> BOSS_IceFox
[INFO] 💀Foxcicle♂ - OwnerName - 66dbae51-1da3-43cb-ab62-44f2177a474e | IsBOSS: False -> True
...
>>> pal.MasteredWaza
['EPalWazaID::AirCanon', 'EPalWazaID::IceMissile']
>>> list_attacks()
[INFO]  - [Dark][30][🍎] Poison Blast: EPalWazaID::PoisonShot
...
>>> pal.add_MasteredWaza("EPalWazaID::PoisonShot")
[INFO] 💀Foxcicle♂ - OwnerName - 66dbae51-1da3-43cb-ab62-44f2177a474e | MasteredWaza: ['EPalWazaID::AirCanon', 'EPalWazaID::IceMissile'] -> ['EPalWazaID::AirCanon', 'EPalWazaID::IceMissile', 'EPalWazaID::PoisonShot']
>>> ...
>>> save_manager.save(r"D:\gamesave\Level_new.sav")
"""
        )
    
    # interactive mode?
    # if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    banner_message = f"\nThank you for using Palworld Pal Editor, made by _connlost with ❤.\nType pal_help() for Pal Editor help message\nType help(object) for help about object."

    pal_help()

    code.interact(banner=banner_message, local=locals())

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
