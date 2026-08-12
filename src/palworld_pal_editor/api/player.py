import traceback

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from palworld_pal_editor.core import SaveManager
from palworld_pal_editor.core.pal_objects import PalObjects
from palworld_pal_editor.core.player_entity import PlayerEntity
from palworld_pal_editor.utils import LOGGER, DataProvider
from palworld_pal_editor.utils.util import reply

player_blueprint = Blueprint("player", __name__)


def _pal_location(manager, pal, party_container_id=None, storage_container_id=None):
    resolver = getattr(manager, "resolve_pal_location", None)
    if resolver is not None:
        return resolver(pal)
    return {
        "RecordedContainerId": str(pal.ContainerId) if pal.ContainerId else None,
        "RecordedSlotIndex": pal.SlotIndex,
        "ActualContainerId": str(pal.ContainerId) if pal.ContainerId else None,
        "ActualSlotIndex": pal.SlotIndex,
        "ActualLocations": [],
        "LocationStatus": "ok",
        "LocationAnomaly": None,
        "ContainerKind": (
            "party"
            if pal.ContainerId == party_container_id
            else "storage"
            if pal.ContainerId == storage_container_id
            else "other"
        ),
        "ContainerLabel": None,
    }


@player_blueprint.route("/player_pals", methods=["POST"])
@jwt_required()
def get_player_pals():
    id = request.json.get("PlayerUId")
    manager = SaveManager()
    player_entity = None
    if id == "PAL_BASE_WORKER_BTN":
        pals = manager.get_working_pals()
    else:
        player_entity = manager.get_player(id)
        if not player_entity:
            return reply(1, None, f"Player {id} Not Found")
        pals = player_entity.get_sorted_pals()

    party_container_id = (
        player_entity.OtomoCharacterContainerId if player_entity else None
    )
    storage_container_id = (
        player_entity.PalStorageContainerId if player_entity else None
    )

    def pal_to_summary(pal):
        location = _pal_location(
            manager, pal, party_container_id, storage_container_id
        )
        return {
            "InstanceId": str(pal.InstanceId) if pal.InstanceId else None,
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
            "IsNewPal": pal.is_new_pal,
            "ContainerId": location["RecordedContainerId"],
            "SlotIndex": location["RecordedSlotIndex"],
            "ActualContainerId": location["ActualContainerId"],
            "ActualSlotIndex": location["ActualSlotIndex"],
            "ActualLocations": location["ActualLocations"],
            "LocationStatus": location["LocationStatus"],
            "LocationAnomaly": location["LocationAnomaly"],
            "ContainerKind": location["ContainerKind"],
            "ContainerLabel": location["ContainerLabel"],
            "FavoriteIndex": pal.FavoriteIndex,
            "IsExpeditionPal": pal.IsExpeditionPal,
            "Is_Unref_Pal": pal.is_unreferenced_pal,
            "in_owner_palbox": pal.in_owner_palbox,
        }

    return reply(
        0,
        [pal_to_summary(pal) for pal in pals],
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

    player_dict = player_to_dict(player_entity)
    player_dict["UnlockedRecipeTechnologyNames"] = (
        player_entity.UnlockedRecipeTechnologyNames or []
    )

    return reply(0, player_dict)


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
    if player_uid == "PAL_BASE_WORKER_BTN":
        return reply(1, None, "PAL_BASE_WORKER_BTN is not a real player")
    player = SaveManager().get_player(player_uid)
    if not player:
        return reply(1, None, f"Player {player_uid} not exist")
    try:
        slot = SaveManager().item_container_data.patch_slot(
            player,
            request.json.get("ContainerKind"),
            request.json.get("SlotIndex"),
            request.json.get("ItemId"),
            request.json.get("Count", 0),
            allow_overstack=bool(request.json.get("AllowOverstack", False)),
        )
        return reply(0, slot)
    except ValueError as error:
        return reply(1, None, str(error))
    except Exception:
        stack_trace = traceback.format_exc()
        LOGGER.error(f"Error patching player inventory slot {stack_trace}")
        return reply(1, None, "Unable to update this inventory slot")


def player_to_dict(player: PlayerEntity):
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
        "UnlockedRecipeTechnologyNames": [],
        "TechnologyPoint": player.TechnologyPoint or 0,
        "bossTechnologyPoint": player.bossTechnologyPoint or 0,
    }


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
