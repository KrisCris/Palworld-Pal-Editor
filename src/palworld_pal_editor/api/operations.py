"""What every Pal-changing route owes the session, in one place.

Four helpers, and each exists because a route that forgot it would fail quietly:
`require_record` and `require_pal_template` turn a missing key into the same 404
rather than an `AttributeError` further in, `operation_result` gives every
mutation one response shape so the client never guesses what an operation did,
and `commit_pal_edit` writes an external Pal back and marks the change set.

`require_pal_template` is here rather than in `templates.py` so that `storages.py`
does not have to import from a sibling route module to create a Pal from one.

Shared by `pals.py`, `pal_heals.py`, `pal_transfers.py`, `rosters.py` and
`templates.py` -- which is why it is here rather than in any one of them.
"""

from palworld_pal_editor.api.errors import ApiError
from palworld_pal_editor.api.pal_serializers import pal_detail
from palworld_pal_editor.core import SaveManager
from palworld_pal_editor.core.pal_record import PalRecord
from palworld_pal_editor.core.templates import pal_templates


def require_record(record_key: str) -> PalRecord:
    """The record that key names, or the 404 every Pal sub-resource would repeat."""
    record = SaveManager().get_record(record_key)
    if record is None:
        raise ApiError(
            "PAL_NOT_FOUND",
            f"No Pal record named {record_key}",
            status=404,
        )
    return record


def operation_result(
    manager: SaveManager,
    record: PalRecord | None = None,
    *,
    affected_roster_keys=(),
    deleted_record_keys=(),
    affected_storage_keys=(),
) -> dict:
    """The one shape every Pal-changing response uses.

    All four keys are always present, so the client reads one shape and never has
    to guess what an operation did. A delete says what is gone, a create says which
    storage now holds one more Pal, and a move fills both at once.
    """
    return {
        "resultRecord": pal_detail(manager, record) if record is not None else None,
        "deletedRecordKeys": list(deleted_record_keys),
        "affectedRosterKeys": list(affected_roster_keys),
        "affectedStorageKeys": list(affected_storage_keys),
    }


def commit_pal_edit(manager: SaveManager, record: PalRecord) -> dict:
    """What every successful single-Pal edit owes the session, in one place.

    A Global Palbox or DPS Pal is a copy that has to be written back before the
    session is saved, and a changed Pal is one the change-set marks have to know
    about. Forgetting either is silent, which is why no route does it by hand.
    """
    manager.pal_mutations.normalize_external_record(record)
    manager.pal_repository.mark_modified(record)
    return operation_result(manager, record)


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
