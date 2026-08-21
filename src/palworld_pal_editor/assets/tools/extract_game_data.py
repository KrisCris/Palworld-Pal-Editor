"""Inspect an installed Palworld build for the local game-data pipeline."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import game_data
from game_data import (
    Manifest,
    SourceInventory,
    check_domains,
    load_asset,
    load_table,
    manifest_from_dict,
    publish_domain,
)

POLICY_PATH = Path(__file__).with_name("policy.json")
_POLICY = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
_BOOTSTRAP = _POLICY["bootstrap"]
KNOWN_BUILD = _BOOTSTRAP["game_build"]
UEX_REVISION = _BOOTSTRAP["uex_revision"]
MAPPING_SHA256 = _BOOTSTRAP["mapping_sha256"]
DOCTOR_ASSETS = tuple(_POLICY["doctor_assets"])
RUNTIME_ASSETS = (
    Path(__file__).parents[4] / "src/palworld_pal_editor/assets"
).resolve()
LEGACY_OWNERSHIP_CANDIDATE = POLICY_PATH.with_name("legacy_ownership_candidate.json")
LEGACY_OWNERSHIP = POLICY_PATH.with_name("legacy_ownership.json")
CHARACTER_DELETION_PROPOSAL = POLICY_PATH.with_name("character_deletion_proposal.json")

_PAK_RELATIVE = Path("Pal/Content/Paks/Pal-Windows.pak")
_APP_MANIFEST = "appmanifest_1623730.acf"


@dataclass(frozen=True)
class Toolchain:
    uex: Path
    usmap: Path
    uex_revision: str
    mapping_sha256: str


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _steam_homes() -> list[Path]:
    homes = [
        Path(value)
        for name in ("STEAM_PATH", "STEAM_INSTALL_PATH")
        if (value := os.environ.get(name))
    ]
    if sys.platform == "win32":
        try:
            import winreg

            for hive, key, value_name in (
                (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
                (
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\WOW6432Node\Valve\Steam",
                    "InstallPath",
                ),
            ):
                try:
                    with winreg.OpenKey(hive, key) as opened:
                        homes.append(Path(winreg.QueryValueEx(opened, value_name)[0]))
                except OSError:
                    pass
        except ImportError:
            pass
        if value := os.environ.get("PROGRAMFILES(X86)"):
            homes.append(Path(value) / "Steam")
    return list(dict.fromkeys(homes))


def _steam_libraries(steam: Path) -> list[Path]:
    libraries = [steam]
    vdf = steam / "steamapps/libraryfolders.vdf"
    if vdf.is_file():
        text = vdf.read_text(encoding="utf-8", errors="replace")
        libraries.extend(
            Path(value.replace("\\\\", "\\"))
            for value in re.findall(r'"path"\s+"([^"]+)"', text)
        )
    return list(dict.fromkeys(libraries))


def find_game_dir(explicit: Path | None = None) -> Path:
    if explicit is not None:
        game = Path(explicit).expanduser().resolve()
        if not (game / _PAK_RELATIVE).is_file():
            raise FileNotFoundError(
                f"Missing {_PAK_RELATIVE} under explicit game path {game}"
            )
        return game
    for steam in _steam_homes():
        for library in _steam_libraries(steam):
            game = library / "steamapps/common/Palworld"
            if (game / _PAK_RELATIVE).is_file():
                return game.resolve()
    raise FileNotFoundError(
        "Palworld was not found in Steam libraries; pass --game-dir"
    )


def detect_build_id(game_dir: Path) -> str:
    manifest = Path(game_dir).parents[1] / _APP_MANIFEST
    if not manifest.is_file():
        raise FileNotFoundError(f"Steam manifest not found: {manifest}")
    match = re.search(r'"buildid"\s+"(\d+)"', manifest.read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"Steam build ID not found in {manifest}")
    return match.group(1)


def require_write_build(build_id: str, allow_unknown_build_write: bool) -> None:
    if build_id != KNOWN_BUILD and not allow_unknown_build_write:
        raise ValueError(
            f"Refusing --write for unknown build {build_id}; "
            "pass --allow-unknown-build-write to override"
        )


def _default_cache() -> Path:
    root = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".cache"))
    return root / "Palworld-Pal-Editor/game-assets"


def ensure_toolchain(
    cache: Path, uex: Path | None = None, usmap: Path | None = None
) -> Toolchain:
    """Validate existing parser and mapping files against the pinned identity."""
    cache = Path(cache)
    executable = Path(uex) if uex is not None else cache / "uex/uex.exe"
    mapping = Path(usmap) if usmap is not None else cache / "Mappings.usmap"
    if not executable.is_file():
        raise FileNotFoundError(f"uex not found: {executable}")
    if not mapping.is_file():
        raise FileNotFoundError(f"Mapping not found: {mapping}")
    mapping_hash = _file_hash(mapping)
    if mapping_hash != MAPPING_SHA256:
        raise ValueError(
            f"mapping SHA-256 mismatch: expected {MAPPING_SHA256}, got {mapping_hash}"
        )
    completed = subprocess.run(
        [str(executable), "--version"],
        check=True,
        capture_output=True,
        text=True,
    )
    version = (completed.stdout or completed.stderr).strip()
    if UEX_REVISION not in version:
        raise ValueError(
            f"uex version must contain pinned revision {UEX_REVISION}, got {version!r}"
        )
    return Toolchain(
        executable.resolve(), mapping.resolve(), UEX_REVISION, mapping_hash
    )


def export_game(
    toolchain: Toolchain, paks_dir: Path, output: Path, profile_path: Path
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    export_roots = [f"{path}.uasset" for path in DOCTOR_ASSETS]
    profile = {
        "profiles": {
            "palworld": {
                "paksDir": str(Path(paks_dir).resolve()),
                "game": "GAME_UE5_1",
                "aesKey": None,
                "usmap": str(toolchain.usmap.resolve()),
                "outputDir": str(output.resolve()),
                "exportRoots": export_roots,
            }
        }
    }
    profile_path.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    subprocess.run(
        [
            str(toolchain.uex),
            "export",
            "--config",
            str(profile_path),
            "--profile",
            "palworld",
            "--only",
            *export_roots,
        ],
        check=True,
    )


def _uex_source(path: str) -> str:
    suffix = (
        ".umap"
        if path == game_data.CHARACTER_ROUTE_SOURCES["incident_world"]
        else ".uasset"
    )
    return f"{path}{suffix}"


def export_sources(
    toolchain: Toolchain,
    paks_dir: Path,
    output: Path,
    profile_dir: Path,
    sources: set[str],
) -> None:
    """Export exact virtual packages in small deterministic UEX batches."""
    _export_roots(
        toolchain,
        paks_dir,
        output,
        profile_dir,
        {_uex_source(source) for source in sources},
    )


def export_prefixes(
    toolchain: Toolchain,
    paks_dir: Path,
    output: Path,
    profile_dir: Path,
    prefixes: set[str],
) -> None:
    """Export deterministic UEX directory or filename prefixes."""
    output.mkdir(parents=True, exist_ok=True)
    profile_dir.mkdir(parents=True, exist_ok=True)
    invalid = prefixes - game_data.CHARACTER_SCENARIO_PREFIX_SOURCES
    if invalid:
        raise ValueError(f"unsupported export prefixes: {sorted(invalid)}")
    roots = prefixes - game_data.CHARACTER_SCENARIO_FILENAME_PREFIX_SOURCES
    for list_number, prefix in enumerate(
        sorted(prefixes & game_data.CHARACTER_SCENARIO_FILENAME_PREFIX_SOURCES)
    ):
        parent, _, basename_prefix = prefix.rpartition("/")
        if not parent or not basename_prefix:
            raise ValueError(f"invalid filename prefix: {prefix}")
        profile_path = profile_dir / f"list-{list_number}.json"
        _write_profile(
            profile_path,
            toolchain,
            paks_dir,
            output,
            [],
        )
        completed = subprocess.run(
            [
                str(toolchain.uex),
                "list",
                parent,
                "--config",
                str(profile_path),
                "--profile",
                "palworld",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        children = sorted(
            {
                child
                for line in completed.stdout.splitlines()
                if (child := line.strip()).startswith(basename_prefix)
                and PurePosixPath(child).name == child
                and PurePosixPath(child).suffix in {".uasset", ".umap"}
            }
        )
        if not children:
            raise ValueError(f"UEX list found no packages for filename prefix {prefix}")
        roots.update(f"{parent}/{child}" for child in children)
    _export_roots(toolchain, paks_dir, output, profile_dir / "export", roots)


def _write_profile(
    profile_path: Path,
    toolchain: Toolchain,
    paks_dir: Path,
    output: Path,
    roots: list[str],
) -> None:
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile = {
        "profiles": {
            "palworld": {
                "paksDir": str(Path(paks_dir).resolve()),
                "game": "GAME_UE5_1",
                "aesKey": None,
                "usmap": str(toolchain.usmap.resolve()),
                "outputDir": str(output.resolve()),
                "exportRoots": roots,
            }
        }
    }
    profile_path.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _export_roots(
    toolchain: Toolchain,
    paks_dir: Path,
    output: Path,
    profile_dir: Path,
    roots: set[str],
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    profile_dir.mkdir(parents=True, exist_ok=True)
    roots = sorted(roots)
    for batch_number, offset in enumerate(range(0, len(roots), 48)):
        batch = roots[offset : offset + 48]
        profile_path = profile_dir / f"profiles-{batch_number}.json"
        _write_profile(profile_path, toolchain, paks_dir, output, batch)
        subprocess.run(
            [
                str(toolchain.uex),
                "export",
                "--config",
                str(profile_path),
                "--profile",
                "palworld",
                "--only",
                *batch,
            ],
            check=True,
        )


def _capture_replacement_actor_sources(export_root: Path) -> set[str]:
    monsters = load_table(export_root, game_data.CHARACTER_EVIDENCE_SOURCES["monsters"])
    bp_classes = load_table(export_root, game_data.SKILL_SOURCES["bp_classes"])
    combat_source = game_data.CHARACTER_SCENARIO_SOURCES["kingwhale_combat"]
    source_id, target_id = game_data.capture_replacement_ids(
        load_asset(export_root, combat_source), combat_source
    )
    roots = game_data.monster_action_blueprint_roots(monsters, bp_classes)
    missing = {source_id, target_id} - roots.keys()
    if missing:
        raise ValueError(
            f"capture replacement characters lack PalActorBP roots: {sorted(missing)}"
        )
    return {roots[source_id], roots[target_id]}


def _virtual_from_object(value, field: str) -> str:
    return game_data._object_path_to_virtual(game_data._object_path(value, field))


def _dynamic_skill_sources(export_root: Path) -> tuple[set[str], set[str]]:
    """Discover exact Blueprint and incident-table dependencies in two stages."""
    spawners = set()
    placements = load_table(
        export_root, game_data.CHARACTER_EVIDENCE_SOURCES["placements"]
    )
    for row_id, row in placements.items():
        object_path = game_data._asset_path_name(
            row.get("SpawnerClass"), f"{row_id}.SpawnerClass"
        )
        spawners.add(game_data._virtual_asset_path(object_path))
    dungeons = load_table(export_root, game_data.CHARACTER_ROUTE_SOURCES["dungeon"])
    for row_id, row in dungeons.items():
        if not game_data._positive_number(
            row.get("WeightInSpawnAreaAndRank"),
            f"{row_id}.WeightInSpawnAreaAndRank",
        ):
            continue
        object_path = game_data._asset_path_name(
            row.get("SpawnerBlueprintSoftClass"),
            f"{row_id}.SpawnerBlueprintSoftClass",
        )
        spawners.add(game_data._virtual_asset_path(object_path))
    world = load_asset(export_root, game_data.CHARACTER_ROUTE_SOURCES["incident_world"])
    persistent_level = "Level'PL_MainWorld5:PersistentLevel'"
    incident_classes = set()
    for actor in world:
        outer = actor.get("Outer")
        class_ref = actor.get("Class")
        if (
            isinstance(outer, dict)
            and outer.get("ObjectName") == persistent_level
            and isinstance(class_ref, str)
            and class_ref.startswith("BlueprintGeneratedClass'")
        ):
            try:
                virtual = game_data._object_path_to_virtual(
                    game_data._blueprint_class_path(class_ref, "incident actor.Class")
                )
            except ValueError:
                pass
            else:
                # Candidate discovery only; positive evidence still requires the
                # placed actor and exported CDO LotteryClass chain.
                if (
                    virtual.startswith("Pal/Content/Pal/Blueprint/Incident/Random/")
                    and "/Lottery/" not in virtual
                ):
                    incident_classes.add(virtual)
    return spawners, incident_classes


def _incident_dependencies(
    export_root: Path, *, inspect_lotteries: bool = True
) -> tuple[set[str], set[str]]:
    world = load_asset(export_root, game_data.CHARACTER_ROUTE_SOURCES["incident_world"])
    persistent_level = "Level'PL_MainWorld5:PersistentLevel'"
    lottery_references = {}
    for actor_index, actor in enumerate(world):
        outer = actor.get("Outer")
        class_ref = actor.get("Class")
        if (
            not isinstance(outer, dict)
            or outer.get("ObjectName") != persistent_level
            or not isinstance(class_ref, str)
            or not class_ref.startswith("BlueprintGeneratedClass'")
        ):
            continue
        class_path = game_data._blueprint_class_path(
            class_ref, f"incident actor {actor_index}.Class"
        )
        try:
            virtual = game_data._object_path_to_virtual(class_path)
        except ValueError:
            continue
        if not game_data._export_path(export_root, virtual).is_file():
            continue
        properties = game_data._select_spawner_default_object(
            load_asset(export_root, virtual),
            class_path.removesuffix(".0"),
            f"incident actor {actor_index}.Class",
        )
        actor_properties = actor.get("Properties", {})
        if not isinstance(actor_properties, dict):
            raise TypeError(
                f"incident actor {actor_index}.Properties must be an object"
            )
        lottery = actor_properties.get("LotteryClass") or properties.get("LotteryClass")
        if lottery is not None:
            field = f"incident actor {actor_index}.LotteryClass"
            lottery_virtual, _ = game_data._referenced_blueprint_identity(
                lottery, field
            )
            lottery_references.setdefault(lottery_virtual, (lottery, field))

    if not inspect_lotteries:
        return set(lottery_references), set()

    settings = load_table(
        export_root, game_data.CHARACTER_ROUTE_SOURCES["incident_settings"]
    )
    setting_index = game_data.casefold_index(settings)
    spawn_tables = set()
    for lottery, (reference, field) in lottery_references.items():
        asset = load_asset(export_root, lottery)
        resolved_lottery, properties = game_data._referenced_blueprint_default(
            asset, reference, field
        )
        if resolved_lottery != lottery:
            raise AssertionError("lottery dependency resolved inconsistently")
        parameters = properties["LotteryParameters"]
        if not isinstance(parameters, list):
            raise TypeError(f"{lottery}.LotteryParameters must be a list")
        for index, parameter in enumerate(parameters):
            if not isinstance(parameter, dict):
                raise TypeError(
                    f"{lottery}.LotteryParameters[{index}] must be an object"
                )
            if not game_data._positive_number(
                parameter.get("LotteryRate"),
                f"{lottery}.LotteryParameters[{index}].LotteryRate",
            ):
                continue
            setting_name = game_data._plain_name(
                parameter.get("SettingName"),
                f"{lottery}.LotteryParameters[{index}].SettingName",
            )
            try:
                setting = settings[setting_index[setting_name.casefold()]]
            except KeyError as error:
                raise ValueError(
                    f"{lottery} references unknown incident setting {setting_name}"
                ) from error
            for field in ("MonsterSpawnData", "NPCSpawnData"):
                value = setting.get(field)
                if (
                    isinstance(value, dict)
                    and isinstance(value.get("ObjectPath"), str)
                    and value["ObjectPath"].casefold() not in {"", "none"}
                ):
                    spawn_tables.add(
                        _virtual_from_object(value, f"{setting_name}.{field}")
                    )
    return set(lottery_references), spawn_tables


def export_skill_domain(
    toolchain: Toolchain, paks_dir: Path, export_root: Path, profile_dir: Path
) -> None:
    static_sources = set(_POLICY["domains"]["skills"]["required_sources"])
    static_sources.update(
        game_data.text_table_path("DT_PalNameText_Common", locale)
        for locale in game_data.LOCALE_DIRECTORIES
    )
    static_sources.update(
        game_data.text_table_path(game_data.PARTNER_SKILL_APPEND_TEXT, locale)
        for locale in game_data.LOCALE_DIRECTORIES
    )
    prefixes = static_sources & game_data.CHARACTER_SCENARIO_PREFIX_SOURCES
    static_sources -= prefixes
    export_sources(
        toolchain, paks_dir, export_root, profile_dir / "static", static_sources
    )
    export_prefixes(
        toolchain, paks_dir, export_root, profile_dir / "scenario-prefixes", prefixes
    )
    monster_rows = load_table(
        export_root, game_data.CHARACTER_EVIDENCE_SOURCES["monsters"]
    )
    bp_class_rows = load_table(export_root, game_data.SKILL_SOURCES["bp_classes"])
    pending = set(
        game_data.monster_action_blueprint_roots(monster_rows, bp_class_rows).values()
    )
    exported_blueprints: set[str] = set()
    generation = 0
    while pending:
        export_sources(
            toolchain,
            paks_dir,
            export_root,
            profile_dir / f"monster-actions-{generation}",
            pending,
        )
        parents = {
            parent
            for path in sorted(pending)
            if (
                parent := game_data.monster_blueprint_parent(
                    load_asset(export_root, path), path
                )
            )
            is not None
        }
        exported_blueprints.update(pending)
        pending = parents - exported_blueprints
        generation += 1
    spawners, incident_classes = _dynamic_skill_sources(export_root)
    export_sources(
        toolchain,
        paks_dir,
        export_root,
        profile_dir / "spawners",
        spawners | incident_classes,
    )
    lotteries, _ = _incident_dependencies(export_root, inspect_lotteries=False)
    export_sources(
        toolchain,
        paks_dir,
        export_root,
        profile_dir / "lotteries",
        lotteries,
    )
    _, spawn_tables = _incident_dependencies(export_root)
    export_sources(
        toolchain,
        paks_dir,
        export_root,
        profile_dir / "incident-spawns",
        spawn_tables,
    )


def export_character_domain(
    toolchain: Toolchain, paks_dir: Path, export_root: Path, profile_dir: Path
) -> None:
    static_sources = set(_POLICY["domains"]["characters"]["required_sources"])
    prefixes = static_sources & game_data.CHARACTER_SCENARIO_PREFIX_SOURCES
    static_sources -= prefixes
    static_sources.update(
        game_data.text_table_path(table_name, locale)
        for table_name in game_data.CHARACTER_TEXT_TABLES.values()
        for locale in game_data.LOCALE_DIRECTORIES
    )
    export_sources(
        toolchain, paks_dir, export_root, profile_dir / "static", static_sources
    )
    export_prefixes(
        toolchain, paks_dir, export_root, profile_dir / "scenario-prefixes", prefixes
    )
    export_sources(
        toolchain,
        paks_dir,
        export_root,
        profile_dir / "capture-actors",
        _capture_replacement_actor_sources(export_root),
    )
    spawners, incident_classes = _dynamic_skill_sources(export_root)
    export_sources(
        toolchain,
        paks_dir,
        export_root,
        profile_dir / "spawners",
        spawners | incident_classes,
    )
    lotteries, _ = _incident_dependencies(export_root, inspect_lotteries=False)
    export_sources(
        toolchain,
        paks_dir,
        export_root,
        profile_dir / "lotteries",
        lotteries,
    )
    _, spawn_tables = _incident_dependencies(export_root)
    export_sources(
        toolchain,
        paks_dir,
        export_root,
        profile_dir / "incident-spawns",
        spawn_tables,
    )
    projected, _ = game_data.load_character_projection(export_root, _POLICY)
    export_sources(
        toolchain,
        paks_dir,
        export_root,
        profile_dir / "icons",
        set(projected["icon_sources"].values()),
    )


def export_progression_domain(
    toolchain: Toolchain, paks_dir: Path, export_root: Path, profile_dir: Path
) -> None:
    export_sources(
        toolchain,
        paks_dir,
        export_root,
        profile_dir,
        set(_POLICY["domains"]["progression"]["required_sources"]),
    )


def export_technology_domain(
    toolchain: Toolchain, paks_dir: Path, export_root: Path, profile_dir: Path
) -> None:
    export_sources(
        toolchain,
        paks_dir,
        export_root,
        profile_dir / "tables",
        set(_POLICY["domains"]["technology"]["required_sources"]),
    )
    built, _ = game_data.load_technology_projection(export_root)
    export_sources(
        toolchain,
        paks_dir,
        export_root,
        profile_dir / "icons",
        set(built["icon_sources"].values()),
    )


def run_doctor(
    *,
    game_dir: Path | None = None,
    uex: Path | None = None,
    usmap: Path | None = None,
    cache: Path | None = None,
) -> dict:
    game = find_game_dir(game_dir)
    build_id = detect_build_id(game)
    toolchain = ensure_toolchain(cache or _default_cache(), uex, usmap)
    with tempfile.TemporaryDirectory(prefix="pal-game-data-doctor-") as directory:
        work = Path(directory)
        export_root = work / "export"
        export_game(
            toolchain,
            game / _PAK_RELATIVE.parent,
            export_root,
            work / "profiles.json",
        )
        source_counts = {
            path: len(load_table(export_root, path)) for path in DOCTOR_ASSETS
        }
    result = {
        "status": "ok",
        "game_build": build_id,
        "known_build": build_id == KNOWN_BUILD,
        "uex_revision": toolchain.uex_revision,
        "mapping_sha256": toolchain.mapping_sha256,
        "source_counts": source_counts,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return result


def _load_manifest(path: Path, policy: dict) -> Manifest:
    if path.is_file():
        manifest = manifest_from_dict(json.loads(path.read_text(encoding="utf-8")))
        if set(manifest.bootstrap) == {"bootstrap"} and isinstance(
            manifest.bootstrap["bootstrap"], dict
        ):
            return Manifest(1, manifest.bootstrap["bootstrap"], manifest.domains)
        return manifest
    return Manifest(1, dict(policy["bootstrap"]), {})


def _stage_outputs(stage: Path, outputs: dict[str, bytes]) -> None:
    for relative, data in outputs.items():
        target = stage.joinpath(*relative.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def run_domain(
    *,
    domain: str,
    write: bool,
    game_dir: Path | None = None,
    uex: Path | None = None,
    usmap: Path | None = None,
    cache: Path | None = None,
    allow_unknown_build_write: bool = False,
    assets: Path = RUNTIME_ASSETS,
    provenance_path: Path = game_data.PROVENANCE_PATH,
) -> dict:
    if domain != "all" and domain not in game_data.DOMAIN_NAMES:
        raise NotImplementedError(f"domain builder is not implemented yet: {domain}")
    if write and domain == "all":
        raise ValueError("all --write requires separately reviewed publishers")
    if write and domain in {"characters", "technology"}:
        raise ValueError(
            f"{domain} --write requires a separately reviewed deletion proposal"
        )
    game = find_game_dir(game_dir)
    build_id = detect_build_id(game)
    if write:
        require_write_build(build_id, allow_unknown_build_write)
    toolchain = ensure_toolchain(cache or _default_cache(), uex, usmap)
    policy = json.loads(json.dumps(_POLICY))
    policy["bootstrap"]["game_build"] = build_id
    existing = _load_manifest(Path(provenance_path), policy)
    with tempfile.TemporaryDirectory(prefix=f"pal-game-data-{domain}-") as directory:
        work = Path(directory)
        export_root = work / "export"
        exporters = {
            "skills": export_skill_domain,
            "characters": export_character_domain,
            "progression": export_progression_domain,
            "technology": export_technology_domain,
        }
        selected_domains = game_data.DOMAIN_NAMES if domain == "all" else (domain,)
        for selected_domain in selected_domains:
            exporters[selected_domain](
                toolchain,
                game / _PAK_RELATIVE.parent,
                export_root,
                (
                    work / "profiles" / selected_domain
                    if domain == "all"
                    else work / "profiles"
                ),
            )
        reference_ids = {}
        approved_static_icons = (
            frozenset(
                path
                for path in ("icons/pals/Human.png", "icons/pals/unknown.png")
                if Path(assets).joinpath(*path.split("/")).is_file()
            )
            if domain in {"all", "characters"}
            else frozenset()
        )
        if domain in {"skills", "characters"}:
            monsters = load_table(
                export_root, game_data.CHARACTER_EVIDENCE_SOURCES["monsters"]
            )
            humans = load_table(
                export_root, game_data.CHARACTER_EVIDENCE_SOURCES["humans"]
            )
            reference_ids["characters"] = frozenset(monsters) | frozenset(humans)
        if domain == "characters":
            levels = load_table(export_root, game_data.SKILL_SOURCES["levels"])
            passives = load_table(export_root, game_data.SKILL_SOURCES["passives"])
            reference_ids.update(
                {
                    "skills": frozenset(
                        row["WazaID"]
                        for row in levels.values()
                        if isinstance(row.get("WazaID"), str) and row["WazaID"]
                    ),
                    "passives": frozenset(passives),
                }
            )
        elif domain == "technology":
            character_rows = {}
            for filename in ("pal_data.json", "human_data.json"):
                character_rows.update(
                    json.loads(
                        (Path(assets) / "data" / filename).read_text(encoding="utf-8")
                    )
                )
            reference_ids["characters"] = frozenset(character_rows)
        sources = SourceInventory(
            present_sources=frozenset(
                source
                for selected_domain in selected_domains
                for source in policy["domains"][selected_domain]["required_sources"]
            ),
            reference_ids=reference_ids,
            available_icons=(
                frozenset(
                    f"icons/pals/{path.name}"
                    for path in (Path(assets) / "icons/pals").glob("*.png")
                )
                if domain == "technology"
                else frozenset()
            ),
            approved_static_icons=approved_static_icons,
        )
        checked = check_domains(domain, export_root, policy, sources, existing)
        if checked.errors:
            raise ValueError("; ".join(checked.errors))
        changed_by_domain = {}
        for selected_domain, selected_candidate in checked.candidates.items():
            changed_by_domain[selected_domain] = [
                relative
                for relative, data in selected_candidate.outputs.items()
                if not (target := Path(assets).joinpath(*relative.split("/"))).is_file()
                or target.read_bytes() != data
            ]
        if domain == "all":
            result = {
                "status": "ok",
                "domain": "all",
                "game_build": build_id,
                "domains": {
                    selected_domain: {
                        "changed_paths": changed_by_domain[selected_domain],
                        "output_counts": selected_candidate.output_counts,
                        "missing_localizations": len(
                            selected_candidate.missing_localizations
                        ),
                        "missing_icons": list(selected_candidate.missing_icons),
                        "diagnostics": list(selected_candidate.diagnostics),
                        "character_metrics": (
                            game_data.character_snapshot_metrics(selected_candidate)
                            if selected_domain == "characters"
                            else None
                        ),
                    }
                    for selected_domain, selected_candidate in checked.candidates.items()
                },
            }
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
            return result
        candidate = checked.candidates[domain]
        changed = changed_by_domain[domain]
        stage = work / "stage"
        _stage_outputs(stage, candidate.outputs)
        deletion_proposal = None
        if domain == "characters":
            deletion_proposal = game_data.build_legacy_deletion_proposal(
                domain,
                candidate,
                Path(assets),
                LEGACY_OWNERSHIP_CANDIDATE,
                LEGACY_OWNERSHIP,
                existing=existing,
            )
            if deletion_proposal is not None:
                CHARACTER_DELETION_PROPOSAL.write_text(
                    json.dumps(deletion_proposal, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
        if write:
            publish_domain(
                stage,
                Path(assets),
                domain,
                candidate,
                existing,
                policy=policy,
                sources=sources,
                provenance_path=Path(provenance_path),
            )
    result = {
        "status": "written" if write else "ok",
        "domain": domain,
        "game_build": build_id,
        "changed_paths": changed,
        "output_counts": candidate.output_counts,
        "missing_localizations": len(candidate.missing_localizations),
        "missing_icons": list(candidate.missing_icons),
        "diagnostics": list(candidate.diagnostics),
        "character_metrics": (
            game_data.character_snapshot_metrics(candidate)
            if domain == "characters"
            else None
        ),
        "deletion_count": (
            len(deletion_proposal["paths"]) if deletion_proposal is not None else 0
        ),
        "deletion_plan_sha256": (
            deletion_proposal["plan_sha256"] if deletion_proposal is not None else None
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--doctor", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    parser.add_argument(
        "--domain",
        choices=("skills", "characters", "progression", "technology", "all"),
    )
    parser.add_argument("--game-dir", type=Path)
    parser.add_argument("--uex", type=Path)
    parser.add_argument("--usmap", type=Path)
    parser.add_argument("--allow-unknown-build-write", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        if args.doctor:
            run_doctor(game_dir=args.game_dir, uex=args.uex, usmap=args.usmap)
            return 0
        if args.domain is None:
            raise ValueError("--check and --write require --domain")
        run_domain(
            domain=args.domain,
            write=args.write,
            game_dir=args.game_dir,
            uex=args.uex,
            usmap=args.usmap,
            allow_unknown_build_write=args.allow_unknown_build_write,
        )
        return 0
    except (
        OSError,
        TypeError,
        ValueError,
        RuntimeError,
        NotImplementedError,
        subprocess.CalledProcessError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
