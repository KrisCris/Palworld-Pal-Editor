from functools import wraps
import json
from pathlib import Path
import sys
from typing import Any, Callable, Optional

from palworld_pal_editor.config import Config
from palworld_pal_editor.utils import LOGGER

# def load_json(filename: str):
#     path = Path(f"./src/palworld_pal_editor/assets/data/{filename}").resolve()
#     with path.open("r") as file:
#         return json.load(file)

def load_json(filename: str) -> Any:
    if getattr(sys, 'frozen', False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).parent

    path = base_path / "assets/data" / filename
    with path.open("r", encoding='utf8') as file:
        return json.load(file)

PAL_ATTACKS:dict[str, dict] = load_json("pal_attacks.json")
PAL_DATA:dict[str, dict] = load_json("pal_data.json")
PAL_PASSIVES:dict[str, dict] = load_json("pal_passives.json")
PAL_XP_THRESHOLDS:list[int] = load_json("pal_xp_thresholds.json")

I18N_LIST = ['en', 'zh-CN']


def none_guard(data_source: dict | list, key_arg_position: int = 0, subkey: Optional[str] = None):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Optional[Any]:
            # Extract key from positional or keyword arguments
            key = args[key_arg_position] if len(args) > key_arg_position else kwargs.get('key', None)
            
            # if key not in data_source, or if subkey not in data source, or sub_data[subkey] is empty
            if key not in data_source or (subkey and (subkey not in data_source[key] or not data_source[key][subkey])):
                LOGGER.warning(f"Key: {key} or subkey: {subkey} were not found in the data source.")
                return None
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

class DataProvider:
    @none_guard(data_source=PAL_DATA, subkey="i18n")
    @staticmethod
    def pal_i18n(key: str) -> Optional[str]:    
        i18n_list: dict = PAL_DATA[key]['i18n']
        return i18n_list.get(Config.i18n, i18n_list.get('en', None))
    
    @none_guard(data_source=PAL_DATA, subkey="Scaling")
    @staticmethod
    def pal_hp_scaling(key: str, is_boss: bool) -> Optional[int]:
        scaling_list: dict = PAL_DATA[key]["Scaling"]
        if is_boss and "HP_BOSS" in scaling_list:
            return scaling_list["HP_BOSS"]
        return scaling_list["HP"]

    @none_guard(data_source=PAL_DATA, subkey="sorting_key")
    @staticmethod
    def pal_sorting_key(key: str, sorting_key="paldeck") -> Optional[str]:
        sorting_key_list: dict = PAL_DATA[key]["sorting_key"]
        return sorting_key_list.get(sorting_key, None)

    @none_guard(data_source=PAL_DATA)
    @staticmethod
    def is_pal_human(key: str) -> Optional[bool]:
        return PAL_DATA[key].get("Human", False)
    
    def pal_level_to_xp(lv: int) -> Optional[int]:
        try:
            return PAL_XP_THRESHOLDS[lv - 1]
        except IndexError:
            LOGGER.warning(f"Level {lv} is out of bounds.")
            return None
        
    @none_guard(data_source=PAL_ATTACKS)
    @staticmethod
    def attack_i18n(key: str) -> Optional[str]:
        i18n_list: dict = PAL_ATTACKS[key]["i18n"]
        return i18n_list.get(Config.i18n, i18n_list.get('en', None))
    
    @staticmethod
    def has_attack(key: str) -> bool:
        return key in PAL_ATTACKS
    
    @staticmethod
    def get_sorted_attacks() -> list[dict]:
        sorted_list = sorted(PAL_ATTACKS.values(), key=lambda item: (item['Type'], item['Power']))
        return sorted_list
    
    @none_guard(data_source=PAL_ATTACKS)
    @staticmethod
    def attack_has_skill_fruit(key: str) -> bool:
        return True if PAL_ATTACKS[key].get("skill_fruit", None) else False