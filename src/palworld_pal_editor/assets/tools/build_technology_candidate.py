"""Build one immutable technology candidate without publishing runtime assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

import extract_game_data as extractor
import game_data


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"immutable candidate already exists: {output}")

    assets = extractor.RUNTIME_ASSETS
    policy = json.loads(extractor.POLICY_PATH.read_text(encoding="utf-8"))
    game = extractor.find_game_dir()
    policy["bootstrap"]["game_build"] = extractor.detect_build_id(game)
    toolchain = extractor.ensure_toolchain(extractor._default_cache())
    existing = extractor._load_manifest(game_data.PROVENANCE_PATH, policy)

    with tempfile.TemporaryDirectory(prefix="pal-game-data-technology-candidate-") as tmp:
        work = Path(tmp)
        export_root = work / "export"
        extractor.export_technology_domain(
            toolchain,
            game / extractor._PAK_RELATIVE.parent,
            export_root,
            work / "profiles",
        )
        character_rows = {}
        for filename in ("pal_data.json", "human_data.json"):
            character_rows.update(
                json.loads((assets / "data" / filename).read_text(encoding="utf-8"))
            )
        sources = game_data.SourceInventory(
            present_sources=frozenset(policy["domains"]["technology"]["required_sources"]),
            reference_ids={"characters": frozenset(character_rows)},
            available_icons=frozenset(
                f"icons/pals/{path.name}"
                for path in (assets / "icons/pals").glob("*.png")
            ),
            approved_static_icons=frozenset(),
        )
        checked = game_data.check_domains(
            "technology", export_root, policy, sources, existing
        )
        if checked.errors:
            raise ValueError("; ".join(checked.errors))
        candidate = checked.candidates["technology"]
        proposal = game_data.build_legacy_deletion_proposal(
            "technology",
            candidate,
            assets,
            extractor.LEGACY_OWNERSHIP_CANDIDATE,
            extractor.LEGACY_OWNERSHIP,
            existing=existing,
        )

        output.mkdir(parents=True)
        stage = output / "candidate"
        extractor._stage_outputs(stage, candidate.outputs)
        changed = []
        for relative, data in sorted(candidate.outputs.items()):
            current = assets.joinpath(*relative.split("/"))
            if not current.is_file() or current.read_bytes() != data:
                changed.append(relative)
        report = {
            "schema_version": 1,
            "domain": "technology",
            "game_build": candidate.identity.game_build,
            "source_counts": dict(sorted(candidate.source_counts.items())),
            "output_counts": dict(sorted(candidate.output_counts.items())),
            "output_hashes": dict(sorted(candidate.hashes.items())),
            "candidate_root_sha256": game_data.canonical_output_root_sha256(
                candidate.outputs
            ),
            "changed_paths": changed,
            "missing_localizations": list(candidate.missing_localizations),
            "missing_icons": list(candidate.missing_icons),
            "diagnostics": list(candidate.diagnostics),
            "deletion_count": len(proposal["paths"]) if proposal is not None else 0,
            "rename_count": len(proposal["renames"]) if proposal is not None else 0,
            "case_only_renames": (
                list(proposal["renames"]) if proposal is not None else []
            ),
            "deletion_plan_sha256": (
                proposal["plan_sha256"] if proposal is not None else None
            ),
            "runtime_non_technology_sha256": {
                path.relative_to(assets).as_posix(): sha256(path.read_bytes())
                for root in (assets / "data", assets / "icons/pals")
                for path in sorted(root.rglob("*"))
                if path.is_file() and path.name != "tech_data.json"
            },
        }
        (output / "review.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        if proposal is not None:
            (output / "deletion-proposal.json").write_text(
                json.dumps(proposal, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        print(
            json.dumps(
                {
                    "output": str(output),
                    "counts": candidate.output_counts,
                    "changed": len(changed),
                    "deletions": len(proposal["paths"]) if proposal is not None else 0,
                    "renames": len(proposal["renames"]) if proposal is not None else 0,
                    "diagnostics": candidate.diagnostics,
                    "root_sha256": report["candidate_root_sha256"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
