import json
import traceback
import uuid

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from palworld_pal_editor.config import Config
from palworld_pal_editor.core import PalEntity, SaveManager
from palworld_pal_editor.utils import LOGGER, DataProvider
from palworld_pal_editor.utils.util import reply

pal_blueprint = Blueprint("pal", __name__)

MAX_PAL_TEMPLATE_COUNT = 50
MAX_PAL_TEMPLATE_NAME_LENGTH = 64
MAX_PAL_JSON_BYTES = 2 * 1024 * 1024
SKILL_TEMPLATE_TYPES = {"active", "passive"}


def _pal_templates() -> list[dict]:
    if not isinstance(Config.palTemplates, list):
        Config.palTemplates = []
    return Config.palTemplates


def _skill_templates() -> list[dict]:
    if not isinstance(Config.skillTemplates, list):
        Config.skillTemplates = []
    return Config.skillTemplates


def _selected_pal(payload: dict) -> PalEntity | None:
    pal_guid = payload.get("PalGuid")
    player_uid = payload.get("PlayerUId")
    if player_uid == "PAL_BASE_WORKER_BTN":
        return SaveManager().get_working_pal(pal_guid)
    player = SaveManager().get_player(player_uid)
    return player.get_pal(pal_guid) if player else None


def _skill_template_summary(template: dict) -> dict:
    summary = {
        "Id": template["Id"],
        "Name": template["Name"],
        "Type": template["Type"],
    }
    if template["Type"] == "passive":
        summary["PassiveSkillList"] = list(template.get("PassiveSkillList") or [])
    else:
        summary["EquipWaza"] = list(template.get("EquipWaza") or [])
    return summary


def _replace_skill_group(pal: PalEntity, template: dict) -> None:
    template_type = template.get("Type")
    if template_type == "passive":
        skills = list(template.get("PassiveSkillList") or [])
        if len(skills) != len(set(skills)) or not all(
            isinstance(skill, str) and DataProvider.has_passive_skill(skill)
            for skill in skills
        ):
            raise ValueError("Passive skill template contains invalid skills.")
        pal.replace_PassiveSkillList(skills)
        return

    equipped = list(template.get("EquipWaza") or [])
    if (
        len(equipped) != len(set(equipped))
        or not all(
            isinstance(skill, str) and DataProvider.has_attack(skill)
            for skill in equipped
        )
    ):
        raise ValueError("Active skill template contains invalid skills.")
    pal.replace_EquipWaza(equipped)


def _parse_pal_json(raw: str) -> dict:
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_PAL_JSON_BYTES:
        raise ValueError("Pal JSON must be text smaller than 2 MiB.")
    pal_obj = json.loads(raw)
    if not isinstance(pal_obj, dict):
        raise TypeError("Pal JSON must contain one Pal object.")
    PalEntity(pal_obj)
    return pal_obj


def _template_summary(template: dict) -> dict:
    pal = PalEntity(_parse_pal_json(template["PalData"]))
    return {
        "Id": template["Id"],
        "Name": template["Name"],
        "CharacterID": pal.CharacterID,
        "DisplayName": pal.DisplayName,
        "IconAccessKey": pal.IconAccessKey,
        "Level": pal.Level or 1,
        "Rank": pal.Rank or 1,
        "IsAwakening": pal.IsAwakening,
        "Talent_HP": pal.Talent_HP or 0,
        "Talent_Shot": pal.Talent_Shot or 0,
        "Talent_Defense": pal.Talent_Defense or 0,
        "PassiveSkillList": pal.PassiveSkillList or [],
        "EquipWaza": pal.EquipWaza or [],
        "MasteredWaza": pal.MasteredWaza or [],
        "Suitabilities": pal.WorkSuitabilities or {},
    }


# Update Pal Data
@pal_blueprint.route("/paldata", methods=["PATCH"])
@jwt_required()
def patch_paldata():
    PalGuid = request.json.get("PalGuid")
    PlayerUId = request.json.get("PlayerUId")
    key = request.json.get("key")
    value = request.json.get("value")
    if key == "heal_all_pals":
        SaveManager().heal_all_pals()
        return reply(0)
    if PlayerUId == "PAL_BASE_WORKER_BTN":
        pal_entity = SaveManager().get_working_pal(PalGuid)
    else:
        pal_entity = SaveManager().get_player(PlayerUId).get_pal(PalGuid)
    try:
        match key:
            case "HasWorkerSick":
                pal_entity.heal_pal()
            case "IsFaintedPal":
                pal_entity.heal_pal()
            case "set_Suitability":
                pal_entity.set_WorkSuitability(value.get("name"), value.get("level"))
            case "set_Suitabilities":
                if not isinstance(value, dict) or any(
                    not isinstance(name, str)
                    or not isinstance(level, int)
                    or isinstance(level, bool)
                    for name, level in value.items()
                ):
                    return reply(1, None, "Invalid work suitability values.")
                for name, level in value.items():
                    pal_entity.set_WorkSuitability(name, level)
            case "pop_PassiveSkillList":
                pal_entity.pop_PassiveSkillList(item=value)
            case "pop_MasteredWaza":
                pal_entity.pop_MasteredWaza(item=value)
            case "pop_EquipWaza":
                pal_entity.pop_EquipWaza(item=value)
            case "add_PassiveSkillList":
                if not pal_entity.add_PassiveSkillList(value, True):
                    return reply(
                        1,
                        None,
                        f"Too many skills, or skill {value} already exists! Or we can't find it in database.",
                    )
            case "add_MasteredWaza":
                if not pal_entity.add_MasteredWaza(value):
                    return reply(
                        1,
                        None,
                        f"Too many skills, or skill {value} already exists! Or we can't find it in database.",
                    )
            case "add_EquipWaza":
                if not pal_entity.add_EquipWaza(value, True):
                    return reply(
                        1,
                        None,
                        f"Too many skills, or skill {value} already exists! Or we can't find it in database.",
                    )
            case "in_owner_palbox":
                if PlayerUId == "PAL_BASE_WORKER_BTN":
                    return reply(1, None, f"Moving pal to basecamp is unsupported.")
                player = SaveManager().get_player(PlayerUId)
                if not SaveManager().move_pal(
                    pal_entity.InstanceId,
                    [player.OtomoCharacterContainerId, player.PalStorageContainerId],
                ):
                    return reply(1, None, f"No enough slot in pal container.")
            case _:
                field = getattr(type(pal_entity), key, None)
                if not isinstance(field, property) or field.fset is None:
                    return reply(1, None, f"Unsupported Pal field: {key}")
                setattr(pal_entity, key, value)
    except Exception as e:
        stack_trace = traceback.format_exc()
        LOGGER.error(f"Error in patch_paldata {stack_trace}")
        return reply(1, None, f"Error in patch_paldata {stack_trace}")
    return reply(0)


# Get Pal Data
@pal_blueprint.route("/paldata", methods=["POST"])
@jwt_required()
def paldata():
    InstanceId = request.json.get("InstanceId")
    PlayerUId = request.json.get("PlayerUId")
    if PlayerUId == "PAL_BASE_WORKER_BTN":
        pal = SaveManager().get_working_pal(InstanceId)
        LOGGER.info(f"Get BASE WORKER {pal}")
    else:
        try:
            player = SaveManager().get_player(PlayerUId)
            pal = player.get_pal(InstanceId)
            LOGGER.info(f"Get {player.NickName}'s pal: {pal}")
        except:
            pass
    if pal:
        return reply(
            0,
            _pal_data(pal),
        )
    LOGGER.warning(
        f"Failed Getting Pal with PlayerID: {PlayerUId}, PalID: {InstanceId}"
    )
    return reply(
        1, None, f"Failed Getting Pal with PlayerID: {PlayerUId}, PalID: {InstanceId}"
    )


@pal_blueprint.route("/maximize", methods=["POST"])
@jwt_required()
def maximize_pal():
    payload = request.json or {}
    pal = _selected_pal(payload)
    if pal is None:
        return reply(1, None, "Failed to find the selected Pal.")
    try:
        pal.maximize_progression()
    except (KeyError, TypeError, ValueError):
        stack_trace = traceback.format_exc()
        LOGGER.error(f"Error maximizing Pal progression {stack_trace}")
        return reply(1, None, f"Error maximizing Pal progression {stack_trace}")
    return reply(0, _pal_data(pal))


# Just some dumb shit
def _pal_data(pal: PalEntity):
    record = DataProvider.get_pal_record(pal.CharacterID) or {}
    return {
        "InstanceId": str(pal.InstanceId) if pal.InstanceId else None,
        "OwnerPlayerUId": (str(pal.OwnerPlayerUId) if pal.OwnerPlayerUId else None),
        "group_id": str(pal.group_id) if pal.group_id else None,
        "ContainerId": str(pal.ContainerId) if pal.CharacterID else None,
        "SlotIndex": pal.SlotIndex,
        "FavoriteIndex": pal.FavoriteIndex,
        "IsImportedCharacter": pal.IsImportedCharacter,
        "OwnerName": pal.OwnerName or None,
        "CharacterID": pal.CharacterID,
        "IconAccessKey": pal.IconAccessKey or None,
        "IconKey": DataProvider.get_pal_icon_key(pal.CharacterID),
        "DataAccessKey": pal.DataAccessKey or None,
        "FamilyID": pal.RawSpecieKey,
        "VariantKind": DataProvider.get_pal_variant_kind(pal.CharacterID),
        "VariantTags": list(DataProvider.get_pal_variant_tags(pal.CharacterID)),
        "PaldeckRecordID": DataProvider.get_pal_paldeck_record_id(pal.CharacterID),
        "PaldeckIndex": record.get("PaldeckIndex"),
        "PaldeckSuffix": record.get("PaldeckSuffix", ""),
        "Invalid": record.get("Invalid", True),
        "RegularlyObtainable": record.get("RegularlyObtainable", False),
        "AvailabilitySources": record.get("AvailabilitySources", []),
        "ObtainMethods": record.get("ObtainMethods", []),
        "I18nName": pal.I18nName or None,
        "DisplayName": pal.DisplayName or None,
        "NickName": pal.NickName or "",
        "SkinName": pal.SkinName or "",
        "Gender": pal.Gender.value if pal.Gender else None,
        "Level": pal.Level or 1,
        "FriendshipLevel": pal.FriendshipLevel or 0,
        "HasBaseVariant": pal.HasBaseVariant,
        "HasBossVariant": pal.HasBossVariant,
        "HasTowerVariant": pal.HasTowerVariant,
        "HasRaidVariant": pal.HasRaidVariant,
        "HasPredatorVariant": pal.HasPredatorVariant,
        "HasWorkerSick": pal.HasWorkerSick,
        "IsFaintedPal": pal.IsFaintedPal,
        "Is_Unref_Pal": pal.is_unreferenced_pal,
        "IsNewPal": pal.is_new_pal,
        "in_owner_palbox": pal.in_owner_palbox,
        "IsHuman": pal.IsHuman,
        "IsBOSS": pal.IsBOSS or False,
        "IsRarePal": pal.IsRarePal or False,
        "IsTower": pal.IsTower or False,
        "IsRAID": pal.IsRAID or False,
        "IsPREDATOR": pal.IsPREDATOR or False,
        "IsSUMMON": pal.IsSUMMON or False,
        "IsOilrig": pal.IsOilrig or False,
        "IsOtomoTower": pal.IsOtomoTower or False,
        "IsExpeditionPal": pal.IsExpeditionPal,
        "ComputedMaxHP": pal.ComputedMaxHP or None,
        "ComputedAttack": pal.ComputedAttack or None,
        "ComputedDefense": pal.ComputedDefense or None,
        "ComputedCraftSpeed": pal.ComputedCraftSpeed or None,
        "Rank": pal.Rank if pal.Rank else 1,
        "RankUpExp": pal.RankUpExp,
        "IsAwakening": pal.IsAwakening,
        "Rank_HP": pal.Rank_HP or 0,
        "Rank_Attack": pal.Rank_Attack or 0,
        "Rank_Defence": pal.Rank_Defence or 0,
        "Rank_CraftSpeed": pal.Rank_CraftSpeed or 0,
        "Talent_HP": pal.Talent_HP or 0,
        "Talent_Melee": pal.Talent_Melee or 0,
        "Talent_Shot": pal.Talent_Shot or 0,
        "Talent_Defense": pal.Talent_Defense or 0,
        "PassiveSkillList": pal.PassiveSkillList or [],
        "EquipWaza": pal.EquipWaza or [],
        "MasteredWaza": pal.MasteredWaza or [],
        "Suitabilities": pal.WorkSuitabilities or {},
        "SuitabilityMinimums": pal.MinimumWorkSuitabilities or {},
    }


@pal_blueprint.route("/dump_data", methods=["POST"])
@jwt_required()
def dump_data():
    PalGuid = request.json.get("PalGuid")
    PlayerUId = request.json.get("PlayerUId")
    if PlayerUId == "PAL_BASE_WORKER_BTN":
        pal = SaveManager().get_working_pal(PalGuid)
        LOGGER.info(f"Get BASE WORKER {pal}")
    else:
        try:
            player = SaveManager().get_player(PlayerUId)
            pal = player.get_pal(PalGuid)
            LOGGER.info(f"Get {player.NickName}'s pal: {pal}")
        except:
            pass
    if pal:
        return reply(0, pal.dump_obj())
    LOGGER.warning(f"Failed Getting Pal with PlayerID: {PlayerUId}, PalID: {PalGuid}")
    return reply(
        1, None, f"Failed Getting Pal with PlayerID: {PlayerUId}, PalID: {PalGuid}"
    )


@pal_blueprint.route("/pal/<pal_id>", methods=["DELETE"])
@jwt_required()
def delete_pal(pal_id):
    if SaveManager().delete_pal(pal_id):
        return reply(0)
    return reply(1, None, f"Error Deleting Pal {pal_id}, check logs for more info.")


@pal_blueprint.route("/add_pal", methods=["POST"])
@jwt_required()
def add_pal():
    payload = request.json or {}
    PlayerUId = payload.get("PlayerUId")
    if PlayerUId == "PAL_BASE_WORKER_BTN":
        LOGGER.warning("Directly add pal to basecamp is not yet supported.")
        return reply(1, None, f"Directly adding pal to basecamp is not yet supported.")
    try:
        mode = payload.get("Mode", "default")
        pal_obj = None
        if mode == "json":
            pal_obj = _parse_pal_json(payload.get("PalJson"))
        elif mode == "template":
            template_id = payload.get("TemplateId")
            template = next(
                (item for item in _pal_templates() if item.get("Id") == template_id),
                None,
            )
            if template is None:
                return reply(1, None, "Pal template not found.")
            pal_obj = _parse_pal_json(template.get("PalData"))
        elif mode != "default":
            return reply(1, None, "Unsupported Pal creation mode.")

        pal_entity = SaveManager().add_pal(PlayerUId, pal_obj)
        if not pal_entity:
            return reply(
                1,
                None,
                "Failed adding Pal. Its containers may be full; check the logs for details.",
            )
    except (TypeError, ValueError, json.JSONDecodeError, KeyError):
        return reply(1, None, f"Invalid Pal data. {traceback.format_exc()}")
    except Exception:
        LOGGER.error(f"Error adding Pal: {traceback.format_exc()}")
        return reply(1, None, "Error adding Pal. Check the logs for details.")
    return reply(0, _pal_data(pal_entity))


@pal_blueprint.route("/templates", methods=["GET"])
@jwt_required()
def list_pal_templates():
    templates = []
    for template in _pal_templates():
        try:
            templates.append(_template_summary(template))
        except (TypeError, ValueError, json.JSONDecodeError, KeyError):
            template_id = template.get("Id") if isinstance(template, dict) else None
            LOGGER.warning(f"Ignoring invalid Pal template {template_id}")
    return reply(0, templates)


@pal_blueprint.route("/templates", methods=["POST"])
@jwt_required()
def create_pal_template():
    payload = request.json or {}
    name = payload.get("Name")
    if not isinstance(name, str) or not (name := name.strip()):
        return reply(1, None, "Template name is required.")
    if len(name) > MAX_PAL_TEMPLATE_NAME_LENGTH:
        return reply(1, None, "Template name must be 64 characters or fewer.")
    if len(_pal_templates()) >= MAX_PAL_TEMPLATE_COUNT:
        return reply(1, None, "At most 50 Pal templates can be saved.")

    player = SaveManager().get_player(payload.get("PlayerUId"))
    pal = player.get_pal(payload.get("PalGuid")) if player else None
    if pal is None:
        return reply(1, None, "Selected Pal not found.")

    template = {
        "Id": uuid.uuid4().hex,
        "Name": name,
        "PalData": pal.dump_obj(),
    }
    try:
        summary = _template_summary(template)
    except (TypeError, ValueError, json.JSONDecodeError, KeyError):
        return reply(1, None, "Selected Pal data cannot be saved as a template.")

    templates = _pal_templates()
    templates.append(template)
    try:
        Config.save_to_file()
    except Exception:
        templates.remove(template)
        raise
    return reply(0, summary)


@pal_blueprint.route("/templates/<template_id>", methods=["DELETE"])
@jwt_required()
def delete_pal_template(template_id: str):
    templates = _pal_templates()
    template = next((item for item in templates if item.get("Id") == template_id), None)
    if template is None:
        return reply(1, None, "Pal template not found.")
    index = templates.index(template)
    templates.pop(index)
    try:
        Config.save_to_file()
    except Exception:
        templates.insert(index, template)
        raise
    return reply(0)


@pal_blueprint.route("/skill_templates", methods=["GET"])
@jwt_required()
def list_skill_templates():
    templates = []
    for template in _skill_templates():
        try:
            if template.get("Type") in SKILL_TEMPLATE_TYPES:
                templates.append(_skill_template_summary(template))
        except (AttributeError, KeyError, TypeError):
            LOGGER.warning("Ignoring invalid skill template entry")
    return reply(0, templates)


@pal_blueprint.route("/skill_templates", methods=["POST"])
@jwt_required()
def create_skill_template():
    payload = request.json or {}
    name = payload.get("Name")
    template_type = payload.get("Type")
    if not isinstance(name, str) or not (name := name.strip()):
        return reply(1, None, "Template name is required.")
    if len(name) > MAX_PAL_TEMPLATE_NAME_LENGTH:
        return reply(1, None, "Template name must be 64 characters or fewer.")
    if template_type not in SKILL_TEMPLATE_TYPES:
        return reply(1, None, "Skill template type must be active or passive.")
    if len(_skill_templates()) >= MAX_PAL_TEMPLATE_COUNT:
        return reply(1, None, "At most 50 skill templates can be saved.")

    pal = _selected_pal(payload)
    if pal is None:
        return reply(1, None, "Selected Pal not found.")

    template = {
        "Id": uuid.uuid4().hex,
        "Name": name,
        "Type": template_type,
    }
    if template_type == "passive":
        template["PassiveSkillList"] = list(pal.PassiveSkillList or [])
    else:
        template["EquipWaza"] = list(pal.EquipWaza or [])

    templates = _skill_templates()
    templates.append(template)
    try:
        Config.save_to_file()
    except Exception:
        templates.remove(template)
        raise
    return reply(0, _skill_template_summary(template))


@pal_blueprint.route("/skill_templates/<template_id>", methods=["PATCH"])
@jwt_required()
def rename_skill_template(template_id: str):
    name = (request.json or {}).get("Name")
    if not isinstance(name, str) or not (name := name.strip()):
        return reply(1, None, "Template name is required.")
    if len(name) > MAX_PAL_TEMPLATE_NAME_LENGTH:
        return reply(1, None, "Template name must be 64 characters or fewer.")
    template = next(
        (item for item in _skill_templates() if item.get("Id") == template_id),
        None,
    )
    if template is None:
        return reply(1, None, "Skill template not found.")
    old_name = template.get("Name")
    template["Name"] = name
    try:
        Config.save_to_file()
    except Exception:
        template["Name"] = old_name
        raise
    return reply(0, _skill_template_summary(template))


@pal_blueprint.route("/skill_templates/<template_id>/apply", methods=["POST"])
@jwt_required()
def apply_skill_template(template_id: str):
    template = next(
        (item for item in _skill_templates() if item.get("Id") == template_id),
        None,
    )
    if template is None:
        return reply(1, None, "Skill template not found.")
    pal = _selected_pal(request.json or {})
    if pal is None:
        return reply(1, None, "Selected Pal not found.")
    try:
        _replace_skill_group(pal, template)
    except (AttributeError, TypeError, ValueError) as error:
        return reply(1, None, str(error))
    summary = _skill_template_summary(template)
    if template.get("Type") == "active":
        summary["MasteredWaza"] = list(pal.MasteredWaza or [])
    return reply(0, summary)


@pal_blueprint.route("/skill_templates/<template_id>", methods=["DELETE"])
@jwt_required()
def delete_skill_template(template_id: str):
    templates = _skill_templates()
    template = next((item for item in templates if item.get("Id") == template_id), None)
    if template is None:
        return reply(1, None, "Skill template not found.")
    index = templates.index(template)
    templates.pop(index)
    try:
        Config.save_to_file()
    except Exception:
        templates.insert(index, template)
        raise
    return reply(0)


@pal_blueprint.route("/dupe_pal", methods=["POST"])
@jwt_required()
def dupe_pal():
    PalGuid = request.json.get("PalGuid")
    PlayerUId = request.json.get("PlayerUId")
    if PlayerUId == "PAL_BASE_WORKER_BTN":
        LOGGER.warning("Directly add pal to basecamp is not yet supported.")
        return reply(1, None, f"Directly adding pal to basecamp is not yet supported.")
    else:
        try:
            player = SaveManager().get_player(PlayerUId)
            pal_obj = player.get_pal(PalGuid)._pal_obj

            pal_entity = SaveManager().add_pal(PlayerUId, pal_obj)
            if not pal_entity:
                return reply(
                    1,
                    None,
                    f"Failed duping pal, likely your pal containers are full, check logs for detail.",
                )
        except:
            return reply(
                1,
                None,
                f"Error happened during duping pal, check logs for detail. {traceback.format_exc()}",
            )
    return reply(0, _pal_data(pal_entity))
