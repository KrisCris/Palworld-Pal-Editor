import traceback
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from palworld_pal_editor.config import PROGRAM_PATH, Config
from palworld_pal_editor.core import SaveManager
from palworld_pal_editor.utils import LOGGER, DataProvider
from palworld_pal_editor.api.util import reply

save_blueprint = Blueprint("save", __name__)


@save_blueprint.route("/fetch_config", methods=["GET"])
def fetch_config():
    return reply(
        0,
        {
            "I18n": Config.i18n,
            "Path": Config.path,
            "HasPassword": Config.password != None,
            "Mode": Config.mode
        },
    )


@save_blueprint.route("/load", methods=["POST"])
# @LOGGER.api_logger
@jwt_required()
def load():
    path = request.json.get("ReadPath", None)
    path = path or Config.path
    if path and SaveManager().open(path):
        Config.path = path
        Config.save_to_file(PROGRAM_PATH / 'config.json')
        return reply(0)
    
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
        return reply(1, msg=f"Error occored during saving, check debug console. {stack_trace}")


@save_blueprint.route("/passive_skills", methods=["GET"])
@jwt_required()
def get_passive_skills():
    passives_raw = DataProvider.get_sorted_passives()
    passives_raw.reverse()
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
            "I18n": list(DataProvider.get_attack_i18n(attack["InternalName"]) or [attack["InternalName"], ""]),
            "HasSkillFruit": DataProvider.has_skill_fruit(attack["InternalName"]),
            "IsUniqueSkill": DataProvider.is_unique_attacks(attack["InternalName"]),
            "Power": attack["Power"],
            "Element": attack["Element"],
            "CT": attack["CT"],
            "Invalid": attack.get("Invalid", False)
        }
        if data["Invalid"]:
            data["I18n"][0] = "❌ " + data["I18n"][0]
        atk_dict[attack["InternalName"]] = data
        atk_arr.append(data)
    return reply(0, {"dict": atk_dict, "arr": atk_arr})


# def displayElement(element):
#       elementEmojis = {
#         'Water': "💧",
#         'Fire': "🔥",
#         'Dragon': "🐉",
#         'Grass': "☘️",
#         'Ground': "🪨",
#         'Ice': "❄️",
#         'Electric': "⚡",
#         'Neutral': "😐",
#         'Dark': "🌑"
#       }
#       return elementEmojis.get(element) or "❓"

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
        data = {
            "InternalName": pal["InternalName"],
            "Elements": pal["Elements"],
            "Invalid": pal.get("Invalid", False),
            "I18n": DataProvider.get_pal_i18n(pal["InternalName"])
            or pal["InternalName"],
            "SortingKey": DataProvider.get_pal_sorting_key(pal["InternalName"]),
        }
        pal_dict[pal["InternalName"]] = data
        pal_arr.append(data)
    return reply(0, {"dict": pal_dict, "arr": pal_arr})

@save_blueprint.route("/file_picker", methods=["GET"])
@jwt_required()
def show_file_picker():
    if Config.mode != "gui":
        msg = "File picker only supports GUI mode."
        LOGGER.warning(msg)
        return reply(1, msg=msg)
    
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    folder_selected = filedialog.askdirectory(parent=root)
    root.destroy()
    LOGGER.info(f"File picker result: {folder_selected}")
    return reply(0, {"path": folder_selected})