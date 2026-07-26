import json
from pathlib import Path

DATA = Path(__file__).parents[1] / "src/palworld_pal_editor/assets/data"
EXP_FIELDS = {
    "BuildEXP",
    "CraftEXP",
    "DropEXP",
    "NextEXP",
    "PalBuildEXP",
    "PalCraftEXP",
    "PalNextEXP",
    "PalTotalEXP",
    "TotalEXP",
}


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def test_build_24181527_progression_tables_match_exported_source_rows():
    experience = load("pal_exp_table.json")
    friendship = load("pal_friendship.json")

    assert len(experience) == 100
    assert len(friendship) == 14
    assert experience["1"] == {
        "BuildEXP": 5,
        "CraftEXP": 5,
        "DropEXP": 10,
        "NextEXP": 0,
        "PalBuildEXP": 5,
        "PalCraftEXP": 4,
        "PalNextEXP": 0,
        "PalTotalEXP": 0,
        "TotalEXP": 0,
    }
    assert experience["65"] == {
        "BuildEXP": 13,
        "CraftEXP": 5,
        "DropEXP": 6516,
        "NextEXP": 977950,
        "PalBuildEXP": 68,
        "PalCraftEXP": 5,
        "PalNextEXP": 6896858,
        "PalTotalEXP": 41376365,
        "TotalEXP": 10582213,
    }
    assert experience["100"] == {
        "BuildEXP": 35,
        "CraftEXP": 5,
        "DropEXP": 179210,
        "NextEXP": 59736607,
        "PalBuildEXP": 5,
        "PalCraftEXP": 4,
        "PalNextEXP": 6896858,
        "PalTotalEXP": 282766395,
        "TotalEXP": 382451548,
    }
    assert friendship["-3"] == {"required_point": -10000}
    assert friendship["0"] == {"required_point": 0}
    assert friendship["10"] == {"required_point": 200000}


def test_progression_tables_have_canonical_integer_keys_and_monotonic_totals():
    experience = load("pal_exp_table.json")
    friendship = load("pal_friendship.json")

    for level, row in experience.items():
        assert str(int(level)) == level
        assert set(row) == EXP_FIELDS
        assert all(type(value) is int for value in row.values())
    for rank, row in friendship.items():
        assert str(int(rank)) == rank
        assert set(row) == {"required_point"}
        assert type(row["required_point"]) is int

    ordered_exp = [experience[str(level)] for level in range(1, 101)]
    assert [row["TotalEXP"] for row in ordered_exp] == sorted(
        row["TotalEXP"] for row in ordered_exp
    )
    assert [row["PalTotalEXP"] for row in ordered_exp] == sorted(
        row["PalTotalEXP"] for row in ordered_exp
    )
    ordered_friendship = [friendship[str(rank)] for rank in range(-3, 11)]
    assert [row["required_point"] for row in ordered_friendship] == sorted(
        row["required_point"] for row in ordered_friendship
    )
