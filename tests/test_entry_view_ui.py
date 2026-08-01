from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEBUI = ROOT / "frontend" / "palworld-pal-editor-webui" / "src"
ENTRY = WEBUI / "views" / "EntryView.vue"
TOP_BAR = WEBUI / "components" / "TopBar.vue"
ICON_SPRITE = WEBUI / "assets" / "ui-icons.svg"
I18N_FILES = [WEBUI / "i18n" / name for name in ("en.js", "fr.js", "ja.js", "zh-CN.js")]

ENTRY_KEYS = (
    "Entry_Title",
    "Entry_Intro",
    "Entry_Support_Title",
    "Entry_Support_Subtitle",
    "Entry_Support_Community_Title",
    "Entry_Support_Community_Description",
    "Entry_Support_Code_Title",
    "Entry_Support_Code_Description",
    "Entry_Support_Issue_Title",
    "Entry_Support_Issue_Description",
    "Entry_Support_Author_Title",
    "Entry_Support_Author_Description",
    "Entry_Downloads_Title",
    "Entry_Downloads_Subtitle",
    "Entry_Download_GitHub_Description",
    "Entry_Download_Nexus_Description",
    "Entry_Download_Bilibili_Description",
    "Entry_Load_Title",
    "Entry_Load_Subtitle",
    "Entry_Path_Label",
    "Entry_Instructions_Title",
    "Entry_Instructions_Subtitle",
    "Entry_Instruction_First_Title",
    "Entry_Instruction_First_Description",
    "Entry_Instruction_WebUI_Title",
    "Entry_Instruction_WebUI_Description",
    "Entry_Instruction_Docker_Title",
    "Entry_Instruction_Docker_Description",
    "Entry_Help",
)


def test_entry_icon_symbols_are_available():
    sprite = ICON_SPRITE.read_text(encoding="utf-8")

    for icon in (
        "message",
        "pull-request",
        "bug",
        "branch",
        "download",
        "video",
        "play",
        "folder-check",
        "shield",
        "box",
        "help",
    ):
        assert f'id="{icon}"' in sprite


def test_entry_view_preserves_actions_links_and_responsive_order():
    source = ENTRY.read_text(encoding="utf-8")

    assert "palStore.show_file_picker" in source
    assert "palStore.loadSave" in source
    assert "palStore.get_updates" in source
    assert "palStore.SHOW_DONATE_FLAG = true" in source
    for url in (
        "https://discord.gg/FnuA95nMJ8",
        "https://github.com/KrisCris/Palworld-Pal-Editor",
        "https://github.com/KrisCris/Palworld-Pal-Editor/issues",
        "https://github.com/KrisCris/Palworld-Pal-Editor/releases",
        "https://www.nexusmods.com/palworld/mods/995?tab=files",
        "https://space.bilibili.com/12184831",
    ):
        assert url in source

    for class_name, order in (
        ("entry-instructions", 2),
        ("entry-support", 3),
        ("entry-downloads", 4),
    ):
        assert f'.{class_name} {{ order: {order};' in source

    assert ".entry-load { order:" not in source
    assert "v-if=\"['zh-CN', 'zh-TW'].includes(palStore.I18n)\"" in source


def test_entry_view_prioritizes_loading_and_only_constrains_middle_content():
    source = ENTRY.read_text(encoding="utf-8")

    assert "align-content: center" in source
    assert "padding: clamp(" in source
    shell_css = source.split(".entry-shell {", 1)[1].split("}", 1)[0]
    assert "width: 100%" in shell_css
    assert "max-width: min(92rem, 1920px)" in shell_css
    assert "margin-inline: auto" in shell_css
    assert "border:" not in shell_css
    assert "background:" not in shell_css
    page_css = source.split(".entry-page {", 1)[1].split("}", 1)[0]
    assert "max-width:" not in page_css
    assert ".entry-footer {\n  width: 100%" in source
    assert "height: 100%" not in source
    assert "grid-template-rows: minmax(0, 1fr)" not in source
    assert ".entry-page,\n  .entry-shell" not in source
    assert source.index('class="entry-load"') < source.index('class="entry-columns"')
    assert '</section>\n\n    <footer class="entry-footer">' in source


def test_entry_view_removes_local_badge_and_renames_community_action():
    source = ENTRY.read_text(encoding="utf-8")

    assert "Entry_Load_Local" not in source
    expected_titles = {
        "en.js": "Join the community",
        "fr.js": "Rejoindre la communauté",
        "ja.js": "コミュニティに参加",
        "zh-CN.js": "加入社区",
    }
    for path in I18N_FILES:
        text = path.read_text(encoding="utf-8")
        assert "Entry_Load_Local:" not in text
        assert f'Entry_Support_Community_Title: "{expected_titles[path.name]}"' in text


def test_entry_brand_uses_the_application_icon():
    source = TOP_BAR.read_text(encoding="utf-8")

    assert "@/assets/logo.ico" in source
    assert "Palworld Pal Editor" in source
    assert "Developed by _connlost" in source


def test_entry_copy_exists_in_every_ui_language():
    for path in I18N_FILES:
        text = path.read_text(encoding="utf-8")
        for key in ENTRY_KEYS:
            assert f"{key}:" in text, f"{key} is missing from {path.name}"
