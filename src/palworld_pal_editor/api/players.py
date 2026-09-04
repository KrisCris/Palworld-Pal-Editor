"""Player resources (spec §8.2).

One serializer for both the list and a single player: the player page and the
player list read the same fields, and a second shape would only be a second thing
to keep in step. Every write answers with that same resource, so the client never
has to follow an edit with a read to see what it did.

`PATCH /api/players/{playerUid}` writes only the fields named below. The route it
replaces took a `{key, value}` pair and, for anything it did not recognise, did
`setattr(player_entity, key, value)` after checking the attribute was a property
with a setter -- which is every settable field `PlayerEntity` has, named by the
client. The allowlist here is the same shape `PATCH /api/pals/{recordKey}` uses.
"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from palworld_pal_editor.api.errors import ApiError, register_error_handlers
from palworld_pal_editor.core import SaveManager
from palworld_pal_editor.core.pal_objects import PalObjects
from palworld_pal_editor.core.player_entity import PlayerEntity
from palworld_pal_editor.utils import DataProvider

players_blueprint = Blueprint("players", __name__)
register_error_handlers(players_blueprint)


def player_resource(player: PlayerEntity) -> dict:
    return {
        "InstanceId": str(player.PlayerUId),
        "GroupId": str(player.group_id) if player.group_id else None,
        "NickName": player.NickName or "",
        "Level": player.Level or 1,
        "Exp": player.Exp or 0,
        "UnusedStatusPoint": player.UnusedStatusPoint or 0,
        "StatusPoints": player.StatusPoints,
        "ExStatusPoints": player.ExStatusPoints,
        "StatusPointTotals": player.StatusPointTotals,
        "StatusPointMinimums": player.StatusPointMinimums,
        "StatusPointMaximums": player.StatusPointMaximums,
        "StatusPointTotalMaximums": PalObjects.StatusPointMaximums,
        "StatusPointMetadata": DataProvider.get_player_status_data(),
        "HasViewingCage": player.has_viewing_cage(),
        "OtomoCharacterContainerId": str(player.OtomoCharacterContainerId),
        "PalStorageContainerId": str(player.PalStorageContainerId),
        "UnlockedRecipeTechnologyNames": player.UnlockedRecipeTechnologyNames or [],
        "TechnologyPoint": player.TechnologyPoint or 0,
        "bossTechnologyPoint": player.bossTechnologyPoint or 0,
    }


def require_player(player_uid: str) -> PlayerEntity:
    player = SaveManager().get_player(player_uid)
    if player is None:
        raise ApiError(
            "PLAYER_NOT_FOUND",
            f"No player named {player_uid}",
            status=404,
        )
    return player


@players_blueprint.route("", methods=["GET"])
@jwt_required()
def list_players():
    manager = SaveManager()
    with manager.session_lock:
        return [player_resource(player) for player in manager.get_players()]


@players_blueprint.route("/<player_uid>", methods=["GET"])
@jwt_required()
def get_player(player_uid: str):
    manager = SaveManager()
    with manager.session_lock:
        return player_resource(require_player(player_uid))


# Each of these is a `PlayerEntity` property whose setter already coerces and
# range-checks what it is handed, which is why nothing is validated again here:
# the save file's rules live next to the save file.
PLAYER_SCALAR_FIELDS = (
    "NickName",
    "Level",
    "UnusedStatusPoint",
    "TechnologyPoint",
    "bossTechnologyPoint",
)


def _set_status_points(player: PlayerEntity, value: dict) -> None:
    for name, points in value.items():
        player.set_StatusPoint(name, points)


def _set_status_point_totals(player: PlayerEntity, value: dict) -> None:
    for name, points in value.items():
        player.set_TotalStatusPoint(name, points)


def _set_unlocked_technologies(player: PlayerEntity, value: list) -> None:
    """Unlock what the client added and lock what it dropped.

    The client sends the list it wants, per §8.3's rule for skills, rather than
    one `add`/`remove` request per technology. The comparison is case-insensitive
    and re-uses the entity's own toggle, so a technology that was already
    unlocked keeps whatever spelling the save has for it -- replacing the array
    wholesale would rewrite those names to this catalog's casing and change bytes
    the user never touched.
    """
    desired = {tech.casefold(): tech for tech in value}
    unlocked = {
        tech.casefold(): tech
        for tech in player.UnlockedRecipeTechnologyNames or []
    }
    for key, tech in desired.items():
        if key not in unlocked:
            player.toggle_UnlockedRecipeTechnologyNames(tech, True)
    for key, tech in unlocked.items():
        if key not in desired:
            player.toggle_UnlockedRecipeTechnologyNames(tech, False)


PLAYER_WRITERS = {
    "StatusPoints": _set_status_points,
    "StatusPointTotals": _set_status_point_totals,
    "UnlockedRecipeTechnologyNames": _set_unlocked_technologies,
}
WRITABLE_PLAYER_FIELDS = frozenset(PLAYER_SCALAR_FIELDS) | set(PLAYER_WRITERS)


@players_blueprint.route("/<player_uid>", methods=["PATCH"])
@jwt_required()
def patch_player(player_uid: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ApiError("PLAYER_PATCH_INVALID", "Request body must be an object")

    unwritable = set(payload) - WRITABLE_PLAYER_FIELDS
    if unwritable:
        raise ApiError(
            "PLAYER_FIELD_UNKNOWN",
            f"Not an editable player field: {', '.join(sorted(unwritable))}",
            details={"writable": sorted(WRITABLE_PLAYER_FIELDS)},
        )

    manager = SaveManager()
    with manager.session_lock:
        player = require_player(player_uid)
        try:
            # Scalars first: `StatusPointTotals` spends and refunds unused points
            # as a side effect, so it has to see the value the request settled on.
            for field in PLAYER_SCALAR_FIELDS:
                if field in payload:
                    setattr(player, field, payload[field])
            for field, write in PLAYER_WRITERS.items():
                if field in payload:
                    write(player, payload[field])
        except (TypeError, ValueError, AttributeError) as error:
            raise ApiError("PLAYER_VALUE_INVALID", str(error))
        return player_resource(player)


@players_blueprint.route("/<player_uid>/inventory", methods=["GET"])
@jwt_required()
def get_player_inventory(player_uid: str):
    manager = SaveManager()
    with manager.session_lock:
        # The player is resolved first, as the PATCH below does: written the other
        # way round, `item_container_data` is read before `require_player` runs, so
        # asking with no save open raised on None instead of answering 404.
        player = require_player(player_uid)
        return manager.item_container_data.inventory_snapshot(player)


@players_blueprint.route("/<player_uid>/inventory/<int:slot_index>", methods=["PATCH"])
@jwt_required()
def patch_player_inventory_slot(player_uid: str, slot_index: int):
    """One slot, addressed by index within the container the body names.

    `slotIndex` alone does not identify a slot -- every container kind numbers its
    own from zero -- so `containerKind` travels in the body while the path stays
    the one §8.2 specifies. The answer is the whole inventory rather than the slot
    that changed: an equip can empty another slot, and the grid redrew from a
    fresh snapshot after every edit anyway.
    """
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ApiError("INVENTORY_PATCH_INVALID", "Request body must be an object")

    manager = SaveManager()
    with manager.session_lock:
        player = require_player(player_uid)
        try:
            manager.item_container_data.patch_slot(
                player,
                payload.get("containerKind"),
                slot_index,
                payload.get("itemId"),
                payload.get("count", 0),
                allow_overstack=bool(payload.get("allowOverstack", False)),
            )
        except ValueError as error:
            raise ApiError("INVENTORY_SLOT_INVALID", str(error))
        return manager.item_container_data.inventory_snapshot(player)


@players_blueprint.route(
    "/<player_uid>/inventory/<int:slot_index>/repairs", methods=["POST"]
)
@jwt_required()
def post_player_inventory_slot_repair(player_uid: str, slot_index: int):
    """Restore one worn item: full durability, full magazine.

    A sub-resource rather than a field on the PATCH above, for the same reason
    `POST /api/session/saves` is one: the PATCH replaces a slot, and a body that
    named no `itemId` would mean "empty this slot" rather than "repair it". Each
    POST here is one repair that happened.

    The answer is the whole inventory, as the slot PATCH's is.
    """
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ApiError("INVENTORY_REPAIR_INVALID", "Request body must be an object")

    manager = SaveManager()
    with manager.session_lock:
        player = require_player(player_uid)
        try:
            manager.item_container_data.repair_slot(
                player, payload.get("containerKind"), slot_index
            )
        except ValueError as error:
            raise ApiError("INVENTORY_REPAIR_REFUSED", str(error))
        return manager.item_container_data.inventory_snapshot(player)
