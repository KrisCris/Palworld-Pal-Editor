import json
from pathlib import Path
import re

from bs4 import BeautifulSoup
import requests


URL_ROOTS = {
    "en": "https://paldb.cc/en/",
    "zh-CN": "https://paldb.cc/cn/",
    "ja": "https://paldb.cc/ja/",
    "fr": "https://paldb.cc/fr/",
}

PAL_SECTION_IDS = {
    "en": "PalPassiveSkills",
    "zh-CN": "帕鲁被动技能",
    "ja": "パルパッシブスキル",
    "fr": "PalCompétencespassives",
}

TOOLS_DIR = Path(__file__).resolve().parent
EXTRA_PAL_PASSIVE_IDS = {"MiniNushi"}


def fetch_soup(url):
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def clean_description(description):
    description = description.replace("(ToSelf)", "").strip()
    description = re.sub(r"(\d+)\s*%", r"\1%", description)
    description = re.sub(r"\s+", " ", description)
    description = re.sub(r"\s+([.;。])", r"\1", description)
    return description


def empty_buffs():
    return {
        "b_Attack": 0.0,
        "b_Defense": 0.0,
        "b_CraftSpeed": 0.0,
        "b_MoveSpeed": 0.0,
    }


def parse_buffs(description):
    buffs = empty_buffs()
    labels = {
        "b_Attack": "attack",
        "b_Defense": "defense",
        "b_CraftSpeed": "work speed",
        "b_MoveSpeed": "movement speed",
    }
    for key, label in labels.items():
        match = re.search(
            rf"{label}\s*(?:increases?|decreases?)?\s*([+-]?\d+)%",
            description,
            re.IGNORECASE,
        )
        if match:
            buffs[key] = float(match.group(1)) / 100
            continue

        match = re.search(
            rf"([+-]?\d+)%\s*(increase|decrease)\w*\s+"
            rf"(?:in|to)\s+{label}\b",
            description,
            re.IGNORECASE,
        )
        if match:
            value = float(match.group(1)) / 100
            if match.group(2).lower().startswith("decrease") and value > 0:
                value = -value
            buffs[key] = value
    return buffs


def table_names(soup):
    names = {}
    for row in soup.select("div.col"):
        box = row.select_one(".flex-grow-1.mx-2")
        code_node = box.find("div", recursive=False) if box else None
        if code_node is None:
            continue
        internal_name = code_node.get_text(strip=True)
        name = " ".join(
            text.strip()
            for text in box.find_all(string=True, recursive=False)
            if text.strip()
        )
        names[internal_name] = name
    return names


def passive_rows(soup, section_id=None):
    root = soup.find(id=section_id) if section_id else soup
    if root is None:
        return
    for row in root.select("div.col"):
        name_node = row.find("div", class_=re.compile(r"^passive-rank-?\d+$"))
        rating_node = row.find("div", class_=re.compile(r"passive_banner_rank-?\d+"))
        description_node = row.find("div", class_="p-2")
        if name_node is None or rating_node is None or description_node is None:
            continue
        rating_class = next(
            value
            for value in rating_node.get("class", [])
            if value.startswith("passive_banner_rank")
        )
        rating = int(rating_class.removeprefix("passive_banner_rank"))
        description = clean_description(
            " ".join(description_node.stripped_strings)
        )
        yield name_node.get_text(strip=True), rating, description


def extract_skills():
    pages = {
        lang: {
            "table": fetch_soup(f"{root}PassiveSkills_Table"),
            "skills": fetch_soup(f"{root}Passive_Skills"),
        }
        for lang, root in URL_ROOTS.items()
    }
    locale_names = {
        lang: table_names(page["table"]) for lang, page in pages.items()
    }
    en_ids_by_name = {name: key for key, name in locale_names["en"].items()}

    skills = {}
    for name, rating, description in passive_rows(
        pages["en"]["skills"], PAL_SECTION_IDS["en"]
    ):
        internal_name = en_ids_by_name.get(name)
        if internal_name is None:
            raise ValueError(f"No PassiveSkills_Table ID for {name!r}")
        skills[internal_name] = {
            "InternalName": internal_name,
            "Rating": rating,
            "I18n": {
                lang: {"Name": "", "Description": ""} for lang in URL_ROOTS
            },
            "Buff": parse_buffs(description),
        }

    all_en_rows = {
        name: (rating, description)
        for name, rating, description in passive_rows(pages["en"]["skills"])
    }
    for internal_name in EXTRA_PAL_PASSIVE_IDS:
        name = locale_names["en"][internal_name]
        rating, description = all_en_rows[name]
        skills[internal_name] = {
            "InternalName": internal_name,
            "Rating": rating,
            "I18n": {
                lang: {"Name": "", "Description": ""} for lang in URL_ROOTS
            },
            "Buff": parse_buffs(description),
        }

    for lang, page in pages.items():
        target_by_name = {
            locale_names[lang][internal_name]: internal_name
            for internal_name in skills
            if internal_name in locale_names[lang]
        }
        for name, _rating, description in passive_rows(page["skills"]):
            internal_name = target_by_name.get(name)
            if internal_name:
                skills[internal_name]["I18n"][lang] = {
                    "Name": name,
                    "Description": description,
                }

    return skills


def main():
    output_path = TOOLS_DIR / "tmp_passive_skills.json"
    output_path.write_text(
        json.dumps(extract_skills(), indent=4, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Passive skills data extracted and saved to {output_path.name!r}.")


if __name__ == "__main__":
    main()
