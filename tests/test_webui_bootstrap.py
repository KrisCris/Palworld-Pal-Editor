from flask_jwt_extended import decode_token
from werkzeug.security import generate_password_hash

from palworld_pal_editor.config import Config
from palworld_pal_editor.webui import app


def login(client, remember=False):
    response = client.post(
        "/api/auth/login",
        json={"password": "secret", "remember": remember},
    )
    assert response.status_code == 200
    return response.get_json()["data"]["access_token"]


def configure_app(monkeypatch):
    app.config.update(
        TESTING=True,
        JWT_SECRET_KEY="test-secret-key-with-at-least-32-bytes",
    )
    monkeypatch.setattr(Config, "_password_hash", generate_password_hash("secret"))


def test_remembered_token_expires_in_seven_days(monkeypatch):
    configure_app(monkeypatch)

    with app.test_client() as client, app.app_context():
        default_payload = decode_token(login(client, remember=False))
        remembered_payload = decode_token(login(client, remember=True))

    assert "exp" not in default_payload
    assert default_payload["sub"] == "webui"
    assert remembered_payload["sub"] == "webui"
    assert remembered_payload["exp"] - remembered_payload["iat"] == 7 * 24 * 60 * 60

