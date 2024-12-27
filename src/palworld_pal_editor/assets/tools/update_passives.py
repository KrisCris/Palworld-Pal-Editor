from bs4 import BeautifulSoup
import requests
import json
import re

# URLs for the different languages
urls = {
    "en": "https://paldb.cc/en/Passive_Skills#PalPassiveSkills",
    "zh-CN": "https://paldb.cc/cn/Passive_Skills#%E5%B8%95%E9%B2%81%E8%A2%AB%E5%8A%A8%E6%8A%80%E8%83%BD",
    "ja": "https://paldb.cc/ja/Passive_Skills#%E3%83%91%E3%83%AB%E3%83%91%E3%83%83%E3%82%B7%E3%83%96%E3%82%B9%E3%82%AD%E3%83%AB",
    "fr": "https://paldb.cc/fr/Passive_Skills#PalCompétencespassives"
}

def clean_description(description):
    description = description.replace("(ToSelf)", "").strip()
    description = re.sub(r"(\d+)\s*%", r"\1%", description)
    description = re.sub(r"\s+", " ", description)
    description = re.sub(r"\s+\.", ".", description)
    description = re.sub(r"\s+。", ".", description)
    description = re.sub(r"\s+;", ";", description)
    return description

def parse_buffs(descriptions, buffs=None):
    buffs = {
        "b_Attack": 0.0,
        "b_Defense": 0.0,
        "b_CraftSpeed": 0.0,
        "b_MoveSpeed": 0.0
    } if buffs is None else buffs

    patterns = {
            "b_Attack": r"(\d+)%\s*(?:increase|decrease)\s*to\s*(attack|攻击|攻撃|attaque)|(attack|攻击|攻撃|attaque)\s*(?:increases|decreases|to)?\s*([+-]?\d+)%|([+-]?\d+)%\s*(attack|攻击|攻撃|attaque)",
            "b_Defense": r"(\d+)%\s*(?:increase|decrease)\s*to\s*(defense|防御|防御|défense)|(defense|防御|防御|défense)\s*(?:increases|decreases|to)?\s*([+-]?\d+)%|([+-]?\d+)%\s*(defense|防御|防御|défense)",
            "b_CraftSpeed": r"(\d+)%\s*(?:increase|decrease)\s*to\s*(work speed|工作速度|作業速度|vitesse de travail)|(work speed|工作速度|作業速度|vitesse de travail)\s*(?:increases|decreases|to)?\s*([+-]?\d+)%|([+-]?\d+)%\s*(work speed|工作速度|作業速度|vitesse de travail)",
            "b_MoveSpeed": r"(\d+)%\s*(?:increase|decrease)\s*to\s*(movement speed|移动速度|移動速度|vitesse de déplacement)|(movement speed|移动速度|移動速度|vitesse de déplacement)\s*(?:increases|decreases|to)?\s*([+-]?\d+)%|([+-]?\d+)%\s*(movement speed|移动速度|移動速度|vitesse de déplacement)"
    }

    for description in descriptions:
        for key, pattern in patterns.items():
            if buffs[key] != 0:
                continue
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                matches = [match.group(1), match.group(2), match.group(3), match.group(4)]
                print(matches)
                value = next((m for m in matches if m and any(char.isdigit() for char in m)), None)
                numeric_value = float(value) / 100
                if "decreases" in description.lower():
                    numeric_value = -numeric_value
                buffs[key] = numeric_value
    return buffs

def extract_description_list(description_div):
    description_list = []

    for child in description_div.children:
        if child.name == "div":
            nested_divs = child.find_all("div", recursive=False)
            if len(nested_divs) > 0:
                for nested_div in nested_divs:
                    description_list.append(nested_div.get_text(separator=" ", strip=True))
            else:
                inner_html = child.decode_contents()
                parts = re.split('<br>|<br/>|<br />', inner_html)
                for part in parts:
                    clean_text = BeautifulSoup(part, 'html.parser').get_text(separator=" ", strip=True)
                    if clean_text:
                        description_list.append(clean_text)
        else:
            continue

    return [clean_description(item.strip()) for item in description_list if item.strip()]

def get_node_id(lang):
    if lang == "en":
        return "PalPassiveSkills"
    elif lang == "zh-CN":
        return "帕鲁被动技能"
    elif lang == "ja":
        return "パルパッシブスキル"
    elif lang == "fr":
        return "PalCompétencespassives"

def extract_skills(html_content, lang):
    soup = BeautifulSoup(html_content, 'html.parser')
    pal_passive_skills = soup.find(id=get_node_id(lang))
    skills_data = {}

    if pal_passive_skills:
        rows = pal_passive_skills.find_all("div", class_="col")
        for row in rows:
            # Find the border div
            border_div = row.find("div", class_="border")
            if not border_div:
                continue

            # Find the div containing the class for rating (passive_banner_rankX)
            rating_div = border_div.find("div", class_=re.compile(r"passive_banner_rank"))
            if not rating_div:
                continue

            # Extract the rating from the class name
            rating_class = next((cls for cls in rating_div.get("class", []) if "passive_banner_rank" in cls), None)
            rating = int(rating_class.replace("passive_banner_rank", "").replace("-", "")) if rating_class else 0
            rating = -rating if "rank-" in rating_class else rating  # Adjust for negative ratings

            # Extract the internal name and skill name
            name_div = rating_div.find("div", class_=re.compile(r"passive-rank"))
            if not name_div:
                continue

            name = name_div.text.strip()
            internal_name = name_div.get("data-hover", "").split("/")[-1]

            # Extract the description
            description_div = border_div.find("div", class_="p-2")
            print(description_div.text)
            description_list = extract_description_list(description_div)
            print(description_list)

            buffs = parse_buffs(description_list, skills_data.get("internal_name",{}).get("Buff",None))

            # Initialize or update the skill data
            if internal_name not in skills_data:
                skills_data[internal_name] = {
                    "InternalName": internal_name,
                    "Rating": rating,
                    "I18n": {
                        "en": {"Name": "", "Description": ""},
                        "zh-CN": {"Name": "", "Description": ""},
                        "ja": {"Name": "", "Description": ""},
                        "fr": {"Name": "", "Description": ""}
                    },
                    "Buff": buffs
                }

            # Update the i18n field for the current language
            skills_data[internal_name]["I18n"][lang] = {
                "Name": name,
                "Description": " ".join(description_list)
            }

    return skills_data

# Fetch and parse HTML for each language
all_skills = {}
for lang, url in urls.items():
    response = requests.get(url)
    if response.status_code == 200:
        skills = extract_skills(response.text, lang)
        for skill_name, skill_data in skills.items():
            if skill_name not in all_skills:
                all_skills[skill_name] = skill_data
            else:
                all_skills[skill_name]["I18n"][lang] = skill_data["I18n"][lang]

# Convert to JSON
skills_json = json.dumps(all_skills, indent=4, ensure_ascii=False)

# Save the JSON to a file
with open("tmp_passive_skills.json", "w", encoding="utf-8") as file:
    file.write(skills_json)

print("Passive skills data extracted and saved to 'tmp_passive_skills.json'.")