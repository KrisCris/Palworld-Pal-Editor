from bs4 import BeautifulSoup
import requests
import json
import re

# URLs for the different languages
urls = {
    "en": "https://paldb.cc/en/Active_Skills",
    "zh-CN": "https://paldb.cc/cn/Active_Skills",
    "ja": "https://paldb.cc/ja/Active_Skills",
    "fr": "https://paldb.cc/fr/Active_Skills"
}

def skill(internal_name):
    return {
        "InternalName": internal_name,
        "Element": "",
        "CT": -1,
        "Power": -1,
        "I18n": {
            "en": {
                "Name":"",
                "Description": ""
            },
            "zh-CN": {
                "Name":"",
                "Description": ""
            },
            "ja": {
                "Name":"",
                "Description": ""
            },
            "fr": {
                "Name":"",
                "Description": ""
            }
        },
        "UniqueSkill": False,
        "SkillFruit": False,
    }

def clean_description(description):
    description = description.strip().replace("。 ", "。").replace("， ", "，").replace("、 ", "、")
    description = re.sub(r'\s+', ' ', description)
    description = re.sub(r"\s+", " ", description)
    description = re.sub(r"\s+\.", ".", description)
    description = re.sub(r"\s+。", ".", description)
    description = re.sub(r"\s+;", ";", description)
    return description

def get_node_id(lang, type):
    if lang == "en":
        if type == "ActiveSkills":
            return "ActiveSkills"
        else:
            return "BossActiveSkills"
    elif lang == "zh-CN":
        if type == "ActiveSkills":
            return "主动技能"
        else:
            return "Boss主动技能"
    elif lang == "ja":
        if type == "ActiveSkills":
            return "アクティブスキル"
        else:
            return "Bossアクティブスキル"
    elif lang == "fr":
        if type == "ActiveSkills":
            return "Compétencesactives"
        else:
            return "BossCompétencesactives"
        
def extract_skills():
    skills_data = {}

    for lang, url in urls.items():
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            for type in ["ActiveSkills", "BossActiveSkills"]:
                skills_div = soup.find(id=get_node_id(lang, type))

                if skills_div:
                    cards = skills_div.find_all("div", class_="card itemPopup")
                    for card in cards:
                        name_node = card.find('a', attrs={'data-hover': re.compile(r'\?s=Waza/.+')})

                        internal_name = name_node['data-hover'].split('/')[-1].replace('%3A%3A', '::').strip()
                        name = name_node.text.strip()
                        desc = clean_description(card.find('div', attrs={'class': "card-body"}).text)
                        if internal_name in skills_data:
                            skills_data[internal_name]["I18n"][lang] = {
                                "Name": name,
                                "Description": desc
                            }
                            continue

                        skill_data = skill(internal_name)
                        skill_data["I18n"][lang] = {
                            "Name": name,
                            "Description": desc
                        }
                        
                        skill_data["UniqueSkill"] = True if card.find('img', {'data-bs-title': "Will not inherit"}) else False

                        try:
                            el = card.find('span', {'style': "padding-left: 35px"}).text
                            skill_data["Element"] = el

                            ct_pw = card.find_all('span', {'style': "color: #73ffff"})

                            ct = int(ct_pw[0].text)
                            skill_data["CT"] = ct

                            power = int(ct_pw[1].text)
                            skill_data["Power"] = power

                            fruit = card.find('img', {'src': f"https://cdn.paldb.cc/image/Others/InventoryItemIcon/Texture/T_itemicon_Consume_SkillCard_{el}.webp"})

                            if fruit:
                                skill_data["SkillFruit"] = True
                        except:
                            print(f"{card.find_all('span')}")


                        print(json.dumps(skill_data, indent=4))
                        skills_data[skill_data['InternalName']] = skill_data
    return skills_data

# Fetch and parse HTML for each language
all_skills = extract_skills()
skills_json = json.dumps(all_skills, indent=4, ensure_ascii=False)
with open("tmp_pal_attacks.json", "w", encoding="utf-8") as file:
    file.write(skills_json)