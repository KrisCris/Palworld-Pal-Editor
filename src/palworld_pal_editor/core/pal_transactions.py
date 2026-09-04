"""The primitives every Pal mutation is built out of.

Two things live here, and neither is an operation. `TouchedParents` is the whole
of this codebase's transaction story: an operation deep-copies the handful of
native parents its commit touches, and rolling back means putting those copies
back. There is no journal and no global snapshot -- a save is far too large to
copy for every edit, and the parents a single write touches are few.

The rest is the Pal payload envelope: who owns a Pal and what its history says
(`set_owner`), and how a payload crossing between the world save and an external
storage file is dressed for its destination.

They are separated from `pal_mutations` because they have no opinion about
creating, moving, copying or deleting anything -- an operation uses them, and
they never call back into one.
"""

import copy
from palworld_save_tools.archive import UUID

from palworld_pal_editor.core.pal_entity import PalEntity
from palworld_pal_editor.core.pal_objects import PalObjects, toUUID
from palworld_pal_editor.core.pal_record import PalRecord


# What belongs to where a Pal is standing rather than to the Pal. A Global Palbox
# copy comes back carrying the Global Palbox's answers for all of these, so an
# overwrite keeps the destination's own.
DESTINATION_OWNED_KEYS = frozenset(
    {
        "OwnerPlayerUId",
        "OldOwnerPlayerUIds",
        "SlotId",
        "ItemContainerId",
        "EquipItemContainerId",
        "MapObjectConcreteInstanceIdAssignedToExpedition",
        "BaseCampWorkerEventType",
        "BaseCampWorkerEventProgressTime",
        "bImportedCharacter",
    }
)


class PalIdentityConflict(ValueError):
    """The target already holds a Pal with the source's identity.

    Carries every candidate rather than picking one: with two the backend has no
    basis to choose, and with one the user still has to see what will be overwritten.
    """

    def __init__(self, candidates: list[PalRecord]):
        super().__init__("Pal identity already exists in the destination")
        self.candidates = candidates


class PalOperationRefused(ValueError):
    """A transfer the current state does not allow, named by a stable business code.

    The message is for the log. What the user sees comes from `code`, which the
    frontend looks up in its own i18n table.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def set_owner(pal: PalEntity, owner_uid: UUID | str | None) -> None:
    """Settle who owns this Pal, current owner and history together.

    They are one decision, not two: the history is what the current owner used to be,
    so a caller that could write one without the other could leave a Pal owned by
    someone who never appears in its own provenance. An ownerless Pal -- a base
    worker, a Pal in the Global Palbox -- keeps the history it arrived with, because
    being put to work in a camp does not undo having been caught.
    """
    if owner_uid is None:
        pal.pal_param.pop("OwnerPlayerUId", None)
        return

    owner_uid = toUUID(str(owner_uid))
    pal.pal_param["OwnerPlayerUId"] = PalObjects.Guid(owner_uid)
    owners = pal.OldOwnerPlayerUIds
    if owners is None:
        pal.pal_param["OldOwnerPlayerUIds"] = PalObjects.ArrayProperty(
            "StructProperty",
            {
                "prop_name": "OldOwnerPlayerUIds",
                "prop_type": "StructProperty",
                "values": [owner_uid],
                "type_name": "Guid",
                "id": PalObjects.EMPTY_UUID,
            },
        )
    elif not owners or str(owners[-1]) != str(owner_uid):
        owners.append(owner_uid)


def prepare_global_parameter(
    source_parameter: dict,
    *,
    preserve_provenance: bool,
) -> dict:
    """A complete SaveParameter rewritten to the rules the Global Palbox keeps.

    Takes and returns the parameter rather than a `PalEntity`, so a Pal that does not
    exist yet -- a template, an import, a brand-new Pal -- can be normalized before
    anything has been written for it to be an entity of.
    """
    save_parameter = copy.deepcopy(source_parameter)
    parameter = save_parameter["value"]
    parameter["OwnerPlayerUId"] = PalObjects.Guid(PalObjects.EMPTY_UUID)
    parameter["ItemContainerId"] = PalObjects.PalContainerId(PalObjects.EMPTY_UUID)
    parameter["MapObjectConcreteInstanceIdAssignedToExpedition"] = PalObjects.Guid(
        PalObjects.EMPTY_UUID
    )
    parameter["bImportedCharacter"] = PalObjects.BoolProperty(True)
    parameter["BaseCampWorkerEventType"] = PalObjects.EnumProperty(
        "EPalBaseCampWorkerEventType",
        "EPalBaseCampWorkerEventType::None",
    )
    parameter["BaseCampWorkerEventProgressTime"] = PalObjects.FloatProperty(0.0)
    if not preserve_provenance:
        parameter["OldOwnerPlayerUIds"] = PalObjects.ArrayProperty(
            "StructProperty",
            {
                "prop_name": "OldOwnerPlayerUIds",
                "prop_type": "StructProperty",
                "values": [],
                "type_name": "Guid",
                "id": PalObjects.EMPTY_UUID,
            },
        )
        parameter["SlotId"] = PalObjects.PalCharacterSlotId(-1, PalObjects.EMPTY_UUID)
    return save_parameter


def restore_local_parameter_envelope(
    incoming_parameter: dict,
    destination_parameter: dict,
) -> dict:
    """The incoming gameplay payload, wearing the destination's own position."""
    merged = copy.deepcopy(incoming_parameter)
    for key in DESTINATION_OWNED_KEYS:
        if key in destination_parameter:
            merged[key] = copy.deepcopy(destination_parameter[key])
        else:
            merged.pop(key, None)
    return merged


def restore_dict(parent: dict, snapshot: dict) -> None:
    """Put a native dict's contents back, in place.

    In place matters: the save file's dicts are referenced from several directions at
    once -- a `PalEntity` binding, a parent array, an index -- so rebinding the name
    would restore the data and leave everything pointing at the old object.
    """
    parent.clear()
    parent.update(copy.deepcopy(snapshot))


def restore_list(parent: list, snapshot: list) -> None:
    """Put a native list's contents back, in place, for the same reason."""
    parent[:] = copy.deepcopy(snapshot)


class TouchedParents:
    """Deep copies of the few native parents one short commit writes into.

    This is a safety net against a bug in the lines below it, not a transaction
    system: every failure the save file can actually produce -- a full container, a
    stale target, a cross-guild move -- has already been answered by `plan()` before
    an executor starts. So it stays small, and what it holds is bounded by what the
    operation touches rather than by the size of the save.
    """

    def __init__(self) -> None:
        self._undo: list = []

    def watch_dict(self, parent: dict) -> None:
        snapshot = copy.deepcopy(parent)
        self._undo.append(lambda: restore_dict(parent, snapshot))

    def watch_list(self, parent: list) -> None:
        snapshot = copy.deepcopy(parent)
        self._undo.append(lambda: restore_list(parent, snapshot))

    def watch_container(self, container) -> None:
        snapshot = container.snapshot_slots()
        self._undo.append(lambda: container.restore_slots(snapshot))

    def watch_group(self, group) -> None:
        snapshot = group.snapshot_handles()
        self._undo.append(lambda: group.restore_handles(snapshot))

    def watch_storage_dirty(self, storage) -> None:
        """A storage file's unsaved flag, which a rolled-back write must not leave set."""
        dirty = storage.dirty
        self._undo.append(lambda: setattr(storage, "dirty", dirty))

    def on_undo(self, undo) -> None:
        """A one-off reversal for something no primitive above covers."""
        self._undo.append(undo)

    def restore(self) -> None:
        for undo in reversed(self._undo):
            undo()
