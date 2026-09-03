"""One healing operation for the three buttons the editor shows (spec §8.3).

Curing an illness, reviving a fainted Pal and healing everything were three RPCs,
and the first two already called the same `PalEntity.heal_pal()`. There is one
resource here and a `scope`, because there is one behaviour.
"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from palworld_pal_editor.api.errors import ApiError, register_error_handlers
from palworld_pal_editor.api.pals import (
    commit_pal_edit,
    operation_result,
    require_record,
)
from palworld_pal_editor.api.rosters import roster_entries
from palworld_pal_editor.core import SaveManager

pal_heals_blueprint = Blueprint("pal_heals", __name__)
register_error_handlers(pal_heals_blueprint)


@pal_heals_blueprint.route("", methods=["POST"])
@jwt_required()
def heal_pals():
    payload = request.get_json(silent=True)
    scope = payload.get("scope") if isinstance(payload, dict) else None
    manager = SaveManager()
    with manager.session_lock:
        if scope == "all":
            manager.pal_mutations.heal_all()
            # Every list on screen now shows different sickness and faint badges,
            # and no single record can say so. Naming the rosters is how a healed
            # Pal three lists away stops being drawn as sick.
            return operation_result(
                manager,
                affected_roster_keys=[
                    entry["rosterKey"] for entry in roster_entries(manager)
                ],
            )
        if scope == "record":
            record_key = payload.get("recordKey")
            if not isinstance(record_key, str) or not record_key:
                raise ApiError("HEAL_RECORD_MISSING", "recordKey is required")
            record = require_record(record_key)
            record.pal.heal_pal()
            return commit_pal_edit(manager, record)
        raise ApiError("HEAL_SCOPE_INVALID", 'scope must be "record" or "all"')
