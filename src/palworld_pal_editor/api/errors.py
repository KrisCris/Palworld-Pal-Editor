"""The one shape a failing REST call takes, per spec §8.7.

Routes raise `ApiError` with a stable business code; the frontend maps that code to
its own i18n text, so no message written here is ever shown to a user verbatim.
Anything else escaping a view is unexpected by definition and comes back as a 500
carrying its traceback, because the person who can act on it is the user filing the
report, not the process that already logged it.

The one exception is a failure to authenticate, which is not this envelope's to
answer and is handed back to auth's own shape below.
"""

import traceback

from flask import jsonify
from flask_jwt_extended.exceptions import JWTExtendedException
from jwt import PyJWTError
from werkzeug.exceptions import HTTPException

from palworld_pal_editor.utils import LOGGER, reply


class ApiError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status: int = 400,
        details: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.details = details or {}


def _envelope(code: str, message: str, details: dict):
    return jsonify({"error": {"code": code, "message": message, "details": details}})


def register_error_handlers(blueprint) -> None:
    """Give one blueprint the §8.7 envelope. Called by every REST blueprint."""

    @blueprint.errorhandler(ApiError)
    def _handle_api_error(error: ApiError):
        LOGGER.warning(f"{error.code}: {error.message}")
        return _envelope(error.code, error.message, error.details), error.status

    @blueprint.errorhandler(JWTExtendedException)
    @blueprint.errorhandler(PyJWTError)
    def _handle_auth_failure(error: Exception):
        # `webui.py`'s `@jwt` loaders answer these, but a blueprint handler shadows
        # an app-level one, so the catch-all below claimed them first and turned a
        # missing or expired token into a 500 with a server traceback in it. Spec
        # §12 leaves auth's behaviour alone this round, so this says what those
        # loaders say -- 401, in the envelope the frontend already reads for them.
        return reply(status=2, msg=str(error)), 401

    @blueprint.errorhandler(Exception)
    def _handle_unexpected(error: Exception):
        # Flask routes its own 404/405/415 through here too; those already say what
        # they mean and are not this envelope's business.
        if isinstance(error, HTTPException):
            return error
        stack_trace = traceback.format_exc()
        LOGGER.error(f"Unexpected error serving a REST request\n{stack_trace}")
        return (
            _envelope(
                "UNEXPECTED_ERROR",
                str(error),
                {"traceback": stack_trace},
            ),
            500,
        )
