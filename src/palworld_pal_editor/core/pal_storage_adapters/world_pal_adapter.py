import copy
from typing import Iterator, Optional

from palworld_save_tools.archive import UUID

from palworld_pal_editor.core.container_data import ContainerData
from palworld_pal_editor.core.pal_entity import PalEntity
from palworld_pal_editor.core.pal_objects import (
    CHARACTER_PARAMETER_STRUCT,
    PalObjects,
    get_nested_attr,
    json_native,
)
from palworld_pal_editor.core.pal_record import PalRecord
from palworld_pal_editor.utils import LOGGER


class WorldPalAdapter:
    """Reads and writes the Pals stored in Level.sav's CharacterSaveParameterMap.

    A World record is shaped like::

        {"key": <identity>,
         "value": {"RawData": {"value": {"group_id": <guid>,
                                         "object": {"SaveParameter": <parameter>}}}}}

    Players are stored in the same array under the same shape, which is why this
    class also answers ``is_player``: the load path walks the array once for players
    and once for Pals, and neither pass should re-derive that layout.
    """

    kind = "world"

    def __init__(
        self, entities_list: list[dict], container_data: ContainerData
    ) -> None:
        self._entities_list = entities_list
        self._container_data = container_data

    @staticmethod
    def entity(native_record: dict) -> PalEntity:
        """Bind a PalEntity to the two real parent dicts inside a World record."""
        return PalEntity(
            native_record["key"],
            native_record["value"]["RawData"]["value"]["object"],
        )

    @staticmethod
    def save_parameter(native_record: dict) -> Optional[dict]:
        """The entry's native SaveParameter property, or None if it is not a character."""
        parameter = get_nested_attr(
            native_record, ["value", "RawData", "value", "object", "SaveParameter"]
        )
        if not isinstance(parameter, dict):
            return None
        if parameter.get("struct_type") != CHARACTER_PARAMETER_STRUCT:
            return None
        return parameter

    @classmethod
    def detach(cls, native_record) -> Optional[dict]:
        """The complete SaveParameter inside a World record, or None if it is not one.

        Strict on purpose (spec §6.1): the identity half has to be there, the
        property has to say it is a character parameter, and a player is not a Pal.
        A dict that merely contains something named SaveParameter is not a World
        record, and guessing would import it into a save as one.
        """
        if not isinstance(native_record, dict) or "key" not in native_record:
            return None
        parameter = cls.save_parameter(native_record)
        if parameter is None or cls.is_player(native_record):
            return None
        return copy.deepcopy(parameter)

    @staticmethod
    def export(record: PalRecord) -> dict:
        """This Pal as a complete World record, in JSON-native values (spec §6.1)."""
        return json_native(record.native_record)

    @classmethod
    def native_record(
        cls,
        save_parameter: Optional[dict],
        *,
        instance_id: UUID | str,
        owner_uid: UUID | str,
        container_id: UUID | str,
        slot_index: int,
        group_id: UUID | str,
    ) -> dict:
        """A World record for one Pal, ready to append to CharacterSaveParameterMap.

        `save_parameter` is the complete gameplay payload the Pal is coming from --
        another storage format, a template, a pasted export -- or None for a Pal
        being invented here, which gets the default one. Either way identity and
        position belong to the target and are written after the payload lands: the
        outer `PlayerUId` stays empty, because a non-empty one makes the game hide
        the Pal.
        """
        record = PalObjects.PalSaveParameter(
            instance_id, owner_uid, container_id, slot_index, group_id
        )
        if save_parameter is not None:
            record["value"]["RawData"]["value"]["object"]["SaveParameter"] = (
                copy.deepcopy(save_parameter)
            )
            # The envelope the factory just wrote is already the target's; the only
            # thing the incoming payload still carries is where it used to sit.
            cls.entity(record).SlotId = (container_id, slot_index)
        return record

    def append(self, native_record: dict) -> None:
        """Put one new World record into CharacterSaveParameterMap."""
        self._entities_list.append(native_record)

    def remove(self, native_record: dict) -> int:
        """Take one World record out, answering where it was.

        The position carries no meaning to the game (spec §4.3), but a failed
        operation putting the record back where it was keeps the array byte-identical
        to what was loaded, which is worth the one integer.
        """
        entry_index = self._entities_list.index(native_record)
        self._entities_list.pop(entry_index)
        return entry_index

    def insert(self, entry_index: int, native_record: dict) -> None:
        self._entities_list.insert(entry_index, native_record)

    @staticmethod
    def is_player(native_record: dict) -> bool:
        parameter = WorldPalAdapter.save_parameter(native_record)
        if parameter is None:
            return False
        return bool(PalObjects.get_BaseType(parameter["value"].get("IsPlayer")))

    @staticmethod
    def storage_key(container_id: UUID | str | None) -> Optional[str]:
        if container_id is None:
            return None
        return f"world-container:{container_id}"

    @classmethod
    def record(
        cls,
        native_record: dict,
        *,
        storage_key: Optional[str],
        slot_index: Optional[int],
        storage_owner_uid: Optional[str],
        pal: Optional[PalEntity] = None,
    ) -> PalRecord:
        """Wrap one World record, binding a PalEntity to it unless one is supplied.

        Nothing here needs the loaded save, so tests and creation paths that hold a
        native record but no session can build one too.
        """
        pal = pal if pal is not None else cls.entity(native_record)
        return PalRecord(
            record_key=f"world:{pal.InstanceId}",
            storage_kind=cls.kind,
            storage_key=storage_key,
            slot_index=slot_index,
            native_record=native_record,
            pal=pal,
            storage_owner_uid=storage_owner_uid,
        )

    def records(self) -> Iterator[PalRecord]:
        """Every Pal in the World save, with its recorded container position checked.

        A Pal whose recorded ContainerId + SlotIndex does not resolve to a slot
        holding its own InstanceId keeps ``storage_key = None`` and stays out of the
        storage index rather than being given a position it does not occupy.
        """
        for native_record in self._entities_list:
            parameter = self.save_parameter(native_record)
            if parameter is None:
                LOGGER.warning(
                    "Non-player/pal data found in CharacterSaveParameterMap, "
                    f"skipping {native_record}"
                )
                continue
            if PalObjects.get_BaseType(parameter["value"].get("IsPlayer")):
                continue
            try:
                pal = self.entity(native_record)
            except Exception as error:
                LOGGER.error(f"Error occured while init'in object: {error}, skipping")
                continue

            # A Pal that does not occupy the slot it records is left without a
            # storage key; SaveManager logs every one of them once load finishes.
            located = self.occupies_recorded_slot(pal)

            yield self.record(
                native_record,
                storage_key=(
                    self.storage_key(pal.ContainerId) if located else None
                ),
                slot_index=pal.SlotIndex if located else None,
                storage_owner_uid=(
                    str(pal.OwnerPlayerUId) if pal.OwnerPlayerUId else None
                ),
                pal=pal,
            )

    def occupies_recorded_slot(self, pal: PalEntity) -> bool:
        """Whether the one slot the Pal records for itself really holds it.

        The whole of World location validation: resolve `ContainerId` + `SlotIndex`
        to one container and one slot and compare `instance_id`. No scan for the
        Pal elsewhere, and no verdict beyond yes or no.
        """
        container = self._container_data.get_container(pal.ContainerId)
        if container is None:
            return False
        slot = next(
            (slot for slot in container.slots if slot.SlotIndex == pal.SlotIndex),
            None,
        )
        if slot is None:
            return False
        return str(slot.instance_id) == str(pal.InstanceId)
