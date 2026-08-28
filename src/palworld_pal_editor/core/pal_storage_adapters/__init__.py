"""Per-format readers and writers for the three places a Pal can physically live.

Each adapter walks its own native structure, hands ``PalEntity`` the two real parent
dicts it found there, and produces ``PalRecord``s for ``PalRepository``. Nothing here
owns identity, ownership, guild membership or conflict rules — those belong to the
operation layer.
"""

from palworld_pal_editor.core.pal_storage_adapters.storage_pal_adapter import (
    DpsPalAdapter,
    GpsPalAdapter,
)
from palworld_pal_editor.core.pal_storage_adapters.world_pal_adapter import (
    WorldPalAdapter,
)

# What `SaveManager.storage_adapters` maps a storageKey to. A union rather than a
# base class or Protocol: the three formats share no method a caller invokes
# without already knowing which one it holds.
PalStorageAdapter = DpsPalAdapter | GpsPalAdapter | WorldPalAdapter

__all__ = [
    "DpsPalAdapter",
    "GpsPalAdapter",
    "PalStorageAdapter",
    "WorldPalAdapter",
]
