from unittest.mock import patch

from flask_jwt_extended import create_access_token

from palworld_pal_editor.config import Config
from palworld_pal_editor.utils import data_provider
from palworld_pal_editor.utils.data_provider import DataProvider
from palworld_pal_editor.webui import app

EXPECTED_LOCALES = {
    "en": "English",
    "de": "Deutsch",
    "es": "Español",
    "es-MX": "Español (México)",
    "fr": "Français",
    "id": "Bahasa Indonesia",
    "it": "Italiano",
    "ja": "日本語",
    "ko": "한국어",
    "pl": "Polski",
    "pt-BR": "Português (Brasil)",
    "ru": "Русский",
    "th": "ไทย",
    "tr": "Türkçe",
    "vi": "Tiếng Việt",
    "zh-CN": "简体中文",
    "zh-TW": "繁體中文",
}


def test_data_provider_exposes_every_game_data_locale():
    assert DataProvider.get_i18n_map() == EXPECTED_LOCALES
    assert DataProvider.default_i18n() == "en"
    assert DataProvider.is_valid_i18n("de")
    assert DataProvider.is_valid_i18n("zh-TW")
    assert not DataProvider.is_valid_i18n("xx")


def test_default_locale_does_not_depend_on_json_key_order():
    reordered = {"de": EXPECTED_LOCALES["de"], **EXPECTED_LOCALES}
    with patch.object(data_provider, "I18N_LIST", reordered):
        assert DataProvider.default_i18n() == "en"


def test_app_config_publishes_all_locales_and_current_untranslated_locale():
    with patch.object(Config, "i18n", "de"), app.test_client() as client:
        payload = client.get("/api/app-config").get_json()

    assert payload["i18n"] == "de"
    assert payload["i18nOptions"] == EXPECTED_LOCALES


def test_i18n_api_and_data_provider_accept_generated_locales():
    app.config["JWT_SECRET_KEY"] = "test-secret-key-with-at-least-32-bytes"
    with app.app_context():
        token = create_access_token(identity="test", expires_delta=False)

    # `save_to_file` is patched because the route persists what it writes, and no
    # test may reach the developer's own config.json.
    with patch.object(Config, "i18n", "en"), patch.object(Config, "save_to_file"),             app.test_client() as client:
        response = client.patch(
            "/api/app-config",
            json={"i18n": "zh-TW"},
            headers={"Authorization": f"Bearer {token}"},
        )
        localized_name = DataProvider.get_pal_i18n("Anubis")

    assert response.get_json()["i18n"] == "zh-TW"
    assert localized_name == "阿努比斯"
