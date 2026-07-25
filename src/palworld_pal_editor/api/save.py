import os
from pathlib import Path
import traceback
from flask import Blueprint, request
from flask_jwt_extended import jwt_required
import asyncio

from palworld_pal_editor.config import (
    PROGRAM_PATH,
    NEXUS_URL,
    Config,
    version_info,
    is_gh_build,
    get_new_version,
)
from palworld_pal_editor.core import SaveManager
from palworld_pal_editor.utils import LOGGER, DataProvider
from palworld_pal_editor.utils.util import get_path_context, reply

save_blueprint = Blueprint("save", __name__)


@save_blueprint.route("/fetch_config", methods=["GET"])
def fetch_config():
    return reply(
        0,
        {
            "I18n": Config.i18n,
            "I18nList": DataProvider.get_i18n_map(),
            "Path": Config.path,
            "HasPassword": Config.password != None,
            "VERSION": version_info(),
            "IsOfficialBuild": is_gh_build(),
        },
    )


@save_blueprint.route("/load", methods=["POST"])
# @LOGGER.api_logger
@jwt_required()
def load():
    path = request.json.get("ReadPath", None)
    path = path or Config.path
    try:
        if path and SaveManager().open(path):
            Config.path = path
            Config.save_to_file(PROGRAM_PATH / "config.json")
            return reply(0)
    except Exception as e:
        stack_trace = traceback.format_exc()
        LOGGER.error(f"Error Loading Save {stack_trace}")
        return reply(
            1,
            msg=f"Error occored during loading, please make sure both the editor and your game save is up to date! Check debug console for further details.",
        )

    LOGGER.warning(f"Failed to load, check path: {path}")
    return reply(1, None, f"Failed to load, check path: {path}")


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
            "I18n": DataProvider.get_passive_i18n(passive["InternalName"])
            or (passive["InternalName"], passive["InternalName"]),
            "Rating": passive["Rating"],
        }
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
            "Power": attack["Power"],
            "Element": attack["Element"],
            "CT": attack["CT"],
            "Invalid": attack.get("Invalid", False),
        }
        if data["Invalid"]:
            data["I18n"][0] = "⚠️ " + data["I18n"][0]
        atk_dict[attack["InternalName"]] = data
        atk_arr.append(data)
    return reply(0, {"dict": atk_dict, "arr": atk_arr})


@save_blueprint.route("/i18n", methods=["PATCH"])
# @jwt_required()
def update_i18n():
    i18n_code = request.json.get("I18n", None)
    if DataProvider.is_valid_i18n(i18n_code):
        Config.i18n = i18n_code
        return reply(0)
    LOGGER.warning(
        f"I18n code {i18n_code} not available. Select from {DataProvider.get_i18n_options()}"
    )
    return reply(1, None, f"I18n code {i18n_code} not available.")


@save_blueprint.route("/pal_data", methods=["GET"])
@jwt_required()
def get_pal_data():
    pals_raw = DataProvider.get_sorted_pals()
    pal_dict = {}
    pal_arr = []
    for pal in pals_raw:
        iname = pal["InternalName"]
        if (
            "BOSS_" in iname
            and DataProvider.boss_has_base_variant(iname)
            or "Boss_" in iname
            and DataProvider.boss_has_base_variant(iname)
        ):
            continue
        data = {
            "InternalName": iname,
            "Elements": pal["Elements"],
            "Invalid": pal.get("Invalid", False),
            "Suitabilities": DataProvider.get_pal_suitabilities(iname),
            "I18n": DataProvider.get_pal_i18n(iname) or iname,
            "SortingKey": DataProvider.get_pal_sorting_key(iname),
            "IsHuman": DataProvider.is_pal_human(iname) or False,
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


@save_blueprint.route("/path", methods=["GET"])
@jwt_required()
def get_path():
    try:
        current_path = Path(Config.path).resolve()
        if not current_path.exists():
            raise Exception(f"Path {current_path} not exist.")
    except:
        pal_local_path = (
            Path(os.environ.get("LOCALAPPDATA", "/")) / "Pal" / "Saved" / "SaveGames"
        )
        if pal_local_path.exists():
            current_path = pal_local_path
        else:
            current_path = PROGRAM_PATH

    old_path = Config.path
    Config.path = str(current_path)

    try:
        return reply(0, get_path_context(current_path))
    except:
        Config.path = old_path
        LOGGER.error(traceback.format_exc())
        return reply(1, msg=f"Error, cannot open path {current_path}.")


@save_blueprint.route("path", methods=["POST"])
@jwt_required()
def update_path():
    path = Path(request.json.get("path")).resolve()
    if not path.exists():
        return reply(1, msg="Path Not Found")

    old_path = Config.path
    Config.path = str(path)

    try:
        return reply(0, get_path_context(path))
    except:
        Config.path = old_path
        LOGGER.error(traceback.format_exc())
        return reply(1, msg=f"Error, cannot open path {path}.")


@save_blueprint.route("path", methods=["PATCH"])
@jwt_required()
def path_back():
    path = Path(Config.path).parent.resolve()
    old_path = Config.path
    Config.path = str(path)

    try:
        return reply(0, get_path_context(path))
    except:
        Config.path = old_path
        LOGGER.error(traceback.format_exc())
        return reply(1, msg=f"Error, cannot open path {path}.")


@save_blueprint.route("donate", methods=["PATCH"])
@jwt_required()
def pop_up_donate():
    Config.set_shown_donate_info()
    return reply(0)


@save_blueprint.route("donate", methods=["GET"])
@jwt_required()
def get_donate():
    return reply(0, {"shouldShowDonate": not Config.shownDonateInfo.get(Config.i18n)})


@save_blueprint.route("update", methods=["GET"])
@jwt_required()
def has_update():
    try:
        version = asyncio.run(get_new_version())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        version = loop.run_until_complete(get_new_version())
    if version is not None:
        return reply(
            0,
            {
                "version": version[0],
                "download_gh": version[1],
                "download_nexus": NEXUS_URL,
            },
            msg="New version available.",
        )
    return reply(1, msg="Failed to get new version.")
