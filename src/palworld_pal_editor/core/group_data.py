from typing import Optional
from palworld_save_tools.gvas import GvasFile
from palworld_save_tools.archive import UUID

from palworld_pal_editor.core.pal_objects import PalObjects
from palworld_pal_editor.utils import LOGGER


class PalGroup:
    def __init__(self, group_obj: dict):
        self._group_obj: dict = group_obj
        self._group_param: dict = group_obj["value"]["RawData"]["value"]
        if (not self.players) and (not self.base_ids):
            raise Exception("Empty Guild")

        self.instance_map = {}
        self.player_map = {}

        for instance in self.individual_character_handle_ids or []:
            self.instance_map[str(instance["instance_id"])] = self.instance_map

        for player in self.players or []:
            self.player_map[str(player["player_uid"])] = player

    def add_pal(self, instanceId: UUID | str) -> bool:
        if instanceId in self.instance_map:
            return False
        new_handle = PalObjects.individual_character_handle_id(instanceId)
        self.instance_map[str(instanceId)] = new_handle
        if self.individual_character_handle_ids is None:
            self._group_param["individual_character_handle_ids"] = []
        self.individual_character_handle_ids.append(new_handle)
        return True
    
    def del_pal(self, instanceId: UUID | str):
        if instanceId not in self.instance_map:
            return
        handle = self.instance_map.pop(instanceId)
        self.individual_character_handle_ids.remove(handle)

    @property
    def group_id(self) -> Optional[UUID]:
        return self._group_param.get("group_id")

    @property
    def individual_character_handle_ids(self) -> Optional[list[dict]]:
        return self._group_param.get("individual_character_handle_ids")

    @property
    def base_ids(self) -> Optional[list[UUID]]:
        return self._group_param.get("base_ids")

    @property
    def guild_name(self) -> Optional[str]:
        return self._group_param.get("guild_name")

    @property
    def players(self) -> Optional[list[dict]]:
        return self._group_param.get("players")


class GroupData:
    def __init__(self, gvas_file: GvasFile) -> None:
        self.group_map = {}
        self._GSDM = gvas_file.properties["worldSaveData"]["value"]["GroupSaveDataMap"]

        for group in self._GSDM["value"]:
            group_id: UUID = group.get("key")
            if not group_id:
                continue

            group_type = PalObjects.get_EnumProperty(
                group.get("value", {}).get("GroupType")
            )
            if group_type != "EPalGroupType::Guild":
                continue

            try:
                group_entity = PalGroup(group)
            except:
                LOGGER.info(f"Empty Guild {group_id}, skipping")
                continue

            self.group_map[str(group_id)] = group_entity

    def get_group(self, group_id: UUID | str) -> Optional[PalGroup]:
        self.group_map.get(group_id)

    def get_groups(self) -> list[PalGroup]:
        return self.group_map.values()
