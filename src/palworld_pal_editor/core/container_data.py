from typing import Optional, overload
from palworld_save_tools.gvas import GvasFile
from palworld_save_tools.archive import UUID

from palworld_pal_editor.core.pal_objects import PalObjects, toUUID
from palworld_pal_editor.utils import LOGGER


class PalContainer:
    def __init__(self, container_obj: dict) -> None:
        self._container_obj: dict = container_obj

        self._slots_data: dict = PalObjects.get_ArrayProperty(
            self._container_obj["value"]["Slots"]
        )

        if self.ID is None or not self._slots_data:
            raise Exception("Invalid Container")

        self.slots: list[ContainerSlot] = [
            ContainerSlot(slot_dict) for slot_dict in self._slots_data
        ]
        # TODO PRINT LOGS

    def __len__(self):
        return len(self.slots)
    
    def __str__(self) -> str:
        return f"{self.ID} - {len(self)}"

    @property
    def ID(self) -> Optional[UUID]:
        return PalObjects.get_BaseType(self._container_obj.get("key", {}).get("ID"))

    def add_pal(self, pal_id: UUID | str) -> int:
        if self.has_pal(pal_id):
            return -1
        
        slot_idx = self.get_empty_slot()
        if slot_idx == -1:
            return slot_idx

        slot = self.slots[slot_idx]
        slot.instance_id = pal_id
        LOGGER.info(f"Pal {pal_id} add to container {self.ID} @ {slot_idx} ")
        return slot_idx

    def del_pal(self, pal_id: UUID | str, slot_idx: int):
        if not self.has_pal(pal_id, slot_idx):
            if slot_idx < len(self.slots):
                LOGGER.warning(
                    f"Unmatched Pal Guid on del_pal: expect {str(self.slots[slot_idx].instance_id)} got {str(pal_id)}."
                )
            return

        self.slots[slot_idx].clear()

    def has_pal(self, pal_id: UUID | str, slot_idx: int = None) -> bool:
        if slot_idx is not None:
            if slot_idx >= len(self.slots):
                return False
            return self.slots[slot_idx].instance_id == pal_id
        else:
            for slot in self.slots:
                if str(slot.instance_id) == str(pal_id):
                    return True
            return False

    def reorder_pals(self, pal_ids: list[UUID | str]):
        id_num = len(pal_ids)
        for i in range(0, len(self.slots)):
            slot = self.slots[i]
            if i < id_num:
                slot.instance_id = pal_ids[i]
            else:
                slot.clear()

    def get_empty_slot(self) -> int:
        """
        Return: slot idx, or -1 if full
        """
        for i in range(0, len(self.slots)):
            if self.slots[i].isEmpty:
                return i
        return -1


class ContainerSlot:
    def __init__(self, slot_data: dict) -> None:
        self._slot_data: dict = slot_data
        self._slot_raw_data: dict = slot_data["RawData"]["value"]

    # def __eq__(self, __value: object) -> bool:
    #     if not isinstance(__value, ContainerSlot):
    #         return False
    #     return UUID.__eq__(self.instance_id, __value.instance_id)

    # def __hash__(self) -> int:
    #     return hash(str(self.instance_id))

    @property
    def isEmpty(self) -> bool:
        id = self.instance_id or PalObjects.EMPTY_UUID
        return id == PalObjects.EMPTY_UUID

    @property
    def instance_id(self) -> Optional[UUID]:
        return self._slot_raw_data.get("instance_id")

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
            except:
                LOGGER.info(f"Invalid Container {container_entity.ID}, skipping")
                continue

            self.container_map[container_entity.ID] = container_entity
            LOGGER.info(f"Container Found: {container_entity}")

    def get_container(self, id: UUID | str) -> Optional[PalContainer]:
        return self.container_map.get(id)

    def get_containers(self) -> list[PalContainer]:
        return self.container_map.values()
