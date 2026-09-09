"""The two response levels every Pal read uses, and the record behind them.

`pal_summary` is what a roster row needs; `pal_detail` is everything the editor page
reads, fetched only when a Pal is clicked. Both are explicit field lists -- nothing
here reflects over the entity, so what the API promises is readable in one place,
and adding a property to `PalEntity` never silently changes the wire.

Naming: a field the save file itself has keeps the game's name and casing
(`InstanceId`, `ContainerId`, `SlotIndex`, `CharacterID`), while the fields the
editor invents to say where a Pal is and what has happened to it are camelCase
(`recordKey`, `storageKey`, `containerLabel`, `changeState`).

Nothing here writes. Reading a Pal and changing one are separate concerns, and the
route modules are the only things that do both.
"""

from palworld_pal_editor.core import PalEntity, SaveManager
from palworld_pal_editor.core.pal_record import PalRecord
from palworld_pal_editor.core.pal_storage_adapters import WorldPalAdapter
from palworld_pal_editor.utils import DataProvider


def guid_string_or_none(value) -> str | None:
    """A guid as text, or None for the save file's several spellings of "nobody"."""
    if value is None:
        return None
    text = str(value)
    if getattr(value, "int", None) == 0 or not text.replace("-", "").strip("0"):
        return None
    return text


def _is_away(manager: SaveManager, record: PalRecord) -> bool:
    """Whether the Pal is somewhere other than its owner's own party or palbox.

    An ownerless Pal is never away -- a base worker is where it belongs.
    Comparing storage keys rather than container ids answers the DPS, GPS and
    unlocated cases in the same breath, since none of those can be a World container
    the owner owns.
    """
    owner = manager.get_player(record.pal.OwnerPlayerUId)
    if owner is None:
        return bool(guid_string_or_none(record.pal.OwnerPlayerUId))
    return record.storage_key not in (
        WorldPalAdapter.storage_key(owner.OtomoCharacterContainerId),
        WorldPalAdapter.storage_key(owner.PalStorageContainerId),
    )


def _change_state(manager: SaveManager, record: PalRecord) -> str:
    """`unchanged | created | modified`, with created winning over modified."""
    if manager.pal_repository.is_created(record):
        return "created"
    return "modified" if manager.pal_repository.is_modified(record) else "unchanged"


def pal_summary(manager: SaveManager, record: PalRecord) -> dict:
    """One roster row: enough to render, sort, group and badge it, and no more."""
    pal = record.pal
    location = manager.storage_directory.resolve_record_location(record)
    static_record = DataProvider.get_pal_record(pal.CharacterID) or {}
    return {
        "recordKey": record.record_key,
        "InstanceId": str(pal.InstanceId) if pal.InstanceId else None,
        "CharacterID": pal.CharacterID,
        "OwnerPlayerUId": guid_string_or_none(pal.OwnerPlayerUId),
        "I18nName": pal.I18nName or None,
        "DisplayName": pal.DisplayName or None,
        "IconAccessKey": pal.IconAccessKey or None,
        "DataAccessKey": pal.DataAccessKey or None,
        "Paldeck": static_record.get("PaldeckIndex"),
        "Gender": pal.Gender.value if pal.Gender else None,
        "FavoriteIndex": pal.FavoriteIndex,
        "IsBOSS": pal.IsBOSS or False,
        "IsRarePal": pal.IsRarePal or False,
        "IsTower": pal.IsTower or False,
        "IsAwakening": pal.IsAwakening,
        "IsImportedCharacter": pal.IsImportedCharacter,
        "IsHuman": pal.IsHuman,
        "IsExpeditionPal": pal.IsExpeditionPal,
        "storageKey": record.storage_key,
        "storageKind": record.storage_kind,
        "storageOwnerPlayerUid": record.storage_owner_uid,
        "ContainerId": location.ContainerId,
        "SlotIndex": location.SlotIndex,
        "containerKind": location.storage_role,
        "containerLabel": location.storage_label,
        "isAway": _is_away(manager, record),
        "changeState": _change_state(manager, record),
    }


def pal_detail(manager: SaveManager, record: PalRecord) -> dict:
    """Every field the editor page reads. The summary's fields plus the editable ones."""
    pal: PalEntity = record.pal
    static_record = DataProvider.get_pal_record(pal.CharacterID) or {}
    owner_uid = guid_string_or_none(pal.OwnerPlayerUId)
    return {
        **pal_summary(manager, record),
        "groupId": guid_string_or_none(record.group_id),
        "OwnerName": pal.OwnerName if owner_uid else None,
        "IconKey": DataProvider.get_pal_icon_key(pal.CharacterID),
        "FamilyID": pal.RawSpecieKey,
        "VariantKind": DataProvider.get_pal_variant_kind(pal.CharacterID),
        "VariantTags": list(DataProvider.get_pal_variant_tags(pal.CharacterID)),
        "PaldeckRecordID": DataProvider.get_pal_paldeck_record_id(pal.CharacterID),
        "PaldeckSuffix": static_record.get("PaldeckSuffix", ""),
        "Invalid": static_record.get("Invalid", True),
        "RegularlyObtainable": static_record.get("RegularlyObtainable", False),
        "AvailabilitySources": static_record.get("AvailabilitySources", []),
        "ObtainMethods": static_record.get("ObtainMethods", []),
        "NickName": pal.NickName or "",
        "SkinName": pal.SkinName or "",
        "Level": pal.Level or 1,
        "FriendshipLevel": pal.FriendshipLevel or 0,
        "HasBaseVariant": pal.HasBaseVariant,
        "HasBossVariant": pal.HasBossVariant,
        "HasTowerVariant": pal.HasTowerVariant,
        "HasRaidVariant": pal.HasRaidVariant,
        "HasPredatorVariant": pal.HasPredatorVariant,
        "HasWorkerSick": pal.HasWorkerSick,
        "IsFaintedPal": pal.IsFaintedPal,
        "IsRAID": pal.IsRAID or False,
        "IsPREDATOR": pal.IsPREDATOR or False,
        "IsSUMMON": pal.IsSUMMON or False,
        "IsOilrig": pal.IsOilrig or False,
        "IsOtomoTower": pal.IsOtomoTower or False,
        "ComputedMaxHP": pal.ComputedMaxHP or None,
        "ComputedAttack": pal.ComputedAttack or None,
        "ComputedDefense": pal.ComputedDefense or None,
        "ComputedCraftSpeed": pal.ComputedCraftSpeed or None,
        "Rank": pal.Rank if pal.Rank else 1,
        "RankUpExp": pal.RankUpExp,
        "Rank_HP": pal.Rank_HP or 0,
        "Rank_Attack": pal.Rank_Attack or 0,
        "Rank_Defence": pal.Rank_Defence or 0,
        "Rank_CraftSpeed": pal.Rank_CraftSpeed or 0,
        "Talent_HP": pal.Talent_HP or 0,
        "Talent_Melee": pal.Talent_Melee or 0,
        "Talent_Shot": pal.Talent_Shot or 0,
        "Talent_Defense": pal.Talent_Defense or 0,
        "PassiveSkillList": pal.PassiveSkillList or [],
        "EquipWaza": pal.EquipWaza or [],
        "MasteredWaza": pal.MasteredWaza or [],
        "Suitabilities": pal.WorkSuitabilities or {},
        "SuitabilityMinimums": pal.MinimumWorkSuitabilities or {},
    }


def native_record(manager: SaveManager, record: PalRecord) -> dict:
    """The record's own native JSON, through the adapter that owns its format.

    A World Pal is the whole `CharacterSaveParameterMap` record; a DPS or Global
    Palbox Pal is its real single-entry `SaveParameterArray`, header and entry
    envelope included, because that envelope is the only thing that says which of
    the two a pasted record came out of.
    """
    adapter = (
        manager.world_adapter
        if record.storage_kind == "world"
        else manager.storage_adapters[record.storage_key]
    )
    return adapter.export(record)
