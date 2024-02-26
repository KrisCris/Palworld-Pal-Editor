import math
from typing import Any, Optional
from palworld_save_tools.archive import UUID
from palworld_pal_editor.config import Config

from palworld_pal_editor.utils import LOGGER, clamp
from palworld_pal_editor.data_provider import DataProvider
from palworld_pal_editor.pal_objects import get_attr_value, get_nested_attr, PalObjects, PalGender, PalRank


class PalEntity:
    def __init__(self, pal_obj: dict) -> None:
        self._pal_obj: dict = pal_obj

        if self._pal_obj["value"]["RawData"]["value"]["object"]["SaveParameter"]['struct_type'] != "PalIndividualCharacterSaveParameter":
            raise Exception(f"{self._pal_obj}'s save param is not PalIndividualCharacterSaveParameter")

        self._pal_key: dict = self._pal_obj['key']
        self._pal_param: dict = self._pal_obj['value']['RawData']['value']['object']['SaveParameter']['value']

        if self.InstanceId is None:
            raise Exception(f"No GUID, skipping {self}")

        if get_attr_value(self._pal_param, "IsPlayer"):
            raise TypeError("Expecting pal_obj, received player_obj: {} - {} - {}".format(self.NickName, self.PlayerUId, self.InstanceId))
        
        self._derived_hp_scaling = self._derive_hp_scaling()
        self._display_name_cache = {}
        ## TODO
        # self._isBoss_cache = {}
        # self._raw_specie_key_cache = {}
        # self._data_access_key_cache = {}

    def __str__(self) -> str:
        return "{} - {} - {}".format(self.DisplayName, self.OwnerName, self.InstanceId)
    
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
    def Rank_HP(self) -> Optional[int]:
        return get_attr_value(self._pal_param, "Rank_HP")

    @property
    def Rank_Attack(self) -> Optional[int]:
        return get_attr_value(self._pal_param, "Rank_Attack")
    
    @property
    def Rank_Defence(self) -> Optional[int]:
        return get_attr_value(self._pal_param, "Rank_Defence")
    
    @property
    def Rank_CraftSpeed(self) -> Optional[int]:
        return get_attr_value(self._pal_param, "Rank_CraftSpeed")
    
    @Rank_HP.setter
    @LOGGER.change_logger('Rank_HP')
    def Rank_HP(self, rank: int) -> None:
        self._set_soul_rank('Rank_HP', rank)
        # TODO maxhp

    @Rank_Attack.setter
    @LOGGER.change_logger('Rank_Attack')
    def Rank_Attack(self, rank: int) -> None:
        self._set_soul_rank('Rank_Attack', rank)

    @Rank_Defence.setter
    @LOGGER.change_logger('Rank_Defence')
    def Rank_Defence(self, rank: int) -> None:
        self._set_soul_rank('Rank_Defence', rank)

    @Rank_CraftSpeed.setter
    @LOGGER.change_logger('Rank_CraftSpeed')
    def Rank_CraftSpeed(self, rank: int) -> None:
        self._set_soul_rank('Rank_CraftSpeed', rank)

    @property
    def ComputedMaxHP(self) -> int:
        """
        Credit to https://www.reddit.com/r/Palworld/comments/1afyau4/pal_stat_mechanics_hidden_ivs_levelup_stats_and/
        """
        Level = self.Level or 1
        HP_Stat = DataProvider.pal_scaling(self.DataAccessKey, "HP", self.IsBOSS) or self._derived_hp_scaling
        HP_IV = (self.Talent_HP or 0) * 0.3 / 100 # 30% of Talent
        HP_Bonus = self._get_passive_buff("b_HP") # 0
        HP_SoulBonus = (self.Rank_HP or 0) * 0.03 # 3% per incr Rank_HP
        CondenserBonus = ((self.Rank or PalRank.Rank0).value - 1) * 0.05 # 5% per incr Rank

        return math.floor(math.floor(500 + 5 * Level + HP_Stat * .5 * Level * (1 + HP_IV)) \
            * (1 + HP_Bonus) * (1 + HP_SoulBonus) * (1 + CondenserBonus))

    @property
    def ComputedAttack(self) -> Optional[int]:
        Level = self.Level or 1
        Attack_Stat = DataProvider.pal_scaling(self.DataAccessKey, "ATK", self.IsBOSS)
        if Attack_Stat is None:
            return None
        Attack_IV = (self.Talent_Shot or 0) * 0.3 / 100 # 30% of Talent
        Attack_Bonus = self._get_passive_buff("b_Attack") # 0
        Attack_SoulBonus = (self.Rank_Attack or 0) * 0.03 # 3% per incr Rank_HP
        CondenserBonus = ((self.Rank or PalRank.Rank0).value - 1) * 0.05 # 5% per incr Rank

        return math.floor(math.floor(100 + Attack_Stat * .075 * Level * (1 + Attack_IV)) \
            * (1 + Attack_Bonus) * (1 + Attack_SoulBonus) * (1 + CondenserBonus))
    
    @property
    def ComputedDefense(self) -> Optional[int]:
        Level = self.Level or 1
        Defense_Stat = DataProvider.pal_scaling(self.DataAccessKey, "DEF", self.IsBOSS)
        if Defense_Stat is None:
            return None
        Defense_IV = (self.Talent_Defense or 0) * 0.3 / 100 # 30% of Talent
        Defense_Bonus = self._get_passive_buff("b_Defense") # 0
        Defense_SoulBonus = (self.Rank_HP or 0) * 0.03 # 3% per incr Rank_HP
        CondenserBonus = ((self.Rank or PalRank.Rank0).value - 1) * 0.05 # 5% per incr Rank

        return math.floor(math.floor(100 + Defense_Stat * .075 * Level * (1 + Defense_IV)) \
            * (1 + Defense_Bonus) * (1 + Defense_SoulBonus) * (1 + CondenserBonus))

    @property
    def HP(self) -> Optional[int]:
        return PalObjects.get_FixedPoint64(self._pal_param.get("HP"))
        # return get_attr_value(self._pal_param, "HP", nested_keys=["value", "Value"])
    
    @HP.setter
    @LOGGER.change_logger('HP')
    def HP(self, value: int) -> None:
        if self.HP is None:
            self._pal_param["HP"] = PalObjects.FixedPoint64(value)
        else:
            PalObjects.set_FixedPoint64(self._pal_param["HP"], value)
            # self._pal_param["HP"]["value"]["Value"]["value"] = value
    @property
    def MaxHP(self) -> Optional[int]:
        return PalObjects.get_FixedPoint64(self._pal_param.get("MaxHP"))
    
    @MaxHP.setter
    @LOGGER.change_logger("MaxHP")
    def MaxHP(self, val: int) -> None:
        if self.MaxHP is None:
            self._pal_param["MaxHP"] = PalObjects.FixedPoint64(val)
        else:
            PalObjects.set_FixedPoint64(self._pal_param["MaxHP"], val)
    # TODO
    # "MaxHP":{
    #     "struct_type":"FixedPoint64",
    #     "struct_id":"palworld_save_tools.archive.UUID(""00000000-0000-0000-0000-000000000000"")",
    #     "id":"None",
    #     "value":{
    #         "Value":{
    #             "id":"None",
    #             "value":5405000,
    #             "type":"Int64Property"
    #         }
    #     },
    #     "type":"StructProperty"
    # },

    @property
    def PassiveSkillList(self) -> Optional[list[str]]:
        return PalObjects.get_ArrayProperty(self._pal_param.get("PassiveSkillList"))

    @LOGGER.change_logger('PassiveSkillList')
    def add_PassiveSkillList(self, skill: str) -> bool:
        if not DataProvider.has_passive_skill(skill):
            LOGGER.warning(f"Can't find pal passive {skill} in database, skipping")
            return False
        
        if self.PassiveSkillList is None:
            self._pal_param["PassiveSkillList"] = PalObjects.ArrayProperty("NameProperty", {"values": []})

        if skill in self.PassiveSkillList:
            LOGGER.warning(f"{self} already has passive {skill}, skipping")
            return False
        
        if len(self.PassiveSkillList) >= 4:
            LOGGER.warning(f"{self} PassiveSkillList has maxed out: {self.PassiveSkillList}, skipping")
            return False
        
        self.PassiveSkillList.append(skill)
        LOGGER.info(f"Added {DataProvider.passive_i18n(skill)[0]} to PassiveSkillList")
        return True
    
    @LOGGER.change_logger('PassiveSkillList')
    def pop_PassiveSkillList(self, idx: int = None, item: str = None) -> Optional[str]:
        try:
            if item is not None:
                idx = self.PassiveSkillList.index(item)
            skill = self.PassiveSkillList.pop(int(idx))
            LOGGER.info(f"Removed {DataProvider.passive_i18n(skill)[0]} from PassiveSkillList")
            return skill
        except Exception as e:
            LOGGER.warning(f"{e}")

    @property
    def EquipWaza(self) -> Optional[list[str]]:
        return PalObjects.get_ArrayProperty(self._pal_param.get("EquipWaza"))

    @LOGGER.change_logger('EquipWaza')
    def add_EquipWaza(self, waza: str) -> bool:
        """
        Normally you can't add the same "waza" twice on a pal.
        """
        if not DataProvider.has_attack(waza):
            LOGGER.warning(f"Can't find pal attack {waza} in database, skipping")
            return False
        
        if self.EquipWaza is None:
            self._pal_param["EquipWaza"] = PalObjects.ArrayProperty("EnumProperty", {"values": []})
        
        if waza in self.EquipWaza:
            LOGGER.warning(f"{self} has already equipped waza {waza}, skipping")
            return False
        
        if len(self.EquipWaza) >= 3:
            LOGGER.warning(f"{self} EquipWaza has maxed out: {self.EquipWaza}, consider add to MasteredWaza instead.")
            return False
        
        self.EquipWaza.append(waza)

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
        # Unused
        # We need a way to cache it, otherwise it's no better than idx into a list
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

        if waza in self.MasteredWaza:
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
            if waza in self.EquipWaza:
                self.pop_EquipWaza(item=waza)
            # return PalObjects.pop_ArrayProperty(self._pal_param["MasteredWaza"], idx)
            LOGGER.info(f"Removed {DataProvider.attack_i18n(waza)} from MasteredWaza")
            return waza
        except Exception as e:
            LOGGER.warning(f"{e}")

    @property
    def Talent_HP(self) -> Optional[int]:
        return PalObjects.get_BaseType(self._pal_param.get('Talent_HP'))
    
    @property
    def Talent_Melee(self) -> Optional[int]:
        return PalObjects.get_BaseType(self._pal_param.get('Talent_Melee'))
    
    @property
    def Talent_Shot(self) -> Optional[int]:
        return PalObjects.get_BaseType(self._pal_param.get('Talent_Shot'))
    
    @property
    def Talent_Defense(self) -> Optional[int]:
        return PalObjects.get_BaseType(self._pal_param.get('Talent_Defense'))
    
    @Talent_HP.setter
    @LOGGER.change_logger("Talent_HP")
    def Talent_HP(self, value: int):
        self._set_iv("Talent_HP", value)
        # TODO maxhp

    @Talent_Melee.setter
    @LOGGER.change_logger("Talent_Melee")
    def Talent_Melee(self, value: int):
        self._set_iv("Talent_Melee", value)

    @Talent_Shot.setter
    @LOGGER.change_logger("Talent_Shot")
    def Talent_Shot(self, value: int):
        self._set_iv("Talent_Shot", value)

    @Talent_Defense.setter
    @LOGGER.change_logger("Talent_Defense")
    def Talent_Defense(self, value: int):
        self._set_iv("Talent_Defense", value)
    
    # REALLY? Stored in Save??
    # "CraftSpeed":{
    #     "id":"None",
    #     "value":70,
    #     "type":"IntProperty"
    # },
            
    # TODO PAL HEALTH
    # Set to 100
    # "SanityValue":{
    #     "id":"None",
    #     "value":97.90009307861328,
    #     "type":"FloatProperty"
    # },
    # Full Stomach -> MaxFullStomach
    # "MaxFullStomach":{
    #     "id":"None",
    #     "value":400.0,
    #     "type":"FloatProperty"
    # },
    # "FullStomach":{
    #     "id":"None",
    #     "value":315.49505615234375,
    #     "type":"FloatProperty"
    # },
    # Just delete the entry:
    # "WorkerSick":{
    #     "id":"None",
    #     "value":{
    #         "type":"EPalBaseCampWorkerSickType",
    #         "value":"EPalBaseCampWorkerSickType::DepressionSprain"
    #     },
    #     "type":"EnumProperty"
    # },
    # Guess empty value is good?
    # "DecreaseFullStomachRates":{
    #     "struct_type":"FloatContainer",
    #     "struct_id":<palworld_save_tools.archive.UUID object at 0x00000140854CCF40>,
    #     "id":"None",
    #     "value":{
            
    #     },
    #     "type":"StructProperty"
    # },
    # "AffectSanityRates":{
    #     "struct_type":"FloatContainer",
    #     "struct_id":<palworld_save_tools.archive.UUID object at 0x00000140854CCFD0>,
    #     "id":"None",
    #     "value":{
            
    #     },
    #     "type":"StructProperty"
    # },
    # "CraftSpeedRates":{
    #     "struct_type":"FloatContainer",
    #     "struct_id":<palworld_save_tools.archive.UUID object at 0x00000140854CD000>,
    #     "id":"None",
    #     "value":{
            
    #     },
    #     "type":"StructProperty"
    # },
            
    ## FOOD BUFF?
    # "FoodWithStatusEffect":{
    #     "id":"None",
    #     "value":"Pancake",
    #     "type":"NameProperty"
    # },
    # "Tiemr_FoodWithStatusEffect":{
    #     "id":"None",
    #     "value":448,
    #     "type":"IntProperty"
    # },
        
            
    # TODO ADD PAL, DEL PAL, CHANGE OWNER?

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
        if getattr(self, property_name) is None:
        # if self.Rank is None:
            self._pal_param[property_name] = PalObjects.IntProperty(rank)
        else:
            PalObjects.set_BaseType(self._pal_param[property_name], rank)

    def _set_iv(self, property_name: str, value: int):
        iv = clamp(0, 100, value)
        if getattr(self, property_name) is None:
            self._pal_param[property_name] = PalObjects.IntProperty(iv)
        else:
            PalObjects.set_BaseType(self._pal_param[property_name], iv)

    def _get_display_name(self) -> str:
        cache_key = (Config.i18n, self.DataAccessKey, self.NickName, self.IsRarePal, self.IsBOSS, self.Gender)
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
        
    def _get_passive_buff(self, buff_key: str) -> float:
        if self.PassiveSkillList is None: return 0
        bonus = 0.0
        for passive in self.PassiveSkillList:
            bonus += DataProvider.get_passive_buff(passive, buff_key)
        return bonus
    
    def _derive_hp_scaling(self) -> int:
        Level = self.Level or 1
        HP_IV = (self.Talent_HP or 0) * 0.3 / 100 # 30% of Talent
        HP_Bonus = self._get_passive_buff("b_HP") # 0
        HP_SoulBonus = (self.Rank_HP or 0) * 0.03 # 3% per incr Rank_HP
        CondenserBonus = ((self.Rank or PalRank.Rank0).value - 1) * 0.05 # 5% per incr Rank
        
        HP_No_Bonus = self.MaxHP / (1 + HP_Bonus) * (1 + HP_SoulBonus) * (1 + CondenserBonus)
        HP_Stat = (HP_No_Bonus - 500 - 5 * Level) / (.5 * Level * (1 + HP_IV))
        return HP_Stat

    def _save(self) -> None:
        # clean up and delete empty / unused entries
        # Rank_type = 0, Rank = PalRank.Rank0
        # nickname? etc
        pass