import ipaddress
import mimetypes
import os
import threading
import traceback
import webbrowser
from pathlib import Path
from urllib.parse import urlsplit

from flask import Flask, request, send_from_directory
from flask_jwt_extended import JWTManager
from werkzeug.exceptions import HTTPException
from werkzeug.security import generate_password_hash

from palworld_pal_editor.api import *
from palworld_pal_editor.config import ASSETS_PATH, Config
from palworld_pal_editor.utils import LOGGER, reply

# attempt to fix MIME TYPE error for some user
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('image/png', '.png')
mimetypes.add_type('text/html', '.html')

app = Flask(__name__, static_folder=ASSETS_PATH / "webui", static_url_path='/')
app.register_blueprint(pal_blueprint, url_prefix='/api/pal')
app.register_blueprint(save_blueprint, url_prefix='/api/save')
app.register_blueprint(auth_blueprint, url_prefix='/api/auth')
app.register_blueprint(session_blueprint, url_prefix='/api/session')
app.register_blueprint(players_blueprint, url_prefix='/api/players')
app.register_blueprint(rosters_blueprint, url_prefix='/api/rosters')
app.register_blueprint(pals_blueprint, url_prefix='/api/pals')
app.register_blueprint(application_blueprint, url_prefix='/api')
app.register_blueprint(research_blueprint, url_prefix='/api/guild-research')
app.register_blueprint(catalogs_blueprint, url_prefix='/api/catalogs')
app.register_blueprint(pal_heals_blueprint, url_prefix='/api/pal-heals')

app.config['JWT_SECRET_KEY'] = Config.JWT_SECRET_KEY
jwt = JWTManager(app)


def _allowed_cors_origin():
    origin = request.headers.get("Origin")
    if not origin or origin == request.host_url.rstrip("/"):
        return None
    try:
        parsed = urlsplit(origin)
        parsed.port
    except (TypeError, ValueError):
        return None
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path
        or parsed.query
        or parsed.fragment
        or origin != f"{parsed.scheme}://{parsed.netloc}"
    ):
        return None
    if Config.password:
        return origin
    try:
        remote_is_loopback = ipaddress.ip_address(request.remote_addr).is_loopback
    except (TypeError, ValueError):
        remote_is_loopback = False
    if remote_is_loopback and parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
        return origin
    return None


@app.before_request
def cors_preflight():
    if (
        request.method == "OPTIONS"
        and request.headers.get("Access-Control-Request-Method")
        and request.headers.get("Origin") != request.host_url.rstrip("/")
    ):
        return "", 204


@app.after_request
def cors_response(response):
    origin = _allowed_cors_origin()
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        vary = response.headers.get("Vary")
        if not vary:
            response.headers["Vary"] = "Origin"
        elif "origin" not in {value.strip().lower() for value in vary.split(",")}:
            response.headers["Vary"] = f"{vary}, Origin"
        if request.method == "OPTIONS" and request.headers.get("Access-Control-Request-Method"):
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
    return response


@app.route('/image/<icon_type>/<filename>')
def serve_image(icon_type, filename):
    if icon_type == 'pals' and '-' in filename:
        filename = filename.replace('-', '/')
    image_path: Path = ASSETS_PATH / 'assets/icons' / icon_type / f"{filename}.png"
    if image_path.exists():
        directory = image_path.parent
        filename = image_path.name
        return send_from_directory(directory, filename)
    else:
        if icon_type == 'pals':
            image_path = ASSETS_PATH / 'assets/icons/pals/unknown.png'
            directory = image_path.parent
            filename = image_path.name
            return send_from_directory(directory, filename)
        return "Image not found", 404


@app.route('/', defaults={'path': ''})
@app.route('/<path>')
def serve(path):
    static_folder_path = Path(app.static_folder)
    target_path = static_folder_path / path
    if path != "" and target_path.exists():
        return send_from_directory(str(static_folder_path), path)
    return send_from_directory(str(static_folder_path), 'index.html')

@app.route('/api/ready')
def ready():
    return reply(status=0, data={"pid": os.getpid()}), 200

@jwt.invalid_token_loader
def invalid_token_callback(error_string):
    return reply(status=2, msg="Invalid Token: " + error_string), 401


@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return reply(status=2, msg="Token has expired"), 401


@jwt.unauthorized_loader
def missing_token_callback(error_string):
    return reply(status=2, msg="Authorization header missing"), 401


@app.errorhandler(Exception)
def unexpected_error(error):
    if isinstance(error, HTTPException):
        return error
    stack_trace = traceback.format_exc()
    LOGGER.error(f"Unhandled backend exception: {stack_trace}")
    return reply(
        status=1,
        data={
            "error": {
                "code": type(error).__name__,
                "log": stack_trace,
            }
        },
        msg="An unexpected backend error occurred.",
    ), 500


def main():
    port = Config.get_runtime_port()
    Config._password_hash = generate_password_hash(Config.password or "")
    if Config.mode == "web" and not Config.debug:
        try:
            threading.Timer(1, lambda: webbrowser.open(f"http://127.0.0.1:{port}") ).start()
        except:
            LOGGER.info("Failed to launch browser.")
    host = '0.0.0.0' if Config.mode == "web" else "127.0.0.1"
    if Config.debug:
        app.run(use_reloader=True, port=port, threaded=True)
    else:
        from waitress import serve
        LOGGER.info(f"LISTENING ON {host}:{port}.")
        serve(app, host=host, port=port, threads=12)
