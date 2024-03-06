from typing import Optional
from palworld_save_tools.archive import UUID

from palworld_pal_editor.core.pal_objects import PalObjects, toUUID
from palworld_pal_editor.utils import LOGGER

class PalContainer:
    def __init__(self, container_data: dict) -> None:       
        self._container_data: dict = container_data
        self._slots_data: dict = container_data["value"]["Slots"]["value"]["values"]
        self.ID: UUID = container_data["key"]["ID"]["value"]
        self.Slots: list[ContainerSlot] = [ContainerSlot(slot_dict) for slot_dict in self._slots_data]

    def __len__(self):
        return len(self.Slots)

    def add_pal(self, pal_id: UUID | str) -> int:
        """
        Return: Slot ID, or -1 if full
        """
        for i in range(0, len(self.Slots)):
            slot = self.Slots[i]
            if slot.isEmpty:
                slot.instance_id = pal_id
                LOGGER.info(f"Pal {pal_id} add to container {self.ID} @ {i} ")
                return i
        return -1
    
    def del_pal(self, pal_id: UUID | str, slot_idx: int):
        if slot_idx > len(self.Slots): return False
        self.Slots[slot_idx].clear()
    
    def has_pal(self, pal_id: UUID | str, slot_idx: int) -> bool:
        if slot_idx > len(self.Slots): return False
        return self.Slots[slot_idx].instance_id == pal_id

    def reorder_pals(self, pal_ids: list[UUID | str]):
        id_num = len(pal_ids)
        for i in range(0, len(self.Slots)):
            slot = self.Slots[i]
            if i < id_num:
                slot.instance_id = pal_ids[i]
            else:
                slot.clear()


class ContainerSlot:
    def __init__(self, slot_data: dict) -> None:
        self._slot_data: dict = slot_data
        self._slot_raw_data: dict = slot_data["RawData"]["value"]

    @property
    def isEmpty(self) -> bool:
        if "instance_id" not in self._slot_raw_data: return True
        return PalObjects.EMPTY_UUID == self._slot_raw_data["instance_id"]
    
    def clear(self):
        self.instance_id = PalObjects.EMPTY_UUID

    @property
    def instance_id(self) -> Optional[UUID]:
        return self._slot_raw_data.get("instance_id")
    
    @instance_id.setter
    def instance_id(self, id: UUID | str):
        self._slot_raw_data["instance_id"] = toUUID(id)

    


class CharacterContainerManager:
    _instance = None
    _container_save_data: Optional[dict]

    _container_mapping: Optional[dict]

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "initialized"):
            self.initialized = True

    def load(self, container_save_data: dict):
        self._container_save_data = container_save_data

        self._container_mapping = {}
        for container_data in container_save_data:
            pass

    def get_empty_slot(self, container_id: UUID | str) -> Optional[int]:
        container = self._container_mapping.get(container_id)
        pass