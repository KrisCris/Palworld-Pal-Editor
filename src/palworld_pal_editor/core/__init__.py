"""The editor's model of an open save.

Two names are re-exported because the API layer asks the package for them rather
than for a module: `SaveManager`, which is the session, and `PalEntity`, which is a
Pal. Everything else is imported from the module that defines it.

This file used to star-import nine modules, which is why `Config`, `LOGGER` and
`DataProvider` were reachable as `core.Config` and friends, and why
`core.StorageKind` resolved to `pal_storage_file`'s two-value one -- the last star
import to define the name won, and it happens to be the one that cannot describe a
Pal in the world save. The canonical `StorageKind` is in `pal_record`, and is
imported from there.
"""

from palworld_pal_editor.core.pal_entity import PalEntity
from palworld_pal_editor.core.save_manager import SaveManager

__all__ = ["PalEntity", "SaveManager"]
