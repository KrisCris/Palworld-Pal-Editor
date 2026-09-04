"""The loaded save, as a resource.

There is exactly one session, so it has no id: `GET` reports what is loaded and
`PUT` replaces it. Everything else in the API reads through whatever this holds.

Writing the session out is a sub-resource rather than a verb on the session: each
`POST /saves` is one save that happened, at a path the caller may choose, and the
session it was made from is unchanged either way.
"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from palworld_pal_editor.api.errors import ApiError, register_error_handlers
from palworld_pal_editor.config import PROGRAM_PATH, Config
from palworld_pal_editor.core import SaveManager
from palworld_pal_editor.core.save_io import SaveFailed
from palworld_pal_editor.utils import LOGGER

session_blueprint = Blueprint("session", __name__)
register_error_handlers(session_blueprint)


def session_resource(manager: SaveManager) -> dict:
    return {
        "loaded": manager.gvas_file is not None,
        "path": str(manager.file_path) if manager.file_path else None,
        # Storages that failed to load. A session is usable without them, so this is
        # a report rather than a failure -- the same list the old players route sent.
        "warnings": list(manager.load_warnings),
    }


@session_blueprint.route("", methods=["GET"])
@jwt_required()
def get_session():
    manager = SaveManager()
    with manager.session_lock:
        return session_resource(manager)


@session_blueprint.route("", methods=["PUT"])
@jwt_required()
def put_session():
    payload = request.get_json(silent=True) or {}
    path = payload.get("path") or Config.path
    if not path:
        raise ApiError("PATH_REQUIRED", "No save path was given")

    manager = SaveManager()
    # open() takes the lock itself and empties the session on any failure, so a
    # rejected load leaves nothing of the previous save behind either.
    if manager.open(path) is None:
        raise ApiError(
            "SAVE_LOAD_FAILED",
            f"Unable to load a save from {path}",
            details={"path": str(path)},
        )

    Config.path = path
    Config.save_to_file(PROGRAM_PATH / "config.json")
    LOGGER.info(f"Session loaded from {path}")
    with manager.session_lock:
        return session_resource(manager)


@session_blueprint.route("/saves", methods=["POST"])
@jwt_required()
def post_session_save():
    """Write the session to disk. `{"path": ...}`, defaulting to where it came from.

    A save that fails has already put the target back the way it was, so the error
    is the whole story -- except for `backupPath`, which the user needs when
    `restored` is false and that folder is the only intact copy left.

    Saving elsewhere does not move the session: `Config.path` still names the save
    that is open, so the next reload opens that one and not the copy.
    """
    payload = request.get_json(silent=True) or {}
    manager = SaveManager()
    path = payload.get("path") or manager.file_path
    if not path:
        raise ApiError("PATH_REQUIRED", "No save path was given")

    try:
        manager.save(str(path))
    except SaveFailed as failure:
        raise ApiError(
            "SAVE_FAILED",
            str(failure),
            details={
                "path": str(path),
                "backupPath": (
                    str(failure.backup_path) if failure.backup_path else None
                ),
                "restored": failure.restored,
            },
        ) from failure

    LOGGER.info(f"Session saved to {path}")
    return {"path": str(path)}, 201
