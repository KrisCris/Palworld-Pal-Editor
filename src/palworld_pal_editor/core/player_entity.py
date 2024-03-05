from typing import Any, Optional
from palworld_save_tools.archive import UUID
from palworld_save_tools.gvas import GvasFile

from palworld_pal_editor.utils import LOGGER, alphanumeric_key
from palworld_pal_editor.core.pal_entity import PalEntity
from palworld_pal_editor.core.pal_objects import get_attr_value


class PlayerEntity:
    def __init__(self, player_obj: dict, palbox: dict[str, PalEntity], gvas_file: GvasFile, compression_times: int) -> None:
        self._player_obj: dict = player_obj
        self._palbox = palbox
        self._gvas_file = gvas_file
        self._gvas_compression_times = compression_times

        if self._player_obj["value"]["RawData"]["value"]["object"]["SaveParameter"]['struct_type'] != "PalIndividualCharacterSaveParameter":
            raise Exception(f"{self._player_obj}'s save param is not PalIndividualCharacterSaveParameter")

        self._player_key: dict = self._player_obj['key']
        self._player_param: dict = self._player_obj['value']['RawData']['value']['object']['SaveParameter']['value']

        if not get_attr_value(self._player_param, "IsPlayer"):
            raise TypeError(
                "Expecting player_obj, received pal_obj: {} - {} - {} - {}".format(
                    get_attr_value(self._player_param, "CharacterID"), self.NickName, self.PlayerUId, self.InstanceId)
            )

    def __str__(self) -> str:
        return "{} - {} - {}".format(self.NickName, self.PlayerUId, self.InstanceId)
    
    def __hash__(self) -> int:
        return hash((self.InstanceId.__hash__(), self.PlayerUId.__hash__()))

    def __eq__(self, __value: object) -> bool:
        return isinstance(__value, PlayerEntity) and self.InstanceId == __value.InstanceId and self.PlayerUId == __value.PlayerUId

    @property
    def PlayerUId(self) -> Optional[UUID]:
        return get_attr_value(self._player_key, "PlayerUId")
    
    @property
    def InstanceId(self) -> Optional[UUID]:
        return get_attr_value(self._player_key, "InstanceId")
    
    @property
    def NickName(self) -> Optional[str]:
        return get_attr_value(self._player_param, "NickName")
    
    @property
    def PlayerGVAS(self) -> Optional[tuple[GvasFile, int]]:
        if (self._gvas_file is None) or (self._gvas_compression_times is None):
            return None
        return self._gvas_file, self._gvas_compression_times
    
    def new_pal(self, pal_entity: PalEntity) -> bool:
        raise NotImplementedError()

    def add_pal(self, pal_entity: PalEntity) -> bool:
        """
        This method only inserts player's pals to `self.palbox`.\n
        Do not confuse with `self.new_pal()`, which is planned for creating pals. 
        """
        pal_guid = str(pal_entity.InstanceId)
        if pal_guid in self._palbox:
            return False
        self._palbox[pal_guid] = pal_entity
        return True
    
    def get_pals(self) -> list[PalEntity]:
        return self._palbox.values()
    
    def get_pal(self, guid: UUID | str) -> Optional[PalEntity]:
        guid = str(guid)
        if guid in self._palbox:
            return self._palbox[guid]
        LOGGER.warning(f"Player {self} has no pal {guid}.")

    def get_sorted_pals(self, sorting_key="paldeck") -> list[PalEntity]:
        match sorting_key:
            case "paldeck": 
                return sorted(self.get_pals(), key=lambda pal: (alphanumeric_key(pal.PalDeckID), pal.Level or 1))