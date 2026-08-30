"""Creating a Pal in one storage, whatever it is being made from (spec §5.4, §8.3).

Default, template and pasted native JSON differ only in where the gameplay payload
comes from. Each is reduced to one complete `SaveParameter` before anything exists,
and the target storage builds its own native record around it -- which is why a
template taken out of the Global Palbox can be created into a player's Palbox
without either format knowing about the other.

S4a adds `POST /api/pal-transfers` beside this: moving a Pal is the same adapters
and a different commit semantic.
"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from palworld_pal_editor.api.errors import ApiError, register_error_handlers
from palworld_pal_editor.api.pals import operation_result
from palworld_pal_editor.api.roster_keys import (
    PLAYER_ROSTER_PREFIX,
    legacy_roster_id,
    roster_key_for_record,
)
from palworld_pal_editor.api.templates import require_pal_template
from palworld_pal_editor.core import SaveManager
from palworld_pal_editor.core.pal_sources import detach_native_record
from palworld_pal_editor.core.pal_templates import template_source

storages_blueprint = Blueprint("storages", __name__)
register_error_handlers(storages_blueprint)


def _creation_roster_key(descriptor: dict, owner_uid) -> str:
    """Which list the new Pal turns up in, and therefore whose targets are legal.

    The storage answers it wherever the storage is a place rather than a person:
    the Global Palbox and a base camp's container belong to no player. Everywhere
    else the new Pal is the requesting player's, which is the whole of what
    `ownerUid` decides.
    """
    if descriptor["StorageKind"] == "global_palbox":
        return "global-palbox"
    if descriptor["ContainerKind"] == "base":
        return "base-workers"
    if not owner_uid:
        raise ApiError(
            "PAL_OWNER_REQUIRED",
            "ownerUid is required to create a Pal in this storage",
        )
    return f"{PLAYER_ROSTER_PREFIX}{owner_uid}"


def _source_parameter(source) -> dict | None:
    """The complete gameplay payload the new Pal is copied from, or None for default.

    Every kind ends as one `SaveParameter` and nothing else: no source contributes
    identity, owner, guild or position, because those belong to wherever the Pal is
    about to land (spec §6.3).
    """
    if not isinstance(source, dict):
        raise ApiError("PAL_SOURCE_INVALID", 'source must be an object with a "kind"')
    kind = source.get("kind")
    if kind == "default":
        return None
    if kind == "template":
        template = require_pal_template(source.get("templateId"))
        try:
            return template_source(template).save_parameter
        except Exception as error:
            raise ApiError("PAL_TEMPLATE_UNREADABLE", str(error))
    if kind == "native-record":
        try:
            return detach_native_record(source.get("record")).save_parameter
        except ValueError as error:
            raise ApiError("PAL_RECORD_UNRECOGNISED", str(error))
    raise ApiError(
        "PAL_SOURCE_KIND_UNKNOWN",
        f"No Pal source kind named {kind}",
        details={"kinds": ["default", "template", "native-record"]},
    )


@storages_blueprint.route("/<storage_key>/pals", methods=["POST"])
@jwt_required()
def create_storage_pal(storage_key: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ApiError("PAL_CREATE_INVALID", "Request body must be an object")

    manager = SaveManager()
    with manager.session_lock:
        descriptor = manager.get_storage_descriptor(storage_key)
        if descriptor is None:
            raise ApiError(
                "STORAGE_NOT_FOUND",
                f"No storage named {storage_key}",
                status=404,
            )
        save_parameter = _source_parameter(payload.get("source"))
        roster_key = _creation_roster_key(descriptor, payload.get("ownerUid"))
        try:
            record = manager.create_pal(
                legacy_roster_id(roster_key),
                descriptor["StorageKey"],
                save_parameter,
            )
        except ValueError as error:
            # Full containers, a target that is not this roster's to write into,
            # and a missing Global Palbox all arrive here; the client shows what
            # the message says rather than re-deriving which one happened.
            raise ApiError("PAL_CREATE_REFUSED", str(error))
        return operation_result(
            manager,
            record,
            affected_roster_keys=[roster_key_for_record(manager, record)],
            affected_storage_keys=[record.storage_key],
        )
