"""What is left of the pre-REST Pal blueprint: containers and the move.

Everything else this file held -- create, duplicate, delete, raw export and the
two kinds of template -- is gone, replaced by the resources under `/api/pals`,
`/api/storages` and `/api/pal-templates`. The three routes below are the last
callers of the old `reply(status, data, msg)` envelope; S4a and S4b delete them
along with this file when the transfer becomes an operation resource.
"""

import traceback

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from palworld_pal_editor.api.pals import guid_string_or_none as _guid_string_or_none
from palworld_pal_editor.core import PalEntity, PalIdentityConflict, SaveManager
from palworld_pal_editor.utils import LOGGER, DataProvider
from palworld_pal_editor.utils.util import reply

pal_blueprint = Blueprint("pal", __name__)


@pal_blueprint.route("/containers", methods=["GET"])
@jwt_required()
def list_pal_containers():
    return reply(0, SaveManager().get_container_registry())


@pal_blueprint.route("/creation_targets/<path:roster_key>", methods=["GET"])
@jwt_required()
def list_pal_creation_targets(roster_key):
    return reply(0, SaveManager().creation_targets(roster_key))


@pal_blueprint.route("/transfer", methods=["POST"])
@jwt_required()
def move_pal():
    payload = request.json or {}
    source_record_key = payload.get("SourceRecordKey")
    target_storage_key = payload.get("TargetStorageKey")
    if not source_record_key or not target_storage_key:
        return reply(
            1,
            None,
            "SourceRecordKey and TargetStorageKey are required.",
        )
    try:
        manager = SaveManager()
        source = manager.get_record(source_record_key)
        result = manager.transfer_pal(
            source_record_key,
            target_storage_key,
            payload.get("Action", "move"),
            payload.get("ExpectedTargetRecordKey"),
        )
        # The Pal list's edited marker is `changeState` alone since S2b, so a move
        # that does not register itself is a move that leaves no mark. S4a takes
        # this over when the transfer becomes an operation resource.
        manager.pal_repository.mark_modified(manager.get_record(result["RecordKey"]))
        return reply(0, result)
    except PalIdentityConflict as conflict:
        locked = conflict.candidates[0] if len(conflict.candidates) == 1 else None
        return reply(
            1,
            {
                "Code": "PAL_IDENTITY_CONFLICT",
                "Incoming": _pal_brief(source.pal) if source else None,
                "Candidates": [
                    _record_location(manager, candidate)
                    for candidate in conflict.candidates
                ],
                "LockedTarget": locked.record_key if locked else None,
                "Existing": _pal_brief(locked.pal) if locked else None,
                "FieldChanges": (
                    _brief_field_changes(source.pal, locked.pal)
                    if source and locked
                    else {}
                ),
            },
            "This genetic identity already exists.",
        )
    except ValueError as error:
        return reply(1, None, str(error))
    except Exception:
        LOGGER.error(f"Error transferring Pal: {traceback.format_exc()}")
        return reply(1, None, "Error transferring Pal. No changes were kept.")


def _pal_brief(pal: PalEntity) -> dict:
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


def _brief_field_changes(incoming: PalEntity, existing: PalEntity) -> dict:
    incoming_data = _pal_brief(incoming)
    existing_data = _pal_brief(existing)
    return {
        key: {"Incoming": value, "Existing": existing_data.get(key)}
        for key, value in incoming_data.items()
        if value != existing_data.get(key)
    }


def _record_location(manager: SaveManager, record) -> dict:
    location = manager.resolve_record_location(record)
    return {
        "RecordKey": record.record_key,
        "StorageKey": record.storage_key,
        "StorageKind": record.storage_kind,
        "StorageOwnerPlayerUid": record.storage_owner_uid,
        "InstanceId": str(record.pal.InstanceId),
        "OwnerPlayerUId": _guid_string_or_none(record.pal.OwnerPlayerUId),
        "ContainerLabel": location["ContainerLabel"],
        "SlotIndex": location["SlotIndex"],
    }
