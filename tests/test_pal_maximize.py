import unittest

from palworld_pal_editor.core.pal_entity import PalEntity
from palworld_pal_editor.core.pal_objects import PalObjects, toUUID
from palworld_pal_editor.core.pal_record import PalRecord
from fakes import world_record


PLAYER_ID = toUUID("11111111-1111-1111-1111-111111111111")
PAL_ID = toUUID("22222222-2222-2222-2222-222222222222")


def make_record(character_id: str = "SheepBall") -> PalRecord:
    pal_obj = PalObjects.PalSaveParameter(
        PAL_ID,
        PLAYER_ID,
        PalObjects.EMPTY_UUID,
        0,
        PalObjects.EMPTY_UUID,
    )
    parameter = pal_obj["value"]["RawData"]["value"]["object"]["SaveParameter"][
        "value"
    ]
    PalObjects.set_BaseType(parameter["CharacterID"], character_id)
    parameter.pop("OwnerPlayerUId", None)
    record = world_record(pal_obj, storage_key="world-container:test")
    pal = record.pal
    pal.Level = 5
    pal.FriendshipLevel = 1
    pal.Rank = 2
    pal.RankUpExp = 9
    pal.Rank_HP = 1
    pal.Rank_Attack = 2
    pal.Rank_Defence = 3
    pal.Rank_CraftSpeed = 4
    pal.Talent_HP = 10
    pal.Talent_Melee = 17
    pal.Talent_Shot = 20
    pal.Talent_Defense = 30
    return record


class PalMaximizeTests(unittest.TestCase):
    """What maximizing means to a Pal. The resource that offers it is covered by
    `test_rest_pal_writes.py`, on a real save rather than a fake manager."""


    def setUp(self):
        self.record = make_record()
        self.pal = self.record.pal

    def test_maximize_progression_uses_only_normal_gameplay_limits(self):
        original_character_id = self.pal.CharacterID
        original_melee = self.pal.Talent_Melee
        suitability_keys = set(self.pal.MinimumWorkSuitabilities or {})
        self.assertTrue(suitability_keys)

        self.pal.maximize_progression()

        self.assertEqual(PalEntity.MAX_LEVEL, self.pal.Level)
        self.assertEqual(PalEntity.MAX_FRIENDSHIP_LEVEL, self.pal.FriendshipLevel)
        self.assertEqual(PalEntity.MAX_CONDENSATION_RANK, self.pal.Rank)
        self.assertEqual(0, self.pal.RankUpExp)
        self.assertEqual(
            [PalEntity.MAX_SOUL_RANK] * 4,
            [
                self.pal.Rank_HP,
                self.pal.Rank_Attack,
                self.pal.Rank_Defence,
                self.pal.Rank_CraftSpeed,
            ],
        )
        self.assertEqual(
            [PalEntity.MAX_TALENT] * 3,
            [self.pal.Talent_HP, self.pal.Talent_Shot, self.pal.Talent_Defense],
        )
        self.assertEqual(original_melee, self.pal.Talent_Melee)
        self.assertTrue(self.pal.IsAwakening)
        self.assertEqual(suitability_keys, set(self.pal.WorkSuitabilities or {}))
        self.assertTrue(
            all(value == 10 for value in (self.pal.WorkSuitabilities or {}).values())
        )
        self.assertEqual(original_character_id, self.pal.CharacterID)

    def test_maximize_does_not_add_pal_only_awakening_to_humans(self):
        human = make_record("SalesPerson_Wander").pal
        self.assertTrue(human.IsHuman)

        human.maximize_progression()

        self.assertFalse(human.IsAwakening)


if __name__ == "__main__":
    unittest.main()
