from flask import Blueprint, jsonify, request
from palworld_pal_editor.api.util import reply

from palworld_pal_editor.core import SaveManager
from palworld_pal_editor.utils import DataProvider

player_blueprint = Blueprint("player", __name__)

@player_blueprint.route("/player_pals", methods=["POST"])
def get_player_pals():
    id = request.json.get("PlayerUId")
    player_entity = SaveManager().get_player(id)
    if not player_entity:
        return reply(1, None, f"Player {id} Not Found")
    pals = player_entity.get_sorted_pals()

    # holyshit, I hate this piece of shit
    return reply(0, [{
        "InstanceId": str(pal.InstanceId) if pal.InstanceId else None,
        "I18nName": pal.I18nName or None,
        "DisplayName": pal.DisplayName or None,
        "Gender": str(pal.Gender) if pal.Gender else None,
        "IsBOSS": pal.IsBOSS or None,
        "IsRarePal": pal.IsRarePal or None,
        "IsTower": pal.IsTower or None,
        "Level": pal.Level or None,
        "DataAccessKey": pal.DataAccessKey or None,
        "IconAccessKey": pal.IconAccessKey or None
    } for pal in pals])
