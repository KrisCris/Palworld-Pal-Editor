"""Guild laboratory research (spec §8.6).

One resource for the whole save: `GET` reports every guild's research tree,
`PATCH /{guildId}` completes some of one guild's and reports the tree again. The
tree's own field names are the ones `GuildLabData.snapshot()` already produces --
§8.3's casing rule is about how a Pal says where it is, and renaming a payload the
BaseCamp editor reads field for field is a rewrite of a component this task is
explicitly not changing.
"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from palworld_pal_editor.api.errors import ApiError, register_error_handlers
from palworld_pal_editor.core import SaveManager

research_blueprint = Blueprint("research", __name__)
register_error_handlers(research_blueprint)

# The three ways to say how much to complete. Exactly one per request: they are
# not filters that narrow each other, they are alternatives, and a request naming
# two of them means the client asked for something it cannot have meant. A scope
# is named by carrying a value -- `"all": false` names nothing, and is a client
# that never decided what it wanted.
COMPLETION_SCOPES = ("researchId", "category", "all")


def _research_resource(manager: SaveManager) -> dict:
    try:
        return manager.get_lab_research()
    except ValueError as error:
        raise ApiError(
            "RESEARCH_NOT_AVAILABLE",
            "This save has no guild laboratory data",
            status=404,
            details={"reason": str(error)},
        )


def _completion_scope(payload: dict) -> dict:
    """The one scope this request names, as `complete()`'s keyword arguments."""
    named = [scope for scope in COMPLETION_SCOPES if payload.get(scope)]
    if len(named) != 1:
        raise ApiError(
            "RESEARCH_SCOPE_INVALID",
            "Name exactly one of researchId, category or all",
            details={"scopes": list(COMPLETION_SCOPES), "named": named},
        )
    return {
        "research_id": payload.get("researchId") or None,
        "category": payload.get("category") or None,
        "all_research": bool(payload.get("all")),
    }


@research_blueprint.route("", methods=["GET"])
@jwt_required()
def get_guild_research():
    manager = SaveManager()
    with manager.session_lock:
        return _research_resource(manager)


@research_blueprint.route("/<guild_id>", methods=["PATCH"])
@jwt_required()
def complete_guild_research(guild_id: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ApiError("RESEARCH_SCOPE_INVALID", "Request body must be an object")
    scope = _completion_scope(payload)

    manager = SaveManager()
    # One lock across the completion and the re-read: what comes back has to be the
    # tree this request produced, not one a second request changed in between.
    with manager.session_lock:
        try:
            changed = manager.complete_lab_research(guild_id, **scope)
        except ValueError as error:
            raise ApiError(
                "RESEARCH_NOT_AVAILABLE",
                f"Nothing to complete for guild {guild_id}",
                status=404,
                details={"guildId": guild_id, "reason": str(error)},
            )
        # How many rows this actually moved. It is the one thing the updated tree
        # cannot say afterwards, and it is what the UI reports back to the user.
        return {"changed": changed, "research": _research_resource(manager)}
