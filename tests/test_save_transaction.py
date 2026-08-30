"""What a save that fails leaves behind (spec §5.5).

A save writes several files that only make sense together -- the world, each
player, each external storage -- so a failure half way through is the one way this
program can corrupt a save it was asked to protect. The answer is a full copy of
every .sav already at the target, taken before the first write and put back if
anything goes wrong, plus rolling back the capture records the save had already
folded into the players.

The backup is of the **target**. The old code copied the loaded save while logging
the target's path, so saving somewhere else backed up the one folder that was never
in danger; the first test here is that bug.
"""

from contextlib import contextmanager
from pathlib import Path
import shutil
from unittest.mock import patch

import pytest

from palworld_pal_editor.core.save_io import GLOBAL_STORAGE_NAME, SaveFailed
from palworld_pal_editor.core.save_manager import SaveManager
from palworld_pal_editor.utils import DataProvider
from world_fixture import LOSSY_UID, open_world, write_empty_global


OTHER_SAVE = (
    Path(__file__).parents[1]
    / "tests/saves/1.0/8C439FF04713B5F986F9CAB485575089"
)


@contextmanager
def failing_write(fail_when):
    """Fail one of the save's file writes, the way a locked file or a full disk does.

    There is no seam in the save path to inject into, because writing the bytes is
    the save. So the real call fails, for the one file `fail_when(path, nth)` picks
    -- which is also the only way to leave a save genuinely half written.
    """
    real_write_bytes = Path.write_bytes
    written = 0

    def write_bytes(self, data):
        nonlocal written
        written += 1
        if fail_when(self, written):
            raise OSError(f"{self.name} is locked")
        return real_write_bytes(self, data)

    with patch.object(Path, "write_bytes", write_bytes):
        yield


def saved_files(directory: Path) -> dict[Path, bytes]:
    return {
        path: path.read_bytes()
        for path in [*directory.glob("*.sav"), *(directory / "Players").glob("*.sav")]
    }


def capture_count(player, paldeck_key: str) -> int:
    for entry in player.PalCaptureCount or []:
        if entry["key"].lower() == paldeck_key.lower():
            return entry["value"]
    return 0


def test_a_failed_save_restores_the_save_it_was_overwriting(tmp_path):
    """Saving A over B backs up B, and a failure puts B back -- all of B.

    Backing up the loaded save instead was the bug: it copies the one folder the
    save cannot hurt, and leaves the folder being overwritten with no way back. So
    what is checked is B's own bytes, in B's backup folder, and B's own bytes again
    in B afterwards -- including the files this save never reached, and not
    including the player files it brought with it, which were never B's to keep.
    """
    manager = open_world(tmp_path)
    other = tmp_path / "other"
    shutil.copytree(OTHER_SAVE, other)
    original = saved_files(other)
    original_players = sorted(path.name for path in (other / "Players").glob("*.sav"))

    # Level.sav goes first and a player file second, so failing the third write
    # leaves this save's own fingerprints on two files that were never its own.
    with failing_write(lambda path, nth: nth == 3):
        with pytest.raises(SaveFailed) as failure:
            manager.save(str(other))

    assert failure.value.restored is True
    backup = failure.value.backup_path
    assert backup.parent.parent == other
    assert (backup / "Level.sav").read_bytes() == original[other / "Level.sav"]
    assert (backup / "Level.sav").read_bytes() != (
        manager.file_path / "Level.sav"
    ).read_bytes()

    assert saved_files(other) == original
    assert sorted(path.name for path in (other / "Players").glob("*.sav")) == (
        original_players
    )


def test_a_failed_save_rolls_back_its_settlement_and_the_retry_settles_once(tmp_path):
    """The three formats go back together, and the capture is counted exactly once.

    Settlement -- the capture count and paldeck flag a created Pal owes its owner --
    is folded into the live players before the first write, so a save that fails has
    to take it back out again. It used to consume its own tracker while doing it, so
    the retry wrote a save that under-counted, silently and permanently.
    """
    empty_global = tmp_path / "empty-global.sav"
    write_empty_global(empty_global)
    manager = open_world(tmp_path, global_palbox=empty_global)
    world = manager.file_path
    created = manager.create_pal(LOSSY_UID, f"dps:{LOSSY_UID}")
    in_global = manager.create_pal("PAL_GLOBAL_STORAGE_BTN", "global-palbox")
    lossy = manager.get_player(LOSSY_UID)
    paldeck_key = DataProvider.get_pal_paldeck_record_id(created.pal.CharacterID)
    before = capture_count(lossy, paldeck_key)

    global_path = world.parent / GLOBAL_STORAGE_NAME
    original = {**saved_files(world), global_path: global_path.read_bytes()}

    # The Global Palbox is written last, so everything else is already on disk and
    # the restore has real work to do.
    with failing_write(lambda path, nth: path.name == GLOBAL_STORAGE_NAME):
        with pytest.raises(SaveFailed) as failure:
            manager.save(str(world))

    assert failure.value.restored is True
    assert (failure.value.backup_path / "Level.sav").read_bytes() == (
        original[world / "Level.sav"]
    )
    assert {**saved_files(world), global_path: global_path.read_bytes()} == original
    assert manager.pal_repository.is_created(created)
    assert capture_count(lossy, paldeck_key) == before

    assert manager.save(str(world)) is True

    assert capture_count(lossy, paldeck_key) == before + 1
    assert manager.pal_repository.created_records() == []

    SaveManager._instance = None
    reopened = SaveManager()
    assert reopened.open(str(world)) is not None
    assert reopened.get_record(created.record_key) is not None
    assert reopened.get_record(in_global.record_key) is not None
