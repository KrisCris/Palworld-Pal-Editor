from flask import jsonify

def reply(status, data=None, msg=None):
    return jsonify({"status": status, "data": data, "msg": msg})
