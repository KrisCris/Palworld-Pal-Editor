"""What storages this save has, and what each one is.

A storage descriptor is derived, never stored: it is a reading of the containers,
the base camps, the guilds, the players and the external storage files, taken
together. Nothing here mutates a save. That is the whole reason this is not a
method on `SaveManager` -- the session owns loading and saving, and answering
"what is this container" is a question about what was loaded, not a step in
loading it.

The answers are cached because a descriptor counts occupancy, so every Pal that
moves invalidates them. `invalidate()` is what a mutation calls.
"""

import re
from dataclasses import dataclass
from typing import Optional

from palworld_pal_editor.core.pal_record import StorageKind
from palworld_pal_editor.core.pal_repository import PalRecord
from palworld_pal_editor.utils import DataProvider


# The order the UI stacks storages in. Lower sorts first.
STORAGE_ROLE_ORDER = {
    "global_palbox": -1,
    "party": 0,
    "storage": 1,
    "dps": 2,
    "special": 3,
    "base": 4,
    "unknown": 5,
}

# A container with exactly this many slots is the viewing cage. The save says
# nothing else that distinguishes it, so the size is the whole test.
VIEWING_CAGE_SIZE = 40


@dataclass(frozen=True, slots=True)
class StorageDescriptor:
    """One storage, as it was the last time the directory built its map.

    A snapshot, not a live view: `occupied` was counted when the map was built and
    is valid until the next `StorageDirectory.invalidate()`. Every mutation that
    moves a Pal calls that, so a descriptor held across one is wrong about how full
    its storage is. Being frozen makes it look more authoritative than it is -- the
    dict this replaced was exactly as stale.

    `storage_role` is the finer of the two kind fields: seven roles (`party`,
    `storage`, `base`, `special`, `unknown`, `dps`, `global_palbox`) against
    `storage_kind`'s three save formats.

    `ContainerId` keeps the save's own spelling because it is the save's field, and
    it is `None` on the two storages that are their own `.sav` file rather than a
    container in Level.sav.
    """

    storage_key: str
    storage_kind: StorageKind
    storage_role: str
    storage_label: str
    ContainerId: Optional[str]
    # One number, not the `Size`/`Capacity` pair this replaced: both were always
    # written from the same value, and nothing ever read them apart.
    slot_count: int
    occupied: int
    # Whose storage this is. Invented, not the save's `OwnerPlayerUId`: for a DPS
    # this is the player whose file it is, which is not the same question as who
    # owns any Pal inside it.
    owner_player_uid: Optional[str] = None
    owner_name: Optional[str] = None
    group_id: Optional[str] = None
    # Which camp this is, and how the owner above was arrived at: `exact`,
    # `inferred`, `unknown` or `unknown_owner`. Production reads neither; they are
    # what a maintainer looks at when a container shows the wrong owner, and
    # `test_pal_container_registry.py` pins them.
    base_id: Optional[str] = None
    base_name: Optional[str] = None
    base_ordinal: Optional[int] = None
    classification: str = "unknown"
    movable_into: bool = False
    cloneable_into: bool = False
    shared: bool = False


@dataclass(frozen=True, slots=True)
class RecordLocation:
    """Where one Pal record sits, and what that place is called.

    The descriptor's fields for the storage, plus the two that are about this record
    rather than the storage. `ContainerId` and `SlotIndex` keep the save's spelling
    because they are its fields; both are `None` for a World record that failed its
    load-time slot check and therefore occupies nothing.
    """

    ContainerId: Optional[str]
    SlotIndex: Optional[int]
    storage_key: Optional[str]
    storage_kind: StorageKind
    storage_role: Optional[str]
    storage_label: Optional[str]


class StorageDirectory:
    def __init__(self, manager) -> None:
        self._manager = manager
        self._cache: Optional[dict[str, StorageDescriptor]] = None

    def invalidate(self) -> None:
        """Forget the cached descriptors after a Pal changed how full something is."""
        self._cache = None

    # --- the map ----------------------------------------------------------

    def _descriptor_map(self) -> dict[str, StorageDescriptor]:
        if self._cache is not None:
            return self._cache
        manager = self._manager
        # An unloaded session has no containers to describe. Left unsaid, the
        # camp and container reads below would raise on None and every storage
        # route would answer 500 with a traceback for an ordinary startup state.
        if manager.container_data is None or manager.camp_data is None:
            return {}

        # Order matters: players and camps claim their containers by id first, so
        # the sweep afterwards only sees the ones nothing has named.
        descriptors: dict[str, StorageDescriptor] = {}
        self._add_player_containers(descriptors)
        self._add_base_camps(descriptors)
        self._add_unclaimed_containers(descriptors)
        self._add_dps_storages(descriptors)
        self._add_global_palbox(descriptors)

        self._cache = descriptors
        return descriptors

    def _add_world_descriptor(self, descriptors: dict, container_id, **values) -> None:
        container = self._manager.container_data.get_container(container_id)
        if container is None:
            return
        descriptors[str(container.ID)] = StorageDescriptor(
            storage_key=f"world-container:{container.ID}",
            storage_kind="world",
            storage_role=values["kind"],
            storage_label=values["label"],
            ContainerId=str(container.ID),
            slot_count=container.SlotNum,
            occupied=len(container.slots),
            owner_player_uid=values.get("owner_player_uid"),
            owner_name=values.get("owner_name"),
            group_id=values.get("group_id"),
            base_id=values.get("base_id"),
            base_name=values.get("base_name"),
            base_ordinal=values.get("base_ordinal"),
            classification=values["classification"],
            movable_into=values["movable_into"],
            cloneable_into=False,
            shared=values.get("shared", False),
        )

    def _add_player_containers(self, descriptors: dict) -> None:
        for player in self._manager.get_players():
            owner_id = str(player.PlayerUId)
            group_id = str(player.group_id) if player.group_id else None
            self._add_world_descriptor(
                descriptors,
                player.OtomoCharacterContainerId,
                kind="party",
                label=f"{player.NickName} · Party",
                owner_player_uid=owner_id,
                owner_name=player.NickName,
                group_id=group_id,
                classification="exact",
                movable_into=True,
            )
            self._add_world_descriptor(
                descriptors,
                player.PalStorageContainerId,
                kind="storage",
                label=f"{player.NickName} · Palbox",
                owner_player_uid=owner_id,
                owner_name=player.NickName,
                group_id=group_id,
                classification="exact",
                movable_into=True,
            )

    def _add_base_camps(self, descriptors: dict) -> None:
        for base_ordinal, camp in enumerate(
            self._manager.camp_data.get_camps(), start=1
        ):
            # A camp still carrying the game's own placeholder name is numbered
            # instead; one the player renamed keeps the name they chose.
            template_match = re.fullmatch(
                r"新規生成拠点テンプレート名(\d+)\(仮\)", camp.name or ""
            )
            display_ordinal = base_ordinal if template_match else None
            self._add_world_descriptor(
                descriptors,
                camp.container_id,
                kind="base",
                label=(
                    f"Base {display_ordinal}"
                    if display_ordinal is not None
                    else camp.name or f"Base {str(camp.id)[:8]}"
                ),
                base_id=str(camp.id),
                base_name=camp.name,
                base_ordinal=display_ordinal,
                group_id=str(camp.owner_group_id),
                classification="exact",
                movable_into=True,
            )

    def _add_unclaimed_containers(self, descriptors: dict) -> None:
        """Containers no player and no camp named, identified by what is in them."""
        for container in self._manager.container_data.get_containers():
            if str(container.ID) in descriptors:
                continue

            if container.SlotNum == VIEWING_CAGE_SIZE:
                self._add_world_descriptor(
                    descriptors,
                    container.ID,
                    kind="special",
                    label="Viewing Cage",
                    classification="inferred",
                    movable_into=True,
                    shared=True,
                )
                continue

            owners, unresolved = self._container_owner_ids(container)
            inferred_owner = self._sole_owner_of(container, owners, unresolved)
            if inferred_owner is not None:
                kind_label = f"Special container ({container.SlotNum} slots)"
                self._add_world_descriptor(
                    descriptors,
                    container.ID,
                    kind="special",
                    label=f"{inferred_owner.NickName} · {kind_label}",
                    owner_player_uid=str(inferred_owner.PlayerUId),
                    owner_name=inferred_owner.NickName,
                    group_id=str(inferred_owner.group_id),
                    classification="inferred",
                    movable_into=True,
                )
                continue

            self._add_world_descriptor(
                descriptors,
                container.ID,
                kind="unknown",
                label=f"Unknown container ({container.SlotNum} slots)",
                classification="unknown",
                movable_into=False,
            )

    def _container_owner_ids(self, container) -> tuple[list[str], bool]:
        """Every occupant's owner, and whether any occupant could not be read."""
        owners = []
        unresolved = False
        for slot in container.slots:
            pal = self._manager.get_pal(slot.instance_id)
            if pal is None or pal.OwnerPlayerUId is None:
                unresolved = True
                continue
            owners.append(str(pal.OwnerPlayerUId))
        return owners, unresolved

    def _sole_owner_of(self, container, owners: list[str], unresolved: bool):
        """The one player who owns everything in here, or None.

        Every slot has to be occupied, readable, and owned by the same player: a
        container this cannot say that about is not claimed for anyone. Nor is one
        whose sole owner is not a player this save has -- that falls through to
        `unknown` exactly as it did before, with no anomaly, because a single
        unreadable owner is not a mixed-owner container.
        """
        if (
            not container.slots
            or unresolved
            or len(owners) != len(container.slots)
            or len(set(owners)) != 1
        ):
            return None
        return self._manager.get_player(owners[0])

    def _add_dps_storages(self, descriptors: dict) -> None:
        dps_name = DataProvider.get_tech_name("DimensionPalStorage") or (
            "Dimensional Pal Storage"
        )
        for storage in self._manager.dps_storages.values():
            owner = self._manager.get_player(storage.owner_uid)
            owner_name = owner.NickName if owner else storage.owner_uid
            descriptors[storage.storage_key] = StorageDescriptor(
                storage_key=storage.storage_key,
                storage_kind="dps",
                storage_role="dps",
                storage_label=f"{owner_name} · {dps_name}",
                ContainerId=None,
                slot_count=storage.slot_count,
                occupied=storage.occupied,
                owner_player_uid=storage.owner_uid,
                owner_name=owner_name,
                group_id=str(owner.group_id) if owner else None,
                classification="exact" if owner else "unknown_owner",
                movable_into=True,
                cloneable_into=False,
                shared=True,
            )

    def _add_global_palbox(self, descriptors: dict) -> None:
        storage = self._manager.global_palbox
        if storage is None:
            return
        descriptors[storage.storage_key] = StorageDescriptor(
            storage_key=storage.storage_key,
            storage_kind="global_palbox",
            storage_role="global_palbox",
            storage_label=(
                DataProvider.get_tech_name("GlobalPalStorage") or "Global Palbox"
            ),
            ContainerId=None,
            slot_count=storage.slot_count,
            occupied=storage.occupied,
            classification="exact",
            movable_into=False,
            cloneable_into=True,
            shared=True,
        )

    # --- questions callers ask -------------------------------------------

    def registry(self) -> list[StorageDescriptor]:
        return sorted(
            self._descriptor_map().values(),
            key=lambda item: (
                item.group_id or "",
                STORAGE_ROLE_ORDER.get(item.storage_role, 99),
                item.storage_label,
                item.ContainerId or "",
            ),
        )

    def descriptor(self, storage_key: str) -> Optional[StorageDescriptor]:
        return next(
            (
                descriptor
                for descriptor in self._descriptor_map().values()
                if descriptor.storage_key == str(storage_key)
                or descriptor.ContainerId == str(storage_key)
            ),
            None,
        )

    def resolve_record_location(self, record: PalRecord | str) -> RecordLocation:
        """Where a record sits, and what that place is called.

        There is one location, and it is the one the Pal records for itself,
        already validated at load. A World record that failed that check has no
        storage key and no container to name.
        """
        record_ref = (
            record
            if isinstance(record, PalRecord)
            else self._manager.get_record(record)
        )
        if record_ref is None:
            raise ValueError("Pal record not found")
        pal = record_ref.pal
        is_world = record_ref.storage_kind == "world"
        located = record_ref.storage_key is not None
        container_id = (
            str(pal.ContainerId) if is_world and located and pal.ContainerId else None
        )
        descriptor = (
            (self._descriptor_map().get(container_id) if located else None)
            if is_world
            else self.descriptor(record_ref.storage_key)
        )
        return RecordLocation(
            # The container and slot the record actually occupies. A World record that
            # failed its load-time slot check occupies neither, and says so.
            ContainerId=container_id,
            SlotIndex=record_ref.slot_index,
            storage_key=record_ref.storage_key,
            storage_kind=record_ref.storage_kind,
            storage_role=(
                descriptor.storage_role
                if descriptor
                else (None if is_world else record_ref.storage_kind)
            ),
            storage_label=descriptor.storage_label if descriptor else None,
        )

    def creation_targets(self, roster_key: str) -> list[StorageDescriptor]:
        """The storages a Pal added to this roster may be created in.

        Where a *new* Pal may go is not where an existing one may be moved, which
        is why this is not a filter over `registry()` the client could apply
        itself.
        """
        roster_key = str(roster_key)
        descriptors = self.registry()
        if roster_key == "base-workers":
            return [
                descriptor
                for descriptor in descriptors
                if descriptor.storage_role == "base" and descriptor.movable_into
            ]
        if roster_key == "global-palbox":
            return [
                descriptor
                for descriptor in descriptors
                if descriptor.storage_kind == "global_palbox"
                and descriptor.cloneable_into
            ]
        if self._manager.get_player(roster_key) is None:
            return []
        return [
            descriptor
            for descriptor in descriptors
            if (
                descriptor.storage_kind == "world"
                and descriptor.storage_role in {"party", "storage"}
                and descriptor.owner_player_uid == roster_key
            )
            or (
                descriptor.storage_kind == "dps"
                and descriptor.owner_player_uid == roster_key
            )
        ]
