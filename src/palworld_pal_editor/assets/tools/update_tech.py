import copy
from io import BytesIO
import time
from bs4 import BeautifulSoup
import requests
import json
import re
import os
from urllib.parse import quote
from PIL import Image

urls = {
    "en": "https://paldb.cc/en/Technologies",
    "zh-CN": "https://paldb.cc/cn/Technologies",
    "ja": "https://paldb.cc/ja/Technologies",
    "fr": "https://paldb.cc/fr/Technologies",
}

def tech_t(internal_name):
    return {
        "InternalName": internal_name,
        "Level": 0,
        "I18n": {"en": {"Name": "", "Type": ""}},
        "BossTechnology": False,
    }

def extract_techs():
    tech_data = {}

    for lang in urls:
        url = urls[lang]
        response = requests.get(url)
        while response.status_code != 200:
            print(f"Failed to fetch {url}")
            time.sleep(5)
            response = requests.get(url)

        soup = BeautifulSoup(response.text, "html.parser")
        rows = soup.select("div.col.pt-2.pb-1.border-bottom")
        for row in rows:
            # 1) Extract the "Level" from the first d-inline-block with a position: relative style
            #    e.g. <div class="d-inline-block" style="position: relative;height: 128px;width:64px;"> 
            level_div = row.select_one('div.d-inline-block[style^="position: relative"]')
            
            level = 0
            if level_div:
                # The numeric level is the text inside that nested <div>, e.g. "1"
                raw_level_text = level_div.get_text(strip=True)
                try:
                    level = int(raw_level_text)
                except ValueError:
                    level = 0  # fallback if parsing fails

            # 2) Extract all .hoverTech items in this row
            tech_items = row.select('div.d-inline-block.hoverTech')
            for tech_div in tech_items:
                # Example: data-hover="?s=Technology/Workbench"
                data_hover = tech_div.get("data-hover", "")
                
                # Extract what's after "Technology/" 
                # e.g. "?s=Technology/Workbench" → "Workbench"
                internal_name = None
                parts = data_hover.split("Technology/")
                if len(parts) > 1:
                    internal_name = parts[1].strip()
                
                # If for some reason we don't find "Technology/", skip
                if not internal_name:
                    continue
                
                # Extract the "Type" from the hoverTechHeader
                # e.g. <div class="hoverTechHeader">Structures</div>
                tech_type_div = tech_div.select_one("div.hoverTechHeader")
                tech_type = tech_type_div.get_text(strip=True) if tech_type_div else ""
                
                # Extract the English "Name" from the hoverTechFooter
                # e.g. <div class="hoverTechFooter">Primitive Workbench</div>
                tech_name_div = tech_div.select_one("div.hoverTechFooter")
                tech_name = tech_name_div.get_text(strip=True) if tech_name_div else ""
                
                # Check if this is a boss technology (class="BossTechnology")
                classes = tech_div.get("class", [])
                boss_technology = ("BossTechnology" in classes)
                
                # Extract the icon URL from inline style
                # e.g. style="background-image: url(https://cdn.../T_icon_buildObject_WorkBench.webp);"
                style_attr = tech_div.get("style", "")
                match = re.search(r'url\((.*?)\)', style_attr)
                icon_url = match.group(1) if match else ""
                
                if icon_url:
                    png_filename = f"{internal_name}.png"
                    if "SkillUnlock_" in internal_name:
                        png_filename = f"{internal_name.replace('SkillUnlock_', '')}.png"
                        if not os.path.exists(f"/Users/connlost/Coding/Palworld-Pal-Editor/src/palworld_pal_editor/assets/icons/pals/{png_filename}"):
                            print(f"Missing Pal Skill Unlock {png_filename}")
                    elif not os.path.exists(png_filename):
                        try:
                            response = requests.get(icon_url, timeout=10)
                            if response.status_code == 200:
                                # Open the image (likely WebP) and convert to RGBA
                                image = Image.open(BytesIO(response.content)).convert("RGBA")
                                image.save(png_filename, "PNG")
                        except Exception as err:
                            print(f"Failed to download/convert {icon_url} for {internal_name}: {err}")

                data = tech_t(internal_name) if internal_name not in tech_data else tech_data[internal_name]
                data["Level"] = level
                data["BossTechnology"] = boss_technology
                data["I18n"][lang] = {"Name": tech_name, "Type": tech_type}
                tech_data[internal_name] = data

    return tech_data


tech_data = extract_techs()

tech_json = json.dumps(tech_data, indent=4, ensure_ascii=False)
with open("tmp_tech_data.json", "w", encoding="utf-8") as file:
    file.write(tech_json)
