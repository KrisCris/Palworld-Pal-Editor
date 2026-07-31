from io import BytesIO
from bs4 import BeautifulSoup
import requests
import json
import re
from pathlib import Path
from PIL import Image

from palworld_pal_editor.assets.tools.paldb import hover_id, logical_pal_icon_id

urls = {
    "en": "https://paldb.cc/en/Technologies",
    "zh-CN": "https://paldb.cc/cn/Technologies",
    "ja": "https://paldb.cc/ja/Technologies",
    "fr": "https://paldb.cc/fr/Technologies",
}

TOOLS_DIR = Path(__file__).resolve().parent
ASSETS_DIR = TOOLS_DIR.parent
PAL_ICON_DIR = ASSETS_DIR / "icons" / "pals"
TECH_ICON_DIR = ASSETS_DIR / "icons" / "tech"

internal_names_replacement = {
    "PALBOX": "PalBox",
    "ShotGunBullet": "ShotgunBullet",
    "OverheatRifle": "OverHeatRifle",
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
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        rows = soup.select("div.col.pt-2.pb-1.border-bottom")
        for row in rows:
            # 1) Extract the "Level" from the first d-inline-block with a position: relative style
            #    e.g. <div class="d-inline-block" style="position: relative;height: 128px;width:64px;"> 
            level_div = row.select_one('div.d-flex > div[style*="width:32px"]')
            
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
                internal_name = hover_id(data_hover, "Technology")
                
                # If for some reason we don't find "Technology/", skip
                if not internal_name:
                    continue
                internal_name = internal_names_replacement.get(
                    internal_name, internal_name
                )
                
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
                
                icon_access_key = None
                if icon_url:
                    if internal_name.startswith("SkillUnlock_"):
                        icon_access_key = logical_pal_icon_id(
                            internal_name.removeprefix("SkillUnlock_")
                        )
                        pal_icon_path = PAL_ICON_DIR / f"{icon_access_key}.png"
                        if not pal_icon_path.exists():
                            print(f"Missing Pal Skill Unlock {pal_icon_path.name}")
                    else:
                        icon_path = TECH_ICON_DIR / f"{internal_name}.png"
                    if not internal_name.startswith("SkillUnlock_") and not icon_path.exists():
                        try:
                            response = requests.get(icon_url, timeout=10)
                            response.raise_for_status()
                            image = Image.open(BytesIO(response.content)).convert("RGBA")
                            image.save(icon_path, "PNG")
                        except Exception as err:
                            print(f"Failed to download/convert {icon_url} for {internal_name}: {err}")

                data = tech_t(internal_name) if internal_name not in tech_data else tech_data[internal_name]
                data["Level"] = level
                data["BossTechnology"] = boss_technology
                data["I18n"][lang] = {"Name": tech_name, "Type": tech_type}
                tech_data[internal_name] = data

    return tech_data


def main():
    tech_data = extract_techs()
    output_path = TOOLS_DIR / "tmp_tech_data.json"
    output_path.write_text(
        json.dumps(tech_data, indent=4, ensure_ascii=False), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
