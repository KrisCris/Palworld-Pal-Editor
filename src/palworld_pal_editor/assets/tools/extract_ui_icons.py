"""Extract the small, allowlisted Palworld UI icon set used by the WebUI."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path

from extract_game_data import (
    RUNTIME_ASSETS,
    _default_cache,
    detect_build_id,
    ensure_toolchain,
    export_sources,
    find_game_dir,
    require_write_build,
)

UI_ICON_SOURCES = (
    ("stat-health", "Pal/Content/Pal/Texture/UI/Main_Menu/T_icon_status_00"),
    ("stat-attack", "Pal/Content/Pal/Texture/UI/Main_Menu/T_icon_status_02"),
    ("stat-defense", "Pal/Content/Pal/Texture/UI/Main_Menu/T_icon_status_03"),
    (
        "stat-work-speed",
        "Pal/Content/Pal/Texture/StatusParameterIcon/T_icon_status_work_speed",
    ),
    (
        "friendship",
        "Pal/Content/Pal/Texture/UI/Main_Menu/T_Icon_PalFriendship_Color",
    ),
    (
        "gender-male",
        "Pal/Content/Pal/Texture/UI/Main_Menu/T_Icon_PanGender_Male",
    ),
    (
        "gender-female",
        "Pal/Content/Pal/Texture/UI/Main_Menu/T_Icon_PanGender_Female",
    ),
    ("rare", "Pal/Content/Pal/Texture/UI/InGame/T_icon_pal_rare"),
    ("boss", "Pal/Content/Pal/Texture/UI/InGame/T_icon_enemy_strong"),
    ("condense", "Pal/Content/Pal/Texture/UI/IngameMenu/T_icon_condense"),
    ("soul", "Pal/Content/Pal/Texture/UI/IngameMenu/T_icon_buildup"),
    (
        "heal",
        "Pal/Content/Pal/Texture/UI/InGame/SkillIcon/T_icon_skill_pal_HPRecovery",
    ),
    (
        "revive",
        "Pal/Content/Pal/Texture/UI/InGame/SkillIcon/T_icon_skill_pal_Revive",
    ),
)

UI_ICON_DIMENSIONS = {
    "stat-health": (24, 24),
    "stat-attack": (24, 24),
    "stat-defense": (24, 24),
    "stat-work-speed": (256, 256),
    "friendship": (64, 64),
    "gender-male": (34, 34),
    "gender-female": (34, 34),
    "rare": (36, 36),
    "boss": (64, 64),
    "condense": (28, 32),
    "soul": (36, 36),
    "heal": (128, 128),
    "revive": (128, 128),
}

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_LOGICAL_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


def validate_icon_sources(sources: Mapping[str, str]) -> None:
    seen_sources = set()
    for logical_name, source in sources.items():
        if not _LOGICAL_NAME.fullmatch(logical_name):
            raise ValueError(f"invalid UI icon logical name: {logical_name!r}")
        if (
            not source.startswith("Pal/Content/")
            or "\\" in source
            or Path(source).suffix
        ):
            raise ValueError(f"invalid UI icon source for {logical_name}: {source!r}")
        folded = source.casefold()
        if folded in seen_sources:
            raise ValueError(f"duplicate UI icon source: {source}")
        seen_sources.add(folded)


def _png_dimensions(data: bytes) -> tuple[int, int] | None:
    if len(data) < 24 or not data.startswith(_PNG_SIGNATURE):
        return None
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def _png_bytes(path: Path, logical_name: str) -> bytes:
    if not path.is_file():
        raise FileNotFoundError(f"missing exported UI icon {logical_name}: {path}")
    data = path.read_bytes()
    expected = UI_ICON_DIMENSIONS[logical_name]
    if _png_dimensions(data) != expected:
        width, height = expected
        raise ValueError(
            f"invalid exported UI icon PNG for {logical_name}; "
            f"expected {width}x{height}: {path}"
        )
    return data


def collect_outputs(export_root: Path) -> dict[str, bytes]:
    sources = dict(UI_ICON_SOURCES)
    validate_icon_sources(sources)
    outputs = {}
    for logical_name, source in UI_ICON_SOURCES:
        exported = Path(export_root).joinpath(*source.split("/")).with_suffix(".png")
        outputs[f"icons/ui/{logical_name}.png"] = _png_bytes(
            exported, logical_name
        )
    return outputs


def _expected_output_paths() -> set[str]:
    return {f"icons/ui/{logical_name}.png" for logical_name, _ in UI_ICON_SOURCES}


def _validated_outputs(outputs: Mapping[str, bytes]) -> None:
    expected = _expected_output_paths()
    if set(outputs) != expected:
        raise ValueError("UI icon outputs must match the exact managed allowlist")
    for relative, data in outputs.items():
        logical_name = Path(relative).stem
        if (
            not isinstance(data, bytes)
            or _png_dimensions(data) != UI_ICON_DIMENSIONS[logical_name]
        ):
            raise ValueError(f"invalid UI icon output bytes: {relative}")


def check_outputs(outputs: Mapping[str, bytes], assets: Path) -> list[str]:
    _validated_outputs(outputs)
    assets = Path(assets)
    return [
        relative
        for relative, expected in sorted(outputs.items())
        if not (target := assets.joinpath(*relative.split("/"))).is_file()
        or target.read_bytes() != expected
    ]


def write_outputs(
    outputs: Mapping[str, bytes],
    assets: Path,
    *,
    replace_file=os.replace,
) -> None:
    _validated_outputs(outputs)
    assets = Path(assets)
    assets.mkdir(parents=True, exist_ok=True)
    originals = {}
    targets = {
        relative: assets.joinpath(*relative.split("/"))
        for relative in sorted(outputs)
    }
    with tempfile.TemporaryDirectory(dir=assets, prefix=".ui-icons-") as directory:
        stage = Path(directory)
        for relative, target in targets.items():
            originals[relative] = target.read_bytes() if target.is_file() else None
            staged = stage / Path(relative).name
            staged.write_bytes(outputs[relative])
        try:
            for relative, target in targets.items():
                target.parent.mkdir(parents=True, exist_ok=True)
                replace_file(stage / Path(relative).name, target)
        except OSError:
            for relative, target in targets.items():
                original = originals[relative]
                if original is None:
                    target.unlink(missing_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(original)
            raise


def run(
    *,
    write: bool,
    game_dir: Path | None = None,
    uex: Path | None = None,
    usmap: Path | None = None,
    allow_unknown_build_write: bool = False,
    assets: Path = RUNTIME_ASSETS,
) -> dict:
    game = find_game_dir(game_dir)
    build_id = detect_build_id(game)
    if write:
        require_write_build(build_id, allow_unknown_build_write)
    toolchain = ensure_toolchain(_default_cache(), uex=uex, usmap=usmap)
    with tempfile.TemporaryDirectory(prefix="pal-ui-icons-") as directory:
        work = Path(directory)
        export_root = work / "export"
        export_sources(
            toolchain,
            game / "Pal/Content/Paks",
            export_root,
            work / "profiles",
            set(dict(UI_ICON_SOURCES).values()),
        )
        outputs = collect_outputs(export_root)
        drift = check_outputs(outputs, assets)
        if write:
            write_outputs(outputs, assets)
            drift = check_outputs(outputs, assets)
    result = {
        "build_id": build_id,
        "mode": "write" if write else "check",
        "managed_icons": len(outputs),
        "drift": drift,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if drift:
        raise ValueError(f"UI icon drift: {', '.join(drift)}")
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    parser.add_argument("--game-dir", type=Path)
    parser.add_argument("--uex", type=Path)
    parser.add_argument("--usmap", type=Path)
    parser.add_argument("--allow-unknown-build-write", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        run(
            write=args.write,
            game_dir=args.game_dir,
            uex=args.uex,
            usmap=args.usmap,
            allow_unknown_build_write=args.allow_unknown_build_write,
        )
        return 0
    except (OSError, TypeError, ValueError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
