import copy
import shutil
import uuid
from pathlib import Path

from palworld_save_tools.gvas import GvasFile
from palworld_save_tools.palsav import decompress_sav_to_gvas
from palworld_save_tools.paltypes import PALWORLD_CUSTOM_PROPERTIES, PALWORLD_TYPE_HINTS

from palworld_pal_editor.core.pal_objects import PalObjects
from palworld_pal_editor.core.save_codec import (
    PAL_STORAGE_CUSTOM_PROPERTIES,
    RAW_PAL_STORAGE_ENTRY,
)
from palworld_pal_editor.core.pal_storage import FixedPalStorage


OCCUPIED_DPS = Path(
    "tests/saves/1.0/AF518B19A47340B8A55BC58137981393/Players/"
    "A18B721D000000000000000000000000_dps.sav"
)


def decode(path: Path, custom_properties: dict) -> tuple[bytes, GvasFile]:
    raw_gvas, _ = decompress_sav_to_gvas(path.read_bytes())
    return raw_gvas, GvasFile.read(
        raw_gvas,
        PALWORLD_TYPE_HINTS,
        custom_properties,
    )


def occupied_indices(entries: list[dict]) -> list[int]:
    return [
        index
        for index, entry in enumerate(entries)
        if PalObjects.get_BaseType(
            entry["InstanceId"]["value"]["InstanceId"]
        )
        != PalObjects.EMPTY_UUID
    ]


def test_sparse_codec_preserves_empty_slots_as_raw_bytes_and_round_trips():
    raw_gvas, generic = decode(OCCUPIED_DPS, PALWORLD_CUSTOM_PROPERTIES)
    _, sparse = decode(OCCUPIED_DPS, PAL_STORAGE_CUSTOM_PROPERTIES)
    generic_entries = generic.properties["SaveParameterArray"]["value"]["values"]
    sparse_entries = sparse.properties["SaveParameterArray"]["value"]["values"]

    expected_occupied = occupied_indices(generic_entries)
    assert expected_occupied == [0, 9, 24]
    assert occupied_indices(sparse_entries) == expected_occupied
    assert len(sparse_entries) == len(generic_entries) == 9600

    assert "_raw_entry" not in sparse_entries[0]
    assert "SaveParameter" in sparse_entries[0]
    assert isinstance(sparse_entries[1]["_raw_entry"], bytes)
    assert "SaveParameter" not in sparse_entries[1]

    assert sparse.write(PAL_STORAGE_CUSTOM_PROPERTIES) == raw_gvas


def test_fixed_storage_allocates_and_clears_sparse_slots_after_reopen(tmp_path):
    storage_path = tmp_path / OCCUPIED_DPS.name
    shutil.copy2(OCCUPIED_DPS, storage_path)
    storage = FixedPalStorage.open(
        storage_path,
        "dps",
        "a18b721d-0000-0000-0000-000000000000",
    )
    assert RAW_PAL_STORAGE_ENTRY in storage._entries[1]

    new_instance_id = str(uuid.uuid4())
    record = storage.allocate(
        copy.deepcopy(storage._entries[0]["SaveParameter"]),
        new_instance_id,
    )
    assert record.slot_index == 1
    assert RAW_PAL_STORAGE_ENTRY not in storage._entries[record.slot_index]
    storage_path.write_bytes(storage.serialize())

    reopened = FixedPalStorage.open(
        storage_path,
        "dps",
        "a18b721d-0000-0000-0000-000000000000",
    )
    reopened_record = reopened.get(record.record_key)
    assert reopened_record is not None
    assert str(reopened_record.pal.InstanceId) == new_instance_id

    reopened.clear(record.record_key)
    storage_path.write_bytes(reopened.serialize())
    cleared = FixedPalStorage.open(
        storage_path,
        "dps",
        "a18b721d-0000-0000-0000-000000000000",
    )
    assert cleared.get(record.record_key) is None
