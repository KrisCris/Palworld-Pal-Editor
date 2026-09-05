"""Where saved templates live, and the one-time upgrade of the old Pal ones.

A Pal template is a name and a Pal, and the Pal is the same native DOM the export
route hands out -- stored as an object, not as JSON encoded a second time into a
string. Reading one back is the same strict recognition an import gets, so there is
one way for a Pal to enter this editor from outside a save.

Skill templates are lists of skill ids and have never been anything else.

Both kinds live in one file of their own under the user data directory. They used
to sit inside `config.json`, which meant changing the interface language rewrote
every saved Pal: they are user data rather than configuration, and a Pal template
carries a whole GVAS payload.
"""

import json
import traceback

from palworld_pal_editor.config import TEMPLATES_PATH, write_json
from palworld_pal_editor.core.pal_import import DetachedPalSource, detach_native_record
from palworld_pal_editor.utils import LOGGER


_store: dict[str, list[dict]] = None


def _templates() -> dict[str, list[dict]]:
    """The template file, read once per run and then held as the live lists.

    An unreadable file is reported and treated as empty rather than raised: a user
    can edit this one by hand, and refusing to start over it would take the rest of
    the editor down with it. Nothing overwrites the file until a template is saved.
    """
    global _store
    if _store is None:
        _store = {"pal": [], "skill": []}
        if TEMPLATES_PATH.exists():
            try:
                data = json.loads(TEMPLATES_PATH.read_text(encoding="utf-8"))
                _store["pal"] = data.get("pal") or []
                _store["skill"] = data.get("skill") or []
            except Exception:
                LOGGER.warning(
                    f"Unable to read saved templates from {TEMPLATES_PATH}, "
                    f"starting with none:\n{traceback.format_exc()}"
                )
    return _store


def pal_templates() -> list[dict]:
    """The saved Pal templates, as a list this session can append to and reorder."""
    return _templates()["pal"]


def skill_templates() -> list[dict]:
    return _templates()["skill"]


def save_templates() -> None:
    """Write both template lists out as one file."""
    write_json(TEMPLATES_PATH, _templates())


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
    `save_templates()`; a failed write puts the old list back and lets the exception
    reach the startup log, because a half-upgraded template file is worse than an
    un-upgraded one.
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
        save_templates()
    except Exception:
        templates[:] = previous
        raise
    LOGGER.info(f"Upgraded {converted} saved Pal template(s) to the native format.")
