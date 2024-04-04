import json
import re
import requests
from bs4 import BeautifulSoup

# https://paldb.cc/en/Active_Skills#UnrevealedActiveSkills
# let items = document.querySelector("#UnrevealedActiveSkills > div").querySelectorAll("a[data-hover]")
# const list = []
# items.forEach(element => {
#   const dataHoverValue = element.getAttribute('data-hover');
#   const parts = dataHoverValue.split('%3A%3A');
#   if (parts.length > 1) {
#     const skillId = parts[1]; // This is the part after "%3A%3A"
#     list.push("EPalWazaID::"+skillId);
#   }
# });

invalid = [
    "EPalWazaID::TidalWave",
    "EPalWazaID::WaterWave",
    "EPalWazaID::Unique_BluePlatypus_Toboggan",
    "EPalWazaID::Intimidate",
    "EPalWazaID::Human_Punch",
    "EPalWazaID::Throw",
    "EPalWazaID::Scratch",
    "EPalWazaID::WorkAttack",
    "EPalWazaID::SnowStorm",
    "EPalWazaID::EnergyShot",
    "EPalWazaID::CrossThunder",
    "EPalWazaID::ThunderRain",
    "EPalWazaID::Funnel_RaijinDaughter",
    "EPalWazaID::Unique_Kirin_LightningTackle",
    "EPalWazaID::Funnel_DreamDemon",
    "EPalWazaID::Psychokinesis",
    "EPalWazaID::Unique_WeaselDragon_FlyingTackle",
    "EPalWazaID::Tremor",
    "EPalWazaID::DiamondFall",
    "EPalWazaID::BeamSlicer",
    "EPalWazaID::Commet",
    "EPalWazaID::DarkTornado",
    "EPalWazaID::Unique_DarkScorpion_Pierce"
]

# https://paldb.cc/en/ActiveSkills_Table
# let items = document.querySelector("#DataTables_Table_0 > tbody").children
# let list = []
# for (let item of items) {
#     list.push(item.children[1].innerText)
# }
skill_list = [
    "EPalWazaID::TidalWave",
    "EPalWazaID::WaterWave",
    "EPalWazaID::AquaJet",
    "EPalWazaID::WaterGun",
    "EPalWazaID::BubbleShot",
    "EPalWazaID::AcidRain",
    "EPalWazaID::WaterBall",
    "EPalWazaID::Unique_BluePlatypus_Toboggan",
    "EPalWazaID::HydroPump",
    "EPalWazaID::Intimidate",
    "EPalWazaID::Human_Punch",
    "EPalWazaID::AirCanon",
    "EPalWazaID::Unique_ChickenPal_ChickenPeck",
    "EPalWazaID::PowerShot",
    "EPalWazaID::Unique_SheepBall_Roll",
    "EPalWazaID::Unique_PinkCat_CatPunch",
    "EPalWazaID::Unique_Alpaca_Tackle",
    "EPalWazaID::Unique_Garm_Bite",
    "EPalWazaID::Unique_Deer_PushupHorn",
    "EPalWazaID::Unique_Boar_Tackle",
    "EPalWazaID::Unique_Eagle_GlidingNail",
    "EPalWazaID::Unique_NaughtyCat_CatPress",
    "EPalWazaID::Throw",
    "EPalWazaID::Unique_HawkBird_Storm",
    "EPalWazaID::PowerBall",
    "EPalWazaID::Unique_SakuraSaurus_SideTackle",
    "EPalWazaID::Unique_Gorilla_GroundPunch",
    "EPalWazaID::Unique_FengyunDeeper_CloudTempest",
    "EPalWazaID::Scratch",
    "EPalWazaID::WorkAttack",
    "EPalWazaID::Unique_KingAlpaca_BodyPress",
    "EPalWazaID::Unique_SaintCentaur_OneSpearRushes",
    "EPalWazaID::HyperBeam",
    "EPalWazaID::SelfDestruct",
    "EPalWazaID::SelfDestruct_Bee",
    "EPalWazaID::SelfExplosion",
    "EPalWazaID::WindCutter",
    "EPalWazaID::SeedMachinegun",
    "EPalWazaID::Unique_FlowerDinosaur_Whip",
    "EPalWazaID::SpecialCutter",
    "EPalWazaID::SeedMine",
    "EPalWazaID::Unique_RobinHood_BowSnipe",
    "EPalWazaID::Unique_QueenBee_SpinLance",
    "EPalWazaID::GrassTornado",
    "EPalWazaID::Unique_GrassPanda_MusclePunch",
    "EPalWazaID::RootAttack",
    "EPalWazaID::SolarBeam",
    "EPalWazaID::SnowStorm",
    "EPalWazaID::EnergyShot",
    "EPalWazaID::IceMissile",
    "EPalWazaID::IceBlade",
    "EPalWazaID::Unique_IceDeer_IceHorn",
    "EPalWazaID::BlizzardLance",
    "EPalWazaID::Unique_CaptainPenguin_BodySlide",
    "EPalWazaID::FrostBreath",
    "EPalWazaID::Unique_VolcanicMonster_Ice_IceAttack",
    "EPalWazaID::Unique_IceHorse_IceBladeAttack",
    "EPalWazaID::IcicleThrow",
    "EPalWazaID::FireBlast",
    "EPalWazaID::FireSeed",
    "EPalWazaID::Unique_FlameBuffalo_FlameHorn",
    "EPalWazaID::FlareArrow",
    "EPalWazaID::Unique_Ronin_Iai",
    "EPalWazaID::Flamethrower",
    "EPalWazaID::Unique_Baphomet_SwallowKite",
    "EPalWazaID::Unique_AmaterasuWolf_FireCharge",
    "EPalWazaID::FlareTornado",
    "EPalWazaID::Unique_FireKirin_Tackle",
    "EPalWazaID::Unique_VolcanicMonster_MagmaAttack",
    "EPalWazaID::Inferno",
    "EPalWazaID::Unique_Horus_FlareBird",
    "EPalWazaID::FireBall",
    "EPalWazaID::CrossThunder",
    "EPalWazaID::ThunderRain",
    "EPalWazaID::SpreadPulse",
    "EPalWazaID::Funnel_RaijinDaughter",
    "EPalWazaID::ElecWave",
    "EPalWazaID::ThunderBall",
    "EPalWazaID::ThunderFunnel",
    "EPalWazaID::LockonLaser",
    "EPalWazaID::Unique_ElecPanda_ElecScratch",
    "EPalWazaID::LineThunder",
    "EPalWazaID::Unique_GrassPanda_Electric_ElectricPunch",
    "EPalWazaID::ThreeThunder",
    "EPalWazaID::Unique_Kirin_LightningTackle",
    "EPalWazaID::Unique_ThunderDragonMan_ThunderSwordAttack",
    "EPalWazaID::LightningStrike",
    "EPalWazaID::Thunderbolt",
    "EPalWazaID::MudShot",
    "EPalWazaID::StoneShotgun",
    "EPalWazaID::Unique_DrillGame_ShellAttack",
    "EPalWazaID::ThrowRock",
    "EPalWazaID::Unique_HerculesBeetle_BeetleTackle",
    "EPalWazaID::SandTornado",
    "EPalWazaID::Unique_Anubis_LowRoundKick",
    "EPalWazaID::Unique_Grassmammoth_Earthquake",
    "EPalWazaID::Unique_Anubis_Tackle",
    "EPalWazaID::Unique_Anubis_GroundPunch",
    "EPalWazaID::RockLance",
    "EPalWazaID::DragonCanon",
    "EPalWazaID::DragonWave",
    "EPalWazaID::DragonBreath",
    "EPalWazaID::Unique_FairyDragon_FairyTornado",
    "EPalWazaID::Unique_JetDragon_JumpBeam",
    "EPalWazaID::DragonMeteor",
    "EPalWazaID::PoisonFog",
    "EPalWazaID::Funnel_DreamDemon",
    "EPalWazaID::PoisonShot",
    "EPalWazaID::DarkBall",
    "EPalWazaID::DarkWave",
    "EPalWazaID::Unique_DarkCrow_TelePoke",
    "EPalWazaID::Unique_Werewolf_Scratch",
    "EPalWazaID::GhostFlame",
    "EPalWazaID::Unique_FireKirin_Dark_DarkTossin",
    "EPalWazaID::ShadowBall",
    "EPalWazaID::Psychokinesis",
    "EPalWazaID::Unique_BlackCentaur_TwoSpearRushes",
    "EPalWazaID::DarkLaser",
    "EPalWazaID::Unique_BlackGriffon_TackleLaser",
    "EPalWazaID::DarkLegion",
    "EPalWazaID::Unique_WeaselDragon_FlyingTackle",
    "EPalWazaID::Tremor",
    "EPalWazaID::DiamondFall",
    "EPalWazaID::BeamSlicer",
    "EPalWazaID::Unique_NightLady_WarpBeam",
    "EPalWazaID::Unique_NightLady_FlameNightmare",
    "EPalWazaID::Commet",
    "EPalWazaID::DarkPulse",
    "EPalWazaID::DarkCanon",
    "EPalWazaID::DarkArrow",
    "EPalWazaID::DarkTornado",
    "EPalWazaID::Apocalypse",
    "EPalWazaID::Unique_NightLady_WarpBeam_Straight",
    "EPalWazaID::Unique_DarkScorpion_Pierce"
]

def get_attack_data(id: str):
    langs = ["en", "cn", "ja"]
    data = {
        "InternalName": id,
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
            }
        }
    }
    parsed = False
    if id in invalid:
        data["Invalid"] = True
    
    for lang in langs:
        try: 
            url = f"https://paldb.cc/{lang}/hover?s=Waza/{id}"
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            if lang == "cn":
                lang = "zh-CN"

            data["I18n"][lang]["Name"] = soup.find('a', attrs={'data-hover': f'?s=Waza/{id.replace(":", "%3A")}'}).text
            data['I18n'][lang]["Description"] = re.sub(r'\s+', ' ', soup.find('div', attrs={'class': "card-body"}).text).strip().replace("。 ", "。").replace("， ", "，").replace("、 ", "、")

            if not parsed:
                unique = soup.find('img', {'data-bs-title': "Will not inherit"})
                if unique:
                    data["UniqueSkill"] = True

                try:
                    el = soup.find('span', {'style': "padding-left: 35px"}).text
                    data["Element"] = el

                    ct_pw = soup.find_all('span', {'style': "color: #73ffff"})

                    ct = int(ct_pw[0].text)
                    data["CT"] = ct

                    power = int(ct_pw[1].text)
                    data["Power"] = power

                    fruit = soup.find('img', {'src': f"https://cdn.paldb.cc/image/Others/InventoryItemIcon/Texture/T_itemicon_Consume_SkillCard_{el}.webp"})

                    if fruit:
                        data["SkillFruit"] = True

                    parsed = True
                except:
                    print(f"{soup.find_all('span')}")
        except:
            print(url)
    return data


with open('./pal_data.json', 'r', encoding='utf8') as pal_file:
    pal_data = json.load(pal_file)

def rename(key: str):
    match(key):
        case 'Grassmammoth': return "GrassMammoth"
        case 'Sheepball': return "SheepBall"
        case _: return key

element_key = {
    "Water": "1",
    "Neutral": "2",
    "Grass": "3",
    "Ice": "4",
    "Fire": "5",
    "Electric": "6",
    "Ground": "7",
    "Dragon": "8",
    "Dark": "9",
}

def main():
    skill_map_raw = {}

    for skill in skill_list:
        print(f"#### Parsing {skill}")
        data = get_attack_data(skill)
        skill_map_raw[skill] = data
        print(data)

    skill_map = {}

    values: list = skill_map_raw.values()
    values = sorted(values, key=lambda x: (
        x.get("Invalid", False),
        element_key.get(x.get("Element", ""), x.get("Element", "")),
        x.get("UniqueSkill", False),
        x.get("Power", -1),
        x.get("CT", -1)
    ))

    for value in values:
        key = value["InternalName"]
        if "Unique" in key:
            pal_key = key.split("_")[1]
            for lang in ["en", "zh-CN", "ja"]:
                pal_key = rename(pal_key)
                pal_name = pal_data[pal_key].get("I18n", {}).get(lang, pal_key)
                value["I18n"][lang]["Name"] += f" [{pal_name}]"
        skill_map[key] = value

    with open('./new_attacks.json', 'w', encoding='utf8') as json_file:
        json.dump(skill_map, json_file, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    main()


# with open('./pal_attacks.json', 'r', encoding='utf8') as json_file:
#     pal_attacks = json.load(json_file)



# for key in pal_attacks:
#     if "Unique" in key:
#         pal_key = key.split("_")[1]
#         for lang in ["en", "zh-CN", "ja"]:
#             pal_key = rename(pal_key)
#             pal_name = pal_data[pal_key].get("I18n", {}).get(lang, pal_key)
#             pal_attacks[key]["I18n"][lang]["Name"] += f" [{pal_name}]"
        

# # for item in pal_attacks:
# #     if item in invalid:
# #         pal_attacks[item]["Invalid"] = True

# new_map = {}

# values: list = pal_attacks.values()
# values = sorted(values, key=lambda x: (
#     x.get("Invalid", False),
#     element_key.get(x.get("Element", ""), x.get("Element", "")),
#     x.get("UniqueSkill", False),
#     x.get("Power", -1),
#     x.get("CT", -1)
# ))

# for value in values:
#     new_map[value["InternalName"]] = value

# with open('./pal_attacks.json', 'w', encoding='utf8') as json_file:
#     json.dump(new_map, json_file, indent=4, ensure_ascii=False)