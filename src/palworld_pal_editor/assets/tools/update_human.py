import copy
import time
from bs4 import BeautifulSoup
import requests
import json
import re
import os
from urllib.parse import quote

urls = {
    "en": "https://paldb.cc/en/NPCs_Table",
    "zh-CN": "https://paldb.cc/cn/NPCs_Table",
    "ja": "https://paldb.cc/ja/NPCs_Table",
    "fr": "https://paldb.cc/fr/NPCs_Table",
}


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
        "SortingKey": {},
        "Suitabilities": suitabilities_t(),
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


def extract_pals():
    pal_data = {}

    for lang in urls:
        url = urls[lang]
        response = requests.get(url)
        while response.status_code != 200:
            print(f"Failed to fetch {url}")
            time.sleep(5)
            response = requests.get(url)

        soup = BeautifulSoup(response.text, "html.parser")
        cards = soup.find_all("div", class_="col")

        for card in cards:
            # <a class="itemname" data-hover="?s=Pals/SheepBall" href="Lamball">Lamball</a>
            name_node = card.find(
                "a", attrs={"data-hover": re.compile(r"\?s=Pals/.+")}
            )
            internal_name = name_node["data-hover"].split("/")[-1].strip()
            name = name_node.text.strip()
            print("# ", internal_name, name)
            if internal_name in pal_data:
                pal = pal_data[internal_name]
            else:
                pal = pal_t(internal_name)
            if name in ["en_text", "-", "en text"]:
                if lang == "en":
                    pal["I18n"][lang] = internal_name
                else:
                    pal["I18n"][lang] = pal["I18n"]["en"]
            else:
                pal["I18n"][lang] = name

            pal_data[internal_name] = pal

    return pal_data

all_pals_raw = extract_pals()

pal_json = json.dumps(all_pals_raw, indent=4, ensure_ascii=False)
with open("tmp_human_data.json", "w", encoding="utf-8") as file:
    file.write(pal_json)