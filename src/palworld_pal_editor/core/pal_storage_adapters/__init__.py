"""Per-format readers and writers for the three places a Pal can physically live.

Each adapter walks its own native structure, hands ``PalEntity`` the two real parent
dicts it found there, and produces ``PalRecord``s for ``PalRepository``. Nothing here
owns identity, ownership, guild membership or conflict rules — those belong to the
operation layer.
"""

from palworld_pal_editor.core.pal_entity import PalEntity
from palworld_pal_editor.core.pal_storage_adapters.storage_pal_adapter import (
    DpsPalAdapter,
    GpsPalAdapter,
    StoragePalAdapter,
)
from palworld_pal_editor.core.pal_storage_adapters.world_pal_adapter import (
    WorldPalAdapter,
)

# What `SaveManager.storage_adapters` maps a storageKey to. A union rather than a
# base class or Protocol: the three formats share no method a caller invokes
# without already knowing which one it holds.
PalAdapter = DpsPalAdapter | GpsPalAdapter | WorldPalAdapter

def bind_entity(storage_kind: str, native_record: dict) -> PalEntity:
    """Bind a `PalEntity` to a native record through the adapter that owns its format.

    Every other binding happens where the record was read or written, next to the
    code that knows which shape it is holding. This exists for the one caller that
    does not: `PalRepository.rebind_and_rekey()` undoing itself has a record whose
    format it can only read off the record.
    """
    if storage_kind == WorldPalAdapter.kind:
        return WorldPalAdapter.entity(native_record)
    return StoragePalAdapter.entity(native_record)


__all__ = [
    "DpsPalAdapter",
    "GpsPalAdapter",
    "PalAdapter",
    "WorldPalAdapter",
    "bind_entity",
]
