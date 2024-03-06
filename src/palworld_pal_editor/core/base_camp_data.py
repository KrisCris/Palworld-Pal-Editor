from typing import Optional
from palworld_save_tools.gvas import GvasFile
from palworld_save_tools.archive import UUID

from palworld_pal_editor.core.pal_objects import PalObjects
from palworld_pal_editor.utils import LOGGER


class PalBaseCamp:
    def __init__(self, camp_obj: dict):
        self._camp_obj: dict = camp_obj
        self._camp_param: dict = camp_obj["value"]["RawData"]["value"]

        if (not self.id) or (not self.owner_group_id):
            LOGGER.warning(str(self._camp_param))
            raise Exception("possible broken camp object")
        
    @property
    def id(self) -> Optional[UUID]:
        return self._camp_param.get("id")

    @property
    def name(self) -> Optional[str]:
        return self._camp_param.get("name")
    
    @property
    def owner_group_id(self) -> Optional[UUID]:
        return self._camp_param.get('group_id_belong_to')

class BaseCampData:
    def __init__(self, gvas_file: GvasFile) -> None:
        self.camp_map = {}
        self._BCSD: list[dict] = gvas_file.properties["worldSaveData"]["value"]["BaseCampSaveData"]

        for camp in self._BCSD["value"]:
            camp_id: UUID = camp.get("key")
            if not camp_id:
                continue

            try:
                camp_entity = PalBaseCamp(camp)
            except:
                LOGGER.info(f"Invalid Base Camp {camp_id}, skipping")
                continue

            self.camp_map[str(camp_id)] = camp_entity

    def get_camp(self, camp_id: UUID | str) -> Optional[PalBaseCamp]:
        self.camp_map.get(camp_id)

    def get_camps(self) -> list[PalBaseCamp]:
        return self.camp_map.values()

    def get_owned_camp(self, group_id: UUID | str) -> list[PalBaseCamp]:
        return [camp for camp in self.get_camps() if camp.owner_group_id == group_id]
