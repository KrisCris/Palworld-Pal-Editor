"""Build immutable local scenario-review candidates without publishing runtime files."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from dataclasses import asdict
from pathlib import Path

import extract_game_data
import game_data


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_rows(data: bytes) -> dict:
    value = json.loads(data.decode("utf-8"))
    if not isinstance(value, dict):
        raise TypeError("candidate JSON output must be an object")
    return value


def _field_delta(before: dict, after: dict) -> dict:
    changed = {}
    for key in sorted(before.keys() | after.keys(), key=str.casefold):
        old = before.get(key)
        new = after.get(key)
        if old == new:
            continue
        if key not in before:
            changed[key] = {"before_missing": True, "after": new}
        elif key not in after:
            changed[key] = {"before": old, "after_missing": True}
        else:
            changed[key] = {"before": old, "after": new}
    return changed


def _json_delta(before: bytes | None, after: bytes) -> dict:
    old_rows = {} if before is None else _json_rows(before)
    new_rows = _json_rows(after)
    added = sorted(new_rows.keys() - old_rows.keys(), key=str.casefold)
    deleted = sorted(old_rows.keys() - new_rows.keys(), key=str.casefold)
    changed = {
        row_id: _field_delta(old_rows[row_id], new_rows[row_id])
        for row_id in sorted(old_rows.keys() & new_rows.keys(), key=str.casefold)
        if old_rows[row_id] != new_rows[row_id]
    }
    return {
        "added_ids": added,
        "deleted_ids": deleted,
        "changed_rows": changed,
    }


def _write_outputs(root: Path, outputs: dict[str, bytes]) -> None:
    for relative, data in sorted(outputs.items()):
        target = root.joinpath(*relative.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def _manifest(candidate: game_data.DomainSnapshot) -> dict:
    manifest = game_data.candidate_manifest(candidate)
    return {
        "domain": candidate.domain,
        "identity": asdict(candidate.identity),
        "policy_sha256": candidate.policy_sha256,
        "source_counts": dict(sorted(manifest.source_counts.items())),
        "output_counts": dict(sorted(manifest.output_counts.items())),
        "output_hashes": dict(sorted(manifest.output_hashes.items())),
        "missing_references": list(manifest.missing_references),
        "missing_localizations": list(manifest.missing_localizations),
        "missing_icons": list(manifest.missing_icons),
        "managed_paths": list(manifest.managed_paths),
        "output_root_sha256": game_data.canonical_output_root_sha256(candidate.outputs),
    }


def _skills_invariants(candidate: game_data.DomainSnapshot) -> dict:
    active = _json_rows(candidate.outputs["data/pal_attacks.json"])
    passive = _json_rows(candidate.outputs["data/pal_passives.json"])
    groups = {
        "active_ids": set(active),
        "passive_ids": set(passive),
        "legal_fruit_ids": {
            key for key, row in active.items() if row.get("SkillFruit") is True
        },
        "exclusive_ids": {
            key for key, row in active.items() if row.get("Exclusive") is True
        },
        "boss_skill_ids": {
            key for key, row in active.items() if row.get("BossSkill") is True
        },
    }
    return {
        name: {
            "count": len(values),
            "sha256": game_data._canonical_id_set_sha256(values),
        }
        for name, values in groups.items()
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--game-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"candidate output already exists: {output}")
    output.mkdir(parents=True)

    game = extract_game_data.find_game_dir(args.game_dir)
    build_id = extract_game_data.detect_build_id(game)
    toolchain = extract_game_data.ensure_toolchain(extract_game_data._default_cache())
    policy = json.loads(json.dumps(extract_game_data._POLICY))
    policy["bootstrap"]["game_build"] = build_id
    runtime = extract_game_data.RUNTIME_ASSETS
    existing = extract_game_data._load_manifest(game_data.PROVENANCE_PATH, policy)

    review = {
        "game_build": build_id,
        "toolchain": {
            "uex_revision": toolchain.uex_revision,
            "mapping_sha256": toolchain.mapping_sha256,
        },
        "domains": {},
    }
    candidates = {}
    for domain in ("characters", "skills"):
        with tempfile.TemporaryDirectory(
            prefix=f"scenario-candidate-{domain}-"
        ) as directory:
            work = Path(directory)
            export_root = work / "export"
            exporter = (
                extract_game_data.export_character_domain
                if domain == "characters"
                else extract_game_data.export_skill_domain
            )
            exporter(
                toolchain,
                game / extract_game_data._PAK_RELATIVE.parent,
                export_root,
                work / "profiles",
            )
            candidate = game_data.build_domain(domain, export_root, policy)
        candidates[domain] = candidate
        domain_root = output / domain
        _write_outputs(domain_root / "outputs", candidate.outputs)
        manifest = _manifest(candidate)
        (domain_root / "candidate-manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        old_entry = existing.domains.get(domain)
        old_paths = set(old_entry.managed_paths) if old_entry else set()
        new_paths = set(candidate.outputs)
        added = sorted(new_paths - old_paths)
        deleted = sorted(old_paths - new_paths)
        changed = []
        unchanged = []
        json_deltas = {}
        for relative, data in sorted(candidate.outputs.items()):
            target = runtime.joinpath(*relative.split("/"))
            before = target.read_bytes() if target.is_file() else None
            if before == data:
                unchanged.append(relative)
                continue
            changed.append(relative)
            if relative.endswith(".json"):
                json_deltas[relative] = _json_delta(before, data)
        png_added = [path for path in added if path.endswith(".png")]
        png_deleted = [path for path in deleted if path.endswith(".png")]
        png_changed = [path for path in changed if path.endswith(".png")]
        review["domains"][domain] = {
            "manifest": manifest,
            "added_paths": added,
            "deleted_paths": deleted,
            "changed_paths": changed,
            "unchanged_path_count": len(unchanged),
            "json_deltas": json_deltas,
            "png_delta": {
                "added": png_added,
                "changed": png_changed,
                "deleted": png_deleted,
            },
        }

    characters = candidates["characters"]
    json_outputs = {
        path: {
            "count": characters.output_counts[path],
            "sha256": characters.hashes[path],
        }
        for path in (
            "data/human_data.json",
            "data/pal_data.json",
            "data/skin_data.json",
        )
    }
    review["proposed_known_build_invariants"] = {
        "characters": {
            build_id: {
                "json_outputs": json_outputs,
                "output_count": len(characters.outputs),
                "output_root_sha256": game_data.canonical_output_root_sha256(
                    characters.outputs
                ),
            }
        },
        "skills_observed_id_sets": _skills_invariants(candidates["skills"]),
    }
    review["candidate_tree_sha256"] = _sha256(
        json.dumps(
            {
                domain: dict(sorted(candidate.hashes.items()))
                for domain, candidate in sorted(candidates.items())
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    (output / "scenario-tag-review-package.json").write_text(
        json.dumps(review, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
