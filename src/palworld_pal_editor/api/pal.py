from flask import Blueprint, jsonify

pal_blueprint = Blueprint('pal', __name__)

@pal_blueprint.route('/pal')
def get_pal():
    return jsonify(["pal get"])