"""Everything the app needs that is not the loaded save.

Three unrelated small things -- what the client should boot with, where the user
can browse for a save, and whether a newer build exists. They share a module
because they are each one route, and a module per route would only make the API
harder to read.

`GET /api/save-paths` is the one behaviour change: browsing a directory is a read
and leaves `Config.path` alone. The route it replaces wrote the browsed path into
the server's config, which turned "go up one level" into a cursor every client
shared. The client now says which directory it wants and gets that directory's
parent back with it, so walking the tree needs no server state at all. What
actually loads is still only `PUT /api/session`'s decision.
"""

import asyncio
import os
from pathlib import Path

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from palworld_pal_editor.api.errors import ApiError, register_error_handlers
from palworld_pal_editor.config import (
    NEXUS_URL,
    PROGRAM_PATH,
    Config,
    get_new_version,
    is_gh_build,
    version_info,
)
from palworld_pal_editor.utils import DataProvider
from palworld_pal_editor.utils.util import get_path_context

application_blueprint = Blueprint("application", __name__)
register_error_handlers(application_blueprint)


def app_config_resource() -> dict:
    """What the client cannot start without.

    `hasPassword` is the reason this route answers without a token: it is how the
    client learns whether it has to authenticate at all.
    """
    return {
        "i18n": Config.i18n,
        "i18nOptions": DataProvider.get_i18n_map(),
        "defaultSavePath": Config.path,
        "hasPassword": bool(Config.password),
        "version": version_info(),
        "isOfficialBuild": is_gh_build(),
        # Per locale, because the prompt is written in one language at a time.
        "donationPromptDismissed": bool(Config.shownDonateInfo.get(Config.i18n)),
    }


def _set_i18n(value) -> None:
    if not DataProvider.is_valid_i18n(value):
        # No `details`: the client was handed every locale there is by
        # `i18nOptions` before it ever sent this.
        raise ApiError("I18N_NOT_AVAILABLE", f"No locale named {value}")
    Config.i18n = value


def _set_donation_prompt_dismissed(value) -> None:
    if not isinstance(value, bool):
        raise ApiError(
            "APP_CONFIG_VALUE_INVALID",
            "donationPromptDismissed must be a boolean",
        )
    Config.shownDonateInfo[Config.i18n] = value


# The whole of what a client may write, in the order a request applies them.
# `Config` holds the JWT secret and the password hash beside these two, so a PATCH
# that reflected onto attribute names would hand those out as well; naming the
# writable fields is what keeps it from being that.
#
# The order is the server's because the dismissal is remembered per locale: a
# request that sets both has to dismiss the prompt for the locale the user ends up
# reading, not the one they were reading before. Request key order cannot decide
# that -- JSON gives no order guarantee, and Flask's own serializer sorts keys.
APP_CONFIG_WRITERS = {
    "i18n": _set_i18n,
    "donationPromptDismissed": _set_donation_prompt_dismissed,
}


def default_save_directory() -> Path:
    """Where browsing starts when the client names no directory.

    The configured save folder if it is still there, then the place the game keeps
    its saves on this machine, then wherever the editor itself lives -- so the
    picker opens somewhere useful rather than on an error.
    """
    if Config.path:
        configured = Path(Config.path).resolve()
        if configured.is_dir():
            return configured
    game_saves = (
        Path(os.environ.get("LOCALAPPDATA", "/")) / "Pal" / "Saved" / "SaveGames"
    )
    return game_saves if game_saves.is_dir() else PROGRAM_PATH


@application_blueprint.route("/app-config", methods=["GET"])
def get_app_config():
    return app_config_resource()


@application_blueprint.route("/app-config", methods=["PATCH"])
@jwt_required()
def patch_app_config():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ApiError("APP_CONFIG_INVALID", "Request body must be an object")

    unwritable = set(payload) - set(APP_CONFIG_WRITERS)
    if unwritable:
        raise ApiError(
            "APP_CONFIG_FIELD_UNKNOWN",
            f"Not an app preference: {', '.join(sorted(unwritable))}",
            details={"writable": sorted(APP_CONFIG_WRITERS)},
        )

    for field, write in APP_CONFIG_WRITERS.items():
        if field in payload:
            write(payload[field])
    Config.save_to_file()
    return app_config_resource()


@application_blueprint.route("/save-paths", methods=["GET"])
@jwt_required()
def browse_save_paths():
    requested = request.args.get("path")
    directory = Path(requested).resolve() if requested else default_save_directory()
    if not directory.is_dir():
        raise ApiError(
            "PATH_NOT_FOUND",
            f"No directory at {directory}",
            status=404,
            details={"path": str(directory)},
        )
    try:
        return get_path_context(directory)
    except OSError as error:
        raise ApiError(
            "PATH_UNREADABLE",
            f"Unable to list {directory}",
            details={"path": str(directory), "reason": str(error)},
        )


@application_blueprint.route("/releases/latest", methods=["GET"])
@jwt_required()
def get_latest_release():
    """Whether a newer build exists, which is a fact and not an error either way.

    `get_new_version()` answers None for every "no" there is -- up to date, not an
    official build, GitHub unreachable -- and the UI does the same thing with all
    of them, so they stay one answer here.
    """
    latest = asyncio.run(get_new_version())
    return {
        "updateAvailable": latest is not None,
        "version": latest[0] if latest else None,
        "downloadUrl": latest[1] if latest else None,
        "nexusUrl": NEXUS_URL,
    }
