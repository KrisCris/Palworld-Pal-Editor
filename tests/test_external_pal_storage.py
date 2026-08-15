import copy
import shutil
from pathlib import Path

from palworld_pal_editor.core.pal_objects import PalObjects, toUUID
from palworld_pal_editor.core.pal_storage import FixedPalStorage


DPS_FIXTURE = Path(
    "tests/saves/1.0/8C439FF04713B5F986F9CAB485575089/Players/"
    "00000000000000000000000000000001_dps.sav"
)
OWNER_UID = toUUID("00000000-0000-0000-0000-000000000001")
INSTANCE_IDS = [
    toUUID(f"10000000-0000-0000-0000-{index:012d}") for index in range(1, 10)
]
STALE_CONTAINER_ID = toUUID("20000000-0000-0000-0000-000000000001")


def copied_empty_dps(tmp_path: Path) -> FixedPalStorage:
    path = tmp_path / "00000000000000000000000000000001_dps.sav"
    shutil.copy2(DPS_FIXTURE, path)
    return FixedPalStorage.open(path, "dps", OWNER_UID)


def make_save_parameter(instance_id):
    pal_obj = PalObjects.PalSaveParameter(
        instance_id,
        OWNER_UID,
        STALE_CONTAINER_ID,
        99,
        PalObjects.EMPTY_UUID,
    )
    return copy.deepcopy(
        pal_obj["value"]["RawData"]["value"]["object"]["SaveParameter"]
    )


def test_external_storage_uses_outer_index_and_round_trips(tmp_path):
    storage = copied_empty_dps(tmp_path)
    record = storage.allocate(make_save_parameter(INSTANCE_IDS[0]), INSTANCE_IDS[0])

    assert record.slot_index == 0
    assert record.record_key == f"dps:{OWNER_UID}:0"
    assert record.pal.InstanceId == INSTANCE_IDS[0]
    assert record.pal.SlotId == (STALE_CONTAINER_ID, 99)

    storage.path.write_bytes(storage.serialize())
    reloaded = FixedPalStorage.open(storage.path, "dps", OWNER_UID)
    reloaded_record = reloaded.get(record.record_key)

    assert reloaded_record is not None
    assert reloaded_record.slot_index == 0
    assert reloaded_record.pal.InstanceId == INSTANCE_IDS[0]
    assert reloaded_record.pal.SlotId == (STALE_CONTAINER_ID, 99)


def test_clear_frees_exact_outer_slot_without_compaction(tmp_path):
    storage = copied_empty_dps(tmp_path)
    records = [
        storage.allocate(make_save_parameter(instance_id), instance_id)
        for instance_id in INSTANCE_IDS[:8]
    ]

    storage.clear(records[2].record_key)

    assert storage.get(records[2].record_key) is None
    assert storage.get(records[7].record_key) is not None
    assert storage.get(records[7].record_key).slot_index == 7
    assert storage.free_index() == 2
