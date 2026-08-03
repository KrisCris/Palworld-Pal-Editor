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
PAL_DATA: dict[str, dict] = load_json("pal_data.json") | load_json("human_data.json")
PAL_DATA_BY_CASEFOLD = {key.casefold(): key for key in PAL_DATA}
PALDECK_RECORD_ID_ALIASES = {
    "Blueplatypus": "BluePlatypus",
    "Werewolf_Ice": "WereWolf_Ice",
}
PAL_VARIANT_KIND_ORDER = {
    kind: index
    for index, kind in enumerate(
        (
            "base",
            "alpha",
            "boss",
            "predator",
            "quest",
            "tower",
            "raid",
            "boss-rush",
            "summon",
            "oilrig",
            "human",
            "other",
        )
    )
}


def _variant_sort_key(character_id: str) -> tuple[int, int, str]:
    record = PAL_DATA[character_id]
    return (
        0 if "base" in record.get("VariantTags", ()) else 1,
        PAL_VARIANT_KIND_ORDER.get(record.get("VariantKind"), 999),
        character_id,
    )


_pal_variants_by_family: dict[str, list[str]] = {}
for _character_id, _record in PAL_DATA.items():
    _pal_variants_by_family.setdefault(_record["FamilyID"], []).append(_character_id)
PAL_VARIANTS_BY_FAMILY: dict[str, tuple[str, ...]] = {
    family_id: tuple(sorted(variants, key=_variant_sort_key))
    for family_id, variants in _pal_variants_by_family.items()
}
PAL_PASSIVES: dict[str, dict] = load_json("pal_passives.json")
PAL_EXP_TABLE: list[int] = load_json("pal_exp_table.json")
PAL_FRIENDSHIP: dict[str, dict] = load_json("pal_friendship.json")
PLAYER_STATUS_DATA: dict[str, dict] = load_json("player_status_data.json")
TECH_DATA: dict[str, dict] = load_json("tech_data.json")
SKIN_DATA: dict[str, dict] = load_json("skin_data.json")

# PAL_ICONS: dict[str] = load_icons("pals")

# I18N_LIST = ["en", "zh-CN", "ja"]
I18N_LIST: dict[str, str] = load_json("i18n_list.json")


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

    @staticmethod
    def default_i18n() -> str:
        return "en"

    @staticmethod
    def get_player_status_data() -> dict[str, dict]:
        return PLAYER_STATUS_DATA

    def get_i18n_map() -> dict[str, str]:
        return I18N_LIST

    # @staticmethod
    # def get_pal_icon(key: str) -> Optional[Any]:
    #     if key not in PAL_ICONS:
    #         LOGGER.warning(f"Pal icon {key} doesn't exist.")
    #         return
    #     return PAL_ICONS[key]
    @staticmethod
    def in_pal_data(key: str) -> bool:
        """
        Checks if the key exists in the PAL_DATA dictionary.
        """
        return key in PAL_DATA

    @staticmethod
    def resolve_pal_key(key: Optional[str]) -> Optional[str]:
        if not key or key in PAL_DATA:
            return key
        return PAL_DATA_BY_CASEFOLD.get(key.casefold(), key)

    @staticmethod
    def get_pal_record(key: Optional[str]) -> Optional[dict]:
        return PAL_DATA.get(DataProvider.resolve_pal_key(key))

    @staticmethod
    def get_pal_family_id(character_id: str) -> str:
        record = DataProvider.get_pal_record(character_id)
        return record["FamilyID"] if record else character_id

    @staticmethod
    def get_pal_variant_kind(character_id: str) -> str:
        record = DataProvider.get_pal_record(character_id)
        return record.get("VariantKind", "other") if record else "other"

    @staticmethod
    def get_pal_variant_tags(character_id: str) -> tuple[str, ...]:
        record = DataProvider.get_pal_record(character_id)
        return tuple(record.get("VariantTags", ())) if record else ()

    @staticmethod
    def get_pal_icon_key(character_id: str) -> str:
        record = DataProvider.get_pal_record(character_id)
        return record.get("IconKey", "unknown") if record else "unknown"

    @staticmethod
    def get_pal_paldeck_record_id(character_id: str) -> Optional[str]:
        record = DataProvider.get_pal_record(character_id)
        if not record or record.get("Human", False):
            return None
        record_id = record.get("PaldeckRecordID") or record["FamilyID"]
        return PALDECK_RECORD_ID_ALIASES.get(record_id, record_id)

    @staticmethod
    def get_family_variants(
        character_id: str, kind: Optional[str] = None
    ) -> tuple[str, ...]:
        record = DataProvider.get_pal_record(character_id)
        if not record:
            return (character_id,) if kind is None else ()
        variants = PAL_VARIANTS_BY_FAMILY[record["FamilyID"]]
        if kind is None:
            return variants
        return tuple(
            variant
            for variant in variants
            if PAL_DATA[variant].get("VariantKind") == kind
        )

    @staticmethod
    def get_pal_variant(character_id: str, kind: str) -> Optional[str]:
        variants = DataProvider.get_family_variants(character_id, kind)
        return variants[0] if len(variants) == 1 else None

    @none_guard(data_source=PAL_DATA, subkey="I18n")
    @staticmethod
    def get_pal_i18n(key: str) -> Optional[str]:
        tags = set(PAL_DATA[key].get("VariantTags", ()))
        if tags and tags.issubset({"alpha", "boss"}):
            key = DataProvider.get_pal_variant(key, "base") or key
        i18n_list: dict = PAL_DATA[key]["I18n"]
        return i18n_list.get(Config.i18n, i18n_list.get("en"))

    @none_guard(data_source=PAL_DATA, subkey="Stats")
    @staticmethod
    def get_pal_stats(pal: str, scaling_type: str) -> Optional[int]:
        scaling_list: dict = PAL_DATA[pal]["Stats"]
        return scaling_list.get(scaling_type, None)

    @none_guard(data_source=PAL_DATA, subkey="Parameters")
    @staticmethod
    def get_pal_parameter(pal: str, parameter: str) -> Optional[float]:
        return PAL_DATA[pal]["Parameters"].get(parameter)

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
                len(item["InternalName"]),
            ),
        )
        return sorted_list

    @staticmethod
    def is_pal_human(key: str) -> Optional[bool]:
        record = DataProvider.get_pal_record(key)
        return record.get("Human", False) if record else None

    @staticmethod
    def has_human_icon(key: str) -> bool:
        record = DataProvider.get_pal_record(key)
        return record.get("HasIcon", False) if record else False

    @staticmethod
    def get_skin_data() -> dict[str, dict]:
        return SKIN_DATA

    @staticmethod
    def get_skin(key: str) -> Optional[dict]:
        return SKIN_DATA.get(key)

    @staticmethod
    def get_skins_for_pal(key: str) -> list[dict]:
        return [
            skin
            for skin in SKIN_DATA.values()
            if skin.get("TargetPalName") == key
        ]

    @staticmethod
    def is_pal_invalid(key: str) -> bool:
        if key not in PAL_DATA:
            return True
        return PAL_DATA[key].get("Invalid", False)

    @none_guard(data_source=PAL_DATA, subkey="Attacks")
    def get_pal_attacks(pal: str) -> Optional[list[str]]:
        return PAL_DATA[pal]["Attacks"]

    @none_guard(data_source=PAL_DATA, subkey="Suitabilities")
    def get_pal_suitabilities(pal: str) -> Optional[dict[str, int]]:
        return PAL_DATA[pal]["Suitabilities"]

    @none_guard(data_source=PAL_DATA, subkey="BestWorkSuitability")
    def get_pal_best_work_suitability(pal: str) -> Optional[str]:
        return PAL_DATA[pal]["BestWorkSuitability"]

    @staticmethod
    def get_pal_level_xp(lv: int) -> Optional[int]:
        try:
            return PAL_EXP_TABLE[str(lv)]["PalTotalEXP"]
        except Exception:
            LOGGER.warning(f"Level {lv} is out of bounds.")
            return None
        
    @staticmethod
    def get_pal_friendship(lv: str) -> Optional[int]:
        try:
            return PAL_FRIENDSHIP[str(lv)]["required_point"]
        except Exception:
            LOGGER.warning(f"Friendship level {lv} is out of bounds.")
            return None
        
    @staticmethod
    def get_pal_friendship_level_from_pts(pts: int) -> Optional[int]:
        max_lv = -3
        for level, data in PAL_FRIENDSHIP.items():
            if pts >= data["required_point"]:
                max_lv = max(max_lv, int(level))
        return max_lv

    @none_guard(data_source=PAL_ATTACKS, subkey="I18n")
    @staticmethod
    def get_attack_i18n(key: str) -> Optional[tuple[str, str]]:
        i18n_list: dict = PAL_ATTACKS[key]["I18n"]
        english: dict = i18n_list.get("en", {})
        i18n: dict = i18n_list.get(Config.i18n, {})
        return (
            i18n.get("Name") or english.get("Name") or key,
            i18n.get("Description") or english.get("Description", ""),
        )

    @staticmethod
    def get_attack_learner_names(key: str) -> list[str]:
        names = []
        seen = set()
        for learner in PAL_ATTACKS.get(key, {}).get("Learners", ()):
            family = DataProvider.get_pal_family_id(learner.get("CharacterID", ""))
            if not family or family.casefold() in seen:
                continue
            seen.add(family.casefold())
            names.append(DataProvider.get_pal_i18n(family) or family)
        return names

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
    def is_non_inheritable_attack(key: str) -> bool:
        return PAL_ATTACKS.get(key, {}).get("NonInheritable", False)

    @staticmethod
    def is_exclusive_attack(key: str) -> bool:
        return PAL_ATTACKS.get(key, {}).get("Exclusive", False)

    @staticmethod
    def is_boss_attack(key: str) -> bool:
        return PAL_ATTACKS.get(key, {}).get("BossSkill", False)

    @staticmethod
    def is_assignable_attack(key: str) -> bool:
        return PAL_ATTACKS.get(key, {}).get("Assignable", False)

    @staticmethod
    def is_assignable_human_attack(key: str) -> bool:
        return PAL_ATTACKS.get(key, {}).get("AssignableToHumans", False)

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
                item["CT"],
            ),
        )
        return sorted_list

    @none_guard(data_source=PAL_PASSIVES, subkey="I18n")
    @staticmethod
    def get_passive_i18n(key: str) -> Optional[tuple[str, str]]:
        i18n_list: dict = PAL_PASSIVES[key]["I18n"]
        english: dict = i18n_list.get("en", {})
        i18n: dict = i18n_list.get(Config.i18n, {})
        return (
            i18n.get("Name") or english.get("Name") or key,
            i18n.get("Description") or english.get("Description", ""),
        )

    @staticmethod
    def has_passive_skill(key: str) -> bool:
        return key in PAL_PASSIVES

    @staticmethod
    def get_sorted_passives() -> list[dict]:
        sorted_list = sorted(
            PAL_PASSIVES.values(),
            key=lambda item: (
                -item["Rating"],
                DataProvider.get_passive_i18n(item["InternalName"]),
            ),
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
        return I18N_LIST.keys()

    @staticmethod
    def get_player_level_xp(lv: int) -> Optional[int]:
        try:
            return PAL_EXP_TABLE[str(lv)]["TotalEXP"]
        except IndexError:
            LOGGER.warning(f"Level {lv} is out of bounds.")
            return None

    @staticmethod
    def get_tech_data() -> dict[str, dict]:
        return TECH_DATA

    @staticmethod
    def get_tech_i18n(key: str) -> dict | str | None:
        record = TECH_DATA.get(key)
        if record is None:
            return None
        i18n_list: dict = record.get("I18n", {})
        return (
            i18n_list.get(Config.i18n)
            or i18n_list.get("en")
            or i18n_list.get("ja")
            or key
        )

    @staticmethod
    def get_tech_lv(key: str) -> int:
        return TECH_DATA.get(key, {}).get("Level", 0)

    @staticmethod
    def is_boss_tech(key: str) -> bool:
        return TECH_DATA.get(key, {}).get("BossTechnology", False)
