from flask import Blueprint, jsonify

player_blueprint = Blueprint('player', __name__)

@player_blueprint.route('/player')
def get_player():
    return jsonify(["player get"])
