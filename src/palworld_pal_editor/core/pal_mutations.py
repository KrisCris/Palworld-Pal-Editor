"""Moving a Pal, copying one somewhere else, and overwriting one with another.

Three things can happen when an existing Pal meets another place or another Pal,
and this module is all three:

    relocate         the same physical Pal, somewhere else. One `PalRecord` throughout.
    replicate        a second physical Pal built from the first. The source stays.
    update-existing  the destination keeps its record and takes the source's payload.

Which one a given source and target mean is not a mode the caller picks. `plan()`
answers it once, and the same answer serves both the capability the move dialog reads
before it offers a target and the transfer that follows -- so the UI cannot offer
something the backend will refuse, and neither side re-derives the rules.

Nothing here snapshots the session. Each executor checks everything it can before it
writes, builds the target payload on a detached copy, and then deep-copies only the
handful of native parents its short commit touches -- see `TouchedParents`.
"""

import copy
import traceback
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from palworld_save_tools.archive import UUID

from palworld_pal_editor.core.pal_entity import PalEntity
from palworld_pal_editor.core.pal_objects import PalObjects, toUUID
from palworld_pal_editor.core.pal_record import PalRecord
from palworld_pal_editor.core.pal_storage_adapters import WorldPalAdapter
from palworld_pal_editor.core.pal_transactions import (
    PalIdentityConflict,
    PalOperationRefused,
    TouchedParents,
    prepare_global_parameter,
    restore_dict,
    restore_list,
    restore_local_parameter_envelope,
    set_owner,
)
from palworld_pal_editor.utils import LOGGER

if TYPE_CHECKING:
    from palworld_pal_editor.core.save_manager import SaveManager


# What a source/target pair means. These three strings are the contract between the
# capability endpoint, this service and the frontend; nothing derives behaviour from
# a storage kind on either side of it.
RELOCATE = "relocate"
REPLICATE = "replicate"
UPDATE_EXISTING = "update-existing"



















@dataclass(slots=True)
class TransferPlan:
    """What one source and one target mean, decided once and used twice.

    `reason` being None is what `allowed` means -- there is no third state where a
    transfer is refused without saying why.
    """

    effect: Optional[str]
    reason: Optional[str] = None
    descriptor: Optional[dict] = None
    # The logical owner the Pal ends up with. Not the storage's owner: a DPS belongs
    # to a player, but the Pals in it keep whoever owned them.
    owner_uid: Optional[str] = None
    # The guild the Pal ends up in. Usually the target storage's, but a shared
    # storage has none of its own, so a Pal put in one stays in the guild it was
    # already in.
    group_id: Optional[str] = None
    candidates: list[PalRecord] = field(default_factory=list)

    @property
    def allowed(self) -> bool:
        return self.reason is None


def _refused(reason: str) -> TransferPlan:
    return TransferPlan(effect=None, reason=reason)


@dataclass(slots=True)
class OperationOutcome:
    """What one transfer changed, in the terms the operation result is built from."""

    record: PalRecord
    deleted_record_keys: list[str] = field(default_factory=list)
    affected_storage_keys: list[str] = field(default_factory=list)


class PalMutationService:
    """The one owner of relocate, replicate and update-existing.

    It holds the session rather than copying anything out of it: every Pal it moves
    stays the repository's, and every native dict it writes is the save file's own.
    """

    def __init__(self, manager: "SaveManager") -> None:
        self._manager = manager

    # --- planning ---------------------------------------------------------

    def capability(self, source_record_key: str, target_storage_key: str) -> TransferPlan:
        """What would happen if this Pal were sent to this storage, without doing it."""
        source = self._manager.get_record(source_record_key)
        if source is None:
            return _refused("SOURCE_NOT_FOUND")
        return self.plan(source, target_storage_key)

    def plan(self, source: PalRecord, target_storage_key: str) -> TransferPlan:
        manager = self._manager
        if source.storage_key is None:
            # A World Pal that does not occupy the slot it records for itself has no
            # position to move out of.
            return _refused("SOURCE_LOCATION_ANOMALY")
        descriptor = manager.storage_directory.descriptor(target_storage_key)
        if descriptor is None:
            return _refused("TARGET_NOT_FOUND")
        if descriptor["StorageKey"] == source.storage_key:
            return _refused("ALREADY_IN_TARGET")
        if source.storage_kind == "global_palbox":
            return self._plan_out_of_global(source, descriptor)
        if descriptor["StorageKind"] == "global_palbox":
            return self._plan_into_global(source, descriptor)
        return self._plan_relocate(source, descriptor)

    def _plan_out_of_global(self, source: PalRecord, descriptor: dict) -> TransferPlan:
        """Global Palbox to somewhere local. Only a player's own party or palbox."""
        if not (
            descriptor["StorageKind"] == "world"
            and descriptor["ContainerKind"] in {"party", "storage"}
            and descriptor.get("OwnerPlayerUId")
        ):
            return _refused("GPS_PLAYER_TARGET_REQUIRED")
        owner = self._manager.get_player(descriptor["OwnerPlayerUId"])
        if owner is None:
            return _refused("TARGET_OWNER_UNAVAILABLE")
        if self._manager.group_data.get_group(descriptor.get("GroupId")) is None:
            return _refused("TARGET_GUILD_UNAVAILABLE")

        candidates = self._local_candidates(source)
        if candidates:
            return TransferPlan(
                UPDATE_EXISTING, descriptor=descriptor, candidates=candidates
            )
        container = self._manager.container_data.get_container(
            descriptor["ContainerId"]
        )
        if container is None or container.get_free_slot_index() == -1:
            return _refused("TARGET_FULL")
        return TransferPlan(
            REPLICATE,
            descriptor=descriptor,
            owner_uid=str(owner.PlayerUId),
            group_id=descriptor["GroupId"],
        )

    def _plan_into_global(self, source: PalRecord, descriptor: dict) -> TransferPlan:
        """Somewhere local to the Global Palbox. The source is always kept."""
        adapter = self._manager.storage_adapters.get(descriptor["StorageKey"])
        if adapter is None:
            return _refused("GLOBAL_PALBOX_UNAVAILABLE")
        candidates = self._global_candidates(source)
        if candidates:
            return TransferPlan(
                UPDATE_EXISTING, descriptor=descriptor, candidates=candidates
            )
        if adapter.storage.free_index() < 0:
            return _refused("TARGET_FULL")
        return TransferPlan(REPLICATE, descriptor=descriptor)

    def _plan_relocate(self, source: PalRecord, descriptor: dict) -> TransferPlan:
        """World and DPS in every combination: the Pal itself goes, and only once."""
        manager = self._manager
        if source.pal.IsExpeditionPal:
            return _refused("EXPEDITION_PAL")
        if not descriptor["MovableInto"]:
            return _refused("TARGET_NOT_MOVABLE")

        if descriptor["StorageKind"] == "dps":
            adapter = manager.storage_adapters.get(descriptor["StorageKey"])
            if adapter is None:
                return _refused("TARGET_NOT_FOUND")
            if adapter.storage.free_index() < 0:
                return _refused("TARGET_FULL")
            if any(
                record.pal.InstanceId == source.pal.InstanceId
                for record in adapter.records()
            ):
                return _refused("DUPLICATE_IN_TARGET")
            # A DPS is a place, not a person: the Pal keeps the owner it already has.
            return TransferPlan(
                RELOCATE,
                descriptor=descriptor,
                owner_uid=_uid_text(source.pal.OwnerPlayerUId),
            )

        if descriptor["StorageKind"] != "world":
            return _refused("TARGET_NOT_MOVABLE")
        container = manager.container_data.get_container(descriptor["ContainerId"])
        if container is None or container.get_free_slot_index() == -1:
            return _refused("TARGET_FULL")
        if container.has_pal(source.pal.InstanceId):
            return _refused("DUPLICATE_IN_TARGET")
        if source.storage_kind != "world" and manager.records_by_instance(
            source.pal.InstanceId, "world"
        ):
            return _refused("DUPLICATE_IN_TARGET")

        shared = bool(descriptor.get("Shared"))
        group_id = descriptor.get("GroupId")
        if descriptor["ContainerKind"] == "base":
            owner_uid = None
        elif shared:
            # A viewing cage is nobody's, so the Pal in it stays whoever's it was --
            # which means it has to be someone's to begin with, and it stays in that
            # owner's guild rather than in the cage's, which has none.
            if source.pal.OwnerPlayerUId is None:
                return _refused("OWNER_REQUIRED")
            owner_uid = str(source.pal.OwnerPlayerUId)
            group_id = self._source_group_id(source)
        else:
            target_owner = manager.get_player(descriptor.get("OwnerPlayerUId"))
            if target_owner is None:
                return _refused("TARGET_OWNER_UNAVAILABLE")
            owner_uid = str(target_owner.PlayerUId)
        if not shared and str(self._source_group_id(source)) != str(group_id):
            return _refused("CROSS_GUILD_UNSUPPORTED")
        if manager.group_data.get_group(group_id) is None:
            return _refused("TARGET_GUILD_UNAVAILABLE")
        return TransferPlan(
            RELOCATE,
            descriptor=descriptor,
            owner_uid=owner_uid,
            group_id=str(group_id),
        )

    def _source_group_id(self, source: PalRecord):
        """The guild the Pal counts as being in: its owner's, or its record's."""
        owner = self._manager.get_player(source.pal.OwnerPlayerUId)
        return owner.group_id if owner else source.group_id

    def _local_candidates(self, source: PalRecord) -> list[PalRecord]:
        return [
            record
            for record in self._manager.records_by_instance(source.pal.InstanceId)
            if record.storage_kind in {"world", "dps"}
        ]

    def _global_candidates(self, source: PalRecord) -> list[PalRecord]:
        return self._manager.records_by_instance(source.pal.InstanceId, "gps")

    # --- executing --------------------------------------------------------

    def transfer(
        self,
        source_record_key: str,
        target_storage_key: str,
        expected_target: Optional[dict] = None,
    ) -> OperationOutcome:
        """Send one Pal to one storage, whatever that turns out to mean.

        `expected_target` is the one existing Pal the user has just been shown and
        confirmed overwriting, and it appears only for that. It is re-checked here
        rather than trusted, because the dialog was open while the session was not
        locked.
        """
        source = self._manager.get_record(source_record_key)
        if source is None:
            raise PalOperationRefused(
                "SOURCE_NOT_FOUND", f"No Pal record named {source_record_key}"
            )
        plan = self.plan(source, target_storage_key)
        if not plan.allowed:
            raise PalOperationRefused(
                plan.reason,
                f"Cannot send {source.record_key} to {target_storage_key}: "
                f"{plan.reason}",
            )
        LOGGER.info(
            f"Pal transfer requested: effect={plan.effect} "
            f"source_record={source.record_key} source_storage={source.storage_key} "
            f"pal={source.pal.InstanceId} pal_owner={source.pal.OwnerPlayerUId} "
            f"target_storage={plan.descriptor['StorageKey']} "
            f"target_kind={plan.descriptor['StorageKind']}"
        )
        if plan.effect == UPDATE_EXISTING:
            return self._update_existing(
                source, self._locked_destination(plan, expected_target)
            )
        if plan.effect == REPLICATE:
            return self._replicate(source, plan)
        return self._relocate(source, plan)

    def _locked_destination(
        self, plan: TransferPlan, expected_target: Optional[dict]
    ) -> PalRecord:
        """The candidate the user confirmed, still where they were shown it.

        A target that has since been deleted, moved or joined by a second candidate
        comes back as the same conflict the user answered the first time, rather than
        as a distinct staleness the dialog would need its own branch for.
        """
        if not isinstance(expected_target, dict) or len(plan.candidates) > 1:
            # A second candidate appearing since the dialog opened is the same
            # staleness as the first one moving: what the user confirmed is no
            # longer what they were asked, so they are asked again.
            raise PalIdentityConflict(plan.candidates)
        destination = next(
            (
                candidate
                for candidate in plan.candidates
                if candidate.record_key == expected_target.get("recordKey")
                and candidate.storage_key == expected_target.get("storageKey")
            ),
            None,
        )
        if destination is None:
            raise PalIdentityConflict(plan.candidates)
        return destination

    # --- relocate ---------------------------------------------------------

    def _relocate(self, source: PalRecord, plan: TransferPlan) -> OperationOutcome:
        if source.storage_kind == "world" and plan.descriptor["StorageKind"] == "world":
            return self._relocate_within_world(source, plan)
        if plan.descriptor["StorageKind"] == "dps":
            return self._relocate_into_storage(source, plan)
        return self._relocate_into_world(source, plan)

    def _relocate_within_world(
        self, source: PalRecord, plan: TransferPlan
    ) -> OperationOutcome:
        """One container to another. Even the native record stays.

        Nothing about the Pal changes format, so there is nothing to build and
        nothing to register: the slot moves, the owner settles, and the record it has
        had all along is re-keyed onto its new storage.
        """
        manager = self._manager
        pal = source.pal
        target_container = manager.container_data.get_container(
            plan.descriptor["ContainerId"]
        )
        source_container = manager.container_data.get_container(pal.ContainerId)
        source_slot = source_container.get_slot(pal.InstanceId)
        origin_storage_key = source.storage_key
        origin_slot_index = source.slot_index

        touched = TouchedParents()
        touched.watch_container(source_container)
        touched.watch_container(target_container)
        touched.watch_dict(pal.pal_param)
        touched.on_undo(
            lambda: _restore_location(source, origin_storage_key, origin_slot_index)
        )
        try:
            slot_index = target_container.add_slot_copy(source_slot)
            if slot_index < 0:
                raise ValueError("Target container has no free slot.")
            source_container.del_pal(pal.InstanceId)
            pal.SlotId = (target_container.ID, slot_index)
            set_owner(pal, plan.owner_uid)
            manager.pal_repository.rebind_and_rekey(
                source,
                record_key=source.record_key,
                storage_kind="world",
                storage_key=WorldPalAdapter.storage_key(target_container.ID),
                slot_index=slot_index,
                native_record=source.native_record,
                pal=pal,
                storage_owner_uid=plan.owner_uid,
            )
        except Exception:
            touched.restore()
            manager.pal_repository.reindex()
            raise
        return self._settled(source, [origin_storage_key])

    def _relocate_into_storage(
        self, source: PalRecord, plan: TransferPlan
    ) -> OperationOutcome:
        """World or DPS into a DPS. The payload converts; the record does not change."""
        manager = self._manager
        adapter = manager.storage_adapters[plan.descriptor["StorageKey"]]
        save_parameter = copy.deepcopy(source.pal.save_parameter)
        instance_id = source.pal.InstanceId
        owner = manager.get_player(plan.owner_uid) if plan.owner_uid else None
        entering_from_world = source.storage_kind == "world"
        origin_storage_key = source.storage_key
        origin_record_key = source.record_key

        touched = TouchedParents()
        touched.watch_dict(adapter.storage.entries[adapter.storage.free_index()])
        touched.watch_storage_dirty(adapter.storage)
        if entering_from_world:
            touched.watch_list(manager.locker.entries())
        try:
            allocated = adapter.allocate(save_parameter, instance_id)
            self.release_record(source, touched)
            if entering_from_world:
                # A Pal held outside the world save is registered in the locker, and
                # the game treats one that is not as still standing in its container.
                manager.locker.add(instance_id)
            manager.pal_repository.rebind_and_rekey(
                source,
                record_key=allocated.record_key,
                storage_kind=adapter.kind,
                storage_key=adapter.storage_key,
                slot_index=allocated.slot_index,
                native_record=allocated.native_record,
                pal=allocated.pal,
                storage_owner_uid=adapter.storage.owner_uid,
                group_id=owner.group_id if owner else None,
            )
        except Exception:
            touched.restore()
            manager.pal_repository.reindex()
            raise
        return self._settled(source, [origin_storage_key], deleted=[origin_record_key])

    def _relocate_into_world(
        self, source: PalRecord, plan: TransferPlan
    ) -> OperationOutcome:
        """A DPS Pal back into a container. It becomes a World record and stops being a copy."""
        manager = self._manager
        descriptor = plan.descriptor
        container = manager.container_data.get_container(descriptor["ContainerId"])
        group = manager.group_data.get_group(plan.group_id)
        instance_id = source.pal.InstanceId
        save_parameter = copy.deepcopy(source.pal.save_parameter)
        origin_storage_key = source.storage_key
        origin_record_key = source.record_key

        touched = TouchedParents()
        touched.watch_container(container)
        touched.watch_group(group)
        touched.watch_list(manager.locker.entries())
        try:
            slot_index = container.add_pal(instance_id)
            if slot_index < 0:
                raise ValueError("Target world container is full.")
            native_record, pal = self._build_world_pal(
                save_parameter, instance_id, container, slot_index, plan
            )
            if not group.add_pal(instance_id):
                raise ValueError("Pal already exists in the target guild.")
            manager.world_adapter.append(native_record)
            touched.on_undo(lambda: manager.world_adapter.remove(native_record))
            self.release_record(source, touched)
            manager.locker.remove(instance_id)
            manager.pal_repository.rebind_and_rekey(
                source,
                record_key=f"world:{instance_id}",
                storage_kind="world",
                storage_key=WorldPalAdapter.storage_key(container.ID),
                slot_index=slot_index,
                native_record=native_record,
                pal=pal,
                storage_owner_uid=plan.owner_uid,
            )
        except Exception:
            touched.restore()
            manager.pal_repository.reindex()
            raise
        return self._settled(source, [origin_storage_key], deleted=[origin_record_key])

    # --- replicate --------------------------------------------------------

    def _replicate(self, source: PalRecord, plan: TransferPlan) -> OperationOutcome:
        """A second physical Pal. The source is untouched, and keeps its identity."""
        if plan.descriptor["StorageKind"] == "global_palbox":
            return self._replicate_into_global(source, plan)
        return self._replicate_into_world(source, plan)

    def _replicate_into_global(
        self, source: PalRecord, plan: TransferPlan
    ) -> OperationOutcome:
        manager = self._manager
        adapter = manager.storage_adapters[plan.descriptor["StorageKey"]]
        parameter = prepare_global_parameter(
            source.pal.save_parameter, preserve_provenance=True
        )

        touched = TouchedParents()
        touched.watch_dict(adapter.storage.entries[adapter.storage.free_index()])
        touched.watch_storage_dirty(adapter.storage)
        try:
            record = adapter.allocate(parameter, source.pal.InstanceId)
            manager.pal_repository.register(record, created=True)
        except Exception:
            touched.restore()
            manager.pal_repository.reindex()
            raise
        return self._settled(record, [source.storage_key], modified=False)

    def _replicate_into_world(
        self, source: PalRecord, plan: TransferPlan
    ) -> OperationOutcome:
        manager = self._manager
        descriptor = plan.descriptor
        container = manager.container_data.get_container(descriptor["ContainerId"])
        group = manager.group_data.get_group(plan.group_id)
        instance_id = source.pal.InstanceId
        save_parameter = copy.deepcopy(source.pal.save_parameter)

        touched = TouchedParents()
        touched.watch_container(container)
        touched.watch_group(group)
        try:
            slot_index = container.add_pal(instance_id)
            if slot_index < 0:
                raise ValueError("Target world container is full.")
            native_record, pal = self._build_world_pal(
                save_parameter, instance_id, container, slot_index, plan
            )
            # A Pal that came back out of the Global Palbox is not away on the
            # expedition its copy was taken during.
            pal.pal_param.pop("MapObjectConcreteInstanceIdAssignedToExpedition", None)
            if not group.add_pal(instance_id):
                raise ValueError("Pal already exists in the target guild.")
            manager.world_adapter.append(native_record)
            touched.on_undo(lambda: manager.world_adapter.remove(native_record))
            record = WorldPalAdapter.record(
                native_record,
                storage_key=WorldPalAdapter.storage_key(container.ID),
                slot_index=slot_index,
                storage_owner_uid=plan.owner_uid,
                pal=pal,
            )
            manager.pal_repository.register(record, created=True)
        except Exception:
            touched.restore()
            manager.pal_repository.reindex()
            raise
        return self._settled(record, [source.storage_key], modified=False)

    # --- update-existing --------------------------------------------------

    def _update_existing(
        self, source: PalRecord, destination: PalRecord
    ) -> OperationOutcome:
        """The destination Pal keeps its record and takes the source's gameplay payload.

        Its position, owner and provenance are its own and stay: this is one Pal
        being brought up to date with another, not a Pal arriving somewhere.
        """
        manager = self._manager
        storage = self._storage_of(destination)

        touched = TouchedParents()
        touched.watch_dict(destination.pal.pal_param)
        if storage is not None:
            touched.watch_storage_dirty(storage)
        try:
            if destination.storage_kind == "global_palbox":
                merged = prepare_global_parameter(
                    source.pal.save_parameter, preserve_provenance=True
                )["value"]
            else:
                merged = restore_local_parameter_envelope(
                    copy.deepcopy(source.pal.save_parameter["value"]),
                    destination.pal.pal_param,
                )
            destination.pal.pal_param.clear()
            destination.pal.pal_param.update(merged)
            destination.pal.reset_display_name_cache()
            if storage is not None:
                storage.dirty = True
            manager.pal_repository.mark_modified(destination)
            manager.pal_repository.reindex()
        except Exception:
            touched.restore()
            manager.pal_repository.reindex()
            raise
        LOGGER.info(
            "Pal transfer succeeded: effect=update-existing "
            f"source_record={source.record_key} "
            f"target_record={destination.record_key} "
            f"target_storage={destination.storage_key} "
            f"target_slot={destination.slot_index} pal={destination.pal.InstanceId}"
        )
        manager.storage_directory.invalidate()
        return OperationOutcome(
            destination, affected_storage_keys=[destination.storage_key]
        )

    # --- shared steps -----------------------------------------------------

    # --- create -----------------------------------------------------------
    #
    # A creation is a plan with no source record. Where a Pal lands decides its
    # identity, its owner and its guild whether it arrived from another storage or
    # from nothing at all, so the three `_create_into_*` bodies below are the
    # `_relocate_into_*` and `_replicate_into_*` bodies with the release half
    # removed -- not a fourth set of rules.

    def _unused_instance_id(self, *claimed) -> UUID:
        """A Pal id nothing in this save is already using.

        `claimed` are the native structures the caller is about to write into -- a
        container, a guild. Those can hold a handle for an id the repository has no
        record for, and a Pal given that id would be the second thing answering to
        it in the save file.
        """
        manager = self._manager
        while True:
            instance_id = toUUID(str(uuid.uuid4()))
            if manager.records_by_instance(instance_id):
                continue
            if any(structure.has_pal(instance_id) for structure in claimed):
                continue
            return instance_id

    def create(
        self,
        roster_key: str,
        target_storage_key: str,
        save_parameter: Optional[dict] = None,
        pal_owner_uid: Optional[str | UUID] = None,
    ) -> PalRecord:
        """Create one Pal in `target_storage_key`, in that storage's own format.

        `save_parameter` is the complete gameplay payload the new Pal is copied
        from -- a live Pal, a template, an imported record -- or None for a default
        Pal. It is the only thing a source contributes: identity, owner, guild and
        position are the target storage's to decide, which is what makes a template
        made from a Global Palbox Pal creatable into a player Palbox.
        """
        allowed = {
            descriptor["StorageKey"]: descriptor
            for descriptor in self._manager.storage_directory.creation_targets(roster_key)
        }
        descriptor = allowed.get(str(target_storage_key))
        if descriptor is None:
            raise ValueError("Target storage is not valid for this roster.")

        kind = descriptor["StorageKind"]
        if kind == "world":
            player_uid = (
                roster_key
                if roster_key != "base-workers"
                else descriptor.get("OwnerPlayerUId")
            )
            return self.create_world_pal(
                player_uid, save_parameter, descriptor["ContainerId"]
            )
        if kind == "global_palbox":
            return self._create_into_global(save_parameter)
        if kind == "dps":
            return self._create_into_dps(
                descriptor, roster_key, pal_owner_uid, save_parameter
            )
        raise ValueError("Creation for this storage is not implemented yet.")

    def _create_into_global(self, save_parameter: Optional[dict]) -> PalRecord:
        manager = self._manager
        storage = manager.global_palbox
        if storage is None:
            raise ValueError("Global Palbox is unavailable.")
        target_index = storage.free_index()
        if target_index < 0:
            raise ValueError("Global Palbox is full.")
        touched = TouchedParents()
        touched.watch_dict(storage.entries[target_index])
        touched.watch_storage_dirty(storage)
        try:
            # No World record is built on the way: a Global Palbox Pal is a
            # parameter in a preallocated slot, and normalizing it is what clears
            # the position and provenance a copied payload arrives with.
            record = manager.storage_adapters[storage.storage_key].allocate(
                prepare_global_parameter(
                    save_parameter
                    if save_parameter is not None
                    else PalObjects.DefaultPalSaveParameter(
                        PalObjects.EMPTY_UUID, PalObjects.EMPTY_UUID, -1
                    ),
                    preserve_provenance=False,
                ),
                self._unused_instance_id(),
            )
            manager.pal_repository.register(record, created=True)
        except Exception:
            touched.restore()
            raise
        manager.storage_directory.invalidate()
        LOGGER.info(
            "Created Global Palbox Pal: "
            f"record={record.record_key} slot={record.slot_index} "
            f"pal={record.pal.InstanceId}"
        )
        return record

    def _create_into_dps(
        self,
        descriptor: dict,
        roster_key: str,
        pal_owner_uid: Optional[str | UUID],
        save_parameter: Optional[dict],
    ) -> PalRecord:
        manager = self._manager
        storage_owner = manager.get_player(roster_key)
        player = manager.get_player(pal_owner_uid) if pal_owner_uid else storage_owner
        storage = manager.dps_storages.get(descriptor["StorageKey"])
        if storage_owner is None or player is None or storage is None:
            raise ValueError("DPS owner or storage is unavailable.")
        target_index = storage.free_index()
        if target_index < 0:
            raise ValueError("Target DPS is full.")
        touched = TouchedParents()
        touched.watch_dict(storage.entries[target_index])
        touched.watch_storage_dirty(storage)
        touched.watch_list(manager.locker.entries())
        try:
            instance_id = self._unused_instance_id()
            record = manager.storage_adapters[storage.storage_key].allocate(
                save_parameter
                if save_parameter is not None
                else PalObjects.DefaultPalSaveParameter(
                    player.PlayerUId, PalObjects.EMPTY_UUID, -1
                ),
                instance_id,
            )
            # The slot is the Pal now, so the rest is written through it rather than
            # onto a scratch record: whatever the payload said about where it lived
            # and who owned it belongs to wherever it came from.
            pal = record.pal
            pal.SlotId = (PalObjects.EMPTY_UUID, -1)
            set_owner(pal, player.PlayerUId)
            pal.pal_param.pop("MapObjectConcreteInstanceIdAssignedToExpedition", None)
            manager.locker.add(instance_id)
            manager._register_external_record(record, created=True)
        except Exception:
            touched.restore()
            raise
        manager.storage_directory.invalidate()
        LOGGER.info(
            "Created DPS Pal: "
            f"record={record.record_key} storage={record.storage_key} "
            f"slot={record.slot_index} pal={record.pal.InstanceId} "
            f"pal_owner={record.pal.OwnerPlayerUId} locker_action=add"
        )
        return record

    def _resolve_world_creation_target(self, player_uid, target_container_id):
        """Which container, guild, owner and historical owner a creation lands on.

        Two ways in. With a target container the storage decides everything and the
        requested player only has to belong to the same guild; without one the Pal
        goes to the requesting player's own party, or their Palbox if the party is
        full. A base container has no owner, which is why the owner and the
        historical owner are separate answers: the Pal ends up owned by nobody but
        still records whose guild caught it.
        """
        manager = self._manager
        requested_player = manager.get_player(player_uid)

        if target_container_id is None:
            if requested_player is None:
                raise ValueError(f"Player {player_uid} not found")
            container = next(
                (
                    candidate
                    for container_id in (
                        requested_player.OtomoCharacterContainerId,
                        requested_player.PalStorageContainerId,
                    )
                    if (
                        candidate := manager.container_data.get_container(container_id)
                    ) is not None
                    and candidate.get_free_slot_index() != -1
                ),
                None,
            )
            return (
                container,
                requested_player.group_id,
                requested_player,
                requested_player,
            )

        descriptor = manager.storage_directory.descriptor(target_container_id)
        if descriptor is None or not descriptor["MovableInto"]:
            raise ValueError(f"Unsafe target container {target_container_id}")
        container = manager.container_data.get_container(target_container_id)
        if container is None or container.get_free_slot_index() == -1:
            raise ValueError("No empty Pal slot")
        group_id = descriptor.get("GroupId")
        owner_id = descriptor.get("OwnerPlayerUId")
        owner_player = manager.get_player(owner_id) if owner_id else None
        if descriptor["ContainerKind"] != "base" and owner_player is None:
            raise ValueError("Target container owner not found")
        if requested_player and str(requested_player.group_id) != str(group_id):
            raise ValueError("Cross-guild Pal creation is unsupported")
        historical_player = owner_player or (
            requested_player
            if requested_player and str(requested_player.group_id) == str(group_id)
            else next(
                (
                    player
                    for player in manager.get_players()
                    if str(player.group_id) == str(group_id)
                ),
                None,
            )
        )
        return container, group_id, owner_player, historical_player

    def _build_created_world_pal(
        self,
        save_parameter,
        instance_id,
        container,
        slot_index,
        group_id,
        owner_player,
        historical_player,
    ):
        """The world Pal a creation writes, provenance included.

        This does not reuse `_build_world_pal`, and the reason is the provenance: a
        relocated Pal *appends* its new owner to the history it arrived with, while
        a created one *starts* a history at whoever's guild made it. Forcing one
        builder to do both would hide that difference rather than remove it.
        """
        native_record = WorldPalAdapter.native_record(
            save_parameter,
            instance_id=instance_id,
            owner_uid=historical_player.PlayerUId,
            container_id=container.ID,
            slot_index=slot_index,
            group_id=group_id,
        )
        pal = WorldPalAdapter.entity(native_record)
        if save_parameter is not None:
            # The item container id is not necessarily referenced in
            # ItemContainerSaveData, so a fresh one is assigned rather than shared
            # with whatever the payload was copied from.
            pal.pal_param["EquipItemContainerId"] = PalObjects.PalContainerId(
                str(uuid.uuid4())
            )
        historical_uid = historical_player.PlayerUId
        pal.pal_param["OldOwnerPlayerUIds"] = PalObjects.ArrayProperty(
            "StructProperty",
            {
                "prop_name": "OldOwnerPlayerUIds",
                "prop_type": "StructProperty",
                "values": [toUUID(historical_uid)],
                "type_name": "Guid",
                "id": PalObjects.EMPTY_UUID,
            },
        )
        pal.pal_param["LastNickNameModifierPlayerUid"] = PalObjects.Guid(historical_uid)
        set_owner(pal, owner_player.PlayerUId if owner_player else None)
        pal.pal_param.pop("MapObjectConcreteInstanceIdAssignedToExpedition", None)
        return native_record, pal

    def create_world_pal(
        self,
        player_uid: str | UUID,
        save_parameter: Optional[dict] = None,
        target_container_id: Optional[str | UUID] = None,
    ) -> PalRecord:
        """Create one Pal in a world container.

        Raises rather than answering None: a caller that ignores a None writes a
        half-made Pal into the save, and every other mutation here already raises.
        """
        manager = self._manager
        (
            container,
            group_id,
            owner_player,
            historical_player,
        ) = self._resolve_world_creation_target(player_uid, target_container_id)
        if container is None or historical_player is None:
            raise ValueError("No valid Pal target or historical owner")
        group = manager.group_data.get_group(group_id)
        if group is None:
            raise ValueError(f"Group {group_id} not found")

        instance_id = self._unused_instance_id(container, group)
        touched = TouchedParents()
        touched.watch_container(container)
        touched.watch_group(group)
        try:
            slot_index = container.add_pal(instance_id)
            if slot_index < 0:
                raise ValueError("Target world container is full.")
            try:
                native_record, pal = self._build_created_world_pal(
                    save_parameter,
                    instance_id,
                    container,
                    slot_index,
                    group_id,
                    owner_player,
                    historical_player,
                )
            except ValueError:
                raise
            except Exception as error:
                # A payload that is not a Pal is a bad value, not a bug here. The
                # old chain reported every failure as one generic ValueError; this
                # keeps the type callers depend on and the cause they could not see.
                raise ValueError(
                    f"Pal payload could not be read: {error!r}"
                ) from error
            if not group.add_pal(instance_id):
                raise ValueError("Duplicated Pal ID in group")
            manager.world_adapter.append(native_record)
            touched.on_undo(lambda: manager.world_adapter.remove(native_record))
            record = manager.world_adapter.record(
                native_record,
                storage_key=WorldPalAdapter.storage_key(container.ID),
                slot_index=slot_index,
                storage_owner_uid=(
                    str(owner_player.PlayerUId) if owner_player else None
                ),
                pal=pal,
            )
            # Every creation entry point registers here, so a Pal made through the
            # CLI or through `create` is tracked the same way -- and marked created,
            # which is what settles its capture count and paldeck flag on save.
            manager.pal_repository.register(record, created=True)
        except Exception:
            touched.restore()
            raise
        manager.storage_directory.invalidate()
        LOGGER.info(f"Added Pal {pal} to container {container.ID}")
        return record

    def duplicate(self, record_key: str, roster_key: str) -> PalRecord:
        """A second Pal built from an existing one, landing where its kind allows.

        Which storage a copy goes to is the source's kind, not the caller's choice:
        an external Pal is copied within its own storage, a world Pal into the first
        of the roster's creation targets with room.
        """
        manager = self._manager
        source = manager.get_record(record_key)
        if source is None:
            raise ValueError("Selected Pal not found.")
        # The whole of what a copy inherits: every gameplay field the source has,
        # including the ones this editor has never heard of.
        source_parameter = source.pal.save_parameter

        if source.storage_kind == "global_palbox":
            clone = self.create("global-palbox", source.storage_key, source_parameter)
        elif source.storage_kind == "dps":
            storage = manager.dps_storages.get(source.storage_key)
            if storage is None:
                raise ValueError("Source DPS is unavailable.")
            clone = self.create(
                str(storage.owner_uid),
                source.storage_key,
                source_parameter,
                pal_owner_uid=source.pal.OwnerPlayerUId,
            )
        else:
            targets = [
                descriptor
                for descriptor in manager.storage_directory.creation_targets(roster_key)
                if descriptor["StorageKind"] == "world"
                and descriptor["ContainerKind"] in {"base", "party", "storage"}
                and descriptor["Occupied"] < descriptor["Capacity"]
            ]
            if not targets:
                raise ValueError("The target Pal containers are full.")
            clone = self.create(roster_key, targets[0]["StorageKey"], source_parameter)

        LOGGER.info(
            "Duplicated Pal: "
            f"source_record={source.record_key} "
            f"source_storage={source.storage_key} "
            f"source_pal={source.pal.InstanceId} "
            f"target_record={clone.record_key} "
            f"target_storage={clone.storage_key} "
            f"target_slot={clone.slot_index} "
            f"target_pal={clone.pal.InstanceId} "
            f"owner={clone.pal.OwnerPlayerUId}"
        )
        return clone

    def delete(self, record_key: str) -> bool:
        """Release a Pal from wherever it is and never put it down again.

        The same three format-specific bodies a relocate owns, with no destination.
        The record is the Pal's location; the baseworker and dangling maps it may
        also appear in are cleared by unregistering it.
        """
        manager = self._manager
        record = manager.get_record(record_key)
        if record is None:
            LOGGER.warning(f"Can't find pal {record_key}")
            return False
        touched = TouchedParents()
        if record.storage_kind == "dps":
            touched.watch_list(manager.locker.entries())
        try:
            self.release_record(record, touched)
            if record.storage_kind == "dps":
                # A Pal that is nowhere is not in the locker either.
                manager.locker.remove(record.pal.InstanceId)
        except Exception:
            touched.restore()
            LOGGER.warning(
                f"Error Deleting PAL {record_key}: {traceback.format_exc()}"
            )
            return False
        manager._unregister_record(record)
        manager.storage_directory.invalidate()
        LOGGER.info(
            f"DELETED PAL {record_key} storage={record.storage_key} "
            f"slot={record.slot_index} pal={record.pal.InstanceId}"
        )
        return True

    def heal_all(self) -> None:
        # Every base worker and dangling Pal is a registered record too, so one pass
        # over the repository covers what three passes over three collections did --
        # plus the Global Palbox, which the old palbox-shaped scan could not reach.
        for record in self._manager.pal_repository.records():
            record.pal.heal_pal()
            # Global Palbox and DPS Pals live outside the world save, so a heal that
            # skips this is discarded when the session is written -- the same
            # normalization every single-Pal edit does, owed to every Pal here too.
            self.normalize_external_record(record)
            self._manager.pal_repository.mark_modified(record)

    def _build_world_pal(
        self,
        save_parameter: dict,
        instance_id: UUID | str,
        container,
        slot_index: int,
        plan: TransferPlan,
    ) -> tuple[dict, PalEntity]:
        """A World record around a payload that came from somewhere else.

        The payload is everything the Pal is; identity, position, guild and owner all
        belong to where it is landing, which is why they are written after it and not
        read out of it.
        """
        native_record = WorldPalAdapter.native_record(
            save_parameter,
            instance_id=instance_id,
            owner_uid=plan.owner_uid or PalObjects.EMPTY_UUID,
            container_id=container.ID,
            slot_index=slot_index,
            group_id=plan.group_id,
        )
        pal = WorldPalAdapter.entity(native_record)
        set_owner(pal, plan.owner_uid)
        return native_record, pal

    def normalize_external_record(self, record: PalRecord) -> None:
        """Make an external record match the format its storage actually stores.

        A Pal read out of a GPS file carries a global envelope; a Pal in a DPS has
        to be in Level.sav's locker for the game to show it. Both are mutations of
        an already-placed Pal, which is why they live with the other mutations
        rather than on the session that loaded the file.
        """
        manager = self._manager
        if record.storage_kind == "global_palbox":
            save_parameter = prepare_global_parameter(
                record.pal.save_parameter, preserve_provenance=True
            )
            record.pal.pal_param.clear()
            record.pal.pal_param.update(save_parameter["value"])
            manager.global_palbox.dirty = True
        elif record.storage_kind == "dps":
            manager.locker.add(record.pal.InstanceId)
            storage = manager.dps_storages.get(record.storage_key)
            if storage is not None:
                storage.dirty = True

    def release_record(self, source: PalRecord, touched: TouchedParents) -> None:
        """Take the Pal out of wherever it is now, in that format's own terms.

        A relocate calls this halfway through and puts the Pal down again; a delete
        calls it and does not. The container and guild are looked up rather than
        assumed, because a save can hold a World Pal whose container is already gone
        -- `_log_location_anomalies` reports those, and deleting one is the fix.
        """
        manager = self._manager
        if source.storage_kind != "world":
            adapter = manager.storage_adapters[source.storage_key]
            touched.watch_dict(adapter.storage.entries[source.slot_index])
            touched.watch_storage_dirty(adapter.storage)
            adapter.clear(source.record_key)
            return

        container = manager.container_data.get_container(source.pal.ContainerId)
        group = manager.group_data.get_group(source.group_id)
        if container is not None:
            touched.watch_container(container)
        if group is not None:
            touched.watch_group(group)
        native_record = source.native_record
        if container is not None:
            container.del_pal(source.pal.InstanceId)
        if group is not None:
            group.del_pal(source.pal.InstanceId)
        entry_index = manager.world_adapter.remove(native_record)
        touched.on_undo(
            lambda: manager.world_adapter.insert(entry_index, native_record)
        )

    def _storage_of(self, record: PalRecord):
        """The save file a record lives in, or None for a World record."""
        if record.storage_kind == "world":
            return None
        return self._manager.storage_adapters[record.storage_key].storage

    def _settled(
        self,
        record: PalRecord,
        origin_storage_keys: list,
        deleted: Optional[list[str]] = None,
        modified: bool = True,
    ) -> OperationOutcome:
        """Everything owed after a successful commit, in one place.

        A Pal that moved is a Pal that changed, and the storage descriptors now count
        one more or one fewer Pal in two places -- forgetting either is silent, which
        is why no executor does it by hand. A replicate opts out of the edited mark
        only because it was registered as created, which outranks it.
        """
        manager = self._manager
        if modified:
            manager.pal_repository.mark_modified(record)
        manager.storage_directory.invalidate()
        LOGGER.info(
            "Pal transfer succeeded: "
            f"result_record={record.record_key} "
            f"result_storage={record.storage_key} result_slot={record.slot_index} "
            f"pal={record.pal.InstanceId} pal_owner={record.pal.OwnerPlayerUId} "
            f"origin_storage={','.join(str(key) for key in origin_storage_keys)}"
        )
        keys = [*origin_storage_keys, record.storage_key]
        return OperationOutcome(
            record,
            deleted_record_keys=list(deleted or []),
            affected_storage_keys=[key for key in dict.fromkeys(keys) if key],
        )


def _restore_location(record: PalRecord, storage_key, slot_index) -> None:
    record.storage_key = storage_key
    record.slot_index = slot_index


def _uid_text(value) -> Optional[str]:
    return str(value) if value else None
