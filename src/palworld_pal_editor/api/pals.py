"""The seven Pal routes, and the field lists that say what a PATCH may write.

Reading a Pal is `pal_serializers.py` and the three things every mutation owes the
session are `operations.py`; what is left here is the HTTP layer plus the one
question only these routes answer -- which fields a client is allowed to set, and
which of them need more than the entity's own setter.
"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from palworld_pal_editor.api.errors import ApiError, register_error_handlers
from palworld_pal_editor.api.operations import (
    commit_pal_edit,
    operation_result,
    require_record,
)
from palworld_pal_editor.api.pal_serializers import native_record, pal_detail
from palworld_pal_editor.api.roster_keys import core_roster_key, roster_key_for_record
from palworld_pal_editor.core import PalEntity, SaveManager
from palworld_pal_editor.utils import DataProvider

pals_blueprint = Blueprint("pals", __name__)
register_error_handlers(pals_blueprint)






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
# here rather than resolved from the URL: reading an action name out of a request
# and looking it up on the entity is how a typo becomes an arbitrary method call.
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
    """One more of this Pal, wherever the backend decides it fits.

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
