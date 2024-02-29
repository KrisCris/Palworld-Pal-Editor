from flask import Blueprint, jsonify, request

from palworld_pal_editor.config import Config
from palworld_pal_editor.core import SaveManager
from palworld_pal_editor.utils import LOGGER
from palworld_pal_editor.api.util import reply

save_blueprint = Blueprint("save", __name__)


@save_blueprint.route("/load", methods=["POST"])
# @LOGGER.api_logger
def load():
    path = request.json.get("SavePath", None)
    path = path or Config.path
    if path and SaveManager().open(f"{path}/Level.sav"):
        return reply(
            0,
            [
                {"id": str(player.PlayerUId), "name": player.NickName}
                for player in SaveManager().get_players()
            ],
        )
    return reply(0, None, "Failed to load, check path")
