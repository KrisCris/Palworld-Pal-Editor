"""Moving a Pal: the capability, the three executors, and the rollback (spec §7, §8.2).

A transfer is the one operation that writes into several native structures at once --
a container's slots, a guild's membership handles, the world's character array, a DPS
file and the locker -- and every one of them has to end up agreeing. So these run
against a copy of the real save and check the whole set, not the return value.

The four rules they exist for:

- a relocate leaves exactly one Pal, and it is the same `PalRecord` object it was
  before, because `_created_records` holds these by identity;
- the capability the move dialog reads and the transfer that follows never disagree;
- overwriting an existing Pal asks first, and the Pal that survives keeps its own
  position, owner and provenance;
- a commit that fails part way leaves a save the game can still read.
"""

import copy

import pytest
from flask_jwt_extended import create_access_token

from palworld_pal_editor.core.pal_objects import PalObjects
from palworld_pal_editor.core.pal_transactions import PalOperationRefused
from palworld_pal_editor.core.pal_repository import PalRepository
from palworld_pal_editor.core.pal_storage_adapters import WorldPalAdapter
from palworld_pal_editor.webui import app
from world_fixture import (
    GPS_FIXTURE,
    LOSSY_UID,
    MINT_UID,
    TIGEREST_UID,
    locker_ids,
    open_world,
)


def storage_key_of(manager, player_uid, container="box") -> str:
    player = manager.get_player(player_uid)
    return WorldPalAdapter.storage_key(
        player.PalStorageContainerId if container == "box"
        else player.OtomoCharacterContainerId
    )


def a_movable_pal(manager, storage_key):
    """The first Pal in a storage that is actually free to be moved.

    An expedition Pal is refused by every relocate, so picking one would test the
    refusal rather than the move.
    """
    return next(
        record
        for record in manager.pal_repository.records_for_storage(storage_key)
        if not record.pal.IsExpeditionPal
    )


def guild_of(manager, uid):
    return manager.group_data.get_group(manager.get_player(uid).group_id)


def client():
    app.config["JWT_SECRET_KEY"] = "test-secret-key-with-at-least-32-bytes"
    with app.app_context():
        token = create_access_token(identity="test", expires_delta=False)
    return app.test_client(), {"Authorization": f"Bearer {token}"}


def transfer(payload, expect=200):
    api, headers = client()
    response = api.post("/api/pal-transfers", json=payload, headers=headers)
    assert response.status_code == expect, response.get_json()
    return response.get_json()


def test_a_move_between_containers_keeps_one_pal_and_one_record(tmp_path):
    manager = open_world(tmp_path)
    source_key = storage_key_of(manager, LOSSY_UID)
    target_key = storage_key_of(manager, MINT_UID, "party")
    record = a_movable_pal(manager, source_key)
    instance_id = record.pal.InstanceId
    guild = guild_of(manager, LOSSY_UID)
    entity_count = len(manager._entities_list)
    handle_count = len(guild.individual_character_handle_ids)

    capability = manager.pal_mutations.capability(record.record_key, target_key)
    assert (capability.allowed, capability.effect) == (True, "relocate")
    outcome = manager.pal_mutations.transfer(record.record_key, target_key)

    # The same object, so a Pal created this session and then moved still settles
    # its capture count when the save is written (spec §4.3).
    assert outcome.record is record
    assert manager.get_record(record.record_key) is record
    assert record.record_key == f"world:{instance_id}"
    assert record.storage_key == target_key
    # World to World does not touch the character array or the guild at all: the
    # Pal was already in both, and is in both afterwards.
    assert len(manager._entities_list) == entity_count
    assert len(guild.individual_character_handle_ids) == handle_count
    assert guild.has_pal(instance_id)
    assert not manager.container_data.get_container(
        manager.get_player(LOSSY_UID).PalStorageContainerId
    ).has_pal(instance_id)
    assert manager.container_data.get_container(
        manager.get_player(MINT_UID).OtomoCharacterContainerId
    ).has_pal(instance_id)
    # Standing in someone else's party makes the Pal theirs, and its history says so.
    assert str(record.pal.OwnerPlayerUId) == MINT_UID
    assert str(record.pal.OldOwnerPlayerUIds[-1]) == MINT_UID
    assert record.pal.SlotId == (
        manager.get_player(MINT_UID).OtomoCharacterContainerId,
        record.slot_index,
    )
    assert manager.pal_repository.is_modified(record)


def test_a_move_out_to_a_dps_and_back_is_one_pal_the_whole_time(tmp_path):
    manager = open_world(tmp_path)
    world_key = storage_key_of(manager, LOSSY_UID)
    dps_key = f"dps:{MINT_UID}"
    record = a_movable_pal(manager, world_key)
    instance_id = str(record.pal.InstanceId)
    world_record_key = record.record_key
    guild = guild_of(manager, LOSSY_UID)
    entity_count = len(manager._entities_list)

    outcome = manager.pal_mutations.transfer(record.record_key, dps_key)

    assert outcome.record is record
    assert record.storage_kind == "dps"
    assert record.record_key.startswith(f"{dps_key}:")
    assert manager.get_record(world_record_key) is None
    assert outcome.deleted_record_keys == [world_record_key]
    assert set(outcome.affected_storage_keys) == {world_key, dps_key}
    # A Pal held outside the world save leaves its container and its guild, and the
    # locker is what tells the game it is being held rather than missing.
    assert len(manager._entities_list) == entity_count - 1
    assert not guild.has_pal(instance_id)
    assert not manager.container_data.get_container(
        manager.get_player(LOSSY_UID).PalStorageContainerId
    ).has_pal(instance_id)
    assert instance_id in locker_ids(manager)
    # A DPS is a place, not a person: whose Pal it is does not change (spec §7).
    assert str(record.pal.OwnerPlayerUId) == LOSSY_UID

    back = manager.pal_mutations.transfer(record.record_key, world_key)

    assert back.record is record
    assert record.record_key == f"world:{instance_id}"
    assert record.storage_kind == "world"
    assert len(manager._entities_list) == entity_count
    assert guild.has_pal(instance_id)
    assert instance_id not in locker_ids(manager)
    assert manager.storage_adapters[dps_key].get(back.deleted_record_keys[0]) is None


def test_a_pal_that_is_not_in_the_slot_it_records_can_go_nowhere(tmp_path):
    """The container location anomaly, as an ordinary refusal (spec §8.2)."""
    manager = open_world(tmp_path)
    record = a_movable_pal(manager, storage_key_of(manager, LOSSY_UID))
    # What the load path leaves behind for a Pal whose recorded ContainerId and
    # SlotIndex do not resolve to a slot holding it.
    record.storage_key = None
    record.slot_index = None

    capability = manager.pal_mutations.capability(
        record.record_key, storage_key_of(manager, MINT_UID, "party")
    )
    assert capability.allowed is False
    assert capability.effect is None
    assert capability.reason == "SOURCE_LOCATION_ANOMALY"

    error = transfer(
        {
            "sourceRecordKey": record.record_key,
            "targetStorageKey": storage_key_of(manager, MINT_UID, "party"),
        },
        expect=409,
    )
    assert error["error"]["code"] == "SOURCE_LOCATION_ANOMALY"


@pytest.mark.parametrize(
    "target, reason",
    [
        ("own-box", "ALREADY_IN_TARGET"),
        ("full-party", "TARGET_FULL"),
        ("other-guild", "CROSS_GUILD_UNSUPPORTED"),
    ],
)
def test_a_target_the_move_dialog_must_grey_out_says_why(tmp_path, target, reason):
    manager = open_world(tmp_path)
    record = a_movable_pal(manager, storage_key_of(manager, LOSSY_UID))
    target_key = {
        "own-box": storage_key_of(manager, LOSSY_UID),
        # LossyBytes' own party is full in this save.
        "full-party": storage_key_of(manager, LOSSY_UID, "party"),
        # Tigerest is the one player in another guild.
        "other-guild": storage_key_of(manager, TIGEREST_UID),
    }[target]

    capability = manager.pal_mutations.capability(record.record_key, target_key)
    assert (capability.allowed, capability.reason) == (False, reason)
    with pytest.raises(PalOperationRefused) as refusal:
        manager.pal_mutations.transfer(record.record_key, target_key)
    assert refusal.value.code == reason


def test_a_copy_into_the_global_palbox_keeps_the_source_and_strips_its_position(
    tmp_path,
):
    manager = open_world(tmp_path, global_palbox=GPS_FIXTURE)
    record = a_movable_pal(manager, storage_key_of(manager, LOSSY_UID))
    provenance = list(record.pal.OldOwnerPlayerUIds or [])
    slot = record.pal.SlotId

    capability = manager.pal_mutations.capability(record.record_key, "global-palbox")
    assert (capability.allowed, capability.effect) == (True, "replicate")
    outcome = manager.pal_mutations.transfer(record.record_key, "global-palbox")

    assert outcome.record is not record
    assert manager.get_record(record.record_key) is record
    assert outcome.record.storage_kind == "global_palbox"
    # Same Pal, and the Global Palbox is where it is being kept rather than who
    # owns it -- so identity and provenance survive and the owner does not.
    assert outcome.record.pal.InstanceId == record.pal.InstanceId
    assert outcome.record.pal.OwnerPlayerUId == PalObjects.EMPTY_UUID
    assert outcome.record.pal.OldOwnerPlayerUIds == provenance
    assert outcome.record.pal.SlotId == slot
    assert outcome.record.pal.IsImportedCharacter is True
    assert manager.pal_repository.is_created(outcome.record)
    # A copy is not a Pal being held elsewhere; only the original is anywhere.
    assert str(outcome.record.pal.InstanceId) not in locker_ids(manager)


def test_bringing_a_copy_back_asks_first_and_then_leaves_the_target_where_it_is(
    tmp_path,
):
    manager = open_world(tmp_path, global_palbox=GPS_FIXTURE)
    local = a_movable_pal(manager, storage_key_of(manager, LOSSY_UID))
    copy_record = manager.pal_mutations.transfer(
        local.record_key, "global-palbox"
    ).record
    local_nickname = local.pal.NickName or ""
    copy_record.pal.NickName = "Came back changed"
    target_key = storage_key_of(manager, MINT_UID, "party")
    local_slot = local.pal.SlotId
    local_owner = local.pal.OwnerPlayerUId
    local_provenance = copy.deepcopy(local.pal.pal_param.get("OldOwnerPlayerUIds"))

    # The identity is in two places now, so the same target that was a copy is an
    # overwrite -- which is why the dialog asks the backend rather than the kind.
    capability = manager.pal_mutations.capability(copy_record.record_key, target_key)
    assert (capability.allowed, capability.effect) == (True, "update-existing")

    request = {
        "sourceRecordKey": copy_record.record_key,
        "targetStorageKey": target_key,
    }
    conflict = transfer(request, expect=409)["error"]
    assert conflict["code"] == "PAL_IDENTITY_CONFLICT"
    assert [item["recordKey"] for item in conflict["details"]["candidates"]] == [
        local.record_key
    ]
    assert conflict["details"]["existing"]["NickName"] == local_nickname
    assert conflict["details"]["fieldChanges"]["NickName"] == {
        "Incoming": "Came back changed",
        "Existing": local_nickname,
    }

    result = transfer(
        {
            **request,
            "conflictResolution": {
                "kind": "update-existing",
                "expectedTarget": {
                    "recordKey": local.record_key,
                    "storageKey": local.storage_key,
                },
            },
        }
    )

    # The Pal that survives is the one that was already there: it takes the payload
    # and keeps everything about where it is standing and whose it is.
    assert result["resultRecord"]["recordKey"] == local.record_key
    assert result["deletedRecordKeys"] == []
    assert result["resultRecord"]["changeState"] == "modified"
    assert local.pal.NickName == "Came back changed"
    assert local.pal.SlotId == local_slot
    assert local.pal.OwnerPlayerUId == local_owner
    assert local.pal.pal_param.get("OldOwnerPlayerUIds") == local_provenance
    assert manager.get_record(copy_record.record_key) is copy_record


def test_a_confirmation_for_a_target_that_has_since_moved_is_refused(tmp_path):
    manager = open_world(tmp_path, global_palbox=GPS_FIXTURE)
    local = a_movable_pal(manager, storage_key_of(manager, LOSSY_UID))
    nickname = local.pal.NickName
    copy_record = manager.pal_mutations.transfer(
        local.record_key, "global-palbox"
    ).record
    copy_record.pal.NickName = "Should not land"

    conflict = transfer(
        {
            "sourceRecordKey": copy_record.record_key,
            "targetStorageKey": storage_key_of(manager, MINT_UID, "party"),
            "conflictResolution": {
                "kind": "update-existing",
                "expectedTarget": {
                    "recordKey": local.record_key,
                    # Where the user was shown it, if they had been shown it there.
                    "storageKey": f"dps:{MINT_UID}",
                },
            },
        },
        expect=409,
    )["error"]

    assert conflict["code"] == "PAL_IDENTITY_CONFLICT"
    assert local.pal.NickName == nickname


def test_a_commit_that_fails_leaves_the_save_exactly_as_it_was(tmp_path):
    """The safety net under a short commit (spec §7).

    Nothing the save file can do reaches here -- a full target, a stale one and a
    cross-guild move are all answered before an executor starts -- so what this
    stands in for is a bug in the executor itself, half way through five native
    structures. What must survive is a save the game can still read.
    """
    manager = open_world(tmp_path)
    world_key = storage_key_of(manager, LOSSY_UID)
    dps_key = f"dps:{MINT_UID}"
    record = a_movable_pal(manager, world_key)
    instance_id = record.pal.InstanceId
    guild = guild_of(manager, LOSSY_UID)
    storage = manager.storage_adapters[dps_key].storage

    before = {
        "record_key": record.record_key,
        "storage_key": record.storage_key,
        "slot_index": record.slot_index,
        "character": record.pal.CharacterID,
        "entities": len(manager._entities_list),
        "entity_at": manager._entities_list.index(record.native_record),
        "handles": len(guild.individual_character_handle_ids),
        "locker": locker_ids(manager),
        "free_slot": storage.free_index(),
        "dirty": storage.dirty,
        "slots": manager.container_data.get_container(
            record.pal.ContainerId
        ).snapshot_slots(),
    }

    failures = [True]
    original_index = PalRepository._index

    def fail_once(self, indexed):
        if failures:
            failures.pop()
            raise RuntimeError("index is broken")
        return original_index(self, indexed)

    with pytest.raises(RuntimeError):
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(PalRepository, "_index", fail_once)
            manager.pal_mutations.transfer(record.record_key, dps_key)

    # The record is back under its own key with a working binding: the rollback
    # re-reads the Pal out of the restored native record rather than putting back an
    # entity bound to dicts nothing references any more (spec §4.2).
    assert manager.get_record(before["record_key"]) is record
    assert record.storage_kind == "world"
    assert (record.storage_key, record.slot_index) == (
        before["storage_key"],
        before["slot_index"],
    )
    assert record.pal.CharacterID == before["character"]
    assert record.pal.InstanceId == instance_id
    assert manager._entities_list.index(record.native_record) == before["entity_at"]
    assert len(manager._entities_list) == before["entities"]
    assert guild.has_pal(instance_id)
    assert len(guild.individual_character_handle_ids) == before["handles"]
    assert locker_ids(manager) == before["locker"]
    assert storage.free_index() == before["free_slot"]
    assert storage.dirty == before["dirty"]
    assert (
        manager.container_data.get_container(record.pal.ContainerId).snapshot_slots()
        == before["slots"]
    )


def test_the_storage_directory_says_where_each_place_belongs(tmp_path):
    """What the move dialog renders, so it stops deriving labels from storage kinds."""
    manager = open_world(tmp_path, global_palbox=GPS_FIXTURE)
    api, headers = client()
    response = api.get("/api/storages", headers=headers)
    assert response.status_code == 200
    storages = {item["storageKey"]: item for item in response.get_json()}
    assert len(storages) == len(response.get_json())

    global_palbox = storages["global-palbox"]
    assert global_palbox["navigationGroupKey"] == "global-palbox"
    assert global_palbox["navigationGroupOrder"] == 0
    assert global_palbox["navigationGroupLabel"] == global_palbox["label"]

    box = storages[storage_key_of(manager, LOSSY_UID)]
    party = storages[storage_key_of(manager, LOSSY_UID, "party")]
    assert box["navigationGroupKey"] == f"player:{LOSSY_UID}"
    assert box["navigationGroupLabel"] == "LossyBytes"
    assert party["navigationGroupKey"] == box["navigationGroupKey"]
    # A player's party is listed above their palbox, and their DPS below both.
    assert party["order"] < box["order"] < storages[f"dps:{LOSSY_UID}"]["order"]
    assert box["ownerPlayerUid"] == LOSSY_UID
    assert box["capacity"] == 960 and box["occupied"] == 776

    bases = [
        item
        for item in storages.values()
        if item["navigationGroupKey"] == "bases"
    ]
    # A base and a viewing cage belong to nobody, and their group headings are the
    # frontend's own translated text rather than English invented here.
    assert bases and all(item["navigationGroupLabel"] is None for item in bases)
    assert all(item["navigationGroupOrder"] == 1 for item in bases)


def test_capability_refuses_a_target_the_global_palbox_may_not_reach(tmp_path):
    manager = open_world(tmp_path, global_palbox=GPS_FIXTURE)
    # A Global Palbox Pal with no local twin, so the answer is about the target
    # rather than about an identity conflict.
    source = manager.get_record("gps:1")
    assert not [
        record
        for record in manager.records_by_instance(source.pal.InstanceId)
        if record.storage_kind != "global_palbox"
    ]
    api, headers = client()

    base = next(
        descriptor["StorageKey"]
        for descriptor in manager.storage_directory.registry()
        if descriptor["ContainerKind"] == "base"
    )
    response = api.get(
        f"/api/storages/{base}/pal-transfer-capability",
        query_string={"sourceRecordKey": source.record_key},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.get_json() == {
        "allowed": False,
        "effect": None,
        "reason": "GPS_PLAYER_TARGET_REQUIRED",
        "resultRosterKey": None,
    }

    target = storage_key_of(manager, MINT_UID)
    allowed = api.get(
        f"/api/storages/{target}/pal-transfer-capability",
        query_string={"sourceRecordKey": source.record_key},
        headers=headers,
    ).get_json()
    assert allowed == {
        "allowed": True,
        "effect": "replicate",
        "reason": None,
        "resultRosterKey": f"player:{MINT_UID}",
    }
