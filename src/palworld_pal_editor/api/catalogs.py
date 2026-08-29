"""The game's own data, which no save can change (spec §8.4).

Five read-only catalogs served straight out of `DataProvider`. They touch no
`SaveManager` and take no session lock, because nothing here depends on which
save is open -- or on one being open at all.

Two shape changes from the routes these replace:

- Each catalog answers with a list and nothing else. The old routes sent the same
  rows twice, once as an array and once as a `{InternalName: row}` dict, so every
  payload was double its size and the client held two objects that had to agree.
  Building that index is one line in `stores/catalogs`, and it is built from the
  list rather than beside it.
- Passive and active skills are one resource, as §8.4 names five catalogs and not
  six. They are still two lists inside it: nothing reads them together.
"""

from flask import Blueprint
from flask_jwt_extended import jwt_required

from palworld_pal_editor.api.errors import register_error_handlers
from palworld_pal_editor.config import Config
from palworld_pal_editor.utils import DataProvider

catalogs_blueprint = Blueprint("catalogs", __name__)
register_error_handlers(catalogs_blueprint)


def _passive_skill_rows() -> list[dict]:
    rows = []
    for passive in DataProvider.get_sorted_passives():
        internal_name = passive["InternalName"]
        row = {
            "InternalName": internal_name,
            "I18n": list(
                DataProvider.get_passive_i18n(internal_name)
                or (internal_name, internal_name)
            ),
            "Rating": passive["Rating"],
            "Invalid": DataProvider.is_invalid_passive(internal_name),
            "Group": DataProvider.get_passive_group(internal_name),
        }
        if row["Invalid"]:
            row["I18n"][0] = "⚠️ " + row["I18n"][0]
        rows.append(row)
    return rows


def _active_skill_rows() -> list[dict]:
    rows = []
    for attack in DataProvider.get_sorted_attacks():
        internal_name = attack["InternalName"]
        row = {
            "InternalName": internal_name,
            "I18n": list(
                DataProvider.get_attack_i18n(internal_name) or [internal_name, ""]
            ),
            "HasSkillFruit": DataProvider.has_skill_fruit(internal_name),
            "IsUniqueSkill": DataProvider.is_unique_attacks(internal_name),
            "NonInheritable": DataProvider.is_non_inheritable_attack(internal_name),
            "Exclusive": DataProvider.is_exclusive_attack(internal_name),
            "BossSkill": DataProvider.is_boss_attack(internal_name),
            "Assignable": DataProvider.is_assignable_attack(internal_name),
            "AssignableToHumans": DataProvider.is_assignable_human_attack(
                internal_name
            ),
            "Power": attack["Power"],
            "Element": attack["Element"],
            "CT": attack["CT"],
            "Invalid": attack.get("Invalid", False),
            "LearnerNames": DataProvider.get_attack_learner_names(internal_name),
        }
        if row["Invalid"]:
            row["I18n"][0] = "⚠️ " + row["I18n"][0]
        rows.append(row)
    return rows


@catalogs_blueprint.route("/pals", methods=["GET"])
@jwt_required()
def get_pal_catalog():
    rows = []
    for pal in DataProvider.get_sorted_pals():
        internal_name = pal["InternalName"]
        tags = pal["VariantTags"]
        rows.append(
            {
                "InternalName": internal_name,
                "Elements": pal["Elements"],
                "Invalid": pal.get("Invalid", False),
                "Suitabilities": DataProvider.get_pal_suitabilities(internal_name),
                "I18n": DataProvider.get_pal_i18n(internal_name) or internal_name,
                "SortingKey": DataProvider.get_pal_sorting_key(internal_name),
                "IsHuman": DataProvider.is_pal_human(internal_name) or False,
                "FamilyID": pal["FamilyID"],
                "VariantKind": pal["VariantKind"],
                "VariantTags": tags,
                "IconKey": pal["IconKey"],
                "IconAccessKey": pal["IconKey"],
                "PaldeckRecordID": DataProvider.get_pal_paldeck_record_id(
                    internal_name
                ),
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
        )
    return {"pals": rows}


@catalogs_blueprint.route("/skills", methods=["GET"])
@jwt_required()
def get_skill_catalog():
    return {"passive": _passive_skill_rows(), "active": _active_skill_rows()}


@catalogs_blueprint.route("/items", methods=["GET"])
@jwt_required()
def get_item_catalog():
    rows = []
    for internal_name, item in DataProvider.get_item_data().items():
        translations = item.get("I18n", {})
        localized = translations.get(Config.i18n) or translations.get("en") or {}
        row = {key: value for key, value in item.items() if key != "I18n"}
        row.update(
            {
                "InternalName": internal_name,
                "Name": localized.get("Name") or internal_name,
                "Description": localized.get("Description") or "",
            }
        )
        rows.append(row)
    rows.sort(key=lambda row: (row["SortId"], row["InternalName"]))
    return {"items": rows}


@catalogs_blueprint.route("/technologies", methods=["GET"])
@jwt_required()
def get_technology_catalog():
    by_level: dict[str, list] = {}
    for tech in DataProvider.get_tech_data():
        icon_key = tech.removeprefix("SkillUnlock_")
        if tech.startswith("SkillUnlock_"):
            icon_key = DataProvider.resolve_pal_key(icon_key)
        by_level.setdefault(DataProvider.get_tech_lv(tech), []).append(
            {
                "InternalName": tech,
                "IconAccessKey": icon_key,
                "I18n": DataProvider.get_tech_i18n(tech),
                "BossTechnology": DataProvider.is_boss_tech(tech),
            }
        )
    return {"byLevel": by_level}


@catalogs_blueprint.route("/skins", methods=["GET"])
@jwt_required()
def get_skin_catalog():
    return {
        "skins": [
            {
                "SkinName": skin["SkinName"],
                "TargetPalName": skin["TargetPalName"],
                "Invalid": skin.get("Invalid", False),
            }
            for skin in DataProvider.get_skin_data().values()
            if skin.get("SkinType") == "EPalSkinType::Pal"
        ]
    }
