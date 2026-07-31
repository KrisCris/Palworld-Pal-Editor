"""Atomically restore the reviewed pre-technology-publication runtime snapshot."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

import extract_game_data as extract
import game_data

ROOT = Path(__file__).resolve().parents[4]
ASSETS = extract.RUNTIME_ASSETS
BACKUP = Path(
    r"C:\Users\connlost\AppData\Local\Temp\Palworld-Pal-Editor-backups"
    r"\technology-20260726-180427"
)
REVIEW = (
    ROOT / "output/task7-technology/final-review-candidate-24181527-20260726-184445/"
    "review.json"
)
PROVENANCE = game_data.PROVENANCE_PATH
EXPECTED = {
    "review_sha256": "0960c6ae2f95ed9e298518abe55c45b470e7fe069688f3878006f242d1d00973",
    "backup_inventory_sha256": "1f5c06988faea342562d9a6105ce08d321d4f6f8608aaa6f43d1ec1717aa69d7",
    "candidate_root_sha256": "26f8fb888454e39fe7291d952696a92a48a1b16301ba8a47b24e67f8af41b233",
    "published_provenance_sha256": "ea031d2b021f53abecafd696eeb19fe4788154f488c6b1f5414567da14d98d9e",
    "restore_count": 470,
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def safe_target(root: Path, relative: str) -> Path:
    if not relative or "\\" in relative:
        raise ValueError(f"unsafe path: {relative!r}")
    target = root.joinpath(*relative.split("/"))
    if not target.resolve(strict=False).is_relative_to(root.resolve()):
        raise ValueError(f"path escapes root: {relative}")
    return target


def technology_inventory(assets: Path) -> dict[str, str]:
    assets = Path(assets)
    files = []
    data = assets / "data/tech_data.json"
    if data.is_file():
        files.append(data)
    icons = assets / "icons/tech"
    if icons.is_dir():
        files.extend(path for path in icons.rglob("*") if path.is_file())
    return {
        path.relative_to(assets).as_posix(): sha256_file(path) for path in sorted(files)
    }


def backup_files(backup: Path) -> dict[str, tuple[Path, str]]:
    backup = Path(backup)
    inventory_path = backup / "inventory.json"
    document = json.loads(inventory_path.read_text(encoding="utf-8"))
    if not isinstance(document, list) or not document:
        raise ValueError("backup inventory must be a non-empty list")
    result = {}
    declared = {"inventory.json"}
    for item in document:
        if not isinstance(item, dict) or set(item) != {"Path", "Sha256", "Length"}:
            raise ValueError("backup inventory entry has unexpected fields")
        stored = item["Path"]
        if stored == "data/tech_data.json":
            runtime = stored
        elif stored.startswith("icons/") and stored.count("/") == 1:
            runtime = "icons/tech/" + stored.removeprefix("icons/")
        else:
            raise ValueError(f"backup path is outside technology scope: {stored}")
        source = safe_target(backup, stored)
        declared.add(stored)
        if (
            not source.is_file()
            or source.stat().st_size != item["Length"]
            or sha256_file(source) != item["Sha256"]
        ):
            raise ValueError(f"backup file differs from inventory: {stored}")
        if runtime in result:
            raise ValueError(f"duplicate backup runtime path: {runtime}")
        result[runtime] = (source, item["Sha256"])
    actual = {
        path.relative_to(backup).as_posix()
        for path in backup.rglob("*")
        if path.is_file()
    }
    if actual != declared:
        raise ValueError("backup contains undeclared or missing files")
    return result


def restored_provenance(provenance: Path, review: dict, expected_root: str):
    raw = Path(provenance).read_bytes()
    manifest = game_data.manifest_from_dict(json.loads(raw))
    if game_data.manifest_bytes(manifest) != raw:
        raise ValueError("published provenance is not canonical")
    technology = manifest.domains.get("technology")
    expected_hashes = review.get("output_hashes")
    if (
        review.get("candidate_root_sha256") != expected_root
        or technology is None
        or technology.output_hashes != expected_hashes
        or set(technology.managed_paths) != set(expected_hashes or {})
    ):
        raise ValueError("published technology provenance differs from candidate")
    domains = dict(manifest.domains)
    del domains["technology"]
    previous = game_data.Manifest(manifest.schema_version, manifest.bootstrap, domains)
    return raw, game_data.manifest_bytes(previous)


def validate_current(assets: Path, review: dict, expected_root: str) -> dict[str, str]:
    expected = review.get("output_hashes")
    if review.get("candidate_root_sha256") != expected_root or not isinstance(
        expected, dict
    ):
        raise ValueError("candidate review binding differs")
    current = technology_inventory(assets)
    if current != expected:
        raise ValueError("current technology runtime differs from published candidate")
    return current


def restore_atomic(
    assets: Path,
    backup: Path,
    provenance: Path,
    review: dict,
    expected_root: str,
) -> int:
    assets = Path(assets)
    provenance = Path(provenance)
    if not assets.is_dir() or not backup.is_dir() or not provenance.is_file():
        raise ValueError("rollback roots must exist")
    previous = backup_files(backup)
    current = validate_current(assets, review, expected_root)
    current_provenance, previous_provenance = restored_provenance(
        provenance, review, expected_root
    )
    current_paths = {relative: safe_target(assets, relative) for relative in current}
    previous_paths = {relative: safe_target(assets, relative) for relative in previous}

    with tempfile.TemporaryDirectory(
        prefix="game-data-rollback-", dir=assets.parent
    ) as directory:
        transaction = Path(directory)
        saved_current = transaction / "current"
        staged_previous = transaction / "previous"
        for relative, target in current_paths.items():
            saved = safe_target(saved_current, relative)
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, saved)
        for relative, (source, _) in previous.items():
            staged = safe_target(staged_previous, relative)
            staged.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, staged)
        saved_provenance = transaction / "current-provenance.json"
        saved_provenance.write_bytes(current_provenance)
        staged_provenance = transaction / "previous-provenance.json"
        staged_provenance.write_bytes(previous_provenance)

        mutated = False
        try:
            for target in current_paths.values():
                target.unlink()
                mutated = True
            for relative, target in sorted(previous_paths.items()):
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(safe_target(staged_previous, relative), target)
            os.replace(staged_provenance, provenance)
            actual = technology_inventory(assets)
            expected = {relative: item[1] for relative, item in previous.items()}
            if actual != expected:
                raise AssertionError("restored runtime differs from exact backup")
            restored_document = json.loads(provenance.read_bytes())
            if "technology" in restored_document.get("domains", {}):
                raise AssertionError("technology provenance was not removed")
        except Exception:
            if mutated:
                rollback_errors = []
                try:
                    for target in list((assets / "icons/tech").glob("*.png")):
                        target.unlink()
                    data = assets / "data/tech_data.json"
                    if data.is_file():
                        data.unlink()
                    for relative, target in sorted(current_paths.items()):
                        target.parent.mkdir(parents=True, exist_ok=True)
                        os.replace(safe_target(saved_current, relative), target)
                    os.replace(saved_provenance, provenance)
                except OSError as error:
                    rollback_errors.append(str(error))
                if rollback_errors:
                    raise RuntimeError(
                        "Rollback restore failed and transaction rollback was incomplete: "
                        + "; ".join(rollback_errors)
                    )
            raise
    return len(previous)


def main() -> None:
    if sha256_file(REVIEW) != EXPECTED["review_sha256"]:
        raise ValueError("candidate review hash differs")
    if sha256_file(BACKUP / "inventory.json") != EXPECTED["backup_inventory_sha256"]:
        raise ValueError("backup inventory hash differs")
    if sha256_file(PROVENANCE) != EXPECTED["published_provenance_sha256"]:
        raise ValueError("published provenance hash differs")
    review = json.loads(REVIEW.read_bytes())
    restored = restore_atomic(
        ASSETS,
        BACKUP,
        PROVENANCE,
        review,
        EXPECTED["candidate_root_sha256"],
    )
    if restored != EXPECTED["restore_count"]:
        raise AssertionError("restored file count differs")
    print(json.dumps({"status": "restored", "files": restored}, indent=2))


if __name__ == "__main__":
    main()
