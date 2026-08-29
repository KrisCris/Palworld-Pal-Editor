"""Shared stand-ins for tests that exercise API routes without a loaded save.

The routes ask SaveManager where a Pal physically is; a test that never opens a
save has to answer that question itself rather than have the route guess.
"""

from unittest.mock import patch

from palworld_pal_editor.api.pal import _pal_data
from palworld_pal_editor.core.pal_entity import PalEntity
from palworld_pal_editor.core.pal_record import PalRecord
from palworld_pal_editor.core.pal_repository import PalRepository
from palworld_pal_editor.core.pal_storage_adapters import WorldPalAdapter


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


def record_location(record: PalRecord, *, container_kind: str = "world") -> dict:
    """The location a loaded session would report for a record that sits where it says."""
    return {
        "ContainerId": str(record.pal.ContainerId) if record.pal.ContainerId else None,
        "SlotIndex": record.slot_index,
        "ContainerKind": container_kind,
        "ContainerLabel": None,
        "StorageKey": record.storage_key,
        "StorageKind": record.storage_kind,
    }


class LocationManager:
    """Answers only the location and created-state questions the Pal DTO asks."""

    def __init__(self, *, created: PalRecord | None = None) -> None:
        # Empty unless a test says otherwise: a Pal outside a loaded session was not
        # created in one, so `is_created` answers False with no special case in the DTO.
        self.pal_repository = PalRepository()
        if created is not None:
            self.pal_repository.register(created, created=True)

    def resolve_record_location(self, record: PalRecord) -> dict:
        return record_location(record)

    def get_player(self, _player_uid):
        return None


def pal_payload(
    pal: PalEntity,
    *,
    record: PalRecord | None = None,
    created: bool = False,
) -> dict:
    """The Pal detail DTO for a Pal that is not part of a loaded session."""
    manager = LocationManager(created=record if created else None)
    with patch("palworld_pal_editor.api.pal.SaveManager", return_value=manager):
        return _pal_data(pal, record)
