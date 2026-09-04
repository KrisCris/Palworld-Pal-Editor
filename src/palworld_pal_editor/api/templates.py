"""Saved Pal and skill templates.

A Pal template is a name and one native Pal record -- the same DOM
`GET /api/pals/{recordKey}/native-record` hands out, stored as an object rather
than as JSON encoded a second time into a string. Reading one back is the same
strict recognition an import gets, so a Pal enters this editor from outside a save
by exactly one road.

A skill template is a list of skill ids. Applying one replaces the whole group,
which is why it answers with an operation result like every other Pal write: the
Pal that comes back is the new authority for it.

Templates live in `Config`, so every write here is followed by one
`Config.save_to_file()` and undone in memory if that write fails. The stored
entries keep their own `Id`/`Name`/`Type` spelling because they are persisted user
data; what this module chooses is only what the API says.
"""

import uuid

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from palworld_pal_editor.api.errors import ApiError, register_error_handlers
from palworld_pal_editor.api.pals import (
    SKILL_GROUPS,
    commit_pal_edit,
    native_record,
    require_record,
)
from palworld_pal_editor.config import Config
from palworld_pal_editor.core import SaveManager
from palworld_pal_editor.core.pal_templates import (
    pal_templates,
    skill_templates,
    template_source,
)
from palworld_pal_editor.utils import LOGGER, DataProvider

templates_blueprint = Blueprint("templates", __name__)
register_error_handlers(templates_blueprint)

MAX_TEMPLATE_COUNT = 50
MAX_TEMPLATE_NAME_LENGTH = 64

# What each kind of skill template stores, and which of a Pal's three skill groups
# applying it replaces. `active` is the UI's word for the equipped list, kept
# because it is already written into every template saved so far.
SKILL_TEMPLATE_GROUPS = {
    "passive": ("PassiveSkillList", "passive"),
    "active": ("EquipWaza", "equipped"),
}


def _stored_name(payload) -> str:
    if not isinstance(payload, dict):
        raise ApiError("TEMPLATE_INVALID", "Request body must be an object")
    name = payload.get("name")
    if not isinstance(name, str) or not (name := name.strip()):
        raise ApiError("TEMPLATE_NAME_REQUIRED", "A template name is required")
    if len(name) > MAX_TEMPLATE_NAME_LENGTH:
        raise ApiError(
            "TEMPLATE_NAME_TOO_LONG",
            f"A template name is at most {MAX_TEMPLATE_NAME_LENGTH} characters",
        )
    return name


def _commit(undo) -> None:
    """Persist the template list, or put it back the way it was.

    Templates are the one thing this API stores outside the save file, so every
    write is followed by one `Config.save_to_file()`. A failed write leaves the
    file as it was, which makes the in-memory list the only thing out of step.
    """
    try:
        Config.save_to_file()
    except Exception:
        undo()
        raise


def pal_template_resource(template: dict) -> dict:
    """One saved Pal template, read through the same recognizer an import uses."""
    pal = template_source(template).entity()
    return {
        "templateId": template["Id"],
        "name": template["Name"],
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


def skill_template_resource(template: dict) -> dict:
    field, _ = SKILL_TEMPLATE_GROUPS[template["Type"]]
    return {
        "templateId": template["Id"],
        "name": template["Name"],
        "type": template["Type"],
        field: list(template.get(field) or []),
    }


def require_pal_template(template_id) -> dict:
    """The saved Pal template that id names, or the 404 its two readers would share."""
    template = next(
        (item for item in pal_templates() if item.get("Id") == template_id),
        None,
    )
    if template is None:
        raise ApiError(
            "PAL_TEMPLATE_NOT_FOUND",
            f"No Pal template named {template_id}",
            status=404,
        )
    return template


def _require_skill_template(template_id) -> dict:
    template = next(
        (
            item
            for item in skill_templates()
            if item.get("Id") == template_id
            and item.get("Type") in SKILL_TEMPLATE_GROUPS
        ),
        None,
    )
    if template is None:
        raise ApiError(
            "SKILL_TEMPLATE_NOT_FOUND",
            f"No skill template named {template_id}",
            status=404,
        )
    return template


@templates_blueprint.route("/pal-templates", methods=["GET"])
@jwt_required()
def list_pal_templates():
    """Every readable saved Pal.

    A template the recognizer refuses is skipped rather than failing the listing:
    it is user data the migration deliberately preserved, and hiding one bad
    entry is better than showing none.
    """
    resources = []
    for template in pal_templates():
        try:
            resources.append(pal_template_resource(template))
        except Exception:
            template_id = template.get("Id") if isinstance(template, dict) else None
            LOGGER.warning(f"Ignoring unreadable Pal template {template_id}")
    return resources


@templates_blueprint.route("/pal-templates", methods=["POST"])
@jwt_required()
def create_pal_template():
    payload = request.get_json(silent=True)
    name = _stored_name(payload)
    templates = pal_templates()
    if len(templates) >= MAX_TEMPLATE_COUNT:
        raise ApiError(
            "TEMPLATE_LIMIT_REACHED",
            f"At most {MAX_TEMPLATE_COUNT} Pal templates can be saved",
        )

    manager = SaveManager()
    with manager.session_lock:
        record = require_record(payload.get("recordKey"))
        template = {
            "Id": uuid.uuid4().hex,
            "Name": name,
            "PalData": native_record(manager, record),
        }
        try:
            resource = pal_template_resource(template)
        except Exception as error:
            # The template is read back through the recognizer before it is kept,
            # so an entry nothing could ever be created from is never written.
            raise ApiError("PAL_TEMPLATE_UNREADABLE", str(error))

    templates.append(template)
    _commit(lambda: templates.remove(template))
    return resource


@templates_blueprint.route("/pal-templates/<template_id>", methods=["DELETE"])
@jwt_required()
def delete_pal_template(template_id: str):
    templates = pal_templates()
    template = require_pal_template(template_id)
    index = templates.index(template)
    templates.pop(index)
    _commit(lambda: templates.insert(index, template))
    return "", 204


@templates_blueprint.route("/skill-templates", methods=["GET"])
@jwt_required()
def list_skill_templates():
    return [
        skill_template_resource(template)
        for template in skill_templates()
        if isinstance(template, dict) and template.get("Type") in SKILL_TEMPLATE_GROUPS
    ]


@templates_blueprint.route("/skill-templates", methods=["POST"])
@jwt_required()
def create_skill_template():
    payload = request.get_json(silent=True)
    name = _stored_name(payload)
    template_type = payload.get("type")
    if template_type not in SKILL_TEMPLATE_GROUPS:
        raise ApiError(
            "SKILL_TEMPLATE_TYPE_UNKNOWN",
            "A skill template is passive or active",
            details={"types": sorted(SKILL_TEMPLATE_GROUPS)},
        )
    templates = skill_templates()
    if len(templates) >= MAX_TEMPLATE_COUNT:
        raise ApiError(
            "TEMPLATE_LIMIT_REACHED",
            f"At most {MAX_TEMPLATE_COUNT} skill templates can be saved",
        )

    field, _ = SKILL_TEMPLATE_GROUPS[template_type]
    manager = SaveManager()
    with manager.session_lock:
        record = require_record(payload.get("recordKey"))
        template = {
            "Id": uuid.uuid4().hex,
            "Name": name,
            "Type": template_type,
            field: list(getattr(record.pal, field) or []),
        }

    templates.append(template)
    _commit(lambda: templates.remove(template))
    return skill_template_resource(template)


@templates_blueprint.route("/skill-templates/<template_id>", methods=["PATCH"])
@jwt_required()
def rename_skill_template(template_id: str):
    name = _stored_name(request.get_json(silent=True))
    template = _require_skill_template(template_id)
    previous = template["Name"]
    template["Name"] = name
    _commit(lambda: template.__setitem__("Name", previous))
    return skill_template_resource(template)


@templates_blueprint.route("/skill-templates/<template_id>", methods=["DELETE"])
@jwt_required()
def delete_skill_template(template_id: str):
    templates = skill_templates()
    template = _require_skill_template(template_id)
    index = templates.index(template)
    templates.pop(index)
    _commit(lambda: templates.insert(index, template))
    return "", 204


@templates_blueprint.route(
    "/pals/<record_key>/skill-template-applications", methods=["POST"]
)
@jwt_required()
def apply_skill_template(record_key: str):
    """Replace one of a Pal's skill groups with a saved one.

    The catalog check and the entity method both come from `pals.SKILL_GROUPS`, so
    a template applies through exactly the code path `PUT .../skills/{group}` uses
    -- including that equipping a skill also learns it. A template saved before a
    game update can name a skill this build has no data for, which is why the list
    is checked on the way in and not only when it was saved.
    """
    payload = request.get_json(silent=True)
    template_id = payload.get("templateId") if isinstance(payload, dict) else None
    template = _require_skill_template(template_id)
    field, group = SKILL_TEMPLATE_GROUPS[template["Type"]]
    skills = list(template.get(field) or [])

    is_known, replace = SKILL_GROUPS[group]
    unknown = [
        skill for skill in skills if not isinstance(skill, str) or not is_known(skill)
    ]
    if unknown:
        raise ApiError(
            "SKILL_UNKNOWN",
            "This template names skills the game does not have: "
            f"{', '.join(map(str, unknown))}",
        )

    manager = SaveManager()
    with manager.session_lock:
        record = require_record(record_key)
        replace(record.pal, skills)
        return commit_pal_edit(manager, record)
