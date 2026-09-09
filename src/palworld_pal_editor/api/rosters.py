"""The read-only Pal lists the UI offers.

A roster is a question, not a stored list: every one of these is derived from the
repository when asked. `GET /api/rosters` says which ones this save has, and
`GET /api/rosters/{rosterKey}/pals` answers one of them with `PalSummary[]` in the
order that list displays -- the detail of any single Pal is a separate request.
"""

from flask import Blueprint
from flask_jwt_extended import jwt_required

from palworld_pal_editor.api.errors import ApiError, register_error_handlers
from palworld_pal_editor.api.pal_serializers import pal_summary
from palworld_pal_editor.api.roster_keys import (
    FIXED_ROSTERS,
    PLAYER_ROSTER_PREFIX,
    core_roster_key,
)
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
    if manager.rosters.working_records():
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


def require_roster(manager: SaveManager, roster_key: str) -> str:
    """The roster key, or a 404. A player roster exists while its player does."""
    if roster_key in FIXED_ROSTERS:
        return roster_key
    player_uid = roster_key.removeprefix(PLAYER_ROSTER_PREFIX)
    if player_uid != roster_key and manager.get_player(player_uid) is not None:
        return roster_key
    raise ApiError(
        "ROSTER_NOT_FOUND",
        f"No roster named {roster_key}",
        status=404,
    )


def roster_records(manager: SaveManager, roster_key: str) -> list:
    require_roster(manager, roster_key)
    if roster_key in FIXED_ROSTERS:
        return manager.rosters.records_for_roster(roster_key)
    return manager.rosters.sorted_records_for_roster(core_roster_key(roster_key))


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


@rosters_blueprint.route("/<roster_key>/pal-creation-targets", methods=["GET"])
@jwt_required()
def list_pal_creation_targets(roster_key: str):
    """The storages a Pal added to this list may be created in, as storage keys.

    Where a *new* Pal may go is not where an existing one may be moved: creating
    into a viewing cage or another guild's base would make a Pal that belongs to
    the list nobody opened. The answer is the save's, not the client's -- which is
    why the client asks for it rather than filtering the storage directory by
    storage kind. What each key looks like is `GET /api/storages`.
    """
    manager = SaveManager()
    with manager.session_lock:
        require_roster(manager, roster_key)
        return [
            descriptor.storage_key
            for descriptor in manager.storage_directory.creation_targets(core_roster_key(roster_key))
        ]
