import copy
from pathlib import Path
import unittest

from palworld_pal_editor.api.pals import pal_detail
from palworld_pal_editor.core.pal_entity import PalEntity
from palworld_pal_editor.core.save_manager import SaveManager


SAVE = (
    Path(__file__).parents[1]
    / "tests/saves/1.0/8C439FF04713B5F986F9CAB485575089"
)


class PalUpgradeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manager = SaveManager()
        if cls.manager.open(str(SAVE)) is None:
            raise AssertionError("1.0 fixture failed to load")
        cls.records = [
            record
            for player in cls.manager.get_players()
            for record in cls.manager.records_for_roster(player.PlayerUId)
        ] + cls.manager.working_records()
        cls.pals = [record.pal for record in cls.records]

    def test_level_80_assignment_preserves_existing_exp(self):
        self.assertEqual(80, PalEntity.MAX_LEVEL)
        pal = next(
            item for item in self.pals if item.Level == 80 and item.Exp == 637_561_014
        )
        original = copy.deepcopy(pal.pal_param)
        try:
            pal.Level = pal.Level
            self.assertEqual(637_561_014, pal.Exp)
        finally:
            pal.pal_param.clear()
            pal.pal_param.update(original)

    def test_rank_change_clears_hidden_condensation_progress(self):
        record = next(
            item
            for item in self.records
            if str(item.pal.InstanceId) == "cfab9a78-49bd-bf16-474f-6e83eee20d7a"
        )
        pal = record.pal
        original = copy.deepcopy(pal.pal_param)
        try:
            self.assertEqual((3, 9), (pal.Rank, pal.RankUpExp))
            self.assertTrue(pal.IsAwakening)
            self.assertEqual(9, pal_detail(self.manager, record)["RankUpExp"])

            pal.Rank = 3
            self.assertEqual(9, pal.RankUpExp)
            pal.Rank = 2
            self.assertEqual(0, pal.RankUpExp)
            self.assertNotIn("RankUpExp", pal.pal_param)
        finally:
            pal.pal_param.clear()
            pal.pal_param.update(original)

    def test_skin_edit_keeps_applier_guid_in_sync(self):
        pal = next(
            item
            for item in self.pals
            if item.DataAccessKey == "GrassBoss"
            and item.SkinName == "GrassBoss_Skin001"
        )
        original = copy.deepcopy(pal.pal_param)
        try:
            self.assertEqual(pal.OwnerPlayerUId, pal.SkinAppliedCharacterId)
            pal.SkinName = None
            self.assertNotIn("SkinName", pal.pal_param)
            self.assertNotIn("SkinAppliedCharacterId", pal.pal_param)
            pal.SkinName = "GrassBoss_Skin001"
            self.assertEqual(pal.OwnerPlayerUId, pal.SkinAppliedCharacterId)
        finally:
            pal.pal_param.clear()
            pal.pal_param.update(original)

    def test_base_worker_skin_uses_last_owner(self):
        pal = next(
            item
            for item in self.manager.get_working_pals()
            if item.RawSpecieKey == "Anubis" and item.OwnerPlayerUId is None
        )
        original = copy.deepcopy(pal.pal_param)
        try:
            self.assertIsNotNone(pal.LastOwnerPlayerUId)
            pal.SkinName = "Anubis_Skin001"
            self.assertEqual(pal.LastOwnerPlayerUId, pal.SkinAppliedCharacterId)
        finally:
            pal.pal_param.clear()
            pal.pal_param.update(original)


if __name__ == "__main__":
    unittest.main()
