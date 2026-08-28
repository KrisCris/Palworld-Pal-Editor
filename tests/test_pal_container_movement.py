import copy
import unittest

from palworld_pal_editor.core.basecamp_data import PalBaseCamp
from palworld_pal_editor.core.container_data import PalContainer
from palworld_pal_editor.core.pal_objects import PalObjects, toUUID
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
OTHER_GROUP_ID = toUUID("88888888-8888-8888-8888-888888888888")


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
        self.assertEqual((0, new_id), (container.slots[-1].inv_idx, container.slots[-1].instance_id))

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
        self._palbox = {}
        self._new_palbox = {}

    def get_pal(self, pal_id, disable_warning=False):
        return self._palbox.get(str(pal_id))

    def add_pal(self, pal):
        if str(pal.InstanceId) in self._palbox:
            return False
        self._palbox[str(pal.InstanceId)] = pal
        pal.set_owner_player_entity(self)
        return True

    def pop_pal(self, pal_id):
        self._new_palbox.pop(str(pal_id), None)
        return self._palbox.pop(str(pal_id), None)


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

    def find_pal_slots(self, pal_id):
        return [
            (container, slot)
            for container in self.get_containers()
            for slot in container.slots
            if str(slot.instance_id) == str(pal_id)
        ]


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


class FakeCampData:
    @staticmethod
    def get_camps():
        return []


def movement_manager(target_kind="base", target_group=GROUP_ID):
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
    target_player = FakePlayer(TARGET_PLAYER_ID, target_group, "Target")
    pal_record = WorldPalAdapter.record(
        PalObjects.PalSaveParameter(
            PAL_ID, source_player.PlayerUId, source.ID, 1, GROUP_ID
        ),
        storage_key=WorldPalAdapter.storage_key(source.ID),
        slot_index=1,
        storage_owner_uid=str(source_player.PlayerUId),
    )
    pal = pal_record.pal
    source_player.add_pal(pal)

    manager = object.__new__(SaveManager)
    manager.players = PlayerRepository()
    manager.players.register(source_player)
    manager.players.register(target_player)
    manager.pal_repository = PalRepository()
    manager.pal_repository.register(pal_record)
    manager.baseworker_mapping = {}
    manager._dangling_pals = {}
    manager.container_data = FakeContainerData(source, target)
    manager.world_adapter = WorldPalAdapter([], manager.container_data)
    manager.storage_adapters = {}
    manager._roster_record_keys = {}
    manager._dps_storages = {}
    manager._global_palbox = None
    manager._container_registry_cache = {
        str(source.ID): {
            "ContainerId": str(source.ID),
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
            "ContainerKind": target_kind,
            "ContainerLabel": "Target",
            "OwnerPlayerUId": str(target_player.PlayerUId) if target_kind != "base" else None,
            "GroupId": str(target_group),
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

    def test_player_to_base_move_uses_sparse_slot_and_removes_current_owner(self):
        manager, pal, source, target, source_player, _ = movement_manager()

        result = manager.move_pal(PAL_ID, TARGET_CONTAINER_ID)

        self.assertTrue(result)
        self.assertEqual((TARGET_CONTAINER_ID, 0), pal.SlotId)
        self.assertIsNone(pal.OwnerPlayerUId)
        self.assertIsNone(source_player.get_pal(PAL_ID))
        self.assertIs(pal, manager.baseworker_mapping[str(PAL_ID)])
        self.assertFalse(source.has_pal(PAL_ID))
        self.assertTrue(target.has_pal(PAL_ID))
        self.assertEqual(17, target.get_slot(PAL_ID)._slot_raw_data["permission_tribe_id"])
        self.assertEqual([1, 2, 3], target.get_slot(PAL_ID)._slot_raw_data["unknown_bytes"])

    def test_location_resolver_reports_every_slot_anomaly(self):
        manager, pal, source, target, _, _ = movement_manager()
        self.assertEqual("ok", manager.resolve_pal_location(pal)["LocationStatus"])

        source.del_pal(PAL_ID)
        self.assertEqual("missing", manager.resolve_pal_location(pal)["LocationStatus"])

        manager, pal, _, _, _, _ = movement_manager()
        pal.SlotId = (TARGET_CONTAINER_ID, 0)
        self.assertEqual(
            "slot_mismatch", manager.resolve_pal_location(pal)["LocationStatus"]
        )

        manager, pal, source, target, _, _ = movement_manager()
        target.add_slot_copy(source.get_slot(PAL_ID))
        self.assertEqual("duplicate", manager.resolve_pal_location(pal)["LocationStatus"])

        manager, pal, _, _, _, _ = movement_manager()
        pal.SlotId = (
            toUUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
            0,
        )
        self.assertEqual(
            "unknown_container", manager.resolve_pal_location(pal)["LocationStatus"]
        )

    def test_player_to_player_move_changes_owner_and_history(self):
        manager, pal, _, _, source_player, target_player = movement_manager("storage")

        self.assertTrue(manager.move_pal(PAL_ID, TARGET_CONTAINER_ID))

        self.assertEqual(TARGET_PLAYER_ID, pal.OwnerPlayerUId)
        self.assertEqual(TARGET_PLAYER_ID, pal.OldOwnerPlayerUIds[-1])
        self.assertIsNone(source_player.get_pal(PAL_ID))
        self.assertIs(pal, target_player.get_pal(PAL_ID))

    def test_move_accepts_a_completely_empty_party_container_and_logs_the_route(self):
        manager, pal, source, target, _, _ = movement_manager("party")
        target.restore_slots([])
        manager._container_registry_cache[str(target.ID)]["Occupied"] = 0

        with self.assertLogs("Palworld-Pal-Editor", level="INFO") as captured:
            result = manager.move_pal(PAL_ID, TARGET_CONTAINER_ID)

        self.assertTrue(result)
        self.assertEqual((TARGET_CONTAINER_ID, 0), pal.SlotId)
        self.assertFalse(source.has_pal(PAL_ID))
        self.assertTrue(target.has_pal(PAL_ID))
        log_text = "\n".join(captured.output)
        self.assertIn(f"pal={PAL_ID}", log_text)
        self.assertIn(f"source={CONTAINER_ID}@1", log_text)
        self.assertIn(f"target={TARGET_CONTAINER_ID}@0", log_text)

    def test_rejected_move_logs_each_target_status_and_reason(self):
        manager, _, _, target, _, _ = movement_manager("storage")
        target.size = 1
        descriptor = manager._container_registry_cache[str(target.ID)]
        descriptor.update({"Size": 1, "Occupied": 1})

        with self.assertLogs("Palworld-Pal-Editor", level="WARNING") as captured:
            with self.assertRaisesRegex(ValueError, "unknown, unsafe, or full"):
                manager.move_pal(PAL_ID, TARGET_CONTAINER_ID)

        log_text = "\n".join(captured.output)
        self.assertIn(f"pal={PAL_ID}", log_text)
        self.assertIn(f"container={TARGET_CONTAINER_ID}", log_text)
        self.assertIn("exists=True", log_text)
        self.assertIn("kind=storage", log_text)
        self.assertIn("occupied=1/1", log_text)
        self.assertIn("movable=True", log_text)
        self.assertIn("reason=Target container is unknown, unsafe, or full.", log_text)

    def test_base_to_player_and_base_to_base_moves_keep_mappings_consistent(self):
        manager, pal, _, _, source_player, target_player = movement_manager("storage")
        source_player.pop_pal(PAL_ID)
        pal.set_owner_player_uid(None)
        manager.baseworker_mapping[str(PAL_ID)] = pal

        self.assertTrue(manager.move_pal(PAL_ID, TARGET_CONTAINER_ID))
        self.assertEqual(TARGET_PLAYER_ID, pal.OwnerPlayerUId)
        self.assertIs(pal, target_player.get_pal(PAL_ID))
        self.assertNotIn(str(PAL_ID), manager.baseworker_mapping)

        manager, pal, _, target, source_player, _ = movement_manager("base")
        source_player.pop_pal(PAL_ID)
        pal.set_owner_player_uid(None)
        manager.baseworker_mapping[str(PAL_ID)] = pal

        self.assertTrue(manager.move_pal(PAL_ID, target.ID))
        self.assertIsNone(pal.OwnerPlayerUId)
        self.assertIs(pal, manager.baseworker_mapping[str(PAL_ID)])

    def test_rejected_expedition_and_cross_guild_moves_are_unchanged(self):
        for expedition, target_group in ((True, GROUP_ID), (False, OTHER_GROUP_ID)):
            with self.subTest(expedition=expedition, target_group=target_group):
                manager, pal, source, target, source_player, _ = movement_manager(
                    "storage", target_group
                )
                if expedition:
                    pal.pal_param["MapObjectConcreteInstanceIdAssignedToExpedition"] = (
                        PalObjects.Guid(CONTAINER_ID)
                    )
                before = (
                    copy.deepcopy(source._slots_data),
                    copy.deepcopy(target._slots_data),
                    copy.deepcopy(pal.pal_param),
                    dict(source_player._palbox),
                )

                with self.assertRaises(ValueError):
                    manager.move_pal(PAL_ID, TARGET_CONTAINER_ID)

                self.assertEqual(before[0], source._slots_data)
                self.assertEqual(before[1], target._slots_data)
                self.assertEqual(before[2], pal.pal_param)
                self.assertEqual(before[3], source_player._palbox)

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

    def test_shared_cage_preserves_player_owner_and_rejects_ownerless_base_pal(self):
        manager, pal, source, target, source_player, _ = movement_manager("special")
        manager._container_registry_cache[str(target.ID)].update(
            {"Shared": True, "OwnerPlayerUId": None, "GroupId": None}
        )

        self.assertTrue(manager.move_pal(PAL_ID, TARGET_CONTAINER_ID))
        self.assertEqual(source_player.PlayerUId, pal.OwnerPlayerUId)
        self.assertIs(pal, source_player.get_pal(PAL_ID))

        manager, pal, source, target, source_player, _ = movement_manager("special")
        manager._container_registry_cache[str(target.ID)].update(
            {"Shared": True, "OwnerPlayerUId": None, "GroupId": None}
        )
        source_player.pop_pal(PAL_ID)
        pal.set_owner_player_uid(None)
        manager.baseworker_mapping[str(PAL_ID)] = pal
        before = (
            copy.deepcopy(source._slots_data),
            copy.deepcopy(target._slots_data),
            copy.deepcopy(pal.pal_param),
        )

        with self.assertRaisesRegex(ValueError, "owner"):
            manager.move_pal(PAL_ID, TARGET_CONTAINER_ID)

        self.assertEqual(before[0], source._slots_data)
        self.assertEqual(before[1], target._slots_data)
        self.assertEqual(before[2], pal.pal_param)

    def test_explicit_base_creation_uses_target_slot_and_clears_expedition(self):
        manager, _, _, target, _, _ = movement_manager()
        manager.group_data = FakeGroupData(FakeGroup())
        manager._entities_list = []
        template = PalObjects.PalSaveParameter(
            toUUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            TARGET_PLAYER_ID,
            CONTAINER_ID,
            2,
            GROUP_ID,
        )
        template["value"]["RawData"]["value"]["object"]["SaveParameter"]["value"][
            "MapObjectConcreteInstanceIdAssignedToExpedition"
        ] = PalObjects.Guid(CONTAINER_ID)

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
        self.assertIs(pal, manager.baseworker_mapping[str(pal.InstanceId)])

    def test_default_creation_prefers_an_empty_party_over_pal_storage(self):
        manager, _, party, storage, player, _ = movement_manager("storage")
        party.restore_slots([])
        player.OtomoCharacterContainerId = party.ID
        player.PalStorageContainerId = storage.ID
        manager.group_data = FakeGroupData(FakeGroup())
        manager._entities_list = []

        record = manager.add_pal(player.PlayerUId)

        self.assertIsNotNone(record)
        pal = record.pal
        self.assertEqual((party.ID, 0), pal.SlotId)
        self.assertTrue(party.has_pal(pal.InstanceId))
        self.assertFalse(storage.has_pal(pal.InstanceId))


if __name__ == "__main__":
    unittest.main()
