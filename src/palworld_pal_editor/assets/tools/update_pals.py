import copy
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from bs4 import BeautifulSoup
import requests
import json
import re
from pathlib import Path
from time import sleep
from PIL import Image

from palworld_pal_editor.assets.tools.paldb import hover_id, labeled_int

# URLs for the different languages
urls = {
    "en": "https://paldb.cc/en/",
    "zh-CN": "https://paldb.cc/cn/",
    "ja": "https://paldb.cc/ja/",
    "fr": "https://paldb.cc/fr/",
}


def pal_t(internal_name):
    return {
        "InternalName": internal_name,
        "Elements": ["Dark"],
        "Attacks": {},
        "Stats": {"HP": 0, "ATK": 0, "DEF": 0, "MELEE": 0, "CRAFTSPEED": 0, "FOOD": 0},
        "I18n": {"en": "", "zh-CN": "", "ja": "", "fr": ""},
        "SortingKey": {"paldeck": ""},
        "Suitabilities": suitabilities_t(),
        "BestWorkSuitability": None,
    }


def suitabilities_t():
    return {
        "EPalWorkSuitability::EmitFlame": 0,
        "EPalWorkSuitability::Watering": 0,
        "EPalWorkSuitability::Seeding": 0,
        "EPalWorkSuitability::GenerateElectricity": 0,
        "EPalWorkSuitability::Handcraft": 0,
        "EPalWorkSuitability::Collection": 0,
        "EPalWorkSuitability::Deforest": 0,
        "EPalWorkSuitability::Mining": 0,
        "EPalWorkSuitability::OilExtraction": 0,
        "EPalWorkSuitability::ProductMedicine": 0,
        "EPalWorkSuitability::Cool": 0,
        "EPalWorkSuitability::Transport": 0,
        "EPalWorkSuitability::MonsterFarm": 0,
    }


name_replace_map = {
    "PAL Genetic Research Unit Commander Victor & Shadowbeak": "Victor & Shadowbeak",
    "帕鲁基因研究部队-队长 维克托 & 异构格里芬": "维克托 & 异构格里芬",
    "パル遺伝子研究部隊 隊長 ヴィクター＆ゼノグリフ": "ヴィクター＆ゼノグリフ",
    "Commandant de l’Unité de Recherche sur les Gènes Victor & Shadowbeak": "Victor & Shadowbeak",
    "Rayne Syndicate Officer Zoe & Grizzbolt": "Zoe & Grizzbolt",
    "雷恩盗猎团的干部 佐伊 & 暴电熊": "佐伊 & 暴电熊",
    "レイン密猟団の幹部 ゾーイ＆エレパンダ": "ゾーイ＆エレパンダ",
    "Officiel du Syndicat de Rayne Zoe & Grizzbolt": "Zoe & Grizzbolt",
    "Free Pal Alliance Founder Lily & Lyleen": "Lily & Lyleen",
    "帕鲁保护团体-创始人 莉莉 & 百合女王": "莉莉 & 百合女王",
    "パル愛護団体 創始者 リリィ＆リリクイン": "リリィ＆リリクイン",
    "Membre Fondateur de la LPP Lily & Lyleen": "Lily & Lyleen",
    "PIDF Officer Marcus & Faleris": "Marcus & Faleris",
    "帕洛斯群岛自卫队干部 马库斯 & 荷鲁斯": "马库斯 & 荷鲁斯",
    "パルパゴス島自警団の幹部 マーカス＆ホルス": "マーカス＆ホルス",
    "Cadre de la Milice Populaire de Palpagos Marcus & Faleris": "Marcus & Faleris",
    "Brothers of the Eternal Pyre Soul Leader Axel & Orserk": "Axel & Orserk",
    "永炎同心会-灵魂领袖 阿克塞尔 & 波鲁杰克斯": "阿克塞尔 & 波鲁杰克斯",
    "永炎の同志 ソウルリーダー アクセル＆ボルゼクス": "アクセル＆ボルゼクス",
    "Chef Spirituel de la Confrérie des Flammes Éternelles Axel & Orserk": "Axel & Orserk",
    "Leader of the Moonflowers Saya & Selyne": "Saya & Selyne",
    "月花众的首领 纱夜 & 辉月伊": "纱夜 & 辉月伊",
    "月花衆の長 サヤ＆セレムーン": "サヤ＆セレムーン",
    "Chef du Clan des Fleurs Lunaires Saya & Selyne": "Saya & Selyne",
    "Jarl of Feybreak  Bjorn & Bastigor": "Bjorn & Bastigor",
    "天坠之民 首领 比约恩 & 霜牙王": "比约恩 & 霜牙王",
    "天落の民 首領 ビョルン＆ヒョウガオー": "ビョルン＆ヒョウガオー",
    "Habitant du Paradis Déchu (Chef) Björn & Bastigor": "Björn & Bastigor",
}


suitabilities_map = {
    "Kindling": "EPalWorkSuitability::EmitFlame",
    "Watering": "EPalWorkSuitability::Watering",
    "Planting": "EPalWorkSuitability::Seeding",
    "Generating Electricity": "EPalWorkSuitability::GenerateElectricity",
    "Handiwork": "EPalWorkSuitability::Handcraft",
    "Gathering": "EPalWorkSuitability::Collection",
    "Lumbering": "EPalWorkSuitability::Deforest",
    "Mining": "EPalWorkSuitability::Mining",
    "Oil Extraction": "EPalWorkSuitability::OilExtraction",
    "Medicine Production": "EPalWorkSuitability::ProductMedicine",
    "Cooling": "EPalWorkSuitability::Cool",
    "Transporting": "EPalWorkSuitability::Transport",
    "Farming": "EPalWorkSuitability::MonsterFarm",
}

els = {
    "Electric",
    "Dragon",
    "Neutral",
    "Grass",
    "Water",
    "Ice",
    "Dark",
    "Fire",
    "Ground",
}

TOOLS_DIR = Path(__file__).resolve().parent
ASSETS_DIR = TOOLS_DIR.parent
PAL_ICON_DIR = ASSETS_DIR / "icons" / "pals"
DATA_PATH = ASSETS_DIR / "data" / "pal_data.json"


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

def fetch_soup(url):
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            if soup.title is None:
                raise requests.RequestException(f"PalDB returned invalid HTML for {url}")
            return soup
        except requests.RequestException:
            if attempt == 2:
                raise
            sleep(2**attempt)


detail_cache = {}
DETAIL_PREFETCH_WORKERS = 16
DETAIL_PREFETCH_PALS = 8


def prefetch_detail_soups(keys):
    missing = list(dict.fromkeys(key for key in keys if key not in detail_cache))
    if not missing:
        return

    with ThreadPoolExecutor(
        max_workers=min(DETAIL_PREFETCH_WORKERS, len(missing))
    ) as executor:
        soups = executor.map(
            lambda key: fetch_soup(f"{urls[key[0]]}{key[1]}"), missing
        )
        detail_cache.update(zip(missing, soups))


def prefetch_pal_details(internal_names):
    keys = [
        (lang, pal_links[internal_name])
        for internal_name in internal_names[:DETAIL_PREFETCH_PALS]
        for lang in urls
    ]
    retained = set(keys)
    for key in list(detail_cache):
        if key[0] != "en" and key not in retained:
            detail_cache.pop(key)
    prefetch_detail_soups(keys)


def get_detail_soup(lang, link):
    cache_key = (lang, link)
    if cache_key in detail_cache:
        soup = detail_cache[cache_key]
        if lang != "en":
            detail_cache.pop(cache_key)
        return soup

    if lang != "en":
        return fetch_soup(f"{urls[lang]}{link}")

    detail_cache[cache_key] = fetch_soup(f"{urls[lang]}{link}")
    return detail_cache[cache_key]


def detail_internal_name(detail_soup):
    code_label = detail_soup.find("div", string=lambda value: value and value.strip() == "Code")
    if code_label is None:
        raise ValueError("PalDB detail page has no Code field")
    return code_label.find_next_sibling("div").get_text(strip=True)


def detail_suitabilities(basic_info_root, preserved):
    rows = (
        basic_info_root.find_all(
            "div",
            class_="border-bottom d-flex justify-content-between py-1 px-3",
        )
        if basic_info_root
        else []
    )
    if not rows:
        if any((preserved or {}).values()):
            raise ValueError("Expected work suitabilities were not found")
        return suitabilities_t()

    suitabilities = suitabilities_t()
    for row in rows:
        name = row.find("a").get_text(strip=True)
        level = row.find_all("div")[-1].get_text(strip=True).replace("Lv", "")
        suitabilities[suitabilities_map[name]] = int(level.strip())
    return suitabilities


def detail_best_work_suitability(detail_soup):
    for row in detail_soup.find_all("div"):
        columns = row.find_all("div", recursive=False)
        if columns and columns[0].get_text(" ", strip=True) == "BestWorkSuitability":
            value = columns[-1].get_text(strip=True)
            known_values = {
                *suitabilities_t(),
                "EPalWorkSuitability::None",
            }
            value = f"EPalWorkSuitability::{value}"
            if value in known_values:
                return value
            raise ValueError(f"Unknown BestWorkSuitability: {value}")
    raise ValueError("PalDB field 'BestWorkSuitability' was not found")


def extract_pals(existing_data=None):
    pal_data = {}
    if existing_data is None:
        existing_data = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    soup = fetch_soup(f'{urls["en"]}Pals')
    cards = soup.find_all("div", class_="col")
    for card in cards:
        # <span class="text-white-50 small">#1</span>, and extract the string after #
        paldeck_id = re.sub(
            r"#", "", card.find("span", class_="text-white-50 small").text
        )

        # <a class="itemname" data-hover="?s=Pals/SheepBall" href="Lamball">Lamball</a>
        name_node = card.find("a", class_="itemname")
        id_node = card.select_one('input[name="image[]"][value]')
        internal_name = id_node["value"] if id_node else None
        if not internal_name and name_node:
            internal_name = hover_id(name_node.get("data-hover", ""), "Pals")
        if not internal_name:
            continue
        link = name_node["href"]
        pal_links[internal_name] = link
        name = name_node.text.strip()
        print("# ", internal_name)
        print("\t", paldeck_id or None, internal_name, name)

        pal = editor_row(internal_name, existing_data)
        pal["SortingKey"]["paldeck"] = paldeck_id
        pal["I18n"]["en"] = name
        if not paldeck_id:
            pal["Invalid"] = True
        else:
            pal.pop("Invalid", None)

        icon_url = card.find(
            "img",
            {
                "src": re.compile(
                    r"https://cdn\.paldb\.cc/image/Pal/Texture/PalIcon/Normal/.+\.webp"
                )
            },
        )["src"]
        if icon_url:
            icon_path = PAL_ICON_DIR / f"{internal_name}.png"
            if not icon_path.exists():
                try:
                    print(f"downloading icon for {internal_name}")
                    response = requests.get(icon_url, timeout=10)
                    response.raise_for_status()
                    image = Image.open(BytesIO(response.content)).convert("RGBA")
                    image.save(icon_path, "PNG")
                except Exception as err:
                    print(
                        f"Failed to download/convert {icon_url} for {internal_name}: {err}"
                    )


        # # <button class="btn btn-sm border rounded" style="padding: 0.1rem;" data-filter="Handiwork1" data-bs-toggle="tooltip" data-bs-title="Handiwork"><img loading="lazy" src="https://cdn.paldb.cc/image/Pal/Texture/UI/InGame/T_icon_palwork_04.webp" class="size24">1</button>
        # suitabilities = suitabilities_t()
        # for el in card.find_all(
        #     "button", {"data-filter": re.compile(r"([a-zA-Z]+)(\d+)")}
        # ):
        #     suitability_name = suitabilities_map[re.sub(r"\d+", "", el["data-filter"])]
        #     suitability_value = int(re.sub(r"[a-zA-Z]+", "", el["data-filter"]))
        #     print("\t", suitability_name, ": ", suitability_value)
        #     if suitability_name not in suitabilities:
        #         raise (f"Unknown suitability: {suitability_name}")
        #     suitabilities[suitability_name] = suitability_value

        # if internal_name in name_set:
        #     with open(
        #         f"{external_res}/{internal_name}.json", "r", encoding="utf-8"
        #     ) as file:
        #         pal_json = json.load(file)
        #         suitabilities["EPalWorkSuitability::OilExtraction"] = (
        #             pal_json["Suitabilities"]["OilExtraction"] or 0
        #         )
        #         print("\t", "OilExtraction: ", suitabilities["EPalWorkSuitability::OilExtraction"])

        # pal["Suitabilities"] = suitabilities

        # <img loading="lazy" src="https://cdn.paldb.cc/image/Pal/Texture/UI/InGame/T_Icon_element_s_01.webp" class="size24" data-bs-toggle="tooltip" data-bs-title="Fire">
        elements = card.find_all(
            "img",
            {"data-bs-toggle": "tooltip", "data-bs-title": re.compile(r"[a-zA-Z]+")},
        )
        print("\t", [el["data-bs-title"] for el in elements])
        for el in elements:
            if el["data-bs-title"] not in els:
                raise ValueError(f"Unknown element: {el['data-bs-title']}")

        pal["Elements"] = [el["data-bs-title"] for el in elements]

        pal_data[internal_name] = pal

    return pal_data


def extract_pal_details(internal_name, link, pal):
    pal_variants = {}
    with ThreadPoolExecutor(max_workers=len(urls)) as executor:
        detail_soups = dict(
            zip(urls, executor.map(lambda lang: get_detail_soup(lang, link), urls))
        )

    for lang, detail_soup in detail_soups.items():

        if internal_name == "GYM_ElecPanda_2":
            # debug
            pass

        # <a class="itemname" data-hover="?s=Pals/SheepBall" href="Lamball">Lamball</a>
        anchor_node = next(
            (
                node
                for node in detail_soup.find_all("a", class_="itemname", href=link)
                if node.find_parent("div", class_="card itemPopup")
            ),
            None,
        )
        if anchor_node is None:
            raise ValueError(f"PalDB detail page has no primary item for {link}")
        
        i18n_name = anchor_node.text.strip()
        if i18n_name in name_replace_map:
            i18n_name = name_replace_map[i18n_name]
        if internal_name == "PlantSlime_Flower":
            i18n_name = f"{i18n_name} {'(Flower)' if lang in ['en', 'fr'] else '(花)'}"
        if internal_name == "BOSS_PlantSlime_Flower":
            i18n_name = f"{i18n_name} {'(Flower)' if lang in ['en', 'fr'] else '(花)'}"
        print("\t", lang, i18n_name)
        pal["I18n"][lang] = (
            i18n_name if (i18n_name != "en_text" and i18n_name != "-") else link
        )

        if lang == "en":
            basic_info_root = anchor_node.find_parent("div", class_="card itemPopup")
            pal["Suitabilities"] = detail_suitabilities(
                basic_info_root, pal.get("Suitabilities")
            )
            pal["BestWorkSuitability"] = detail_best_work_suitability(detail_soup)



            # <div class="d-flex justify-content-between p-2 align-items-center border-bottom">
            #   <div><img src="https://cdn.paldb.cc/image/Pal/Texture/UI/Main_Menu/T_icon_status_00.webp">Health</div>
            #   <div>105</div>
            # </div>
            # Get the health value, there is always an img with src="https://cdn.paldb.cc/image/Pal/Texture/UI/Main_Menu/T_icon_status_00.webp" before the health value
            stats_heading = detail_soup.find(
                "h5", class_="card-title text-info", string="Stats"
            )
            stats_root = stats_heading.find_parent("div", class_="card-body")
            health = labeled_int(stats_root, "Health")
            print("\t", "Health: ", health)
            food = labeled_int(stats_root, "Food")
            print("\t", "Food: ", food)
            # <div class="d-flex justify-content-between p-2 align-items-center border-bottom">
            #                 <div>MeleeAttack</div>
            #                 <div>70</div>
            #             </div>
            # Get the MeleeAttack values
            melee_attack = labeled_int(stats_root, "MeleeAttack")
            print("\t", "Melee Attack: ", melee_attack)
            attack = labeled_int(stats_root, "Attack")
            print("\t", "Attack: ", attack)
            defense = labeled_int(stats_root, "Defense")
            print("\t", "Defense: ", defense)
            work_speed = labeled_int(stats_root, "Work Speed")
            print("\t", "Work Speed: ", work_speed)

            pal["Stats"]["HP"] = health
            pal["Stats"]["ATK"] = attack
            pal["Stats"]["DEF"] = defense
            pal["Stats"]["MELEE"] = melee_attack
            pal["Stats"]["CRAFTSPEED"] = work_speed
            pal["Stats"]["FOOD"] = food

            skills_body = detail_soup.find(
                "h5", class_="card-title text-info", string="Active Skills"
            ).find_next("div")
            if skills_body:
                # Extract all <div class="col"> within the found card-body
                pal["Attacks"] = {}
                cols = skills_body.find_all("div", class_="col", recursive=True)
                for col in cols:
                    atk_node = col.find("a", attrs={"data-hover": True})
                    atk_internal_name = (
                        hover_id(atk_node["data-hover"], "Waza") if atk_node else None
                    )
                    if not atk_internal_name:
                        continue
                    parent_text = atk_node.parent.get_text(
                        strip=True
                    )  # Get text, removing extra spaces
                    level_match = re.search(
                        r"Lv\.\s*(\d+)", parent_text
                    )  # Extract the level
                    level = int(level_match.group(1)) if level_match else None
                    print("\t", atk_internal_name, "\t", level)

                    pal["Attacks"][atk_internal_name] = level

            # find variants
            tribes_row = (
                detail_soup.find("h5", class_="card-title text-info", string="Tribes")
                .find_next("table")
                .find_all("tr")
            )
            # <tr><td><a class="itemname" data-hover="?s=Pals/BOSS_SheepBall" href="Big_Floof_Lamball"><div class="size32alpha"></div><img loading="lazy" src="https://cdn.paldb.cc/image/Pal/Texture/PalIcon/Normal/T_SheepBall_icon_normal.webp" class="size32 rounded-circle border border-danger">Big Floof Lamball</a></td><td>Tribe Boss</td></tr>
            variant_refs = [
                (name_node["href"], name_node.text.strip())
                for tribe_row in tribes_row
                if (name_node := tribe_row.find("a", class_="itemname")) is not None
            ]
            internal_names_by_link = {
                known_link: key for key, known_link in pal_links.items()
            }
            unknown_links = list(
                dict.fromkeys(
                    link
                    for link, _name in variant_refs
                    if link not in internal_names_by_link
                )
            )
            prefetch_detail_soups(("en", link) for link in unknown_links)
            for v_link in unknown_links:
                v_internal_name = detail_internal_name(
                    get_detail_soup("en", v_link)
                )
                internal_names_by_link[v_link] = v_internal_name
                pal_links.setdefault(v_internal_name, v_link)

            for v_link, v_name in variant_refs:
                v_internal_name = internal_names_by_link[v_link]
                print("\tvariants - ", v_internal_name, v_name, v_link)
                if v_internal_name == internal_name:
                    continue
                pal_variants[v_internal_name] = v_name
    detail_cache.pop(("en", link), None)
    print(json.dumps(pal, indent=4, ensure_ascii=False))
    return pal_variants


def preserve_undiscovered_invalid(all_pals, existing_data):
    candidates_by_paldeck = {}
    for pal in all_pals.values():
        paldeck = pal.get("SortingKey", {}).get("paldeck")
        if paldeck:
            candidates_by_paldeck.setdefault(paldeck, []).append(pal)

    for internal_name, existing in existing_data.items():
        if internal_name in all_pals or not existing.get("Invalid"):
            continue

        preserved = editor_row(internal_name, existing_data)
        paldeck = preserved.get("SortingKey", {}).get("paldeck")
        candidates = candidates_by_paldeck.get(paldeck, [])
        matching = [
            pal
            for pal in candidates
            if pal.get("Suitabilities") == preserved.get("Suitabilities")
        ]
        best_values = {
            pal.get("BestWorkSuitability") for pal in (matching or candidates)
        }
        preserved["BestWorkSuitability"] = (
            best_values.pop()
            if len(best_values) == 1
            else "EPalWorkSuitability::None"
        )
        all_pals[internal_name] = preserved

def main():
    global pal_links
    pal_links = {}
    existing_data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    all_pals_raw = extract_pals(existing_data)
    all_pals = {}

    pal_internal_names = list(all_pals_raw.keys())
    while pal_internal_names:
        prefetch_pal_details(pal_internal_names)
        internal_name = pal_internal_names.pop(0)
        pal = all_pals_raw[internal_name]
        try:
            pal_variants = extract_pal_details(internal_name, pal_links[internal_name], pal)
        except Exception as err:
            raise RuntimeError(
                f"Failed to extract complete details for {internal_name}"
            ) from err
        for variant_internal_name in pal_variants:
            if variant_internal_name not in all_pals_raw:
                pal_internal_names.insert(0, variant_internal_name)
                variant_pal = editor_row(variant_internal_name, existing_data)
                variant_pal["SortingKey"]["paldeck"] = pal["SortingKey"]["paldeck"]
                variant_pal["InternalName"] = variant_internal_name
                variant_pal["I18n"]["en"] = pal_variants[variant_internal_name]
                all_pals_raw[variant_internal_name] = variant_pal

        if re.match(r"(GYM_[A-Za-z_]+?)(_2)$", internal_name):
            for lang in pal["I18n"]:
                pal["I18n"][lang] = pal["I18n"][lang] + " II"
        if re.match(r"^SUMMON_.+", internal_name):
            pal["Invalid"] = True
        if re.match(r"(GYM_[A-Za-z_]+?)(_\d+.+)", internal_name):
            pal["Invalid"] = True
        if re.match(r"^Quest_.+", internal_name):
            pal["Invalid"] = True
        if re.match(r"(RAID_[A-Za-z_]+?)(_\d+.+)", internal_name):
            pal["Invalid"] = True
        if re.match(r"^PREDATOR_.+", internal_name):
            pal["Invalid"] = True
        if re.match(r"(.+)_Oilrig", internal_name):
            pal["Invalid"] = True

        all_pals[internal_name] = pal

    preserve_undiscovered_invalid(all_pals, existing_data)
    output_path = TOOLS_DIR / "tmp_pal_data.json"
    output_path.write_text(
        json.dumps(all_pals, indent=4, ensure_ascii=False), encoding="utf-8"
    )


pal_links = {}


if __name__ == "__main__":
    main()
