"""What is left of the pre-REST Pal blueprint: the move.

Everything else this file held -- create, duplicate, delete, raw export, the two
kinds of template, the container registry and the creation-target list -- is gone,
replaced by the resources under `/api/pals`, `/api/storages`, `/api/rosters` and
`/api/pal-templates`. The move has a resource too, in `api/pal_transfers.py`, and
the dialogs call it; this route is the last caller of the old
`reply(status, data, msg)` envelope and S4c deletes this file with the chain
behind it.
"""

import traceback

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from palworld_pal_editor.api.pal_transfers import brief_field_changes, pal_brief
from palworld_pal_editor.api.pals import guid_string_or_none as _guid_string_or_none
from palworld_pal_editor.core import PalIdentityConflict, SaveManager
from palworld_pal_editor.utils import LOGGER
from palworld_pal_editor.utils.util import reply

pal_blueprint = Blueprint("pal", __name__)


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
                "Incoming": pal_brief(source.pal) if source else None,
                "Candidates": [
                    _record_location(manager, candidate)
                    for candidate in conflict.candidates
                ],
                "LockedTarget": locked.record_key if locked else None,
                "Existing": pal_brief(locked.pal) if locked else None,
                "FieldChanges": (
                    brief_field_changes(source.pal, locked.pal)
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
