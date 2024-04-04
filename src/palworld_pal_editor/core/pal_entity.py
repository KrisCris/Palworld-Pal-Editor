import copy
import math
import re
import traceback
from typing import Optional
from palworld_save_tools.archive import UUID
from palworld_pal_editor.config import Config

from palworld_pal_editor.utils import LOGGER, clamp, DataProvider
from palworld_pal_editor.core.pal_objects import PalObjects, PalGender, PalRank, get_attr_value, get_nested_attr, toUUID
from palworld_pal_editor.utils.util import type_guard


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
        
        # self._derived_hp_scaling = self._derive_hp_scaling()
        self._display_name_cache = {}
        self.owner_player_entity = None
        ## TODO
        # self._isBoss_cache = {}
        # self._raw_specie_key_cache = {}
        # self._data_access_key_cache = {}
        self.is_unreferenced_pal = False

    def __str__(self) -> str:
        return "{} - {} - {}".format(self.DisplayName, self.OwnerName, self.InstanceId)
    
    def __hash__(self) -> int:
        return self.InstanceId.__hash__()

    def __eq__(self, __value: object) -> bool:
        return isinstance(__value, PalEntity) and self.InstanceId == __value.InstanceId
    
    def set_owner_player_entity(self, player):
        self.owner_player_entity = player

    @property
    def in_owner_palbox(self) -> bool:
        # base pal, no owner
        if not self.owner_player_entity: return True
        if  self.ContainerId == self.owner_player_entity.OtomoCharacterContainerId or \
            self.ContainerId == self.owner_player_entity.PalStorageContainerId:
            return True
        return False

    @property
    def group_id(self) -> Optional[UUID]:
        return get_nested_attr(self._pal_obj, ['value', 'RawData', 'value', 'group_id'])
    
    @group_id.setter
    def group_id(self, id: UUID | str):
        self._pal_obj['value']['RawData']['value']['group_id'] = id

    @property
    def PlayerUId(self) -> Optional[UUID]:
        # should be EMPTY UUID, but sometimes it's set to player uid in singleplayer game, weird
        return get_attr_value(self._pal_key, "PlayerUId")
    
    @PlayerUId.setter
    def PlayerUId(self, id: UUID | str) -> Optional[UUID]:
        self._pal_key["PlayerUId"] = PalObjects.Guid(id)
    
    @property
    def InstanceId(self) -> Optional[UUID]:
        return get_attr_value(self._pal_key, "InstanceId")
    
    @InstanceId.setter
    def InstanceId(self, id: UUID | str):
        self._pal_key["InstanceId"] = PalObjects.Guid(id)
    
    @property
    def OwnerPlayerUId(self) -> Optional[UUID]:
        return get_attr_value(self._pal_param, "OwnerPlayerUId")
    
    @property
    def LastOwnerPlayerUId(self) -> Optional[UUID]:
        if self.OldOwnerPlayerUIds:
            return self.OldOwnerPlayerUIds[-1]
    
    @property
    def OwnerName(self) -> str:
        from .save_manager import SaveManager
        player = SaveManager().get_player(self.OwnerPlayerUId)
        if player and player.NickName:
            return player.NickName
        return self.OwnerPlayerUId
    
    @property
    def OldOwnerPlayerUIds(self) -> Optional[list[UUID]]:
        return PalObjects.get_ArrayProperty(self._pal_param.get("OldOwnerPlayerUIds"))
    
    @property
    def SlotID(self) -> Optional[tuple[UUID, int]]:
        return PalObjects.get_PalCharacterSlotId(self._pal_param.get("SlotID"))
    
    @SlotID.setter
    def SlotID(self, slot_id: tuple[UUID | str, int]):
        self._pal_param['SlotID'] = PalObjects.PalCharacterSlotId(slot_id[1], slot_id[0])
    
    @property
    def ContainerId(self) -> Optional[UUID]:
        if (slot := self.SlotID) is None: return
        return slot[0]
    
    @property
    def SlotIndex(self) -> Optional[int]:
        if (slot := self.SlotID) is None: return
        return slot[1]
    
    @property
    def CharacterID(self) -> Optional[str]:
        return get_attr_value(self._pal_param, "CharacterID")
    
    @CharacterID.setter
    @LOGGER.change_logger('CharacterID')
    @type_guard
    def CharacterID(self, value: str) -> None:
        og_specie = self._RawSpecieKey

        if self.CharacterID is None:
            self._pal_param["CharacterID"] = PalObjects.NameProperty(value)
        else:
            PalObjects.set_BaseType(self._pal_param["CharacterID"], value)

        # Remove / Add Gender
        match self.DataAccessKey:
            case "GYM_ThunderDragonMan": self.Gender = PalGender.MALE
            case "GYM_LilyQueen": self.Gender = PalGender.FEMALE
            case "GYM_Horus": self.Gender = PalGender.MALE
            case "GYM_BlackGriffon": self.Gender = PalGender.MALE
            case "GYM_ElecPanda": self.Gender = PalGender.FEMALE
        if self.Gender and self.IsHuman:
            self.del_Gender()
        elif not self.Gender and self.IsPal:
            # well, just randomly picked lol
            self.Gender = PalGender.FEMALE

        new_specie = self._RawSpecieKey
        if new_specie != og_specie:
            self.remove_unique_attacks()

        self.learn_attacks()
        self.heal_pal()
        self.clear_worker_sick()
        # self.MaxHP = self.ComputedMaxHP
        self.HP = self.ComputedMaxHP

    @property
    def _RawSpecieKey(self) -> Optional[str]:
        key = self.CharacterID
        if self._IsBOSS:
            if "Boss_" in key:
                key = key.split("Boss_")[1]
            else:
                key = key.split("BOSS_")[1]
        if self.IsTower:
            key = key.split("GYM_")[1]
        if self.IsRAID:
            pattern = r'RAID_([A-Za-z_]+?)(?:_\d+)?$'
            match = re.search(pattern, self.CharacterID)
            if match:
                key = match.group(1)
        return key
    
    @property
    def IsRAID(self) -> bool:
        pattern = r'RAID_([A-Za-z_]+?)(?:_\d+)?$'
        match = re.search(pattern, self.CharacterID)
        if match:
            return True
        return False
    
    @property
    def IsHuman(self) -> bool:
        return DataProvider.is_pal_human(self.DataAccessKey)
            
    @property
    def IsPal(self):
        if DataProvider.get_pal_sorting_key(self.DataAccessKey) and not self.IsHuman:
            return True
        return False
    
    @property
    def HasTowerVariant(self) -> bool:
        if self.IsTower: return True
        if DataProvider.has_tower_variant_pal(self.DataAccessKey):
            return True
        return False

    @property
    def IconAccessKey(self) -> Optional[str]:
        if self.IsHuman:
            return "Human"
        if self.IsRAID:
            return self._RawSpecieKey
        return self.DataAccessKey

    @property
    def DataAccessKey(self) -> Optional[str]:
        if self.IsTower:
            return self.CharacterID
        if self.IsRAID:
            return self.CharacterID
        
        key = self._RawSpecieKey
        match key:
            case "Sheepball":
                key = "SheepBall"
            case "LazyCatFish":
                key = "LazyCatfish"
            case "Police_HandGun":
                key = "Police_Handgun"
        return key
    
    @property
    def IsInvalid(self) -> bool:
        return DataProvider.is_pal_invalid(self.DataAccessKey)
    
    @property
    def I18nName(self) -> Optional[str]:
        return DataProvider.get_pal_i18n(self.DataAccessKey)

    @property
    def DisplayName(self) -> str:
        return self._get_display_name()
    
    @property
    def PalDeckID(self) -> str:
        key = DataProvider.get_pal_sorting_key(self.DataAccessKey)
        return key if key else self.DataAccessKey
    
    @property
    def Gender(self) -> Optional[PalGender]:
        return PalGender.from_value(PalObjects.get_EnumProperty(self._pal_param.get("Gender")))
        
    @Gender.setter
    @LOGGER.change_logger('Gender')
    @type_guard
    def Gender(self, gender: PalGender | str) -> None:
        if not self.Gender and not self.IsPal:
            LOGGER.warning("This pal has no gender.")
            return
        if isinstance(gender, PalGender):
            pal_gender = gender
        else:
            pal_gender = PalGender.from_value(gender)
            if not pal_gender:
                return
        if self.Gender is None:
            self._pal_param["Gender"] = PalObjects.EnumProperty("EPalGenderType", pal_gender.value)
        else:
            PalObjects.set_EnumProperty(self._pal_param["Gender"], pal_gender.value)

    @LOGGER.change_logger('Gender')
    def del_Gender(self):
        if self.IsHuman or not self.IsPal:
            self._pal_param.pop("Gender", None)

    @property
    def IsTower(self) -> bool:
        if "GYM_" in self.CharacterID:
            return True
        return False
    
    @IsTower.setter
    @type_guard
    def IsTower(self, value: bool) -> None:
        if not value:
            self.CharacterID = self._RawSpecieKey
        else:
            self.CharacterID = f"GYM_{self._RawSpecieKey}"
        # self.MaxHP = self.ComputedMaxHP
        self.HP = self.ComputedMaxHP

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
    @type_guard
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
    @type_guard
    def IsBOSS(self, value: bool) -> None:
        # Boss and Rare can only exist one
        if self.IsRarePal and not value:
            return
        if self.IsRarePal and value:
            self.IsRarePal = False
        self._IsBOSS = value
        # Update MaxHP
        # self.MaxHP = self.ComputedMaxHP
        self.HP = self.ComputedMaxHP

    @property
    def IsRarePal(self) -> Optional[bool]:
        return get_attr_value(self._pal_param, "IsRarePal")
    
    @IsRarePal.setter
    @LOGGER.change_logger('IsRarePal')
    @type_guard
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
    @type_guard
    def NickName(self, value: str) -> None:
        if self.NickName is None:
            self._pal_param["NickName"] = PalObjects.StrProperty(value)
        else:
            self._pal_param["NickName"]["value"] = value
        # clear up
        if not self.NickName:
            self._pal_param.pop("NickName", None)

    @property
    def Level(self) -> Optional[int]:
        return get_attr_value(self._pal_param, "Level")
    
    @Level.setter
    @LOGGER.change_logger('Level')
    @type_guard
    def Level(self, value: int) -> None:
        value = clamp(1, 50, value)
        if self.Level is None:
            self._pal_param["Level"] = PalObjects.IntProperty(value)
        else:
            self._pal_param["Level"]["value"] = value
        self.Exp = DataProvider.get_level_xp(self.Level)
        # Update MaxHP
        # self.MaxHP = self.ComputedMaxHP
        self.HP = self.ComputedMaxHP
        # Learn Attacks
        self.learn_attacks()

    @property
    def Exp(self) -> Optional[int]:
        return get_attr_value(self._pal_param, "Exp")
    
    @Exp.setter
    @LOGGER.change_logger('Exp')
    @type_guard
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
    @type_guard
    def Rank(self, rank: PalRank | int) -> None:
        if isinstance(rank, PalRank):
            pal_rank = rank
        else:
            pal_rank = PalRank.from_value(rank)
            if not pal_rank:
                LOGGER.warning(f"Invalid rank value {rank}")
                return

        if self.Rank is None:
            self._pal_param["Rank"] = PalObjects.IntProperty(pal_rank.value)
        else:
            PalObjects.set_BaseType(self._pal_param["Rank"], pal_rank.value)

        # self.MaxHP = self.ComputedMaxHP
        self.HP = self.ComputedMaxHP

        if self.Rank == PalRank.Rank0:
            self._pal_param.pop("Rank", None)

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
    @type_guard
    def Rank_HP(self, rank: int) -> None:
        self._set_soul_rank('Rank_HP', rank)
        # self.MaxHP = self.ComputedMaxHP
        self.HP = self.ComputedMaxHP

    @Rank_Attack.setter
    @LOGGER.change_logger('Rank_Attack')
    @type_guard
    def Rank_Attack(self, rank: int) -> None:
        self._set_soul_rank('Rank_Attack', rank)

    @Rank_Defence.setter
    @LOGGER.change_logger('Rank_Defence')
    @type_guard
    def Rank_Defence(self, rank: int) -> None:
        self._set_soul_rank('Rank_Defence', rank)

    @Rank_CraftSpeed.setter
    @LOGGER.change_logger('Rank_CraftSpeed')
    @type_guard
    def Rank_CraftSpeed(self, rank: int) -> None:
        self._set_soul_rank('Rank_CraftSpeed', rank)

    @property
    def ComputedMaxHP(self) -> int:
        """
        Credit to https://www.reddit.com/r/Palworld/comments/1afyau4/pal_stat_mechanics_hidden_ivs_levelup_stats_and/
        """
        Level = self.Level or 1
        HP_Stat = DataProvider.get_pal_scaling(self.DataAccessKey, "HP", self.IsBOSS)
        if HP_Stat is None:
            return None
        HP_IV = (self.Talent_HP or 0) * 0.3 / 100 # 30% of Talent
        HP_Bonus = self._get_passive_buff("b_HP") # 0
        HP_SoulBonus = (self.Rank_HP or 0) * 0.03 # 3% per incr Rank_HP
        CondenserBonus = ((self.Rank or PalRank.Rank0).value - 1) * 0.05 # 5% per incr Rank

        # slightly off but not a big deal i suppose
        return math.floor(math.floor(500 + 5 * Level + HP_Stat * .5 * Level * (1 + HP_IV)) \
            * (1 + HP_Bonus) * (1 + HP_SoulBonus) * (1 + CondenserBonus)) * 1000

    @property
    def ComputedAttack(self) -> Optional[int]:
        Level = self.Level or 1
        Attack_Stat = DataProvider.get_pal_scaling(self.DataAccessKey, "ATK", self.IsBOSS)
        if Attack_Stat is None:
            return None
        Attack_IV = (self.Talent_Shot or 0) * 0.3 / 100 # 30% of Talent
        Attack_Bonus = self._get_passive_buff("b_Attack")
        Attack_SoulBonus = (self.Rank_Attack or 0) * 0.03 # 3% per incr Rank_HP
        CondenserBonus = ((self.Rank or PalRank.Rank0).value - 1) * 0.05 # 5% per incr Rank

        # slightly off when soul / condenser bonus presents...
        base_attack = math.floor(math.floor(100 + Attack_Stat * 0.075 * Level * (1 + Attack_IV)) * (1 + Attack_SoulBonus) * (1 + CondenserBonus))
        return math.floor(base_attack * (1 + Attack_Bonus))
        # return math.floor(math.floor(100 + Attack_Stat * .075 * Level * (1 + Attack_IV)) \
        #     * (1 + Attack_Bonus) * (1 + Attack_SoulBonus) * (1 + CondenserBonus))
    
    @property
    def ComputedDefense(self) -> Optional[int]:
        Level = self.Level or 1
        Defense_Stat = DataProvider.get_pal_scaling(self.DataAccessKey, "DEF", self.IsBOSS)
        if Defense_Stat is None:
            return None
        Defense_IV = (self.Talent_Defense or 0) * 0.3 / 100 # 30% of Talent
        Defense_Bonus = self._get_passive_buff("b_Defense")
        Defense_SoulBonus = (self.Rank_Defence or 0) * 0.03 # 3% per incr Rank_HP
        CondenserBonus = ((self.Rank or PalRank.Rank0).value - 1) * 0.05 # 5% per incr Rank

        # TODO it works fine without the condenser and soul bonus, need to figure out what was wrong
        base_defense = math.floor(math.floor(50 + math.ceil(Defense_Stat * 0.075 * Level) * (1 + Defense_IV)) * (1 + Defense_SoulBonus) * (1 + CondenserBonus))
        return math.floor(base_defense * (1 + Defense_Bonus))
        # return math.floor(math.floor(50 + Defense_Stat * 0.075 * Level * (1 + Defense_IV))
        #     * (1 + Defense_Bonus)  * (1 + Defense_SoulBonus) * (1 + CondenserBonus))

    @property
    def ComputedCraftSpeed(self) -> Optional[int]:
        Base_CraftSpeed = self.CraftSpeed
        if self.CraftSpeed is None: return None
        CraftSpeed_SoulBonus = (self.Rank_CraftSpeed or 0) * 0.03 # 3% per incr Rank_HP
        Defense_Bonus = self._get_passive_buff("b_CraftSpeed")
        return math.floor(math.floor(Base_CraftSpeed * (1 + CraftSpeed_SoulBonus)) * (1 + Defense_Bonus))


    @property
    def HP(self) -> Optional[int]:
        return PalObjects.get_FixedPoint64(self._pal_param.get("HP"))
    
    @HP.setter
    @LOGGER.change_logger('HP')
    @type_guard
    def HP(self, value: int) -> None:
        if self.HP is None:
            self._pal_param["HP"] = PalObjects.FixedPoint64(value)
        else:
            PalObjects.set_FixedPoint64(self._pal_param["HP"], value)

    # @property
    # def MaxHP(self) -> Optional[int]:
    #     return PalObjects.get_FixedPoint64(self._pal_param.get("MaxHP"))
    
    # @MaxHP.setter
    # @LOGGER.change_logger("MaxHP")
    # def MaxHP(self, val: int) -> None:
    #     if self.MaxHP is None:
    #         self._pal_param["MaxHP"] = PalObjects.FixedPoint64(val)
    #     else:
    #         PalObjects.set_FixedPoint64(self._pal_param["MaxHP"], val)

    #     self.HP = self.MaxHP

    @property
    def PassiveSkillList(self) -> Optional[list[str]]:
        return PalObjects.get_ArrayProperty(self._pal_param.get("PassiveSkillList"))

    @LOGGER.change_logger('PassiveSkillList')
    @type_guard
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
        LOGGER.info(f"Added {DataProvider.get_passive_i18n(skill)[0]} to PassiveSkillList")
        # Update MaxHP, but no such skill atm.
        # self.MaxHP = self.ComputedMaxHP
        # self.HP = self.ComputedMaxHP
        return True
    
    @LOGGER.change_logger('PassiveSkillList')
    def pop_PassiveSkillList(self, idx: int = None, item: str = None) -> Optional[str]:
        try:
            if item is not None:
                idx = self.PassiveSkillList.index(item)
            skill = self.PassiveSkillList.pop(int(idx))
            LOGGER.info(f"Removed {DataProvider.get_passive_i18n(skill)[0]} from PassiveSkillList")
            # Update MaxHP, but no such skill atm.
            # self.MaxHP = self.ComputedMaxHP
            return skill
        except Exception as e:
            LOGGER.warning(f"{e}")

    @property
    def EquipWaza(self) -> Optional[list[str]]:
        return PalObjects.get_ArrayProperty(self._pal_param.get("EquipWaza"))

    @LOGGER.change_logger('EquipWaza')
    @type_guard
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

        if waza not in (self.MasteredWaza or []):
            self.add_MasteredWaza(waza)

        LOGGER.info(f"Added {DataProvider.get_attack_i18n(waza)[0]} to EquipWaza")
        return True
    
    @LOGGER.change_logger('EquipWaza')
    def pop_EquipWaza(self, idx: int = None, item: str = None) -> Optional[str]:
        try:
            if item is not None:
                idx = self.EquipWaza.index(item)
            waza = self.EquipWaza.pop(int(idx))
            LOGGER.info(f"Removed {DataProvider.get_attack_i18n(waza)[0]} from EquipWaza")
            return waza
        except Exception as e:
            LOGGER.warning(f"{e}")

    @property
    def num_EquipWaza(self) -> int:
        return len(self.EquipWaza or [])
    
    @property
    def num_EmptyEquipWaza(self) -> int:
        return 3 - self.num_EquipWaza

    @property
    def MasteredWaza(self) -> Optional[list[str]]:
        return PalObjects.get_ArrayProperty(self._pal_param.get("MasteredWaza"))

    # @property
    # def MasteredWazaSet(self) -> Optional[set[str]]:
    #     # Unused
    #     # We need a way to cache it, otherwise it's no better than idx into a list
    #     return set(self.MasteredWaza) if self.MasteredWaza is not None else None

    @LOGGER.change_logger('MasteredWaza')
    @type_guard
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
        LOGGER.info(f"Added {DataProvider.get_attack_i18n(waza)[0]} to MasteredWaza")
        
        # if self.num_EmptyEquipWaza > 0:
        #     self.add_EquipWaza(waza)
        return True

    @LOGGER.change_logger('MasteredWaza')
    @type_guard
    def pop_MasteredWaza(self, idx: int = None, item: str = None) -> Optional[str]:
        try:
            if item is not None:
                idx = self.MasteredWaza.index(item)
            waza = self.MasteredWaza.pop(int(idx))
            if waza in (self.EquipWaza or []):
                self.pop_EquipWaza(item=waza)
            # return PalObjects.pop_ArrayProperty(self._pal_param["MasteredWaza"], idx)
            LOGGER.info(f"Removed {DataProvider.get_attack_i18n(waza)[0]} from MasteredWaza")
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
    @type_guard
    def Talent_HP(self, value: int):
        self._set_iv("Talent_HP", value)
        # self.MaxHP = self.ComputedMaxHP
        self.HP = self.ComputedMaxHP

    @Talent_Melee.setter
    @LOGGER.change_logger("Talent_Melee")
    @type_guard
    def Talent_Melee(self, value: int):
        self._set_iv("Talent_Melee", value)

    @Talent_Shot.setter
    @LOGGER.change_logger("Talent_Shot")
    @type_guard
    def Talent_Shot(self, value: int):
        self._set_iv("Talent_Shot", value)

    @Talent_Defense.setter
    @LOGGER.change_logger("Talent_Defense")
    @type_guard
    def Talent_Defense(self, value: int):
        self._set_iv("Talent_Defense", value)
    
    @property
    def CraftSpeed(self) -> Optional[int]:
        return PalObjects.get_BaseType(self._pal_param.get("CraftSpeed"))
            
    @property
    def SanityValue(self) -> Optional[float]:
        return PalObjects.get_BaseType(self._pal_param.get("SanityValue"))
    
    @SanityValue.setter
    @LOGGER.change_logger("SanityValue")
    @type_guard
    def SanityValue(self, val: float):
        if self.SanityValue is None:
            self._pal_param["SanityValue"] = PalObjects.FloatProperty(val)
        else:
            PalObjects.set_BaseType(self._pal_param.get("SanityValue"), val)
    
    @property
    def MaxFullStomach(self) -> Optional[float]:
        return PalObjects.get_BaseType(self._pal_param.get("MaxFullStomach"))
    
    @property
    def FullStomach(self) -> Optional[float]:
        return PalObjects.get_BaseType(self._pal_param.get("FullStomach"))
    
    @FullStomach.setter
    @LOGGER.change_logger("FullStomach")
    @type_guard
    def FullStomach(self, val: float):
        if self.FullStomach is None:
            self._pal_param["HP"] = PalObjects.FloatProperty(val)
        else:
            PalObjects.set_BaseType(self._pal_param['FullStomach'], val)
            
    @property
    def WorkerSick(self) -> Optional[str]:
        """
        I thought this would be ArrayProperty...
        ```json
        "WorkerSick":{
            "id":"None",
            "value":{
                "type":"EPalBaseCampWorkerSickType",
                "value":"EPalBaseCampWorkerSickType::DepressionSprain"
            },
            "type":"EnumProperty"
        },
        ```
        """
        return PalObjects.get_EnumProperty(self._pal_param.get("WorkerSick"))
    
    @property
    def HasWorkerSick(self) -> bool:
        return self.WorkerSick is not None
    
    @property
    def PalReviveTimer(self) -> Optional[float]:
        """
        ```json
        "PalReviveTimer":{
            "id":"None",
            "value":22.99822425842285,
            "type":"FloatProperty"
        }
        ```
        """
        return PalObjects.get_BaseType(self._pal_param.get("PalReviveTimer"))
    
    # @PalReviveTimer.setter
    # @LOGGER.change_logger("PalReviveTimer")
    # def PalReviveTimer(self, val: float) -> Optional[float]:
    #     if self.PalReviveTimer is None:
    #         return
    #     PalObjects.set_BaseType(self._pal_param.get("PalReviveTimer"), val)
    
    @property
    def PhysicalHealth(self) -> Optional[str]:
        """
        ```json
        "PhysicalHealth":{
            "id":"None",
            "value":{
                "type":"EPalStatusPhysicalHealthType",
                "value":"EPalStatusPhysicalHealthType::Dying"
            },
            "type":"EnumProperty"
        },
        ```
        """
        return PalObjects.get_EnumProperty(self._pal_param.get("PhysicalHealth"))
    
    @property
    def IsFaintedPal(self) -> bool:
        if self.PalReviveTimer or self.PhysicalHealth == "EPalStatusPhysicalHealthType::Dying":
            return True
        return False

    @LOGGER.change_logger("PhysicalHealth")
    def heal_pal(self):
        if self.IsFaintedPal:
            self._pal_param.pop("PalReviveTimer", None)
        if self.PhysicalHealth == "EPalStatusPhysicalHealthType::Dying":
            self._pal_param.pop("PhysicalHealth", None)
        # if not self.MaxHP:
        #     self.MaxHP = self.ComputedMaxHP
        self.HP = self.ComputedMaxHP            

    @property
    def FoodWithStatusEffect(self) -> Optional[str]:
        return PalObjects.get_BaseType(self._pal_param.get("FoodWithStatusEffect"))
    
    @property
    def Timer_FoodWithStatusEffect(self) -> Optional[int]:
        """
        Tiemr_FoodWithStatusEffect is NOT a typo. This is how it coded in the save.
        ```json
        "Tiemr_FoodWithStatusEffect":{
            "id":"None",
            "value":448,
            "type":"IntProperty"
        },
        ```
        """
        return PalObjects.get_BaseType(self._pal_param.get("Tiemr_FoodWithStatusEffect"))

    @Timer_FoodWithStatusEffect.setter
    @LOGGER.change_logger("Timer_FoodWithStatusEffect")
    @type_guard
    def Timer_FoodWithStatusEffect(self, val: int) -> bool:
        if self.FoodWithStatusEffect is None or self.Timer_FoodWithStatusEffect is None:
            LOGGER.warning("Trying to set food effect timer when there is no food eaten.")
            return False
        PalObjects.set_BaseType(self._pal_param['Tiemr_FoodWithStatusEffect'], val)
        
    def learn_attacks(self):
        for atk in DataProvider.get_attacks_to_learn(self.DataAccessKey, self.Level or 1):
            if atk not in (self.MasteredWaza or []):
                self.add_MasteredWaza(atk)
        # for atk in DataProvider.get_attacks_to_forget(self.DataAccessKey, self.Level):
        #     if atk in self.MasteredWaza:
        #         self.pop_MasteredWaza(atk)
                
    def remove_unique_attacks(self):
        if self.MasteredWaza is None:
            return
        atks = self.MasteredWaza.copy()
        if not atks: return
        for atk in atks:
            if DataProvider.is_unique_attacks(atk):
                self.pop_MasteredWaza(item=atk)

    @LOGGER.change_logger("WorkerSick")
    def clear_worker_sick(self):
        self._pal_param.pop("WorkerSick", None)
        if self.MaxFullStomach:
            self.FullStomach = self.MaxFullStomach
        self.SanityValue = 100.0

    def max_lv_exp(self):
        exp = DataProvider.get_level_xp(self.Level)
        if isinstance(exp, int):
            self.Exp = exp - 1

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

    def print_obj(self):
        print(self.dump_obj())

    def dump_obj(self) -> str:
        return str(self._pal_obj)

    def _set_soul_rank(self, property_name: str, rank: int):
        rank = clamp(0, 10, rank)
        if getattr(self, property_name) is None:
            self._pal_param[property_name] = PalObjects.IntProperty(rank)
        else:
            PalObjects.set_BaseType(self._pal_param[property_name], rank)

        if getattr(self, property_name) == 0:
            self._pal_param.pop(property_name, None)

    def _set_iv(self, property_name: str, value: int):
        iv = clamp(0, 100, value)
        if getattr(self, property_name) is None:
            self._pal_param[property_name] = PalObjects.IntProperty(iv)
        else:
            PalObjects.set_BaseType(self._pal_param[property_name], iv)

    def _get_display_name(self) -> str:
        cache_key = (Config.i18n, self.DataAccessKey, self.NickName, self.IsRarePal, self.IsBOSS, self.IsTower, self.Gender)
        try:
            return self._display_name_cache[cache_key]
        except KeyError:
            species_name = self.I18nName or self.DataAccessKey
            rare_prefix = "✨" if self.IsRarePal else ""
            boss_prefix = "💀" if self.IsBOSS else ""
            tower_prefix = "🗼" if self.IsTower else ""
            nickname_suffix = f" ({self.NickName})" if self.NickName else ""

            gender_suffix = ""
            if self.Gender == PalGender.FEMALE:
                gender_suffix = "♀"
            elif self.Gender == PalGender.MALE:
                gender_suffix = "♂"

            name = f"{rare_prefix}{boss_prefix}{tower_prefix}{species_name}{nickname_suffix}{gender_suffix}"
            self._display_name_cache[cache_key] = name
            return name
        
    def _get_passive_buff(self, buff_key: str) -> float:
        if self.PassiveSkillList is None: return 0
        bonus = 0.0
        for passive in (self.PassiveSkillList or []):
            bonus += DataProvider.get_passive_buff(passive, buff_key)
        return bonus
    

    # Deprecated
    # def _derive_hp_scaling(self) -> int:
    #     try:
    #         def adjust_number(n):
    #             last_digit = n % 5
    #             if last_digit < 3:
    #                 return n - last_digit
    #             else:
    #                 return n - last_digit + 5

    #         Level = self.Level or 1
    #         HP_IV = (self.Talent_HP or 0) * 0.3 / 100 # 30% of Talent
    #         HP_Bonus = self._get_passive_buff("b_HP") # 0
    #         HP_SoulBonus = (self.Rank_HP or 0) * 0.03 # 3% per incr Rank_HP
    #         CondenserBonus = ((self.Rank or PalRank.Rank0).value - 1) * 0.05 # 5% per incr Rank
            
    #         HP_No_Bonus = math.ceil(self.MaxHP / 1000 / ((1 + HP_Bonus) * (1 + HP_SoulBonus) * (1 + CondenserBonus)))
    #         HP_Stat = math.ceil((HP_No_Bonus - 500 - 5 * Level) / (.5 * Level * (1 + HP_IV)))
    #         return adjust_number(HP_Stat)
    #     except:
    #         LOGGER.error(traceback.format_exc())


    # TODO Guess empty value is good?
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