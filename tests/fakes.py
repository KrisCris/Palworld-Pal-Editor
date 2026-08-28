"""Shared stand-ins for tests that exercise API routes without a loaded save.

The routes ask SaveManager where a Pal physically is; a test that never opens a
save has to answer that question itself rather than have the route guess.
"""

from unittest.mock import patch

from palworld_pal_editor.api.pal import _pal_data
from palworld_pal_editor.core.pal_entity import PalEntity
from palworld_pal_editor.core.pal_record import PalRecord
from palworld_pal_editor.core.save_manager import SaveManager


def world_record(
    pal: PalEntity,
    *,
    storage_key: str | None = "world-container:test",
    slot_index: int | None = 0,
) -> PalRecord:
    """A World PalRecord shaped exactly like the one SaveManager registers."""
    return SaveManager._world_record(
        pal,
        storage_key=storage_key,
        slot_index=slot_index,
        storage_owner_uid=None,
    )


def record_location(record: PalRecord, *, container_kind: str = "world") -> dict:
    """The location a loaded session would report for a Pal that sits where it says."""
    container_id = str(record.pal.ContainerId) if record.pal.ContainerId else None
    slot_index = record.pal.SlotIndex
    return {
        "RecordedContainerId": container_id,
        "RecordedSlotIndex": slot_index,
        "ActualContainerId": container_id,
        "ActualSlotIndex": slot_index,
        "ActualLocations": [],
        "LocationStatus": "ok",
        "LocationAnomaly": None,
        "ContainerKind": container_kind,
        "ContainerLabel": None,
    }


class LocationManager:
    """Answers only the location questions the Pal DTO builder asks."""

    def resolve_record_location(self, record: PalRecord) -> dict:
        return record_location(record)

    def resolve_pal_location(self, pal: PalEntity) -> dict:
        return record_location(world_record(pal))

    def get_player(self, _player_uid):
        return None


def pal_payload(pal: PalEntity) -> dict:
    """The Pal detail DTO for a Pal that is not part of a loaded session."""
    with patch(
        "palworld_pal_editor.api.pal.SaveManager", return_value=LocationManager()
    ):
        return _pal_data(pal)
