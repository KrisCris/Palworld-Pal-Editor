from typing import Any, Optional
from palworld_save_tools.archive import UUID
from .utils import Logger
from .pal_entity import PalEntity

LOGGER = Logger()

from .pal_objects import get_attr_value, PalObjects

class PlayerEntity:
    def __init__(self, player_obj: dict, palbox: set[PalEntity] = set()) -> None:
        self._player_obj: dict = player_obj
        self.palbox = palbox

        if self._player_obj["value"]["RawData"]["value"]["object"]["SaveParameter"] != "PalIndividualCharacterSaveParameter":
            raise Exception("%s's save param is not PalIndividualCharacterSaveParameter" % self._player_obj)

        self._player_key: dict = self._player_obj['key']
        self._player_param: dict = self._player_obj['value']['RawData']['value']['object']['SaveParameter']['value']

        if not get_attr_value(self._player_param, "IsPlayer"):
            raise TypeError(
                "Expecting player_obj, received pal_obj: %s - %s - %s - %s" % 
                (get_attr_value(self._player_param, "CharacterID"), self.NickName, self.PlayerUId, self.InstanceId)
            )

    def __str__(self) -> str:
        return "%s - %s - %s" % (self.NickName, self.PlayerUId, self.InstanceId)
    
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
        return get_attr_value("NickName")
    
    def add_pal(self, pal_entity: PalEntity) -> bool:
        if pal_entity in self.palbox:
            return False
        self.palbox.add(pal_entity)
        return True
