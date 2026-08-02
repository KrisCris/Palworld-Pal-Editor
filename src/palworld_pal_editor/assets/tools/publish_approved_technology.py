"""Publish only the independently reviewed build-24181527 technology candidate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import extract_game_data as extract
import game_data

ROOT = Path(__file__).resolve().parents[4]
ASSETS = extract.RUNTIME_ASSETS
CANDIDATE_PACKAGE = (
    ROOT
    / "output/task7-technology/final-review-candidate-24181527-20260726-193133"
)
APPROVAL_PATH = (
    ROOT
    / "output/task7-technology/approval-change-24181527-20260726-193746/"
    "technology-change-approval.json"
)
CREDENTIAL_PATH = (
    ROOT
    / "output/task7-technology/publication-credential-v2-24181527-20260726-194834/"
    "technology-publication-credential.json"
)
SOURCE_PATHS = {
    "game_data.py": Path(game_data.__file__),
    "extract_game_data.py": Path(extract.__file__),
    "policy.json": extract.POLICY_PATH,
    "test_pipeline.py": Path(game_data.__file__).with_name("test_pipeline.py"),
    "test_technology_publisher.py": Path(game_data.__file__).with_name(
        "test_technology_publisher.py"
    ),
}
EXPECTED = {
    "review_sha256": "9c8ad6028abd73d46f225f43958794e21c25881d82019fbdc7c2a57dcd6ede5d",
    "proposal_sha256": "e71ee92cdc45b42f9eea04c8511f27f754959fe971f790df4dcd5f38ddb92297",
    "approval_sha256": "115c4a9794b513ab83d1e8bbd885ed8f3e9e2cba23beb20ca3c759cba2053f29",
    "credential_sha256": "eab2972eed42270f9aa80676eacdd5132a9630f0989cf5ddb59f3214b9c69045",
    "output_root_sha256": "26f8fb888454e39fe7291d952696a92a48a1b16301ba8a47b24e67f8af41b233",
    "json_sha256": "27428f3f0d23eda01fde01eb51aa7c42d510965900b78f66c1f648488f2a206e",
    "output_count": 465,
    "game_build": "24181527",
    "policy_sha256": "525a5269290c71ab4383eae63d5703276b63483c05f36a5f9f2b72d2f29113a4",
    "plan_sha256": "6a36efca5f682227a7682335055c6606fed7fa3513de9c9526aa3dd190bb4f6b",
    "paths": (
        "icons/tech/Battle_RangeWeapon_BowGun_Fire.png",
        "icons/tech/Battle_RangeWeapon_BowGun_Poison.png",
        "icons/tech/Battle_RangeWeapon_Bow_Fire.png",
        "icons/tech/Battle_RangeWeapon_Bow_Poison.png",
        "icons/tech/RepairKit.png",
    ),
    "renames": (
        ("icons/tech/OverHeatRifle.png", "icons/tech/OverheatRifle.png"),
        ("icons/tech/PalBox.png", "icons/tech/PALBOX.png"),
        ("icons/tech/ShotgunBullet.png", "icons/tech/ShotGunBullet.png"),
    ),
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def file_inventory(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def validate_static_bindings(
    candidate_package: Path,
    approval_path: Path,
    credential_path: Path,
    expected: dict,
    source_paths: dict[str, Path],
) -> tuple[dict, dict, dict, dict[str, bytes]]:
    candidate_package = Path(candidate_package)
    review_path = candidate_package / "review.json"
    proposal_path = candidate_package / "deletion-proposal.json"
    for path in (review_path, proposal_path, approval_path, credential_path):
        if not Path(path).is_file():
            raise FileNotFoundError(path)
    hashes = {
        "review_sha256": sha256_file(review_path),
        "proposal_sha256": sha256_file(proposal_path),
        "approval_sha256": sha256_file(Path(approval_path)),
        "credential_sha256": sha256_file(Path(credential_path)),
    }
    for key, actual in hashes.items():
        if actual != expected[key]:
            label = key.removesuffix("_sha256").replace("_", " ")
            raise ValueError(f"{label} SHA-256 changed: {actual}")

    review = json.loads(review_path.read_text(encoding="utf-8"))
    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    approval = json.loads(Path(approval_path).read_text(encoding="utf-8"))
    credential = json.loads(Path(credential_path).read_text(encoding="utf-8"))
    stage = candidate_package / "candidate"
    outputs = {
        path.relative_to(stage).as_posix(): path.read_bytes()
        for path in sorted(stage.rglob("*"))
        if path.is_file()
    }
    output_hashes = {path: sha256_bytes(data) for path, data in outputs.items()}
    reviewed_hashes = review.get("output_hashes")
    if not isinstance(reviewed_hashes, dict) or set(outputs) != set(reviewed_hashes):
        raise ValueError("candidate output paths differ from reviewed package")
    if output_hashes != reviewed_hashes:
        raise ValueError("candidate output hashes differ from reviewed package")
    if len(outputs) != expected["output_count"]:
        raise ValueError("candidate output count changed")
    if output_hashes.get("data/tech_data.json") != expected["json_sha256"]:
        raise ValueError("candidate technology JSON changed")
    if game_data.canonical_output_root_sha256(outputs) != expected[
        "output_root_sha256"
    ]:
        raise ValueError("candidate output root changed")

    snapshot = proposal.get("candidate_snapshot", {})
    paths = tuple(item.get("path") for item in proposal.get("paths", ()))
    renames = tuple(
        (item.get("from_path"), item.get("to_path"))
        for item in proposal.get("renames", ())
    )
    if (
        review.get("schema_version") != 1
        or review.get("domain") != "technology"
        or review.get("game_build") != expected["game_build"]
        or review.get("candidate_root_sha256") != expected["output_root_sha256"]
        or snapshot.get("domain") != "technology"
        or snapshot.get("game_build") != expected["game_build"]
        or snapshot.get("policy_sha256") != expected["policy_sha256"]
        or snapshot.get("output_root_sha256") != expected["output_root_sha256"]
        or proposal.get("schema_version") != 3
        or proposal.get("kind") != "legacy_change_proposal"
        or proposal.get("plan_sha256") != expected["plan_sha256"]
        or paths != expected["paths"]
        or renames != expected["renames"]
        or review.get("deletion_count") != len(paths)
        or review.get("rename_count") != len(renames)
        or review.get("case_only_renames") != proposal.get("renames")
    ):
        raise ValueError("candidate review or change proposal binding changed")
    approval_fields = {
        "schema_version",
        "kind",
        "reviewer",
        "review_date",
        "approved_plan_sha256",
        "approved_deletions",
        "approved_renames",
    }
    if (
        set(approval) != approval_fields
        or approval.get("schema_version") != 2
        or approval.get("kind") != "legacy_change_approval"
        or approval.get("reviewer") == proposal["ownership_evidence"][
            "ownership_reviewer"
        ]
        or approval.get("approved_plan_sha256") != expected["plan_sha256"]
        or approval.get("approved_deletions") != proposal.get("paths")
        or approval.get("approved_renames") != proposal.get("renames")
    ):
        raise ValueError("change approval binding changed")
    if tuple(path.name for path in Path(approval_path).parent.iterdir()) != (
        Path(approval_path).name,
    ):
        raise ValueError("deletion approval package must contain exactly one file")

    credential_fields = {
        "schema_version",
        "kind",
        "reviewer",
        "review_date",
        "candidate_review_sha256",
        "change_proposal_sha256",
        "change_approval_sha256",
        "candidate_root_sha256",
        "policy_sha256",
        "game_build",
        "plan_sha256",
        "deletions",
        "renames",
        "source_sha256",
    }
    if (
        set(credential) != credential_fields
        or credential.get("schema_version") != 2
        or credential.get("kind") != "technology_publication_credential"
        or not isinstance(credential.get("reviewer"), str)
        or not credential["reviewer"].strip()
        or credential["reviewer"] == approval.get("reviewer")
        or credential.get("candidate_review_sha256") != hashes["review_sha256"]
        or credential.get("change_proposal_sha256") != hashes["proposal_sha256"]
        or credential.get("change_approval_sha256") != hashes["approval_sha256"]
        or credential.get("candidate_root_sha256") != expected["output_root_sha256"]
        or credential.get("policy_sha256") != expected["policy_sha256"]
        or credential.get("game_build") != expected["game_build"]
        or credential.get("plan_sha256") != expected["plan_sha256"]
        or credential.get("deletions") != proposal.get("paths")
        or credential.get("renames") != proposal.get("renames")
        or set(credential.get("source_sha256", {})) != set(source_paths)
    ):
        raise ValueError("publication credential binding changed")
    if tuple(path.name for path in Path(credential_path).parent.iterdir()) != (
        Path(credential_path).name,
    ):
        raise ValueError("publication credential package must contain exactly one file")
    for name, path in source_paths.items():
        actual = sha256_file(path)
        if actual != credential["source_sha256"][name]:
            raise ValueError(f"reviewed source changed: {name}={actual}")
    return review, proposal, approval, outputs


def _protected_runtime_inventory(assets: Path) -> dict[str, str]:
    roots = (Path(assets) / "data", Path(assets) / "icons/pals")
    return {
        path.relative_to(assets).as_posix(): sha256_file(path)
        for root in roots
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != "tech_data.json"
    }


def validate_runtime_bindings(assets: Path, review: dict, proposal: dict) -> None:
    assets = Path(assets)
    if _protected_runtime_inventory(assets) != review.get(
        "runtime_non_technology_sha256"
    ):
        raise ValueError("protected runtime drift detected")
    for item in proposal.get("paths", ()):
        target = assets.joinpath(*item["path"].split("/"))
        if not target.is_file() or sha256_file(target) != item["current_sha256"]:
            raise ValueError(f"technology runtime drift detected: {item['path']}")
    for item in proposal.get("renames", ()):
        source = item["from_path"]
        target = item["to_path"]
        source_path = assets.joinpath(*source.split("/"))
        if (
            source == target
            or source.casefold() != target.casefold()
            or game_data._actual_relative_case(assets, source) != source
            or not source_path.is_file()
            or sha256_file(source_path) != item["current_sha256"]
        ):
            raise ValueError(f"technology runtime drift detected: {source}")


def validate_publication_changes(
    before: dict[str, str],
    after: dict[str, str],
    proposal: dict,
    candidate_hashes: dict[str, str],
) -> dict[str, tuple]:
    deletion_paths = tuple(item["path"] for item in proposal.get("paths", ()))
    rename_pairs = tuple(
        (item["from_path"], item["to_path"])
        for item in proposal.get("renames", ())
    )
    rename_sources = {source for source, _ in rename_pairs}
    removed = set(before) - set(after)
    actual_deletions = tuple(sorted(removed - rename_sources))
    if actual_deletions != tuple(sorted(deletion_paths)):
        raise AssertionError(f"unexpected deletion set: {actual_deletions}")
    for item in proposal.get("renames", ()):
        source = item["from_path"]
        target = item["to_path"]
        if (
            source == target
            or source.casefold() != target.casefold()
            or before.get(source) != item["current_sha256"]
            or source in after
            or after.get(target) != item["candidate_sha256"]
            or candidate_hashes.get(target) != item["candidate_sha256"]
        ):
            raise AssertionError(f"case-only rename postcondition failed: {source}")
    return {"deletions": actual_deletions, "renames": rename_pairs}


def publish_atomic(
    stage: Path,
    assets: Path,
    candidate: game_data.DomainSnapshot,
    manifest: game_data.Manifest,
    policy: dict,
    sources: game_data.SourceInventory,
    provenance_path: Path,
    legacy_candidate_path: Path | None,
    legacy_ownership_path: Path | None,
    proposal: dict | None,
    approval: dict | None,
) -> game_data.Manifest:
    return game_data.publish_domain(
        stage,
        assets,
        "technology",
        candidate,
        manifest,
        policy=policy,
        sources=sources,
        provenance_path=provenance_path,
        legacy_candidate_path=legacy_candidate_path,
        legacy_ownership_path=legacy_ownership_path,
        legacy_deletion_proposal=proposal,
        legacy_deletion_approval=approval,
    )


def _candidate_from_artifacts(
    outputs: dict[str, bytes], review: dict, proposal: dict
) -> game_data.DomainSnapshot:
    snapshot = proposal["candidate_snapshot"]
    identity = game_data.BuildIdentity(
        snapshot["game_build"],
        snapshot["parser_revision"],
        snapshot["mapping_sha256"],
    )
    return game_data.snapshot_from_outputs(
        "technology",
        outputs,
        identity,
        snapshot["policy_sha256"],
        review["source_counts"],
        icon_dimensions={
            path: game_data._png_dimensions(data)
            for path, data in outputs.items()
            if path.endswith(".png")
        },
        missing_localizations=tuple(review["missing_localizations"]),
        missing_icons=tuple(review["missing_icons"]),
        diagnostics=tuple(review["diagnostics"]),
    )


def _source_inventory(assets: Path, policy: dict) -> game_data.SourceInventory:
    characters = {}
    for filename in ("pal_data.json", "human_data.json"):
        characters.update(
            json.loads((Path(assets) / "data" / filename).read_text(encoding="utf-8"))
        )
    return game_data.SourceInventory(
        present_sources=frozenset(policy["domains"]["technology"]["required_sources"]),
        reference_ids={"characters": frozenset(characters)},
        available_icons=frozenset(
            f"icons/pals/{path.name}"
            for path in (Path(assets) / "icons/pals").glob("*.png")
        ),
        approved_static_icons=frozenset(),
    )


def main() -> None:
    review, proposal, approval, outputs = validate_static_bindings(
        CANDIDATE_PACKAGE,
        APPROVAL_PATH,
        CREDENTIAL_PATH,
        EXPECTED,
        SOURCE_PATHS,
    )
    game = extract.find_game_dir()
    build = extract.detect_build_id(game)
    extract.require_write_build(build, False)
    if build != EXPECTED["game_build"]:
        raise ValueError(f"reviewed game build changed: {build}")
    policy = json.loads(json.dumps(extract._POLICY))
    policy["bootstrap"]["game_build"] = build
    if game_data.domain_policy_hash(policy, "technology") != EXPECTED["policy_sha256"]:
        raise ValueError("reviewed technology policy changed")
    candidate = _candidate_from_artifacts(outputs, review, proposal)
    sources = _source_inventory(ASSETS, policy)
    existing = extract._load_manifest(game_data.PROVENANCE_PATH, policy)
    fresh = game_data.build_legacy_deletion_proposal(
        "technology",
        candidate,
        ASSETS,
        extract.LEGACY_OWNERSHIP_CANDIDATE,
        extract.LEGACY_OWNERSHIP,
        existing=existing,
    )
    if fresh is not None and fresh != proposal:
        raise ValueError("fresh technology change proposal changed")
    active_proposal = fresh or {"paths": (), "renames": ()}
    if fresh is not None:
        validate_runtime_bindings(ASSETS, review, proposal)
    before = file_inventory(ASSETS)
    expected_after = dict(before)
    old_entry = existing.domains.get("technology")
    old_paths = set(old_entry.managed_paths) if old_entry is not None else set()
    for path in old_paths - set(candidate.outputs):
        expected_after.pop(path, None)
    for item in active_proposal["paths"]:
        expected_after.pop(item["path"])
    for item in active_proposal["renames"]:
        expected_after.pop(item["from_path"])
    expected_after.update(candidate.hashes)
    if fresh is not None:
        changes = validate_publication_changes(
            before, expected_after, proposal, candidate.hashes
        )
        validate_runtime_bindings(ASSETS, review, proposal)
    else:
        new_by_fold = {path.casefold(): path for path in candidate.outputs}
        changes = {
            "deletions": tuple(
                sorted(path for path in old_paths if path.casefold() not in new_by_fold)
            ),
            "renames": tuple(
                sorted(
                    (path, new_by_fold[path.casefold()])
                    for path in old_paths
                    if path.casefold() in new_by_fold
                    and path != new_by_fold[path.casefold()]
                )
            ),
        }
    validate_static_bindings(
        CANDIDATE_PACKAGE,
        APPROVAL_PATH,
        CREDENTIAL_PATH,
        EXPECTED,
        SOURCE_PATHS,
    )
    publish_atomic(
        CANDIDATE_PACKAGE / "candidate",
        ASSETS,
        candidate,
        existing,
        policy,
        sources,
        game_data.PROVENANCE_PATH,
        extract.LEGACY_OWNERSHIP_CANDIDATE if fresh is not None else None,
        extract.LEGACY_OWNERSHIP if fresh is not None else None,
        proposal if fresh is not None else None,
        approval if fresh is not None else None,
    )
    print(
        json.dumps(
            {
                "status": "published",
                "domain": "technology",
                "game_build": build,
                "output_count": len(candidate.outputs),
                "deleted": changes["deletions"],
                "renamed": changes["renames"],
                "output_root_sha256": EXPECTED["output_root_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
