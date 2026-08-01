from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEBUI = ROOT / "frontend" / "palworld-pal-editor-webui" / "src"
APP = WEBUI / "App.vue"
UI_ICON = WEBUI / "components" / "modules" / "UiIcon.vue"


def test_ui_icons_use_an_inline_sprite_for_packaged_webviews():
    app = APP.read_text(encoding="utf-8")
    icon = UI_ICON.read_text(encoding="utf-8")

    assert "ui-icons.svg?raw" in app
    assert 'v-html="uiIconSprite"' in app
    assert "spriteUrl" not in icon
    assert ':href="`#${name}`"' in icon
