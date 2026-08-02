from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import game_data
import publish_approved_technology as publisher
from test_pipeline import (
    FIXTURE_POLICY,
    PNG_2X2,
    fixture_candidate,
    fixture_outputs,
    fixture_sources,
    snapshot,
    stage_candidate,
    write_candidate,
    write_ownership_evidence,
)

ROOT = Path(__file__).resolve().parents[4]
CANDIDATE = (
    ROOT
    / "output/task7-technology/final-review-candidate-24181527-20260726-193133"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TechnologyPublisherTests(unittest.TestCase):
    def binding_fixture(self, root: Path):
        source = root / "source.py"
        source.write_bytes(b"reviewed source")
        review = json.loads((CANDIDATE / "review.json").read_text(encoding="utf-8"))
        proposal = json.loads(
            (CANDIDATE / "deletion-proposal.json").read_text(encoding="utf-8")
        )
        approval = {
            "schema_version": 2,
            "kind": "legacy_change_approval",
            "reviewer": "/root/fresh-change-review",
            "review_date": "2026-07-26",
            "approved_plan_sha256": proposal["plan_sha256"],
            "approved_deletions": proposal["paths"],
            "approved_renames": proposal["renames"],
        }
        approval_path = root / "approval/approval.json"
        approval_path.parent.mkdir()
        approval_path.write_text(
            json.dumps(approval, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        credential = {
            "schema_version": 2,
            "kind": "technology_publication_credential",
            "reviewer": "/root/fresh-publisher-review",
            "review_date": "2026-07-26",
            "candidate_review_sha256": sha256(CANDIDATE / "review.json"),
            "change_proposal_sha256": sha256(CANDIDATE / "deletion-proposal.json"),
            "change_approval_sha256": sha256(approval_path),
            "candidate_root_sha256": review["candidate_root_sha256"],
            "policy_sha256": proposal["candidate_snapshot"]["policy_sha256"],
            "game_build": review["game_build"],
            "plan_sha256": proposal["plan_sha256"],
            "deletions": proposal["paths"],
            "renames": proposal["renames"],
            "source_sha256": {"source.py": sha256(source)},
        }
        credential_path = root / "credential/credential.json"
        credential_path.parent.mkdir()
        credential_path.write_text(
            json.dumps(credential, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        expected = {
            "review_sha256": sha256(CANDIDATE / "review.json"),
            "proposal_sha256": sha256(CANDIDATE / "deletion-proposal.json"),
            "approval_sha256": sha256(approval_path),
            "credential_sha256": sha256(credential_path),
            "output_root_sha256": review["candidate_root_sha256"],
            "json_sha256": review["output_hashes"]["data/tech_data.json"],
            "output_count": len(review["output_hashes"]),
            "game_build": review["game_build"],
            "policy_sha256": proposal["candidate_snapshot"]["policy_sha256"],
            "plan_sha256": proposal["plan_sha256"],
            "paths": tuple(item["path"] for item in proposal["paths"]),
            "renames": tuple(
                (item["from_path"], item["to_path"])
                for item in proposal["renames"]
            ),
        }
        return source, approval_path, credential_path, expected

    def test_static_bindings_fail_closed_for_missing_wrong_and_extra_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, approval, credential, expected = self.binding_fixture(root)
            publisher.validate_static_bindings(
                CANDIDATE,
                approval,
                credential,
                expected,
                {"source.py": source},
            )

            with self.assertRaises(FileNotFoundError):
                publisher.validate_static_bindings(
                    CANDIDATE,
                    root / "missing-approval.json",
                    credential,
                    expected,
                    {"source.py": source},
                )
            with self.assertRaisesRegex(ValueError, "approval SHA-256"):
                publisher.validate_static_bindings(
                    CANDIDATE,
                    approval,
                    credential,
                    {**expected, "approval_sha256": "0" * 64},
                    {"source.py": source},
                )

            copied = root / "candidate"
            shutil.copytree(CANDIDATE, copied)
            extra = copied / "candidate/icons/tech/Unexpected.png"
            extra.write_bytes(PNG_2X2)
            with self.assertRaisesRegex(ValueError, "candidate output paths"):
                publisher.validate_static_bindings(
                    copied,
                    approval,
                    credential,
                    expected,
                    {"source.py": source},
                )

            extra.unlink()
            proposal_path = copied / "deletion-proposal.json"
            proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
            proposal["paths"].append(
                {
                    "path": "icons/tech/UnexpectedDeletion.png",
                    "current_sha256": "0" * 64,
                }
            )
            proposal_path.write_text(
                json.dumps(proposal, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            rebound = dict(expected)
            rebound["proposal_sha256"] = sha256(proposal_path)
            credential_data = json.loads(credential.read_text(encoding="utf-8"))
            credential_data["change_proposal_sha256"] = rebound[
                "proposal_sha256"
            ]
            credential.write_text(
                json.dumps(credential_data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            rebound["credential_sha256"] = sha256(credential)
            with self.assertRaisesRegex(ValueError, "proposal binding"):
                publisher.validate_static_bindings(
                    copied,
                    approval,
                    credential,
                    rebound,
                    {"source.py": source},
                )

            tamper_root = root / "rename-tamper"
            tamper_root.mkdir()
            source, approval, credential, expected = self.binding_fixture(tamper_root)
            approval_data = json.loads(approval.read_text(encoding="utf-8"))
            approval_data["approved_renames"][0]["to_path"] = (
                "icons/tech/Overheatrifle.png"
            )
            approval.write_text(
                json.dumps(approval_data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            rebound = {**expected, "approval_sha256": sha256(approval)}
            credential_data = json.loads(credential.read_text(encoding="utf-8"))
            credential_data["change_approval_sha256"] = rebound["approval_sha256"]
            credential.write_text(
                json.dumps(credential_data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            rebound["credential_sha256"] = sha256(credential)
            with self.assertRaisesRegex(ValueError, "approval binding"):
                publisher.validate_static_bindings(
                    CANDIDATE,
                    approval,
                    credential,
                    rebound,
                    {"source.py": source},
                )

    def test_source_and_runtime_drift_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, approval, credential, expected = self.binding_fixture(root)
            source.write_bytes(b"drift")
            with self.assertRaisesRegex(ValueError, "reviewed source changed"):
                publisher.validate_static_bindings(
                    CANDIDATE,
                    approval,
                    credential,
                    expected,
                    {"source.py": source},
                )

            assets = root / "assets"
            protected = assets / "data/pal_data.json"
            deletion = assets / "icons/tech/Stale.png"
            protected.parent.mkdir(parents=True)
            deletion.parent.mkdir(parents=True)
            protected.write_bytes(b"protected")
            deletion.write_bytes(b"delete")
            review = {
                "runtime_non_technology_sha256": {
                    "data/pal_data.json": hashlib.sha256(b"protected").hexdigest()
                }
            }
            proposal = {
                "paths": [
                    {
                        "path": "icons/tech/Stale.png",
                        "current_sha256": hashlib.sha256(b"delete").hexdigest(),
                    }
                ]
            }
            publisher.validate_runtime_bindings(assets, review, proposal)
            protected.write_bytes(b"drift")
            with self.assertRaisesRegex(ValueError, "runtime drift"):
                publisher.validate_runtime_bindings(assets, review, proposal)
            protected.write_bytes(b"protected")
            deletion.write_bytes(b"deletion drift")
            with self.assertRaisesRegex(ValueError, "runtime drift"):
                publisher.validate_runtime_bindings(assets, review, proposal)

            rename_assets = root / "rename-assets"
            rename_source = rename_assets / "icons/tech/PalBox.png"
            rename_source.parent.mkdir(parents=True)
            rename_source.write_bytes(b"old icon")
            rename_review = {"runtime_non_technology_sha256": {}}
            rename_proposal = {
                "paths": [],
                "renames": [
                    {
                        "from_path": "icons/tech/PalBox.png",
                        "to_path": "icons/tech/PALBOX.png",
                        "current_sha256": hashlib.sha256(b"old icon").hexdigest(),
                    }
                ],
            }
            publisher.validate_runtime_bindings(
                rename_assets, rename_review, rename_proposal
            )
            temporary = rename_assets / "icons/tech/temporary.png"
            os.replace(rename_source, temporary)
            os.replace(temporary, rename_assets / "icons/tech/PALBOX.png")
            with self.assertRaisesRegex(ValueError, "runtime drift"):
                publisher.validate_runtime_bindings(
                    rename_assets, rename_review, rename_proposal
                )

    def test_postconditions_classify_deletions_and_case_only_renames(self):
        stale = "icons/tech/Stale.png"
        old = "icons/tech/PalBox.png"
        new = "icons/tech/PALBOX.png"
        before = {stale: "stale-hash", old: "old-hash"}
        after = {new: "new-hash"}
        proposal = {
            "paths": [{"path": stale, "current_sha256": "stale-hash"}],
            "renames": [
                {
                    "from_path": old,
                    "to_path": new,
                    "current_sha256": "old-hash",
                    "candidate_sha256": "new-hash",
                }
            ],
        }

        result = publisher.validate_publication_changes(
            before, after, proposal, {new: "new-hash"}
        )

        self.assertEqual(result["deletions"], (stale,))
        self.assertEqual(result["renames"], ((old, new),))
        with self.assertRaisesRegex(AssertionError, "rename"):
            publisher.validate_publication_changes(
                before,
                {"icons/tech/Palbox.png": "new-hash"},
                proposal,
                {new: "new-hash"},
            )

    def test_partial_publication_failure_rolls_back_everything(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "assets"
            stage = root / "stage"
            provenance = root / "provenance.json"
            outputs = fixture_outputs()["technology"]
            old = fixture_candidate("technology", outputs)
            write_candidate(assets, old)
            stale_path = "icons/tech/Stale.png"
            stale = assets.joinpath(*stale_path.split("/"))
            stale.write_bytes(PNG_2X2)
            candidate = fixture_candidate("technology", outputs)
            stage_candidate(stage, candidate)
            digest = hashlib.sha256(PNG_2X2).hexdigest()
            legacy_candidate, ownership, _, _ = write_ownership_evidence(
                root,
                [
                    {"path": "icons/tech/TestTech.png", "sha256": digest},
                    {"path": stale_path, "sha256": digest},
                ],
            )
            proposal = game_data.build_legacy_deletion_proposal(
                "technology", candidate, assets, legacy_candidate, ownership
            )
            approval = {
                "schema_version": 2,
                "kind": "legacy_change_approval",
                "reviewer": "fixture-independent-reviewer",
                "review_date": "2026-07-26",
                "approved_plan_sha256": proposal["plan_sha256"],
                "approved_deletions": proposal["paths"],
                "approved_renames": proposal["renames"],
            }
            before = snapshot(assets)
            real_replace = os.replace
            replacements = 0

            def fail_after_first_replacement(source, destination):
                nonlocal replacements
                if Path(destination).is_relative_to(assets):
                    replacements += 1
                    if replacements == 2:
                        raise OSError("injected partial publication failure")
                return real_replace(source, destination)

            with (
                patch("game_data.os.replace", side_effect=fail_after_first_replacement),
                self.assertRaisesRegex(OSError, "injected partial"),
            ):
                publisher.publish_atomic(
                    stage,
                    assets,
                    candidate,
                    game_data.Manifest(1, {}, {}),
                    FIXTURE_POLICY,
                    fixture_sources(),
                    provenance,
                    legacy_candidate,
                    ownership,
                    proposal,
                    approval,
                )

            self.assertEqual(snapshot(assets), before)
            self.assertFalse(provenance.exists())


if __name__ == "__main__":
    unittest.main()
