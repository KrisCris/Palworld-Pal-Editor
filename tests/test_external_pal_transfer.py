"""What a Pal keeps when it changes format (spec §6.3, §7).

`test_pal_transfers.py` owns the capability and the three executors as such. What
is left here is the part only the real save files can answer: a payload written in
one format and read back in another, and the two side lists -- the DPS locker and
the Global Palbox -- that have to agree with it afterwards.
"""

import copy
from pathlib import Path

import pytest

from palworld_pal_editor.core.pal_objects import PalObjects
from palworld_pal_editor.core.pal_operations import (
    PalIdentityConflict,
    PalOperationRefused,
)
from palworld_pal_editor.core.save_manager import SaveManager
from world_fixture import (
    LOSSY_UID,
    MINT_UID,
    locker_ids,
    open_world,
    write_empty_global,
)


def open_copied_world(tmp_path: Path, with_global=False) -> SaveManager:
    """This file's Global Palbox is always the empty one: it tests creating into it."""
    if not with_global:
        return open_world(tmp_path)
    empty_global = tmp_path / "empty-global.sav"
    write_empty_global(empty_global)
    return open_world(tmp_path, global_palbox=empty_global)


def a_world_pal(manager, player_uid):
    """One of a player's Pals that is really standing in the container it records."""
    return next(
        record
        for record in manager.records_for_roster(player_uid)
        if record.storage_kind == "world"
        and not record.pal.IsExpeditionPal
        and record.storage_key is not None
    )


def test_a_move_between_two_dps_files_keeps_the_pal_whole(tmp_path):
    """DPS to DPS: the one row of the spec §7 table with no World record in it.

    Nothing converts, so what has to hold is that the record is re-keyed rather than
    replaced, that the Pal keeps the owner it had -- a DPS is a place, not a person
    -- and that the locker does not move, because the Pal was held outside the world
    save before and still is.
    """
    manager = open_copied_world(tmp_path)
    lossy_dps = manager.storage_adapters[f"dps:{LOSSY_UID}"]
    mint_dps = manager.storage_adapters[f"dps:{MINT_UID}"]
    # Mint's Pal is physically stored in Lossy's public DPS in the real fixture.
    # The adapter reads a fresh record out of the file every call, so the one the
    # session holds -- the one a transfer moves -- is the repository's.
    origin_key = next(
        record.record_key
        for record in lossy_dps.records()
        if str(record.pal.OwnerPlayerUId) == MINT_UID
    )
    source = manager.get_record(origin_key)
    instance_id = str(source.pal.InstanceId)
    character = source.pal.CharacterID
    locker_before = locker_ids(manager)

    outcome = manager.pal_operations.transfer(origin_key, mint_dps.storage_key)

    assert outcome.record is source
    assert outcome.deleted_record_keys == [origin_key]
    assert source.storage_key == mint_dps.storage_key
    assert source.record_key.startswith(f"{mint_dps.storage_key}:")
    assert str(source.pal.InstanceId) == instance_id
    assert source.pal.CharacterID == character
    assert str(source.pal.OwnerPlayerUId) == MINT_UID
    assert lossy_dps.get(origin_key) is None
    assert manager.get_record(origin_key) is None
    assert manager.get_record(source.record_key) is source
    assert locker_ids(manager) == locker_before


def test_deleting_and_creating_in_a_dps_keep_the_locker_in_step(tmp_path):
    """The locker is the game's list of Pals held outside the world save.

    A Pal that stops existing has to leave it, and one created in a DPS has to join
    it: an entry the locker does not list reads to the game as a Pal still standing
    in a container somewhere.
    """
    manager = open_copied_world(tmp_path)
    lossy = manager.get_player(LOSSY_UID)
    lossy_dps = manager.storage_adapters[f"dps:{LOSSY_UID}"]
    doomed = lossy_dps.records()[0]
    doomed_id = str(doomed.pal.InstanceId)
    occupied_before = lossy_dps.storage.occupied

    assert manager.delete_pal(doomed.record_key) is True

    assert manager.get_record(doomed.record_key) is None
    assert lossy_dps.get(doomed.record_key) is None
    assert lossy_dps.storage.occupied == occupied_before - 1
    assert doomed_id not in locker_ids(manager)

    target_keys = {
        descriptor["StorageKey"]
        for descriptor in manager.storage_directory.creation_targets(LOSSY_UID)
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


def test_a_pal_created_in_the_global_palbox_carries_no_local_position(tmp_path):
    """A Global Palbox entry is a payload, not a Pal standing anywhere.

    Every field that says where a Pal is or whose it is has to be cleared on the way
    in, including the ones written outside `SaveParameter`; the game reads a Global
    Palbox entry that still names a container as belonging to a save it is not in.
    """
    manager = open_copied_world(tmp_path, with_global=True)

    created = manager.create_pal("global-palbox", "global-palbox")

    assert created.storage_kind == "global_palbox"
    assert created.pal.OwnerPlayerUId == PalObjects.EMPTY_UUID
    assert created.pal.OldOwnerPlayerUIds == []
    assert created.pal.SlotId == (PalObjects.EMPTY_UUID, -1)
    assert created.pal.IsImportedCharacter is True
    assert PalObjects.get_PalContainerId(
        created.pal.pal_param["ItemContainerId"]
    ) == PalObjects.EMPTY_UUID
    assert PalObjects.get_BaseType(
        created.native_record["InstanceId"]["value"]["PlayerUId"]
    ) == PalObjects.EMPTY_UUID
    # Nothing is holding it: the Global Palbox is not this save's locker.
    assert str(created.pal.InstanceId) not in locker_ids(manager)


def test_a_copy_out_of_the_global_palbox_lands_as_the_target_players_own(tmp_path):
    """The other direction: a payload becomes a World Pal in somebody's Palbox.

    Only a player's own Party or Palbox can take one, because that is the only
    target that answers the two questions the payload does not: whose it is and
    which guild it joins.
    """
    manager = open_copied_world(tmp_path, with_global=True)
    lossy = manager.get_player(LOSSY_UID)
    source = manager.create_pal("global-palbox", "global-palbox")
    base = next(
        descriptor
        for descriptor in manager.storage_directory.registry()
        if descriptor["ContainerKind"] == "base"
    )

    for target in (f"dps:{LOSSY_UID}", base["StorageKey"]):
        with pytest.raises(PalOperationRefused) as refused:
            manager.pal_operations.transfer(source.record_key, target)
        assert refused.value.code == "GPS_PLAYER_TARGET_REQUIRED"

    outcome = manager.pal_operations.transfer(
        source.record_key, f"world-container:{lossy.PalStorageContainerId}"
    )

    # A copy: the Global Palbox keeps its own entry, and the new Pal is a second
    # physical Pal with the same identity.
    assert manager.get_record(source.record_key) is source
    assert outcome.record is not source
    assert outcome.deleted_record_keys == []
    assert outcome.record.storage_kind == "world"
    assert outcome.record.pal.InstanceId == source.pal.InstanceId
    assert str(outcome.record.pal.OwnerPlayerUId) == LOSSY_UID
    assert manager.group_data.get_group(lossy.group_id).has_pal(
        str(outcome.record.pal.InstanceId)
    )
    assert str(outcome.record.pal.InstanceId) not in locker_ids(manager)


def test_a_second_local_twin_makes_a_confirmed_overwrite_ambiguous_again(tmp_path):
    """Two candidates and the backend does not choose, confirmation or not.

    The user confirmed one target out of one. A second Pal with the same identity
    appearing since is the same staleness as that target moving, so it comes back as
    the conflict again rather than being overwritten on a guess (spec §7).
    """
    manager = open_copied_world(tmp_path, with_global=True)
    lossy_dps = manager.storage_adapters[f"dps:{LOSSY_UID}"]
    source = a_world_pal(manager, LOSSY_UID)
    gps_record = manager.pal_operations.transfer(
        source.record_key, "global-palbox"
    ).record
    duplicate = lossy_dps.allocate(
        gps_record.pal.save_parameter, gps_record.pal.InstanceId
    )
    manager.add_locker_id(duplicate.pal.InstanceId)
    manager._register_external_record(duplicate)
    source_snapshot = copy.deepcopy(source.pal.pal_param)

    with pytest.raises(PalIdentityConflict) as collision:
        manager.pal_operations.transfer(
            gps_record.record_key,
            source.storage_key,
            {
                "recordKey": source.record_key,
                "storageKey": source.storage_key,
            },
        )

    assert {record.record_key for record in collision.value.candidates} == {
        source.record_key,
        duplicate.record_key,
    }
    assert source.pal.pal_param == source_snapshot


def test_duplicate_pal_registers_a_new_record_in_the_source_storage(tmp_path):
    manager = open_copied_world(tmp_path, with_global=True)
    lossy_dps = manager.storage_adapters[f"dps:{LOSSY_UID}"]

    dps_source = next(
        record
        for record in lossy_dps.records()
        if str(record.pal.OwnerPlayerUId) == MINT_UID
    )
    gps_source = manager.create_pal("global-palbox", "global-palbox")
    world_source = next(
        record
        for record in manager.records_for_roster(LOSSY_UID)
        if record.storage_kind == "world"
        and record.storage_key is not None
    )

    dps_clone = manager.duplicate_pal(dps_source.record_key, LOSSY_UID)
    gps_clone = manager.duplicate_pal(gps_source.record_key, "global-palbox")
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
    assert manager.save(str(manager.file_path)) is True

    SaveManager._instance = None
    reopened = SaveManager()
    assert reopened.open(str(manager.file_path)) is not None
    for record_key, instance_id in zip(clone_keys, clone_ids):
        record = reopened.get_record(record_key)
        assert record is not None
        assert str(record.pal.InstanceId) == instance_id


def test_base_worker_creation_targets_and_create(tmp_path):
    manager = open_copied_world(tmp_path)
    base_targets = manager.storage_directory.creation_targets("base-workers")
    assert base_targets
    base_key = base_targets[0]["StorageKey"]

    created = manager.create_pal("base-workers", base_key)

    assert created.storage_kind == "world"
    assert created.pal.OwnerPlayerUId is None
    assert created in manager.records_for_roster("base-workers")
    assert manager.get_record(created.record_key) is created

    assert manager.save(str(manager.file_path)) is True
    SaveManager._instance = None
    reopened = SaveManager()
    assert reopened.open(str(manager.file_path)) is not None
    persisted = reopened.get_record(created.record_key)
    assert persisted is not None
    assert str(persisted.pal.InstanceId) == str(created.pal.InstanceId)


def test_base_worker_duplicate_produces_a_fresh_base_pal(tmp_path):
    manager = open_copied_world(tmp_path)
    base_records = [
        record
        for record in manager.records_for_roster("base-workers")
        if record.storage_key is not None
    ]
    assert base_records
    source = base_records[0]

    clone = manager.duplicate_pal(source.record_key, "base-workers")

    assert clone.pal.InstanceId != source.pal.InstanceId
    assert clone.pal.OwnerPlayerUId is None
    assert clone.storage_kind == "world"
    assert clone in manager.records_for_roster("base-workers")
    assert manager.get_record(clone.record_key) is clone
