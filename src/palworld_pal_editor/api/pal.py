import json
import traceback
import uuid

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from palworld_pal_editor.config import Config
from palworld_pal_editor.core import PalEntity, PalIdentityConflict, SaveManager
from palworld_pal_editor.utils import LOGGER, DataProvider
from palworld_pal_editor.utils.util import reply

pal_blueprint = Blueprint("pal", __name__)

MAX_PAL_TEMPLATE_COUNT = 50
MAX_PAL_TEMPLATE_NAME_LENGTH = 64
MAX_PAL_JSON_BYTES = 2 * 1024 * 1024
SKILL_TEMPLATE_TYPES = {"active", "passive"}


@pal_blueprint.route("/containers", methods=["GET"])
@jwt_required()
def list_pal_containers():
    return reply(0, SaveManager().get_container_registry())


@pal_blueprint.route("/creation_targets/<path:roster_key>", methods=["GET"])
@jwt_required()
def list_pal_creation_targets(roster_key):
    return reply(0, SaveManager().creation_targets(roster_key))


@pal_blueprint.route("/move", methods=["POST"])
@pal_blueprint.route("/transfer", methods=["POST"])
@jwt_required()
def move_pal():
    payload = request.json or {}
    source_record_key = payload.get("SourceRecordKey")
    target_storage_key = payload.get("TargetStorageKey")
    if source_record_key or target_storage_key:
        if not source_record_key or not target_storage_key:
            return reply(
                1,
                None,
                "SourceRecordKey and TargetStorageKey are required.",
            )
        try:
            manager = SaveManager()
            source = manager.get_record(source_record_key)
            result = manager.transfer_pal(
                source_record_key,
                target_storage_key,
                payload.get("Action", "move"),
                payload.get("ExpectedTargetRecordKey"),
            )
            return reply(0, result)
        except PalIdentityConflict as conflict:
            locked = conflict.candidates[0] if len(conflict.candidates) == 1 else None
            return reply(
                1,
                {
                    "Code": "PAL_IDENTITY_CONFLICT",
                    "Incoming": _pal_brief(source.pal) if source else None,
                    "Candidates": [
                        _record_location(manager, candidate)
                        for candidate in conflict.candidates
                    ],
                    "LockedTarget": locked.record_key if locked else None,
                    "Existing": _pal_brief(locked.pal) if locked else None,
                    "FieldChanges": (
                        _brief_field_changes(source.pal, locked.pal)
                        if source and locked
                        else {}
                    ),
                },
                "This genetic identity already exists.",
            )
        except ValueError as error:
            return reply(1, None, str(error))
        except Exception:
            LOGGER.error(f"Error transferring Pal: {traceback.format_exc()}")
            return reply(1, None, "Error transferring Pal. No changes were kept.")

    pal_guid = payload.get("PalGuid")
    target_container_id = payload.get("TargetContainerId")
    if not pal_guid or not target_container_id:
        return reply(1, None, "PalGuid and TargetContainerId are required.")
    try:
        SaveManager().move_pal(pal_guid, target_container_id)
        pal = SaveManager().get_pal(pal_guid)
        return reply(0, _pal_data(pal) if pal else None)
    except ValueError as error:
        return reply(1, None, str(error))
    except Exception:
        LOGGER.error(f"Error moving Pal: {traceback.format_exc()}")
        return reply(1, None, "Error moving Pal. No changes were kept.")


def _pal_templates() -> list[dict]:
    if not isinstance(Config.palTemplates, list):
        Config.palTemplates = []
    return Config.palTemplates


def _skill_templates() -> list[dict]:
    if not isinstance(Config.skillTemplates, list):
        Config.skillTemplates = []
    return Config.skillTemplates


def _selected_record(payload: dict):
    manager = SaveManager()
    if record_key := payload.get("RecordKey"):
        return manager.get_record(record_key)
    return manager.get_unique_world_record(
        payload.get("PalGuid") or payload.get("InstanceId")
    )


def _selected_pal(payload: dict) -> PalEntity | None:
    record = _selected_record(payload)
    return record.pal if record else None


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
        "IconKey": DataProvider.get_pal_icon_key(pal.CharacterID),
        "IconAccessKey": pal.IconAccessKey,
        "Level": pal.Level or 1,
        "Rank": pal.Rank or 1,
        "FriendshipLevel": pal.FriendshipLevel or 0,
        "FavoriteIndex": pal.FavoriteIndex,
        "IsBOSS": pal.IsBOSS or False,
        "IsRarePal": bool(pal.IsRarePal),
        "IsAwakening": pal.IsAwakening,
        "IsImportedCharacter": pal.IsImportedCharacter,
        "Talent_HP": pal.Talent_HP or 0,
        "Talent_Shot": pal.Talent_Shot or 0,
        "Talent_Defense": pal.Talent_Defense or 0,
        "Rank_HP": pal.Rank_HP or 0,
        "Rank_Attack": pal.Rank_Attack or 0,
        "Rank_Defence": pal.Rank_Defence or 0,
        "Rank_CraftSpeed": pal.Rank_CraftSpeed or 0,
        "PassiveSkillList": pal.PassiveSkillList or [],
        "EquipWaza": pal.EquipWaza or [],
        "MasteredWaza": pal.MasteredWaza or [],
        "Suitabilities": pal.WorkSuitabilities or {},
    }


# Update Pal Data
@pal_blueprint.route("/paldata", methods=["PATCH"])
@jwt_required()
def patch_paldata():
    payload = request.json or {}
    key = payload.get("key")
    value = payload.get("value")
    if key == "heal_all_pals":
        SaveManager().heal_all_pals()
        return reply(0)
    try:
        record = _selected_record(payload)
        if record is None:
            return reply(1, None, "Selected Pal not found.")
        pal_entity = record.pal
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
                if record.storage_kind != "world" or pal_entity.OwnerPlayerUId is None:
                    return reply(1, None, f"Moving pal to basecamp is unsupported.")
                player = SaveManager().get_player(pal_entity.OwnerPlayerUId)
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
        SaveManager().normalize_external_record(record)
    except Exception as e:
        stack_trace = traceback.format_exc()
        LOGGER.error(f"Error in patch_paldata {stack_trace}")
        return reply(1, None, f"Error in patch_paldata {stack_trace}")
    return reply(0, _pal_data(pal_entity, record))


# Get Pal Data
@pal_blueprint.route("/paldata", methods=["POST"])
@jwt_required()
def paldata():
    payload = request.json or {}
    try:
        record = _selected_record(payload)
    except ValueError as error:
        return reply(1, None, str(error))
    if record:
        return reply(0, _pal_data(record.pal, record))
    return reply(1, None, "Selected Pal not found.")


@pal_blueprint.route("/maximize", methods=["POST"])
@jwt_required()
def maximize_pal():
    payload = request.json or {}
    try:
        record = _selected_record(payload)
        if record is None:
            return reply(1, None, "Failed to find the selected Pal.")
        pal = record.pal
        pal.maximize_progression()
        SaveManager().normalize_external_record(record)
    except (KeyError, TypeError, ValueError):
        stack_trace = traceback.format_exc()
        LOGGER.error(f"Error maximizing Pal progression {stack_trace}")
        return reply(1, None, f"Error maximizing Pal progression {stack_trace}")
    return reply(0, _pal_data(pal, record))


# Just some dumb shit
def _pal_data(pal: PalEntity, pal_record=None):
    record = DataProvider.get_pal_record(pal.CharacterID) or {}
    manager = SaveManager()
    record_resolver = getattr(manager, "resolve_record_location", None)
    resolver = getattr(manager, "resolve_pal_location", None)
    location = (
        record_resolver(pal_record)
        if pal_record is not None and record_resolver
        else resolver(pal)
        if resolver and getattr(manager, "container_data", None)
        else {
        "RecordedContainerId": str(pal.ContainerId) if pal.ContainerId else None,
        "RecordedSlotIndex": pal.SlotIndex,
        "ActualContainerId": str(pal.ContainerId) if pal.ContainerId else None,
        "ActualSlotIndex": pal.SlotIndex,
        "ActualLocations": [],
        "LocationStatus": "ok",
        "LocationAnomaly": None,
        "ContainerKind": "other",
        "ContainerLabel": None,
        }
    )
    owner_uid = _guid_string_or_none(pal.OwnerPlayerUId)
    return {
        "RecordKey": pal_record.record_key if pal_record else f"world:{pal.InstanceId}",
        "StorageKey": pal_record.storage_key if pal_record else None,
        "StorageKind": pal_record.storage_kind if pal_record else "world",
        "StorageOwnerPlayerUid": (
            pal_record.storage_owner_uid if pal_record else None
        ),
        "InstanceId": str(pal.InstanceId) if pal.InstanceId else None,
        "OwnerPlayerUId": owner_uid,
        "group_id": _guid_string_or_none(pal.group_id),
        "ContainerId": location["RecordedContainerId"],
        "SlotIndex": location["RecordedSlotIndex"],
        "ActualContainerId": location["ActualContainerId"],
        "ActualSlotIndex": location["ActualSlotIndex"],
        "ActualLocations": location["ActualLocations"],
        "LocationStatus": location["LocationStatus"],
        "LocationAnomaly": location["LocationAnomaly"],
        "ContainerKind": location["ContainerKind"],
        "ContainerLabel": location["ContainerLabel"],
        "FavoriteIndex": pal.FavoriteIndex,
        "IsImportedCharacter": pal.IsImportedCharacter,
        "OwnerName": pal.OwnerName if owner_uid else None,
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


def _pal_brief(pal: PalEntity) -> dict:
    return {
        "CharacterID": pal.CharacterID,
        "IconKey": DataProvider.get_pal_icon_key(pal.CharacterID),
        "DisplayName": pal.DisplayName,
        "NickName": pal.NickName or "",
        "Gender": pal.Gender.value if pal.Gender else None,
        "Level": pal.Level or 1,
        "Exp": pal.Exp or 0,
        "Rank": pal.Rank or 1,
        "FriendshipLevel": pal.FriendshipLevel or 0,
        "FavoriteIndex": pal.FavoriteIndex,
        "IsBOSS": pal.IsBOSS,
        "IsRarePal": bool(pal.IsRarePal),
        "IsAwakening": pal.IsAwakening,
        "IsImportedCharacter": pal.IsImportedCharacter,
        "Talent_HP": pal.Talent_HP or 0,
        "Talent_Melee": pal.Talent_Melee or 0,
        "Talent_Shot": pal.Talent_Shot or 0,
        "Talent_Defense": pal.Talent_Defense or 0,
        "Rank_HP": pal.Rank_HP or 0,
        "Rank_Attack": pal.Rank_Attack or 0,
        "Rank_Defence": pal.Rank_Defence or 0,
        "Rank_CraftSpeed": pal.Rank_CraftSpeed or 0,
        "ComputedMaxHP": pal.ComputedMaxHP,
        "ComputedAttack": pal.ComputedAttack,
        "ComputedDefense": pal.ComputedDefense,
        "ComputedCraftSpeed": pal.ComputedCraftSpeed,
        "Suitabilities": pal.WorkSuitabilities or {},
        "EquipWaza": pal.EquipWaza or [],
        "PassiveSkillList": pal.PassiveSkillList or [],
    }


def _brief_field_changes(incoming: PalEntity, existing: PalEntity) -> dict:
    incoming_data = _pal_brief(incoming)
    existing_data = _pal_brief(existing)
    return {
        key: {"Incoming": value, "Existing": existing_data.get(key)}
        for key, value in incoming_data.items()
        if value != existing_data.get(key)
    }


def _record_location(manager: SaveManager, record) -> dict:
    location = manager.resolve_record_location(record)
    return {
        "RecordKey": record.record_key,
        "StorageKey": record.storage_key,
        "StorageKind": record.storage_kind,
        "StorageOwnerPlayerUid": record.storage_owner_uid,
        "InstanceId": str(record.pal.InstanceId),
        "OwnerPlayerUId": _guid_string_or_none(record.pal.OwnerPlayerUId),
        "ContainerLabel": location["ContainerLabel"],
        "ActualSlotIndex": location["ActualSlotIndex"],
        "LocationStatus": location["LocationStatus"],
    }


def _guid_string_or_none(value) -> str | None:
    if value is None:
        return None
    text = str(value)
    if getattr(value, "int", None) == 0 or not text.replace("-", "").strip("0"):
        return None
    return text


@pal_blueprint.route("/dump_data", methods=["POST"])
@jwt_required()
def dump_data():
    try:
        record = _selected_record(request.json or {})
    except ValueError as error:
        return reply(1, None, str(error))
    if record:
        return reply(0, record.pal.dump_obj())
    return reply(1, None, "Selected Pal not found.")


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
    roster_key = payload.get("RosterKey")
    target_storage_key = payload.get("TargetStorageKey")
    target_container_id = payload.get("TargetContainerId")
    if PlayerUId == "PAL_BASE_WORKER_BTN" and not target_container_id:
        LOGGER.warning("Directly add pal to basecamp is not yet supported.")
        return reply(1, None, "Choose a base container before adding a Pal.")
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

        if roster_key or target_storage_key:
            if not roster_key or not target_storage_key:
                return reply(
                    1,
                    None,
                    "RosterKey and TargetStorageKey are required.",
                )
            record = SaveManager().create_pal(
                roster_key, target_storage_key, pal_obj
            )
            pal_entity = record.pal
        else:
            record = None
            pal_entity = (
                SaveManager().add_pal(PlayerUId, pal_obj, target_container_id)
                if target_container_id
                else SaveManager().add_pal(PlayerUId, pal_obj)
            )
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
    data = _pal_data(pal_entity)
    if record is not None:
        data.update(
            {
                "RecordKey": record.record_key,
                "StorageKey": record.storage_key,
                "StorageKind": record.storage_kind,
            }
        )
    return reply(0, data)


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

    try:
        record = _selected_record(payload)
    except ValueError as error:
        return reply(1, None, str(error))
    if record is None:
        return reply(1, None, "Selected Pal not found.")
    pal = record.pal

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

    try:
        record = _selected_record(payload)
    except ValueError as error:
        return reply(1, None, str(error))
    if record is None:
        return reply(1, None, "Selected Pal not found.")
    pal = record.pal

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
    try:
        record = _selected_record(request.json or {})
        if record is None:
            return reply(1, None, "Selected Pal not found.")
        pal = record.pal
        _replace_skill_group(pal, template)
        SaveManager().normalize_external_record(record)
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
    payload = request.json or {}
    PlayerUId = payload.get("PlayerUId")
    if PlayerUId == "PAL_BASE_WORKER_BTN":
        LOGGER.warning("Directly add pal to basecamp is not yet supported.")
        return reply(1, None, f"Directly adding pal to basecamp is not yet supported.")
    try:
        record = SaveManager().duplicate_pal(payload.get("RecordKey"), PlayerUId)
    except ValueError as error:
        LOGGER.warning(
            "Failed duplicating Pal: "
            f"record={payload.get('RecordKey')} roster={PlayerUId} error={error}"
        )
        return reply(1, None, str(error))
    except Exception:
        LOGGER.error(
            "Failed duplicating Pal: "
            f"record={payload.get('RecordKey')} roster={PlayerUId}\n"
            f"{traceback.format_exc()}"
        )
        return reply(1, None, "Failed duplicating Pal. Check logs for details.")
    return reply(0, _pal_data(record.pal, record))
