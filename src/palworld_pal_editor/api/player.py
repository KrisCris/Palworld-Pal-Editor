import traceback
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from palworld_pal_editor.api.util import reply

from palworld_pal_editor.core import SaveManager
from palworld_pal_editor.utils import LOGGER, DataProvider

player_blueprint = Blueprint("player", __name__)


@player_blueprint.route("/player_pals", methods=["POST"])
@jwt_required()
def get_player_pals():
    id = request.json.get("PlayerUId")
    if id == "PAL_BASE_WORKER_BTN":
        pals = SaveManager().get_working_pals()
    else:
        player_entity = SaveManager().get_player(id)
        if not player_entity:
            return reply(1, None, f"Player {id} Not Found")
        pals = player_entity.get_sorted_pals()

    # I hate this piece of shit
    return reply(
        0,
        [
            {
                "InstanceId": str(pal.InstanceId) if pal.InstanceId else None,
                # "OwnerPlayerUId": str(pal.OwnerPlayerUId) if pal.OwnerPlayerUId else None,
                # "OwnerName": pal.OwnerName or None,
                "IconAccessKey": pal.IconAccessKey or None,
                "DataAccessKey": pal.DataAccessKey or None,
                "I18nName": pal.I18nName or None,
                "DisplayName": pal.DisplayName or None,
                "Gender": pal.Gender.value if pal.Gender else None,
                # "IsTower": pal.IsTower or False,
                # "IsBOSS": pal.IsBOSS or False,
                # "IsRarePal": pal.IsRarePal or False,
                # "NickName": pal.NickName or "",
                # "Level": pal.Level or 1,
                # "Rank": pal.Rank.value if pal.Rank else 1,
                # "Rank_HP": pal.Rank_HP or 0,
                # "Rank_Attack": pal.Rank_Attack or 0,
                # "Rank_Defence": pal.Rank_Defence or 0,
                # "Rank_CraftSpeed": pal.Rank_CraftSpeed or 0,
                # "MaxHP": pal.MaxHP or None,
                # "ComputedAttack": pal.ComputedAttack or None,
                # "ComputedDefense": pal.ComputedDefense or None,
                # "PassiveSkillList": pal.PassiveSkillList or [],
                # "MasteredWaza": pal.MasteredWaza or [],
                # "Talent_HP": pal.Talent_HP or 0,
                # "Talent_Melee": pal.Talent_Melee or 0,
                # "Talent_Shot": pal.Talent_Shot or 0,
                # "Talent_Defense": pal.Talent_Defense or 0,
                "Is_Unref_Pal": pal.is_unreferenced_pal,
                "in_owner_palbox": pal.in_owner_palbox,
            }
            for pal in pals
        ],
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
                {
                    "id": str(player.PlayerUId),
                    "name": player.NickName,
                    "hasViewingCage": player.has_viewing_cage(),
                    "OtomoCharacterContainerId": str(player.OtomoCharacterContainerId),
                    "PalStorageContainerId": str(player.PalStorageContainerId)
                }
                for player in SaveManager().get_players()
            ],
            "hasWorkingPal": (True if len(workingpals) else False),
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

    return reply(
        0,
        {
            "id": str(player_entity.PlayerUId),
            "name": player_entity.NickName,
            "hasViewingCage": player_entity.has_viewing_cage(),
            "OtomoCharacterContainerId": str(player_entity.OtomoCharacterContainerId),
            "PalStorageContainerId": str(player_entity.PalStorageContainerId)
        },
    )


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
            case "unlock_viewing_cage":
                player_entity.unlock_viewing_cage()
            case _:
                pass
    except Exception as e:
        stack_trace = traceback.format_exc()
        LOGGER.error(f"Error in patching player data {stack_trace}")
        return reply(1, None, f"Error in patching player data {stack_trace}")
    return reply(0)
