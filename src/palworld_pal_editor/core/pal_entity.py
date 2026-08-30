import math
from typing import Optional
from palworld_save_tools.archive import UUID
from palworld_pal_editor.config import Config

from palworld_pal_editor.utils import LOGGER, clamp, DataProvider
from palworld_pal_editor.core.pal_objects import (
    PalObjects,
    PalGender,
    PalSuitability,
    dumps,
    toUUID,
)
from palworld_pal_editor.utils.util import type_guard

MAX_WORK_SUITABILITY = 10


def condensation_work_suitability_bonus(
    base_suitabilities: dict[str, int], rank: int, best_work_suitability: Optional[str]
) -> dict[str, int]:
    """Return the derived 1.0 condensation bonus for each existing work type."""
    base = {key: value for key, value in base_suitabilities.items() if value > 0}
    bonus = {key: 0 for key in base}
    if best_work_suitability == "EPalWorkSuitability::None":
        best_work_suitability = None
    if not base:
        return bonus

    current = base.copy()
    order = tuple(
        suit.value
        for suit in PalSuitability
        if suit is not PalSuitability.OilExtraction
    )

    def nth_highest(n: int) -> Optional[str]:
        values = sorted(set(current.values()), reverse=True)
        if n >= len(values):
            return None
        return next((key for key in order if current.get(key) == values[n]), None)

    for step in range(1, min(rank - 1, 4) + 1):
        if step == 4:
            for key in base:
                bonus[key] += 1
                current[key] += 1
            continue

        if len(current) == 1:
            target = next(iter(current))
        elif step == 1:
            target = best_work_suitability
        elif step == 2:
            target = nth_highest(1) or best_work_suitability
        elif len(current) == 2:
            target = best_work_suitability
        else:
            target = nth_highest(2) or nth_highest(1) or best_work_suitability

        if target is not None:
            if target in bonus:
                bonus[target] += 1
            current[target] = current.get(target, 0) + 1

    return bonus


class PalEntity:
    MAX_LEVEL = 80
    MAX_INVALID_LEVEL = 100
    MAX_FRIENDSHIP_LEVEL = 10
    MAX_CONDENSATION_RANK = 5
    MAX_SOUL_RANK = 20
    MAX_TALENT = 100

    def __init__(self, pal_key: dict, save_parameter_owner: dict) -> None:
        # The two stable parent dicts, handed over by the storage adapter that found
        # them in its own native format: the identity struct's value, and the dict
        # that owns the SaveParameter property. Everything else is read through them
        # on demand so that replacing a whole native property (e.g. overwriting
        # SaveParameter from another source) stays visible to this entity.
        self._pal_key: dict = pal_key
        self._save_parameter_owner: dict = save_parameter_owner

        if self.save_parameter["struct_type"] != "PalIndividualCharacterSaveParameter":
            raise Exception(
                f"{dumps(save_parameter_owner)}'s save param is not "
                "PalIndividualCharacterSaveParameter"
            )

        if self.InstanceId is None:
            raise Exception(f"No GUID, skipping {self}")

        if self.CharacterID is None:
            raise Exception(f"No CharacterID, skipping {dumps(save_parameter_owner)}")

        if PalObjects.get_BaseType(self.pal_param.get("IsPlayer")):
            raise TypeError(
                "Expecting pal_obj, received player_obj: {} - {} - {}".format(
                    self.NickName, self.PlayerUId, self.InstanceId
                )
            )

        self._display_name_cache = {}

    def __str__(self) -> str:
        return f"{self.DisplayName} - {self.InstanceId}"

    @property
    def save_parameter(self) -> dict:
        """The whole native SaveParameter property, read live from its parent."""
        return self._save_parameter_owner["SaveParameter"]

    @property
    def pal_param(self) -> dict:
        """The SaveParameter value dict — the Pal's own native fields."""
        return self._save_parameter_owner["SaveParameter"]["value"]

    def _set_key_guid(self, field: str, id: UUID | str) -> None:
        """Write a Guid on the outer identity key in place.

        Replacing the whole property dict would detach any native reference the
        save file already holds to it, so an existing property is mutated and
        only a missing one is built from the factory.
        """
        existing = self._pal_key.get(field)
        if existing is None:
            self._pal_key[field] = PalObjects.Guid(id)
        else:
            PalObjects.set_BaseType(existing, toUUID(str(id)))

    def reset_display_name_cache(self) -> None:
        """Forget the cached display names after the payload is replaced wholesale.

        Every other edit goes through a setter that knows what it invalidated; an
        overwrite swaps the whole `SaveParameter` value at once and cannot.
        """
        self._display_name_cache = {}

    @property
    def PlayerUId(self) -> Optional[UUID]:
        # should be EMPTY UUID, but sometimes it's set to player uid in singleplayer game, weird
        return PalObjects.get_BaseType(self._pal_key.get("PlayerUId"))

    @PlayerUId.setter
    def PlayerUId(self, id: UUID | str) -> Optional[UUID]:
        self._set_key_guid("PlayerUId", id)

    @property
    def InstanceId(self) -> Optional[UUID]:
        return PalObjects.get_BaseType(self._pal_key.get("InstanceId"))

    @InstanceId.setter
    def InstanceId(self, id: UUID | str):
        self._set_key_guid("InstanceId", id)

    @property
    def OwnerPlayerUId(self) -> Optional[UUID]:
        return PalObjects.get_BaseType(self.pal_param.get("OwnerPlayerUId"))

    @property
    def LastOwnerPlayerUId(self) -> Optional[UUID]:
        if self.OldOwnerPlayerUIds:
            return self.OldOwnerPlayerUIds[-1]

    @property
    def OwnerName(self) -> Optional[str]:
        from .save_manager import SaveManager

        player = SaveManager().get_player(self.OwnerPlayerUId)
        if player and player.NickName:
            return player.NickName
        return str(self.OwnerPlayerUId) if self.OwnerPlayerUId else None

    @property
    def OldOwnerPlayerUIds(self) -> Optional[list[UUID]]:
        return PalObjects.get_ArrayProperty(self.pal_param.get("OldOwnerPlayerUIds"))

    @property
    def SlotId(self) -> Optional[tuple[UUID, int]]:
        return PalObjects.get_PalCharacterSlotId(self.pal_param.get("SlotId"))

    @SlotId.setter
    @LOGGER.change_logger("SlotId")
    def SlotId(self, slot_id: tuple[UUID | str, int]):
        self.pal_param["SlotId"] = PalObjects.PalCharacterSlotId(
            slot_id[1], slot_id[0]
        )

    @property
    def ContainerId(self) -> Optional[UUID]:
        if (slot := self.SlotId) is None:
            return
        return slot[0]

    @property
    def SlotIndex(self) -> Optional[int]:
        if (slot := self.SlotId) is None:
            return
        return slot[1]

    @property
    def CharacterID(self) -> Optional[str]:
        return PalObjects.get_BaseType(self.pal_param.get("CharacterID"))

    @CharacterID.setter
    @LOGGER.change_logger("CharacterID")
    @type_guard
    def CharacterID(self, value: str) -> None:
        og_specie = self.RawSpecieKey

        if self.CharacterID is None:
            self.pal_param["CharacterID"] = PalObjects.NameProperty(value)
        else:
            PalObjects.set_BaseType(self.pal_param["CharacterID"], value)

        self.update_UniqueNPCID()
        if DataProvider.get_pal_variant_kind(self.CharacterID) not in (
            "alpha",
            "boss",
        ):
            self._set_rare_flag(False)

        # Remove / Add Gender
        if self.IsTower:
            match self.RawSpecieKey:
                case "ThunderDragonMan":
                    self.Gender = PalGender.MALE
                case "LilyQueen":
                    self.Gender = PalGender.FEMALE
                case "Horus":
                    self.Gender = PalGender.MALE
                case "BlackGriffon":
                    self.Gender = PalGender.MALE
                case "ElecPanda":
                    self.Gender = PalGender.FEMALE
                case "MoonQueen":
                    self.Gender = PalGender.FEMALE
                case "SnowTigerBeastman":
                    self.Gender = PalGender.MALE

        if self.Gender and (self.IsHuman or self.IsOtomoTower):
            self.del_Gender()

        if not self.Gender and not (self.IsHuman or self.IsOtomoTower):
            # well, just randomly picked lol
            self.Gender = PalGender.FEMALE

        new_specie = self.RawSpecieKey
        if new_specie != og_specie:
            self.SkinName = None
            # Unset invalid movesets
            self.remove_unique_attacks()
            # Unset invalid work suitabilities
            if self.AddedWorkSuitabilities:
                new_suits = DataProvider.get_pal_suitabilities(self.DataAccessKey)
                new_bonus = condensation_work_suitability_bonus(
                    new_suits or {},
                    self.Rank or 1,
                    DataProvider.get_pal_best_work_suitability(self.DataAccessKey),
                )
                for suit, rank in self.AddedWorkSuitabilities.items():
                    if new_suits is None or new_suits[suit.value] == 0:
                        self.set_WorkSuitability(suit, 0)
                    elif (
                        rank + new_suits[suit.value] + new_bonus.get(suit.value, 0)
                        > MAX_WORK_SUITABILITY
                    ):
                        self.set_WorkSuitability(suit, MAX_WORK_SUITABILITY)

        self.learn_attacks()
        if self.IsTower or self.IsRAID or self.IsPREDATOR:
            self.equip_all_pal_attacks()

        self.heal_pal()
        # self.clear_worker_sick()
        if maxHP := self.ComputedMaxHP:
            self.Hp = maxHP

    @property
    def RawSpecieKey(self) -> Optional[str]:
        return DataProvider.get_pal_family_id(self.CharacterID)

    @property
    def IsSUMMON(self) -> bool:
        return "summon" in DataProvider.get_pal_variant_tags(self.CharacterID)

    @property
    def IsOilrig(self) -> bool:
        return "oilrig" in DataProvider.get_pal_variant_tags(self.CharacterID)

    @property
    def IsExpeditionPal(self) -> bool:
        expedition_id = PalObjects.get_BaseType(
            self.pal_param.get("MapObjectConcreteInstanceIdAssignedToExpedition")
        )
        return expedition_id not in (None, PalObjects.EMPTY_UUID)

    @property
    def IsRAID(self) -> bool:
        return "raid" in DataProvider.get_pal_variant_tags(self.CharacterID)

    @property
    def IsPREDATOR(self) -> bool:
        return "predator" in DataProvider.get_pal_variant_tags(self.CharacterID)

    @property
    def IsHuman(self) -> bool:
        return DataProvider.is_pal_human(self.CharacterID) or False

    @property
    def HasBaseVariant(self) -> bool:
        return any(
            "base" in DataProvider.get_pal_variant_tags(variant)
            for variant in DataProvider.get_family_variants(self.CharacterID)
        )

    @property
    def HasBossVariant(self) -> bool:
        return any(
            "boss" in DataProvider.get_pal_variant_tags(variant)
            for variant in DataProvider.get_family_variants(self.CharacterID)
        )

    @property
    def HasTowerVariant(self) -> bool:
        return any(
            "tower" in DataProvider.get_pal_variant_tags(variant)
            for variant in DataProvider.get_family_variants(self.CharacterID)
        )

    @property
    def HasRaidVariant(self) -> bool:
        return any(
            "raid" in DataProvider.get_pal_variant_tags(variant)
            for variant in DataProvider.get_family_variants(self.CharacterID)
        )

    @property
    def HasPredatorVariant(self) -> bool:
        return any(
            "predator" in DataProvider.get_pal_variant_tags(variant)
            for variant in DataProvider.get_family_variants(self.CharacterID)
        )

    @property
    def IconAccessKey(self) -> Optional[str]:
        if self.SkinName:
            return f"skin-{self.SkinName}"
        return DataProvider.get_pal_icon_key(self.CharacterID)

    @property
    def DataAccessKey(self) -> Optional[str]:
        return DataProvider.resolve_pal_key(self.CharacterID)

    @property
    def IsFavoritePal(self) -> Optional[bool]:
        return PalObjects.get_BaseType(self.pal_param.get("IsFavoritePal"))

    @IsFavoritePal.setter
    @LOGGER.change_logger("IsFavoritePal")
    @type_guard
    def IsFavoritePal(self, value: bool) -> None:
        if self.IsFavoritePal is None:
            self.pal_param["IsFavoritePal"] = PalObjects.BoolProperty(value)
        else:
            PalObjects.set_BaseType(self.pal_param["IsFavoritePal"], value)

    @property
    def FavoriteIndex(self) -> int:
        favorite = self.pal_param.get("FavoriteIndex")
        value = PalObjects.get_ByteProperty(favorite)
        if value is None:
            value = PalObjects.get_BaseType(favorite)
        return value if isinstance(value, int) else 0

    @FavoriteIndex.setter
    @LOGGER.change_logger("FavoriteIndex")
    @type_guard
    def FavoriteIndex(self, value: int) -> None:
        if isinstance(value, bool) or not 0 <= value <= 3:
            raise ValueError("FavoriteIndex must be an integer from 0 to 3")
        favorite = self.pal_param.get("FavoriteIndex")
        if favorite is None:
            self.pal_param["FavoriteIndex"] = PalObjects.ByteProperty(value)
        elif favorite.get("type") == "ByteProperty":
            PalObjects.set_ByteProperty(favorite, value)
        else:
            PalObjects.set_BaseType(favorite, value)

    @property
    def IsImportedCharacter(self) -> bool:
        """Whether the game marks this Pal as imported from Global Pal Storage."""
        return bool(
            PalObjects.get_BaseType(self.pal_param.get("bImportedCharacter"))
        )

    @IsImportedCharacter.setter
    @LOGGER.change_logger("IsImportedCharacter")
    @type_guard
    def IsImportedCharacter(self, value: bool) -> None:
        if value:
            self.pal_param["bImportedCharacter"] = PalObjects.BoolProperty(True)
        else:
            self.pal_param.pop("bImportedCharacter", None)

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
        return PalGender.from_value(
            PalObjects.get_EnumProperty(self.pal_param.get("Gender"))
        )

    @Gender.setter
    @LOGGER.change_logger("Gender")
    @type_guard
    def Gender(self, gender: PalGender | str) -> None:
        if gender == "NONE":
            self.pal_param.pop("Gender", None)
        if self.IsHuman or self.IsOtomoTower:
            LOGGER.warning(f"Pal {self.CharacterID} has no gender by default!!")
            # return
        if isinstance(gender, PalGender):
            pal_gender = gender
        else:
            pal_gender = PalGender.from_value(gender)
            if not pal_gender:
                return
        if self.Gender is None:
            self.pal_param["Gender"] = PalObjects.EnumProperty(
                "EPalGenderType", pal_gender.value
            )
        else:
            PalObjects.set_EnumProperty(self.pal_param["Gender"], pal_gender.value)

    @LOGGER.change_logger("Gender")
    def del_Gender(self):
        if self.IsHuman or self.IsOtomoTower:
            self.pal_param.pop("Gender", None)
            return
        LOGGER.info("Only human or otomo tower can have no gender.")

    @property
    def IsTower(self) -> bool:
        return "tower" in DataProvider.get_pal_variant_tags(self.CharacterID)

    @property
    def IsOtomoTower(self) -> bool:
        tags = DataProvider.get_pal_variant_tags(self.CharacterID)
        return "tower" in tags and "otomo" in tags

    @IsTower.setter
    @type_guard
    def IsTower(self, value: bool) -> None:
        variant = DataProvider.get_pal_variant(
            self.CharacterID, "tower" if value else "base"
        )
        if variant is not None:
            self.CharacterID = variant
        if maxHP := self.ComputedMaxHP:
            self.Hp = maxHP

    @property
    def _IsBOSS(self) -> bool:
        return "boss" in DataProvider.get_pal_variant_tags(self.CharacterID)

    @_IsBOSS.setter
    @LOGGER.change_logger("_IsBOSS")
    @type_guard
    def _IsBOSS(self, value: bool) -> None:
        if value:
            variant = DataProvider.get_pal_variant(
                self.CharacterID, "alpha"
            ) or DataProvider.get_pal_variant(self.CharacterID, "boss")
        else:
            variant = DataProvider.get_pal_variant(self.CharacterID, "base")
        if variant is not None:
            self.CharacterID = variant

    @property
    def IsBOSS(self) -> bool:
        """
        Check if the pal is diaplayed as BOSS in game.
        """
        if self.IsRarePal:
            return False
        return self._IsBOSS

    @IsBOSS.setter
    @LOGGER.change_logger("IsBOSS")
    @type_guard
    def IsBOSS(self, value: bool) -> None:
        # Boss and Rare can only exist one
        if self.IsRarePal and not value:
            return
        if self.IsRarePal and value:
            self.IsRarePal = False
        self._IsBOSS = value

        if maxHP := self.ComputedMaxHP:
            self.Hp = maxHP

    @property
    def IsRarePal(self) -> Optional[bool]:
        return PalObjects.get_BaseType(self.pal_param.get("IsRarePal"))

    def _set_rare_flag(self, value: bool) -> None:
        if self.IsRarePal is None:
            self.pal_param["IsRarePal"] = PalObjects.BoolProperty(value)
        else:
            PalObjects.set_BaseType(self.pal_param["IsRarePal"], value)

    @IsRarePal.setter
    @LOGGER.change_logger("IsRarePal")
    @type_guard
    def IsRarePal(self, value: bool) -> None:
        # Boss and Rare can only exist one
        if self.IsBOSS and not value:
            return

        kind = DataProvider.get_pal_variant_kind(self.CharacterID)
        if value and kind not in ("alpha", "boss"):
            variant = DataProvider.get_pal_variant(
                self.CharacterID, "alpha"
            ) or DataProvider.get_pal_variant(self.CharacterID, "boss")
            if variant is None:
                return
            self.CharacterID = variant

        self._set_rare_flag(value)
        if not value and kind in ("alpha", "boss"):
            self._IsBOSS = False

    @property
    def FilteredNickName(self) -> Optional[str]:
        return PalObjects.get_BaseType(self.pal_param.get("FilteredNickName"))

    @FilteredNickName.setter
    @LOGGER.change_logger("FilteredNickName")
    @type_guard
    def FilteredNickName(self, value: str) -> None:
        if self.FilteredNickName is None:
            self.pal_param["FilteredNickName"] = PalObjects.StrProperty(value)
        else:
            self.pal_param["FilteredNickName"]["value"] = value

        if not self.FilteredNickName:
            self.pal_param.pop("FilteredNickName", None)

    @property
    def NickName(self) -> Optional[str]:
        return self._NickName or self.FilteredNickName

    @NickName.setter
    @type_guard
    def NickName(self, value: str) -> None:
        self._NickName = value
        self.FilteredNickName = value

    @property
    def _NickName(self) -> Optional[str]:
        return PalObjects.get_BaseType(self.pal_param.get("NickName"))

    @_NickName.setter
    @LOGGER.change_logger("NickName")
    @type_guard
    def _NickName(self, value: str) -> None:
        if self._NickName is None:
            self.pal_param["NickName"] = PalObjects.StrProperty(value)
        else:
            self.pal_param["NickName"]["value"] = value

        if not self._NickName:
            self.pal_param.pop("NickName", None)

    @property
    def Level(self) -> Optional[int]:
        return PalObjects.get_ByteProperty(self.pal_param.get("Level"))

    @Level.setter
    @LOGGER.change_logger("Level")
    @type_guard
    def Level(self, value: int) -> None:
        value = clamp(1, PalEntity.MAX_INVALID_LEVEL, value)
        if self.Level == value:
            return
        if self.Level is None:
            self.pal_param["Level"] = PalObjects.ByteProperty(value)
        else:
            PalObjects.set_ByteProperty(self.pal_param["Level"], value)
        self.Exp = DataProvider.get_pal_level_xp(self.Level)

        if maxHP := self.ComputedMaxHP:
            self.Hp = maxHP

        self.learn_attacks()

    @property
    def Exp(self) -> Optional[int]:
        return PalObjects.get_BaseType(self.pal_param.get("Exp"))

    @Exp.setter
    @LOGGER.change_logger("Exp")
    @type_guard
    def Exp(self, value: int) -> None:
        if self.Exp is None:
            self.pal_param["Exp"] = PalObjects.Int64Property(value)
        else:
            PalObjects.set_BaseType(self.pal_param["Exp"], value)

    @property
    def FriendshipLevel(self) -> Optional[int]:
        return DataProvider.get_pal_friendship_level_from_pts(self.FriendshipPoint or 0)

    @FriendshipLevel.setter
    @type_guard
    def FriendshipLevel(self, level: int) -> None:
        self.FriendshipPoint = DataProvider.get_pal_friendship(level or 0)

    @property
    def FriendshipPoint(self) -> Optional[int]:
        return PalObjects.get_BaseType(self.pal_param.get("FriendshipPoint"))

    @FriendshipPoint.setter
    @LOGGER.change_logger("FriendshipPoint")
    @type_guard
    def FriendshipPoint(self, value: int) -> None:
        if self.FriendshipPoint is None:
            self.pal_param["FriendshipPoint"] = PalObjects.IntProperty(value)
        else:
            PalObjects.set_BaseType(self.pal_param["FriendshipPoint"], value)

        if maxHP := self.ComputedMaxHP:
            self.Hp = maxHP

    @property
    def Rank(self) -> Optional[int]:
        return PalObjects.get_ByteProperty(self.pal_param.get("Rank"))

    @Rank.setter
    @LOGGER.change_logger("Rank")
    @type_guard
    def Rank(self, rank: int) -> None:
        # 1 = no star, 2 = 1 star, 3 = 2 star, 4 = 3 star, 5 = 4 star
        previous_rank = self.Rank or 1
        rank = clamp(1, 255, rank)
        if self.Rank is None:
            self.pal_param["Rank"] = PalObjects.ByteProperty(rank)
        else:
            PalObjects.set_ByteProperty(self.pal_param.get("Rank"), rank)

        if maxHP := self.ComputedMaxHP:
            self.Hp = maxHP

        if self.Rank == 1:
            self.pal_param.pop("Rank", None)

        if rank != previous_rank:
            self.RankUpExp = 0

    @property
    def RankUpExp(self) -> int:
        return PalObjects.get_BaseType(self.pal_param.get("RankUpExp")) or 0

    @RankUpExp.setter
    @type_guard
    def RankUpExp(self, value: int) -> None:
        value = clamp(PalObjects.UInt16Min, PalObjects.UInt16Max, value)
        if value == 0:
            self.pal_param.pop("RankUpExp", None)
        elif self.RankUpExp == 0:
            self.pal_param["RankUpExp"] = PalObjects.UInt16Property(value)
        else:
            PalObjects.set_BaseType(self.pal_param["RankUpExp"], value)

    @property
    def IsAwakening(self) -> bool:
        return bool(PalObjects.get_BaseType(self.pal_param.get("bIsAwakening")))

    @IsAwakening.setter
    @type_guard
    def IsAwakening(self, value: bool) -> None:
        if value:
            self.pal_param["bIsAwakening"] = PalObjects.BoolProperty(True)
        else:
            self.pal_param.pop("bIsAwakening", None)
        if maxHP := self.ComputedMaxHP:
            self.Hp = maxHP

    @property
    def Rank_HP(self) -> Optional[int]:
        return PalObjects.get_ByteProperty(self.pal_param.get("Rank_HP"))

    @property
    def Rank_Attack(self) -> Optional[int]:
        return PalObjects.get_ByteProperty(self.pal_param.get("Rank_Attack"))

    @property
    def Rank_Defence(self) -> Optional[int]:
        return PalObjects.get_ByteProperty(self.pal_param.get("Rank_Defence"))

    @property
    def Rank_CraftSpeed(self) -> Optional[int]:
        return PalObjects.get_ByteProperty(self.pal_param.get("Rank_CraftSpeed"))

    @Rank_HP.setter
    @LOGGER.change_logger("Rank_HP")
    @type_guard
    def Rank_HP(self, rank: int) -> None:
        self._set_soul_rank("Rank_HP", rank)
        if maxHP := self.ComputedMaxHP:
            self.Hp = maxHP

    @Rank_Attack.setter
    @LOGGER.change_logger("Rank_Attack")
    @type_guard
    def Rank_Attack(self, rank: int) -> None:
        self._set_soul_rank("Rank_Attack", rank)

    @Rank_Defence.setter
    @LOGGER.change_logger("Rank_Defence")
    @type_guard
    def Rank_Defence(self, rank: int) -> None:
        self._set_soul_rank("Rank_Defence", rank)

    @Rank_CraftSpeed.setter
    @LOGGER.change_logger("Rank_CraftSpeed")
    @type_guard
    def Rank_CraftSpeed(self, rank: int) -> None:
        self._set_soul_rank("Rank_CraftSpeed", rank)

    @property
    def ComputedMaxHP(self) -> Optional[int]:
        level = self.Level or 1
        hp_stat = self._base_stat_with_friendship("HP", "Friendship_HP")
        if hp_stat is None:
            return None
        raw_hp = math.trunc(
            (hp_stat * (1 + (self.Talent_HP or 0) * 0.003) + 10)
            * 0.5
            * level
            + 500
        )
        raw_hp = self._apply_rank_upgrades(raw_hp, self.Rank_HP)
        return math.trunc(raw_hp * (1 + self._get_passive_buff("b_HP"))) * 1000

    @property
    def ComputedAttack(self) -> Optional[int]:
        level = self.Level or 1
        attack_stat = self._base_stat_with_friendship(
            "ATK", "Friendship_ShotAttack"
        )
        if attack_stat is None:
            return None
        raw_attack = math.trunc(
            attack_stat * (1 + (self.Talent_Shot or 0) * 0.003) * level * 0.075
            + 100
        )
        raw_attack = self._apply_rank_upgrades(raw_attack, self.Rank_Attack)
        return math.trunc(raw_attack * (1 + self._get_passive_buff("b_Attack")))

    @property
    def ComputedDefense(self) -> Optional[int]:
        level = self.Level or 1
        defense_stat = self._base_stat_with_friendship(
            "DEF", "Friendship_Defense"
        )
        if defense_stat is None:
            return None
        raw_defense = math.trunc(
            defense_stat
            * (1 + (self.Talent_Defense or 0) * 0.003)
            * level
            * 0.075
            + 50
        )
        raw_defense = self._apply_rank_upgrades(raw_defense, self.Rank_Defence)
        return math.trunc(raw_defense * (1 + self._get_passive_buff("b_Defense")))

    @property
    def ComputedCraftSpeed(self) -> Optional[int]:
        craft_speed = DataProvider.get_pal_stats(self.DataAccessKey, "CRAFTSPEED")
        if craft_speed is None:
            return None
        raw_craft_speed = math.trunc(
            craft_speed * (1 + (self.Rank_CraftSpeed or 0) * 0.03)
        )
        return math.trunc(
            raw_craft_speed * (1 + self._get_passive_buff("b_CraftSpeed"))
        )

    def _base_stat_with_friendship(
        self, stat_key: str, friendship_key: str
    ) -> Optional[float]:
        stat = DataProvider.get_pal_stats(self.DataAccessKey, stat_key)
        if stat is None:
            return None
        if self.IsAwakening:
            stat *= 1.1
        if (friendship_level := self.FriendshipLevel or 0) > 0:
            stat += friendship_level * (
                DataProvider.get_pal_parameter(self.DataAccessKey, friendship_key) or 0
            )
        return stat

    def _apply_rank_upgrades(self, stat: int, soul_rank: Optional[int]) -> int:
        stat = math.trunc(stat * (1 + ((self.Rank or 1) - 1) * 0.05))
        return math.trunc(stat * (1 + (soul_rank or 0) * 0.03))

    @property
    def Hp(self) -> Optional[int]:
        return PalObjects.get_FixedPoint64(self.pal_param.get("Hp"))

    @Hp.setter
    @LOGGER.change_logger("Hp")
    @type_guard
    def Hp(self, value: int) -> None:
        if self.Hp is None:
            self.pal_param["Hp"] = PalObjects.FixedPoint64(value)
        else:
            PalObjects.set_FixedPoint64(self.pal_param["Hp"], value)

    @property
    def PassiveSkillList(self) -> Optional[list[str]]:
        return PalObjects.get_ArrayProperty(self.pal_param.get("PassiveSkillList"))

    @LOGGER.change_logger("PassiveSkillList")
    @type_guard
    def add_PassiveSkillList(self, skill: str, force: bool = False) -> bool:
        if not DataProvider.has_passive_skill(skill):
            LOGGER.warning(f"Can't find pal passive {skill} in database, skipping")
            return False

        if self.PassiveSkillList is None:
            self.pal_param["PassiveSkillList"] = PalObjects.ArrayProperty(
                "NameProperty", {"values": []}
            )

        if skill in self.PassiveSkillList:
            LOGGER.warning(f"{self} already has passive {skill}, skipping")
            return False

        if not force and len(self.PassiveSkillList) >= 4:
            LOGGER.warning(
                f"{self} PassiveSkillList has maxed out: {self.PassiveSkillList}, skipping"
            )
            return False

        self.PassiveSkillList.append(skill)
        LOGGER.info(
            f"Added {DataProvider.get_passive_i18n(skill)[0]} to PassiveSkillList"
        )
        if maxHP := self.ComputedMaxHP:
            self.Hp = maxHP
        return True

    @LOGGER.change_logger("PassiveSkillList")
    def pop_PassiveSkillList(self, idx: int = None, item: str = None) -> Optional[str]:
        try:
            if item is not None:
                idx = self.PassiveSkillList.index(item)
            skill = self.PassiveSkillList.pop(int(idx))
            LOGGER.info(
                f"Removed {DataProvider.get_passive_i18n(skill)[0]} from PassiveSkillList"
            )
            if maxHP := self.ComputedMaxHP:
                self.Hp = maxHP
            return skill
        except Exception as e:
            LOGGER.warning(f"{e}")

    @LOGGER.change_logger("PassiveSkillList")
    def replace_PassiveSkillList(self, skills: list[str]) -> None:
        self.pal_param["PassiveSkillList"] = PalObjects.ArrayProperty(
            "NameProperty", {"values": list(skills)}
        )

    @property
    def EquipWaza(self) -> Optional[list[str]]:
        return PalObjects.get_ArrayProperty(self.pal_param.get("EquipWaza"))

    @LOGGER.change_logger("EquipWaza")
    @type_guard
    def add_EquipWaza(self, waza: str, force=False) -> bool:
        """
        Normally you can't add the same "waza" twice on a pal.
        """
        if not DataProvider.has_attack(waza):
            LOGGER.warning(f"Can't find pal attack {waza} in database, skipping")
            return False

        if self.EquipWaza is None:
            self.pal_param["EquipWaza"] = PalObjects.ArrayProperty(
                "EnumProperty", {"values": []}
            )
        if waza in self.EquipWaza:
            LOGGER.warning(f"{self} has already equipped waza {waza}, skipping")
            return False

        if not force and len(self.EquipWaza) >= 3:
            LOGGER.warning(
                f"{self} EquipWaza has maxed out: {self.EquipWaza}, consider add to MasteredWaza instead."
            )
            return False

        self.EquipWaza.append(waza)

        if waza not in (self.MasteredWaza or []):
            self.add_MasteredWaza(waza)

        LOGGER.info(f"Added {DataProvider.get_attack_i18n(waza)[0]} to EquipWaza")
        return True

    @LOGGER.change_logger("EquipWaza")
    def pop_EquipWaza(self, idx: int = None, item: str = None) -> Optional[str]:
        try:
            if item is not None:
                idx = self.EquipWaza.index(item)
            waza = self.EquipWaza.pop(int(idx))
            LOGGER.info(
                f"Removed {DataProvider.get_attack_i18n(waza)[0]} from EquipWaza"
            )
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
        return PalObjects.get_ArrayProperty(self.pal_param.get("MasteredWaza"))

    @LOGGER.change_logger("MasteredWaza")
    @type_guard
    def add_MasteredWaza(self, waza: str) -> bool:
        """
        Normally you can't add the same "waza" twice on a pal.
        """
        if not DataProvider.has_attack(waza):
            LOGGER.warning(f"Pal attack {waza} not in database, skipping")
            return False

        if self.MasteredWaza is None:
            self.pal_param["MasteredWaza"] = PalObjects.ArrayProperty(
                "EnumProperty", {"values": []}
            )

        if waza in self.MasteredWaza:
            LOGGER.info(f"{self} has already learned waza {waza}, skipping")
            return False

        self.MasteredWaza.append(waza)

        LOGGER.info(f"Added {DataProvider.get_attack_i18n(waza)[0]} to MasteredWaza")

        if self.num_EmptyEquipWaza > 0:
            self.add_EquipWaza(waza)

        return True

    @LOGGER.change_logger("MasteredWaza")
    @type_guard
    def pop_MasteredWaza(self, idx: int = None, item: str = None) -> Optional[str]:
        try:
            if item is not None:
                idx = self.MasteredWaza.index(item)
            waza = self.MasteredWaza.pop(int(idx))
            if waza in (self.EquipWaza or []):
                self.pop_EquipWaza(item=waza)

            LOGGER.info(
                f"Removed {DataProvider.get_attack_i18n(waza)[0]} from MasteredWaza"
            )
            return waza
        except Exception as e:
            LOGGER.warning(f"{e}")

    def replace_EquipWaza(self, equipped: list[str]) -> None:
        old_equipped = list(self.EquipWaza or [])
        if self.MasteredWaza is None:
            self.pal_param["MasteredWaza"] = PalObjects.ArrayProperty(
                "EnumProperty", {"values": []}
            )
        for skill in equipped:
            if skill not in self.MasteredWaza:
                self.MasteredWaza.append(skill)
        self.pal_param["EquipWaza"] = PalObjects.ArrayProperty(
            "EnumProperty", {"values": list(equipped)}
        )
        LOGGER.info(f"{self} | EquipWaza: {old_equipped} -> {equipped}")

    @LOGGER.change_logger("MasteredWaza")
    def replace_MasteredWaza(self, mastered: list[str]) -> None:
        """Learn exactly this list, and unequip whatever is no longer on it.

        `pop_MasteredWaza` already refuses to leave an equipped skill unlearned;
        replacing the whole list has to keep the same invariant, or the save ends
        up with a Pal whose active slots hold skills it has not mastered.
        """
        old_mastered = list(self.MasteredWaza or [])
        self.pal_param["MasteredWaza"] = PalObjects.ArrayProperty(
            "EnumProperty", {"values": list(mastered)}
        )
        for waza in list(self.EquipWaza or []):
            if waza not in mastered:
                self.pop_EquipWaza(item=waza)
        LOGGER.info(f"{self} | MasteredWaza: {old_mastered} -> {mastered}")

    @property
    def AddedWorkSuitabilities(self) -> Optional[dict[PalSuitability, int]]:
        return PalObjects.get_WorkSuitabilities(
            self.pal_param.get("GotWorkSuitabilityAddRankList")
        )

    @property
    def WorkSuitabilities(self) -> Optional[dict[str, int]]:
        suits = self.MinimumWorkSuitabilities
        if suits is None:
            return None

        if self.AddedWorkSuitabilities:
            for suit, rank in self.AddedWorkSuitabilities.items():
                suit = suit.value
                if suit in suits:
                    suits[suit] = min(MAX_WORK_SUITABILITY, suits[suit] + rank)

        return suits

    @property
    def MinimumWorkSuitabilities(self) -> Optional[dict[str, int]]:
        suits_data = DataProvider.get_pal_suitabilities(self.DataAccessKey)
        if not suits_data:
            return None

        suits = {key: value for key, value in suits_data.items() if value > 0}

        condensation_bonus = condensation_work_suitability_bonus(
            suits,
            self.Rank or 1,
            DataProvider.get_pal_best_work_suitability(self.DataAccessKey),
        )
        for suit, rank in condensation_bonus.items():
            suits[suit] = min(MAX_WORK_SUITABILITY, suits[suit] + rank)

        return suits

    @LOGGER.change_logger("WorkSuitabilities")
    @LOGGER.change_logger("AddedWorkSuitabilities")
    @type_guard
    def set_WorkSuitability(self, suit: PalSuitability | str, rank: int) -> None:
        if self.AddedWorkSuitabilities is None:
            self.pal_param["GotWorkSuitabilityAddRankList"] = (
                PalObjects.GotWorkSuitabilityAddRankList()
            )

        if isinstance(suit, str):
            suit = PalSuitability.from_value(suit)
            if not suit:
                LOGGER.warning(f"Invalid suit {suit}, skipping")
                return

        if rank <= 0:
            PalObjects.pop_WorkSuitability(
                self.pal_param["GotWorkSuitabilityAddRankList"], suit
            )
        else:
            suits = DataProvider.get_pal_suitabilities(self.DataAccessKey)
            if not suits:
                return

            condensation_bonus = condensation_work_suitability_bonus(
                suits,
                self.Rank or 1,
                DataProvider.get_pal_best_work_suitability(self.DataAccessKey),
            )
            added_rank = rank - (
                suits[suit.value] + condensation_bonus.get(suit.value, 0)
            )
            if added_rank <= 0:
                PalObjects.pop_WorkSuitability(
                    self.pal_param["GotWorkSuitabilityAddRankList"], suit
                )
            else:
                PalObjects.set_WorkSuitability(
                    self.pal_param["GotWorkSuitabilityAddRankList"], suit, added_rank
                )

        if not self.AddedWorkSuitabilities:
            self.pal_param.pop("GotWorkSuitabilityAddRankList", None)

    @property
    def Talent_HP(self) -> Optional[int]:
        return PalObjects.get_ByteProperty(self.pal_param.get("Talent_HP"))

    @property
    def Talent_Melee(self) -> Optional[int]:
        return PalObjects.get_ByteProperty(self.pal_param.get("Talent_Melee"))

    @property
    def Talent_Shot(self) -> Optional[int]:
        return PalObjects.get_ByteProperty(self.pal_param.get("Talent_Shot"))

    @property
    def Talent_Defense(self) -> Optional[int]:
        return PalObjects.get_ByteProperty(self.pal_param.get("Talent_Defense"))

    @Talent_HP.setter
    @LOGGER.change_logger("Talent_HP")
    @type_guard
    def Talent_HP(self, value: int):
        self._set_iv("Talent_HP", value)

        if maxHP := self.ComputedMaxHP:
            self.Hp = maxHP

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

    # @property
    # def CraftSpeed(self) -> Optional[int]:
    #     return PalObjects.get_BaseType(self.pal_param.get("CraftSpeed"))

    @property
    def SanityValue(self) -> Optional[float]:
        return PalObjects.get_BaseType(self.pal_param.get("SanityValue"))

    @SanityValue.setter
    @LOGGER.change_logger("SanityValue")
    @type_guard
    def SanityValue(self, val: float):
        if self.SanityValue is None:
            self.pal_param["SanityValue"] = PalObjects.FloatProperty(val)
        else:
            PalObjects.set_BaseType(self.pal_param.get("SanityValue"), val)

    @property
    def FullStomach(self) -> Optional[float]:
        return PalObjects.get_BaseType(self.pal_param.get("FullStomach"))

    @FullStomach.setter
    @LOGGER.change_logger("FullStomach")
    @type_guard
    def FullStomach(self, val: float):
        if self.FullStomach is None:
            self.pal_param["FullStomach"] = PalObjects.FloatProperty(val)
        else:
            PalObjects.set_BaseType(self.pal_param["FullStomach"], val)

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
        return PalObjects.get_EnumProperty(self.pal_param.get("WorkerSick"))

    @property
    def HungerType(self) -> Optional[str]:
        return PalObjects.get_EnumProperty(self.pal_param.get("HungerType"))

    @property
    def UniqueNPCID(self) -> str:
        return PalObjects.get_BaseType(self.pal_param.get("UniqueNPCID"))

    @LOGGER.change_logger("UniqueNPCID")
    def update_UniqueNPCID(self) -> None:
        if self.CharacterID not in [
            "GrassBoss",
            "ForestBoss",
            "DesertBoss",
            "ElectricBoss",
            "SnowBoss",
            "SakurajimaBoss",
            "VikingBoss",
        ]:
            LOGGER.info(
                f"Pal {self.CharacterID} is not a Tower Human, UniqueNPCID will be unset."
            )
            self.pal_param.pop("UniqueNPCID", None)
            return

        if self.UniqueNPCID is None:
            self.pal_param["UniqueNPCID"] = PalObjects.NameProperty(self.CharacterID)
        else:
            PalObjects.set_BaseType(self.pal_param["UniqueNPCID"], self.CharacterID)

        if not self.UniqueNPCID:
            self.pal_param.pop("UniqueNPCID", None)

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
        return PalObjects.get_BaseType(self.pal_param.get("PalReviveTimer"))

    # @PalReviveTimer.setter
    # @LOGGER.change_logger("PalReviveTimer")
    # def PalReviveTimer(self, val: float) -> Optional[float]:
    #     if self.PalReviveTimer is None:
    #         return
    #     PalObjects.set_BaseType(self.pal_param.get("PalReviveTimer"), val)

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
        return PalObjects.get_EnumProperty(self.pal_param.get("PhysicalHealth"))

    @property
    def IsFaintedPal(self) -> bool:
        if (
            self.PalReviveTimer
            or self.PhysicalHealth == "EPalStatusPhysicalHealthType::Dying"
        ):
            return True
        return False

    @LOGGER.change_logger("PhysicalHealth")
    @LOGGER.change_logger("WorkerSick")
    @LOGGER.change_logger("HungerType")
    @LOGGER.change_logger("PalReviveTimer")
    def heal_pal(self):
        self.pal_param.pop("PalReviveTimer", None)
        self.pal_param.pop("PhysicalHealth", None)
        self.pal_param.pop("WorkerSick", None)
        self.pal_param.pop("HungerType", None)

        if maxFullStomach := DataProvider.get_pal_stats(self.DataAccessKey, "FOOD"):
            self.FullStomach = maxFullStomach
        else:
            self.FullStomach = 150.0

        self.SanityValue = 100.0
        if maxHP := self.ComputedMaxHP:
            self.Hp = maxHP

    @property
    def FoodWithStatusEffect(self) -> Optional[str]:
        return PalObjects.get_BaseType(self.pal_param.get("FoodWithStatusEffect"))

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
        return PalObjects.get_BaseType(
            self.pal_param.get("Tiemr_FoodWithStatusEffect")
        )

    @Timer_FoodWithStatusEffect.setter
    @LOGGER.change_logger("Timer_FoodWithStatusEffect")
    @type_guard
    def Timer_FoodWithStatusEffect(self, val: int) -> bool:
        if self.FoodWithStatusEffect is None or self.Timer_FoodWithStatusEffect is None:
            LOGGER.warning(
                "Trying to set food effect timer when there is no food eaten."
            )
            return False
        PalObjects.set_BaseType(self.pal_param["Tiemr_FoodWithStatusEffect"], val)

    @property
    def SkinName(self) -> Optional[str]:
        value = PalObjects.get_BaseType(self.pal_param.get("SkinName"))
        return None if not value or value == "None" else value

    @property
    def SkinAppliedCharacterId(self) -> Optional[UUID]:
        return PalObjects.get_BaseType(
            self.pal_param.get("SkinAppliedCharacterId")
        )

    @SkinName.setter
    @LOGGER.change_logger("SkinName")
    @type_guard
    def SkinName(self, value: str | None) -> None:
        if not value or value == "None":
            self.pal_param.pop("SkinName", None)
            self.pal_param.pop("SkinAppliedCharacterId", None)
            return
        skin = DataProvider.get_skin(value)
        if skin is None or DataProvider.get_pal_family_id(
            skin.get("TargetPalName")
        ) != DataProvider.get_pal_family_id(self.CharacterID):
            raise ValueError(f"Skin {value} is not valid for {self.DataAccessKey}")
        skin_applier = self.OwnerPlayerUId or self.LastOwnerPlayerUId
        if skin_applier is None:
            raise ValueError(
                "A Pal must have an owner or previous owner before a skin can be applied"
            )
        if self.SkinName is None:
            self.pal_param["SkinName"] = PalObjects.NameProperty(value)
        else:
            PalObjects.set_BaseType(self.pal_param["SkinName"], value)
        self.pal_param["SkinAppliedCharacterId"] = PalObjects.Guid(
            skin_applier
        )

    def learn_attacks(self):
        # if self.IsHuman:
        #     self.add_MasteredWaza("EPalWazaID::Human_Punch")
        # else:
        for atk in DataProvider.get_attacks_to_learn(
            self.DataAccessKey, self.Level or 1
        ):
            if atk not in (self.MasteredWaza or []):
                self.add_MasteredWaza(atk)

    def equip_all_pal_attacks(self):
        atks = DataProvider.get_attacks_to_learn(self.DataAccessKey, self.Level or 1)
        if not atks:
            return
        (self.EquipWaza or []).clear()
        for atk in atks:
            if atk not in (self.EquipWaza or []):
                self.add_EquipWaza(atk, True)

    def remove_unique_attacks(self):
        if self.MasteredWaza is None:
            return
        atks = self.MasteredWaza.copy()
        if not atks:
            return
        for atk in atks:
            if self.IsHuman:
                self.pop_MasteredWaza(item=atk)
            elif DataProvider.is_unique_attacks(atk):
                self.pop_MasteredWaza(item=atk)

    def maximize_progression(self) -> None:
        """Set every normal, player-facing Pal upgrade to its legal maximum."""
        self.Level = self.MAX_LEVEL
        self.FriendshipLevel = self.MAX_FRIENDSHIP_LEVEL
        self.Rank = self.MAX_CONDENSATION_RANK
        self.RankUpExp = 0

        self.Rank_HP = self.MAX_SOUL_RANK
        self.Rank_Attack = self.MAX_SOUL_RANK
        self.Rank_Defence = self.MAX_SOUL_RANK
        self.Rank_CraftSpeed = self.MAX_SOUL_RANK

        self.Talent_HP = self.MAX_TALENT
        self.Talent_Shot = self.MAX_TALENT
        self.Talent_Defense = self.MAX_TALENT

        if not self.IsHuman:
            self.IsAwakening = True

        for suitability in tuple(self.MinimumWorkSuitabilities or {}):
            self.set_WorkSuitability(suitability, MAX_WORK_SUITABILITY)

    def _set_soul_rank(self, property_name: str, rank: int):
        # valid option is rank = clamp(0, 20, rank)
        rank = clamp(0, 255, rank)
        if getattr(self, property_name) is None:
            self.pal_param[property_name] = PalObjects.ByteProperty(rank)
        else:
            PalObjects.set_ByteProperty(self.pal_param.get(property_name), rank)

        if getattr(self, property_name) == 0:
            self.pal_param.pop(property_name, None)

    def _set_iv(self, property_name: str, value: int):
        # valid option is value = clamp(0, 100, value)
        iv = clamp(0, 255, value)
        if getattr(self, property_name) is None:
            self.pal_param[property_name] = PalObjects.ByteProperty(iv)
        else:
            PalObjects.set_ByteProperty(self.pal_param[property_name], iv)

    def _get_display_name(self) -> str:
        cache_key = (
            Config.i18n,
            self.DataAccessKey,
            self.NickName,
            # self.Gender,
        )
        try:
            return self._display_name_cache[cache_key]
        except KeyError:
            species_key = self.DataAccessKey
            species_name = DataProvider.get_pal_i18n(species_key) or species_key
            nickname_suffix = f" ({self.NickName})" if self.NickName else ""

            # gender_suffix = ""
            # if self.Gender == PalGender.FEMALE:
            #     gender_suffix = "♀"
            # elif self.Gender == PalGender.MALE:
            #     gender_suffix = "♂"

            # name = f"{rare_prefix}{boss_prefix}{tower_prefix}{species_name}{nickname_suffix}{gender_suffix}"
            name = f"{species_name}{nickname_suffix}"
            self._display_name_cache[cache_key] = name
            return name

    def _get_passive_buff(self, buff_key: str) -> float:
        if self.PassiveSkillList is None:
            return 0
        bonus = 0.0
        for passive in self.PassiveSkillList or []:
            bonus += DataProvider.get_passive_buff(passive, buff_key)
        return bonus
