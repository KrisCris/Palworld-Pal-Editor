import copy
from typing import Optional

from palworld_save_tools.archive import UUID

from palworld_pal_editor.core.pal_entity import PalEntity
from palworld_pal_editor.core.pal_objects import (
    CHARACTER_PARAMETER_STRUCT,
    json_native,
)
from palworld_pal_editor.core.pal_record import PalRecord
from palworld_pal_editor.core.pal_storage import ENTRY_TYPE_NAME, PalStorageSaveFile


class StoragePalAdapter:
    """Reads and writes the Pals in one PalStorage save file — a DPS or the GPS.

    ``PalStorageSaveFile`` owns the file and the slot array; this owns what a slot
    *means* — the record key grammar, the two parent dicts a ``PalEntity`` binds to,
    and the ``PalRecord`` handed to the repository. DPS and GPS share that layout
    entirely; only the key grammar differs, which is what the subclasses carry.
    """

    kind: str
    # The one field that tells a DPS export and a GPS export apart.
    entry_type_name: str

    def __init__(self, storage: PalStorageSaveFile) -> None:
        self.storage = storage

    @property
    def storage_key(self) -> str:
        return self.storage.storage_key

    def record_key(self, slot_index: int) -> str:
        return f"{self._key_prefix}{slot_index}"

    @property
    def _key_prefix(self) -> str:
        raise NotImplementedError

    @classmethod
    def detach(cls, native_property) -> Optional[dict]:
        """The SaveParameter in a one-entry SaveParameterArray of this format.

        A DPS export and a GPS export are the same shape apart from `type_name`, so
        the name and the entry count are both load-bearing: without them
        an import would be guessing which storage the record came out of.
        """
        if not isinstance(native_property, dict):
            return None
        if native_property.get("type") != "ArrayProperty":
            return None
        value = native_property.get("value")
        if not isinstance(value, dict):
            return None
        if value.get("type_name") != cls.entry_type_name:
            return None
        entries = value.get("values")
        if not isinstance(entries, list) or len(entries) != 1:
            return None
        entry = entries[0]
        parameter = entry.get("SaveParameter") if isinstance(entry, dict) else None
        if not isinstance(parameter, dict):
            return None
        if parameter.get("struct_type") != CHARACTER_PARAMETER_STRUCT:
            return None
        return copy.deepcopy(parameter)

    def export(self, record: PalRecord) -> dict:
        """This Pal as a one-entry SaveParameterArray, in JSON-native values.

        The property header is copied off the live array rather than written from
        memory. The header and the entry envelope are what say a record came from a
        DPS rather than the Global Palbox, and an export that flattened them to a
        bare parameter could not be told apart on the way back in.
        """
        array = self.storage.array_property
        return json_native(
            {
                **{key: value for key, value in array.items() if key != "value"},
                "value": {
                    **{
                        key: value
                        for key, value in array["value"].items()
                        if key != "values"
                    },
                    "values": [record.native_record],
                },
            }
        )

    @staticmethod
    def entity(entry: dict) -> PalEntity:
        """Bind a PalEntity to the two real parent dicts inside one array entry.

        The entry itself owns ``SaveParameter`` and its ``InstanceId`` value dict is
        the identity parent, so no World-shaped envelope is involved.
        """
        return PalEntity(entry["InstanceId"]["value"], entry)

    def records(self) -> list[PalRecord]:
        return [
            self._record(slot_index, entry)
            for slot_index, entry in enumerate(self.storage.entries)
            if self.storage.occupies(entry)
        ]

    def get(self, record_key: str) -> Optional[PalRecord]:
        slot_index = self.slot_index(record_key)
        if slot_index is None:
            return None
        entry = self.storage.entries[slot_index]
        if not self.storage.occupies(entry):
            return None
        return self._record(slot_index, entry)

    def slot_index(self, record_key: str) -> Optional[int]:
        """The slot this record key names, or None if the key is not ours."""
        if not record_key.startswith(self._key_prefix):
            return None
        try:
            slot_index = int(record_key.removeprefix(self._key_prefix))
            self.storage.entries[slot_index]
        except (IndexError, ValueError):
            return None
        return slot_index

    def allocate(
        self,
        save_parameter: dict,
        instance_id: UUID | str,
        player_uid: UUID | str | None = None,
    ) -> PalRecord:
        slot_index = self.storage.write_free_slot(
            save_parameter, instance_id, player_uid
        )
        return self._record(slot_index, self.storage.entries[slot_index])

    def clear(self, record_key: str) -> None:
        slot_index = self.slot_index(record_key)
        if slot_index is None or not self.storage.occupies(
            self.storage.entries[slot_index]
        ):
            raise KeyError(record_key)
        self.storage.clear_slot(slot_index)

    def _record(self, slot_index: int, entry: dict) -> PalRecord:
        return PalRecord(
            record_key=self.record_key(slot_index),
            storage_kind=self.kind,
            storage_key=self.storage_key,
            slot_index=slot_index,
            native_record=entry,
            pal=self.entity(entry),
            storage_owner_uid=self.storage.owner_uid,
        )


class DpsPalAdapter(StoragePalAdapter):
    """A single player's Dimension Pal Storage file."""

    kind = "dps"
    entry_type_name = ENTRY_TYPE_NAME["dps"]

    @property
    def _key_prefix(self) -> str:
        return f"dps:{self.storage.owner_uid}:"


class GpsPalAdapter(StoragePalAdapter):
    """The world's single Global Pal Storage file."""

    kind = "global_palbox"
    entry_type_name = ENTRY_TYPE_NAME["global_palbox"]

    @property
    def _key_prefix(self) -> str:
        return "gps:"
