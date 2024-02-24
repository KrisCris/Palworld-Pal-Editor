from functools import wraps
import json
from pathlib import Path
import sys
from typing import Any, Callable, Optional

from .config import Config

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
    with path.open("r") as file:
        return json.load(file)

PAL_ATTACKS:dict[str, dict] = load_json("pal_attacks.json")
PAL_DATA:dict[str, dict] = load_json("pal_data.json")
PAL_PASSIVES:dict[str, dict] = load_json("pal_passives.json")
PAL_XP_THRESHOLDS:list[int] = load_json("pal_xp_thresholds.json")

I18N_LIST = ['en', 'zh-CN']


def none_guard(data_source: dict | list, key_arg_position: int, subkey: Optional[str] = None):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Optional[Any]:
            # Extract key from positional or keyword arguments
            key = args[key_arg_position] if len(args) > key_arg_position else kwargs.get('key', None)
            
            # if key not in data_source, or if subkey not in data source, or sub_data[subkey] is empty
            if key not in data_source or (subkey and (subkey not in data_source[key] or not data_source[key][subkey])):
                return None
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

class DataAccessor:
    @none_guard(data_source=PAL_DATA, key_arg_position=0, subkey="i18n")
    @staticmethod
    def get_pal_specie_name(key: str) -> Optional[str]:    
        # if key not in PAL_DATA:
        #     return None
        
        # pal_data:dict = PAL_DATA[key]

        # # Check if 'i18n' key exists and has at least one entry
        # if 'i18n' not in pal_data or not pal_data['i18n']:
        #     return None
        # access i18n list and return the preferred language or default to English
        i18n_list: dict = PAL_DATA[key]['i18n']
        return i18n_list.get(Config.i18n, i18n_list.get('en', None))
    
    @none_guard(data_source=PAL_DATA, key_arg_position=0, subkey="Scaling")
    @staticmethod
    def get_pal_hp_scaling(key: str, is_boss: bool) -> Optional[int]:
        # if key not in PAL_DATA:
        #     return None
        
        # pal_data:dict = PAL_DATA[key]

        # if "Scaling" not in pal_data or not pal_data["Scaling"]:
        #     return None
        
        scaling_list: dict = PAL_DATA[key]["Scaling"]
        if is_boss and "HP_BOSS" in scaling_list:
            return scaling_list["HP_BOSS"]
        return scaling_list["HP"]

    @none_guard(data_source=PAL_DATA, key_arg_position=0, subkey="sorting_key")
    @staticmethod
    def get_pal_sorting_key(key: str, sorting_key="paldeck") -> Optional[str]:
        sorting_key_list: dict = PAL_DATA[key]["sorting_key"]
        sorting_key_list.get(sorting_key, None)

    