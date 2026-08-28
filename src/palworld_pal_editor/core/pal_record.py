from dataclasses import dataclass
from typing import Literal

from palworld_save_tools.archive import UUID

from palworld_pal_editor.core.pal_entity import PalEntity


StorageKind = Literal["world", "dps", "global_palbox"]


@dataclass(eq=False, slots=True)
class PalRecord:
    """A runtime handle on one physical Pal record.

    Not a second copy of the Pal: ``native_record`` is the save file's own dict and
    ``pal`` reads through parent dicts inside it, so editing through ``pal`` edits
    what gets serialized.

    ``eq=False`` is deliberate — identity sets hold these objects across relocate,
    which mutates ``record_key``/``storage_key``/``slot_index``. A value-based hash
    over mutable fields would silently lose them.
    """

    record_key: str
    storage_kind: StorageKind
    # None when the Pal records a ContainerId that resolves to no real container.
    # Such a record stays out of the storage index rather than being given a fake key.
    storage_key: str | None
    slot_index: int | None
    native_record: dict
    pal: PalEntity
    # World only, read from the native record; DPS/GPS are always None.
    group_id: UUID | str | None = None
    # Which player's storage file this record physically lives in — not the Pal's
    # logical owner, which is always PalEntity.OwnerPlayerUId. Transitional: once the
    # storage adapter routing table exists it answers this from the storageKey.
    storage_owner_uid: str | None = None
