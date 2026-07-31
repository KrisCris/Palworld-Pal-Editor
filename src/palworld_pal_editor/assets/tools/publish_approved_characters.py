"""One-shot publisher for the independently approved character snapshot.

This wrapper intentionally binds the reviewed source bytes, candidate identity,
deletion proposal, and approval before making exactly one atomic publication call.
It is a local audit artifact, not part of the shipped maintainer tooling.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import tempfile
from pathlib import Path

import extract_game_data as extract
import game_data
from game_data import SourceInventory, check_domains, load_table

ROOT = Path(__file__).resolve().parents[4]
ASSETS = extract.RUNTIME_ASSETS
PROPOSAL_PATH = Path(__file__).with_name("character_deletion_proposal.json")
APPROVAL_PATH = Path(__file__).with_name("character_deletion_approval.json")
CREDENTIAL_PATH = (
    ROOT / "output/task3-character-audit/fresh-deletion-review-credential.json"
)

EXPECTED_SIGNATURE = (
    "(stage: 'Path', assets: 'Path', domain: 'str', candidate: 'DomainSnapshot', "
    "manifest: 'Manifest', *, policy: 'dict', sources: 'SourceInventory', "
    "provenance_path: 'Path | None' = None, legacy_candidate_path: 'Path | None' "
    "= None, legacy_ownership_path: 'Path | None' = None, "
    "legacy_deletion_proposal: 'dict | None' = None, legacy_deletion_approval: "
    "'dict | None' = None) -> 'Manifest'"
)
EXPECTED = {
    "approval_sha256": "f7063f1cdddc5ec60f3ac4cbe37778c950d504bc902ba2254b2e03a59f06b741",
    "credential_sha256": "050132d72c88f370191f1ce4b3b04224bca493c027c1db3252bec4e52e8630c2",
    "proposal_sha256": "a9b81f75cb660fce7780cf85cc51ea01690e111c7f94e7a36401281eec6df580",
    "plan_sha256": "02305a96305f91bd1cf900873547e2329f097fe0c6facfe9a07abf03f2fe8154",
    "output_root_sha256": "a78348be73afe5c6f3c8a3946b88f131958182a606a61b9dc311a821ce1388f2",
    "policy_domain_sha256": "7d2b0ea5561aceb6f9d22198d58b7de7b7d92254cfbd749f12ac8f56d57f616c",
    "game_build": "24181527",
    "parser_revision": "e3e940c4337ee045dcce40c896e481b4e6ab7b9d",
    "mapping_sha256": "241c45de9d5b55b246cd4b39d62b9209faf7758ce0637e1f7a545aa0f75f71f0",
    "output_count": 482,
    "json_sha256": {
        "data/pal_data.json": "0f701a6933a7d646bbfb8d8e724a611088ca822ee97b4394eb12e544e4027c6a",
        "data/human_data.json": "879d2a80b91d2bbf2e1cff1aa50b792c85483c0cb58a5eadc01d0d79cd0cdaa3",
        "data/skin_data.json": "7dde2c0a1a316c9d0b5eaa160d28b8fc6b544bbe072d767b6dfb791e2be4ca1d",
    },
}
EXPECTED_SOURCE_SHA256 = {
    "game_data.py": "c21150dceefb6aa6bd1d6f94d617ff1df2ad87280165a806a8808d0514824f01",
    "extract_game_data.py": "6b5e87cfa9af7c43be571376e316dfc4ad8fd39fd5dd3acf1912173fd55a533b",
    "test_pipeline.py": "40c1e61b58cfae3fd93dc01fcdfd52dd09fadc05f53611d2d4fa83589d30ed20",
    "policy.json": "66a4e939d3f12b626c269d026bd70095165fbc174622bb4af5718bbd2e2d96c0",
}
EXPECTED_DELETIONS = (
    "icons/pals/BOSS_Male_People2.png",
    "icons/pals/BeardedDragon.png",
    "icons/pals/BlackFurDragon.png",
    "icons/pals/ElecLion.png",
    "icons/pals/GYM_BlackGriffon.png",
    "icons/pals/GYM_BlueSkyDragon.png",
    "icons/pals/GYM_ElecPanda.png",
    "icons/pals/GYM_Horus.png",
    "icons/pals/GYM_LilyQueen.png",
    "icons/pals/GYM_MoonQueen.png",
    "icons/pals/GYM_SnowTigerBeastman.png",
    "icons/pals/GYM_ThunderDragonMan.png",
    "icons/pals/GYM_WorldTreeDragon.png",
    "icons/pals/PlantSlime_Flower.png",
    "icons/pals/skin/IceHorse_Skin001.png",
)
OUTSIDE_ASSET_TARGETS = (
    ".playwright-cli",
    "pyproject.toml",
    "requirements.txt",
    "src/palworld_pal_editor/assets/tools/paldb.py",
    "src/palworld_pal_editor/assets/tools/update_actives.py",
    "src/palworld_pal_editor/assets/tools/update_human.py",
    "src/palworld_pal_editor/assets/tools/update_human_pal.py",
    "src/palworld_pal_editor/assets/tools/update_pals.py",
    "src/palworld_pal_editor/assets/tools/update_passives.py",
    "src/palworld_pal_editor/assets/tools/update_tech.py",
    "tests/test_game_character_data.py",
    "tests/test_paldb_updates.py",
    "uv.lock",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json_sha256(value: object) -> str:
    return sha256_bytes(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    )


def inventory(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def selected_inventory() -> dict[str, str]:
    result = {}
    for relative in OUTSIDE_ASSET_TARGETS:
        target = ROOT / relative
        if target.is_file():
            result[relative] = sha256_file(target)
        elif target.is_dir():
            result.update(
                {
                    path.relative_to(ROOT).as_posix(): sha256_file(path)
                    for path in sorted(target.rglob("*"))
                    if path.is_file()
                }
            )
    return result


def inventory_root(values: dict[str, str]) -> str:
    return canonical_json_sha256(values)


def assert_static_bindings(
    *, verify_legacy_targets: bool = True
) -> tuple[dict, dict, dict]:
    actual_signature = str(inspect.signature(game_data.publish_domain))
    if actual_signature != EXPECTED_SIGNATURE:
        raise AssertionError(f"publish_domain signature changed: {actual_signature}")
    source_paths = {
        "game_data.py": Path(game_data.__file__),
        "extract_game_data.py": Path(extract.__file__),
        "test_pipeline.py": Path(game_data.__file__).with_name("test_pipeline.py"),
        "policy.json": extract.POLICY_PATH,
    }
    actual_sources = {name: sha256_file(path) for name, path in source_paths.items()}
    if actual_sources != EXPECTED_SOURCE_SHA256:
        raise AssertionError(f"reviewed source bytes changed: {actual_sources}")
    files = {
        "proposal_sha256": sha256_file(PROPOSAL_PATH),
        "approval_sha256": sha256_file(APPROVAL_PATH),
        "credential_sha256": sha256_file(CREDENTIAL_PATH),
    }
    for key, actual in files.items():
        if actual != EXPECTED[key]:
            raise AssertionError(f"{key} changed: {actual}")
    proposal = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
    approval = json.loads(APPROVAL_PATH.read_text(encoding="utf-8"))
    credential = json.loads(CREDENTIAL_PATH.read_text(encoding="utf-8"))
    expected_approval_fields = {
        "schema_version",
        "kind",
        "reviewer",
        "review_date",
        "approved_plan_sha256",
    }
    if set(approval) != expected_approval_fields:
        raise AssertionError("publisher approval schema changed")
    if approval.get("schema_version") != 1:
        raise AssertionError("publisher approval schema version changed")
    if approval.get("kind") != "legacy_deletion_approval":
        raise AssertionError("publisher approval kind changed")
    if approval.get("review_date") != "2026-07-26":
        raise AssertionError("publisher approval review date changed")
    if approval.get("reviewer") != "/root/task3_approval_schema_review":
        raise AssertionError("publisher approval reviewer changed")
    if approval.get("approved_plan_sha256") != EXPECTED["plan_sha256"]:
        raise AssertionError("approval plan binding changed")
    binding = credential.get("approved_binding", {})
    if credential.get("reviewer") != "/root/task3_approval_schema_review":
        raise AssertionError("fresh publisher reviewer changed")
    if credential.get("prior_publisher_gate_reviewer") != (
        "/root/task3_publish_gate_review"
    ):
        raise AssertionError("prior publisher reviewer reference changed")
    if credential.get("prior_deletion_reviewer") != "/root/task3_deletion_review":
        raise AssertionError("prior deletion reviewer reference changed")
    if credential.get("publisher_approval_sha256") != EXPECTED["approval_sha256"]:
        raise AssertionError("credential approval hash binding changed")
    if credential.get("review_package_sha256") != (
        "fc9f9687194f5cd3f956847b13804550a0f30ba30fb5d2eb37d394aa90301e25"
    ):
        raise AssertionError("credential review package binding changed")
    expected_binding = {
        "proposal_sha256": EXPECTED["proposal_sha256"],
        "plan_sha256": EXPECTED["plan_sha256"],
        "output_root_sha256": EXPECTED["output_root_sha256"],
        "policy_sha256": EXPECTED["policy_domain_sha256"],
        "game_build": EXPECTED["game_build"],
        "parser_revision": EXPECTED["parser_revision"],
        "mapping_sha256": EXPECTED["mapping_sha256"],
        "deletion_count": len(EXPECTED_DELETIONS),
        "source_sha256": {
            "game_data_py": EXPECTED_SOURCE_SHA256["game_data.py"],
            "extract_game_data_py": EXPECTED_SOURCE_SHA256["extract_game_data.py"],
            "test_pipeline_py": EXPECTED_SOURCE_SHA256["test_pipeline.py"],
            "policy_json": EXPECTED_SOURCE_SHA256["policy.json"],
        },
    }
    for key, expected in expected_binding.items():
        if binding.get(key) != expected:
            raise AssertionError(f"fresh review credential binding changed: {key}")
    if credential.get("earlier_approval_reused") is not False:
        raise AssertionError("fresh reviewer credential does not reject earlier reuse")
    proposal_paths = tuple(item["path"] for item in proposal.get("paths", ()))
    if proposal_paths != EXPECTED_DELETIONS:
        raise AssertionError(f"deletion membership/order changed: {proposal_paths}")
    credential_paths = tuple(binding.get("paths", ()))
    if credential_paths != EXPECTED_DELETIONS:
        raise AssertionError("credential deletion membership/order changed")
    if verify_legacy_targets:
        for item in proposal["paths"]:
            target = ASSETS.joinpath(*item["path"].split("/"))
            actual = sha256_file(target)
            expected = item["current_sha256"]
            if actual != expected or item["baseline_sha256"] != expected:
                raise AssertionError(
                    f"reviewed deletion target changed: {item['path']}"
                )
            if item["backup_sha256"] != expected:
                raise AssertionError(f"backup binding differs: {item['path']}")
    return proposal, approval, credential


def main() -> None:
    game = extract.find_game_dir(None)
    build_id = extract.detect_build_id(game)
    extract.require_write_build(build_id, False)
    if build_id != EXPECTED["game_build"]:
        raise AssertionError(f"game build changed: {build_id}")
    toolchain = extract.ensure_toolchain(extract._default_cache())
    if toolchain.uex_revision != EXPECTED["parser_revision"]:
        raise AssertionError("parser revision changed")
    if toolchain.mapping_sha256 != EXPECTED["mapping_sha256"]:
        raise AssertionError("mapping hash changed")
    policy = json.loads(json.dumps(extract._POLICY))
    policy["bootstrap"]["game_build"] = build_id
    if (
        canonical_json_sha256(policy["domains"]["characters"])
        != EXPECTED["policy_domain_sha256"]
    ):
        raise AssertionError("character policy binding changed")
    existing = extract._load_manifest(game_data.PROVENANCE_PATH, policy)
    proposal, approval, credential = assert_static_bindings(
        verify_legacy_targets="characters" not in existing.domains
    )
    with tempfile.TemporaryDirectory(prefix="approved-character-publish-") as directory:
        work = Path(directory)
        export_root = work / "export"
        extract.export_character_domain(
            toolchain,
            game / extract._PAK_RELATIVE.parent,
            export_root,
            work / "profiles",
        )
        monsters = load_table(
            export_root, game_data.CHARACTER_EVIDENCE_SOURCES["monsters"]
        )
        humans = load_table(export_root, game_data.CHARACTER_EVIDENCE_SOURCES["humans"])
        levels = load_table(export_root, game_data.SKILL_SOURCES["levels"])
        passives = load_table(export_root, game_data.SKILL_SOURCES["passives"])
        sources = SourceInventory(
            present_sources=frozenset(
                policy["domains"]["characters"]["required_sources"]
            ),
            reference_ids={
                "characters": frozenset(monsters) | frozenset(humans),
                "skills": frozenset(
                    row["WazaID"]
                    for row in levels.values()
                    if isinstance(row.get("WazaID"), str) and row["WazaID"]
                ),
                "passives": frozenset(passives),
            },
            available_icons=frozenset(),
            approved_static_icons=frozenset(
                path
                for path in ("icons/pals/Human.png", "icons/pals/unknown.png")
                if ASSETS.joinpath(*path.split("/")).is_file()
            ),
        )
        checked = check_domains("characters", export_root, policy, sources, existing)
        if checked.errors:
            raise AssertionError("; ".join(checked.errors))
        candidate = checked.candidates["characters"]
        if len(candidate.outputs) != EXPECTED["output_count"]:
            raise AssertionError(
                f"candidate output count changed: {len(candidate.outputs)}"
            )
        actual_root = game_data.canonical_output_root_sha256(candidate.outputs)
        if actual_root != EXPECTED["output_root_sha256"]:
            raise AssertionError(f"candidate output root changed: {actual_root}")
        for relative, expected in EXPECTED["json_sha256"].items():
            actual = candidate.hashes.get(relative)
            if actual != expected:
                raise AssertionError(f"candidate JSON changed: {relative}={actual}")
        fresh_proposal = game_data.build_legacy_deletion_proposal(
            "characters",
            candidate,
            ASSETS,
            extract.LEGACY_OWNERSHIP_CANDIDATE,
            extract.LEGACY_OWNERSHIP,
            existing=existing,
        )
        if fresh_proposal is not None and fresh_proposal != proposal:
            raise AssertionError(
                "fresh deletion proposal differs from reviewed proposal"
            )
        stage = work / "stage"
        extract._stage_outputs(stage, candidate.outputs)

        # Snapshot as late as possible. Everything outside the reviewed candidate and
        # exact deletion set is checked byte-for-byte after the atomic call.
        before_assets = inventory(ASSETS)
        before_external = selected_inventory()
        active_proposal = fresh_proposal or {"paths": (), "renames": ()}
        for item in active_proposal["paths"]:
            if before_assets.get(item["path"]) != item["current_sha256"]:
                raise AssertionError(
                    f"deletion target changed before publish: {item['path']}"
                )
        before_provenance = sha256_file(game_data.PROVENANCE_PATH)

        # The sole state-changing call in this wrapper. Do not retry on failure.
        legacy_arguments = (
            {
                "legacy_candidate_path": extract.LEGACY_OWNERSHIP_CANDIDATE,
                "legacy_ownership_path": extract.LEGACY_OWNERSHIP,
                "legacy_deletion_proposal": proposal,
                "legacy_deletion_approval": approval,
            }
            if fresh_proposal is not None
            else {}
        )
        updated = game_data.publish_domain(
            stage,
            ASSETS,
            "characters",
            candidate,
            existing,
            policy=policy,
            sources=sources,
            provenance_path=game_data.PROVENANCE_PATH,
            **legacy_arguments,
        )

        after_assets = inventory(ASSETS)
        after_external = selected_inventory()
        before_paths = set(before_assets)
        after_paths = set(after_assets)
        deleted = tuple(sorted(before_paths - after_paths))
        added = tuple(sorted(after_paths - before_paths))
        old_entry = existing.domains.get("characters")
        managed_removals = (
            set(old_entry.managed_paths) - set(candidate.outputs)
            if old_entry is not None
            else set()
        )
        expected_deletions = (
            managed_removals
            | {item["path"] for item in active_proposal["paths"]}
            | {item["from_path"] for item in active_proposal["renames"]}
        )
        if deleted != tuple(sorted(expected_deletions)):
            raise AssertionError(f"unexpected deletion set: {deleted}")
        expected_added = tuple(
            sorted(path for path in candidate.outputs if path not in before_assets)
        )
        if added != expected_added:
            raise AssertionError(f"unexpected addition set: {added}")
        for relative, expected in candidate.hashes.items():
            if after_assets.get(relative) != expected:
                raise AssertionError(f"published output differs: {relative}")
        protected = before_paths - set(candidate.outputs) - set(EXPECTED_DELETIONS)
        changed_protected = tuple(
            sorted(
                relative
                for relative in protected
                if after_assets.get(relative) != before_assets[relative]
            )
        )
        if changed_protected:
            raise AssertionError(f"protected asset files changed: {changed_protected}")
        if after_external != before_external:
            raise AssertionError("protected files outside runtime assets changed")
        if updated.domains["characters"].output_root_sha256 != actual_root:
            raise AssertionError("updated manifest character root differs")
        after_provenance = sha256_file(game_data.PROVENANCE_PATH)
        if after_provenance == before_provenance:
            raise AssertionError("provenance did not change")

    print(
        json.dumps(
            {
                "status": "published",
                "domain": "characters",
                "game_build": build_id,
                "publish_call_count": 1,
                "approval_sha256": EXPECTED["approval_sha256"],
                "credential_sha256": EXPECTED["credential_sha256"],
                "proposal_sha256": EXPECTED["proposal_sha256"],
                "plan_sha256": proposal["plan_sha256"],
                "output_count": len(candidate.outputs),
                "output_root_sha256": actual_root,
                "json_sha256": EXPECTED["json_sha256"],
                "before_asset_count": len(before_assets),
                "after_asset_count": len(after_assets),
                "before_asset_inventory_root": inventory_root(before_assets),
                "after_asset_inventory_root": inventory_root(after_assets),
                "deleted_paths": list(deleted),
                "added_paths": list(added),
                "protected_asset_count": len(protected),
                "changed_protected_assets": [],
                "protected_external_count": len(before_external),
                "changed_protected_external": [],
                "provenance_before_sha256": before_provenance,
                "provenance_after_sha256": after_provenance,
                "reviewer": credential["reviewer"],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
