"""What a player is carrying: inventory and equipment slots, and the items in them.

Two structures that have to be maintained together. `ItemContainerSaveData` holds
each container's slots -- an item id and a count -- and `DynamicItemSaveData` holds
the per-item state a stack cannot express, such as a weapon's durability and the
rounds left in its magazine. A slot points at a dynamic entry by id, so adding,
replacing or clearing a slot means writing both, and a dynamic entry nothing points
at any more has to go.

Only the containers a player can meaningfully edit are exposed
(`EDITABLE_CONTAINERS`); the rest are left alone.
"""

from __future__ import annotations

import copy
import uuid
from typing import TYPE_CHECKING, Optional

from palworld_save_tools.archive import UUID
from palworld_save_tools.gvas import GvasFile

from palworld_pal_editor.core.pal_objects import PalObjects, toUUID
from palworld_pal_editor.utils.data_provider import DataProvider

if TYPE_CHECKING:
    from palworld_pal_editor.core.player_entity import PlayerEntity


EMPTY_UUID = "00000000-0000-0000-0000-000000000000"
ITEM_SLOT_CUSTOM_VERSION = bytes(
    [
        1,
        0,
        0,
        0,
        126,
        180,
        234,
        18,
        154,
        27,
        90,
        255,
        113,
        170,
        113,
        188,
        223,
        51,
        214,
        14,
        1,
        0,
        0,
        0,
    ]
)
DYNAMIC_ITEM_CUSTOM_VERSION = bytes(
    [
        1,
        0,
        0,
        0,
        56,
        11,
        0,
        222,
        73,
        73,
        215,
        206,
        151,
        223,
        45,
        153,
        192,
        193,
        195,
        105,
        1,
        0,
        0,
        0,
    ]
)
ARMOR_SLOT_GROUPS = {
    0: "Head",
    1: "Body",
    2: "Accessory",
    3: "Accessory",
    4: "Shield",
    5: "Glider",
    6: "Accessory",
    7: "Accessory",
    8: "SphereModule",
}
EDITABLE_CONTAINERS = {"common", "key_items", "weapons", "armor", "food"}


def _uuid_string(value: object) -> str:
    return str(value).lower()


def _byte_array(value: bytes) -> dict:
    return PalObjects.ArrayProperty("ByteProperty", {"values": value})


class ItemContainerData:
    def __init__(self, gvas_file: GvasFile) -> None:
        world = gvas_file.properties["worldSaveData"]["value"]
        self.container_entries: list[dict] = world.get("ItemContainerSaveData", {}).get(
            "value", []
        )
        self.dynamic_entries: list[dict] = (
            world.get("DynamicItemSaveData", {}).get("value", {}).get("values", [])
        )
        self.containers: dict[str, dict] = {}
        self.dynamic_items: dict[str, dict] = {}
        self.index_warnings: list[str] = []
        self._rebuild_indexes()

    def _rebuild_indexes(self) -> None:
        self.containers.clear()
        self.dynamic_items.clear()
        self.index_warnings.clear()
        for entry in self.container_entries:
            try:
                container_id = _uuid_string(entry["key"]["ID"]["value"])
                if container_id in self.containers:
                    self.index_warnings.append(
                        f"duplicate item container GUID: {container_id}"
                    )
                    continue
                self.containers[container_id] = entry
            except (KeyError, TypeError):
                self.index_warnings.append("malformed item container entry")
        for entry in self.dynamic_entries:
            try:
                raw = entry["RawData"]["value"]
                dynamic_id = _uuid_string(raw["id"]["local_id_in_created_world"])
                if dynamic_id == EMPTY_UUID:
                    self.index_warnings.append("dynamic item has a nil local GUID")
                    continue
                if dynamic_id in self.dynamic_items:
                    self.index_warnings.append(
                        f"duplicate dynamic item GUID: {dynamic_id}"
                    )
                    continue
                self.dynamic_items[dynamic_id] = entry
            except (KeyError, TypeError):
                self.index_warnings.append("malformed dynamic item entry")

    @staticmethod
    def _slot_values(container: dict) -> list[dict]:
        return container["value"]["Slots"]["value"]["values"]

    @staticmethod
    def _slot_num(container: dict) -> int:
        return int(container["value"]["SlotNum"]["value"])

    def _container_for(
        self, player: PlayerEntity, container_kind: str
    ) -> tuple[Optional[str], Optional[dict]]:
        container_id = player.InventoryContainerIds.get(container_kind)
        if container_id is None:
            return None, None
        key = _uuid_string(container_id)
        return key, self.containers.get(key)

    def _normalized_slot(self, raw_slot: Optional[dict], slot_index: int) -> dict:
        if raw_slot is None:
            return {
                "slot_index": slot_index,
                "static_id": None,
                "effective_static_id": None,
                "count": 0,
                "dynamic_id": None,
                "dynamic_type": None,
                "durability": None,
                "ammo": None,
                "character_id": None,
                "warning": None,
            }
        raw = raw_slot["RawData"]["value"]
        static_id = raw["item"]["static_id"]
        local_id = _uuid_string(raw["item"]["dynamic_id"]["local_id_in_created_world"])
        item = DataProvider.get_item(static_id)
        warning = None
        dynamic = None if local_id == EMPTY_UUID else self.dynamic_items.get(local_id)
        dynamic_raw = dynamic["RawData"]["value"] if dynamic else None
        effective_static_id = (
            dynamic_raw["id"]["static_id"] if dynamic_raw is not None else static_id
        )
        effective_item = DataProvider.get_item(effective_static_id)
        if item is None:
            warning = f"unknown item: {static_id}"
        elif local_id != EMPTY_UUID and dynamic_raw is None:
            warning = f"dangling dynamic item GUID: {local_id}"
        elif effective_item is None:
            warning = f"unknown dynamic item: {effective_static_id}"
        elif effective_static_id != static_id and any(
            item.get(field) != effective_item.get(field)
            for field in ("NameKey", "Group", "TypeA", "TypeB", "DynamicType")
        ):
            warning = "dynamic item static ID does not match its slot family"
        return {
            "slot_index": slot_index,
            "static_id": static_id,
            "effective_static_id": effective_static_id,
            "count": int(raw["count"]),
            "dynamic_id": None if local_id == EMPTY_UUID else local_id,
            "dynamic_type": dynamic_raw.get("type") if dynamic_raw else None,
            "durability": dynamic_raw.get("durability") if dynamic_raw else None,
            "ammo": dynamic_raw.get("remaining_bullets") if dynamic_raw else None,
            "character_id": dynamic_raw.get("character_id") if dynamic_raw else None,
            "warning": warning,
        }

    def inventory_snapshot(self, player: PlayerEntity) -> dict:
        containers = {}
        warnings = list(self.index_warnings)
        for kind in ("weapons", "armor", "food", "common", "key_items", "drop"):
            container_id, container = self._container_for(player, kind)
            if container is None:
                warning = (
                    f"player has no {kind} container reference"
                    if container_id is None
                    else f"referenced {kind} container was not found: {container_id}"
                )
                containers[kind] = {
                    "id": container_id,
                    "slot_num": 0,
                    "editable": False,
                    "slots": [],
                    "warning": warning,
                }
                warnings.append(warning)
                continue
            slot_num = self._slot_num(container)
            by_index = {}
            for slot in self._slot_values(container):
                try:
                    index = int(slot["RawData"]["value"]["slot_index"])
                except (KeyError, TypeError, ValueError):
                    warnings.append(f"{kind} contains a malformed slot")
                    continue
                if index < 0 or index >= slot_num:
                    warnings.append(f"{kind} slot index is outside SlotNum: {index}")
                    continue
                if index in by_index:
                    warnings.append(f"{kind} contains duplicate slot index: {index}")
                    continue
                by_index[index] = slot
            containers[kind] = {
                "id": container_id,
                "slot_num": slot_num,
                "editable": kind in EDITABLE_CONTAINERS,
                "slots": [
                    self._normalized_slot(by_index.get(index), index)
                    for index in range(slot_num)
                ],
                "warning": None,
            }
        return {"containers": containers, "warnings": warnings}

    @staticmethod
    def _allowed_group(container_kind: str, slot_index: int) -> Optional[str]:
        if container_kind == "key_items":
            return "KeyItem"
        if container_kind == "weapons":
            return "Weapon"
        if container_kind == "food":
            return "Food"
        if container_kind == "armor":
            try:
                return ARMOR_SLOT_GROUPS[slot_index]
            except KeyError as error:
                raise ValueError(f"Unknown armor slot: {slot_index}") from error
        return None

    @staticmethod
    def _validate_item(
        container_kind: str,
        slot_index: int,
        item_id: str,
        count: int,
        allow_overstack: bool,
    ) -> tuple[dict, int]:
        item = DataProvider.get_item(item_id)
        if item is None:
            raise ValueError(f"Unknown item: {item_id}")
        if (
            not item["Legal"]
            or item["Disabled"]
            or item["MonsterOnly"]
            or item["Group"] == "None"
        ):
            raise ValueError(f"Item is not selectable: {item_id}")
        if item["DynamicType"] == "egg":
            raise ValueError(
                "Creating eggs requires a contained Pal and is not supported"
            )
        allowed = ItemContainerData._allowed_group(container_kind, slot_index)
        if container_kind == "common":
            if item["Group"] == "KeyItem":
                raise ValueError("Key items must use the key-item container")
        elif item["Group"] != allowed:
            raise ValueError(
                f"{item_id} belongs to {item['Group']}, expected {allowed}"
            )
        if container_kind in {"weapons", "armor"}:
            count = 1
        if type(count) is not int or count < 1 or count > 999_999:
            raise ValueError("Item count must be between 1 and 999999")
        if not allow_overstack and count > item["MaxStackCount"]:
            raise ValueError(
                f"Item count exceeds MaxStackCount {item['MaxStackCount']}"
            )
        return item, count

    @staticmethod
    def _new_slot_entry(
        slot_index: int,
        count: int,
        item_id: str,
        dynamic_id: Optional[UUID],
    ) -> dict:
        local_id = dynamic_id or PalObjects.EMPTY_UUID
        return {
            "RawData": PalObjects.ArrayProperty(
                "ByteProperty",
                {
                    "slot_index": slot_index,
                    "count": count,
                    "item": {
                        "static_id": item_id,
                        "dynamic_id": {
                            "created_world_id": PalObjects.EMPTY_UUID,
                            "local_id_in_created_world": local_id,
                        },
                    },
                    "trailing_bytes": bytes(20),
                },
                ".worldSaveData.ItemContainerSaveData.Value.Slots.Slots.RawData",
            ),
            "CustomVersionData": _byte_array(ITEM_SLOT_CUSTOM_VERSION),
        }

    @staticmethod
    def _new_dynamic_entry(item_id: str, item: dict, dynamic_id: UUID) -> dict:
        dynamic_type = item["DynamicType"]
        base = {
            "type": dynamic_type,
            "id": {
                "created_world_id": PalObjects.EMPTY_UUID,
                "local_id_in_created_world": dynamic_id,
                "static_id": item_id,
            },
            "leading_bytes": bytes(4),
            "durability": float(item["MaxDurability"]),
            "trailing_bytes": bytes(4),
        }
        if dynamic_type == "weapon":
            base.update(
                {
                    "remaining_bullets": item["MagazineSize"],
                    "passive_skill_list": [],
                    "unknown_str": "None",
                }
            )
        elif dynamic_type != "armor":
            raise ValueError(f"Unsupported new dynamic item type: {dynamic_type}")
        return {
            "RawData": PalObjects.ArrayProperty(
                "ByteProperty",
                base,
                ".worldSaveData.DynamicItemSaveData.DynamicItemSaveData.RawData",
            ),
            "CustomVersionData": _byte_array(DYNAMIC_ITEM_CUSTOM_VERSION),
        }

    def _new_dynamic_id(self) -> UUID:
        while True:
            value = toUUID(str(uuid.uuid4()))
            if value is not None and _uuid_string(value) not in self.dynamic_items:
                return value

    def _dynamic_reference_count(self, dynamic_id: str) -> int:
        count = 0
        for container in self.containers.values():
            for slot in self._slot_values(container):
                try:
                    local_id = _uuid_string(
                        slot["RawData"]["value"]["item"]["dynamic_id"][
                            "local_id_in_created_world"
                        ]
                    )
                except (KeyError, TypeError):
                    continue
                count += local_id == dynamic_id
        return count

    def repair_slot(
        self, player: PlayerEntity, container_kind: str, slot_index: int
    ) -> dict:
        """Put one worn item back to the maxima the game data gives it.

        Durability and ammunition together, because they wear out together and
        restoring one without the other leaves the item still unusable.

        This edits the dynamic entry in place rather than replacing the item.
        Re-placing it would restore both, but it would mint a new dynamic id and
        throw away everything else the entry holds -- a weapon's passive skills
        above all -- which is a replacement, not a repair.

        The two maxima are not equally trustworthy, which is why each is applied
        only where it is known. `MagazineSize` is sound: across the fixture save's
        2095 loaded weapons, not one carries more ammunition than its magazine,
        and none carries ammunition without one. `MaxDurability` is 0 in the game
        data for grappling guns, sphere launchers and the NPC weapons, while real
        ones in a save carry 150 to 450, so writing "the maximum" there would
        write a zero over a working item. An item with neither maximum known is
        refused rather than silently left alone.
        """
        if container_kind not in EDITABLE_CONTAINERS:
            raise ValueError(f"Container is not editable: {container_kind}")
        _container_id, container = self._container_for(player, container_kind)
        if container is None:
            raise ValueError(f"Player {container_kind} container is missing")
        slot_num = self._slot_num(container)
        if type(slot_index) is not int or slot_index < 0 or slot_index >= slot_num:
            raise ValueError(f"Slot index is outside SlotNum: {slot_index}")

        slot = next(
            (
                candidate
                for candidate in self._slot_values(container)
                if candidate["RawData"]["value"]["slot_index"] == slot_index
            ),
            None,
        )
        if slot is None:
            raise ValueError(f"Slot {slot_index} is empty")
        local_id = _uuid_string(
            slot["RawData"]["value"]["item"]["dynamic_id"]["local_id_in_created_world"]
        )
        dynamic = None if local_id == EMPTY_UUID else self.dynamic_items.get(local_id)
        if dynamic is None:
            raise ValueError("This item has nothing to restore")
        dynamic_raw = dynamic["RawData"]["value"]

        static_id = dynamic_raw["id"]["static_id"]
        item = DataProvider.get_item(static_id) or {}
        restored = []
        maximum = item.get("MaxDurability")
        if "durability" in dynamic_raw and maximum:
            dynamic_raw["durability"] = float(maximum)
            restored.append("durability")
        magazine = item.get("MagazineSize")
        if "remaining_bullets" in dynamic_raw and magazine:
            dynamic_raw["remaining_bullets"] = int(magazine)
            restored.append("ammo")

        if not restored:
            raise ValueError(
                f"The game data gives {static_id} no maximum durability or "
                "magazine size to restore"
            )
        return self._normalized_slot(slot, slot_index)

    def patch_slot(
        self,
        player: PlayerEntity,
        container_kind: str,
        slot_index: int,
        item_id: Optional[str],
        count: int,
        *,
        allow_overstack: bool,
    ) -> dict:
        if container_kind not in EDITABLE_CONTAINERS:
            raise ValueError(f"Container is not editable: {container_kind}")
        _container_id, container = self._container_for(player, container_kind)
        if container is None:
            raise ValueError(f"Player {container_kind} container is missing")
        slot_num = self._slot_num(container)
        if type(slot_index) is not int or slot_index < 0 or slot_index >= slot_num:
            raise ValueError(f"Slot index is outside SlotNum: {slot_index}")
        slots = self._slot_values(container)
        old_slot = next(
            (
                slot
                for slot in slots
                if slot["RawData"]["value"]["slot_index"] == slot_index
            ),
            None,
        )
        old_dynamic_id = None
        if old_slot is not None:
            value = old_slot["RawData"]["value"]["item"]["dynamic_id"]
            local_id = _uuid_string(value["local_id_in_created_world"])
            old_dynamic_id = None if local_id == EMPTY_UUID else local_id

        new_slot = None
        new_dynamic = None
        if item_id is not None:
            item, count = self._validate_item(
                container_kind, slot_index, item_id, count, allow_overstack
            )
            dynamic_id = (
                self._new_dynamic_id() if item["DynamicType"] is not None else None
            )
            new_slot = self._new_slot_entry(slot_index, count, item_id, dynamic_id)
            if dynamic_id is not None:
                new_dynamic = self._new_dynamic_entry(item_id, item, dynamic_id)

        original_slots = copy.deepcopy(slots)
        original_dynamics = copy.deepcopy(self.dynamic_entries)
        warning = None
        try:
            slots[:] = [
                slot
                for slot in slots
                if slot["RawData"]["value"]["slot_index"] != slot_index
            ]
            if new_slot is not None:
                slots.append(new_slot)
                slots.sort(key=lambda slot: slot["RawData"]["value"]["slot_index"])
            if new_dynamic is not None:
                self.dynamic_entries.append(new_dynamic)
            if old_dynamic_id is not None:
                references = self._dynamic_reference_count(old_dynamic_id)
                if references == 0:
                    self.dynamic_entries[:] = [
                        entry
                        for entry in self.dynamic_entries
                        if _uuid_string(
                            entry["RawData"]["value"]["id"]["local_id_in_created_world"]
                        )
                        != old_dynamic_id
                    ]
                else:
                    warning = (
                        f"preserved shared dynamic item {old_dynamic_id} "
                        f"referenced by {references} other slot(s)"
                    )
            self._rebuild_indexes()
            result = self._normalized_slot(new_slot, slot_index)
            if warning:
                result["warning"] = warning
            return result
        except Exception:
            slots[:] = original_slots
            self.dynamic_entries[:] = original_dynamics
            self._rebuild_indexes()
            raise
