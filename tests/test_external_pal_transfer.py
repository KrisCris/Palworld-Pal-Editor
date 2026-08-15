import copy
import shutil
from pathlib import Path

import pytest

from palworld_pal_editor.core.pal_objects import PalObjects
from palworld_pal_editor.core.pal_storage import FixedPalStorage
from palworld_pal_editor.core.save_manager import PalIdentityConflict, SaveManager


WORLD_FIXTURE = Path(
    "tests/saves/1.0/AF518B19A47340B8A55BC58137981393"
)
EMPTY_DPS_FIXTURE = Path(
    "tests/saves/1.0/8C439FF04713B5F986F9CAB485575089/Players/"
    "00000000000000000000000000000001_dps.sav"
)
LOSSY_UID = "a18b721d-0000-0000-0000-000000000000"
MINT_UID = "c8b99cc9-0000-0000-0000-000000000000"


def write_empty_global(path: Path) -> None:
    shutil.copy2(EMPTY_DPS_FIXTURE, path)
    storage = FixedPalStorage.open(path, "dps", LOSSY_UID)
    storage.gvas_file.header.save_game_class_name = (
        "/Script/Pal.PalGlobalPalStorageSaveGame"
    )
    storage.gvas_file.properties["SaveParameterArray"]["value"]["type_name"] = (
        "PalGlobalPalStorageSaveParameter"
    )
    path.write_bytes(storage.serialize())


def open_copied_world(tmp_path: Path, with_global=False) -> SaveManager:
    world = tmp_path / "world"
    shutil.copytree(WORLD_FIXTURE, world)
    if with_global:
        write_empty_global(world.parent / "GlobalPalStorage.sav")
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


def test_global_creation_export_import_and_update_keep_the_right_envelopes(
    tmp_path,
):
    manager = open_copied_world(tmp_path, with_global=True)
    global_storage = manager._global_palbox
    mint = manager.get_player(MINT_UID)

    created = manager.create_pal("PAL_GLOBAL_STORAGE_BTN", "global-palbox")
    created_id = str(created.pal.InstanceId)
    assert created.storage_kind == "global_palbox"
    assert created.pal.OwnerPlayerUId == PalObjects.EMPTY_UUID
    assert created.pal.OldOwnerPlayerUIds == []
    assert created.pal.SlotId == (PalObjects.EMPTY_UUID, -1)
    assert created.pal.IsImportedCharacter is True
    assert PalObjects.get_PalContainerId(
        created.pal._pal_param["ItemContainerId"]
    ) == PalObjects.EMPTY_UUID
    assert PalObjects.get_BaseType(
        created.external_record["InstanceId"]["value"]["PlayerUId"]
    ) == PalObjects.EMPTY_UUID
    assert created_id not in locker_ids(manager)

    imported = manager.transfer_pal(
        created.record_key,
        f"world-container:{mint.PalStorageContainerId}",
        "clone",
    )
    imported_record = manager.get_record(imported["RecordKey"])
    assert manager.get_record(created.record_key) is created
    assert str(imported_record.pal.InstanceId) == created_id
    assert str(imported_record.pal.OwnerPlayerUId) == MINT_UID
    assert manager.resolve_record_location(imported_record)["LocationStatus"] == "ok"

    world_source = next(
        record
        for record in manager.records_for_roster(LOSSY_UID)
        if record.storage_kind == "world"
        and not record.pal.IsExpeditionPal
        and manager.resolve_record_location(record)["LocationStatus"] == "ok"
    )
    source_old_owners = list(world_source.pal.OldOwnerPlayerUIds or [])
    source_slot = world_source.pal.SlotId
    exported = manager.transfer_pal(
        world_source.record_key, "global-palbox", "clone"
    )
    gps_record = manager.get_record(exported["RecordKey"])
    assert manager.get_record(world_source.record_key) is world_source
    assert gps_record.pal.InstanceId == world_source.pal.InstanceId
    assert gps_record.pal.OwnerPlayerUId == PalObjects.EMPTY_UUID
    assert gps_record.pal.OldOwnerPlayerUIds == source_old_owners
    assert gps_record.pal.SlotId == source_slot
    assert gps_record.pal.IsImportedCharacter is True
    assert str(gps_record.pal.InstanceId) not in locker_ids(manager)

    with pytest.raises(PalIdentityConflict) as collision:
        manager.transfer_pal(
            gps_record.record_key,
            f"world-container:{mint.PalStorageContainerId}",
            "clone",
        )
    assert [item.record_key for item in collision.value.candidates] == [
        world_source.record_key
    ]

    destination_envelope = {
        "record_key": world_source.record_key,
        "owner": world_source.pal.OwnerPlayerUId,
        "owners": copy.deepcopy(world_source.pal._pal_param.get("OldOwnerPlayerUIds")),
        "group": world_source.pal.group_id,
        "slot": world_source.pal.SlotId,
        "expedition": copy.deepcopy(
            world_source.pal._pal_param.get(
                "MapObjectConcreteInstanceIdAssignedToExpedition"
            )
        ),
        "locker": locker_ids(manager),
    }
    gps_record.pal.NickName = "GPS update payload"
    updated = manager.transfer_pal(
        gps_record.record_key,
        world_source.storage_key,
        "update",
        world_source.record_key,
    )
    updated_record = manager.get_record(updated["RecordKey"])
    assert updated_record.record_key == destination_envelope["record_key"]
    assert updated_record.pal.NickName == "GPS update payload"
    assert updated_record.pal.OwnerPlayerUId == destination_envelope["owner"]
    assert (
        updated_record.pal._pal_param.get("OldOwnerPlayerUIds")
        == destination_envelope["owners"]
    )
    assert updated_record.pal.group_id == destination_envelope["group"]
    assert updated_record.pal.SlotId == destination_envelope["slot"]
    assert (
        updated_record.pal._pal_param.get(
            "MapObjectConcreteInstanceIdAssignedToExpedition"
        )
        == destination_envelope["expedition"]
    )
    assert locker_ids(manager) == destination_envelope["locker"]


def test_global_import_requires_an_owned_player_party_or_palbox(tmp_path):
    manager = open_copied_world(tmp_path, with_global=True)
    source = manager.create_pal("PAL_GLOBAL_STORAGE_BTN", "global-palbox")
    lossy = manager.get_player(LOSSY_UID)
    base = next(
        descriptor
        for descriptor in manager.get_container_registry()
        if descriptor["ContainerKind"] == "base"
    )

    for target in (f"dps:{LOSSY_UID}", base["StorageKey"]):
        with pytest.raises(ValueError, match="player Party or Palbox"):
            manager.transfer_pal(source.record_key, target, "clone")

    imported = manager.transfer_pal(
        source.record_key,
        f"world-container:{lossy.PalStorageContainerId}",
        "clone",
    )
    imported_record = manager.get_record(imported["RecordKey"])
    assert imported_record.pal.OwnerPlayerUId == lossy.PlayerUId


def test_duplicate_pal_registers_a_new_record_in_the_source_storage(tmp_path):
    manager = open_copied_world(tmp_path, with_global=True)
    lossy_dps = manager._dps_storages[f"dps:{LOSSY_UID}"]

    dps_source = next(
        record
        for record in lossy_dps.records()
        if str(record.pal.OwnerPlayerUId) == MINT_UID
    )
    gps_source = manager.create_pal("PAL_GLOBAL_STORAGE_BTN", "global-palbox")
    world_source = next(
        record
        for record in manager.records_for_roster(LOSSY_UID)
        if record.storage_kind == "world"
        and manager.resolve_record_location(record)["LocationStatus"] == "ok"
    )

    dps_clone = manager.duplicate_pal(dps_source.record_key, LOSSY_UID)
    gps_clone = manager.duplicate_pal(gps_source.record_key, "PAL_GLOBAL_STORAGE_BTN")
    world_clone = manager.duplicate_pal(world_source.record_key, LOSSY_UID)

    assert dps_clone.storage_key == dps_source.storage_key
    assert dps_clone.pal.InstanceId != dps_source.pal.InstanceId
    assert dps_clone.pal.OwnerPlayerUId == dps_source.pal.OwnerPlayerUId
    assert manager.get_record(dps_clone.record_key) is dps_clone
    assert str(dps_clone.pal.InstanceId) in locker_ids(manager)

    assert gps_clone.storage_key == gps_source.storage_key == "global-palbox"
    assert gps_clone.pal.InstanceId != gps_source.pal.InstanceId
    assert manager.get_record(gps_clone.record_key) is gps_clone
    assert str(gps_clone.pal.InstanceId) not in locker_ids(manager)

    assert world_clone.storage_kind == "world"
    assert world_clone.pal.InstanceId != world_source.pal.InstanceId
    assert manager.get_record(world_clone.record_key) is world_clone

    clone_keys = [
        dps_clone.record_key,
        gps_clone.record_key,
        world_clone.record_key,
    ]
    clone_ids = [
        str(dps_clone.pal.InstanceId),
        str(gps_clone.pal.InstanceId),
        str(world_clone.pal.InstanceId),
    ]
    assert manager.save(str(manager._file_path)) is True

    SaveManager._instance = None
    reopened = SaveManager()
    assert reopened.open(str(manager._file_path)) is not None
    for record_key, instance_id in zip(clone_keys, clone_ids):
        record = reopened.get_record(record_key)
        assert record is not None
        assert str(record.pal.InstanceId) == instance_id


def test_global_update_rejects_ambiguous_destination_identity(tmp_path):
    manager = open_copied_world(tmp_path, with_global=True)
    lossy_dps = manager._dps_storages[f"dps:{LOSSY_UID}"]
    source = next(
        record
        for record in manager.records_for_roster(LOSSY_UID)
        if record.storage_kind == "world"
        and not record.pal.IsExpeditionPal
        and manager.resolve_record_location(record)["LocationStatus"] == "ok"
    )
    exported = manager.transfer_pal(source.record_key, "global-palbox", "clone")
    gps_record = manager.get_record(exported["RecordKey"])
    duplicate = lossy_dps.allocate(
        manager._save_parameter(gps_record.pal), gps_record.pal.InstanceId
    )
    manager._add_locker_id(duplicate.pal.InstanceId)
    manager._register_external_record(duplicate)
    source_snapshot = copy.deepcopy(source.pal._pal_param)

    with pytest.raises(PalIdentityConflict) as collision:
        manager.transfer_pal(
            gps_record.record_key,
            source.storage_key,
            "update",
            source.record_key,
        )

    assert {record.record_key for record in collision.value.candidates} == {
        source.record_key,
        duplicate.record_key,
    }
    assert source.pal._pal_param == source_snapshot


def test_save_transaction_restores_level_dps_and_global_on_replace_failure(
    tmp_path, monkeypatch
):
    manager = open_copied_world(tmp_path, with_global=True)
    manager.create_pal(LOSSY_UID, f"dps:{LOSSY_UID}")
    manager.create_pal("PAL_GLOBAL_STORAGE_BTN", "global-palbox")
    level_path = manager._file_path / "Level.sav"
    dps_path = manager._dps_storages[f"dps:{LOSSY_UID}"].path
    global_path = manager._global_palbox.path
    original = {
        level_path: level_path.read_bytes(),
        dps_path: dps_path.read_bytes(),
        global_path: global_path.read_bytes(),
    }
    replace_count = 0
    real_replace = manager._replace_staged_output

    def fail_second_replace(temp, target):
        nonlocal replace_count
        replace_count += 1
        if replace_count == 2:
            raise OSError("injected replacement failure")
        real_replace(temp, target)

    monkeypatch.setattr(manager, "_replace_staged_output", fail_second_replace)

    assert manager.save(str(manager._file_path)) is False
    assert replace_count == 2
    assert {path: path.read_bytes() for path in original} == original
