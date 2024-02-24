from typing import Any, Optional
from palworld_save_tools.archive import UUID
from .utils import Logger
LOGGER = Logger()

from .pal_objects import get_attr_value, PalObjects

class PalEntity:
    def __init__(self, pal_obj: dict) -> None:
        self._pal_obj: dict = pal_obj

        if self._pal_obj["value"]["RawData"]["value"]["object"]["SaveParameter"]['struct_type'] != "PalIndividualCharacterSaveParameter":
            raise Exception("%s's save param is not PalIndividualCharacterSaveParameter" % self._pal_obj)

        self._pal_key: dict = self._pal_obj['key']
        self._pal_param: dict = self._pal_obj['value']['RawData']['value']['object']['SaveParameter']['value']

        if self.InstanceId is None:
            raise Exception(f"No GUID, skipping {self}")

        if get_attr_value(self._pal_param, "IsPlayer"):
            raise TypeError("Expecting pal_obj, received player_obj: %s - %s - %s" % (self.NickName, self.PlayerUId, self.InstanceId))

    def __str__(self) -> str:
        return "%s - %s - %s - %s" % (self.CharacterID, self.NickName, self.OwnerPlayerUId, self.InstanceId)
    
    def __hash__(self) -> int:
        return self.InstanceId.__hash__()

    def __eq__(self, __value: object) -> bool:
        return isinstance(__value, PalEntity) and self.InstanceId == __value.InstanceId

    @property
    def PlayerUId(self) -> Optional[UUID]:
        return get_attr_value(self._pal_key, "PlayerUId")
    
    @property
    def InstanceId(self) -> Optional[UUID]:
        return get_attr_value(self._pal_key, "InstanceId")
    
    @property
    def OwnerPlayerUId(self) -> Optional[UUID]:
        return get_attr_value(self._pal_param, "OwnerPlayerUId")
    
    @property
    def OldOwnerPlayerUIds(self) -> Optional[list[UUID]]:
        return get_attr_value(self._pal_param, "OldOwnerPlayerUIds")
    
    @property
    def CharacterID(self) -> Optional[str]:
        return get_attr_value(self._pal_param, "CharacterID")
    
    @property
    def NickName(self) -> Optional[str]:
        return get_attr_value(self._pal_param, "NickName")
    
    @NickName.setter
    def NickName(self, value: str) -> None:
        if self.NickName is None:
            self._pal_param["NickName"] = PalObjects.StrProperty(value)
        else:
            self._pal_param["NickName"]["value"] = value

    @property
    def Level(self) -> Optional[int]:
        return get_attr_value(self._pal_param, "Level")
    
    @Level.setter
    def Level(self, value: int) -> None:
        if self.Level is None:
            self._pal_param["Level"] = PalObjects.IntProperty(value)
        else:
            self._pal_param["Level"]["value"] = value

    @property
    def Exp(self) -> Optional[int]:
        return get_attr_value(self._pal_param, "Exp")
    
    @Exp.setter
    def Exp(self, value: int) -> None:
        if self.Exp is None:
            self._pal_param["Exp"] = PalObjects.IntProperty(value)
        else:
            self._pal_param["Exp"]["value"] = value

    @property
    def HP(self) -> Optional[int]:
        return get_attr_value(self._pal_param, "HP", nested_keys=["value", "Value"])
    
    @HP.setter
    def HP(self, value: int) -> None:
        if self.HP is None:
            self._pal_param["HP"] = PalObjects.FixedPoint64(value)
        else:
            self._pal_param["HP"]["value"]["Value"]["value"] = value


    def pprint_pal_stats(self):
        line = ""
        for key in self._pal_param:
            line += f" - {key}: "
            container = self._pal_param[key]
            value = PalObjects.get_container_value(container)
            if value is None:
                line += "print not yet supported"
            elif isinstance(value, list):
                line += "\n\t" + "\n\t".join(map(str, value))
            else:
                line += str(value)

            line += "\n"
        LOGGER.info(line)