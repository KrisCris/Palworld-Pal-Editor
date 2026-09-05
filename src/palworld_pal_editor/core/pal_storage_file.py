"""The two Pal storage formats that are a save file of their own.

A Dimensional Pal Storage (`<uid>_dps.sav`) and the Global Pal Storage
(`GlobalPalStorage.sav`) are whole `.sav` files whose payload is a single array of
fixed Pal slots -- unlike world Pals, which live inside Level.sav. Opening those
files, finding a free slot, clearing one and re-serializing the result is this
module; what an entry means is the adapters' business.

`ExternalStorageKind` names only those two. The canonical `StorageKind`, which
also covers Pals living inside Level.sav, is in `pal_record.py`.
"""

import copy
from pathlib import Path
from typing import Literal

from palworld_save_tools.archive import UUID
from palworld_save_tools.gvas import GvasFile
from palworld_save_tools.palsav import compress_gvas_to_sav, decompress_sav_to_gvas
from palworld_save_tools.paltypes import PALWORLD_TYPE_HINTS

from .pal_objects import PalObjects, toUUID
from .save_codec import PAL_STORAGE_CUSTOM_PROPERTIES


# The two formats that live in a `.sav` of their own. Deliberately not named
# `StorageKind`: that is `pal_record`'s three-value one, and a module that
# imported this believing it canonical could not describe a world Pal.
ExternalStorageKind = Literal["dps", "global_palbox"]

# What each format calls the entries in its SaveParameterArray. This is how a DPS
# record and a GPS record are told apart -- they are otherwise the same shape -- so
# the loader and the import recognizer have to be reading the same two strings.
ENTRY_TYPE_NAME = {
    "dps": "PalDimensionPalStorageSaveParameter",
    "global_palbox": "PalGlobalPalStorageSaveParameter",
}


class PalStorageSaveFile:
    """One DPS or GPS save file: its GVAS, its slot array, and its dirty flag.

    The game preallocates ``SaveParameterArray`` and never changes its length, so a
    slot is claimed and released in place rather than appended and removed — unlike
    the World save, where adding a Pal appends to ``CharacterSaveParameterMap`` and
    separately adds a slot to a ``PalContainer``.

    What a slot *means* — record keys, Pal binding, PalRecord — belongs to the
    matching adapter in ``pal_storage_adapters``; this class only reads and writes
    the array.
    """

    _EXPECTED_CLASS = {
        "dps": "/Script/Pal.PalDimensionPalStorageSaveGame",
        "global_palbox": "/Script/Pal.PalGlobalPalStorageSaveGame",
    }

    def __init__(
        self,
        path: Path,
        kind: ExternalStorageKind,
        owner_uid: UUID | str | None,
        gvas_file: GvasFile,
        save_type: int,
    ) -> None:
        self.path = path
        self.kind = kind
        self.owner_uid = str(toUUID(owner_uid)) if owner_uid is not None else None
        self.gvas_file = gvas_file
        self.save_type = save_type
        self.dirty = False

    @classmethod
    def open(
        cls,
        path: Path,
        kind: ExternalStorageKind,
        owner_uid: UUID | str | None = None,
    ) -> "PalStorageSaveFile":
        path = Path(path)
        raw_gvas, save_type = decompress_sav_to_gvas(path.read_bytes())
        gvas_file = GvasFile.read(
            raw_gvas,
            PALWORLD_TYPE_HINTS,
            PAL_STORAGE_CUSTOM_PROPERTIES,
        )
        if gvas_file.header.save_game_class_name != cls._EXPECTED_CLASS[kind]:
            raise ValueError(
                f"Unexpected {kind} save class: "
                f"{gvas_file.header.save_game_class_name}"
            )
        array = gvas_file.properties.get("SaveParameterArray")
        if not array or array.get("value", {}).get("type_name") != ENTRY_TYPE_NAME[kind]:
            raise ValueError(f"Unexpected {kind} SaveParameterArray")
        return cls(path, kind, owner_uid, gvas_file, save_type)

    @property
    def storage_key(self) -> str:
        if self.kind == "global_palbox":
            return "global-palbox"
        return f"dps:{self.owner_uid}"

    @property
    def slot_count(self) -> int:
        return len(self.entries)

    @property
    def occupied(self) -> int:
        return sum(self.occupies(entry) for entry in self.entries)

    @property
    def array_property(self) -> dict:
        """The whole native SaveParameterArray property, header included.

        Exporting one Pal means handing back a property of this exact shape holding
        a single entry, so the header is data to be copied rather than a constant an
        adapter can write from memory.
        """
        return self.gvas_file.properties["SaveParameterArray"]

    @property
    def entries(self) -> list[dict]:
        return self.array_property["value"]["values"]

    def free_index(self) -> int:
        for slot_index, entry in enumerate(self.entries):
            if not self.occupies(entry):
                return slot_index
        return -1

    def write_free_slot(
        self,
        save_parameter: dict,
        instance_id: UUID | str,
        player_uid: UUID | str | None = None,
    ) -> int:
        slot_index = self.free_index()
        if slot_index < 0:
            raise ValueError(f"{self.storage_key} is full")
        entry = self.entries[slot_index]
        entry.clear()
        entry["SaveParameter"] = copy.deepcopy(save_parameter)
        entry["InstanceId"] = self._instance_id(instance_id, player_uid)
        self.dirty = True
        return slot_index

    def clear_slot(self, slot_index: int) -> None:
        self.entries[slot_index]["InstanceId"] = self._instance_id(
            PalObjects.EMPTY_UUID,
            PalObjects.EMPTY_UUID,
        )
        self.dirty = True

    def serialize(self) -> bytes:
        raw_gvas = copy.deepcopy(self.gvas_file).write(PAL_STORAGE_CUSTOM_PROPERTIES)
        return compress_gvas_to_sav(raw_gvas, self.save_type)

    @staticmethod
    def occupies(entry: dict) -> bool:
        instance_id = PalObjects.get_BaseType(
            entry.get("InstanceId", {}).get("value", {}).get("InstanceId")
        )
        return instance_id is not None and instance_id != PalObjects.EMPTY_UUID

    @staticmethod
    def _instance_id(
        instance_id: UUID | str,
        player_uid: UUID | str | None,
    ) -> dict:
        return PalObjects.PalInstanceID(instance_id, player_uid)
