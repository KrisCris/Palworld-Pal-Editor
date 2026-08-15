import copy
import shutil
from pathlib import Path

import pytest

from palworld_pal_editor.core.pal_objects import PalObjects
from palworld_pal_editor.core.save_manager import SaveManager


WORLD_FIXTURE = Path(
    "tests/saves/1.0/AF518B19A47340B8A55BC58137981393"
)
LOSSY_UID = "a18b721d-0000-0000-0000-000000000000"
MINT_UID = "c8b99cc9-0000-0000-0000-000000000000"


def open_copied_world(tmp_path: Path) -> SaveManager:
    world = tmp_path / "world"
    shutil.copytree(WORLD_FIXTURE, world)
    SaveManager._instance = None
    manager = SaveManager()
    assert manager.open(str(world)) is not None
    return manager


def locker_ids(manager: SaveManager) -> list[str]:
    return [
        str(PalObjects.get_BaseType(entry["InstanceId"]))
        for entry in manager._locker_entries()
    ]


def test_dps_transfer_delete_and_contextual_creation_preserve_save_invariants(
    tmp_path,
):
    manager = open_copied_world(tmp_path)
    lossy = manager.get_player(LOSSY_UID)
    mint = manager.get_player(MINT_UID)
    lossy_dps = manager._dps_storages[f"dps:{LOSSY_UID}"]
    mint_dps = manager._dps_storages[f"dps:{MINT_UID}"]

    # Mint's Pal is physically stored in Lossy's public DPS in the real fixture.
    source = next(
        record
        for record in lossy_dps.records()
        if str(record.pal.OwnerPlayerUId) == MINT_UID
    )
    instance_id = str(source.pal.InstanceId)
    original_locker = locker_ids(manager)

    moved = manager.transfer_pal(source.record_key, mint_dps.storage_key, "move")
    moved_record = manager.get_record(moved["RecordKey"])
    assert lossy_dps.get(source.record_key) is None
    assert moved_record.storage_key == mint_dps.storage_key
    assert str(moved_record.pal.OwnerPlayerUId) == MINT_UID
    assert str(moved_record.pal.InstanceId) == instance_id
    assert locker_ids(manager) == original_locker

    moved = manager.transfer_pal(
        moved_record.record_key,
        f"world-container:{mint.PalStorageContainerId}",
        "move",
    )
    world_record = manager.get_record(moved["RecordKey"])
    location = manager.resolve_record_location(world_record)
    assert world_record.record_key == f"world:{instance_id}"
    assert str(world_record.pal.OwnerPlayerUId) == MINT_UID
    assert location["LocationStatus"] == "ok"
    assert world_record.pal.SlotIndex == location["ActualSlotIndex"]
    assert instance_id not in locker_ids(manager)
    assert manager.group_data.get_group(mint.group_id).has_pal(instance_id)

    world_source = next(
        record
        for record in manager.records_for_roster(LOSSY_UID)
        if record.storage_kind == "world"
        and not record.pal.IsExpeditionPal
        and manager.resolve_record_location(record)["LocationStatus"] == "ok"
    )
    world_instance_id = str(world_source.pal.InstanceId)
    world_owner = str(world_source.pal.OwnerPlayerUId)
    source_group = manager.group_data.get_group(world_source.pal.group_id)
    moved = manager.transfer_pal(world_source.record_key, lossy_dps.storage_key, "move")
    dps_record = manager.get_record(moved["RecordKey"])
    assert str(dps_record.pal.OwnerPlayerUId) == world_owner
    assert world_source.pal._pal_obj not in manager._entities_list
    assert not source_group.has_pal(world_instance_id)
    assert locker_ids(manager)[-1] == world_instance_id

    deleted_slot = dps_record.slot_index
    assert manager.delete_pal(dps_record.record_key) is True
    assert lossy_dps.free_index() == deleted_slot
    assert world_instance_id not in locker_ids(manager)

    target_keys = {
        descriptor["StorageKey"]
        for descriptor in manager.creation_targets(LOSSY_UID)
    }
    assert target_keys == {
        f"world-container:{lossy.OtomoCharacterContainerId}",
        f"world-container:{lossy.PalStorageContainerId}",
        lossy_dps.storage_key,
    }
    created = manager.create_pal(LOSSY_UID, lossy_dps.storage_key)
    assert created.storage_kind == "dps"
    assert str(created.pal.OwnerPlayerUId) == LOSSY_UID
    assert created.pal.IsExpeditionPal is False
    assert str(created.pal.InstanceId) in locker_ids(manager)


def test_full_dps_target_rejects_without_mutating_source_or_locker(
    tmp_path, monkeypatch
):
    manager = open_copied_world(tmp_path)
    source_storage = manager._dps_storages[f"dps:{LOSSY_UID}"]
    target_storage = manager._dps_storages[f"dps:{MINT_UID}"]
    source = source_storage.records()[0]
    source_snapshot = copy.deepcopy(source.external_record)
    target_snapshot = copy.deepcopy(target_storage._entries)
    locker_snapshot = copy.deepcopy(manager._locker_entries())
    registry_snapshot = set(manager._record_mapping)
    monkeypatch.setattr(target_storage, "free_index", lambda: -1)

    with pytest.raises(ValueError, match="full"):
        manager.transfer_pal(source.record_key, target_storage.storage_key, "move")

    assert source.external_record == source_snapshot
    assert target_storage._entries == target_snapshot
    assert manager._locker_entries() == locker_snapshot
    assert set(manager._record_mapping) == registry_snapshot
