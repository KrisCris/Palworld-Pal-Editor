import unittest
import tempfile
from pathlib import Path

from palworld_pal_editor.core.save_manager import SaveManager


FIXTURE = Path(
    "tests/saves/1.0/8C439FF04713B5F986F9CAB485575089"
).resolve()


class PalContainerRegistryFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous_manager = SaveManager._instance
        SaveManager._instance = None
        cls.manager = SaveManager()
        if cls.manager.open(str(FIXTURE)) is None:
            raise RuntimeError("Failed to load Palworld 1.0 fixture")

    @classmethod
    def tearDownClass(cls):
        SaveManager._instance = cls.previous_manager

    def test_registry_classifies_players_bases_and_unknown_without_capacity_guessing(self):
        descriptors = self.manager.get_container_registry()
        by_kind = {}
        for descriptor in descriptors:
            by_kind.setdefault(descriptor["ContainerKind"], []).append(descriptor)

        self.assertEqual(2, len(by_kind["party"]))
        self.assertEqual(2, len(by_kind["storage"]))
        self.assertEqual(3, len(by_kind["base"]))
        self.assertEqual(1, len(by_kind["unknown"]))
        self.assertNotIn("special", by_kind)

        bases = sorted(by_kind["base"], key=lambda item: item["Occupied"])
        self.assertEqual([3, 36, 44], [item["Occupied"] for item in bases])
        self.assertTrue(all(item["MovableInto"] for item in bases))
        base_by_ordinal = {
            item["BaseOrdinal"]: item
            for item in by_kind["base"]
        }
        self.assertEqual({1, 2, 3}, set(base_by_ordinal))
        self.assertEqual(
            ["Base 1", "Base 2", "Base 3"],
            [base_by_ordinal[index]["ContainerLabel"] for index in (1, 2, 3)],
        )
        self.assertEqual(10, by_kind["unknown"][0]["Size"])
        self.assertFalse(by_kind["unknown"][0]["MovableInto"])
        self.assertEqual("unknown", by_kind["unknown"][0]["Classification"])

    def test_fixture_pals_have_one_matching_physical_slot(self):
        pals = [
            *self.manager.get_working_pals(),
            *(pal for player in self.manager.get_players() for pal in player.get_pals()),
        ]

        statuses = [self.manager.resolve_pal_location(pal)["LocationStatus"] for pal in pals]

        self.assertGreater(len(statuses), 900)
        self.assertEqual({"ok"}, set(statuses))

    def test_base_pals_resolve_to_each_registered_base_container(self):
        counts = {}
        for pal in self.manager.get_working_pals():
            location = self.manager.resolve_pal_location(pal)
            counts[location["ActualContainerId"]] = counts.get(
                location["ActualContainerId"], 0
            ) + 1

        self.assertEqual([3, 36, 44], sorted(counts.values()))

    def test_duplicate_template_names_use_the_base_save_data_order(self):
        camps = list(self.manager.camp_data.get_camps())
        group = self.manager.group_data.get_group(camps[0].owner_group_id)
        original_base_ids = group._group_param["base_ids"]
        original_names = [camp._camp_param.get("name") for camp in camps]
        original_cache = getattr(self.manager, "_container_registry_cache", None)

        try:
            group._group_param["base_ids"] = [camp.id for camp in reversed(camps)]
            for camp in camps:
                camp._camp_param["name"] = "新規生成拠点テンプレート名2(仮)"
            self.manager._container_registry_cache = None

            descriptors = {
                item["BaseId"]: item
                for item in self.manager.get_container_registry()
                if item["ContainerKind"] == "base"
            }

            self.assertEqual(
                [1, 2, 3],
                [descriptors[str(camp.id)]["BaseOrdinal"] for camp in camps],
            )
        finally:
            group._group_param["base_ids"] = original_base_ids
            for camp, name in zip(camps, original_names):
                camp._camp_param["name"] = name
            self.manager._container_registry_cache = original_cache


class PalContainerRoundTripTests(unittest.TestCase):
    def test_moved_pal_serializes_and_reloads_in_the_same_slot(self):
        previous_manager = SaveManager._instance
        try:
            SaveManager._instance = None
            manager = SaveManager()
            self.assertIsNotNone(manager.open(str(FIXTURE)))
            player = next(
                player
                for player in manager.get_players()
                if len(manager.container_data.get_container(player.OtomoCharacterContainerId).slots)
                < manager.container_data.get_container(player.OtomoCharacterContainerId).size
            )
            pal = next(
                pal
                for pal in player.get_pals()
                if str(pal.ContainerId) == str(player.PalStorageContainerId)
            )
            pal_id = str(pal.InstanceId)
            player_id = str(player.PlayerUId)
            target_id = str(player.OtomoCharacterContainerId)

            self.assertTrue(manager.move_pal(pal_id, target_id))
            expected_slot = pal.SlotIndex

            with tempfile.TemporaryDirectory() as directory:
                output = Path(directory, "world")
                output.mkdir()
                self.assertTrue(manager.save(str(output)))

                SaveManager._instance = None
                reloaded = SaveManager()
                self.assertIsNotNone(reloaded.open(str(output)))
                reloaded_pal = reloaded.get_player(player_id).get_pal(pal_id)
                self.assertEqual(target_id, str(reloaded_pal.ContainerId))
                self.assertEqual(expected_slot, reloaded_pal.SlotIndex)
                location = reloaded.resolve_pal_location(reloaded_pal)
                self.assertEqual("ok", location["LocationStatus"])
        finally:
            SaveManager._instance = previous_manager


if __name__ == "__main__":
    unittest.main()
