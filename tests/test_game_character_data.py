import json
from pathlib import Path

ASSETS = Path(__file__).parents[1] / "src/palworld_pal_editor/assets"
DATA = ASSETS / "data"
LOCALES = {
    "ja",
    "de",
    "en",
    "es",
    "es-MX",
    "fr",
    "id",
    "it",
    "ko",
    "pl",
    "pt-BR",
    "ru",
    "th",
    "tr",
    "vi",
    "zh-CN",
    "zh-TW",
}
STATS = {"HP", "ATK", "DEF", "MELEE", "CRAFTSPEED", "FOOD"}
SUITABILITIES = {
    "EPalWorkSuitability::EmitFlame",
    "EPalWorkSuitability::Watering",
    "EPalWorkSuitability::Seeding",
    "EPalWorkSuitability::GenerateElectricity",
    "EPalWorkSuitability::Handcraft",
    "EPalWorkSuitability::Collection",
    "EPalWorkSuitability::Deforest",
    "EPalWorkSuitability::Mining",
    "EPalWorkSuitability::OilExtraction",
    "EPalWorkSuitability::ProductMedicine",
    "EPalWorkSuitability::Cool",
    "EPalWorkSuitability::Transport",
    "EPalWorkSuitability::MonsterFarm",
}
PARAMETERS = {
    "Size",
    "Rarity",
    "Support",
    "Friendship_HP",
    "Friendship_ShotAttack",
    "Friendship_Defense",
    "Friendship_CraftSpeed",
    "EnemyMaxHPRate",
    "EnemyInflictDamageRate",
    "EnemyReceiveDamageRate",
    "EnemyWazaCoolTimeRate",
    "CaptureRateCorrect",
    "ExpRatio",
    "Price",
    "StatusResistUpRate",
    "WalkSpeed",
    "SlowWalkSpeed",
    "RunSpeed",
    "RideSprintSpeed",
    "TransportSpeed",
    "SwimSpeed",
    "SwimDashSpeed",
    "FullStomachDecreaseRate",
    "FoodAmount",
    "MaxFullStomach",
    "Stamina",
    "Nocturnal",
    "Predator",
    "Edible",
    "BiologicalGrade",
    "MaleProbability",
    "CombiRank",
    "CombiDuplicatePriority",
    "IgnoreCombi",
    *{f"WorkSuitability_{name.rsplit('::', 1)[1]}" for name in SUITABILITIES},
}
CHARACTER_FIELDS = {
    "InternalName",
    "FamilyID",
    "FamilyResolved",
    "VariantKind",
    "VariantTags",
    "IconKey",
    "Invalid",
    "RegularlyObtainable",
    "ObtainMethods",
    "AvailabilitySources",
    "I18n",
    "Elements",
    "Stats",
    "Parameters",
    "Suitabilities",
    "BestWorkSuitability",
    "DefaultPassives",
    "Attacks",
    "SortingKey",
    "PaldeckIndex",
    "PaldeckSuffix",
    "Breeding",
}
SKIN_SOURCE_FIELDS = {
    "SkinName",
    "SkinType",
    "SkinStaticClass",
    "bIsHairAccessory",
    "TargetActorClassName",
    "TargetPalName",
    "bAutoGetItem",
    "PlatformItemID_Steam",
}
SCENARIO_INVALID_TO_VALID_SOURCES = {
    "Boss_Anubis": {"Kind": "placement", "ID": "3587"},
    "BOSS_DarkScorpion": {"Kind": "placement", "ID": "1694"},
    "BOSS_DarkScorpion_Ground": {"Kind": "placement", "ID": "1940"},
    "BOSS_DomeArmorDragon": {"Kind": "placement", "ID": "6742"},
    "BOSS_ElecPanda": {"Kind": "placement", "ID": "4385"},
    "BOSS_GhostDragon": {"Kind": "placement", "ID": "1565"},
    "BOSS_KingWhale_otomo": {
        "Kind": "capture-replace",
        "ID": "BP_AICombatModule_KingWhale_Wild",
    },
    "BOSS_Umihebi": {"Kind": "placement", "ID": "921"},
    "BOSS_VolcanoDragon": {"Kind": "placement", "ID": "358"},
    "BOSS_VolcanoDragon_Ice": {"Kind": "placement", "ID": "2939"},
    "BOSS_Yeti_Grass": {"Kind": "placement", "ID": "2165"},
    "GYM_ElecPanda_Otomo": {
        "Kind": "quest-reward",
        "ID": "FABP_GrassBoss01",
    },
}


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def test_game_derived_character_contract():
    pals = load("pal_data.json")
    humans = load("human_data.json")
    skills = load("pal_attacks.json")
    passives = load("pal_passives.json")

    assert len(pals) == 753
    assert len(humans) == 433
    assert {
        "Werewolf_Ice",
        "GrassPanda_Electric_Tower",
        "BOSS_KingWhale_otomo",
        "PREDATOR_FlowerRabbit_Quest",
    }.issubset(pals)

    pal_index = {key.casefold(): key for key in pals}
    assert len(pal_index) == len(pals)
    for table, human in ((pals, False), (humans, True)):
        for character_id, row in table.items():
            expected = CHARACTER_FIELDS | ({"Human", "HasIcon"} if human else set())
            if "PaldeckRecordID" in row:
                expected.add("PaldeckRecordID")
            assert set(row) == expected, character_id
            assert row["InternalName"] == character_id
            assert set(row["I18n"]) == LOCALES
            assert all(row["I18n"].values())
            assert set(row["Stats"]) == STATS
            assert set(row["Parameters"]) == PARAMETERS
            assert set(row["Suitabilities"]) == SUITABILITIES
            assert row["Invalid"] is (not row["RegularlyObtainable"])
            assert all(skill in skills for skill in row["Attacks"])
            assert all(passive in passives for passive in row["DefaultPassives"])
            assert (
                row["IconKey"] in {"Human", "unknown"}
                or (ASSETS / "icons/pals" / f"{row['IconKey']}.png").is_file()
            )
            if human:
                assert row["FamilyID"] == character_id
                assert row["FamilyResolved"] is True
                assert row["Human"] is True
                assert row["HasIcon"] is (row["IconKey"] != "Human")
            elif row["FamilyResolved"]:
                assert row["FamilyID"].casefold() in pal_index
            else:
                assert row["FamilyID"].casefold() not in pal_index


def test_unique_breeding_requires_reachable_parents_and_alpha_follows_valid_base():
    pals = load("pal_data.json")

    for character_id in (
        "BeardedDragon",
        "BlackFurDragon",
        "DarkMutant",
        "ElecLion",
        "FlowerPrince",
        "GrassDragon",
        "Mothman",
        "PinkKangaroo",
        "PoseidonOrca",
        "WaterLizard",
    ):
        assert pals[character_id]["Invalid"] is True, character_id
        assert pals[character_id]["RegularlyObtainable"] is False, character_id
        assert pals[character_id]["AvailabilitySources"] == [], character_id

    assert pals["GhostRabbit_Grass"]["Invalid"] is False
    assert "unique-breeding" in pals["GhostRabbit_Grass"]["ObtainMethods"]
    assert pals["BOSS_GhostRabbit_Grass"]["Invalid"] is False
    assert pals["BOSS_GhostRabbit_Grass"]["AvailabilitySources"] == [
        {"Kind": "alpha-form", "ID": "GhostRabbit_Grass"}
    ]


def test_authoritative_family_variant_and_source_values():
    pals = load("pal_data.json")

    assert pals["BOSS_KingWhale_otomo"]["FamilyID"] == "KingWhale"
    assert pals["GrassPanda_Electric_Tower"]["FamilyID"] == ("GrassPanda_Electric")
    assert pals["GYM_BlackGriffon"]["FamilyID"] == "BlackGriffon"
    assert pals["PREDATOR_WhiteShieldDragon_Quest"]["FamilyID"] == ("WhiteShieldDragon")
    assert pals["BOSS_ElecPanda_BossRush"]["Invalid"] is True
    assert pals["GYM_BlackGriffon"]["Invalid"] is True
    assert pals["BOSS_ElecPanda_BossRush"]["VariantTags"] == [
        "boss-rush",
        "tower",
    ]
    assert pals["BOSS_ElecPanda_BossRush"]["Parameters"]["Predator"] is True
    assert pals["BOSS_ElecPanda_BossRush"]["VariantKind"] == "boss-rush"

    raid_legend_deer = pals["RAID_LegendDeer"]
    assert raid_legend_deer["VariantKind"] == "raid"
    assert raid_legend_deer["Invalid"] is True
    assert raid_legend_deer["RegularlyObtainable"] is False
    assert raid_legend_deer["ObtainMethods"] == []
    assert raid_legend_deer["AvailabilitySources"] == []

    raid_egg_ids = {
        "NightLady",
        "BOSS_NightLady",
        "NightLady_Dark",
        "BOSS_NightLady_Dark",
        "KingBahamut_Dragon",
        "BOSS_KingBahamut_Dragon",
        "DarkMechaDragon",
        "BOSS_DarkMechaDragon",
        "LegendDeer",
        "BOSS_LegendDeer",
    }
    assert {
        character_id
        for character_id, row in pals.items()
        if any(source["Kind"] == "raid-egg" for source in row["AvailabilitySources"])
    } == raid_egg_ids
    assert (
        sum(
            source["Kind"] == "raid-egg"
            for row in pals.values()
            for source in row["AvailabilitySources"]
        )
        == 18
    )

    for raid_egg_id in raid_egg_ids:
        raid_egg = pals[raid_egg_id]
        assert raid_egg["Invalid"] is False
        assert raid_egg["RegularlyObtainable"] is True
        assert "raid-egg" in raid_egg["ObtainMethods"]

    for raid_servant_id in (
        "SUMMON_DarkAlien",
        "SUMMON_WhiteAlienDragon",
        "SUMMON_DarkAlien_MAX",
        "SUMMON_WhiteAlienDragon_MAX",
    ):
        raid_servant = pals[raid_servant_id]
        assert raid_servant["Invalid"] is True
        assert raid_servant["RegularlyObtainable"] is False
        assert raid_servant["AvailabilitySources"] == []

    king_whale = pals["KingWhale"]
    assert king_whale["Stats"] == {
        "HP": 180,
        "ATK": 120,
        "DEF": 200,
        "MELEE": 100,
        "CRAFTSPEED": 100,
        "FOOD": 600,
    }
    assert king_whale["Parameters"]["CombiRank"] == 20
    assert king_whale["Parameters"]["IgnoreCombi"] is True
    assert king_whale["Parameters"]["Friendship_ShotAttack"] == 1.7
    assert king_whale["PaldeckIndex"] == 203
    assert king_whale["PaldeckSuffix"] == ""


def test_kingwhale_runtime_publication_uses_exact_character_evidence():
    pals = load("pal_data.json")

    for character_id in ("KingWhale", "BOSS_KingWhale"):
        row = pals[character_id]
        assert row["Invalid"] is True
        assert row["RegularlyObtainable"] is False
        assert row["ObtainMethods"] == []
        assert row["AvailabilitySources"] == []

    otomo = pals["BOSS_KingWhale_otomo"]
    assert otomo["FamilyID"] == "KingWhale"
    assert otomo["VariantKind"] == "boss"
    assert otomo["VariantTags"] == ["boss", "otomo"]
    assert otomo["Invalid"] is False
    assert otomo["RegularlyObtainable"] is True
    assert otomo["ObtainMethods"] == ["capture-replace"]
    assert otomo["AvailabilitySources"] == [
        {
            "Kind": "capture-replace",
            "ID": "BP_AICombatModule_KingWhale_Wild",
        }
    ]


def test_zoe_otomo_runtime_publication_uses_exact_reward_evidence():
    zoe = load("pal_data.json")["GYM_ElecPanda_Otomo"]

    assert zoe["FamilyID"] == "ElecPanda"
    assert zoe["VariantKind"] == "tower"
    assert zoe["VariantTags"] == ["otomo", "tower"]
    assert zoe["Invalid"] is False
    assert zoe["RegularlyObtainable"] is True
    assert zoe["ObtainMethods"] == ["quest-reward"]
    assert zoe["AvailabilitySources"] == [
        {"Kind": "quest-reward", "ID": "FABP_GrassBoss01"}
    ]


def test_runtime_character_acquisition_never_uses_family_propagation():
    characters = load("pal_data.json") | load("human_data.json")

    propagated_methods = {
        (character_id, method)
        for character_id, row in characters.items()
        for method in row["ObtainMethods"]
        if method.startswith("family-")
    }
    propagated_sources = {
        (character_id, source["Kind"], source["ID"])
        for character_id, row in characters.items()
        for source in row["AvailabilitySources"]
        if source["Kind"].startswith("family-")
    }
    assert propagated_methods == set()
    assert propagated_sources == set()


def test_exact_scenario_publication_rows_use_approved_sources():
    pals = load("pal_data.json")

    assert len(SCENARIO_INVALID_TO_VALID_SOURCES) == 12
    for character_id, source in SCENARIO_INVALID_TO_VALID_SOURCES.items():
        row = pals[character_id]
        assert row["Invalid"] is False, character_id
        assert row["RegularlyObtainable"] is True, character_id
        assert row["ObtainMethods"] == [source["Kind"]], character_id
        assert row["AvailabilitySources"] == [source], character_id


def test_game_derived_skin_contract_and_missing_icon_policy():
    pals = load("pal_data.json")
    humans = load("human_data.json")
    skins = load("skin_data.json")
    characters = {key.casefold() for key in pals | humans}

    assert len(skins) == 29
    for skin_id, row in skins.items():
        assert set(row) == SKIN_SOURCE_FIELDS | {
            "InternalName",
            "I18n",
            "IconKey",
            "Invalid",
        }
        assert row["InternalName"] == row["SkinName"] == skin_id
        assert set(row["I18n"]) == LOCALES
        assert all(row["I18n"].values())
        assert row["TargetPalName"].casefold() in characters
        icon = ASSETS / "icons/pals/skin" / f"{row['IconKey']}.png"
        assert icon.is_file() or row["Invalid"] is True

    assert skins["IceHorse_Skin001"]["Invalid"] is True
    assert skins["IceHorse_Skin001"]["I18n"]["en"] == "Noble Frostallion"
    assert set(skins["IceHorse_Skin001"]["I18n"]) == LOCALES
    assert not (
        ASSETS / "icons/pals/skin" / f"{skins['IceHorse_Skin001']['IconKey']}.png"
    ).is_file()
    assert skins["PinkCat_Skin002"]["Invalid"] is True
    assert not (
        ASSETS / "icons/pals/skin" / f"{skins['PinkCat_Skin002']['IconKey']}.png"
    ).is_file()
