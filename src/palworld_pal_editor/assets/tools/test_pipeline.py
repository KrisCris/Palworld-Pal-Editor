from __future__ import annotations

import hashlib
import io
import json
import os
import struct
import subprocess
import tempfile
import unittest
import zlib
from copy import deepcopy
from dataclasses import replace
from pathlib import Path, PurePosixPath
from unittest.mock import patch

import extract_game_data
import game_data
from extract_game_data import (
    DOCTOR_ASSETS,
    KNOWN_BUILD,
    MAPPING_SHA256,
    UEX_REVISION,
    Toolchain,
    detect_build_id,
    ensure_toolchain,
    require_write_build,
    run_doctor,
)
from game_data import (
    DOMAIN_BUILDERS,
    BuildIdentity,
    Manifest,
    Reference,
    SourceInventory,
    build_legacy_deletion_proposal,
    build_legacy_ownership_candidate,
    candidate_manifest,
    casefold_index,
    check_domains,
    domain_policy_hash,
    load_asset,
    load_table,
    load_text_table,
    manifest_bytes,
    manifest_from_dict,
    publish_domain,
    snapshot_from_outputs,
    validate_domain,
    write_legacy_ownership_candidate,
)

LOCALES = (
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
)
DOMAINS = ("skills", "characters", "progression", "technology")
REQUIRED_SOURCES = {
    "skills": ("Pal/Content/Pal/DataTable/Waza/DT_WazaDataTable_Common",),
    "characters": (
        "Pal/Content/Pal/DataTable/Character/DT_PalMonsterParameter_Common",
    ),
    "progression": ("Pal/Content/Pal/DataTable/Exp/DT_PalExpTable",),
    "technology": (
        "Pal/Content/Pal/DataTable/Technology/DT_TechnologyRecipeUnlock_Common",
    ),
}
FIXTURE_POLICY = {
    "schema_version": 1,
    "bootstrap": {
        "game_build": KNOWN_BUILD,
        "uex_revision": UEX_REVISION,
        "mapping_sha256": MAPPING_SHA256,
    },
    "domains": {
        domain: {"required_sources": list(REQUIRED_SOURCES[domain]), "option": domain}
        for domain in DOMAINS
    },
}
FIXTURE_POLICY["domains"]["skills"]["supported_routes"] = sorted(
    game_data.SUPPORTED_CHARACTER_ROUTES
)
FIXTURE_POLICY["domains"]["characters"]["supported_routes"] = sorted(
    game_data.SUPPORTED_CHARACTER_ROUTES
)
IDENTITY = BuildIdentity(KNOWN_BUILD, UEX_REVISION, MAPPING_SHA256)


def json_bytes(rows: dict[str, dict]) -> bytes:
    return (json.dumps(rows, sort_keys=True, separators=(",", ":")) + "\n").encode()


def png_chunk(kind: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    )


def png_bytes(width: int, height: int, *, compressed: bytes | None = None) -> bytes:
    pixels = b"".join(b"\0" + b"\x10\x20\x30\xff" * width for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + png_chunk(
            b"IDAT", zlib.compress(pixels) if compressed is None else compressed
        )
        + png_chunk(b"IEND", b"")
    )


PNG_1X1 = png_bytes(1, 1)
PNG_2X2 = png_bytes(2, 2)


def text_i18n(label: str) -> dict[str, str]:
    return {locale: f"{label}-{locale}" for locale in LOCALES}


def content_i18n(label: str, *, typed: bool = False) -> dict[str, dict[str, str]]:
    return {
        locale: {
            "Name": f"{label}-name-{locale}",
            "Description": f"{label}-description-{locale}",
            **({"Type": f"{label}-type-{locale}"} if typed else {}),
        }
        for locale in LOCALES
    }


def fixture_character_fields(character_id: str, label: str) -> dict:
    parameters = {
        field: (
            "EPalSizeType::M"
            if field == "Size"
            else False
            if field in {"Nocturnal", "Predator", "Edible", "IgnoreCombi"}
            else 0
        )
        for field in game_data.CHARACTER_PARAMETER_FIELDS
    }
    return {
        "InternalName": character_id,
        "FamilyID": character_id,
        "FamilyResolved": True,
        "VariantKind": "base",
        "VariantTags": ["base"],
        "IconKey": character_id,
        "Invalid": False,
        "RegularlyObtainable": True,
        "ObtainMethods": ["placement"],
        "AvailabilitySources": [{"Kind": "placement", "ID": "Fixture"}],
        "I18n": text_i18n(label),
        "Elements": ["Neutral"],
        "Stats": {field: 1 for field in game_data.CHARACTER_STATS},
        "Parameters": parameters,
        "Suitabilities": {
            f"EPalWorkSuitability::{name}": parameters[f"WorkSuitability_{name}"]
            for name in game_data.WORK_SUITABILITIES
        },
        "BestWorkSuitability": "EPalWorkSuitability::None",
        "DefaultPassives": [],
        "Attacks": {},
        "SortingKey": {"paldeck": "1"},
        "PaldeckIndex": 1,
        "PaldeckSuffix": "",
        "Breeding": {
            "CombiRank": 0,
            "CombiDuplicatePriority": 0,
            "IgnoreCombi": False,
            "UniqueRecipes": [],
        },
    }


def fixture_outputs() -> dict[str, dict[str, bytes]]:
    return {
        "skills": {
            "data/pal_attacks.json": json_bytes(
                {
                    "TestSkill": {
                        "InternalName": "TestSkill",
                        "Element": "Normal",
                        "CT": 1.0,
                        "Power": 10,
                        "I18n": content_i18n("skill"),
                        "UniqueSkill": False,
                        "Disabled": False,
                        "NonInheritable": False,
                        "SkillFruit": True,
                        "Exclusive": False,
                        "BossSkill": False,
                        "Assignable": True,
                        "AssignableToHumans": False,
                        "Invalid": False,
                        "Category": "Shot",
                        "Strength": "None",
                        "Effects": [],
                        "Learners": [{"CharacterID": "TestPal", "Level": 1}],
                    }
                }
            ),
            "data/pal_passives.json": json_bytes(
                {
                    "TestPassive": {
                        "InternalName": "TestPassive",
                        "Rating": 1,
                        "I18n": content_i18n("passive"),
                        "Buff": {
                            "b_Attack": 0.0,
                            "b_Defense": 0.0,
                            "b_CraftSpeed": 0.0,
                            "b_MoveSpeed": 0.0,
                        },
                        "Category": "SortDisplayable",
                        "TargetElementType": "None",
                        "Effects": [],
                        "Invocation": {
                            "ActiveOtomo": False,
                            "Worker": False,
                            "Riding": False,
                            "Reserve": False,
                            "InOtomo": False,
                            "Always": True,
                            "InBaseCamp": False,
                        },
                        "AddInvokeTriggerTypes": [],
                        "DescriptionSource": {locale: "composed" for locale in LOCALES},
                    }
                }
            ),
        },
        "characters": {
            "data/pal_data.json": json_bytes(
                {
                    "TestPal": {
                        **fixture_character_fields("TestPal", "pal"),
                        "DefaultPassives": ["TestPassive"],
                        "Attacks": {"TestSkill": 1},
                    }
                }
            ),
            "data/human_data.json": json_bytes(
                {
                    "TestHuman": {
                        **fixture_character_fields("TestHuman", "human"),
                        "IconKey": "Human",
                        "Human": True,
                        "HasIcon": False,
                    }
                }
            ),
            "data/skin_data.json": json_bytes(
                {
                    "TestSkin": {
                        "SkinName": "TestSkin",
                        "SkinType": "EPalSkinType::Pal",
                        "SkinStaticClass": "PalCharacterClass",
                        "bIsHairAccessory": False,
                        "TargetActorClassName": "None",
                        "TargetPalName": "TestPal",
                        "bAutoGetItem": False,
                        "PlatformItemID_Steam": -1,
                        "InternalName": "TestSkin",
                        "I18n": text_i18n("skin"),
                        "IconKey": "TestSkin",
                        "Invalid": False,
                    }
                }
            ),
            "icons/pals/TestPal.png": PNG_1X1,
            "icons/pals/skin/TestSkin.png": PNG_2X2,
        },
        "progression": {
            "data/pal_exp_table.json": json_bytes(
                {
                    "1": {
                        "BuildEXP": 1,
                        "CraftEXP": 1,
                        "DropEXP": 1,
                        "NextEXP": 1,
                        "PalBuildEXP": 1,
                        "PalCraftEXP": 1,
                        "PalNextEXP": 1,
                        "PalTotalEXP": 1,
                        "TotalEXP": 1,
                    }
                }
            ),
            "data/pal_friendship.json": json_bytes({"0": {"required_point": 0}}),
            "data/player_status_data.json": json_bytes(
                {
                    "最大HP": {
                        "category": "stat",
                        "icon": "stat-health",
                        "maximum": 1,
                        "source": "AddMaxHPPerStatusPoint",
                        "unit": "flat",
                        "values": [0, 100],
                    }
                }
            ),
        },
        "technology": {
            "data/tech_data.json": json_bytes(
                {
                    "TestTech": {
                        "InternalName": "TestTech",
                        "Level": 1,
                        "Tier": 0,
                        "Cost": 1,
                        "BossTechnology": False,
                        "Requirements": {
                            "DefeatTowerBoss": "",
                            "ResearchID": "",
                        },
                        "Prerequisites": [],
                        "UnlockItems": ["TestItem"],
                        "UnlockBuildObjects": [],
                        "I18n": content_i18n("technology", typed=True),
                        "UnlockPalSkill": "TestPal",
                        "IconKey": "TestTech",
                        "IconKind": "item",
                    }
                }
            ),
            "icons/tech/TestTech.png": PNG_2X2,
        },
    }


def fixture_candidate(domain: str, outputs: dict[str, bytes] | None = None):
    selected = outputs if outputs is not None else fixture_outputs()[domain]
    dimensions = {
        path: ((1, 1) if path.endswith("TestPal.png") else (2, 2))
        for path in selected
        if path.endswith(".png")
    }
    return snapshot_from_outputs(
        domain,
        selected,
        IDENTITY,
        domain_policy_hash(FIXTURE_POLICY, domain),
        {source: 1 for source in REQUIRED_SOURCES[domain]},
        icon_dimensions=dimensions,
    )


def fixture_candidates():
    return {domain: fixture_candidate(domain) for domain in DOMAINS}


def fixture_sources(*, present: set[str] | None = None) -> SourceInventory:
    return SourceInventory(
        present_sources=frozenset(
            present
            if present is not None
            else {source for paths in REQUIRED_SOURCES.values() for source in paths}
        ),
        reference_ids={
            "characters": frozenset({"TestPal", "TestHuman"}),
            "skills": frozenset({"TestSkill"}),
            "passives": frozenset({"TestPassive"}),
            "skins": frozenset({"TestSkin"}),
            "technology": frozenset({"TestTech"}),
        },
        available_icons=frozenset({"icons/pals/TestPal.png"}),
        approved_static_icons=frozenset(
            {"icons/pals/Human.png", "icons/pals/unknown.png"}
        ),
    )


def fixture_manifest(candidates: dict | None = None) -> Manifest:
    selected = candidates or fixture_candidates()
    return Manifest(
        schema_version=1,
        bootstrap={
            "legacy_ownership": {
                "baseline_commit": "ffe29c70c436829675a017cde178620c6c7c713e",
                "backup_inventory_sha256": "fixture-backup-hash",
                "review_approval": "approved-fixture",
            }
        },
        domains={
            domain: candidate_manifest(candidate)
            for domain, candidate in selected.items()
        },
    )


def builder(candidate):
    return lambda export_root, policy: candidate


def fixture_errors(
    domain: str,
    candidate,
    *,
    sources: SourceInventory | None = None,
    existing: Manifest | None = None,
) -> list[str]:
    return validate_domain(
        domain,
        candidate,
        sources or fixture_sources(),
        existing or Manifest(1, {}, {}),
        FIXTURE_POLICY,
    )


def write_table(root: Path, virtual_path: str, rows: dict[str, dict]) -> None:
    path = root / f"{virtual_path}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([{"Type": "DataTable", "Rows": rows}]), encoding="utf-8")


def write_asset(root: Path, virtual_path: str, exports: list[dict]) -> None:
    path = root / f"{virtual_path}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(exports), encoding="utf-8")


def write_player_status_sources(root: Path) -> None:
    rows = {
        str(index): {
            "RelicType": f"EPalRelicType::{relic_type}",
            "Rank": 1,
            "EffectRate": 0 if relic_type == "CapturePower" else index,
        }
        for index, relic_type in enumerate(
            game_data._PLAYER_RELIC_DEFINITIONS, start=1
        )
    }
    write_table(root, game_data.PROGRESSION_SOURCES["player_status"], rows)
    write_asset(
        root,
        game_data.PROGRESSION_SOURCES["game_setting"],
        [
            {
                "Name": "Default__BP_PalGameSetting_C",
                "Properties": {
                    field: index
                    for index, (field, _, _) in enumerate(
                        game_data._PLAYER_STAT_DEFINITIONS.values(), start=1
                    )
                },
            }
        ],
    )


def snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file()
    }


def stage_candidate(stage: Path, candidate) -> None:
    for relative, data in candidate.outputs.items():
        target = stage.joinpath(*relative.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def write_candidate(assets: Path, candidate) -> None:
    stage_candidate(assets, candidate)


def changed_candidate(domain: str):
    outputs = fixture_outputs()[domain]
    path = {
        "skills": "data/pal_attacks.json",
        "characters": "data/pal_data.json",
        "progression": "data/pal_exp_table.json",
        "technology": "data/tech_data.json",
    }[domain]
    rows = json.loads(outputs[path])
    row = next(iter(rows.values()))
    if domain == "characters":
        row["I18n"]["en"] = "changed"
    elif domain == "progression":
        row["BuildEXP"] = 2
    else:
        row["I18n"]["en"]["Name"] = "changed"
    outputs[path] = json_bytes(rows)
    return fixture_candidate(domain, outputs)


def legacy_plan_hash(accepted: list[dict[str, str]]) -> str:
    encoded = json.dumps(
        accepted, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def document_bytes(document: dict) -> bytes:
    return (
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode()


def write_ownership_evidence(
    root: Path,
    accepted: list[dict[str, str]],
    *,
    reviewer: str = "fixture-ownership-reviewer",
) -> tuple[Path, Path, dict, dict]:
    candidate = {
        "schema_version": 1,
        "baseline_commit": "fixture-baseline",
        "backup_inventory_sha256": "fixture-backup",
        "accepted_count": len(accepted),
        "accepted": accepted,
        "plan_sha256": legacy_plan_hash(accepted),
        "review_approval": None,
    }
    candidate_path = root / "legacy_ownership_candidate.json"
    write_legacy_ownership_candidate(candidate_path, candidate)
    scope_counts = {"pals": 0, "skin": 0, "tech": 0}
    for item in accepted:
        if item["path"].startswith("icons/pals/skin/"):
            scope_counts["skin"] += 1
        elif item["path"].startswith("icons/pals/"):
            scope_counts["pals"] += 1
        else:
            scope_counts["tech"] += 1
    ownership = {
        "schema_version": 1,
        "kind": "legacy_ownership_evidence",
        "baseline_commit": candidate["baseline_commit"],
        "backup_inventory_sha256": candidate["backup_inventory_sha256"],
        "ownership_plan_sha256": candidate["plan_sha256"],
        "candidate_artifact": candidate_path.name,
        "candidate_artifact_sha256": hashlib.sha256(
            candidate_path.read_bytes()
        ).hexdigest(),
        "accepted_count": len(accepted),
        "scope_counts": scope_counts,
        "review": {
            "decision": "approved_ownership_evidence_only",
            "reviewer": reviewer,
            "review_date": "2026-07-26",
        },
    }
    ownership_path = root / "legacy_ownership.json"
    ownership_path.write_bytes(document_bytes(ownership))
    return candidate_path, ownership_path, candidate, ownership


def make_directory_link(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            check=True,
            capture_output=True,
        )


class LoaderTests(unittest.TestCase):
    def test_load_table_uses_full_virtual_asset_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wanted = "Pal/Content/Pal/DataTable/Character/DT_PalMonsterParameter_Common"
            write_table(root, wanted, {"Exact": {"Value": 1}})
            write_table(
                root,
                "Decoy/DT_PalMonsterParameter_Common",
                {"Wrong": {"Value": 2}},
            )

            self.assertEqual(load_table(root, wanted), {"Exact": {"Value": 1}})

    def test_load_text_table_maps_base_and_l10n_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            name = "DT_PalNameText_Common"
            write_table(
                root,
                f"Pal/Content/Pal/DataTable/Text/{name}",
                {"PAL_NAME_TEST": {"TextData": {"LocalizedString": "Japanese"}}},
            )
            write_table(
                root,
                f"Pal/Content/L10N/zh-Hans/Pal/DataTable/Text/{name}",
                {"PAL_NAME_TEST": {"TextData": {"LocalizedString": "Simplified"}}},
            )

            self.assertIn("PAL_NAME_TEST", load_text_table(root, name, "ja"))
            self.assertEqual(
                load_text_table(root, name, "zh-CN")["PAL_NAME_TEST"]["TextData"][
                    "LocalizedString"
                ],
                "Simplified",
            )

    def test_load_table_rejects_missing_and_ambiguous_exports(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            virtual = "Pal/Content/Pal/DataTable/Test/DT_Test"
            with self.assertRaisesRegex(FileNotFoundError, "DT_Test"):
                load_table(root, virtual)
            path = root / f"{virtual}.json"
            path.parent.mkdir(parents=True)
            path.write_text(
                json.dumps(
                    [
                        {"Type": "DataTable", "Rows": {"A": {}}},
                        {"Type": "DataTable", "Rows": {"B": {}}},
                    ]
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "exactly one DataTable"):
                load_table(root, virtual)

    def test_load_table_rejects_noncanonical_virtual_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            canonical = "Pal/Content/Pal/DataTable/Test/DT_Test"
            write_table(root, canonical, {"Exact": {}})

            for virtual in (
                "Pal//Content/Pal/DataTable/Test/DT_Test",
                "Pal/./Content/Pal/DataTable/Test/DT_Test",
                "Pal/Content/Pal/DataTable/Test/DT_Test/",
            ):
                with (
                    self.subTest(virtual=virtual),
                    self.assertRaisesRegex(ValueError, "canonical"),
                ):
                    load_table(root, virtual)


class ToolchainTests(unittest.TestCase):
    def test_character_and_skill_exporters_request_scenario_prefix_roots(self) -> None:
        expected = {
            "Pal/Content/Pal/Blueprint/Spawner/Quest",
            (
                "Pal/Content/Pal/Blueprint/Spawner/SheetsVariant/"
                "BP_PalSpawner_Sheets_Quest_"
            ),
            "Pal/Content/Pal/Maps/MainWorld_5/PL_MainWorld5/_Generated_/oilrig_",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            toolchain = Toolchain(
                root / "uex.exe",
                root / "Mappings.usmap",
                UEX_REVISION,
                MAPPING_SHA256,
            )
            requested = {}

            def fake_export_sources(
                selected: Toolchain,
                paks_dir: Path,
                export_root: Path,
                profile_dir: Path,
                sources: set[str],
            ) -> None:
                self.assertEqual(selected, toolchain)
                requested.setdefault(profile_dir.parts[-2], set()).update(sources)
                for source in sources:
                    if source in {
                        game_data.CHARACTER_EVIDENCE_SOURCES["human_actions"],
                        game_data.CHARACTER_ROUTE_SOURCES["incident_world"],
                        *expected,
                    }:
                        write_asset(export_root, source, [])
                    else:
                        write_table(export_root, source, {})

            def fake_export_prefixes(
                selected: Toolchain,
                paks_dir: Path,
                export_root: Path,
                profile_dir: Path,
                prefixes: set[str],
            ) -> None:
                self.assertEqual(selected, toolchain)
                requested.setdefault(profile_dir.parts[-2], set()).update(prefixes)

            with (
                patch.object(
                    extract_game_data,
                    "export_sources",
                    side_effect=fake_export_sources,
                ),
                patch.object(
                    extract_game_data,
                    "export_prefixes",
                    side_effect=fake_export_prefixes,
                ),
                patch.object(
                    game_data,
                    "load_character_projection",
                    return_value=({"icon_sources": {}}, {}),
                ),
                patch.object(
                    extract_game_data,
                    "_capture_replacement_actor_sources",
                    return_value=set(),
                ),
            ):
                extract_game_data.export_skill_domain(
                    toolchain,
                    root / "paks",
                    root / "skills-export",
                    root / "skills-profiles",
                )
                extract_game_data.export_character_domain(
                    toolchain,
                    root / "paks",
                    root / "characters-export",
                    root / "characters-profiles",
                )

        self.assertEqual(
            expected - requested["skills-profiles"],
            set(),
            "skills exporter omitted scenario prefix roots",
        )
        self.assertEqual(
            expected - requested["characters-profiles"],
            set(),
            "character exporter omitted scenario prefix roots",
        )

    def test_prefix_export_roots_are_not_rewritten_as_single_packages(self) -> None:
        roots = {
            "Pal/Content/Pal/Blueprint/Spawner/Quest",
            (
                "Pal/Content/Pal/Blueprint/Spawner/SheetsVariant/"
                "BP_PalSpawner_Sheets_Quest_"
            ),
            "Pal/Content/Pal/Maps/MainWorld_5/PL_MainWorld5/_Generated_/oilrig_",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            toolchain = Toolchain(
                root / "uex.exe",
                root / "Mappings.usmap",
                UEX_REVISION,
                MAPPING_SHA256,
            )
            commands = []
            listed_children = {
                "Pal/Content/Pal/Blueprint/Spawner/SheetsVariant": (
                    "BP_PalSpawner_Sheets_Quest_Alpha.uasset\n"
                    "BP_PalSpawner_Sheets_Quest_Beta.umap\n"
                    "BP_PalSpawner_Sheets_Quest_Ignored.txt\n"
                    "BP_Unrelated.uasset\n"
                ),
                "Pal/Content/Pal/Maps/MainWorld_5/PL_MainWorld5/_Generated_": (
                    "oilrig_Alpha.umap\n"
                    "oilrig_Beta.uasset\n"
                    "nested/oilrig_Ignored.uasset\n"
                    "not_oilrig.uasset\n"
                ),
            }

            def fake_run(command: list[str], **kwargs):
                commands.append(command)
                if command[1] == "list":
                    return subprocess.CompletedProcess(
                        command,
                        0,
                        stdout=listed_children[command[2]],
                        stderr="",
                    )
                return subprocess.CompletedProcess(command, 0)

            with patch.object(
                extract_game_data.subprocess, "run", side_effect=fake_run
            ):
                extract_game_data.export_prefixes(
                    toolchain,
                    root / "paks",
                    root / "export",
                    root / "profiles",
                    roots,
                )
            profile = json.loads(
                (root / "profiles/export/profiles-0.json").read_text(encoding="utf-8")
            )

        exact_packages = {
            "Pal/Content/Pal/Blueprint/Spawner/Quest",
            (
                "Pal/Content/Pal/Blueprint/Spawner/SheetsVariant/"
                "BP_PalSpawner_Sheets_Quest_Alpha.uasset"
            ),
            (
                "Pal/Content/Pal/Blueprint/Spawner/SheetsVariant/"
                "BP_PalSpawner_Sheets_Quest_Beta.umap"
            ),
            (
                "Pal/Content/Pal/Maps/MainWorld_5/PL_MainWorld5/_Generated_/"
                "oilrig_Alpha.umap"
            ),
            (
                "Pal/Content/Pal/Maps/MainWorld_5/PL_MainWorld5/_Generated_/"
                "oilrig_Beta.uasset"
            ),
        }
        self.assertEqual(
            set(profile["profiles"]["palworld"]["exportRoots"]), exact_packages
        )
        list_commands = [command for command in commands if command[1] == "list"]
        self.assertEqual(
            {command[2] for command in list_commands}, set(listed_children)
        )
        export_commands = [command for command in commands if command[1] == "export"]
        self.assertEqual(len(export_commands), 1)
        only_index = export_commands[0].index("--only")
        self.assertEqual(set(export_commands[0][only_index + 1 :]), exact_packages)

    def test_prefix_export_fails_closed_when_uex_lists_no_matching_packages(
        self,
    ) -> None:
        prefix = (
            "Pal/Content/Pal/Blueprint/Spawner/SheetsVariant/"
            "BP_PalSpawner_Sheets_Quest_"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            toolchain = Toolchain(
                root / "uex.exe",
                root / "Mappings.usmap",
                UEX_REVISION,
                MAPPING_SHA256,
            )
            completed = subprocess.CompletedProcess(
                [], 0, stdout="BP_Unrelated.uasset\nnested/Bad.uasset\n", stderr=""
            )
            with (
                patch.object(
                    extract_game_data.subprocess, "run", return_value=completed
                ) as mocked_run,
                self.assertRaisesRegex(
                    ValueError, "UEX list found no packages for filename prefix"
                ),
            ):
                extract_game_data.export_prefixes(
                    toolchain,
                    root / "paks",
                    root / "export",
                    root / "profiles",
                    {prefix},
                )

        self.assertEqual(mocked_run.call_count, 1)
        self.assertEqual(
            mocked_run.call_args.args[0][1:3],
            ["list", prefix.rpartition("/")[0]],
        )

    def test_unknown_build_write_requires_explicit_override(self) -> None:
        with self.assertRaisesRegex(ValueError, "99999999"):
            require_write_build("99999999", False)

        require_write_build("99999999", True)
        require_write_build(KNOWN_BUILD, False)

    def test_toolchain_rejects_unpinned_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            uex = root / "uex.exe"
            mapping = root / "Mappings.usmap"
            uex.write_bytes(b"not executed")
            mapping.write_bytes(b"wrong mapping")

            with self.assertRaisesRegex(ValueError, MAPPING_SHA256):
                ensure_toolchain(root, uex, mapping)

    def test_toolchain_requires_pinned_parser_revision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            uex = root / "uex.exe"
            mapping = root / "Mappings.usmap"
            uex.write_bytes(b"fixture")
            mapping.write_bytes(b"fixture mapping")
            fixture_hash = hashlib.sha256(mapping.read_bytes()).hexdigest()
            completed = subprocess.CompletedProcess(
                [str(uex), "--version"], 0, stdout="1.0.0+wrong-revision\n", stderr=""
            )

            with (
                patch.object(extract_game_data, "MAPPING_SHA256", fixture_hash),
                patch.object(
                    extract_game_data.subprocess, "run", return_value=completed
                ),
                self.assertRaisesRegex(ValueError, UEX_REVISION),
            ):
                ensure_toolchain(root, uex, mapping)

    def test_steam_manifest_reports_pinned_build_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            library = Path(directory)
            game = library / "steamapps/common/Palworld"
            (game / "Pal/Content/Paks").mkdir(parents=True)
            (game / "Pal/Content/Paks/Pal-Windows.pak").write_bytes(b"pak")
            (library / "steamapps/appmanifest_1623730.acf").write_text(
                f'"AppState" {{ "buildid" "{KNOWN_BUILD}" }}', encoding="utf-8"
            )

            self.assertEqual(detect_build_id(game), KNOWN_BUILD)


class DoctorTests(unittest.TestCase):
    def test_doctor_mounts_and_parses_without_mutating_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            game = root / "steamapps/common/Palworld"
            paks = game / "Pal/Content/Paks"
            paks.mkdir(parents=True)
            (paks / "Pal-Windows.pak").write_bytes(b"pak")
            (root / "steamapps/appmanifest_1623730.acf").write_text(
                f'"AppState" {{ "buildid" "{KNOWN_BUILD}" }}', encoding="utf-8"
            )
            (root / "assets/data").mkdir(parents=True)
            (root / "assets/data/sentinel.json").write_text(
                "unchanged", encoding="utf-8"
            )
            before = snapshot(root)
            toolchain = Toolchain(
                root / "uex.exe", root / "Mappings.usmap", UEX_REVISION, MAPPING_SHA256
            )

            def fake_export(
                selected: Toolchain, paks_dir: Path, export_root: Path, profile: Path
            ) -> None:
                self.assertEqual(selected, toolchain)
                self.assertEqual(paks_dir, paks)
                for virtual in DOCTOR_ASSETS:
                    write_table(export_root, virtual, {"Fixture": {}})

            output = io.StringIO()
            old_cwd = Path.cwd()
            try:
                os.chdir(root)
                with (
                    patch.object(
                        extract_game_data, "ensure_toolchain", return_value=toolchain
                    ),
                    patch.object(
                        extract_game_data, "export_game", side_effect=fake_export
                    ),
                    patch("sys.stdout", output),
                ):
                    result = run_doctor(game_dir=game)
            finally:
                os.chdir(old_cwd)

            self.assertEqual(result["game_build"], KNOWN_BUILD)
            self.assertEqual(result["uex_revision"], UEX_REVISION)
            self.assertEqual(set(result["source_counts"]), set(DOCTOR_ASSETS))
            self.assertIn(KNOWN_BUILD, output.getvalue())
            self.assertEqual(snapshot(root), before)


class PublisherTests(unittest.TestCase):
    @staticmethod
    def installed_skills_candidate(outputs: dict[str, bytes] | None = None):
        policy = json.loads(extract_game_data.POLICY_PATH.read_text(encoding="utf-8"))
        selected = outputs or {
            relative: (extract_game_data.RUNTIME_ASSETS / Path(relative)).read_bytes()
            for relative in (
                "data/pal_attacks.json",
                "data/pal_passives.json",
            )
        }
        bootstrap = policy["bootstrap"]
        candidate = snapshot_from_outputs(
            "skills",
            selected,
            BuildIdentity(
                bootstrap["game_build"],
                bootstrap["uex_revision"],
                bootstrap["mapping_sha256"],
            ),
            domain_policy_hash(policy, "skills"),
            {source: 1 for source in policy["domains"]["skills"]["required_sources"]},
        )
        attacks = json.loads(selected["data/pal_attacks.json"])
        sources = SourceInventory(
            present_sources=frozenset(policy["domains"]["skills"]["required_sources"]),
            reference_ids={
                "characters": frozenset(
                    learner["CharacterID"]
                    for row in attacks.values()
                    for learner in row["Learners"]
                )
            },
            available_icons=frozenset(),
            approved_static_icons=frozenset(),
        )
        return policy, candidate, sources

    def test_known_build_skill_forgery_is_rejected_before_any_mutation(self) -> None:
        policy, original, _sources = self.installed_skills_candidate()
        active_path = "data/pal_attacks.json"
        passive_path = "data/pal_passives.json"
        original_attacks = json.loads(original.outputs[active_path])
        original_passives = json.loads(original.outputs[passive_path])
        legal_fruit = next(
            skill_id for skill_id, row in original_attacks.items() if row["SkillFruit"]
        )
        boss_skill = next(
            skill_id for skill_id, row in original_attacks.items() if row["BossSkill"]
        )
        ordinary_skill = next(
            skill_id
            for skill_id, row in original_attacks.items()
            if not row["BossSkill"]
        )
        removable_active = next(
            skill_id
            for skill_id in original_attacks
            if skill_id not in {"EPalWazaID::Human_Punch", "EPalWazaID::Psychokinesis"}
        )

        def forged_outputs(kind: str) -> dict[str, bytes]:
            attacks = deepcopy(original_attacks)
            passives = deepcopy(original_passives)
            if kind == "psychokinesis-fruit":
                attacks["EPalWazaID::Psychokinesis"]["SkillFruit"] = True
            elif kind == "missing-nushi":
                del passives["Nushi"]
            elif kind == "missing-active":
                del attacks[removable_active]
            elif kind == "human-exclusive":
                attacks["EPalWazaID::Human_Punch"]["Exclusive"] = True
            elif kind == "fruit-swap":
                attacks["EPalWazaID::Psychokinesis"]["SkillFruit"] = True
                attacks[legal_fruit]["SkillFruit"] = False
            elif kind == "boss-skill-swap":
                attacks[boss_skill]["BossSkill"] = False
                attacks[ordinary_skill]["BossSkill"] = True
            return {
                active_path: json_bytes(attacks),
                passive_path: json_bytes(passives),
            }

        expected = {
            "psychokinesis-fruit": "legal_fruit_ids",
            "missing-nushi": "passive_ids",
            "missing-active": "active_ids",
            "human-exclusive": "Human_Punch",
            "fruit-swap": "legal_fruit_ids",
            "boss-skill-swap": "boss_skill_ids",
        }
        for kind, fragment in expected.items():
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                assets = root / "assets"
                stage = root / "stage"
                provenance = root / "provenance.json"
                assets.mkdir()
                marker = assets / "marker.txt"
                marker.write_bytes(b"unchanged")
                _, forged, forged_sources = self.installed_skills_candidate(
                    forged_outputs(kind)
                )
                stage_candidate(stage, forged)
                before = snapshot(assets)

                errors = validate_domain(
                    "skills",
                    forged,
                    forged_sources,
                    Manifest(1, {}, {}),
                    policy,
                )
                self.assertTrue(any(fragment in error for error in errors), errors)
                with self.assertRaises(ValueError):
                    publish_domain(
                        stage,
                        assets,
                        "skills",
                        forged,
                        Manifest(1, {}, {}),
                        policy=policy,
                        sources=forged_sources,
                        provenance_path=provenance,
                    )

                self.assertEqual(snapshot(assets), before)

    def test_known_build_character_forgery_is_rejected_before_any_mutation(
        self,
    ) -> None:
        outputs = fixture_outputs()["characters"]
        pals = json.loads(outputs["data/pal_data.json"])
        king_whale = pals.pop("TestPal")
        king_whale.update(
            {
                "InternalName": "KingWhale",
                "FamilyID": "KingWhale",
                "IconKey": "KingWhale",
            }
        )
        anubis = deepcopy(king_whale)
        anubis.update(
            {
                "InternalName": "Anubis",
                "FamilyID": "Anubis",
                "IconKey": "Anubis",
                "I18n": text_i18n("anubis"),
            }
        )
        pals = {"KingWhale": king_whale, "Anubis": anubis}
        outputs["data/pal_data.json"] = json_bytes(pals)
        humans = json.loads(outputs["data/human_data.json"])
        outputs["data/human_data.json"] = json_bytes(humans)
        skins = json.loads(outputs["data/skin_data.json"])
        skins["TestSkin"]["TargetPalName"] = "KingWhale"
        outputs["data/skin_data.json"] = json_bytes(skins)
        outputs["icons/pals/KingWhale.png"] = outputs.pop("icons/pals/TestPal.png")
        outputs["icons/pals/Anubis.png"] = PNG_2X2

        def output_root(candidate_outputs: dict[str, bytes]) -> str:
            digest = hashlib.sha256()
            for path, data in sorted(candidate_outputs.items()):
                digest.update(path.encode("utf-8"))
                digest.update(b"\0")
                digest.update(hashlib.sha256(data).hexdigest().encode("ascii"))
                digest.update(b"\n")
            return digest.hexdigest()

        policy = deepcopy(FIXTURE_POLICY)
        json_paths = tuple(path for path in outputs if path.endswith(".json"))
        policy["domains"]["characters"]["known_build_invariants"] = {
            KNOWN_BUILD: {
                "json_outputs": {
                    path: {
                        "count": len(json.loads(outputs[path])),
                        "sha256": hashlib.sha256(outputs[path]).hexdigest(),
                    }
                    for path in sorted(json_paths)
                },
                "output_count": len(outputs),
                "output_root_sha256": output_root(outputs),
            }
        }
        sources = replace(
            fixture_sources(),
            reference_ids={
                **fixture_sources().reference_ids,
                "characters": frozenset({"KingWhale", "Anubis", "TestHuman"}),
            },
        )

        def candidate(candidate_outputs: dict[str, bytes]):
            dimensions = {
                path: ((1, 1) if data == PNG_1X1 else (2, 2))
                for path, data in candidate_outputs.items()
                if path.endswith(".png")
            }
            return snapshot_from_outputs(
                "characters",
                candidate_outputs,
                IDENTITY,
                domain_policy_hash(policy, "characters"),
                {source: 1 for source in REQUIRED_SOURCES["characters"]},
                icon_dimensions=dimensions,
            )

        original = candidate(outputs)
        self.assertEqual(
            validate_domain(
                "characters", original, sources, Manifest(1, {}, {}), policy
            ),
            [],
        )

        mutations = {}
        for name in ("hp", "localized-name", "family-casing"):
            changed = deepcopy(outputs)
            rows = json.loads(changed["data/pal_data.json"])
            if name == "hp":
                rows["KingWhale"]["Stats"]["HP"] += 1
            elif name == "localized-name":
                rows["KingWhale"]["I18n"]["en"] = "Forged KingWhale"
            else:
                rows["KingWhale"]["FamilyID"] = "kingwhale"
            changed["data/pal_data.json"] = json_bytes(rows)
            mutations[name] = changed
        changed = deepcopy(outputs)
        rows = json.loads(changed["data/pal_data.json"])
        rows["KingWhale"]["IconKey"] = "unknown"
        changed["data/pal_data.json"] = json_bytes(rows)
        del changed["icons/pals/KingWhale.png"]
        mutations["justified-static-fallback"] = changed
        changed = deepcopy(outputs)
        changed["icons/pals/KingWhale.png"] = changed["icons/pals/Anubis.png"]
        mutations["png-substitution"] = changed

        for name, changed in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                assets = root / "assets"
                stage = root / "stage"
                assets.mkdir()
                marker = assets / "marker.txt"
                marker.write_bytes(b"unchanged")
                forged = candidate(changed)
                stage_candidate(stage, forged)
                before = snapshot(assets)

                errors = validate_domain(
                    "characters", forged, sources, Manifest(1, {}, {}), policy
                )
                self.assertTrue(
                    any("known-build invariant" in error for error in errors),
                    errors,
                )
                with self.assertRaisesRegex(ValueError, "known-build invariant"):
                    publish_domain(
                        stage,
                        assets,
                        "characters",
                        forged,
                        Manifest(1, {}, {}),
                        policy=policy,
                        sources=sources,
                        provenance_path=root / "provenance.json",
                    )

                self.assertEqual(snapshot(assets), before)
                self.assertFalse((root / "provenance.json").exists())

    def test_publish_replaces_only_manifest_managed_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "assets"
            stage = root / "stage"
            provenance = root / "provenance.json"
            old = fixture_candidate("skills")
            candidate = changed_candidate("skills")
            write_candidate(assets, old)
            unmanaged = assets / "data/unmanaged.json"
            unmanaged.write_bytes(b"unchanged")
            unmanaged_hash = hashlib.sha256(unmanaged.read_bytes()).hexdigest()
            stage_candidate(stage, candidate)
            existing = Manifest(
                1, {"fixture": True}, {"skills": candidate_manifest(old)}
            )

            result = publish_domain(
                stage,
                assets,
                "skills",
                candidate,
                existing,
                policy=FIXTURE_POLICY,
                sources=fixture_sources(),
                provenance_path=provenance,
            )

            for relative, expected in candidate.outputs.items():
                self.assertEqual(
                    assets.joinpath(*relative.split("/")).read_bytes(), expected
                )
            self.assertEqual(
                hashlib.sha256(unmanaged.read_bytes()).hexdigest(), unmanaged_hash
            )
            self.assertEqual(result.domains["skills"], candidate_manifest(candidate))
            self.assertEqual(
                manifest_from_dict(json.loads(provenance.read_bytes())), result
            )

    def test_publish_rolls_back_all_replacements_after_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "assets"
            stage = root / "stage"
            provenance = root / "provenance.json"
            old = fixture_candidate("characters")
            candidate = changed_candidate("characters")
            write_candidate(assets, old)
            stale = assets / "icons/pals/Stale.png"
            stale.parent.mkdir(parents=True, exist_ok=True)
            stale.write_bytes(PNG_1X1)
            old_entry = candidate_manifest(old)
            old_entry = replace(
                old_entry,
                managed_paths=old_entry.managed_paths + ("icons/pals/Stale.png",),
                output_hashes={
                    **old_entry.output_hashes,
                    "icons/pals/Stale.png": hashlib.sha256(PNG_1X1).hexdigest(),
                },
            )
            existing = Manifest(1, {"fixture": True}, {"characters": old_entry})
            provenance.write_bytes(manifest_bytes(existing))
            stage_candidate(stage, candidate)
            before_assets = snapshot(assets)
            before_provenance = provenance.read_bytes()
            real_replace = os.replace
            replacements = 0

            def fail_after_first_replacement(source, destination):
                nonlocal replacements
                target = Path(destination)
                if target.is_relative_to(assets):
                    replacements += 1
                    if replacements == 2:
                        raise OSError("injected after first replacement")
                return real_replace(source, destination)

            with (
                patch("game_data.os.replace", side_effect=fail_after_first_replacement),
                self.assertRaisesRegex(OSError, "injected"),
            ):
                publish_domain(
                    stage,
                    assets,
                    "characters",
                    candidate,
                    existing,
                    policy=FIXTURE_POLICY,
                    sources=fixture_sources(),
                    provenance_path=provenance,
                )

            self.assertEqual(snapshot(assets), before_assets)
            self.assertEqual(provenance.read_bytes(), before_provenance)

    def test_publish_rolls_back_atomic_provenance_after_late_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "assets"
            stage = root / "stage"
            provenance = root / "provenance.json"
            old = fixture_candidate("skills")
            candidate = changed_candidate("skills")
            write_candidate(assets, old)
            stage_candidate(stage, candidate)
            existing = Manifest(
                1, {"fixture": True}, {"skills": candidate_manifest(old)}
            )
            provenance.write_bytes(manifest_bytes(existing))
            before_assets = snapshot(assets)
            before_provenance = provenance.read_bytes()
            real_replace = os.replace
            failed = False

            def fail_after_provenance_replace(source, destination):
                nonlocal failed
                result = real_replace(source, destination)
                if Path(destination) == provenance and not failed:
                    failed = True
                    raise OSError("injected after provenance replacement")
                return result

            with (
                patch(
                    "game_data.os.replace", side_effect=fail_after_provenance_replace
                ),
                self.assertRaisesRegex(OSError, "injected"),
            ):
                publish_domain(
                    stage,
                    assets,
                    "skills",
                    candidate,
                    existing,
                    policy=FIXTURE_POLICY,
                    sources=fixture_sources(),
                    provenance_path=provenance,
                )

            self.assertEqual(snapshot(assets), before_assets)
            self.assertEqual(provenance.read_bytes(), before_provenance)

    def test_manifest_paths_reject_absolute_parent_symlink_and_outside_assets(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "assets"
            stage = root / "stage"
            provenance = root / "provenance.json"
            assets.mkdir()
            marker = assets / "marker.txt"
            marker.write_bytes(b"unchanged")
            candidate = fixture_candidate("skills")
            stage_candidate(stage, candidate)
            base_entry = candidate_manifest(fixture_candidate("characters"))

            invalid_path_sets = (
                ("C:/outside.png",),
                ("/outside.png",),
                ("../outside.png",),
                ("data/../outside.png",),
                ("data\\outside.png",),
                ("data//outside.png",),
                ("data/./outside.png",),
                ("data/Duplicate.png", "data/Duplicate.png"),
                ("data/Case.png", "data/case.png"),
            )
            for paths in invalid_path_sets:
                with self.subTest(paths=paths):
                    bad_entry = replace(
                        base_entry,
                        managed_paths=paths,
                        output_hashes={path: "0" * 64 for path in paths},
                    )
                    existing = Manifest(1, {}, {"characters": bad_entry})
                    with self.assertRaises(ValueError):
                        publish_domain(
                            stage,
                            assets,
                            "skills",
                            candidate,
                            existing,
                            policy=FIXTURE_POLICY,
                            sources=fixture_sources(),
                            provenance_path=provenance,
                        )
                    self.assertEqual(marker.read_bytes(), b"unchanged")
                    self.assertFalse(provenance.exists())

            outside = root / "outside"
            outside.mkdir()
            link = assets / "linked"
            make_directory_link(link, outside)
            bad_entry = replace(
                base_entry,
                managed_paths=("linked/outside.png",),
                output_hashes={"linked/outside.png": "0" * 64},
            )
            with self.assertRaises(ValueError):
                publish_domain(
                    stage,
                    assets,
                    "skills",
                    candidate,
                    Manifest(1, {}, {"characters": bad_entry}),
                    policy=FIXTURE_POLICY,
                    sources=fixture_sources(),
                    provenance_path=provenance,
                )
            self.assertEqual(list(outside.iterdir()), [])

            inside_target = assets / "inside-target"
            inside_target.mkdir()
            inside_link = assets / "inside-linked"
            make_directory_link(inside_link, inside_target)
            bad_entry = replace(
                base_entry,
                managed_paths=("inside-linked/output.png",),
                output_hashes={"inside-linked/output.png": "0" * 64},
            )
            with self.assertRaisesRegex(ValueError, "symlink|reparse"):
                publish_domain(
                    stage,
                    assets,
                    "skills",
                    candidate,
                    Manifest(1, {}, {"characters": bad_entry}),
                    policy=FIXTURE_POLICY,
                    sources=fixture_sources(),
                    provenance_path=provenance,
                )

            directory_target = assets / "data/directory.json"
            directory_target.mkdir(parents=True)
            bad_entry = replace(
                base_entry,
                managed_paths=("data/directory.json",),
                output_hashes={"data/directory.json": "0" * 64},
            )
            with self.assertRaises(ValueError):
                publish_domain(
                    stage,
                    assets,
                    "skills",
                    candidate,
                    Manifest(1, {}, {"characters": bad_entry}),
                    policy=FIXTURE_POLICY,
                    sources=fixture_sources(),
                    provenance_path=provenance,
                )

    def test_domain_publish_preserves_other_domain_files_and_manifest_entries(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "assets"
            stage = root / "stage"
            provenance = root / "provenance.json"
            candidates = fixture_candidates()
            for current in candidates.values():
                write_candidate(assets, current)
            existing = fixture_manifest(candidates)
            candidate = changed_candidate("skills")
            stage_candidate(stage, candidate)
            other_bytes = {
                path: data
                for domain, current in candidates.items()
                if domain != "skills"
                for path, data in current.outputs.items()
            }
            other_entries = {
                domain: manifest_bytes(Manifest(1, {}, {domain: entry}))
                for domain, entry in existing.domains.items()
                if domain != "skills"
            }

            result = publish_domain(
                stage,
                assets,
                "skills",
                candidate,
                existing,
                policy=FIXTURE_POLICY,
                sources=fixture_sources(),
                provenance_path=provenance,
            )

            for relative, expected in other_bytes.items():
                self.assertEqual(
                    assets.joinpath(*relative.split("/")).read_bytes(), expected
                )
            for domain, expected in other_entries.items():
                actual = manifest_bytes(
                    Manifest(1, {}, {domain: result.domains[domain]})
                )
                self.assertEqual(actual, expected)
            self.assertEqual(result.bootstrap, existing.bootstrap)

    def test_partial_publish_rejects_mixed_toolchain_identity_without_relabeling_domains(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "assets"
            stage = root / "stage"
            provenance = root / "provenance.json"
            candidate = fixture_candidate("skills")
            stage_candidate(stage, candidate)
            old_identity = BuildIdentity(KNOWN_BUILD, UEX_REVISION, "0" * 64)
            old_character = replace(
                fixture_candidate("characters"), identity=old_identity
            )
            existing = Manifest(
                1,
                {"fixture": True},
                {"characters": candidate_manifest(old_character)},
            )
            assets.mkdir()
            before = snapshot(assets)
            before_manifest = manifest_bytes(existing)

            with self.assertRaisesRegex(ValueError, "toolchain identity"):
                publish_domain(
                    stage,
                    assets,
                    "skills",
                    candidate,
                    existing,
                    policy=FIXTURE_POLICY,
                    sources=fixture_sources(),
                    provenance_path=provenance,
                )

            self.assertEqual(snapshot(assets), before)
            self.assertEqual(manifest_bytes(existing), before_manifest)
            self.assertFalse(provenance.exists())

    def test_invalid_candidate_finishes_validation_before_any_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "assets"
            stage = root / "stage"
            assets.mkdir()
            marker = assets / "marker.txt"
            marker.write_bytes(b"unchanged")
            candidate = fixture_candidate("skills")
            stage_candidate(stage, candidate)
            forged = replace(candidate, hashes={})

            with self.assertRaisesRegex(ValueError, "hash"):
                publish_domain(
                    stage,
                    assets,
                    "skills",
                    forged,
                    Manifest(1, {}, {}),
                    policy=FIXTURE_POLICY,
                    sources=fixture_sources(),
                    provenance_path=root / "provenance.json",
                )

            self.assertEqual(
                snapshot(assets),
                {"marker.txt": hashlib.sha256(b"unchanged").hexdigest()},
            )

    def test_publish_rejects_stale_policy_hash_before_any_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "assets"
            stage = root / "stage"
            provenance = root / "provenance.json"
            old = fixture_candidate("skills")
            write_candidate(assets, old)
            candidate = replace(changed_candidate("skills"), policy_sha256="0" * 64)
            stage_candidate(stage, candidate)
            existing = Manifest(1, {}, {"skills": candidate_manifest(old)})
            before_assets = snapshot(assets)
            before_manifest = manifest_bytes(existing)

            with self.assertRaisesRegex(ValueError, "policy"):
                publish_domain(
                    stage,
                    assets,
                    "skills",
                    candidate,
                    existing,
                    policy=FIXTURE_POLICY,
                    sources=fixture_sources(),
                    provenance_path=provenance,
                )

            self.assertEqual(snapshot(assets), before_assets)
            self.assertEqual(manifest_bytes(existing), before_manifest)
            self.assertFalse(provenance.exists())

    def test_publish_rejects_forged_empty_unresolved_report_before_mutation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "assets"
            stage = root / "stage"
            provenance = root / "provenance.json"
            assets.mkdir()
            marker = assets / "marker.txt"
            marker.write_bytes(b"unchanged")
            outputs = fixture_outputs()["characters"]
            rows = json.loads(outputs["data/pal_data.json"])
            rows["TestPal"]["Attacks"] = {"MissingSkill": 1}
            outputs["data/pal_data.json"] = json_bytes(rows)
            candidate = fixture_candidate("characters", outputs)
            self.assertEqual(candidate.missing_references, ())
            stage_candidate(stage, candidate)
            existing = Manifest(1, {}, {})
            before_assets = snapshot(assets)
            before_manifest = manifest_bytes(existing)

            with self.assertRaisesRegex(ValueError, "MissingSkill|unresolved"):
                publish_domain(
                    stage,
                    assets,
                    "characters",
                    candidate,
                    existing,
                    policy=FIXTURE_POLICY,
                    sources=fixture_sources(),
                    provenance_path=provenance,
                )

            self.assertEqual(snapshot(assets), before_assets)
            self.assertEqual(manifest_bytes(existing), before_manifest)
            self.assertFalse(provenance.exists())

    def test_legacy_deletion_requires_exact_independent_review_plan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "assets"
            stage = root / "stage"
            owned = {
                "icons/pals/OwnedA.png": PNG_1X1,
                "icons/pals/skin/OwnedB.png": PNG_2X2,
                "icons/pals/Human.png": PNG_1X1,
                "icons/pals/unknown.png": PNG_1X1,
            }
            for relative, data in owned.items():
                target = assets.joinpath(*relative.split("/"))
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            candidate = fixture_candidate("characters")
            stage_candidate(stage, candidate)
            accepted = [
                {"path": path, "sha256": hashlib.sha256(data).hexdigest()}
                for path, data in sorted(owned.items())
            ]
            candidate_path, ownership_path, _, ownership = write_ownership_evidence(
                root, accepted
            )
            proposal = build_legacy_deletion_proposal(
                "characters",
                candidate,
                assets,
                candidate_path,
                ownership_path,
            )
            expected = {
                path: item["sha256"]
                for path, item in zip(sorted(owned), accepted, strict=True)
                if path not in game_data._STATIC_PAL_ICONS
            }
            self.assertEqual(
                {item["path"] for item in proposal["paths"]}, set(expected)
            )
            for item in proposal["paths"]:
                self.assertEqual(
                    {
                        "path",
                        "current_sha256",
                        "baseline_sha256",
                        "backup_sha256",
                        "candidate_output_state",
                        "record_reference_state",
                        "record_references",
                        "reason",
                    },
                    set(item),
                )
                self.assertEqual(item["current_sha256"], expected[item["path"]])
                self.assertEqual(item["baseline_sha256"], expected[item["path"]])
                self.assertEqual(item["backup_sha256"], expected[item["path"]])
                self.assertEqual(item["candidate_output_state"], "absent")
                self.assertEqual(item["record_reference_state"], "none")
                self.assertEqual(item["record_references"], [])
                self.assertEqual(item["reason"], "not_referenced_by_candidate_records")
            self.assertEqual(
                set(proposal["candidate_snapshot"]),
                {
                    "domain",
                    "game_build",
                    "parser_revision",
                    "mapping_sha256",
                    "policy_sha256",
                    "json_outputs",
                    "metrics",
                    "output_count",
                    "output_root_sha256",
                    "output_hashes",
                },
            )
            approval = {
                "schema_version": 2,
                "kind": "legacy_change_approval",
                "reviewer": "fixture-independent-deletion-reviewer",
                "review_date": "2026-07-26",
                "approved_plan_sha256": proposal["plan_sha256"],
                "approved_deletions": proposal["paths"],
                "approved_renames": proposal["renames"],
            }
            before = snapshot(assets)

            bad_proposals = []
            bad = deepcopy(proposal)
            bad["paths"] = bad["paths"][:-1]
            bad_proposals.append(bad)
            bad = deepcopy(proposal)
            bad["paths"].append(
                {"path": "icons/pals/Extra.png", "existing_sha256": "0" * 64}
            )
            bad_proposals.append(bad)
            bad = deepcopy(proposal)
            bad["paths"][0]["current_sha256"] = "0" * 64
            bad_proposals.append(bad)
            bad = deepcopy(proposal)
            bad["candidate_snapshot"]["output_hashes"] = {}
            bad_proposals.append(bad)
            bad = deepcopy(proposal)
            bad["domain"] = "technology"
            bad_proposals.append(bad)
            bad = deepcopy(proposal)
            bad["ownership_evidence"]["candidate_artifact_sha256"] = "0" * 64
            bad_proposals.append(bad)
            bad = deepcopy(proposal)
            bad["plan_sha256"] = "0" * 64
            bad_proposals.append(bad)

            for bad_proposal in bad_proposals:
                with (
                    self.subTest(proposal=bad_proposal),
                    self.assertRaisesRegex(ValueError, "proposal|plan"),
                ):
                    publish_domain(
                        stage,
                        assets,
                        "characters",
                        candidate,
                        Manifest(1, {}, {}),
                        policy=FIXTURE_POLICY,
                        sources=fixture_sources(),
                        provenance_path=root / "provenance.json",
                        legacy_candidate_path=candidate_path,
                        legacy_ownership_path=ownership_path,
                        legacy_deletion_proposal=bad_proposal,
                        legacy_deletion_approval=approval,
                    )
                self.assertEqual(snapshot(assets), before)
                self.assertFalse((root / "provenance.json").exists())

            bad_approvals = []
            bad = deepcopy(approval)
            bad["approved_plan_sha256"] = "0" * 64
            bad_approvals.append(bad)
            bad = deepcopy(approval)
            bad["proposal"] = deepcopy(proposal)
            bad_approvals.append(bad)
            bad = deepcopy(approval)
            bad["reviewer"] = ""
            bad_approvals.append(bad)
            bad = deepcopy(approval)
            bad["reviewer"] = ownership["review"]["reviewer"]
            bad_approvals.append(bad)
            bad = deepcopy(approval)
            bad["unexpected"] = True
            bad_approvals.append(bad)
            bad = deepcopy(approval)
            del bad["approved_plan_sha256"]
            bad_approvals.append(bad)

            for bad_approval in bad_approvals:
                with (
                    self.subTest(approval=bad_approval),
                    self.assertRaisesRegex(ValueError, "approval|reviewer"),
                ):
                    publish_domain(
                        stage,
                        assets,
                        "characters",
                        candidate,
                        Manifest(1, {}, {}),
                        policy=FIXTURE_POLICY,
                        sources=fixture_sources(),
                        provenance_path=root / "provenance.json",
                        legacy_candidate_path=candidate_path,
                        legacy_ownership_path=ownership_path,
                        legacy_deletion_proposal=proposal,
                        legacy_deletion_approval=bad_approval,
                    )
                self.assertEqual(snapshot(assets), before)
                self.assertFalse((root / "provenance.json").exists())

            publish_domain(
                stage,
                assets,
                "characters",
                candidate,
                Manifest(1, {}, {}),
                policy=FIXTURE_POLICY,
                sources=fixture_sources(),
                provenance_path=root / "provenance.json",
                legacy_candidate_path=candidate_path,
                legacy_ownership_path=ownership_path,
                legacy_deletion_proposal=proposal,
                legacy_deletion_approval=approval,
            )
            for path in owned:
                exists = assets.joinpath(*path.split("/")).exists()
                self.assertEqual(exists, path in game_data._STATIC_PAL_ICONS)

    def test_case_only_rename_is_reviewed_and_rolls_back_exact_casing(self) -> None:
        def setup(root: Path):
            assets = root / "assets"
            stage = root / "stage"
            old_path = "icons/tech/TESTTECH.png"
            old_target = assets.joinpath(*old_path.split("/"))
            old_target.parent.mkdir(parents=True)
            old_target.write_bytes(PNG_1X1)
            candidate = fixture_candidate("technology")
            stage_candidate(stage, candidate)
            digest = hashlib.sha256(PNG_1X1).hexdigest()
            candidate_path, ownership_path, _, ownership = write_ownership_evidence(
                root, [{"path": "icons/tech/TestTech.png", "sha256": digest}]
            )
            proposal = build_legacy_deletion_proposal(
                "technology", candidate, assets, candidate_path, ownership_path
            )
            approval = {
                "schema_version": 2,
                "kind": "legacy_change_approval",
                "reviewer": "fixture-independent-change-reviewer",
                "review_date": "2026-07-26",
                "approved_plan_sha256": proposal["plan_sha256"],
                "approved_deletions": proposal["paths"],
                "approved_renames": proposal["renames"],
            }
            self.assertNotEqual(approval["reviewer"], ownership["review"]["reviewer"])
            return assets, stage, candidate, candidate_path, ownership_path, proposal, approval

        def exact_names(assets: Path) -> set[str]:
            return {path.name for path in (assets / "icons/tech").iterdir()}

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (
                assets,
                stage,
                candidate,
                candidate_path,
                ownership_path,
                proposal,
                approval,
            ) = setup(root)
            self.assertEqual(proposal["schema_version"], 3)
            self.assertEqual(proposal["kind"], "legacy_change_proposal")
            self.assertEqual(proposal["paths"], [])
            self.assertEqual(
                proposal["renames"],
                [
                    {
                        "from_path": "icons/tech/TESTTECH.png",
                        "to_path": "icons/tech/TestTech.png",
                        "current_sha256": hashlib.sha256(PNG_1X1).hexdigest(),
                        "baseline_sha256": hashlib.sha256(PNG_1X1).hexdigest(),
                        "backup_sha256": hashlib.sha256(PNG_1X1).hexdigest(),
                        "candidate_sha256": hashlib.sha256(PNG_2X2).hexdigest(),
                        "candidate_output_state": "case_only_rename",
                        "reason": "candidate_uses_canonical_path_casing",
                    }
                ],
            )

            bad_approval = deepcopy(approval)
            bad_approval["approved_renames"][0]["to_path"] = (
                "icons/tech/Testtech.png"
            )
            with self.assertRaisesRegex(ValueError, "approval"):
                publish_domain(
                    stage,
                    assets,
                    "technology",
                    candidate,
                    Manifest(1, {}, {}),
                    policy=FIXTURE_POLICY,
                    sources=fixture_sources(),
                    provenance_path=root / "provenance.json",
                    legacy_candidate_path=candidate_path,
                    legacy_ownership_path=ownership_path,
                    legacy_deletion_proposal=proposal,
                    legacy_deletion_approval=bad_approval,
                )
            self.assertIn("TESTTECH.png", exact_names(assets))
            self.assertNotIn("TestTech.png", exact_names(assets))

            publish_domain(
                stage,
                assets,
                "technology",
                candidate,
                Manifest(1, {}, {}),
                policy=FIXTURE_POLICY,
                sources=fixture_sources(),
                provenance_path=root / "provenance.json",
                legacy_candidate_path=candidate_path,
                legacy_ownership_path=ownership_path,
                legacy_deletion_proposal=proposal,
                legacy_deletion_approval=approval,
            )
            self.assertIn("TestTech.png", exact_names(assets))
            self.assertNotIn("TESTTECH.png", exact_names(assets))
            self.assertEqual(PNG_2X2, (assets / "icons/tech/TestTech.png").read_bytes())

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (
                assets,
                stage,
                candidate,
                candidate_path,
                ownership_path,
                proposal,
                approval,
            ) = setup(root)
            real_replace = os.replace
            calls = 0

            def fail_once(source, destination):
                nonlocal calls
                calls += 1
                if calls == 3:
                    raise OSError("injected after case-only rename")
                return real_replace(source, destination)

            with (
                patch.object(game_data.os, "replace", side_effect=fail_once),
                self.assertRaisesRegex(OSError, "injected"),
            ):
                publish_domain(
                    stage,
                    assets,
                    "technology",
                    candidate,
                    Manifest(1, {}, {}),
                    policy=FIXTURE_POLICY,
                    sources=fixture_sources(),
                    provenance_path=root / "provenance.json",
                    legacy_candidate_path=candidate_path,
                    legacy_ownership_path=ownership_path,
                    legacy_deletion_proposal=proposal,
                    legacy_deletion_approval=approval,
                )
            self.assertIn("TESTTECH.png", exact_names(assets))
            self.assertNotIn("TestTech.png", exact_names(assets))
            self.assertEqual(PNG_1X1, (assets / "icons/tech/TESTTECH.png").read_bytes())
            self.assertFalse((assets / "data/tech_data.json").exists())
            self.assertFalse((root / "provenance.json").exists())

    def test_deletion_plan_binds_invalid_allowed_missing_skin_reference(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "assets"
            path = "icons/pals/skin/OwnedB.png"
            target = assets.joinpath(*path.split("/"))
            target.parent.mkdir(parents=True)
            target.write_bytes(PNG_2X2)
            outputs = fixture_outputs()["characters"]
            skins = json.loads(outputs["data/skin_data.json"])
            skins["TestSkin"]["Invalid"] = True
            skins["TestSkin"]["IconKey"] = "OwnedB"
            outputs["data/skin_data.json"] = json_bytes(skins)
            candidate = replace(
                fixture_candidate("characters", outputs),
                missing_icons=(path,),
            )
            digest = hashlib.sha256(PNG_2X2).hexdigest()
            candidate_path, ownership_path, _, _ = write_ownership_evidence(
                root, [{"path": path, "sha256": digest}]
            )

            proposal = build_legacy_deletion_proposal(
                "characters", candidate, assets, candidate_path, ownership_path
            )

            self.assertEqual(len(proposal["paths"]), 1)
            item = proposal["paths"][0]
            self.assertEqual(item["record_reference_state"], "invalid_allowed_missing")
            self.assertEqual(
                item["record_references"],
                [
                    {
                        "output_path": "data/skin_data.json",
                        "record_id": "TestSkin",
                        "field": "IconKey",
                        "state": "invalid_allowed_missing",
                    }
                ],
            )
            self.assertEqual(
                item["reason"], "referenced_only_by_invalid_allowed_missing_record"
            )

    def test_publish_allows_invalid_skin_missing_icon_with_approved_deletion(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "assets"
            stage = root / "stage"
            path = "icons/pals/skin/OwnedB.png"
            target = assets.joinpath(*path.split("/"))
            target.parent.mkdir(parents=True)
            target.write_bytes(PNG_2X2)
            outputs = fixture_outputs()["characters"]
            skins = json.loads(outputs["data/skin_data.json"])
            skins["TestSkin"]["Invalid"] = True
            skins["TestSkin"]["IconKey"] = "OwnedB"
            outputs["data/skin_data.json"] = json_bytes(skins)
            candidate = replace(
                fixture_candidate("characters", outputs),
                missing_icons=(path,),
            )
            stage_candidate(stage, candidate)
            digest = hashlib.sha256(PNG_2X2).hexdigest()
            candidate_path, ownership_path, _, _ = write_ownership_evidence(
                root, [{"path": path, "sha256": digest}]
            )
            proposal = build_legacy_deletion_proposal(
                "characters", candidate, assets, candidate_path, ownership_path
            )
            approval = {
                "schema_version": 2,
                "kind": "legacy_change_approval",
                "reviewer": "fixture-independent-deletion-reviewer",
                "review_date": "2026-07-26",
                "approved_plan_sha256": proposal["plan_sha256"],
                "approved_deletions": proposal["paths"],
                "approved_renames": proposal["renames"],
            }

            result = publish_domain(
                stage,
                assets,
                "characters",
                candidate,
                Manifest(1, {}, {}),
                policy=FIXTURE_POLICY,
                sources=fixture_sources(),
                provenance_path=root / "provenance.json",
                legacy_candidate_path=candidate_path,
                legacy_ownership_path=ownership_path,
                legacy_deletion_proposal=proposal,
                legacy_deletion_approval=approval,
            )

            self.assertFalse(target.exists())
            self.assertEqual(
                result.domains["characters"], candidate_manifest(candidate)
            )
            self.assertTrue((root / "provenance.json").is_file())

    def test_publish_rejects_valid_skin_missing_icon_before_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "assets"
            stage = root / "stage"
            provenance = root / "provenance.json"
            assets.mkdir()
            marker = assets / "marker.txt"
            marker.write_bytes(b"unchanged")
            outputs = fixture_outputs()["characters"]
            skins = json.loads(outputs["data/skin_data.json"])
            skins["TestSkin"]["IconKey"] = "MissingSkin"
            outputs["data/skin_data.json"] = json_bytes(skins)
            del outputs["icons/pals/skin/TestSkin.png"]
            missing = "icons/pals/skin/MissingSkin.png"
            candidate = replace(
                fixture_candidate("characters", outputs),
                missing_icons=(missing,),
            )
            stage_candidate(stage, candidate)
            before = snapshot(assets)

            with self.assertRaisesRegex(ValueError, "unresolved output icon"):
                publish_domain(
                    stage,
                    assets,
                    "characters",
                    candidate,
                    Manifest(1, {}, {}),
                    policy=FIXTURE_POLICY,
                    sources=fixture_sources(),
                    provenance_path=provenance,
                )

            self.assertEqual(snapshot(assets), before)
            self.assertFalse(provenance.exists())

    def test_legacy_ownership_approval_alone_cannot_delete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "assets"
            stage = root / "stage"
            owned = {
                "icons/pals/OwnedA.png": PNG_1X1,
                "icons/pals/skin/OwnedB.png": PNG_2X2,
            }
            for relative, data in owned.items():
                target = assets.joinpath(*relative.split("/"))
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            candidate = fixture_candidate("characters")
            stage_candidate(stage, candidate)
            accepted = [
                {"path": path, "sha256": hashlib.sha256(data).hexdigest()}
                for path, data in sorted(owned.items())
            ]
            candidate_path, ownership_path, _, ownership = write_ownership_evidence(
                root, accepted
            )
            self.assertEqual(
                ownership["review"]["decision"],
                "approved_ownership_evidence_only",
            )
            self.assertFalse(any("deletion" in key for key in ownership))
            before = snapshot(assets)

            with self.assertRaisesRegex(ValueError, "deletion approval"):
                publish_domain(
                    stage,
                    assets,
                    "characters",
                    candidate,
                    Manifest(1, {}, {}),
                    policy=FIXTURE_POLICY,
                    sources=fixture_sources(),
                    provenance_path=root / "provenance.json",
                    legacy_candidate_path=candidate_path,
                    legacy_ownership_path=ownership_path,
                )

            self.assertEqual(snapshot(assets), before)


class LegacyOwnershipTests(unittest.TestCase):
    def test_managed_domain_skips_one_shot_legacy_evidence(self) -> None:
        candidate = fixture_candidate("characters")
        existing = Manifest(
            1,
            {},
            {"characters": candidate_manifest(candidate)},
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "assets"
            assets.mkdir()

            proposal = build_legacy_deletion_proposal(
                "characters",
                candidate,
                assets,
                root / "missing-candidate.json",
                root / "missing-ownership.json",
                existing=existing,
            )

        self.assertIsNone(proposal)

    def test_legacy_candidate_writer_refuses_self_approval(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "legacy_ownership_candidate.json"
            candidate = {
                "schema_version": 1,
                "accepted": [],
                "plan_sha256": hashlib.sha256(b"[]").hexdigest(),
                "review_approval": None,
            }

            write_legacy_ownership_candidate(output, candidate)

            self.assertEqual(json.loads(output.read_bytes()), candidate)
            with self.assertRaisesRegex(ValueError, "unapproved"):
                write_legacy_ownership_candidate(
                    output,
                    {**candidate, "review_approval": {"reviewer": "self"}},
                )
            self.assertEqual(json.loads(output.read_bytes()), candidate)

    def test_legacy_ownership_accepts_only_scoped_tracked_backup_hash_matches(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            assets = repo / "src/palworld_pal_editor/assets"
            backup = repo / "backup"
            baseline_files = {
                "icons/pals/Good.png": b"pal",
                "icons/pals/skin/GoodSkin.png": b"skin",
                "icons/tech/GoodTech.png": b"tech",
                "icons/elements/Element_Fire.png": b"element",
                "icons/pals/ChangedCurrent.png": b"current",
                "icons/pals/ChangedBackup.png": b"backup",
                "icons/pals/Directory.png": b"directory",
                "icons/pals/Linked.png": b"linked",
            }
            for relative, data in baseline_files.items():
                assets.joinpath(*relative.split("/")).parent.mkdir(
                    parents=True, exist_ok=True
                )
                assets.joinpath(*relative.split("/")).write_bytes(data)
                backup.joinpath(*relative.split("/")).parent.mkdir(
                    parents=True, exist_ok=True
                )
                backup.joinpath(*relative.split("/")).write_bytes(data)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "add", "src"], cwd=repo, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Fixture",
                    "-c",
                    "user.email=fixture@example.invalid",
                    "commit",
                    "-qm",
                    "baseline",
                ],
                cwd=repo,
                check=True,
            )
            baseline = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            (assets / "icons/pals/ChangedCurrent.png").write_bytes(b"changed")
            (backup / "icons/pals/ChangedBackup.png").write_bytes(b"changed")
            (assets / "icons/pals/Directory.png").unlink()
            (assets / "icons/pals/Directory.png").mkdir()
            linked = assets / "icons/pals/Linked.png"
            linked.unlink()
            linked_target = repo / "linked-target"
            linked_target.mkdir()
            make_directory_link(linked, linked_target)
            (assets / "icons/pals/Untracked.png").write_bytes(b"untracked")
            (backup / "icons/pals/Untracked.png").write_bytes(b"untracked")

            candidate = build_legacy_ownership_candidate(repo, assets, backup, baseline)

            self.assertEqual(
                candidate["accepted"],
                [
                    {
                        "path": "icons/pals/Good.png",
                        "sha256": hashlib.sha256(b"pal").hexdigest(),
                    },
                    {
                        "path": "icons/pals/skin/GoodSkin.png",
                        "sha256": hashlib.sha256(b"skin").hexdigest(),
                    },
                    {
                        "path": "icons/tech/GoodTech.png",
                        "sha256": hashlib.sha256(b"tech").hexdigest(),
                    },
                ],
            )
            self.assertIsNone(candidate["review_approval"])
            self.assertEqual(candidate["accepted_count"], 3)
            self.assertEqual(
                candidate["plan_sha256"], legacy_plan_hash(candidate["accepted"])
            )


class ValidationTests(unittest.TestCase):
    def test_character_snapshot_metrics_count_records_reuse_and_unresolved_ids(
        self,
    ) -> None:
        outputs = fixture_outputs()["characters"]
        rows = json.loads(outputs["data/pal_data.json"])
        variant = deepcopy(rows["TestPal"])
        variant.update(
            {
                "InternalName": "TestVariant",
                "FamilyID": "TestPal",
                "VariantKind": "other",
                "VariantTags": [],
            }
        )
        unresolved = deepcopy(rows["TestPal"])
        unresolved.update(
            {
                "InternalName": "RAID_Unresolved",
                "FamilyID": "RawRaidTribe",
                "FamilyResolved": False,
                "IconKey": "unknown",
                "Invalid": True,
                "RegularlyObtainable": False,
                "ObtainMethods": [],
                "AvailabilitySources": [],
                "VariantKind": "raid",
                "VariantTags": ["raid"],
            }
        )
        rows.update({"TestVariant": variant, "RAID_Unresolved": unresolved})
        outputs["data/pal_data.json"] = json_bytes(rows)

        metrics = game_data.character_snapshot_metrics(
            fixture_candidate("characters", outputs)
        )

        self.assertEqual(metrics["character_records"], 4)
        self.assertEqual(metrics["unknown_icon_records"], 1)
        self.assertEqual(metrics["human_static_icon_records"], 1)
        self.assertEqual(metrics["game_icon_records"], 2)
        self.assertEqual(metrics["game_icon_unique_keys"], 1)
        self.assertEqual(metrics["game_icon_reused_records"], 1)
        self.assertEqual(metrics["unresolved_family_ids"], ["RAID_Unresolved"])

    def test_character_snapshot_metrics_report_exact_installed_scenario_census(
        self,
    ) -> None:
        pals = {}
        humans = {}

        def add_record(target: dict, character_id: str, *tags: str) -> None:
            row = fixture_character_fields(character_id, character_id)
            row["VariantTags"] = sorted(tags)
            row["VariantKind"] = tags[0]
            target[character_id] = row

        for tag, count in (
            ("predator", 48),
            ("raid", 19),
            ("tower", 31),
            ("boss-rush", 8),
            ("quest", 7),
            ("oilrig", 6),
            ("summon", 4),
        ):
            for index in range(count):
                add_record(pals, f"Pal_{tag}_{index}", tag)
        add_record(pals, "GYM_ElecPanda_Otomo", "tower", "otomo")
        add_record(pals, "BOSS_KingWhale_otomo", "boss", "otomo")
        for tag, count in (("quest", 7), ("oilrig", 19)):
            for index in range(count):
                add_record(humans, f"Human_{tag}_{index}", "human", tag)
        outputs = fixture_outputs()["characters"]
        outputs["data/pal_data.json"] = json_bytes(pals)
        outputs["data/human_data.json"] = json_bytes(humans)

        metrics = game_data.character_snapshot_metrics(
            fixture_candidate("characters", outputs)
        )
        self.assertIn("scenario_identity_counts", metrics)
        census = metrics["scenario_identity_counts"]

        self.assertEqual(
            census,
            {
                "pals": {
                    "predator": 48,
                    "raid": 19,
                    "tower": 32,
                    "boss-rush": 8,
                    "quest": 7,
                    "oilrig": 6,
                    "summon": 4,
                    "otomo": 2,
                },
                "humans": {"quest": 7, "oilrig": 19},
                "combined": {"quest": 14, "oilrig": 25},
            },
        )

    def test_skill_output_relationships_are_recomputed_from_output_bytes(self) -> None:
        cases = []

        outputs = fixture_outputs()["skills"]
        rows = json.loads(outputs["data/pal_attacks.json"])
        rows["TestSkill"]["Exclusive"] = True
        outputs["data/pal_attacks.json"] = json_bytes(rows)
        cases.append((outputs, "Exclusive"))

        outputs = fixture_outputs()["skills"]
        rows = json.loads(outputs["data/pal_attacks.json"])
        rows["TestSkill"]["Disabled"] = True
        outputs["data/pal_attacks.json"] = json_bytes(rows)
        cases.append((outputs, "Disabled"))

        outputs = fixture_outputs()["skills"]
        rows = json.loads(outputs["data/pal_attacks.json"])
        rows["TestSkill"]["Learners"].append({"CharacterID": "TestPal", "Level": 1})
        outputs["data/pal_attacks.json"] = json_bytes(rows)
        cases.append((outputs, "duplicate learner"))

        for outputs, fragment in cases:
            with self.subTest(fragment=fragment):
                errors = fixture_errors("skills", fixture_candidate("skills", outputs))
                self.assertTrue(any(fragment in error for error in errors), errors)

    def test_known_build_invariants_are_not_reused_for_an_unknown_build(self) -> None:
        policy = json.loads(extract_game_data.POLICY_PATH.read_text(encoding="utf-8"))
        known_candidate = PublisherTests.installed_skills_candidate()[1]
        attacks = json.loads(known_candidate.outputs["data/pal_attacks.json"])
        attacks["EPalWazaID::Psychokinesis"]["SkillFruit"] = True
        forged_outputs = dict(known_candidate.outputs)
        forged_outputs["data/pal_attacks.json"] = json_bytes(attacks)
        _, forged, sources = PublisherTests.installed_skills_candidate(forged_outputs)

        known_errors = validate_domain(
            "skills", forged, sources, Manifest(1, {}, {}), policy
        )
        self.assertTrue(
            any("legal_fruit_ids" in error for error in known_errors), known_errors
        )

        unknown_policy = deepcopy(policy)
        unknown_policy["bootstrap"]["game_build"] = "future-build"
        unknown_candidate = snapshot_from_outputs(
            "skills",
            forged.outputs,
            replace(forged.identity, game_build="future-build"),
            domain_policy_hash(unknown_policy, "skills"),
            forged.source_counts,
        )
        unknown_errors = validate_domain(
            "skills",
            unknown_candidate,
            sources,
            Manifest(1, {}, {}),
            unknown_policy,
        )
        self.assertFalse(
            any("known-build invariant" in error for error in unknown_errors),
            unknown_errors,
        )

    def test_character_invariant_is_not_reused_for_an_unknown_build(self) -> None:
        outputs = fixture_outputs()["characters"]

        def root(candidate_outputs: dict[str, bytes]) -> str:
            digest = hashlib.sha256()
            for path, data in sorted(candidate_outputs.items()):
                digest.update(path.encode())
                digest.update(b"\0")
                digest.update(hashlib.sha256(data).hexdigest().encode())
                digest.update(b"\n")
            return digest.hexdigest()

        policy = deepcopy(FIXTURE_POLICY)
        policy["domains"]["characters"]["known_build_invariants"] = {
            KNOWN_BUILD: {
                "json_outputs": {
                    path: {
                        "count": len(json.loads(data)),
                        "sha256": hashlib.sha256(data).hexdigest(),
                    }
                    for path, data in outputs.items()
                    if path.endswith(".json")
                },
                "output_count": len(outputs),
                "output_root_sha256": root(outputs),
            }
        }
        changed = deepcopy(outputs)
        rows = json.loads(changed["data/pal_data.json"])
        rows["TestPal"]["Stats"]["HP"] += 1
        changed["data/pal_data.json"] = json_bytes(rows)
        known = snapshot_from_outputs(
            "characters",
            changed,
            IDENTITY,
            domain_policy_hash(policy, "characters"),
            {source: 1 for source in REQUIRED_SOURCES["characters"]},
            icon_dimensions=fixture_candidate("characters").icon_dimensions,
        )
        known_errors = validate_domain(
            "characters", known, fixture_sources(), Manifest(1, {}, {}), policy
        )
        self.assertTrue(
            any("known-build invariant" in error for error in known_errors),
            known_errors,
        )

        unknown_policy = deepcopy(policy)
        unknown_policy["bootstrap"]["game_build"] = "future-build"
        unknown = replace(
            known,
            identity=replace(known.identity, game_build="future-build"),
            policy_sha256=domain_policy_hash(unknown_policy, "characters"),
        )
        unknown_errors = validate_domain(
            "characters",
            unknown,
            fixture_sources(),
            Manifest(1, {}, {}),
            unknown_policy,
        )
        self.assertFalse(
            any("known-build invariant" in error for error in unknown_errors),
            unknown_errors,
        )

    def test_missing_required_source_fails_validation(self) -> None:
        missing = REQUIRED_SOURCES["characters"][0]
        sources = fixture_sources(
            present={
                source
                for paths in REQUIRED_SOURCES.values()
                for source in paths
                if source != missing
            }
        )

        errors = validate_domain(
            "characters",
            fixture_candidate("characters"),
            sources,
            Manifest(1, {}, {}),
            FIXTURE_POLICY,
        )

        self.assertTrue(any(missing in error for error in errors), errors)

    def test_empty_source_inventory_cannot_bypass_policy_requirements(self) -> None:
        errors = fixture_errors(
            "characters",
            fixture_candidate("characters"),
            sources=fixture_sources(present=set()),
        )

        self.assertTrue(
            all(
                any(source in error for error in errors)
                for source in REQUIRED_SOURCES["characters"]
            ),
            errors,
        )

    def test_present_required_source_with_zero_count_fails_validation(self) -> None:
        candidate = fixture_candidate("characters")
        counts = dict(candidate.source_counts)
        source = REQUIRED_SOURCES["characters"][0]
        counts[source] = 0

        errors = fixture_errors("characters", replace(candidate, source_counts=counts))

        self.assertTrue(
            any(source in error and "empty" in error for error in errors), errors
        )

    def test_every_output_row_must_match_schema_and_internal_name(self) -> None:
        outputs = fixture_outputs()["characters"]
        rows = json.loads(outputs["data/pal_data.json"])
        rows["TestPal"]["InternalName"] = "WrongPal"
        outputs["data/pal_data.json"] = json_bytes(rows)

        errors = validate_domain(
            "characters",
            fixture_candidate("characters", outputs),
            fixture_sources(),
            Manifest(1, {}, {}),
            FIXTURE_POLICY,
        )

        self.assertTrue(
            any("TestPal" in error and "InternalName" in error for error in errors),
            errors,
        )

    def test_output_schema_rejects_missing_required_field(self) -> None:
        outputs = fixture_outputs()["skills"]
        rows = json.loads(outputs["data/pal_attacks.json"])
        del rows["TestSkill"]["Learners"]
        outputs["data/pal_attacks.json"] = json_bytes(rows)

        errors = validate_domain(
            "skills",
            fixture_candidate("skills", outputs),
            fixture_sources(),
            Manifest(1, {}, {}),
            FIXTURE_POLICY,
        )

        self.assertTrue(any("Learners" in error for error in errors), errors)

    def test_skill_schemas_are_exact_and_reject_malformed_metadata(self) -> None:
        cases = []

        outputs = fixture_outputs()["skills"]
        rows = json.loads(outputs["data/pal_attacks.json"])
        rows["TestSkill"]["Unexpected"] = True
        outputs["data/pal_attacks.json"] = json_bytes(rows)
        cases.append((outputs, "Unexpected"))

        outputs = fixture_outputs()["skills"]
        rows = json.loads(outputs["data/pal_attacks.json"])
        rows["TestSkill"]["UniqueSkill"] = True
        outputs["data/pal_attacks.json"] = json_bytes(rows)
        cases.append((outputs, "UniqueSkill"))

        outputs = fixture_outputs()["skills"]
        rows = json.loads(outputs["data/pal_passives.json"])
        rows["TestPassive"]["Invocation"]["Always"] = "true"
        outputs["data/pal_passives.json"] = json_bytes(rows)
        cases.append((outputs, "Invocation"))

        outputs = fixture_outputs()["skills"]
        rows = json.loads(outputs["data/pal_passives.json"])
        rows["TestPassive"]["DescriptionSource"]["en"] = "legacy"
        outputs["data/pal_passives.json"] = json_bytes(rows)
        cases.append((outputs, "DescriptionSource"))

        for outputs, field in cases:
            with self.subTest(field=field):
                errors = fixture_errors("skills", fixture_candidate("skills", outputs))
                self.assertTrue(any(field in error for error in errors), errors)

    def test_every_output_path_rejects_invalid_field_types(self) -> None:
        cases = []

        outputs = fixture_outputs()["characters"]
        rows = json.loads(outputs["data/pal_data.json"])
        rows["TestPal"]["Attacks"] = [123]
        outputs["data/pal_data.json"] = json_bytes(rows)
        cases.append(("characters", outputs, "data/pal_data.json", "Attacks"))

        outputs = fixture_outputs()["characters"]
        rows = json.loads(outputs["data/human_data.json"])
        rows["TestHuman"]["DefaultPassives"] = [123]
        outputs["data/human_data.json"] = json_bytes(rows)
        cases.append(("characters", outputs, "data/human_data.json", "DefaultPassives"))

        outputs = fixture_outputs()["characters"]
        rows = json.loads(outputs["data/skin_data.json"])
        rows["TestSkin"]["TargetPalName"] = 123
        outputs["data/skin_data.json"] = json_bytes(rows)
        cases.append(("characters", outputs, "data/skin_data.json", "TargetPalName"))

        outputs = fixture_outputs()["skills"]
        rows = json.loads(outputs["data/pal_attacks.json"])
        rows["TestSkill"]["Learners"] = [{"CharacterID": 123, "Level": 1}]
        outputs["data/pal_attacks.json"] = json_bytes(rows)
        cases.append(("skills", outputs, "data/pal_attacks.json", "Learners"))

        outputs = fixture_outputs()["skills"]
        rows = json.loads(outputs["data/pal_passives.json"])
        rows["TestPassive"]["I18n"]["en"]["Name"] = ""
        outputs["data/pal_passives.json"] = json_bytes(rows)
        cases.append(("skills", outputs, "data/pal_passives.json", "Name"))

        outputs = fixture_outputs()["progression"]
        rows = json.loads(outputs["data/pal_exp_table.json"])
        rows["1"]["BuildEXP"] = "one"
        outputs["data/pal_exp_table.json"] = json_bytes(rows)
        cases.append(("progression", outputs, "data/pal_exp_table.json", "BuildEXP"))

        outputs = fixture_outputs()["progression"]
        rows = json.loads(outputs["data/pal_friendship.json"])
        rows["0"]["required_point"] = True
        outputs["data/pal_friendship.json"] = json_bytes(rows)
        cases.append(
            ("progression", outputs, "data/pal_friendship.json", "required_point")
        )

        outputs = fixture_outputs()["technology"]
        rows = json.loads(outputs["data/tech_data.json"])
        rows["TestTech"]["IconKind"] = "invalid"
        outputs["data/tech_data.json"] = json_bytes(rows)
        cases.append(("technology", outputs, "data/tech_data.json", "IconKind"))

        for domain, outputs, path, field in cases:
            with self.subTest(path=path, field=field):
                errors = fixture_errors(domain, fixture_candidate(domain, outputs))
                self.assertTrue(
                    any(path in error and field in error for error in errors), errors
                )

    def test_i18n_keys_are_exactly_the_17_supported_locales(self) -> None:
        outputs = fixture_outputs()["characters"]
        rows = json.loads(outputs["data/skin_data.json"])
        del rows["TestSkin"]["I18n"]["zh-TW"]
        outputs["data/skin_data.json"] = json_bytes(rows)

        errors = validate_domain(
            "characters",
            fixture_candidate("characters", outputs),
            fixture_sources(),
            Manifest(1, {}, {}),
            FIXTURE_POLICY,
        )

        self.assertTrue(
            any("17 supported locales" in error for error in errors), errors
        )

    def test_cross_references_must_resolve(self) -> None:
        outputs = fixture_outputs()["characters"]
        rows = json.loads(outputs["data/pal_data.json"])
        rows["TestPal"]["Attacks"] = {"MissingSkill": 1}
        outputs["data/pal_data.json"] = json_bytes(rows)

        errors = validate_domain(
            "characters",
            fixture_candidate("characters", outputs),
            fixture_sources(),
            Manifest(1, {}, {}),
            FIXTURE_POLICY,
        )

        self.assertTrue(any("MissingSkill" in error for error in errors), errors)

    def test_casefold_index_rejects_colliding_source_ids(self) -> None:
        with self.assertRaisesRegex(
            ValueError, r"IceWitch.*Icewitch|Icewitch.*IceWitch"
        ):
            casefold_index({"IceWitch": {}, "Icewitch": {}})

    def test_candidate_reference_inventory_rejects_missing_and_extra_entries(
        self,
    ) -> None:
        candidate = fixture_candidate("characters")
        extra = Reference(
            "data/pal_data.json",
            "TestPal",
            "Attacks",
            "skills",
            "StaleSkill",
        )
        for references in (candidate.references[:-1], candidate.references + (extra,)):
            with self.subTest(references=references):
                errors = fixture_errors(
                    "characters", replace(candidate, references=references)
                )
                self.assertTrue(
                    any("reference inventory" in error for error in errors), errors
                )

    def test_candidate_id_inventory_rejects_missing_extra_and_stale_entries(
        self,
    ) -> None:
        candidate = fixture_candidate("characters")
        inventories = []
        missing = dict(candidate.ids)
        missing["characters"] = frozenset({"TestHuman"})
        inventories.append(missing)
        extra = dict(candidate.ids)
        extra["characters"] = extra["characters"] | {"GhostCharacter"}
        inventories.append(extra)
        stale = dict(candidate.ids)
        stale["skills"] = frozenset({"StaleSkill"})
        inventories.append(stale)

        for ids in inventories:
            with self.subTest(ids=ids):
                errors = fixture_errors("characters", replace(candidate, ids=ids))
                self.assertTrue(
                    any("ID inventory" in error for error in errors), errors
                )

    def test_missing_references_report_must_exactly_match_derived_unresolved_refs(
        self,
    ) -> None:
        outputs = fixture_outputs()["characters"]
        rows = json.loads(outputs["data/pal_data.json"])
        rows["TestPal"]["Attacks"] = {"MissingSkill": 1}
        outputs["data/pal_data.json"] = json_bytes(rows)
        candidate = fixture_candidate("characters", outputs)
        expected = "data/pal_data.json:TestPal:Attacks->skills:MissingSkill"

        unreported = fixture_errors("characters", candidate)
        reported = fixture_errors(
            "characters", replace(candidate, missing_references=(expected,))
        )

        self.assertTrue(
            any("missing_references report" in error for error in unreported),
            unreported,
        )
        self.assertFalse(
            any("missing_references report" in error for error in reported),
            reported,
        )
        self.assertTrue(any(expected in error for error in reported), reported)

    def test_domain_rejects_missing_and_empty_required_outputs(self) -> None:
        outputs = fixture_outputs()["skills"]
        del outputs["data/pal_passives.json"]
        missing = fixture_errors("skills", fixture_candidate("skills", outputs))
        outputs = fixture_outputs()["skills"]
        outputs["data/pal_passives.json"] = json_bytes({})
        empty = fixture_errors("skills", fixture_candidate("skills", outputs))

        self.assertTrue(
            any(
                "missing required output data/pal_passives.json" in error
                for error in missing
            ),
            missing,
        )
        self.assertTrue(
            any(
                "empty required output data/pal_passives.json" in error
                for error in empty
            ),
            empty,
        )

    def test_domain_rejects_forbidden_wrong_domain_output(self) -> None:
        outputs = fixture_outputs()["skills"]
        outputs["data/pal_data.json"] = fixture_outputs()["characters"][
            "data/pal_data.json"
        ]

        errors = fixture_errors("skills", fixture_candidate("skills", outputs))

        self.assertTrue(
            any("forbidden output data/pal_data.json" in error for error in errors),
            errors,
        )

    def test_missing_character_skin_and_technology_icons_fail_validation(self) -> None:
        cases = []
        character = fixture_outputs()["characters"]
        del character["icons/pals/TestPal.png"]
        cases.append(("characters", character, "icons/pals/TestPal.png"))
        skin = fixture_outputs()["characters"]
        del skin["icons/pals/skin/TestSkin.png"]
        cases.append(("characters", skin, "icons/pals/skin/TestSkin.png"))
        technology = fixture_outputs()["technology"]
        del technology["icons/tech/TestTech.png"]
        cases.append(("technology", technology, "icons/tech/TestTech.png"))

        for domain, outputs, missing in cases:
            with self.subTest(domain=domain, missing=missing):
                errors = fixture_errors(domain, fixture_candidate(domain, outputs))
                self.assertTrue(any(missing in error for error in errors), errors)

    def test_invalid_skin_may_report_an_intentionally_missing_icon(self) -> None:
        outputs = fixture_outputs()["characters"]
        rows = json.loads(outputs["data/skin_data.json"])
        rows["TestSkin"]["Invalid"] = True
        outputs["data/skin_data.json"] = json_bytes(rows)
        missing = "icons/pals/skin/TestSkin.png"
        del outputs[missing]
        candidate = replace(
            fixture_candidate("characters", outputs), missing_icons=(missing,)
        )

        errors = fixture_errors("characters", candidate)

        self.assertFalse(
            any("unresolved output icon" in error for error in errors), errors
        )
        self.assertFalse(
            any("missing_icons report" in error for error in errors), errors
        )

    def test_character_metadata_and_availability_invariant_are_validated(self) -> None:
        outputs = fixture_outputs()["characters"]
        rows = json.loads(outputs["data/pal_data.json"])
        rows["TestPal"]["FamilyID"] = ""
        rows["TestPal"]["Invalid"] = True
        outputs["data/pal_data.json"] = json_bytes(rows)

        errors = fixture_errors("characters", fixture_candidate("characters", outputs))

        self.assertTrue(any("FamilyID must be" in error for error in errors), errors)
        self.assertTrue(
            any(
                "Invalid must equal not RegularlyObtainable" in error
                for error in errors
            ),
            errors,
        )

    def test_family_resolution_flag_must_match_collision_checked_character_index(
        self,
    ) -> None:
        outputs = fixture_outputs()["characters"]
        rows = json.loads(outputs["data/pal_data.json"])
        rows["TestPal"]["FamilyID"] = "RawMissingTribe"
        rows["TestPal"]["FamilyResolved"] = False
        outputs["data/pal_data.json"] = json_bytes(rows)
        unresolved = fixture_candidate("characters", outputs)

        self.assertFalse(
            any(
                "FamilyResolved" in error or "RawMissingTribe" in error
                for error in fixture_errors("characters", unresolved)
            ),
            fixture_errors("characters", unresolved),
        )

        rows["TestPal"]["FamilyResolved"] = True
        outputs["data/pal_data.json"] = json_bytes(rows)
        false_resolved = fixture_errors(
            "characters", fixture_candidate("characters", outputs)
        )
        self.assertTrue(
            any("FamilyResolved" in error for error in false_resolved), false_resolved
        )

        rows["TestPal"]["FamilyID"] = "testpal"
        rows["TestPal"]["FamilyResolved"] = False
        outputs["data/pal_data.json"] = json_bytes(rows)
        false_unresolved = fixture_errors(
            "characters", fixture_candidate("characters", outputs)
        )
        self.assertTrue(
            any("FamilyResolved" in error for error in false_unresolved),
            false_unresolved,
        )

    def test_static_character_fallback_requires_explicit_approval(self) -> None:
        sources = fixture_sources()
        unapproved = replace(sources, approved_static_icons=frozenset())

        errors = fixture_errors(
            "characters", fixture_candidate("characters"), sources=unapproved
        )

        self.assertTrue(
            any("icons/pals/Human.png" in error for error in errors), errors
        )

    def test_technology_pal_icon_resolves_through_character_inventory(self) -> None:
        outputs = fixture_outputs()["technology"]
        rows = json.loads(outputs["data/tech_data.json"])
        rows["TestTech"]["IconKind"] = "pal"
        rows["TestTech"]["IconKey"] = "TestPal"
        outputs["data/tech_data.json"] = json_bytes(rows)
        del outputs["icons/tech/TestTech.png"]

        errors = fixture_errors("technology", fixture_candidate("technology", outputs))

        self.assertEqual(errors, [])

    def test_png_header_and_dimensions_are_valid(self) -> None:
        outputs = fixture_outputs()["characters"]
        outputs["icons/pals/TestPal.png"] = b"bad signature" + PNG_1X1[13:]

        errors = validate_domain(
            "characters",
            fixture_candidate("characters", outputs),
            fixture_sources(),
            Manifest(1, {}, {}),
            FIXTURE_POLICY,
        )

        self.assertTrue(any("PNG signature" in error for error in errors), errors)

    def test_png_decode_rejects_invalid_compressed_data(self) -> None:
        outputs = fixture_outputs()["characters"]
        outputs["icons/pals/TestPal.png"] = png_bytes(1, 1, compressed=b"not-zlib")

        errors = validate_domain(
            "characters",
            fixture_candidate("characters", outputs),
            fixture_sources(),
            Manifest(1, {}, {}),
            FIXTURE_POLICY,
        )

        self.assertTrue(any("PNG decode" in error for error in errors), errors)

    def test_png_dimensions_must_match_candidate_inventory(self) -> None:
        candidate = fixture_candidate("characters")
        dimensions = dict(candidate.icon_dimensions)
        dimensions["icons/pals/TestPal.png"] = (2, 2)

        errors = validate_domain(
            "characters",
            replace(candidate, icon_dimensions=dimensions),
            fixture_sources(),
            Manifest(1, {}, {}),
            FIXTURE_POLICY,
        )

        self.assertTrue(any("expected 2x2" in error for error in errors), errors)

    def test_provenance_contains_complete_identity_counts_hashes_and_paths(
        self,
    ) -> None:
        candidate = fixture_candidate("skills")
        entry = candidate_manifest(candidate).to_dict()
        manifest = Manifest(
            1, {"fixture": True}, {"skills": candidate_manifest(candidate)}
        )

        self.assertEqual(
            set(entry),
            {
                "game_build",
                "parser_revision",
                "mapping_sha256",
                "policy_sha256",
                "source_counts",
                "output_counts",
                "output_hashes",
                "missing_references",
                "missing_localizations",
                "missing_icons",
                "managed_paths",
            },
        )
        self.assertEqual(entry["game_build"], KNOWN_BUILD)
        self.assertEqual(entry["parser_revision"], UEX_REVISION)
        self.assertEqual(entry["mapping_sha256"], MAPPING_SHA256)
        self.assertEqual(
            entry["policy_sha256"], domain_policy_hash(FIXTURE_POLICY, "skills")
        )
        self.assertEqual(entry["managed_paths"], sorted(candidate.outputs))
        self.assertEqual(set(entry["output_hashes"]), set(candidate.outputs))
        self.assertEqual(
            set(manifest.to_dict()), {"schema_version", "bootstrap", "domains"}
        )
        self.assertNotIn("game_build", manifest.to_dict()["bootstrap"])
        encoded = manifest_bytes(manifest)
        self.assertTrue(encoded.endswith(b"\n"))
        self.assertEqual(manifest_from_dict(json.loads(encoded)), manifest)


class RunDomainTests(unittest.TestCase):
    @staticmethod
    def toolchain() -> Toolchain:
        return Toolchain(Path("uex"), Path("usmap"), UEX_REVISION, MAPPING_SHA256)

    def test_all_check_exports_and_cross_validates_every_domain(self) -> None:
        exported = []

        def exporter(name: str):
            def run(_toolchain, _paks_dir, export_root, _profile_dir):
                export_root.mkdir(parents=True, exist_ok=True)
                (export_root / f"{name}.ready").write_text(name, encoding="utf-8")
                exported.append(name)

            return run

        def checked_builder(name: str):
            def build(export_root, _policy):
                if not (export_root / f"{name}.ready").is_file():
                    raise ValueError(f"{name} exporter was not run")
                return fixture_candidate(name)

            return build

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "assets"
            (assets / "icons/pals").mkdir(parents=True)
            for name in ("Human.png", "unknown.png"):
                (assets / "icons/pals" / name).write_bytes(PNG_1X1)
            builders = {domain: checked_builder(domain) for domain in DOMAINS}
            patches = [
                patch.object(extract_game_data, "find_game_dir", return_value=root),
                patch.object(extract_game_data, "detect_build_id", return_value=KNOWN_BUILD),
                patch.object(
                    extract_game_data,
                    "ensure_toolchain",
                    return_value=self.toolchain(),
                ),
                patch.object(
                    extract_game_data,
                    "_load_manifest",
                    return_value=Manifest(1, {}, {}),
                ),
                patch.object(extract_game_data, "_POLICY", deepcopy(FIXTURE_POLICY)),
                patch.object(extract_game_data, "export_skill_domain", exporter("skills")),
                patch.object(
                    extract_game_data,
                    "export_character_domain",
                    exporter("characters"),
                ),
                patch.object(
                    extract_game_data,
                    "export_progression_domain",
                    exporter("progression"),
                ),
                patch.object(
                    extract_game_data,
                    "export_technology_domain",
                    exporter("technology"),
                ),
                patch.dict(DOMAIN_BUILDERS, builders, clear=True),
                patch("sys.stdout", new=io.StringIO()),
            ]
            with patches[0], patches[1], patches[2], patches[3], patches[4], patches[
                5
            ], patches[6], patches[7], patches[8], patches[9], patches[10]:
                result = extract_game_data.run_domain(
                    domain="all",
                    write=False,
                    assets=assets,
                    provenance_path=root / "provenance.json",
                )

        self.assertEqual(exported, list(DOMAINS))
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["domain"], "all")
        self.assertEqual(set(result["domains"]), set(DOMAINS))
        for domain in DOMAINS:
            self.assertEqual(
                set(result["domains"][domain]["changed_paths"]),
                set(fixture_outputs()[domain]),
            )

    def test_all_write_requires_reviewed_publishers_before_game_access(self) -> None:
        with (
            patch.object(
                extract_game_data,
                "find_game_dir",
                side_effect=AssertionError("must reject before game access"),
            ),
            self.assertRaisesRegex(
                ValueError, "all --write requires separately reviewed publishers"
            ),
        ):
            extract_game_data.run_domain(domain="all", write=True)

    def test_matching_character_check_skips_stale_legacy_ownership(self) -> None:
        candidate = fixture_candidate("characters")

        def source_rows(_root, source):
            if source == game_data.CHARACTER_EVIDENCE_SOURCES["monsters"]:
                return {"TestPal": {}}
            if source == game_data.CHARACTER_EVIDENCE_SOURCES["humans"]:
                return {"TestHuman": {}}
            if source == game_data.SKILL_SOURCES["levels"]:
                return {"TestPal": {"WazaID": "TestSkill"}}
            if source == game_data.SKILL_SOURCES["passives"]:
                return {"TestPassive": {}}
            raise AssertionError(f"unexpected source: {source}")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "assets"
            write_candidate(assets, candidate)
            for name in ("Human.png", "unknown.png"):
                (assets / "icons/pals" / name).write_bytes(PNG_1X1)
            (assets / "data/pal_data.json").unlink()
            proposal_path = root / "character_deletion_proposal.json"
            proposal_path.write_text("unchanged", encoding="utf-8")
            existing = Manifest(
                1,
                {},
                {"characters": candidate_manifest(candidate)},
            )
            with (
                patch.object(extract_game_data, "find_game_dir", return_value=root),
                patch.object(
                    extract_game_data, "detect_build_id", return_value=KNOWN_BUILD
                ),
                patch.object(
                    extract_game_data,
                    "ensure_toolchain",
                    return_value=self.toolchain(),
                ),
                patch.object(
                    extract_game_data, "_load_manifest", return_value=existing
                ),
                patch.object(extract_game_data, "_POLICY", deepcopy(FIXTURE_POLICY)),
                patch.object(extract_game_data, "export_character_domain"),
                patch.object(extract_game_data, "load_table", side_effect=source_rows),
                patch.dict(
                    DOMAIN_BUILDERS,
                    {"characters": builder(candidate)},
                    clear=True,
                ),
                patch.object(
                    extract_game_data,
                    "LEGACY_OWNERSHIP_CANDIDATE",
                    root / "missing-candidate.json",
                ),
                patch.object(
                    extract_game_data,
                    "LEGACY_OWNERSHIP",
                    root / "missing-ownership.json",
                ),
                patch.object(
                    extract_game_data,
                    "CHARACTER_DELETION_PROPOSAL",
                    proposal_path,
                ),
                patch("sys.stdout", new=io.StringIO()),
            ):
                result = extract_game_data.run_domain(
                    domain="characters",
                    write=False,
                    assets=assets,
                    provenance_path=root / "provenance.json",
                )

            self.assertEqual(proposal_path.read_text(encoding="utf-8"), "unchanged")
            self.assertEqual(result["changed_paths"], ["data/pal_data.json"])
            self.assertEqual(result["deletion_count"], 0)
            self.assertIsNone(result["deletion_plan_sha256"])


class DomainCheckTests(unittest.TestCase):
    def test_all_domain_rejects_output_path_overlap(self) -> None:
        candidates = fixture_candidates()
        outputs = fixture_outputs()["technology"]
        outputs["icons/pals/TestPal.png"] = PNG_1X1
        candidates["technology"] = fixture_candidate("technology", outputs)
        builders = {
            domain: builder(candidate) for domain, candidate in candidates.items()
        }

        with patch.dict(DOMAIN_BUILDERS, builders, clear=True):
            result = check_domains(
                "all",
                Path("unused"),
                FIXTURE_POLICY,
                fixture_sources(),
                Manifest(1, {}, {}),
            )

        self.assertTrue(
            any("output path overlap" in error for error in result.errors),
            result.errors,
        )

    def test_all_domain_requires_every_builder(self) -> None:
        candidates = fixture_candidates()
        incomplete = {
            domain: builder(candidate)
            for domain, candidate in candidates.items()
            if domain != "technology"
        }

        with patch.dict(DOMAIN_BUILDERS, incomplete, clear=True):
            result = check_domains(
                "all",
                Path("unused"),
                FIXTURE_POLICY,
                fixture_sources(),
                Manifest(1, {}, {}),
            )

        self.assertTrue(
            any("technology" in error for error in result.errors), result.errors
        )
        self.assertEqual(result.manifest, Manifest(1, {}, {}))

    def test_all_domain_requires_cross_domain_reference(self) -> None:
        outputs = fixture_outputs()["characters"]
        rows = json.loads(outputs["data/pal_data.json"])
        rows["TestPal"]["Attacks"] = {"MissingSkill": 1}
        outputs["data/pal_data.json"] = json_bytes(rows)
        candidates = fixture_candidates()
        candidates["characters"] = fixture_candidate("characters", outputs)
        builders = {
            domain: builder(candidate) for domain, candidate in candidates.items()
        }

        with patch.dict(DOMAIN_BUILDERS, builders, clear=True):
            result = check_domains(
                "all",
                Path("unused"),
                FIXTURE_POLICY,
                fixture_sources(),
                Manifest(1, {}, {}),
            )

        self.assertTrue(
            any("MissingSkill" in error for error in result.errors), result.errors
        )

    def test_all_domain_ignores_stale_reference_inventory(self) -> None:
        outputs = fixture_outputs()["skills"]
        outputs["data/pal_attacks.json"] = json_bytes({})
        candidates = fixture_candidates()
        candidates["skills"] = fixture_candidate("skills", outputs)
        builders = {
            domain: builder(candidate) for domain, candidate in candidates.items()
        }

        with patch.dict(DOMAIN_BUILDERS, builders, clear=True):
            result = check_domains(
                "all",
                Path("unused"),
                FIXTURE_POLICY,
                fixture_sources(),
                Manifest(1, {}, {}),
            )

        self.assertTrue(
            any("TestSkill" in error for error in result.errors), result.errors
        )

    def test_all_domain_can_replace_every_toolchain_identity_together(self) -> None:
        old_identity = BuildIdentity("old-build", "old-parser", "0" * 64)
        old = {
            domain: candidate_manifest(replace(candidate, identity=old_identity))
            for domain, candidate in fixture_candidates().items()
        }
        existing = Manifest(1, {"fixture": True}, old)
        candidates = fixture_candidates()
        builders = {
            domain: builder(candidate) for domain, candidate in candidates.items()
        }

        with patch.dict(DOMAIN_BUILDERS, builders, clear=True):
            result = check_domains(
                "all", Path("unused"), FIXTURE_POLICY, fixture_sources(), existing
            )

        self.assertEqual(result.errors, ())
        self.assertTrue(
            all(
                entry.mapping_sha256 == MAPPING_SHA256
                for entry in result.manifest.domains.values()
            )
        )

    def test_partial_check_rejects_mixed_toolchain_identity_without_relabeling_domains(
        self,
    ) -> None:
        old_identity = BuildIdentity(KNOWN_BUILD, UEX_REVISION, "0" * 64)
        old_character = replace(fixture_candidate("characters"), identity=old_identity)
        existing = Manifest(
            1,
            {"fixture": True},
            {"characters": candidate_manifest(old_character)},
        )
        before = existing.to_dict()

        with patch.dict(
            DOMAIN_BUILDERS,
            {"skills": builder(fixture_candidate("skills"))},
            clear=True,
        ):
            result = check_domains(
                "skills", Path("unused"), FIXTURE_POLICY, fixture_sources(), existing
            )

        self.assertTrue(
            any("toolchain identity" in error for error in result.errors), result.errors
        )
        self.assertEqual(result.manifest, existing)
        self.assertEqual(existing.to_dict(), before)

    def test_domain_policy_hash_does_not_relabel_other_domains(self) -> None:
        changed = deepcopy(FIXTURE_POLICY)
        changed["domains"]["skills"]["option"] = "changed"

        self.assertNotEqual(
            domain_policy_hash(FIXTURE_POLICY, "skills"),
            domain_policy_hash(changed, "skills"),
        )
        for domain in ("characters", "progression", "technology"):
            self.assertEqual(
                domain_policy_hash(FIXTURE_POLICY, domain),
                domain_policy_hash(changed, domain),
            )

    def test_partial_check_updates_only_selected_manifest_entry(self) -> None:
        candidates = fixture_candidates()
        existing = fixture_manifest(candidates)
        outputs = fixture_outputs()["skills"]
        rows = json.loads(outputs["data/pal_attacks.json"])
        rows["TestSkill"]["CT"] = 2
        outputs["data/pal_attacks.json"] = json_bytes(rows)
        changed_skills = fixture_candidate("skills", outputs)

        with patch.dict(
            DOMAIN_BUILDERS, {"skills": builder(changed_skills)}, clear=True
        ):
            result = check_domains(
                "skills", Path("unused"), FIXTURE_POLICY, fixture_sources(), existing
            )

        self.assertEqual(result.errors, ())
        self.assertNotEqual(
            result.manifest.domains["skills"], existing.domains["skills"]
        )
        for domain in ("characters", "progression", "technology"):
            self.assertEqual(result.manifest.domains[domain], existing.domains[domain])

    def test_check_never_mutates_assets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "assets/data").mkdir(parents=True)
            (root / "assets/data/unmanaged.json").write_text(
                "unchanged", encoding="utf-8"
            )
            before = snapshot(root)

            with patch.dict(
                DOMAIN_BUILDERS,
                {"skills": builder(fixture_candidate("skills"))},
                clear=True,
            ):
                result = check_domains(
                    "skills",
                    root,
                    FIXTURE_POLICY,
                    fixture_sources(),
                    Manifest(1, {}, {}),
                )

            self.assertEqual(result.errors, ())
            self.assertEqual(snapshot(root), before)


class CharacterEvidenceTests(unittest.TestCase):
    MONSTERS = "Pal/Content/Pal/DataTable/Character/DT_PalMonsterParameter_Common"
    HUMANS = "Pal/Content/Pal/DataTable/Character/DT_PalHumanParameter_Common"
    PLACEMENTS = "Pal/Content/Pal/DataTable/Spawner/DT_PalSpawnerPlacement"
    HUMAN_ACTIONS = (
        "Pal/Content/Pal/Blueprint/Character/NPC/BP_NPC_StandardHumanDataSet"
    )
    ITEMS = game_data.SKILL_SOURCES["items"]

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.export_root = Path(self.temporary.name)
        self.policy = deepcopy(FIXTURE_POLICY)
        self.policy["domains"]["skills"]["required_sources"] = [
            self.MONSTERS,
            self.HUMANS,
            self.PLACEMENTS,
            self.HUMAN_ACTIONS,
            self.ITEMS,
            game_data.SKILL_SOURCES["bp_classes"],
            *game_data.RAID_REACHABILITY_SOURCES.values(),
            *game_data.CHARACTER_ROUTE_SOURCES.values(),
            *game_data.CHARACTER_SCENARIO_SOURCES.values(),
        ]
        self.policy["domains"]["skills"]["supported_routes"] = [
            "placement",
            "reached_wild",
            "dungeon",
            "cage",
            "fishing_spot",
            "fish_pond",
            "shop_table_direct",
            "invader",
            "visitor",
            "arena_solo",
            "raid_boss",
            "raid_egg",
            "raid_servant",
            "unique_breeding",
            "mainworld5_incident",
            "quest_spawner",
            "oilrig",
            "quest_reward",
            "capture_replace",
        ]
        self.policy["domains"]["characters"]["required_sources"] = list(
            self.policy["domains"]["skills"]["required_sources"]
        )
        self.policy["domains"]["characters"]["supported_routes"] = list(
            self.policy["domains"]["skills"]["supported_routes"]
        )
        for route, source in game_data.CHARACTER_ROUTE_SOURCES.items():
            if route == "incident_world":
                write_asset(self.export_root, source, [])
            else:
                write_table(self.export_root, source, {})
        write_table(self.export_root, self.ITEMS, {})
        for source in game_data.RAID_REACHABILITY_SOURCES.values():
            write_table(self.export_root, source, {})
        write_table(
            self.export_root,
            self.MONSTERS,
            {
                "BOSS_NotScenario": {
                    "Tribe": "EPalTribeID::BOSS_NotScenario",
                    "IsBoss": False,
                    "IsTowerBoss": False,
                    "IsRaidBoss": False,
                    "Predator": False,
                },
                "FriendlyLooking": {
                    "Tribe": "EPalTribeID::ScenarioFamily",
                    "IsBoss": False,
                    "IsTowerBoss": True,
                    "IsRaidBoss": False,
                    "Predator": True,
                },
                "ScenarioFamily": {
                    "Tribe": "EPalTribeID::ScenarioFamily",
                    "IsBoss": False,
                    "IsTowerBoss": False,
                    "IsRaidBoss": False,
                    "Predator": False,
                },
                "AlphaPal": {
                    "Tribe": "EPalTribeID::AlphaFamily",
                    "IsBoss": True,
                    "IsTowerBoss": False,
                    "IsRaidBoss": False,
                    "Predator": False,
                },
                "AlphaFamily": {
                    "Tribe": "EPalTribeID::AlphaFamily",
                    "IsBoss": False,
                    "IsTowerBoss": False,
                    "IsRaidBoss": False,
                    "Predator": False,
                },
                "Anubis": {
                    "Tribe": "EPalTribeID::Anubis",
                    "IsBoss": False,
                    "IsTowerBoss": False,
                    "IsRaidBoss": False,
                    "Predator": True,
                },
                "ElecPanda": {
                    "Tribe": "EPalTribeID::ElecPanda",
                    "IsBoss": False,
                    "IsTowerBoss": True,
                    "IsRaidBoss": False,
                    "Predator": True,
                },
                "BluePlatypus": {
                    "Tribe": "EPalTribeID::Blueplatypus",
                    "IsBoss": False,
                    "IsTowerBoss": False,
                    "IsRaidBoss": False,
                    "Predator": False,
                },
                "StrawHatCat": {
                    "Tribe": "EPalTribeID::Strawhatcat",
                    "IsBoss": False,
                    "IsTowerBoss": False,
                    "IsRaidBoss": False,
                    "Predator": False,
                },
                "RowName": {
                    "Tribe": "EPalTribeID::RowName",
                    "IsBoss": False,
                    "IsTowerBoss": False,
                    "IsRaidBoss": False,
                    "Predator": False,
                },
            },
        )
        write_table(
            self.export_root,
            self.HUMANS,
            {
                "ReachableHuman": {
                    "Tribe": "EPalTribeID::Human",
                    "IsBoss": False,
                    "IsTowerBoss": False,
                    "IsRaidBoss": False,
                },
                "UnreachableHuman": {
                    "Tribe": "EPalTribeID::Human",
                    "IsBoss": False,
                    "IsTowerBoss": False,
                    "IsRaidBoss": False,
                },
                "BossHuman": {
                    "Tribe": "EPalTribeID::Human",
                    "IsBoss": True,
                    "IsTowerBoss": False,
                    "IsRaidBoss": False,
                },
            },
        )
        monsters = load_table(self.export_root, self.MONSTERS)
        for character_id, row in monsters.items():
            row["BPClass"] = character_id
        write_table(self.export_root, self.MONSTERS, monsters)
        write_table(
            self.export_root,
            game_data.SKILL_SOURCES["bp_classes"],
            {
                character_id: {"BPClass": {"AssetPathName": "None"}}
                for character_id in monsters
            },
        )
        write_table(
            self.export_root,
            self.PLACEMENTS,
            {
                "OrdinaryPlacement": {
                    "SpawnerName": "ordinary",
                    "SpawnerType": "EPalSpawnedCharacterType::Common",
                    "PlacementType": "EPalSpawnerPlacementType::Field",
                    "SpawnerClass": {
                        "AssetPathName": (
                            "/Game/Pal/Blueprint/Spawner/BP_Ordinary.BP_Ordinary_C"
                        )
                    },
                },
                "AlphaPlacement": {
                    "SpawnerName": "alpha",
                    "SpawnerType": "EPalSpawnedCharacterType::FieldBoss",
                    "PlacementType": "EPalSpawnerPlacementType::FieldBoss",
                    "SpawnerClass": {
                        "AssetPathName": "/Game/Pal/Blueprint/Spawner/BP_Alpha.BP_Alpha_C"
                    },
                },
                "HumanPlacement": {
                    "SpawnerName": "human",
                    "SpawnerType": "EPalSpawnedCharacterType::Common",
                    "PlacementType": "EPalSpawnerPlacementType::Field",
                    "SpawnerClass": {
                        "AssetPathName": "/Game/Pal/Blueprint/Spawner/BP_Human.BP_Human_C"
                    },
                },
                "ScenarioPlacement": {
                    "SpawnerName": "scenario",
                    "SpawnerType": "EPalSpawnedCharacterType::FieldBoss",
                    "PlacementType": "EPalSpawnerPlacementType::FieldBoss",
                    "SpawnerClass": {
                        "AssetPathName": (
                            "/Game/Pal/Blueprint/Spawner/BP_Scenario.BP_Scenario_C"
                        )
                    },
                },
            },
        )
        self._write_spawner(
            "Pal/Content/Pal/Blueprint/Spawner/BP_Ordinary",
            {"Key": "boss_notscenario"},
            {"Key": "None"},
            include_row_name=True,
            extra_pal_ids=({"Key": "anubis"}, {"Key": "ELECPANDA"}),
        )
        self._write_spawner(
            "Pal/Content/Pal/Blueprint/Spawner/BP_Alpha",
            {"Key": "alphapal"},
            {"Key": "None"},
            extra_pal_id={"Key": "boss_notscenario"},
        )
        self._write_spawner(
            "Pal/Content/Pal/Blueprint/Spawner/BP_Human",
            {"Key": "None"},
            {"Key": "reachablehuman"},
        )
        self._write_spawner(
            "Pal/Content/Pal/Blueprint/Spawner/BP_Scenario",
            {"Key": "FriendlyLooking"},
            {"Key": "None"},
        )
        write_asset(
            self.export_root,
            self.HUMAN_ACTIONS,
            [
                {
                    "Type": "PalStaticCharacterParameterComponent",
                    "Name": "StaticCharacterParameterComponent",
                    "Properties": {
                        "WazaActionDeclarationMap": [
                            {
                                "Key": "EPalWazaID::Human_Punch",
                                "Value": {
                                    "AssetPathName": (
                                        "/Game/Pal/Blueprint/Action/NPC/"
                                        "BP_Action_NPC_MeleeAttack."
                                        "BP_Action_NPC_MeleeAttack_C"
                                    )
                                },
                            }
                        ]
                    },
                },
                {
                    "Type": "BP_NPC_StandardHumanDataSet_C",
                    "Name": "Default__BP_NPC_StandardHumanDataSet_C",
                    "Properties": {
                        "WazaActionDeclarationMap": [
                            {"Key": "EPalWazaID::UnrelatedObjectSkill"}
                        ]
                    },
                },
            ],
        )
        for name in (
            "grass_boss_reward",
            "kingwhale_controller",
            "kingwhale_combat",
        ):
            write_asset(
                self.export_root, game_data.CHARACTER_SCENARIO_SOURCES[name], []
            )
        for prefix in game_data.CHARACTER_SCENARIO_PREFIX_SOURCES:
            suffix = "Fixture" if prefix.endswith("_") else "/Fixture"
            asset_path = prefix + suffix
            stem = PurePosixPath(asset_path).name
            write_asset(
                self.export_root,
                asset_path,
                [
                    {
                        "Type": f"{stem}_C",
                        "Name": f"Default__{stem}_C",
                        "Properties": {},
                    }
                ],
            )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _write_incident_lottery_fixture(
        self, *, object_name: str, lottery_exports: list[dict]
    ) -> None:
        write_asset(
            self.export_root,
            game_data.CHARACTER_ROUTE_SOURCES["incident_world"],
            [
                {
                    "Type": "BP_Incident_C",
                    "Name": "PlacedIncident",
                    "Class": (
                        "BlueprintGeneratedClass'Pal/Content/Pal/Blueprint/Incident/"
                        "Random/BP_Incident.BP_Incident_C'"
                    ),
                    "Outer": {"ObjectName": "Level'PL_MainWorld5:PersistentLevel'"},
                    "Properties": {
                        "LotteryClass": {
                            "ObjectName": object_name,
                            "ObjectPath": (
                                "Pal/Content/Pal/Blueprint/Incident/Random/BP_Lottery.0"
                            ),
                        }
                    },
                }
            ],
        )
        write_asset(
            self.export_root,
            "Pal/Content/Pal/Blueprint/Incident/Random/BP_Incident",
            [
                {
                    "Type": "BP_Incident_C",
                    "Name": "Default__BP_Incident_C",
                    "Properties": {},
                }
            ],
        )
        write_asset(
            self.export_root,
            "Pal/Content/Pal/Blueprint/Incident/Random/BP_Lottery",
            lottery_exports,
        )

    def _write_spawner(
        self,
        virtual_path: str,
        pal_id: dict[str, str],
        npc_id: dict[str, str],
        *,
        include_row_name: bool = False,
        extra_pal_id: dict[str, str] | None = None,
        extra_pal_ids: tuple[dict[str, str], ...] = (),
        extra_exports: tuple[dict, ...] = (),
    ) -> None:
        class_name = Path(virtual_path).name + "_C"
        members = [
            {
                "PalId": pal_id,
                "NPCID": npc_id,
                "Level": 1,
                "Level_Max": 3,
                "Num": 1,
                "Num_Max": 1,
            }
        ]
        if include_row_name:
            members.append(
                {
                    "PalId": {"Key": "RowName"},
                    "NPCID": {"Key": "None"},
                    "Level": 1,
                    "Level_Max": 1,
                    "Num": 1,
                    "Num_Max": 1,
                }
            )
        for additional_pal_id in (
            *((extra_pal_id,) if extra_pal_id is not None else ()),
            *extra_pal_ids,
        ):
            members.append(
                {
                    "PalId": additional_pal_id,
                    "NPCID": {"Key": "None"},
                    "Level": 1,
                    "Level_Max": 1,
                    "Num": 1,
                    "Num_Max": 1,
                }
            )
        write_asset(
            self.export_root,
            virtual_path,
            [
                {
                    "Type": class_name,
                    "Name": "Default__" + class_name,
                    "Properties": {
                        "SpawnGroupList": [
                            {
                                "Weight": 1,
                                "PalList": members,
                            }
                        ]
                    },
                },
                *extra_exports,
            ],
        )

    def build(self):
        self.assertTrue(
            hasattr(game_data, "build_character_evidence"),
            "build_character_evidence is not implemented",
        )
        return game_data.build_character_evidence(self.export_root, self.policy)

    def _seed_reachable_raid_items(self, *item_ids: str) -> None:
        enemy_source = game_data.CHARACTER_ROUTE_SOURCES["dungeon"]
        enemies = load_table(self.export_root, enemy_source)
        enemies["FixtureRaidArea"] = {
            "SpawnAreaId": "FixtureRaidArea",
            "WeightInSpawnAreaAndRank": 1,
            "SpawnerBlueprintSoftClass": {
                "AssetPathName": (
                    "/Game/Pal/Blueprint/Spawner/BP_FixtureRaidDungeon."
                    "BP_FixtureRaidDungeon_C"
                ),
                "SubPathString": "",
            },
        }
        write_table(self.export_root, enemy_source, enemies)
        self._write_spawner(
            "Pal/Content/Pal/Blueprint/Spawner/BP_FixtureRaidDungeon",
            {"Key": "None"},
            {"Key": "None"},
        )
        write_table(
            self.export_root,
            game_data.RAID_REACHABILITY_SOURCES["dungeon_items"],
            {
                "FixtureRaidPool": {
                    "SpawnAreaId": "FixtureRaidArea",
                    "ItemFieldLotteryName": "FixtureRaidPool",
                }
            },
        )
        write_table(
            self.export_root,
            game_data.RAID_REACHABILITY_SOURCES["item_lottery"],
            {
                f"FixtureRaidItem{index}": {
                    "FieldName": "FixtureRaidPool",
                    "WeightInSlot": 1,
                    "StaticItemId": item_id,
                    "MaxNum": 1,
                    "NumUnit": 1,
                }
                for index, item_id in enumerate(item_ids)
            },
        )

    def test_casefold_fname_join_preserves_authoritative_character_and_family(
        self,
    ) -> None:
        evidence = self.build()["BOSS_NotScenario"]

        self.assertEqual(evidence.character_id, "BOSS_NotScenario")
        self.assertEqual(evidence.family_id, "BOSS_NotScenario")
        self.assertTrue(evidence.family_resolved)
        self.assertEqual(evidence.tribe, "BOSS_NotScenario")
        self.assertEqual(evidence.variant_tags, frozenset({"base"}))
        self.assertEqual(
            tuple(
                (source.kind, source.source_id)
                for source in evidence.acquisition_sources
            ),
            (
                ("placement", "OrdinaryPlacement"),
                ("placement", "AlphaPlacement"),
            ),
        )
        self.assertTrue(evidence.regularly_obtainable)

    def test_ordinary_source_survives_overlapping_scenario_tags(self) -> None:
        graph = self.build()

        self.assertEqual(graph["Anubis"].variant_tags, frozenset({"base"}))
        self.assertEqual(
            graph["ElecPanda"].variant_tags,
            frozenset({"base", "tower"}),
        )
        for character_id in ("Anubis", "ElecPanda"):
            with self.subTest(character_id=character_id):
                self.assertEqual(
                    tuple(
                        (source.kind, source.source_id)
                        for source in graph[character_id].acquisition_sources
                    ),
                    (("placement", "OrdinaryPlacement"),),
                )
                self.assertTrue(graph[character_id].regularly_obtainable)

    def test_boss_rush_tag_uses_authoritative_reward_metadata(self) -> None:
        monsters = load_table(self.export_root, self.MONSTERS)
        monsters["ElecPanda"]["FirstDefeatRewardItemID"] = "BossDefeatReward_BossRush"
        write_table(self.export_root, self.MONSTERS, monsters)

        evidence = self.build()["ElecPanda"]

        self.assertEqual(
            evidence.variant_tags,
            frozenset({"base", "tower", "boss-rush"}),
        )

    def test_structured_metadata_distinguishes_predator_and_scenario_tags(
        self,
    ) -> None:
        monsters = load_table(self.export_root, self.MONSTERS)
        monsters.update(
            {
                "PrefixPredator": {
                    "Tribe": "EPalTribeID::PrefixPredator",
                    "BPClass": "PrefixPredator",
                    "IsBoss": False,
                    "IsTowerBoss": False,
                    "IsRaidBoss": False,
                    "Predator": False,
                    "NamePrefixID": "PREDATOR_NAME",
                },
                "GymPrefix": {
                    "Tribe": "EPalTribeID::GymPrefix",
                    "BPClass": "GymPrefix",
                    "IsBoss": False,
                    "IsTowerBoss": False,
                    "IsRaidBoss": False,
                    "Predator": True,
                    "NamePrefixID": "GYM_NAME_Fixture",
                },
                "RaidBGM": {
                    "Tribe": "EPalTribeID::RaidBGM",
                    "BPClass": "RaidBGM",
                    "IsBoss": False,
                    "IsTowerBoss": False,
                    "IsRaidBoss": False,
                    "Predator": False,
                    "BattleBGM": "EPalBattleBGM::RaidBossFixture",
                },
                "BossRushPrefix": {
                    "Tribe": "EPalTribeID::BossRushPrefix",
                    "BPClass": "BossRushPrefix",
                    "IsBoss": False,
                    "IsTowerBoss": False,
                    "IsRaidBoss": False,
                    "Predator": False,
                    "NamePrefixID": "BOSS_NAME_FixtureBossRush",
                    "FirstDefeatRewardItemID": "None",
                },
            }
        )
        write_table(self.export_root, self.MONSTERS, monsters)
        bp_classes = load_table(self.export_root, game_data.SKILL_SOURCES["bp_classes"])
        for character_id in (
            "PrefixPredator",
            "GymPrefix",
            "RaidBGM",
            "BossRushPrefix",
        ):
            bp_classes[character_id] = {"BPClass": {"AssetPathName": "None"}}
        write_table(
            self.export_root,
            game_data.SKILL_SOURCES["bp_classes"],
            bp_classes,
        )

        graph = self.build()

        self.assertEqual(graph["Anubis"].variant_tags, frozenset({"base"}))
        self.assertEqual(
            graph["PrefixPredator"].variant_tags, frozenset({"base", "predator"})
        )
        self.assertEqual(graph["GymPrefix"].variant_tags, frozenset({"base", "tower"}))
        self.assertEqual(graph["RaidBGM"].variant_tags, frozenset({"base", "raid"}))
        self.assertEqual(
            graph["BossRushPrefix"].variant_tags,
            frozenset({"base", "boss-rush"}),
        )

    def test_bpclass_package_tokens_add_only_exact_scenario_identities(self) -> None:
        monsters = load_table(self.export_root, self.MONSTERS)
        monsters.update(
            {
                character_id: {
                    "Tribe": f"EPalTribeID::{character_id}",
                    "BPClass": bp_class,
                    "IsBoss": False,
                    "IsTowerBoss": False,
                    "IsRaidBoss": False,
                    "Predator": False,
                }
                for character_id, bp_class in (
                    ("OilrigPal", "OilrigClass"),
                    ("QuestPal", "QuestClass"),
                    ("SummonPal", "SummonClass"),
                    ("OtomoPal", "OtomoClass"),
                    ("GenericPal", "GenericHumanClass"),
                    ("NearMissPal", "NearMissClass"),
                )
            }
        )
        write_table(self.export_root, self.MONSTERS, monsters)
        write_table(
            self.export_root,
            game_data.SKILL_SOURCES["bp_classes"],
            {
                name: {
                    "BPClass": {
                        "AssetPathName": (
                            "/Game/Pal/Blueprint/Character/Monster/PalActorBP/Fixture/"
                            f"BP_Fixture_{token}.BP_Fixture_{token}_C"
                        )
                    }
                }
                for name, token in (
                    ("OilrigClass", "Oilrig"),
                    ("QuestClass", "Quest"),
                    ("SummonClass", "Summon"),
                    ("OtomoClass", "Otomo"),
                )
            }
            | {
                "GenericHumanClass": {
                    "BPClass": {
                        "AssetPathName": (
                            "/Game/Pal/Blueprint/Character/NPC/Normal/"
                            "BP_NPC_HumanNormal.BP_NPC_HumanNormal_C"
                        )
                    }
                },
                "NearMissClass": {
                    "BPClass": {
                        "AssetPathName": (
                            "/Game/Pal/Blueprint/Character/Monster/PalActorBP/"
                            "Fixture/BP_Fixture_Oilrigged_Questing_Summoner_"
                            "OtomoLike.BP_Fixture_Oilrigged_Questing_Summoner_"
                            "OtomoLike_C"
                        )
                    }
                },
            },
        )
        for domain in ("skills", "characters"):
            self.policy["domains"][domain]["required_sources"].append(
                game_data.SKILL_SOURCES["bp_classes"]
            )

        graph = game_data.build_character_evidence(
            self.export_root, self.policy, "characters"
        )
        with patch.object(
            game_data, "build_monster_action_declarations", return_value=({}, ())
        ):
            skill_graph = game_data.build_character_evidence(
                self.export_root, self.policy, "skills"
            )

        self.assertEqual(graph["OilrigPal"].variant_tags, frozenset({"base", "oilrig"}))
        self.assertEqual(graph["QuestPal"].variant_tags, frozenset({"base", "quest"}))
        self.assertEqual(graph["SummonPal"].variant_tags, frozenset({"base", "summon"}))
        self.assertEqual(graph["OtomoPal"].variant_tags, frozenset({"base", "otomo"}))
        self.assertEqual(graph["GenericPal"].variant_tags, frozenset({"base"}))
        self.assertEqual(graph["NearMissPal"].variant_tags, frozenset({"base"}))
        self.assertEqual(set(skill_graph), set(graph))
        for character_id in graph:
            with self.subTest(character_id=character_id):
                self.assertEqual(
                    skill_graph[character_id].variant_tags,
                    graph[character_id].variant_tags,
                )
                self.assertEqual(
                    skill_graph[character_id].acquisition_sources,
                    graph[character_id].acquisition_sources,
                )
                self.assertEqual(
                    skill_graph[character_id].encounter_sources,
                    graph[character_id].encounter_sources,
                )
                self.assertEqual(
                    skill_graph[character_id].regularly_obtainable,
                    graph[character_id].regularly_obtainable,
                )

    def test_exact_scenario_exports_add_identity_and_availability_evidence(
        self,
    ) -> None:
        monsters = load_table(self.export_root, self.MONSTERS)
        monsters.update(
            {
                "QuestSpawned": {
                    "Tribe": "EPalTribeID::QuestSpawned",
                    "IsBoss": False,
                    "IsTowerBoss": False,
                    "IsRaidBoss": False,
                    "Predator": False,
                },
                "SheetsQuestPal": {
                    "Tribe": "EPalTribeID::SheetsQuestPal",
                    "IsBoss": False,
                    "IsTowerBoss": False,
                    "IsRaidBoss": False,
                    "Predator": False,
                },
                "BattleTargetOnly": {
                    "Tribe": "EPalTribeID::BattleTargetOnly",
                    "IsBoss": False,
                    "IsTowerBoss": False,
                    "IsRaidBoss": False,
                    "Predator": False,
                },
                "ObjectiveOnly": {
                    "Tribe": "EPalTribeID::ObjectiveOnly",
                    "IsBoss": False,
                    "IsTowerBoss": False,
                    "IsRaidBoss": False,
                    "Predator": False,
                },
                "GYM_ElecPanda_Otomo": {
                    "Tribe": "EPalTribeID::GYM_ElecPanda_Otomo",
                    "IsBoss": False,
                    "IsTowerBoss": False,
                    "IsRaidBoss": False,
                    "Predator": False,
                    "NamePrefixID": "GYM_NAME_Fixture",
                },
                "NonTowerGift": {
                    "Tribe": "EPalTribeID::NonTowerGift",
                    "IsBoss": False,
                    "IsTowerBoss": False,
                    "IsRaidBoss": False,
                    "Predator": False,
                },
                "KingWhale": {
                    "Tribe": "EPalTribeID::KingWhale",
                    "IsBoss": False,
                    "IsTowerBoss": False,
                    "IsRaidBoss": False,
                    "Predator": False,
                },
                "BOSS_KingWhale": {
                    "Tribe": "EPalTribeID::KingWhale",
                    "BPClass": "BOSS_KingWhale",
                    "IsBoss": True,
                    "IsTowerBoss": False,
                    "IsRaidBoss": False,
                    "Predator": False,
                },
                "BOSS_KingWhale_otomo": {
                    "Tribe": "EPalTribeID::KingWhale",
                    "IsBoss": True,
                    "IsTowerBoss": False,
                    "IsRaidBoss": False,
                    "Predator": False,
                    "BPClass": "BOSS_KingWhale_otomo",
                },
                "BOSS_KingWhale_other": {
                    "Tribe": "EPalTribeID::KingWhale",
                    "BPClass": "BOSS_KingWhale_other",
                    "IsBoss": True,
                    "IsTowerBoss": False,
                    "IsRaidBoss": False,
                    "Predator": False,
                },
            }
        )
        for character_id, row in monsters.items():
            row.setdefault("BPClass", character_id)
        write_table(self.export_root, self.MONSTERS, monsters)
        humans = load_table(self.export_root, self.HUMANS)
        humans.update(
            {
                "QuestHuman": {
                    "Tribe": "EPalTribeID::Human",
                    "IsBoss": False,
                    "IsTowerBoss": False,
                    "IsRaidBoss": False,
                },
                "SheetsQuestHuman": {
                    "Tribe": "EPalTribeID::Human",
                    "IsBoss": False,
                    "IsTowerBoss": False,
                    "IsRaidBoss": False,
                },
                "OilrigHuman": {
                    "Tribe": "EPalTribeID::Human",
                    "IsBoss": False,
                    "IsTowerBoss": False,
                    "IsRaidBoss": False,
                },
                "MiniOilrigDecoy": {
                    "Tribe": "EPalTribeID::Human",
                    "IsBoss": False,
                    "IsTowerBoss": False,
                    "IsRaidBoss": False,
                },
            }
        )
        write_table(self.export_root, self.HUMANS, humans)
        bp_classes = {
            character_id: {"BPClass": {"AssetPathName": "None"}}
            for character_id in monsters
        }
        bp_classes["BOSS_KingWhale"] = {
            "BPClass": {
                "AssetPathName": (
                    "/Game/Pal/Blueprint/Character/Monster/PalActorBP/KingWhale/"
                    "BP_KingWhale_BOSS.BP_KingWhale_BOSS_C"
                )
            }
        }
        bp_classes["BOSS_KingWhale_otomo"] = {
            "BPClass": {
                "AssetPathName": (
                    "/Game/Pal/Blueprint/Character/Monster/PalActorBP/KingWhale/"
                    "BP_KingWhale_BOSS_otomo.BP_KingWhale_BOSS_otomo_C"
                )
            }
        }
        bp_classes["BOSS_KingWhale_other"] = {
            "BPClass": {
                "AssetPathName": (
                    "/Game/Pal/Blueprint/Character/Monster/PalActorBP/KingWhale/"
                    "BP_KingWhale_BOSS_other.BP_KingWhale_BOSS_other_C"
                )
            }
        }
        write_table(
            self.export_root,
            game_data.SKILL_SOURCES["bp_classes"],
            bp_classes,
        )
        for domain in ("skills", "characters"):
            self.policy["domains"][domain]["required_sources"].extend(
                (
                    game_data.SKILL_SOURCES["bp_classes"],
                    "Pal/Content/Pal/Blueprint/Spawner/Quest",
                    "Pal/Content/Pal/Blueprint/Spawner/SheetsVariant/BP_PalSpawner_Sheets_Quest_",
                    "Pal/Content/Pal/Maps/MainWorld_5/PL_MainWorld5/_Generated_/oilrig_",
                    "Pal/Content/Pal/Blueprint/FlowGraph/NPCTalkFlow/Graph/FABP_GrassBoss01",
                    "Pal/Content/Pal/Blueprint/Controller/Monster/BP_MonsterAIController_Wild_KingWhale",
                    "Pal/Content/Pal/Blueprint/Controller/Monster/BP_AICombatModule_KingWhale_Wild",
                )
            )
        write_asset(
            self.export_root,
            "Pal/Content/Pal/Blueprint/Spawner/Quest/BP_PalSpawner_Quest_Fixture",
            [
                {
                    "Type": "BP_PalSpawner_Quest_Fixture_C",
                    "Name": "Default__BP_PalSpawner_Quest_Fixture_C",
                    "Properties": {
                        "SpawnGroupList": [
                            {
                                "Weight": 1,
                                "PalList": [
                                    {
                                        "PalId": {"Key": "QuestSpawned"},
                                        "NPCID": {"Key": "QuestHuman"},
                                        "Level": 1,
                                        "Level_Max": 1,
                                        "Num": 1,
                                        "Num_Max": 1,
                                    }
                                ],
                            }
                        ],
                        "BattleTargetCharacterId": ["BattleTargetOnly"],
                        "RequirePalIdArray_OR": [{"Key": "ObjectiveOnly"}],
                    },
                }
            ],
        )
        write_asset(
            self.export_root,
            "Pal/Content/Pal/Blueprint/Spawner/Quest/BP_PalSpawner_Quest_Decoy",
            [
                {
                    "Type": "BP_PalSpawner_Quest_Decoy_C",
                    "Name": "Default__BP_PalSpawner_Quest_Decoy_C",
                    "Properties": {},
                },
                {
                    "Type": "BP_Unrelated_C",
                    "Name": "SpawnGroupHolderDecoy",
                    "Properties": {
                        "SpawnGroupList": [
                            {
                                "Weight": 1,
                                "PalList": [
                                    {
                                        "PalId": {"Key": "ObjectiveOnly"},
                                        "NPCID": {"Key": "None"},
                                        "Level": 1,
                                        "Level_Max": 1,
                                        "Num": 1,
                                        "Num_Max": 1,
                                    }
                                ],
                            }
                        ]
                    },
                },
            ],
        )
        write_asset(
            self.export_root,
            (
                "Pal/Content/Pal/Blueprint/Spawner/SheetsVariant/"
                "BP_PalSpawner_Sheets_Quest_Fixture"
            ),
            [
                {
                    "Type": "BP_PalSpawner_Sheets_Quest_Fixture_C",
                    "Name": "Default__BP_PalSpawner_Sheets_Quest_Fixture_C",
                    "Properties": {
                        "SpawnGroupList": [
                            {
                                "Weight": 1,
                                "PalList": [
                                    {
                                        "PalId": {"Key": "SheetsQuestPal"},
                                        "NPCID": {"Key": "SheetsQuestHuman"},
                                        "Level": 1,
                                        "Level_Max": 1,
                                        "Num": 1,
                                        "Num_Max": 1,
                                    }
                                ],
                            }
                        ],
                        "CountPalId": {"Key": "ObjectiveOnly"},
                    },
                }
            ],
        )
        write_asset(
            self.export_root,
            (
                "Pal/Content/Pal/Maps/MainWorld_5/PL_MainWorld5/_Generated_/"
                "oilrig_Fixture"
            ),
            [
                {
                    "Type": "BP_OilrigNPCSpawner_Mono_C",
                    "Properties": {
                        "HumanName": {"Key": "OilrigHuman"},
                        "OtomoName": {"Key": "Anubis"},
                    },
                },
                {
                    "Type": "BP_Unrelated_C",
                    "Properties": {
                        "HumanName": {"Key": "MiniOilrigDecoy"},
                        "OtomoName": {"Key": "ObjectiveOnly"},
                    },
                },
            ],
        )
        write_asset(
            self.export_root,
            "Pal/Content/Pal/Blueprint/FlowGraph/NPCTalkFlow/Graph/FABP_GrassBoss01",
            [
                *({"Type": "Ignored"} for _ in range(17)),
                {
                    "Type": "FNBP_GetCharacter_C",
                    "Properties": {
                        "PalId": {"Key": "NonTowerGift"},
                        "Level": 1,
                        "NetworkInvokeName": "Get_Decoy",
                    },
                },
                {
                    "Type": "FNBP_GetCharacter_C",
                    "Properties": {
                        "PalId": {"Key": "GYM_ElecPanda_Otomo"},
                        "Level": 1,
                        "NetworkInvokeName": "Get_Zoe",
                    },
                },
                {
                    "Type": "FNBP_GetCharacter_C",
                    "Properties": {
                        "PalId": {"Key": "GYM_ElecPanda_Otomo"},
                        "Level": 1,
                        "NetworkInvokeName": "Get_ZoeRE",
                    },
                },
            ],
        )
        write_asset(
            self.export_root,
            "Pal/Content/Pal/Blueprint/Controller/Monster/BP_AICombatModule_KingWhale_Wild",
            [
                {"Type": "Ignored"},
                {
                    "Properties": {
                        "CaptureReplaceSourceCharacterID": "BOSS_KingWhale",
                        "CaptureReplaceTargetCharacterID": "BOSS_KingWhale_otomo",
                    }
                },
            ],
        )
        write_asset(
            self.export_root,
            "Pal/Content/Pal/Blueprint/Character/Monster/PalActorBP/KingWhale/BP_KingWhale_BOSS",
            [
                {
                    "Type": "BlueprintGeneratedClass",
                    "Name": "BP_KingWhale_BOSS_C",
                    "Package": (
                        "Pal/Content/Pal/Blueprint/Character/Monster/PalActorBP/"
                        "KingWhale/BP_KingWhale_BOSS"
                    ),
                    "SuperStruct": {
                        "ObjectName": "Class'PalMonsterCharacter'",
                        "ObjectPath": "/Script/Pal",
                    },
                },
                {
                    "Type": "PalStaticCharacterParameterComponent",
                    "Name": "StaticCharacterParameterComponent",
                    "Properties": {"WazaActionDeclarationMap": []},
                },
            ],
        )
        write_asset(
            self.export_root,
            "Pal/Content/Pal/Blueprint/Character/Monster/PalActorBP/KingWhale/BP_KingWhale_BOSS_otomo",
            [
                {
                    "Type": "BlueprintGeneratedClass",
                    "Name": "BP_KingWhale_BOSS_otomo_C",
                    "Package": (
                        "Pal/Content/Pal/Blueprint/Character/Monster/PalActorBP/"
                        "KingWhale/BP_KingWhale_BOSS_otomo"
                    ),
                    "SuperStruct": {
                        "ObjectName": "Class'PalMonsterCharacter'",
                        "ObjectPath": "/Script/Pal",
                    },
                },
                {
                    "Type": "PalStaticCharacterParameterComponent",
                    "Name": "StaticCharacterParameterComponent",
                    "Properties": {"WazaActionDeclarationMap": []},
                },
            ],
        )
        write_asset(
            self.export_root,
            "Pal/Content/Pal/Blueprint/Character/Monster/PalActorBP/KingWhale/BP_KingWhale_BOSS_other",
            [
                {
                    "Type": "BlueprintGeneratedClass",
                    "Name": "BP_KingWhale_BOSS_other_C",
                    "Package": (
                        "Pal/Content/Pal/Blueprint/Character/Monster/PalActorBP/"
                        "KingWhale/BP_KingWhale_BOSS_other"
                    ),
                    "SuperStruct": {
                        "ObjectName": "Class'PalMonsterCharacter'",
                        "ObjectPath": "/Script/Pal",
                    },
                }
            ],
        )
        write_asset(
            self.export_root,
            (
                "Pal/Content/Pal/Blueprint/Controller/Monster/"
                "BP_MonsterAIController_Wild_KingWhale"
            ),
            [
                {"Type": "BlueprintGeneratedClass"},
                {
                    "Type": "BP_MonsterAIController_Wild_KingWhale_C",
                    "Name": "Default__BP_MonsterAIController_Wild_KingWhale_C",
                    "Properties": {
                        "CombatModuleClass": {
                            "ObjectName": (
                                "BlueprintGeneratedClass'"
                                "BP_AICombatModule_KingWhale_Wild_C'"
                            ),
                            "ObjectPath": (
                                "Pal/Content/Pal/Blueprint/Controller/Monster/"
                                "BP_AICombatModule_KingWhale_Wild.0"
                            ),
                        }
                    },
                },
            ],
        )
        graph = game_data.build_character_evidence(
            self.export_root, self.policy, "characters"
        )

        self.assertEqual(
            graph["QuestSpawned"].variant_tags, frozenset({"base", "quest"})
        )
        self.assertEqual(
            graph["QuestHuman"].variant_tags, frozenset({"human", "quest"})
        )
        self.assertEqual(
            graph["SheetsQuestPal"].variant_tags, frozenset({"base", "quest"})
        )
        self.assertEqual(
            graph["SheetsQuestHuman"].variant_tags, frozenset({"human", "quest"})
        )
        self.assertEqual(graph["BattleTargetOnly"].variant_tags, frozenset({"base"}))
        self.assertEqual(graph["BattleTargetOnly"].acquisition_sources, ())
        self.assertTrue(graph["BattleTargetOnly"].encounter_sources)
        self.assertEqual(graph["ObjectiveOnly"].variant_tags, frozenset({"base"}))
        self.assertEqual(graph["ObjectiveOnly"].acquisition_sources, ())
        self.assertEqual(graph["ObjectiveOnly"].encounter_sources, ())
        self.assertEqual(
            graph["OilrigHuman"].variant_tags, frozenset({"human", "oilrig"})
        )
        self.assertEqual(graph["MiniOilrigDecoy"].variant_tags, frozenset({"human"}))
        self.assertEqual(graph["MiniOilrigDecoy"].encounter_sources, ())
        self.assertTrue(
            any(
                diagnostic.kind == "quest_spawner_gap"
                and diagnostic.source_id == "BP_PalSpawner_Quest_Decoy"
                and "outside the exact package CDO" in diagnostic.detail
                for diagnostic in graph.diagnostics
            ),
            graph.diagnostics,
        )
        self.assertTrue(
            any(
                diagnostic.kind == "oilrig_spawner_gap"
                and diagnostic.source_id == "oilrig_Fixture"
                and "BP_Unrelated_C" in diagnostic.detail
                for diagnostic in graph.diagnostics
            ),
            graph.diagnostics,
        )
        self.assertEqual(graph["Anubis"].variant_tags, frozenset({"base"}))
        self.assertTrue(
            any(
                source.kind == "oilrig-otomo"
                for source in graph["Anubis"].encounter_sources
            )
        )
        self.assertIn("otomo", graph["GYM_ElecPanda_Otomo"].variant_tags)
        self.assertNotIn("otomo", graph["NonTowerGift"].variant_tags)
        self.assertEqual(graph["NonTowerGift"].acquisition_sources, ())
        self.assertFalse(graph["NonTowerGift"].regularly_obtainable)
        self.assertTrue(graph["QuestSpawned"].encounter_sources)
        self.assertTrue(graph["OilrigHuman"].encounter_sources)
        self.assertEqual(
            graph["GYM_ElecPanda_Otomo"].acquisition_sources,
            (game_data.EvidenceSource("quest-reward", "FABP_GrassBoss01"),),
        )
        self.assertEqual(
            graph["BOSS_KingWhale_otomo"].acquisition_sources,
            (
                game_data.EvidenceSource(
                    "capture-replace", "BP_AICombatModule_KingWhale_Wild"
                ),
            ),
        )
        self.assertTrue(graph["GYM_ElecPanda_Otomo"].regularly_obtainable)
        self.assertEqual(graph["BOSS_KingWhale"].acquisition_sources, ())
        self.assertFalse(graph["BOSS_KingWhale"].regularly_obtainable)
        self.assertIn(
            game_data.EvidenceSource(
                "capture-replace-source", "BP_AICombatModule_KingWhale_Wild"
            ),
            graph["BOSS_KingWhale"].encounter_sources,
        )
        self.assertEqual(graph["KingWhale"].acquisition_sources, ())
        self.assertFalse(graph["KingWhale"].regularly_obtainable)
        self.assertEqual(
            graph["BOSS_KingWhale_otomo"].variant_tags,
            frozenset({"boss", "otomo"}),
        )
        self.assertTrue(graph["BOSS_KingWhale_otomo"].regularly_obtainable)

        with patch.object(
            game_data, "build_monster_action_declarations", return_value=({}, ())
        ):
            skill_graph = game_data.build_character_evidence(
                self.export_root, self.policy, "skills"
            )
        self.assertEqual(set(skill_graph), set(graph))
        for character_id in graph:
            with self.subTest(character_id=character_id):
                self.assertEqual(
                    skill_graph[character_id].variant_tags,
                    graph[character_id].variant_tags,
                )
                self.assertEqual(
                    skill_graph[character_id].acquisition_sources,
                    graph[character_id].acquisition_sources,
                )
                self.assertEqual(
                    skill_graph[character_id].encounter_sources,
                    graph[character_id].encounter_sources,
                )
                self.assertEqual(
                    skill_graph[character_id].regularly_obtainable,
                    graph[character_id].regularly_obtainable,
                )

        module_path = (
            "Pal/Content/Pal/Blueprint/Controller/Monster/"
            "BP_AICombatModule_KingWhale_Wild"
        )
        controller_path = (
            "Pal/Content/Pal/Blueprint/Controller/Monster/"
            "BP_MonsterAIController_Wild_KingWhale"
        )
        valid_module = load_asset(self.export_root, module_path)
        valid_controller = load_asset(self.export_root, controller_path)
        valid_monsters = load_table(self.export_root, self.MONSTERS)

        def assert_capture_rejected(
            *, module=valid_module, controller=valid_controller, rows=valid_monsters
        ) -> None:
            write_asset(self.export_root, module_path, module)
            write_asset(self.export_root, controller_path, controller)
            write_table(self.export_root, self.MONSTERS, rows)
            rejected = game_data.build_character_evidence(
                self.export_root, self.policy, "characters"
            )
            self.assertFalse(rejected["BOSS_KingWhale_otomo"].regularly_obtainable)
            self.assertTrue(
                any(
                    "capture" in diagnostic.kind for diagnostic in rejected.diagnostics
                ),
                rejected.diagnostics,
            )

        orphan_controller = deepcopy(valid_controller)
        orphan_controller[1]["Properties"]["CombatModuleClass"] = {
            "ObjectName": "BlueprintGeneratedClass'BP_Unrelated_C'",
            "ObjectPath": "Pal/Content/Pal/Blueprint/Controller/Monster/BP_Unrelated.0",
        }
        with self.subTest(capture_replace="orphan-module"):
            assert_capture_rejected(controller=orphan_controller)

        unresolved_source = deepcopy(valid_module)
        unresolved_source[1]["Properties"]["CaptureReplaceSourceCharacterID"] = (
            "MissingSource"
        )
        with self.subTest(capture_replace="unresolved-source"):
            assert_capture_rejected(module=unresolved_source)

        unresolved_target = deepcopy(valid_module)
        unresolved_target[1]["Properties"]["CaptureReplaceTargetCharacterID"] = (
            "MissingTarget"
        )
        with self.subTest(capture_replace="unresolved-target"):
            assert_capture_rejected(module=unresolved_target)

        mismatched_family = deepcopy(valid_monsters)
        mismatched_family["BOSS_KingWhale_otomo"]["Tribe"] = (
            "EPalTribeID::DifferentFamily"
        )
        with self.subTest(capture_replace="family-tribe-mismatch"):
            assert_capture_rejected(rows=mismatched_family)

        non_otomo_target = deepcopy(valid_module)
        non_otomo_target[1]["Properties"]["CaptureReplaceTargetCharacterID"] = (
            "BOSS_KingWhale_other"
        )
        with self.subTest(capture_replace="non-otomo-target"):
            assert_capture_rejected(module=non_otomo_target)

    def test_kingwhale_dynamic_sources_are_counted_symmetrically_in_manifests(
        self,
    ) -> None:
        self._seed_valid_fail_closed_scenario_routes()
        monsters = load_table(self.export_root, self.MONSTERS)
        for row in monsters.values():
            for index in range(1, 5):
                row.setdefault(f"PassiveSkill{index}", "None")
        write_table(self.export_root, self.MONSTERS, monsters)
        for name in ("waza", "levels", "passives"):
            write_table(self.export_root, game_data.SKILL_SOURCES[name], {})
        for source_path in game_data.CHARACTER_SOURCES.values():
            write_table(self.export_root, source_path, {})
        for table_name in {
            "DT_SkillNameText_Common",
            "DT_SkillDescText_Common",
            "DT_UI_Common_Text_Common",
            *game_data.CHARACTER_TEXT_TABLES.values(),
        }:
            for locale in game_data.LOCALE_DIRECTORIES:
                write_table(
                    self.export_root,
                    game_data.text_table_path(table_name, locale),
                    {},
                )

        empty_projection = {
            "pals": {},
            "humans": {},
            "skins": {},
            "icon_sources": {},
            "missing_localizations": (),
            "missing_icons": (),
        }
        with patch.object(
            game_data, "build_character_records", return_value=empty_projection
        ):
            character_candidate = game_data.build_domain(
                "characters", self.export_root, self.policy
            )
        skill_candidate = game_data.build_domain(
            "skills", self.export_root, self.policy
        )

        kingwhale_sources = {
            (
                "Pal/Content/Pal/Blueprint/Character/Monster/PalActorBP/"
                "KingWhale/BP_KingWhale_BOSS"
            ): 2,
            (
                "Pal/Content/Pal/Blueprint/Character/Monster/PalActorBP/"
                "KingWhale/BP_KingWhale_BOSS_otomo"
            ): 2,
            game_data.CHARACTER_SCENARIO_SOURCES["kingwhale_controller"]: 2,
            game_data.CHARACTER_SCENARIO_SOURCES["kingwhale_combat"]: 2,
        }
        for domain, candidate in (
            ("characters", character_candidate),
            ("skills", skill_candidate),
        ):
            surfaces = {
                "snapshot": candidate.source_counts,
                "manifest": candidate_manifest(candidate).source_counts,
            }
            for surface, source_counts in surfaces.items():
                for source_path, expected_count in kingwhale_sources.items():
                    with self.subTest(
                        domain=domain,
                        surface=surface,
                        source_path=source_path,
                    ):
                        self.assertEqual(
                            source_counts.get(source_path),
                            expected_count,
                        )

    def test_family_join_preserves_authoritative_target_spelling(self) -> None:
        graph = self.build()

        self.assertEqual(graph["BluePlatypus"].family_id, "Blueplatypus")
        self.assertTrue(graph["BluePlatypus"].family_resolved)
        self.assertEqual(graph["StrawHatCat"].family_id, "Strawhatcat")
        self.assertTrue(graph["StrawHatCat"].family_resolved)

    def test_exact_acquisition_does_not_propagate_to_distinct_family_row(
        self,
    ) -> None:
        graph = self.build()

        self.assertEqual(
            graph["AlphaPal"].acquisition_sources,
            (game_data.EvidenceSource("placement", "AlphaPlacement"),),
        )
        self.assertTrue(graph["AlphaPal"].regularly_obtainable)
        self.assertEqual(graph["AlphaFamily"].acquisition_sources, ())
        self.assertFalse(graph["AlphaFamily"].regularly_obtainable)

    def test_unresolved_family_is_preserved_and_reported(self) -> None:
        monsters = load_table(self.export_root, self.MONSTERS)
        monsters["RAID_Part"] = {
            "Tribe": "EPalTribeID::PartWithoutTarget",
            "IsBoss": False,
            "IsTowerBoss": False,
            "IsRaidBoss": True,
            "Predator": False,
        }
        write_table(self.export_root, self.MONSTERS, monsters)
        self._seed_valid_fail_closed_scenario_routes()

        graph = self.build()

        self.assertEqual(graph["RAID_Part"].family_id, "PartWithoutTarget")
        self.assertFalse(graph["RAID_Part"].family_resolved)
        self.assertFalse(graph.complete)
        self.assertEqual(
            [
                (diagnostic.kind, diagnostic.source_id, diagnostic.detail)
                for diagnostic in graph.diagnostics
            ],
            [
                (
                    "unresolved_family",
                    "RAID_Part",
                    "PartWithoutTarget",
                )
            ],
        )

    def test_override_name_does_not_infer_an_unresolved_family_relation(self) -> None:
        monsters = load_table(self.export_root, self.MONSTERS)
        monsters["ScenarioPart"] = {
            "Tribe": "EPalTribeID::MissingPartTribe",
            "OverrideNameTextID": "PAL_NAME_ScenarioFamily",
            "IsBoss": True,
            "IsTowerBoss": False,
            "IsRaidBoss": True,
            "Predator": False,
        }
        write_table(self.export_root, self.MONSTERS, monsters)

        graph = self.build()
        evidence = graph["ScenarioPart"]

        self.assertEqual(evidence.family_id, "MissingPartTribe")
        self.assertFalse(evidence.family_resolved)
        self.assertIn(
            game_data.EvidenceDiagnostic(
                "unresolved_family", "ScenarioPart", "MissingPartTribe"
            ),
            graph.diagnostics,
        )

    def test_scenario_tags_come_from_source_fields_not_character_name(self) -> None:
        graph = self.build()
        ordinary = graph["BOSS_NotScenario"]
        scenario = graph["FriendlyLooking"]

        self.assertNotIn("boss", ordinary.variant_tags)
        self.assertEqual(scenario.variant_tags, frozenset({"tower"}))
        self.assertEqual(scenario.acquisition_sources, ())
        self.assertFalse(scenario.regularly_obtainable)
        self.assertEqual(graph["ScenarioFamily"].acquisition_sources, ())
        self.assertFalse(graph["ScenarioFamily"].regularly_obtainable)

    def test_field_boss_source_marks_exact_alpha_obtainable(self) -> None:
        evidence = self.build()["AlphaPal"]

        self.assertEqual(evidence.family_id, "AlphaFamily")
        self.assertEqual(evidence.variant_tags, frozenset({"boss", "alpha"}))
        self.assertEqual(
            tuple(
                (source.kind, source.source_id)
                for source in evidence.acquisition_sources
            ),
            (("placement", "AlphaPlacement"),),
        )
        self.assertTrue(evidence.regularly_obtainable)

    def test_reachable_human_action_is_usage_not_assignability_evidence(self) -> None:
        evidence = self.build()["ReachableHuman"]

        self.assertEqual(evidence.family_id, "ReachableHuman")
        self.assertEqual(evidence.tribe, "Human")
        self.assertEqual(evidence.variant_tags, frozenset({"human"}))
        self.assertEqual(
            evidence.action_declarations, frozenset({"EPalWazaID::Human_Punch"})
        )
        self.assertEqual(
            tuple(
                (source.kind, source.source_id)
                for source in evidence.acquisition_sources
            ),
            (("placement", "HumanPlacement"),),
        )

    def test_human_boss_flag_is_preserved_without_name_inference(self) -> None:
        graph = self.build()

        self.assertEqual(graph["BossHuman"].variant_tags, frozenset({"human", "boss"}))
        self.assertEqual(graph["UnreachableHuman"].variant_tags, frozenset({"human"}))

    def test_arena_waza_list_records_exact_pal_action_declarations(self) -> None:
        arena = load_table(self.export_root, game_data.CHARACTER_ROUTE_SOURCES["arena"])
        arena["ExplicitArenaActions"] = {
            "NPCID": {"Key": "None"},
            "UniqueNPCID": {"Key": "None"},
            "OtomoList": [
                {
                    "PalId": {"Key": "Anubis"},
                    "WazaList": [
                        "EPalWazaID::StoneShotgun",
                        "EPalWazaID::GroundSmash",
                    ],
                }
            ],
        }
        write_table(self.export_root, game_data.CHARACTER_ROUTE_SOURCES["arena"], arena)

        evidence = self.build()["Anubis"]

        self.assertEqual(
            evidence.action_declarations,
            frozenset(
                {
                    "EPalWazaID::StoneShotgun",
                    "EPalWazaID::GroundSmash",
                }
            ),
        )

    def test_unrelated_spawner_object_does_not_create_reachability(self) -> None:
        self._write_spawner(
            "Pal/Content/Pal/Blueprint/Spawner/BP_Ordinary",
            {"Key": "boss_notscenario"},
            {"Key": "None"},
            extra_exports=(
                {
                    "Type": "BP_Ordinary_C",
                    "Name": "UnrelatedObject",
                    "Properties": {
                        "SpawnGroupList": [
                            {
                                "Weight": 1,
                                "PalList": [
                                    {
                                        "PalId": {"Key": "None"},
                                        "NPCID": {"Key": "UnreachableHuman"},
                                    }
                                ],
                            }
                        ]
                    },
                },
            ),
        )

        self.assertFalse(self.build()["UnreachableHuman"].regularly_obtainable)

    def test_ambiguous_spawner_default_object_is_rejected(self) -> None:
        self._write_spawner(
            "Pal/Content/Pal/Blueprint/Spawner/BP_Ordinary",
            {"Key": "boss_notscenario"},
            {"Key": "None"},
            extra_exports=(
                {
                    "Type": "BP_Ordinary_C",
                    "Name": "Default__BP_Ordinary_C",
                    "Properties": {"SpawnGroupList": []},
                },
            ),
        )

        with self.assertRaisesRegex(
            ValueError, "OrdinaryPlacement.SpawnerClass.*exactly one default object"
        ):
            self.build()

    def test_non_cdo_spawner_holder_is_rejected(self) -> None:
        write_asset(
            self.export_root,
            "Pal/Content/Pal/Blueprint/Spawner/BP_Ordinary",
            [
                {
                    "Type": "BP_Ordinary_C",
                    "Name": "NotTheDefaultObject",
                    "Properties": {"SpawnGroupList": []},
                }
            ],
        )

        with self.assertRaisesRegex(
            ValueError, "OrdinaryPlacement.SpawnerClass.*exactly one default object"
        ):
            self.build()

    def test_ambiguous_human_action_component_is_rejected(self) -> None:
        write_asset(
            self.export_root,
            self.HUMAN_ACTIONS,
            [
                {
                    "Type": "PalStaticCharacterParameterComponent",
                    "Name": "StaticCharacterParameterComponent",
                    "Properties": {"WazaActionDeclarationMap": []},
                },
                {
                    "Type": "PalStaticCharacterParameterComponent",
                    "Name": "StaticCharacterParameterComponent",
                    "Properties": {"WazaActionDeclarationMap": []},
                },
            ],
        )

        with self.assertRaisesRegex(ValueError, "human action.*exactly one.*component"):
            self.build()

    def test_missing_spawn_group_is_an_explicit_incomplete_diagnostic(self) -> None:
        placements = load_table(self.export_root, self.PLACEMENTS)
        object_path = (
            "/Game/Pal/Blueprint/Spawner/HumanNPCBoss/BP_HumanBoss.BP_HumanBoss_C"
        )
        placements["UnsupportedHumanBoss"] = {
            "SpawnerName": "unsupported-human-boss",
            "SpawnerType": "EPalSpawnedCharacterType::FieldBoss",
            "PlacementType": "EPalSpawnerPlacementType::FieldBoss",
            "SpawnerClass": {"AssetPathName": object_path},
        }
        write_table(self.export_root, self.PLACEMENTS, placements)
        write_asset(
            self.export_root,
            "Pal/Content/Pal/Blueprint/Spawner/HumanNPCBoss/BP_HumanBoss",
            [
                {
                    "Type": "BP_HumanBoss_C",
                    "Name": "Default__BP_HumanBoss_C",
                    "Properties": {"SomeInheritedBossField": "not expanded"},
                }
            ],
        )
        self._seed_valid_fail_closed_scenario_routes()

        graph = self.build()

        self.assertFalse(graph.complete)
        self.assertEqual(
            [(item.kind, item.source_id) for item in graph.diagnostics],
            [("unsupported_spawner", object_path)],
        )

    def test_reached_wild_and_positive_dungeon_routes_are_exactly_gated(self) -> None:
        def wild_row(spawner: str, weight: int, target: str) -> dict:
            return {
                "SpawnerName": spawner,
                "SpawnerType": "EPalWildSpawnerType::FieldBoss",
                "Weight": weight,
                "Pal_1": target,
                "Pal_2": "None",
                "Pal_3": "None",
                "NPC_1": "None",
                "NPC_2": "None",
                "NPC_3": "None",
                "OriginalRowName": "None",
                "OriginalSpawnerName": "None",
            }

        write_table(
            self.export_root,
            game_data.CHARACTER_ROUTE_SOURCES["wild"],
            {
                "Reached": wild_row("ordinary", 1, "ScenarioFamily"),
                "Zero": wild_row("ordinary", 0, "UnreachableHuman"),
                "Unreached": wild_row("not-placed", 1, "UnreachableHuman"),
            },
        )
        write_table(
            self.export_root,
            game_data.CHARACTER_ROUTE_SOURCES["dungeon"],
            {
                "Positive": {
                    "WeightInSpawnAreaAndRank": 1,
                    "SpawnerBlueprintSoftClass": {
                        "AssetPathName": (
                            "/Game/Pal/Blueprint/Spawner/BP_Dungeon.BP_Dungeon_C"
                        ),
                        "SubPathString": "",
                    },
                    "SpawnerName": "dungeon",
                    "SpawnAreaId": "area",
                    "RankType": "rank",
                },
                "Zero": {
                    "WeightInSpawnAreaAndRank": 0,
                    "SpawnerBlueprintSoftClass": {
                        "AssetPathName": (
                            "/Game/Pal/Blueprint/Spawner/BP_Missing.BP_Missing_C"
                        ),
                        "SubPathString": "",
                    },
                    "SpawnerName": "missing",
                    "SpawnAreaId": "area",
                    "RankType": "rank",
                },
            },
        )
        self._write_spawner(
            "Pal/Content/Pal/Blueprint/Spawner/BP_Dungeon",
            {"Key": "None"},
            {"Key": "UnreachableHuman"},
        )

        graph = self.build()

        self.assertIn(
            ("wild", "Reached"),
            {
                (source.kind, source.source_id)
                for source in graph["ScenarioFamily"].acquisition_sources
            },
        )
        self.assertIn(
            ("dungeon", "Positive"),
            {
                (source.kind, source.source_id)
                for source in graph["UnreachableHuman"].acquisition_sources
            },
        )
        self.assertNotIn(
            "wild",
            {source.kind for source in graph["UnreachableHuman"].acquisition_sources},
        )

    def test_direct_route_tables_preserve_each_exact_provenance_and_gate(self) -> None:
        target = "UnreachableHuman"
        write_table(
            self.export_root,
            game_data.CHARACTER_ROUTE_SOURCES["cage"],
            {
                "Positive": {"PalId": target, "Weight": 1, "FieldName": "field"},
                "Zero": {"PalId": "ReachableHuman", "Weight": 0, "FieldName": "field"},
            },
        )
        write_table(
            self.export_root,
            game_data.CHARACTER_ROUTE_SOURCES["fishing_spot"],
            {"Spot": {"PalName": {"Key": target}}},
        )
        write_table(
            self.export_root,
            game_data.CHARACTER_ROUTE_SOURCES["fish_pond"],
            {
                "Pond": {"CharacterID": target, "Weight": 1},
                "Zero": {"CharacterID": "ReachableHuman", "Weight": 0},
            },
        )
        write_table(
            self.export_root,
            game_data.CHARACTER_ROUTE_SOURCES["shop"],
            {"Shop": {"CharacterIDArray": [{"Key": target}]}},
        )
        slot_row = {
            "Weight": 1,
            **{f"Number_{suffix}": int(suffix == "A") for suffix in "ABCDE"},
            "CharactorID_A": target,
            "Otomo_A": "None",
        }
        for route in ("invader", "visitor"):
            write_table(
                self.export_root,
                game_data.CHARACTER_ROUTE_SOURCES[route],
                {"Event": slot_row},
            )
        write_table(
            self.export_root,
            game_data.CHARACTER_ROUTE_SOURCES["unique_npc"],
            {
                "Used": {"CharacterID": target},
                "Unreferenced": {"CharacterID": "ReachableHuman"},
            },
        )
        write_table(
            self.export_root,
            game_data.CHARACTER_ROUTE_SOURCES["arena"],
            {
                "Arena": {
                    "NPCID": {"Key": "None"},
                    "UniqueNPCID": {"Key": "Used"},
                    "OtomoList": [{"PalId": {"Key": "ScenarioFamily"}}],
                }
            },
        )
        write_table(
            self.export_root,
            game_data.CHARACTER_ROUTE_SOURCES["raid_boss"],
            {
                "Raid": {
                    "InfoList": [{"PalId": {"Key": "FriendlyLooking"}}],
                    "EggPalIDAndWeight": [
                        {"Key": {"Key": "AlphaPal"}, "Value": 0.1},
                        {"Key": {"Key": "AlphaFamily"}, "Value": 0.9},
                        {"Key": {"Key": target}, "Value": 0},
                    ],
                    "SummonMeteor_Num": [
                        {
                            "HPRate": 0.5,
                            "SummonPalInfoList": [
                                {
                                    "PalNameAndNum": [
                                        {
                                            "Key": {"Key": "FriendlyLooking"},
                                            "Value": 1,
                                        }
                                    ]
                                }
                            ],
                        }
                    ],
                    "SummonGeneratorClass": {
                        "ObjectPath": "Pal/Content/Test/BP_RaidGenerator.0"
                    },
                }
            },
        )
        write_table(
            self.export_root,
            self.ITEMS,
            {
                "Raid": {
                    "bLegalInGame": True,
                    "TypeA": "EPalItemTypeA::Consume",
                    "TypeB": "EPalItemTypeB::ConsumeOther",
                }
            },
        )
        write_table(
            self.export_root,
            game_data.CHARACTER_ROUTE_SOURCES["breeding"],
            {
                "Combi": {
                    "ChildCharacterID": target,
                    "ParentTribeA": "EPalTribeID::Anubis",
                    "ParentTribeB": "EPalTribeID::Anubis",
                }
            },
        )
        self._seed_reachable_raid_items("Raid")

        graph = self.build()
        kinds = {source.kind for source in graph[target].acquisition_sources}

        self.assertTrue(
            {
                "cage",
                "fishing-spot",
                "fish-pond",
                "shop-table-direct",
                "invader",
                "visitor",
                "arena",
                "unique-breeding",
            }.issubset(kinds),
            kinds,
        )
        self.assertFalse(
            any(
                source.source_id == "Unreferenced"
                for source in graph["ReachableHuman"].acquisition_sources
            )
        )
        self.assertIn(
            ("scenario-raid-boss", "Raid"),
            {
                (source.kind, source.source_id)
                for source in graph["FriendlyLooking"].encounter_sources
            },
        )
        self.assertEqual(graph["FriendlyLooking"].acquisition_sources, ())
        self.assertIn(
            ("scenario-raid-servant", "Raid"),
            {
                (source.kind, source.source_id)
                for source in graph["FriendlyLooking"].encounter_sources
            },
        )
        self.assertIn(
            ("raid-egg", "Raid"),
            {
                (source.kind, source.source_id)
                for source in graph["AlphaPal"].acquisition_sources
            },
        )
        self.assertEqual(
            graph["AlphaFamily"].acquisition_sources,
            (game_data.EvidenceSource("raid-egg", "Raid"),),
        )
        self.assertTrue(graph["AlphaFamily"].regularly_obtainable)
        self.assertNotIn(
            "raid-egg",
            {source.kind for source in graph[target].acquisition_sources},
        )
        self.assertTrue(any(item.kind == "coverage_gap" for item in graph.diagnostics))

    def test_each_supported_route_is_individually_gated_by_policy(self) -> None:
        target = "UnreachableHuman"
        write_table(
            self.export_root,
            game_data.CHARACTER_ROUTE_SOURCES["raid_boss"],
            {
                "Raid": {
                    "InfoList": [{"PalId": {"Key": target}}],
                    "EggPalIDAndWeight": [{"Key": {"Key": target}, "Value": 1}],
                    "SummonMeteor_Num": [
                        {
                            "HPRate": 0.5,
                            "SummonPalInfoList": [
                                {
                                    "PalNameAndNum": [
                                        {"Key": {"Key": target}, "Value": 1}
                                    ]
                                }
                            ],
                        }
                    ],
                    "SummonGeneratorClass": {
                        "ObjectPath": "Pal/Content/Test/BP_RaidGenerator.0"
                    },
                }
            },
        )
        write_table(
            self.export_root,
            self.ITEMS,
            {
                "Raid": {
                    "bLegalInGame": True,
                    "TypeA": "EPalItemTypeA::Consume",
                    "TypeB": "EPalItemTypeB::ConsumeOther",
                }
            },
        )
        write_table(
            self.export_root,
            game_data.CHARACTER_ROUTE_SOURCES["wild"],
            {
                "Reached": {
                    "SpawnerName": "ordinary",
                    "SpawnerType": "EPalWildSpawnerType::FieldBoss",
                    "Weight": 1,
                    "Pal_1": "None",
                    "Pal_2": "None",
                    "Pal_3": "None",
                    "NPC_1": target,
                    "NPC_2": "None",
                    "NPC_3": "None",
                    "OriginalRowName": "None",
                    "OriginalSpawnerName": "None",
                }
            },
        )
        write_table(
            self.export_root,
            game_data.CHARACTER_ROUTE_SOURCES["dungeon"],
            {
                "Dungeon": {
                    "WeightInSpawnAreaAndRank": 1,
                    "SpawnerBlueprintSoftClass": {
                        "AssetPathName": (
                            "/Game/Pal/Blueprint/Spawner/BP_RouteDungeon."
                            "BP_RouteDungeon_C"
                        ),
                        "SubPathString": "",
                    },
                    "SpawnerName": "dungeon",
                    "SpawnAreaId": "area",
                    "RankType": "rank",
                }
            },
        )
        self._write_spawner(
            "Pal/Content/Pal/Blueprint/Spawner/BP_RouteDungeon",
            {"Key": "None"},
            {"Key": target},
        )
        write_table(
            self.export_root,
            game_data.CHARACTER_ROUTE_SOURCES["cage"],
            {"Cage": {"PalId": target, "Weight": 1, "FieldName": "field"}},
        )
        write_table(
            self.export_root,
            game_data.CHARACTER_ROUTE_SOURCES["fishing_spot"],
            {"Spot": {"PalName": {"Key": target}}},
        )
        write_table(
            self.export_root,
            game_data.CHARACTER_ROUTE_SOURCES["fish_pond"],
            {"Pond": {"CharacterID": target, "Weight": 1}},
        )
        write_table(
            self.export_root,
            game_data.CHARACTER_ROUTE_SOURCES["shop"],
            {"Shop": {"CharacterIDArray": [{"Key": target}]}},
        )
        slot = {
            "Weight": 1,
            **{f"Number_{suffix}": int(suffix == "A") for suffix in "ABCDE"},
            "CharactorID_A": target,
            "Otomo_A": "None",
        }
        for route in ("invader", "visitor"):
            write_table(
                self.export_root,
                game_data.CHARACTER_ROUTE_SOURCES[route],
                {"Event": slot},
            )
        write_table(
            self.export_root,
            game_data.CHARACTER_ROUTE_SOURCES["unique_npc"],
            {"Used": {"CharacterID": target}},
        )
        write_table(
            self.export_root,
            game_data.CHARACTER_ROUTE_SOURCES["arena"],
            {
                "Arena": {
                    "NPCID": {"Key": "None"},
                    "UniqueNPCID": {"Key": "Used"},
                    "OtomoList": [],
                }
            },
        )
        write_table(
            self.export_root,
            game_data.CHARACTER_ROUTE_SOURCES["breeding"],
            {
                "Combi": {
                    "ChildCharacterID": target,
                    "ParentTribeA": "EPalTribeID::Anubis",
                    "ParentTribeB": "EPalTribeID::Anubis",
                }
            },
        )
        self._write_incident_lottery_fixture(
            object_name="BlueprintGeneratedClass'BP_Lottery_C'",
            lottery_exports=[
                {
                    "Type": "BP_Lottery_C",
                    "Name": "Default__BP_Lottery_C",
                    "Properties": {
                        "LotteryParameters": [
                            {"SettingName": "RouteSetting", "LotteryRate": 1}
                        ]
                    },
                }
            ],
        )
        write_table(
            self.export_root,
            game_data.CHARACTER_ROUTE_SOURCES["incident_settings"],
            {
                "RouteSetting": {
                    "MonsterSpawnData": {
                        "ObjectPath": (
                            "Pal/Content/Pal/DataTable/Incident/DT_RouteSpawn.0"
                        )
                    },
                    "NPCSpawnData": {"ObjectPath": "None"},
                }
            },
        )
        write_table(
            self.export_root,
            "Pal/Content/Pal/DataTable/Incident/DT_RouteSpawn",
            {"Spawn": {"CharacterID": {"Key": target}}},
        )

        kinds = {
            "placement": "placement",
            "reached_wild": "wild",
            "dungeon": "dungeon",
            "cage": "cage",
            "fishing_spot": "fishing-spot",
            "fish_pond": "fish-pond",
            "shop_table_direct": "shop-table-direct",
            "invader": "invader",
            "visitor": "visitor",
            "arena_solo": "arena",
            "raid_boss": "ordinary-raid-boss",
            "raid_egg": "raid-egg",
            "raid_servant": "scenario-raid-servant",
            "unique_breeding": "unique-breeding",
            "mainworld5_incident": "incident",
        }
        self._seed_reachable_raid_items("Raid")
        baseline = self.build()
        baseline_kinds = {
            source.kind
            for evidence in baseline.values()
            for source in (*evidence.acquisition_sources, *evidence.encounter_sources)
        }
        self.assertTrue(set(kinds.values()).issubset(baseline_kinds), baseline_kinds)

        original_routes = list(self.policy["domains"]["skills"]["supported_routes"])
        for route, source_kind in kinds.items():
            with self.subTest(route=route):
                self.policy["domains"]["skills"]["supported_routes"] = [
                    value for value in original_routes if value != route
                ]
                graph = self.build()
                emitted = {
                    source.kind
                    for evidence in graph.values()
                    for source in (
                        *evidence.acquisition_sources,
                        *evidence.encounter_sources,
                    )
                }
                self.assertNotIn(source_kind, emitted)
                self.assertNotIn(f"family-{source_kind}", emitted)
                self.assertTrue(
                    any(
                        diagnostic.kind == "coverage_gap" and route in diagnostic.detail
                        for diagnostic in graph.diagnostics
                    ),
                    graph.diagnostics,
                )
        self.policy["domains"]["skills"]["supported_routes"] = original_routes

    def test_character_domain_uses_its_own_raid_route_policy(self) -> None:
        target = "UnreachableHuman"
        write_table(
            self.export_root,
            game_data.CHARACTER_ROUTE_SOURCES["raid_boss"],
            {"Raid": {"InfoList": [{"PalId": {"Key": target}}]}},
        )
        write_table(
            self.export_root,
            self.ITEMS,
            {
                "Raid": {
                    "bLegalInGame": True,
                    "TypeA": "EPalItemTypeA::Consume",
                    "TypeB": "EPalItemTypeB::ConsumeOther",
                }
            },
        )
        self._seed_reachable_raid_items("Raid")
        character_policy = self.policy["domains"]["characters"]
        character_policy["required_sources"] = list(
            self.policy["domains"]["skills"]["required_sources"]
        )
        character_policy["supported_routes"] = ["raid_boss"]

        enabled = game_data.build_character_evidence(
            self.export_root, self.policy, "characters"
        )
        self.assertEqual(enabled[target].acquisition_sources, ())
        self.assertIn(
            ("ordinary-raid-boss", "Raid"),
            {
                (source.kind, source.source_id)
                for source in enabled[target].encounter_sources
            },
        )

        character_policy["supported_routes"] = []
        disabled = game_data.build_character_evidence(
            self.export_root, self.policy, "characters"
        )
        self.assertEqual(disabled[target].acquisition_sources, ())
        self.assertEqual(disabled[target].encounter_sources, ())
        self.assertTrue(
            any(
                item.kind == "coverage_gap"
                and item.source_id == game_data.CHARACTER_ROUTE_SOURCES["raid_boss"]
                for item in disabled.diagnostics
            )
        )

    def test_illegal_raid_summon_item_disables_all_row_evidence(self) -> None:
        target = "UnreachableHuman"
        write_table(
            self.export_root,
            game_data.CHARACTER_ROUTE_SOURCES["raid_boss"],
            {
                "Raid": {
                    "InfoList": [{"PalId": {"Key": target}}],
                    "EggPalIDAndWeight": [{"Key": {"Key": target}, "Value": 1}],
                    "SummonMeteor_Num": [],
                }
            },
        )
        write_table(
            self.export_root,
            self.ITEMS,
            {
                "Raid": {
                    "bLegalInGame": False,
                    "TypeA": "EPalItemTypeA::Consume",
                    "TypeB": "EPalItemTypeB::ConsumeOther",
                }
            },
        )

        graph = self.build()

        self.assertEqual(graph[target].acquisition_sources, ())
        self.assertEqual(graph[target].encounter_sources, ())
        self.assertTrue(
            any(
                item.kind == "illegal_raid_summon_item" and item.source_id == "Raid"
                for item in graph.diagnostics
            )
        )

    def test_raid_summon_reachability_uses_direct_recipe_and_reward_closure(
        self,
    ) -> None:
        legal_item = {
            "bLegalInGame": True,
            "TypeA": "EPalItemTypeA::Consume",
            "TypeB": "EPalItemTypeB::ConsumeOther",
        }
        write_table(
            self.export_root,
            self.ITEMS,
            {
                **{
                    item_id: legal_item
                    for item_id in ("Direct", "Recipe", "Reward", "Self")
                },
                "Blueprint": {"bLegalInGame": True},
                "Material": {"bLegalInGame": True},
            },
        )
        write_table(
            self.export_root,
            game_data.CHARACTER_ROUTE_SOURCES["raid_boss"],
            {
                "Direct": {
                    "InfoList": [],
                    "EggPalIDAndWeight": [{"Key": {"Key": "AlphaPal"}, "Value": 1}],
                    "SummonMeteor_Num": [],
                    "SuccessItemList": [
                        {
                            "ItemName": {"Key": "Reward"},
                            "Rate": 100,
                            "Min": 1,
                            "Max": 1,
                        }
                    ],
                },
                "Recipe": {
                    "InfoList": [],
                    "EggPalIDAndWeight": [{"Key": {"Key": "AlphaFamily"}, "Value": 1}],
                    "SummonMeteor_Num": [],
                    "SuccessItemList": [],
                },
                "Reward": {
                    "InfoList": [],
                    "EggPalIDAndWeight": [
                        {"Key": {"Key": "ReachableHuman"}, "Value": 1}
                    ],
                    "SummonMeteor_Num": [],
                    "SuccessItemList": [],
                },
                "Self": {
                    "InfoList": [],
                    "EggPalIDAndWeight": [
                        {"Key": {"Key": "UnreachableHuman"}, "Value": 1}
                    ],
                    "SummonMeteor_Num": [],
                    "SuccessItemList": [
                        {
                            "ItemName": {"Key": "Self"},
                            "Rate": 100,
                            "Min": 1,
                            "Max": 1,
                        }
                    ],
                },
            },
        )
        write_table(
            self.export_root,
            game_data.RAID_REACHABILITY_SOURCES["recipes"],
            {
                "BuildRecipe": {
                    "Product_Id": "Recipe",
                    "Product_Count": 1,
                    "UnlockItemID": "Blueprint",
                    "Material1_Id": "Material",
                    "Material1_Count": 1,
                }
            },
        )
        self._seed_reachable_raid_items(
            "Direct", "Blueprint", "Material", "UnknownLotteryItem"
        )

        graph = self.build()

        expected = {
            "AlphaPal": ("raid-egg", "Direct"),
            "AlphaFamily": ("raid-egg", "Recipe"),
            "ReachableHuman": ("raid-egg", "Reward"),
        }
        for character_id, source in expected.items():
            self.assertIn(
                source,
                {
                    (item.kind, item.source_id)
                    for item in graph[character_id].acquisition_sources
                },
            )
        self.assertNotIn(
            "raid-egg",
            {item.kind for item in graph["UnreachableHuman"].acquisition_sources},
        )
        self.assertTrue(
            any(
                item.kind == "unreachable_raid_summon_item" and item.source_id == "Self"
                for item in graph.diagnostics
            )
        )
        self.assertEqual(
            [
                (item.source_id, item.detail)
                for item in graph.diagnostics
                if item.kind == "unknown_item"
            ],
            [("UnknownLotteryItem", "FixtureRaidItem3.StaticItemId")],
        )

    def test_raid_summon_item_join_and_shape_fail_closed(self) -> None:
        target = "UnreachableHuman"
        write_table(
            self.export_root,
            game_data.CHARACTER_ROUTE_SOURCES["raid_boss"],
            {
                "Raid": {
                    "InfoList": [{"PalId": {"Key": target}}],
                    "EggPalIDAndWeight": [],
                    "SummonMeteor_Num": [],
                }
            },
        )
        cases = (
            ({}, "missing exact summon item"),
            (
                {
                    "Raid": {
                        "bLegalInGame": "true",
                        "TypeA": "EPalItemTypeA::Consume",
                        "TypeB": "EPalItemTypeB::ConsumeOther",
                    }
                },
                "bLegalInGame",
            ),
            (
                {
                    "Raid": {
                        "bLegalInGame": True,
                        "TypeA": "EPalItemTypeA::Consume",
                        "TypeB": "EPalItemTypeB::Weapon",
                    }
                },
                "ConsumeOther",
            ),
        )
        for items, message in cases:
            with self.subTest(message=message):
                write_table(self.export_root, self.ITEMS, items)
                with self.assertRaisesRegex((TypeError, ValueError), message):
                    self.build()

    def test_raid_egg_and_servant_counts_reject_negative_or_missing_generator(
        self,
    ) -> None:
        target = "UnreachableHuman"
        write_table(
            self.export_root,
            self.ITEMS,
            {
                "Raid": {
                    "bLegalInGame": True,
                    "TypeA": "EPalItemTypeA::Consume",
                    "TypeB": "EPalItemTypeB::ConsumeOther",
                }
            },
        )
        self._seed_reachable_raid_items("Raid")
        invalid_rows = (
            (
                {
                    "InfoList": [],
                    "EggPalIDAndWeight": [{"Key": {"Key": target}, "Value": -1}],
                    "SummonMeteor_Num": [],
                },
                "cannot be negative",
            ),
            (
                {
                    "InfoList": [],
                    "EggPalIDAndWeight": [
                        {"Key": {"Key": "UnknownEggPal"}, "Value": 1}
                    ],
                    "SummonMeteor_Num": [],
                },
                "unknown character UnknownEggPal",
            ),
            (
                {
                    "InfoList": [],
                    "EggPalIDAndWeight": [],
                    "SummonMeteor_Num": [
                        {
                            "HPRate": 0.5,
                            "SummonPalInfoList": [
                                {
                                    "PalNameAndNum": [
                                        {"Key": {"Key": target}, "Value": 1}
                                    ]
                                }
                            ],
                        }
                    ],
                },
                "SummonGeneratorClass",
            ),
        )
        for row, message in invalid_rows:
            with self.subTest(message=message):
                write_table(
                    self.export_root,
                    game_data.CHARACTER_ROUTE_SOURCES["raid_boss"],
                    {"Raid": row},
                )
                with self.assertRaisesRegex((TypeError, ValueError), message):
                    self.build()

    def test_disabled_shop_route_emits_only_a_coverage_diagnostic(self) -> None:
        target = "UnreachableHuman"
        write_table(
            self.export_root,
            game_data.CHARACTER_ROUTE_SOURCES["shop"],
            {"Shop": {"CharacterIDArray": [{"Key": target}]}},
        )
        self.policy["domains"]["skills"]["supported_routes"].remove("shop_table_direct")

        graph = self.build()

        self.assertNotIn(
            "shop-table-direct",
            {source.kind for source in graph[target].acquisition_sources},
        )
        self.assertTrue(
            any(
                item.kind == "coverage_gap" and "shop_table_direct" in item.detail
                for item in graph.diagnostics
            ),
            graph.diagnostics,
        )

    def test_supported_routes_policy_rejects_malformed_values(self) -> None:
        cases = (
            "shop_table_direct",
            ["shop_table_direct", "shop_table_direct"],
            ["not_a_route"],
            [123],
        )
        for supported_routes in cases:
            with self.subTest(supported_routes=supported_routes):
                self.policy["domains"]["skills"]["supported_routes"] = supported_routes
                with self.assertRaisesRegex(ValueError, "supported_routes"):
                    self.build()

    def test_human_boss_mono_and_squad_shapes_select_exact_boss_targets(self) -> None:
        placements = load_table(self.export_root, self.PLACEMENTS)
        placements.update(
            {
                "Mono": {
                    "SpawnerName": "mono",
                    "SpawnerType": "EPalSpawnedCharacterType::FieldBoss",
                    "PlacementType": "EPalSpawnerPlacementType::FieldBoss",
                    "SpawnerClass": {
                        "AssetPathName": (
                            "/Game/Pal/Blueprint/Spawner/HumanNPCBoss/BP_NameMismatch."
                            "BP_NameMismatch_C"
                        )
                    },
                },
                "Squad": {
                    "SpawnerName": "squad",
                    "SpawnerType": "EPalSpawnedCharacterType::FieldBoss",
                    "PlacementType": "EPalSpawnerPlacementType::FieldBoss",
                    "SpawnerClass": {
                        "AssetPathName": (
                            "/Game/Pal/Blueprint/Spawner/HumanNPCBoss/BP_Squad."
                            "BP_Squad_C"
                        )
                    },
                },
            }
        )
        write_table(self.export_root, self.PLACEMENTS, placements)
        write_asset(
            self.export_root,
            "Pal/Content/Pal/Blueprint/Spawner/HumanNPCBoss/BP_NameMismatch",
            [
                {
                    "Type": "BP_NameMismatch_C",
                    "Name": "Default__BP_NameMismatch_C",
                    "Properties": {
                        "HumanName": {"Key": "UnreachableHuman"},
                        "OtomoName": {"Key": "ScenarioFamily"},
                    },
                }
            ],
        )
        write_asset(
            self.export_root,
            "Pal/Content/Pal/Blueprint/Spawner/HumanNPCBoss/BP_Squad",
            [
                {
                    "Type": "BP_Squad_C",
                    "Name": "Default__BP_Squad_C",
                    "Properties": {"SaveKeyName": "ReachableHuman"},
                },
                *[
                    {
                        "Type": "BP_NPCSpawnPointComponent_C",
                        "Name": f"Point{index}",
                        "Properties": {"NPCName": {"Key": character_id}},
                    }
                    for index, character_id in enumerate(
                        ("ReachableHuman", "UnreachableHuman", "ScenarioFamily")
                    )
                ],
            ],
        )

        graph = self.build()

        self.assertIn("boss", graph["UnreachableHuman"].variant_tags)
        self.assertIn("boss", graph["ReachableHuman"].variant_tags)
        self.assertNotIn("boss", graph["ScenarioFamily"].variant_tags)
        self.assertFalse(
            any(item.kind == "unsupported_spawner" for item in graph.diagnostics)
        )

    def test_incident_requires_placed_actor_positive_lottery_and_exact_spawn_rows(
        self,
    ) -> None:
        world = game_data.CHARACTER_ROUTE_SOURCES["incident_world"]
        write_asset(
            self.export_root,
            world,
            [
                {
                    "Type": "BP_Incident_C",
                    "Name": "PlacedIncident",
                    "Class": (
                        "BlueprintGeneratedClass'Pal/Content/Pal/Blueprint/Incident/"
                        "Random/BP_Incident.BP_Incident_C'"
                    ),
                    "Outer": {"ObjectName": "Level'PL_MainWorld5:PersistentLevel'"},
                    "Properties": {
                        "LotteryClass": {
                            "ObjectName": "BlueprintGeneratedClass'BP_Lottery_C'",
                            "ObjectPath": (
                                "Pal/Content/Pal/Blueprint/Incident/Random/BP_Lottery.0"
                            ),
                        }
                    },
                }
            ],
        )
        write_asset(
            self.export_root,
            "Pal/Content/Pal/Blueprint/Incident/Random/BP_Incident",
            [
                {
                    "Type": "BP_Incident_C",
                    "Name": "Default__BP_Incident_C",
                    "Properties": {
                        "LotteryClass": {
                            "ObjectPath": (
                                "Pal/Content/Pal/Blueprint/Incident/Random/BP_Wrong.0"
                            )
                        }
                    },
                }
            ],
        )
        write_asset(
            self.export_root,
            "Pal/Content/Pal/Blueprint/Incident/Random/BP_Lottery",
            [
                {
                    "Type": "BP_Lottery_C",
                    "Name": "Default__BP_Lottery_C",
                    "Properties": {
                        "LotteryParameters": [
                            {"SettingName": "TestSetting", "LotteryRate": 1},
                            {"SettingName": "Missing", "LotteryRate": 0},
                        ]
                    },
                }
            ],
        )
        write_table(
            self.export_root,
            game_data.CHARACTER_ROUTE_SOURCES["incident_settings"],
            {
                "TestSetting": {
                    "MonsterSpawnData": {
                        "ObjectPath": (
                            "Pal/Content/Pal/DataTable/Incident/DT_TestSpawn.0"
                        )
                    },
                    "NPCSpawnData": {"ObjectPath": "None"},
                }
            },
        )
        write_table(
            self.export_root,
            "Pal/Content/Pal/DataTable/Incident/DT_TestSpawn",
            {
                "NoWeightField": {
                    "CharacterID": {"Key": "ScenarioFamily"},
                }
            },
        )

        graph = self.build()

        self.assertIn(
            "incident",
            {source.kind for source in graph["ScenarioFamily"].acquisition_sources},
        )
        self.assertFalse(
            any(item.kind == "unsupported_acquisition" for item in graph.diagnostics)
        )

    def test_incident_lottery_rejects_a_decoy_default_object(self) -> None:
        self._write_incident_lottery_fixture(
            object_name="BlueprintGeneratedClass'BP_Lottery_C'",
            lottery_exports=[
                {
                    "Type": "BP_Decoy_C",
                    "Name": "Default__BP_Decoy_C",
                    "Properties": {"LotteryParameters": []},
                }
            ],
        )

        with self.assertRaisesRegex(ValueError, "BP_Lottery_C"):
            self.build()

    def test_incident_dependency_discovery_rejects_a_decoy_default_object(
        self,
    ) -> None:
        self._write_incident_lottery_fixture(
            object_name="BlueprintGeneratedClass'BP_Lottery_C'",
            lottery_exports=[
                {
                    "Type": "BP_Decoy_C",
                    "Name": "Default__BP_Decoy_C",
                    "Properties": {"LotteryParameters": []},
                }
            ],
        )

        with self.assertRaisesRegex(ValueError, "BP_Lottery_C"):
            extract_game_data._incident_dependencies(self.export_root)

    def test_incident_lottery_rejects_object_name_path_mismatch(self) -> None:
        self._write_incident_lottery_fixture(
            object_name="BlueprintGeneratedClass'BP_Other_C'",
            lottery_exports=[
                {
                    "Type": "BP_Lottery_C",
                    "Name": "Default__BP_Lottery_C",
                    "Properties": {"LotteryParameters": []},
                }
            ],
        )

        with self.assertRaisesRegex(ValueError, "ObjectName.*ObjectPath|mismatch"):
            self.build()

    def test_action_blueprint_alone_does_not_validate_unreachable_human(self) -> None:
        evidence = self.build()["UnreachableHuman"]

        self.assertFalse(evidence.regularly_obtainable)
        self.assertEqual(evidence.acquisition_sources, ())
        self.assertEqual(evidence.action_declarations, frozenset())

    def test_rowname_resolves_before_empty_fname_sentinel(self) -> None:
        graph = self.build()

        self.assertTrue(graph["RowName"].regularly_obtainable)
        self.assertEqual(
            tuple(
                (source.kind, source.source_id)
                for source in graph["RowName"].acquisition_sources
            ),
            (("placement", "OrdinaryPlacement"),),
        )
        self.assertNotIn("None", graph)

    def test_monster_scenario_fields_require_actual_booleans(self) -> None:
        valid_monsters = load_table(self.export_root, self.MONSTERS)

        for field in ("IsBoss", "IsTowerBoss", "IsRaidBoss", "Predator"):
            for malformed in ("False", 0, None):
                with self.subTest(field=field, malformed=malformed):
                    monsters = deepcopy(valid_monsters)
                    monsters["Anubis"][field] = malformed
                    write_table(self.export_root, self.MONSTERS, monsters)

                    with self.assertRaises(TypeError) as raised:
                        self.build()

                    self.assertEqual(
                        str(raised.exception), f"Anubis.{field} must be a bool"
                    )

    def _seed_valid_fail_closed_scenario_routes(self) -> None:
        monsters = load_table(self.export_root, self.MONSTERS)
        monsters["GYM_ElecPanda_Otomo"] = {
            "Tribe": "EPalTribeID::GYM_ElecPanda_Otomo",
            "BPClass": "GYM_ElecPanda_Otomo",
            "IsBoss": False,
            "IsTowerBoss": False,
            "IsRaidBoss": False,
            "Predator": False,
            "NamePrefixID": "GYM_NAME_Fixture",
        }
        monsters["KingWhale"] = {
            "Tribe": "EPalTribeID::KingWhale",
            "BPClass": "KingWhale",
            "IsBoss": False,
            "IsTowerBoss": False,
            "IsRaidBoss": False,
            "Predator": False,
        }
        for character_id in ("BOSS_KingWhale", "BOSS_KingWhale_otomo"):
            monsters[character_id] = {
                "Tribe": "EPalTribeID::KingWhale",
                "BPClass": character_id,
                "IsBoss": True,
                "IsTowerBoss": False,
                "IsRaidBoss": False,
                "Predator": False,
            }
        write_table(self.export_root, self.MONSTERS, monsters)

        bp_classes = load_table(self.export_root, game_data.SKILL_SOURCES["bp_classes"])
        bp_classes["GYM_ElecPanda_Otomo"] = {"BPClass": {"AssetPathName": "None"}}
        bp_classes["KingWhale"] = {"BPClass": {"AssetPathName": "None"}}
        actor_root = "Pal/Content/Pal/Blueprint/Character/Monster/PalActorBP/KingWhale"
        for character_id, actor_name in (
            ("BOSS_KingWhale", "BP_KingWhale_BOSS"),
            ("BOSS_KingWhale_otomo", "BP_KingWhale_BOSS_otomo"),
        ):
            actor_path = f"{actor_root}/{actor_name}"
            bp_classes[character_id] = {
                "BPClass": {
                    "AssetPathName": (
                        f"/Game/{actor_path.removeprefix('Pal/Content/')}."
                        f"{actor_name}_C"
                    )
                }
            }
            write_asset(
                self.export_root,
                actor_path,
                [
                    {
                        "Type": "BlueprintGeneratedClass",
                        "Name": f"{actor_name}_C",
                        "Package": actor_path,
                        "SuperStruct": {
                            "ObjectName": "Class'PalMonsterCharacter'",
                            "ObjectPath": "/Script/Pal",
                        },
                    },
                    {
                        "Type": "PalStaticCharacterParameterComponent",
                        "Name": "StaticCharacterParameterComponent",
                        "Properties": {"WazaActionDeclarationMap": []},
                    },
                ],
            )
        write_table(
            self.export_root,
            game_data.SKILL_SOURCES["bp_classes"],
            bp_classes,
        )

        module_path = game_data.CHARACTER_SCENARIO_SOURCES["kingwhale_combat"]
        write_asset(
            self.export_root,
            module_path,
            [
                {"Type": "Ignored"},
                {
                    "Type": "BP_AICombatModule_KingWhale_Wild_C",
                    "Name": "Default__BP_AICombatModule_KingWhale_Wild_C",
                    "Properties": {
                        "CaptureReplaceSourceCharacterID": "BOSS_KingWhale",
                        "CaptureReplaceTargetCharacterID": "BOSS_KingWhale_otomo",
                    },
                },
            ],
        )
        write_asset(
            self.export_root,
            game_data.CHARACTER_SCENARIO_SOURCES["kingwhale_controller"],
            [
                {"Type": "BlueprintGeneratedClass"},
                {
                    "Type": "BP_MonsterAIController_Wild_KingWhale_C",
                    "Name": "Default__BP_MonsterAIController_Wild_KingWhale_C",
                    "Properties": {
                        "CombatModuleClass": {
                            "ObjectName": (
                                "BlueprintGeneratedClass'"
                                "BP_AICombatModule_KingWhale_Wild_C'"
                            ),
                            "ObjectPath": f"{module_path}.0",
                        }
                    },
                },
            ],
        )
        write_asset(
            self.export_root,
            game_data.CHARACTER_SCENARIO_SOURCES["grass_boss_reward"],
            [
                *({"Type": "Ignored"} for _ in range(18)),
                {
                    "Type": "FNBP_GetCharacter_C",
                    "Properties": {
                        "PalId": {"Key": "GYM_ElecPanda_Otomo"},
                        "Level": 1,
                        "NetworkInvokeName": "Get_Zoe",
                    },
                },
                {
                    "Type": "FNBP_GetCharacter_C",
                    "Properties": {
                        "PalId": {"Key": "GYM_ElecPanda_Otomo"},
                        "Level": 1,
                        "NetworkInvokeName": "Get_ZoeRE",
                    },
                },
            ],
        )

    def test_complete_fixture_exposes_no_diagnostics(self) -> None:
        self._seed_valid_fail_closed_scenario_routes()
        graph = self.build()

        self.assertTrue(graph.complete, graph.diagnostics)
        self.assertEqual(graph.diagnostics, ())


class MonsterActionDeclarationTests(unittest.TestCase):
    MONSTERS = "Pal/Content/Pal/DataTable/Character/DT_PalMonsterParameter_Common"
    BP_CLASSES = "Pal/Content/Pal/DataTable/Character/DT_PalBPClass_Common"
    MONSTER_BASE = "Pal/Content/Pal/Blueprint/Character/Monster/BP_MonsterBase"
    ORDINARY_BP = (
        "Pal/Content/Pal/Blueprint/Character/Monster/PalActorBP/Fixture/BP_Ordinary"
    )
    BOSS_BP = "Pal/Content/Pal/Blueprint/Character/Monster/PalActorBP/Fixture/BP_Boss"

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.monsters = {
            "Ordinary": {
                "BPClass": "ordinaryclass",
                "IsBoss": False,
                "IsTowerBoss": False,
                "IsRaidBoss": False,
            },
            "Boss": {
                "BPClass": "BossClass",
                "IsBoss": True,
                "IsTowerBoss": False,
                "IsRaidBoss": False,
            },
        }
        self.bp_classes = {
            "OrdinaryClass": {
                "BPClass": {
                    "AssetPathName": (
                        "/Game/Pal/Blueprint/Character/Monster/PalActorBP/Fixture/"
                        "BP_Ordinary.BP_Ordinary_C"
                    )
                }
            },
            "BossClass": {
                "BPClass": {
                    "AssetPathName": (
                        "/Game/Pal/Blueprint/Character/Monster/PalActorBP/Fixture/"
                        "BP_Boss.BP_Boss_C"
                    )
                }
            },
        }
        write_table(self.root, self.MONSTERS, self.monsters)
        write_table(self.root, self.BP_CLASSES, self.bp_classes)
        self._write_blueprint(
            self.MONSTER_BASE,
            parent=None,
            actions=(
                "EPalWazaID::Common",
                "EPalWazaID::Unique_CaptainPenguin_BodySlide",
                "EPalWazaID::Unique_GhostAnglerfish_SweepBait",
            ),
        )
        self._write_blueprint(
            self.ORDINARY_BP,
            parent=self.MONSTER_BASE,
            actions=("EPalWazaID::InheritedOrdinary",),
            tombstones=(
                "EPalWazaID::Unique_CaptainPenguin_BodySlide",
                "EPalWazaID::Unique_GhostAnglerfish_SweepBait",
            ),
        )
        self._write_blueprint(
            self.BOSS_BP,
            parent=self.ORDINARY_BP,
            actions=("EPalWazaID::BossActionOnly",),
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def _class_name(virtual_path: str) -> str:
        return PurePosixPath(virtual_path).name + "_C"

    def _write_blueprint(
        self,
        virtual_path: str,
        *,
        parent: str | None,
        actions: tuple[str, ...],
        tombstones: tuple[str, ...] = (),
        extra_exports: tuple[dict, ...] = (),
        malformed_parent_name: str | None = None,
    ) -> None:
        class_name = self._class_name(virtual_path)
        if parent is None:
            super_struct = {
                "ObjectName": "Class'PalMonsterCharacter'",
                "ObjectPath": "/Script/Pal",
            }
        else:
            parent_class = self._class_name(parent)
            super_struct = {
                "ObjectName": (
                    malformed_parent_name or f"BlueprintGeneratedClass'{parent_class}'"
                ),
                "ObjectPath": f"{parent}.0",
            }
        write_asset(
            self.root,
            virtual_path,
            [
                {
                    "Type": "BlueprintGeneratedClass",
                    "Name": class_name,
                    "Package": virtual_path,
                    "SuperStruct": super_struct,
                },
                {
                    "Type": "PalStaticCharacterParameterComponent",
                    "Name": "StaticCharacterParameterComponent",
                    "Properties": {
                        "WazaActionDeclarationMap": [
                            {
                                "Key": skill_id,
                                "Value": {
                                    "AssetPathName": (
                                        "/Game/Pal/Blueprint/Action/Waza/"
                                        f"BP_{index}.BP_{index}_C"
                                    )
                                },
                            }
                            for index, skill_id in enumerate(actions)
                        ]
                        + [
                            {
                                "Key": skill_id,
                                "Value": {"AssetPathName": ""},
                            }
                            for skill_id in tombstones
                        ]
                    },
                },
                *extra_exports,
            ],
        )

    def build(self):
        self.assertTrue(
            hasattr(game_data, "build_monster_action_declarations"),
            "build_monster_action_declarations is not implemented",
        )
        return game_data.build_monster_action_declarations(
            self.root, self.monsters, self.bp_classes
        )

    def test_exact_bpclass_join_traverses_inherited_action_maps(self) -> None:
        actions, sources = self.build()

        self.assertEqual(
            actions,
            {
                "Ordinary": frozenset(
                    {"EPalWazaID::Common", "EPalWazaID::InheritedOrdinary"}
                ),
                "Boss": frozenset(
                    {
                        "EPalWazaID::Common",
                        "EPalWazaID::InheritedOrdinary",
                        "EPalWazaID::BossActionOnly",
                    }
                ),
            },
        )
        self.assertEqual(
            sources,
            tuple(sorted({self.MONSTER_BASE, self.ORDINARY_BP, self.BOSS_BP})),
        )

    def test_unimplemented_bpclass_is_skipped_and_ambiguity_is_rejected(self) -> None:
        missing = deepcopy(self.monsters)
        missing["Boss"]["BPClass"] = "MissingClass"
        actions, _ = game_data.build_monster_action_declarations(
            self.root, missing, self.bp_classes
        )
        self.assertNotIn("Boss", actions)

        ambiguous = deepcopy(self.bp_classes)
        ambiguous["bossclass"] = ambiguous["BossClass"]
        with self.assertRaisesRegex(ValueError, "Case-insensitive key collision"):
            game_data.build_monster_action_declarations(
                self.root, self.monsters, ambiguous
            )

    def test_bpclass_types_and_exact_pal_actor_paths_are_required(self) -> None:
        malformed_monsters = deepcopy(self.monsters)
        malformed_monsters["Boss"]["BPClass"] = None
        with self.assertRaisesRegex(TypeError, "Boss.BPClass"):
            game_data.build_monster_action_declarations(
                self.root, malformed_monsters, self.bp_classes
            )

        malformed_classes = deepcopy(self.bp_classes)
        malformed_classes["BossClass"]["BPClass"] = {"AssetPathName": 42}
        with self.assertRaisesRegex(TypeError, "BossClass.BPClass"):
            game_data.build_monster_action_declarations(
                self.root, self.monsters, malformed_classes
            )

        mismatched_class = deepcopy(self.bp_classes)
        mismatched_class["BossClass"]["BPClass"]["AssetPathName"] = (
            "/Game/Pal/Blueprint/Character/Monster/PalActorBP/Fixture/"
            "BP_Boss.BP_Other_C"
        )
        with self.assertRaisesRegex(ValueError, "BP_Other_C.*BP_Boss_C|does not match"):
            game_data.build_monster_action_declarations(
                self.root, self.monsters, mismatched_class
            )

        outside_pal_actor = deepcopy(self.bp_classes)
        outside_pal_actor["BossClass"]["BPClass"]["AssetPathName"] = (
            "/Game/Pal/Blueprint/Character/Monster/BP_Boss.BP_Boss_C"
        )
        with self.assertRaisesRegex(ValueError, "PalActorBP"):
            game_data.build_monster_action_declarations(
                self.root, self.monsters, outside_pal_actor
            )

    def test_missing_or_ambiguous_blueprint_exports_are_rejected(self) -> None:
        missing_classes = deepcopy(self.bp_classes)
        missing_classes["BossClass"]["BPClass"]["AssetPathName"] = (
            "/Game/Pal/Blueprint/Character/Monster/PalActorBP/Fixture/"
            "BP_Missing.BP_Missing_C"
        )
        with self.assertRaisesRegex(FileNotFoundError, "BP_Missing"):
            game_data.build_monster_action_declarations(
                self.root, self.monsters, missing_classes
            )

        duplicate = {
            "Type": "BlueprintGeneratedClass",
            "Name": "BP_Boss_C",
            "Package": self.BOSS_BP,
            "SuperStruct": {
                "ObjectName": "BlueprintGeneratedClass'BP_Ordinary_C'",
                "ObjectPath": f"{self.ORDINARY_BP}.0",
            },
        }
        self._write_blueprint(
            self.BOSS_BP,
            parent=self.ORDINARY_BP,
            actions=("EPalWazaID::BossActionOnly",),
            extra_exports=(duplicate,),
        )
        with self.assertRaisesRegex(ValueError, "exactly one.*BP_Boss_C"):
            self.build()

    def test_parent_identity_and_action_map_types_are_strict(self) -> None:
        self._write_blueprint(
            self.BOSS_BP,
            parent=self.ORDINARY_BP,
            actions=("EPalWazaID::BossActionOnly",),
            malformed_parent_name="BlueprintGeneratedClass'BP_Wrong_C'",
        )
        with self.assertRaisesRegex(
            ValueError, "BP_Wrong_C.*BP_Ordinary_C|does not match"
        ):
            self.build()

        self._write_blueprint(
            self.BOSS_BP,
            parent=self.ORDINARY_BP,
            actions=("EPalWazaID::BossActionOnly",),
        )
        asset = load_asset(self.root, self.BOSS_BP)
        asset[1]["Properties"]["WazaActionDeclarationMap"][0]["Key"] = None
        write_asset(self.root, self.BOSS_BP, asset)
        with self.assertRaisesRegex(TypeError, "WazaActionDeclarationMap.*Key"):
            self.build()


class CharacterRecordTests(unittest.TestCase):
    @staticmethod
    def character_row(**overrides) -> dict:
        row = {
            "Tribe": "EPalTribeID::BaseFamily",
            "BPClass": "BaseFamily",
            "ZukanIndex": 42,
            "ZukanIndexSuffix": "B",
            "IsBoss": False,
            "IsTowerBoss": False,
            "IsRaidBoss": False,
            "Predator": False,
            "FirstDefeatRewardItemID": "None",
            "OverrideNameTextID": "None",
            "NamePrefixID": "None",
            "ElementType1": "EPalElementType::Water",
            "ElementType2": "EPalElementType::None",
            "Hp": 101,
            "ShotAttack": 102,
            "Defense": 103,
            "MeleeAttack": 104,
            "CraftSpeed": 105,
            "MaxFullStomach": 106,
            "BestWorkSuitability": "EPalWorkSuitability::Watering",
            "Size": "EPalSizeType::M",
            "Rarity": 7,
            "Support": 108,
            "Friendship_HP": 1.1,
            "Friendship_ShotAttack": 1.2,
            "Friendship_Defense": 1.3,
            "Friendship_CraftSpeed": 1.4,
            "EnemyMaxHPRate": 2.1,
            "EnemyInflictDamageRate": 2.2,
            "EnemyReceiveDamageRate": 2.3,
            "EnemyWazaCoolTimeRate": 2.4,
            "CaptureRateCorrect": 0.5,
            "ExpRatio": 3.1,
            "Price": 999.0,
            "StatusResistUpRate": 3.2,
            "WalkSpeed": 110,
            "SlowWalkSpeed": 111,
            "RunSpeed": 112,
            "RideSprintSpeed": 113,
            "TransportSpeed": 114,
            "SwimSpeed": 115,
            "SwimDashSpeed": 116,
            "FullStomachDecreaseRate": 0.9,
            "FoodAmount": 8,
            "Stamina": 117,
            "Nocturnal": True,
            "Edible": False,
            "BiologicalGrade": 5,
            "MaleProbability": 40,
            "CombiRank": 120,
            "CombiDuplicatePriority": 121,
            "IgnoreCombi": False,
            "PassiveSkill1": "TestPassive",
            "PassiveSkill2": "None",
            "PassiveSkill3": "None",
            "PassiveSkill4": "None",
        }
        row.update(
            {
                f"WorkSuitability_{name}": index
                for index, name in enumerate(
                    (
                        "EmitFlame",
                        "Watering",
                        "Seeding",
                        "GenerateElectricity",
                        "Handcraft",
                        "Collection",
                        "Deforest",
                        "Mining",
                        "OilExtraction",
                        "ProductMedicine",
                        "Cool",
                        "Transport",
                        "MonsterFarm",
                    )
                )
            }
        )
        row.update(overrides)
        return row

    @staticmethod
    def text(value: str) -> dict:
        return {"TextData": {"LocalizedString": value, "SourceString": value}}

    def setUp(self) -> None:
        self.monsters = {
            "BaseFamily": self.character_row(),
            "ScenarioVariant": self.character_row(
                BPClass="ScenarioVariant",
                IsTowerBoss=True,
                Predator=True,
                FirstDefeatRewardItemID="BossDefeatReward_BossRush",
                ZukanIndex=-1,
            ),
            "AlphaVariant": self.character_row(
                BPClass="AlphaVariant", IsBoss=True, ZukanIndex=-1
            ),
        }
        self.humans = {
            "ReachableHuman": self.character_row(
                Tribe="EPalTribeID::Human",
                BPClass="NPC_ReachableHuman",
                ZukanIndex=-1,
                ZukanIndexSuffix="",
                BestWorkSuitability="EPalWorkSuitability::None",
            )
        }
        source = game_data.EvidenceSource("placement", "ordinary")
        self.evidence = game_data.CharacterEvidenceGraph(
            {
                "BaseFamily": game_data.Evidence(
                    "BaseFamily",
                    "BaseFamily",
                    True,
                    "BaseFamily",
                    frozenset({"base"}),
                    (source,),
                    (game_data.EvidenceSource("ordinary-placement", "ordinary"),),
                    frozenset(),
                    True,
                ),
                "ScenarioVariant": game_data.Evidence(
                    "ScenarioVariant",
                    "BaseFamily",
                    True,
                    "BaseFamily",
                    frozenset({"tower", "predator", "boss-rush"}),
                    (),
                    (game_data.EvidenceSource("scenario-placement", "scenario"),),
                    frozenset(),
                    False,
                ),
                "AlphaVariant": game_data.Evidence(
                    "AlphaVariant",
                    "BaseFamily",
                    True,
                    "BaseFamily",
                    frozenset({"boss", "alpha"}),
                    (game_data.EvidenceSource("placement", "alpha"),),
                    (game_data.EvidenceSource("ordinary-placement", "alpha"),),
                    frozenset(),
                    True,
                ),
                "ReachableHuman": game_data.Evidence(
                    "ReachableHuman",
                    "ReachableHuman",
                    True,
                    "Human",
                    frozenset({"human"}),
                    (source,),
                    (game_data.EvidenceSource("ordinary-placement", "ordinary"),),
                    frozenset({"TestSkill"}),
                    True,
                ),
            },
            (),
        )
        self.tables = {
            "monsters": self.monsters,
            "humans": self.humans,
            "levels": {
                "BaseSkill": {
                    "PalId": "basefamily",
                    "WazaID": "TestSkill",
                    "Level": 7,
                }
            },
            "passives": {"TestPassive": {}},
            "breeding": {
                "UniquePair": {
                    "ParentTribeA": "EPalTribeID::ParentA",
                    "ParentTribeB": "EPalTribeID::ParentB",
                    "ParentGenderA": "EPalGenderType::Male",
                    "ParentGenderB": "EPalGenderType::Female",
                    "ChildCharacterID": "basefamily",
                }
            },
            "icons": {
                "basefamily": {
                    "Icon": {
                        "AssetPathName": (
                            "/Game/Pal/Texture/PalIcon/Normal/T_Base.T_Base"
                        ),
                        "SubPathString": "",
                    }
                }
            },
            "skins": {
                "GoodSkin": {
                    "SkinName": "GoodSkin",
                    "SkinType": "EPalSkinType::Pal",
                    "SkinStaticClass": "PalCharacterClass",
                    "bIsHairAccessory": False,
                    "TargetActorClassName": "None",
                    "TargetPalName": "basefamily",
                    "bAutoGetItem": False,
                    "PlatformItemID_Steam": -1,
                },
                "MissingSkin": {
                    "SkinName": "MissingSkin",
                    "SkinType": "EPalSkinType::Pal",
                    "SkinStaticClass": "PalCharacterClass",
                    "bIsHairAccessory": False,
                    "TargetActorClassName": "None",
                    "TargetPalName": "BaseFamily",
                    "bAutoGetItem": False,
                    "PlatformItemID_Steam": -1,
                },
            },
            "skin_icons": {
                "goodskin": {
                    "Icon": {
                        "AssetPathName": "/Game/Pal/Texture/PalIcon/SKin/T_Good.T_Good",
                        "SubPathString": "",
                    }
                }
            },
        }
        self.texts = {
            name: {locale: {} for locale in game_data.LOCALE_DIRECTORIES}
            for name in ("pal", "human", "unique", "prefix", "ui")
        }
        for locale in game_data.LOCALE_DIRECTORIES:
            self.texts["pal"][locale]["PAL_NAME_BaseFamily"] = self.text(
                f"Base {locale}"
            )
            self.texts["human"][locale]["None"] = self.text(f"Human {locale}")
            self.texts["ui"][locale]["SKIN_NAME_GoodSkin"] = self.text(f"Good {locale}")
        self.texts["ui"]["ja"]["SKIN_NAME_MissingSkin"] = self.text("Japanese only")

    def build(self) -> dict:
        self.assertTrue(
            hasattr(game_data, "build_character_records"),
            "build_character_records is not implemented",
        )
        return game_data.build_character_records(self.tables, self.texts, self.evidence)

    def test_records_preserve_source_fields_and_choose_safe_availability(self) -> None:
        built = self.build()
        base = built["pals"]["BaseFamily"]
        scenario = built["pals"]["ScenarioVariant"]
        alpha = built["pals"]["AlphaVariant"]

        self.assertEqual(
            base["Stats"],
            {
                "HP": 101,
                "ATK": 102,
                "DEF": 103,
                "MELEE": 104,
                "CRAFTSPEED": 105,
                "FOOD": 106,
            },
        )
        self.assertEqual(base["Parameters"]["Friendship_HP"], 1.1)
        self.assertEqual(base["Parameters"]["WorkSuitability_Watering"], 1)
        self.assertEqual(base["Suitabilities"]["EPalWorkSuitability::Watering"], 1)
        self.assertEqual(base["DefaultPassives"], ["TestPassive"])
        self.assertEqual(base["Attacks"], {"TestSkill": 7})
        self.assertEqual(
            base["Breeding"]["UniqueRecipes"],
            [self.tables["breeding"]["UniquePair"]],
        )
        self.assertFalse(base["Invalid"])
        self.assertTrue(base["RegularlyObtainable"])
        self.assertEqual(base["VariantKind"], "base")
        self.assertTrue(scenario["Invalid"])
        self.assertFalse(scenario["RegularlyObtainable"])
        self.assertEqual(scenario["VariantKind"], "boss-rush")
        self.assertFalse(alpha["Invalid"])
        self.assertEqual(alpha["VariantKind"], "alpha")

    def test_overlapping_otomo_tags_keep_tower_and_boss_display_kinds(self) -> None:
        self.tables["monsters"].update(
            {
                "GYM_ElecPanda_Otomo": self.character_row(
                    BPClass="GYM_ElecPanda_Otomo", ZukanIndex=-1
                ),
                "BOSS_KingWhale_otomo": self.character_row(
                    BPClass="BOSS_KingWhale_otomo", ZukanIndex=-1
                ),
            }
        )
        evidence = dict(self.evidence)
        evidence.update(
            {
                "GYM_ElecPanda_Otomo": game_data.Evidence(
                    "GYM_ElecPanda_Otomo",
                    "BaseFamily",
                    True,
                    "BaseFamily",
                    frozenset({"tower", "otomo"}),
                    (game_data.EvidenceSource("quest-reward", "FABP_GrassBoss01"),),
                    (),
                    frozenset(),
                    True,
                ),
                "BOSS_KingWhale_otomo": game_data.Evidence(
                    "BOSS_KingWhale_otomo",
                    "BaseFamily",
                    True,
                    "BaseFamily",
                    frozenset({"boss", "otomo"}),
                    (
                        game_data.EvidenceSource(
                            "capture-replace", "BP_AICombatModule_KingWhale_Wild"
                        ),
                    ),
                    (),
                    frozenset(),
                    True,
                ),
            }
        )

        built = game_data.build_character_records(
            self.tables,
            self.texts,
            game_data.CharacterEvidenceGraph(evidence, ()),
        )["pals"]

        self.assertEqual(
            built["GYM_ElecPanda_Otomo"]["VariantTags"], ["otomo", "tower"]
        )
        self.assertEqual(built["GYM_ElecPanda_Otomo"]["VariantKind"], "tower")
        self.assertEqual(
            built["BOSS_KingWhale_otomo"]["VariantTags"], ["boss", "otomo"]
        )
        self.assertEqual(built["BOSS_KingWhale_otomo"]["VariantKind"], "boss")

    def test_casefold_family_icon_and_skin_joins_preserve_authoritative_ids(
        self,
    ) -> None:
        built = self.build()

        self.assertEqual(built["pals"]["ScenarioVariant"]["FamilyID"], "BaseFamily")
        self.assertTrue(built["pals"]["ScenarioVariant"]["FamilyResolved"])
        self.assertEqual(built["pals"]["ScenarioVariant"]["IconKey"], "BaseFamily")
        self.assertEqual(built["humans"]["ReachableHuman"]["IconKey"], "Human")
        self.assertEqual(built["skins"]["GoodSkin"]["TargetPalName"], "BaseFamily")
        self.assertEqual(built["skins"]["GoodSkin"]["IconKey"], "GoodSkin")
        self.assertFalse(built["skins"]["GoodSkin"]["Invalid"])
        self.assertEqual(
            built["icon_sources"],
            {
                "icons/pals/BaseFamily.png": (
                    "Pal/Content/Pal/Texture/PalIcon/Normal/T_Base"
                ),
                "icons/pals/skin/GoodSkin.png": (
                    "Pal/Content/Pal/Texture/PalIcon/SKin/T_Good"
                ),
            },
        )

    def test_character_name_localization_join_is_case_insensitive(self) -> None:
        for locale in game_data.LOCALE_DIRECTORIES:
            localized = self.texts["pal"][locale].pop("PAL_NAME_BaseFamily")
            self.texts["pal"][locale]["PAL_NAME_basefamily"] = localized

        built = self.build()

        self.assertEqual(
            built["pals"]["BaseFamily"]["I18n"],
            {
                locale: f"Base {locale}"
                for locale in game_data.LOCALE_DIRECTORIES
            },
        )
        self.assertFalse(
            any(
                item.startswith("character:BaseFamily:")
                for item in built["missing_localizations"]
            )
        )

    def test_missing_skin_icon_is_invalid_and_japanese_text_falls_back(self) -> None:
        built = self.build()
        skin = built["skins"]["MissingSkin"]

        self.assertTrue(skin["Invalid"])
        self.assertEqual(skin["IconKey"], "MissingSkin")
        self.assertEqual(set(skin["I18n"].values()), {"Japanese only"})
        self.assertIn("skin:MissingSkin:en:Name", built["missing_localizations"])
        self.assertIn("icons/pals/skin/MissingSkin.png", built["missing_icons"])

    def test_malformed_source_scalar_is_rejected(self) -> None:
        self.tables["monsters"]["BaseFamily"]["WorkSuitability_Watering"] = "1"

        with self.assertRaisesRegex(
            TypeError, "BaseFamily.WorkSuitability_Watering must be numeric"
        ):
            self.build()

    def test_unresolved_source_family_preserves_raw_tribe_and_resolution_state(
        self,
    ) -> None:
        evidence = dict(self.evidence)
        evidence["ScenarioVariant"] = replace(
            evidence["ScenarioVariant"],
            family_id="MissingTribe",
            family_resolved=False,
        )

        built = game_data.build_character_records(
            self.tables,
            self.texts,
            game_data.CharacterEvidenceGraph(evidence, ()),
        )

        self.assertEqual(built["pals"]["ScenarioVariant"]["FamilyID"], "MissingTribe")
        self.assertFalse(built["pals"]["ScenarioVariant"]["FamilyResolved"])

    def test_character_domain_snapshot_loads_only_resolved_texture_pngs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.tables["icons"]["ReachableHuman"] = {
                "Icon": {
                    "AssetPathName": (
                        "/Game/Pal/Texture/PalIcon/Normal/T_Missing.T_Missing"
                    ),
                    "SubPathString": "",
                }
            }
            source_paths = {
                "monsters": game_data.CHARACTER_EVIDENCE_SOURCES["monsters"],
                "humans": game_data.CHARACTER_EVIDENCE_SOURCES["humans"],
                "levels": game_data.SKILL_SOURCES["levels"],
                "passives": game_data.SKILL_SOURCES["passives"],
                "breeding": game_data.CHARACTER_ROUTE_SOURCES["breeding"],
                **game_data.CHARACTER_SOURCES,
            }
            for name, source_path in source_paths.items():
                write_table(root, source_path, self.tables[name])
            for name, table_name in game_data.CHARACTER_TEXT_TABLES.items():
                for locale in game_data.LOCALE_DIRECTORIES:
                    write_table(
                        root,
                        game_data.text_table_path(table_name, locale),
                        self.texts[name][locale],
                    )
            scenario_prefix_counts = {
                "Pal/Content/Pal/Blueprint/Spawner/Quest": 8,
                (
                    "Pal/Content/Pal/Blueprint/Spawner/SheetsVariant/"
                    "BP_PalSpawner_Sheets_Quest_"
                ): 4,
                (
                    "Pal/Content/Pal/Maps/MainWorld_5/PL_MainWorld5/_Generated_/oilrig_"
                ): 14,
            }
            for prefix, count in scenario_prefix_counts.items():
                for index in range(count):
                    write_asset(root, f"{prefix}Fixture{index}", [{"Type": "Fixture"}])
            for virtual_path in (
                "Pal/Content/Pal/Texture/PalIcon/Normal/T_Base",
                "Pal/Content/Pal/Texture/PalIcon/SKin/T_Good",
            ):
                png = root.joinpath(*virtual_path.split("/")).with_suffix(".png")
                png.parent.mkdir(parents=True, exist_ok=True)
                png.write_bytes(PNG_1X1)

            policy = deepcopy(FIXTURE_POLICY)
            policy["domains"]["characters"]["required_sources"] = (
                list(source_paths.values())
                + [
                    game_data.text_table_path(table_name, locale)
                    for table_name in game_data.CHARACTER_TEXT_TABLES.values()
                    for locale in game_data.LOCALE_DIRECTORIES
                ]
                + list(scenario_prefix_counts)
            )
            with patch.object(
                game_data,
                "build_character_evidence",
                return_value=self.evidence,
            ):
                try:
                    candidate = game_data.build_characters_domain(root, policy)
                except FileNotFoundError as error:
                    self.fail(
                        f"character snapshot did not count prefix assets: {error}"
                    )

            self.assertEqual(candidate.domain, "characters")
            self.assertEqual(
                set(candidate.outputs),
                {
                    "data/pal_data.json",
                    "data/human_data.json",
                    "data/skin_data.json",
                    "icons/pals/BaseFamily.png",
                    "icons/pals/skin/GoodSkin.png",
                },
            )
            self.assertEqual(
                candidate.icon_dimensions,
                {
                    "icons/pals/BaseFamily.png": (1, 1),
                    "icons/pals/skin/GoodSkin.png": (1, 1),
                },
            )
            self.assertEqual(
                candidate.missing_icons,
                ("icons/pals/skin/MissingSkin.png",),
            )
            humans = json.loads(candidate.outputs["data/human_data.json"])
            self.assertEqual(humans["ReachableHuman"]["IconKey"], "Human")
            self.assertFalse(humans["ReachableHuman"]["HasIcon"])
            for prefix, count in scenario_prefix_counts.items():
                self.assertIn(prefix, candidate.source_counts)
                self.assertEqual(candidate.source_counts[prefix], count)


class SkillDomainTests(unittest.TestCase):
    @staticmethod
    def passive_row(**overrides) -> dict:
        row = {
            "Rank": 1,
            "OverrideDescMsgID": "None",
            "TargetElementType": "EPalElementType::None",
            "EffectType1": "EPalPassiveSkillEffectType::ShotAttack",
            "EffectValue1": 20.0,
            "TargetType1": "EPalPassiveSkillEffectTargetType::ToSelf",
            "EffectType2": "EPalPassiveSkillEffectType::no",
            "EffectValue2": 0.0,
            "TargetType2": "EPalPassiveSkillEffectTargetType::None",
            "EffectType3": "EPalPassiveSkillEffectType::no",
            "EffectValue3": 0.0,
            "TargetType3": "EPalPassiveSkillEffectTargetType::None",
            "EffectType4": "EPalPassiveSkillEffectType::no",
            "EffectValue4": 0.0,
            "TargetType4": "EPalPassiveSkillEffectTargetType::None",
            "InvokeActiveOtomo": False,
            "InvokeWorker": False,
            "InvokeRiding": False,
            "InvokeReserve": False,
            "InvokeInOtomo": False,
            "InvokeAlways": True,
            "InvokeInBaseCamp": False,
            "AddInvokeTriggerType_1": "EPalPassiveAddTriggerType::None",
            "AddInvokeTriggerType_2": "EPalPassiveAddTriggerType::None",
            "AddPal": False,
            "AddRarePal": False,
            "AddWorldTreePal": False,
            "AddMutationPal": False,
            "OverrideNameTextID": "None",
            "Category": "EPalPassiveCategory::SortDisplayable",
        }
        row.update(overrides)
        return row

    @staticmethod
    def text(value: str) -> dict:
        return {"TextData": {"LocalizedString": value}}

    def passive_texts(self, passive_ids: tuple[str, ...]):
        names = {
            locale: {
                f"PASSIVE_{passive_id}": self.text(f"{locale} name {passive_id}")
                for passive_id in passive_ids
            }
            for locale in LOCALES
        }
        descriptions = {locale: {} for locale in LOCALES}
        ui = {
            locale: {
                "ShotAttack": self.text(f"{locale} attack"),
                "COMMON_STATUS_RANGE_ATTACK": self.text(f"{locale} attack"),
                "COMMON_STATUS_DEFENCE": self.text(f"{locale} defense"),
                "COMMON_STATUS_SPEED": self.text(f"{locale} work speed"),
            }
            for locale in LOCALES
        }
        return names, descriptions, ui

    @staticmethod
    def evidence(
        character_id: str,
        tags: set[str],
        *,
        obtainable: bool,
        actions: set[str] | None = None,
        encounter_kind: str | None = "ordinary-placement",
    ):
        return game_data.Evidence(
            character_id=character_id,
            family_id=character_id,
            family_resolved=True,
            tribe=character_id,
            variant_tags=frozenset(tags),
            acquisition_sources=(
                (game_data.EvidenceSource("placement", character_id),)
                if obtainable
                else ()
            ),
            encounter_sources=(
                (game_data.EvidenceSource(encounter_kind, character_id),)
                if encounter_kind is not None
                else ()
            ),
            action_declarations=frozenset(actions or set()),
            regularly_obtainable=obtainable,
        )

    @staticmethod
    def waza(skill_id: str, **overrides) -> dict:
        row = {
            "WazaType": skill_id,
            "Element": "EPalElementType::Normal",
            "IgnoreRandomInherit": True,
            "Category": "EPalWazaCategory::Melee",
            "Power": 10,
            "CoolTime": 2.0,
            "EffectType1": "EPalAdditionalEffectType::None",
            "EffectValue1": 0,
            "EffectValueEx1": 0.0,
            "EffectType2": "EPalAdditionalEffectType::None",
            "EffectValue2": 0,
            "EffectValueEx2": 0.0,
            "DisabledData": False,
            "Strength": "EPalWazaStrength::None",
        }
        row.update(overrides)
        return row

    def active_texts(self, skill_ids: tuple[str, ...]):
        names = {}
        descriptions = {}
        for locale in LOCALES:
            names[locale] = {}
            descriptions[locale] = {}
            for skill_id in skill_ids:
                tail = skill_id.partition("::")[2]
                key = f"ACTION_SKILL_{tail}"
                names[locale][key] = self.text(f"{locale} name {tail}")
                descriptions[locale][key] = self.text(f"{locale} description {tail}")
        return names, descriptions

    def test_passive_eligibility_metadata_and_descriptions(self) -> None:
        included = (
            "ByAddPal",
            "ByRare",
            "ByWorldTree",
            "ByMutation",
            "DisplayableWithoutLottery",
            "Explicit",
            "Composed",
            "MiniNushi",
        )
        passives = {
            "ByAddPal": self.passive_row(AddPal=True),
            "ByRare": self.passive_row(AddRarePal=True),
            "ByWorldTree": self.passive_row(AddWorldTreePal=True),
            "ByMutation": self.passive_row(AddMutationPal=True),
            "DisplayableWithoutLottery": self.passive_row(),
            "Explicit": self.passive_row(
                AddPal=True,
                OverrideDescMsgID="EXPLICIT_DESC",
                TargetElementType="EPalElementType::Fire",
                EffectType2="EPalPassiveSkillEffectType::Defense",
                EffectValue2=-10.0,
                TargetType2="EPalPassiveSkillEffectTargetType::ToSelfAndTrainer",
                EffectType3="EPalPassiveSkillEffectType::CraftSpeed",
                EffectValue3=30.0,
                TargetType3="EPalPassiveSkillEffectTargetType::ToSelf",
                EffectType4="EPalPassiveSkillEffectType::MoveSpeed",
                EffectValue4=40.0,
                TargetType4="EPalPassiveSkillEffectTargetType::ToTrainer",
                InvokeActiveOtomo=True,
                InvokeWorker=True,
                InvokeRiding=True,
                InvokeReserve=True,
                InvokeInOtomo=True,
                InvokeAlways=False,
                InvokeInBaseCamp=True,
                AddInvokeTriggerType_1="EPalPassiveAddTriggerType::OnAttack",
                AddInvokeTriggerType_2="EPalPassiveAddTriggerType::OnDamage",
            ),
            "Composed": self.passive_row(AddPal=True),
            "MiniNushi": self.passive_row(),
            "HumanOnly": self.passive_row(
                Category="EPalPassiveCategory::SortNotDisplayable"
            ),
            "EquipmentOnly": self.passive_row(
                AddArmor=True, Category="EPalPassiveCategory::SortNotDisplayable"
            ),
            "PartnerOnly": self.passive_row(
                IsStackablePartnerSkillBySameTribe=True,
                Category="EPalPassiveCategory::SortNotDisplayable",
            ),
            "Hidden": self.passive_row(
                AddPal=True, Category="EPalPassiveCategory::SortNotDisplayable"
            ),
            "TestOnly": self.passive_row(
                Category="EPalPassiveCategory::SortNotDisplayable"
            ),
        }
        names, descriptions, ui = self.passive_texts(included)
        for locale in LOCALES:
            descriptions[locale]["EXPLICIT_DESC"] = self.text(
                "Power {EffectValue1}% <uiCommon id=|ShotAttack|/> <NumBlue_13>+</>"
            )

        rows, missing = game_data.build_passive_records(
            passives, names, descriptions, ui
        )

        self.assertEqual(set(rows), set(included))
        self.assertEqual(missing, ())
        explicit = rows["Explicit"]
        self.assertEqual(explicit["Category"], "SortDisplayable")
        self.assertEqual(explicit["TargetElementType"], "Fire")
        self.assertEqual(
            explicit["Effects"],
            [
                {
                    "EffectType": "ShotAttack",
                    "EffectValue": 20.0,
                    "TargetType": "ToSelf",
                },
                {
                    "EffectType": "Defense",
                    "EffectValue": -10.0,
                    "TargetType": "ToSelfAndTrainer",
                },
                {
                    "EffectType": "CraftSpeed",
                    "EffectValue": 30.0,
                    "TargetType": "ToSelf",
                },
                {
                    "EffectType": "MoveSpeed",
                    "EffectValue": 40.0,
                    "TargetType": "ToTrainer",
                },
            ],
        )
        self.assertEqual(
            explicit["Buff"],
            {
                "b_Attack": 0.2,
                "b_Defense": -0.1,
                "b_CraftSpeed": 0.3,
                "b_MoveSpeed": 0.0,
            },
        )
        self.assertEqual(
            explicit["Invocation"],
            {
                "ActiveOtomo": True,
                "Worker": True,
                "Riding": True,
                "Reserve": True,
                "InOtomo": True,
                "Always": False,
                "InBaseCamp": True,
            },
        )
        self.assertEqual(explicit["AddInvokeTriggerTypes"], ["OnAttack", "OnDamage"])
        self.assertEqual(
            explicit["I18n"]["en"]["Description"],
            "Power 20% en attack +",
        )
        self.assertEqual(explicit["DescriptionSource"]["en"], "explicit")
        self.assertEqual(
            rows["Composed"]["I18n"]["en"]["Description"],
            "en attack +20%",
        )
        self.assertEqual(
            rows["Composed"]["I18n"]["zh-CN"]["Description"],
            "zh-CN attack +20%",
        )
        self.assertEqual(rows["Composed"]["DescriptionSource"]["en"], "composed")

    def test_passive_projection_includes_self_max_hp_buff(self) -> None:
        passives = {
            "HealthPenalty": self.passive_row(
                AddPal=True,
                EffectType1="EPalPassiveSkillEffectType::MaxHP",
                EffectValue1=-50.0,
            )
        }
        names, descriptions, ui = self.passive_texts(("HealthPenalty",))

        rows, _missing = game_data.build_passive_records(
            passives, names, descriptions, ui
        )

        self.assertEqual(rows["HealthPenalty"]["Buff"]["b_HP"], -0.5)

    def test_active_classification_uses_evidence_not_names(self) -> None:
        ids = (
            "EPalWazaID::Ordinary",
            "EPalWazaID::BossOnly",
            "EPalWazaID::Mixed",
            "EPalWazaID::Fruit",
            "EPalWazaID::Psychokinesis",
            "EPalWazaID::Exclusive",
            "EPalWazaID::Human_Punch",
            "EPalWazaID::BlueprintOnly",
            "EPalWazaID::Disabled",
            "EPalWazaID::MissingName",
            "EPalWazaID::AlphaSkill",
            "EPalWazaID::AcquiredBoss",
        )
        waza = {skill_id: self.waza(skill_id) for skill_id in ids}
        waza["EPalWazaID::Ordinary"]["IgnoreRandomInherit"] = False
        waza["EPalWazaID::Exclusive"]["IgnoreRandomInherit"] = False
        waza["EPalWazaID::Disabled"]["DisabledData"] = True
        levels = {
            "1": {"PalId": "OrdinaryPal", "WazaID": ids[0], "Level": 1},
            "2": {"PalId": "ScenarioPal", "WazaID": ids[1], "Level": 2},
            "3": {"PalId": "ScenarioPal", "WazaID": ids[2], "Level": 3},
            "4": {"PalId": "OrdinaryPal", "WazaID": ids[2], "Level": 4},
            "5": {"PalId": "ScenarioPal", "WazaID": ids[4], "Level": 5},
            "6": {"PalId": "OrdinaryPal", "WazaID": ids[5], "Level": 6},
            "7": {"PalId": "OrdinaryPal", "WazaID": ids[8], "Level": 7},
            "8": {"PalId": "ScenarioPal", "WazaID": ids[9], "Level": 8},
            "9": {"PalId": "AlphaPal", "WazaID": ids[10], "Level": 9},
            "10": {"PalId": "AcquiredBoss", "WazaID": ids[11], "Level": 10},
            "11": {"PalId": "MissingParameterRow", "WazaID": ids[0], "Level": 11},
        }
        items = {
            "LegalFruit": {
                "TypeB": "EPalItemTypeB::ConsumeWazaMachine",
                "bLegalInGame": True,
                "WazaID": ids[3],
            },
            "IllegalFruit": {
                "TypeB": "EPalItemTypeB::ConsumeWazaMachine",
                "bLegalInGame": False,
                "WazaID": ids[4],
            },
        }
        evidence = {
            "OrdinaryPal": self.evidence("OrdinaryPal", {"base"}, obtainable=True),
            "ScenarioPal": self.evidence(
                "ScenarioPal",
                {"tower", "predator"},
                obtainable=False,
                encounter_kind="scenario-placement",
            ),
            "AlphaPal": self.evidence("AlphaPal", {"boss", "alpha"}, obtainable=True),
            "ReachableHuman": self.evidence(
                "ReachableHuman",
                {"human"},
                obtainable=True,
                actions={"EPalWazaID::Human_Punch"},
            ),
            "AcquiredBoss": self.evidence(
                "AcquiredBoss",
                {"boss"},
                obtainable=True,
                encounter_kind="scenario-cage-boss",
            ),
        }
        graph = game_data.CharacterEvidenceGraph(evidence, ())
        names, descriptions = self.active_texts(ids)
        for locale in LOCALES:
            key = "ACTION_SKILL_MissingName"
            names[locale].pop(key)

        rows, missing = game_data.build_active_records(
            waza, levels, items, names, descriptions, graph
        )

        self.assertFalse(rows[ids[0]]["BossSkill"])
        self.assertTrue(rows[ids[0]]["Assignable"])
        self.assertEqual(
            rows[ids[0]]["Learners"],
            [{"CharacterID": "OrdinaryPal", "Level": 1}],
        )
        self.assertTrue(rows[ids[1]]["BossSkill"])
        self.assertFalse(rows[ids[2]]["BossSkill"])
        self.assertTrue(rows[ids[2]]["Assignable"])
        self.assertTrue(rows[ids[3]]["SkillFruit"])
        self.assertFalse(rows[ids[4]]["SkillFruit"])
        self.assertTrue(rows[ids[5]]["Exclusive"])
        self.assertFalse(rows[ids[6]]["Invalid"])
        self.assertFalse(rows[ids[6]]["Assignable"])
        self.assertTrue(rows[ids[7]]["Invalid"])
        self.assertTrue(rows[ids[8]]["Invalid"])
        self.assertTrue(rows[ids[9]]["Invalid"])
        self.assertTrue(rows[ids[10]]["BossSkill"])
        self.assertTrue(rows[ids[11]]["BossSkill"])
        self.assertTrue(
            any("EPalWazaID::MissingName:en:Name" in item for item in missing)
        )

    def test_active_localization_keys_are_case_insensitive(self) -> None:
        skill_id = "EPalWazaID::Railbolt"
        names, descriptions = self.active_texts((skill_id,))
        for locale in LOCALES:
            names[locale]["ACTION_SKILL_RailBolt"] = names[locale].pop(
                "ACTION_SKILL_Railbolt"
            )
        graph = game_data.CharacterEvidenceGraph(
            {
                "OrdinaryPal": self.evidence(
                    "OrdinaryPal", {"base"}, obtainable=True
                )
            },
            (),
        )

        rows, missing = game_data.build_active_records(
            {skill_id: self.waza(skill_id)},
            {"1": {"PalId": "OrdinaryPal", "WazaID": skill_id, "Level": 1}},
            {},
            names,
            descriptions,
            graph,
        )

        self.assertEqual(rows[skill_id]["I18n"]["en"]["Name"], "en name Railbolt")
        self.assertFalse(rows[skill_id]["Invalid"])
        self.assertFalse(any(f"active:{skill_id}" in item for item in missing))

    def test_human_skill_assignability_uses_actions_and_human_learners(self) -> None:
        punch = "EPalWazaID::Human_Punch"
        weapon = "EPalWazaID::Weapon_Use"
        partner = "EPalWazaID::PartnerOnly"
        ids = (punch, weapon, partner)
        names, descriptions = self.active_texts(ids)
        graph = game_data.CharacterEvidenceGraph(
            {
                "ReachableHuman": self.evidence(
                    "ReachableHuman",
                    {"human"},
                    obtainable=True,
                    actions={punch},
                ),
                "HumanTemplate": self.evidence(
                    "HumanTemplate", {"human"}, obtainable=False
                ),
                "OrdinaryPal": self.evidence(
                    "OrdinaryPal",
                    {"base"},
                    obtainable=True,
                    actions={partner},
                ),
            },
            (),
        )

        rows, _ = game_data.build_active_records(
            {skill_id: self.waza(skill_id) for skill_id in ids},
            {
                "1": {"PalId": "HumanTemplate", "WazaID": weapon, "Level": 1}
            },
            {},
            names,
            descriptions,
            graph,
        )

        self.assertTrue(rows[punch]["AssignableToHumans"])
        self.assertTrue(rows[weapon]["AssignableToHumans"])
        self.assertFalse(rows[partner]["AssignableToHumans"])
        self.assertFalse(rows[punch]["Assignable"])
        self.assertFalse(rows[weapon]["Assignable"])
        self.assertFalse(rows[punch]["Invalid"])
        self.assertFalse(rows[weapon]["Invalid"])

    def test_boss_skill_uses_exact_core_flags_not_scenario_or_predator(self) -> None:
        ids = (
            "EPalWazaID::DirectBoss",
            "EPalWazaID::TowerBoss",
            "EPalWazaID::RaidBoss",
            "EPalWazaID::PredatorOnly",
            "EPalWazaID::ScenarioOnly",
            "EPalWazaID::UnresolvedOnly",
        )
        names, descriptions = self.active_texts(ids)
        graph = game_data.CharacterEvidenceGraph(
            {
                "DirectBoss": self.evidence(
                    "DirectBoss", {"boss"}, obtainable=False, encounter_kind=None
                ),
                "TowerBoss": self.evidence(
                    "TowerBoss", {"tower"}, obtainable=False, encounter_kind=None
                ),
                "RaidBoss": self.evidence(
                    "RaidBoss", {"raid"}, obtainable=False, encounter_kind=None
                ),
                "PredatorOnly": self.evidence(
                    "PredatorOnly",
                    {"predator"},
                    obtainable=False,
                    encounter_kind="scenario-placement",
                ),
                "ScenarioOnly": self.evidence(
                    "ScenarioOnly",
                    set(),
                    obtainable=False,
                    encounter_kind="scenario-arena",
                ),
            },
            (),
        )
        levels = {
            str(index): {"PalId": pal, "WazaID": skill_id, "Level": index}
            for index, (pal, skill_id) in enumerate(
                (
                    ("DirectBoss", ids[0]),
                    ("TowerBoss", ids[1]),
                    ("RaidBoss", ids[2]),
                    ("PredatorOnly", ids[3]),
                    ("ScenarioOnly", ids[4]),
                    ("BOSS_NameMustNotResolve", ids[5]),
                ),
                1,
            )
        }

        rows, _ = game_data.build_active_records(
            {skill_id: self.waza(skill_id) for skill_id in ids},
            levels,
            {},
            names,
            descriptions,
            graph,
        )

        self.assertEqual(
            [rows[skill_id]["BossSkill"] for skill_id in ids],
            [True, True, True, False, False, False],
        )

    def test_nonboss_user_or_legal_fruit_cancels_boss_skill(self) -> None:
        mixed = "EPalWazaID::MixedUsers"
        fruit = "EPalWazaID::BossFruit"
        names, descriptions = self.active_texts((mixed, fruit))
        graph = game_data.CharacterEvidenceGraph(
            {
                "Boss": self.evidence(
                    "Boss",
                    {"boss"},
                    obtainable=False,
                    encounter_kind="scenario-placement",
                ),
                "Ordinary": self.evidence(
                    "Ordinary", {"base"}, obtainable=False, encounter_kind=None
                ),
            },
            (),
        )

        rows, _ = game_data.build_active_records(
            {mixed: self.waza(mixed), fruit: self.waza(fruit)},
            {
                "1": {"PalId": "Boss", "WazaID": mixed, "Level": 1},
                "2": {"PalId": "Ordinary", "WazaID": mixed, "Level": 1},
                "3": {"PalId": "Boss", "WazaID": fruit, "Level": 1},
            },
            {
                "LegalFruit": {
                    "TypeB": "EPalItemTypeB::ConsumeWazaMachine",
                    "bLegalInGame": True,
                    "WazaID": fruit,
                }
            },
            names,
            descriptions,
            graph,
        )

        self.assertFalse(rows[mixed]["BossSkill"])
        self.assertFalse(rows[fruit]["BossSkill"])

    def test_action_only_boss_is_cancelled_by_inherited_ordinary_user(self) -> None:
        boss_only = "EPalWazaID::BossActionOnly"
        inherited = "EPalWazaID::InheritedAction"
        human = "EPalWazaID::Human_Punch"
        ids = (boss_only, inherited, human)
        names, descriptions = self.active_texts(ids)
        graph = game_data.CharacterEvidenceGraph(
            {
                "Boss": self.evidence(
                    "Boss",
                    {"boss"},
                    obtainable=False,
                    encounter_kind=None,
                    actions={boss_only, inherited},
                ),
                "Ordinary": self.evidence(
                    "Ordinary",
                    {"base"},
                    obtainable=False,
                    encounter_kind=None,
                    actions={inherited},
                ),
                "OrdinaryHuman": self.evidence(
                    "OrdinaryHuman",
                    {"human"},
                    obtainable=True,
                    actions={human},
                ),
            },
            (),
        )

        rows, _ = game_data.build_active_records(
            {skill_id: self.waza(skill_id) for skill_id in ids},
            {},
            {},
            names,
            descriptions,
            graph,
        )

        self.assertTrue(rows[boss_only]["BossSkill"])
        self.assertFalse(rows[inherited]["BossSkill"])
        self.assertFalse(rows[human]["BossSkill"])

    def test_boss_skill_requires_complete_i18n_and_master_user_to_be_editable(
        self,
    ) -> None:
        psychokinesis = "EPalWazaID::Psychokinesis"
        predator = "EPalWazaID::PredatorBeam"
        action_only = "EPalWazaID::ActionOnly"
        ids = (psychokinesis, predator, action_only)
        names, descriptions = self.active_texts(ids)
        for locale in LOCALES:
            descriptions[locale].pop("ACTION_SKILL_PredatorBeam")
            names[locale].pop("ACTION_SKILL_ActionOnly")
            descriptions[locale].pop("ACTION_SKILL_ActionOnly")
        graph = game_data.CharacterEvidenceGraph(
            {
                "Boss": self.evidence(
                    "Boss",
                    {"boss"},
                    obtainable=False,
                    encounter_kind=None,
                    actions={action_only},
                )
            },
            (),
        )

        rows, _ = game_data.build_active_records(
            {skill_id: self.waza(skill_id) for skill_id in ids},
            {
                "1": {"PalId": "Boss", "WazaID": psychokinesis, "Level": 8},
                "2": {"PalId": "Boss", "WazaID": predator, "Level": 1},
            },
            {},
            names,
            descriptions,
            graph,
        )

        self.assertEqual(
            {
                skill_id: (
                    rows[skill_id]["BossSkill"],
                    rows[skill_id]["Invalid"],
                    rows[skill_id]["Assignable"],
                )
                for skill_id in ids
            },
            {
                psychokinesis: (True, False, True),
                predator: (True, True, False),
                action_only: (True, True, False),
            },
        )

    def test_base_arena_learner_makes_mixed_boss_skill_ordinary(self) -> None:
        skill_id = "EPalWazaID::MixedBreedingBoss"
        names, descriptions = self.active_texts((skill_id,))
        graph = game_data.CharacterEvidenceGraph(
            {
                "BaseLearner": game_data.Evidence(
                    character_id="BaseLearner",
                    family_id="BaseLearner",
                    family_resolved=True,
                    tribe="BaseLearner",
                    variant_tags=frozenset({"base", "predator"}),
                    acquisition_sources=(
                        game_data.EvidenceSource("arena", "Legend_Arena"),
                    ),
                    encounter_sources=(
                        game_data.EvidenceSource("scenario-arena", "Legend_Arena"),
                    ),
                    action_declarations=frozenset(),
                    regularly_obtainable=True,
                ),
                "ScenarioBoss": game_data.Evidence(
                    character_id="ScenarioBoss",
                    family_id="BaseLearner",
                    family_resolved=True,
                    tribe="BaseLearner",
                    variant_tags=frozenset({"boss", "tower"}),
                    acquisition_sources=(),
                    encounter_sources=(
                        game_data.EvidenceSource(
                            "scenario-placement", "TowerEncounter"
                        ),
                    ),
                    action_declarations=frozenset(),
                    regularly_obtainable=False,
                ),
            },
            (),
        )

        rows, missing = game_data.build_active_records(
            {skill_id: self.waza(skill_id)},
            {
                "Base": {
                    "PalId": "BaseLearner",
                    "WazaID": skill_id,
                    "Level": 10,
                },
                "Boss": {
                    "PalId": "ScenarioBoss",
                    "WazaID": skill_id,
                    "Level": 20,
                },
            },
            {},
            names,
            descriptions,
            graph,
        )

        self.assertEqual(missing, ())
        self.assertFalse(rows[skill_id]["BossSkill"])
        self.assertTrue(rows[skill_id]["Assignable"])
        self.assertEqual(
            rows[skill_id]["Learners"],
            [
                {"CharacterID": "BaseLearner", "Level": 10},
                {"CharacterID": "ScenarioBoss", "Level": 20},
            ],
        )

    def test_capturable_scenario_learner_remains_boss_only(self) -> None:
        skill_id = "EPalWazaID::CapturableScenarioBoss"
        names, descriptions = self.active_texts((skill_id,))
        graph = game_data.CharacterEvidenceGraph(
            {
                "CapturableScenario": game_data.Evidence(
                    character_id="CapturableScenario",
                    family_id="CanonicalBase",
                    family_resolved=True,
                    tribe="CanonicalBase",
                    variant_tags=frozenset({"boss", "tower"}),
                    acquisition_sources=(
                        game_data.EvidenceSource("cage", "ScenarioCage"),
                    ),
                    encounter_sources=(
                        game_data.EvidenceSource("scenario-cage", "ScenarioCage"),
                    ),
                    action_declarations=frozenset(),
                    regularly_obtainable=True,
                ),
            },
            (),
        )

        rows, missing = game_data.build_active_records(
            {skill_id: self.waza(skill_id)},
            {
                "Boss": {
                    "PalId": "CapturableScenario",
                    "WazaID": skill_id,
                    "Level": 30,
                },
            },
            {},
            names,
            descriptions,
            graph,
        )

        self.assertEqual(missing, ())
        self.assertTrue(rows[skill_id]["BossSkill"])
        self.assertTrue(rows[skill_id]["Assignable"])
        self.assertEqual(
            rows[skill_id]["Learners"],
            [{"CharacterID": "CapturableScenario", "Level": 30}],
        )

    def test_obtainable_base_with_only_scenario_encounters_is_ordinary(
        self,
    ) -> None:
        skill_id = "EPalWazaID::BaseScenarioOnly"
        names, descriptions = self.active_texts((skill_id,))
        graph = game_data.CharacterEvidenceGraph(
            {
                "BaseScenario": game_data.Evidence(
                    character_id="BaseScenario",
                    family_id="BaseScenario",
                    family_resolved=True,
                    tribe="BaseScenario",
                    variant_tags=frozenset({"base", "predator"}),
                    acquisition_sources=(
                        game_data.EvidenceSource("arena", "ScenarioArena"),
                        game_data.EvidenceSource("unique-breeding", "BreedingRow"),
                    ),
                    encounter_sources=(
                        game_data.EvidenceSource("scenario-arena", "ScenarioArena"),
                    ),
                    action_declarations=frozenset(),
                    regularly_obtainable=True,
                ),
                "InertBoss": game_data.Evidence(
                    character_id="InertBoss",
                    family_id="BaseScenario",
                    family_resolved=True,
                    tribe="BaseScenario",
                    variant_tags=frozenset({"boss", "predator"}),
                    acquisition_sources=(),
                    encounter_sources=(),
                    action_declarations=frozenset(),
                    regularly_obtainable=False,
                ),
            },
            (),
        )

        rows, missing = game_data.build_active_records(
            {skill_id: self.waza(skill_id)},
            {
                "Base": {
                    "PalId": "BaseScenario",
                    "WazaID": skill_id,
                    "Level": 40,
                },
                "Boss": {
                    "PalId": "InertBoss",
                    "WazaID": skill_id,
                    "Level": 40,
                },
            },
            {},
            names,
            descriptions,
            graph,
        )

        self.assertEqual(missing, ())
        self.assertFalse(rows[skill_id]["BossSkill"])
        self.assertEqual(
            rows[skill_id]["Learners"],
            [
                {"CharacterID": "BaseScenario", "Level": 40},
                {"CharacterID": "InertBoss", "Level": 40},
            ],
        )

    def test_skill_classification_blocks_only_acquisition_diagnostics(self) -> None:
        skill_id = "EPalWazaID::Fixture"
        waza = {skill_id: self.waza(skill_id)}
        names, descriptions = self.active_texts((skill_id,))
        evidence = {
            "FixturePal": self.evidence("FixturePal", {"base"}, obtainable=True)
        }
        unresolved_family = game_data.CharacterEvidenceGraph(
            evidence,
            (
                game_data.EvidenceDiagnostic(
                    "unresolved_family", "RAID_Part", "MissingFamily"
                ),
            ),
        )

        rows, _ = game_data.build_active_records(
            waza,
            {"1": {"PalId": "FixturePal", "WazaID": skill_id, "Level": 1}},
            {},
            names,
            descriptions,
            unresolved_family,
        )
        self.assertFalse(rows[skill_id]["Invalid"])

        incomplete_acquisition = game_data.CharacterEvidenceGraph(
            evidence,
            (
                game_data.EvidenceDiagnostic(
                    "unsupported_spawner", "/Game/BP_HumanBoss.BP_HumanBoss_C", "1"
                ),
            ),
        )
        with self.assertRaisesRegex(ValueError, "acquisition evidence is incomplete"):
            game_data.build_active_records(
                waza,
                {
                    "1": {
                        "PalId": "FixturePal",
                        "WazaID": skill_id,
                        "Level": 1,
                    }
                },
                {},
                names,
                descriptions,
                incomplete_acquisition,
            )

    def test_skills_domain_builds_only_the_two_runtime_json_files(self) -> None:
        skill_id = "EPalWazaID::Fixture"
        passive_id = "FixturePassive"
        graph = game_data.CharacterEvidenceGraph(
            {"FixturePal": self.evidence("FixturePal", {"base"}, obtainable=True)},
            (),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_table(
                root,
                game_data.SKILL_SOURCES["waza"],
                {skill_id: self.waza(skill_id)},
            )
            write_table(
                root,
                game_data.SKILL_SOURCES["levels"],
                {
                    "1": {
                        "PalId": "FixturePal",
                        "WazaID": skill_id,
                        "Level": 1,
                    }
                },
            )
            write_table(root, game_data.SKILL_SOURCES["items"], {})
            write_table(
                root,
                game_data.SKILL_SOURCES["passives"],
                {passive_id: self.passive_row(AddPal=True)},
            )
            write_table(
                root,
                game_data.CHARACTER_EVIDENCE_SOURCES["monsters"],
                {
                    "FixturePal": {
                        "PassiveSkill1": passive_id,
                        "PassiveSkill2": "None",
                        "PassiveSkill3": "None",
                        "PassiveSkill4": "None",
                    }
                },
            )
            names, descriptions = self.active_texts((skill_id,))
            passive_names, passive_descriptions, ui = self.passive_texts((passive_id,))
            for locale in LOCALES:
                names[locale].update(passive_names[locale])
                descriptions[locale].update(passive_descriptions[locale])
                write_table(
                    root,
                    game_data.text_table_path("DT_SkillNameText_Common", locale),
                    names[locale],
                )
                write_table(
                    root,
                    game_data.text_table_path("DT_SkillDescText_Common", locale),
                    descriptions[locale],
                )
                write_table(
                    root,
                    game_data.text_table_path("DT_UI_Common_Text_Common", locale),
                    ui[locale],
                )
            scenario_prefix_counts = {
                "Pal/Content/Pal/Blueprint/Spawner/Quest": 8,
                (
                    "Pal/Content/Pal/Blueprint/Spawner/SheetsVariant/"
                    "BP_PalSpawner_Sheets_Quest_"
                ): 4,
                (
                    "Pal/Content/Pal/Maps/MainWorld_5/PL_MainWorld5/_Generated_/oilrig_"
                ): 14,
            }
            for prefix, count in scenario_prefix_counts.items():
                for index in range(count):
                    write_asset(root, f"{prefix}Fixture{index}", [{"Type": "Fixture"}])
            policy = deepcopy(FIXTURE_POLICY)
            policy["domains"]["skills"]["required_sources"].extend(
                scenario_prefix_counts
            )

            with patch.object(
                game_data, "build_character_evidence", return_value=graph
            ):
                candidate = game_data.build_domain("skills", root, policy)

        self.assertEqual(
            set(candidate.outputs),
            {"data/pal_attacks.json", "data/pal_passives.json"},
        )
        self.assertEqual(candidate.output_counts["data/pal_attacks.json"], 1)
        self.assertEqual(candidate.output_counts["data/pal_passives.json"], 1)
        for prefix, count in scenario_prefix_counts.items():
            self.assertIn(prefix, candidate.source_counts)
            self.assertEqual(candidate.source_counts[prefix], count)
        self.assertEqual(
            candidate.references,
            (
                Reference(
                    "data/pal_attacks.json",
                    skill_id,
                    "Learners.CharacterID",
                    "characters",
                    "FixturePal",
                ),
            ),
        )

class ProgressionDomainTests(unittest.TestCase):
    def test_known_build_progression_forgery_is_rejected_before_mutation(
        self,
    ) -> None:
        outputs = fixture_outputs()["progression"]
        policy = deepcopy(FIXTURE_POLICY)
        policy["domains"]["progression"]["known_build_invariants"] = {
            KNOWN_BUILD: {
                "json_outputs": {
                    path: {
                        "count": len(json.loads(data)),
                        "sha256": hashlib.sha256(data).hexdigest(),
                    }
                    for path, data in outputs.items()
                }
            }
        }

        changed = dict(outputs)
        experience = json.loads(changed["data/pal_exp_table.json"])
        experience["1"]["TotalEXP"] = -123
        changed["data/pal_exp_table.json"] = json_bytes(experience)
        forged = snapshot_from_outputs(
            "progression",
            changed,
            IDENTITY,
            domain_policy_hash(policy, "progression"),
            {source: 1 for source in REQUIRED_SOURCES["progression"]},
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "assets"
            stage = root / "stage"
            assets.mkdir()
            (assets / "marker.txt").write_bytes(b"unchanged")
            stage_candidate(stage, forged)
            before = snapshot(assets)

            errors = validate_domain(
                "progression",
                forged,
                fixture_sources(),
                Manifest(1, {}, {}),
                policy,
            )
            self.assertTrue(
                any("known-build invariant" in error for error in errors), errors
            )
            with self.assertRaisesRegex(ValueError, "known-build invariant"):
                publish_domain(
                    stage,
                    assets,
                    "progression",
                    forged,
                    Manifest(1, {}, {}),
                    policy=policy,
                    sources=fixture_sources(),
                    provenance_path=root / "provenance.json",
                )
            self.assertEqual(snapshot(assets), before)

    def test_progression_exporter_requests_only_declared_sources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            toolchain = Toolchain(
                root / "uex.exe",
                root / "Mappings.usmap",
                UEX_REVISION,
                MAPPING_SHA256,
            )
            requested = []

            def fake_export_sources(
                selected: Toolchain,
                paks_dir: Path,
                export_root: Path,
                profile_dir: Path,
                sources: set[str],
            ) -> None:
                self.assertEqual(selected, toolchain)
                requested.append(sources)

            with patch.object(
                extract_game_data,
                "export_sources",
                side_effect=fake_export_sources,
            ):
                extract_game_data.export_progression_domain(
                    toolchain,
                    root / "paks",
                    root / "export",
                    root / "profiles",
                )

        self.assertEqual(
            requested,
            [set(extract_game_data._POLICY["domains"]["progression"]["required_sources"])],
        )

    def test_progression_domain_projects_exact_source_rows(self) -> None:
        exp_source = "Pal/Content/Pal/DataTable/Exp/DT_PalExpTable"
        friendship_source = (
            "Pal/Content/Pal/DataTable/Friendship/DT_FriendshipRankTable"
        )
        exp_rows = {
            "1": {
                "BuildEXP": 17,
                "CraftEXP": 16,
                "DropEXP": 15,
                "NextEXP": 14,
                "PalBuildEXP": 13,
                "PalCraftEXP": 12,
                "PalNextEXP": 11,
                "PalTotalEXP": 10,
                "TotalEXP": 9,
            },
            "2": {
                "BuildEXP": 27,
                "CraftEXP": 26,
                "DropEXP": 25,
                "NextEXP": 24,
                "PalBuildEXP": 23,
                "PalCraftEXP": 22,
                "PalNextEXP": 21,
                "PalTotalEXP": 20,
                "TotalEXP": 19,
            },
        }
        friendship_rows = {
            "MinusOne": {"FriendshipRank": -1, "RequiredPoint": -7},
            "Zero": {"FriendshipRank": 0, "RequiredPoint": 3},
            "One": {"FriendshipRank": 1, "RequiredPoint": 29},
        }
        policy = deepcopy(FIXTURE_POLICY)
        policy["domains"]["progression"]["required_sources"] = [
            exp_source,
            friendship_source,
            game_data.PROGRESSION_SOURCES["player_status"],
            game_data.PROGRESSION_SOURCES["game_setting"],
        ]

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_table(root, exp_source, exp_rows)
            write_table(root, friendship_source, friendship_rows)
            write_player_status_sources(root)
            candidate = game_data.build_domain("progression", root, policy)

        self.assertEqual(
            json.loads(candidate.outputs["data/pal_exp_table.json"]), exp_rows
        )
        self.assertEqual(
            json.loads(candidate.outputs["data/pal_friendship.json"]),
            {
                "-1": {"required_point": -7},
                "0": {"required_point": 3},
                "1": {"required_point": 29},
            },
        )
        player_status = json.loads(
            candidate.outputs["data/player_status_data.json"]
        )
        self.assertEqual(18, len(player_status))
        self.assertEqual(51, len(player_status["最大HP"]["values"]))
        self.assertEqual(50, player_status["最大HP"]["values"][-1])
        self.assertEqual("rank", player_status["捕獲率"]["unit"])
        self.assertEqual([0, 1], player_status["捕獲率"]["values"])
        self.assertEqual(
            candidate.source_counts,
            {
                exp_source: 2,
                friendship_source: 3,
                game_data.PROGRESSION_SOURCES["player_status"]: 13,
                game_data.PROGRESSION_SOURCES["game_setting"]: 1,
            },
        )

    def test_progression_domain_rejects_non_integer_source_values(self) -> None:
        exp_source = "Pal/Content/Pal/DataTable/Exp/DT_PalExpTable"
        friendship_source = (
            "Pal/Content/Pal/DataTable/Friendship/DT_FriendshipRankTable"
        )
        exp_row = {
            field: 1
            for field in (
                "BuildEXP",
                "CraftEXP",
                "DropEXP",
                "NextEXP",
                "PalBuildEXP",
                "PalCraftEXP",
                "PalNextEXP",
                "PalTotalEXP",
                "TotalEXP",
            )
        }
        exp_row["NextEXP"] = 1.5
        policy = deepcopy(FIXTURE_POLICY)
        policy["domains"]["progression"]["required_sources"] = [
            exp_source,
            friendship_source,
            game_data.PROGRESSION_SOURCES["player_status"],
            game_data.PROGRESSION_SOURCES["game_setting"],
        ]

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_table(root, exp_source, {"1": exp_row})
            write_table(
                root,
                friendship_source,
                {"Zero": {"FriendshipRank": 0, "RequiredPoint": 0}},
            )
            write_player_status_sources(root)
            with self.assertRaisesRegex(ValueError, "NextEXP must be an integer"):
                game_data.build_domain("progression", root, policy)

    def test_progression_domain_rejects_duplicate_friendship_ranks(self) -> None:
        exp_source = "Pal/Content/Pal/DataTable/Exp/DT_PalExpTable"
        friendship_source = (
            "Pal/Content/Pal/DataTable/Friendship/DT_FriendshipRankTable"
        )
        exp_row = {
            field: 1
            for field in (
                "BuildEXP",
                "CraftEXP",
                "DropEXP",
                "NextEXP",
                "PalBuildEXP",
                "PalCraftEXP",
                "PalNextEXP",
                "PalTotalEXP",
                "TotalEXP",
            )
        }
        policy = deepcopy(FIXTURE_POLICY)
        policy["domains"]["progression"]["required_sources"] = [
            exp_source,
            friendship_source,
            game_data.PROGRESSION_SOURCES["player_status"],
            game_data.PROGRESSION_SOURCES["game_setting"],
        ]

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_table(root, exp_source, {"1": exp_row})
            write_table(
                root,
                friendship_source,
                {
                    "First": {"FriendshipRank": 0, "RequiredPoint": 0},
                    "Second": {"FriendshipRank": 0, "RequiredPoint": 1},
                },
            )
            write_player_status_sources(root)
            with self.assertRaisesRegex(ValueError, "duplicate FriendshipRank 0"):
                game_data.build_domain("progression", root, policy)


class TechnologyProjectionTests(unittest.TestCase):
    def test_technology_write_requires_reviewed_publisher(self) -> None:
        with (
            patch.object(
                extract_game_data,
                "find_game_dir",
                side_effect=AssertionError("must reject before game access"),
            ),
            self.assertRaisesRegex(
                ValueError, "technology --write requires a separately reviewed"
            ),
        ):
            extract_game_data.run_domain(domain="technology", write=True)

    def test_known_build_technology_forgery_is_rejected(self) -> None:
        outputs = fixture_outputs()["technology"]
        policy = deepcopy(FIXTURE_POLICY)
        policy["domains"]["technology"]["known_build_invariants"] = {
            KNOWN_BUILD: {
                "json_outputs": {
                    "data/tech_data.json": {
                        "count": 1,
                        "sha256": hashlib.sha256(
                            outputs["data/tech_data.json"]
                        ).hexdigest(),
                    }
                },
                "output_count": len(outputs),
                "output_root_sha256": game_data.canonical_output_root_sha256(outputs),
            }
        }

        def candidate(candidate_outputs: dict[str, bytes]):
            return snapshot_from_outputs(
                "technology",
                candidate_outputs,
                IDENTITY,
                domain_policy_hash(policy, "technology"),
                {source: 1 for source in REQUIRED_SOURCES["technology"]},
                icon_dimensions={
                    path: (2, 2)
                    for path in candidate_outputs
                    if path.endswith(".png")
                },
            )

        self.assertEqual(
            validate_domain(
                "technology",
                candidate(outputs),
                fixture_sources(),
                Manifest(1, {}, {}),
                policy,
            ),
            [],
        )
        changed = dict(outputs)
        rows = json.loads(changed["data/tech_data.json"])
        rows["TestTech"]["Cost"] += 1
        changed["data/tech_data.json"] = json_bytes(rows)
        errors = validate_domain(
            "technology",
            candidate(changed),
            fixture_sources(),
            Manifest(1, {}, {}),
            policy,
        )

        self.assertTrue(any("known-build invariant" in error for error in errors), errors)

    @staticmethod
    def _text(value: str) -> dict:
        return {
            "TextData": {
                "Namespace": "fixture",
                "Key": "fixture",
                "SourceString": value,
                "LocalizedString": value,
            }
        }

    def _fixture(self) -> tuple[dict, dict, dict]:
        technology = {
            "BuildTech": {
                "UnlockBuildObjects": ["Workbench"],
                "UnlockItemRecipes": [],
                "Name": "BUILD_NAME",
                "Description": "BUILDOBJECT_DESC_Workbench",
                "IconName": "StaleTechnologyIcon",
                "RequireDefeatTowerBoss": "EPalBossType::DesertBoss",
                "RequireTechnology": "OldBuildTech",
                "RequireResearchId": "Building5",
                "IsBossTechnology": True,
                "LevelCap": 12,
                "Tier": 2,
                "Cost": 3,
            },
            "ItemTech": {
                "UnlockBuildObjects": [],
                "UnlockItemRecipes": ["TestItem", "StaleSecondaryItem"],
                "Name": "ITEM_NAME",
                "Description": "ITEM_DESC_TestItem",
                "IconName": "testicon",
                "RequireDefeatTowerBoss": "EPalBossType::None",
                "RequireTechnology": "None",
                "RequireResearchId": "None",
                "IsBossTechnology": False,
                "LevelCap": 3,
                "Tier": 0,
                "Cost": 1,
            },
            "PalTech": {
                "UnlockBuildObjects": [],
                "UnlockItemRecipes": ["PalGear"],
                "Name": "PAL_NAME",
                "Description": "PAL_DESC",
                "IconName": "thunderdog_ice",
                "RequireDefeatTowerBoss": "EPalBossType::None",
                "RequireTechnology": "None",
                "RequireResearchId": "None",
                "IsBossTechnology": False,
                "LevelCap": 8,
                "Tier": 1,
                "Cost": 2,
            },
        }
        tables = {
            "technology": technology,
            "items": {
                "TestItem": {
                    "IconName": "TestIcon",
                    "TypeB": "EPalItemTypeB::Weapon",
                    "bLegalInGame": True,
                },
                "PalGear": {
                    "IconName": "SkillUnlock_Saddle",
                    "TypeB": "EPalItemTypeB::Essential_PalGear",
                    "bLegalInGame": True,
                },
            },
            "pal_icons": {
                "ThunderDog_Ice": {
                    "Icon": {
                        "AssetPathName": "/Game/Pal/Texture/ThunderDog_Ice.ThunderDog_Ice",
                        "SubPathString": "",
                    }
                }
            },
            "characters": {"ThunderDog_Ice": {}},
            "item_icons": {
                "TestIcon": {
                    "Icon": {
                        "AssetPathName": "/Game/Pal/Texture/TestItem.TestItem",
                        "SubPathString": "",
                    }
                }
            },
            "build_icons": {
                "Workbench": {
                    "SoftIcon": {
                        "AssetPathName": "/Game/Pal/Texture/Workbench.Workbench",
                        "SubPathString": "",
                    }
                }
            },
        }
        localized = {
            "names": {
                "BUILD_NAME": self._text("<mapObjectName id=|Workbench|/>"),
                "ITEM_NAME": self._text("<itemName id=|TestItem|/>"),
                "PAL_NAME": self._text("Pal saddle"),
            },
            "descriptions": {"PAL_DESC": self._text("Use with a Pal")},
            "item_descriptions": {
                "ITEM_DESC_TestItem": self._text("Craft <itemName id=|TestItem|/>")
            },
            "building_descriptions": {
                "BUILDOBJECT_DESC_Workbench": self._text(
                    "Build <mapObjectName id=|Workbench|/>"
                )
            },
            "items": {"ITEM_NAME_TestItem": self._text("Fixture item")},
            "buildings": {"MAPOBJECT_NAME_Workbench": self._text("Fixture bench")},
            "pals": {
                "PAL_NAME_ThunderDog_Ice": self._text("Rayhound Cryst")
            },
            "ui": {
                "COMMON_ELEMENT_NAME_Ice": self._text("Ice"),
                "TECHNOLOGY_CATEGOFY_BUILDING": self._text("Fixture structures"),
                "TECHNOLOGY_CATEGOFY_ITEM": self._text("Fixture items"),
            },
        }
        texts = {
            name: {locale: deepcopy(rows) for locale in game_data.LOCALE_DIRECTORIES}
            for name, rows in localized.items()
        }
        return tables, texts, {"ThunderDog_Ice": "ThunderDog_Ice"}

    def test_exact_casefold_fallback_and_pal_icon_joins(self) -> None:
        tables, texts, character_icons = self._fixture()
        texts["ui"]["de"]["TECHNOLOGY_CATEGOFY_BUILDING"] = self._text(
            "Fixture Bauwerke"
        )
        texts["ui"]["de"]["TECHNOLOGY_CATEGOFY_ITEM"] = self._text(
            "Fixture Gegenstaende"
        )

        built = game_data.build_technology_records(tables, texts, character_icons)

        self.assertEqual(
            built["records"]["BuildTech"]["I18n"]["en"]["Name"],
            "Fixture bench",
        )
        self.assertEqual(
            built["records"]["ItemTech"]["I18n"]["en"]["Description"],
            "Craft Fixture item",
        )
        self.assertEqual(
            built["records"]["BuildTech"]["I18n"]["en"]["Description"],
            "Build Fixture bench",
        )
        self.assertEqual(
            built["records"]["BuildTech"]["I18n"]["en"]["Type"],
            "Fixture structures",
        )
        self.assertEqual(
            built["records"]["ItemTech"]["I18n"]["en"]["Type"],
            "Fixture items",
        )
        self.assertEqual(
            built["records"]["BuildTech"]["I18n"]["de"]["Type"],
            "Fixture Bauwerke",
        )
        self.assertEqual(
            built["records"]["ItemTech"]["I18n"]["de"]["Type"],
            "Fixture Gegenstaende",
        )
        self.assertEqual(
            built["records"]["ItemTech"]["UnlockItems"],
            ["TestItem", "StaleSecondaryItem"],
        )
        self.assertEqual(
            built["diagnostics"],
            (
                {
                    "Kind": "unresolved-item",
                    "TechnologyID": "ItemTech",
                    "Field": "UnlockItems",
                    "TargetID": "StaleSecondaryItem",
                },
            ),
        )
        self.assertEqual(built["records"]["ItemTech"]["IconKind"], "item")
        self.assertEqual(
            built["icon_sources"]["icons/tech/ItemTech.png"],
            "Pal/Content/Pal/Texture/TestItem",
        )
        self.assertEqual(built["records"]["BuildTech"]["IconKind"], "building")
        self.assertEqual(
            built["icon_sources"]["icons/tech/BuildTech.png"],
            "Pal/Content/Pal/Texture/Workbench",
        )
        self.assertEqual(
            built["records"]["BuildTech"]["Requirements"],
            {"DefeatTowerBoss": "DesertBoss", "ResearchID": "Building5"},
        )
        self.assertEqual(
            built["records"]["BuildTech"]["Prerequisites"], ["OldBuildTech"]
        )
        pal = built["records"]["PalTech"]
        self.assertEqual(pal["UnlockPalSkill"], "ThunderDog_Ice")
        self.assertEqual(pal["IconKind"], "pal")
        self.assertEqual(pal["IconKey"], "ThunderDog_Ice")
        self.assertNotIn("icons/tech/PalTech.png", built["icon_sources"])

    def test_character_ui_and_image_markup_is_resolved(self) -> None:
        tables, texts, character_icons = self._fixture()
        texts["descriptions"]["en"]["PAL_DESC"] = self._text(
            "Use <characterName id=|thunderdog_ice|/> "
            "with <img id=|ElemIcon_Ice|/><uiCommon "
            "id=|common_element_name_ice| style=|Elem_Ice|/>"
        )

        built = game_data.build_technology_records(tables, texts, character_icons)

        self.assertEqual(
            built["records"]["PalTech"]["I18n"]["en"]["Description"],
            "Use Rayhound Cryst with Ice",
        )
        self.assertNotRegex(
            built["records"]["PalTech"]["I18n"]["en"]["Description"],
            r"<(?:characterName|uiCommon|img)\b",
        )

    def test_illegal_pal_gear_is_rejected(self) -> None:
        tables, texts, character_icons = self._fixture()
        tables["items"]["PalGear"]["bLegalInGame"] = False

        with self.assertRaisesRegex(ValueError, "PalTech.*bLegalInGame"):
            game_data.build_technology_records(tables, texts, character_icons)

    def test_technology_candidate_snapshot_does_not_require_character_metrics(self) -> None:
        snapshot = game_data._candidate_snapshot(fixture_candidate("technology"))

        self.assertEqual(snapshot["domain"], "technology")
        self.assertEqual(snapshot["metrics"], {})


if __name__ == "__main__":
    unittest.main()
