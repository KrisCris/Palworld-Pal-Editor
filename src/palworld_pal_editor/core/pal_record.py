"""One Pal, and the physical place in the save it lives.

A record pairs a `PalEntity` with where its bytes actually are -- which of the three
save formats, which storage, which slot. Two Pals that read identically are not
interchangeable: one may be in a player's palbox and the other in a Dimensional Pal
Storage file, and almost every rule about what may be done to a Pal turns on which.

`StorageKind` is defined here and only here, naming all three. The narrower one in
`pal_storage_file.py` is called `ExternalStorageKind` precisely so that nothing can
import it by this name and end up with a type that cannot describe a world Pal.
"""

from dataclasses import dataclass
from typing import Literal, Optional

from palworld_save_tools.archive import UUID

from palworld_pal_editor.core.pal_entity import PalEntity
from palworld_pal_editor.core.pal_objects import get_nested_attr


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
    # None when the Pal does not occupy the container slot it records for itself.
    # Such a record stays out of the storage index rather than being given a position
    # it is not in.
    storage_key: str | None
    slot_index: int | None
    native_record: dict
    pal: PalEntity
    # Which player's storage file this record physically lives in — not the Pal's
    # logical owner, which is always PalEntity.OwnerPlayerUId.
    storage_owner_uid: str | None = None
    # DPS and GPS entries carry no native guild id, so the loader stores the owning
    # player's guild here for the guild rules to compare against. World records
    # ignore this: `group_id` reads and writes their own native envelope.
    external_group_id: UUID | str | None = None

    @property
    def group_id(self) -> Optional[UUID | str]:
        """The Pal's guild id.

        A World record reads it live out of the native envelope it already holds, so
        this and the bytes that get serialized cannot drift apart.
        """
        if self.storage_kind == "world":
            return get_nested_attr(
                self.native_record, ["value", "RawData", "value", "group_id"]
            )
        return self.external_group_id

    @group_id.setter
    def group_id(self, group_id: UUID | str) -> None:
        if self.storage_kind == "world":
            self.native_record["value"]["RawData"]["value"]["group_id"] = group_id
        else:
            self.external_group_id = group_id
