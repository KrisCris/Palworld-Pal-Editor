import traceback

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from palworld_pal_editor.core import SaveManager
from palworld_pal_editor.utils import LOGGER
from palworld_pal_editor.utils.util import reply

save_blueprint = Blueprint("save", __name__)


@save_blueprint.route("/save", methods=["POST"])
@jwt_required()
def save():
    path = request.json.get("WritePath", None)
    try:
        if SaveManager().save(path):
            return reply(0)
        return reply(1, msg=f"Path not available? {path}")
    except Exception as e:
        stack_trace = traceback.format_exc()
        LOGGER.error(f"Error in patch_paldata {stack_trace}")
        return reply(
            1, msg=f"Error occored during saving, check debug console. {stack_trace}"
        )
