from typing import Any, Optional
from palworld_save_tools.archive import UUID

from palworld_pal_editor.utils import LOGGER, clamp
from palworld_pal_editor.data_provider import DataProvider
from palworld_pal_editor.pal_objects import get_attr_value, get_nested_attr, PalObjects, PalGender, PalRank


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
        
        self._display_name_cache = {}
        ## TODO
        # self._isBoss_cache = {}
        # self._raw_specie_key_cache = {}
        # self._data_access_key_cache = {}

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
        if DataProvider.is_pal_human(self.DataAccessKey):
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
        # ## TODO maybe cache some of the expaneive operations in the future
        # name = DataProvider.pal_specie_name(self.DataAccessKey)
        # name = name if name else self.DataAccessKey
        # name += f" ({self.NickName})" if self.NickName else ""
        # if self.IsRarePal:
        #     name = "✨" + name
        # if self.IsBOSS:
        #     name = "💀" + name
        # match self.Gender:
        #     case PalGender.FEMALE.value: name += "♀"
        #     case PalGender.MALE.value: name += "♂"
        # return name
        return self._get_display_name()
    
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
        if not isinstance(gender, PalGender):
            LOGGER.warning(f"Invalid gender value: {gender}")
            return
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
        return False
        
    @_IsBOSS.setter
    @LOGGER.change_logger("_IsBOSS")
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
        # Boss and Rare can only exist one
        if self.IsRarePal and not value:
            return
        if self.IsRarePal and value:
            self.IsRarePal = False
        self._IsBOSS = value
        # TODO Update MaxHP

    @property
    def IsRarePal(self) -> Optional[bool]:
        return get_attr_value(self._pal_param, "IsRarePal")
    
    @IsRarePal.setter
    @LOGGER.change_logger('IsRarePal')
    def IsRarePal(self, value: bool) -> None:
        # Boss and Rare can only exist one
        if self.IsBOSS and not value:
            return
        # if self.IsBOSS and value:
        #     self.IsBOSS = False

        if self.IsRarePal is None:
            self._pal_param["IsRarePal"] = PalObjects.BoolProperty(value)
        else:
            PalObjects.set_BaseType(self._pal_param["IsRarePal"], value)

        if value and not self._IsBOSS:
            self._IsBOSS = True
        if not value and self._IsBOSS:
            self._IsBOSS = False
    
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
        if not isinstance(rank, PalRank):
            LOGGER.warning(f"Invalid rank value {rank}")
            return
        # if rank == PalRank.Rank0:
        #     self._pal_param.pop('Rank', None)
        #     return
        if self.Rank is None:
            self._pal_param["Rank"] = PalObjects.IntProperty(rank.value)
        else:
            PalObjects.set_BaseType(self._pal_param["Rank"], rank.value)
        # TODO
        # Update MaxHP

    @property
    def Rank_HP(self) -> Optional[str]:
        return get_attr_value(self._pal_param, "Rank_HP")

    @Rank_HP.setter
    @LOGGER.change_logger('Rank_HP')
    def Rank_HP(self, rank: int) -> None:
        self._set_soul_rank('Rank_HP', rank)

    @property
    def Rank_Attack(self) -> Optional[str]:
        return get_attr_value(self._pal_param, "Rank_Attack")

    @Rank_Attack.setter
    @LOGGER.change_logger('Rank_Attack')
    def Rank_Attack(self, rank: int) -> None:
        self._set_soul_rank('Rank_Attack', rank)

    @property
    def Rank_Defence(self) -> Optional[str]:
        return get_attr_value(self._pal_param, "Rank_Defence")

    @Rank_Defence.setter
    @LOGGER.change_logger('Rank_Defence')
    def Rank_Defence(self, rank: int) -> None:
        self._set_soul_rank('Rank_Defence', rank)

    @property
    def Rank_CraftSpeed(self) -> Optional[str]:
        return get_attr_value(self._pal_param, "Rank_CraftSpeed")

    @Rank_CraftSpeed.setter
    @LOGGER.change_logger('Rank_CraftSpeed')
    def Rank_CraftSpeed(self, rank: int) -> None:
        self._set_soul_rank('Rank_CraftSpeed', rank)

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

    @property
    def EquipWaza(self) -> Optional[list[str]]:
        return PalObjects.get_ArrayProperty(self._pal_param.get("EquipWaza"))

    @property
    def EquipWazaSet(self) -> Optional[set[str]]:
        return set(self.EquipWaza) if self.EquipWaza is not None else None

    @LOGGER.change_logger('EquipWaza')
    def add_EquipWaza(self, waza: str) -> bool:
        """
        Normally you can't add the same "waza" twice on a pal.
        """
        if not DataProvider.has_attack(waza):
            LOGGER.warning(f"Pal attack {waza} not in database, skipping")
            return False
        
        if self.EquipWaza is None:
            self._pal_param["EquipWaza"] = PalObjects.ArrayProperty("EnumProperty", {"values": []})
        
        if waza in self.EquipWazaSet:
            LOGGER.warning(f"{self} has already equipped waza {waza}, skipping")
            return False
        
        if len(self.EquipWaza) >= 3:
            LOGGER.warning(f"{self} EquipWaza maxed out {self.EquipWaza}, consider add to MasteredWaza instead.")
            return False
        
        self.EquipWaza.append(waza)
        # PalObjects.add_ArrayProperty(self._pal_param["EquipWaza"], waza)
        # TODO add waza MasteredWaza
        if waza not in self.MasteredWaza:
            self.add_MasteredWaza(waza)

        LOGGER.info(f"Added {DataProvider.attack_i18n(waza)} to EquipWaza")
        return True
    
    @LOGGER.change_logger('EquipWaza')
    def pop_EquipWaza(self, idx: int = None, item: str = None) -> Optional[str]:
        try:
            if item is not None:
                idx = self.EquipWaza.index(item)
            waza = self.EquipWaza.pop(int(idx))
            LOGGER.info(f"Removed {DataProvider.attack_i18n(waza)} from EquipWaza")
            return waza
        except Exception as e:
            LOGGER.warning(f"{e}")

    @property
    def MasteredWaza(self) -> Optional[list[str]]:
        return PalObjects.get_ArrayProperty(self._pal_param.get("MasteredWaza"))

    @property
    def MasteredWazaSet(self) -> Optional[set[str]]:
        return set(self.MasteredWaza) if self.MasteredWaza is not None else None

    @LOGGER.change_logger('MasteredWaza')
    def add_MasteredWaza(self, waza: str) -> bool:
        """
        Normally you can't add the same "waza" twice on a pal.
        """
        if not DataProvider.has_attack(waza):
            LOGGER.warning(f"Pal attack {waza} not in database, skipping")
            return False
    
        if self.MasteredWaza is None:
            self._pal_param["MasteredWaza"] = PalObjects.ArrayProperty("EnumProperty", {"values": []})

        if waza in self.MasteredWazaSet:
            LOGGER.info(f"{self} has already learned waza {waza}, skipping")
            return False
        
        self.MasteredWaza.append(waza)
        # PalObjects.add_ArrayProperty(self._pal_param["MasteredWaza"], waza)
        LOGGER.info(f"Added {DataProvider.attack_i18n(waza)} to MasteredWaza")
        return True

    @LOGGER.change_logger('MasteredWaza')
    def pop_MasteredWaza(self, idx: int = None, item: str = None) -> Optional[str]:
        try:
            if item is not None:
                idx = self.MasteredWaza.index(item)
            waza = self.MasteredWaza.pop(int(idx))
            if waza in self.EquipWazaSet:
                self.pop_EquipWaza(item=waza)
            # return PalObjects.pop_ArrayProperty(self._pal_param["MasteredWaza"], idx)
            LOGGER.info(f"Removed {DataProvider.attack_i18n(waza)} from MasteredWaza")
            return waza
        except Exception as e:
            LOGGER.warning(f"{e}")

    def print_stats(self):
        lines = [f"{self}: "]
        tab = "\t"
        for key in self._pal_param:
            line = f"{tab}- {key}: "

            container = self._pal_param[key]
            value = PalObjects.get_container_value(container)

            if isinstance(value, list):
                lines.append(line)
                for item in value:
                    sub_line = f"{tab * 2}- {item}"
                    lines.append(sub_line)
                continue

            if value is None:
                value = f"Not yet supported, but you can manually print it by `vars(pal._pal_param['{key}'])`"

            lines.append(f"{line}{value}")
        LOGGER.info("\n".join(lines))

    def _set_soul_rank(self, property_name: str, rank: int):
        rank = clamp(0, 10, rank)
        # if rank == 0:
        #     self._pal_param.pop(property_name, None)
        #     return
        if self.Rank is None:
            self._pal_param[property_name] = PalObjects.IntProperty(rank)
        else:
            PalObjects.set_BaseType(self._pal_param[property_name], rank)

    def _get_display_name(self) -> str:
        cache_key = (self.DataAccessKey, self.NickName, self.IsRarePal, self.IsBOSS, self.Gender)
        try:
            return self._display_name_cache[cache_key]
        except KeyError:
            species_name = DataProvider.pal_i18n(self.DataAccessKey) or self.DataAccessKey
            rare_prefix = "✨" if self.IsRarePal else ""
            boss_prefix = "💀" if self.IsBOSS else ""
            nickname_suffix = f" ({self.NickName})" if self.NickName else ""

            gender_suffix = ""
            if self.Gender == PalGender.FEMALE:
                gender_suffix = "♀"
            elif self.Gender == PalGender.MALE:
                gender_suffix = "♂"

            name = f"{rare_prefix}{boss_prefix}{species_name}{nickname_suffix}{gender_suffix}"
            self._display_name_cache[cache_key] = name
            return name
        
    def _save(self) -> None:
        # clean up and delete empty / unused entries
        # Rank_type = 0, Rank = PalRank.Rank0
        # nickname? etc
        pass