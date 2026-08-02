import json
from pathlib import Path

from flask_jwt_extended import create_access_token

from palworld_pal_editor.webui import app

DATA = Path(__file__).parents[1] / "src/palworld_pal_editor/assets/data"
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
ACTIVE_FIELDS = {
    "InternalName",
    "Element",
    "CT",
    "Power",
    "I18n",
    "UniqueSkill",
    "Disabled",
    "NonInheritable",
    "SkillFruit",
    "Exclusive",
    "BossSkill",
    "Assignable",
    "AssignableToHumans",
    "Invalid",
    "Category",
    "Strength",
    "Effects",
    "Learners",
}
PASSIVE_FIELDS = {
    "InternalName",
    "Rating",
    "I18n",
    "Buff",
    "Category",
    "TargetElementType",
    "Effects",
    "Invocation",
    "AddInvokeTriggerTypes",
    "DescriptionSource",
}
INVOCATION_FIELDS = {
    "ActiveOtomo",
    "Worker",
    "Riding",
    "Reserve",
    "InOtomo",
    "Always",
    "InBaseCamp",
}
SUPPORTED_KINGWHALE_SKILL_LEVELS = {
    "EPalWazaID::Unique_KingWhale_AquaBlade": 15,
    "EPalWazaID::Unique_KingWhale_AquaTornado": 60,
    "EPalWazaID::Unique_KingWhale_Breaching": 40,
    "EPalWazaID::Unique_KingWhale_HomingBubble": 1,
    "EPalWazaID::Unique_KingWhale_Maelstrom": 30,
    "EPalWazaID::Unique_KingWhale_WaveTackle": 22,
}
UNSUPPORTED_KINGWHALE_SKILL_IDS = {
    "EPalWazaID::Unique_KingWhale_TidalBore",
    "EPalWazaID::Unique_KingWhale_SuperTidalBore",
}


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def test_game_derived_active_skill_contract():
    attacks = load("pal_attacks.json")
    boss_skills = {skill_id for skill_id, row in attacks.items() if row["BossSkill"]}

    assert len(attacks) == 384
    assert sum(row["SkillFruit"] for row in attacks.values()) == 92
    assert sum(row["Exclusive"] for row in attacks.values()) == 11
    assert len(boss_skills) == 34
    assert (
        sum(
            row["BossSkill"] and not row["Invalid"] and row["Assignable"]
            for row in attacks.values()
        )
        == 1
    )
    assert attacks["EPalWazaID::Human_Punch"]["Invalid"] is False
    assert attacks["EPalWazaID::Human_Punch"]["Assignable"] is False
    psychokinesis = attacks["EPalWazaID::Psychokinesis"]
    assert psychokinesis["SkillFruit"] is False
    assert psychokinesis["BossSkill"] is True
    assert psychokinesis["Invalid"] is False
    assert psychokinesis["Assignable"] is True
    assert attacks["EPalWazaID::Unique_DarkAlien_JumpScractch"]["BossSkill"] is False
    super_tidal_bore = attacks["EPalWazaID::Unique_KingWhale_SuperTidalBore"]
    assert super_tidal_bore["BossSkill"] is True
    assert super_tidal_bore["Invalid"] is True
    assert super_tidal_bore["Assignable"] is False
    for skill_id in (
        "EPalWazaID::PredatorBeam",
        "EPalWazaID::PredatorLockon",
        "EPalWazaID::PredatorWave",
    ):
        assert attacks[skill_id]["BossSkill"] is True
        assert attacks[skill_id]["Invalid"] is True
        assert attacks[skill_id]["Assignable"] is False
    radiant_purge_otomo = attacks["EPalWazaID::Unique_LegendDeer_RadiantPurge_Otomo"]
    assert radiant_purge_otomo["BossSkill"] is False
    assert radiant_purge_otomo["Invalid"] is False
    assert radiant_purge_otomo["Assignable"] is True
    for skill_id in (
        "EPalWazaID::Unique_LegendDeer_BarrierRelease_Normal",
        "EPalWazaID::Unique_LegendDeer_BarrierRelease_Grass",
        "EPalWazaID::Unique_LegendDeer_BarrierRelease_Water",
        "EPalWazaID::Unique_LegendDeer_RadiantPurge",
    ):
        assert attacks[skill_id]["BossSkill"] is True
        assert attacks[skill_id]["Invalid"] is True
        assert attacks[skill_id]["Assignable"] is False
    for skill_id, row in attacks.items():
        assert set(row) == ACTIVE_FIELDS, skill_id
        assert row["InternalName"] == skill_id
        assert row["UniqueSkill"] == row["NonInheritable"]
        assert set(row["I18n"]) == LOCALES
        assert all(
            set(text) == {"Name", "Description"}
            and text["Name"]
            and text["Description"]
            for text in row["I18n"].values()
        )
        assert all(
            set(learner) == {"CharacterID", "Level"}
            and isinstance(learner["CharacterID"], str)
            and isinstance(learner["Level"], int)
            for learner in row["Learners"]
        )


def test_case_mismatched_active_skill_localization_is_resolved():
    railbolt = load("pal_attacks.json")["EPalWazaID::Railbolt"]

    assert railbolt["I18n"]["en"]["Name"] == "Thunder Rail"
    assert railbolt["I18n"]["zh-CN"]["Name"] == "并联雷光"
    assert railbolt["Invalid"] is False
    assert railbolt["Assignable"] is True


def test_supported_kingwhale_runtime_skills_are_valid_and_assignable():
    attacks = load("pal_attacks.json")

    assert len(SUPPORTED_KINGWHALE_SKILL_LEVELS) == 6
    assert SUPPORTED_KINGWHALE_SKILL_LEVELS.keys() <= attacks.keys()
    assert {
        skill_id
        for skill_id in SUPPORTED_KINGWHALE_SKILL_LEVELS
        if attacks[skill_id]["Invalid"] or not attacks[skill_id]["Assignable"]
    } == set()
    for skill_id, level in SUPPORTED_KINGWHALE_SKILL_LEVELS.items():
        assert {
            "CharacterID": "BOSS_KingWhale_otomo",
            "Level": level,
        } in attacks[skill_id]["Learners"]


def test_unsupported_kingwhale_runtime_skills_remain_unassignable():
    attacks = load("pal_attacks.json")

    assert UNSUPPORTED_KINGWHALE_SKILL_IDS <= attacks.keys()
    for skill_id in UNSUPPORTED_KINGWHALE_SKILL_IDS:
        assert attacks[skill_id]["Invalid"] is True
        assert attacks[skill_id]["Assignable"] is False


def test_game_derived_pal_passive_contract():
    passives = load("pal_passives.json")

    assert len(passives) == 115
    assert {"MiniNushi", "Nushi"} <= passives.keys()
    assert passives["MiniNushi"]["Rating"] == 3
    assert passives["MiniNushi"]["I18n"]["zh-CN"]["Name"] == "大猎物"
    for passive_id, row in passives.items():
        assert set(row) == PASSIVE_FIELDS, passive_id
        assert row["InternalName"] == passive_id
        assert set(row["I18n"]) == LOCALES
        assert set(row["DescriptionSource"]) == LOCALES
        assert set(row["Invocation"]) == INVOCATION_FIELDS
        assert all(type(value) is bool for value in row["Invocation"].values())
        assert set(row["Buff"]) == {
            "b_Attack",
            "b_Defense",
            "b_CraftSpeed",
            "b_MoveSpeed",
        }
        assert all(
            set(text) == {"Name", "Description"}
            and text["Name"]
            and text["Description"]
            for text in row["I18n"].values()
        )
        assert all(
            source in {"explicit", "composed"}
            for source in row["DescriptionSource"].values()
        )
        assert all(
            set(effect) == {"EffectType", "EffectValue", "TargetType"}
            for effect in row["Effects"]
        )


def test_active_skill_endpoint_preserves_shape_and_exposes_game_metadata():
    app.config.update(
        TESTING=True,
        JWT_SECRET_KEY="test-secret-key-with-at-least-32-bytes",
    )
    with app.app_context():
        token = create_access_token(identity="test", expires_delta=False)
    with app.test_client() as client:
        response = client.get(
            "/api/save/active_skills",
            headers={"Authorization": f"Bearer {token}"},
        )

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["status"] == 0
    assert set(payload["data"]) == {"dict", "arr"}
    assert len(payload["data"]["dict"]) == len(payload["data"]["arr"]) == 384

    expected_fields = {
        "InternalName",
        "I18n",
        "HasSkillFruit",
        "IsUniqueSkill",
        "NonInheritable",
        "Exclusive",
        "BossSkill",
        "Assignable",
        "AssignableToHumans",
        "Power",
        "Element",
        "CT",
        "Invalid",
    }
    attacks = load("pal_attacks.json")
    for row in payload["data"]["arr"]:
        skill_id = row["InternalName"]
        source = attacks[skill_id]
        assert set(row) == expected_fields
        assert payload["data"]["dict"][skill_id] == row
        assert row["HasSkillFruit"] == source["SkillFruit"]
        assert row["IsUniqueSkill"] == source["UniqueSkill"]
        assert row["NonInheritable"] == source["NonInheritable"]
        assert row["Exclusive"] == source["Exclusive"]
        assert row["BossSkill"] == source["BossSkill"]
        assert row["Assignable"] == source["Assignable"]
        assert row["AssignableToHumans"] == source["AssignableToHumans"]

    human_punch = payload["data"]["dict"]["EPalWazaID::Human_Punch"]
    assert human_punch["Invalid"] is False
    assert human_punch["Assignable"] is False
    assert human_punch["AssignableToHumans"] is True

    weapon_use = payload["data"]["dict"]["EPalWazaID::Weapon_Use"]
    assert weapon_use["Invalid"] is False
    assert weapon_use["Assignable"] is False
    assert weapon_use["AssignableToHumans"] is True
