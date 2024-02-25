from typing import Any, Optional
from palworld_save_tools.archive import UUID

from palworld_pal_editor.utils import LOGGER, clamp
from palworld_pal_editor.data_provider import DataProvider
from palworld_pal_editor.pal_objects import get_attr_value, PalObjects, PalGender, PalRank


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
        return "%s - %s - %s" % (self.DisplayName, self.OwnerName, self.InstanceId)
    
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
    def OwnerName(self) -> str:
        from .save_manager import SaveManager
        player = SaveManager().get_player(self.OwnerPlayerUId)
        if player:
            nickname = player.NickName
            return nickname if nickname else self.OwnerPlayerUId
        return self.OwnerPlayerUId
    
    @property
    def OldOwnerPlayerUIds(self) -> Optional[list[UUID]]:
        return get_attr_value(self._pal_param, "OldOwnerPlayerUIds")
    
    @property
    def CharacterID(self) -> Optional[str]:
        return get_attr_value(self._pal_param, "CharacterID")
    
    @CharacterID.setter
    @LOGGER.change_logger('CharacterID')
    def CharacterID(self, value: str) -> None:
        if self.CharacterID is None:
            self._pal_param["CharacterID"] = PalObjects.NameProperty(value)
        else:
            PalObjects.set_BaseType(self._pal_param["CharacterID"], value)
    
    @property
    def _RawSpecieKey(self) -> Optional[str]:
        key = self.CharacterID
        if self._IsBOSS:
            if "Boss_" in key:
                key = key.split("Boss_")[1]
            else:
                key = key.split("BOSS_")[1]
        return key

    @property
    def IconAccessKey(self) -> Optional[str]:
        if DataProvider.pal_is_human(self.DataAccessKey):
            return "Human"
        return self.DataAccessKey

    @property
    def DataAccessKey(self) -> Optional[str]:
        key = self._RawSpecieKey
        match key:
            case "SheepBall":
                key = "Sheepball"
            case "LazyCatFish":
                key = "LazyCatfish"
        return key
    
    @property
    def DisplayName(self) -> str:
        name = DataProvider.pal_specie_name(self.DataAccessKey)
        name = name if name else self.DataAccessKey
        name += f" ({self.NickName})" if self.NickName else ""
        if self.IsRarePal:
            name = "✨" + name
        if self.IsBOSS:
            name = "💀" + name
        match self.Gender:
            case PalGender.FEMALE.value: name += "♀"
            case PalGender.MALE.value: name += "♂"
        return name
    
    @property
    def PalDeckID(self) -> str:
        key = DataProvider.pal_sorting_key(self.DataAccessKey)
        return key if key else self.DataAccessKey
    
    @property
    def Gender(self) -> Optional[str]:
        return PalGender.from_value(get_attr_value(self._pal_param, "Gender", ["value"]))
    
    @Gender.setter
    @LOGGER.change_logger('Gender')
    def Gender(self, gender: PalGender) -> None:
        if not self.Gender:
            LOGGER.warning("This pal has no gender.")
            return
        PalObjects.set_EnumProperty(self._pal_param["Gender"], gender.value)

    @property
    def _IsBOSS(self) -> bool:
        """
        Check if CharacterID has BOSS_ or Boss_ prefix.
        """
        if "BOSS_" in self.CharacterID or "Boss_" in self.CharacterID:
            return True
        
    @_IsBOSS.setter
    def _IsBOSS(self, value: bool) -> None:
        if not value:
            self.CharacterID = self._RawSpecieKey
        elif not self._IsBOSS and value:
            self.CharacterID = f"BOSS_{self._RawSpecieKey}"
    
    @property
    def IsBOSS(self) -> bool:
        """
        Check if the pal is diaplayed as BOSS in game.
        """
        if self.IsRarePal:
            return False
        return self._IsBOSS
    
    @IsBOSS.setter
    @LOGGER.change_logger('IsBOSS')
    def IsBOSS(self, value: bool) -> None:
        if self.IsRarePal and value:
            self.IsRarePal = False
        self._IsBOSS = value

        # TODO Update MaxHP

    @property
    def IsRarePal(self) -> bool:
        return get_attr_value(self._pal_param, "IsRarePal")
    
    @IsRarePal.setter
    @LOGGER.change_logger('IsRarePal')
    def IsRarePal(self, value: bool) -> None:
        if self.IsRarePal is None:
            self._pal_param["IsRarePal"] = PalObjects.BoolProperty(value)
        else:
            PalObjects.set_BaseType(self._pal_param["IsRarePal"], value)
        
        # from my observation, all rare pals are named BOSS_PalCharacterId
        if value and not self._IsBOSS:
            self.CharacterID = "BOSS_" + self.CharacterID
    
    @property
    def NickName(self) -> Optional[str]:
        return get_attr_value(self._pal_param, "NickName")
    
    @NickName.setter
    @LOGGER.change_logger('NickName')
    def NickName(self, value: str) -> None:
        if self.NickName is None:
            self._pal_param["NickName"] = PalObjects.StrProperty(value)
        else:
            self._pal_param["NickName"]["value"] = value

    @property
    def Level(self) -> Optional[int]:
        return get_attr_value(self._pal_param, "Level")
    
    @Level.setter
    @LOGGER.change_logger('Level')
    def Level(self, value: int) -> None:
        value = clamp(1, 50, value)
        if self.Level is None:
            self._pal_param["Level"] = PalObjects.IntProperty(value)
        else:
            self._pal_param["Level"]["value"] = value
        self.Exp = DataProvider.pal_level_to_xp(self.Level)
        # TODO Update MaxHP

    @property
    def Exp(self) -> Optional[int]:
        return get_attr_value(self._pal_param, "Exp")
    
    @Exp.setter
    @LOGGER.change_logger('Exp')
    def Exp(self, value: int) -> None:
        if self.Exp is None:
            self._pal_param["Exp"] = PalObjects.IntProperty(value)
        else:
            self._pal_param["Exp"]["value"] = value

    @property
    def Rank(self) -> Optional[PalRank]:
        return PalRank.from_value(get_attr_value(self._pal_param, "Rank"))

    @Rank.setter
    @LOGGER.change_logger('Rank')
    def Rank(self, rank: PalRank) -> None:
        if self.Rank is None:
            self._pal_param["Rank"] = PalObjects.IntProperty(rank.value)
        else:
            PalObjects.set_BaseType(self._pal_param["Rank"], rank.value)
        # TODO
        # Update MaxHP

    @property
    def HP(self) -> Optional[int]:
        return get_attr_value(self._pal_param, "HP", nested_keys=["value", "Value"])
    
    @HP.setter
    @LOGGER.change_logger('HP')
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