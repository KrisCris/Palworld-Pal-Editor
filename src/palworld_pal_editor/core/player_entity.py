import copy
from typing import Any, Optional
from palworld_save_tools.archive import UUID
from palworld_save_tools.gvas import GvasFile

from palworld_pal_editor.utils import LOGGER
from palworld_pal_editor.core.pal_entity import PalEntity
from palworld_pal_editor.core.pal_objects import PalObjects, StatusName
from palworld_pal_editor.utils.data_provider import DataProvider
from palworld_pal_editor.utils.util import clamp, type_guard


class PlayerEntity:
    MAX_LEVEL = 80
    MAX_INVALID_LEVEL = 100

    def __init__(
        self,
        group_id: UUID | str,
        player_obj: dict,
        gvas_file: GvasFile,
        compression_times: int,
    ) -> None:
        self._player_obj: dict = player_obj
        self._gvas_file: GvasFile = gvas_file
        self._gvas_compression_times: int = compression_times
        self.group_id = group_id

        if (
            self._player_obj["value"]["RawData"]["value"]["object"]["SaveParameter"][
                "struct_type"
            ]
            != "PalIndividualCharacterSaveParameter"
        ):
            raise Exception(
                f"{self._player_obj}'s save param is not PalIndividualCharacterSaveParameter"
            )

        self._player_key: dict = self._player_obj["key"]
        self._player_param: dict = self._player_obj["value"]["RawData"]["value"][
            "object"
        ]["SaveParameter"]["value"]
        if not PalObjects.get_BaseType(self._player_param.get("IsPlayer")):
            raise TypeError(
                "Expecting player_obj, received pal_obj: {} - {} - {} - {}".format(
                    PalObjects.get_BaseType(self._player_param.get("CharacterID")),
                    self.NickName,
                    self.PlayerUId,
                    self.InstanceId,
                )
            )

        self._player_save_data: dict = self._gvas_file.properties["SaveData"]["value"]

        IndividualId = self._player_save_data.get("IndividualId", {}).get("value", {})
        sav_playerUId = PalObjects.get_BaseType(IndividualId.get("PlayerUId"))
        sav_InstanceId = PalObjects.get_BaseType(IndividualId.get("InstanceId"))
        if self.PlayerUId != sav_playerUId:
            raise Exception(
                f"PlayerUId unmatch: Level.sav: {self.PlayerUId} v.s. playerid.sav {sav_playerUId}"
            )
        if self.InstanceId != sav_InstanceId:
            raise Exception(
                f"InstanceId unmatch: Level.sav: {self.InstanceId} v.s. playerid.sav {sav_InstanceId}"
            )
        

    def __str__(self) -> str:
        return "{} - {} - {}".format(self.NickName, self.PlayerUId, self.InstanceId)

    def __hash__(self) -> int:
        return hash((self.InstanceId.__hash__(), self.PlayerUId.__hash__()))

    def __eq__(self, __value: object) -> bool:
        return (
            isinstance(__value, PlayerEntity)
            and self.InstanceId == __value.InstanceId
            and self.PlayerUId == __value.PlayerUId
        )

    @property
    def PlayerUId(self) -> Optional[UUID]:
        return PalObjects.get_BaseType(self._player_key.get("PlayerUId"))

    @property
    def InstanceId(self) -> Optional[UUID]:
        return PalObjects.get_BaseType(self._player_key.get("InstanceId"))

    @property
    def NickName(self) -> Optional[str]:
        return PalObjects.get_BaseType(self._player_param.get("NickName"))
    
    @NickName.setter
    @LOGGER.change_logger("NickName")
    @type_guard
    def NickName(self, value: str) -> None:
        if self.NickName is None:
            self._player_param["NickName"] = PalObjects.StrProperty(value)
        else:
            self._player_param["NickName"]["value"] = value

        if not self.NickName:
            self._player_param.pop("NickName", None)

    @property
    def UnusedStatusPoint(self) -> Optional[int]:
        return PalObjects.get_BaseType(self._player_param.get("UnusedStatusPoint"))
    
    @UnusedStatusPoint.setter
    @LOGGER.change_logger("UnusedStatusPoint")
    @type_guard
    def UnusedStatusPoint(self, value: int) -> None:
        value = clamp(PalObjects.UInt16Min, PalObjects.UInt16Max, value)
        if self.UnusedStatusPoint is None:
            self._player_param["UnusedStatusPoint"] = PalObjects.IntProperty(value)
        else:
            PalObjects.set_BaseType(self._player_param["UnusedStatusPoint"], value)

    @property
    def GotStatusPointList(self) -> Optional[list[dict]]:
        return PalObjects.get_ArrayProperty(self._player_param.get("GotStatusPointList"))

    @property
    def StatusPoints(self) -> dict[str, int]:
        if not self.GotStatusPointList:
            self._player_param["GotStatusPointList"] = PalObjects.GotStatusPointList()
        return {
            PalObjects.get_BaseType(entry.get("StatusName")): (
                PalObjects.get_BaseType(entry.get("StatusPoint")) or 0
            )
            for entry in self.GotStatusPointList or []
        }

    @property
    def ExStatusPoints(self) -> dict[str, int]:
        return {
            PalObjects.get_BaseType(entry.get("StatusName")): (
                PalObjects.get_BaseType(entry.get("StatusPoint")) or 0
            )
            for entry in self.GotExStatusPointList or []
        }

    @property
    def StatusPointMaximums(self) -> dict[str, int]:
        maximums = PalObjects.StatusPointMaximums.copy()
        ex_points = self.ExStatusPoints
        for name in PalObjects.ExStatusNames:
            maximums[name] = max(0, maximums[name] - max(0, ex_points.get(name, 0)))
        return maximums

    @property
    def StatusPointTotals(self) -> dict[str, int]:
        normal = self.StatusPoints
        extra = self.ExStatusPoints
        return {
            name: normal.get(name, 0) + extra.get(name, 0)
            for name in PalObjects.StatusNames
        }

    @property
    def StatusPointMinimums(self) -> dict[str, int]:
        return {name: 0 for name in PalObjects.StatusNames}

    @LOGGER.change_logger("StatusPointTotals")
    @type_guard
    def set_TotalStatusPoint(self, name: str, points: int) -> None:
        if name not in PalObjects.ExStatusNames:
            raise ValueError(f"Player status does not support item points: {name}")

        normal = max(0, self.StatusPoints.get(name, 0))
        extra = max(0, self.ExStatusPoints.get(name, 0))
        unused = max(0, self.UnusedStatusPoint or 0)
        total = clamp(0, PalObjects.StatusPointMaximums[name], points)
        change = total - normal - extra

        if change < 0:
            refunded = min(normal, -change)
            next_normal = normal - refunded
            next_extra = extra - (-change - refunded)
            next_unused = unused + refunded
            if next_unused > PalObjects.UInt16Max:
                raise ValueError("Unused Stat Points would exceed the save limit")
        else:
            spent = min(unused, change)
            next_normal = normal + spent
            next_extra = extra + change - spent
            next_unused = unused - spent

        self.set_StatusPoint(name, next_normal)
        if not self.GotExStatusPointList:
            self._player_param["GotExStatusPointList"] = PalObjects.GotExStatusPointList()
        for entry in self.GotExStatusPointList or []:
            if PalObjects.get_BaseType(entry.get("StatusName")) == name:
                PalObjects.set_BaseType(entry["StatusPoint"], next_extra)
                break
        else:
            self.GotExStatusPointList.append(
                PalObjects.StatusPointStruct(name, next_extra)
            )
        self.UnusedStatusPoint = next_unused

    @LOGGER.change_logger("StatusPoints")
    @type_guard
    def set_StatusPoint(self, name: str, points: int) -> None:
        if name not in PalObjects.StatusNames:
            raise ValueError(f"Unknown player status upgrade: {name}")
        points = clamp(0, self.StatusPointMaximums[name], points)
        if not self.GotStatusPointList:
            self._player_param["GotStatusPointList"] = PalObjects.GotStatusPointList()
        for entry in self.GotStatusPointList or []:
            if PalObjects.get_BaseType(entry.get("StatusName")) == name:
                PalObjects.set_BaseType(entry["StatusPoint"], points)
                return
        self.GotStatusPointList.append(PalObjects.StatusPointStruct(name, points))
    
    @property
    def GotExStatusPointList(self) -> Optional[list[dict]]:
        return PalObjects.get_ArrayProperty(self._player_param.get("GotExStatusPointList"))
    
    @property
    def StatusPointHP(self) -> Optional[int]:
        if not self.GotStatusPointList:
            self._player_param["GotStatusPointList"] = PalObjects.GotStatusPointList()

        for sp in self.GotStatusPointList:
            if (PalObjects.get_BaseType(sp.get("StatusName")) == StatusName.MaxHP):
                status_point = PalObjects.get_BaseType(sp.get("StatusPoint"))
                return status_point
            
    @property
    def StatusPointSP(self) -> Optional[int]:
        if not self.GotStatusPointList:
            self._player_param["GotStatusPointList"] = PalObjects.GotStatusPointList()

        for sp in self.GotStatusPointList:
            if (PalObjects.get_BaseType(sp.get("StatusName")) == StatusName.MaxSP):
                status_point = PalObjects.get_BaseType(sp.get("StatusPoint"))
                return status_point
            
    @property
    def StatusPointATK(self) -> Optional[int]:
        if not self.GotStatusPointList:
            self._player_param["GotStatusPointList"] = PalObjects.GotStatusPointList()

        for sp in self.GotStatusPointList:
            if (PalObjects.get_BaseType(sp.get("StatusName")) == StatusName.Attack):
                status_point = PalObjects.get_BaseType(sp.get("StatusPoint"))
                return status_point
            
    @property
    def StatusPointCarryWeight(self) -> Optional[int]:
        if not self.GotStatusPointList:
            self._player_param["GotStatusPointList"] = PalObjects.GotStatusPointList()

        for sp in self.GotStatusPointList:
            if (PalObjects.get_BaseType(sp.get("StatusName")) == StatusName.CarryWeight):
                status_point = PalObjects.get_BaseType(sp.get("StatusPoint"))
                return status_point
            
    @property
    def StatusPointCaptureRate(self) -> Optional[int]:
        if not self.GotStatusPointList:
            self._player_param["GotStatusPointList"] = PalObjects.GotStatusPointList()

        for sp in self.GotStatusPointList:
            if (PalObjects.get_BaseType(sp.get("StatusName")) == StatusName.CaptureRate):
                status_point = PalObjects.get_BaseType(sp.get("StatusPoint"))
                return status_point
            
    @property
    def StatusPointWorkSpeed(self) -> Optional[int]:
        if not self.GotStatusPointList:
            self._player_param["GotStatusPointList"] = PalObjects.GotStatusPointList()

        for sp in self.GotStatusPointList:
            if (PalObjects.get_BaseType(sp.get("StatusName")) == StatusName.WorkSpeed):
                status_point = PalObjects.get_BaseType(sp.get("StatusPoint"))
                return status_point
            
    # do this for ex points as well, while ex points do not have the capture rate thing
    @property
    def ExStatusPointHP(self) -> Optional[int]:
        if not self.GotExStatusPointList:
            self._player_param["GotExStatusPointList"] = PalObjects.GotExStatusPointList()

        for sp in self.GotExStatusPointList:
            if (PalObjects.get_BaseType(sp.get("StatusName")) == StatusName.MaxHP):
                status_point = PalObjects.get_BaseType(sp.get("StatusPoint"))
                return status_point
            
    @property
    def ExStatusPointSP(self) -> Optional[int]:
        if not self.GotExStatusPointList:
            self._player_param["GotExStatusPointList"] = PalObjects.GotExStatusPointList()

        for sp in self.GotExStatusPointList:
            if (PalObjects.get_BaseType(sp.get("StatusName")) == StatusName.MaxSP):
                status_point = PalObjects.get_BaseType(sp.get("StatusPoint"))
                return status_point
    
    @property
    def ExStatusPointATK(self) -> Optional[int]:
        if not self.GotExStatusPointList:
            self._player_param["GotExStatusPointList"] = PalObjects.GotExStatusPointList()
        
        for sp in self.GotExStatusPointList:
            if (PalObjects.get_BaseType(sp.get("StatusName")) == StatusName.Attack):
                status_point = PalObjects.get_BaseType(sp.get("StatusPoint"))
                return status_point
            
    @property
    def ExStatusPointCarryWeight(self) -> Optional[int]:
        if not self.GotExStatusPointList:
            self._player_param["GotExStatusPointList"] = PalObjects.GotExStatusPointList()

        for sp in self.GotExStatusPointList:
            if (PalObjects.get_BaseType(sp.get("StatusName")) == StatusName.CarryWeight):
                status_point = PalObjects.get_BaseType(sp.get("StatusPoint"))
                return status_point
            
    @property
    def ExStatusPointWorkSpeed(self) -> Optional[int]:
        if not self.GotExStatusPointList:
            self._player_param["GotExStatusPointList"] = PalObjects.GotExStatusPointList()

        for sp in self.GotExStatusPointList:
            if (PalObjects.get_BaseType(sp.get("StatusName")) == StatusName.WorkSpeed):
                status_point = PalObjects.get_BaseType(sp.get("StatusPoint"))
                return status_point

    @property
    def Level(self) -> Optional[int]:
        return PalObjects.get_ByteProperty(self._player_param.get("Level"))
    
    @Level.setter
    @LOGGER.change_logger("Level")
    @type_guard
    def Level(self, value: int) -> None:
        value = clamp(1, PlayerEntity.MAX_INVALID_LEVEL, value)
        if self.Level == value:
            return
        if self.Level is None:
            self._player_param["Level"] = PalObjects.ByteProperty(1)
        
        status_points = value - self.Level
        new_unused_status_point = (self.UnusedStatusPoint or 0) + status_points
        if new_unused_status_point < 0:
            LOGGER.warning(f"Player {self} has insufficient status points to level down.")
            return
        
        PalObjects.set_ByteProperty(self._player_param["Level"], value)
        self.Exp = DataProvider.get_player_level_xp(self.Level)
        self.UnusedStatusPoint = new_unused_status_point
    
    @property
    def Exp(self) -> Optional[int]:
        return PalObjects.get_BaseType(self._player_param.get("Exp"))
    
    @Exp.setter
    @LOGGER.change_logger("Exp")
    @type_guard
    def Exp(self, value: int) -> None:
        if self.Exp is None:
            self._player_param["Exp"] = PalObjects.Int64Property(value)
        else:
            PalObjects.set_BaseType(self._player_param["Exp"], value)

    @property
    def OtomoCharacterContainerId(self) -> Optional[UUID]:
        return PalObjects.get_PalContainerId(
            self._player_save_data.get("OtomoCharacterContainerId")
        )

    @property
    def PalStorageContainerId(self) -> Optional[UUID]:
        return PalObjects.get_PalContainerId(
            self._player_save_data.get("PalStorageContainerId")
        )

    @property
    def InventoryContainerIds(self) -> dict[str, Optional[UUID]]:
        info = self._player_save_data.get("InventoryInfo") or self._player_save_data.get(
            "inventoryInfo"
        )
        values = info.get("value", {}) if isinstance(info, dict) else {}

        def container_id(*names: str) -> Optional[UUID]:
            return next(
                (
                    PalObjects.get_PalContainerId(values[name])
                    for name in names
                    if name in values
                ),
                None,
            )

        return {
            "common": container_id("CommonContainerId", "MainContainerId"),
            "drop": container_id("DropSlotContainerId"),
            "key_items": container_id("EssentialContainerId"),
            "weapons": container_id("WeaponLoadOutContainerId"),
            "armor": container_id("PlayerEquipArmorContainerId"),
            "food": container_id("FoodEquipContainerId"),
        }

    @property
    def OtomoOrder(self) -> Optional[str]:
        # what is this thing??
        return PalObjects.get_EnumProperty(self._player_save_data.get("OtomoOrder"))

    @property
    def UnlockedRecipeTechnologyNames(self) -> Optional[list[str]]:
        return PalObjects.get_ArrayProperty(
            self._player_save_data.get("UnlockedRecipeTechnologyNames")
        )

    def _unlocked_technology_name(self, tech: str) -> Optional[str]:
        return next(
            (
                unlocked
                for unlocked in self.UnlockedRecipeTechnologyNames or []
                if unlocked.casefold() == tech.casefold()
            ),
            None,
        )

    @LOGGER.change_logger("UnlockedRecipeTechnologyNames")
    def toggle_UnlockedRecipeTechnologyNames(self, tech: str, status: bool):
        if self.UnlockedRecipeTechnologyNames is None:
            self._player_save_data["UnlockedRecipeTechnologyNames"] = (
                PalObjects.ArrayProperty("NameProperty", {"values": []})
            )
        unlocked = self._unlocked_technology_name(tech)
        if status:
            if unlocked is not None:
                LOGGER.warning(f"Attempt to unlock {tech}, but it has already been unlocked, skipping")
                return
            self.UnlockedRecipeTechnologyNames.append(tech)
        else:
            if unlocked is None:
                LOGGER.warning(f"Attempt to lock {tech}, but it has not been unlocked, skipping")
                return
            self.UnlockedRecipeTechnologyNames.remove(unlocked)

    @LOGGER.change_logger("UnlockedRecipeTechnologyNames")
    def unlock_all_techs(self):
        if self.UnlockedRecipeTechnologyNames is None:
            self._player_save_data["UnlockedRecipeTechnologyNames"] = (
                PalObjects.ArrayProperty("NameProperty", {"values": []})
            )
        unlocked = {
            tech.casefold() for tech in self.UnlockedRecipeTechnologyNames
        }
        for tech in DataProvider.get_tech_data():
            if tech.casefold() not in unlocked:
                self.UnlockedRecipeTechnologyNames.append(tech)
                unlocked.add(tech.casefold())
        LOGGER.info(f"Unlocked all techs for {self}")

    def has_viewing_cage(self) -> bool:
        return self._unlocked_technology_name("DisplayCharacter") is not None

    def unlock_viewing_cage(self):
        self.toggle_UnlockedRecipeTechnologyNames("DisplayCharacter", True)

    @property
    def PlayerGVAS(self) -> Optional[tuple[GvasFile, int]]:
        if (self._gvas_file is None) or (self._gvas_compression_times is None):
            return None
        return self._gvas_file, self._gvas_compression_times

    @property
    def TechnologyPoint(self) -> Optional[int]:
        return PalObjects.get_BaseType(self._player_save_data.get("TechnologyPoint"))
    
    @TechnologyPoint.setter
    @LOGGER.change_logger("TechnologyPoint")
    @type_guard
    def TechnologyPoint(self, value: int) -> None:
        if self.TechnologyPoint is None:
            self._player_save_data["TechnologyPoint"] = PalObjects.IntProperty(value)
        else:
            PalObjects.set_BaseType(self._player_save_data["TechnologyPoint"], value)

    @property
    def bossTechnologyPoint(self) -> Optional[int]:
        return PalObjects.get_BaseType(self._player_save_data.get("bossTechnologyPoint"))
    
    @bossTechnologyPoint.setter
    @LOGGER.change_logger("bossTechnologyPoint")
    @type_guard
    def bossTechnologyPoint(self, value: int) -> None:
        if self.bossTechnologyPoint is None:
            self._player_save_data["bossTechnologyPoint"] = PalObjects.IntProperty(value)
        else:
            PalObjects.set_BaseType(self._player_save_data["bossTechnologyPoint"], value)
    
    def try_create_pal_record_data(self):
        if "RecordData" not in self._player_save_data:
            self._player_save_data["RecordData"] = PalObjects.PalLoggedinPlayerSaveDataRecordData()
        record_data = self._player_save_data["RecordData"]["value"]

        if "PalCaptureCount" not in record_data:
            record_data["PalCaptureCount"] = PalObjects.MapProperty("NameProperty", "IntProperty")
        
        if "PaldeckUnlockFlag" not in record_data:
            record_data["PaldeckUnlockFlag"] = PalObjects.MapProperty("NameProperty", "BoolProperty")

    @property
    def PalCaptureCount(self) -> Optional[list]:
        if not (record_data := self._player_save_data.get("RecordData", None)):
            return None
        record_data: dict = record_data["value"]
        return PalObjects.get_MapProperty(record_data.get("PalCaptureCount", None))
    
    @property
    def PaldeckUnlockFlag(self) -> Optional[list]:
        if not (record_data := self._player_save_data.get("RecordData", None)):
            return None
        record_data: dict = record_data["value"]
        return PalObjects.get_MapProperty(record_data.get("PaldeckUnlockFlag", None))

    def get_pal_capture_count(self, name: str) -> int:
        try:
            return self._player_save_data["RecordData"]["value"]["PalCaptureCount"]["value"][name]
        except:
            return 0
        
    def inc_pal_capture_count(self, name: str):
        self.try_create_pal_record_data()
        for record in self.PalCaptureCount:
            if record['key'].lower() == name.lower():
                record['value'] += 1
                return
        LOGGER.info(f"Creating new pal capture count record for {name}")
        self.PalCaptureCount.append({
            'key': name,
            'value': 1
        })

    def unlock_paldeck(self, name: str):
        self.try_create_pal_record_data()
        for record in self.PaldeckUnlockFlag:
            if record['key'].lower() == name.lower():
                record['value'] = True
                return
        self.PaldeckUnlockFlag.append({
            'key': name,
            'value': True
        })

    def settle_captured_pal(self, pal_entity: PalEntity) -> None:
        """Apply one Pal created this session to this player's capture records.

        Every rule here came out of the old save-time settlement unchanged: skip invalid
        Pals, skip Humans and Pals with no sorting key, skip a Pal with no paldeck
        record id, and treat a missing `SkillUnlock_<Pal>` as a warning rather than an
        error. Only the tracking moved out -- which Pals are new is `PalRepository`'s
        question now, and this settles exactly the one it is handed.
        """
        if DataProvider.is_pal_invalid(pal_entity.DataAccessKey):
            LOGGER.info(f"Skip player records update for invalid pal: {pal_entity}")
            return
        if pal_entity.IsHuman or not DataProvider.get_pal_sorting_key(pal_entity.DataAccessKey):
            LOGGER.info(f"Skip player records update for pal: {pal_entity}")
            return

        key = DataProvider.get_pal_paldeck_record_id(pal_entity.CharacterID)
        if key is None:
            LOGGER.info(f"Skip player records update for pal: {pal_entity}")
            return
        self.unlock_paldeck(key)
        self.inc_pal_capture_count(key)

        tech_key = "SkillUnlock_" + key
        if DataProvider.get_tech_i18n(tech_key) is None:
            LOGGER.warning(f"Technology {tech_key} not found, which may or may not be a bug. If you are unsure please report to the dev.")
        else:
            self.toggle_UnlockedRecipeTechnologyNames(tech_key, True)

    # The two player-file properties `settle_captured_pal` writes into. A save that
    # settles and then fails to write every output restores them, so a retry does not
    # count the same capture twice.
    _SETTLED_PROPERTIES = ("RecordData", "UnlockedRecipeTechnologyNames")

    def snapshot_capture_records(self) -> dict:
        return {
            name: copy.deepcopy(self._player_save_data.get(name))
            for name in self._SETTLED_PROPERTIES
        }

    def restore_capture_records(self, snapshot: dict) -> None:
        for name, value in snapshot.items():
            if value is None:
                self._player_save_data.pop(name, None)
            else:
                self._player_save_data[name] = value
