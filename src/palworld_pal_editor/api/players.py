"""Player resources (spec §8.2).

One serializer for both the list and a single player: the player page and the
player list read the same fields, and a second shape would only be a second thing
to keep in step.
"""

from flask import Blueprint
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
