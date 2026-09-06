import shutil
from pathlib import Path

import pytest

from palworld_pal_editor.core.save_manager import SaveManager


WORLD_FIXTURE = Path("tests/saves/1.0/AF518B19A47340B8A55BC58137981393")


def open_copied_world(tmp_path: Path) -> SaveManager:
    world = tmp_path / "world"
    shutil.copytree(WORLD_FIXTURE, world)
    SaveManager._instance = None
    manager = SaveManager()
    assert manager.open(str(world)) is not None
    return manager


def test_delete_base_worker_pal_by_world_record_key(tmp_path):
    """Deleting a base-worker pal addressed by its ``world:<InstanceId>``
    RecordKey must succeed. These pals are stored in ``baseworker_mapping`` keyed
    by the bare InstanceId, so the prefix must be stripped before lookup."""
    manager = open_copied_world(tmp_path)
    base_pals = list(manager.baseworker_mapping.values())
    if not base_pals:
        pytest.skip("fixture has no base-worker pals to exercise this path")

    pal = base_pals[0]
    instance_id = str(pal.InstanceId)
    record_key = f"world:{instance_id}"

    assert manager.get_record(record_key) is not None
    assert manager.delete_pal(record_key) is True

    # Removed from the working roster and its record is unregistered.
    assert instance_id not in manager.baseworker_mapping
    assert manager.get_record(record_key) is None
    assert manager.get_pal(instance_id) is None


def test_delete_base_worker_pal_by_bare_instance_id(tmp_path):
    """Deleting a base-worker pal addressed by its bare InstanceId also works."""
    manager = open_copied_world(tmp_path)
    base_pals = list(manager.baseworker_mapping.values())
    if not base_pals:
        pytest.skip("fixture has no base-worker pals to exercise this path")

    pal = base_pals[0]
    instance_id = str(pal.InstanceId)

    assert manager.delete_pal(instance_id) is True
    assert instance_id not in manager.baseworker_mapping
    assert manager.get_pal(instance_id) is None
