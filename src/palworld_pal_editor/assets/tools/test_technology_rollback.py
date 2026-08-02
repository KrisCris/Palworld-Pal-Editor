from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import rollback_failed_technology_publication as rollback


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def domain(paths: dict[str, bytes], root: str) -> dict:
    return {
        "game_build": "24181527",
        "parser_revision": root,
        "mapping_sha256": "mapping",
        "policy_sha256": "policy",
        "source_counts": {},
        "output_counts": {},
        "output_hashes": {path: digest(data) for path, data in paths.items()},
        "missing_references": [],
        "missing_localizations": [],
        "missing_icons": [],
        "managed_paths": sorted(paths),
    }


class TechnologyRollbackTests(unittest.TestCase):
    def fixture(self, root: Path):
        assets = root / "assets"
        backup = root / "backup"
        provenance = root / "provenance.json"
        current = {
            "data/tech_data.json": b"new-json",
            "icons/tech/PALBOX.png": b"new-palbox",
            "icons/tech/Keep.png": b"new-keep",
        }
        previous = {
            "data/tech_data.json": b"old-json",
            "icons/tech/PalBox.png": b"old-palbox",
            "icons/tech/Keep.png": b"old-keep",
            "icons/tech/Legacy.png": b"old-legacy",
        }
        for relative, data in current.items():
            target = assets.joinpath(*relative.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        inventory = []
        for relative, data in previous.items():
            stored = (
                relative
                if relative == "data/tech_data.json"
                else relative.replace("icons/tech/", "icons/")
            )
            target = backup.joinpath(*stored.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            inventory.append(
                {"Path": stored, "Sha256": digest(data), "Length": len(data)}
            )
        (backup / "inventory.json").write_text(
            json.dumps(inventory, indent=2) + "\n", encoding="utf-8"
        )
        document = {
            "schema_version": 1,
            "bootstrap": {"game_build": "24181527"},
            "domains": {
                "skills": domain({"data/pal_attacks.json": b"skills"}, "skills"),
                "technology": domain(current, "candidate-root"),
            },
        }
        provenance.write_bytes(
            rollback.game_data.manifest_bytes(
                rollback.game_data.manifest_from_dict(document)
            )
        )
        review = {
            "candidate_root_sha256": "candidate-root",
            "output_hashes": {path: digest(data) for path, data in current.items()},
        }
        return assets, backup, provenance, current, previous, review

    def assert_tree(self, assets: Path, expected: dict[str, bytes]) -> None:
        actual = {}
        for path in sorted((assets / "data").glob("tech_data.json")):
            actual[path.relative_to(assets).as_posix()] = path.read_bytes()
        for path in sorted((assets / "icons/tech").glob("*.png")):
            actual[path.relative_to(assets).as_posix()] = path.read_bytes()
        self.assertEqual(expected, actual)

    def test_restores_exact_backup_and_removes_only_technology_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            assets, backup, provenance, _, previous, review = self.fixture(
                Path(directory)
            )
            before = json.loads(provenance.read_text(encoding="utf-8"))

            restored = rollback.restore_atomic(
                assets, backup, provenance, review, "candidate-root"
            )

            self.assertEqual(4, restored)
            self.assert_tree(assets, previous)
            after = json.loads(provenance.read_text(encoding="utf-8"))
            self.assertNotIn("technology", after["domains"])
            self.assertEqual(before["domains"]["skills"], after["domains"]["skills"])

    def test_refuses_current_or_backup_drift_before_mutation(self):
        for drift in ("current", "backup"):
            with self.subTest(drift=drift), tempfile.TemporaryDirectory() as directory:
                assets, backup, provenance, current, _, review = self.fixture(
                    Path(directory)
                )
                before_provenance = provenance.read_bytes()
                if drift == "current":
                    (assets / "icons/tech/Keep.png").write_bytes(b"drift")
                    expected = dict(current)
                    expected["icons/tech/Keep.png"] = b"drift"
                else:
                    (backup / "icons/Keep.png").write_bytes(b"drift")
                    expected = current

                with self.assertRaises(ValueError):
                    rollback.restore_atomic(
                        assets, backup, provenance, review, "candidate-root"
                    )

                self.assert_tree(assets, expected)
                self.assertEqual(before_provenance, provenance.read_bytes())

    def test_injected_partial_failure_rolls_back_complete_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            assets, backup, provenance, current, _, review = self.fixture(
                Path(directory)
            )
            before_provenance = provenance.read_bytes()
            real_replace = os.replace
            calls = 0

            def fail_once(source, destination):
                nonlocal calls
                calls += 1
                if calls == 3:
                    raise OSError("injected partial failure")
                return real_replace(source, destination)

            with patch.object(
                rollback.os, "replace", side_effect=fail_once
            ), self.assertRaises(OSError):
                rollback.restore_atomic(
                    assets, backup, provenance, review, "candidate-root"
                )

            self.assert_tree(assets, current)
            self.assertEqual(before_provenance, provenance.read_bytes())


if __name__ == "__main__":
    unittest.main()
