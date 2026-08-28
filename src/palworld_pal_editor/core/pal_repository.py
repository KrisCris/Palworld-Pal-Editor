from typing import Optional

from palworld_save_tools.archive import UUID

from palworld_pal_editor.core.pal_record import PalRecord
from palworld_pal_editor.utils import LOGGER


class PalRepository:
    """The single runtime authority for every physical Pal record in the session.

    The secondary indexes map to record keys only; ``_records`` holds the one copy of
    each ``PalRecord`` and every index can be rebuilt from it.
    """

    def __init__(self) -> None:
        self._records: dict[str, PalRecord] = {}
        self._by_owner: dict[str, set[str]] = {}
        self._by_storage: dict[str, dict[int, str]] = {}
        self._by_instance: dict[str, set[str]] = {}

    def __len__(self) -> int:
        return len(self._records)

    def __contains__(self, record_key: object) -> bool:
        return str(record_key) in self._records

    # --- registration -----------------------------------------------------

    def register(self, record: PalRecord) -> PalRecord:
        if record.record_key in self._records:
            raise ValueError(f"Duplicated Pal RecordKey: {record.record_key}")
        self._records[record.record_key] = record
        self._index(record)
        return record

    def unregister(self, record: PalRecord | str) -> Optional[PalRecord]:
        record_key = record if isinstance(record, str) else record.record_key
        removed = self._records.pop(record_key, None)
        if removed is not None:
            self.reindex()
        return removed

    def snapshot_records(self) -> dict[str, PalRecord]:
        """A shallow copy of the record set, for rolling a failed mutation back."""
        return dict(self._records)

    def replace_records(self, records: dict[str, PalRecord]) -> None:
        """Restore the whole record set, e.g. when rolling a failed mutation back."""
        self._records = records
        self.reindex()

    def reindex(self) -> None:
        """Rebuild every secondary index from ``_records``.

        Owner and instance id live on the Pal and can change under an edit, so the
        indexes are rebuilt rather than patched whenever a record leaves or moves.
        """
        self._by_owner = {}
        self._by_storage = {}
        self._by_instance = {}
        for record in self._records.values():
            self._index(record)

    def _index(self, record: PalRecord) -> None:
        owner = record.pal.OwnerPlayerUId
        if owner:
            self._by_owner.setdefault(str(owner), set()).add(record.record_key)

        instance_id = record.pal.InstanceId
        if instance_id:
            self._by_instance.setdefault(str(instance_id), set()).add(
                record.record_key
            )

        if record.storage_key is None or record.slot_index is None:
            return
        slots = self._by_storage.setdefault(record.storage_key, {})
        occupant = slots.get(record.slot_index)
        if occupant is not None and occupant != record.record_key:
            LOGGER.error(
                f"Duplicated storage slot {record.storage_key}[{record.slot_index}]: "
                f"{occupant} already holds it, refusing to index {record.record_key}"
            )
            return
        slots[record.slot_index] = record.record_key

    # --- queries ----------------------------------------------------------

    def get(self, record_key: str) -> Optional[PalRecord]:
        return self._records.get(str(record_key))

    def records(self) -> list[PalRecord]:
        return list(self._records.values())

    def records_for_owner(self, player_uid: UUID | str) -> list[PalRecord]:
        return self._lookup(self._by_owner.get(str(player_uid)))

    def records_by_instance(self, instance_id: UUID | str) -> list[PalRecord]:
        return self._lookup(self._by_instance.get(str(instance_id)))

    def records_for_storage(self, storage_key: str) -> list[PalRecord]:
        slots = self._by_storage.get(str(storage_key), {})
        return [self._records[slots[index]] for index in sorted(slots)]

    def _lookup(self, record_keys: Optional[set[str]]) -> list[PalRecord]:
        if not record_keys:
            return []
        return [self._records[key] for key in sorted(record_keys)]
