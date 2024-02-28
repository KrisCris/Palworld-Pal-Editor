from flask import Blueprint, jsonify

from palworld_pal_editor.config import Config
from palworld_pal_editor.core import SaveManager

save_blueprint = Blueprint('save', __name__)

@save_blueprint.route('/load')
def load():
    if Config.path and SaveManager.open(Config.path):
        return jsonify(SaveManager.get_players()) # just an example