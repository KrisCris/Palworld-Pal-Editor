"""Extract the runtime laboratory research catalogue from an installed game."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

import extract_game_data
from game_data import load_table


SOURCE = "Pal/Content/Pal/DataTable/Lab/DT_LabResearchDataTable"
ASSETS = Path(__file__).parents[1]
OUTPUT_PATH = ASSETS / "data/lab_research.json"
PROVENANCE_PATH = Path(__file__).with_name("lab_research_provenance.json")


def _enum_tail(value: str, field: str, row_id: str) -> str:
    if not isinstance(value, str) or "::" not in value:
        raise ValueError(f"{row_id}.{field} is not a namespaced enum")
    return value.rsplit("::", 1)[1]


def _optional_name(value: object, field: str, row_id: str) -> str | None:
    if not isinstance(value, str):
        raise ValueError(f"{row_id}.{field} is not a name")
    return None if value.casefold() == "none" else value


def project(rows: dict[str, dict]) -> dict[str, dict]:
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

        records[research_id] = {
            "TextId": str(row["TextId"]),
            "Category": _enum_tail(
                row["LabCategoryWorkSuitability"],
                "LabCategoryWorkSuitability",
                research_id,
            ),
            "SubCategory": _enum_tail(
                row["LabCategorySubType"], "LabCategorySubType", research_id
            ),
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


def extract(game_dir: Path | None = None) -> tuple[dict[str, dict], dict]:
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
            {SOURCE},
        )
        records = project(load_table(export_root, SOURCE))
    return records, {
        "schema_version": 1,
        "game_build": build_id,
        "source": SOURCE,
        "row_count": len(records),
        "uex_revision": toolchain.uex_revision,
        "mapping_sha256": toolchain.mapping_sha256,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-dir", type=Path)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    records, provenance = extract(args.game_dir)
    encoded = (
        json.dumps(records, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    )
    provenance["output_sha256"] = hashlib.sha256(encoded).hexdigest()
    print(json.dumps(provenance, ensure_ascii=False, indent=2, sort_keys=True))
    if args.write:
        OUTPUT_PATH.write_bytes(encoded)
        PROVENANCE_PATH.write_text(
            json.dumps(provenance, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
