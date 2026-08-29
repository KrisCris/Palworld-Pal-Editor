from flask_jwt_extended import decode_token
from werkzeug.security import generate_password_hash

from palworld_pal_editor.config import Config
from fakes import world_record
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

def select_pal(monkeypatch, record):
    manager = SaveManager()
    monkeypatch.setattr(manager, "get_unique_world_record", lambda _pal_id: record)
    monkeypatch.setattr(manager, "normalize_external_record", lambda _record: None)
    monkeypatch.setattr(manager, "get_player", lambda _player_id: None)
    monkeypatch.setattr(
        manager,
        "resolve_record_location",
        lambda _record: {
            "ContainerId": None,
            "SlotIndex": 0,
            "ContainerKind": "world",
            "ContainerLabel": None,
        },
    )


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
    record = world_record(PalObjects.PalSaveParameter(
        PalObjects.EMPTY_UUID,
        PalObjects.EMPTY_UUID,
        PalObjects.EMPTY_UUID,
        0,
        PalObjects.EMPTY_UUID,
    ))
    monkeypatch.setattr(
        record.pal,
        "set_WorkSuitability",
        lambda name, level: updates.append((name, level)),
    )

    select_pal(monkeypatch, record)

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
    record = world_record(PalObjects.PalSaveParameter(
        PalObjects.EMPTY_UUID,
        PalObjects.EMPTY_UUID,
        PalObjects.EMPTY_UUID,
        0,
        PalObjects.EMPTY_UUID,
    ))
    pal = record.pal

    select_pal(monkeypatch, record)

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
