import copy
import time
from bs4 import BeautifulSoup
import requests
import json
import re
import os
from urllib.parse import quote

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
        "I18n": {"en": "", "zh-CN": "", "ja": ""},
        "SortingKey": {"paldeck": ""},
        "Suitabilities": suitabilities_t(),
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
        # "EPalWorkSuitability::OilExtraction": 0,
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
    # "Oil Extraction": "EPalWorkSuitability::OilExtraction",
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

external_res = (
)


def get_json_names(directory):
    try:
        json_files = [f for f in os.listdir(directory) if f.endswith(".json")]
        names = {os.path.splitext(f)[0] for f in json_files}
        return names
    except Exception:
        print(f"Directory {directory} not found.")
        return set()


name_set = get_json_names(external_res)


def extract_pals():
    pal_data = {}

    response = requests.get(f"{urls["en"]}Pals")
    while response.status_code != 200:
        print(f"Failed to fetch {urls["en"]}Pals")
        time.sleep(5)
        response = requests.get(f"{urls["en"]}Pals")

    soup = BeautifulSoup(response.text, "html.parser")
    cards = soup.find_all("div", class_="col")
    for card in cards:
        # <span class="text-white-50 small">#1</span>, and extract the string after #
        paldeck_id = re.sub(
            r"#", "", card.find("span", class_="text-white-50 small").text
        )

        # <a class="itemname" data-hover="?s=Pals/SheepBall" href="Lamball">Lamball</a>
        name_node = card.find(
            "a", attrs={"class": "itemname", "data-hover": re.compile(r"\?s=Pals/.+")}
        )
        link = name_node["href"]
        internal_name = name_node["data-hover"].split("/")[-1].strip()
        pal_links[internal_name] = link
        name = name_node.text.strip()
        print("# ", internal_name)
        print("\t", paldeck_id or None, internal_name, name)

        pal = pal_t(internal_name)
        pal["SortingKey"]["paldeck"] = paldeck_id
        pal["I18n"]["en"] = name
        if not paldeck_id:
            pal["Invalid"] = True

        icon_url = card.find(
            "img",
            {
                "src": re.compile(
                    r"https://cdn\.paldb\.cc/image/Pal/Texture/PalIcon/Normal/.+\.webp"
                )
            },
        )["src"]
        if icon_url:
            png_filename = f"{internal_name}.png"
            if not os.path.exists(f"../icons/pals/{png_filename}"):
                try:
                    print(f"downloading icon for {internal_name}")
                    response = requests.get(icon_url, timeout=10)
                    if response.status_code == 200:
                        # Open the image (likely WebP) and convert to RGBA
                        with open(f"./{png_filename}", "wb") as f:
                            f.write(response.content)
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
                raise (f"Unknown element: {el['data-bs-title']}")

        pal["Elements"] = [el["data-bs-title"] for el in elements]

        pal_data[internal_name] = pal

    return pal_data


def extract_pal_details(internal_name, link, pal):
    pal_variants = {}
    for lang in urls:
        url = f"{urls[lang]}{link}"
        response = requests.get(url)
        while response.status_code != 200:
            print(f"Failed to fetch {url}")
            time.sleep(10)
            response = requests.get(url)

        detail_soup = BeautifulSoup(response.text, "html.parser")

        if internal_name == "GYM_ElecPanda_2":
            # debug
            pass

        # <a class="itemname" data-hover="?s=Pals/SheepBall" href="Lamball">Lamball</a>
        anchor_node = detail_soup.find(
            "a",
            attrs={"class": "itemname", "data-hover": f"?s=Pals/{internal_name}"},
            string=True,
        )
        potential_root = anchor_node.find_parent(
            "div", attrs={"id": re.compile(r"Pals(?:-\d+)?")}
        )
        if potential_root:
            detail_soup = potential_root
        
        i18n_name = anchor_node.text.strip()
        if i18n_name in name_replace_map:
            i18n_name = name_replace_map[i18n_name]
        if internal_name == "PlantSlime_Flower":
            i18n_name = f"{i18n_name} {"(Flower)" if lang in ["en", "fr"] else "(花)"}"
        if internal_name == "BOSS_PlantSlime_Flower":
            i18n_name = f"{i18n_name} {"(Flower)" if lang in ["en", "fr"] else "(花)"}"
        print("\t", lang, i18n_name)
        pal["I18n"][lang] = (
            i18n_name if (i18n_name != "en_text" and i18n_name != "-") else link
        )

        if lang == "en":
            basic_info_root = anchor_node.find_parent("div", class_="card itemPopup")
            if basic_info_root:
                # <div class="border-bottom d-flex justify-content-between py-1 px-3">
                #     <div><a href="Lumbering"><img loading="lazy" src="https://cdn.paldb.cc/image/Pal/Texture/UI/InGame/T_icon_palwork_06.webp" class="size24"> Lumbering</a></div><div><span style="font-size:x-small">Lv</span>3</div>
                # </div>
                # Extract all <div class="border-bottom d-flex justify-content-between py-1 px-3"> within the found card-body and locate the text value of the first <a> tag and the Lv of the div
                suitability_divs = basic_info_root.find_all("div", class_="border-bottom d-flex justify-content-between py-1 px-3")
                if suitability_divs:
                    suitabilities = suitabilities_t()
                    for div in suitability_divs:
                        name = div.find("a").get_text(strip=True)
                        level = div.find_all("div")[-1].get_text(strip=True).replace("Lv", "").strip()
                        suitabilities[suitabilities_map[name]] = int(level)
                    pal["Suitabilities"] = suitabilities
                else:
                    print(pal["I18n"]["en"], "Suitabilities not found")
                    pal.pop("Suitabilities", None)
            else:
                print(pal["I18n"]["en"], "Suitabilities not found")
                pal.pop("Suitabilities", None)



            # <div class="d-flex justify-content-between p-2 align-items-center border-bottom">
            #   <div><img src="https://cdn.paldb.cc/image/Pal/Texture/UI/Main_Menu/T_icon_status_00.webp">Health</div>
            #   <div>105</div>
            # </div>
            # Get the health value, there is always an img with src="https://cdn.paldb.cc/image/Pal/Texture/UI/Main_Menu/T_icon_status_00.webp" before the health value
            health = int(
                detail_soup.find(
                    "img",
                    {
                        "src": "https://cdn.paldb.cc/image/Pal/Texture/UI/Main_Menu/T_icon_status_00.webp"
                    },
                )
                .find_next("div")
                .text
            )
            print("\t", "Health: ", health)
            food = int(
                detail_soup.find_all(
                    "img",
                    {
                        "src": "https://cdn.paldb.cc/image/Pal/Texture/UI/Main_Menu/T_Icon_foodamount_off.webp"
                    },
                )[-1]
                .find_next("div")
                .text
            )
            print("\t", "Food: ", food)
            # <div class="d-flex justify-content-between p-2 align-items-center border-bottom">
            #                 <div>MeleeAttack</div>
            #                 <div>70</div>
            #             </div>
            # Get the MeleeAttack values
            melee_attack = int(
                detail_soup.find("div", string="MeleeAttack").find_next("div").text
            )
            print("\t", "Melee Attack: ", melee_attack)
            attack = int(
                detail_soup.find(
                    "img",
                    {
                        "src": "https://cdn.paldb.cc/image/Pal/Texture/UI/Main_Menu/T_icon_status_02.webp"
                    },
                )
                .find_next("div")
                .text
            )
            print("\t", "Attack: ", attack)
            defense = int(
                detail_soup.find(
                    "img",
                    {
                        "src": "https://cdn.paldb.cc/image/Pal/Texture/UI/Main_Menu/T_icon_status_03.webp"
                    },
                )
                .find_next("div")
                .text
            )
            print("\t", "Defense: ", defense)
            work_speed = int(
                detail_soup.find(
                    "img",
                    {
                        "src": "https://cdn.paldb.cc/image/Pal/Texture/UI/Main_Menu/T_icon_status_05.webp"
                    },
                )
                .find_next("div")
                .text
            )
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
                    atk_node = col.find(
                        "a", attrs={"data-hover": re.compile(r"\?s=Waza/.+")}
                    )
                    atk_internal_name = (
                        atk_node["data-hover"]
                        .split("/")[-1]
                        .replace("%3A%3A", "::")
                        .strip()
                    )
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
            for tribe_row in tribes_row:
                name_node = tribe_row.find(
                    "a",
                    attrs={
                        "class": "itemname",
                        "data-hover": re.compile(r"\?s=Pals/.+"),
                    },
                )
                v_link = name_node["href"]
                v_internal_name = name_node["data-hover"].split("/")[-1].strip()
                if v_internal_name not in pal_links:
                    pal_links[v_internal_name] = v_link
                v_name = name_node.text.strip()
                print("\tvariants - ", v_internal_name, v_name, v_link)
                if v_internal_name == internal_name:
                    continue
                pal_variants[v_internal_name] = v_name
    print(json.dumps(pal, indent=4, ensure_ascii=False))
    return pal_variants

pal_links = {}
all_pals_raw = extract_pals()
all_pals = {}

pal_internal_names = list(all_pals_raw.keys())
while len(pal_internal_names) > 0:
    internal_name = pal_internal_names.pop(0)
    pal = all_pals_raw[internal_name]
    try:
        pal_variants = extract_pal_details(internal_name, pal_links[internal_name], pal)
    except:
        print(f"Failed to extract details for {internal_name}")
        continue
    for variant_internal_name in pal_variants:
        if (
            variant_internal_name not in all_pals_raw
            # and "BOSS" not in variant_internal_name
            # and "Boss" not in variant_internal_name
        ):
            pal_internal_names.insert(0, variant_internal_name)
            variant_pal = copy.deepcopy(pal)
            variant_pal["InternalName"] = variant_internal_name
            variant_pal["I18n"]["en"] = pal_variants[variant_internal_name]
            variant_pal["Suitabilities"] = suitabilities_t()
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

pal_json = json.dumps(all_pals, indent=4, ensure_ascii=False)
with open("tmp_pal_data.json", "w", encoding="utf-8") as file:
    file.write(pal_json)
