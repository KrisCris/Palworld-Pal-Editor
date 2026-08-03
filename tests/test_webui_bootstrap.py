from flask_jwt_extended import decode_token
from werkzeug.security import generate_password_hash

from palworld_pal_editor.config import Config
from palworld_pal_editor.core import PalEntity, SaveManager
from palworld_pal_editor.core.pal_objects import PalObjects
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


def test_save_status_uses_gvas_file(monkeypatch):
    configure_app(monkeypatch)
    manager = SaveManager()
    monkeypatch.delattr(manager, "gvas_file", raising=False)

    with app.test_client() as client:
        token = login(client)
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/save/status", headers=headers)
        assert response.get_json()["data"] == {"SaveLoaded": False}

        monkeypatch.setattr(manager, "gvas_file", object(), raising=False)
        response = client.get("/api/save/status", headers=headers)
        assert response.get_json()["data"] == {"SaveLoaded": True}


def test_remembered_token_expires_in_seven_days(monkeypatch):
    configure_app(monkeypatch)

    with app.test_client() as client, app.app_context():
        default_payload = decode_token(login(client, remember=False))
        remembered_payload = decode_token(login(client, remember=True))

    assert "exp" not in default_payload
    assert default_payload["sub"] == "webui"
    assert remembered_payload["sub"] == "webui"
    assert remembered_payload["exp"] - remembered_payload["iat"] == 7 * 24 * 60 * 60


def test_heal_all_pals_does_not_require_a_selected_player(monkeypatch):
    configure_app(monkeypatch)
    healed = []
    monkeypatch.setattr(SaveManager(), "heal_all_pals", lambda: healed.append(True))

    with app.test_client() as client:
        token = login(client)
        response = client.patch(
            "/api/pal/paldata",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "PlayerUId": None,
                "PalGuid": None,
                "key": "heal_all_pals",
                "value": None,
            },
        )

    assert response.status_code == 200
    assert response.get_json()["status"] == 0
    assert healed == [True]


def test_max_suitabilities_updates_all_requested_types_in_one_patch(monkeypatch):
    configure_app(monkeypatch)
    updates = []

    class Pal:
        def set_WorkSuitability(self, name, level):
            updates.append((name, level))

    class Player:
        def get_pal(self, _pal_id):
            return Pal()

    monkeypatch.setattr(SaveManager(), "get_player", lambda _player_id: Player())

    with app.test_client() as client:
        token = login(client)
        response = client.patch(
            "/api/pal/paldata",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "PlayerUId": "player",
                "PalGuid": "pal",
                "key": "set_Suitabilities",
                "value": {"Handcraft": 5, "Mining": 5},
            },
        )

    assert response.get_json()["status"] == 0
    assert updates == [("Handcraft", 5), ("Mining", 5)]


def test_priority_uses_the_generic_pal_patch(monkeypatch):
    configure_app(monkeypatch)
    pal = PalEntity(PalObjects.PalSaveParameter(
        PalObjects.EMPTY_UUID,
        PalObjects.EMPTY_UUID,
        PalObjects.EMPTY_UUID,
        0,
        PalObjects.EMPTY_UUID,
    ))

    class Player:
        NickName = "Tester"

        def get_pal(self, _pal_id):
            return pal

    monkeypatch.setattr(SaveManager(), "get_player", lambda _player_id: Player())

    with app.test_client() as client:
        token = login(client)
        response = client.patch(
            "/api/pal/paldata",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "PlayerUId": "player",
                "PalGuid": "pal",
                "key": "FavoriteIndex",
                "value": 3,
            },
        )

    assert response.get_json()["status"] == 0
    assert pal.FavoriteIndex == 3


def test_uncaught_api_error_returns_exception_details(monkeypatch):
    configure_app(monkeypatch)
    monkeypatch.setattr(SaveManager(), "get_player", lambda _player_id: None)

    with app.test_client() as client:
        token = login(client)
        response = client.patch(
            "/api/pal/paldata",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "PlayerUId": "missing-player",
                "PalGuid": "missing-pal",
                "key": "NickName",
                "value": "test",
            },
        )

    payload = response.get_json()
    assert response.status_code == 500
    assert payload["status"] == 1
    assert payload["data"]["error"]["code"] == "AttributeError"
    assert "Traceback (most recent call last)" in payload["data"]["error"]["log"]
    assert "get_pal" in payload["data"]["error"]["log"]
