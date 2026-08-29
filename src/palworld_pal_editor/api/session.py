"""The loaded save, as a resource (spec §8.1).

There is exactly one session, so it has no id: `GET` reports what is loaded and
`PUT` replaces it. Everything else in the API reads through whatever this holds.
"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from palworld_pal_editor.api.errors import ApiError, register_error_handlers
from palworld_pal_editor.config import PROGRAM_PATH, Config
from palworld_pal_editor.core import SaveManager
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
