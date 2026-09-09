"""Shared stand-ins for tests that exercise API routes without a loaded save.

The routes ask SaveManager where a Pal physically is; a test that never opens a
save has to answer that question itself rather than have the route guess.
"""

from palworld_pal_editor.api.pal_serializers import pal_detail
from palworld_pal_editor.core.pal_entity import PalEntity
from palworld_pal_editor.core.pal_record import PalRecord
from palworld_pal_editor.core.pal_repository import PalRepository
from palworld_pal_editor.core.pal_storage_adapters import WorldPalAdapter
from palworld_pal_editor.core.storage_directory import RecordLocation


def world_pal(pal_obj: dict) -> PalEntity:
    """A PalEntity bound to a World record, the way the load path binds one."""
    return WorldPalAdapter.entity(pal_obj)


def world_record(
    pal_obj: dict,
    *,
    storage_key: str | None = "world-container:test",
    slot_index: int | None = 0,
    pal: PalEntity | None = None,
) -> PalRecord:
    """A World PalRecord shaped exactly like the one SaveManager registers."""
    return WorldPalAdapter.record(
        pal_obj,
        storage_key=storage_key,
        slot_index=slot_index,
        storage_owner_uid=None,
        pal=pal,
    )


def record_location(record: PalRecord, *, storage_role: str = "world") -> RecordLocation:
    """The location a loaded session would report for a record that sits where it says."""
    return RecordLocation(
        ContainerId=str(record.pal.ContainerId) if record.pal.ContainerId else None,
        SlotIndex=record.slot_index,
        storage_key=record.storage_key,
        storage_kind=record.storage_kind,
        storage_role=storage_role,
        storage_label=None,
    )


class FakeStorageDirectory:
    """The one question `api/` asks the directory about a Pal outside a session."""

    def resolve_record_location(self, record: PalRecord) -> RecordLocation:
        return record_location(record)


class LocationManager:
    """Answers only the location and created-state questions the Pal DTO asks."""

    def __init__(self, *, created: PalRecord | None = None) -> None:
        # Empty unless a test says otherwise: a Pal outside a loaded session was not
        # created in one, so `is_created` answers False with no special case in the DTO.
        self.pal_repository = PalRepository()
        if created is not None:
            self.pal_repository.register(created, created=True)
        self.storage_directory = FakeStorageDirectory()

    def get_player(self, _player_uid):
        return None


def pal_payload(record: PalRecord, *, created: bool = False) -> dict:
    """The Pal detail DTO for a Pal that is not part of a loaded session.

    A record, not an entity: the DTO answers where a Pal is as well as what it
    is, and a Pal with nowhere to be was only ever a shape the old route had to
    tolerate.
    """
    return pal_detail(LocationManager(created=record if created else None), record)
