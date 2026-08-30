"""The read-only Pal lists the UI offers (spec §8.2).

A roster is a question, not a stored list: every one of these is derived from the
repository when asked. `GET /api/rosters` says which ones this save has, and
`GET /api/rosters/{rosterKey}/pals` answers one of them with `PalSummary[]` in the
order that list displays -- the detail of any single Pal is a separate request.
"""

from flask import Blueprint
from flask_jwt_extended import jwt_required

from palworld_pal_editor.api.errors import ApiError, register_error_handlers
from palworld_pal_editor.api.pals import pal_summary
from palworld_pal_editor.api.roster_keys import FIXED_ROSTERS, PLAYER_ROSTER_PREFIX
from palworld_pal_editor.core import SaveManager
from palworld_pal_editor.utils import DataProvider

rosters_blueprint = Blueprint("rosters", __name__)
register_error_handlers(rosters_blueprint)


def roster_entries(manager: SaveManager) -> list[dict]:
    """Every list this save can show, in the order the UI stacks them.

    `label` is data or nothing: a player's nickname, or the game's own name for the
    Global Palbox. Where it is None the frontend supplies its own translated text,
    since a label invented here would be untranslatable English in the UI.
    """
    entries = [
        {
            "rosterKey": f"{PLAYER_ROSTER_PREFIX}{player.PlayerUId}",
            "kind": "player",
            "label": player.NickName or "",
            "playerUid": str(player.PlayerUId),
        }
        for player in manager.get_players()
    ]
    if manager.working_records():
        entries.append(
            {
                "rosterKey": "base-workers",
                "kind": "base",
                "label": None,
                "playerUid": None,
            }
        )
    if manager.has_global_palbox:
        entries.append(
            {
                "rosterKey": "global-palbox",
                "kind": "global_palbox",
                "label": (
                    DataProvider.get_tech_name("GlobalPalStorage") or None
                ),
                "playerUid": None,
            }
        )
    return entries


def roster_records(manager: SaveManager, roster_key: str) -> list:
    if roster_key in FIXED_ROSTERS:
        return manager.records_for_roster(FIXED_ROSTERS[roster_key])
    if roster_key.startswith(PLAYER_ROSTER_PREFIX):
        player_uid = roster_key[len(PLAYER_ROSTER_PREFIX):]
        if manager.get_player(player_uid) is not None:
            return manager.sorted_records_for_roster(player_uid)
    raise ApiError(
        "ROSTER_NOT_FOUND",
        f"No roster named {roster_key}",
        status=404,
    )


@rosters_blueprint.route("", methods=["GET"])
@jwt_required()
def list_rosters():
    manager = SaveManager()
    with manager.session_lock:
        return roster_entries(manager)


@rosters_blueprint.route("/<roster_key>/pals", methods=["GET"])
@jwt_required()
def list_roster_pals(roster_key: str):
    manager = SaveManager()
    with manager.session_lock:
        return [
            pal_summary(manager, record)
            for record in roster_records(manager, roster_key)
        ]
