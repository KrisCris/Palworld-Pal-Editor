from pathlib import Path
import unittest

from palworld_pal_editor.api.pal_serializers import pal_detail
from palworld_pal_editor.core.pal_entity import condensation_work_suitability_bonus
from palworld_pal_editor.core.pal_objects import PalSuitability
from palworld_pal_editor.core.save_manager import SaveManager


SAVE = (
    Path(__file__).parents[1]
    / "tests/saves/1.0/8C439FF04713B5F986F9CAB485575089"
)


class CondensationSuitabilityTests(unittest.TestCase):
    def test_rank_targets_best_then_lower_distinct_work_levels(self):
        suit = PalSuitability
        cases = (
            (
                {suit.Seeding.value: 2, suit.MonsterFarm.value: 1},
                5,
                suit.MonsterFarm.value,
                {suit.Seeding.value: 1, suit.MonsterFarm.value: 4},
            ),
            (
                {
                    suit.Seeding.value: 4,
                    suit.Handcraft.value: 4,
                    suit.Collection.value: 4,
                    suit.Deforest.value: 3,
                    suit.ProductMedicine.value: 4,
                },
                4,
                suit.Seeding.value,
                {
                    suit.Seeding.value: 1,
                    suit.Handcraft.value: 1,
                    suit.Collection.value: 0,
                    suit.Deforest.value: 1,
                    suit.ProductMedicine.value: 0,
                },
            ),
            (
                {suit.Mining.value: 7, suit.Handcraft.value: 3},
                5,
                suit.Mining.value,
                {suit.Mining.value: 3, suit.Handcraft.value: 2},
            ),
        )
        for base, rank, best, expected in cases:
            with self.subTest(base=base, rank=rank):
                self.assertEqual(
                    expected, condensation_work_suitability_bonus(base, rank, best)
                )

    def test_oil_and_missing_best_follow_native_selection_rules(self):
        suit = PalSuitability
        base = {
            suit.Mining.value: 3,
            suit.OilExtraction.value: 2,
            suit.Transport.value: 1,
        }
        self.assertEqual(
            {
                suit.Mining.value: 2,
                suit.OilExtraction.value: 0,
                suit.Transport.value: 1,
            },
            condensation_work_suitability_bonus(base, 4, suit.Mining.value),
        )
        self.assertEqual(
            {suit.Watering.value: 0, suit.Mining.value: 1},
            condensation_work_suitability_bonus(
                {suit.Watering.value: 4, suit.Mining.value: 2}, 4, None
            ),
        )

    def test_payload_separates_condensation_minimum_from_manual_bonus(self):
        manager = SaveManager()
        self.assertIsNotNone(manager.open(str(SAVE)))
        records = [
            record
            for player in manager.get_players()
            for record in manager.rosters.records_for_roster(player.PlayerUId)
        ] + manager.rosters.working_records()
        record = next(
            item
            for item in records
            if item.pal.Rank == 5
            and item.pal.MinimumWorkSuitabilities
            and item.pal.WorkSuitabilities
        )
        pal = record.pal
        payload = pal_detail(manager, record)
        self.assertEqual(pal.MinimumWorkSuitabilities, payload["SuitabilityMinimums"])
        self.assertTrue(
            all(0 < value <= 10 for value in payload["Suitabilities"].values())
        )


if __name__ == "__main__":
    unittest.main()
