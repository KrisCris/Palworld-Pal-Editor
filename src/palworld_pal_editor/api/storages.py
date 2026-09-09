"""Creating a Pal in one storage, whatever it is being made from.

Default, template and pasted native JSON differ only in where the gameplay payload
comes from. Each is reduced to one complete `SaveParameter` before anything exists,
and the target storage builds its own native record around it -- which is why a
template taken out of the Global Palbox can be created into a player's Palbox
without either format knowing about the other.

`POST /api/pal-transfers` sits beside this: moving a Pal is the same adapters and a
different commit semantic. What this module adds for it is the storage directory the
move dialog renders, and the contextual capability that says -- for one Pal and one
target -- whether it may go and what would happen if it did.
"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from palworld_pal_editor.api.errors import ApiError, register_error_handlers
from palworld_pal_editor.api.operations import operation_result, require_pal_template
from palworld_pal_editor.api.roster_keys import (
    PLAYER_ROSTER_PREFIX,
    UNROSTERED,
    core_roster_key,
    roster_key_for_record,
    roster_key_for_target,
)
from palworld_pal_editor.core import SaveManager
from palworld_pal_editor.core.storage_directory import StorageDescriptor
from palworld_pal_editor.core.pal_mutations import UPDATE_EXISTING
from palworld_pal_editor.core.pal_import import detach_native_record
from palworld_pal_editor.core.templates import template_source

storages_blueprint = Blueprint("storages", __name__)
register_error_handlers(storages_blueprint)


# Where a storage sits in the move dialog's navigation. The frontend renders these
# and does not re-derive them from a storage kind. A group whose label is
# None is one of the two fixed groups the frontend has its own translated text for,
# since a label invented here would be untranslatable English in the UI.
GLOBAL_PALBOX_GROUP = "global-palbox"
BASES_GROUP = "bases"
OTHER_GROUP = "other"

# Within one group. The same order the container registry has always listed in.
ROLE_ORDER_WITHIN_GROUP = {
    "party": 0,
    "storage": 1,
    "dps": 2,
    "special": 3,
    "base": 4,
    "unknown": 5,
}

# What kind of place a storage is, as an i18n key rather than as English. The
# registry's own `storage_label` is composed in English ("Alice · Palbox"), so a
# frontend that rendered it would show untranslated text in every other locale --
# and one that re-derived the wording from `storageKind` would be the branching
# this removes. So the descriptor splits the label in two: `label` is the data
# half (a nickname, a base's name), and `labelKey`/`labelArgs` name the translated
# half the frontend already has.
CONTAINER_LABEL_KEYS = {
    "party": "Editor_Container_Party",
    "storage": "Editor_Container_Palbox",
    "dps": "Editor_Container_DimensionalPalStorage",
    "global_palbox": "Editor_Container_GlobalPalbox",
}


def _label(descriptor: StorageDescriptor) -> tuple:
    """`(label, labelKey, labelArgs)` -- the data half, then the translated half."""
    kind = descriptor.storage_role
    if kind == "base":
        if descriptor.base_ordinal:
            return None, "Editor_Container_Base", [descriptor.base_ordinal]
        return descriptor.base_name or descriptor.storage_label, None, []
    if kind == "special":
        # A viewing cage belongs to the guild rather than to a player, and is the
        # one special container with a name of its own.
        if descriptor.shared:
            return None, "Editor_Container_ViewingCage", []
        return (
            descriptor.owner_name,
            "Editor_Container_Special",
            [descriptor.slot_count],
        )
    if kind == "unknown":
        return None, "Editor_Container_Unknown", [descriptor.slot_count]
    label_key = CONTAINER_LABEL_KEYS.get(kind)
    if label_key is None:
        return descriptor.storage_label, None, []
    return descriptor.owner_name, label_key, []


def _creation_roster_key(descriptor: StorageDescriptor, owner_uid) -> str:
    """Which list the new Pal turns up in, and therefore whose targets are legal."""
    roster_key = roster_key_for_target(descriptor, owner_uid)
    if roster_key == UNROSTERED:
        # A Pal created here would belong to no list and appear nowhere. A Pal that
        # is *moved* there may, because it came from a list the user was looking at.
        raise ApiError(
            "PAL_OWNER_REQUIRED",
            "ownerUid is required to create a Pal in this storage",
        )
    return roster_key


def _navigation(descriptor: StorageDescriptor, order: dict) -> tuple:
    if descriptor.storage_kind == "global_palbox":
        # Null like the bases group: "Global Palbox" is a phrase the frontend has
        # translated, not a name this save holds.
        return GLOBAL_PALBOX_GROUP, None, 0
    if descriptor.storage_role == "base":
        return BASES_GROUP, None, 1
    owner_uid = descriptor.owner_player_uid
    if owner_uid in order:
        return (
            f"{PLAYER_ROSTER_PREFIX}{owner_uid}",
            descriptor.owner_name,
            2 + order[owner_uid],
        )
    return OTHER_GROUP, None, 99


def player_order(manager: SaveManager) -> dict:
    """Which player's group comes first, so the dialog lists them as the UI does."""
    return {
        str(player.PlayerUId): index
        for index, player in enumerate(manager.get_players())
    }


def storage_descriptor(descriptor: StorageDescriptor, order: dict) -> dict:
    """One place a Pal can be, as the move dialog needs it.

    Generated from the containers, players and repository indexes that already exist,
    every time it is asked for: there is no second directory of storages being kept
    in step with the first.

    `label` carries only what is data -- a nickname, a base's name -- and is null
    where the whole name is a translated phrase; see `_label`.
    """
    group_key, group_label, group_order = _navigation(descriptor, order)
    label, label_key, label_args = _label(descriptor)
    return {
        "storageKey": descriptor.storage_key,
        "storageKind": descriptor.storage_kind,
        "label": label,
        "labelKey": label_key,
        "labelArgs": label_args,
        "navigationGroupKey": group_key,
        "navigationGroupLabel": group_label,
        "navigationGroupOrder": group_order,
        "order": ROLE_ORDER_WITHIN_GROUP.get(descriptor.storage_role, 99),
        "capacity": descriptor.slot_count,
        "occupied": descriptor.occupied,
        "ownerPlayerUid": descriptor.owner_player_uid,
        "containerId": descriptor.ContainerId,
    }


def require_descriptor(manager: SaveManager, storage_key: str) -> StorageDescriptor:
    descriptor = manager.storage_directory.descriptor(storage_key)
    if descriptor is None:
        raise ApiError(
            "STORAGE_NOT_FOUND",
            f"No storage named {storage_key}",
            status=404,
        )
    return descriptor


def transfer_capability(manager: SaveManager, plan) -> dict:
    """What sending one Pal to one storage would do, before anything is done.

    `resultRosterKey` is the list the Pal ends up in, so the client can refresh it
    without guessing. For an overwrite that is the destination's list, because the
    destination is the Pal that survives.
    """
    if not plan.allowed:
        return {
            "allowed": False,
            "effect": None,
            "reason": plan.reason,
            "resultRosterKey": None,
        }
    roster_key = (
        roster_key_for_record(manager, plan.candidates[0])
        if plan.effect == UPDATE_EXISTING
        else roster_key_for_target(plan.descriptor, plan.owner_uid)
    )
    return {
        "allowed": True,
        "effect": plan.effect,
        "reason": None,
        "resultRosterKey": roster_key,
    }


@storages_blueprint.route("", methods=["GET"])
@jwt_required()
def list_storages():
    """Every place a Pal can be, including the ones nothing may be moved into."""
    manager = SaveManager()
    with manager.session_lock:
        order = player_order(manager)
        return [
            storage_descriptor(descriptor, order)
            for descriptor in manager.storage_directory.registry()
        ]


@storages_blueprint.route("/<storage_key>", methods=["GET"])
@jwt_required()
def get_storage(storage_key: str):
    manager = SaveManager()
    with manager.session_lock:
        return storage_descriptor(
            require_descriptor(manager, storage_key), player_order(manager)
        )


@storages_blueprint.route("/<storage_key>/pal-transfer-capability", methods=["GET"])
@jwt_required()
def get_pal_transfer_capability(storage_key: str):
    """Whether this Pal may go to this storage, asked per Pal and per target.

    Static `MovableInto` cannot answer it: whether a move is allowed depends on the
    Pal's guild, its owner, whether the target already holds its identity, and
    whether the Pal is in the slot it records for itself. So the dialog asks about
    the pair rather than about the target alone.
    """
    source_record_key = request.args.get("sourceRecordKey")
    if not source_record_key:
        raise ApiError(
            "PAL_SOURCE_REQUIRED", "sourceRecordKey is a required query parameter"
        )
    manager = SaveManager()
    with manager.session_lock:
        require_descriptor(manager, storage_key)
        return transfer_capability(
            manager,
            manager.pal_mutations.capability(source_record_key, storage_key),
        )


def _source_parameter(source) -> dict | None:
    """The complete gameplay payload the new Pal is copied from, or None for default.

    Every kind ends as one `SaveParameter` and nothing else: no source contributes
    identity, owner, guild or position, because those belong to wherever the Pal is
    about to land.
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
        descriptor = manager.storage_directory.descriptor(storage_key)
        if descriptor is None:
            raise ApiError(
                "STORAGE_NOT_FOUND",
                f"No storage named {storage_key}",
                status=404,
            )
        save_parameter = _source_parameter(payload.get("source"))
        roster_key = _creation_roster_key(descriptor, payload.get("ownerUid"))
        try:
            record = manager.pal_mutations.create(
                core_roster_key(roster_key),
                descriptor.storage_key,
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
