import traceback

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from palworld_pal_editor.config import Config
from palworld_pal_editor.core import SaveManager
from palworld_pal_editor.utils import LOGGER, DataProvider
from palworld_pal_editor.utils.util import reply

save_blueprint = Blueprint("save", __name__)


@save_blueprint.route("/save", methods=["POST"])
@jwt_required()
def save():
    path = request.json.get("WritePath", None)
    try:
        if SaveManager().save(path):
            return reply(0)
        return reply(1, msg=f"Path not available? {path}")
    except Exception as e:
        stack_trace = traceback.format_exc()
        LOGGER.error(f"Error in patch_paldata {stack_trace}")
        return reply(
            1, msg=f"Error occored during saving, check debug console. {stack_trace}"
        )


@save_blueprint.route("/passive_skills", methods=["GET"])
@jwt_required()
def get_passive_skills():
    passives_raw = DataProvider.get_sorted_passives()
    passive_dict = {}
    passive_arr = []
    for passive in passives_raw:
        data = {
            "InternalName": passive["InternalName"],
            "I18n": list(
                DataProvider.get_passive_i18n(passive["InternalName"])
                or (passive["InternalName"], passive["InternalName"])
            ),
            "Rating": passive["Rating"],
            "Invalid": DataProvider.is_invalid_passive(passive["InternalName"]),
            "Group": DataProvider.get_passive_group(passive["InternalName"]),
        }
        if data["Invalid"]:
            data["I18n"][0] = "⚠️ " + data["I18n"][0]
        passive_dict[passive["InternalName"]] = data
        passive_arr.append(data)

    return reply(0, {"dict": passive_dict, "arr": passive_arr})


@save_blueprint.route("/active_skills", methods=["GET"])
@jwt_required()
def get_active_skills():
    attacks_raw = DataProvider.get_sorted_attacks()
    atk_dict = {}
    atk_arr = []
    for attack in attacks_raw:
        # if attack.get("Invalid", None):
        #     continue
        data = {
            "InternalName": attack["InternalName"],
            # "I18n": f'[{displayElement(attack["Element"])}] ' \
            #         f'{"🍐" if DataProvider.has_skill_fruit(attack["InternalName"]) else ""}' \
            #         f'{"✨"if DataProvider.is_unique_attacks(attack["InternalName"]) else ""}' \
            #         f'{DataProvider.get_attack_i18n(attack["InternalName"]) or attack["InternalName"]}',
            "I18n": list(
                DataProvider.get_attack_i18n(attack["InternalName"])
                or [attack["InternalName"], ""]
            ),
            "HasSkillFruit": DataProvider.has_skill_fruit(attack["InternalName"]),
            "IsUniqueSkill": DataProvider.is_unique_attacks(attack["InternalName"]),
            "NonInheritable": DataProvider.is_non_inheritable_attack(
                attack["InternalName"]
            ),
            "Exclusive": DataProvider.is_exclusive_attack(attack["InternalName"]),
            "BossSkill": DataProvider.is_boss_attack(attack["InternalName"]),
            "Assignable": DataProvider.is_assignable_attack(attack["InternalName"]),
            "AssignableToHumans": DataProvider.is_assignable_human_attack(
                attack["InternalName"]
            ),
            "Power": attack["Power"],
            "Element": attack["Element"],
            "CT": attack["CT"],
            "Invalid": attack.get("Invalid", False),
            "LearnerNames": DataProvider.get_attack_learner_names(
                attack["InternalName"]
            ),
        }
        if data["Invalid"]:
            data["I18n"][0] = "⚠️ " + data["I18n"][0]
        atk_dict[attack["InternalName"]] = data
        atk_arr.append(data)
    return reply(0, {"dict": atk_dict, "arr": atk_arr})


@save_blueprint.route("/item_data", methods=["GET"])
@jwt_required()
def get_item_data():
    item_dict = {}
    item_arr = []
    for internal_name, item in DataProvider.get_item_data().items():
        translations = item.get("I18n", {})
        localized = translations.get(Config.i18n) or translations.get("en") or {}
        row = {
            key: value
            for key, value in item.items()
            if key != "I18n"
        }
        row.update(
            {
                "InternalName": internal_name,
                "Name": localized.get("Name") or internal_name,
                "Description": localized.get("Description") or "",
            }
        )
        item_dict[internal_name] = row
        item_arr.append(row)
    item_arr.sort(key=lambda row: (row["SortId"], row["InternalName"]))
    return reply(0, {"dict": item_dict, "arr": item_arr})


@save_blueprint.route("/pal_data", methods=["GET"])
@jwt_required()
def get_pal_data():
    pals_raw = DataProvider.get_sorted_pals()
    pal_dict = {}
    pal_arr = []
    for pal in pals_raw:
        iname = pal["InternalName"]
        tags = pal["VariantTags"]
        data = {
            "InternalName": iname,
            "Elements": pal["Elements"],
            "Invalid": pal.get("Invalid", False),
            "Suitabilities": DataProvider.get_pal_suitabilities(iname),
            "I18n": DataProvider.get_pal_i18n(iname) or iname,
            "SortingKey": DataProvider.get_pal_sorting_key(iname),
            "IsHuman": DataProvider.is_pal_human(iname) or False,
            "FamilyID": pal["FamilyID"],
            "VariantKind": pal["VariantKind"],
            "VariantTags": tags,
            "IconKey": pal["IconKey"],
            "IconAccessKey": pal["IconKey"],
            "PaldeckRecordID": DataProvider.get_pal_paldeck_record_id(iname),
            "PaldeckIndex": pal.get("PaldeckIndex"),
            "PaldeckSuffix": pal.get("PaldeckSuffix", ""),
            "RegularlyObtainable": pal["RegularlyObtainable"],
            "AvailabilitySources": pal["AvailabilitySources"],
            "ObtainMethods": pal["ObtainMethods"],
            "IsBOSS": "boss" in tags,
            "IsTower": "tower" in tags,
            "IsRAID": "raid" in tags,
            "IsPREDATOR": "predator" in tags,
            "IsSUMMON": "summon" in tags,
            "IsOilrig": "oilrig" in tags,
            "IsOtomoTower": "tower" in tags and "otomo" in tags,
        }
        pal_dict[iname] = data
        pal_arr.append(data)
    return reply(0, {"dict": pal_dict, "arr": pal_arr})


@save_blueprint.route("/skin_data", methods=["GET"])
@jwt_required()
def get_skin_data():
    skins = [
        {
            "SkinName": skin["SkinName"],
            "TargetPalName": skin["TargetPalName"],
            "Invalid": skin.get("Invalid", False),
        }
        for skin in DataProvider.get_skin_data().values()
        if skin.get("SkinType") == "EPalSkinType::Pal"
    ]
    return reply(0, {"arr": skins})


@save_blueprint.route("/tech_data", methods=["GET"])
@jwt_required()
def get_tech_data():
    tech_data = DataProvider.get_tech_data()
    tech_lv_dict: dict[str, list] = {}
    for tech in tech_data:
        lv = DataProvider.get_tech_lv(tech)
        lv_arr = tech_lv_dict.get(lv, [])
        icon_key = tech.removeprefix("SkillUnlock_")
        if tech.startswith("SkillUnlock_"):
            icon_key = DataProvider.resolve_pal_key(icon_key)
        data = {
            "InternalName": tech,
            "IconAccessKey": icon_key,
            "I18n": DataProvider.get_tech_i18n(tech),
            "BossTechnology": DataProvider.is_boss_tech(tech),
        }
        lv_arr.append(data)
        tech_lv_dict[lv] = lv_arr

    return reply(0, {"techLvDict": tech_lv_dict})
