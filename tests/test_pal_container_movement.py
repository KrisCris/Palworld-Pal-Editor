import copy
import unittest

from palworld_pal_editor.core.basecamp_data import PalBaseCamp
from palworld_pal_editor.core.container_data import PalContainer
from palworld_pal_editor.core.pal_objects import PalObjects, toUUID
from palworld_pal_editor.core.pal_operations import (
    PalOperationRefused,
    PalOperationService,
    set_owner,
)
from palworld_pal_editor.core.pal_repository import PalRepository
from palworld_pal_editor.core.pal_storage_adapters import WorldPalAdapter
from palworld_pal_editor.core.player_repository import PlayerRepository
from palworld_pal_editor.core.save_manager import SaveManager


CONTAINER_ID = toUUID("11111111-1111-1111-1111-111111111111")
PAL_ID = toUUID("22222222-2222-2222-2222-222222222222")
BASE_ID = toUUID("33333333-3333-3333-3333-333333333333")
GROUP_ID = toUUID("44444444-4444-4444-4444-444444444444")
TARGET_CONTAINER_ID = toUUID("66666666-6666-6666-6666-666666666666")
TARGET_PLAYER_ID = toUUID("77777777-7777-7777-7777-777777777777")


def container_object(size=3, slots=None):
    return {
        "key": {"ID": PalObjects.Guid(CONTAINER_ID)},
        "value": {
            "SlotNum": PalObjects.IntProperty(size),
            "Slots": PalObjects.ArrayProperty(
                "StructProperty", {"values": slots or []}
            ),
        },
    }


class PalContainerMutationTests(unittest.TestCase):
    def test_sparse_add_uses_actual_free_inventory_index(self):
        occupied = PalObjects.ContainerSlotData(1)
        occupied["RawData"]["value"]["instance_id"] = PAL_ID
        container = PalContainer(container_object(slots=[occupied]))

        new_id = toUUID("55555555-5555-5555-5555-555555555555")
        slot_index = container.add_pal(new_id)

        self.assertEqual(0, slot_index)
        self.assertEqual(
            (0, new_id), (container.slots[-1].SlotIndex, container.slots[-1].instance_id)
        )

    def test_transferred_slot_preserves_raw_fields_and_does_not_alias_source(self):
        source_slot = PalObjects.ContainerSlotData(1)
        source_slot["RawData"]["value"].update(
            {"instance_id": PAL_ID, "permission_tribe_id": 17, "unknown_bytes": [1, 2, 3]}
        )
        source = PalContainer(container_object(slots=[source_slot]))
        target_obj = container_object(size=2)
        target_obj["key"]["ID"] = PalObjects.Guid(
            toUUID("66666666-6666-6666-6666-666666666666")
        )
        target = PalContainer(target_obj)

        copied_source = copy.deepcopy(source_slot)
        target_index = target.add_slot_copy(source.get_slot(PAL_ID))

        self.assertEqual(0, target_index)
        self.assertEqual(17, target.slots[0]._slot_raw_data["permission_tribe_id"])
        self.assertEqual([1, 2, 3], target.slots[0]._slot_raw_data["unknown_bytes"])
        target.slots[0]._slot_raw_data["unknown_bytes"].append(4)
        self.assertEqual(copied_source, source_slot)


class BaseCampContainerTests(unittest.TestCase):
    def test_worker_container_comes_from_worker_director_raw_data(self):
        camp = PalBaseCamp(
            {
                "value": {
                    "RawData": {
                        "value": {
                            "id": BASE_ID,
                            "name": "Test Base",
                            "group_id_belong_to": GROUP_ID,
                        }
                    },
                    "WorkerDirector": {
                        "value": {"RawData": {"value": {"container_id": CONTAINER_ID}}}
                    },
                }
            }
        )

        self.assertEqual(CONTAINER_ID, camp.container_id)


class FakePlayer:
    def __init__(self, player_id, group_id, name):
        self.PlayerUId = player_id
        self.group_id = group_id
        self.NickName = name
        self.OtomoCharacterContainerId = None
        self.PalStorageContainerId = None


def as_base_worker(manager, pal, container_id=CONTAINER_ID):
    """Turn the fixture's owned Pal into an ownerless base worker.

    There is no base-worker collection to add it to any more, so this sets up what
    actually makes one: no owner, standing in a container a camp owns.
    """
    set_owner(pal, None)
    manager.camp_data.add_camp(container_id)
    manager.pal_repository.reindex()


def as_shared_cage(manager, container):
    """Make the target the one world container nobody owns: a viewing cage."""
    manager._container_registry_cache[str(container.ID)].update(
        {"Shared": True, "OwnerPlayerUId": None, "GroupId": None}
    )


def unchanged_state(source, target, pal):
    """What a refused transfer must leave exactly as it found it."""
    return (
        copy.deepcopy(source._slots_data),
        copy.deepcopy(target._slots_data),
        copy.deepcopy(pal.pal_param),
    )


def refusal(manager, target):
    """The capability's answer, checked against the transfer that follows it.

    They are the same decision: what the move dialog greys out is what the POST
    would have refused, and a test that asked only one of them could not tell.
    """
    target_key = WorldPalAdapter.storage_key(target.ID)
    capability = manager.pal_operations.capability("world:" + str(PAL_ID), target_key)
    try:
        manager.pal_operations.transfer("world:" + str(PAL_ID), target_key)
    except PalOperationRefused as refused:
        assert refused.code == capability.reason, (refused.code, capability.reason)
    return capability.allowed, capability.reason


def sole_world_record(manager):
    """The record the World adapter yields for this fixture's one Pal.

    Reading it back through a fresh adapter is how the load path decides whether a
    Pal occupies the slot it records, so a test can mutate the containers and ask
    the same question the load asks.
    """
    native = manager.pal_repository.get("world:" + str(PAL_ID)).native_record
    [record] = list(WorldPalAdapter([native], manager.container_data).records())
    return record


def in_roster(manager, roster_key, pal_id):
    """Whether the roster the old UI asks for lists this Pal."""
    return any(
        str(record.pal.InstanceId) == str(pal_id)
        for record in manager.records_for_roster(roster_key)
    )


def rosters_of(manager, pal_id):
    """Every roster listing this Pal -- what the roster dict used to record."""
    keys = ["PAL_BASE_WORKER_BTN", "PAL_OTHER_PAL_BTN"] + [
        str(player.PlayerUId) for player in manager.players.all()
    ]
    return sorted(key for key in keys if in_roster(manager, key, pal_id))


class FakeContainerData:
    def __init__(self, *containers):
        self.container_map = {container.ID: container for container in containers}

    def get_container(self, container_id):
        return next(
            (item for item in self.container_map.values() if str(item.ID) == str(container_id)),
            None,
        )

    def get_containers(self):
        return self.container_map.values()


class FakeGroup:
    def __init__(self):
        self.pals = set()

    def has_pal(self, pal_id):
        return str(pal_id) in self.pals

    def add_pal(self, pal_id):
        if self.has_pal(pal_id):
            return False
        self.pals.add(str(pal_id))
        return True

    def del_pal(self, pal_id):
        self.pals.discard(str(pal_id))


class FakeGroupData:
    def __init__(self, group):
        self.group = group

    def get_group(self, group_id):
        return self.group if str(group_id) == str(GROUP_ID) else None


class FakeCamp:
    def __init__(self, container_id):
        self.container_id = container_id


class FakeCampData:
    def __init__(self, *container_ids):
        self.camps = [FakeCamp(container_id) for container_id in container_ids]

    def add_camp(self, container_id):
        self.camps.append(FakeCamp(container_id))

    def get_camps(self):
        return self.camps


def movement_manager(target_kind="base"):
    source_slot = PalObjects.ContainerSlotData(1)
    source_slot["RawData"]["value"].update(
        {"instance_id": PAL_ID, "permission_tribe_id": 17, "unknown_bytes": [1, 2, 3]}
    )
    source = PalContainer(container_object(size=3, slots=[source_slot]))
    target_obj = container_object(size=3)
    target_obj["key"]["ID"] = PalObjects.Guid(TARGET_CONTAINER_ID)
    occupied = PalObjects.ContainerSlotData(1)
    occupied["RawData"]["value"]["instance_id"] = toUUID(
        "99999999-9999-9999-9999-999999999999"
    )
    target_obj["value"]["Slots"]["value"]["values"] = [occupied]
    target = PalContainer(target_obj)

    source_player = FakePlayer(toUUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"), GROUP_ID, "Source")
    target_player = FakePlayer(TARGET_PLAYER_ID, GROUP_ID, "Target")
    pal_record = WorldPalAdapter.record(
        PalObjects.PalSaveParameter(
            PAL_ID, source_player.PlayerUId, source.ID, 1, GROUP_ID
        ),
        storage_key=WorldPalAdapter.storage_key(source.ID),
        slot_index=1,
        storage_owner_uid=str(source_player.PlayerUId),
    )
    pal = pal_record.pal

    manager = object.__new__(SaveManager)
    manager.players = PlayerRepository()
    manager.players.register(source_player)
    manager.players.register(target_player)
    manager.pal_repository = PalRepository()
    manager.pal_repository.register(pal_record)
    # A "base" target means the target container is some camp's worker container;
    # that is the whole of what makes the Pals inside it base workers.
    manager.camp_data = FakeCampData(
        *([TARGET_CONTAINER_ID] if target_kind == "base" else [])
    )
    manager.container_data = FakeContainerData(source, target)
    manager.world_adapter = WorldPalAdapter([], manager.container_data)
    manager.storage_adapters = {}
    manager._dps_storages = {}
    manager._global_palbox = None
    manager.group_data = FakeGroupData(FakeGroup())
    manager.pal_operations = PalOperationService(manager)
    manager._container_registry_cache = {
        str(source.ID): {
            "ContainerId": str(source.ID),
            "StorageKey": WorldPalAdapter.storage_key(source.ID),
            "StorageKind": "world",
            "ContainerKind": "storage",
            "ContainerLabel": "Source · Palbox",
            "OwnerPlayerUId": str(source_player.PlayerUId),
            "GroupId": str(GROUP_ID),
            "Size": source.size,
            "Occupied": len(source.slots),
            "Classification": "exact",
            "MovableInto": True,
        },
        str(target.ID): {
            "ContainerId": str(target.ID),
            "StorageKey": WorldPalAdapter.storage_key(target.ID),
            "StorageKind": "world",
            "ContainerKind": target_kind,
            "ContainerLabel": "Target",
            "OwnerPlayerUId": str(target_player.PlayerUId) if target_kind != "base" else None,
            "GroupId": str(GROUP_ID),
            "Size": target.size,
            "Occupied": len(target.slots),
            "Classification": "exact",
            "MovableInto": True,
        },
    }
    SaveManager._instance = manager
    return manager, pal, source, target, source_player, target_player


class SaveManagerMovementTests(unittest.TestCase):
    def setUp(self):
        self.previous_manager = SaveManager._instance

    def tearDown(self):
        SaveManager._instance = self.previous_manager

    def test_a_world_record_is_located_only_by_the_slot_it_records(self):
        """Container location validation in full: one container, one slot, one id.

        What the old resolver split into `missing`, `slot_mismatch` and
        `unknown_container` is one answer now -- the record occupies nothing, so it
        gets no storage key. `duplicate` is not looked for at all: finding it needed
        a scan of every container, which is exactly the scan the Pal's own recorded
        position makes unnecessary.
        """
        manager, _, _, _, _, _ = movement_manager()
        self.assertIsNotNone(sole_world_record(manager).storage_key)

        with self.subTest("the recorded container does not exist"):
            manager, pal, _, _, _, _ = movement_manager()
            pal.SlotId = (toUUID("cccccccc-cccc-cccc-cccc-cccccccccccc"), 0)
            self.assertIsNone(sole_world_record(manager).storage_key)

        with self.subTest("the recorded slot is not in the container"):
            manager, _, source, _, _, _ = movement_manager()
            source.del_pal(PAL_ID)
            self.assertIsNone(sole_world_record(manager).storage_key)

        with self.subTest("the recorded slot holds a different Pal"):
            manager, _, source, _, _, _ = movement_manager()
            source.get_slot(PAL_ID).instance_id = toUUID(
                "dddddddd-dddd-dddd-dddd-dddddddddddd"
            )
            self.assertIsNone(sole_world_record(manager).storage_key)

    def test_load_logs_one_warning_per_container_location_anomaly(self):
        """Spec §9: the anomaly is a load log line, and nothing else survives it."""
        manager, _, source, _, _, _ = movement_manager()
        source.del_pal(PAL_ID)
        record = sole_world_record(manager)
        manager.pal_repository = PalRepository()
        manager.pal_repository.register(record)

        with self.assertLogs("Palworld-Pal-Editor", level="WARNING") as captured:
            manager._log_location_anomalies()

        logged = "\n".join(captured.output)
        for field in (
            f"record_key={record.record_key}",
            f"InstanceId={PAL_ID}",
            f"ContainerId={CONTAINER_ID}",
            "SlotIndex=1",
            "container_exists=True",
            "slot_exists=False",
            "slot_instance_id=None",
        ):
            self.assertIn(field, logged)

    def test_a_relocate_into_a_camp_hands_the_pal_over_to_the_camp(self):
        """World to World, into a base's worker container (spec §7).

        Two things settle at once: the Pal stops being anybody's, and the roster
        that lists it becomes the base-worker one. The slot it lands in is a copy of
        the slot it left, so the fields this editor has never heard of travel with
        it instead of being rebuilt from the ones it has.
        """
        manager, pal, source, target, _, _ = movement_manager("base")
        record = manager.get_record("world:" + str(PAL_ID))

        outcome = manager.pal_operations.transfer(
            record.record_key, WorldPalAdapter.storage_key(target.ID)
        )

        # A relocate is the same Pal in a new place: one record, still this one.
        self.assertIs(record, outcome.record)
        self.assertEqual([], outcome.deleted_record_keys)
        self.assertEqual((TARGET_CONTAINER_ID, 0), pal.SlotId)
        self.assertIsNone(pal.OwnerPlayerUId)
        self.assertEqual(["PAL_BASE_WORKER_BTN"], rosters_of(manager, PAL_ID))
        self.assertFalse(source.has_pal(PAL_ID))
        self.assertTrue(target.has_pal(PAL_ID))
        slot = target.get_slot(PAL_ID)
        self.assertEqual(17, slot._slot_raw_data["permission_tribe_id"])
        self.assertEqual([1, 2, 3], slot._slot_raw_data["unknown_bytes"])

    def test_a_relocate_into_a_players_container_hands_the_pal_over(self):
        """The target container's owner wins, whoever the Pal belonged to before.

        Ownership settles once, current owner and history together, so a Pal that
        arrives in someone's Palbox is theirs and says so in its own provenance
        (spec §7.1).
        """
        for source_state in ("an owned Pal", "an ownerless base worker"):
            with self.subTest(source_state):
                manager, pal, _, target, _, _ = movement_manager("storage")
                if source_state == "an ownerless base worker":
                    as_base_worker(manager, pal)

                manager.pal_operations.transfer(
                    "world:" + str(PAL_ID), WorldPalAdapter.storage_key(target.ID)
                )

                self.assertEqual(TARGET_PLAYER_ID, pal.OwnerPlayerUId)
                self.assertEqual(TARGET_PLAYER_ID, pal.OldOwnerPlayerUIds[-1])
                self.assertEqual([str(TARGET_PLAYER_ID)], rosters_of(manager, PAL_ID))

    def test_a_shared_cage_keeps_the_pals_own_owner_and_needs_it_to_have_one(self):
        """A viewing cage is nobody's, so it decides nothing about the Pal in it.

        It has no guild either, which is why it is the one world target a Pal may
        enter without matching guilds: the Pal stays in the guild it was already in.
        An ownerless base worker has no owner to keep, and is refused.
        """
        manager, pal, _, target, source_player, _ = movement_manager("special")
        as_shared_cage(manager, target)

        manager.pal_operations.transfer(
            "world:" + str(PAL_ID), WorldPalAdapter.storage_key(target.ID)
        )

        self.assertEqual(source_player.PlayerUId, pal.OwnerPlayerUId)
        self.assertEqual([str(source_player.PlayerUId)], rosters_of(manager, PAL_ID))

        manager, pal, source, target, _, _ = movement_manager("special")
        as_shared_cage(manager, target)
        as_base_worker(manager, pal)
        before = unchanged_state(source, target, pal)

        self.assertEqual(
            (False, "OWNER_REQUIRED"), refusal(manager, target)
        )
        self.assertEqual(before, unchanged_state(source, target, pal))

    def test_an_expedition_pal_goes_nowhere_and_nothing_moves(self):
        """The one refusal that is about the Pal rather than the target (spec §8.2)."""
        manager, pal, source, target, _, _ = movement_manager("storage")
        pal.pal_param["MapObjectConcreteInstanceIdAssignedToExpedition"] = (
            PalObjects.Guid(CONTAINER_ID)
        )
        before = unchanged_state(source, target, pal)

        self.assertEqual((False, "EXPEDITION_PAL"), refusal(manager, target))
        self.assertEqual(before, unchanged_state(source, target, pal))

    def test_40_slot_world_container_is_a_shared_viewing_cage(self):
        manager, _, source, target, source_player, _ = movement_manager()
        target.size = 40
        source_player.PalStorageContainerId = source.ID
        manager.camp_data = FakeCampData()
        manager._container_registry_cache = None

        descriptor = manager._container_descriptor_map()[str(target.ID)]

        self.assertEqual("special", descriptor["ContainerKind"])
        self.assertEqual("Viewing Cage", descriptor["ContainerLabel"])
        self.assertTrue(descriptor["Shared"])
        self.assertTrue(descriptor["MovableInto"])
        self.assertIsNone(descriptor["OwnerPlayerUId"])

    def test_explicit_base_creation_uses_target_slot_and_clears_expedition(self):
        manager, _, _, target, _, _ = movement_manager()
        manager._entities_list = []
        # What a creation is handed is the payload, not a record: where it used to
        # sit and who used to own it are the target container's to decide.
        template = PalObjects.DefaultPalSaveParameter(
            TARGET_PLAYER_ID, CONTAINER_ID, 2
        )
        template["value"]["MapObjectConcreteInstanceIdAssignedToExpedition"] = (
            PalObjects.Guid(CONTAINER_ID)
        )

        record = manager.add_pal(
            "PAL_BASE_WORKER_BTN", template, target_container_id=target.ID
        )

        self.assertIsNotNone(record)
        pal = record.pal
        self.assertEqual((target.ID, 0), pal.SlotId)
        self.assertIsNone(pal.OwnerPlayerUId)
        self.assertNotIn(
            "MapObjectConcreteInstanceIdAssignedToExpedition", pal.pal_param
        )
        self.assertEqual(
            ["PAL_BASE_WORKER_BTN"], rosters_of(manager, pal.InstanceId)
        )

    def test_default_creation_prefers_an_empty_party_over_pal_storage(self):
        manager, _, party, storage, player, _ = movement_manager("storage")
        party.restore_slots([])
        player.OtomoCharacterContainerId = party.ID
        player.PalStorageContainerId = storage.ID
        manager._entities_list = []

        record = manager.add_pal(player.PlayerUId)

        self.assertIsNotNone(record)
        pal = record.pal
        self.assertEqual((party.ID, 0), pal.SlotId)
        self.assertTrue(party.has_pal(pal.InstanceId))
        self.assertFalse(storage.has_pal(pal.InstanceId))


if __name__ == "__main__":
    unittest.main()
