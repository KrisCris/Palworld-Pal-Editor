"""Exact-path loaders shared by the local game-data pipeline."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import struct
import subprocess
import tarfile
import tempfile
import zlib
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

LOCALE_DIRECTORIES = {
    "ja": None,
    "de": "de",
    "en": "en",
    "es": "es",
    "es-MX": "es-MX",
    "fr": "fr",
    "id": "id",
    "it": "it",
    "ko": "ko",
    "pl": "pl",
    "pt-BR": "pt-BR",
    "ru": "ru",
    "th": "th",
    "tr": "tr",
    "vi": "vi",
    "zh-CN": "zh-Hans",
    "zh-TW": "zh-Hant",
}
DOMAIN_NAMES = ("skills", "characters", "progression", "technology")
PROVENANCE_PATH = Path(__file__).with_name("provenance.json")

_CHARACTER_OUTPUT_FIELDS = frozenset(
    {
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
)
_SKIN_OUTPUT_FIELDS = frozenset(
    {
        "SkinName",
        "SkinType",
        "SkinStaticClass",
        "bIsHairAccessory",
        "TargetActorClassName",
        "TargetPalName",
        "bAutoGetItem",
        "PlatformItemID_Steam",
        "InternalName",
        "I18n",
        "IconKey",
        "Invalid",
    }
)

_ENTITY_SCHEMAS = {
    "data/pal_data.json": _CHARACTER_OUTPUT_FIELDS,
    "data/human_data.json": _CHARACTER_OUTPUT_FIELDS | {"Human", "HasIcon"},
    "data/skin_data.json": _SKIN_OUTPUT_FIELDS,
    "data/pal_attacks.json": frozenset(
        {
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
    ),
    "data/pal_passives.json": frozenset(
        {
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
    ),
    "data/tech_data.json": frozenset(
        {
            "InternalName",
            "Level",
            "Tier",
            "Cost",
            "BossTechnology",
            "Requirements",
            "Prerequisites",
            "UnlockItems",
            "UnlockBuildObjects",
            "UnlockPalSkill",
            "IconKey",
            "IconKind",
            "I18n",
        }
    ),
}
_PAL_EXP_FIELDS = (
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
_PROGRESSION_SCHEMAS = {
    "data/pal_exp_table.json": frozenset(_PAL_EXP_FIELDS),
    "data/pal_friendship.json": frozenset({"required_point"}),
    "data/player_status_data.json": frozenset(
        {"category", "icon", "maximum", "source", "unit", "values"}
    ),
}
_OUTPUT_KINDS = {
    "data/pal_data.json": "characters",
    "data/human_data.json": "characters",
    "data/skin_data.json": "skins",
    "data/pal_attacks.json": "skills",
    "data/pal_passives.json": "passives",
    "data/tech_data.json": "technology",
}
_REQUIRED_OUTPUTS = {
    "skills": frozenset({"data/pal_attacks.json", "data/pal_passives.json"}),
    "characters": frozenset(
        {"data/pal_data.json", "data/human_data.json", "data/skin_data.json"}
    ),
    "progression": frozenset(
        {
            "data/pal_exp_table.json",
            "data/pal_friendship.json",
            "data/player_status_data.json",
        }
    ),
    "technology": frozenset({"data/tech_data.json"}),
}
_STATIC_PAL_ICONS = frozenset({"icons/pals/Human.png", "icons/pals/unknown.png"})
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_PASSIVE_BUFF_FIELDS = frozenset(
    {"b_Attack", "b_Defense", "b_CraftSpeed", "b_MoveSpeed"}
)
_PASSIVE_INVOCATION_FIELDS = frozenset(
    {"ActiveOtomo", "Worker", "Riding", "Reserve", "InOtomo", "Always", "InBaseCamp"}
)
CHARACTER_EVIDENCE_SOURCES = {
    "monsters": "Pal/Content/Pal/DataTable/Character/DT_PalMonsterParameter_Common",
    "humans": "Pal/Content/Pal/DataTable/Character/DT_PalHumanParameter_Common",
    "placements": "Pal/Content/Pal/DataTable/Spawner/DT_PalSpawnerPlacement",
    "human_actions": (
        "Pal/Content/Pal/Blueprint/Character/NPC/BP_NPC_StandardHumanDataSet"
    ),
}
CHARACTER_SCENARIO_SOURCES = {
    "quest_spawners": "Pal/Content/Pal/Blueprint/Spawner/Quest",
    "quest_sheet_spawners": (
        "Pal/Content/Pal/Blueprint/Spawner/SheetsVariant/BP_PalSpawner_Sheets_Quest_"
    ),
    "oilrig_maps": (
        "Pal/Content/Pal/Maps/MainWorld_5/PL_MainWorld5/_Generated_/oilrig_"
    ),
    "grass_boss_reward": (
        "Pal/Content/Pal/Blueprint/FlowGraph/NPCTalkFlow/Graph/FABP_GrassBoss01"
    ),
    "kingwhale_controller": (
        "Pal/Content/Pal/Blueprint/Controller/Monster/"
        "BP_MonsterAIController_Wild_KingWhale"
    ),
    "kingwhale_combat": (
        "Pal/Content/Pal/Blueprint/Controller/Monster/BP_AICombatModule_KingWhale_Wild"
    ),
}
CHARACTER_SCENARIO_PREFIX_SOURCES = frozenset(
    CHARACTER_SCENARIO_SOURCES[name]
    for name in ("quest_spawners", "quest_sheet_spawners", "oilrig_maps")
)
CHARACTER_SCENARIO_FILENAME_PREFIX_SOURCES = frozenset(
    CHARACTER_SCENARIO_SOURCES[name] for name in ("quest_sheet_spawners", "oilrig_maps")
)
OILRIG_NPC_SPAWNER_TYPES = frozenset(
    {"BP_OilrigNPCSpawner_Mono_C", "BP_OilrigNPCSpawner_Infinite_C"}
)
CHARACTER_ROUTE_SOURCES = {
    "wild": "Pal/Content/Pal/DataTable/Spawner/DT_PalWildSpawner",
    "dungeon": "Pal/Content/Pal/DataTable/Dungeon/DT_DungeonEnemySpawnDataTable",
    "cage": "Pal/Content/Pal/DataTable/Character/DT_CapturedCagePal",
    "fishing_spot": (
        "Pal/Content/Pal/DataTable/Fishing/DT_PalFishingSpotPalSpawnerDataTable"
    ),
    "fish_pond": ("Pal/Content/Pal/DataTable/Fishing/DT_PalFishPondLotteryDataTable"),
    "shop": "Pal/Content/Pal/DataTable/PalShop/DT_PalShopCreateData",
    "invader": "Pal/Content/Pal/DataTable/Invader/DT_PalInvader",
    "visitor": "Pal/Content/Pal/DataTable/Invader/DT_PalVisitorNPC",
    "arena": "Pal/Content/Pal/DataTable/Arena/DT_ArenaSoloNPCTable",
    "raid_boss": "Pal/Content/Pal/Blueprint/RaidBoss/DT_PalRaidBoss_Common",
    "unique_npc": "Pal/Content/Pal/DataTable/Character/DT_UniqueNPC_Common",
    "breeding": "Pal/Content/Pal/DataTable/Character/DT_PalCombiUnique",
    "incident_settings": (
        "Pal/Content/Pal/DataTable/Incident/DT_RandomIncidentSettings"
    ),
    "incident_world": "Pal/Content/Pal/Maps/MainWorld_5/PL_MainWorld5",
}
RAID_REACHABILITY_SOURCES = {
    "recipes": "Pal/Content/Pal/DataTable/Item/DT_ItemRecipeDataTable_Common",
    "item_lottery": "Pal/Content/Pal/DataTable/Item/DT_ItemLotteryDataTable",
    "dungeon_items": (
        "Pal/Content/Pal/DataTable/Dungeon/DT_DungeonItemLotteryDataTable"
    ),
}
SUPPORTED_CHARACTER_ROUTES = frozenset(
    {
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
    }
)
SKILL_SOURCES = {
    "waza": "Pal/Content/Pal/DataTable/Waza/DT_WazaDataTable_Common",
    "levels": "Pal/Content/Pal/DataTable/Waza/DT_WazaMasterLevel_Common",
    "items": "Pal/Content/Pal/DataTable/Item/DT_ItemDataTable_Common",
    "passives": "Pal/Content/Pal/DataTable/PassiveSkill/DT_PassiveSkill_Main_Common",
    "bp_classes": "Pal/Content/Pal/DataTable/Character/DT_PalBPClass_Common",
}
PROGRESSION_SOURCES = {
    "experience": "Pal/Content/Pal/DataTable/Exp/DT_PalExpTable",
    "friendship": (
        "Pal/Content/Pal/DataTable/Friendship/DT_FriendshipRankTable"
    ),
    "player_status": (
        "Pal/Content/Pal/DataTable/Player/DT_PlayerStatusRankMasterDataTable"
    ),
    "game_setting": "Pal/Content/Pal/Blueprint/System/BP_PalGameSetting",
}
TECHNOLOGY_SOURCES = {
    "technology": (
        "Pal/Content/Pal/DataTable/Technology/DT_TechnologyRecipeUnlock_Common"
    ),
    "items": "Pal/Content/Pal/DataTable/Item/DT_ItemDataTable_Common",
    "pal_icons": (
        "Pal/Content/Pal/DataTable/Character/DT_PalCharacterIconDataTable_Common"
    ),
    "characters": (
        "Pal/Content/Pal/DataTable/Character/DT_PalMonsterParameter_Common"
    ),
    "item_icons": "Pal/Content/Pal/DataTable/Item/DT_ItemIconDataTable_Common",
    "build_icons": (
        "Pal/Content/Pal/DataTable/MapObject/Building/"
        "DT_BuildObjectIconDataTable_Common"
    ),
}
TECHNOLOGY_TEXT_TABLES = {
    "names": "DT_TechnologyNameText_Common",
    "descriptions": "DT_TechnologyDescText_Common",
    "item_descriptions": "DT_ItemDescriptionText_Common",
    "building_descriptions": "DT_BuildObjectDescText_Common",
    "items": "DT_ItemNameText_Common",
    "buildings": "DT_MapObjectNameText_Common",
    "pals": "DT_PalNameText_Common",
    "ui": "DT_UI_Common_Text_Common",
}
CHARACTER_SOURCES = {
    "icons": (
        "Pal/Content/Pal/DataTable/Character/DT_PalCharacterIconDataTable_Common"
    ),
    "skin_icons": (
        "Pal/Content/Pal/DataTable/Character/"
        "DT_PalCharacterIconDataTable_SkinOverride_Common"
    ),
    "skins": "Pal/Content/Pal/DataTable/Skin/DT_SkinDataTable_Common",
}
CHARACTER_TEXT_TABLES = {
    "pal": "DT_PalNameText_Common",
    "human": "DT_HumanNameText_Common",
    "unique": "DT_UniqueNPCText_Common",
    "prefix": "DT_NamePrefixText_Common",
    "ui": "DT_UI_Common_Text_Common",
}
CHARACTER_STATS = {
    "HP": "Hp",
    "ATK": "ShotAttack",
    "DEF": "Defense",
    "MELEE": "MeleeAttack",
    "CRAFTSPEED": "CraftSpeed",
    "FOOD": "MaxFullStomach",
}
WORK_SUITABILITIES = (
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
CHARACTER_PARAMETER_FIELDS = (
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
    *(f"WorkSuitability_{name}" for name in WORK_SUITABILITIES),
)
SKIN_SOURCE_FIELDS = (
    "SkinName",
    "SkinType",
    "SkinStaticClass",
    "bIsHairAccessory",
    "TargetActorClassName",
    "TargetPalName",
    "bAutoGetItem",
    "PlatformItemID_Steam",
)
# Cooked spawner defaults use these FNames for an intentionally empty slot.
_EMPTY_CHARACTER_FNAME_KEYS = frozenset({"none", "rowname"})


@dataclass(frozen=True)
class BuildIdentity:
    game_build: str
    parser_revision: str
    mapping_sha256: str


@dataclass(frozen=True)
class Reference:
    source_path: str
    source_id: str
    field: str
    target_kind: str
    target_id: str


@dataclass(frozen=True)
class DomainSnapshot:
    domain: str
    outputs: dict[str, bytes]
    identity: BuildIdentity
    policy_sha256: str
    source_counts: dict[str, int]
    output_counts: dict[str, int]
    references: tuple[Reference, ...]
    ids: dict[str, frozenset[str]]
    missing_references: tuple[str, ...]
    missing_localizations: tuple[str, ...]
    missing_icons: tuple[str, ...]
    hashes: dict[str, str]
    icon_dimensions: dict[str, tuple[int, int]]
    diagnostics: tuple[dict[str, str], ...] = ()


@dataclass(frozen=True)
class SourceInventory:
    present_sources: frozenset[str]
    reference_ids: dict[str, frozenset[str]]
    available_icons: frozenset[str]
    approved_static_icons: frozenset[str]


@dataclass(frozen=True)
class DomainManifest:
    game_build: str
    parser_revision: str
    mapping_sha256: str
    policy_sha256: str
    source_counts: dict[str, int]
    output_counts: dict[str, int]
    output_hashes: dict[str, str]
    missing_references: tuple[str, ...]
    missing_localizations: tuple[str, ...]
    missing_icons: tuple[str, ...]
    managed_paths: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "game_build": self.game_build,
            "parser_revision": self.parser_revision,
            "mapping_sha256": self.mapping_sha256,
            "policy_sha256": self.policy_sha256,
            "source_counts": dict(sorted(self.source_counts.items())),
            "output_counts": dict(sorted(self.output_counts.items())),
            "output_hashes": dict(sorted(self.output_hashes.items())),
            "missing_references": list(self.missing_references),
            "missing_localizations": list(self.missing_localizations),
            "missing_icons": list(self.missing_icons),
            "managed_paths": list(self.managed_paths),
        }


@dataclass(frozen=True)
class Manifest:
    schema_version: int
    bootstrap: dict
    domains: dict[str, DomainManifest]

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "bootstrap": deepcopy_json(self.bootstrap),
            "domains": {
                domain: entry.to_dict()
                for domain, entry in sorted(self.domains.items())
            },
        }


@dataclass(frozen=True)
class CheckResult:
    candidates: dict[str, DomainSnapshot]
    manifest: Manifest
    errors: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceSource:
    kind: str
    source_id: str


@dataclass(frozen=True)
class Evidence:
    character_id: str
    family_id: str
    family_resolved: bool
    tribe: str
    variant_tags: frozenset[str]
    acquisition_sources: tuple[EvidenceSource, ...]
    encounter_sources: tuple[EvidenceSource, ...]
    action_declarations: frozenset[str]
    regularly_obtainable: bool


@dataclass(frozen=True)
class EvidenceDiagnostic:
    kind: str
    source_id: str
    detail: str


@dataclass(frozen=True)
class CharacterEvidenceGraph(Mapping[str, Evidence]):
    evidence: dict[str, Evidence]
    diagnostics: tuple[EvidenceDiagnostic, ...]
    consumed_asset_sources: tuple[str, ...] = ()

    def __getitem__(self, key: str) -> Evidence:
        return self.evidence[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.evidence)

    def __len__(self) -> int:
        return len(self.evidence)

    @property
    def complete(self) -> bool:
        return not self.diagnostics


def manifest_bytes(manifest: Manifest) -> bytes:
    return (
        json.dumps(
            manifest.to_dict(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def manifest_from_dict(document: dict) -> Manifest:
    if not isinstance(document, dict) or set(document) != {
        "schema_version",
        "bootstrap",
        "domains",
    }:
        raise ValueError(
            "Provenance must contain schema_version, bootstrap, and domains"
        )
    if document["schema_version"] != 1 or not isinstance(document["bootstrap"], dict):
        raise ValueError("Provenance schema version/bootstrap is invalid")
    if not isinstance(document["domains"], dict):
        raise TypeError("Provenance domains must be an object")
    fields = {
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
    }
    domains = {}
    for domain, raw in document["domains"].items():
        if (
            domain not in DOMAIN_NAMES
            or not isinstance(raw, dict)
            or set(raw) != fields
        ):
            raise ValueError(f"Invalid provenance entry for domain {domain}")
        if any(
            not isinstance(raw[field], str)
            for field in (
                "game_build",
                "parser_revision",
                "mapping_sha256",
                "policy_sha256",
            )
        ):
            raise ValueError(f"Invalid provenance identity for domain {domain}")
        for field in ("source_counts", "output_counts"):
            if not isinstance(raw[field], dict) or any(
                not isinstance(key, str)
                or not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
                for key, value in raw[field].items()
            ):
                raise ValueError(f"Invalid provenance {field} for domain {domain}")
        if not isinstance(raw["output_hashes"], dict) or any(
            not isinstance(path, str) or not isinstance(value, str)
            for path, value in raw["output_hashes"].items()
        ):
            raise ValueError(f"Invalid provenance output_hashes for domain {domain}")
        for field in (
            "missing_references",
            "missing_localizations",
            "missing_icons",
            "managed_paths",
        ):
            if not isinstance(raw[field], list) or any(
                not isinstance(value, str) for value in raw[field]
            ):
                raise ValueError(f"Invalid provenance {field} for domain {domain}")
        domains[domain] = DomainManifest(
            game_build=raw["game_build"],
            parser_revision=raw["parser_revision"],
            mapping_sha256=raw["mapping_sha256"],
            policy_sha256=raw["policy_sha256"],
            source_counts=dict(raw["source_counts"]),
            output_counts=dict(raw["output_counts"]),
            output_hashes=dict(raw["output_hashes"]),
            missing_references=tuple(raw["missing_references"]),
            missing_localizations=tuple(raw["missing_localizations"]),
            missing_icons=tuple(raw["missing_icons"]),
            managed_paths=tuple(raw["managed_paths"]),
        )
    return Manifest(1, deepcopy_json(document["bootstrap"]), domains)


DomainBuilder = Callable[[Path, dict], DomainSnapshot]
DOMAIN_BUILDERS: dict[str, DomainBuilder] = {}


def deepcopy_json(value):
    return json.loads(json.dumps(value))


def _export_path(export_root: Path, virtual_asset_path: str) -> Path:
    relative = PurePosixPath(virtual_asset_path)
    if (
        not virtual_asset_path
        or "\\" in virtual_asset_path
        or virtual_asset_path != relative.as_posix()
        or relative.is_absolute()
        or relative.parts[:2] != ("Pal", "Content")
        or any(part in ("", ".", "..") or ":" in part for part in relative.parts)
        or relative.suffix
    ):
        raise ValueError(
            "virtual_asset_path must be a canonical full extensionless Pal/Content path: "
            f"{virtual_asset_path!r}"
        )
    return Path(export_root).joinpath(*relative.parts).with_suffix(".json")


def _load_uex_table(path: Path) -> dict[str, dict]:
    document = json.loads(path.read_text(encoding="utf-8"))
    tables = (
        [
            item
            for item in document
            if isinstance(item, dict) and item.get("Type") == "DataTable"
        ]
        if isinstance(document, list)
        else []
    )
    if len(tables) != 1 or not isinstance(tables[0].get("Rows"), dict):
        raise ValueError(f"Expected exactly one DataTable with Rows in {path}")
    rows = tables[0]["Rows"]
    if any(
        not isinstance(key, str) or not isinstance(row, dict)
        for key, row in rows.items()
    ):
        raise ValueError(f"Expected DataTable rows to be named objects in {path}")
    return rows


def load_table(export_root: Path, virtual_asset_path: str) -> dict[str, dict]:
    """Load one UEX DataTable by its full extensionless virtual asset path."""
    path = _export_path(export_root, virtual_asset_path)
    if not path.is_file():
        raise FileNotFoundError(f"Missing exported table: {path}")
    return _load_uex_table(path)


def load_text_table(
    export_root: Path, table_name: str, output_locale: str
) -> dict[str, dict]:
    """Load a text table from the Japanese base path or exact L10N directory."""
    if not table_name or Path(table_name).name != table_name or "." in table_name:
        raise ValueError(
            f"table_name must be an extensionless basename: {table_name!r}"
        )
    try:
        source_locale = LOCALE_DIRECTORIES[output_locale]
    except KeyError as error:
        raise ValueError(f"Unsupported output locale: {output_locale}") from error
    prefix = (
        "Pal/Content/Pal/DataTable/Text"
        if source_locale is None
        else f"Pal/Content/L10N/{source_locale}/Pal/DataTable/Text"
    )
    return load_table(export_root, f"{prefix}/{table_name}")


def text_table_path(table_name: str, output_locale: str) -> str:
    """Return the canonical virtual path used by ``load_text_table``."""
    if not table_name or Path(table_name).name != table_name or "." in table_name:
        raise ValueError(
            f"table_name must be an extensionless basename: {table_name!r}"
        )
    try:
        source_locale = LOCALE_DIRECTORIES[output_locale]
    except KeyError as error:
        raise ValueError(f"Unsupported output locale: {output_locale}") from error
    prefix = (
        "Pal/Content/Pal/DataTable/Text"
        if source_locale is None
        else f"Pal/Content/L10N/{source_locale}/Pal/DataTable/Text"
    )
    return f"{prefix}/{table_name}"


def load_asset(export_root: Path, virtual_asset_path: str) -> list[dict]:
    """Load one non-DataTable UEX JSON export by exact virtual asset path."""
    path = _export_path(export_root, virtual_asset_path)
    if not path.is_file():
        raise FileNotFoundError(f"Missing exported asset: {path}")
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, list) or any(
        not isinstance(item, dict) for item in document
    ):
        raise ValueError(f"Expected a list of named UEX exports in {path}")
    return document


def load_asset_collection(
    export_root: Path, virtual_path_prefix: str
) -> tuple[tuple[str, list[dict]], ...]:
    """Load every exported asset below a directory or filename prefix."""
    exact = _export_path(export_root, virtual_path_prefix)
    if exact.is_file():
        return ((virtual_path_prefix, load_asset(export_root, virtual_path_prefix)),)

    relative = PurePosixPath(virtual_path_prefix)
    base = Path(export_root).joinpath(*relative.parts)
    if base.is_dir():
        paths = sorted(
            base.rglob("*.json"), key=lambda path: path.as_posix().casefold()
        )
    else:
        parent = base.parent
        paths = (
            sorted(
                (path for path in parent.glob(f"{base.name}*.json") if path.is_file()),
                key=lambda path: path.as_posix().casefold(),
            )
            if parent.is_dir()
            else []
        )
    if not paths:
        raise FileNotFoundError(
            f"Missing exported asset collection: {virtual_path_prefix}"
        )

    loaded = []
    for path in paths:
        virtual_path = PurePosixPath(
            *path.relative_to(export_root).with_suffix("").parts
        ).as_posix()
        loaded.append((virtual_path, load_asset(export_root, virtual_path)))
    return tuple(loaded)


def _enum_tail(value, field: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a serialized enum string")
    _, separator, tail = value.rpartition("::")
    if not separator or not tail:
        raise ValueError(f"{field} must contain a nonempty enum tail: {value!r}")
    return tail


def _fname_key(value, field: str) -> str:
    if (
        not isinstance(value, dict)
        or not isinstance(value.get("Key"), str)
        or not value["Key"]
    ):
        raise TypeError(f"{field} must be a serialized FName object with Key")
    return value["Key"]


def _asset_path_name(value, field: str) -> str:
    if (
        not isinstance(value, dict)
        or not isinstance(value.get("AssetPathName"), str)
        or not value["AssetPathName"]
    ):
        raise TypeError(f"{field} must contain AssetPathName")
    return value["AssetPathName"]


def _virtual_asset_path(object_path: str) -> str:
    package, separator, object_name = object_path.partition(".")
    if (
        not separator
        or not package.startswith("/Game/")
        or not object_name
        or "." in object_name
    ):
        raise ValueError(f"Unsupported game object path: {object_path!r}")
    return f"Pal/Content/{package.removeprefix('/Game/')}"


def _select_spawner_default_object(
    exports: list[dict], object_path: str, field: str
) -> dict:
    object_name = object_path.partition(".")[2]
    expected_name = f"Default__{object_name}"
    holders = [
        item
        for item in exports
        if item.get("Type") == object_name and item.get("Name") == expected_name
    ]
    if len(holders) != 1:
        raise ValueError(
            f"{field} expected exactly one default object {expected_name!r} "
            f"of type {object_name!r}, got {len(holders)}"
        )
    properties = holders[0].get("Properties")
    if not isinstance(properties, dict):
        raise TypeError(f"{field} default object Properties must be an object")
    return properties


def _select_human_action_component(exports: list[dict]) -> dict:
    holders = [
        item
        for item in exports
        if item.get("Type") == "PalStaticCharacterParameterComponent"
        and item.get("Name") == "StaticCharacterParameterComponent"
    ]
    if len(holders) != 1:
        raise ValueError(
            "human action asset expected exactly one "
            "PalStaticCharacterParameterComponent/StaticCharacterParameterComponent "
            f"component, got {len(holders)}"
        )
    properties = holders[0].get("Properties")
    if not isinstance(properties, dict):
        raise TypeError("human action component Properties must be an object")
    return properties


def _strict_bool(row: dict, field: str, character_id: str) -> bool:
    value = row.get(field)
    if type(value) is not bool:
        raise TypeError(f"{character_id}.{field} must be a bool")
    return value


def _positive_number(value, field: str) -> bool:
    if not _is_number(value):
        raise TypeError(f"{field} must be numeric")
    return value > 0


def _plain_name(value, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise TypeError(f"{field} must be a nonempty string")
    return value


def _object_path(value, field: str) -> str:
    if (
        not isinstance(value, dict)
        or not isinstance(value.get("ObjectPath"), str)
        or not value["ObjectPath"]
    ):
        raise TypeError(f"{field} must contain ObjectPath")
    return value["ObjectPath"]


def _object_path_to_virtual(object_path: str) -> str:
    normalized = object_path.removesuffix(".0")
    if normalized.startswith("Pal/Content/") and "." not in normalized:
        return normalized
    package, separator, object_name = normalized.partition(".")
    if (
        separator
        and package.startswith("Pal/Content/")
        and object_name
        and "." not in object_name
    ):
        return package
    return _virtual_asset_path(normalized)


def _blueprint_class_path(value, field: str) -> str:
    prefix = "BlueprintGeneratedClass'"
    if (
        not isinstance(value, str)
        or not value.startswith(prefix)
        or not value.endswith("'")
    ):
        raise TypeError(f"{field} must be a serialized BlueprintGeneratedClass")
    object_path = value[len(prefix) : -1]
    if not object_path:
        raise ValueError(f"{field} contains an empty BlueprintGeneratedClass path")
    return object_path


def _referenced_blueprint_identity(reference, field: str) -> tuple[str, str]:
    object_path = _object_path(reference, field)
    virtual_path = _object_path_to_virtual(object_path)
    expected_type = f"{PurePosixPath(virtual_path).name}_C"
    if not isinstance(reference, dict):
        raise TypeError(f"{field} must be an object reference")
    serialized_class = _blueprint_class_path(
        reference.get("ObjectName"), f"{field}.ObjectName"
    )
    referenced_type = serialized_class.rsplit("/", 1)[-1].rsplit(".", 1)[-1]
    if referenced_type != expected_type:
        raise ValueError(
            f"{field}.ObjectName type {referenced_type!r} does not match "
            f"ObjectPath type {expected_type!r}"
        )
    return virtual_path, expected_type


def _referenced_blueprint_default(
    exports: list[dict], reference, field: str
) -> tuple[str, dict]:
    virtual_path, expected_type = _referenced_blueprint_identity(reference, field)
    properties = _select_spawner_default_object(
        exports, f"{virtual_path}.{expected_type}", field
    )
    return virtual_path, properties


def _casefold_key_index(rows: dict[str, dict], field: str) -> dict[str, str]:
    index: dict[str, str] = {}
    for key in rows:
        if not isinstance(key, str) or not key:
            raise TypeError(f"{field} keys must be nonempty strings")
        folded = key.casefold()
        if folded in index and index[folded] != key:
            raise ValueError(
                f"Case-insensitive key collision in {field}: {index[folded]} / {key}"
            )
        index[folded] = key
    return index


def _pal_actor_blueprint_identity(value, field: str) -> tuple[str, str]:
    object_path = _asset_path_name(value, field)
    package, separator, object_name = object_path.partition(".")
    prefix = "/Game/Pal/Blueprint/Character/Monster/PalActorBP/"
    if not separator or not package.startswith(prefix) or not object_name:
        raise ValueError(f"{field} must reference an exact PalActorBP class")
    expected_type = f"{package.rsplit('/', 1)[-1]}_C"
    if object_name != expected_type:
        raise ValueError(
            f"{field} class {object_name!r} does not match {expected_type!r}"
        )
    return _virtual_asset_path(object_path), expected_type


def monster_action_blueprint_roots(
    monster_rows: dict[str, dict], bp_class_rows: dict[str, dict]
) -> dict[str, str]:
    """Resolve every monster's exact PalActor Blueprint through BPClass."""
    bp_class_index = _casefold_key_index(bp_class_rows, "DT_PalBPClass_Common")
    roots = {}
    for character_id in sorted(monster_rows, key=str.casefold):
        row = monster_rows[character_id]
        if not isinstance(row, dict):
            raise TypeError(f"{character_id} must be an object")
        bp_class = _plain_name(row.get("BPClass"), f"{character_id}.BPClass")
        bp_row_id = bp_class_index.get(bp_class.casefold())
        if bp_row_id is None:
            # Parameter rows can precede their actor Blueprint implementation.
            # Without a BPClass row there is no exact action source to follow.
            continue
        bp_row = bp_class_rows[bp_row_id]
        if not isinstance(bp_row, dict):
            raise TypeError(f"{bp_row_id} must be an object")
        bp_value = bp_row.get("BPClass")
        if _asset_path_name(bp_value, f"{bp_row_id}.BPClass") == "None":
            continue
        roots[character_id] = _pal_actor_blueprint_identity(
            bp_value, f"{bp_row_id}.BPClass"
        )[0]
    return roots


def _scenario_package_tag(value, field: str) -> tuple[str, str] | None:
    """Return an exact Pal actor path and scenario stem token, when present."""
    object_path = _asset_path_name(value, field)
    if object_path == "None":
        return None
    package, separator, object_name = object_path.partition(".")
    prefix = "/Game/Pal/Blueprint/Character/Monster/PalActorBP/"
    if not separator or not package.startswith(prefix) or not object_name:
        return None
    expected_type = f"{package.rsplit('/', 1)[-1]}_C"
    if object_name != expected_type:
        raise ValueError(
            f"{field} class {object_name!r} does not match {expected_type!r}"
        )
    stem = package.rsplit("/", 1)[-1]
    tags = {
        token.casefold()
        for token in stem.split("_")
        if token.casefold() in {"oilrig", "quest", "summon", "otomo"}
    }
    if len(tags) > 1:
        raise ValueError(f"{field} has ambiguous scenario package tokens: {tags}")
    return f"Pal/Content/{package.removeprefix('/Game/')}", next(iter(tags), "")


def _select_blueprint_default(
    exports: list[dict], virtual_path: str, field: str
) -> dict:
    expected_type = f"{PurePosixPath(virtual_path).name}_C"
    holders = [
        item
        for item in exports
        if item.get("Type") == expected_type
        and item.get("Name") == f"Default__{expected_type}"
    ]
    if len(holders) != 1:
        raise ValueError(
            f"{field} expected exactly one default {expected_type!r}, got "
            f"{len(holders)}"
        )
    properties = holders[0].get("Properties")
    if not isinstance(properties, dict):
        raise TypeError(f"{field} default Properties must be an object")
    return properties


def capture_replacement_ids(exports: list[dict], virtual_path: str) -> tuple[str, str]:
    """Read the exact capture-replacement pair from one combat-module CDO."""
    if len(exports) <= 1 or not isinstance(exports[1].get("Properties"), dict):
        raise ValueError(f"{virtual_path} is missing exact export [1] Properties")
    expected_type = f"{PurePosixPath(virtual_path).name}_C"
    if "Type" in exports[1] and exports[1].get("Type") != expected_type:
        raise ValueError(f"{virtual_path} export [1] has an unexpected Type")
    if "Name" in exports[1] and exports[1].get("Name") != f"Default__{expected_type}":
        raise ValueError(f"{virtual_path} export [1] has an unexpected Name")
    properties = exports[1]["Properties"]
    return (
        _plain_name(
            properties.get("CaptureReplaceSourceCharacterID"),
            f"{virtual_path}.CaptureReplaceSourceCharacterID",
        ),
        _plain_name(
            properties.get("CaptureReplaceTargetCharacterID"),
            f"{virtual_path}.CaptureReplaceTargetCharacterID",
        ),
    )


def _select_monster_generated_class(exports: list[dict], virtual_path: str) -> dict:
    expected_name = f"{PurePosixPath(virtual_path).name}_C"
    holders = [
        item
        for item in exports
        if item.get("Type") == "BlueprintGeneratedClass"
        and item.get("Name") == expected_name
    ]
    if len(holders) != 1:
        raise ValueError(
            f"{virtual_path} expected exactly one BlueprintGeneratedClass "
            f"{expected_name!r}, got {len(holders)}"
        )
    package = holders[0].get("Package")
    if package != virtual_path:
        raise ValueError(
            f"{virtual_path} generated class Package must equal its exact path"
        )
    return holders[0]


def monster_blueprint_parent(exports: list[dict], virtual_path: str) -> str | None:
    """Return one exact Blueprint parent, or None for the native Pal parent."""
    generated = _select_monster_generated_class(exports, virtual_path)
    parent = generated.get("SuperStruct")
    field = f"{virtual_path}.SuperStruct"
    if not isinstance(parent, dict):
        raise TypeError(f"{field} must be an object reference")
    object_name = parent.get("ObjectName")
    object_path = parent.get("ObjectPath")
    if (
        isinstance(object_name, str)
        and object_name.startswith("Class'")
        and object_name.endswith("'")
    ):
        if object_path != "/Script/Pal":
            raise ValueError(f"{field} native parent must belong to /Script/Pal")
        return None
    parent_virtual, _ = _referenced_blueprint_identity(parent, field)
    return parent_virtual


def _monster_blueprint_action_map(
    exports: list[dict], virtual_path: str
) -> dict[str, tuple[str, str]]:
    holders = [
        item
        for item in exports
        if item.get("Type") == "PalStaticCharacterParameterComponent"
        and item.get("Name") == "StaticCharacterParameterComponent"
    ]
    if len(holders) > 1:
        raise ValueError(
            f"{virtual_path} expected at most one exact static character component, "
            f"got {len(holders)}"
        )
    if not holders:
        return {}
    if "Properties" not in holders[0]:
        return {}
    properties = holders[0].get("Properties")
    if not isinstance(properties, dict):
        raise TypeError(f"{virtual_path} action component Properties must be an object")
    declarations = properties.get("WazaActionDeclarationMap", [])
    if not isinstance(declarations, list):
        raise TypeError(f"{virtual_path}.WazaActionDeclarationMap must be a list")
    actions: dict[str, tuple[str, str]] = {}
    for index, declaration in enumerate(declarations):
        field = f"{virtual_path}.WazaActionDeclarationMap[{index}]"
        if not isinstance(declaration, dict):
            raise TypeError(f"{field} must be an object")
        action = _plain_name(declaration.get("Key"), f"{field}.Key")
        value = declaration.get("Value")
        if not isinstance(value, dict) or not isinstance(
            action_path := value.get("AssetPathName"), str
        ):
            raise TypeError(f"{field}.Value must contain a string AssetPathName")
        folded = action.casefold()
        if folded in actions and actions[folded][0] != action:
            raise ValueError(
                f"Case-insensitive key collision in WazaActionDeclarationMap: "
                f"{actions[folded][0]} / {action}"
            )
        actions[folded] = (action, action_path)
    return actions


def _monster_blueprint_actions(
    exports: list[dict], virtual_path: str
) -> frozenset[str]:
    return frozenset(
        action
        for action, action_path in _monster_blueprint_action_map(
            exports, virtual_path
        ).values()
        if action_path
    )


def build_monster_action_declarations(
    export_root: Path,
    monster_rows: dict[str, dict],
    bp_class_rows: dict[str, dict],
) -> tuple[dict[str, frozenset[str]], tuple[str, ...]]:
    """Union exact PalActor action maps across each Blueprint inheritance chain."""
    roots = monster_action_blueprint_roots(monster_rows, bp_class_rows)
    cache: dict[str, dict[str, tuple[str, str]]] = {}
    sources: set[str] = set()

    def inherited_action_map(
        virtual_path: str, stack: tuple[str, ...]
    ) -> dict[str, tuple[str, str]]:
        if virtual_path in cache:
            return cache[virtual_path]
        if virtual_path in stack:
            raise ValueError(
                "Monster Blueprint inheritance cycle: "
                + " -> ".join((*stack, virtual_path))
            )
        exports = load_asset(export_root, virtual_path)
        sources.add(virtual_path)
        parent = monster_blueprint_parent(exports, virtual_path)
        inherited = (
            {}
            if parent is None
            else dict(inherited_action_map(parent, (*stack, virtual_path)))
        )
        declarations = _monster_blueprint_action_map(exports, virtual_path)
        for folded, (action, _action_path) in declarations.items():
            if folded in inherited and inherited[folded][0] != action:
                raise ValueError(
                    f"Case-insensitive action key collision across {virtual_path}: "
                    f"{inherited[folded][0]} / {action}"
                )
        inherited.update(declarations)
        cache[virtual_path] = inherited
        return cache[virtual_path]

    actions = {
        character_id: frozenset(
            action
            for action, action_path in inherited_action_map(root, ()).values()
            if action_path
        )
        for character_id, root in roots.items()
    }
    return actions, tuple(sorted(sources))


def _supported_character_routes(policy: dict, domain: str = "skills") -> frozenset[str]:
    try:
        routes = policy["domains"][domain]["supported_routes"]
    except (KeyError, TypeError) as error:
        raise ValueError(f"{domain} supported_routes policy is missing") from error
    if not isinstance(routes, list) or any(
        not isinstance(route, str) or not route for route in routes
    ):
        raise ValueError(
            f"{domain} supported_routes must be a list of nonempty strings"
        )
    if len(routes) != len(set(routes)):
        raise ValueError(f"{domain} supported_routes must not contain duplicates")
    unknown = set(routes) - SUPPORTED_CHARACTER_ROUTES
    if unknown:
        raise ValueError(
            f"{domain} supported_routes contains unknown routes: {unknown}"
        )
    return frozenset(routes)


def _resolve_character(
    character_index: dict[str, str], value: str, field: str
) -> str | None:
    target = _plain_name(value, field)
    folded = target.casefold()
    if folded in character_index:
        return character_index[folded]
    if folded in _EMPTY_CHARACTER_FNAME_KEYS or folded == "no":
        return None
    raise ValueError(f"{field} references unknown character {target}")


def _resolve_fname_character(
    character_index: dict[str, str], value, field: str
) -> str | None:
    return _resolve_character(character_index, _fname_key(value, field), field)


def _append_evidence(items: list[EvidenceSource], source: EvidenceSource) -> None:
    if source not in items:
        items.append(source)


def _record_character_edge(
    mutable: dict[str, dict],
    character_id: str,
    source_kind: str,
    source_id: str,
    *,
    acquisition: bool,
    encounter_kind: str | None,
    boss: bool = False,
) -> None:
    node = mutable[character_id]
    if boss:
        node["tags"].add("boss")
    if acquisition:
        _append_evidence(node["sources"], EvidenceSource(source_kind, source_id))
    if encounter_kind is not None:
        _append_evidence(node["encounters"], EvidenceSource(encounter_kind, source_id))


def _spawn_group_targets(
    groups, character_index: dict[str, str], field: str
) -> list[str]:
    if not isinstance(groups, list):
        raise TypeError(f"{field} must be a list")
    targets = []
    for group_index, group in enumerate(groups):
        label = f"{field}[{group_index}]"
        if not isinstance(group, dict):
            raise TypeError(f"{label} must be an object")
        if not _positive_number(group.get("Weight"), f"{label}.Weight"):
            continue
        members = group.get("PalList")
        if not isinstance(members, list):
            raise TypeError(f"{label}.PalList must be a list")
        for member_index, member in enumerate(members):
            member_label = f"{label}.PalList[{member_index}]"
            if not isinstance(member, dict):
                raise TypeError(f"{member_label} must be an object")
            for target_field in ("PalId", "NPCID"):
                target = _resolve_fname_character(
                    character_index,
                    member.get(target_field),
                    f"{member_label}.{target_field}",
                )
                if target is not None:
                    targets.append(target)
    return targets


def _human_boss_targets(
    exports: list[dict], properties: dict, character_index: dict[str, str], field: str
) -> list[tuple[str, bool]] | None:
    if "HumanName" in properties:
        human = _resolve_fname_character(
            character_index, properties.get("HumanName"), f"{field}.HumanName"
        )
        if human is None:
            raise ValueError(f"{field}.HumanName cannot be empty")
        targets = [(human, True)]
        if "OtomoName" in properties:
            otomo = _resolve_fname_character(
                character_index, properties.get("OtomoName"), f"{field}.OtomoName"
            )
            if otomo is not None:
                targets.append((otomo, False))
        return targets
    if "SaveKeyName" not in properties:
        return None
    save_key = _plain_name(properties.get("SaveKeyName"), f"{field}.SaveKeyName")
    components = []
    for item in exports:
        if item.get("Type") != "BP_NPCSpawnPointComponent_C":
            continue
        component_properties = item.get("Properties")
        if not isinstance(component_properties, dict):
            raise TypeError(f"{field} NPC spawn-point Properties must be an object")
        target = _resolve_fname_character(
            character_index,
            component_properties.get("NPCName"),
            f"{field}.NPCName",
        )
        if target is not None:
            components.append((target, target.casefold() == save_key.casefold()))
    if len(components) != 3 or sum(boss for _, boss in components) != 1:
        raise ValueError(
            f"{field} squad requires three NPC spawn points and one SaveKeyName boss"
        )
    return components


def build_character_evidence(
    export_root: Path, policy: dict, domain: str = "skills"
) -> CharacterEvidenceGraph:
    """Build the minimum shared character/source graph used by skill policy."""
    supported_routes = _supported_character_routes(policy, domain)
    try:
        required_sources = policy["domains"][domain]["required_sources"]
    except (KeyError, TypeError) as error:
        raise ValueError(f"{domain} required_sources policy is missing") from error
    declared_sources = (
        set(CHARACTER_EVIDENCE_SOURCES.values())
        | set(CHARACTER_ROUTE_SOURCES.values())
        | set(RAID_REACHABILITY_SOURCES.values())
        | set(CHARACTER_SCENARIO_SOURCES.values())
        | {SKILL_SOURCES["bp_classes"]}
    )
    if not isinstance(required_sources, list) or not declared_sources.issubset(
        required_sources
    ):
        raise ValueError(f"{domain} policy is missing character-evidence sources")

    monsters = load_table(export_root, CHARACTER_EVIDENCE_SOURCES["monsters"])
    humans = load_table(export_root, CHARACTER_EVIDENCE_SOURCES["humans"])
    overlap = monsters.keys() & humans.keys()
    if overlap:
        raise ValueError(f"Character ID occurs in monster and human tables: {overlap}")
    rows = {**monsters, **humans}
    character_index = casefold_index(rows)
    monster_index = casefold_index(monsters)
    diagnostics = []
    consumed_asset_sources = set()

    def load_evidence_asset(source_path: str) -> list[dict]:
        asset = load_asset(export_root, source_path)
        consumed_asset_sources.add(source_path)
        return asset

    def route_enabled(route: str, source_path: str) -> bool:
        enabled = route in supported_routes
        if not enabled:
            diagnostics.append(
                EvidenceDiagnostic(
                    "coverage_gap",
                    source_path,
                    f"{route} is not enabled in supported_routes",
                )
            )
        return enabled

    mutable = {}
    for character_id, row in rows.items():
        human = character_id in humans
        tribe = _enum_tail(row.get("Tribe"), f"{character_id}.Tribe")
        core_flags = {
            field: _strict_bool(row, field, character_id)
            for field in ("IsBoss", "IsTowerBoss", "IsRaidBoss")
        }
        if not human:
            _strict_bool(row, "Predator", character_id)
        if human:
            family_id = character_id
            family_resolved = True
        else:
            family_id = tribe
            family_resolved = tribe.casefold() in monster_index
            if not family_resolved:
                diagnostics.append(
                    EvidenceDiagnostic("unresolved_family", character_id, tribe)
                )
        tags = {"human"} if human else set()
        tags.update(
            tag
            for field, tag in (
                ("IsBoss", "boss"),
                ("IsTowerBoss", "tower"),
                ("IsRaidBoss", "raid"),
            )
            if core_flags[field]
        )
        if not human:
            prefix = row.get("NamePrefixID")
            if prefix is not None and (not isinstance(prefix, str) or not prefix):
                raise TypeError(f"{character_id}.NamePrefixID must be a string")
            battle_bgm = row.get("BattleBGM")
            if battle_bgm is not None and _enum_tail(
                battle_bgm, f"{character_id}.BattleBGM"
            ).startswith("RaidBoss"):
                tags.add("raid")
            if prefix == "PREDATOR_NAME":
                tags.add("predator")
            if isinstance(prefix, str) and prefix.startswith("GYM_NAME_"):
                tags.add("tower")
            if row.get("FirstDefeatRewardItemID") == "BossDefeatReward_BossRush":
                tags.add("boss-rush")
            if (
                isinstance(prefix, str)
                and prefix.startswith("BOSS_NAME_")
                and prefix.endswith("BossRush")
            ):
                tags.add("boss-rush")
            if family_resolved and character_id.casefold() == family_id.casefold():
                tags.add("base")
        mutable[character_id] = {
            "family_id": family_id,
            "family_resolved": family_resolved,
            "tribe": tribe,
            "tags": tags,
            "sources": [],
            "encounters": [],
            "actions": set(),
        }

    bp_class_source = SKILL_SOURCES["bp_classes"]
    bp_classes = load_table(export_root, bp_class_source)
    bp_class_index = _casefold_key_index(bp_classes, "DT_PalBPClass_Common")
    actor_roots = {}
    for character_id, row in monsters.items():
        bp_class_value = row.get("BPClass")
        if bp_class_value is None:
            continue
        bp_class = _plain_name(bp_class_value, f"{character_id}.BPClass")
        bp_row_id = bp_class_index.get(bp_class.casefold())
        if bp_row_id is None:
            continue
        bp_row = bp_classes[bp_row_id]
        if not isinstance(bp_row, dict):
            raise TypeError(f"{bp_row_id} must be an object")
        resolved = _scenario_package_tag(bp_row.get("BPClass"), f"{bp_row_id}.BPClass")
        if resolved is None:
            continue
        actor_root, scenario_tag = resolved
        actor_roots[character_id] = actor_root
        if scenario_tag:
            mutable[character_id]["tags"].add(scenario_tag)

    if domain == "skills":
        action_monsters = {
            character_id: row
            for character_id, row in monsters.items()
            if isinstance(row.get("BPClass"), str) and row["BPClass"]
        }
        monster_actions, action_sources = build_monster_action_declarations(
            export_root, action_monsters, bp_classes
        )
        consumed_asset_sources.update(action_sources)
        for character_id, actions in monster_actions.items():
            mutable[character_id]["actions"].update(actions)

    for source_name in ("quest_spawners", "quest_sheet_spawners"):
        source_path = CHARACTER_SCENARIO_SOURCES[source_name]
        if not route_enabled("quest_spawner", source_path):
            continue
        try:
            assets = load_asset_collection(export_root, source_path)
        except FileNotFoundError as error:
            diagnostics.append(
                EvidenceDiagnostic("coverage_gap", source_path, str(error))
            )
            continue
        for asset_path, exports in assets:
            source_id = PurePosixPath(asset_path).name
            try:
                properties = _select_blueprint_default(exports, asset_path, asset_path)
            except (TypeError, ValueError) as error:
                diagnostics.append(
                    EvidenceDiagnostic("quest_spawner_gap", source_id, str(error))
                )
                continue
            extra_spawn_holders = [
                item
                for item in exports
                if isinstance(item.get("Properties"), dict)
                and "SpawnGroupList" in item["Properties"]
                and not (
                    item.get("Type") == f"{source_id}_C"
                    and item.get("Name") == f"Default__{source_id}_C"
                )
            ]
            if extra_spawn_holders:
                diagnostics.append(
                    EvidenceDiagnostic(
                        "quest_spawner_gap",
                        source_id,
                        "SpawnGroupList exists outside the exact package CDO",
                    )
                )
                continue
            if "SpawnGroupList" not in properties:
                continue
            for target in _spawn_group_targets(
                properties["SpawnGroupList"],
                character_index,
                f"{asset_path}.SpawnGroupList",
            ):
                mutable[target]["tags"].add("quest")
                _record_character_edge(
                    mutable,
                    target,
                    "quest-spawner",
                    source_id,
                    acquisition=False,
                    encounter_kind="scenario-quest",
                )
            battle_targets = properties.get("BattleTargetCharacterId", [])
            if not isinstance(battle_targets, list) or any(
                not isinstance(target, str) or not target for target in battle_targets
            ):
                diagnostics.append(
                    EvidenceDiagnostic(
                        "quest_spawner_gap",
                        source_id,
                        "BattleTargetCharacterId must be a list of character IDs",
                    )
                )
                continue
            for target_index, value in enumerate(battle_targets):
                target = _resolve_character(
                    character_index,
                    value,
                    f"{asset_path}.BattleTargetCharacterId[{target_index}]",
                )
                if target is not None:
                    _record_character_edge(
                        mutable,
                        target,
                        "quest-target",
                        source_id,
                        acquisition=False,
                        encounter_kind="scenario-quest-target",
                    )

    oilrig_source = CHARACTER_SCENARIO_SOURCES["oilrig_maps"]
    if route_enabled("oilrig", oilrig_source):
        try:
            oilrig_assets = load_asset_collection(export_root, oilrig_source)
        except FileNotFoundError as error:
            diagnostics.append(
                EvidenceDiagnostic("coverage_gap", oilrig_source, str(error))
            )
            oilrig_assets = ()
        for asset_path, exports in oilrig_assets:
            source_id = PurePosixPath(asset_path).name
            for export_index, item in enumerate(exports):
                properties = item.get("Properties")
                if not isinstance(properties, dict) or "HumanName" not in properties:
                    continue
                actor_type = item.get("Type")
                if actor_type not in OILRIG_NPC_SPAWNER_TYPES:
                    diagnostics.append(
                        EvidenceDiagnostic(
                            "oilrig_spawner_gap",
                            source_id,
                            f"HumanName holder has unsupported Type {actor_type!r}",
                        )
                    )
                    continue
                human = _resolve_fname_character(
                    character_index,
                    properties.get("HumanName"),
                    f"{asset_path}[{export_index}].HumanName",
                )
                if human is not None:
                    mutable[human]["tags"].add("oilrig")
                    _record_character_edge(
                        mutable,
                        human,
                        "oilrig",
                        source_id,
                        acquisition=False,
                        encounter_kind="scenario-oilrig",
                    )
                if "OtomoName" not in properties:
                    continue
                otomo = _resolve_fname_character(
                    character_index,
                    properties.get("OtomoName"),
                    f"{asset_path}[{export_index}].OtomoName",
                )
                if otomo is not None:
                    _record_character_edge(
                        mutable,
                        otomo,
                        "oilrig-otomo",
                        source_id,
                        acquisition=False,
                        encounter_kind="oilrig-otomo",
                    )

    grass_source = CHARACTER_SCENARIO_SOURCES["grass_boss_reward"]
    if route_enabled("quest_reward", grass_source):
        grass_asset = load_asset(export_root, grass_source)
        source_id = PurePosixPath(grass_source).name
        for export_index, expected_invoke in ((18, "Get_Zoe"), (19, "Get_ZoeRE")):
            if export_index >= len(grass_asset):
                diagnostics.append(
                    EvidenceDiagnostic(
                        "quest_reward_gap",
                        source_id,
                        f"missing exact export [{export_index}]",
                    )
                )
                continue
            item = grass_asset[export_index]
            if item.get("Type") != "FNBP_GetCharacter_C":
                diagnostics.append(
                    EvidenceDiagnostic(
                        "quest_reward_gap",
                        source_id,
                        f"export [{export_index}] is not FNBP_GetCharacter_C",
                    )
                )
                continue
            properties = item.get("Properties")
            if not isinstance(properties, dict):
                raise TypeError(
                    f"{grass_source}[{export_index}].Properties must be an object"
                )
            invoke_name = properties.get("NetworkInvokeName")
            level = properties.get("Level")
            if invoke_name != expected_invoke or not _is_number(level) or level != 1:
                diagnostics.append(
                    EvidenceDiagnostic(
                        "quest_reward_gap",
                        source_id,
                        f"export [{export_index}] is not {expected_invoke} level 1",
                    )
                )
                continue
            target = _resolve_fname_character(
                character_index,
                properties.get("PalId"),
                f"{grass_source}[{export_index}].PalId",
            )
            if target is None or "tower" not in mutable[target]["tags"]:
                diagnostics.append(
                    EvidenceDiagnostic(
                        "quest_reward_gap",
                        source_id,
                        f"{invoke_name} target is not an exact tower companion",
                    )
                )
                continue
            mutable[target]["tags"].add("otomo")
            _record_character_edge(
                mutable,
                target,
                "quest-reward",
                source_id,
                acquisition=True,
                encounter_kind=None,
            )

    capture_source = CHARACTER_SCENARIO_SOURCES["kingwhale_combat"]
    controller_source = CHARACTER_SCENARIO_SOURCES["kingwhale_controller"]
    if route_enabled("capture_replace", capture_source):
        try:
            controller_properties = _select_blueprint_default(
                load_evidence_asset(controller_source),
                controller_source,
                controller_source,
            )
            referenced_module, _ = _referenced_blueprint_identity(
                controller_properties.get("CombatModuleClass"),
                f"{controller_source}.CombatModuleClass",
            )
            if referenced_module != capture_source:
                raise ValueError(
                    f"controller references {referenced_module}, not {capture_source}"
                )
            source_name, target_name = capture_replacement_ids(
                load_evidence_asset(referenced_module), referenced_module
            )
            source_character = _resolve_character(
                character_index,
                source_name,
                f"{capture_source}.CaptureReplaceSourceCharacterID",
            )
            target_character = _resolve_character(
                character_index,
                target_name,
                f"{capture_source}.CaptureReplaceTargetCharacterID",
            )
            if source_character is None or target_character is None:
                raise ValueError("capture replacement cannot use an empty character")
            source_actor = actor_roots.get(source_character)
            target_actor = actor_roots.get(target_character)
            if source_actor is None or target_actor is None:
                raise ValueError(
                    "capture replacement characters lack exact PalActorBP rows"
                )
            if mutable[source_character]["tribe"] != mutable[target_character]["tribe"]:
                raise ValueError("capture replacement characters do not share Tribe")
            if PurePosixPath(source_actor).parent != PurePosixPath(target_actor).parent:
                raise ValueError(
                    "capture replacement actors do not share an actor family"
                )
            if "otomo" not in mutable[target_character]["tags"]:
                raise ValueError(
                    "capture replacement target lacks exact otomo package token"
                )
            if "otomo" in mutable[source_character]["tags"]:
                raise ValueError(
                    "capture replacement source unexpectedly has an otomo package token"
                )
            _select_monster_generated_class(
                load_evidence_asset(source_actor), source_actor
            )
            _select_monster_generated_class(
                load_evidence_asset(target_actor), target_actor
            )
        except (FileNotFoundError, TypeError, ValueError) as error:
            diagnostics.append(
                EvidenceDiagnostic("capture_replace_gap", capture_source, str(error))
            )
        else:
            source_id = PurePosixPath(capture_source).name
            _record_character_edge(
                mutable,
                source_character,
                "capture-replace-source",
                source_id,
                acquisition=False,
                encounter_kind="capture-replace-source",
            )
            _record_character_edge(
                mutable,
                target_character,
                "capture-replace",
                source_id,
                acquisition=True,
                encounter_kind=None,
            )

    placements = load_table(export_root, CHARACTER_EVIDENCE_SOURCES["placements"])
    unsafe_tags = {
        "tower",
        "raid",
        "predator",
        "boss-rush",
        "oilrig",
        "summon",
        "quest",
    }
    placement_rows = (
        placements.items()
        if route_enabled("placement", CHARACTER_EVIDENCE_SOURCES["placements"])
        else ()
    )
    for placement_id, placement in placement_rows:
        spawner_type = _enum_tail(
            placement.get("SpawnerType"), f"{placement_id}.SpawnerType"
        )
        placement_type = _enum_tail(
            placement.get("PlacementType"), f"{placement_id}.PlacementType"
        )
        object_path = _asset_path_name(
            placement.get("SpawnerClass"), f"{placement_id}.SpawnerClass"
        )
        asset = load_asset(export_root, _virtual_asset_path(object_path))
        properties = _select_spawner_default_object(
            asset, object_path, f"{placement_id}.SpawnerClass"
        )
        boss_targets = set()
        if "SpawnGroupList" in properties:
            targets = _spawn_group_targets(
                properties["SpawnGroupList"],
                character_index,
                f"{placement_id}.SpawnGroupList",
            )
        elif specialized := _human_boss_targets(
            asset, properties, character_index, f"{placement_id}.SpawnerClass"
        ):
            targets = [target for target, _ in specialized]
            boss_targets = {target for target, boss in specialized if boss}
        else:
            diagnostic = EvidenceDiagnostic(
                "unsupported_spawner", object_path, placement_id
            )
            if diagnostic not in diagnostics:
                diagnostics.append(diagnostic)
            continue
        for character_id in targets:
            evidence = mutable[character_id]
            field_boss = (spawner_type, placement_type) == (
                "FieldBoss",
                "FieldBoss",
            )
            ordinary = (spawner_type, placement_type) == ("Common", "Field")
            if character_id in boss_targets:
                evidence["tags"].add("boss")
            if field_boss and "boss" in evidence["tags"]:
                evidence["tags"].add("alpha")
            safe_field_boss = field_boss and not evidence["tags"] & unsafe_tags
            _record_character_edge(
                mutable,
                character_id,
                "placement",
                placement_id,
                acquisition=ordinary or safe_field_boss,
                encounter_kind=(
                    "ordinary-placement"
                    if ordinary or safe_field_boss
                    else "scenario-placement"
                ),
                boss=character_id in boss_targets,
            )

    def record_route(
        character_id: str,
        kind: str,
        source_id: str,
        *,
        acquisition: bool = True,
        encounter: bool = False,
    ) -> None:
        scenario = bool(mutable[character_id]["tags"] & unsafe_tags)
        _record_character_edge(
            mutable,
            character_id,
            kind,
            source_id,
            acquisition=acquisition,
            encounter_kind=(
                f"{'scenario' if scenario else 'ordinary'}-{kind}"
                if encounter
                else None
            ),
        )

    reached_wild_names = {
        _plain_name(row.get("SpawnerName"), f"{row_id}.SpawnerName").casefold()
        for row_id, row in placements.items()
    }
    wild_rows = (
        load_table(export_root, CHARACTER_ROUTE_SOURCES["wild"]).items()
        if route_enabled("reached_wild", CHARACTER_ROUTE_SOURCES["wild"])
        else ()
    )
    for row_id, row in wild_rows:
        spawner_name = _plain_name(row.get("SpawnerName"), f"{row_id}.SpawnerName")
        if spawner_name.casefold() not in reached_wild_names or not _positive_number(
            row.get("Weight"), f"{row_id}.Weight"
        ):
            continue
        for index in range(1, 4):
            for field in (f"Pal_{index}", f"NPC_{index}"):
                target = _resolve_character(
                    character_index, row.get(field), f"{row_id}.{field}"
                )
                if target is not None:
                    record_route(target, "wild", row_id, encounter=True)

    dungeon_rows = (
        load_table(export_root, CHARACTER_ROUTE_SOURCES["dungeon"]).items()
        if route_enabled("dungeon", CHARACTER_ROUTE_SOURCES["dungeon"])
        else ()
    )
    for row_id, row in dungeon_rows:
        if not _positive_number(
            row.get("WeightInSpawnAreaAndRank"),
            f"{row_id}.WeightInSpawnAreaAndRank",
        ):
            continue
        object_path = _asset_path_name(
            row.get("SpawnerBlueprintSoftClass"),
            f"{row_id}.SpawnerBlueprintSoftClass",
        )
        asset = load_asset(export_root, _virtual_asset_path(object_path))
        properties = _select_spawner_default_object(
            asset, object_path, f"{row_id}.SpawnerBlueprintSoftClass"
        )
        if "SpawnGroupList" not in properties:
            diagnostics.append(
                EvidenceDiagnostic("unsupported_acquisition", object_path, row_id)
            )
            continue
        for target in _spawn_group_targets(
            properties["SpawnGroupList"],
            character_index,
            f"{row_id}.SpawnGroupList",
        ):
            record_route(target, "dungeon", row_id, encounter=True)

    cage_rows = (
        load_table(export_root, CHARACTER_ROUTE_SOURCES["cage"]).items()
        if route_enabled("cage", CHARACTER_ROUTE_SOURCES["cage"])
        else ()
    )
    for row_id, row in cage_rows:
        if _positive_number(row.get("Weight"), f"{row_id}.Weight"):
            target = _resolve_character(
                character_index, row.get("PalId"), f"{row_id}.PalId"
            )
            if target is not None:
                record_route(target, "cage", row_id)

    fishing_spot_rows = (
        load_table(export_root, CHARACTER_ROUTE_SOURCES["fishing_spot"]).items()
        if route_enabled("fishing_spot", CHARACTER_ROUTE_SOURCES["fishing_spot"])
        else ()
    )
    for row_id, row in fishing_spot_rows:
        target = _resolve_fname_character(
            character_index, row.get("PalName"), f"{row_id}.PalName"
        )
        if target is not None:
            record_route(target, "fishing-spot", row_id, encounter=True)

    fish_pond_rows = (
        load_table(export_root, CHARACTER_ROUTE_SOURCES["fish_pond"]).items()
        if route_enabled("fish_pond", CHARACTER_ROUTE_SOURCES["fish_pond"])
        else ()
    )
    for row_id, row in fish_pond_rows:
        if _positive_number(row.get("Weight"), f"{row_id}.Weight"):
            target = _resolve_character(
                character_index, row.get("CharacterID"), f"{row_id}.CharacterID"
            )
            if target is not None:
                record_route(target, "fish-pond", row_id, encounter=True)

    shop_rows = load_table(export_root, CHARACTER_ROUTE_SOURCES["shop"])
    shop_enabled = route_enabled("shop_table_direct", CHARACTER_ROUTE_SOURCES["shop"])
    if shop_rows and shop_enabled:
        diagnostics.append(
            EvidenceDiagnostic(
                "coverage_gap",
                CHARACTER_ROUTE_SOURCES["shop"],
                "shop_table_direct has no independently proven cooked consumer",
            )
        )
    if shop_enabled:
        for row_id, row in shop_rows.items():
            targets = row.get("CharacterIDArray")
            if not isinstance(targets, list):
                raise TypeError(f"{row_id}.CharacterIDArray must be a list")
            for index, value in enumerate(targets):
                target = _resolve_fname_character(
                    character_index, value, f"{row_id}.CharacterIDArray[{index}]"
                )
                if target is not None:
                    record_route(target, "shop-table-direct", row_id)

    for route in ("invader", "visitor"):
        if not route_enabled(route, CHARACTER_ROUTE_SOURCES[route]):
            continue
        for row_id, row in load_table(
            export_root, CHARACTER_ROUTE_SOURCES[route]
        ).items():
            if not _positive_number(row.get("Weight"), f"{row_id}.Weight"):
                continue
            for suffix in "ABCDE":
                if not _positive_number(
                    row.get(f"Number_{suffix}"), f"{row_id}.Number_{suffix}"
                ):
                    continue
                for field in (f"CharactorID_{suffix}", f"Otomo_{suffix}"):
                    target = _resolve_character(
                        character_index, row.get(field), f"{row_id}.{field}"
                    )
                    if target is not None:
                        record_route(target, route, row_id, encounter=True)

    unique_rows = load_table(export_root, CHARACTER_ROUTE_SOURCES["unique_npc"])
    unique_index = casefold_index(unique_rows)
    arena_rows = (
        load_table(export_root, CHARACTER_ROUTE_SOURCES["arena"]).items()
        if route_enabled("arena_solo", CHARACTER_ROUTE_SOURCES["arena"])
        else ()
    )
    for row_id, row in arena_rows:
        direct = _resolve_fname_character(
            character_index, row.get("NPCID"), f"{row_id}.NPCID"
        )
        if direct is not None:
            record_route(direct, "arena", row_id, encounter=True)
        unique_id = _fname_key(row.get("UniqueNPCID"), f"{row_id}.UniqueNPCID")
        if unique_id.casefold() not in _EMPTY_CHARACTER_FNAME_KEYS:
            try:
                unique_row_id = unique_index[unique_id.casefold()]
            except KeyError as error:
                raise ValueError(
                    f"{row_id}.UniqueNPCID references unknown unique NPC {unique_id}"
                ) from error
            unique_target = _resolve_character(
                character_index,
                unique_rows[unique_row_id].get("CharacterID"),
                f"{row_id}.UniqueNPCID.CharacterID",
            )
            if unique_target is not None:
                record_route(unique_target, "arena", row_id, encounter=True)
        otomo = row.get("OtomoList")
        if not isinstance(otomo, list):
            raise TypeError(f"{row_id}.OtomoList must be a list")
        for index, member in enumerate(otomo):
            if not isinstance(member, dict):
                raise TypeError(f"{row_id}.OtomoList[{index}] must be an object")
            target = _resolve_fname_character(
                character_index,
                member.get("PalId"),
                f"{row_id}.OtomoList[{index}].PalId",
            )
            if target is not None:
                record_route(target, "arena", row_id, encounter=True)
                actions = member.get("WazaList", [])
                if not isinstance(actions, list):
                    raise TypeError(
                        f"{row_id}.OtomoList[{index}].WazaList must be a list"
                    )
                for action_index, action in enumerate(actions):
                    mutable[target]["actions"].add(
                        _plain_name(
                            action,
                            f"{row_id}.OtomoList[{index}].WazaList[{action_index}]",
                        )
                    )

    raid_source = CHARACTER_ROUTE_SOURCES["raid_boss"]
    raid_boss_enabled = route_enabled("raid_boss", raid_source)
    raid_egg_enabled = route_enabled("raid_egg", raid_source)
    raid_servant_enabled = route_enabled("raid_servant", raid_source)
    raid_route_enabled = raid_boss_enabled or raid_egg_enabled or raid_servant_enabled
    raid_rows = load_table(export_root, raid_source) if raid_route_enabled else {}
    raid_items = {}
    reachable_raid_items = set()
    if raid_route_enabled:
        item_source = SKILL_SOURCES["items"]
        reachability_sources = {item_source, *RAID_REACHABILITY_SOURCES.values()}
        if not reachability_sources.issubset(required_sources):
            raise ValueError(f"{domain} policy is missing raid reachability sources")
        raid_items = load_table(export_root, item_source)

    def positive_raid_value(value, field: str) -> bool:
        if not _is_number(value):
            raise TypeError(f"{field} must be numeric")
        if value < 0:
            raise ValueError(f"{field} cannot be negative")
        return value > 0

    def legal_item(item_id: str, field: str) -> bool:
        if item_id not in raid_items:
            diagnostics.append(EvidenceDiagnostic("unknown_item", item_id, field))
            return False
        return _strict_bool(raid_items[item_id], "bLegalInGame", item_id)

    legal_raid_rows = set()
    if raid_route_enabled:
        for row_id in raid_rows:
            if row_id not in raid_items:
                raise ValueError(f"{row_id} is missing exact summon item")
            summon_item = raid_items[row_id]
            if not _strict_bool(summon_item, "bLegalInGame", row_id):
                diagnostics.append(
                    EvidenceDiagnostic(
                        "illegal_raid_summon_item",
                        row_id,
                        "bLegalInGame is false",
                    )
                )
                continue
            if (
                summon_item.get("TypeA") != "EPalItemTypeA::Consume"
                or summon_item.get("TypeB") != "EPalItemTypeB::ConsumeOther"
            ):
                raise ValueError(f"{row_id} summon item must be Consume/ConsumeOther")
            legal_raid_rows.add(row_id)

        dungeon_rows_for_items = load_table(
            export_root, CHARACTER_ROUTE_SOURCES["dungeon"]
        )
        active_areas = {
            _plain_name(row.get("SpawnAreaId"), f"{row_id}.SpawnAreaId")
            for row_id, row in dungeon_rows_for_items.items()
            if positive_raid_value(
                row.get("WeightInSpawnAreaAndRank"),
                f"{row_id}.WeightInSpawnAreaAndRank",
            )
        }
        dungeon_item_rows = load_table(
            export_root, RAID_REACHABILITY_SOURCES["dungeon_items"]
        )
        active_item_fields = {
            _plain_name(
                row.get("ItemFieldLotteryName"),
                f"{row_id}.ItemFieldLotteryName",
            )
            for row_id, row in dungeon_item_rows.items()
            if _plain_name(row.get("SpawnAreaId"), f"{row_id}.SpawnAreaId")
            in active_areas
        }
        item_lottery_rows = load_table(
            export_root, RAID_REACHABILITY_SOURCES["item_lottery"]
        )
        reachable_items = set()
        for row_id, row in item_lottery_rows.items():
            field_name = _plain_name(row.get("FieldName"), f"{row_id}.FieldName")
            if field_name not in active_item_fields:
                continue
            quantities = (
                positive_raid_value(row.get("WeightInSlot"), f"{row_id}.WeightInSlot"),
                positive_raid_value(row.get("MaxNum"), f"{row_id}.MaxNum"),
                positive_raid_value(row.get("NumUnit"), f"{row_id}.NumUnit"),
            )
            if not all(quantities):
                continue
            item_id = _plain_name(row.get("StaticItemId"), f"{row_id}.StaticItemId")
            if legal_item(item_id, f"{row_id}.StaticItemId"):
                reachable_items.add(item_id)

        recipes = []
        for row_id, row in load_table(
            export_root, RAID_REACHABILITY_SOURCES["recipes"]
        ).items():
            product_id = _plain_name(row.get("Product_Id"), f"{row_id}.Product_Id")
            if product_id not in legal_raid_rows:
                continue
            if not positive_raid_value(
                row.get("Product_Count"), f"{row_id}.Product_Count"
            ):
                continue
            prerequisites = []
            unlock_id = _plain_name(row.get("UnlockItemID"), f"{row_id}.UnlockItemID")
            if unlock_id.casefold() not in _EMPTY_CHARACTER_FNAME_KEYS:
                if not legal_item(unlock_id, f"{row_id}.UnlockItemID"):
                    continue
                prerequisites.append(unlock_id)
            for index in range(1, 6):
                item_field = f"Material{index}_Id"
                count_field = f"Material{index}_Count"
                count = row.get(count_field, 0)
                if not positive_raid_value(count, f"{row_id}.{count_field}"):
                    continue
                material_id = _plain_name(row.get(item_field), f"{row_id}.{item_field}")
                if not legal_item(material_id, f"{row_id}.{item_field}"):
                    prerequisites = None
                    break
                prerequisites.append(material_id)
            if prerequisites is not None:
                recipes.append((product_id, tuple(prerequisites)))

        rewards = {}
        for row_id in legal_raid_rows:
            entries = raid_rows[row_id].get("SuccessItemList", [])
            if not isinstance(entries, list):
                raise TypeError(f"{row_id}.SuccessItemList must be a list")
            rewards[row_id] = []
            for index, entry in enumerate(entries):
                field = f"{row_id}.SuccessItemList[{index}]"
                if not isinstance(entry, dict):
                    raise TypeError(f"{field} must be an object")
                if not positive_raid_value(entry.get("Rate"), f"{field}.Rate"):
                    continue
                if not positive_raid_value(entry.get("Max"), f"{field}.Max"):
                    continue
                item_id = _fname_key(entry.get("ItemName"), f"{field}.ItemName")
                if legal_item(item_id, f"{field}.ItemName"):
                    rewards[row_id].append(item_id)

        changed = True
        while changed:
            changed = False
            for product_id, prerequisites in recipes:
                if product_id not in reachable_items and set(prerequisites).issubset(
                    reachable_items
                ):
                    reachable_items.add(product_id)
                    changed = True
            for source_id, reward_ids in rewards.items():
                if source_id not in reachable_items:
                    continue
                for item_id in reward_ids:
                    if item_id not in reachable_items:
                        reachable_items.add(item_id)
                        changed = True
        reachable_raid_items = legal_raid_rows & reachable_items

    for row_id, row in raid_rows.items():
        if row_id not in legal_raid_rows:
            continue
        if row_id not in reachable_raid_items:
            diagnostics.append(
                EvidenceDiagnostic(
                    "unreachable_raid_summon_item",
                    row_id,
                    "no reachable dungeon loot, recipe, or raid-reward path",
                )
            )
            continue

        if raid_boss_enabled:
            info_list = row.get("InfoList")
            if not isinstance(info_list, list):
                raise TypeError(f"{row_id}.InfoList must be a list")
            for index, info in enumerate(info_list):
                field = f"{row_id}.InfoList[{index}]"
                if not isinstance(info, dict):
                    raise TypeError(f"{field} must be an object")
                target = _resolve_fname_character(
                    character_index, info.get("PalId"), f"{field}.PalId"
                )
                if target is not None:
                    record_route(
                        target,
                        "raid-boss",
                        row_id,
                        acquisition=False,
                        encounter=True,
                    )

        if raid_egg_enabled:
            egg_entries = row.get("EggPalIDAndWeight")
            if not isinstance(egg_entries, list):
                raise TypeError(f"{row_id}.EggPalIDAndWeight must be a list")
            for index, entry in enumerate(egg_entries):
                field = f"{row_id}.EggPalIDAndWeight[{index}]"
                if not isinstance(entry, dict):
                    raise TypeError(f"{field} must be an object")
                if not positive_raid_value(entry.get("Value"), f"{field}.Value"):
                    continue
                target = _resolve_fname_character(
                    character_index, entry.get("Key"), f"{field}.Key"
                )
                if target is not None:
                    record_route(target, "raid-egg", row_id)

        if raid_servant_enabled:
            phases = row.get("SummonMeteor_Num", [])
            if not isinstance(phases, list):
                raise TypeError(f"{row_id}.SummonMeteor_Num must be a list")
            if phases:
                generator = _object_path(
                    row.get("SummonGeneratorClass"),
                    f"{row_id}.SummonGeneratorClass",
                )
                _object_path_to_virtual(generator)
            for phase_index, phase in enumerate(phases):
                phase_field = f"{row_id}.SummonMeteor_Num[{phase_index}]"
                if not isinstance(phase, dict):
                    raise TypeError(f"{phase_field} must be an object")
                if not positive_raid_value(
                    phase.get("HPRate"), f"{phase_field}.HPRate"
                ):
                    continue
                groups = phase.get("SummonPalInfoList")
                if not isinstance(groups, list):
                    raise TypeError(f"{phase_field}.SummonPalInfoList must be a list")
                for group_index, group in enumerate(groups):
                    group_field = f"{phase_field}.SummonPalInfoList[{group_index}]"
                    if not isinstance(group, dict):
                        raise TypeError(f"{group_field} must be an object")
                    members = group.get("PalNameAndNum")
                    if not isinstance(members, list):
                        raise TypeError(f"{group_field}.PalNameAndNum must be a list")
                    for member_index, member in enumerate(members):
                        member_field = f"{group_field}.PalNameAndNum[{member_index}]"
                        if not isinstance(member, dict):
                            raise TypeError(f"{member_field} must be an object")
                        if not positive_raid_value(
                            member.get("Value"), f"{member_field}.Value"
                        ):
                            continue
                        target = _resolve_fname_character(
                            character_index,
                            member.get("Key"),
                            f"{member_field}.Key",
                        )
                        if target is not None:
                            _record_character_edge(
                                mutable,
                                target,
                                "raid-servant",
                                row_id,
                                acquisition=False,
                                encounter_kind="scenario-raid-servant",
                            )

    breeding_rows = (
        load_table(export_root, CHARACTER_ROUTE_SOURCES["breeding"]).items()
        if route_enabled("unique_breeding", CHARACTER_ROUTE_SOURCES["breeding"])
        else ()
    )
    breeding_recipes = []
    for row_id, row in breeding_rows:
        target = _resolve_character(
            character_index,
            row.get("ChildCharacterID"),
            f"{row_id}.ChildCharacterID",
        )
        parents = tuple(
            _resolve_character(
                character_index,
                _enum_tail(row.get(field), f"{row_id}.{field}"),
                f"{row_id}.{field}",
            )
            for field in ("ParentTribeA", "ParentTribeB")
        )
        if target is not None and all(parents):
            breeding_recipes.append((row_id, target, parents))

    incident_enabled = route_enabled(
        "mainworld5_incident", CHARACTER_ROUTE_SOURCES["incident_world"]
    )
    incident_settings = (
        load_table(export_root, CHARACTER_ROUTE_SOURCES["incident_settings"])
        if incident_enabled
        else {}
    )
    incident_setting_index = casefold_index(incident_settings)
    world = (
        load_asset(export_root, CHARACTER_ROUTE_SOURCES["incident_world"])
        if incident_enabled
        else []
    )
    persistent_level = "Level'PL_MainWorld5:PersistentLevel'"
    placed_incident_spawners = 0
    for actor_index, actor in enumerate(world):
        outer = actor.get("Outer")
        if not isinstance(outer, dict) or outer.get("ObjectName") != persistent_level:
            continue
        class_ref = actor.get("Class")
        if not isinstance(class_ref, str) or not class_ref.startswith(
            "BlueprintGeneratedClass'"
        ):
            continue
        class_path = _blueprint_class_path(
            class_ref, f"incident actor {actor_index}.Class"
        )
        try:
            spawner_virtual = _object_path_to_virtual(class_path)
        except ValueError:
            continue
        if not _export_path(export_root, spawner_virtual).is_file():
            continue
        spawner_asset = load_asset(export_root, spawner_virtual)
        spawner_properties = _select_spawner_default_object(
            spawner_asset,
            class_path.removesuffix(".0"),
            f"incident actor {actor_index}.Class",
        )
        actor_properties = actor.get("Properties", {})
        if not isinstance(actor_properties, dict):
            raise TypeError(
                f"incident actor {actor_index}.Properties must be an object"
            )
        lottery_ref = actor_properties.get("LotteryClass") or spawner_properties.get(
            "LotteryClass"
        )
        if lottery_ref is None:
            continue
        lottery_field = f"incident actor {actor_index}.LotteryClass"
        lottery_path = _object_path(lottery_ref, lottery_field)
        lottery_virtual = _object_path_to_virtual(lottery_path)
        lottery_asset = load_asset(export_root, lottery_virtual)
        resolved_virtual, lottery_properties = _referenced_blueprint_default(
            lottery_asset, lottery_ref, lottery_field
        )
        if resolved_virtual != lottery_virtual:
            raise AssertionError("lottery reference resolved inconsistently")
        parameters = lottery_properties.get("LotteryParameters")
        if not isinstance(parameters, list):
            raise TypeError(
                f"incident actor {actor_index}.LotteryParameters must be a list"
            )
        placed_incident_spawners += 1
        for parameter_index, parameter in enumerate(parameters):
            label = f"incident actor {actor_index}.LotteryParameters[{parameter_index}]"
            if not isinstance(parameter, dict):
                raise TypeError(f"{label} must be an object")
            if not _positive_number(
                parameter.get("LotteryRate"), f"{label}.LotteryRate"
            ):
                continue
            setting_name = _plain_name(
                parameter.get("SettingName"), f"{label}.SettingName"
            )
            try:
                setting_id = incident_setting_index[setting_name.casefold()]
            except KeyError as error:
                raise ValueError(
                    f"{label}.SettingName references unknown setting {setting_name}"
                ) from error
            setting = incident_settings[setting_id]
            for spawn_field in ("MonsterSpawnData", "NPCSpawnData"):
                spawn_ref = setting.get(spawn_field)
                if not isinstance(spawn_ref, dict) or spawn_ref.get(
                    "ObjectPath", ""
                ).casefold() in {"", "none"}:
                    continue
                spawn_path = _object_path(spawn_ref, f"{setting_id}.{spawn_field}")
                spawn_virtual = _object_path_to_virtual(spawn_path)
                for spawn_id, spawn in load_table(export_root, spawn_virtual).items():
                    incident_id = f"{setting_id}:{spawn_field}:{spawn_id}"
                    for target_field in ("CharacterID", "OtomoName"):
                        if target_field not in spawn:
                            continue
                        target = _resolve_fname_character(
                            character_index,
                            spawn.get(target_field),
                            f"{incident_id}.{target_field}",
                        )
                        if target is not None:
                            record_route(
                                target, "incident", incident_id, encounter=True
                            )
                    if "UniqueNPCID" not in spawn:
                        continue
                    unique_id = _fname_key(
                        spawn["UniqueNPCID"], f"{incident_id}.UniqueNPCID"
                    )
                    if unique_id.casefold() in _EMPTY_CHARACTER_FNAME_KEYS:
                        continue
                    try:
                        unique_row_id = unique_index[unique_id.casefold()]
                    except KeyError as error:
                        raise ValueError(
                            f"{incident_id}.UniqueNPCID references unknown unique NPC "
                            f"{unique_id}"
                        ) from error
                    target = _resolve_character(
                        character_index,
                        unique_rows[unique_row_id].get("CharacterID"),
                        f"{incident_id}.UniqueNPCID.CharacterID",
                    )
                    if target is not None:
                        record_route(target, "incident", incident_id, encounter=True)
    if incident_settings and not placed_incident_spawners:
        diagnostics.append(
            EvidenceDiagnostic(
                "unsupported_acquisition",
                CHARACTER_ROUTE_SOURCES["incident_world"],
                "no placed incident spawner reached a lottery",
            )
        )

    reachable_families = {
        value["family_id"].casefold()
        for value in mutable.values()
        if value["sources"]
    }
    pending_recipes = list(breeding_recipes)
    changed = True
    while changed:
        changed = False
        for recipe in pending_recipes[:]:
            row_id, target, parents = recipe
            if not {
                mutable[parent]["family_id"].casefold() for parent in parents
            }.issubset(reachable_families):
                continue
            record_route(target, "unique-breeding", row_id)
            source = EvidenceSource("unique-breeding", row_id)
            sources = mutable[target]["sources"]
            sources.remove(source)
            incident_index = next(
                (index for index, item in enumerate(sources) if item.kind == "incident"),
                len(sources),
            )
            sources.insert(incident_index, source)
            reachable_families.add(mutable[target]["family_id"].casefold())
            pending_recipes.remove(recipe)
            changed = True

    for character_id, value in mutable.items():
        if not value["tags"] or not value["tags"].issubset({"boss", "alpha"}):
            continue
        base_id = character_index.get(value["family_id"].casefold())
        if base_id and mutable[base_id]["sources"] and not value["sources"]:
            record_route(character_id, "alpha-form", base_id)

    action_assets = load_asset(export_root, CHARACTER_EVIDENCE_SOURCES["human_actions"])
    action_properties = _select_human_action_component(action_assets)
    declarations = action_properties.get("WazaActionDeclarationMap")
    if not isinstance(declarations, list):
        raise TypeError("WazaActionDeclarationMap must be a list")
    actions = set()
    for declaration in declarations:
        if (
            not isinstance(declaration, dict)
            or not isinstance(declaration.get("Key"), str)
            or not declaration["Key"]
        ):
            raise TypeError("WazaActionDeclarationMap entry requires a string Key")
        actions.add(declaration["Key"])
    for character_id in humans:
        if mutable[character_id]["encounters"]:
            mutable[character_id]["actions"].update(actions)

    evidence = {
        character_id: Evidence(
            character_id=character_id,
            family_id=value["family_id"],
            family_resolved=value["family_resolved"],
            tribe=value["tribe"],
            variant_tags=frozenset(value["tags"]),
            acquisition_sources=tuple(value["sources"]),
            encounter_sources=tuple(value["encounters"]),
            action_declarations=frozenset(value["actions"]),
            regularly_obtainable=bool(value["sources"]),
        )
        for character_id, value in mutable.items()
    }
    return CharacterEvidenceGraph(
        evidence,
        tuple(diagnostics),
        tuple(sorted(consumed_asset_sources)),
    )


def _source_number(row: dict, field: str, row_id: str):
    value = row.get(field)
    if not _is_number(value):
        raise TypeError(f"{row_id}.{field} must be numeric")
    return value


def _source_bool(row: dict, field: str, row_id: str) -> bool:
    value = row.get(field)
    if type(value) is not bool:
        raise TypeError(f"{row_id}.{field} must be a bool")
    return value


def _source_string(row: dict, field: str, row_id: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value:
        raise TypeError(f"{row_id}.{field} must be a nonempty string")
    return value


def _localized_character_names(
    character_id: str,
    row: dict,
    texts: dict[str, dict[str, dict]],
    *,
    human: bool,
) -> tuple[dict[str, str], list[str]]:
    override = _source_string(row, "OverrideNameTextID", character_id)
    key = (
        override
        if override.casefold() != "none"
        else f"PAL_NAME_{_enum_tail(row['Tribe'], f'{character_id}.Tribe')}"
    )
    table_names = ("human", "unique") if human else ("pal",)
    prefix_key = _source_string(row, "NamePrefixID", character_id)
    missing = []

    def localized_part(locale: str, names: tuple[str, ...], text_id: str) -> str | None:
        return next(
            (
                value
                for name in names
                if (value := _text_value(texts[name][locale], text_id)) is not None
            ),
            None,
        )

    def fallback(names: tuple[str, ...], text_id: str, default: str) -> str:
        return next(
            (
                value
                for locale in ("en", "ja")
                if (value := localized_part(locale, names, text_id)) is not None
            ),
            default,
        )

    output = {}
    for locale in LOCALE_DIRECTORIES:
        name = localized_part(locale, table_names, key)
        if name is None:
            missing.append(f"character:{character_id}:{locale}:Name:{key}")
            name = fallback(table_names, key, character_id)
        prefix = ""
        if prefix_key.casefold() != "none":
            prefix = localized_part(locale, ("prefix",), prefix_key) or ""
            if not prefix:
                missing.append(f"character:{character_id}:{locale}:Prefix:{prefix_key}")
                prefix = fallback(("prefix",), prefix_key, "")
        output[locale] = f"{prefix} {name}".strip()
    return output, missing


def _texture_virtual_path(icon_row: dict, label: str, field: str = "Icon") -> str:
    icon = icon_row.get(field)
    if not isinstance(icon, dict):
        raise TypeError(f"{label}.{field} must be an object")
    asset_path = icon.get("AssetPathName")
    if (
        not isinstance(asset_path, str)
        or not asset_path.startswith("/Game/")
        or "." not in asset_path
    ):
        raise TypeError(f"{label}.{field}.AssetPathName must be a game object path")
    package, object_name = asset_path.split(".", 1)
    if not object_name or package.rsplit("/", 1)[-1] != object_name:
        raise ValueError(f"{label}.{field}.AssetPathName package/object mismatch")
    return f"Pal/Content/{package.removeprefix('/Game/')}"


def _variant_kind(tags: frozenset[str]) -> str:
    for kind in (
        "boss-rush",
        "quest",
        "summon",
        "oilrig",
        "tower",
        "raid",
        "predator",
        "alpha",
        "base",
        "human",
        "boss",
    ):
        if kind in tags:
            return kind
    return "other"


def build_character_records(
    tables: dict[str, dict[str, dict]],
    texts: dict[str, dict[str, dict[str, dict]]],
    evidence_graph: CharacterEvidenceGraph,
) -> dict:
    """Project validated character tables without reading or writing the filesystem."""
    required_tables = {
        "monsters",
        "humans",
        "levels",
        "passives",
        "breeding",
        "icons",
        "skins",
        "skin_icons",
    }
    if set(tables) != required_tables:
        raise ValueError(f"Character tables must be exactly {sorted(required_tables)}")
    if set(texts) != set(CHARACTER_TEXT_TABLES) or any(
        set(localized) != set(LOCALE_DIRECTORIES) for localized in texts.values()
    ):
        raise ValueError(
            "Character text tables must contain five tables and 17 locales"
        )
    monsters = tables["monsters"]
    humans = tables["humans"]
    overlap = monsters.keys() & humans.keys()
    if overlap:
        raise ValueError(f"Character ID occurs in monster and human tables: {overlap}")
    characters = {**monsters, **humans}
    character_index = casefold_index(characters)
    passive_index = casefold_index(tables["passives"])
    icon_index = casefold_index(tables["icons"])
    skin_icon_index = casefold_index(tables["skin_icons"])
    if set(evidence_graph) != set(characters):
        raise ValueError("Character evidence IDs do not match parameter-table IDs")

    attacks = {character_id: {} for character_id in characters}
    diagnostics = []
    for source_id, level_row in tables["levels"].items():
        character_ref = _source_string(level_row, "PalId", source_id)
        skill_id = _source_string(level_row, "WazaID", source_id)
        level = level_row.get("Level")
        if not isinstance(level, int) or isinstance(level, bool):
            raise TypeError(f"{source_id}.Level must be an integer")
        character_id = character_index.get(character_ref.casefold())
        if character_id is None:
            diagnostics.append(
                f"learnset:{source_id}:unknown-character:{character_ref}"
            )
            continue
        previous = attacks[character_id].setdefault(skill_id, level)
        if previous != level:
            raise ValueError(
                f"{source_id} gives conflicting levels for {character_id}:{skill_id}"
            )

    unique_recipes = {character_id: [] for character_id in characters}
    for recipe_id, recipe in tables["breeding"].items():
        if set(recipe) != {
            "ParentTribeA",
            "ParentTribeB",
            "ParentGenderA",
            "ParentGenderB",
            "ChildCharacterID",
        }:
            raise ValueError(
                f"{recipe_id} breeding fields are incomplete or unexpected"
            )
        for field in recipe:
            _source_string(recipe, field, recipe_id)
        child_ref = recipe["ChildCharacterID"]
        try:
            child_id = character_index[child_ref.casefold()]
        except KeyError as error:
            raise ValueError(
                f"{recipe_id}.ChildCharacterID references unknown character {child_ref}"
            ) from error
        unique_recipes[child_id].append(deepcopy_json(recipe))

    missing_localizations = []
    missing_icons = []
    pending_icons: dict[str, tuple[str, str]] = {}
    icon_sources: dict[str, str] = {}
    icon_source_keys: dict[tuple[str, str], str] = {}

    def add_icon(logical_key: str, source: str, directory: str) -> str:
        canonical_source = (directory.casefold(), source.casefold())
        if canonical_source in icon_source_keys:
            return icon_source_keys[canonical_source]
        path = f"{directory}/{logical_key}.png"
        folded_path = path.casefold()
        if folded_path in pending_icons and pending_icons[folded_path][1] != source:
            raise ValueError(f"Case-insensitive logical icon collision: {path}")
        pending_icons[folded_path] = (path, source)
        icon_sources[path] = source
        icon_source_keys[canonical_source] = logical_key
        return logical_key

    records = {}
    ordered_characters = sorted(
        characters,
        key=lambda character_id: (
            evidence_graph[character_id].family_id.casefold()
            != character_id.casefold(),
            character_id in humans,
            character_id.casefold(),
        ),
    )
    for character_id in ordered_characters:
        row = characters[character_id]
        evidence = evidence_graph[character_id]
        human = character_id in humans
        i18n, missing = _localized_character_names(
            character_id, row, texts, human=human
        )
        missing_localizations.extend(missing)
        stats = {
            output: _source_number(row, source, character_id)
            for output, source in CHARACTER_STATS.items()
        }
        parameters = {}
        for field in CHARACTER_PARAMETER_FIELDS:
            if field in {"Size"}:
                parameters[field] = _source_string(row, field, character_id)
            elif field in {"Nocturnal", "Predator", "Edible", "IgnoreCombi"}:
                parameters[field] = _source_bool(row, field, character_id)
            else:
                parameters[field] = _source_number(row, field, character_id)
        suitabilities = {
            f"EPalWorkSuitability::{name}": parameters[f"WorkSuitability_{name}"]
            for name in WORK_SUITABILITIES
        }
        passives = []
        for index in range(1, 5):
            field = f"PassiveSkill{index}"
            passive_ref = _source_string(row, field, character_id)
            if passive_ref.casefold() == "none":
                continue
            try:
                passives.append(passive_index[passive_ref.casefold()])
            except KeyError as error:
                raise ValueError(
                    f"{character_id}.{field} references unknown passive {passive_ref}"
                ) from error

        family = evidence.family_id
        family_row_id = character_index.get(family.casefold())
        deck_id = family_row_id if family_row_id in monsters else character_id
        deck_row = characters[deck_id]
        deck_index = deck_row.get("ZukanIndex")
        if (
            not isinstance(deck_index, int)
            or isinstance(deck_index, bool)
            or deck_index < 0
        ):
            deck_id = character_id
            deck_row = row
            deck_index = deck_row.get("ZukanIndex")
        if not isinstance(deck_index, int) or isinstance(deck_index, bool):
            raise TypeError(f"{deck_id}.ZukanIndex must be an integer")
        deck_suffix = deck_row.get("ZukanIndexSuffix")
        if not isinstance(deck_suffix, str):
            raise TypeError(f"{deck_id}.ZukanIndexSuffix must be a string")
        sorting_key = f"{deck_index}{deck_suffix}" if deck_index >= 0 else ""

        icon_match = None
        for candidate in (
            character_id,
            _source_string(row, "BPClass", character_id),
            family,
        ):
            if icon_id := icon_index.get(candidate.casefold()):
                icon_match = icon_id
                break
        if icon_match is None:
            icon_key = "Human" if human else "unknown"
            diagnostics.append(f"character:{character_id}:static-icon:{icon_key}")
            has_icon = False
        else:
            source = _texture_virtual_path(tables["icons"][icon_match], icon_match)
            suggested_key = (
                family
                if icon_match.casefold() == family.casefold()
                else character_index.get(icon_match.casefold(), icon_match)
            )
            icon_key = add_icon(suggested_key, source, "icons/pals")
            has_icon = True

        row_output = {
            "InternalName": character_id,
            "FamilyID": family,
            "FamilyResolved": evidence.family_resolved,
            "VariantKind": _variant_kind(evidence.variant_tags),
            "VariantTags": sorted(evidence.variant_tags),
            "IconKey": icon_key,
            "Invalid": not evidence.regularly_obtainable,
            "RegularlyObtainable": evidence.regularly_obtainable,
            "ObtainMethods": sorted(
                {source.kind for source in evidence.acquisition_sources}
            ),
            "AvailabilitySources": [
                {"Kind": source.kind, "ID": source.source_id}
                for source in evidence.acquisition_sources
            ],
            "I18n": i18n,
            "Elements": [
                element
                for value in (row.get("ElementType1"), row.get("ElementType2"))
                if (element := _character_element(value, character_id)) is not None
            ],
            "Stats": stats,
            "Parameters": parameters,
            "Suitabilities": suitabilities,
            "BestWorkSuitability": _source_string(
                row, "BestWorkSuitability", character_id
            ),
            "DefaultPassives": passives,
            "Attacks": dict(sorted(attacks[character_id].items())),
            "SortingKey": {"paldeck": sorting_key},
            "PaldeckIndex": deck_index,
            "PaldeckSuffix": deck_suffix,
            "Breeding": {
                "CombiRank": parameters["CombiRank"],
                "CombiDuplicatePriority": parameters["CombiDuplicatePriority"],
                "IgnoreCombi": parameters["IgnoreCombi"],
                "UniqueRecipes": unique_recipes[character_id],
            },
        }
        if deck_id.casefold() != family.casefold():
            row_output["PaldeckRecordID"] = deck_id
        if human:
            row_output["Human"] = True
            row_output["HasIcon"] = has_icon
        records[character_id] = row_output

    skins = {}
    for skin_id, row in sorted(tables["skins"].items()):
        if set(row) != set(SKIN_SOURCE_FIELDS):
            raise ValueError(f"{skin_id} skin fields are incomplete or unexpected")
        for field in (
            "SkinName",
            "SkinType",
            "SkinStaticClass",
            "TargetActorClassName",
            "TargetPalName",
        ):
            _source_string(row, field, skin_id)
        for field in ("bIsHairAccessory", "bAutoGetItem"):
            _source_bool(row, field, skin_id)
        platform_id = row.get("PlatformItemID_Steam")
        if not isinstance(platform_id, int) or isinstance(platform_id, bool):
            raise TypeError(f"{skin_id}.PlatformItemID_Steam must be an integer")
        if row["SkinName"] != skin_id:
            raise ValueError(f"{skin_id}.SkinName must equal its row ID")
        try:
            target = character_index[row["TargetPalName"].casefold()]
        except KeyError as error:
            raise ValueError(
                f"{skin_id}.TargetPalName references unknown character "
                f"{row['TargetPalName']}"
            ) from error
        key = f"SKIN_NAME_{skin_id}"
        i18n = {}
        for locale in LOCALE_DIRECTORIES:
            name = _text_value(texts["ui"][locale], key)
            if name is None:
                missing_localizations.append(f"skin:{skin_id}:{locale}:Name")
                name = next(
                    (
                        value
                        for fallback_locale in ("en", "ja")
                        if (value := _text_value(texts["ui"][fallback_locale], key))
                    ),
                    skin_id,
                )
            i18n[locale] = name
        icon_id = skin_icon_index.get(skin_id.casefold())
        if icon_id is None:
            icon_key = skin_id
            invalid = True
            missing_icons.append(f"icons/pals/skin/{skin_id}.png")
        else:
            source = _texture_virtual_path(
                tables["skin_icons"][icon_id], f"skin:{icon_id}"
            )
            icon_key = add_icon(skin_id, source, "icons/pals/skin")
            invalid = False
        skin = deepcopy_json(row)
        skin.update(
            {
                "InternalName": skin_id,
                "TargetPalName": target,
                "I18n": i18n,
                "IconKey": icon_key,
                "Invalid": invalid,
            }
        )
        skins[skin_id] = skin

    return {
        "pals": {key: records[key] for key in monsters},
        "humans": {key: records[key] for key in humans},
        "skins": skins,
        "icon_sources": dict(sorted(icon_sources.items())),
        "missing_localizations": tuple(sorted(set(missing_localizations))),
        "missing_icons": tuple(sorted(set(missing_icons))),
        "diagnostics": tuple(sorted(set(diagnostics))),
    }


def _character_element(value, character_id: str) -> str | None:
    element = _enum_tail(value, f"{character_id}.ElementType")
    return {
        "Normal": "Neutral",
        "Fire": "Fire",
        "Water": "Water",
        "Electricity": "Electric",
        "Leaf": "Grass",
        "Ice": "Ice",
        "Earth": "Ground",
        "Dark": "Dark",
        "Dragon": "Dragon",
        "None": None,
    }.get(element, element)


def _text_value(rows: dict[str, dict], key: str) -> str | None:
    row = rows.get(key)
    if row is None:
        return None
    if not isinstance(row, dict) or not isinstance(row.get("TextData"), dict):
        raise TypeError(f"Text row {key} must contain TextData")
    data = row["TextData"]
    value = data.get("LocalizedString") or data.get("SourceString")
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"Text row {key} must contain string text")
    return value or None


def _number_text(value: float, *, signed: bool = False) -> str:
    if not _is_number(value):
        raise TypeError(f"Effect value must be numeric: {value!r}")
    text = str(int(value)) if float(value).is_integer() else str(value)
    return f"+{text}" if signed and value >= 0 else text


def _clean_game_text(
    text: str,
    effect_values: tuple[int | float, ...],
    ui_rows: dict[str, dict],
    missing: list[str],
    label: str,
) -> str:
    for index, value in enumerate(effect_values, 1):
        text = text.replace(f"{{EffectValue{index}}}", _number_text(value))

    def replace_ui(match: re.Match) -> str:
        key = match.group(1)
        value = _text_value(ui_rows, key)
        if value is None:
            missing.append(f"{label}:UI:{key}")
            return key
        return value

    text = re.sub(r"<uiCommon id=\|([^|]+)\|\s*/>", replace_ui, text)
    text = re.sub(r"<[^>]+>", "", text)
    return " ".join(text.split())


def _locale_fallback(
    tables: dict[str, dict[str, dict]], key: str, internal_id: str
) -> str:
    for locale in ("en", "ja"):
        if value := _text_value(tables[locale], key):
            return value
    return internal_id


def build_passive_records(
    passive_rows: dict[str, dict],
    names_by_locale: dict[str, dict[str, dict]],
    descriptions_by_locale: dict[str, dict[str, dict]],
    ui_by_locale: dict[str, dict[str, dict]],
) -> tuple[dict[str, dict], tuple[str, ...]]:
    """Build the exact Pal-passive projection from already loaded source tables."""
    if (
        set(names_by_locale) != set(LOCALE_DIRECTORIES)
        or set(descriptions_by_locale) != set(LOCALE_DIRECTORIES)
        or set(ui_by_locale) != set(LOCALE_DIRECTORIES)
    ):
        raise ValueError("Passive localization must contain exactly 17 locales")
    missing = []
    records = {}
    invocation_fields = {
        "ActiveOtomo": "InvokeActiveOtomo",
        "Worker": "InvokeWorker",
        "Riding": "InvokeRiding",
        "Reserve": "InvokeReserve",
        "InOtomo": "InvokeInOtomo",
        "Always": "InvokeAlways",
        "InBaseCamp": "InvokeInBaseCamp",
    }
    buff_fields = {
        "ShotAttack": "b_Attack",
        "Defense": "b_Defense",
        "CraftSpeed": "b_CraftSpeed",
        "MoveSpeed": "b_MoveSpeed",
    }
    for passive_id, row in passive_rows.items():
        for field in invocation_fields.values():
            if type(row.get(field)) is not bool:
                raise TypeError(f"{passive_id}.{field} must be a bool")
        category = _enum_tail(row.get("Category"), f"{passive_id}.Category")
        if category != "SortDisplayable":
            continue
        effects = []
        effect_values = []
        buff = {
            "b_Attack": 0.0,
            "b_Defense": 0.0,
            "b_CraftSpeed": 0.0,
            "b_MoveSpeed": 0.0,
        }
        for index in range(1, 5):
            effect_type = _enum_tail(
                row.get(f"EffectType{index}"),
                f"{passive_id}.EffectType{index}",
            )
            target_type = _enum_tail(
                row.get(f"TargetType{index}"),
                f"{passive_id}.TargetType{index}",
            )
            value = row.get(f"EffectValue{index}")
            if not _is_number(value):
                raise TypeError(f"{passive_id}.EffectValue{index} must be numeric")
            effect_values.append(value)
            if effect_type in {"None", "no"} or value == 0:
                continue
            effects.append(
                {
                    "EffectType": effect_type,
                    "EffectValue": value,
                    "TargetType": target_type,
                }
            )
            if (
                target_type in {"ToSelf", "ToSelfAndTrainer"}
                and effect_type in buff_fields
            ):
                buff[buff_fields[effect_type]] += value / 100
        triggers = []
        for index in range(1, 3):
            trigger = _enum_tail(
                row.get(f"AddInvokeTriggerType_{index}"),
                f"{passive_id}.AddInvokeTriggerType_{index}",
            )
            if trigger != "None":
                triggers.append(trigger)
        name_key = row.get("OverrideNameTextID")
        if not isinstance(name_key, str):
            raise TypeError(f"{passive_id}.OverrideNameTextID must be a string")
        if name_key == "None":
            name_key = f"PASSIVE_{passive_id}"
        override_description = row.get("OverrideDescMsgID")
        if not isinstance(override_description, str):
            raise TypeError(f"{passive_id}.OverrideDescMsgID must be a string")
        description_keys = (
            override_description,
            f"PASSIVE_{passive_id}_DESC",
            f"PASSIVE_{passive_id}",
        )
        i18n = {}
        sources = {}
        for locale in LOCALE_DIRECTORIES:
            name = _text_value(names_by_locale[locale], name_key)
            if name is None:
                missing.append(f"passive:{passive_id}:{locale}:Name:{name_key}")
                name = _locale_fallback(names_by_locale, name_key, passive_id)
            description = None
            for key in description_keys:
                if key != "None" and (
                    description := _text_value(descriptions_by_locale[locale], key)
                ):
                    break
            if description is not None:
                description = _clean_game_text(
                    description,
                    tuple(effect_values),
                    ui_by_locale[locale],
                    missing,
                    f"passive:{passive_id}:{locale}:Description",
                )
                source = "explicit"
            else:
                parts = []
                for effect in effects:
                    effect_type = effect["EffectType"]
                    label = (
                        _text_value(ui_by_locale[locale], effect_type) or effect_type
                    )
                    parts.append(
                        f"{effect['TargetType']}: {label} "
                        f"{_number_text(effect['EffectValue'], signed=True)}"
                    )
                description = "; ".join(parts) or passive_id
                source = "composed"
            i18n[locale] = {"Name": name, "Description": description}
            sources[locale] = source
        records[passive_id] = {
            "InternalName": passive_id,
            "Rating": row.get("Rank"),
            "I18n": i18n,
            "Buff": buff,
            "Category": category,
            "TargetElementType": _enum_tail(
                row.get("TargetElementType"),
                f"{passive_id}.TargetElementType",
            ),
            "Effects": effects,
            "Invocation": {
                output: row[source] for output, source in invocation_fields.items()
            },
            "AddInvokeTriggerTypes": triggers,
            "DescriptionSource": sources,
        }
    return records, tuple(sorted(set(missing)))


def build_active_records(
    waza_rows: dict[str, dict],
    level_rows: dict[str, dict],
    item_rows: dict[str, dict],
    names_by_locale: dict[str, dict[str, dict]],
    descriptions_by_locale: dict[str, dict[str, dict]],
    evidence_graph: CharacterEvidenceGraph,
) -> tuple[dict[str, dict], tuple[str, ...]]:
    """Build active-skill records from Waza data and the shared evidence graph."""
    blockers = tuple(
        diagnostic
        for diagnostic in evidence_graph.diagnostics
        if diagnostic.kind in {"unsupported_spawner", "unsupported_acquisition"}
    )
    if blockers:
        raise ValueError(
            "Character acquisition evidence is incomplete: "
            + ", ".join(item.source_id for item in blockers)
        )
    if set(names_by_locale) != set(LOCALE_DIRECTORIES) or set(
        descriptions_by_locale
    ) != set(LOCALE_DIRECTORIES):
        raise ValueError("Active localization must contain exactly 17 locales")
    by_id = {}
    for source_id, row in waza_rows.items():
        skill_id = row.get("WazaType")
        if not isinstance(skill_id, str) or not skill_id:
            raise TypeError(f"{source_id}.WazaType must be a string")
        folded = skill_id.casefold()
        if folded in by_id:
            raise ValueError(f"Case-insensitive WazaType collision: {skill_id}")
        by_id[folded] = (skill_id, row)
    character_index = casefold_index(evidence_graph.evidence)
    learners = {skill_id: [] for skill_id, _ in by_id.values()}
    for source_id, row in level_rows.items():
        skill_ref = row.get("WazaID")
        character_ref = row.get("PalId")
        level = row.get("Level")
        if not isinstance(skill_ref, str) or not skill_ref:
            raise TypeError(f"{source_id}.WazaID must be a string")
        if not isinstance(character_ref, str) or not character_ref:
            raise TypeError(f"{source_id}.PalId must be a string")
        if not isinstance(level, int) or isinstance(level, bool):
            raise TypeError(f"{source_id}.Level must be an integer")
        try:
            skill_id = by_id[skill_ref.casefold()][0]
        except KeyError as error:
            raise ValueError(
                f"{source_id} references unknown WazaID {skill_ref}"
            ) from error
        try:
            character_id = character_index[character_ref.casefold()]
        except KeyError:
            # The installed master table contains a small set of level rows for
            # characters absent from both authoritative parameter tables. They
            # are not output as learner references or used as validity evidence.
            continue
        learners[skill_id].append({"CharacterID": character_id, "Level": level})
    legal_fruits = set()
    for item_id, row in item_rows.items():
        if row.get("TypeB") != "EPalItemTypeB::ConsumeWazaMachine":
            continue
        if type(row.get("bLegalInGame")) is not bool:
            raise TypeError(f"{item_id}.bLegalInGame must be a bool")
        skill_ref = row.get("WazaID")
        if not isinstance(skill_ref, str) or not skill_ref:
            raise TypeError(f"{item_id}.WazaID must be a string")
        try:
            skill_id = by_id[skill_ref.casefold()][0]
        except KeyError as error:
            raise ValueError(
                f"{item_id} references unknown WazaID {skill_ref}"
            ) from error
        if row["bLegalInGame"]:
            legal_fruits.add(skill_id)
    action_users = {}
    reachable_action_skills = set()
    for evidence in evidence_graph.values():
        for skill_id in evidence.action_declarations:
            action_users.setdefault(skill_id.casefold(), set()).add(
                evidence.character_id
            )
            if evidence.encounter_sources:
                reachable_action_skills.add(skill_id.casefold())
    missing = []
    records = {}
    for skill_id, row in by_id.values():
        for field in ("IgnoreRandomInherit", "DisabledData"):
            if type(row.get(field)) is not bool:
                raise TypeError(f"{skill_id}.{field} must be a bool")
        skill_learners = sorted(
            learners[skill_id],
            key=lambda item: (item["CharacterID"].casefold(), item["Level"]),
        )
        learner_evidence = [
            evidence_graph[item["CharacterID"]] for item in skill_learners
        ]
        reachable = [
            item
            for item in learner_evidence
            if item.acquisition_sources or item.encounter_sources
        ]
        legal_fruit = skill_id in legal_fruits
        disabled = row["DisabledData"]
        non_inheritable = row["IgnoreRandomInherit"]
        action_usage = skill_id.casefold() in reachable_action_skills
        usage = bool(reachable) or legal_fruit or action_usage
        key = f"ACTION_SKILL_{skill_id.partition('::')[2]}"
        complete_i18n = all(
            _text_value(names_by_locale[locale], key) is not None
            and _text_value(descriptions_by_locale[locale], key) is not None
            for locale in LOCALE_DIRECTORIES
        )
        authoritative_name = any(
            _text_value(names_by_locale[locale], key) for locale in LOCALE_DIRECTORIES
        )
        i18n = {}
        for locale in LOCALE_DIRECTORIES:
            name = _text_value(names_by_locale[locale], key)
            if name is None:
                missing.append(f"active:{skill_id}:{locale}:Name:{key}")
                name = _locale_fallback(names_by_locale, key, skill_id)
            description = _text_value(descriptions_by_locale[locale], key)
            if description is None:
                missing.append(f"active:{skill_id}:{locale}:Description:{key}")
                description = _locale_fallback(descriptions_by_locale, key, skill_id)
            i18n[locale] = {
                "Name": _clean_game_text(
                    name, (), {}, missing, f"active:{skill_id}:{locale}:Name"
                ),
                "Description": _clean_game_text(
                    description,
                    (),
                    {},
                    missing,
                    f"active:{skill_id}:{locale}:Description",
                ),
            }
        effects = []
        for index in range(1, 3):
            effect_type = _enum_tail(
                row.get(f"EffectType{index}"), f"{skill_id}.EffectType{index}"
            )
            value = row.get(f"EffectValue{index}")
            extra = row.get(f"EffectValueEx{index}")
            if not _is_number(value) or not _is_number(extra):
                raise TypeError(f"{skill_id}.EffectValue{index} must be numeric")
            if effect_type != "None":
                effects.append(
                    {
                        "EffectType": effect_type,
                        "EffectValue": value,
                        "EffectValueEx": extra,
                    }
                )
        learner_users = {item["CharacterID"] for item in skill_learners}
        boss_learner_users = {
            character_id
            for character_id in learner_users
            if evidence_graph[character_id].variant_tags & {"boss", "tower", "raid"}
        }
        action_user_ids = action_users.get(skill_id.casefold(), set())
        human_learner_users = {
            character_id
            for character_id in learner_users
            if "human" in evidence_graph[character_id].variant_tags
        }
        pal_learner_users = learner_users - human_learner_users
        human_action_users = {
            character_id
            for character_id in action_user_ids
            if "human" in evidence_graph[character_id].variant_tags
        }
        assignable_to_humans = not disabled and bool(
            human_learner_users or human_action_users
        )
        boss_action_users = {
            character_id
            for character_id in action_user_ids
            if evidence_graph[character_id].variant_tags & {"boss", "tower", "raid"}
        }
        level_boss_only = bool(boss_learner_users) and not (
            learner_users - boss_learner_users
        )
        action_boss_only = bool(boss_action_users) and not (
            action_user_ids - boss_action_users
        )
        boss_skill = (level_boss_only or action_boss_only) and not legal_fruit
        if boss_skill:
            invalid = disabled or not complete_i18n or not bool(skill_learners)
            assignable = not invalid
        else:
            invalid = disabled or not authoritative_name or not (
                usage or assignable_to_humans
            )
            assignable = (
                not disabled
                and usage
                and (bool(pal_learner_users) or legal_fruit or not non_inheritable)
            )
        records[skill_id] = {
            "InternalName": skill_id,
            "Element": _enum_tail(row.get("Element"), f"{skill_id}.Element"),
            "CT": row.get("CoolTime"),
            "Power": row.get("Power"),
            "I18n": i18n,
            "UniqueSkill": non_inheritable,
            "Disabled": disabled,
            "NonInheritable": non_inheritable,
            "SkillFruit": legal_fruit,
            "Exclusive": (
                not disabled
                and bool(skill_learners)
                and not non_inheritable
                and not legal_fruit
            ),
            "BossSkill": boss_skill,
            "Assignable": assignable,
            "AssignableToHumans": assignable_to_humans,
            "Invalid": invalid,
            "Category": _enum_tail(row.get("Category"), f"{skill_id}.Category"),
            "Strength": _enum_tail(row.get("Strength"), f"{skill_id}.Strength"),
            "Effects": effects,
            "Learners": skill_learners,
        }
    return records, tuple(sorted(set(missing)))


def _json_document_bytes(rows: dict[str, dict]) -> bytes:
    return (json.dumps(rows, ensure_ascii=False, indent=4) + "\n").encode("utf-8")


def _scenario_source_counts(
    export_root: Path, required_sources: set[str]
) -> dict[str, int]:
    counts = {}
    for path in CHARACTER_SCENARIO_SOURCES.values():
        if path not in required_sources:
            continue
        counts[path] = len(
            load_asset_collection(export_root, path)
            if path in CHARACTER_SCENARIO_PREFIX_SOURCES
            else load_asset(export_root, path)
        )
    return counts


def _evidence_asset_source_counts(
    export_root: Path, evidence: CharacterEvidenceGraph
) -> dict[str, int]:
    return {
        path: len(load_asset(export_root, path))
        for path in evidence.consumed_asset_sources
    }


def build_skills_domain(export_root: Path, policy: dict) -> DomainSnapshot:
    """Build active/passive runtime snapshots from one exported game build."""
    required_sources = set(policy["domains"]["skills"]["required_sources"])
    loaded = {
        name: load_table(export_root, path)
        for name, path in SKILL_SOURCES.items()
        if name != "bp_classes" or path in required_sources
    }
    monster_rows = load_table(export_root, CHARACTER_EVIDENCE_SOURCES["monsters"])
    names = {
        locale: load_text_table(export_root, "DT_SkillNameText_Common", locale)
        for locale in LOCALE_DIRECTORIES
    }
    descriptions = {
        locale: load_text_table(export_root, "DT_SkillDescText_Common", locale)
        for locale in LOCALE_DIRECTORIES
    }
    ui = {
        locale: load_text_table(export_root, "DT_UI_Common_Text_Common", locale)
        for locale in LOCALE_DIRECTORIES
    }
    evidence = build_character_evidence(export_root, policy)
    active, missing_active = build_active_records(
        loaded["waza"],
        loaded["levels"],
        loaded["items"],
        names,
        descriptions,
        evidence,
    )
    passive, missing_passive = build_passive_records(
        loaded["passives"], names, descriptions, ui
    )
    source_counts = {SKILL_SOURCES[name]: len(rows) for name, rows in loaded.items()}
    source_counts[CHARACTER_EVIDENCE_SOURCES["monsters"]] = len(monster_rows)
    source_counts.update(_scenario_source_counts(export_root, required_sources))
    source_counts.update(_evidence_asset_source_counts(export_root, evidence))
    for name, path in CHARACTER_EVIDENCE_SOURCES.items():
        if name == "monsters" or path not in required_sources:
            continue
        source_counts[path] = len(
            load_asset(export_root, path)
            if name == "human_actions"
            else load_table(export_root, path)
        )
    for name, path in CHARACTER_ROUTE_SOURCES.items():
        if path not in required_sources:
            continue
        source_counts[path] = len(
            load_asset(export_root, path)
            if name == "incident_world"
            else load_table(export_root, path)
        )
    for path in RAID_REACHABILITY_SOURCES.values():
        if path in required_sources:
            source_counts[path] = len(load_table(export_root, path))
    for table_name, localized in (
        ("DT_SkillNameText_Common", names),
        ("DT_SkillDescText_Common", descriptions),
        ("DT_UI_Common_Text_Common", ui),
    ):
        for locale, rows in localized.items():
            source_counts[text_table_path(table_name, locale)] = len(rows)
    outputs = {
        "data/pal_attacks.json": _json_document_bytes(active),
        "data/pal_passives.json": _json_document_bytes(passive),
    }
    return snapshot_from_outputs(
        "skills",
        outputs,
        _identity_from_policy(policy),
        domain_policy_hash(policy, "skills"),
        source_counts,
        missing_localizations=tuple(sorted(set(missing_active + missing_passive))),
    )


def _texture_png_path(export_root: Path, virtual_asset_path: str) -> Path:
    json_path = _export_path(export_root, virtual_asset_path)
    return json_path.with_suffix(".png")


def load_character_projection(export_root: Path, policy: dict) -> tuple[dict, dict]:
    """Load exact character sources and return projected records plus counts."""
    source_paths = {
        "monsters": CHARACTER_EVIDENCE_SOURCES["monsters"],
        "humans": CHARACTER_EVIDENCE_SOURCES["humans"],
        "levels": SKILL_SOURCES["levels"],
        "passives": SKILL_SOURCES["passives"],
        "breeding": CHARACTER_ROUTE_SOURCES["breeding"],
        **CHARACTER_SOURCES,
    }
    tables = {
        name: load_table(export_root, path) for name, path in source_paths.items()
    }
    texts = {
        name: {
            locale: load_text_table(export_root, table_name, locale)
            for locale in LOCALE_DIRECTORIES
        }
        for name, table_name in CHARACTER_TEXT_TABLES.items()
    }
    evidence = build_character_evidence(export_root, policy, "characters")
    built = build_character_records(tables, texts, evidence)
    source_counts = {path: len(tables[name]) for name, path in source_paths.items()}
    for name, table_name in CHARACTER_TEXT_TABLES.items():
        for locale, rows in texts[name].items():
            source_counts[text_table_path(table_name, locale)] = len(rows)
    required_sources = policy["domains"]["characters"]["required_sources"]
    if not isinstance(required_sources, list):
        raise TypeError("characters required_sources must be a list")
    asset_sources = {
        CHARACTER_EVIDENCE_SOURCES["human_actions"],
        CHARACTER_ROUTE_SOURCES["incident_world"],
        *(
            path
            for path in CHARACTER_SCENARIO_SOURCES.values()
            if path not in CHARACTER_SCENARIO_PREFIX_SOURCES
        ),
    }
    source_counts.update(_scenario_source_counts(export_root, set(required_sources)))
    source_counts.update(_evidence_asset_source_counts(export_root, evidence))
    for path in required_sources:
        if path not in source_counts:
            source_counts[path] = len(
                load_asset(export_root, path)
                if path in asset_sources
                else load_table(export_root, path)
            )
    return built, source_counts


def build_characters_domain(export_root: Path, policy: dict) -> DomainSnapshot:
    """Build character, human, skin, and referenced-icon runtime snapshots."""
    built, source_counts = load_character_projection(export_root, policy)
    outputs = {}
    icon_dimensions = {}
    for output_path, source_path in built["icon_sources"].items():
        path = _texture_png_path(export_root, source_path)
        if not path.is_file():
            icon_key = PurePosixPath(output_path).stem
            if output_path.startswith("icons/pals/skin/"):
                for skin in built["skins"].values():
                    if skin["IconKey"] == icon_key:
                        skin["Invalid"] = True
                built["missing_icons"] = tuple(
                    sorted({*built["missing_icons"], output_path})
                )
            else:
                for group, fallback in (
                    (built["pals"], "unknown"),
                    (built["humans"], "Human"),
                ):
                    for record in group.values():
                        if record["IconKey"] == icon_key:
                            record["IconKey"] = fallback
                            if "HasIcon" in record:
                                record["HasIcon"] = False
            continue
        data = path.read_bytes()
        outputs[output_path] = data
        icon_dimensions[output_path] = _png_dimensions(data)
    outputs.update(
        {
            "data/pal_data.json": _json_document_bytes(built["pals"]),
            "data/human_data.json": _json_document_bytes(built["humans"]),
            "data/skin_data.json": _json_document_bytes(built["skins"]),
        }
    )
    return snapshot_from_outputs(
        "characters",
        outputs,
        _identity_from_policy(policy),
        domain_policy_hash(policy, "characters"),
        source_counts,
        icon_dimensions=icon_dimensions,
        missing_localizations=built["missing_localizations"],
        missing_icons=built["missing_icons"],
    )


def _progression_integer(row: dict, field: str, row_id: str) -> int:
    value = row.get(field)
    if type(value) is not int:
        raise ValueError(f"{row_id}.{field} must be an integer")
    return value


_PLAYER_STAT_DEFINITIONS = {
    "最大HP": ("AddMaxHPPerStatusPoint", "stat-health", "flat"),
    "最大SP": ("AddMaxSPPerStatusPoint", "stat-stamina", "flat"),
    "攻撃力": ("AddPowerPerStatusPoint", "stat-attack", "percent"),
    "所持重量": ("AddMaxInventoryWeightPerStatusPoint", "stat-weight", "flat"),
    "作業速度": ("AddWorkSpeedPerStatusPoint", "stat-work-speed", "flat"),
}
_PLAYER_RELIC_DEFINITIONS = {
    "CapturePower": ("捕獲率", "ability-capture", "rank"),
    "HungerReduction": ("空腹率低減", "ability-hunger", "percent"),
    "SwimSpeed": ("泳ぎ速度", "ability-swim", "percent"),
    "FoodDecayReduction": ("食料腐敗低減", "ability-food-decay", "percent"),
    "JumpPower": ("ジャンプ力", "ability-jump", "percent"),
    "ClimbSpeed": ("崖登り速度", "ability-climb", "percent"),
    "StatusAilmentResist": ("状態異常耐性", "ability-status-resist", "percent"),
    "StaminaReduction": ("スタミナ消費軽減", "ability-stamina-cost", "percent"),
    "SphereHoming": ("パルスフィアホーミング", "ability-sphere-homing", "percent"),
    "MoveSpeed": ("移動速度アップ", "ability-move-speed", "percent"),
    "GliderSpeed": ("滑空速度", "ability-glider-speed", "percent"),
    "ExpBonus": ("経験値ボーナス", "ability-exp", "percent"),
    "RainbowPassiveRate": ("虹パッシブ率", "ability-rainbow", "percent"),
}
_PLAYER_STATUS_ORDER = (
    "最大HP",
    "最大SP",
    "攻撃力",
    "所持重量",
    "捕獲率",
    "作業速度",
    "空腹率低減",
    "泳ぎ速度",
    "食料腐敗低減",
    "ジャンプ力",
    "崖登り速度",
    "状態異常耐性",
    "スタミナ消費軽減",
    "パルスフィアホーミング",
    "移動速度アップ",
    "滑空速度",
    "経験値ボーナス",
    "虹パッシブ率",
)


def _game_setting_properties(exports: list[dict]) -> dict:
    matches = [
        item.get("Properties")
        for item in exports
        if item.get("Name") == "Default__BP_PalGameSetting_C"
        and isinstance(item.get("Properties"), dict)
    ]
    if len(matches) != 1:
        raise ValueError("BP_PalGameSetting must contain exactly one default object")
    return matches[0]


def _player_status_projection(export_root: Path) -> dict[str, dict]:
    settings = _game_setting_properties(
        load_asset(export_root, PROGRESSION_SOURCES["game_setting"])
    )
    projected = {}
    for name, (field, icon, unit) in _PLAYER_STAT_DEFINITIONS.items():
        increment = settings.get(field)
        if not _is_number(increment) or increment <= 0:
            raise ValueError(f"BP_PalGameSetting.{field} must be positive numeric")
        projected[name] = {
            "category": "stat",
            "icon": icon,
            "maximum": 50,
            "source": field,
            "unit": unit,
            "values": [rank * increment for rank in range(51)],
        }

    grouped: dict[str, list[dict]] = {}
    for row_id, row in load_table(
        export_root, PROGRESSION_SOURCES["player_status"]
    ).items():
        relic_type = row.get("RelicType")
        if not isinstance(relic_type, str) or "::" not in relic_type:
            raise ValueError(f"{row_id}.RelicType must be an EPalRelicType value")
        grouped.setdefault(relic_type.rsplit("::", 1)[1], []).append(row)
    if set(grouped) != set(_PLAYER_RELIC_DEFINITIONS):
        raise ValueError("player status table relic types do not match the supported set")
    for relic_type, (name, icon, unit) in _PLAYER_RELIC_DEFINITIONS.items():
        rows = sorted(grouped[relic_type], key=lambda row: row.get("Rank", -1))
        ranks = [row.get("Rank") for row in rows]
        if ranks != list(range(1, len(rows) + 1)):
            raise ValueError(f"{relic_type} ranks must be contiguous from 1")
        rates = [row.get("EffectRate") for row in rows]
        if any(not _is_number(rate) for rate in rates):
            raise ValueError(f"{relic_type}.EffectRate must be numeric")
        projected[name] = {
            "category": "effigy",
            "icon": icon,
            "maximum": len(rows),
            "source": f"EPalRelicType::{relic_type}",
            "unit": unit,
            "values": [0, *ranks] if unit == "rank" else [0, *rates],
        }
    return {name: projected[name] for name in _PLAYER_STATUS_ORDER}


def build_progression_domain(export_root: Path, policy: dict) -> DomainSnapshot:
    """Project the exact progression rows and player upgrade limits used by saves."""
    experience_source = load_table(export_root, PROGRESSION_SOURCES["experience"])
    friendship_source = load_table(export_root, PROGRESSION_SOURCES["friendship"])
    experience = {}
    for level, row in sorted(experience_source.items()):
        if str(int(level)) != level:
            raise ValueError(f"experience level key must be canonical integer: {level}")
        experience[level] = {
            field: _progression_integer(row, field, level)
            for field in _PAL_EXP_FIELDS
        }
    friendship = {}
    for row_id, row in friendship_source.items():
        rank = _progression_integer(row, "FriendshipRank", row_id)
        required = _progression_integer(row, "RequiredPoint", row_id)
        key = str(rank)
        if key in friendship:
            raise ValueError(f"duplicate FriendshipRank {rank}")
        friendship[key] = {"required_point": required}
    friendship = dict(sorted(friendship.items()))
    outputs = {
        "data/pal_exp_table.json": _json_document_bytes(experience),
        "data/pal_friendship.json": _json_document_bytes(friendship),
        "data/player_status_data.json": _json_document_bytes(
            _player_status_projection(export_root)
        ),
    }
    return snapshot_from_outputs(
        "progression",
        outputs,
        _identity_from_policy(policy),
        domain_policy_hash(policy, "progression"),
        {
            PROGRESSION_SOURCES["experience"]: len(experience_source),
            PROGRESSION_SOURCES["friendship"]: len(friendship_source),
            PROGRESSION_SOURCES["player_status"]: len(
                load_table(export_root, PROGRESSION_SOURCES["player_status"])
            ),
            PROGRESSION_SOURCES["game_setting"]: len(
                load_asset(export_root, PROGRESSION_SOURCES["game_setting"])
            ),
        },
    )


_TECHNOLOGY_SOURCE_FIELDS = frozenset(
    {
        "UnlockBuildObjects",
        "UnlockItemRecipes",
        "Name",
        "Description",
        "IconName",
        "RequireDefeatTowerBoss",
        "RequireTechnology",
        "RequireResearchId",
        "IsBossTechnology",
        "LevelCap",
        "Tier",
        "Cost",
    }
)
_TECHNOLOGY_PLACEHOLDER = re.compile(
    r"<(itemName|mapObjectName|characterName|uiCommon|img) "
    r"id=\|([^|]+)\|(?:\s+[^>]*)?/>",
    re.IGNORECASE,
)
_TECHNOLOGY_SEMANTIC_MARKUP = re.compile(
    r"<(?:itemName|mapObjectName|characterName|uiCommon)\b", re.IGNORECASE
)


def _technology_item_name_key(item_id: str, items: dict[str, dict]) -> str:
    item = items.get(item_id, {})
    override = item.get("OverrideName")
    return (
        override
        if isinstance(override, str) and override.casefold() != "none"
        else f"ITEM_NAME_{item_id}"
    )


def _technology_text(
    tables: dict[str, dict[str, dict]],
    table_names: tuple[str, ...],
    key: str,
    locale: str,
    fallback: str,
) -> tuple[str, bool]:
    def lookup(selected: str) -> str | None:
        for name in table_names:
            rows = tables[name][selected]
            value = _text_value(rows, key)
            if value is None:
                folded = key.casefold()
                actual = next((row_id for row_id in rows if row_id.casefold() == folded), None)
                value = _text_value(rows, actual) if actual is not None else None
            if value is not None:
                return value
        return None

    value = lookup(locale)
    if value is not None:
        return value, False
    return next((value for lang in ("en", "ja") if (value := lookup(lang))), fallback), True


def _expand_technology_text(
    text: str,
    locale: str,
    texts: dict[str, dict[str, dict]],
    items: dict[str, dict],
    missing: list[str],
    label: str,
) -> str:
    item_index = casefold_index(items)

    def replace(match: re.Match) -> str:
        kind, source_id = match.groups()
        kind = kind.casefold()
        if kind == "img":
            return ""
        if kind == "itemname":
            item_id = item_index.get(source_id.casefold(), source_id)
            key = _technology_item_name_key(item_id, items)
            tables = ("items",)
        elif kind == "mapobjectname":
            key = f"MAPOBJECT_NAME_{source_id}"
            tables = ("buildings",)
        elif kind == "charactername":
            key = f"PAL_NAME_{source_id}"
            tables = ("pals",)
        else:
            key = source_id
            tables = ("ui",)
        value, absent = _technology_text(texts, tables, key, locale, source_id)
        if absent:
            missing.append(f"{label}:{locale}:placeholder:{key}")
        return value

    expanded = " ".join(_TECHNOLOGY_PLACEHOLDER.sub(replace, text).split())
    if match := _TECHNOLOGY_SEMANTIC_MARKUP.search(expanded):
        raise ValueError(f"Unresolved technology markup in {label}:{locale}: {match.group()}")
    return expanded


def build_technology_records(
    tables: dict[str, dict[str, dict]],
    texts: dict[str, dict[str, dict[str, dict]]],
    character_icon_keys: dict[str, str],
) -> dict:
    """Build technology rows and logical icon sources from exported tables."""
    if set(tables) != set(TECHNOLOGY_SOURCES):
        raise ValueError("Technology source tables are incomplete or unexpected")
    if set(texts) != set(TECHNOLOGY_TEXT_TABLES) or any(
        set(locales) != set(LOCALE_DIRECTORIES) for locales in texts.values()
    ):
        raise ValueError("Technology localization must contain exactly 17 locales")

    technologies = tables["technology"]
    items = tables["items"]
    indexes = {
        name: casefold_index(rows)
        for name, rows in tables.items()
        if name != "technology"
    }
    character_index = casefold_index({key: {} for key in character_icon_keys})
    records = {}
    icon_sources = {}
    missing = []
    diagnostics = []

    for technology_id, row in sorted(technologies.items()):
        if set(row) != _TECHNOLOGY_SOURCE_FIELDS:
            raise ValueError(
                f"{technology_id} technology fields are incomplete or unexpected"
            )
        unlock_items = row["UnlockItemRecipes"]
        unlock_buildings = row["UnlockBuildObjects"]
        if (
            not isinstance(unlock_items, list)
            or any(not isinstance(value, str) or not value for value in unlock_items)
            or not isinstance(unlock_buildings, list)
            or any(
                not isinstance(value, str) or not value for value in unlock_buildings
            )
            or bool(unlock_items) is bool(unlock_buildings)
        ):
            raise ValueError(
                f"{technology_id} must unlock exactly one of items or build objects"
            )

        resolved_items = []
        for item_id in unlock_items:
            canonical = indexes["items"].get(item_id.casefold())
            if canonical is None:
                diagnostics.append(
                    {
                        "Kind": "unresolved-item",
                        "TechnologyID": technology_id,
                        "Field": "UnlockItems",
                        "TargetID": item_id,
                    }
                )
            else:
                resolved_items.append(canonical)

        icon_name = _source_string(row, "IconName", technology_id)
        pal_gear = [
            item_id
            for item_id in resolved_items
            if items[item_id].get("TypeB") == "EPalItemTypeB::Essential_PalGear"
        ]
        if pal_gear:
            if any(items[item_id].get("bLegalInGame") is not True for item_id in pal_gear):
                raise ValueError(
                    f"{technology_id} Essential_PalGear must have bLegalInGame=true"
                )
            pal_icon_id = indexes["pal_icons"].get(icon_name.casefold())
            if pal_icon_id is None:
                raise ValueError(
                    f"{technology_id} Pal gear IconName does not resolve: {icon_name}"
                )
            character_id = character_index.get(pal_icon_id.casefold())
            if character_id is None:
                raise ValueError(
                    f"{technology_id} Pal gear has no character IconKey: {pal_icon_id}"
                )
            unlock_pal = character_icon_keys[character_id]
            icon_kind = "pal"
            icon_key = unlock_pal
        else:
            unlock_pal = ""
            table_name = "build_icons" if unlock_buildings else "item_icons"
            candidates = [icon_name, *(unlock_buildings or unlock_items)]
            candidates.extend(
                items[item_id].get("IconName")
                for item_id in resolved_items
                if isinstance(items[item_id].get("IconName"), str)
            )
            icon_id = next(
                (
                    indexes[table_name][candidate.casefold()]
                    for candidate in candidates
                    if candidate.casefold() in indexes[table_name]
                ),
                None,
            )
            if icon_id is None:
                raise ValueError(f"{technology_id} icon does not resolve: {icon_name}")
            icon_kind = "building" if unlock_buildings else "item"
            icon_key = technology_id
            icon_sources[f"icons/tech/{technology_id}.png"] = _texture_virtual_path(
                tables[table_name][icon_id],
                f"{technology_id}:{icon_id}",
                "SoftIcon" if table_name == "build_icons" else "Icon",
            )

        name_fallback_id = (unlock_buildings or unlock_items)[0]
        fallback_name_key = (
            f"MAPOBJECT_NAME_{name_fallback_id}"
            if unlock_buildings
            else _technology_item_name_key(name_fallback_id, items)
        )
        fallback_name_table = "buildings" if unlock_buildings else "items"
        type_key = (
            "TECHNOLOGY_CATEGOFY_BUILDING"
            if unlock_buildings
            else "TECHNOLOGY_CATEGOFY_ITEM"
        )
        i18n = {}
        for locale in LOCALE_DIRECTORIES:
            name, name_absent = _technology_text(
                texts, ("names",), row["Name"], locale, ""
            )
            if not name:
                name, fallback_absent = _technology_text(
                    texts,
                    (fallback_name_table,),
                    fallback_name_key,
                    locale,
                    technology_id,
                )
                name_absent = name_absent or fallback_absent
            description, description_absent = _technology_text(
                texts,
                ("descriptions", "item_descriptions", "building_descriptions"),
                row["Description"],
                locale,
                row["Description"],
            )
            if name_absent:
                missing.append(
                    f"technology:{technology_id}:{locale}:Name:{row['Name']}"
                )
            if description_absent:
                missing.append(
                    f"technology:{technology_id}:{locale}:Description:{row['Description']}"
                )
            type_name, type_absent = _technology_text(
                texts,
                ("ui",),
                type_key,
                locale,
                "Structures" if unlock_buildings else "Items",
            )
            if type_absent:
                missing.append(
                    f"technology:{technology_id}:{locale}:Type:{type_key}"
                )
            i18n[locale] = {
                "Name": _expand_technology_text(
                    name, locale, texts, items, missing, f"technology:{technology_id}:Name"
                ),
                "Description": _expand_technology_text(
                    description,
                    locale,
                    texts,
                    items,
                    missing,
                    f"technology:{technology_id}:Description",
                ),
                "Type": type_name,
            }

        english_type = i18n["en"]["Type"]
        source_differs = any(
            (value := _text_value(texts["ui"][locale], type_key)) is not None
            and value != english_type
            for locale in LOCALE_DIRECTORIES
            if locale != "en"
        )
        if source_differs and all(
            localized["Type"] == english_type
            for locale, localized in i18n.items()
            if locale != "en"
        ):
            raise ValueError(
                f"{technology_id} technology Type localization collapsed to English"
            )

        boss = _source_string(row, "RequireDefeatTowerBoss", technology_id)
        prerequisite = _source_string(row, "RequireTechnology", technology_id)
        research = _source_string(row, "RequireResearchId", technology_id)
        records[technology_id] = {
            "InternalName": technology_id,
            "Level": _progression_integer(row, "LevelCap", technology_id),
            "Tier": _progression_integer(row, "Tier", technology_id),
            "Cost": _progression_integer(row, "Cost", technology_id),
            "BossTechnology": _source_bool(row, "IsBossTechnology", technology_id),
            "Requirements": {
                "DefeatTowerBoss": (
                    "" if boss == "EPalBossType::None" else _enum_tail(boss, technology_id)
                ),
                "ResearchID": "" if research.casefold() == "none" else research,
            },
            "Prerequisites": (
                [] if prerequisite.casefold() == "none" else [prerequisite]
            ),
            "UnlockItems": list(unlock_items),
            "UnlockBuildObjects": list(unlock_buildings),
            "UnlockPalSkill": unlock_pal,
            "IconKind": icon_kind,
            "IconKey": icon_key,
            "I18n": i18n,
        }
    return {
        "records": records,
        "icon_sources": dict(sorted(icon_sources.items())),
        "missing_localizations": tuple(sorted(set(missing))),
        "diagnostics": tuple(diagnostics),
    }


def load_technology_projection(export_root: Path) -> tuple[dict, dict]:
    tables = {
        name: load_table(export_root, path) for name, path in TECHNOLOGY_SOURCES.items()
    }
    texts = {
        name: {
            locale: load_text_table(export_root, table_name, locale)
            for locale in LOCALE_DIRECTORIES
        }
        for name, table_name in TECHNOLOGY_TEXT_TABLES.items()
    }
    character_icon_keys = {row_id: row_id for row_id in tables["characters"]}
    built = build_technology_records(tables, texts, character_icon_keys)
    source_counts = {
        path: len(tables[name]) for name, path in TECHNOLOGY_SOURCES.items()
    }
    for name, table_name in TECHNOLOGY_TEXT_TABLES.items():
        for locale, rows in texts[name].items():
            source_counts[text_table_path(table_name, locale)] = len(rows)
    return built, source_counts


def build_technology_domain(export_root: Path, policy: dict) -> DomainSnapshot:
    built, source_counts = load_technology_projection(export_root)
    outputs = {}
    icon_dimensions = {}
    for output_path, source_path in built["icon_sources"].items():
        data = _texture_png_path(export_root, source_path).read_bytes()
        outputs[output_path] = data
        icon_dimensions[output_path] = _png_dimensions(data)
    outputs["data/tech_data.json"] = _json_document_bytes(built["records"])
    return snapshot_from_outputs(
        "technology",
        outputs,
        _identity_from_policy(policy),
        domain_policy_hash(policy, "technology"),
        source_counts,
        icon_dimensions=icon_dimensions,
        missing_localizations=built["missing_localizations"],
        diagnostics=built["diagnostics"],
    )


DOMAIN_BUILDERS["skills"] = build_skills_domain
DOMAIN_BUILDERS["characters"] = build_characters_domain
DOMAIN_BUILDERS["progression"] = build_progression_domain
DOMAIN_BUILDERS["technology"] = build_technology_domain


def casefold_index(rows: dict[str, dict]) -> dict[str, str]:
    index: dict[str, str] = {}
    for key in rows:
        folded = key.casefold()
        if folded in index and index[folded] != key:
            raise ValueError(f"Case-insensitive ID collision: {index[folded]} / {key}")
        index[folded] = key
    return index


def domain_policy_hash(policy: dict, domain: str) -> str:
    try:
        domain_policy = policy["domains"][domain]
    except (KeyError, TypeError) as error:
        raise ValueError(f"Missing policy for domain {domain}") from error
    encoded = json.dumps(
        domain_policy, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _identity_from_policy(policy: dict) -> BuildIdentity:
    try:
        bootstrap = policy["bootstrap"]
        return BuildIdentity(
            str(bootstrap["game_build"]),
            str(bootstrap["uex_revision"]),
            str(bootstrap["mapping_sha256"]),
        )
    except (KeyError, TypeError) as error:
        raise ValueError("Policy bootstrap identity is incomplete") from error


def _json_rows(data: bytes, path: str) -> dict[str, dict]:
    try:
        rows = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{path}: invalid JSON: {error}") from error
    if not isinstance(rows, dict) or any(
        not isinstance(key, str) or not isinstance(row, dict)
        for key, row in rows.items()
    ):
        raise ValueError(f"{path}: expected an object of named row objects")
    return rows


def _references(path: str, rows: dict[str, dict]) -> tuple[Reference, ...]:
    references = []
    for row_id, row in rows.items():
        if path in ("data/pal_data.json", "data/human_data.json"):
            for field in ("FamilyID", "PaldeckRecordID"):
                if field == "FamilyID" and row.get("FamilyResolved") is not True:
                    continue
                if isinstance(target := row.get(field), str) and target:
                    references.append(
                        Reference(path, row_id, field, "characters", target)
                    )
            references.extend(
                Reference(path, row_id, "DefaultPassives", "passives", target)
                for target in row.get("DefaultPassives", [])
                if isinstance(target, str)
            )
            references.extend(
                Reference(path, row_id, "Attacks", "skills", target)
                for target in (
                    row.get("Attacks", {})
                    if isinstance(row.get("Attacks"), dict)
                    else {}
                )
                if isinstance(target, str)
            )
        elif path == "data/skin_data.json":
            if isinstance(target := row.get("TargetPalName"), str) and target:
                references.append(
                    Reference(path, row_id, "TargetPalName", "characters", target)
                )
        elif path == "data/pal_attacks.json":
            references.extend(
                Reference(
                    path,
                    row_id,
                    "Learners.CharacterID",
                    "characters",
                    target,
                )
                for learner in row.get("Learners", [])
                if isinstance(learner, dict)
                and isinstance(target := learner.get("CharacterID"), str)
                and target
            )
        elif path == "data/tech_data.json":
            if isinstance(target := row.get("UnlockPalSkill"), str) and target:
                references.append(
                    Reference(path, row_id, "UnlockPalSkill", "characters", target)
                )
    return tuple(references)


def _derive_inventory(
    outputs: dict[str, bytes],
) -> tuple[dict[str, frozenset[str]], tuple[Reference, ...]]:
    ids: dict[str, set[str]] = {}
    references = []
    for path, data in outputs.items():
        if not path.endswith(".json"):
            continue
        rows = _json_rows(data, path)
        if kind := _OUTPUT_KINDS.get(path):
            ids.setdefault(kind, set()).update(rows)
        references.extend(_references(path, rows))
    return (
        {kind: frozenset(values) for kind, values in ids.items()},
        tuple(
            sorted(
                references,
                key=lambda item: (
                    item.source_path,
                    item.source_id,
                    item.field,
                    item.target_kind,
                    item.target_id,
                ),
            )
        ),
    )


def snapshot_from_outputs(
    domain: str,
    outputs: dict[str, bytes],
    identity: BuildIdentity,
    policy_sha256: str,
    source_counts: dict[str, int],
    *,
    icon_dimensions: dict[str, tuple[int, int]] | None = None,
    missing_references: tuple[str, ...] = (),
    missing_localizations: tuple[str, ...] = (),
    missing_icons: tuple[str, ...] = (),
    diagnostics: tuple[dict[str, str], ...] = (),
) -> DomainSnapshot:
    output_counts = {}
    for path, data in outputs.items():
        if path.endswith(".json"):
            rows = _json_rows(data, path)
            output_counts[path] = len(rows)
        else:
            output_counts[path] = 1
    ids, references = _derive_inventory(outputs)
    return DomainSnapshot(
        domain=domain,
        outputs=dict(outputs),
        identity=identity,
        policy_sha256=policy_sha256,
        source_counts=dict(source_counts),
        output_counts=output_counts,
        references=references,
        ids=ids,
        missing_references=tuple(missing_references),
        missing_localizations=tuple(missing_localizations),
        missing_icons=tuple(missing_icons),
        hashes={
            path: hashlib.sha256(data).hexdigest() for path, data in outputs.items()
        },
        icon_dimensions=dict(icon_dimensions or {}),
        diagnostics=tuple(diagnostics),
    )


def candidate_manifest(candidate: DomainSnapshot) -> DomainManifest:
    return DomainManifest(
        game_build=candidate.identity.game_build,
        parser_revision=candidate.identity.parser_revision,
        mapping_sha256=candidate.identity.mapping_sha256,
        policy_sha256=candidate.policy_sha256,
        source_counts=dict(candidate.source_counts),
        output_counts=dict(candidate.output_counts),
        output_hashes=dict(candidate.hashes),
        missing_references=tuple(candidate.missing_references),
        missing_localizations=tuple(candidate.missing_localizations),
        missing_icons=tuple(candidate.missing_icons),
        managed_paths=tuple(sorted(candidate.outputs)),
    )


def _png_dimensions(data: bytes) -> tuple[int, int]:
    if not data.startswith(_PNG_SIGNATURE):
        raise ValueError("PNG signature is invalid")
    position = len(_PNG_SIGNATURE)
    header = None
    compressed = bytearray()
    ended = False
    while position < len(data):
        if position + 12 > len(data):
            raise ValueError("PNG decode failed: truncated chunk")
        length = struct.unpack(">I", data[position : position + 4])[0]
        end = position + 12 + length
        if end > len(data):
            raise ValueError("PNG decode failed: truncated payload")
        kind = data[position + 4 : position + 8]
        payload = data[position + 8 : position + 8 + length]
        expected_crc = struct.unpack(">I", data[position + 8 + length : end])[0]
        if zlib.crc32(kind + payload) & 0xFFFFFFFF != expected_crc:
            raise ValueError("PNG decode failed: chunk CRC mismatch")
        if kind == b"IHDR":
            if header is not None or len(payload) != 13:
                raise ValueError("PNG decode failed: invalid IHDR")
            header = struct.unpack(">IIBBBBB", payload)
        elif kind == b"IDAT":
            compressed.extend(payload)
        elif kind == b"IEND":
            ended = True
            break
        position = end
    if header is None or not compressed or not ended:
        raise ValueError("PNG decode failed: required chunk missing")
    width, height, bit_depth, color_type, compression, filtering, interlace = header
    if not width or not height or compression or filtering or interlace:
        raise ValueError("PNG decode failed: unsupported header")
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color_type)
    if channels is None or bit_depth != 8:
        raise ValueError("PNG decode failed: unsupported pixel format")
    try:
        decoded = zlib.decompress(bytes(compressed))
    except zlib.error as error:
        raise ValueError(f"PNG decode failed: {error}") from error
    row_size = 1 + width * channels
    if len(decoded) != height * row_size or any(
        decoded[offset] > 4 for offset in range(0, len(decoded), row_size)
    ):
        raise ValueError("PNG decode failed: invalid scanlines")
    return width, height


def _canonical_output_path(path: str) -> bool:
    relative = PurePosixPath(path)
    return bool(
        path
        and "\\" not in path
        and path == relative.as_posix()
        and not relative.is_absolute()
        and all(
            part not in ("", ".", "..") and ":" not in part for part in relative.parts
        )
    )


def _normalized_managed_path(path: str) -> PurePosixPath:
    if not isinstance(path, str):
        raise TypeError(f"Managed path must be a string: {path!r}")
    relative = PurePosixPath(path)
    if (
        not _canonical_output_path(path)
        or path != relative.as_posix()
        or not relative.parts
    ):
        raise ValueError(f"Managed path is not canonical and relative: {path!r}")
    return relative


def _is_link(path: Path) -> bool:
    return path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction())


def _safe_file_target(root: Path, path: str) -> Path:
    relative = _normalized_managed_path(path)
    root = Path(root)
    if _is_link(root) or not root.is_dir():
        raise ValueError(f"Asset root must be a real directory: {root}")
    resolved_root = root.resolve()
    current = root
    for part in relative.parts[:-1]:
        current /= part
        if _is_link(current):
            raise ValueError(f"Managed path crosses a symlink/reparse point: {path}")
        if current.exists() and not current.is_dir():
            raise ValueError(f"Managed path parent is not a directory: {path}")
    target = root.joinpath(*relative.parts)
    if _is_link(target):
        raise ValueError(f"Managed path is a symlink/reparse point: {path}")
    if target.exists() and not target.is_file():
        raise ValueError(f"Managed path target is not a file: {path}")
    if not target.resolve(strict=False).is_relative_to(resolved_root):
        raise ValueError(f"Managed path escapes asset root: {path}")
    return target


def _actual_relative_case(root: Path, path: str) -> str | None:
    relative = _normalized_managed_path(path)
    current = Path(root)
    actual = []
    for part in relative.parts:
        if not current.is_dir() or _is_link(current):
            return None
        matches = [
            child for child in current.iterdir() if child.name.casefold() == part.casefold()
        ]
        if len(matches) > 1:
            raise ValueError(f"Ambiguous casefold path in asset root: {path}")
        if not matches:
            return None
        current = matches[0]
        actual.append(current.name)
    if not current.is_file() or _is_link(current):
        return None
    return PurePosixPath(*actual).as_posix()


def _validate_manifest_paths(manifest: Manifest, assets: Path) -> None:
    if manifest.schema_version != 1 or not isinstance(manifest.bootstrap, dict):
        raise ValueError("Manifest schema version/bootstrap is invalid")
    seen = {}
    for domain, entry in manifest.domains.items():
        if domain not in DOMAIN_NAMES:
            raise ValueError(f"Unknown manifest domain: {domain}")
        if set(entry.output_hashes) != set(entry.managed_paths):
            raise ValueError(f"{domain}: managed paths and output hashes differ")
        for path in entry.managed_paths:
            _safe_file_target(assets, path)
            folded = path.casefold()
            if previous := seen.get(folded):
                raise ValueError(
                    f"Duplicate/casefold managed path: {previous} / {path}"
                )
            seen[folded] = path


def _legacy_path_allowed(path: str) -> bool:
    try:
        parts = _normalized_managed_path(path).parts
    except ValueError:
        return False
    return bool(
        (len(parts) == 3 and parts[:2] in (("icons", "pals"), ("icons", "tech")))
        or (len(parts) == 4 and parts[:3] == ("icons", "pals", "skin"))
    ) and parts[-1].endswith(".png")


def _legacy_domain_owns(domain: str, path: str) -> bool:
    parts = _normalized_managed_path(path).parts
    if domain == "characters":
        return parts[:2] == ("icons", "pals")
    if domain == "technology":
        return parts[:2] == ("icons", "tech")
    return False


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _legacy_plan_hash(accepted: list[dict[str, str]]) -> str:
    encoded = json.dumps(
        accepted, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return _sha256_bytes(encoded)


def _backup_inventory(backup: Path) -> tuple[dict[str, str], str]:
    inventory = {}
    for path in sorted(Path(backup).rglob("*")):
        if path.is_dir() and not _is_link(path):
            continue
        relative = path.relative_to(backup).as_posix()
        _normalized_managed_path(relative)
        inventory[relative] = (
            f"link:{os.readlink(path)}" if _is_link(path) else _file_sha256(path)
        )
    encoded = json.dumps(
        inventory, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return inventory, _sha256_bytes(encoded)


def build_legacy_ownership_candidate(
    repo: Path,
    assets: Path,
    backup: Path,
    baseline_commit: str,
) -> dict:
    repo = Path(repo).resolve()
    assets = Path(assets)
    backup = Path(backup)
    if not repo.is_dir() or not assets.is_dir() or not backup.is_dir():
        raise ValueError("Repository, assets, and backup roots must be directories")
    if _is_link(assets) or _is_link(backup):
        raise ValueError("Assets and backup roots must not be symlinks")
    try:
        assets_prefix = assets.resolve().relative_to(repo).as_posix()
    except ValueError as error:
        raise ValueError("Assets must be contained by the repository") from error
    archive = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "archive",
            "--format=tar",
            baseline_commit,
            "--",
            f"{assets_prefix}/icons/pals",
            f"{assets_prefix}/icons/tech",
        ],
        check=True,
        capture_output=True,
    ).stdout
    baseline_files = {}
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tar:
        for member in tar.getmembers():
            prefix = f"{assets_prefix}/"
            if not member.isfile() or not member.name.startswith(prefix):
                continue
            relative = member.name[len(prefix) :]
            if not _legacy_path_allowed(relative):
                continue
            source = tar.extractfile(member)
            if source is None:
                continue
            baseline_files[relative] = source.read()
    backup_inventory, backup_inventory_hash = _backup_inventory(backup)
    accepted = []
    rejected = []
    for relative, baseline_data in sorted(baseline_files.items()):
        baseline_hash = _sha256_bytes(baseline_data)
        try:
            current = _safe_file_target(assets, relative)
            saved = _safe_file_target(backup, relative)
        except ValueError as error:
            rejected.append({"path": relative, "reason": str(error)})
            continue
        if not current.is_file() or not saved.is_file():
            rejected.append({"path": relative, "reason": "missing regular file"})
        elif _file_sha256(current) != baseline_hash:
            rejected.append({"path": relative, "reason": "current hash differs"})
        elif _file_sha256(saved) != baseline_hash:
            rejected.append({"path": relative, "reason": "backup hash differs"})
        else:
            accepted.append({"path": relative, "sha256": baseline_hash})
    return {
        "schema_version": 1,
        "baseline_commit": baseline_commit,
        "backup_root": str(backup.resolve()),
        "backup_inventory_sha256": backup_inventory_hash,
        "backup_file_count": len(backup_inventory),
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "accepted": accepted,
        "rejected": rejected,
        "plan_sha256": _legacy_plan_hash(accepted),
        "review_approval": None,
    }


def write_legacy_ownership_candidate(path: Path, candidate: dict) -> None:
    if not isinstance(candidate, dict) or candidate.get("review_approval") is not None:
        raise ValueError("Legacy candidate artifact must remain unapproved")
    path = Path(path)
    if _is_link(path) or (path.exists() and not path.is_file()):
        raise ValueError(f"Legacy candidate target must be a regular file: {path}")
    if _is_link(path.parent) or not path.parent.is_dir():
        raise ValueError(
            f"Legacy candidate parent must be a real directory: {path.parent}"
        )
    encoded = (
        json.dumps(candidate, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    with tempfile.TemporaryDirectory(
        prefix="legacy-ownership-candidate-", dir=path.parent
    ) as directory:
        staged = Path(directory) / path.name
        staged.write_bytes(encoded)
        os.replace(staged, path)


def _read_json_artifact(path: Path, label: str) -> tuple[dict, str]:
    path = Path(path)
    if _is_link(path) or not path.is_file():
        raise ValueError(f"{label} must be a real file: {path}")
    data = path.read_bytes()
    try:
        document = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} is invalid JSON: {error}") from error
    if not isinstance(document, dict):
        raise TypeError(f"{label} must be a JSON object")
    return document, _sha256_bytes(data)


def _legacy_scope_counts(accepted: list[dict[str, str]]) -> dict[str, int]:
    counts = {"pals": 0, "skin": 0, "tech": 0}
    for item in accepted:
        path = item["path"]
        if path.startswith("icons/pals/skin/"):
            counts["skin"] += 1
        elif path.startswith("icons/pals/"):
            counts["pals"] += 1
        elif path.startswith("icons/tech/"):
            counts["tech"] += 1
    return counts


def _load_legacy_ownership_evidence(
    candidate_path: Path,
    ownership_path: Path,
) -> tuple[dict, dict, dict[str, str], dict]:
    candidate, candidate_hash = _read_json_artifact(
        candidate_path, "Legacy ownership candidate"
    )
    ownership, ownership_hash = _read_json_artifact(
        ownership_path, "Legacy ownership evidence"
    )
    accepted = candidate.get("accepted")
    if (
        candidate.get("schema_version") != 1
        or candidate.get("review_approval") is not None
        or not isinstance(accepted, list)
        or any(
            not isinstance(item, dict)
            or set(item) != {"path", "sha256"}
            or not isinstance(item["path"], str)
            or not isinstance(item["sha256"], str)
            for item in accepted
        )
        or candidate.get("accepted_count") != len(accepted)
        or candidate.get("plan_sha256") != _legacy_plan_hash(accepted)
    ):
        raise ValueError("Legacy ownership candidate is invalid or self-approved")
    expected_fields = {
        "schema_version",
        "kind",
        "baseline_commit",
        "backup_inventory_sha256",
        "ownership_plan_sha256",
        "candidate_artifact",
        "candidate_artifact_sha256",
        "accepted_count",
        "scope_counts",
        "review",
    }
    review = ownership.get("review")
    if (
        set(ownership) != expected_fields
        or ownership.get("schema_version") != 1
        or ownership.get("kind") != "legacy_ownership_evidence"
        or ownership.get("baseline_commit") != candidate.get("baseline_commit")
        or ownership.get("backup_inventory_sha256")
        != candidate.get("backup_inventory_sha256")
        or ownership.get("ownership_plan_sha256") != candidate.get("plan_sha256")
        or ownership.get("candidate_artifact") != Path(candidate_path).name
        or ownership.get("candidate_artifact_sha256") != candidate_hash
        or ownership.get("accepted_count") != len(accepted)
        or ownership.get("scope_counts") != _legacy_scope_counts(accepted)
        or not isinstance(review, dict)
        or set(review) != {"decision", "reviewer", "review_date"}
        or review.get("decision") != "approved_ownership_evidence_only"
        or not isinstance(review.get("reviewer"), str)
        or not review["reviewer"].strip()
        or not isinstance(review.get("review_date"), str)
        or not review["review_date"].strip()
    ):
        raise ValueError("Legacy ownership evidence does not match candidate artifact")
    paths = {}
    for item in accepted:
        path = item["path"]
        if not _legacy_path_allowed(path):
            raise ValueError(f"Legacy ownership path is outside scoped roots: {path}")
        folded = path.casefold()
        if folded in {existing.casefold() for existing in paths}:
            raise ValueError(f"Duplicate/casefold legacy ownership path: {path}")
        paths[path] = item["sha256"]
    identity = {
        "candidate_artifact_sha256": candidate_hash,
        "ownership_artifact_sha256": ownership_hash,
        "baseline_commit": candidate["baseline_commit"],
        "backup_inventory_sha256": candidate["backup_inventory_sha256"],
        "ownership_plan_sha256": candidate["plan_sha256"],
        "ownership_reviewer": review["reviewer"],
    }
    return candidate, ownership, paths, identity


def _candidate_snapshot(candidate: DomainSnapshot) -> dict:
    json_outputs = {
        path: {
            "count": candidate.output_counts[path],
            "sha256": candidate.hashes[path],
        }
        for path in sorted(candidate.outputs)
        if path.endswith(".json")
    }
    return {
        "domain": candidate.domain,
        "game_build": candidate.identity.game_build,
        "parser_revision": candidate.identity.parser_revision,
        "mapping_sha256": candidate.identity.mapping_sha256,
        "policy_sha256": candidate.policy_sha256,
        "json_outputs": json_outputs,
        "metrics": (
            character_snapshot_metrics(candidate)
            if candidate.domain == "characters"
            else {}
        ),
        "output_count": len(candidate.outputs),
        "output_root_sha256": canonical_output_root_sha256(candidate.outputs),
        "output_hashes": dict(sorted(candidate.hashes.items())),
    }


def character_snapshot_metrics(candidate: DomainSnapshot) -> dict:
    if candidate.domain != "characters":
        raise ValueError("Character metrics require a characters candidate")
    pals = _json_rows(candidate.outputs["data/pal_data.json"], "data/pal_data.json")
    humans = _json_rows(
        candidate.outputs["data/human_data.json"], "data/human_data.json"
    )
    characters = {**pals, **humans}
    game_icon_keys = [
        row["IconKey"]
        for row in characters.values()
        if row.get("IconKey") not in {"Human", "unknown"}
    ]
    pal_scenario_tags = (
        "predator",
        "raid",
        "tower",
        "boss-rush",
        "quest",
        "oilrig",
        "summon",
        "otomo",
    )
    human_scenario_tags = ("quest", "oilrig")

    def count_tags(rows: dict[str, dict], tags: tuple[str, ...]) -> dict[str, int]:
        return {
            tag: sum(tag in row.get("VariantTags", ()) for row in rows.values())
            for tag in tags
        }

    pal_counts = count_tags(pals, pal_scenario_tags)
    human_counts = count_tags(humans, human_scenario_tags)
    return {
        "character_records": len(characters),
        "unknown_icon_records": sum(
            row.get("IconKey") == "unknown" for row in characters.values()
        ),
        "human_static_icon_records": sum(
            row.get("IconKey") == "Human" for row in characters.values()
        ),
        "game_icon_records": len(game_icon_keys),
        "game_icon_unique_keys": len(set(game_icon_keys)),
        "game_icon_reused_records": len(game_icon_keys) - len(set(game_icon_keys)),
        "unresolved_family_ids": sorted(
            character_id
            for character_id, row in characters.items()
            if row.get("FamilyResolved") is False
        ),
        "scenario_identity_counts": {
            "pals": pal_counts,
            "humans": human_counts,
            "combined": {
                tag: pal_counts[tag] + human_counts[tag] for tag in human_scenario_tags
            },
        },
    }


def _candidate_icon_reference_details(
    candidate: DomainSnapshot,
) -> dict[str, list[dict[str, str]]]:
    details: dict[str, list[dict[str, str]]] = {}
    for output_path in (
        "data/pal_data.json",
        "data/human_data.json",
        "data/skin_data.json",
    ):
        data = candidate.outputs.get(output_path)
        if data is None:
            continue
        for record_id, row in _json_rows(data, output_path).items():
            icon_key = row.get("IconKey")
            if not isinstance(icon_key, str) or not icon_key:
                continue
            skin = output_path == "data/skin_data.json"
            icon_path = (
                f"icons/pals/skin/{icon_key}.png"
                if skin
                else f"icons/pals/{icon_key}.png"
            )
            state = (
                "invalid_allowed_missing"
                if skin and row.get("Invalid") is True
                else "required"
            )
            details.setdefault(icon_path, []).append(
                {
                    "output_path": output_path,
                    "record_id": record_id,
                    "field": "IconKey",
                    "state": state,
                }
            )
    return {
        path: sorted(
            references,
            key=lambda item: (item["output_path"], item["record_id"]),
        )
        for path, references in details.items()
    }


def _deletion_proposal(
    domain: str,
    candidate: DomainSnapshot,
    assets: Path,
    paths: dict[str, str],
    ownership_identity: dict,
) -> dict:
    candidate_paths = {path.casefold(): path for path in candidate.outputs}
    references = _candidate_icon_reference_details(candidate)
    deletions = []
    renames = []
    for path, expected_hash in sorted(paths.items()):
        if not _legacy_domain_owns(domain, path) or path in _STATIC_PAL_ICONS:
            continue
        target = _safe_file_target(assets, path)
        if not target.is_file():
            continue
        actual_case = _actual_relative_case(assets, path)
        if actual_case is None:
            continue
        actual_hash = _file_sha256(target)
        if actual_hash != expected_hash:
            raise ValueError(f"Legacy owned file changed since review: {path}")
        candidate_path = candidate_paths.get(path.casefold())
        if candidate_path is not None:
            if candidate_path != actual_case:
                renames.append(
                    {
                        "from_path": actual_case,
                        "to_path": candidate_path,
                        "current_sha256": actual_hash,
                        "baseline_sha256": expected_hash,
                        "backup_sha256": expected_hash,
                        "candidate_sha256": candidate.hashes[candidate_path],
                        "candidate_output_state": "case_only_rename",
                        "reason": "candidate_uses_canonical_path_casing",
                    }
                )
            continue
        path = actual_case
        record_references = references.get(path, [])
        reference_state = (
            "none"
            if not record_references
            else "invalid_allowed_missing"
            if all(
                item["state"] == "invalid_allowed_missing" for item in record_references
            )
            else "required"
        )
        reason = (
            "not_referenced_by_candidate_records"
            if reference_state == "none"
            else "referenced_only_by_invalid_allowed_missing_record"
            if reference_state == "invalid_allowed_missing"
            else "candidate_has_required_record_reference"
        )
        deletions.append(
            {
                "path": path,
                "current_sha256": actual_hash,
                "baseline_sha256": expected_hash,
                "backup_sha256": expected_hash,
                "candidate_output_state": "absent",
                "record_reference_state": reference_state,
                "record_references": record_references,
                "reason": reason,
            }
        )
    proposal = {
        "schema_version": 3,
        "kind": "legacy_change_proposal",
        "domain": domain,
        "candidate_snapshot": _candidate_snapshot(candidate),
        "ownership_evidence": dict(ownership_identity),
        "paths": deletions,
        "renames": renames,
    }
    encoded = json.dumps(
        proposal, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {**proposal, "plan_sha256": _sha256_bytes(encoded)}


def build_legacy_deletion_proposal(
    domain: str,
    candidate: DomainSnapshot,
    assets: Path,
    candidate_path: Path,
    ownership_path: Path,
    *,
    existing: Manifest | None = None,
) -> dict | None:
    if existing is not None and domain in existing.domains:
        return None
    _, _, paths, identity = _load_legacy_ownership_evidence(
        candidate_path, ownership_path
    )
    return _deletion_proposal(domain, candidate, Path(assets), paths, identity)


def _legacy_publication_context(
    domain: str,
    candidate: DomainSnapshot,
    assets: Path,
    candidate_path: Path | None,
    ownership_path: Path | None,
    proposal: dict | None,
    approval: dict | None,
) -> tuple[dict[str, str], dict[str, str], tuple[tuple[str, str], ...]]:
    values = (candidate_path, ownership_path, proposal, approval)
    if all(value is None for value in values):
        return {}, {}, ()
    if candidate_path is None or ownership_path is None:
        raise ValueError(
            "Legacy ownership requires both candidate and evidence artifacts"
        )
    _, ownership, paths, identity = _load_legacy_ownership_evidence(
        candidate_path, ownership_path
    )
    owned = {
        path: digest
        for path, digest in paths.items()
        if _legacy_domain_owns(domain, path)
    }
    fresh = _deletion_proposal(domain, candidate, assets, paths, identity)
    if fresh["paths"] or fresh["renames"]:
        if proposal is None or approval is None:
            raise ValueError("Legacy deletion approval is required")
        if proposal != fresh:
            raise ValueError("Legacy deletion proposal does not match fresh plan")
        expected_approval_fields = {
            "schema_version",
            "kind",
            "reviewer",
            "review_date",
            "approved_plan_sha256",
            "approved_deletions",
            "approved_renames",
        }
        if (
            not isinstance(approval, dict)
            or set(approval) != expected_approval_fields
            or approval.get("schema_version") != 2
            or approval.get("kind") != "legacy_change_approval"
            or approval.get("approved_plan_sha256") != fresh["plan_sha256"]
            or approval.get("approved_deletions") != fresh["paths"]
            or approval.get("approved_renames") != fresh["renames"]
            or not isinstance(approval.get("reviewer"), str)
            or not approval["reviewer"].strip()
            or approval["reviewer"] == ownership["review"]["reviewer"]
            or not isinstance(approval.get("review_date"), str)
            or not approval["review_date"].strip()
        ):
            raise ValueError(
                "Legacy change approval does not exactly match fresh plan"
            )
        deletions = {item["path"]: item["current_sha256"] for item in fresh["paths"]}
        renames = tuple(
            (item["from_path"], item["to_path"]) for item in fresh["renames"]
        )
    else:
        if proposal is not None or approval is not None:
            raise ValueError("Legacy deletion proposal/approval is unexpected")
        deletions = {}
        renames = ()
    return owned, deletions, renames


def _output_contract_errors(domain: str, candidate: DomainSnapshot) -> list[str]:
    errors = []
    required = _REQUIRED_OUTPUTS[domain]
    for path in sorted(required - candidate.outputs.keys()):
        errors.append(f"{domain}: missing required output {path}")
    for path, data in candidate.outputs.items():
        allowed = (
            path in required
            or (
                domain == "characters"
                and path.startswith("icons/pals/")
                and path.endswith(".png")
            )
            or (
                domain == "technology"
                and path.startswith("icons/tech/")
                and path.endswith(".png")
            )
        )
        if not _canonical_output_path(path) or not allowed:
            errors.append(f"{domain}: forbidden output {path}")
        if path in required:
            try:
                if not _json_rows(data, path):
                    errors.append(f"{domain}: empty required output {path}")
            except ValueError as error:
                errors.append(str(error))
    return errors


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _i18n_errors(path: str, row_id: str, value) -> list[str]:
    if not isinstance(value, dict) or set(value) != set(LOCALE_DIRECTORIES):
        return [
            f"{path} row {row_id}: I18n keys must be exactly the 17 supported locales"
        ]
    if path in (
        "data/pal_data.json",
        "data/human_data.json",
        "data/skin_data.json",
    ):
        if any(not isinstance(text, str) or not text for text in value.values()):
            return [f"{path} row {row_id}: I18n values must be nonempty strings"]
        return []
    required = {"Name", "Description"}
    if path == "data/tech_data.json":
        required.add("Type")
    for locale, text in value.items():
        if not isinstance(text, dict) or any(
            not isinstance(text.get(field), str) or not text[field]
            for field in required
        ):
            return [
                f"{path} row {row_id}: I18n {locale} requires nonempty "
                + ", ".join(sorted(required))
            ]
    return []


def _field_type_errors(path: str, row_id: str, row: dict) -> list[str]:
    prefix = f"{path} row {row_id}"
    errors = []
    if path in ("data/pal_data.json", "data/human_data.json"):
        for field in ("FamilyID", "VariantKind", "BestWorkSuitability"):
            if not isinstance(row.get(field), str) or not row[field]:
                errors.append(f"{prefix}: {field} must be a nonempty string")
        for field in ("Invalid", "RegularlyObtainable"):
            if type(row.get(field)) is not bool:
                errors.append(f"{prefix}: {field} must be a bool")
        if type(row.get("FamilyResolved")) is not bool:
            errors.append(f"{prefix}: FamilyResolved must be a bool")
        if (
            type(row.get("Invalid")) is bool
            and type(row.get("RegularlyObtainable")) is bool
            and row["Invalid"] is not (not row["RegularlyObtainable"])
        ):
            errors.append(f"{prefix}: Invalid must equal not RegularlyObtainable")
        for field in ("VariantTags", "ObtainMethods", "Elements"):
            values = row.get(field)
            if not isinstance(values, list) or any(
                not isinstance(value, str) or not value for value in values
            ):
                errors.append(f"{prefix}: {field} must be list[str]")
        availability = row.get("AvailabilitySources")
        if not isinstance(availability, list) or any(
            not isinstance(source, dict)
            or set(source) != {"Kind", "ID"}
            or any(
                not isinstance(source.get(field), str) or not source[field]
                for field in ("Kind", "ID")
            )
            for source in availability
        ):
            errors.append(f"{prefix}: AvailabilitySources metadata is invalid")
        stats = row.get("Stats")
        if (
            not isinstance(stats, dict)
            or set(stats) != set(CHARACTER_STATS)
            or any(not _is_number(value) for value in stats.values())
        ):
            errors.append(f"{prefix}: Stats metadata is invalid")
        parameters = row.get("Parameters")
        if not isinstance(parameters, dict) or set(parameters) != set(
            CHARACTER_PARAMETER_FIELDS
        ):
            errors.append(f"{prefix}: Parameters metadata is invalid")
        else:
            for field, value in parameters.items():
                valid = (
                    isinstance(value, str) and bool(value)
                    if field == "Size"
                    else type(value) is bool
                    if field in {"Nocturnal", "Predator", "Edible", "IgnoreCombi"}
                    else _is_number(value)
                )
                if not valid:
                    errors.append(f"{prefix}: Parameters.{field} has invalid type")
        suitabilities = row.get("Suitabilities")
        expected_suitabilities = {
            f"EPalWorkSuitability::{name}" for name in WORK_SUITABILITIES
        }
        if (
            not isinstance(suitabilities, dict)
            or set(suitabilities) != expected_suitabilities
            or any(not _is_number(value) for value in suitabilities.values())
        ):
            errors.append(f"{prefix}: Suitabilities metadata is invalid")
        passives = row.get("DefaultPassives")
        attacks = row.get("Attacks")
        if not isinstance(passives, list) or any(
            not isinstance(value, str) or not value for value in passives
        ):
            errors.append(f"{prefix}: DefaultPassives must be list[str]")
        if not isinstance(attacks, dict) or any(
            not isinstance(key, str)
            or not key
            or not isinstance(level, int)
            or isinstance(level, bool)
            for key, level in attacks.items()
        ):
            errors.append(f"{prefix}: Attacks must be a string-keyed level map")
        sorting = row.get("SortingKey")
        if (
            not isinstance(sorting, dict)
            or set(sorting) != {"paldeck"}
            or not isinstance(sorting.get("paldeck"), str)
        ):
            errors.append(f"{prefix}: SortingKey metadata is invalid")
        if not isinstance(row.get("PaldeckIndex"), int) or isinstance(
            row.get("PaldeckIndex"), bool
        ):
            errors.append(f"{prefix}: PaldeckIndex must be an integer")
        if not isinstance(row.get("PaldeckSuffix"), str):
            errors.append(f"{prefix}: PaldeckSuffix must be a string")
        breeding = row.get("Breeding")
        if (
            not isinstance(breeding, dict)
            or set(breeding)
            != {
                "CombiRank",
                "CombiDuplicatePriority",
                "IgnoreCombi",
                "UniqueRecipes",
            }
            or not _is_number(breeding["CombiRank"])
            or not _is_number(breeding["CombiDuplicatePriority"])
            or type(breeding["IgnoreCombi"]) is not bool
            or not isinstance(breeding["UniqueRecipes"], list)
            or any(
                not isinstance(recipe, dict)
                or set(recipe)
                != {
                    "ParentTribeA",
                    "ParentTribeB",
                    "ParentGenderA",
                    "ParentGenderB",
                    "ChildCharacterID",
                }
                or any(
                    not isinstance(value, str) or not value for value in recipe.values()
                )
                for recipe in breeding["UniqueRecipes"]
            )
        ):
            errors.append(f"{prefix}: Breeding metadata is invalid")
        if path == "data/human_data.json":
            if row.get("Human") is not True:
                errors.append(f"{prefix}: Human must be true")
            if type(row.get("HasIcon")) is not bool:
                errors.append(f"{prefix}: HasIcon must be a bool")
    elif path == "data/skin_data.json":
        if not isinstance(row.get("TargetPalName"), str) or not row["TargetPalName"]:
            errors.append(f"{prefix}: TargetPalName must be a nonempty string")
        for field in (
            "SkinName",
            "SkinType",
            "SkinStaticClass",
            "TargetActorClassName",
        ):
            if not isinstance(row.get(field), str) or not row[field]:
                errors.append(f"{prefix}: {field} must be a nonempty string")
        for field in ("bIsHairAccessory", "bAutoGetItem", "Invalid"):
            if type(row.get(field)) is not bool:
                errors.append(f"{prefix}: {field} must be a bool")
        if not isinstance(row.get("PlatformItemID_Steam"), int) or isinstance(
            row.get("PlatformItemID_Steam"), bool
        ):
            errors.append(f"{prefix}: PlatformItemID_Steam must be an integer")
    elif path == "data/pal_attacks.json":
        learners = row.get("Learners")
        if not isinstance(learners, list) or any(
            not isinstance(learner, dict)
            or set(learner) != {"CharacterID", "Level"}
            or not isinstance(learner.get("CharacterID"), str)
            or not learner["CharacterID"]
            or not isinstance(learner.get("Level"), int)
            or isinstance(learner["Level"], bool)
            for learner in learners
        ):
            errors.append(
                f"{prefix}: Learners must contain CharacterID strings and integer Level values"
            )
        for field in (
            "UniqueSkill",
            "Disabled",
            "NonInheritable",
            "SkillFruit",
            "Exclusive",
            "BossSkill",
            "Assignable",
            "AssignableToHumans",
            "Invalid",
        ):
            if type(row.get(field)) is not bool:
                errors.append(f"{prefix}: {field} must be a bool")
        if row.get("UniqueSkill") != row.get("NonInheritable"):
            errors.append(f"{prefix}: UniqueSkill must equal NonInheritable")
        for field in ("CT", "Power"):
            if not _is_number(row.get(field)):
                errors.append(f"{prefix}: {field} must be numeric")
        for field in ("Element", "Category", "Strength"):
            if not isinstance(row.get(field), str) or not row[field]:
                errors.append(f"{prefix}: {field} must be a nonempty string")
        effects = row.get("Effects")
        if not isinstance(effects, list) or any(
            not isinstance(effect, dict)
            or set(effect) != {"EffectType", "EffectValue", "EffectValueEx"}
            or not isinstance(effect.get("EffectType"), str)
            or not effect["EffectType"]
            or not _is_number(effect.get("EffectValue"))
            or not _is_number(effect.get("EffectValueEx"))
            for effect in effects
        ):
            errors.append(f"{prefix}: Effects metadata is invalid")
    elif path == "data/pal_passives.json":
        if not _is_number(row.get("Rating")):
            errors.append(f"{prefix}: Rating must be numeric")
        for field in ("Category", "TargetElementType"):
            if not isinstance(row.get(field), str) or not row[field]:
                errors.append(f"{prefix}: {field} must be a nonempty string")
        buff = row.get("Buff")
        if (
            not isinstance(buff, dict)
            or set(buff) != _PASSIVE_BUFF_FIELDS
            or any(not _is_number(value) for value in buff.values())
        ):
            errors.append(f"{prefix}: Buff metadata is invalid")
        effects = row.get("Effects")
        if not isinstance(effects, list) or any(
            not isinstance(effect, dict)
            or set(effect) != {"EffectType", "EffectValue", "TargetType"}
            or not isinstance(effect.get("EffectType"), str)
            or not effect["EffectType"]
            or not _is_number(effect.get("EffectValue"))
            or not isinstance(effect.get("TargetType"), str)
            or not effect["TargetType"]
            for effect in effects
        ):
            errors.append(f"{prefix}: Effects metadata is invalid")
        invocation = row.get("Invocation")
        if (
            not isinstance(invocation, dict)
            or set(invocation) != _PASSIVE_INVOCATION_FIELDS
            or any(type(value) is not bool for value in invocation.values())
        ):
            errors.append(f"{prefix}: Invocation metadata is invalid")
        triggers = row.get("AddInvokeTriggerTypes")
        if not isinstance(triggers, list) or any(
            not isinstance(value, str) or not value for value in triggers
        ):
            errors.append(f"{prefix}: AddInvokeTriggerTypes must be list[str]")
        description_sources = row.get("DescriptionSource")
        if (
            not isinstance(description_sources, dict)
            or set(description_sources) != set(LOCALE_DIRECTORIES)
            or any(
                value not in {"explicit", "composed"}
                for value in description_sources.values()
            )
        ):
            errors.append(f"{prefix}: DescriptionSource metadata is invalid")
    elif path == "data/player_status_data.json":
        if row.get("category") not in {"stat", "effigy"}:
            errors.append(f"{prefix}: category is invalid")
        if row.get("unit") not in {"flat", "percent", "rank"}:
            errors.append(f"{prefix}: unit is invalid")
        for field in ("icon", "source"):
            if not isinstance(row.get(field), str) or not row[field]:
                errors.append(f"{prefix}: {field} must be a nonempty string")
        maximum = row.get("maximum")
        values = row.get("values")
        if type(maximum) is not int or maximum < 1:
            errors.append(f"{prefix}: maximum must be a positive integer")
        if (
            not isinstance(values, list)
            or any(not _is_number(value) for value in values)
            or type(maximum) is not int
            or len(values) != maximum + 1
            or not values
            or values[0] != 0
        ):
            errors.append(f"{prefix}: values must cover every rank from zero")
    elif path in _PROGRESSION_SCHEMAS:
        for field in _PROGRESSION_SCHEMAS[path]:
            if field in row and not _is_number(row[field]):
                errors.append(f"{prefix}: {field} must be numeric")
    elif path == "data/tech_data.json":
        for field in ("Level", "Tier", "Cost"):
            if type(row.get(field)) is not int:
                errors.append(f"{prefix}: {field} must be an integer")
        if type(row.get("BossTechnology")) is not bool:
            errors.append(f"{prefix}: BossTechnology must be a bool")
        requirements = row.get("Requirements")
        if (
            not isinstance(requirements, dict)
            or set(requirements) != {"DefeatTowerBoss", "ResearchID"}
            or any(not isinstance(value, str) for value in requirements.values())
        ):
            errors.append(f"{prefix}: Requirements metadata is invalid")
        for field in ("Prerequisites", "UnlockItems", "UnlockBuildObjects"):
            values = row.get(field)
            if not isinstance(values, list) or any(
                not isinstance(value, str) or not value for value in values
            ):
                errors.append(f"{prefix}: {field} must be list[str]")
        if bool(row.get("UnlockItems")) is bool(row.get("UnlockBuildObjects")):
            errors.append(f"{prefix}: exactly one unlock kind is required")
        if not isinstance(row.get("UnlockPalSkill"), str):
            errors.append(f"{prefix}: UnlockPalSkill must be a string")
        if row.get("IconKind") not in {"pal", "item", "building"}:
            errors.append(f"{prefix}: IconKind is invalid")
    if (
        path in _ENTITY_SCHEMAS
        and (not isinstance(row.get("IconKey"), str) or not row["IconKey"])
        and path not in ("data/pal_attacks.json", "data/pal_passives.json")
    ):
        errors.append(f"{prefix}: IconKey must be a nonempty string")
    return errors


def _canonical_id_set_sha256(values: set[str]) -> str:
    encoded = json.dumps(
        sorted(values), ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def canonical_output_root_sha256(outputs: Mapping[str, bytes]) -> str:
    """Bind every sorted character-domain path to the SHA-256 of its bytes."""
    digest = hashlib.sha256()
    for path, data in sorted(outputs.items()):
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(data).hexdigest().encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _skill_output_semantic_errors(candidate: DomainSnapshot) -> list[str]:
    data = candidate.outputs.get("data/pal_attacks.json")
    if data is None:
        return []
    try:
        rows = _json_rows(data, "data/pal_attacks.json")
    except ValueError:
        return []
    errors = []
    boolean_fields = (
        "UniqueSkill",
        "Disabled",
        "NonInheritable",
        "SkillFruit",
        "Exclusive",
        "Assignable",
        "AssignableToHumans",
        "Invalid",
    )
    for skill_id, row in rows.items():
        prefix = f"data/pal_attacks.json row {skill_id}"
        learners = row.get("Learners")
        valid_learners = isinstance(learners, list) and all(
            isinstance(learner, dict)
            and isinstance(learner.get("CharacterID"), str)
            and learner["CharacterID"]
            and isinstance(learner.get("Level"), int)
            and not isinstance(learner["Level"], bool)
            for learner in learners
        )
        if valid_learners:
            learner_ids = [learner["CharacterID"] for learner in learners]
            learner_pairs = [
                (learner["CharacterID"], learner["Level"]) for learner in learners
            ]
            if len(learner_ids) != len(set(learner_ids)) or len(learner_pairs) != len(
                set(learner_pairs)
            ):
                errors.append(f"{prefix}: duplicate learner ID or ID-level entry")
        if any(type(row.get(field)) is not bool for field in boolean_fields):
            continue
        disabled = row["Disabled"]
        non_inheritable = row["NonInheritable"]
        legal_fruit = row["SkillFruit"]
        invalid = row["Invalid"]
        has_learners = bool(learners) if valid_learners else False
        if row["UniqueSkill"] != non_inheritable:
            errors.append(f"{prefix}: UniqueSkill must equal NonInheritable")
        expected_exclusive = (
            not disabled and has_learners and not non_inheritable and not legal_fruit
        )
        if row["Exclusive"] != expected_exclusive:
            errors.append(
                f"{prefix}: Exclusive must equal enabled + learner + inheritable "
                "+ no legal fruit"
            )
        if disabled and not invalid:
            errors.append(f"{prefix}: Disabled skills must be Invalid")
        if disabled and row["Assignable"]:
            errors.append(f"{prefix}: Disabled skills cannot be Assignable")
        if disabled and row["AssignableToHumans"]:
            errors.append(f"{prefix}: Disabled skills cannot be human-assignable")
        if legal_fruit and row["Assignable"] != (not disabled):
            errors.append(
                f"{prefix}: legal-fruit Assignable state is inconsistent with Disabled"
            )
        if not invalid and not row["AssignableToHumans"]:
            expected_assignable = not disabled and (
                has_learners or legal_fruit or not non_inheritable
            )
            if row["Assignable"] != expected_assignable:
                errors.append(f"{prefix}: valid-skill Assignable state is inconsistent")
    return errors


def _character_family_errors(
    candidate: DomainSnapshot, sources: SourceInventory
) -> list[str]:
    try:
        characters = casefold_index(
            {
                character_id: {}
                for character_id in sources.reference_ids.get("characters", ())
            }
        )
    except ValueError as error:
        return [f"characters: {error}"]
    errors = []
    for path in ("data/pal_data.json", "data/human_data.json"):
        data = candidate.outputs.get(path)
        if data is None:
            continue
        try:
            rows = _json_rows(data, path)
        except ValueError:
            continue
        for character_id, row in rows.items():
            family = row.get("FamilyID")
            resolved = row.get("FamilyResolved")
            if not isinstance(family, str) or not family or type(resolved) is not bool:
                continue
            exists = family.casefold() in characters
            prefix = f"{path} row {character_id}"
            if resolved and not exists:
                errors.append(
                    f"{prefix}: FamilyResolved=true but FamilyID {family} does not resolve"
                )
            elif not resolved and exists:
                errors.append(
                    f"{prefix}: FamilyResolved=false but FamilyID {family} resolves"
                )
            if path == "data/human_data.json" and (
                not resolved or family != character_id
            ):
                errors.append(
                    f"{prefix}: human family must be self-resolved with exact spelling"
                )
    return errors


def _known_build_skill_errors(candidate: DomainSnapshot, policy: dict) -> list[str]:
    try:
        configured = policy["domains"]["skills"].get("known_build_invariants", {})
    except (AttributeError, KeyError, TypeError):
        return ["skills: known_build_invariants policy is invalid"]
    if not isinstance(configured, dict):
        return ["skills: known_build_invariants policy must be an object"]
    expected = configured.get(candidate.identity.game_build)
    if expected is None:
        return []
    if not isinstance(expected, dict):
        return [
            f"skills: known-build invariant {candidate.identity.game_build} is invalid"
        ]
    try:
        active = _json_rows(
            candidate.outputs["data/pal_attacks.json"], "data/pal_attacks.json"
        )
        passive = _json_rows(
            candidate.outputs["data/pal_passives.json"], "data/pal_passives.json"
        )
    except (KeyError, ValueError):
        return []
    groups = {
        "active_ids": set(active),
        "passive_ids": set(passive),
        "legal_fruit_ids": {
            skill_id
            for skill_id, row in active.items()
            if row.get("SkillFruit") is True
        },
        "exclusive_ids": {
            skill_id for skill_id, row in active.items() if row.get("Exclusive") is True
        },
        "boss_skill_ids": {
            skill_id for skill_id, row in active.items() if row.get("BossSkill") is True
        },
    }
    errors = []
    for name, values in groups.items():
        invariant = expected.get(name)
        if (
            not isinstance(invariant, dict)
            or not isinstance(invariant.get("count"), int)
            or isinstance(invariant["count"], bool)
            or not isinstance(invariant.get("sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", invariant["sha256"])
        ):
            errors.append(
                f"skills: known-build invariant {candidate.identity.game_build} "
                f"{name} policy is invalid"
            )
            continue
        actual_hash = _canonical_id_set_sha256(values)
        if len(values) != invariant["count"]:
            errors.append(
                f"skills: known-build invariant {name} count is {len(values)}, "
                f"expected {invariant['count']}"
            )
        if actual_hash != invariant["sha256"]:
            errors.append(
                f"skills: known-build invariant {name} SHA-256 is {actual_hash}, "
                f"expected {invariant['sha256']}"
            )
    required_passive = expected.get("required_passive_ids")
    forbidden_passive = expected.get("forbidden_passive_ids")
    if not isinstance(required_passive, list) or any(
        not isinstance(value, str) or not value for value in required_passive
    ):
        errors.append("skills: known-build required_passive_ids policy is invalid")
    else:
        errors.extend(
            f"skills: known-build required passive {value} is missing"
            for value in required_passive
            if value not in passive
        )
    if not isinstance(forbidden_passive, list) or any(
        not isinstance(value, str) or not value for value in forbidden_passive
    ):
        errors.append("skills: known-build forbidden_passive_ids policy is invalid")
    else:
        errors.extend(
            f"skills: known-build forbidden passive {value} is present"
            for value in forbidden_passive
            if value in passive
        )
    human = active.get("EPalWazaID::Human_Punch")
    if human is None:
        errors.append("skills: required EPalWazaID::Human_Punch is missing")
    elif (
        human.get("Invalid") is not False
        or human.get("Assignable") is not False
        or human.get("AssignableToHumans") is not True
        or human.get("Exclusive") is not False
    ):
        errors.append(
            "skills: EPalWazaID::Human_Punch must be valid, human-assignable, "
            "Pal-nonassignable, and nonexclusive"
        )
    psychokinesis = active.get("EPalWazaID::Psychokinesis")
    if psychokinesis is None:
        errors.append("skills: required EPalWazaID::Psychokinesis is missing")
    elif psychokinesis.get("SkillFruit") is not False:
        errors.append("skills: EPalWazaID::Psychokinesis cannot be a legal fruit")
    return errors


def _known_build_character_errors(candidate: DomainSnapshot, policy: dict) -> list[str]:
    try:
        configured = policy["domains"]["characters"].get("known_build_invariants", {})
    except (AttributeError, KeyError, TypeError):
        return ["characters: known_build_invariants policy is invalid"]
    if not isinstance(configured, dict):
        return ["characters: known_build_invariants policy must be an object"]
    expected = configured.get(candidate.identity.game_build)
    if expected is None:
        return []
    required_fields = {"json_outputs", "output_count", "output_root_sha256"}
    if not isinstance(expected, dict) or set(expected) != required_fields:
        return [
            (
                f"characters: known-build invariant {candidate.identity.game_build} "
                "is invalid"
            )
        ]
    json_outputs = expected.get("json_outputs")
    required_json = {
        "data/pal_data.json",
        "data/human_data.json",
        "data/skin_data.json",
    }
    if not isinstance(json_outputs, dict) or set(json_outputs) != required_json:
        return ["characters: known-build invariant json_outputs policy is invalid"]
    errors = []
    for path in sorted(required_json):
        invariant = json_outputs[path]
        if (
            not isinstance(invariant, dict)
            or set(invariant) != {"count", "sha256"}
            or not isinstance(invariant.get("count"), int)
            or isinstance(invariant["count"], bool)
            or not isinstance(invariant.get("sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", invariant["sha256"])
        ):
            errors.append(f"characters: known-build invariant {path} policy is invalid")
            continue
        data = candidate.outputs.get(path)
        if data is None:
            continue
        try:
            count = len(_json_rows(data, path))
        except ValueError:
            continue
        actual_hash = hashlib.sha256(data).hexdigest()
        if count != invariant["count"]:
            errors.append(
                f"characters: known-build invariant {path} count is {count}, "
                f"expected {invariant['count']}"
            )
        if actual_hash != invariant["sha256"]:
            errors.append(
                f"characters: known-build invariant {path} SHA-256 is "
                f"{actual_hash}, expected {invariant['sha256']}"
            )
    output_count = expected.get("output_count")
    if not isinstance(output_count, int) or isinstance(output_count, bool):
        errors.append("characters: known-build invariant output_count is invalid")
    elif len(candidate.outputs) != output_count:
        errors.append(
            f"characters: known-build invariant output count is "
            f"{len(candidate.outputs)}, expected {output_count}"
        )
    expected_root = expected.get("output_root_sha256")
    if not isinstance(expected_root, str) or not re.fullmatch(
        r"[0-9a-f]{64}", expected_root
    ):
        errors.append("characters: known-build invariant output root is invalid")
    else:
        actual_root = canonical_output_root_sha256(candidate.outputs)
        if actual_root != expected_root:
            errors.append(
                f"characters: known-build invariant output root is {actual_root}, "
                f"expected {expected_root}"
            )
    return errors


def _known_build_progression_errors(
    candidate: DomainSnapshot, policy: dict
) -> list[str]:
    try:
        configured = policy["domains"]["progression"].get(
            "known_build_invariants", {}
        )
    except (AttributeError, KeyError, TypeError):
        return ["progression: known_build_invariants policy is invalid"]
    if not isinstance(configured, dict):
        return ["progression: known_build_invariants policy must be an object"]
    expected = configured.get(candidate.identity.game_build)
    if expected is None:
        return []
    required = set(_PROGRESSION_SCHEMAS)
    if (
        not isinstance(expected, dict)
        or set(expected) != {"json_outputs"}
        or not isinstance(expected["json_outputs"], dict)
        or set(expected["json_outputs"]) != required
    ):
        return [
            (
                f"progression: known-build invariant {candidate.identity.game_build} "
                "is invalid"
            )
        ]
    errors = []
    for path in sorted(required):
        invariant = expected["json_outputs"][path]
        if (
            not isinstance(invariant, dict)
            or set(invariant) != {"count", "sha256"}
            or not isinstance(invariant.get("count"), int)
            or isinstance(invariant["count"], bool)
            or not isinstance(invariant.get("sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", invariant["sha256"])
        ):
            errors.append(
                f"progression: known-build invariant {path} policy is invalid"
            )
            continue
        data = candidate.outputs.get(path)
        if data is None:
            continue
        try:
            count = len(_json_rows(data, path))
        except ValueError:
            continue
        actual_hash = hashlib.sha256(data).hexdigest()
        if count != invariant["count"]:
            errors.append(
                f"progression: known-build invariant {path} count is {count}, "
                f"expected {invariant['count']}"
            )
        if actual_hash != invariant["sha256"]:
            errors.append(
                f"progression: known-build invariant {path} SHA-256 is "
                f"{actual_hash}, expected {invariant['sha256']}"
            )
    return errors


def _known_build_technology_errors(
    candidate: DomainSnapshot, policy: dict
) -> list[str]:
    try:
        configured = policy["domains"]["technology"].get(
            "known_build_invariants", {}
        )
    except (AttributeError, KeyError, TypeError):
        return ["technology: known_build_invariants policy is invalid"]
    if not isinstance(configured, dict):
        return ["technology: known_build_invariants policy must be an object"]
    expected = configured.get(candidate.identity.game_build)
    if expected is None:
        return []
    required_fields = {"json_outputs", "output_count", "output_root_sha256"}
    if not isinstance(expected, dict) or set(expected) != required_fields:
        return [
            f"technology: known-build invariant {candidate.identity.game_build} is invalid"
        ]
    json_outputs = expected["json_outputs"]
    if not isinstance(json_outputs, dict) or set(json_outputs) != {
        "data/tech_data.json"
    }:
        return ["technology: known-build invariant json_outputs policy is invalid"]
    invariant = json_outputs["data/tech_data.json"]
    errors = []
    if (
        not isinstance(invariant, dict)
        or set(invariant) != {"count", "sha256"}
        or not isinstance(invariant.get("count"), int)
        or isinstance(invariant["count"], bool)
        or not isinstance(invariant.get("sha256"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", invariant["sha256"])
    ):
        errors.append(
            "technology: known-build invariant data/tech_data.json policy is invalid"
        )
    elif data := candidate.outputs.get("data/tech_data.json"):
        try:
            count = len(_json_rows(data, "data/tech_data.json"))
        except ValueError:
            count = None
        actual_hash = hashlib.sha256(data).hexdigest()
        if count is not None and count != invariant["count"]:
            errors.append(
                f"technology: known-build invariant data/tech_data.json count is "
                f"{count}, expected {invariant['count']}"
            )
        if actual_hash != invariant["sha256"]:
            errors.append(
                f"technology: known-build invariant data/tech_data.json SHA-256 is "
                f"{actual_hash}, expected {invariant['sha256']}"
            )
    output_count = expected["output_count"]
    if not isinstance(output_count, int) or isinstance(output_count, bool):
        errors.append("technology: known-build invariant output_count is invalid")
    elif len(candidate.outputs) != output_count:
        errors.append(
            f"technology: known-build invariant output count is "
            f"{len(candidate.outputs)}, expected {output_count}"
        )
    expected_root = expected["output_root_sha256"]
    if not isinstance(expected_root, str) or not re.fullmatch(
        r"[0-9a-f]{64}", expected_root
    ):
        errors.append("technology: known-build invariant output root is invalid")
    else:
        actual_root = canonical_output_root_sha256(candidate.outputs)
        if actual_root != expected_root:
            errors.append(
                f"technology: known-build invariant output root is {actual_root}, "
                f"expected {expected_root}"
            )
    return errors


def _schema_errors(candidate: DomainSnapshot) -> list[str]:
    errors = []
    for path, data in candidate.outputs.items():
        if not path.endswith(".json"):
            continue
        try:
            rows = _json_rows(data, path)
        except ValueError as error:
            errors.append(str(error))
            continue
        required = _ENTITY_SCHEMAS.get(path)
        exact = path in {
            "data/pal_data.json",
            "data/human_data.json",
            "data/skin_data.json",
            "data/pal_attacks.json",
            "data/pal_passives.json",
        }
        if required is None:
            required = _PROGRESSION_SCHEMAS.get(path)
            exact = required is not None
        if required is None:
            errors.append(f"{path}: no output schema")
            continue
        for row_id, row in rows.items():
            missing = required - row.keys()
            if missing:
                errors.append(
                    f"{path} row {row_id}: missing required fields {sorted(missing)}"
                )
            allowed = set(required)
            if path in ("data/pal_data.json", "data/human_data.json") and isinstance(
                row.get("PaldeckRecordID"), str
            ):
                allowed.add("PaldeckRecordID")
            if exact and set(row) != allowed:
                unexpected = set(row) - allowed
                errors.append(
                    f"{path} row {row_id}: fields must be exactly {sorted(allowed)}; "
                    f"unexpected fields {sorted(unexpected)}"
                )
            if path in _ENTITY_SCHEMAS and row.get("InternalName") != row_id:
                errors.append(
                    f"{path} row {row_id}: InternalName must equal the top-level key"
                )
            if path in _ENTITY_SCHEMAS:
                errors.extend(_i18n_errors(path, row_id, row.get("I18n")))
            errors.extend(_field_type_errors(path, row_id, row))
    return errors


def _reference_label(reference: Reference) -> str:
    return (
        f"{reference.source_path}:{reference.source_id}:{reference.field}"
        f"->{reference.target_kind}:{reference.target_id}"
    )


def _reference_errors(
    references: tuple[Reference, ...], sources: SourceInventory
) -> tuple[list[str], tuple[str, ...]]:
    errors = []
    indexes = {}
    for kind, ids in sources.reference_ids.items():
        try:
            indexes[kind] = casefold_index({row_id: {} for row_id in ids})
        except ValueError as error:
            errors.append(f"{kind}: {error}")
    unresolved = tuple(
        sorted(
            _reference_label(reference)
            for reference in references
            if reference.target_id.casefold()
            not in indexes.get(reference.target_kind, {})
        )
    )
    errors.extend(f"unresolved output reference {label}" for label in unresolved)
    return errors, unresolved


def _icon_references(
    candidate: DomainSnapshot,
) -> tuple[tuple[str, bool, bool], ...]:
    references = []
    for path, data in candidate.outputs.items():
        if path not in _ENTITY_SCHEMAS:
            continue
        for row in _json_rows(data, path).values():
            key = row.get("IconKey")
            if not isinstance(key, str) or not key:
                continue
            if path in ("data/pal_data.json", "data/human_data.json"):
                references.append((f"icons/pals/{key}.png", False, False))
            elif path == "data/skin_data.json":
                references.append(
                    (
                        f"icons/pals/skin/{key}.png",
                        False,
                        row.get("Invalid") is True,
                    )
                )
            elif path == "data/tech_data.json":
                pal = row.get("IconKind") == "pal"
                references.append(
                    (
                        f"icons/pals/{key}.png" if pal else f"icons/tech/{key}.png",
                        pal,
                        False,
                    )
                )
    return tuple(references)


def _icon_errors(
    candidate: DomainSnapshot, sources: SourceInventory
) -> tuple[list[str], tuple[str, ...]]:
    owned = {path for path in candidate.outputs if path.endswith(".png")}
    approved = sources.approved_static_icons & _STATIC_PAL_ICONS
    missing = tuple(
        sorted(
            {
                path
                for path, allow_external, _allow_missing in _icon_references(candidate)
                if path not in owned
                and path not in approved
                and (not allow_external or path not in sources.available_icons)
            }
        )
    )
    allowed_missing = {
        path
        for path, _allow_external, allow_missing in _icon_references(candidate)
        if allow_missing
    }
    return (
        [
            f"unresolved output icon {path}"
            for path in missing
            if path not in allowed_missing
        ],
        missing,
    )


def _png_errors(candidate: DomainSnapshot) -> list[str]:
    errors = []
    for path, data in candidate.outputs.items():
        if not path.endswith(".png"):
            continue
        try:
            actual = _png_dimensions(data)
        except ValueError as error:
            errors.append(f"{path}: {error}")
            continue
        expected = candidate.icon_dimensions.get(path)
        if expected is None:
            errors.append(f"{path}: expected PNG dimensions are missing")
        elif actual != expected:
            errors.append(
                f"{path}: PNG dimensions are {actual[0]}x{actual[1]}, "
                f"expected {expected[0]}x{expected[1]}"
            )
    return errors


def _identity(entry: DomainManifest) -> BuildIdentity:
    return BuildIdentity(entry.game_build, entry.parser_revision, entry.mapping_sha256)


def validate_domain(
    domain: str,
    candidate: DomainSnapshot,
    sources: SourceInventory,
    existing: Manifest,
    policy: dict,
) -> list[str]:
    errors = []
    if candidate.domain != domain:
        errors.append(f"Candidate domain {candidate.domain} does not match {domain}")
    try:
        domain_policy = policy["domains"][domain]
        required_sources = domain_policy["required_sources"]
        if not isinstance(required_sources, list) or any(
            not isinstance(source, str) or not source for source in required_sources
        ):
            raise ValueError
    except (KeyError, TypeError, ValueError):
        required_sources = ()
        errors.append(f"{domain}: required_sources policy is invalid")
    if domain in {"skills", "characters"}:
        try:
            _supported_character_routes(policy, domain)
        except ValueError as error:
            errors.append(str(error))
    for source in required_sources:
        if source not in sources.present_sources:
            errors.append(f"{domain}: missing required source {source}")
        elif candidate.source_counts.get(source, 0) <= 0:
            errors.append(f"{domain}: required source {source} is empty")
    try:
        expected_identity = _identity_from_policy(policy)
        if candidate.identity != expected_identity:
            errors.append(f"{domain}: candidate toolchain identity is stale")
        if candidate.policy_sha256 != domain_policy_hash(policy, domain):
            errors.append(f"{domain}: candidate domain-policy hash is stale")
    except ValueError as error:
        errors.append(str(error))
    for existing_domain, entry in existing.domains.items():
        if _identity(entry) != candidate.identity:
            errors.append(
                f"{domain}: toolchain identity differs from existing domain "
                f"{existing_domain}"
            )
    errors.extend(_output_contract_errors(domain, candidate))
    try:
        derived_ids, derived_references = _derive_inventory(candidate.outputs)
    except ValueError as error:
        errors.append(str(error))
        derived_ids, derived_references = {}, ()
    if candidate.ids != derived_ids:
        errors.append(f"{domain}: candidate ID inventory does not match output bytes")
    if candidate.references != derived_references:
        errors.append(
            f"{domain}: candidate reference inventory does not match output bytes"
        )
    expected_hashes = {
        path: hashlib.sha256(data).hexdigest()
        for path, data in candidate.outputs.items()
    }
    if candidate.hashes != expected_hashes:
        errors.append(f"{domain}: output hashes are incomplete or stale")
    expected_counts = {}
    for path, data in candidate.outputs.items():
        try:
            expected_counts[path] = (
                len(_json_rows(data, path)) if path.endswith(".json") else 1
            )
        except ValueError as error:
            errors.append(str(error))
    if candidate.output_counts != expected_counts:
        errors.append(f"{domain}: output counts are incomplete or stale")
    errors.extend(_schema_errors(candidate))
    if domain == "skills":
        errors.extend(_skill_output_semantic_errors(candidate))
        errors.extend(_known_build_skill_errors(candidate, policy))
    elif domain == "characters":
        errors.extend(_character_family_errors(candidate, sources))
        errors.extend(_known_build_character_errors(candidate, policy))
    elif domain == "progression":
        errors.extend(_known_build_progression_errors(candidate, policy))
    elif domain == "technology":
        errors.extend(_known_build_technology_errors(candidate, policy))
    reference_errors, unresolved = _reference_errors(derived_references, sources)
    errors.extend(reference_errors)
    if candidate.missing_references != unresolved:
        errors.append(
            f"{domain}: missing_references report does not match output bytes"
        )
    icon_errors, missing_icons = _icon_errors(candidate, sources)
    errors.extend(icon_errors)
    if candidate.missing_icons != missing_icons:
        errors.append(f"{domain}: missing_icons report does not match output bytes")
    errors.extend(_png_errors(candidate))
    return errors


def build_domain(domain: str, export_root: Path, policy: dict) -> DomainSnapshot:
    if domain not in DOMAIN_NAMES:
        raise ValueError(f"Unknown domain: {domain}")
    try:
        builder = DOMAIN_BUILDERS[domain]
    except KeyError as error:
        raise ValueError(f"No builder registered for domain {domain}") from error
    candidate = builder(Path(export_root), policy)
    if candidate.domain != domain:
        raise ValueError(
            f"Builder for {domain} returned candidate for {candidate.domain}"
        )
    if candidate.identity != _identity_from_policy(policy):
        raise ValueError(f"Builder for {domain} returned the wrong toolchain identity")
    expected_policy_hash = domain_policy_hash(policy, domain)
    if candidate.policy_sha256 != expected_policy_hash:
        raise ValueError(f"Builder for {domain} returned the wrong domain-policy hash")
    return candidate


def check_domains(
    domain: str,
    export_root: Path,
    policy: dict,
    sources: SourceInventory,
    existing: Manifest,
) -> CheckResult:
    selected = DOMAIN_NAMES if domain == "all" else (domain,)
    if domain != "all" and domain not in DOMAIN_NAMES:
        return CheckResult({}, existing, (f"Unknown domain: {domain}",))
    missing_builders = [name for name in selected if name not in DOMAIN_BUILDERS]
    if missing_builders:
        return CheckResult(
            {},
            existing,
            tuple(
                f"No builder registered for domain {name}" for name in missing_builders
            ),
        )
    candidates = {}
    errors = []
    for name in selected:
        try:
            candidates[name] = build_domain(name, export_root, policy)
        except (OSError, ValueError) as error:
            errors.append(str(error))
    if errors:
        return CheckResult(candidates, existing, tuple(errors))
    owners = {}
    for name, candidate in candidates.items():
        for path in candidate.outputs:
            if previous := owners.get(path):
                errors.append(f"output path overlap {path}: {previous} and {name}")
            else:
                owners[path] = name
    reference_ids = (
        {}
        if domain == "all"
        else {kind: set(ids) for kind, ids in sources.reference_ids.items()}
    )
    available_icons = set() if domain == "all" else set(sources.available_icons)
    for candidate in candidates.values():
        try:
            derived_ids, _ = _derive_inventory(candidate.outputs)
        except ValueError:
            derived_ids = {}
        for kind, ids in derived_ids.items():
            reference_ids.setdefault(kind, set()).update(ids)
        available_icons.update(
            path for path in candidate.outputs if path.endswith(".png")
        )
    combined_sources = SourceInventory(
        present_sources=sources.present_sources,
        reference_ids={kind: frozenset(ids) for kind, ids in reference_ids.items()},
        available_icons=frozenset(available_icons),
        approved_static_icons=sources.approved_static_icons,
    )
    validation_existing = (
        Manifest(existing.schema_version, existing.bootstrap, {})
        if domain == "all"
        else existing
    )
    for name, candidate in candidates.items():
        errors.extend(
            validate_domain(
                name,
                candidate,
                combined_sources,
                validation_existing,
                policy,
            )
        )
    if errors:
        return CheckResult(candidates, existing, tuple(errors))
    domains = dict(existing.domains)
    domains.update(
        {name: candidate_manifest(candidate) for name, candidate in candidates.items()}
    )
    manifest = Manifest(
        schema_version=existing.schema_version,
        bootstrap=deepcopy_json(existing.bootstrap),
        domains=domains,
    )
    return CheckResult(candidates, manifest, ())


def _safe_standalone_file(path: Path, assets: Path) -> Path:
    path = Path(path).absolute()
    if path.resolve(strict=False).is_relative_to(Path(assets).resolve()):
        raise ValueError("Local provenance must be outside runtime assets")
    for parent in (path, *path.parents):
        if _is_link(parent):
            raise ValueError(f"Provenance path crosses a symlink: {path}")
        if parent == path:
            if parent.exists() and not parent.is_file():
                raise ValueError(f"Provenance target is not a file: {path}")
        elif parent.exists() and not parent.is_dir():
            raise ValueError(f"Provenance parent is not a directory: {path}")
    if not path.parent.is_dir():
        raise ValueError(f"Provenance parent does not exist: {path.parent}")
    return path


def _candidate_publish_errors(
    domain: str,
    candidate: DomainSnapshot,
    existing: Manifest,
) -> list[str]:
    errors = []
    if domain not in DOMAIN_NAMES or candidate.domain != domain:
        errors.append(f"Candidate domain {candidate.domain} does not match {domain}")
    for existing_domain, entry in existing.domains.items():
        if _identity(entry) != candidate.identity:
            errors.append(
                f"{domain}: toolchain identity differs from existing domain "
                f"{existing_domain}"
            )
    errors.extend(_output_contract_errors(domain, candidate))
    expected_hashes = {
        path: _sha256_bytes(data) for path, data in candidate.outputs.items()
    }
    if candidate.hashes != expected_hashes:
        errors.append(f"{domain}: output hashes are incomplete or stale")
    expected_counts = {}
    try:
        for path, data in candidate.outputs.items():
            expected_counts[path] = (
                len(_json_rows(data, path)) if path.endswith(".json") else 1
            )
        ids, references = _derive_inventory(candidate.outputs)
    except ValueError as error:
        errors.append(str(error))
        ids, references = {}, ()
    if candidate.output_counts != expected_counts:
        errors.append(f"{domain}: output counts are incomplete or stale")
    if candidate.ids != ids:
        errors.append(f"{domain}: candidate ID inventory does not match output bytes")
    if candidate.references != references:
        errors.append(
            f"{domain}: candidate reference inventory does not match output bytes"
        )
    errors.extend(_schema_errors(candidate))
    errors.extend(_png_errors(candidate))
    if candidate.missing_references:
        errors.append(f"{domain}: unresolved references cannot be published")
    return errors


def _ensure_parent(path: Path, created: list[Path]) -> None:
    missing = []
    current = path
    while not current.exists():
        missing.append(current)
        current = current.parent
    if _is_link(current) or not current.is_dir():
        raise ValueError(f"Publish parent is not a real directory: {current}")
    for directory in reversed(missing):
        directory.mkdir()
        created.append(directory)


def publish_domain(
    stage: Path,
    assets: Path,
    domain: str,
    candidate: DomainSnapshot,
    manifest: Manifest,
    *,
    policy: dict,
    sources: SourceInventory,
    provenance_path: Path | None = None,
    legacy_candidate_path: Path | None = None,
    legacy_ownership_path: Path | None = None,
    legacy_deletion_proposal: dict | None = None,
    legacy_deletion_approval: dict | None = None,
) -> Manifest:
    stage = Path(stage)
    assets = Path(assets)
    if not stage.is_dir() or _is_link(stage):
        raise ValueError(f"Stage must be a real directory: {stage}")
    if not assets.is_dir() or _is_link(assets):
        raise ValueError(f"Assets must be a real directory: {assets}")
    if stage.resolve().is_relative_to(assets.resolve()):
        raise ValueError("Stage must be outside runtime assets")
    errors = validate_domain(domain, candidate, sources, manifest, policy)
    errors.extend(_candidate_publish_errors(domain, candidate, manifest))
    if errors:
        raise ValueError("; ".join(errors))
    staged = {}
    for relative, expected in candidate.outputs.items():
        source = _safe_file_target(stage, relative)
        if not source.is_file():
            raise ValueError(f"Missing staged output: {relative}")
        data = source.read_bytes()
        if data != expected or _sha256_bytes(data) != candidate.hashes[relative]:
            raise ValueError(f"Staged output hash differs from candidate: {relative}")
        staged[relative] = source
    domains = dict(manifest.domains)
    domains[domain] = candidate_manifest(candidate)
    updated = Manifest(
        manifest.schema_version, deepcopy_json(manifest.bootstrap), domains
    )
    _validate_manifest_paths(updated, assets)
    provenance = _safe_standalone_file(
        provenance_path or PROVENANCE_PATH,
        assets,
    )
    legacy_owned, legacy_deletions, legacy_renames = _legacy_publication_context(
        domain,
        candidate,
        assets,
        legacy_candidate_path,
        legacy_ownership_path,
        legacy_deletion_proposal,
        legacy_deletion_approval,
    )
    old_entry = manifest.domains.get(domain)
    old_paths = set(old_entry.managed_paths) if old_entry is not None else set()
    new_paths = set(candidate.outputs)
    new_folded = {path.casefold() for path in new_paths}
    stale_hashes = (
        {
            path: old_entry.output_hashes[path]
            for path in old_paths
            if path.casefold() not in new_folded
        }
        if old_entry is not None
        else {}
    )
    stale_hashes.update(legacy_deletions)
    stale_targets = {}
    for relative, expected_hash in stale_hashes.items():
        target = _safe_file_target(assets, relative)
        if target.is_file() and _file_sha256(target) != expected_hash:
            raise ValueError(f"Refusing to delete changed managed file: {relative}")
        stale_targets[relative] = target
    destinations = {
        relative: _safe_file_target(assets, relative) for relative in staged
    }
    old_folded = {path.casefold() for path in old_paths}
    approved_folded = {path.casefold(): digest for path, digest in legacy_owned.items()}
    for relative, target in destinations.items():
        if (
            relative.endswith(".png")
            and target.is_file()
            and relative.casefold() not in old_folded
        ):
            expected = approved_folded.get(relative.casefold())
            if expected is None or _file_sha256(target) != expected:
                raise ValueError(f"Refusing to replace unowned icon: {relative}")
    created_dirs = []
    mutations: list[tuple[Path, Path | None, Path]] = []
    with tempfile.TemporaryDirectory(
        prefix="game-data-publish-", dir=assets.parent
    ) as directory:
        transaction = Path(directory)

        def remember(target: Path) -> None:
            backup = None
            restore_target = target
            if target.is_file():
                try:
                    relative = target.relative_to(assets).as_posix()
                except ValueError:
                    relative = None
                if relative is not None:
                    actual_case = _actual_relative_case(assets, relative)
                    if actual_case is not None:
                        restore_target = _safe_file_target(assets, actual_case)
                backup = transaction / f"backup-{len(mutations):04d}"
                shutil.copy2(target, backup)
            mutations.append((target, backup, restore_target))

        try:
            for relative, target in sorted(stale_targets.items()):
                if not target.is_file():
                    continue
                remember(target)
                target.unlink()
            for index, (relative, source) in enumerate(sorted(staged.items())):
                target = destinations[relative]
                _ensure_parent(target.parent, created_dirs)
                incoming = transaction / f"incoming-{index:04d}"
                shutil.copy2(source, incoming)
                remember(target)
                os.replace(incoming, target)
            for _, target_path in legacy_renames:
                if _actual_relative_case(assets, target_path) != target_path:
                    raise AssertionError(
                        f"Case-only rename did not produce exact path: {target_path}"
                    )
            for relative, expected_hash in candidate.hashes.items():
                target = destinations[relative]
                if (
                    _actual_relative_case(assets, relative) != relative
                    or not target.is_file()
                    or _file_sha256(target) != expected_hash
                ):
                    raise AssertionError(
                        f"Published output failed exact postcondition: {relative}"
                    )
            for relative, target in stale_targets.items():
                if target.is_file():
                    raise AssertionError(
                        f"Approved stale output was not deleted: {relative}"
                    )
            incoming_provenance = transaction / "provenance.json"
            incoming_provenance.write_bytes(manifest_bytes(updated))
            remember(provenance)
            os.replace(incoming_provenance, provenance)
            if provenance.read_bytes() != manifest_bytes(updated):
                raise AssertionError("Published provenance failed postcondition")
        except Exception:
            rollback_errors = []
            for target, backup, restore_target in reversed(mutations):
                try:
                    if backup is None:
                        if target.is_file() or _is_link(target):
                            target.unlink()
                    else:
                        if target.is_file() or _is_link(target):
                            target.unlink()
                        _ensure_parent(restore_target.parent, created_dirs)
                        os.replace(backup, restore_target)
                except (OSError, ValueError) as error:
                    rollback_errors.append(f"{target}: {error}")
            for directory_path in reversed(created_dirs):
                try:
                    directory_path.rmdir()
                except OSError:
                    pass
            if rollback_errors:
                raise RuntimeError(
                    "Publish failed and rollback was incomplete: "
                    + "; ".join(rollback_errors)
                )
            raise
    return updated
