import logging
import json
import uuid
import math
import copy
from pathlib import Path
from typing import Optional

from palworld_save_tools.gvas import GvasFile
from palworld_save_tools.archive import FArchiveReader, FArchiveWriter, UUID
from palworld_save_tools.json_tools import CustomEncoder
from palworld_save_tools.palsav import compress_gvas_to_sav, decompress_sav_to_gvas
from palworld_save_tools.paltypes import PALWORLD_CUSTOM_PROPERTIES, PALWORLD_TYPE_HINTS

from .utils import Logger

LOGGER = Logger()


def skip_decode(reader: FArchiveReader, type_name: str, size: int, path: str):
    if type_name == "ArrayProperty":
        array_type = reader.fstring()
        value = {
            "skip_type": type_name,
            "array_type": array_type,
            "id": reader.optional_guid(),
            "value": reader.read(size),
        }
    elif type_name == "MapProperty":
        key_type = reader.fstring()
        value_type = reader.fstring()
        _id = reader.optional_guid()
        value = {
            "skip_type": type_name,
            "key_type": key_type,
            "value_type": value_type,
            "id": _id,
            "value": reader.read(size),
        }
    elif type_name == "StructProperty":
        value = {
            "skip_type": type_name,
            "struct_type": reader.fstring(),
            "struct_id": reader.guid(),
            "id": reader.optional_guid(),
            "value": reader.read(size),
        }
    else:
        raise Exception(
            f"Expected ArrayProperty or MapProperty or StructProperty, got {type_name} in {path}"
        )
    return value


def skip_encode(writer: FArchiveWriter, property_type: str, properties: dict) -> int:
    if "skip_type" not in properties:
        if properties["custom_type"] in PALWORLD_CUSTOM_PROPERTIES is not None:
            # print("process parent encoder -> ", properties['custom_type'])
            return PALWORLD_CUSTOM_PROPERTIES[properties["custom_type"]][1](
                writer, property_type, properties
            )
        else:
            # Never be run to here
            return writer.property_inner(writer, property_type, properties)
    if property_type == "ArrayProperty":
        del properties["custom_type"]
        del properties["skip_type"]
        writer.fstring(properties["array_type"])
        writer.optional_guid(properties.get("id", None))
        writer.write(properties["value"])
        return len(properties["value"])
    elif property_type == "MapProperty":
        del properties["custom_type"]
        del properties["skip_type"]
        writer.fstring(properties["key_type"])
        writer.fstring(properties["value_type"])
        writer.optional_guid(properties.get("id", None))
        writer.write(properties["value"])
        return len(properties["value"])
    elif property_type == "StructProperty":
        del properties["custom_type"]
        del properties["skip_type"]
        writer.fstring(properties["struct_type"])
        writer.guid(properties["struct_id"])
        writer.optional_guid(properties.get("id", None))
        writer.write(properties["value"])
        return len(properties["value"])
    else:
        raise Exception(
            f"Expected ArrayProperty or MapProperty or StructProperty, got {property_type}"
        )


PALEDITOR_CUSTOM_PROPERTIES = copy.deepcopy(PALWORLD_CUSTOM_PROPERTIES)
PALEDITOR_CUSTOM_PROPERTIES[".worldSaveData.MapObjectSaveData"] = (
    skip_decode,
    skip_encode,
)
PALEDITOR_CUSTOM_PROPERTIES[".worldSaveData.FoliageGridSaveDataMap"] = (
    skip_decode,
    skip_encode,
)
PALEDITOR_CUSTOM_PROPERTIES[".worldSaveData.MapObjectSpawnerInStageSaveData"] = (
    skip_decode,
    skip_encode,
)
PALEDITOR_CUSTOM_PROPERTIES[".worldSaveData.DynamicItemSaveData"] = (
    skip_decode,
    skip_encode,
)
PALEDITOR_CUSTOM_PROPERTIES[".worldSaveData.ItemContainerSaveData"] = (
    skip_decode,
    skip_encode,
)
# PALEDITOR_CUSTOM_PROPERTIES[".worldSaveData.CharacterContainerSaveData"] = (skip_decode, skip_encode)
# PALEDITOR_CUSTOM_PROPERTIES[".worldSaveData.GroupSaveDataMap"] = (skip_decode, skip_encode)


class SaveManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "initialized"):
            self._file_path = None
            self._raw_gvas = None
            self._compression_times = 0x31
            self.gvas_file = None


    def open(self, file_path: str) -> Optional[GvasFile]:
        self._file_path = Path(file_path).resolve()
        if not self._file_path.exists():
            LOGGER.error(f"Save file does not exist: {self._file_path}.")
            return False

        LOGGER.info(f"Opening {self._file_path}")
        with self._file_path.open("rb") as file:
            data = file.read()

            try:
                LOGGER.info("Decompressing sav")
                self._raw_gvas, self._compression_times = decompress_sav_to_gvas(data)
            except Exception as e:
                LOGGER.error(
                    f"Caught Exception: palworld_save_tools::palsav::decompress_sav_to_gvas: {e}"
                )
                return None
            
            LOGGER.info("Reading gvas file")
            self.gvas_file = GvasFile.read(
                self._raw_gvas, PALWORLD_TYPE_HINTS, PALEDITOR_CUSTOM_PROPERTIES
            )
            LOGGER.info("Done")
        return True

    def save(self, file_path: str, _create_dir=False) -> bool:
        output_path = Path(file_path).resolve()

        if not output_path.parent.exists():
            LOGGER.error(f"Path does not exist: {output_path.parent}")
            if _create_dir:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                LOGGER.debug(f"Path {output_path.parent} created")
            else:
                return False

        LOGGER.info("Compressing GVAS file")
        sav_data = compress_gvas_to_sav(
            self.gvas_file.write(PALEDITOR_CUSTOM_PROPERTIES), self._compression_times
        )

        LOGGER.info(f"Saving to {output_path}")
        with output_path.open("wb") as file:
            file.write(sav_data)
        LOGGER.info(f"Saved to {output_path}")


if __name__ == "__main__":
    sm = SaveManager()
    sm.open(input())
    sm.save(input())