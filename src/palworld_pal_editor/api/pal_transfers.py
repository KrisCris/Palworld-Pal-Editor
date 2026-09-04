"""Moving a Pal, as one resource.

A transfer is a transaction across records the client cannot see -- a container slot,
a guild's membership, a DPS entry, the locker -- so it is a resource of its own rather
than a PATCH on the Pal. The request says only where the Pal should end up; whether
that means a move, a copy into the Global Palbox or an overwrite is the backend's to
decide, and the same decision the move dialog already read out of the capability.

The one thing the client does decide is which existing Pal an overwrite lands on, and
only after being shown it. That comes back as `conflictResolution.expectedTarget` and
is re-checked here against the session lock, because the dialog was open while the
save was not held.
"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from palworld_pal_editor.api.errors import ApiError, register_error_handlers
from palworld_pal_editor.api.pals import operation_result, require_record
from palworld_pal_editor.api.roster_keys import roster_key_for_record
from palworld_pal_editor.core import PalEntity, SaveManager
from palworld_pal_editor.core.pal_transactions import (
    PalIdentityConflict,
    PalOperationRefused,
)
from palworld_pal_editor.core.pal_record import PalRecord
from palworld_pal_editor.utils import DataProvider

pal_transfers_blueprint = Blueprint("pal_transfers", __name__)
register_error_handlers(pal_transfers_blueprint)


def pal_brief(pal: PalEntity) -> dict:
    """Everything the overwrite dialog compares between two Pals.

    Gameplay only: what a Pal *is*, never where it is or whose it is. The user is
    deciding whether the incoming Pal is worth losing the existing one for, and its
    slot and owner are not part of that -- the destination keeps its own.
    """
    return {
        "CharacterID": pal.CharacterID,
        "IconKey": DataProvider.get_pal_icon_key(pal.CharacterID),
        "DisplayName": pal.DisplayName,
        "NickName": pal.NickName or "",
        "Gender": pal.Gender.value if pal.Gender else None,
        "Level": pal.Level or 1,
        "Exp": pal.Exp or 0,
        "Rank": pal.Rank or 1,
        "FriendshipLevel": pal.FriendshipLevel or 0,
        "FavoriteIndex": pal.FavoriteIndex,
        "IsBOSS": pal.IsBOSS,
        "IsRarePal": bool(pal.IsRarePal),
        "IsAwakening": pal.IsAwakening,
        "IsImportedCharacter": pal.IsImportedCharacter,
        "Talent_HP": pal.Talent_HP or 0,
        "Talent_Melee": pal.Talent_Melee or 0,
        "Talent_Shot": pal.Talent_Shot or 0,
        "Talent_Defense": pal.Talent_Defense or 0,
        "Rank_HP": pal.Rank_HP or 0,
        "Rank_Attack": pal.Rank_Attack or 0,
        "Rank_Defence": pal.Rank_Defence or 0,
        "Rank_CraftSpeed": pal.Rank_CraftSpeed or 0,
        "ComputedMaxHP": pal.ComputedMaxHP,
        "ComputedAttack": pal.ComputedAttack,
        "ComputedDefense": pal.ComputedDefense,
        "ComputedCraftSpeed": pal.ComputedCraftSpeed,
        "Suitabilities": pal.WorkSuitabilities or {},
        "EquipWaza": pal.EquipWaza or [],
        "PassiveSkillList": pal.PassiveSkillList or [],
    }


def brief_field_changes(incoming: PalEntity, existing: PalEntity) -> dict:
    """Only what differs, so the dialog can show what is actually at stake."""
    incoming_data = pal_brief(incoming)
    existing_data = pal_brief(existing)
    return {
        key: {"Incoming": value, "Existing": existing_data.get(key)}
        for key, value in incoming_data.items()
        if value != existing_data.get(key)
    }


def _candidate(manager: SaveManager, record: PalRecord) -> dict:
    """One Pal the user could be about to overwrite, named well enough to pick."""
    location = manager.storage_directory.resolve_record_location(record)
    return {
        "recordKey": record.record_key,
        "storageKey": record.storage_key,
        "SlotIndex": record.slot_index,
        "label": location["ContainerLabel"],
    }


def conflict_details(
    manager: SaveManager, source: PalRecord, candidates: list[PalRecord]
) -> dict:
    """The conflict payload: what is arriving, what it would replace, and the diff.

    `existing` and `fieldChanges` are filled only when there is exactly one candidate.
    With several, the backend has no basis for picking one and the user answers with
    a candidate from the list instead.
    """
    locked = candidates[0] if len(candidates) == 1 else None
    return {
        "incoming": pal_brief(source.pal),
        "existing": pal_brief(locked.pal) if locked else None,
        "fieldChanges": brief_field_changes(source.pal, locked.pal) if locked else {},
        "candidates": [_candidate(manager, record) for record in candidates],
    }


def _expected_target(payload: dict):
    """The one existing Pal the user confirmed overwriting, if they were asked.

    Present only in a GPS identity-conflict confirmation -- it is not a field DPS
    records carry, and nothing else in a transfer request names a second Pal.
    """
    resolution = payload.get("conflictResolution")
    if not isinstance(resolution, dict):
        return None
    return resolution.get("expectedTarget")


def _unique(keys) -> list:
    return [key for key in dict.fromkeys(keys) if key]


@pal_transfers_blueprint.route("", methods=["POST"])
@jwt_required()
def create_pal_transfer():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ApiError("PAL_TRANSFER_INVALID", "Request body must be an object")
    source_record_key = payload.get("sourceRecordKey")
    target_storage_key = payload.get("targetStorageKey")
    if not source_record_key or not target_storage_key:
        raise ApiError(
            "PAL_TRANSFER_INVALID",
            "sourceRecordKey and targetStorageKey are required",
        )

    manager = SaveManager()
    with manager.session_lock:
        source = require_record(source_record_key)
        # Read before the move: afterwards the record may be somewhere else, or the
        # key may name nothing at all, and the client still has to refresh the list
        # the Pal left.
        source_roster_key = roster_key_for_record(manager, source)
        source_storage_key = source.storage_key
        try:
            outcome = manager.pal_mutations.transfer(
                source_record_key, target_storage_key, _expected_target(payload)
            )
        except PalIdentityConflict as conflict:
            raise ApiError(
                "PAL_IDENTITY_CONFLICT",
                "This identity already exists in the destination",
                status=409,
                details=conflict_details(manager, source, conflict.candidates),
            )
        except PalOperationRefused as refusal:
            # Every refusal is the save's current state saying no -- a full target, a
            # stale one, a Pal that is not where it says it is -- so they are all the
            # same kind of answer and all carry their own code.
            raise ApiError(refusal.code, str(refusal), status=409)
        return operation_result(
            manager,
            outcome.record,
            deleted_record_keys=outcome.deleted_record_keys,
            affected_roster_keys=_unique(
                [source_roster_key, roster_key_for_record(manager, outcome.record)]
            ),
            affected_storage_keys=_unique(
                [source_storage_key, *outcome.affected_storage_keys]
            ),
        )
