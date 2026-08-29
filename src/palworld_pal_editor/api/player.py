import traceback

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from palworld_pal_editor.api.pals import guid_string_or_none as _guid_string_or_none
from palworld_pal_editor.api.players import player_resource as player_to_dict
from palworld_pal_editor.core import SaveManager
from palworld_pal_editor.utils import LOGGER, DataProvider
from palworld_pal_editor.utils.util import reply

player_blueprint = Blueprint("player", __name__)



@player_blueprint.route("/player_pals", methods=["POST"])
@jwt_required()
def get_player_pals():
    roster_key = request.json.get("RosterKey") or request.json.get("PlayerUId")
    manager = SaveManager()

    if roster_key in ("PAL_GLOBAL_STORAGE_BTN", "PAL_BASE_WORKER_BTN"):
        # Both come back in the order their own list displays: slot order for the
        # Global Palbox, base-worker order for the camps.
        records = manager.records_for_roster(roster_key)
    else:
        if not manager.get_player(roster_key):
            return reply(1, None, f"Player {roster_key} Not Found")
        records = manager.sorted_records_for_roster(roster_key)

    def pal_to_summary(record):
        pal = record.pal
        location = manager.resolve_record_location(record)
        return {
            "RecordKey": record.record_key,
            "InstanceId": str(pal.InstanceId) if pal.InstanceId else None,
            "StorageKey": record.storage_key,
            "StorageKind": record.storage_kind,
            "StorageOwnerPlayerUid": record.storage_owner_uid,
            "OwnerPlayerUid": _guid_string_or_none(pal.OwnerPlayerUId),
            "IconAccessKey": pal.IconAccessKey or None,
            "DataAccessKey": pal.DataAccessKey or None,
            "I18nName": pal.I18nName or None,
            "DisplayName": pal.DisplayName or None,
            "Gender": pal.Gender.value if pal.Gender else None,
            "IsTower": pal.IsTower or False,
            "IsBOSS": pal.IsBOSS or False,
            "IsRarePal": pal.IsRarePal or False,
            "IsAwakening": pal.IsAwakening,
            "IsImportedCharacter": pal.IsImportedCharacter,
            "IsHuman": pal.IsHuman,
            "IsNewPal": manager.pal_repository.is_created(record),
            "ContainerId": location["ContainerId"],
            "SlotIndex": location["SlotIndex"],
            "ContainerKind": location["ContainerKind"],
            "ContainerLabel": location["ContainerLabel"],
            "FavoriteIndex": pal.FavoriteIndex,
            "IsExpeditionPal": pal.IsExpeditionPal,
            "in_owner_palbox": pal.in_owner_palbox,
        }

    return reply(
        0,
        [pal_to_summary(record) for record in records if record is not None],
    )


@player_blueprint.route("/players_data", methods=["GET"])
@jwt_required()
def get_player_list():
    workingpals = SaveManager().get_working_pals()
    players = SaveManager().get_players()
    if not players:
        return reply(1, None, "No Player Found")
    return reply(
        0,
        {
            "players": [
                player_to_dict(player) for player in SaveManager().get_players()
            ],
            "hasWorkingPal": (True if len(workingpals) else False),
            "containers": SaveManager().get_container_registry(),
            "specialRosters": (
                [
                    {
                        "RosterKey": "PAL_GLOBAL_STORAGE_BTN",
                        "Kind": "global_palbox",
                        "Label": (
                            DataProvider.get_tech_name("GlobalPalStorage")
                            or "Global Palbox"
                        ),
                    }
                ]
                if SaveManager().has_global_palbox
                else []
            ),
            "warnings": list(getattr(SaveManager(), "load_warnings", [])),
        },
    )


@player_blueprint.route("/player_data", methods=["POST"])
@jwt_required()
def get_player_data():
    PlayerUId = request.json.get("PlayerUId")

    if PlayerUId == "PAL_BASE_WORKER_BTN":
        LOGGER.warning(f"PAL_BASE_WORKER_BTN is not a real player")
        return reply(1, None, f"PAL_BASE_WORKER_BTN is not a real player")

    player_entity = SaveManager().get_player(PlayerUId)
    if not player_entity:
        LOGGER.warning(f"Player {PlayerUId} not exist")
        return reply(1, None, f"Player {PlayerUId} not exist")

    return reply(0, player_to_dict(player_entity))


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
