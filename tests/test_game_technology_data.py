import json
from pathlib import Path


ASSETS = Path(__file__).parents[1] / "src/palworld_pal_editor/assets"
LOCALES = {
    "ja",
    "de",
    "en",
    "es",
    "es-MX",
    "fr",
    "id",
    "it",
    "ko",
    "pl",
    "pt-BR",
    "ru",
    "th",
    "tr",
    "vi",
    "zh-CN",
    "zh-TW",
}
FIELDS = {
    "InternalName",
    "Level",
    "Tier",
    "Cost",
    "BossTechnology",
    "Requirements",
    "Prerequisites",
    "UnlockItems",
    "UnlockBuildObjects",
    "UnlockPalSkill",
    "IconKind",
    "IconKey",
    "I18n",
}


def load_rows(filename):
    return json.loads((ASSETS / "data" / filename).read_text(encoding="utf-8"))


def test_build_24181527_technology_projection_is_complete():
    rows = load_rows("tech_data.json")

    assert len(rows) == 588
    assert sum(bool(row["UnlockBuildObjects"]) for row in rows.values()) == 217
    assert sum(bool(row["UnlockItems"]) for row in rows.values()) == 371
    # The case-insensitive Thunderdog_Ice -> ThunderDog_Ice join is the 124th.
    assert sum(row["IconKind"] == "pal" for row in rows.values()) == 124
    assert all(set(row) == FIELDS for row in rows.values())
    assert all(row_id == row["InternalName"] for row_id, row in rows.items())


def test_technology_locales_and_icons_resolve():
    rows = load_rows("tech_data.json")

    for row in rows.values():
        assert set(row["I18n"]) == LOCALES
        assert all(
            set(text) == {"Name", "Description", "Type"}
            and all(isinstance(value, str) and value for value in text.values())
            for text in row["I18n"].values()
        )
        assert bool(row["UnlockItems"]) is not bool(row["UnlockBuildObjects"])
        icon_root = "pals" if row["IconKind"] == "pal" else "tech"
        assert (ASSETS / "icons" / icon_root / f"{row['IconKey']}.png").is_file()
        if row["IconKind"] == "pal":
            assert not (ASSETS / "icons/tech" / f"{row['IconKey']}.png").exists()

    assert rows["Workbench"]["I18n"]["zh-CN"]["Type"] == "建筑"
    assert rows["Product_Axe_Grade_01"]["I18n"]["zh-CN"]["Type"] == "道具"
    assert len({text["Type"] for text in rows["Workbench"]["I18n"].values()}) > 1


def test_representative_requirements_prerequisites_and_pal_skill_join():
    rows = load_rows("tech_data.json")

    assert rows["Special_ElectricHatchingPalEgg"]["Requirements"] == {
        "DefeatTowerBoss": "DesertBoss",
        "ResearchID": "",
    }
    assert rows["Special_ElectricHatchingPalEgg"]["Prerequisites"] == [
        "Special_HatchingPalEgg"
    ]
    pal_gear = rows["SkillUnlock_Thunderdog_Ice"]
    assert pal_gear["UnlockItems"] == ["SkillUnlock_Thunderdog_Ice"]
    assert pal_gear["UnlockPalSkill"] == "ThunderDog_Ice"
    assert pal_gear["IconKind"] == "pal"
    assert pal_gear["IconKey"] == "ThunderDog_Ice"


def test_technology_icons_are_only_referenced_logical_files():
    rows = load_rows("tech_data.json")
    expected = {
        f"{row['IconKey']}.png" for row in rows.values() if row["IconKind"] != "pal"
    }
    actual = {path.name for path in (ASSETS / "icons/tech").glob("*.png")}

    assert actual == expected
    assert all(not name.startswith("T_") for name in actual)
