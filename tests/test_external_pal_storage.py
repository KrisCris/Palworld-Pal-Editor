import copy
import shutil
from pathlib import Path

from palworld_pal_editor.core.pal_objects import PalObjects, toUUID
from palworld_pal_editor.core.pal_storage import FixedPalStorage
from palworld_pal_editor.core.pal_storage_adapters import DpsPalAdapter
from palworld_pal_editor.core.save_manager import SaveManager


DPS_FIXTURE = Path(
    "tests/saves/1.0/8C439FF04713B5F986F9CAB485575089/Players/"
    "00000000000000000000000000000001_dps.sav"
)
OWNER_UID = toUUID("00000000-0000-0000-0000-000000000001")
INSTANCE_IDS = [
    toUUID(f"10000000-0000-0000-0000-{index:012d}") for index in range(1, 10)
]
STALE_CONTAINER_ID = toUUID("20000000-0000-0000-0000-000000000001")
WORLD_PAL_ID = toUUID("cfab9a78-49bd-bf16-474f-6e83eee20d7a")
WORLD_FIXTURE = Path(
    "tests/saves/1.0/8C439FF04713B5F986F9CAB485575089"
)


def copied_empty_dps(tmp_path: Path) -> DpsPalAdapter:
    path = tmp_path / "00000000000000000000000000000001_dps.sav"
    shutil.copy2(DPS_FIXTURE, path)
    return DpsPalAdapter(FixedPalStorage.open(path, "dps", OWNER_UID))


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


def copied_world(tmp_path: Path) -> Path:
    path = tmp_path / "world"
    shutil.copytree(WORLD_FIXTURE, path)
    return path


def write_synthetic_global(path: Path, instance_id) -> None:
    shutil.copy2(DPS_FIXTURE, path)
    storage = FixedPalStorage.open(path, "dps", OWNER_UID)
    storage.gvas_file.header.save_game_class_name = (
        "/Script/Pal.PalGlobalPalStorageSaveGame"
    )
    storage.gvas_file.properties["SaveParameterArray"]["value"]["type_name"] = (
        "PalGlobalPalStorageSaveParameter"
    )
    DpsPalAdapter(storage).allocate(make_save_parameter(instance_id), instance_id)
    path.write_bytes(storage.serialize())


def test_external_storage_uses_outer_index_and_round_trips(tmp_path):
    adapter = copied_empty_dps(tmp_path)
    record = adapter.allocate(make_save_parameter(INSTANCE_IDS[0]), INSTANCE_IDS[0])

    assert record.slot_index == 0
    assert record.record_key == f"dps:{OWNER_UID}:0"
    assert record.pal.InstanceId == INSTANCE_IDS[0]
    assert record.pal.SlotId == (STALE_CONTAINER_ID, 99)

    path = adapter.storage.path
    path.write_bytes(adapter.storage.serialize())
    reloaded = DpsPalAdapter(FixedPalStorage.open(path, "dps", OWNER_UID))
    reloaded_record = reloaded.get(record.record_key)

    assert reloaded_record is not None
    assert reloaded_record.slot_index == 0
    assert reloaded_record.pal.InstanceId == INSTANCE_IDS[0]
    assert reloaded_record.pal.SlotId == (STALE_CONTAINER_ID, 99)


def test_clear_frees_exact_outer_slot_without_compaction(tmp_path):
    adapter = copied_empty_dps(tmp_path)
    records = [
        adapter.allocate(make_save_parameter(instance_id), instance_id)
        for instance_id in INSTANCE_IDS[:8]
    ]

    adapter.clear(records[2].record_key)

    assert adapter.get(records[2].record_key) is None
    assert adapter.get(records[7].record_key) is not None
    assert adapter.get(records[7].record_key).slot_index == 7
    assert adapter.storage.free_index() == 2


def test_save_manager_discovers_qualified_dps_and_optional_global_records(tmp_path):
    previous_manager = SaveManager._instance
    try:
        world = copied_world(tmp_path)
        SaveManager._instance = None
        manager = SaveManager()
        assert manager.open(str(world)) is not None
        assert manager.has_global_palbox is False

        dps_path = world / "Players/00000000000000000000000000000001_dps.sav"
        dps = FixedPalStorage.open(dps_path, "dps", OWNER_UID)
        DpsPalAdapter(dps).allocate(
            make_save_parameter(INSTANCE_IDS[1]), INSTANCE_IDS[1]
        )
        dps_path.write_bytes(dps.serialize())
        write_synthetic_global(world.parent / "GlobalPalStorage.sav", WORLD_PAL_ID)

        assert manager.open(str(world)) is not None
        assert manager.has_global_palbox is True
        assert manager.get_record(f"world:{WORLD_PAL_ID}").pal.InstanceId == WORLD_PAL_ID
        assert manager.get_record("gps:0").pal.InstanceId == WORLD_PAL_ID
        assert {
            record.record_key
            for record in manager.records_by_instance(WORLD_PAL_ID, "all")
        } == {f"world:{WORLD_PAL_ID}", "gps:0"}
        assert f"dps:{OWNER_UID}:0" in {
            record.record_key
            for record in manager.records_for_roster(str(OWNER_UID))
        }
    finally:
        SaveManager._instance = previous_manager


def test_save_persists_prewrite_global_storage_backup(tmp_path):
    previous_manager = SaveManager._instance
    try:
        world = copied_world(tmp_path)
        global_path = world.parent / "GlobalPalStorage.sav"
        write_synthetic_global(global_path, WORLD_PAL_ID)
        original_global_data = global_path.read_bytes()

        SaveManager._instance = None
        manager = SaveManager()
        assert manager.open(str(world)) is not None
        manager.storage_adapters["global-palbox"].allocate(
            make_save_parameter(INSTANCE_IDS[2]),
            INSTANCE_IDS[2],
        )

        assert manager.save(str(world)) is True

        backup_directories = list(
            (world / "Palworld-Pal-Editor-Backup").iterdir()
        )
        assert len(backup_directories) == 1
        assert (
            backup_directories[0] / "GlobalPalStorage.sav"
        ).read_bytes() == original_global_data
        assert global_path.read_bytes() != original_global_data
    finally:
        SaveManager._instance = previous_manager
