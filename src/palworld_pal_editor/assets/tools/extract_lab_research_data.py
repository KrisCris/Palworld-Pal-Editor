"""Extract the runtime laboratory research catalogue from an installed game."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from collections.abc import Mapping
from pathlib import Path

import extract_game_data
from game_data import load_asset, load_table


SOURCE = "Pal/Content/Pal/DataTable/Lab/DT_LabResearchDataTable"
ICON_WIDGET = (
    "Pal/Content/Pal/Blueprint/UI/UserInterface/IngameMenu/Research/"
    "WBP_ResearchEffectIcon"
)
ASSETS = Path(__file__).parents[1]
OUTPUT_PATH = ASSETS / "data/lab_research.json"
ICON_OUTPUT = ASSETS / "icons/lab"
PROVENANCE_PATH = Path(__file__).with_name("lab_research_provenance.json")
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _enum_tail(value: str, field: str, row_id: str) -> str:
    if not isinstance(value, str) or "::" not in value:
        raise ValueError(f"{row_id}.{field} is not a namespaced enum")
    return value.rsplit("::", 1)[1]


def _optional_name(value: object, field: str, row_id: str) -> str | None:
    if not isinstance(value, str):
        raise ValueError(f"{row_id}.{field} is not a name")
    return None if value.casefold() == "none" else value


def _texture_virtual_path(value: object, label: str) -> str:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be a soft object path")
    asset_path = value.get("AssetPathName")
    if (
        not isinstance(asset_path, str)
        or not asset_path.startswith("/Game/")
        or "." not in asset_path
    ):
        raise TypeError(f"{label}.AssetPathName must be a game object path")
    package, object_name = asset_path.split(".", 1)
    if not object_name or package.rsplit("/", 1)[-1] != object_name:
        raise ValueError(f"{label}.AssetPathName package/object mismatch")
    return f"Pal/Content/{package.removeprefix('/Game/')}"


def _icon_map(entries: object, enum_name: str) -> dict[str, str]:
    if not isinstance(entries, list):
        raise TypeError(f"{enum_name} icon map must be a list")
    output = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise TypeError(f"{enum_name}[{index}] must be an object")
        key = _enum_tail(entry.get("Key"), "Key", f"{enum_name}[{index}]")
        if key in output:
            raise ValueError(f"duplicate {enum_name} icon: {key}")
        output[key] = _texture_virtual_path(
            entry.get("Value"), f"{enum_name}[{index}].Value"
        )
    return output


def load_icon_maps(export_root: Path) -> tuple[dict[str, str], dict[str, str]]:
    asset = load_asset(export_root, ICON_WIDGET)
    defaults = [
        item
        for item in asset
        if item.get("Name") == "Default__WBP_ResearchEffectIcon_C"
    ]
    if len(defaults) != 1 or not isinstance(defaults[0].get("Properties"), dict):
        raise ValueError("research icon widget has no unique class defaults")
    properties = defaults[0]["Properties"]
    return (
        _icon_map(properties.get("MainTypeIcons"), "EPalWorkSuitability"),
        _icon_map(properties.get("SubTypeIcons"), "EPalLabCategorySubType"),
    )


def project(
    rows: dict[str, dict],
    category_icons: Mapping[str, str],
    effect_icons: Mapping[str, str],
) -> dict[str, dict]:
    records: dict[str, dict] = {}
    for research_id, row in rows.items():
        required_work = row.get("RequiredWorkAmount")
        effect_value = row.get("EffectValue")
        if (
            not isinstance(required_work, (int, float))
            or isinstance(required_work, bool)
            or required_work <= 0
        ):
            raise ValueError(f"{research_id}.RequiredWorkAmount must be positive")
        if not isinstance(effect_value, (int, float)) or isinstance(effect_value, bool):
            raise ValueError(f"{research_id}.EffectValue must be numeric")

        materials = []
        for index in range(1, 5):
            item_id = _optional_name(
                row.get(f"Material{index}_Id"),
                f"Material{index}_Id",
                research_id,
            )
            count = row.get(f"Material{index}_Count")
            if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                raise ValueError(
                    f"{research_id}.Material{index}_Count must be a nonnegative integer"
                )
            if item_id is not None and count:
                materials.append({"ItemId": item_id, "Count": count})

        category = _enum_tail(
            row["LabCategoryWorkSuitability"],
            "LabCategoryWorkSuitability",
            research_id,
        )
        sub_category = _enum_tail(
            row["LabCategorySubType"], "LabCategorySubType", research_id
        )
        if category not in category_icons:
            raise ValueError(f"{research_id} has no game category icon: {category}")
        if sub_category not in effect_icons:
            raise ValueError(f"{research_id} has no game effect icon: {sub_category}")

        records[research_id] = {
            "TextId": str(row["TextId"]),
            "Category": category,
            "CategoryIconKey": f"category-{category}",
            "SubCategory": sub_category,
            "IconKey": f"effect-{sub_category}",
            "RequiredWorkAmount": required_work,
            "RequiredResearchId": _optional_name(
                row["RequiredResearchId"], "RequiredResearchId", research_id
            ),
            "EffectType": _enum_tail(row["EffectType"], "EffectType", research_id),
            "EffectValue": effect_value,
            "EffectWorkSuitability": _enum_tail(
                row["EffectOptionWorkSuitability"],
                "EffectOptionWorkSuitability",
                research_id,
            ),
            "EffectItemType": _enum_tail(
                row["EffectOptionItemType"],
                "EffectOptionItemType",
                research_id,
            ),
            "EffectDescriptionTextId": _optional_name(
                row["EffectDescriptionTextIdOverwrite"],
                "EffectDescriptionTextIdOverwrite",
                research_id,
            ),
            "Essential": bool(row["bIsEssential"]),
            "Materials": materials,
        }
    return records


def _png_bytes(path: Path, label: str) -> bytes:
    if not path.is_file():
        raise FileNotFoundError(f"missing exported laboratory icon {label}: {path}")
    data = path.read_bytes()
    dimensions = (
        int.from_bytes(data[16:20], "big"),
        int.from_bytes(data[20:24], "big"),
    )
    if len(data) < 24 or not data.startswith(_PNG_SIGNATURE) or dimensions != (80, 80):
        raise ValueError(f"invalid 80x80 laboratory icon PNG {label}: {path}")
    return data


def extract(
    game_dir: Path | None = None,
) -> tuple[dict[str, dict], dict[str, bytes], dict]:
    game = extract_game_data.find_game_dir(game_dir)
    build_id = extract_game_data.detect_build_id(game)
    toolchain = extract_game_data.ensure_toolchain(extract_game_data._default_cache())
    with tempfile.TemporaryDirectory(prefix="pal-lab-research-") as directory:
        work = Path(directory)
        export_root = work / "export"
        extract_game_data.export_sources(
            toolchain,
            game / extract_game_data._PAK_RELATIVE.parent,
            export_root,
            work / "profiles",
            {SOURCE, ICON_WIDGET},
        )
        category_icons, effect_icons = load_icon_maps(export_root)
        records = project(
            load_table(export_root, SOURCE), category_icons, effect_icons
        )
        used_category_icons = {
            definition["Category"]: category_icons[definition["Category"]]
            for definition in records.values()
        }
        used_effect_icons = {
            definition["SubCategory"]: effect_icons[definition["SubCategory"]]
            for definition in records.values()
        }
        extract_game_data.export_sources(
            toolchain,
            game / extract_game_data._PAK_RELATIVE.parent,
            export_root,
            work / "icon-profiles",
            set(used_category_icons.values()) | set(used_effect_icons.values()),
        )
        icons = {}
        for prefix, sources in (
            ("category", used_category_icons),
            ("effect", used_effect_icons),
        ):
            for key, source in sources.items():
                path = export_root.joinpath(*source.split("/")).with_suffix(".png")
                icons[f"{prefix}-{key}.png"] = _png_bytes(path, f"{prefix}-{key}")
    return records, icons, {
        "schema_version": 1,
        "game_build": build_id,
        "source": SOURCE,
        "icon_source": ICON_WIDGET,
        "row_count": len(records),
        "icon_count": len(icons),
        "uex_revision": toolchain.uex_revision,
        "mapping_sha256": toolchain.mapping_sha256,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-dir", type=Path)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    records, icons, provenance = extract(args.game_dir)
    encoded = (
        json.dumps(records, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    )
    provenance["output_sha256"] = hashlib.sha256(encoded).hexdigest()
    provenance["icon_sha256"] = {
        name: hashlib.sha256(data).hexdigest()
        for name, data in sorted(icons.items())
    }
    print(json.dumps(provenance, ensure_ascii=False, indent=2, sort_keys=True))
    if args.write:
        OUTPUT_PATH.write_bytes(encoded)
        ICON_OUTPUT.mkdir(parents=True, exist_ok=True)
        for name, data in icons.items():
            (ICON_OUTPUT / name).write_bytes(data)
        PROVENANCE_PATH.write_text(
            json.dumps(provenance, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
