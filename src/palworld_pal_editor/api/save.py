from flask import Blueprint, jsonify, request

from palworld_pal_editor.config import Config
from palworld_pal_editor.core import SaveManager
from palworld_pal_editor.utils import LOGGER, DataProvider
from palworld_pal_editor.api.util import reply

save_blueprint = Blueprint("save", __name__)


@save_blueprint.route("/load", methods=["POST"])
# @LOGGER.api_logger
def load():
    path = request.json.get("SavePath", None)
    path = path or Config.path
    if path and SaveManager().open(f"{path}/Level.sav"):
        workingpals = SaveManager().get_working_pals()
        return reply(
            0,
            {
                "players": [
                    {"id": str(player.PlayerUId), "name": player.NickName}
                    for player in SaveManager().get_players()
                ],
                "hasWorkingPal": (True if len(workingpals) else False),
            },
        )
    return reply(1, None, "Failed to load, check path")


@save_blueprint.route("/passive_skills", methods=["GET"])
def get_passive_skills():
    passives_raw = DataProvider.get_sorted_passives()
    passives = [
        {
            "InternalName": passive["InternalName"],
            "I18n": DataProvider.get_passive_i18n(passive["InternalName"]),
            "Rating": passive["Rating"],
        }
        for passive in passives_raw
    ]
    passives.reverse()

    return reply(0, passives)


@save_blueprint.route("/active_skills", methods=["GET"])
def get_active_skills():
    attacks_raw = DataProvider.get_sorted_attacks()
    attacks = [
        {
            "InternalName": attack["InternalName"],
            "I18n": DataProvider.get_attack_i18n(attack["InternalName"]),
            "Power": attack["Power"],
            "Element": attack["Element"],
        }
        for attack in attacks_raw
    ]
    return reply(0, attacks)
