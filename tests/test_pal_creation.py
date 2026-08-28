import copy
import unittest

from palworld_pal_editor.core.group_data import PalGroup
from palworld_pal_editor.core.pal_objects import PalObjects, toUUID
from palworld_pal_editor.core.pal_repository import PalRepository
from palworld_pal_editor.core.pal_storage_adapters import WorldPalAdapter
from palworld_pal_editor.core.player_repository import PlayerRepository
from palworld_pal_editor.core.save_manager import SaveManager


TARGET_PLAYER = toUUID("11111111-1111-1111-1111-111111111111")
TARGET_GROUP = toUUID("22222222-2222-2222-2222-222222222222")
TARGET_CONTAINER = toUUID("33333333-3333-3333-3333-333333333333")
SOURCE_PLAYER = toUUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
SOURCE_GROUP = toUUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
SOURCE_CONTAINER = toUUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


class FakeContainer:
    def __init__(self):
        self.ID = TARGET_CONTAINER
        self.pals = []

    def get_empty_slot(self):
        return 7

    def add_pal(self, pal_id):
        if pal_id in self.pals:
            return -1
        self.pals.append(pal_id)
        return 7

    def del_pal(self, pal_id):
        self.pals.remove(pal_id)

    def has_pal(self, pal_id):
        return pal_id in self.pals


class FakeGroup:
    def __init__(self):
        self.pals = []

    def add_pal(self, pal_id):
        if pal_id in self.pals:
            return False
        self.pals.append(pal_id)
        return True

    def del_pal(self, pal_id):
        self.pals.remove(pal_id)

    def has_pal(self, pal_id):
        return pal_id in self.pals


class FakePlayer:
    NickName = "Target"
    PlayerUId = TARGET_PLAYER
    group_id = TARGET_GROUP
    OtomoCharacterContainerId = toUUID("44444444-4444-4444-4444-444444444444")
    PalStorageContainerId = TARGET_CONTAINER

    def __init__(self):
        self.pals = {}

    def add_pal(self, pal):
        key = str(pal.InstanceId)
        if key in self.pals:
            return False
        self.pals[key] = pal
        pal.set_owner_player_entity(self)
        return True


class FakeContainerData:
    def __init__(self, container):
        self.container = container

    def get_container(self, container_id):
        return self.container if container_id == self.container.ID else None


class FakeGroupData:
    def __init__(self, group):
        self.group = group

    def get_group(self, group_id):
        return self.group if group_id == TARGET_GROUP else None


def manager_fixture():
    manager = object.__new__(SaveManager)
    player = FakePlayer()
    container = FakeContainer()
    group = FakeGroup()
    manager.players = PlayerRepository()
    manager.players.register(player)
    manager.pal_repository = PalRepository()
    manager.container_data = FakeContainerData(container)
    manager.group_data = FakeGroupData(group)
    manager._entities_list = []
    manager.world_adapter = WorldPalAdapter(
        manager._entities_list, manager.container_data
    )
    SaveManager._instance = manager
    return manager, player, container, group


class PalCreationTests(unittest.TestCase):
    def setUp(self):
        self.previous_manager = SaveManager._instance

    def tearDown(self):
        SaveManager._instance = self.previous_manager

    def test_default_pal_has_no_placeholder_nickname(self):
        manager, _, _, _ = manager_fixture()

        record = manager.add_pal(TARGET_PLAYER)

        self.assertIsNone(record.pal.NickName)
        self.assertTrue(record.pal.is_new_pal)

    def test_cloned_pal_keeps_traits_but_rewrites_save_identity(self):
        manager, _, _, _ = manager_fixture()
        source = PalObjects.PalSaveParameter(
            toUUID("dddddddd-dddd-dddd-dddd-dddddddddddd"),
            SOURCE_PLAYER,
            SOURCE_CONTAINER,
            2,
            SOURCE_GROUP,
        )
        parameter = source["value"]["RawData"]["value"]["object"]["SaveParameter"]["value"]
        parameter["NickName"] = PalObjects.StrProperty("Keeper")
        parameter["EquipItemContainerId"] = PalObjects.PalContainerId(SOURCE_CONTAINER)
        parameter["MapObjectConcreteInstanceIdAssignedToExpedition"] = PalObjects.Guid(SOURCE_CONTAINER)
        original = copy.deepcopy(source)

        record = manager.add_pal(TARGET_PLAYER, source)
        pal = record.pal

        self.assertEqual("Keeper", pal.NickName)
        self.assertNotEqual(original["key"]["InstanceId"]["value"], pal.InstanceId)
        self.assertEqual(PalObjects.EMPTY_UUID, pal.PlayerUId)
        self.assertEqual(TARGET_PLAYER, pal.OwnerPlayerUId)
        self.assertEqual([TARGET_PLAYER], pal.OldOwnerPlayerUIds)
        self.assertEqual((TARGET_CONTAINER, 7), pal.SlotId)
        self.assertEqual(TARGET_GROUP, record.group_id)
        self.assertNotEqual(
            SOURCE_CONTAINER,
            PalObjects.get_PalContainerId(pal.pal_param["EquipItemContainerId"]),
        )
        self.assertNotIn("MapObjectConcreteInstanceIdAssignedToExpedition", pal.pal_param)
        self.assertEqual(
            TARGET_PLAYER,
            PalObjects.get_BaseType(pal.pal_param["LastNickNameModifierPlayerUid"]),
        )
        self.assertEqual(original, source)

    def test_invalid_import_rolls_back_container_and_group_reservations(self):
        manager, player, container, group = manager_fixture()

        pal = manager.add_pal(TARGET_PLAYER, {"invalid": True})

        self.assertIsNone(pal)
        self.assertEqual([], container.pals)
        self.assertEqual([], group.pals)
        self.assertEqual({}, player.pals)
        self.assertEqual([], manager._entities_list)

    def test_group_lookup_accepts_uuid_objects(self):
        group = object.__new__(PalGroup)
        handle = PalObjects.individual_character_handle_id(TARGET_PLAYER)
        group.instance_map = {str(TARGET_PLAYER): handle}
        group._group_param = {
            "guild_name": "Test",
            "individual_character_handle_ids": [handle],
        }

        self.assertTrue(group.has_pal(TARGET_PLAYER))
        group.del_pal(TARGET_PLAYER)
        self.assertFalse(group.has_pal(TARGET_PLAYER))


if __name__ == "__main__":
    unittest.main()
