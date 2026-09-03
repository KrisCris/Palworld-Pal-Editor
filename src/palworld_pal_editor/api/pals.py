"""Pal resources, and the two response levels every Pal read uses (spec §8.3).

`PalSummary` is what a roster row needs; `PalDetail` is everything the editor page
reads, fetched only when a Pal is clicked. Both are explicit field lists -- nothing
here reflects over the entity, so what the API promises is readable in one place.

Naming follows §8.3: a field the save file itself has keeps the game's name and
casing (`InstanceId`, `ContainerId`, `SlotIndex`, `CharacterID`), while the fields
the editor invents to say where a Pal is and what has happened to it are camelCase
(`recordKey`, `storageKey`, `containerLabel`, `changeState`).
"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from palworld_pal_editor.api.errors import ApiError, register_error_handlers
from palworld_pal_editor.api.roster_keys import core_roster_key, roster_key_for_record
from palworld_pal_editor.core import PalEntity, SaveManager
from palworld_pal_editor.core.pal_record import PalRecord
from palworld_pal_editor.core.pal_storage_adapters import WorldPalAdapter
from palworld_pal_editor.utils import DataProvider

pals_blueprint = Blueprint("pals", __name__)
register_error_handlers(pals_blueprint)


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

    Spec §7.1: an ownerless Pal is never away -- a base worker is where it belongs.
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
        "ContainerId": location["ContainerId"],
        "SlotIndex": location["SlotIndex"],
        "containerKind": location["ContainerKind"],
        "containerLabel": location["ContainerLabel"],
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
    the two a pasted record came out of (spec §6.1).
    """
    adapter = (
        manager.world_adapter
        if record.storage_kind == "world"
        else manager.storage_adapters[record.storage_key]
    )
    return adapter.export(record)


def require_record(record_key: str) -> PalRecord:
    """The record that key names, or the 404 every Pal sub-resource would repeat."""
    record = SaveManager().get_record(record_key)
    if record is None:
        raise ApiError(
            "PAL_NOT_FOUND",
            f"No Pal record named {record_key}",
            status=404,
        )
    return record


def operation_result(
    manager: SaveManager,
    record: PalRecord | None = None,
    *,
    affected_roster_keys=(),
    deleted_record_keys=(),
    affected_storage_keys=(),
) -> dict:
    """The one shape every Pal-changing response uses (spec §8.3).

    All four keys are always present, so the client reads one shape and never has
    to guess what an operation did. A delete says what is gone, a create says which
    storage now holds one more Pal, and a move fills both at once.
    """
    return {
        "resultRecord": pal_detail(manager, record) if record is not None else None,
        "deletedRecordKeys": list(deleted_record_keys),
        "affectedRosterKeys": list(affected_roster_keys),
        "affectedStorageKeys": list(affected_storage_keys),
    }


def commit_pal_edit(manager: SaveManager, record: PalRecord) -> dict:
    """What every successful single-Pal edit owes the session, in one place.

    A Global Palbox or DPS Pal is a copy that has to be written back before the
    session is saved, and a changed Pal is one the change-set marks have to know
    about. Forgetting either is silent, which is why no route does it by hand.
    """
    manager.pal_mutations.normalize_external_record(record)
    manager.pal_repository.mark_modified(record)
    return operation_result(manager, record)


# Each of these is a `PalEntity` property whose setter already coerces and
# range-checks what it is handed, which is why nothing is validated again below:
# the save file's rules live next to the save file. Being settable is not what
# makes a field writable -- being named here is.
PAL_SCALAR_FIELDS = (
    "CharacterID",
    "NickName",
    "SkinName",
    "Gender",
    "Level",
    "FriendshipLevel",
    "Rank",
    "Rank_HP",
    "Rank_Attack",
    "Rank_Defence",
    "Rank_CraftSpeed",
    "Talent_HP",
    "Talent_Melee",
    "Talent_Shot",
    "Talent_Defense",
    "FavoriteIndex",
    "IsRarePal",
    "IsBOSS",
    "IsAwakening",
    "IsImportedCharacter",
)


def _set_suitabilities(pal: PalEntity, value) -> None:
    """A partial `{name: level}` map, the shape a player's status points take too."""
    for name, level in value.items():
        pal.set_WorkSuitability(name, level)


PAL_WRITERS = {"Suitabilities": _set_suitabilities}
WRITABLE_PAL_FIELDS = frozenset(PAL_SCALAR_FIELDS) | set(PAL_WRITERS)

# The three skill lists, each with the catalog that says a name is real and the
# entity method that swaps the whole list for a new one. The methods are named
# here rather than resolved from the URL: spec §8.3 rules out reading an action
# name out of a request and looking it up on the entity.
SKILL_GROUPS = {
    "passive": (DataProvider.has_passive_skill, PalEntity.replace_PassiveSkillList),
    "equipped": (DataProvider.has_attack, PalEntity.replace_EquipWaza),
    "mastered": (DataProvider.has_attack, PalEntity.replace_MasteredWaza),
}


@pals_blueprint.route("/<record_key>", methods=["GET"])
@jwt_required()
def get_pal(record_key: str):
    manager = SaveManager()
    with manager.session_lock:
        return pal_detail(manager, require_record(record_key))


@pals_blueprint.route("/<record_key>", methods=["PATCH"])
@jwt_required()
def patch_pal(record_key: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ApiError("PAL_PATCH_INVALID", "Request body must be an object")
    unwritable = set(payload) - WRITABLE_PAL_FIELDS
    if unwritable:
        raise ApiError(
            "PAL_FIELD_UNKNOWN",
            f"Not an editable Pal field: {', '.join(sorted(unwritable))}",
            details={"writable": sorted(WRITABLE_PAL_FIELDS)},
        )

    manager = SaveManager()
    with manager.session_lock:
        record = require_record(record_key)
        try:
            for field in PAL_SCALAR_FIELDS:
                if field in payload:
                    setattr(record.pal, field, payload[field])
            for field, write in PAL_WRITERS.items():
                if field in payload:
                    write(record.pal, payload[field])
        except (TypeError, ValueError, AttributeError) as error:
            raise ApiError("PAL_VALUE_INVALID", str(error))
        return commit_pal_edit(manager, record)


@pals_blueprint.route("/<record_key>", methods=["DELETE"])
@jwt_required()
def delete_pal(record_key: str):
    """Remove one Pal from the save.

    The roster and the storage are read before the delete, because afterwards the
    record answers for nowhere: it is the one operation whose `resultRecord` is
    null, so `deletedRecordKeys` is all the client gets to act on.
    """
    manager = SaveManager()
    with manager.session_lock:
        record = require_record(record_key)
        roster_key = roster_key_for_record(manager, record)
        storage_key = record.storage_key
        if not manager.pal_mutations.delete(record.record_key):
            raise ApiError(
                "PAL_DELETE_FAILED",
                f"Unable to delete {record_key}",
                status=500,
            )
        return operation_result(
            manager,
            deleted_record_keys=[record.record_key],
            affected_roster_keys=[roster_key],
            affected_storage_keys=[key for key in (storage_key,) if key],
        )


@pals_blueprint.route("/<record_key>/native-record", methods=["GET"])
@jwt_required()
def get_pal_native_record(record_key: str):
    """This Pal as its own storage format writes it, for export and templates."""
    manager = SaveManager()
    with manager.session_lock:
        return native_record(manager, require_record(record_key))


@pals_blueprint.route("/<record_key>/duplicates", methods=["POST"])
@jwt_required()
def duplicate_pal(record_key: str):
    """One more of this Pal, wherever the backend decides it fits (spec §8.3).

    There is no target in the request because the editor's copy button has never
    offered one: a Global Palbox or DPS Pal is copied inside its own storage, and a
    World Pal into the first container of its roster with room. Which roster that
    is comes from the record rather than from whatever list the client had open --
    the button is on the Pal, and the two cannot disagree.
    """
    manager = SaveManager()
    with manager.session_lock:
        record = require_record(record_key)
        try:
            clone = manager.pal_mutations.duplicate(
                record.record_key,
                core_roster_key(roster_key_for_record(manager, record)),
            )
        except ValueError as error:
            raise ApiError("PAL_DUPLICATE_REFUSED", str(error))
        return operation_result(
            manager,
            clone,
            affected_roster_keys=[roster_key_for_record(manager, clone)],
            affected_storage_keys=[clone.storage_key],
        )


@pals_blueprint.route("/<record_key>/skills/<group>", methods=["PUT"])
@jwt_required()
def put_pal_skills(record_key: str, group: str):
    """The list the Pal should end up with, not one add or one removal.

    The count limits the UI enforces are not repeated here: the RPCs this replaces
    passed `force=True` every time, so the backend has never been what stops a
    fifth passive. What it does stop is a name the game has no skill for, which is
    a Pal the game cannot load.
    """
    if group not in SKILL_GROUPS:
        raise ApiError(
            "SKILL_GROUP_UNKNOWN", f"No skill group named {group}", status=404
        )
    payload = request.get_json(silent=True)
    skills = payload.get("skills") if isinstance(payload, dict) else None
    if not isinstance(skills, list):
        raise ApiError("SKILL_LIST_INVALID", 'Request body must be {"skills": [...]}')

    is_known, replace = SKILL_GROUPS[group]
    unknown = [
        skill for skill in skills if not isinstance(skill, str) or not is_known(skill)
    ]
    if unknown:
        raise ApiError(
            "SKILL_UNKNOWN",
            f"Not a {group} skill this game has: {', '.join(map(str, unknown))}",
        )
    if len(skills) != len(set(skills)):
        raise ApiError("SKILL_LIST_INVALID", "A skill cannot be listed twice")

    manager = SaveManager()
    with manager.session_lock:
        record = require_record(record_key)
        replace(record.pal, skills)
        return commit_pal_edit(manager, record)


@pals_blueprint.route("/<record_key>/maximization", methods=["POST"])
@jwt_required()
def maximize_pal(record_key: str):
    """Every normal upgrade at once. It takes no body: there is nothing to choose."""
    manager = SaveManager()
    with manager.session_lock:
        record = require_record(record_key)
        record.pal.maximize_progression()
        return commit_pal_edit(manager, record)
