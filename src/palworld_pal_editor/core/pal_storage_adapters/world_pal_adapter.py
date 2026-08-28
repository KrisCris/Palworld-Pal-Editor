from typing import Iterator, Optional

from palworld_save_tools.archive import UUID

from palworld_pal_editor.core.container_data import ContainerData
from palworld_pal_editor.core.pal_entity import PalEntity
from palworld_pal_editor.core.pal_objects import PalObjects, get_nested_attr
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
        if parameter.get("struct_type") != "PalIndividualCharacterSaveParameter":
            return None
        return parameter

    @staticmethod
    def is_player(native_record: dict) -> bool:
        parameter = WorldPalAdapter.save_parameter(native_record)
        if parameter is None:
            return False
        return bool(PalObjects.get_BaseType(parameter["value"].get("IsPlayer")))

    @staticmethod
    def set_group_id(native_record: dict, group_id: UUID | str) -> None:
        """Write the guild id on a World record that has no PalRecord yet."""
        native_record["value"]["RawData"]["value"]["group_id"] = group_id

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

            located = self._occupies_recorded_slot(pal)
            pal.is_unreferenced_pal = not located
            if not located:
                LOGGER.info(f"Likely Ghost Pal: {pal}")

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

    def _occupies_recorded_slot(self, pal: PalEntity) -> bool:
        """Whether the one slot the Pal records for itself really holds it."""
        container = self._container_data.get_container(pal.ContainerId)
        if container is None:
            return False
        slot_index = pal.SlotIndex
        slot = next(
            (slot for slot in container.slots if slot.inv_idx == slot_index), None
        )
        if slot is None:
            return False
        return str(slot.instance_id) == str(pal.InstanceId)

    @staticmethod
    def envelope(record: PalRecord) -> dict:
        """A World-shaped record for `record`, built when the Pal lives elsewhere.

        Legacy: raw JSON export, template save and duplicate still speak the World
        envelope no matter where the Pal actually is. S3c replaces those callers with
        a SaveParameter-level payload and deletes this together with the fake shape.
        """
        if record.storage_kind == "world":
            return record.native_record
        return {
            "key": record.native_record["InstanceId"]["value"],
            "value": {
                "RawData": {
                    "value": {
                        "group_id": PalObjects.EMPTY_UUID,
                        "object": {
                            "SaveParameter": record.native_record["SaveParameter"]
                        },
                    }
                }
            },
        }
