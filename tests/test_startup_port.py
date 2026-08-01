import sys

import pytest

import palworld_pal_editor.__main__ as app_main
from palworld_pal_editor.config import Config


def run_setup(monkeypatch, mode, selected_port):
    for key in ("debug", "i18n", "mode", "nocli", "password", "path", "port"):
        monkeypatch.setattr(Config, key, getattr(Config, key))
    monkeypatch.setattr(
        Config, "_runtime_port", getattr(Config, "_runtime_port", None), raising=False
    )

    saved = []
    checked = []
    monkeypatch.setattr(Config, "load_from_file", classmethod(lambda cls: None))
    monkeypatch.setattr(
        Config,
        "save_to_file",
        classmethod(lambda cls, file_path=None: saved.append(cls.to_dict())),
    )
    monkeypatch.setattr(
        app_main,
        "check_or_generate_port",
        lambda port, host: checked.append((port, host)) or selected_port,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["palworld-pal-editor", "--mode", mode, "--port", "58080", "--nocli"],
    )

    app_main.setup_config_from_args()
    return checked, saved


@pytest.mark.parametrize(
    ("mode", "expected_host"),
    [("gui", "127.0.0.1"), ("web", "0.0.0.0")],
)
def test_startup_checks_the_address_the_backend_will_bind(
    monkeypatch, mode, expected_host
):
    checked, _ = run_setup(monkeypatch, mode, 58080)

    assert checked == [(58080, expected_host)]


def test_automatic_fallback_port_is_not_saved(monkeypatch):
    _, saved = run_setup(monkeypatch, "gui", 63886)

    assert Config.port == 58080
    assert Config.get_runtime_port() == 63886

    Config.save_to_file()
    assert [snapshot["port"] for snapshot in saved] == [58080, 58080]
