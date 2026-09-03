"""Creating and deleting a Pal through the one pipeline both now go through.

These are the §7 identity rules, checked against a real save rather than fakes:
what a new Pal inherits from its source, what it takes from where it lands, and
that a payload this editor cannot read leaves no half-written Pal behind. Delete
is here too because it is the same rules read backwards -- a Pal is gone when the
container slot, the guild handle and the record are all gone with it.

`create_pal` is addressed by roster and target storage, `delete_pal` by record
key; neither takes a bare InstanceId any more.
"""

import copy
import shutil
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from palworld_pal_editor.core.group_data import PalGroup
from palworld_pal_editor.core.pal_objects import PalObjects, toUUID
from palworld_pal_editor.core.pal_storage_adapters import WorldPalAdapter
from palworld_pal_editor.core.save_manager import SaveManager


WORLD_FIXTURE = Path(__file__).parents[1] / "tests/saves/1.0/AF518B19A47340B8A55BC58137981393"
OWNER_UID = "a18b721d-0000-0000-0000-000000000000"
SOURCE_CONTAINER = toUUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


class PalCreationTests(unittest.TestCase):
    """Each test opens its own copy: creating and deleting both mutate the save."""

    def setUp(self):
        self.previous_manager = SaveManager._instance
        self.addCleanup(self.restore)
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        world = Path(self._temp.name, "world")
        shutil.copytree(WORLD_FIXTURE, world)

        SaveManager._instance = None
        self.manager = SaveManager()
        self.assertIsNotNone(self.manager.open(str(world)))
        self.player = self.manager.get_player(OWNER_UID)
        self.palbox_id = self.player.PalStorageContainerId
        self.palbox = WorldPalAdapter.storage_key(self.palbox_id)

    def restore(self):
        SaveManager._instance = self.previous_manager

    def container(self):
        return self.manager.container_data.get_container(self.palbox_id)

    def group(self):
        return self.manager.group_data.get_group(self.player.group_id)

    def source_parameter(self) -> dict:
        """A live Pal's complete payload, marked so it can be recognised again."""
        record = next(
            item
            for item in self.manager.records_for_roster(OWNER_UID)
            if item.storage_kind == "world"
        )
        parameter = copy.deepcopy(record.pal.save_parameter)
        fields = parameter["value"]
        fields["NickName"] = PalObjects.StrProperty("Keeper")
        fields["EquipItemContainerId"] = PalObjects.PalContainerId(SOURCE_CONTAINER)
        fields["MapObjectConcreteInstanceIdAssignedToExpedition"] = PalObjects.Guid(
            SOURCE_CONTAINER
        )
        return parameter


    def test_a_failed_world_creation_leaves_container_group_and_entities_untouched(self):
        """The rollback that has to survive `add_pal` and the transfer path merging.

        The two implementations undo a half-made Pal by different means -- one with
        `container_added` / `group_added` flags, one with `TouchedParents` -- and
        only one of them can remain. Whichever it is has to leave all three places
        a world Pal is written exactly as it found them.

        The guild refusing the Pal is the failure to force, because it happens
        after the container slot is taken and after the entity is appended, so a
        rollback that misses any of the three shows up here.
        """
        container = self.container()
        group = self.group()
        before = (
            len(container.slots),
            len(group.individual_character_handle_ids or []),
            len(self.manager._entities_list),
        )

        with unittest.mock.patch.object(PalGroup, "add_pal", return_value=False):
            with self.assertRaises(Exception):
                self.manager.pal_mutations.create(OWNER_UID, self.palbox)

        self.assertEqual(
            (
                len(container.slots),
                len(group.individual_character_handle_ids or []),
                len(self.manager._entities_list),
            ),
            before,
        )

    def test_a_default_pal_is_unnamed_and_counts_as_new_until_the_save_is_written(self):
        record = self.manager.pal_mutations.create(OWNER_UID, self.palbox)

        self.assertIsNone(record.pal.NickName)
        self.assertTrue(self.manager.pal_repository.is_created(record))
        self.assertIs(record, self.manager.get_record(record.record_key))
        # A Pal exists in three places at once, and a create that misses one of
        # them writes a save the game reads as corrupt.
        self.assertTrue(self.container().has_pal(record.pal.InstanceId))
        self.assertTrue(self.group().has_pal(record.pal.InstanceId))
        self.assertIn(record.native_record, self.manager._entities_list)

    def test_a_copy_keeps_the_payload_and_takes_the_targets_identity(self):
        source = self.source_parameter()
        untouched = copy.deepcopy(source)

        record = self.manager.pal_mutations.create(OWNER_UID, self.palbox, source)
        pal = record.pal

        # Everything the source contributes is gameplay, and all of it survives.
        self.assertEqual("Keeper", pal.NickName)
        # Everything else belongs to where it landed.
        self.assertEqual(PalObjects.EMPTY_UUID, pal.PlayerUId)
        self.assertEqual(toUUID(OWNER_UID), pal.OwnerPlayerUId)
        self.assertEqual([toUUID(OWNER_UID)], pal.OldOwnerPlayerUIds)
        self.assertEqual((self.palbox_id, record.slot_index), pal.SlotId)
        self.assertEqual(self.player.group_id, record.group_id)
        self.assertEqual(
            toUUID(OWNER_UID),
            PalObjects.get_BaseType(pal.pal_param["LastNickNameModifierPlayerUid"]),
        )
        # The two things a copy must not inherit: the item container someone else
        # is holding, and an expedition the source is away on.
        self.assertNotEqual(
            SOURCE_CONTAINER,
            PalObjects.get_PalContainerId(pal.pal_param["EquipItemContainerId"]),
        )
        self.assertNotIn(
            "MapObjectConcreteInstanceIdAssignedToExpedition", pal.pal_param
        )
        # The payload is copied out of, never written into: the source Pal a
        # template or a duplicate came from is still whatever it was.
        self.assertEqual(untouched, source)

    def test_a_payload_this_editor_cannot_read_reserves_nothing(self):
        before = (
            len(self.manager.pal_repository.records()),
            len(self.manager._entities_list),
            self.container().get_free_slot_index(),
            len(self.group().instance_map),
        )

        with self.assertRaises(ValueError):
            self.manager.pal_mutations.create(OWNER_UID, self.palbox, {"invalid": True})

        # The slot and the guild handle are claimed before the Pal is built, so a
        # payload that fails halfway has to give both back.
        self.assertEqual(
            before,
            (
                len(self.manager.pal_repository.records()),
                len(self.manager._entities_list),
                self.container().get_free_slot_index(),
                len(self.group().instance_map),
            ),
        )

    def test_deleting_a_pal_gives_back_its_slot_and_its_guild_handle(self):
        record = self.manager.pal_mutations.create(OWNER_UID, self.palbox)
        instance_id = record.pal.InstanceId

        self.assertTrue(self.manager.pal_mutations.delete(record.record_key))

        self.assertIsNone(self.manager.get_record(record.record_key))
        self.assertFalse(self.container().has_pal(instance_id))
        self.assertFalse(self.group().has_pal(instance_id))
        self.assertNotIn(record.native_record, self.manager._entities_list)

    def test_deleting_a_base_worker_takes_it_out_of_the_working_roster(self):
        record = self.manager.working_records()[0]
        instance_id = str(record.pal.InstanceId)

        self.assertTrue(self.manager.pal_mutations.delete(record.record_key))

        # A base worker is not a kind of record, it is a Pal standing in a camp's
        # container -- so removing the record is what empties the roster.
        self.assertNotIn(
            instance_id,
            {str(item.pal.InstanceId) for item in self.manager.working_records()},
        )
        self.assertIsNone(self.manager.get_record(record.record_key))

    def test_a_missing_record_key_deletes_nothing(self):
        self.assertFalse(
            self.manager.pal_mutations.delete("world:00000000-0000-0000-0000-000000000000")
        )


class PalGroupTests(unittest.TestCase):
    def test_a_guild_handle_lookup_accepts_uuid_objects(self):
        """Create and delete both address the guild by a `UUID`, not by its text."""
        pal_id = toUUID("11111111-1111-1111-1111-111111111111")
        group = object.__new__(PalGroup)
        handle = PalObjects.individual_character_handle_id(pal_id)
        group.instance_map = {str(pal_id): handle}
        group._group_param = {
            "guild_name": "Test",
            "individual_character_handle_ids": [handle],
        }

        self.assertTrue(group.has_pal(pal_id))
        group.del_pal(pal_id)
        self.assertFalse(group.has_pal(pal_id))


if __name__ == "__main__":
    unittest.main()
