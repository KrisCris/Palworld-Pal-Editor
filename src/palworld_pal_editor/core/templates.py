"""Where saved templates live, and the one-time upgrade of the old Pal ones.

A Pal template is a name and a Pal, and the Pal is the same native DOM the export
route hands out -- stored as an object, not as JSON encoded a second time into a
string. Reading one back is the same strict recognition an import gets, so there is
one way for a Pal to enter this editor from outside a save.

Skill templates are lists of skill ids and have never been anything else.
"""

import json
import traceback

from palworld_pal_editor.config import Config
from palworld_pal_editor.core.pal_import import DetachedPalSource, detach_native_record
from palworld_pal_editor.utils import LOGGER


def pal_templates() -> list[dict]:
    """The saved Pal templates, as a list this session can append to and reorder."""
    if not isinstance(Config.palTemplates, list):
        Config.palTemplates = []
    return Config.palTemplates


def skill_templates() -> list[dict]:
    if not isinstance(Config.skillTemplates, list):
        Config.skillTemplates = []
    return Config.skillTemplates


def template_source(template: dict) -> DetachedPalSource:
    """The Pal a saved template describes.

    A template whose upgrade failed still holds its original string, so this reads
    both shapes -- one `json.loads` and then the same recognizer either way, rather
    than a second template format with its own rules.
    """
    pal_data = template.get("PalData")
    if isinstance(pal_data, str):
        pal_data = json.loads(pal_data)
    return detach_native_record(pal_data)


def migrate_pal_templates() -> None:
    """Upgrade saved Pal templates to the native DOM, once, at startup.

    Recognition by shape only: an entry whose `PalData` is a string is old, an entry
    whose `PalData` is an object is current, and neither gains a format or version
    marker. The work happens on a copy and is written with one atomic
    `Config.save_to_file()`; a failed write puts the old list back and lets the
    exception reach the startup log, because a half-upgraded template file is worse
    than an un-upgraded one.
    """
    templates = pal_templates()
    upgraded = list(templates)
    converted = 0
    for index, template in enumerate(upgraded):
        if not isinstance(template, dict):
            continue
        # Templates saved by <= 1.0.x stored PalData as a JSON string; 1.1+ stores
        # the native GVAS DOM. This branch upgrades persisted user templates in
        # place. Users may skip multiple major releases, so do not remove it after
        # only one or two releases. TODO(3.0+): remove only when direct upgrades
        # from 1.0.x are no longer supported. Without this branch stale strings
        # remain preserved but are not loadable; removing it must never delete or
        # overwrite those entries.
        if not isinstance(template.get("PalData"), str):
            continue
        try:
            native_record = json.loads(template["PalData"])
            detach_native_record(native_record)
        except Exception:
            LOGGER.warning(
                "Keeping an unreadable Pal template exactly as it was: "
                f"name={template.get('Name')!r} id={template.get('Id')!r}\n"
                f"{traceback.format_exc()}"
            )
            continue
        upgraded[index] = {**template, "PalData": native_record}
        converted += 1

    if not converted:
        return
    previous = list(templates)
    templates[:] = upgraded
    try:
        Config.save_to_file()
    except Exception:
        templates[:] = previous
        raise
    LOGGER.info(f"Upgraded {converted} saved Pal template(s) to the native format.")
