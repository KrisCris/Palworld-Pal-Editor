import traceback

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from palworld_pal_editor.core import SaveManager
from palworld_pal_editor.utils import LOGGER
from palworld_pal_editor.utils.util import reply

player_blueprint = Blueprint("player", __name__)



@player_blueprint.route("/inventory", methods=["POST"])
@jwt_required()
def get_player_inventory():
    player_uid = request.json.get("PlayerUId")
    if player_uid == "PAL_BASE_WORKER_BTN":
        return reply(1, None, "PAL_BASE_WORKER_BTN is not a real player")
    player = SaveManager().get_player(player_uid)
    if not player:
        return reply(1, None, f"Player {player_uid} not exist")
    try:
        return reply(0, SaveManager().item_container_data.inventory_snapshot(player))
    except Exception:
        stack_trace = traceback.format_exc()
        LOGGER.error(f"Error reading player inventory {stack_trace}")
        return reply(1, None, "Unable to read this player's item containers")


@player_blueprint.route("/inventory_slot", methods=["PATCH"])
@jwt_required()
def patch_player_inventory_slot():
    player_uid = request.json.get("PlayerUId")
    container_kind = request.json.get("ContainerKind")
    slot_index = request.json.get("SlotIndex")
    item_id = request.json.get("ItemId")
    count = request.json.get("Count", 0)
    allow_overstack = bool(request.json.get("AllowOverstack", False))
    context = (
        f"player={player_uid} container={container_kind} slot={slot_index} "
        f"item={item_id} count={count} allow_overstack={allow_overstack}"
    )
    if player_uid == "PAL_BASE_WORKER_BTN":
        LOGGER.warning(f"Inventory slot update rejected: {context}; invalid player")
        return reply(1, None, "PAL_BASE_WORKER_BTN is not a real player")
    player = SaveManager().get_player(player_uid)
    if not player:
        LOGGER.warning(f"Inventory slot update rejected: {context}; player not found")
        return reply(1, None, f"Player {player_uid} not exist")
    LOGGER.info(f"Inventory slot update requested: {context}")
    try:
        slot = SaveManager().item_container_data.patch_slot(
            player,
            container_kind,
            slot_index,
            item_id,
            count,
            allow_overstack=allow_overstack,
        )
        LOGGER.info(f"Inventory slot update succeeded: {context}")
        return reply(0, slot)
    except ValueError as error:
        LOGGER.warning(f"Inventory slot update rejected: {context}; reason={error}")
        return reply(1, None, str(error))
    except Exception:
        stack_trace = traceback.format_exc()
        LOGGER.error(f"Inventory slot update failed: {context}\n{stack_trace}")
        return reply(1, None, "Unable to update this inventory slot")


@player_blueprint.route("/player_data", methods=["PATCH"])
@jwt_required()
def patch_player_data():
    PlayerUId = request.json.get("PlayerUId")
    key = request.json.get("key")
    value = request.json.get("value")

    if PlayerUId == "PAL_BASE_WORKER_BTN":
        LOGGER.warning(f"PAL_BASE_WORKER_BTN is not a real player")
        return reply(1, None, f"PAL_BASE_WORKER_BTN is not a real player")

    player_entity = SaveManager().get_player(PlayerUId)
    if not player_entity:
        LOGGER.warning(f"Player {PlayerUId} not exist")
        return reply(1, None, f"Player {PlayerUId} not exist")

    try:
        match key:
            case "toggle_UnlockedRecipeTechnologyNames":
                player_entity.toggle_UnlockedRecipeTechnologyNames(value["tech"], value["status"])
            case "unlock_all_techs":
                player_entity.unlock_all_techs()
            case "unlock_viewing_cage":
                player_entity.unlock_viewing_cage()
            case "set_StatusPoint":
                player_entity.set_StatusPoint(value["name"], value["points"])
            case "set_TotalStatusPoint":
                player_entity.set_TotalStatusPoint(value["name"], value["points"])
            case _:
                field = getattr(type(player_entity), key, None)
                if not isinstance(field, property) or field.fset is None:
                    return reply(1, None, f"Unsupported player field: {key}")
                setattr(player_entity, key, value)
    except Exception as e:
        stack_trace = traceback.format_exc()
        LOGGER.error(f"Error in patching player data {stack_trace}, key: {key}, value: {value}")
        return reply(1, None, f"Error in patching player data {stack_trace}")
    return reply(0)
