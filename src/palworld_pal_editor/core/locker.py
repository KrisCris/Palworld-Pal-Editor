"""Which Pals the game believes are in a Dimensional Pal Storage.

`InLockerCharacterInstanceIDArray` lives in Level.sav, not in the DPS file it
describes: the world save keeps the list, each DPS `.sav` keeps the Pals. Both
halves have to agree or the game shows a storage it cannot open, so every
mutation that puts a Pal into a DPS or takes one out maintains this alongside
the slot itself.

It is read through the manager rather than handed a `GvasFile` because a reload
replaces that file, and an index holding the old one would maintain a locker
belonging to a save nobody has open any more.
"""

from typing import Optional

from palworld_pal_editor.core.pal_objects import PalObjects, toUUID
from palworld_save_tools.archive import UUID


class LockerIndex:
    def __init__(self, manager) -> None:
        self._manager = manager

    def entries(self) -> list[dict]:
        """The live list, created on first use if this save has never had one."""
        world_data = self._manager.gvas_file.properties["worldSaveData"]["value"]
        locker = world_data.get("InLockerCharacterInstanceIDArray")
        if locker is None:
            locker = PalObjects.InLockerCharacterInstanceIDArray()
            world_data["InLockerCharacterInstanceIDArray"] = locker
        return locker["value"]

    @staticmethod
    def _instance_id(entry: dict) -> Optional[UUID]:
        return PalObjects.get_BaseType(entry.get("InstanceId"))

    def add(self, instance_id: UUID | str) -> None:
        instance_id = toUUID(str(instance_id))
        if any(self._instance_id(entry) == instance_id for entry in self.entries()):
            return
        # A locker entry stores the fields bare, without the struct envelope an
        # external storage slot wraps them in.
        self.entries().append(PalObjects.PalInstanceIDFields(instance_id))

    def remove(self, instance_id: UUID | str) -> None:
        instance_id = toUUID(str(instance_id))
        entries = self.entries()
        # In place: the list is the one the save holds, and rebinding the name
        # here would leave the save's own list untouched.
        entries[:] = [
            entry for entry in entries if self._instance_id(entry) != instance_id
        ]
