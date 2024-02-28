from functools import wraps
import json
from pathlib import Path
import sys
from typing import Any, Callable, Optional

from palworld_pal_editor.config import Config
from palworld_pal_editor.utils import LOGGER

def load_json(filename: str) -> Any:
    if getattr(sys, 'frozen', False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).parent.parent

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
            key = args[key_arg_position] if len(args) > key_arg_position else kwargs.get('key')
            
            # if key not in data_source, or if subkey not in data source, or sub_data[subkey] is empty
            if key not in data_source or (subkey and (subkey not in data_source[key] or not data_source[key][subkey])):
                LOGGER.warning(f"Key: {key} or subkey: {subkey} were not found in the data source.")
                return None
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

class DataProvider:
    @property
    def default_i18n() -> str:
        return I18N_LIST[0]
    
    @none_guard(data_source=PAL_DATA, subkey="I18n")
    @staticmethod
    def get_pal_i18n(key: str) -> Optional[str]:    
        i18n_list: dict = PAL_DATA[key]['I18n']
        return i18n_list.get(Config.i18n, i18n_list.get('en'))
    
    @none_guard(data_source=PAL_DATA, subkey="Scaling")
    @staticmethod
    def get_pal_scaling(pal: str, scaling_type: str, is_boss: bool) -> Optional[int]:
        if scaling_type not in {'HP', 'ATK', 'DEF'}: return None

        scaling_list: dict = PAL_DATA[pal]["Scaling"]
        if is_boss and f"{scaling_type}_BOSS" in scaling_list:
            return scaling_list[f"{scaling_type}_BOSS"]
        return scaling_list[scaling_type]

    @none_guard(data_source=PAL_DATA, subkey="SortingKey")
    @staticmethod
    def get_pal_sorting_key(key: str, sorting_key="paldeck") -> Optional[str]:
        sorting_key_list: dict = PAL_DATA[key]["SortingKey"]
        return sorting_key_list.get(sorting_key)

    @none_guard(data_source=PAL_DATA)
    @staticmethod
    def is_pal_human(key: str) -> Optional[bool]:
        return PAL_DATA[key].get("Human", False)
    
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
    def get_attack_i18n(key: str) -> Optional[str]:
        i18n_list: dict = PAL_ATTACKS[key]["I18n"]
        return i18n_list.get(Config.i18n, i18n_list.get('en'))
    
    @staticmethod
    def has_attack(key: str) -> bool:
        return key in PAL_ATTACKS
    
    @staticmethod
    def get_sorted_attacks() -> list[dict]:
        sorted_list = sorted(PAL_ATTACKS.values(), key=lambda item: (item['Type'], item['Power']))
        return sorted_list
    
    @none_guard(data_source=PAL_ATTACKS)
    @staticmethod
    def has_skill_fruit(attack: str) -> bool:
        return True if PAL_ATTACKS[attack].get("SkillFruit") else False

    @none_guard(data_source=PAL_PASSIVES, subkey="i18n")
    @staticmethod
    def get_passive_i18n(key: str) -> Optional[tuple[str, str]]:
        i18n_list: dict = PAL_PASSIVES[key]["i18n"]
        i18n: dict = i18n_list.get(Config.i18n, i18n_list.get('en'))
        return (i18n.get("Name"), i18n.get("Description"))

    @staticmethod
    def has_passive_skill(key: str) -> bool:
        return key in PAL_PASSIVES
    
    @staticmethod
    def get_sorted_passives() -> list[dict]:
        sorted_list = sorted(PAL_PASSIVES.values(), key=lambda item: (item['Rating'], item['CodeName']))
        return sorted_list
    
    @staticmethod
    def get_passive_buff(key: str, buff_key: str) -> float:
        return PAL_PASSIVES.get(key, {}).get("Buff", {}).get(buff_key, 0)
    
    @staticmethod
    def get_attacks_to_learn(pal: str, level: int) -> list[str]:
        attacks = DataProvider.get_pal_attacks(pal)
        if attacks is None: 
            return []
        return [attack for attack in attacks if attacks[attack] <= level]
    
    @staticmethod
    def get_attacks_to_forget(pal: str, level: int) -> list[str]:
        attacks = DataProvider.get_pal_attacks(pal)
        if attacks is None: 
            return []
        return [attack for attack in attacks if attacks[attack] > level and not DataProvider.has_skill_fruit(attack)]
    
    @staticmethod
    def is_valid_i18n(key: str):
        return key in I18N_LIST
    
    @staticmethod
    def get_i18n_options() -> list[str]:
        return I18N_LIST