"""Reading a Pal that is not in the save: a pasted export, or a saved template.

The product is a `DetachedPalSource` -- one complete `SaveParameter` and the format
it was found in. It is deliberately not a `PalRecord`: it has no record key, no
storage, no slot and no change state, and the repository never sees it. Only once a
target adapter has written it somewhere does a real record exist.

Recognition is strict and per format. Each adapter answers only for its
own complete native shape, and nothing here falls back to "it seems to have a
SaveParameter in it somewhere" -- a record whose format cannot be named is a record
that would be imported as a guess.
"""

from dataclasses import dataclass

from palworld_pal_editor.core.pal_entity import PalEntity
from palworld_pal_editor.core.pal_objects import PalObjects
from palworld_pal_editor.core.pal_record import StorageKind
from palworld_pal_editor.core.pal_storage_adapters import (
    DpsPalAdapter,
    GpsPalAdapter,
    WorldPalAdapter,
)

# The three formats, asked in turn. Order is not significance: no two of them accept
# the same record, which is the property the strict checks exist to hold.
RECOGNIZERS = (WorldPalAdapter, DpsPalAdapter, GpsPalAdapter)


@dataclass(frozen=True, slots=True)
class DetachedPalSource:
    """One Pal read out of a native record, ready to be created somewhere.

    `save_parameter` is already a copy, so whatever it was read out of -- a stored
    template, a request body -- cannot be edited by the creation that follows.
    """

    kind: StorageKind
    save_parameter: dict

    def entity(self) -> PalEntity:
        """A `PalEntity` over this parameter, for reading the Pal before it exists.

        The identity half is a placeholder: a detached source has no InstanceId
        until something creates it, and nobody may read one off it.
        """
        return PalEntity(
            {"InstanceId": PalObjects.Guid(PalObjects.EMPTY_UUID)},
            {"SaveParameter": self.save_parameter},
        )


def detach_native_record(native_record) -> DetachedPalSource:
    """Recognise one native Pal record and take its complete gameplay payload."""
    for adapter in RECOGNIZERS:
        save_parameter = adapter.detach(native_record)
        if save_parameter is not None:
            return DetachedPalSource(adapter.kind, save_parameter)
    raise ValueError(
        "Not a Pal record this editor recognises: expected one World "
        "CharacterSaveParameterMap record, or a single-entry DPS or Global Palbox "
        "SaveParameterArray."
    )
