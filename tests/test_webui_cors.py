import os

import pytest

from palworld_pal_editor import gui
from palworld_pal_editor.config import Config
from palworld_pal_editor.webui import app

PUBLIC_ORIGIN = "https://frontend.example.test"
LOOPBACK_ORIGIN = "http://localhost:5173"


@pytest.fixture(autouse=True)
def configure_cors_app(monkeypatch):
    app.config.update(TESTING=True)
    monkeypatch.setattr(Config, "password", None)


def assert_allowed(response, origin):
    assert response.headers["Access-Control-Allow-Origin"] == origin
    assert "Origin" in response.headers["Vary"]
    assert "Access-Control-Allow-Credentials" not in response.headers


def test_ready_identifies_the_serving_process():
    with app.test_client() as client:
        response = client.get("/api/ready")

    assert response.status_code == 200
    assert response.get_json()["data"]["pid"] == os.getpid()


def test_gui_accepts_only_its_own_backend_process():
    class Response:
        status_code = 200

        def __init__(self, pid):
            self.pid = pid

        def json(self):
            return {"status": 0, "data": {"pid": self.pid}}

    assert gui.is_current_backend(Response(os.getpid())) is True
    assert gui.is_current_backend(Response(os.getpid() + 1)) is False


def test_password_protected_backend_allows_public_preflight(monkeypatch):
    monkeypatch.setattr(Config, "password", "secret")

    with app.test_client() as client:
        response = client.options(
            "/api/ready",
            headers={
                "Origin": PUBLIC_ORIGIN,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization, Content-Type",
            },
        )

    assert response.status_code == 204
    assert_allowed(response, PUBLIC_ORIGIN)
    assert response.headers["Access-Control-Allow-Methods"] == "GET, POST, PATCH, DELETE, OPTIONS"
    assert response.headers["Access-Control-Allow-Headers"] == "Authorization, Content-Type"


def test_password_protected_backend_allows_public_get(monkeypatch):
    monkeypatch.setattr(Config, "password", "secret")

    with app.test_client() as client:
        response = client.get("/api/ready", headers={"Origin": PUBLIC_ORIGIN})

    assert response.status_code == 200
    assert_allowed(response, PUBLIC_ORIGIN)


@pytest.mark.parametrize(
    ("password", "expected"),
    [(None, False), ("", False), ("secret", True)],
)
def test_app_config_reports_only_nonempty_passwords(monkeypatch, password, expected):
    monkeypatch.setattr(Config, "password", password)

    with app.test_client() as client:
        response = client.get("/api/app-config")

    assert response.status_code == 200
    assert response.get_json()["hasPassword"] is expected


def test_empty_password_does_not_enable_public_cors(monkeypatch):
    monkeypatch.setattr(Config, "password", "")

    with app.test_client() as client:
        response = client.get("/api/ready", headers={"Origin": PUBLIC_ORIGIN})

    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" not in response.headers


def test_unprotected_backend_rejects_public_preflight():
    with app.test_client() as client:
        response = client.options(
            "/api/auth/auth",
            headers={
                "Origin": PUBLIC_ORIGIN,
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 204
    assert "Access-Control-Allow-Origin" not in response.headers
    assert "Access-Control-Allow-Credentials" not in response.headers


def test_unprotected_backend_allows_loopback_origin_from_loopback_client():
    with app.test_client() as client:
        response = client.get(
            "/api/ready",
            headers={"Origin": LOOPBACK_ORIGIN},
            environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
        )

    assert response.status_code == 200
    assert_allowed(response, LOOPBACK_ORIGIN)


def test_unprotected_backend_rejects_loopback_origin_from_public_client():
    with app.test_client() as client:
        response = client.get(
            "/api/ready",
            headers={"Origin": LOOPBACK_ORIGIN},
            environ_overrides={"REMOTE_ADDR": "203.0.113.8"},
        )

    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" not in response.headers
    assert "Access-Control-Allow-Credentials" not in response.headers


def test_allowed_image_response_has_cors_headers(monkeypatch):
    monkeypatch.setattr(Config, "password", "secret")

    with app.test_client() as client:
        response = client.get("/image/pals/unknown", headers={"Origin": PUBLIC_ORIGIN})

    assert response.status_code == 200
    assert_allowed(response, PUBLIC_ORIGIN)


def test_allowed_not_found_and_unexpected_error_have_cors_headers(monkeypatch):
    monkeypatch.setattr(Config, "password", "secret")

    def fail_ready():
        raise RuntimeError("expected test error")

    monkeypatch.setitem(app.view_functions, "ready", fail_ready)
    with app.test_client() as client:
        not_found = client.get("/image/missing/not-found", headers={"Origin": PUBLIC_ORIGIN})
        error = client.get("/api/ready", headers={"Origin": PUBLIC_ORIGIN})

    assert not_found.status_code == 404
    assert_allowed(not_found, PUBLIC_ORIGIN)
    assert error.status_code == 500
    assert_allowed(error, PUBLIC_ORIGIN)


@pytest.mark.parametrize(
    "origin",
    [
        "https://frontend.example.test/",
        "https://frontend.example.test/path",
        "https://frontend.example.test/?query=yes",
        "https://frontend.example.test/#fragment",
        "https://frontend.example.test?",
        "https://frontend.example.test#",
        "https://user:secret@frontend.example.test",
        "https://frontend.example.test:invalid",
    ],
)
def test_password_protected_backend_rejects_non_origin_values(monkeypatch, origin):
    monkeypatch.setattr(Config, "password", "secret")

    with app.test_client() as client:
        response = client.get("/api/ready", headers={"Origin": origin})

    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" not in response.headers


def test_malformed_ipv6_origin_fails_closed_without_a_server_error(monkeypatch):
    monkeypatch.setattr(Config, "password", "secret")
    monkeypatch.setitem(app.config, "TESTING", False)

    with app.test_client() as client:
        response = client.get("/api/ready", headers={"Origin": "https://[::1"})

    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" not in response.headers


@pytest.mark.parametrize("remote_addr", [None, "not-an-ip-address"])
def test_unprotected_backend_rejects_missing_or_invalid_remote_address(remote_addr):
    with app.test_client() as client:
        response = client.get(
            "/api/ready",
            headers={"Origin": LOOPBACK_ORIGIN},
            environ_overrides={"REMOTE_ADDR": remote_addr},
        )

    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" not in response.headers
