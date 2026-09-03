import copy
from typing import Optional, overload
from palworld_save_tools.gvas import GvasFile
from palworld_save_tools.archive import UUID

from palworld_pal_editor.core.pal_objects import PalObjects, toUUID
from palworld_pal_editor.utils import LOGGER


class PalContainer:
    def __init__(self, container_obj: dict) -> None:
        self._container_obj: dict = container_obj

        self._slots_data: list = PalObjects.get_ArrayProperty(
            self._container_obj["value"]["Slots"]
        )

        if self.ID is None or self._slots_data is None:
            raise Exception("Invalid Container")

        self.size: int = PalObjects.get_BaseType(self._container_obj["value"]["SlotNum"])
        if self.size is None:
            raise Exception(f"Container {self.ID} Size Unknown")

        self._rebuild_slot_state()

    def _rebuild_slot_state(self):
        self.slots = [ContainerSlot(slot_dict) for slot_dict in self._slots_data]

    def __len__(self):
        return len(self.slots)
    
    def __str__(self) -> str:
        return f"{self.ID} - {len(self)}"

    @property
    def ID(self) -> Optional[UUID]:
        return PalObjects.get_BaseType(self._container_obj.get("key", {}).get("ID"))

    def get_free_slot_index(self) -> int:
        """The lowest game ``SlotIndex`` this container has room for, or -1 if full.

        Derived from the slots themselves on every call. It used to be a heap kept
        alongside them, which had to be pushed and popped in step with every add and
        delete and went wrong quietly whenever one of those forgot.
        """
        if len(self.slots) >= self.size:
            return -1
        taken = {slot.SlotIndex for slot in self.slots}
        # -1 rather than StopIteration when a save records slot numbers outside the
        # container's own size; that is a broken save, not a full container.
        return next((index for index in range(self.size) if index not in taken), -1)

    def add_pal(self, pal_id: UUID | str) -> int:
        if self.has_pal(pal_id):
            return -1

        slot_index = self.get_free_slot_index()
        if slot_index == -1:
            return -1

        self._slots_data.append(PalObjects.ContainerSlotData(slot_index))
        slot = ContainerSlot(self._slots_data[-1])
        slot.instance_id = pal_id
        self.slots.append(slot)

        LOGGER.info(f"Pal {pal_id} add to container {self.ID} @ {slot_index}")
        return slot_index

    def get_slot(self, pal_id: UUID | str) -> Optional["ContainerSlot"]:
        entry_index = self._find_entry_index(pal_id)
        return self.slots[entry_index] if entry_index is not None else None

    def add_slot_copy(self, source_slot: "ContainerSlot") -> int:
        if source_slot is None or self.has_pal(source_slot.instance_id):
            return -1
        slot_index = self.get_free_slot_index()
        if slot_index == -1:
            return -1

        slot_data = copy.deepcopy(source_slot._slot_data)
        PalObjects.set_BaseType(slot_data["SlotIndex"], slot_index)
        self._slots_data.append(slot_data)
        self.slots.append(ContainerSlot(slot_data))
        return slot_index

    def snapshot_slots(self) -> list[dict]:
        return copy.deepcopy(self._slots_data)

    def restore_slots(self, snapshot: list[dict]):
        self._slots_data[:] = copy.deepcopy(snapshot)
        self._rebuild_slot_state()

    def del_pal(self, pal_id: UUID):
        entry_index = self._find_entry_index(pal_id)
        if entry_index is None:
            LOGGER.warning(f"Can't find PalID on del_pal: {str(pal_id)}.")
            return

        self.slots[entry_index].clear()  # unnecessary since 0.3.3
        self.slots.pop(entry_index)
        self._slots_data.pop(entry_index)

    def _find_entry_index(self, pal_id: UUID | str) -> Optional[int]:
        """Where this Pal's slot entry sits in the Python lists, for delete/replace.

        This is not a game ``SlotIndex``: `slots` and `_slots_data` hold one entry
        per occupied slot in save order, and the game index lives on the entry.
        """
        for index, slot in enumerate(self.slots):
            if str(slot.instance_id) == str(pal_id):
                return index
        return None

    def has_pal(self, pal_id: UUID | str) -> bool:
        return self._find_entry_index(pal_id) is not None

    # def reorder_pals(self, pal_ids: list[UUID | str]):
    #     id_num = len(pal_ids)
    #     for i in range(0, len(self.slots)):
    #         slot = self.slots[i]
    #         if i < id_num:
    #             slot.instance_id = pal_ids[i]
    #         else:
    #             slot.clear()


class ContainerSlot:
    def __init__(self, slot_data: dict) -> None:
        self._slot_data: dict = slot_data
        self._slot_raw_data: dict = slot_data["RawData"]["value"]

    @property
    def instance_id(self) -> Optional[UUID]:
        return self._slot_raw_data.get("instance_id")

    @property
    def SlotIndex(self) -> int:
        """The game slot number this entry occupies, same name as PalEntity's."""
        return PalObjects.get_BaseType(self._slot_data.get("SlotIndex"))

    @instance_id.setter
    def instance_id(self, id: UUID | str):
        self._slot_raw_data["instance_id"] = toUUID(id)

    def clear(self):
        self.instance_id = PalObjects.EMPTY_UUID


class ContainerData:
    def __init__(self, gvas_file: GvasFile) -> None:
        self.container_map = {}

        self._wsd = gvas_file.properties["worldSaveData"]["value"]
        if "CharacterContainerSaveData" not in self._wsd:
            LOGGER.info("No Container Found")
            return
        self._CCSD: dict = self._wsd["CharacterContainerSaveData"]

        for container in self._CCSD["value"]:
            try:
                container_entity = PalContainer(container)
            except Exception as e:
                LOGGER.warning(f"Invalid Container: {e}, skipping")
                continue

            self.container_map[container_entity.ID] = container_entity
            LOGGER.info(f"Container Found: {container_entity}")

    def get_container(self, id: UUID | str) -> Optional[PalContainer]:
        if id is None:
            return None
        container = self.container_map.get(id)
        if container is not None:
            return container
        try:
            return self.container_map.get(toUUID(str(id)))
        except (TypeError, ValueError):
            return None

    def get_containers(self) -> list[PalContainer]:
        return self.container_map.values()
