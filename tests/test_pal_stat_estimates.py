import unittest

from palworld_pal_editor.core.pal_entity import PalEntity
from palworld_pal_editor.core.pal_objects import PalObjects


class PalStatEstimateTests(unittest.TestCase):
    def test_awakened_jetragon_uses_saved_permanent_upgrades(self) -> None:
        pal_object = PalObjects.PalSaveParameter(
            PalObjects.EMPTY_UUID,
            PalObjects.EMPTY_UUID,
            PalObjects.EMPTY_UUID,
            0,
            PalObjects.EMPTY_UUID,
        )
        parameter = pal_object["value"]["RawData"]["value"]["object"]["SaveParameter"][
            "value"
        ]
        PalObjects.set_BaseType(parameter["CharacterID"], "BOSS_JetDragon")
        parameter.pop("OwnerPlayerUId", None)
        pal = PalEntity(pal_object)
        pal.Level = 80
        pal.Rank = 5
        pal.Rank_HP = 20
        pal.Rank_Attack = 20
        pal.Rank_Defence = 20
        pal.Rank_CraftSpeed = 20
        pal.Talent_HP = 100
        pal.Talent_Shot = 100
        pal.Talent_Defense = 100
        pal.FriendshipPoint = 200_000
        pal.IsAwakening = True
        for passive in (
            "WorldTree_ATK",
            "WorldTree_MoveSpeed",
            "WorldTree_ATK_DEF",
            "Legend",
        ):
            pal.add_PassiveSkillList(passive)

        self.assertEqual(9_489_000, pal.ComputedMaxHP)
        self.assertEqual(pal.ComputedMaxHP, pal.Hp)
        self.assertEqual(5_556, pal.ComputedAttack)
        self.assertEqual(2_558, pal.ComputedDefense)
        self.assertEqual(160, pal.ComputedCraftSpeed)


if __name__ == "__main__":
    unittest.main()
