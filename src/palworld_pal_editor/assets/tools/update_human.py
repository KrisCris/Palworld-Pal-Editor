import copy
from bs4 import BeautifulSoup
import requests
import json
from pathlib import Path

from palworld_pal_editor.assets.tools.paldb import hover_id

urls = {
    "en": "https://paldb.cc/en/NPCs_Table",
    "zh-CN": "https://paldb.cc/cn/NPCs_Table",
    "ja": "https://paldb.cc/ja/NPCs_Table",
    "fr": "https://paldb.cc/fr/NPCs_Table",
}

TOOLS_DIR = Path(__file__).resolve().parent
DATA_PATH = TOOLS_DIR.parent / "data" / "human_data.json"


def pal_t(internal_name):
    return {
        "InternalName": internal_name,
        "Elements": [],
        "Attacks": {"EPalWazaID::Human_Punch": 1},
        "Human": True,
        "I18n": {
            "en": "",
            "zh-CN": "",
            "ja": "",
            "fr": "",
        },
        "SortingKey": {"paldeck": ""},
        "Stats": {
            "HP": 100,
            "ATK": 100,
            "DEF": 100,
            "MELEE": 100,
            "CRAFTSPEED": 100,
            "FOOD": 100,
        },
        "Suitabilities": suitabilities_t(),
        "HasIcon": False,
    }


def suitabilities_t():
    return {
        "EPalWorkSuitability::EmitFlame": 0,
        "EPalWorkSuitability::Watering": 0,
        "EPalWorkSuitability::Seeding": 0,
        "EPalWorkSuitability::GenerateElectricity": 0,
        "EPalWorkSuitability::Handcraft": 1,
        "EPalWorkSuitability::Collection": 0,
        "EPalWorkSuitability::Deforest": 0,
        "EPalWorkSuitability::Mining": 0,
        "EPalWorkSuitability::OilExtraction": 0,
        "EPalWorkSuitability::ProductMedicine": 0,
        "EPalWorkSuitability::Cool": 0,
        "EPalWorkSuitability::Transport": 0,
        "EPalWorkSuitability::MonsterFarm": 0,
    }


def editor_row(internal_name, existing_data):
    template = pal_t(internal_name)
    row = copy.deepcopy(existing_data.get(internal_name, template))
    row["InternalName"] = internal_name
    for key, value in template.items():
        row.setdefault(key, copy.deepcopy(value))
    for lang in urls:
        row["I18n"].setdefault(lang, "")
    for key, value in template["Stats"].items():
        row["Stats"].setdefault(key, value)
    for key, value in template["Suitabilities"].items():
        row["Suitabilities"].setdefault(key, value)
    return row


def apply_locale_name(row, lang, name):
    current = row["I18n"].get(lang, "")
    if name.strip().lower().replace("_", " ") in {"en text", "-"}:
        row["I18n"][lang] = (
            current
            or row["I18n"].get("en")
            or row["InternalName"]
        )
    elif current and name.casefold() in current.casefold() and len(name) < len(current):
        # PalDB's NPC table sometimes drops a title/prefix that the editor already has.
        return
    else:
        row["I18n"][lang] = name


def extract_pals(existing_data=None):
    pal_data = {}
    if existing_data is None:
        existing_data = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    for lang in urls:
        url = urls[lang]
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        cards = soup.find_all("div", class_="col")

        for card in cards:
            # <a class="itemname" data-hover="?s=Pals/SheepBall" href="Lamball">Lamball</a>
            name_node = card.find("a", attrs={"data-hover": True})
            internal_name = (
                hover_id(name_node["data-hover"], "Pals") if name_node else None
            )
            if not internal_name:
                continue
            name = name_node.text.strip()
            print("# ", internal_name, name)
            if internal_name in pal_data:
                pal = pal_data[internal_name]
            else:
                pal = editor_row(internal_name, existing_data)
            apply_locale_name(pal, lang, name)

            pal_data[internal_name] = pal

    for pal in pal_data.values():
        fallback = pal["I18n"]["en"] or pal["InternalName"]
        for lang in urls:
            pal["I18n"][lang] = pal["I18n"][lang] or fallback
    return pal_data

def main():
    output_path = TOOLS_DIR / "tmp_human_data.json"
    output_path.write_text(
        json.dumps(extract_pals(), indent=4, ensure_ascii=False), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
