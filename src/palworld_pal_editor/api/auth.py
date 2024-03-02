from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required
from werkzeug.security import check_password_hash
from palworld_pal_editor.api.util import reply

from palworld_pal_editor.config import Config

auth_blueprint = Blueprint("auth", __name__)

@auth_blueprint.route("/auth", methods=["GET"])
@jwt_required()
def auth():
    return reply(0)

@auth_blueprint.route("/login", methods=["POST"])
def login():
    password = request.json.get("password", "")

    if not check_password_hash(Config._password_hash, password):
        return reply(2, None, "Bad password"), 401

    access_token = create_access_token(identity=password, expires_delta=False)
    return reply(0, {"access_token": access_token}), 200
