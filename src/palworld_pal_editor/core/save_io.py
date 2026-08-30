"""Backing up and restoring the .sav files one save writes (spec §5.5).

The save itself is ordinary: serialize a deepcopy of each live GVAS and write the
bytes to their file. What needs a home of its own is the part that runs when that
does not work — because a save that fails half way through has already overwritten
some of the files the game needs to agree with each other.

So this keeps a complete copy of every .sav already at the target before the first
byte is written, and puts them all back if anything goes wrong. Two rules keep it
small enough to trust:

- the backup is of the **target**, not of the loaded save. Saving somewhere else is
  exactly when a backup matters, and the loaded folder is not the one about to be
  overwritten.
- restoring is the plain inverse of backing up. There is no manifest and no
  transaction log: what the backup folder holds is what goes back, and the files
  this save created are the ones that get removed.

If restoring itself fails there is nothing further to try, so it says so and leaves
the backup folder alone for the user to copy back by hand.
"""

from datetime import datetime
from pathlib import Path
import shutil
from typing import Optional

from palworld_pal_editor.utils import LOGGER

BACKUP_FOLDER_NAME = "Palworld-Pal-Editor-Backup"
# The one save file that lives beside the world folder instead of inside it.
GLOBAL_STORAGE_NAME = "GlobalPalStorage.sav"


class SaveFailed(Exception):
    """A save that did not happen, and what is left on disk because of it.

    `backup_path` is where the untouched files are. It matters most when `restored`
    is False: the save failed, putting the originals back failed too, and that folder
    is the only complete copy left.
    """

    def __init__(
        self,
        message: str,
        *,
        backup_path: Optional[Path] = None,
        restored: bool = True,
    ) -> None:
        super().__init__(message)
        self.backup_path = backup_path
        self.restored = restored


def _ignore_everything_but_saves(directory, names: list[str]) -> list[str]:
    """Copy the Players folder and the .sav files, and nothing else.

    This is what keeps the backup folder out of its own backup, and what keeps a save
    folder's screenshots and metadata from being copied on every save.
    """
    return [
        name for name in names if name != "Players" and not name.endswith(".sav")
    ]


def existing_saves(output_path: Path, global_storage_path: Path) -> list[Path]:
    """Every .sav already at the target — the files a save here would overwrite."""
    found = [
        *sorted(output_path.glob("*.sav")),
        *sorted((output_path / "Players").glob("*.sav")),
    ]
    if global_storage_path.exists():
        found.append(global_storage_path)
    return found


def backup_saves(output_path: Path, global_storage_path: Path) -> Optional[Path]:
    """Copy every .sav at the target into a timestamped folder, or None if bare.

    Saving into an empty folder has nothing to preserve, and leaving an empty backup
    behind would only make the new save folder look like it had a history.
    """
    if not existing_saves(output_path, global_storage_path):
        LOGGER.info(f"Nothing to back up at {output_path}")
        return None

    backup_dir = (
        output_path
        / BACKUP_FOLDER_NAME
        / datetime.now().strftime(r"%Y-%m-%d_%H-%M-%S")
    )
    LOGGER.info(f"Backing up {output_path} to {backup_dir}")
    shutil.copytree(output_path, backup_dir, ignore=_ignore_everything_but_saves)
    if global_storage_path.exists():
        shutil.copy2(global_storage_path, backup_dir / GLOBAL_STORAGE_NAME)
    return backup_dir


def _restored_to(backup_dir: Path, output_path: Path, backup_file: Path) -> Path:
    """Where one backed-up file came from."""
    relative = backup_file.relative_to(backup_dir)
    if str(relative) == GLOBAL_STORAGE_NAME:
        return output_path.parent / GLOBAL_STORAGE_NAME
    return output_path / relative


def restore_saves(
    backup_dir: Optional[Path], output_path: Path, created: list[Path]
) -> None:
    """Undo a failed save: every backed-up file back, every new file gone.

    Files the save did not reach are restored anyway. They are byte-identical to what
    is already there, and checking which ones were written would be the transaction
    log this deliberately does not keep.
    """
    for backup_file in sorted(backup_dir.rglob("*.sav")) if backup_dir else []:
        target = _restored_to(backup_dir, output_path, backup_file)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup_file, target)
        LOGGER.info(f"Restored {target}")
    for path in created:
        path.unlink(missing_ok=True)
        LOGGER.info(f"Removed the file this save created: {path}")
