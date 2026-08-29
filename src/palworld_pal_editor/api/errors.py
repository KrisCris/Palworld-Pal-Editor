"""The one shape a failing REST call takes, per spec §8.7.

Routes raise `ApiError` with a stable business code; the frontend maps that code to
its own i18n text, so no message written here is ever shown to a user verbatim.
Anything else escaping a view is unexpected by definition and comes back as a 500
carrying its traceback, because the person who can act on it is the user filing the
report, not the process that already logged it.
"""

import traceback

from flask import jsonify
from werkzeug.exceptions import HTTPException

from palworld_pal_editor.utils import LOGGER


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
