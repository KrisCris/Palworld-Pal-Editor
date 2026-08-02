from datetime import timedelta

from flask import Blueprint, request
from flask_jwt_extended import create_access_token, jwt_required
from werkzeug.security import check_password_hash

from palworld_pal_editor.config import Config
from palworld_pal_editor.utils.util import reply

auth_blueprint = Blueprint("auth", __name__)

@auth_blueprint.route("/auth", methods=["GET"])
@jwt_required()
def auth():
    return reply(0)

@auth_blueprint.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    password = data.get("password", "")

    if not check_password_hash(Config._password_hash, password):
        return reply(2, None, "Bad password"), 401

    access_token = create_access_token(
        identity="webui",
        expires_delta=timedelta(days=7) if data.get("remember") is True else False,
    )
    return reply(0, {"access_token": access_token}), 200
