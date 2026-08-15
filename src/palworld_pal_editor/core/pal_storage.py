import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from palworld_save_tools.archive import UUID
from palworld_save_tools.gvas import GvasFile
from palworld_save_tools.palsav import compress_gvas_to_sav, decompress_sav_to_gvas
from palworld_save_tools.paltypes import PALWORLD_TYPE_HINTS

from .pal_entity import PalEntity
from .pal_objects import PalObjects, toUUID
from .save_codec import PAL_STORAGE_CUSTOM_PROPERTIES


StorageKind = Literal["dps", "global_palbox"]


@dataclass(slots=True)
class PalRecordRef:
    record_key: str
    storage_key: str
    storage_kind: Literal["world", "dps", "global_palbox"]
    slot_index: int
    pal: PalEntity
    storage_owner_uid: str | None = None
    external_record: dict | None = None


class FixedPalStorage:
    _EXPECTED_CLASS = {
        "dps": "/Script/Pal.PalDimensionPalStorageSaveGame",
        "global_palbox": "/Script/Pal.PalGlobalPalStorageSaveGame",
    }
    _EXPECTED_TYPE = {
        "dps": "PalDimensionPalStorageSaveParameter",
        "global_palbox": "PalGlobalPalStorageSaveParameter",
    }

    def __init__(
        self,
        path: Path,
        kind: StorageKind,
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
        kind: StorageKind,
        owner_uid: UUID | str | None = None,
    ) -> "FixedPalStorage":
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
        if not array or array.get("value", {}).get("type_name") != cls._EXPECTED_TYPE[kind]:
            raise ValueError(f"Unexpected {kind} SaveParameterArray")
        return cls(path, kind, owner_uid, gvas_file, save_type)

    @property
    def storage_key(self) -> str:
        if self.kind == "global_palbox":
            return "global-palbox"
        return f"dps:{self.owner_uid}"

    @property
    def capacity(self) -> int:
        return len(self._entries)

    @property
    def occupied(self) -> int:
        return sum(self._occupied(entry) for entry in self._entries)

    @property
    def _entries(self) -> list[dict]:
        return self.gvas_file.properties["SaveParameterArray"]["value"]["values"]

    def record_key(self, slot_index: int) -> str:
        if self.kind == "global_palbox":
            return f"gps:{slot_index}"
        return f"dps:{self.owner_uid}:{slot_index}"

    def records(self) -> list[PalRecordRef]:
        return [
            self._record(slot_index, entry)
            for slot_index, entry in enumerate(self._entries)
            if self._occupied(entry)
        ]

    def get(self, record_key: str) -> PalRecordRef | None:
        prefix = "gps:" if self.kind == "global_palbox" else f"dps:{self.owner_uid}:"
        if not record_key.startswith(prefix):
            return None
        try:
            slot_index = int(record_key.removeprefix(prefix))
            entry = self._entries[slot_index]
        except (IndexError, ValueError):
            return None
        if not self._occupied(entry):
            return None
        return self._record(slot_index, entry)

    def free_index(self) -> int:
        for slot_index, entry in enumerate(self._entries):
            if not self._occupied(entry):
                return slot_index
        return -1

    def allocate(
        self,
        save_parameter: dict,
        instance_id: UUID | str,
        player_uid: UUID | str | None = None,
    ) -> PalRecordRef:
        slot_index = self.free_index()
        if slot_index < 0:
            raise ValueError(f"{self.storage_key} is full")
        entry = self._entries[slot_index]
        entry.clear()
        entry["SaveParameter"] = copy.deepcopy(save_parameter)
        entry["InstanceId"] = self._instance_id(instance_id, player_uid)
        self.dirty = True
        return self._record(slot_index, entry)

    def clear(self, record_key: str) -> None:
        record = self.get(record_key)
        if record is None or record.external_record is None:
            raise KeyError(record_key)
        record.external_record["InstanceId"] = self._instance_id(
            PalObjects.EMPTY_UUID,
            PalObjects.EMPTY_UUID,
        )
        self.dirty = True

    def serialize(self) -> bytes:
        raw_gvas = copy.deepcopy(self.gvas_file).write(PAL_STORAGE_CUSTOM_PROPERTIES)
        return compress_gvas_to_sav(raw_gvas, self.save_type)

    def _record(self, slot_index: int, entry: dict) -> PalRecordRef:
        pal_obj = {
            "key": entry["InstanceId"]["value"],
            "value": {
                "RawData": {
                    "value": {
                        "group_id": PalObjects.EMPTY_UUID,
                        "object": {"SaveParameter": entry["SaveParameter"]},
                    }
                }
            },
        }
        return PalRecordRef(
            record_key=self.record_key(slot_index),
            storage_key=self.storage_key,
            storage_kind=self.kind,
            slot_index=slot_index,
            pal=PalEntity(pal_obj),
            storage_owner_uid=self.owner_uid,
            external_record=entry,
        )

    @staticmethod
    def _occupied(entry: dict) -> bool:
        instance_id = PalObjects.get_BaseType(
            entry.get("InstanceId", {}).get("value", {}).get("InstanceId")
        )
        return instance_id is not None and instance_id != PalObjects.EMPTY_UUID

    @staticmethod
    def _instance_id(
        instance_id: UUID | str,
        player_uid: UUID | str | None,
    ) -> dict:
        return {
            "struct_type": "PalInstanceID",
            "struct_id": PalObjects.EMPTY_UUID,
            "id": None,
            "value": {
                "PlayerUId": PalObjects.Guid(player_uid or PalObjects.EMPTY_UUID),
                "InstanceId": PalObjects.Guid(instance_id),
                "DebugName": PalObjects.StrProperty(""),
            },
            "type": "StructProperty",
        }
