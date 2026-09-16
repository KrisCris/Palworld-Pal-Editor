"""What this editor decodes out of a save, and what it copies through untouched.

`palworld_save_tools` decodes a save according to per-path handlers, and two kinds
of override live here.

`skip_decode`/`skip_encode` and the two skip lists cover the properties this editor
never reads -- foliage, dungeons, map objects. They are kept as raw bytes and
written back byte for byte, which is both much faster and safer than re-encoding
something nothing here understands.

`decode_save_parameter_array` is the opposite case: the external Pal storage array
*is* the Pals, so an occupied entry is decoded properly. An empty slot still keeps
its original bytes, because there is nothing in it worth rebuilding.
"""

import copy

from palworld_save_tools.archive import FArchiveReader, FArchiveWriter
from palworld_save_tools.paltypes import PALWORLD_CUSTOM_PROPERTIES

from .pal_objects import PalObjects


RAW_PAL_STORAGE_ENTRY = "_raw_entry"


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
            return PALWORLD_CUSTOM_PROPERTIES[properties["custom_type"]][1](
                writer, property_type, properties
            )
        return writer.property_inner(writer, property_type, properties)
    if property_type == "ArrayProperty":
        del properties["custom_type"]
        del properties["skip_type"]
        writer.fstring(properties["array_type"])
        writer.optional_guid(properties.get("id", None))
        writer.write(properties["value"])
        return len(properties["value"])
    if property_type == "MapProperty":
        del properties["custom_type"]
        del properties["skip_type"]
        writer.fstring(properties["key_type"])
        writer.fstring(properties["value_type"])
        writer.optional_guid(properties.get("id", None))
        writer.write(properties["value"])
        return len(properties["value"])
    if property_type == "StructProperty":
        del properties["custom_type"]
        del properties["skip_type"]
        writer.fstring(properties["struct_type"])
        writer.guid(properties["struct_id"])
        writer.optional_guid(properties.get("id", None))
        writer.write(properties["value"])
        return len(properties["value"])
    raise Exception(
        f"Expected ArrayProperty or MapProperty or StructProperty, got {property_type}"
    )


MAIN_SKIP_PROPERTIES = copy.deepcopy(PALWORLD_CUSTOM_PROPERTIES)
MAIN_SKIP_PROPERTIES[".worldSaveData.MapObjectSaveData"] = (skip_decode, skip_encode)
MAIN_SKIP_PROPERTIES[".worldSaveData.FoliageGridSaveDataMap"] = (
    skip_decode,
    skip_encode,
)
MAIN_SKIP_PROPERTIES[".worldSaveData.MapObjectSpawnerInStageSaveData"] = (
    skip_decode,
    skip_encode,
)
MAIN_SKIP_PROPERTIES[".worldSaveData.WorkSaveData"] = (skip_decode, skip_encode)
MAIN_SKIP_PROPERTIES[".worldSaveData.DungeonSaveData"] = (skip_decode, skip_encode)
MAIN_SKIP_PROPERTIES[".worldSaveData.EnemyCampSaveData"] = (skip_decode, skip_encode)
MAIN_SKIP_PROPERTIES[".worldSaveData.CharacterParameterStorageSaveData"] = (
    skip_decode,
    skip_encode,
)
MAIN_SKIP_PROPERTIES[".worldSaveData.InvaderSaveData"] = (skip_decode, skip_encode)
MAIN_SKIP_PROPERTIES[".worldSaveData.DungeonPointMarkerSaveData"] = (
    skip_decode,
    skip_encode,
)
MAIN_SKIP_PROPERTIES[".worldSaveData.GameTimeSaveData"] = (skip_decode, skip_encode)
MAIN_SKIP_PROPERTIES[".worldSaveData.FixedWeaponDestroySaveData"] = (
    skip_decode,
    skip_encode,
)
MAIN_SKIP_PROPERTIES[".worldSaveData.OilrigSaveData"] = (skip_decode, skip_encode)
MAIN_SKIP_PROPERTIES[".worldSaveData.SupplySaveData"] = (skip_decode, skip_encode)
MAIN_SKIP_PROPERTIES[".worldSaveData.RandomizerSaveData"] = (skip_decode, skip_encode)
PLAYER_SKIP_PROPERTIES = copy.deepcopy(PALWORLD_CUSTOM_PROPERTIES)
PLAYER_SKIP_PROPERTIES[".SaveData.PlayerCharacterMakeData"] = (
    skip_decode,
    skip_encode,
)
PLAYER_SKIP_PROPERTIES[".SaveData.LastTransform"] = (skip_decode, skip_encode)


def _read_raw_entry(reader: FArchiveReader, path: str) -> tuple[bytes, dict]:
    entry_start = reader.data.tell()
    instance_id = None
    while True:
        name = reader.fstring()
        if name == "None":
            break
        type_name = reader.fstring()
        size = reader.u64()
        property_path = f"{path}.{name}"
        if name == "InstanceId":
            instance_id = reader.property(type_name, size, property_path)
        elif name == "SaveParameter" and type_name == "StructProperty":
            reader.fstring()
            reader.guid()
            reader.optional_guid()
            reader.skip(size)
        else:
            raise ValueError(
                f"Unexpected external Pal storage property: {property_path} ({type_name})"
            )
    if instance_id is None:
        raise ValueError(f"External Pal storage entry has no InstanceId: {path}")

    entry_end = reader.data.tell()
    reader.data.seek(entry_start)
    raw_entry = reader.read(entry_end - entry_start)
    reader.data.seek(entry_end)
    return raw_entry, instance_id


def _is_occupied_instance_id(instance_id: dict) -> bool:
    value = PalObjects.get_BaseType(instance_id["value"].get("InstanceId"))
    return value is not None and value != PalObjects.EMPTY_UUID


def decode_save_parameter_array(
    reader: FArchiveReader,
    type_name: str,
    size: int,
    path: str,
) -> dict:
    if type_name != "ArrayProperty":
        raise ValueError(f"Expected ArrayProperty, got {type_name} in {path}")
    array_type = reader.fstring()
    array_id = reader.optional_guid()
    if array_type != "StructProperty":
        raise ValueError(f"Expected StructProperty array, got {array_type} in {path}")

    count = reader.u32()
    prop_name = reader.fstring()
    prop_type = reader.fstring()
    reader.u64()
    struct_type = reader.fstring()
    struct_id = reader.guid()
    reader.skip(1)
    entry_path = f"{path}.{prop_name}"
    entries = []
    for _ in range(count):
        raw_entry, instance_id = _read_raw_entry(reader, entry_path)
        if _is_occupied_instance_id(instance_id):
            entry_reader = reader.internal_copy(raw_entry, debug=False)
            entries.append(entry_reader.properties_until_end(entry_path))
        else:
            entries.append(
                {
                    "InstanceId": instance_id,
                    RAW_PAL_STORAGE_ENTRY: raw_entry,
                }
            )

    return {
        "array_type": array_type,
        "id": array_id,
        "value": {
            "prop_name": prop_name,
            "prop_type": prop_type,
            "values": entries,
            "type_name": struct_type,
            "id": struct_id,
        },
    }


def encode_save_parameter_array(
    writer: FArchiveWriter,
    property_type: str,
    properties: dict,
) -> int:
    if property_type != "ArrayProperty":
        raise ValueError(f"Expected ArrayProperty, got {property_type}")
    if properties["array_type"] != "StructProperty":
        raise ValueError(
            f"Expected StructProperty array, got {properties['array_type']}"
        )

    writer.fstring(properties["array_type"])
    writer.optional_guid(properties.get("id"))
    value_start = writer.data.tell()
    value = properties["value"]
    entries = value["values"]
    writer.u32(len(entries))
    writer.fstring(value["prop_name"])
    writer.fstring(value["prop_type"])
    size_position = writer.data.tell()
    writer.u64(0)
    writer.fstring(value["type_name"])
    writer.guid(value["id"])
    writer.u(0)
    entries_start = writer.data.tell()
    for entry in entries:
        raw_entry = entry.get(RAW_PAL_STORAGE_ENTRY)
        if raw_entry is not None:
            writer.write(raw_entry)
        else:
            writer.properties(entry)
    end_position = writer.data.tell()
    writer.data.seek(size_position)
    writer.u64(end_position - entries_start)
    writer.data.seek(end_position)
    return end_position - value_start


PAL_STORAGE_CUSTOM_PROPERTIES = copy.deepcopy(PALWORLD_CUSTOM_PROPERTIES)
PAL_STORAGE_CUSTOM_PROPERTIES[".SaveParameterArray"] = (
    decode_save_parameter_array,
    encode_save_parameter_array,
)
