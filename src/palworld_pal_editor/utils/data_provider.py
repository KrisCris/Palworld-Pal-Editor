from functools import wraps
import json
from typing import Any, Callable, Optional

# from PIL import Image

from palworld_pal_editor.config import ASSETS_PATH, Config
from palworld_pal_editor.utils import LOGGER
from palworld_pal_editor.utils.util import alphanumeric_key


def load_json(filename: str) -> Any:
    path = ASSETS_PATH / "assets/data" / filename
    with path.open("r", encoding="utf8") as file:
        return json.load(file)


# def load_icons(sub_path: str) -> dict[str]:
#     icons = {}
#     valid_extensions = {".jpg", ".jpeg", ".png"}
#     path = BASE_PATH / "assets/icons" / sub_path
#     for img_path in path.iterdir():
#         if img_path.suffix.lower() in valid_extensions:
#             try:
#                 img = Image.open(img_path)
#                 icons[img_path.stem] = img
#             except IOError as e:
#                 LOGGER.error(f"Error opening {img_path}: {e}")
#     return icons


PAL_ATTACKS: dict[str, dict] = load_json("pal_attacks.json")
PAL_DATA: dict[str, dict] = load_json("pal_data.json")
PAL_PASSIVES: dict[str, dict] = load_json("pal_passives.json")
PAL_XP_THRESHOLDS: list[int] = load_json("pal_xp_thresholds.json")

# PAL_ICONS: dict[str] = load_icons("pals")

I18N_LIST = ["en", "zh-CN", "ja"]


def none_guard(
    data_source: dict | list, key_arg_position: int = 0, subkey: Optional[str] = None
):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Optional[Any]:
            # Extract key from positional or keyword arguments
            key = (
                args[key_arg_position]
                if len(args) > key_arg_position
                else kwargs.get("key")
            )

            # if key not in data_source, or if subkey not in data source, or sub_data[subkey] is empty
            if key not in data_source or (
                subkey
                and (subkey not in data_source[key] or not data_source[key][subkey])
            ):
                # LOGGER.warning(
                #     f"Key: {key} or subkey: {subkey} were not found in the data source."
                # )
                return None

            return func(*args, **kwargs)

        return wrapper

    return decorator


class DataProvider:
    icon_cache = {}

    @property
    def default_i18n() -> str:
        return I18N_LIST[0]

    # @staticmethod
    # def get_pal_icon(key: str) -> Optional[Any]:
    #     if key not in PAL_ICONS:
    #         LOGGER.warning(f"Pal icon {key} doesn't exist.")
    #         return
    #     return PAL_ICONS[key]

    @none_guard(data_source=PAL_DATA, subkey="I18n")
    @staticmethod
    def get_pal_i18n(key: str) -> Optional[str]:
        i18n_list: dict = PAL_DATA[key]["I18n"]
        return i18n_list.get(Config.i18n, i18n_list.get("en"))

    @none_guard(data_source=PAL_DATA, subkey="Scaling")
    @staticmethod
    def get_pal_scaling(pal: str, scaling_type: str, is_boss: bool) -> Optional[int]:
        if scaling_type not in {"HP", "ATK", "DEF"}:
            return None

        scaling_list: dict = PAL_DATA[pal]["Scaling"]
        if is_boss and f"{scaling_type}_BOSS" in scaling_list:
            return scaling_list[f"{scaling_type}_BOSS"]
        return scaling_list.get(scaling_type, None)

    @none_guard(data_source=PAL_DATA, subkey="SortingKey")
    @staticmethod
    def get_pal_sorting_key(key: str, sorting_key="paldeck") -> Optional[str]:
        sorting_key_list: dict = PAL_DATA[key]["SortingKey"]
        return sorting_key_list.get(sorting_key)

    @staticmethod
    def get_sorted_pals() -> list[dict]:
        sorted_list = sorted(
            PAL_DATA.values(),
            key=lambda item: (
                DataProvider.is_pal_human(item["InternalName"]),
                alphanumeric_key(
                    DataProvider.get_pal_sorting_key(item["InternalName"])
                    or DataProvider.get_pal_i18n(item["InternalName"])
                ),
            ),
        )
        return sorted_list

    @staticmethod
    def has_tower_variant_pal(key: str) -> bool:
        return f"GYM_{key}" in PAL_DATA

    @none_guard(data_source=PAL_DATA)
    @staticmethod
    def is_pal_human(key: str) -> Optional[bool]:
        return PAL_DATA[key].get("Human", False)
    
    @staticmethod
    def is_pal_invalid(key: str) -> bool:
        if key not in PAL_DATA: return True
        return PAL_DATA[key].get("Invalid", False)

    @none_guard(data_source=PAL_DATA, subkey="Attacks")
    def get_pal_attacks(pal: str) -> Optional[list[str]]:
        return PAL_DATA[pal]["Attacks"]

    @staticmethod
    def get_level_xp(lv: int) -> Optional[int]:
        try:
            return PAL_XP_THRESHOLDS[lv - 1]
        except IndexError:
            LOGGER.warning(f"Level {lv} is out of bounds.")
            return None

    @none_guard(data_source=PAL_ATTACKS, subkey="I18n")
    @staticmethod
    def get_attack_i18n(key: str) -> Optional[tuple[str, str]]:
        i18n_list: dict = PAL_ATTACKS[key]["I18n"]
        i18n: dict = i18n_list.get(Config.i18n, i18n_list.get("en"))
        return  (i18n.get("Name", key), i18n.get("Description", ""))

    @staticmethod
    def has_attack(key: str) -> bool:
        return key in PAL_ATTACKS

    @staticmethod
    def has_skill_fruit(attack: str) -> bool:
        if attack not in PAL_ATTACKS:
            return False
        if PAL_ATTACKS[attack].get("SkillFruit"):
            return True
        return False

    @staticmethod
    def is_invalid_attack(key: str) -> bool:
        if key not in PAL_ATTACKS:
            return True
        return PAL_ATTACKS[key].get("Invalid", False)

    @staticmethod
    def is_unique_attacks(key: str) -> bool:
        if key not in PAL_ATTACKS:
            return False
        return PAL_ATTACKS[key].get("UniqueSkill", False)

    @staticmethod
    def get_sorted_attacks() -> list[dict]:
        sorted_list = sorted(
            PAL_ATTACKS.values(),
            key=lambda item: (
                DataProvider.is_invalid_attack(item["InternalName"]),
                item["Element"],
                DataProvider.is_unique_attacks(item["InternalName"]),
                # DataProvider.has_skill_fruit(item["InternalName"]),
                item["Power"],
                item["CT"]
            ),
        )
        return sorted_list

    @none_guard(data_source=PAL_PASSIVES, subkey="I18n")
    @staticmethod
    def get_passive_i18n(key: str) -> Optional[tuple[str, str]]:
        i18n_list: dict = PAL_PASSIVES[key]["I18n"]
        i18n: dict = i18n_list.get(Config.i18n, i18n_list.get("en"))
        return (i18n.get("Name", key), i18n.get("Description", ""))

    @staticmethod
    def has_passive_skill(key: str) -> bool:
        return key in PAL_PASSIVES

    @staticmethod
    def get_sorted_passives() -> list[dict]:
        sorted_list = sorted(
            PAL_PASSIVES.values(),
            key=lambda item: (item["Rating"], item["InternalName"]),
        )
        return sorted_list

    @staticmethod
    def get_passive_buff(key: str, buff_key: str) -> float:
        return PAL_PASSIVES.get(key, {}).get("Buff", {}).get(buff_key, 0)

    @staticmethod
    def get_attacks_to_learn(pal: str, level: int) -> list[str]:
        attacks = DataProvider.get_pal_attacks(pal)
        if attacks is None:
            return []
        return [attack for attack in attacks if attacks[attack] <= (level or 1)]

    @staticmethod
    def get_attacks_to_forget(pal: str, level: int) -> list[str]:
        attacks = DataProvider.get_pal_attacks(pal)
        if attacks is None:
            return []
        return [
            attack
            for attack in attacks
            if attacks[attack] > level and not DataProvider.has_skill_fruit(attack)
        ]

    @staticmethod
    def is_valid_i18n(key: str):
        return key in I18N_LIST

    @staticmethod
    def get_i18n_options() -> list[str]:
        return I18N_LIST
